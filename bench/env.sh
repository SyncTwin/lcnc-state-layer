#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Environment of a benchmark run (CPU, OS, compiler, library versions).
PY=${PY:-python3}
echo "date: $(date -u +%FT%TZ)"
echo "cpu: $(lscpu | sed -n 's/^Model name:\s*//p'), $(nproc) CPUs, $(lscpu | sed -n 's/^Hypervisor vendor:\s*//p') VM"
echo "os: $(. /etc/os-release; echo "$PRETTY_NAME"), kernel $(uname -r)"
echo "compiler: $(${CXX:-g++} --version | head -1), flags -O2 -std=c++20"
for p in nlohmann-json3-dev libflatbuffers-dev flatbuffers-compiler protobuf-compiler zlib1g-dev \
         python3-cbor2 python3-msgpack python3-flatbuffers python3-protobuf python3-websockets \
         python3-jsonschema nodejs; do
    v=$(dpkg-query -W -f="\${Version}" "$p" 2>/dev/null); [ -n "$v" ] && echo "deb $p $v"
done
echo "python (bench): $($PY --version 2>&1)"
$PY - <<'PYEOF'
import importlib
for m in ("cbor2", "msgpack", "flatbuffers", "google.protobuf", "orjson", "numpy"):
    try:
        mod = importlib.import_module(m)
        v = getattr(mod, "__version__", None) or getattr(mod, "version", None)
        extra = ""
        if m == "cbor2":
            try:
                import _cbor2; extra = " (C extension)"
            except ImportError:
                extra = " (pure Python)"
        if m == "msgpack":
            try:
                from msgpack import _cmsgpack; extra = " (C extension)"
            except ImportError:
                extra = " (pure Python)"
        if m == "google.protobuf":
            from google.protobuf.internal import api_implementation
            extra = " (%s)" % api_implementation.Type()
        print("py %s %s%s %s" % (m, v, extra, getattr(mod, "__file__", "")))
    except Exception as e:
        print("py %s missing (%s)" % (m, type(e).__name__))
PYEOF
command -v node >/dev/null && echo "node $(node --version)" && for p in cbor-x @msgpack/msgpack; do
    f="$(dirname "$0")/node/node_modules/$p/package.json"
    [ -f "$f" ] && node -e "const j=require('$f'); console.log('npm', j.name, j.version, j.license)"
done
true
