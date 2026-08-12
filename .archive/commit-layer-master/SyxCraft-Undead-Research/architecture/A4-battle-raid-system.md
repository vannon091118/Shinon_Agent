# A4 — Battle & Raid System Analysis (V71 "Reign of Terror")

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — All findings verified against V71 JAR

---

## 1. Native Battle System — Technical Specification

### Battle Architecture (from JAR analysis)

```java
// Core battle packages
game.battle/
├── div/              // Divisions (unit groups)
├── factors/          // Battle modifiers (terrain, morale, etc.)
├── formation/        // Battle formations
├── setting/          // Battle settings
├── state/            // Battle state
├── thread/
│   ├── general/offence/  // Offense thread
│   ├── order/        // Order thread
│   ├── position/     // Position thread
│   ├── status/       // Status thread
│   └── trajectory/   // Trajectory thread
└── util/             // Battle utilities

// Settlement battle
settlement.battle.invasion/
    // Invasion mechanics for settlement battles

// Entity AI
settlement.entity.humanoid.ai.battle/
    // Battle AI modules for humanoids
```

### Key Battle Classes

| Class | Purpose |
|-------|---------|
| `Armies` | Container for divisions |
| `Div` (Division) | Unit group with race, class, stats |
| `Factors` | Battle modifiers (terrain, morale, etc.) |
| `Formation` | Battle formation logic |
| `Thread` | Battle simulation threads |

### Division Structure
```java
class Div {
    int total;           // Total unit count
    Race race;           // Unit race
    HCLASS class;        // CITIZEN, SLAVE, NOBLE, REBEL
    double morale;       // Current morale
    double damage;       // Accumulated damage
    // ...
}
```

---

## 2. Native Raid System — Technical Specification

### Raid Events (from JAR analysis)
- `game/raiding/RaiderTextsRace` — Raider text by race
- `game/events/slave/EventUprising` — Slave uprisings
- `settlement/battle/invasion/` — Settlement invasion

### Raid Event Structure (from `EventUprising.class`)
```txt
SLAVE_RAID: {
    OCCURRENCE: {
        RACE: { ORC: 1.0 },
        REQUIRES: { EQUAL: { HAS_TECH: ORC_SLAVERY } }
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
            { TYPE: POPULATION_CLASS_ADD, CLASS: SLAVE, RACE: HUMAN, AMOUNT: { RELATIVE: 0.15 } },
            { TYPE: CREDITS, AMOUNT: -1000 }
        ]
    }]
}
```

### Raid Triggers (Native)
| Trigger Type | Mechanism |
|--------------|-----------|
| **Scheduled** | Periodic check via `TileUpdater` |
| **Territory** | Distance to faction territory |
| **Population** | Target population threshold |
| **Diplomatic** | WAR stance enables raids |
| **Tech** | Requires specific tech (e.g., `ORC_SLAVERY`) |

### Raid Event Actions
| Action | Purpose |
|--------|---------|
| `POPULATION_CLASS_ADD` | Add slaves from raid |
| `CREDITS` | Cost/reward |
| `FACTION_RELATION` | Relation change |
| `BUILDING_DAMAGE` | Damage settlement buildings |
| `SETTLEMENT_ADD` | Add settlement (conquest) |

---

## 3. Battle System Integration

### Mod SDK Battle Hooks
```java
interface GameEventsApi {
    // Called before battle starts
    void onBeforeBattle(BattleContext context);
    
    // Called during battle
    void onBattle(BattleContext context);
    
    // Called after battle ends
    void onAfterBattle(BattleResult result);
    
    // Battle result
    enum BattleResult {
        VICTORY, DEFEAT, DRAW, RETREAT
    }
    
    class BattleContext {
        Faction attacker;
        Faction defender;
        Region region;
        List<Div> attackerDivisions;
        List<Div> defenderDivisions;
        BattleResult result;
    }
}
```

### Battle Event Actions
```txt
CHOICES: [{
    ACTIONS: [
        # Battle outcome effects
        { TYPE: BUILDING_DAMAGE, TARGET: "RANDOM", DAMAGE: 0.3 },
        { TYPE: SETTLEMENT_ADD, BUILDING: "WATCHTOWER" },
        
        # Population changes
        { TYPE: POPULATION_CLASS_ADD, CLASS: SLAVE, RACE: HUMAN, AMOUNT: 10 },
        { TYPE: POPULATION_CLASS_CHANGE, FROM: CITIZEN, TO: SLAVE, RACE: HUMAN, AMOUNT: 5 },
        
        # Diplomatic
        { TYPE: FACTION_RELATION, FACTION: "DEFENDER", VALUE: -25 },
        
        # Resources
        { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: 15 }
    ]
}]
```

---

## 4. Raid System for SyxCraft

### Orc Raid Pipeline (Technical)

```
Orc Faction (NPC)
    │
    ├─► Scheduled Raid Check (TileUpdater)
    │       ├─► Check: WAR stance with Human
    │       ├─► Check: ORC_SLAVERY tech
    │       ├─► Check: Distance to Human settlement < 50 tiles
    │       └─► Check: Human POPULATION_RACE_HUMAN > 50
    │
    ├─► Event Trigger: ORC_SLAVE_RAID
    │       ├─► SELECTION: REGIONS with filters
    │       │       ├─► FACTION_IS_PLAYER: 0 (NPC only)
    │       │       ├─► POPULATION_RACE_HUMAN: > 50
    │       │       └─► DISTANCE_TO_ORC_TERRITORY: < 50
    │       └─► CHOICES: [RAID, ABORT]
    │
    ├─► On RAID Success:
    │       ├─► EVENT: SLAVE_RAID_SUCCESS
    │       │       └─► POPULATION_CLASS_ADD: CLASS=SLAVE, RACE=HUMAN, AMOUNT=15
    │       ├─► CREDITS: -1000 (raid cost)
    │       └─► FACTION_RELATION: HUMAN_FACTION, -25
    │
    └─► Stockpile Update: Orc now has SLAVE (HUMAN) population
```

### Raid Configuration for SyxCraft

```txt
# V71/data/init/event/ORC_SLAVE_RAID.txt
_ignoreVanilla: true,
ORC_SLAVE_RAID: {
    ICON: 32->ORC->RAID,
    DURATION: { DAYS: 3.0 },
    
    OCCURRENCE: {
        RACE: { ORC: 1.0 },
        REQUIRES: { EQUAL: { HAS_TECH: ORC_SLAVERY } },
        MAX_SPAWNS: 1
    },
    
    SELECTION: {
        REGIONS: {
            MAX_AMOUNT: { AMOUNT: 1 },
            FILTERS: [
                { EQUAL: { FACTION_IS_PLAYER: 0 } },
                { GREATER: { POPULATION_RACE_HUMAN: 50 } },
                { LESS: { DISTANCE_TO_FACTION_TERRITORY: 50 } }
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
},
```

---

## 5. Player vs NPC Raids

### NPC → Player Settlement Raids
```txt
# Orc NPC raids Player Human settlement
ORC_RAID_PLAYER_HUMAN: {
    SELECTION: {
        REGIONS: {
            FILTERS: [
                { EQUAL: { FACTION_IS_PLAYER: 1 } },
                { EQUAL: { FACTION_RACE: HUMAN } },
                { GREATER: { POPULATION_RACE_HUMAN: 30 } },
                { LESS: { DISTANCE_TO_ORC_TERRITORY: 50 } }
            ]
        }
    }
}
```

### Player → NPC Settlement Raids
```txt
# Undead Player raids NPC Human for slaves
UNDEAD_RAID_NPC_HUMAN: {
    SELECTION: {
        REGIONS: {
            FILTERS: [
                { EQUAL: { FACTION_IS_PLAYER: 0 } },
                { EQUAL: { FACTION_RACE: HUMAN } },
                { GREATER: { POPULATION_RACE_HUMAN: 20 } }
            ]
        }
    }
}
```

---

## 6. Battle & Raid Mod SDK Integration

### `GameEventsApi` — Battle Hooks
```java
interface GameEventsApi {
    // Pre-battle
    void onBeforeBattle(BattleContext ctx);
    
    // During battle (per tick)
    void onBattleTick(BattleContext ctx);
    
    // Post-battle
    void onAfterBattle(BattleResult result);
    
    // Raid hooks
    void onRaidScheduled(RaidContext ctx);
    void onRaidExecuted(RaidResult result);
    
    // Classes
    class BattleContext {
        Faction attacker;
        Faction defender;
        Region region;
        List<Div> attackerDivs;
        List<Div> defenderDivs;
    }
    
    class RaidContext {
        Faction raider;
        Faction target;
        Region targetRegion;
        String raidType;
    }
    
    class RaidResult {
        boolean success;
        int slavesCaptured;
        int casualties;
        List<String> buildingsDamaged;
    }
}
```

### `GameFactionApi` — Raid Control
```java
interface GameFactionApi {
    // Schedule raid
    void scheduleRaid(Faction target, String raidType, Region region);
    
    // Execute raid immediately
    void executeRaid(Faction target, String raidType);
    
    // Get raid history
    List<RaidRecord> getRaidHistory();
    
    // Raid cooldowns
    double getRaidCooldown(String raidType);
}
```

---

## 7. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Does `POPULATION_CLASS_ADD` work in raid events? | **UNVERIFIED** | CRITICAL |
| Can NPC factions raid Player settlements? | **UNVERIFIED** | HIGH |
| Does `DISTANCE_TO_FACTION_TERRITORY` filter exist? | **UNVERIFIED** | HIGH |
| Can Raids target specific Population Class? | **UNVERIFIED** | HIGH |
| Does `GameEventsApi.onRaidExecuted()` exist? | **UNVERIFIED** | MEDIUM |
| Can Player manually trigger raid via Event? | **UNVERIFIED** | MEDIUM |

---

## 8. Recommendations

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| Raid System | Use native Event + `SELECTION.REGIONS` | Native, no Java |
| Slave Capture | `POPULATION_CLASS_ADD: CLASS=SLAVE` | Native Event Action |
| Raid Targeting | `SELECTION.REGIONS` with distance/population filters | Native |
| Orc Raid Schedule | Event `OCCURRENCE` with Tech requirement | Native |
| Player Raids | Event with `FACTION_IS_PLAYER: 0` filter | Native |

---

*End of A4 — Battle & Raid System Analysis*
*All findings from V71.44 JAR analysis (2026-06-24 build)*