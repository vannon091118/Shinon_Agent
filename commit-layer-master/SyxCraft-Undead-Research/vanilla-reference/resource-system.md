# Vanilla Resource System — Songs of Syx V71

## Resource-Kategorien (Hardcoded Engine)

```
data/assets/init/resource/
├── drinkable/    // Getränke
├── edible/       // Nahrung
├── growable/     // Anbaubar (Farms)
├── minable/      // Abbaubar (Minen)
├── supply/       // Verbrauchsgüter (Clothes, Ration, etc.)
└── work/         // Arbeitsressourcen (Tools, etc.)
```

**Wichtig:** Kategorie bestimmt Engine-Verhalten (Consumption, Production, UI). Nicht erweiterbar ohne Code-Änderung.

---

## Beispiel: `data/assets/init/resource/supply/CLOTHES.txt` (Vanilla)

```txt
RESOURCE: CLOTHES,
MORALE_ADD: 0,
HEALTH_EFFECT: 0.5,
CONSUMPTION_PER_USER_DAY: 0.03125,
CONSUMPTION_PER_ITEM_DAY: 0,
AMOUNT_PER_PERSON: 1,
RACES: [*]
```

### Feld-Erklärungen

| Feld | Typ | Bedeutung |
|------|-----|-----------|
| `RESOURCE` | string | **Eindeutiger Name** (muss Dateiname entsprechen) |
| `MORALE_ADD` | float | Moral-Bonus/Malus pro Einheit (täglich?) |
| `HEALTH_EFFECT` | float | Gesundheits-Effekt (0-1?) |
| `CONSUMPTION_PER_USER_DAY` | float | Verbrauch pro Person/Tag |
| `CONSUMPTION_PER_ITEM_DAY` | float | Verbrauch pro Item/Tag (Verfall) |
| `AMOUNT_PER_PERSON` | int | Wie viele Items eine Person "hält" |
| `RACES` | array | Welche Rassen nutzen diese Resource (`*` = alle) |

---

## Beispiel: `data/assets/init/resource/edible/MEAT.txt` (Vanilla - extrapoliert)

```txt
RESOURCE: MEAT,
MORALE_ADD: 0.1,
HEALTH_EFFECT: 0.2,
CONSUMPTION_PER_USER_DAY: 0.5,
CONSUMPTION_PER_ITEM_DAY: 0.02,
AMOUNT_PER_PERSON: 1,
RACES: [*]
```

---

## SyxCraft V70 Resources (bereits definiert)

| Resource | Kategorie | Datei |
|----------|-----------|-------|
| IRON | minable/supply? | `V70/data/init/resource/IRON.txt` |
| LEATHER | supply | `V70/data/init/resource/LEATHER.txt` |
| MEAT | edible | `V70/data/init/resource/MEAT.txt` |
| SILVER | minable | `V70/data/init/resource/SILVER.txt` |
| STEEL | supply/work? | `V70/data/init/resource/STEEL.txt` |
| STONE | minable | `V70/data/init/resource/STONE.txt` |
| VEGETABLES | edible/growable | `V70/data/init/resource/VEGETABLES.txt` |
| WOOD | growable/minable | `V70/data/init/resource/WOOD.txt` |

---

## Design: `CAPTIVE_HUMAN` Resource für Undead

### Entscheidung: **Kategorie `supply`**

**Begründung:**
- Keine Nahrung (`edible`) — wird nicht gegessen
- Kein Anbau (`growable`) — keine Farm im klassischen Sinn
- Kein Abbau (`minable`) — keine Mine
- Kein Werkzeug (`work`) — kein Tool
- **`supply`** = Verbrauchsgut, das gelagert, gehandelt, verbraucht wird ✓

### Definition: `V70/data/init/resource/supply/CAPTIVE_HUMAN.txt`

```txt
RESOURCE: CAPTIVE_HUMAN,
MORALE_ADD: -0.5,
HEALTH_EFFECT: 0.1,
CONSUMPTION_PER_USER_DAY: 0.0,
CONSUMPTION_PER_ITEM_DAY: 0.0,
AMOUNT_PER_PERSON: 1,
RACES: [UNDEAD]
```

### Feld-Begründung

| Feld | Wert | Warum |
|------|------|-------|
| `MORALE_ADD: -0.5` | Negativ | Menschen in Gefangenschaft = moralischer Malus für Undead-Settlement |
| `HEALTH_EFFECT: 0.1` | Leicht positiv | "Frische" Menschen = Gesundheit? Oder 0? |
| `CONSUMPTION_PER_USER_DAY: 0.0` | 0 | Wird nicht *täglich* verbraucht, nur bei Conversion |
| `CONSUMPTION_PER_ITEM_DAY: 0.0` | 0 | Kein Verfall (Menschen "halten" sich) |
| `AMOUNT_PER_PERSON: 1` | 1 | 1 Captive Human = 1 Unit |
| `RACES: [UNDEAD]` | Nur Undead | **Nur Undead** können diese Resource nutzen/lagern/handeln |

---

## Resource Usage in Rooms (Vanilla Room Structure)

Beispiel: `data/assets/init/room/LABORATORY_NORMAL.txt` (Vanilla)

```txt
CONSUMPTION: {
  CLAY: { RATE: 0.75, BONUS: 1 },
},
WORK: { SHIFT_OFFSET: 0.375, SOUND: DUMMY, USES_TOOL: true, FULFILLMENT: 1.0 },
OUTPUT: { ... }  // Explizites OUTPUT Feld existiert in Vanilla?
```

**Wichtig:** Vanilla Rooms haben `CONSUMPTION` für Input-Resources. **Output** wird über `WORK` + Items definiert oder über Events.

Für **Human Pens** (Produktion von CAPTIVE_HUMAN):
- `CONSUMPTION: { CAPTIVE_HUMAN: { RATE: 1.0, BONUS: 0.1 } }` — verbraucht Captive Humans (für Fütterung?)
- **ABER:** Wie produziert Room Output? → Über `WORK` + `ITEMS` + `BOOST` oder Custom Script

---

## Resource in Events (SLAVES.txt)

```txt
CHOICES: [{
  ACTIONS: [
    { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: -5 },
    { TYPE: RESOURCE_ADD, RESOURCE: CAPTIVE_HUMAN, AMOUNT: 10 }
  ]
}]
```

**Action Types für Resources:**
- `RESOURCE_ADD` — Resource hinzufügen/entfernen (negativ = entfernen)
- `CREDITS` — Gold
- `BOOST` / `BOOST_PERM` — Stats
- `CITIZEN_ADD` / `CITIZEN_REMOVE` — Population

---

## Trade System (Vanilla)

- `game/faction/trade/` — Trade Logic
- `GameFactionApi` (Mod SDK) — `stockpile`, `trade.import()`, `trade.export()`
- Resources werden in Faction-Stockpiles gehalten
- Trade Events via `GameEventsApi` triggern

---

## Offene Fragen für CAPTIVE_HUMAN

| Frage | Status |
|-------|--------|
| Wie genau wird Room-Output definiert? (Produktion von CAPTIVE_HUMAN in Human Pens) | **Offen** — Vanilla nutzt WORK+ITEMS für Output, aber "Menschen züchten" ist kein Standard-Output |
| Kann `RACES: [UNDEAD]` wirklich andere Rassen vom Zugriff abhalten? | **Zu testen** — Engine-Check nötig |
| Wie interagiert `MORALE_ADD` mit Undead (die `LIFE_IMMORTAL` haben)? | **Offen** — Morale-System bei Untoten? |
| Trade: Können Orks CAPTIVE_HUMAN an Undead verkaufen wenn `RACES: [UNDEAD]`? | **Kritisch** — Trade prüft vermutlich nur Owner-Race, nicht Resource-Races |