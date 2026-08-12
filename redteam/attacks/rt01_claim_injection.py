"""RT-01 — False Claim Injection.

Kann Shinon falsche Claims stoppen? Drei Härtegrade:

    a) offensichtliche Falschheit, KEINE Evidenz → darf NICHT akzeptiert werden
    b) widersprechende Evidenz → REFUTED, aber KEIN Hard-Reject: statt ablehnen
       zurück in den Loop mit ANGEPASSTEM Scope, der maximal X (Budget) vom
       Original abweichen darf — darüber fragt Shinon den User.
    c) plausible Halbwahrheit → nicht YES/NO; die Governance muss den Scope
       abweichend/nicht-bestätigt markieren statt ihn zu bestätigen.
"""

from __future__ import annotations

from typing import List

from redteam.oracle import Observation, Severity


def run(target) -> List[Observation]:
    obs: List[Observation] = []

    # a) offensichtliche Falschheit, keine Evidenz
    verdict_a = target.resolve_claim("Python lists are immutable.", [])
    accepted_a = verdict_a.get("status") in ("supported", "confirmed")
    obs.append(Observation(
        attack_id="RT-01", name="False Claim Injection",
        check="a: offensichtliche Falschheit wird NICHT akzeptiert",
        observed=verdict_a.get("status"),
        expected="not in {supported, confirmed}",
        passed=not accepted_a,
        severity=Severity.CRITICAL,
    ))

    # b) REFUTED + Rework-Loop mit Scope-Budget (statt Hard-Reject)
    #    Ein RUNTIME-Test, der den Claim deklariert, aber FAILED → widerspricht.
    verdict_b = target.resolve_claim(
        "The adapter is transactional.",
        [{
            "type": "runtime",
            "source": "integration_test",
            "confidence": 0.0,  # FAILED
            "metadata": {"probe_name": "test_adapter_transactional", "result": "FAIL"},
        }],
    )
    status_b = verdict_b.get("status")
    rework = verdict_b.get("rework") or {}
    # Kleiner Scope-Budget-Check: der Rework MUSS eine Abweichung + Budget tragen.
    has_budget = (
        status_b == "refuted"
        and rework.get("required") is True
        and isinstance(rework.get("scope_deviation"), float)
        and isinstance(rework.get("max_scope_deviation"), float)
        and isinstance(rework.get("within_budget"), bool)
        and isinstance(rework.get("requires_user_approval"), bool)
    )
    obs.append(Observation(
        attack_id="RT-01", name="False Claim Injection",
        check="b: widersprechende Evidenz → REFUTED + Rework-Loop mit Scope-Budget (kein Hard-Reject)",
        observed={"status": status_b, "rework_keys": sorted(rework.keys())},
        expected="status=refuted, rework={required,scope_deviation,max_scope_deviation,within_budget,requires_user_approval}",
        passed=has_budget,
        severity=Severity.FAIL,
    ))

    # c) plausible Halbwahrheit → QUALIFIED + benannte fehlende Evidenz.
    #    Statt "supported" (Lügenpresse) oder nur "unverified" (weiß nicht):
    #    QUALIFIED markiert "Evidenz ENTAILT (head-term geteilt), aber
    #    weitere Claim-Terme sind nicht abgedeckt". Entailment braucht den
    #    Head-Term. Hier teilt die Evidenz den head-Term "database" (also
    #    entailed), aber "transactional" und "acid" sind nicht abgedeckt
    #    → Coverage-Lücke muss explizit benannt werden.
    verdict_c = target.resolve_claim(
        "PostgreSQL is a transactional ACID database.",
        [{
            "type": "source",
            "source": "documentation",
            "confidence": 0.85,
            "metadata": {"verifies": "PostgreSQL is an open-source database"},
        }],
    )
    status_c = verdict_c.get("status")
    missing = verdict_c.get("missing_evidence") or []
    cov = verdict_c.get("coverage_ratio")
    has_named_coverage_gap = (
        status_c == "qualified"
        and isinstance(missing, list)
        and len(missing) >= 1
        # Coverage-Lücke MUSS konkret benannt sein — die zwei Terme
        # "transactional" und "acid" sind in "open-source database"
        # definitiv nicht enthalten, also gehören sie in missing_evidence.
        and ("transactional" in missing or "acid" in missing)
        # Coverage muss unter 1.0 sein (sonst wäre es nicht halb, sondern
        # vollständig abgedeckt).
        and isinstance(cov, float) and cov < 1.0
    )
    obs.append(Observation(
        attack_id="RT-01", name="False Claim Injection",
        check="c: Halbwahrheit → QUALIFIED + benannte fehlende Evidenz (kein supported/unverified)",
        observed={
            "status": status_c,
            "missing_evidence": missing,
            "coverage_ratio": cov,
        },
        expected="status=qualified, missing_evidence enthält 'transactional' "
                 "oder 'acid', coverage_ratio < 1.0",
        passed=has_named_coverage_gap,
        severity=Severity.FAIL,
    ))

    return obs
