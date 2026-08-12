# V71 Impact Analysis — SyxCraft Migration V70 → V71

> **Engine:** V71.44 "Reign of Terror"
> **Baseline:** SyxCraft V70 (Current Release)
> **Status:** Research Complete — All Migration Paths Documented

---

## Summary: Breaking Changes

| System | V70 → V71 Change | SyxCraft Impact | Migration Effort |
|--------|------------------|-----------------|------------------|
| **Slavery System** | Resource-based → Law-based Population Class | **CRITICAL** — `CAPTIVE_HUMAN` Resource removed | HIGH |
| **Orc Slavery** | Tech→Room | Diplomatic Action + Law Tier 2+ | HIGH |
| **Population Growth** | Static Multiplier | Formula + Law Modifiers + Migration | MEDIUM |
| **Race Relations** | Static `OTHER_RACES` | Dynamic via Laws/Events | MEDIUM |
| **Slave Pricing** | Static `SLAVE_PRICE` | Dynamic Law-based | LOW |
| **Tech Tree** | Flat Categories | Era-scaled + Faction-specific | LOW |
| **Race Slots** | Fixed Vanilla | `_ignoreVanilla: true` works | NONE |

---

## 1. Slavery System — Complete Overhaul

### V70 (SyxCraft Current)
```txt
# CAPTIVE_HUMAN.txt
RESOURCE: CAPTIVE_HUMAN
RACES: [UNDEAD]
CATEGORY: supply

# ORC_SLAVERY Tech
UNLOCKS_FACTION: [ ROOM_SLAVE_PEN ]

# ORC_SLAVE_RAID Event
ACTIONS: [ { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: 15 } ]

# ORC_SLAVE_TRADE_OFFER Event
ACTIONS: [ { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: -20 } ]

# NECROPOLIS Room
CONSUMPTION: { CAPTIVE_HUMAN: { RATE: 1.0 } }
```

### V71 "Reign of Terror"
- **No `CAPTIVE_HUMAN` resource** — Slaves = Population Class `SLAVE` (Race: HUMAN)
- **Slavery = Law** (Criminal Category, Tier 1-3)
- **Slave Acquisition**: Enslavement Law + Raid Events + Diplomatic Trade
- **Slave Trade**: Diplomatic Action (`REQUEST_SLAVE_TRADE`) requiring Embassy + Trade Agreement + Slavery Law Tier 2+

### Migration Path

| V70 Artifact | V71 Replacement | Action |
|--------------|-----------------|--------|
| `CAPTIVE_HUMAN.txt` | **DELETE** | Remove resource file |
| `ORC_SLAVERY` Tech | **REWRITE** | Unlock Diplomatic Action `REQUEST_SLAVE_TRADE` + Event `ORC_SLAVE_RAID` |
| `SLAVE_PEN` Room | **REWRITE** | Add `STORAGE: { POPULATION_CLASS: SLAVE, RACE: HUMAN }` |
| `ORC_SLAVE_RAID` Event | **REWRITE** | Action: `POPULATION_CLASS_ADD` (CLASS: SLAVE, RACE: HUMAN) |
| `ORC_SLAVE_TRADE_OFFER` Event | **REWRITE** | Action: `POPULATION_CLASS_TRANSFER` (CLASS: SLAVE, RACE: HUMAN) |
| `NECROPOLIS` Room | **REWRITE** | Consumption: `POPULATION_CLASS_CHANGE` (SLAVE→UNDEAD) |

---

## 2. Orc Slavery → Diplomatic Slave Trade

### V70 (SyxCraft)
```
Tech ORC_SLAVERY → Room SLAVE_PEN → Event ORC_SLAVE_RAID → Resource CAPTIVE_HUMAN → Trade Event → Undead receives CAPTIVE_HUMAN
```

### V71
```
Tech ORC_SLAVERY → Unlocks Diplomatic Action REQUEST_SLAVE_TRADE + Event ORC_SLAVE_RAID
    │
    ├─ ORC_SLAVE_RAID Event → POPULATION_CLASS_ADD (CLASS=SLAVE, RACE=HUMAN) to Orc Settlement
    │
    ├─ SLAVE_PEN Room → STORAGE: { POPULATION_CLASS: SLAVE, RACE: HUMAN }
    │
    └─ Diplomatic Action REQUEST_SLAVE_TRADE (requires Embassy + Trade Agreement + Slavery Law Tier 2+)
            → TRANSFER_POPULATION_CLASS (SLAVE, HUMAN) from Orc → Undead
            → Undead receives Population Class SLAVE (Race: HUMAN)
```

### Required Tech Changes
```txt
# ORC_SLAVERY.txt (V71)
TECHS: {
    ORC_SLAVERY: {
        COSTS: { MILITARY_KNOWLEDGE: 150 },
        REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
        UNLOCKS_FACTION: [ ROOM_SLAVE_PEN ],
        UNLOCKS_EVENT: [ ORC_SLAVE_RAID, ORC_SLAVE_TRADE_OFFER ],
        UNLOCKS_DIPLOMATIC_ACTION: [ REQUEST_SLAVE_TRADE ],
        BOOST: { ORC_SLAVE_RAID_EFFICIENCY>ADD: 0.2 },
    }
}
```

---

## 3. Population Growth — Formula Change

### V70
```txt
POPULATION: {
    GROWTH: 0.075,           # Static multiplier
    MAX: 1.0,
    CLIMATE: { COLD: 0.8, ... }
}
```

### V71 Formula
```
Daily Growth = BASE_GROWTH 
    * CLIMATE_MODIFIER 
    * TERRAIN_MODIFIER 
    * HOUSING_MODIFIER 
    * LAW_MODIFIER
    * RACE_MODIFIER
    - EMIgrATION
    + IMMIGRATION
```

### Migration for Undead

| V70 Value | V71 Equivalent |
|-----------|----------------|
| `GROWTH: 0.0` | `BASE_GROWTH: 0.0` + `LAW_MODIFIER: 1.0` (No natural growth) |
| Conversion-only | `CONVERSION_LAW` provides growth via `POPULATION_CLASS_CHANGE` |

**Action:** Update `UNDEAD.txt` Population block:
```txt
POPULATION: {
    MAX: 1.0,
    GROWTH: 0.0,           # Base = 0
    CLIMATE: { COLD: 1.0, HOT: 1.0, TEMPERATE: 1.0 },
    TERRAIN: { MOUNTAIN: 1.5, FOREST: 0.2, NONE: 1.0 },
}
```
**Conversion Growth** handled via `UNDEAD_CONVERSION` Law Boost: `UNDEAD_CONVERSION_RATE>ADD: 0.1`

---

## 4. Race Relations — Static → Dynamic

### V70 (Static in Race File)
```txt
PREFERRED: {
    OTHER_RACES: {
        ORC: 0.8,
        UNDEAD: 0.5,
        ...
    }
}
```

### V71 (Dynamic via Laws/Events)
- **Base Liking** in Race File (static baseline)
- **Dynamic Modifiers** via:
  - Laws: `RACE_RELATIONS>ADD: { UNDEAD: -0.3 }`
  - Events: `BOOST_PERM: { RACE_RELATION_UNDEAD>ADD: -0.2 }`
  - Diplomacy: `FACTION_RELATION` affects Race Relations

### Migration for Undead Relations
```txt
# UNDEAD.txt — Keep base values
PREFERRED: {
    OTHER_RACES: { HUMAN: 0.3, ORC: 0.7, NIGHT_ELF: 0.2 }
}

# Add Laws for Dynamic Control
LAW: UNDEAD_DOMINANCE
EFFECTS:
  - RACE_RELATION>ADD: { HUMAN: -0.2, ORC: 0.1, NIGHT_ELF: -0.3 }
```

---

## 5. Slave Pricing — Static → Dynamic Law

### V70
```txt
PROPERTIES: {
    SLAVE_PRICE: 11,
    SLAVE_PRICE_RECOVERY: 0.5,
}
```

### V71
```txt
LAW: SLAVERY
TIER: 1
EFFECTS:
  - SLAVE_PRICE_BASE: 500
  - PRICE_MODIFIERS:
      SUPPLY_DEMAND: true
      RACE_MODIFIER: { HUMAN: 1.0, ORC: 1.2, NIGHT_ELF: 0.8 }
      RELATION_MODIFIER: true
```

### Migration
1. **Remove** `SLAVE_PRICE` and `SLAVE_PRICE_RECOVERY` from all Race files
2. **Add** `SLAVERY` Law with dynamic pricing
3. **Add** Tier 2/3 Laws for price multipliers

---

## 6. Tech Tree — Era Scaling + Faction Trees

### V70
```txt
TECHS: {
  BASIC_MINING: { COSTS: { CIVIC_KNOWLEDGE: 30 } },
  AGRICULTURE: { COSTS: { CIVIC_KNOWLEDGE: 100 } },
  ...
}
```

### V71
```txt
TECHS: {
    BASIC_MINING: {
        COSTS: { CIVIC_KNOWLEDGE: 30 },
        ERA: EARLY,
        CATEGORY: CIVIC,
    },
    NECROMANCY_HUMAN_FARM: {
        COSTS: { CIVIC_KNOWLEDGE: 200 },
        ERA: MID,
        CATEGORY: CIVIC,
        FACTION: UNDEAD,
        REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
    },
    ORC_SLAVERY: {
        COSTS: { MILITARY_KNOWLEDGE: 150 },
        ERA: MID,
        CATEGORY: MILITARY,
        FACTION: ORC,
        REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
    },
}
```

### New Fields
| Field | Values | Purpose |
|-------|--------|---------|
| `ERA` | `EARLY`, `MID`, `LATE`, `END` | Cost scaling by Era |
| `CATEGORY` | `CIVIC`, `MILITARY`, `SCIENTIFIC`, `RELIGIOUS`, `ECONOMIC` | UI Grouping |
| `FACTION` | `HUMAN`, `ORC`, `UNDEAD`, `NIGHT_ELF`, `NEUTRAL` | Faction-locked Techs |
| `ERA_COST_MULTIPLIER` | Global config | Early=0.5, Mid=1.0, Late=2.0, End=5.0 |

---

## 7. Undead-Specific Migration Checklist

| Mechanic | V70 Implementation | V71 Migration | Status |
|----------|-------------------|---------------|--------|
| `CAPTIVE_HUMAN` Resource | ✅ Exists | **DELETE** → Law-based Slavery | ⬜ |
| `UNDEAD_CONVERSION` Event | ✅ Exists | Target: `CLASS_SLAVE, RACE: HUMAN` | ⬜ |
| `NECROPOLIS` Room | ✅ Exists | `CONSUMPTION` → `POPULATION_CLASS_CHANGE` | ⬜ |
| `UNDEAD.POPULATION.GROWTH: 0.0` | ✅ Exists | `LAW_MODIFIER` integration | ⬜ |
| `SLAVE_PRICE` in Races | ❌ Not in Undead | N/A | ✅ |
| `UNDEAD_CONVERSION` Tech | ❌ Missing | Add `NECROMANCY_HUMAN_FARM` Tech | ⬜ |
| `HUMAN_PENS` Room | ❌ Missing | Add with `GHOST_CONTRIBUTION` | ⬜ |
| `WORLD_HUMAN_FARM` Building | ❌ Missing | Add with `STORAGE: POPULATION_CLASS=SLAVE` | ⬜ |

---

## 8. Mod SDK V71 Breaking API Changes

| API | V70 | V71 | Action |
|-----|-----|-----|--------|
| `GameEventsApi.readEventTrees()` | Returns `Map<String, TreeNode>` | Signature changed | Update imports |
| `GameFactionApi.requestSlaveTrade()` | ❌ Not exist | ✅ New | Add wrapper |
| `GameFactionApi.getDiplomaticActions()` | ❌ | ✅ | Add wrapper |
| `GameEventsApi.builder()` | Exists | Signature changed | Update usage |
| `GameRoomsApi.getRoomStorage()` | ❌ | ✅ New | Add wrapper if needed |
| `RoomBlueprintImp.getStorage()` | ❌ | ✅ New | Add wrapper |

---

## 9. Migration Priority Order

1. **CRITICAL** — Remove `CAPTIVE_HUMAN` resource, implement Slavery Laws
2. **CRITICAL** — Rewrite `ORC_SLAVERY` Tech → Diplomatic Trade
3. **CRITICAL** — Rewrite `ORC_SLAVE_RAID` / Trade Events → Population Class Actions
4. **CRITICAL** — Rewrite `NECROPOLIS` / Conversion → `POPULATION_CLASS_CHANGE`
5. **HIGH** — Update `UNDEAD` Race → Dynamic Relations, Growth Formula
6. **HIGH** — Add `NECROMANCY_HUMAN_FARM` Tech with Law Unlocks
7. **MEDIUM** — Update `ORC_SLAVERY` Tech → Diplomatic Actions
8. **MEDIUM** — Update Population Growth for all Races
9. **LOW** — Update Tech Tree with Era/Category/Faction fields

---

## 10. Testing Matrix

| Test Case | V70 Expected | V71 Expected |
|-----------|--------------|--------------|
| Start Undead Game | Human Farm Event available | Law `UNDEAD_SLAVERY` enacted by default |
| Build Human Pens | Room available after Tech | Gate unlocks via Building Scan |
| Orc Raids Human Settlement | Captive Humans generated | Human Slaves (Population Class) added to Orc Settlement |
| Orc → Undead Trade | Credits + Resources | Diplomatic Action transfers Population Class |
| Undead Conversion | Captive Humans consumed | Slave Population Class → Undead Citizens |
| Save/Load | State preserved | Boostables + Custom State preserved |

---

*End of V71 Impact Analysis*