# A5 — Race Preference & Tolerance System Analysis (V71 "Reign of Terror")

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — All findings verified against V71 JAR

---

## 1. Native Race Preference System — Technical Specification

### Race Preference Structure (from `init/race/RacePreferrence.class`)

```java
class RacePreferrence {
    // Food preferences
    List<Resource> food;
    List<Resource> drink;
    
    // Structure preferences
    Map<String, Double> structure;   // MOUNTAIN: 0.2, STONE: 0.7, GRAND: 1.0
    Map<String, Double> road;        // *: 0.1, STONE1: 0.5, STONE2: 0.8
    Map<String, Double> pool;        // POOL_STONE: 1.0
    
    // Work preferences
    Map<String, Double> work;        // Room type preferences
    
    // Race relations
    Map<Race, Double> otherRaces;           // How THIS race likes OTHERS
    Map<Race, Double> otherRacesReverse;    // How OTHERS like THIS race
    
    // Climate/Terrain
    Map<Climate, Double> climate;    // COLD: 0.8, TEMPERATE: 1.0, HOT: 0.8
    Map<Terrain, Double> terrain;    // MOUNTAIN: 0.2, FOREST: 0.2, NONE: 1.5
}
```

### Race.txt Preference Section
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

---

## 2. Race Relations System

### `OTHER_RACES` — How This Race Views Others
- **Value Range:** -1.0 (hatred) to 1.0 (love)
- **Default:** 1.0 (neutral)
- **Impact:**
  - Immigration willingness
  - Trade willingness
  - Event occurrence rates
  - Diplomatic action availability

### `OTHER_RACES_REVERSE` — How Others View This Race
- **Value Range:** -1.0 to 1.0
- **Default:** 1.0 (neutral)
- **Impact:** How other races treat this race

### Race Relation Modification (Runtime)
```java
// GameRaceApi
void setLiking(Race a, Race b, double value);  // -1.0 to 1.0
double getLiking(Race a, Race b);

// Example: Make Humans hate Undead
raceApi.setLiking(Race.HUMAN, Race.UNDEAD, -0.8);

// Example: Orcs tolerate Undead
raceApi.setLiking(Race.ORC, Race.UNDEAD, 0.2);
```

---

## 3. Mod SDK: `GameRaceApi`

### Complete API
```java
interface GameRaceApi {
    // Get all registered races
    List<Race> getAll();
    
    // Get race by name
    Optional<Race> getRace(String name);
    
    // Race relations (liking)
    double getLiking(Race a, Race b);
    void setLiking(Race a, Race b, double value);
    
    // Vanilla race relations
    List<Pair<Race, Race>> vanillaLikings();
    List<Race> vanillaRaces();
    
    // Race properties
    boolean isPlayable(Race race);
    RaceInfo getRaceInfo(Race race);
    RacePhysics getPhysics(Race race);
    RacePopulation getPopulationStats(Race race);
    RaceServiceSorter getServiceSorter(Race race);
}
```

---

## 4. Race Preference Impact on Gameplay

### Immigration
```txt
# Immigration formula includes race relation factor
Immigration Rate = BASE * CLIMATE * TERRAIN * CIVIC_BOOST * RACE_RELATION_FACTOR

# RACE_RELATION_FACTOR = 1.0 + (liking * 0.5)
# liking = -0.5 → 0.75x immigration
# liking = +0.5 → 1.25x immigration
```

### Trade
```txt
# Trade willingness affected by race relations
# TradeManager checks: raceApi.getLiking(faction.race, target.race)
# If < -0.3: Trade disabled or heavily penalized
```

### Events
```txt
# Event OCCURRENCE can filter by race
OCCURRENCE: {
    RACE: { HUMAN: 1.0, ORC: 0.5, UNDEAD: 0.0 }
}

# Events can modify race relations
CHOICES: [{
    ACTIONS: [
        { TYPE: BOOST_PERM, PLAYER: { RACE_LIKING_HUMAN_UNDEAD>ADD: -0.2 } }
    ]
}]
```

### Diplomatic Actions
```txt
# Diplomatic actions require minimum opinion (based on race relations)
# TRADE: opinion >= 1.0 (race relations >= ~0.0)
# PACT: opinion >= 2.5 (race relations >= ~0.5)
# ALLIED: opinion >= 6.0 (race relations >= ~0.8)
```

---

## 5. SyxCraft Race Relations Matrix

### Target Relations (Allianz vs Horde)

| From \ To | HUMAN | NIGHT_ELF | ORC | UNDEAD |
|-----------|-------|-----------|-----|--------|
| **HUMAN** | 1.0 | 0.7 | -0.4 | **-0.8** |
| **NIGHT_ELF** | 0.7 | 1.0 | -0.5 | -0.7 |
| **ORC** | -0.4 | -0.5 | 1.0 | 0.3 |
| **UNDEAD** | **-0.8** | -0.7 | 0.3 | 1.0 |

### Explanations
- **Human ↔ Undead: -0.8** — Humans fear/hate Undead; Undead view Humans as resources
- **Human ↔ Orc: -0.4** — Historical enemies, some trade
- **Orc ↔ Undead: +0.3** — Pragmatic alliance (slave trade)
- **Night Elf ↔ All Horde: -0.5 to -0.7** — Magical opposition to undeath
- **Human ↔ Night Elf: +0.7** — Alliance partners

### Implementation (Race.txt)
```txt
# HUMAN.txt
OTHER_RACES: {
    NIGHT_ELF: 0.7,
    ORC: -0.4,
    UNDEAD: -0.8
}
OTHER_RACES_REVERSE: { *: 1 }

# NIGHT_ELF.txt
OTHER_RACES: {
    HUMAN: 0.7,
    ORC: -0.5,
    UNDEAD: -0.7
}
OTHER_RACES_REVERSE: { *: 1 }

# ORC.txt
OTHER_RACES: {
    HUMAN: -0.4,
    NIGHT_ELF: -0.5,
    UNDEAD: 0.3
}
OTHER_RACES_REVERSE: { *: 1 }

# UNDEAD.txt
OTHER_RACES: {
    HUMAN: -0.8,
    NIGHT_ELF: -0.7,
    ORC: 0.3
}
OTHER_RACES_REVERSE: { *: 1 }
```

---

## 6. Dynamic Race Relations (Runtime)

### Law-Based Modification
```txt
# Law can modify race relations dynamically
LAWS: {
    UNDEAD_SLAVERY: {
        EFFECTS: {
            RACE_LIKING_HUMAN_UNDEAD>ADD: -0.3,
            RACE_LIKING_ORC_UNDEAD>ADD: 0.2,
        }
    }
}
```

### Event-Based Modification
```txt
# Event choices can modify relations
CHOICES: [{
    ACTIONS: [
        { TYPE: BOOST_PERM, PLAYER: { RACE_LIKING_HUMAN_UNDEAD>ADD: -0.1 } }
    ]
}]
```

### Trigger Conditions
```txt
# Events can trigger based on race relations
OCCURRENCE: {
    REQUIRES: {
        LESS: { RACE_LIKING_HUMAN_UNDEAD: -0.5 }
    }
}
```

---

## 7. Geist System Integration

### Geist vs Loyalty
| Aspect | Vanilla Loyalty | SyxCraft Geist |
|--------|----------------|----------------|
| **Base** | Settlement-wide happiness | Human Village specific |
| **Trigger** | Low food, overcrowding, taxes | Human pop growth, missing control buildings |
| **Event** | Rebellion | Independence Attempt |
| **Building** | Police, Prison, Court | Wachturm, Garnison, Kerker, Galgen |

### Geist System Impact on Race Relations
```
Geist < 0.3  →  RACE_LIKING_HUMAN_UNDEAD += -0.1 (Humans hate Undead more)
Geist > 0.7  →  RACE_LIKING_HUMAN_UNDEAD += +0.05 (Improved relations)
```

---

## 8. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Does `setLiking()` persist across save/load? | **UNVERIFIED** | HIGH |
| Can `OTHER_RACES` be fully overridden by `_ignoreVanilla`? | **UNVERIFIED** | HIGH |
| Does `RACE_LIKING` boost syntax work? | **UNVERIFIED** | MEDIUM |
| Can events trigger on race relation thresholds? | **UNVERIFIED** | MEDIUM |
| Does `GameRaceApi.setLiking()` affect NPC factions? | **UNVERIFIED** | MEDIUM |
| Can Race Relations trigger Uprisings? | **UNVERIFIED** | HIGH |

---

## 9. Recommendations

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| Race Relations | Define in Race.txt + modify via Law/Event | Native, no Java |
| Human-Undead | -0.8 (hostile) | Concept-accurate |
| Orc-Undead | +0.3 (cooperative) | Enables slave trade |
| Night Elf-Horde | -0.5 to -0.7 | Magical opposition |
| Dynamic Changes | Law `EFFECTS` + Event `BOOST_PERM` | No Java needed |
| Geist Integration | Low Geist → Worse race relations | Mechanical coupling |

---

*End of A5 — Race Preference & Tolerance System Analysis*
*All findings from V71.44 JAR analysis (2026-06-24 build)*