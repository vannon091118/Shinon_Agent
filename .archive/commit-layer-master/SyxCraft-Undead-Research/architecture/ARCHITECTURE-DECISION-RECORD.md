# ARCHITECTURE DECISION RECORD — SyxCraft Four-Race Overhaul

> **Project:** SyxCraft — WoW-inspired Overhaul for Songs of Syx V71.44
> **Date:** 2026-07-14
> **Phase:** System Architecture Research Complete
> **Status:** Ready for Implementation Planning

---

## EXECUTIVE SUMMARY

This document records all architectural decisions for the SyxCraft mod based on comprehensive Research Phases 1-2 and System Architecture Analysis (Blocks A, B, C).

**Key Principle:** Build on V71 native systems (Laws, Slavery, Diplomacy, Events) — extend only where engine gaps exist.

---

## DECISIONS MADE

### D1: Script Architecture — **Option C (Hybrid Core + Race Modules)**
**Decision:** Single Mod, Single Script Entry Point (`SyxCraftCoreScript`), Race Logic in isolated Modules (`UndeadModule`, `OrcModule`, `HumanModule`, `NightElfModule`) communicating via typed `CoreBus`.

**Rationale:**
- Single Workshop Upload (1 Mod, 1 JAR, 1 Version)
- No Load Order Issues
- Agent Parallel Work via Package Isolation
- Cross-Race Communication via Core Bus (Type-Safe, No Race Conditions)
- Core State Manager for Unified Save/Load

**Structure:**
```
com.syxcraft.core       → Architecture Agent
com.syxcraft.undead     → Undead Agent
com.syxcraft.orc        → Orc Agent
com.syxcraft.human      → Human Agent
com.syxcraft.nightelf   → Night Elf Agent
```

---

### D2: Mod Structure — **Single Mod (Option A)**
**Decision:** `mods/SyxCraft/V71/` contains ALL race data files and ONE script JAR.

**Rationale:**
- Cross-Race Features (Slave Trade, Diplomacy, War) work natively without Mod Dependencies
- No Circular Dependency Hell (Orc needs Undead, Undead needs Orc)
- Single Build, Single Test, Single Upload

---

### D3: Slavery System — **V71 Law-Based Population Class (Native)**
**Decision:** Remove `CAPTIVE_HUMAN` resource entirely. Use native `PopulationClass.SLAVE` (Race: HUMAN) + V71 Slavery Laws.

**Migration:**
| V70/Concept | V71 Implementation |
|-------------|-------------------|
| `CAPTIVE_HUMAN` Resource | `CLASS_SLAVE, RACE: HUMAN` Population |
| `HUMAN_PENS` Room | Removed — Slave production via Raid Events |
| `NECROPOLIS` Room | `POPULATION_CLASS_CHANGE: FROM=SLAVE TO=CITIZEN RACE=UNDEAD` |
| Orc Slave Trade | Diplomatic Action `REQUEST_SLAVE_TRADE` + `POPULATION_CLASS_TRANSFER` |

**Laws Required:**
- `UNDEAD_SLAVERY` (Criminal, Tier 1) — Enables slave ownership
- `UNDEAD_CONVERSION` (Criminal, Tier 2, req: UNDEAD_SLAVERY) — Enables conversion
- `ORC_SLAVERY` (Criminal, Tier 1) — Enables Orc raids
- `HUMAN_FARM_MANAGEMENT` (Civic, Tier 2) — Unlocks World Building

---

### D4: Dual Settlement — **Region-Based Human Village + Core State Manager**
**Decision:** Human Village = Adjacent Region with `HUMAN_VILLAGE` flag. NOT a native second Settlement.

**Implementation:**
- Region Population holds Human Citizens
- Region Stockpile holds Human Resources
- Core State Manager tracks: Region IDs, Population, Geist, Gates
- Gate Manager scans Human Village Buildings each tick
- No Resource Transfer between settlements (Core Concept)

**Gate System (Building in A → Function in B):**
| Gate | Trigger Building (Human Village) | Unlocks (Undead Capital) | Mechanism |
|------|--------------------------------|-------------------------|-----------|
| MILITARY | BARRACKS | Undead Military Buildings | CoreState Boost Flag |
| CONVERSION | GRANARY | UNDEAD_CONVERSION Event | CoreState Boost Flag |
| GEIST_DECAY | WATCHTOWER | Geist Decay -20% | CoreState Boost Flag |

---

### D5: Geist System — **Custom Mood via Core State Manager**
**Decision:** Geist = Custom State (0.0 = full control, 1.0 = rebellion). Replaces Loyalty for Human Village.

**Components:**
- `GhostState` — Control/Fear/Conditioning levels
- `GhostManager` — Updates from BOTH settlements' buildings
- Events at thresholds: 0.7 (Rebellion), 0.9 (Critical)
- Persisted via Core State Manager (FilePutter/FileGetter)

---

### D6: Orc-Undead Slave Pipeline — **Native Events + Diplomatic Actions**
**Decision:** Full pipeline using V71 native systems.

```
Orc Raid Event → POPULATION_CLASS_ADD: SLAVE(HUMAN) → Orc Stockpile
    ↓ Diplomatic Action REQUEST_SLAVE_TRADE (requires PACT, ORC_SLAVERY, UNDEAD_SLAVERY laws)
POPULATION_CLASS_TRANSFER → Undead Stockpile: SLAVE(HUMAN)
    ↓ UNDEAD_CONVERSION Event (requires UNDEAD_CONVERSION law)
POPULATION_CLASS_CHANGE: SLAVE→CITIZEN RACE=UNDEAD → Undead Citizen +1
```

---

### D7: Alliance vs Horde — **FactionGroup Enum + Custom War State**
**Decision:** No native Faction Group. Implement `FactionGroup { ALLIANCE, HORDE }` in Core State.

**War System:**
- War Score: Custom Core State (Battle wins, Region capture, Conversions)
- Territorial Control: Region Flags in Core State
- Diplomatic Stances driven by Race Relations + Laws

---

### D8: Shared Narrative Events — **Core Bus + Core State Manager**
**Decision:** Data Events for Broadcast, Core State for Shared Progress, Core Bus for Coordination.

**Patterns:**
- Broadcast: `FACTIONS` filter in Event Selection
- Progress: Boost Flags + Core State counters
- Coordination: Core Bus Events (`NarrativeEvent`)

---

### D9: Validator Schemas — **4 JSON Schemas for New File Types**
**Decision:** Pre-commit validation via local hooks (not CI).

**Schemas Created:**
- `resource-supply.schema.json` — CAPTIVE_HUMAN, BONE, ESSENCE, MOONWATER
- `room-custom.schema.json` — HUMAN_PENS, NECROPOLIS, MOONWELL, DRUIDIC_GROVE
- `event-custom.schema.json` — UNDEAD_CONVERSION, INDEPENDENCE_ATTEMPT, ORC_SLAVE_TRADE
- `world-building.schema.json` — WORLD_HUMAN_FARM, MOONWELL, SENTINEL_OUTPOST

---

### D10: Build & Deploy — **Maven + Local Hooks (No CI/CD)**
**Decision:** `mvn clean package -Pmod-sdk` + local pre-commit hooks for validation.

**Hooks:**
- `pre-commit`: JSON Schema validation, Version Sync, Asset Naming
- `post-commit`: Signature Update, Changelog Reminder
- `pre-push`: Full Build + Test Run

---

## OPEN QUESTIONS — REQUIRING FELIX DECISION

| # | Question | Options | Priority |
|---|----------|---------|----------|
| **Q1** | **_ignoreVanilla: true on Race Slots** — Test confirms it works? | A) Yes, full override / B) Partial / C) Crashes | **CRITICAL** — Test first |
| **Q2** | **Native Dual Settlement** — Any V71 API for multi-settlement? | A) Yes / B) No (use Region workaround) | **CRITICAL** — Architecture pivot |
| **Q3** | **Population Class Transfer** — `POPULATION_CLASS_TRANSFER` cross-faction works? | A) Yes / B) No (Script bridge needed) | **CRITICAL** — Pipeline blocker |
| **Q4** | **Mod SDK Availability** — `io.github.4rg0n:sos-mod-sdk:0.1.5` on GitHub Packages? | A) Public / B) Private (needs token) / C) Local only | **HIGH** — Build blocker |
| **Q5** | **Diplomatic Action Data Files** — Custom actions loadable via `_ignoreVanilla`? | A) Yes / B) No (Java only) | **HIGH** — Slave Trade design |

---

## IMPLEMENTATION ORDER (Phase 3)

### Sprint 1: Foundation (Week 1-2)
1. **Maven Module Setup** — `syxcraft` with `mod-sdk` profile
2. **Core Script Skeleton** — `SyxCraftCoreScript`, `CoreBus`, `CoreStateManager`
3. **Validator Schemas** — Add to `tools/schemas/`, configure pre-commit hook
4. **Test Race Override** — `_ignoreVanilla: true` on UNDEAD + Human

### Sprint 2: Undead MVP (Week 2-4)
1. **Data Files** — UNDEAD.txt, SLAVERY Laws, NECROMANCY Tech, Events
2. **UndeadModule** — GhostManager, ConversionManager, GateManager, HumanFarmManager
3. **Dual Settlement** — Region initialization, Human Village population
4. **Build + Smoke Test** — 100 Days test run

### Sprint 3: Orc Integration (Week 4-5)
1. **OrcModule** — RaidManager, SlaveTradeManager
2. **Diplomatic Action** — REQUEST_SLAVE_TRADE
3. **Pipeline Test** — Orc Raid → Trade → Undead Conversion

### Sprint 4: Human + Night Elf (Week 5-7)
1. **HumanModule** — ImmigrationManager
2. **NightElfModule** — StealthManager, MoonwellManager
3. **Alliance/Horde** — FactionGroup, War State, Conflict Events

### Sprint 5: Polish & Release (Week 7-8)
1. **Balance Playtest** — 3-5 Players, 100 Days each
2. **UI/Notifications** — Farm Panel, Geist Tooltip, Gate Notifications
3. **Workshop Upload** — _src folder, Version Sync, Changelog

---

## RISK REGISTER

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `_ignoreVanilla` fails on Race | High | Blocker | Test Day 1, fallback: extend vanilla |
| `POPULATION_CLASS_TRANSFER` broken | Medium | Blocker | Script bridge fallback |
| Mod SDK not available | Low | High | Local JAR install |
| Cross-Settlement State loss on Save | Medium | High | CoreStateManager extensive testing |
| Agent Merge Conflicts | Low | Medium | Strict Package Ownership |

---

## SUCCESS CRITERIA (Phase 1 Complete)

```
✅ New Game → Undead Selected
✅ Two Settlements: Undead Capital (>10 pop) + Human Village (10 pop, adjacent)
✅ Geist UI visible in Human Village panel
✅ 30 Days: Geist decays without control buildings
✅ Build Watchtower in Human Village → Geist decay reduces
✅ Build Barracks in Human Village → Undead Military Buildings unlock
✅ Build Granary in Human Village → UNDEAD_CONVERSION Event available
✅ OGREIC_TRIBUTE Event → CAPTIVE_HUMAN (SLAVE) in stockpile
✅ UNDEAD_CONVERSION Event → SLAVE(HUMAN) → CITIZEN(UNDEAD)
✅ Save → Load → State identical (Geist, Gates, Stockpiles, Population)
✅ 100 Days playable without crash
```

---

## FILES CREATED (Reference)

### Research Phase 1-2
```
SyxCraft-Undead-Research/
├── vanilla-reference/ (5 files)
├── sdk-reference/ (2 files)
├── mod-structure-concept/ (1 file)
├── data-examples/ (2 files)
├── open-questions/ (3 files)
├── research-notes/ (1 file)
├── syxcraft-current-state/ (3 files)
├── phase-2/ (4 JSON schemas)
├── building-gate-architecture.md
├── ghost-system-analysis.md
├── orc-slave-system.md
├── v71-impact-analysis.md
├── java-agent-architecture-spec.md
├── interdependency-matrix.md
├── Night_Elf_Mechanics_Spec.md
└── README.md
```

### Architecture Research (This Phase)
```
SyxCraft-Undead-Research/architecture/
├── A1-slavery-system.md
├── A2-law-system.md
├── A3-diplomatic-actions.md
├── A4-battle-raid-system.md
├── A5-race-preference-system.md
├── A6-region-worldmap-system.md
├── A7-immigration-population-flow.md
├── B1-multi-race-script-architecture.md
├── B2-cross-settlement-communication.md
├── B3-gate-system-engine-analysis.md
├── B4-mod-module-structure.md
├── C1-orc-undead-slave-pipeline.md
├── C2-alliance-horde-conflict-system.md
├── C3-shared-narrative-events.md
└── ARCHITECTURE-DECISION-RECORD.md  ← THIS FILE
```

---

## NEXT ACTION

**Felix entscheidet Q1-Q5 oben.** Dann Sprint 1 Start.

*End of Architecture Decision Record*