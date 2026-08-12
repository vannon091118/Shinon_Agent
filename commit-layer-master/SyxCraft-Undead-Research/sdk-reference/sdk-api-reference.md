# Argon Mod SDK V0 — API Reference

> **Source:** Workshop Mod `3331182511` (Mod SDK V0) — kompilierte Klassen analysiert via `strings`
> **Package:** `com.github.argon.sos.mod.sdk`
> **Game Version:** V71.44

---

## Core Classes

### `AbstractModSdkScript` — Base für alle Mod Scripts
```java
public abstract class AbstractModSdkScript implements SCRIPT {
    protected final PhaseManager phaseManager;
    protected final StateManager stateManager;
    protected final GameApis gameApis;
    protected final PropertiesStore propertiesStore;
    
    // Constructor Injection
    public AbstractModSdkScript(PhaseManager pm, StateManager sm, GameApis apis, PropertiesStore ps)
}
```

### `GameApis` — Zentrale Registry (Singleton pro Game)
```java
public class GameApis {
    public GameRaceApi race() { ... }
    public GameRoomsApi rooms() { ... }
    public GameEventsApi events() { ... }      // VOLLER Event Zugriff!
    public GameFactionApi faction() { ... }
    public GameSaveApi save() { ... }
    public GameStatsApi stats() { ... }
    public GameUiApi ui() { ... }
    public GameSoundsApi sounds() { ... }
    public GameWeatherApi weather() { ... }
    public GameAnimalsApi animals() { ... }
    public GameLangApi lang() { ... }
    public GameModApi mod() { ... }
    
    // Lifecycle Hooks (override in Script)
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
    
    // Vanilla Referenzen
    public List<Race> vanillaRaces() { ... }
    public List<Pair<Race, Race>> vanillaLikings() { ... }
}
```

---

## GameEventsApi — Event System (READ/WRITE!)

```java
public class GameEventsApi {
    // Alle Event Resources lesen
    public List<EventResource> readEventResources() { ... }
    
    // Einzelnes Event
    public Optional<EventResource> getEventResource(String name) { ... }
    
    // Event Trees parsen (Conditions, Choices, etc.)
    public void readEventTrees() { ... }
    public void readEvents() { ... }
    
    // Event Container Builder (Runtime Event Creation!)
    public EventContainer.Builder builder() { ... }
    
    // Event Locks (Cooldowns)
    public Map<String, EventLocker> getEventLockers() { ... }
    
    // Utility
    public static boolean isEnabled(EventResource resource) { ... }
}
```

### EventContainer Builder
```java
public class EventContainer.Builder {
    public Builder context(Context ctx) { ... }      // ON_SPAWN, SELECTION, CONDITION, etc.
    public Builder event(Event event) { ... }
    public EventContainer build() { ... }
}
```

### EventContainer.Context Enum
- `ON_SPAWN`
- `SELECTION` 
- `CONDITION`
- `DURATION`
- `CHOICE`
- `ABORTER`
- `ON_EXPIRE`

---

## GameFactionApi — Diplomacy & Trade

```java
public class GameFactionApi {
    // Player Faction
    public Player getPlayer() { ... }
    
    // Alle NPC Factions
    public Map<String, Faction> getFactions() { ... }
    public Map<String, FactionNPC> getFactionNPCs() { ... }
    
    // Reload
    public void reloadFactions() { ... }
}
```

### FactionNPC (NPC Faction Data)
- Name, Relations, Trade Stockpiles, Diplomacy State

---

## GameSaveApi — Save/Load Hooks

```java
public class GameSaveApi {
    // Save Callbacks
    public void onGameSaved(Path path, FilePutter putter) { }
    public void onGameLoaded(Path path, FileGetter getter) { }
    
    // Save File Access
    public Optional<SaveFile> findByName(String name) { ... }
    public Optional<SaveFile> findByPathContains(Path path) { ... }
    public List<SaveFile> list() { ... }
    
    // Battle Save Detection
    public boolean isBattleSave(Path path) { ... }
    public void setCurrentBattleSave(Path path) { ... }
}
```

### FilePutter / FileGetter (Serialization)
```java
// Schreiben (Position-basiert!)
putter.mark(version).chars("KEY").chars("VALUE").chars(intValue);

// Lesen (Gleiche Reihenfolge!)
getter.check();  // Version check
String value = getter.chars("KEY");
int intValue = getter.chars("KEY");  // Auto-parse
```

---

## GameRoomsApi — Room Definitions

```java
public class GameRoomsApi {
    public List<RoomBlueprintImp> getRooms() { ... }
    public Optional<RoomBlueprintImp> getRoomByKey(String key) { ... }
    public Optional<RoomBlueprintImp> getRoomBySound(String soundKey) { ... }
}
```

---

## GameUiApi — UI Integration

```java
public class GameUiApi {
    // Notifications
    public void showNotification(String title, String message, NotificationType type, double duration) { ... }
    
    // Resource Tooltips
    public void setResourceTooltip(String resourceName, String tooltip) { ... }
    
    // Custom Menus/Panels (Advanced)
    public void openCustomPanel(String panelId) { ... }
}
```

---

## GameModApi — Mod Metadata

```java
public class GameModApi {
    public List<ModInfo> getCurrentMods() { ... }
    public Optional<ModInfo> getModByName(String name) { ... }
}
```

---

## Phase Manager & State Manager

### PhaseManager
```java
public class PhaseManager {
    public void register(Phase phase, Phases sdkPhase) { ... }
}
```

### Phases (SDK-extended)
```java
public enum Phases {
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
}
```

---

## PropertiesStore — Mod Config

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

## Utility Classes

### ReflectionUtil
```java
public class ReflectionUtil {
    public static Optional<Field> getDeclaredField(String name, Class<?> clazz) { ... }
    public static Optional<Object> getDeclaredFieldValue(Field field, Object target) { ... }
    public static Object invokeMethod(String methodName, Object target, Object... args) { ... }
}
```

### GameEventUtil
```java
public class GameEventUtil {
    public static Boolean isEnabled(EventResource resource) { ... }
    public static Optional<Object> getDeclaredFieldValue(Field field, Object target) { ... }
}
```

### Lists (Conversion Helper)
```java
public class Lists {
    public static <T> List<T> fromGameLIST(LIST<?> gameList) { ... }
}
```

---

## JsonConfigStore — Versioned Config

```java
public class JsonConfigStore {
    public static class ConfigDefinition { ... }
    public static class ConfigObject { ... }
    // Versioned config with migration support
}
```

---

## Dependency: `sos-mod-sdk` Maven

```xml
<dependency>
    <groupId>io.github.4rg0n</groupId>
    <artifactId>sos-mod-sdk</artifactId>
    <version>0.1.5</version>
</dependency>
```

**Repo:** `https://maven.pkg.github.com/4rg0n/Songs-of-Syx-Mod-SDK` (GitHub Packages — needs auth)

---

## Verfügbarkeit Check

| API | In Mod SDK V0? | In Vanilla Script? |
|-----|----------------|-------------------|
| `GameEventsApi` (Read/Write Events) | ✅ | ❌ |
| `GameRaceApi` (setLiking) | ✅ | ❌ |
| `GameFactionApi` (Trade/Stockpile) | ✅ | ❌ |
| `GameSaveApi` (Custom State) | ✅ | ✅ (via Script) |
| `GameUiApi` (Notifications) | ✅ | ⚠️ Limited |
| `GameRoomsApi` (Read Rooms) | ✅ | ❌ |
| `GameStatsApi` (Boosts) | ✅ | ❌ |
| `ReflectionUtil` (Private Fields) | ✅ | ❌ |
| `PhaseManager/StateManager` | ✅ | ❌ |

---

## Empfehlung für Undead Mod

### Mit Mod SDK (Profile `mod-sdk` aktiv)
- **Vorteile:** Volle Event Control, Race Likings, Faction Trade, UI Notifications
- **Nachteil:** Extra Dependency, Build Complexity

### Ohne Mod SDK (Vanilla Script Only)
- **Vorteile:** Einfacher Build, weniger Dependencies
- **Nachteil:** Kein `setLiking`, kein `GameEventsApi` Write, kein `GameFactionApi`

**Decision:** **Mod SDK nutzen** — Die Kern-Features (Conversion Events, Orc Trade, Race Relations) brauchen SDK APIs.

---

## Build Setup (pom.xml)

```xml
<profiles>
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
</profiles>
```

```bash
# Build mit SDK
mvn clean package -Pmod-sdk

# Build ohne SDK (Vanilla Script Only)
mvn clean package
```