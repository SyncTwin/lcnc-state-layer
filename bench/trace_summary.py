#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Check a recorded trace against schema/emc_stat.schema.json and summarise it.

usage: trace_summary.py traces/x.jsonl.gz [...]   -> Markdown on stdout

Per trace: ticks, duration, file size, schema violations, how often each
top-level stat field changes between consecutive ticks, and float noise:
ticks where the machine is not moving (current_vel == 0 and inpos) but a
position field still changed.
"""
import collections
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "schema"))


def load(path):
    with gzip.open(path, "rt") as f:
        meta = json.loads(f.readline())["meta"]
        ticks = [json.loads(line) for line in f]
    return meta, ticks


def main(paths):
    from validate import Validator
    v = Validator()
    for path in paths:
        meta, ticks = load(path)
        bad = 0
        first_err = None
        for t in ticks:
            e = v.stat_error(t["stat"])
            if e:
                bad += 1
                first_err = first_err or e
        changes = collections.Counter()
        still_moves = collections.Counter()
        still_ticks = 0
        for a, b in zip(ticks, ticks[1:]):
            sa, sb = a["stat"], b["stat"]
            for k in sb:
                if sa.get(k) != sb[k]:
                    changes[k] += 1
            if sb["current_vel"] == 0 and sb["inpos"] and sa["current_vel"] == 0:
                still_ticks += 1
                for k in ("position", "actual_position", "joint_position",
                          "joint_actual_position"):
                    if sa[k] != sb[k]:
                        still_moves[k] += 1
        n = len(ticks)
        dur = ticks[-1]["t"] - ticks[0]["t"] if n > 1 else 0
        print("### %s" % os.path.basename(path))
        print()
        print("- ticks: %d, duration %.1f s, period %.3f s (%s)" % (
            n, dur, meta["period"], meta["period_source"]))
        print("- file: %d bytes gzip; fields per tick: %d; LinuxCNC %s" % (
            os.path.getsize(path), len(meta["fields"]), meta["linuxcnc_version"]))
        print("- schema `emc_stat.schema.json`: %d of %d ticks invalid%s" % (
            bad, n, (" (first: %s)" % first_err) if first_err else ""))
        print("- standing still (current_vel == 0, inpos, previous tick also 0): %d tick pairs; "
              "position fields changed anyway: %s" % (
                  still_ticks, dict(still_moves) or "none"))
        print("- fields changing between consecutive ticks (count of %d pairs):" % (n - 1))
        print()
        print("| field | changed | share |")
        print("|---|---:|---:|")
        for k, c in changes.most_common():
            print("| `%s` | %d | %.1f %% |" % (k, c, 100.0 * c / max(1, n - 1)))
        unchanged = sorted(set(meta["fields"]) - set(changes))
        print()
        print("- never changed (%d): %s" % (len(unchanged), ", ".join("`%s`" % k for k in unchanged)))
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
