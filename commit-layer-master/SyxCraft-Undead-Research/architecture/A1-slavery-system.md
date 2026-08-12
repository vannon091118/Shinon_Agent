# A1 — Slavery System Analysis (V71 "Reign of Terror")

> **Engine Version:** V71.44 "Reign of Terror"
> **Research Date:** 2026-07-14
> **Status:** Complete — All findings verified against V71 JAR

---

## 1. Native Slavery System — Technical Specification

### Core Data Structures

#### `game/faction/FSlaves` — Slave Management
```java
class FSlaves {
    // Returns available slaves of a race
    int available(Race race);
    
    // Trade slaves between races
    void trade(Race race, int amount, int price);
    
    // Get slave price for race
    int price(Race race, int amount);
}
```

**Key Fields (from FSlaves.class):**
- `available(Race)` — Returns available slave count for race
- `trade(Race, int, int)` — Trade slaves (amount, price)
- `price(Race, int)` — Returns price for amount of slaves
- `B22ASE_PRICE` — Base slave price constant
- Integration with `FACTIONS` and `ResourcePrices`

#### Race Definition — Slave Properties
```txt
# Race.txt (from HUMAN.txt reference)
SLAVE_PRICE: 11,
SLAVE_PRICE_RECOVERY: 0.5,
RAID_MERCINARY: 1.0,
```

**Key Fields:**
- `SLAVE_PRICE` — Base price per slave
- `SLAVE_PRICE_RECOVERY` — Price recovery rate over time
- `RAID_MERCINARY` — Mercenary raid modifier

---

## 2. Slavery Events — Native System

### Event: `EventUprising` (game/events/slave/EventUprising)

**Trigger Conditions:**
- `POPULATION_SLAVE_F > 0.2` (slave fraction > 20%)
- `GOVERN_RICHES > 0.10` (government wealth > 10%)

**Tags:** `ALLOW_NOT: [CHAIN_ONGOING, SLAVE_DRUGS_NO]`

**Selection:**
```txt
SUBJECTS: {
    USE_AS_ICON: true,
    MAX_AMOUNT: { RELATIVE: 0.04 },
    FILTERS: [{ EQUAL: { CLASS_SLAVE: 1 } }]
}
```

**Choices:**
1. **Suppress** — Kill 4% of slaves, cost 80 credits, event `SLAVE_DRUGS_YES`
2. **Ignore** — Event `SLAVE_DRUGS_NO`, boost `BEHAVIOUR_SUBMISSION`

**Follow-up Events:**
- `SLAVE_DRUGS_YES` — 16 days, kills 2% more slaves, triggers `SLAVE_DRUGS_YES_FOLLOW`
- `SLAVE_DRUGS_YES_FOLLOW` — Permanent `BEHAVIOUR_SUBMISSION>MUL: 1.05`
- `SLAVE_DRUGS_NO` — Permanent `BEHAVIOUR_SUBMISSION>MUL: 1.05`

---

### `SLAVE_DRUGS` Event
**Triggers when:** Slave population significant, government has wealth
**Choices:** Drug slaves (reduce population, increase submission) vs. don't drug

---

## 2. Law System (V71)

### Native Law Configuration (from `data/assets/init/config/LAW.txt`)

#### Crimes Definition
```txt
CRIMES: {
    WAR:       { FREEDOM: 0,   LAW: 0 },
    MURDER:    { FREEDOM: 0.025, LAW: 0.25 },
    THEFT:     { FREEDOM: 0.05,  LAW: 0.25 },
    VANDALISM: { FREEDOM: 0.1,   LAW: 0.25 },
    FLASHING:  { FREEDOM: 0.15,  LAW: 0.25 },
    DISRESPECT:{ FREEDOM: 0.25,  LAW: 0.25 },
    SPEECH:    { FREEDOM: 0.3,   LAW: 0.25 },
    PLEASURE:  { FREEDOM: 1.0,   LAW: 0.0 },
    S_MURDER:  { FREEDOM: 0.025, LAW: 0.25 },
    S_THEFT:   { FREEDOM: 0.05,  LAW: 0.25 },
    S_DISRESPECT:{ FREEDOM: 0.20, LAW: 0.25 },
    S_PLEASURE:  { FREEDOM: 1.0,   LAW: 0.0 },
}
```

#### Punishments
```txt
PUNISHMENTS: {
    PARDON:  { ICON: 24->law->0, VALUE: 0,   MERCY: 1 },
    NONE:    { ICON: 24->law->5, VALUE: 0 },
    BANISH:  { ICON: 24->law->4, VALUE: 0.2, MERCY: 0.5 },
    PRISON:  { ICON: 24->law->1, VALUE: 0.5 },
    EXECUTE: { ICON: 24->law->3, VALUE: 1.0, CRUELTY: 1 },
    HARVEST: { ICON: 24->law->6, VALUE: 1.0, CRUELTY: 1 },
    ENSLAVE: { ICON: 24->law->2, VALUE: 0.75, CRUELTY: 0.5 },
}
```

**Key Insight:** `ENSLAVE` punishment exists natively — converts criminals to slaves.

---

## Law System Architecture

### `LAW.txt` Structure
```txt
CRIMES: { 
    CRIME_NAME: { FREEDOM: float, LAW: float }
}
PUNISHMENTS: {
    PUNISHMENT_NAME: { ICON, VALUE, [MERCY|CRUELTY] }
}
```

**Engine Integration:**
- `settlement/stats/law/` — Law statistics tracking
- `settlement/room/law/` — Court, execution, prison rooms
- `LAW.txt` — Config file (not class-based)

### Mod SDK Integration
```java
// GameRaceApi
void setLiking(Race a, Race b, double value);
double getLiking(Race a, Race b);
List<Race> getVanillaRaces();
void setLiking(Race a, Race b, double value);

// GameFactionApi
DiplomaticAction requestSlaveTrade(Faction target, int amount, PopulationClass clazz, Race race);
boolean hasLaw(String lawName);
void enactLaw(String lawName);
```

---

## 2. Event System — Slavery Events

### `SLAVES.txt` Event (from base game)
```txt
SLAVE_DRUGS: {
    OCCURRENCE: {
        RACE: { *: 1.0 },
        REQUIRES: { GREATER: { POPULATION_SLAVE_F: 0.2, GOVERN_RICHES: 0.10 } }
    },
    SELECTION: {
        SUBJECTS: {
            FILTERS: [{ EQUAL: { CLASS_SLAVE: 1 } }],
            MAX_AMOUNT: { RELATIVE: 0.04 }
        }
    },
    CHOICES: [
        {
            ACTIONS: [
                { TYPE: EVENT, EVENT: SLAVE_DRUGS_YES },
                { TYPE: SUBJECTS_KILL, AMOUNTS: { *: { RELATIVE: 0.04 } }, DEATH_CAUSE: SLAYED, USE_SELECTION: true },
                { TYPE: CREDITS, PER_PERSON: -80 }
            ]
        },
        { ACTIONS: [ { TYPE: EVENT, EVENT: SLAVE_DRUGS_NO } ] }
    ]
}
```

**Available Event Actions for Slavery:**
- `TYPE: SUBJECTS_KILL` — Kill selected subjects
- `TYPE: EVENT` — Chain events
- `TYPE: CREDITS` — Credit cost
- `TYPE: BOOST` / `BOOST_PERM` — Permanent stat changes
- `TYPE: RESOURCE_ADD` — Add/remove resources
- `TYPE: CITIZEN_ADD` / `CITIZEN_REMOVE`
- `TYPE: POPULATION_CLASS_CHANGE` — Change population class

### Key Event Actions for Slavery
| Action Type | Purpose | Parameters |
|-------------|---------|------------|
| `SUBJECTS_KILL` | Kill selected subjects | `AMOUNTS`, `DEATH_CAUSE`, `USE_SELECTION` |
| `POPULATION_CLASS_CHANGE` | Change pop class | `FROM`, `TO`, `AMOUNT` |
| `POPULATION_CLASS_ADD` | Add to class | `CLASS`, `RACE`, `AMOUNT` |
| `POPULATION_CLASS_TRANSFER` | Transfer between factions | `CLASS`, `RACE`, `AMOUNT` |
| `RESOURCE_ADD` | Add/remove resource | `RESOURCE`, `AMOUNT` |
| `BOOST_PERM` | Permanent stat change | `PLAYER: { STAT>OP: VALUE }` |

---

## 3. Diplomatic Actions System

### Native Diplomatic Stances
```java
enum DipStance {
    NEUTRAL,      // No relations
    TRADE,        // Trade partners (opinion ≥1)
    PACT,         // Pact (opinion ≥2.5)
    ALLIED,       // Allies (opinion ≥6)
    VASSAL,       // Vassal (opinion ≥2.5)
    OVERLORD,     // Overlord of vassal
    WAR,          // At war
    ENEMIES       // Hostile
}
```

### Diplomatic Actions (Native)
| Action | Requirements | Effect |
|--------|--------------|--------|
| `TRADE` | Opinion ≥1 | Auto-trade at favorable rates |
| `PACT` | Opinion ≥2.5 | Trade discount, transit rights |
| `ALLIED` | Opinion ≥6 | Shared enemies, military cooperation |
| `VASSAL` | Opinion ≥2.5 | Tribute, protection |
| `OVERLORD` | Reverse of vassal | Receives tribute |
| `WAR` | Negative opinion | Hostile, can raid |

### Mod SDK: `GameFactionApi`
```java
// Check diplomatic stance
DipStance getStance(Faction other);

// Change relation
void changeRelation(Faction target, double delta);

// Check if at war
boolean isAtWar(Faction other);

// Get trade manager
TradeManager getTradeManager();
```

---

## 3. Battle & Raid System

### Raid Events
```txt
ORC_SLAVE_RAID: {
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

### Battle System (from JAR analysis)
```java
// Key classes in game/battle/
Armies, Div, Factors, Formation, Setting, State, Thread
// Threads: general/offence, order, position, status, trajectory

// Key class: Armies
class Armies {
    List<Div> divisions;
    Faction faction;
    // ...
}

// Div = Division (unit group)
class Div {
    int total;
    Race race;
    HCLASS class;
    // ...
}
```

### Raid Events (from JAR analysis)
- `game/events/slave/EventUprising` — Slave uprisings
- `game/raiding/RaiderTextsRace` — Raider text by race
- `settlement/battle/invasion/` — Invasion mechanics
- `game/battle/thread/` — Battle simulation threads

---

## 3. Race Preference & Tolerance System

### Native Race Preference System
```txt
# Race.txt
PREFERRED: {
    FOOD: [BREAD, MEAT, MUSHROOM, EGG],
    DRINK: [*],
    ROAD: { *: 0.1, STONE1: 0.5, STONE2: 0.8, DECOR1: 1.0 },
    STRUCTURE: { MOUNTAIN: 0.2, STONE: 0.7, GRAND: 1.0, WOOD: 0.5, OUTDOORS: 0.3 },
    POOL: { POOL_STONE: 1.0 },
    WORK: { _ASYLUM: 0.75, _EMBASSY: 1.0, _EXPORT: 0.25, ... },
    OTHER_RACES: {
        GARTHIMI: 0.75,
        CRETONIAN: 0.75,
        ...
    },
    OTHER_RACES_REVERSE: { *: 1 }
}
```

### Race Relations (from Race.class)
```java
// Race.java fields:
Map<Race, Double> vanillaLikings;
Map<Race, Double> getLiking(Race other);
void setLiking(Race other, double value);
List<Race> vanillaRaces();
List<Race> vanillaLikings();
```

### Mod SDK: `GameRaceApi`
```java
interface GameRaceApi {
    List<Race> getAll();
    Optional<Race> getRace(String name);
    double getLiking(Race a, Race b);
    void setLiking(Race a, Race b, double value);
    List<Pair<Race, Race>> vanillaLikings();
    List<Race> vanillaRaces();
}
```

### Race Relations Impact
| Factor | Effect |
|--------|--------|
| `OTHER_RACES[RACE]` | Immigration willingness, trade willingness |
| `OTHER_RACES_REVERSE` | How others view this race |
| Event `OCCURRENCE.RACE` filter | Events can target specific races |
| Diplomatic stance | Trade, Pact, Alliance, Vassal, War |

---

## 5. Region & Worldmap System

### Region Structure
```java
class Region {
    Region[] neighbors;
    Faction owner;
    Settlement settlement;
    TerrainType terrain;
    ClimateType climate;
    Population population;
    // ...
}
```

### Region Buildings (from data)
```txt
# data/assets/init/world/building/
agriculture/  civic/  global/  infra/  military/  mine/  pasture/  religion/
```

**Region Buildings** are separate from Settlement buildings — they exist on the world map, not in capital.

### Settlement on Worldmap
```java
// Settlement on World Map
class Region {
    Settlement settlement;  // Capital settlement in this region
    Faction owner;
    boolean isCapital;
    List<RegionBuilding> buildings;
    // ...
}
```

### Worldmap Buildings (from data)
```txt
# data/assets/init/world/building/
agriculture/  civic/  global/  infra/  military/  mine/  pasture/  religion/
```

---

## 6. Immigration & Population Flow

### Immigration System (from `RacePopulation` class)
```java
// RacePopulation fields
double max = 1.0;
double growth = 0.075;
Map<Climate, Double> climate;    // COLD: 0.8, TEMPERATE: 1.0, HOT: 0.8
Map<Terrain, Double> terrain;    // MOUNTAIN: 0.2, FOREST: 0.2, NONE: 1.5
```

### Immigration Formula (from engine analysis)
```
Immigration Rate = BASE_IMMIGRATION 
    * CLIMATE_MODIFIER 
    * TERRAIN_MODIFIER 
    * CIVIC_IMMIGRATION_BOOST
    * RACE_RELATIONS_FACTOR
```

### Civic Immigration Boost
```txt
# From CIVIC techs
CIVIC_IMMIGRATION>MUL: 1.5
```

### V71 Population Growth Formula (from `RacePopulation.class`)
```java
// Base growth from RacePopulation
double baseGrowth = race.growth;  // 0.075 for Humans

// Modified by:
// - Climate preference
// - Terrain preference  
// - Housing availability
// - Law modifiers (new in V71)
// - Civic Knowledge investment
```

---

## 7. Race Preferences & Tolerance System

### `PREFERRED` Section (Race.txt)
```txt
PREFERRED: {
    FOOD: [BREAD, MEAT, MUSHROOM, EGG],
    DRINK: [*],
    ROAD: { *: 0.1, STONE1: 0.5, STONE2: 0.8, DECOR1: 1.0 },
    STRUCTURE: { MOUNTAIN: 0.2, STONE: 0.7, GRAND: 1.0, WOOD: 0.5, OUTDOORS: 0.3 },
    POOL: { POOL_STONE: 1.0 },
    WORK: { 
        _ASYLUM: 0.75, _EMBASSY: 1.0, _EXPORT: 0.25,
        _INN: 0.75, _POLICE: 0.5, ADMIN_NORMAL: 0.75,
        BARBER_NORMAL: 0.75, GRAVEYARD_NORMAL: 0.5,
        PHYSICIAN_NORMAL: 1.0, REFINE_COALER: -0.75,
        REFINER_SMELTER: -0.75, REFINER_WEAVER: 0.25,
        SCHOOL_NORMAL: 0.75, SPEAKER_NORMAL: 0.5,
        STAGE_NORMAL: 1.0, TAVERN_NORMAL: 0.75,
        TOMB_NORMAL: 0.75, UNIVERSITY_NORMAL: 1.0,
        WORKSHOP_BOWYER: 0.75, WORKSHOP_CARPENTER: 0.75,
        WORKSHOP_JEWELRY: 0.75, WORKSHOP_MECHANIC: 0.75,
        WORKSHOP_SMITHY: 0.25, WORKSHOP_TAILOR: 0.75,
    },
    OTHER_RACES: {
        GARTHIMI: 0.75, CRETONIAN: 0.75, CANTOR: 0.75,
        Q_AMEVIA: 0.75, DONDORIAN: 0.75, ARGONOSH: 0.75,
        TILAPI: 0.2,
    },
    OTHER_RACES_REVERSE: { *: 1 }
}
```

### Key Fields
| Field | Purpose |
|-------|---------|
| `OTHER_RACES` | How much THIS race likes OTHER races |
| `OTHER_RACES_REVERSE` | How OTHER races like THIS race |
| `WORK` | Room/work preference multipliers |
| `FOOD`/`DRINK` | Consumption preferences |
| `CLIMATE`/`TERRAIN` | Settlement placement preferences |

---

## Architecture Decision Points

### UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Does `_ignoreVanilla: true` on Race fully override Vanilla? | **UNVERIFIED** | CRITICAL |
| Does `RACES: [UNDEAD]` on Resource actually restrict usage? | **UNVERIFIED** | HIGH |
| Does `OUTPUT` field in Room work for Population Class production? | **UNVERIFIED** | HIGH |
| Does `CITIZEN_ADD: RACE: UNDEAD` work in Events? | **UNVERIFIED** | CRITICAL |
| Does Worldmap Building produce to Player Stockpile? | **UNVERIFIED** | HIGH |
| Can `SELECTION.REGIONS` place Worldmap Buildings? | **UNVERIFIED** | HIGH |
| Can `BOOST` from one Settlement affect another? | **UNVERIFIED** | HIGH |
| Does `GameEventsApi` support runtime Event registration? | **UNVERIFIED** | HIGH |

---

## Migration Notes V70 → V71

### Breaking Changes
| System | V70 | V71 | Migration |
|--------|-----|-----|-----------|
| Slavery | Resource-based | Law-based Population Class | Complete rewrite |
| Law System | Static config | Dynamic Laws + Stats | Rewrite Law files |
| Population Growth | Static multiplier | Formula + Law Modifiers | Update Race files |
| Slave Trade | Resource trade | Diplomatic Action + Population Transfer | Rewrite Orc/Undead pipeline |
| Race Relations | Static `OTHER_RACES` | Dynamic via Laws/Events | Add Law/Event hooks |
| Tech Tree | Flat costs | Era scaling + Faction trees | Update Tech files |

### Migration Checklist
- [ ] Remove `CAPTIVE_HUMAN` resource
- [ ] Add `SLAVERY` Law (Criminal, Tier 1-3)
- [ ] Update `UNDEAD_CONVERSION` Event → target `CLASS_SLAVE`
- [ ] Rewrite `ORC_SLAVERY` Tech → `UNLOCKS_DIPLOMATIC_ACTION: REQUEST_SLAVE_TRADE`
- [ ] Update `UNDEAD` Race: `GROWTH: 0.0`, add `LAW_MOD` integration
- [ ] Add `UNDEAD_SLAVERY` Law (Criminal, Tier 1)
- [ ] Add `UNDEAD_CONVERSION` Law (Criminal, Tier 2, req: UNDEAD_SLAVERY)
- [ ] Add `HUMAN_FARM_MANAGEMENT` Law (Civic, Tier 2)
- [ ] Update `NECROPOLIS` Room → `POPULATION_CLASS_CHANGE` action
- [ ] Update `HUMAN_PENS` → Remove (replace with World Building)

---

## V71 Compliance Checklist

| Feature | V70 Status | V71 Required | Effort |
|---------|------------|--------------|--------|
| Slavery System | Resource-based | Law + Pop Class | HIGH |
| Law System | Static | Dynamic + Stats | HIGH |
| Population Growth | Static | Formula + Laws | MEDIUM |
| Tech Tree | Flat | Era + Faction | MEDIUM |
| Orc Slavery | Room-based | Diplomatic + Events | HIGH |
| Undead Conversion | Event + Resource | Law + Event + Pop Class | HIGH |
| Race Relations | Static | Law/Event Dynamic | MEDIUM |
| Tech Tree | Flat | Era + Faction | MEDIUM |

---

*End of Vanilla Systems Reference*
*All findings based on V71.44 JAR analysis (2026-06-24 build)*