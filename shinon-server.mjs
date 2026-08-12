#!/usr/bin/env node
// ═══════════════════════════════════════════════════════════════════════
// shinon-server.mjs — Unified Frontend Server
//
// Dient 2 Seiten + Slide-out Settings:
//   GET  /              → Shinon Chat (Seite 1)
//   GET  /stats         → Statistiken & Tracking (Seite 2)  
//   GET  /api/state     → Proxy zum Dashboard
//   POST /api/chat      → Chat-Nachricht an LIMEN → LLM-Antwort
//   GET  /api/keys      → Key-Status aus LIMEN-DB
//   POST /api/keys      → Key speichern
//   GET  /api/personality → Persönlichkeits-Werte
//   POST /api/personality → Persönlichkeit speichern
//   GET  /api/config    → Config lesen/schreiben
//   POST /api/prosa     → NarrativeSpec → Prosa (render(), model vs. fallback)
//
// Usage:
//   node shinon-server.mjs [PORT]
// ═══════════════════════════════════════════════════════════════════════

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';
import { spawn } from 'node:child_process';
import { DatabaseSync } from 'node:sqlite';
import { HTML } from './shinon-ui.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.argv[2] || '4300', 10);

const PROJECT_ROOT = __dirname;
// ─── DB Paths — respects paths.py SSOT via env vars injected by ctl.py
const SHINON_HOME = process.env.SHINON_HOME
  || path.join(process.env.HOME || process.env.USERPROFILE || PROJECT_ROOT, '.shinon');
const LIMEN_DB = process.env.LIMEN_DB
  || path.join(SHINON_HOME, 'data', 'limen', 'limen.db');
const TID_DB = process.env.GOALCHAIN_DB
  || path.join(SHINON_HOME, 'data', 'goal-chain', 'tid-state.db');
// ─── SHINON memory (env-first, then SHINON_HOME)
const SHINON_DATA_DIR = process.env.SHINON_DATA_DIR
  || path.join(SHINON_HOME, 'data', 'shinon');
try { fs.mkdirSync(SHINON_DATA_DIR, { recursive: true }); } catch (_) {}
const SHINON_MEM = path.join(SHINON_DATA_DIR, 'memory.db');
// ─── BUG-P0-1 FIX: LIMEN runs on 8001 (confirmed by limen-main/start_limen.py)
const LIMEN_URL = 'http://127.0.0.1:8001';

// ═══ SERVER ════════════════════════════════════════════════════════════
function sendJSON(res, code, data) {
  res.writeHead(code, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
  res.end(JSON.stringify(data));
}

function readJSON(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', c => { body += c; if (body.length > 1_000_000) reject('too large'); });
    req.on('end', () => { try { resolve(JSON.parse(body)); } catch (e) { resolve({}); } });
  });
}

// ═══ Native SQLite (node:sqlite) — kein Python-Subprocess ═══════════════
// Ersetzt das alte execSync(python3 -c "sqlite3 ...") Muster:
//   * kein Shell-String-Escaping / keine SQL-Injection über die Shell
//   * keine 50–100ms Python-Spawn pro Query — Mikrosekunden, in-process
//   * parameterisiert via Prepared Statements (?,?,...) statt Interpolation
// Gleiches Muster wie live-dashboard-server.mjs (DatabaseSync).

const _dbCache = new Map();

function getDB(dbPath) {
  if (!fs.existsSync(dbPath)) return null;
  if (_dbCache.has(dbPath)) return _dbCache.get(dbPath);
  let db;
  try {
    db = new DatabaseSync(dbPath);
    db.exec('PRAGMA busy_timeout=5000');
    try { db.exec('PRAGMA journal_mode=WAL'); } catch (_) { /* schon gesetzt / gelockt */ }
  } catch (e) {
    console.error(`[db] open failed (${dbPath}):`, e.message);
    return null;
  }
  _dbCache.set(dbPath, db);
  return db;
}

function queryDB(dbPath, sql, ...params) {
  const db = getDB(dbPath);
  if (!db) return null;
  try {
    return db.prepare(sql).all(...params);
  } catch (e) {
    console.error(`[db] query failed (${dbPath}):`, e.message);
    return [];
  }
}

function execDB(dbPath, sql, ...params) {
  const db = getDB(dbPath);
  if (!db) return false;
  try {
    db.prepare(sql).run(...params);
    return true;
  } catch (e) {
    console.error(`[db] exec failed (${dbPath}):`, e.message);
    return false;
  }
}

// ═══ Prosa-Renderer (NarrativeSpec → Text, rein, model vs. fallback) ═══
function renderProsa(spec) {
  const script = path.join(PROJECT_ROOT, 'render_prosa.py');
  try {
    const out = execSync(`python3 "${script}"`, {
      input: JSON.stringify(spec || {}),
      cwd: PROJECT_ROOT,
      timeout: 60000,
      encoding: 'utf-8',
      maxBuffer: 2 * 1024 * 1024,
    });
    return JSON.parse(out.trim() || '{}');
  } catch (e) {
    // render_prosa.py gibt bei ungültiger Spec {"error": ...} mit exit 1 aus.
    const out = (e.stdout || Buffer.from('')).toString().trim();
    if (out) { try { return JSON.parse(out); } catch (_) { /* fallthrough */ } }
    return { error: 'prosa render failed', detail: String(e.message || e) };
  }
}

// ═══ Chat Config (opt-in: Chat nutzt User-API / LIMEN) ════════════════════
// [chat] use_api in shinon.toml. Der Bridge (Python) liest dieselbe Quelle.
// Hier nur read/toggle für die UI. Env-Override SHINON_CHAT_USE_API gewinnt.

function chatConfigPath() {
  return process.env.SHINON_CONFIG || path.join(SHINON_HOME, 'config', 'shinon.toml');
}

function readChatConfig() {
  const env = process.env.SHINON_CHAT_USE_API;
  if (env !== undefined && env !== '') {
    return { use_api: ['1', 'true', 'yes', 'on'].includes(env.toLowerCase()), default_intent: 'chat' };
  }
  const cfgPath = chatConfigPath();
  try {
    if (!fs.existsSync(cfgPath)) return { use_api: false, default_intent: 'chat' };
    // Reiner JS-Parse der [chat]-Sektion (kein Python-Subprocess).
    const lines = fs.readFileSync(cfgPath, 'utf-8').split('\n');
    let inChat = false;
    let useApi = false;
    let defaultIntent = 'chat';
    for (const line of lines) {
      const l = line.trim();
      if (/^\[chat\]\s*$/.test(l)) { inChat = true; continue; }
      if (inChat && l.startsWith('[')) break;
      if (inChat && /^use_api\s*=/.test(l)) useApi = /=\s*(true|1|yes|on)/i.test(l);
      if (inChat && /^default_intent\s*=/.test(l)) {
        const m = l.match(/=\s*"([^"]+)"/);
        if (m && ['chat', 'task', 'ambiguous'].includes(m[1])) defaultIntent = m[1];
      }
    }
    return { use_api: useApi, default_intent: defaultIntent };
  } catch (e) {
    return { use_api: false, default_intent: 'chat' };
  }
}

function writeChatConfig(useApi) {
  const cfgPath = chatConfigPath();
  try {
    if (!fs.existsSync(cfgPath)) return false;
    const lines = fs.readFileSync(cfgPath, 'utf-8').split('\n');
    let chatIdx = -1;
    let useApiIdx = -1;
    for (let i = 0; i < lines.length; i++) {
      const l = lines[i].trim();
      if (/^\[chat\]\s*$/.test(l)) { chatIdx = i; continue; }
      if (chatIdx !== -1 && l.startsWith('[')) break;
      if (chatIdx !== -1 && /^use_api\s*=/.test(l)) useApiIdx = i;
    }
    const newLine = `use_api = ${useApi ? 'true' : 'false'}`;
    if (useApiIdx !== -1) {
      lines[useApiIdx] = newLine;                       // ersetzen
    } else if (chatIdx !== -1) {
      lines.splice(chatIdx + 1, 0, newLine);            // direkt unter [chat]
    } else {
      lines.push('', '[chat]', newLine, 'default_intent = "chat"');  // Sektion anlegen
    }
    fs.writeFileSync(cfgPath, lines.join('\n'), 'utf-8');
    return true;
  } catch (e) { return false; }
}

// ═══ FUSION BRIDGE ═══════════════════════════════════════════════════════
// Calls fusion-main/fusion/event_runtime.py via shinon_fusion_bridge.py.
// Returns { reply, model, source, character_context, claims_count } or null.
// Exit 0 → full reply from ShinonEngine via LIMEN
// Exit 2 → no LLM reply but character_context available → enrich LIMEN prompt
// Exit 1 / timeout → null → fall through to direct LIMEN call

const FUSION_BRIDGE = path.join(PROJECT_ROOT, 'shinon_fusion_bridge.py');
const FUSION_TIMEOUT_MS = 12000;

function callFusionBridge(payload) {
  return new Promise((resolve) => {
    let stdout = '';
    let done = false;

    const venv = path.join(PROJECT_ROOT, '.venv', 'bin', 'python3');
    const py3  = fs.existsSync(venv) ? venv : 'python3';

    const proc = spawn(py3, [FUSION_BRIDGE], {
      cwd: PROJECT_ROOT,
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' },
    });

    proc.stdout.on('data', chunk => { stdout += chunk.toString(); });
    // stderr is ignored (fusion logs there)

    const timer = setTimeout(() => {
      if (!done) { done = true; proc.kill('SIGTERM'); resolve(null); }
    }, FUSION_TIMEOUT_MS);

    proc.on('close', (code) => {
      clearTimeout(timer);
      if (done) return;
      done = true;

      if (!stdout.trim()) { resolve(null); return; }
      try {
        const result = JSON.parse(stdout.trim());
        // code 0 → real reply; code 2 → no reply but character_context
        result._exit = code;
        resolve(result);
      } catch { resolve(null); }
    });

    proc.on('error', () => { clearTimeout(timer); if (!done) { done = true; resolve(null); } });

    proc.stdin.write(JSON.stringify(payload));
    proc.stdin.end();
  });
}

// ═══ SYSTEM PROMPT BUILDER ═══════════════════════════════════════════════
// Builds the LIMEN system prompt, optionally enriched by fusion character context.

function buildSystemPrompt(personality, characterContext) {
  const skepticism = (personality && personality.skepticism != null) ? personality.skepticism : 8;
  const directness  = (personality && personality.directness  != null) ? personality.directness  : 7;

  const lines = [
    'Du bist Shinon — eine kritische, skeptische KI-Persönlichkeit.',
    'Deine Kern-Haltung: Hinterfragen, prüfen, validieren. Glaube nichts ungeprüft.',
    `Skepsis-Level: ${skepticism}/10. Direktheit: ${directness}/10.`,
    'Antworte auf Deutsch. Sei präzise, direkt und ehrlich. Kein Geschwafel. Kein Yes-Man-Verhalten.',
    'Wenn du etwas nicht weißt, sag es klar. Wenn der User Unsinn redet, sag es ihm.',
  ];

  if (characterContext && typeof characterContext === 'object') {
    // Tone directive from ShinonEngine attitude evaluation
    if (characterContext.tone_directive) {
      lines.push(`\nTON-DIREKTIVE (aus Shinon Character Layer): ${characterContext.tone_directive}`);
    }
    // Emotional state
    if (characterContext.emotional_state && characterContext.emotional_state !== 'neutral') {
      lines.push(`AKTUELLER EMOTIONALER ZUSTAND: ${characterContext.emotional_state}`);
    }
    // Confrontation mode
    if (characterContext.should_confront) {
      lines.push('KONFRONTATIONS-MODUS: Der User zeigt Inkonsistenzen — weise klar darauf hin.');
    }
    // Attitude dimensions from SQLite memory
    const att = characterContext.attitudes;
    if (att && typeof att === 'object' && Object.keys(att).length > 0) {
      const attStr = Object.entries(att)
        .map(([k, v]) => `${k}=${v}`)
        .join(', ');
      lines.push(`ATTITUDE-DIMENSIONEN (-10..+10): ${attStr}`);
    }
    // Detected patterns from input
    if (Array.isArray(characterContext.patterns) && characterContext.patterns.length > 0) {
      lines.push(`ERKANNTE MUSTER: ${characterContext.patterns.join(', ')}`);
    }
  }

  return lines.join('\n');
}

// ═══ LIMEN CHAT CALL ════════════════════════════════════════════════════
// Promisified LIMEN call used by the fusion-enriched chat handler.

function limenChat(systemPrompt, userMessage, history) {
  return new Promise((resolve) => {
    const messages = [
      { role: 'system', content: systemPrompt },
      ...(Array.isArray(history) ? history.filter(m => m.role && m.content) : []),
      { role: 'user', content: userMessage },
    ];

    const limenReq = http.request({
      hostname: '127.0.0.1', port: 8001, path: '/v1/chat/completions',
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000,
    }, (limenRes) => {
      let data = '';
      limenRes.on('data', c => data += c);
      limenRes.on('end', () => {
        try {
          const json = JSON.parse(data);
          const reply = json.choices?.[0]?.message?.content || '';
          resolve({ reply, model: json.model || 'limen' });
        } catch { resolve(null); }
      });
    });
    limenReq.on('error', () => resolve(null));
    limenReq.on('timeout', () => { limenReq.destroy(); resolve(null); });
    limenReq.write(JSON.stringify({ model: 'auto', messages, max_tokens: 600 }));
    limenReq.end();
  });
}

// ═══ ROUTES ═══════════════════════════════════════════════════════════
const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  const pathname = url.pathname;

  // CORS
  if (req.method === 'OPTIONS') {
    res.writeHead(204, { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' });
    return res.end();
  }

  // HTML Pages
  if (req.method === 'GET' && (pathname === '/' || pathname === '/chat')) {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(HTML);
  }
  // Static Assets
  if (req.method === 'GET' && pathname.startsWith('/assets/')) {
    const assetPath = path.join(PROJECT_ROOT, pathname);
    if (fs.existsSync(assetPath)) {
      const ext = path.extname(assetPath).toLowerCase();
      const contentType = (ext === '.jpg' || ext === '.jpeg') ? 'image/jpeg' : (ext === '.svg' ? 'image/svg+xml' : 'application/octet-stream');
      res.writeHead(200, { 'Content-Type': contentType, 'Cache-Control': 'public, max-age=86400' });
      return fs.createReadStream(assetPath).pipe(res);
    }
  }

  // API: Ping
  if (pathname === '/api/ping') return sendJSON(res, 200, { ok: true, time: new Date().toISOString() });

  // API: Chat config — Opt-in ob Chat die User-API (LIMEN) nutzt
  if (req.method === 'GET' && pathname === '/api/chat/config') {
    return sendJSON(res, 200, readChatConfig());
  }
  if (req.method === 'POST' && pathname === '/api/chat/config') {
    const body = await readJSON(req);
    const useApi = !!body.use_api;
    const ok = writeChatConfig(useApi);
    return sendJSON(res, ok ? 200 : 500, ok ? readChatConfig() : { error: 'could not write chat config' });
  }

  // API: Chat — Fusion-first orchestration
  // Flow:
  //   1. Call fusion bridge (ShinonEngine character layer + Promtguard + KARMA)
  //      a. exit 0  → fusion produced a full reply (ShinonEngine called LIMEN) → use it
  //      b. exit 2  → fusion ran but no LLM reply → use character_context to enrich LIMEN prompt
  //      c. null    → fusion timed out / crashed → bare LIMEN call with basic prompt
  //   2. All paths fall back to generateFallbackReply() if LIMEN is also unreachable.
  if (req.method === 'POST' && pathname === '/api/chat') {
    const body = await readJSON(req);
    const message     = body.message     || '';
    const personality = body.personality  || {};
    const history     = body.history      || [];
    const sessionId   = body.session_id
                     || body.sessionId
                     || `sess-${Date.now()}`;

    // ── Step 1: Try fusion pipeline ──────────────────────────────────
    let fusionResult = null;
    try {
      fusionResult = await callFusionBridge({
        message, session_id: sessionId, history, personality,
      });
    } catch (e) {
      // unexpected — treated as null (fallback)
    }

    // ── Step 2a: Fusion produced a full reply (task OR local chat) ───
    if (fusionResult && fusionResult._exit === 0 && fusionResult.reply) {
      return sendJSON(res, 200, {
        reply:  fusionResult.reply,
        model:  fusionResult.model  || 'fusion',
        source: fusionResult.source || 'fusion',
        intent: fusionResult.intent  || '',
        claims: fusionResult.claims_count || 0,
        cid:    fusionResult.correlation_id || '',
      });
    }

    // ── Step 2b/c: Build system prompt (with or without character context) ─
    const characterContext = (fusionResult && fusionResult.character_context)
      ? fusionResult.character_context
      : null;
    const systemPrompt = buildSystemPrompt(personality, characterContext);

    // ── Step 3: Call LIMEN with enriched prompt ───────────────────────
    const limenResult = await limenChat(systemPrompt, message, history);

    if (limenResult && limenResult.reply) {
      return sendJSON(res, 200, {
        reply:  limenResult.reply,
        model:  limenResult.model || 'limen',
        source: characterContext ? 'fusion+limen' : 'limen',
        claims: fusionResult?.claims_count || 0,
        cid:    fusionResult?.correlation_id || '',
      });
    }

    // ── Step 4: Full offline fallback ────────────────────────────────
    return sendJSON(res, 200, {
      reply:  generateFallbackReply(message),
      model:  'shinon-offline',
      source: 'fallback',
    });
  }

  // API: Keys — proxy to LIMEN internal API (BUG-P0-3 FIX: avoid wrong DB path + SQL-injection)
  if (req.method === 'GET' && pathname === '/api/keys') {
    // Try LIMEN API first, fall back to direct SQLite read
    try {
      const limenKeys = await new Promise((resolve, reject) => {
        const r = http.get('http://127.0.0.1:8001/v1/dashboard/keys', res2 => {
          let d = ''; res2.on('data', c => d += c);
          res2.on('end', () => { try { resolve(JSON.parse(d)); } catch { reject(new Error('parse')); } });
        });
        r.on('error', reject); r.setTimeout(2000, () => { r.destroy(); reject(new Error('timeout')); });
      });
      // Normalize LIMEN dashboard/keys format to UI format
      const keys = (limenKeys.providers || limenKeys.keys || []).map(p => ({
        id: p.key_id || p.id || p.provider, provider: p.provider,
        deployment: p.deployment || 'default',
        status: p.status || 'active',
        health_pct: Math.round(p.health_score ?? p.health_pct ?? 100),
        rpm: Math.round(p.observed_rpm ?? p.rpm ?? 0),
        errors: p.error_count ?? p.errors ?? 0,
        success: p.success_count ?? p.success ?? 0,
      }));
      return sendJSON(res, 200, { keys, total: keys.length, active: keys.filter(k => k.status === 'active').length });
    } catch (_) {
      // Fallback: direct SQLite (works in standalone mode without LIMEN running)
      const rows = queryDB(LIMEN_DB, "SELECT key_id, provider, deployment, status, health_score, observed_rpm, error_count, success_count FROM providers WHERE value != ''");
      const keys = (rows || []).map(r => ({
        id: r.key_id, provider: r.provider, deployment: r.deployment,
        status: r.status, health_pct: Math.round(r.health_score || 100),
        rpm: Math.round(r.observed_rpm || 0), errors: r.error_count || 0, success: r.success_count || 0,
      }));
      return sendJSON(res, 200, { keys, total: keys.length, active: keys.filter(k => k.status === 'active').length });
    }
  }

  if (req.method === 'POST' && pathname === '/api/keys') {
    const body = await readJSON(req);
    const provider = String(body.provider || '').replace(/[^a-zA-Z0-9_\-]/g, '');
    const value = body.value;
    if (!provider || !value) return sendJSON(res, 400, { error: 'provider and value required' });
    // BUG-P1-5 FIX: Use LIMEN API instead of raw SQL to avoid injection
    try {
      const limenOk = await new Promise((resolve, reject) => {
        const payload = JSON.stringify({ value: String(value) });
        const r = http.request({
          hostname: '127.0.0.1', port: 8001, path: `/v1/_internal/keys/${encodeURIComponent(provider)}`,
          method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) },
        }, res2 => { resolve(res2.statusCode < 400); });
        r.on('error', reject); r.write(payload); r.end();
      });
      return sendJSON(res, limenOk ? 200 : 500, { ok: limenOk });
    } catch (_) {
      // Fallback: direkter nativer SQLite-Write (Prepared Statement, keine Shell)
      const keyId = provider + '-shinon-ui';
      const meta = JSON.stringify({ api_key: value, source: 'shinon-ui' });
      const ok = execDB(LIMEN_DB,
        'INSERT OR REPLACE INTO providers (key_id, provider, deployment, value, status, priority, meta_json) VALUES (?,?,?,?,?,?,?)',
        keyId, provider, 'default', String(value), 'active', 1, meta);
      return sendJSON(res, ok ? 200 : 500, ok ? { ok: true } : { ok: false, error: 'db write failed' });
    }
  }

  // API: Personality
  if (req.method === 'GET' && pathname === '/api/personality') {
    const rows = queryDB(SHINON_MEM, "SELECT dimension, value FROM attitudes");
    const personality = {};
    if (rows) rows.forEach(r => { personality[r.dimension] = r.value; });
    return sendJSON(res, 200, personality);
  }

  if (req.method === 'POST' && pathname === '/api/personality') {
    const body = await readJSON(req);
    // Prepared Statements (native sqlite) — keine Shell, keine Interpolation.
    const updates = Object.entries(body)
      .filter(([k]) => /^[a-zA-Z0-9_]+$/.test(k))  // whitelist dimension names
      .map(([k, v]) => ({ dim: k, val: Math.max(-10, Math.min(10, Number(v))) }));
    for (const { dim, val } of updates) {
      execDB(SHINON_MEM, "UPDATE attitudes SET value=?,updated_at=datetime('now') WHERE dimension=?", val, dim);
    }
    return sendJSON(res, 200, { ok: true });
  }

  // API: State (proxied from dashboard DB)
  // BUG-P2-4 FIX: Method check added
  if (req.method === 'GET' && pathname === '/api/state') {
    try {
      const rows = queryDB(TID_DB, "SELECT status, COUNT(*) as c FROM tasks GROUP BY status");
      const state = { total: 0, done: 0, failed: 0, pending: 0, in_progress: 0 };
      if (rows) rows.forEach(r => {
        state.total += r.c;
        if (r.status === 'DONE') state.done = r.c;
        if (r.status === 'FAILED') state.failed = r.c;
        if (r.status === 'PENDING') state.pending = r.c;
        if (r.status === 'IN_PROGRESS') state.in_progress = r.c;
      });
      return sendJSON(res, 200, state);
    } catch (e) { return sendJSON(res, 200, { total: 0 }); }
  }

  // API: Triggers
  // BUG-P2-4 FIX: Method check added
  if (req.method === 'GET' && pathname === '/api/triggers') {
    const rows = queryDB(TID_DB, "SELECT decision_type as skill, COUNT(*) as trigger_count FROM dispatcher_decisions WHERE decision_type LIKE '%TRIGGER%' OR decision_type = 'CHAIN_SCRIPT_FAILED' GROUP BY decision_type ORDER BY trigger_count DESC LIMIT 10");
    return sendJSON(res, 200, { triggers: rows || [] });
  }

  // API: Prosa-Status — Modell + llama-cli vorhanden? (Qualitätslayer-Badge)
  if (req.method === 'GET' && pathname === '/api/prosa/status') {
    const statusScript = path.join(PROJECT_ROOT, 'model_bootstrap.py');
    try {
      const out = execSync(`python3 "${statusScript}" --status --json`, {
        cwd: PROJECT_ROOT,
        timeout: 5000,
        encoding: 'utf-8',
        maxBuffer: 1024 * 1024,
      });
      return sendJSON(res, 200, JSON.parse(out.trim() || '{}'));
    } catch (e) {
      return sendJSON(res, 500, { error: 'prosa status failed', detail: String(e.message || e) });
    }
  }

  // API: Prosa — NarrativeSpec → Text (rein, model vs. fallback)
  // Body: NarrativeSpec direkt als JSON-Objekt (z.B. {task, tone, max_sentences})
  //       ODER eingewickelt als {spec: {...}}. Beides wird akzeptiert.
  if (req.method === 'POST' && pathname === '/api/prosa') {
    const body = await readJSON(req);
    const wrapped = (body && typeof body === 'object' && !Array.isArray(body)
                     && typeof body.spec === 'object' && body.spec !== null
                     && !Array.isArray(body.spec));
    const spec = wrapped ? body.spec : body;
    const result = renderProsa(spec);
    if (result.error) return sendJSON(res, 400, result);
    return sendJSON(res, 200, result);
  }

  // 404
  sendJSON(res, 404, { error: 'not found' });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`🦇 Shinon UI · http://127.0.0.1:${PORT}`);
  console.log(`   Chat:    http://127.0.0.1:${PORT}/`);
  console.log(`   Stats:   http://127.0.0.1:${PORT}/stats`);
  console.log(`   Settings: ⚙️  Button in Sidebar`);
});

// ═══ Fallback Reply Generator ═══════════════════════════════════════
function generateFallbackReply(message) {
  const lower = message.toLowerCase();
  if (lower.includes('hallo') || lower.includes('hi') || lower.includes('hey'))
    return 'Hallo. Was willst du wissen? Ich bin nicht hier um Smalltalk zu machen.';
  if (lower.includes('wer bist du') || lower.includes('was bist du'))
    return 'Ich bin Shinon. Eine kritische, skeptische KI. Ich hinterfrage Annahmen — auch deine. Und ich bin offline, also bekommst du nur diese vorgefertigte Antwort. Starte LIMEN für echte Antworten.';
  if (lower.includes('hilfe') || lower.includes('help'))
    return 'Wobei brauchst du Hilfe? Sei präzise. Und starte LIMEN (./shinon start) für echte KI-Antworten.';
  return '⚠️ LIMEN ist nicht erreichbar. Ich kann im Moment nur eingeschränkt antworten. Starte LIMEN mit: ./shinon start';
}
