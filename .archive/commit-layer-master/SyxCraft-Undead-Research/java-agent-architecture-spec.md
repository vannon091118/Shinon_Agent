# Java Agent Architecture Specification — SyxCraft Undead

> **Purpose:** Clear contracts for multiple independent coding agents working on the Undead mod.
> **Principle:** Agents must never break each other's code. Clear boundaries, explicit permissions.

---

## 1. Architecture Overview

```
SyxCraft-Undead (Maven Module)
├── src/main/java/com/syxcraft/undead/
│   ├── UndeadScript.java                    # ENTRY POINT — implements SCRIPT
│   ├── instance/
│   │   └── UndeadInstance.java              # SCRIPT_INSTANCE — all game loops
│   ├── state/
│   │   ├── GhostState.java                  # Geist State + Update Logic
│   │   ├── HumanFarmState.java              # Farm State (Level, Captives, Upgrades)
│   │   └── ConversionState.java             # Conversion Cooldowns, Stats
│   ├── manager/
│   │   ├── HumanFarmManager.java            # Farm Logic, Building Gates
│   │   ├── ConversionManager.java           # Conversion Logic, Cooldowns
│   │   ├── OrcTradeManager.java             # Orc Trade, Diplomatic Actions
│   │   ├── GateManager.java                 # Building Gates, Feature Flags
│   │   └── GhostManager.java                # Geist Update, Events, UI
│   ├── event/
│   │   └── UndeadEventBuilder.java          # Runtime Event Creation
│   ├── util/
│   │   ├── UndeadUtils.java                 # Helpers: Race Checks, Resource Access
│   │   ├── SettlementReflection.java        # Reflection on Engine Classes
│   │   └── ReflectionUtil.java              # Safe Reflection Wrapper
│   └── constant/
│       └── UndeadConstants.java             # All String Keys, Boost Names, Event Names
├── src/main/resources/mod-files/
│   ├── _Info.txt
│   └── data/init/...                        # All .txt Data Files
└── src/test/...                             # Unit + Integration Tests
```

---

## 2. Entry Points — Strict Boundaries

### 2.1 UndeadScript (SCRIPT Entry Point)
```java
package com.syxcraft.undead;

import script.SCRIPT;

public final class UndeadScript implements SCRIPT {
    
    // Constants — NO logic here
    private static final INFO INFO = new INFO("SyxCraft Undead Overhaul", "WoW-inspired Undead faction with dual-city management");
    
    @Override public CharSequence name() { return INFO.name; }
    @Override public CharSequence desc() { return INFO.desc; }
    @Override public boolean initBeforeGameCreated() { return false; }
    @Override public boolean isSelectable() { return true; }
    @Override public boolean forceInit() { return false; }
    
    // ONLY creates Instance — NO LOGIC
    @Override
    public SCRIPT_INSTANCE createInstance() {
        return new UndeadInstance();
    }
}
```

**Agents MAY:**
- Modify `INFO` constants
- Add/remove `initBeforeGameCreated`, `isSelectable`, `forceInit` overrides

**Agents MUST NOT:**
- Add any logic in this class
- Add fields/dependencies
- Call any Engine APIs

---

### 2.2 UndeadInstance (SCRIPT_INSTANCE — The Only Logic Container)

```java
package com.syxcraft.undead.instance;

import script.SCRIPT_INSTANCE;
import com.github.argon.sos.mod.sdk.phase.PhaseManager;
import com.github.argon.sos.mod.sdk.phase.state.StateManager;
import com.github.argon.sos.mod.sdk.api.GameApis;
import com.github.argon.sos.mod.sdk.properties.PropertiesStore;

public final class UndeadInstance implements SCRIPT_INSTANCE {
    
    // Managers — Initialized in constructor, NEVER null
    private final HumanFarmManager humanFarmManager;
    private final ConversionManager conversionManager;
    private final OrcTradeManager orcTradeManager;
    private final GhostManager ghostManager;
    private final GateManager gateManager;
    
    // State — Persisted via Save/Load
    private final GhostState ghostState;
    private final HumanFarmState farmState;
    private final ConversionState conversionState;
    
    // Dependencies (Injected via Mod SDK)
    private final GameApis gameApis;
    private final PhaseManager phaseManager;
    private final StateManager stateManager;
    private final PropertiesStore propertiesStore;
    
    // Constructor — ONLY place for initialization
    public UndeadInstance(
        PhaseManager phaseManager,
        StateManager stateManager,
        GameApis gameApis,
        PropertiesStore propertiesStore
    ) {
        this.phaseManager = phaseManager;
        this.stateManager = stateManager;
        this.gameApis = gameApis;
        this.propertiesStore = propertiesStore;
        
        // Initialize State FIRST (needed by Managers)
        this.ghostState = new GhostState();
        this.farmState = new HumanFarmState();
        this.conversionState = new ConversionState();
        
        // Initialize Managers (inject State + APIs)
        this.humanFarmManager = new HumanFarmManager(farmState, gameApis, propertiesStore);
        this.conversionManager = new ConversionManager(conversionState, gameApis);
        this.orcTradeManager = new OrcTradeManager(gameApis);
        this.ghostManager = new GhostManager(ghostState, gameApis);
        this.gateManager = new GateManager(gameApis);
        
        // Register SDK Phases
        registerPhases();
    }
    
    // SCRIPT_INSTANCE Interface Methods — DELEGATE ONLY
    @Override public void update(double dt) {
        ghostManager.update(dt);
        humanFarmManager.update(dt);
        conversionManager.update(dt);
        orcTradeManager.update(dt);
        gateManager.update();
    }
    
    @Override public void initBeforeGameCreated() { /* Delegate */ }
    @Override public void initBeforeGameInited() { /* Delegate */ }
    @Override public void initNewGameSession() { /* Delegate */ }
    @Override public void onGameLoaded(Path path, FileGetter getter) { /* Delegate */ }
    @Override public void onGameSaved(Path path, FilePutter putter) { /* Delegate */ }
    @Override public void onGameSaveReloaded() { /* Delegate */ }
    @Override public void onBeforeBattle() { /* Delegate */ }
    @Override public void onBattle() { /* Delegate */ }
    @Override public void onAfterBattle() { /* Delegate */ }
    @Override public void onCrash(Throwable t) { /* Delegate */ }
    @Override public boolean handleBrokenSavedState() { return false; }
    
    // Phase Registration — ONLY here
    private void registerPhases() {
        phaseManager.register(Phase.INIT_NEW_GAME_SESSION, Phases.INIT_NEW_GAME_SESSION);
        phaseManager.register(Phase.ON_GAME_UPDATE, Phases.ON_GAME_UPDATE);
        phaseManager.register(Phase.ON_GAME_SAVED, Phases.ON_GAME_SAVED);
        phaseManager.register(Phase.ON_GAME_LOADED, Phases.ON_GAME_LOADED);
    }
    
    // Getters for Agents extending this class
    public HumanFarmManager humanFarmManager() { return humanFarmManager; }
    public ConversionManager conversionManager() { return conversionManager; }
    // ... other getters
}
```

**Agents MAY:**
- Add new Manager fields + initialization
- Add new State fields
- Add new Phase registrations
- Add new delegate methods

**Agents MUST NOT:**
- Put logic directly in delegate methods (delegate to Managers)
- Add Engine API calls in Instance class
- Modify Manager initialization order

---

## 3. Manager Contracts — Single Responsibility

### 3.1 HumanFarmManager
```java
public final class HumanFarmManager {
    private final HumanFarmState state;
    private final GameApis apis;
    private final PropertiesStore props;
    
    // AGENTS MAY: Add new methods, modify update logic
    // AGENTS MUST NOT: Access Engine directly, modify State directly from outside
    
    public void update(double dt) {
        // 1. Scan for Human Farms (Building Scan)
        scanForHumanFarms();
        
        // 2. Process Farm Production
        processFarmProduction(dt);
        
        // 3. Check Gates → Unlock Undead Functions
        checkBuildingGates();
    }
    
    // Agents MAY override/extend
    protected void scanForHumanFarms() { /* ... */ }
    protected void processFarmProduction(double dt) { /* ... */ }
    protected void checkBuildingGates() { /* ... */ }
}
```

### 3.2 ConversionManager
```java
public final class ConversionManager {
    private final ConversionState state;
    private final GameApis apis;
    
    // Agents MAY: Modify conversion rates, add new conversion types
    // Agents MUST NOT: Direct Engine population manipulation
    
    public void update(double dt) {
        updateCooldowns(dt);
        checkConversionAvailability();
    }
    
    public ConversionResult attemptConversion(int amount) {
        // Validation → Event Trigger → State Update
        return ConversionResult.SUCCESS;
    }
}
```

### 3.3 GhostManager
```java
public final class GhostManager {
    private final GhostState state;
    private final GameApis apis;
    
    // Agents MAY: Add new Geist factors, modify thresholds
    // Agents MUST NOT: Direct UI manipulation
    
    public void update(double dt) {
        state.update(dt);
        checkThresholds();
        updateUI();
    }
}
```

### 3.4 GateManager (Building Gates)
```java
public final class GateManager {
    private final GameApis apis;
    private final Set<String> unlockedGates = new HashSet<>();
    
    // Agents MAY: Add new gates, modify gate conditions
    // Agents MUST NOT: Direct Room manipulation
    
    public void update() {
        scanBuildingGates();
    }
    
    public boolean isUnlocked(String gateKey) {
        return unlockedGates.contains(gateKey);
    }
}
```

---

## 4. State Classes — Persistence Contracts

### 4.1 Serialization Rules
```java
public interface PersistableState {
    // Version ALWAYS first
    void write(FilePutter putter);
    void read(FileGetter getter);
    
    // Version format: mark(version) → fields in FIXED ORDER
    // NEVER change order — add new fields at END with version bump
}
```

### 4.2 GhostState Example
```java
public final class GhostState implements PersistableState {
    private static final int CURRENT_VERSION = 1;
    
    // State Fields
    private double geistValue = 0.0;
    private double controlLevel = 0.0;
    private double fearLevel = 0.0;
    private double conditioningLevel = 0.0;
    private boolean rebellionActive = false;
    private boolean criticalActive = false;
    
    @Override
    public void write(FilePutter putter) {
        putter.mark(CURRENT_VERSION)
            .chars("GEIST_VALUE").chars(String.valueOf(geistValue))
            .chars("CONTROL_LEVEL").chars(String.valueOf(controlLevel))
            .chars("FEAR_LEVEL").chars(String.valueOf(fearLevel))
            .chars("CONDITIONING_LEVEL").chars(String.valueOf(conditioningLevel))
            .chars("REBELLION_ACTIVE").chars(String.valueOf(rebellionActive))
            .chars("CRITICAL_ACTIVE").chars(String.valueOf(criticalActive));
    }
    
    @Override
    public void read(FileGetter getter) {
        getter.check(); // Validates version
        geistValue = Double.parseDouble(getter.chars("GEIST_VALUE"));
        controlLevel = Double.parseDouble(getter.chars("CONTROL_LEVEL"));
        fearLevel = Double.parseDouble(getter.chars("FEAR_LEVEL"));
        conditioningLevel = Double.parseDouble(getter.chars("CONDITIONING_LEVEL"));
        rebellionActive = Boolean.parseBoolean(getter.chars("REBELLION_ACTIVE"));
        criticalActive = Boolean.parseBoolean(getter.chars("CRITICAL_ACTIVE"));
    }
}
```

---

## 5. Event Building — Runtime Events

### 5.1 UndeadEventBuilder
```java
public final class UndeadEventBuilder {
    private final GameEventsApi eventsApi;
    private final GameApis gameApis;
    
    public UndeadEventBuilder(GameEventsApi eventsApi, GameApis gameApis) {
        this.eventsApi = eventsApi;
        this.gameApis = gameApis;
    }
    
    // Agents MAY: Add new event creation methods
    // Agents MUST NOT: Modify existing event structures
    
    public void registerGhostEvents() {
        registerRebellionEvent();
        registerCriticalEvent();
    }
    
    private void registerRebellionEvent() {
        EventContainer container = EventContainer.builder()
            .context(Context.ON_SPAWN)
            .event(Event.builder("GEIST_REBELLION")
                .icon("32->REBELLION")
                .duration(Days.of(30))
                .occurrence(Occurrence.builder()
                    .race(Race.HUMAN, 1.0)
                    .requires(Requires.greater("GEIST_VALUE", 0.7))
                    .tags(Tags.allowNot(ChainOngoing.class))
                    .build())
                .choices(Choice.of(actions -> actions
                    .populationClassChange(PopulationClass.SLAVE, PopulationClass.REBEL, 0.5)
                    .boostPerm("REBELLION_ACTIVE", 1)
                    .credits(-5000)
                    .buildingDamage(BuildingDamage.randomControlBuilding(), 0.5)
                ))
                .build())
            .build();
        
        eventsApi.registerEvent(container);
    }
}
```

### 5.2 Event Naming Convention
| Event Type | Prefix | Example |
|------------|--------|---------|
| Conversion | `UNDEAD_` | `UNDEAD_CONVERSION` |
| Farm | `HUMAN_FARM_` | `HUMAN_FARM_ESTABLISHED` |
| Ghost | `GEIST_` | `GEIST_REBELLION` |
| Trade | `ORC_TRADE_` | `ORC_SLAVE_TRADE_OFFER` |
| Building Gate | `GATE_` | `GATE_HUMAN_PENS_BUILT` |

---

## 6. Constants — Single Source of Truth

```java
public final class UndeadConstants {
    
    // Boost Keys (Gate Flags)
    public static final String BOOST_HUMAN_PENS_BUILT = "UNDEAD_GATE_HUMAN_PENS_BUILT";
    public static final String BOOST_NECROPOLIS_UNLOCKED = "UNDEAD_GATE_NECROPOLIS_UNLOCKED";
    public static final String BOOST_HUMAN_PENS_LEVEL = "UNDEAD_GATE_HUMAN_PENS_LEVEL";
    
    // State Keys (Save/Load)
    public static final String STATE_GHOST = "SYXCRAFT_GHOST_STATE";
    public static final String STATE_FARM = "SYXCRAFT_FARM_STATE";
    public static final String STATE_CONVERSION = "SYXCRAFT_CONVERSION_STATE";
    
    // Resource/Race/Class Names (Exact Engine Strings)
    public static final String RACE_UNDEAD = "UNDEAD";
    public static final String RACE_HUMAN = "HUMAN";
    public static final String RACE_ORC = "ORC";
    public static final String CLASS_CITIZEN = "CITIZEN";
    public static final String CLASS_SLAVE = "SLAVE";
    public static final String CLASS_REBEL = "REBEL";
    public static final String RESOURCE_ESSENCE = "ESSENCE";
    public static final String RESOURCE_CAPTIVE_HUMAN = "CAPTIVE_HUMAN";
    
    // Event Names
    public static final String EVENT_UNDEAD_CONVERSION = "UNDEAD_CONVERSION";
    public static final String EVENT_HUMAN_FARM_ESTABLISH = "HUMAN_FARM_ESTABLISH";
    public static final String EVENT_GEIST_REBELLION = "GEIST_REBELLION";
    
    // Tech Names
    public static final String TECH_NECROMANCY_HUMAN_FARM = "NECROMANCY_HUMAN_FARM";
    public static final String TECH_ORC_SLAVERY = "ORC_SLAVERY";
    
    // Room Keys
    public static final String ROOM_HUMAN_PENS = "HUMAN_PENS";
    public static final String ROOM_NECROPOLIS = "NECROPOLIS";
    public static final String ROOM_SLAVE_PEN = "SLAVE_PEN";
    
    // Building Keys
    public static final String BUILDING_WORLD_HUMAN_FARM = "WORLD_HUMAN_FARM";
}
```

**Agents MAY:** Add new constants
**Agents MUST NOT:** Modify existing constants

---

## 7. Reflection Boundaries — Safe Wrapper

```java
public final class ReflectionUtil {
    
    // AGENTS MUST USE THIS — NEVER direct Class.forName/Field access
    
    public static Optional<Field> getDeclaredField(String fieldName, Class<?> clazz) {
        try {
            Field field = clazz.getDeclaredField(fieldName);
            field.setAccessible(true);
            return Optional.of(field);
        } catch (NoSuchFieldException e) {
            return Optional.empty();
        }
    }
    
    public static Optional<Object> getFieldValue(Object target, String fieldName) {
        return getDeclaredField(fieldName, target.getClass())
            .map(field -> {
                try { return field.get(target); }
                catch (IllegalAccessException e) { return null; }
            });
    }
    
    public static void setFieldValue(Object target, String fieldName, Object value) {
        getDeclaredField(fieldName, target.getClass()).ifPresent(field -> {
            try { field.set(target, value); }
            catch (IllegalAccessException e) { throw new RuntimeException(e); }
        });
    }
    
    public static Optional<Method> getDeclaredMethod(String methodName, Class<?> clazz, Class<?>... paramTypes) {
        try {
            Method method = clazz.getDeclaredMethod(methodName, paramTypes);
            method.setAccessible(true);
            return Optional.of(method);
        } catch (NoSuchMethodException e) { return Optional.empty(); }
    }
    
    public static Object invokeMethod(Object target, String methodName, Object... args) {
        Class<?>[] paramTypes = Arrays.stream(args).map(Object::getClass).toArray(Class[]::new);
        return getDeclaredMethod(target.getClass(), methodName, paramTypes)
            .map(m -> {
                try { return m.invoke(target, args); }
                catch (Exception e) { throw new RuntimeException(e); }
            })
            .orElseThrow(() -> new IllegalStateException("Method not found"));
    }
}
```

**Reflection Rules:**
- **ALLOWED:** Reading private fields for Gate Checks, Event Data Extraction
- **FORBIDDEN:** Modifying Engine State, Calling private Engine Methods
- **ALL Reflection** must go through `ReflectionUtil`

---

## 7. Testing Requirements

### 7.1 Unit Tests (Per Manager)
```java
@Test
public void testHumanFarmGateUnlock() {
    // Given: Fresh Instance
    // When: Human Pens Built Event fires
    // Then: Gate Unlocked, Necropolis Available
}

@Test
public void testConversionCooldown() {
    // Given: Conversion on Cooldown
    // When: Attempt Conversion
    // Then: Rejected with Cooldown Message
}
```

### 7.2 Integration Tests
```java
@Test
public void testFullConversionFlow() {
    // New Game → Research Tech → Build Farm → Capture Slaves → Convert
    // Verify: Undead Population increases, Human Slaves decrease
}
```

### 7.3 Save/Load Tests
```java
@Test
public void testSaveLoadPersistence() {
    // Play 100 Days → Save → Load → Verify All States Match
}
```

---

## 8. Agent Permissions Matrix

| Component | Extend | Override | New Methods | New Fields | Engine Access |
|-----------|--------|----------|-------------|------------|---------------|
| `UndeadScript` | ❌ | ❌ | ❌ | ❌ | ❌ |
| `UndeadInstance` | ✅ (subclass) | ✅ (delegates) | ✅ | ✅ | ❌ |
| `*Manager` | ✅ | ✅ (protected) | ✅ | ✅ (private) | ❌ |
| `*State` | ✅ | ❌ | ✅ | ✅ | ❌ |
| `UndeadEventBuilder` | ✅ | ✅ | ✅ | ✅ | ✅ (via API) |
| `ReflectionUtil` | ❌ | ❌ | ❌ | ❌ | ❌ (Wrapper only) |
| `UndeadConstants` | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 9. Build & Deploy

### 9.1 Maven Profile
```xml
<profile>
    <id>mod-sdk</id>
    <dependencies>
        <dependency>
            <groupId>io.github.4rg0n</groupId>
            <artifactId>sos-mod-sdk</artifactId>
            <version>${mod.sdk.version}</version>
        </dependency>
    </dependencies>
    <repositories>
        <repository>
            <id>github-4rg0n</id>
            <url>https://maven.pkg.github.com/4rg0n/Songs-of-Syx-Mod-SDK</url>
        </repository>
    </repositories>
</profile>
```

### 9.2 Build Commands
```bash
# Development Build
mvn clean package

# With Mod SDK (Full API Access)
mvn clean package -Pmod-sdk

# Install to Game
cp target/out/SyxCraft-Undead/V71 ~/.local/share/songsofsyx/mods/SyxCraft-Undead/
```

---

## 10. Verification Checklist

Before any Agent commits:
- [ ] All new constants in `UndeadConstants`
- [ ] All new State fields have `write/read` with version bump
- [ ] All new Events follow naming convention + registered in Builder
- [ ] All new Gates registered in `GateManager` + UI notified
- [ ] All Reflection via `ReflectionUtil` only
- [ ] Unit Tests pass: `mvn test`
- [ ] Integration Test: Full Game Flow works
- [ ] Save/Load Test: 100 Days → Save → Load → States Match
- [ ] No direct Engine API calls in Managers (via GameApis only)

---

*End of Java Agent Architecture Specification*