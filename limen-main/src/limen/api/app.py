"""FastAPI application for the LIMEN foundation."""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from time import monotonic
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from limen import __version__
from limen.api.middleware import BodySizeLimitMiddleware
from limen.api.routes.anthropic import router as anthropic_router
from limen.api.routes.codex import router as codex_router
from limen.api.routes.internal import create_internal_router
from limen.api.routes.public import router as public_router
from limen.api.schemas import ErrorEnvelope, ErrorResponse
from limen.persistence import Database
from limen.queue import QueueWorker
from limen.routing import Dispatcher
from limen.routing.registry import ProviderRegistry
from limen.transport import HttpTransport

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from limen.config import LimenConfig


# ── Audit auth dependency ─────────────────────────────────────────────


def verify_audit_token(request: Request) -> None:
    """Reject requests without a valid X-Proxy-Audit-Key header."""
    token = request.app.state.audit_token
    if not token:
        raise HTTPException(status_code=401, detail="audit not configured")
    provided = request.headers.get("X-Proxy-Audit-Key", "")
    if provided != token:
        raise HTTPException(status_code=401, detail="invalid audit token")


AuditDep = Depends(verify_audit_token)


# ── App factory ───────────────────────────────────────────────────────


def create_app(config: LimenConfig) -> FastAPI:
    """Create an application with database, transport, and registry lifecycle."""
    if config.audit.audit_token_secret == "REPLACE_ME_WITH_RANDOM_HEX":  # noqa: S105
        print(
            "[limen] WARNUNG: audit_token_secret ist noch der Beispiel-Wert "
            "'REPLACE_ME_WITH_RANDOM_HEX'.\n"
            "        Ersetze ihn in ~/.config/limen/config.toml mit einem "
            "zufälligen Hex-String (z.B. openssl rand -hex 32).",
            file=sys.stderr,
        )
    database = Database(
        config.database.path,
        busy_timeout_ms=config.database.busy_timeout_ms,
        sync_mode=config.database.sync_mode,
    )
    transport = HttpTransport(config)
    registry = ProviderRegistry(config)
    retry_max_attempts = int(config.raw.get("retry", {}).get("max_attempts", 10))
    dispatcher = Dispatcher(
        registry,
        transport,
        audit_writer=database.write_event,
        max_attempts=retry_max_attempts,
    )

    def _ui_broadcast(event_type: str, **extra: object) -> None:
        payload: dict[str, object] = {"type": event_type, "ts": monotonic(), **extra}
        for client_q in app.state.ui_clients:
            try:
                client_q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    worker = QueueWorker(database, dispatcher, ui_event=_ui_broadcast)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.open()
        # ── Recover persisted key states (cooldowns, dead keys) ──
        try:
            persisted = database.recover_key_states()
            for deployment_name, key_states in persisted.items():
                for dep in registry.deployments:
                    if dep.deployment == deployment_name:
                        dep.pool.restore_persisted_states(key_states, deployment=deployment_name)
                        break
        except (OSError, RuntimeError):
            pass  # recovery is best-effort
        await transport.open()
        await worker.start()
        try:
            yield
        finally:
            await worker.stop()
            await transport.close()
            database.close()

    app = FastAPI(title="LIMEN", version=__version__, lifespan=lifespan)
    app.state.database = database
    app.state.dispatcher = dispatcher
    app.state.registry = registry
    app.state.transport = transport
    app.state.worker = worker
    app.state.audit_token = config.audit.audit_token_secret
    app.state.started_at = monotonic()
    app.state.last_request_at = None
    app.state.ui_clients = set()
    app.state.broadcast_ui_event = _ui_broadcast
    app.state.config = config
    app.state.queue_config = config.queue

    app.add_middleware(
        BodySizeLimitMiddleware,
        max_bytes=config.server.max_body_size_kb * 1024,
    )

    @app.exception_handler(HTTPException)
    async def _render_error(_: Request, exception: HTTPException) -> JSONResponse:
        envelope = _render_envelope(exception)
        response = JSONResponse(status_code=exception.status_code, content=envelope)
        retry_after = exception.headers.get("Retry-After") if exception.headers else None
        if retry_after:
            response.headers["Retry-After"] = retry_after
        return response

    app.include_router(public_router)
    app.include_router(anthropic_router)
    app.include_router(codex_router)
    app.include_router(create_internal_router(AuditDep))

    return app


# ── Error rendering ──────────────────────────────────────────────────


def _render_envelope(exception: HTTPException) -> dict[str, object]:
    detail = exception.detail
    if isinstance(detail, dict):
        inner = detail.get("error")
        if isinstance(inner, dict) and {"message", "type"} <= inner.keys():
            return detail
        if {"message", "type"} <= detail.keys():
            return {"error": detail}
    message = str(detail) if detail is not None else exception.__class__.__name__
    envelope = ErrorResponse(
        error=ErrorEnvelope(
            message=message,
            type=exception.__class__.__name__,
            code=str(exception.status_code),
            param=None,
        )
    )
    return envelope.to_dict()
