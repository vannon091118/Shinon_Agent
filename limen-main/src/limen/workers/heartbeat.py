"""Heartbeat loop: periodic worker liveness updates to the database."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from limen.persistence.database import Database


class HeartbeatLoop:
    """Emits periodic heartbeats to the ``worker_heartbeats`` table."""

    def __init__(
        self,
        database: Database,
        worker_id: str,
        *,
        interval: float = 5.0,
    ) -> None:
        self._database = database
        self._worker_id = worker_id
        self._interval = interval
        self._task: asyncio.Task[None] | None = None
        self._current_task_id: str = ""

    def set_current_task(self, task_id: str) -> None:
        self._current_task_id = task_id

    def start(self) -> None:
        self._database.heartbeat(self._worker_id, state="idle")
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._database.heartbeat(self._worker_id, state="dead")
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            state = "busy" if self._current_task_id else "idle"
            self._database.heartbeat(
                self._worker_id, state=state, task_id=self._current_task_id
            )
