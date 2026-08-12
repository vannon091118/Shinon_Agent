#!/usr/bin/env python3
"""
shinon_fusion_bridge.py — Node→Python Bridge for shinon-server.mjs

Called as subprocess by shinon-server.mjs.
  stdin:  JSON {"message": "...", "session_id": "...", "history": [...], "personality": {...}}
  stdout: JSON {"reply": "...", "model": "...", "source": "fusion", "character_context": {...}, ...}
  stderr: logging only (ignored by caller)

Exit codes:
  0 = OK, reply field is populated
  1 = hard error (bad input / unexpected exception)
  2 = fusion ran but produced no usable reply → caller should use LIMEN fallback with character_context
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

# ── Path Setup ──────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE / "fusion-main"))
sys.path.insert(0, str(_HERE / "karma-main"))
sys.path.insert(0, str(_HERE / "limen-main" / "src"))

# ── Logging → stderr only (stdout is JSON channel) ──────────────────────
logging.basicConfig(
    stream=sys.stderr,
    level=logging.WARNING,
    format="[fusion-bridge] %(levelname)s %(message)s",
)
log = logging.getLogger("shinon_fusion_bridge")


# ── Helpers ─────────────────────────────────────────────────────────────

def _exit_error(msg: str, code: int = 1) -> None:
    print(json.dumps({"error": msg}), flush=True)
    sys.exit(code)


def _safe_str(value: object, maxlen: int = 200) -> str:
    s = str(value) if not isinstance(value, str) else value
    return s[:maxlen]


def _extract_reply(shinon_output: object) -> str:
    if shinon_output is None:
        return ""
    if isinstance(shinon_output, dict):
        return str(shinon_output.get("reply", "") or "")
    for attr in ("reply", "text", "content"):
        v = getattr(shinon_output, attr, None)
        if v and isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _extract_character_context(shinon_output: object) -> dict:
    """Pull out character context fields that enhance the LIMEN system prompt."""
    ctx: dict = {}
    if shinon_output is None:
        return ctx

    src: dict = shinon_output if isinstance(shinon_output, dict) else {}
    if not isinstance(shinon_output, dict):
        for attr in ("character_context", "attitudes", "emotional_state",
                     "tone_directive", "should_confront"):
            v = getattr(shinon_output, attr, None)
            if v is not None:
                src[attr] = v.to_dict() if hasattr(v, "to_dict") else v

    cc = src.get("character_context") or {}
    if isinstance(cc, dict):
        ctx["tone_directive"]  = cc.get("tone_directive", "")
        ctx["should_confront"] = bool(cc.get("confront", False))
        ctx["emotional_state"] = cc.get("emotional_state", "neutral")
        attitudes = cc.get("attitudes") or {}
        if isinstance(attitudes, dict):
            ctx["attitudes"] = {k: round(float(v), 1)
                                for k, v in attitudes.items()
                                if isinstance(v, (int, float))}
        patterns = cc.get("patterns") or []
        if patterns:
            ctx["patterns"] = [
                p.get("type", "?") if isinstance(p, dict) else str(p)
                for p in patterns[:5]
            ]

    handoff = src.get("handoff_to_promtguard") or {}
    if isinstance(handoff, dict):
        pi = handoff.get("processed_input", "")
        if pi and pi != src.get("reply", ""):
            ctx["processed_input_summary"] = _safe_str(pi, 300)

    if not ctx.get("tone_directive"):
        ctx["tone_directive"] = _safe_str(
            src.get("tone_directive", "NORMAL_INTERACTION: Match user sentiment."))
    if "should_confront" not in ctx:
        ctx["should_confront"] = bool(src.get("should_confront", False))
    if not ctx.get("emotional_state"):
        ctx["emotional_state"] = _safe_str(src.get("emotional_state", "neutral"))

    return ctx


def _extract_model(shinon_output: object) -> str:
    if shinon_output is None:
        return "fusion"
    if isinstance(shinon_output, dict):
        return str(shinon_output.get("model", "fusion") or "fusion")
    m = getattr(shinon_output, "model", None)
    return str(m) if m else "fusion"


# ── Main async runner ────────────────────────────────────────────────────

async def run(data: dict) -> dict:
    message     = data.get("message", "").strip()
    session_id  = data.get("session_id") or "default"
    history     = data.get("history") or []
    personality = data.get("personality") or {}

    if not message:
        raise ValueError("message is empty")

    from fusion.event_runtime import ControlPlaneRuntime  # type: ignore

    # Use synthetic pre-processor when personality is configured (no extra LIMEN pre-call)
    preprocess_mode = "synthetic" if personality else "auto"

    rt = ControlPlaneRuntime(preprocess_mode=preprocess_mode)
    result = await rt.process(
        user_text=message,
        session_id=session_id,
        history=history,
    )

    reply             = _extract_reply(result.shinon_output)
    model             = _extract_model(result.shinon_output)
    character_context = _extract_character_context(result.shinon_output)
    claims_count      = len(result.claims) if result.claims else 0
    correlation_id    = result.correlation_id or ""

    out: dict = {
        "reply":             reply,
        "model":             model,
        "source":            "fusion",
        "character_context": character_context,
        "claims_count":      claims_count,
        "correlation_id":    correlation_id,
    }
    if result.error:
        out["warning"] = _safe_str(result.error, 500)
    return out


# ── Entry Point ──────────────────────────────────────────────────────────

def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        _exit_error(f"Invalid JSON on stdin: {e}", code=1)

    try:
        result = asyncio.run(run(data))
    except ValueError as e:
        _exit_error(str(e), code=1)
    except Exception as e:
        log.exception("Fusion pipeline error")
        # code 2 → Node caller falls back to direct LIMEN call
        _exit_error(f"Fusion pipeline error: {e}", code=2)

    reply = result.get("reply", "")
    if not reply or not reply.strip():
        # Fusion ran successfully but ShinonEngine produced no LLM reply.
        # Node will use character_context to enhance the LIMEN system prompt.
        result["reply"] = ""
        print(json.dumps(result), flush=True)
        sys.exit(2)

    print(json.dumps(result), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
