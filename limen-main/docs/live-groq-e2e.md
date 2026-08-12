# Live-Groq-E2E — Plan, Pre-Flight, Risiken

Dieses Dokument beschreibt, wie ein **echtes** Ende-zu-Ende mit einem
Groq-API-Key abläuft. Es beschreibt **kein** Skript, das hier ohne
ausdrückliche Bestätigung laufen darf: Provider-Keys kosten reale
Tokens, Audit-Verbindlichkeiten greifen, und Provider können den Key
bei einem 429-Sturm sperren.

Verwandt:

- [`scripts/live_e2e_groq.sh`](../scripts/live_e2e_groq.sh) — die
  konkrete Strecke (mit `--check-only` für den Dry-Run).
- [`docs/phase1-reset-gate.md`](./phase1-reset-gate.md) — Phase-1-Vertrag.
- [`scripts/phase1_smoke.sh`](../scripts/phase1_smoke.sh) — deterministische
  Negativpfad-Verifikation ohne Provider-Key.
- [`AGENTS.md`](../AGENTS.md) §2 / §6 — Geheimnisse niemals in Git.

## 1. Wann dieser Plan greift

Phase-1-Reset-Gate ist erfüllt:

- `scripts/phase1_smoke.sh` → **18/18 grün.**
- `pytest -q` → **38 passed, 37 skipped** (Phase 2 + Phase 5 sind Vertrag-Phase,
  dürfen übersprungen sein).
- Goose-Launcher-Dry-Run zeigt LIMEN als Provider ohne Real-Key.

Danach folgt dieser Plan, um den **rückwärtigen** Pfad
Provider-Key → LIMEN → Goose zu prüfen. Das ist **kein** Mock mehr.

## 2. Pre-Flight — was du brauchst

| Punkt | Quelle | Akzeptanz |
|---|---|---|
| Groq-API-Key | https://console.groq.com/keys | `gsk-…`, 50+ Zeichen, **niemals** in Git |
| Modell-Name | https://console.groq.com/docs/models | z. B. `llama-3.3-70b-versatile`, `llama-3.1-8b-instant` |
| Internet aus der Sandbox | `curl -sI https://api.groq.com/openai/v1` | `HTTP/2 200` |
| Port frei | `ss -ltn '( sport = :18100 )'` | keine Antwort = frei |
| LIMEN-Quellen | `~/Schreibtisch/limen` (oder Symlink) | `uv run python -m limen.cli --help` antwortet |

**Schlüssel niemals** in `argv`, Logs, Skript-Output, Chat-Verlauf oder
in `~/.bash_history` ohne `HISTCONTROL=ignorespace` + führendes
Leerzeichen. Der Plan und das Skript lesen den Key ausschließlich aus
`STDIN` (mit `read -rs`) oder aus der ENV `GROQ_API_KEY`, **nie** aus
positionalen Argumenten.

## 3. Risiken — vor dem ersten Run lesen

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|---|---|---|---|
| Key landet in Git | gering (Skript fordert 0600) | hoch (Revoke + Re-Issue) | `.gitignore` prüft `ag`, die geänderten Files vor `git add` mit `git diff` inspizieren |
| 429-Sturm durch Schleifen-Test | mittel | mittel (Key gesperrt für ≤ 60 s) | `--check-only` zuerst; max_calls ≤ 2; Cooldown beachten |
| Falsche Modell-ID | mittel | gering (400 von Groq) | `models.json` lokal von Groq abrufen oder Default `llama-3.3-70b-versatile` halten |
| LIMEN-Backup überschreibt Original | gering | hoch (User muss manuell zurückrollen) | `~/.config/limen/config.toml.bak.<ts>` wird vorher gesichert, On-Error-Restore im Skript |
| Goose-Swap vergisst Schlüssel | gering | hoch (User charts gegen alten Provider) | `scripts/launch_limen.py restore goose` ist der Notausgang |
| Streaming-Falle | gering | mittel (Limiter ignoriert SSE) | Skript sendet `stream: false` explizit im Payload |
| Goose bleibt nach Restart auf altem Provider | gering | gering (User Restart von Goose) | Doku: nach Swap Goose neu starten |

**Verboten:**

- `set -x` für Aufrufe mit Key im ENV → würde Key ins stderr loggen.
- `echo "$GROQ_API_KEY"` / `cat ~/.config/limen/config.toml` ins Log.
- Test-Loop mit `for i in {1..100}` ohne Cooldown.

## 4. Step-by-Step-Runbook

### 4.1 Skript-Dry-Run

```bash
scripts/live_e2e_groq.sh --check-only --port 18100 --prompt "ping"
```

Erwartete Ausgabe (Beispiel):

```
[preflight] key present (gsk-…)                    ✓
[preflight] limen repo located                    ✓
[preflight] provider reachable                     ✓
[preflight] model resolved                         ✓ llama-3.3-70b-versatile
[preflight] port 18100 free                        ✓
[plan]       backup ~/.config/limen/config.toml   ✓
[plan]       LIMEN write new config with groq      ✓
[plan]       LIMEN init                             ✓
[plan]       LIMEN start (background)               ✓
[plan]       /health 200 + 1 e2e call               ✓
[plan]       restore config.toml from backup       ✓
```

Kein Server wird in `--check-only`-Modus gestartet; keine Calls gehen
raus; keine Config wird geschrieben.

### 4.2 Voller Run

```bash
scripts/live_e2e_groq.sh --port 18100 --prompt "Reply with exactly: LIMEN live test passed."
```

Reihenfolge:

1. **Pre-Flight** (jede Prüfung explizit ausgegeben, Exit bei Misserfolg).
2. **Backup** `~/.config/limen/config.toml` → `config.toml.bak.<ts>`.
3. **Schreiben** neue `config.toml` mit `[providers.groq]`. Mode `0600`,
   nur GENAU ein Provider aktiviert (Groq), kein zweiter `enabled=true`.
4. **`limen init`** initialisiert die Datenbank.
5. **`limen start`** im Hintergrund; `/health` muss `200` mit
   `status:"ok"` liefern, **innerhalb** von 8 s.
6. **`/v1/models`** muss das konfigurierte Modell listen.
7. **Ein einzelner** `POST /v1/chat/completions` mit `max_tokens=4` und
   dem gewählten Prompt. Erwartung: HTTP 200, `usage.total_tokens`
   ≤ 12, `choices[0].message.content` non-empty.
8. **Teardown**: LIMEN stoppen, Original-Config aus Backup wiederherstellen
   (auf Wunsch `--keep-config` setzen).
9. **Reporting**: genau ein Satz in stdout, in stderr nur Diagnose.

### 4.3 Was du nach dem Run tust

- Ergebnis-Curl-Response in `docs/live-groq-e2e.<ts>.md` dokumentieren
  (keine Klartext-Keys, sondern nur `usage` und `id`).
- Token-Konto auf https://console.groq.com/ prüfen.
- Goose-Konfig zurück auf Original oder bewusst auf Groq-Swap belassen
  (`scripts/launch_limen.py restore goose`).

## 5. Failure-Map

| Was passiert | Wo | Reaktion |
|---|---|---|
| `gsk-` key missing | Pre-Flight | Exit 1, Hinweis auf `GROQ_API_KEY` |
| Provider unerreichbar (DNS / TLS) | Pre-Flight | Exit 1, Hinweis: später erneut versuchen |
| Modell nicht in Groq-Modelliste | Pre-Flight | Exit 1, andere Modellname wählen |
| Port belegt | Pre-Flight | Exit 1, `--port` setzen |
| Goose-Backup-Schreiben fehlgeschlagen | Pre-Flight | Exit 2, kein LIMEN-Start |
| `limen init` failt | Run | Exit 3, Backup-Config wird wiederhergestellt |
| `/health` nicht 200 nach 8 s | Run | Exit 4, Backup-Restore + Limen-Stop |
| Groq 401 / 403 | Run | Exit 5, Backup-Restore, Hinweis „Key ungültig" |
| Groq 429 | Run | Cooldown (`Retry-After`), Antwort melden, kein Re-Submit bis Cooldown |
| Groq 5xx / Timeout | Run | Backup-Restore, Exit 6, **kein** Retry-Loop |
| `chat.completions` Antwort nicht parsable | Run | Body nach `limen_response_<ts>.json` retten, `jq`/JSON-Decode-Hinweis |

Jeder Exit-Code ist eindeutig → in CI/Runbook später direkt auswertbar.

## 6. Audit-Trail

Was LIMEN für den Run in der SQLite (`~/.limen/state.db`) redigiert:

- `audit_events` mit `key.claimed`, `key.released` — `key_id` als SHA-256-Hash
  der ersten 16 Zeichen + `***`.
- **Kein** `Authorization`-Header im Klartext.
- **Kein** Modell-Body im Klartext, nur Token-Usage.

Nach dem Run:

```bash
sqlite3 ~/.limen/state.db "SELECT event_type, payload_json FROM audit_events ORDER BY id ASC" | head -20
```

Erwartung: keine `gsk-…`-Sequenz im Output. Falls doch: Post-Mortem
notwendig, Key rotieren.

## 7. Verwandte Artefakte

- [`scripts/live_e2e_groq.sh`](../scripts/live_e2e_groq.sh)
- [`scripts/phase1_smoke.sh`](../scripts/phase1_smoke.sh) — gleiche Strecke
  offline.
- [`docs/phase1-reset-gate.md`](./phase1-reset-gate.md)
- [`scripts/launch_limen.py`](../scripts/launch_limen.py) — Backup-Konvention
  und Restore-Pfad.
