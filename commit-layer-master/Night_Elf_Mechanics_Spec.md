# Night Elf Mechanics Specification — SyxCraft Alliance Faction

> **Ziel:** Night Elves müssen **eigene einzigartige Mechanik** haben, nicht nur "Elf mit anderen Stats". Vergleichbarer Detailgrad wie Undead.

---

## Core Identity: **Wächter des Waldes / Hüter des Gleichgewichts**

| Aspekt | Design |
|--------|--------|
| **Theme** | Naturmagie, Mondlicht, Stealth, Langzeit-Strategie |
| **Playstyle** | Defensiv, Territorial, Magisch, Langsam aber unaufhaltsam |
| **Unique Loop** | **Moonwell Essenz → Groves → Sentinels → Territory Control → Blight Resistance** |
| **Ressource** | **MOONWATER** (einzigartig, nur Night Elf) + **ESSENCE** (geteilt mit Undead) |

---

## Race Definition: NIGHT_ELF.txt (V71)

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
    CORPSE_DECAY: true,
    SLEEPS: false,  -- Meditation statt Schlaf
    SLAVE_PRICE: 0,
    RAID_MERCINARY: 0.5,
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
    DRINK: [WATER, MOONWATER],
    CLIMATE: { COLD: 1.0, TEMPERATE: 0.8, HOT: 0.3 },
    OTHER_RACES: { HUMAN: 0.6, ORC: 0.4, UNDEAD: 0.2, NIGHT_ELF: 1.0 },
    WORK: {
        FARMING: 1.1,
        CRAFTING: 1.0,
        RESEARCH: 1.4,
        RANGED_COMBAT: 1.3,
    },
},
POPULATION: {
    MAX: 0.8,          -- Niedrigere Pop-Cap
    GROWTH: 0.03,      -- Langsames Wachstum
    CLIMATE: { COLD: 1.0, TEMPERATE: 0.8, HOT: 0.4 },
    TERRAIN: { FOREST: 1.5, MOUNTAIN: 0.8, PLAINS: 0.5 },
},
TRAITS: { NIGHT_ELF: 1.0, MOON_TOUCHED: 1.0, STEALTHY: 1.0 },
RESOURCE: { ESSENCE: 10, MOONWATER: 5 },

BOOST: {
    SERVICE_LEARNING: 1.1,
    SERVICE_STEALTH: 1.3,
    RANGED_COMBAT: 1.2,
    RESEARCH_SPEED: 1.15,
    FOREST_MOVEMENT: 1.3,
},
```

---

## Unique Resource: **MOONWATER**

```txt
# V71/data/init/resource/supply/MOONWATER.txt
_ignoreVanilla: true,
RESOURCE: MOONWATER,
MORALE_ADD: 0.3,
HEALTH_EFFECT: 0.5,
CONSUMPTION_PER_USER_DAY: 0.05,
CONSUMPTION_PER_ITEM_DAY: 0.0,
AMOUNT_PER_PERSON: 1,
RACES: [NIGHT_ELF],
ICON: 32->NIGHT_ELF->MOONWATER,
VALUE: 200,
WEIGHT: 1.0,
SPRITE: MOONWATER,
STACK_SIZE: 20,
CATEGORY_DEFAULT: 1,
EDIBLE: true,
PROPERTIES: {
    TRADEABLE: true,
    MAGICAL: true,
    PERISHABLE: false,
    REGENERATES: true,  -- Einzigartig: regeneriert in Moonwells
},
```

**Mechanik:** Moonwater regeneriert sich in **Moonwells** (Room). Night Elves verbrauchen es täglich. Fällt Vorrat auf 0 → **Moon Fade** Debuff (-50% Stats, keine Regeneration).

---

## Unique Buildings (Rooms)

### 1. MOONWELL — Herz der Night Elf Economy

```txt
# V71/data/init/room/MOONWELL.txt
_ignoreVanilla: true,
ICON: 32->NIGHT_ELF->MOONWELL,
RESOURCES: [STONE, METAL, ESSENCE, MOONWATER],
AREA_COSTS: [0, 0, 0, 0],
FLOOR: [STONE2, DIRT],
MINI_COLOR: 100_200_255,
VALUE_DEGRADE_PER_YEAR: 0.01,
VALUE_PER_WORKER: 0,
VALUE_WORK_SPEED: 1,
BOOST: NIGHT_ELF_MOON_BLESSING,

CONSUMPTION: {
    ESSENCE: { RATE: 0.2, BONUS: 0.1 },
},

WORK: {
    SHIFT_OFFSET: 0.0,  -- Immer aktiv (Nacht/Tag)
    SOUND: MOONWELL_AMBIENT,
    USES_TOOL: false,
    FULFILLMENT: 1.0,
},

OUTPUT: {
    RESOURCE: MOONWATER,
    BASE_RATE: 2.0,          -- 2 Moonwater/Tag base
    BONUS_PER_LEVEL: 0.5,    -- +0.5 pro Upgrade
    MAX_WORKERS: 5,
    REQUIRES_NIGHT: true,    -- Nur nachts Produktion
},

ITEMS: [
    { COSTS: [2, 1, 1, 1], STATS: [2, 1] },
],

UPGRADES: [
    { RESOURCE_MASK: [4, 1, 1, 0], BOOST: 0 },
    { RESOURCE_MASK: [4, 2, 2, 1], BOOST: 0.5 },
    { RESOURCE_MASK: [4, 3, 3, 2], BOOST: 1.0 },
],

EXPERIENCE_BONUS: { BONUS: 1.5, MAX_EMPLOYEES: 200 },

SPRITES: {
    WELL: { FPS: 4, SHADOW_LENGTH: 8, SHADOW_HEIGHT: 4, ROTATES: false, FRAMES: [WELL: 0..7] },
    GLOW: { FPS: 2, SHADOW_LENGTH: 0, SHADOW_HEIGHT: 0, ROTATES: true, FRAMES: [GLOW: 0..3] },
},
```

---

### 2. DRUIDIC_GROVE — Anti-Blight / Territory Control

```txt
# V71/data/init/room/DRUIDIC_GROVE.txt
_ignoreVanilla: true,
ICON: 32->NIGHT_ELF->GROVE,
RESOURCES: [WOOD, STONE, ESSENCE],
AREA_COSTS: [0, 0, 0],
FLOOR: [DIRT, GRASS],
MINI_COLOR: 50_150_50,
VALUE_DEGRADE_PER_YEAR: 0.02,
VALUE_PER_WORKER: 0,
VALUE_WORK_SPEED: 1,
BOOST: NIGHT_ELF_DRUIDIC_POWER,

CONSUMPTION: {
    ESSENCE: { RATE: 0.3, BONUS: 0.05 },
    MOONWATER: { RATE: 0.1, BONUS: 0.02 },
},

WORK: {
    SHIFT_OFFSET: 0.25,
    SOUND: DRUIDIC_CHANT,
    USES_TOOL: false,
    FULFILLMENT: 1.2,
},

EFFECTS: {
    BLIGHT_RESISTANCE_RADIUS: 50,      -- Tiles um Grove
    BLIGHT_CLEANSE_RATE: 0.1,          -- % Blight pro Tag entfernt
    FOREST_GROWTH_BONUS: 0.2,          -- Wald wächst schneller
    WILDLIFE_SPAWN_BOOST: 1.5,         -- Mehr Tiere
},

UPGRADES: [
    { RESOURCE_MASK: [4, 1, 0], BOOST: 0 },
    { RESOURCE_MASK: [4, 2, 1], BOOST: 0.5 },
    { RESOURCE_MASK: [4, 3, 2], BOOST: 1.0 },
],

SPRITES: {
    TREE_ANCIENT: { FPS: 1, SHADOW_LENGTH: 10, SHADOW_HEIGHT: 5, ROTATES: false, FRAMES: [TREE: 0..3] },
    VINES: { FPS: 3, SHADOW_LENGTH: 4, SHADOW_HEIGHT: 2, ROTATES: false, FRAMES: [VINES: 0..5] },
},
```

---

### 3. SENTINEL_OUTPOST — Military / Vision

```txt
# V71/data/init/room/SENTINEL_OUTPOST.txt
_ignoreVanilla: true,
ICON: 32->NIGHT_ELF->SENTINEL,
RESOURCES: [WOOD, STONE, METAL, MOONWATER],
AREA_COSTS: [0, 0, 0, 0],
FLOOR: [WOOD, STONE1],
MINI_COLOR: 150_200_100,
VALUE_DEGRADE_PER_YEAR: 0.03,
VALUE_PER_WORKER: 0,
VALUE_WORK_SPEED: 1,
BOOST: NIGHT_ELF_SENTINEL_VIGILANCE,

CONSUMPTION: {
    MOONWATER: { RATE: 0.2, BONUS: 0.05 },
},

WORK: {
    SHIFT_OFFSET: 0.5,  -- Nacht-Shift
    SOUND: BOW_STRING,
    USES_TOOL: true,
    FULFILLMENT: 0.8,
},

OUTPUT: {
    RESOURCE: SENTINEL_PATROL,  -- Virtuelle Resource für Vision
    BASE_RATE: 1.0,
    BONUS_PER_LEVEL: 0.25,
    MAX_WORKERS: 10,
},

EFFECTS: {
    VISION_RADIUS: 80,           -- Tiles Vision
    STEALTH_DETECTION: 0.8,      -- Erkannt Chance für Stealth Units
    RAID_DEFENSE_BONUS: 0.3,     -- Defense vs Raids
    Orc_RAID_COOLDOWN_MULT: 1.5, -- Orc Raid Cooldown in Region x1.5
},

UPGRADES: [
    { RESOURCE_MASK: [4, 1, 1, 0], BOOST: 0 },
    { RESOURCE_MASK: [4, 2, 2, 1], BOOST: 0.5 },
    { RESOURCE_MASK: [4, 3, 3, 2], BOOST: 1.0 },
],
```

---

### 4. MOONWELL — Moonwater Production (siehe oben)

---

## Tech Tree: Night Elf Specific

### Kategorien: **DRUIDIC**, **SENTINEL**, **LUNAR**, **ARCANE**

```txt
# V71/data/init/tech/DRUIDIC.txt
_ignoreVanilla: true,
TECHS: {
    DRUIDIC_GROVES: {
        COSTS: { CIVIC_KNOWLEDGE: 100, RELIGIOUS_KNOWLEDGE: 50 },
        REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
        UNLOCKS_FACTION: [ ROOM_DRUIDIC_GROVE, ROOM_MOONWELL ],
        UNLOCKS_EVENT: [ BLIGHT_CLEANSE, FOREST_EXPANSION ],
        BOOST: { BLIGHT_RESISTANCE>ADD: 0.2 },
        DESCRIPTION: "Ermöglicht Druidische Haine und Mondbrunnen. Reinigt Blight, erweitert Wälder.",
    },
    
    ANCIENT_GUARDIANS: {
        COSTS: { CIVIC_KNOWLEDGE: 300, SCIENTIFIC_KNOWLEDGE: 200 },
        REQUIRES_TECH_LEVEL: { DRUIDIC_GROVES: 2 },
        UNLOCKS_FACTION: [ ROOM_ANCIENT_PROTECTOR ],
        BOOST: { FOREST_DEFENSE>MUL: 1.5 },
        DESCRIPTION: "Erweckt Alte Wächter. Massive Verteidigungsboni in Waldgebieten.",
    },
}

# V71/data/init/tech/SENTINEL.txt
_ignoreVanilla: true,
TECHS: {
    SENTINEL_OUTPOST: {
        COSTS: { MILITARY_KNOWLEDGE: 150 },
        REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
        UNLOCKS_FACTION: [ ROOM_SENTINEL_OUTPOST, ROOM_MOONWELL ],
        UNLOCKS_EVENT: [ SENTINEL_PATROL, RAID_WARNING ],
        BOOST: { VISION_RANGE>ADD: 20, STEALTH_DETECTION>ADD: 0.2 },
        DESCRIPTION: "Sentinel-Außenposten: Vision, Stealth-Detection, Raid-Warnung.",
    },
    
    MOON_BLADES: {
        COSTS: { MILITARY_KNOWLEDGE: 300, SCIENTIFIC_KNOWLEDGE: 200 },
        REQUIRES_TECH_LEVEL: { SENTINEL_OUTPOST: 2 },
        UNLOCKS_FACTION: [ ROOM_MOON_FORGE ],
        BOOST: { RANGED_DAMAGE>MUL: 1.3, MOON_DAMAGE>ADD: 15 },
        DESCRIPTION: "Mondklingen: Erhöht Fernkampfschaden, Mondschaden vs Undead.",
    },
}

# V71/data/init/tech/LUNAR.txt
_ignoreVanilla: true,
TECHS: {
    MOONWELL_MASTERY: {
        COSTS: { RELIGIOUS_KNOWLEDGE: 200, CIVIC_KNOWLEDGE: 100 },
        REQUIRES_TECH_LEVEL: { DRUIDIC_GROVES: 1 },
        UNLOCKS_FACTION: [ ROOM_MOONWELL_UPGRADE_1, ROOM_MOONWELL_UPGRADE_2 ],
        BOOST: { MOONWATER_PRODUCTION>MUL: 1.5, MOONWATER_REGEN>ADD: 0.1 },
        DESCRIPTION: "Mondbrunn-Meisterschaft: Mehr Moonwater, schnellere Regeneration.",
    },
    
    MOON_FADE_IMMUNITY: {
        COSTS: { RELIGIOUS_KNOWLEDGE: 500, ARCANE_KNOWLEDGE: 300 },
        REQUIRES_TECH_LEVEL: { MOONWELL_MASTERY: 2 },
        UNLOCKS_EVENT: [ MOON_FADE_PROTECTION ],
        BOOST: { MOON_FADE_RESISTANCE>SET: 1.0 },
        DESCRIPTION: "Immunität gegen Moon Fade. Night Elves verlieren keine Stats bei Moonwater-Mangel.",
    },
}

# V71/data/init/tech/ARCANE.txt
_ignoreVanilla: true,
TECHS: {
    MOONWELL_ESSENCE_SYNTHESIS: {
        COSTS: { SCIENTIFIC_KNOWLEDGE: 200, ARCANE_KNOWLEDGE: 150 },
        REQUIRES_TECH_LEVEL: { DRUIDIC_GROVES: 1 },
        UNLOCKS_FACTION: [ ROOM_ESSENCE_CONDENSER ],
        BOOST: { ESSENCE_FROM_MOONWATER>ADD: 0.1 },
        DESCRIPTION: "Konvertiert Moonwater zu Essence. Teile mit Undead möglich.",
    },
}
```

---

## Unique Events

### 1. BLIGHT_CLEANSE (Druidic Grove)

```txt
# V71/data/init/event/BLIGHT_CLEANSE.txt
BLIGHT_CLEANSE: {
    ICON: 32->NIGHT_ELF->CLEANSE,
    DURATION: { DAYS: 5.0 },
    OCCURRENCE: {
        RACE: { NIGHT_ELF: 1.0 },
        REQUIRES: { GREATER: { BLIGHT_LEVEL: 10, HAS_DRUIDIC_GROVE: 1 } }
    },
    SELECTION: {
        REGIONS: {
            MAX_AMOUNT: { AMOUNT: 3 },
            FILTERS: [ { GREATER: { BLIGHT_LEVEL: 20 } } ]
        }
    },
    CHOICES: [
        {
            ACTIONS: [
                { TYPE: EVENT, EVENT: BLIGHT_CLEANSE_START },
                { TYPE: RESOURCE_ADD, RESOURCE: ESSENCE, AMOUNT: -20 },
                { TYPE: RESOURCE_ADD, RESOURCE: MOONWATER, AMOUNT: -50 },
            ]
        }
    ]
}

BLIGHT_CLEANSE_START: {
    ICON: 32->NIGHT_ELF->CLEANSE,
    DURATION: { DAYS: 10.0 },
    ON_SPAWN: {
        ACTIONS: [
            { TYPE: BOOST_PERM, PLAYER: { BLIGHT_LEVEL>MUL: 0.5 } },
            { TYPE: EVENT, EVENT: BLIGHT_CLEANSE_PROGRESS },
        ]
    }
}
```

---

### 2. SENTINEL_PATROL (Sentinel Outpost)

```txt
# V71/data/init/event/SENTINEL_PATROL.txt
SENTINEL_PATROL: {
    ICON: 32->NIGHT_ELF->PATROL,
    DURATION: { DAYS: 30.0 },
    OCCURRENCE: {
        RACE: { NIGHT_ELF: 1.0 },
        REQUIRES: { EQUAL: { HAS_SENTINEL_OUTPOST: 1 } },
        MAX_SPAWNS: 1,
    },
    CHOICES: [
        {
            ACTIONS: [
                { TYPE: BOOST_PERM, PLAYER: { VISION_RANGE>ADD: 30 } },
                { TYPE: BOOST_PERM, PLAYER: { Orc_RAID_COOLDOWN>MUL: 1.5 } },
            ]
        }
    ]
}
```

---

### 3. MOON_FADE (Night Elf Unique Threat)

```txt
# V71/data/init/event/MOON_FADE.txt
MOON_FADE: {
    ICON: 32->NIGHT_ELF->FADE,
    DURATION: { DAYS: 1.0 },
    OCCURRENCE: {
        RACE: { NIGHT_ELF: 1.0 },
        REQUIRES: { LESS: { RESOURCE_MOONWATER: 5 } }
    },
    TAGS: { ALLOW_NOT: [CHAIN_ONGOING] },
    CHOICES: [
        {
            ACTIONS: [
                { TYPE: BOOST_PERM, PLAYER: { ALL_STATS>MUL: 0.5 } },
                { TYPE: EVENT, EVENT: MOON_FADE_WARNING },
            ]
        }
    ]
}

MOON_FADE_WARNING: {
    ICON: 32->NIGHT_ELF->WARNING,
    DURATION: { DAYS: 7.0 },
    ON_SPAWN: {
        ACTIONS: [
            { TYPE: NOTIFICATION, TEXT: "Moonwater Vorräte kritisch! Moonwells aktivieren!" },
        ]
    }
}
```

---

## Race Relations (Dynamic via Laws/Events)

| Ziel | Base Liking | Law/Event Modifier |
|------|-------------|-------------------|
| Human | 0.6 | +0.2 bei `ALLIANCE_COMMAND` |
| Orc | 0.4 | -0.3 bei `ORC_SLAVERY` |
| Undead | 0.2 | -0.5 bei `DARK_RITUALS` |
| Night Elf | 1.0 | — |

---

## Unique Playstyle Summary

| Phase | Fokus | Key Buildings | Key Resources |
|-------|-------|---------------|---------------|
| **Early** | Moonwell + Grove | Moonwell, Druidic Grove | Moonwater, Essence |
| **Mid** | Territory Control | Sentinel Outpost, Druidic Grove | Moonwater, Vision |
| **Late** | Anti-Blight / Endgame | Ancient Guardians, Moonwell Mastery | Moonwater Immunity, Essence Synthese |

---

## Integration mit Undead/Orc/Human

| Interaktion | Mechanik |
|-------------|----------|
| **Undead → Night Elf** | Blight Spread Event → Druidic Grove cleansed |
| **Orc → Night Elf** | Raid Target → Sentinel Outpost warns |
| **Human → Night Elf** | Alliance Trade → Moonwater export |
| **Night Elf → Undead** | Essence Trade (Moonwell Synthesis) |
| **Night Elf → Orc** | Raid Defense → Orc Raid Cooldown x1.5 |

---

## Offene Fragen für Night Elf

1. **Moonwater als Hard Requirement?** → Ja, Moon Fade = Game Over Risk
2. **Essence Trade mit Undead?** → Ja via `MOONWELL_ESSENCE_SYNTHESIS` Tech
3. **Blight Mechanik schon in V71?** → Muss geprüft werden (V71 Impact Analysis)
4. **Night Elf Start Bias?** → Forest spawn guaranteed via `HOME` map