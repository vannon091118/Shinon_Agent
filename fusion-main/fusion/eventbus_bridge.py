#!/usr/bin/env python3
"""
EventBus → JSONL Bridge (standalone daemon, now optional)
=========================================================

With EventBusLiveLogger integrated into ControlPlaneRuntime.wire(),
the live log is auto-managed. This standalone script is now an
optional daemon for use cases where the runtime is NOT being used
but events still need to be captured.

Usage (optional):
  python3 eventbus_bridge.py --fresh      # manual bridge
  python3 eventbus_bridge.py --daemon     # background daemon
"""

import asyncio
import sys
from pathlib import Path

LOG_PATH = Path("/tmp/eventbus-live-log.jsonl")
MAX_LINES = 5000

sys.path.insert(0, "fusion-main")
sys.path.insert(0, "karma-main")

from fusion.event_bus import (
    get_event_bus,
    AsyncEventBus,
    Event,
    EventBusLiveLogger,
    ALL_PIPELINE_EVENTS,
)


async def bridge_main(fresh: bool = False) -> None:
    """Attach to EventBus and forward all events to JSONL log."""
    if fresh:
        bus = AsyncEventBus()
    else:
        bus = get_event_bus()

    logger = EventBusLiveLogger()
    logger.attach(bus)

    print(f"[eventbus-bridge] Attached: {len(ALL_PIPELINE_EVENTS)} event types → {LOG_PATH}")
    print(f"[eventbus-bridge] Press Ctrl+C to stop")

    try:
        while True:
            await asyncio.sleep(5)
            written = await logger.flush()
            print(f"  ... {written} events logged", end="\r", flush=True)
    except KeyboardInterrupt:
        print(f"\n[eventbus-bridge] Stopped. {LOG_PATH}")
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    fresh = "--fresh" in sys.argv
    daemon = "--daemon" in sys.argv

    if daemon:
        import subprocess
        cmd = [sys.executable, __file__, "--fresh"]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        start_new_session=True)
        print(f"[eventbus-bridge] Daemon started (PID will be detached)")
        sys.exit(0)

    asyncio.run(bridge_main(fresh=fresh))
