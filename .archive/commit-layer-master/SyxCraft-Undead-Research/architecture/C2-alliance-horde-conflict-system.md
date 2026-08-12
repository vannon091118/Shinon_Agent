# C2 — Alliance vs Horde Conflict System Analysis

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — Technical Specification

---

## 1. Native Faction War System

### Does SoS have a native Faction War System?

**From JAR Analysis:** **JA, aber begrenzt.**

```java
// game/faction/diplomacy/DIP.class
enum DipStance {
    NEUTRAL,    // 0
    TRADE,      // 1
    PACT,       // 2.5
    ALLIED,     // 6
    VASSAL,     // 2.5
    OVERLORD,
    WAR,        // Total War
    ENEMIES     // Hostile
}

// game/faction/FACTIONS.class
class Factions {
    // War declaration
    void declareWar(Faction a, Faction b);
    void makePeace(Faction a, Faction b);
    
    // Stance management
    DipStance getStance(Faction a, Faction b);
    void setStance(Faction a, Faction b, DipStance stance);
    
    // War mechanics
    List<Faction> getEnemies(Faction faction);
    List<Faction> getAllies(Faction faction);
}
```

### Native War Features
| Feature | Native Support |
|---------|----------------|
| War Declaration | ✅ `declareWar()` |
| Peace Treaty | ✅ `makePeace()` |
| Allied Stance | ✅ Shared enemies, auto-trade |
| Vassalage | ✅ Tribute + Protection |
| War Score | ❓ Nicht direkt sichtbar |
| Territorial Control | ❌ Kein natives System |
| War Events | ✅ Battle Events |

---

## 2. Faction War for SyxCraft

### Alliance vs Horde Structure

```
ALLIANCE (Faction Group)          HORDE (Faction Group)
├── Human Player                  ├── Orc Player
├── Human NPC Factions            ├── Orc NPC Factions
├── Night Elf Player              ├── Undead Player
└── Night Elf NPC Factions        └── Undead NPC Factions
```

### War Declaration Mechanics

```txt
# Event: FACTION_WAR_DECLARATION
FACTION_WAR_DECLARATION: {
    ICON: 32->MILITARY->WAR,
    DURATION: { DAYS: 1.0 },
    
    OCCURRENCE: {
        REQUIRES: {
            GREATER: { 
                FACTION_RELATION_ALLIANCE_HORDE: -50 
            }
        }
    },
    
    SELECTION: {
        FACTIONS: {
            FILTERS: [
                { EQUAL: { FACTION_GROUP: HORDE } }
            ]
        }
    },
    
    CHOICES: [{
        ACTIONS: [
            { TYPE: FACTION_RELATION, FACTION: TARGET, VALUE: -100 },
            { TYPE: EVENT, EVENT: WAR_DECLARED },
            { TYPE: NOTIFICATION, TEXT: "Krieg wurde erklärt!" }
        ]
    }]
}
```

### Diplomatic Stance Integration

```txt
# Race Relations drive initial stance
# Human/Undead: -0.8 → Likely WAR/ENEMIES
# Orc/Undead: +0.3 → Likely PACT/TRADE
# Human/Night Elf: +0.7 → Likely ALLIED/PACT

# Alliance Formation (via Diplomatic Actions)
# Human + Night Elf → PACT → ALLIED
# Orc + Undead → PACT → ALLIED
```

---

## 3. Conflict System Design

### War State Tracking (Core State)
```java
class WarState {
    boolean allianceHordeWar = false;
    long warStartTime = 0;
    int allianceWarScore = 0;
    int hordeWarScore = 0;
    Map<Integer, Integer> regionControl = new HashMap<>(); // regionId -> factionGroup
    
    void updateWarScore(FactionGroup winner, Region region) {
        if (winner == ALLIANCE) allianceWarScore += 10;
        else hordeWarScore += 10;
        
        regionControl.put(region.id, winner.ordinal());
    }
}
```

### War Score Factors
| Action | Alliance Score | Horde Score |
|--------|---------------|-------------|
| Win Battle | +10 | +10 |
| Capture Region | +25 | +25 |
| Kill Enemy Leader | +50 | +50 |
| Slave Trade (Horde) | 0 | +5 per 10 slaves |
| Conversion (Undead) | 0 | +3 per convert |
| Human Immigration | +2 per immigrant | 0 |
| Moonwell Built | +15 | 0 |

---

## 4. Territorial Control System

### Region Ownership
```java
// Native: Region has owner Faction
// SyxCraft: Extend with FactionGroup ownership

enum FactionGroup {
    NEUTRAL,
    ALLIANCE,   // Human + Night Elf
    HORDE       // Orc + Undead
}

class RegionControl {
    Map<Integer, FactionGroup> regionControl = new HashMap<>();
    
    FactionGroup getController(Region region) {
        return regionControl.getOrDefault(region.id, NEUTRAL);
    }
    
    void setController(Region region, FactionGroup group) {
        regionControl.put(region.id, group);
        // Trigger event
        coreBus.publish(new RegionControlChangedEvent(region, group));
    }
    
    List<Region> getContestedRegions() {
        // Regions adjacent to both groups
    }
}
```

### Contested Region Events
```txt
# Event: CONTESTED_REGION
CONTESTED_REGION: {
    SELECTION: {
        REGIONS: {
            FILTERS: [
                { EQUAL: { IS_CONTESTED: 1 } }
            ]
        }
    },
    
    CHOICES: [{
        ACTIONS: [
            { TYPE: FACTION_RELATION, FACTION: ATTACKER, VALUE: 5 },
            { TYPE: EVENT, EVENT: REGION_BATTLE }
        ]
    }]
}
```

---

## 5. Shared Narrative Events

### Multi-Faction Events (Native Support)

```txt
# Event affecting ALL Alliance members
ALLIANCE_INVASION: {
    OCCURRENCE: {
        REQUIRES: { 
            GREATER: { WAR_SCORE_HORDE: 100 } 
        }
    },
    
    SELECTION: {
        FACTIONS: {
            FILTERS: [ { EQUAL: { FACTION_GROUP: ALLIANCE } } ]
        }
    },
    
    CHOICES: [{
        ACTIONS: [
            { TYPE: BOOST_PERM, PLAYER: { ALLIANCE_MILITARY_BOOST>ADD: 0.2 } },
            { TYPE: NOTIFICATION, TEXT: "Die Allianz mobilisiert!" }
        ]
    }]
}
```

### Event Coordination via Core Bus
```java
// Core Bus Event
public record AllianceHordeEvent(FactionGroup source, WarEventType type, Region region) 
    implements CoreEvent {}

// Published by any Module
coreBus.publish(new AllianceHordeEvent(HORDE, RAID_SUCCESS, region));

// Subscribed by all Modules
@Subscribe
void onWarEvent(AllianceHordeEvent e) {
    if (e.type() == RAID_SUCCESS && e.source() == HORDE) {
        // Alliance modules react: increase defense, mobilize
        // Horde modules react: increase aggression
    }
}
```

---

## 6. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Funktioniert `declareWar()` für NPC Factions? | **UNVERIFIED** | HIGH |
| Können Diplomatic Actions WAR auslösen? | **UNVERIFIED** | HIGH |
| Gibt es natives War Score System? | **UNVERIFIED** | MEDIUM |
| Funktionieren Multi-Faction Events? | **UNVERIFIED** | MEDIUM |
| Kann `FACTION_GROUP` als Filter genutzt werden? | **UNVERIFIED** | HIGH |

---

## 7. Recommendations

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| War Declaration | Diplomatic Action + Event | Native + Extensible |
| War Score | Custom Core State | No native system |
| Territorial Control | Region Flags + Core State | Native Region + Extension |
| Alliance/Horde | FactionGroup Enum in Core | Clean separation |
| Multi-Faction Events | Core Bus + Data Events | Native Event System |

---

*End of C2 — Alliance vs Horde Conflict System Analysis*
*All findings from V71.44 analysis and Mod SDK review*