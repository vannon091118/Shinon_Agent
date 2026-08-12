#!/usr/bin/env python3
"""
Goal-Chain Live Dashboard Server — SSE-basiert, kein Meta-Refresh.
v2: Aggregiert nun (.agents/skills/live/) Skill-Snapshots.

Endpoints:
  GET /                 → HTML Dashboard (HTML+JS, SSE consumer)
  GET /events           → SSE Stream (alle Updates als JSON)
  GET /api/skills       → JSON Snapshot aller Skills (curl-friendly)
  GET /api/state        → Volle State-Übersicht (TIDs + Skills)
  GET /api/skill/<name> → Token-saving snapshot einer einzelnen Skill (text)

Pollt SQLite (TIDs) AND .agents/skills/live/ (Skill-Updates) alle 500ms,
pusht Diffs via Server-Sent Events.
"""

import sqlite3
import json
import time
import threading
import http.server
import os
import sys
import re
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DB_PATH = PROJECT_ROOT / ".agents/skills/goal-chain/db/tid-state.db"
LIVE_DIR = PROJECT_ROOT / ".agents/skills/live"
REGISTRY = LIVE_DIR / "registry.jsonl"
LIMEN_DB_PATH = PROJECT_ROOT / "limen-main" / "data" / "limen.db"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4200
_raw_run_id = sys.argv[2] if len(sys.argv) > 2 else None

LIVE_DIR.mkdir(parents=True, exist_ok=True)

def _auto_detect_run() -> str | None:
    """Find the best active run: prefer non-complete runs, then most recent."""
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        # Prefer runs with PENDING TIDs, ordered by most recent (highest run_id suffix)
        row = cur.execute("""
            SELECT run_id, COUNT(*) as total,
                   SUM(CASE WHEN status IN ('DONE','ROOT_CAUSE_DONE','FAILED') THEN 1 ELSE 0 END) as finished
            FROM tasks GROUP BY run_id
            HAVING total > finished
            ORDER BY finished DESC, run_id DESC LIMIT 1
        """).fetchone()
        if not row:
            row = cur.execute("""
                SELECT run_id FROM tasks GROUP BY run_id
                ORDER BY run_id DESC LIMIT 1
            """).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None

# Resolve RUN_ID: explicit arg > auto-detect > UNSEEDED fallback
if _raw_run_id and _raw_run_id not in ("UNSEEDED", "None", ""):
    RUN_ID = _raw_run_id
else:
    detected = _auto_detect_run()
    RUN_ID = detected if detected else _raw_run_id  # keep UNSEEDED if nothing found
    if detected:
        print(f"[dashboard] Auto-detected run: {RUN_ID}", file=sys.stderr)

# ─── SSE Clients ───────────────────────────────────────────────────
sse_clients = []
last_state_hash = ""
lock = threading.Lock()

# ─── Skill Snapshot Reader ─────────────────────────────────────────

STATE_ICONS = {
    "active":    ("🔄", "#3b82f6"),
    "idle":      ("⏸️ ",  "#6b7280"),
    "done":      ("✅", "#10b981"),
    "error":     ("❌", "#ef4444"),
    "planning":  ("🧠", "#f59e0b"),
    "pending":   ("⏳", "#9ca3af"),
}


def parse_snapshot_md(path: Path):
    """Extract YAML frontmatter from a skill snapshot markdown file."""
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    fm_match = re.search(r"^---\s*\n(.+?)\n---", text, re.DOTALL)
    if not fm_match:
        return {"skill": path.stem, "state": "unknown", "summary": text[:200]}
    fm = fm_match.group(1)
    parsed = {"skill": path.stem}
    for line in fm.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip().strip('"')
        if key == "tags":
            val = [t.strip() for t in val.lstrip("[").rstrip("]").split(",") if t.strip()]
        elif key in ("activation_count",):
            # Numeric fields: coerce to int so JSON consumers don't see strings
            try: val = int(val)
            except (ValueError, TypeError): pass
        parsed[key] = val
    # Extract first non-frontmatter line as summary
    body = text[fm_match.end():]
    summary = ""
    for line in body.splitlines():
        line = line.strip().lstrip("#").strip()
        if line and not line.startswith(">"):
            summary = line
            break
    parsed["summary"] = summary[:200]
    parsed["icon"], parsed["color"] = STATE_ICONS.get(parsed.get("state", ""), ("⏳", "#9ca3af"))
    parsed["file"] = str(path)
    parsed["mtime"] = path.stat().st_mtime
    parsed["size_bytes"] = path.stat().st_size
    return parsed


def get_skills_state() -> list:
    """Read all .agents/skills/live/*.md → list of dicts."""
    if not LIVE_DIR.exists():
        return []
    skills = []
    for p in sorted(LIVE_DIR.glob("*.md")):
        data = parse_snapshot_md(p)
        if data:
            skills.append(data)
    return skills


def get_recent_registry(n: int = 10) -> list:
    """Tail of registry.jsonl (newest entries)."""
    if not REGISTRY.exists():
        return []
    try:
        with REGISTRY.open("r") as f:
            lines = f.readlines()
        out = []
        for line in lines[-n:]:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return list(reversed(out))
    except Exception:
        return []


# ─── DB Polling ────────────────────────────────────────────────────

def get_db_state():
    """Read TID state from DB."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if RUN_ID:
        where = f"WHERE run_id='{RUN_ID}'"
    else:
        row = cur.execute("SELECT run_id FROM tasks ORDER BY phase_seq DESC LIMIT 1").fetchone()
        where = f"WHERE run_id='{row['run_id']}'" if row else "WHERE 1=0"

    total = cur.execute(f"SELECT COUNT(*) as c FROM tasks {where}").fetchone()["c"]
    done = cur.execute(f"SELECT COUNT(*) as c FROM tasks {where} AND status='DONE'").fetchone()["c"]
    inprog = cur.execute(f"SELECT COUNT(*) as c FROM tasks {where} AND status='IN_PROGRESS'").fetchone()["c"]
    failed = cur.execute(f"SELECT COUNT(*) as c FROM tasks {where} AND status='FAILED'").fetchone()["c"]
    skipped = cur.execute(f"SELECT COUNT(*) as c FROM tasks {where} AND status='SKIPPED'").fetchone()["c"]
    root_cause_done = cur.execute(f"SELECT COUNT(*) as c FROM tasks {where} AND status='ROOT_CAUSE_DONE'").fetchone()["c"]
    pending = total - done - inprog - failed - skipped - root_cause_done
    pct = int(done * 100 // total) if total > 0 else 0

    goal_row = cur.execute(f"SELECT goal, projekt, run_id FROM tasks {where} LIMIT 1").fetchone()
    goal = goal_row["goal"] if goal_row else "N/A"
    projekt = goal_row["projekt"] if goal_row else "N/A"
    active_run_id = goal_row["run_id"] if goal_row else "N/A"

    tids = []
    for r in cur.execute(f"SELECT tid, phase, phase_section, status, skill_name, requires_approval, template_id FROM tasks {where} ORDER BY phase_seq"):
        tids.append({
            "tid": r["tid"], "phase": r["phase"], "section": r["phase_section"],
            "status": r["status"], "skill": (r["skill_name"] or "").split("/")[-1],
            "checkpoint": r["requires_approval"] == 1, "template": r["template_id"] or "—",
        })

    next_row = cur.execute(f"""
        SELECT t.tid FROM tasks t {where} AND t.status='PENDING'
        AND NOT EXISTS (
            SELECT 1 FROM pre_tasks pt JOIN tasks pt2 ON pt.pre_tid=pt2.tid
            WHERE pt.tid=t.tid AND pt2.status NOT IN ('DONE','SKIPPED','ROOT_CAUSE_DONE')
        )
        ORDER BY t.phase_seq LIMIT 1
    """).fetchone()
    next_tid = next_row["tid"] if next_row else None

    evil_twins = []
    for r in cur.execute(f"SELECT phase_section, status FROM tasks {where} AND phase_section LIKE 'evil-twin%' ORDER BY phase_seq"):
        evil_twins.append({"section": r["phase_section"], "status": r["status"]})

    decisions = []
    for r in cur.execute(f"""
        SELECT d.tid, d.decision_type, d.decision_value, d.timestamp
        FROM dispatcher_decisions d JOIN tasks t ON d.tid=t.tid {where}
        ORDER BY d.decision_id DESC LIMIT 5
    """):
        decisions.append({"tid": r["tid"].split("-")[-1][:18], "type": r["decision_type"][:10], "value": r["decision_value"][:20]})

    phases = {}
    for r in cur.execute(f"SELECT phase, status, COUNT(*) as c FROM tasks {where} GROUP BY phase, status"):
        p = r["phase"]
        if p not in phases:
            phases[p] = {"done": 0, "active": 0, "pending": 0, "failed": 0}
        s = r["status"]
        if s == "DONE": phases[p]["done"] = r["c"]
        elif s == "IN_PROGRESS": phases[p]["active"] = r["c"]
        elif s == "FAILED": phases[p]["failed"] = r["c"]
        elif s == "PENDING": phases[p]["pending"] = r["c"]
    conn.close()

    return {
        "total": total, "done": done, "inprog": inprog, "failed": failed,
        "skipped": skipped, "root_cause_done": root_cause_done,
        "pending": pending, "pct": pct, "goal": goal, "projekt": projekt, "run_id": active_run_id,
        "tids": tids, "next_tid": next_tid, "evil_twins": evil_twins, "decisions": decisions,
        "phases": phases, "time": time.strftime("%H:%M:%S"),
    }


def get_full_state():
    """Combined payload: TIDs + Skills + Recent Registry."""
    db_state = get_db_state()
    skills = get_skills_state()
    recent = get_recent_registry(12)
    db_state["skills"] = skills
    db_state["skills_count"] = len(skills)
    db_state["recent_registry"] = recent
    return db_state


def get_key_status():
    """Query LIMEN providers table for key health, budgets, and status."""
    if not LIMEN_DB_PATH.exists():
        return {"available": False, "db_path": str(LIMEN_DB_PATH), "keys": [],
                "summary": {"total": 0, "active": 0, "cooldown": 0, "dead": 0}}

    try:
        conn = sqlite3.connect(str(LIMEN_DB_PATH))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Check if providers table exists
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if "providers" not in tables:
            conn.close()
            return {"available": False, "db_path": str(LIMEN_DB_PATH), "keys": [],
                    "summary": {"total": 0, "active": 0, "cooldown": 0, "dead": 0},
                    "note": "providers table not found — LIMEN DB may not be initialized"}

        # Query all providers with budget info
        rows = cur.execute("""
            SELECT key_id, provider, deployment, status, cooldown_until,
                   observed_itpm, observed_rpm, meta_json, last_used_at, priority
            FROM providers ORDER BY priority, deployment
        """).fetchall()

        keys = []
        summary = {"total": 0, "active": 0, "cooldown": 0, "dead": 0}
        for r in rows:
            summary["total"] += 1
            status = r["status"]
            if status == "active": summary["active"] += 1
            elif status == "cooldown": summary["cooldown"] += 1
            elif status == "dead": summary["dead"] += 1

            # Parse budget from meta_json
            tokens_used = r["observed_itpm"] or 0
            tokens_max = 1_000_000
            requests_used = r["observed_rpm"] or 0
            requests_max = 500

            try:
                meta = json.loads(r["meta_json"] or "{}")
                if isinstance(meta, dict):
                    tokens_max = int(meta.get("tokens_max", tokens_max))
                    requests_max = int(meta.get("requests_max", requests_max))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            token_pct = (tokens_used / tokens_max * 100) if tokens_max > 0 else 0
            request_pct = (requests_used / requests_max * 100) if requests_max > 0 else 0

            # Determine health color
            if status == "dead":
                health_color = "#ef4444"
                health_pct = 0
            elif status == "cooldown":
                health_color = "#f59e0b"
                health_pct = 50
            elif token_pct > 90 or request_pct > 90:
                health_color = "#f59e0b"
                health_pct = max(100 - token_pct, 100 - request_pct)
            else:
                health_color = "#10b981"
                health_pct = 100 - max(token_pct, request_pct)

            # Short fingerprint for display
            key_id_display = r["key_id"].split(":")[-1][:8] if ":" in r["key_id"] else r["key_id"][:8]

            keys.append({
                "id": key_id_display,
                "full_id": r["key_id"],
                "provider": r["provider"] or r["deployment"],
                "deployment": r["deployment"],
                "status": status,
                "cooldown_until": r["cooldown_until"],
                "tokens_used": tokens_used,
                "tokens_max": tokens_max,
                "token_pct": round(token_pct, 1),
                "requests_used": requests_used,
                "requests_max": requests_max,
                "request_pct": round(request_pct, 1),
                "health_pct": round(health_pct, 1),
                "health_color": health_color,
                "last_used": (r["last_used_at"] or "")[11:19] if r["last_used_at"] else "",
                "priority": r["priority"],
            })

        conn.close()
        return {"available": True, "db_path": str(LIMEN_DB_PATH), "keys": keys, "summary": summary}
    except Exception as e:
        return {"available": False, "db_path": str(LIMEN_DB_PATH), "keys": [],
                "summary": {"total": 0, "active": 0, "cooldown": 0, "dead": 0},
                "error": str(e)}


def poll_loop():
    """Background: poll DB+Live-dir, push SSE events on change."""
    global last_state_hash
    while True:
        try:
            state = get_full_state()
            state_json = json.dumps(state, ensure_ascii=False)
            state_hash = str(hash(state_json))
            if state_hash != last_state_hash:
                last_state_hash = state_hash
                with lock:
                    dead = []
                    for client in sse_clients:
                        try:
                            client.append(state_json)
                        except Exception:
                            dead.append(client)
                    for d in dead:
                        sse_clients.remove(d)
        except Exception as e:
            print(f"[poll] Error: {e}", file=sys.stderr)
        time.sleep(0.5)


# ─── HTTP Handlers ─────────────────────────────────────────────────
HTML_FILE = Path(__file__).parent / "live-dashboard.html"


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silent

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            with open(HTML_FILE, "rb") as f:
                self._send(200, "text/html; charset=utf-8", f.read())

        elif path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            queue = []
            with lock:
                sse_clients.append(queue)
            try:
                while True:
                    if queue:
                        data = queue.pop(0)
                        msg = f"data: {data}\n\n"
                        self.wfile.write(msg.encode("utf-8"))
                        self.wfile.flush()
                    else:
                        time.sleep(0.2)
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                with lock:
                    if queue in sse_clients:
                        sse_clients.remove(queue)

        elif path == "/api/skills":
            skills = get_skills_state()
            self._send(200, "application/json; charset=utf-8",
                       json.dumps({"count": len(skills), "skills": skills,
                                   "time": time.strftime("%H:%M:%S")},
                                  ensure_ascii=False, indent=2))

        elif path == "/api/state":
            self._send(200, "application/json; charset=utf-8",
                       json.dumps(get_full_state(), ensure_ascii=False, indent=2))

        elif path.startswith("/api/skill/"):
            skill_name = path[len("/api/skill/"):]
            snap = LIVE_DIR / f"{skill_name}.md"
            if snap.exists():
                self._send(200, "text/markdown; charset=utf-8", snap.read_text(encoding="utf-8"))
            else:
                self._send(404, "application/json", json.dumps({"error": f"no snapshot for {skill_name}"}))

        elif path == "/api/registry":
            recent = get_recent_registry(50)
            self._send(200, "application/json; charset=utf-8",
                       json.dumps({"count": len(recent), "entries": recent}, ensure_ascii=False, indent=2))

        elif path == "/api/keys":
            self._send(200, "application/json; charset=utf-8",
                       json.dumps(get_key_status(), ensure_ascii=False, indent=2))

        else:
            self._send(404, "application/json", json.dumps({"error": "not found", "hint": "try /events, /api/skills, /api/state, /api/skill/<name>"}))


# ─── HTML — Skill-Tile Section wird vom .html-Template gerendert ────
SENTINEL_CSS = "/* skill-tile-injected v1 */"
SENTINEL_JS  = "<!-- skill-tile-injected v1 -->"


def generate_html():
    """Validate HTML exists — CSS and JS are now hardcoded inline (no injection needed).

    Previously this function injected CSS/JS after </style> which broke rendering.
    Now the HTML file is self-contained. Sentinel check prevents re-injection.
    """
    if not HTML_FILE.exists():
        HTML_FILE.write_text("<html><body><h1>Dashboard HTML missing</h1></body></html>", encoding="utf-8")
        return

    existing = HTML_FILE.read_text(encoding="utf-8")

    # Clean up any old injections (idempotent — only runs once)
    if SENTINEL_CSS in existing:
        # Remove old sentinel and all injected CSS blocks
        import re
        # Strip everything between sentinel and </style> (old broken injections)
        existing = re.sub(r'\n/\* skill-tile-injected.*?</style>', '</style>', existing, flags=re.DOTALL)
        # Also remove any orphaned /* skill-tile styles */ blocks
        existing = re.sub(r'/\* skill-tile styles \*/.*?}(?=\s*\n/\* skill-tile)', '', existing, flags=re.DOTALL)
        existing = existing.replace(SENTINEL_CSS, '/* --- skill-tile CSS now inline in <style> --- */')

    if SENTINEL_JS in existing:
        # Remove old injected JS sections
        existing = re.sub(r'<!-- skill-tile-injected.*?</script>\s*\n', '', existing, flags=re.DOTALL)
        existing = existing.replace(SENTINEL_JS, '<!-- skill-tile JS now inline in main <script> -->')

    # Remove duplicate skill-tile-section blocks (keep only the one in the original HTML body)
    # Find all <!-- skill-tile-section --> markers and keep only the first
    parts = existing.split('<!-- skill-tile-section -->')
    if len(parts) > 2:
        # Keep first occurrence (the one in the HTML body), remove the rest
        existing = parts[0] + '<!-- skill-tile-section -->' + parts[1]
        # Remove duplicate sections (everything after the first complete section)
        # Find </script> after the first section and cut there
        script_end = existing.find('</script>', existing.find('<!-- skill-tile-section -->'))
        if script_end > 0:
            body_end = existing.find('</body>')
            if body_end > script_end:
                existing = existing[:script_end+9] + '\n\n' + existing[body_end:]

    HTML_FILE.write_text(existing, encoding="utf-8")


def _port_check(port: int) -> bool:
    """Returns True if port is FREE on loopback (safe to bind)."""
    import socket as _s
    s = _s.socket()
    s.settimeout(0.5)
    try:
        return s.connect_ex(("127.0.0.1", port)) != 0
    finally:
        s.close()


# ─── Main ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    generate_html()
    print(f"[dashboard] HTML written: {HTML_FILE}")
    print(f"[dashboard] Live dir:    {LIVE_DIR}")

    poll_thread = threading.Thread(target=poll_loop, daemon=True)
    poll_thread.start()

    # Port-busy protection
    if not _port_check(PORT):
        print(f"[dashboard] ❌ Port {PORT} already in use on loopback.", file=sys.stderr)
        print(f"[dashboard]   Either stop the previous server, or pick another port.", file=sys.stderr)
        print(f"[dashboard]   Common fix: pkill -9 -f live-dashboard-server && restart", file=sys.stderr)
        sys.exit(2)

    try:
        server = http.server.HTTPServer(("127.0.0.1", PORT), DashboardHandler)
    except OSError as e:
        print(f"[dashboard] ❌ Bind failed on port {PORT}: {e}", file=sys.stderr)
        sys.exit(2)

    print(f"[dashboard] Local SSE server: http://127.0.0.1:{PORT}")
    print(f"[dashboard] Events stream:   http://127.0.0.1:{PORT}/events")
    print(f"[dashboard] Skills API:     http://127.0.0.1:{PORT}/api/skills")
    print(f"[dashboard] State API:      http://127.0.0.1:{PORT}/api/state")
    print(f"[dashboard] Registry API:   http://127.0.0.1:{PORT}/api/registry")
    print(f"[dashboard] Skill context:  http://127.0.0.1:{PORT}/api/skill/<name>")
    print(f"[dashboard] Poll: 500ms · Push on change only")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[dashboard] Shutting down.")
        server.shutdown()
