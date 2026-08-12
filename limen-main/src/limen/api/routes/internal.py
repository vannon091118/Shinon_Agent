"""Internal audit endpoints: status, SSE event stream, and key management."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

_KEY_STORE = Path("~/.limen/keys.json").expanduser()


class KeySetRequest(BaseModel):
    key: str = Field(min_length=1, max_length=512)
    name: str = Field(default="", max_length=64)


def _read_key_store() -> dict[str, object]:
    """Read the persisted key store, returning {} if missing or corrupt.

    Values may be plain strings (legacy) or ``{key, name}`` dicts.
    """
    try:
        raw: object = json.loads(_KEY_STORE.read_text())
        return raw if isinstance(raw, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _write_key_store(data: dict[str, object]) -> None:
    import tempfile
    _KEY_STORE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=_KEY_STORE.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise
    Path(tmp).chmod(0o600)
    Path(tmp).rename(_KEY_STORE)


def _resolve_key_value(entry: object) -> str | None:
    """Extract the raw key string from a store entry (str or dict)."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        val = entry.get("key")
        return val if isinstance(val, str) else None
    return None


def resolve_key_from_store(provider: str, env_var: str) -> str | None:
    """Resolve a key: env var first, then key store fallback."""
    import os
    env_value = os.environ.get(env_var)
    if env_value:
        return env_value
    return _resolve_key_value(_read_key_store().get(provider))


def create_internal_router(audit_dep: Any) -> APIRouter:
    """Build an APIRouter for /v1/_internal endpoints with audit auth."""

    router = APIRouter()

    @router.get(
        "/v1/_internal/status",
        dependencies=[audit_dep],
    )
    async def internal_status(request: Request) -> dict[str, object]:
        app = request.app
        registry = app.state.registry
        database = app.state.database
        started_at = app.state.started_at
        last_request_at = app.state.last_request_at

        active_k = sum(1 for d in registry.deployments if d.aggregated_status == "active")

        def _fetch_beats() -> list[Any]:
            return list(database.connection.execute(
                "SELECT worker_id, last_beat_at, state, beat_count, current_task_id"
                " FROM worker_heartbeats ORDER BY last_beat_at DESC LIMIT 5"
            ).fetchall())

        beat_rows = await asyncio.to_thread(_fetch_beats)
        worker_states = [
            {
                "worker_id": row["worker_id"],
                "last_beat_at": row["last_beat_at"],
                "state": row["state"],
                "beat_count": row["beat_count"],
                "current_task_id": row["current_task_id"],
            }
            for row in beat_rows
        ]
        return {
            "activity": {
                "state": "active" if active_k > 0 else "degraded",
                "uptime_seconds": int(monotonic() - started_at),
                "last_request_at": last_request_at,
                "queue_depth": await asyncio.to_thread(database.queue_depth),
                "worker_count": 1,
            },
            "workers": worker_states,
            "deployments_active": active_k,
        }

    @router.get(
        "/v1/_internal/events",
        dependencies=[audit_dep],
    )
    async def internal_events(
        request: Request,
        since: int = Query(default=0, ge=0),
    ) -> StreamingResponse:
        database = request.app.state.database

        async def _event_stream() -> AsyncIterator[str]:
            last_id = since
            while True:
                try:
                    rows = await asyncio.to_thread(
                        database.read_events, since_id=last_id, limit=50
                    )
                except (OSError, RuntimeError):
                    await asyncio.sleep(1.0)
                    continue
                for row in rows:
                    event_id = int(str(row["id"]))
                    event_type = str(row["event_type"])
                    payload = str(row["payload_json"])
                    data = json.dumps({
                        "id": event_id,
                        "event": event_type,
                        "data": payload,
                        "timestamp": str(row.get("timestamp", "")),
                        "correlation_id": str(row.get("correlation_id", "")),
                    })
                    yield f"id: {event_id}\ndata: {data}\n\n"
                    last_id = max(last_id, event_id)
                await asyncio.sleep(0.5)

        return StreamingResponse(
            _event_stream(),
            media_type="text/event-stream; charset=utf-8",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
            },
        )

    @router.post(
        "/v1/_internal/keys/{provider}",
        dependencies=[audit_dep],
    )
    async def set_provider_key(provider: str, body: KeySetRequest) -> dict[str, str]:
        if not provider or "/" in provider or ".." in provider:
            raise HTTPException(status_code=400, detail="invalid provider name")
        store = _read_key_store()
        store[provider] = {"key": body.key, "name": body.name.strip() or provider}
        _write_key_store(store)
        return {"status": "stored", "provider": provider}

    @router.get(
        "/v1/_internal/keys",
        dependencies=[audit_dep],
    )
    async def list_stored_keys() -> dict[str, list[str]]:
        store = _read_key_store()
        return {"providers": sorted(store.keys())}

    @router.get(
        "/v1/_internal/keys/{provider}/name",
        dependencies=[audit_dep],
    )
    async def get_key_name(provider: str) -> dict[str, str]:
        entry = _read_key_store().get(provider)
        if isinstance(entry, dict):
            return {"name": str(entry.get("name", provider))}
        return {"name": provider}

    @router.get(
        "/v1/_internal/keys/names",
        dependencies=[audit_dep],
    )
    async def get_all_key_names() -> dict[str, object]:
        store = _read_key_store()
        names: dict[str, str] = {}
        for prov, entry in store.items():
            if isinstance(entry, dict) and entry.get("name"):
                names[prov + "#1"] = str(entry["name"])
        return {"names": names}

    @router.post(
        "/v1/_internal/claude-config",
        dependencies=[audit_dep],
    )
    async def write_claude_config(request: Request) -> dict[str, str]:
        """Write ~/.claude/settings.json pointing at this LIMEN instance."""
        import json as _json
        from pathlib import Path as _Path

        config_path = _Path("~/.claude/settings.json").expanduser()
        port = request.app.state.config.server.port
        config = {
            "env": {
                "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{port}",
                "ANTHROPIC_API_KEY": "limen-no-auth-required",
                "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1",
            },
        }
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(_json.dumps(config, indent=2) + "\n")
        return {"status": "written", "path": str(config_path)}

    return router
