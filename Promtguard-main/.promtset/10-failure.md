# R10 — Fehler-Transparenz

**Kein stilles Sterben.** Jeder Fehler wird gemeldet, bevor er weitergericht wird.

## Was ist ein "stilles Sterben"?

- Ein Agent halluziniert eine Datei, die nicht existiert → sagt nichts
- Ein Build schlägt fehl → Coder sagt "fertig" ohne Compile-Check
- Eine Diskrepanz wird gefunden → Agent ignoriert sie (RULE-1-VIOLATION)
- Ein Research-JSON hat fehlende Felder → wird trotzdem ingestiert

## Melde-Pflicht

| Ereignis | Melde-Weg | Frist |
|---|---|---|
| Compile-Fehler | User im Output | Sofort |
| Decision-Konflikt | User + decision-journal | Vor nächstem Task |
| Verwaiste Task-ID | User | Bei Entdeckung |
| Diskrepanz in Research | Folge-Research (RULE 1) | Bei Entdeckung |
| Schema-Validierung fehlgeschlagen | User + ingest abgelehnt | Bei ingest |

## Verstoss

Ein nicht gemeldeter Fehler, der später von einem anderen Agenten entdeckt wird:
- Fehler wird sofort gemeldet
- Ursprungs-Agent wird im decision-journal vermerkt
- Wiederholung → Task-Pflicht für den Agenten (wenn möglich)
