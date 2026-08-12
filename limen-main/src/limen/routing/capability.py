"""
LIMEN Capability Matrix — Provider→Model Routing

Maps models to providers based on capability (context window, tool support),
cost tiers, health scoring, and rate limit state.

Contract: limen.contract.json § key_pool
Selection criteria:
  1. Capability match (model family, context window, tool support)
  2. Rate limit state (current TPM/RPD/RPM usage vs. limits)
  3. Cost priority (cheapest capable key first)
  4. Health (recent error rate, latency percentile)
  5. Affinity (sticky routing for streaming sessions)
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


# ─── Model Family ────────────────────────────────────────────────────


class ModelFamily(str, Enum):
    """Known model families for capability matching."""

    GPT4 = "gpt-4"
    GPT4_5 = "gpt-4.5"
    GPT35 = "gpt-3.5"
    CLAUDE3 = "claude-3"
    CLAUDE4 = "claude-4"
    GEMINI = "gemini"
    LLAMA3 = "llama-3"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"
    GROK = "grok"
    UNKNOWN = "unknown"


@dataclass
class ModelCapability:
    """What a model/provider combination can handle."""

    family: ModelFamily = ModelFamily.UNKNOWN
    max_context_tokens: int = 8192
    supports_tools: bool = False
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_json_mode: bool = False


# ─── Cost Tiers ──────────────────────────────────────────────────────


@dataclass
class CostTier:
    """Pricing per 1M tokens for a model/provider combination."""

    input_per_1m_usd: float = 0.0
    output_per_1m_usd: float = 0.0
    tier: str = "free"  # free | budget | standard | premium

    @property
    def blended_cost(self) -> float:
        """Blended cost (3:1 input:output ratio) per 1M tokens."""
        return (self.input_per_1m_usd * 0.75) + (self.output_per_1m_usd * 0.25)


# ─── Health Scores ───────────────────────────────────────────────────


@dataclass
class HealthScore:
    """Rolling health metrics for one key."""

    window_seconds: float = 300.0  # 5 minutes
    _errors: deque = field(default_factory=deque)  # [(timestamp, error), ...]
    _latencies: deque = field(default_factory=deque)  # [(timestamp, ms), ...]
    _total_requests: int = 0
    _total_errors: int = 0

    def record_success(self, latency_ms: float = 0, *, now: Optional[float] = None) -> None:
        now = now if now is not None else time.monotonic()
        self._latencies.append((now, latency_ms))
        self._total_requests += 1
        self._purge(now)

    def record_error(self, *, now: Optional[float] = None) -> None:
        now = now if now is not None else time.monotonic()
        self._errors.append((now, True))
        self._total_requests += 1
        self._total_errors += 1
        self._purge(now)

    def error_rate(self, *, now: Optional[float] = None) -> float:
        now = now if now is not None else time.monotonic()
        self._purge(now)
        recent_total = len(self._latencies) + len(self._errors)
        if recent_total == 0:
            return 0.0
        return len(self._errors) / recent_total

    def avg_latency_ms(self, *, now: Optional[float] = None) -> float:
        now = now if now is not None else time.monotonic()
        self._purge(now)
        if not self._latencies:
            return 0.0
        return sum(ms for _, ms in self._latencies) / len(self._latencies)

    def p95_latency_ms(self, *, now: Optional[float] = None) -> float:
        now = now if now is not None else time.monotonic()
        self._purge(now)
        if not self._latencies:
            return 0.0
        sorted_lat = sorted(ms for _, ms in self._latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def score(self, *, now: Optional[float] = None) -> float:
        """0.0 = unhealthy, 1.0 = perfect health."""
        now = now if now is not None else time.monotonic()
        err = self.error_rate(now=now)
        return max(0.0, 1.0 - (err * 5.0))  # 20% error rate = 0.0

    def _purge(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._errors and self._errors[0][0] < cutoff:
            self._errors.popleft()
        while self._latencies and self._latencies[0][0] < cutoff:
            self._latencies.popleft()


# ─── Capability Entry ────────────────────────────────────────────────


@dataclass
class CapabilityEntry:
    """One provider + model combination in the capability matrix."""

    provider: str           # openai, groq, deepinfra, openrouter, etc.
    deployment: str         # key alias / deployment name
    model_patterns: List[str] = field(default_factory=list)  # glob patterns: "gpt-4*", "claude-3*"
    capability: ModelCapability = field(default_factory=ModelCapability)
    cost: CostTier = field(default_factory=CostTier)
    health: HealthScore = field(default_factory=HealthScore)
    priority: int = 10       # lower = higher priority
    tags: Set[str] = field(default_factory=set)

    def matches_model(self, model: str) -> bool:
        """Check if this entry can serve the requested model."""
        import fnmatch
        return any(fnmatch.fnmatch(model.lower(), p.lower()) for p in self.model_patterns)


# ─── Capability Matrix ───────────────────────────────────────────────


class CapabilityMatrix:
    """Registry of provider capabilities for intelligent routing.

    Usage:
        matrix = CapabilityMatrix()
        matrix.register(
            provider="openai", deployment="prod-key-1",
            model_patterns=["gpt-4*", "gpt-3.5*"],
            capability=ModelCapability(family=ModelFamily.GPT4, max_context_tokens=128000, supports_tools=True),
            cost=CostTier(input_per_1m_usd=30.0, output_per_1m_usd=60.0, tier="premium"),
        )
        candidates = matrix.find_candidates("gpt-4-turbo")
    """

    def __init__(self):
        self._entries: List[CapabilityEntry] = []

    def register(self, entry: CapabilityEntry) -> None:
        self._entries.append(entry)

    def find_candidates(self, model: str) -> List[CapabilityEntry]:
        """Find all entries that can serve the requested model."""
        return [e for e in self._entries if e.matches_model(model)]

    def best_key(
        self,
        model: str,
        *,
        exclude_deployments: Optional[Set[str]] = None,
        prefer_streaming: bool = False,
        min_health: float = 0.3,
        now: Optional[float] = None,
    ) -> Optional[CapabilityEntry]:
        """Select the best key for a model request.

        Ranking: health > capability fit > cost > priority.
        Excludes unhealthy and excluded deployments.
        """
        candidates = self.find_candidates(model)
        if not candidates:
            return None

        now = now if now is not None else time.monotonic()

        # Filter out excluded and unhealthy
        filtered = [
            c for c in candidates
            if (exclude_deployments is None or c.deployment not in exclude_deployments)
            and c.health.score(now=now) >= min_health
        ]
        if not filtered:
            return None

        # Sort by: health score > streaming support > cost > priority
        # Health is dominant — an unhealthy streaming key loses to a healthy non-streaming one
        def rank(entry: CapabilityEntry) -> Tuple[float, int, float, int]:
            health_rank = -entry.health.score(now=now)  # higher health = more negative = first
            streaming_bonus = 0 if (prefer_streaming and entry.capability.supports_streaming) else 1
            cost_rank = entry.cost.blended_cost
            prio_rank = entry.priority
            return (health_rank, streaming_bonus, cost_rank, prio_rank)

        filtered.sort(key=rank)
        return filtered[0]

    def get_health(self, provider: str, deployment: str) -> Optional[HealthScore]:
        for e in self._entries:
            if e.provider == provider and e.deployment == deployment:
                return e.health
        return None

    def record_success(
        self, provider: str, deployment: str, latency_ms: float = 0
    ) -> None:
        for e in self._entries:
            if e.provider == provider and e.deployment == deployment:
                e.health.record_success(latency_ms)
                return

    def record_error(self, provider: str, deployment: str) -> None:
        for e in self._entries:
            if e.provider == provider and e.deployment == deployment:
                e.health.record_error()
                return

    @property
    def entries(self) -> List[CapabilityEntry]:
        return list(self._entries)


# ─── Pre-built provider capabilities ─────────────────────────────────

# Common model → family mapping
_MODEL_FAMILY_MAP: Dict[str, ModelFamily] = {
    "gpt-4": ModelFamily.GPT4,
    "gpt-4o": ModelFamily.GPT4,
    "gpt-4-turbo": ModelFamily.GPT4,
    "gpt-4.5": ModelFamily.GPT4_5,
    "gpt-3.5": ModelFamily.GPT35,
    "claude-3": ModelFamily.CLAUDE3,
    "claude-3.5": ModelFamily.CLAUDE3,
    "claude-4": ModelFamily.CLAUDE4,
    "gemini": ModelFamily.GEMINI,
    "llama-3": ModelFamily.LLAMA3,
    "mistral": ModelFamily.MISTRAL,
    "deepseek": ModelFamily.DEEPSEEK,
    "grok": ModelFamily.GROK,
}

# Known context windows per family
_CONTEXT_WINDOWS: Dict[ModelFamily, int] = {
    ModelFamily.GPT4: 128000,
    ModelFamily.GPT4_5: 128000,
    ModelFamily.GPT35: 16385,
    ModelFamily.CLAUDE3: 200000,
    ModelFamily.CLAUDE4: 200000,
    ModelFamily.GEMINI: 1_000_000,
    ModelFamily.LLAMA3: 8192,
    ModelFamily.MISTRAL: 32768,
    ModelFamily.DEEPSEEK: 65536,
    ModelFamily.GROK: 131072,
    ModelFamily.UNKNOWN: 8192,
}


def guess_capability(model: str) -> ModelCapability:
    """Guess a model's capability from its name string.

    Sorted by key length descending so longer prefixes match first
    (e.g. gpt-4.5 matches GPT4_5 before gpt-4 matches GPT4).
    """
    model_lower = model.lower()
    sorted_map = sorted(_MODEL_FAMILY_MAP.items(), key=lambda x: -len(x[0]))
    for prefix, family in sorted_map:
        if prefix in model_lower:
            ctx = _CONTEXT_WINDOWS.get(family, 8192)
            return ModelCapability(
                family=family,
                max_context_tokens=ctx,
                supports_tools=family in (ModelFamily.GPT4, ModelFamily.GPT4_5, ModelFamily.CLAUDE3, ModelFamily.CLAUDE4),
                supports_streaming=True,
                supports_vision=family in (ModelFamily.GPT4, ModelFamily.CLAUDE3, ModelFamily.CLAUDE4, ModelFamily.GEMINI),
                supports_json_mode=family in (ModelFamily.GPT4, ModelFamily.GPT4_5),
            )
    return ModelCapability()
