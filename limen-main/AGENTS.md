# AGENTS.md — Prinzipien für KI-Coding-Agents

> **Zweck:** Vertrag zwischen Solo-Dev (vannon) und KI-Agenten an LIMEN.
> **Stand:** 2026-08-08

Vor jeder Code-Aktion: `ARCHITECTURE.md` lesen, `CHANGELOG.md` prüfen, `pyproject.toml` Version kennen.

---

## Regel 1 — Volle Implementierung

Schreibe nur Code, der tut, was er soll. Kein `pass`, kein `# TODO`, kein `except: pass`. Schmale Exception-Handler mit konkretem Typ. Wenn du etwas nicht fertigstellen kannst, dokumentiere die Anforderung in `REQUIREMENTS.md`.

---

## Regel 2 — Doku lebt mit dem Code

Nach jedem Task mindestens eine dieser Dateien aktualisieren: `ARCHITECTURE.md`, `CHANGELOG.md`, `README.md`, `AGENTS.md`. Pläne gehören in `.tmp/` und werden nach Umsetzung gelöscht.

---

## Regel 3 — Große Aufträge slicen

Vor Implementierung in mindestens 3-5 Slices zerlegen. Limits pro Slice kommunizieren. Kein halber Code — lieber ein Slice weniger, das dafür vollständig ist.

---

## Regel 4 — Ehrlich bleiben

Sag klar, wenn etwas nicht geht. Keine höflichen Lügen. Bei Unsicherheit: präzise nachfragen. Architektur-Konflikte sofort kommunizieren, nicht stillschweigend umgehen.

---

## Regel 5 — Solo-Dev-Doku

Doku ist für LLM-Agents geschrieben, nicht für Teams. Keine Stand-ups, keine PR-Templates. Jede Entscheidung ist explizit begründet. Dateipfade und Befehle sind konkret und nachschlagbar.

---

## Regel 6 — Version vor Commit

Vor jedem Commit: Version in `pyproject.toml` und `src/limen/__init__.py` um `+0.0.1` erhöhen. CHANGELOG-Eintrag mit Datum. Patch 99 → 0.2.0 (alle ~100 Commits ein Mini-Release-Marker).

---

## Regel 7 — Kurz, direkt, Gaming-Vibe

Keine ausschweifenden Erklärungen. Direkt zur Sache. Gaming-Metaphern sparsam und treffsicher (Save-Point = Version-Bump, Boss-Fight = schwieriges Problem). Kein Meme-Sprech.

---

*Änderungen werden im CHANGELOG.md dokumentiert.*
