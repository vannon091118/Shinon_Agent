---
name: multi-agent-orchestrator
description: "Orchestriere Multi-Agent-Workflows mit definierten Rollen, Gates und Preflight-Checks. Nutze bei komplexen Tasks, die mehrere spezialisierte Agent-Rollen erfordern (Task-Orchestrator, Arbiter-Coder, Protocol-Enforcer, Architecture-Guardian). Aus LifeGameLab Agent-System extrahiert."
category: agents
stack: AUTONOM + GOVERNANCE
risk: high
side_effects: code_changes
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
---

# Multi-Agent Orchestrator

Orchestriere spezialisierte Agent-Rollen für komplexe, sicherheitskritische Code-Tasks.

## Rollen-Architektur

```
Task-Orchestrator  →  Plant, routet Tasks, keine Code-Edits
       ↓
Arbiter-Coder      →  Implementiert im genehmigten Scope (Explorer/Worker-Modus)
       ↓
Protocol-Enforcer  →  Prüft Protokoll-Verletzungen und Invarianten
       ↓
Architecture-Guardian → Prüft Layer-Grenzen und Cross-Layer-Leaks
```

## Rollen im Detail

### Task-Orchestrator (Planer)
- **Scope**: Nur LLM-Layer-Koordination
- **Input**: Ticket/Prompt + geänderte Pfade
- **Output**: PLAN.md mit Task-Slices + Worker-Routing
- **Guard**: Keine Code-Edits in Produktdateien
- **Done**: PLAN.md existiert mit Task-Slices und Worker-Zuweisung

### Arbiter-Coder (Implementierer)
- **Scope**: Genehmigter Slice
- **Input**: PLAN.md + Target-Files + Acceptance-Tests
- **Output**: PATCH.md + geänderte Dateien + Rationale
- **Guard**: Kein Merge ohne Gate-Check
- **Done**: PATCH.md mit geänderten Dateien und Begründung

### Protocol-Enforcer (Prüfer)
- **Scope**: Protokoll- und Invarianten-Review
- **Input**: PATCH.md + Protokoll-Dokumentation
- **Output**: PROTOCOL_REPORT.md mit ## Verdict
- **Guard**: Blockiert unsichere Mutationen
- **Done**: Verdict "no violations found" oder nummerierte Liste

### Architecture-Guardian (Architekt)
- **Scope**: Layer-Grenzen-Review
- **Input**: Patch-Diff + Architektur-Dokumentation
- **Output**: ARCH_REVIEW.md mit ## Verdict
- **Guard**: Blockiert Cross-Layer-Leaks
- **Done**: Verdict "no violations found" oder nummerierte Liste

## Execution-Chain (Sequentiell)

```
classify → entry → ack → check → execute
```

1. **classify**: Task-Kategorie bestimmen
2. **entry**: Entry-Mode festlegen (work | security)
3. **ack**: Scope bestätigen
4. **check**: Preflight-Gates prüfen
5. **execute**: Erst nach grünem `check` schreiben!

## Harte Regeln

- Kein Schreiben ohne grünen `check`
- Task-Orchestrator ist Parent-only — Subagents niemals orchestrieren
- Nach `POST_REPORT_LOCK=true`: Nur Read-Only + Reporting
- Vor jedem File-Scan: Subagent-Rebuttal für jede Annahme (1-6 Subagents parallel)
- Keine direkten Intent/Struktur/Fehler-Schlüsse ohne Subagent-Rebuttal

## Abgeleitete Rollen (via Config)

| Rolle | Typische LLM-Priorität |
|---|---|
| Documentation-Auditor | Light (Docs-Drift-Prüfung) |
| Quality-Reviewer | Standard (Test-Review) |
| Domain-Coordinator | Standard (Scope-Erweiterung) |
| Test-Engineer | Standard (Test-Erstellung) |
| Versioning-Release | Light (Changelog, Versionierung) |
| Gate-Compliance-Checker | Standard (Final-Gate) |
