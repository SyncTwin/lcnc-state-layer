# SPDX-License-Identifier: GPL-2.0-or-later
"""Transport-independent core of the state layer.

One StateLayer per LinuxCNC instance.  It owns the sidecar's only
linuxcnc.command and linuxcnc.error_channel objects, polls linuxcnc.stat at a
fixed period, and turns every change into a JSON Merge Patch (RFC 7396) with a
sequence number.  Transports (websocket server, trace recorder, tests)
subscribe to the published messages.

State layout (snapshot.state):
    stat         every data field of linuxcnc.stat, names as in the module
    errors       {"seq": n, "recent": [last ERROR_RING entries]} -- the
                 error_channel is read here only, so every client sees every
                 entry the sidecar gets
    program_end  {"seq", "reason", "file", "line", "command_id"} -- absent
                 until the first program run ends

Commands go through ONE queue and are sent one at a time, each with its own
NML serial, by a child process (sender.py) that owns the only
linuxcnc.command object: the module waits for the serial echo holding the
GIL, which would stall the ticks; the next one is sent only after the previous one is resolved
(or, for long running ones, seen running).  Outcome rules (see
docs/report/CORE_CHANGES.adoc for what NML cannot tell):

    RCS status of our own serial (echo_serial_number == serial):
        RCS_ERROR -> failed
        RCS_DONE  -> completed.  task sets RCS_DONE only when execState is
                     DONE, motion and io are DONE, the MDI and interpreter
                     queues are empty and interpState is IDLE
                     (emctaskmain.cc:3720-3729), so for mdi/auto it means the
                     motion finished; for home it only means accepted, so
                     home completes when stat shows the joints homed.
    echo_serial_number already past our serial before we saw a final status
        (a command from another NML client, e.g. AXIS or halui, was processed
        in between) -> "accepted": received, outcome unknown.  emcmodule's
        wait_complete() would say RCS_DONE here (emcmodule.cc:932-935); we
        never report that as completed.
    long running commands (mdi, auto run/step/resume, run, home) that are
    still busy when the queue moves on are finished from stat (interp_state
    back to IDLE / joints homed): marked "attribution": "heuristic".
    no echo of our serial within EMC_COMMAND_TIMEOUT, or the sender process
        died/hung after starting the NML write -> "unknown": the message may
        be in task's queue and run later; it is never sent again.

abort, state ESTOP and state OFF do not wait in the queue: a second sender
process sends them at once; commands still queued are not sent.  Commands
in flight become "aborted" only when task has taken the abort (its serial
echoed), not when it is submitted.
"""
import asyncio
import collections
import copy
import json
import logging
import os
import sys
import time
import uuid

from . import merge_patch
from .statdict import stat_names, stat_to_dict

log = logging.getLogger("lcnc_state")

SCHEMA_VERSION = 1
ERROR_RING = 16
COMMAND_TIMEOUT = 5.0          # as EMC_COMMAND_TIMEOUT in emcmodule.cc
HOME_TIMEOUT = 300.0           # ASSUMPTION, not measured: longest homing sequence
RESOLVE_POLL = 0.005           # s between status polls while resolving a command
ERROR_GRACE = 0.03             # s to wait for an error text after RCS_ERROR
SEND_MARGIN = 1.0              # ASSUMPTION, not measured: sender reply beyond emcSendCommand's own 5 s wait
SPAWN_TIMEOUT = 5.0            # ASSUMPTION, not measured: sender start and "sending" marker
EFFECT_TIMEOUT = 1.0           # ASSUMPTION, not measured: RCS_DONE -> effect visible in stat
VIEW_STATE_MAX = 64 * 1024     # ASSUMPTION, not measured: opaque blob limit
VIEW_STATE_KEYS = 1024         # ASSUMPTION, not measured
FAILING_KINDS = ("OPERATOR_ERROR", "NML_ERROR")


class CommandError(Exception):
    pass


class SendError(Exception):
    """The command was not written to NML: linuxcnc.command raised, or the
    sender process could not take the request."""


class SendUnknown(Exception):
    """The sender died or hung after it started the NML write: the command
    may or may not have reached task.  It is never sent again by us."""


SENDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sender.py")


class CommandSender:
    """Parent end of sender.py: one request in flight at a time (a lock
    serializes callers), restarted on the next send if it died.  A sender
    that does not answer in time is killed."""

    def __init__(self, module_name, label="command"):
        self.module_name = module_name
        self.label = label
        self.proc = None
        self.lock = asyncio.Lock()

    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(
            sys.executable, SENDER, self.module_name,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
        r = await self._read(SPAWN_TIMEOUT, SendError)
        if not r.get("ready"):
            self.close()
            raise SendError(r.get("error", "sender did not start"))
        log.info("%s sender pid %d", self.label, self.proc.pid)

    async def _read(self, timeout, exc):
        try:
            line = await asyncio.wait_for(self.proc.stdout.readline(), timeout)
        except asyncio.TimeoutError:
            self.close()
            raise exc("%s sender did not answer within %.1f s, killed"
                      % (self.label, timeout))
        if not line:
            self.close()
            raise exc("%s sender exited" % self.label)
        return json.loads(line)

    async def send(self, name, args):
        async with self.lock:
            if self.proc is None or self.proc.returncode is not None:
                await self.start()
            try:
                self.proc.stdin.write((json.dumps({"name": name, "args": args}) + "\n").encode())
                await self.proc.stdin.drain()
            except (BrokenPipeError, ConnectionResetError) as e:
                self.close()
                raise SendError("%s sender: %s" % (self.label, e))
            r = await self._read(SPAWN_TIMEOUT, SendError)
            if not r.get("sending"):
                raise SendError(r.get("error", "unexpected sender reply %r" % (r,)))
            # from here the NML write may have happened
            r = await self._read(COMMAND_TIMEOUT + SEND_MARGIN, SendUnknown)
            if "error" in r:
                raise SendError(r["error"])
            return r["serial"], r["send"]

    def close(self):
        if self.proc is not None and self.proc.returncode is None:
            self.proc.kill()
        self.proc = None


def _const(lc, value, prefixes):
    """Accept a linuxcnc constant by name ("MODE_AUTO") or by value."""
    if isinstance(value, str):
        if not any(value.startswith(p) for p in prefixes) or not hasattr(lc, value):
            raise CommandError("unknown constant %r (expected %s*)"
                               % (value, "/".join(prefixes)))
        return getattr(lc, value)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CommandError("expected constant name or int, got %r" % (value,))
    return value


def _joints(st, a):
    return range(st.joints) if not a or a[0] < 0 else [a[0]]


def _spindle(st, a, i):
    return st.spindle[a[i] if len(a) > i else 0]


# What a command must change in stat before it is reported "completed".
# RCS_DONE alone is not enough: motion rejects some commands asynchronously
# (reportError in motion/command.c) after task already reported RCS_DONE, and
# the error text arrives later on error_channel with nothing tying it to the
# command.  Commands not listed here and executed by motion/io (jog, spindle,
# brake, override_limits, digital/analog outputs) end as "accepted".
def _state_reached(lc, task_state, wanted):
    """task reports its state from io estop and traj enabled only
    (determineState, emctask.cc): ESTOP, else ESTOP_RESET while traj is
    disabled, else ON.  STATE_OFF is never reported: STATE_OFF disables traj,
    so it shows as ESTOP_RESET, or stays ESTOP when sent in estop.
    STATE_ESTOP_RESET on a machine already out of estop leaves it ON."""
    if wanted == lc.STATE_OFF:
        return task_state != lc.STATE_ON
    if wanted == lc.STATE_ESTOP_RESET:
        return task_state != lc.STATE_ESTOP
    return task_state == wanted


EFFECTS = {
    "state": lambda lc, st, a: _state_reached(lc, st.task_state, a[0]),
    "mode": lambda lc, st, a: st.task_mode == a[0],
    "home": lambda lc, st, a: all(st.joint[j]["homed"] and not st.joint[j]["homing"]
                                  for j in _joints(st, a)),
    "unhome": lambda lc, st, a: all(not st.joint[j]["homed"] for j in _joints(st, a)),
    "set_optional_stop": lambda lc, st, a: st.optional_stop == bool(a[0]),
    "set_block_delete": lambda lc, st, a: st.block_delete == bool(a[0]),
    "feedrate": lambda lc, st, a: abs(st.feedrate - a[0]) < 1e-9,
    "rapidrate": lambda lc, st, a: abs(st.rapidrate - a[0]) < 1e-9,
    "maxvel": lambda lc, st, a: abs(st.max_velocity - a[0]) < 1e-9,
    "spindleoverride": lambda lc, st, a: abs(_spindle(st, a, 1)["override"] - a[0]) < 1e-9,
    "set_feed_override": lambda lc, st, a: st.feed_override_enabled == bool(a[0]),
    "set_spindle_override": lambda lc, st, a: _spindle(st, a, 1)["override_enabled"] == bool(a[0]),
    "teleop_enable": lambda lc, st, a: (st.motion_mode == lc.TRAJ_MODE_TELEOP) == bool(a[0]),
    "traj_mode": lambda lc, st, a: st.motion_mode == a[0],
    "program_open": lambda lc, st, a: st.file == a[0],
    "flood": lambda lc, st, a: st.flood == a[0],
    "mist": lambda lc, st, a: st.mist == a[0],
    "abort": lambda lc, st, a: st.interp_state == lc.INTERP_IDLE,
}
# Executed inside task itself: RCS_DONE for the own serial means done.
TASK_LOCAL = ("load_tool_table", "reset_interpreter", "tool_offset")


class Pending:
    """A command sent to LinuxCNC whose outcome is not final yet."""

    def __init__(self, cid, client, name, args, serial, kind, sent_at):
        self.id = cid
        self.client = client
        self.name = name
        self.args = args
        self.serial = serial
        self.kind = kind            # "quick" | "long" | "home"
        self.sent_at = sent_at
        self.seen_busy = False
        self.errors = []
        self.aborted = False


UNKNOWN_SENT = ("command sender died or hung after starting the NML write; "
                "task may or may not execute it, not sent again")


class StateLayer:
    ALLOWED = ("state", "mode", "home", "unhome", "jog", "mdi", "program_open",
               "auto", "abort", "set_optional_stop", "set_block_delete",
               "feedrate", "rapidrate", "spindleoverride", "maxvel", "spindle",
               "flood", "mist", "brake", "override_limits", "teleop_enable",
               "traj_mode", "load_tool_table", "reset_interpreter",
               "set_feed_override", "set_spindle_override", "tool_offset",
               "set_digital_output", "set_analog_output", "run")

    def __init__(self, lc, allow_commands=False, view_store=None,
                 drop_fields=(), deadband=0.0, clock=time.monotonic,
                 error_channel=True):
        self.lc = lc
        self.stat = lc.stat()
        self.cstat = lc.stat()      # separate channel object for command resolution
        # error_channel is an NML queue: every read takes the entry away from
        # all other readers (a GUI next to the sidecar)
        self.err = lc.error_channel() if error_channel else None
        self.sender = CommandSender(lc.__name__) if allow_commands else None
        # abort / estop / machine off: own process, not queued behind the
        # command the worker is busy with
        self.usender = CommandSender(lc.__name__, "urgent") if allow_commands else None
        self.allow_commands = allow_commands
        self.clock = clock
        self.deadband = deadband
        self.epoch = uuid.uuid4().hex
        self.stat.poll()
        self.names = [n for n in stat_names(self.stat) if n not in drop_fields]
        self.drop_fields = list(drop_fields)
        self.error_kinds = {getattr(lc, k): k for k in (
            "OPERATOR_ERROR", "OPERATOR_TEXT", "OPERATOR_DISPLAY",
            "NML_ERROR", "NML_TEXT", "NML_DISPLAY")}
        self.seq = 0
        self.error_seq = 0
        self.errors = []
        self.program_end = None
        self.program_end_seq = 0
        self._run = None            # current AUTO program run or None
        self._run_err_seq0 = 0      # error_seq when the last run/auto command was sent
        self._last_auto = None      # (command id, sent at) of the last auto/run
        self.pending = []           # handed over to the tick tracker
        self.resolving = []         # commands being sent or resolved now
        self._abort_serials = []    # our aborts not yet echoed by task
        self._aborts_sending = 0    # aborts whose send has not returned a serial yet
        self._aborted_at = None     # serial of the last abort task has taken
        self.queue = collections.deque()
        self._wake = None
        self.subscribers = []
        self.views = view_store if view_store is not None else {}
        self.last_stat = stat_to_dict(self.stat, self.names)
        self.state = self._build_state(self.last_stat)
        self.ticks = 0
        self.empty_ticks = 0

    # ------------------------------------------------------------ state
    def _build_state(self, stat):
        st = {"stat": stat,
              "errors": {"seq": self.error_seq, "recent": list(self.errors)}}
        if self.program_end is not None:
            st["program_end"] = dict(self.program_end)
        return st

    def snapshot(self, view_key=None, keepalive=None):
        msg = {"type": "snapshot", "seq": self.seq, "epoch": self.epoch,
               "schema_version": SCHEMA_VERSION,
               "server": {"linuxcnc_version": getattr(self.lc, "version", ""),
                          "allow_commands": self.allow_commands,
                          "error_channel": self.err is not None,
                          "dropped_fields": self.drop_fields,
                          "deadband": self.deadband},
               "state": self.state}
        if keepalive:
            msg["server"]["keepalive"] = keepalive
        if view_key is not None and view_key in self.views:
            msg["view_state"] = {"key": view_key, "blob": self.views[view_key]}
        return msg

    def subscribe(self, fn):
        self.subscribers.append(fn)

    def _publish(self, msg):
        for fn in list(self.subscribers):
            fn(msg)

    # ------------------------------------------------------------- tick
    def tick(self, publish=True):
        """Poll error_channel and stat and track commands and program runs
        (always: a program end must not be lost while nobody listens); diff
        and publish a patch only if `publish`."""
        now = self.clock()
        new_errors = self._drain_errors()
        self.stat.poll()
        stat = stat_to_dict(self.stat, self.names)
        self._track_aborts(stat)
        if not self._aborts_sending:
            # task may already have taken an abort whose serial is not known
            # yet: finishing commands or a run now would call them completed
            self._track_pending(stat, now)
            self._track_program(stat, new_errors)
        self.last_stat = stat
        new_state = self._build_state(stat)
        if not publish:
            # nobody to send a patch to: the next client starts from a snapshot
            self.state = new_state
            return None
        patch = merge_patch.diff(self.state, new_state, self.deadband)
        self.ticks += 1
        if not patch:
            self.empty_ticks += 1
            return None
        self.seq += 1
        if self.deadband:
            # keep what clients have: values inside the deadband stay old
            self.state = merge_patch.apply(copy.deepcopy(self.state), patch)
        else:
            self.state = new_state
        msg = {"type": "patch", "seq": self.seq, "patch": patch}
        self._publish(msg)
        return msg

    def _drain_errors(self):
        new = []
        while self.err is not None:
            e = self.err.poll()
            if not e:
                break
            kind, text = e
            self.error_seq += 1
            entry = {"seq": self.error_seq, "kind": self.error_kinds.get(kind, str(kind)),
                     "text": text, "time": time.time()}
            # NML gives no command serial with an error: attribute by time window
            inflight = self.pending + self.resolving
            if inflight:
                entry["command_ids"] = [p.id for p in inflight]
                entry["attribution"] = "heuristic"
                for p in inflight:
                    p.errors.append(entry)
            new.append(entry)
            self.errors = (self.errors + [entry])[-ERROR_RING:]
            if self._run is not None and entry["kind"] in FAILING_KINDS:
                self._run["error"] = True
        return new

    # ------------------------------------------------------- program end
    def _track_program(self, stat, new_errors):
        lc = self.lc
        running = (stat["task_mode"] == lc.MODE_AUTO and
                   stat["interp_state"] != lc.INTERP_IDLE)
        if self._run is None and running:
            echo0 = stat["echo_serial_number"]
            # started by an auto/run command of this sidecar sent in the last
            # 2 s, or by another NML client (AXIS cycle start, halui)
            recent = self._last_auto is not None and self.clock() - self._last_auto[1] < 2.0
            cid = self._last_auto[0] if recent else None
            self._last_auto = None
            # errors since that command was sent, else since this tick
            seq0 = self._run_err_seq0 if recent else self.error_seq - len(new_errors)
            self._run = {"file": stat["file"], "error": any(
                e["kind"] in FAILING_KINDS and e["seq"] > seq0 for e in self.errors),
                "abort": False, "command_id": cid, "echo0": echo0}
        run = self._run
        if run is None:
            return
        if stat["task_state"] != lc.STATE_ON:
            run["abort"] = True        # ESTOP / machine off ends the run
        if self._aborted_at is not None and self._aborted_at > run["echo0"]:
            run["abort"] = True        # task took our abort during the run
        if not running:
            reason = "aborted" if run["abort"] else "error" if run["error"] else "completed"
            self.program_end_seq += 1
            self.program_end = {"seq": self.program_end_seq, "reason": reason,
                                "file": run["file"], "line": stat["motion_line"],
                                "command_id": run["command_id"],
                                "attribution": "heuristic"}
            self._run = None

    def _track_aborts(self, stat):
        """An abort counts once task has taken it: echo_serial_number reached
        its serial (and not with RCS_ERROR for it).  Commands sent before it
        that are still in flight end as aborted."""
        echo, rcs = stat["echo_serial_number"], stat["state"]
        for s in list(self._abort_serials):
            if echo > s or (echo == s and rcs != self.lc.RCS_ERROR):
                self._abort_serials.remove(s)
                self._aborted_at = max(s, self._aborted_at or s)
            elif echo == s:             # abort itself failed
                self._abort_serials.remove(s)
        if self._aborted_at is not None:
            for p in self.pending:
                if p.serial < self._aborted_at:
                    p.aborted = True

    # ---------------------------------------------------------- commands
    def _kind(self, name, args):
        if name in ("mdi", "run"):
            return "long"
        if name == "auto" and args:
            return "long" if args[0] in (self.lc.AUTO_RUN, self.lc.AUTO_STEP,
                                         self.lc.AUTO_RESUME) else "quick"
        if name == "home":
            return "home"
        return "quick"

    def _convert(self, name, args):
        """Validate against the linuxcnc.command API, return call args."""
        lc = self.lc
        a = list(args or [])
        prefixes = {"state": ("STATE_",), "mode": ("MODE_",), "auto": ("AUTO_",),
                    "traj_mode": ("TRAJ_MODE_",), "spindle": ("SPINDLE_",),
                    "jog": ("JOG_",), "flood": ("FLOOD_",), "mist": ("MIST_",),
                    "brake": ("BRAKE_",)}
        if name in prefixes:
            if not a:
                raise CommandError("%s needs an argument" % name)
            a[0] = _const(lc, a[0], prefixes[name])
        if name == "auto":
            a = a[:1] + [int(x) for x in a[1:]]
        return a

    def submit(self, client, msg):
        """Handle a `command` message: validate, then queue.  Returns an
        immediate command_result for a rejected command, else None (the
        result goes to `client` later)."""
        cid = msg.get("id")
        name = msg.get("name")
        if not self.allow_commands:
            return self._result(cid, "failed", "commands disabled: sidecar runs "
                                "read-only, start it with --allow-commands")
        if name not in self.ALLOWED:
            return self._result(cid, "failed", "unknown command %r" % (name,))
        if self._urgent(name, msg.get("args") or []):
            # not queued: sent at once by its own process.  Commands still
            # queued were submitted before it and are not sent.
            while self.queue:
                c, m = self.queue.popleft()
                c(self._result(m.get("id"), "failed", "not sent: %s submitted after it" % name))
            asyncio.ensure_future(self._urgent_send(client, msg))
            return None
        self.queue.append((client, msg))
        if self._wake is not None:
            self._wake.set()
        return None

    def _urgent(self, name, args):
        if name == "abort":
            return True
        if name != "state" or not args:
            return False
        try:
            v = _const(self.lc, args[0], ("STATE_",))
        except CommandError:
            return False
        return v in (self.lc.STATE_ESTOP, self.lc.STATE_OFF)

    async def _urgent_send(self, client, msg):
        try:
            res = await self._process(client, msg, self.usender)
        except Exception as e:
            log.exception("command %r", msg)
            res = self._result(msg.get("id"), "failed", "%s: %s" % (type(e).__name__, e))
        if res is not None:
            client(res)

    async def command_worker(self):
        """Sends queued commands one at a time (urgent ones go around it)."""
        self._wake = asyncio.Event()
        for s in (self.sender, self.usender):
            try:
                await s.start()
            except Exception as e:  # LinuxCNC not up yet: retried on the first send
                log.warning("%s sender: %s", s.label, e)
        while True:
            if not self.queue:
                self._wake.clear()
                await self._wake.wait()
                continue
            client, msg = self.queue.popleft()
            try:
                res = await self._process(client, msg)
            except Exception as e:      # never let one command kill the worker
                log.exception("command %r", msg)
                res = self._result(msg.get("id"), "failed", "%s: %s" % (type(e).__name__, e))
            if res is not None:
                client(res)

    async def _send(self, p, name, sender=None):
        """Send `name` for pending command p and set p.serial.  Ticks go on
        meanwhile; errors read during the send are attributed to p."""
        if name == "auto":
            self._run_err_seq0 = self.error_seq
            self._last_auto = (p.id, self.clock())
        self.resolving.append(p)
        if name == "abort":
            self._aborts_sending += 1
        try:
            p.serial, dt = await (sender or self.sender).send(name, p.args)
            if name == "abort":
                self._abort_serials.append(p.serial)
        finally:
            self.resolving.remove(p)
            if name == "abort":
                self._aborts_sending -= 1
        p.sent_at = self.clock()
        return dt

    async def _process(self, client, msg, sender=None):
        cid, name, args = msg.get("id"), msg["name"], msg.get("args") or []
        if name == "run":
            return await self._run_program(client, cid, args)
        try:
            call_args = self._convert(name, args)
            kind = self._kind(name, call_args)
            p = Pending(cid, client, name, call_args, None, kind, self.clock())
            dt = await self._send(p, name, sender)
        except (CommandError, ValueError, TypeError, IndexError) as e:
            return self._result(cid, "failed", "%s: %s" % (type(e).__name__, e))
        except SendError as e:
            return self._result(cid, "failed", str(e))
        except SendUnknown as e:
            return self._result(cid, "unknown", "%s: %s" % (e, UNKNOWN_SENT))
        log.info("command %s %s%r serial=%d kind=%s send=%.1f ms",
                 cid, name, call_args, p.serial, kind, dt * 1e3)
        return await self._resolve(p)

    async def _resolve(self, p):
        """Watch our serial in stat until the outcome is known, or (long
        commands) until it is seen running; then hand over to tick()."""
        lc = self.lc
        effect = EFFECTS.get(p.name)
        done_at = None              # when RCS_DONE for our serial was seen
        self.resolving.append(p)
        try:
            while True:
                self.cstat.poll()
                diff = self.cstat.echo_serial_number - p.serial
                rcs = self.cstat.state
                now = self.clock()
                failing = [e for e in p.errors if e["kind"] in FAILING_KINDS]
                if diff == 0 and rcs == lc.RCS_ERROR:
                    await asyncio.sleep(ERROR_GRACE)
                    self._drain_errors()
                    return self._final(p, "failed", "RCS_ERROR")
                if failing and p.kind == "quick":
                    return self._final(p, "failed")
                if p.kind != "quick":
                    if diff == 0 and rcs == lc.RCS_DONE and p.kind == "long":
                        await asyncio.sleep(ERROR_GRACE)
                        self._drain_errors()
                        return self._final(p, "completed")
                    if diff > 0 or now - p.sent_at > COMMAND_TIMEOUT or (
                            diff == 0 and (self.cstat.interp_state != lc.INTERP_IDLE or
                                           (p.kind == "home" and rcs == lc.RCS_DONE))):
                        p.seen_busy = self.cstat.interp_state != lc.INTERP_IDLE
                        self._handover(p)
                        return None
                else:
                    if diff == 0 and rcs == lc.RCS_DONE and done_at is None:
                        done_at = now
                    if diff >= 0 and (done_at is not None or diff > 0):
                        if effect is not None and effect(lc, self.cstat, p.args):
                            await asyncio.sleep(ERROR_GRACE)
                            self._drain_errors()
                            return self._final(p, "completed")
                        if effect is None and done_at is not None and p.name in TASK_LOCAL:
                            await asyncio.sleep(ERROR_GRACE)
                            self._drain_errors()
                            return self._final(p, "completed")
                        since = now - (done_at if done_at is not None else p.sent_at)
                        if since > (EFFECT_TIMEOUT if effect is not None else ERROR_GRACE * 4):
                            self._drain_errors()
                            if [e for e in p.errors if e["kind"] in FAILING_KINDS]:
                                return self._final(p, "failed")
                            if effect is None:
                                return self._final(p, "accepted", "RCS_DONE; effect not "
                                                   "checkable in stat for %s" % p.name
                                                   if done_at is not None else
                                                   "echo_serial_number moved past this "
                                                   "command before its status was seen "
                                                   "(command from another NML client)")
                            if done_at is None:
                                return self._final(p, "accepted", "echo_serial_number moved "
                                                   "past this command before its status was "
                                                   "seen and stat does not show its effect")
                            return self._final(p, "failed", "RCS_DONE but stat does not show "
                                               "the effect within %.1f s" % EFFECT_TIMEOUT)
                    elif now - p.sent_at > COMMAND_TIMEOUT:
                        # emcSendCommand's own timeout is not reported by the
                        # module (emcmodule.cc), the message is in task's
                        # queue and may still be executed
                        return self._final(p, "unknown", "task did not echo serial %d "
                                           "within %.0f s; it may still execute it"
                                           % (p.serial, COMMAND_TIMEOUT))
                await asyncio.sleep(RESOLVE_POLL)
        finally:
            self.resolving.remove(p)

    def _handover(self, p):
        self.pending.append(p)

    def _homed(self, p, st):
        joints = range(st.joints) if not p.args or p.args[0] == -1 else [p.args[0]]
        return all(st.joint[j]["homed"] and not st.joint[j]["homing"] for j in joints)

    def _final(self, p, outcome, error=None, heuristic=False):
        failing = [e for e in p.errors if e["kind"] in FAILING_KINDS]
        if outcome == "completed" and failing:
            outcome = "failed"
        if outcome == "failed" and failing and (error is None or error == "RCS_ERROR"):
            error = failing[-1]["text"] if error is None else "RCS_ERROR: " + failing[-1]["text"]
        r = self._result(p.id, outcome, error)
        if p.errors:
            r["errors"] = p.errors
        if p.errors or heuristic:
            r["attribution"] = "heuristic"
        log.info("command %s %s -> %s%s", p.id, p.name, outcome,
                 " (%s)" % error if error else "")
        return r

    async def _run_program(self, client, cid, args):
        """run {file?, line?, expect_file?}: MODE_AUTO, program_open, AUTO_RUN,
        each resolved before the next.  expect_file refuses to start a
        different program than the client shows (grandixximo,
        discussioncomment-18848558); the check and AUTO_RUN are separate NML
        commands, so another client can still load a program in between."""
        lc = self.lc
        opts = args[0] if args and isinstance(args[0], dict) else {}
        steps = []
        self.cstat.poll()
        if self.cstat.task_mode != lc.MODE_AUTO:
            steps.append(("mode", [lc.MODE_AUTO]))
        if opts.get("file"):
            steps.append(("program_open", [opts["file"]]))
        for name, a in steps:
            p = Pending(cid, client, name, a, None, "quick", self.clock())
            try:
                await self._send(p, name)
            except SendError as e:
                return self._result(cid, "failed", "%s: %s" % (name, e))
            except SendUnknown as e:
                return self._result(cid, "unknown", "%s: %s: %s" % (name, e, UNKNOWN_SENT))
            r = await self._resolve(p)
            if r["outcome"] != "completed":
                r["error"] = "%s: %s" % (name, r.get("error", r["outcome"]))
                return r
        self.cstat.poll()
        expect = opts.get("expect_file")
        if expect is not None and self.cstat.file != expect:
            return self._result(cid, "failed", "loaded program %r is not the expected %r"
                                % (self.cstat.file, expect))
        a = [lc.AUTO_RUN, int(opts.get("line", 0))]
        ends0 = self.program_end_seq
        p = Pending(cid, client, "run", a, None, "long", self.clock())
        try:
            await self._send(p, "auto")
        except SendError as e:
            return self._result(cid, "failed", "auto: %s" % e)
        except SendUnknown as e:
            return self._result(cid, "unknown", "auto: %s: %s" % (e, UNKNOWN_SENT))
        r = await self._resolve(p)
        if (r is not None and r["outcome"] in ("failed", "aborted") and self._run is None
                and self.program_end_seq == ends0):
            # ended before any tick saw it running: record the end anyway
            self.program_end_seq += 1
            self.program_end = {"seq": self.program_end_seq,
                                "reason": "error" if r["outcome"] == "failed" else "aborted",
                                "file": self.cstat.file, "line": self.cstat.motion_line,
                                "command_id": cid, "attribution": "heuristic"}
            self._last_auto = None
        return r

    def _result(self, cid, outcome, error=None):
        r = {"type": "command_result", "id": cid, "outcome": outcome}
        if error:
            r["error"] = error
        return r

    def _track_pending(self, stat, now):
        """Finish handed-over long/home commands from stat (heuristic)."""
        lc = self.lc
        echo, rcs = stat["echo_serial_number"], stat["state"]
        done = []
        for p in self.pending:
            diff = echo - p.serial
            failing = [e for e in p.errors if e["kind"] in FAILING_KINDS]
            own_error = diff == 0 and rcs == lc.RCS_ERROR
            machine_off = stat["task_state"] != lc.STATE_ON
            outcome = err = None
            if p.kind == "home":
                if own_error or failing:
                    outcome, err = "failed", "RCS_ERROR" if own_error else None
                elif p.aborted or machine_off:
                    outcome = "aborted"
                elif all(stat["joint"][j]["homed"] and not stat["joint"][j]["homing"]
                         for j in (range(stat["joints"]) if not p.args or p.args[0] == -1
                                   else [p.args[0]])):
                    outcome = "completed"
                elif now - p.sent_at > HOME_TIMEOUT:
                    outcome, err = "failed", "timeout: joints not homed within %.0f s" % HOME_TIMEOUT
            else:
                idle = stat["interp_state"] == lc.INTERP_IDLE
                if not idle:
                    p.seen_busy = True
                finished = idle and ((diff == 0 and rcs in (lc.RCS_DONE, lc.RCS_ERROR)) or
                                     (diff > 0 and (p.seen_busy or now - p.sent_at > 1.0)))
                if finished or (machine_off and idle):
                    if p.aborted or machine_off:
                        outcome = "aborted"
                    elif own_error or failing or stat["exec_state"] == lc.EXEC_ERROR:
                        outcome, err = "failed", "RCS_ERROR" if own_error else None
                    elif diff == 0 or p.seen_busy:
                        outcome = "completed"
                    else:
                        outcome, err = "accepted", ("overtaken by another NML client's "
                                                    "command before it was seen running")
            if outcome:
                done.append(p)
                p.client(self._final(p, outcome, err, heuristic=True))
        for p in done:
            self.pending.remove(p)

    # -------------------------------------------------------- view state
    def view_put(self, key, blob, size):
        if not isinstance(key, str) or not key:
            raise CommandError("view_state_put: key must be a non-empty string")
        if size > VIEW_STATE_MAX:
            raise CommandError("view_state_put: blob of %d bytes exceeds %d"
                               % (size, VIEW_STATE_MAX))
        if key not in self.views and len(self.views) >= VIEW_STATE_KEYS:
            raise CommandError("view_state_put: too many keys")
        self.views[key] = blob
