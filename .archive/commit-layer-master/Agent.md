# AGENT RULEBOOK — SyxCraft Project
> **Regelwerk für alle Agents, die in diesem Projekt arbeiten.** Basierend auf der etablierten Arbeitsweise. Verpflichtend.

---

## 1. GRUNDPRINZIPIEN

### 1.1 Keine halben Sachen
- **Alles oder nichts.** Ein Feature ist fertig wenn: Data Files + Script + Tests + Documentation + Build erfolgreich.
- **Keine TODOs im Code.** Wenn etwas unfertig ist: Issue erstellen, Branch löschen, neu beginnen.

### 1.2 Research First, Build Second
- **Kein Code ohne Research-Dokument.** Jedes Feature braucht: Vanilla-Reference, SDK-Capability-Check, Data-Examples.
- **Research liegt in `~/Schreibtisch/Next/SyxCraft-Undead-Research/`** — dort nachschauen bevor du codierst.

### 1.3 V71-First Mindset
- **Engine-Version V71.44 ist Law.** Alle Data Files müssen V71-kompatibel sein (Laws, Slavery, Population, Race Relations).
- **V70/V69 nur für Legacy-Support** — separat, nicht gemischt.

### 1.4 Determinism is Sacred
- **Kein `Math.random()`, keine System-Zeit, keine Threads.** Alles deterministisch über Game RNG.
- **Save/Load muss 1:1 reproduzierbar sein.** FilePutter/FileGetter Reihenfolge exakt einhalten.

---

## 2. WORKFLOW

### 2.1 Feature Development Cycle
```
1. RESEARCH    → Vanilla Reference + SDK Check + Data Examples dokumentieren
2. DESIGN      → Interdependency Matrix prüfen, Tech Dependencies validieren
3. DATA        → .txt Files in V71 Structure schreiben (_ignoreVanilla: true)
4. SCRIPT      → Java Implementation (Manager-Klassen + UndeadScript Entry)
5. BUILD       → mvn clean package -Pmod-sdk
6. TEST        → New Game → Undead wählen → 100 Days spielen → Save/Load
7. DOCUMENT    → CHANGELOG + README Update
```

### 2.2 Commit Discipline
- **Ein Feature = Ein Commit** (oder squash vor Merge)
- **Commit Message Format:**
  ```
  [FEATURE] Short description
  - Data: file1.txt, file2.txt
  - Script: ClassName.java
  - Test: Scenario X passed
  ```
- **Keine WIP-Commits auf main.** Feature-Branches nur.

### 2.3 Code Review (Self-Review vor Commit)
- [ ] Alle .txt Files haben `_ignoreVanilla: true` und Header
- [ ] Java Classes folgen Naming Convention (`*Manager`, `*EventBuilder`, `*State`)
- [ ] Save/Load Serialisierung: Reihenfolge identisch in Putter/Getter
- [ ] Keine Hardcoded Strings für Resource/Race/Tech Names (Constants nutzen)
- [ ] V71 Compatibility: Laws, Slavery, Population, Race Relations geprüft

---

## 3. DATEI-STRUKTUR & NAMING

### 3.1 Mod Structure (V71)
```
mods/SyxCraft-Undead/
├── V71/
│   ├── _info.txt
│   ├── data/init/
│   │   ├── race/UNDEAD.txt
│   │   ├── resource/supply/CAPTIVE_HUMAN.txt
│   │   ├── room/HUMAN_PENS.txt
│   │   ├── room/NECROPOLIS.txt
│   │   ├── tech/NECROMANCY_HUMAN_FARM.txt
│   │   ├── event/UNDEAD_CONVERSION.txt
│   │   ├── event/HUMAN_FARM_ESTABLISH.txt
│   │   └── world/building/WORLD_HUMAN_FARM.txt
│   └── script/
│       ├── syxcraft-undead.jar
│       └── _src/syxcraft-undead-sources.jar
```

### 3.2 Naming Conventions
| Typ | Pattern | Beispiel |
|-----|---------|----------|
| Race | `RACE_NAME.txt` | `UNDEAD.txt` |
| Resource | `RESOURCE_NAME.txt` | `CAPTIVE_HUMAN.txt` |
| Room | `ROOM_NAME.txt` | `HUMAN_PENS.txt` |
| Tech | `TECH_NAME.txt` | `NECROMANCY_HUMAN_FARM.txt` |
| Event | `EVENT_NAME.txt` | `UNDEAD_CONVERSION.txt` |
| World Building | `BUILDING_NAME.txt` | `WORLD_HUMAN_FARM.txt` |
| Java Class (Manager) | `*Manager.java` | `HumanFarmManager.java` |
| Java Class (Event) | `*EventBuilder.java` | `UndeadEventBuilder.java` |
| Java Class (State) | `*State.java` | `HumanFarmState.java` |
| Java Class (Entry) | `*Script.java` | `UndeadScript.java` |

### 3.3 Data File Header (Pflicht)
```txt
# LLM.entry
# STRUCTURE_EXPLANATION: One-line purpose
# ENGINE_DEFAULTS: Key defaults
# LAST_ENTRY: Entry N
# FILE_CONTEXT: V71/data/init/...
# VERSION: X.Y.Z
# FLAGS: DATA_NEW, VERIFIED
# FLAG_COUNT: N
```

---

## 4. JAVA IMPLEMENTATION RULES

### 4.1 Class Structure
```java
// Entry Point: implements SCRIPT
public final class UndeadScript implements SCRIPT {
    // Constants, no instance fields
    @Override public CharSequence name() { return "SyxCraft Undead Overhaul"; }
    @Override public SCRIPT_INSTANCE createInstance() { return new UndeadInstance(); }
}

// Instance: implements SCRIPT_INSTANCE
final class UndeadInstance implements SCRIPT_INSTANCE {
    private final HumanFarmManager farmManager;
    private final ConversionManager conversionManager;
    // State via State-Classes, NICHT instanz-Variablen
    
    @Override public void onGameUpdate(double dt) { ... }
    @Override public void onGameSaved(Path, FilePutter) { ... }
    @Override public void onGameLoaded(Path, FileGetter) { ... }
}
```

### 4.2 State Management
- **Keine Instanz-Variablen in Script-Instance.** Alles in `*State` Klassen.
- **Save/Load:** `FilePutter` / `FileGetter` — **Reihenfolge exakt gleich.**
- **Versioning:** Ersten `putter.mark(version)` schreiben, beim Load `getter.check()` prüfen.

### 4.3 Manager Pattern
- Ein Manager pro Subsystem (`HumanFarmManager`, `ConversionManager`, `OrcTradeManager`)
- **Keine Logik im Script-Entry.** Script delegiert nur an Manager.
- **Dependency Injection** über Constructor (PhaseManager, StateManager, GameApis, PropertiesStore)

### 4.4 Event Building (Runtime)
```java
// Via GameEventsApi
EventContainer container = EventContainer.builder()
    .context(EventContainer.Context.ON_SPAWN)
    .event(customEvent)
    .build();
gameApis.events().registerEvent(container);
```

### 4.4 Reflection (Last Resort)
- **Nur via `ReflectionUtil`** aus Mod SDK.
- **Niemals** direkt `Class.getDeclaredField()`.
- **Dokumentieren** warum Reflection nötig war.

---

## 5. DATA FILE STANDARDS

### 5.1 Resource Definition (Supply)
```txt
RESOURCE: NAME,
MORALE_ADD: -0.5,
HEALTH_EFFECT: 0.1,
CONSUMPTION_PER_USER_DAY: 0.0,
CONSUMPTION_PER_ITEM_DAY: 0.0,
AMOUNT_PER_PERSON: 1,
RACES: [UNDEAD],
ICON: 32->CATEGORY->INDEX,
VALUE: 100,
WEIGHT: 80.0,
SPRITE: SPRITE_NAME,
STACK_SIZE: 10,
CATEGORY_DEFAULT: 1,
EDIBLE: false,
PROPERTIES: { TRADEABLE: true, PERISHABLE: false, CONVERTIBLE: true },
```

### 5.2 Room with OUTPUT
```txt
OUTPUT: {
    RESOURCE: CAPTIVE_HUMAN,
    BASE_RATE: 0.02,
    BONUS_PER_LEVEL: 0.005,
    MAX_WORKERS: 20,
},
```

### 5.3 Tech with UNLOCKS_WORLD_BUILDING
```txt
TECHS: {
    TECH_NAME: {
        COSTS: { CIVIC_KNOWLEDGE: 200 },
        REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 },
        UNLOCKS_FACTION: [ ROOM_A, ROOM_B ],
        UNLOCKS_WORLD_BUILDING: [ WORLD_BUILDING_NAME ],
        UNLOCKS_EVENT: [ EVENT_A, EVENT_B ],
        UNLOCKS_LAW: [ LAW_NAME ],
        BOOST: { STAT>ADD: 0.1 },
    },
}
```

### 5.4 Event with SELECTION.REGIONS
```txt
EVENT_NAME: {
    SELECTION: {
        REGIONS: {
            MAX_AMOUNT: { AMOUNT: 1 },
            MIN_AMOUNT: { AMOUNT: 1 },
            FILTERS: [
                { GREATER: { PROP_TERRAIN_PLAINS: 0.3 } },
                { LESS: { IS_CAPITAL: 1 } }
            ]
        }
    },
}
```

---

## 6. V71 COMPLIANCE CHECKLIST

### 6.1 Laws & Government
- [ ] `SLAVE_PRICE` aus Race entfernt → Law-basiert
- [ ] `ORC_SLAVERY` Tech → Diplomatic Slave Trade Action
- [ ] `UNDEAD_CONVERSION` Event → Target: Population Class SLAVE (Race: HUMAN)

### 6.2 Population Growth
- [ ] `POPULATION.GROWTH` als Multiplier (1.0 = vanilla)
- [ ] `GROWTH` kann negativ sein
- [ ] Migration/Emigration als separate Flows

### 6.3 Race Relations
- [ ] `OTHER_RACES` Liking via Law/Event modifizierbar
- [ ] Faction-level Relations affect Trade/Raids

### 6.4 Slavery System
- [ ] `CAPTIVE_HUMAN` Resource → Population Class SLAVE Migration
- [ ] Slave Trade = Diplomatic Action (Embassy + Trade Agreement + Slavery Law Tier 2+)

---

## 7. TESTING PROTOCOL

### 7.1 Smoke Test (jedes Build)
```bash
mvn clean package -Pmod-sdk
cp mods/SyxCraft-Undead
cp target/out/SyxCraft-Undead/V71 ~/.local/share/songsofsyx/mods/
# Game starten → New Game → Undead wählen → 50 Days → Save → Load → Continue
```

### 7.2 Feature Tests (pro Feature)
| Feature | Test |
|---------|------|
| Human Farm | Tech erforschen → Event triggern → Region wählen → Building erscheint → Captive Humans generieren |
| Conversion | Captive Humans + Essence → Event triggern → Undead Citizens + Cooldown |
| Orc Trade | Orc Faction → Raid Event → Captives generieren → Trade Event → Undead erhält Captives |
| Save/Load | 100 Days spielen → Save → Load → State identisch (Farms, Captives, Cooldowns) |

### 7.3 Regression Test (vor Release)
- V70 Save laden → Migration funktioniert
- Multiplayer Desync Test (2 Clients, gleiche Actions)
- 500 Days Simulation → Performance < 16ms/Frame

---

## 8. DOCUMENTATION STANDARDS

### 8.1 CHANGELOG.md
```markdown
## [0.1.0] - 2026-07-14
### Added
- Undead Race (UNDEAD.txt)
- CAPTIVE_HUMAN Resource
- Human Pens Room + Necropolis Room
- Necromancy Human Farm Tech
- World Human Farm Worldmap Building
- Conversion Event + Human Farm Establish Event
### Fixed
- V71 Slavery System Integration
### Changed
- UNDEAD Race: ADULT_AT_DAY 20→60, FOOD: [] removed
```

### 8.2 README.md (Mod Root)
- Installation, Requirements, Compatibility
- Feature Overview
- Known Issues / Planned

---

## 9. GIT & BRANCH STRATEGY

### 9.1 Branches
- `main` — Protected, nur Releases
- `feature/*` — Ein Feature pro Branch
- `hotfix/*` — Nur für Critical Bugs auf main
- `experiment/*` — Research, wird nie gemerged

### 9.2 Merge Policy
- Squash & Merge
- Delete Branch nach Merge
- Main Branch Protection: Required Reviews = 1 (Self-Review zählt)

---

## 10. ESCALATION & BLOCKERS

### 10.1 Blocker Definition
- Engine Bug (V71 Regression)
- Mod SDK Missing/Unavailable
- Vanilla Data Structure Change (Breaking)
- Research Gap (Vanilla Mechanic nicht verstanden)

### 10.2 Escalation Path
1. **Research Gap** → Research dokumentieren → Decision dokumentieren → Weiter
2. **Engine Bug** → Workaround dokumentieren → Issue upstream → Workaround implementieren
3. **SDK Missing** → Vanilla Script Only Fallback → Feature Scope reduzieren
4. **Breaking Change** → Migration Path dokumentieren → Breaking Release (Major Version)

---

## 11. QUICK REFERENCE

### 11.1 Wichtige Pfade
| Zweck | Pfad |
|-------|------|
| Mod Root | `/home/vannon/Schreibtisch/Next/SyxCraft/mods/SyxCraft-Undead/` |
| V71 Data | `mods/SyxCraft-Undead/V71/data/init/` |
| Research | `~/Schreibtisch/Next/SyxCraft-Undead-Research/` |
| V71 Info | `/home/vannon/Schreibtisch/Next/SyxCraft/V71/_info.txt` |
| Interdependency | `/home/vannon/Schreibtisch/Next/Interdependency_Matrix.md` |
| Night Elf Spec | `/home/vannon/Schreibtisch/Next/Night_Elf_Mechanics_Spec.md` |

### 11.2 Wichtige Commands
```bash
# Build
cd /home/vannon/Schreibtisch/Next/SyxCraft/mods/SyxCraft-Undead
mvn clean package -Pmod-sdk

# Install to Game
cp -r target/out/SyxCraft-Undead/V71 ~/.local/share/songsofsyx/mods/SyxCraft-Undead/

# Validator
cd /home/vannon/Schreibtisch/Next/SyxCraft-Undead-Research && npm test
```

---

## 12. SIGNATURE

**Jeder Agent bestätigt durch Arbeit in diesem Projekt:**
> Ich habe dieses Rulebook gelesen, verstanden und wende es an.  
> Abweichungen dokumentiere ich mit Begründung im Commit.

---

*Version 1.0 — 2026-07-14 — Basierend auf SyxCraft Undead Overhaul Research & Implementation*