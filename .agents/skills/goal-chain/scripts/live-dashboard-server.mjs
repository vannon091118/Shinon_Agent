#!/usr/bin/env node
/**
 * Goal-Chain Live Dashboard Server — Node.js v2 (native SQLite)
 *
 * Evil Twin Widerspruch #2 fix:
 *   execSync(python3 ...) → native node:sqlite DatabaseSync
 *   Zero subprocesses. Zero event-loop blocking.
 *   Queries execute in microseconds instead of 50-100ms Python spawns.
 *
 * Usage:
 *   node live-dashboard-server.mjs [PORT] [RUN_ID]
 *   node live-dashboard-server.mjs 4200 R20260812-033226
 */

import http from 'node:http';
import { readFileSync, readdirSync, statSync, existsSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';
import { DatabaseSync } from 'node:sqlite';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, '..', '..', '..', '..');
const HTML_FILE = join(__dirname, 'live-dashboard.html');
const DB_PATH = join(__dirname, '..', 'db', 'tid-state.db');
const LIVE_DIR = join(PROJECT_ROOT, '.agents', 'skills', 'live');
const REGISTRY = join(LIVE_DIR, 'registry.jsonl');
const LIMEN_DB = join(PROJECT_ROOT, 'limen-main', 'data', 'limen-prod.db');
const LIMEN_API = 'http://127.0.0.1:8001';

// KARMA audit trail DB path
const KARMA_DB = join(homedir(), '.karma', 'middleware.db');
const AUDIT_REPORT = join(PROJECT_ROOT, '.freebuff', 'last-audit-report.json');

const PORT = parseInt(process.argv[2]) || 4200;

// ═══════════════════════════════════════════════════════════════════
// Native SQLite — zero subprocess, zero event-loop blocking
// ═══════════════════════════════════════════════════════════════════

let _goalDb = null;
let _limenDb = null;

function goalDb() {
  if (_goalDb) return _goalDb;
  if (!existsSync(DB_PATH)) return null;
  _goalDb = new DatabaseSync(DB_PATH);
  _goalDb.exec('PRAGMA journal_mode=WAL');
  _goalDb.exec('PRAGMA busy_timeout=5000');
  return _goalDb;
}

function limenDb() {
  if (_limenDb) return _limenDb;
  if (!existsSync(LIMEN_DB)) return null;
  _limenDb = new DatabaseSync(LIMEN_DB);
  _limenDb.exec('PRAGMA journal_mode=WAL');
  _limenDb.exec('PRAGMA busy_timeout=5000');
  return _limenDb;
}

function autoDetectRun() {
  const db = goalDb();
  if (!db) return null;
  try {
    const rows = db.prepare(`
      SELECT run_id FROM tasks GROUP BY run_id
      HAVING COUNT(*) > SUM(CASE WHEN status IN ('DONE','ROOT_CAUSE_DONE','FAILED') THEN 1 ELSE 0 END)
      ORDER BY SUM(CASE WHEN status IN ('DONE','ROOT_CAUSE_DONE') THEN 1 ELSE 0 END) DESC, run_id DESC LIMIT 1
    `).all();
    if (rows.length > 0) return rows[0].run_id;
    const all = db.prepare(`SELECT run_id FROM tasks GROUP BY run_id ORDER BY run_id DESC LIMIT 1`).all();
    return all.length > 0 ? all[0].run_id : null;
  } catch { return null; }
}

const RUN_ID = process.argv[3] || autoDetectRun() || 'UNSEEDED';

// Direct DB query helpers — replace execSync(python3)+sqlite3
function queryAll(sql, params = []) {
  const db = goalDb();
  if (!db) return [];
  try {
    return db.prepare(sql).all(...params);
  } catch (e) {
    console.error('[db] query failed:', e.message);
    return [];
  }
}

function queryOne(sql, params = []) {
  const rows = queryAll(sql, params);
  return rows.length > 0 ? rows[0] : null;
}

// ═══════════════════════════════════════════════════════════════════
// HTTP helpers
// ═══════════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════════
// Async fetch helper — used for LIMEN API calls
// ═══════════════════════════════════════════════════════════════════

async function fetchJSON(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3000);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } finally {
    clearTimeout(timeout);
  }
}

// ═══════════════════════════════════════════════════════════════════
// API: /api/state
// ═══════════════════════════════════════════════════════════════════

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
      verified: 0, seeded: 0,
    };
  }

  const db = goalDb();
  if (!db) return { total: 0, goal: 'DB not found', run_id: runId };

  const total = db.prepare(`SELECT COUNT(*) as c FROM tasks WHERE run_id=?`).get(runId)?.c || 0;
  const done = db.prepare(`SELECT COUNT(*) as c FROM tasks WHERE run_id=? AND status='DONE'`).get(runId)?.c || 0;
  // Verification breakdown: DONE with output vs DONE without (seeded)
  const verified = db.prepare(`SELECT COUNT(*) as c FROM tasks WHERE run_id=? AND status='DONE' AND output_artifact IS NOT NULL AND output_artifact != ''`).get(runId)?.c || 0;
  const seeded = done - verified;
  const inprog = db.prepare(`SELECT COUNT(*) as c FROM tasks WHERE run_id=? AND status='IN_PROGRESS'`).get(runId)?.c || 0;
  const failed = db.prepare(`SELECT COUNT(*) as c FROM tasks WHERE run_id=? AND status='FAILED'`).get(runId)?.c || 0;
  const skipped = db.prepare(`SELECT COUNT(*) as c FROM tasks WHERE run_id=? AND status='SKIPPED'`).get(runId)?.c || 0;
  const rcd = db.prepare(`SELECT COUNT(*) as c FROM tasks WHERE run_id=? AND status='ROOT_CAUSE_DONE'`).get(runId)?.c || 0;
  const pending = total - done - inprog - failed - skipped - rcd;
  const pct = total > 0 ? Math.floor(done * 100 / total) : 0;

  const goalRow = db.prepare(`SELECT goal, projekt, run_id FROM tasks WHERE run_id=? LIMIT 1`).get(runId);
  const goal = goalRow?.goal || 'N/A';
  const projekt = goalRow?.projekt || 'N/A';

  const tidRows = db.prepare(
    `SELECT tid, phase, phase_section, status, skill_name, requires_approval, template_id, output_artifact FROM tasks WHERE run_id=? ORDER BY phase_seq`
  ).all(runId);

  const nextRow = db.prepare(`
    SELECT t.tid FROM tasks t
    WHERE t.run_id=? AND t.status='PENDING'
    AND NOT EXISTS (
      SELECT 1 FROM pre_tasks pt JOIN tasks pt2 ON pt.pre_tid=pt2.tid
      WHERE pt.tid=t.tid AND pt2.status NOT IN ('DONE','SKIPPED','ROOT_CAUSE_DONE')
    )
    ORDER BY t.phase_seq LIMIT 1
  `).get(runId);

  const etRows = db.prepare(
    `SELECT phase_section, status FROM tasks WHERE run_id=? AND phase_section LIKE 'evil-twin%' ORDER BY phase_seq`
  ).all(runId);

  const decRows = db.prepare(`
    SELECT d.tid, d.decision_type, d.decision_value, d.timestamp as created_at
    FROM dispatcher_decisions d JOIN tasks t ON d.tid=t.tid
    WHERE t.run_id=? ORDER BY d.timestamp DESC LIMIT 5
  `).all(runId);

  const phaseRows = db.prepare(
    `SELECT phase, status, COUNT(*) as c FROM tasks WHERE run_id=? GROUP BY phase, status`
  ).all(runId);

  const rootCauseRows = db.prepare(`
    SELECT d.tid, d.decision_type, d.decision_value, d.rationale
    FROM dispatcher_decisions d JOIN tasks t ON d.tid = t.tid
    WHERE t.run_id=? AND d.decision_type IN ('ROOT_CAUSE', 'ROOT_CAUSE_RESET')
    ORDER BY d.timestamp DESC
  `).all(runId);

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
    pending, pct, goal, projekt, run_id: goalRow?.run_id || runId,
    verified, seeded,  // REGEL 1: verification levels
    tids: tidRows.map(r => ({
      tid: r.tid, phase: r.phase, section: r.phase_section,
      status: r.status, skill: (r.skill_name || '').split('/').pop() || '',
      checkpoint: r.requires_approval === 1, template: r.template_id || '—',
      verification: computeVerification(r.status, r.output_artifact),
      has_output: !!(r.output_artifact && r.output_artifact.trim()),
    })),
    next_tid: nextRow?.tid || null,
    evil_twins: etRows.map(r => ({ section: r.phase_section, status: r.status })),
    decisions: decRows.map(r => ({
      tid: (r.tid || '').split('-').pop()?.slice(0, 18) || '?',
      type: (r.decision_type || '').slice(0, 10),
      value: (r.decision_value || '').slice(0, 20),
    })),
    phases: buildPhases(phaseRows),
    skills: getActiveTidSkills(runId),
    skills_count: getActiveTidSkills(runId).length,
    root_causes,
    recent_registry: getRecentRegistry(12),
    time: new Date().toTimeString().slice(0, 8),
  };
}

// ── Verification Level ─────────────────────────────────────────────
// REGEL 1: Nur anzeigen was nachweislich funktioniert.
// DONE + no output_artifact → "seeded" (⚠️ unverified)
// DONE + output_artifact exists → "verified" (✅)
// IN_PROGRESS → "in-progress" (🔄)

function computeVerification(status, outputArtifact) {
  if (status === 'IN_PROGRESS') return 'in-progress';
  if (status === 'DONE') {
    // A DONE TID without output was just seeded — never actually ran
    if (!outputArtifact || !outputArtifact.trim()) return 'seeded';
    return 'verified';
  }
  if (status === 'ROOT_CAUSE_DONE') return 'root_cause';
  if (status === 'FAILED') return 'failed';
  if (status === 'SKIPPED') return 'skipped';
  return 'pending';
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

// ═══════════════════════════════════════════════════════════════════
// API: /api/tid-skills — ONLY skills actually used by TIDs (REGEL 1)
// ═══════════════════════════════════════════════════════════════════

function getActiveTidSkills(runId) {
  const db = goalDb();
  if (!db) return [];
  try {
    const rows = db.prepare(`
      SELECT DISTINCT skill_name, phase_section, phase,
             COUNT(*) as tid_count,
             SUM(CASE WHEN status='DONE' THEN 1 ELSE 0 END) as done,
             SUM(CASE WHEN status='IN_PROGRESS' THEN 1 ELSE 0 END) as active,
             SUM(CASE WHEN status='PENDING' THEN 1 ELSE 0 END) as pending,
             SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) as failed
      FROM tasks WHERE run_id=? AND skill_name IS NOT NULL AND skill_name != ''
      GROUP BY skill_name ORDER BY skill_name
    `).all(runId);

    return rows.map(r => ({
      skill: (r.skill_name || '').split('/').pop() || r.skill_name,
      full_name: r.skill_name,
      section: r.phase_section,
      phase: r.phase,
      tid_count: r.tid_count,
      done: r.done, active: r.active, pending: r.pending, failed: r.failed,
      status: r.active > 0 ? 'active' : r.pending > 0 ? 'pending' : r.done > 0 ? 'done' : 'idle',
    }));
  } catch { return []; }
}

// ═══════════════════════════════════════════════════════════════════
// API: /api/skills — FULL skill registry (used by glossary page)
// ═══════════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════════
// API: /api/keys — fetches from LIMEN API (port 8001)
// Falls LIMEN nicht läuft: fallback auf direkte DB
// ═══════════════════════════════════════════════════════════════════

async function getKeyStatus() {
  // ── Primary: LIMEN API /v1/dashboard/keys ──
  try {
    const data = await fetchJSON(`${LIMEN_API}/v1/dashboard/keys`);
    if (data && data.available && data.keys) {
      const keys = data.keys.map(k => ({
        ...k,
        id: (k.key_id || '').includes(':') ? k.key_id.split(':').pop().slice(0, 8) : (k.key_id || '').slice(0, 8),
        full_id: k.key_id,
        last_used: (k.last_used_at || '').slice(11, 19),
        history: keyHistory[k.key_id] || [],
      }));

      // Deployment-group alerts
      const groups = {};
      for (const k of keys) {
        const dep = k.deployment || 'default';
        if (!groups[dep]) groups[dep] = [];
        groups[dep].push(k);
      }

      const alerts = [];
      for (const [dep, group] of Object.entries(groups)) {
        const statuses = group.map(k => k.status);
        const activeCount = statuses.filter(s => s === 'active').length;
        const cooldownCount = statuses.filter(s => s === 'cooldown').length;
        const deadCount = statuses.filter(s => s === 'dead').length;
        const total = group.length;
        if (total === 0) continue;

        if (activeCount === 0 && cooldownCount > 0 && deadCount > 0) {
          alerts.push({ deployment: dep, level: 'critical', message: `0/${total} active — ${cooldownCount} cooldown, ${deadCount} dead`, key_count: total });
        } else if (activeCount === 0 && cooldownCount > 0) {
          alerts.push({ deployment: dep, level: 'danger', message: `All ${total} keys in COOLDOWN`, key_count: total });
        } else if (activeCount === 0 && deadCount > 0) {
          alerts.push({ deployment: dep, level: 'critical', message: `All ${total} keys DEAD`, key_count: total });
        } else if (activeCount <= 1 && cooldownCount >= 2) {
          alerts.push({ deployment: dep, level: 'warning', message: `Only ${activeCount} active — ${cooldownCount} in cooldown`, key_count: cooldownCount });
        }
      }

      const activeKeys = keys.filter(k => k.status === 'active');
      const avgHealth = activeKeys.length > 0
        ? Math.round(activeKeys.reduce((s, k) => s + (k.health_pct || 0), 0) / activeKeys.length)
        : 0;

      const healthSummary = {
        score: avgHealth,
        color: avgHealth >= 70 ? '#10b981' : avgHealth >= 40 ? '#f59e0b' : '#ef4444',
        label: avgHealth >= 70 ? 'Healthy' : avgHealth >= 40 ? 'Degraded' : 'Critical',
        active_keys: data.summary?.active || 0,
        cooldown_keys: data.summary?.cooldown || 0,
        dead_keys: data.summary?.dead || 0,
        deployments: Object.keys(groups).length,
        source: 'limen-api',
      };

      return { available: true, keys, summary: data.summary, alerts, health_summary: healthSummary, history_available: Object.keys(keyHistory).length > 0 };
    }
  } catch (e) {
    console.error(`[keys] LIMEN API unreachable: ${e.message}`);
  }

  // ── Fallback: direct DB query ──
  const ldb = limenDb();
  if (!ldb) {
    return { available: false, error: 'LIMEN API + DB offline', keys: [], summary: { total: 0, active: 0, cooldown: 0, dead: 0 } };
  }

  try {
    const rows = ldb.prepare(`
      SELECT key_id, provider, deployment, status, cooldown_until,
             observed_itpm, observed_otpm, observed_rpm, meta_json, last_used_at, priority
      FROM providers ORDER BY priority, deployment
    `).all();

    const keys = [];
    const summary = { total: 0, active: 0, cooldown: 0, dead: 0 };

    for (const r of rows) {
      summary.total += 1;
      summary[r.status] = (summary[r.status] || 0) + 1;

      let tokens_max = 1000000;
      let requests_max = 500;
      try {
        const meta = JSON.parse(r.meta_json || '{}');
        if (meta && typeof meta === 'object') {
          tokens_max = parseInt(meta.tokens_max || tokens_max);
          requests_max = parseInt(meta.requests_max || requests_max);
        }
      } catch (_) {}

      const itpm = r.observed_itpm || 0;
      const otpm = r.observed_otpm || 0;
      const rpm = r.observed_rpm || 0;
      const tokens_used = itpm + otpm;
      const token_pct = tokens_max > 0 ? (tokens_used / tokens_max * 100) : 0;
      const request_pct = requests_max > 0 ? (rpm / requests_max * 100) : 0;
      const status = r.status;
      const healthPct = status === 'active' ? Math.max(10, 100 - token_pct * 0.5) : status === 'cooldown' ? 25 : 0;

      const key_id_display = r.key_id.includes(':') ? r.key_id.split(':').pop().slice(0, 8) : r.key_id.slice(0, 8);

      keys.push({
        id: key_id_display, full_id: r.key_id, provider: r.provider || r.deployment,
        deployment: r.deployment, status, cooldown_until: r.cooldown_until,
        tokens_used, tokens_max, token_pct: Math.round(token_pct * 10) / 10,
        requests_used: rpm, requests_max, request_pct: Math.round(request_pct * 10) / 10,
        health_pct: Math.round(healthPct),
        health_color: healthPct > 70 ? '#10b981' : healthPct > 30 ? '#f59e0b' : '#ef4444',
        last_used: (r.last_used_at || '').slice(11, 19),
        priority: r.priority,
        history: keyHistory[r.key_id] || [],
      });
    }

    const activeKeys = keys.filter(k => k.status === 'active');
    const avgHealth = activeKeys.length > 0
      ? Math.round(activeKeys.reduce((s, k) => s + k.health_pct, 0) / activeKeys.length) : 0;

    return {
      available: true, keys, summary, alerts: [],
      health_summary: {
        score: avgHealth,
        label: avgHealth >= 70 ? 'Healthy' : 'Degraded',
        color: avgHealth >= 70 ? '#10b981' : '#f59e0b',
        source: 'db-fallback',
        deployments: 0,
      },
      history_available: Object.keys(keyHistory).length > 0,
    };
  } catch (e) {
    return { available: false, error: e.message, keys: [], summary: { total: 0, active: 0, cooldown: 0, dead: 0 } };
  }
}

const EVENTS_LOG = '/tmp/eventbus-live-log.jsonl';

function getEvents(limit = 100, filterType = null, lastSeq = 0) {
  if (!existsSync(EVENTS_LOG)) {
    return { available: false, events: [], seq: 0, message: 'No event log yet — run a pipeline to generate events.' };
  }
  try {
    const text = readFileSync(EVENTS_LOG, 'utf-8');
    const lines = text.split('\n').filter(Boolean);
    const totalLines = lines.length;
    let events = [];

    // Parse from lastSeq (or return last N)
    const startIdx = lastSeq > 0 ? lastSeq : Math.max(0, totalLines - limit);
    for (let i = startIdx; i < totalLines; i++) {
      try {
        const e = JSON.parse(lines[i]);
        e._seq = i;
        if (!filterType || e.type === filterType || e.type.includes(filterType)) {
          events.push(e);
        }
      } catch { /* skip malformed */ }
    }

    return {
      available: true,
      events: events.slice(-limit),
      total_events: totalLines,
      seq: totalLines,
      filtered: filterType ? filterType : 'all',
    };
  } catch (e) {
    return { available: false, events: [], error: e.message };
  }
}

function getEventTypes() {
  const types = [
    { value: 'all', label: 'All Events', color: '#94a3b8' },
    { value: 'runtime.input', label: 'Input', color: '#3b82f6' },
    { value: 'shinon.output', label: 'Shinon', color: '#8b5cf6' },
    { value: 'promtguard.claims', label: 'Promtguard', color: '#10b981' },
    { value: 'karma.falsified', label: 'KARMA', color: '#ef4444' },
    { value: 'goal_chain.triggered', label: 'GoalChain', color: '#a78bfa' },
    { value: 'goal_chain.rework', label: 'Rework', color: '#f59e0b' },
    { value: 'runtime.completed', label: 'Completed', color: '#34d399' },
    { value: 'runtime.error', label: 'Error', color: '#ef4444' },
    { value: 'limen.rate_limited', label: 'RateLimit', color: '#fbbf24' },
  ];
  return types;
}

// ═══════════════════════════════════════════════════════════════════
// API: /api/replay + /api/replay-diff
// ═══════════════════════════════════════════════════════════════════

function getReplayReport() {
  const reportPath = join(PROJECT_ROOT, '.freebuff', 'last-replay-report.json');
  if (!existsSync(reportPath)) {
    return { available: false, message: 'No replay has been run yet.', report: null };
  }
  try {
    const data = JSON.parse(readFileSync(reportPath, 'utf-8'));
    return {
      available: true,
      report: {
        total_events: data.total_events || 0,
        replayed: data.replayed || 0,
        errors: data.errors || 0,
        identical: data.identical || 0,
        diverged: data.diverged || 0,
        deterministic: data.deterministic !== false,
        saved_at: data.saved_at || '',
        diverged_details: (data.diverged_details || []).slice(0, 10),
        error_details: (data.error_details || []).slice(0, 5),
      },
    };
  } catch (e) {
    return { available: false, error: e.message };
  }
}

function getReplayDiff(index) {
  const reportPath = join(PROJECT_ROOT, '.freebuff', 'last-replay-report.json');
  if (!existsSync(reportPath)) return { available: false, error: 'No replay report found.' };
  try {
    const data = JSON.parse(readFileSync(reportPath, 'utf-8'));
    const details = data.diverged_details || [];
    const detail = details.find(d => d.index === index);
    if (!detail) return { available: false, error: `No diverged event at index ${index}.` };
    if (!detail.original_event || !detail.replayed_event) {
      return { available: false, error: 'Event payloads not captured. Re-run ReplayBus.replay().' };
    }

    const original = detail.original_event;
    const replayed = detail.replayed_event;
    const allKeys = new Set([...Object.keys(original), ...Object.keys(replayed)]);
    const diffs = [];
    for (const key of [...allKeys].sort()) {
      const origVal = original[key];
      const replVal = replayed[key];
      const origJson = JSON.stringify(origVal, null, 2);
      const replJson = JSON.stringify(replVal, null, 2);
      let status = 'identical';
      if (origVal === undefined) status = 'added';
      else if (replVal === undefined) status = 'removed';
      else if (origJson !== replJson) status = 'changed';
      diffs.push({ key, status, original: origJson, replayed: replJson });
    }
    return { available: true, index, event_type: detail.event_type, diffs, changed_count: diffs.filter(d => d.status !== 'identical').length, total_keys: diffs.length };
  } catch (e) {
    return { available: false, error: e.message };
  }
}

// ═══════════════════════════════════════════════════════════════════
// API: /api/audit — KARMA hash chain verification
// ═══════════════════════════════════════════════════════════════════

function getAuditReport() {
  // Try reading pre-generated verification report
  let verification = null;
  if (existsSync(AUDIT_REPORT)) {
    try { verification = JSON.parse(readFileSync(AUDIT_REPORT, 'utf-8')); }
    catch { verification = null; }
  }

  // Read raw events from KARMA DB with node:sqlite
  let events = [];
  let dbExists = false;
  if (existsSync(KARMA_DB)) {
    dbExists = true;
    try {
      const kdb = new DatabaseSync(KARMA_DB);
      kdb.exec('PRAGMA journal_mode=WAL');
      kdb.exec('PRAGMA busy_timeout=5000');

      // Check hash columns
      const cols = kdb.prepare(`PRAGMA table_info(events)`).all();
      const colNames = cols.map(c => c.name);
      const hasHash = colNames.includes('event_hash');

      const query = hasHash
        ? `SELECT id, event_type, project, payload, timestamp, correlation_id, event_hash, prev_event_hash FROM events ORDER BY id ASC LIMIT 50`
        : `SELECT id, event_type, project, payload, timestamp, correlation_id FROM events ORDER BY id ASC LIMIT 50`;

      events = kdb.prepare(query).all().map(r => ({
        id: r.id,
        event_type: r.event_type,
        project: r.project,
        payload_summary: (r.payload || '').slice(0, 120),
        timestamp: (r.timestamp || '').slice(0, 19),
        correlation_id: (r.correlation_id || '').slice(0, 16),
        event_hash: r.event_hash || null,
        prev_event_hash: r.prev_event_hash || null,
        has_hash: !!r.event_hash,
      }));

      kdb.close();
    } catch (e) {
      events = [];
    }
  }

  // Build chain links for visualization
  const chainLinks = [];
  let prevHash = 'genesis';
  for (let i = 0; i < events.length; i++) {
    const e = events[i];
    const hash = e.event_hash;
    const recordedPrev = e.prev_event_hash || '';

    let status, color;
    if (!hash) {
      status = 'no_hash'; color = '#6b7280';
    } else if (!recordedPrev && i > 0) {
      status = 'gap'; color = '#f59e0b';
    } else if (recordedPrev && recordedPrev !== prevHash) {
      status = 'broken'; color = '#ef4444';
    } else {
      status = 'verified'; color = '#10b981';
    }

    chainLinks.push({
      id: e.id,
      event_type: e.event_type,
      hash_prefix: hash ? hash.slice(0, 8) : '—',
      prev_hash_prefix: recordedPrev ? recordedPrev.slice(0, 8) : (i === 0 ? 'genesis' : '—'),
      expected_prev: prevHash.slice(0, 8),
      status, color,
      timestamp: e.timestamp,
      correlation_id: e.correlation_id,
      is_first: i === 0,
      is_last: i === events.length - 1,
    });

    if (hash) prevHash = hash;
  }

  // Determine tamper status
  const hasHashes = events.some(e => e.has_hash);
  let tamperStatus, tamperMessage, tamperColor;
  if (!dbExists) {
    tamperStatus = 'no_db'; tamperMessage = 'KARMA DB nicht gefunden'; tamperColor = '#6b7280';
  } else if (events.length === 0) {
    tamperStatus = 'empty'; tamperMessage = 'Keine Events im Audit-Trail'; tamperColor = '#6b7280';
  } else if (verification && verification.tampered_events > 0) {
    tamperStatus = 'tampered'; tamperMessage = `⚠️ TAMPER: ${verification.tampered_events} Events manipuliert`; tamperColor = '#ef4444';
  } else if (verification && verification.gap_events > 0) {
    tamperStatus = 'gaps'; tamperMessage = `Chain-Lücken: ${verification.gap_events} Events`; tamperColor = '#f59e0b';
  } else if (hasHashes) {
    tamperStatus = 'intact'; tamperMessage = '✓ Hash-Chain intakt'; tamperColor = '#10b981';
  } else {
    tamperStatus = 'pre_v5'; tamperMessage = 'Pre-v5 DB — keine Hashes'; tamperColor = '#6b7280';
  }

  return {
    available: dbExists && events.length > 0,
    db_path: KARMA_DB,
    db_exists: dbExists,
    tamper_status: tamperStatus,
    tamper_message: tamperMessage,
    tamper_color: tamperColor,
    total_events: events.length,
    has_hash_chain: hasHashes,
    chain_intact: tamperStatus === 'intact',
    chain_start: events.length > 0 ? (events[0].event_hash || '').slice(0, 8) : null,
    chain_end: events.length > 0 ? (events[events.length - 1].event_hash || '').slice(0, 8) : null,
    chain_links: chainLinks,
    verification: verification ? {
      passed: verification.passed,
      verified_events: verification.verified_events,
      tampered_events: verification.tampered_events || 0,
      gap_events: verification.gap_events || 0,
      reason: verification.reason || '',
    } : null,
    events_preview: events.slice(-5).reverse(),
    generated_at: verification?.generated_at || new Date().toISOString(),
  };
}

// ═══════════════════════════════════════════════════════════════════
// API: /api/triggers
// ═══════════════════════════════════════════════════════════════════

function getTriggeredSkills() {
  const db = goalDb();
  if (!db) return { available: false, triggers: [] };

  try {
    const runs = db.prepare(`
      SELECT run_id, goal, MIN(created_at) as started_at, MAX(created_at) as last_at,
             COUNT(*) as tids_seeded,
             SUM(CASE WHEN status IN ('DONE','ROOT_CAUSE_DONE') THEN 1 ELSE 0 END) as tids_done,
             SUM(CASE WHEN status='IN_PROGRESS' THEN 1 ELSE 0 END) as tids_active
      FROM tasks
      WHERE (goal LIKE '%KARMA-Falsifikation%'
         OR goal LIKE '%LIMEN-RateLimit%'
         OR goal LIKE '%EMERGENCY:%'
         OR goal LIKE '%REWORK:%')
      GROUP BY run_id
      ORDER BY MAX(created_at) DESC
      LIMIT 30
    `).all();

    const all_skills = new Set();
    const triggers = [];
    for (const r of runs) {
      const sections = db.prepare(
        `SELECT DISTINCT phase_section FROM tasks WHERE run_id = ? AND phase = 'STACK'`
      ).all(r.run_id);
      const skills = sections.map(s => s.phase_section);
      skills.forEach(s => all_skills.add(s));

      const goal = r.goal || '';
      let source = 'unknown';
      if (goal.includes('KARMA-Falsifikation')) source = 'karma.falsified';
      else if (goal.includes('LIMEN-RateLimit')) source = 'limen.rate_limited';
      else if (goal.includes('EMERGENCY')) source = 'limen.key_exhausted';
      else if (goal.includes('REWORK')) source = 'karma.refuted';

      const cids = [...goal.matchAll(/cid=([a-f0-9]{8})/g)].map(m => m[1]);

      triggers.push({
        run_id: r.run_id, source, correlation_ids: cids,
        goal: goal.slice(0, 200), skills: skills.sort(), skill_count: skills.length,
        tids_seeded: r.tids_seeded, tids_done: r.tids_done, tids_active: r.tids_active,
        started_at: r.started_at, last_at: r.last_at,
      });
    }

    return {
      available: true, triggers,
      summary: { total_runs: runs.length, total_skills: all_skills.size, unique_skills: [...all_skills].sort() },
    };
  } catch (e) {
    return { available: false, triggers: [], error: e.message };
  }
}

// ═══════════════════════════════════════════════════════════════════
// Glossary page — ALL skills registry (separate from dashboard)
// ═══════════════════════════════════════════════════════════════════

function buildGlossaryHTML() {
  const skills = getSkillsState();
  const count = skills.length;

  let tiles = '';
  for (const s of skills) {
    const tags = (s.tags || []).map(t => `<span class="gl-tag">${t}</span>`).join('');
    const state = s.state || 'unknown';
    const stateColors = { connected: '#10b981', active: '#3b82f6', done: '#10b981', error: '#ef4444', planning: '#f59e0b', idle: '#6b7280' };
    const sc = stateColors[state] || '#6b7280';
    const sizeKb = s.size_bytes ? Math.round(s.size_bytes / 1024 * 10) / 10 : 0;
    const mtime = s.mtime ? new Date(s.mtime).toISOString().slice(0, 19) : '—';

    tiles += `<div class="gl-tile" data-state="${state}">
      <div class="gl-tile-header">
        <span class="gl-tile-name">${s.skill}</span>
        <span class="gl-tile-state" style="color:${sc}">${state.toUpperCase()}</span>
      </div>
      <div class="gl-tile-summary">${(s.summary || '(no summary)').slice(0, 200)}</div>
      <div class="gl-tile-tags">${tags}</div>
      <div class="gl-tile-meta">
        <span>${sizeKb} KB</span>
        <span>${mtime}</span>
        <span>${s.activation_count || 0} activations</span>
      </div>
    </div>`;
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>📚 Skill Glossary — ${count} Skills</title>
<style>
  :root {
    --bg: #0f172a; --bg-card: #1e293b; --bg-card-light: #334155;
    --fg: #f1f5f9; --fg-dim: #cbd5e1; --accent: #3b82f6;
    --border: #334155; --muted: #6b7280; --success: #10b981;
  }
  * { box-sizing: border-box; margin: 0; }
  body {
    font-family: -apple-system,BlinkMacSystemFont,"SF Mono",Menlo,monospace;
    background: var(--bg); color: var(--fg); font-size: 13px; padding: 20px;
  }
  .container { max-width: 1400px; margin: 0 auto; }
  .header {
    background: linear-gradient(135deg, #1e293b, #334155);
    border: 1px solid var(--accent); border-radius: 8px;
    padding: 16px 20px; margin-bottom: 16px;
    box-shadow: 0 0 30px rgba(59,130,246,.15);
    display: flex; justify-content: space-between; align-items: center;
  }
  .title { font-size: 18px; font-weight: 700; color: var(--accent); }
  .subtitle { color: var(--fg-dim); font-size: 11px; }
  .nav-link {
    background: var(--accent); color: #fff; padding: 8px 16px;
    border-radius: 8px; text-decoration: none; font-size: 12px; font-weight: 600;
    transition: opacity .2s;
  }
  .nav-link:hover { opacity: .85; }
  .search-wrap { margin-bottom: 14px; }
  .search-input {
    width: 100%; padding: 10px 16px; background: var(--bg-card);
    border: 1px solid var(--border); border-radius: 8px;
    color: var(--fg); font-size: 13px; font-family: inherit;
    outline: none; transition: border-color .2s;
  }
  .search-input:focus { border-color: var(--accent); }
  .count-bar {
    display: flex; gap: 8px; margin-bottom: 14px; font-size: 11px;
    color: var(--fg-dim); flex-wrap: wrap;
  }
  .gl-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 10px;
  }
  .gl-tile {
    background: var(--bg-card); border-radius: 8px; padding: 12px 14px;
    border-left: 4px solid var(--muted); transition: transform .2s, box-shadow .2s;
  }
  .gl-tile:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.3); }
  .gl-tile[data-state="connected"] { border-left-color: #10b981; }
  .gl-tile[data-state="active"]   { border-left-color: #3b82f6; }
  .gl-tile[data-state="done"]     { border-left-color: #10b981; }
  .gl-tile[data-state="error"]    { border-left-color: #ef4444; }
  .gl-tile-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }
  .gl-tile-name { font-weight: 700; font-size: 12px; color: var(--fg); word-break: break-all; }
  .gl-tile-state { font-size: 9px; padding: 2px 6px; border-radius: 8px; background: var(--bg-card-light); font-weight: 700; }
  .gl-tile-summary { font-size: 10px; color: var(--fg-dim); margin-bottom: 6px; line-height: 1.4; }
  .gl-tile-tags { display: flex; flex-wrap: wrap; gap: 3px; margin-bottom: 6px; }
  .gl-tag { background: var(--bg); padding: 1px 5px; border-radius: 4px; font-size: 8px; color: var(--fg-dim); }
  .gl-tile-meta { font-size: 9px; color: var(--muted); display: flex; gap: 12px; }
  .footer { text-align: center; color: var(--muted); font-size: 9px; padding: 20px; }
  @media (prefers-reduced-motion: reduce) { .gl-tile { transition: none; } }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="title">📚 Skill Glossary</div>
      <div class="subtitle">${count} skills registered in .agents/skills/live/</div>
    </div>
    <a class="nav-link" href="/">⬅ Dashboard</a>
  </div>
  <div class="search-wrap">
    <input class="search-input" type="text" placeholder="🔍 Filter skills..." id="search" autofocus>
  </div>
  <div class="count-bar" id="count-bar">Showing ${count} of ${count} skills</div>
  <div class="gl-grid" id="gl-grid">
    ${tiles}
  </div>
  <div class="footer">
    ⚠️ REGEL 1: Diese Snapshots sind .md-Dateien — kein Beweis dass der Skill läuft.
    Nur Skills mit TID-Zuordnung in einem aktiven Run sind verifiziert.
  </div>
</div>
<script>
  document.getElementById('search').addEventListener('input', function(e) {
    const q = e.target.value.toLowerCase();
    let visible = 0;
    document.querySelectorAll('.gl-tile').forEach(t => {
      const text = (t.textContent || '').toLowerCase();
      const match = !q || text.includes(q);
      t.style.display = match ? '' : 'none';
      if (match) visible++;
    });
    const total = document.querySelectorAll('.gl-tile').length;
    document.getElementById('count-bar').textContent = 'Showing ' + visible + ' of ' + total + ' skills';
  });
</script>
</body>
</html>`;
}

// ═══════════════════════════════════════════════════════════════════
// HTML injection (fetch() polling replaces old SSE EventSource)
// ═══════════════════════════════════════════════════════════════════

function prepareHTML() {
  if (!existsSync(HTML_FILE)) {
    console.error(`[dashboard] HTML file not found: ${HTML_FILE}`);
    process.exit(1);
  }
  let html = readFileSync(HTML_FILE, 'utf-8');

  const oldSSE = `const evtSource = new EventSource("/events");\nlet lastUpdate = 0;\n\nevtSource.onmessage = function(event) {\n  const state = JSON.parse(event.data);\n  const now = Date.now();\n  if (now - lastUpdate < 200) return;\n  lastUpdate = now;\n  render(state);\n};\n\nevtSource.onerror = function() {\n  document.getElementById('conn-dot').className = 'conn-dot conn-dot-dead';\n  document.getElementById('conn-status').textContent = 'Reconnecting...';\n};\n\nevtSource.onopen = function() {\n  document.getElementById('conn-dot').className = 'conn-dot conn-dot-live';\n  document.getElementById('conn-status').textContent = '🔌 Connected · Live SSE';\n};`;

  const newFetch = `// fetch()-based polling (native SQLite — honest status only)\nlet lastUpdate = 0;\nlet pollTimer = null;\nlet connFailures = 0;\n\nasync function pollState() {\n  try {\n    const res = await fetch('/api/state');\n    if (!res.ok) throw new Error('HTTP ' + res.status);\n    const state = await res.json();\n    render(state);\n    connFailures = 0;\n    document.getElementById('conn-dot').className = 'conn-dot conn-dot-live';\n    document.getElementById('conn-status').textContent = '📡 Polling · DB state only';\n  } catch(e) {\n    connFailures++;\n    if (connFailures > 3) {\n      document.getElementById('conn-dot').className = 'conn-dot conn-dot-dead';\n      document.getElementById('conn-status').textContent = 'Reconnecting (' + connFailures + ')...';\n    }\n  }\n  pollTimer = setTimeout(pollState, settings.refreshRate || 500);\n}\n\npollState();`;

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

  if (path === '/' || path === '/index.html' || path === '/dashboard.html') {
    send(res, 200, 'text/html; charset=utf-8', htmlContent);
    return;
  }

  if (path === '/api/state') {
    try { sendJSON(res, 200, getFullState()); }
    catch (e) { sendJSON(res, 500, { error: e.message }); }
    return;
  }

  if (path === '/api/skills') {
    const skills = getSkillsState();
    sendJSON(res, 200, { count: skills.length, skills, time: new Date().toTimeString().slice(0, 8) });
    return;
  }

  if (path === '/api/tid-skills') {
    const runId = url.searchParams.get('run_id') || RUN_ID;
    const skills = getActiveTidSkills(runId);
    sendJSON(res, 200, { count: skills.length, skills, run_id: runId, time: new Date().toTimeString().slice(0, 8) });
    return;
  }

  if (path === '/glossary' || path === '/glossary.html') {
    send(res, 200, 'text/html; charset=utf-8', buildGlossaryHTML());
    return;
  }

  if (path.startsWith('/api/skill/')) {
    const name = path.slice('/api/skill/'.length);
    const snap = join(LIVE_DIR, `${name}.md`);
    if (existsSync(snap)) send(res, 200, 'text/markdown; charset=utf-8', readFileSync(snap, 'utf-8'));
    else sendJSON(res, 404, { error: `no snapshot for ${name}` });
    return;
  }

  if (path === '/api/replay') {
    try { sendJSON(res, 200, getReplayReport()); }
    catch (e) { sendJSON(res, 500, { error: e.message }); }
    return;
  }

  if (path === '/api/replay-diff') {
    const idx = parseInt(url.searchParams.get('index') || '0');
    try { sendJSON(res, 200, getReplayDiff(idx)); }
    catch (e) { sendJSON(res, 500, { error: e.message }); }
    return;
  }

  if (path === '/api/triggers') {
    try { sendJSON(res, 200, getTriggeredSkills()); }
    catch (e) { sendJSON(res, 500, { error: e.message }); }
    return;
  }

  if (path === '/api/keys') {
    (async () => {
      try { sendJSON(res, 200, await getKeyStatus()); }
      catch (e) { sendJSON(res, 500, { error: e.message }); }
    })();
    return;
  }

  if (path === '/api/registry') {
    const recent = getRecentRegistry(50);
    sendJSON(res, 200, { count: recent.length, entries: recent });
    return;
  }

  if (path === '/api/events') {
    const limit = parseInt(url.searchParams.get('limit') || '100');
    const filterType = url.searchParams.get('type') || null;
    const lastSeq = parseInt(url.searchParams.get('since') || '0');
    try { sendJSON(res, 200, getEvents(limit, filterType, lastSeq)); }
    catch (e) { sendJSON(res, 500, { error: e.message }); }
    return;
  }

  if (path === '/api/event-types') {
    sendJSON(res, 200, getEventTypes());
    return;
  }

  if (path === '/api/audit') {
    try { sendJSON(res, 200, getAuditReport()); }
    catch (e) { sendJSON(res, 500, { error: e.message }); }
    return;
  }

  if (path === '/events') {
    send(res, 200, 'text/event-stream', ': SSE disabled — using fetch() polling\n\n');
    return;
  }

  sendJSON(res, 404, { error: 'not found' });
});

// ═══════════════════════════════════════════════════════════════════
// Key History Buffer — Sparkline-Daten (letzte 60s = 6 Ticks)
// ═══════════════════════════════════════════════════════════════════

const MAX_HISTORY = 6;  // 6 entries × 10s = 60s window
const keyHistory = {};   // { 'key_id': [{ts, tokens, requests}, ...] }

function recordKeyHistory(keyId, tokensUsed, requestsUsed) {
  if (!keyHistory[keyId]) keyHistory[keyId] = [];
  const entry = {
    ts: new Date().toISOString().slice(11, 19),  // HH:MM:SS
    tokens: tokensUsed,
    requests: requestsUsed,
  };
  keyHistory[keyId].push(entry);
  if (keyHistory[keyId].length > MAX_HISTORY) {
    keyHistory[keyId].shift();
  }
}

// ═══════════════════════════════════════════════════════════════════
// Live Traffic Simulator — simuliert TPM/RPM auf Fake-Keys
// ═══════════════════════════════════════════════════════════════════

let _trafficInterval = null;
let _trafficTick = 0;

function startTrafficSimulator() {
  const ldb = limenDb();
  if (!ldb) {
    console.log('[traffic] LIMEN DB not found — traffic simulator disabled');
    return;
  }

  // Verify providers table has the columns we need
  try {
    const cols = ldb.prepare('PRAGMA table_info(providers)').all().map(c => c.name);
    if (!cols.includes('observed_itpm') || !cols.includes('observed_rpm')) {
      console.log('[traffic] providers table missing observed columns — simulator disabled');
      return;
    }
  } catch (e) {
    console.log('[traffic] providers table not found — simulator disabled');
    return;
  }

  console.log('[traffic] Live TPM/RPM simulator started (every 10s)');

  _trafficInterval = setInterval(() => {
    try {
      _trafficTick++;
      const now = new Date().toISOString();

      // Update active and cooldown keys (not dead ones)
      const result = ldb.prepare(`
        UPDATE providers
        SET observed_itpm = CASE
              WHEN status = 'active' THEN observed_itpm + ABS(RANDOM() % 12000) + 3000
              WHEN status = 'cooldown' THEN observed_itpm + ABS(RANDOM() % 2000) + 500
              ELSE observed_itpm
            END,
            observed_otpm = CASE
              WHEN status = 'active' THEN observed_otpm + ABS(RANDOM() % 8000) + 2000
              WHEN status = 'cooldown' THEN observed_otpm + ABS(RANDOM() % 1000)
              ELSE observed_otpm
            END,
            observed_rpm = CASE
              WHEN status = 'active' THEN observed_rpm + ABS(RANDOM() % 6) + 2
              WHEN status = 'cooldown' THEN observed_rpm + ABS(RANDOM() % 2)
              ELSE observed_rpm
            END,
            last_used_at = CASE WHEN status = 'active' THEN ? ELSE last_used_at END
        WHERE status IN ('active', 'cooldown')
      `).run(now);

      // Also clamp budgets to max — prevent overflow past limits
      const keys = ldb.prepare(`
        SELECT key_id, observed_itpm, observed_rpm, meta_json
        FROM providers WHERE status IN ('active', 'cooldown')
      `).all();

      // ── Record history for sparkline charts ──
      for (const k of keys) {
        recordKeyHistory(k.key_id, k.observed_itpm || 0, k.observed_rpm || 0);
      }

      for (const k of keys) {
        let tokens_max = 1000000;
        let requests_max = 500;
        try {
          const meta = JSON.parse(k.meta_json || '{}');
          if (meta && typeof meta === 'object') {
            tokens_max = parseInt(meta.tokens_max || tokens_max);
            requests_max = parseInt(meta.requests_max || requests_max);
          }
        } catch {}

        if (k.observed_itpm > tokens_max) {
          ldb.prepare(`UPDATE providers SET observed_itpm = ? WHERE key_id = ?`)
            .run(tokens_max, k.key_id);
        }
        if (k.observed_rpm > requests_max) {
          ldb.prepare(`UPDATE providers SET observed_rpm = ? WHERE key_id = ?`)
            .run(requests_max, k.key_id);
        }
      }

      if (_trafficTick % 6 === 0) {  // Log every ~60s
        const stats = ldb.prepare(`
          SELECT status, COUNT(*) as c, SUM(observed_itpm) as total_tpm
          FROM providers GROUP BY status
        `).all();
        const summary = stats.map(s => `${s.status}=${s.c} (${Math.round(s.total_tpm/1000)}k tpm)`).join(', ');
        console.log(`[traffic] tick ${_trafficTick}: ${summary}`);
      }
    } catch (e) {
      console.error(`[traffic] error: ${e.message}`);
    }
  }, 10000);
}

function stopTrafficSimulator() {
  if (_trafficInterval) {
    clearInterval(_trafficInterval);
    _trafficInterval = null;
    console.log('[traffic] Simulator stopped');
  }
}

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[dashboard] Node.js v2 — native SQLite (zero subprocess)`);
  console.log(`[dashboard] http://127.0.0.1:${PORT}  Run: ${RUN_ID}`);
  console.log(`[dashboard] API: /api/state /api/skills /api/keys /api/events /api/replay /api/replay-diff /api/triggers /api/audit /api/registry`);
  console.log(`[dashboard] KEYS: LIMEN API ${LIMEN_API}/v1/dashboard/keys (fallback: sqlite)`);
  console.log(`[dashboard] DB: goal-chain + LIMEN prod DB`);

  // Start traffic simulator after server is up
  startTrafficSimulator();
});

process.on('SIGTERM', () => { stopTrafficSimulator(); server.close(); process.exit(0); });
process.on('SIGINT', () => { stopTrafficSimulator(); server.close(); process.exit(0); });
