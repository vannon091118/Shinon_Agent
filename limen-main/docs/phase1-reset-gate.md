# Phase 1 — Reset Gate

Phase 1 ist „fertig", wenn ein externer OpenAI-kompatibler Client (Goose
Block) den nicht-streamenden Pfad gegen LIMEN erfolgreich nutzen kann —
und wenn der lokale Setup das deterministisch nachweisen kann, bevor der
erste echte Provider-Key ins Spiel kommt.

Diese Seite ist die einzige Wahrheit für das Gate. Sie gehört zu
[`ARCHITECTURE.md`](../ARCHITECTURE.md) und wird mit jedem Phase-1-Commit
mitgeführt.

## 1. Vorbedingungen

- `uv` ist installiert und auf dem PATH.
- `git status` ist sauber (kein versehentlich committed Geheimnis).
- `config.toml.example` ist kopiert nach `~/.config/limen/config.toml`
  und mit `chmod 600 ~/.config/limen/config.toml` abgesichert.
- Phase 0 ist grün: `pytest -q`, `ruff check src tests`, `mypy src tests`
  und `uv lock --check` laufen ohne Fehler durch.

## 2. Offline-Verifikation — kein echter Provider-Key

Skript: [`scripts/phase1_smoke.sh`](../scripts/phase1_smoke.sh). Es
baut eine isolierte `umask 077`-Verzeichnisstruktur, schreibt eine eigene
Konfig mit nicht auflösbarem Provider (`https://provider.invalid/v1`),
bringt LIMEN auf `127.0.0.1:18180` hoch und prüft deterministisch:

| # | Aktion | Erwartung |
|---|---|---|
| 1 | `limen init` | Exit 0; `state.db` und WAL/SHM-Sidecars mit Mode `0600` |
| 2 | `limen start` | Uvicorn lauscht auf `127.0.0.1:18180` |
| 3 | `GET /health` | `200` mit `status: "ok"` und `db_writable: true` |
| 4 | `GET /v1/models` | `200`, `data` enthält genau ein konfiguriertes Modell |
| 5 | `POST /v1/chat/completions` mit Bogus-Modell | `400` mit `error.type: "unknown_model"` |
| 6 | `POST /v1/chat/completions` mit `stream: true` | `400` mit `error.type: "request_invalid"` |
| 7 | `POST /v1/chat/completions` mit gültigem Modell auf unauflösbarem Provider | `502` mit `error.type: "provider_unreachable"`, **kein** echt-Header `Authorization`/LIMEN-debug durchgeleckt |
| 8 | Oversize-Body > `max_body_size_kb` | `413` mit `Request body too large` |
| 9 | Ungültiger `Content-Length` | `400` mit `Invalid Content-Length` |
| 10 | Header-Hygiene | Keine `Set-Cookie`, kein `X-Provider-Stuff`, kein `X-LIMEN-Failure` im Erfolgsfall |

Aufruf:

```bash
./scripts/phase1_smoke.sh            # default Port 18180
LIMEN_PORT=19090 ./scripts/phase1_smoke.sh
```

Exit-Code:

- `0` — alle 10 Checks grün.
- `1` — Vorbedingung fehlgeschlagen (uv, lock, tests, tools).
- `2+` — einzelner Endpoint-Check hat die Erwartung verletzt. Das
  Skript gibt die genaue Assertion und das beobachtete Verhalten aus.

## 3. Goose Desktop — Plu-in

Goose (Block) spricht jeden OpenAI-kompatiblen Endpunkt an. LIMEN
authentifiziert in Phase 1 nicht, daher ist jeder API-Key-String
akzeptabel (LIMEN reicht ihn nur an den konfigurierten Provider weiter).

Custom-Provider-Eintrag in Goose:

| Feld | Wert |
|---|---|
| Provider-Name | `LIMEN Local` (frei wählbar) |
| Base URL | `http://127.0.0.1:<port>/v1` (Port aus `[server].port`, Default 8000) |
| API Key | `not-required` (Platzhalter, LIMEN prüft nicht) |
| Default Model | exakt der Modellname aus `[providers.X] models = [...]` |

Nachdem Goose konfiguriert ist, soll ein nicht-streamender Round-Trip
gelingen:

### 3.1 Live-Vertrag (manuell nach Desktop-Install)

```text
1. Server: limen start   # in Terminal 1
2. Goose: Chat öffnen, Modell auswählen, eine kurze Frage stellen.
3. Erwartung: Erste Antwort in <Provider-Latenz + Dispatch> ms, keine
   LIMEN/Set-Cookie-Header im Goose-Log, kein Stack-Trace.
```

### 3.2 Was Goose **nicht** testet (Scope bewusst)

- Streaming (`stream: true`) — Goose Phase 1 lässt es Standardpfad sein,
  LIMEN lehnt es mit `400 request_invalid` ab. Goose erwartet keine SSE.
- Authentifizierung — Phase 1 hat keine; LIMEN reicht Authorization
  unverändert an den Provider weiter. Provider-Credentials sind also nur
  in `config.toml` und in LIMENs Outbound-Header zu finden.

## 4. Reset-Kriterien (Definition-of-Done)

Phase 1 gilt als reset, **wenn alle drei Bedingungen** erfüllt sind:

- `scripts/phase1_smoke.sh` läuft mit Exit `0`.
- Goose öffnet eine Session auf dem LIMEN-Port (Default 8000), schickt eine
  nicht-streamende Anfrage und erhält eine Antwort mit
  `choices[0].message.content` ≠ leer, ohne 4xx/5xx.
- Der `pytest`-Lauf aus `tests/` ist grün (Stand: 35 passed) und es
  liegt kein offener `TODO`, kein Catch-0, kein Mock-Placeholder in
  `src/limen/`.

## 5. Nach dem Reset

- Provider-Key deaktivieren oder rotieren.
- LIMEN mit `Ctrl+C` sauber stoppen.
- Falls Goose Antworten gecached hat: Cache leeren, sonst sieht der
  nächste Test den vorigen Provider-Stand.
- Im Zweifel den `provider_unreachable`-Pfad mit dem Smoke nochmal
  wiederholen — er ist deterministisch.

## 6. Verwandte Dateien

- [`scripts/phase1_smoke.sh`](../scripts/phase1_smoke.sh) — Skript zu
  diesem Gate.
- [`ARCHITECTURE.md`](../ARCHITECTURE.md) §Phase 1 — Vertrag und Reset.
- [`CHANGELOG.md`](../CHANGELOG.md) `[0.0.6]` — Implementierungs-Stand.
