#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Start the headless LinuxCNC sim (run-in-place tree) as an unprivileged user.
#   LINUXCNC_SRC  run-in-place LinuxCNC tree (default /tmp/linuxcnc)
#   SIM_WORKDIR   writable copy of this directory (default /tmp/lcnc-sim)
#   SIM_USER      user to run as when started by root (default runner)
# rtapi_app refuses to run as root, hence the user switch.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
LINUXCNC_SRC=${LINUXCNC_SRC:-/tmp/linuxcnc}
SIM_WORKDIR=${SIM_WORKDIR:-/tmp/lcnc-sim}
SIM_USER=${SIM_USER:-runner}
mkdir -p "$SIM_WORKDIR"
cp "$here/axis_mm_headless.ini" "$here/headless_display" "$here/sim_mm.tbl" "$here/cooling.hal" "$SIM_WORKDIR/"
cmd=". '$LINUXCNC_SRC/scripts/rip-environment' && cd '$SIM_WORKDIR' && exec linuxcnc '$SIM_WORKDIR/axis_mm_headless.ini'"
if [ "$(id -u)" = 0 ]; then
    chown -R "$SIM_USER" "$SIM_WORKDIR"
    exec su "$SIM_USER" -s /bin/bash -c "$cmd" < /dev/null
else
    exec bash -c "$cmd"
fi
