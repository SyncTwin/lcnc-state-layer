#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Repeat the whole encoding benchmark on one recorded trace:
#   bench/run.sh traces/<prog>_<period>.jsonl.gz [EVERY]
# EVERY: use every Nth tick (simulates a slower poll from a faster trace).
# Env: REPEATS_CPP (20), REPEATS_PY (5), REPEATS_NODE (20), PY (python with
# C-accelerated cbor2/msgpack; default: python3.12 if it has them, else python3).
# Output: bench/results/<label>.csv (all sides) and bench/results/<label>.md
set -eu
here=$(cd "$(dirname "$0")" && pwd)
trace=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
every=${2:-1}
REPEATS_CPP=${REPEATS_CPP:-20}
REPEATS_PY=${REPEATS_PY:-5}
REPEATS_NODE=${REPEATS_NODE:-20}
build=$here/build
mkdir -p "$build" "$here/results"

if [ -z "${PY:-}" ]; then
    PY=python3
    if command -v python3.12 >/dev/null && python3.12 -c "import _cbor2; from msgpack import _cmsgpack" 2>/dev/null; then
        PY=python3.12
    fi
fi

# 1. codecs from schema/emc_stat.schema.json, flatbuffers code, Machinetalk protobuf
python3 "$here/gen_codecs.py" "$build/gen"
(cd "$build/gen" && flatc --cpp --python -o . emc_common.fbs emc_stat.fbs)
if command -v protoc >/dev/null; then
    mkdir -p "$build/pb"
    (cd "$here/../third_party/machinetalk-protobuf/src" &&
     protoc --python_out="$build/pb" -I . machinetalk/protobuf/*.proto 2>/dev/null) || true
fi
# 2. C++ bench (-O2)
${CXX:-g++} -O2 -std=c++20 -I "$build/gen" "$here/cpp/bench.cc" -o "$build/bench_cpp"

# 3. corpus
base=$(basename "$trace" .jsonl.gz)
label=$base
[ "$every" != 1 ] && label="${base}_every${every}"
period=$(python3 "$here/prepare.py" "$trace" "$build/corpus_$label.jsonl" --every "$every" | awk '{print $4}')
echo "== $label: period $period s, C++ x$REPEATS_CPP, $PY x$REPEATS_PY, node x$REPEATS_NODE"

# 4. run
"$build/bench_cpp" "$build/corpus_$label.jsonl" "$REPEATS_CPP" "$build/cpp_$label.csv" "$label" "$period"
"$PY" -W ignore "$here/py_bench.py" "$trace" "$build/py_$label.csv" --every "$every" \
    --repeats "$REPEATS_PY" --label "$label"
if command -v node >/dev/null; then
    [ -d "$here/node/node_modules" ] || (cd "$here/node" && npm install --no-audit --no-fund >/dev/null 2>&1) || true
    node "$here/node/bench.mjs" "$build/corpus_$label.jsonl" "$REPEATS_NODE" "$build/node_$label.csv" "$label" "$period"
fi

# 5. merge, environment, report
{ head -1 "$build/cpp_$label.csv"; for s in cpp py node; do
    [ -f "$build/${s}_$label.csv" ] && tail -n +2 "$build/${s}_$label.csv"; done; } > "$here/results/$label.csv"
PY="$PY" "$here/env.sh" > "$here/results/env.txt"
python3 "$here/report.py" "$here/results/$label.csv" > "$here/results/$label.md"
echo "== wrote $here/results/$label.csv and $label.md"
