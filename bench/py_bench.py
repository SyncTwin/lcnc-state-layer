#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Encoding benchmark on recorded EMC_STAT updates (Python side).

usage: py_bench.py TRACE.jsonl.gz OUT.csv [--every N] [--repeats R] [--gen DIR]

Encode = stat dict -> bytes, decode = bytes -> dict (full) or -> client state
(patch / delta variants), per message, median over R passes after one warm-up
pass, then median and p95 over messages.  Clock: time.perf_counter_ns.
Variants that need a library that is not installed are skipped (logged).
"""
import argparse
import copy
import csv
import gzip
import json
import os
import statistics
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "sidecar"))
from lcnc_state import merge_patch as mp   # noqa: E402

BEATS = ("heartbeat", "taskbeat")


def pct(v, p):
    if not v:
        return 0.0
    s = sorted(v)
    return s[min(len(s) - 1, int(p * (len(s) - 1) + 0.5))]


def load(path, every):
    with gzip.open(path, "rt") as f:
        meta = json.loads(f.readline())["meta"]
        ticks = [json.loads(line)["stat"] for i, line in enumerate(f) if i % every == 0]
    return meta, ticks


def objidx(v, all_arrays):
    if isinstance(v, dict):
        return {k: objidx(x, all_arrays) for k, x in v.items()}
    if isinstance(v, list) and (all_arrays or (v and isinstance(v[0], dict))):
        return {str(i): objidx(x, all_arrays) for i, x in enumerate(v)}
    return v


class Row:
    def __init__(self, lib, variant, note=""):
        self.lib, self.variant, self.note = lib, variant, note
        self.ticks = self.msgs = 0
        self.bytes, self.enc, self.dec, self.diff, self.apply = [], [], [], [], []
        self.cold_enc = self.cold_dec = 0.0


def run(row, ticks, R, step):
    """step(i) -> None (no message) or (nbytes, enc_ns, dec_ns, diff_ns, apply_ns);
    step(None) resets per-pass state."""
    n = len(ticks)
    per = [[] for _ in range(n)]
    nbytes = [None] * n
    for p in range(R + 1):
        step(None)
        for i in range(n):
            r = step(i)
            if p == 0:
                if r is not None and row.cold_enc == 0:
                    row.cold_enc, row.cold_dec = r[1] / 1e3, r[2] / 1e3
                continue
            if r is None:
                continue
            nbytes[i] = r[0]
            per[i].append(r[1:])
    row.ticks = n
    for i in range(n):
        if nbytes[i] is None:
            continue
        row.msgs += 1
        row.bytes.append(nbytes[i])
        cols = list(zip(*per[i]))
        row.enc.append(statistics.median(cols[0]) / 1e3)
        row.dec.append(statistics.median(cols[1]) / 1e3)
        row.diff.append(statistics.median(cols[2]) / 1e3)
        row.apply.append(statistics.median(cols[3]) / 1e3)
    return row


T = time.perf_counter_ns


def full_variant(lib, variant, ticks, R, enc, dec, note=""):
    row = Row(lib, variant, note)
    out = {}

    def step(i):
        if i is None:
            return None
        t0 = T()
        b = enc(ticks[i])
        t1 = T()
        out["last"] = dec(b)
        t2 = T()
        return (len(b), t1 - t0, t2 - t1, 0, 0)
    run(row, ticks, R, step)
    if out["last"] != ticks[-1]:
        row.note += " ROUNDTRIP MISMATCH"
    return row


def patch_variant(lib, variant, ticks, R, enc, dec, view=lambda s: s, deadband=0.0,
                  note="", deflate=False):
    row = Row(lib, variant, note)
    st = {}

    def step(i):
        if i is None:
            st.clear()
            return None
        if i == 0:
            st["prev"] = view(ticks[0])
            st["client"] = copy.deepcopy(st["prev"])
            if deflate:
                st["z"] = zlib.compressobj(6, zlib.DEFLATED, -15)
                st["u"] = zlib.decompressobj(-15)
            return None
        t0 = T()
        cur = view(ticks[i])
        t1 = T()
        p = mp.diff(st["prev"], cur, deadband)
        t2 = T()
        if deadband and p:
            st["prev"] = mp.apply(st["prev"], copy.deepcopy(p))
        elif p:
            st["prev"] = cur
        if not p:
            return None
        b = enc(p)
        if deflate:  # permessage-deflate, context takeover (RFC 7692)
            b = st["z"].compress(b) + st["z"].flush(zlib.Z_SYNC_FLUSH)
            b = b[:-4]
        t3 = T()
        if deflate:
            raw = st["u"].decompress(b + b"\x00\x00\xff\xff")
            q = dec(raw)
        else:
            q = dec(b)
        t4 = T()
        mp.apply(st["client"], q)
        t5 = T()
        return (len(b), t3 - t0, t5 - t3, t2 - t1, t5 - t4)
    run(row, ticks, R, step)
    if not deadband and st.get("client") != view(ticks[-1]):
        row.note += " ROUNDTRIP MISMATCH"
    return row


def full_deflate(lib, variant, ticks, R, enc, dec, note=""):
    row = Row(lib, variant, note)
    st = {}

    def step(i):
        if i is None:
            st["z"] = zlib.compressobj(6, zlib.DEFLATED, -15)
            st["u"] = zlib.decompressobj(-15)
            return None
        t0 = T()
        b = enc(ticks[i])
        b = st["z"].compress(b) + st["z"].flush(zlib.Z_SYNC_FLUSH)
        b = b[:-4]
        t1 = T()
        st["last"] = dec(st["u"].decompress(b + b"\x00\x00\xff\xff"))
        t2 = T()
        return (len(b), t1 - t0, t2 - t1, 0, 0)
    run(row, ticks, R, step)
    return row


# ------------------------------------------------------------ flatbuffers
def fb_variants(ticks, R, gen):
    sys.path.insert(0, gen)
    import fb_codec
    rows = [full_variant("flatbuffers", "fb_full", ticks, R,
                         lambda d: bytes(fb_codec.pack(d)), fb_codec.unpack)]
    row = Row("flatbuffers", "fb_delta", "EmcStatDelta: changed fields only, arrays whole")
    st = {}

    def step(i):
        if i is None:
            st.clear()
            return None
        if i == 0:
            st["client"] = copy.deepcopy(ticks[0])
            return None
        t0 = T()
        b = fb_codec.pack_delta(ticks[i - 1], ticks[i])
        t1 = T()
        if b is None:
            return None
        b = bytes(b)
        fb_codec.apply_delta(b, st["client"])
        t2 = T()
        return (len(b), t1 - t0, t2 - t1, t1 - t0, t2 - t1)
    run(row, ticks, R, step)
    if st["client"] != ticks[-1]:
        row.note += " ROUNDTRIP MISMATCH"
    rows.append(row)
    return rows


# --------------------------------------------- protobuf (Machinetalk .proto)
def pb_variants(ticks, R, pbdir):
    """Machinetalk status messages (machinetalk-protobuf, MIT) filled from the
    stat dict the way mkwrapper fills them; full update = motion+io+task+interp
    every tick, incremental = only changed fields, repeated elements by index,
    floats with mkwrapper's 0.0001 threshold (mkwrapper.py not_equal)."""
    sys.path.insert(0, pbdir)
    from machinetalk.protobuf import message_pb2, types_pb2
    from google.protobuf.descriptor import FieldDescriptor as FD
    skipped = set()

    def setp(pos, v):
        for a, x in zip("xyzabcuvw", v):
            setattr(pos, a, x)

    def setf(m, name, v):
        f = m.DESCRIPTOR.fields_by_name[name]
        if f.enum_type is not None and f.enum_type.values_by_number.get(int(v)) is None:
            skipped.add(name)
            return
        setattr(m, name, v)

    def build(s):
        c = message_pb2.Container()
        c.type = types_pb2.MT_EMCSTAT_FULL_UPDATE
        mo = c.emc_status_motion
        for k in ("active_queue", "adaptive_feed_enabled", "block_delete", "current_line",
                  "current_vel", "delay_left", "distance_to_go", "enabled", "feed_hold_enabled",
                  "feed_override_enabled", "feedrate", "g5x_index", "inpos", "motion_line",
                  "motion_type", "motion_mode", "paused", "probe_tripped", "probe_val",
                  "probing", "queue", "queue_full", "rotation_xy", "state", "max_velocity",
                  "max_acceleration", "rapidrate"):
            setf(mo, k, s[k])
        mo.id = s["motion_id"]
        for k in ("actual_position", "dtg", "g5x_offset", "g92_offset", "position",
                  "probed_position"):
            setp(getattr(mo, k), s[k])
        setp(mo.joint_actual_position, s["joint_actual_position"][:9])
        setp(mo.joint_position, s["joint_position"][:9])
        for name in ("ain", "aout"):
            for i, v in enumerate(s[name]):
                e = getattr(mo, name).add(); e.index = i; e.value = v
        for name in ("din", "dout"):
            for i, v in enumerate(s[name]):
                e = getattr(mo, name).add(); e.index = i; e.value = bool(v)
        for i, v in enumerate(s["limit"]):
            e = mo.limit.add(); e.index = i; e.value = v
        for i, a in enumerate(s["axis"]):
            e = mo.axis.add(); e.index = i; e.velocity = a["velocity"]
        for i, j in enumerate(s["joint"]):
            e = mo.joint.add(); e.index = i
            for k in ("enabled", "fault", "homed", "homing", "inpos", "max_hard_limit",
                      "max_soft_limit", "min_hard_limit", "min_soft_limit", "override_limits"):
                setattr(e, k, bool(j[k]))
            for k in ("ferror_current", "ferror_highmark", "input", "output", "velocity"):
                setattr(e, k, j[k])
        for i, sp in enumerate(s["spindle"]):
            e = mo.spindle.add(); e.index = i
            for k in ("brake", "enabled", "override_enabled", "homed", "orient_fault",
                      "orient_state"):
                setattr(e, k, bool(sp[k]))
            e.direction = sp["direction"]; e.speed = sp["speed"]; e.override = sp["override"]
        io = c.emc_status_io
        io.estop = bool(s["estop"]); io.flood = bool(s["flood"]); io.mist = bool(s["mist"])
        setp(io.tool_offset, s["tool_offset"])
        io.pocket_prepped = s["pocket_prepped"]; io.tool_in_spindle = s["tool_in_spindle"]
        for i, t in enumerate(s["tool_table"]):
            e = io.tool_table.add(); e.index = i; e.id = t["id"]
            e.diameter = t["diameter"]; e.frontangle = t["frontangle"]
            e.backangle = t["backangle"]; e.orientation = t["orientation"]
            setp(e.offset, [t[a + "offset"] for a in "xyzabcuvw"])
        ta = c.emc_status_task
        for k in ("echo_serial_number", "exec_state", "file", "input_timeout", "optional_stop",
                  "read_line", "task_mode", "task_paused", "task_state", "call_level"):
            setf(ta, k, s[k])
        it = c.emc_status_interp
        it.command = s["command"]
        for k in ("interp_state", "interpreter_errcode", "program_units"):
            setf(it, k, s[k])
        for name in ("gcodes", "mcodes"):
            for i, v in enumerate(s[name]):
                e = getattr(it, name).add(); e.index = i; e.value = v
        for i, v in enumerate(s["settings"]):
            e = it.settings.add(); e.index = i; e.value = v
        return c

    def changed(a, b, thr):
        if isinstance(a, float) or isinstance(b, float):
            return abs(a - b) > thr
        return a != b

    def incr(prev, cur, out, thr):
        any_ = False
        for f, v in cur.ListFields():
            if f.label == FD.LABEL_REPEATED:
                pmap = {e.index: e for e in getattr(prev, f.name)}
                for e in v:
                    pe = pmap.get(e.index)
                    tmp = type(e)()
                    if pe is None:
                        tmp.CopyFrom(e)
                        sub = True
                    else:
                        sub = incr(pe, e, tmp, thr)
                    if sub:
                        tmp.index = e.index
                        getattr(out, f.name).add().CopyFrom(tmp)
                        any_ = True
            elif f.type == FD.TYPE_MESSAGE:
                tmp = type(v)()
                if incr(getattr(prev, f.name), v, tmp, thr) or not prev.HasField(f.name):
                    getattr(out, f.name).CopyFrom(tmp if prev.HasField(f.name) else v)
                    any_ = True
            else:
                if f.name == "index":
                    continue
                if not prev.HasField(f.name) or changed(getattr(prev, f.name), v, thr):
                    setattr(out, f.name, v)
                    any_ = True
        return any_

    def merge_by_index(dst, src):
        """pymachinetalk-style client merge: repeated elements by index."""
        for f, v in src.ListFields():
            if f.label == FD.LABEL_REPEATED:
                dmap = {e.index: e for e in getattr(dst, f.name)}
                for e in v:
                    d = dmap.get(e.index)
                    if d is None:
                        getattr(dst, f.name).add().CopyFrom(e)
                    else:
                        merge_by_index(d, e)
            elif f.type == FD.TYPE_MESSAGE:
                merge_by_index(getattr(dst, f.name), v)
            else:
                setattr(dst, f.name, v)

    rows = []
    row = Row("protobuf", "pb_machinetalk_full", "Machinetalk status.proto, motion+io+task+interp")
    out = {}

    def step(i):
        if i is None:
            return None
        t0 = T()
        b = build(ticks[i]).SerializeToString()
        t1 = T()
        c = message_pb2.Container()
        c.ParseFromString(b)
        t2 = T()
        return (len(b), t1 - t0, t2 - t1, 0, 0)
    rows.append(run(row, ticks, R, step))

    row = Row("protobuf", "pb_machinetalk_incremental",
              "mkwrapper style: changed fields, repeated by index, float threshold 1e-4")
    st = {}

    def step2(i):
        if i is None:
            st.clear()
            return None
        if i == 0:
            st["prev"] = build(ticks[0])
            st["client"] = message_pb2.Container()
            st["client"].CopyFrom(st["prev"])
            return None
        t0 = T()
        cur = build(ticks[i])
        t1 = T()
        tx = message_pb2.Container()
        tx.type = types_pb2.MT_EMCSTAT_INCREMENTAL_UPDATE
        any_ = incr(st["prev"], cur, tx, 1e-4)
        t2 = T()
        # mkwrapper keeps its mirror updated only with what it sent
        merge_by_index(st["prev"], tx)
        if not any_:
            return None
        b = tx.SerializeToString()
        t3 = T()
        c = message_pb2.Container()
        c.ParseFromString(b)
        t4 = T()
        merge_by_index(st["client"], c)
        t5 = T()
        return (len(b), t3 - t0, t5 - t3, t2 - t1, t5 - t4)
    rows.append(run(row, ticks, R, step2))
    if skipped:
        for r in rows:
            r.note += "; enum values not in .proto, field left out: " + " ".join(sorted(skipped))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trace")
    ap.add_argument("out")
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--gen", default=os.path.join(HERE, "build", "gen"))
    ap.add_argument("--pb", default=os.path.join(HERE, "build", "pb"))
    ap.add_argument("--label")
    a = ap.parse_args()
    meta, ticks = load(a.trace, a.every)
    period = meta["period"] * a.every
    label = a.label or os.path.basename(a.trace).split(".")[0]
    R = a.repeats
    print("py bench: %s, %d ticks, period %g s, %d repeats" % (label, len(ticks), period, R),
          file=sys.stderr)
    jd = lambda o: json.dumps(o, separators=(",", ":")).encode()
    rows = []

    def add(r):
        rows.append(r)
        print("  %s %s %s" % (r.lib, r.variant, r.note), file=sys.stderr, flush=True)

    add(full_variant("json", "json_full", ticks, R, jd, json.loads))
    add(patch_variant("json", "json_merge_patch", ticks, R, jd, json.loads))
    add(full_deflate("json+zlib", "json_full_deflate", ticks, R, jd, json.loads,
                     "permessage-deflate simulated: raw deflate, context takeover, level 6"))
    add(patch_variant("json+zlib", "json_merge_patch_deflate", ticks, R, jd, json.loads,
                      deflate=True, note="permessage-deflate simulated (RFC 7692)"))
    nob = [{k: v for k, v in t.items() if k not in BEATS} for t in ticks]
    add(patch_variant("json", "json_merge_patch_no_beats", nob, R, jd, json.loads,
                      note="heartbeat, taskbeat dropped (sidecar --drop-fields)"))
    add(patch_variant("json", "json_merge_patch_no_beats_deadband", nob, R, jd, json.loads,
                      deadband=1e-4, note="+ float deadband 1e-4 (mkwrapper threshold)"))
    add(patch_variant("json", "json_merge_patch_objidx_structs", ticks, R, jd, json.loads,
                      view=lambda s: objidx(s, False), note="arrays of objects as {index: obj}"))
    add(patch_variant("json", "json_merge_patch_objidx_all", ticks, R, jd, json.loads,
                      view=lambda s: objidx(s, True), note="all arrays as {index: value}"))
    try:
        import orjson
        add(full_variant("orjson", "json_full", ticks, R, orjson.dumps, orjson.loads))
        add(patch_variant("orjson", "json_merge_patch", ticks, R, orjson.dumps, orjson.loads))
    except ImportError:
        print("  orjson not installed: skipped", file=sys.stderr)
    import cbor2
    add(full_variant("cbor2", "cbor_full", ticks, R, cbor2.dumps, cbor2.loads))
    add(patch_variant("cbor2", "cbor_merge_patch", ticks, R, cbor2.dumps, cbor2.loads))
    import msgpack
    mpk = lambda o: msgpack.packb(o, use_bin_type=True)
    mun = lambda b: msgpack.unpackb(b, raw=False)
    add(full_variant("msgpack", "msgpack_full", ticks, R, mpk, mun))
    add(patch_variant("msgpack", "msgpack_merge_patch", ticks, R, mpk, mun))
    for r in fb_variants(ticks, R, a.gen):
        add(r)
    try:
        for r in pb_variants(ticks, R, a.pb):
            add(r)
    except Exception as e:      # protobuf runtime/gencode mismatch etc.
        print("  protobuf skipped: %s: %s" % (type(e).__name__, e), file=sys.stderr)

    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow("side,lib,variant,trace,period_s,ticks,msgs,empty_pct,bytes_mean,bytes_p50,"
                   "bytes_p95,bytes_max,enc_med_us,enc_p95_us,dec_med_us,dec_p95_us,diff_med_us,"
                   "diff_p95_us,apply_med_us,apply_p95_us,cold_enc_us,cold_dec_us,repeats,note"
                   .split(","))
        for r in rows:
            full = "full" in r.variant
            empty = 0.0 if full else 100.0 * (r.ticks - 1 - r.msgs) / max(1, r.ticks - 1)
            w.writerow(["py", r.lib, r.variant, label, period, r.ticks, r.msgs, "%.1f" % empty,
                        "%.0f" % statistics.mean(r.bytes) if r.bytes else 0,
                        "%.0f" % pct(r.bytes, .5), "%.0f" % pct(r.bytes, .95),
                        max(r.bytes) if r.bytes else 0,
                        "%.2f" % pct(r.enc, .5), "%.2f" % pct(r.enc, .95),
                        "%.2f" % pct(r.dec, .5), "%.2f" % pct(r.dec, .95),
                        "%.2f" % pct(r.diff, .5), "%.2f" % pct(r.diff, .95),
                        "%.2f" % pct(r.apply, .5), "%.2f" % pct(r.apply, .95),
                        "%.2f" % r.cold_enc, "%.2f" % r.cold_dec, R, r.note.strip()])


if __name__ == "__main__":
    main()
