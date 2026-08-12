# C1 — Orc-Undead Slave Pipeline (End-to-End)

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — Technical Specification

---

## 1. Pipeline Overview

```
ORC RAID ON HUMAN
       │
       ▼
SLAVE CAPTURE (Population Class)
       │
       ▼
ORC STOCKPILE: SLAVE (HUMAN)
       │
       ▼
DIPLOMATIC ACTION: REQUEST_SLAVE_TRADE
       │
       ▼
POPULATION_CLASS_TRANSFER: ORC → UNDEAD
       │
       ▼
UNDEAD STOCKPILE: SLAVE (HUMAN)
       │
       ▼
EVENT: UNDEAD_CONVERSION
       │
       ▼
POPULATION_CLASS_CHANGE: SLAVE → CITIZEN (UNDEAD)
       │
       ▼
UNDEAD POPULATION +1
```

---

## 2. Step-by-Step Technical Implementation

### Step 1: Orc Raid on Human Settlement

**Trigger:** Orc NPC Faction (or Player Orc) raids Human Settlement

**Mechanism:** Native Event `ORC_SLAVE_RAID`

```txt
# V71/data/init/event/ORC_SLAVE_RAID.txt
_ignoreVanilla: true,
ORC_SLAVE_RAID: {
    ICON: 32->ORC->RAID,
    DURATION: { DAYS: 3.0 },
    
    OCCURRENCE: {
        RACE: { ORC: 1.0 },
        REQUIRES: { EQUAL: { HAS_TECH: ORC_RAIDING } },
        MAX_SPAWNS: 1
    },
    
    SELECTION: {
        REGIONS: {
            MAX_AMOUNT: { AMOUNT: 1 },
            FILTERS: [
                { EQUAL: { FACTION_IS_PLAYER: 0 } },        // NPC Only
                { EQUAL: { FACTION_RACE: HUMAN } },          // Human Faction
                { GREATER: { POPULATION_RACE_HUMAN: 50 } },  // Min 50 Humans
                { LESS: { DISTANCE_TO_ORC_TERRITORY: 50 } }  // Near Orc
            ]
        }
    },
    
    CHOICES: [
        {
            ACTIONS: [
                { TYPE: EVENT, EVENT: ORC_SLAVE_RAID_SUCCESS },
                { TYPE: POPULATION_CLASS_ADD, CLASS: SLAVE, RACE: HUMAN, AMOUNT: 15 },
                { TYPE: CREDITS, AMOUNT: -1000 },
                { TYPE: FACTION_RELATION, FACTION: TARGET, VALUE: -25 }
            ]
        },
        {
            ACTIONS: [ { TYPE: EVENT, EVENT: ORC_SLAVE_RAID_ABORT } ]
        }
    ]
},

ORC_SLAVE_RAID_SUCCESS: {
    ICON: 32->ORC->SUCCESS,
    DURATION: { DAYS: 30.0 },
    ON_SPAWN: {
        ACTIONS: [
            { TYPE: POPULATION_CLASS_ADD, CLASS: SLAVE, RACE: HUMAN, AMOUNT: 15 },
            { TYPE: BOOST_PERM, PLAYER: { ORC_SLAVES_CAPTURED>ADD: 15 } }
        ]
    }
}
```

**Result:** Orc Faction gains 15 SLAVE (HUMAN) population in their stockpile.

---

### Step 2: Orc Stockpile Management

**Mechanism:** Native Faction Stockpile tracks `SLAVE` Population Class

```java
// GameFactionApi
int slaveCount = apis.faction().getPopulation(PopulationClass.SLAVE, Race.HUMAN);
// Returns SLAVE (HUMAN) count for this faction
```

**No Java needed** — Native stockpile system handles this.

---

### Step 3: Diplomatic Slave Trade (Orc → Undead)

**Mechanism:** Custom Diplomatic Action `REQUEST_SLAVE_TRADE`

```txt
# V71/data/init/diplomacy/REQUEST_SLAVE_TRADE.txt
_ignoreVanilla: true,
DIPLOMATIC_ACTIONS: {
    REQUEST_SLAVE_TRADE: {
        NAME: "Sklavenhandel anbieten",
        REQUIRES_STANCE: PACT,
        REQUIRES_LAW: [ ORC_SLAVERY, UNDEAD_SLAVERY ],
        REQUIRES_BUILDING: [ EMBASSY ],
        MAX_PER_YEAR: 4,
        
        COST: {
            GP: 200,
            CREDITS: 1000,
            RELATION: -0.5
        },
        
        EFFECTS: {
            POPULATION_CLASS_TRANSFER: {
                FROM_FACTION: ORC,
                TO_FACTION: UNDEAD,
                CLASS: SLAVE,
                RACE: HUMAN,
                AMOUNT: 20
            },
            CREDITS_TRANSFER: {
                FROM: UNDEAD,
                TO: ORC,
                AMOUNT: 3000
            },
            ESSENCE_TRANSFER: {
                FROM: UNDEAD,
                TO: ORC,
                AMOUNT: 5
            },
            FACTION_RELATION: { TARGET: 10 }
        },
        
        DESCRIPTION: "Orks verkaufen gefangene menschliche Sklaven an Untote gegen Credits und Essenz."
    }
}
```

**Mod SDK Execution:**
```java
// In OrcTradeManager (Undead Module) or Orc Module
public void offerSlaveTrade() {
    Faction orcFaction = getOrcFaction();
    Faction undeadFaction = getUndeadFaction();
    
    if (orcFaction == null || undeadFaction == null) return;
    
    // Check stance
    if (apis.faction().getStance(orcFaction, undeadFaction) != DipStance.PACT) return;
    
    // Check laws
    if (!apis.faction().hasLaw(orcFaction, "ORC_SLAVERY")) return;
    if (!apis.faction().hasLaw(undeadFaction, "UNDEAD_SLAVERY")) return;
    
    // Check stockpile
    int availableSlaves = apis.faction().getPopulation(orcFaction, PopulationClass.SLAVE, Race.HUMAN);
    if (availableSlaves < 20) return;
    
    // Execute Diplomatic Action
    apis.faction().executeDiplomaticAction("REQUEST_SLAVE_TRADE", orcFaction, undeadFaction);
}
```

---

### Step 4: Population Class Transfer

**Native Event Action:**
```txt
{ TYPE: POPULATION_CLASS_TRANSFER, 
  FROM_FACTION: "ORC_FACTION",
  TO_FACTION: "UNDEAD_FACTION", 
  CLASS: "SLAVE", 
  RACE: "HUMAN", 
  AMOUNT: 20 }
```

**Engine Effect:**
- Orc Faction: SLAVE(HUMAN) -= 20
- Undead Faction: SLAVE(HUMAN) += 20
- Automatic stockpile update

---

### Step 5: Undead Conversion Event

**Mechanism:** Native Event `UNDEAD_CONVERSION`

```txt
# V71/data/init/event/UNDEAD_CONVERSION.txt
_ignoreVanilla: true,
UNDEAD_CONVERSION: {
    ICON: 32->UNDEAD->CONVERT,
    DURATION: { DAYS: 1.0 },
    
    OCCURRENCE: {
        RACE: { UNDEAD: 1.0 },
        REQUIRES: { 
            EQUAL: { 
                BOOST_UNDEAD_GATE_CONVERSION: 1 
            },
            GREATER: { 
                POPULATION_CLASS_SLAVE_HUMAN: 10,
                RESOURCE_ESSENCE: 1 
            }
        }
    },
    
    TAGS: { ALLOW_NOT: [ CHAIN_ONGOING ] },
    
    SELECTION: {
        SUBJECTS: {
            USE_AS_ICON: true,
            FILTERS: [ { EQUAL: { CLASS_SLAVE: 1, RACE: HUMAN } } ],
            MAX_AMOUNT: { RELATIVE: 0.1 }
        }
    },
    
    CHOICES: [
        {
            ACTIONS: [
                { TYPE: POPULATION_CLASS_CHANGE, FROM: SLAVE, TO: CITIZEN, RACE: UNDEAD, AMOUNT: { RELATIVE: 0.1 } },
                { TYPE: EVENT, EVENT: UNDEAD_RISE },
                { TYPE: POPULATION_CLASS_ADD, CLASS: SLAVE, RACE: HUMAN, AMOUNT: { RELATIVE: -0.1 } },
                { TYPE: RESOURCE_ADD, RESOURCE: ESSENCE, AMOUNT: -1 },
                { TYPE: BOOST_PERM, PLAYER: { UNDEAD_CONVERSION_COOLDOWN>SET: 1 } }
            ]
        },
        {
            ACTIONS: [ { TYPE: EVENT, EVENT: CONVERSION_CANCELLED } ]
        }
    ]
}
```

**Key Actions:**
1. `POPULATION_CLASS_CHANGE` — SLAVE(HUMAN) → CITIZEN(UNDEAD)  ← **Core mechanic**
2. `POPULATION_CLASS_ADD` (negative) — Remove SLAVE from stockpile
3. `RESOURCE_ADD` ESSENCE -1 — Cost
4. `BOOST_PERM` — Cooldown flag

---

## 3. Law Requirements

### Required Laws (V71)

| Law | Tier | Category | Purpose |
|-----|------|----------|---------|
| `ORC_SLAVERY` | 1 | Criminal | Enables Orc slave raids & trade |
| `UNDEAD_SLAVERY` | 1 | Criminal | Enables Undead slave ownership |
| `UNDEAD_CONVERSION` | 2 | Criminal | Enables Conversion Event |
| `HUMAN_FARM_MANAGEMENT` | 2 | Civic | Unlocks World Human Farm |

### Law Definitions

```txt
# UNDEAD_SLAVERY.txt
_ignoreVanilla: true,
LAWS: {
    UNDEAD_SLAVERY: {
        CATEGORY: CRIMINAL,
        TIER: 1,
        GP_COST: 500,
        REQUIRES_BUILDING: [ COURTHOUSE ],
        EFFECTS: {
            SLAVERY_ENABLED>SET: 1,
            SLAVE_RACE_WHITELIST>ADD: [ HUMAN ],
            SLAVE_PRICE_BASE>SET: 500,
        },
        DESCRIPTION: "Ermöglicht Versklavung von Menschen."
    },
}

# UNDEAD_CONVERSION.txt
_ignoreVanilla: true,
LAWS: {
    UNDEAD_CONVERSION: {
        CATEGORY: CRIMINAL,
        TIER: 2,
        GP_COST: 1000,
        REQUIRES_LAW: [ UNDEAD_SLAVERY ],
        UNLOCKS_EVENT: [ UNDEAD_CONVERSION ],
        EFFECTS: {
            CONVERSION_ENABLED>SET: 1,
            CONVERSION_RATIO>SET: 1.0,
            CONVERSION_ESSENCE_COST>SET: 1,
            CONVERSION_COOLDOWN_DAYS>SET: 30,
        },
        DESCRIPTION: "Ermöglicht Konvertierung menschlicher Sklaven zu Untoten Bürgern."
    },
}
```

---

## 4. Tech Tree Integration

### Orc Tech
```txt
# ORC_RAIDING.txt
_ignoreVanilla: true,
TECHS: {
    ORC_RAIDING: {
        COST: { CIVIC: 200, MILITARY: 300 },
        REQUIRES: { BASIC_MINING: 1 },
        UNLOCKS_LAW: [ ORC_SLAVERY ],
        UNLOCKS_EVENT: [ ORC_SLAVE_RAID ],
        UNLOCKS_ROOM: [ ORC_SLAVE_PEN ],
        DESCRIPTION: "Ermöglicht Sklaven-Raids auf menschliche Siedlungen."
    },
}
```

### Undead Tech
```txt
# NECROMANCY_HUMAN_FARM.txt
_ignoreVanilla: true,
TECHS: {
    NECROMANCY_HUMAN_FARM: {
        COST: { CIVIC: 200, OCCULT: 300 },
        REQUIRES: { BASIC_MINING: 1 },
        UNLOCKS_LAW: [ UNDEAD_CONVERSION, HUMAN_FARM_MANAGEMENT ],
        UNLOCKS_EVENT: [ FOUND_HUMAN_FARM ],
        UNLOCKS_WORLD_BUILDING: [ WORLD_HUMAN_FARM ],
        DESCRIPTION: "Ermöglicht Errichtung von Menschenfarmen."
    },
}
```

---

## 5. Pipeline State Tracking

### Orc Side
```java
class OrcTradeState {
    int slavesAvailable = 0;
    int slavesTradedThisYear = 0;
    long lastTradeTime = 0;
    
    void onRaidSuccess(int count) {
        slavesAvailable += count;
    }
    
    boolean canTrade() {
        return slavesAvailable >= 20 
            && slavesTradedThisYear < 4
            && System.currentTimeMillis() - lastTradeTime > YEAR_IN_MILLIS / 4;
    }
}
```

### Undead Side
```java
class UndeadConversionState {
    double conversionCooldown = 0; // days
    int totalConversions = 0;
    double conversionRatio = 1.0; // 1:1 base
    
    boolean canConvert() {
        return conversionCooldown <= 0 
            && apis.faction().getPopulation(PopulationClass.SLAVE, Race.HUMAN) >= 10
            && apis.faction().getResourceAmount("ESSENCE") >= 1;
    }
}
```

---

## 6. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Funktioniert `POPULATION_CLASS_TRANSFER` cross-faction? | **UNVERIFIED** | CRITICAL |
| Kann NPC Faction Diplomat Action ausführen? | **UNVERIFIED** | CRITICAL |
| Functioniert `POPULATION_CLASS_CHANGE` SLAVE→CITIZEN mit RACE Change? | **UNVERIFIED** | CRITICAL |
| Werden Diplomatic Actions in Data Files geladen? | **UNVERIFIED** | HIGH |
| Muss `EMBASSY` gebaut sein für Diplomatic Action? | **UNVERIFIED** | HIGH |
| Functioniert `FROM_FACTION` / `TO_FACTION` in Event Action? | **UNVERIFIED** | CRITICAL |

---

## 7. Recommendations

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| Raid System | Native Event + `POPULATION_CLASS_ADD` | No Java needed |
| Slave Storage | Native Faction Stockpile (Population Class) | Built-in |
| Trade | Custom Diplomatic Action + `POPULATION_CLASS_TRANSFER` | Native V71 |
| Conversion | Event with `POPULATION_CLASS_CHANGE` | Core mechanic |
| Law Gates | `UNLOCKS_EVENT`, `UNLOCKS_LAW` in Tech | Clean progression |

---

*End of C1 — Orc-Undead Slave Pipeline Analysis*
*All findings from V71.44 analysis and Mod SDK review*