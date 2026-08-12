# Vanilla Tech System — Songs of Syx V71

## Tech Datei-Struktur

```
data/assets/init/tech/
├── ADMIN.txt
├── AGRI.txt
├── ARCHITECTURE.txt
├── BATTLE.txt
├── CIVIC.txt
├── EMPIRE.txt
├── HUSB.txt
├── MINES.txt
├── REFINER.txt
├── SCIENCE.txt
└── WORKSHOP.txt
```

---

## Tech-Struktur (am Beispiel `CIVIC.txt`)

```txt
TREE: {
  0: [FOOD0, _____, MARK0, _____, REL00, REL22, STAG0, AREA0, NURS1, LAV00, _____, HOSP0, _____],
  1: [CANT0, INN00, MARK1, TAVER, REL11, REL33, STAG1, AREA1, NURS2, ASY00, LAV01, DOC00, _____],
  2: [FOOD1, _____, _____, TAVE1, _____, REL44, STAG2, AREA2, _____, REST0, _____, HOSP1, DOC01],
  3: [FOOD5, BAR00, PLEA0, _____, _____, _____, _____, _____, _____, _____, _____, HEALB, _____],
  4: [_____, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____],
},

COLOR: 0_148_255,
ICON: 32->_ICONS->27,
CATEGORY: 25,
TECHS: {
  NURS1: {
    COSTS: { CIVIC_KNOWLEDGE: 10 },
    UNLOCKS_FACTION: [ ROOM_NURSERY_NORMAL ],
    REQUIRES: { GREATER: { POPULATION: 250 } },
  },
  NURS2: {
    LEVEL_MAX: 4,
    LEVEL_COST_INC: 25,
    COSTS: { CIVIC_KNOWLEDGE: 25 },
    REQUIRES_TECH_LEVEL: { NURS1: 1 },
    BOOST: { ROOM_NURSERY_NORMAL>ADD: 1 },
  },
  STAG0: {
    COSTS: { CIVIC_KNOWLEDGE: 5 },
    UNLOCKS_FACTION: [ ROOM_STAGE_NORMAL ],
  },
  STAG1: {
    COSTS: { CIVIC_KNOWLEDGE: 40 },
    REQUIRES_TECH_LEVEL: { STAG0: 1 },
    UNLOCKS_FACTION: [ ROOM_STAGE_NORMAL_UPGRADE_1 ],
    REQUIRES: { GREATER: { POPULATION: 500 } },
  },
  // ...
  MARK0: {
    COSTS: { CIVIC_KNOWLEDGE: 10 },
    UNLOCKS_FACTION: [ ROOM_MARKET_NORMAL_UPGRADE_1 ],
  },
  TAVER: {
    COSTS: { CIVIC_KNOWLEDGE: 20 },
    REQUIRES_TECH_LEVEL: { MARK0: 1 },
    UNLOCKS_FACTION: [ ROOM_TAVERN_NORMAL ],
    REQUIRES: { GREATER: { POPULATION: 500 } },
  },
}
```

---

## Tech-Felder Referenz

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `TREE` | object | 2D Grid Layout (Zeilen 0-4, Spalten 0-12) für Tech-Tree UI |
| `COLOR` | string | RGB Farbe `R_G_B` für Tree Visualisierung |
| `ICON` | string | Sprite Referenz `SIZE->CATEGORY->INDEX` |
| `CATEGORY` | int | Tech-Kategorie ID (für UI Gruppierung) |
| `TECHS` | object | Alle Tech-Definitionen |

### Innerhalb von `TECHS: { TECH_NAME: { ... } }`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `COSTS` | object | `{ KNOWLEDGE_TYPE: AMOUNT }` — z.B. `CIVIC_KNOWLEDGE: 100` |
| `REQUIRES_TECH_LEVEL` | object | `{ OTHER_TECH: LEVEL }` — Vorrausetzung |
| `REQUIRES` | object | `{ GREATER: { STAT: VALUE }, LESS: {...}, EQUAL: {...} }` — Game State Conditions |
| `UNLOCKS_FACTION` | array | `[ ROOM_NAME, BUILDING_NAME ]` — Freischaltungen für Player Faction |
| `UNLOCKS_BUILDING` | array | Weltkarten-Gebäude (Regions) |
| `UNLOCKS_WORLD_BUILDING` | array | Weltkarten-Gebäude (Regions) — **Custom?** |
| `UNLOCKS_EVENT` | array | Events die verfügbar werden |
| `BOOST` | object | Permanente Boosts bei Research `{ STAT>OP: VALUE }` |
| `LEVEL_MAX` | int | Max Level für Level-Up Techs |
| `LEVEL_COST_INC` | int | Kosten-Steigerung pro Level |
| `DESCRIPTION` | string | Tooltip Text |

---

## Knowledge Types (Costs)

| Type | Beschreibung |
|------|--------------|
| `CIVIC_KNOWLEDGE` | Zivisches Wissen (Standard) |
| `MILITARY_KNOWLEDGE` | Militärisches Wissen |
| `ECONOMIC_KNOWLEDGE` | Wirtschaftliches Wissen |
| `SCIENTIFIC_KNOWLEDGE` | Wissenschaftliches Wissen |
| `RELIGIOUS_KNOWLEDGE` | Religiöses Wissen |

---

## SyxCraft Techs (V70) — Pattern

```txt
# ALLIANCE_COMMAND.txt
_ignoreVanilla: true,
TECHS: {
  ALLIANCE_COMMAND: {
    COSTS: { CIVIC_KNOWLEDGE: 50 },
    REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
    UNLOCKS_FACTION: [ ROOM_ALLIANCE_HQ ],
  },
}
```

```txt
# AGRICULTURE.txt
_ignoreVanilla: true,
TECHS: {
  AGRICULTURE: {
    COSTS: { CIVIC_KNOWLEDGE: 100 },
    UNLOCKS_BUILDING: [ VEGETABLE_FARM, GRAIN_FARM ],
  },
}
```

```txt
# PASTURE.txt
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

## Undead Techs — Design

### 1. `NECROMANCY_HUMAN_FARM` (Early-Mid Game)

```txt
TECHS: {
  NECROMANCY_HUMAN_FARM: {
    COSTS: { CIVIC_KNOWLEDGE: 200 },
    REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
    UNLOCKS_FACTION: [ ROOM_HUMAN_PENS, ROOM_NECROPOLIS ],
    UNLOCKS_WORLD_BUILDING: [ WORLD_HUMAN_FARM ],
    UNLOCKS_EVENT: [ FOUND_HUMAN_FARM, UNDEAD_CONVERSION ],
    BOOST: { UNDEAD_CAPTIVE_HUMAN_EFFICIENCY>ADD: 0.1 },
    DESCRIPTION: "Ermöglicht Menschenfarmen auf Weltkarte und Menschenställe/Nekropolen in Hauptstadt.",
  },
}
```

### 2. `ORC_SLAVERY` (Orc Tech Tree)

```txt
TECHS: {
  ORC_SLAVERY: {
    COSTS: { MILITARY_KNOWLEDGE: 150 },
    REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
    UNLOCKS_FACTION: [ ROOM_SLAVE_PEN ],
    UNLOCKS_EVENT: [ ORC_SLAVE_RAID, ORC_SELL_CAPTIVES ],
    BOOST: { ORC_SLAVE_RAID_EFFICIENCY>ADD: 0.2 },
    DESCRIPTION: "Ermöglicht Versklavung von Menschen bei Raids und Handel mit Untoten.",
  },
}
```

### 3. `UNDEAD_NECROPOLIS_MASTERY` (Late Game)

```txt
TECHS: {
  UNDEAD_NECROPOLIS_MASTERY: {
    COSTS: { CIVIC_KNOWLEDGE: 500, SCIENTIFIC_KNOWLEDGE: 300 },
    REQUIRES_TECH_LEVEL: { NECROMANCY_HUMAN_FARM: 1 },
    UNLOCKS_FACTION: [ ROOM_NECROPOLIS_UPGRADE_1, ROOM_NECROPOLIS_UPGRADE_2 ],
    BOOST: { 
      CONVERSION_EFFICIENCY>ADD: 0.25,
      CAPTIVE_HUMAN_CAPACITY>MUL: 2.0,
    },
    DESCRIPTION: "Verbessert Nekropolen: Schnellere Konvertierung, mehr Kapazität.",
  },
}
```

### 4. `DARK_RITUALS` (Magic/Religion)

```txt
TECHS: {
  DARK_RITUALS: {
    COSTS: { RELIGIOUS_KNOWLEDGE: 200 },
    REQUIRES_TECH_LEVEL: { NECROMANCY_HUMAN_FARM: 1 },
    UNLOCKS_EVENT: [ MASS_CONVERSION, ESSENCE_HARVEST ],
    BOOST: { 
      ESSENCE_PRODUCTION>MUL: 1.5,
      RITUAL_SPEED>ADD: 0.3,
    },
    DESCRIPTION: "Dunkle Rituale: Massenkonvertierung, Essenz-Ernte.",
  },
}
```

---

## Tech Tree Integration

### Kategorien für Undead Techs

| Tech | Kategorie | Knowledge Type | Tier |
|------|-----------|----------------|------|
| `NECROMANCY_HUMAN_FARM` | CIVIC | `CIVIC_KNOWLEDGE` | Early-Mid (Req BASIC_MINING) |
| `ORC_SLAVERY` | MILITARY | `MILITARY_KNOWLEDGE` | Early (Req BASIC_MINING) |
| `UNDEAD_NECROPOLIS_MASTERY` | CIVIC/SCIENCE | `CIVIC` + `SCIENTIFIC` | Late |
| `DARK_RITUALS` | RELIGION | `RELIGIOUS_KNOWLEDGE` | Mid-Late |

### UI Position (TREE Grid)

```
TREE: {
  0: [NECRO0, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____],
  1: [NECRO1, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____],
  2: [NECRO2, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____, _____],
}
```

---

## Offene Fragen Tech System

| Frage | Status |
|-------|--------|
| Unterstützt Engine `UNLOCKS_WORLD_BUILDING` oder nur `UNLOCKS_BUILDING`? | **Unbekannt** — Test nötig |
| Wie werden `UNLOCKS_EVENT` Events im UI angezeigt? | **Event-Panel** vermutlich |
| Kann `REQUIRES` auf Custom Stats/Boosts prüfen (z.B. `HAS_HUMAN_FARM>SET: 1`)? | **Wahrscheinlich** — Boost System |
| Gibt es `UNLOCKS_RACE` für Race-spezifische Techs? | **Nicht gesehen** — über `UNLOCKS_FACTION` Rooms steuern |
| Wie werden `LEVEL_MAX` Techs im Tree dargestellt? | **Level-Indikator** am Node |