#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""SL-1 smoke test: drive a running LinuxCNC through the stock Python module.

ESTOP_RESET -> ON -> home all joints -> AUTO -> program_open -> AUTO_RUN,
then wait until the interpreter is idle again.  Uses only linuxcnc.stat /
linuxcnc.command / linuxcnc.error_channel, the same calls a GUI makes.

usage: smoke_run.py PROGRAM.ngc [PROGRAM2.ngc ...]
"""
import sys
import time

import linuxcnc

s = linuxcnc.stat()
c = linuxcnc.command()
e = linuxcnc.error_channel()

INTERP = {linuxcnc.INTERP_IDLE: "IDLE", linuxcnc.INTERP_READING: "READING",
          linuxcnc.INTERP_PAUSED: "PAUSED", linuxcnc.INTERP_WAITING: "WAITING"}


def log(*a):
    print("%.3f" % time.monotonic(), *a, flush=True)


def drain_errors():
    while True:
        err = e.poll()
        if not err:
            return
        log("error_channel:", err)


def wait(pred, timeout, what):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        s.poll()
        drain_errors()
        if pred():
            log("ok:", what, "after %.2f s" % (time.monotonic() - t0))
            return True
        time.sleep(0.05)
    log("TIMEOUT:", what)
    return False


def cmd(name, *args):
    rv = getattr(c, name)(*args)
    done = c.wait_complete(10.0)
    log("command %s%r -> wait_complete=%r" % (name, args, done))
    return done


def main(programs):
    s.poll()
    log("connected: ini=%s joints=%d task_state=%d" % (s.ini_filename, s.joints, s.task_state))
    cmd("state", linuxcnc.STATE_ESTOP_RESET)
    cmd("state", linuxcnc.STATE_ON)
    wait(lambda: s.task_state == linuxcnc.STATE_ON, 5, "task_state == STATE_ON")
    cmd("mode", linuxcnc.MODE_MANUAL)
    cmd("home", -1)
    if not wait(lambda: all(s.homed[j] for j in range(s.joints)), 60, "all joints homed"):
        return 1
    cmd("set_optional_stop", False)
    rc = 0
    for prog in programs:
        cmd("mode", linuxcnc.MODE_AUTO)
        cmd("program_open", prog)
        s.poll()
        log("loaded file=%s" % s.file)
        t0 = time.monotonic()
        cmd("auto", linuxcnc.AUTO_RUN, 0)
        wait(lambda: s.interp_state != linuxcnc.INTERP_IDLE, 5, "program started")
        last = None
        while True:
            s.poll()
            drain_errors()
            cur = (INTERP.get(s.interp_state), s.exec_state, s.motion_line)
            if cur[:2] != (last or (None, None, None))[:2]:
                log("interp_state=%s exec_state=%d motion_line=%d" % cur)
            last = cur
            if s.interp_state == linuxcnc.INTERP_IDLE:
                break
            if time.monotonic() - t0 > 1800:
                log("TIMEOUT: program did not finish")
                rc = 1
                break
            time.sleep(0.1)
        log("program %s finished in %.1f s, motion_line=%d, position=%s" % (
            prog, time.monotonic() - t0, s.motion_line, s.position[:3]))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
