# SPDX-License-Identifier: GPL-2.0-or-later
"""linuxcnc.stat -> plain dict, field names exactly as the Python module has them.

Tuples become lists, the per-joint/axis/spindle dicts stay dicts, and the
tool_result struct sequences in tool_table become dicts with the struct's
field names.  Methods (poll, toolinfo) are skipped; nothing else is dropped.
"""

# Field order of linuxcnc.tool_result (emcmodule.cc tool_result_fields).
TOOL_FIELDS = ("id", "xoffset", "yoffset", "zoffset", "aoffset", "boffset",
               "coffset", "uoffset", "voffset", "woffset", "diameter",
               "frontangle", "backangle", "orientation")

# Callables on linuxcnc.stat; everything else is data.
METHODS = ("poll", "toolinfo")


def stat_names(stat):
    """Sorted data attribute names of a linuxcnc.stat object."""
    names = []
    for k in dir(stat):
        if k.startswith("_") or k in METHODS:
            continue
        if callable(getattr(stat, k)):
            continue
        names.append(k)
    return sorted(names)


def to_plain(v):
    if isinstance(v, (bool, int, float, str)) or v is None:
        return v
    if isinstance(v, dict):
        return {k: to_plain(x) for k, x in v.items()}
    if type(v).__name__ == "tool_result":
        return {f: getattr(v, f) for f in TOOL_FIELDS}
    if isinstance(v, (tuple, list)):
        return [to_plain(x) for x in v]
    raise TypeError("unexpected stat value type %s" % type(v).__name__)


def stat_to_dict(stat, names):
    return {k: to_plain(getattr(stat, k)) for k in names}
