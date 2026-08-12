"""
Chat Router — deterministische Intent-Klassifikation + Chat-Antworten.

Der Chat ist der DEFAULT. Ein Task (goal-chain / Pipeline) wird nur gestartet,
wenn der User es explizit sagt: `/goal`-/`/task`-Präfix oder ein klares
Imperativ-Bauverb mit Objekt. Alles andere ist Chat — und Chat kostet
KEINE API-Calls, solange der User nicht opt-in't.

Philosophie (abgesegnet):
    * 100 % deterministisch — KEIN LLM, KEIN API-Verbrauch, KEINE State-Mutation.
    * Chat-Antworten kommen aus einem Textbaustein-Pool + Schlagwort-Scanner
      (der "Multiple-choice Fallback" aus der Architektur-Diskussion).
    * Shinon ist kritisch, skeptisch, trocken und KURZ. Der Ton ist in den
      Bausteinen eingebrannt — kein Modell erfindet ihn.
    * Der Qualitätslayer (SmolLM2) bzw. die API (LIMEN) ist ein Opt-in
      (`[chat] use_api = true`), kein Bestandteil des Default-Pfads.

Scope: 0.3.0  |  Reine Funktionen. Kein Import von EventBus/Runtime/Pipeline.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

# ─── Intent constants ─────────────────────────────────────────────────

CHAT = "chat"
TASK = "task"
AMBIGUOUS = "ambiguous"


# ─── Task verbs ───────────────────────────────────────────────────────
# STRONG: eindeutige Coding-Verben → TASK auch ohne Objekt ("refactor").
# WEAK: mehrdeutige Verben ("mach", "test", "fix", "make") → TASK nur wenn
#       ein Objekt folgt (>= 2 Wörter) UND keine Nicht-Task-Kollokation.
# Das ist der Schutz davor, dass Chat-Input fälschlich die Pipeline startet
# und User-API-Keys verbrennt.

STRONG_TASK_VERBS = frozenset({
    "bau", "baue", "bauen", "build",
    "implementier", "implementiere", "implementieren", "implement",
    "entwickel", "entwickle", "entwickeln", "develop",
    "refaktoriere", "refaktorier", "refactor",
    "programmier", "programmiere", "codier", "codiere",
    "deploy", "deploye", "migrier", "migriere", "migrate",
    "kompilier", "kompiliere", "compile",
    "portier", "portiere", "port",
    "dokumentier", "dokumentiere", "integrier", "integriere", "integrate",
})

WEAK_TASK_VERBS = frozenset({
    "mach", "mache", "machen", "make",
    "erstell", "erstelle", "erstellen", "erstellt", "create",
    "schreib", "schreibe", "schreiben", "write",
    "fix", "fixe", "reparier", "repariere",
    "installier", "installiere", "install",
    "konfigurier", "konfiguriere", "configure",
    "optimier", "optimiere", "optimize",
    "teste", "test", "analyse", "analysiere", "analyze",
    "generier", "generiere", "generate",
    "erweitere", "erweiter", "extend",
    "add", "remove", "rename", "update", "upgrade", "code",
})

TASK_VERBS = STRONG_TASK_VERBS | WEAK_TASK_VERBS

# Falsch-Positive, die mit einem Weak-Verb beginnen, aber KEIN Task sind.
_NON_TASK_PHRASES = (
    "mach dir keine", "mach dir nichts", "mach keinen", "mach mal",
    "make sure", "make sense", "make it", "make me", "make a",
    "test the water", "fix a date", "fix this meeting",
    "code red", "add fuel", "remove yourself",
)

# Einleitungs-Acks, die vor dem eigentlichen Verb stehen dürfen
# ("ja, bau mir X" → Task trotz führendem "ja").
_LEAD_ACKS = frozenset({"ja", "ok", "okay", "bitte", "please", "jawohl"})


def _is_non_task_phrase(lower: str) -> bool:
    return any(p in lower for p in _NON_TASK_PHRASES)


# ─── Tech-/Code-Indikatoren ───────────────────────────────────────────
# Weak-Verb-Fragmente ("fix dinner", "make coffee", "write a poem") sind
# KEINE Tasks, es sei denn ihr Objekt trägt mindestens EIN Tech-/Code-
# Signal. Sonst → AMBIGUOUS (Rückfrage). Das ist der API-Schutz: sonst
# verbrennt jeder Smalltalk einen Key an LIMEN. Bilingual (EN/DE),
# bare lowercase tokens.
_TECH_WORDS = frozenset({
    # General / dev nouns
    "api", "apis", "endpoint", "endpunkt", "route", "router", "middleware",
    "controller", "model", "modell", "view", "ansicht", "template", "vorlage",
    "schema", "db", "database", "datenbank", "sql", "query", "abfrage",
    "migration", "migrate", "migrier", "cache", "queue", "warteschlange",
    "worker", "job", "flow", "parser", "lexer", "ast", "engine", "runtime",
    # Web / UI
    "app", "application", "anwendung", "web", "server", "client", "frontend",
    "backend", "page", "seite", "component", "komponente", "element",
    "widget", "css", "html", "json", "yaml", "toml", "xml", "svg",
    # Code structure
    "code", "codebase", "codebasis", "function", "funktion", "func",
    "method", "methode", "class", "klasse", "module", "modul", "pkg",
    "package", "paket", "lib", "library", "bibliothek", "framework",
    "dependency", "dep", "deps", "abhängigkeit", "import", "deprecated",
    # Tooling
    "tool", "werkzeug", "script", "skript", "file", "datei", "dir",
    "directory", "verzeichnis", "folder", "ordner", "path", "pfad",
    "src", "config", "configuration", "konfiguration", "einstellung",
    "setting", "env", "environment", "umgebung",
    # Build/deploy/CI
    "build", "compile", "kompilier", "kompiliere", "deploy", "release",
    "ship", "install", "installier", "installiere", "uninstall", "setup",
    "einrichten", "teardown", "docker", "container", "compose", "pipeline",
    "ci", "cd", "cron", "schedule",
    # Test/QA
    "test", "tests", "spec", "mock", "stub", "fixture", "suite", "coverage",
    "abdeckung", "lint", "format", "smoke", "regression", "integration",
    "e2e",
    # Docs/git
    "doc", "docs", "doku", "dokumentation", "documentation", "readme",
    "changelog", "license", "lizenz", "commit", "branch", "merge",
    "zusammenführen", "rebase", "push", "pull", "git", "pr",
    # Runtime/errors/perf
    "log", "logs", "logger", "protokoll", "metric", "metrics", "monitor",
    "alert", "error", "errors", "fehler", "exception", "exceptions",
    "ausnahme", "fail", "failure", "crash", "absturz", "bug", "bugs",
    "defect", "issue", "ticket", "fix", "patch", "hotfix",
    "refactor", "refaktoriere", "rewrite", "optimize", "optimier",
    "optimiere", "perf", "performance", "leistung", "memory", "leak",
    "leck", "race", "deadlock", "thread", "async", "asynchron", "promise",
    "callback", "event", "ereignis", "hook", "handler",
    # Auth/security
    "auth", "login", "logout", "anmeldung", "abmeldung", "session",
    "sitzung", "token", "jwt", "oauth", "sso", "role", "permission",
    "user", "benutzer", "password", "kennwort", "hash", "encrypt",
    "verschlüsseln", "decrypt", "entschlüsseln", "ssl", "tls", "https",
    "cert", "zertifikat", "proxy", "balancer",
    # Shinon-specific / governance
    "probe", "gate", "evidence", "beweis", "claim", "anspruch", "fact",
    "tatsache", "knowledge", "wissen", "persona", "attitude", "haltung",
    "mood", "stimmung", "tone", "prompt", "llm", "agent", "skill",
    "fähigkeit", "integration", "aufgabe",
})


def _has_tech_word(tokens: list[str]) -> bool:
    return any(t.strip(".!?,;:\"").lower() in _TECH_WORDS for t in tokens)


def strip_task_prefix(text: str) -> str:
    """Für /goal-/task-Präfixe: den eigentlichen Inhalt zurückgeben."""
    t = text.strip()
    lower = t.lower()
    for prefix in ("/goal ", "/task ", "goal ", "task "):
        if lower.startswith(prefix):
            return t[len(prefix):].strip()
    return t


# ─── Chat signals (Substrings, lowercased) ────────────────────────────

_CHAT_GREETING_WORDS = frozenset({
    "hi", "hallo", "hello", "hey", "moin", "servus", "yo", "hej", "na",
    "tag", "hi!", "hey!",
})

_CHAT_GREETING_PHRASES = (
    "guten tag", "guten morgen", "guten abend", "grüß", "gruess",
)


def _is_greeting(lower: str) -> bool:
    """Gruß-Erkennung an Wortgrenzen — 'hi' trifft NICHT 'himmel'."""
    words = lower.split()
    if words and words[0].rstrip("!.?,:;") in _CHAT_GREETING_WORDS:
        return True
    return lower.startswith(_CHAT_GREETING_PHRASES)


_CHAT_SELF = (
    "wer bist du", "was bist du", "stell dich vor", "vorstell dich",
    "wer bist", "was kannst du", "was kann", "was machst du", "bist du",
)

_CHAT_TOPIC = (
    "welche api", "welcher api", "welche modelle", "welches modell",
    "welche provider", "welcher provider", "api key", "apikey", "provider",
    "was ist", "wie funktioni", "erklär", "erklaer", "erkläre", "erkläre",
    "was bedeutet", "wofür", "wozu", "warum", "wieso", "hilfe", "help",
    "einstellungen", "konfigur", "config", "wie starte", "wie installier",
)

_CHAT_ACK = (
    "danke", "ok", "okay", "cool", "nice", "gut", "perfekt", "top", "super",
    "verstanden", "passt", "alles klar", "macht sinn", "ja", "nein",
    "weiß nicht", "weiss nicht", "vielleicht", "egal", "nichts", "nix",
    # bilingual acks (small additions for parity)
    "thanks", "ty", "merci", "thx", "danke schön", "danke sehr",
)


def _matches_any(lower: str, needles) -> bool:
    return any(n in lower for n in needles)


def _is_question(text: str) -> bool:
    t = text.strip()
    if t.endswith("?"):
        return True
    lower = t.lower()
    question_words = (
        "wer", "was", "wie", "warum", "wieso", "weshalb", "wann", "wo",
        "welch", "wem", "wen", "wessen", "can you", "could you", "what",
        "why", "how", "who", "where", "when", "which", "kannst du",
        "könntest du", "koenntest du",
    )
    first = lower.split()[0].rstrip(".!?,:;") if lower.split() else ""
    return first in question_words or lower.startswith(tuple(question_words))


def classify_intent(text: str) -> str:
    """Deterministische Klassifikation: 'chat' | 'task' | 'ambiguous'.

    Reihenfolge (bewusst so):
      1. Explizites /goal- oder /task-Präfix   -> task
      2. Bauverb als erstes Wort (mit Objekt)  -> task
      3. Chat-Signal (Gruß/Selbst/Thema/Ack)   -> chat
      4. Frage ohne Task-Verb                  -> chat
      5. Kurzer Rest ohne Signal               -> ambiguous
      6. Default                               -> chat
    """
    t = (text or "").strip()
    if not t:
        return CHAT

    lower = t.lower()

    # 1. Explicit task prefix
    for prefix in ("/goal ", "/task ", "goal ", "task "):
        if lower.startswith(prefix):
            return TASK
    if lower in ("/goal", "/task", "goal", "task"):
        return TASK

    words = lower.split()

    # 2. Build verb as first word (nach optionalem "ja/ok/bitte")
    idx = 0
    if words and words[0].rstrip(".!?,:;") in _LEAD_ACKS and len(words) > 1:
        idx = 1
    first = words[idx].rstrip(".!?,:;") if idx < len(words) else ""

    if first in TASK_VERBS:
        if first in STRONG_TASK_VERBS:
            return TASK
        # Weak-Verb: braucht Objekt + darf KEINE Nicht-Task-Phrase sein +
        # muss ein Tech-/Code-Signal im Objekt tragen.
        # Fragment-Schutz: "fix dinner" / "make coffee" / "write a poem"
        # → KEIN Task (kostet API-Usage), sondern AMBIGUOUS (Rückfrage).
        # Explizite Carve-outs ("make sense") bleiben via _NON_TASK_PHRASES.
        tail = [w for w in words[idx + 1:] if w.strip(".!?,;:")]
        if (len(tail) >= 1
                and not _is_non_task_phrase(lower)
                and _has_tech_word(tail)):
            return TASK

    # 3. Chat signals
    if _is_greeting(lower):
        return CHAT
    if _matches_any(lower, _CHAT_SELF):
        return CHAT
    if _matches_any(lower, _CHAT_TOPIC):
        return CHAT
    if _matches_any(lower, _CHAT_ACK):
        return CHAT

    # 4. Question → chat
    if _is_question(t):
        return CHAT

    # 5. Short, no signal → ambiguous (ask what the user wants)
    if len(t.split()) <= 3:
        return AMBIGUOUS

    # 6. Default: chat
    return CHAT


# ─── Deterministic chat replies (Textbaustein-Pool) ───────────────────
# Schlagwort-Scanner über den Input; jede Regel liefert einen kurzen,
# trockenen Shinon-Satz. Kein LLM. Mood individualisiert leicht.

# Emotionale Zustände, bei denen Shinon kürzer/schärfer antwortet.
_NEGATIVE_MOODS = frozenset({
    "annoyed", "impatient", "confrontational", "adversarial", "skeptical",
})


def chat_reply(message: str, mood: str = "neutral") -> str:
    """Deterministische Chat-Antwort aus dem Textbaustein-Pool.

    Reine Funktion: Input-String -> Output-String. Kein DB-, kein File-,
    kein API-Zugriff. `mood` (emotional_state aus dem Character-Layer)
    individualisiert nur die Wortwahl — nie den Inhalt.
    """
    m = (message or "").strip().lower()
    negative = mood in _NEGATIVE_MOODS

    # Fähigkeiten (vor Selbst-Vorstellung: "was kannst du" ist eine
    # Fähigkeits-Frage, keine "wer bist du"-Frage)
    if any(k in m for k in ("was kannst du", "was kann", "was machst du")):
        return ("Ich kann chatten oder Tasks fahren. Chat ist Standard und kostet nichts. "
                "Für einen Task: klarer Imperativ, z. B. „Bau ein Game of Life“. "
                "Mit `use_api = true` beantwortet auch der Chat über deine API.")

    # Gruß
    if _is_greeting(m):
        if negative:
            return "Ja. Worum geht's?"
        return ("Hallo. Chat oder Task — sag, was du brauchst. "
                "Einen Task startest du mit einem klaren Verb, z. B. „Bau ein Game of Life“.")

    # Selbst-Vorstellung
    if any(k in m for k in ("wer bist du", "was bist du", "stell dich vor", "vorstell dich", "bist du")):
        return ("Ich bin Shinon. Kritisch, skeptisch, präzise. "
                "Ich hinterfrage Annahmen — auch deine. Chat ist Standard; "
                "für einen Task gib ein klares Verb an.")

    # API / Provider / Keys / Modelle
    if any(k in m for k in ("api", "key", "provider", "modell", "model", "anbieter")):
        return ("Provider: Groq, OpenRouter, NVIDIA NIM, Mistral. "
                "Keys liegen in einer Datei: ~/.shinon/config/.env. "
                "Noch keiner hinterlegt — ich laufe deshalb ohne API-Calls.")

    # Hilfe / Einstellungen / Start
    if _matches_any(m, _CHAT_TOPIC):
        return ("Ich kann chatten oder Tasks fahren. "
                "Chat ist Standard und kostet nichts. "
                "Willst du, dass auch der Chat deine API nutzt: "
                "`shinon chat --use-api` oder [chat] use_api = true in shinon.toml.")

    # Bestätigungen / Smalltalk-Ack
    if _matches_any(m, _CHAT_ACK):
        return "Verstanden."

    # Frage
    if _is_question(message):
        return ("Gute Frage. Ich antworte aber nur präzise, wenn die Frage präzise ist. "
                "Was genau willst du wissen — oder ist es ein Task?")

    # Default: kurz + Rückfrage (zwingt nichts auf)
    if negative:
        return "Sag konkret, was du willst — chatten oder bauen?"
    return ("Das ist weder klar Chat noch klarer Task. "
            "Sag mir, was du willst — chatten oder etwas bauen? "
            "Für einen Task: klarer Imperativ, z. B. „Refactor den Auth-Router“.")


def clarify_reply() -> str:
    """Deterministische Rückfrage bei mehrdeutigem Input (ambiguous)."""
    return ("Ich kann das nicht eindeutig einordnen. "
            "Willst du chatten oder einen Task starten? "
            "Task-Beispiel: „Implementiere OAuth2-Login“. Alles andere behandle ich als Chat.")


# ─── Config reading (opt-in for API-backed chat) ──────────────────────
# Liest [chat] use_api aus shinon.toml. Env-Override SHINON_CHAT_USE_API
# gewinnt (für schnelles Umschalten ohne File-Edit / Tests).

try:
    import paths as _P  # noqa: E402
    _SHINON_CONFIG = _P.CONFIG_DIR / "shinon.toml"
except Exception:  # pragma: no cover - paths.py fehlt nur außerhalb des Repos
    _SHINON_CONFIG = Path.home() / ".shinon" / "config" / "shinon.toml"


def read_chat_config() -> Dict[str, object]:
    """{use_api: bool, default_intent: str} — deterministisch, read-only."""
    # Env-Override hat Vorrang
    env = os.environ.get("SHINON_CHAT_USE_API")
    if env is not None:
        return {"use_api": env.strip().lower() in ("1", "true", "yes", "on"),
                "default_intent": "chat"}

    result: Dict[str, object] = {"use_api": False, "default_intent": "chat"}
    try:
        import tomllib
        raw = tomllib.loads(_SHINON_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return result

    chat = raw.get("chat", {})
    if isinstance(chat, dict):
        use_api = chat.get("use_api", False)
        result["use_api"] = bool(use_api)
        default_intent = chat.get("default_intent", "chat")
        if default_intent in (CHAT, TASK, AMBIGUOUS):
            result["default_intent"] = default_intent
    return result
