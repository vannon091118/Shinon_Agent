# 🔬 SKILL-AUDIT v3 — Verifizierter Nutzen- und Risiko-Audit

> **645 Skills · 29 Kategorien · Stand: 11. August 2026 (Namenskonflikte bereinigt)**
>
> Quelle der Bestandszahlen: lokale `skills/**/SKILL.md`-Dateien, rekursiv gezählt. Reproduzierbarer Prüfer: [`skills/validate-catalog.py`](validate-catalog.py). Die Zahl 540 ist ein PyYAML-6.0.3-`SafeLoader`-Bestandsbefund, nicht automatisch der Fehlerstatus des produktiven Skill-Loaders. Der Validator ist ohne PyYAML oder ohne explizites `--allow-yaml-errors` fail-closed.
> Dieser Report trennt lokale Befunde, Ableitungen und externe Gegenprüfung. Er behauptet nicht, dass ein LLM jede Skill-Anweisung automatisch korrekt validiert.

## 1. Ergebnis auf einen Blick

| Befund | Ergebnis |
|---|---:|
| Lokale `SKILL.md` | **645** |
| Top-Level-Kategorien | **29** |
| Fehlende `name`-Felder (textuell) | **0** |
| Fehlende `description`-Felder (textuell) | **0** |
| Strikt parsebare YAML-Frontmatter | **106/646** |
| PyYAML 6.0.3 `SafeLoader`-Parserfehler (Bestandsbefund) | **540/646** |
| Kategorien ohne README (vor der Korrektur) | **1** → `content-parser`; aktuell **0** |
| Doppelte `name`-Werte | **0** (5 Gruppen + 1 Anomalie bereinigt am 11.08.2026) |
| Alter Index | **643 Skills / 27 Kategorien** — korrigiert |

### Wichtigste Korrektur

Der vorherige Audit war nicht vollständig: `content-parser` fehlte als Top-Level-Kategorie im Index; `osint-self-audit` war im Index nicht als eigene Kategorie ausgewiesen; `communication-apis` wurde mit 82 statt 108 Skills geführt. Außerdem enthielt der alte Report 28 Detailblöcke für 27 Kategorien. Die neue Quelle der Wahrheit ist der Dateibestand.

## 2. Bestand nach Kategorie

| Kategorie | Skills | Zweck | Dominanter Stack | Autonomie |
|---|---:|---|---|---|
| `agents` | 7 | Agentenführung, Orchestrierung, Webhooks, Doku, Tracking | AUTONOM + GOVERNANCE | gated |
| `ai-ml` | 28 | Hugging Face, NVIDIA, OpenAI und Modellbetrieb | LOGISCH + SELF-IMPROVE | gated |
| `bioscience` | 76 | Bio-APIs, NGS, Protein- und Molekül-Workflows | LOGISCH + GOVERNANCE | gated |
| `claude-tools` | 9 | Memory, Scheduling und Office-Dateiverarbeitung | MEMORY + AUTONOM | gated |
| `cloud-platforms` | 89 | Vercel, Render, Netlify, Cloudflare, DigitalOcean | AUTONOM + GOVERNANCE | gated |
| `communication` | 38 | Gmail, Outlook, Slack, Teams, Kalender, Superhuman | GOVERNANCE + KREATIV | human-required bei Send |
| `communication-apis` | 108 | Twilio- und Zoom-APIs für Nachrichten, Voice, Video | GOVERNANCE + AUTONOM | human-required bei externem Send |
| `content-parser` | 1 | URL-Inhalte extrahieren und normalisieren | LOGISCH + GOVERNANCE | gated |
| `data-analytics` | 14 | Airtable, Deepnote, Hex, Mixpanel, PostHog | LOGISCH | gated |
| `databases` | 10 | Supabase, Neon, Box und Google Drive | LOGISCH + GOVERNANCE | gated |
| `design` | 6 | UI-Richtung, Canvas, Tailwind, Accessibility, Performance | KREATIV → GOVERNANCE → LOGISCH | gated |
| `design-tools` | 40 | Figma, Canva, Remotion, Hyperframes, MagicPath, DataViz | KREATIV + GOVERNANCE | gated |
| `development` | 8 | Debugging, Architektur, Python, TypeScript, React Native | LOGISCH + SELF-IMPROVE | ready mit Tests |
| `devtools` | 20 | GitHub, CircleCI, Sentry, Replay, Temporal, Skill-Evaluation | LOGISCH + AUTONOM | gated |
| `documents` | 4 | DOCX, PDF, PPTX und XLSX | LOGISCH + GOVERNANCE | gated |
| `ecommerce` | 26 | Shopify, Stripe und Wix | GOVERNANCE + AUTONOM | human-required bei Geld |
| `finance` | 44 | Daloopa, Moody’s, Morningstar, Datasite, Chronograph | LOGISCH + GOVERNANCE | human-required bei Advice |
| `games` | 2 | PlayCanvas und Lua-Modding | KREATIV + GOVERNANCE | gated |
| `gaming` | 9 | Phaser, Three.js, R3F und Asset-Pipelines | KREATIV → LOGISCH | gated |
| `gemini-tools` | 2 | Antigravity-Guide und Customizations | MEMORY + GOVERNANCE | gated |
| `media` | 6 | Audio, Screenshots, Desktop-Automation, HeyGen, Generierung | KREATIV + GOVERNANCE | gated |
| `meta` | 3 | Skills finden, erstellen, evaluieren und Learnings pflegen | SELF-IMPROVE + MEMORY | gated |
| `mobile-dev` | 35 | iOS, macOS, Expo und Android-QA | LOGISCH + GOVERNANCE | gated |
| `osint-self-audit` | 1 | Datenschutz-Selbstaudit für den anfragenden User | GOVERNANCE + LOGISCH | human-required |
| `productivity` | 24 | Linear, Notion, Atlassian, SharePoint, Zotero, Legal | MEMORY + GOVERNANCE | gated |
| `research` | 5 | Community-/Deep-Research, Heatmaps, Persona, Wiki | LOGISCH + MEMORY | gated |
| `security` | 14 | Security-Scans, Threat Models, Findings, Code Review | GOVERNANCE + LOGISCH | human-required bei Freigabe |
| `testing` | 1 | Playwright-E2E, Fixtures, Mocking, Reports | LOGISCH + GOVERNANCE | ready mit CI |
| `web-dev` | 16 | Web-App-Building und Superpowers-Workflows | KREATIV → GOVERNANCE → LOGISCH | gated |

## 3. Was jeder Skill-Typ im Vorhaben leisten soll

Die 646 Skills werden nicht nach Dateinamen „zusammengeklebt“. Ihre Rolle ergibt sich aus ihrer Beschreibung und ihrem Ausführungsrisiko:

| Skill-Typ | Zweck | Wert | Bündelungsregel | Falsifizierungs-Gate |
|---|---|---|---|---|
| Router/Top-Level | Aufgabe erkennen und an Spezialisten weiterleiten | weniger Trigger-Konflikte | ein Router pro Anbieter-/Domänenfamilie | Fehlrouting mit Testprompts messen |
| API-/CLI-Operator | einen klaren Dienst bedienen | reproduzierbare Tool-Nutzung | Auth, Version und Rate-Limit zentralisieren | `--help`, Schema- und Smoke-Test |
| Kreativ-Generator | Varianten, Texte, UI oder Medien erzeugen | hohe Suchbreite | nie als eigene Qualitätsinstanz verwenden | Review gegen Brief, Brand- und Lizenzregeln |
| Logik-/Analyse-Skill | Daten, Code oder Ergebnisse prüfen | Fehler sichtbar machen | Ergebnis an Parser, Rechner oder Test übergeben | harte Assertions, nicht LLM-Meinung |
| Governance-/Security-Skill | Rechte, Grenzen, Freigaben, Audit | Schaden begrenzen | vor Seiteneffekten ausführen | fail-closed, Scope- und Approval-Test |
| Memory-/Dokumentations-Skill | Wissen, Quellen und Entscheidungen bewahren | weniger Wiederholungsfehler | versioniert, dedupliziert, mit Provenienz | Retrieval- und Drift-Test |
| Self-Improve-/Eval-Skill | Verhalten messen und verbessern | nachvollziehbare Iteration | Änderungen nur über Regression-Suite promoten | held-out Tests und Rollback |
| Domain-Router | komplexe Spezialpipeline wählen | weniger Kontext-Bloat | Routing von Ausführung trennen | falsche Route als negatives Testbeispiel |

## 4. 6-Stack-Regeln, technisch korrigiert

### MEMORY
Speichert Entscheidungen, Quellen, Konfigurationen und bestätigte Learnings. Rohes Vektor-RAG ist nur ein Abrufkanal, keine Wahrheit. Jeder Memory-Eintrag braucht Quelle, Zeit, Status und Version.

### SELF-IMPROVE
Verbessert Skills nur über beobachtete Fehler, reproduzierbare Tests und explizite Promotion. Kein Skill darf seine eigene Produktionsdefinition ungeprüft überschreiben.

### GOVERNANCE
Regeln liegen möglichst außerhalb des LLM: JSON-Schema, AST-/Parserprüfung, Berechtigungsprüfung, Budget, Rate-Limit, Allowlist, Approval oder CI-Gate. „Der Prompt sagt, sei vorsichtig“ ist kein Gate.

### AUTONOM
Dirigiert begrenzte Schritte über einen Zustandsgraphen. Jeder Schritt hat Input, Output-Schema, Timeout, Retry-Limit, Seiteneffekt-Klasse und Abbruchzustand.

### KREATIV
Erzeugt Kandidaten und Varianten. Kreativität darf nicht als Beweis für Richtigkeit, Markenfreigabe, Sicherheit oder rechtliche Zulässigkeit gelten.

### LOGISCH
Prüft mit Code, Parsern, Tests, Messwerten, Quellenabgleich oder Fachregeln. Ein zweiter LLM-Text ist ein Review-Hinweis, aber keine formale Verifikation.

### Harte Pipeline

```text
KREATIV  →  GOVERNANCE  →  LOGISCH  →  MEMORY / SELF-IMPROVE
             (Policy-Code)    (Tests/Parser/Rechner)
```

Die Pfeile bedeuten Kontrollpunkte, nicht dass jedes Problem zwingend alle Stufen braucht. Kleine rein analytische Aufgaben dürfen KREATIV überspringen; externe Kommunikation, Geld, Deployments und personenbezogene Daten dürfen die Governance-Stufe nicht überspringen.

## 5. Kategorie-Audit: Nutzen, Anpassung, Falsifizierung

### `agents` — 7
- **Gedacht für:** Autorun, Rollenverteilung, User/Agent-Arbeitsteilung, Webhook- und Tracking-Adapter, Doku.
- **Wert:** macht aus einzelnen Skills einen Ablauf mit Verantwortung und Übergaben.
- **Optimieren:** versionierte Handoff-Schemas, Zustandsgraph statt freier Agenten-Schwarm, Idempotenz für Webhooks und Budget-/Retry-Limits.
- **Falsifizierung:** Multi-Agenten sind nicht automatisch schneller; gemeinsame Datenbanken und APIs erzeugen versteckte Kopplung. `autorun` kann nicht beweisen, dass „fertig“ auch fachlich korrekt ist.
- **Status:** gated.

### `ai-ml` — 28
- **Gedacht für:** Modelle, Datasets, Training, Inference, NVIDIA-Infrastruktur, OpenAI-Apps.
- **Wert:** reduziert Setup- und Integrationsarbeit für ML-Systeme.
- **Optimieren:** Modell-/CUDA-/SDK-Version pinnen, Kosten- und GPU-Preflight, private Eval-Splits, Sandbox für Code und Daten.
- **Falsifizierung:** Leaderboards beweisen keine Produktionsrobustheit; `temperature=0` macht ein LLM nicht zu einem formalen Rechner.
- **Status:** gated.

### `bioscience` — 76
- **Gedacht für:** 50+ wissenschaftliche Datenquellen, NGS-Router/Pipelines und Boltz-Design/Screening.
- **Wert:** reproduzierbare Datenabfragen und Pipeline-Scaffolding.
- **Optimieren:** Referenz-Build, Tool-/Container-Version, Checksums, QC, Provenienz und unabhängige fachliche Freigabe speichern.
- **Falsifizierung:** API-Ergebnis ist nicht automatisch biologisch korrekt; ein erfolgreicher Pipeline-Lauf ist keine klinische Diagnose oder Therapieempfehlung.
- **Status:** gated; klinisch/regulatorisch human-required.

### `claude-tools` — 9
- **Gedacht für:** Memory-Konsolidierung, Termine, Briefings und Office-Dateiformate.
- **Wert:** verbindet Sitzungswissen mit wiederverwendbaren Artefakten.
- **Optimieren:** Memory-Einträge versionieren; Dokumente per Struktur- und Render-Diff prüfen; Scheduler mit deduplizierten Job-IDs.
- **Falsifizierung:** Deduplizierung kann wichtige Unterschiede löschen; ein erzeugtes Office-Dokument kann trotz syntaktischer Gültigkeit visuell falsch sein.
- **Status:** gated.

### `cloud-platforms` — 89
- **Gedacht für:** Build, Deploy, Storage, Edge, Queues, Observability und Plattformbetrieb.
- **Wert:** beschleunigt wiederholbare Deployments.
- **Optimieren:** Provider-Router, CLI-Versionen pinnen, Dry-Run, Environment-Allowlist, Secret-Scan, Kosten- und Rollback-Gate.
- **Falsifizierung:** Branch-/Environment-Schutz ist nicht automatisch unangreifbar; Admin-Bypass und Tarif-/Konfigurationsgrenzen müssen geprüft werden. Edge ist nicht pauschal schneller.
- **Status:** gated.

### `communication` — 38
- **Gedacht für:** Lesen, Zusammenfassen, Triage, Drafts und Kalenderplanung.
- **Wert:** reduziert Informations- und Planungsaufwand.
- **Optimieren:** Draft-first, Empfänger-/Kanal-Preview, PII-Redaktion, keine automatische Zusage, deduplizierte Message-ID.
- **Falsifizierung:** „Sent“ beweist nicht exakt-einmalige Zustellung; Kalenderoptimierung kennt nicht automatisch kulturelle oder organisatorische Buffer.
- **Status:** human-required bei Versand/externen Zusagen.

### `communication-apis` — 108
- **Gedacht für:** Twilio- und Zoom-Integrationen über viele Plattformen und Kanäle.
- **Wert:** wiederverwendbare Integrationsmuster für Messaging, Voice, Video, OAuth und Webhooks.
- **Optimieren:** Provider-Version/Capability-Matrix, serverseitige Token, Rate-Limit-Backoff, Webhook-Signatur, Idempotenz und Send-Approval.
- **Falsifizierung:** „Twilio/Zoom kann alles“ verwechselt Produktlinien; SDK-Versionen, Plattformen und Berechtigungen unterscheiden sich.
- **Status:** human-required bei realer Kommunikation.

### `content-parser` — 1
- **Gedacht für:** URL-Extraktion als Vorstufe für andere Skills.
- **Wert:** strukturiert externe Inhalte und Referenzen.
- **Optimieren:** Quelle als unverified markieren, kanonische URL nachprüfen, API-Key/Kosten/Rate-Limits schützen.
- **Falsifizierung:** Extrahierter Inhalt kann unvollständig, manipuliert oder paywall-/robots-bedingt nicht repräsentativ sein.
- **Status:** gated.

### `data-analytics` — 14
- **Gedacht für:** Produktmetriken, Notebooks, Airtable und Dashboards.
- **Wert:** macht Datenabfragen und Beobachtungen wiederholbar.
- **Optimieren:** Schema-first, read-only SQL, PII-Klassifizierung, Query-Hash und Metrikdefinition speichern.
- **Falsifizierung:** LLM-SQL kann Tabellen/Spalten erfinden; eine Metrik ist ohne Definition und Kohorte nicht objektiv.
- **Status:** gated.

### `databases` — 10
- **Gedacht für:** Datenbanken, Storage, Google-Drive-Objekte, RLS und Migrationen.
- **Wert:** sichere Persistenz und strukturierte Seiteneffekte.
- **Optimieren:** Migrations-Diff, RLS-Testmatrix, Indexprüfung, Least-Privilege, Backup und Rollback.
- **Falsifizierung:** RLS-Aktivierung allein beweist keine korrekte Policy; Views und privilegierte Funktionen können Schutzgrenzen verändern.
- **Status:** gated.

### `design` — 6
- **Gedacht für:** visuelle Richtung, Designsysteme, Canvas, Accessibility und Performance.
- **Wert:** macht kreative Arbeit absichtsvoll und prüfbar.
- **Optimieren:** Tokens als Datenmodell; axe-/Lighthouse-/Browser-Checks getrennt von Kreativentscheidungen.
- **Falsifizierung:** „distinctive“ ist kein objektiver Messwert; Lighthouse ersetzt keine Real-User-Messung.
- **Status:** gated.

### `design-tools` — 40
- **Gedacht für:** Figma, Canva, Motion, Remotion, MagicPath und Datenvisualisierung.
- **Wert:** übersetzt Designabsicht in Assets und Code.
- **Optimieren:** Figma-Code-Mapping, Brand-Token-Gate, Lizenzprovenienz, Render-Snapshot und Accessibility-Test.
- **Falsifizierung:** Plugin- oder API-Ausgabe kann driften; generierte Logos, Texte und Diagramme sind nicht automatisch markenkonform oder wahr.
- **Status:** gated.

### `development` — 8
- **Gedacht für:** Planen, Debuggen, Architektur, Review, Testing, Performance und TypeScript/RN.
- **Wert:** stärkster logischer Kern für Codearbeit.
- **Optimieren:** Fehlerhypothese→Beweis→minimaler Fix→Regressionstest; nach wiederholten Fehlversuchen Architektur eskalieren.
- **Falsifizierung:** Root Cause ist bei Blackboxes nicht immer beweisbar; Coverage ist kein Qualitätsbeweis.
- **Status:** ready mit Tests und Review.

### `devtools` — 20
- **Gedacht für:** GitHub/CI, Sentry, Replay, Temporal, Base44 und Skill-Evaluation.
- **Wert:** schließt den Feedback- und Betriebszyklus.
- **Optimieren:** Dry-Run vor Publish, Branch-Schutz, CI-Retry-Limit, Workflow-Determinismus und Post-Deploy-Rollback.
- **Falsifizierung:** Grün bedeutet nicht flaky-frei; Sentry-Symptom und Root Cause sind nicht dasselbe; Temporal-Workflows müssen Replay-Determinismus einhalten.
- **Status:** gated.

### `documents` — 4
- **Gedacht für:** DOCX, PDF, PPTX und XLSX lesen, erzeugen und bearbeiten.
- **Wert:** liefert prüfbare Business-Artefakte.
- **Optimieren:** OOXML-/PDF-Strukturdiff, Render-Preview, Formel-/Referenzprüfung, Template-Versionierung.
- **Falsifizierung:** Parser-Erfolg beweist kein korrektes Layout; LLM-generierte Tabellenformeln können semantisch falsch sein.
- **Status:** gated.

### `ecommerce` — 26
- **Gedacht für:** Storefronts, Shopify-Apps, Stripe-Zahlungen und Wix-Apps.
- **Wert:** beschleunigt Commerce-Implementierung.
- **Optimieren:** Geldbewegung nur mit Idempotenz, Betrag-/Währung-/Empfänger-Preview, Refund-Gate, Webhook-Reconciliation und Sandbox.
- **Falsifizierung:** Idempotency-Keys haben Providerregeln/TTL; „API-Aufruf erfolgreich“ bedeutet nicht, dass Fulfillment oder Refund fachlich korrekt ist.
- **Status:** human-required bei Geld und Refunds.

### `finance` — 44
- **Gedacht für:** DCF/Comps/Earnings, Credit, Funds, M&A und Portfolio-Reports.
- **Wert:** Recherche- und Modellierungsassistenz, nicht autonome Anlageberatung.
- **Optimieren:** Zahlen nur aus Quellen-IDs; Rechnen in deterministischem Code; Annahmen, Fallbacks und Sensitivitäten ausweisen.
- **Falsifizierung:** Mathe kann korrekt sein, obwohl Inputs veraltet oder selektiv sind; Peer-Auswahl ist eine Modellannahme.
- **Status:** human-required bei Advice/Entscheidungen.

### `games` — 2
- **Gedacht für:** PlayCanvas-ECS und sichere Lua-Spielsysteme.
- **Wert:** engine-spezifischer Game-/Mod-Bau.
- **Optimieren:** server-authoritative Regeln, Lua-Sandbox-Review, Asset-Manifest und deterministische Update-Grenzen.
- **Falsifizierung:** LLM-Lua ist nicht automatisch multiplayer-safe; PlayCanvas passt nicht zu jedem Genre oder Assetmaßstab.
- **Status:** gated.

### `gaming` — 9
- **Gedacht für:** Browser-Games und Sprite-/3D-Asset-Pipelines.
- **Wert:** kreative Prototypen mit messbaren Runtime-Grenzen.
- **Optimieren:** State/View-Trennung, Asset- und Frame-Budget, Playwright-/Playtest-Schleife.
- **Falsifizierung:** LLM-Inferenz gehört nicht in einen latenzkritischen Game-Loop; Browser-Performance auf Desktop überträgt sich nicht auf Mobile.
- **Status:** gated.

### `gemini-tools` — 2
- **Gedacht für:** Gemini-/Antigravity-spezifische Navigation und Anpassung.
- **Wert:** Laufzeitwissen für ein bestimmtes Agenten-Ökosystem.
- **Optimieren:** Produkt-/CLI-Version, Referenz-Hash und Smoke-Test dokumentieren.
- **Falsifizierung:** Proprietäre Customizations sind nicht universell; lokale Guides veralten bei Plattformupdates.
- **Status:** gated.

### `media` — 6
- **Gedacht für:** Generierung, Transkription, Avatare, Screenshots und Desktop-Steuerung.
- **Wert:** multimodale Eingabe und Ausgabe.
- **Optimieren:** Lizenz-/Einwilligungsnachweis, Kostenlimit, Modell-/Codec-Metadaten und lokale Verarbeitung bevorzugen.
- **Falsifizierung:** Seed allein garantiert keine bitweise Reproduzierbarkeit; Transkription kann bei Akzenten, Stille und Fachsprache Fehler enthalten.
- **Status:** gated.

### `meta` — 3
- **Gedacht für:** Skills suchen, erstellen, evaluieren und aus Fehlern lernen.
- **Wert:** zentraler Self-Improve-Kern.
- **Optimieren:** Skill-Änderungen nur per Benchmark, Regression, Review und Rollback promoten; externe Skills vor Installation prüfen.
- **Falsifizierung:** Mehr Skills erhöhen nicht automatisch Qualität; Selbstmodifikation ohne Ground Truth kann Regressionen verstärken.
- **Status:** gated.

### `mobile-dev` — 35
- **Gedacht für:** native iOS/macOS-Apps, Expo und Android-QA.
- **Wert:** plattformspezifische Build-, Debug- und Release-Hilfe.
- **Optimieren:** SDK/Xcode-Version pinnen, Signing-/Entitlement-Checks, EAS-Preflight, reale Geräte ergänzen.
- **Falsifizierung:** Cloud-Build beseitigt keine Apple-/Google-Konto- oder Review-Anforderungen; Emulator-QA deckt reale Hardware nicht vollständig ab.
- **Status:** gated.

### `osint-self-audit` — 1
- **Gedacht für:** read-only Selbstprüfung des eigenen öffentlichen und lokalen digitalen Fußabdrucks.
- **Wert:** Privacy-Risiken sichtbar machen.
- **Optimieren:** nur User-Selbstaudit, Secrets nie ausgeben, lokale Daten minimieren, jede Online-Aussage kanonisch verifizieren, Case-File nicht publizieren.
- **Falsifizierung:** Suchtreffer sind keine Beweise; Handle-Matches können zu einer falschen Identitätsverknüpfung führen.
- **Status:** human-required.
- **Anomalie:** Der identische Skill liegt zusätzlich unter `security/osint-self-audit`; beide Pfade sind aktuell eine Duplikat-Gruppe.

### `productivity` — 24
- **Gedacht für:** Aufgaben, Wissen, Meetings, Legal- und Enterprise-Dokumente.
- **Wert:** übersetzt unstrukturierten Kontext in kontrollierte Arbeitsobjekte.
- **Optimieren:** Single-Writer pro Datentyp, schema-first Updates, idempotente Writes, Status-/Provenienzfeld.
- **Falsifizierung:** Knowledge-Graph ist kein automatisch aktueller Source of Truth; Sync kann bei Schemaänderungen semantisch driften.
- **Status:** gated.

### `research` — 5
- **Gedacht für:** Quellenrecherche, Community-Evidenz, Heatmaps und Wiki-Konsolidierung.
- **Wert:** nachvollziehbare Erkenntnisse statt bloßer Antworttexte.
- **Optimieren:** Coverage-Ledger, kanonische URLs, Retrieval-/Verification-Trennung, Evidence JSON und Bias-/Unknown-Felder.
- **Falsifizierung:** reale URL bedeutet nicht, dass sie die Behauptung stützt; eine Heatmap zeigt nur die Stichprobe, nicht „die Community“.
- **Status:** gated.

### `security` — 14
- **Gedacht für:** Threat Model, Finding-Lifecycle, Security-Scan, Validation und Code Review.
- **Wert:** wichtigste Governance-Schicht.
- **Optimieren:** fail-closed Scope-Gate, Threat Model vor Discovery, harte Tool-Budgets, unabhängige Tests und menschliche Freigabe für Risikoakzeptanz.
- **Falsifizierung:** mehr Scan-Pässe bedeuten nicht automatisch mehr Recall; ein vorgeschlagener Fix kann Ursache und Regression übersehen.
- **Status:** human-required bei Risikoakzeptanz/Release.

### `testing` — 1
- **Gedacht für:** Playwright-E2E, Page Objects, Fixtures, API-Mocking und Trace-Auswertung.
- **Wert:** maschinenprüfbare Ausführung kritischer User-Flows.
- **Optimieren:** role-/label-basierte Locators, deterministische Testdaten, keine festen Sleeps, Flaky-Test-Quarantäne.
- **Falsifizierung:** E2E-Coverage ist nicht Produktqualität; UI-Tests können durch Timing, Browser und externe Dienste flaken.
- **Status:** ready mit CI-Gate.

### `web-dev` — 16
- **Gedacht für:** Frontend-App-Building, React/Next, shadcn, Supabase und strukturierte Entwicklungsworkflows.
- **Wert:** verbindet kreative Umsetzung mit Test- und Review-Schleifen.
- **Optimieren:** kreative Komponenten zuerst als Kandidaten; danach Accessibility, Performance, Security, Tests und Deployment separat prüfen.
- **Falsifizierung:** App-Builder-Boilerplate ist keine korrekte Businesslogik; shadcn ist kein fertiges Produktdesign; Supabase-Integration ist nicht automatisch sicher.
- **Status:** gated.

## 6. Lokal gefundene Anomalien

### Doppelte `name`-Werte — ALLE BEREINIGT (11.08.2026)

| Name (ALT) | Pfade | Lösung |
|---|---|---|
| `agents-sdk` → `openai-agents-sdk` / `cloudflare-agents-sdk` | ai-ml/openai + cloudflare | Provider-Präfix vergeben ✅ |
| `chronograph-portfolio-company-one-pager` → `chronograph-gp-...` / `chronograph-lp-...` | finance GP und LP | GP/LP-Kontext im Namen ergänzt ✅ |
| `osint-self-audit` → nur Top-Level | Top-Level + `security/` | security/-Duplikat gelöscht; Top-Level ist kanonisch ✅ |
| `shadcn` → `vercel-shadcn` / `shadcn-best-practices` | Vercel und Web-Dev | Provider-/Workflow-Kontext ergänzt ✅ |
| `supabase-postgres-best-practices` → canonical + `-web` Suffix | databases und web-dev | databases ist kanonisch; web-dev erhielt Suffix ✅ |
| `v` → `view-refactor` | mobile-dev/build-macos-apps | War bereits behoben; Name ist korrekt `view-refactor` ✅ |

### Weitere Strukturprobleme

- Alle 646 Skills enthalten textuell eine `name`- und `description`-Zeile. Das bedeutet nicht, dass die Frontmatter formal parsebar ist: Der strikte YAML-Test fand 540 Parserfehler, überwiegend durch unquoted Vendor-Präfixe wie `[codex:hugging-face]`. Das ist jetzt ein Hauptproblem des Health-Checks.
- Mehrere `description`-Zeilen nutzen YAML-Faltungsmarker (`>-`, `|`) oder unquoted Vendorpräfixe. Ein Parser muss YAML korrekt lesen; simples `grep` erzeugt falsche Leer-/Duplikatbefunde. **Nächster technischer Schritt:** Parserfehler kategorisieren und zuerst den Loader-Vertrag klären, bevor 540 Dateien massenhaft umformatiert werden.
- `communication-apis` ist die größte Kategorie (108) und braucht Router/Capability-Matrix statt eines flachen Triggerhaufens.
- `content-parser` hatte vor dieser Runde keine README; aktuell haben alle 29 Kategorien eine README.
- `osint-self-audit` enthält personenbezogene Referenzdaten im Skill-Kontext. Das ist ein Governance-/Privacy-Risiko und kein normaler Skill-Inhalt. Dieser Pfad darf nicht unkontrolliert nach `~/.agents/skills` oder in andere globale Agentenverzeichnisse repliziert werden; ein globaler Sync muss ihn explizit ausschließen oder eine bereinigte Variante verwenden.

## 7. Online-Falsifizierung: belastbare Regeln

Die Online-Recherche wurde am 11. August 2026 als Gegenprüfung verwendet, nicht als Ersatz für lokale Analyse. Die folgenden Punkte sind technische Empfehlungen aus den verlinkten Dokumentationen, keine universellen Beweise für jede Anbieter-Version:

1. **Deploy-Gates:** GitHub-Environment-Schutz kann je nach Berechtigung, Tarif und Bypass-Einstellung anders wirken. Gate-Konfiguration explizit testen; nicht nur den Namen der Regel dokumentieren.
2. **Zahlungen:** Idempotency-Keys sind provider- und zeitabhängig. Transaktionsstatus über Webhooks/Reconciliation prüfen; Geld- und Refund-Aktionen nicht allein aus einem LLM-Text ableiten.
3. **RLS:** `ENABLE ROW LEVEL SECURITY` allein reicht nicht. Policies, Indizes, Views und privilegierte Funktionen separat testen.
4. **OAuth:** Tokens nicht blind zwischen Diensten weiterreichen. Audience, Scope und Delegation minimieren; für Token Exchange die jeweilige Providerimplementierung prüfen.
5. **Kommunikation:** „gesendet“ ist keine Garantie für exakt-einmalige Zustellung. Message-ID, deduplizierender Konsument und sichtbarer Send-Status sind erforderlich.
6. **Mobile Release:** EAS automatisiert Builds, aber Konten, Signierung, App-Store-Policies und aktuelle SDK-Anforderungen bleiben externe Gates.
7. **Research:** URL-/DOI-Existenz ist kein Beleg, dass eine Quelle die Aussage stützt. Claim-to-source-Checks und Unknown/Unverified-Felder sind Pflicht.
8. **AI-Evaluation:** öffentliche Leaderboards und LLM-as-a-Judge sind Hinweise, keine alleinige Produktionsfreigabe. Private, aufgabenspezifische Tests ergänzen.
9. **Dokumente:** Round-trip-Parsing kann Layout, Formeln und Metadaten verändern. Struktur- und Render-Diff vor Auslieferung.
10. **Games:** LLM-Inferenz gehört nicht in den latenzkritischen Render-/Physik-Thread; Kernlogik bleibt regelbasiert.

### Verwendete technische Quellen

- GitHub Actions Environments: <https://docs.github.com/actions/deployment/targeting-different-environments/using-environments-for-deployment>
- Stripe Idempotent Requests: <https://docs.stripe.com/api/idempotent_requests>
- PostgreSQL Row Security: <https://www.postgresql.org/docs/current/ddl-rowsecurity.html>
- Supabase RLS: <https://supabase.com/docs/guides/database/postgres/row-level-security>
- OAuth 2.0 Token Exchange, RFC 8693: <https://datatracker.ietf.org/doc/html/rfc8693>
- Expo EAS Submit: <https://docs.expo.dev/submit/ios/>
- Confluent Delivery Semantics: <https://docs.confluent.io/kafka/design/delivery-semantics.html>

## 8. Priorisierte Anpassung für dieses Bündelungsprojekt

### P0 — vor weiterer Autonomie
1. Index und alle READMEs aus Dateibestand generieren, nicht aus handgepflegten Zahlen.
2. `osint-self-audit` kanonisieren und personenbezogene Case-Files strikt lokal halten.
3. Die fünf Namenskonflikt-Gruppen und den Einzelnamen `v` entscheiden: kanonischer Pfad, Alias oder Merge.
4. Vendor-Router für `communication-apis`, `cloud-platforms`, `bioscience` und `design-tools` einführen.
5. Trigger-Tests gegen Nachbar-Skills schreiben; bei Mehrfachmatch fail-closed oder Nachfrage.

### P1 — danach
6. Einheitliches frontmatter ergänzen: `category`, `stack`, `risk`, `side_effects`, `requires_approval`, `version`, `last_verified`.
7. Handoff-Schema für AUTONOM definieren: `task_id`, `scope`, `input`, `artifacts`, `evidence`, `status`, `next_action`, `rollback`.
8. Governance-Policies als maschinenlesbare Dateien führen; Skills referenzieren sie nur.
9. Self-Improve nur über private Regressionstests, Review und Rollback promoten.
10. Memory mit Provenienz, Ablaufdatum und Confidence statt blindem Volltext-RAG.

### P2 — Qualitätsausbau
11. Für jede Domäne 3–10 repräsentative Skill-Evals erstellen; nicht 646 manuelle Benchmark-Skripte.
12. Drift-Job: README-Zahl, Frontmatter, Referenzen, Provider-Version und tatsächliche Dateien vergleichen.
13. Globalen Sync erst nach Bestandstest und Diff-Bericht durchführen.

## 9. Schluss

Die Sammlung ist **brauchbar, aber nicht autonom-fertig**. Der größte Wert liegt nicht in 646 isolierten Textdateien, sondern in einer kontrollierten Routing- und Prüfarchitektur. Der sichere Zielzustand ist:

```text
User-Task
  → Router mit negativen Trigger-Tests
  → Skill mit versioniertem Input/Output-Schema
  → Governance-Gate für Rechte, Kosten und Seiteneffekte
  → deterministische Prüfung durch Code/Parser/Test/Quelle
  → Memory mit Provenienz
  → Self-Improve erst nach Regression + Review
```

**Verifizierter Status:** 645 Skills · 29 Kategorien · 0 fehlende Textfelder · 540 PyYAML-SafeLoader-Parserfehler · 0 aktuelle README-Fehler · 0 Namenskonflikte (alle bereinigt) · 1 README ergänzt · 1 Duplikat gelöscht (security/osint-self-audit).
