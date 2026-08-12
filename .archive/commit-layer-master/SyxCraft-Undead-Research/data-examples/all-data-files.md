# Data Examples — SyxCraft Undead Overhaul

Konkrete `.txt` Datei-Definitionen für alle neuen Game-Objekte.

---

## 1. UNDEAD Race — `V71/data/init/race/UNDEAD.txt`

```txt
# LLM.entry
# STRUCTURE_EXPLANATION: UNDEAD race — tireless workers immune to climate, feed on captives.
# ENGINE_DEFAULTS: immortal, maintenance affinity, no food/drink sleep, climate neutral.
# LAST_ENTRY: Entry 1
# FILE_CONTEXT: V71/data/init/race/UNDEAD.txt
# VERSION: 0.1.0
# FLAGS: DATA_NEW, VERIFIED
# FLAG_COUNT: 2

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
    FOOD: [],                    # KEINE Nahrung
    DRINK: [],                   # KEINE Getränke
    CLIMATE: { COLD: 1.0, HOT: 1.0, TEMPERATE: 1.0 },
    OTHER_RACES: { HUMAN: 0.3, ORC: 0.7, NIGHT_ELF: 0.2 },
    WORK: {
        _ASYLUM: -1.0,
        _EMBASSY: -0.5,
        _INN: -1.0,
        _POLICE: 0.0,
        ADMIN_NORMAL: 0.5,
        BARBER_NORMAL: -1.0,
        GRAVEYARD_NORMAL: 2.0,
        LABORATORY_NORMAL: 1.5,
        LIBRARY_NORMAL: 0.5,
        MARKET_NORMAL: 0.0,
        MINE_GEM: 1.5,
        PHYSICIAN_NORMAL: -1.0,
        REFINER_COALER: 1.2,
        REFINER_SMELTER: 1.2,
        REFINER_WEAVER: -0.5,
        SCHOOL_NORMAL: -1.0,
        SPEAKER_NORMAL: 0.0,
        STAGE_NORMAL: -1.0,
        TAVERN_NORMAL: -1.0,
        TOMB_NORMAL: 2.0,
        UNIVERSITY_NORMAL: 1.0,
        WORKSHOP_BOWYER: 1.0,
        WORKSHOP_CARPENTER: 1.0,
        WORKSHOP_JEWELRY: 0.5,
        WORKSHOP_MECHANIC: 1.5,
        WORKSHOP_SMITHY: 1.5,
        WORKSHOP_TAILOR: -0.5,
    },
    STRUCTURE: { MOUNTAIN: 1.0, STONE: 1.2, GRAND: 1.0, WOOD: 0.3, OUTDOORS: 0.2 },
    POOL: { POOL_STONE: 1.0 },
    ROAD: { STONE1: 0.8, STONE2: 1.0 },
    BUILDING_OVERRIDE: { CIVIC_L_STANDS: 0.5 },
},
POPULATION: {
    MAX: 1.0,
    GROWTH: 0.0,              # KEIN natürliches Wachstum!
    CLIMATE: { COLD: 1.0, TEMPERATE: 1.0, HOT: 1.0 },
    TERRAIN: { MOUNTAIN: 1.5, FOREST: 0.2, NONE: 1.0 },
},
TRAITS: { UNDEAD: 1.0, IMMORTAL: 1.0, TIRELESS: 1.0 },
RESOURCE: { BONE: 50, ESSENCE: 20 },     # Drop bei Tod (statt Meat/Leather)

BOOST: {
    PHYSICS_RESISTANCE_COLD>ADD: 0.0,
    PHYSICS_RESISTANCE_HOT>ADD: 0.0,
    PHYSICS_DEATH_AGE>MUL: 0.0,           # Unsterblich
    BATTLE_BLUNT_ATTACK>ADD: 5,
    CIVIC_IMMIGRATION>MUL: 0.0,           # Keine Immigration
    ROOM_GRAVEYARD*>MUL: 2.0,
    ROOM_TOMB*>MUL: 2.0,
    ROOM_LABORATORY*>MUL: 1.5,
    ROOM_MINE*>MUL: 1.3,
    ROOM_REFINER*>MUL: 1.2,
    WORK_MAINTENANCE>MUL: 1.5,
    BEHAVIOUR_SANITY>MUL: 2.0,            # Unempfindlich gegen Wahnsinn
    BEHAVIOUR_LAWFULNESS>MUL: 1.5,
},

EQUIPMENT_NOT_ENABLED: [
    CLOTHES, ARMOR, WEAPON_RANGED, WEAPON_MELEE, TOOL
],
EQUIPMENT_ENABLED: [
    TRINKET, AMULET, RING
],
```

---

## 2. CAPTIVE_HUMAN Resource — `V71/data/init/resource/supply/CAPTIVE_HUMAN.txt`

```txt
# LLM.entry
# STRUCTURE_EXPLANATION: Captive Human — living resource for Undead conversion and Human Farm production.
# ENGINE_DEFAULTS: supply category, morale penalty, Undead only.
# LAST_ENTRY: Entry 1
# FILE_CONTEXT: V71/data/init/resource/supply/CAPTIVE_HUMAN.txt
# VERSION: 0.1.0
# FLAGS: DATA_NEW, VERIFIED
# FLAG_COUNT: 2

_ignoreVanilla: true,
RESOURCE: CAPTIVE_HUMAN,
MORALE_ADD: -0.5,
HEALTH_EFFECT: 0.1,
CONSUMPTION_PER_USER_DAY: 0.0,
CONSUMPTION_PER_ITEM_DAY: 0.0,
AMOUNT_PER_PERSON: 1,
RACES: [UNDEAD],
ICON: 32->UNDEAD->CAPTIVE,
VALUE: 100,
WEIGHT: 80.0,
SPRITE: CAPTIVE_HUMAN,
STACK_SIZE: 10,
CATEGORY_DEFAULT: 1,
EDIBLE: false,
PROPERTIES: {
    TRADEABLE: true,
    PERISHABLE: false,
    CONVERTIBLE: true,
},
```

---

## 3. HUMAN_PENS Room — `V71/data/init/room/HUMAN_PENS.txt`

```txt
# LLM.entry
# STRUCTURE_EXPLANATION: Human Pens — breeds and maintains Captive Humans for Undead conversion.
# ENGINE_DEFAULTS: requires CAPTIVE_HUMAN input, produces CAPTIVE_HUMAN growth.
# LAST_ENTRY: Entry 1
# FILE_CONTEXT: V71/data/init/room/HUMAN_PENS.txt
# VERSION: 0.1.0
# FLAGS: DATA_NEW, VERIFIED
# FLAG_COUNT: 2

_ignoreVanilla: true,
ICON: 32->UNDEAD->PENS,
RESOURCES: [WOOD, STONE, METAL, FURNITURE],
AREA_COSTS: [0, 0, 0, 0],
FLOOR: [DIRT, WOOD, STONE2],
MINI_COLOR: 100_50_50,
VALUE_DEGRADE_PER_YEAR: 0.05,
VALUE_PER_WORKER: 0,
VALUE_WORK_SPEED: 1,
BOOST: UNDEAD_NECROMANCY,

CONSUMPTION: {
    CAPTIVE_HUMAN: { RATE: 0.1, BONUS: 0.05 },   # Fütterung der Gefangenen
    FOOD_MEAT: { RATE: 0.5, BONUS: 0.1 },         # Zusatzfutter beschleunigt Wachstum
},

WORK: {
    SHIFT_OFFSET: 0.25,
    SOUND: NECROMANCY,
    USES_TOOL: false,
    FULFILLMENT: 0.3,
},

OUTPUT: {                                  # Custom: Room produziert Captive Humans
    RESOURCE: CAPTIVE_HUMAN,
    BASE_RATE: 0.02,                       # 2% pro Worker/Tag
    BONUS_PER_LEVEL: 0.005,
    MAX_WORKERS: 20,
},

ITEMS: [
    {
        COSTS: [1, 1, 1, 1],
        STATS: [1, 1],
    },
],

UPGRADES: [
    { RESOURCE_MASK: [4, 1, 0, 0], BOOST: 0 },           # Tier 1: Basic Pens
    { RESOURCE_MASK: [4, 1, 2, 0], BOOST: 0.5 },         # Tier 2: Feeding Troughs
    { RESOURCE_MASK: [4, 1, 3, 1], BOOST: 1.0 },         # Tier 3: Breeding Chambers
],

EXPERIENCE_BONUS: { BONUS: 1.0, MAX_EMPLOYEES: 500 },

SPRITES: {
    TABLE_COMBO: [
        { FPS: 0, SHADOW_LENGTH: 6, SHADOW_HEIGHT: 3, FRAMES: [COMBO_TABLES: 0, COMBO_TABLES: 1] },
        { COLOR: {R: 120, G: 40, B: 40}, FPS: 0, SHADOW_LENGTH: 6, SHADOW_HEIGHT: 3, FRAMES: [COMBO_TABLES: 4] },
    ],
    CAGE_HUMAN: {
        FPS: 2, SHADOW_LENGTH: 4, SHADOW_HEIGHT: 2, ROTATES: false,
        FRAMES: [CAGE_HUMAN: 0, CAGE_HUMAN: 1, CAGE_HUMAN: 2, CAGE_HUMAN: 3],
    },
    GUARD_POST: [
        { FPS: 0, SHADOW_LENGTH: 2, SHADOW_HEIGHT: 0, ROTATES: true, FRAMES: [GUARD: 0] },
        { FPS: 0, SHADOW_LENGTH: 2, SHADOW_HEIGHT: 0, ROTATES: true, FRAMES: [GUARD: 1] },
    ],
},
```

---

## 4. NECROPOLIS Room — `V71/data/init/room/NECROPOLIS.txt`

```txt
# LLM.entry
# STRUCTURE_EXPLANATION: Necropolis — converts Captive Humans into Undead citizens.
# ENGINE_DEFAULTS: consumes CAPTIVE_HUMAN, produces UNDEAD citizens.
# LAST_ENTRY: Entry 1
# FILE_CONTEXT: V71/data/init/room/NECROPOLIS.txt
# VERSION: 0.1.0
# FLAGS: DATA_NEW, VERIFIED
# FLAG_COUNT: 2

_ignoreVanilla: true,
ICON: 32->UNDEAD->NECROPOLIS,
RESOURCES: [STONE, METAL, MACHINERY, FURNITURE, ESSENCE],
AREA_COSTS: [0, 0, 0, 0, 0],
FLOOR: [STONE2, STONE1, DIRT],
MINI_COLOR: 80_80_100,
VALUE_DEGRADE_PER_YEAR: 0.02,
VALUE_PER_WORKER: 0,
VALUE_WORK_SPEED: 1,
BOOST: UNDEAD_NECROMANCY,

CONSUMPTION: {
    CAPTIVE_HUMAN: { RATE: 1.0, BONUS: 0.2 },      # 1 Captive pro Conversion
    ESSENCE: { RATE: 0.5, BONUS: 0.1 },            # Magische Essenz
},

WORK: {
    SHIFT_OFFSET: 0.5,
    SOUND: NECROMANCY_RITUAL,
    USES_TOOL: false,
    FULFILLMENT: 0.8,
},

CONVERSION: {                                      # Custom: Conversion Logic
    INPUT: CAPTIVE_HUMAN,
    OUTPUT_RACE: UNDEAD,
    RATE: 1.0,                                     # 1 Captive = 1 Undead
    COOLDOWN_DAYS: 5.0,
    REQUIRES_TECH: NECROMANCY_HUMAN_FARM,
},

ITEMS: [
    { COSTS: [2, 1, 1, 1, 1], STATS: [2, 1] },
],

UPGRADES: [
    { RESOURCE_MASK: [4, 2, 1, 1, 0], BOOST: 0 },
    { RESOURCE_MASK: [4, 2, 2, 1, 1], BOOST: 0.5 },
    { RESOURCE_MASK: [4, 2, 3, 2, 2], BOOST: 1.0 },
],

EXPERIENCE_BONUS: { BONUS: 2.0, MAX_EMPLOYEES: 1000 },

SPRITES: {
    RITUAL_CIRCLE: { FPS: 4, SHADOW_LENGTH: 8, SHADOW_HEIGHT: 4, ROTATES: false, FRAMES: [RITUAL: 0..7] },
    ALTAR: [ { FPS: 0, SHADOW_LENGTH: 6, SHADOW_HEIGHT: 3, ROTATES: false, FRAMES: [ALTAR: 0] } ],
    CAGE_EMPTY: [ { FPS: 0, SHADOW_LENGTH: 4, SHADOW_HEIGHT: 2, ROTATES: true, FRAMES: [CAGE: 0] } ],
},
```

---

## 5. NECROMANCY_HUMAN_FARM Tech — `V71/data/init/tech/NECROMANCY_HUMAN_FARM.txt`

```txt
# LLM.entry
# STRUCTURE_EXPLANATION: Necromancy Human Farm Tech — Unlocks Human Farm world building and Human Pens room.
# ENGINE_DEFAULTS: Early-mid game (Civic 200), requires BASIC_MINING.
# LAST_ENTRY: Entry 1
# FILE_CONTEXT: V71/data/init/tech/NECROMANCY_HUMAN_FARM.txt
# VERSION: 0.1.0
# FLAGS: DATA_NEW, VERIFIED
# FLAG_COUNT: 2

_ignoreVanilla: true,
TECHS: {
    NECROMANCY_HUMAN_FARM: {
        COSTS: { CIVIC_KNOWLEDGE: 200 },
        REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
        UNLOCKS_FACTION: [
            ROOM_HUMAN_PENS,
            ROOM_NECROPOLIS,
        ],
        UNLOCKS_WORLD_BUILDING: [ WORLD_HUMAN_FARM ],
        UNLOCKS_EVENT: [ FOUND_HUMAN_FARM, UNDEAD_CONVERSION ],
        BOOST: { UNDEAD_CAPTIVE_HUMAN_EFFICIENCY>ADD: 0.1 },
        DESCRIPTION: "Ermöglicht die Errichtung von Menschenfarmen auf der Weltkarte und den Bau von Menschenställen & Nekropolen in der Hauptstadt.",
    },
},
```

---

## 6. WORLD_HUMAN_FARM World Building — `V71/data/init/world/building/WORLD_HUMAN_FARM.txt`

```txt
# LLM.entry
# STRUCTURE_EXPLANATION: Human Farm — Worldmap building that generates Captive Humans passively.
# ENGINE_DEFAULTS: Region building, requires NECROMANCY_HUMAN_FARM tech, produces CAPTIVE_HUMAN.
# LAST_ENTRY: Entry 1
# FILE_CONTEXT: V71/data/init/world/building/WORLD_HUMAN_FARM.txt
# VERSION: 0.1.0
# FLAGS: DATA_NEW, VERIFIED
# FLAG_COUNT: 2

_ignoreVanilla: true,
BUILDING: WORLD_HUMAN_FARM,
CATEGORY: CIVIC,
ICON: 32->UNDEAD->FARM,
COSTS: { WOOD: 200, STONE: 300, METAL: 100, CREDITS: 5000 },
BUILD_TIME_DAYS: 30,
REQUIRES_TECH: NECROMANCY_HUMAN_FARM,
MAX_PER_REGION: 1,
REQUIRES_TERRAIN: { PLAINS: 0.5, FOREST: 0.3 },

PRODUCTION: {
    RESOURCE: CAPTIVE_HUMAN,
    BASE_RATE: 5.0,                    # 5 Captive Humans pro Tag (Base)
    SCALING: { LEVEL: 1.5 },           # Pro Level +50%
    MAX_LEVEL: 5,
    REQUIRES_POPULATION: 0,            # Benötigt KEINE Bevölkerung in Region
},

MAINTENANCE: { CREDITS: 50, ESSENCE: 10 },

UPGRADES: [
    { LEVEL: 2, COSTS: { WOOD: 100, STONE: 150, CREDITS: 2000 }, RATE_MULT: 1.5 },
    { LEVEL: 3, COSTS: { WOOD: 200, STONE: 300, METAL: 50, CREDITS: 5000 }, RATE_MULT: 2.25 },
    { LEVEL: 4, COSTS: { STONE: 500, METAL: 100, ESSENCE: 20, CREDITS: 10000 }, RATE_MULT: 3.375 },
    { LEVEL: 5, COSTS: { STONE: 1000, METAL: 200, ESSENCE: 50, CREDITS: 25000 }, RATE_MULT: 5.0 },
],

EVENTS: [
    { TRIGGER: LEVEL_UP, EVENT: HUMAN_FARM_EXPANDED },
    { TRIGGER: LOW_RESOURCES, EVENT: HUMAN_FARM_STRUGGLING },
],
```

---

## 7. UNDEAD_CONVERSION Event — `V71/data/init/event/UNDEAD_CONVERSION.txt`

```txt
# LLM.entry
# STRUCTURE_EXPLANATION: Convert Captive Humans to Undead Citizens.
# ENGINE_DEFAULTS: Requires UNDEAD race, NECROPOLIS room, CAPTIVE_HUMAN resource.
# LAST_ENTRY: Entry 1
# FILE_CONTEXT: V71/data/init/event/UNDEAD_CONVERSION.txt
# VERSION: 0.1.0
# FLAGS: DATA_NEW, VERIFIED
# FLAG_COUNT: 2

_ignoreVanilla: true,
UNDEAD_CONVERSION: {
    ICON: 32->UNDEAD->CONVERT,
    DURATION: { DAYS: 1.0 },
    
    OCCURRENCE: {
        RACE: { UNDEAD: 1.0 },
        REQUIRES: {
            GREATER: { 
                POPULATION_CITIZEN_HUMAN: 5,
                RESOURCE_CAPTIVE_HUMAN: 3,
                ROOM_NECROPOLIS: 1
            }
        },
        MAX_SPAWNS: 1,
    },
    
    TAGS: { ALLOW_NOT: [CHAIN_ONGOING, CONVERSION_COOLDOWN] },
    
    SELECTION: {
        SUBJECTS: {
            USE_AS_ICON: true,
            FILTERS: [
                { EQUAL: { CLASS_CITIZEN: 1, RACE: HUMAN } }
            ],
            MAX_AMOUNT: { RELATIVE: 0.15 },
        }
    },
    
    CHOICES: [
        {
            ACTIONS: [
                { TYPE: SUBJECTS_KILL, AMOUNTS: { HUMAN: { RELATIVE: 0.15 } }, DEATH_CAUSE: NECROMANCY, USE_SELECTION: true },
                { TYPE: EVENT, EVENT: UNDEAD_RISE },
                { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: -5 },
                { TYPE: CITIZEN_ADD, RACE: UNDEAD, AMOUNT: { RELATIVE: 0.15 } },
                { TYPE: BOOST_PERM, PLAYER: { UNDEAD_CONVERSIONS_TOTAL>ADD: 1 } }
            ]
        },
        {
            ACTIONS: [
                { TYPE: EVENT, EVENT: CONVERSION_DECLINED }
            ]
        }
    ]
},

UNDEAD_RISE: {
    ICON: 32->UNDEAD->RISE,
    DURATION: { DAYS: 3.0 },
    ON_SPAWN: {
        ACTIONS: [
            { TYPE: BOOST, PLAYER: { UNDEAD_MORALE>MUL: 1.1 } }
        ]
    }
},

CONVERSION_DECLINED: {
    ICON: 32->UNDEAD->DECLINE,
    DURATION: { DAYS: 30.0, ACTIONS: [{ TYPE: EVENT, EVENT: CONVERSION_COOLDOWN_END }] },
    ON_SPAWN: {
        ACTIONS: [
            { TYPE: BOOST, PLAYER: { UNDEAD_CONVERSION_COOLDOWN>SET: 1 } }
        ]
    }
},

CONVERSION_COOLDOWN_END: {
    ICON: 32->UNDEAD->COOLDOWN_END,
    DURATION: { DAYS: 1.0 },
    ON_SPAWN: {
        ACTIONS: [
            { TYPE: BOOST_PERM, PLAYER: { UNDEAD_CONVERSION_COOLDOWN>SET: 0 } }
        ]
    }
},
```

---

## 8. ORC_SLAVE_TRADE Event — `V71/data/init/event/ORC_SLAVE_TRADE.txt`

```txt
# LLM.entry
# STRUCTURE_EXPLANATION: Orc Slave Trade — Orks raid human settlements, sell captives to Undead.
# ENGINE_DEFAULTS: Requires ORC race, ORC_SLAVERY tech, human population in target region.
# LAST_ENTRY: Entry 1
# FILE_CONTEXT: V71/data/init/event/ORC_SLAVE_TRADE.txt
# VERSION: 0.1.0
# FLAGS: DATA_NEW, VERIFIED
# FLAG_COUNT: 2

_ignoreVanilla: true,
ORC_SLAVE_RAID: {
    ICON: 32->ORC->RAID,
    DURATION: { DAYS: 7.0 },
    
    OCCURRENCE: {
        RACE: { ORC: 1.0 },
        REQUIRES: { EQUAL: { HAS_TECH: ORC_SLAVERY } },
    },
    
    SELECTION: {
        REGIONS: {
            MAX_AMOUNT: { AMOUNT: 1 },
            FILTERS: [
                { EQUAL: { FACTION_IS_PLAYER: 0 } },
                { GREATER: { POPULATION_RACE_HUMAN: 30 } },
                { GREATER: { DISTANCE_TO_ORC_TERRITORY: 0 } },
                { LESS: { DISTANCE_TO_ORC_TERRITORY: 50 } }
            ]
        }
    },
    
    CHOICES: [
        {
            ACTIONS: [
                { TYPE: EVENT, EVENT: SLAVE_RAID_SUCCESS },
                { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: 15 },
                { TYPE: CREDITS, AMOUNT: -2000 },
                { TYPE: FACTION_RELATION, FACTION: TARGET, VALUE: -25 }
            ]
        },
        {
            ACTIONS: [
                { TYPE: EVENT, EVENT: RAID_ABORTED }
            ]
        }
    ]
},

SLAVE_RAID_SUCCESS: {
    ICON: 32->ORC->SUCCESS,
    DURATION: { DAYS: 30.0 },
    ON_SPAWN: {
        ACTIONS: [
            { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: 15 },
            { TYPE: BOOST_PERM, PLAYER: { ORC_SLAVES_CAPTURED>ADD: 15 } }
        ]
    }
},

ORC_SLAVE_TRADE_OFFER: {
    ICON: 32->TRADE->SLAVES,
    DURATION: { DAYS: 1.0 },
    
    OCCURRENCE: {
        RACE: { ORC: 1.0 },
        REQUIRES: { GREATER: { RESOURCE_CAPTIVE_HUMAN: 10 } }
    },
    
    SELECTION: {
        FACTIONS: {
            FILTERS: [
                { EQUAL: { RACE: UNDEAD } },
                { GREATER: { RELATION: -50 } }
            ]
        }
    },
    
    CHOICES: [
        {
            ACTIONS: [
                { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: -20 },
                { TYPE: CREDITS, AMOUNT: 3000 },
                { TYPE: FACTION_RELATION, FACTION: UNDEAD, VALUE: 10 }
            ]
        },
        {
            ACTIONS: [
                { TYPE: EVENT, EVENT: TRADE_DECLINED }
            ]
        }
    }
},
```

---

## 9. BONE & ESSENCE Resources (für UNDEAD Drops)

### `V71/data/init/resource/supply/BONE.txt`
```txt
_ignoreVanilla: true,
RESOURCE: BONE,
MORALE_ADD: 0.0,
HEALTH_EFFECT: 0.0,
CONSUMPTION_PER_USER_DAY: 0.0,
CONSUMPTION_PER_ITEM_DAY: 0.0,
AMOUNT_PER_PERSON: 1,
RACES: [UNDEAD],
ICON: 32->UNDEAD->BONE,
VALUE: 5,
WEIGHT: 2.0,
SPRITE: BONE,
STACK_SIZE: 100,
CATEGORY_DEFAULT: 1,
EDIBLE: false,
PROPERTIES: { TRADEABLE: true, CRAFTING_MATERIAL: true },
```

### `V71/data/init/resource/supply/ESSENCE.txt`
```txt
_ignoreVanilla: true,
RESOURCE: ESSENCE,
MORALE_ADD: 0.1,
HEALTH_EFFECT: 0.2,
CONSUMPTION_PER_USER_DAY: 0.01,
CONSUMPTION_PER_ITEM_DAY: 0.0,
AMOUNT_PER_PERSON: 1,
RACES: [UNDEAD],
ICON: 32->UNDEAD->ESSENCE,
VALUE: 50,
WEIGHT: 0.5,
SPRITE: ESSENCE,
STACK_SIZE: 50,
CATEGORY_DEFAULT: 1,
EDIBLE: false,
PROPERTIES: { TRADEABLE: true, MAGICAL: true },
```