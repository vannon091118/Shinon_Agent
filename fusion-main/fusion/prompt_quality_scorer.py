"""
Prompt Quality Scorer — Measure input quality and correlate with PreProcessor stats.

After each ControlPlaneRuntime.process() call, scores the input quality:
  1. claims_per_char  — Claims extracted per 100 characters of input
  2. falsification_rate — Fraction of claims that were falsified (refuted/edited)
  3. verified_rate — Fraction of claims that passed falsification
  4. unverified_rate — Fraction of claims still unverified
  5. preprocess_mode — synthetic | llm | passthrough | off
  6. quality_score — Composite 0.0–1.0 (higher = better input)

Persists to prompt-quality.jsonl for correlation analysis.
Useful for:
  - Comparing präzise vs. ungenau vs. ausschweifend inputs
  - Measuring PreProcessor impact (synthetic vs. llm mode)
  - Detecting input quality degradation over time
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_LOG_PATH = Path("/tmp/prompt-quality.jsonl")


@dataclass
class PromptQualityScore:
    """One quality measurement of a pipeline input."""

    correlation_id: str = ""
    timestamp: str = ""

    # Input metrics
    input_length: int = 0
    input_source: str = "direct"  # direct | preprocessed
    original_length: int = 0

    # Claim extraction
    claims_count: int = 0
    claims_per_100_chars: float = 0.0

    # Falsification
    falsification_total: int = 0
    falsification_refuted: int = 0
    falsification_edited: int = 0
    falsification_supported: int = 0
    falsification_unverified: int = 0
    falsification_rate: float = 0.0  # refuted + edited / total
    verified_rate: float = 0.0        # supported / total
    unverified_rate: float = 0.0      # unverified / total

    # PreProcessor correlation
    preprocess_mode: str = "off"      # off | llm | synthetic | passthrough
    preprocess_requirements: int = 0  # requirements extracted by PreProcessor
    preprocess_tests: int = 0

    # Composite quality score (0.0–1.0)
    # Higher = better: high claims density, low refuted rate, high verified rate
    quality_score: float = 0.0

    # Error info
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "input_length": self.input_length,
            "input_source": self.input_source,
            "original_length": self.original_length,
            "claims_count": self.claims_count,
            "claims_per_100_chars": round(self.claims_per_100_chars, 4),
            "falsification_total": self.falsification_total,
            "falsification_refuted": self.falsification_refuted,
            "falsification_edited": self.falsification_edited,
            "falsification_supported": self.falsification_supported,
            "falsification_unverified": self.falsification_unverified,
            "falsification_rate": round(self.falsification_rate, 4),
            "verified_rate": round(self.verified_rate, 4),
            "unverified_rate": round(self.unverified_rate, 4),
            "preprocess_mode": self.preprocess_mode,
            "preprocess_requirements": self.preprocess_requirements,
            "preprocess_tests": self.preprocess_tests,
            "quality_score": round(self.quality_score, 4),
            "error": self.error,
        }


class PromptQualityScorer:
    """Score prompt quality after each pipeline run.

    Computes metrics from a RuntimeResult and persists to JSONL
    for correlation analysis. Integrates with the PreProcessor
    to measure its impact on claim extraction quality.

    Usage:
        scorer = PromptQualityScorer()
        score = scorer.score(result)
        print(f"Quality: {score.quality_score:.2f} ({score.claims_per_100_chars:.1f} claims/100c)")

        # Correlation: compare präzise vs. ungenau inputs
        präzise_scores = scorer.get_scores_by_mode("preprocessed")
        vague_scores = scorer.get_scores_by_mode("direct")
    """

    def __init__(self, log_path: Optional[Path] = None):
        self._log_path = Path(log_path) if log_path else DEFAULT_LOG_PATH
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def score(self, result: Any) -> PromptQualityScore:
        """Score a RuntimeResult from ControlPlaneRuntime.process().

        Args:
            result: RuntimeResult with claims, falsification_results,
                    preprocess_info, input_text, original_input

        Returns:
            PromptQualityScore with all metrics computed
        """
        score = PromptQualityScore()
        score.correlation_id = getattr(result, 'correlation_id', '')
        score.timestamp = datetime.now(timezone.utc).isoformat()

        # ── Input metrics ──
        input_text = getattr(result, 'input_text', '') or ''
        original_text = getattr(result, 'original_input', '') or ''
        score.input_length = len(input_text)
        score.original_length = len(original_text)

        if original_text and original_text != input_text:
            score.input_source = "preprocessed"
        else:
            score.input_source = "direct"

        # ── Claim extraction ──
        claims = getattr(result, 'claims', []) or []
        score.claims_count = len(claims)
        if score.input_length > 0:
            score.claims_per_100_chars = (len(claims) / score.input_length) * 100

        # ── Falsification results ──
        fals_results = getattr(result, 'falsification_results', []) or []
        score.falsification_total = len(fals_results)

        for fr in fals_results:
            status = getattr(fr, 'result', None)
            if status == 'refuted':
                score.falsification_refuted += 1
            elif status == 'edited':
                score.falsification_edited += 1
            elif status == 'supported':
                score.falsification_supported += 1
            elif status == 'unverified' or status is None:
                score.falsification_unverified += 1
            else:
                # unknown status → treat as unverified
                score.falsification_unverified += 1

        if score.falsification_total > 0:
            score.falsification_rate = (
                score.falsification_refuted + score.falsification_edited
            ) / score.falsification_total
            score.verified_rate = score.falsification_supported / score.falsification_total
            score.unverified_rate = score.falsification_unverified / score.falsification_total

        # ── PreProcessor correlation ──
        preprocess = getattr(result, 'preprocess_info', None) or {}
        score.preprocess_mode = preprocess.get('mode', 'off')
        score.preprocess_requirements = preprocess.get('requirements_count', 0)
        score.preprocess_tests = preprocess.get('tests_count', 0)

        # ── Error ──
        score.error = getattr(result, 'error', None)

        # ── Composite quality score ──
        # Formula: rewards high claim density + high verification, penalizes high refutation
        # claims_per_char component: max at ~5 claims/100c
        claims_component = min(score.claims_per_100_chars / 5.0, 1.0) * 0.3

        # verification component: higher verified_rate = better
        verification_component = score.verified_rate * 0.4

        # penalty for high falsification rate: 1 - falsification_rate
        falsification_penalty = (1.0 - score.falsification_rate) * 0.3

        score.quality_score = claims_component + verification_component + falsification_penalty
        score.quality_score = max(0.0, min(1.0, score.quality_score))

        return score

    def persist(self, score: PromptQualityScore) -> None:
        """Append score to JSONL log file."""
        try:
            with open(self._log_path, 'a') as f:
                f.write(json.dumps(score.to_dict(), ensure_ascii=False) + '\n')
        except Exception as exc:
            logger.warning("Failed to persist prompt quality score: %s", exc)

    def score_and_persist(self, result: Any) -> PromptQualityScore:
        """Score a result and persist to JSONL. Convenience wrapper."""
        score = self.score(result)
        self.persist(score)
        return score

    def load_all(self) -> List[Dict[str, Any]]:
        """Load all persisted scores from JSONL."""
        scores = []
        try:
            if self._log_path.exists():
                with open(self._log_path) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                scores.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
        except Exception as exc:
            logger.warning("Failed to load prompt quality scores: %s", exc)
        return scores

    def get_scores_by_mode(self, input_source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get scores filtered by input_source (direct | preprocessed)."""
        all_scores = self.load_all()
        if input_source:
            return [s for s in all_scores if s.get('input_source') == input_source]
        return all_scores

    def correlation_report(self) -> Dict[str, Any]:
        """Generate a correlation report between PreProcessor usage and quality.

        Compares direct vs. preprocessed inputs across all runs.
        """
        all_scores = self.load_all()
        if not all_scores:
            return {"available": False, "message": "No prompt quality data yet"}

        direct = [s for s in all_scores if s.get('input_source') == 'direct']
        preprocessed = [s for s in all_scores if s.get('input_source') == 'preprocessed']

        def avg(lst, key):
            if not lst:
                return 0.0
            return sum(s.get(key, 0) for s in lst) / len(lst)

        report = {
            "available": True,
            "total_runs": len(all_scores),
            "direct_runs": len(direct),
            "preprocessed_runs": len(preprocessed),

            # Direct (no PreProcessor)
            "direct": {
                "avg_claims_per_100c": round(avg(direct, 'claims_per_100_chars'), 2),
                "avg_falsification_rate": round(avg(direct, 'falsification_rate'), 2),
                "avg_verified_rate": round(avg(direct, 'verified_rate'), 2),
                "avg_quality_score": round(avg(direct, 'quality_score'), 2),
            } if direct else None,

            # Preprocessed (via LLM or synthetic)
            "preprocessed": {
                "avg_claims_per_100c": round(avg(preprocessed, 'claims_per_100_chars'), 2),
                "avg_falsification_rate": round(avg(preprocessed, 'falsification_rate'), 2),
                "avg_verified_rate": round(avg(preprocessed, 'verified_rate'), 2),
                "avg_quality_score": round(avg(preprocessed, 'quality_score'), 2),
            } if preprocessed else None,

            # Correlation insight
            "insight": _correlation_insight(direct, preprocessed),

            # Latest 5 scores
            "latest": sorted(all_scores, key=lambda s: s.get('timestamp', ''), reverse=True)[:5],
        }

        return report


def _correlation_insight(direct: List, preprocessed: List) -> str:
    """Generate a human-readable correlation insight."""
    if not direct and not preprocessed:
        return "No data for correlation."

    if not direct:
        return "All inputs were preprocessed — no baseline for comparison."
    if not preprocessed:
        return "No preprocessed inputs yet — run with PreProcessor enabled to compare."

    def avg(lst, key):
        return sum(s.get(key, 0) for s in lst) / len(lst)

    d_claims = avg(direct, 'claims_per_100_chars')
    p_claims = avg(preprocessed, 'claims_per_100_chars')
    d_quality = avg(direct, 'quality_score')
    p_quality = avg(preprocessed, 'quality_score')

    parts = []
    if p_claims > d_claims:
        diff = p_claims - d_claims
        parts.append(f"PreProcessor erhöht Claim-Dichte um +{diff:.1f} claims/100c")
    elif d_claims > p_claims:
        parts.append(f"Direkter Input hat höhere Claim-Dichte (+{d_claims - p_claims:.1f})")

    if p_quality > d_quality:
        parts.append(f"PreProcessor verbessert Quality-Score um +{p_quality - d_quality:.2f}")
    elif d_quality > p_quality:
        parts.append(f"Direkter Input hat besseren Quality-Score (+{d_quality - p_quality:.2f})")

    if not parts:
        parts.append("Kein signifikanter Unterschied zwischen direkten und preprocessed Inputs.")

    return " · ".join(parts)


# ─── Global singleton ────────────────────────────────────────────────

_global_scorer: Optional[PromptQualityScorer] = None


def get_quality_scorer(log_path: Optional[Path] = None) -> PromptQualityScorer:
    """Get or create the global PromptQualityScorer singleton."""
    global _global_scorer
    if _global_scorer is None:
        _global_scorer = PromptQualityScorer(log_path=log_path)
    return _global_scorer
