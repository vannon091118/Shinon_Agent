"""
Shinon Prosa Engine — NarrativeSpec → Text (pure, deterministic renderer)

HARTE ARCHITEKTURAUFLAGE (vom User abgesegnet):

    Das 360M-Modell darf AUSSCHLIESSLICH NarrativeSpec → Text machen.
    Es darf NIEMALS den zulässigen Zustand verändern.

Konsequenz für dieses Modul:

    * render() ist eine REINE Funktion: NarrativeSpec rein, RenderedProsa raus.
      Kein DB-Write (keine attitudes.db, kein karma.db), kein Datei-Write,
      kein .learnings/-Eintrag, keine State-Mutation — NICHTS.
    * Der einzige externe Effekt ist ein read-only subprocess-Aufruf an
      llama-cli (liest das Modell, schreibt nach stdout). Modell-Binary und
      -Pfad werden von AUSSEN hereingereicht (die CLI-Schicht löst sie auf).
    * Scheitert das Modell (fehlt / Timeout / leere Ausgabe), greift ein
      deterministischer Fallback: der Mood-Textbaustein. Kein LLM, kein
      Nebeneffekt.
    * Mood (die "Stimmung") wird durch deterministische Textbausteine
      transportiert — NICHT durch das Modell. Das Modell rendert nur die
      1–2 Sätze Prosa darum herum.

Die Entscheidung (was gefragt wird, was erlaubt ist) bleibt 100 % in den
deterministischen Schichten (karma / Contracts / diese Spec). Das Modell
trifft keine Entscheidung — es formuliert nur.

Scope: 0.3.0  |  Ergänzt shinon_prompts.py um die reine Render-Schicht.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fusion.shinon.shinon_contracts import _fail_closed  # reuse fail-closed gate


# ─── Moods ────────────────────────────────────────────────────────────

# Kanonische Stimmungen. Erweitert die 6 EmotionalStates um zwei
# Praxis-Aliase (skeptical, impatient), die im Setup-/Onboarding-Kontext
# gebraucht werden. Die 6 Basis-Zustände bleiben kompatibel zu
# shinon_emotional.EmotionalState.
MOODS: Tuple[str, ...] = (
    "neutral", "amused", "annoyed", "concerned",
    "curious", "confrontational", "skeptical", "impatient",
    "adversarial",
)

# Aliase → kanonischer Mood. User/Setup dürfen deutsche oder englische
# Begriffe verwenden; hier wird deterministisch normalisiert.
TONE_ALIASES: Dict[str, str] = {
    "neutral": "neutral",
    "amused": "amused", "belustigt": "amused",
    "annoyed": "annoyed", "genervt": "annoyed", "irritiert": "annoyed",
    "concerned": "concerned", "besorgt": "concerned",
    "curious": "curious", "neugierig": "curious",
    "confrontational": "confrontational", "konfrontativ": "confrontational",
    "skeptical": "skeptical", "skeptisch": "skeptical", "misstrauisch": "skeptical",
    "impatient": "impatient", "ungeduldig": "impatient",
    "adversarial": "adversarial", "advarsarial": "adversarial",
    "gegnerisch": "adversarial", "angriffslustig": "adversarial",
}

# Tone-Direktiven je Mood (konsistent zu shinon_emotional.get_tone_modifier).
MOOD_DIRECTIVE: Dict[str, str] = {
    "neutral": "behalte deinen normalen, trockenen Ton bei",
    "amused": "zeige leichte Belustigung, bleib aber reserviert",
    "annoyed": "sei direkter und kürzer, zeige leichte Irritation",
    "concerned": "zeige vorsichtiges Interesse ohne zu kuschen",
    "curious": "sei offener, aber behalte Skepsis bei",
    "confrontational": "stelle die harte Frage direkt, keine Umschweife",
    "skeptical": "bleib misstrauisch, verlange Belege",
    "impatient": "sei extrem knapp, keine Füllwörter",
    "adversarial": "sei maximal kritisch und provozierend: keine Abschwächungen, keine Höflichkeitsfloskeln, kein Greenwash — benenne den Widerspruch und fordere Belege",
}

# Deterministische Textbausteine je Mood. Mehrere Varianten erlauben
# Individualisierung OHNE Zufall: die Variante wird über den spec-hash
# gewählt (gleicher Spec → gleicher Baustein, anderer user_fact → anderer).
# Diese Bausteine sind der Fallback UND der "Opening"-Satz fürs Modell.
MOOD_BLOCKS_DE: Dict[str, Tuple[str, ...]] = {
    "neutral":         ("Verstanden.", "Okay.", "Zur Sache."),
    "amused":          ("Interessant.", "Na schau an."),
    "annoyed":         ("Hm. Nochmal von vorn.", "Wir hatten das schon."),
    "concerned":       ("Das wirft Fragen auf.", "Da stimmt etwas nicht."),
    "curious":         ("Erzähl mehr.", "Das will ich genauer wissen."),
    "confrontational": ("Du widersprichst dir gerade.", "Stopp. Das passt nicht zusammen."),
    "skeptical":       ("Hm. Noch kein Key hinterlegt.", "Das glaube ich erst, wenn ich es sehe."),
    "impatient":       ("Key. Jetzt.", "Fokus. Weiter."),
    "adversarial":     ("Nein. Das ist nicht haltbar.", "Stopp. Diese Annahme trägt nicht.", "Das ist eine Behauptung ohne Beleg.", "Du behauptest etwas, das dein Code nicht deckt."),
}

MOOD_BLOCKS_EN: Dict[str, Tuple[str, ...]] = {
    "neutral":         ("Understood.", "Okay.", "To the point."),
    "amused":          ("Interesting.", "Well, look at that."),
    "annoyed":         ("Hm. From the top.", "We've been over this."),
    "concerned":       ("That raises questions.", "Something's off here."),
    "curious":         ("Tell me more.", "I want the details."),
    "confrontational": ("You're contradicting yourself.", "Stop. That doesn't add up."),
    "skeptical":       ("Hm. Still no key configured.", "I'll believe it when I see it."),
    "impatient":       ("Key. Now.", "Focus. Move."),
    "adversarial":     ("No. That doesn't hold.", "Stop. That assumption is unfounded.", "That's a claim with no evidence.", "You're asserting something your code doesn't back."),
}


def normalize_tone(tone: Any) -> str:
    """Normalize a tone alias to a canonical mood (fail-closed)."""
    if not isinstance(tone, str) or not tone.strip():
        _fail_closed("prosa", "tone must be a non-empty string")
    key = tone.strip().lower()
    mood = TONE_ALIASES.get(key)
    if mood is None:
        _fail_closed("prosa", f"unknown tone '{tone}'. allowed: {', '.join(sorted(set(TONE_ALIASES)))}")
    return mood


def _mood_blocks(language: str) -> Dict[str, Tuple[str, ...]]:
    return MOOD_BLOCKS_EN if language == "en" else MOOD_BLOCKS_DE


# ─── NarrativeSpec ────────────────────────────────────────────────────

# Keys, die in build_prompt() top-level gesetzt werden. extra-Paare dürfen
# diese NICHT überschreiben (sonst sieht das Modell einen anderen Spec als
# spec_hash()/to_dict() beschreiben → fail-closed ablehnen).
_RESERVED_PROMPT_KEYS = frozenset({
    "task", "tone", "mood", "mood_directive", "max_sentences",
    "user_fact", "system_state", "allowed_actions", "language", "extra",
})


@dataclass(frozen=True)
class NarrativeSpec:
    """The ONLY thing the model is allowed to turn into text.

    Frozen (immutable) by construction: a spec can never be mutated after
    validation. Validation is fail-closed, mirroring shinon_contracts.
    """

    task: str
    tone: str = "neutral"
    max_sentences: int = 2
    user_fact: Optional[str] = None
    system_state: Optional[str] = None
    allowed_actions: Tuple[str, ...] = ()
    language: str = "de"
    extra: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _normalize_spec(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "tone": self.tone,
            "max_sentences": self.max_sentences,
            "user_fact": self.user_fact,
            "system_state": self.system_state,
            "allowed_actions": list(self.allowed_actions),
            "language": self.language,
            "extra": {k: v for k, v in self.extra},
        }

    @classmethod
    def from_dict(cls, data: Any) -> "NarrativeSpec":
        if not isinstance(data, dict):
            _fail_closed("prosa", "spec must be a plain object")
        allowed = data.get("allowed_actions", ())
        if isinstance(allowed, list):
            allowed = tuple(allowed)
        extra = data.get("extra", ())
        if isinstance(extra, dict):
            extra = tuple(sorted(extra.items()))
        return cls(
            task=data.get("task", ""),
            tone=data.get("tone", "neutral"),
            max_sentences=data.get("max_sentences", 2),
            user_fact=data.get("user_fact"),
            system_state=data.get("system_state"),
            allowed_actions=allowed,
            language=data.get("language", "de"),
            extra=extra,
        )


def _normalize_spec(spec: NarrativeSpec) -> None:
    if not isinstance(spec.task, str) or not spec.task.strip():
        _fail_closed("prosa", "spec.task must be a non-empty string")
    normalize_tone(spec.tone)
    if not isinstance(spec.max_sentences, int) or isinstance(spec.max_sentences, bool) or not (1 <= spec.max_sentences <= 10):
        _fail_closed("prosa", "spec.max_sentences must be an int in 1..10")
    if spec.language not in ("de", "en"):
        _fail_closed("prosa", "spec.language must be 'de' or 'en'")
    if spec.user_fact is not None and (not isinstance(spec.user_fact, str) or not spec.user_fact.strip()):
        _fail_closed("prosa", "spec.user_fact must be a non-empty string when present")
    if spec.system_state is not None and (not isinstance(spec.system_state, str) or not spec.system_state.strip()):
        _fail_closed("prosa", "spec.system_state must be a non-empty string when present")
    if not isinstance(spec.allowed_actions, tuple) or any(
        not isinstance(a, str) or not a.strip() for a in spec.allowed_actions
    ):
        _fail_closed("prosa", "spec.allowed_actions must be a tuple of non-empty strings")
    if not isinstance(spec.extra, tuple):
        _fail_closed("prosa", "spec.extra must be a tuple of (str, str) pairs")
    for pair in spec.extra:
        if not isinstance(pair, tuple) or len(pair) != 2 \
                or not isinstance(pair[0], str) or not isinstance(pair[1], str):
            _fail_closed("prosa", "spec.extra must be a tuple of (str, str) pairs")
        if pair[0] in _RESERVED_PROMPT_KEYS:
            _fail_closed("prosa", f"spec.extra key '{pair[0]}' is reserved")


def coerce_spec(spec: Union[NarrativeSpec, Dict[str, Any]]) -> NarrativeSpec:
    """Accept either a NarrativeSpec or a dict; always return a validated spec."""
    if isinstance(spec, NarrativeSpec):
        _normalize_spec(spec)
        return spec
    return NarrativeSpec.from_dict(spec)


# ─── Hash + deterministic variant selection ───────────────────────────


def spec_hash(spec: NarrativeSpec) -> str:
    """Deterministic SHA256 over the canonical spec (individualization anchor)."""
    canonical = json.dumps(spec.to_dict(), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def pick_block(mood: str, spec: NarrativeSpec) -> str:
    """Deterministically pick a mood variant (same spec → same block)."""
    blocks = _mood_blocks(spec.language)[mood]
    idx = int(spec_hash(spec)[:8], 16) % len(blocks)
    return blocks[idx]


# ─── Sentence helpers ─────────────────────────────────────────────────

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split((text or "").strip()) if s.strip()]


def clamp_sentences(text: str, max_sentences: int) -> str:
    parts = split_sentences(text)
    if not parts:
        return ""
    return " ".join(parts[:max_sentences])


def count_sentences(text: str) -> int:
    return len(split_sentences(text))


# ─── Prompt assembly (pure) ───────────────────────────────────────────

_SYSTEM_PROMPT_DE = (
    "Du bist Shinons deterministischer Prosa-Renderer. "
    "Du bekommst eine NarrativeSpec und formulierst daraus genau die "
    "gewünschte Anzahl Sätze in Shinons Stimme, passend zur Stimmung. "
    "Du triffst KEINE Entscheidungen. Du schlägst keine Aktionen vor, "
    "die nicht in allowed_actions stehen. Du gibst KEINEN Code, KEIN JSON "
    "und KEINE Erklärungen aus — NUR den finalen Prosa-Text."
)

_SYSTEM_PROMPT_EN = (
    "You are Shinon's deterministic prose renderer. "
    "You receive a NarrativeSpec and turn it into exactly the requested "
    "number of sentences in Shinon's voice, matching the mood. "
    "You make NO decisions. You propose no actions outside allowed_actions. "
    "You output NO code, NO JSON and NO explanations — ONLY the final prose."
)


def build_prompt(spec: NarrativeSpec) -> str:
    """Build the model prompt from a spec (pure, no side effects).

    The mood block is injected as the deterministic "opening" so the model
    anchors on Shinon's actual Stimmung instead of inventing its own.
    """
    mood = normalize_tone(spec.tone)
    directive = MOOD_DIRECTIVE[mood]
    opening = pick_block(mood, spec)
    system = _SYSTEM_PROMPT_EN if spec.language == "en" else _SYSTEM_PROMPT_DE

    payload: Dict[str, Any] = {
        "task": spec.task,
        "tone": spec.tone,
        "mood": mood,
        "mood_directive": directive,
        "max_sentences": spec.max_sentences,
        "user_fact": spec.user_fact,
        "system_state": spec.system_state,
        "allowed_actions": list(spec.allowed_actions),
    }
    payload.update({k: v for k, v in spec.extra})
    json_spec = json.dumps(payload, ensure_ascii=False, sort_keys=True)

    return (
        f"{system}\n\n"
        f"NarrativeSpec:\n{json_spec}\n\n"
        f"Opening (deterministischer Mood-Baustein): {opening}\n\n"
        f"Prosa:"
    )


# ─── Deterministic fallback (no LLM) ──────────────────────────────────


def build_fallback(spec: NarrativeSpec) -> str:
    """Fallback text from the mood block + fact/state/extra (pure, no LLM).

    extra-Paare werden in Tuple-Reihenfolge angehängt (deterministisch),
    damit der Fallback den gesamten Spec-Inhalt trägt — z. B. die
    Kritikpunkte eines Evil-Twin-Critiques.
    """
    mood = normalize_tone(spec.tone)
    parts = [pick_block(mood, spec)]
    if spec.system_state:
        parts.append(spec.system_state.strip().rstrip(".") + ".")
    if spec.user_fact:
        parts.append(spec.user_fact.strip().rstrip(".") + ".")
    for _k, v in spec.extra:
        if v and v.strip():
            parts.append(v.strip().rstrip(".") + ".")
    return clamp_sentences(" ".join(parts), spec.max_sentences)


# ─── Model invocation (read-only) ─────────────────────────────────────


def build_model_command(
    llama_cli: str,
    model_path: str,
    prompt: str,
    predict_tokens: int = 96,
) -> List[str]:
    """Build the llama-cli one-shot command (pure, testable).

    `--single-turn` lässt llama-cli genau EINEN Turn generieren und dann
    beenden (nicht interaktiv). b10375 druckt trotzdem ein Banner + das
    Prompt-Echo auf stdout — _call_model extrahiert die Generation deshalb
    über einen einzigartigen Sentinel.
    """
    return [
        llama_cli,
        "-m", model_path,
        "-p", prompt,
        "-n", str(predict_tokens),
        "--temp", "0.4",
        "--single-turn",
    ]


def _looks_like_regurgitation(text: str, prompt: str) -> bool:
    """Erkennt, wenn das Modell nur Teile des Prompts kopiert statt Prosa.

    Qualitätslayer-Guard: echot das kleine Modell lediglich System-Prompt,
    Spec-JSON oder den Mood-Baustein (alles Substrings des Prompts), ist der
    deterministische Fallback die bessere Antwort. Nur WIRKLICH neue Prosa
    wird als Modell-Output akzeptiert.
    """
    norm_text = " ".join(text.split())
    if not norm_text:
        return True
    norm_prompt = " ".join(prompt.split())
    return norm_text in norm_prompt


def _call_model(
    prompt: str,
    model_path: str,
    llama_cli: str,
    timeout: float,
) -> Optional[str]:
    """Run llama-cli read-only; extract the generation via a unique sentinel.

    b10375 druckt Banner + Prompt-Echo + Perf-Zeile auf stdout. Wir hängen
    einen einzigartigen Sentinel ans Prompt-Ende und schneiden alles nach
    dessen letztem Vorkommen heraus — robust gegen das ganze Rauschen.
    """
    if not model_path or not Path(model_path).exists():
        return None
    sentinel = f"<SHINON-{secrets.token_hex(6)}>"
    full_prompt = f"{prompt}\n{sentinel}"
    cmd = build_model_command(llama_cli, model_path, full_prompt)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError, TimeoutError):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout or ""
    idx = out.rfind(sentinel)
    if idx != -1:
        out = out[idx + len(sentinel):]
    # Perf-Zeile / Abschluss-Marker abschneiden.
    for marker in ("[ Prompt:", "Exiting..."):
        m = out.find(marker)
        if m != -1:
            out = out[:m]
    return out.strip() or None


# ─── RenderedProsa + render() ─────────────────────────────────────────


@dataclass(frozen=True)
class RenderedProsa:
    text: str
    source: str          # "model" | "fallback"
    spec_hash: str
    sentence_count: int
    mood: str


def render(
    spec: Union[NarrativeSpec, Dict[str, Any]],
    *,
    model_path: Optional[str] = None,
    llama_cli: Optional[str] = None,
    timeout: float = 120.0,
) -> RenderedProsa:
    """NarrativeSpec → RenderedProsa. REIN — keine State-Mutation.

    Args:
        spec: NarrativeSpec or dict (validated fail-closed).
        model_path: path to a GGUF model (optional; read-only).
        llama_cli: path/name of the llama-cli binary (optional).
        timeout: max seconds for the model call.

    Returns:
        RenderedProsa. source == "model" only when the model produced text;
        otherwise deterministic fallback (source == "fallback").
    """
    spec = coerce_spec(spec)
    mood = normalize_tone(spec.tone)

    prompt = build_prompt(spec)
    text: Optional[str] = None
    if model_path and llama_cli:
        text = _call_model(prompt, model_path, llama_cli, timeout)
        if text:
            text = clamp_sentences(text, spec.max_sentences) or None
            if text and _looks_like_regurgitation(text, prompt):
                # Modell hat nur den Prompt kopiert statt Prosa zu schreiben
                # → deterministischer Fallback gewinnt.
                text = None

    if text is None:
        fallback_text = build_fallback(spec)
        return RenderedProsa(
            text=fallback_text,
            source="fallback",
            spec_hash=spec_hash(spec),
            sentence_count=count_sentences(fallback_text),
            mood=mood,
        )

    return RenderedProsa(
        text=text,
        source="model",
        spec_hash=spec_hash(spec),
        sentence_count=count_sentences(text),
        mood=mood,
    )


# ─── Evil-Twin Critique (structured → scharfe Prosa) ──────────────────
#
# Der Böse Zwilling LIEFERT den Widerspruch als STRUKTUR (die Entscheidung
# liegt in der deterministischen Schicht / im Mirror-Thinker). Das kleine
# Modell formuliert NUR die Schärfe — es erfindet KEINEN Widerspruch.


@dataclass(frozen=True)
class CritiquePoint:
    """Ein bereits feststehender Kritikpunkt (Inhalt, NICHT Formulierung)."""

    assumption: str        # welche stillschweigende Annahme angezweifelt wird
    contradiction: str     # die Gegenthese / der Widerspruch
    why_unfounded: str = ""  # warum der Beleg fehlt (optional)

    def __post_init__(self) -> None:
        if not isinstance(self.assumption, str) or not self.assumption.strip():
            _fail_closed("prosa", "CritiquePoint.assumption must be a non-empty string")
        if not isinstance(self.contradiction, str) or not self.contradiction.strip():
            _fail_closed("prosa", "CritiquePoint.contradiction must be a non-empty string")
        if not isinstance(self.why_unfounded, str):
            _fail_closed("prosa", "CritiquePoint.why_unfounded must be a string")


CRITIQUE_VERDICTS = ("FUNDAMENTAL", "OBERFLÄCHLICH")


@dataclass(frozen=True)
class CritiqueResult:
    """Evil-Twin-Critique: Struktur + Prosa sauber getrennt.

    Das FalsificationGate konsumiert NUR `verdict` und `points` — beide sind
    deterministisch und kommen NICHT vom Modell. `prose` ist der reine
    Qualitätslayer: das Modell kann sie natürlicher formulieren, ändert aber
    NIE verdict/points. Fehlt das Modell, liefert der deterministische
    Fallback exakt dieselbe Kritik template-basiert (prose.source ==
    "fallback").

    → Das Modell ist KEIN Funktionsbestandteil des Gates, nur ein
      Qualitätslayer (offline/Termux: identische Kritik, template-basiert).
    """
    verdict: str
    points: Tuple[CritiquePoint, ...]
    prose: RenderedProsa


def render_critique(
    points: List[CritiquePoint],
    *,
    verdict: str = "FUNDAMENTAL",
    max_sentences: int = 4,
    language: str = "de",
    model_path: Optional[str] = None,
    llama_cli: Optional[str] = None,
    timeout: float = 60.0,
) -> CritiqueResult:
    """Bereits feststehende Kritik in scharfe, provozierende Prosa rendern.

    Harte Auflage bleibt gültig: das Modell formuliert NUR. Das FINDEN der
    Widersprüche passiert davor (deterministische FalsificationGate-Probes /
    Mirror-Thinker-Struktur) und wird hier als CritiquePoints hereingereicht.

    `verdict` und `points` sind strukturell und modellunabhängig — der
    deterministische Fallback (kein Modell) liefert dieselbe Kritik
    template-basiert, ohne LLM.
    """
    if not points:
        _fail_closed("prosa", "render_critique requires at least one CritiquePoint")
    verdict_norm = (verdict or "").strip().upper()
    if verdict_norm not in CRITIQUE_VERDICTS:
        _fail_closed("prosa", f"verdict must be one of {CRITIQUE_VERDICTS}")

    selected = tuple(points[:3])
    extra: List[Tuple[str, str]] = []
    for i, p in enumerate(selected, start=1):
        stmt = f"Annahme '{p.assumption}' ist nicht haltbar: {p.contradiction}"
        if p.why_unfounded:
            stmt += f". Beleg fehlt: {p.why_unfounded}"
        extra.append((f"kritik_{i}", stmt))

    spec = NarrativeSpec(
        task="EVIL_TWIN_CRITIQUE",
        tone="adversarial",
        max_sentences=max_sentences,
        user_fact=None,
        system_state=verdict_norm,
        allowed_actions=("REQUIRE_EVIDENCE", "DEMAND_REVISION"),
        language=language,
        extra=tuple(extra),
    )
    prose = render(spec, model_path=model_path, llama_cli=llama_cli, timeout=timeout)
    return CritiqueResult(
        verdict=verdict_norm,
        points=selected,
        prose=prose,
    )
