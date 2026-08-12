# C3 — Shared Narrative Events Analysis

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — Technical Specification

---

## 1. Native Multi-Settlement Event Support

### Does SoS support Events affecting multiple Settlements?

**From JAR Analysis:** **TEILWEISE.**

```java
// GameEventsApi
interface GameEventsApi {
    // Trigger event for specific faction
    void triggerEvent(String eventName, Faction faction);
    
    // Trigger event for specific settlement
    void triggerEvent(String eventName, Settlement settlement);
    
    // Trigger event for specific region
    void triggerEvent(String eventName, Region region);
    
    // Select settlements for event
    List<Settlement> selectSettlements(SelectionCriteria criteria);
    
    class SelectionCriteria {
        int maxAmount;
        int minAmount;
        Map<String, Object> filters; // RACE, CLASS, POPULATION, etc.
    }
}
```

### Multi-Target Event Structure
```txt
SHARED_NARRATIVE_EVENT: {
    OCCURRENCE: {
        REQUIRES: { GREATER: { WAR_SCORE: 200 } }
    },
    
    SELECTION: {
        # Can target multiple factions
        FACTIONS: {
            FILTERS: [
                { EQUAL: { FACTION_GROUP: ALLIANCE } }
            ],
            MAX_AMOUNT: { AMOUNT: 10 }
        }
    },
    
    CHOICES: [{
        ACTIONS: [
            # Applies to EACH selected faction
            { TYPE: BOOST_PERM, PLAYER: { MILITARY_READINESS>ADD: 0.2 } },
            { TYPE: NOTIFICATION, TEXT: "Die Allianz mobilisiert!" }
        ]
    }]
}
```

**Key Limitation:** Events sind **pro Settlement/Faction** instanziiert. Kein echtes "Shared Event" mit gemeinsamer State.

---

## 2. Shared Narrative Event Patterns für SyxCraft

### Pattern 1: Broadcast Event (One-to-Many)
```txt
# Core publishes via Bus, Modules reagieren
ALLIANCE_MOBILIZATION: {
    OCCURRENCE: { REQUIRES: { GREATER: { HORDE_THREAT: 100 } } },
    SELECTION: { FACTIONS: { FILTERS: [{ EQUAL: { FACTION_GROUP: ALLIANCE }}] }},
    CHOICES: [{
        ACTIONS: [
            { TYPE: BOOST_PERM, PLAYER: { DEFENSE_BONUS>ADD: 0.15 } },
            { TYPE: NOTIFICATION, TEXT: "Allianz-Mobilisierung: Verteidigungsbonus +15%" }
        ]
    }]
}
```

### Pattern 2: Coordinated Event (Shared State via Core)
```java
// Core State: Shared Narrative Progress
class NarrativeState {
    Map<String, Double> eventProgress = new HashMap<>(); // eventId -> 0.0-1.0
    Map<String, Long> eventTimestamps = new HashMap<>();
    
    void advanceEvent(String eventId, double delta) {
        eventProgress.merge(eventId, delta, Math::min);
    }
    
    boolean isEventComplete(String eventId) {
        return eventProgress.getOrDefault(eventId, 0.0) >= 1.0;
    }
}

// Event Choice adds to shared progress
SHARED_WAR_EFFORT: {
    CHOICES: [{
        ACTIONS: [
            { TYPE: EVENT, EVENT: CORE_ADVANCE_NARRATIVE, 
              PAYLOAD: { EVENT_ID: "WAR_EFFORT", AMOUNT: 0.1 } }
        ]
    }]
}
```

### Pattern 3: Cross-Faction Chain Events
```
HORDE_EVENT: ORC_CHIEFTAIN_CHALLENGE
    ↓ (Success)
ALLIANCE_EVENT: ALLIANCE_RESPONDS_TO_CHALLENGE
    ↓ (Both complete)
SHARED_EVENT: CHIEFTAIN_DUEL_RESOLUTION
```

---

## 3. SyxCraft Shared Narrative Events

### Event 1: "Die Große Invasion" (Alliance vs Horde)

```txt
GREAT_INVASION: {
    ICON: 32->MILITARY->INVASION,
    DURATION: { DAYS: 30.0 },
    
    OCCURRENCE: {
        REQUIRES: { 
            GREATER: { 
                WAR_SCORE_HORDE: 150,
                WAR_SCORE_ALLIANCE: 150
            }
        },
        MAX_SPAWNS: 1
    },
    
    SELECTION: {
        FACTIONS: {
            FILTERS: [
                { EQUAL: { FACTION_GROUP: ALLIANCE } },
                { EQUAL: { FACTION_GROUP: HORDE } }
            ]
        }
    },
    
    CHOICES: [
        {
            NAME: "Volle Mobilisierung",
            ACTIONS: [
                { TYPE: BOOST_PERM, PLAYER: { MILITARY_PRODUCTION>MUL: 1.5 } },
                { TYPE: RESOURCE_ADD, RESOURCE: MANPOWER, AMOUNT: 100 },
                { TYPE: EVENT, EVENT: INVASION_MOBILIZED }
            ]
        },
        {
            NAME: "Verteidigungshaltung",
            ACTIONS: [
                { TYPE: BOOST_PERM, PLAYER: { DEFENSE_BONUS>ADD: 0.25 } },
                { TYPE: RESOURCE_ADD, RESOURCE: FORTIFICATION_MATERIALS, AMOUNT: 50 },
                { TYPE: EVENT, EVENT: INVASION_DEFENSIVE }
            ]
        },
        {
            NAME: "Diplomatische Lösung suchen",
            ACTIONS: [
                { TYPE: FACTION_RELATION, FACTION: ENEMY_GROUP, VALUE: 10 },
                { TYPE: CREDITS, AMOUNT: -5000 },
                { TYPE: EVENT, EVENT: INVASION_DIPLOMACY }
            ]
        }
    ]
},

INVASION_MOBILIZED: {
    ON_SPAWN: {
        ACTIONS: [
            { TYPE: BOOST_PERM, PLAYER: { WAR_EFFORT>ADD: 1 } }
        ]
    }
}
```

### Event 2: "Der Seuchen-Ausbruch" (Affects All)

```txt
PLAGUE_OUTBREAK: {
    ICON: 32->LAW->PLAGUE,
    DURATION: { DAYS: 60.0 },
    
    OCCURRENCE: {
        REQUIRES: { GREATER: { TOTAL_POPULATION: 5000 } },
        MAX_SPAWNS: 1
    },
    
    SELECTION: {
        FACTIONS: { MAX_AMOUNT: { AMOUNT: 20 } }
    },
    
    CHOICES: [
        {
            NAME: "Quarantäne verhängen",
            ACTIONS: [
                { TYPE: BOOST_PERM, PLAYER: { TRADE_INCOME>MUL: 0.5 } },
                { TYPE: BOOST_PERM, PLAYER: { PLAGUE_RESISTANCE>ADD: 0.3 } },
                { TYPE: RESOURCE_ADD, RESOURCE: MEDICINE, AMOUNT: -100 }
            ]
        },
        {
            NAME: "Kräuterheilkunde einsetzen",
            ACTIONS: [
                { TYPE: BOOST_PERM, PLAYER: { HEALING_RATE>MUL: 1.5 } },
                { TYPE: RESOURCE_ADD, RESOURCE: HERBS, AMOUNT: -50 }
            ]
        },
        {
            NAME: "Opfer bringen (Undead Only)",
            REQUIRES: { RACE: UNDEAD },
            ACTIONS: [
                { TYPE: POPULATION_CLASS_ADD, CLASS: CITIZEN, RACE: UNDEAD, AMOUNT: -5 },
                { TYPE: BOOST_PERM, PLAYER: { PLAGUE_IMMUNITY>SET: 1 } }
            ]
        }
    ]
}
```

### Event 3: "Das Älteste Erwacht" (Night Elf + Undead Lore)

```txt
ANCIENT_AWAKENING: {
    ICON: 32->RELIGION->ANCIENT,
    DURATION: { DAYS: 1.0 },
    
    OCCURRENCE: {
        REQUIRES: { 
            EQUAL: { HAS_TECH: NIGHT_ELF_DRUIDISM },
            EQUAL: { HAS_TECH: UNDEAD_NECROMANCY }
        },
        MAX_SPAWNS: 1
    },
    
    SELECTION: {
        FACTIONS: {
            FILTERS: [
                { EQUAL: { RACE: NIGHT_ELF } },
                { EQUAL: { RACE: UNDEAD } }
            ]
        }
    },
    
    CHOICES: [
        {
            NAME: "Verbünden gegen die Bedrohung",
            ACTIONS: [
                { TYPE: FACTION_RELATION, FACTION: OTHER_GROUP, VALUE: 25 },
                { TYPE: EVENT, EVENT: ANCIENT_ALLIANCE_FORMED },
                { TYPE: BOOST_PERM, PLAYER: { ANCIENT_KNOWLEDGE>ADD: 0.5 } }
            ]
        },
        {
            NAME: "Die Macht für sich nutzen",
            ACTIONS: [
                { TYPE: BOOST_PERM, PLAYER: { DARK_POWER>ADD: 1.0 } },
                { TYPE: FACTION_RELATION, FACTION: OTHER_GROUP, VALUE: -30 },
                { TYPE: EVENT, EVENT: ANCIENT_BETRAYAL }
            ]
        }
    ]
}
```

---

## 4. Core Bus Integration for Shared Events

### Event Bus Types
```java
// Core Bus Events for Narrative Coordination
public sealed interface NarrativeEvent extends CoreEvent {
    record ChapterStarted(String chapterId, String title) implements NarrativeEvent {}
    record ChapterProgress(String chapterId, double progress) implements NarrativeEvent {}
    record ChapterCompleted(String chapterId, FactionGroup winner) implements NarrativeEvent {}
    record SharedChoiceMade(String eventId, String choiceId, FactionGroup faction) implements NarrativeEvent {}
}

// Publishing from Module
coreBus.publish(new NarrativeEvent.SharedChoiceMade("GREAT_INVASION", "MOBILIZE", ALLIANCE));

// Subscribing in other Modules
@Subscribe
void onSharedChoice(NarrativeEvent.SharedChoiceMade e) {
    if (e.eventId().equals("GREAT_INVASION") && e.factionGroup() != myFactionGroup) {
        // Enemy chose something - react
        adjustStrategy(e.choiceId());
    }
}
```

---

## 5. Data-Only Shared Events (No Java)

### Pure Data Approach via Boost Flags
```txt
# Event sets Boost Flag
SHARED_WAR_EFFORT: {
    CHOICES: [{
        ACTIONS: [
            { TYPE: BOOST_PERM, PLAYER: { WAR_EFFORT_CONTRIBUTION>ADD: 1 } }
        ]
    }]
}

# Other Module reads Boost
NIGHT_ELF_RESPONSE: {
    OCCURRENCE: {
        REQUIRES: { GREATER: { BOOST_WAR_EFFORT_CONTRIBUTION: 5 } }
    },
    CHOICES: [{
        ACTIONS: [
            { TYPE: BOOST_PERM, PLAYER: { ALLIANCE_SUPPORT>ADD: 0.1 } }
        ]
    }]
}
```

### Shared State via Core State Manager
```java
// Core State (persisted)
class SharedNarrativeState {
    Map<String, Double> chapterProgress = new HashMap<>();
    Map<String, Map<FactionGroup, Integer>> factionChoices = new HashMap<>();
    Map<String, Long> eventTimestamps = new HashMap<>();
    
    void recordChoice(String chapterId, FactionGroup group, String choiceId) {
        factionChoices.computeIfAbsent(chapterId, k -> new HashMap<>())
            .merge(group, 1, Integer::sum);
    }
    
    int getVotes(String chapterId, String choiceId) {
        return factionChoices.getOrDefault(chapterId, Map.of())
            .values().stream().mapToInt(Integer::intValue).sum();
    }
}
```

---

## 6. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Funktionieren `FACTIONS` Filter in Event Selection? | **UNVERIFIED** | HIGH |
| Werden Events pro Faction instanziiert oder shared? | **UNVERIFIED** | HIGH |
| Kann `FACTION_GROUP` als Filter genutzt werden? | **UNVERIFIED** | HIGH |
| Funktioniert `BOOST_PERM` cross-faction? | **UNVERIFIED** | HIGH |
| Event Chain über Core Bus persistiert bei Save/Load? | **UNVERIFIED** | CRITICAL |

---

## 7. Recommendations

| Pattern | Use Case | Implementation |
|---------|----------|----------------|
| Broadcast Event | Alliance-wide mobilization | Data Event + FACTIONS filter |
| Coordinated Progress | War effort, plague response | Core State Manager + Boost Flags |
| Chain Events | Lore events, betrayals | Core Bus + Event Actions |
| Shared Choice Voting | Diplomatic decisions | Core State Manager + Event |

---

*End of C3 — Shared Narrative Events Analysis*
*All findings from V71.44 analysis and Mod SDK review*