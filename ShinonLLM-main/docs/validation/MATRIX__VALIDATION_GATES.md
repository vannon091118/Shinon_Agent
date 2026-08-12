# Validation Gates Matrix

This repository-local matrix is the canonical validation reference for gate automation.

| Blueprint ID | Gate ID | Check | Status | Source |
|---|---|---|---|---|
| `BP__ops__ops_scripts_check_gates_ps1` | `GATE_AUTOMATION` | Gate automation script exists and resolves repo-local matrix path. | `PENDING` | `ops/scripts/check-gates.ps1` |
| `BP__runtime__contract_gate` | `GATE_CONTRACT` | Contract schema gate passes for valid payloads and blocks invalid payloads. | `PENDING` | `tests/gates/contract-gate.spec.ts` |
| `BP__runtime__replay_gate` | `GATE_REPLAY` | Replay hash is deterministic and sequence integrity is fail-closed. | `PENDING` | `tests/gates/replay-gate.spec.ts` |
| `BP__runtime__baseline_integrity` | `GATE_BASELINE` | Baseline integrity prints deterministic `testline` output for release verification. | `PENDING` | `tests/gates/baseline-integrity.spec.ts` |

