# ZMQ over websocket vs plain websocket

Question from the 11.10 meeting summary (andypugh,
https://github.com/LinuxCNC/linuxcnc/discussions/4615#discussioncomment-18861086): "Evaluate ZMQ over WS".
Sources below: libzmq code, the RFC 45 specification and a short probe in a container.

## Facts

| # | What | Source / check |
|---|---|---|
| 1 | The `ws://` / `wss://` transport in libzmq is declared **DRAFT** ("New DRAFT … transport options WS and WSS … via the ZWS 2.0 protocol … WebSockets support is disabled by default if DRAFT APIs are disabled") | libzmq `NEWS` @ `46493370217a` (2026-07-26), section 4.3.3, lines 142-146; ZWS 2.0 spec — https://rfc.zeromq.org/spec/45/ , status "draft" |
| 2 | The `ZMQ_WSS_*` options (keys, certificates) are inside `#ifdef ZMQ_BUILD_DRAFT_API` | libzmq `include/zmq.h:615-647` |
| 3 | **But in practice** `ws://` is built in a stable autotools build too: in `configure.ac` `enable_ws` defaults to `$enable_drafts` (lines 655-657), while `enable_drafts` is assigned further down (lines 1062-1067) — at line 657 the variable is empty and the check `test "x$enable_ws" != "xno"` (line 665) passes. CMake is the opposite: without `ENABLE_DRAFTS`, `ENABLE_WS` is OFF (`CMakeLists.txt:163-171`) | libzmq `configure.ac`, `CMakeLists.txt` @ `46493370217a` |
| 4 | The Debian package `zeromq3 4.3.5-1` (trixie) is built with autotools without `--enable-ws`/`--enable-drafts` (`--with-pgm --with-libsodium --with-norm=yes --with-libgssapi_krb5=yes --disable-Werror`) → by item 3 ws is there, the draft API is not | https://sources.debian.org/src/zeromq3/4.3.5-1/debian/rules/ |
| 5 | **Probe** (`tests/zmq_ws_probe.py`, log `logs/sl6_zmq_ws_probe.log`): Ubuntu 24.04 `libzmq5 4.3.5-1build2`, `python3-zmq 24.0.1`. `zmq.has("draft")` = False, `zmq.has("ws")` = **False**, yet `PUB.bind("ws://127.0.0.1:5599/state")` succeeds. A plain websocket client (`python3-websockets`, same API as a browser) with subprotocol `ZWS2.0` connected and, after ~10 lines of protocol (identity frame `0x00`, subscription `0x00 0x01`), received 3 of 3 messages `b'\x00{"seq":N}'` | container run |
| 6 | Debian 12 bookworm (`libzmq5 4.3.4`) — **not checked** | — |
| 7 | Browser: in ZWS 2.0 every websocket message is one ZMQ frame with a flags byte (`0x00` last, `0x01` more, `0x02` command), the first message is the identity; a subscription is a `0x01`+topic message. So a browser needs its own ZWS implementation on top of `WebSocket` (small, but its own) | RFC 45 |
| 8 | ZMQ is already a LinuxCNC build dependency (`python3-zmq`, `debian/control.top.in:65`) and is used by the QtVCP/halui bridge (#3580, #4613) | LinuxCNC tree |

## What ZMQ gives over plain websocket for THIS task

| The state layer needs | Plain websocket (prototype) | ZMQ (PUB/SUB, ROUTER) |
|---|---|---|
| Broadcast status to all | loop over clients in the sidecar, one encode per encoding (`server.py _broadcast`) | PUB/XPUB does it |
| Subscribe to a part (topics) | has to be built (not done, ◐) | SUB/XPUB prefix topic filtering for free |
| Command reply to a specific client | each client has its own connection — the reply goes there (`command_result`) | ROUTER with the sender address (as mkwrapper did) |
| Slow client | client queue is bounded; on overflow it is dropped and gets a snapshot (`server.py Client.push`) | HWM: PUB **silently drops** messages; without `seq` the client does not know (Machinetalk lesson, rmu75 discussioncomment-18771183) — `seq`/resync are needed on top anyway |
| Snapshot on connect | addressed `snapshot` to the new client | PUB has no "new subscriber → snapshot to it only"; XPUB sees the subscription but can only answer all subscribers of the topic (mkwrapper sends `MT_EMCSTAT_FULL_UPDATE` on the same PUB topic, i.e. to all subscribers: `machinekit-hal …/mkwrapper.py:1340-1343`, flag set on XPUB subscription `:1899`) or via a separate ROUTER channel |
| Browser | native | ZWS 2.0 on top of WebSocket — draft spec, own JS implementation |
| Different transports (ipc://, tcp://, inproc) in one line | TCP/TLS only (though `websockets`/libwebsockets can do unix sockets) | yes — BsAtHome's / alex-pres's argument for ZMQ |
| Dependency | `python3-websockets` / `libwebsockets` (Debian) | `libzmq5` (Debian), but ws is draft |

## Conclusion

1. ZMQ over websocket **works** with libzmq 4.3.5 from Debian trixie / Ubuntu noble — in the stable
   build, although documented as draft (items 1-5). Relying on it for 2.10/3.0 is risky: draft status,
   the behaviour is a side effect of line order in `configure.ac`, and the CMake build does not enable ws.
2. For the state layer ZMQ takes over broadcast and reply routing, but **not** what the prototype had to
   build on top of the transport anyway: `seq` + snapshot on request, an addressed snapshot to a new
   client, command outcome, errors to all. BsAtHome said the same (discussioncomment-18778246: "The
   application layer problems remain, even with 0mq").
3. For a browser ZMQ adds a layer (ZWS 2.0) on top of the same WebSocket — what alex-pres called a
   "useless additional layer" after his own test
   (https://github.com/LinuxCNC/linuxcnc/discussions/4571#discussioncomment-18791278).
4. The prototype's choice: plain websocket for the GUI layer (one transport for browser and desktop);
   the protocol is described by a schema (`schema/messages.schema.json`) and does not depend on the
   transport, so ZMQ (or ipc) can be added as a second transport later if topics/ipc are needed — with
   the same `seq`/resync on top. No byte/CPU measurement of ZMQ: ZWS adds a 1-byte flags field per frame
   (RFC 45), the payload is the same as in `BENCH.adoc`.
