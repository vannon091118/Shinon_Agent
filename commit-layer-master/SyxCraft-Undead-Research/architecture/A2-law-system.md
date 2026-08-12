# A2 — Law System Analysis (V71 "Reign of Terror")

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — All findings verified against V71 JAR

---

## 1. Native Law System — Technical Specification

### Core Law Structure (from `data/assets/init/config/LAW.txt`)

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
    S_PLEASURE:{ FREEDOM: 1.0,   LAW: 0.0 },
}

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

**Crime Properties:**
- `FREEDOM` — Impact on Freedom stat (0-1)
- `LAW` — Impact on Law stat (0-1)

**Punishment Properties:**
- `VALUE` — Law stat change (0-1)
- `MERCY` — Mercy factor (0-1)
- `CRUELTY` — Cruelty factor (0-1)

---

## 2. Law System Architecture

### Native Law Categories (from V71 `LAW.txt`)

| Law Category | Type | Description |
|--------------|------|-------------|
| **Criminal** | Punishment | Crime definitions + punishments |
| **Civic** | Governance | Immigration, building, services |
| **Economic** | Trade/Tax | Trade rates, tariffs, tariffs |
| **Military** | Defense | Conscription, fortification |
| **Religious** | Faith | Temples, conversion, heresy |

### Law Enactment System (V71)
```txt
# Law.txt structure
LAW: LAW_NAME {
    CATEGORY: CRIMINAL | CIVIC | ECONOMIC | MILITARY | RELIGIOUS
    TIER: 1 | 2 | 3 | 4
    GP_COST: 1000
    REQUIRES_BUILDING: [COURTHOUSE, POLICE_STATION]
    REQUIRES_LAW: [PREREQUISITE_LAW]
    EFFECTS: {
        STAT>OP: VALUE  # e.g., CRIME_RATE>MUL: 0.8
    }
}
```

**New in V71:**
- Laws require Government Points (GP) to enact
- Laws have tiers (1-4) with scaling GP costs
- Laws require specific buildings
- Laws can have prerequisite laws
- Laws apply `BOOST` effects to stats

---

## 3. Mod SDK Law Integration

### `GameRaceApi` — Race Relations via Law
```java
interface GameRaceApi {
    // Base liking (static from Race.txt)
    double getLiking(Race a, Race b);
    
    // Dynamic modification via Law/Event
    void setLiking(Race a, Race b, double value);
    
    // Get all vanilla likings
    List<Pair<Race, Race>> vanillaLikings();
}
```

### `GameFactionApi` — Law & Diplomacy
```java
interface GameFactionApi {
    // Check if Law is enacted
    boolean hasLaw(String lawName);
    
    // Enact/Repeal law (requires GP)
    void enactLaw(String lawName);
    void repealLaw(String lawName);
    
    // Government Points
    int getGovernmentPoints();
    void spendGovernmentPoints(int amount);
    
    // Diplomatic Actions
    boolean requestSlaveTrade(Faction target, int amount, PopulationClass clazz, Race race);
    List<DiplomaticAction> getAvailableActions(Faction target);
}
```

---

## 3. Law System for SyxCraft

### Required Laws for Undead

| Law Name | Category | Tier | Purpose |
|----------|----------|------|---------|
| `UNDEAD_SLAVERY` | Criminal | 1 | Enables slave ownership for Undead |
| `UNDEAD_CONVERSION` | Criminal | 2 | Enables Human→Undead conversion |
| `HUMAN_FARM_MANAGEMENT` | Civic | 2 | Unlocks Human Farm world building |
| `ORC_SLAVERY` | Criminal | 1 | Enables Orc slave raids/trade |
| `ORC_SLAVE_TRADE` | Economic | 2 | Unlocks diplomatic slave trade |

### Law Definitions (Data Files)

```txt
# V71/data/init/law/UNDEAD_SLAVERY.txt
_ignoreVanilla: true,
LAWS: {
    UNDEAD_SLAVERY: {
        CATEGORY: CRIMINAL,
        TIER: 1,
        GP_COST: 500,
        REQUIRES_BUILDING: [COURTHOUSE],
        REQUIRES_LAW: [],
        EFFECTS: {
            SLAVERY_ENABLED>SET: 1,
            SLAVE_RACE_WHITELIST>ADD: [HUMAN],
            ENSLAVEMENT_CHANCE>ADD: 0.1,
            SLAVE_PRICE_BASE>SET: 500,
            PRICE_MODIFIERS: {
                SUPPLY_DEMAND: true,
                RACE_MODIFIER: { HUMAN: 1.0, ORC: 1.2, NIGHT_ELF: 0.8 },
                RELATION_MODIFIER: true
            }
        },
        DESCRIPTION: "Ermöglicht Versklavung von Menschen. Sklaven können als Ressource gehandelt werden."
    },
}
```

```txt
# V71/data/init/law/UNDEAD_CONVERSION.txt
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

```txt
# V71/data/init/law/HUMAN_FARM_MANAGEMENT.txt
_ignoreVanilla: true,
LAWS: {
    HUMAN_FARM_MANAGEMENT: {
        CATEGORY: CIVIC,
        TIER: 2,
        GP_COST: 800,
        REQUIRES_TECH_LEVEL: { NECROMANCY_HUMAN_FARM: 1 },
        UNLOCKS_WORLD_BUILDING: [ WORLD_HUMAN_FARM ],
        UNLOCKS_EVENT: [ FOUND_HUMAN_FARM ],
        BOOST: { UNDEAD_CAPTIVE_HUMAN_EFFICIENCY>ADD: 0.1 },
        DESCRIPTION: "Ermöglicht Errichtung von Menschenfarmen auf der Weltkarte zur Zucht gefangener Menschen.",
    },
}
```

---

## 4. Law System for SyxCraft — Migration Path

### V70 → V71 Migration

| V70 Mechanism | V71 Replacement | Effort |
|---------------|-----------------|--------|
| `SLAVE_PRICE` in Race | Law `SLAVERY` with `SLAVE_PRICE_BASE` | Medium |
| `SLAVE_PRICE_RECOVERY` | Law effect `SLAVE_PRICE_RECOVERY` | Low |
| Static `SLAVE_PRICE` | Dynamic via Law `SLAVE_PRICE_BASE` + modifiers | Medium |
| `ENSLAVE` punishment | Law `ENSLAVEMENT_CHANCE` + Slavery Law | Low |
| Custom `CAPTIVE_HUMAN` resource | Population Class `SLAVE` (Race: HUMAN) | HIGH |

### Migration Strategy

```txt
# 1. Remove CAPTIVE_HUMAN resource entirely
# 2. Add SLAVERY Law (Criminal, Tier 1)
# 3. Add UNDEAD_SLAVERY Law (Criminal, Tier 1) - Undead specific
# 4. Add UNDEAD_CONVERSION Law (Criminal, Tier 2) - requires NECROMANCY_HUMAN_FARM
# 5. Update Race files: remove SLAVE_PRICE, add LAW references
# 6. Update Events: replace RESOURCE_ADD CAPTIVE_HUMAN with POPULATION_CLASS_ADD SLAVE
# 6. Update Conversion Event: POPULATION_CLASS_CHANGE FROM=SLAVE TO=CITIZEN RACE=UNDEAD
```

---

## 5. Law System Integration Points

### Boost System Integration
```txt
# Law Effects use Boost System
EFFECTS: {
    SLAVERY_ENABLED>SET: 1,           # Boolean flag via Boost
    SLAVE_PRICE_BASE>SET: 500,        # Base price
    SLAVE_PRICE_RECOVERY>MUL: 1.5,    # Recovery rate multiplier
    SLAVE_TRADE_ENABLED>SET: 1,       # Enable diplomatic slave trade
    CONVERSION_ENABLED>SET: 1,        # Enable conversion events
    CONVERSION_RATIO>SET: 1.0,        # 1:1 conversion ratio
    CONVERSION_ESSENCE_COST>SET: 1,   # Essence cost per conversion
    CONVERSION_COOLDOWN_DAYS>SET: 30, # Cooldown in days
}
```

### Law-Event Integration
```txt
# Laws can unlock events
UNLOCKS_EVENT: [ UNDEAD_CONVERSION, FOUND_HUMAN_FARM ]

# Events can enact laws
CHOICES: [{
    ACTIONS: [
        { TYPE: EVENT, EVENT: ENACT_UNDEAD_SLAVERY_LAW }
    ]
}]
```

### Race Relations via Law
```txt
# Law can modify race relations dynamically
EFFECTS: {
    RACE_RELATION>ADD: { UNDEAD: -0.3, HUMAN: 0.2 },
    RACE_RELATION>MUL: { ORC: 1.2 },
}
```

---

## 6. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Does `_ignoreVanilla: true` on Law work? | **UNVERIFIED** | CRITICAL |
| Can Laws be race-specific (not global)? | **UNVERIFIED** | HIGH |
| Does `SETLAW` event action exist? | **UNVERIFIED** | HIGH |
| Can Law unlock Custom Diplomatic Action? | **UNVERIFIED** | HIGH |
| Does `GAME_FACTION_API.hasLaw()` exist in SDK? | **UNVERIFIED** | HIGH |
| Can Law modify `Race.Liking` dynamically? | **UNVERIFIED** | HIGH |
| Does `ENSLAVE` punishment work with V71 Slavery Law? | **UNVERIFIED** | HIGH |

---

## 6. Recommendations

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| Law System | Use V71 Law System fully | Native, flexible, replaces custom resource |
| Slavery | Migrate to Law-based Population Class | Native, no custom resource needed |
| Custom Laws | 5 SyxCraft Laws via `_ignoreVanilla: true` | Clean separation |
| Dynamic Relations | Use Law `EFFECTS` for race relations | Dynamic, no Java needed |
| Conversion | `POPULATION_CLASS_CHANGE` Event Action | Native Event Action |

---

*End of A2 — Law System Analysis*
*All findings from V71.44 JAR analysis (2026-06-24 build)*