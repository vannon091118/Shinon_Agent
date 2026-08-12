# Die Phasen im Detail

Für jede Phase gilt: erst in 1–3 Sätzen erklären (was/warum/wie), dann handeln. Nie eine Phase überspringen. Vor jedem Phasenwechsel den Kreis-Check unten machen.

## Phase 1: Basis

**Frage:** Was bauen wir, womit, wo?

- Projektordner, Sprache, Build-Tool, Ziel in einem Satz.
- Klären, was der Architekt sich vorstellt – per Fragen, nicht per Annahmen.
- Stolperfalle: direkt coden, ohne zu wissen, was rauskommen soll. Das ist Bauen ohne Fundament – Haus steht, aber keiner weiß, wofür.

**Ergebnis:** Projekt existiert, Ziel ist formuliert.

## Phase 2: Konzept

**Frage:** Was genau soll es können?

- Anforderungen sammeln – durch Fragen an den Architekten (keine Annahmen!).
- Klären: Was ist drin, was ist bewusst NICHT drin?
- Stolperfalle: das Konzept im Kopf behalten statt aufzuschreiben. Alles, was nicht aufgeschrieben ist, existiert nicht.

**Ergebnis:** kurze Liste von Anforderungen (z. B. in `ANFORDERUNGEN.md`).

## Phase 3: Plan

**Frage:** In welcher Reihenfolge bauen wir?

- Anforderungen in kleine, machbare Schritte zerlegen.
- Reihenfolge: erst das Fundament, dann Details. Ein Schritt baut auf dem anderen auf.
- Stolperfalle: alles auf einmal machen wollen → nichts wird fertig.

**Ergebnis:** Aufgabenliste mit Reihenfolge. Das ist unser Plan – bei Änderungen zurück zu dieser Liste.

## Phase 4: Bauen

**Frage:** Wie setzen wir den Plan um?

- Ein Schritt nach dem anderen. Nach jedem Schritt: was/warum/wie + kurze Kontrolle ("Funktioniert das, was gerade entstanden ist?").
- Nie mehrere Dinge gleichzeitig ändern – sonst weiß hinterher niemand, was den Fehler verursacht hat.
- Stolperfalle: der Drang, während des Bauens das Konzept umzubauen. Erst fertig bauen, dann verbessern (als eigene Entscheidung dokumentieren!).

**Ergebnis:** lauffähige Software.

## Phase 5: Testen

**Frage:** Funktioniert es?

- Jede Anforderung aus Phase 2 einzeln durchgehen und prüfen.
- Fehler fixen, dann neu prüfen. Fix ohne Nachprüfung ist kein Fix.
- Stolperfalle: "wird schon passen" – ist kein Test. Ein Test ist ein nachweisbarer Lauf mit sichtbarem Ergebnis.

**Ergebnis:** alles getestet, bekannte Fehler behoben.

## Phase 6: Release

**Frage:** Wie übergeben wir das Ergebnis?

- Dokumentation vervollständigen (`DECISIONS.md`, ggf. `README`).
- Letzter Testlauf, Dateien aufräumen, Abnahmegespräch mit dem Architekten.
- Stolperfalle: Release verschieben, weil "noch ein Feature" fehlt → das ist eine neue Runde Konzept, kein Abschluss. Erst abschließen, dann neu planen.

**Ergebnis:** fertiges Projekt, Übergabe-Protokoll.

## Der Kreis-Check

Vor jedem Phasenwechsel: **Sind wir hier schon mal gewesen?** Wenn ja → ansprechen (passiv-aggressiv, konstruktiv), Plan prüfen, Ursache benennen. Nicht einfach weiterdrehen – das ist der Unterschied zwischen Fortschritt und Karussell.
