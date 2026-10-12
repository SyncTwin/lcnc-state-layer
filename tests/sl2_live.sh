#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# SL-2 live check against a running LinuxCNC (sim/run_sim.sh):
#   sidecar (commands on, schema validation on)
#   client A: verifies reconstructed state against a snapshot every 50 patches
#   client B: drops every 37th patch -> seq gap -> resync_request -> verify
#   driver:   homes and runs the programs through the sidecar's commands
# Must run as the user owning the LinuxCNC NML segments, with rip-environment.
set -u
here=$(cd "$(dirname "$0")/.." && pwd)
out=${OUT:-$here/logs}
progs=("$@")
port=${PORT:-8791}
python3 "$here/sidecar/linuxcnc-state-layer" --allow-commands --validate --port "$port" \
    ${TRACE:+--trace "$TRACE"} > "$out/sl2_sidecar.log" 2>&1 &
sc=$!
sleep 2
python3 "$here/clients/python/lcnc_state_client.py" "ws://127.0.0.1:$port/" --verify-every 50 \
    --duration "${DURATION:-200}" > "$out/sl2_client_verify.log" 2>&1 &
ca=$!
python3 "$here/clients/python/lcnc_state_client.py" "ws://127.0.0.1:$port/" --verify-every 50 \
    --drop-every 37 --duration "${DURATION:-200}" > "$out/sl2_client_dropseq.log" 2>&1 &
cb=$!
sleep 1
python3 "$here/tests/drive_programs.py" --url "ws://127.0.0.1:$port/" "${progs[@]}" > "$out/sl2_driver.log" 2>&1
drc=$?
wait $ca; carc=$?
wait $cb; cbrc=$?
kill -TERM $sc; wait $sc
echo "driver rc=$drc clientA rc=$carc clientB rc=$cbrc"
