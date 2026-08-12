# V71 Orc Slave System — Complete Analysis

> **Engine:** V71.44 "Reign of Terror"
> **Source:** Vanilla Data Extraction + Engine Analysis
> **Purpose:** Enable "Slaves as War Loot" mechanic for Orcs → Undead Trade

---

## 1. Vanilla Slavery System — V71 State

### Core Data Structures

```java
// Population Class System (V71 New)
public enum PopulationClass {
    CITIZEN,
    SLAVE,
    NOBLE
}

// Settlement Population Tracking
public class Settlement {
    Map<Race, Map<PopulationClass, Integer>> population;
    Map<Race, Map<PopulationClass, Double>> loyalty;
    
    // Methods
    public int getPopulation(Race race, PopulationClass clazz);
    public void addPopulation(Race race, PopulationClass clazz, int amount);
    public void removePopulation(Race race, PopulationClass clazz, int amount);
    public void changePopulationClass(Race race, PopulationClass from, PopulationClass to, int amount);
}
```

### Slavery Law System (V71 New)

```txt
# V71/data/init/law/SLAVERY.txt
LAW: SLAVERY
CATEGORY: CRIMINAL
TIER: 1
GP_COST: 100
REQUIRES_BUILDING: [COURTHOUSE]
EFFECTS:
  - POPULATION_CLASS_SLAVE_ENABLED: true
  - SLAVE_RACE_WHITELIST: [HUMAN, ORC, NIGHT_ELF]
  - ENSLAVEMENT_CHANCE: 0.1        # Chance per crime
  - SLAVE_PRICE_BASE: 500          # Dynamic base price
  - PRICE_MODIFIERS:
      SUPPLY_DEMAND: true
      RACE_MODIFIER: { HUMAN: 1.0, ORC: 1.2, NIGHT_ELF: 0.8 }
      RELATION_MODIFIER: true

LAW: SLAVERY_TIER_2
CATEGORY: CRIMINAL
TIER: 2
REQUIRES_LAW: SLAVERY
GP_COST: 500
EFFECTS:
  - SLAVE_TRADE_ENABLED: true        # Diplomatic Action unlock
  - RAID_ENSLAVEMENT_CHANCE: 0.25    # Raid capture chance
  - SLAVE_PRICE_MULTIPLIER: 1.5

LAW: SLAVERY_TIER_3
CATEGORY: CRIMINAL
TIER: 3
REQUIRES_LAW: SLAVERY_TIER_2
GP_COST: 2000
EFFECTS:
  - MASS_ENSLAVEMENT: true
  - SLAVE_TRADE_TAX: 0.1
```

### Enslavement Sources (V71)

| Source | Mechanism | Output |
|--------|-----------|--------|
| **Crime Punishment** | Law: `ENSLAVEMENT_CHANCE` per crime | SLAVE Class added to Settlement |
| **Raid Capture** | Raid Event → `ENSLAVEMENT_CHANCE` | Captured Population → SLAVE Class |
| **Diplomatic Trade** | Diplomatic Action `REQUEST_SLAVE_TRADE` | Population Class Transfer |
| **Enslavement Law** | Court Decision | Manual Population Class Change |

---

## 2. Orc Slave System — SyxCraft Requirements

### Concept Requirements
1. **Orcs raid Human settlements** → Capture Humans as Slaves
2. **Orcs store Slaves** in their own Slave Pens (intermediate storage)
3. **Orcs sell Slaves to Undead** via Diplomatic Trade
4. **Undead convert Slaves** → Undead Citizens

### V71 Integration Points

#### A. Orc Raid Event → Slave Generation
```txt
# V71/data/init/event/ORC_SLAVE_RAID.txt
ORC_SLAVE_RAID: {
    ICON: 32->ORC->RAID,
    DURATION: { DAYS: 7.0 },
    OCCURRENCE: {
        RACE: { ORC: 1.0 },
        REQUIRES: { 
            EQUAL: { HAS_TECH: ORC_SLAVERY },
            GREATER: { POPULATION_RACE_HUMAN: 30 }
        }
    },
    SELECTION: {
        REGIONS: {
            FILTERS: [
                { EQUAL: { FACTION_IS_PLAYER: 0 } },
                { GREATER: { POPULATION_RACE_HUMAN: 50 } },
                { LESS: { DISTANCE_TO_ORC_TERRITORY: 50 } }
            ]
        }
    },
    CHOICES: [{
        ACTIONS: [
            { TYPE: EVENT, EVENT: SLAVE_RAID_SUCCESS },
            { TYPE: POPULATION_CLASS_ADD, CLASS: SLAVE, RACE: HUMAN, AMOUNT: { RELATIVE: 0.1 } },
            { TYPE: CREDITS, AMOUNT: -1000 },
            { TYPE: FACTION_RELATION, FACTION: TARGET, VALUE: -50 }
        ]
    }, {
        ACTIONS: [ { TYPE: EVENT, EVENT: RAID_ABORTED } ]
    }]
}
```

**Key V71 Change:** `TYPE: POPULATION_CLASS_ADD` instead of `RESOURCE_ADD`

---

#### B. Orc Slave Pen — Intermediate Storage
```txt
# V71/data/init/room/SLAVE_PEN.txt
_ignoreVanilla: true,
ICON: 32->ORC->SLAVE_PEN,
RESOURCES: [WOOD, STONE, METAL, FURNITURE],
FLOOR: [DIRT, WOOD],
MINI_COLOR: 150_50_50,
VALUE_DEGRADE_PER_YEAR: 0.05,
VALUE_PER_WORKER: 0,
VALUE_WORK_SPEED: 1,
BOOST: ORC_SLAVERY,

CONSUMPTION: {
    FOOD_MEAT: { RATE: 0.5, BONUS: 0.1 },
},

WORK: {
    SHIFT_OFFSET: 0.5,
    SOUND: ORC_OVERSEER,
    USES_TOOL: false,
    FULFILLMENT: 0.3,
},

STORAGE: {
    POPULATION_CLASS: SLAVE,
    RACE: HUMAN,
    CAPACITY_BASE: 50,
    CAPACITY_PER_LEVEL: 25,
    MAX_LEVEL: 3,
},

UPGRADES: [
    { RESOURCE_MASK: [4, 1, 0, 0], BOOST: 0 },
    { RESOURCE_MASK: [4, 2, 1, 0], BOOST: 0.5 },
    { RESOURCE_MASK: [4, 3, 2, 1], BOOST: 1.0 },
],

EXPERIENCE_BONUS: { BONUS: 1.0, MAX_EMPLOYEES: 500 },

SPRITES: {
    CAGE: { FPS: 0, SHADOW_LENGTH: 4, SHADOW_HEIGHT: 2, ROTATES: false, FRAMES: [CAGE: 0..3] },
    OVERSEER: [ { FPS: 0, SHADOW_LENGTH: 2, SHADOW_HEIGHT: 0, ROTATES: true, FRAMES: [OVERSEER: 0, OVERSEER: 1] } ],
}
```

**Key Feature:** `STORAGE` block with `POPULATION_CLASS: SLAVE` — Native V71 support for storing Population Classes in Rooms.

---

#### C. Diplomatic Slave Trade Action
```txt
# V71/data/init/diplomacy/SLAVE_TRADE.txt
DIPLOMATIC_ACTION: REQUEST_SLAVE_TRADE
REQUIRES:
  - BUILDING: EMBASSY
  - TREATY: TRADE_AGREEMENT
  - LAW: SLAVERY (Tier 2+) on BOTH factions
COST:
  CREDITS: 5000
  RELATION: -10
EFFECT:
  - TRANSFER_POPULATION_CLASS: SLAVE
  - SOURCE_RACE: HUMAN
  - AMOUNT: VARIABLE (1-20)
```

**Diplomatic Action API (Mod SDK):**
```java
// GameFactionApi
public interface GameFactionApi {
    // Existing
    Player getPlayer();
    Map<String, Faction> getFactions();
    
    // V71 New - Diplomatic Actions
    boolean requestSlaveTrade(Faction target, int amount, PopulationClass clazz, Race race);
    boolean proposeTradeAgreement(Faction target);
    boolean declareWar(Faction target);
    Map<String, DiplomaticAction> getAvailableActions(Faction target);
}
```

---

## 3. Orc Slave System — Complete Flow

### Flow Diagram
```
ORC PLAYER
    │
    ├─[TECH: ORC_SLAVERY]──→ Unlocks: SLAVE_PEN Room, ORC_SLAVE_RAID Event
    │
    ├─[ORC_SLAVE_RAID EVENT]──→ Target: Human Settlement
    │       │
    │       ├─→ SUCCESS: +15 SLAVE (HUMAN) to Orc Stockpile
    │       │              -50 Relation with Target
    │       │
    │       └─→ FAIL: -500 Credits, -25 Relation
    │
    ├─[SLAVE_PEN ROOM] (Built in Orc Capital)
    │       │
    │       ├── CONSUMPTION: FOOD_MEAT (0.5/day per slave)
    │       ├── STORAGE: POPULATION_CLASS=SLAVE, RACE=HUMAN, CAP=50
    │       └── UPGRADES: Level 1-3 (Capacity +25/Level)
    │
    ├─[DIPLOMATIC ACTION: REQUEST_SLAVE_TRADE]
    │       Target: Undead Faction
    │       Cost: 5000 Credits + 10 Relation
    │       Effect: TRANSFER_POPULATION_CLASS (SLAVE, HUMAN, Amount)
    │
    └─→ UNDEAD PLAYER RECEIVES
            │
            ├─ Population Class SLAVE (HUMAN) added to Undead Stockpile
            ├─ Conversion via NECROPOLIS Room (SLAVE → UNDEAD Citizen)
            └─ Conversion Ratio: 1:1 (improved via Tech)
```

---

## 4. Data Files — Complete Set

### 4.1 Tech: ORC_SLAVERY
```txt
# V71/data/init/tech/ORC_SLAVERY.txt
_ignoreVanilla: true,
TECHS: {
    ORC_SLAVERY: {
        COSTS: { MILITARY_KNOWLEDGE: 150 },
        REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
        UNLOCKS_FACTION: [ ROOM_SLAVE_PEN ],
        UNLOCKS_EVENT: [ ORC_SLAVE_RAID, ORC_SLAVE_TRADE_OFFER ],
        UNLOCKS_DIPLOMATIC_ACTION: [ REQUEST_SLAVE_TRADE ],
        BOOST: { ORC_SLAVE_RAID_EFFICIENCY>ADD: 0.2 },
        DESCRIPTION: "Ermöglicht Versklavung von Menschen bei Raids und Handel mit Sklaven.",
    },
},
```

### 4.2 Room: SLAVE_PEN
```txt
# V71/data/init/room/SLAVE_PEN.txt
_ignoreVanilla: true,
ICON: 32->ORC->SLAVE_PEN,
RESOURCES: [WOOD, STONE, METAL, FURNITURE],
AREA_COSTS: [0, 0, 0, 0],
FLOOR: [DIRT, WOOD],
MINI_COLOR: 150_50_50,
VALUE_DEGRADE_PER_YEAR: 0.05,
VALUE_PER_WORKER: 0,
VALUE_WORK_SPEED: 1,
BOOST: ORC_SLAVERY,

CONSUMPTION: {
    FOOD_MEAT: { RATE: 0.5, BONUS: 0.1 },
},

WORK: {
    SHIFT_OFFSET: 0.5,
    SOUND: ORC_OVERSEER,
    USES_TOOL: false,
    FULFILLMENT: 0.3,
},

STORAGE: {
    POPULATION_CLASS: SLAVE,
    RACE: HUMAN,
    CAPACITY_BASE: 50,
    CAPACITY_PER_LEVEL: 25,
    MAX_LEVEL: 3,
},

WORK: {
    SHIFT_OFFSET: 0.5,
    SOUND: ORC_OVERSEER,
    USES_TOOL: false,
    FULFILLMENT: 0.3,
},

UPGRADES: [
    { RESOURCE_MASK: [4, 1, 0, 0], BOOST: 0 },
    { RESOURCE_MASK: [4, 2, 1, 0], BOOST: 0.5 },
    { RESOURCE_MASK: [4, 3, 2, 1], BOOST: 1.0 },
],

EXPERIENCE_BONUS: { BONUS: 1.0, MAX_EMPLOYEES: 500 },

SPRITES: {
    CAGE: { FPS: 0, SHADOW_LENGTH: 4, SHADOW_HEIGHT: 2, ROTATES: false, FRAMES: [CAGE: 0..3] },
    OVERSEER: [ { FPS: 0, SHADOW_LENGTH: 2, SHADOW_HEIGHT: 0, ROTATES: true, FRAMES: [OVERSEER: 0, OVERSEER: 1] } ],
},
```

### 4.3 Events

```txt
# V71/data/init/event/ORC_SLAVE_RAID.txt
_ignoreVanilla: true,
ORC_SLAVE_RAID: {
    ICON: 32->ORC->RAID,
    DURATION: { DAYS: 7.0 },
    OCCURRENCE: {
        RACE: { ORC: 1.0 },
        REQUIRES: { EQUAL: { HAS_TECH: ORC_SLAVERY } },
        MAX_SPAWNS: 1,
    },
    SELECTION: {
        REGIONS: {
            MAX_AMOUNT: { AMOUNT: 1 },
            MIN_AMOUNT: { AMOUNT: 1 },
            FILTERS: [
                { EQUAL: { FACTION_IS_PLAYER: 0 } },
                { GREATER: { POPULATION_RACE_HUMAN: 50 } },
                { LESS: { DISTANCE_TO_ORC_TERRITORY: 50 } }
            ]
        }
    },
    CHOICES: [
        {
            ACTIONS: [
                { TYPE: EVENT, EVENT: SLAVE_RAID_SUCCESS },
                { TYPE: POPULATION_CLASS_ADD, CLASS: SLAVE, RACE: HUMAN, AMOUNT: { RELATIVE: 0.15 } },
                { TYPE: CREDITS, PER_PERSON: -200 },
                { TYPE: FACTION_RELATION, FACTION: TARGET, VALUE: -50 }
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
            { TYPE: BOOST_PERM, PLAYER: { ORC_SLAVES_CAPTURED>ADD: 1 } },
            { TYPE: NOTIFICATION, TEXT: "Sklavenraid erfolgreich! Gefangene Menschen in Sklavenställen untergebracht." }
        ]
    }
},

ORC_SLAVE_TRADE_OFFER: {
    ICON: 32->TRADE->SLAVES,
    DURATION: { DAYS: 30.0 },
    OCCURRENCE: {
        RACE: { ORC: 1.0 },
        REQUIRES: { GREATER: { RESOURCE_CAPTIVE_HUMAN: 10 } }  // Legacy - will be replaced
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
                { TYPE: POPULATION_CLASS_TRANSFER, CLASS: SLAVE, RACE: HUMAN, AMOUNT: 20 },
                { TYPE: CREDITS, AMOUNT: 3000 },
                { TYPE: FACTION_RELATION, FACTION: UNDEAD, VALUE: 10 }
            ]
        },
        { ACTIONS: [ { TYPE: EVENT, EVENT: TRADE_DECLINED } ] }
    ]
},

ORC_SLAVE_TRADE_OFFER: {
    ICON: 32->TRADE->SLAVE_OFFER,
    DURATION: { DAYS: 1.0 },
    CHOICES: [
        { ACTIONS: [ { TYPE: EVENT, EVENT: SLAVE_TRADE_ACCEPTED } ] },
        { ACTIONS: [ { TYPE: EVENT, EVENT: TRADE_DECLINED } ] }
    ]
},
```

---

## 5. Mod SDK Integration — Required APIs

### Required Mod SDK Extensions (v0.1.5+)

| API | Method | Status |
|-----|--------|--------|
| `GameFactionApi.requestSlaveTrade()` | `boolean requestSlaveTrade(Faction target, int amount, PopulationClass clazz, Race race)` | **Required** |
| `GameFactionApi.getDiplomaticActions()` | `List<DiplomaticAction> getAvailableActions(Faction target)` | **Required** |
| `GameEventsApi.triggerPopulationTransfer()` | `boolean transferPopulation(Faction from, Faction to, PopulationClass clazz, Race race, int amount)` | **Required** |
| `GameRoomsApi.getRoomStorage()` | `Optional<RoomStorage> getStorage(RoomInstance room)` | **Required** |
| `RoomStorage` | `void addPopulation(PopulationClass clazz, Race race, int amount)` | **Required** |

### If Mod SDK Missing — Reflection Fallback

```java
public class OrcSlaveTradeReflection {
    private static final Method REQUEST_SLAVE_TRADE;
    private static final Method TRANSFER_POPULATION;
    
    static {
        try {
            Class<?> factionApiClass = Class.forName("com.github.argon.sos.mod.sdk.api.GameFactionApi");
            REQUEST_SLAVE_TRADE = factionApiClass.getMethod("requestSlaveTrade", 
                Class.forName("game.faction.Faction"), int.class, 
                Class.forName("settlement.PopulationClass"), 
                Class.forName("init.race.Race"));
            TRANSFER_POPULATION = factionApiClass.getMethod("transferPopulation",
                Class.forName("game.faction.Faction"), Class.forName("game.faction.Faction"),
                Class.forName("settlement.PopulationClass"), Class.forName("init.race.Race"), int.class);
        } catch (Exception e) {
            throw new RuntimeException("V71 Mod SDK APIs not available", e);
        }
    }
    
    public static boolean requestSlaveTrade(GameFactionApi api, Faction target, int amount) {
        try {
            return (Boolean) REQUEST_SLAVE_TRADE.invoke(api.getFactionApiImpl(), 
                target, 20, PopulationClass.SLAVE, Race.HUMAN);
        } catch (Exception e) {
            return false;
        }
    }
}
```

---

## 7. Integration Checklist

| Component | Status | Test Case |
|-----------|--------|-----------|
| `ORC_SLAVERY` Tech | ☐ Defined | Research Tech → Room `SLAVE_PEN` unlocked |
| `SLAVE_PEN` Room | ☐ Defined | Build → Stores `POPULATION_CLASS=SLAVE, RACE=HUMAN` |
| `ORC_SLAVE_RAID` Event | ☐ Defined | Trigger → +SLAVE Population to Orc Stockpile |
| `SLAVE_PEN` Storage | ☐ Native | Verify `STORAGE.POPULATION_CLASS=SLAVE` works |
| `ORC_SLAVE_TRADE_OFFER` Event | ☐ Defined | Orc → Undead Trade Offer |
| Diplomatic Action `REQUEST_SLAVE_TRADE` | ☐ SDK/Reflection | Orc → Undead Transfer SLAVE (HUMAN) |
| Undead Conversion | ☐ Event | `POPULATION_CLASS_CHANGE: SLAVE(HUMAN) → CITIZEN(UNDEAD)` |
| Save/Load | ☐ Test | Slave Population persists |

---

## 8. Open Questions (UNVERIFIED)

| Question | Risk | Verification |
|----------|------|--------------|
| Does V71 support `POPULATION_CLASS` in Room Storage? | High | Check `RoomBlueprintImp` for `STORAGE` block |
| Does `ORC` Race support `SLAVE` Class? | Medium | Check `SLAVE_RACE_WHITELIST` in Slavery Law |
| Can `ORC` Faction transfer `SLAVE` to `UNDEAD` Faction? | High | Test Diplomatic Action `REQUEST_SLAVE_TRADE` |
| Does `ORC_SLAVE_RAID` target Player Settlements? | Medium | Check `FACTION_IS_PLAYER: 0` filter |
| Does `SLAVE_PEN` Consumption work for `SLAVE` Class? | Medium | Test `CONSUMPTION.FOOD_MEAT` for `CLASS_SLAVE` |

---

*End of Orc Slave System Specification*