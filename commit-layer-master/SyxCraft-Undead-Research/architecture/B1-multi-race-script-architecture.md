# B1 — Multi-Race Script Architecture Analysis

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — Architecture Decision Documented

---

## 1. The Core Architecture Question

**KERNFRAGE:** Ein Script für alle vier Rassen oder vier separate Module die kommunizieren?

Diese Entscheidung bestimmt alles: Build-Prozess, Agent-Parallelarbeit, Testing, Workshop-Upload, Dependencies.

---

## 2. Option Analysis

### Option A — Monolithisch (Ein SyxCraftScript für alle Rassen)

```java
// Ein Script, alle Rassen
public class SyxCraftScript implements SCRIPT {
    public SCRIPT_INSTANCE createInstance() {
        return new SyxCraftInstance();
    }
}

public class SyxCraftInstance implements SCRIPT_INSTANCE {
    // Delegiert an Race-Module basierend auf Player Race
    private UndeadModule undeadModule;
    private OrcModule orcModule;
    private HumanModule humanModule;
    private NightElfModule nightElfModule;
    
    void onGameUpdate(double dt) {
        Race playerRace = getPlayerRace();
        switch(playerRace) {
            case UNDEAD -> undeadModule.update(dt);
            case ORC -> orcModule.update(dt);
            case HUMAN -> humanModule.update(dt);
            case NIGHT_ELF -> nightElfModule.update(dt);
        }
    }
}
```

**Wie erkennt das Script die Spieler-Rasse?**
```java
Race playerRace = apis.faction().getPlayer().getRace();
// Oder über GameRaceApi
Race playerRace = apis.race().getPlayerRace();
```

**Risiken:**
| Risiko | Bewertung |
|--------|-----------|
| Script-Größe | **HOCH** — Alle 4 Rassen in einem JAR |
| Manager-Abhängigkeiten | **HOCH** — Cross-Manager-Imports |
| Testing | **MITTEL** — Mocking komplex |
| Agent-Parallelarbeit | **KRITISCH** — Konflikte bei gleichzeitiger Arbeit |
| Load Order | **NIEDRIG** — Ein Script, keine Konflikte |
| Workshop Upload | **NIEDRIG** — Ein Mod, ein Upload |

---

### Option B — Modulare Scripts (Ein Script pro Rasse)

```java
// 4 separate Mods, 4 separate Scripts
mods/
├── SyxCraft-Undead/
│   └── script/UndeadScript.jar
├── SyxCraft-Orc/
│   └── script/OrcScript.jar
├── SyxCraft-Human/
│   └── script/HumanScript.jar
└── SyxCraft-NightElf/
    └── script/NightElfScript.jar
```

**Kann SoS mehrere Scripts gleichzeitig laden?**
- **JA** — SoS lädt alle installierten Mods und ihre Scripts
- Jeder Mod hat sein eigenes `SCRIPT` Implementation
- Scripts laufen isoliert, teilen sich aber Game State

**Wie kommunizieren zwei Scripts?**
```java
// NICHT direkt möglich — keine Script-zu-Script API
// Workarounds:
1. Shared State via GameFactionApi (Boosts, Stockpiles)
2. Events (GameEventsApi) — ein Script triggert Event, anderes reagiert
3. Diplomatie (GameFactionApi) — Diplomatic Actions
3. Race Relations (GameRaceApi.setLiking())
```

**Risiken:**
| Risiko | Bewertung |
|--------|-----------|
| Synchronisation | **KRITISCH** — Race Conditions bei Shared State |
| Load Order | **HOCH** — Wer lädt zuerst? |
| Testing Isolation | **NIEDRIG** — Perfekt isoliert |
| Agent-Parallelarbeit | **NIEDRIG** — Agenten arbeiten an verschiedenen Mods |
| Workshop | **MITTEL** — 4 Mods, 4 Uploads, Dependency Management |

---

### Option C — Hybrid (Core-Script + Race-Module als Klassen)

```java
// Ein Core-Script, Race-Module als interne Klassen
public class SyxCraftCoreScript implements SCRIPT {
    public SCRIPT_INSTANCE createInstance() {
        return new SyxCraftCoreInstance();
    }
}

public class SyxCraftCoreInstance implements SCRIPT_INSTANCE {
    // Core verwaltet Race-Module
    private final Map<Race, RaceModule> modules = new EnumMap<>(Race.class);
    
    public SyxCraftCoreInstance() {
        modules.put(Race.UNDEAD, new UndeadModule(this));
        modules.put(Race.ORC, new OrcModule(this));
        modules.put(Race.HUMAN, new HumanModule(this));
        modules.put(Race.NIGHT_ELF, new NightElfModule(this));
    }
    
    void onGameUpdate(double dt) {
        // Core Logik für alle Rassen
        coreManager.update(dt);
        
        // Delegate to player's race module
        Race playerRace = getPlayerRace();
        RaceModule module = modules.get(playerRace);
        if (module != null) {
            module.update(dt);
        }
        
        // Cross-race communication via Core Bus
        coreBus.process();
    }
}
```

**Race-Module kennen sich NICHT gegenseitig:**
```java
public abstract class RaceModule {
    protected final SyxCraftCoreInstance core;
    // Zugriff nur auf Core-Services, NICHT auf andere Module
    protected final CoreBus bus;
    protected final GameApis apis;
    
    public abstract void update(double dt);
    public abstract void onGameSaved(FilePutter putter);
    public abstract void onGameLoaded(FileGetter getter);
}

// UndeadModule
public class UndeadModule extends RaceModule {
    private GhostManager ghostManager;
    private ConversionManager conversionManager;
    // ...
    
    void update(double dt) {
        ghostManager.update(dt);
        conversionManager.update(dt);
        
        // Publiziert Events auf Core Bus
        if (ghostManager.shouldTriggerRebellion()) {
            bus.publish(new RebellionEvent(this, humanVillageRegion));
        }
    }
}

// OrcModule
public class OrcModule extends RaceModule {
    private RaidManager raidManager;
    private TradeManager tradeManager;
    
    void update(double dt) {
        raidManager.update(dt);
        
        // Reagiert auf Core Bus Events
        // NICHT direkt auf UndeadModule!
    }
    
    @Subscribe
    void onRebellionEvent(RebellionEvent e) {
        // Orcs können Rebellion ausnutzen
        raidManager.scheduleOpportunisticRaid(e.region());
    }
}
```

**Core Bus Pattern:**
```java
public class CoreBus {
    private final List<Consumer<CoreEvent>> subscribers = new CopyOnWriteArrayList<>();
    
    public void publish(CoreEvent event) {
        subscribers.forEach(s -> s.accept(event));
    }
    
    public void subscribe(Consumer<CoreEvent> handler) {
        subscribers.add(handler);
    }
}

public interface CoreEvent {}

public record RebellionEvent(RaceModule source, Region region) implements CoreEvent {}
public record SlaveTradeEvent(int amount, Faction from, Faction to) implements CoreEvent {}
public record GateUnlockedEvent(String gateKey) implements CoreEvent {}
```

---

## 3. Vergleichsmatrix

| Kriterium | Option A (Monolith) | Option B (Modular) | Option C (Hybrid) |
|-----------|---------------------|-------------------|-------------------|
| **Script-Größe** | ~5000 LOC | 4x ~1500 LOC | ~1000 Core + 4x ~1000 |
| **Build** | 1 JAR | 4 JARs | 1 JAR (Core) |
| **Workshop** | 1 Mod | 4 Mods | 1 Mod |
| **Agent Parallel** | ❌ Konflikte | ✅ Isoliert | ✅ Module isoliert |
| **Cross-Race Comm** | Direkter Zugriff | Events/State | Core Bus (typed) |
| **Testing** | Komplex (Mocking) | Einfach (isolated) | Mittel (Core mocken) |
| **Load Order** | Egal | Kritisch | Egal (ein Script) |
| **Shared State** | Einfach | Schwer (Race Cond.) | Core State Manager |
| **Hot Reload** | Ganzes Script | Einzelnes Modul | Core + Modul |
| **Dependency Hell** | Keine | Mod Dependencies | Keine |

---

## 4. Empfehlung: **Option C — Hybrid Core + Race Modules**

### Begründung

1. **Single Workshop Mod** — Ein Upload, eine Version, keine Dependency-Hölle
2. **Single Script Entry Point** — SoS lädt ein Script, keine Load-Order-Probleme
3. **Agent-Parallelarbeit** — Agenten arbeiten an separaten `RaceModule` Klassen
   - Agent 1: `UndeadModule.java` + `GhostManager.java`
   - Agent 2: `OrcModule.java` + `RaidManager.java`
   - Agent 3: `HumanModule.java` + `ImmigrationManager.java`
   - Agent 4: `NightElfModule.java` + `StealthManager.java`
   - **Keine Merge-Konflikte** — Jeder Agent in seinem Package
4. **Cross-Race Communication** — Typisierter Core Bus, keine Race Conditions
5. **Testing** — Core kann gemockt werden, Module isoliert testbar
6. **Extensibility** — Neue Rassen = neue Module, Core unchanged

### Package Structure für Hybrid
```
src/main/java/com/syxcraft/
├── core/
│   ├── SyxCraftCoreScript.java          # SCRIPT Implementation
│   ├── SyxCraftCoreInstance.java        # SCRIPT_INSTANCE Implementation
│   ├── CoreBus.java                     # Event Bus für Cross-Race
│   ├── CoreEvent.java                   # Base Event Interface
│   ├── CoreStateManager.java            # Shared State (Save/Load)
│   └── RaceModule.java                  # Abstract Base Class
├── undead/
│   ├── UndeadModule.java
│   ├── manager/
│   │   ├── GhostManager.java
│   │   ├── ConversionManager.java
│   │   ├── GateManager.java
│   │   └── HumanFarmManager.java
│   ├── state/
│   │   ├── GhostState.java
│   │   ├── ConversionState.java
│   │   └── HumanFarmState.java
│   └── event/
│       ├── RebellionEvent.java
│       └── ConversionEvent.java
├── orc/
│   ├── OrcModule.java
│   ├── manager/
│   │   ├── RaidManager.java
│   │   └── SlaveTradeManager.java
│   └── event/
│       └── SlaveRaidEvent.java
├── human/
│   ├── HumanModule.java
│   └── manager/
│       └── ImmigrationManager.java
├── nightelf/
│   ├── NightElfModule.java
│   └── manager/
│       └── StealthManager.java
└── constant/
    └── UndeadConstants.java             # Shared Constants
```

---

## 5. Implementation Contracts für Agents

### Core Contract (Agent 0 — Architecture)
```java
// Core verwaltet:
// - Race Module Registry
// - Core Bus (Event Distribution)
// - Shared State (Save/Load)
// - Phase Registration
// - Cross-Race Queries

// Core DARF:
// - Module registrieren
// - Events publizieren/subscriben
// - Shared State lesen/schreiben

// Core NICHT DARF:
// - Race-spezifische Logik enthalten
// - Direkt auf Module zugreifen (nur über Bus)
```

### Module Contract (Agent 1-4 — Race Implementation)
```java
// Jedes RaceModule:
// - Erbt von RaceModule (abstract)
// - Bekommt CoreBus + GameApis injected
// - MUSS update(dt), onSave, onLoad implementieren
// - DARF Core Bus Events publizieren/subcriben
// - DARF Core State Manager nutzen

// Module NICHT DARF:
// - Andere Module direkt instanziieren/zugreifen
// - Engine-Internals ohne SDK Wrapper nutzen
// - Static State halten (nur über State Manager)
```

---

## 6. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Lädt SoS ein Script pro Mod oder alle Scripts aller Mods? | **UNVERIFIED** | CRITICAL |
| Können mehrere Mods je ein Script haben? | **UNVERIFIED** | CRITICAL |
| Funktioniert `CoreBus` Pattern ohne Memory Leaks? | **UNVERIFIED** | HIGH |
| Save/Load von Core State + Module States atomar? | **UNVERIFIED** | HIGH |
| Funktioniert `abstract class RaceModule` mit Mod SDK? | **UNVERIFIED** | MEDIUM |

---

## 7. Architecture Decision Record

**DECISION:** **Option C — Hybrid Core Script + Race Modules**

**RATIONALE:**
- Single Mod, Single Workshop Upload, Single Script Entry Point
- Race Modules isoliert für Agent-Parallelarbeit
- Core Bus für typsichere Cross-Race Communication
- Core State Manager für einheitliches Save/Load
- Extensible für zukünftige Rassen

**CONSEQUENCES:**
- Core muss zuerst stabil sein (Blocker für alle Agenten)
- Core Bus Pattern muss getestet werden
- Module Contract muss strikt eingehalten werden
- Shared State über Core State Manager (nicht Static)

---

*End of B1 — Multi-Race Script Architecture Analysis*
*All findings from V71.44 analysis and Mod SDK review*