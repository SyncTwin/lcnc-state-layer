# SPDX-License-Identifier: GPL-2.0-or-later
"""Websocket transport for StateLayer (python3-websockets, Debian 12: 10.4,
Debian 13: 15.x; only API common to both is used).

URL query parameters:
    view_key=K     return the view state stored under K in the first snapshot
    encoding=E     json (default, text frames) | cbor | msgpack (binary frames)

Each client has a bounded outgoing queue.  A client that falls behind does not
make the sidecar buffer patches without limit (rmu75,
discussioncomment-18771183): its queue is flushed and it gets a fresh snapshot.
"""
import asyncio
import json
import logging
import urllib.parse

from . import codec
from .core import CommandError

log = logging.getLogger("lcnc_state.ws")

QUEUE_MAX = 256


def _path(ws):
    if hasattr(ws, "request") and getattr(ws, "request", None) is not None:
        return ws.request.path          # websockets >= 13 (new asyncio API)
    return getattr(ws, "path", "/")     # websockets 10.x legacy API


class Client:
    def __init__(self, ws, encoding, view_key, server):
        self.ws = ws
        self.encoding = encoding
        self.enc = codec.encoder(encoding)
        self.dec = codec.decoder(encoding)
        self.view_key = view_key
        self.server = server
        self.queue = asyncio.Queue(QUEUE_MAX)
        self.peer = getattr(ws, "remote_address", None)
        self.overflows = 0

    def push(self, data):
        try:
            self.queue.put_nowait(data)
        except asyncio.QueueFull:
            self.overflows += 1
            while not self.queue.empty():
                self.queue.get_nowait()
            log.warning("client %s fell behind, resending snapshot", self.peer)
            self.queue.put_nowait(self.enc(self.server.layer.snapshot(
                self.view_key, self.server.keepalive)))

    def send_msg(self, msg):
        self.push(self.enc(msg))


class Server:
    def __init__(self, layer, period, host="127.0.0.1", port=8791,
                 compression=True, ping_interval=20.0, ping_timeout=20.0,
                 validator=None, keepalive=2.0):
        self.layer = layer
        self.period = period
        self.host = host
        self.port = port
        self.compression = "deflate" if compression else None
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.validator = validator
        self.clients = set()
        self.tick_hooks = []
        self.keepalive = keepalive
        self._last_sent = 0.0
        self._cache = {}
        layer.subscribe(self._broadcast)

    # one encode per message and encoding, shared by all clients
    def _broadcast(self, msg):
        self._last_sent = asyncio.get_running_loop().time()
        self._cache = {}
        for c in list(self.clients):
            data = self._cache.get(c.encoding)
            if data is None:
                data = self._cache[c.encoding] = c.enc(msg)
            c.push(data)

    async def _ticker(self):
        loop = asyncio.get_running_loop()
        nxt = loop.time()
        while True:
            try:
                # stat is polled and commands / program runs are tracked
                # always; diff and send only while someone listens
                listening = bool(self.clients or self.tick_hooks)
                self.layer.tick(publish=listening)
                for h in self.tick_hooks:
                    h(self.layer)
                if (self.clients and self.keepalive and
                        loop.time() - self._last_sent >= self.keepalive):
                    self._broadcast({"type": "ping", "seq": self.layer.seq,
                                     "epoch": self.layer.epoch})
            except Exception:
                log.exception("tick failed")
            nxt += self.period
            delay = nxt - loop.time()
            if delay < 0:                 # overran: skip, do not burst
                nxt = loop.time()
                delay = 0
            await asyncio.sleep(delay)

    async def _writer(self, c):
        while True:
            data = await c.queue.get()
            await c.ws.send(data)

    async def handler(self, ws, path=None):
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(path or _path(ws)).query)
        encoding = q.get("encoding", ["json"])[0]
        view_key = q.get("view_key", [None])[0]
        if encoding not in codec.ENCODINGS:
            await ws.send(json.dumps({"type": "error",
                                      "message": "unknown encoding %r" % encoding}))
            return
        c = Client(ws, encoding, view_key, self)
        self.clients.add(c)
        log.info("client %s connected (encoding=%s view_key=%s), %d clients",
                 c.peer, encoding, view_key, len(self.clients))
        c.send_msg(self.layer.hello())
        c.send_msg(self.layer.snapshot(view_key, self.keepalive))
        writer = asyncio.ensure_future(self._writer(c))
        try:
            async for raw in ws:
                try:
                    msg = c.dec(raw)
                    if not isinstance(msg, dict):
                        raise ValueError("message is not an object")
                except Exception as e:
                    c.send_msg({"type": "error", "message": "undecodable message: %s" % e})
                    continue
                self._dispatch(c, msg, len(raw))
        except Exception as e:      # connection closed / reset
            log.info("client %s: %s", c.peer, type(e).__name__)
        finally:
            writer.cancel()
            self.clients.discard(c)
            log.info("client %s gone, %d clients", c.peer, len(self.clients))

    def _dispatch(self, c, msg, size):
        if self.validator is not None:
            err = self.validator(msg)
            if err:
                log.warning("invalid message from %s: %s", c.peer, err)
                c.send_msg({"type": "error", "message": "invalid message: %s" % err,
                            "in_reply_to": msg.get("id")})
                return
        t = msg.get("type")
        if t == "resync_request":
            c.send_msg(self.layer.snapshot(c.view_key, self.keepalive))
        elif t == "command":
            res = self.layer.submit(c.send_msg, msg)
            if res is not None:
                c.send_msg(res)
        elif t == "view_state_put":
            key, blob = msg.get("key"), msg.get("blob")
            try:
                self.layer.view_put(key, blob, size)
            except CommandError as e:
                c.send_msg({"type": "error", "message": str(e)})
                return
            c.view_key = key
            out = {"type": "view_state", "key": key, "blob": blob}
            for o in list(self.clients):
                if o is not c and o.view_key == key:
                    o.send_msg(out)
        else:
            c.send_msg({"type": "error", "message": "unknown message type %r" % (t,)})

    async def run(self):
        import websockets
        kw = dict(compression=self.compression, ping_interval=self.ping_interval,
                  ping_timeout=self.ping_timeout, max_size=1 << 20, close_timeout=2)
        async with websockets.serve(self.handler, self.host, self.port, **kw):
            log.info("listening on ws://%s:%d/ period=%.3f s commands=%s epoch=%s",
                     self.host, self.port, self.period, self.layer.allow_commands,
                     self.layer.epoch)
            worker = asyncio.ensure_future(self.layer.command_worker())
            try:
                await self._ticker()
            finally:
                worker.cancel()
