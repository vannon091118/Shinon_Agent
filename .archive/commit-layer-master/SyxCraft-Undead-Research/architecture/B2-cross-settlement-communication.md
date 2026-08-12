# B2 — Cross-Settlement State Communication Analysis

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — Architecture Decision Documented

---

## 1. The Core Problem

**Undead-Spieler managt ZWEI Settlements gleichzeitig:**
1. **Undead Capital** (Native Capital Settlement)
2. **Human Village** (Simulated Second Settlement)

**Beide Settlements teilen KEINE Ressourcen — komplett getrennte Economies.**

**Aber:** Gebäude im Human Village schalten Funktionen in der Undead Capital frei (Gate System).
Und: Geist-System im Human Village wird durch Gebäude in der Undead Capital beeinflusst.

**Frage:** Wie kommuniziert State zwischen zwei Settlements?

---

## 2. Native Engine Capabilities

### Settlement Structure (from JAR)
```java
// Faction has ONE capital settlement
class Faction {
    Settlement capital;           // THE capital
    List<Settlement> settlements; // Only capital for player
    Region capitalRegion;
}

// Settlement
class Settlement {
    String name;
    Region region;
    Faction faction;
    Stockpile stockpile;
    Population population;
    List<Room> rooms;
    StatsGovernment government;
    StatsLaw law;
}
```

### GameFactionApi — Settlement Access
```java
interface GameFactionApi {
    // Get player's capital settlement
    Settlement getCapital();
    
    // Get all settlements (only capital for player)
    List<Settlement> getSettlements();
    
    // Get settlement by region
    Optional<Settlement> getSettlement(Region region);
}
```

### GameSaveApi — Custom State
```java
interface GameSaveApi {
    // Save custom data per script instance
    void put(String key, Serializable value);
    <T> Optional<T> get(String key, Class<T> type);
    
    // Per-settlement state?
    void putForSettlement(Settlement s, String key, Serializable value);
    <T> Optional<T> getFromSettlement(Settlement s, String key, Class<T> type);
}
```

**KRITISCH:** `GameSaveApi` hat KEINE per-Settlement Methoden im SDK!
Nur global pro Script Instance.

---

## 3. Cross-Settlement Communication Options

### Option A — Boost Flags (Native, No Shared State)
```java
// Undead Capital builds Wachturm
// Setzt Boost Flag
apis.stats().getBoostable("UNDEAD_GATE_WACHTURM_BUILT").setValue(1.0);

// Human Village Script liest Boost
boolean hasWatchtower = apis.stats().getBoostable("UNDEAD_GATE_WACHTURM_BUILT").getValue() > 0;
```

**Pro:** Native, keine Java-Kommunikation nötig
**Con:** Boosts sind global pro Faction, nicht pro Settlement

---

### Option B — GameEventsApi (Event-Driven)
```java
// Undead Capital: Building gebaut
apis.events().triggerEvent("BUILDING_BUILT", humanVillageRegion, 
    Map.of("building", "WACHTTURM", "owner", "UNDEAD_CAPITAL"));

// Human Village: Event listener
apis.events().onEvent("BUILDING_BUILT", ctx -> {
    if ("WACHTTURM".equals(ctx.get("building"))) {
        geistManager.reduceDecayRate(0.2);
    }
});
```

**Pro:** Native Event System, loose coupling
**Con:** Events sind transient, nicht persistiert

---

### Option C — Core State Manager (Java, Recommended)
```java
// Core verwaltet State für BEIDE Settlements
public class CoreStateManager {
    // Per-Settlement State Maps
    private final Map<Integer, SettlementState> settlementStates = new HashMap<>();
    
    // Key: Region ID
    public void setSettlementState(int regionId, SettlementState state) { ... }
    public SettlementState getSettlementState(int regionId) { ... }
    
    // Save/Load
    public void onGameSaved(FilePutter putter) {
        putter.mark(1);
        putter.chars("SETTLEMENT_COUNT").chars(String.valueOf(settlementStates.size()));
        for (var entry : settlementStates.entrySet()) {
            putter.chars("SETTLEMENT_" + entry.getKey()).chars(entry.getValue().serialize());
        }
    }
    
    public void onGameLoaded(FileGetter getter) {
        getter.check();
        int count = Integer.parseInt(getter.chars("SETTLEMENT_COUNT"));
        for (int i = 0; i < count; i++) {
            int regionId = Integer.parseInt(getter.chars("SETTLEMENT_" + i + "_ID"));
            SettlementState state = SettlementState.deserialize(getter.chars("SETTLEMENT_" + i + "_DATA"));
            settlementStates.put(regionId, state);
        }
    }
}

public class SettlementState {
    int regionId;
    String settlementType; // "UNDEAD_CAPITAL" | "HUMAN_VILLAGE"
    Map<String, Double> boosts;
    Map<String, Integer> buildingCounts;
    Map<String, Object> customData;
}
```

**Usage in Modules:**
```java
// Undead Module schreibt
coreState.setSettlementState(undeadCapitalRegionId, 
    state.withBoost("UNDEAD_GATE_MILITARY", true));

// Human Module liest
boolean hasMilitary = coreState.getSettlementState(humanVillageRegionId)
    .getBoost("UNDEAD_GATE_MILITARY", false);
```

---

## 4. Gate System Implementation (Building → Function)

### Gate Definition (Data-Driven)
```txt
# V71/data/init/gates/GATES.txt
_ignoreVanilla: true,
GATES: {
    MILITARY: {
        TRIGGER_BUILDING: BARRACKS,           // In Human Village
        UNLOCKS: UNDEAD_MILITARY_BUILDINGS,   // In Undead Capital
        BOOST_KEY: UNDEAD_GATE_MILITARY,
        DESCRIPTION: "Menschendorf Kaserne → Untote Militärgebäude"
    },
    CONVERSION: {
        TRIGGER_BUILDING: GRANARY,            // In Human Village
        UNLOCKS: UNDEAD_CONVERSION_EVENT,     // In Undead Capital
        BOOST_KEY: UNDEAD_GATE_CONVERSION,
        DESCRIPTION: "Menschendorf Getreidespeicher → Konversion freischalten"
    },
    GEIST_DECAY_REDUCTION: {
        TRIGGER_BUILDING: WATCHTOWER,         // In Human Village
        UNLOCKS: GEIST_DECAY_REDUCTION_20,    // In Undead Capital
        BOOST_KEY: UNDEAD_GATE_WATCHTOWER,
        EFFECT: { GEIST_DECAY_RATE>MUL: 0.8 },
        DESCRIPTION: "Menschendorf Wachturm → Geist-Verfall -20%"
    }
}
```

### Gate Manager (Core)
```java
public class GateManager {
    private final CoreStateManager coreState;
    private final GameApis apis;
    
    void update() {
        // Scan Human Village for gate buildings
        Settlement humanVillage = getHumanVillage();
        if (humanVillage == null) return;
        
        for (Gate gate : GATES) {
            String boostKey = gate.boostKey();
            boolean alreadyUnlocked = coreState.getBoost(undeadCapitalRegionId, boostKey);
            
            if (!alreadyUnlocked && hasBuilding(humanVillage, gate.triggerBuilding())) {
                unlockGate(gate);
            }
        }
    }
    
    private void unlockGate(Gate gate) {
        // 1. Set Boost Flag
        coreState.setBoost(undeadCapitalRegionId, gate.boostKey(), true);
        
        // 2. Notify Player
        apis.ui().showNotification(
            "Neue Funktion freigeschaltet!",
            gate.description(),
            NotificationType.SUCCESS
        );
        
        // 3. Publish Core Event
        coreBus.publish(new GateUnlockedEvent(gate.key()));
    }
    
    private boolean hasBuilding(Settlement settlement, String buildingKey) {
        return settlement.getRooms().stream()
            .anyMatch(r -> r.getKey().equalsIgnoreCase(buildingKey));
    }
}
```

---

## 5. Geist System Cross-Settlement

### Geist State (Human Village)
```java
public class GhostState {
    // Human Village Region ID
    private final int humanVillageRegionId;
    
    // Components (0.0 - 1.0)
    private double controlLevel = 0.0;      // From Undead Capital buildings
    private double fearLevel = 0.0;         // From Human Village buildings
    private double conditioningLevel = 0.0; // From both
    
    // Computed Geist (0.0 = full control, 1.0 = rebellion)
    private double geistValue = 0.5;
    
    // Update from BOTH settlements
    public void update(int controlBuildingsUndead, int fearBuildingsHuman, int conditioningBuildingsBoth) {
        // Control from Undead Capital
        controlLevel = Math.min(controlBuildingsUndead * 0.02, 0.5);
        
        // Fear from Human Village
        fearLevel = Math.min(fearBuildingsHuman * 0.03, 0.6);
        
        // Conditioning from both
        conditioningLevel = Math.min((controlBuildingsUndead + fearBuildingsHuman) * 0.005, 0.8);
        
        // Compute Geist
        geistValue = (1.0 - controlLevel) * 0.5 
                   + fearLevel * 0.3 
                   + (1.0 - conditioningLevel) * 0.2;
    }
    
    public double getGeistValue() { return geistValue; }
}
```

### Geist Manager (Core)
```java
public class GhostManager {
    private final CoreStateManager coreState;
    private final int humanVillageRegionId;
    private final int undeadCapitalRegionId;
    
    void update() {
        // Count buildings in BOTH settlements
        int controlBuildings = countBuildings(undeadCapitalRegionId, 
            Set.of("WACHTTURM", "GARNISON", "KERKER", "UEBERWACHUNGSTURM"));
        int fearBuildings = countBuildings(humanVillageRegionId,
            Set.of("GALGEN", "FOLTERKAMMER", "OEFFENTLICHE_HINRICHTUNG"));
        int conditioningBuildings = countBuildings(undeadCapitalRegionId,
            Set.of("INDOKTRINATIONSHALLE", "PROPAGANDATURM", "RITUALSTAETTE"));
        
        // Update Geist State
        GhostState geist = coreState.getGhostState(humanVillageRegionId);
        geist.update(controlBuildings, fearBuildings, conditioningBuildings);
        
        // Check thresholds
        if (geist.getGeistValue() >= 0.7 && !geist.wasRebellionTriggered()) {
            triggerRebellion();
        }
    }
}
```

---

## 6. Save/Load Strategy

### Per-Settlement State Serialization
```java
// CoreStateManager.save()
public void onGameSaved(FilePutter putter) {
    putter.mark(1); // Version
    
    // Undead Capital State
    putter.chars("UC_REGION_ID").chars(String.valueOf(undeadCapitalRegionId));
    putter.chars("UC_STATE").chars(undeadCapitalState.serialize());
    
    // Human Village State
    putter.chars("HV_REGION_ID").chars(String.valueOf(humanVillageRegionId));
    putter.chars("HV_STATE").chars(humanVillageState.serialize());
    
    // Ghost State
    putter.chars("GHOST_STATE").chars(ghostState.serialize());
    
    // Gates
    putter.chars("GATES_COUNT").chars(String.valueOf(unlockedGates.size()));
    int i = 0;
    for (String gate : unlockedGates) {
        putter.chars("GATE_" + i).chars(gate);
        i++;
    }
}

// CoreStateManager.load()
public void onGameLoaded(FileGetter getter) {
    getter.check(); // Version
    
    undeadCapitalRegionId = Integer.parseInt(getter.chars("UC_REGION_ID"));
    undeadCapitalState = SettlementState.deserialize(getter.chars("UC_STATE"));
    
    humanVillageRegionId = Integer.parseInt(getter.chars("HV_REGION_ID"));
    humanVillageState = SettlementState.deserialize(getter.chars("HV_STATE"));
    
    ghostState = GhostState.deserialize(getter.chars("GHOST_STATE"));
    
    int gateCount = Integer.parseInt(getter.chars("GATES_COUNT"));
    for (int i = 0; i < gateCount; i++) {
        unlockedGates.add(getter.chars("GATE_" + i));
    }
}
```

---

## 7. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Funktioniert `FilePutter/FileGetter` für komplexe nested State? | **UNVERIFIED** | CRITICAL |
| Können Boosts per Settlement unterschieden werden? | **UNVERIFIED** | HIGH |
| Funktioniert `GameEventsApi` Cross-Settlement? | **UNVERIFIED** | HIGH |
| Persistiert `CoreStateManager` State korrekt bei Save/Load? | **UNVERIFIED** | CRITICAL |
| Kann `GameSaveApi` per Settlement speichern? | **UNVERIFIED** | HIGH |

---

## 8. Recommendations

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| State Storage | Core State Manager (Java) | Vollkontrolle, typsicher, persistiert |
| Gate Detection | Scan Human Village Buildings each tick | Einfach, zuverlässig |
| Geist Calculation | Core Manager (reads both settlements) | Single Source of Truth |
| Cross-Communication | Core Bus Events + Boost Flags | Dual-Layer: Events für UI, Boosts für Logic |
| Save/Load | Core State Manager serialisiert alles | Atomar, versioniert |

---

*End of B2 — Cross-Settlement State Communication Analysis*
*All findings from V71.44 analysis and Mod SDK review*