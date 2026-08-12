# E — Implementation Sequence & Lessons Learned

> **Quelle:** Rekonstruktion aus Research Phase 1+2, Architektur-Blöcke A-C, V71 JAR-Analyse
> **Prinzip:** NUR öffentlich dokumentierte Change-Notes/Changelog-Logik — KEIN Code/Asset aus fremden Mods
> **Lizenz-Grenze:** Explizit — keine Code-Inspektion fremder Mods, nur Engine-Analyse + eigene Design-Entscheidungen

---

## CHRONOLOGISCHE TIMELINE — SYXCRAFT NEUAUFBAU

### PHASE 0 — KONZEPT-VALIDIERUNG (Research Phase 1)
**Datum:** 2026-07-13 bis 14
**Trigger:** Entscheidung v0.0.48 verwerfen, konzeptgetriebener Neuaufbau

| Entscheidung | Begründung | Lehre für uns |
|-------------|-----------|---------------|
| v0.0.48 verworfen | "Feature-Silo ohne Interdependenz", Night Elf = Stat-Clone | **Erst Interdependenz-Matrix, dann Race-Design** |
| 4-Rassen-Framework | Allianz/Horde mechanisch sinnvoll | **FactionGroup als Architektur-Primitiv** |
| Undead als First-Class-Citizen | Dual-City + Geist + Gate = Testbarer MVP | **Scope auf 1 Rasse MVP reduzieren, dann skalieren** |
| Java als Agent-Einstieg | Nicht für Komplexität, sondern für Engine-Zugriff | **Java nur dort wo Engine keine Data-Lösung hat** |

**LEHRE:** Concept-First spart 80% Refactor-Zeit. "Was nicht im Konzept steht, wird nicht gebaut."

---

### PHASE 1 — ENGINE-DEEP-DIVE & V71 MIGRATION (Research Phase 2 + Architecture Block A)
**Datum:** 2026-07-14 (parallel)
**Trigger:** V71 "Reign of Terror" released — Slavery, Laws, Population Growth changed

| Analysierte Engine-Systeme | Kritische Findings | Migration-Impact |
|---------------------------|-------------------|------------------|
| **Slavery System** | V71: `PopulationClass.SLAVE` statt Resource; Laws steuern Price/Recovery | `CAPTIVE_HUMAN` Resource → ENTFERNEN; `POPULATION_CLASS_CHANGE` nutzen |
| **Law System** | V71: Dynamic Laws (GP Cost, Tiers, Prereqs, Boost Effects) | Alle Custom-Mechaniken → Laws migrieren |
| **Diplomatic Actions** | V71: Stance-based (NEUTRAL→TRADE→PACT→ALLIED), Embassy required | Orc↔Undead Slave Trade = Custom Diplomatic Action |
| **Population Growth** | V71: Formula = Base × Climate × Terrain × Housing × Food × Law | Undead `GROWTH: 0.0` + Conversion-only via Law |
| **Race Relations** | `GameRaceApi.setLiking()` runtime-modifiable | Geist-System → Race Relations boosten |

**UNVERIFIED BLOCKER (muss Felix testen):**
| # | Frage | Test-Kommando |
|---|-------|---------------|
| Q1 | `_ignoreVanilla: true` auf HUMAN/ORC Race-Slots → Engine-Crash? | New Game → Undead wählen → Save/Load |
| Q2 | `POPULATION_CLASS_TRANSFER` cross-faction (Orc→Undead) → funktioniert? | Event triggern → Stockpile prüfen |
| Q3 | `REQUIRES_BOOST` in Room.txt + Event `REQUIRES.EQUAL.BOOST` → Engine respektiert? | Building bauen → Event prüfen |

**LEHRE:** **Engine-Änderungen diktieren Data-Struktur.** Nicht "wie wollen wir es", sondern "wie unterstützt die Engine es nativ". Jede Custom-Resource die ein natives Population-Class ersetzt = Technical Debt.

---

### PHASE 2 — ARCHITEKTUR-ENTSCHEIDUNGEN (Architecture Blocks B + C)
**Datum:** 2026-07-14 (Entscheidungen dokumentiert)

| Decision Point | Optionen | Entscheidung | Begründung (komprimiert) |
|----------------|----------|--------------|--------------------------|
| **Script-Architektur** | A: Monolith / B: 4 Mods / C: Hybrid Core+Modules | **C — Hybrid** | 1 Mod, 1 Script, Package-Isolation für Agents, Core Bus für Cross-Race |
| **Mod-Struktur** | A: Single Mod / B: 4 Mods | **A — Single** | Circular Dependency Orc↔Undead unmöglich bei 4 Mods |
| **Dual Settlement** | A: Native / B: Region-Proxy / C: Worldmap Building | **B — Region-Proxy + Core State** | Engine hart 1 Capital; Region hat Population/Stockpile/Buildings nativ |
| **Gate-System** | A: Native Boost / B: Event / C: Scan + Core State | **C — Scan + Core State** | Native Boosts nur faction-wide; Events nicht persistiert |
| **Geist-System** | A: Loyalty Rename / B: Custom State / C: Law Boost | **B — Custom State** | Loyalty ≠ Control Gradient; braucht eigene Decay/Building-Logic |
| **Slave Pipeline** | A: Resource / B: Population Class / C: Hybrid | **B — Population Class** | V71 Native, keine Custom Resource nötig |

**LEHRE:** **Architektur-Entscheidungen vor Implementation.** Jede "später korrigieren wir das" kostet 10x mehr. Die Decision Records in `architecture/` sind das Fundament — Agents arbeiten GEGEN diese Contracts, nicht mit Freiheitsgraden.

---

### PHASE 3 — IMPLEMENTATION SEQUENCE (Plan für Phase 3)
**Noch NICHT ausgeführt — basiert auf allen vorherigen Phasen**

#### Sprint 1: Foundation (Week 1-2)
```
1. Maven Module `syxcraft` mit `mod-sdk` Profile
   → Game JAR installieren, SDK Dependency (GitHub Packages Auth?)
2. Core Script Skeleton
   → SyxCraftCoreScript, CoreBus, CoreStateManager
   → Package Structure anlegen (core/, undead/, orc/, human/, nightelf/)
3. Validator Schemas in tools/schemas/
   → Pre-Commit Hook: JSON Schema Validation
4. Race Override Test
   → UNDEAD.txt mit _ignoreVanilla: true → New Game → Save/Load
   → **BLOCKER:** Wenn Q1 crasht → Architecture Pivot
```

#### Sprint 2: Undead MVP (Week 2-4)
```
1. Data Files: UNDEAD.txt, SLAVERY Laws, NECROMANCY Tech, Events
2. UndeadModule: GhostManager, ConversionManager, GateManager, HumanFarmManager
3. Dual Settlement Init: Adjacent Region claimen, Human Village (10 Citizens) spawnen
4. Gate Scan Loop: Human Village Buildings → Core State Boost Flags
5. Build + 100 Days Smoke Test
   → Geist visible? Gates unlocken? Conversion triggert?
```

#### Sprint 3: Orc Integration (Week 4-5)
```
1. OrcModule: RaidManager, SlaveTradeManager
2. Diplomatic Action: REQUEST_SLAVE_TRADE (requires PACT, both Slavery Laws)
3. Pipeline Test: Orc Raid → SLAVE(HUMAN) in Orc Stockpile → Trade → Undead Conversion
```

#### Sprint 4: Human + Night Elf (Week 5-7)
```
1. HumanModule: ImmigrationManager (CIVIC_IMMIGRATION>MUL: 1.5)
2. NightElfModule: StealthManager, MoonwellManager, Druidic Grove
3. FactionGroup Enum: ALLIANCE / HORDE in Core State
4. War State: Custom Score, Region Control Flags
5. Shared Narrative Events: Core Bus + Data Events
```

#### Sprint 5: Polish & Release (Week 7-8)
```
1. Balance Playtest: 3-5 Spieler, 100 Days each
2. UI: Farm Panel, Geist Tooltip, Gate Notifications
3. Workshop Upload: _src folder, Version Sync, Changelog
```

---

## ÜBERGEORDNETE LEHREN — "WOULD DO AGAIN" VS "WOULD NEVER DO AGAIN"

### ✅ WOULD DO AGAIN
| Practice | Warum |
|----------|-------|
| **Concept-First, Research-Second, Code-Last** | 3 Phasen Research sparten geschätzt 200h Refactor |
| **Architecture Decision Records (ADRs)** in `architecture/` | Agents arbeiten gegen Contracts, nicht ins Blaue |
| **Single Mod, Single Script, Package-Isolation** | Keine Dependency Hell, Parallele Agent-Arbeit möglich |
| **Engine-Native First (Laws, Population Class, Events)** | Custom Resource `CAPTIVE_HUMAN` war Technical Debt |
| **Core State Manager + Core Bus Pattern** | Saubere Cross-Settlement + Cross-Race Communication |
| **Validator Schemas als Pre-Commit Hook** | Data-Files validieren vor Build, nicht nach Crash |
| **Scope-Reduktion: Undead MVP First** | 4 Rassen parallel = Chaos; 1 Rasse testbar = Fortschritt |

### ❌ WOULD NEVER DO AGAIN
| Anti-Pattern | Was stattdessen |
|--------------|-----------------|
| **Custom Resource für natives Population-Class** | `POPULATION_CLASS_CHANGE` + Laws nutzen |
| **Monolithisches Script ohne Module** | Package-Isolation + Core Bus |
| **4 Mods für 4 Rassen** | Circular Dependency bei Cross-Features (Slave Trade) |
| **Event-only State (nicht persistiert)** | Core State Manager + FilePutter/FileGetter |
| **Boost-Flags für Cross-Settlement ohne Scan** | Building Scan jeden Tick → deterministisch |
| **Implementation vor Architecture Decisions** | Jede ADR spart 10x Refactor-Zeit |
| **Balance vor Feature-Complete** | Numbers sind Platzhalter bis MVP testbar |

---

## OFFENE BLOCKER — MÜSSEN VOR SPRINT 1 GEKLÄRT WERDEN

| Blocker | Test | Owner |
|---------|------|-------|
| **Q1** `_ignoreVanilla` auf HUMAN/ORC Race-Slots crash-free? | New Game → Undead → Save/Load | Felix |
| **Q2** `POPULATION_CLASS_TRANSFER` Orc→Undead funktioniert? | Event triggern → Stockpile prüfen | Felix |
| **Q3** `REQUIRES_BOOST` in Room + Event `EQUAL.BOOST` respektiert? | Building bauen → Event prüfen | Felix |
| **Q4** Mod SDK `io.github.4rg0n:sos-mod-sdk:0.1.5` auf GitHub Packages öffentlich? | `mvn dependency:get` | Felix |
| **Q5** Custom Diplomatic Actions via Data File ladbar? | `DIPLOMATIC_ACTIONS` in `_ignoreVanilla` testen | Felix |

---

## NÄCHSTER SCHRITT
**Felix entscheidet Q1-Q5** → Sprint 1 startet.

*Ende E — Implementation Sequence & Lessons Learned*
*Basierend auf Research Phase 1+2, Architecture A-C, V71 Engine-Analyse*