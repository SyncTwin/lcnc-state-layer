// SPDX-License-Identifier: GPL-2.0-or-later
// Encoding benchmark on recorded EMC_STAT updates (browser side, run in node).
//
// usage: node bench.mjs CORPUS.jsonl REPEATS OUT.csv TRACE_LABEL PERIOD_S
//
// Same method as the C++ and Python benches: per message median over REPEATS
// passes after one warm-up pass, then median / p95 over messages.  Encode:
// object -> string/bytes; decode: string/bytes -> object, for patches plus
// applyMergePatch() from clients/web/merge_patch.js (the code the browser runs).
// Clock: process.hrtime.bigint().
import { readFileSync, writeFileSync } from "node:fs";
import { applyMergePatch, createMergePatch } from "../../clients/web/merge_patch.js";

const [, , corpus, repArg, out, label, period] = process.argv;
const R = Number(repArg || 20);
const ticks = readFileSync(corpus, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
const now = () => process.hrtime.bigint();
const us = (a, b) => Number(b - a) / 1000;
const pct = (v, p) => {
  if (!v.length) return 0;
  const s = [...v].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.round(p * (s.length - 1)))];
};
const med = (v) => pct(v, 0.5);
const deep = (o) => structuredClone(o);

const libs = [{ lib: "JSON", enc: (o) => JSON.stringify(o), dec: (s) => JSON.parse(s), size: (s) => Buffer.byteLength(s) }];
try {
  const { encode, decode } = await import("cbor-x");
  libs.push({ lib: "cbor-x", enc: encode, dec: decode, size: (b) => b.length });
} catch (e) { console.error("cbor-x not installed: skipped"); }
try {
  const { encode, decode } = await import("@msgpack/msgpack");
  libs.push({ lib: "@msgpack/msgpack", enc: encode, dec: decode, size: (b) => b.length });
} catch (e) { console.error("@msgpack/msgpack not installed: skipped"); }

function run(name, lib, step) {
  const n = ticks.length;
  const per = Array.from({ length: n }, () => []);
  const bytes = new Array(n).fill(-1);
  let cold = null;
  for (let p = 0; p <= R; p++) {
    step(null);
    for (let i = 0; i < n; i++) {
      const r = step(i);
      if (p === 0) { if (r && !cold) cold = r; continue; }
      if (!r) continue;
      bytes[i] = r[0];
      per[i].push(r.slice(1));
    }
  }
  const row = { name, lib, msgs: 0, bytes: [], enc: [], dec: [], diff: [], apply: [], cold };
  for (let i = 0; i < n; i++) {
    if (bytes[i] < 0) continue;
    row.msgs++; row.bytes.push(bytes[i]);
    for (const [k, j] of [["enc", 0], ["dec", 1], ["diff", 2], ["apply", 3]]) row[k].push(med(per[i].map((x) => x[j])));
  }
  return row;
}

const rows = [];
for (const L of libs) {
  const vname = L.lib === "JSON" ? "json" : L.lib === "cbor-x" ? "cbor" : "msgpack";
  let last;
  const rf = run(`${vname}_full`, L.lib, (i) => {
    if (i === null) return null;
    const t0 = now(); const b = L.enc(ticks[i]); const t1 = now(); last = L.dec(b); const t2 = now();
    return [L.size(b), us(t0, t1), us(t1, t2), 0, 0];
  });
  if (JSON.stringify(last) !== JSON.stringify(ticks.at(-1))) rf.note = "ROUNDTRIP MISMATCH";
  rows.push(rf);
  let client;
  const rp = run(`${vname}_merge_patch`, L.lib, (i) => {
    if (i === null) return null;
    if (i === 0) { client = deep(ticks[0]); return null; }
    const t0 = now();
    const p = createMergePatch(ticks[i - 1], ticks[i]);
    const t1 = now();
    if (!Object.keys(p).length) return null;
    const b = L.enc(p);
    const t2 = now();
    const q = L.dec(b);
    const t3 = now();
    client = applyMergePatch(client, q);
    const t4 = now();
    return [L.size(b), us(t0, t2), us(t2, t4), us(t0, t1), us(t3, t4)];
  });
  if (JSON.stringify(client) !== JSON.stringify(ticks.at(-1))) rp.note = "ROUNDTRIP MISMATCH";
  rows.push(rp);
}

const head = "side,lib,variant,trace,period_s,ticks,msgs,empty_pct,bytes_mean,bytes_p50,bytes_p95,bytes_max," +
  "enc_med_us,enc_p95_us,dec_med_us,dec_p95_us,diff_med_us,diff_p95_us,apply_med_us,apply_p95_us," +
  "cold_enc_us,cold_dec_us,repeats,note";
const f2 = (x) => x.toFixed(2);
const lines = [head];
for (const r of rows) {
  const full = r.name.includes("full");
  const empty = full ? 0 : (100 * (ticks.length - 1 - r.msgs)) / Math.max(1, ticks.length - 1);
  const mean = r.bytes.reduce((a, b) => a + b, 0) / Math.max(1, r.bytes.length);
  lines.push(["node", r.lib, r.name, label, period, ticks.length, r.msgs, empty.toFixed(1), mean.toFixed(0),
    pct(r.bytes, 0.5), pct(r.bytes, 0.95), Math.max(...r.bytes),
    f2(pct(r.enc, 0.5)), f2(pct(r.enc, 0.95)), f2(pct(r.dec, 0.5)), f2(pct(r.dec, 0.95)),
    f2(pct(r.diff, 0.5)), f2(pct(r.diff, 0.95)), f2(pct(r.apply, 0.5)), f2(pct(r.apply, 0.95)),
    f2(r.cold ? r.cold[1] : 0), f2(r.cold ? r.cold[2] : 0), R, `"${r.note || ""}"`].join(","));
  console.error(`  ${r.lib} ${r.name} ${r.note || ""}`);
}
writeFileSync(out, lines.join("\n") + "\n");
