#!/bin/bash
# phase.sh LABEL CLIENTS DURATION_S : one jitter phase (CLIENTS=-1 -> no sidecar)
set -u
B=$HOME/sl-bench; L=$1; N=$2; D=$3; O=$B/out/$L; mkdir -p $O
export PYTHONPATH=$B/pylib
SC=""
if [ "$N" -ge 0 ]; then
  python3 $B/sidecar/linuxcnc-state-layer --ini $B/sim/run/axis_mm_headless.ini > $O/sidecar.log 2>&1 &
  SC=$!; sleep 3
  for i in $(seq 1 $N); do python3 $B/clients/python/lcnc_state_client.py --verify-every 50 --duration $((D+5)) > $O/client_$i.log 2>&1 & done
  sleep 3
fi
halcmd setp servo-thread.tmax 0; halcmd setp timedelta.0.reset 1; sleep 0.01; halcmd setp timedelta.0.reset 0
timeout $((D+10)) halsampler -n $((D*1000)) > $O/samples.txt 2>$O/halsampler.err &
HS=$!
if [ -n "$SC" ]; then
  sleep 30
  read u1 s1 < <(awk '{print $14, $15}' /proc/$SC/stat); t1=$(date +%s.%N)
  sleep 60
  read u2 s2 < <(awk '{print $14, $15}' /proc/$SC/stat); t2=$(date +%s.%N)
  rss=$(awk '/VmRSS/{print $2}' /proc/$SC/status); hz=$(getconf CLK_TCK)
  python3 -c "print('sidecar cpu_pct_60s=%.2f rss_kb=%s' % ((($u2+$s2)-($u1+$s1))/$hz/($t2-$t1)*100, $rss))" > $O/sidecar_cpu.txt
  taskset -pc $SC >> $O/sidecar_cpu.txt
fi
wait $HS
{ echo "servo-thread.tmax $(halcmd getp servo-thread.tmax)"; for p in max- min- jitter avg-err; do echo "timedelta.0.$p $(halcmd getp timedelta.0.$p 2>/dev/null || halcmd getp timedelta.0.$p)"; done; } > $O/hal_end.txt
[ -n "$SC" ] && { sleep 8; kill $SC; wait $SC 2>/dev/null; }
echo "phase $L done"
