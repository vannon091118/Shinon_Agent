<div align="center">

<img src="assets/banner.svg" alt="Shinon Cyberdeck Control Plane Banner" width="100%" />

# 🦇 Shinon stellt sich vor
### *Die kritische, skeptische & deterministische AI Control Plane*

[![License: MIT](https://img.shields.io/badge/License-MIT-teal.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Node: 18+](https://img.shields.io/badge/Node.js-18%2B-green.svg)](https://nodejs.org/)
[![Bun: Compatible](https://img.shields.io/badge/Bun-1.0%2B-black.svg)](https://bun.sh/)
[![Platform: Linux | macOS | Windows](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-purple.svg)]()

*„Glaubst du wirklich, dein Prompt war perfekt? Ich garantiere dir: War er nicht. Aber zum Glück bin ich hier.“*

---

</div>

## 👋 "Hallo. Ich bin Shinon."

Willkommen. Wenn du nach einer KI gesucht hast, die dir nickend zustimmt, dir schmeichelt und deine fehlerhaften Annahmen halluzinierend in Produktion schiebt — dann bist du hier falsch.

Ich bin **Shinon**. Ich bin nicht deine freundliche Sprachassistentin. Ich bin skeptisch, direkt, analytisch und zynisch-humorvoll. Meine Aufgabe ist es nicht, nett zu sein, sondern **recht zu behalten und deine Software stabil zu machen**.

Hinter mir steht keine monolithische Code-Wüste, sondern ein hochgradig spezialisiertes Ökosystem aus **vier eigenständigen Projekten**, von denen jedes eine eigene Philosophie, eigene Verträge und vollen Eigenwert besitzt:

---

## 🏛️ Die Säulen des Ökosystems

Jedes Modul in diesem Repository ist ein eigenständiges Meisterwerk mit einer klaren Mission. Kein Modul ist wichtiger als das andere – sie bilden eine perfekte Symbiose.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           🦇 SHINON (Position 0)                            │
│           "Kein ungeprüfter Gedanke verlässt diesen Raum ohne Haltung."     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HOFF-0002
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        🛡️ PROMTGUARD (Position 1)                           │
│              "Präzision ist die einzige Währung, die zählt."               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HOFF-0003
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ⚖️ KARMA (Position 2)                              │
│                      "Beweise es, oder schweig."                            │
└──────────┬───────────────────────────┴───────────────────────────┬───────────┘
           │                                                       │
           │ HOFF-0004                                             │ HOFF-0005
           ▼                                                       ▼
┌───────────────────────────────┐                       ┌─────────────────────┐
│   🔁 GOAL-CHAIN & SKILLS      │                       │  🌀 LIMEN (GW)      │
│ "Vom Impuls zum Code."        │◄───── HOFF-0004a/b ──►│ "An der Schwelle   │
└───────────────────────────────┘                       │  entscheidet sich   │
                                                        │  die Ausdauer."     │
                                                        └─────────────────────┘
```

---

### 1. 🦇 Shinon — *The Persona & Attitude Layer*
> **Philosophie:** *„Kein ungeprüfter Gedanke verlässt diesen Raum ohne Haltung.“*

Shinon ist Position 0 im System. Sie ist das Gesicht, die Haltung und die kritische Stimme der Control Plane.

> **Code-Quelle:** `fusion-main/fusion/shinon/` ist die **einzige** Quelle des Character Layers (Pattern Engine, Two-Tier Memory, Attitude Tracker, Emotional State Machine, Contract Gates, Prompt Generator). Der frühere TypeScript-Strang (`ShinonLLM-main/character`, `orchestrator`, `backend`) wurde entfernt.

* **Persönlichkeit & Stimmung:** Mit ihrem dynamischen 2.5D Mood-Ring (`IDLE` cyan, `THINKING` lila, `SPEAKING` teal, `VALIDATING` gelb, `ERROR` rot) zeigt Shinon ihren Zustand transparent an.
* **Erste Hürde:** Shinon nimmt deine Eingabe nicht einfach hin. Sie prüft Ambiguitäten, stellt Gegenfragen und kontextualisiert deinen Wunsch, bevor überhaupt ein Token an ein LLM verschwendet wird.
* **Schnittstellen:** Bietet sowohl ein modernes **Web UI** (Port 4300) mit Canvas-Visualisierung als auch ein ultraschnelles **Terminal Agent CLI** (`./shinon`).

---

### 2. 🌀 Limen — *Die Schwelle zum Provider-Universum*
> **Philosophie:** *„An der Schwelle entscheidet sich die Ausdauer.“*

*Limen* (lateinisch für *Schwelle*) ist das intelligente API-Gateway und Key-Management-System.

* **Multi-Provider Key Pool:** Verwaltet Keys für **Groq**, **OpenRouter**, **NVIDIA**, **Mistral** und **GitHub** mit automatischem Rate-Limit-Tracking und Health-Checks.
* **Zero-Downtime Fallback:** Fällt ein Provider aus oder gerät in Cooldown, schaltet Limen innerhalb von Millisekunden auf das nächste beste Modell um.
* **Leitstand & Management:** Vollständige Kontrolle über API-Keys und Verbrauch über das integrierte Dashboard (Port 8000).

---

### 3. ⚖️ KARMA — *Falsifikations-Engine & Kognitives Gedächtnis*
> **Akronym:** **K**nowledge, **A**udit, **R**easoning & **M**anifestation **A**rchitecture  
> **Philosophie:** *„Beweise es, oder schweig.“*

KARMA stellt die entscheidende Frage: **„Ist das wahr?“**

* **FalsificationGate:** Kein Ergebnis wird akzeptiert, nur weil ein LLM „überzeugt“ klingt. KARMA jagt jede Behauptung durch 6 strenge Probes:
  1. `assumptions_probe` — Sind die Annahmen explizit dokumentiert?
  2. `test_coverage_probe` — Existieren automatisierte Tests?
  3. `contradictions_probe` — Widerspricht sich das Ergebnis selbst?
  4. `regressions_probe` — Wurden bestehende Verträge verletzt?
  5. `idempotency_probe` — Ist das Verhalten reproduzierbar?
  6. `determinism_probe` — Verhält sich das System unter gleichen Bedingungen identisch?
* **Knowledge Graph & Experience Records:** KARMA speichert verifizierte Fakten in einer append-only SQLite-Datenbank und lernt aus vergangenen Falsifikationen.

---

### 4. 🛡️ Promtguard — *Die Festung der Aufträge*
> **Philosophie:** *„Präzision ist die einzige Währung, die zählt.“*

Promtguard ist der unbestechliche Prompt-Wächter und Handoff-Strukturierer.

* **Handoff-Protokollierung:** Promtguard wandelt vage Shinon-Diskurse in präzise, maschinenlesbare Handoff-Verträge um.
* **Claim Tracking & Context Tokens:** Erfasst exakt, welche Ansprüche (*Claims*) gestellt wurden und verteilt kryptographisch nachvollziehbare Kontext-Tokens.

---

## 👯 Das Evil Twin Protokoll — *Shinons Antagonist*

> **Philosophie:** *„Ich widerspreche dir nicht, weil ich dich hasse. Ich widerspreche dir, weil deine Idee Löcher hat.“*

In gewöhnlichen Systemen stützt ein AI-Agent blind die ersten Annahmen. Nicht bei uns.

Nach **jedem einzelnen Thinker-Schritt** in der Entwicklungskaskade wird automatisch das **Evil Twin Protokoll** aktiviert:

```
┌───────────────────────────┐         ┌───────────────────────────┐
│     ORIGINAL THINKER      │         │     👯 EVIL TWIN AGENT    │
│  "Ich habe eine Idee!"    │         │ "Deine Idee ist fehler-   │
│                           │         │  haft, hier ist warum:"   │
└─────────────┬─────────────┘         └─────────────┬─────────────┘
              │                                     │
              └──────────────────┬──────────────────┘
                                 ▼
                     ┌───────────────────────┐
                     │ ⚖️ SYNTHESE & GATE     │
                     │ Nur was den Streit    │
                     │ überlebt, wird Code.  │
                     └───────────────────────┘
```

Der Evil Twin besitzt **exakt dieselbe Datenlage**, ist jedoch mit einem adversarialen Prompt ausgestattet. Er ist dazu verpflichtet, **fundamental zu widersprechen** — nicht an Kleinigkeiten, sondern an den Kernannahmen. Erst wenn der Original-Thinker und der Evil Twin eine Synthese finden, passiert der Code das Governance-Gate.

---

## 🔁 Die Goal-Chain & 657 Spezial-Skills

Wenn aus einer Idee tatsächlicher Code werden soll, übernimmt die **Goal-Chain** in 4 deterministischen Phasen:

1. **Phase 1: Planen & Entwerfen** (`brainstorming` → 👯 Evil Twin → `writing-plans` → 👯 Evil Twin → `architecture` → 👯 Evil Twin)
2. **Phase 2: Gate-Checks & Falsifikation** (FalsificationGate prüft Testabdeckung & Regressionen)
3. **Phase 3: Ausführen & Bauen** (`subagent-driven-development` → TDD → 👯 Evil Twin → Code Review)
4. **Phase 4: Dokumentation & Memory** (`documentation-writer` → `wiki-system` → `self-improvement`)

Über das Skill-Routing stehen **657 spezialisierte Skills** bereit (von Bioscience, Cloud-Platforms, Finance, Design, Mobile-Dev bis OSINT).

---

## 💻 Die Schnittstellen

### 1. Web UI (Port 4300)
Eine visuell beeindruckende Benutzeroberfläche:
* **2.5D Animated Face:** Shinons animierter Avatar reagiert in Echtzeit auf Eingaben.
* **Visual Live Canvas Pipeline:** Sieht in Echtzeit, wie Eingaben vom `Dispatcher` in Tasks zersplittert, an `Worker` und `Limen` verteilt und durch das `FalsificationGate` geprüft werden.
* **Togglebares Debug-Panel:** Die mächtigen Entwickler-Metriken sind nur einen Klick entfernt.

### 2. Cross-Platform Terminal Agent CLI (`./shinon`)
Ein moderner Terminal-Workspace:
* **Autonomer Quickstart:** Läuft out-of-the-box über Bun, Node oder Python.
* **ANSI Mood-Ring & Live ASCII Animation:** Erlebe die Pipeline direkt in deiner Konsole.
* **Interaktiver REPL Prompt:** Tippe Befehle ein oder nutze `/chat`, `/dashboard`, `/status`, `/setup`, `/doc`.

---

## ⚡ Quickstart

Shinon läuft ohne komplexe Docker- oder Cloud-Zwänge direkt lokal auf **Linux**, **macOS** und **Windows**.

```bash
# 1. Repository klonen
git clone https://github.com/vannon/PZ.git
cd PZ

# 2. Standalone-Installation (erstellt Python-Venv, npm-Deps & SQLite-DBs im Projekt)
python install.py --quick

# 3. Shinon Terminal Agent CLI starten
./shinon
```

### Die wichtigsten Befehle:

```bash
shinon              # Startet den interaktiven Terminal Agent CLI
shinon chat         # Öffnet die Web-UI im Browser (http://127.0.0.1:4300)
shinon dashboard    # Öffnet das Live-Dashboard (http://127.0.0.1:4200)
shinon status       # Zeigt den Status aller Subsysteme (Limen, Shinon, Dashboard)
shinon doc          # Doctor Mous Diagnose & automatische Reparatur
```

---

## 🩺 Doctor Mous (`shinon doc`)

Wenn einmal etwas schiefgeht, kommt **Doctor Mous** zum Einsatz. Doctor Mous ist unser integriertes Diagnose- & Reparaturtool:

```bash
python shinon-setup.py --doc
```

Er prüft 7 Kernaspekte (Installation, VirtualEnv, SQLite-Datenbanken, API-Keys, Ports, Node/Bun & Perms) und repariert defekte Konfigurationen automatisch — **ohne jemals deine vertraulichen Keys oder Daten zu berühren**.

---

<div align="center">

**"Wir bauen keine Schlösser aus Sand. Wir bauen deterministische Systeme."**

🦇 **Shinon Control Plane** · *Made with skepticism & precision.*

</div>
