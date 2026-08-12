# Interdependency Matrix — SyxCraft Four-Faction WoW Overhaul

> **Purpose:** Every race/faction must mechanically interact with ≥2 others. No isolated silos.
> **Format:** `From → To | What | Condition | Mechanic`
> **Engine:** V71.44 "Reign of Terror"

---

## Core Resource Flow

```
HUMAN (Population) 
    ──[ORC_SLAVE_RAID]──→ ORC (SLAVE Stockpile)
    ──[UNDEAD_CONVERSION]──→ UNDEAD (Citizens)
    
ORC (CAPTIVE_HUMAN Stockpile) 
    ──[SLAVE_TRADE]──→ UNDEAD (SLAVE Input)
    ──[RAID_LOOT]──→ ORC (Credits/Resources)
    
UNDEAD (ESSENCE/BONE Output)
    ──[ESSENCE_TRADE]──→ NIGHT_ELF (Moonwell Synthesis)
    ──[BONE_CRAFTING]──→ HUMAN/ORC (Equipment)

NIGHT_ELF (MOONWATER/ESSENCE Output)
    ──[ALLIANCE_TRADE]──→ HUMAN (Diplomacy Bonus)
    ──[BLIGHT_CLEANSE]──→ ALL (Blight Reduction)
```

---

## Full 4x4 Matrix (16 Directions)

### HUMAN (Allianz) → Others

| Von → Nach | Was | Bedingung | Mechanik |
|------------|-----|-----------|----------|
| **Human → Orc** | Trade Goods (Food, Equipment) | `TRADE_AGREEMENT` + Neutral Relations | Standard Trade Caravan; Orcs need Food, Humans need Metals |
| **Human → Night Elf** | Alliance Support (Diplomacy/Trade Bonus) | `ALLIANCE_COMMAND` Tech + Embassy | `ALLIANCE_SUPPORT` Event → +25% Trade Value, +Migration Boost |
| **Human → Undead** | Conversion Source (Unwilling) | Human Population in Range | `UNDEAD_CONVERSION` Event targets SLAVE Class HUMAN → Undead Citizen |
| **Human → Human** | Migration/Trade | Open Borders | Standard Immigration/Emigration |

### ORC (Horde) → Others

| Von → Nach | Was | Bedingung | Mechanik |
|------------|-----|-----------|----------|
| **Orc → Human** | Slave Raids (Population Loss) | `ORC_SLAVERY` Tech + Human Settlement in Range (50 tiles) | `ORC_SLAVE_RAID` Event → Human loses SLAVE Class citizens → Orc gains SLAVE Stockpile |
| **Orc → Night Elf** | Raid Target | `ORC_SLAVERY` + Night Elf Settlement | `ORC_SLAVE_RAID` on Night Elf Settlement → SLAVE Capture (Race: NIGHT_ELF possible via Law) |
| **Orc → Undead** | Slave Trade (Credits + Essence) | `ORC_SLAVERY` Tech + Diplomatic Trade Agreement + SLAVERY Law Tier 2+ | Diplomatic Action `REQUEST_SLAVE_TRADE` → Transfer SLAVE Class Population for Credits + ESSENCE |
| **Orc → Orc** | Inter-Clan Raids | Horde Faction Relations | Internal Horde Mechanics |

### UNDEAD (Horde) → Others

| Von → Nach | Was | Bedingung | Mechanik |
|------------|-----|-----------|----------|
| **Undead → Human** | Conversion Target | `NECROMANCY_HUMAN_FARM` Tech + `HUMAN_PENS` Room + CAPTIVE_HUMAN Stock | `UNDEAD_CONVERSION` Event: SLAVE (HUMAN) → UNDEAD Citizen (1:1 base, Tech improves) |
| **Undead → Orc** | Essence/Bone Trade | Trade Agreement + Neutral Relations | Trade: ESSENCE/BONE for Credits/Resources |
| **Undead → Night Elf** | Blight Spread (Threat) | `DARK_RITUALS` Tech | `BLIGHT_SPREAD` Event → Terrain Corruption → Night Elf Farming Penalty |
| **Undead → Night Elf** | Essence Trade (Moonwell Synthesis) | `MOONWELL_ESSENCE_SYNTHESIS` Tech (Night Elf) | Night Elf Tech unlocks Essence ↔ Moonwater Conversion |
| **Undead → Undead** | Conversion Efficiency | `NECROPOLIS_MASTERY` Tech | Conversion Ratio 1:1 → 1:2, Cooldown Reduction |

### NIGHT_ELF (Allianz) → Others

| Von → Nach | Was | Bedingung | Mechanik |
|------------|-----|-----------|----------|
| **Night Elf → Human** | Alliance Support / Moonwater Export | `ALLIANCE_COMMAND` + Embassy | Trade Bonus + Vision Share + Migration Boost |
| **Night Elf → Orc** | Anti-Horde Counter | `SENTINEL_OUTPOST` Tech | `WATCHING_THE_HORDE` Buff → Orc Raid Cooldown ×1.5 in Region |
| **Night Elf → Undead** | Blight Cleanse | `DRUIDIC_GROVES` Tech + `BLIGHT_CLEANSE` Event | `BLIGHT_CLEANSE` Event → Blight Level ×0.5 in Region |
| **Night Elf → Undead** | Essence Trade (Moonwell Synthesis) | `MOONWELL_ESSENCE_SYNTHESIS` Tech | Trade: MOONWATER → ESSENCE (Rate: 10:1) |
| **Night Elf → Night Elf** | Territory Control | `ANCIENT_GUARDIANS` Tech | Forest Expansion + Defense Bonus |

---

## Tech Dependency Graph (Cross-Faction)

```
BASIC_MINING (Universal)
    │
    ├─→ ALLIANCE_COMMAND (Human) ──→ ROOM_ALLIANCE_HQ
    ├─→ ORC_SLAVERY (Orc) ──→ Diplomatic Action: REQUEST_SLAVE_TRADE
    ├─→ NECROMANCY_HUMAN_FARM (Undead) ──→ Laws: UNDEAD_SLAVERY, UNDEAD_CONVERSION, HUMAN_FARM_MGMT
    │       │
    │       ├─→ UNDEAD_NECROPOLIS_MASTERY (Civic+Scientific) ──→ Room Upgrades, Conversion 1:2
    │       └─→ DARK_RITUALS (Religious) ──→ MASS_CONVERSION, ESSENCE_HARVEST
    │
    ├─→ SENTINEL_OUTPOST (Night Elf) ──→ ROOM_SENTINEL_OUTPOST
    │       │
    │       └─→ MOON_BLADES (Military+Scientific) ──→ MOON_FORGE, Moon Damage vs Undead
    │
    ├─→ DRUIDIC_GROVES (Night Elf) ──→ ROOM_DRUIDIC_GROVE, ROOM_MOONWELL
    │       │
    │       ├─→ ANCIENT_GUARDIANS (Civic+Scientific) ──→ Forest Defense
    │       └─→ MOONWELL_MASTERY (Religious+Civic) ──→ Moonwater ×1.5, Regeneration
    │
    └─→ DRUIDIC_GROVES ──→ MOONWELL_ESSENCE_SYNTHESIS (Scientific+Arcane) ──→ ESSENCE_FROM_MOONWATER
```

---

## Resource Flow Summary

| Resource | Producers | Consumers | Cross-Faction Flow |
|----------|-----------|-----------|-------------------|
| **SLAVE (Pop Class)** | Orc Raids, Enslavement Law | Undead Conversion, Orc Storage | Orc → Undead (Trade) |
| **CAPTIVE_HUMAN** | ~~Resource~~ → **SLAVE Class** | Undead Conversion | N/A (Replaced by SLAVE Class) |
| **ESSENCE** | Undead Drops, Night Elf Moonwell Synthesis | Undead Conversion, Night Elf Magic, Crafting | Undead → Night Elf (Trade), Undead → Human/Orc (Crafting) |
| **BONE** | Undead Drops | Undead Crafting, Human/Orc Equipment | Undead → All (Trade) |
| **MOONWATER** | Night Elf Moonwells | Night Elf Consumption, Undead Trade | Night Elf → Undead (Trade) |
| **MOONWATER → ESSENCE** | Night Elf Tech `MOONWELL_ESSENCE_SYNTHESIS` | Undead Conversion Fuel | Night Elf → Undead (Trade) |
| **CREDITS** | All Factions | All Trade | Universal Medium |

---

## Validation Rules (Architecture Constraints)

1. **No Isolated Race:** Each race has ≥2 incoming + ≥2 outgoing edges
2. **Resource Circularity:** Every produced resource consumed by ≥1 other race
3. **Tech Reachability:** Every tech reachable from `BASIC_MINING`
4. **Event Chaining:** Events form Trigger → Choice → Consequence → Follow-up chains
4. **Balance Symmetry:** Horde/Alliance resource flow within ±20%

---

## Open Questions for Implementation

| Question | Impact | Resolution Needed |
|----------|--------|-------------------|
| Can Night Elf SLAVE Class exist? | Orc raids on Night Elf settlements | Vanilla Law: `SLAVE_RACE_WHITELIST` configurable? |
| `SLAVE` Class for Night Elf Race? | Orc raids on Night Elf settlements | Check V71 `SLAVE_RACE_WHITELIST` Law config |
| Moonwater as Physical Resource? | Trade logistics | `EDIBLE: true` + `TRADEABLE: true` + `STACK_SIZE: 20` |
| Blight Mechanic in V71? | Night Elf Cleanse Event | Check V71 `BLIGHT_LEVEL` terrain property |
| Essence ↔ Moonwater Conversion Rate? | Trade Balance | Start 10:1, adjustable via Tech |

---

*End of Interdependency Matrix*