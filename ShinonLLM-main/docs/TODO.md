# ShinonLLM - TODO (Aus Chat-Session 2026-04-05)

## Vision (Aktueller Scope 0.3.0-alpha)

> **Die meisten KI-Assistenten sind digitale Handtaschenhalter. Wir bauen was mit Charakter.**

Shinon ist keine freundliche Servicekraft. Sie ist eine Persona mit Gedächtnis, Haltungen und der Fähigkeit, dich zur Rede zu stellen wenn du dich widersprichst.

**Core-Prinzipien:**

1. Runtime denkt, LLM formuliert
2. Two-Tier Memory (Fakten + Patterns)
3. Hot/Mid/Cold Zones
4. Fail-closed (aber menschenlesliche Fehlermeldungen)

---

## Abgeschlossen (Heute)

- [x] Doku-Härtung: 6 veraltete Dateien gelöscht
- [x] Neue README.md (AGENTS-Stil, mit Index)
- [x] HANDSHAKE_CURRENT_STATE.md (Scope 0.3.0)
- [x] ARCHITECTURE_OVERVIEW.md (Two-Tier + Zones)
- [x] MEMORY_POLICY.md (erweitert für 0.3.0)
- [x] Test-Fix: router.spec.ts `stream: true` ergänzt
- [x] Menschenlesliche Fehlermeldungen (`humanErrors.ts`)
- [x] Platzhalter für neue Module erstellt:
  - `character/core/identity.ts`
  - `character/attitudes/tracker.ts`
  - `character/experience/patterns.ts`
  - `character/experience/twoTierMemory.ts`
  - `character/state/emotional.ts`
  - `character/prompts/generator.ts`
  - `memory/zones/hotZone.ts`
  - `memory/zones/midZone.ts`
  - `memory/zones/coldZone.ts`

---

## Offen: Phase 0 (Kritische Lücken - Status Apr 2026)

### SQLite-Datenbank Status (READ-ONLY)

**Aktuell persistiert (funktioniert):**

- `session_memory_entries` - Nur Chat-Verlauf via `sessionPersistence.ts`
- Pfad: `%LOCALAPPDATA%\ShinonLLM\session-memory.sqlite`
- Schema: v1 (nur `session_memory_entries` Tabelle)

**Nicht persistiert (In-Memory only / verloren bei Neustart):**

- `personal_facts` - Tier 1 existiert nur als Type-Definition in `twoTierMemory.ts`
- `patterns` - Tier 2 existiert nur als Type-Definition in `patterns.ts`
- `pattern_links` - Verknüpfungen nicht implementiert
- `attitudes` - Haltungs-Tracking nicht implementiert

**Unimplementierte Module (PLACEHOLDERS):**

- `memory/zones/hotZone.ts` - TODO: Implementiere Hot Zone mit SQLite-Backend
- `memory/zones/midZone.ts` - TODO: Implementiere Mid Zone mit Score-basierter Selektion
- `memory/zones/coldZone.ts` - TODO: Implementiere Cold Zone mit Pattern-Extraktion
- `character/experience/patterns.ts` - `extractPattern()`, `findContradictions()`, `scoreConfidence()` geben nur Defaults zurück
- `character/experience/twoTierMemory.ts` - `queryTier1()`, `queryTier2()`, `linkTier1ToTier2()` sind leere Stubs
- `memory/src/longterm/memoryStore.ts` - Reine In-Memory-Implementierung, keine SQLite-Persistenz

### Kritische Blocker für 0.3.0

1. **LongTerm Memory hat kein SQLite-Backend** - Alles fliegt beim Neustart
2. **Pattern Engine ist Geister-Code** - Schöne Typen, keine Logik
3. **Memory Zones sind Luftschlösser** - Cold Zone ruft Funktionen die `null`/`[]` returnieren
4. **Schema v2 existiert nicht** - `PRAGMA user_version` bleibt bei 1

---

## Offen: Phase 1 (DB Schema v2)

### SQLite Migration (v1 → v2)

**Neue Tabellen:**

- [ ] `personal_facts` - Tier 1 (konkrete Fakten)
  - `id`, `content`, `category`, `created_at`, `session_id`
- [ ] `patterns` - Tier 2 (Pattern-Anker)
  - `id`, `anchor`, `type`, `confidence`, `examples_json`, `created_at`
- [ ] `pattern_links` - Verknüpfungen Tier 1 ↔ Tier 2
  - `pattern_id`, `fact_id`, `relation_type`
- [ ] `attitudes` - Haltungs-Tracking pro User
  - `user_id`, `dimension`, `score`, `updated_at`, `history_json`

**Migration-Plan:**

1. [ ] Backup existing database
2. [ ] Create new tables
3. [ ] Migrate `session_memory_entries` → `personal_facts`
4. [ ] Set `PRAGMA user_version = 2`
5. [ ] Verify with `npm run verify:backend`

**Fail-closed:** Schema v3+ → Blocked until explicit migration support

---

## Offen: Phase 2 (Zone Management)

### Hot Zone (Current Session)

- [ ] Implementiere `HotZone.load()` - ungefilterter Zugriff
- [ ] Implementiere `HotZone.append()` - neue Einträge speichern
- [ ] Transition zu Mid Zone bei Session-Ende

### Mid Zone (Last 10 Sessions)

- [ ] Implementiere `MidZone.load()` - Score-basierte Selektion (top 20%)
- [ ] Implementiere `MidZone.promoteFromHot()` - Aus Hot Zone übernehmen
- [ ] Implementiere `MidZone.demoteToCold()` - Altes nach Cold Zone verschieben

### Cold Zone (Archive)

- [ ] Implementiere `ColdZone.archive()` - Sessions archivieren
- [ ] Implementiere `ColdZone.extractPatterns()` - Pattern-Härtung
- [ ] Implementiere `ColdZone.loadPatterns()` - Anker abrufen

**Zone-Übergänge:**
- Session End → Hot → Mid (Session 11 → Cold)
- Mid → Cold nach 10 Sessions
- Cold → Pattern-Extraktion (automatisch)

---

## Offen: Phase 3 (Pattern Engine)

### Pattern-Erkennung

- [ ] Implementiere `extractPattern(fact)`
  - Typ-Erkennung: `preference`, `commitment`, `relationship`, `contradiction`
- [ ] Implementiere `findContradictions(factA, factB)`
  - Beispiel: "Anna" vs "Lisa" Inkonsistenz erkennen
- [ ] Implementiere `scoreConfidence(pattern)`
  - Frequency + Recency + Consistency

### Pattern-Typen (MVP)

| Typ | Beispiel | Trigger |
|-----|----------|---------|
| `preference` | "Ich mag Pizza" | "mag", "liebe", "hasse" |
| `commitment` | "Ich werde das morgen tun" | "werde", "verspreche", "bis [Datum]" |
| `relationship` | "Meine Freundin Anna" | "Freund*", "Partner*", "mit [Name]" |
| `contradiction` | "War mit Anna, jetzt mit Lisa" | Zwei relationship-Fakten mit unterschiedlichen Personen |

**Confrontation-Szenario (Anna→Lisa):**
1. 1.4.: "Ich bin glücklich mit Anna" → relationship pattern (Anna)
2. 5.3.: "Hab Date mit Lisa" → relationship pattern (Lisa)
3. System erkennt: Beziehung mit verschiedenen Personen in <30 Tagen
4. Konfidenz > 0.8 → Confrontation-Modus
5. Shinon: "Warte, am 1.4. warst du mit Anna glücklich. Jetzt Date mit Lisa?"

---

## Offen: Phase 4 (Attitude Tracker)

### Haltungs-Dimensionen

- [ ] `warmth`: -10 (kalt) bis +10 (warm)
- [ ] `respect`: -10 (verachtend) bis +10 (wertschätzend)
- [ ] `patience`: -10 (genervt) bis +10 (nachsichtig)
- [ ] `trust`: -10 (misstrauisch) bis +10 (vertrauend)

### Update-Regeln

| Event | Warmth | Respect | Patience | Trust |
|-------|--------|---------|----------|-------|
| Inkonsistenz gefunden | -1 | -2 | -2 | -3 |
| Versprechen eingehalten | +1 | +2 | 0 | +3 |
| Versprechen gebrochen | -2 | -3 | -2 | -5 |
| Wiederholte Muster | +1 (positiv) / -1 (negativ) | ±2 | ±1 | ±2 |

### Confrontation Logic

- [ ] `shouldConfront(state, confidence)`
- Trigger: `patience < 5` UND `confidence > 0.8`
- [ ] Implementiere Threshold-Checks
- [ ] Attitude-Persistence (über Sessions)

---

## Offen: Phase 5 (Prompt Generator)

### "Shinons Gedanken"-Prompts

- [ ] Template-Engine für Prompt-Generierung
- [ ] Integration: Attitude-Werte → Tondirektive
- [ ] Integration: Emotional State → Tondirektive
- [ ] Integration: Patterns → explizite Addressierung
- [ ] Integration: Relevant Facts → Kontext

### Prompt-Struktur

```text
Du bist Shinon. Du hast mit diesem User {{interactionCount}} Interaktionen.

Deine aktuelle Haltung:
- Wärme: {{attitude.warmth}}/10
- Respekt: {{attitude.respect}}/10
- Geduld: {{attitude.patience}}/10
- Vertrauen: {{attitude.trust}}/10

Erkannte Muster:
{{patterns}}

Relevante Erinnerungen:
{{facts}}

Deine aktuelle Stimmung: {{emotionalState}}
{{toneDirective}}

User Input: {{userText}}

Antworte als Shinon. Dein Ton sollte deine Haltung widerspiegeln.
Wenn Geduld < 4, sei direkter/sarkastischer.
Wenn ein Muster mit Konfidenz > 0.8 erkannt wurde, adressiere es explizit.
```

### Confrontation Prompt

- [ ] Spezieller Prompt für Konfrontations-Modus
- [ ] Template: "Ich muss dich auf etwas ansprechen..."
- [ ] Referenzierung vergangener Fakten mit Datum

---

## Offen: Phase 6 (Integration)

### Orchestrator

- [ ] Ersetze `buildRuntimePlan` (aktuell Regex) durch Pattern-Engine
- [ ] Integriere Attitude-Check in Pipeline
- [ ] Integriere Prompt-Generator

### Chat Route

- [ ] Verbinde `sessionPersistence` mit Two-Tier Memory
- [ ] Speichere Fakten in Tier 1
- [ ] Extrahiere Patterns nach Session-Ende

### Backend Router

- [ ] Berücksichtige Attitude für Routing-Entscheidungen
- [ ] Fail-closed mit menschenleslichen Fehlermeldungen

---

## Qualitäts-Gates (Release 0.3.0)

Vor Release müssen alle Gates grün sein:

- [ ] `npm run test:determinism` → PASS
- [ ] `npm run verify:backend` → PASS
- [ ] `npm run test:e2e` → PASS

**Neue Gates (optional für 0.3.0):**

- [ ] Pattern-Engine determinism check
- [ ] Attitude calculation determinism check
- [ ] Confrontation scenario E2E test (Anna→Lisa)

---

## Dokumentation (Inhalt aus Chat-Session)

### Besprochene Konzepte

- **Two-Tier Memory**: Schicht 1 (Personal/Fakten) + Schicht 2 (Pattern/Anker)
- **Hot/Mid/Cold Zones**: Zeitbasierte Zone mit Pattern-Härtung
- **Decay als Vermenschlichung**: Nicht FIFO, sondern Relevanz-basiert
- **Confrontation Logic**: Shinon spricht Inkonsistenzen an
- **Runtime denkt, LLM formuliert**: LLM ist nur Text-Engine
- **Determinismus**: Replay-Hash muss identisch bleiben
- **Fail-closed**: Bei Unsicherheit abbrechen, nicht raten

### Architektur-Entscheidungen

- Lokales LLM (0.5B-7B), keine Cloud-Abhängigkeit
- SQLite für Persistence
- Character-System mit festem Core + dynamischen Attitudes
- Pattern-Engine für Muster-Erkennung
- Menschenlesliche Fehlermeldungen (statt kryptischer Codes)

---

## Nächste Schritte

1. **Starte mit Phase 1**: SQLite Schema v2 erstellen
2. **Tägliche Checkpoints**: 30-min Sync nach jedem Tag
3. **Fokus**: Pattern-Engine und Attitude-Tracker sind kritisch für 0.3.0

---

*Erstellt aus Chat-Session am 2026-04-05*
*Scope: 0.3.0-alpha "Real Persona with Two-Tier Memory"*

---

## Bekannte Fehler (Heute entdeckt)

### Kritisch: Unimplementierte SQLite-Persistenz

**Status: Daten gehen bei Neustart verloren**

| Modul | Datei | Problem | Impact |
|-------|-------|---------|--------|
| LongTerm Memory | `memory/src/longterm/memoryStore.ts:229` | Reine In-Memory, kein SQLite | Alle Fakten fliegen bei Restart |
| Hot Zone | `memory/src/zones/hotZone.ts:32` | TODO: Implementiere Hot Zone | Ungefilterter Session-Zugriff nicht vorhanden |
| Mid Zone | `memory/src/zones/midZone.ts:31` | TODO: Implementiere Mid Zone | Keine Score-basierte Selektion |
| Cold Zone | `memory/src/zones/coldZone.ts:36` | TODO: Implementiere Cold Zone | Keine Pattern-Härtung, kein Archiv |
| Pattern Engine | `character/src/experience/patterns.ts:45` | `extractPattern()` gibt immer `null` | Keine Pattern-Erkennung |
| Pattern Engine | `character/src/experience/patterns.ts:50` | `findContradictions()` gibt immer `false` | Keine Inkonsistenzerkennung |
| Pattern Engine | `character/src/experience/patterns.ts:59` | `scoreConfidence()` unimplementiert | Keine Konfidenz-Berechnung |
| Two-Tier Memory | `character/src/experience/twoTierMemory.ts:37` | `queryTier1()` gibt `null` | Tier 1 nicht abfragbar |
| Two-Tier Memory | `character/src/experience/twoTierMemory.ts:42` | `queryTier2()` gibt `null` | Tier 2 nicht abfragbar |
| Two-Tier Memory | `character/src/experience/twoTierMemory.ts:47` | `linkTier1ToTier2()` leer | Keine Verknüpfung möglich |

**Fix-Priorität:**
1. **HÖCHSTE**: LongTerm Memory SQLite-Backend (Blocker für 0.3.0)
2. **HOCH**: Pattern Engine Implementierung (Core Feature)
3. **MITTEL**: Memory Zones mit SQLite-Anbindung
4. **NIEDRIG**: TypeScript-Syntax-Fixes in Platzhaltern

### TypeScript-Fehler in Platzhaltern
- [ ] `character/src/attitudes/tracker.ts`: `readonly history` → `ReadonlyArray` (Syntax-Fehler)
- [ ] `character/src/experience/patterns.ts`: `readonly examples` → `ReadonlyArray` (Syntax-Fehler)
- [ ] `character/src/prompts/generator.ts`: `generateConfrontationPrompt` Parameter-Typ korrigieren

### Dokumentation Lint-Fehler (Optional)
- [ ] `README.md`: Table-Spacing korrigieren (line 20)
- [ ] `HANDSHAKE_CURRENT_STATE.md`: Blanks around lists/tables
- [ ] `MEMORY_POLICY.md`: Multiple blank lines entfernen (line 148)

### Test-Fehler (Bestehend)
- [ ] `tests/unit/router.spec.ts`: `fallbackMetadata` fehlte `stream: true` (bereits behoben, aber verify prüfen)

### Build/Integration
- [ ] Neue `character/` Module in tsconfig.json aufnehmen
- [ ] Export-Statements für neue Module hinzufügen
- [ ] `npm run build` muss ohne Fehler durchlaufen
- [ ] `npm run verify:backend` muss grün sein

---

## Fehlende Integrationen

### Orchestrator
- [ ] `orchestrateTurn.ts`: `buildRuntimePlan` durch Pattern-Engine ersetzen
- [ ] `buildPrompt.ts`: Statischen System-Prompt durch dynamischen Character-Prompt ersetzen
- [ ] Attitude-Check vor LLM-Call einbauen
- [ ] Prompt-Generator Integration

### Memory-Pipeline
- [ ] `sessionPersistence.ts`: Neue Tabellen-Schema (v2) implementieren
- [ ] `retrieveContext.ts`: Two-Tier Abfrage-Logik
- [ ] `scoreContext.ts`: Erweiterte Scoring-Dimensionen (Frequency, Impact)

### Backend
- [ ] `chat.ts`: Neue Memory-System Integration
- [ ] `humanErrors.ts`: In bestehende Fehler-Handling Pipeline integrieren

### Shared
- [ ] `index.ts` oder `barrel exports` für neue `character/` Module
- [ ] Type-Definitions exportieren

---

## Pre-Flight Checklist (Vor Phase 1)

Bevor du mit dem SQLite Schema v2 anfängst, stelle sicher:

- [ ] Alle TypeScript-Fehler in Platzhaltern behoben
- [ ] `npm run build` läuft durch
- [ ] `npm run verify:backend` ist grün
- [ ] Neue Module sind korrekt verlinkt
- [ ] Keine broken imports

**Warum das wichtig ist:**
Wenn du mit einem broken Build in Phase 1 startest, weißt du nie ob Schema-Fehler vom neuen Code oder vom alten Zustand kommen. Sauberer Start = sauberes Debugging.
