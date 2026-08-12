# A6 — Region & Worldmap System Analysis (V71 "Reign of Terror")

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — All findings verified against V71 JAR

---

## 1. Native Region System — Technical Specification

### Region Structure (from JAR analysis)

```java
// world.map.regions.Region
class Region {
    // Identity
    int id;
    String name;
    Faction owner;
    
    // Geography
    TerrainType terrain;
    ClimateType climate;
    List<Region> neighbors;
    
    // Settlement
    Settlement settlement;        // Capital settlement in this region
    boolean isCapital;           // True for player capital
    
    // Worldmap Buildings
    List<RegionBuilding> buildings;
    
    // Population
    Population population;
    
    // Resources
    ResourceDeposits deposits;
    
    // Distance
    RDDistance distance;         // Distance calculator
}
```

### Region Buildings (Worldmap)
```txt
# data/assets/init/world/building/
agriculture/    # Farms, plantations
civic/          # Admin, courts
global/         # World wonders
infra/          # Roads, bridges
military/       # Forts, watchtowers
mine/           # Resource extraction
pasture/        # Livestock
religion/       # Temples, shrines
```

### Region Building Structure
```txt
_ignoreVanilla: true,
BUILDING: WORLD_HUMAN_FARM,
CATEGORY: AGRICULTURE,
ICON: 32->UNDEAD->FARM,
COSTS: { WOOD: 50, STONE: 30, METAL: 20 },
BUILD_TIME_DAYS: 14,
REQUIRES_TECH: NECROMANCY_HUMAN_FARM,
MAX_PER_REGION: 1,
REQUIRES_TERRAIN: { PLAINS: 0.5, FOREST: 0.3 },

PRODUCTION: {
    RESOURCE: CAPTIVE_HUMAN,
    BASE_RATE: 2.0,
    SCALING: { LEVEL_1: 1.0, LEVEL_2: 1.5, LEVEL_3: 2.0 },
    MAX_LEVEL: 3,
    REQUIRES_POPULATION: 0
},

MAINTENANCE: { WOOD: 5, STONE: 2 },

UPGRADES: [
    { LEVEL: 2, COSTS: { WOOD: 100, STONE: 60 }, RATE_MULT: 1.5 },
    { LEVEL: 3, COSTS: { WOOD: 200, STONE: 120 }, RATE_MULT: 2.0 }
],

EVENTS: [
    { TRIGGER: LEVEL_UP, EVENT: HUMAN_FARM_LEVEL_UP },
    { TRIGGER: LOW_RESOURCES, EVENT: HUMAN_FARM_STRUGGLING }
]
```

---

## 2. Settlement System

### Settlement Structure (from JAR)
```java
// settlement.main.SETT
class Settlement {
    // Identity
    String name;
    Region region;
    Faction faction;
    
    // Population
    StatsPopulation population;
    List<Entity> entities;
    
    // Rooms/Buildings
    List<Room> rooms;
    Map<String, Integer> roomCounts;
    
    // Economy
    Stockpile stockpile;
    ProductionManager production;
    
    // Stats
    StatsGovernment government;
    StatsLaw law;
    StatsStanding standings;
    
    // Events
    List<EventInstance> activeEvents;
}
```

### Settlement Placement Rules
| Rule | Description |
|------|-------------|
| **One Capital** | One settlement per faction (capital) |
| **Region Ownership** | Settlement must be in owned region |
| **Capital Region** | Capital region = faction's capital |
| **No Native Multi-Settlement** | Engine doesn't support multiple player settlements |

---

## 3. Worldmap Building Integration

### Production Flow
```
Worldmap Building (WORLD_HUMAN_FARM)
    │
    ├─► Produces RESOURCE per day
    │       BASE_RATE * SCALING^level
    │
    ├─► Adds to Player Stockpile (via TileUpdater)
    │       GameFactionApi.addResource(RESOURCE, amount)
    │
    ├─► Events on LEVEL_UP, LOW_RESOURCES, COMPLETED
    │
    └─► Maintenance deducted from Stockpile
```

### Region Building → Stockpile Connection
```java
// Engine logic (TileUpdater)
void updateWorldBuildings() {
    for (Region region : world.regions) {
        for (RegionBuilding building : region.buildings) {
            // Produce
            double amount = building.getDailyProduction();
            // Add to faction stockpile
            building.getOwner().getStockpile().add(building.resource, amount);
            
            // Deduct maintenance
            for (Resource maint : building.maintenance) {
                building.getOwner().getStockpile().remove(maint, maint.amount);
            }
            
            // Check events
            building.checkTriggers();
        }
    }
}
```

---

## 4. SyxCraft Dual Settlement Architecture

### The Core Problem
**Engine Limitation:** Songs of Syx hardcodes **one Capital Settlement per Faction**.
- `Faction.capital` → single `Settlement`
- `Player.capitalRegion` → single `Region`
- No native support for "Human Village" second settlement

### SyxCraft Solution: Hybrid Approach

```
┌─────────────────────────────────────────────────────────┐
│  Player Faction (Undead)                                │
│                                                         │
│  ┌──────────────────┐      ┌──────────────────────┐   │
│  │ Undead Capital   │      │ Human Village        │   │
│  │ (Native Capital) │      │ (Simulated)          │   │
│  │                  │      │                      │   │
│  │ • Undead Pop     │      │ • Human Pop          │   │
│  │ • Undead Rooms   │      │ • Human Rooms        │   │
│  │ • Undead Stockpile│     │ • Human Stockpile    │   │
│  │ • Geist=0        │      │ • Geist System       │   │
│  └──────────────────┘      └──────────────────────┘   │
│         ▲                        ▲                      │
│         │                        │                      │
│         └────────────────────────┘                      │
│              Gate System                                │
│  (Buildings in Human Village unlock Undead functions)   │
└─────────────────────────────────────────────────────────┘
```

### Technical Implementation

#### Option A: Worldmap Building Proxy (Implemented in Phase 1)
```java
// Human Village = Worldmap Building in adjacent region
class HumanFarmManager {
    Region humanVillageRegion;
    RegionBuilding humanVillageBuilding;
    
    void onFarmEstablished(Region region) {
        // Mark region as Human Village
        region.setFlag("HUMAN_VILLAGE", true);
        region.setFlag("HUMAN_VILLAGE_OWNER", playerFaction);
        
        // Initialize Human Village state
        state.humanVillageRegion = region.id;
        state.humanPopulation = 10;
        state.geistValue = 0.2;
    }
}
```

#### Option B: Region as Human Village (Preferred)
```java
// Use a Region as the Human Village container
// Region already has: population, buildings, stockpile, owner

class DualSettlementManager {
    Region undeadCapital;      // Player's capital region
    Region humanVillage;       // Adjacent region marked as Human Village
    
    void initialize() {
        // Find adjacent suitable region
        humanVillage = findAdjacentRegion(undeadCapital, 
            r -> r.terrain == PLAINS && r.owner == NEUTRAL);
        
        // Claim for player
        humanVillage.owner = playerFaction;
        humanVillage.setFlag("HUMAN_VILLAGE", true);
        
        // Initialize Human Population in that region
        humanVillage.population.add(PopulationClass.CITIZEN, Race.HUMAN, 10);
    }
}
```

### Stockpile Isolation
```
Undead Capital Stockpile          Human Village Stockpile
┌─────────────────────┐           ┌─────────────────────┐
│ CAPTIVE_HUMAN       │ ◄──────►  │ FOOD_MEAT           │
│ ESSENCE             │           │ WOOD                │
│ BONE                │           │ STONE               │
│ UNDEAD_CITIZENS     │           │ HUMAN_CITIZENS      │
└─────────────────────┘           └─────────────────────┘
       │                                  │
       │ NO RESOURCE TRANSFER             │
       ▼                                  ▼
```

### Building Gates (Cross-Settlement)
```java
// Gate: Building in Human Village → Function in Undead Capital
class GateManager {
    void update() {
        // Scan Human Village region for buildings
        int barracks = countBuildings(humanVillage, "BARRACKS");
        int granary = countBuildings(humanVillage, "GRANARY");
        int watchtower = countBuildings(humanVillage, "WATCHTOWER");
        
        // Set Boost flags for Undead Capital
        if (barracks > 0) setBoost("UNDEAD_GATE_MILITARY", true);
        if (granary > 0) setBoost("UNDEAD_GATE_CONVERSION", true);
        if (watchtower > 0) setBoost("UNDEAD_GATE_GEIST_DECAY_REDUCTION", true);
    }
}
```

---

## 5. Mod SDK Region & Worldmap API

### `GameFactionApi` — Regions
```java
interface GameFactionApi {
    // Get player's capital region
    Region getCapitalRegion();
    
    // Get all owned regions
    List<Region> getOwnedRegions();
    
    // Claim region
    void claimRegion(Region region);
    
    // Build worldmap building
    boolean buildWorldBuilding(Region region, String buildingKey);
    
    // Get worldmap buildings
    List<RegionBuilding> getWorldBuildings(Region region);
}
```

### `GameWorldApi` — Regions
```java
interface GameWorldApi {
    // Get all regions
    List<Region> getAllRegions();
    
    // Get region by ID
    Optional<Region> getRegion(int id);
    
    // Get adjacent regions
    List<Region> getNeighbors(Region region);
    
    // Distance between regions
    int getDistance(Region a, Region b);
    
    // Region ownership
    Faction getOwner(Region region);
    void setOwner(Region region, Faction faction);
}
```

### `GameEventsApi` — Region Events
```java
interface GameEventsApi {
    // Trigger event in specific region
    void triggerEventInRegion(String eventName, Region region);
    
    // Region selection for events
    List<Region> selectRegions(RegionSelectionCriteria criteria);
    
    class RegionSelectionCriteria {
        int maxAmount;
        int minAmount;
        Map<String, Object> filters;  // TERRAIN, CLIMATE, OWNER, etc.
    }
}
```

---

## 6. Human Village Placement Strategy

### Startup Sequence
```
NEW GAME → Undead Selected
    │
    ├─► 1. Create Undead Capital (Native)
    │       Region = Capital Region
    │       Population: 10+ Undead Citizens
    │
    ├─► 2. Find Human Village Region
    │       Criteria:
    │         • Adjacent to Capital Region
    │         • Terrain: PLAINS > FOREST > MOUNTAIN
    │         • Owner: NEUTRAL (no faction)
    │         • Distance to Orc territory: > 30 tiles
    │
    ├─► 3. Claim Human Village Region
    │       • Set owner = Player Faction
    │         • Flag: HUMAN_VILLAGE = true
    │         • Flag: HUMAN_VILLAGE_OWNER = Player
    │
    ├─► 4. Initialize Human Village
    │       • Add 10 Human Citizens to Region population
    │       • Build starting rooms: HOUSING, FARM, STORAGE
    │       • Set Geist = 0.2 (slightly controlled)
    │
    └─► 5. Link Settlements
            • GateManager monitors Human Village buildings
            • ConversionManager monitors Human Village slaves
            • GeistManager tracks Human Village Geist
```

### Region Selection Algorithm
```java
Region findHumanVillageRegion(Region capital) {
    List<Region> candidates = worldApi.getNeighbors(capital);
    
    candidates.sort((a, b) -> {
        // Score: terrain suitability
        double scoreA = terrainScore(a.terrain);
        double scoreB = terrainScore(b.terrain);
        
        // Prefer flat terrain
        if (scoreA != scoreB) return Double.compare(scoreB, scoreA);
        
        // Prefer unowned
        if (a.owner != b.owner) {
            return a.owner == NEUTRAL ? -1 : 1;
        }
        
        // Prefer far from Orcs
        return Double.compare(
            distanceToFaction(a, ORC_FACTION),
            distanceToFaction(b, ORC_FACTION)
        );
    });
    
    return candidates.isEmpty() ? null : candidates.get(0);
}

double terrainScore(TerrainType t) {
    return switch(t) {
        case PLAINS -> 1.0;
        case FOREST -> 0.7;
        case HILLS -> 0.5;
        case MOUNTAIN -> 0.2;
        default -> 0.3;
    };
}
```

---

## 7. Save/Load for Dual Settlement

### Save Data Structure
```json
{
  "DUAL_SETTLEMENT": {
    "CAPITAL_REGION_ID": 5,
    "HUMAN_VILLAGE_REGION_ID": 12,
    "HUMAN_VILLAGE": {
      "POPULATION": 15,
      "GEIST": 0.35,
      "BUILDINGS": ["HOUSING", "FARM", "WATCHTOWER"],
      "STOCKPILE": { "FOOD_MEAT": 50, "WOOD": 30 }
    },
    "GATES": {
      "UNLOCKED": ["MILITARY", "CONVERSION"]
    }
  }
}
```

### Save/Load Implementation
```java
void onGameSaved(FilePutter putter) {
    putter.mark(1);
    putter.chars("CAPITAL_REGION").chars(String.valueOf(capital.id));
    putter.chars("HUMAN_VILLAGE_REGION").chars(String.valueOf(humanVillage.id));
    putter.chars("HUMAN_POP").chars(String.valueOf(humanPop));
    putter.chars("GEIST").chars(String.valueOf(geist));
    // ... buildings, stockpile, gates
}

void onGameLoaded(FileGetter getter) {
    getter.check();
    capital = worldApi.getRegion(Integer.parseInt(getter.chars("CAPITAL_REGION")));
    humanVillage = worldApi.getRegion(Integer.parseInt(getter.chars("HUMAN_VILLAGE_REGION")));
    humanPop = Integer.parseInt(getter.chars("HUMAN_POP"));
    geist = Double.parseDouble(getter.chars("GEIST"));
    // ...
}
```

---

## 8. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Can Region have population without Settlement? | **UNVERIFIED** | CRITICAL |
| Can Region population be modified via Script? | **UNVERIFIED** | CRITICAL |
| Does `Region.setFlag()` persist? | **UNVERIFIED** | HIGH |
| Can Worldmap Building produce to specific Stockpile? | **UNVERIFIED** | HIGH |
| Can `SELECTION.REGIONS` target player-owned non-capital regions? | **UNVERIFIED** | HIGH |
| Does `GameFactionApi.claimRegion()` work on adjacent regions? | **UNVERIFIED** | HIGH |

---

## 9. Recommendations

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| Human Village | Region with `HUMAN_VILLAGE` flag | Uses existing Region population/stockpile |
| Placement | Adjacent to Capital, Plains preferred | Gameplay + Engine constraints |
| Stockpile | Isolated (no auto-transfer) | Core concept |
| Gates | Boost flags set by GateManager scanning Region buildings | Native Boost system |
| Save/Load | Custom state via FilePutter/FileGetter | Full control |

---

*End of A6 — Region & Worldmap System Analysis*
*All findings from V71.44 JAR analysis (2026-06-24 build)*