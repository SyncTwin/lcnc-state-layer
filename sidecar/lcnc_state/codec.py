# SPDX-License-Identifier: GPL-2.0-or-later
"""Wire encodings of the sidecar's messages.

json is the default and the only text encoding; cbor and msgpack carry the
same message objects in binary websocket frames.  All three come from Debian
packages (python3 stdlib, python3-cbor2, python3-msgpack).
"""
import json

ENCODINGS = {}


def _json_enc(obj):
    return json.dumps(obj, separators=(",", ":"), allow_nan=False)


def _json_dec(data):
    return json.loads(data)


ENCODINGS["json"] = (_json_enc, _json_dec)

try:
    import cbor2
    ENCODINGS["cbor"] = (cbor2.dumps, cbor2.loads)
except ImportError:  # optional
    pass

try:
    import msgpack
    ENCODINGS["msgpack"] = (lambda o: msgpack.packb(o, use_bin_type=True),
                            lambda d: msgpack.unpackb(d, raw=False))
except ImportError:  # optional
    pass


def encoder(name):
    return ENCODINGS[name][0]


def decoder(name):
    return ENCODINGS[name][1]
