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
//
// Usage:
//   node shinon-server.mjs [PORT]
// ═══════════════════════════════════════════════════════════════════════

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';
import { HTML } from './shinon-ui.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.argv[2] || '4300', 10);

const PROJECT_ROOT = __dirname;
const LIMEN_DB = path.join(PROJECT_ROOT, 'data/limen/limen.db');
const TID_DB = path.join(PROJECT_ROOT, '.agents/skills/goal-chain/db/tid-state.db');
// ─── Project-relative SHINON memory (Standalone Mode, no $HOME leak)
const SHINON_DATA_DIR = process.env.SHINON_DATA_DIR
  || path.join(__dirname, 'data', 'shinon');
try { fs.mkdirSync(SHINON_DATA_DIR, { recursive: true }); } catch (_) {}
const SHINON_MEM = path.join(SHINON_DATA_DIR, 'memory.db');
const LIMEN_URL = 'http://127.0.0.1:8000';

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

function queryDB(dbPath, sql, ...params) {
  try {
    if (!fs.existsSync(dbPath)) return null;
    const escaped = sql.replace(/'/g, "'\\''");
    const result = execSync(
      `python3 -c "
import sqlite3,json
conn=sqlite3.connect('${dbPath}')
cur=conn.cursor()
cur.execute('''${escaped}''')
rows=[dict(r) for r in cur.fetchall()]
print(json.dumps(rows,default=str))
conn.close()
"`, { timeout: 5000, encoding: 'utf-8', maxBuffer: 1024 * 1024 }
    );
    return JSON.parse(result.trim() || '[]');
  } catch (e) { return []; }
}

function execDB(dbPath, sql) {
  try {
    const escaped = sql.replace(/'/g, "'\\''");
    execSync(`python3 -c "
import sqlite3
conn=sqlite3.connect('${dbPath}')
conn.execute('''${escaped}''')
conn.commit()
conn.close()
"`, { timeout: 5000 });
    return true;
  } catch (e) { return false; }
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
  if (req.method === 'GET' && pathname === '/stats') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(HTML);
  }

  // API: Ping
  if (pathname === '/api/ping') return sendJSON(res, 200, { ok: true, time: new Date().toISOString() });

  // API: Chat
  if (req.method === 'POST' && pathname === '/api/chat') {
    const body = await readJSON(req);
    const message = body.message || '';
    const personality = body.personality || {};

    // Build system prompt with personality
    const skepticism = personality.skepticism || 8;
    const directness = personality.directness || 7;

    const systemPrompt = `Du bist Shinon — eine kritische, skeptische KI-Persönlichkeit. 
Deine Kern-Haltung: Hinterfragen, prüfen, validieren. Glaube nichts ungeprüft.
Skepsis-Level: ${skepticism}/10. Direktheit: ${directness}/10.
Antworte auf Deutsch. Sei präzise, direkt und ehrlich. Kein Geschwafel. Kein Yes-Man-Verhalten.
Wenn du etwas nicht weißt, sag es klar. Wenn der User Unsinn redet, sag es ihm.`;

    try {
      // Forward to LIMEN
      const limenReq = http.request({
        hostname: '127.0.0.1', port: 8000, path: '/v1/chat/completions',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        timeout: 30000,
      }, (limenRes) => {
        let data = '';
        limenRes.on('data', c => data += c);
        limenRes.on('end', () => {
          try {
            const json = JSON.parse(data);
            const reply = json.choices?.[0]?.message?.content || '(LIMEN antwortete ohne Inhalt)';
            const model = json.model || '?';
            sendJSON(res, 200, { reply, model });
          } catch (e) {
            sendJSON(res, 200, { reply: '(Fehler beim Parsen der LIMEN-Antwort)' });
          }
        });
      });
      limenReq.on('error', () => {
        // Fallback: generiere kritische Antwort ohne LLM
        const fallback = generateFallbackReply(message);
        sendJSON(res, 200, { reply: fallback, model: 'shinon-fallback' });
      });
      limenReq.write(JSON.stringify({
        model: 'auto',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: message },
        ],
        max_tokens: 500,
      }));
      limenReq.end();
    } catch (e) {
      const fallback = generateFallbackReply(message);
      sendJSON(res, 200, { reply: fallback, model: 'shinon-offline' });
    }
    return;
  }

  // API: Keys
  if (req.method === 'GET' && pathname === '/api/keys') {
    const rows = queryDB(LIMEN_DB, "SELECT key_id, provider, deployment, status, health_score, observed_rpm, error_count, success_count FROM providers WHERE value != ''");
    const keys = (rows || []).map(r => ({
      id: r.key_id, provider: r.provider, deployment: r.deployment,
      status: r.status, health_pct: Math.round(r.health_score || 100),
      rpm: Math.round(r.observed_rpm || 0), errors: r.error_count || 0, success: r.success_count || 0,
    }));
    return sendJSON(res, 200, { keys, total: keys.length, active: keys.filter(k => k.status === 'active').length });
  }

  if (req.method === 'POST' && pathname === '/api/keys') {
    const body = await readJSON(req);
    const provider = body.provider;
    const value = body.value;
    if (!provider || !value) return sendJSON(res, 400, { error: 'provider and value required' });

    const keyId = provider + '-shinon-ui';
    const meta = JSON.stringify({ api_key: value, source: 'shinon-ui' });
    const ok = execDB(LIMEN_DB,
      `INSERT OR REPLACE INTO providers (key_id, provider, deployment, value, status, priority, meta_json)
       VALUES ('${keyId}', '${provider}', 'default', '${value}', 'active', 1, '${meta}')`);
    return sendJSON(res, ok ? 200 : 500, { ok: !!ok });
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
    for (const [key, value] of Object.entries(body)) {
      execDB(SHINON_MEM, `UPDATE attitudes SET value = ${Number(value)}, updated_at = datetime('now') WHERE dimension = '${key}'`);
    }
    return sendJSON(res, 200, { ok: true });
  }

  // API: State (proxied from dashboard DB)
  if (pathname === '/api/state') {
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
  if (pathname === '/api/triggers') {
    const rows = queryDB(TID_DB, "SELECT decision_type as skill, COUNT(*) as trigger_count FROM dispatcher_decisions WHERE decision_type LIKE '%TRIGGER%' OR decision_type = 'CHAIN_SCRIPT_FAILED' GROUP BY decision_type ORDER BY trigger_count DESC LIMIT 10");
    return sendJSON(res, 200, { triggers: rows || [] });
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
