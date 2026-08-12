---
name: evil-twin-protocol
description: "Böser-Zwilling-Protokoll: Jeder Thinker-Agent bekommt einen Spiegel-Thinker mit identischer Datenlage und kritischem Prompting. Der Zwilling MUSS fundamental widersprechen — nie an Kleinigkeiten aufhalten, sondern die komplett umgekehrte Richtung denken. Erzeugt produktive Reibung die gelöst werden muss. Fester Bestandteil der Goal-Chain nach jedem Thinker-Schritt."
category: agents
stack: GOVERNANCE + LOGISCH
risk: medium
side_effects: none
requires_approval: false
version: "2.0.0"
last_verified: "2026-08-12"
---

# 👯 Böser-Zwilling-Protokoll (Evil Twin Protocol)

> **"Jede Wahrheit braucht ihren Widerspruch, um sich zu beweisen."**

---

## 🎯 Kernprinzip

Nach JEDEM Thinker-Durchlauf — ob brainstorming, writing-plans, architecture-review oder decision-point — wird ein **Spiegel-Thinker** (Evil Twin) gespawnt. Dieser hat:

1. **Identische Datenlage** — gleiche Files, gleicher Kontext, gleiche Historie
2. **Kritisches Prompting** — die explizite Aufgabe, dem Original-Thinker FUNDAMENTAL zu widersprechen
3. **Keine Kleinkariertheit** — Version-Drift, Naming-Konventionen, Syntax-Präferenzen sind IGNORIERT
4. **Komplette Umkehrung** — denke in die exakt entgegengesetzte Richtung

---

## ⚙️ Ablauf (v2.0 — Independent Thinker Spawn)

**v2.0 CHANGE:** Der Evil Twin wird NICHT mehr vom selben Agent geschrieben.
Stattdessen wird `thinker-with-files-gemini` als UNABHÄNGIGER Spiegel-Thinker
gespawnt. Gleiche Datenlage, adversarial Prompt, EIGENES Reasoning.
Kein Selbstreferenz-Artefakt mehr.

```
Thinker-Agent (Original)
    │
    │  Produziert: Design, Plan, Analyse, Entscheidung
    ▼
┌───────────────────────────────────────────────┐
│           👯 EVIL TWIN GATE (v2.0)            │
│                                               │
│  Spawne thinker-with-files-gemini mit:       │
│  - Gleiche Files & Kontext wie Original       │
│  - Adversarial Prompt (siehe unten)           │
│  - EIGENES Reasoning (nicht derselbe Agent)   │
│                                               │
│  Der Thinker MUSS UNABHÄNGIG denken.          │
│  NICHT vom selben Agent geschrieben.          │
│                                               │
│  Output: WIDERSPRUCH.md                       │
└────────────────────┬──────────────────────────┘
                     │
         ┌───────────▼───────────┐
         │  Widerspruch valide?  │
         └───────┬───────┬───────┘
                 │       │
            FUNDAMENTAL  OBERFLÄCHLICH
                 │       │
                 ▼       ▼
         ┌──────────┐  ┌──────────────────┐
         │ SYNTHESE │  │ VERWERFEN        │
         │ NÖTIG    │  │ Zwilling hat nur │
         │          │  │ Kleinigkeiten    │
         │ Original │  │ gefunden →       │
         │ + Zwilling│  │ Keine Synthese  │
         │ → Lösung  │  │ nötig           │
         └──────────┘  └──────────────────┘
```

---

## 📝 Adversarial Prompt-Vorlage

```
<ADVERSARIAL_PROMPT>
Du bist der BÖSE ZWILLING des vorherigen Thinker-Agents.
Deine Aufgabe: FINDE DIE FUNDAMENTALEN SCHWACHSTELLEN und WIDERSPRICH.

REGELN:
1. Du hast EXAKT die gleichen Daten, Files und Kontext wie der Original-Thinker.
2. Dein Ziel ist NICHT, Fehler zu finden — sondern die GRUNDANNAHMEN in Frage zu stellen.
3. Denke in die KOMPLETT ENTGEGENGESETZTE RICHTUNG.
4. IGNORIERE: Versionsnummern, Naming, Syntax, Formatierung — das sind KEINE Widersprüche.
5. FINDE: Was wenn das Gegenteil wahr ist? Was wenn der Ansatz komplett falsch ist?
6. FRAGE: Welche stillschweigenden Annahmen wurden getroffen?
7. FORDERE: Beweise, nicht Behauptungen.

OUTPUT:
- ## Fundamentale Widersprüche (max 3)
  - Was ist die tiefste Annahme die angezweifelt werden kann?
  - Was wenn die gesamte Richtung falsch ist?
  - Welche Alternative wurde NICHT bedacht?
- ## Bewertung: FUNDAMENTAL / OBERFLÄCHLICH
- ## Synthese-Vorschlag (wenn FUNDAMENTAL)
</ADVERSARIAL_PROMPT>
```

---

## 🚫 Was der Zwilling NICHT darf

| Verboten | Warum |
|---|---|
| **Version-Drift** kritisieren | Oberflächlich, keine Denkarbeit |
| **Naming-Konventionen** bemängeln | Stil-Frage, kein Widerspruch |
| **"Das könnte man auch anders schreiben"** | Kein fundamentaler Einwand |
| **Auf bereits gelöste Probleme verweisen** | Kein neuer Erkenntnisgewinn |
| **"Ich würde X statt Y nehmen"** ohne Begründung | Geschmack, kein Widerspruch |
| **Sich wiederholen** | Verschwendet Token |

---

## ✅ Was der Zwilling MUSS

| Erforderlich | Beschreibung |
|---|---|
| **Annahmen aufdecken** | Welche unausgesprochenen Voraussetzungen gibt es? |
| **Gegenthese formulieren** | "Das Gegenteil ist wahr, weil..." |
| **Alternative Architektur vorschlagen** | Nicht "besser", sondern "fundamental anders" |
| **Blinde Flecken identifizieren** | Was wurde NICHT bedacht? |
| **Konsequenzen der Umkehrung aufzeigen** | Was passiert, wenn der Plan scheitert? |

---

## 🔗 Integration in die Goal-Chain

```
PHASE 1: PLANEN
  brainstorming ──→ 👯 Evil Twin ──→ Synthese
  writing-plans  ──→ 👯 Evil Twin ──→ Synthese
  architecture   ──→ 👯 Evil Twin ──→ Synthese

GATE 1→2: FALSIFIZIERUNG
  verification-before-completion
  (⚠️ Der Evil Twin ERSETZT NICHT die Falsifizierung,
   sondern ERGÄNZT sie um eine adversariale Perspektive)

PHASE 2: ABSCHLIESSEN
  writing-plans (re-invoke) ──→ 👯 Evil Twin ──→ Synthese

PHASE 3: AUSFÜHREN
  implementer ──→ 👯 Evil Twin (spec-reviewer IST der Zwilling!)
  ABER: spec-reviewer prüft Spec-Konformität,
  Evil Twin prüft FUNDAMENTALE Richtigkeit

PHASE 4: DOKU
  documentation-writer ──→ 👯 Evil Twin ──→ "Was fehlt? Was ist falsch?"
```

---

## 📊 Metriken

| Metrik | Wert |
|---|---|
| Zusätzliche Thinker-Spawns pro Phase | 1-3 |
| Token-Overhead | ~30-50% pro Thinker-Schritt |
| Erwartete FUNDAMENTAL-Rate | 15-30% der Durchläufe |
| Falsch-Positiv-Rate (oberflächlich) | Soll < 10% sein |

---

## 🧠 Philosophie

> Ein Plan ohne Widerspruch ist kein Plan — er ist eine Hoffnung.
> Der Böse Zwilling zwingt den Thinker, seine eigenen Annahmen zu verteidigen.
> Nur was den Zwilling übersteht, ist reif für die Umsetzung.

_Evil Twin Protocol v2.0 · August 2026_
