# vm-virt: servo-thread jitter with and without the sidecar

Host: our stand VM `vm-virt` (KVM on AMD EPYC-Milan, 4 vCPU: 0,1 general, 2,3 isolated `isolcpus=2,3 nohz_full rcu_nocbs`, 2 GB RAM),
kernel 6.12.111 PREEMPT_RT, Debian 13. LinuxCNC 2.10.0~pre2 (packaged uspace build) running `sim/axis_mm_headless.ini`
(servo-thread 1 ms; RT thread `rtapi_app:T#0` SCHED_FIFO 98 on CPU 3). Load in every phase: `axis.ngc` run in a loop (`tools/driver.py`).
Sidecar and clients on CPUs 0,1, period 0.1 s, read-only, json, `--no-error-channel` (see below).

Measured with stock components: `timedelta` added first in servo-thread (period of every tick, ns) sampled every tick by
`sampler` + `halsampler` (300 000 ticks = 5 min per phase), `servo-thread.tmax` reset at phase start. Sidecar CPU: /proc utime+stime over 60 s
(pidstat/sysstat not on the VM), RSS from /proc/PID/status.

| phase | ticks | period min / p1 / p50 / p99 / p99.9 / max, µs | abs(jitter) p99 / max, µs | servo-thread.tmax, µs | sidecar CPU / RSS |
|---|---:|---|---|---:|---|
| p0_nosidecar | 300000 | 940.9 / 986.9 / 999.9 / 1014.0 / 1019.1 / 1068.4 | 15.0 / 68.4 | 96.4 | — |
| p1_1client | 299997 | 972.0 / 985.5 / 999.9 / 1014.9 / 1020.1 / 1033.8 | 15.7 / 33.8 | 10.0 | cpu_pct_60s=0.87 rss_kb=30552 |
| p2_5clients | 300000 | 939.8 / 986.2 / 999.9 / 1014.4 / 1019.7 / 1059.3 | 15.4 / 60.2 | 35.2 | cpu_pct_60s=1.37 rss_kb=30920 |

No difference attributable to the sidecar: p99 period jitter is 15.0 / 15.7 / 15.4 µs, worst case 68 µs happened in the run without it.
CPU of the sidecar on this host: 0.87 % (1 client), 1.37 % (5 clients); RSS ~30 MB. Client integrity: 360 verifications, 0 mismatches, 0 gaps.

Not measured: 20 clients (stand needed back), p99 of `servo-thread.time` (the thread's `.time` pin cannot be sampled through a net:
the thread writes its own storage, a linked signal keeps 0), the codec benchmark on this VM (Debian trixie debs were prepared, not run).

Found: with LinuxCNC 2.10.0~pre2 the error channel poll raises `linuxcnc.error: Error buffer invalid` on every tick, so the sidecar
publishes nothing (`ticks=0`); the runs above use `--no-error-channel`. websockets 15.0.1 (PyPI wheel, same version as Debian 13) was
put on PYTHONPATH from a temporary directory, nothing installed on the VM.
