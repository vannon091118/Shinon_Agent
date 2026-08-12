# SyxCraft Current State Analysis

> **Analyse des bestehenden SyxCraft Repositories** (`vannon091118/SyxCraft`)
> **Stand:** 2026-07-14
> **Branch:** main (V70)

---

## Repository Struktur

```
SyxCraft/
├── pom.xml                              # Maven Build (Java 21, Game JAR als provided)
├── package.json                         # Node Validator (SyxCode Framework)
├── syxcode.config.json                  # Validator Config
├── README.md                            # Projekt-Doku (WoW Overhaul: Allianz/Horde)
├── doku/PROJECT_PLAN.md                 # Phasen-Plan (Phase 2 aktiv)
├── V70/
│   ├── data/init/
│   │   ├── race/
│   │   │   ├── HUMAN.txt                # Allianz — Standard Mensch
│   │   │   ├── ORC.txt                  # Horde — Melee/Mining Fokus
│   │   │   ├── UNDEAD.txt               # Horde — Immortal, Maintenance, Climate Neutral
│   │   │   └── NIGHT_ELF.txt            # Allianz — Learning/Stealth, Cold Climate
│   │   ├── tech/
│   │   │   ├── AGRICULTURE.txt          # Unlocks: VEGETABLE_FARM, GRAIN_FARM
│   │   │   ├── BASIC_MINING.txt         # Unlocks: ROOM_MINE (Req für ALLIANCE_COMMAND)
│   │   │   ├── PASTURE.txt              # Req: AGRICULTURE → LIVESTOCK_PEN
│   │   │   ├── TAILORING.txt            # Unlocks: TAILOR
│   │   │   └── ALLIANCE_COMMAND.txt     # Alliance-spezifisch → ROOM_ALLIANCE_HQ
│   │   ├── resource/                    # 8 Ressourcen (IRON, LEATHER, MEAT, SILVER, STEEL, STONE, VEGETABLES, WOOD)
│   │   ├── room/                        # WAREHOUSE.txt
│   │   ├── items/ plants/ animals/ diplomacy/ factions/ weather/ world/  (weitere Ordner)
│   │   └── res/                         # Assets (Sprites, Maps)
├── src/main/java/com/syxcraft/
│   └── AllianceLogic.java               # Placeholder Java Klasse
├── tools/core/
│   ├── validator.js                     # SyxCode Validator
│   └── signatures_updater.js
└── .codex/                              # Codex Config
```

---

## Bestehende Races (V70/data/init/race/)

| Race | Fraktion | Key Features |
|------|----------|--------------|
| **HUMAN** | Allianz | `ADULT_AT_DAY: 80`, `BOOST: CIVIC_IMMIGRATION>MUL: 1.5`, `ROOM_UNIVERSITY*>MUL: 1.5`, `PREFERRED.FOOD: [BREAD, MEAT, VEGETABLES]` |
| **ORC** | Horde | `ADULT_AT_DAY: 60`, `BATTLE.MELEE: 1.5`, `ENVIRONMENT.HEAT_RESISTANCE: 1.2`, `WORK.MINING: 1.2`, `PREFERRED.FOOD: [MEAT]` |
| **UNDEAD** | Horde | `LIFE_IMMORTAL: true`, `ADULT_AT_DAY: 20`, `ENVIRONMENT.*_RESISTANCE: 1.0`, `WORK.MAINTENANCE: 1.5`, `PREFERRED.FOOD: [MEAT]`, `OTHER_RACES: {HUMAN: 0.5, ORC: 0.9}` |
| **NIGHT_ELF** | Allianz | `ADULT_AT_DAY: 120`, `ACCESS.LEARNING: 1.3`, `BATTLE.RANGED: 1.2`, `ENVIRONMENT.COLD_RESISTANCE: 1.2`, `SERVICE.STEALTH: 1.3`, `PREFERRED.FOOD: [FRUIT, MEAT]` |

**Alle Races haben:** `_ignoreVanilla: true`, `PLAYABLE: true`, eigene `FILES` (Bio, Sprite, Icon, Home Map).

---

## Bestehende Techs (V70/data/init/tech/)

| Tech | Category | Cost | Requires | Unlocks |
|------|----------|------|----------|---------|
| `AGRICULTURE` | Civic | 100 | - | `VEGETABLE_FARM`, `GRAIN_FARM` |
| `BASIC_MINING` | Civic | 30 | - | `ROOM_MINE` |
| `PASTURE` | Civic | 150 | `AGRICULTURE` | `LIVESTOCK_PEN` |
| `TAILORING` | Civic | 120 | - | `TAILOR` |
| `ALLIANCE_COMMAND` | Civic | 50 | `BASIC_MINING` (Level 1) | `ROOM_ALLIANCE_HQ` (Faction-spezifisch) |

**Pattern:** `_ignoreVanilla: true`, `TECHS: { TECH_NAME: { COSTS, REQUIRES, UNLOCKS_FACTION/BUILDING } }`.

---

## Ressourcen (V70/data/init/resource/)

| Resource | Category | Key Fields |
|----------|----------|------------|
| `MEAT.txt` | edible | `EDIBLE: true`, `VALUE: 18`, `WEIGHT: 1.0`, `STACK_SIZE: 60` |
| `IRON`, `STEEL`, `SILVER`, `STONE` | minable/supply | `EDIBLE: false`, `TRADEABLE: true` |
| `LEATHER`, `WOOD`, `VEGETABLES` | supply/growable | `STACK_SIZE: 60-100` |

**Fehlt für Undead:** `CAPTIVE_HUMAN` (supply), `BONE` (supply), `ESSENCE` (supply).

---

## Rooms (V70/data/init/room/)

Nur `WAREHOUSE.txt` definiert. **Fehlen:** `HUMAN_PENS`, `NECROPOLIS`, `SLAVE_PEN` (Orc), `ALLIANCE_HQ`.

---

## Java Code (src/main/java/com/syxcraft/)

```java
// AllianceLogic.java — Placeholder
package com.syxcraft;

public class AllianceLogic {
    // Placeholder for Alliance-specific logic
}
```

**Keine Script Implementation** — noch kein `SCRIPT` Interface, kein `AbstractModSdkScript`.

---

## Build System

### Maven (pom.xml)
- Java 21
- Game JAR als `provided` Dependency (lokal via `maven-install-plugin`)
- `maven-shade-plugin` für Fat JAR (excludes Game Classes)
- `maven-source-plugin` für Source JAR (Workshop)
- `maven-resources-plugin` kopiert `mod-files/` nach `target/out/<artifactId>/V<major>/`

### Node (package.json)
```json
{
  "scripts": {
    "test": "node tools/core/validator.js",
    "sync:version": "node tools/core/validator.js --sync-version",
    "signatures:update": "node tools/core/signatures_updater.js"
  }
}
```
**SyxCode Validator** prüft: Data File Syntax, Hashes, Version Sync, Governance.

---

## Gaps für Undead Overhaul

| Bereich | Status | Was fehlt |
|---------|--------|-----------|
| **Race UNDEAD** | ✅ Definiert | Aber: `SLEEPS`, `CORPSE_DECAY`, `RESOURCE` (BONE/ESSENCE), `BOOST` Details |
| **Resource CAPTIVE_HUMAN** | ❌ Fehlt | Supply-Type, `RACES: [UNDEAD]`, Morale/Health Effects |
| **Resource BONE/ESSENCE** | ❌ Fehlt | Undead-spezifische Drops/Crafting |
| **Room HUMAN_PENS** | ❌ Fehlt | Consumes CAPTIVE_HUMAN, Produces CAPTIVE_HUMAN (Growth) |
| **Room NECROPOLIS** | ❌ Fehlt | Conversion: CAPTIVE_HUMAN → UNDEAD Citizen |
| **Room SLAVE_PEN** | ❌ Fehlt | Orc Room: Produces CAPTIVE_HUMAN from Raids |
| **Tech NECROMANCY_HUMAN_FARM** | ❌ Fehlt | Early Tech → Unlocks World Building + Rooms |
| **Tech ORC_SLAVERY** | ❌ Fehlt | Orc Tech → Unlocks Slave Raids/Trade |
| **World Building WORLD_HUMAN_FARM** | ❌ Fehlt | Worldmap Building für Region → Passive Captive Gen |
| **Events** | ❌ Fehlt | Conversion, Farm Establish, Orc Raid, Trade, Policy |
| **Script System** | ❌ Fehlt | `UndeadScript.java`, State Manager, Farm Logic, Trade Logic |
| **Mod SDK Integration** | ❓ Unklar | `sos-mod-sdk` Dependency verfügbar? |
| **Validator Schemas** | ❌ Fehlt | Für neue File Types (custom room, world building, event) |

---

## Nächste Schritte (Empfohlen)

1. **Validator Schemas erweitern** für neue File Types
2. **Data Files erstellen** (alle `.txt` aus `data-examples/`)
3. **Maven Modul für Script** aufsetzen (`UndeadScript.java` + Mod SDK Profile)
4. **Test-Mod bauen** → In Spiel laden → UNDEAD Race wählen → Farm bauen → Conversion testen
5. **Balance iterieren** → Numbers anpassen
6. **Workshop Upload** vorbereiten