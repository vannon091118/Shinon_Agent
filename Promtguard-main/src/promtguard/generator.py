"""
Promtguard Prompt Generator — Research, Claim Extraction, Handoff HOFF-0002

5-step pipeline:
  1. research — Generate structured research prompt (Rolle A)
  2. ingest   — Parse research output, extract claims per claim-v1.json
  3. build    — Generate atomic task prompts (Rolle B)
  4. handoff  — Produce HOFF-0002 handoff with claims + context tokens
  5. improve  — Self-improvement from success patterns

Status model: tate.md (unverified/verified/refuted/refined/unknown)
Evidence enum: code/doc/test_output/chat/mixed
Confidence: high/medium/low

Position: 1 (between Shinon and KARMA)
Asks: "What is the task?"
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─── tate.md Status Model ────────────────────────────────────────────


class ClaimStatus:
    """tate.md-compliant claim status with Evidence-Enum and Confidence."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REFUTED = "refuted"
    REFINED = "refined"
    UNKNOWN = "unknown"  # "requested but cannot be verified from local state"

    VALID = {UNVERIFIED, VERIFIED, REFUTED, REFINED, UNKNOWN}

    # Evidence types (tate.md Evidence-Enum)
    EVIDENCE_CODE = "code"
    EVIDENCE_DOC = "doc"
    EVIDENCE_TEST = "test_output"
    EVIDENCE_CHAT = "chat"
    EVIDENCE_MIXED = "mixed"

    # Confidence levels
    CONFIDENCE_HIGH = "high"
    CONFIDENCE_MEDIUM = "medium"
    CONFIDENCE_LOW = "low"


# ─── Claim (claim-v1.json schema) ─────────────────────────────────────


@dataclass
class Claim:
    """Single claim per claim-v1.json schema + tate.md fields."""

    id: str  # CLAIM-{PREFIX}-{SEQ:03d}
    claim: str
    status: str = ClaimStatus.UNVERIFIED
    evidence: str = ""              # file:line:code
    evidence_type: str = ClaimStatus.EVIDENCE_CHAT
    confidence: str = ClaimStatus.CONFIDENCE_MEDIUM
    source: str = ""                # RES-NNN or "generator"
    source_decision_index: int = 0
    claim_origin: str = "explicit-declaration"
    verified_by: str = ""
    verified_at: str = ""
    verified_evidence: str = ""
    alternatives_rejected: List[str] = field(default_factory=list)
    created_at: str = ""
    promtset_version: str = "2.0.0"

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "claim": self.claim,
            "status": self.status,
            "confidence": self.confidence,
            "evidence_type": self.evidence_type,
            "source": self.source,
            "claim_origin": self.claim_origin,
            "timestamp": self.created_at,
            "created_at": self.created_at,
            "promtset_version": self.promtset_version,
        }
        if self.evidence:
            d["evidence"] = self.evidence
        if self.verified_by:
            d["verified_by"] = self.verified_by
            d["verified_at"] = self.verified_at
            d["verified_evidence"] = self.verified_evidence
        if self.alternatives_rejected:
            d["alternatives_rejected"] = self.alternatives_rejected
        return d


# ─── Context Token ───────────────────────────────────────────────────


@dataclass
class ContextToken:
    """CTX-{PREFIX}-{TYPE}-{SEQ} — full research context snapshot."""

    id: str
    source: str = ""
    summary: str = ""
    claims_extracted: int = 0
    decisions_count: int = 0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "summary": self.summary,
            "claims_extracted": self.claims_extracted,
            "decisions_count": self.decisions_count,
            "created_at": self.created_at,
        }


# ─── Handoff HOFF-0002 ───────────────────────────────────────────────


@dataclass
class Handoff:
    """HOFF-0002 handoff: Shinon → Promtguard → KARMA."""

    handoff_id: str = "HOFF-0002"
    handoff_version: str = "1.0"
    from_component: str = "promtguard"
    to_component: str = "karma"
    timestamp: str = ""
    note: str = ""
    task_prompt: Optional[str] = None
    claims: List[Claim] = field(default_factory=list)
    context_token_id: str = ""
    promtset_version: str = "2.0.0"

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "handoff_version": self.handoff_version,
            "handoff_id": self.handoff_id,
            "from": self.from_component,
            "to": self.to_component,
            "timestamp": self.timestamp,
            "note": self.note,
            "promtset_version": self.promtset_version,
            "claim_count": len(self.claims),
            "claim_ids": [c.id for c in self.claims],
        }
        if self.task_prompt:
            d["task_prompt"] = self.task_prompt
        if self.context_token_id:
            d["context_token_id"] = self.context_token_id
        return d


# ─── Research Prompt (Rolle A) ────────────────────────────────────────


@dataclass
class ResearchPrompt:
    """Generated research prompt per Rolle A template."""

    mode: str = "discover"  # discover | verify | conflict
    context_tokens: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    instruction: str = ""
    full_prompt: str = ""


# ─── Task Prompt (Rolle B) ───────────────────────────────────────────


@dataclass
class TaskPrompt:
    """Generated atomic task prompt per Rolle B template."""

    task_id: str = ""
    context: str = ""
    constraints: List[str] = field(default_factory=list)
    instruction: str = ""
    acceptance_criteria: List[str] = field(default_factory=list)
    scope_in: str = ""
    scope_out: List[str] = field(default_factory=list)
    target_agent: str = "implementer"
    full_prompt: str = ""


# ─── Pipeline Result ─────────────────────────────────────────────────


@dataclass
class PipelineResult:
    """Complete result of one prompt generation cycle."""

    user_input: str
    research_prompt: Optional[ResearchPrompt] = None
    task_prompt: Optional[TaskPrompt] = None
    claims: List[Claim] = field(default_factory=list)
    context_token: Optional[ContextToken] = None
    handoff: Optional[Handoff] = None
    mode: str = ""  # research | build | direct
    correlation_id: str = ""

    def __post_init__(self):
        if not self.correlation_id:
            self.correlation_id = str(uuid.uuid4())[:8]


# ─── Prompt Generator ────────────────────────────────────────────────


class PromptGenerator:
    """Generates research prompts, extracts claims, builds handoffs.

    Usage:
        gen = PromptGenerator(state_dir=Path(".promtset/state"))
        result = gen.generate(user_input="Analyze the OAuth2 module",
                              mode="research", session_id="sess-001")
        print(f"Claims: {len(result.claims)}, Handoff: {result.handoff.handoff_id}")
    """

    _CLAIM_ID_PATTERN = re.compile(r"^CLAIM-[A-Z]{3,5}-\d{3}$")

    def __init__(self, state_dir: Optional[Path] = None):
        self._state_dir = Path(state_dir) if state_dir else Path(".promtset/state")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        # Per-instance counters (thread-safe per generator)
        self._claim_counter: int = 1
        self._res_counter: int = 1
        self._ctx_counter: int = 100
        self._task_counter: int = 1

    # ── Step 1: Research ──────────────────────────────────────────

    def generate_research_prompt(
        self, user_input: str, *, mode: str = "discover", context_tokens: Optional[List[str]] = None
    ) -> ResearchPrompt:
        """Generate a structured research prompt (Rolle A).

        Produces a read-only research assignment with context, constraints,
        and concrete investigation steps.
        """
        ctx = context_tokens or []
        ctx_block = "\n".join(f"  - {t}" for t in ctx[:5]) if ctx else "  - (none — first research pass)"

        constraints = [
            "READ-ONLY: Do NOT modify any code.",
            "Evidence required: file:line:code per finding.",
            "Output: researcher-context/v2 JSON schema.",
            "One claim per distinct statement.",
        ]

        instruction = self._build_research_instruction(user_input, mode)

        full = self._render_research_prompt(user_input, ctx_block, constraints, instruction, mode)

        return ResearchPrompt(
            mode=mode,
            context_tokens=ctx,
            constraints=constraints,
            instruction=instruction,
            full_prompt=full,
        )

    def _build_research_instruction(self, user_input: str, mode: str) -> str:
        if mode == "verify":
            return (
                "CROSS-CHECK the following claim against the codebase. "
                "Find code-level evidence (file:line:code) that confirms or refutes it. "
                "Required: 3+ independent evidence points.\n\n"
                f"Claim to verify: {user_input}"
            )
        elif mode == "conflict":
            return (
                "CONFLICT DETECTED. Two or more claims contradict each other. "
                "Investigate the codebase to determine which claim is correct. "
                "Document the false claim with evidence of the refutation.\n\n"
                f"Conflict: {user_input}"
            )
        else:  # discover
            return (
                "Investigate the following topic in the codebase. "
                "Map the relevant code paths, identify key functions, "
                "and document evidence with file:line:code references. "
                "Required: 5+ distinct evidence points.\n\n"
                f"Research topic: {user_input}"
            )

    def _render_research_prompt(
        self, user_input: str, ctx_block: str, constraints: List[str], instruction: str, mode: str
    ) -> str:
        constraints_text = "\n".join(f"  - {c}" for c in constraints)
        return f"""## KONTEXT-SCAN-PROTOKOLL
Mode: {mode}
Context tokens used:
{ctx_block}

## RESEARCH-PROMPT (an Researcher)
### TEIL 1: KONTEXT
User input: {user_input}

### TEIL 2: CONSTRAINTS
{constraints_text}

### TEIL 3: INSTRUCTION
{instruction}"""

    # ── Step 2: Ingest — Extract Claims ───────────────────────────

    def extract_claims(
        self, research_output: str, *, source: str = "", max_claims: int = 20
    ) -> List[Claim]:
        """Extract claims from research output (ingest).

        Parses structured research JSON or plain text with:
        - Bullet points, numbered lists, claim-like statements
        - Evidence patterns (file:line:code)
        - Confidence indicators
        """
        claims: List[Claim] = []

        # Try structured JSON first
        if research_output.strip().startswith("{"):
            json_claims = self._parse_json_claims(research_output, source)
            if json_claims:
                return json_claims[:max_claims]

        # Fallback: heuristic extraction from text
        lines = research_output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue

            # Claim patterns
            is_claim = any([
                line.startswith(("- ", "* ", "• ", "> ")),
                re.match(r"^\d+[\.)]\s", line),
                re.search(r"\b(must|should|shall|will|always|never)\b", line, re.I),
                re.search(r"[a-zA-Z0-9_/\-.]+\.\w+:\d+:", line),  # file:line: evidence
            ])

            if is_claim:
                evidence = ""
                ev_match = re.search(r"([a-zA-Z0-9_/\-.]+\.\w+:\d+:.*?)(?:\s|$)", line)
                if ev_match:
                    evidence = ev_match.group(1).rstrip(".,; ")

                confidence = ClaimStatus.CONFIDENCE_MEDIUM
                if evidence:
                    confidence = ClaimStatus.CONFIDENCE_HIGH
                elif re.search(r"\b(might|maybe|perhaps|could be)\b", line, re.I):
                    confidence = ClaimStatus.CONFIDENCE_LOW

                evidence_type = ClaimStatus.EVIDENCE_CODE if evidence else ClaimStatus.EVIDENCE_CHAT

                claim = Claim(
                    id=self._next_claim_id(),
                    claim=line.lstrip("-*•> 0123456789.) ").strip(),
                    source=source or "generator",
                    evidence=evidence,
                    evidence_type=evidence_type,
                    confidence=confidence,
                )
                claims.append(claim)

                if len(claims) >= max_claims:
                    break

        return claims

    def _parse_json_claims(self, json_text: str, source: str) -> List[Claim]:
        """Parse claims from structured JSON research output."""
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            return []

        claims: List[Claim] = []
        # Support multiple JSON structures
        for field in ("claims", "findings", "decisions"):
            items = data.get(field, [])
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    claim_text = item.get("claim") or item.get("finding") or item.get("what", "")
                    if not claim_text:
                        continue
                    claim = Claim(
                        id=self._next_claim_id(),
                        claim=str(claim_text),
                        evidence=str(item.get("evidence", "")),
                        evidence_type=ClaimStatus.EVIDENCE_CODE if item.get("evidence") else ClaimStatus.EVIDENCE_CHAT,
                        confidence=str(item.get("confidence", ClaimStatus.CONFIDENCE_MEDIUM)),
                        source=source or str(item.get("source", "generator")),
                    )
                    claims.append(claim)
        return claims

    # ── Step 3: Build Task Prompt ─────────────────────────────────

    def build_task_prompt(
        self, claims: List[Claim], *, context: str = "", target_agent: str = "implementer"
    ) -> TaskPrompt:
        """Generate an atomic task prompt from claims (Rolle B).

        Produces a single atomic task with scope, constraints, and acceptance criteria.
        """
        task_id = f"TASK-{self._next_task_seq():03d}"

        claim_texts = "\n".join(f"  - [{c.id}] {c.claim}" for c in claims[:10])
        scope = ", ".join(set(
            c.claim.split(":")[0].strip()[:60] if ":" in c.claim else c.claim[:60]
            for c in claims[:5]
        ))

        constraints = [
            "Atomar: one coherent change, max 3 files.",
            "TDD: write test first, then implement.",
            f"Evidence required per claim: file:line:code.",
            "Acceptance: all claims verified or refuted.",
        ]

        acceptance = []
        for c in claims[:5]:  # Top 5 claims get individual criteria
            short = c.claim[:80] + ("..." if len(c.claim) > 80 else "")
            acceptance.append(
                f"Claim [{c.id}]: verify '{short}' with code evidence (file:line:code)"
            )
        acceptance.extend([
            "All evidence references resolve to actual code locations",
            "No new TODOs or FIXMEs introduced",
        ])

        instruction = (
            f"Implement the changes described in the claims below. "
            f"Scope: {scope}. "
            f"Each claim must be verified (found evidence) or refuted (cannot be confirmed)."
        )

        full = self._render_task_prompt(
            task_id, claim_texts, context, constraints, instruction, acceptance, target_agent
        )

        return TaskPrompt(
            task_id=task_id,
            context=context or f"Claims extracted from research",
            constraints=constraints,
            instruction=instruction,
            acceptance_criteria=acceptance,
            scope_in=scope,
            scope_out=[],
            target_agent=target_agent,
            full_prompt=full,
        )

    def _render_task_prompt(
        self, task_id: str, claims_text: str, context: str,
        constraints: List[str], instruction: str, acceptance: List[str], target: str,
    ) -> str:
        c_text = "\n".join(f"  - {c}" for c in constraints)
        a_text = "\n".join(f"  - [ ] {a}" for a in acceptance)
        return f"""## KONTEXT-SCAN-PROTOKOLL
Task: {task_id}
Context: {context}

## ZERLEGUNG
Target agent: {target}
Claims:
{claims_text}

## TASK-PROMPT {task_id}
### TEIL 1: KONTEXT
{context}

### TEIL 2: CONSTRAINTS
{c_text}

### TEIL 3: INSTRUCTION
{instruction}

### ACCEPTANCE CRITERIA
{a_text}"""

    # ── Step 4: Handoff HOFF-0002 ─────────────────────────────────

    def build_handoff(
        self, claims: List[Claim], *, task_prompt: Optional[TaskPrompt] = None, note: str = ""
    ) -> Handoff:
        """Build HOFF-0002 handoff from claims to KARMA."""
        ctx_id = f"CTX-GEN-CTX-{self._next_ctx_seq():03d}"

        if not note:
            verified = sum(1 for c in claims if c.status == ClaimStatus.VERIFIED)
            unverified = sum(1 for c in claims if c.status == ClaimStatus.UNVERIFIED)
            note = (
                f"Claims: {len(claims)} total, {verified} verified, {unverified} unverified. "
                f"Ready for KARMA falsification."
            )

        return Handoff(
            handoff_id="HOFF-0002",
            from_component="promtguard",
            to_component="karma",
            note=note,
            task_prompt=task_prompt.full_prompt if task_prompt else None,
            claims=claims,
            context_token_id=ctx_id,
        )

    # ── Full Pipeline ─────────────────────────────────────────────

    def generate(
        self,
        user_input: str,
        *,
        mode: str = "research",
        session_id: str = "",
        research_output: Optional[str] = None,
        context_tokens: Optional[List[str]] = None,
    ) -> PipelineResult:
        """Run the prompt generation pipeline.

        Modes:
        - "research": Generate research prompt (Step 1 only)
        - "ingest": Parse research_output → claims (Step 2 only)
        - "build": claims → task prompt (Step 3 only)
        - "handoff": claims → HOFF-0002 (Step 4 only)
        - "full": Steps 1→2→3→4 complete pipeline
        """
        result = PipelineResult(user_input=user_input, mode=mode)

        if mode in ("research", "full"):
            result.research_prompt = self.generate_research_prompt(
                user_input, mode="discover", context_tokens=context_tokens
            )

        if research_output and mode in ("ingest", "full"):
            result.claims = self.extract_claims(
                research_output, source=f"RES-{self._res_seq():03d}"
            )

        if result.claims and mode in ("build", "full"):
            result.task_prompt = self.build_task_prompt(result.claims, context=user_input)

        if result.claims and mode in ("handoff", "full"):
            result.handoff = self.build_handoff(result.claims, task_prompt=result.task_prompt)
            result.context_token = ContextToken(
                id=result.handoff.context_token_id,
                source="promptgen",
                summary=user_input[:200],
                claims_extracted=len(result.claims),
                decisions_count=len(result.claims),
            )

        return result

    # ── Claim Verification (tate.md latest-wins) ──────────────────

    def verify_claim(
        self, claim_id: str, new_status: str, *, evidence: str = "", verified_by: str = ""
    ) -> Claim:
        """Verify/refute a claim (latest-wins: creates new version with same ID)."""
        if new_status not in ClaimStatus.VALID:
            raise ValueError(f"Invalid status: {new_status}")

        prefix = f"[{new_status.upper()}]"
        return Claim(
            id=claim_id,
            claim=f"{prefix} Verified by {verified_by or 'manual'}",
            status=new_status,
            evidence=evidence,
            evidence_type=ClaimStatus.EVIDENCE_CODE if evidence else ClaimStatus.EVIDENCE_CHAT,
            confidence=ClaimStatus.CONFIDENCE_HIGH,
            verified_by=verified_by,
            verified_at=datetime.now(timezone.utc).isoformat(),
            verified_evidence=evidence,
        )

    # ── Persistence ───────────────────────────────────────────────

    def persist_claims(self, claims: List[Claim]) -> None:
        """Append claims to claim-log.jsonl (append-only)."""
        path = self._state_dir / "claim-log.jsonl"
        with open(path, "a") as f:
            for c in claims:
                f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")

    def persist_handoff(self, handoff: Handoff) -> None:
        """Append handoff to handoffs.jsonl."""
        path = self._state_dir / "handoffs.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(handoff.to_dict(), ensure_ascii=False) + "\n")

    # ── Counter helpers ───────────────────────────────────────────

    def _next_claim_id(self, prefix: str = "GEN") -> str:
        cid = f"CLAIM-{prefix}-{self._claim_counter:03d}"
        self._claim_counter += 1
        return cid

    def _res_seq(self) -> int:
        seq = self._res_counter
        self._res_counter += 1
        return seq

    def _next_ctx_seq(self) -> int:
        seq = self._ctx_counter
        self._ctx_counter += 1
        return seq

    def _next_task_seq(self) -> int:
        seq = self._task_counter
        self._task_counter += 1
        return seq
