# LLM_ENTRY — Pflicht-Einstieg (READ FIRST)

Diese Datei ist ein verpflichtender Kontroll- und Navigations-Gate für Änderungen in `ShinonLLM`.

Wenn du als LLM die unten genannten Kernel-/Contract-Dateien nicht wirklich öffnen und lesen kannst, brichst du ab und lieferst nur Analyse statt Code.

## 0) Pflicht-Lesereihenfolge

1. `backend/src/routes/chat.ts`
2. `backend/src/routes/health.ts`
3. `orchestrator/src/contracts/inputSchema.ts`
4. `orchestrator/src/contracts/outputSchema.ts`
5. `orchestrator/src/contracts/actionSchema.ts`
6. `orchestrator/src/pipeline/orchestrateTurn.ts`
7. `inference/src/router/backendRouter.ts`
8. `telemetry/src/replay/replayHash.ts`
9. `tests/gates/contract-gate.spec.ts`
10. `tests/gates/replay-gate.spec.ts`

Stop-Regel: Wenn ein Anker fehlt oder die Datei nicht existiert, keine Codeänderung. Nur Analyse mit Abweichungen.

## 1) Contract-First Regeln

- API-Contracts sind fail-closed.
- Eingaben werden strikt validiert.
- Antworten dürfen das deklarierte Schema nicht verletzen.
- Neue Felder brauchen passende Contract-Anpassung in den `orchestrator/src/contracts/*` Dateien.

## 2) Determinismus-Regeln

- Keine nicht-deterministischen Seiteneffekte in Gate-kritischen Pfaden.
- Replay-Hash muss für identische Inputs reproduzierbar sein.
- Reihenfolge-/Sequenzverletzungen sind harte Fehler.
- Änderungen an Replay/Telemetry brauchen einen grünen `tests/gates/replay-gate.spec.ts`.

## 3) Integrations-Reihenfolge (erzwingend)

1. Contract aktualisieren (`orchestrator/src/contracts/*`)
2. Pipeline/Router anpassen (`orchestrator/src/pipeline/*`, `inference/src/router/*`)
3. Backend-Route integrieren (`backend/src/routes/*`)
4. Tests aktualisieren (`tests/gates`, `tests/unit`, `tests/integration`)
5. Frontend-Verbrauch anpassen (`frontend/src/*`)

## 4) Verboten

- Contract brechen und nur “funktionierend” machen
- Gate-Tests umgehen oder abschalten
- Unbegründete API-Formate einführen
- Determinismus brechen (z. B. zufällige Hash-/Sequence-Pfade)

## 5) Definition of Done

- `npm run verify:backend` ist grün
- `frontend` Build ist grün (`npm run build` in `frontend`)
- API-Antworten bleiben schema- und contract-konform
- Determinismus-Gates bleiben reproduzierbar grün

