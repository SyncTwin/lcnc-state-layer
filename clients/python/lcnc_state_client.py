#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Python client of the LinuxCNC state layer.

Asyncio API (StateClient): read the hello (configuration: joints, axes,
spindles; the snapshot's per-joint/axis/spindle arrays are sized by it), subscribe, apply JSON Merge Patches, detect a gap
in seq and ask for a snapshot, verify the reconstructed state against a fresh
snapshot every N patches, send commands and wait for this client's own
command_result, store view state.

Blocking facade (RemoteStat / RemoteCommand / RemoteErrorChannel): the same
call shapes as linuxcnc.stat / linuxcnc.command / linuxcnc.error_channel, so
an existing GUI can switch with a couple of lines:

    s = RemoteStat("ws://127.0.0.1:8791/")    # instead of linuxcnc.stat()
    s.poll(); print(s.task_state, s.position)

Dependencies: python3-websockets (and python3-cbor2 / python3-msgpack only for
the binary encodings).
"""
import asyncio
import itertools
import json
import logging
import threading
import time

log = logging.getLogger("lcnc_state_client")


def merge_patch(target, patch):
    """RFC 7396 section 2."""
    if not isinstance(patch, dict):
        return patch
    if not isinstance(target, dict):
        target = {}
    for k, v in patch.items():
        if v is None:
            target.pop(k, None)
        else:
            target[k] = merge_patch(target.get(k), v)
    return target


def _codec(encoding):
    if encoding == "json":
        return (lambda o: json.dumps(o, separators=(",", ":"))), json.loads
    if encoding == "cbor":
        import cbor2
        return cbor2.dumps, cbor2.loads
    if encoding == "msgpack":
        import msgpack
        return (lambda o: msgpack.packb(o, use_bin_type=True),
                lambda d: msgpack.unpackb(d, raw=False))
    raise ValueError(encoding)


def first_difference(a, b, path=""):
    """Path of the first difference between two JSON values, or None."""
    if type(a) is not type(b):
        return path or "<root>"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return "%s/%s" % (path, k)
            d = first_difference(a[k], b[k], "%s/%s" % (path, k))
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return path + "[len]"
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, "%s[%d]" % (path, i))
            if d:
                return d
        return None
    return None if a == b else (path or "<root>")


class StateClient:
    def __init__(self, url, view_key=None, encoding="json", verify_every=0,
                 drop_every=0):
        self.url = url
        self.view_key = view_key
        self.encoding = encoding
        self.enc, self.dec = _codec(encoding)
        self.verify_every = verify_every
        self.drop_every = drop_every
        self.hello = None           # configuration message, first on every connection
        self.state = None
        self.seq = None
        self.epoch = None
        self.keepalive = None
        self.link = "down"          # down -> trying -> up (idea: pymachinetalk subscribe.py)
        self.last_rx = 0.0
        self.view_state = None
        self.server = {}
        self.ws = None
        self._ids = itertools.count(1)
        self._waiters = {}
        self._awaiting_snapshot = False
        self._verify_pending = False
        self._since_verify = 0
        self._patch_count = 0
        self.listeners = []
        self.stats = {"snapshots": 0, "patches": 0, "gaps": 0, "resyncs": 0,
                      "verified_equal": 0, "verified_mismatch": 0, "dropped": 0,
                      "bytes": 0, "view_state_updates": 0}
        self.ready = asyncio.Event()

    def _url(self):
        q = []
        if self.view_key:
            q.append("view_key=" + self.view_key)
        if self.encoding != "json":
            q.append("encoding=" + self.encoding)
        return self.url + (("&" if "?" in self.url else "?") + "&".join(q) if q else "")

    async def send(self, msg):
        await self.ws.send(self.enc(msg))

    async def resync(self):
        self._awaiting_snapshot = True
        self.stats["resyncs"] += 1
        await self.send({"type": "resync_request", "seq": self.seq or 0})

    async def run(self):
        """One connection; returns when it closes."""
        import websockets
        self.link = "trying"
        async with websockets.connect(self._url(), max_size=1 << 22) as ws:
            self.ws = ws
            async for raw in ws:
                self.last_rx = time.monotonic()
                self.stats["bytes"] += len(raw)
                await self._handle(self.dec(raw))
        self.link = "down"

    async def run_forever(self, retry=1.0, missed=5):
        """Reconnect on close or when nothing arrived for `missed` keepalive
        periods; each new connection starts with a fresh snapshot."""
        while True:
            task = asyncio.ensure_future(self.run())
            try:
                while not task.done():
                    await asyncio.sleep(0.2)
                    if (self.link == "up" and self.keepalive and
                            time.monotonic() - self.last_rx > missed * self.keepalive):
                        log.warning("no message for %d keepalive periods, reconnecting", missed)
                        task.cancel()
                        break
                await asyncio.gather(task, return_exceptions=True)
            except asyncio.CancelledError:
                task.cancel()
                raise
            self.link = "down"
            self.ready.clear()
            await asyncio.sleep(retry)

    async def _handle(self, msg):
        t = msg.get("type")
        if t == "hello":
            self.hello = msg
        elif t == "snapshot":
            self.stats["snapshots"] += 1
            if self._verify_pending and self.state is not None and msg["seq"] == self.seq:
                diff = first_difference(self.state, msg["state"])
                if diff is None:
                    self.stats["verified_equal"] += 1
                    log.info("verify at seq %d: reconstructed state == snapshot", self.seq)
                else:
                    self.stats["verified_mismatch"] += 1
                    log.error("verify at seq %d: MISMATCH at %s", self.seq, diff)
            self._verify_pending = False
            self._awaiting_snapshot = False
            if self.epoch is not None and msg.get("epoch") != self.epoch:
                log.warning("server epoch changed %s -> %s: sidecar restarted, seq restarts",
                            self.epoch, msg.get("epoch"))
            self.epoch = msg.get("epoch")
            self.state = msg["state"]
            self.seq = msg["seq"]
            self.server = msg.get("server", {})
            self.keepalive = self.server.get("keepalive")
            self.link = "up"
            if "view_state" in msg:
                self.view_state = msg["view_state"]["blob"]
            self.ready.set()
            for fn in self.listeners:
                fn(self, msg)
        elif t == "patch":
            if self.state is None or self._awaiting_snapshot:
                return
            self._patch_count += 1
            if self.drop_every and self._patch_count % self.drop_every == 0:
                self.stats["dropped"] += 1        # fault injection: lose this one
                return
            if msg["seq"] != self.seq + 1:
                self.stats["gaps"] += 1
                log.warning("seq gap: have %d, got %d -> resync_request", self.seq, msg["seq"])
                await self.resync()
                return
            self.state = merge_patch(self.state, msg["patch"])
            self.seq = msg["seq"]
            self.stats["patches"] += 1
            for fn in self.listeners:
                fn(self, msg)
            self._since_verify += 1
            if self.verify_every and self._since_verify >= self.verify_every:
                self._since_verify = 0
                self._verify_pending = True
                await self.send({"type": "resync_request", "seq": self.seq})
        elif t == "command_result":
            fut = self._waiters.pop(msg.get("id"), None)
            if fut is not None and not fut.done():
                fut.set_result(msg)
        elif t == "ping":
            pass                    # liveness only (last_rx updated)
        elif t == "view_state":
            self.view_state = msg["blob"]
            self.stats["view_state_updates"] += 1
        elif t == "error":
            log.warning("server error: %s", msg.get("message"))
            fut = self._waiters.pop(msg.get("in_reply_to"), None)
            if fut is not None and not fut.done():
                fut.set_result({"type": "command_result", "id": msg.get("in_reply_to"),
                                "outcome": "failed", "error": msg.get("message")})

    async def command(self, name, *args, timeout=None):
        cid = "%s-%d" % (id(self) & 0xffff, next(self._ids))
        fut = asyncio.get_running_loop().create_future()
        self._waiters[cid] = fut
        await self.send({"type": "command", "id": cid, "name": name, "args": list(args)})
        return await asyncio.wait_for(fut, timeout)

    async def view_state_put(self, blob, key=None):
        self.view_key = key or self.view_key
        await self.send({"type": "view_state_put", "key": self.view_key, "blob": blob})


# --------------------------------------------------------------- blocking
class _Background:
    """One asyncio loop in a thread holding a StateClient."""

    def __init__(self, url, **kw):
        self.loop = asyncio.new_event_loop()
        self.client = None
        self._kw = kw
        self._url = url
        self._started = threading.Event()
        self.thread = threading.Thread(target=self._main, daemon=True)
        self.thread.start()
        self._started.wait()
        asyncio.run_coroutine_threadsafe(self.client.ready.wait(), self.loop).result(10)

    def _main(self):
        asyncio.set_event_loop(self.loop)
        self.client = StateClient(self._url, **self._kw)
        self._started.set()
        self.loop.run_until_complete(self.client.run())

    def call(self, coro, timeout=None):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)


_shared = {}


def _bg(url):
    if url not in _shared:
        _shared[url] = _Background(url)
    return _shared[url]


JOINT_ARRAYS = ("joint", "homed", "limit", "joint_position", "joint_actual_position")


def _blank(v):
    """Zero value of the same shape (what linuxcnc.stat has in unused slots)."""
    if isinstance(v, dict):
        return {k: _blank(x) for k, x in v.items()}
    if isinstance(v, bool):
        return False
    return type(v)() if isinstance(v, (int, float, str, list)) else v


def expand_stat(stat, hello):
    """Back to the linuxcnc.stat shape: per-joint/spindle arrays padded to
    hello.stat_max, axis entries put at their axis index."""
    out = dict(stat)
    mx = hello["stat_max"]
    for k, n in [(k, mx["joints"]) for k in JOINT_ARRAYS] + [("spindle", mx["spindles"])]:
        v = out.get(k)
        if v:
            out[k] = v + [_blank(v[0]) for _ in range(n - len(v))]
    if out.get("axis"):
        full = [_blank(out["axis"][0]) for _ in range(mx["axes"])]
        for a, v in zip(hello["axes"], out["axis"]):
            full[a["index"]] = v
        out["axis"] = full
    return out


class RemoteStat:
    """linuxcnc.stat look-alike: poll() copies the latest state into attributes
    (lists become tuples, as linuxcnc.stat returns them; arrays expanded to
    the linuxcnc.stat lengths with expand_stat, so stat.axis[2] is Z)."""

    def __init__(self, url="ws://127.0.0.1:8791/"):
        self._bg = _bg(url)

    def poll(self):
        c = self._bg.client
        for k, v in expand_stat(c.state["stat"], c.hello).items():
            setattr(self, k, _tuplify(v))
        self.seq = c.seq


def _tuplify(v):
    if isinstance(v, list):
        return tuple(_tuplify(x) for x in v)
    return v


class RemoteErrorChannel:
    """linuxcnc.error_channel look-alike over the shared error ring: every
    instance sees every entry once (no single-consumer queue)."""

    KINDS = {"OPERATOR_ERROR": 11, "OPERATOR_TEXT": 12, "OPERATOR_DISPLAY": 13,
             "NML_ERROR": 1, "NML_TEXT": 2, "NML_DISPLAY": 3}

    def __init__(self, url="ws://127.0.0.1:8791/"):
        self._bg = _bg(url)
        self._seen = self._bg.client.state["errors"]["seq"]

    def poll(self):
        for e in self._bg.client.state["errors"]["recent"]:
            if e["seq"] > self._seen:
                self._seen = e["seq"]
                return (self.KINDS.get(e["kind"], 0), e["text"])
        return None


class RemoteCommand:
    """linuxcnc.command look-alike: every method sends a command and returns
    its command_result outcome; wait_complete() returns the last outcome."""

    def __init__(self, url="ws://127.0.0.1:8791/"):
        self._bg = _bg(url)
        self.last = None

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def call(*args):
            self.last = self._bg.call(self._bg.client.command(name, *args))
            return self.last
        return call

    def wait_complete(self, timeout=5.0):
        return self.last


# -------------------------------------------------------------------- CLI
async def _cli(args):
    c = StateClient(args.url, view_key=args.view_key, encoding=args.encoding,
                    verify_every=args.verify_every, drop_every=args.drop_every)
    task = asyncio.ensure_future(c.run())
    t0 = time.monotonic()
    try:
        await asyncio.wait_for(c.ready.wait(), 10)
        h, st = c.hello, c.state["stat"]
        if h is None:
            log.error("no hello before the snapshot")
            return 1
        lens = {k: len(st[k]) for k in ("joint", "axis", "spindle") if k in st}
        want = {"joint": h["joints"], "axis": len(h["axes"]), "spindle": h["spindles"]}
        sized = all(lens[k] == want[k] for k in lens)
        log.info("hello: joints=%d axes=%s spindles=%d kins=%d stat_max=%s; snapshot arrays %s %s",
                 h["joints"], "".join(a["letter"] for a in h["axes"]), h["spindles"],
                 h["kinematics_type"], h["stat_max"], lens,
                 "== hello" if sized else "!= hello %s" % want)
        if not sized:
            return 1
        log.info("snapshot seq=%d, %d stat fields, server=%s", c.seq,
                 len(c.state["stat"]), c.server)
        last_report = t0
        while time.monotonic() - t0 < args.duration:
            await asyncio.sleep(0.5)
            if task.done():
                break
            if time.monotonic() - last_report >= 10:
                last_report = time.monotonic()
                log.info("seq=%d stats=%s", c.seq, c.stats)
        # final verification against a fresh snapshot
        c._verify_pending = True
        await c.send({"type": "resync_request", "seq": c.seq})
        await asyncio.sleep(1.0)
    finally:
        task.cancel()
    log.info("final seq=%d stats=%s", c.seq, c.stats)
    return 0 if c.stats["verified_mismatch"] == 0 and c.stats["verified_equal"] > 0 else 1


def main():
    import argparse
    ap = argparse.ArgumentParser(description="subscribe and verify")
    ap.add_argument("url", nargs="?", default="ws://127.0.0.1:8791/")
    ap.add_argument("--view-key")
    ap.add_argument("--encoding", default="json", choices=("json", "cbor", "msgpack"))
    ap.add_argument("--verify-every", type=int, default=50,
                    help="compare reconstructed state with a fresh snapshot every N patches")
    ap.add_argument("--drop-every", type=int, default=0,
                    help="fault injection: silently drop every Nth patch")
    ap.add_argument("--duration", type=float, default=30)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    raise SystemExit(asyncio.run(_cli(args)))


if __name__ == "__main__":
    main()
