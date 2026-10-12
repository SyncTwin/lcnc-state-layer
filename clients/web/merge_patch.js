// SPDX-License-Identifier: GPL-2.0-or-later
// JSON Merge Patch (RFC 7396) for the LinuxCNC state layer clients.
// Shared by the browser client (index.html) and the node checks/benchmark.

// Apply `patch` to `target` (RFC 7396 section 2); returns the result.
// `target` is modified in place when both are objects.
export function applyMergePatch(target, patch) {
  if (patch === null || typeof patch !== "object" || Array.isArray(patch)) return patch;
  if (target === null || typeof target !== "object" || Array.isArray(target)) target = {};
  for (const k of Object.keys(patch)) {
    const v = patch[k];
    if (v === null) delete target[k];
    else target[k] = applyMergePatch(target[k], v);
  }
  return target;
}

function equal(a, b) {
  if (a === b) return true;
  if (typeof a !== typeof b || a === null || b === null || typeof a !== "object") return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) if (!equal(a[i], b[i])) return false;
    return true;
  }
  const ka = Object.keys(a), kb = Object.keys(b);
  if (ka.length !== kb.length) return false;
  for (const k of ka) if (!(k in b) || !equal(a[k], b[k])) return false;
  return true;
}

// Merge patch turning `a` into `b` (both objects); {} when equal.
export function createMergePatch(a, b) {
  const p = {};
  for (const k of Object.keys(a)) if (!(k in b)) p[k] = null;
  for (const k of Object.keys(b)) {
    if (!(k in a)) { p[k] = b[k]; continue; }
    const x = a[k], y = b[k];
    if (equal(x, y)) continue;
    if (x && y && typeof x === "object" && typeof y === "object" && !Array.isArray(x) && !Array.isArray(y)) {
      const sub = createMergePatch(x, y);
      if (Object.keys(sub).length) p[k] = sub;
    } else p[k] = y;
  }
  return p;
}
