# lcnc-state-layer

SPDX-License-Identifier: GPL-2.0-or-later (see `LICENSE`, same as LinuxCNC)

Prototype of a state layer for LinuxCNC as a **sidecar** (no changes to LinuxCNC core):
it reads EMC_STAT through the existing NML interface (the stock `linuxcnc` Python module),
serves websocket clients with a full snapshot + JSON Merge Patch (RFC 7396) deltas with a
sequence number, accepts commands and answers each client with its own outcome, keeps opaque
per-client view state. Main output — an encoding benchmark on real EMC_STAT updates
(JSON full / Merge Patch / CBOR / MessagePack / flatbuffers / Machinetalk protobuf):
[`docs/report/BENCH.adoc`](docs/report/BENCH.adoc).

Context: LinuxCNC developer discussion about replacing NML (LinuxCNC/linuxcnc#4571, #4613).
This is a prototype for that discussion, not a proposed patch: the numbers and the list of what a
sidecar cannot solve are the point.

- Benchmark: [`docs/report/BENCH.adoc`](docs/report/BENCH.adoc) · requirements table: [`docs/report/REQUIREMENTS.adoc`](docs/report/REQUIREMENTS.adoc) ·
  what a sidecar cannot solve: `docs/report/CORE_CHANGES.adoc` · ZMQ over websocket: `docs/report/ZMQ_WS.md` ·
  approaches compared: `docs/report/APPROACHES.md` · provenance: `PROVENANCE.md`
- Protocol page in LinuxCNC doc format: `docs/src/code/state-layer.adoc`
- Using the Python client: [`docs/python_client.md`](docs/python_client.md)

> **WARNING: with `--allow-commands` a browser or script connected to the sidecar can move the
> machine. The sidecar is read-only by default and listens on 127.0.0.1 by default.**

## Layout

| Path | What |
|---|---|
| `schema/emc_stat.schema.json` | JSON Schema (draft 2020-12) of `state.stat` = every field of `linuxcnc.stat` (generated once from a live stat by `schema/gen_emc_stat_schema.py`) |
| `schema/messages.schema.json` | envelopes: `snapshot`, `patch`, `resync_request`, `command`, `command_result`, `view_state_put`, `view_state`, `ping`, `error` |
| `schema/fbs/` | flatbuffers schema, generated from the JSON Schema (the "second schema" of the flatbuffers variant), `Pose` from rmu75's IDL |
| `sidecar/linuxcnc-state-layer` | the sidecar (Python asyncio + python3-websockets over the `linuxcnc` module) |
| `clients/python/lcnc_state_client.py` | Python client (asyncio `StateClient`, blocking `RemoteStat`/`RemoteCommand`/`RemoteErrorChannel` with the `linuxcnc` call shapes) |
| `clients/web/` | browser client: `index.html` + `merge_patch.js` (no framework) |
| `bench/` | benchmark: `run.sh`, C++ / Python / node benches, codec generator, results in `bench/results/` |
| `traces/` | recorded stat traces of live program runs (input of the benchmark) |
| `sim/` | headless sim config and scripts; `tests/` — live scenarios; `logs/` — run logs |
| `third_party/` | Machinekit sources as pinned submodules, read-only (`git submodule update --init` only if you need them) |

Why Python for the sidecar: it uses the same `linuxcnc` module every Python GUI uses, needs
only Debian packages, and the core must not be touched; a C++ path through libnml would add
nothing the module does not give.

## Quick start on a stock LinuxCNC 2.10 (run-in-place) — how the results were produced

```sh
# LinuxCNC master (2.10-pre), uspace, headless
git clone https://github.com/LinuxCNC/linuxcnc /tmp/linuxcnc
sudo sh /tmp/linuxcnc/.github/scripts/install-deps-headless.sh   # or the apt list inside it
cd /tmp/linuxcnc/src && ./autogen.sh && \
  ./configure --with-realtime=uspace --disable-gui --disable-manpages --disable-build-documentation && \
  make -j"$(nproc)"
sudo apt install $(grep -v '^#' debian-packages.txt | cut -d' ' -f1)

# start the sim (as an unprivileged user; rtapi_app refuses root)
sim/run_sim.sh &                     # LINUXCNC_SRC=/tmp/linuxcnc, SIM_WORKDIR=/tmp/lcnc-sim

# in another shell, same user:
. /tmp/linuxcnc/scripts/rip-environment
sidecar/linuxcnc-state-layer --allow-commands --validate     # ws://127.0.0.1:8791/
python3 clients/python/lcnc_state_client.py --verify-every 50 --duration 30
python3 -m http.server -d clients/web 8000   # browser: http://127.0.0.1:8000/
```

Headless display: `sim/axis_mm_headless.ini` is `configs/sim/axis/axis_mm.ini` with `[DISPLAY]DISPLAY =
./headless_display` (a script that blocks until LinuxCNC shuts down, because there is no X server)
and without `axis_manualtoolchange.hal` (a Tk dialog; `core_sim.hal` already loops tool-change).

Checks that were run (logs in `logs/`): `tests/sl2_live.sh` (snapshot/patch/seq/resync),
`tests/record_traces.sh` (SL-3), `tests/sl4_live.sh` (commands, outcomes, errors, program end,
view state, read-only), `tests/web_node_check.py` (browser patch code vs Python),
`python3 -m pytest tests/test_merge_patch.py`.

## Repeat the benchmark (one command)

```sh
bench/run.sh traces/axis_100ms.jsonl.gz          # -> bench/results/axis_100ms.{csv,md}, env.txt
```

Needs `bench/tools-packages.txt` (Debian packages; orjson from PyPI and two npm packages for the
benchmark only — the variants are skipped if missing). `REPEATS_CPP`, `REPEATS_PY`, `REPEATS_NODE`
set the repeats; a second argument N uses every Nth tick.

## Dependencies and licenses

Product (sidecar + clients):

| Name | Version tested | License | In Debian |
|---|---|---|---|
| LinuxCNC (`linuxcnc` Python module) | master 2.10.0~pre2 @ 2655e62fe6aa | GPL-2.0 | yes |
| python3-websockets | 10.4 | BSD-3-Clause | yes |
| python3-jsonschema (only `--validate`) | 4.10.3 (apt); 4.26 was picked up from /usr/local in the container | MIT | yes |
| python3-cbor2 (only `?encoding=cbor`) | 5.6.2 | MIT | yes |
| python3-msgpack (only `?encoding=msgpack`) | 1.0.3 | Apache-2.0 | yes |

Benchmark and tests only:

| Name | Version | License | In Debian |
|---|---|---|---|
| nlohmann-json3-dev | 3.11.3 | MIT | yes |
| libflatbuffers-dev, flatbuffers-compiler, python3-flatbuffers | 2.0.8 | Apache-2.0 | yes |
| protobuf-compiler, python3-protobuf | 3.21.12 | BSD-3-Clause | yes |
| machinetalk-protobuf `.proto` (submodule, input only) | eeceeb1 | MIT | no |
| python3-numpy, python3-pytest | 1.26.4, apt | BSD-3-Clause, MIT | yes |
| python3-zmq / libzmq5 (ZMQ_WS probe) | 24.0.1 / 4.3.5 | BSD-3-Clause / MPL-2.0 | yes |
| orjson | 3.10.12 | Apache-2.0 OR MIT | **no** (PyPI) |
| cbor-x | 1.6.0 | MIT | **no** (npm) |
| @msgpack/msgpack | 2.8.0 | ISC | **no** (npm) |
| node | 22.22.0 (container) | MIT | yes (nodejs) |

Taken from others: see `PROVENANCE.md` (rmu75's `emc_common.fbs`, GPL-2.0; LinuxCNC sim files).

## Run next to a real LinuxCNC 2.10 + lcec machine

The sidecar is a separate process that attaches to an already running LinuxCNC: the same NML
file as the GUI, no rebuild of LinuxCNC, no change to its configuration. Axes and joints are read
from stat (`axis_mask`, `joints`), nothing assumes the sim.

**Default is read-only. `--allow-commands` lets any connected client move real servos.**
**It listens on 127.0.0.1; exposing it to the network (`--host`) is the operator's decision.**

1. Install on the machine (Debian 12/13, python3.11+): `sudo apt install python3-websockets`
   (optional `python3-jsonschema python3-cbor2 python3-msgpack`). The `linuxcnc` module comes from
   the installed LinuxCNC (package, or `. scripts/rip-environment` for run-in-place). Copy this
   repository (only `sidecar/`, `schema/`, `clients/` are needed).
2. With LinuxCNC running (any GUI), as the same user:
   `sidecar/linuxcnc-state-layer` (add `--ini /path/machine.ini` if `INI_FILE_NAME` is not set; the
   poll period is taken from `[DISPLAY]CYCLE_TIME` as AXIS does).
3. Check the connection: `python3 clients/python/lcnc_state_client.py --duration 20` — the log
   shows `snapshot seq=…` and the `seq` growing, and `verify … reconstructed state == snapshot`.
4. Record a trace while a program runs (started from the GUI as usual):
   `sidecar/linuxcnc-state-layer --port 8792 --trace traces/mymachine_100ms.jsonl.gz` and stop it
   with Ctrl-C after the program ends.
5. Repeat the benchmark on it: `bench/run.sh traces/mymachine_100ms.jsonl.gz`.
6. Stop: Ctrl-C (SIGINT/SIGTERM). The sidecar holds nothing LinuxCNC needs.

Important on a real machine: **by default the sidecar reads `error_channel`. It is a queue
with one consumer: if the GUI reads it too (AXIS, QtVCP, Gmoccapy do), each error goes to only one
of them, and the GUI may never show an error the sidecar took** (`docs/report/CORE_CHANGES.adoc`
CC-2). Next to such a GUI start the sidecar with `--no-error-channel`: errors stay with the GUI,
`errors.recent` stays empty, `snapshot.server.error_channel` is `false`, and command outcomes rest
on RCS status and stat only. Do not run two sidecars on one LinuxCNC for the same reason.

Command outcomes: `completed`, `failed`, `aborted`, `accepted` (task took it, a command from
another NML client came in between, outcome not known) and `unknown` (no echo of its serial within
5 s, or the sending process died after starting the write: task may still run it later; the sidecar
never sends it again, the client decides). `abort`, `state STATE_ESTOP` and `state STATE_OFF` are
not queued behind other commands: a second process sends them at once, and commands still queued
are not sent.

Known limits:
- `linuxcnc.command.wait_complete()` reports RCS_DONE when another client's command was echoed after
  ours (CC-1); a GUI using it next to the sidecar may report someone else's result as its own.
- `completed` for a command executed by motion/io means stat shows the requested effect; if another
  client produced the same effect meanwhile, it is still reported as ours.

Checked on real servos once (EtherCAT, 3 drives on X/Y/Z, jog only, one client): see the last
section of `docs/report/BENCH.adoc`.

Not verified:
- LinuxCNC 2.10 release packages (sim runs: master @ 2655e62fe6aa run-in-place, Ubuntu 24.04);
- a G-code program on live axes, homing on switches, more joints/spindles; the deadband against
  real encoder noise;
- real-time kernel timing in the sim runs (the container is not RT: task reported "main loop took 0.01–0.08 s");
- several clients, websocket clients over a real network; Debian 12 package versions (bookworm);
- a real browser against the live sidecar (only the patch-apply code was checked in node).
