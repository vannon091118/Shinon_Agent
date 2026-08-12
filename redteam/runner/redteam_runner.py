"""Red-Team Runner — führt Angriffe gegen die Governance aus, bewertet, reportet.

Usage (aus dem Projekt-Root):
    python3 -m redteam.runner.redteam_runner                    # Baseline
    python3 -m redteam.runner.redteam_runner --mutate           # Mutation-Test
    python3 -m redteam.runner.redteam_runner --report PATH      # JSON-Report
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from redteam import harness  # noqa: E402
from redteam.attacks import ATTACKS  # noqa: E402
from redteam.oracle import Report  # noqa: E402


def run_suite(target) -> Report:
    report = Report()
    for aid, name, fn in ATTACKS:
        report.observations.extend(fn(target))
    return report


def print_report(report: Report) -> None:
    print("═" * 66)
    print("  🦇 SHINON RED TEAM — Governance (LLM-Faulheit & Bias-Drift)")
    print("═" * 66)
    for o in report.observations:
        mark = "✅" if o.passed else "❌"
        sev = "PASS" if o.passed else o.severity.label
        print(f"  {mark} [{o.attack_id}] {o.check}")
        print(f"       observed={o.observed!r}  expected={o.expected!r}  → {sev}")
    print("─" * 66)
    print(f"  Passed: {report.passed_count}/{report.total}")
    print(f"  Governance-Debt: {report.governance_debt:.0f}  (nach Severity gewichtet)")
    by = report.by_severity()
    for s in ("PASS", "WARN", "FAIL", "CRITICAL", "CATASTROPHIC"):
        if by.get(s):
            print(f"    {s:13s} {by[s]}")
    print("═" * 66)


def main() -> int:
    ap = argparse.ArgumentParser(prog="redteam-runner")
    ap.add_argument("--mutate", action="store_true", help="Mutation-Testing aktivieren")
    ap.add_argument("--report", default=None, help="JSON-Report-Pfad")
    args = ap.parse_args()

    baseline = run_suite(harness)

    if args.mutate:
        # Sabotiere: evidenzfreie Claims werden jetzt akzeptiert.
        harness.mutate("confidence_resolver", "evidence_free_accept")
        try:
            mutated = run_suite(harness)
        finally:
            harness.reset_mutations()

        print("╔" + "═" * 64 + "╗")
        print("║  MUTATION TEST — confidence_resolver: evidence_free_accept   ║")
        print("╚" + "═" * 64 + "╝")
        print(f"  Baseline-Debt: {baseline.governance_debt:.0f}")
        print(f"  Mutiert-Debt:  {mutated.governance_debt:.0f}")
        if mutated.governance_debt > baseline.governance_debt:
            print("  ✅ Suite wird rot → sie testet die Governance wirklich.")
            rc = 0
        else:
            print("  ❌ Suite bleibt grün trotz Sabotage → Suite ist Müll.")
            rc = 1
        print()
        print("── Baseline-Report ──")
        print_report(baseline)
        print("── Mutierter-Report ──")
        print_report(mutated)
        return rc

    print_report(baseline)
    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(baseline.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\n  📄 Report → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
