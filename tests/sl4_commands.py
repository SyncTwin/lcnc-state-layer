#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""SL-4 live scenario: commands and outcomes per client, errors to all,
program_end reasons, view state, read-only default.

Runs against a sidecar started with --allow-commands (URL), next to a running
LinuxCNC sim.  Needs the linuxcnc module (foreign NML client helpers), i.e.
run as the LinuxCNC user with rip-environment.  Writes a Markdown result
table to --report and exits non-zero if any check fails.
"""
import argparse
import asyncio
import logging
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "clients", "python"))
from lcnc_state_client import StateClient   # noqa: E402
import linuxcnc                                # noqa: E402
RAW = linuxcnc.stat()

log = logging.getLogger("sl4")
ROWS = []


def check(case, who, what, got, expect, ok=None, note=""):
    if ok is None:
        ok = got in expect if isinstance(expect, (tuple, list, set)) else got == expect
    ROWS.append((case, who, what, str(got), str(expect), "✅" if ok else "❌", note))
    log.info("%s %s | %s | %s -> %s (expect %s) %s", "OK " if ok else "BAD", case, who, what,
             got, expect, note)
    return ok


async def connect(url, key=None):
    c = StateClient(url, view_key=key)
    c.task = asyncio.ensure_future(c.run())
    await asyncio.wait_for(c.ready.wait(), 10)
    return c


async def until(c, pred, timeout):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if pred(c.state):
            return True
        await asyncio.sleep(0.05)
    return False


def err_texts(c, since):
    return [e["text"] for e in c.state["errors"]["recent"] if e["seq"] > since]


async def main(a):
    url = a.url
    A = await connect(url, "A")
    B = await connect(url, "B")
    st = lambda: A.state["stat"]

    # 0. machine on, homed (setup, not a check unless it fails)
    for name, args in (("state", ["STATE_ESTOP_RESET"]), ("state", ["STATE_ON"]),
                       ("mode", ["MODE_MANUAL"])):
        r = await A.command(name, *args, timeout=10)
        if r["outcome"] != "completed":
            check("0 setup", "A", "%s%r" % (name, args), r["outcome"], "completed")
    if not all(st()["homed"][:st()["joints"]]):
        r = await A.command("home", -1, timeout=120)
        check("0 setup", "A", "home(-1) on unhomed machine", r["outcome"], "completed",
              note="completed only when stat shows all joints homed")
    await until(A, lambda s: s["stat"]["motion_mode"] == 3, 5)   # TRAJ_MODE_TELEOP after homing

    # 1. unknown command / bad argument -> failed, only to the sender
    r = await A.command("fly", timeout=5)
    check("1 invalid", "A", "fly()", r["outcome"], "failed", note=r.get("error", ""))
    r = await B.command("mode", "MODE_BOGUS", timeout=5)
    check("1 invalid", "B", "mode('MODE_BOGUS')", r["outcome"], "failed", note=r.get("error", ""))
    r = await B.command("mdi", timeout=5)
    check("1 invalid", "B", "mdi() without argument", r["outcome"], "failed", note=r.get("error", ""))

    # 2. command in the wrong state -> failed for the sender, error visible to both
    e0 = A.state["errors"]["seq"]
    r = await B.command("unhome", 0, timeout=10)
    check("2 wrong state", "B", "unhome(0) in teleop mode", r["outcome"], "failed",
          note=r.get("error", ""))
    await asyncio.sleep(0.3)
    ta, tb = err_texts(A, e0), err_texts(B, e0)
    check("2 wrong state", "A+B", "error entry seen by both clients", "%d/%d" % (len(ta), len(tb)),
          "both ≥1", ok=bool(ta) and ta == tb, note="; ".join(ta))
    r = await A.command("mdi", "G0 X10", timeout=10)
    check("2 wrong state", "A", "mdi('G0 X10') in MODE_MANUAL", r["outcome"], "failed",
          note=r.get("error", ""))

    # 3. both clients send quick commands at the same time -> each gets its own results
    async def burst(c, tag, n):
        out = []
        for i in range(n):
            r = await c.command("set_block_delete", i % 2 == 0, timeout=10)
            out.append(r)
        return out
    ra, rb = await asyncio.gather(burst(A, "A", 10), burst(B, "B", 10))
    ida = {r["id"] for r in ra}
    idb = {r["id"] for r in rb}
    oa, ob = sorted({r["outcome"] for r in ra}), sorted({r["outcome"] for r in rb})
    check("3 concurrent", "A", "10× set_block_delete", oa, ["completed"],
          ok=oa == ["completed"] and len(ida) == 10,
          note="own ids only: %s" % (len(ida) == 10 and not (ida & idb)))
    check("3 concurrent", "B", "10× set_block_delete", ob, ["completed"],
          ok=ob == ["completed"] and len(idb) == 10,
          note="interleaved with A's in one sidecar queue")

    # 4. MDI: completed means the motion finished (emctaskmain.cc:3720-3729)
    r = await A.command("mode", "MODE_MDI", timeout=10)
    t0 = time.monotonic()
    r = await A.command("mdi", "G90 G0 X20 Y15", timeout=60)
    RAW.poll()                       # raw NML status right at the result
    raw = dict(vel=RAW.current_vel, dtg=RAW.distance_to_go, inpos=RAW.inpos,
               interp=RAW.interp_state, g5x=[round(x, 3) for x in RAW.g5x_offset[:2]],
               pos=[round(x, 3) for x in RAW.position[:2]])
    check("4 mdi", "A", "mdi('G90 G0 X20 Y15')", r["outcome"], "completed",
          note="after %.2f s" % (time.monotonic() - t0))
    check("4 mdi", "raw stat", "machine stopped at the moment of completed",
          "vel=%g dtg=%g inpos=%s interp=%d" % (raw["vel"], raw["dtg"], raw["inpos"], raw["interp"]),
          "vel=0 dtg=0 inpos interp=IDLE",
          ok=raw["vel"] == 0 and raw["dtg"] == 0 and raw["inpos"] and raw["interp"] == 1,
          note="position %s = 20,15 + g5x_offset %s" % (raw["pos"], raw["g5x"]))

    # 5. abort during a program run: run -> aborted (A), abort -> completed (B)
    run = asyncio.ensure_future(A.command("run", {"file": a.long_program}, timeout=600))
    await until(A, lambda s: s["stat"]["interp_state"] != 1 and s["stat"]["task_mode"] == 2, 10)
    await asyncio.sleep(3)
    pe0 = (A.state.get("program_end") or {}).get("seq", 0)
    rb = await B.command("abort", timeout=10)
    ra = await run
    check("5 abort", "B", "abort() during run", rb["outcome"], "completed")
    check("5 abort", "A", "run(%s) aborted by B" % os.path.basename(a.long_program),
          ra["outcome"], "aborted")
    await until(A, lambda s: (s.get("program_end") or {}).get("seq", 0) > pe0, 5)
    check("5 abort", "A", "program_end.reason", (A.state.get("program_end") or {}).get("reason"),
          "aborted")

    # 6. program runs to M2 -> completed
    ra = await A.command("run", {"file": a.short_program}, timeout=600)
    check("6 completed", "A", "run(%s)" % os.path.basename(a.short_program), ra["outcome"],
          "completed")
    await asyncio.sleep(0.3)
    check("6 completed", "B", "program_end.reason seen by B",
          (B.state.get("program_end") or {}).get("reason"), "completed")

    # 7. program stops with an error -> failed / program_end error
    e0 = A.state["errors"]["seq"]
    ra = await A.command("run", {"file": a.error_program}, timeout=120)
    check("7 error", "A", "run(%s)" % os.path.basename(a.error_program), ra["outcome"], "failed",
          note=ra.get("error", ""))
    await asyncio.sleep(0.3)
    check("7 error", "B", "program_end.reason seen by B",
          (B.state.get("program_end") or {}).get("reason"), "error",
          note="; ".join(err_texts(B, e0)))

    # 8. expect_file: run refuses a different loaded program
    ra = await A.command("run", {"expect_file": "/nonexistent/other.ngc"}, timeout=30)
    check("8 expect_file", "A", "run(expect_file=other)", ra["outcome"], "failed",
          note=ra.get("error", ""))

    # back to manual/teleop for the next cases
    await A.command("mode", "MODE_MANUAL", timeout=10)
    await until(A, lambda s: s["stat"]["motion_mode"] == 3, 5)

    # 9. another NML command writer next to the sidecar (AXIS/halui): a failing
    #    command must never be reported completed
    w = subprocess.Popen([sys.executable, os.path.join(HERE, "foreign_nml.py"), "writer", "6"],
                         stdout=subprocess.PIPE, text=True)
    await asyncio.sleep(0.3)
    outs = []
    t0 = time.monotonic()
    while time.monotonic() - t0 < 5:
        r = await B.command("program_open", "/nonexistent/sl4.ngc", timeout=10)
        outs.append(r["outcome"])
    wout = w.communicate(timeout=30)[0]
    log.info("foreign writer output:\n%s", wout)
    counts = {k: outs.count(k) for k in sorted(set(outs))}
    check("9 foreign writer", "B", "%d× program_open(nonexistent) while another client writes"
          % len(outs), counts, "no completed", ok="completed" not in counts,
          note="accepted = echo moved past our serial before its status was seen")
    mine = [l for l in wout.splitlines() if "mine demo" in l]
    check("9 foreign writer", "raw emcmodule", "c1.mdi() in MANUAL (fails), c2 command, c1.wait_complete()",
          mine[0].split("->")[1].split("(")[0].strip() if mine else "?", "1 (=RCS_DONE: the mine)",
          ok=bool(mine) and "-> 1 " in mine[0], note=mine[0] if mine else "")

    # 10. a second error_channel reader (like AXIS) takes errors from the sidecar
    for interval in ("0.2", "0.005"):
        rd = subprocess.Popen([sys.executable, os.path.join(HERE, "foreign_nml.py"), "reader",
                               "6", interval], stdout=subprocess.PIPE, text=True)
        await asyncio.sleep(0.5)
        e0 = A.state["errors"]["seq"]
        n = 20
        for i in range(n):
            await B.command("program_open", "/nonexistent/sl4_%d.ngc" % i, timeout=10)
            await asyncio.sleep(0.15)
        rout = rd.communicate(timeout=30)[0]
        got_reader = sum(1 for l in rout.splitlines() if l.startswith("reader: ("))
        await asyncio.sleep(0.3)
        got_sidecar = A.state["errors"]["seq"] - e0
        check("10 second reader", "sidecar vs reader",
              "%d failing program_open, other reader polls every %s s" % (n, interval),
              "sidecar %d, other reader %d" % (got_sidecar, got_reader), "sum = all errors",
              ok=got_sidecar + got_reader >= n,
              note="error_channel is a single-consumer queue (cms_in.cc:817-828): "
                   "an entry goes to whichever reader polls first")

    # 11. view state per client key
    await A.view_state_put({"tab": "auto", "zoom": 1.5})
    await B.view_state_put({"tab": "mdi", "dro": "machine"})
    A2 = await connect(url, "A")
    check("11 view state", "A2 (key A)", "snapshot.view_state on connect", A2.view_state,
          {"tab": "auto", "zoom": 1.5})
    await A.view_state_put({"tab": "auto", "zoom": 2.0})
    await asyncio.sleep(0.3)
    check("11 view state", "A2 (key A)", "view_state pushed when A changes it", A2.view_state,
          {"tab": "auto", "zoom": 2.0})
    for c in (A, B, A2):
        c.task.cancel()
    await asyncio.sleep(0.2)
    A3 = await connect(url, "A")
    B3 = await connect(url, "B")
    check("11 view state", "A (reconnect)", "own blob back", A3.view_state, {"tab": "auto", "zoom": 2.0})
    check("11 view state", "B (reconnect)", "own blob back", B3.view_state,
          {"tab": "mdi", "dro": "machine"})
    big = "x" * (70 * 1024)
    await B3.view_state_put(big)
    await asyncio.sleep(0.3)
    B4 = await connect(url, "B")
    check("11 view state", "B", "70 KiB blob refused, old blob kept", B4.view_state,
          {"tab": "mdi", "dro": "machine"}, note="limit 64 KiB (ASSUMPTION, not measured)")

    # 12. read-only default.  Started only now: a second sidecar is a second
    #     error_channel reader and would take errors from the first one.
    if a.readonly_port:
        ro = subprocess.Popen([sys.executable, os.path.join(ROOT, "sidecar", "linuxcnc-state-layer"),
                               "--port", str(a.readonly_port)],
                              stdout=open(os.path.join(ROOT, "logs", "sl4_sidecar_readonly.log"), "w"),
                              stderr=subprocess.STDOUT)
        await asyncio.sleep(2)
        R = await connect("ws://127.0.0.1:%d/" % a.readonly_port)
        r = await R.command("state", "STATE_ESTOP", timeout=5)
        check("12 read-only", "R", "command to a sidecar without --allow-commands", r["outcome"],
              "failed", note=r.get("error", ""))
        R.task.cancel()
        ro.terminate()
        try:
            ro.wait(15)
        except subprocess.TimeoutExpired:
            ro.kill()
            log.warning("read-only sidecar did not stop on SIGTERM within 15 s")
    for c in (A3, B3, B4):
        c.task.cancel()

    bad = [r for r in ROWS if r[5] != "✅"]
    with open(a.report, "w") as f:
        f.write("| case | client | action | got | expected | ok | note |\n|---|---|---|---|---|---|---|\n")
        for r in ROWS:
            f.write("| %s |\n" % " | ".join(x.replace("|", "\\|").replace("\n", " ") for x in r))
        f.write("\n%d checks, %d failed\n" % (len(ROWS), len(bad)))
    log.info("%d checks, %d failed", len(ROWS), len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    # EMC2_HOME is set by scripts/rip-environment; /tmp/linuxcnc is the README clone path
    lcnc = os.environ.get("EMC2_HOME", "/tmp/linuxcnc")
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8791/")
    ap.add_argument("--readonly-port", type=int)
    ap.add_argument("--long-program", default=os.path.join(lcnc, "share", "axis", "images", "axis.ngc"))
    ap.add_argument("--short-program",
                    default=os.path.join(lcnc, "nc_files", "gmoccapy_2_tools_with_cutter_radius_compensation.ngc"))
    ap.add_argument("--error-program", default=os.path.join(ROOT, "sim", "error_test.ngc"))
    ap.add_argument("--report", default=os.path.join(ROOT, "logs", "sl4_results.md"))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    sys.exit(asyncio.run(main(ap.parse_args())))
