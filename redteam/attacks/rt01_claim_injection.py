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

    # c) Halbwahrheit → Scope-Abweichung begrenzt; über Budget → User fragen
    #    Ein Test, der NUR "exists" verifiziert, entailed den Claim nicht →
    #    rework_scope_deviation = 1.0 (nichts gedeckt) → requires_user_approval.
    verdict_c = target.resolve_claim(
        "SQLite supports concurrent writes.",
        [{
            "type": "test",
            "source": "internal_test",
            "confidence": 0.9,
            "metadata": {"test_name": "test_component_exists", "result": "PASS"},
        }],
    )
    # Entailment-Gate dropt das irrelevante Evidence → Claim bleibt unverified,
    # aber NIE supported/confirmed. Halbwahrheit wird nicht als wahr verkauft.
    status_c = verdict_c.get("status")
    not_laundered = status_c not in ("supported", "confirmed")
    obs.append(Observation(
        attack_id="RT-01", name="False Claim Injection",
        check="c: Halbwahrheit wird nicht als wahr verkauft (nicht supported/confirmed)",
        observed=status_c,
        expected="not in {supported, confirmed}",
        passed=not_laundered,
        severity=Severity.FAIL,
    ))

    return obs
