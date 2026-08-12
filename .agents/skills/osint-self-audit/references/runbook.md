# Runbook — komplette Selbst-Recherche in einem Task

> Alle Befehle sind **read-only** (nichts schreiben, nichts installieren). Secrets: **nur Key-Namen** ausgeben, nie Werte. Befehle mit `timeout` absichern, wenn große Verzeichnisse durchsucht werden.
> **Pfade sind Beispiele** aus der Umgebung des Skill-Besitzers (`~/Schreibtisch/projects/`, `~/.freebuff/`, `~/.claude.json`). Vor der Ausführung an die tatsächliche `$HOME`-Struktur des untersuchten Systems anpassen (`ls ~` zuerst) — Ziel ist Reproduktion **ohne Kontext** auf beliebigen Systemen.

## Schritt 1 — Ankündigung & Legende

Dem User mitteilen: read-only, Evidenz-Legende, Dauer. Legende: ✅ direkt verifiziert · ⚠️ nur Suchtreffer/Researcher · ❌ widerlegt.

## Schritt 2 — Lokale Recon (parallel via Basher)

```bash
# Identität
whoami; hostname; id; uname -a; head -3 /etc/os-release; hostname -I
ls /home; getent passwd $(whoami) | cut -d: -f7

# Home-Überblick (Ordner verraten Projekte, Tools, Hobbys)
ls -la /home/$USER | head -45

# Git-Identitäten + Remotes (auch in allen Projekt-Repos)
cat ~/.gitconfig
for d in ~/Schreibtisch/projects/*/; do echo "--- $d"; git -C "$d" log --all --format='%ae' 2>/dev/null | sort -u | head -8; done

# Handles aus Shell-History (Kern-Schritt!)
grep -hoE '(github\.com|gitlab\.com)/([A-Za-z0-9._-]+)' ~/.zsh_history ~/.bash_history 2>/dev/null | sort -u

# ALLE Emails aus History (ZÄHLEN, nicht head-10!)
grep -hoE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' ~/.zsh_history 2>/dev/null | sort | uniq -c | sort -rn | head -20

# SSH (Kommentar im Pub-Key = oft Email!)
ls -la ~/.ssh; cat ~/.ssh/id_ed25519.pub | awk '{print $NF}'; cat ~/.ssh/config 2>/dev/null

# Env: nur NAMEN sensibler Variablen
env | cut -d= -f1 | grep -iE 'key|token|secret|passw|api|user' | sort

# Emails in Agent-/App-Datenbanken (Werte bleiben unangetastet)
grep -rhoE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' ~/.claude.json ~/.freebuff/desktop-v2.db 2>/dev/null | sort -u | head -10
strings ~/.freebuff/desktop-v2.db 2>/dev/null | grep -oE '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' | sort -u | head -10

# App-Spuren (Streaming, Browser, Mail, Gaming)
ls ~/.config | grep -iE 'obs|twitch|chrom|firefox|evolution|steam|kodi'
```

## Schritt 3 — Online-Recon (pro Plattform ein Researcher, parallel)

Suchstrings je Plattform (Handle = gefundener Kern-Handle):

- Steam: `steamcommunity.com <handle>` → Profil laden (Standort, Level, „Currently In-Game", Review-Tab!)
- GitHub: `<handle>` Profil + Repos laden; **danach Commit-API (Schritt 5)**
- Reddit: `old.reddit.com/user/<handle>/overview` (funktioniert oft, wo www blockt) → Bio, Subreddits, ältere Posts über Pagination
- Twitch: `twitch.tv/<handle>` + `/videos?filter=all` → Bio, VODs, Kategorien
- TikTok: `tiktok.com/@<handle>` → Bio, **Ort**, Follower, „since YYYY"
- YouTube: `youtube.com/<handle>` oder `channel/<ID>` → Bio, Video-Titel, Stream-Tools (PRISMLiveStudio etc.)
- Twitter/X: `site:x.com <handle>` · Facebook: `site:facebook.com <handle>` · Instagram: `site:instagram.com <handle>` → **Fehlen dokumentieren** („kein indexiertes Konto")
- PSN/Gaming-Foren: `<handle> squad`, `<handle> Delta Force`, `<handle> Monster Hunter`
- Leaks: `<email>` pastebin · `<email>` leak · `<email>` breach (nur Index; echte Leak-Checks leitet man den User an HIBP weiter)

## Schritt 4 — Kanonische Verifikation

Jede Kernaussage per `read_url` auf der Original-Seite prüfen. Reddit-Fallback: `old.reddit.com/...`. **Ein „Researcher hat gesagt" ist keine Evidenz.** Bei Diskrepanz: ❌ markieren und im Bericht aufführen.

## Schritt 5 — GitHub-API-Falle (kritisch, zuletzt wegen Rate-Limit)

```bash
# Unauthentifiziert: 60 Requests/h. Sparsam, priorisiert, nur für die wichtigsten Repos.
# URL: https://api.github.com/repos/<owner>/<repo>/commits?per_page=100
# JSON-Felder: commit.author.name + commit.author.email (+ Co-authored-by in message)
```
> **Warum kritisch:** GitHub-UI versteckt Emails, aber die API liefert Author-Name **und** Email. README-Kontaktadressen sind harmlos dagegen — die Commit-Historie enthält oft Klarname + Geburtsjahr-Email. Genau das war beim Case-File der Durchbruch.

## Schritt 6 — Synthese

Dossier bauen (Format in SKILL.md). Evidenz je Zeile. Drei Ebenen trennen: **beobachtet** (✅) / **korroboriert** (mehrere Quellen) / **Interpretation** (klar als solche labeln) / **unbekannt**.

## Schritt 7 — Abschluss

De-Risiko-Maßnahmen anbieten (`references/mitigations.md`): Git-Historie bereinigen ist meist der größte Hebel. Fragen, ob Artefakte geschrieben werden sollen (nur mit expliziter Freigabe — Standard ist read-only).
