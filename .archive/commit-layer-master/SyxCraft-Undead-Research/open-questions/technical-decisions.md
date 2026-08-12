# Open Questions & Technical Decisions — SyxCraft Undead Overhaul

> **Status:** Research Phase — Entscheidungen noch ausstehend
> **Priorität:** Hoch (blockieren Implementation)

---

## 🔴 Kritische Technische Fragen (Blocker)

### 1. **Race System: Kann `_ignoreVanilla: true` ein komplett neues Race definieren?**
- **Kontext:** Vanilla hat KEIN UNDEAD Race. SyxCraft definiert bereits `UNDEAD.txt` mit `_ignoreVanilla: true`.
- **Risiko:** Engine erwartet bestimmte Hardcoded Races (Human, Orc, etc.) für UI, Savegames, Networking.
- **Test nötig:** Neues Spiel mit UNDEAD starten → Save/Load → Multiplayer (falls relevant).
- **Fallback:** Falls nicht → UNDEAD als "Variant" von Human mit `BOOST` definieren.

### 2. **Resource System: Funktioniert `RACES: [UNDEAD]` als Zugriffskontrolle?**
- **Kontext:** `CAPTIVE_HUMAN` Resource soll **nur** von Undead genutzt/gelagert/gehandelt werden können.
- **Risiko:** Engine prüft `RACES` möglicherweise nur bei **Consumption** (Verbrauch), nicht bei Storage/Trade/UI.
- **Test nötig:** Human Player → Trade mit Undead → CAPTIVE_HUMAN im Lager? UI zeigt Resource?
- **Workaround:** Script `ON_GAME_UPDATE` prüft: `if (player.race != UNDEAD) removeResource(CAPTIVE_HUMAN)`.

### 3. **Room Output: Gibt es natives `OUTPUT` Feld für Rooms?**
- **Kontext:** `HUMAN_PENS` soll `CAPTIVE_HUMAN` **produzieren** (Wachstum), nicht nur verbrauchen.
- **Risiko:** Vanilla Rooms definieren `CONSUMPTION` + `WORK` + `ITEMS` → Output implizit über Items/Work. Kein explizites `OUTPUT` Feld bekannt.
- **Analyse nötig:** Wie produziert `LIVESTOCK_PEN` Tiere? → `data/assets/init/room/LIVESTOCK_PEN.txt` prüfen.
- **Fallback:** Script `ON_GAME_UPDATE` → `if (room.type == HUMAN_PENS) addResource(CAPTIVE_HUMAN, rate)`.

### 4. **Conversion Event: Funktioniert `CITIZEN_ADD` mit `RACE: UNDEAD`?**
- **Kontext:** `UNDEAD_CONVERSION` Event nutzt `{ TYPE: CITIZEN_ADD, RACE: UNDEAD, AMOUNT: ... }`.
- **Risiko:** Engine prüft ggf. nur Vanilla Races. `CITIZEN_ADD` könnte auf Hardcoded Race-Enum prüfen.
- **Test nötig:** Event manuell triggern → Prüfen ob Untoter Citizen erscheint (Sprite, Stats, Name).
- **Fallback:** Script `gameApis.race().getRace("UNDEAD")` → `settlement.addCitizen(race, count)` via Mod SDK.

### 5. **Dual Settlement: Weltkarten-Building als Proxy?**
- **Kontext:** Engine unterstützt **keine** 2. Capital-Map pro Player. Workaround: `WORLD_HUMAN_FARM` Building in Region.
- **Risiko:** 
  - Keine eigene Map für "Human Farm" → Kein Room-Building, keine Micro-Management.
  - Script muss `WORLD_HUMAN_FARM` Level/Production tracken → Virtual State.
- **Entscheidung:** Akzeptabel für MVP? Oder Mod SDK `GameSaveApi` für echte 2. Settlement-Map?
- **Mod SDK Check:** `GameSaveApi` hat `onGameSaved/Loaded` → Custom Data persistierbar. Aber **keine** API für 2. Capital-Map.

### 6. **Mod SDK Availability: Ist `sos-mod-sdk` auf Maven Central / GitHub Packages?**
- **Kontext:** `pom.xml` profile `mod-sdk` referenziert `io.github.4rg0n:sos-mod-sdk:0.1.5`.
- **Risiko:** Repo nicht öffentlich → Build schlägt fehl.
- **Action:** `gh api repos/4rg0n/Songs-of-Syx-Mod-SDK` prüfen oder 4rg0n kontaktieren.
- **Fallback:** Ohne Mod SDK → Nur Vanilla Script API (`SCRIPT` Interface) + Reflection.

### 7. **Event System: Kann `SELECTION.REGIONS` Weltkarten-Regionen für Building-Placement nutzen?**
- **Kontext:** `FOUND_HUMAN_FARM` Event soll Region auswählen → `SETTLEMENT_ADD` Building platzieren.
- **Risiko:** `SETTLEMENT_ADD` erwartet vermutlich Capital-Map Building, nicht Worldmap Building.
- **Test nötig:** Event mit `SELECTION.REGIONS` + `SETTLEMENT_ADD: WORLD_HUMAN_FARM` triggern.
- **Alternative:** Script `GameFactionApi` / `GameEventsApi` → Programmatisch Worldmap Building platzieren.

---

## 🟡 Wichtige Design-Fragen (Balance & UX)

### 8. **CAPTIVE_HUMAN Growth Rate Balancing**
| Parameter | Vorschlag | Begründung |
|-----------|-----------|------------|
| `HUMAN_PENS` Base Rate | 2% pro Worker/Tag | 20 Worker = 4 Captives/Tag |
| `WORLD_HUMAN_FARM` Base | 5/Tag (Level 1) | Passive Income, skaliert mit Level |
| Conversion Cost | 5 Captive + 1 Essence | Meaningful Decision |
| Conversion Cooldown | 30 Tage | Verhindert Spam |
| Max Captives Storage | 500 (Stack 10) | Lagerung begrenzt |

**Frage:** Sind diese Zahlen "fun" oder "grindy"? → Playtest nötig.

### 9. **Orc Slavery: Automatisch vs. Event-gesteuert?**
- **Option A (Automatisch):** Script prüft jede Orc-Faction pro Tick → Auto-Raid wenn `ORC_SLAVERY` Tech + Mensch in Reichweite.
- **Option B (Event-gesteuert):** `ORC_SLAVE_RAID` Event spawnt natürlich → Spieler entscheidet.
- **Empfehlung:** **B** für Player Agency, **A** für NPC Orcs (Script-seitig).

### 10. **Undead Immigration: Wie kommen neue Untote ins Spiel?**
- **Nur Conversion** (Human → Undead) → Begrenzt durch Human Population.
- **Keine natürliche Immigration** (`CIVIC_IMMIGRATION>MUL: 0.0`).
- **Problem:** Mid-Game → Human Population agotiert → Undead stagnieren.
- **Lösung:** 
  - `NECROPOLIS` Room generiert langsam "Free Undead" (ohne Captive Cost).
  - Oder: `WORLD_HUMAN_FARM` Level 5 unlockt "Raise Dead" Event (Battlefield → Undead).

### 11. **Night Elf / Alliance Integration?**
- **SyxCraft hat** `NIGHT_ELF` Race + `ALLIANCE_COMMAND` Tech.
- **Undead = Horde** (mit Orcs).
- **Frage:** Braucht Undead spezifische Anti-Alliance Techs? `HORDE_WARFARE` Tech Tree?

---

## 🟢 Integration & Workflow Fragen

### 12. **Maven Build: `local.properties` für Game Paths?**
- **Aktuell:** `pom.xml` hat Hardcoded Defaults (`${user.home}/.steam/steam/...`).
- **Best Practice:** `local.properties` (gitignored) mit `game.install.directory`, `game.workshop.directory`.
- **Action:** `local.properties.example` committen, `.gitignore` ergänzen.

### 13. **Validator (SyxCode) Schema für neue Types?**
- **Neue Files:** `CAPTIVE_HUMAN.txt`, `HUMAN_PENS.txt`, `NECROPOLIS.txt`, `WORLD_HUMAN_FARM.txt`, Event Files.
- **Validator** prüft gegen Schemas → Muss erweitert werden.
- **Action:** JSON Schemas in `tools/schemas/` für `resource-supply`, `room-custom`, `world-building`, `event-custom` anlegen.

### 14. **Workshop Upload: `_src` Ordner Pflicht?**
- **SyxCraft README:** "Source JAR für Workshop Transparenz".
- **Action:** `maven-source-plugin` konfiguriert → `target/out/.../script/_src/syxcraft-undead-sources.jar`.
- **Test:** Workshop Upload via Mod Uploader Tool prüfen.

### 15. **Multiplayer Compatibility?**
- **Songs of Syx** hat Multiplayer (Coop?).
- **Script Mods** syncen State via Savegame → Deterministisch?
- **Risk:** `ON_GAME_UPDATE` Logic muss **deterministisch** sein (kein `Math.random()`, keine System-Time).
- **Action:** Alle Random-Entscheidungen über Game RNG (Seed-basiert) oder Event-Choices.

### 16. **Determinism & Save/Load**
- Custom State in `onGameSaved/Loaded` → Muss exakt same Order beim Schreiben/Lesen!
- `FilePutter`/`FileGetter` sind **position-basiert** → Reihenfolge kritisch.
- Test: Save → Load → Save → Load → State identisch?

---

## 📋 Entscheidungs-Template

Für jede Frage: **Format für User-Entscheidung**

```
## #N: Frage?
| Option | Was passiert? (Impact, 1-2 Zeilen) |
|--------|-------------------------------------|
| A | ... |
| B | ... |
| C | ... |
**Empfehlung:** X — weil ...
```

**Deine Wahl:** `1=A, 2=B, 3=C` oder **„Alle Empfehlungen übernehmen“**