#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# SL-4 live scenario: sidecar with commands + a read-only sidecar, then
# tests/sl4_commands.py.  Run as the LinuxCNC user with rip-environment.
set -u
here=$(cd "$(dirname "$0")/.." && pwd)
python3 "$here/sidecar/linuxcnc-state-layer" --allow-commands --validate --port 8791 \
    > "$here/logs/sl4_sidecar.log" 2>&1 &
sc=$!
sleep 2
python3 "$here/tests/sl4_commands.py" --url ws://127.0.0.1:8791/ --readonly-port 8793 \
    > "$here/logs/sl4_scenario.log" 2>&1
rc=$?
kill -TERM $sc; wait $sc
echo "sl4 rc=$rc"
