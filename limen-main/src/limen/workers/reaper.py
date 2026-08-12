"""Reaper loop: dead-worker detection and event pruning."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from limen.persistence.database import Database


class ReaperLoop:
    """Periodically reaps dead workers and prunes old events."""

    def __init__(
        self,
        database: Database,
        *,
        interval: float = 15.0,
    ) -> None:
        self._database = database
        self._interval = interval
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            dead = self._database.reap_dead_workers()
            for worker_id in dead:
                self._database.write_event("worker.dead", {
                    "worker_id": worker_id,
                })
            self._database.prune_events()
