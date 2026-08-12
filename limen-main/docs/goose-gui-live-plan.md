# Goose-Desktop ↔ LIMEN ↔ Groq (Live-Key) — Schritt-für-Schritt-Plan

> **Ziel:** Die Goose-Electron-App als echte GUI starten, mit einem von LIMEN
> vermittelten Live‑Endpoint reden und die Round-Trips auditiert aufzeichnen.
> Kein Mock, kein lokaler Python-Stub.

---

## 1. Architektur-Bild

```
┌──────────────────┐    OpenAI-kompatibles     ┌──────────────────┐    HTTPS    ┌──────────────┐
│  Goose Desktop   │ ──── /v1/chat/completions ──▶│  LIMEN (127.0.0.1)│ ──────────▶ │   Groq API   │
│  (Electron GUI)  │ ◀────  Antwort + Audit  ─────│ 127.0.0.1:8000  │ ◀────────── │ api.groq.com  │
└──────────────────┘                            └──────────────────┘             └──────────────┘
                                                         │
                                                         ▼
                                                 ~/.limen/state.db   (Audit-Events,
                                                                          Redacted Headers)
```

Drei klar getrennte Vertrauens­zonen. Goose **sieht** LIMEN als „Provider X mit
Base URL `http://127.0.0.1:8000/v1`". Der echte Groq‑Key liegt **nur** in LIMEN
(`env:GROQ_API_KEY` oder TOML `keys = [...]`), nicht in Goose.

---

## 2. Vorbedingungen — was schon stehen muss

| Komponente | Status (heute) | Aktion wenn fehlt |
|---|---|---|
| Goose 1.45.0 installiert | ✅ `dpkg -l goose` → `ii 1.45.0 amd64` | `dpkg -i ~/Downloads/goose_1.45.0_amd64.deb` |
| LIMEN-Code auf `0.0.6`-Stand | ✅ `git log -1` zeigt `1b25988` | `git pull` |
| Python-Toolchain + uv | ✅ `uv --version` | `pip install uv` |
| Echte Groq-API-Key | ❌ du brauchst ihn live | `https://console.groq.com/keys` (kostenlos mit Account) |
| Funktionierender Netzwerk-Egress zu `api.groq.com` | ? | `curl -sS -o /dev/null -w '%{http_code}\\n' https://api.groq.com/openai/v1/models -H 'Authorization: Bearer gsk-test'` |

**Was du NICHT brauchst:** die Phase-1-Smoke-Skript-Pfad-Kette — sie sind
lt. Reset-Gate der Vorabtest, kein Live-Traffic nötig.

---

## 3. Pre-Flight — Vorbereitung in trockener Umgebung

### 3.0 Skript-getriebener Vorlauf (optional, empfohlen)

Falls du **vorher** `scripts/live_e2e_groq.sh` laufen lässt, ist Phase A
bereits vorbereitet. Zwei Pfade:

| Flag | Was passiert | Was danach zu tun ist |
|---|---|---|
| `--check-only` | Offline-Verifikation: Key-Shape, Pre-Flight, **kein** Side-Effect | unverändert mit Phase A fortfahren |
| `--keep-config` | Full-Run lässt die ursprüngliche `~/.config/limen/config.toml` **persistent** modifiziert zurück (kein Restore am Ende); LIMEN ist gestoppt | weiter mit Phase A und dem TOML-Key-Patch (Workaround A), ohne die Konfig neu zu schreiben |

**Reihenfolge, wenn beide Schritte verbunden werden sollen:**

1. `scripts/live_e2e_groq.sh --check-only --port 18100` — bestätigt Key + Egress ohne Risiko.
2. `scripts/live_e2e_groq.sh --keep-config --port 18100 --model llama-3.3-70b-versatile` — schreibt eine TOML mit aktivem Groq-Provider nach `~/.config/limen/config.toml` und **rührt sie nicht mehr an**. Die Datei enthält aktuell noch `keys = []` (Workaround dafür in §4.0).
3. Direkt mit Phase A fortfahren, **ohne** den TOML-Block aus §3.1 neu zu schreiben — falls §3.1 etwas überschreiben würde, geht der `--keep-config`-Effekt verloren.

**Audit-Hinweis:** der `--keep-config`-Run erzeugt mehrere Audit-Events in
`state.db` mit `provider.request.sent`. Beim Goose-Round-Trip in Phase C
kommen weitere Events dazu — die Phase-D-Auswertung kann zwischen
„Skript-Token" und „Goose-Token" unterscheiden, weil die Round-Trip-Quelle im
Audit-Stream getrennt loggt.

### 3.1 LIMEN-Konfig frisch schreiben (kein Editieren auf bestehender Datei)

```bash
# Stand ablegen, damit du notfalls zurückrollen kannst
cp ~/.config/limen/config.toml ~/.config/limen/config.toml.bak.$(date +%s) 2>/dev/null || true

# Neue Config schreiben — kein Echo mit Key!
umask 077
cat > ~/.config/limen/config.toml <<'EOF'
[server]
host = "127.0.0.1"
port = 8000
worker_count = 1
log_level = "info"
max_body_size_kb = 256

[database]
path = "~/.limen/state.db"
wal_mode = true
busy_timeout_ms = 30000
sync_mode = "normal"

[timeouts]
connect_seconds = 5
write_seconds = 30
read_seconds = 120
pool_seconds = 5
max_request_wait_seconds = 30

[retry]
max_attempts = 3
max_wait_seconds = 60
backoff_seconds = [1, 2, 5]
jitter_ratio = 0.2
respect_retry_after = true
retry_before_first_stream_chunk_only = true

[security]
reject_non_localhost = true
config_mode = "owner-only"
database_mode = "owner-only"
redact_provider_bodies = true
redact_authorization_headers = true

[providers.groq]
enabled = true
base_url = "https://api.groq.com/openai/v1"
priority = 1
limit_scope = "unknown"
account_id = "groq-account-main"
keys = []                                 # leer — Key kommt aus env
models = ["llama-3.3-70b-versatile"]      # exakt diese Model-ID
capabilities = ["chat", "json"]
EOF
chmod 600 ~/.config/limen/config.toml     # owner-only wie [security].config_mode verlangt
```

**Wichtiger Sicherheits­hinweis:** `gsk-...` niemals in die TOML schreiben.
LIMEN resolvet `keys = []` derzeit zu leere Liste; Groq-Auth muss also per
Adapter-Patch nachgereicht werden (siehe TODO in §3.2). **Alternative für
Phase 2+:** `keys = ["env:GROQ_API_KEY"]` direkt in der TOML — aktuell noch
nicht implementiert.

### 3.2 Aktueller Stand: Auth-Bypass in Phase 1

LIMEN Phase 1 prüft **keinen** Auth-Header. Der Adapter sendet `Bearer <key>`
an Groq — wenn `keys = []` konfiguriert ist, schickt er `Bearer ` ohne Token.
**Folge:** Groq antwortet `401 invalid_api_key`.

**Workaround für den Live-Test:**

```bash
# Workaround A: Key direkt in der TOML — funktioniert, aber persistiert.
#   Riskant: Backup-Kette beachten, chmod 600 erledigt den Rest.
#   Empfohlen nur für kurze Live-Sessions.

# Workaround B: Key per --patch in der Datei setzen, nach Test wieder leeren.
#   Nicht von uns unterstützt — Handarbeit erforderlich.
```

**Sauberer Workaround (für jetzt):** TOML mit Key schreiben, nach Test
TOML-Backup wiederherstellen.

### 3.3 Erste Verifikation ohne Goose

```bash
# Limen starten — Shell-Variable nicht in History:
read -rs GROQ_API_KEY                  # Eingabe ohne Echo, oder
export GROQ_API_KEY="gsk-..."          # nur in dieser Shell-Session, kein .bashrc

# (Workaround A) Key in TOML injizieren — sed vorübergehend:
sed -i 's|keys = \[\]|keys = ["'"$GROQ_API_KEY"'"]|' ~/.config/limen/config.toml

# LIMEN hochfahren:
limen start                            # foreground; alternativ `&` mit nohup
# Listener checken (anderes Terminal):
ss -ltn 'sport = :8000'                # muss 127.0.0.1:8000 zeigen

# Smoke gegen LIMEN allein (kein Groq-Roundtrip, aber Phase-1-Pfade):
LIMEN_PORT=8000 ./scripts/phase1_smoke.sh
# → erwartet 18 passed, 0 failed
```

**Erwartetes Ergebnis:** `/health` 200, `/v1/models` listet
`llama-3.3-70b-versatile`. Wenn `phase1_smoke.sh` fehlschlägt, ist LIMEN kaputt
— stopp, nicht weiter zu Goose.

---

## 4. Phase A — LIMEN mit echter Provider-Config betreiben

### 4.0 Auth-Lücke — der zentrale Haken für Goose-Chat

Phase 1 hat eine **harte** Einschränkung: `keys = []` führt zu einem
`Authorization: Bearer ` ohne Token nach Groq → 401. Für die Skript-Variante
in Phase C braucht der Goose-Chat denselben Key-Pfad. Es gibt drei
gleichwertige Workarounds; wähle einen:

- **Workaround A (TOML-Patch):** vor `limen start` einmalig
  `sed -i 's|keys = \[\]|keys = ["gsk-..."]|' ~/.config/limen/config.toml`;
  danach `sed -i 's|keys = \["gsk-[^"]*"\]|keys = []|' ...` zum Aufräumen.
  Auditierbar, **aber** der Klartext-Key steht kurzfristig in der TOML.
- **Workaround C (Skript-Override):** `scripts/live_e2e_groq.sh` mit
  `--keep-config` modifiziert die TOML nicht nur in `keys`, sondern startet
  auch LIMEN mit `LIMEN_CONFIG_AUTH_BYPASS=1` (nicht implementiert — als
  TODO für Phase 2 in `docs/phase2-routing-contract.md`). Bis dahin:
  Workaround A nehmen.
- **Workaround langfristig:** Phase 2 implementiert `keys = ["env:GROQ_API_KEY"]`
  im Adapter — Key bleibt ausschließlich in der Shell-Variable und wird bei
  Bedarf in den `Authorization`-Header gerendert. Der Vertrag steht im
  Phase-2-Doc.

**Audit-Implikation:** Welcher Workaround auch immer — der Audit-Stream
darf den Key **nie** im Klartext sehen. Das ist `redact_authorization_headers`-
Default in `[security]`. Falls Phase D etwas anderes zeigt: sofort stoppen,
Phase-D-Failure-Map zeigt Schritt-für-Schritt.

### 4.1 Start-Varianten

| Variante | Befehl | Was du bekommst |
|---|---|---|
| Empfohlen (sichtbar) | `cd ~/Schreibtisch/limen && uv run limen start` | Foreground, Ctrl+C stoppt |
| Hintergrund + Logfile | `nohup uv run limen start →/tmp/limen-live.log 2>&1 &` | Headless, Logs in `/tmp/limen-live.log` |
| Via Launcher | `python3 scripts/launch_limen.py start` | Erkennt vorhandene Config und startet |

### 4.2 Verifikation, dass LIMEN wirklich Groq sieht

```bash
# Modelliste — LIMEN fragt bei init einmalig groq nach allen Modellen?
# Phase 1 lädt sie statisch aus der TOML. Das hier testet nur, dass die
# Config gelesen wurde:
curl -sS http://127.0.0.1:8000/v1/models | jq .

# Health:
curl -sS http://127.0.0.1:8000/health | jq .

# Echter Roundtrip vor Goose (cURL + jq):
curl -sS http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer any-string' \
  -d '{"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"hi"}],"max_tokens":4}' \
  | jq '.choices[0].message.content, .usage'
# → erwartet nicht-leeren Inhalt + usage.total_tokens
```

### 4.3 Was wenn 401?

LIMEN leitet 401 als `provider_unreachable` zurück. Diagnose:

```bash
# Logs:
tail -f /tmp/limen-live.log             # foreground case
# oder:
journalctl --user -u limen             # nach systemd-User-Unit (Phase 3+)

# Provider direkt testen (zeigt, ob der Key bei Groq akzeptiert wird):
curl -sS https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY" | jq '.data[].id'
#   → muss ≥1 Modell zeigen. Wenn nicht: Key ungültig oder Account-Flag.
```

---

## 5. Phase B — Goose neu starten und Provider-Block einhängen

### 5.1 Goose beenden, falls offen

- **Electron-Window schließen** — nicht minimieren.
- **Tray-Icon** (falls im System-Tray) → Rechtsklick → „Quit".
- **CLI-Backstop** falls weder Window noch Tray: `pkill -f "Goose"`.

### 5.2 Backup-Kette prüfen

```bash
ls -lt ~/.config/goose/config.yaml.bak.* | head -5
# → zeigt drei aktuelle Backups aus den E2E-Tests. Keine Aktion nötig.
```

### 5.3 Dry-Run zuerst — kein Write bis du es sagst

```bash
python3 scripts/launch_limen.py dry-run goose
```

Erwartete Ausgabe:

```
[plan] Agent            : goose
[plan] Target           : /home/vannon/.config/goose/config.yaml
[plan] Backup →         : …/config.yaml.bak.<unix-ts>
[plan] Provider name    : groq                       (oder `primary` aus LIMEN-Config)
[plan] Model            : llama-3.3-70b-versatile
[plan] Base URL         : http://127.0.0.1:8000/v1
[plan] API key          : limen-local (placeholder)
status: "dry-run"
```

**YAML-Snippet, das der Patcher einfügen wird:**

```yaml
providers:
  limen_local:
    enabled: true
    model: llama-3.3-70b-versatile
    base_url: http://127.0.0.1:8000/v1
    api_key: not-required
    configured: true
```

### 5.4 Patch anwenden — explizit bestätigen

```bash
python3 scripts/launch_limen.py swap goose
# Default: y/N-Prompt. Eingabe: y
```

Verifikation nach Patch:

```bash
diff <(git -C ~/Schreibtisch/limen show 1b25988:scripts/launch_limen.py 2>/dev/null || true) /dev/null 2>&1 || true
# Inhalt relevant: Backup-Länge, Provider-Block neu:
tail -20 ~/.config/goose/config.yaml
# → muss `limen_local`-Block enthalten
ls -lt ~/.config/goose/config.yaml.bak.* | head -1
# → muss neuer Eintrag ganz oben stehen
```

### 5.5 Goose neu starten — Electron-Config wird neu geladen

```bash
goose &
# Electron öffnet das Hauptfenster; Framedauer ~3-6s beim ersten Start.
```

**Wichtig:** Goose **liest** `~/.config/goose/config.yaml` **einmal beim Start**.
Nach dem Goose-Start: `Settings → Providers` zeigt jetzt **sechs** Einträge:
nvidia, openrouter, minimax, ollama_cloud, cerebras, **limen_local**.

### 5.6 Falls Goose nicht startet

- **Error:** „GUI kann nicht geöffnet werden" → display-Env prüfen
  (`echo $DISPLAY`, muss auf aktiven X-Server/Wayland zeigen).
- **Error:** „prop not found `base_url`" → Goose-Schema hat sich geändert
  (1.45.0 versteht das Feld). Vor Patch `grep -A6 "limen_local" ~/.config/goose/config.yaml` zeigen lassen.
- **Error:** nichts — Goose startet, aber zeigt keine neuen Provider →
  LIMEN-Patch wurde nicht angewendet oder falsches YAML-Backup eingespielt.

---

## 6. Phase C — Roundtrip in Goose

### 6.1 Modell wechseln

- In Goose: oben links Modellname klicken → Drop-Down → `limen_local` →
  Modell-Untermenü → `llama-3.3-70b-versatile` auswählen.

### 6.2 Frage stellen

> Beispiel-Eingabe: `Was ist 7×8? Antworte in genau drei Wörtern.`

### 6.3 Erwartung

- **Latenz:** 1-3s für llama-3.3-70b bei Groq + ~50ms LIMEN-Overhead.
- **Inhalt:** Antwortsatz in deutscher Sprache (oder englisch, je nach
  Modellverhalten — llama-3.3-70b liefert in der Sprache der Frage).
- **Toolchain-Hinweis:** Falls Goose eine GPU-Warning bringt
  („GPU process launch failed"): egal, blockiert den Provider-Pfad nicht.

### 6.4 Zweiter Roundtrip als Stresstest

- Eine zweite Frage direkt hinterher, um zu sehen, dass das Audit-Doppelt
  ist und LIMEN kein State-Leak hat.
- 30 RPM ist Groqs Soft-Ceiling für free tier — **nicht** in einer
  Schleife testen, sonst 429.

---

## 7. Phase D — Audit & Verify

### 7.1 Audit-DB auslesen (kein Plaintext-Key)

```bash
# Audit-Pfad laut [database].path:
sqlite3 ~/.limen/state.db \
  "SELECT ts, event_type, key_hash, status FROM audit_events
   WHERE ts > datetime('now','-5 minutes')
   ORDER BY ts DESC LIMIT 10;"
```

Was du sehen willst:

- `provider.request.sent` mit `key_hash` ≠ NULL (Hash, nicht Klartext).
- `provider.response.received` mit `status=200`.
- Keine Zeile mit `authorization` im Body.

### 7.2 Redaction-Check

```bash
sqlite3 ~/.limen/state.db \
  "SELECT event_type, body FROM audit_events
   WHERE ts > datetime('now','-5 minutes') AND body LIKE '%gsk-%';"
# Erwartetes Ergebnis: 0 Zeilen (kein Klartext-Key im Audit-Body).
```

Falls etwas gefunden wird: **sofort** LIMEN stoppen, Commit-Note schreiben,
Patch-Stand notieren — der Audit-Stream ist eine Sicherheitsgrenze.

### 7.3 LIMEN-Logs

```bash
tail -50 /tmp/limen-live.log | grep -E '(provider\.|key\.|chat\.|audit)'
# oder im Foreground die `[INFO]`/`[WARN]`-Zeilen beobachten.
```

---

## 8. Phase E — Cleanup & Restore

### 8.1 Reihenfolge (Reihenfolge ist wichtig)

1. **Goose beenden** (Electron-Window schließen).
2. **Goose-Config wiederherstellen** — jüngster Backup:
   ```bash
   python3 scripts/launch_limen.py restore goose
   # → zeigt den konkreten Backup-Pfad, fragt y/N.
   # „y" → restore der ersten Zeile aus `ls -lt config.yaml.bak.* | head -1`.
   ```
3. **GROQ_API_KEY aus der TOML entfernen** — falls du Workaround A
   angewendet hast:
   ```bash
   sed -i 's|keys = \["gsk-[^"]*"\]|keys = []|' ~/.config/limen/config.toml
   diff ~/.config/limen/config.toml ~/.config/limen/config.toml.bak.<ts> | head -5
   # Sollte nach 'restore' gegen die Pre-Live-Config identisch sein.
   ```
4. **LIMEN stoppen** — Ctrl+C im Vordergrund-Terminal, oder
   `pkill -f "limen.cli start"`.
5. **Persistente `GROQ_API_KEY`-Shell-Variable löschen:**
   ```bash
   unset GROQ_API_KEY
   history -c && history -w
   ```
6. **Persistenz-Check** — kein Klartext-Key mehr im Klartext-Filesystem:
   ```bash
   grep -rI "gsk-$GROQ_API_KEY_HINT" ~/.config/limen/ 2>/dev/null || echo "(clean)"
   ```

### 8.2 Was bleibt nach dem Live-Test

- `~/.limen/state.db` wächst (~50 KB pro 10 Calls). Kein Aufräumen nötig,
  Phase 3 hat Vacuum-Job.
- Goose-Config ist auf den **vor-Live**-Stand restored (E2E-Tests haben
  drei Backups hinterlassen — wenn du vor diesem Run keine neuen Edits
  gemacht hast, ist es identisch mit dem letzten E2E-Pre-Stand).
- LIMEN-TOML zeigt `keys = []` (oder den ursprünglichen Stand, falls du
  Workaround B hattest).
- Logs in `/tmp/limen-live.log` — kannst du löschen oder für Audit behalten.

---

## 9. Failure-Map (was wann zu tun ist)

| Symptom | Ursache | Aktion |
|---|---|---|
| Goose zeigt `limen_local` nicht in Providers | Patcher hat YAML falsch eingefügt | `restore goose`, dann manuell Patch mit `cat >> .config/goose/config.yaml <<EOF … EOF` |
| Goose: `401 invalid_api_key` | Key-Bypass fehlt (Phase 1) | Workaround A anwenden, LIMEN neu starten |
| Goose: leerer response, status ok | Groq hat Modell anders benannt | `curl …/v1/models -H "Authorization: Bearer $GROQ_API_KEY" \| jq '.data[].id'` zeigen lassen, TOML `models` angleichen |
| Groq: `429 rate_limit_exceeded` | 30 RPM Soft-Ceiling | Warten + seltener testen, Phase-2-Cooldown-Header abwarten |
| `audit_events` zeigt Klartext-Key | Leck im Audit-Stream | Sofort LIMEN stoppen, Issue notieren, Phase 1 hat `redact_authorization_headers = true` als Default |
| `phase1_smoke.sh` schlägt fehl | LIMEN kaputt | Vor Goose-Phase aufhören, Phase-1-Reset-Gate (`docs/phase1-reset-gate.md`) abarbeiten |
| Goose startet, sieht aber `limen_local ≥1 Modell nicht` | Goose Schema erwartet `models: [...]` statt `model:` | Launcher-Patch in `scripts/launch_limen.py::_goose_yaml_block` korrigieren |
| Goose startet, Provider gewählt, sendet nichts | 127.0.0.1:8000 nicht erreichbar | `ss -ltn 'sport = :8000'` und LIMEN-Logs prüfen |
| Goose-Chat zeigt nach Skript-Run `provider_unreachable` statt Token | `--keep-config` hat eine Config mit `keys = []` hinterlassen; Auth-Lücke §4.0 zuschlägt | Workaround A aus §4.0 nachholen, dann `limen start` neu — **nicht** das Skript erneut laufen lassen |
| Goose-Chat-Round-Trip erscheint in Audit mit Quell-Tag statt den Skript-Calls | Skript- und Goose-Calls sind **getrennte Sessions** in `state.db` | Unterscheidung mit `WHERE ts > datetime('now','-5 minutes')` und Round-Trip-Gruppen-ID im Audit-Stream (Phase 2 liefert strukturierte IDs) |
| `phase1_smoke.sh` schlägt nach `--keep-config`-Run fehl | Config wurde auf nur-Groq-Provider reduziert, andere Provider im Default-Smoke nicht da | Smoke gegen Port 8000 fahren **vor** `--keep-config`, oder: nur die `/health` und `/v1/models`-Prüfungen in Phase-D durchführen |

---

## 10. Was ich aus dem Weg räume (für dich)

- **README.md:** Verweis auf dieses Doc als „Goose-GUI Live Test" Abschnitt
  ergänzen, neben dem bestehenden Phase-1-Smoke-Verweis.
- **ARCHITECTURE.md:** §10.3 mit dem Architektur-Bild + Phasen A-E als
  Ablauf verankern für spätere Onboarding-Sessions.
- **`docs/phase1-reset-gate.md`** unverändert — die Reset-Gate-Definition
  bleibt die Wahrheit, dieses Doc fügt nur den echten Goose-Live-Case
  hinzu.

---

## 11. Verwandte Dateien

- `docs/phase1-reset-gate.md` — Phase-1-Vertrag und Smoke-Pfad.
- `docs/live-groq-e2e.md` — Skript-getriebener LIMEN→Groq-Pfad (kein Goose).
- `scripts/launch_limen.py` — Auto-Detection und Provider-Swap.
- `scripts/phase1_smoke.sh` — LIMEN Pre-Flight-Smoke.
- `scripts/live_e2e_groq.sh` — Skript-getriebenes Live-Groq-E2E.
- `ARCHITECTURE.md` §10 — Tooling- und Reset-Sektion.
- `AGENTS.md` §1 (keine Stubs/Catch-0) — gilt für jeden Schritt hier.
