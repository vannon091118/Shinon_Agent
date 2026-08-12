# Vanilla Reference — Songs of Syx Data Structures

## Race System (`data/assets/init/race/`)

### HUMAN.txt (Vanilla)
```txt
PLAYABLE: true
PROPERTIES: { HEIGHT: 6, WIDTH: 9, BABY_DAYS: 12, CHILD_DAYS: 80, CORPSE_DECAY: true, SLEEPS: true, SLAVE_PRICE: 11, SLAVE_PRICE_RECOVERY: 0.5, RAID_MERCINARY: 1.0 }
HOME: HUMAN
TECH: [*]
PREFERRED: { FOOD: [BREAD, MEAT, MUSHROOM, EGG], DRINK: [*], WORK: { LABORATORY_NORMAL: 2.0, LIBRARY_NORMAL: 2.0, FARM*: 1.1 }, OTHER_RACES: { GARTHIMI: 0.75, CRETONIAN: 0.75, TILAPI: 0.2 } }
POPULATION: { MAX: 1.0, GROWTH: 0.075, CLIMATE: { COLD: 0.8, TEMPERATE: 1.0, HOT: 0.8 } }
TRAITS: { FIGHTER: 0.1, GLUTTON: 0.1, SPRINTER: 0.1 }
RESOURCE: { MEAT: 30, LEATHER: 10 }
BOOST: { PHYSICS_RESISTANCE_COLD>ADD: -0.15, CIVIC_IMMIGRATION>MUL: 1.5, ROOM_UNIVERSITY*>MUL: 1.5, ROOM_FARM*>MUL: 1.1 }
SPRITE_FILE: HUMAN
```

### ORC.txt (Vanilla)
```txt
PROPERTIES: { HEIGHT: 7, WIDTH: 10, ADULT_AT_DAY: 60 }
HOME: ORC
PREFERRED: { FOOD: [MEAT], CLIMATE: { HOT: 1.0, WARM: 0.8 }, OTHER_RACES: { HUMAN: 0.8, UNDEAD: 0.9 } }
STATS: { BATTLE: { MELEE: 1.5, MORALE: 1.2 }, ENVIRONMENT: { HEAT_RESISTANCE: 1.2, COLD_RESISTANCE: 0.5 }, WORK: { MINING: 1.2 } }
```

---

## Resource System (`data/assets/init/resource/`)

### Supply Resource (CLOTHES.txt)
```txt
RESOURCE: CLOTHES,
MORALE_ADD: 0,
HEALTH_EFFECT: 0.5,
CONSUMPTION_PER_USER_DAY: 0.03125,
CONSUMPTION_PER_ITEM_DAY: 0,
AMOUNT_PER_PERSON: 1,
RACES: [*]
```

---

## Event System (`data/assets/init/event/`)

### SLAVES.txt Structure
```txt
SLAVE_DRUGS: {
  OCCURRENCE: { RACE: { *: 1.0 }, REQUIRES: { GREATER: { POPULATION_SLAVE_F: 0.2, GOVERN_RICHES: 0.10 } } },
  TAGS: { ALLOW_NOT: [CHAIN_ONGOING, SLAVE_DRUGS_NO] },
  SELECTION: { SUBJECTS: { FILTERS: [{ EQUAL: { CLASS_SLAVE: 1 } }], MAX_AMOUNT: { RELATIVE: 0.04 } } },
  CHOICES: [
    { ACTIONS: [ { TYPE: EVENT, EVENT: SLAVE_DRUGS_YES }, { TYPE: SUBJECTS_KILL, AMOUNTS: { *: { RELATIVE: 0.04 } }, DEATH_CAUSE: SLAYED, USE_SELECTION: true }, { TYPE: CREDITS, PER_PERSON: -80 } ] },
    { ACTIONS: [ { TYPE: EVENT, EVENT: SLAVE_DRUGS_NO } ] }
  ]
}
```

**Action Types:** `EVENT`, `SUBJECTS_KILL`, `CREDITS`, `BOOST`, `BOOST_PERM`, `RESOURCE_ADD`, `CITIZEN_ADD`, `SETTLEMENT_ADD`, `FACTION_RELATION`

---

## Tech System (`data/assets/init/tech/`)

### CIVIC.txt Example
```txt
TREE: {
  0: [FOOD0, _____, MARK0, _____, REL00, REL22, STAG0, AREA0, NURS1, LAV00, _____, HOSP0, _____],
  1: [CANT0, INN00, MARK1, TAVER, REL11, REL33, STAG1, AREA1, NURS2, ASY00, LAV01, DOC00, _____],
}
COLOR: 0_148_255
CATEGORY: 25
TECHS: {
  NURS1: { COSTS: { CIVIC_KNOWLEDGE: 10 }, UNLOCKS_FACTION: [ROOM_NURSERY_NORMAL], REQUIRES: { GREATER: { POPULATION: 250 } } },
  STAG0: { COSTS: { CIVIC_KNOWLEDGE: 5 }, UNLOCKS_FACTION: [ROOM_STAGE_NORMAL] },
  ALLIANCE_COMMAND: { COSTS: { CIVIC_KNOWLEDGE: 50 }, REQUIRES_TECH_LEVEL: { BASIC_MINING: 1 }, UNLOCKS_FACTION: [ROOM_ALLIANCE_HQ] }
}
```

---

## Script System

### Vanilla SCRIPT Interface
```java
interface SCRIPT {
    CharSequence name();
    CharSequence desc();
    boolean initBeforeGameCreated();
    boolean isSelectable();
    boolean forceInit();
    SCRIPT_INSTANCE createInstance();
}

interface SCRIPT_INSTANCE {
    void update(double deltaSeconds);
    void initBeforeGameCreated();
    void initBeforeGameInited();
    void initNewGameSession();
    void onGameLoaded(Path, FileGetter);
    void onGameSaved(Path, FilePutter);
    void onGameSaveReloaded();
    void onBeforeBattle();
    void onBattle();
    void onAfterBattle();
    void onCrash(Throwable);
    boolean handleBrokenSavedState();
}
```

### Phases (from Phases.class)
```java
INIT_BEFORE_GAME_CREATED
INIT_GAME_RESOURCES_LOADED
INIT_MOD_CREATE_INSTANCE
ON_GAME_SAVE_LOADED / ON_GAME_SAVE_RELOADED
INIT_NEW_GAME_SESSION
INIT_GAME_UPDATING
ON_GAME_UPDATE(dt)
INIT_GAME_UI_PRESENT
INIT_SETTLEMENT_UI_PRESENT
ON_GAME_SAVED
ON_BEFORE_BATTLE / ON_BATTLE / ON_AFTER_BATTLE
ON_CRASH
```