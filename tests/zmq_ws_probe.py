#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""SL-6 probe: does the distribution libzmq accept a ws:// endpoint, and can a
plain websocket client (what a browser has) talk to it?

Run with the Python that has python3-zmq (Debian/Ubuntu package).
"""
import asyncio
import sys
import time

import zmq

print("libzmq", zmq.zmq_version(), "pyzmq", zmq.pyzmq_version(),
      "has(draft)", zmq.has("draft"), "has(ws)", zmq.has("ws"))
ctx = zmq.Context()
pub = ctx.socket(zmq.PUB)
try:
    pub.bind("ws://127.0.0.1:5599/state")
    print("bind ws://127.0.0.1:5599/state: OK")
except zmq.ZMQError as e:
    print("bind ws:// FAILED: %s (errno %s)" % (e, e.errno))
    sys.exit(0)


async def browser_like():
    """Minimal ZWS 2.0 SUB client (RFC 45, protocol "ZWS2.0", no mechanism):
    one websocket message per ZMQ frame, first byte = flags (0x00 last,
    0x01 more, 0x02 command); first message each way = routing identity;
    subscribe = message whose body is 0x01 + topic."""
    import websockets
    try:
        async with websockets.connect("ws://127.0.0.1:5599/state", subprotocols=["ZWS2.0"]) as ws:
            print("plain websocket connect OK, subprotocol", ws.subprotocol)
            ident = await asyncio.wait_for(ws.recv(), 2)
            print("server identity frame:", ident)
            await ws.send(b"\x00")              # our (empty) identity, last frame
            await ws.send(b"\x00\x01")          # subscribe to everything
            await asyncio.sleep(0.2)
            for i in range(3):
                pub.send(b'{"seq":%d}' % i)
            got = []
            try:
                while len(got) < 3:
                    got.append(await asyncio.wait_for(ws.recv(), 2))
            except asyncio.TimeoutError:
                pass
            print("received %d messages: %r" % (len(got), got))
    except Exception as e:
        print("plain websocket connect FAILED: %s: %s" % (type(e).__name__, e))

asyncio.run(browser_like())
