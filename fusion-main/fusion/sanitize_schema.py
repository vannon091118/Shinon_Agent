"""
sanitizeBySchema — LifeGameLab schema.js port to Python

Deterministic schema validation with defaults and clamps.
Enforces the "Promter writes patches, system validates them" contract.

Pattern:
  1. Input data arrives as dict
  2. Schema defines allowed fields, types, defaults, clamps
  3. sanitize() strips unknown fields, fills defaults, clamps values
  4. Invalid data → ValueError with field path

Contract: The prompter/agent proposes patches. The system (this module)
validates them BEFORE applying — never trust the prompter's output.

Usage:
    schema = {
        "name": {"type": str, "required": True},
        "max_tokens": {"type": int, "default": 1000, "min": 1, "max": 1_000_000},
        "temperature": {"type": float, "default": 0.7, "min": 0.0, "max": 2.0},
    }
    sanitized = sanitize({"name": "test", "extra": "ignored"}, schema)
    # → {"name": "test", "max_tokens": 1000, "temperature": 0.7}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union


def sanitize(
    data: Dict[str, Any],
    schema: Dict[str, Dict[str, Any]],
    *,
    allow_extra: bool = False,
) -> Dict[str, Any]:
    """Validate and sanitize data against a schema.

    Args:
        data: Input dict to validate.
        schema: Field definitions. Each key maps to a field spec:
            - type: Python type (str, int, float, bool, list, dict)
            - required: bool — if True, field MUST be present
            - default: value — used when field is missing
            - min/max: int/float — clamp value to range
            - choices: list — restrict to allowed values
            - nullable: bool — allow None
        allow_extra: If False, strip unknown keys. If True, pass through.

    Returns:
        Sanitized dict with defaults filled, unknown keys stripped,
        and values clamped to min/max.

    Raises:
        ValueError: If a required field is missing or type is wrong.
    """
    result: Dict[str, Any] = {}

    # 1. Validate known fields
    for field_name, field_spec in schema.items():
        expected_type = field_spec.get("type", str)
        required = field_spec.get("required", False)
        nullable = field_spec.get("nullable", False)

        if field_name not in data:
            if required:
                raise ValueError(f"Required field missing: {field_name}")
            if "default" in field_spec:
                result[field_name] = field_spec["default"]
            continue

        value = data[field_name]

        # Null check
        if value is None:
            if nullable:
                result[field_name] = None
                continue
            if required:
                raise ValueError(f"Required field is null: {field_name}")
            if "default" in field_spec:
                result[field_name] = field_spec["default"]
            continue

        # Type coercion (try, don't force)
        try:
            if expected_type == int and isinstance(value, (int, float)):
                value = int(value)
            elif expected_type == float and isinstance(value, (int, float)):
                value = float(value)
            elif expected_type == str and not isinstance(value, str):
                value = str(value)
            elif expected_type == bool and not isinstance(value, bool):
                value = bool(value)
            elif expected_type == list and not isinstance(value, list):
                if isinstance(value, (str, int, float)):
                    value = [value]
                else:
                    value = list(value)
            elif not isinstance(value, expected_type):
                raise ValueError(
                    f"Field '{field_name}' expected {expected_type.__name__}, "
                    f"got {type(value).__name__}"
                )
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Field '{field_name}': {exc}") from exc

        # Clamp numeric values
        if expected_type in (int, float) and value is not None:
            if "min" in field_spec:
                value = max(field_spec["min"], value)
            if "max" in field_spec:
                value = min(field_spec["max"], value)

        # Validate choices
        if "choices" in field_spec and value not in field_spec["choices"]:
            raise ValueError(
                f"Field '{field_name}': value '{value}' not in "
                f"allowed choices: {field_spec['choices']}"
            )

        result[field_name] = value

    # 2. Strip (or pass through) unknown keys
    if allow_extra:
        for key, value in data.items():
            if key not in schema:
                result[key] = value

    return result


def assert_patches_allowed(
    patches: List[Dict[str, Any]],
    allowed_paths: List[str],
) -> None:
    """Validate that all patches target allowed paths.

    Port of LifeGameLab's ``assertPatchesAllowed`` — mechanical enforcement
    that the prompter/agent can only mutate approved paths.

    Args:
        patches: List of patch dicts with 'path' key (dot-notation).
        allowed_paths: List of allowed path prefixes.

    Raises:
        ValueError: If any patch targets a path not in allowed_paths.
    """
    for i, patch in enumerate(patches):
        path = patch.get("path", "")
        if not path:
            raise ValueError(f"Patch {i}: missing 'path' field")

        allowed = any(
            path == prefix or path.startswith(prefix + ".")
            for prefix in allowed_paths
        )

        if not allowed:
            raise ValueError(
                f"Patch {i}: path '{path}' is not in allowed paths. "
                f"Allowed: {allowed_paths}"
            )


# ─── Pre-built Schemas ────────────────────────────────────────────────


CLAIM_SCHEMA: Dict[str, Dict[str, Any]] = {
    "id": {"type": str, "required": True},
    "claim": {"type": str, "required": True},
    "status": {
        "type": str,
        "default": "unverified",
        "choices": ["unverified", "verified", "refuted", "refined", "unknown"],
    },
    "evidence": {"type": str, "default": ""},
    "confidence": {
        "type": str,
        "default": "medium",
        "choices": ["high", "medium", "low"],
    },
    "source": {"type": str, "default": "unknown"},
    "claim_origin": {
        "type": str,
        "default": "explicit-declaration",
        "choices": ["explicit-declaration", "decision-extraction", "inference"],
    },
    "evidence_type": {
        "type": str,
        "default": "chat",
        "choices": ["code", "doc", "test_output", "chat", "mixed"],
    },
    "alternatives_rejected": {"type": list, "default": []},
}


DISPATCH_PATCH_SCHEMA: Dict[str, Dict[str, Any]] = {
    "path": {"type": str, "required": True},
    "op": {
        "type": str,
        "required": True,
        "choices": ["set", "inc", "dec", "push", "del", "merge"],
    },
    "value": {"type": object, "nullable": True},
}


RUN_STATE_SCHEMA: Dict[str, Dict[str, Any]] = {
    "pipeline_run_id": {"type": str, "required": True},
    "goal": {"type": str, "required": True},
    "project": {"type": str, "required": True},
    "status": {
        "type": str,
        "default": "INIT",
        "choices": ["INIT", "IN_PROGRESS", "COMPLETED", "FAILED", "ABORTED"],
    },
    "current_phase": {"type": str, "nullable": True, "default": None},
}


# ─── Schema Registry ───────────────────────────────────────────────────


_SCHEMA_REGISTRY: Dict[str, Dict[str, Dict[str, Any]]] = {
    "claim-v1": CLAIM_SCHEMA,
    "dispatch-patch-v1": DISPATCH_PATCH_SCHEMA,
    "run-state-v1": RUN_STATE_SCHEMA,
}


def sanitize_by_schema_name(
    data: Dict[str, Any],
    schema_name: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Sanitize data against a named schema from the registry.

    Args:
        data: Input data dict.
        schema_name: Key from _SCHEMA_REGISTRY (e.g., "claim-v1").
        **kwargs: Passed to sanitize().

    Returns:
        Sanitized dict.

    Raises:
        KeyError: If schema_name is not registered.
        ValueError: Schema validation fails.
    """
    schema = _SCHEMA_REGISTRY.get(schema_name)
    if schema is None:
        raise KeyError(f"Unknown schema: '{schema_name}'. Available: {list(_SCHEMA_REGISTRY)}")
    return sanitize(data, schema, **kwargs)
