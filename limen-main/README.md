# LIMEN

> **Limen** (lat.) — *Schwelle, Eingang.*
>
> LIMEN ist die unsichtbare Schwelle zwischen CLI-AI-Tools und mehreren
> OpenAI-kompatiblen Provider-Deployments.

## Was LIMEN ist

LIMEN ist ein **lokaler API-Backend/Dispatcher/Router** für `127.0.0.1`.
Es nimmt zunächst nicht-streamende OpenAI-kompatible Requests an (`POST
/v1/chat/completions`), wählt ein passendes Provider-Deployment und gibt eine
transparente OpenAI-kompatible Antwort zurück.

Der Router ist kein Black Box-Spielzeug:

- zentraler Provider-Dispatch statt paralleler Provider-Pfade;
- deklarative Registry für Provider, einzelne Modelle, Capabilities und Limits;
- lokaler Request-Scanner (Größe, Code-/Strukturanteil, Komplexitäts-Score) ohne zusätzlichen Provider-Call;
- SQLite WAL für Key-Zustände, Queue und Audit-Ereignisse (mit Events-Prune);
- `${ENV_VAR}`-Auflösung für API-Keys in der Config;
- Admission Control: `max_pending` + `max_wait_seconds` → 503 bei Queue-Voll;
- konservative Retries mit `Retry-After`, Backoff und Jitter;
- redigierte Live-Ereignisse mit Correlation-ID;
- Control Center für Aktivität, Dispatcher-Fluss, Request-Inspector, Simulation
  und kontrollierte Laufzeitgrenzen.

## Eigenständige Konzeptbasis

Die Architektur übernimmt keine fremden Namen, Pfade oder Implementierungen.
Sie destilliert und formuliert nur belastbare Konzepte neu: transaktionale
Persistenz, typisierte Audit-Events, zentraler Dispatch, capability-bewusstes
Routing, Retry-/Cooldown-Zustände, SSE-Beobachtbarkeit und Operator-Steuerung.

Keine künstliche Funktionsbegrenzung: Die Zieloberfläche darf die vollständige
redigierte Routing-Realität darstellen. Sichtbare Grenzen sind Sicherheit,
Datenintegrität und überprüfbare Semantik — nicht die Menge der UI-Funktionen.

## Declarative Model Registry und Request-Scan

Provider bleiben unter `[providers.<name>]` für URL und Keys konfiguriert. Für
Slice 1+2 kann jedes Modell zusätzlich einen eigenen `[models.<name>]`-Block
bekommen. Die Registry erzeugt daraus ein eigenes Deployment pro Modell und
übernimmt Modell-Capabilities, Kontextlimit, Priorität, Free-Markierung und
Eskalationsgruppe. Die bestehende `providers.<name>.models`-Liste bleibt als
kompatibler Fallback erhalten.

Vor dem expliziten Dispatch misst LIMEN lokal und deterministisch die ungefähre
Input-/Outputgröße, Kontextgröße, Message-Anzahl sowie Code- und Strukturanteil.
Der daraus berechnete Score wird als `request.scanned` auditiert. Er ändert in
Slice 1+2 noch **nicht** das vom Client angeforderte Modell; automatisches
`model="auto"` und die Eskalationskette sind der nächste Slice.

## Status

```text
CURRENT: 0.0.17 ALLE PHASEN 0-5 IMPLEMENTIERT + MODEL SCAN + PIPELINE UI + AUTO-ROUTING + NAMED KEYS + ARCHITECTURE REFACTOR
         Phase 0-5: Foundation, Single-Provider, Multi-Provider/Resilienz,
         Durable Queue, Audit/Heartbeat, Streaming. 207 passed, 0 skipped.
NEXT:    Phase 6A — Betriebs-Härtung
```

## Schnell-Übersicht

| Aspekt | Wert |
|---|---|
| Sprache | Python 3.11+ |
| MVP-Schema | OpenAI-kompatibel, `stream=false` |
| Bind | `127.0.0.1` — Port via `[server].port` (Default 8000), kein LAN |
| Persistenz | SQLite WAL, versioniertes Schema |
| Auth | Public ohne Auth; Audit nur mit Token |
| Deployment | systemd-User-Unit erst in der Hardening-Phase |
| Betrieb | ein Benutzer, ein Rechner, eine DB |
| Test-Client | Goose (Block) Desktop, Open Interpreter (Backup) |
| Konzeptbasis | destillierte, eigenständige Routing-/Persistenz-/Observability-Muster |

## Phasen in Kurzform

0. **Contract/Foundation:** Config, SQLite, Migrationen, Transaktionen, Basistests.
1. **Single-Provider E2E:** ein Adapter, ein Key, OpenAI-Vertrag ohne Streaming. **Implementiert** (`v0.0.6`).
2. **Multi-Provider/Resilienz:** Registry, Rotation, Limit-Scope, Failure-Types.
   **Implementiert** (`v0.0.9`) — 27 Contract-Asserts grün.
3. **Durable Queue/Recovery:** Leases, atomare Claims, Restart-Recovery,
   eingeschränkte Idempotency. **Implementiert** (`v0.0.11`) — 19 Contract-Asserts grün.
4. **Audit/Heartbeat:** typed Events, Audit-Auth, SSE, Reaper. **Implementiert** (`v0.0.12`) — 12 Contract-Asserts grün.
5. **Streaming/Kompatibilität:** SSE-Wire-Format, No-Retry-After-First-Chunk.
   **Implementiert** (`v0.0.10`) — 12 Contract-Asserts grün.
6A. **Betriebs-Härtung:** systemd, Secret-Schutz und messbare Optimierungen.
6B. **Control Center/Diagnose:** vollständige redigierte Sichtbarkeit, Simulation,
   Slider mit Preview/Apply/Reset und optionale Komfortschichten.

Die verbindlichen Akzeptanzkriterien stehen in
[`ARCHITECTURE.md`](./ARCHITECTURE.md).

## Schnellstart (nach Implementation)

```bash
cd ~/Schreibtisch/limen
uv sync
cp config.toml.example ~/.config/limen/config.toml
$EDITOR ~/.config/limen/config.toml
limen init
limen start
```

## Launcher (Auto-Detection + Backup)

`scripts/launch_limen.py` findet installierte Agent-Clients (Goose, Claude
Code, Open Interpreter, Aider, Continue.dev, opencode), legt eine
nummerierte Liste vor, lässt dich wählen und tauscht die Provider-Config
gegen LIMEN. Vor jedem Write wird das Original als
`<datei>.bak.<unix-ts>` (oder `<datei>.env.bak.<unix-ts>`) gesichert.

```bash
scripts/launch_limen.py list              # nur Detection-Tabelle
scripts/launch_limen.py dry-run goose     # Plan ohne Schreiben
scripts/launch_limen.py swap              # interaktiv: Backup + Patch + (optional) start
scripts/launch_limen.py swap interpreter --start
scripts/launch_limen.py restore goose     # jüngsten Backup zurückspielen
```

## Live-E2E gegen echtes Groq

`scripts/live_e2e_groq.sh` führt eine echte Round-Trip-Anfrage an
[https://api.groq.com/openai/v1](https://api.groq.com/openai/v1) durch LIMEN.
[Pre-Flight, Risiken und Failure-Map stehen in `docs/live-groq-e2e.md`](./docs/live-groq-e2e.md).

```bash
scripts/live_e2e_groq.sh --check-only --port 18100          # Pre-Flight: Port, Repo, Tools
scripts/live_e2e_groq.sh \
  --port 18100 --stream \
  --key gsk_yourKey1 --key gsk_yourKey2 \
  --model llama-3.3-70b-versatile \
  --prompt "Reply with exactly: LIMEN live test passed."
```

Das Skript sichert `~/.config/limen/config.toml → *.bak.<ts>`, schreibt
eine Groq-only-Konfig (mit allen `--key`-Werten als TOML-Array), startet
LIMEN im Hintergrund, ruft genau einen Mini-Completion (`max_tokens` ≤ 8),
stoppt LIMEN am Ende und stellt die Original-Konfig wieder her. Key wird
**nie** in Klartext geloggt. Artefakte landen in `mktemp -d`.

Mit `--stream` wird die Streaming-Antwort auf `data:`-Zeilen geprüft.
Mit mehreren `--key`-Flags wird Multi-Key-Rotation live testbar.

## Queue-Recovery-Test

`scripts/recovery_test.sh` testet `recover_leases()` isoliert — ohne echte
Provider-Keys. Injiziert einen `in_flight`-Task mit abgelaufener Lease,
startet LIMEN und verifiziert das `queue.recovery`-Event sowie die
Status-Änderung `in_flight` → `dead`.

```bash
scripts/recovery_test.sh
```

Erster Public-Test nach Phase 1:

```bash
# Port aus ~/.config/limen/config.toml → [server].port (Default 8000)
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"hi"}]}'
```

Vor dem Goose-Round-Tripp das Reset-Gate headless abnehmen:

```bash
./scripts/phase1_smoke.sh  # 18 deterministische Assertions, kein echter Key nötig
```

Die Pflicht-Checkliste und die Goose-Plu-in-Anleitung stehen in
[`docs/phase1-reset-gate.md`](./docs/phase1-reset-gate.md).

## Goose-Desktop ↔ LIMEN ↔ Groq (echter Round-Trip als GUI)

Für die volle End-to-End-Strecke mit Goose als echter Electron-GUI und einem
Live‑Groq‑Key gilt das ausführliche Runbook
[`docs/goose-gui-live-plan.md`](./docs/goose-gui-live-plan.md). Dort stehen
Pre-Flight, Phase A (LIMEN-Start), Phase B (Goose-Patch + Restart), Phase C
(Roundtrip), Phase D (Audit/Verify), Phase E (Cleanup/Restore) und die
Failure‑Map. **§3.0** im Plan-Doc verbindet das Skript
`scripts/live_e2e_groq.sh` (`--check-only` für Pre-Flight, `--keep-config`
für Full-Run) mit Phase A‑E; **§4.0** zeigt die drei Workarounds für die
Phase-1-Auth-Lücke.

Kurzfassung:

```bash
# 1. Groq-Key bereitstellen (keine Persistenz in der Shell-History).
read -rs GROQ_API_KEY; export GROQ_API_KEY

# 2. LIMEN-Konfig mit groq-Provider anlegen (Key aus env oder kurzfristig in TOML).
$EDITOR ~/.config/limen/config.toml

# 3. Pre-Flight ohne Goose.
LIMEN_PORT=8000 ./scripts/phase1_smoke.sh

# 4. LIMEN starten.
uv run limen start

# 5. Goose beenden, Patch planen + anwenden.
python3 scripts/launch_limen.py dry-run goose
python3 scripts/launch_limen.py swap goose   # Backup + Patch + y/N
goose &                                     # Electron neu starten

# 6. In Goose: Provider „limen_local" wählen, kurze Frage stellen.

# 7. Teardown in umgekehrter Reihenfolge — Goose-Close, restore, LIMEN-Stop.
python3 scripts/launch_limen.py restore goose
unset GROQ_API_KEY
```

## Dokumente

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — einzige Plan- und Architekturquelle
- [`CHANGELOG.md`](./CHANGELOG.md) — dokumentierte Änderungen
- [`AGENTS.md`](./AGENTS.md) — Arbeitsvertrag für Agents
- [`docs/phase1-reset-gate.md`](./docs/phase1-reset-gate.md) — Phase-1-Checkliste
  und Goose-Plu-in
- [`docs/phase5-streaming-contract.md`](./docs/phase5-streaming-contract.md) —
  Phase-5-Streaming-Vertrag (SSE, No-Retry-After-First-Chunk, Header-Policy)
- [`docs/phase2-routing-contract.md`](./docs/phase2-routing-contract.md) —
  Phase-2-Multi-Provider-Routing mit Key-Pool-Rotation und `limit_scope`-Semantik
- [`docs/live-groq-e2e.md`](./docs/live-groq-e2e.md) — Skript-getriebenes
  Live-Groq-E2E (`scripts/live_e2e_groq.sh`) mit Pre-Flight und Failure-Map
- [`docs/goose-gui-live-plan.md`](./docs/goose-gui-live-plan.md) — Goose-Desktop ↔
  LIMEN ↔ Groq Live-GUI-Runbook mit Phasen A–E und Cleanup-Trap
- [`config.toml.example`](./config.toml.example) — konservative Startwerte und
  zentrale Registry

---

