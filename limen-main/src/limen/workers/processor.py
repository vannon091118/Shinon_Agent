"""Queue processor: claims and dispatches entries from the durable queue."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from limen.persistence.database import Database
    from limen.routing.dispatcher import Dispatcher


class QueueProcessor:
    """Core loop that drains the durable queue entry by entry."""

    def __init__(
        self,
        database: Database,
        dispatcher: Dispatcher,
        worker_id: str,
        *,
        poll_interval: float = 0.1,
        max_attempts: int = 3,
        heartbeat: Any = None,
        ui_event: Callable[..., None] | None = None,
    ) -> None:
        self._database = database
        self._dispatcher = dispatcher
        self._worker_id = worker_id
        self._poll_interval = poll_interval
        self._max_attempts = max_attempts
        self._heartbeat = heartbeat  # HeartbeatLoop for task tracking
        self._ui_event = ui_event
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
            entry = self._database.claim_next()
            if entry is None:
                await asyncio.sleep(self._poll_interval)
                continue
            task_id = str(entry["id"])
            if self._heartbeat is not None:
                self._heartbeat.set_current_task(task_id)
            if self._ui_event is not None:
                self._ui_event("worker.claimed", task_id=task_id)
            try:
                await self._process(entry)
            finally:
                if self._heartbeat is not None:
                    self._heartbeat.set_current_task("")

    async def _process(self, entry: dict[str, object]) -> None:
        from limen.schemas import ChatCompletionRequest

        task_id = str(entry["id"])
        try:
            body = json.loads(str(entry["body_json"]))
            request = ChatCompletionRequest.model_validate(body)
        except (json.JSONDecodeError, ValueError) as exc:
            self._database.dead_task(task_id)
            self._database.write_event("task.dead", {
                "id": task_id,
                "reason": f"invalid body: {exc}",
            })
            return

        self._database.write_event("task.started", {
            "id": task_id,
            "correlation_id": str(entry.get("correlation_id", "")),
        })

        started_at = datetime.now(UTC).timestamp()
        try:
            if request.is_streaming:
                self._database.finish_task(task_id)
                return
            correlation_id = str(entry.get("correlation_id", entry["id"]))
            cached = self._database.check_idempotent(correlation_id, "chat.completion")
            if cached is not None:
                self._database.finish_task(task_id)
                self._database.write_event("task.completed", {
                    "id": task_id,
                    "provider_deployment": "idempotent_cache",
                    "duration_seconds": 0.0,
                    "correlation_id": correlation_id,
                })
                return
            ui_cb = self._ui_event
            min_context_tokens = 0
            if request.model == "auto":
                from limen.routing.scanner import scan_request

                min_context_tokens = scan_request(request).context_tokens
            outcome = await self._dispatcher.dispatch(
                request,
                ui_event=(
                    (lambda et, **pl: ui_cb(et, **pl, request_id=task_id))
                    if ui_cb is not None else None
                ),
                min_context_tokens=min_context_tokens,
            )
            elapsed = datetime.now(UTC).timestamp() - started_at
            result_json = outcome.response.model_dump_json()
            if self._database.check_idempotent(correlation_id, "chat.completion") is None:
                self._database.store_idempotent(
                    correlation_id,
                    "chat.completion",
                    result_json,
                )
            self._database.finish_task(task_id)
            self._database.write_event("task.completed", {
                "id": task_id,
                "provider_deployment": outcome.deployment,
                "duration_seconds": round(elapsed, 3),
                "correlation_id": outcome.correlation_id,
            })
        except BaseException as exc:
            if isinstance(exc, asyncio.CancelledError):
                self._database.fail_task(task_id)
                raise
            attempts = int(str(entry.get("attempt_count", 0))) + 1
            if attempts < self._max_attempts:
                backoff = min(2.0 ** (attempts - 1), 30.0)
                jitter = backoff * 0.25
                await asyncio.sleep(backoff + (jitter * (
                    float(str(hash(task_id) % 1000)) / 1000.0
                )))
            self._database.write_event("task.failed", {
                "id": task_id,
                "model": str(entry.get("target_model", "")),
                "stream_flag": False,
                "failure_type": type(exc).__name__,
                "attempts": attempts,
                "waited_seconds": round(
                    datetime.now(UTC).timestamp() - started_at, 3
                ),
                "correlation_id": str(entry.get("correlation_id", "")),
            })
            if attempts >= self._max_attempts:
                self._database.dead_task(task_id)
                self._database.write_event("task.dead", {
                    "id": task_id,
                    "reason": str(exc),
                })
            else:
                self._database.fail_task(task_id)
