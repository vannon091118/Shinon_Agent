# Phase 2 — Multi-Provider-Routing, Key-Pool und Limit-Scope

Phase 2 erweitert den Dispatcher aus Phase 1 um Registry-Auflösung,
Key-Pool-Rotation, limit-scope-aware Fallback und Cooldown. Diese Seite
ist die einzige Wahrheit für den Vertrag. Bei Widerspruch zwischen Code
und Doc gewinnt das Doc.

Verwandt:

- [`ARCHITECTURE.md` §Phase 2](../ARCHITECTURE.md#phase-2--registry-multi-provider-und-resilienz)
- [`ARCHITECTURE.md` §4.2 Provider- und Limit-Scope](../ARCHITECTURE.md#42-provider--und-limit-scope)
- [`ARCHITECTURE.md` §5 Failure- und Retry-Modell](../ARCHITECTURE.md#5-failure--und-retry-modell)
- [`docs/phase1-reset-gate.md`](./phase1-reset-gate.md)
- [`tests/integration/test_phase2_routing_contract.py`](../tests/integration/test_phase2_routing_contract.py)
- [`tests/integration/test_phase1_dispatcher.py`](../tests/integration/test_phase1_dispatcher.py)

## 1. Geltungsbereich & Migration

Phase 2 erweitert:

- `ProviderRegistry` um Capability-/Pattern-Routing und Prioritäts-Sortierung.
- `Dispatcher` um Multi-Deployment-Auswahl, Key-Rotation und Cooldown.
- `Failure-Classifier` bleibt unverändert; jede Auswahl reagiert auf den
  schon typisierten `ProviderFailure.failure_type`.

Phase 2 ist **rückwärtskompatibel** zu Phase 1:

- `tests/integration/test_phase1_dispatcher.py` bleibt unverändert grün.
- `scripts/phase1_smoke.sh` lokal grün.
- `POST /v1/chat/completions` mit einem einzigen Provider/Key verhält sich
  identisch zu Phase 1, *außer* dass Retry-Budget und Cooldown jetzt
  zusätzlich greifen (was in Phase 1 noch leer war).

## 2. ProviderRegistry — Auflösung

### 2.1 Deklaration

Die Registry bleibt die einzige Wahrheit für Base-URL, Modell, Capabilities,
Priority und Account-Zugehörigkeit eines Deployments. Jedes Deployment wird
aus einem TOML-Block `[providers.<name>]` gelesen und intern auf genau eine
`ProviderDeployment`-Instanz pro Modell abgebildet.

```yaml
[providers.groq]
enabled = true
base_url = "https://api.groq.com/openai/v1"
priority = 1                 # kleiner = früher probieren
limit_scope = "unknown"      # siehe §5
account_id = "groq-account-main"
keys = ["gsk-...", "gsk-..."]
models = ["llama-3.3-70b-versatile"]
capabilities = ["chat", "json"]
soft_rpm = 28                # weiche Selbstbeschränkung, kein Vertrag mit Provider
soft_itpm = 5500
soft_otpm = 5500
```

### 2.2 Sortierung

`ProviderRegistry.resolve(model)` liefert eine **geordnete Liste** von
Kandidaten-Deployments, sortiert nach:

1. `priority` (aufsteigend). Default `100`.
2. Modellname (deterministisch, lexikographisch), um Test-Stabilität zu
   garantieren.

Innerhalb des gewählten Deployments rotiert der Key-Pool (§3). Multi-Modell-
Provider werden nicht automatisch zu mehreren Deployments aufgeblasen — pro
Modellname entsteht ein eigenes `ProviderDeployment`-Dataclass-Wert mit
einem eigenen Key-Pool, sofern die Registry das in einem späteren Schritt
explizit macht. Phase 2 ignoriert das und nutzt einen Pool pro Provider
(wie bisher).

### 2.3 Capability-Gate

Bevor ein Deployment in die Kandidatenliste aufgenommen wird, prüft die
Registry:

- `enabled = true`
- `capabilities ⊇ required_capabilities` (Default: `["chat"]`)
- Modellname aus `models` ist non-empty

`/v1/models` antwortet weiterhin mit nur den `enabled`-Deployments.

## 3. Key-Pool-Modell

### 3.1 Datenstruktur

Pro Deployment existiert genau ein `KeyPool`-Objekt:

```text
KeyPool
├── keys: tuple[Key, ...]          # Reihenfolge aus TOML
│   └── Key
│       ├── id: text               # der TOML-String, redacted im Log
│       ├── scope: str             # matched limit_scope
│       ├── status: active|cooldown|dead
│       ├── cooldown_until: iso8601|null
│       ├── last_used_at: iso8601|null
│       └── consecutive_failures: int
└── cursor: int                    # Round-Robin-Index
```

### 3.2 Rotation

- Round-Robin auf `cursor`, **deterministisch** und parallel-sicher durch
  einen `asyncio.Lock` pro Pool.
- Nach erfolgreich abgeschlossenem Provider-Call wird der Cursor
  inkrementiert (modulo Anzahl Keys).
- Bei Cooldown wird der Cursor nicht weiterbewegt; der nächste Aufruf liest
  einfach den nächsten „lebenden" Key.
- `dead`-Keys werden übersprungen, niemals probiert. Eine Rotation zählt
  nur Keys mit `status=active`.

### 3.3 Atomarer Claim

Wenn zwei Coroutinen gleichzeitig auf demselben Pool rotieren, darf
niemals derselbe Key zweimal angefragt werden. Der `Key.claim()`-Pfad:

1. setzt `last_used_at = jetzt`;
2. inkrementiert `consecutive_failures` nicht;
3. gibt den Key-Wert an den Adapter.
4. Failure-Rückgabe (via `key.release(failure)`) entscheidet, ob der
   Key auf `cooldown` oder `dead` wechselt — §6.

`claim` und `release` sind in SQLite als Transaktion geloggt (Audit-Reihe
`key.claimed`, `key.released`), ohne `Authorization`-Header im Klartext.

## 4. Limit-Scope-Semantik

`limit_scope` definiert, *auf welcher Ebene* die rpm/itpm/otpm-Ceiling
zählt. Damit entscheidet das Feld, ob zwei Keys tatsächlich zwei
unabhängige Kapazitätseinheiten sind oder denselben Account teilen.

| `limit_scope` | Effekt auf Key-Multiplikation |
|---|---|
| `key` | jeder Key ist eine volle Kapazitätseinheit (`keys × base_caps`) |
| `account` | Keys desselben `account_id` sind *eine* Einheit (kein Multiplikator) |
| `provider` | alle Keys pro Provider teilen sich die Einheit |
| `model` | alle Keys aller Provider pro Modell teilen sich die Einheit |
| `unknown` | konservativ: kein Multiplikator, eine geteilte Einheit |

### 4.1 Kapazitätsbeobachtung (`observed_*`)

LIMEN beobachtet Antwort-Header (`x-ratelimit-remaining-*`,
`retry-after`) und reichert die soft_caps zu `observed_*`-Werten an.
Diese werden nur zur Anzeige und Warnung benutzt; die Limits bleiben
Provider-definiert.

### 4.2 Warnschwellen

Wenn `observed_rpm > soft_rpm × 0.8` für ein Deployment, wird das
Deployment **nicht** automatisch in `cooldown` versetzt. Stattdessen
erscheint ein `deployment.warning`-Audit-Event mit `kind=near_limit`,
siehe §10.

## 5. Cooldown & Failure-Mapping

`ProviderFailure.failure_type` aus
[`src/limen/resilience/classifier.py`](../src/limen/resilience/classifier.py)
entscheidet die Reaktion:

| Failure-Type | key.status nach Aufruf | cooldown-Dauer | Deployment-Fallback? |
|---|---|---|---|
| `rate_limited` | `cooldown` für max(`Retry-After`, `backoff_seconds[0]`) | Provider-Header hat Vorrang | ja, wenn `limit_scope ∈ {account, provider, model, unknown}` |
| `provider_unreachable` | bleibt `active` | nicht-blockierend | ja, ab Versuch 2 |
| `key_quota_exhausted` | `cooldown` für Account-Quota-Window (Default 1h) | Account-ID bezogen | ja, wenn `limit_scope = account` |
| `key_revoked` | `dead` (manuell, bis Konfig-Update) | unbegrenzt | ja (Key wird übersprungen) |
| `request_invalid` | unverändert | n/a | nein |
| `request_too_large` | unverändert | n/a | nein |
| `unhandled_error` | `cooldown` für `backoff_seconds[0]` | jitter-only | ja |

### 5.1 Cooldown-Reihenfolge

`cooldown_until` ist **monoton wachsend**: ein zweiter Fehler desselben
Typs innerhalb eines aktiven Cooldowns verlängert nicht, ein anderer
Failure-Typ kann parallel einen unabhängigen Cooldown aufsetzen (z. B.
gleichzeitig `cooldown` und `dead`).

After the cooldown elapses, `key.status = active` automatically.
`dead` wird durch einen Konfigurations-Reload (`limen init`/`start`)
zurückgesetzt, nicht durch Zeit.

## 6. Fallback-Regeln

`Dispatcher.dispatch(request)` läuft eine **Pipeline** ab:

1. `Registry.resolve(model)` → Candidate-Liste.
2. Cold-Start: erster Kandidat nach `priority`.
3. Pro Versuch: nimm aktives Key-Pool-Mitglied; rufe Adapter.
4. Bei `request_invalid`/`request_too_large`/`key_revoked+dead_keys`:
   ad-hoc Fail oder nächster Kandidat (siehe §5).
5. Bei `rate_limited`/`provider_unreachable`/`key_quota_exhausted`:
   nimm nächsten Kandidaten gemäß account-/provider-scope-aware Sortierung.
6. Maximale Versuche = `len(candidates) × keys_count`. Wenn alle
   scheitern: 503 `no_available_deployment` (Phase 1) bzw. 502 mit
   `failure_type=provider_unreachable` (Phase 2) und Audit-Event.
7. Bei `unhandled_error` maximal `retry.max_attempts` (TOML) total
   über die gesamte Pipeline; danach 500.

### 6.1 429 ohne Retry-After

`Retry-After` fehlt → Default-Backoff `backoff_seconds[0]` (=1) mit `+jitter`.

### 6.2 429 mit Retry-After > wait_seconds

Provider zwingt Wartezeit länger als `retry.max_wait_seconds`. LIMEN
bricht die Pipeline ab und liefert 503 mit `failure=rate_limited`,
`hint=retry_after_exceeds_max_wait`.

## 7. Status-Surface

### 7.1 `GET /v1/models`

Liefert eine `data`-Liste pro Deployment:

```json
{
  "id": "llama-3.3-70b-versatile",
  "object": "model",
  "owned_by": "groq",
  "status": "active",
  "limit_scope": "unknown",
  "priority": 1,
  "tags": ["chat", "json"]
}
```

`status ∈ {active, cooldown, dead}` ist die *Deployment*-Aggregation
über alle Keys (Aggregation: `active` wenn min. 1 Key aktiv; sonst
`cooldown`/`dead` analog).

### 7.2 `GET /health`

Bleibt kompatibel zu Phase 1, erweitert:

```json
{
  "status": "ok|degraded|down",
  "deployments_active": int,
  "deployments_cooldown": int,
  "deployments_dead": int,
  ...
}
```

`degraded` jetzt zusätzlich, wenn `cooldown`/`dead > 0 && active > 0`;
`down` nur bei `db_writable=false`.

## 8. Audit-Events (Phase-2-Scope)

Phase 2 emittiert zusätzlich folgende Audit-Events mit redacted Feldern:

| Event | Felder (rot markiert: verboten im Klartext) |
|---|---|
| `key.claimed` | `deployment`, `key_id`, `account_id`, `correlation_id` |
| `key.released` | `deployment`, `key_id`, `failure_type`, `latency_ms` |
| `key.cooldown_set` | `deployment`, `key_id`, `until`, `reason` |
| `key.dead` | `deployment`, `key_id`, `reason` |
| `deployment.warning` | `deployment`, `kind=near_limit|under_pressure`, `metric` |
| `deployment.fallback` | `from_deployment`, `to_deployment`, `reason` |

`Authorization`-Header ist in keinem Event enthalten. Key-IDs werden
als SHA-256-Hash der ersten 16 Zeichen + `***`-Suffix geloggt.

## 9. Verbotene Pfade

- Synthetische Quota-Inventur, die `key.count × soft_rpm` als
  Gesamtkapazität ausgibt ohne auf `limit_scope` zu achten.
- Pauschale 24h-`cooldown`-Defaults — jeder Cooldown ist Failure-Type-
  abhängig.
- Refresh der Key-Liste ohne `limen init`/`start`-Reload.
- Direkter Provider-spezifischer Code im API- oder Dispatcher-Layer
  (`api/`, `routing/dispatcher.py`). Provider-Spezifika leben nur in
  `adapters/<provider>.py`.
- Modellnamen-Heuristiken für Pre-Cold-Start-Order (`free`, `flash`,
  `mini`, `nano` werden ignoriert).

## 10. Reset-Gate

Phase 2 ist reset, **wenn alle** Bedingungen erfüllt sind:

1. Mindestens die in §12 Test-Mapping genannten Tests grün.
2. `tests/integration/test_phase1_dispatcher.py` (35 old + 1 anchor =
   36) und `scripts/phase1_smoke.sh` (18/18) bleiben unverändert grün.
3. Ein 24h-Loop mit `>= 1000` deterministischen Mock-Requests über
   `tests/integration/test_phase2_routing_contract.py::stress_*` zeigt
   keine 429-Death-Loop (`<= 1 %` 5xx).
4. Kein Audit-Event enthält einen Klartext-Key oder
   `Authorization`-Header.
5. Kein neuer `time.sleep` und keine synchronen DB-Calls im
   Async-Request-Loop.

## 11. Forbidden Assertion Patterns (für Tests)

Das Phase-2-Test-Gerüst darf nicht:

- ohne Transport-Mock direkt gegen den Internet-Provider testen
- `time.sleep` zur „Wartezeit-Simulation" verwenden (Cooldown-Uhren
  müssen injizierbar sein, sonst sind die Tests nicht deterministisch).
- `os.environ` global mutieren.
- reale API-Keys in Test-Fixtures schreiben.

## 12. Test-Mapping

Jeder Vertragspunkt hat genau einen oder mehrere Tests in
[`tests/integration/test_phase2_routing_contract.py`](../tests/integration/test_phase2_routing_contract.py).
Alle Tests sind bis Phase-2-Implementierung per `@pytest.mark.skip`
markiert und werden ohne weitere Test-Änderungen aktiv, sobald die
Implementation steht.

| Vertragspunkt | Testname | Was wird geprüft |
|---|---|---|
| §2 Sortierung | `test_registry_resolves_lowest_priority_first` | Prio 1 vor Prio 2 vor Prio 100 |
| §2 Sortierung | `test_registry_resolves_lexicographically_within_same_priority` | deterministische Tie-Breaker |
| §2 Capability-Gate | `test_registry_excludes_deployment_missing_required_capability` | `capabilities` ⊇ Required |
| §2 Capability-Gate | `test_registry_excludes_disabled_deployment` | `enabled=false` raus |
| §3 Rotation | `test_key_pool_rotates_round_robin_across_successful_calls` | Cursor fortschritt |
| §3 Rotation | `test_key_pool_skips_cooldown_and_dead_keys` | keine `cooldown`/`dead`-Keys |
| §3 Atomic Claim | `test_concurrent_dispatch_never_claims_same_key_twice` | asyncio.Lock + 50 parallele Calls |
| §4 Limit-Scope | `test_unknown_scope_does_not_multiply_capacity` | Capacity wird geteilt |
| §4 Limit-Scope | `test_key_scope_does_multiply_capacity` | Capacity wird multipliziert |
| §4 Limit-Scope | `test_account_scope_shares_keys_across_providers_with_same_account_id` | gleicher Account = geteilt |
| §4 Soft-Caps | `test_observed_rpm_near_soft_limit_emits_warning_event_not_cooldown` | Event, kein Cooldown |
| §5 Cooldown | `test_rate_limited_sets_cooldown_with_retry_after_minimum` | Cooldown ≥ Retry-After |
| §5 Cooldown | `test_provider_unreachable_does_not_block_key` | Key bleibt active |
| §5 Cooldown | `test_key_quota_exhausted_blocks_only_keys_in_same_account_scope` | Scope-aware |
| §5 Cooldown | `test_key_revoked_marks_key_dead_never_recovered_by_time` | manuell raus |
| §6 Fallback | `test_dispatcher_falls_back_to_next_deployment_on_rate_limited` | 2 Deployments, 1 429, 2. versucht |
| §6 Fallback | `test_dispatcher_does_not_fallback_on_request_invalid` | Phase 1 400 bleibt |
| §6 Fallback | `test_dispatcher_respects_max_attempts_budget_across_deployments` | Gesamtbudget gilt |
| §6 429 ohne Retry-After | `test_dispatcher_uses_backoff_floor_when_retry_after_missing` | Default-Backoff |
| §7 `/v1/models` | `test_models_endpoint_reports_deployment_status_aggregate` | active/cooldown/dead |
| §7 `/health` | `test_health_reports_degraded_when_some_deployments_cooldown` | degraded-Pfad |
| §8 Audit-Redaction | `test_audit_event_never_logs_authorization_or_full_key` | Key-Hash + kein Header |
| §8 Audit-Reihenfolge | `test_audit_events_log_claim_before_release_and_failure_type` | Order |
| §10 Reset | `test_stress_one_thousand_requests_no_429_death_loop` | Loop-Schutz |
| §10 Reset | `test_stress_failover_under_simulated_provider_outage` | Recovery ohne State-Drift |
| §11 Forbidden | `test_no_synchronous_sleep_in_request_loop` | statisch: kein `time.sleep` in `src/limen/routing/` |

Diese Tests sind stub-frei. Siehe Doc-§11 für die Forbidden Patterns,
die das Gerüst einhält.
