# Open Questions — Technical Decisions Required

> **Format:** Für jede Frage → Optionen → Impact → Empfehlung
> **Entscheidung:** User wählt `1=A, 2=B, 3=C` oder `"Alle Empfehlungen übernehmen"`

---

## 1. Race System: Funktioniert `_ignoreVanilla: true` für komplett neues UNDEAD Race?

| Option | Was passiert? |
|--------|---------------|
| **A: Ja, Engine akzeptiert beliebig viele Races** | UNDEAD Race wird wie Vanilla Races behandelt (UI, Savegames, Multiplayer) |
| **B: Teilweise — UI/Selection geht, aber Savegame/MP Probleme** | Singleplayer OK, Multiplayer Desync oder Save-Corruption möglich |
| **C: Nein — Engine hardcoded Vanilla Races** | UNDEAD muss als "Variant" von Human definiert werden (BOOST nur) |

**Empfehlung:** **A testen** — SyxCraft hat bereits `UNDEAD.txt` mit `_ignoreVanilla: true` definiert. **Test:** Neues Spiel als UNDEAD → Save/Load → Multiplayer (falls relevant).

---

## 2. Resource Access Control: Funktioniert `RACES: [UNDEAD]` als Zugriffskontrolle?

| Option | Was passiert? |
|--------|---------------|
| **A: Ja, Engine prüft RACES bei Storage/Trade/UI** | Nur Undead können CAPTIVE_HUMAN lagern/handeln/sehen |
| **B: Nur bei Consumption (Verbrauch)** | Andere Races können Resource handeln/lagern, aber nicht verbrauchen |
| **C: Keine Enforcement — nur Metadaten** | Jeder kann Resource nutzen, `RACES` ist nur Info |

**Empfehlung:** **B/C annehmen, Script-seitig enforce** — `ON_GAME_UPDATE` prüft: `if (player.race != UNDEAD) removeResource(CAPTIVE_HUMAN)`.

---

## 3. Room Output: Gibt es natives `OUTPUT` Feld für Rooms?

| Option | Was passiert? |
|--------|---------------|
| **A: Ja, `OUTPUT: { RESOURCE: X, BASE_RATE: Y }` wird unterstützt** | HUMAN_PENS produziert CAPTIVE_HUMAN nativ via Data File |
| **B: Nein, Output nur implizit via WORK + ITEMS** | Production muss via Script `ON_GAME_UPDATE` implementiert werden |
| **C: Teilweise — nur für bestimmte Room Types (Farms, Mines)** | Nur Vanilla-definierte Room Types haben Output |

**Empfehlung:** **B annehmen, Script implementieren** — `LIVESTOCK_PEN.txt` prüfen wie Vanilla Tier-Produktion macht. Script: `addCaptiveHumans(rate * workers * dt)`.

---

## 4. Conversion Event: Funktioniert `CITIZEN_ADD` mit `RACE: UNDEAD`?

| Option | Was passiert? |
|--------|---------------|
| **A: Ja, Engine erstellt UNDEAD Citizen mit korrekten Stats/Sprite** | Event `UNDEAD_CONVERSION` funktioniert nativ |
| **B: Citizen wird erstellt, aber Sprite/Stats fehlen (Vanilla Race Enum)** | Citizen existiert aber ist "broken" — Fix via Script nötig |
| **C: Nein, `CITIZEN_ADD` akzeptiert nur Vanilla Races** | Conversion muss via Script `settlement.addCitizen(race, count)` |

**Empfehlung:** **Testen** — Event triggern → Citizen prüfen. Falls B/C: Script `ConversionManager.convert(captives, essence)`.

---

## 5. Dual Settlement: Worldmap Building als Proxy für 2. Settlement?

| Option | Was passiert? |
|--------|---------------|
| **A: Ja, `WORLD_HUMAN_FARM` Building in Region = funktionale 2. Economy** | Passive Production, Events, Upgrades — volle Feature Parity |
| **B: Teilweise — Production OK, aber keine Map, keine Rooms, kein Micro** | "Virtual Settlement" — gut für Passive Income, schlecht für Micro-Management |
| **C: Nein — Worldmap Buildings können keine Resources in Player Stockpile legen** | Workaround: Script `ON_GAME_UPDATE` liest Building Level → `addResource()` |

**Empfehlung:** **A/B Hybrid** — Worldmap Building für Passive Production + Script für Stockpile Transfer + Events für "Farm Management UI".

---

## 6. Mod SDK Availability: Ist `sos-mod-sdk` auf Maven/GitHub Packages verfügbar?

| Option | Was passiert? |
|--------|---------------|
| **A: Ja, öffentlich auf GitHub Packages / Maven Central** | `-Pmod-sdk` Profile funktioniert out of the box |
| **B: Ja, aber privat (GitHub Packages mit Auth)** | Build braucht `GITHUB_TOKEN` mit `read:packages` |
| **C: Nein, nicht veröffentlicht** | Mod SDK nicht nutzbar → Vanilla Script Only + Reflection |

**Action Required:** Prüfen `gh api repos/4rg0n/Songs-of-Syx-Mod-SDK` oder 4rg0n kontaktieren.

**Empfehlung:** **Vanilla Script + Reflection als Baseline** — Mod SDK nur für "Nice to Have" (UI Notifications, Race Liking Runtime).

---

## 7. Event System: Kann `SELECTION.REGIONS` Worldmap-Regionen für Building Placement nutzen?

| Option | Was passiert? |
|--------|---------------|
| **A: Ja, `SETTLEMENT_ADD: WORLD_HUMAN_FARM` platziert Building in gewählter Region** | Event-basiertes Farm-Placement funktioniert nativ |
| **B: `SETTLEMENT_ADD` nur für Capital-Map Buildings** | Worldmap Building Placement geht nur via Script/API |
| **C: Event Selection → Script Callback → Programmatische Placement** | Hybrid: Event für Player Choice, Script für Execution |

**Empfehlung:** **C** — Event triggert `FOUND_HUMAN_FARM` → Script `HumanFarmManager.establishFarm(regionId)` platziert Building programmatisch.

---

## 8. Orc Slavery: Automatisch (Script) vs Event-gesteuert?

| Option | Was passiert? |
|--------|---------------|
| **A: Automatisch — Script prüft jede Orc Faction pro Tick → Auto-Raid** | Hohe Frequenz, wenig Player Agency, Performance Cost |
| **B: Event-gesteuert — `ORC_SLAVE_RAID` Event spawnt natürlich** | Natürlicher Rhythmus, Player kann reagieren (Diplomatie, Defense) |
| **C: Hybrid — NPC Orcs Auto, Player Orcs Event** | NPCs aggressiv, Player Orcs brauchen Decision |

**Empfehlung:** **B** — Natürlicher Gameflow, besser für Balance.

---

## 9. Undead Immigration: Wie kommen neue Untote ins Spiel?

| Option | Was passiert? |
|--------|---------------|
| **A: Nur Conversion (Human → Undead)** | Begrenzt durch Human Population — Stagnation Mid-Game |
| **B: Conversion + `NECROPOLIS` generiert "Free Undead" langsam** | Steady Trickle unabhängig von Captives |
| **C: Conversion + `WORLD_HUMAN_FARM` Level 5 unlockt "Raise Dead" Event (Battlefield → Undead)** | Late Game Scaling via Warfare |

**Empfehlung:** **B + C** — `NECROPOLIS` Room: `FREE_UNDEAD_RATE: 0.1/Tag` + Level 5 Farm: `RAISE_DEAD` Event.

---

## 10. Multiplayer Support: Script Mods kompatibel?

| Option | Was passiert? |
|--------|---------------|
| **A: Ja, deterministische Scripts syncen via Savegame** | MP funktioniert out of the box |
| **B: Nur wenn alle Clients exakt gleiche Mod Version + Load Order** | Fragil, Desync Risk |
| **C: Nein, Script Mods brechen MP** | Singleplayer Only |

**Empfehlung:** **Singleplayer Only für MVP** — MP Support als Post-1.0 Feature. Dokumentieren: "MP nicht getestet, nicht unterstützt".

---

## 11. Determinism & Save/Load: Custom State Serialization

| Option | Was passiert? |
|--------|---------------|
| **A: `FilePutter/FileGetter` Position-basiert — Reihenfolge kritisch** | `putter.mark(1).chars("KEY").chars(val)` → `getter.check().chars("KEY")` muss exakt gleiche Reihenfolge |
| **B: JSON/Map-basiert via Mod SDK `PropertiesStore`** | Key-Value, reihenfolgenunabhängig, typsicher |
| **C: Beides gemischt — Vanilla Script für Save/Load, Mod SDK für Config** | Pragmatisch |

**Empfehlung:** **A für Vanilla Script** — strikte Reihenfolge dokumentieren. **B für Config** via `PropertiesStore`.

---

## 12. Balance Knobs: Welche Werte sind Playtest-Kandidaten?

| Knob | Current | Range | Effect |
|------|---------|-------|--------|
| `HUMAN_PENS.BASE_RATE` | 0.02 | 0.01–0.05 | Farm Output linear |
| `WORLD_HUMAN_FARM.LEVEL_MULT` | 1.5 | 1.2–2.0 | Farm Scaling exponentiell |
| `CONVERSION.CAPTIVE_COST` | 5 | 3–10 | Conversion Speed |
| `CONVERSION.COOLDOWN_DAYS` | 30 | 15–90 | Conversion Frequency |
| `UNDEAD.ADULT_AT_DAY` | 60 | 20–80 | Worker Readiness |
| `UNDEAD.WORK_SPEED` | 0.9 | 0.7–1.1 | Economic Output |
| `UNDEAD.ESSENCE_MAINTENANCE` | 0.0 | 0.0–0.2 | Ongoing Cost |
| `ORC_SLAVE_RAID.BASE_CAPTIVES` | 20 | 10–40 | Trade Supply |
| `CAPTIVE_HUMAN.STACK_SIZE` | 10 | 5–50 | Storage Granularity |

---

## Entscheidungs-Template

```
## Meine Entscheidungen:
1=A, 2=B, 3=B, 4=Testen, 5=C, 6=Vanilla Script, 7=C, 8=B, 9=B+C, 10=Singleplayer, 11=A, 12=Alle oben

## Oder: "Alle Empfehlungen übernehmen"
```

**Nächster Schritt:** Nach Entscheidung → `/execution` triggern mit komplettem Konzept.