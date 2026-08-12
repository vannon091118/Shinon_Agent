"""
Two-Tier Memory — SQLite-backed facts (T1) + patterns (T2) (ported from twoTierMemory.ts)
v2: + Hot→Mid→Cold zone migration, pattern reinforcement, cross-tier queries, WAL mode

Scope: 0.3.0  |  Source: ShinonLLM-main/character/src/experience/twoTierMemory.ts
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from fusion.shinon.shinon_patterns import Pattern, PersonalFact, PatternExample


# ─── Config ───────────────────────────────────────────────────────────


@dataclass
class TwoTierMemoryConfig:
    tier1_table: str = "personal_facts"
    tier2_table: str = "patterns"
    link_table: str = "pattern_links"
    enable_cross_tier_queries: bool = True
    # Zone migration thresholds (days)
    hot_max_age_days: int = 1       # Facts stay HOT for 1 day
    mid_max_age_days: int = 7        # Facts move from MID to COLD after 7 days
    # Pattern reinforcement: max examples before oldest is dropped
    max_examples_per_pattern: int = 20
    # Minimum confidence to keep a pattern after pruning
    min_confidence_to_keep: float = 0.3


# ─── Adapter Interface ────────────────────────────────────────────────


class MemoryAdapter:
    """Abstract adapter for memory persistence."""
    
    def all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        raise NotImplementedError
    
    def run(self, sql: str, params: tuple = ()) -> None:
        raise NotImplementedError


class SqliteMemoryAdapter(MemoryAdapter):
    """SQLite implementation of MemoryAdapter with WAL mode for concurrent access."""
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()
    
    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=5000")
            
            # Tier 1: Personal Facts with zone support
            conn.execute("""
                CREATE TABLE IF NOT EXISTS personal_facts (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'event',
                    session_id TEXT NOT NULL DEFAULT 'default',
                    conversation_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    zone TEXT NOT NULL DEFAULT 'hot',
                    relevance_score REAL NOT NULL DEFAULT 0.5
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_session ON personal_facts(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_zone ON personal_facts(zone)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_category ON personal_facts(category)")
            
            # Tier 2: Patterns with anchor-based unique constraint
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    anchor TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0.5,
                    examples_json TEXT NOT NULL DEFAULT '[]',
                    first_seen TEXT NOT NULL,
                    last_reinforced TEXT NOT NULL,
                    reinforcement_count INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON patterns(confidence)")
            
            # Links between Tier 1 and Tier 2
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_links (
                    pattern_id TEXT NOT NULL,
                    fact_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL DEFAULT 'example_of',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (pattern_id, fact_id)
                )
            """)
            conn.commit()
    
    def _connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        return conn
    
    def all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self._lock:
            with self._connection() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, params).fetchall()
                return [dict(r) for r in rows]
    
    def run(self, sql: str, params: tuple = ()) -> None:
        with self._lock:
            with self._connection() as conn:
                conn.execute(sql, params)
                conn.commit()


# ─── Two-Tier Memory ──────────────────────────────────────────────────


class TwoTierMemory:
    """Two-tier memory system: Tier 1 (facts) + Tier 2 (patterns).
    
    Features:
      - Hot→Mid→Cold zone migration based on time thresholds
      - Pattern reinforcement: merging new facts into existing patterns
      - Cross-tier queries: find patterns by fact, facts by pattern
      - WAL mode for concurrent access
    """
    
    def __init__(self, adapter: Optional[MemoryAdapter] = None, db_path: Optional[Path] = None):
        self.adapter = adapter or SqliteMemoryAdapter(db_path or Path("shinon_memory.db"))
        self.config = TwoTierMemoryConfig()
    
    # ── Tier 1: Facts ─────────────────────────────────────────────
    
    def save_fact(self, fact: PersonalFact, zone: str = "hot") -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.adapter.run(
            "INSERT OR REPLACE INTO personal_facts "
            "(id, content, category, session_id, conversation_id, created_at, zone, relevance_score) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (fact.id, fact.content, fact.category, fact.session_id, "default",
             fact.created_at or now, zone, 0.5)
        )
    
    def query_tier1(
        self,
        session_id: Optional[str] = None,
        category: Optional[str] = None,
        zone: Optional[str] = None,
        limit: int = 50,
    ) -> List[PersonalFact]:
        query = "SELECT id, content, category, session_id, created_at FROM personal_facts WHERE 1=1"
        params: list = []
        
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if category:
            query += " AND category = ?"
            params.append(category)
        if zone:
            query += " AND zone = ?"
            params.append(zone)
        
        query += " ORDER BY created_at DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        rows = self.adapter.all(query, tuple(params))
        return [
            PersonalFact(
                id=r["id"], content=r["content"], category=r["category"],
                created_at=r["created_at"], session_id=r.get("session_id", "default"),
            )
            for r in rows
        ]
    
    # ── Zone Migration (Hot→Mid→Cold) ───────────────────────────
    
    def migrate_zones(self) -> Dict[str, int]:
        """Migrate facts between zones based on age thresholds.
        
        Returns: {hot→mid: N, mid→cold: N, cold_pruned: N}
        """
        now = datetime.now(timezone.utc)
        hot_cutoff = (now - timedelta(days=self.config.hot_max_age_days)).isoformat()
        mid_cutoff = (now - timedelta(days=self.config.mid_max_age_days)).isoformat()
        
        result = {"hot_to_mid": 0, "mid_to_cold": 0, "cold_pruned": 0}
        
        # Hot → Mid: facts older than hot_max_age_days
        rows = self.adapter.all(
            "SELECT id FROM personal_facts WHERE zone='hot' AND created_at < ? LIMIT 500",
            (hot_cutoff,)
        )
        for row in rows:
            self.adapter.run(
                "UPDATE personal_facts SET zone='mid' WHERE id=?",
                (row["id"],)
            )
        result["hot_to_mid"] = len(rows)
        
        # Mid → Cold: facts older than mid_max_age_days
        rows = self.adapter.all(
            "SELECT id FROM personal_facts WHERE zone='mid' AND created_at < ? LIMIT 500",
            (mid_cutoff,)
        )
        for row in rows:
            self.adapter.run(
                "UPDATE personal_facts SET zone='cold' WHERE id=?",
                (row["id"],)
            )
        result["mid_to_cold"] = len(rows)
        
        # Cold pruning: delete facts older than mid_max_age_days * 2
        prune_cutoff = (now - timedelta(days=self.config.mid_max_age_days * 2)).isoformat()
        rows = self.adapter.all(
            "SELECT id FROM personal_facts WHERE zone='cold' AND created_at < ? LIMIT 500",
            (prune_cutoff,)
        )
        for row in rows:
            # Delete links first, then fact
            self.adapter.run("DELETE FROM pattern_links WHERE fact_id=?", (row["id"],))
            self.adapter.run("DELETE FROM personal_facts WHERE id=?", (row["id"],))
        result["cold_pruned"] = len(rows)
        
        return result
    
    # ── Tier 2: Patterns ──────────────────────────────────────────
    
    def save_pattern(self, pattern: Pattern) -> None:
        """Save a pattern. If anchor already exists, REINFORCE instead of overwrite."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Check if pattern with same anchor already exists
        existing = self.adapter.all(
            "SELECT id, anchor, type, confidence, examples_json, first_seen, last_reinforced, "
            "reinforcement_count FROM patterns WHERE anchor=?",
            (pattern.anchor,)
        )
        
        if existing:
            # REINFORCE: merge new examples, bump counter, update confidence
            old = existing[0]
            new_count = old["reinforcement_count"] + 1
            new_last = pattern.last_reinforced or now
            
            # Merge examples (deduplicate by fact_id)
            try:
                old_examples = json.loads(old.get("examples_json", "[]"))
            except (json.JSONDecodeError, TypeError):
                old_examples = []
            
            new_examples = [{"factId": e.fact_id, "content": e.content, "date": e.date}
                           for e in pattern.examples]
            
            # Merge + deduplicate by fact_id
            seen_ids = set()
            merged = []
            for ex in old_examples + new_examples:
                fid = ex.get("factId", "")
                if fid and fid not in seen_ids:
                    seen_ids.add(fid)
                    merged.append(ex)
            
            # Keep max examples
            if len(merged) > self.config.max_examples_per_pattern:
                merged = merged[-self.config.max_examples_per_pattern:]
            
            # Recalculate confidence from merged data
            from fusion.shinon.shinon_patterns import score_confidence
            temp_pattern = Pattern(
                id=pattern.id, anchor=pattern.anchor, type=pattern.type,
                confidence=pattern.confidence,
                examples=[PatternExample(fact_id=e.get("factId",""), content=e.get("content",""), date=e.get("date",""))
                         for e in merged[:5]],
                first_seen=old["first_seen"],
                last_reinforced=new_last,
                reinforcement_count=new_count,
            )
            new_confidence = score_confidence(temp_pattern)
            
            self.adapter.run(
                "UPDATE patterns SET confidence=?, examples_json=?, last_reinforced=?, "
                "reinforcement_count=? WHERE anchor=?",
                (new_confidence, json.dumps(merged), new_last, new_count, pattern.anchor)
            )
        else:
            # Fresh pattern
            self.adapter.run(
                "INSERT OR REPLACE INTO patterns "
                "(id, anchor, type, confidence, examples_json, first_seen, last_reinforced, "
                "reinforcement_count, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pattern.id, pattern.anchor, pattern.type, pattern.confidence,
                 json.dumps([{"factId": e.fact_id, "content": e.content, "date": e.date}
                            for e in pattern.examples]),
                 pattern.first_seen or now, pattern.last_reinforced or now,
                 pattern.reinforcement_count, now)
            )
    
    def query_tier2(
        self,
        pattern_type: Optional[str] = None,
        anchor: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> List[Pattern]:
        query = ("SELECT id, anchor, type, confidence, examples_json, first_seen, last_reinforced, "
                 "reinforcement_count, created_at FROM patterns WHERE 1=1")
        params: list = []
        
        if pattern_type:
            query += " AND type = ?"
            params.append(pattern_type)
        if anchor:
            query += " AND anchor = ?"
            params.append(anchor)
        if min_confidence > 0:
            query += " AND confidence >= ?"
            params.append(min_confidence)
        
        query += " ORDER BY confidence DESC, last_reinforced DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        rows = self.adapter.all(query, tuple(params))
        patterns = []
        for r in rows:
            examples = []
            try:
                examples_raw = json.loads(r.get("examples_json", "[]"))
                examples = [PatternExample(
                    fact_id=e.get("factId", ""), content=e.get("content", ""), date=e.get("date", "")
                ) for e in examples_raw]
            except (json.JSONDecodeError, TypeError):
                pass
            
            patterns.append(Pattern(
                id=r["id"], anchor=r["anchor"], type=r["type"],
                confidence=float(r["confidence"]), examples=examples,
                first_seen=r["first_seen"], last_reinforced=r["last_reinforced"],
                reinforcement_count=int(r["reinforcement_count"]),
            ))
        return patterns
    
    # ── Cross-Tier Links ──────────────────────────────────────────
    
    def link_fact_to_pattern(
        self, fact_id: str, pattern_id: str,
        relation: str = "example_of",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.adapter.run(
            "INSERT OR REPLACE INTO pattern_links (pattern_id, fact_id, relation_type, created_at) "
            "VALUES (?, ?, ?, ?)",
            (pattern_id, fact_id, relation, now)
        )
    
    def query_facts_by_pattern(self, pattern_id: str, limit: int = 20) -> List[PersonalFact]:
        """Cross-tier: find all facts linked to a specific pattern."""
        if not self.config.enable_cross_tier_queries:
            return []
        
        rows = self.adapter.all(
            "SELECT f.id, f.content, f.category, f.session_id, f.created_at "
            "FROM personal_facts f "
            "JOIN pattern_links pl ON f.id = pl.fact_id "
            "WHERE pl.pattern_id = ? "
            "ORDER BY f.created_at DESC LIMIT ?",
            (pattern_id, limit)
        )
        return [
            PersonalFact(
                id=r["id"], content=r["content"], category=r["category"],
                created_at=r["created_at"], session_id=r.get("session_id", "default"),
            )
            for r in rows
        ]
    
    def query_patterns_by_fact(self, fact_id: str) -> List[Pattern]:
        """Cross-tier: find all patterns linked to a specific fact."""
        if not self.config.enable_cross_tier_queries:
            return []
        
        rows = self.adapter.all(
            "SELECT p.id, p.anchor, p.type, p.confidence, p.examples_json, "
            "p.first_seen, p.last_reinforced, p.reinforcement_count, p.created_at "
            "FROM patterns p "
            "JOIN pattern_links pl ON p.id = pl.pattern_id "
            "WHERE pl.fact_id = ? "
            "ORDER BY p.confidence DESC",
            (fact_id,)
        )
        patterns = []
        for r in rows:
            examples = []
            try:
                examples_raw = json.loads(r.get("examples_json", "[]"))
                examples = [PatternExample(
                    fact_id=e.get("factId", ""), content=e.get("content", ""), date=e.get("date", "")
                ) for e in examples_raw]
            except (json.JSONDecodeError, TypeError):
                pass
            patterns.append(Pattern(
                id=r["id"], anchor=r["anchor"], type=r["type"],
                confidence=float(r["confidence"]), examples=examples,
                first_seen=r["first_seen"], last_reinforced=r["last_reinforced"],
                reinforcement_count=int(r["reinforcement_count"]),
            ))
        return patterns
    
    # ── Convenience ───────────────────────────────────────────────
    
    def ingest_fact(self, fact: PersonalFact, zone: str = "hot") -> Optional[Pattern]:
        """Save fact + extract pattern + link them. Uses reinforcement if pattern exists."""
        from fusion.shinon.shinon_patterns import extract_pattern
        
        self.save_fact(fact, zone)
        pattern = extract_pattern(fact)
        if pattern:
            self.save_pattern(pattern)
            # Link fact to pattern (use anchor to find pattern ID after possible reinforcement)
            existing = self.adapter.all(
                "SELECT id FROM patterns WHERE anchor=?", (pattern.anchor,)
            )
            if existing:
                self.link_fact_to_pattern(fact.id, existing[0]["id"])
        return pattern
    
    def prune_low_confidence_patterns(self) -> int:
        """Remove patterns below minimum confidence threshold."""
        rows = self.adapter.all(
            "SELECT id FROM patterns WHERE confidence < ? AND reinforcement_count <= 1",
            (self.config.min_confidence_to_keep,)
        )
        for row in rows:
            self.adapter.run("DELETE FROM pattern_links WHERE pattern_id=?", (row["id"],))
            self.adapter.run("DELETE FROM patterns WHERE id=?", (row["id"],))
        return len(rows)
    
    def get_stats(self) -> Dict[str, Any]:
        """Return memory statistics."""
        facts = self.adapter.all(
            "SELECT zone, COUNT(*) as cnt FROM personal_facts GROUP BY zone"
        )
        patterns = self.adapter.all(
            "SELECT type, COUNT(*) as cnt FROM patterns GROUP BY type"
        )
        links = self.adapter.all("SELECT COUNT(*) as cnt FROM pattern_links")
        return {
            "facts_by_zone": {r["zone"]: r["cnt"] for r in facts},
            "total_facts": sum(r["cnt"] for r in facts),
            "patterns_by_type": {r["type"]: r["cnt"] for r in patterns},
            "total_patterns": sum(r["cnt"] for r in patterns),
            "total_links": links[0]["cnt"] if links else 0,
        }

    # ── Combined Query: Character Memory ──────────────────────────

    def query_character_memory(
        self,
        session_id: Optional[str] = None,
        min_confidence: float = 0.3,
        tier1_limit: int = 10,
        tier2_limit: int = 10,
    ) -> Dict[str, Any]:
        """Combined Tier1 + Tier2 query for character context assembly.

        Fetches relevant facts AND patterns in one call, with cross-tier
        linking resolved. This is the primary query used by ShinonEngine
        to assemble PromptContext for the prompt generator.

        Returns a dict with:
          - facts: List[PersonalFact] — recent Tier1 facts
          - patterns: List[Pattern] — high-confidence Tier2 patterns
          - linked: List[{pattern, facts}] — cross-tier linked pairs
          - stats: summary stats

        Args:
            session_id: Optional session filter for facts
            min_confidence: Minimum pattern confidence (default 0.3)
            tier1_limit: Max facts to return
            tier2_limit: Max patterns to return

        Returns:
            Dict with facts, patterns, linked, stats
        """
        # Fetch Tier 1 facts
        facts = self.query_tier1(
            session_id=session_id,
            zone="hot",
            limit=tier1_limit,
        )
        if len(facts) < tier1_limit:
            mid_facts = self.query_tier1(
                session_id=session_id,
                zone="mid",
                limit=tier1_limit - len(facts),
            )
            facts.extend(mid_facts)

        # Fetch Tier 2 patterns
        patterns = self.query_tier2(
            min_confidence=min_confidence,
            limit=tier2_limit,
        )

        # Cross-tier linking
        linked = []
        if self.config.enable_cross_tier_queries and patterns:
            for pattern in patterns[:5]:  # Link top 5 patterns
                linked_facts = self.query_facts_by_pattern(pattern.id, limit=5)
                if linked_facts:
                    linked.append({
                        "pattern": pattern,
                        "facts": linked_facts,
                    })

        stats = self.get_stats()

        return {
            "facts": facts,
            "patterns": patterns,
            "linked": linked,
            "stats": stats,
        }
