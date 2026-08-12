"""Strict, deterministic validation for persisted knowledge facts.

Facts are project knowledge, not arbitrary implementation state. The shared
SQLite ``facts`` table also stores internal runtime namespaces; those
namespaces are explicitly allow-listed and bypass only at the trusted
PersistenceLayer boundary.
"""

from __future__ import annotations

from typing import Any

REQUIRED_FACT_KEYS = frozenset({"fact", "source", "confidence", "verified_by"})
CONFIDENCE_LEVELS = frozenset({"high", "medium", "low"})

# ``verified_by`` is an identity, not free-form prose. An unknown agent/model
# cannot self-attest as a trusted verifier.
VERIFIER_REGISTRY = frozenset({
    "source", "runtime", "test", "karma", "promtguard",
    "falsification_gate", "evil_twin", "human", "manual", "system",
})

# A verifier identity is only valid when the runtime can name the concrete
# verification boundary. ``verified_by`` is deliberately not an arbitrary
# model/agent label: persisted facts must point at one of these attestations.
VERIFIER_REQUIREMENTS = {
    "source": {"source"},
    "runtime": {"runtime"},
    "test": {"test", "pytest"},
    "karma": {"karma"},
    "promtguard": {"promtguard"},
    "falsification_gate": {"falsification_gate", "gate"},
    "evil_twin": {"evil_twin", "evil-twin"},
    "human": {"human", "manual"},
    "manual": {"human", "manual"},
    "system": {"system"},
}


def verifier_is_registered(verified_by: Any) -> bool:
    """Whether an identity is issued by Shinon's verifier registry."""
    return isinstance(verified_by, str) and verified_by in VERIFIER_REQUIREMENTS

# Namespaces used for implementation state in the shared facts table. Their
# values have their own schemas and may be strings, numbers, or arbitrary
# structured state; they are not user knowledge facts.
SYSTEM_DOMAINS = frozenset({
    "config", "ml", "claims", "karma", "karma_executions", "shinon_memory",
    "prompt_variants", "idempotency", "governance", "execution",
})


def is_system_domain(domain: str) -> bool:
    return domain.startswith("_") or domain in SYSTEM_DOMAINS


def _validate_fact(
    value: Any,
    *,
    domain: str | None = None,
    allow_system: bool = False,
) -> None:
    """Validate one knowledge fact, fail-closed by default.

    ``allow_system`` is used only by the SQLite boundary after the caller has
    selected an explicit internal namespace. Public MemoryBus writes always
    use strict validation, including for names such as ``config``.
    """
    if allow_system and domain is not None and is_system_domain(domain):
        return
    if not isinstance(value, dict):
        raise ValueError("Facts must be JSON objects.")

    missing = REQUIRED_FACT_KEYS - value.keys()
    if missing:
        raise ValueError(f"Fact missing required keys: {sorted(missing)}")

    fact = value.get("fact")
    source = value.get("source")
    confidence = value.get("confidence")
    verified_by = value.get("verified_by")

    if not isinstance(fact, str) or not fact.strip():
        raise ValueError("Fact field must be a non-empty string.")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("Source field must be a non-empty string.")
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError(
            f"Invalid confidence '{confidence}'. Valid: {sorted(CONFIDENCE_LEVELS)}"
        )
    if not verifier_is_registered(verified_by):
        raise ValueError(
            f"Unknown verifier identity '{verified_by}'. "
            f"Valid: {sorted(VERIFIER_REGISTRY)}"
        )


def validate_verifier_identity(verified_by: Any) -> str:
    """Return a canonical verifier id, rejecting self-attested free text."""
    if not verifier_is_registered(verified_by):
        raise ValueError(
            f"Unknown verifier identity '{verified_by}'. "
            f"Valid: {sorted(VERIFIER_REGISTRY)}"
        )
    return verified_by


def validate_persisted_value(domain: str, value: Any) -> None:
    """Validate a knowledge fact immediately before it crosses into SQLite.

    Runtime namespaces must use ``PersistenceLayer.set_internal_fact``; a
    domain name alone is never permission to bypass the fact contract.
    """
    _validate_fact(value, domain=domain, allow_system=False)


__all__ = [
    "REQUIRED_FACT_KEYS", "CONFIDENCE_LEVELS", "VERIFIER_REGISTRY",
    "SYSTEM_DOMAINS", "is_system_domain", "_validate_fact",
    "validate_verifier_identity", "validate_persisted_value",
]
