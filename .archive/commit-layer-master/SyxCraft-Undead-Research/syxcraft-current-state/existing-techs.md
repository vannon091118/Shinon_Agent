# SyxCraft Current State — Existing Techs (V70)

> **Source:** `vannon091118/SyxCraft` Repository, `V70/data/init/tech/`
> **Stand:** 2026-07-14

---

## AGRICULTURE.txt

```txt
_ignoreVanilla: true,
TECHS: {
  AGRICULTURE: {
    COSTS: { CIVIC_KNOWLEDGE: 100 },
    UNLOCKS_BUILDING: [ VEGETABLE_FARM, GRAIN_FARM ],
  },
}
```

---

## BASIC_MINING.txt

```txt
_ignoreVanilla: true,
TECHS: {
  BASIC_MINING: {
    COSTS: { CIVIC_KNOWLEDGE: 30 },
    UNLOCKS_FACTION: [ ROOM_MINE ],
  },
}
```

---

## PASTURE.txt

```txt
_ignoreVanilla: true,
TECHS: {
  PASTURE: {
    COSTS: { CIVIC_KNOWLEDGE: 150 },
    REQUIRES: [ AGRICULTURE ],
    UNLOCKS_BUILDING: [ LIVESTOCK_PEN ],
  },
}
```

---

## TAILORING.txt

```txt
_ignoreVanilla: true,
TECHS: {
  TAILORING: {
    COSTS: { CIVIC_KNOWLEDGE: 120 },
    UNLOCKS_BUILDING: [ TAILOR ],
  },
}
```

---

## ALLIANCE_COMMAND.txt

```txt
_ignoreVanilla: true,
TECHS: {
  ALLIANCE_COMMAND: {
    COSTS: { CIVIC_KNOWLEDGE: 50 },
    REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
    UNLOCKS_FACTION: [ ROOM_ALLIANCE_HQ ],
  },
}
```

---

## Tech Comparison Matrix

| Tech | Category | Cost | Requires | Unlocks |
|------|----------|------|----------|---------|
| `AGRICULTURE` | Civic | 100 CIVIC | - | VEGETABLE_FARM, GRAIN_FARM |
| `BASIC_MINING` | Civic | 30 CIVIC | - | ROOM_MINE (Faction) |
| `PASTURE` | Civic | 150 CIVIC | AGRICULTURE | LIVESTOCK_PEN |
| `TAILORING` | Civic | 120 CIVIC | - | TAILOR |
| `ALLIANCE_COMMAND` | Civic | 50 CIVIC | BASIC_MINING L1 | ROOM_ALLIANCE_HQ (Faction) |

---

## Pattern Analysis

### Cost Scaling
- **Early Game:** 30-50 Knowledge (BASIC_MINING, ALLIANCE_COMMAND)
- **Mid Game:** 100-150 Knowledge (AGRICULTURE, TAILORING, PASTURE)
- **Late Game:** 200+ Knowledge (nicht in Current State)

### Requirement Types
1. **`REQUIRES_TECH_LEVEL`** — Andere Tech auf bestimmten Level (`{ BASIC_MINING: 1 }`)
2. **`REQUIRES`** — Game State Conditions (`{ GREATER: { POPULATION: 250 } }`)
3. **`REQUIRES` Array** — Andere Techs als Hard Requirement (`[ AGRICULTURE ]`)

### Unlock Types
| Type | Beispiel | Ziel |
|------|----------|------|
| `UNLOCKS_FACTION` | `[ ROOM_MINE ]` | Capital Room für Player Faction |
| `UNLOCKS_BUILDING` | `[ VEGETABLE_FARM ]` | Weltkarten-Gebäude (Region) |
| `UNLOCKS_EVENT` | `[ EVENT_NAME ]` | Event verfügbar machen |
| `BOOST` | `{ STAT>OP: VALUE }` | Permanenter Stat Bonus |

---

## Undead Tech Tree — Required Additions

| Tech ID | Category | Cost | Requires | Unlocks | Purpose |
|---------|----------|------|----------|---------|---------|
| `NECROMANCY_HUMAN_FARM` | Civic | 200 | BASIC_MINING L1 | ROOM_HUMAN_PENS, ROOM_NECROPOLIS, WORLD_HUMAN_FARM, Events | Core Mechanic Enabler |
| `ORC_SLAVERY` | Military | 150 | BASIC_MINING L1 | ROOM_SLAVE_PEN, Events | Orc Trade Enabler |
| `UNDEAD_NECROPOLIS_MASTERY` | Civic/Science | 500+300 | NECROMANCY_HUMAN_FARM | ROOM_NECROPOLIS_UPGRADES, Boosts | Late Game Scaling |
| `DARK_RITUALS` | Religious | 200 | NECROMANCY_HUMAN_FARM | MASS_CONVERSION, ESSENCE_HARVEST | Magic/Utility |
| `UNDEAD_HORDE_WARFARE` | Military | 300 | ORC_SLAVERY | ROOM_HORDE_BARRACKS, Boosts | Horde Synergy |

---

## Knowledge Types für Undead

| Knowledge Type | Source | Undead Relevanz |
|----------------|--------|-----------------|
| `CIVIC_KNOWLEDGE` | Libraries, Universities | Haupt-Tech (Necromancy, Farm) |
| `MILITARY_KNOWLEDGE` | Barracks, Battles | Orc Slavery, Horde Warfare |
| `SCIENTIFIC_KNOWLEDGE` | Laboratories | Necropolis Mastery |
| `RELIGIOUS_KNOWLEDGE` | Temples, Rituals | Dark Rituals |
| `ECONOMIC_KNOWLEDGE` | Markets, Trade | Nicht primär |

---

## Integration in SyxCraft

### Option A: Neue Tech-Datei `UNDEAD_NECROMANCY.txt`
```
V70/data/init/tech/UNDEAD_NECROMANCY.txt
```

### Option B: In bestehende `CIVIC.txt` / `MILITARY.txt` integrieren
- Pro: Weniger Files
- Contra: Mischt Faction-spezifische Techs mit Vanilla

**Empfehlung:** **Option A** — Separate Files für Modularity & Validator.

---

## Validator Schema Update Required

Neue Tech-Types benötigen Schema:
```json
// tools/schemas/tech-undead.schema.json
{
  "type": "object",
  "properties": {
    "TECHS": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "UNLOCKS_WORLD_BUILDING": { "type": "array", "items": { "type": "string" } },
          "UNLOCKS_FACTION": { "type": "array", "items": { "type": "string" } },
          "UNLOCKS_EVENT": { "type": "array", "items": { "type": "string" } }
        }
      }
    }
  }
}
```