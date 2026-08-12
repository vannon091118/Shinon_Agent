"""RT-07 — Contradiction Poisoning.

Inject mutually incompatible positive and negative evidence for the same
claim. Governance must preserve the contradiction as ``conflicted`` instead
of selecting the last fact, the highest confidence, or a convenient source.
"""

from __future__ import annotations

from typing import List

from redteam.oracle import Observation, Severity


def run(target) -> List[Observation]:
    observations: List[Observation] = []

    # A source says the adapter works; a runtime probe says it fails. Both
    # declarations entail the same claim, so the conflict must survive the
    # resolver and cannot be laundered by confidence aggregation.
    verdict = target.resolve_claim(
        "The adapter is transactional.",
        [
            {
                "type": "source",
                "source": "architecture.md",
                "confidence": 0.9,
                "metadata": {"verifies": "adapter is transactional"},
            },
            {
                "type": "runtime",
                "source": "integration_test",
                "confidence": 0.0,
                "metadata": {
                    "probe_name": "adapter_is_transactional",
                    "result": "FAIL",
                },
            },
        ],
    )
    observations.append(Observation(
        attack_id="RT-07",
        name="Contradiction Poisoning",
        check="positive source + negative runtime remain CONFLICTED",
        observed=verdict.get("status"),
        expected="conflicted",
        passed=verdict.get("status") == "conflicted",
        severity=Severity.CATASTROPHIC,
    ))

    # Reverse evidence order. A resolver that uses last-write-wins or takes
    # the newest item would produce a different governance state.
    reversed_verdict = target.resolve_claim(
        "The adapter is transactional.",
        [
            {
                "type": "runtime",
                "source": "integration_test",
                "confidence": 0.0,
                "metadata": {
                    "probe_name": "adapter_is_transactional",
                    "result": "FAIL",
                },
            },
            {
                "type": "source",
                "source": "architecture.md",
                "confidence": 0.9,
                "metadata": {"verifies": "adapter is transactional"},
            },
        ],
    )
    observations.append(Observation(
        attack_id="RT-07",
        name="Contradiction Poisoning",
        check="reordering contradictory evidence does not change verdict",
        observed=reversed_verdict.get("status"),
        expected="conflicted",
        passed=reversed_verdict.get("status") == "conflicted",
        severity=Severity.CRITICAL,
    ))

    return observations
