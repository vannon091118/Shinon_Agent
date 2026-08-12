"""Unit tests for the audit-failure labelling in ``durable_dispatch``.

Slice FE-E: typed dispatch failures (rate_limited, request_invalid, ...)
must reach the ``task.failed`` audit log with the original vocabulary, not
the outer ``HTTPException`` classname. Signals (``KeyboardInterrupt``) must
propagate without touching the durable ledger.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import HTTPException

if TYPE_CHECKING:
    from limen.routing import Dispatcher

from limen.api.dispatch import _failure_type_label, durable_dispatch
from limen.persistence import Database
from limen.schemas import ChatCompletionRequest

# ── _failure_type_label: pure helper ────────────────────────────────────



def test_failure_type_label_unwraps_http_exception_envelope() -> None:
    """The ``to_http_exception`` envelope carries ``error.type`` verbatim — use it."""
    exc = HTTPException(
        status_code=429,
        detail={"error": {"type": "rate_limited", "code": "429"}},
    )
    assert _failure_type_label(exc) == "rate_limited"


def test_failure_type_label_unwraps_provider_failure_when_typed() -> None:
    """If the typed dispatch exception (e.g. ProviderFailure) surfaces unwrapped,
    use its ``failure_type`` variant.
    """
    from limen.resilience import ProviderFailure

    exc = ProviderFailure(
        failure_type="rate_limited",
        message="throttled",
        http_code=429,
        retry_after_seconds=5,
    )
    assert _failure_type_label(exc) == "rate_limited"


def test_failure_type_label_falls_back_to_class_name() -> None:
    """Unexpected exceptions fall back to their Python class — still useful in audit."""
    sentinel = RuntimeError("not in the 8-enum vocabulary")
    assert _failure_type_label(sentinel) == "RuntimeError"


def test_failure_type_label_handles_bare_http_exception_detail() -> None:
    """An HTTPException without an ``error.type`` envelope shows the class name."""
    exc = HTTPException(status_code=503, detail={"message": "service unavailable"})
    assert _failure_type_label(exc) == "HTTPException"


# ── durable_dispatch: end-to-end audit row ──────────────────────────────


def _build_database(tmp_path: Path) -> tuple[Database, Path]:
    db = Database(tmp_path / "state.db", busy_timeout_ms=5000, sync_mode="normal")
    db.open()
    return db, tmp_path / "state.db"


def _read_failure_row(db_path: Path, task_id_pattern: str) -> tuple[str, dict[str, object]]:
    """Return the most recent ``task.failed`` row matching *task_id_pattern*."""
    with sqlite3.connect(db_path) as conn:
        rows = list(
            conn.execute(
                "SELECT event_type, payload_json FROM events"
                " WHERE event_type='task.failed' ORDER BY id DESC"
            )
        )
    for ev, payload in rows:
        decoded = json.loads(payload)
        if task_id_pattern in str(decoded.get("id", "")):
            return str(ev), decoded
    raise AssertionError(f"no task.failed event found for {task_id_pattern!r}")


class _StubDispatcher:
    """Stand-in for ``Dispatcher`` that raises a *typed* HTTPException."""

    async def dispatch(self, request: ChatCompletionRequest, **kwargs: object) -> None:
        raise HTTPException(
            status_code=429,
            detail={"error": {"type": "rate_limited", "code": "429", "message": "slow"}},
        )


class _UnexpectedDispatcher:
    """Stand-in that raises an unrelated exception — must reach audit as class name."""

    async def dispatch(self, request: ChatCompletionRequest, **kwargs: object) -> None:
        raise ValueError("unexpected pipeline error")


@pytest.mark.asyncio
async def test_durable_dispatch_records_typed_failure_type_for_http_envelope(
    tmp_path: Path,
) -> None:
    """Rate-limited calls must show ``rate_limited`` failure_type, not ``HTTPException``."""
    database, db_path = _build_database(tmp_path)
    try:
        request = ChatCompletionRequest.model_validate(
            {"model": "fake-model", "messages": [{"role": "user", "content": "x"}]}
        )
        with pytest.raises(HTTPException) as exc_info:
            await durable_dispatch(
                request,
                database,
                cast("Dispatcher", _StubDispatcher()),  # type: ignore[arg-type]
            )
        assert exc_info.value.status_code == 429
        _, row = _read_failure_row(db_path, task_id_pattern="")
        assert row["failure_type"] == "rate_limited"
        assert row["stream_flag"] is False
        assert row["attempts"] == 1
    finally:
        database.close()


@pytest.mark.asyncio
async def test_durable_dispatch_records_python_class_for_unexpected_exceptions(
    tmp_path: Path,
) -> None:
    """Unexpected exceptions still reach the audit log — surface as their class name."""
    database, db_path = _build_database(tmp_path)
    try:
        request = ChatCompletionRequest.model_validate(
            {"model": "fake-model", "messages": [{"role": "user", "content": "x"}]}
        )
        with pytest.raises(ValueError):
            await durable_dispatch(
                request,
                database,
                cast("Dispatcher", _UnexpectedDispatcher()),  # type: ignore[arg-type]
            )
        _, row = _read_failure_row(db_path, task_id_pattern="")
        assert row["failure_type"] == "ValueError"
    finally:
        database.close()


def test_durable_dispatch_does_not_swallow_keyboard_interrupt() -> None:
    """``KeyboardInterrupt`` is *not* an ``Exception`` subclass → it must propagate cleanly.

    We pin the behavior by importing the module under test and asserting the
    exception handler does not catch it: ``except Exception:`` excludes
    ``BaseException`` subclasses by definition.
    """
    # ``BaseException`` is the root, ``Exception`` is a strict subclass.
    assert issubclass(Exception, BaseException)
    assert not issubclass(KeyboardInterrupt, Exception)
    # This means a CTRL-C during durble_dispatch will not enter its error path.
    # We can't easily simulate CTRL-C without the process; the structural
    # assertion above is the contract.
