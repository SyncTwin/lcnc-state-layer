# APPROACHES — comparison of approaches to a "state layer for GUIs"

From primary sources (repositories, commits — by link). Bytes/CPU are from `bench/run.sh` on the trace
`traces/axis_100ms.jsonl.gz` (axis.ngc, 0.1 s poll, 1383 ticks; `bench/results/axis_100ms.csv`) where that
was possible on our trace; otherwise "not measured". Where the prototype is worse, it says so.

## Rows

| Approach | Fit for GUIs (AXIS / Gmoccapy / QtVCP / panelui / browser) | Snapshot + deltas | Command outcome to each client | Errors not lost | View state | Message schema | Dependencies (Debian?) | LinuxCNC style | Maturity, activity | Bytes / CPU per update | License |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **NML today** (LinuxCNC master @ `2655e62fe6aa`) | all Python GUIs — `linuxcnc` module; browser — only via a bridge | no: each client copies the whole EMC_STAT on every poll (`emcmodule.cc:1028`), task XDR-marshals the whole buffer (`linuxcnc.nml:11`, 20480 B) | no: shared status, `wait_complete` catches another client's echo (`emcmodule.cc:932-935`) | no: single-consumer queue (`cms_in.cc:746`, `:821`) | no | CMS C++ classes, no IDL | in core | — | in use since the 1990s; being replaced (#4571) | full EMC_STAT over NML — buffer 20480 B (`linuxcnc.nml`), CPU not measured | GPL-2.0 |
| **ZMQ halui ↔ GUI, c-morley** (#3580 — merged and reverted 2026-09-17; #4613 open, branch `zmq-halui-gui` @ `deef877fb7`) | AXIS/Gmoccapy/QtVCP get requests from halui (cycle start, softkey, jog rate); browser — no | not about state (halui → GUI event messages) | no | no (NML as before) | no | hand-written JSON (rmu75, #3580 issuecomment-3643625975) | python3-zmq (Debian), embedded CPython in halui | debated: embedded Python, ZMQ on top of NML (rene-dev, #4613 issuecomment-5943476643) | PR open, under discussion | not measured (different task) | GPL-2.0 |
| **New layer sketch, grandixximo** (#4571 discussioncomment-18848558, -18871710) | architecture: three kinds of state, focus, core→UI request/reply | proposed: snapshot + JSON Merge Patch with seq | proposed (per-client completion) | proposed (log with seq) | yes, opaque blob | proposed: JSON Schema | — | — | text, no code | measured by this prototype | — |
| **rmu75 `rs/zmq-experiments`** (@ `07c35ceb762f`, 2023-11-13) | replaces CMS/NML inside LinuxCNC; GUI via his client (cockpit) | no (full messages) | no (as NML) | 0mq error broadcast possible (rmu75, #3580 issuecomment-3422052670) | no | flatbuffers IDL (`emc_stat.fbs` 175 lines, "outdated and incomplete") | libzmq, flatbuffers (Debian) | C++ in the LinuxCNC tree | prototype branch, 2023 | flatbuffers full on our schema (`Pose` from his IDL): **6367 B**, C++ encode **6.7 us**, parse **3.6 us** | GPL-2.0 |
| **Machinekit Machinetalk** (mkwrapper: machinekit-hal `dd9b188`, 2024-03-26; `machinekit` archived since 2020-03; clients QtQuickVcp 2019, pymachinetalk 2020) | QtQuickVcp/Machineface (Qt5/QML), pymachinetalk; browser — via the webtalk bridge | yes: full update on subscribe + incremental (changed fields, arrays by `index`, 1e-4 threshold) | partly: ticket + reply to the sender, but only "executed/completed"; the `wait_complete` code is discarded | one reader → broadcast to all (no seq) | no | protobuf (`machinetalk-protobuf`, MIT), EMC fields up to 2.8 | libzmq, protobuf (Debian); gsl generator — not in Debian; Qt5 | CMake (machinekit-hal), own generator | stalled | with their `status.proto` on our trace (Python, protobuf 4.21 cpp): full **8383 B**, encode 846 us, parse 132 us; incremental "as mkwrapper" **156 B** (p95 223), encode with diff 2803 us | GPL (mkwrapper), MIT (.proto, pymachinetalk), LGPL-2.1 (QtQuickVcp), AGPL-3.0 (Machineface) |
| **Rockhopper** (MachineryScience/Rockhopper, last commit `70c4f63` 2016-08-30) — **inactive since 2016** | browser; JSON commands over websocket, "watch" on changed variables | partly: subscription to single variables with change notification | reply to a command — yes, outcome — no | reads `error_channel` itself (`LinuxCNCWebSktSvr.py:98`, `:214`) → shares the queue with the GUI | no | JSON, no schema | Tornado, Python 2 | no | inactive | not measured | GPL-3.0-or-later (README) |
| **lcnc-suite** (bildobodo/lcnc-suite, last commit `1386e71` 2026-06-12) — **active** | Vue 3 web UI + "UI-agnostic WebSocket gateway" (FastAPI) | no: full `status` ~40 fields at 30 Hz (README) | `reply {ok}` — no outcome | reads `error_channel` itself (`lcnc-gateway/gateway.py:1557`) | no ("armed" clients exist) | JSON per README, no schema | FastAPI in a venv (not Debian) | no | "under active development" (README) | not measured (subset of fields; full JSON of the same kind as our `json_full`) | GPL-3.0 |
| **OpcUaHalServer** (TheRoslyak/OpcUaHalServer, `2db20b0` 2023-12-15) | OPC UA clients; data from **HAL**, not NML | OPC UA subscriptions (standard) | no (writes "unfinished", forum 2023) | not about NML errors | no | OPC UA model | open62541 (build from source per README) | no | 3 files, 2023 | not measured | no license file in the repository |
| **This prototype** | Python GUIs — a facade with the `linuxcnc.stat` API (2-3 lines, `docs/python_client.md`); browser — native | yes: snapshot + RFC 7396 with seq, resync, epoch | yes: own `command_result` to each, `completed/failed/aborted/accepted`; but heuristic (CC-1, CC-3) | to all sidecar clients — yes; next to a GUI that reads the channel — **no** (CC-2) | yes | JSON Schema + generated `.fbs` | python3-websockets (Debian) | Python over `linuxcnc`, names from stat, asciidoc page | prototype, 2026-10 | JSON Merge Patch **6302 B** (C++ encode with diff 461 us, parse+apply 182 us); + permessage-deflate **199 B**; "arrays as index dictionaries" **744 B** | GPL-2.0-or-later (as LinuxCNC) |

## Where the prototype is worse

- **Arrays**: RFC 7396 replaces an array as a whole — `joint[16]`, positions go out whole on every tick:
  6302 B against 156 B for Machinetalk index deltas and 744 B for the "arrays as index dictionaries" variant
  (the same RFC 7396, a different data model).
- **Topics**: Machinetalk subscribes to branches (`motion`/`task`/`io`/`config`/`interp`); here there is one
  topic — a phone DRO also gets `tool_table`.
- **Errors and outcome** — the same NML wrapper as mkwrapper and Rockhopper: with a second GUI reading
  `error_channel`, errors are lost by one of the two (in all three projects).
- **Preview, files, HAL** — Machinetalk had them (preview, FTP, haltalk); this prototype does not.

## Where it is better (as checked)

- `seq` + resync + epoch (mkwrapper has no `seq`), no false `completed` in a run with a foreign writer
  (`logs/sl4_results.md` #9), view state, one schema for C++/Python/browser, browser without a bridge,
  Debian packages only.
