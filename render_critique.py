#!/usr/bin/env python3
"""
render_critique.py — stdin-JSON → CritiqueResult-JSON (Brücke für Evil-Twin-Scripts)

Koppelt den Mirror-Thinker (typisiertes objections[]-Schema) an render_critique():

    * Der Mirror-Thinker liefert die KRITIK als STRUKTUR (verdict + objections[]).
    * Dieses Skript validiert sie deterministisch (validate_objections, fail-closed)
      und rendert daraus die scharfe Prosa via render_critique() (reine Funktion,
      null State-Mutation — die harte Architekturauflage bleibt).
    * Das Gate konsumiert `verdict` + `objections` (deterministisch, NIE aus der
      Prosa). Die WIDERSPRUCH-Datei (.md) bekommt NUR `prose.text`.

Input  (stdin):
    {
      "verdict": "FUNDAMENTAL" | "OBERFLÄCHLICH",
      "objections": [
        {
          "kind": "assumption|contradiction|missing_evidence|scope|architecture|determinism",
          "target": "WAS kritisiert wird (Komponente/Claim/Schritt)",
          "claim": "die angegriffene Behauptung/Annahme",
          "argument": "die Gegenthese / das Gegenargument",
          "required_evidence": "welcher Beleg fehlt (optional)"
        },
        ...
      ]
    }
    (Variable Länge. Markdown-Code-Fences um das JSON werden tolerant entfernt.)

Output (stdout):
    {
      "verdict": "...",
      "objections": [{"kind","target","claim","argument","required_evidence"}, ...],
      "prose": {"text","source","spec_hash","sentence_count","mood"}
    }
    oder {"error": "..."} (exit 1) bei ungültiger Eingabe.

Modell-/Binary-Auflösung wie render_prosa.py (model_bootstrap, read-only).
Fehlt Modell oder Binary, fällt render_critique deterministisch auf den
Mood-Fallback zurück (prose.source == "fallback").
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "fusion-main"))

from fusion.shinon.shinon_prosa import (  # noqa: E402
    CRITIQUE_VERDICTS,
    render_critique,
    validate_objections,
)
from model_bootstrap import resolve_model_path, resolve_llama_cli  # noqa: E402

# Wenn der Zwilling NICHTS Fundamentales fand (OBERFLÄCHLICH + leere
# objections), liefern wir einen deterministischen No-Op-Result statt zu
# crashen. Der Verdict wird als Anker vorangestellt, damit auch dieser Pfad
# den Drift-Marker (FUNDAMENTAL|OBERFLÄCHLICH) erfüllt.
_NO_OBJECTION_TEXT = (
    "{verdict}. Kein fundamentaler Widerspruch — nur Oberflächlichkeiten."
)


def _extract_json(raw: str) -> str:
    """Entferne ggf. umschließende Markdown-Code-Fences (```json ... ```)."""
    s = raw.strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def _serialize(result) -> dict:
    return {
        "verdict": result.verdict,
        "objections": [
            {
                "kind": o.kind,
                "target": o.target,
                "claim": o.claim,
                "argument": o.argument,
                "required_evidence": o.required_evidence,
            }
            for o in result.objections
        ],
        "prose": {
            "text": result.prose.text,
            "source": result.prose.source,
            "spec_hash": result.prose.spec_hash,
            "sentence_count": result.prose.sentence_count,
            "mood": result.prose.mood,
        },
    }


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(_extract_json(raw) if raw.strip() else "{}")
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid JSON: {e}"}, ensure_ascii=False))
        return 1
    if not isinstance(data, dict):
        print(json.dumps({"error": "critique must be a JSON object"}))
        return 1

    verdict = (data.get("verdict") or "FUNDAMENTAL").strip().upper()
    if verdict not in CRITIQUE_VERDICTS:
        print(json.dumps(
            {"error": f"verdict must be one of {CRITIQUE_VERDICTS}"},
            ensure_ascii=False,
        ))
        return 1

    # Deterministischer Validator: rohe objections[] → typisierte Objections.
    # Fail-closed: ungültiges kind/Feld → ValueError → error-JSON (exit 1).
    objections_raw = data.get("objections")
    try:
        objections = validate_objections(objections_raw if objections_raw is not None else [])
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1

    if not objections:
        # Contract-Invariante: FUNDAMENTAL ⇔ ≥1 Einwand. FUNDAMENTAL ohne
        # Einwand ist ein Widerspruch — fail-closed statt self-contradictory
        # No-Op-Result. Nur OBERFLÄCHLICH darf leer sein.
        if verdict == "FUNDAMENTAL":
            print(json.dumps(
                {"error": "FUNDAMENTAL requires at least one objection"},
                ensure_ascii=False,
            ))
            return 1
        # OBERFLÄCHLICH ohne Einwände → deterministischer No-Op-Result.
        result = {
            "verdict": verdict,
            "objections": [],
            "prose": {
                "text": _NO_OBJECTION_TEXT.format(verdict=verdict),
                "source": "fallback",
                "spec_hash": "",
                "sentence_count": 1,
                "mood": "adversarial",
            },
        }
    else:
        try:
            cr = render_critique(
                objections,
                verdict=verdict,
                model_path=str(resolve_model_path()),
                llama_cli=resolve_llama_cli(),
            )
        except ValueError as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
            return 1
        result = _serialize(cr)

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
