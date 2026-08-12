"""GovernanceTarget — dünner Adapter auf die ECHTE deterministische Governance.

Das Red Team greift NICHT das LLM an. Es ruft die echten deterministischen
Funktionen auf:

    * karma.core.evidence.ConfidenceResolver → Claim-Verdict
    * karma.core.evidence.ClaimStatus        → hat die Governance ein REJECT?
    * (RT-03+) FalsificationGate, Memory-Provenance, Schema-Validierung

Mutation-Testing: `mutate()` sabotiert die ECHTE Komponente (monkeypatcht
`ConfidenceResolver.resolve`); die Suite MUSS danach roter werden. Sonst
testet die Suite die Governance nicht wirklich — sie wäre ein grünes
CI-Badge ohne Aussage.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_karma_src = PROJECT_ROOT / "karma-main"
if _karma_src.exists():
    sys.path.insert(0, str(_karma_src))

from karma.core.evidence import (  # noqa: E402
    Claim,
    ClaimStatus,
    ConfidenceResolver,
    Evidence,
    EvidenceType,
)

# ─── Mutation-Hook (monkeypatcht die ECHTE Klasse) ───────────────────
_MUTATIONS: Dict[str, str] = {}

# @staticmethod → Zugriff liefert die nackte Funktion (kein Bound-Method).
_ORIGINAL_RESOLVE = ConfidenceResolver.resolve


def _mutated_evidence_free_accept(claim):
    """MUTIERT: evidenzfreier Claim wird als 'supported' akzeptiert."""
    if not claim.evidences:
        return {"overall": 0.9, "status": "supported"}
    return _ORIGINAL_RESOLVE(claim)


def mutate(component: str, mode: str = "always_accept") -> None:
    """Sabotiere eine Governance-Komponente (Mutation-Testing)."""
    _MUTATIONS[component] = mode
    if component == "confidence_resolver" and mode == "evidence_free_accept":
        ConfidenceResolver.resolve = staticmethod(_mutated_evidence_free_accept)


def reset_mutations() -> None:
    _MUTATIONS.clear()
    ConfidenceResolver.resolve = staticmethod(_ORIGINAL_RESOLVE)


# ─── Governance-Ziele (die ECHTE Logik, kein Mock) ────────────────────

def resolve_claim(statement: str, evidence_specs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Claim + Evidence → Verdict via ConfidenceResolver (echte Logik).

    Ruft die LIVE-Klassenmethode auf, damit der Mutation-Hook greift.
    """
    claim = Claim.create(project="redteam", statement=statement, domain="test")
    for es in evidence_specs:
        claim.evidences.append(Evidence.create(
            claim_id=claim.claim_id,
            evidence_type=EvidenceType(es["type"]),
            source=es.get("source", "redteam"),
            confidence=float(es.get("confidence", 0.0)),
            metadata=es.get("metadata", {}),
        ))
    return ConfidenceResolver.resolve(claim)


def capabilities() -> Dict[str, Any]:
    """Was die Governance deterministisch KANN — aus dem echten Code abgeleitet."""
    # REJECT-Verdict: prüft den echten ClaimStatus-Enum.
    has_reject = any(
        s in ("reject", "refuted", "falsified")
        for s in (m.lower() for m in ClaimStatus.__members__)
    )
    # Entailment: prüft den echten Resolver-Quelltext (nicht nur dir()-Namen).
    try:
        resolver_src = inspect.getsource(ConfidenceResolver.resolve).lower()
    except (OSError, TypeError):
        resolver_src = ""
    checks_entailment = "entail" in resolver_src
    # Scope-Deviation-Budget: der Resolver muss beim Refutieren einen Rework
    # mit angepasstem Scope zurückgeben statt hart abzulehnen.
    checks_scope_budget = "rework" in resolver_src and "scope_deviation" in resolver_src
    return {
        "has_reject_verdict": has_reject,
        "checks_entailment": checks_entailment,
        "has_scope_budget": checks_scope_budget,
    }
