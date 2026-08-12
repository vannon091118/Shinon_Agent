#!/usr/bin/env python3
"""
JSONL → SQLite Migration — Promtguard claim-log.jsonl → pipeline-state.db

Reads the append-only claim-log.jsonl, deduplicates by claim_id
(latest-wins), and upserts into the centralized pipeline-state.db
→ claims table.

Schema: interface-specs/pipeline-state.schema.sql § claims
  claim_id          TEXT PRIMARY KEY    — CLAIM-SYX-001
  pipeline_run_id   TEXT                — latest run that touched this claim
  source_component  TEXT                — promtguard | karma
  status            TEXT                — unverified | supported | confirmed | refuted | conflicted
  verified_by       TEXT                — karma | promtguard
  verified_at       TEXT                — ISO timestamp
  claim_text        TEXT                — Full claim statement
  evidence          TEXT                — File:line:code references
  confidence        TEXT                — high | medium | low
  source_res        TEXT                — RES-NNN origin
  claim_origin      TEXT                — decision-extraction | explicit-declaration
  idempotency_fp    TEXT                — SHA-256 fingerprint
  alternatives_json TEXT                — JSON array of rejected alternatives
  created_at        TEXT                — ISO timestamp
  updated_at        TEXT                — ISO timestamp

Usage:
  python3 tools/migrate-claims-to-sqlite.py [--dry-run] [--source-dir .promtset/state] [--db pipeline-state.db]
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def create_schema(conn: sqlite3.Connection) -> None:
    """Create the claims table + indexes from pipeline-state.schema.sql."""
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
        CREATE INDEX IF NOT EXISTS idx_claims_source ON claims(source_component);
    """)


def parse_jsonl(path: Path) -> list[dict]:
    """Read JSONL, return parsed lines (non-empty, valid JSON)."""
    claims = []
    if not path.exists():
        print(f"  ⚠️  {path} not found — skipping")
        return claims

    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                claims.append(data)
            except json.JSONDecodeError as exc:
                print(f"  ⚠️  Line {i}: invalid JSON — {exc}")
    return claims


def deduplicate(claims: list[dict]) -> dict[str, dict]:
    """Deduplicate by claim_id: latest timestamp wins."""
    by_id: dict[str, dict] = {}
    for c in claims:
        cid = c.get("id", "")
        if not cid:
            continue
        # TEST-RESIDUE claims are noise — skip
        if "TEST-RESIDUE" in c.get("claim", ""):
            continue

        ts = c.get("timestamp", c.get("created_at", ""))
        existing = by_id.get(cid)
        if existing is None or ts > existing.get("timestamp", existing.get("created_at", "")):
            by_id[cid] = c
    return by_id


def upsert_claims(conn: sqlite3.Connection, claims: dict[str, dict], dry_run: bool = False) -> int:
    """Upsert deduplicated claims into the claims table. Returns count."""
    now = datetime.now(timezone.utc).isoformat()
    count = 0

    for cid, c in sorted(claims.items()):
        claim_text = c.get("claim", "")
        status = c.get("status", "unverified")
        evidence = c.get("evidence", "")
        confidence = c.get("confidence", "medium")
        source_res = c.get("source_res", "")
        claim_origin = c.get("claim_origin", "explicit-declaration")
        idempotency_fp = c.get("idempotency_fingerprint", "")
        verified_by_raw = c.get("verified_by", c.get("verified_by_res", ""))
        # Map to schema-valid values: CHECK(verified_by IN ('karma','promtguard'))
        verified_by_map = {"manual": "promtguard", "": None, "karma": "karma", "promtguard": "promtguard"}
        verified_by = verified_by_map.get(verified_by_raw, "promtguard")
        verified_at = c.get("verified_at", "")
        created_at = c.get("timestamp", c.get("created_at", now))
        alternatives = c.get("alternatives_rejected", [])
        alternatives_json = json.dumps(alternatives, ensure_ascii=False) if alternatives else "[]"

        # Map JSONL status to schema status
        status_map = {
            "unverified": "unverified",
            "verified": "confirmed",
            "refuted": "refuted",
            "refined": "unverified",
            "unknown": "unverified",
        }
        db_status = status_map.get(status, "unverified")

        if dry_run:
            print(f"  [DRY RUN] {cid}: {db_status} | {claim_text[:80]}...")
            count += 1
            continue

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
                source_res = excluded.source_res,
                claim_origin = excluded.claim_origin,
                idempotency_fp = excluded.idempotency_fp,
                alternatives_json = excluded.alternatives_json,
                updated_at = excluded.updated_at
        """, (
            cid, db_status, verified_by or None, verified_at or None,
            claim_text, evidence, confidence, source_res, claim_origin,
            idempotency_fp, alternatives_json, created_at, now,
        ))
        count += 1

    return count


def main():
    dry_run = "--dry-run" in sys.argv

    # Parse args
    source_dir = Path(".promtset/state")
    db_path = Path("pipeline-state.db")

    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--source-dir" and i + 1 < len(args):
            source_dir = Path(args[i + 1])
        elif arg == "--db" and i + 1 < len(args):
            db_path = Path(args[i + 1])

    claim_log = source_dir / "claim-log.jsonl"

    print(f"📦 JSONL → SQLite Migration")
    print(f"   Source: {claim_log}")
    print(f"   Target: {db_path}")
    if dry_run:
        print(f"   Mode:   DRY RUN (no writes)")
    print()

    # 1. Read JSONL
    raw_claims = parse_jsonl(claim_log)
    print(f"   Read {len(raw_claims)} raw claims from JSONL")

    # 2. Deduplicate
    unique = deduplicate(raw_claims)
    print(f"   After dedup: {len(unique)} unique claims")
    print(f"   Skipped: {len(raw_claims) - len(unique)} duplicates/test-residues")

    # 3. Open DB, create schema
    if not dry_run:
        conn = sqlite3.connect(str(db_path))
        create_schema(conn)
    else:
        conn = None

    # 4. Upsert
    count = upsert_claims(conn or sqlite3.connect(":memory:"), unique, dry_run=dry_run)
    status = "(dry run)" if dry_run else "✅"
    print(f"   {status} Upserted {count} claims")

    # 5. Stats
    if not dry_run and conn:
        conn.commit()
        cur = conn.cursor()
        for row in cur.execute(
            "SELECT status, COUNT(*) FROM claims GROUP BY status ORDER BY COUNT(*) DESC"
        ):
            print(f"   {row[0]:>12}: {row[1]}")
        conn.close()

    print()
    print("✅ Migration complete" if not dry_run else "✅ Dry run complete — use without --dry-run to write")


if __name__ == "__main__":
    main()
