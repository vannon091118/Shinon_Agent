# Research Notes — SyxCraft Undead Overhaul

## Overview

This directory contains deep-dive technical analysis for implementing the WoW-inspired Undead faction in Songs of Syx via the SyxCraft mod framework.

---

## Completed Research Areas

| Document | Topic | Status |
|----------|-------|--------|
| `vanilla-reference/vanilla-data-structures.md` | Vanilla Race, Resource, Event, Tech, Script Systems | ✅ Complete |
| `vanilla-reference/tech-system.md` | Tech Tree Structure, Costs, Unlocks, Undead Integration | ✅ Complete |
| `sdk-reference/sdk-api-reference.md` | Argon Mod SDK V0 Full API Reference | ✅ Complete |
| `sdk-reference/sdk-capabilities.md` | Capability Matrix, Vanilla vs SDK, Build Setup | ✅ Complete |
| `mod-structure-concept/mod-structure.md` | Maven Project, Data Files, Build/Deploy, Workshop | ✅ Complete |
| `data-examples/undead-data-files.md` | Complete .txt Data Files for all Undead Objects | ✅ Complete |
| `research-notes/dual-settlement-workaround.md` | Worldmap Building + Script Hybrid for 2nd Settlement | ✅ Complete |
| `open-questions/technical-decisions.md` | 9 Critical Technical Questions with Options | ✅ Complete |
| `open-questions/balance-questions.md` | Economy Formulas, Growth Models, Playtest Scenarios | ✅ Complete |

---

## Key Technical Findings

### 1. **Engine Limitations**
- **No native dual settlement** — Engine hardcoded single Capital per Player
- **Workaround:** Worldmap Building (`WORLD_HUMAN_FARM`) + Script State = Functional Proxy
- **Save/Load:** Custom state via `FilePutter/FileGetter` in `onGameSaved/Loaded`

### 2. **Mod SDK V0 (Argon/4rg0n) — Available Capabilities**
| API | Status | Critical For Undead |
|-----|--------|---------------------|
| `GameEventsApi` | ✅ Read/Write Events | Conversion Events, Farm Events |
| `GameRaceApi.setLiking()` | ✅ Runtime Race Relations | Human/Undead/Orc Dynamics |
| `GameFactionApi` | ✅ Trade, Stockpiles, Diplomacy | Orc Slave Trade |
| `GameSaveApi` | ✅ Custom State Persistence | Farm State, Cooldowns |
| `GameUiApi` | ✅ Notifications, Tooltips | Farm Management UI |
| `GameRoomsApi` | ✅ Read Room Definitions | Validation |

**Build Requirement:** GitHub Packages auth (`GITHUB_TOKEN`) for `io.github.4rg0n:sos-mod-sdk`

### 3. **Vanilla Script System — Sufficient for MVP**
- `SCRIPT` + `SCRIPT_INSTANCE` interfaces cover all lifecycle hooks
- `ON_GAME_UPDATE(dt)` = Main logic loop
- `FilePutter/FileGetter` = Custom Save Data
- **Reflection** needed for: `GameEventsApi` (read), `GameFactionApi` (trade)

### 4. **Data Structure Compatibility**
- SyxCraft V70 already defines `UNDEAD` race with `_ignoreVanilla: true`
- Missing: `CAPTIVE_HUMAN` resource, `HUMAN_PENS`/`NECROPOLIS` rooms, `NECROMANCY_HUMAN_FARM` tech, Events
- **Format:** Brace-style key-value (not JSON) — `_ignoreVanilla: true` overrides Vanilla

---

## Implementation Priority

### Phase 1: Foundation (Week 1-2)
- [ ] Maven Module `syxcraft-undead` mit `mod-sdk` Profile
- [ ] Data Files: `UNDEAD.txt`, `CAPTIVE_HUMAN.txt`, `NECROMANCY_HUMAN_FARM.txt`
- [ ] `UndeadScript.java` Skeleton + State Manager
- [ ] Validator Schemas für neue File Types

### Phase 2: Core Mechanics (Week 2-3)
- [ ] `HumanFarmManager` — Worldmap Building Logic + Production
- [ ] `ConversionManager` — Human→Undead Event + Script Fallback
- [ ] `OrcTradeManager` — NPC Orc Raids + Player Trade
- [ ] Custom Events: `FOUND_HUMAN_FARM`, `UNDEAD_CONVERSION`

### Phase 3: Integration & Polish (Week 3-4)
- [ ] UI: Farm Panel, Captive Human Tooltip, Notifications
- [ ] Save/Load State Persistence
- [ ] Tech Tree Integration (`UNDEAD_NECROPOLIS_MASTERY`, `DARK_RITUALS`)
- [ ] Race Relations: `setLiking(UNDEAD, HUMAN, 0.3)`, etc.

### Phase 4: Balance & Release (Week 4-5)
- [ ] Playtest: 3-5 Spieler, 100 Days each
- [ ] Balance Knobs: Farm Output, Conversion Cost, Cooldowns
- [ ] Workshop Upload: `_src` folder, Version Sync
- [ ] Documentation: README, CHANGELOG

---

## Critical Open Questions (Need Decisions)

| # | Question | Options | Impact |
|---|----------|---------|--------|
| 1 | Race System: `_ignoreVanilla` works? | A: Full support / B: Partial / C: No | **Blocker** — Test first |
| 2 | Resource `RACES: [UNDEAD]` enforced? | A: Full / B: Consumption only / C: Metadata | Design — Script fallback ready |
| 3 | Room `OUTPUT` field exists? | A: Yes / B: No (Script only) | Implementation path |
| 4 | `CITIZEN_ADD: RACE: UNDEAD` works? | A: Full / B: Broken / C: No | Conversion mechanic |
| 5 | Worldmap Building → Player Stockpile? | A: Native / B: Script bridge | Farm production |
| 6 | Mod SDK publicly available? | A: Yes / B: Private / C: No | Build config |
| 7 | `SELECTION.REGIONS` for Worldmap Building? | A: Native / B: Capital only / C: Hybrid | Farm placement UX |
| 8 | Orc Slavery: Auto vs Event? | A: Auto / B: Event / C: Hybrid | Gameflow |
| 9 | Undead Immigration Source? | A: Conversion only / B: +Necropolis / C: +Events | Late game |

---

## File Inventory

```
SyxCraft-Undead-Research/
├── README.md                          # This file
├── vanilla-reference/
│   └── vanilla-data-structures.md     # Vanilla Race, Resource, Event, Tech, Script
│   └── tech-system.md                 # Tech Tree Details
├── sdk-reference/
│   ├── sdk-api-reference.md           # Full Mod SDK API
│   └── sdk-capabilities.md            # Matrix, Build, Decision
├── mod-structure-concept/
│   └── mod-structure.md               # Maven, Data, Build, Deploy
├── data-examples/
│   └── undead-data-files.md           # All .txt Files Complete
├── open-questions/
│   ├── technical-decisions.md         # 9 Critical Decisions
│   ├── balance-questions.md           # Economy, Growth, Playtest
│   └── decision-template.md           # Decision Format
├── research-notes/
│   └── dual-settlement-workaround.md  # Worldmap + Script Hybrid
└── syxcraft-current-state/
    ├── existing-races.md              # SyxCraft V70 Races
    ├── existing-techs.md              # SyxCraft V70 Techs
    └── gaps-analysis.md               # What's Missing for Undead
```

---

## Next Actions

1. **User Review** — Prüfe `open-questions/technical-decisions.md` → Entscheidungen treffen
2. **Test Race System** — Quick test: `UNDEAD` Race in neuem Spiel → Save/Load
3. **Mod SDK Auth** — GitHub Token für `4rg0n/Songs-of-Syx-Mod-SDK` prüfen
3. **Start Implementation** — Maven Modul + Data Files + Script Skeleton