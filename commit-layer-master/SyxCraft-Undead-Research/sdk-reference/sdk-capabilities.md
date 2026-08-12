# SDK Reference — Argon Mod SDK V0 (4rg0n/songs-of-syx-mod-example)

> **Source:** Workshop Mod `3331182511` (Mod SDK V0) + GitHub `4rg0n/songs-of-syx-mod-example`
> **Version:** 0.1.5 (Game V71.44)
> **Status:** Analyse der kompilierten Klassen aus Workshop JAR

---

## Core Architecture

### AbstractModSdkScript — Base Class für Mod Scripts

```java
package com.github.argon.sos.mod.sdk;

public abstract class AbstractModSdkScript implements SCRIPT {
    protected final PhaseManager phaseManager;
    protected final StateManager stateManager;
    protected final GameApis gameApis;
    protected final PropertiesStore propertiesStore;
    
    // Constructor Injection
    public AbstractModSdkScript(PhaseManager pm, StateManager sm, GameApis apis, PropertiesStore ps) {
        this.phaseManager = pm;
        this.stateManager = sm;
        this.gameApis = apis;
        this.propertiesStore = ps;
        
        // Logging Setup
        initLogging();
        
        // SDK Phasen registrieren
        registerSdkPhases(phaseManager);
    }
    
    // Phasen-Registrierung (erweitert Vanilla Phasen)
    protected void registerSdkPhases(PhaseManager pm) {
        pm.register(Phase.INIT_BEFORE_GAME_CREATED, Phases.INIT_BEFORE_GAME_CREATED);
        pm.register(Phase.INIT_GAME_RESOURCES_LOADED, Phases.INIT_GAME_RESOURCES_LOADED);
        pm.register(Phase.INIT_MOD_CREATE_INSTANCE, Phases.INIT_MOD_CREATE_INSTANCE);
        pm.register(Phase.ON_GAME_SAVE_LOADED, Phases.ON_GAME_SAVE_LOADED);
        pm.register(Phase.ON_GAME_SAVE_RELOADED, Phases.ON_GAME_SAVE_RELOADED);
        pm.register(Phase.INIT_NEW_GAME_SESSION, Phases.INIT_NEW_GAME_SESSION);
        pm.register(Phase.INIT_GAME_UPDATING, Phases.INIT_GAME_UPDATING);
        pm.register(Phase.ON_GAME_UPDATE, Phases.ON_GAME_UPDATE);
        pm.register(Phase.INIT_GAME_UI_PRESENT, Phases.INIT_GAME_UI_PRESENT);
        pm.register(Phase.INIT_SETTLEMENT_UI_PRESENT, Phases.INIT_SETTLEMENT_UI_PRESENT);
        pm.register(Phase.ON_GAME_SAVED, Phases.ON_GAME_SAVED);
        pm.register(Phase.ON_BEFORE_BATTLE, Phases.ON_BEFORE_BATTLE);
        pm.register(Phase.ON_BATTLE, Phases.ON_BATTLE);
        pm.register(Phase.ON_AFTER_BATTLE, Phases.ON_AFTER_BATTLE);
        pm.register(Phase.ON_CRASH, Phases.ON_CRASH);
    }
}
```

---

## GameApis — Zentrale Registry

```java
public class GameApis {
    // Race Management
    public GameRaceApi race() { ... }
    
    // Room Definitions
    public GameRoomsApi rooms() { ... }
    
    // Event System (READ/WRITE!)
    public GameEventsApi events() { ... }
    
    // Factions, Diplomacy, Trade
    public GameFactionApi faction() { ... }
    
    // Save/Load Hooks
    public GameSaveApi save() { ... }
    
    // Stats, Boosts
    public GameStatsApi stats() { ... }
    
    // UI Notifications, Menus
    public GameUiApi ui() { ... }
    
    // Sounds, Weather, Animals
    public GameSoundsApi sounds() { ... }
    public GameWeatherApi weather() { ... }
    public GameAnimalsApi animals() { ... }
    
    // Localization
    public GameLangApi lang() { ... }
    
    // Mod Metadata
    public GameModApi mod() { ... }
    
    // Lifecycle Hooks (für Override in Mod Script)
    public void initBeforeGameCreated() { }
    public void initModCreateInstance() { }
    public void onGameUpdate(double seconds) { }
    public void onGameSaved(Path path, FilePutter putter) { }
    public void onGameLoaded(Path path, FileGetter getter) { }
    public void onGameSaveReloaded() { }
    public void initNewGameSession() { }
    public void onBeforeBattle() { }
    public void onBattle() { }
    public void onAfterBattle() { }
    public void onCrash(Throwable throwable) { }
}
```

---

## GameRaceApi — Race Management

```java
public class GameRaceApi {
    // Alle Races
    public List<Race> getAll() { ... }
    
    // Race by Name
    public Optional<Race> getRace(String name) { ... }
    
    // Race Likings (Runtime änderbar!)
    public double getLiking(Race a, Race b) { ... }
    public void setLiking(Race a, Race b, double value) { ... }
    
    // Race Preferences
    public RacePreferrence getPreferences(Race race) { ... }
    
    // Vanilla Referenzen
    public List<Race> vanillaRaces() { ... }
    public List<Pair<Race, Race>> vanillaLikings() { ... }
    
    // Citizen Counts pro Race
    public Map<Race, Integer> getCitizenRaces() { ... }
}
```

**Power Move:** `setLiking()` zur Runtime → Dynamic Diplomacy!

---

## GameEventsApi — Event System (VOLLZUGRIFF)

```java
public class GameEventsApi {
    // Event Resources lesen
    public List<EventResource> getEventResources() { ... }
    public Optional<EventResource> getEventResource(String name) { ... }
    
    // Event Trees parsen (Conditions, Choices, Aborters)
    public Map<String, TreeNode> readEventTrees() { ... }
    public Map<String, TreeNode> readEvents() { ... }
    
    // Event Container Builder (Runtime Event Creation!)
    public static class EventContainer {
        public Event getEvent() { ... }
        public TreeNode getNode() { ... }
        
        public static class Builder {
            public Builder context(Context ctx) { ... }
            public Builder event(Event event) { ... }
            public Builder node(Object node) { ... }
            public EventContainer build() { ... }
        }
    }
    
    // Event Locks (Cooldowns, Chain Control)
    public Map<String, EventLocker> getEventLockers() { ... }
    public Map<String, EventLocker> newEventLocks() { ... }
    
    // Context Types
    public enum Context {
        ON_SPAWN, SELECTION, CONDITION, DURATION, 
        CHOICE, ABORTER, ON_EXPIRE, ON_FULFILL
    }
}
```

**GameEventUtil:**
```java
public class GameEventUtil {
    public static Boolean isEnabled(EventResource resource) { ... }
}
```

---

## GameRoomsApi — Room Definitions

```java
public class GameRoomsApi {
    public List<RoomBlueprintImp> getRooms() { ... }
    public Optional<RoomBlueprintImp> getRoomByKey(String key) { ... }
    public Optional<RoomBlueprintImp> getRoomBySound(String soundKey, String roomKey) { ... }
}
```

**RoomBlueprintImp** enthält: Items, Upgrades, Consumption, Work, Sprites, Boosts.

---

## GameFactionApi — Diplomacy & Trade

```java
public class GameFactionApi {
    // Player Faction
    public Player getPlayer() { ... }
    
    // NPC Factions
    public Map<String, Faction> getFactions() { ... }
    public Map<String, FactionNPC> getFactionNPCs() { ... }
    
    // Reload
    public void reloadFactions() { ... }
}
```

**FactionNPC** hat: Name, Relations, Trade Stockpiles, Diplomacy State.

---

## GameSaveApi — Save/Load Hooks

```java
public class GameSaveApi {
    // Save/Load Callbacks
    public void onGameSaved(Path path, FilePutter putter) { ... }
    public void onGameLoaded(Path path, FileGetter getter) { ... }
    
    // Save File Access
    public Optional<SaveFile> getSaveFile() { ... }
    public List<SaveFile> list() { ... }
    public Optional<SaveFile> findByName(String name) { ... }
    
    // Battle Save Detection
    public boolean isBeforeBattleSave(Path path) { ... }
    public boolean isBattleSave(Path path) { ... }
    public Path getBattleSavePath() { ... }
    public Path getBeforeBattleSavePath() { ... }
    
    // Save Stamp (Version/Time)
    public String getSaveStamp(Path path) { ... }
}
```

---

## GameStatsApi / GameUiApi / GameSoundsApi

```java
// Stats & Boosts
public class GameStatsApi {
    public Map<String, Stat> getAllStats() { ... }
    public Optional<Stat> getStat(String name) { ... }
    public Map<String, Boostable> getBoostables() { ... }
}

// UI
public class GameUiApi {
    public void showNotification(String title, String text) { ... }
    public void addMenuButton(String id, String label, Runnable action) { ... }
    public void openCustomPanel(String id) { ... }
}

// Sounds
public class GameSoundsApi {
    public void playSound(String soundKey, float volume) { ... }
    public void playMusic(String musicKey) { ... }
}
```

---

## Phase & State Management

### Phases (Erweitert Vanilla)

```java
public enum Phase {
    INIT_BEFORE_GAME_CREATED,
    INIT_GAME_RESOURCES_LOADED,
    INIT_MOD_CREATE_INSTANCE,
    ON_GAME_SAVE_LOADED,
    ON_GAME_SAVE_RELOADED,
    INIT_NEW_GAME_SESSION,
    INIT_GAME_UPDATING,
    ON_GAME_UPDATE,
    INIT_GAME_UI_PRESENT,
    INIT_SETTLEMENT_UI_PRESENT,
    ON_GAME_SAVED,
    ON_BEFORE_BATTLE,
    ON_BATTLE,
    ON_AFTER_BATTLE,
    ON_CRASH
}
```

### StateManager

```java
public class StateManager {
    public State getState() { ... }
}

public class State {
    public boolean isInitGameUpdating() { ... }
    public void setInitGameUpdating(boolean b) { ... }
    public boolean isInitGameUiPresent() { ... }
    public void setInitGameUiPresent(boolean b) { ... }
    public boolean isInitSettlementUiPresent() { ... }
    public void setInitSettlementUiPresent(boolean b) { ... }
    public boolean isNewGameSession() { ... }
    public void setNewGameSession(boolean b) { ... }
    // ... Battle State, Save State, etc.
}
```

---

## Config System (JsonConfigStore)

```java
// Versioned Config mit Migration Support
public class JsonConfigStore {
    public <T> Optional<T> get(String key, Class<T> type) { ... }
    public void set(String key, Object value) { ... }
    public void registerConfig(String key, ConfigDefinition def) { ... }
}

// Config Definition
ConfigDefinition.builder()
    .version(1)
    .migrationHandler(new CustomMigrationHandler())
    .build();
```

---

## Properties Store (Simple Key-Value)

```java
public class PropertiesStore {
    public void set(String key, String value) { ... }
    public String get(String key) { ... }
    public int getInt(String key, int defaultValue) { ... }
    public double getDouble(String key, double defaultValue) { ... }
    public boolean getBoolean(String key, boolean defaultValue) { ... }
}
```

---

## ReflectionUtil (Engine Internals Access)

```java
public class ReflectionUtil {
    public static Optional<Field> getDeclaredField(String name, Class<?> clazz) { ... }
    public static Optional<Object> getDeclaredFieldValue(Field field, Object target) { ... }
    public static Object invokeMethod(String methodName, Object target, Object... args) { ... }
}
```

**Warnung:** Reflection bricht bei Game Updates! Nur für Notfälle.

---

## Logging

```java
public class Loggers {
    public static Logger getLogger(Class<?> clazz) { ... }
    public static void setLevels(Level level) { ... }
}

public enum Level { TRACE, DEBUG, INFO, WARN, ERROR }

// Env Variable: MOD.LOG_LEVEL
```

---

## Maven Dependency (aus songs-of-syx-mod-example)

```xml
<profile>
    <id>mod-sdk</id>
    <dependencies>
        <dependency>
            <groupId>io.github.4rg0n</groupId>
            <artifactId>sos-mod-sdk</artifactId>
            <version>0.1.5</version>
        </dependency>
    </dependencies>
</profile>
```

**Repository:** Wahrscheinlich GitHub Packages (io.github.4rg0n) — muss authentifiziert sein.

---

## Example Mod Script (aus songs-of-syx-mod-example)

### MainScript.java
```java
package your.mod;

public class MainScript implements SCRIPT {
    private final INFO info = new INFO("Example Mod", "Description");
    
    @Override public CharSequence name() { return info.name; }
    @Override public CharSequence desc() { return info.desc; }
    @Override public boolean isSelectable() { return true; }
    @Override public boolean forceInit() { return false; }
    @Override public void initBeforeGameCreated() { }
    @Override public void initBeforeGameInited() { }
    
    @Override public SCRIPT_INSTANCE createInstance() {
        return new InstanceScript();
    }
}
```

### InstanceScript.java
```java
package your.mod;

public class InstanceScript implements SCRIPT_INSTANCE {
    @Override public void update(double deltaSeconds) { }
    
    @Override public void save(FilePutter file) { }
    @Override public void load(FileGetter file) { }
    
    @Override public void onGameLoaded(Path path, FileGetter getter) { }
    @Override public void onGameSaved(Path path, FilePutter putter) { }
    @Override public void onGameSaveReloaded() { }
    @Override public void initNewGameSession() { }
    @Override public void onBeforeBattle() { }
    @Override public void onBattle() { }
    @Override public void onAfterBattle() { }
    @Override public void onCrash(Throwable t) { }
    @Override public boolean handleBrokenSavedState() { return false; }
}
```

---

## Capability Matrix für Undead Overhaul

| Feature | Vanilla Script API | Mod SDK V0 | Notes |
|---------|-------------------|------------|-------|
| Race CRUD | ❌ | ✅ `GameRaceApi` | `setLiking()` runtime! |
| Room Definitions | ❌ | ✅ `GameRoomsApi` | Read-only? |
| Event System | ❌ | ✅ `GameEventsApi` | **Full Read/Write** |
| Faction/Trade | ❌ | ✅ `GameFactionApi` | Stockpile, Diplomacy |
| Save/Load Custom Data | ✅ `FilePutter/Getter` | ✅ `GameSaveApi` | Beide gehen |
| UI Customization | ❌ | ✅ `GameUiApi` | Notifications, Menus |
| Sound/Weather | ❌ | ✅ `GameSoundsApi`/`WeatherApi` | Nice to have |
| Localization | ❌ | ✅ `GameLangApi` | Für deutsche Texte |
| Mod Metadata | ❌ | ✅ `GameModApi` | Version Check |
| Phase/State Management | ❌ | ✅ `PhaseManager`/`StateManager` | Cleaner Lifecycle |
| Config System | ❌ | ✅ `JsonConfigStore` | Versioned Configs |
| Reflection Access | ✅ (manual) | ✅ `ReflectionUtil` | Wrapper |

---

## Entscheidung: Vanilla Script vs. Mod SDK

| Kriterium | Vanilla Script (1B) | Mod SDK |
|-----------|---------------------|---------|
| **Setup** | Einfach (nur Game JAR) | Erfordert `sos-mod-sdk` Dependency |
| **Event Write** | ❌ Nur via Reflection | ✅ Native `EventContainer.Builder` |
| **Faction/Trade** | ❌ Reflection | ✅ Native API |
| **Race Liking** | ❌ Reflection | ✅ `setLiking()` |
| **Learning Curve** | Niedrig | Mittel |
| **Future-Proof** | Reflection bricht bei Updates | SDK wird gepflegt |
| **Dependency** | Keine | `io.github.4rg0n:sos-mod-sdk` |

**Empfehlung für Undead:** **Vanilla Script (1B) + gezielte Reflection** für Event/Faction Access.
- Mod SDK nur wenn `sos-mod-sdk` problemlos verfügbar ist.
- Vanilla Script reicht für: `ON_GAME_UPDATE` Logic, Save/Load, Conversion Events.
- Reflection nur für: `GameEventsApi` Read, `GameFactionApi` Trade.

---

## Nächste Schritte SDK

1. **Verfügbarkeit prüfen:** `gh api repos/4rg0n/Songs-of-Syx-Mod-SDK` oder Maven Central Search
2. **Falls verfügbar:** Mod SDK Profile in `pom.xml` aktivieren
3. **Falls nicht:** Vanilla Script + Reflection Helper Classes schreiben
4. **Documentation:** Eigene `UndeadReflectionUtil` für häufige Engine Access Patterns