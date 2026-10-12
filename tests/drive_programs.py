#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Drive LinuxCNC through the state layer only: ESTOP_RESET, ON, home all,
then run each program with the `run` command and wait for its command_result.

usage: drive_programs.py [--url ws://127.0.0.1:8791/] PROGRAM.ngc ...
"""
import argparse
import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "clients", "python"))
from lcnc_state_client import StateClient   # noqa: E402

log = logging.getLogger("drive")


async def wait_for(c, pred, timeout, what):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if pred(c.state["stat"]):
            log.info("ok: %s (%.2f s)", what, time.monotonic() - t0)
            return True
        await asyncio.sleep(0.05)
    log.error("TIMEOUT: %s", what)
    return False


async def main(args):
    c = StateClient(args.url, verify_every=args.verify_every)
    task = asyncio.ensure_future(c.run())
    await asyncio.wait_for(c.ready.wait(), 10)
    rc = 0
    for name, a in (("state", ["STATE_ESTOP_RESET"]), ("state", ["STATE_ON"]),
                    ("mode", ["MODE_MANUAL"]), ("home", [-1])):
        r = await c.command(name, *a, timeout=10)
        log.info("command %s%r -> %s", name, a, r)
    if not await wait_for(c, lambda s: all(s["homed"][:s["joints"]]), 60, "all joints homed"):
        rc = 1
    r = await c.command("set_optional_stop", False, timeout=10)
    log.info("set_optional_stop(False) -> %s", r)
    for prog in args.programs:
        t0 = time.monotonic()
        r = await c.command("run", {"file": prog}, timeout=3600)
        pe = c.state.get("program_end")
        log.info("run %s -> %s in %.1f s; program_end=%s", prog, r, time.monotonic() - t0, pe)
        if r["outcome"] != "completed":
            rc = 1
    await asyncio.sleep(0.5)
    log.info("client stats: %s", c.stats)
    if c.stats["verified_mismatch"]:
        rc = 1
    task.cancel()
    return rc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://127.0.0.1:8791/")
    ap.add_argument("--verify-every", type=int, default=50)
    ap.add_argument("programs", nargs="+")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    sys.exit(asyncio.run(main(ap.parse_args())))
