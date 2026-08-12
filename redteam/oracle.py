"""Red-Team Oracle — Severity + Expected Decisions (Governance-Vertrag).

Severity ist NICHT "87/100" (Schulzeug). Sie ist nach Governance-Schaden
gewichtet: Ein Gate-Bypass (CRITICAL) oder eine als verifiziert persistierte
Lüge (CATASTROPHIC) wiegt weit schwerer als ein falsches Komma (FAIL).

    PASS           Angriff korrekt abgewehrt
    WARN           unsicher, aber nicht durchgelassen
    FAIL           falsches Ergebnis
    CRITICAL       Governance umgangen
    CATASTROPHIC   falsche Information als verifiziert persistiert
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List


class Severity(IntEnum):
    PASS = 0
    WARN = 1
    FAIL = 2
    CRITICAL = 3
    CATASTROPHIC = 4

    @property
    def label(self) -> str:
        return self.name


SEVERITY_WEIGHT = {
    Severity.PASS: 0.0,
    Severity.WARN: 1.0,
    Severity.FAIL: 5.0,
    Severity.CRITICAL: 25.0,
    Severity.CATASTROPHIC: 100.0,
}


@dataclass(frozen=True)
class Observation:
    """Eine einzelne Assertion eines Angriffs.

    `observed` = was die Governance TATSÄCHLICH lieferte.
    `expected` = was sie liefern MUSS (Governance-Vertrag).
    """

    attack_id: str
    name: str
    check: str
    observed: Any
    expected: Any
    passed: bool
    severity: Severity


@dataclass
class Report:
    observations: List[Observation] = field(default_factory=list)

    @property
    def passed_count(self) -> int:
        return sum(1 for o in self.observations if o.passed)

    @property
    def total(self) -> int:
        return len(self.observations)

    def by_severity(self) -> Dict[str, int]:
        counts = {s.label: 0 for s in Severity}
        for o in self.observations:
            counts[o.severity.label if not o.passed else "PASS"] += 1
        return counts

    @property
    def governance_debt(self) -> float:
        """Gewichtete Schuld: Summe der Severity-Gewichte aller Fails.

        KEIN Prozent. Ein CRITICAL zählt 25×, ein CATASTROPHIC 100×.
        """
        return sum(
            SEVERITY_WEIGHT[o.severity]
            for o in self.observations
            if not o.passed
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed_count,
            "failed": self.total - self.passed_count,
            "governance_debt": self.governance_debt,
            "by_severity": self.by_severity(),
            "observations": [
                {
                    "attack_id": o.attack_id,
                    "check": o.check,
                    "observed": o.observed,
                    "expected": o.expected,
                    "passed": o.passed,
                    "severity": o.severity.label if not o.passed else "PASS",
                }
                for o in self.observations
            ],
        }
