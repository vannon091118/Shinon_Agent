#!/usr/bin/env python3
"""
KARMA Audit Trail Report Generator

Runs AuditTrailVerifier against the KARMA events table and outputs
a combined JSON report with:
  - Full verification results (tamper/gap detection)
  - Hash chain links for visualization
  - Tamper indicator status
  - Latest events summary

Usage:
    python3 karma-audit.py                    # uses default KARMA DB
    python3 karma-audit.py --project PZ       # scope to project
    python3 karma-audit.py --output /tmp/audit.json
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_karma_db_path() -> Path:
    """Find the central Shinon KARMA database."""
    framework_dir = os.environ.get(
        "KARMA_FRAMEWORK_DIR",
        str(Path(os.environ.get("SHINON_HOME", str(Path.home() / ".shinon"))) / "data" / "karma"),
    )
    return Path(framework_dir) / os.environ.get("KARMA_DB_FILENAME", "karma.db")


def get_raw_events(db_path: Path, project: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Read raw events with hash chain from the KARMA DB using sqlite3 directly."""
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        # Check if hash columns exist
        cols = conn.execute("PRAGMA table_info(events)").fetchall()
        col_names = [c[1] for c in cols]
        has_hash = "event_hash" in col_names

        if has_hash:
            query = (
                "SELECT id, event_type, project, payload, timestamp, "
                "correlation_id, event_hash, prev_event_hash "
                "FROM events WHERE 1=1"
            )
        else:
            query = (
                "SELECT id, event_type, project, payload, timestamp, "
                "correlation_id "
                "FROM events WHERE 1=1"
            )

        params: List[Any] = []
        if project:
            query += " AND project = ?"
            params.append(project)
        query += " ORDER BY id ASC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, tuple(params)).fetchall()
        events = []
        for r in rows:
            d = dict(r)
            # Truncate payload for visualization
            try:
                payload = json.loads(d.get("payload", "{}"))
                d["payload_summary"] = str(payload)[:120]
            except (json.JSONDecodeError, TypeError):
                d["payload_summary"] = str(d.get("payload", ""))[:120]
            d["payload"] = d.get("payload", "")[:200]
            events.append(d)
        return events
    finally:
        conn.close()


def run_verifier(db_path: Path, project: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Run the full AuditTrailVerifier from KARMA."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "karma-main"))
        from karma.core.persistence import PersistenceLayer, PersistenceConfig
        from karma.core.replay import AuditTrailVerifier

        config = PersistenceConfig(framework_dir=db_path.parent, db_filename=db_path.name)
        persistence = PersistenceLayer(config)
        verifier = AuditTrailVerifier(persistence)
        report = verifier.verify(project=project, limit=500)
        return report.to_dict()
    except Exception as exc:
        return {
            "passed": False,
            "total_events": 0,
            "verified_events": 0,
            "tampered_events": 0,
            "gap_events": 0,
            "reason": f"Verifier failed: {exc}",
            "error": str(exc),
        }


def build_chain_visualization(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build simplified chain link data for frontend visualization.

    Each link shows: event ID, hash prefix (8 chars), prev link, status.
    """
    links = []
    prev_hash = "genesis"
    for i, event in enumerate(events):
        event_hash = event.get("event_hash", "")
        recorded_prev = event.get("prev_event_hash", "")

        # Determine link status
        if not event_hash:
            status = "no_hash"  # pre-v5 event
            color = "#6b7280"
        elif not recorded_prev and i > 0:
            status = "gap"
            color = "#f59e0b"
        elif recorded_prev and recorded_prev != prev_hash:
            status = "broken"
            color = "#ef4444"
        elif event_hash == prev_hash:
            status = "verified" if i > 0 else "genesis"
            color = "#10b981" if i > 0 else "#3b82f6"
        else:
            status = "verified"
            color = "#10b981"

        links.append({
            "id": event.get("id"),
            "event_type": event.get("event_type", ""),
            "hash_prefix": event_hash[:8] if event_hash else "—",
            "prev_hash_prefix": recorded_prev[:8] if recorded_prev else ("genesis" if i == 0 else "—"),
            "expected_prev": prev_hash[:8],
            "status": status,
            "color": color,
            "timestamp": (event.get("timestamp", "") or "")[:19],
            "correlation_id": (event.get("correlation_id", "") or "")[:16],
            "is_first": i == 0,
            "is_last": i == len(events) - 1,
        })

        if event_hash:
            prev_hash = event_hash

    return links


def main() -> None:
    parser = argparse.ArgumentParser(description="KARMA Audit Trail Report")
    parser.add_argument("--project", default=None, help="Scope to project")
    parser.add_argument("--output", default=None, help="Output JSON file path")
    parser.add_argument("--limit", type=int, default=100, help="Max events to read")
    parser.add_argument("--skip-verify", action="store_true", help="Skip full verifier run")
    args = parser.parse_args()

    db_path = get_karma_db_path()
    db_exists = db_path.exists()

    # Get raw events
    events = get_raw_events(db_path, project=args.project, limit=args.limit)

    # Build chain visualization
    chain_links = build_chain_visualization(events)

    # Run verifier
    if not args.skip_verify and db_exists:
        verification = run_verifier(db_path, project=args.project)
    else:
        verification = None

    # Build summary
    has_hashes = any(e.get("event_hash") for e in events)
    chain_intact = verification.get("passed", False) if verification else (has_hashes and len(events) > 0)

    # Determine tamper status
    if not db_exists:
        tamper_status = "no_db"
        tamper_message = "KARMA DB nicht gefunden — keine Events"
        tamper_color = "#6b7280"
    elif not events:
        tamper_status = "empty"
        tamper_message = "Keine Events im Audit-Trail"
        tamper_color = "#6b7280"
    elif verification and verification.get("tampered_events", 0) > 0:
        tamper_status = "tampered"
        tamper_message = f"TAMPER DETECTED: {verification['tampered_events']} events"
        tamper_color = "#ef4444"
    elif verification and verification.get("gap_events", 0) > 0:
        tamper_status = "gaps"
        tamper_message = f"Chain gaps: {verification['gap_events']} events"
        tamper_color = "#f59e0b"
    elif chain_intact:
        tamper_status = "intact"
        tamper_message = "Hash-Chain intakt ✓"
        tamper_color = "#10b981"
    else:
        tamper_status = "unknown"
        tamper_message = "Verifikation nicht möglich"
        tamper_color = "#6b7280"

    report = {
        "available": db_exists and len(events) > 0,
        "db_path": str(db_path),
        "db_exists": db_exists,
        "tamper_status": tamper_status,
        "tamper_message": tamper_message,
        "tamper_color": tamper_color,
        "total_events": len(events),
        "has_hash_chain": has_hashes,
        "chain_intact": chain_intact,
        "chain_start": events[0].get("event_hash", "")[:8] if events else None,
        "chain_end": events[-1].get("event_hash", "")[:8] if events else None,
        "chain_links": chain_links,
        "verification": verification,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": args.project or "ALL",
    }

    output_json = json.dumps(report, indent=2, ensure_ascii=False)
    print(output_json)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)


if __name__ == "__main__":
    main()
