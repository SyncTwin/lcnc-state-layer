#!/usr/bin/env python3
# Bench load: run axis.ngc in a loop through the stock linuxcnc module until STOP file appears.
import linuxcnc, os, sys, time
ngc, stop = sys.argv[1], sys.argv[2]
s, c = linuxcnc.stat(), linuxcnc.command()
def wait(pred, t=30):
    t0 = time.time()
    while time.time() - t0 < t:
        s.poll()
        if pred(): return True
        time.sleep(0.05)
    raise SystemExit("timeout")
c.state(linuxcnc.STATE_ESTOP_RESET); c.state(linuxcnc.STATE_ON); wait(lambda: s.task_state == linuxcnc.STATE_ON)
c.mode(linuxcnc.MODE_MANUAL); c.wait_complete(); c.home(-1); wait(lambda: all(s.homed[:3]), 60)
c.mode(linuxcnc.MODE_AUTO); c.wait_complete(); c.program_open(ngc); c.wait_complete()
n = 0
while not os.path.exists(stop):
    c.auto(linuxcnc.AUTO_RUN, 0); wait(lambda: s.interp_state != linuxcnc.INTERP_IDLE, 10)
    wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE, 600); n += 1
    print("run", n, "done", flush=True)
