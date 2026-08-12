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

// ═══ HTML ══════════════════════════════════════════════════════════════
const HTML = `<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0b1118">
<title>Shinon · Control Plane</title>
<style>
/* ═══ RESET & BASE ═══ */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0b1118;--bg2:#111c26;--bg3:#16222e;--bg4:#1a2a38;
  --fg:#edf3f3;--fg2:#bccfd6;--fg3:#8ba0a7;--fg4:#5a727a;
  --accent:#b7f0df;--accent2:#71e0ad;--gold:#f2bd70;--red:#f07c77;
  --border:rgba(188,211,222,.12);--shadow:0 8px 32px rgba(0,0,0,.3);
  --radius:12px;--radius-sm:8px;
  font-family:"Trebuchet MS","Segoe UI",system-ui,sans-serif;
  background:var(--bg);color:var(--fg);line-height:1.5;
}
body{
  min-height:100vh;
  background:radial-gradient(circle at 15% 0%,rgba(77,157,155,.12),transparent 40rem),
             radial-gradient(circle at 85% 10%,rgba(242,189,112,.08),transparent 30rem),var(--bg);
}
/* ═══ LAYOUT ═══ */
.app{display:flex;height:100vh;overflow:hidden}
.sidebar{
  width:64px;background:var(--bg2);border-right:1px solid var(--border);
  display:flex;flex-direction:column;align-items:center;padding:16px 0;gap:8px;flex-shrink:0;
}
.sidebar-btn{
  width:44px;height:44px;border-radius:var(--radius-sm);border:none;background:transparent;
  color:var(--fg3);cursor:pointer;font-size:20px;transition:all .2s;display:flex;
  align-items:center;justify-content:center;position:relative;
}
.sidebar-btn:hover{background:var(--bg3);color:var(--fg)}
.sidebar-btn.active{background:var(--bg4);color:var(--accent)}
.sidebar-btn .badge{
  position:absolute;top:4px;right:4px;width:8px;height:8px;border-radius:50%;
  background:var(--red);display:none;
}
.sidebar-btn .badge.show{display:block}
.sidebar-spacer{flex:1}
.main{
  flex:1;display:flex;flex-direction:column;overflow:hidden;position:relative;
}
.header{
  padding:12px 24px;border-bottom:1px solid var(--border);background:var(--bg2);
  display:flex;align-items:center;justify-content:space-between;flex-shrink:0;
}
.header h1{font:700 1.1rem Georgia,serif;letter-spacing:-.02em}
.header-right{display:flex;align-items:center;gap:12px}
.status-dot{width:10px;height:10px;border-radius:50%}
.status-dot.live{background:var(--accent2);box-shadow:0 0 8px rgba(113,224,173,.4)}
.status-dot.dead{background:var(--red)}
.page{display:none;flex:1;overflow:hidden}
.page.active{display:flex;flex-direction:column}

/* ═══ CHAT PAGE ═══ */
.chat-messages{flex:1;overflow-y:auto;padding:20px 24px;display:flex;flex-direction:column;gap:16px}
.chat-msg{display:flex;gap:12px;max-width:85%;animation:fadeIn .3s ease}
.chat-msg.user{align-self:flex-end;flex-direction:row-reverse}
.chat-msg.shinon{align-self:flex-start}
.chat-avatar{
  width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-size:18px;flex-shrink:0;
}
.chat-msg.user .chat-avatar{background:var(--bg3)}
.chat-msg.shinon .chat-avatar{background:rgba(183,240,223,.12);color:var(--accent)}
.chat-bubble{
  padding:12px 16px;border-radius:var(--radius);line-height:1.55;font-size:.92rem;
}
.chat-msg.user .chat-bubble{background:var(--bg4);border:1px solid var(--border)}
.chat-msg.shinon .chat-bubble{background:rgba(183,240,223,.06);border:1px solid rgba(183,240,223,.15)}
.chat-bubble .typing{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);animation:typing 1.4s infinite;margin:0 2px}
.chat-bubble .typing:nth-child(2){animation-delay:.2s}
.chat-bubble .typing:nth-child(3){animation-delay:.4s}
@keyframes typing{0%,60%,100%{opacity:.3;transform:translateY(0)}30%{opacity:1;transform:translateY(-4px)}}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.chat-input-area{
  padding:16px 24px;border-top:1px solid var(--border);background:var(--bg2);flex-shrink:0;
}
.chat-input-row{display:flex;gap:10px;align-items:center}
.chat-input-row textarea{
  flex:1;padding:12px 16px;border:1px solid var(--border);border-radius:var(--radius);
  background:var(--bg3);color:var(--fg);font:inherit;font-size:.9rem;resize:none;
  min-height:48px;max-height:120px;outline:none;transition:border-color .2s;
}
.chat-input-row textarea:focus{border-color:var(--accent)}
.chat-input-row button{
  padding:0 20px;height:48px;border:none;border-radius:var(--radius);
  background:var(--accent);color:var(--bg);font:700 .9rem inherit;cursor:pointer;
  transition:all .2s;white-space:nowrap;
}
.chat-input-row button:hover{background:var(--accent2)}
.chat-input-row button:disabled{opacity:.5;cursor:not-allowed}
.chat-empty{
  flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  color:var(--fg3);gap:8px;padding:40px;
}
.chat-empty .icon{font-size:48px;margin-bottom:8px}
.chat-empty h2{font:700 1.5rem Georgia,serif;color:var(--fg2)}
.chat-empty p{max-width:400px;text-align:center;font-size:.9rem}

/* ═══ STATS PAGE ═══ */
.stats-grid{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;
  padding:16px 20px;overflow-y:auto;flex:1;align-content:start;
}
.stat-card{
  background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);
  padding:16px;box-shadow:var(--shadow);
}
.stat-card .card-title{
  font:700 .72rem monospace;letter-spacing:.12em;text-transform:uppercase;
  color:var(--fg3);margin-bottom:12px;
}
.stat-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0}
.stat-row+.stat-row{border-top:1px solid var(--border)}
.stat-label{color:var(--fg3);font-size:.8rem}
.stat-value{font:700 .9rem monospace;font-variant-numeric:tabular-nums}
.stat-value.good{color:var(--accent2)}.stat-value.warn{color:var(--gold)}.stat-value.bad{color:var(--red)}
.health-bar{
  height:4px;border-radius:2px;background:var(--bg3);margin-top:4px;overflow:hidden;
}
.health-bar-fill{height:100%;border-radius:2px;transition:width .5s}
.health-bar-fill.good{background:var(--accent2)}.health-bar-fill.warn{background:var(--gold)}.health-bar-fill.bad{background:var(--red)}
.key-chip{
  display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:20px;
  font-size:.75rem;background:var(--bg3);border:1px solid var(--border);
}
.key-chip .dot{width:7px;height:7px;border-radius:50%}
.key-chip .dot.active{background:var(--accent2)}.key-chip .dot.cooldown{background:var(--gold)}.key-chip .dot.dead{background:var(--red)}
.sparkline{font:9px monospace;color:var(--accent);letter-spacing:1px;white-space:nowrap;overflow:hidden}

/* ═══ SETTINGS SLIDE-OUT ═══ */
.settings-overlay{
  position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:100;
  display:none;opacity:0;transition:opacity .25s;
}
.settings-overlay.open{display:block;opacity:1}
.settings-panel{
  position:fixed;top:0;right:0;bottom:0;width:420px;max-width:90vw;
  background:var(--bg2);border-left:1px solid var(--border);
  z-index:101;transform:translateX(100%);transition:transform .3s ease;
  display:flex;flex-direction:column;overflow-y:auto;
}
.settings-panel.open{transform:translateX(0)}
.settings-header{
  padding:20px 24px;border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;
}
.settings-header h2{font:700 1.1rem Georgia,serif}
.settings-close{
  width:32px;height:32px;border:none;border-radius:50%;background:var(--bg3);
  color:var(--fg3);cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;
  transition:all .2s;
}
.settings-close:hover{background:var(--bg4);color:var(--fg)}
.settings-body{padding:20px 24px;display:flex;flex-direction:column;gap:24px;flex:1}
.settings-section{}
.settings-section h3{
  font:700 .78rem monospace;letter-spacing:.1em;text-transform:uppercase;
  color:var(--fg3);margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border);
}
.settings-row{display:flex;align-items:center;justify-content:space-between;padding:8px 0}
.settings-row label{font-size:.88rem;color:var(--fg2)}
.settings-row input[type=range]{width:140px;accent-color:var(--accent)}
.settings-row .range-val{font:700 .8rem monospace;color:var(--accent);min-width:28px;text-align:right}
.settings-row input[type=password],.settings-row input[type=text]{
  flex:1;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);
  background:var(--bg3);color:var(--fg);font:inherit;font-size:.85rem;outline:none;
}
.settings-row input:focus{border-color:var(--accent)}
.settings-row select{
  padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);
  background:var(--bg3);color:var(--fg);font:inherit;font-size:.85rem;min-width:140px;
}
.settings-row button{
  padding:6px 18px;border:none;border-radius:var(--radius-sm);font:700 .78rem inherit;
  cursor:pointer;transition:all .2s;
}
.btn-save{background:var(--accent);color:var(--bg)}
.btn-save:hover{background:var(--accent2)}
.btn-test{background:rgba(242,189,112,.15);color:var(--gold)}
.btn-test:hover{background:var(--gold);color:var(--bg)}
.btn-danger{background:rgba(240,124,119,.12);color:var(--red)}
.btn-danger:hover{background:var(--red);color:var(--bg)}
.settings-toast{
  padding:8px 14px;border-radius:var(--radius-sm);font-size:.8rem;display:none;
}
.settings-toast.show{display:block}
.settings-toast.ok{background:rgba(113,224,173,.12);color:var(--accent2)}
.settings-toast.err{background:rgba(240,124,119,.12);color:var(--red)}
.tooltip{
  position:relative;display:inline-flex;align-items:center;gap:4px;
  border-bottom:1px dotted var(--fg4);cursor:help;
}
.tooltip::after{
  content:attr(data-tip);position:absolute;bottom:120%;left:50%;transform:translateX(-50%);
  background:var(--bg4);color:var(--fg);padding:6px 10px;border-radius:6px;font-size:.72rem;
  white-space:nowrap;pointer-events:none;opacity:0;transition:opacity .15s;z-index:10;
  border:1px solid var(--border);max-width:260px;white-space:normal;
}
.tooltip:hover::after{opacity:1}

/* ═══ RESPONSIVE ═══ */
@media(max-width:640px){
  .sidebar{width:48px;padding:8px 0}
  .sidebar-btn{width:36px;height:36px;font-size:16px}
  .chat-msg{max-width:95%}
  .stats-grid{grid-template-columns:1fr}
  .settings-panel{width:100vw}
}
@media(prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.01ms!important}
}
</style>
</head>
<body>
<div class="app">
  <!-- Sidebar -->
  <nav class="sidebar">
    <button class="sidebar-btn active" data-page="chat" title="Chat" aria-label="Chat">💬</button>
    <button class="sidebar-btn" data-page="stats" title="Statistiken" aria-label="Statistiken">📊</button>
    <div class="sidebar-spacer"></div>
    <button class="sidebar-btn" id="btn-settings" title="Einstellungen" aria-label="Einstellungen">⚙️<span class="badge" id="keys-badge"></span></button>
  </nav>

  <!-- Main Area -->
  <main class="main">
    <header class="header">
      <h1 id="page-title">💬 Shinon Chat</h1>
      <div class="header-right">
        <span id="conn-dot" class="status-dot live"></span>
        <span id="conn-text" style="font-size:.75rem;color:var(--fg3)">verbunden</span>
      </div>
    </header>

    <!-- Page 1: Chat -->
    <section class="page active" id="page-chat">
      <div class="chat-messages" id="chat-messages">
        <div class="chat-empty" id="chat-empty">
          <div class="icon">🦇</div>
          <h2>Shinon</h2>
          <p>Kritisch. Skeptisch. Präzise.<br>Stell mir eine Frage — ich antworte ehrlich.</p>
        </div>
      </div>
      <div class="chat-input-area">
        <div class="chat-input-row">
          <textarea id="chat-input" rows="1" placeholder="Nachricht an Shinon…" aria-label="Chat-Nachricht"></textarea>
          <button id="chat-send" aria-label="Senden">▶</button>
        </div>
      </div>
    </section>

    <!-- Page 2: Statistics -->
    <section class="page" id="page-stats">
      <div class="stats-grid" id="stats-grid"></div>
    </section>
  </main>
</div>

<!-- Settings Slide-Out -->
<div class="settings-overlay" id="settings-overlay"></div>
<aside class="settings-panel" id="settings-panel">
  <div class="settings-header">
    <h2>⚙️ Einstellungen</h2>
    <button class="settings-close" id="settings-close" aria-label="Schließen">✕</button>
  </div>
  <div class="settings-body">
    <!-- Theme -->
    <div class="settings-section">
      <h3>🎨 Design</h3>
      <div class="settings-row">
        <label>Dark Mode</label>
        <input type="range" id="theme-toggle" min="0" max="1" value="1" oninput="toggleTheme(this.value)" aria-label="Theme">
      </div>
    </div>

    <!-- Persönlichkeit -->
    <div class="settings-section">
      <h3>🎭 Persönlichkeit <span class="tooltip" data-tip="Shinon bleibt immer kritisch/skeptisch. Diese Werte justieren NUR die Intensität.">ⓘ</span></h3>
      <div id="personality-sliders"></div>
    </div>

    <!-- API Keys -->
    <div class="settings-section">
      <h3>🔑 API-Keys</h3>
      <div id="keys-list"></div>
      <div class="settings-row" style="margin-top:8px">
        <select id="key-provider" aria-label="Anbieter">
          <option value="groq">Groq</option>
          <option value="openrouter">OpenRouter</option>
          <option value="nvidia">NVIDIA</option>
        </select>
        <input type="password" id="key-value" placeholder="API-Key…" aria-label="Key">
        <button class="btn-save" id="key-save-btn">Speichern</button>
      </div>
      <div class="settings-toast" id="key-toast"></div>
    </div>

    <!-- Info -->
    <div class="settings-section">
      <h3>ℹ️ Über Shinon</h3>
      <p style="font-size:.82rem;color:var(--fg3);line-height:1.6">
        Shinon Control Plane v1.0<br>
        LIMEN API-Gateway · KARMA FalsificationGate<br>
        goal-chain Entwicklungskaskade · Promtguard Claims<br><br>
        <span class="tooltip" data-tip="Doctor Mous diagnostiziert und repariert Probleme, ohne deine Secrets zu löschen.">🩺 Doctor Mous</span> — <code>./shinon --doc</code>
      </p>
    </div>
  </div>
</aside>

<script>
// ═══ STATE ══════════════════════════════════════════════════
const state = {
  page: 'chat',
  messages: [],
  personality: { skepticism: 8, directness: 7, helpfulness: 4, patience: 5, curiosity: 6 },
  keys: [],
  theme: 'dark',
};

// ═══ PAGE SWITCHING ═════════════════════════════════════════
function switchPage(page) {
  state.page = page;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  document.querySelectorAll('.sidebar-btn[data-page]').forEach(b => b.classList.remove('active'));
  document.querySelector('.sidebar-btn[data-page="' + page + '"]')?.classList.add('active');
  document.getElementById('page-title').textContent = page === 'chat' ? '💬 Shinon Chat' : '📊 Statistiken & Tracking';
  if (page === 'stats') loadStats();
}

document.querySelectorAll('.sidebar-btn[data-page]').forEach(btn => {
  btn.addEventListener('click', () => switchPage(btn.dataset.page));
});

// ═══ SETTINGS SLIDE-OUT ════════════════════════════════════
const overlay = document.getElementById('settings-overlay');
const panel = document.getElementById('settings-panel');

function openSettings() { overlay.classList.add('open'); panel.classList.add('open'); loadSettings(); }
function closeSettings() { overlay.classList.remove('open'); panel.classList.remove('open'); }

document.getElementById('btn-settings').addEventListener('click', openSettings);
document.getElementById('settings-close').addEventListener('click', closeSettings);
overlay.addEventListener('click', closeSettings);

// ═══ CHAT ═══════════════════════════════════════════════════
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const chatSend = document.getElementById('chat-send');
const chatEmpty = document.getElementById('chat-empty');

function addMessage(role, content) {
  if (document.getElementById('chat-empty')) chatEmpty.remove();
  const div = document.createElement('div');
  div.className = 'chat-msg ' + role;
  div.innerHTML = '<div class="chat-avatar">' + (role === 'user' ? '👤' : '🦇') + '</div><div class="chat-bubble">' + escapeHtml(content) + '</div>';
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTyping() {
  if (document.getElementById('chat-empty')) chatEmpty.remove();
  const div = document.createElement('div');
  div.className = 'chat-msg shinon';
  div.id = 'typing-indicator';
  div.innerHTML = '<div class="chat-avatar">🦇</div><div class="chat-bubble"><span class="typing"></span><span class="typing"></span><span class="typing"></span></div>';
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTyping() { const t = document.getElementById('typing-indicator'); if (t) t.remove(); }

async function sendMessage() {
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = '';
  chatSend.disabled = true;

  addMessage('user', text);
  addTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, personality: state.personality }),
    });
    const data = await res.json();
    removeTyping();
    addMessage('shinon', data.reply || '(keine Antwort — ist LIMEN gestartet?)');
  } catch (e) {
    removeTyping();
    addMessage('shinon', '⚠️ Keine Verbindung zum Server. Ist LIMEN gestartet? ./shinon start');
  }
  chatSend.disabled = false;
  chatInput.focus();
}

chatSend.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
}

// ═══ STATS ══════════════════════════════════════════════════
async function loadStats() {
  try {
    const [keysRes, stateRes, triggersRes] = await Promise.all([
      fetch('/api/keys').then(r => r.json()),
      fetch('/api/state').then(r => r.json()).catch(() => ({})),
      fetch('/api/triggers').then(r => r.json()).catch(() => ({})),
    ]);
    renderStats(keysRes, stateRes, triggersRes);
  } catch (e) {
    document.getElementById('stats-grid').innerHTML = '<div class="stat-card"><div class="card-title">⚠️ Nicht verfügbar</div><p style="color:var(--fg3);font-size:.85rem">Server nicht erreichbar</p></div>';
  }
}function renderStats(keysData, stateData, triggersData) {
  const grid = document.getElementById('stats-grid');
  const keys = keysData.keys || [];
  const active = keys.filter(k => k.status === 'active').length;
  const cooldown = keys.filter(k => k.status === 'cooldown').length;
  const dead = keys.filter(k => k.status === 'dead').length;

  // MOCK-Daten wenn kein Backend
  const isOffline = !keys.length && (!stateData || !stateData.total);

  let html = '';

  // Keys Card
  html += '<div class="stat-card"><div class="card-title">🔑 API-Keys</div>';
  if (isOffline) {
    html += '<div class="stat-row"><span class="stat-label" style="color:var(--fg4)">Backend nicht erreichbar</span></div>';
    html += '<div class="stat-row"><span class="stat-label" style="font-size:.72rem;color:var(--gold)">Starte mit: ./shinon start</span></div>';
  } else {
    html += '<div class="stat-row"><span class="stat-label">Aktiv</span><span class="stat-value good">' + active + '</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Cooldown</span><span class="stat-value warn">' + cooldown + '</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Dead</span><span class="stat-value bad">' + dead + '</span></div>';
    if (keys.length === 0) html += '<div class="stat-row"><span class="stat-label" style="color:var(--fg4)">Keine Keys</span></div>';
    for (const k of keys.slice(0, 8)) {
      html += '<div class="stat-row"><span class="stat-label" style="font-size:.72rem">' + k.provider + '</span><span class="stat-value" style="font-size:.72rem">' +
        '<span class="key-chip"><span class="dot ' + k.status + '"></span>' + (k.health_pct || 100) + '%</span></span></div>';
    }
  }
  html += '</div>';

  // TID Card
  if (stateData.total !== undefined) {
    html += '<div class="stat-card"><div class="card-title">🎯 goal-chain TIDs</div>';
    html += '<div class="stat-row"><span class="stat-label">Gesamt</span><span class="stat-value">' + (stateData.total || 0) + '</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Erledigt</span><span class="stat-value good">' + (stateData.done || 0) + '</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Fehlgeschlagen</span><span class="stat-value bad">' + (stateData.failed || 0) + '</span></div>';
    html += '<div class="stat-row"><span class="stat-label">Ausstehend</span><span class="stat-value" style="color:var(--gold)">' + (stateData.pending || 0) + '</span></div>';
    const pct = stateData.total > 0 ? Math.round((stateData.done || 0) * 100 / stateData.total) : 0;
    html += '<div class="health-bar"><div class="health-bar-fill good" style="width:' + pct + '%"></div></div>';
    html += '<div style="font-size:.68rem;color:var(--fg4);margin-top:4px">' + pct + '% abgeschlossen</div>';
    html += '</div>';
  }

  // Triggers Card
  if (triggersData.triggers) {
    html += '<div class="stat-card"><div class="card-title">⚡ KARMA-Trigger</div>';
    const trigs = triggersData.triggers || [];
    html += '<div class="stat-row"><span class="stat-label">Getriggerte Skills</span><span class="stat-value good">' + trigs.length + '</span></div>';
    for (const t of trigs.slice(0, 6)) {
      html += '<div class="stat-row"><span class="stat-label" style="font-size:.7rem">' + (t.skill || t.trigger_type || '?') + '</span><span style="font-size:.65rem;color:var(--fg4)">' + (t.trigger_count || 1) + '×</span></div>';
    }
    html += '</div>';
  }

  // System Card
  html += '<div class="stat-card"><div class="card-title">💻 System</div>';
  html += '<div class="stat-row"><span class="stat-label">LIMEN</span><span class="stat-value good">Port 8000</span></div>';
  html += '<div class="stat-row"><span class="stat-label">Dashboard</span><span class="stat-value good">Port 4200</span></div>';
  html += '<div class="stat-row"><span class="stat-label">Shinon UI</span><span class="stat-value good">Port ' + window.location.port + '</span></div>';
  html += '<div class="stat-row"><span class="stat-label">Aktualisiert</span><span class="stat-value" style="font-size:.7rem">' + new Date().toLocaleTimeString('de-DE') + '</span></div>';
  html += '</div>';

  grid.innerHTML = html;
}

// ═══ SETTINGS ═══════════════════════════════════════════════
async function loadSettings() {
  // Personality
  loadPersonality();
  // Keys
  loadKeys();
}

async function loadPersonality() {
  try {
    const res = await fetch('/api/personality');
    if (res.ok) {
      const data = await res.json();
      Object.assign(state.personality, data);
    }
  } catch (e) {}
  renderPersonalitySliders();
}

function renderPersonalitySliders() {
  const container = document.getElementById('personality-sliders');
  const labels = { skepticism: 'Skepsis', directness: 'Direktheit', helpfulness: 'Hilfsbereitschaft', patience: 'Geduld', curiosity: 'Neugier' };
  const tips = {
    skepticism: 'Hinterfragt Aussagen und Annahmen',
    directness: 'Sagt direkt was Sache ist',
    helpfulness: 'Hilft aktiv vs. zurückhaltend',
    patience: 'Geduldig erklären vs. knapp antworten',
    curiosity: 'Stellt Rückfragen vs. akzeptiert'
  };
  let html = '';
  for (const [key, val] of Object.entries(state.personality)) {
    html += '<div class="settings-row"><label class="tooltip" data-tip="' + (tips[key] || '') + '">' + (labels[key] || key) + '</label>' +
      '<input type="range" min="1" max="10" value="' + val + '" oninput="updatePersonality(\'' + key + '\',this.value)" aria-label="' + key + '">' +
      '<span class="range-val" id="pv-' + key + '">' + val + '</span></div>';
  }
  container.innerHTML = html;
}

function updatePersonality(key, value) {
  state.personality[key] = parseInt(value);
  document.getElementById('pv-' + key).textContent = value;
  fetch('/api/personality', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ [key]: parseInt(value) }),
  }).catch(() => {});
}

async function loadKeys() {
  try {
    const res = await fetch('/api/keys');
    const data = await res.json();
    state.keys = data.keys || [];
    renderKeysList();
    // Badge
    const badge = document.getElementById('keys-badge');
    const deadKeys = state.keys.filter(k => k.status === 'dead' || k.status === 'cooldown').length;
    if (deadKeys > 0) { badge.textContent = deadKeys; badge.classList.add('show'); }
    else badge.classList.remove('show');
  } catch (e) {}
}

function renderKeysList() {
  const container = document.getElementById('keys-list');
  if (state.keys.length === 0) {
    container.innerHTML = '<div style="color:var(--fg4);font-size:.82rem;padding:8px 0">Keine Keys konfiguriert</div>';
    return;
  }
  let html = '';
  for (const k of state.keys) {
    const icon = k.status === 'active' ? '🟢' : (k.status === 'cooldown' ? '🟡' : '🔴');
    html += '<div class="settings-row"><span>' + icon + ' ' + k.provider + '</span><span style="font-size:.72rem;color:var(--fg3)">Health: ' + (k.health_pct || 100) + '%</span></div>';
  }
  container.innerHTML = html;
}

// Key save
document.getElementById('key-save-btn').addEventListener('click', async () => {
  const provider = document.getElementById('key-provider').value;
  const value = document.getElementById('key-value').value.trim();
  if (!value) return;
  const toast = document.getElementById('key-toast');
  try {
    const res = await fetch('/api/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, value }),
    });
    if (res.ok) {
      document.getElementById('key-value').value = '';
      toast.textContent = '✓ Key gespeichert';
      toast.className = 'settings-toast ok show';
      loadKeys();
    } else {
      toast.textContent = '✗ Fehler beim Speichern';
      toast.className = 'settings-toast err show';
    }
  } catch (e) {
    toast.textContent = '✗ Keine Verbindung';
    toast.className = 'settings-toast err show';
  }
  setTimeout(() => toast.classList.remove('show'), 3000);
});

// Theme
function toggleTheme(v) {
  const isDark = v === '1';
  document.documentElement.style.setProperty('--bg', isDark ? '#0b1118' : '#f5f7fa');
  document.documentElement.style.setProperty('--bg2', isDark ? '#111c26' : '#fff');
  document.documentElement.style.setProperty('--bg3', isDark ? '#16222e' : '#e8ecf1');
  document.documentElement.style.setProperty('--bg4', isDark ? '#1a2a38' : '#dde2e8');
  document.documentElement.style.setProperty('--fg', isDark ? '#edf3f3' : '#1a1a2e');
  document.documentElement.style.setProperty('--fg2', isDark ? '#bccfd6' : '#334');
  document.documentElement.style.setProperty('--fg3', isDark ? '#8ba0a7' : '#667');
  document.documentElement.style.setProperty('--fg4', isDark ? '#5a727a' : '#99a');
}

// ═══ POLLING ════════════════════════════════════════════════
let pollTimer = null;
function startPolling() {
  if (state.page === 'stats') loadStats();
  pollTimer = setTimeout(startPolling, 3000);
}
startPolling();

// Check connection
async function checkConn() {
  try {
    const res = await fetch('/api/ping');
    const dot = document.getElementById('conn-dot');
    const txt = document.getElementById('conn-text');
    if (res.ok) { dot.className = 'status-dot live'; txt.textContent = 'verbunden'; }
    else { dot.className = 'status-dot dead'; txt.textContent = 'fehler'; }
  } catch (e) { document.getElementById('conn-dot').className = 'status-dot dead'; document.getElementById('conn-text').textContent = 'getrennt'; }
}
setInterval(checkConn, 10000);
checkConn();
</script>
</body>
</html>`;

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
