"""QueueWorker: coordinates the background processing triad.

Composes ``QueueProcessor``, ``HeartbeatLoop``, and ``ReaperLoop``
from ``limen.workers``. This module remains as a thin facade for
backward-compatibility; the implementation lives in ``workers/``.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from limen.workers import HeartbeatLoop, QueueProcessor, ReaperLoop

if TYPE_CHECKING:
    from collections.abc import Callable

    from limen.persistence.database import Database
    from limen.routing.dispatcher import Dispatcher


class QueueWorker:
    """Background worker that drains the durable queue.

    Delegates to:
    - ``QueueProcessor`` — claims and dispatches queue entries.
    - ``HeartbeatLoop`` — periodic liveness updates.
    - ``ReaperLoop`` — dead-worker detection and event pruning.
    """

    def __init__(
        self,
        database: Database,
        dispatcher: Dispatcher,
        *,
        poll_interval: float = 0.1,
        max_attempts: int = 3,
        heartbeat_interval: float = 5.0,
        reaper_interval: float = 15.0,
        ui_event: Callable[..., None] | None = None,
    ) -> None:
        self._database = database
        worker_id = f"worker-{os.getpid()}"
        self._heartbeat = HeartbeatLoop(database, worker_id, interval=heartbeat_interval)
        self._reaper = ReaperLoop(database, interval=reaper_interval)
        self._processor = QueueProcessor(
            database, dispatcher, worker_id,
            poll_interval=poll_interval, max_attempts=max_attempts,
            heartbeat=self._heartbeat, ui_event=ui_event,
        )

    async def start(self) -> None:
        recovered = self._database.recover_leases()
        if recovered:
            self._database.write_event("queue.recovery", {
                "recovered_count": recovered,
            })
        self._heartbeat.start()
        self._reaper.start()
        self._processor.start()

    async def stop(self) -> None:
        await self._processor.stop()
        await self._reaper.stop()
        await self._heartbeat.stop()
