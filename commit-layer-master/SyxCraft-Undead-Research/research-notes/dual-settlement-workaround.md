# Dual Settlement Workaround — Technical Analysis

> **Problem:** Songs of Syx Engine unterstützt **keine** mehreren Capital-Maps (Settlements) pro Player.
> **Lösung:** Worldmap Building `WORLD_HUMAN_FARM` als Proxy für "2. Settlement".

---

## Engine-Limitationen

### Was NICHT geht (Vanilla)
- **Eine Capital-Map pro Player** — `settlement.main.SETT` ist Singleton pro Player.
- **Keine API** für `createSecondSettlement()` oder ähnlich.
- **Savegame** speichert genau eine Settlement-Struktur.
- **UI** (Tabs, Menüs) hardcoded für eine Settlement.

### Was GEHT (Workarounds)

| Workaround | Beschreibung | Pros | Cons |
|------------|--------------|------|------|
| **A: Worldmap Building** | `WORLD_HUMAN_FARM` in Region → generiert Ressourcen passiv | Einfach, nutzt bestehende Systeme (Region Buildings, Trade) | Keine eigene Map, kein Micro-Management, keine Rooms |
| **B: Virtual Settlement (Script)** | Script tracked "Farm State" separat → Simuliert 2. Economy | Vollständige Logik kontrollierbar, Save/Load via `FilePutter` | UI nur via Custom Script (`GameUiApi`), kein natives Settlement-Feeling |
| **C: Region als "Mini-Settlement"** | Region Upgrades = "Buildings", Population = Captives | Nutzt Worldmap System | Limitiert auf Worldmap-Mechanik |
| **D: Mod SDK Deep Hack** | `GameSaveApi` + Reflection → 2. `SETT` Instanz im Savegame | Echte 2. Map möglich | **Sehr riskant**, Engine-Crashes wahrscheinlich, Multiplayer inkompatibel |

---

## Empfohlene Lösung: **Hybrid A + B**

### Data Layer (Worldmap)
```
WORLD_HUMAN_FARM (Region Building)
├── Level 1-5
├── Production: CAPTIVE_HUMAN/Tag
├── Maintenance: Credits + Essence
├── Upgrades: Cost + Production Multiplier
└── Events: LEVEL_UP, LOW_RESOURCES, EXPANDED
```

### Logic Layer (Script)
```java
// UndeadScript.java - ON_GAME_UPDATE
private void processHumanFarms(double dt) {
    // 1. Finde alle Player-Regions mit WORLD_HUMAN_FARM
    List<Region> farms = gameApis.faction().getPlayer().getRegions().stream()
        .filter(r -> r.hasBuilding("WORLD_HUMAN_FARM"))
        .toList();
    
    // 2. Für jede Farm: Production berechnen
    for (Region farm : farms) {
        int level = farm.getBuildingLevel("WORLD_HUMAN_FARM");
        double dailyProduction = FARM_BASE[level] * getEfficiencyBoost();
        
        // 3. Captive Humans zum Player Stockpile addieren
        addCaptiveHumans(dailyProduction * dt);
        
        // 4. Farm State updaten (für UI/Events)
        farmState.setProduction(farm.getId(), dailyProduction);
    }
    
    // 5. Conversion Logic (NECROPOLIS Room)
    processConversions(dt);
}

// Save/Load Custom State
@Override
public void onGameSaved(Path path, FilePutter putter) {
    putter.mark(1)
        .chars("HUMAN_FARM_COUNT").chars(String.valueOf(farms.size()))
        .chars("TOTAL_CAPTIVES").chars(String.valueOf(totalCaptives))
        .chars("CONVERSION_COOLDOWN").chars(String.valueOf(conversionCooldown));
        
    for (FarmState farm : farms) {
        putter.chars("FARM_" + farm.id + "_LEVEL").chars(String.valueOf(farm.level));
        putter.chars("FARM_" + farm.id + "_REGION").chars(farm.regionId);
    }
}

@Override
public void onGameLoaded(Path path, FileGetter getter) {
    getter.check();
    int farmCount = Integer.parseInt(getter.chars("HUMAN_FARM_COUNT"));
    totalCaptives = Integer.parseInt(getter.chars("TOTAL_CAPTIVES"));
    conversionCooldown = Double.parseDouble(getter.chars("CONVERSION_COOLDOWN"));
    
    farms.clear();
    for (int i = 0; i < farmCount; i++) {
        int level = Integer.parseInt(getter.chars("FARM_" + i + "_LEVEL"));
        String regionId = getter.chars("FARM_" + i + "_REGION");
        farms.add(new FarmState(i, level, regionId));
    }
}
```

### UI Layer (GameUiApi)

```java
// Custom Notification für Farm Events
gameApis.ui().showNotification(
    "Human Farm Established",
    "Your necromancers have established a human farm in " + regionName,
    NotificationType.SUCCESS,
    10.0
);

// Custom Tooltip für Captive Human Resource
gameApis.ui().setResourceTooltip("CAPTIVE_HUMAN", 
    "Captive Humans\n" +
    "Used for: Necropolis Conversion\n" +
    "Produced by: Human Farms (Worldmap), Human Pens (Capital)\n" +
    "Current Stock: " + captiveCount + " / " + captiveCapacity
);
```

---

## Event-Integration

### `FOUND_HUMAN_FARM` Event Flow

```
1. Tech NECROMANCY_HUMAN_FARM erforscht
   ↓
2. Event FOUND_HUMAN_FARM spawnt (MAX_SPAWNS: 1)
   ↓
3. SELECTION.REGIONS → Spieler wählt Region
   ↓
4. CHOICE: "Establish Farm"
   ACTIONS:
   - SETTLEMENT_ADD: WORLD_HUMAN_FARM (in gewählter Region)
   - BOOST_PERM: HAS_HUMAN_FARM>SET: 1 (Player Flag)
   - RESOURCE_ADD: CAPTIVE_HUMAN: 10 (Starter Stock)
   ↓
5. Script: ON_GAME_UPDATE detected Farm → startet Production Loop
```

### Conversion Cooldown System

```java
// Boost als Cooldown Flag
BOOST_PERM: { UNDEAD_CONVERSION_COOLDOWN>SET: 1 }  // 30 Tage
// Nach 30 Tagen: Event CONVERSION_COOLDOWN_END → BOOST_PERM: SET: 0
```

---

## Mod SDK Capabilities für Dual Settlement

| API | Methode | Nutzt für Farm |
|-----|---------|----------------|
| `GameFactionApi` | `getPlayer().getRegions()` | Farm Regions finden |
| `GameFactionApi` | `getPlayer().getStockpile()` | Captive Human Count |
| `GameEventsApi` | `getEventResource()`, `readEventTrees()` | Custom Events lesen/schreiben |
| `GameSaveApi` | `onGameSaved/Loaded` | Farm State persistieren |
| `GameUiApi` | `showNotification()`, `setResourceTooltip()` | Farm UI |
| `GameRaceApi` | `setLiking(UNDEAD, HUMAN, -1.0)` | Race Relations |
| `PropertiesStore` | `set/get("farm_level", 1)` | Config persistieren |
| `PhaseManager` | `register(Phase.ON_GAME_UPDATE, ...)` | Main Loop Hook |

---

## Risiken & Mitigations

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Savegame Corruption durch Custom State | Mittel | Hoch | `handleBrokenSavedState() = true`, Version-Check in State |
| Multiplayer Desync | Hoch (wenn MP) | Hoch | **Kein MP Support** initial, nur Singleplayer |
| Performance: `ON_GAME_UPDATE` prüft alle Regions jeden Tick | Niedrig | Mittel | Cache Farm Regions, nur dirty Farms updaten |
| UI Confusion: "Wo ist meine 2. Stadt?" | Hoch | Mittel | Klare Tooltips, Farm Panel in Capital UI |
| Balance: Farm zu stark/schwach | Hoch | Hoch | Config via `PropertiesStore` + Playtest |

---

## Test-Plan

```bash
# 1. Unit Test: Farm Production Math
assert farmProduction(level=1) == 5.0
assert farmProduction(level=5) == 25.3

# 2. Integration Test: Save/Load
game.newGame(UNDEAD)
game.researchTech(NECROMANCY_HUMAN_FARM)
game.triggerEvent(FOUND_HUMAN_FARM, region=R1)
game.save("test.sav")
game.load("test.sav")
assert farmExists(R1) && farmLevel == 1

# 3. Playtest: 100 Days Undead
# - Farm Tech Day ~30
# - Farm Established Day ~50  
# - First Conversion Day ~80
# - Stable Growth Day ~120
```

---

## Alternative: "True" Dual Settlement (Future)

Falls **Mod SDK** `GameSaveApi` tieferen Zugriff erlaubt:

```java
// Hypothetisch - wenn Engine 2. Settlement unterstützt
Settlement humanFarm = gameApis.save().createSettlement(
    "Human Farm",
    SettlementType.OUTPOST,
    region.getMapTemplate()
);
// Dann: humanFarm.buildRoom(HUMAN_PENS), etc.
```

**Aktueller Stand:** Nicht in Mod SDK sichtbar → **Nicht verfolgen** für MVP.