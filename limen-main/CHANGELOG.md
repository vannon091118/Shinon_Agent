# Changelog — LIMEN

Alle nennenswerten Änderungen an LIMEN werden hier dokumentiert.

## [0.0.20] — 2026-08-08

### Added
- **Claude-Code-Distribution:** `limen claude install` installiert eine gepinnte
  Claude-Code-Version (`@anthropic-ai/claude-code@2.1.226`) in
  `~/.limen/claude-code/` und schreibt einen Wrapper nach `~/.limen/bin/claude`.
- `limen claude update` — aktualisiert auf `@latest`.
- `limen claude version` — zeigt installierte Version.
- `limen claude config` — expliziter Subcommand für Config-Schreiben (ohne
  Subcommand wie vorher auch möglich).

### Changed
- **Keine hardcoded Claude-Modelle mehr.** `[anthropic]` ist jetzt ein freies
  `dict[str, str]` — User definieren eigene Alias-Keys. `AnthropicConfig`-Klasse
  entfernt.

## [0.0.19] — 2026-08-08

### Added
- **Anthropic Messages API:** `POST /v1/messages` (non-stream + SSE streaming) mit
  vollständiger Übersetzung Anthropic ↔ OpenAI. Unterstützt `system`, `stop_sequences`,
  `temperature`, `top_p`, `top_k`.
- **Codex Responses API:** `POST /v1/responses` (non-stream + SSE streaming) mit
  `response.output_text.delta`-Events.
- **`[anthropic]` Config-Sektion:** Modell-Alias-Mapping (sonnet/opus/haiku/fable +
  canonical IDs) → konfigurierte LIMEN-Modelle.
- **`limen codex` CLI:** Schreibt `~/.codex/config.toml` mit `wire_api = "responses"`
  und verweist auf LIMEN als Gateway.
- **Contract-Tests:** 15 Tests für Anthropic- und Codex-Endpunkte (Request-Parsing,
  Alias-Resolution, Stream-Flag, CLI-Config).

### Changed
- **AGENTS.md** auf 7 knappe Prinzipien reduziert — keine "Verboten"-Listen, keine
  langen Beispiele. Jede Regel ein Absatz.

## [0.0.18] — 2026-08-08

### Added
- **Content-Fingerprint-Idempotency:** `check_idempotent()` verwendet jetzt SHA-256
  über Modell + Messages + Parameter statt einer frischen UUID. Echter
  Cache-Treffer möglich — vorher war Idempotency de facto tot.
- **Key-State-Persistenz:** Key-Zustände (active/cooldown/dead) werden nach
  jedem Claim/Release in die `providers`-Tabelle geschrieben und beim Startup
  per Fingerprint-Matching wiederhergestellt. Überlebt Restarts — 429-Stürme
  bleiben gebannt.

### Changed
- **Generischer Fallback-Dispatcher:** Jedes unbekannte Modell wird wie `auto`
  geroutet — kein Hardcode mehr für Claude-IDs oder andere Agent-Modelle.
  Free-Tier-Deployments werden vor Paid-Modellen priorisiert.
- **Hardcoded Modelle restlos entfernt:** Keine `CLAUDE_MODEL_IDS`-, `providerModels`-
  oder `startswith("claude-")`-Strings mehr im Code. `/v1/models` zeigt nur
  echte Registry-Modelle + `auto`.

### Fixed
- **Streaming-Audit:** `task.failed`-Events schreiben die echte Versuchszahl aus
  `PipelineExhausted.attempts` statt hardcoded `1`. Non-Stream-Audit ebenso.
- **Key-State-Persistenz-Bugs (Review):** `cooldown_until` war immer `None`
  (tote Ternary). Recovery matched nach Fingerprint, nicht nach Raw-Wert.
  `AdapterRequestError`-Pfad schreibt jetzt korrekten Status.

## [0.0.17] — 2026-08-08

### Added
- Benannte API-Keys: Schlüssel-Panel mit Namensfeld, Canvas-Zonen zeigen
  benutzerdefinierte Namen, Key-Zonen anklickbar (→ Panel-Scroll).
- Key-Store persistiert jetzt `{key, name}` pro Provider (abwärtskompatibel
  zu Plain-String-Einträgen). Neue Endpunkte: `GET …/keys/{provider}/name`,
  `GET …/keys/names`.

### Changed
- **Schema-Extraktion:** Domain-Typen (`ChatCompletionRequest` etc.) aus
  `api/schemas.py` → `limen/schemas/`. Adapter, Routing & Worker importieren
  jetzt von `limen.schemas`, nicht mehr vom HTTP-Layer.
- **Audit-Extraktion:** `AuditLog`-Klasse aus `Database` → `persistence/audit.py`.
  `Database` delegiert `write_event`/`read_events`/`prune_events` dorthin.
- **UI-Template-Extraktion:** Leitstand-HTML aus `routes/public.py` (`_UI_HTML`-
  String-Literal) → `templates/leitstand.html` mit `_load_ui_html()`-Loader.
- **Streaming-Refactoring:** `stream_completion` delegiert Key-Walking an
  `run_pipeline(stream=True)` statt eigener While-True-Schleife zu führen.
- **`_ui_broadcast` dedupliziert:** `app.state.broadcast_ui_event` statt
  zweier identischer Closures in `app.py` und `public.py`.

### Fixed
- **Streaming-Audit ehrlich:** `key.released("success")`, `finish_task`,
  `task.completed` und `provider.responded` werden erst im
  `_wrapped_stream.finally`-Block nach tatsächlichem Stream-Ende geschrieben
  (vorher: vor dem ersten Byte → Audit log bei Stream-Abbruch).
- `PipelineExhausted.attempts` als Attribut exponiert → `task.failed`-Event
  hat echte Versuchszahl statt `0`.
- `OpenCode`-Config auf LIMEN-Port 18100 korrigiert.

## [0.0.16] — 2026-08-08

### Added
- `model="auto"` als Routing-Sentinel: LIMEN wählt automatisch das beste
  verfügbare Deployment anhand der konfigurierten Priorität und Kontextgröße.
- Routing-Einstellungen-Panel im Leitstand mit Live-Modellübersicht und
  Auto-Routing-Statusanzeige.
- `routing.auto` SSE-Event mit Kategorie, Score und Kontext-Tokens.
- `/v1/models` listet jetzt `model="auto"` als eigenes synthetisches Modell.
- `QueueProcessor` wendet Kontextfenster-Filterung auch im Recovery-Pfad an.

## [0.0.15] — 2026-08-08

### Added
- Deklarative Modell-Registry mit lokalem Request-Size-/Komplexitäts-Scan.
- Center-Gate-Canvas-Pipeline mit FIFO-Stau, Worker-Carry und Latenz-
  Streudiagramm für abgeschlossene Requests.
- Multi-Provider- und Queue-Recovery-E2E-Skripte sowie Audit-/Visualizer-
  Integrationstests.
- `limen`-Version aus einem zentralen Versionswert für App und User-Agent.


## [0.0.14] — 2026-08-08

### Added
- **Slice 1+2 Model Registry und Request-Scan.** Einzelne Modelle können
  über `[models.<name>]` unabhängig von Provider-Key-Konfigurationen gepflegt
  werden. Ein lokaler, deterministischer Scanner schreibt Größen-, Struktur-
  und Komplexitätswerte als `request.scanned` ins Audit; explizite Modelle
  bleiben unverändert geroutet.
- **SSE-Live-Visualizer.** `/v1/_internal/live-visualizer` — ungeschützter
  SSE-Endpoint, der echte Request-Lifecycle-Events streamt (`request.arrived`,
  `db.lock_waiting`, `db.lock_acquired`). Per-Client `asyncio.Queue` via
  Broadcast-Set in `app.state.ui_clients`. Frontend verbindet sich via
  `EventSource`, Canvas rendert echte Request-IDs; fällt nach 3s auf
  Sandbox-Simulation zurück.
- **CLI Dev-Modus.** `limen` ohne Subcommand startet Backend mit `info`-
  Logging und öffnet Chromium (`--dev`-Flag auch via `limen start --dev`).
  `_kill_port()` via `fuser -k` beendet alte Prozesse auf Ziel-Port.
- **SQLite Concurrency Simulator** (`simulator.html`). Standalone SPA mit
  2D-Canvas-Animation (API-Kreise, Worker, SQLITE-LOCK), Latenz-
  Streudiagramm, Timeout-Flash, Slidern für Anfragerate und Schreibdauer.
  Keine Abhängigkeiten, reines Vanilla JS/CSS/HTML.
- `test_build_parser_defaults_to_no_command` — CLI erlaubt jetzt leeren
  Subcommand (startet Dev-Modus).
- **Canvas-Pipeline erweitert.** API-Kreise laufen sichtbar bis zum
  gestrichelten Center-Gate, stauen dort FIFO, werden vom Worker aufgenommen
  und zu Provider-/Key-Zielen getragen. Abgeschlossene Requests verschwinden;
  jede Antwort wird in einem echten Latenz-Streudiagramm geplottet.

### Changed
- `durable_dispatch()` und `stream_completion()` akzeptieren optionalen
  `ui_event`-Callback für Live-Visualisierung.
- `chat_completions()` generiert `request_id` und feuert `request.arrived`
  vor Dispatch.
- **Control Center redesign.** German UI ("LIMEN Leitstand") replacing the
  minimal English placeholder. Dark theme with teal/gold palette, live
  `.health` polling every 2 s, CSS-animated request signal and queue
  tokens, offline state fallback, skip link, `prefers-reduced-motion`
  support, responsive mobile layout. No technical terms in visible text.
- `timeFormat` instead of misleading `formatMoment`; `in` operator
  instead of `Object.prototype.hasOwnProperty.call`; dead flex layout
  removed from `.masthead`.
- Added coverage for SSE fields and empty-key redaction boundaries.

## [0.0.12] — 2026-08-08

### Added
- **Phase 4: Audit, Heartbeat & Reporting.** Typed events with correlation_id
  (`task.started`, `task.completed`, `task.failed`, `worker.dead`), audit auth
  via `X-Proxy-Audit-Key` header, internal status endpoint, SSE event stream.
- Worker heartbeat loop writing to `worker_heartbeats` table every 5s.
- Worker reaper loop detecting stale workers and recovering their in-flight tasks.
- `GET /v1/_internal/status` — worker states, activity, queue depth (auth-protected).
- `GET /v1/_internal/events` — SSE stream of redacted audit events (auth-protected).
- `AuditConfig` with `audit_token_secret` from `[audit]` TOML section.
- `Database.heartbeat()`, `Database.reap_dead_workers()`, `Database.read_events()`.

### Changed
- `_durable_dispatch()` and `_stream_completion()` now emit `task.started`,
  `task.completed`, and `task.failed` events with correlation_id.
- `QueueWorker` now runs three concurrent loops: queue processing, heartbeat,
  and reaper.
- `/health` unchanged — public API stays audit-free.

## [0.0.11] — 2026-08-08

### Added
- **Phase 3: Durable Queue & Crash-Recovery.** Requests are persisted to SQLite
  before dispatch via atomic `emplace()` (insert + claim). On crash, expired
  ``in_flight`` leases are reset to ``pending`` on next startup and processed by
  the background worker.
- `Database.emplace()` — atomic insert-and-claim for the request path.
- `QueueWorker` background task with startup lease recovery and polling loop.
- Idempotency table (`idempotency_keys`) with `check_idempotent()` /
  `store_idempotent()` for content-addressed result caching.
- `/health` now reports live `queue_depth` from the database.

### Changed
- Non-streaming `POST /v1/chat/completions` now goes through
  `_durable_dispatch()`: emplace → dispatch → finish → store idempotent.
- Streaming path uses `emplace()` for durability before the SSE stream starts;
  finished or failed entries are marked accordingly.

### Fixed
- Removed aggressive content-based idempotency check that caused identical
  sequential requests to return cached results (broke rotation/failover tests).

## [0.0.10] — 2026-08-08

### Added

- Phase 5 Streaming: `stream=true` im Chat-Completions-Endpoint.
  `OpenAICompatibleAdapter.dispatch_stream()` ruft Provider via
  `post()` auf und liefert `(content_type, byte_iterator)` für
  `StreamingResponse`.
- `_stream_completion()` in `api/app.py`: claimt Key via Pool,
  returned SSE-StreamingResponse mit `text/event-stream`,
  `Cache-Control: no-cache`, `X-Accel-Buffering: no`. Pre-Stream-
  Errors als JSON (`HTTPException`). Kein Retry bei Streams.
- Redisignter SSE-Chunk-Forwarding-Pfad in
  `tests/integration/test_phase5_streaming_contract.py`:
  `_ChunkedStream`-Mock gibt Chunks via `content` zurück.

### Changed

- Streaming-Guard (`request_invalid`/"streaming is enabled only after
  Phase 5") aus `dispatch()` und `dispatch_single()` entfernt.
- `track_request`-Middleware (BaseHTTPMiddleware) entfernt — bricht
  `StreamingResponse`. `last_request_at` wird jetzt inline im
  `chat_completions`-Handler gesetzt.
- `test_chat_completion_streaming_is_rejected` →
  `test_chat_completion_streaming_is_accepted`: erwartet 200 statt 400.

### Tested

- 12 Phase-5-Contract-Asserts aus
  `tests/integration/test_phase5_streaming_contract.py` aktiviert
  (kein `@pytest.mark.skip` mehr). 128 passed, 0 skipped.
- Mypy strict + Ruff clean auf 21 Source-Files.

## [0.0.9] — 2026-08-08

### Added

- `src/limen/routing/key_pool.py`: KeyPool mit Round-Robin-Rotation,
  Cooldown (zeitbasiert, `clock`-injizierbar), `dead`-Status und
  `asyncio.Lock` für atomare Claims. Keys starten `active`;
  `rate_limited`/`key_quota_exhausted`/`unhandled_error` setzen
  `cooldown` mit failure-typ-abhängiger Dauer; `key_revoked` markiert
  `dead` (nur manuelle Konfig-Reload); `provider_unreachable` lässt
  den Key `active`.
- `src/limen/routing/pipeline.py`: FallbackPipeline (`run_pipeline`)
  iteriert Kandidaten-Deployments in Priority-Reihenfolge, claimt
  Keys aus dem KeyPool und setzt Fallback-Regeln durch:
  `request_invalid`/`request_too_large` stoppen sofort;
  `key_revoked` überspringt tote Keys; `provider_unreachable`
  springt zum nächsten Deployment; `rate_limited`/
  `key_quota_exhausted` cooldownen den Key und probieren nächsten.
  Bei totaler Erschöpfung wird der letzte Fehler mit Original-
  Statuscode weitergereicht (kein 503-Wrapper für Einzel-Key-Setups).
- Audit-Events `key.claimed`, `key.released`, `key.dead`,
  `key.cooldown_set` werden über `Database.write_event()` als
  redacted Fire-and-Forget-Events persistiert. Key-IDs erscheinen
  nur als SHA-256-Hash (`_redact_key()`).
- `Database.write_event()`: synchrone Methode zum Schreiben in die
  `events`-Tabelle; Fehler werden still geschluckt, blockieren nie den
  Request-Pfad.

### Changed

- `ProviderRegistry.resolve()` gibt jetzt eine **Liste** von
  Kandidaten zurück (nicht nur einen). Capability-Gate filtert nach
  `required_capabilities` (Default: `["chat"]`). Jedes
  `ProviderDeployment` hält jetzt einen `KeyPool`.
- `ProviderDeployment` ist nicht mehr `frozen` — der `pool` mutiert
  zur Laufzeit. Neue Properties: `aggregated_status` (aggregiert
  über alle Keys), `active_key_count`, `cooldown_key_count`,
  `dead_key_count`.
- `OpenAICompatibleAdapter.dispatch_single()`: neuer Single-Key-
  Aufruf für die Pipeline. `dispatch()` (Phase-1-kompatibel)
  delegiert jetzt an `dispatch_single()` und behält den internen
  Key-Loop für Phase-1-Kompatibilität.
- `Dispatcher` übergibt `run_pipeline` den Audit-Writer und nutzt
  jetzt den Pipeline-Pfad. `_resolve_max_attempts()` berechnet das
  Gesamtbudget aus Key-Pool-Größen.
- `/health` zeigt `deployments_active`, `deployments_cooldown`,
  `deployments_dead`. Status `degraded`, wenn kein Deployment aktiv.
- `/v1/models` enthält `status`, `limit_scope`, `priority` und
  `tags` pro Modelleintrag.

### Tested

- 25 Phase-2-Contract-Asserts aus
  `tests/integration/test_phase2_routing_contract.py` (alle
  aktiviert, kein `@pytest.mark.skip` mehr).
- Alle 91 Phase-0/1-Tests bleiben grün (116 total, 12 Phase-5
  skipped).
- Mypy strict + Ruff clean auf 21 Source-Files.

## [0.0.8] — 2026-08-08

### Added

- `tests/scripts/test_launch_limen.py`: 53 Pytest-Tests gegen
  `scripts/launch_limen.py`, gegliedert in zehn Klassen — Modul-Surface,
  Patcher-Parse, LIMEN-Option-Logik, Dry-Run-No-Side-Effect, Golden-Swap-
  Restore pro Agent, Config-Missing-Patcher, Restore-Missing-Target,
  Detection, Restore-Failure, CLI-Subprocesses. Pro Agent (goose, claude,
  interpreter, aider, continue, opencode) wird ein Golden-Sample mit
  realistischer Format-Topologie definiert; Round-Trip = swap + restore
  muss SHA-256-Byte-Identität liefern. Tests laden das Skript frisch pro
  Instanz via `importlib.util.spec_from_file_location` mit eigenem HOME.
- `docs/goose-gui-live-plan.md`: Goose-Desktop ↔ LIMEN ↔ Groq Runbook für
  Phase-1-Live-Chat mit echter Electron-GUI. Elf Abschnitte: Architektur-
  Bild, Vorbedingungen, Pre-Flight, Phase A (LIMEN mit echter Groq-Config),
  Phase B (Goose-Patch via Launcher), Phase C (Roundtrip), Phase D
  (Audit/Verify), Phase E (Cleanup/Restore), Failure-Map, Cross-Links,
  Verwandte Dateien. §3.0 verkettet das Skript `scripts/live_e2e_groq.sh`
  (`--check-only` für Pre-Flight, `--keep-config` für Full-Run) mit Phase A;
  §4.0 zeigt die drei Workarounds für die Phase-1-Auth-Lücke.

### Changed

- `README.md`: Goose-GUI-Abschnitt verweist jetzt explizit auf §3.0
  (Skript-Vorlauf) und §4.0 (Auth-Lücken-Workarounds).
- `ARCHITECTURE.md` §10.3: Skript-Vorlauf-Integration dokumentiert; die
  `--check-only`+`--keep-config`-Verkettung ist die empfohlene Sequenz,
  weil sie Pre-Flight und Cleanup deterministisch kombiniert.

### Fixed

- `scripts/launch_limen.py::restore_backup`: wenn das Backup einer
  ursprünglich nicht-existierenden Config leer ist, wurde die gepatchedete
  Datei mit `b""` überschrieben. Erkanntes Regressionsrisiko aus der neuen
  Test-Suite. Fix: bei leerer Backup-Datei und existierendem Target →
  `target.unlink()` statt `shutil.copy2(latest, target)`.
- `scripts/launch_limen.py::perform_swap` Backups für nicht-existente
  Targets: schreibt jetzt eine leere Backup-Datei (`b""`) statt
  `FileNotFoundError` zu werfen, damit `restore_backup()` einen
  nachvollziehbaren Anker hat.
- `scripts/launch_limen.py::_patch_goose`, `_patch_claude`,
  `_patch_interpreter`: `read_text()`-Call war unbedingt und crashed bei
  fehlender Datei. Fix: `if path.exists() else ""` plus `if text.strip()
  else {}`-Fallback in den JSON/YAML-Loadern — analog zu den
  Override-Patchern (aider, continue, opencode), die die Datei
  komplett neu rendern.

## [0.0.7] — 2026-08-08

### Added

- `docs/phase1-reset-gate.md`: Verbindliche Checkliste für das Phase-1-Reset-Gate
  mit zehn Assertions, Goose-Plugin-Tabelle (Base URL `http://127.0.0.1:8000/v1`,
  API-Key freier Platzhalter, Modell aus `[providers.<name>] models = [...]`)
  und Definition-of-Done inkl. drei Reset-Bedingungen.
- `scripts/phase1_smoke.sh`: idempotenter, headless-fähiger Smoke gegen
  `limen init`/`limen start` mit konfigurierbarem Port und umask‑077‑Tmp,
  Verifiziert `init`-Exit‑Code, Listener, `/health`, `/v1/models`,
  `unknown_model` (400), `request_invalid` (400), `provider_unreachable` (502),
  Header‑Hygiene, Oversize‑Body (413) und ungültigen `Content-Length` (400).
- `docs/phase5-streaming-contract.md`: Vertrag für Phase 5 mit separater
  Response‑Shape (`chat.completion.chunk`), No‑Retry‑nach‑erstem‑Chunk‑Regel,
  SSE‑Format, Header‑Policy, Client‑Disconnect‑Semantik, Backpressure‑Regeln,
  verbotenen Pfaden, Reset‑Gate‑Bedingungen und Test‑Mapping.
- `tests/integration/test_phase5_streaming_contract.py`: 13 Funktionen
  (zwölf Phase‑5‑Asserts + ein Anker‑Selbsttest) gegen `httpx.MockTransport`
  und `TestClient`, mit echtem SSE‑Parser (`parse_sse`). Alle zwölf Asserts
  per `@pytest.mark.skip(reason="Phase 5 implementation pending — contract locked")`
  belegt — keine `pass`, keine `TODO`-Marker, keine Stubs.
- `docs/phase2-routing-contract.md`: Vertrag für Phase 2 (ProviderRegistry,
  Key‑Pool, `limit_scope`‑Tabelle, Cooldown‑Mapping auf sieben Failure‑Typen,
  Fallback‑Pipeline, Status‑Surface, Audit‑Events, verbotene Pfade,
  Reset‑Gate‑Bedingungen, Forbidden‑Assertion‑Patterns, Test‑Mapping).
- `tests/integration/test_phase2_routing_contract.py`: Routing‑aware
  `httpx`‑Stub mit host‑suffix‑Dispatcher, `_StatefulScript` für
  deterministische 429/200‑Sequenzen und 27 Funktionen (25 Phase‑2‑Asserts +
  zwei statische Drift‑Guardians gegen `time.sleep` bzw. `pass;\n`). Echte
  TOML‑Renderings in Phase‑2‑Form, kein `tmp_path`-Override der internen
  Config‑Loader.
- `scripts/launch_limen.py`: Auto‑Detection‑Launcher für kompatible Agent‑CLIs
  (`goose`, `claude`, `interpreter`, `aider`, `continue`, `opencode`) mit
  Sub‑Commands `list`, `dry-run [agent]`, `swap [agent] [--start]`,
  `start [--config]` und `restore <agent>`. Backup‑Konvention aus
  `AGENTS.md` §2 (`<datei>.bak.<unix-ts>`, `.env`-Dateien als `.env.bak.<ts>`,
  Modus vom Original übernommen).
- `docs/live-groq-e2e.md`: Phase‑1‑Reset‑Gate‑Erweiterung mit Plan,
  Risiken, Pre‑Flight, Schritt‑Runbook und Failure‑Map für Live‑Groq.
- `scripts/live_e2e_groq.sh`: idempotente, isolierte Strecke mit
  `set -euo pipefail`, Cleanup‑Trap, `--check-only`-Modus und hartem
  `max_tokens ≤ 8`-Ceiling. Backup → LIMEN → `/v1/chat/completions` →
  Restore mit klaren Exit‑Codes 1..8 je Failure‑Typ.

### Changed

- `README.md`: Übersicht um `phase1-reset-gate`, `phase2-routing-contract`,
  `phase5-streaming-contract`, `live-groq-e2e` und den Launcher erweitert;
  Status‑Zeile auf „Phase‑2‑ und Phase‑5‑Verträge gerahmt (37 Asserts
  skipped)" aktualisiert; Live‑E2E‑Sektion mit Verweis auf
  `scripts/live_e2e_groq.sh` ergänzt.
- `ARCHITECTURE.md`: Phase‑1‑, Phase‑2‑ und Phase‑5‑Sektionen auf die neuen
  Vertragsdokumente verlinkt; Launcher‑Skript und Live‑E2E‑Runbook in §10
  verankert; Reset‑Kriterium für Phase 2 präzisiert („mind. 25 vertragliche
  Asserts").
- `pyproject.toml`: `[tool.mypy].mypy_path = "src"` ergänzt;
  `[tool.ruff.lint.per-file-ignores]` für `tests/integration/test_phase?_*.py`
  (`E501` lange Config‑Literale) und `scripts/` (`T201` Prints im Launcher)
  präzisiert; `warn_unused_ignores = false` für Test‑Override gesetzt.

### Fixed

- `scripts/launch_limen.py::_read_limen_options`: doppeltes `/v1`-Suffix bei
  schon‑vorhandenem `provider.base_url` verhindert; nur anhängen, wenn das
  Suffix fehlt. Ohne Fix patchte der Launcher z. B. `http://…:9000/v1` zu
  `http://…:9000/v1/v1` und schickte nachfolgende Calls auf den falschen
  Pfad.

## [0.0.6] — 2026-08-07

### Added

- Phase 1: OpenAI-kompatible Public-Schemas (`ChatCompletionRequest`/
  `Response`/`ErrorEnvelope`) als kanonischer Wire-Vertrag.
- OpenAI-kompatibler Referenz-Adapter mit Key-Rotation, Bearer-Auth und
  redacted Proxy-Headern (`X-Proxy-Request-Id`, `X-Proxy-Correlation-Id`).
- `HttpTransport` als lifespan-eigener `httpx.AsyncClient` mit separater
  Timeout-Konfiguration.
- `ProviderRegistry` mit Capability-/Priority-Sortierung.
- `Dispatcher` mit Single-Deployment-Auswahl und typisiertem Fehler-Mapping.
- Failure-Classifier (`limen.resilience.classifier`) mit sieben Failure-Typen
  (`rate_limited`, `provider_unreachable`, `key_quota_exhausted`,
  `key_revoked`, `request_invalid`, `request_too_large`, `unhandled_error`).
- Custom `HTTPException`-Renderer, der das LIMEN-`{"error":{...}}`-Envelope
  für alle 4xx/5xx-Antworten liefert.
- Integrationstests für Happy-Path, 503 ohne Provider, 400 bei unbekanntem
  Modell, 400 bei `stream=true`, 429 mit `Retry-After`, 401, 502,
  Header-Hygiene und Mock-Transport per `httpx`-Stub.
- Unit-Tests für den Failure-Classifier inkl. Body-Keyword-Erkennung
  (`quota`/`insufficient_quota`/`context length`).

### Changed

- `config.__init__` exportiert `ProviderConfig`, damit Registry/Adapter sie
  importieren können ohne TYPECHECKING-Hack.
- `limen.api.app` hält den Dispatcher nicht mehr via Modul-Global; er wird
  per Konstruktor an den lifespan-eigenen Transport gebunden.
- `mypy.strict` aktiv für `src/limen`; Tests sind über
  `[[tool.mypy.overrides]]` auf nicht-strict gesetzt.

## [0.0.5] — 2026-08-07

### Added

- Internes Refactoring: `ProviderFailure` als kanonischer Name, ehemals
  `ProviderFailureError`-Splitting zusammengeführt.

### Fixed

- Resilience-Classifier behandelte `408` als `request_invalid`, obwohl es als
  Transport-Retry zählt. Reihenfolge der Provider-Failure-Branches korrigiert.

## [0.0.4] — 2026-08-07

### Added

- `uv.lock` als reproduzierbare Dependency-Auflösung für die Dev-Toolchain.

### Changed

- pytest, Ruff und mypy über `uv sync --extra dev` installiert und ausgeführt.
- Ruff-Funde in Imports, Typing und Foundation-Markup behoben.
- Phase-0-Reset-Gate geschlossen; eine nicht blockierende Starlette-Testclient-
  DeprecationWarning bleibt als nächste Toolchain-Pflege dokumentiert.

## [0.0.3] — 2026-08-07

### Added

- Phase-0-Fundament: src-layout mit validiertem TOML-Config-Loader und harter
  Localhost-only-Prüfung.
- SQLite-WAL-Datenbank mit owner-only Permissions, Schema-Version 1,
  idempotenter Initialisierung und explizitem `BEGIN IMMEDIATE`-Rollback.
- `limen init` und `limen start` als echte CLI-Kommandos.
- FastAPI-Lifespan mit `/health`, `/v1/models` und isolierter lokaler Control-
  Center-Startseite.
- Unit- und Integrationstests für Config-Sicherheit, WAL, Schema und Rollback.

### Changed

- Phase-0-Status von Bootstrap-only auf implementierte Foundation aktualisiert.
- Health-Status, Request-Body-Limit, DB-Sidecar-Rechte und Phase-0-CLI-Scope
  gegen Grenzfälle gehärtet.
- Dev-Toolchain über `uv sync --extra dev` verankert; pytest, Ruff und mypy
  validieren die Foundation.

## [0.0.2] — 2026-08-07

### Added

- DEC-011: Goose (Block) als primärer externer Test-Client festgelegt.
  Open Interpreter als Backup. Cline für Streaming-Phase 5 vorgemerkt.
- `limen start` als einziger Launch-Command: startet Backend + Web-UI
  (Control Center) gemeinsam.
- Abschnitt 9.4 „Externe Test-Clients“ in ARCHITECTURE.md.

### Changed

- Phase 1 Reset-Kriterium: von „CLI-Tool“ auf „Goose Desktop“ als
  Test-Client umgestellt.
- Ziel-Beschreibung: von „CLI-AI-Tools“ auf „CLI- und Desktop-AI-Tools“
  erweitert.

## [0.0.1] — 2026-08-07

### Added

- Projekt-Bootstrap mit README, `pyproject.toml`, `ARCHITECTURE.md`,
  `config.toml.example` und `AGENTS.md`.
- `ARCHITECTURE.md` als einzige Plan-of-Record-Datei mit überprüften Phasen,
  Akzeptanzkriterien, Failure-Modell und Decisions-Log.
- Vollständige Control-Center-Zielarchitektur:
  - echter Live-Arbeitsstatus getrennt von Heartbeats;
  - korrelierter Dispatcher-Fluss vom Eingang bis zum Ergebnis;
  - Request-Inspector mit Auswahlgründen, Versuchen und Limit-Scope;
  - Slider für Parallelität, Queue, Rate, Retry, Timeout, Cooldown und Gewichtung;
  - `preview → validate → apply → audit` für Laufzeitänderungen;
  - Simulation mit demselben Request- und Routing-Vertrag ohne externe Aufrufe.

### Changed

- Die persistente LIMEN-Dokumentation nennt keine fremden Projekte, Pfade oder
  Herkunftsdateien mehr. Nur destillierte, eigenständig formulierte Konzepte
  bleiben erhalten.
- Die Architektur begrenzt die Ziel-Funktionalität nicht künstlich auf einen
  Statusscreen: redigierte Routing-Realität darf vollständig erklärt,
  visualisiert und innerhalb validierter Grenzen gesteuert werden.
- SQLite WAL, atomare Transaktionen, versionierte Migrationen, Idempotency,
  Schema-Prewarm und typisierte Events sind als eigenständige Muster beschrieben.
- Zentraler Dispatch, deklarative Registry, Capability-Gates, Rate-Limit-Scope,
  Retry-/Cooldown-Zustände und falsifizierbare Optimierungen sind verbindliche
  LIMEN-Konzepte.
- Queue/Lease/Recovery steht vor Heartbeat/Reaper; `rate_limited` bleibt ein
  eigener Failure-Type mit `Retry-After`, Backoff und Jitter.
- Streaming und äußere Kompatibilitätsverträge bleiben explizite Verträge mit
  lokalen Smoke-Tests; sie werden nicht stillschweigend nachgebaut.
- README, Architektur-Phasen, Glossar und Decisions-Log sind auf die neue
  anonymisierte Zielarchitektur synchronisiert.

### Not Done

- Kein LIMEN-Quellcode
- Keine Testsuite
- Keine Adapter-Module
- Keine systemd-Unit
- Keine Control-Center-Implementierung
- Keine echte Provider-Integration in automatischen Tests

### Decisions Made

- LIMEN bleibt ein eigenständiger Single-User-/Single-Host-Router.
- `ARCHITECTURE.md` ist die einzige Planquelle; alte Root-Entwürfe werden nicht
  als zusätzliche Wahrheit weitergeführt.
- Konzepte werden adaptiert und neu formuliert, nicht als Namen, Pfade oder
  Implementierungen übernommen.
- Die Zieloberfläche darf vollständig sein; Phasen definieren Reihenfolge und
  Testbarkeit, nicht künstliche Funktionsgrenzen.

[0.0.10]: #010--2026-08-08
[0.0.9]: #009--2026-08-08
[0.0.8]: #008--2026-08-08
[0.0.7]: #007--2026-08-08
[0.0.6]: #006--2026-08-07
[0.0.1]: #001--2026-08-07
