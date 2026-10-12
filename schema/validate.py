# SPDX-License-Identifier: GPL-2.0-or-later
"""Validate state layer messages and stat dicts against schema/*.json.

Uses python3-jsonschema (Debian 12: 4.10, draft 2020-12 supported).
"""
import json
import os

import jsonschema

CLIENT_TYPES = ("resync_request", "command", "view_state_put")


class Validator:
    def __init__(self, schema_dir=os.path.dirname(os.path.abspath(__file__))):
        with open(os.path.join(schema_dir, "emc_stat.schema.json")) as f:
            self.stat_schema = json.load(f)
        with open(os.path.join(schema_dir, "messages.schema.json")) as f:
            self.msg_schema = json.load(f)
        cls = jsonschema.Draft202012Validator
        # Inline the stat schema where messages reference it by $id, so no
        # remote-reference resolver is needed (its API differs between the
        # jsonschema in Debian 12 (4.10) and newer releases).
        stat = {k: v for k, v in self.stat_schema.items() if k not in ("$schema", "$id")}
        msg = json.loads(json.dumps(self.msg_schema).replace(
            json.dumps({"$ref": self.stat_schema["$id"]}), json.dumps(stat)))
        self._stat = cls(self.stat_schema)
        # one validator per envelope: the root schema without oneOf, $ref to the def
        base = {k: v for k, v in msg.items() if k not in ("oneOf", "$id")}
        self._defs = {name: cls(dict(base, **{"$ref": "#/$defs/" + name}))
                      for name in msg["$defs"]}

    @staticmethod
    def _first(validator, obj):
        err = jsonschema.exceptions.best_match(validator.iter_errors(obj))
        if err is None:
            return None
        path = "/".join(str(p) for p in err.absolute_path)
        return "%s: %s" % (path or "<root>", err.message[:300])

    def stat_error(self, stat):
        return self._first(self._stat, stat)

    def message_error(self, msg):
        t = msg.get("type") if isinstance(msg, dict) else None
        if t not in self._defs:
            return "unknown message type %r" % (t,)
        return self._first(self._defs[t], msg)

    def client_message_error(self, msg):
        t = msg.get("type") if isinstance(msg, dict) else None
        if t not in CLIENT_TYPES:
            return "type must be one of %s, got %r" % (", ".join(CLIENT_TYPES), t)
        return self.message_error(msg)
