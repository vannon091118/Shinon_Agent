"""
LLM Pre-Processor for Shinon — Structure imprecise prompts before pipeline.

Sends raw user input to OpenRouter (via LIMEN KeyPool) with a structuring
prompt. The LLM returns structured JSON with requirements, architecture, and
tests. This structured output becomes the clean input for the pipeline,
ensuring high-quality claim extraction even from vague prompts.

Fallback: When no OpenRouter key is available (test/synthetic mode), a
rule-based heuristic structures the input using sentence segmentation,
keyword density, and imperative detection — the same engine that powers
the Promtguard claim extractor.

Usage:
    preprocessor = LLMPreProcessor(key_pool=pool)
    structured = await preprocessor.structure("Mach so ein Game of Life Ding")
    # → {goal: "...", requirements: [...], architecture: {...}, tests: [...]}
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ─── Structuring prompt (sent to OpenRouter LLM) ──────────────────────

STRUCTURING_SYSTEM_PROMPT = """You are a requirements engineer. Your job is to take a vague,
imprecise, or long-winded user prompt and structure it into a precise,
machine-readable JSON format.

Follow this schema EXACTLY:

{
  "goal": "<one-line summary of what to build>",
  "requirements": [
    "<specific, testable requirement 1>",
    "<specific, testable requirement 2>",
    ...
  ],
  "architecture": {
    "components": ["<component 1>", "<component 2>", ...],
    "dataFlow": "<one-paragraph data flow description>",
    "patterns": ["<design pattern 1>", ...]
  },
  "tests": [
    "<specific test case 1>",
    "<specific test case 2>",
    ...
  ],
  "techStack": {
    "language": "<programming language>",
    "framework": "<framework or 'none'>",
    "dependencies": ["<dep 1>", ...]
  }
}

RULES:
1. Every requirement MUST be specific and testable (no "should be good").
2. If the user doesn't specify a tech stack, INFER the most appropriate one.
3. Tests MUST describe concrete assertions (e.g., "Grid initializes with all dead cells").
4. Output ONLY valid JSON — no markdown, no explanations, no code blocks.
5. If the input is ALREADY precise, just restructure it into this format."""


# ─── Structured output schema ─────────────────────────────────────────

@dataclass
class StructuredInput:
    """Structured representation of a user prompt after preprocessing."""

    goal: str = ""
    requirements: List[str] = field(default_factory=list)
    architecture_components: List[str] = field(default_factory=list)
    architecture_data_flow: str = ""
    architecture_patterns: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    tech_language: str = ""
    tech_framework: str = ""
    tech_dependencies: List[str] = field(default_factory=list)
    original_input: str = ""
    preprocessed: bool = False
    mode: str = "synthetic"  # "llm" or "synthetic"

    def to_text(self) -> str:
        """Convert structured input back to a clean text block for the pipeline."""
        lines = [f"# Goal: {self.goal}", ""]

        if self.requirements:
            lines.append("## Requirements")
            for i, req in enumerate(self.requirements, 1):
                lines.append(f"{i}. {req}")
            lines.append("")

        if self.architecture_components:
            lines.append("## Architecture")
            lines.append(f"Components: {', '.join(self.architecture_components)}")
            if self.architecture_data_flow:
                lines.append(f"Data Flow: {self.architecture_data_flow}")
            if self.architecture_patterns:
                lines.append(f"Patterns: {', '.join(self.architecture_patterns)}")
            lines.append("")

        if self.tests:
            lines.append("## Tests")
            for i, test in enumerate(self.tests, 1):
                lines.append(f"{i}. {test}")
            lines.append("")

        if self.tech_language:
            lines.append("## Tech Stack")
            stack = self.tech_language
            if self.tech_framework:
                stack += f" + {self.tech_framework}"
            lines.append(f"- {stack}")
            if self.tech_dependencies:
                lines.append(f"- Dependencies: {', '.join(self.tech_dependencies)}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "requirements": self.requirements,
            "architecture": {
                "components": self.architecture_components,
                "dataFlow": self.architecture_data_flow,
                "patterns": self.architecture_patterns,
            },
            "tests": self.tests,
            "techStack": {
                "language": self.tech_language,
                "framework": self.tech_framework,
                "dependencies": self.tech_dependencies,
            },
            "preprocessed": self.preprocessed,
            "mode": self.mode,
        }

    @classmethod
    def from_llm_response(cls, response_json: Dict[str, Any], original: str) -> "StructuredInput":
        """Parse LLM JSON response into StructuredInput."""
        arch = response_json.get("architecture", {})
        if isinstance(arch, list):
            arch = {"components": arch, "dataFlow": "", "patterns": []}
        tech = response_json.get("techStack", {})
        if isinstance(tech, list):
            tech = {"language": tech[0] if tech else "", "framework": "", "dependencies": tech[1:]}

        return cls(
            goal=str(response_json.get("goal", "")),
            requirements=_ensure_list(response_json.get("requirements", [])),
            architecture_components=_ensure_list(arch.get("components", [])),
            architecture_data_flow=str(arch.get("dataFlow", "")),
            architecture_patterns=_ensure_list(arch.get("patterns", [])),
            tests=_ensure_list(response_json.get("tests", [])),
            tech_language=str(tech.get("language", "")),
            tech_framework=str(tech.get("framework", "")),
            tech_dependencies=_ensure_list(tech.get("dependencies", [])),
            original_input=original,
            preprocessed=True,
            mode="llm",
        )


def _ensure_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str):
        return [value] if value else []
    return []


# ─── Quality heuristic — does this input need structuring? ───────────

# Keywords that indicate a precise, well-structured input
# Anchored: must appear at line start or after a section header
_STRUCTURED_INDICATORS = [
    r"^\d+\.\s",           # Numbered list
    r"^[-*]\s",            # Bullet points (dash or asterisk)
    r"^#{1,3}\s",          # Markdown headings
    r"```",                # Code blocks
    r"(?m)^(requirements?|architecture|test(s|ing)|components?)\s*:",  # Section headers
    r"(?m)^(goal|objective|purpose|ziel|aufgabe)\s*:",  # Goal sections
]


def needs_structuring(user_text: str) -> bool:
    """Heuristic: does this input need LLM preprocessing?

    Returns True if:
    - Input is very short (< 80 chars) — likely underspecified
    - Input is very long (> 800 chars) — likely long-winded
    - Input has NO structured indicators (no bullets, headings, sections)
    """
    text = user_text.strip()

    # Very short = certainly underspecified
    if len(text) < 80:
        return True

    # Very long with no structure = long-winded
    if len(text) > 800:
        structured_lines = sum(
            1 for indicator in _STRUCTURED_INDICATORS
            if re.search(indicator, text, re.MULTILINE)
        )
        if structured_lines < 3:
            return True

    # Check for any structured indicators
    has_structure = any(
        re.search(indicator, text, re.MULTILINE)
        for indicator in _STRUCTURED_INDICATORS
    )

    return not has_structure


# ─── Synthetic structuring (fallback when no LLM available) ───────────

# Technology keywords for inference (expanded beyond GoL)
_TECH_KEYWORDS = [
    # Format: (keyword, language, framework, dependencies)
    ("node", "javascript", "node.js", []),
    ("python", "python", "", []),
    ("rust", "rust", "", []),
    ("react", "javascript", "react", []),
    ("vue", "javascript", "vue", []),
    ("angular", "typescript", "angular", []),
    ("typescript", "typescript", "", []),
    ("game of life", "javascript", "node.js", []),
    ("api", "javascript", "express", []),
    ("rest", "javascript", "express", []),
    ("graphql", "javascript", "apollo", []),
    ("oauth", "javascript", "express", ["passport"]),
    ("auth", "javascript", "express", ["passport"]),
    ("login", "javascript", "express", ["passport"]),
    ("database", "python", "sqlite", []),
    ("sqlite", "python", "sqlite", []),
    ("postgres", "python", "postgres", ["psycopg2"]),
    ("cli", "javascript", "node.js", []),
    ("terminal", "javascript", "node.js", []),
    ("web", "javascript", "react", []),
    ("frontend", "javascript", "react", []),
    ("backend", "javascript", "express", []),
    ("fullstack", "javascript", "express + react", []),
    ("docker", "python", "docker", []),
]

# Domain keywords → requirements (generalized, multi-domain)
_DOMAIN_KEYWORDS = [
    # Format: (keyword, requirement description)
    # Game of Life
    ("zelle", "Cell state management (alive/dead)"),
    ("cell", "Cell state management (alive/dead)"),
    ("grid", "2D grid data structure"),
    ("gitter", "2D grid data structure"),
    ("nachbar", "Neighbor counting (Moore neighborhood)"),
    ("neighbor", "Neighbor counting (Moore neighborhood)"),
    ("regel", "Conway's Game of Life rules (B3/S23)"),
    ("rule", "Conway's Game of Life rules (B3/S23)"),
    ("conway", "Conway's Game of Life rules (B3/S23)"),
    ("generation", "Generation update loop"),
    ("torus", "Torus wrap-around boundary"),
    # API / Backend
    ("endpoint", "REST API endpoint implementation"),
    ("route", "Request routing and handler"),
    ("middleware", "Request middleware pipeline"),
    ("auth", "Authentication and authorization"),
    ("login", "User login flow"),
    ("oauth", "OAuth2 authentication flow"),
    ("session", "Session management"),
    ("jwt", "JWT token-based authentication"),
    # Data
    ("database", "Database integration and queries"),
    ("schema", "Database schema design"),
    ("migration", "Database migration strategy"),
    ("cache", "Caching layer implementation"),
    # UI
    ("component", "Reusable UI components"),
    ("state", "State management"),
    ("render", "Rendering / display output"),
    ("style", "CSS / styling system"),
    # Universal
    ("test", "Unit test suite"),
    ("error", "Error handling strategy"),
    ("log", "Logging and monitoring"),
    ("config", "Configuration management"),
    ("seed", "Deterministic seed-based initialization"),
    ("color", "Color/ANSI visual output"),
    ("keyboard", "Keyboard controls (start/pause/quit)"),
    ("tastatur", "Keyboard controls (start/pause/quit)"),
    ("loop", "Generation update loop"),
]


def _infer_tech_stack(text: str) -> Dict[str, Any]:
    """Infer tech stack from keywords in user text."""
    text_lower = text.lower()
    best = None
    best_len = 0
    for keyword, lang, framework, deps in _TECH_KEYWORDS:
        if keyword in text_lower and len(keyword) > best_len:
            best = {"language": lang, "framework": framework, "dependencies": deps}
            best_len = len(keyword)
    if best:
        return best
    return {"language": "javascript", "framework": "node.js", "dependencies": []}


def _infer_requirements(text: str) -> List[str]:
    """Extract requirements from domain keywords."""
    found = set()
    text_lower = text.lower()
    for keyword, requirement in _DOMAIN_KEYWORDS:
        if keyword in text_lower:
            found.add(requirement)
    result = list(found)

    # Add domain-agnostic basics if few requirements found
    universal = [
        "Error handling strategy",
        "Configuration management",
        "Unit test suite",
    ]
    if len(result) < 3:
        for u in universal:
            if u not in result:
                result.append(u)

    return result


def _infer_goal(text: str) -> str:
    """Extract a one-line goal summary."""
    # Clean up: remove newlines, collapse spaces
    clean = " ".join(text.split())

    # Find first sentence that looks like a goal statement
    sentences = re.split(r"[.!?]\s+", clean)
    for s in sentences:
        s = s.strip().rstrip("\n0123456789. ")  # Remove trailing numbers/bullets
        if len(s) > 15 and any(
            kw in s.lower()
            for kw in ["bau", "build", "mach", "make", "create", "erstelle", "implement",
                       "baue", "erstelle", "entwickle"]
        ):
            return s
    # Fallback: first sentence > 15 chars
    for s in sentences:
        s = s.strip().rstrip("\n0123456789. ")
        if len(s) > 15:
            return s
    return clean[:100]


def _synthetic_structure(user_text: str) -> StructuredInput:
    """Rule-based structuring without LLM call.

    Uses keyword matching to infer domain, tech stack, requirements, and tests.
    Generalized beyond Game of Life — works for CLI tools, APIs, UIs, databases.
    Architecture is inferred from domain keywords, not hardcoded.
    """
    tech = _infer_tech_stack(user_text)
    requirements = _infer_requirements(user_text)
    goal = _infer_goal(user_text)

    # Infer architecture from domain
    text_lower = user_text.lower()
    is_game_of_life = any(kw in text_lower for kw in ["game of life", "zelle", "conway", "gol"])
    is_api = any(kw in text_lower for kw in ["api", "endpoint", "rest", "graphql"])
    is_auth = any(kw in text_lower for kw in ["oauth", "login", "auth", "session"])
    is_web = any(kw in text_lower for kw in ["react", "vue", "frontend", "web", "ui"])
    is_cli = any(kw in text_lower for kw in ["cli", "terminal", "konsole", "command"])

    if is_game_of_life:
        components = ["Grid (Uint8Array)", "Rules Engine", "Renderer (ANSI/Terminal)", "Game Loop", "CLI Entry Point"]
        data_flow = "CLI args → Grid.init(seed) → Game loop: Rules.compute(Grid) → Renderer.draw(Grid) → Repeat"
        patterns = ["Separation of Concerns", "Pure Functions", "Deterministic"]
        tests = [
            "Grid initializes with correct dimensions",
            "Rules compute B3/S23 correctly for all 512 combinations",
            "Blinker oscillator period is 2",
            "Block still life never changes",
            "Glider moves correctly across the grid",
            "Torus wrap-around works at all edges",
            "Renderer produces correct ANSI output",
        ]
    elif is_api or is_auth:
        components = ["Router", "Controllers", "Middleware", "Database Layer", "Auth Module"]
        data_flow = "Request → Router → Middleware → Controller → Database → Response"
        patterns = ["MVC", "Middleware Chain", "Repository Pattern"]
        tests = [
            "API endpoint returns correct status codes",
            "Authentication middleware rejects invalid tokens",
            "Request validation catches malformed inputs",
            "Error handler returns proper error responses",
            "Database queries use parameterized statements",
        ]
    elif is_web:
        components = ["Components", "State Management", "Router", "API Client", "Styling"]
        data_flow = "User Action → State Update → Re-render → API Call → Response → State Update"
        patterns = ["Component Architecture", "Unidirectional Data Flow", "Separation of Concerns"]
        tests = [
            "Components render without errors",
            "User interactions trigger correct state changes",
            "API client handles network errors gracefully",
            "Responsive design works at all breakpoints",
        ]
    elif is_cli:
        components = ["Argument Parser", "Core Logic", "Output Formatter", "Config Manager"]
        data_flow = "CLI args → Parser → Config → Core Logic → Formatter → stdout/stderr"
        patterns = ["Separation of Concerns", "Strategy Pattern (output formats)", "Command Pattern"]
        tests = [
            "CLI accepts all documented arguments",
            "Help text is generated correctly",
            "Invalid arguments produce clear error messages",
            "Output format matches specification",
        ]
    else:
        # Generic software project
        components = ["Core Module", "Input/Output Layer", "Configuration", "Error Handling"]
        data_flow = "Input → Processing → Output"
        patterns = ["Separation of Concerns", "Pure Functions"]
        tests = [
            "Core logic produces correct results",
            "Input validation rejects invalid data",
            "Error cases are handled gracefully",
            "Output format matches specification",
        ]

    return StructuredInput(
        goal=goal,
        requirements=requirements,
        architecture_components=components,
        architecture_data_flow=data_flow,
        architecture_patterns=patterns,
        tests=tests,
        tech_language=tech["language"],
        tech_framework=tech["framework"],
        tech_dependencies=tech["dependencies"],
        original_input=user_text,
        preprocessed=True,
        mode="synthetic",
    )


# ─── LLMPreProcessor ──────────────────────────────────────────────────


class LLMPreProcessor:
    """Pre-processes raw user input through LIMEN API Gateway.

    Three modes:
    - ``"auto"``: Uses quality heuristic to decide if structuring is needed
    - ``"force"``: Always structures via LLM (LIMEN or direct KeyPool)
    - ``"synthetic"``: Uses rule-based heuristic, no LLM call

    When ``limen_backend`` is provided, routes LLM calls through LIMEN's
    /v1/chat/completions — gaining automatic KeyPool rotation, 429 handling,
    and provider routing. Falls back to synthetic if LIMEN is unreachable.

    The ``key_pool`` parameter is kept for backward compatibility but
    deprecates in favor of LIMENBackend.
    """

    def __init__(
        self,
        key_pool: Optional[Any] = None,
        limen_backend: Optional[Any] = None,
        mode: str = "auto",
        model: str = "auto",
        max_tokens: int = 1500,
        timeout: float = 30.0,
    ):
        self._key_pool = key_pool
        self._limen_backend = limen_backend
        self._mode = mode
        self._model = model
        self._max_tokens = max_tokens
        self._timeout = timeout
        self._calls: int = 0
        self._synthetic_fallbacks: int = 0
        self._limen_calls: int = 0

    @property
    def stats(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "calls": self._calls,
            "synthetic_fallbacks": self._synthetic_fallbacks,
            "mode": self._mode,
            "model": self._model,
        }
        if self._limen_backend is not None:
            result["limen_calls"] = self._limen_calls
            result["backend"] = "LIMEN"
            result["backend_stats"] = self._limen_backend.stats
        elif self._key_pool is not None:
            result["backend"] = "KeyPool"
        else:
            result["backend"] = "none"
        return result

    async def structure(self, user_text: str) -> StructuredInput:
        """Structure raw user input.

        Returns:
            StructuredInput with goal, requirements, architecture, tests.
            The original input is preserved in .original_input.
        """
        # Auto mode: check if structuring is needed
        if self._mode == "auto" and not needs_structuring(user_text):
            logger.debug("Input already structured — skipping preprocessing")
            return StructuredInput(
                goal=user_text[:100],
                original_input=user_text,
                preprocessed=False,
                mode="passthrough",
            )

        # Try LLM path: LIMEN first, then KeyPool fallback
        if self._limen_backend is not None:
            try:
                return await self._llm_structure_via_limen(user_text)
            except Exception as exc:
                logger.warning("LIMEN structuring failed — trying KeyPool: %s", exc)
        if self._key_pool is not None:
            try:
                return await self._llm_structure(user_text)
            except Exception as exc:
                logger.warning("LLM structuring failed — falling back to synthetic: %s", exc)

        # Synthetic fallback
        self._synthetic_fallbacks += 1
        return _synthetic_structure(user_text)

    async def _llm_structure_via_limen(self, user_text: str) -> StructuredInput:
        """Structure input via LIMEN API Gateway.

        Routes through LIMEN's /v1/chat/completions — KeyPool rotation,
        429 handling, and provider routing are all handled by LIMEN.
        No claim/release needed — LIMEN owns key management.
        """
        if self._limen_backend is None:
            raise RuntimeError("No LIMEN backend configured")

        data = await self._limen_backend.chat(
            messages=[{"role": "user", "content": user_text}],
            model=self._model,
            temperature=0.1,
            max_tokens=self._max_tokens,
            response_format={"type": "json_object"},
            system=STRUCTURING_SYSTEM_PROMPT,
        )

        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        self._calls += 1
        self._limen_calls += 1

        return StructuredInput.from_llm_response(parsed, user_text)

    async def _llm_structure(self, user_text: str) -> StructuredInput:
        """Structure input via direct OpenRouter API (legacy KeyPool path)."""
        import httpx

        # Get an API key from the pool
        key_value = await self._key_pool.claim(
            model=self._model,
            estimated_tokens=800,
        )
        if key_value is None:
            raise RuntimeError("No active OpenRouter key available in pool")

        try:
            payload = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": STRUCTURING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_text},
                ],
                "temperature": 0.1,  # Low temp for structured output
                "max_tokens": self._max_tokens,
                "response_format": {"type": "json_object"},
            }

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {key_value}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:4200",
                        "X-Title": "Shinon LLM PreProcessor",
                    },
                )

            if response.status_code != 200:
                raise RuntimeError(
                    f"OpenRouter returned {response.status_code}: {response.text[:200]}"
                )

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Parse JSON from LLM response
            parsed = json.loads(content)
            self._calls += 1

            # Release key with success
            try:
                await self._key_pool.release(key_value, None, tokens_used=data.get("usage", {}).get("total_tokens", 0))
            except Exception:
                pass

            return StructuredInput.from_llm_response(parsed, user_text)

        except Exception:
            # Release key with failure
            try:
                await self._key_pool.release(key_value, "unhandled_error", cooldown_seconds=5)
            except Exception:
                pass
            raise


# ─── Integration helper ───────────────────────────────────────────────

def create_preprocessor_from_limen(
    limen_db_path: str = "limen-main/data/limen.db",
    limen_url: str = "http://127.0.0.1:8001",
    mode: str = "auto",
) -> LLMPreProcessor:
    """Create an LLMPreProcessor wired to the LIMEN API Gateway.

    Routes all LLM calls through LIMEN's /v1/chat/completions —
    gaining automatic KeyPool rotation, 429 handling, and provider routing.
    Falls back to synthetic mode if LIMEN is unreachable.

    Args:
        limen_db_path: Path to limen.db (used for fallback KeyPool)
        limen_url: LIMEN API base URL
        mode: "auto", "force", or "synthetic"

    Returns:
        Configured LLMPreProcessor ready for use.
    """
    import sqlite3
    from pathlib import Path

    db_path = Path(limen_db_path)
    if not db_path.exists():
        logger.warning("LIMEN DB not found at %s — preprocessor will use synthetic mode", db_path)
        return LLMPreProcessor(mode="synthetic")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Find openrouter provider entries
    rows = conn.execute(
        "SELECT * FROM providers WHERE provider='openrouter' AND status='active'"
    ).fetchall()

    if not rows:
        logger.warning("No active openrouter keys in LIMEN DB — synthetic mode")
        conn.close()
        return LLMPreProcessor(mode="synthetic")

    # Extract key values from meta_json
    keys = []
    for row in rows:
        meta = json.loads(row["meta_json"] or "{}")
        key_value = meta.get("api_key", meta.get("key_value", ""))
        if key_value:
            keys.append(key_value)

    conn.close()

    if not keys:
        logger.warning("OpenRouter keys found but no api_key in meta_json — synthetic mode")
        return LLMPreProcessor(mode="synthetic")

    # Create KeyPool
    from limen.routing.key_pool import KeyPool
    pool = KeyPool(deployment="openrouter-free", keys=keys, provider="openrouter")

    # Create LIMENBackend
    from fusion.limen_backend import LIMENBackend
    backend = LIMENBackend(base_url=limen_url, timeout=30.0)

    logger.info("LLMPreProcessor created via LIMEN: %s, mode=%s", limen_url, mode)
    return LLMPreProcessor(limen_backend=backend, key_pool=pool, mode=mode)
