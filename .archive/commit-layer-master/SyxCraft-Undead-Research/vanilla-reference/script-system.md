# Vanilla Script System — Songs of Syx V71

## Script-Architektur

### Entry Point: `script.SCRIPT` Interface

```java
package script;

public interface SCRIPT {
    CharSequence name();
    CharSequence desc();
    boolean initBeforeGameCreated();
    boolean isSelectable();
    boolean forceInit();
    SCRIPT_INSTANCE createInstance();
    
    interface SCRIPT_INSTANCE {
        void update(double deltaSeconds);
        void initBeforeGameCreated();
        void initBeforeGameInited();
        void initNewGameSession();
        void onGameLoaded(Path path, FileGetter getter);
        void onGameSaved(Path path, FilePutter putter);
        void onGameSaveReloaded();
        void onBeforeBattle();
        void onBattle();
        void onAfterBattle();
        void onCrash(Throwable t);
        boolean handleBrokenSavedState();
    }
}
```

### Script Engine: `script.ScriptEngine`

- Lädt alle Scripts aus `data/script/` + Mod JARs
- Verwaltet Script-Instanzen pro Savegame
- Ruft `update(dt)` jeden Tick auf
- Persistiert Script-State via `save()` / `load()`

---

## Script Phasen (aus `Phases.class`)

| Phase | Zeitpunkt | Typische Nutzung |
|-------|-----------|------------------|
| `INIT_BEFORE_GAME_CREATED` | Vor `new GAME()` | Static Setup, Config laden |
| `INIT_GAME_RESOURCES_LOADED` | Assets geladen | Race/Room/Resource Überprüfung |
| `INIT_MOD_CREATE_INSTANCE` | Script-Instanzen erstellt | Mod-spezifische Instanzen |
| `ON_GAME_SAVE_LOADED` | Savegame geladen | State restore |
| `ON_GAME_SAVE_RELOADED` | Nach Reload (F5) | UI/State refresh |
| `INIT_NEW_GAME_SESSION` | Neues Spiel gestartet | Starting Conditions setzen |
| `INIT_GAME_UPDATING` | Game Loop startet | Per-Tick Preparation |
| `ON_GAME_UPDATE(dt)` | **Jeder Tick** | **Hauptlogik hier!** |
| `INIT_GAME_UI_PRESENT` | Capital UI ready | UI Hooks, Buttons |
| `INIT_SETTLEMENT_UI_PRESENT` | Settlement UI ready | Settlement-spezifische UI |
| `ON_GAME_SAVED` | Save abgeschlossen | State persistieren |
| `ON_BEFORE_BATTLE` | Kampf startet | Pre-Battle Buffs |
| `ON_BATTLE` | Kampf läuft | Battle Logic |
| `ON_AFTER_BATTLE` | Kampf endet | Post-Battle Cleanup |
| `ON_CRASH` | Unhandled Exception | Crash-Reporting |

---

## Minimal Script Example (Vanilla Template)

```java
package your.mod;

import script.SCRIPT;
import script.SCRIPT_INSTANCE;
import util.info.INFO;

public class MainScript implements SCRIPT {
    private final INFO info = new INFO("Mod Name", "Description");
    
    @Override public CharSequence name() { return info.name; }
    @Override public CharSequence desc() { return info.desc; }
    @Override public boolean isSelectable() { return true; }
    @Override public boolean forceInit() { return false; }
    @Override public boolean initBeforeGameCreated() { return false; }
    
    @Override public void initBeforeGameCreated() {
        System.out.println("[MOD] initBeforeGameCreated");
    }
    
    @Override public void initBeforeGameInited() {
        System.out.println("[MOD] initBeforeGameInited");
    }
    
    @Override public SCRIPT_INSTANCE createInstance() {
        return new InstanceScript();
    }
    
    public static class InstanceScript implements SCRIPT_INSTANCE {
        @Override public void update(double dt) {
            // Hauptlogik jeden Tick
        }
        
        @Override public void onGameSaved(Path path, FilePutter putter) {
            // Save custom data
            putter.chars("MY_MOD_DATA").chars(jsonString);
        }
        
        @Override public void onGameLoaded(Path path, FileGetter getter) {
            // Load custom data
            String json = getter.chars("MY_MOD_DATA");
        }
        
        // ... andere Methoden mit Default-Impl
    }
}
```

---

## File Putter / Getter (Save/Load Serialization)

```java
// Schreiben (onGameSaved)
putter.mark(1).chars("KEY").chars("VALUE").chars("ANOTHER_KEY").chars(intValue);

// Lesen (onGameLoaded)
getter.check(); // Version check
String value = getter.chars("KEY");
int intValue = getter.chars("ANOTHER_KEY"); // Auto-parse
```

**Wichtig:** Position-basiert! Reihenfolge beim Schreiben = Reihenfolge beim Lesen.

---

## Mod SDK V0: AbstractModSdkScript (Erweitert Vanilla Script)

```java
package com.github.argon.sos.mod.sdk;

public abstract class AbstractModSdkScript implements SCRIPT {
    protected final PhaseManager phaseManager;
    protected final StateManager stateManager;
    protected final GameApis gameApis;
    protected final PropertiesStore propertiesStore;
    
    // Phasen registrieren
    phaseManager.register(Phase.INIT_GAME_RESOURCES_LOADED, Phases.INIT_GAME_RESOURCES_LOADED);
    phaseManager.register(Phase.ON_GAME_UPDATE, Phases.ON_GAME_UPDATE);
    
    // State Management
    stateManager.getState().isInitGameUpdating();
    stateManager.getState().setInitGameUpdating(true);
}
```

### GameApis — Vollzugriff auf Engine

```java
gameApis.race()     // GameRaceApi     — Races, Likings, Boosts
gameApis.rooms()    // GameRoomsApi    — Room Definitions
gameApis.events()   // GameEventsApi   — Event System (READ/WRITE!)
gameApis.faction()  // GameFactionApi  — Diplomacy, Trade, NPC Factions
gameApis.save()     // GameSaveApi     — Save/Load Hooks, SaveFile Access
gameApis.stats()    // GameStatsApi    — Stats, Boosts
gameApis.ui()       // GameUiApi       — Notifications, Menus
gameApis.sounds()   // GameSoundsApi   — Sound Playback
gameApis.weather()  // GameWeatherApi  — Weather Control
gameApis.animals()  // GameAnimalsApi  — Animal Spawning
gameApis.lang()     // GameLangApi     — Localization
gameApis.mod()      // GameModApi      — Mod Metadata, Other Mods
```

---

## Undead Script Design: `UndeadScript.java`

### Struktur

```java
package com.syxcraft.undead;

import script.SCRIPT;
import com.github.argon.sos.mod.sdk.AbstractModSdkScript;
import com.github.argon.sos.mod.sdk.phase.Phase;
import com.github.argon.sos.mod.sdk.phase.Phases;
import com.github.argon.sos.mod.sdk.game.api.GameApis;

public class UndeadScript extends AbstractModSdkScript {
    
    public UndeadScript(PhaseManager pm, StateManager sm, GameApis apis, PropertiesStore ps) {
        super(pm, sm, apis, ps);
        // Phasen registrieren
        pm.register(Phase.INIT_NEW_GAME_SESSION, Phases.INIT_NEW_GAME_SESSION);
        pm.register(Phase.ON_GAME_UPDATE, Phases.ON_GAME_UPDATE);
        pm.register(Phase.ON_GAME_SAVED, Phases.ON_GAME_SAVED);
        pm.register(Phase.ON_GAME_LOADED, Phases.ON_GAME_SAVE_LOADED);
    }
    
    @Override public CharSequence name() { return "SyxCraft Undead Overhaul"; }
    @Override public CharSequence desc() { return "WoW-inspired Undead faction with Human Farm mechanics"; }
    @Override public boolean isSelectable() { return true; }
    
    @Override public void initNewGameSession() {
        // Undead Starting Conditions
        if (gameApis.mod().getCurrentMod().isPresent()) {
            setupUndeadStart();
        }
    }
    
    @Override public void onGameUpdate(double dt) {
        // 1. Human Farm Check
        checkHumanFarmRequirement();
        
        // 2. Captive Human Growth Logic
        processHumanFarms(dt);
        
        // 3. Conversion Cooldowns
        updateConversionCooldowns(dt);
        
        // 4. Orc Trade Monitoring
        monitorOrcTrade();
    }
    
    @Override public void onGameSaved(Path path, FilePutter putter) {
        putter.mark(1)
            .chars("HUMAN_FARM_REGION_ID").chars(humanFarmRegionId != null ? humanFarmRegionId : "")
            .chars("CAPTIVE_HUMAN_COUNT").chars(String.valueOf(captiveHumanCount))
            .chars("CONVERSION_COOLDOWN").chars(String.valueOf(conversionCooldown));
    }
    
    @Override public void onGameLoaded(Path path, FileGetter getter) {
        getter.check();
        humanFarmRegionId = getter.chars("HUMAN_FARM_REGION_ID");
        captiveHumanCount = Integer.parseInt(getter.chars("CAPTIVE_HUMAN_COUNT"));
        conversionCooldown = Double.parseDouble(getter.chars("CONVERSION_COOLDOWN"));
    }
    
    // Helper Methods...
    private void setupUndeadStart() { ... }
    private void checkHumanFarmRequirement() { ... }
    private void processHumanFarms(double dt) { ... }
    private void updateConversionCooldowns(double dt) { ... }
    private void monitorOrcTrade() { ... }
}
```

---

## State Management (Mod SDK)

```java
// Phase State
stateManager.getState().isInitGameUpdating();
stateManager.getState().setInitGameUpdating(true);

// Custom State via PropertiesStore
propertiesStore.set("human_farm_level", 1);
propertiesStore.set("conversion_efficiency", 1.0);
int farmLevel = propertiesStore.getInt("human_farm_level", 1);
```

---

## Script Registration (Maven Build)

### `pom.xml` (Auszug)

```xml
<build>
    <plugins>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-shade-plugin</artifactId>
            <executions>
                <execution>
                    <phase>package</phase>
                    <goals><goal>shade</goal></goals>
                    <configuration>
                        <artifactSet>
                            <excludes><exclude>com.songsofsyx:*</exclude></excludes>
                        </artifactSet>
                    </configuration>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

### Output Structure (nach `mvn package`)

```
target/out/SyxCraft-Undead/
├── V71/
│   ├── data/
│   │   ├── init/
│   │   │   ├── race/UNDEAD.txt
│   │   │   ├── resource/supply/CAPTIVE_HUMAN.txt
│   │   │   ├── room/HUMAN_PENS.txt
│   │   │   ├── tech/NECROMANCY_HUMAN_FARM.txt
│   │   │   └── event/UNDEAD_CONVERSION.txt, HUMAN_FARM.txt, ...
│   │   └── script/
│   │       └── SyxCraft-Undead.jar  <-- COMPILED SCRIPT
│   └── _Info.txt
```

---

## Wichtige Engine-Klassen (für Reflection/Access)

| Klasse | Zweck | Mod SDK Access |
|--------|-------|----------------|
| `game.GAME` | Haupt-Game-Instanz | `gameApis` indirekt |
| `game.faction.FACTIONS` | Alle Fraktionen | `gameApis.faction().getFactions()` |
| `game.faction.player.Player` | Spieler-Fraktion | `gameApis.faction().getPlayer()` |
| `world.WORLD` | Weltkarte | `gameApis.faction().getPlayer().getWorld()` |
| `settlement.main.SETT` | Capital Settlement | `gameApis.faction().getPlayer().getSettlement()` |
| `init.race.RACES` | Race Registry | `gameApis.race().getAll()` |
| `init.race.Race` | Race Definition | `gameApis.race().getRace("UNDEAD")` |
| `game.events.EVENTS` | Event Engine | `gameApis.events().readEventResources()` |
| `game.events.EVENTS$EventResource` | Event Definition | `GameEventUtil` |
| `settlement.room.main.ROOMS` | Room Registry | `gameApis.rooms().getRooms()` |
| `init.tech.TECHS` | Tech Tree | Via Events/Boosts |
| `snake2d.util.file.FilePutter/Getter` | Save Serialization | Direct in Script |

---

## Offene Script-Fragen

| Frage | Antwort |
|-------|---------|
| Wie erkenne ich "Undead Player" in `ON_GAME_UPDATE`? | `gameApis.race().getRace("UNDEAD").filter(r -> gameApis.faction().getPlayer().getRace().equals(r))` |
| Wie prüfe ich "Tech erforscht"? | `gameApis.faction().getPlayer().hasTech("NECROMANCY_HUMAN_FARM")` (via Boost/Event Check) |
| Wie platziere ich `WORLD_HUMAN_FARM` auf Weltkarte? | `SELECTION.REGIONS` in Event → `SETTLEMENT_ADD: WORLD_HUMAN_FARM` |
| Wie lese ich `CAPTIVE_HUMAN` Stockpile? | `gameApis.faction().getPlayer().getStockpile().get("CAPTIVE_HUMAN")` |
| Kann ich `BOOST_PERM` für "Has Human Farm" setzen? | Ja — `gameApis.events().getEventResource("HUMAN_FARM_ESTABLISHED").ifPresent(...)` |

---

## Script-Dateien für Undead Concept (zu erstellen)

```
src/main/java/com/syxcraft/undead/
├── UndeadScript.java              // Main Script (extends AbstractModSdkScript)
├── state/
│   ├── UndeadState.java           // State Manager (Human Farm, Captives, Cooldowns)
│   └── HumanFarmState.java        // Farm-spezifischer State
├── logic/
│   ├── HumanFarmManager.java      // Farm Growth, Production, Upkeep
│   ├── ConversionManager.java     // Human→Undead Conversion Logic
│   ├── OrcTradeManager.java       // Orc→Undead Trade Monitoring
│   └── TechUnlockManager.java     // Tech-basierte Feature Flags
├── events/
│   └── UndeadEventBuilder.java    // Runtime Event Creation via GameEventsApi
└── util/
    └── UndeadUtils.java           // Helper: Race Checks, Resource Access
```