#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Helpers that act as OTHER NML clients next to the sidecar (like AXIS or halui).

  foreign_nml.py writer SECONDS   send set_block_delete() in a loop (a second
                                  command writer), then demonstrate the
                                  emcmodule wait_complete() mine once
  foreign_nml.py reader SECONDS [INTERVAL]
                                  poll error_channel every INTERVAL s (0.2 like
                                  AXIS error_task, axis.py:794)
                                  (a second error reader) and print what it got
"""
import sys
import time

import linuxcnc


def writer(seconds):
    c = linuxcnc.command()
    t0 = time.monotonic()
    n = 0
    while time.monotonic() - t0 < seconds:
        c.set_block_delete(n % 2 == 0)
        n += 1
        time.sleep(0.002)
    print("writer: sent %d commands in %.1f s" % (n, seconds), flush=True)
    # The mine (emcmodule.cc emcWaitCommandComplete): echo_serial_number past
    # our serial counts as RCS_DONE even if our command failed.
    s = linuxcnc.stat()
    c1, c2 = linuxcnc.command(), linuxcnc.command()
    s.poll()
    c1.mdi("G0 X1")                 # in MODE_MANUAL task rejects it: RCS_ERROR
    c2.set_block_delete(True)       # another client's command right after
    r = c1.wait_complete(2.0)
    s.poll()
    print("writer: mine demo: task_mode=%d, c1.mdi() serial=%d, c2 serial=%d, echo=%d, "
          "c1.wait_complete() -> %d (RCS_DONE=%d, RCS_ERROR=%d)"
          % (s.task_mode, c1.serial, c2.serial, s.echo_serial_number, r,
             linuxcnc.RCS_DONE, linuxcnc.RCS_ERROR), flush=True)


def reader(seconds, interval=0.2):
    e = linuxcnc.error_channel()
    t0 = time.monotonic()
    got = []
    while time.monotonic() - t0 < seconds:
        m = e.poll()
        while m:
            got.append(m)
            print("reader: %r" % (m,), flush=True)
            m = e.poll()
        time.sleep(interval)
    print("reader: got %d error_channel entries" % len(got), flush=True)


if __name__ == "__main__":
    {"writer": writer, "reader": reader}[sys.argv[1]](*map(float, sys.argv[2:]))
