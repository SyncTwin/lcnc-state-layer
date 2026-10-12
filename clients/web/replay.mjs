// SPDX-License-Identifier: GPL-2.0-or-later
// Replay a patch stream with the same applyMergePatch the browser uses.
// usage: node replay.mjs PATCHES.jsonl OUT_CHECKPOINTS.jsonl EVERY
// PATCHES: first line {"snapshot": state}, then {"seq": n, "patch": {...}}.
// Writes {"seq", "state"} every EVERY patches and at the end.
import { readFileSync, writeFileSync } from "node:fs";
import { applyMergePatch } from "./merge_patch.js";

const [, , inp, out, everyArg] = process.argv;
const every = Number(everyArg || 100);
const lines = readFileSync(inp, "utf8").split("\n").filter(Boolean);
let state = JSON.parse(lines[0]).snapshot;
let seq = 0, gaps = 0;
const cps = [];
for (const line of lines.slice(1)) {
  const m = JSON.parse(line);
  if (m.seq !== seq + 1) gaps++;
  state = applyMergePatch(state, m.patch);
  seq = m.seq;
  if (seq % every === 0) cps.push(JSON.stringify({ seq, state }));
}
cps.push(JSON.stringify({ seq, state }));
writeFileSync(out, cps.join("\n") + "\n");
console.log(`node replay: ${lines.length - 1} patches, ${cps.length} checkpoints, seq gaps ${gaps}`);
