"""Public API routes: German control center, health, models, and chat."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from limen.api.dispatch import durable_dispatch, stream_completion
from limen.api.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ErrorResponse,
)

_UI_HTML_CACHE: str | None = None


def _load_ui_html() -> str:
    """Load the Leitstand UI template from disk, cached after first read."""
    global _UI_HTML_CACHE
    if _UI_HTML_CACHE is not None:
        return _UI_HTML_CACHE
    template_path = Path(__file__).resolve().parent.parent.parent / "templates" / "leitstand.html"
    raw = template_path.read_text(encoding="utf-8")
    if not raw.startswith("<!doctype"):
        raw = "<!doctype html>\n" + raw
    _UI_HTML_CACHE = raw
    return raw


router = APIRouter()


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def control_center() -> str:
    return _load_ui_html()


@router.get("/v1/_internal/live-visualizer", include_in_schema=False)
async def live_visualizer(request: Request) -> StreamingResponse:
    queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
    request.app.state.ui_clients.add(queue)

    async def generate() -> AsyncIterator[str]:
        try:
            yield ":ok\n\n"
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            request.app.state.ui_clients.discard(queue)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/v1/dashboard/keys")
async def dashboard_keys(request: Request) -> dict[str, object]:
    """Public endpoint: per-key health data for the Control Plane dashboard.

    Returns status, rate-limit budgets, and health metrics for all
    providers in the database — no auth required (localhost-only).
    """
    import json as _json
    from datetime import UTC, datetime

    database = request.app.state.database
    registry = request.app.state.registry

    rows = await asyncio.to_thread(
        lambda: list(database.connection.execute(
            "SELECT key_id, provider, deployment, status, cooldown_until,"
            " observed_itpm, observed_otpm, observed_rpm,"
            " error_count, success_count,"
            " meta_json, last_used_at, priority"
            " FROM providers ORDER BY priority ASC, provider ASC"
        ).fetchall())
    )

    keys: list[dict[str, object]] = []
    now = datetime.now(UTC)

    # Build in-memory KeyPool lookup for real-time health stats
    # Key: key_id → {error_count, success_count, health_score, error_rate, total_requests}
    pool_stats: dict[str, dict[str, object]] = {}
    for dep in registry.deployments:
        import hashlib as _hl
        for key in dep.pool.keys:
            fp = _hl.sha256(key.value.encode()).hexdigest()[:16]
            key_id = f"{dep.deployment}:{fp}"
            pool_stats[key_id] = {
                "error_count": key.error_count,
                "success_count": key.success_count,
                "total_requests": key.total_requests,
                "error_rate": round(key.error_rate, 4),
                "health_score": round(key.health_score, 4),
            }

    # Build a lookup of registry deployments for capability/rpm info
    dep_lookup: dict[str, object] = {}
    for dep in registry.deployments:
        dep_lookup[dep.deployment] = {
            "soft_rpm": getattr(dep, "soft_rpm", None),
            "soft_itpm": getattr(dep, "soft_itpm", None),
            "soft_otpm": getattr(dep, "soft_otpm", None),
            "capabilities": list(dep.capabilities) if hasattr(dep, "capabilities") else [],
            "model": dep.model if hasattr(dep, "model") else "",
        }

    for row in rows:
        key_id = str(row["key_id"])
        provider = str(row["provider"])
        deployment = str(row["deployment"])
        status = str(row["status"])
        cooldown_until = row["cooldown_until"]
        itpm = int(row["observed_itpm"] or 0)
        otpm = int(row["observed_otpm"] or 0)
        rpm = int(row["observed_rpm"] or 0)
        priority_val = int(row["priority"] or 1)

        # Parse meta_json for budget limits
        meta: dict[str, object] = {}
        try:
            meta_raw = row["meta_json"]
            if meta_raw:
                meta = _json.loads(str(meta_raw))
        except (_json.JSONDecodeError, TypeError):
            pass

        tokens_max = int(meta.get("tokens_max", 1_000_000))
        requests_max = int(meta.get("requests_max", 500))
        model = str(meta.get("model", ""))

        # Merge registry info if available
        reg_info = dep_lookup.get(deployment, {})
        soft_rpm = reg_info.get("soft_rpm")
        soft_itpm = reg_info.get("soft_itpm")

        # Read persisted error/success counts (fallback: 0 if column missing from v1 DB)
        db_error_count = 0
        db_success_count = 0
        try:
            db_error_count = int(row["error_count"] or 0)
            db_success_count = int(row["success_count"] or 0)
        except (IndexError, KeyError):
            pass

        # Merge with in-memory KeyPool stats (real-time, live from Key objects)
        live_stats = pool_stats.get(key_id, {})
        error_count = live_stats.get("error_count", db_error_count)
        success_count = live_stats.get("success_count", db_success_count)
        total_requests = error_count + success_count
        error_rate = live_stats.get("error_rate", (error_count / max(total_requests, 1)) if total_requests > 0 else 0.0)
        health_score = live_stats.get("health_score", 1.0 if status == "active" else 0.25 if status == "cooldown" else 0.0)

        # Calculate health: use KeyPool health_score if available, else fallback
        if status == "active":
            health_pct = round(health_score * 100, 1)
        elif status == "cooldown":
            health_pct = 25.0
        else:
            health_pct = 0.0

        # Calculate cooldown remaining seconds
        cooldown_remaining: float | None = None
        if cooldown_until and status == "cooldown":
            try:
                cooldown_dt = datetime.fromisoformat(str(cooldown_until))
                remaining = (cooldown_dt - now).total_seconds()
                cooldown_remaining = max(0.0, remaining)
            except (ValueError, OSError):
                pass

        keys.append({
            "key_id": key_id,
            "provider": provider,
            "deployment": deployment,
            "status": status,
            "cooldown_until": cooldown_until,
            "cooldown_remaining": cooldown_remaining,
            "tokens_used": itpm + otpm,
            "tokens_max": tokens_max,
            "token_pct": round((itpm + otpm) / max(tokens_max, 1) * 100, 1),
            "requests_used": rpm,
            "requests_max": requests_max,
            "request_pct": round(rpm / max(requests_max, 1) * 100, 1),
            "health_pct": round(health_pct, 1),
            "health_color": "#10b981" if health_pct > 70 else "#f59e0b" if health_pct > 30 else "#ef4444",
            "error_count": error_count,
            "success_count": success_count,
            "total_requests": total_requests,
            "error_rate": round(error_rate * 100, 1),
            "health_score": round(health_score, 4),
            "priority": priority_val,
            "model": model,
            "soft_rpm": soft_rpm,
            "soft_itpm": soft_itpm,
            "capabilities": reg_info.get("capabilities", []),
            "last_used_at": str(row["last_used_at"] or ""),
        })

    # Summary
    active = sum(1 for k in keys if k["status"] == "active")
    cooldown = sum(1 for k in keys if k["status"] == "cooldown")
    dead = sum(1 for k in keys if k["status"] == "dead")

    return {
        "available": True,
        "summary": {
            "total": len(keys),
            "active": active,
            "cooldown": cooldown,
            "dead": dead,
        },
        "keys": keys,
    }


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    app_state = request.app.state
    database = app_state.database
    registry = app_state.registry

    db_writable = await asyncio.to_thread(database.health_check)
    provider_available = bool(registry.deployments)
    active = sum(1 for d in registry.deployments if d.aggregated_status == "active")
    cooldown = sum(1 for d in registry.deployments if d.aggregated_status == "cooldown")
    dead = sum(1 for d in registry.deployments if d.aggregated_status == "dead")
    status = "ok" if db_writable and provider_available and active > 0 else "degraded"
    if not db_writable:
        status = "down"
    return {
        "status": status,
        "uptime_seconds": int(monotonic() - app_state.started_at),
        "pid": os.getpid(),
        "last_request_at": app_state.last_request_at,
        "db_writable": db_writable,
        "queue_depth": await asyncio.to_thread(database.queue_depth),
        "deployments_active": active,
        "deployments_cooldown": cooldown,
        "deployments_dead": dead,
    }


@router.get("/v1/models")
async def models(request: Request) -> dict[str, object]:
    registry = request.app.state.registry
    entries: list[dict[str, object]] = [
        {
            "id": deployment.model,
            "object": "model",
            "owned_by": deployment.provider,
            "status": deployment.aggregated_status,
            "limit_scope": deployment.limit_scope,
            "priority": deployment.priority,
            "tags": list(deployment.capabilities),
            "free": deployment.free,
            "max_context_tokens": deployment.max_context_tokens,
            "escalation_group": deployment.escalation_group,
        }
        for deployment in registry.deployments
        if deployment.model
    ]
    # Advertise "auto" as a synthetic model so CLI agents can select
    # LIMEN's automatic fallback-chain routing.
    entries.append(
        {
            "id": "auto",
            "object": "model",
            "owned_by": "limen",
            "status": "active",
            "limit_scope": "provider",
            "priority": 0,
            "tags": ["chat", "auto"],
            "free": True,
            "max_context_tokens": 131_072,
            "escalation_group": "default",
        }
    )
    return {"object": "list", "data": entries}


@router.post(
    "/v1/chat/completions",
    response_model=ChatCompletionResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def chat_completions(
    request: ChatCompletionRequest,
    req: Request,
) -> JSONResponse | StreamingResponse:
    app_state = req.app.state
    app_state.last_request_at = datetime.now(UTC).isoformat()

    request_id = uuid4().hex[:12]
    from functools import partial

    ui_event = partial(app_state.broadcast_ui_event, request_id=request_id)

    ui_event("request.arrived", model=request.model)

    # ── Admission control ──
    queue_cfg = app_state.queue_config
    queue_depth = await asyncio.to_thread(app_state.database.queue_depth)
    if queue_depth >= queue_cfg.max_pending:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "message": f"Warteschlange voll ({queue_depth}/{queue_cfg.max_pending}) — bitte später versuchen",
                    "type": "queue_full",
                    "code": "503",
                    "param": None,
                }
            },
            headers={"Retry-After": str(int(queue_cfg.max_wait_seconds))},
        )

    if request.is_streaming:
        return await stream_completion(
            request,
            app_state.registry,
            app_state.transport,
            app_state.database,
            ui_event=ui_event,
            max_attempts=int(app_state.dispatcher.max_attempts),
            correlation_id=request_id,
        )
    response = await durable_dispatch(
        request,
        app_state.database,
        app_state.dispatcher,
        ui_event=ui_event,
        correlation_id=request_id,
    )
    return JSONResponse(
        content=response.model_dump(),
        headers={"X-Request-Id": request_id},
    )
