---
name: osint-self-audit
description: "OSINT-Selbstaudit / digitaler Fußabdruck in EINEM Task, ohne Vorwissen. Nutze diesen Skill, wenn der User wissen will, was das Internet und die lokale Maschine über IHN verraten ('was weiß das Internet über mich', 'was findet ein Fremder über mich heraus', 'Privacy-Audit', 'digitale Fußspur', 'OSINT', 'Doxx-Selbsttest', 'Profil aufräumen', 'wie viel ist über mich öffentlich'). Liefert ein vollständiges Dossier mit Evidenz-Legende (✅/⚠️/❌). Enthält ein Case-File mit allen Ergebnissen des Subjekts 'vannon0911' als Referenz. NUR für Selbst-Audits des anfragenden Users — niemals für Dritte."
category: osint-self-audit
stack: GOVERNANCE + LOGISCH
risk: high
side_effects: network_calls
requires_approval: true
version: 1.0.0
last_verified: 2026-08-11
metadata:
  author: vannon
  version: 1.0.0
  category: security
  sensitivity: "⚠️ ENTHÄLT PERSONENBEZOGENE DATEN (Case-File). Nur lokal verwenden, niemals publizieren oder an Dritte weitergeben."

---
# OSINT-Selbstaudit — digitaler Fußabdruck in einem Task

Ziel: In **einem einzigen Task** (ohne vorherigen Kontext) herausfinden, was über den anfragenden User bekannt ist — aus **lokalen Daten** (read-only) und **öffentlichem Internet** — und als Dossier mit Evidenz-Legende berichten.

> ⚠️ **Sicherheitsgrenze:** Dies ist ein **Selbst-Audit**. Das Subjekt ist IMMER der User, der den Skill anfordert. Keine Recherche über Dritte, kein Doxxing, keine Deanonymisierung, kein Scraping von Kontakten/Freunden Dritter. Freundeslisten, Kontaktlisten und private Daten Anderer werden **nicht** in den Bericht übernommen.

## Wann nutzen (Trigger)

- „Was weiß das Internet über mich?"
- „Was findet ein Fremder über mich heraus?"
- „Privacy-Audit / OSINT-Selbsttest / Doxx-Selbsttest"
- „Wie viel ist über mich öffentlich?" / „Wie groß ist mein digitaler Fußabdruck?"
- „Erstelle mein Profil / Dossier"

## Ablauf in einem Task (Kurzversion — Details: `references/runbook.md`)

1. **Ankündigen:** read-only Modus, Evidenz-Legende (✅ direkt verifiziert · ⚠️ nur Suchtreffer · ❌ widerlegt).
2. **Lokale Recon (read-only):** System-ID, Hostname, Home-Ordner, Git-Identitäten, Shell-History (Handles!), SSH-Key-Kommentar, Env-**Key-Namen** (Werte niemals ausgeben), Projekte, Mail-/AI-Tool-Configs.
3. **Handle-Extraktion:** aus History + Configs die Benutzernamen (github/gitlab/psn/steam) sammeln.
4. **Online-Recon:** Jede Plattform separat durchsuchen (Steam, GitHub, Reddit, Twitch, TikTok, YouTube, Twitter/X, Facebook, Instagram, PSN, Pastebin). Suchstrings siehe Runbook.
5. **Kanonische Verifikation:** Jeden wichtigen Fund per `read_url` auf der Original-Seite prüfen (Reddit-Fallback: `old.reddit.com`). Such-Snippets sind KEINE Beweise.
6. **GitHub-API-Falle (kritisch!):** Commit-Historien öffentlicher Repos zeigen Author-Namen + Emails via `api.github.com/repos/<owner>/<repo>/commits`. READMEs lügen nicht, aber die **Commit-Historie verrät mehr** — dort liegt oft der Klarname. (Rate-Limit: unauthentifiziert 60/h — zuletzt und sparsam nutzen, priorisieren.)
7. **Synthese:** Dossier erstellen (Steckbrief, Plattform-Matrix, Verknüpfungskette, Timeline, Risiko-Bilanz). Jede Aussage mit Evidenzgrad. Nicht gefundenes explizit als „nicht gefunden" kennzeichnen — „kein Beleg" ≠ „existiert nicht".
8. **Abschluss:** De-Risiko-Maßnahmen anbieten (`references/mitigations.md`).

## Output-Format (Dossier)

```markdown
# OSINT-Dossier — <Handle>
- Steckbrief-Karte (Handle, Alias, Plattformen, Klarname 🟢/🟡/🔴, Wohnort, Emails, Telefon, Adresse, Leaks)
- Plattform-Matrix (Plattform | Handle | Stats | Was ein Fremder sieht | Evidenz)
- Verknüpfungskette (wie ein Fremder die Identität zusammensetzt — inkl. Commit-Historie!)
- Timeline (Konto-Erstellungen, Streamer-Ära, Aktivität)
- Risiko-Bilanz (Kategorie | Ampel | Begründung)
- Kernaussage: Was ist das größte Leck? (meist: Handle-Reuse + öffentliche Git-Commit-Emails)
```

## Referenz: Case-File

Das vollständige, bereits verifizierte Ergebnis für das Subjekt **`vannon0911`** (inkl. aller Emails, Accounts, URLs und der Commit-Historie-Falle) liegt in **`references/case-file-vannon.md`**. Ein frischer Agent kann es als:
- **Soll-Zustand** verwenden (Ergebnisse reproduzieren/abgleichen), und
- als **Schablone** für den Aufbau neuer Dossiers.

## Wichtige Lektionen (aus Fehlern gelernt)

1. **Immer Commit-Historie prüfen**, nicht nur README — Klarname + Email liegen oft in Git-Commits.
2. **Keine Snippets als Beweis** — jede Kernaussage auf der Original-Seite verifizieren (ein Researcher-Fund „Instagram 2018" erwies sich als fremdes Konto).
3. **Emails zählen:** Es sind meist mehr als gedacht (Shell-History, SSH-Key-Kommentar, Agent-DBs, Git-Commits, Repo-Readmes).
4. **Werte von Secrets nie ausgeben** — nur Key-Namen auflisten.
5. **Handle-Reuse ist das größte Leck:** ein Name verbindet Steam/GitHub/Reddit/Twitch/TikTok/YouTube/PSN.
