# Vanilla Race System — Songs of Syx V71

## Race Datei-Struktur

```
data/assets/init/race/
├── HUMAN.txt
├── ORC.txt
├── CRETONIAN.txt
├── GARTHIMI.txt
├── ARGONOSH.txt
├── TILAPI.txt
├── CANTOR.txt
├── Q_AMEVIA.txt
├── DONDORIAN.txt
└── home/
    ├── HUMAN.txt
    ├── ORC.txt
    └── ...
```

---

## HUMAN.txt (Vanilla Reference)

```txt
PLAYABLE: true
PROPERTIES: {
  HEIGHT: 6, WIDTH: 9, BABY_DAYS: 12, CHILD_DAYS: 80
  CORPSE_DECAY: true, SLEEPS: true
  SLAVE_PRICE: 11, SLAVE_PRICE_RECOVERY: 0.5
  RAID_MERCINARY: 1.0
}
HOME: HUMAN
TECH: [*]
PREFERRED: {
  FOOD: [BREAD, MEAT, MUSHROOM, EGG]
  DRINK: [*]
  ROAD: { *: 0.1, STONE1: 0.5, STONE2: 0.8, DECOR1: 1.0 }
  STRUCTURE: { MOUNTAIN: 0.2, STONE: 0.7, GRAND: 1, WOOD: 0.5, OUTDOORS: 0.3 }
  POOL: { POOL_STONE: 1 }
  WORK: { _ASYLUM: 0.75, _EMBASSY: 1.0, LABORATORY_NORMAL: 2.0, LIBRARY_NORMAL: 2.0, ... }
  OTHER_RACES: { GARTHIMI: 0.75, CRETONIAN: 0.75, TILAPI: 0.2, ... }
  OTHER_RACES_REVERSE: { *: 1 }
  BUILDING_OVERRIDE: { CIVIC_L_STANDS: 1.5 }
}
POPULATION: { MAX: 1.0, GROWTH: 0.075, CLIMATE: { COLD: 0.8, TEMPERATE: 1.0, HOT: 0.8 }, TERRAIN: { MOUNTAIN: 0.2, FOREST: 0.2, NONE: 1.5 } }
TRAITS: { FIGHTER: 0.1, GLUTTON: 0.1, SPRINTER: 0.1 }
RESOURCE: { MEAT: 30, LEATHER: 10 }
STATS: { ACCESS_NOISE: { CITIZEN: 0.5, INVERTED: true }, ... }
SPRITE_FILE: HUMAN
ICON_SMALL: 24->race->Human->0
ICON_BIG: 32->race->Human->0

BOOST: {
  PHYSICS_RESISTANCE_COLD>ADD: -0.15, PHYSICS_RESISTANCE_HOT>ADD: -0.15
  PHYSICS_DEATH_AGE>MUL: 0.8, BATTLE_BLUNT_ATTACK>ADD: 10
  CIVIC_IMMIGRATION>MUL: 1.5, ROOM_UNIVERSITY*>MUL: 1.5
  BEHAVIOUR_LAWFULNESS>MUL: 0.75, BEHAVIOUR_SANITY>MUL: 0.8
  ROOM_FARM*>MUL: 1.1, ROOM_ORCHARD*>MUL: 1.1
}
EQUIPMENT_ENABLED: []
```

---

## ORC.txt (Vanilla Reference)

```txt
PLAYABLE: true
PROPERTIES: {
  HEIGHT: 7, WIDTH: 10, ADULT_AT_DAY: 60
}
HOME: ORC
TECH: [*]
PREFERRED: {
  FOOD: [MEAT]
  CLIMATE: { HOT: 1.0, WARM: 0.8 }
  OTHER_RACES: { HUMAN: 0.8, UNDEAD: 0.9 }
}
STATS: {
  BATTLE: { MELEE: 1.5, MORALE: 1.2 }
  ENVIRONMENT: { HEAT_RESISTANCE: 1.2, COLD_RESISTANCE: 0.5 }
  WORK: { MINING: 1.2 }
}
SPRITE_FILE: ORC
ICON_SMALL: 24->race->Orc->0
ICON_BIG: 32->race->Orc->0
```

---

## UNDEAD.txt — **Existiert NICHT in Vanilla!**

**Muss komplett neu erstellt werden.** Siehe `data-examples/UNDEAD.txt`.

---

## Race-Felder Referenz

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `PLAYABLE` | bool | Spieler kann Race beim Start wählen |
| `PROPERTIES` | object | Physische Props: Height, Width, Age, Corpse, Sleep, Slave Price |
| `HOME` | string | Verweis auf `data/assets/init/race/home/<NAME>.txt` |
| `TECH` | array | Verfügbare Techs (`*` = alle) |
| `PREFERRED` | object | Präferenzen: Food, Climate, Work, Other Races, Structures, Roads |
| `POPULATION` | object | Max, Growth, Climate/Terrain Modifiers |
| `TRAITS` | object | Trait-Wahrscheinlichkeiten (0.0-1.0) |
| `RESOURCE` | object | Drop bei Tod (Meat, Leather, etc.) |
| `STATS` | object | Detaillierte Stats: Access, Appearance, Battle, Disease, Education, Environment, Food, Service, Work, Burial, Equip, Religion, Monuments |
| `SPRITE_FILE` | string | Sprite-Datei Name (ohne .png) |
| `ICON_SMALL/BIG` | string | Icon Sprite Referenz `SIZE->CATEGORY->NAME->INDEX` |
| `BOOST` | object | **Global Race Boosts** — Syntax: `STAT>OP: VALUE` (ADD/MUL/SET) |
| `EQUIPMENT_ENABLED` | array | Welche Equipment-Slots Race nutzen kann |

---

## PREFERRED.WORK — Room Affinitäten

```txt
WORK: {
  ROOM_TYPE: AFFINITY  // -1.0 bis 2.0+, 0 = neutral
  _ASYLUM: 0.75
  LABORATORY_NORMAL: 2.0
  MINE_GEM: -1.0
  FARM*: 1.1
}
```
- **Positiv** = Race arbeitet gerne/effizient dort
- **Negativ** = Race vermeidet/schlecht dort
- **Wildcards** (`FARM*`) matchen alle Farm-Varianten

---

## PREFERRED.OTHER_RACES — Race Relations

```txt
OTHER_RACES: { TARGET_RACE: VALUE }  // Wie sehr THIS Race TARGET mag
OTHER_RACES_REVERSE: { TARGET_RACE: VALUE }  // Wie sehr TARGET THIS mag
```
- **1.0** = Neutral
- **>1.0** = Positiv (Immigration, Trade, Diplomacy Bonus)
- **<1.0** = Negativ (Conflict, weniger Immigration)

---

## BOOST — Global Race Modifiers

Syntax: `STAT_NAME>OPERATION: VALUE`

| Operation | Bedeutung |
|-----------|-----------|
| `>ADD` | Additiv: `BASE + VALUE` |
| `>MUL` | Multiplikativ: `BASE * VALUE` |
| `>SET` | Setzt auf Wert (selten) |

**Beispiele:**
```txt
BOOST: {
  CIVIC_IMMIGRATION>MUL: 1.5        // 50% mehr Immigration
  ROOM_UNIVERSITY*>MUL: 1.5         // Alle University Rooms 50% effizienter
  PHYSICS_DEATH_AGE>MUL: 0.8        // 20% kürzeres Leben
  WORK_MAINTENANCE>MUL: 1.5         // 50% bessere Maintenance Work
}
```

---

## Race-spezifische Dateien (home/)

`data/assets/init/race/home/HUMAN.txt` — Start-Settlement Config:
- Start-Gebäude
- Start-Ressourcen
- Start-Population
- Map-Layout

---

## Mod SDK: GameRaceApi

```java
GameRaceApi raceApi = gameApis.race();

// Alle Races
List<Race> all = raceApi.getAll();

// Race by Name
Optional<Race> undead = raceApi.getRace("UNDEAD");

// Race Likings lesen/setzen
double liking = raceApi.getLiking(raceA, raceB);
raceApi.setLiking(raceA, raceB, 0.5);  // Runtime ändern!

// Vanilla Referenzen
List<Race> vanillaRaces = raceApi.vanillaRaces();
List<Pair<Race, Race>> vanillaLikings = raceApi.vanillaLikings();
```

---

## Offene Fragen Race System

| Frage | Status |
|-------|--------|
| Kann `_ignoreVanilla: true` Vanilla Race überschreiben? | **Ja** — in SyxCraft bereits genutzt |
| Wie verhält sich `LIFE_IMMORTAL: true` bei Age/Death? | **Zu testen** — wahrscheinlich `DEATH_AGE` ignoriert |
| Funktioniert `CORPSE_DECAY: false` für Skelette? | **Wahrscheinlich** |
| Kann `RESOURCE` Drop bei Untoten `BONE`, `ESSENCE` sein? | **Ja** — neue Resource definieren |
| Wie interagiert `SLAVE_PRICE` mit `CLASS_SLAVE` Untoten? | **Unclear** — Untote sind keine Sklaven |