#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Outcome and tracking checks against a running LinuxCNC sim.

    1  command sender killed while task has not echoed the command yet
       (milltask stopped) -> unknown; task executes it after SIGCONT
    2  no echo within EMC_COMMAND_TIMEOUT (milltask stopped, sender alive)
       -> unknown; task executes it after SIGCONT
    3  two programs started by another NML client while no websocket client
       is connected -> program_end.seq == 2 for the first client
    4  --no-error-channel: the error stays for the other error_channel reader
    5  abort while the command queue is busy: time to abort result and to
       interp_state IDLE

Each case starts its own sidecar (--sidecar, default this tree).  Run as the
LinuxCNC user next to a running sim; it stops and continues milltask (sim
only, never on a machine with servos).
"""
import argparse
import asyncio
import os
import re
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "clients", "python"))
from lcnc_state_client import StateClient   # noqa: E402
import linuxcnc                                # noqa: E402

RAW = linuxcnc.stat()
FAILS = []


def say(case, what, got, ok):
    print("%s %-3s %-58s %s" % ("OK " if ok else "BAD", case, what, got), flush=True)
    if not ok:
        FAILS.append((case, what))


def pid_of(name):
    return int(subprocess.check_output(["pgrep", "-n", "-x", name]).split()[0])


class Sidecar:
    def __init__(self, tree, port, *extra):
        self.log = "/tmp/outcome_sidecar_%d.log" % port
        self.p = subprocess.Popen([sys.executable, os.path.join(tree, "sidecar",
                                                                "linuxcnc-state-layer"),
                                   "--port", str(port)] + list(extra),
                                  stdout=open(self.log, "w"), stderr=subprocess.STDOUT)
        self.url = "ws://127.0.0.1:%d/" % port
        time.sleep(2)

    def sender_pid(self):
        m = re.search(r"command sender pid (\d+)", open(self.log).read())
        return int(m.group(1)) if m else None

    def stop(self):
        self.p.send_signal(signal.SIGINT)
        self.p.wait(10)


async def connect(url):
    c = StateClient(url)
    c.task = asyncio.ensure_future(c.run())
    await asyncio.wait_for(c.ready.wait(), 10)
    return c


async def until(pred, timeout, step=0.005):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if pred():
            return time.monotonic() - t0
        await asyncio.sleep(step)
    return None


def raw_wait(pred, timeout):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        RAW.poll()
        if pred(RAW):
            return True
        time.sleep(0.02)
    return False


def machine_on_homed(cmd):
    cmd.state(linuxcnc.STATE_ESTOP_RESET); cmd.wait_complete()
    cmd.state(linuxcnc.STATE_ON); cmd.wait_complete()
    RAW.poll()
    if not all(RAW.joint[j]["homed"] for j in range(RAW.joints)):
        cmd.mode(linuxcnc.MODE_MANUAL); cmd.wait_complete()
        cmd.teleop_enable(0); cmd.wait_complete()
        cmd.home(-1); cmd.wait_complete()
        raw_wait(lambda s: all(s.joint[j]["homed"] for j in range(s.joints)), 30)


async def stopped_task_case(a, case, kill):
    sc = Sidecar(a.sidecar, a.port, "--allow-commands")
    try:
        c = await connect(sc.url)
        b = c.state["stat"]["block_delete"]
        task = pid_of("milltask")
        os.kill(task, signal.SIGSTOP)
        t0 = time.monotonic()
        try:
            fut = asyncio.ensure_future(c.command("set_block_delete", int(not b), timeout=20))
            if kill:
                await asyncio.sleep(0.5)        # sender is inside emcSendCommand now
                os.kill(sc.sender_pid(), signal.SIGKILL)
                r = await fut
            else:
                r = await asyncio.wait_for(asyncio.shield(fut), 15)
        finally:
            os.kill(task, signal.SIGCONT)
        dt = time.monotonic() - t0
        say(case, "set_block_delete with task stopped%s: outcome" %
            (", sender killed" if kill else ""), "%s in %.2f s (%s)" % (
                r["outcome"], dt, r.get("error", "")), r["outcome"] == "unknown")
        late = await until(lambda: c.state["stat"]["block_delete"] == (not b), 3)
        say(case, "executed by task after SIGCONT", "after %.2f s" % late
            if late is not None else "no", late is not None)
        r2 = await c.command("set_block_delete", int(b), timeout=10)
        say(case, "next command (sender restarted if killed)", r2["outcome"],
            r2["outcome"] == "completed")
        c.task.cancel()
    finally:
        sc.stop()


async def case3(a, cmd, ngc):
    sc = Sidecar(a.sidecar, a.port)
    try:
        for _ in range(2):
            cmd.mode(linuxcnc.MODE_AUTO); cmd.wait_complete()
            cmd.program_open(ngc); cmd.wait_complete()
            cmd.auto(linuxcnc.AUTO_RUN, 0)
            raw_wait(lambda s: s.interp_state != linuxcnc.INTERP_IDLE, 5)
            raw_wait(lambda s: s.interp_state == linuxcnc.INTERP_IDLE, 30)
            time.sleep(0.3)
        c = await connect(sc.url)
        pe = c.state.get("program_end") or {}
        say("3", "two runs by another client, no ws client: program_end",
            "seq=%s reason=%s" % (pe.get("seq"), pe.get("reason")),
            pe.get("seq") == 2 and pe.get("reason") == "completed")
        c.task.cancel()
    finally:
        sc.stop()


async def case4(a, cmd, flag):
    sc = Sidecar(a.sidecar, a.port, *([flag] if flag else []))
    try:
        c = await connect(sc.url)
        e0 = c.state["errors"]["seq"]
        ech = linuxcnc.error_channel()
        while ech.poll():
            pass
        cmd.mode(linuxcnc.MODE_MDI); cmd.wait_complete()
        cmd.mdi("G1 X1 F0"); cmd.wait_complete()
        time.sleep(0.5)                     # several sidecar ticks
        mine = []
        while True:
            e = ech.poll()
            if not e:
                break
            mine.append(e[1])
        await asyncio.sleep(0.2)
        got = c.state["errors"]["seq"] - e0
        srv = c.server.get("error_channel")
        label = flag or "default"
        if flag:
            say("4", "%s: sidecar errors / other reader" % label,
                "%d / %d (server.error_channel=%s)" % (got, len(mine), srv),
                got == 0 and len(mine) >= 1)
        else:
            say("4", "%s: sidecar errors / other reader" % label,
                "%d / %d" % (got, len(mine)), got >= 1)
        cmd.mode(linuxcnc.MODE_MANUAL); cmd.wait_complete()
        c.task.cancel()
    finally:
        sc.stop()


async def case5(a, ngc):
    sc = Sidecar(a.sidecar, a.port, "--allow-commands")
    try:
        c = await connect(sc.url)
        A = await connect(sc.url)
        run = asyncio.ensure_future(A.command("run", {"file": ngc}, timeout=60))
        busy = await until(lambda: c.state["stat"]["interp_state"] != linuxcnc.INTERP_IDLE, 10)
        say("5", "program running", "after %.2f s" % busy if busy else "no", busy is not None)
        # commands that occupy the queue: each one waits EFFECT_TIMEOUT for an
        # effect stat never shows (task clamps a negative max velocity to 0)
        vmax = c.state["stat"]["max_velocity"]
        blockers = [asyncio.ensure_future(A.command("maxvel", -1.0, timeout=60))
                    for _ in range(a.blockers)]
        await asyncio.sleep(0.3)
        t0 = time.monotonic()
        ab = asyncio.ensure_future(c.command("abort", timeout=60))
        idle = await until(lambda: c.state["stat"]["interp_state"] == linuxcnc.INTERP_IDLE, 30)
        r = await ab
        t_res = time.monotonic() - t0
        say("5", "abort behind %d queued commands: interp IDLE after" % a.blockers,
            "%.3f s" % idle if idle is not None else "never", idle is not None and idle < 1.0)
        say("5", "abort result", "%s after %.3f s" % (r["outcome"], t_res),
            r["outcome"] == "completed")
        rr = await run
        say("5", "run result (aborted by fact)", rr["outcome"], rr["outcome"] == "aborted")
        outs = [(await b)["outcome"] for b in blockers]
        say("5", "queued blockers", ",".join(outs), True)
        pe = c.state.get("program_end") or {}
        say("5", "program_end.reason", pe.get("reason"), pe.get("reason") == "aborted")
        cmd = linuxcnc.command()
        cmd.maxvel(vmax); cmd.wait_complete()
        c.task.cancel(); A.task.cancel()
    finally:
        sc.stop()


async def main(a):
    cmd = linuxcnc.command()
    ngc_short = "/tmp/outcome_short.ngc"
    ngc_long = "/tmp/outcome_long.ngc"
    open(ngc_short, "w").write("G21 G90\nG4 P0.3\nM2\n")
    open(ngc_long, "w").write("G21 G90\nG4 P20\nM2\n")
    machine_on_homed(cmd)
    want = set(a.cases.split(","))
    if "1" in want:
        await stopped_task_case(a, "1", kill=True)
    if "2" in want:
        await stopped_task_case(a, "2", kill=False)
    if "3" in want:
        await case3(a, cmd, ngc_short)
    if "4" in want:
        await case4(a, cmd, "--no-error-channel")
        await case4(a, cmd, None)
    if "5" in want:
        machine_on_homed(cmd)
        await case5(a, ngc_long)
    print("failed:", len(FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sidecar", default=ROOT, help="tree holding sidecar/ (default: this one)")
    ap.add_argument("--port", type=int, default=8796)
    ap.add_argument("--cases", default="1,2,3,4,5")
    ap.add_argument("--blockers", type=int, default=3)
    sys.exit(asyncio.run(main(ap.parse_args())))
