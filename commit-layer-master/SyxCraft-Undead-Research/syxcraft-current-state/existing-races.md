# SyxCraft Current State — Existing Races

> **Source:** `vannon091118/SyxCraft` Repository, `V70/data/init/race/`
> **Stand:** 2026-07-14

---

## HUMAN.txt (Allianz)

```txt
_ignoreVanilla: true,
PLAYABLE: true,
FILES: {
    BIO_FILE: 'biographies/HUMAN.txt',
    SPRITE_FILE: 'sprites/races/HUMAN.png',
    ICON_BIG: 'races/Human_Icon.png',
    ICON_SMALL: 'races/Human_Icon.png',
    HOME: 'maps/home/HUMAN.map',
},
PROPERTIES: {
    HEIGHT: 6,
    WIDTH: 9,
    ADULT_AT_DAY: 80,
},
STATS: {
    ACCESS: { LEARNING: 1.2 },
    APPEARANCE: { HAIR_COLORS: [BROWN, BLONDE, BLACK], SKIN_COLORS: [FAIR, TAN] },
    BATTLE: { MELEE: 1.0, RANGED: 1.1, MORALE: 1.0 },
    DISEASE: { RESISTANCE: 1.0 },
    EDUCATION: { INTELLIGENCE: 1.1 },
    ENVIRONMENT: { COLD_RESISTANCE: 0.8, HEAT_RESISTANCE: 0.7 },
    FOOD: { HUNGER_RATE: 1.0 },
    SERVICE: { SPEED: 1.1 },
    WORK: { SPEED: 1.0 },
    BURIAL: { PREFERENCE: GRAVE },
    EQUIP: { CLOTHES: 1.0, TOOLS: 1.0 },
    RELIGION: { AFFINITY: 1.1 },
},
PREFERENCES: {
    FOOD: [BREAD, MEAT, VEGETABLES],
    DRINK: [WATER, BEER],
    CLIMATE: { HOT: 0.7, TEMPERATE: 1.0, COLD: 0.6 },
    OTHER_RACES: { ORC: 0.8, UNDEAD: 0.5, NIGHT_ELF: 1.0 },
    STRUCTURE: { BRICK: 1.1, STONE: 1.2, WOOD: 1.0 },
    WORK: { FARMING: 1.2, CRAFTING: 1.1, MINING: 0.8 },
    ROAD: { STONE: 1.1 },
},
BOOST: {
    SERVICE_LEARNING: 1.2,
    SERVICE_SPEED: 1.1,
},
```

---

## ORC.txt (Horde)

```txt
_ignoreVanilla: true,
PLAYABLE: true,
FILES: {
    BIO_FILE: 'biographies/ORC.txt',
    SPRITE_FILE: 'sprites/races/ORC.png',
    ICON_BIG: 'races/ORC_icon.png',
    ICON_SMALL: 'races/ORC_icon.png',
    HOME: 'maps/home/ORC.map',
},
PROPERTIES: {
    HEIGHT: 7,
    WIDTH: 10,
    ADULT_AT_DAY: 60,
},
STATS: {
    BATTLE: { MELEE: 1.5, MORALE: 1.2 },
    ENVIRONMENT: { HEAT_RESISTANCE: 1.2, COLD_RESISTANCE: 0.5 },
    WORK: { MINING: 1.2 },
},
PREFERENCES: {
    FOOD: [MEAT],
    CLIMATE: { HOT: 1.0, WARM: 0.8 },
    OTHER_RACES: { HUMAN: 0.8, UNDEAD: 0.9 },
},
```

---

## UNDEAD.txt (Horde) — **Bestehend**

```txt
_ignoreVanilla: true,
PLAYABLE: true,
FILES: {
    BIO_FILE: 'biographies/UNDEAD.txt',
    SPRITE_FILE: 'sprites/races/UNDEAD.png',
    ICON_BIG: 'races/UNDEAD_icon.png',
    ICON_SMALL: 'races/UNDEAD_icon.png',
    HOME: 'maps/home/UNDEAD.map',
},
PROPERTIES: {
    HEIGHT: 6,
    WIDTH: 9,
    ADULT_AT_DAY: 20,
    CORPSE_DECAY: false,
    SLEEPS: false,
    SLAVE_PRICE: 0,
    SLAVE_PRICE_RECOVERY: 0,
    RAID_MERCINARY: 0.0,
},
STATS: {
    LIFE_IMMORTAL: true,
    ENVIRONMENT: { HEAT_RESISTANCE: 1.0, COLD_RESISTANCE: 1.0, TEMPERATE_RESISTANCE: 1.0 },
    WORK: { MAINTENANCE: 1.5, SPEED: 0.9 },
    FOOD: { HUNGER_RATE: 0.0 },
    SERVICE: { SPEED: 0.8 },
    ACCESS_NOISE: { CITIZEN: 0.0 },
    ACCESS_SPACE: { CITIZEN: 0.3 },
},
PREFERENCES: {
    FOOD: [],
    DRINK: [],
    CLIMATE: { COLD: 1.0, HOT: 1.0, TEMPERATE: 1.0 },
    OTHER_RACES: { HUMAN: 0.3, ORC: 0.7, NIGHT_ELF: 0.2 },
    WORK: {
        _ASYLUM: -1.0, _EMBASSY: -0.5, _INN: -1.0, _POLICE: 0.0,
        ADMIN_NORMAL: 0.5, BARBER_NORMAL: -1.0, GRAVEYARD_NORMAL: 2.0,
        LABORATORY_NORMAL: 1.5, LIBRARY_NORMAL: 0.5, MARKET_NORMAL: 0.0,
        MINE_GEM: 1.5, PHYSICIAN_NORMAL: -1.0, REFINER_COALER: 1.2,
        REFINER_SMELTER: 1.2, REFINER_WEAVER: -0.5, SCHOOL_NORMAL: -1.0,
        SPEAKER_NORMAL: 0.0, STAGE_NORMAL: -1.0, TAVERN_NORMAL: -1.0,
        TOMB_NORMAL: 2.0, UNIVERSITY_NORMAL: 1.0, WORKSHOP_BOWYER: 1.0,
        WORKSHOP_CARPENTER: 1.0, WORKSHOP_JEWELRY: 0.5, WORKSHOP_MECHANIC: 1.5,
        WORKSHOP_SMITHY: 1.5, WORKSHOP_TAILOR: -0.5,
    },
    STRUCTURE: { MOUNTAIN: 1.0, STONE: 1.2, GRAND: 1.0, WOOD: 0.3, OUTDOORS: 0.2 },
    POOL: { POOL_STONE: 1.0 },
    ROAD: { STONE1: 0.8, STONE2: 1.0 },
    BUILDING_OVERRIDE: { CIVIC_L_STANDS: 0.5 },
},
POPULATION: {
    MAX: 1.0,
    GROWTH: 0.0,
    CLIMATE: { COLD: 1.0, TEMPERATE: 1.0, HOT: 1.0 },
    TERRAIN: { MOUNTAIN: 1.5, FOREST: 0.2, NONE: 1.0 },
},
TRAITS: { UNDEAD: 1.0, IMMORTAL: 1.0, TIRELESS: 1.0 },
RESOURCE: { BONE: 50, ESSENCE: 20 },

BOOST: {
    PHYSICS_RESISTANCE_COLD>ADD: 0.0,
    PHYSICS_RESISTANCE_HOT>ADD: 0.0,
    PHYSICS_DEATH_AGE>MUL: 0.0,
    BATTLE_BLUNT_ATTACK>ADD: 5,
    CIVIC_IMMIGRATION>MUL: 0.0,
    ROOM_GRAVEYARD*>MUL: 2.0,
    ROOM_TOMB*>MUL: 2.0,
    ROOM_LABORATORY*>MUL: 1.5,
    ROOM_MINE*>MUL: 1.3,
    ROOM_REFINER*>MUL: 1.2,
    WORK_MAINTENANCE>MUL: 1.5,
    BEHAVIOUR_SANITY>MUL: 2.0,
    BEHAVIOUR_LAWFULNESS>MUL: 1.5,
},

EQUIPMENT_NOT_ENABLED: [ CLOTHES, ARMOR, WEAPON_RANGED, WEAPON_MELEE, TOOL ],
EQUIPMENT_ENABLED: [ TRINKET, AMULET, RING ],
```

---

## NIGHT_ELF.txt (Allianz)

```txt
_ignoreVanilla: true,
PLAYABLE: true,
FILES: {
    BIO_FILE: 'biographies/NIGHT_ELF.txt',
    SPRITE_FILE: 'sprites/races/NIGHT_ELF.png',
    ICON_BIG: 'races/NIGHT_ELF_icon.png',
    ICON_SMALL: 'races/NIGHT_ELF_icon.png',
    HOME: 'maps/home/NIGHT_ELF.map',
},
PROPERTIES: {
    HEIGHT: 7,
    WIDTH: 10,
    ADULT_AT_DAY: 120,
},
STATS: {
    ACCESS: { LEARNING: 1.3 },
    BATTLE: { MELEE: 0.9, RANGED: 1.2, MORALE: 0.8 },
    DISEASE: { RESISTANCE: 1.2 },
    ENVIRONMENT: { COLD_RESISTANCE: 1.2, HEAT_RESISTANCE: 0.5 },
    FOOD: { HUNGER_RATE: 0.8 },
    SERVICE: { SPEED: 1.2, STEALTH: 1.3 },
},
PREFERENCES: {
    FOOD: [FRUIT, MEAT],
    DRINK: [WATER],
    CLIMATE: { COLD: 1.0, TEMPERATE: 0.8 },
    OTHER_RACES: { HUMAN: 0.6, ORC: 0.4, UNDEAD: 0.3 },
},
BOOST: {
    SERVICE_LEARNING: 1.1,
    SERVICE_STEALTH: 1.3,
},
```

---

## Race Comparison Matrix

| Feature | HUMAN | ORC | UNDEAD | NIGHT_ELF |
|---------|-------|-----|--------|-----------|
| **Faction** | Allianz | Horde | Horde | Allianz |
| `ADULT_AT_DAY` | 80 | 60 | **20** | 120 |
| `LIFE_IMMORTAL` | false | false | **true** | false |
| `SLEEPS` | true | true | **false** | true |
| `FOOD` | [BREAD, MEAT, VEG] | [MEAT] | **[]** | [FRUIT, MEAT] |
| `GROWTH` | 0.075 | ~0.05 | **0.0** | ~0.03 |
| `CLIMATE` | Temperate pref | Hot pref | **All 1.0** | Cold pref |
| `WORK_SPEED` | 1.0 | ~1.0 | **0.9** | ~1.0 |
| `MAINTENANCE` | 1.0 | ~1.0 | **1.5** | ~1.0 |
| `IMMIGRATION` | +50% | ~0% | **0%** | ~0% |
| `OTHER_RACES: UNDEAD` | 0.5 | 0.9 | N/A | 0.3 |
| `OTHER_RACES: HUMAN` | N/A | 0.8 | **0.3** | 0.6 |
| `RESOURCE DROP` | MEAT, LEATHER | MEAT, LEATHER | **BONE, ESSENCE** | MEAT, LEATHER |

---

## Gaps für Undead Overhaul (vs. Current SyxCraft UNDEAD)

| Aspekt | Current SyxCraft | Required for Overhaul | Status |
|--------|------------------|----------------------|--------|
| **Conversion Mechanic** | ❌ Fehlt | Human → Undead via Event | **NEU** |
| **CAPTIVE_HUMAN Resource** | ❌ Fehlt | Supply-Type, RACES: [UNDEAD] | **NEU** |
| **Human Farm (World Building)** | ❌ Fehlt | `WORLD_HUMAN_FARM` in Region | **NEU** |
| **Human Pens Room** | ❌ Fehlt | Produces CAPTIVE_HUMAN | **NEU** |
| **Necropolis Room** | ❌ Fehlt | Consumes CAPTIVE_HUMAN → UNDEAD | **NEU** |
| **Necromancy Tech Tree** | ❌ Fehlt | `NECROMANCY_HUMAN_FARM` etc. | **NEU** |
| **Orc Slavery Tech** | ❌ Fehlt | `ORC_SLAVERY` → Slave Raids | **NEU** |
| **Faction Policies** | ❌ Fehlt | Script-simulated via Events | **NEU** |
| **Dual Settlement Logic** | ❌ Fehlt | Script State + Worldmap Building | **NEU** |
| **BONE/ESSENCE Resources** | ❌ Fehlt | Undead Drops, Crafting | **NEU** |
| **Script System** | ❌ Fehlt | `UndeadScript.java` + State | **NEU** |