# B3 — Gate System Engine Analysis

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — Architecture Decision Documented

---

## 1. The Gate Concept

**Definition:** Ein Gebäude in Siedlung A (Human Village) schaltet eine Funktion in Siedlung B (Undead Capital) frei.

**Für SyxCraft MVP Gates:**
| Gate | Building in Human Village | Unlocks in Undead Capital |
|------|--------------------------|---------------------------|
| MILITARY | BARRACKS (Kaserne) | Undead Militärgebäude |
| CONVERSION | GRANARY (Getreidespeicher) | UNDEAD_CONVERSION Event |
| GEIST_DECAY | WATCHTOWER (Wachturm) | Geist-Decay -20% |

---

## 2. Native Engine Options Analysis

### Option 1: Room BOOST System (Native)

```txt
# Race.txt
BOOST: {
    ROOM_BARRACKS>MUL: 1.5,  // Aber: wirkt nur in GLEICHER Settlement
}
```

**Problem:** Boosts aus Race.txt wirken **nur in der eigenen Settlement**.
Kein nativer Cross-Settlement Boost.

---

### Option 2: Shared Boostable (GameStatsApi)

```java
// GameStatsApi
interface GameStatsApi {
    // Boostable sind global pro Faction
    Boostable getBoostable(String key);
    
    // Kann man Settlement-spezifische Boosts erstellen?
    Boostable createBoostable(String key, Settlement settlement);
}
```

**SDK Analysis:** `GameStatsApi` bietet nur **faction-weite** Boostables.
Keine Settlement-spezifischen Boostables im SDK.

---

### Option 3: GameEventsApi (Build Event → Unlock)

```java
// Event: BUILDING_BUILT
// Payload: { building: "BARRACKS", region: humanVillageRegion }

// Listener in Undead Module
apis.events().onEvent("BUILDING_BUILT", ctx -> {
    if ("BARRACKS".equals(ctx.get("building")) 
        && isHumanVillageRegion(ctx.getRegion())) {
        // Set Unlock Flag
        coreState.setGateUnlocked("MILITARY", true);
    }
});
```

**Pro:** Native Event System
**Con:** Events sind transient, nicht persistiert bei Save/Load

---

### Option 4: Custom State + Building Scan (Recommended)

```java
// GateManager scannt Human Village Buildings jeden Tick
public class GateManager {
    void update() {
        Settlement humanVillage = getHumanVillage();
        if (humanVillage == null) return;
        
        for (Gate gate : GATES) {
            if (!coreState.isGateUnlocked(undeadCapitalRegionId, gate.key())) {
                if (hasBuilding(humanVillage, gate.triggerBuilding())) {
                    unlockGate(gate);
                }
            }
        }
    }
    
    private boolean hasBuilding(Settlement settlement, String buildingKey) {
        return settlement.getRooms().stream()
            .anyMatch(r -> r.getKey().equalsIgnoreCase(buildingKey));
    }
}
```

**Pro:** 
- Kein Event-System nötig
- Automatisch korrekt nach Save/Load (Buildings bleiben)
- Keine Race Conditions
- Funktioniert ohne SDK-Erweiterung

**Con:** Scan jeden Tick (aber nur wenige Buildings, vernachlässigbar)

---

## 3. Gate System Implementation (Recommended)

### Data-Driven Gates
```txt
# V71/data/init/gates/GATES.txt
_ignoreVanilla: true,
GATES: {
    MILITARY: {
        TRIGGER_BUILDING: BARRACKS,
        UNLOCKS: UNDEAD_MILITARY_BUILDINGS,
        BOOST_KEY: UNDEAD_GATE_MILITARY,
        NOTIFICATION: "Militärgebäude freigeschaltet!"
    },
    CONVERSION: {
        TRIGGER_BUILDING: GRANARY,
        UNLOCKS: UNDEAD_CONVERSION_EVENT,
        BOOST_KEY: UNDEAD_GATE_CONVERSION,
        NOTIFICATION: "Konversion freigeschaltet!"
    },
    GEIST_DECAY: {
        TRIGGER_BUILDING: WATCHTOWER,
        UNLOCKS: GEIST_DECAY_REDUCTION,
        BOOST_KEY: UNDEAD_GATE_WATCHTOWER,
        EFFECT: { GEIST_DECAY_RATE>MUL: 0.8 },
        NOTIFICATION: "Geist-Stabilität verbessert!"
    }
}
```

### Gate Manager Implementation
```java
public class GateManager {
    private final CoreStateManager coreState;
    private final GameApis apis;
    private final CoreBus bus;
    private final Set<String> unlockedGates = new HashSet<>();
    
    // Gate Definitions (could be loaded from Data File)
    private static final List<Gate> GATES = List.of(
        new Gate("MILITARY", "BARRACKS", "UNDEAD_GATE_MILITARY", 
                 "Menschendorf Kaserne → Untote Militärgebäude"),
        new Gate("CONVERSION", "GRANARY", "UNDEAD_GATE_CONVERSION",
                 "Menschendorf Getreidespeicher → Konversion freischalten"),
        new Gate("GEIST_DECAY", "WATCHTOWER", "UNDEAD_GATE_WATCHTOWER",
                 "Menschendorf Wachturm → Geist-Verfall -20%")
    );
    
    void update() {
        Settlement humanVillage = getHumanVillage();
        if (humanVillage == null) return;
        
        for (Gate gate : GATES) {
            String boostKey = gate.boostKey();
            
            // Already unlocked?
            if (coreState.isBoostActive(undeadCapitalRegionId, boostKey)) continue;
            
            // Check trigger building
            if (hasBuilding(humanVillage, gate.triggerBuilding())) {
                unlockGate(gate);
            }
        }
    }
    
    private void unlockGate(Gate gate) {
        // 1. Activate Boost Flag
        coreState.setBoost(undeadCapitalRegionId, gate.boostKey(), true);
        
        // 2. Track as unlocked
        unlockedGates.add(gate.key());
        
        // 3. Notify Player
        apis.ui().showNotification(
            "Neue Funktion freigeschaltet!",
            gate.description(),
            GameUiApi.NotificationType.SUCCESS,
            10.0
        );
        
        // 4. Publish Event for other modules
        bus.publish(new GateUnlockedEvent(gate.key(), gate.boostKey()));
        
        // 5. Log
        System.out.println("[GateManager] Unlocked: " + gate.key());
    }
    
    private boolean hasBuilding(Settlement settlement, String buildingKey) {
        try {
            // Use reflection to access built rooms
            var rooms = ReflectionUtil.getFieldValue(settlement, "rooms");
            if (rooms instanceof List) {
                return ((List<?>) rooms).stream()
                    .anyMatch(r -> buildingKey.equalsIgnoreCase(
                        ReflectionUtil.getFieldValue(r, "key")));
            }
        } catch (Exception e) {
            // Silent fail
        }
        return false;
    }
    
    // Save/Load
    void onGameSaved(FilePutter putter) {
        putter.mark(1)
            .chars("UNLOCKED_GATES_COUNT").chars(String.valueOf(unlockedGates.size()));
        int i = 0;
        for (String gate : unlockedGates) {
            putter.chars("GATE_" + i).chars(gate);
            i++;
        }
    }
    
    void onGameLoaded(FileGetter getter) {
        getter.check();
        int count = Integer.parseInt(getter.chars("UNLOCKED_GATES_COUNT"));
        for (int i = 0; i < count; i++) {
            unlockedGates.add(getter.chars("GATE_" + i));
        }
    }
}
```

---

## 4. Room Requirements (Gate Enforcement)

### Undead Military Buildings — Require Gate
```txt
# V71/data/init/room/UNDEAD_BARRACKS.txt
_ignoreVanilla: true,
ICON: 32->UNDEAD->BARRACKS,
RESOURCES: [WOOD, STONE, METAL],
AREA_COSTS: [0, 0, 0, 0],
FLOOR: [DIRT, WOOD, STONE2],
MINI_COLOR: 150_50_50,

# GATE REQUIREMENT: Military Gate must be unlocked
REQUIRES_BOOST: UNDEAD_GATE_MILITARY,

VALUE_DEGRADE_PER_YEAR: 0.05,
VALUE_PER_WORKER: 0,
VALUE_WORK_SPEED: 1,
BOOST: UNDEAD_MILITARY,

CONSUMPTION: {
    FOOD_MEAT: { RATE: 1.0, BONUS: 0.2 },
    ESSENCE: { RATE: 0.1, BONUS: 0.05 },
},

WORK: {
    SHIFT_OFFSET: 0.25,
    SOUND: MILITARY,
    USES_TOOL: false,
    FULFILLMENT: 0.5,
},

OUTPUT: {
    RESOURCE: UNDEAD_SOLDIER,
    BASE_RATE: 0.1,
    BONUS_PER_LEVEL: 0.05,
    MAX_WORKERS: 20,
},
```

### Conversion Event — Requires Gate
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
            } 
        }
    },
    ...
}
```

---

## 5. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Funktioniert `REQUIRES_BOOST` in Room.txt? | **UNVERIFIED** | CRITICAL |
| Funktioniert `REQUIRES.EQUAL.BOOST_X` in Event? | **UNVERIFIED** | CRITICAL |
| Scannt `Settlement.getRooms()` alle gebauten Rooms? | **UNVERIFIED** | HIGH |
| Performance: Building Scan jeden Tick? | **UNVERIFIED** | LOW |
| Persistieren Boost-Flags via Core State korrekt? | **UNVERIFIED** | CRITICAL |

---

## 6. Recommendation

**Ansatz: Building Scan + Core State Boost Flags**

| Layer | Implementation |
|-------|----------------|
| **Detection** | GateManager scannt Human Village Buildings jeden Tick |
| **State** | CoreStateManager hält Boost-Flags pro Settlement |
| **Enforcement** | Room/Event `REQUIRES_BOOST` / `REQUIRES.EQUAL.BOOST` |
| **Persistence** | CoreStateManager Save/Load |
| **UI Feedback** | GameUiApi Notification beim Unlock |

**Warum nicht Events?** Events sind transient, nicht persistiert. Building Scan ist deterministisch und funktioniert nach Save/Load automatisch.

**Warum nicht Native Boosts?** SDK bietet nur faction-weite Boosts, keine per-Settlement.

---

*End of B3 — Gate System Engine Analysis*
*All findings from V71.44 analysis and Mod SDK review*