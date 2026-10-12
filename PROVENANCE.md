# PROVENANCE — what was taken and from where

Code by other authors is used only under a license compatible with LinuxCNC's GPL-2.0, with
authorship kept. Ideas are marked "after" with a link. No Machinekit code was copied into this
prototype.

## Code (copied)

| What | Source | Author | License | GPL-2.0 compatible |
|---|---|---|---|---|
| `schema/fbs/emc_common.fbs` (struct `Pose`, `Cartesian`) — verbatim, with a reference header | https://github.com/rmu75/linuxcnc/blob/07c35ceb762f83492b95ad5aab5673910072833a/src/emc/flatbuf/emc_common.fbs (branch `rs/zmq-experiments`) | rmu75 (Robert Schöftner) | GPL-2.0 (LinuxCNC tree, `COPYING` of the branch) | yes |
| `sim/axis_mm_headless.ini` (copy + 2 edits, marked in the file), `sim/sim_mm.tbl`, `sim/cooling.hal` | LinuxCNC `configs/sim/axis/` @ `2655e62fe6aa` | LinuxCNC contributors | GPL-2.0 | yes |
| RFC 7396 Appendix A test vectors in `tests/test_merge_patch.py` | https://www.rfc-editor.org/rfc/rfc7396#appendix-A | IETF (P. Hoffman, J. Snell) | IETF Trust (RFC code components — Simplified BSD) | yes |

Generated code (`bench/build/gen/*`, `schema/fbs/emc_stat.fbs`) is produced by `bench/gen_codecs.py`
and `flatc` from `schema/emc_stat.schema.json` in this repository.

## Ideas (taken "after", no code)

| Idea | Where here | Source | Author / rights holder | Source license |
|---|---|---|---|---|
| NML client sidecar without core changes; snapshot on subscribe, then changes; one reader of `error_channel` fanned out to all; command reply only to the sender (ticket) | `sidecar/` | machinekit-hal `src/executables/mkwrapper/src/mkwrapper.py` @ `dd9b188` (`third_party/machinekit-hal`) | Machinekit-HAL (`COPYING`: GPL) | GPL |
| Float deadband 0.0001 (`not_equal`) | `--deadband`, `merge_patch.same()` | same, `mkwrapper.py:821-823` | same | GPL |
| Poll NML only while there are subscribers | `server.py _ticker` | same, `mkwrapper.py:670` (`if self.status_service_subscribed`) | same | GPL |
| Ping period in the first message (`keepalive_timer`) | `snapshot.server.keepalive`, message `ping` | same, `mkwrapper.py:1853-1856`; `machinetalk-protobuf` `object.proto` `ProtocolParameters` | mkwrapper; Michael Haberler (protobuf) | GPL; MIT |
| Index deltas for arrays (element with `index`) — as the "arrays as index dictionaries" variant of the benchmark | `bench/*` variant `objidx` | `mkwrapper.py` (repeated fields filled by `index`), client merge — pymachinetalk `common.py` | Machinekit; Tormach Inc (pymachinetalk, MIT) | GPL; MIT |
| `seq` + process identity (epoch): a client tells a gap from a server restart | `snapshot.epoch` | machinekit-hal `src/modules/unmanaged/components/haltalk/src/haltalk_group.cc` | Michael Haberler, (C) 2013-2014 | GPL-2.0-or-later |
| Client state machine `down → trying → up`, "dead after 5 missed pings" | `StateClient.run_forever`, `clients/web/index.html` | pymachinetalk `machinetalk_core/common/subscribe.py` @ `be4bffd` | Tormach Inc, (C) 2015 | MIT |
| Machine configuration as its own message before the data (axes/joints count, axis_mask, kinematics, units, cycle time, max velocity/acceleration, per-joint index + backlash, ferror, position limits from stat) | `hello` (`sidecar/lcnc_state/core.py` `StateLayer.hello`, `schema/messages.schema.json` `$defs/hello`) | machinekit-hal `mkwrapper.py:967-1217` (`update_config`, `config` channel, full update on subscribe `:1900-1902`) @ `dd9b188`; `machinetalk-protobuf` `status.proto:213-229` (`EmcStatusConfigAxis`), `:373-413` (`EmcStatusConfig`) @ `eeceeb1`. Differences: one message per connection, not a subscribed channel with incremental updates; nothing from the INI | Machinekit; Michael Haberler (protobuf) | GPL; MIT |
| Bind to loopback by default | `--host 127.0.0.1` | mkwrapper `REMOTE=0` (`machinekit.ini`) | Machinekit | GPL |
| Snapshot + JSON Merge Patch with `seq`, snapshot request on a gap; view state as an opaque blob; compare encodings by measurement | the whole prototype | grandixximo https://github.com/LinuxCNC/linuxcnc/discussions/4571#discussioncomment-18871710, alex-pres discussioncomment-18868495 (view state) | comment authors | — |
| Run names the expected program | `run{expect_file}` | grandixximo discussioncomment-18848558 | — | — |
| Error log with a sequence number, broadcast to all | `state.errors` | grandixximo discussioncomment-18521152; c-morley #2013 | — | — |
| flatbuffers as a candidate, rmu75's IDL as the base | `schema/fbs/`, benchmark | rmu75 `rs/zmq-experiments`; rene-dev (first post of #4571) | — | GPL-2.0 |
| List of GUI pain points (command outcome, errors, program end…) | `docs/report/REQUIREMENTS.adoc` | c-morley https://github.com/LinuxCNC/linuxcnc/pull/4613#issuecomment-6104978584 | — | — |

## Only read (nothing taken)

| What | Commit | License (by files) |
|---|---|---|
| `third_party/machinekit-cnc` | `93065fc` | GPL (`COPYING`) |
| `third_party/machinetalk-protobuf` — `.proto` files used **as benchmark input** (`*_pb2.py` generated into `bench/build/pb`, not committed) | `eeceeb1` | MIT (Michael Haberler 2014) |
| `third_party/QtQuickVcp` | `cbe2fe3` | LGPL-2.1 (`LICENSE.LGPL`) |
| `third_party/Machineface` | `dd15610` | AGPL-3.0 (`LICENSE`) — nothing copied |
| libzmq (ws transport probe, outside the repository) | `46493370217a` | MPL-2.0 |
