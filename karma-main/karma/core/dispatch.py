"""
KARMA Dispatch Gate — Deterministic Write Control

Ported from LifeGameLab BioEmergenzia/src/kernel/store.js
DNA: dispatch() as single write entry, mutationMatrix, assertPatchesAllowed.

Principle: "Prompter hat KEINEN Code-Zugriff" — enforced mechanically.
Only explicitly allowed paths can be written to. No path → no write. Point.
"""

import hashlib
import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from karma.core.persistence import PersistenceLayer

logger = logging.getLogger(__name__)


# ─── Deterministic JSON (stableStringify) ────────────────────────────

def stable_stringify(value: Any) -> str:
    """Deterministic JSON stringify with sorted object keys.

    Ported from LifeGameLab stableStringify.js.
    Same output for semantically identical inputs regardless of key order.
    Used for fingerprinting and replay drift detection.
    """
    return _stringify(value)


def _stringify(v: Any) -> str:
    if v is None:
        return "null"
    t = type(v)
    if t is bool:
        return "true" if v else "false"
    if t in (int, float):
        if t is float and not (float("-inf") < v < float("inf")):
            return "null"
        return str(v)
    if t is str:
        return json.dumps(v, ensure_ascii=False)
    if t in (list, tuple):
        return "[" + ",".join(_stringify(item) for item in v) + "]"
    if t is dict:
        keys = sorted(v.keys())
        parts = [json.dumps(k, ensure_ascii=False) + ":" + _stringify(v[k]) for k in keys]
        return "{" + ",".join(parts) + "}"
    # undefined / function / symbol → null
    return "null"


def hash32(value: str) -> str:
    """SHA-256 based hash, returns first 8 hex chars (32-bit equiv).

    Ported from LifeGameLab hash32.js.
    """
    return hashlib.sha256(value.encode()).hexdigest()[:8]


# ─── RNG: xorshift32 with salted streams ────────────────────────────

def _xorshift32(seed: int):
    """xorshift32 PRNG. Deterministic, seed-replayable."""
    x = seed & 0xFFFFFFFF

    def next_u32() -> int:
        nonlocal x
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        return x & 0xFFFFFFFF

    return next_u32


class RngStream:
    """A single deterministic RNG stream for one domain (world/sim/cos)."""

    def __init__(self, base_seed: int, salt: str):
        salted = base_seed ^ (int(hash32(f"{base_seed}:{salt}"), 16) & 0xFFFFFFFF)
        self._gen = _xorshift32(salted if salted else 0x12345678)

    def u32(self) -> int:
        return self._gen()

    def f01(self) -> float:
        return self._gen() / 4294967296.0

    def int_range(self, lo: int, hi: int) -> int:
        """Inclusive lo, exclusive hi."""
        r = self._gen() / 4294967296.0
        return int(lo + r * (hi - lo))


class DeterministicRng:
    """Deterministic RNG with salted streams.

    Ported from LifeGameLab rng.js — xorshift32, salted streams world/sim/cos.
    Used by KARMA ReplayEngine for seed-based replay.
    """

    def __init__(self, seed: str = ""):
        base = int(hash32(str(seed)), 16) & 0xFFFFFFFF
        self.world = RngStream(base, "world")
        self.sim = RngStream(base, "sim")
        self.cos = RngStream(base, "cos")


# ─── Patch Operations ────────────────────────────────────────────────

@dataclass
class Patch:
    op: str          # "set" | "inc" | "push" | "del"
    path: str        # JSON Pointer, e.g. "/facts/key"
    value: Any = None
    amount: float = 1.0


def apply_patches(base_state: Dict, patches: List[Patch]) -> Dict:
    """Apply a list of patches to base_state, returning a new state dict.

    Immutable updates with shallow copies along the path.
    Ported from LifeGameLab patches.js.
    """
    if not isinstance(patches, list):
        raise TypeError("Patches must be a list")

    next_state = base_state
    for i, p in enumerate(patches):
        if not isinstance(p, Patch):
            raise TypeError(f"Patch at index {i} must be a Patch")
        next_state = _apply_one(next_state, p)
    return next_state


def _apply_one(state: Dict, p: Patch) -> Dict:
    parts = [unescape_json_pointer(seg) for seg in p.path.split("/")[1:]]
    if not parts:
        return state

    # Build clone path
    stack = []
    cur = state
    for i in range(len(parts) - 1):
        k = parts[i]
        stack.append((cur, k))
        cur = cur.get(k) if isinstance(cur, dict) else None
        if cur is None:
            cur = {}

    leaf_key = parts[-1]

    # Clone root
    out = _clone_container(state)
    out_cur = out
    for parent, k in stack:
        prev_val = parent.get(k) if isinstance(parent, dict) else None
        cloned = _clone_container(prev_val)
        out_cur[k] = cloned
        out_cur = cloned

    prev_val = out_cur.get(leaf_key) if isinstance(out_cur, dict) else None

    if p.op == "set":
        out_cur[leaf_key] = p.value
    elif p.op == "inc":
        amt = float(p.amount) if isinstance(p.amount, (int, float)) else 1.0
        base = float(prev_val) if isinstance(prev_val, (int, float)) else 0.0
        out_cur[leaf_key] = base + amt
    elif p.op == "push":
        arr = list(prev_val) if isinstance(prev_val, list) else []
        arr.append(p.value)
        out_cur[leaf_key] = arr
    elif p.op == "del":
        if isinstance(out_cur, list):
            try:
                idx = int(leaf_key)
                out_cur.pop(idx)
            except (ValueError, IndexError):
                pass
        elif isinstance(out_cur, dict):
            out_cur.pop(leaf_key, None)
    else:
        raise ValueError(f"Unknown patch op: {p.op}")
    return out


def _clone_container(v: Any) -> Any:
    if isinstance(v, list):
        return list(v)
    if isinstance(v, dict):
        return dict(v)
    return {}


def unescape_json_pointer(s: str) -> str:
    return s.replace("~1", "/").replace("~0", "~")


def assert_patches_allowed(patches: List[Patch], allowed_prefixes: List[str]) -> None:
    """Enforce that every patch path starts with an allowed prefix.

    Ported from LifeGameLab patches.js assertPatchesAllowed.
    The mechanical enforcement of "Prompter hat KEINEN Code-Zugriff".
    """
    if not isinstance(patches, list):
        raise TypeError("Patches must be a list")
    prefixes = list(allowed_prefixes) if isinstance(allowed_prefixes, list) else []

    for p in patches:
        if not isinstance(p, Patch):
            raise TypeError("Patch must be a Patch object")
        path = p.path
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError(f"Patch path invalid: {path}")

        allowed = any(
            isinstance(pref, str) and (
                path == pref or path.startswith(pref + "/" if not pref.endswith("/") else pref)
            )
            for pref in prefixes
        )
        if not allowed:
            raise PermissionError(f"Patch path not allowed: {path}")


# ─── Schema Validation (sanitizeBySchema) ──────────────────────────

# Schema definition uses a simple dict-based DSL compatible with
# LifeGameLab schema.js. Types: string, number, boolean, enum, array, object.
SchemaDef = Dict[str, Any]


def sanitize_by_schema(value: Any, schema: Optional[SchemaDef]) -> Any:
    """Validate and coerce value to match schema.

    Ported from LifeGameLab schema.js sanitizeBySchema().
    Returns sanitized value with defaults, clamping, and type coercion.
    Never raises — always returns a valid value per schema.
    """
    if not schema:
        return value
    stype = schema.get("type", "any")

    if stype == "string":
        out = value if isinstance(value, str) else schema.get("default", "")
        if not isinstance(out, str):
            out = str(out)
        max_len = schema.get("maxLen")
        if isinstance(max_len, int) and max_len > 0:
            out = out[:max_len]
        return out

    if stype == "number":
        out = value if (isinstance(value, (int, float)) and not (isinstance(value, float) and not (float("-inf") < value < float("inf")))) else schema.get("default", 0)
        if not isinstance(out, (int, float)):
            out = 0
        mn = schema.get("min")
        mx = schema.get("max")
        if isinstance(mn, (int, float)):
            out = max(mn, out)
        if isinstance(mx, (int, float)):
            out = min(mx, out)
        if schema.get("int"):
            out = int(out)
        return out

    if stype == "boolean":
        return bool(value) if isinstance(value, bool) else schema.get("default", False)

    if stype == "enum":
        allowed = schema.get("values", [])
        if not isinstance(allowed, list):
            allowed = []
        if value in allowed:
            return value
        default = schema.get("default")
        return default if default is not None else (allowed[0] if allowed else None)

    if stype == "array":
        arr = list(value) if isinstance(value, (list, tuple)) else (list(schema.get("default", [])) if isinstance(schema.get("default"), (list, tuple)) else [])
        item_schema = schema.get("items")
        max_len = schema.get("maxLen", float("inf"))
        if not isinstance(max_len, (int, float)) or max_len < 0:
            max_len = float("inf")
        arr = arr[:int(max_len)]
        return [sanitize_by_schema(item, item_schema) for item in arr]

    if stype == "object":
        shape = schema.get("shape", {})
        if not isinstance(shape, dict):
            shape = {}
        src = value if (isinstance(value, dict) and not isinstance(value, list)) else schema.get("default", {})
        if not isinstance(src, dict):
            src = {}
        out = {}
        for key, field_schema in shape.items():
            out[key] = sanitize_by_schema(src.get(key), field_schema)
        return out

    # unknown type — pass through unchanged
    return value


# ─── Action / Mutation Matrix ────────────────────────────────────────

MUTATION_MATRIX: Dict[str, List[str]] = {
    "RECORD_EXPERIENCE": ["/experiences", "/karma_executions"],
    "UPDATE_CLAIM":      ["/claims"],
    "FALSIFY":           ["/claims", "/karma_executions"],
    "SET_FACT":          ["/facts"],
    "LOG_EVENT":         ["/execution_log", "/events"],
    "UPDATE_MEMORY":     ["/shinon_memory"],
    # No path → no write. Point.
}


@dataclass
class Action:
    type: str
    payload: Dict[str, Any] = field(default_factory=dict)


# ─── Dispatch Gate ───────────────────────────────────────────────────

ReducerFn = Callable[[Dict, Action, DeterministicRng], List[Patch]]


class DispatchGate:
    """Single write entry point for KARMA state.

    Ported from LifeGameLab store.js dispatch().
    All writes go through here. No direct DB access outside dispatch().

    Thread safety: dispatch() is safe for concurrent callers (DB writes
    go through PersistenceLayer transactions). _listeners iteration is
    NOT thread-safe — subscribe/unsubscribe before concurrent dispatch.

    Usage:
        gate = DispatchGate(persistence)
        action = Action("SET_FACT", {"domain": "karma", "key": "test", "value": 42})
        gate.dispatch(action)
    """

    def __init__(self, persistence: PersistenceLayer, reducer: Optional[ReducerFn] = None):
        self.persistence = persistence
        self._reducer = reducer or _default_reducer
        self._listeners: Set[Callable] = set()
        self._lock = threading.Lock()
        self._state_version = 0
        self._rng = DeterministicRng()

    def dispatch(self, action: Action) -> Tuple[Dict, List[Patch]]:
        """THE single write entry. All state changes go through here.

        Returns:
            (next_state, patches) — the resulting state and the patches
            that were applied. This allows recorders/wrappers to capture
            patches without re-computing them via the reducer.
        """
        # Validate action
        if not isinstance(action, Action):
            raise TypeError("Action must be an Action object")
        if not isinstance(action.type, str) or not action.type:
            raise ValueError("Action.type must be a non-empty string")

        # Get allowed paths from mutation matrix
        allowed = MUTATION_MATRIX.get(action.type, [])
        if not allowed:
            raise PermissionError(f"Unknown action type: {action.type}")

        # Let reducer produce patches
        current_state = self.persistence.get_all_memory(
            self.persistence.get_active_project()
        )
        patches = self._reducer(current_state, action, self._rng)

        if not isinstance(patches, list):
            raise TypeError("Reducer must return a list of patches")

        if not patches:
            logger.warning("Reducer returned empty patches for action %s", action.type)

        # ENFORCE write gate
        assert_patches_allowed(patches, allowed)

        # Apply patches to state
        next_state = apply_patches(
            current_state if current_state else {},
            patches
        )

        # Persist all patches to appropriate persistence targets
        project = self.persistence.get_active_project()
        self._persist_patches(project, patches)

        # Emit event for audit trail
        self.persistence.emit_event(
            "dispatch.executed",
            project,
            {
                "action_type": action.type,
                "patch_count": len(patches),
                "state_version": self._state_version + 1,
            },
            correlation_id=action.payload.get("correlation_id"),
        )

        self._state_version += 1
        self._notify()

        return next_state, patches

    def _persist_patches(self, project: str, patches: List[Patch]) -> None:
        """Route each patch to the correct persistence target.

        Persistence adapters:
          /facts/             → facts table (karma domain)
          /claims/            → facts table (claims domain)
          /karma_executions/  → facts table (karma_executions domain)
          /shinon_memory/     → facts table (shinon_memory domain)
          /experiences/       → emit_event
          /events/            → emit_event
        """
        for p in patches:
            path = p.path
            if path.startswith("/facts/"):
                key = path[len("/facts/"):]
                if p.op == "set":
                    self.persistence.set_fact(project, "karma", key, p.value)
                elif p.op == "del":
                    self.persistence.delete_fact(project, "karma", key)
                else:
                    logger.warning("Unsupported op %s for /facts/ patch", p.op)
            elif path.startswith("/claims/"):
                # Claims: persist as karma facts in domain "claims"
                # Path format: /claims/{claim_id}/{field}
                parts = path.split("/")
                if len(parts) >= 4:
                    claim_id = parts[2]
                    field = parts[3]
                    if p.op == "set":
                        self.persistence.set_internal_fact(project, "claims", f"{claim_id}/{field}", p.value)
                    elif p.op == "del":
                        self.persistence.delete_fact(project, "claims", f"{claim_id}/{field}")
                else:
                    logger.debug("Skipping malformed /claims/ path: %s (expected /claims/{id}/{field})", path)
            elif path.startswith("/karma_executions/"):
                parts = path.split("/")
                if len(parts) >= 3:
                    execution_id = parts[2]
                    if p.op == "set":
                        self.persistence.set_internal_fact(project, "karma_executions", execution_id, p.value)
            elif path.startswith("/shinon_memory/"):
                # Shinon memory: persist as karma facts in domain "shinon_memory"
                # Path format: /shinon_memory/{session_id}/{key}
                parts = path.split("/")
                if len(parts) >= 4:
                    session_id = parts[2]
                    key = parts[3]
                    if p.op == "set":
                        self.persistence.set_internal_fact(project, "shinon_memory", f"{session_id}/{key}", p.value)
                    elif p.op == "del":
                        self.persistence.delete_fact(project, "shinon_memory", f"{session_id}/{key}")
                else:
                    logger.debug("Skipping malformed /shinon_memory/ path: %s (expected /shinon_memory/{session_id}/{key})", path)
            elif path.startswith("/experiences/") or path.startswith("/events/"):
                if p.op == "set":
                    self.persistence.emit_event(
                        "patch.persisted", project,
                        {"path": path, "op": p.op},
                    )
            else:
                logger.warning(
                    "Patch to %s not persisted — no adapter for this domain", path
                )

    def subscribe(self, fn: Callable) -> Callable:
        """Subscribe to state changes. Returns unsubscribe function."""
        with self._lock:
            self._listeners.add(fn)
        return lambda: self._unsubscribe(fn)

    def _unsubscribe(self, fn: Callable) -> None:
        with self._lock:
            self._listeners.discard(fn)

    def _notify(self):
        with self._lock:
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn()
            except Exception:
                pass

    @property
    def version(self) -> int:
        return self._state_version


def _default_reducer(state: Dict, action: Action, rng: DeterministicRng) -> List[Patch]:
    """Default reducer — maps Action.type to patches.

    Each domain module can override this with its own reducer logic.
    """
    patches: List[Patch] = []

    if action.type == "SET_FACT":
        domain = action.payload.get("domain", "karma")
        key = action.payload.get("key", "")
        value = action.payload.get("value")
        patches.append(Patch(op="set", path=f"/facts/{domain}/{key}", value=value))

    elif action.type == "RECORD_EXPERIENCE":
        exp_id = action.payload.get("id", "")
        patches.append(Patch(
            op="set",
            path=f"/experiences/{exp_id}",
            value=action.payload
        ))

    elif action.type == "UPDATE_CLAIM":
        claim_id = action.payload.get("claim_id", "")
        status = action.payload.get("status", "unverified")
        claim_text = action.payload.get("claim", "")
        patches.append(Patch(
            op="set",
            path=f"/claims/{claim_id}/status",
            value=status
        ))
        patches.append(Patch(
            op="set",
            path=f"/claims/{claim_id}/text",
            value=claim_text
        ))

    elif action.type == "FALSIFY":
        claim_id = action.payload.get("claim_id", "")
        result = action.payload.get("result", "unverified")
        confidence = action.payload.get("confidence", 0.5)
        evidence = action.payload.get("evidence", [])
        patches.append(Patch(
            op="set",
            path=f"/claims/{claim_id}/status",
            value=result
        ))
        patches.append(Patch(
            op="set",
            path=f"/claims/{claim_id}/confidence",
            value=confidence
        ))
        patches.append(Patch(
            op="set",
            path=f"/claims/{claim_id}/evidence",
            value=evidence
        ))
        patches.append(Patch(
            op="set",
            path=f"/karma_executions/{claim_id}",
            value={
                "claim_id": claim_id,
                "result": result,
                "confidence": confidence,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ))

    elif action.type == "UPDATE_MEMORY":
        session_id = action.payload.get("session_id", "")
        key = action.payload.get("key", "")
        value = action.payload.get("value")
        if key and session_id:
            patches.append(Patch(
                op="set",
                path=f"/shinon_memory/{session_id}/{key}",
                value=value
            ))

    return patches
