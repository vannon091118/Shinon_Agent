#!/usr/bin/env node
/**
 * Goal-Chain Live Dashboard Server — Node.js (zero-dependency)
 *
 * Replaces the Python http.server/SSE approach that dies in background.
 * Uses Node.js built-in `http` module — no npm install needed.
 * HTML polls /api/state via fetch() instead of SSE.
 *
 * Usage:
 *   node live-dashboard-server.mjs [PORT] [RUN_ID]
 *   node live-dashboard-server.mjs 4200 R20260812-033226
 */

import http from 'node:http';
import { readFileSync, readdirSync, statSync, existsSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, '..', '..', '..', '..');
const HTML_FILE = join(__dirname, 'live-dashboard.html');
const DB_PATH = join(__dirname, '..', 'db', 'tid-state.db');
const LIVE_DIR = join(PROJECT_ROOT, '.agents', 'skills', 'live');
const REGISTRY = join(LIVE_DIR, 'registry.jsonl');
const LIMEN_DB = join(PROJECT_ROOT, 'limen-main', 'data', 'limen.db');

const PORT = parseInt(process.argv[2]) || 4200;
const RUN_ID = process.argv[3] || autoDetectRun() || 'UNSEEDED';

function autoDetectRun() {
  if (!existsSync(DB_PATH)) return null;
  try {
    const script = `
import sqlite3, sys
conn = sqlite3.connect(${JSON.stringify(DB_PATH)})
cur = conn.cursor()
row = cur.execute("""
  SELECT run_id FROM tasks GROUP BY run_id
  HAVING COUNT(*) > SUM(CASE WHEN status IN ('DONE','ROOT_CAUSE_DONE','FAILED') THEN 1 ELSE 0 END)
  ORDER BY SUM(CASE WHEN status IN ('DONE','ROOT_CAUSE_DONE') THEN 1 ELSE 0 END) DESC, run_id DESC LIMIT 1
""").fetchone()
if not row:
  row = cur.execute("SELECT run_id FROM tasks GROUP BY run_id ORDER BY run_id DESC LIMIT 1").fetchone()
conn.close()
print(row[0] if row else '')
`;
    return execSync(`python3 -c "${script.replace(/"/g, '\\"')}"`, { encoding: 'utf8' }).trim() || null;
  } catch { return null; }
}

// ─── MIME types ────────────────────────────────────────────────────
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

function send(res, code, contentType, body) {
  res.writeHead(code, {
    'Content-Type': contentType,
    'Cache-Control': 'no-cache',
    'Access-Control-Allow-Origin': '*',
  });
  res.end(body);
}

function sendJSON(res, code, data) {
  send(res, code, 'application/json; charset=utf-8', JSON.stringify(data, null, 2));
}

// ─── DB Queries via Python (zero-dependency SQLite access) ─────────

function queryDB(sql, params = []) {
  // Escape for Python triple-quoted string
  const pySql = sql.replace(/\\/g, '\\\\').replace(/'''/g, "\\'\\'\\'");
  const pyParams = JSON.stringify(params);
  const script = `
import sqlite3, json, sys
conn = sqlite3.connect(${JSON.stringify(DB_PATH)})
conn.row_factory = sqlite3.Row
cur = conn.cursor()
try:
    cur.execute("""${pySql}""", json.loads('''${pyParams}'''))
    rows = [dict(r) for r in cur.fetchall()]
    print(json.dumps(rows, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"error": str(e)}), file=sys.stderr)
    print("[]")
conn.close()
`;
  try {
    const out = execSync(`python3 -c "${script.replace(/"/g, '\\"')}"`, {
      encoding: 'utf8', timeout: 5000,
    });
    return JSON.parse(out.trim() || '[]');
  } catch (e) {
    console.error('[db] query failed:', e.message);
    return [];
  }
}

function queryDBOne(sql, params = []) {
  const rows = queryDB(sql, params);
  return rows.length > 0 ? rows[0] : null;
}

// ─── API: /api/state ───────────────────────────────────────────────

function getFullState() {
  const runId = RUN_ID === 'UNSEEDED' ? autoDetectRun() || 'UNSEEDED' : RUN_ID;
  if (runId === 'UNSEEDED' || !existsSync(DB_PATH)) {
    return {
      total: 0, done: 0, inprog: 0, failed: 0, skipped: 0,
      root_cause_done: 0, pending: 0, pct: 0,
      goal: 'No DB', projekt: 'N/A', run_id: 'UNSEEDED',
      tids: [], next_tid: null, evil_twins: [], decisions: [],
      phases: {}, skills: [], skills_count: 0, recent_registry: [],
      time: new Date().toTimeString().slice(0, 8),
    };
  }

  const where = `WHERE run_id='${runId}'`;
  const total = queryDBOne(`SELECT COUNT(*) as c FROM tasks ${where}`)?.['c'] || 0;
  const done = queryDBOne(`SELECT COUNT(*) as c FROM tasks ${where} AND status='DONE'`)?.['c'] || 0;
  const inprog = queryDBOne(`SELECT COUNT(*) as c FROM tasks ${where} AND status='IN_PROGRESS'`)?.['c'] || 0;
  const failed = queryDBOne(`SELECT COUNT(*) as c FROM tasks ${where} AND status='FAILED'`)?.['c'] || 0;
  const skipped = queryDBOne(`SELECT COUNT(*) as c FROM tasks ${where} AND status='SKIPPED'`)?.['c'] || 0;
  const rcd = queryDBOne(`SELECT COUNT(*) as c FROM tasks ${where} AND status='ROOT_CAUSE_DONE'`)?.['c'] || 0;
  const pending = total - done - inprog - failed - skipped - rcd;
  const pct = total > 0 ? Math.floor(done * 100 / total) : 0;

  const goalRow = queryDBOne(`SELECT goal, projekt, run_id FROM tasks ${where} LIMIT 1`);
  const goal = goalRow?.goal || 'N/A';
  const projekt = goalRow?.projekt || 'N/A';
  const activeRunId = goalRow?.run_id || 'N/A';

  const tidRows = queryDB(
    `SELECT tid, phase, phase_section, status, skill_name, requires_approval, template_id FROM tasks ${where} ORDER BY phase_seq`
  );

  const nextRow = queryDBOne(`
    SELECT t.tid FROM tasks t ${where} AND t.status='PENDING'
    AND NOT EXISTS (
      SELECT 1 FROM pre_tasks pt JOIN tasks pt2 ON pt.pre_tid=pt2.tid
      WHERE pt.tid=t.tid AND pt2.status NOT IN ('DONE','SKIPPED','ROOT_CAUSE_DONE')
    )
    ORDER BY t.phase_seq LIMIT 1
  `);

  const etRows = queryDB(
    `SELECT phase_section, status FROM tasks ${where} AND phase_section LIKE 'evil-twin%' ORDER BY phase_seq`
  );

  const decRows = queryDB(`
    SELECT d.tid, d.decision_type, d.decision_value, d.created_at as timestamp
    FROM dispatcher_decisions d JOIN tasks t ON d.tid=t.tid ${where}
    ORDER BY d.decision_id DESC LIMIT 5
  `);

  const phaseRows = queryDB(
    `SELECT phase, status, COUNT(*) as c FROM tasks ${where} GROUP BY phase, status`
  );

  // Root cause decisions per TID (for expandable detail in dashboard)
  const rootCauseRows = queryDB(`
    SELECT d.tid, d.decision_type, d.decision_value, d.rationale
    FROM dispatcher_decisions d JOIN tasks t ON d.tid = t.tid ${where}
    AND d.decision_type IN ('ROOT_CAUSE', 'ROOT_CAUSE_RESET')
    ORDER BY d.decision_id DESC
  `);
  const root_causes = {};
  for (const r of (rootCauseRows || [])) {
    if (!root_causes[r.tid]) root_causes[r.tid] = [];
    root_causes[r.tid].push({
      type: r.decision_type,
      value: (r.decision_value || '').slice(0, 300),
      rationale: (r.rationale || '').slice(0, 200),
    });
  }

  return {
    total, done, inprog, failed, skipped, root_cause_done: rcd,
    pending, pct, goal, projekt, run_id: activeRunId,
    tids: tidRows.map(r => ({
      tid: r.tid, phase: r.phase, section: r.phase_section,
      status: r.status, skill: (r.skill_name || '').split('/').pop() || '',
      checkpoint: r.requires_approval === 1, template: r.template_id || '—',
    })),
    next_tid: nextRow?.tid || null,
    evil_twins: etRows.map(r => ({ section: r.phase_section, status: r.status })),
    decisions: decRows.map(r => ({
      tid: (r.tid || '').split('-').pop()?.slice(0, 18) || '?',
      type: (r.decision_type || '').slice(0, 10),
      value: (r.decision_value || '').slice(0, 20),
    })),
    phases: buildPhases(phaseRows),
    skills: getSkillsState(),
    skills_count: getSkillsState().length,
    root_causes,
    recent_registry: getRecentRegistry(12),
    time: new Date().toTimeString().slice(0, 8),
  };
}

function buildPhases(rows) {
  const phases = {};
  for (const r of rows) {
    const p = r.phase;
    if (!phases[p]) phases[p] = { done: 0, active: 0, pending: 0, failed: 0 };
    const s = r.status;
    if (s === 'DONE') phases[p].done = r.c;
    else if (s === 'IN_PROGRESS') phases[p].active = r.c;
    else if (s === 'FAILED') phases[p].failed = r.c;
    else if (s === 'PENDING') phases[p].pending = r.c;
  }
  return phases;
}

// ─── API: /api/skills ──────────────────────────────────────────────

function getSkillsState() {
  if (!existsSync(LIVE_DIR)) return [];
  const skills = [];
  try {
    for (const f of readdirSync(LIVE_DIR).sort()) {
      if (!f.endsWith('.md')) continue;
      const data = parseSnapshotMd(join(LIVE_DIR, f));
      if (data) skills.push(data);
    }
  } catch (e) { /* ignore */ }
  return skills;
}

function parseSnapshotMd(filePath) {
  try {
    const text = readFileSync(filePath, 'utf-8');
    const fm = text.match(/^---\s*\n(.+?)\n---/s);
    const parsed = { skill: filePath.split('/').pop().replace('.md', '') };
    if (fm) {
      for (const line of fm[1].split('\n')) {
        const idx = line.indexOf(':');
        if (idx < 0) continue;
        const key = line.slice(0, idx).trim();
        let val = line.slice(idx + 1).trim().replace(/^"(.*)"$/, '$1');
        if (key === 'tags') val = val.replace(/^\[|\]$/g, '').split(',').map(t => t.trim()).filter(Boolean);
        parsed[key] = val;
      }
      const body = text.slice(fm.index + fm[0].length);
      const firstLine = body.split('\n').find(l => l.trim() && !l.trim().startsWith('>') && !l.trim().startsWith('#'))?.trim().replace(/^#+\s*/, '');
      parsed.summary = (firstLine || '').slice(0, 200);
    }
    const st = statSync(filePath);
    parsed.mtime = st.mtimeMs;
    parsed.size_bytes = st.size;
    parsed.state = parsed.state || 'connected';
    return parsed;
  } catch { return null; }
}

function getRecentRegistry(n) {
  if (!existsSync(REGISTRY)) return [];
  try {
    const lines = readFileSync(REGISTRY, 'utf-8').split('\n').filter(Boolean);
    return lines.slice(-n).map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean).reverse();
  } catch { return []; }
}

// ─── API: /api/keys ────────────────────────────────────────────────

function getKeyStatus() {
  if (!existsSync(LIMEN_DB)) {
    return { available: false, db_path: LIMEN_DB, keys: [], summary: { total: 0, active: 0, cooldown: 0, dead: 0 } };
  }
  try {
    const script = `
import sqlite3, json
conn = sqlite3.connect(${JSON.stringify(LIMEN_DB)})
conn.row_factory = sqlite3.Row
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
if "providers" not in tables:
    print(json.dumps({"error": "no providers table"}))
    conn.close()
    raise SystemExit(0)
rows = cur.execute("""
  SELECT key_id, provider, deployment, status, cooldown_until,
         observed_itpm, observed_rpm, meta_json, last_used_at, priority
  FROM providers ORDER BY priority, deployment
""").fetchall()
keys = []; summary = {"total":0,"active":0,"cooldown":0,"dead":0}
for r in rows:
    summary["total"] += 1
    st = r["status"]; summary[st] = summary.get(st, 0) + 1
    tokens_used = r["observed_itpm"] or 0; tokens_max = 1000000
    requests_used = r["observed_rpm"] or 0; requests_max = 500
    try:
        meta = json.loads(r["meta_json"] or "{}")
        if isinstance(meta, dict):
            tokens_max = int(meta.get("tokens_max", tokens_max))
            requests_max = int(meta.get("requests_max", requests_max))
    except: pass
    token_pct = (tokens_used / tokens_max * 100) if tokens_max > 0 else 0
    request_pct = (requests_used / requests_max * 100) if requests_max > 0 else 0
    if st == "dead": health = "danger"; hp = 0
    elif st == "cooldown": health = "warn"; hp = 50
    elif token_pct > 90 or request_pct > 90: health = "warn"; hp = max(100 - token_pct, 100 - request_pct)
    else: health = "success"; hp = 100 - max(token_pct, request_pct)
    key_id_display = r["key_id"].split(":")[-1][:8] if ":" in r["key_id"] else r["key_id"][:8]
    keys.append({
        "id": key_id_display, "full_id": r["key_id"], "provider": r["provider"] or r["deployment"],
        "deployment": r["deployment"], "status": st, "cooldown_until": r["cooldown_until"],
        "tokens_used": tokens_used, "tokens_max": tokens_max, "token_pct": round(token_pct, 1),
        "requests_used": requests_used, "requests_max": requests_max, "request_pct": round(request_pct, 1),
        "health_pct": round(hp, 1), "health_color": health,
        "last_used": (r["last_used_at"] or "")[11:19] if r["last_used_at"] else "",
        "priority": r["priority"]
    })
conn.close()
print(json.dumps({"available":True, "db_path":${JSON.stringify(LIMEN_DB)},"keys":keys,"summary":summary}, ensure_ascii=False))
`;
    const out = execSync(`python3 -c "${script.replace(/"/g, '\\"')}"`, { encoding: 'utf8', timeout: 5000 });
    return JSON.parse(out.trim());
  } catch (e) {
    return { available: false, db_path: LIMEN_DB, keys: [], summary: { total: 0, active: 0, cooldown: 0, dead: 0 }, error: e.message };
  }
}

// ─── Frontmatter injection (CSS/JS already inline) ─────────────────

function prepareHTML() {
  if (!existsSync(HTML_FILE)) {
    console.error(`[dashboard] HTML file not found: ${HTML_FILE}`);
    process.exit(1);
  }
  let html = readFileSync(HTML_FILE, 'utf-8');

  // Replace EventSource SSE with fetch() polling
  // The HTML currently uses: const evtSource = new EventSource("/events");
  // We replace it with a setInterval fetch('/api/state') pattern
  const oldSSE = `const evtSource = new EventSource("/events");\nlet lastUpdate = 0;\n\nevtSource.onmessage = function(event) {\n  const state = JSON.parse(event.data);\n  const now = Date.now();\n  if (now - lastUpdate < 200) return;\n  lastUpdate = now;\n  render(state);\n};\n\nevtSource.onerror = function() {\n  document.getElementById('conn-dot').className = 'conn-dot conn-dot-dead';\n  document.getElementById('conn-status').textContent = 'Reconnecting...';\n};\n\nevtSource.onopen = function() {\n  document.getElementById('conn-dot').className = 'conn-dot conn-dot-live';\n  document.getElementById('conn-status').textContent = '🔌 Connected · Live SSE';\n};`;

  const newFetch = `// fetch()-based polling (replacing SSE for server stability)\nlet lastUpdate = 0;\nlet pollTimer = null;\nlet connFailures = 0;\n\nasync function pollState() {\n  try {\n    const res = await fetch('/api/state');\n    if (!res.ok) throw new Error('HTTP ' + res.status);\n    const state = await res.json();\n    render(state);\n    connFailures = 0;\n    document.getElementById('conn-dot').className = 'conn-dot conn-dot-live';\n    document.getElementById('conn-status').textContent = '🔌 Connected · Live Fetch';\n  } catch(e) {\n    connFailures++;\n    if (connFailures > 3) {\n      document.getElementById('conn-dot').className = 'conn-dot conn-dot-dead';\n      document.getElementById('conn-status').textContent = 'Reconnecting (' + connFailures + ')...';\n    }\n  }\n  pollTimer = setTimeout(pollState, settings.refreshRate || 500);\n}\n\npollState();`;

  if (html.includes('new EventSource("/events")')) {
    html = html.replace(oldSSE, newFetch);
  }

  return html;
}

// ═══════════════════════════════════════════════════════════════════
// HTTP Server
// ═══════════════════════════════════════════════════════════════════

const htmlContent = prepareHTML();

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
  const path = url.pathname;

  // Static files
  if (path === '/' || path === '/index.html') {
    send(res, 200, 'text/html; charset=utf-8', htmlContent);
    return;
  }

  if (path === '/dashboard.html') {
    send(res, 200, 'text/html; charset=utf-8', htmlContent);
    return;
  }

  // API endpoints
  if (path === '/api/state') {
    try {
      const state = getFullState();
      sendJSON(res, 200, state);
    } catch (e) {
      sendJSON(res, 500, { error: e.message });
    }
    return;
  }

  if (path === '/api/skills') {
    const skills = getSkillsState();
    sendJSON(res, 200, { count: skills.length, skills, time: new Date().toTimeString().slice(0, 8) });
    return;
  }

  if (path.startsWith('/api/skill/')) {
    const name = path.slice('/api/skill/'.length);
    const snap = join(LIVE_DIR, `${name}.md`);
    if (existsSync(snap)) {
      send(res, 200, 'text/markdown; charset=utf-8', readFileSync(snap, 'utf-8'));
    } else {
      sendJSON(res, 404, { error: `no snapshot for ${name}` });
    }
    return;
  }

  if (path === '/api/keys') {
    try {
      const keys = getKeyStatus();
      sendJSON(res, 200, keys);
    } catch (e) {
      sendJSON(res, 500, { error: e.message });
    }
    return;
  }

  if (path === '/api/registry') {
    const recent = getRecentRegistry(50);
    sendJSON(res, 200, { count: recent.length, entries: recent });
    return;
  }

  // Legacy SSE endpoint — return an empty stream so old clients don't hang
  if (path === '/events') {
    send(res, 200, 'text/event-stream', ': SSE disabled — use fetch() polling\n\n');
    return;
  }

  // 404
  sendJSON(res, 404, { error: 'not found', hint: 'try /api/state, /api/skills, /api/keys' });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[dashboard] Node.js server: http://127.0.0.1:${PORT}`);
  console.log(`[dashboard] DB: ${DB_PATH}  Run: ${RUN_ID}`);
  console.log(`[dashboard] API: /api/state /api/skills /api/keys /api/registry`);
  console.log(`[dashboard] Mode: fetch() polling (no SSE) — restart-safe`);
});

// Graceful shutdown
process.on('SIGTERM', () => { server.close(); process.exit(0); });
process.on('SIGINT', () => { server.close(); process.exit(0); });
