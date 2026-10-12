#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""bench/results/<label>.csv -> Markdown tables (one per side)."""
import csv
import sys

SIDES = {"cpp": "C++ (nlohmann/json 3.11, flatbuffers 2.0.8, -O2)",
         "py": "Python (stdlib json, orjson, cbor2, msgpack, flatbuffers, protobuf)",
         "node": "JavaScript in node (browser code path)"}


def f(x, nd=1):
    x = float(x)
    return ("%." + str(nd) + "f") % x if x < 100 else "%.0f" % x


def main(path):
    rows = list(csv.DictReader(open(path)))
    if not rows:
        return
    period = float(rows[0]["period_s"])
    print("Trace `%s`, %s ticks, poll period %g s (budget per tick %g µs). "
          "Bytes per message sent; CPU per message in µs (median / p95 over messages, "
          "each the median of the repeats); empty = share of ticks with nothing to send."
          % (rows[0]["trace"], rows[0]["ticks"], period, period * 1e6))
    print()
    for side, title in SIDES.items():
        rs = [r for r in rows if r["side"] == side]
        if not rs:
            continue
        print("#### %s, repeats %s" % (title, rs[0]["repeats"]))
        print()
        print("| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 "
              "| diff med | apply med | empty | enc+dec of tick | note |")
        print("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
        for r in rs:
            share = (float(r["enc_med_us"]) + float(r["dec_med_us"])) / (period * 1e6) * 100
            print("| %s | %s | %s | %s | %s | %s | %s / %s | %s / %s | %s | %s | %s %% | %.2f %% | %s |" % (
                r["variant"], r["lib"], r["bytes_mean"], r["bytes_p50"], r["bytes_p95"], r["bytes_max"],
                f(r["enc_med_us"]), f(r["enc_p95_us"]), f(r["dec_med_us"]), f(r["dec_p95_us"]),
                f(r["diff_med_us"]) if float(r["diff_med_us"]) else "–",
                f(r["apply_med_us"]) if float(r["apply_med_us"]) else "–",
                r["empty_pct"], share, r["note"]))
        print()


if __name__ == "__main__":
    main(sys.argv[1])
