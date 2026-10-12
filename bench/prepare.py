#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Trace -> plain corpus for the C++ and node benchmarks.

usage: prepare.py TRACE.jsonl.gz OUT.jsonl [--every N]
Writes one stat dict per line (every Nth tick, default every tick) and prints
the effective period.
"""
import argparse
import gzip
import json

ap = argparse.ArgumentParser()
ap.add_argument("trace")
ap.add_argument("out")
ap.add_argument("--every", type=int, default=1)
a = ap.parse_args()
with gzip.open(a.trace, "rt") as f, open(a.out, "w") as o:
    meta = json.loads(f.readline())["meta"]
    n = 0
    for i, line in enumerate(f):
        if i % a.every == 0:
            o.write(json.dumps(json.loads(line)["stat"], separators=(",", ":")) + "\n")
            n += 1
print("%d ticks, period %g s" % (n, meta["period"] * a.every))
