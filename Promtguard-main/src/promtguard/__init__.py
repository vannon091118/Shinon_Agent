"""
Promtguard — Prompt Generation, Claim Extraction, HOFF-0002 Handoff

5-step pipeline: research → ingest → build → handoff → self-improve
Status model: tate.md (unverified/verified/refuted/refined/unknown)
"""

from promtguard.generator import (
    PromptGenerator,
    Claim,
    ClaimStatus,
    Handoff,
    ContextToken,
    ResearchPrompt,
    TaskPrompt,
    PipelineResult,
)

__all__ = [
    "PromptGenerator",
    "Claim",
    "ClaimStatus",
    "Handoff",
    "ContextToken",
    "ResearchPrompt",
    "TaskPrompt",
    "PipelineResult",
]
