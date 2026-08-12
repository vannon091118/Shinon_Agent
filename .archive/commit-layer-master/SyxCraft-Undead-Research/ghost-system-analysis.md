# Ghost System (Custom Mood) — Technical Analysis

> **Engine:** V71.44 "Reign of Terror"
> **Mod SDK:** 0.1.5
> **Goal:** Implement "Geist" as custom mood system for Human Settlement under Undead control

---

## 1. Vanilla Loyalty System — Complete Analysis

### Data Structure (from Engine Analysis)

```java
// Settlement Entity — Loyalty Tracking
public class Settlement {
    // Loyalty per Race per Class
    private Map<Race, Map<PopulationClass, LoyaltyData>> loyaltyMap;
    
    // LoyaltyData
    public static class LoyaltyData {
        public double currentValue;      // 0.0 - 1.0
        public double targetValue;       // Computed target
        public double changeRate;        // Per day
        public List<LoyaltyModifier> modifiers;
    }
    
    // LoyaltyModifier
    public static class LoyaltyModifier {
        public String source;        // Source identifier
        public double value;         // Modifier value (-1.0 to +1.0)
        public boolean permanent;    // Permanent vs temporary
        public double durationDays;  // If temporary
    }
}
```

### Loyalty Update Cycle (Per Game Day)

```java
// In Settlement.updateDaily()
public void updateLoyalty(double dt) {
    for (Race race : getRacesPresent()) {
        for (PopulationClass clazz : PopulationClass.values()) {
            LoyaltyData data = getLoyalty(race, clazz);
            
            // Compute target value from modifiers
            double target = 0.5; // Base
            for (LoyaltyModifier mod : data.modifiers) {
                target += mod.value;
            }
            target = Math.clamp(target, 0.0, 1.0);
            data.targetValue = target;
            
            // Interpolate current toward target
            double changeRate = 0.05; // 5% per day base
            data.currentValue += (data.targetValue - data.currentValue) * changeRate * dt;
        }
    }
}
```

### Loyalty Sources (Vanilla)

| Source | Modifier | Duration | Target Class |
|--------|----------|----------|--------------|
| **Food Quality** | +0.1 per quality tier | Permanent | CITIZEN |
| **Housing Quality** | +0.05 per level | Permanent | CITIZEN |
| **Employment** | +0.1 if employed | While employed | CITIZEN |
| **Overcrowding** | -0.2 | While overcrowded | ALL |
| **Starvation** | -0.5/day | While starving | ALL |
| **Law Effects** | Law-specific | While Law active | Specified |
| **Racial Tension** | -0.1 per disliked race | Permanent | CITIZEN |
| **Events** | Event-specific | Event duration | Event-targeted |

### UI Representation

```java
// GameUiApi — Loyalty Display
public interface GameUiApi {
    // Shows loyalty bar in Population Panel
    void setRaceLoyaltyTooltip(Race race, PopulationClass clazz, String tooltip);
    
    // Adds custom loyalty modifier display
    void addLoyaltyModifierDisplay(Race race, String key, String label, double value, boolean positive);
}
```

---

## 2. Ghost System Requirements — Design Spec

### Concept Differences: Loyalty vs. Geist

| Aspect | Loyalty (Vanilla) | Geist (SyxCraft) |
|--------|-------------------|------------------|
| **Semantic** | Zufriedenheit/Zugehörigkeit | Kontrolle/Geistige Versklavung |
| **Range** | 0.0 - 1.0 (0 = Aufstand) | 0.0 - 1.0 (0 = Aufstand) |
| **Semantic Inversion** | Niedrig = Schlecht | **Niedrig = Gut** (für Undead) |
| **Drivers** | Zufriedenheit, Bedürfnisse | Kontrolle, Angst, Konditionierung |
| **Inversion Point** | 0.3 = Unzufrieden | **0.7 = Kontrollverlust** (für Undead) |
| **Events** | Aufstand, Auswanderung | Aufstand, Flucht, Sabotage |

### Geist Data Model (Custom)

```java
// Custom State per Settlement (Human Settlement under Undead Control)
public class GhostState {
    // Core Value: 0.0 = Vollständige Kontrolle, 1.0 = Vollständiger Aufstand
    private double geistValue = 0.0;
    
    // Components
    private double controlLevel = 0.0;       // 0.0 - 1.0 (Kontrollgebäude)
    private double fearLevel = 0.0;          // 0.0 - 1.0 (Angstgebäude)
    private double conditioningLevel = 0.0;  // 0.0 - 1.0 (Konditionierungsgebäude)
    
    // Thresholds
    private static final double REBELLION_THRESHOLD = 0.7;
    private static final double CRITICAL_THRESHOLD = 0.9;
    
    // Dynamic Modifiers (per Day)
    private double dailyControlDecay = 0.02;      // Kontrolle baut ab
    private double dailyFearDecay = 0.01;         // Angst baut langsamer ab
    private double dailyConditioningGain = 0.005; // Konditionierung wächst langsam
    
    // Events Triggered
    private boolean rebellionEventTriggered = false;
    private boolean criticalEventTriggered = false;
}
```

### Geist Calculation (Per Game Day)

```java
public void updateGhost(double dt) {
    // 1. Base Control from Buildings
    double controlFromBuildings = calculateControlFromBuildings();
    
    // 2. Base Fear from Events/Buildings
    double fearFromEvents = calculateFearFromEvents();
    double fearFromBuildings = calculateFearFromBuildings();
    
    // 3. Base Conditioning from Buildings
    double conditioningFromBuildings = calculateConditioningFromBuildings();
    
    // 4. Apply Daily Changes
    geistState.controlLevel = Math.clamp(
        geistState.controlLevel + (controlFromBuildings - geistState.dailyControlDecay) * dt, 
        0.0, 1.0);
    
    geistState.fearLevel = Math.clamp(
        geistState.fearLevel + (fearFromEvents + fearFromBuildings - geistState.dailyFearDecay) * dt, 
        0.0, 1.0);
    
    geistState.conditioningLevel = Math.clamp(
        geistState.conditioningLevel + (conditioningFromBuildings + geistState.dailyConditioningGain) * dt, 
        0.0, 1.0);
    
    // 5. Compute Geist Value (Inverted Logic for Undead)
    // High Control + High Fear + High Conditioning = Low Geist (Good for Undead)
    double controlFactor = 1.0 - geistState.controlLevel;      // 0 = Full Control
    double fearFactor = geistState.fearLevel;                  // 1 = Max Fear
    double conditioningFactor = 1.0 - geistState.conditioningLevel; // 0 = Fully Conditioned
    
    // Weighted Combination
    double newGeist = (controlFactor * 0.5) + (fearFactor * 0.3) + (conditioningFactor * 0.2);
    geistState.geistValue = Math.clamp(newGeist, 0.0, 1.0);
    
    // 6. Check Thresholds
    checkThresholds();
}
```

---

## 3. Building Contributions

### Control Buildings (Reduce Geist)

| Building | Control/Day | Max | Upgrades |
|----------|-------------|-----|----------|
| **Wachturm** | +0.02/day | 0.3 | +0.01 per Level |
| **Garnison** | +0.03/day | 0.5 | +0.015 per Level |
| **Kerker** | +0.04/day | 0.4 | +0.02 per Level |
| **Überwachungsturm** | +0.015/day | 0.25 | +0.01 per Level |

### Fear Buildings (Increase Fear → Lower Geist for Undead)

| Building | Fear/Day | Max | Upgrades |
|----------|----------|-----|----------|
| **Galgen** | +0.03/day | 0.5 | +0.015 per Level |
| **Folterkammer** | +0.05/day | 0.6 | +0.025 per Level |
| **Öffentliche Hinrichtung** | +0.08/event | 0.8 | N/A (Event) |

### Conditioning Buildings (Reduce Geist Long-term)

| Building | Conditioning/Day | Max | Upgrades |
|----------|------------------|-----|----------|
| **Indoktrinationshalle** | +0.005/day | 0.8 | +0.002/Level |
| **Propagandaturm** | +0.003/day | 0.5 | +0.001/Level |
| **Ritualstätte** | +0.01/event | 0.7 | Event-based |

---

## 3. Events & Thresholds

### Threshold Events

| Geist Value | Event | Effect |
|-------------|-------|--------|
| **≥ 0.5** | `GEIST_UNREST` | Warning: "Unruhe wächst" — UI Warning |
| **≥ 0.7** | `GEIST_REBELLION` | **Aufstand** — Bevölkerung wird SLAVE → REBEL Class |
| **≥ 0.9** | `GEIST_CRITICAL` | **Kritisch** — Massive Desertion, Gebäude Zerstörung |

### Rebellion Event
```txt
GEIST_REBELLION: {
    ICON: 32->REBELLION,
    DURATION: { DAYS: 30.0 },
    OCCURRENCE: {
        RACE: { HUMAN: 1.0 },
        REQUIRES: { GREATER: { GEIST_VALUE: 0.7 } }
    },
    TAGS: { ALLOW_NOT: [CHAIN_ONGOING] },
    CHOICES: [{
        ACTIONS: [
            { TYPE: POPULATION_CLASS_CHANGE, FROM: SLAVE, TO: REBEL, AMOUNT: { RELATIVE: 0.5 } },
            { TYPE: BOOST_PERM, PLAYER: { REBELLION_ACTIVE>SET: 1 } },
            { TYPE: RESOURCE_ADD, RESOURCE: CREDITS, AMOUNT: -5000 },
            { TYPE: BUILDING_DAMAGE, TARGET: RANDOM_CONTROL_BUILDING, DAMAGE: 0.5 }
        ]
    }]
}
```

### Critical Event
```txt
GEIST_CRITICAL: {
    ICON: 32->CATASTROPHE,
    DURATION: { DAYS: 60.0 },
    OCCURRENCE: {
        REQUIRES: { GREATER: { GEIST_VALUE: 0.9 } }
    },
    ON_SPAWN: {
        ACTIONS: [
            { TYPE: POPULATION_CLASS_CHANGE, FROM: SLAVE, TO: CITIZEN, RACE: HUMAN, AMOUNT: { RELATIVE: 0.8 } },
            { TYPE: BUILDING_DESTROY, TARGET: RANDOM_CONTROL_BUILDING },
            { TYPE: RESOURCE_ADD, RESOURCE: CREDITS, AMOUNT: -20000 },
            { TYPE: BOOST_PERM, PLAYER: { HUMAN_INDEPENDENCE>SET: 1 } }
        ]
    }
}
```

---

## 4. Mod SDK Implementation — Custom Mood System

### 4.1 State Persistence (GameSaveApi)

```java
public class GhostStateManager {
    private static final String GHOST_STATE_KEY = "SYXCRAFT_GHOST_STATE";
    
    public void save(Path path, FilePutter putter, GhostState state) {
        putter.mark(1)
            .chars("GEIST_VALUE").chars(String.valueOf(state.geistValue))
            .chars("CONTROL_LEVEL").chars(String.valueOf(state.controlLevel))
            .chars("FEAR_LEVEL").chars(String.valueOf(state.fearLevel))
            .chars("CONDITIONING_LEVEL").chars(String.valueOf(state.conditioningLevel))
            .chars("REBELLION_ACTIVE").chars(String.valueOf(state.rebellionActive))
            .chars("CRITICAL_ACTIVE").chars(String.valueOf(state.criticalActive));
    }
    
    public GhostState load(Path path, FileGetter getter) {
        getter.check();
        GhostState state = new GhostState();
        state.geistValue = Double.parseDouble(getter.chars("GEIST_VALUE"));
        state.controlLevel = Double.parseDouble(getter.chars("CONTROL_LEVEL"));
        state.fearLevel = Double.parseDouble(getter.chars("FEAR_LEVEL"));
        state.conditioningLevel = Double.parseDouble(getter.chars("CONDITIONING_LEVEL"));
        state.rebellionActive = Boolean.parseBoolean(getter.chars("REBELLION_ACTIVE"));
        state.criticalActive = Boolean.parseBoolean(getter.chars("CRITICAL_ACTIVE"));
        return state;
    }
}
```

### 4.2 UI Integration (GameUiApi)

```java
public class GhostUiManager {
    private final GameUiApi uiApi;
    
    public void updateGhostDisplay(double geistValue) {
        // Custom Tooltip in Population Panel
        String tooltip = buildGhostTooltip(geistValue);
        uiApi.setRaceLoyaltyTooltip(Race.HUMAN, PopulationClass.SLAVE, tooltip);
        
        // Custom Mood Indicator
        String geistLabel = getGeistLabel(geistValue);
        uiApi.setRaceLoyaltyModifierDisplay(
            Race.HUMAN, 
            "GEIST", 
            geistLabel, 
            geistValue, 
            geistValue < 0.5 // Good for Undead = Green
        );
    }
    
    private String buildGeistTooltip(double geist) {
        return String.format(
            "GEIST: %.0f%%\n" +
            "Kontrolle: %.0f%%\n" +
            "Angst: %.0f%%\n" +
            "Konditionierung: %.0f%%\n\n" +
            "%s",
            geist * 100,
            controlLevel * 100,
            fearLevel * 100,
            conditioningLevel * 100,
            getGeistDescription(geist)
        );
    }
}
```

### 4.3 Event Integration (GameEventsApi)

```java
public class GhostEventBuilder {
    private final GameEventsApi eventsApi;
    
    public void registerGhostEvents() {
        // Rebellion Event
        EventContainer rebellion = EventContainer.builder()
            .context(Context.ON_SPAWN)
            .event(createRebellionEvent())
            .build();
        eventsApi.registerEvent(rebellion);
        
        // Critical Event
        EventContainer critical = EventContainer.builder()
            .context(Context.ON_SPAWN)
            .event(createCriticalEvent())
            .build();
        eventsApi.registerEvent(critical);
    }
    
    private Event createRebellionEvent() {
        return Event.builder("GEIST_REBELLION")
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
            .build();
    }
}
```

### 4.4 UI Integration — Custom Mood Bar

```java
public class GhostUiRenderer {
    public void renderGhostMood(GameUiApi ui, GhostState state) {
        // Custom Mood Bar in Population Panel
        ui.addCustomPanel("SYXCRAFT_GHOST_PANEL", ctx -> {
            ctx.addLabel("GEIST DER MENSCHEN");
            ctx.addProgressBar(
                "GEIST", 
                state.geistValue, 
                getGeistColor(state.geistValue),
                getGeistLabel(state.geistValue)
            );
            
            ctx.addSeparator();
            ctx.addLabel("Kontrolle: " + (int)(state.controlLevel * 100) + "%");
            ctx.addLabel("Angst: " + (int)(state.fearLevel * 100) + "%");
            ctx.addLabel("Konditionierung: " + (int)(state.conditioningLevel * 100) + "%");
            
            ctx.addSeparator();
            ctx.addLabel(getGeistDescription(state.geistValue));
        });
    }
    
    private Color getGeistColor(double geist) {
        if (geist < 0.3) return Color.GREEN;      // Good for Undead
        if (geist < 0.5) return Color.YELLOW;
        if (geist < 0.7) return Color.ORANGE;
        return Color.RED; // Rebellion imminent
    }
}
```

---

## 5. Building Definitions — Ghost Contributions

### Control Buildings

```txt
# V71/data/init/room/WACHTTURM.txt
_ignoreVanilla: true,
ICON: 32->UNDEAD->WACHTTURM,
RESOURCES: [WOOD, STONE, METAL],
FLOOR: [STONE1, STONE2],
WORK: { SHIFT_OFFSET: 0.25, SOUND: BELL, USES_TOOL: false, FULFILLMENT: 0.5 },
BOOST: UNDEAD_CONTROL,
GHOST_CONTRIBUTION: {
    TYPE: CONTROL,
    BASE_RATE: 0.02,
    MAX: 0.3,
    PER_LEVEL: 0.01
},

# V71/data/init/room/GARNISON.txt
_ignoreVanilla: true,
ICON: 32->UNDEAD->GARNISON,
RESOURCES: [WOOD, STONE, METAL, FURNITURE, MACHINERY],
FLOOR: [STONE1, STONE2],
WORK: { SHIFT_OFFSET: 0.0, SOUND: MARCH, USES_TOOL: true, FULFILLMENT: 0.3 },
BOOST: UNDEAD_CONTROL,
GHOST_CONTRIBUTION: {
    TYPE: CONTROL,
    BASE_RATE: 0.03,
    MAX: 0.5,
    PER_LEVEL: 0.015
},
```

### Fear Buildings

```txt
# V71/data/init/room/GALGEN.txt
_ignoreVanilla: true,
ICON: 32->UNDEAD->GALGEN,
RESOURCES: [WOOD, STONE],
FLOOR: [DIRT, WOOD],
WORK: { SHIFT_OFFSET: 0.5, SOUND: BELL_TOLL, USES_TOOL: false, FULFILLMENT: 0.2 },
BOOST: UNDEAD_FEAR,
GHOST_CONTRIBUTION: {
    TYPE: FEAR,
    BASE_RATE: 0.03,
    MAX: 0.5,
    PER_LEVEL: 0.015
},
EVENTS: [
    { TRIGGER: LEVEL_UP, EVENT: PUBLIC_EXECUTION }
],

# V71/data/init/room/FOLTERKAMMER.txt
_ignoreVanilla: true,
ICON: 32->UNDEAD->FOLTERKAMMER,
RESOURCES: [STONE, METAL, LEATHER],
FLOOR: [STONE1, STONE2],
WORK: { SHIFT_OFFSET: 0.0, SOUND: SCREAM, USES_TOOL: true, FULFILLMENT: 0.1 },
BOOST: UNDEAD_FEAR,
GHOST_CONTRIBUTION: {
    TYPE: FEAR,
    BASE_RATE: 0.05,
    MAX: 0.6,
    PER_LEVEL: 0.025
},
```

### Conditioning Buildings

```txt
# V71/data/init/room/INDOKTRINATIONSHALLE.txt
_ignoreVanilla: true,
ICON: 32->UNDEAD->INDOKTRINATION,
RESOURCES: [WOOD, STONE, BOOK, ESSENCE],
FLOOR: [STONE1, STONE2],
WORK: { SHIFT_OFFSET: 0.25, SOUND: CHANT, USES_TOOL: false, FULFILLMENT: 0.8 },
BOOST: UNDEAD_CONDITIONING,
GHOST_CONTRIBUTION: {
    TYPE: CONDITIONING,
    BASE_RATE: 0.005,
    MAX: 0.8,
    PER_LEVEL: 0.002
},

# V71/data/init/room/PROPAGANDATURM.txt
_ignoreVanilla: true,
ICON: 32->UNDEAD->PROPAGANDA,
RESOURCES: [WOOD, STONE, PAPER],
FLOOR: [WOOD, STONE1],
WORK: { SHIFT_OFFSET: 0.0, SOUND: HORN, USES_TOOL: false, FULFILLMENT: 0.3 },
BOOST: UNDEAD_CONDITIONING,
GHOST_CONTRIBUTION: {
    TYPE: CONDITIONING,
    BASE_RATE: 0.003,
    MAX: 0.5,
    PER_LEVEL: 0.001
},
```

---

## 4. Save/Load Implementation

```java
public class GhostStateManager {
    private static final String SAVE_KEY = "SYXCRAFT_GHOST_STATE";
    
    public void onGameSaved(Path path, FilePutter putter, GhostState state) {
        putter.mark(1)
            .chars("GEIST_VALUE").chars(String.valueOf(state.geistValue))
            .chars("CONTROL_LEVEL").chars(String.valueOf(state.controlLevel))
            .chars("FEAR_LEVEL").chars(String.valueOf(state.fearLevel))
            .chars("CONDITIONING_LEVEL").chars(String.valueOf(state.conditioningLevel))
            .chars("REBELLION_ACTIVE").chars(String.valueOf(state.rebellionActive))
            .chars("CRITICAL_ACTIVE").chars(String.valueOf(state.criticalActive));
    }
    
    public GhostState load(Path path, FileGetter getter) {
        getter.check();
        GhostState state = new GhostState();
        state.geistValue = Double.parseDouble(getter.chars("GEIST_VALUE"));
        state.controlLevel = Double.parseDouble(getter.chars("CONTROL_LEVEL"));
        state.fearLevel = Double.parseDouble(getter.chars("FEAR_LEVEL"));
        state.conditioningLevel = Double.parseDouble(getter.chars("CONDITIONING_LEVEL"));
        state.rebellionActive = Boolean.parseBoolean(getter.chars("REBELLION_ACTIVE"));
        state.criticalActive = Boolean.parseBoolean(getter.chars("CRITICAL_ACTIVE"));
        return state;
    }
}
```

---

## 5. Open Risks & UNVERIFIED

| Risk | Verification Needed |
|------|---------------------|
| `GEIST_VALUE` as custom mood in UI — does `GameUiApi.setRaceLoyaltyModifierDisplay` support custom keys? | **UNVERIFIED** — Test `setRaceLoyaltyModifierDisplay(Race.HUMAN, "GEIST", ...)` |
| `GHOST_VALUE` as Boost — can `GameStatsApi.getBoostable("GEIST_VALUE")` be created dynamically? | **UNVERIFIED** — Test `GameStatsApi` dynamic boost creation |
| `POPULATION_CLASS_CHANGE` Event Action — does it support `FROM: SLAVE, TO: REBEL`? | **UNVERIFIED** — Check `EventActionType.POPULATION_CLASS_CHANGE` params |
| `GEIST_VALUE` as Event Occurrence Condition — `REQUIRES: { GREATER: { GEIST_VALUE: 0.7 } }` | **UNVERIFIED** — Event Engine may not support custom boost conditions |
| `GHOST_CONTRIBUTION` in Room Data — does `GameRoomsApi` parse custom `GHOST_CONTRIBUTION` block? | **UNVERIFIED** — Room Blueprint may ignore unknown fields |

---

## Verification Checklist (Must Pass Before Implementation)

- [ ] `GameUiApi.setRaceLoyaltyModifierDisplay("GEIST", ...)` works
- [ ] `GameStatsApi` can create/query custom Boost "GEIST_VALUE"
- [ ] Event Condition `GREATER: { GEIST_VALUE: 0.7 }` evaluates
- [ ] `POPULATION_CLASS_CHANGE` Action supports `FROM: SLAVE, TO: REBEL`
- [ ] Room `GHOST_CONTRIBUTION` block parsed without error
- [ ] Custom Save Key "SYXCRAFT_GHOST_STATE" persists across Save/Load

---

*End of Ghost System Analysis*