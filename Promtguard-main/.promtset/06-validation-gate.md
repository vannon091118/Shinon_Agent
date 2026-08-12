# R06 — Validierungs-Gate (Konsistenz + Abschluss-Check)

**Neue Tasks dürfen keinen früheren Entscheidungen widersprechen. Bevor ein Task als "erledigt" markiert wird, prüft der Agent gegen ALLE Vorentscheidungen.**

## Konsistenz-Prüfung (vor Task-Build)

1. **Entscheidungen laden:** Alle Einträge aus `decision-journal.jsonl`
2. **Task analysieren:** Was will der Task ändern?
3. **Widerspruch suchen:** Sagt eine frühere Decision etwas ANDERES über diese Datei/Logik?
4. **Wenn Widerspruch:** Task pausieren, User informieren, Decision aktualisieren oder Task anpassen
5. **Wenn kein Widerspruch:** Task freigeben

## Abschluss-Prüfung (vor "completed")

1. **Hat der Task das gemacht, was im Scope stand?** (Nicht mehr, nicht weniger)
2. **Widerspricht das Ergebnis einer früheren Decision?** (Konsistenz-Check oben)
3. **Sind alle code_refs mit file:line belegt?** (Kein "siehe Code")
4. **Hat der Coder einen Context-Token ausgegeben?** (Sonst ist der Task unsichtbar)
5. **Kompiliert das Projekt?** (Syntax-Check nach jedem Edit-Batch)

## Beispiele

| Entscheidung im Journal | Task | Prüfung |
|---|---|---|
| "perHeadTax hat kein Hard Cap" | "Füge Hard Cap 500 in EconConfig ein" | ⚠️ WIDERSPRUCH → Task pausieren |
| "28/28 EngineMirror Coverage" | "Migriere EngineSeams.entitiesAvailable()" | ⚠️ BEREITS ERLEDIGT → Task ablehnen |
| "Wallets hat 14 Arrays" | "Zähle Wallets-Arrays" | ✅ Bestätigt alte Entscheidung |

## Implementierung

```bash
# Syntax-Check nach Coder
cd Projekt && mvn compile -q 2>&1 | head -20

# Task im Index markieren
python3 .promtset/tools/promptgen.py task-done TASK-NNN \
  --agent coder-1 --status completed \
  --summary "..." --code-refs '[...]'
```

## Bei Fehlern

- Compile-Fehler → Task geht zurück an Coder (NICHT completed)
- Decision-Konflikt → Task geht zurück an Promter (manuelle Klärung)
- Fehlender Context-Token → Task gilt als NICHT abgeschlossen
