# SPDX-License-Identifier: GPL-2.0-or-later
"""Child process that owns the sidecar's only linuxcnc.command object.

Each linuxcnc.command method writes the NML message and then polls the status
buffer until task echoes its serial (emcSendCommand in emcmodule.cc, sleeping
EMC_COMMAND_DELAY between polls).  The GIL is held for the whole wait, 10-100
ms, so neither the asyncio loop nor another Python thread of the sidecar runs
meanwhile and stat ticks are late.  Sending from this separate process keeps
the ticks on time.

Protocol: one JSON object per line.
    parent -> child  {"name": <linuxcnc.command method>, "args": [...]}
    child -> parent  {"sending": true}, then
                     {"serial": n, "send": seconds} | {"error": "<exc>: <text>"}
The child writes {"ready": true} once linuxcnc.command() is created.  It reads
requests one at a time, so commands are sent in the order the parent writes
them.  {"sending": true} is written right before the method is called: if the
child dies or hangs after it, the NML message may have been written and the
parent cannot tell, so it must not send the command again.  "error" means the
message was not written (the method raised, or the serial did not change:
c->write() failed, emcSendCommand returns before setting the serial).
"""
import importlib
import json
import sys
import time


def main():
    lc = importlib.import_module(sys.argv[1] if len(sys.argv) > 1 else "linuxcnc")
    out = sys.stdout
    try:
        cmd = lc.command()
    except Exception as e:
        out.write(json.dumps({"error": "%s: %s" % (type(e).__name__, e)}) + "\n")
        return 1
    out.write('{"ready": true}\n')
    out.flush()
    for line in sys.stdin:
        req = json.loads(line)
        out.write('{"sending": true}\n')
        out.flush()
        t0 = time.monotonic()
        prev = cmd.serial
        try:
            getattr(cmd, req["name"])(*req["args"])
            if cmd.serial == prev:
                res = {"error": "NML write failed (serial unchanged)"}
            else:
                res = {"serial": cmd.serial, "send": time.monotonic() - t0}
        except Exception as e:
            res = {"error": "%s: %s" % (type(e).__name__, e)}
        out.write(json.dumps(res) + "\n")
        out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
