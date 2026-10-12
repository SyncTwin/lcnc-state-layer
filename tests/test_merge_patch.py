# SPDX-License-Identifier: GPL-2.0-or-later
"""RFC 7396 Appendix A test cases plus diff/apply round trips (pytest)."""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sidecar"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "clients", "python"))
from lcnc_state import merge_patch                 # noqa: E402
from lcnc_state_client import merge_patch as client_apply   # noqa: E402

RFC7396_A = [
    ({"a": "b"}, {"a": "c"}, {"a": "c"}),
    ({"a": "b"}, {"b": "c"}, {"a": "b", "b": "c"}),
    ({"a": "b"}, {"a": None}, {}),
    ({"a": "b", "b": "c"}, {"a": None}, {"b": "c"}),
    ({"a": ["b"]}, {"a": "c"}, {"a": "c"}),
    ({"a": "c"}, {"a": ["b"]}, {"a": ["b"]}),
    ({"a": {"b": "c"}}, {"a": {"b": "d", "c": None}}, {"a": {"b": "d"}}),
    ({"a": [{"b": "c"}]}, {"a": [1]}, {"a": [1]}),
    (["a", "b"], ["c", "d"], ["c", "d"]),
    ({"a": "b"}, ["c"], ["c"]),
    ({"a": "foo"}, None, None),
    ({"a": "foo"}, "bar", "bar"),
    ({"e": None}, {"a": 1}, {"e": None, "a": 1}),
    ([1, 2], {"a": "b", "c": None}, {"a": "b"}),
    ({}, {"a": {"bb": {"ccc": None}}}, {"a": {"bb": {}}}),
]


def test_rfc7396_appendix_a():
    for target, patch, result in RFC7396_A:
        assert merge_patch.apply(copy.deepcopy(target), patch) == result
        assert client_apply(copy.deepcopy(target), patch) == result


def test_diff_roundtrip():
    a = {"stat": {"position": [1.0, 2.0, 3.0], "task_state": 1, "joint": [{"homed": 0}],
                  "file": ""}, "errors": {"seq": 0, "recent": []}}
    b = copy.deepcopy(a)
    b["stat"]["position"][1] = 2.5
    b["stat"]["task_state"] = 4
    b["errors"] = {"seq": 1, "recent": [{"seq": 1, "text": "x"}]}
    b["program_end"] = {"seq": 1, "reason": "completed"}
    p = merge_patch.diff(a, b)
    assert p == {"stat": {"position": [1.0, 2.5, 3.0], "task_state": 4},
                 "errors": {"seq": 1, "recent": [{"seq": 1, "text": "x"}]},
                 "program_end": {"seq": 1, "reason": "completed"}}
    assert merge_patch.apply(copy.deepcopy(a), p) == b
    assert merge_patch.diff(b, b) == {}


def test_bool_int_distinct():
    assert merge_patch.diff({"x": 1}, {"x": True}) == {"x": True}


def test_deadband():
    a = {"pos": [1.0, 2.0], "v": 0.0, "n": 3}
    b = {"pos": [1.00001, 2.0], "v": 0.00002, "n": 3}
    assert merge_patch.diff(a, b, 1e-4) == {}
    c = {"pos": [1.00001, 2.5], "v": 0.00002, "n": 3}
    assert merge_patch.diff(a, c, 1e-4) == {"pos": [1.00001, 2.5]}
