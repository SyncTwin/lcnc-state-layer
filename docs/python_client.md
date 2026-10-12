# Using the Python client

A Python agent or script (for example a service running on the LinuxCNC machine) talks the same protocol as every other client, no adapter:

```python
import asyncio, sys
sys.path.insert(0, "clients/python")
from lcnc_state_client import StateClient

async def main():
    c = StateClient("ws://127.0.0.1:8791/", view_key="my-agent", verify_every=0)
    task = asyncio.ensure_future(c.run_forever())          # reconnects, fresh snapshot each time
    await c.ready.wait()
    print(c.state["stat"]["task_state"], c.state["errors"]["recent"][-1:])
    r = await c.command("mdi", "G0 X10", timeout=60)       # needs sidecar --allow-commands
    print(r["outcome"], r.get("error"))                     # completed | failed | aborted | accepted | unknown
    await c.view_state_put({"panel": "jobs"})               # opaque, returned on reconnect
    task.cancel()

asyncio.run(main())
```

- Errors: read `c.state["errors"]["recent"]` (every entry has `seq`); do **not** open a second
  `linuxcnc.error_channel()` next to the sidecar — it takes entries away from it
  (`logs/sl4_results.md` case 10, `docs/report/CORE_CHANGES.adoc` CC-2).
- Commands: `command_result.outcome == "completed"` is reported only when the command's own RCS status
  and the effect in stat agree; `accepted` means received but the outcome is unknown.
- Same protocol for the browser and any other client: `schema/messages.schema.json`.
