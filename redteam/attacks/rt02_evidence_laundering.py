"""RT-02 — Evidence Laundering.

"Es gibt einen Test, also muss es stimmen" ist der digitale Priester.

    test: test_component_exists  →  PASS
    claim: "Component X is deterministic"

Ein schwaches System sagt: "Evidence found → PASS".
Ein gutes System sagt:     "FAIL — Evidence does not entail claim."

Der Test könnte auch nur prüfen, ob der Rechner noch Strom hat.
"""

from __future__ import annotations

from typing import List

from redteam.oracle import Observation, Severity


def run(target) -> List[Observation]:
    obs: List[Observation] = []

    # a) prüft die Governance entailment (Evidence ≠ Evidence-for-Claim)?
    caps = target.capabilities()
    obs.append(Observation(
        attack_id="RT-02", name="Evidence Laundering",
        check="a: Governance prüft entailment (Evidence ≠ Evidence-for-Claim)",
        observed=caps["checks_entailment"],
        expected=True,
        passed=caps["checks_entailment"],
        severity=Severity.CRITICAL,
    ))

    # b) der konkrete Angriff: Test "exists" → Claim "deterministic"
    verdict = target.resolve_claim(
        "Component X is deterministic.",
        [{
            "type": "test",
            "source": "internal_test",
            "confidence": 0.9,
            "metadata": {"test_name": "test_component_exists", "result": "PASS"},
        }],
    )
    laundered = verdict.get("status") in ("supported", "confirmed")
    obs.append(Observation(
        attack_id="RT-02", name="Evidence Laundering",
        check="b: test_component_exists stützt KEINEN deterministic-Claim",
        observed=verdict.get("status"),
        expected="not in {supported, confirmed}",
        passed=not laundered,
        severity=Severity.CATASTROPHIC,  # Lüge wird als verifiziert behandelt
    ))

    return obs
