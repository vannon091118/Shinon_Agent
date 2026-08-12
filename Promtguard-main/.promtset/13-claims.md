# R13 — Claims (Verifikations-Atome)

**Jede Research-Aussage IST ein Claim, bis sie verifiziert wurde.**  
Claims sind die Brücke zwischen Research-Befunden und codierten Tatsachen.

## Definition

Ein **CLAIM** ist eine diskrete, atomare, falsifizierbare Aussage über das System
— typischerweise aus `decisions[]` oder explizit deklariert über `claims[]`
im Research-JSON. Ein Claim ist _kein_ Design-Entscheid (→ Decision-Journal),
sondern eine konkrete Behauptung über Code/Architektur/Verhalten.

| Konzept | Wann es lebt | Wo es steht |
|---|---|---|
| **Decision** | Architektonische Wahl mit Trade-offs | `decision-journal.jsonl` |
| **Claim** | Faktische Behauptung, falsifizierbar | `claim-log.jsonl` |
| **Context-Token** | Beleg dass ein Task erledigt wurde | `context-log.jsonl` |

## Lebenszyklus

```
1. Research liefert JSON
   └─ ingest extrahiert automatisch EIN CLAIM PRO DECISION
      (claim_origin = "decision-extraction", status = "unverified")
   └─ ingest akzeptiert auch explizite claims[] / verified_claims[]

2. Re-Research prüft gegen aktuellen Code
   └─ Research-JSON enthält verified_claims[] (z.B. RES-019 zu RES-014)
   └─ ingest aktualisiert CLAIM-Status:
      verified (positiv bestätigt)
      refuted  (widerlegt — alter Eintrag bleibt, neue Zeile mit status=refuted)
      refined  (präzisiert — neue Formulierung in zusätzlicher Zeile)

3. Konsument (Coder, Folge-Research) sieht nur den letzten Status pro ID
   └─ resolve_claims() = latest-wins pro CLAIM-ID
```

## ID-Format

**`CLAIM-{PREFIX}-{SEQ:03d}`** — analog zu CTX, pro Projekt isoliert.

Beispiele: `CLAIM-SYX-001`, `CLAIM-GEN-042`

- Prefix = Projekt-Prefix (aus `projects.json`, gleicher Mechanismus wie CTX)
- SEQ = fortlaufende 3-stellige Nummer pro Projekt im `claim-log.jsonl`
- IDs sind deterministisch — nachträgliches Backfill von 122 existierenden
  Decisions ist via `claim migrate-from-decisions` möglich (kein Default)

## Append-only + Latest-wins

`claim-log.jsonl` ist append-only wie alle State-Logs. **Status-Updates werden
als NEUE Zeile mit derselben ID angehängt** — die alte Zeile wird NICHT
gelöscht (R01).

```jsonl
{"id":"CLAIM-SYX-001","status":"unverified","claim":"perHeadTax hat kein Hard Cap","source_res":"RES-002","timestamp":"2026-07-28T05:36:55Z"}
{"id":"CLAIM-SYX-001","status":"verified","verified_by_res":"RES-014","verified_evidence":"Fiscal.java:224:setHeadTax → Math.max(0,v)","timestamp":"2026-07-28T07:05:59Z"}
```

Lesen: `resolve_claims()` durchläuft das Log von oben nach unten und nimmt
jeweils den letzten Eintrag pro ID → aktueller Status.

## Subcommands (`promptgen.py`)

| Subcommand | Zweck |
|---|---|
| `claim list` | Alle Claims gruppiert nach Status |
| `claim show CLAIM-XXX` | Decision-Trail eines Claims (alle Zeilen) |
| `claim verify CLAIM-XXX --status X --evidence Y` | Manuell verifizieren/widerlegen |
| `claim migrate-from-decisions [--min-id RES-NNN]` | Backfill: Decisions → Claims (EINMALIG) |

## Schema

**Eintrag:** `.promtset/schemas/claim-v1.json` — definiert Pflichtfelder
`id, claim, status, source_res, timestamp`.

**Im Research-JSON** (`.promtset/schemas/researcher-context-v2.json`, optional):

```jsonc
{
  "claims": [           // optionales Feld — explizite Claim-Deklarationen
    {
      "claim": "EngineSeams.java hat 28 public static Methoden",
      "evidence": "EngineSeams.java:30-280",
      "confidence": "high"
    }
  ],
  "verified_claims": [  // optionales Feld — Verifikations-Updates
    {
      "claim_index": 0,   // optional: 0-basierter Index der originalen claims[] Zeile
      "claim_id": "CLAIM-SYX-012",  // optional: direkte ID-Referenz wenn schon existent
      "claim": "EngineSeams.java hat 28 public static Methoden (verified)",
      "status": "verified",          // verified | refuted | refined
      "evidence": "EngineSeams.java:280"
    }
  ]
}
```

`decisions[]` ist weiterhin für architektonische Entscheidungen da. Claims
entstehen **automatisch aus jedem Eintrag in `decisions[]`** — ein Decision
mit `what + evidence + confidence` ist bereits ein Claim.

## Warum eigene Datei?

- Decision-Journal dokumentiert Trade-offs (`why`, `alternatives_rejected`)
- Claim-Log dokumentiert Behauptungen und ihren Verifikationszustand
- Vermischung würde beide Semantiken korrumpieren
- Verifikations-Trail eines Claims braucht Historie (alle Updates chronologisch)
- Append-only bleibt sauber: alte "unverified"-Zeilen bleiben stehen,
  neue "verified"-Zeilen erscheinen mit gleicher ID
