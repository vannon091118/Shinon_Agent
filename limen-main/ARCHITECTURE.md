# LIMEN — Architecture Specification

> **Plan-of-Record:** Diese Datei ist die einzige verbindliche Architektur- und
> Umsetzungsplanung für LIMEN. Der Chat und alte Entwürfe sind keine Quelle der
> Wahrheit.
>
> **Stand:** 2026-08-08 · **Status:** PHASES_0-5_IMPLEMENTED + HARDENING · **Owner:** vannon
> **Betrieb:** ein Benutzer, ein Rechner, localhost-only

```yaml
---
title: LIMEN Architecture
version: 0.7-PHASE5_HARDENED
status: PHASES_0-5_IMPLEMENTED
last_updated: 2026-08-08
owner: vannon
audience: solo-dev and AI implementer
pattern_review:
  - transactional_sqlite_persistence
  - typed_audit_events
  - central_provider_dispatch
  - capability_aware_routing
  - retry_and_cooldown_state_machines
  - server_sent_event_observability
  - operator_control_surfaces
  provenance_policy: "Source projects are not named in LIMEN documentation; only re-authored concepts are retained."
---
```

## Inhaltsverzeichnis

1. [Ziel und harte Grenzen](#1-ziel-und-harte-grenzen)
2. [Verträge und Sichtbarkeitsebenen](#2-verträge-und-sichtbarkeitsebenen)
3. [Destillierte Konzepte](#3-destillierte-konzepte)
4. [Zentrale Architektur](#4-zentrale-architektur)
5. [Failure- und Retry-Modell](#5-failure--und-retry-modell)
6. [Persistenz und Zustandsmodell](#6-persistenz-und-zustandsmodell)
7. [Control Center](#7-control-center)
8. [Plan-of-Record: Umsetzungsphasen](#8-plan-of-record-umsetzungsphasen)
9. [Tests und Falsifizierung](#9-tests-und-falsifizierung)
10. [Betrieb und Sicherheit](#10-betrieb-und-sicherheit)
11. [Decisions-Log und offene Punkte](#11-decisions-log-und-offene-punkte)
12. [Glossar](#12-glossar)

---

## 1. Ziel und harte Grenzen

### 1.1 Ziel

LIMEN ist ein lokaler OpenAI-kompatibler Forward-Proxy/Dispatcher für CLI-
und Desktop-AI-Tools. Er nimmt Requests auf dem konfigurierten Port an (Default 8000, siehe `[server] port`), wählt ein
kompatibles Provider-Deployment, ruft die Provider-API auf und gibt eine
transparente OpenAI-kompatible Antwort zurück.

Der Kernwert ist **vollständig nachvollziehbares Routing**. LIMEN darf die
gesamte Betriebsrealität sichtbar und steuerbar machen; die Grenze liegt nicht
bei der UI, sondern bei Sicherheit, Datenintegrität und überprüfbarer Semantik:

- ein zentraler Provider-Dispatch statt paralleler Provider-Pfade,
- deklarative Provider-/Modell-Registry als Single Source of Truth; jedes
  `[models.<name>]`-Element bildet ein eigenes, validiertes Deployment,
- lokaler Request-Scanner für Größe und Komplexität; bei `model="auto"`
  filtert er Deployments nach Kontextfenster und priorisiert nach Config,
- `model="auto"` als Routing-Sentinel: LIMEN wählt selbstständig das
  beste Deployment; explizite Modelle bleiben unverändert geroutet,
- Key- und Deployment-Zustände mit atomaren SQLite-Updates,
- konservative Retries mit `Retry-After`, Backoff und Jitter,
- unverfälschte Live-Ereignisse ohne Secrets,
- ein Control Center für Aktivität, Routing-Entscheidungen, Simulation und
  kontrollierte Laufzeitänderungen.

### 1.2 Harte Grenzen

LIMEN ist zunächst:

- **single-user**, **single-host**, **localhost-only**;
- OpenAI-kompatibel mit einer separat prüfbaren Kompatibilitätsgrenze;
- deterministisch testbar mit Mock-Transports;
- ein Router mit vollständiger Beobachtungs- und Steuerungsschicht;
- offen für Streaming, Simulation, Diagnose und Laufzeitsteuerung, sobald deren
  Verträge und Tests definiert sind.

LIMEN ist nicht auf eine kleine Anzeige oder einen reinen Statusserver begrenzt.
Das Control Center darf jede interne, redigierte Routing-Information erklären,
visualisieren und — innerhalb validierter Grenzen — verändern. Nicht sichtbar
werden Secrets, vollständige Authorization-Header, unredigierte Provider-Bodies
oder sensible Prompt-Inhalte.

Die äußere Kompatibilitätsgrenze wird nicht geraten. Vor ihrer Aktivierung muss
ein lokaler Contract-Smoketest Request-, Tool- und Streaming-Semantik belegen.
Bis dahin bleibt die Grenze ein expliziter Vertrag und wird nicht stillschweigend
nachgebaut.

### 1.3 Kein Inline-Design

Aus dem globalen Review wird folgende Regel übernommen:

- keine Provider-URLs, Auth-Header, Retry-Logik oder Modellheuristiken inline in
  Endpoint-Handlern;
- keine zweite Provider-Registry in Config, Code und UI;
- keine parallelen Legacy-/Experimental-Implementierungen;
- keine Inline-Secrets in Quickrefs, Benchmarks, Tests oder Dokumentation;
- jede Cross-Cutting-Funktion hat genau einen benannten Owner.

Provider-Adapter rufen den zentralen Dispatch auf. Der HTTP-Layer kennt weder
Provider-Sonderfälle noch Key-Rotation.

---

## 2. Verträge und Sichtbarkeitsebenen

### 2.1 Public API

```yaml
binding: "127.0.0.1"  # Port via [server].port (Default 8000)
auth: none
mvp_endpoints:
  - POST /v1/chat/completions   # stream=false verbindlich
  - GET /v1/models
  - GET /health
later_endpoints:
  - POST /v1/chat/completions   # stream=true, eigene Phase
response_contract:
  success: provider-compatible OpenAI JSON
  error: OpenAI-compatible {error: {message, type, param, code}}
forbidden_response_headers:
  - X-Routed-By
  - X-Provider-Health
  - X-Limen
  - raw provider diagnostic headers
```

Im Fehlerfall muss LIMEN das OpenAI-Fehlerformat wahren. Interne Failure-Types,
Key-IDs, Provider-Namen und Stacktraces bleiben im Audit-Kanal.

### 2.2 Keepalive

```yaml
binding: "127.0.0.1"  # Port via [server].port (Default 8000)
endpoint: GET /health
auth: none
response:
  status: ok | degraded | down
  uptime_seconds: integer
  pid: integer
  last_request_at: iso8601|null
  db_writable: boolean
  queue_depth: integer
provider_internals: forbidden
```

`ok` bedeutet: Prozess und Persistenz sind funktionsfähig. `degraded` bedeutet:
Prozess lebt, aber kein geeigneter Provider ist aktuell aktiv. `down` wird nur
bei nicht funktionsfähiger Kernpersistenz oder nicht beantwortbarem Service
verwendet.

### 2.3 Audit API

Audit wird erst nach dem funktionierenden Routing-Kern aktiviert.

```yaml
binding: "127.0.0.1"  # optional später UNIX-Socket; Port via [server].port (Default 8000)
auth: X-Proxy-Audit-Key
endpoints:
  - GET /v1/_internal/status
  - GET /v1/_internal/events       # SSE, Phase 4
  - GET /v1/_internal/heartbeat    # Phase 4
  - POST /v1/_internal/test/simulate # dev-only, niemals production
```

Webhook-Delivery ist optional und darf nur redigierte Events senden. Webhook-
Retries sind begrenzt und dürfen keinen Provider-Request blockieren.

### 2.4 Identitäten

Jeder Request erhält beim Eintritt:

- `request_id`: eindeutig und nicht vom kurzen Modellnamen abgeleitet;
- `correlation_id`: verbindet Request, Provider-Versuche und Audit-Events;
- `tool_label`: interne Diagnoseinformation, niemals Public-Header;
- `stream_flag`: Teil des Request-Vertrags und der Retry-Entscheidung.

---

## 3. Destillierte Konzepte

Die folgenden Muster sind eigenständig formuliert. Ihre Herkunft ist für LIMEN
irrelevant; entscheidend ist, dass jedes Muster einen klaren Zweck, Owner und
Testvertrag besitzt.

### 3.1 Persistenz- und Transaktionsmuster

| Konzept | LIMEN-Anwendung |
|---|---|
| SQLite WAL, Foreign Keys und Busy Timeout | State und Queue ohne JSON-Datei-Drift |
| explizite `BEGIN IMMEDIATE`-Transaktion | atomarer Key-Claim und Zustandswechsel |
| versioniertes Schema | `PRAGMA user_version`, idempotente Migrationen |
| Migration-Sentinel | nur bei einer echten Altlast-Migration |
| Schema-Registry und Startup-Prewarm | DDL nicht im ersten Request |
| typisierte Events mit Correlation-ID | Audit, Watcher und UI-Timeline |
| Idempotency unter Concurrent Load | gleiche Anfragen parallel sicher deduplizieren |
| append-only Traceability | Entscheidungen bleiben nachträglich erklärbar |

### 3.2 Router- und Dispatcher-Muster

Slice 1+2 führt zwei kleine, getrennte Verträge ein:

- `ModelConfig` beschreibt genau ein Modell unabhängig von den Provider-Keys;
- `scan_request()` berechnet lokal einen deterministischen Größen-/Komplexitäts-
  Score und emittiert `request.scanned` in den Audit-Kanal.

Die Messung ist keine Provider-Verfügbarkeitsprüfung und kein stilles Routing.
`model="auto"`, Online-Katalogprüfung und Eskalationsketten bleiben ein
separater Folgeslice.

| Konzept | LIMEN-Regel |
|---|---|
| ein zentraler Provider-Call | genau ein Dispatch- und Retry-Orchestrator |
| deklarative Registry und Capability-Gates | Modelle, Rollen und Fähigkeiten vor Auswahl prüfen |
| Rate-Limit-Kaskade und Provider-Skip | `rate_limited` eigener Failure-Type; Scope bleibt sichtbar |
| datenbasierte Scores | Metriken beeinflussen Routing erst ab ausreichender Beobachtung |
| kanonischer Request-Builder | Adapter, Simulation und Tests verwenden denselben Vertrag |
| benannte Route-Map | keine lange Inline-if/else-Kette |
| atomare Zustandswechsel | jeder mehrteilige Übergang ist transaktional und testbar |
| falsifizierbare Optimierung | messbar, reproduzierbar, isoliert, reversibel, negativ getestet |

### 3.3 Bewusst nicht in den Kern

- Memory-, Lern-, Graph-, Reward-, Replay- oder autonome Orchestrator-Schichten;
- pauschale Kapazitätsmultiplikation durch die Anzahl von Keys;
- blindes Fallback bei ungültigen Payloads oder bereits begonnenen Streams;
- Inline-/Experimental-Duplikate;
- unredigierte Secrets und Providerantworten im Audit- oder UI-Kanal.

Die Konzepte werden adaptiert, nicht kopiert. LIMEN erhält eigene Datenmodelle,
Namen, Tests und Verantwortungsgrenzen. Zusätzlich gilt: keine breiten
`except Exception: pass`-Handler, kein stilles Fehler-Verschlucken und nur
konkrete Recovery-Aktionen mit konkreten Exception-Typen.

### 3.4 Bewusst nicht übernommen

- Lern-, Reward-, Knowledge-Graph-, Replay- und autonome Orchestrator-Schichten:
  gehören nicht in einen transparenten Forward-Proxy.
- mehrteilige DB-Isolation: LIMEN ist zunächst eine einzelne lokale DB.
- zusätzlicher Tool- oder Transport-Layer: kein neuer Kanal ohne Vertrag.
- Snapshot-/Response-Cache im MVP: LLM-Requests sind nicht pauschal sicher
  deduplizierbar.
- heuristische „5 Keys = 5-fache Kapazität“: Provider-Limits können account-,
  modell- oder providerweit gelten.
- blindes Fallback bei jedem Fehler: falsche Payloads und bereits gestartete
  Streams dürfen nicht wiederholt werden.
- `inline_*`- oder Experimental-Duplikate: ein Pfad, ein Owner, ein Testvertrag.

---

## 4. Zentrale Architektur

```text
CLI-AI-Tool / äußere Kompatibilitätsschicht
        │ OpenAI-kompatibler Request
        ▼
┌──────────────────────────────────────────────────────────────┐
│ LIMEN HTTP Layer                                             │
│ Contract validation · request/correlation IDs · health       │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Request Coordinator                                          │
│ queue policy · retry budget · stream boundary · error map    │
└──────────────┬───────────────────────────────┬───────────────┘
               ▼                               ▼
      ┌────────────────┐              ┌───────────────────────┐
      │ Pool/Route     │              │ Persistence           │
      │ Manager        │◄────────────►│ SQLite WAL            │
      │ registry/score │              │ keys/queue/events     │
      └───────┬────────┘              └───────────────────────┘
              ▼
      ┌────────────────┐
      │ ProviderAdapter│  ← one interface, provider-specific HTTP only
      │ deployment set │
      └───────┬────────┘
              ▼
        Provider API
```

### 4.1 Zuständigkeiten

```text
src/limen/
├── api/                 # FastAPI-Routen, OpenAI-Vertrag, Control-Center-HTML
├── config/              # TOML-Laden, Validierung, keine Secrets in Logs
├── adapters/            # ein Adapter pro Provider, kein Routing
├── routing/             # Registry, Capability-Matrix, Pool, Pipeline, Scanner
├── resilience/          # Failure-Classifier, Retry/Backoff/Circuit-Regeln
├── persistence/         # SQLite, Schema, Migrationen, AuditLog, Queue/Idempotency
├── schemas/             # Domain-Typen (ChatCompletionRequest etc.) — kein HTTP
├── templates/           # Leitstand-HTML (ausgelagert aus routes/public.py)
├── workers/             # QueueProcessor, Reaper, Heartbeat
└── cli.py               # init/start/opencode; keine Business-Logik inline
```

### 4.2 Provider- und Limit-Scope

Jedes Deployment erhält explizite Kapazitätsmetadaten:

```yaml
limit_scope: key | account | provider | model | unknown
rpm: integer|null
itpm: integer|null
otpm: integer|null
source: configured | response_header | observed | unknown
confidence: configured | observed | provisional
```

Ein Key darf nur dann als unabhängige Kapazität gezählt werden, wenn `limit_scope`
und Account-Zugehörigkeit das rechtfertigen. Bei `account` oder `unknown` wird
konservativ geteilt statt multipliziert.

### 4.3 Secrets und Konfiguration

API-Keys in `[providers.<name>].keys` unterstützen `${ENV_VAR}`-Auflösung:

```toml
keys = ["${GROQ_API_KEY}", "${GROQ_BACKUP_KEY}"]
```

Unbekannte Variablen bleiben literal (`${MISSING}`) und führen zu einem
401/403 beim Provider-Call — keine stillschweigende Null-Key-Anfrage.
Der `audit_token_secret` wird beim Start geprüft: der Beispiel-Wert
`REPLACE_ME_WITH_RANDOM_HEX` erzeugt eine Warnung auf stderr.

### 4.4 Admission Control

`[queue]` definiert harte Grenzen für die Warteschlange:

```toml
[queue]
max_pending = 500        # max. wartende Requests; 503 bei Überschreitung
max_wait_seconds = 30     # Retry-After-Header bei Queue-Voll
lease_seconds = 60        # Lease-Dauer für in_flight-Einträge
```

Die Prüfung erfolgt **vor** dem Enqueue — ein voller Queue liefert sofort
`503 queue_full` mit `Retry-After`-Header.

### 4.5 Cold Start und Routing

- Primary-/Priority-Order kommt aus der Registry.
- Health/Fallback darf die Priority nur übersteuern, wenn der Zustand belegt ist.
- Metriken werden erst ab einer Mindestzahl von Beobachtungen verwendet.
- Ohne Metriken keine Scheingenauigkeit durch Modellnamen wie `free`, `flash`
  oder `70b`.
- Capability-Matrix prüft Modell, Stream, Tool-Calls und gewünschte Rolle.
- `provider -> adapter -> request builder` wird nur einmal definiert.

---

## 5. Failure- und Retry-Modell

### 5.1 Failure-Types

`rate_limited` ist ausdrücklich ein eigener Typ. Die vollständige Liste lautet:

| Typ | Erkennung | Reaktion |
|---|---|---|
| `rate_limited` | HTTP 429, Provider-Body oder Limit-Header | `Retry-After` als Untergrenze, Backoff + Jitter, Scope beachten |
| `provider_unreachable` | DNS, Connect-/Read-Timeout, HTTP 5xx | begrenztes Retry mit anderem kompatiblem Deployment |
| `key_quota_exhausted` | 402 oder belastbares Quota-Muster | Key/Account gemäß Scope sperren, kein blindes Wiederholen |
| `key_revoked` | 401/403 oder belastbares Revocation-Muster | Key `dead`, manuelle Aktion erforderlich |
| `request_invalid` | 400, invalides Modell/Payload | kein Retry; OpenAI-kompatibler Clientfehler |
| `request_too_large` | Budget/Kontextgrenze vor Provider-Call | kein Retry; klare 413/400-nahe Clientantwort |
| `worker_dead_with_request` | Heartbeat-Reaper nach durable Queue | Request atomar zurück auf `pending`, Event senden |
| `unhandled_error` | nicht klassifizierte Ausnahme | intern loggen, maximal ein sicherer Retry vor Stream-Beginn |

### 5.2 Retry-Regeln

- Kein Retry bei `request_invalid`, `request_too_large` oder bereits begonnenem
  Streaming-Output.
- `Retry-After` ist eine Mindestwartezeit, kein Vorschlag.
- Backoff enthält Jitter, damit parallele Requests keinen Thundering Herd bilden.
- Jeder Request hat ein maximales Retry-Budget und eine maximale Wartezeit.
- Ein Provider wird nicht dauerhaft deaktiviert, nur weil ein einzelner Key
  einen Fehler liefert. Key-, Account- und Provider-Zustand werden getrennt.
- Ein 429-Circuit-Breaker darf nur bei nachgewiesener provider-/accountweiter
  Kaskade öffnen. Keine pauschale 24-Stunden-Sperre.
- Nach dem ersten ausgegebenen Stream-Chunk ist der Request nicht mehr sicher
  wiederholbar. Der Client erhält einen protokollkonformen Streamfehler oder
  Disconnect; kein doppelter zweiter Completion-Versuch.

### 5.3 Events

```yaml
task.started:
  request_id: string
  correlation_id: string
task.completed:
  request_id: string
  provider_deployment: string
  duration_seconds: float
task.failed:
  request_id: string
  model: string
  stream_flag: bool
  failure_type: enum[8]
  attempts: list[string]
  waited_seconds: float
  correlation_id: string
key.state_changed:  # ← Phase 6 (geplant)
  key_id: fingerprint-only
  provider: string
  previous_status: string
  status: active|cooldown|dead
  reason: string
  http_code: integer|null
worker.dead:
  worker_id: string
  current_task_id: string|null
  missed_beats: integer
```

Payloads enthalten keine vollständigen API-Keys, Authorization-Header,
Provider-Response-Bodies oder Stacktraces.

---

## 6. Persistenz und Zustandsmodell

### 6.1 SQLite-Regeln

```yaml
database_path: ~/.limen/state.db
journal_mode: WAL
synchronous: NORMAL
foreign_keys: ON
busy_timeout_ms: 30000
transaction_mode: BEGIN IMMEDIATE for state claims/mutations
schema_version: PRAGMA user_version
```

Jede Connection wird über einen klaren Lifecycle erzeugt und beim App-Shutdown
geschlossen. Bei Async-Code darf synchrones SQLite-I/O nicht den Event-Loop
blockieren; Persistenzzugriffe laufen über einen dedizierten Worker oder eine
bewusst begrenzte Async-Integration.

### 6.2 Tabellen

```yaml
providers:
  key_id: text primary key              # deployment#3, kein Secret
  provider: text not null
  deployment: text not null
  api_key_fingerprint: text not null
  account_id: text|null                 # fingerprint/label, kein Secret
  limit_scope: key|account|provider|model|unknown
  status: active|cooldown|dead
  cooldown_until: iso8601|null
  last_used_at: iso8601|null
  priority: integer
  observed_rpm: integer|null
  observed_itpm: integer|null
  observed_otpm: integer|null
  meta_json: text

queue:
  id: text primary key
  body_json: text not null               # canonical, redacted-at-rest policy
  target_model: text not null
  tool_label: text|null
  stream_flag: boolean not null
  status: pending|in_flight|done|dead
  attempt_count: integer not null
  lease_until: iso8601|null
  created_at: iso8601 not null
  picked_up_at: iso8601|null
  finished_at: iso8601|null
  correlation_id: text not null

idempotency_keys:
  key: text primary key
  request_fingerprint: text not null
  operation: text not null
  expires_at: iso8601 not null
  result_json: text|null

events:
  id: integer primary key autoincrement
  event_type: text not null
  payload_json: text not null             # redacted
  timestamp: iso8601 not null
  correlation_id: text

worker_heartbeats:
  worker_id: text primary key
  last_beat_at: iso8601 not null
  state: idle|busy|dead
  current_task_id: text|null
  beat_count: integer not null

schema_meta:
  key: text primary key
  value: text not null
```

`providers` speichert niemals vollständige API-Keys. Die effektiven Secrets
kommen ausschließlich aus geschützter Config/Environment und werden nur im
Adapter-Request verwendet.

### 6.4 Events-Prune

Die `events`-Tabelle wächst im Betrieb unbegrenzt. Der Reaper-Loop (15s-Intervall)
ruft `prune_events(keep_count=100_000)` auf und löscht die ältesten Einträge
oberhalb dieser Grenze. Kein TTL-basiertes Pruning — reines Row-Count-Limit.

### 6.3 Queue- und Idempotency-Vertrag

Queue wird vor Heartbeat/Reaper implementiert. Ein Worker claimt einen Request
atomar (`pending` → `in_flight`) mit Lease. Bei Prozessende werden abgelaufene
Leases beim Start wieder `pending`.

Idempotency ist nicht „jeder gleiche LLM-Request wird gecacht“:

- nur Requests mit sicherem, vollständig kanonisiertem Fingerprint;
- `stream=true` zunächst ausgeschlossen;
- Tool-Calls, nichtdeterministische Parameter und unbekannte Semantik zunächst
  ausgeschlossen;
- TTL und Resultatgröße begrenzt;
- Deduplizierung: `check_idempotent()` wird **vor** `store_idempotent()`
  aufgerufen — sowohl im API-Pfad (`dispatch.py`) als auch im Worker-Pfad
  (`worker.py`). Ein Cache-Treffer überspringt den Provider-Call komplett.

Response-Cache und Snapshot-Cache sind im MVP deaktiviert. Aktivierung braucht
einen eigenen Benchmark und negative Tests gegen falsche Wiederverwendung.

---

## 7. Control Center

Das Control Center ist keine dekorative TUI und kein abgespeckter Statusscreen.
Es ist die lokale Leitstelle für die komplette, redigierte Laufzeitrealität.
Die Implementierungsphasen bestimmen nur die Reihenfolge, in der die Daten dafür
entstehen — nicht den Funktionsumfang der Zieloberfläche.

### 7.1 Live-Arbeitsstatus

Der Status trennt Prozessleben von echter Arbeit:

```yaml
activity:
  state: active | idle | stale | degraded | stopped
  last_heartbeat_at: iso8601|null
  last_progress_at: iso8601|null
  last_completed_request_at: iso8601|null
  active_requests: integer
  queue_depth: integer
  worker_count: integer
  current_phase: string|null
  stale_after_seconds: integer
```

`active` erfordert aktuellen Heartbeat und aktuellen Fortschritt. Ein Prozess,
der nur Heartbeats sendet, gilt nicht automatisch als aktiv. `stale` bedeutet,
dass der Prozess erreichbar ist, aber seit dem konfigurierten Intervall keinen
belegten Fortschritt erzeugt hat. `degraded` bedeutet, dass der Dispatcher lebt,
aber eine relevante Kapazität, Persistenz oder Route eingeschränkt ist.

### 7.2 Dispatcher-Fluss

Die Hauptansicht zeigt jeden Request als echten, korrelierten Zustandspfad:

```text
INCOMING → QUEUE → CLAIM → ROUTE DECISION → DEPLOYMENT ATTEMPT
    → RETRY / COOLDOWN / FALLBACK → COMPLETED | FAILED
```

Jeder Knoten liefert mindestens Zeitstempel, Status, Wartezeit, Versuchszähler
und Correlation-ID. Animierte Punkte dürfen nur aus echten Events entstehen;
die Oberfläche simuliert keine Aktivität, wenn kein Fortschritt belegt ist.

### 7.3 Request-Inspector

Ein ausgewählter Request erklärt nicht nur das Ergebnis, sondern die komplette
Entscheidungskette:

```yaml
request_inspector:
  request_id: string
  model: string
  status: queued | in_flight | completed | failed
  attempts: integer
  elapsed_ms: integer
  queue_wait_ms: integer
  selected_deployment: string|null
  routing_reasons: [string]
  rejected_candidates: [{deployment: string, reason: string}]
  limit_scope: key | account | provider | model | unknown
  effective_limits: object
  related_events: [event_id]
```

Die UI erklärt zum Beispiel: Fähigkeit nicht vorhanden, Deployment im Cooldown,
Account-Limit erreicht, Priorität übersteuert oder Fallback nach Timeout. Sie
zeigt keine vollständigen Keys, Authorization-Header oder unredigierten Bodies.

### 7.4 Kontrollflächen und Slider

Laufzeitgrenzen werden als gewünschter, effektiver und erzwungener Wert gezeigt:

| Grenze | Wirkung |
|---|---|
| maximale Parallelität | Anzahl gleichzeitiger Provider-Aufrufe |
| Queue-Limit | maximale wartende Requests |
| Request-Rate | lokale Obergrenze neuer Requests pro Sekunde |
| Retry-Budget | maximale Versuche pro Request |
| maximale Wartezeit | Queue- und Retry-Wartebudget |
| Rate-Limit-Cooldown | Mindestwartezeit nach `rate_limited` |
| Timeout-Budget | getrennte Connect-, Write-, Read- und Pool-Grenzen |
| Deployment-Gewichtung | bevorzugte Verteilung ohne Capability-Verletzung |
| Batch-Größe | Anzahl gebündelter Einheiten, wenn der Vertrag dies erlaubt |

Jede Änderung läuft durch `preview → validate → apply → audit`. Die Preview zeigt
neben dem neuen Wert erwartete Queue-Länge, Parallelität, Limit-Risiko und den
Grund, warum ein effektiver Wert niedriger als der Wunschwert sein kann. Apply
gilt standardmäßig für neue Requests; laufende Requests werden nicht heimlich
umkonfiguriert. Ein Reset auf sichere Defaults ist immer verfügbar.

### 7.5 Simulation

Die Simulation verwendet denselben Request-Builder, dieselbe Registry und dieselbe
Routingentscheidung wie der echte Pfad, führt aber keine externe Anfrage aus.
Sie vergleicht aktuelle und vorgeschlagene Grenzen und zeigt:

- erwartete Queue-Tiefe und Wartezeit;
- Verteilung auf Deployments;
- mögliche Rate-Limit-Kaskaden;
- Retry- und Fallback-Anteile;
- Kapazitätskonflikte aus `key`, `account`, `provider`, `model` oder `unknown`;
- Unterschiede zwischen Wunschwert und effektivem Wert.

Simulationsergebnisse werden als Simulation markiert und niemals als echte
Laufzeitaktivität in die Erfolgsmetriken geschrieben.

### 7.6 Control-Center-Vertrag

```yaml
control_center:
  read:
    - GET /v1/_internal/status
    - GET /v1/_internal/events
    - GET /v1/_internal/requests/{request_id}
    - GET /v1/_internal/limits
  write:
    - POST /v1/_internal/simulate       # ← Phase 6B (geplant)
    - POST /v1/_internal/limits/preview   # ← Phase 6B (geplant)
    - POST /v1/_internal/limits/apply     # ← Phase 6B (geplant)
    - POST /v1/_internal/limits/reset     # ← Phase 6B (geplant)
  requirements:
    - audit_auth
    - localhost_only
    - redacted_payloads
    - atomic_config_update
    - audit_event_for_each_apply_or_reset
```

Jede UI-Steuerung ist optional; ein Ausfall der Oberfläche darf Requests,
Persistenz und Dispatcher nicht stoppen. Ein Ausfall des Audit-Streams darf
sichtbar als `observability_degraded` erscheinen, aber keine Aktivität vortäuschen.

## 8. Plan-of-Record: Umsetzungsphasen

Phasen bleiben sequenziell. Keine Phase gilt wegen „Code vorhanden“ als erledigt;
das jeweilige Reset-Kriterium und die Tests müssen grün sein.

### 8.0 MVP-Schnitt und erster Live-Test

Der MVP ist bewusst klein: **Phase 0 + Phase 1**, ein lokaler OpenAI-kompatibler
`stream=false`-Pfad und genau ein echter Provider-Key für den ersten Live-Test.
Der MVP beweist den Kernpfad; er ist noch kein Multi-Provider- oder Streaming-
Release.

#### MVP kann

- `limen init` erstellt eine owner-only SQLite-WAL-Datenbank;
- `limen start` startet den lokalen Dienst auf dem konfigurierten Port (Default 8000);
- `GET /health` meldet Prozess- und Persistenzzustand;
- `GET /v1/models` liefert nur konfigurierte Modelle;
- `POST /v1/chat/completions` akzeptiert `stream=false`;
- ein deklarierter Provider-Adapter ruft den echten Provider auf;
- Fehler werden im OpenAI-Format ausgegeben, ohne Provider- oder LIMEN-Debugheader;
- ungültige Requests werden nicht wiederholt;
- Provider-429 wird begrenzt, mit `Retry-After` und Backoff als internem
  `rate_limited`-Failure-Type behandelt; persistente Audit-Ausgabe folgt in Phase 4;
- der gleiche Pfad läuft vollständig mit `httpx.MockTransport`, ohne echten Key.

#### MVP kann ausdrücklich noch nicht

- `stream=true`, Tool-Call-Kompatibilität oder automatische Retries nach dem
  ersten Stream-Chunk;
- Multi-Provider-Rotation, Key-Pool, Queue-Leases, Crash-Recovery oder SSE-Audit;
- eine belastbare Kapazitätsaussage aus mehreren Keys;
- LAN-Betrieb, Authentifizierung der Public-API oder Produktionsbetrieb.

#### Reihenfolge mit Reset-Gates

1. **Foundation bauen:** Paketstruktur, Config-Modelle, Localhost-Rejection,
   SQLite-Schema/WAL, atomare Transaktion und `limen init`.
   Gate: Phase-0-Unit- und Persistenztests grün; keine echte Provider-Anfrage.
2. **Referenzadapter bauen:** kanonischer Request-Builder, ein Adapter,
   `/health`, `/v1/models`, `stream=false`-Contract und OpenAI-Fehler-Mapping.
   Gate: Mock-Provider-E2E grün; Ruff, mypy und pytest grün.
3. **Resilienz vor Live-Schaltung:** 400, 401/403, 429, 5xx, Timeout und „kein
   passender Key“ deterministisch testen. Nur erlaubte Fehler dürfen retryen.
   Gate: kein Retry bei invalidem Request, begrenztes Retry bei 429/5xx,
   Secretsafe-Logs und keine Debugheader.
4. **Mock-E2E und Goose-Gate ausführen:** Dienst starten, `/health`, `/v1/models`
   und eine Mock-Completion mit `curl` prüfen. Danach den gleichen nicht-streamenden
   Mock-Pfad mit Goose (Block) als Desktop-Client ausführen. Die minimale Web-UI
   muss erreichbar sein und denselben Health-Zustand anzeigen; ein UI-Ausfall darf
   den API-Pfad nicht stoppen.
   Gate: localhost-only, DB beschreibbar, Modell sichtbar, Mock-Completion 200,
   Goose-Request erfolgreich, UI erreichbar.
5. **Live-Test vorbereiten:** vor Aktivierung des Keys Provider, Base-URL, konkretes
   Modell, Limit-Scope und Kosten-/Quota-Risiko in der owner-only Config prüfen.
   Ein `<configured-model>`-Platzhalter ist nur in der Vorlage erlaubt, nicht im
   ausgeführten Gate. LIMEN darf eingehende `Authorization`-Header nicht an den
   Provider weiterleiten; die Public-API bleibt `auth: none`.
6. **Erster Live-Test:** einen kurzen, nicht sensiblen Prompt gegen den konkret
   freigegebenen Provider senden und danach bewusst einen erwarteten Clientfehler
   prüfen. Bei unbekanntem Modell, fehlendem Key, 401/403, Timeout oder Quota-
   Warnung sofort abbrechen. Nach jedem Test `/health` und die Secretsafe-Logs
   prüfen.
   Gate: eine valide Completion, eine valide OpenAI-Fehlerantwort, keine Secrets
   in Logs/Events, Prozess bleibt nach dem Fehler gesund.
7. **MVP einfrieren:** Providername, Modell, Testzeitpunkt, Ergebnis und bekannte
   Grenzen dokumentieren; Key wieder deaktivieren/rotieren, falls er temporär war;
   Status in README und CHANGELOG aktualisieren. Erst dann Phase 2 freigeben.

#### Runbook für den ersten Live-Test

Das Runbook setzt zwei Terminals voraus: `limen start` läuft in Terminal 1,
Smoke- und Live-Requests in Terminal 2. Der konkrete Stop-Befehl gehört zum
CLI-Vertrag von Phase 0 und wird nicht vorweg erfunden.

```bash
# 0. Port prüfen (Default 8000, Override via [server].port in config.toml)
ss -ltn "sport = :8000"  || echo "Port 8000 belegt — config.toml anpassen"

# 1. isolierte Umgebung und Konfiguration
uv sync
cp config.toml.example ~/.config/limen/config.toml
chmod 600 ~/.config/limen/config.toml
$EDITOR ~/.config/limen/config.toml

# 2. Foundation und lokaler Smoke-Test
limen init
limen start                         # in Terminal 1; Tests in Terminal 2
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/v1/models

# 3. Mock- und Goose-Gate ohne echten Provider-Key
#    Mock-Transport und Goose-Test laufen über die Contract-Suite.
uv run pytest -q tests/integration/test_single_provider_flow.py

# 4. Echter, nicht-streamender Test — Key niemals in die Shell schreiben
#    Vorher Provider, Modell und Quota-Risiko in config.toml konkret prüfen.
curl -fsS http://127.0.0.1:8000/v1/chat/completions \\
  -H 'Content-Type: application/json' \\
  -d '{"model":"<validated-configured-model>","messages":[{"role":"user","content":"Reply with exactly: LIMEN live test passed."}],"stream":false}'

# 5. Nach dem Test in Terminal 1: Prozess kontrolliert stoppen und Key deaktivieren
#    Der konkrete Stop-Befehl wird mit dem CLI-Vertrag von Phase 0 festgelegt.
```

Das Runbook ist erst ausführbar, wenn Phase 0/1 implementiert und die lokale
Contract-Suite grün ist. `<configured-model>` bleibt ein Platzhalter, damit kein
Provider- oder Modellname zum versteckten Vertrag wird. Der Live-Test beweist
Erreichbarkeit und Contract-Semantik, nicht Provider-Stabilität oder kostenloses
Kontingent.

### Phase 0 — Contract und Foundation

**Scope:** Paketstruktur, TOML-Validierung, SQLite WAL, Schema-Versionierung,
Migration-Sentinel nur bei Bedarf, atomare Transaktion, minimales typed Event-
Modell, `limen init`.

**Reihenfolge-Hinweis:** Phase 0 baut nur die Foundation. Die genannten
Funktionen sind dadurch nicht verboten oder aus der Zielarchitektur entfernt;
sie erhalten später eigene Verträge, Datenpfade und Tests.

**Implementierungsstand:** Config-Loader, Localhost-Rejection, SQLite-WAL mit
Schema-Version 1, atomare Transaktionen, `limen init`/`limen start`, `/health`,
`/v1/models`, lokale Control-Center-Startseite, Request-Body-Limit und
Foundation-Tests sind implementiert. `/health` meldet `degraded`, wenn SQLite
lebt, aber kein aktiv konfiguriertes Modell verfügbar ist. Legacy-Migrationen
existieren noch nicht; der `user_version`-
Sentinel lehnt unbekannte höhere Versionen ab. Das Phase-0-Reset-Gate ist
geschlossen: Ruff, mypy und pytest laufen in der per `uv sync --extra dev`
reproduzierbaren Dev-Umgebung grün. Eine bekannte, nicht blockierende
StarletteDeprecationWarning aus dem Testclient bleibt als Dependency-Restschuld
für die nächste Toolchain-Pflege dokumentiert.

**Akzeptanzkriterien nach Implementierung:**

- `test_config_rejects_invalid_local_bind` grün;
- WAL, Foreign Keys und Busy Timeout sind per Test sichtbar;
- Schema-Init ist wiederholbar und erzeugt keine doppelten DDL-Effekte;
- Migrationen sind idempotent und bei echten Altlasten sentinel-geschützt;
- Transaktionsrollback lässt keinen halben Key-Zustand zurück;
- `limen init` erzeugt eine geschützte lokale DB mit Basistabellen;
- `limen start` startet Backend + Web-UI (Control Center) als gemeinsamen Prozess;
- Ruff, mypy und pytest laufen nach dem Anlegen von Quellcode und Tests grün.

**Reset:** alle Foundation-Tests grün, Doku synchronisiert.

### Phase 1 — Single-Provider E2E

**Scope:** ein zentraler Provider-Adapter als Referenzadapter,
ein Key, ein Worker/Request-Pfad, OpenAI-Contract, `/v1/models`, `/health`.
Streaming wird hier nur noch nicht aktiviert; es ist kein Zielverbot.
Erster externer Smoke-Test mit Goose (Block) als Desktop-Test-Client.

**Akzeptanzkriterien:**

- Mock-Provider liefert eine valide 200-Completion;
- kein Key liefert eine OpenAI-kompatible 503-Antwort ohne Panic;
- ungültiges Modell/Payload wird nicht retried;
- Upstream-429 wird mit `rate_limited`, `Retry-After` und begrenztem Retry geprüft;
- Public-Response enthält keine LIMEN-/Provider-Debugheader;
- `httpx.AsyncClient` wird über App-Lifespan erzeugt und geschlossen;
- mindestens ein Integrationstest läuft ohne echten Provider-Key.

**Implementierungsstand:** OpenAI-kompatible Public-Schemas,
OpenAI-kompatibler Referenz-Adapter mit Key-Rotation und rotierten
Redaction-Headern, lifespan-eigener `HttpTransport`, `ProviderRegistry`
nach Capabilities/Priority, `Dispatcher` mit Single-Deployment-Auswahl,
Failure-Classifier (sieben Typen, Body-Keyword-Erkennung) und
Public-Error-Renderer, Integrationstests für Happy-Path, 503, 400, 429,
401, 502, Header-Hygiene und Mock-Transport. `pytest`/`ruff`/`mypy`
laufen grün (35 Tests). Live-Smoke gegen `/health`, `/v1/models` und
`POST /v1/chat/completions` mit nicht erreichbarem Provider liefert
`502 provider_unreachable` mit redacted Original-Body.

**Reset-Gate-Checkliste:** [`docs/phase1-reset-gate.md`](../docs/phase1-reset-gate.md).
Verbindlich offline: `scripts/phase1_smoke.sh` (18/18 grün ohne echten
Provider-Key). Goose-Plu-in-Felder sind in der Checkliste tabelliert;
Streaming wird in Phase 1 weiterhin mit `400 request_invalid`
abgelehnt.

**Reset:** ein externer Test-Client (Goose Desktop) kann den nicht-streamenden,
gemockten End-to-End-Pfad stabil nutzen; `POST /v1/chat/completions` und
`GET /v1/models` liefern valide, OpenAI-kompatible Antworten.

### Phase 2 — Registry, Multi-Provider und Resilienz

**Scope:** zentrale Provider-Registry, Adapter-Interface, mehrere Deployments
nur nach Capability-Prüfung, Key-Pool, Rotation, Failure-Classifier,
Cooldown und limit-scope-aware Fallback.

**Vertragsanker:** [`docs/phase2-routing-contract.md`](../docs/phase2-routing-contract.md)
definiert Key-Pool-Rotation, `limit_scope`-Semantik, Cooldown-Tabelle und
Audit-Pflichten. Test-Scaffold ohne Stub: [`tests/integration/test_phase2_routing_contract.py`](../tests/integration/test_phase2_routing_contract.py)
mit 25 contract-Asserts und 2 statischen Drift-Guardians, alle Phase-2-Asserts
per `@pytest.mark.skip` belegt bis die Implementierung steht.

**Akzeptanzkriterien:**

- kein Provider-spezifischer Dispatch-Code in API-Handlern;
- Registry ist die einzige Quelle für Base-URL, Modell, Capabilities und Priority;
- Rotation ist atomar und unter parallelen Claims duplikatfrei;
- `rate_limited`, Quota, Revoked, Invalid und Unreachable werden getrennt getestet;
- `Retry-After` und exponentieller Backoff mit Jitter werden getestet;
- accountweite Limits verhindern falsche Kapazitätsmultiplikation;
- Cold Start verwendet Priority, nicht Modellnamen-Heuristiken;
- jeder Adapter nutzt denselben kanonischen Request-Builder.

**Reset:** mind. 25 vertragliche Asserts in `test_phase2_routing_contract.py`
grün ohne Skip-Marker, plus 30+ deterministische Mock-Requests zeigen
korrekte Auswahl, Rotation, Fallback und Zustandsrückkehr ohne
429-Death-Loop.

### Phase 3 — Durable Queue und Crash-Recovery

**Scope:** persistente Queue, atomare Claim-/Lease-/Finish-Übergänge, ein Worker
zuerst, danach konfigurierbare Workerzahl, Startup-Recovery, eingeschränkte
Idempotency.

**Akzeptanzkriterien:**

- 20 pending Requests werden nach kontrolliertem Prozessabbruch wieder aufgenommen;
- abgelaufene `in_flight`-Leases werden genau einmal zurückgesetzt;
- parallele gleiche Idempotency-Keys erzeugen höchstens einen Provider-Call;
- TTL-Cleanup funktioniert deterministisch;
- Queue-Cap und maximale Wartezeit verhindern Memory-Druck;
- keine synchronen DB-Langläufer blockieren den Async-Request-Loop.

**Reset:** Recovery- und Concurrent-Idempotency-Tests grün.

### Phase 4 — Audit, Heartbeat und Reporting

**Scope:** persistente typed Events, Audit-Auth, Status-Snapshot, SSE, Worker-
Heartbeat/Reaper nach vorhandener Queue, redigierte optionale Webhooks.

**Akzeptanzkriterien:**

- Audit ohne Token liefert 401, gültiges Token liefert nur redigierte Daten;
- `task.failed`, `key.state_changed` und `worker.dead` enthalten Correlation-ID;
- SSE beendet sich sauber bei Client-Disconnect;
- Reaper markiert einen Lease korrekt und erzeugt genau ein Worker-Event;
- Webhook-Timeout und Retry blockieren keinen Provider-Request;
- Public-API bleibt frei von Audit-Informationen.

**Reset:** lokaler Audit-Client kann Fehler live verfolgen, ohne den Router zu
beeinträchtigen.

### Phase 5 — Streaming und äußere Kompatibilitätsverträge

**Scope:** `stream=true` als eigener Vertrag mit `httpx.AsyncClient.stream()` und
FastAPI `StreamingResponse`; Chunk-/Disconnect-Tests; lokale Contract-Smoketests
für jede aktivierte äußere Kompatibilitätsschicht.

**Vertragsanker:** [`docs/phase5-streaming-contract.md`](../docs/phase5-streaming-contract.md)
ist die einzige Wahrheit für SSE-Wire-Format, No-Retry-After-First-Chunk und
Header-Policy. Test-Gerüst ohne Stub: [`tests/integration/test_phase5_streaming_contract.py`](../tests/integration/test_phase5_streaming_contract.py)
mit 12 contract-Asserts, alle aktuell per `@pytest.mark.skip` markiert bis die
Implementierung steht.

**Regeln:**

- Retry nur vor dem ersten ausgelieferten Chunk;
- nach Stream-Beginn kein automatischer zweiter Completion-Call;
- `async with` schließt Upstream-Streams auch bei Client-Abbruch;
- jede Übersetzungsschicht bleibt ein expliziter Vertrag außerhalb des Router-
  Kerns und wird nicht stillschweigend nachgebaut;
- Tool-, Prompt- und Streaming-Semantik werden nur nach positivem Smoke-Test
  aktiviert.

**Reset:** Streaming-Tests für Erfolg, Upstream-Abbruch, Client-Abbruch,
Backpressure und „kein Retry nach erstem Chunk“ sind grün, alle 12 Asserts in
`test_phase5_streaming_contract.py` ohne Skip-Marker.

### Phase 6A — Betriebs-Härtung

**Scope:** systemd-User-Unit, `IPAddressDeny=any` plus localhost allowance,
Config-Drift-Event, Dateirechte, Token-/RPM-/TPM-Tracking.

**Akzeptanzkriterien:**

- systemd-Unit erlaubt keine LAN-Exposition;
- Config und DB sind owner-only geschützt;
- Drift erzeugt eine Warnung, aber zerstört keine laufenden Requests;
- Secrets erscheinen nicht in Logs, Events, Benchmarks oder Fehlern;
- Optimierungen haben messbare, reproduzierbare und negative Tests.

**Reset:** lokaler Betrieb ist reproduzierbar, auditierbar und reversibel.

### Phase 6B — Diagnose- und Komfortschichten

**Scope:** heuristische Diagnose, optionaler Diagnose-Key, lokale Bedienoberflächen
und weitere Komfortfunktionen. Diese Phase beschreibt die Implementierungs-
reihenfolge, keine Begrenzung der Ziel-Funktionalität.

**Akzeptanzkriterien:**

- Diagnose funktioniert ohne LLM-Key mit Heuristik-Fallback;
- Diagnosefehler blockieren weder HTTP-Requests noch Persistenz;
- Bedienoberflächen zeigen effektive Werte, Entscheidungsgründe und Audit-Events;
- 100-Event-Belastungstest und Shutdown-Test sind grün.

**Reset:** Komfortschichten sind optional, reversibel und vom Router-Kern isoliert.

## 9. Tests und Falsifizierung

### 9.1 Werkzeuge

- `pytest`, `pytest-asyncio`, `pytest-cov`;
- `httpx.MockTransport` für Provider-Calls;
- FastAPI-Testclient für Public-/Audit-Verträge;
- temporäre SQLite-Dateien für WAL-/Migration-/Concurrency-Tests;
- keine echten Free-Tier-Provider in automatischen Tests;
- kein API-Key in Fixtures oder Testausgaben.

### 9.4 Externe Test-Clients

Die LIMEN-Public-API wird gegen reale, externe AI-Coding-Desktop-Apps validiert.
Diese Clients sprechen natives OpenAI-Protokoll und werden mit `OPENAI_API_BASE`
bzw. `OPENAI_HOST` auf den LIMEN-Port umgebogen (Default `http://127.0.0.1:8000`).

| Client | Rolle | Phase | Konfiguration |
|---|---|---|---|
| **Goose** (Block) | Primärer Test-Client | Phase 1+ | `OPENAI_HOST` auf LIMEN-Port (Default 8000), Dummy-API-Key |
| **Open Interpreter** | Backup-Client | Phase 1+ | Desktop: Settings → Custom Endpoint → LIMEN-Port/v1 (Default 8000), `wire_api: chat` |
| **Cline** (VS Code) | Streaming-/Tool-Härtetest | Phase 5+ | `apiBase:` auf LIMEN-Port (Default 8000) |

Auswahlprinzipien:

- Desktop-App (kein reines Terminal-Tool), GUI-first;
- OpenAI-kompatibler Custom-Endpoint ohne Provider-seitige Magie;
- Coding-Agent mit realen Multi-Step-Workflows;
- Open-Source, aktiv maintained;
- MVP (`stream=false`) muss ohne Streaming überleben.

Claude Code ist bewusst nicht als Test-Client aufgenommen: Es spricht Anthropics
API-Protokoll, nicht OpenAI. Eine Anthropic→OpenAI-Übersetzung ist eine äußere
Kompatibilitätsschicht und kein LIMEN-Kernvertrag.

### 9.2 Teststruktur

```text
tests/
├── unit/
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_dispatch_failure_audit.py
│   ├── test_internal_key_store.py
│   ├── test_resilience.py
│   └── test_scanner.py
├── integration/
│   ├── test_app.py
│   ├── test_audit_identity.py
│   ├── test_live_visualizer.py
│   ├── test_persistence.py
│   ├── test_phase1_dispatcher.py
│   ├── test_phase2_routing_contract.py
│   ├── test_phase3_queue.py
│   ├── test_phase4_audit.py
│   ├── test_phase5_streaming_contract.py
│   └── test_streaming_attempt_budget.py
└── scripts/
    └── test_launch_limen.py
```

### 9.3 Falsifizierungs-Checkliste

Vor jeder Änderung am Routing oder an einer Optimierung:

1. **Messbar:** Welche Metrik wird besser oder schlechter?
2. **Reproduzierbar:** Ist das Ergebnis in drei Mock-/Stressläufen stabil?
3. **Isoliert:** Ist die Ursache diese Änderung und nicht Provider-Rauschen?
4. **Reversibel:** Kann der alte Zustand reproduziert werden?
5. **Negativ getestet:** Gibt es einen Fall, in dem die Optimierung nicht greifen
   darf?
6. **SSOT geprüft:** Gibt es jetzt eine zweite Registry, Heuristik oder Route?
7. **Failure geprüft:** Was passiert bei 429, 5xx, 401, Disconnect und Crash?

## 10. Betrieb und Sicherheit

- Bind immer auf `127.0.0.1`; Konfiguration mit anderem Host wird abgelehnt.
- `config.toml` und `state.db` mit owner-only Permissions anlegen.
- Vollständige API-Keys niemals in SQLite, Logs, Events, Benchmarks oder Fehlern.
- Audit-Token aus sicherer Config/Environment laden; nicht in CLI-Argumente.
- Webhook-Payloads redigieren; URL und Header nicht in Public-Events zeigen.
- Provider-Response-Bodies kürzen und secretsafe speichern.
- HTTPX-Timeouts getrennt konfigurieren: connect, write, read, pool.
- Read-Timeout für normale und Streaming-Requests getrennt behandeln.
- AsyncClient im Lifespan verwalten, nicht pro Request neu erzeugen.
- Keine externen Research-/Provider-Calls während automatischer Tests.
- Jedes außerhalb der Runtime exponierte Secret muss vor Implementation geprüft,
  widerrufen oder rotiert und aus Dokumentation/Arbeitsdateien entfernt werden.
  Die Architektur wiederholt niemals secret-ähnliche Inhalte.

### 10.1 Launcher und Agent-Integration

[`scripts/launch_limen.py`](../scripts/launch_limen.py) ist die einzige
offizielle Brücke zu bestehenden Agent-Clients (Goose, Claude Code,
Open Interpreter, Aider, Continue.dev, opencode). Vertrag:

- Auto-Detection über Binary und Config-Pfad (kein Default-Verhalten
  ohne installiertem Tool).
- Modale Bestätigung vor jedem Schreibvorgang (Trockenlauf via
  `dry-run`).
- Backup-Konvention: `<datei>.bak.<unix-ts>` für YAML/JSON/TOML bzw.
  `<datei>.env.bak.<unix-ts>` für `.env`-Dateien.
- `restore <agent>` spielt den jüngsten Backup zurück; keine
  Mehrfach-Version-Pickers.
- Der Launcher ändert **nicht** LIMENs eigene Core-Module; nur
  Agent-Config-Dateien außerhalb des Repos.

**Seit v0.0.19** bietet LIMEN native Wire-Format-Übersetzer für
Claude Code und Codex, die keinen Launcher mehr benötigen:

- `POST /v1/messages` — Anthropic Messages API (non-stream + SSE),
  inkl. `[anthropic]` Modell-Alias-Mapping.
- `POST /v1/responses` — OpenAI Responses API für Codex (non-stream + SSE).
- `limen claude` / `limen codex` — CLI-Befehle schreiben die
  jeweilige Agent-Config direkt auf LIMEN.

- Der Launcher ändert **nicht** LIMENs eigene Core-Module; nur
  externe Config-Files werden angefasst, niemals Key-Material.

### 10.2 Live-E2E gegen Provider

[`scripts/live_e2e_groq.sh`](../scripts/live_e2e_groq.sh) ist die einzige
offizielle Live-Strecke für eine echte Provider-Verifizierung (Groq ist
das erste unterstützte Ziel). Vertrag:

- Strict Pre-Flight (`--check-only`) ohne Side-Effects inkl. `ss -ltn`-Port-Check.
- Key niemals in Klartext oder in Logs; Quelle ist `--key` (wiederholbar),
  `GROQ_API_KEY` oder interaktive Eingabe.
- **Multi-Key**: `--key gsk_aaa --key gsk_bbb` schreibt beide Keys in die
  TOML-Konfig — Key-Rotation im Dispatcher live testbar.
- **Streaming**: `--stream` setzt `stream: true` im Request-Payload;
  Streaming-Response wird auf `data:`-Zeilen geprüft.
- Pre-Flight `--check-only` prüft Port-Freiheit (`ss -ltn`), Repo, curl, jq.
- Artefakte landen in `mktemp -d` (kein CWD-Müll).
- Post-Flight: Audit-Verify via `/v1/_internal/events` prüft auf
  `task.completed`-Event.
- Failure-Map deckt 401/403, 429 (Cooldown), 5xx (kein Retry-Loop),
  ungültige Modell-ID, Port-Belegung und LIMEN-Startfehler ab; jede
  Variante hat einen eindeutigen Exit-Code.

### 10.4 Queue-Recovery-Test

[`scripts/recovery_test.sh`](../scripts/recovery_test.sh) testet die
`recover_leases()`-Pipeline isoliert — ohne echte Provider-Keys:

- Temp-DB + Config, `limen init`
- Injiziert einen `in_flight`-Queue-Eintrag mit abgelaufener Lease
- Startet LIMEN, prüft `queue.recovery`-Event in der DB
- Verifiziert Status-Änderung: `in_flight` → `pending` → `dead` (ohne Provider)
- Cleanup via `trap EXIT`

Mit echten Provider-Keys würde der recovered Task erfolgreich dispatched.

### 10.3 Goose-Desktop ↔ LIMEN ↔ Provider (Live-GUI-Runbook)

[`docs/goose-gui-live-plan.md`](../docs/goose-gui-live-plan.md) ist das
verbindliche Runbook für die **GUI-Live-Strecke** (Electron Goose statt
Skript-Pfad). Vertrag:

- **Drei Vertrauens­zonen:** Goose → LIMEN → Provider. Der echte Provider-Key
  liegt **nur** in LIMEN (TOML `keys` oder Env), nicht in Goose.
- **Phase A (LIMEN-Start):** Provider-Config mit `enabled = true`,
  ggf. Key-Patch in TOML; Smoke vor Goose grün.
- **Phase B (Goose-Patch):** `launch_limen.py dry-run goose` → `swap goose` →
  Goose neu starten (Electron lädt Config neu).
- **Phase C (Roundtrip):** ein bis zwei Mini-Round-Trips; Latenz
  Provider + LIMEN‑Overhead.
- **Phase D (Audit):** `~/.limen/state.db` zeigt pro Request
  `task.started` / `key.claimed` / `key.released` / `task.completed`
  ohne Klartext-Key (Redaction schon in Phase 1 erzwungen).
- **Phase E (Cleanup):** Goose-Close → `launch_limen.py restore goose` →
  LIMEN‑Stop → `unset GROQ_API_KEY`. Reihenfolge ist verbindlich.
- **Failure-Map** im Doc listet die gängigen Stolperfallen
  (Goose-Schema-Drift, 401/429, leeres Modell-Set, Audit-Leck) mit der
  jeweiligen Aktion.

Phase 1 kann **keinen** Auth-Bypass garantieren; `keys = []` führt aktuell zu
einer Anfrage ohne `Bearer`-Token. Live-Runs mit echtem Key erfordern bis
Phase 2 entweder den TOML-Patch (mit anschließendem Sed‑Restore) oder einen
Phase‑2‑Auth‑Adapter. Diese Einschränkung ist im Doc explizit rot
gekenn­zeichnet.

**Skript-Vorlauf-Integration:** §3.0 im Doc beschreibt die Verkettung mit
`scripts/live_e2e_groq.sh` — `--check-only` als risikofreier Pre-Flight,
`--keep-config` als Full-Run mit anschließendem Phase-A-Direkteinstieg. §4.0
zeigt die drei Workarounds (A: TOML-Patch, C: Skript-Override als
Phase-2-TODO, langfristig: `keys=["env:GROQ_API_KEY"]`). Die Verkettung ist
die *empfohlene* Sequenz, weil sie Pre-Flight und Cleanup deterministisch
kombiniert, statt zwei lose Enden.

## 11. Decisions-Log und offene Punkte

### 11.1 Entscheidungen

| ID | Datum | Entscheidung | Begründung |
|---|---|---|---|
| DEC-001 | 2026-08-07 | LIMEN bleibt ein eigenständiger Router | klare Verantwortungsgrenze: Routing vs. Memory |
| DEC-002 | 2026-08-07 | ein Benutzer/ein Rechner/localhost-only | kein Multi-Tenant- und LAN-Aufwand |
| DEC-003 | 2026-08-07 | `ARCHITECTURE.md` ist einzige Plan-of-Record-Datei | verhindert Drift zwischen Outline und Final-Plan |
| DEC-004 | 2026-08-07 | Queue vor Heartbeat/Reaper | Reaper braucht durable Zustandsübergänge |
| DEC-005 | 2026-08-07 | Streaming getrennt vom MVP | Retry-/Partial-Response-Semantik ist ein eigener Vertrag |
| DEC-006 | 2026-08-07 | `rate_limited` eigener Failure-Type | 429 ist weder Netzwerkfehler noch Quota-Death |
| DEC-007 | 2026-08-07 | Limit-Scope ist explizites Datenfeld | Keys multiplizieren nicht automatisch Account-Kapazität |
| DEC-008 | 2026-08-07 | zentrale Registry und zentraler Dispatch | parallele Provider-Pfade driften und verlieren Zustandskonsistenz |
| DEC-009 | 2026-08-07 | keine Inline-/Experimental-Duplikate | ein Owner, ein Vertrag, ein Testpfad |
| DEC-010 | 2026-08-07 | Konzepte werden adaptiert, nicht kopiert | LIMEN erhält eigene Domäne, Namen und Testverträge |
| DEC-011 | 2026-08-07 | Goose (Block) primärer externer Test-Client | Desktop-AI-Coding-App, natives OpenAI-Protokoll, `OPENAI_HOST`-Config; Open Interpreter als Backup |

### 11.2 Offene Punkte vor den jeweiligen Phasen

- **HF-001 / Phase 2:** Welche Provider-Limits sind accountweit und welche
  keyweit? Unbekanntes wird konservativ behandelt.
- **HF-002 / Phase 3:** Soll Queue bei Überlast warten oder sofort 503 liefern?
  Entscheidung hängt von gemessener lokaler Last ab; Default ist harter Cap plus
  503 nach kurzer Wartezeit.
- **HF-003 / Phase 4:** Webhook direkt in TOML oder deaktiviert? Default bleibt
  deaktiviert; kein Plugin-Loader im Kern.
- **HF-004 / Phase 5:** Kompatibilitätsversion und unterstützte Tool-/Stream-
  Semantik müssen mit einem echten lokalen Smoke-Test bestätigt werden.
- **HF-005 / Phase 6:** Diagnosezugriff bleibt getrennt vom User-Pool, falls ein
  Diagnose-LLM überhaupt aktiviert wird.

## 12. Glossar

- **Adapter:** Provider-spezifischer HTTP-Client. Er kennt URL/Auth/Response-
  Details, aber keine globale Routing-Policy.
- **Deployment:** Kombination aus Provider, Account/Key, Modell und Capabilities.
- **Failure-Type:** normalisierte interne Fehlerklasse mit definierter Reaktion.
- **Kompatibilitätsschicht:** externe Übersetzung oder Anpassung; nicht Teil des
  LIMEN-Kerncontracts, solange ihr Vertrag nicht bestätigt ist.
- **Limit-Scope:** Ebene, auf der RPM/TPM gelten: Key, Account, Provider, Modell
  oder unbekannt.
- **Pool:** auswählbare Deployments, nicht automatisch die Summe aller Keys.
- **Queue-Lease:** zeitlich begrenzte Besitzmarkierung eines `in_flight`-Requests.
- **SSOT:** Single Source of Truth; genau eine kanonische Registry oder Route.
- **Streaming Boundary:** Zeitpunkt des ersten an den Client gesendeten Chunks.
  Danach ist ein transparenter Retry nicht mehr sicher.
- **Plan-of-Record:** diese Datei; bei Widerspruch wird zuerst der Code geprüft,
  danach diese Datei aktualisiert.

---

*Stand: 2026-08-08 — Phasen 0–5 implementiert. Phase 6A (Betriebs-Härtung) ist der nächste Boss.*
