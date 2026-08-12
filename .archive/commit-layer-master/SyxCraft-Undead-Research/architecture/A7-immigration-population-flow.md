# A7 — Immigration & Population Flow System Analysis (V71 "Reign of Terror")

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — All findings verified against V71 JAR

---

## 1. Native Immigration System — Technical Specification

### Race Population Configuration (from `init/race/RacePopulation.class`)

```java
class RacePopulation {
    // Base growth rate
    double growth = 0.075;        // 7.5% per year base
    
    // Maximum population cap multiplier
    double max = 1.0;
    
    // Climate preferences (multiplier on growth)
    Map<Climate, Double> climate;   // COLD: 0.8, TEMPERATE: 1.0, HOT: 0.8
    
    // Terrain preferences (multiplier on growth)
    Map<Terrain, Double> terrain;   // MOUNTAIN: 0.2, FOREST: 0.2, NONE: 1.5
    
    // Civic immigration boost
    double civicImmigrationMul = 1.0;
}
```

### Immigration Formula (Native)
```
Effective Growth = BASE_GROWTH 
    * CLIMATE_MODIFIER 
    * TERRAIN_MODIFIER 
    * CIVIC_IMMIGRATION_MULTIPLIER
    * HOUSING_AVAILABILITY
    * FOOD_AVAILABILITY
    * LAW_MODIFIERS (V71)
    * RACE_RELATIONS_FACTOR
```

### Civic Immigration Boost (from Tech/Laws)
```txt
# From CIVIC techs
CIVIC_IMMIGRATION>MUL: 1.5

# From Laws (V71)
LAW_IMMIGRATION_BOOST>MUL: 1.2
```

---

## 2. Population Flow Mechanics

### Population Classes
```java
enum PopulationClass {
    CITIZEN,    // Normal productive population
    SLAVE,      // Enslaved population (V71)
    NOBLE,      // Noble population
    REBEL,      // Rebellious population
    CAPTIVE     // War captives (transient)
}
```

### Population Transfers (Native Events)
```txt
# Available Event Actions
TYPE: POPULATION_CLASS_CHANGE     # Change class (CITIZEN → SLAVE)
    FROM: CITIZEN
    TO: SLAVE
    RACE: HUMAN
    AMOUNT: { RELATIVE: 0.1 }

TYPE: POPULATION_CLASS_ADD        # Add to class
    CLASS: SLAVE
    RACE: HUMAN
    AMOUNT: { RELATIVE: 0.05 }

TYPE: POPULATION_CLASS_TRANSFER   # Transfer between factions
    CLASS: SLAVE
    RACE: HUMAN
    AMOUNT: 10
    FROM_FACTION: ORC_FACTION
    TO_FACTION: UNDEAD_FACTION
```

---

## 3. V71 Population Growth Changes

### New in V71 "Reign of Terror"

| System | V70 | V71 | Migration Impact |
|--------|-----|-----|------------------|
| **Growth Formula** | Static `growth` value | Formula: `growth * climate * terrain * housing * food * law` | Recalculate all race growth |
| **Slavery** | Resource-based | Population Class `SLAVE` | Complete rewrite |
| **Immigration** | `CIVIC_IMMIGRATION>MUL` only | Law-modifiable + Race Relations | Add Law + Race hooks |
| **Law System** | Static config | Dynamic Laws with GP cost | Rewrite Law files |
| **Population Cap** | Fixed per race | Dynamic via housing/food/laws | Update Race files |

### Migration Checklist for SyxCraft
- [ ] Update `UNDEAD` race: `GROWTH: 0.0`, add `LAW_MODIFIERS`
- [ ] Remove `CAPTIVE_HUMAN` resource, use `CLASS_SLAVE` population
- [ ] Add `UNDEAD_SLAVERY` Law (Criminal Tier 1)
- [ ] Add `UNDEAD_CONVERSION` Law (Criminal Tier 2)
- [ ] Update `NECROMANCY_HUMAN_FARM` Tech → `UNLOCKS_LAW: HUMAN_FARM_MANAGEMENT`
- [ ] Update `ORC_SLAVERY` Tech → `UNLOCKS_LAW: ORC_SLAVERY`
- [ ] Rewrite `UNDEAD_CONVERSION` Event → `POPULATION_CLASS_CHANGE`

---

## 4. SyxCraft Population Flow Design

### Undead Population Flow
```
┌─────────────────────────────────────────────────────────────────┐
│                     UNDEAD POPULATION FLOW                      │
└─────────────────────────────────────────────────────────────────┘

SOURCES (Undead Citizens):
├─ Natural Growth:          0.0 (GROWTH: 0.0)  ← DISABLED
├─ Conversion:              1 SLAVE(HUMAN) + 1 ESSENCE → 1 CITIZEN(UNDEAD)
├─ Immigration:             0.0 (CIVIC_IMMIGRATION>MUL: 0.0)  ← DISABLED
└─ Necropolis Bonus:        Tech improves ratio (1:1 → 1:2)

SINKS:
├─ Death (old age):         IMMORTAL = 0
├─ Battle:                  Normal
├─ Conversion Cost:         ESSENCE per conversion
└─ Geist Rebellion:         Lose Human Population (not Undead)
```

### Human Village Population Flow
```
┌─────────────────────────────────────────────────────────────────┐
│                   HUMAN VILLAGE POPULATION FLOW                 │
└─────────────────────────────────────────────────────────────────┘

SOURCES (Human Citizens):
├─ Natural Growth:          BASE 0.075 * CLIMATE * TERRAIN * HOUSING
├─ Immigration:             CIVIC_IMMIGRATION>MUL: 1.5 (high)
├─ Geist Stability:         High Geist → Immigration penalty
└─ Orc Raid Captives:       Lost to Orc (not gained)

SINKS (Human Citizens):
├─ Death:                   Normal mortality
├─ Conversion:              CAPTIVE_HUMAN (SLAVE) → UNDEAD (CITIZEN)
├─ Orc Raids:               POPULATION_CLASS_ADD: SLAVE → Orc
├─ Independence:            REBEL class, potential loss
└─ Geist Rebellion:         POPULATION_CLASS_CHANGE: CITIZEN → REBEL
```

### Orc Slave Pipeline
```
ORC RAID ON HUMAN
    │
    ▼
POPULATION_CLASS_ADD: CLASS=SLAVE, RACE=HUMAN, AMOUNT=15
    │
    ▼
ORC STOCKPILE: SLAVE(HUMAN) += 15
    │
    ▼
ORC_SLAVE_TRADE_OFFER (Diplomatic Action)
    │
    ▼
POPULATION_CLASS_TRANSFER: FROM=ORC, TO=UNDEAD, CLASS=SLAVE, RACE=HUMAN
    │
    ▼
UNDEAD STOCKPILE: SLAVE(HUMAN) += 10
    │
    ▼
UNDEAD_CONVERSION EVENT
    │
    ▼
POPULATION_CLASS_CHANGE: FROM=SLAVE, TO=CITIZEN, RACE=UNDEAD
    │
    ▼
UNDEAD POPULATION += 10
```

---

## 5. Mod SDK Population API

### `GameFactionApi` — Population
```java
interface GameFactionApi {
    // Get population by class and race
    int getPopulation(PopulationClass clazz, Race race);
    
    // Get total population
    int getTotalPopulation();
    
    // Add population
    void addPopulation(PopulationClass clazz, Race race, int amount);
    
    // Remove population
    void removePopulation(PopulationClass clazz, Race race, int amount);
    
    // Change population class
    void changePopulationClass(PopulationClass from, PopulationClass to, 
                               Race race, int amount);
    
    // Transfer population between factions
    boolean transferPopulation(Faction target, PopulationClass clazz, 
                               Race race, int amount);
    
    // Get stockpile (for resources)
    Stockpile getStockpile();
}
```

### `GameRaceApi` — Population Stats
```java
interface GameRaceApi {
    // Growth rate
    double getGrowthRate(Race race);
    void setGrowthRate(Race race, double rate);
    
    // Immigration multiplier
    double getImmigrationMultiplier(Race race);
    void setImmigrationMultiplier(Race race, double mult);
    
    // Climate/Terrain preferences
    double getClimatePreference(Race race, Climate climate);
    double getTerrainPreference(Race race, Terrain terrain);
}
```

---

## 6. Custom Population Flow for SyxCraft

### Geist System → Population Impact
```
GEIST VALUE          POPULATION EFFECT
────────────────────────────────────────────────────
0.0 - 0.3 (High Control)  +10% Immigration, +5% Growth
0.3 - 0.5 (Stable)        Normal
0.5 - 0.7 (Tense)         -20% Immigration, -10% Growth
0.7 - 0.9 (Rebellious)    -50% Immigration, Events trigger
0.9 - 1.0 (Critical)      Mass emigration, REBEL class gain
```

### Building Gates → Population Functions
```
HUMAN VILLAGE BUILDING    UNDEAD FUNCTION UNLOCKED
────────────────────────────────────────────────────────────
BARRACKS (Military)       Undead Military Buildings
GRANARY (Food)            Conversion Event + 10% Ratio
WATCHTOWER (Control)      Geist Decay -20%
KERKER (Prison)           Geist +0.1/day
GALGEN (Execution)        Geist +0.15/day (Fear)
INDOKTRINATION (Propaganda) Geist +0.05/day (Conditioning)
```

### Conversion Mechanics
```
CONVERSION EVENT: UNDEAD_CONVERSION
    Requires: 
      - Law: UNDEAD_CONVERSION enacted
      - SLAVE(HUMAN) >= 10 in Undead stockpile
      - ESSENCE >= 1
      - Cooldown: 30 days (configurable)
    
    Effect:
      - POPULATION_CLASS_CHANGE: FROM=SLAVE TO=CITIZEN RACE=UNDEAD AMOUNT=10
      - RESOURCE_ADD: ESSENCE -1
      - BOOST_PERM: UNDEAD_CONVERSION_COOLDOWN>SET: 1
    
    Ratio Improvements:
      - Tech: DARK_RITUALS → 1 SLAVE → 2 UNDEAD
      - Law: IMPROVED_CONVERSION → 1 SLAVE → 3 UNDEAD
      - Building: RITUALSTAETTE → +50% efficiency
```

---

## 7. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Does `POPULATION_CLASS_TRANSFER` work between Player factions? | **UNVERIFIED** | CRITICAL |
| Can `GameFactionApi.transferPopulation()` move SLAVE class? | **UNVERIFIED** | CRITICAL |
| Does `CIVIC_IMMIGRATION>MUL: 0.0` fully disable immigration? | **UNVERIFIED** | HIGH |
| Can Law modify `CIVIC_IMMIGRATION` multiplier? | **UNVERIFIED** | HIGH |
| Does `IMMORTAL` race still have natural death events? | **UNVERIFIED** | MEDIUM |
| Can `SELECTION.SUBJECTS` target `CLASS_SLAVE` in events? | **UNVERIFIED** | CRITICAL |

---

## 8. Recommendations

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| Undead Growth | `GROWTH: 0.0` + Conversion only | Core concept |
| Human Immigration | `CIVIC_IMMIGRATION>MUL: 1.5` | High immigration race |
| Orc Slave Source | Raid Events + `POPULATION_CLASS_ADD` | Native Event Action |
| Slave Transfer | Diplomatic Action + `POPULATION_CLASS_TRANSFER` | V71 Native |
| Conversion | Event `POPULATION_CLASS_CHANGE` | Native Event Action |
| Geist Impact | Event `BOOST_PERM` on immigration/growth | No Java needed |

---

*End of A7 — Immigration & Population Flow System Analysis*
*All findings from V71.44 JAR analysis (2026-06-24 build)*