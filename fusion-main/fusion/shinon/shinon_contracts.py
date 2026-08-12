"""
Shinon Contract Gates — Fail-closed input/output/action validation

Every gate fails CLOSED: invalid input → ValueError, not silent pass-through.
stableSerialize ensures deterministic validation (sorted keys, no circular refs).

Scope: 0.3.0  |  Canonical: fusion-main/fusion/shinon/ (ex-TypeScript port)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple, Union


# ─── Types ────────────────────────────────────────────────────────────

ChatRole = str  # "system" | "user" | "assistant"
ChatHistoryEntry = Dict[str, str]

ValidatedAssistantPayload = Dict[str, Any]

ParseResult = Union[
    Dict[str, Any],  # {"success": True, "data": ...}
    Dict[str, Any],  # {"success": False, "error": ...}
]


# ─── Validation Primitives ────────────────────────────────────────────


def _fail_closed(gate: str, message: str) -> None:
    """Fail closed: raise ValueError immediately on invalid input."""
    raise ValueError(f"{gate}: {message}")


def _is_plain_object(value: Any) -> bool:
    """Check if value is a plain dict (not a list, not None, not a primitive)."""
    return isinstance(value, dict)


def _is_non_empty_string(value: Any) -> bool:
    """Check if value is a non-empty string."""
    return isinstance(value, str) and len(value.strip()) > 0


def _normalize_string(value: Any, field_name: str, gate: str) -> str:
    """Validate and trim a required non-empty string field."""
    if not _is_non_empty_string(value):
        _fail_closed(gate, f"{field_name} must be a non-empty string")
    return value.strip()


def _normalize_optional_string(value: Any, field_name: str, gate: str) -> Optional[str]:
    """Validate an optional string field."""
    if value is None:
        return None
    if not _is_non_empty_string(value):
        _fail_closed(gate, f"{field_name} must be a non-empty string when present")
    return value.strip()


def _normalize_history_entry(entry: Any, index: int, gate: str) -> ChatHistoryEntry:
    """Validate a single chat history entry."""
    if not _is_plain_object(entry):
        _fail_closed(gate, f"turn.history[{index}] must be a plain object")

    role = entry.get("role", "")
    if role not in ("system", "user", "assistant"):
        _fail_closed(gate, f"turn.history[{index}].role must be system, user, or assistant")

    content = _normalize_string(
        entry.get("content", ""), f"turn.history[{index}].content", gate
    )

    return {"role": role, "content": content}


def _normalize_turn(candidate: Any, gate: str) -> Dict[str, Any]:
    """Validate a full chat turn (userText + history)."""
    if not _is_plain_object(candidate):
        _fail_closed(gate, "turn must be a plain object")

    user_text = _normalize_string(candidate.get("userText", ""), "turn.userText", gate)

    history_raw = candidate.get("history", [])
    if not isinstance(history_raw, list):
        _fail_closed(gate, "turn.history must be an array")

    history = [_normalize_history_entry(entry, i, gate) for i, entry in enumerate(history_raw)]

    # Optional request metadata
    request = candidate.get("request")
    if request is not None:
        if not _is_plain_object(request):
            _fail_closed(gate, "turn.request must be a plain object when present")
        for field in ("sessionId", "conversationId", "requestId"):
            val = request.get(field)
            if val is not None and not _is_non_empty_string(val):
                _fail_closed(gate, f"turn.request.{field} must be a non-empty string when present")

    return {
        "requestId": _normalize_optional_string(candidate.get("requestId"), "turn.requestId", gate),
        "sessionId": _normalize_optional_string(candidate.get("sessionId"), "turn.sessionId", gate),
        "conversationId": _normalize_optional_string(candidate.get("conversationId"), "turn.conversationId", gate),
        "userText": user_text,
        "history": history,
    }


def _normalize_memory_context(candidate: Any, gate: str) -> Dict[str, Any]:
    """Validate memory context as a plain dict."""
    if not _is_plain_object(candidate):
        _fail_closed(gate, "memoryContext must be a plain object")
    return dict(candidate)


# ─── stableSerialize ──────────────────────────────────────────────────


def stable_serialize(value: Any, seen: Optional[set] = None) -> str:
    """Deterministic JSON-like serialization with sorted keys.

    Ported from TypeScript stableSerialize. Ensures that two objects
    with the same data produce the same string representation,
    regardless of key order. Detects circular references.

    Args:
        value: Any JSON-serializable value
        seen: Set of object ids for circular reference detection

    Returns:
        Deterministic string representation
    """
    if seen is None:
        seen = set()

    if value is None:
        return "null"

    if isinstance(value, str):
        return json.dumps(value)

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, list):
        items = [stable_serialize(item, seen) for item in value]
        return f"[{','.join(items)}]"

    if isinstance(value, dict):
        obj_id = id(value)
        if obj_id in seen:
            _fail_closed("stableSerialize", "circular reference detected")
        seen.add(obj_id)

        sorted_keys = sorted(value.keys())
        parts = [
            f"{json.dumps(k)}:{stable_serialize(value[k], seen)}"
            for k in sorted_keys
        ]
        seen.discard(obj_id)
        return f"{{{','.join(parts)}}}"

    # Fallback for unsupported types
    return json.dumps(str(value))


def _summarize_memory_context(memory_context: Dict[str, Any]) -> str:
    """Create a deterministic summary string for a memory context."""
    entries = [
        f"{k}={stable_serialize(memory_context[k])}"
        for k in sorted(memory_context.keys())
    ]
    return " | ".join(entries)


def _build_prompt(turn: Dict[str, Any], memory_context: Dict[str, Any], gate: str) -> str:
    """Build a validation prompt from turn + memory context."""
    history = turn.get("history", [])
    history_block = "\n".join(
        f"{entry['role'].upper()}: {entry['content']}"
        for entry in history
    ) if history else "HISTORY: <empty>"

    memory_summary = _summarize_memory_context(memory_context)

    extra = ""
    if gate == "actionSchema":
        extra = " and allowed actions"

    return "\n".join([
        f"SYSTEM: Validate assistant payload{extra}.",
        f"USER: {turn['userText']}",
        history_block,
        memory_summary if memory_summary else "MEMORY: <empty>",
    ])


def _build_model_name(memory_context: Dict[str, Any], prompt: str) -> str:
    """Determine model name from context hint or prompt length."""
    model_hint = memory_context.get("modelHint", "")
    if isinstance(model_hint, str) and model_hint.strip():
        return model_hint.strip()
    return "orchestrator-long" if len(prompt) > 1800 else "orchestrator-default"


def _build_validated_payload(
    turn: Dict[str, Any],
    memory_context: Dict[str, Any],
    gate: str,
) -> ValidatedAssistantPayload:
    """Build the validated assistant payload."""
    prompt = _build_prompt(turn, memory_context, gate)
    return {
        "reply": turn["userText"],
        "message": {
            "role": "assistant",
            "content": turn["userText"],
        },
        "source": "orchestrator",
        "model": _build_model_name(memory_context, prompt),
        "prompt": prompt,
        "guardrailStatus": "validated",
    }


# ─── inputSchema ──────────────────────────────────────────────────────


def validate_input(input_data: Any) -> ValidatedAssistantPayload:
    """Validate an input payload against inputSchema (fail-closed).

    Required fields:
      - input.turn (plain object with userText + history)
      - input.memoryContext (plain object)

    Args:
        input_data: Raw input payload

    Returns:
        ValidatedAssistantPayload

    Raises:
        ValueError: On any validation failure
    """
    gate = "inputSchema"

    if not _is_plain_object(input_data):
        _fail_closed(gate, "input must be a plain object")

    if "turn" not in input_data:
        _fail_closed(gate, "input.turn is required")
    if "memoryContext" not in input_data:
        _fail_closed(gate, "input.memoryContext is required")

    turn = _normalize_turn(input_data["turn"], gate)
    memory_context = _normalize_memory_context(input_data["memoryContext"], gate)
    return _build_validated_payload(turn, memory_context, gate)


def safe_validate_input(input_data: Any) -> Dict[str, Any]:
    """Validate input with safe parse (returns {success, data/error}).

    Never raises — always returns a result dict.
    """
    try:
        return {"success": True, "data": validate_input(input_data)}
    except (ValueError, TypeError) as e:
        return {"success": False, "error": str(e)}


# ─── outputSchema ─────────────────────────────────────────────────────


def validate_output(output_data: Any) -> ValidatedAssistantPayload:
    """Validate an output payload against outputSchema (fail-closed).

    Required fields:
      - output.turn (plain object with userText + history)
      - output.memoryContext (plain object)

    Args:
        output_data: Raw output payload

    Returns:
        ValidatedAssistantPayload

    Raises:
        ValueError: On any validation failure
    """
    gate = "outputSchema"

    if not _is_plain_object(output_data):
        _fail_closed(gate, "output must be a plain object")

    if "turn" not in output_data:
        _fail_closed(gate, "output.turn is required")
    if "memoryContext" not in output_data:
        _fail_closed(gate, "output.memoryContext is required")

    turn = _normalize_turn(output_data["turn"], gate)
    memory_context = _normalize_memory_context(output_data["memoryContext"], gate)
    return _build_validated_payload(turn, memory_context, gate)


def safe_validate_output(output_data: Any) -> Dict[str, Any]:
    """Validate output with safe parse (returns {success, data/error})."""
    try:
        return {"success": True, "data": validate_output(output_data)}
    except (ValueError, TypeError) as e:
        return {"success": False, "error": str(e)}


# ─── actionSchema ─────────────────────────────────────────────────────


def _normalize_allowed_actions(memory_context: Dict[str, Any], gate: str) -> List[str]:
    """Extract and validate allowed actions from memory context."""
    candidate = memory_context.get("allowedActions")
    if candidate is None:
        return []

    if not isinstance(candidate, list):
        _fail_closed(gate, "memoryContext.allowedActions must be an array when present")

    normalized = []
    for i, entry in enumerate(candidate):
        if not _is_non_empty_string(entry):
            _fail_closed(gate, f"memoryContext.allowedActions[{i}] must be a non-empty string")
        normalized.append(entry.strip())

    return normalized


def _validate_declared_actions(memory_context: Dict[str, Any], gate: str) -> None:
    """Validate that declared actions are in the allowed set."""
    allowed = _normalize_allowed_actions(memory_context, gate)
    candidate = memory_context.get("actions")

    if candidate is None:
        return

    if not isinstance(candidate, list):
        _fail_closed(gate, "memoryContext.actions must be an array when present")

    if len(candidate) == 0:
        return

    if len(allowed) == 0:
        _fail_closed(gate, "memoryContext.actions are not allowed without memoryContext.allowedActions")

    for i, action in enumerate(candidate):
        if not _is_plain_object(action):
            _fail_closed(gate, f"memoryContext.actions[{i}] must be a plain object")

        action_type = action.get("type", "")
        if not _is_non_empty_string(action_type):
            _fail_closed(gate, f"memoryContext.actions[{i}].type must be a non-empty string")

        if action_type.strip() not in allowed:
            _fail_closed(gate, f"memoryContext.actions[{i}].type is not allowed")

        args = action.get("args")
        if args is not None and not _is_plain_object(args):
            _fail_closed(gate, f"memoryContext.actions[{i}].args must be a plain object when present")

        target = action.get("target")
        if target is not None and not _is_non_empty_string(target):
            _fail_closed(gate, f"memoryContext.actions[{i}].target must be a non-empty string when present")


def validate_actions(input_data: Any) -> ValidatedAssistantPayload:
    """Validate an action payload against actionSchema (fail-closed).

    In addition to inputSchema checks, also validates:
      - allowedActions list in memoryContext
      - actions declared must be in allowedActions

    Args:
        input_data: Raw action payload

    Returns:
        ValidatedAssistantPayload

    Raises:
        ValueError: On any validation failure
    """
    gate = "actionSchema"

    if not _is_plain_object(input_data):
        _fail_closed(gate, "input must be a plain object")

    if "turn" not in input_data:
        _fail_closed(gate, "input.turn is required")
    if "memoryContext" not in input_data:
        _fail_closed(gate, "input.memoryContext is required")

    turn = _normalize_turn(input_data["turn"], gate)
    memory_context = _normalize_memory_context(input_data["memoryContext"], gate)
    _validate_declared_actions(memory_context, gate)
    return _build_validated_payload(turn, memory_context, gate)


def safe_validate_actions(input_data: Any) -> Dict[str, Any]:
    """Validate actions with safe parse (returns {success, data/error})."""
    try:
        return {"success": True, "data": validate_actions(input_data)}
    except (ValueError, TypeError) as e:
        return {"success": False, "error": str(e)}


# ─── Convenience ──────────────────────────────────────────────────────


def validate_all(input_data: Any) -> Tuple[ValidatedAssistantPayload, ValidatedAssistantPayload, ValidatedAssistantPayload]:
    """Run all three contract gates in sequence: input → output → action.

    Returns:
        Tuple of (input_result, output_result, action_result)

    Raises:
        ValueError: On first validation failure
    """
    input_result = validate_input(input_data)
    output_result = validate_output(input_data)
    action_result = validate_actions(input_data)
    return input_result, output_result, action_result
