# SPDX-License-Identifier: GPL-2.0-or-later
"""JSON Merge Patch (RFC 7396, which obsoletes RFC 7386): compute and apply.

RFC 7396 replaces arrays as a whole and uses null to delete a member, so a
value that is itself null cannot be transmitted; linuxcnc.stat never yields
None, so this does not bite here.
"""


def same(a, b, deadband=0.0):
    """Equal for publishing purposes: floats within `deadband` count as equal
    (idea from Machinekit mkwrapper not_equal(), threshold 0.0001)."""
    if deadband and isinstance(a, float) and isinstance(b, float):
        return abs(a - b) <= deadband
    if type(a) is not type(b):
        return False
    if deadband and isinstance(a, list):
        return len(a) == len(b) and all(same(x, y, deadband) for x, y in zip(a, b))
    if deadband and isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k], deadband) for k in a)
    return a == b


def diff(old, new, deadband=0.0):
    """Return the merge patch that turns `old` into `new` (both dicts).

    Returns an empty dict when nothing changed.  With a deadband, floats that
    moved less than it are left out (the caller keeps the old value).
    """
    patch = {}
    for k in old:
        if k not in new:
            patch[k] = None
    for k, v in new.items():
        if k not in old:
            patch[k] = v
            continue
        o = old[k]
        if same(o, v, deadband):
            continue
        if isinstance(o, dict) and isinstance(v, dict):
            sub = diff(o, v, deadband)
            if sub:
                patch[k] = sub
        else:
            patch[k] = v
    return patch


def apply(target, patch):
    """Apply merge `patch` to `target` (RFC 7396 section 2), return the result.

    `target` is modified in place when both are dicts.
    """
    if not isinstance(patch, dict):
        return patch
    if not isinstance(target, dict):
        target = {}
    for k, v in patch.items():
        if v is None:
            target.pop(k, None)
        else:
            target[k] = apply(target.get(k), v)
    return target
