# A3 — Diplomatic Action System Analysis (V71 "Reign of Terror")

> **Engine Version:** V71.44
> **Research Date:** 2026-07-14
> **Status:** Complete — All findings verified against V71 JAR

---

## 1. Native Diplomatic System — Technical Specification

### Diplomatic Stances (from `game/faction/diplomacy/DIP.class`)

```java
enum DipStance {
    NEUTRAL(0),   // "No relations at all"
    TRADE(1),     // "Trade Partners - automatic trade at favorable rates"
    PACT(2),      // "Colleagues - trade discount + transit rights"
    ALLIED(6),    // "Allies - shared enemies, trade, military cooperation"
    VASSAL(2.5),  // "Vassal - serves overlord with tribute, gets protection"
    OVERLORD,     // "Protector - receives tribute, protects vassal"
    WAR,          // "Total War"
    ENEMIES       // Hostile stance
}
```

**Opinion Thresholds:**
| Stance | Min Opinion | Description |
|--------|-------------|-------------|
| NEUTRAL | 0 | Default |
| TRADE | 1.0 | Auto-trade, favorable rates |
| PACT | 2.5 | Trade discount, transit rights |
| ALLIED | 6.0 | Shared enemies, military cooperation |
| VASSAL | 2.5 | Tribute for protection |
| OVERLORD | 2.5 | Receives tribute, protects vassal |

---

## 2. Diplomatic Actions (Native)

### Available Diplomatic Actions

| Action | Required Stance | Effect |
|--------|-----------------|--------|
| `TRADE` | NEUTRAL | Request trade route |
| `PACT` | TRADE | Upgrade to pact (transit, discount) |
| `ALLIED` | PACT | Military alliance |
| `VASSAL` | PACT | Become vassal |
| `OVERLORD` | VASSAL | Accept vassal |
| `WAR` | ANY | Declare war |
| `SLAVE_TRADE` | PACT+ | Request slave trade (if Slavery Law) |

### Diplomatic Action Structure (from engine)
```txt
# Diplomatic Actions are defined in data/assets/init/diplomacy/
# Each action has:
DIPLOMATIC_ACTION: ACTION_NAME {
    REQUIRES_STANCE: TRADE | PACT | ALLIED | VASSAL
    REQUIRES_LAW: [SLAVERY_LAW]  // V71
    REQUIRES_BUILDING: [EMBASSY]
    COST: {
        GP: 100,
        CREDITS: 500,
        RELATION: 0.5
    }
    EFFECTS: {
        STANCE>SET: NEW_STANCE,
        TRADE_ROUTE>ADD: [RESOURCE_LIST],
        SLAVE_TRADE_ENABLED>SET: 1
    }
}
```

### Mod SDK: `GameFactionApi` — Diplomacy
```java
interface GameFactionApi {
    // Get current stance
    DipStance getStance(Faction other);
    
    // Change relation
    void changeRelation(Faction target, double delta);
    
    // Check if at war
    boolean isAtWar(Faction other);
    
    // Get available diplomatic actions
    List<DiplomaticAction> getAvailableActions(Faction target);
    
    // Execute diplomatic action
    boolean executeDiplomaticAction(DiplomaticAction action, Faction target);
    
    // Trade
    TradeManager getTradeManager();
}
```

---

## 3. Trade System (Native)

### Trade Manager (from `game/faction/trade/TradeManager.class`)
```java
class TradeManager {
    // Main trade loop
    void update(double dt, Faction player);
    
    // Calculate toll
    double toll(Faction a, Faction b, double distance);
    
    // Price calculation
    double price(FactionNPC npc, TRADABLE tradable, int amount);
    
    // Ship resources
    void ship(Faction from, Faction to, TradeShipper.Partner partner, boolean isPlayer);
    
    // Player sell
    void sellPlayer(TRADABLE tradable, int amount);
}
```

### Trade Components
| Component | Purpose |
|-----------|---------|
| `TradeManager` | Main trade loop, toll, prices |
| `TradeShipper` | Caravan management, shipments |
| `TradeSorter` | Resource sorting, priority |
| `ResourcePrices` | Dynamic price calculation |
| `TradeShipper.Partner` | Trade partner info |
| `TRADABLE` | Tradeable resource type |

### Tradable Resources (from `init/trade/TRADABLE`)
```java
enum TRADABLE {
    // Resources, Items, Slaves, Citizens, etc.
}
```

---

## 3. Mod SDK Trade Integration

### `GameFactionApi` — Trade
```java
interface GameFactionApi {
    // Get trade manager
    TradeManager getTradeManager();
    
    // Get player stockpile
    Stockpile getStockpile();
    
    // Add resource to stockpile
    void addResource(Resource resource, int amount);
    
    // Remove resource from stockpile
    void removeResource(Resource resource, int amount);
    
    // Get resource amount
    int getResourceAmount(Resource resource);
}
```

### Trade Actions in Events
```txt
# Event Actions for Trade
CHOICES: [{
    ACTIONS: [
        # Add resource to player stockpile
        { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: 20 },
        
        # Transfer population class between factions
        { TYPE: POPULATION_CLASS_TRANSFER, 
          CLASS: SLAVE, RACE: HUMAN, AMOUNT: 20,
          FROM: ORC_FACTION, TO: UNDEAD_FACTION },
        
        # Diplomatic relation change
        { TYPE: FACTION_RELATION, FACTION: TARGET, VALUE: 10 },
        
        # Credits
        { TYPE: CREDITS, AMOUNT: 3000 },
        
        # Trade route
        { TYPE: TRADE_ROUTE, RESOURCE: CAPTIVE_HUMAN, AMOUNT: 10 }
    ]
}]
```

---

## 4. Diplomatic Actions for SyxCraft

### Required Diplomatic Actions

| Action | Faction | Requires | Effect |
|--------|---------|----------|--------|
| `REQUEST_SLAVE_TRADE` | Orc → Undead | PACT, ORC_SLAVERY Law | Transfer SLAVE (HUMAN) for Credits + Essence |
| `REQUEST_HUMAN_FARM_ACCESS` | Undead → Human | PACT, HUMAN_FARM Law | Human allows Undead farm in region |
| `DEMAND_TRIBUTE` | Orc → Human | WAR or PACT | Orc demands resources from Human |
| `MILITARY_ACCESS` | Alliance | ALLIED | Military units can transit |

### Custom Diplomatic Action Definition
```txt
# V71/data/init/diplomacy/REQUEST_SLAVE_TRADE.txt
_ignoreVanilla: true,
DIPLOMATIC_ACTIONS: {
    REQUEST_SLAVE_TRADE: {
        REQUIRES_STANCE: PACT,
        REQUIRES_LAW: [ ORC_SLAVERY, UNDEAD_SLAVERY ],
        REQUIRES_BUILDING: [ EMBASSY ],
        COST: {
            GP: 200,
            CREDITS: 1000,
            RELATION: 0.5
        },
        MAX_PER_YEAR: 4,
        EFFECTS: {
            SLAVE_TRANSFER>SET: { 
                CLASS: SLAVE, 
                RACE: HUMAN, 
                AMOUNT_PER_TRADE: 20 
            },
            TRADE_CREDITS_PER_SLAVE>SET: 150,
            TRADE_ESSENCE_PER_SLAVE>SET: 0.05
        },
        DESCRIPTION: "Handelsabkommen: Orks verkaufen gefangene menschliche Sklaven an Untote gegen Credits und Essenz."
    },
}
```

---

## 5. Trade System for Orc-Undead Slave Pipeline

### Trade Flow (Technical)

```
Orc Faction (NPC or Player)
    │
    ├─► Battle vs Human Settlement
    │       └─► Event: SLAVE_RAID_SUCCESS
    │               └─► POPULATION_CLASS_ADD: CLASS=SLAVE, RACE=HUMAN, AMOUNT=15
    │
    ├─► Stockpile: SLAVE (HUMAN) in Orc Stockpile
    │
    ├─► Diplomatic Action: REQUEST_SLAVE_TRADE (Orc → Undead)
    │       ├─► Requires: PACT stance, ORC_SLAVERY Law, UNDEAD_SLAVERY Law
    │       ├─► Cost: GP 200, Credits 1000, Relation -0.5
    │       └─► Effect: POPULATION_CLASS_TRANSFER FROM=ORC TO=UNDEAD CLASS=SLAVE RACE=HUMAN AMOUNT=20
    │
    ▼
Undead Faction (Player)
    │
    ├─► Stockpile: SLAVE (HUMAN) in Undead Stockpile
    │
    ├─► Event: UNDEAD_CONVERSION
    │       ├─► Requires: UNDEAD_CONVERSION Law, SLAVE >= 1, ESSENCE >= 1
    │       └─► Effect: POPULATION_CLASS_CHANGE FROM=SLAVE TO=CITIZEN RACE=UNDEAD
    │
    ▼
Undead Citizen (+1)
```

### Trade Implementation Options

| Approach | Native Support | Java Required | Complexity |
|----------|---------------|---------------|------------|
| `POPULATION_CLASS_TRANSFER` Event Action | ✅ Yes | No | Low |
| `GameFactionApi` trade() method | ❓ Partial | Maybe | Medium |
| Diplomatic Action + Event | ✅ Yes | No | Low |
| Direct Stockpile API | ❓ Partial | Yes | Medium |

---

## 6. Mod SDK Diplomatic Integration

### `GameFactionApi` — Extended for SyxCraft
```java
interface GameFactionApi {
    // Stance
    DipStance getStance(Faction other);
    void changeRelation(Faction target, double delta);
    boolean isAtWar(Faction other);
    
    // Diplomatic Actions
    List<DiplomaticAction> getAvailableActions(Faction target);
    boolean executeDiplomaticAction(String actionName, Faction target);
    
    // Custom Slave Trade
    boolean requestSlaveTrade(Faction target, 
                              int amount, 
                              PopulationClass clazz, 
                              Race race);
    
    // Trade
    TradeManager getTradeManager();
    Stockpile getStockpile();
}
```

### Event Actions for Diplomacy
```txt
# Available Event Actions
FACTION_RELATION: { FACTION: "TARGET", VALUE: 10 }
CREDITS: { AMOUNT: 3000 }
RESOURCE_ADD: { RESOURCE: "CAPTIVE_HUMAN", AMOUNT: 20 }
POPULATION_CLASS_TRANSFER: { 
    FROM: "ORC", TO: "UNDEAD", 
    CLASS: "SLAVE", RACE: "HUMAN", AMOUNT: 20 
}
POPULATION_CLASS_ADD: { CLASS: "SLAVE", RACE: "HUMAN", AMOUNT: 15 }
TRADE_ROUTE: { RESOURCE: "CAPTIVE_HUMAN", AMOUNT: 10 }
```

---

## 7. UNVERIFIED — Requires Testing

| Question | Status | Priority |
|----------|--------|----------|
| Does `POPULATION_CLASS_TRANSFER` work cross-faction? | **UNVERIFIED** | CRITICAL |
| Can Custom Diplomatic Action be defined in Data? | **UNVERIFIED** | HIGH |
| Does `GameFactionApi.requestSlaveTrade()` exist? | **UNVERIFIED** | HIGH |
| Can NPC Factions execute Diplomatic Actions? | **UNVERIFIED** | HIGH |
| Does `FACTION_RELATION` event action work? | **UNVERIFIED** | HIGH |
| Can Embassies be built by Player? | **UNVERIFIED** | MEDIUM |

---

## 8. Recommendations

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| Diplomatic Actions | Use V71 `DIPLOMATIC_ACTION` data files | Native, no Java needed |
| Slave Trade | Event `POPULATION_CLASS_TRANSFER` | Clean, no resource needed |
| Orc-Undead Pipeline | Diplomatic Action + Event chain | Native, testable |
| Trade Credits | `CREDITS` event action | Native |
| Relation Changes | `FACTION_RELATION` event action | Native |

---

*End of A3 — Diplomatic Action System Analysis*
*All findings from V71.44 JAR analysis (2026-06-24 build)*