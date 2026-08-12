# Interdependency Matrix — SyxCraft Four-Faction WoW Overhaul

> **Zweck:** Jede Rasse/Fraktion muss mechanisch mit mindestens 2 anderen verknüpft sein. Keine isolierten Silos.
> **Format:** `Von → Nach | Was | Bedingung | Mechanik`

---

## Horde (Orcs + Undead)

| Von → Nach | Was | Bedingung | Mechanik |
|------------|-----|-----------|----------|
| **Orc → Undead** | Captive Humans (Ressource) | `ORC_SLAVERY` Tech + Raid Event | `ORC_SLAVE_RAID` Event → `CAPTIVE_HUMAN` in Orc Stockpile → Trade Offer an Undead |
| **Undead → Orc** | Credits + Essence | Trade Accept | Diplomacy Event `ORC_SLAVE_TRADE_OFFER` → Credits/ESSENCE transfer |
| **Orc → Human** | Raid Target (Population Loss) | `ORC_SLAVERY` + Human Settlement in Range | `ORC_SLAVE_RAID` Event → Human Settlement verliert Bürger |
| **Undead → Human** | Conversion Target | `NECROMANCY_HUMAN_FARM` Tech + `HUMAN_PENS` Room | `UNDEAD_CONVERSION` Event → Human Bürger → Undead Bürger |

---

## Allianz (Human + Night Elf)

| Von → Nach | Was | Bedingung | Mechanik |
|------------|-----|-----------|----------|
| **Human → Night Elf** | Alliance Support (Diplomacy/Trade Bonus) | `ALLIANCE_COMMAND` Tech + Embassy | `ALLIANCE_SUPPORT` Event → Trade Bonus + Migration Boost |
| **Night Elf → Human** | Magic/Scout Support | `SENTINEL_OUTPOST` Tech + Moonwell | `SENTINEL_AID` Event → Vision + Magic Buff |
| **Human → Undead** | Conversion Source (Unwilling) | Human Population in Range | `UNDEAD_CONVERSION` Event zielt auf Human Bürger |
| **Night Elf → Undead** | Anti-Undead Counter | `DRUIDIC_GROVES` Tech | `BLIGHT_CLEANSE` Event reduziert Undead Conversion Rate in Region |

---

## Cross-Faction (Horde ↔ Allianz)

| Von → Nach | Was | Bedingung | Mechanik |
|------------|-----|-----------|----------|
| **Orc → Night Elf** | Raid Target | `ORC_SLAVERY` + Night Elf Settlement | `ORC_SLAVE_RAID` auf Night Elf Siedlungen |
| **Undead → Night Elf** | Blight Spread | `DARK_RITUALS` Tech | `BLIGHT_SPREAD` Event → Terrain Corruption → Night Elf Farming Penalty |
| **Human → Orc** | Trade (Reluctant) | Neutral Diplomacy | Standard Trade, aber Relations Penalty |
| **Night Elf → Orc** | Anti-Horde Buff | `SENTINEL_OUTPOST` | `WATCHING_THE_HORDE` Buff → Orc Raid Cooldown Increase |

---

## Ressourcen-Fluss (Resource Flow)

```
HUMAN (Population) 
    ↓ [ORC_SLAVE_RAID] 
ORC (CAPTIVE_HUMAN Stockpile) 
    ↓ [TRADE: Credits + ESSENCE] 
UNDEAD (CAPTIVE_HUMAN Input) 
    ↓ [HUMAN_PENS: Growth / NECROPOLIS: Conversion] 
UNDEAD (Population + BONE/ESSENCE Output)
```

---

## Tech-Abhängigkeiten (Tech Dependencies)

| Tech | Benötigt Von | Freischaltet Für |
|------|--------------|------------------|
| `BASIC_MINING` | `ORC_SLAVERY`, `ALLIANCE_COMMAND`, `NECROMANCY_HUMAN_FARM` | `ROOM_MINE` |
| `ORC_SLAVERY` (Orc) | — | `ROOM_SLAVE_PEN`, `ORC_SLAVE_RAID` Event |
| `NECROMANCY_HUMAN_FARM` (Undead) | `BASIC_MINING` | `ROOM_HUMAN_PENS`, `ROOM_NECROPOLIS`, `WORLD_HUMAN_FARM` |
| `ORC_SLAVERY` (Orc) | `BASIC_MINING` | `ROOM_SLAVE_PEN`, `ORC_SLAVE_RAID` |
| `ALLIANCE_COMMAND` (Human) | `BASIC_MINING` L1 | `ROOM_ALLIANCE_HQ` |
| `SENTINEL_OUTPOST` (Night Elf) | `BASIC_MINING` | `ROOM_MOONWELL`, `SENTINEL_AID` |
| `DRUIDIC_GROVES` (Night Elf) | `SENTINEL_OUTPOST` | `ROOM_GROVE`, `BLIGHT_CLEANSE` |
| `ORC_SLAVERY` (Orc) | `BASIC_MINING` L1 | `ROOM_SLAVE_PEN`, `ORC_SLAVE_RAID` |

---

## Validierungsregeln (Validation Rules)

1. **Keine isolierte Rasse:** Jede Rasse muss min. 2 eingehende + 2 ausgehende Pfeile haben
2. **Ressourcen-Kreislauf:** Jede produzierte Ressource muss von mind. 1 anderer Rasse verbraucht werden
3. **Tech-Abhängigkeit:** Keine Tech ohne Pfad von `BASIC_MINING`
4. **Event-Ketten:** Events müssen in Ketten (Trigger → Choice → Consequence → Follow-up) denken
5. **Balance-Check:** Horde/Allianz Ressourcen-Fluss muss symmetrisch sein (±20%)