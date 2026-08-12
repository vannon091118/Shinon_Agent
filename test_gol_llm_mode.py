#!/usr/bin/env python3
"""
GOL TEST 2 — LLM Mode: Buffy = Kontrolleinheit, Runtime + LLM = alles.

ABLAUF:
  1. User-Input (vage, 1 Satz) → PreProcessor → OpenRouter LLM → Structured JSON
  2. Structured JSON → Shinon → Character Context
  3. Shinon Output → Promtguard → Claims
  4. Claims → KARMA FalsificationGate → Results
  5. ALLES wird in /tmp/gol-test2-output/ gespeichert

BUFFY DARF: Dieses Kontroll-Skript schreiben. Nichts sonst.
BUFFY DARF NICHT: Game of Life Code schreiben, Claims formulieren, Struktur vorgeben.
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "fusion-main")
sys.path.insert(0, "karma-main")
sys.path.insert(0, "limen-main/src")

from fusion.event_runtime import ControlPlaneRuntime

# ── Output-Verzeichnis ────────────────────────────────────────────
OUT_DIR = Path("/tmp/gol-test2-output")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── User Input — EXTREM vage, kein Kontext ────────────────────────
# Das LLM bekommt NUR diesen Text + den STRUCTURING_SYSTEM_PROMPT.
USER_INPUT = (
    "Bau ein Game of Life als Node.js CLI Programm mit Terminal Rendering "
    "und Conway Regeln. Es soll Tests haben."
)

# ── Timestamp ─────────────────────────────────────────────────────
TS = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

async def main():
    print("=" * 70)
    print("GOL TEST 2 — LLM Mode (Buffy = Kontrolleinheit)")
    print(f"Start: {TS}")
    print(f"User Input: {USER_INPUT}")
    print("=" * 70)

    # ── Runtime mit PreProcessor im auto-Mode ──────────────────
    # auto = PreProcessor prüft needs_structuring() → True → LLM call
    print("\n[1] ControlPlaneRuntime(preprocess_mode='auto')")
    rt = ControlPlaneRuntime(preprocess_mode="auto")
    print(f"    Preprocessor stats: {rt.get_preprocessor_stats()}")

    # ── Pipeline ausführen ─────────────────────────────────────
    print(f"\n[2] rt.process(user_input)...")
    result = await rt.process(USER_INPUT)

    # ── Ergebnisse sammeln ─────────────────────────────────────
    print(f"\n[3] RESULTS")
    print(f"    Correlation ID: {result.correlation_id}")
    print(f"    Original Input: {result.original_input[:100]}...")
    print(f"    Processed Input: {result.input_text[:150]}...")
    print(f"    Claims: {len(result.claims)}")
    print(f"    Falsification Results: {len(result.falsification_results)}")

    # Preprocess info
    pp = result.preprocess_info
    if pp:
        print(f"\n    PREPROCESSOR:")
        print(f"      Mode:    {pp.get('mode')}")
        print(f"      Goal:    {pp.get('goal', 'N/A')[:80]}")
        print(f"      Reqs:    {pp.get('requirements_count', 0)}")
        print(f"      Tests:   {pp.get('tests_count', 0)}")

    # Claims (erste 10)
    print(f"\n    CLAIMS ({len(result.claims)} total, showing first 10):")
    for i, claim in enumerate(result.claims[:10]):
        cid = getattr(claim, 'id', f'CLAIM-{i+1:03d}')
        ctext = getattr(claim, 'claim', str(claim))[:100]
        cstatus = getattr(claim, 'status', '?')
        print(f"      [{cid}] [{cstatus}] {ctext}")

    # Falsification
    if result.falsification_results:
        print(f"\n    FALSIFICATION ({len(result.falsification_results)} results):")
        for fr in result.falsification_results[:10]:
            cid = getattr(fr, 'claim_id', '?')
            fres = getattr(fr, 'result', '?')
            fconf = getattr(fr, 'confidence', '?')
            fgate = getattr(fr, 'gate_version', '?')
            print(f"      [{cid}] {fres} (conf={fconf}, gate={fgate})")

    if result.error:
        print(f"\n    ERROR: {result.error}")

    # ── Alles auf Disk speichern ────────────────────────────────
    output = {
        "test": "GOL_TEST_2_LLM_MODE",
        "timestamp": TS,
        "correlation_id": result.correlation_id,
        "user_input": USER_INPUT,
        "original_input": result.original_input,
        "processed_input": result.input_text,
        "preprocess_info": pp,
        "claims": [
            {
                "id": getattr(c, 'id', f'CLAIM-{i+1:03d}'),
                "claim": getattr(c, 'claim', str(c)),
                "status": getattr(c, 'status', '?'),
                "confidence": getattr(c, 'confidence', None),
            }
            for i, c in enumerate(result.claims)
        ],
        "falsification_results": [
            {
                "claim_id": getattr(fr, 'claim_id', '?'),
                "result": getattr(fr, 'result', '?'),
                "confidence": getattr(fr, 'confidence', None),
                "gate_version": getattr(fr, 'gate_version', None),
                "evidence": str(getattr(fr, 'evidence', ''))[:200],
            }
            for fr in result.falsification_results
        ],
        "error": result.error,
        "aggregator": result.aggregator_summary,
    }

    out_file = OUT_DIR / f"result-{TS}.json"
    out_file.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n[4] Full result saved to {out_file}")

    # Auch als lesbare Text-Datei
    txt_file = OUT_DIR / f"result-{TS}.txt"
    with open(txt_file, "w") as f:
        f.write(f"GOL TEST 2 — LLM Mode\n")
        f.write(f"{'='*70}\n")
        f.write(f"Timestamp: {TS}\n")
        f.write(f"Correlation: {result.correlation_id}\n")
        f.write(f"User Input: {USER_INPUT}\n\n")
        f.write(f"PREPROCESSOR: {pp}\n\n")
        f.write(f"CLAIMS ({len(result.claims)}):\n")
        for i, c in enumerate(result.claims):
            f.write(f"  [{getattr(c, 'id', i)}] {getattr(c, 'claim', str(c))}\n")
        f.write(f"\nFALSIFICATION ({len(result.falsification_results)}):\n")
        for fr in result.falsification_results:
            f.write(f"  [{getattr(fr, 'claim_id', '?')}] {getattr(fr, 'result', '?')}\n")
    print(f"    Text report saved to {txt_file}")

    # ── Stats ─────────────────────────────────────────────────
    pp_stats = rt.get_preprocessor_stats()
    print(f"\n[5] STATS")
    print(f"    PreProcessor: {pp_stats}")
    print(f"    Pipeline: {result.summary()}")
    print(f"\n{'='*70}")
    print(f"GOL TEST 2 COMPLETE — All work done by Runtime + LLM")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
