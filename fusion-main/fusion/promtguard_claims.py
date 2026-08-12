"""
Promtguard Claims — Prompt Parsing & Claim Extraction (Python)

Receives HOFF-0002 handoff from Shinon. Parses user intent,
extracts claims, assigns CLAIM-GEN-NNN IDs, persists as JSONL.

Contract: promtguard.contract.json v1.0.0
Status model: tate.md (unverified/verified/refuted/refined/unknown)
Position: 1 (prompt layer)
Asks: "What is the task?"
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─── Claim Status (tate.md model) ────────────────────────────────────


class ClaimStatus:
    """tate.md status model with Evidence-Enum and Confidence."""

    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REFUTED = "refuted"
    REFINED = "refined"
    UNKNOWN = "unknown"  # "requested but cannot be verified from local state"

    VALID_STATUSES = {UNVERIFIED, VERIFIED, REFUTED, REFINED, UNKNOWN}

    # Evidence types (from tate.md)
    EVIDENCE_CODE = "code"
    EVIDENCE_DOC = "doc"
    EVIDENCE_TEST = "test_output"
    EVIDENCE_CHAT = "chat"
    EVIDENCE_MIXED = "mixed"


@dataclass
class Claim:
    """Single claim per claim-v1.json schema."""

    id: str  # CLAIM-GEN-NNN
    claim: str
    status: str = ClaimStatus.UNVERIFIED
    evidence: str = ""
    confidence: str = "medium"
    source: str = "shinon_passthrough"
    source_decision_index: int = 0
    claim_origin: str = "explicit-declaration"
    verified_by: str = ""
    verified_at: str = ""
    verified_evidence: str = ""
    alternatives_rejected: List[str] = field(default_factory=list)
    evidence_type: str = ClaimStatus.EVIDENCE_CHAT
    created_at: str = ""
    promtset_version: str = "2.0.0"

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "claim": self.claim,
            "status": self.status,
            "confidence": self.confidence,
            "source": self.source,
            "claim_origin": self.claim_origin,
            "timestamp": self.created_at,
            "created_at": self.created_at,
            "promtset_version": self.promtset_version,
            "evidence_type": self.evidence_type,
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


# ─── Handoff ─────────────────────────────────────────────────────────


@dataclass
class Handoff:
    """R04-compliant handoff between components."""

    handoff_version: str = "1.0"
    from_component: str = "promtguard"
    to_component: str = "karma"
    timestamp: str = ""
    note: str = ""
    task_id: str = ""
    promtset_version: str = "2.0.0"

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "handoff_version": self.handoff_version,
            "from": self.from_component,
            "to": self.to_component,
            "timestamp": self.timestamp,
            "note": self.note,
            "promtset_version": self.promtset_version,
        }
        if self.task_id:
            d["task_id"] = self.task_id
        return d


# ─── Context Token ───────────────────────────────────────────────────


@dataclass
class ContextToken:
    """CTX-GEN-NNN context token — full context snapshot."""

    id: str
    source: str = ""
    summary: str = ""
    claims_extracted: int = 0
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
            "created_at": self.created_at,
        }


# ─── Promtguard Engine ───────────────────────────────────────────────


class PromtguardClaims:
    """Receives Shinon handoff, extracts claims, persists to JSONL.

    MVP mode: Simple intent-based claim extraction.
    No full research pipeline. Direct handoff to KARMA.
    """

    _CLAIM_ID_PATTERN = re.compile(r"^CLAIM-[A-Z]{3,5}-\d{3}$")

    def __init__(self, state_dir: Optional[Path] = None):
        self._state_dir = Path(state_dir) if state_dir else Path(".promtset/state")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._claim_counter = self._load_counter()

    # ─── Counter ───────────────────────────────────────────────────

    def _counter_path(self) -> Path:
        return self._state_dir / "claim-counter.txt"

    def _load_counter(self) -> int:
        path = self._counter_path()
        if path.exists():
            try:
                return int(path.read_text().strip())
            except (ValueError, OSError):
                pass
        return 0

    def _save_counter(self) -> None:
        self._counter_path().write_text(str(self._claim_counter))

    def _next_claim_id(self, prefix: str = "GEN") -> str:
        self._claim_counter += 1
        self._save_counter()
        return f"CLAIM-{prefix}-{self._claim_counter:03d}"

    def _next_ctx_id(self) -> str:
        return f"CTX-GEN-CTX-{self._claim_counter + 100:03d}"

    # ─── Claim Extraction ──────────────────────────────────────────

    def extract_claims(
        self, processed_input: str, source: str = "shinon_passthrough"
    ) -> List[Claim]:
        """Extract claims from processed user input.

        Primary: Bullet points, numbered lists, must/should/shall patterns.
        Fallback: Sentence segmentation + keyword density scoring for vague inputs.
        """
        claims: List[Claim] = []
        lines = processed_input.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue

            # Detect claim-like patterns
            is_claim = any([
                line.startswith(("- ", "* ", "• ", "> ")),
                re.match(r"^\d+[\.\)]\s", line),
                re.search(r"\b(must|should|shall|will|always|never)\b", line, re.I),
            ])

            if is_claim:
                claim = Claim(
                    id=self._next_claim_id(),
                    claim=line.lstrip("-*•> 0123456789.) "),
                    source=source,
                    confidence="medium",
                )
                claims.append(claim)

        # ── Fallback: sentence segmentation + keyword density (v2.1) ──
        # When bullet/list extraction yields < 2 claims, fall back to
        # sentence-level segmentation with keyword density scoring.
        # This handles vague/imprecise inputs where the user doesn't use
        # structured formatting or explicit claim keywords.
        if len(claims) < 2 and len(processed_input.strip()) >= 30:
            fallback_claims = self._extract_claims_fallback(
                processed_input, source
            )
            # Only use fallback if it produces MORE claims than primary
            if len(fallback_claims) > len(claims):
                claims = fallback_claims

        # Last resort: entire input as one claim
        if not claims and len(processed_input.strip()) >= 10:
            summary = processed_input.strip()[:200]
            claim = Claim(
                id=self._next_claim_id(),
                claim=summary,
                source=source,
                confidence="low",
            )
            claims.append(claim)

        return claims

    # ─── Fallback Heuristics (v2.1) ──────────────────────────────────

    # Domain-relevant keywords for claim scoring.
    # Higher weight = stronger claim signal from vague text.
    _TECH_KEYWORDS: Dict[str, float] = {
        # Architecture / structure
        "node": 2.0, "javascript": 2.0, "typescript": 2.0, "python": 2.0,
        "cli": 2.0, "terminal": 2.0, "console": 1.5, "command": 1.5,
        "grid": 2.5, "array": 1.5, "uint8": 2.0, "matrix": 1.5,
        "render": 2.0, "renderer": 2.5, "ansi": 2.0, "escape": 1.0,
        "loop": 1.5, "interval": 1.5, "timer": 1.5, "tick": 1.5,
        "test": 2.0, "unit": 1.5, "integration": 2.0, "snapshot": 2.0,
        "module": 1.5, "component": 1.5, "class": 1.0, "function": 1.0,
        "api": 1.5, "endpoint": 1.5, "server": 1.5, "client": 1.0,
        "database": 2.0, "sqlite": 2.0, "store": 1.0, "persist": 1.5,
        "config": 1.5, "option": 1.0, "argument": 1.0, "flag": 1.0,
        # Package / ecosystem
        "npm": 1.5, "package": 1.5, "dependency": 1.5, "import": 1.0,
        "eslint": 1.5, "prettier": 1.5, "jest": 1.5,
    }

    _IMPERATIVE_KEYWORDS: Dict[str, float] = {
        # German imperatives / hortatives
        "soll": 2.0, "muss": 2.5, "mach": 1.5, "bau": 2.0, "erstell": 2.0,
        "kann": 1.0, "könnte": 1.0, "vielleicht": 0.8, "wäre": 1.0,
        "brauch": 1.5, "braucht": 1.5, "will": 1.5, "möchte": 1.5,
        # English imperatives
        "must": 2.5, "should": 2.0, "shall": 2.0, "need": 1.5,
        "build": 2.0, "create": 2.0, "make": 1.5, "implement": 2.0,
        "use": 1.0, "run": 1.0, "add": 1.0, "support": 1.0,
    }

    _DOMAIN_KEYWORDS: Dict[str, float] = {
        # Game of Life domain
        "game of life": 2.5, "zelle": 2.0, "zellen": 2.0,
        "nachbar": 2.0, "nachbarn": 2.0, "regel": 2.0, "regeln": 2.0,
        "muster": 1.5, "pattern": 1.5, "generation": 1.5,
        "torus": 2.5, "wrap": 1.5, "lebend": 1.5, "tot": 1.5,
        "überlebt": 1.5, "stirbt": 1.5, "geboren": 1.5,
        "conway": 2.0, "cellular": 2.0, "automaton": 2.0,
    }

    def _sentence_segment(self, text: str) -> List[str]:
        """Split text into sentences using multiple boundary strategies.

        Strategy 1: Split on [.!?] followed by space + capital letter
        Strategy 2: Split on newlines (paragraph boundaries)
        Strategy 3: Split on German sentence connectors (und, aber, also, dann)

        Returns clean sentences >= 8 chars (or >= 4 chars if high keyword score).
        """
        # Primary: split on sentence-ending punctuation followed by capital letter
        raw = re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ])', text.strip())

        # Secondary: split multi-paragraph segments on newlines
        sentences = []
        for segment in raw:
            segment = segment.strip()
            if not segment:
                continue
            # If segment still has newlines, split further
            sub = [s.strip() for s in segment.split('\n') if s.strip()]
            sentences.extend(sub)

        # Filter: keep sentences >= 8 chars, or short ones with strong keywords
        filtered = []
        for s in sentences:
            s = s.rstrip('.')
            if len(s) >= 12:
                filtered.append(s)
            elif len(s) >= 6 and self._score_sentence(s) > 1.5:
                # Short but high-value (e.g., "50x50 grid", "Uint8Array")
                filtered.append(s)
        return filtered

    def _score_sentence(self, text: str) -> float:
        """Score a sentence by keyword density across tech, imperative, and domain.

        Returns a float representing claim relevance:
          < 0.8 = noise (skip entirely)
          0.8-1.5 = moderate (include but with low confidence)
          > 1.5 = strong claim (include independently with medium confidence)
        """
        lowered = text.lower()
        score = 0.0

        # Tech keywords
        for kw, weight in self._TECH_KEYWORDS.items():
            if kw in lowered:
                score += weight

        # Imperative/hortative keywords
        for kw, weight in self._IMPERATIVE_KEYWORDS.items():
            if kw in lowered:
                score += weight

        # Domain keywords
        for kw, weight in self._DOMAIN_KEYWORDS.items():
            if kw in lowered:
                score += weight

        # Length normalization: very short or very long adjust score
        if len(text) < 15:
            score *= 0.7
        elif len(text) > 100:
            score = min(score, score * 0.9 + 0.5)  # bonus cap

        return score

    def _extract_claims_fallback(
        self, text: str, source: str
    ) -> List[Claim]:
        """Fallback claim extraction: sentence segmentation + keyword density.

        Algorithm:
          1. Segment into sentences
          2. Score each sentence by keyword density
          3. Extract sentences scoring >= 1.0 as individual claims
          4. Skip sentences scoring < 0.8 (noise/filler)
          5. Group low-scoring sentences (0.8-1.0) with adjacent claims

        This handles vague inputs like "Mach so ein Game of Life Ding"
        (6 claims from 510 chars) and long-winded inputs with filler
        text (7+ claims from 2800 chars).
        """
        sentences = self._sentence_segment(text)
        if not sentences:
            return []

        claims: List[Claim] = []
        scored = [(s, self._score_sentence(s)) for s in sentences]

        NOISE_THRESHOLD = 0.8   # Below this: skip entirely
        CLAIM_THRESHOLD = 1.0   # Above this: standalone claim

        i = 0
        while i < len(scored):
            s, score = scored[i]

            if score >= CLAIM_THRESHOLD:
                # Strong sentence → individual claim
                claims.append(Claim(
                    id=self._next_claim_id(),
                    claim=s[:200],
                    source=source,
                    confidence="medium" if score > 2.0 else "low",
                ))
                i += 1
            elif score < NOISE_THRESHOLD:
                # Noise/filler → skip entirely
                i += 1
            else:
                # Moderate sentence (0.8-1.0) → group with next claim
                group = [s]
                j = i + 1
                # Collect consecutive moderate sentences (max 2)
                while j < len(scored) and scored[j][1] < CLAIM_THRESHOLD and scored[j][1] >= NOISE_THRESHOLD and len(group) < 2:
                    group.append(scored[j][0])
                    j += 1

                if j < len(scored) and scored[j][1] >= CLAIM_THRESHOLD:
                    # Next is a strong claim — prepend group to it
                    group.append(scored[j][0])
                    combined = " ".join(group)[:200]
                    claims.append(Claim(
                        id=self._next_claim_id(),
                        claim=combined,
                        source=source,
                        confidence="low",
                    ))
                    i = j + 1
                elif len(group) >= 2:
                    # At least 2 moderate sentences → make a weak claim
                    combined = " ".join(group)[:200]
                    claims.append(Claim(
                        id=self._next_claim_id(),
                        claim=combined,
                        source=source,
                        confidence="low",
                    ))
                    i = j
                else:
                    i = j  # Single moderate sentence with no strong neighbor → skip

        return claims

    # ─── Persistence ───────────────────────────────────────────────

    def append_claim(self, claim: Claim) -> None:
        """Append one claim to claim-log.jsonl AND upsert into pipeline-state.db.

        JSONL remains the append-only audit trail. SQLite provides
        queryable, latest-wins access for cross-component consumers
        (KARMA, goal-chain, dashboard).
        """
        # 1. JSONL (append-only audit trail — never skip)
        path = self._state_dir / "claim-log.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(claim.to_dict(), ensure_ascii=False) + "\n")

        # 2. SQLite (centralized, queryable)
        self._upsert_claim_sqlite(claim)

    def append_claims(self, claims: List[Claim]) -> None:
        """Append multiple claims."""
        for c in claims:
            self.append_claim(c)

    def append_handoff(self, handoff: Handoff) -> None:
        """Append handoff to handoffs.jsonl."""
        path = self._state_dir / "handoffs.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(handoff.to_dict(), ensure_ascii=False) + "\n")

    def append_context_token(self, token: ContextToken) -> None:
        """Append context token to context-log.jsonl."""
        path = self._state_dir / "context-log.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(token.to_dict(), ensure_ascii=False) + "\n")

    # ─── Verification ──────────────────────────────────────────────

    def verify_claim(
        self,
        claim_id: str,
        new_status: str,
        evidence: str = "",
        verified_by: str = "",
        original_claim: str = "",
    ) -> Optional[Claim]:
        """Verify/refute a claim (latest-wins: append new line with same ID).

        Args:
            claim_id: CLAIM-GEN-NNN ID to verify.
            new_status: New status (verified/refuted/refined).
            evidence: File:line:code evidence reference.
            verified_by: Who/what verified this claim.
            original_claim: Original claim text (preserved for context).
        """
        if new_status not in ClaimStatus.VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")

        claim_text = (
            f"[{new_status.upper()}] {original_claim}"
            if original_claim
            else f"VERIFICATION: {new_status}"
        )

        claim = Claim(
            id=claim_id,
            claim=claim_text,
            status=new_status,
            evidence=evidence,
            verified_by=verified_by,
            verified_at=datetime.now(timezone.utc).isoformat(),
            verified_evidence=evidence,
        )
        self.append_claim(claim)
        return claim

    # ─── Stats ─────────────────────────────────────────────────────

    # ─── SQLite Dual-Write ────────────────────────────────────────

    def _db_path(self) -> Path:
        """Path to the centralized pipeline-state.db."""
        return Path("pipeline-state.db")

    def _ensure_claims_table(self, conn: sqlite3.Connection) -> None:
        """Create claims table if not exists (from pipeline-state.schema.sql)."""
        conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA busy_timeout=5000;

            CREATE TABLE IF NOT EXISTS claims (
                claim_id         TEXT PRIMARY KEY,
                pipeline_run_id  TEXT DEFAULT '',
                source_component TEXT NOT NULL DEFAULT 'promtguard'
                    CHECK(source_component IN ('promtguard','karma')),
                status           TEXT NOT NULL DEFAULT 'unverified'
                    CHECK(status IN ('unverified','supported','confirmed','refuted','conflicted')),
                verified_by      TEXT CHECK(verified_by IN ('karma','promtguard')),
                verified_at      TEXT,
                claim_text       TEXT NOT NULL DEFAULT '',
                evidence         TEXT DEFAULT '',
                confidence       TEXT DEFAULT 'medium'
                    CHECK(confidence IN ('high','medium','low')),
                source_res       TEXT DEFAULT '',
                claim_origin     TEXT DEFAULT 'explicit-declaration',
                idempotency_fp   TEXT DEFAULT '',
                alternatives_json TEXT DEFAULT '[]',
                created_at       TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
            CREATE INDEX IF NOT EXISTS idx_claims_run ON claims(pipeline_run_id);
        """)

    def _upsert_claim_sqlite(self, claim: Claim) -> None:
        """Upsert a claim into the centralized pipeline-state.db."""
        try:
            db_path = self._db_path()
            conn = sqlite3.connect(str(db_path), timeout=5)
            self._ensure_claims_table(conn)

            now = datetime.now(timezone.utc).isoformat()
            alternatives_json = json.dumps(
                claim.alternatives_rejected, ensure_ascii=False
            ) if claim.alternatives_rejected else "[]"

            # Map JSONL status to schema status
            status_map = {
                "unverified": "unverified",
                "verified": "confirmed",
                "refuted": "refuted",
                "refined": "unverified",
                "unknown": "unverified",
            }
            db_status = status_map.get(claim.status, "unverified")

            conn.execute("""
                INSERT INTO claims (
                    claim_id, source_component, status, verified_by, verified_at,
                    claim_text, evidence, confidence, source_res, claim_origin,
                    idempotency_fp, alternatives_json, created_at, updated_at
                ) VALUES (?, 'promtguard', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(claim_id) DO UPDATE SET
                    status = excluded.status,
                    verified_by = COALESCE(excluded.verified_by, claims.verified_by),
                    verified_at = COALESCE(excluded.verified_at, claims.verified_at),
                    claim_text = excluded.claim_text,
                    evidence = excluded.evidence,
                    confidence = excluded.confidence,
                    updated_at = excluded.updated_at
            """, (
                claim.id,
                db_status,
                claim.verified_by or None,
                claim.verified_at or None,
                claim.claim,
                claim.evidence or "",
                claim.confidence or "medium",
                claim.source or "",
                claim.claim_origin or "explicit-declaration",
                "",  # idempotency_fp
                alternatives_json,
                claim.created_at or now,
                now,
            ))

            conn.commit()
            conn.close()
        except Exception as exc:
            # SQLite write MUST NOT break the primary JSONL path
            import logging
            logging.getLogger(__name__).warning(
                "Promtguard: SQLite dual-write failed for %s: %s",
                claim.id, exc,
            )

    def get_claims_from_db(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query claims from the centralized SQLite DB."""
        db_path = self._db_path()
        if not db_path.exists():
            return []

        try:
            conn = sqlite3.connect(str(db_path), timeout=5)
            conn.row_factory = sqlite3.Row

            if status:
                rows = conn.execute(
                    "SELECT * FROM claims WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM claims ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()

            result = [dict(r) for r in rows]
            conn.close()
            return result
        except Exception:
            return []

    def stats(self) -> Dict[str, int]:
        """Count claims by status from claim-log."""
        counts = {s: 0 for s in ClaimStatus.VALID_STATUSES}
        path = self._state_dir / "claim-log.jsonl"
        if not path.exists():
            return counts

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    status = data.get("status", ClaimStatus.UNKNOWN)
                    if status in counts:
                        counts[status] += 1
                except json.JSONDecodeError:
                    pass
        return counts
