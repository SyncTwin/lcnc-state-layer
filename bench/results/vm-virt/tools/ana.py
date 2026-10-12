#!/usr/bin/env python3
# ana.py OUTDIR : servo-thread period stats per phase from halsampler (col0 = timedelta.0.out, ns)
import gzip, os, sys
root = sys.argv[1]
def pct(v, q): return v[min(len(v)-1, int(q*len(v)))]
print("| phase | samples | period min / p1 / p50 / p99 / p99.9 / max, µs | |jitter| p99 / max, µs | timedelta.jitter, µs | servo-thread.tmax, µs | sidecar CPU, RSS |")
print("|---|---:|---|---|---:|---:|---|")
for ph in sorted(os.listdir(root)):
    d = os.path.join(root, ph)
    if not ph.startswith("p") or not os.path.isdir(d): continue
    v = []
    for line in gzip.open(os.path.join(d, "samples.txt.gz"), "rt"):
        p = line.split()
        if p and p[0].lstrip("-").isdigit() and p[0] != "0": v.append(int(p[0]))
    v.sort(); j = sorted(abs(x - 1000000) for x in v)
    he = dict(l.split()[:2] for l in open(os.path.join(d, "hal_end.txt")) if l.strip())
    cpu = open(os.path.join(d, "sidecar_cpu.txt")).readline().strip().replace("sidecar ", "") if os.path.exists(os.path.join(d, "sidecar_cpu.txt")) else "—"
    f = lambda x: "%.1f" % (x / 1000)
    print("| %s | %d | %s | %s / %s | %s | %s | %s |" % (ph, len(v), " / ".join(f(pct(v, q)) for q in (0, .01, .5, .99, .999)) + " / " + f(v[-1]),
          f(pct(j, .99)), f(j[-1]), f(int(he["timedelta.0.jitter"])), f(int(he["servo-thread.tmax"])), cpu))
