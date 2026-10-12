#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# SL-3: record stat traces while programs run through the sidecar.
#   record_traces.sh PERIOD_MS PROGRAM.ngc [PROGRAM.ngc ...]
# One trace per program: traces/<program>_<PERIOD_MS>ms.jsonl.gz (every polled
# stat dict + time).  The first program's trace also covers ESTOP_RESET, ON and
# homing.  Runs as the user owning the LinuxCNC NML segments.
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
ms=$1; shift
period=$(python3 -c "print($ms/1000)")
port=${PORT:-8792}
for prog in "$@"; do
    name=$(basename "$prog" .ngc)
    trace="$here/traces/${name}_${ms}ms.jsonl.gz"
    python3 "$here/sidecar/linuxcnc-state-layer" --allow-commands --port "$port" \
        --period "$period" --trace "$trace" > "$here/logs/sl3_sidecar_${name}_${ms}ms.log" 2>&1 &
    sc=$!
    sleep 1.5
    python3 "$here/tests/drive_programs.py" --url "ws://127.0.0.1:$port/" --verify-every 100 \
        "$prog" > "$here/logs/sl3_driver_${name}_${ms}ms.log" 2>&1 || echo "driver failed for $prog"
    sleep 1
    kill -TERM $sc; wait $sc || true
    ls -l "$trace"
done
