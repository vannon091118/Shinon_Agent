#!/usr/bin/env python3
"""
render_prosa.py — stdin-JSON → RenderedProsa-JSON (Brücke für die Web-UI)

`POST /api/prosa` in shinon-server.mjs schickt eine NarrativeSpec als JSON
über stdin hierher. Dieses Skript ruft die REINE render()-Funktion der
Prosa-Engine auf und druckt RenderedProsa als JSON. Keine State-Mutation
(render() ist pure — die harte Architekturauflage bleibt gültig).

Input  (stdin): NarrativeSpec als JSON-Objekt
                 {task, tone, max_sentences, user_fact, system_state,
                  allowed_actions, language, extra}
Output (stdout):
                 {"text", "source", "spec_hash", "sentence_count", "mood"}
                 oder {"error": "…"} (exit code 1) bei ungültiger Spec.

Modell-/Binary-Auflösung (read-only, zentralisiert in model_bootstrap.py):
  1. SHINON_PROSA_MODEL            (expliziter Modell-Pfad)
  2. $SHINON_HOME/models/<default>
llama-cli via PATH oder $SHINON_HOME/bin (llama-cli / llama-cli.exe).
Fehlt Modell oder Binary, fällt render() deterministisch auf den
Mood-Fallback zurück (source="fallback"). Download ist opt-in
(python3 model_bootstrap.py --model / --llama-cli) — nie automatisch.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "fusion-main"))

from fusion.shinon.shinon_prosa import render  # noqa: E402
from model_bootstrap import resolve_model_path, resolve_llama_cli  # noqa: E402


def main() -> int:
    raw = sys.stdin.read()
    try:
        spec = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid JSON: {e}"}))
        return 1
    if not isinstance(spec, dict):
        print(json.dumps({"error": "spec must be a JSON object"}))
        return 1
    try:
        r = render(
            spec,
            model_path=str(resolve_model_path()),
            llama_cli=resolve_llama_cli(),
        )
    except ValueError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1
    print(json.dumps({
        "text": r.text,
        "source": r.source,
        "spec_hash": r.spec_hash,
        "sentence_count": r.sentence_count,
        "mood": r.mood,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
