# Building Gate Architecture — Technical Analysis

> **Context:** Gebäude in Stadt A (Menschendorf) schaltet Funktion in Stadt B (Undead-Hauptstadt) frei.
> **Engine:** V71.44 | Mod SDK 0.1.5

---

## 1. Problem Analysis

### Requirements
| Requirement | Detail |
|-------------|--------|
| **Trigger** | Gebäude X im Menschendorf gebaut/upgegradet |
| **Effect** | Funktion Y in Undead-Hauptstadt freischalten |
| **Direction** | Einseitig: Menschendorf → Undead-Hauptstadt |
| **Persistence** | Save/Load fähig |
| **UI Feedback** | Spieler sieht freigeschaltete Optionen in Undead-Stadt |
| **Reversibility?** | Nein — einmal freigeschaltet bleibt freigeschaltet |

---

## 2. Available APIs (Mod SDK 0.1.5 / V71.44)

| API | Capability | Limitation |
|-----|------------|------------|
| **GameRoomsApi** | `getRooms()`, `getRoomByKey(key)` | **Read-only** Room Definitions — **kein Zugriff auf gebaute Instanzen** |
| **GameEventsApi** | `getEventResources()`, `builder()`, `registerEvent()` | **Runtime Event Creation möglich** |
| **GameFactionApi** | `getPlayer()`, `getFactions()`, `getPlayer().hasTech()` | Read-only Faction/Tech State |
| **GameFactionApi (V71)** | `requestSlaveTrade()`, `getDiplomaticActions()` | **New in V71** |
| **GameStatsApi** | `getBoostable()`, `getBoostable(name)` | **Boostables lesen/setzen** |
| **GameSaveApi** | `onGameSaved/Loaded`, `FilePutter/FileGetter` | **Custom State Persistence** |
| **GameUiApi** | `showNotification()`, `setResourceTooltip()`, `registerCustomPanel()` | UI Integration |
| **PhaseManager / StateManager** | `register(Phase, Phases)`, `getState()` | **Mod SDK Extension** |

### Critical Gap
> **Keine API für "Gebäude gebaut in Siedlung A → Event in Siedlung B"**
> - `GameRoomsApi` gibt nur **Definitions** zurück, keine Instanzen
> - **Kein** `BuildingBuiltEvent` im Event-System
> - **Kein** `SettlementListener` Interface

---

## 3. Architecture Options

### Option A: Tech Tree als Gate (Empfohlen — Native)
**Mechanik:** Tech `NECROMANCY_HUMAN_FARM` unlocked → Laws/Rooms available

```txt
# Tech Tree Gate (Native)
TECHS: {
  NECROMANCY_HUMAN_FARM: {
    UNLOCKS_FACTION: [ ROOM_HUMAN_PENS, ROOM_NECROPOLIS ],
    UNLOCKS_WORLD_BUILDING: [ WORLD_HUMAN_FARM ],
    UNLOCKS_LAW: [ UNDEAD_SLAVERY, UNDEAD_CONVERSION ],
    UNLOCKS_EVENT: [ FOUND_HUMAN_FARM ],
  }
}
```

| Vorteil | Nachteil |
|---------|----------|
| **100% Native** — keine Script-Logik nötig | **Kein Gebäude-Trigger** — Tech = Forschungsfortschritt, nicht Gebäude |
| Save/Load native | Kein Gebäude-Bau-Feedback |
| UI zeigt Tech Tree | Kein "Gebäude X gebaut → Y freigeschaltet" UX |

### Option B: Event-Driven (Script) — Building Built Detection

**Problem:** Kein `BUILDING_BUILT` Event in V71.

**Workaround: Periodic Scan in `ON_GAME_UPDATE`**

```java
public class BuildingGateManager {
    private static final Set<String> GATE_BUILDINGS = Set.of(
        "HUMAN_PENS", "NECROPOLIS", "INDOKTRINATIONSHALLE", "PROPAGANDATURM"
    );
    
    private final Set<String> unlockedFunctions = new HashSet<>();
    
    public void onGameUpdate(double dt) {
        // Scan Human Farm Settlement for built gate buildings
        Settlement humanFarm = getHumanFarmSettlement();
        if (humanFarm == null) return;
        
        for (String buildingKey : GATE_BUILDINGS) {
            if (isBuildingBuilt(humanFarm, buildingKey) && 
                !unlockedFunctions.contains(buildingKey)) {
                unlockFunction(buildingKey);
            }
        }
    }
    
    private boolean isBuildingBuilt(Settlement settlement, String buildingKey) {
        // Via Reflection or Mod SDK if available
        // Settlement.getBuiltRooms() → check for buildingKey
    }
    
    private void unlockFunction(String buildingKey) {
        unlockedFunctions.add(buildingKey);
        // Unlock via Tech/Boost/Event
        switch (buildingKey) {
            case "HUMAN_PENS": 
                apis.stats().getBoostable("HUMAN_PENS_UNLOCKED").setValue(1.0);
                break;
            case "NECROPOLIS":
                apis.stats().getBoostable("NECROPOLIS_UNLOCKED").setValue(1.0);
                break;
        }
    }
}
```

**Reflection Helper:**
```java
public class SettlementReflection {
    private static final Method GET_BUILT_ROOMS;
    private static final Field ROOM_INSTANCE_KEY;
    
    static {
        try {
            Class<?> settlementClass = Class.forName("settlement.main.SETT");
            GET_BUILT_ROOMS = settlementClass.getDeclaredMethod("getBuiltRooms");
            GET_BUILT_ROOMS.setAccessible(true);
            
            Class<?> roomInstanceClass = Class.forName("settlement.room.RoomInstance");
            ROOM_INSTANCE_KEY = roomInstanceClass.getDeclaredField("key");
            ROOM_INSTANCE_KEY.setAccessible(true);
        } catch (Exception e) {
            throw new RuntimeException("Reflection setup failed", e);
        }
    }
    
    public static Set<String> getBuiltRoomKeys(Settlement settlement) {
        try {
            List<?> rooms = (List<?>) GET_BUILT_ROOMS.invoke(settlement);
            return rooms.stream()
                .map(r -> (String) ROOM_INSTANCE_KEY.get(r))
                .collect(Collectors.toSet());
        } catch (Exception e) {
            return Set.of();
        }
    }
}
```

---

## 4. Architecture Comparison

| Kriterium | Option A: Tech Gate (Native) | Option B: Building Scan (Script) | Option C: Hybrid |
|-----------|------------------------------|----------------------------------|------------------|
| **Implementierungsaufwand** | Gering (Data Only) | Mittel (Script + Reflection) | Mittel |
| **Gameplay Feel** | Tech Tree Progression | **Gebäude-Bau = Progression** | Beide |
| **Save/Load** | Native | Custom State nötig | Hybrid |
| **UI Feedback** | Tech Tree zeigt Fortschritt | Benötigt Custom UI | Beide |
| **Flexibilität** | Gering (nur Tech Tree) | **Hoch** (beliebige Trigger) | Mittel |
| **Performance** | Optimal | Scan pro Tick (optimierbar) | Gut |
| **V71 Kompatibilität** | 100% | Reflection Risiko | Hoch |

---

## 4. Empfohlene Architektur: **Hybrid (Option C)**

### Core Principle
**Tech Tree = High-Level Gates** (Major Milestones)  
**Building Scan = Fine-Grained Unlocks** (Specific Functions)

### Implementation

#### 1. Major Gates via Tech Tree (Native)
```txt
# NECROMANCY_HUMAN_FARM.txt
TECHS: {
  NECROMANCY_HUMAN_FARM: {
    COSTS: { CIVIC_KNOWLEDGE: 200 },
    REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
    UNLOCKS_FACTION: [ ROOM_HUMAN_PENS, ROOM_NECROPOLIS ],
    UNLOCKS_WORLD_BUILDING: [ WORLD_HUMAN_FARM ],
    UNLOCKS_LAW: [ UNDEAD_SLAVERY, UNDEAD_CONVERSION ],
    UNLOCKS_EVENT: [ FOUND_HUMAN_FARM ],
  }
}
```

#### 2. Fine-Grained Unlocks via Building Scan (Script)

```java
public class BuildingGateManager {
    // Gate Definition
    private record Gate(String buildingKey, String unlockKey, String description) {}
    
    private static final List<Gate> GATES = List.of(
        new Gate("HUMAN_PENS", "UNDEAD_HUMAN_PENS", "Menschenställe für Sklavenhaltung"),
        new Gate("NECROPOLIS", "UNDEAD_NECROPOLIS", "Nekropole für Konvertierung"),
        new Gate("INDOKTRINATIONSHALLE", "UNDEAD_INDOCTRINATION", "Konditionierung der Sklaven"),
        new Gate("PROPAGANDATURM", "UNDEAD_PROPAGANDA", "Propaganda für Geist-Kontrolle"),
        new Gate("WELT_HUMAN_FARM", "UNDEAD_WORLD_FARM", "Weltkarten-Menschenfarm")
    );
    
    private final Map<String, Boolean> unlocked = new ConcurrentHashMap<>();
    
    public void onGameUpdate(double dt, GameApis apis) {
        Settlement humanFarm = getHumanFarm(apis);
        if (humanFarm == null) return;
        
        Set<String> builtKeys = SettlementReflection.getBuiltRoomKeys(humanFarm);
        
        for (Gate gate : GATES) {
            String unlockKey = gate.unlockKey();
            if (!unlocked.getOrDefault(unlockKey, false) && builtKeys.contains(gate.buildingKey())) {
                unlockFunction(unlockKey, apis);
            }
        }
    }
    
    private void unlockFunction(String unlockKey, GameApis apis) {
        unlocked.put(unlockKey, true);
        
        // 1. Boost setzen (für Room Requirements)
        apis.stats().getBoostable(unlockKey).setValue(1.0);
        
        // 2. Law Enactment (falls Law-Gate)
        if (unlockKey.startsWith("UNDEAD_LAW_")) {
            apis.laws().enactLaw(unlockKey.replace("UNDEAD_LAW_", ""));
        }
        
        // 3. UI Notification
        apis.ui().showNotification(
            "Neue Funktion freigeschaltet",
            "Durch Bau im Menschendorf: " + getDescription(unlockKey),
            NotificationType.SUCCESS, 10.0
        );
        
        // 3. Persist
        markDirty();
    }
}
```

#### 3. Room Requirements via Boostables

```txt
# V71/data/init/room/NECROPOLIS.txt
_ignoreVanilla: true,
ICON: 32->UNDEAD->NECROPOLIS,
RESOURCES: [STONE, METAL, MACHINERY, FURNITURE, ESSENCE],
FLOOR: [STONE2, STONE1, DIRT],
REQUIRES_BOOST: { UNDEAD_NECROPOLIS_UNLOCKED: 1.0 },
# ... rest
```

---

## 5. Save/Load State

```java
public class BuildingGateStateManager {
    private static final String SAVE_KEY = "SYXCRAFT_BUILDING_GATES";
    
    public void onGameSaved(Path path, FilePutter putter, Map<String, Boolean> unlocked) {
        putter.mark(1)
            .chars("VERSION").chars("1")
            .chars("COUNT").chars(String.valueOf(unlocked.size()));
        
        for (Map.Entry<String, Boolean> entry : unlocked.entrySet()) {
            putter.chars(entry.getKey()).chars(String.valueOf(entry.getValue()));
        }
    }
    
    public Map<String, Boolean> load(Path path, FileGetter getter) {
        getter.check();
        int version = Integer.parseInt(getter.chars("VERSION"));
        int count = Integer.parseInt(getter.chars("COUNT"));
        
        Map<String, Boolean> unlocked = new HashMap<>();
        for (int i = 0; i < count; i++) {
            String key = getter.chars("KEY_" + i);
            String val = getter.chars("VAL_" + i);
            unlocked.put(key, Boolean.parseBoolean(val));
        }
        return unlocked;
    }
}
```

---

## 5. Room Requirements via Boostables

```txt
# NECROPOLIS.txt
_ignoreVanilla: true,
ICON: 32->UNDEAD->NECROPOLIS,
RESOURCES: [STONE, METAL, MACHINERY, FURNITURE, ESSENCE],
FLOOR: [STONE2, STONE1, DIRT],
REQUIRES_BOOST: { UNDEAD_NECROPOLIS_UNLOCKED: 1.0 },
# ...
```

```java
// In Room Validation (Engine)
public boolean canBuild(RoomBlueprintImp blueprint) {
    for (Map.Entry<String, Double> req : blueprint.getRequiredBoosts().entrySet()) {
        Boostable boost = gameStatsApi.getBoostable(req.getKey());
        if (boost == null || boost.getValue() < req.getValue()) {
            return false; // Requirement not met
        }
    }
    return true;
}
```

---

## 6. UI Integration

### 4.1 Notification on Unlock
```java
apis.ui().showNotification(
    "Neue Funktion freigeschaltet",
    "Durch Bau im Menschendorf: " + gate.description(),
    NotificationType.SUCCESS, 10.0
);
```

### 4.2 Custom Panel: Menschendorf-Management
```java
public class HumanFarmPanelBuilder implements PanelBuilder {
    @Override
    public void build(PanelContext ctx) {
        ctx.addLabel("Menschendorf — Freigeschaltete Funktionen");
        
        for (Gate gate : BuildingGateManager.GATES) {
            boolean unlocked = BuildingGateManager.isUnlocked(gate.unlockKey());
            ctx.addRow(row -> {
                row.addLabel(gate.description());
                row.addLabel(unlocked ? "✓ Freigeschaltet" : "🔒 Gesperrt");
                if (!unlocked) {
                    row.addTooltip("Bau im Menschendorf: " + gate.buildingKey());
                }
            });
        }
    }
}
```

---

## 6. Open Risks (UNVERIFIED)

| Risk | Impact | Verification |
|------|--------|--------------|
| `SettlementReflection.getBuiltRoomKeys()` works in V71 | **HIGH** — Reflection break on update | Test in Dev Build |
| `Boostable` for Room Requirements works | **MEDIUM** | Test Room Requirement UI |
| `GameStatsApi.getBoostable()` creates new if missing? | **MEDIUM** | Test `getBoostable("NEW_KEY")` |
| Scan Performance: 100+ Buildings per Tick | **LOW** | Cache built keys, scan only on `ON_GAME_SAVED` + `ON_GAME_UPDATE` 1x/day |
| Save/Load Order with Mod SDK | **LOW** | Test Save → Load → Gates persist |

---

## 7. Recommendation Summary

| Approach | Use Case |
|----------|----------|
| **Tech Tree Gates** | Major Milestones (Human Farm, Necropolis, Conversion) |
| **Building Scan** | Fine-Grained (Indoktrination, Propaganda, Wachturm, etc.) |
| **Hybrid** | **EMPFOHLEN** — Best of both Worlds |

---

*End of Building Gate Architecture Analysis*