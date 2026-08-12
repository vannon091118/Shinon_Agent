# Vanilla Event System — Songs of Syx V71

## Event-Dateien in Vanilla

```
data/assets/init/event/
├── ARTI.txt      // Artifacts
├── CIVIC.txt     // Civic Events (Bürgermeister, Gesetze, etc.)
├── DIPLO.txt     // Diplomacy Events
├── EARLY.txt     // Early Game Events
├── ENVIRO.txt    // Environment Events (Weather, Disasters)
├── HINT.txt      // Tutorial Hints
├── PROD.txt      // Production Events
├── REGION.txt    // Worldmap Region Events
├── RELIGION.txt  // Religion Events
├── SLAVES.txt    // Slavery Events (wichtig für Undead!)
├── TEST.txt      // Test Events
└── _CONFIG.txt   // Global Event Config
```

---

## Event-Struktur (am Beispiel `SLAVES.txt`)

```txt
EVENT_NAME: {
  ICON: 32->ICON_CATEGORY->INDEX,
  DURATION: { DAYS: 1.0, ACTIONS: [{ TYPE: EVENT, EVENT: FOLLOW_UP_EVENT }] },
  
  OCCURRENCE: {
    CLIMATE: { *: 1.0 },
    TERRAIN: { *: 1.0 },
    RACE: { *: 1.0 },
    REQUIRES: { GREATER: { POPULATION_SLAVE_F: 0.2, GOVERN_RICHES: 0.10 } }
  },
  
  TAGS: { ALLOW_NOT: [CHAIN_ONGOING, SLAVE_DRUGS_NO] },
  
  SELECTION: {
    SUBJECTS: {
      USE_AS_ICON: true,
      MAX_AMOUNT: { RELATIVE: 0.04 },
      FILTERS: [
        { EQUAL: { CLASS_SLAVE: 1 } }
      ]
    }
  },
  
  CHOICES: [
    {
      ACTIONS: [
        { TYPE: EVENT, EVENT: SLAVE_DRUGS_YES },
        { TYPE: SUBJECTS_KILL, AMOUNTS: { *: { RELATIVE: 0.04 } }, DAMAGE: false, DEATH_CAUSE: SLAYED, USE_SELECTION: true },
        { TYPE: CREDITS, PER_PERSON: -80 }
      ]
    },
    {
      ACTIONS: [
        { TYPE: EVENT, EVENT: SLAVE_DRUGS_NO }
      ]
    }
  ]
}
```

---

## Event-Felder erklärt

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `ICON` | string | Sprite-Referenz `SIZE->CATEGORY->INDEX` |
| `DURATION` | object | Dauer + optionale Follow-up Actions |
| `OCCURRENCE` | object | **Spawn-Bedingungen** (Climate, Terrain, Race, Requirements) |
| `TAGS` | object | Chain-Control (`ALLOW_NOT`, `REQUIRE`) |
| `SELECTION` | object | **Wer ist betroffen** (SUBJECTS, REGIONS, FACTIONS, etc.) |
| `CHOICES` | array | Spieler-Optionen mit Actions |

---

## OCCURRENCE — Spawn-Bedingungen

```txt
OCCURRENCE: {
  CLIMATE: { COLD: 0.5, TEMPERATE: 1.0, HOT: 0.0 },  // 0 = nie, 1 = normal
  TERRAIN: { MOUNTAIN: 0.0, FOREST: 1.0, *: 0.5 },
  RACE: { HUMAN: 1.0, ORC: 0.5, UNDEAD: 0.0 },
  REQUIRES: {
    GREATER: { POPULATION: 100, CIVIC_KNOWLEDGE: 50 },
    LESS: { WORLD_THREAT: 0.5 },
    EQUAL: { HAS_TECH: NECROMANCY }
  },
  MAX_SPAWNS: 1  // Wie oft maximal pro Spiel
}
```

---

## SELECTION — Ziel-Auswahl

| Selection Type | Filter | Beispiel |
|----------------|--------|----------|
| `SUBJECTS` | `CLASS_CITIZEN`, `CLASS_SLAVE`, `CLASS_NOBLE`, `RACE`, `MAX_AMOUNT` | Bürger, Sklaven, Adelige |
| `REGIONS` | `POPULATION_RACE_HUMAN`, `FACTION_IS_PLAYER`, `HAS_BOOST_PERM` | Weltkarten-Regionen |
| `FACTIONS` | `RELATION`, `IS_PLAYER` | Andere Fraktionen |

```txt
SELECTION: {
  SUBJECTS: {
    FILTERS: [
      { EQUAL: { CLASS_CITIZEN: 1, RACE: HUMAN } },
      { GREATER: { AGE: 20 } }
    ],
    MAX_AMOUNT: { RELATIVE: 0.1 }  // 10% der passenden Bevölkerung
  }
}
```

---

## CHOICE ACTIONS — Was passiert bei Auswahl

| Action Type | Parameter | Beschreibung |
|-------------|-----------|--------------|
| `EVENT` | `EVENT: NAME` | Triggert anderes Event |
| `SUBJECTS_KILL` | `AMOUNTS`, `DAMAGE`, `DEATH_CAUSE`, `USE_SELECTION` | Tötet ausgewählte Einheiten |
| `CREDITS` | `PER_PERSON`, `AMOUNT` | Gold geben/nehmen |
| `BOOST` | `PLAYER: { STAT>OP: VALUE }` | Temporärer Stat-Boost |
| `BOOST_PERM` | `PLAYER: { STAT>OP: VALUE }`, `USE_SELECTION_REGIONS` | **Permanenter** Boost |
| `RESOURCE_ADD` | `RESOURCE: NAME`, `AMOUNT` | Resource hinzufügen/entfernen |
| `CITIZEN_ADD` | `RACE: NAME`, `AMOUNT` | Bürger hinzufügen (Rasse wählbar!) |
| `CITIZEN_REMOVE` | `RACE`, `AMOUNT` | Bürger entfernen |
| `SETTLEMENT_ADD` | `BUILDING: NAME` | Gebäude bauen |
| `FACTION_RELATION` | `FACTION`, `VALUE` | Diplomatie ändern |

---

## Conversion Event Design: Human → Undead

### `CONVERT_HUMAN_TO_UNDEAD.txt`

```txt
CONVERT_HUMAN_TO_UNDEAD: {
  ICON: 32->UNDEAD->CONVERSION,
  DURATION: { DAYS: 1.0 },
  
  OCCURRENCE: {
    RACE: { UNDEAD: 1.0 },
    REQUIRES: {
      GREATER: { 
        POPULATION_CITIZEN_HUMAN: 10,
        RESOURCE_CAPTIVE_HUMAN: 5 
      }
    }
  },
  
  TAGS: { ALLOW_NOT: [CHAIN_ONGOING] },
  
  SELECTION: {
    SUBJECTS: {
      USE_AS_ICON: true,
      FILTERS: [
        { EQUAL: { CLASS_CITIZEN: 1, RACE: HUMAN } }
      ],
      MAX_AMOUNT: { RELATIVE: 0.1 }
    }
  },
  
  CHOICES: [
    {
      // Option: Konvertieren
      ACTIONS: [
        { TYPE: SUBJECTS_KILL, AMOUNTS: { HUMAN: { RELATIVE: 0.1 } }, DEATH_CAUSE: NECROMANCY, USE_SELECTION: true },
        { TYPE: EVENT, EVENT: UNDEAD_RISE },
        { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: -5 },
        { TYPE: CITIZEN_ADD, RACE: UNDEAD, AMOUNT: { RELATIVE: 0.1 } }
      ]
    },
    {
      // Option: Abbrechen
      ACTIONS: [
        { TYPE: EVENT, EVENT: CONVERT_CANCELLED }
      ]
    }
  ]
}
```

### Folge-Event: `UNDEAD_RISE.txt`

```txt
UNDEAD_RISE: {
  ICON: 32->UNDEAD->RISE,
  DURATION: { DAYS: 5.0 },
  ON_SPAWN: {
    ACTIONS: [
      { TYPE: BOOST_PERM, PLAYER: { UNDEAD_CONVERSION_EFFICIENCY>ADD: 0.05 } }
    ]
  }
}
```

---

## Human Farm Event: Gründung

### `FOUND_HUMAN_FARM.txt`

```txt
FOUND_HUMAN_FARM: {
  ICON: 32->UNDEAD->FARM,
  DURATION: { DAYS: 1.0 },
  
  OCCURRENCE: {
    RACE: { UNDEAD: 1.0 },
    REQUIRES: {
      EQUAL: { HAS_TECH: NECROMANCY_HUMAN_FARM }
    },
    MAX_SPAWNS: 1
  },
  
  TAGS: { ALLOW_NOT: [HAS_HUMAN_FARM] },
  
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
  
  CHOICES: [
    {
      ACTIONS: [
        { TYPE: EVENT, EVENT: HUMAN_FARM_ESTABLISHED },
        { TYPE: SETTLEMENT_ADD, BUILDING: WORLD_HUMAN_FARM },
        { TYPE: BOOST_PERM, USE_SELECTION_REGIONS: true, PLAYER: { HAS_HUMAN_FARM>SET: 1 } }
      ]
    }
  ]
}
```

---

## Orc Slavery Event: Raid → Captives

### `ORC_SLAVE_RAID.txt`

```txt
ORC_SLAVE_RAID: {
  ICON: 32->ORC->RAID,
  DURATION: { DAYS: 10.0 },
  
  OCCURRENCE: {
    RACE: { ORC: 1.0 },
    REQUIRES: { EQUAL: { HAS_TECH: ORC_SLAVERY } }
  },
  
  SELECTION: {
    REGIONS: {
      FILTERS: [
        { EQUAL: { FACTION_IS_PLAYER: 0 } },
        { GREATER: { POPULATION_RACE_HUMAN: 50 } }
      ]
    }
  },
  
  CHOICES: [
    {
      ACTIONS: [
        { TYPE: EVENT, EVENT: SLAVE_RAID_SUCCESS },
        { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: 20 }
      ]
    }
  ]
}
```

---

## Mod SDK: GameEventsApi (Runtime Event Manipulation)

Aus Argon Mod SDK V0 (`GameEventsApi.class`):

```java
// Events zur Runtime lesen
List<EventResource> resources = gameEventsApi.getEventResources();

// Einzelnes Event holen
Optional<EventResource> event = gameEventsApi.getEventResource("CONVERT_HUMAN_TO_UNDEAD");

// Event-Container bauen (für Runtime-Event-Erstellung)
EventContainer container = EventContainer.builder()
    .context(EventContainer.Context.ON_SPAWN)
    .event(customEvent)
    .build();

// Event-Locks (verhindern Spam)
Map<String, EventLocker> locks = gameEventsApi.getEventLockers();

// Event Tree lesen (alle Events mit Conditions/Choices)
Map<String, TreeNode> trees = gameEventsApi.readEventTrees();
```

**Mächtig:** Events können zur **Runtime** erstellt/modifiziert werden → Dynamic Events basierend auf Game State!

---

## Offene Fragen Events

| Frage | Status |
|-------|--------|
| Kann `CITIZEN_ADD` mit `RACE: UNDEAD` wirklich Untote erschaffen? | **Zu testen** — Engine-Check |
| Wie interagiert `RESOURCE_ADD` mit `RACES: [UNDEAD]` Resource? | **Zu testen** — Trade/Stockpile Check |
| Kann `SELECTION.REGIONS` Weltkarten-Regionen für Building-Placement nutzen? | **Wahrscheinlich** — `SETTLEMENT_ADD` nutzt Selection |
| Wie verhindere ich Event-Spam bei `ON_GAME_UPDATE` Checks? | **Script-seitig** — State Manager + Cooldowns |
| Gibt es `ON_GAME_LOAD` Event für Farm-Wiederherstellung? | **Ja** — `ON_GAME_SAVE_LOADED` / `ON_GAME_SAVE_RELOADED` Phasen |

---

## Event-Dateien für Undead Concept (zu erstellen)

```
V70/data/init/event/
├── UNDEAD_CONVERSION.txt      // Human → Undead Conversion
├── HUMAN_FARM.txt             // Farm Gründung + Management
├── ORC_SLAVERY.txt            // Orc Slave Raids → Captive Humans
├── NECROMANCY_POLICY.txt      // Undead Policy Activation
└── CAPTIVE_HUMAN_TRADE.txt    // Trade Events Orc→Undead
```