#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Same patch stream through the Python client and the browser's JS code (node).

usage: web_node_check.py TRACE.jsonl.gz [EVERY]
Builds snapshot + patches from the trace with the sidecar's diff, applies them
with clients/python merge_patch and with clients/web/merge_patch.js under node,
and compares the states at every checkpoint.
"""
import copy
import gzip
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sidecar"))
sys.path.insert(0, os.path.join(ROOT, "clients", "python"))
from lcnc_state import merge_patch                 # noqa: E402
from lcnc_state_client import merge_patch as apply  # noqa: E402

trace = sys.argv[1]
every = int(sys.argv[2]) if len(sys.argv) > 2 else 100
with gzip.open(trace, "rt") as f:
    f.readline()
    states = [{"stat": json.loads(l)["stat"]} for l in f]
tmp = tempfile.mkdtemp()
pf, cf = os.path.join(tmp, "patches.jsonl"), os.path.join(tmp, "cps.jsonl")
py_cps = {}
with open(pf, "w") as f:
    f.write(json.dumps({"snapshot": states[0]}) + "\n")
    client = copy.deepcopy(states[0])
    seq = 0
    for a, b in zip(states, states[1:]):
        p = merge_patch.diff(a, b)
        if not p:
            continue
        seq += 1
        f.write(json.dumps({"seq": seq, "patch": p}) + "\n")
        client = apply(client, p)
        if seq % every == 0:
            py_cps[seq] = copy.deepcopy(client)
    py_cps[seq] = copy.deepcopy(client)
r = subprocess.run(["node", os.path.join(ROOT, "clients", "web", "replay.mjs"), pf, cf, str(every)],
                   capture_output=True, text=True)
print(r.stdout.strip(), r.stderr.strip())
ok = bad = 0
for line in open(cf):
    cp = json.loads(line)
    # JSON numbers: node prints 1.0 as 1; == compares 1 == 1.0 as equal
    if cp["state"] == py_cps[cp["seq"]]:
        ok += 1
    else:
        bad += 1
        print("MISMATCH at seq", cp["seq"])
final_equal_trace = py_cps[seq] == states[-1]
print("%s: %d patches; node vs python checkpoints equal: %d, different: %d; "
      "final python state == last trace tick: %s" % (os.path.basename(trace), seq, ok, bad, final_equal_trace))
sys.exit(1 if bad or not final_equal_trace else 0)
