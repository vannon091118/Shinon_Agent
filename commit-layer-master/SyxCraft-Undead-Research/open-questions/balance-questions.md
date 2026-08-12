# Balance Questions — SyxCraft Undead Overhaul

> **Ziel:** Quantifizierte Design-Entscheidungen für Playtest-Phase
> **Methode:** Spreadsheet-Ready Zahlen, klare Formeln, Test-Cases

---

## 1. CAPTIVE_HUMAN Economy

### Growth Formulas

| Source | Formula | Base | Scaling |
|--------|---------|------|---------|
| **HUMAN_PENS** (Room) | `daily_growth = workers * BASE_RATE * (1 + level_bonus * level)` | `BASE_RATE = 0.02` (2%/Worker/Tag) | `level_bonus = 0.005` pro Upgrade |
| **WORLD_HUMAN_FARM** (Worldmap) | `daily_growth = BASE_RATE * LEVEL_MULT^level` | `BASE_RATE = 5.0`/Tag | `LEVEL_MULT = 1.5` pro Level (Max 5) |
| **ORC_SLAVE_RAID** (Event) | `captives = BASE_RAID * EFFICIENCY * RANDOM(0.8, 1.2)` | `BASE_RAID = 20` | `EFFICIENCY` via Tech/Boost |

### Conversion Costs

| Input | Cost | Output | Cooldown |
|-------|------|--------|----------|
| **Standard Conversion** | 5 CAPTIVE_HUMAN + 1 ESSENCE | 1 UNDEAD Citizen | 30 Tage (Global) |
| **Mass Conversion** (Event) | 50 CAPTIVE_HUMAN + 10 ESSENCE | 10 UNDEAD Citizens | 90 Tage |
| **Ritual Conversion** (Dark Rituals Tech) | 20 CAPTIVE_HUMAN + 5 ESSENCE | 5 UNDEAD + 20 ESSENCE | 60 Tage |

### Stockpile Limits

| Resource | Stack Size | Max per Settlement | Warning Threshold |
|----------|------------|-------------------|-------------------|
| `CAPTIVE_HUMAN` | 10 | 500 (Level 1) → 2000 (Level 5 Farm) | 80% → Morale Penalty |
| `ESSENCE` | 50 | 200 | 50% → Conversion Cooldown +50% |
| `BONE` | 100 | 1000 | - |

---

## 2. Human Farm Balance

### Farm Level Progression

| Level | Cost (Wood/Stone/Metal/Credits) | Build Time | Daily Captives | Maintenance (Credits/Essence) |
|-------|--------------------------------|------------|----------------|-------------------------------|
| 1 | 200 / 300 / 100 / 5,000 | 30 Tage | 5.0 | 50 / 10 |
| 2 | +100 / +150 / +0 / +2,000 | 15 Tage | 7.5 (×1.5) | 75 / 15 |
| 3 | +200 / +300 / +50 / +5,000 | 20 Tage | 11.25 (×2.25) | 125 / 25 |
| 4 | +500 / +500 / +100 / +10,000 | 25 Tage | 16.875 (×3.375) | 250 / 40 |
| 5 | +1000 / +1000 / +200 / +25,000 | 30 Tage | 25.3 (×5.0) | 500 / 75 |

**Total Investment Level 5:** ~2000 Wood, 2250 Stone, 450 Metal, 47,000 Credits, 120 Tage Build Time.

### ROI Calculation

```
Level 5 Farm: 25.3 Captives/Tag
Conversion: 5 Captives = 1 Undead
→ 5 Undead/Tag = 35 Undead/Woche
Break-even (Credits): 47,000 / (35 * Credit_Value_Per_Undead)
```

**Frage:** Wie viel "Wert" hat 1 Undead Citizen in Credits/Tag?
- Arbeit: ~1.0 Work Speed × Maintenance 1.5 = 1.5 effektiv
- Kein Food/Drink Cost = ~2 Credits/Tag Ersparnis
- 35 Undead/Woche × 2 Credits × 7 = 490 Credits/Woche
- Break-even: ~96 Wochen (zu lang!)

**Anpassung nötig:** Entweder Farm Output ↑ oder Conversion Cost ↓ oder Undead Wert ↑.

---

## 3. Orc Trade Balance

### Orc Slave Pen (NPC Building)

| Parameter | Wert |
|-----------|------|
| Raid Cooldown | 60 Tage |
| Base Captives per Raid | 20 |
| Efficiency (Tech) | +20% pro Level |
| Sale Price to Undead | 50 Credits pro Captive |
| Max Stockpile (Orc) | 100 Captives |

### Trade Flow

```
Orc Raid (Human Settlement) 
    → 20 Captive Humans generated in Orc Stockpile
    → Orc offers Trade: 20 CAPTIVE_HUMAN for 1,000 Credits
    → Undead Player accepts/negotiates
    → Credits transferred, Captives moved to Undead Stockpile
```

**Balance Check:** 
- 1,000 Credits für 20 Captives = 50 Credits/Captive
- Conversion Cost: 5 Captives + 1 Essence = 1 Undead
- → 250 Credits + Essence pro Undead via Trade
- vs. Own Farm: ~2,000 Credits Invest für 5 Captives/Tag → 400 Credits/Captive (amortisiert)

**Trade ist günstiger** → Gut für Early Game, Farm für Late Game Autonomie.

---

## 4. Undead Race Stats Balance

### Comparison: Human vs. Undead (SyxCraft V70)

| Stat | Human | Undead (Current) | Δ | Bewertung |
|------|-------|------------------|---|-----------|
| `ADULT_AT_DAY` | 80 | **20** | -75% | **Sehr schnell** — Snowball Risk |
| `GROWTH` | 0.075 | 0.0 (implizit) | -100% | Kein natürliches Wachstum ✓ |
| `LIFE_IMMORTAL` | false | **true** | — | **Stark** — Keine Alterung |
| `FOOD.HUNGER_RATE` | 1.0 | 0.0 | -100% | **Sehr stark** — Kein Food Cost |
| `WORK.MAINTENANCE` | 1.0 | **1.5** | +50% | Gut für Infrastruktur |
| `WORK.SPEED` | 1.0 | **0.9** | -10% | Leichter Malus |
| `ENVIRONMENT.*_RESISTANCE` | 0.7-1.0 | **1.0 all** | +15-30% | **Sehr stark** — Überall siedelbar |
| `CIVIC_IMMIGRATION` | 1.5 (Boost) | 0.0 (Boost) | — | Keine Immigration ✓ |
| `BEHAVIOUR_SANITY` | 1.0 | **2.0** (Boost) | +100% | **Sehr stark** — Kein Wahnsinn |

### Identifizierte Imbalances

1. **`ADULT_AT_DAY: 20`** → Untote "erwachsen" in 20 Tagen vs 80 bei Menschen. Conversion → sofort arbeitsfähig. **Fix:** `ADULT_AT_DAY: 60` (wie Orcs) oder Conversion setzt `AGE = ADULT_AT_DAY`.

2. **Kein Food/Drink + Immortal + Climate Immune** = **Übermächtig** für Expansion. **Fix:** 
   - `MAINTENANCE` Cost: Untote brauchen `ESSENCE` pro Tag (0.1/Citizen) für "Erhalt".
   - Oder: `WORK.SPEED: 0.7` (30% langsamer) als Tradeoff.

3. **Conversion Snowball:** 1 Human Farm → 5 Captives/Tag → 1 Undead/Tag → Mehr Worker → Mehr Farms. **Fix:** Global Conversion Cooldown + Captive Cap.

---

## 5. Tech Cost Balancing

### Knowledge Costs by Tier

| Tier | Techs | CIVIC_KNOWLEDGE | MILITARY | SCIENTIFIC | RELIGIOUS |
|------|-------|----------------|----------|------------|-----------|
| Early (1-2) | BASIC_MINING, AGRICULTURE | 30-100 | - | - | - |
| Mid (3-5) | NECROMANCY_HUMAN_FARM, ORC_SLAVERY | 150-200 | 150 | - | - |
| Late (6-8) | NECROPOLIS_MASTERY, DARK_RITUALS | 300-500 | - | 300 | 200 |
| End (9+) | MASS_CONVERSION, LICH_TRANSFORMATION | 1000 | 500 | 500 | 500 |

**Knowledge Generation Rate (ca.):**
- Early Game: ~5-10 Civic/Day
- Mid Game: ~20-50 Civic/Day  
- Late Game: ~100+ Civic/Day

→ `NECROMANCY_HUMAN_FARM` (200) = ~10-40 Tage Early, ~4-10 Tage Mid. **OK.**

---

## 6. Playtest Scenarios (Test Cases)

| Scenario | Setup | Expected Outcome | Pass Criteria |
|----------|-------|------------------|---------------|
| **TC-01: Fresh Undead Start** | New Game, Undead Race, No Farm | Struggle Early, Rush Farm Tech | Farm Tech by Day 50, Survive Day 100 |
| **TC-02: Conversion Loop** | 100 Humans captured, Farm Level 1 | Stable Undead Growth | +5 Undead/Week sustained |
| **TC-03: Orc Trade Dependency** | No Farm, Orc Neighbor | Trade for Captives | 100 Captives by Day 100 via Trade |
| **TC-04: Late Game Snowball** | Farm Level 5, 200 Undead | Explosive Growth? | Growth Rate < 10%/Week |
| **TC-05: Human Player vs Undead** | Human Player attacks Undead | Undead Defense viable | Undead don't auto-lose |
| **TC-06: Save/Load Stability** | 500h Game, Save/Load 10x | State preserved | Zero desync, zero data loss |

---

## 7. Balance Adjustment Knobs (Für Playtest)

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

## 8. Metriken für Automatisierte Balance-Checks

```python
# Pseudo-Code für Balance Simulation
def simulate_undead_growth(days=365):
    state = {
        'undead': 10,
        'captives': 0,
        'farm_level': 1,
        'essence': 50,
        'credits': 1000
    }
    
    for day in range(days):
        # Farm Production
        state['captives'] += farm_output(state['farm_level'])
        
        # Conversion (if cooldown ready)
        if can_convert(state):
            convert = min(state['captives'] // 5, state['essence'])
            state['undead'] += convert
            state['captives'] -= convert * 5
            state['essence'] -= convert
        
        # Orc Trade (random)
        if day % 60 == 0 and orc_trade_available():
            buy = min(20, state['credits'] // 50)
            state['captives'] += buy
            state['credits'] -= buy * 50
        
        # Maintenance
        state['essence'] -= state['undead'] * ESSENCE_MAINTENANCE
        
        # Growth Cap Check
        if state['undead'] > CAPTIVE_CAP(state['farm_level']):
            # Stagnation
            pass
    
    return state
```

**Target Metrics:**
- Day 100: ~50 Undead (Early Game)
- Day 365: ~300 Undead (Mid Game)  
- Day 730: ~800 Undead (Late Game, cap-nahe)
- Nie: >2000 Undead (Hard Cap durch Captive Economy)

---

## Nächste Schritte

1. **Spreadsheet erstellen** mit allen Formeln → Live-Balancing während Playtest
2. **Simulation Script** (Python/Node) für 1000 Monte-Carlo Runs
3. **Playtest Session** mit 3-5 Spielern → Feedback → Knobs justieren
4. **Version 0.1.0** → Balance Freeze → Content Complete