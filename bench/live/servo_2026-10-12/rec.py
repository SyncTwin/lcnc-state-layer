#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Recorder for the live-servo run of lcnc-state-layer (manual experiment on a test bench, 2026-10-12).

Connects to the sidecar websocket, writes every received frame (raw text + recv time) to a
jsonl.gz, keeps the reconstructed state, optionally runs a command script through the
sidecar (timing each command_result), samples HAL encoder pins with halcmd and pairs them
with the stream position. Safety: a finally-block sends STATE_OFF + STATE_ESTOP straight
through linuxcnc.command (independent of the sidecar).
"""
import argparse, asyncio, gzip, json, subprocess, sys, time

sys.path.insert(0, "vendor")
import websockets  # noqa: E402


def merge(t, p):
    if not isinstance(p, dict):
        return p
    if not isinstance(t, dict):
        t = {}
    for k, v in p.items():
        if v is None:
            t.pop(k, None)
        else:
            t[k] = merge(t.get(k), v)
    return t


def halget(pin):
    r = subprocess.run(["halcmd", "-s", "getp", pin], capture_output=True, text=True, timeout=3)
    return r.stdout.strip()


async def main(a):
    out = gzip.open(a.out, "wt")
    state, seq, gaps = None, None, 0
    samples, results = [], []
    async with websockets.connect(a.url, max_size=None) as ws:
        async def reader():
            nonlocal state, seq, gaps
            async for raw in ws:
                t = time.monotonic()
                m = json.loads(raw)
                out.write(json.dumps({"t": t, "raw": raw}) + "\n")
                if m["type"] == "snapshot":
                    state, seq = m["state"], m["seq"]
                elif m["type"] == "patch":
                    if seq is not None and m["seq"] != seq + 1:
                        gaps += 1
                    state = merge(state, m["patch"]); seq = m["seq"]
                elif m["type"] == "command_result":
                    w = waiters.pop(m.get("id"), None)
                    if w:
                        w.set_result((t, m))
        waiters = {}
        rt = asyncio.ensure_future(reader())

        async def cmd(name, *args, timeout=30):
            cid = "c%d" % (len(results) + 1)
            fut = asyncio.get_running_loop().create_future()
            waiters[cid] = fut
            t0 = time.monotonic()
            await ws.send(json.dumps({"type": "command", "id": cid, "name": name, "args": list(args)}))
            t1, m = await asyncio.wait_for(fut, timeout)
            r = {"name": name, "args": args, "outcome": m.get("outcome"), "error": m.get("error"),
                 "ms": round((t1 - t0) * 1000, 1)}
            results.append(r)
            print("CMD", json.dumps(r), flush=True)
            return r

        def sample(tag):
            enc = halget("lcec.0.x.srv-actual-position")
            fb = halget("joint.0.motor-pos-fb")
            st = (state or {}).get("stat", {})
            s = {"tag": tag, "t": time.monotonic(), "seq": seq, "hal_enc_counts": enc, "hal_motor_pos_fb": fb,
                 "stream_joint0": (st.get("joint_actual_position") or [None])[0],
                 "stream_actual_x": (st.get("actual_position") or [None])[0]}
            samples.append(s)
            print("SAMPLE", json.dumps(s), flush=True)

        try:
            await asyncio.sleep(1.0)
            if a.script == "idle":
                for i in range(a.idle_samples):
                    sample("idle%d" % i)
                    await asyncio.sleep(a.duration / a.idle_samples)
            elif a.script == "jog":
                sample("before")
                await cmd("state", "STATE_ESTOP_RESET")
                await cmd("state", "STATE_ON")
                await cmd("mode", "MODE_MANUAL")
                # joint jog, incremental: jog(JOG_INCREMENT, jjogmode=True, joint 0, vel mm/s, incr mm)
                r = await cmd("jog", "JOG_INCREMENT", True, 0, a.vel, a.incr)
                for i in range(6):
                    await asyncio.sleep(a.incr / a.vel / 5)
                    sample("fwd%d" % i)
                await asyncio.sleep(0.8)
                sample("fwd_end")
                await cmd("jog", "JOG_INCREMENT", True, 0, a.vel, -a.incr)
                await asyncio.sleep(a.incr / a.vel + 0.8)
                sample("back_end")
                await cmd("state", "STATE_OFF")
                await cmd("state", "STATE_ESTOP")
                await asyncio.sleep(1.0)
                sample("after_off")
            elif a.script == "quick":
                for i in range(a.idle_samples):
                    await cmd("set_block_delete", i % 2 == 0)
        finally:
            if a.script == "jog":
                import linuxcnc
                c = linuxcnc.command()
                c.state(linuxcnc.STATE_OFF); c.state(linuxcnc.STATE_ESTOP)
                print("SAFETY state OFF+ESTOP sent directly", flush=True)
            await asyncio.sleep(0.5)
            rt.cancel()
    out.close()
    json.dump({"samples": samples, "results": results, "gaps": gaps, "last_seq": seq},
              open(a.out.replace(".jsonl.gz", ".summary.json"), "w"), indent=1)
    print("DONE gaps=%d last_seq=%s" % (gaps, seq))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8791/")
    ap.add_argument("--out", required=True)
    ap.add_argument("--script", choices=("idle", "jog", "quick"), default="idle")
    ap.add_argument("--duration", type=float, default=30)
    ap.add_argument("--idle-samples", type=int, default=5)
    ap.add_argument("--vel", type=float, default=5.0)
    ap.add_argument("--incr", type=float, default=2.0)
    asyncio.run(main(ap.parse_args()))
