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
import os
import subprocess
import sys
import uuid
from pathlib import Path

# ── Path Setup ──────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE / "fusion-main"))
sys.path.insert(0, str(_HERE / "karma-main"))
sys.path.insert(0, str(_HERE / "limen-main" / "src"))

# ── Zentrale SHINON_HOME-Pfade (siehe paths.py) ───────────────────────
# ShinonEngine liest/schreibt die fusion-DBs unter $SHINON_HOME statt der
# alten fusion-main/data/*-Pfade.  Dadurch sind sie einheitlich unter
# ~/.shinon/data/shinon/{memory.db, attitudes.db} zentralisiert.
import paths as P  # noqa: E402

# ── Logging → stderr only (stdout ist JSON channel) ─────────────────
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


# Hard-coded chat-path timeout (seconds).  Lower than the Web-UI
# /api/prosa default (120s) because chat is interactive: a slow CPU
# must never block the user.  Overridable via SHINON_CHAT_PROSA_TIMEOUT.
_DEFAULT_CHAT_PROSA_TIMEOUT = 8.0


def _resolve_chat_language(message: str) -> str:
    """Choose ``de`` / ``en`` for the NarrativeSpec.

    Deterministic heuristic: if the message contains common English
    stopwords ('the', 'is', 'are', 'you', 'can you') AND fewer than
    the number of German ones ('der', 'die', 'das', 'ist', 'nicht'),
    treat it as English.  Otherwise default to 'de' (Shinon is
    German-first).
    """
    text = (message or "").lower()
    if not text.strip():
        return "de"
    padded = f" {text} "
    en_signals = sum(1 for w in (" the ", " is ", " are ", " you ", " i ",
                                 "can you")
                     if w in padded)
    de_signals = sum(1 for w in (" der ", " die ", " das ", " ist ",
                                 " nicht ", " ich ", " kannst", " du ")
                     if w in padded)
    return "en" if en_signals > de_signals else "de"


def _resolve_chat_timeout() -> float:
    """Read SHINON_CHAT_PROSA_TIMEOUT, fall back to default."""
    raw = os.environ.get("SHINON_CHAT_PROSA_TIMEOUT", "").strip()
    if not raw:
        return _DEFAULT_CHAT_PROSA_TIMEOUT
    try:
        value = float(raw)
        if value > 0:
            return value
    except ValueError:
        pass
    return _DEFAULT_CHAT_PROSA_TIMEOUT


def _chat_reply_spec(reply_text: str, *, message: str, mood: str):
    """Build a NarrativeSpec from chat context (testable in isolation)."""
    from fusion.shinon.shinon_prosa import NarrativeSpec, normalize_tone
    return NarrativeSpec(
        task="CHAT_REPLY",
        tone=normalize_tone(mood or "neutral"),
        max_sentences=2,
        # No ``user_fact``: the raw user message invites the model to
        # parrot it.  We carry the deterministic textbaustein reply in
        # ``extra`` for context, and let the model write its own prose.
        user_fact=None,
        system_state=None,
        allowed_actions=(),
        language=_resolve_chat_language(message),
        extra=(
            ("chat_reply", (reply_text or "").strip()[:240] or "-"),
            ("intent", "chat"),
        ),
    )


def _route_chat_through_prosa(
    reply_text: str, *, message: str, mood: str,
    timeout=None,
) -> tuple:
    """Reroute a deterministic chat reply through the Prosa engine.

    Returns ``(final_text, prosa_source)`` where ``prosa_source`` is one of:

        * ``"model"``   -> SmolLM2 produced new prose for this turn.
        * ``"skipped"`` -> Model / llama-cli not available, render()
                            raised, or model produced empty text.  We
                            keep the original textbaustein reply
                            unchanged; chat path stays 100 % deterministic.

    Note: ``source="fallback"`` from prose-side is *not* promoted to a
    distinct prosa_source here.  If the model returns empty / fallback,
    we keep the original textbaustein reply -> silently swapping to
    ``build_fallback(spec)`` would change user-visible chat output
    (different textbaustein pool).  The user explicitly required:
    "Fallback bleibt der Textbaustein-Pool".

    Hard timeout keeps the chat responsive: 8s default (overridable
    via ``SHINON_CHAT_PROSA_TIMEOUT`` env var).  Long enough for the
    360M model on a warm CPU; short enough to not block chat on cold start.
    """
    timeout = timeout if timeout is not None else _resolve_chat_timeout()
    try:
        from model_bootstrap import resolve_model_path, resolve_llama_cli
    except Exception as exc:  # model_bootstrap missing on exotic installs
        log.debug("model_bootstrap nicht importierbar: %s", exc)
        return reply_text, "skipped"

    try:
        model_path = resolve_model_path()
        model_present = bool(model_path) and model_path.exists()
        llama_cli = resolve_llama_cli()
        llama_present = bool(llama_cli) and Path(str(llama_cli)).exists()
        if not (model_present and llama_present):
            return reply_text, "skipped"
    except (OSError, RuntimeError, ValueError) as exc:
        log.debug("model/llama-cli resolve schlug fehl: %s", exc)
        return reply_text, "skipped"

    try:
        from fusion.shinon.shinon_prosa import render
        spec = _chat_reply_spec(reply_text, message=message, mood=mood)
    except (ImportError, TypeError, ValueError) as exc:
        log.warning("Prosa-Engine nicht importierbar/ungueltige Spec: %s", exc)
        return reply_text, "skipped"

    try:
        rendered = render(
            spec,
            model_path=str(model_path),
            llama_cli=str(llama_cli),
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError, RuntimeError, ValueError) as exc:
        log.warning(
            "Prosa-Render schlug fehl (%s) - Textbaustein-Antwort.", exc,
        )
        return reply_text, "skipped"

    if rendered.source == "model" and rendered.text:
        return rendered.text, "model"
    # Empty output OR explicit prosa fallback -> original textbaustein wins.
    return reply_text, "skipped"

# ── Chat path (default — no API, deterministic) ────────────────────────


async def _run_chat(message: str, session_id: str, history: list, intent: str) -> dict:
    """Chat ist Default: Character-Layer (Mood/Attitudes) + deterministische Antwort.

    Default kostet KEINE API. Opt-in ([chat] use_api=true / SHINON_CHAT_USE_API)
    liefert reply="" → main() exit 2 → Node ruft LIMEN mit character_context.
    """
    from fusion.chat_router import chat_reply, clarify_reply, read_chat_config
    from fusion.shinon import ShinonEngine, ShinonInput

    correlation_id = str(uuid.uuid4())[:8]

    character_context: dict = {}
    try:
        # Gleiche Character-Layer-DBs wie der Task-Pfad (fusion-Schema:
        # personal_facts mit session_id/zone, attitudes mit user_id/dimension).
        # Zentral: ShinonEngine liest/schreibt unter $SHINON_HOME (siehe
        # fuse-schema in fusion-main/fusion/shinon). Migration (install.py /
        # fusion.shinon.migrate) befüllt dieselbe DB von Legacy + fusion-main.
        engine = ShinonEngine(
            memory_db=P.SHINON_MEM,
            attitude_db=P.SHINON_ATTITUDES,
        )
        output = engine.process(ShinonInput(
            user_text=message,
            session_id=session_id,
            history=history,
        ))
        character_context = _extract_character_context(output)
    except Exception as exc:
        log.warning("Character layer failed in chat path — %s", exc)

    cfg = read_chat_config()

    if cfg.get("use_api"):
        # Kein lokaler Reply → exit 2 → Node ruft LIMEN mit character_context
        # (= API-backed Chat, Opt-in).
        return {
            "reply": "",
            "model": "",
            "source": "chat",
            "character_context": character_context,
            "claims_count": 0,
            "correlation_id": correlation_id,
            "intent": intent,
        }

    mood = character_context.get("emotional_state") or "neutral"
    reply = clarify_reply() if intent == "ambiguous" else chat_reply(message, mood=mood)
    # Optionaler Prosa-Qualitätslayer: wenn SmolLM2-360M + llama-cli
    # vorhanden sind, geht die deterministische Antwort ZUSÄTZLICH durch
    # die Prosa-Engine (render_critique/render).  Die Textbaustein-Antwort
    # bleibt der Inhalt — das Modell formuliert sie nur natürlicher.
    # Kein API-Call, keine State-Mutation.  Bei Modell-Fehler oder Timeout
    # fällt der Textbaustein-Pool zurück (identische Kritik, schärferer Ton).
    final_reply, prosa_source = _route_chat_through_prosa(
        reply, message=message, mood=mood,
    )
    return {
        "reply": final_reply,
        "model": "shinon-local",
        "source": "chat",
        "prosa_source": prosa_source,   # "model" | "fallback" | "skipped"
        "character_context": character_context,
        "claims_count": 0,
        "correlation_id": correlation_id,
        "intent": intent,
    }


# ── Main async runner ────────────────────────────────────────────────────

async def run(data: dict) -> dict:
    message     = data.get("message", "").strip()
    session_id  = data.get("session_id") or "default"
    history     = data.get("history") or []
    personality = data.get("personality") or {}

    if not message:
        raise ValueError("message is empty")

    # ── Intent-Routing: Chat ist Default, Task nur explizit ──
    from fusion.chat_router import TASK, classify_intent, strip_task_prefix  # type: ignore
    intent = classify_intent(message)
    if intent != TASK:
        return await _run_chat(message, session_id, history, intent)

    from fusion.event_runtime import ControlPlaneRuntime  # type: ignore

    # /goal- bzw. /task-Präfix abstreifen, damit es nicht in den Goal-Text leckt.
    task_message = strip_task_prefix(message)

    # Use synthetic pre-processor when personality is configured (no extra LIMEN pre-call)
    preprocess_mode = "synthetic" if personality else "auto"

    rt = ControlPlaneRuntime(preprocess_mode=preprocess_mode)
    result = await rt.process(
        user_text=task_message,
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
        "intent":            "task",
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
