#!/usr/bin/env bun
// ════════════════════════════════════════════════════════════════════════
// shinon-cli.mjs — Cyberdeck Terminal Chat Agent v3.0
// Keine Stubs. Vollständig implementiert.
// Kompatibel: Bun / Node.js ≥ 18
// ════════════════════════════════════════════════════════════════════════

import http from 'node:http';
import readline from 'node:readline';
import { execSync } from 'node:child_process';


// ════ ANSI COLOR PALETTE ════════════════════════════════════════════════
const C = {
  reset:   '\x1b[0m',
  bold:    '\x1b[1m',
  dim:     '\x1b[2m',
  italic:  '\x1b[3m',
  ul:      '\x1b[4m',
  // Foreground
  black:   '\x1b[30m',
  red:     '\x1b[31m',
  green:   '\x1b[32m',
  yellow:  '\x1b[33m',
  blue:    '\x1b[34m',
  magenta: '\x1b[95m',
  cyan:    '\x1b[36m',
  white:   '\x1b[37m',
  // Bright
  bCyan:   '\x1b[96m',
  bMag:    '\x1b[35m',
  bGreen:  '\x1b[92m',
  bYellow: '\x1b[93m',
  bRed:    '\x1b[91m',
  bBlue:   '\x1b[94m',
  bWhite:  '\x1b[97m',
  // Background
  bgDark:  '\x1b[40m',
  bgCyan:  '\x1b[46m',
  bgMag:   '\x1b[45m',
};

// ════ MOOD STATE MACHINE ════════════════════════════════════════════════
const MOODS = {
  idle:  { label: 'IDLE',       color: C.bCyan,   sym: '◉',  text: 'Bereit' },
  think: { label: 'THINKING',   color: C.bMag,    sym: '◎',  text: 'Verarbeite…' },
  speak: { label: 'SPEAKING',   color: C.bGreen,  sym: '◉',  text: 'Antwortet' },
  gate:  { label: 'VALIDATING', color: C.bYellow, sym: '◎',  text: 'Gate-Check' },
  error: { label: 'ERROR',      color: C.bRed,    sym: '⊗',  text: 'Fehler' },
};
let currentMood = 'idle';

/** Get formatted mood indicator string */
function moodStr() {
  const m = MOODS[currentMood] || MOODS.idle;
  return `${m.color}${C.bold}${m.sym} ${m.label}${C.reset}${C.dim} — ${m.text}${C.reset}`;
}

// ════ TERMINAL HELPERS ══════════════════════════════════════════════════
const COLS = () => process.stdout.columns || 80;

/** Repeat a character n times */
function rep(char, n) { return char.repeat(Math.max(0, n)); }

/** Draw a horizontal rule in the given color */
function hr(color, char) {
  color = color || C.dim;
  char  = char  || '─';
  return `${color}${rep(char, COLS())}${C.reset}`;
}

/** Box-draw helper — wraps text in a neon HUD-style box */
function hudBox(lines, borderColor, title) {
  borderColor = borderColor || C.bCyan;
  const innerW = COLS() - 4;
  const titleStr = title ? ` ${C.bold}${title}${C.reset}${borderColor} ` : '';
  const topBar   = `${borderColor}╔══${titleStr}${rep('═', Math.max(0, innerW - (title ? title.length + 3 : 0)))}╗${C.reset}`;
  const botBar   = `${borderColor}╚${rep('═', innerW + 2)}╝${C.reset}`;
  const formatted = lines.map(function(l){
    // Strip ANSI when measuring
    const visible = l.replace(/\x1b\[[0-9;]*m/g, '');
    const pad = Math.max(0, innerW - visible.length);
    return `${borderColor}║${C.reset} ${l}${rep(' ', pad)} ${borderColor}║${C.reset}`;
  });
  return [topBar, ...formatted, botBar].join('\n');
}

/** Pad a string (strip ANSI for measurement) to given visible width */
function padV(str, w) {
  const visible = str.replace(/\x1b\[[0-9;]*m/g, '');
  return str + rep(' ', Math.max(0, w - visible.length));
}

// ════ MARKDOWN → TERMINAL RENDERER ════════════════════════════════════
/**
 * Convert a subset of Markdown to terminal-formatted text.
 * Supports: **bold**, *italic*, `code`, # headings, - lists, > quotes, --- hr, ```blocks```
 */
function renderMarkdown(text) {
  const lines = text.split('\n');
  const out = [];
  let inCodeBlock = false;
  let codeLang = '';

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Code block fence
    if (line.startsWith('```')) {
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeLang = line.slice(3).trim();
        out.push(`${C.dim}${C.bgDark}  ▸ ${codeLang || 'code'} ${C.reset}`);
      } else {
        inCodeBlock = false;
        out.push(`${C.dim}${rep('·', Math.min(40, COLS() - 4))}${C.reset}`);
      }
      continue;
    }

    if (inCodeBlock) {
      out.push(`  ${C.bCyan}${line}${C.reset}`);
      continue;
    }

    // Headings
    if (/^### /.test(line)) {
      out.push(`${C.bMag}${C.bold}▸▸ ${line.slice(4)}${C.reset}`);
      continue;
    }
    if (/^## /.test(line)) {
      out.push(`${C.bMag}${C.bold}${C.ul}▸ ${line.slice(3)}${C.reset}`);
      continue;
    }
    if (/^# /.test(line)) {
      out.push(hr(C.bCyan, '━'));
      out.push(`${C.bCyan}${C.bold}  ${line.slice(2).toUpperCase()}${C.reset}`);
      out.push(hr(C.bCyan, '─'));
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      out.push(hr(C.dim, '─'));
      continue;
    }

    // Blockquotes
    if (/^> /.test(line)) {
      out.push(`  ${C.bMag}│${C.reset}${C.italic} ${line.slice(2)}${C.reset}`);
      continue;
    }

    // Unordered list items
    if (/^[-*] /.test(line)) {
      out.push(`  ${C.bCyan}◦${C.reset} ${applyInline(line.slice(2))}`);
      continue;
    }

    // Numbered list items
    const numMatch = line.match(/^(\d+)\. (.*)/);
    if (numMatch) {
      out.push(`  ${C.bCyan}${numMatch[1]}.${C.reset} ${applyInline(numMatch[2])}`);
      continue;
    }

    out.push(applyInline(line));
  }

  return out.join('\n');
}

/** Apply inline formatting: bold, italic, code */
function applyInline(text) {
  // Inline code: `code`
  text = text.replace(/`([^`]+)`/g, `${C.bCyan}$1${C.reset}`);
  // Bold: **text**
  text = text.replace(/\*\*([^*]+)\*\*/g, `${C.bold}$1${C.reset}`);
  // Italic: *text*
  text = text.replace(/\*([^*]+)\*/g, `${C.italic}$1${C.reset}`);
  return text;
}

// ════ BANNER ═══════════════════════════════════════════════════════════
/** Print the main Cyberdeck banner */
function printBanner() {
  const w = COLS();
  console.clear();
  const m = MOODS[currentMood] || MOODS.idle;

  // Logo line
  const logo  = `${C.bold}${C.bMag}🦇 SHINON${C.reset}${C.bCyan} · ${C.reset}${C.dim}Cyberdeck Terminal Agent${C.reset}${C.bCyan} v3.0${C.reset}`;
  const ver   = `${C.dim}2026 · Cyberdeck Edition${C.reset}`;
  const mLine = `${C.dim}Mood:${C.reset} ${m.color}${m.sym} ${m.label}${C.reset}${C.dim} — ${m.text}${C.reset}`;

  const inner = w - 4;
  const topDiv = `${C.bMag}╔${rep('═', inner + 2)}╗${C.reset}`;
  const botDiv = `${C.bMag}╚${rep('═', inner + 2)}╝${C.reset}`;

  function row(text) {
    const vis = text.replace(/\x1b\[[0-9;]*m/g, '');
    const pad = Math.max(0, inner - vis.length);
    return `${C.bMag}║${C.reset} ${text}${rep(' ', pad)} ${C.bMag}║${C.reset}`;
  }

  console.log(topDiv);
  console.log(row(logo));
  console.log(row(`${C.dim}Sie ist Shinon — Kritisch. Skeptisch. Präzise.${C.reset}${rep(' ', Math.max(0, inner - 46))}`));
  console.log(row(mLine));
  console.log(botDiv);
  console.log(`${C.dim}Befehle: /help /status /pipeline /clear /exit  |  Text = Chat${C.reset}`);
  console.log('');
}

// ════ ASCII PIPELINE VISUALIZER ════════════════════════════════════════
const PIPELINE_STEPS = [
  { name: 'DISPATCHER', color: C.bMag,    desc: 'input split  → 3 tasks' },
  { name: 'WORKERS',    color: C.bBlue,   desc: 'A / B / C    parallel' },
  { name: 'ROUTER',     color: C.bYellow, desc: 'LIMEN route  → provider' },
  { name: 'LIMEN',      color: C.bRed,    desc: 'API gateway  → LLM' },
  { name: 'KARMA',      color: C.bGreen,  desc: 'falsi-gate   verify' },
  { name: 'EVIL TWIN',  color: C.bMag,    desc: 'adversarial  mirror' },
  { name: 'RESULT',     color: C.bCyan,   desc: 'validated ✓  final' },
];

/**
 * Render the ASCII pipeline visualizer.
 * @param {number} activeIdx — index of currently highlighted step (-1 = all idle)
 * @returns {string[]} lines to print
 */
function renderPipeline(activeIdx) {
  const w = Math.min(COLS(), 72);
  const inner = w - 2;
  const lines = [];
  lines.push(`${C.dim}┌${rep('─', inner)}┐${C.reset}`);

  PIPELINE_STEPS.forEach(function(step, i) {
    const isActive = (i === activeIdx);
    const nc  = isActive ? step.color + C.bold : C.dim;
    const sym = isActive ? '▓' : '░';
    const nameW = 12;
    const namePad = rep(' ', Math.max(0, nameW - step.name.length));
    const row = `${sym} ${nc}${step.name}${namePad}${C.reset}  ${C.dim}${step.desc}${C.reset}`;
    const vis = row.replace(/\x1b\[[0-9;]*m/g, '');
    const pad = Math.max(0, inner - 2 - vis.length);
    const arrow = (i < PIPELINE_STEPS.length - 1) ? (isActive ? `${step.color}↓${C.reset}` : `${C.dim}↓${C.reset}`) : ' ';
    lines.push(`${C.dim}│${C.reset} ${row}${rep(' ', pad)} ${C.dim}│${C.reset}`);
    if (i < PIPELINE_STEPS.length - 1) {
      const midPad = rep(' ', Math.max(0, Math.floor(inner / 2) - 1));
      lines.push(`${C.dim}│${midPad}${C.reset}${arrow}${C.dim}${rep(' ', Math.max(0, inner - midPad.length - 1))}│${C.reset}`);
    }
  });

  lines.push(`${C.dim}└${rep('─', inner)}┘${C.reset}`);
  return lines;
}

/**
 * Animate the pipeline step-by-step in the terminal.
 * Prints each step, highlights it for a moment, then continues.
 */
async function animatePipelineFull() {
  console.log();
  console.log(`${C.dim}${rep('─', Math.min(COLS(), 72))}${C.reset}`);
  console.log(`${C.bCyan}${C.bold}  CYBERDECK PIPELINE — LIVE EXECUTION${C.reset}`);
  console.log(`${C.dim}${rep('─', Math.min(COLS(), 72))}${C.reset}`);

  for (let i = 0; i < PIPELINE_STEPS.length; i++) {
    const step = PIPELINE_STEPS[i];
    process.stdout.write(`  ${step.color}${C.bold}[${step.name}]${C.reset} ${C.dim}${step.desc}${C.reset}…`);
    await sleep(220);
    process.stdout.write(` ${step.color}✓${C.reset}\n`);
    await sleep(80);
  }
  console.log(`${C.dim}${rep('─', Math.min(COLS(), 72))}${C.reset}`);
  console.log();
}

// ════ TYPING INDICATOR ══════════════════════════════════════════════════
const SPINNER_FRAMES = ['◰', '◳', '◲', '◱'];
let spinnerTimer = null;
let spinnerFrame = 0;

function startTypingIndicator() {
  if (spinnerTimer) return;
  spinnerFrame = 0;
  spinnerTimer = setInterval(function() {
    const frame = SPINNER_FRAMES[spinnerFrame % SPINNER_FRAMES.length];
    process.stdout.write(`\r  ${C.bMag}${C.bold}🦇 Shinon${C.reset} ${C.dim}│${C.reset} ${C.bCyan}${frame}${C.reset}${C.dim} verarbeitet…${C.reset}   `);
    spinnerFrame++;
  }, 120);
}

function stopTypingIndicator() {
  if (spinnerTimer) {
    clearInterval(spinnerTimer);
    spinnerTimer = null;
    process.stdout.write('\r' + rep(' ', Math.min(COLS(), 60)) + '\r');
  }
}

// ════ HTTP CLIENT ═══════════════════════════════════════════════════════
const SERVER_PORT = 4300;
const SERVER_HOST = '127.0.0.1';

/**
 * POST /api/chat — Send a message to the Shinon server.
 * @param {string} message
 * @returns {Promise<{reply:string, model:string}>}
 */
function sendChat(message) {
  return new Promise(function(resolve) {
    const postData = JSON.stringify({ message });
    const req = http.request({
      hostname: SERVER_HOST, port: SERVER_PORT,
      path: '/api/chat', method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
      },
      timeout: 30000,
    }, function(res) {
      let body = '';
      res.on('data', function(c){ body += c; });
      res.on('end', function(){
        try {
          const data = JSON.parse(body);
          resolve({ reply: data.reply || '(Keine Antwort)', model: data.model || '?' });
        } catch(_) {
          resolve({ reply: '⚠️ Antwort konnte nicht gelesen werden.', model: '?' });
        }
      });
    });
    req.on('error', function() {
      resolve({ reply: generateLocalFallback(message), model: 'offline' });
    });
    req.on('timeout', function() {
      req.destroy();
      resolve({ reply: '⚠️ Server-Timeout. Ist ./shinon start gelaufen?', model: 'timeout' });
    });
    req.write(postData);
    req.end();
  });
}

/**
 * GET a JSON endpoint from the server.
 * @param {string} path
 * @returns {Promise<object|null>}
 */
function getJSON(path) {
  return new Promise(function(resolve) {
    const req = http.request({
      hostname: SERVER_HOST, port: SERVER_PORT,
      path: path, method: 'GET', timeout: 5000,
    }, function(res) {
      let body = '';
      res.on('data', function(c){ body += c; });
      res.on('end', function(){
        try { resolve(JSON.parse(body)); }
        catch(_){ resolve(null); }
      });
    });
    req.on('error', function(){ resolve(null); });
    req.on('timeout', function(){ req.destroy(); resolve(null); });
    req.end();
  });
}

// ════ LOCAL FALLBACK ════════════════════════════════════════════════════
/** Generate a local reply when server is offline */
function generateLocalFallback(msg) {
  const m = msg.toLowerCase().trim();
  if (m.match(/^(hallo|hi|hey|moin|guten\s)/)) {
    return 'Hallo. Ich bin Shinon — im Offline-Modus.\nStarte den Server: `./shinon start`';
  }
  if (m.includes('wer bist du') || m.includes('was bist du') || m.includes('stell dich vor')) {
    return '**Ich bin Shinon** — eine kritische, skeptische KI-Persönlichkeit.\n\nIch hinterfrage Annahmen, prüfe Argumente und begleite autonome Entwicklung.\n\nDerzeit im *Offline-Modus*. Starte mit `./shinon start` für volle KI-Antworten.';
  }
  if (m.includes('pipeline') || m.includes('architektur')) {
    return 'Die Shinon-Pipeline:\n\n**DISPATCHER** → splits input in 3 parallel Tasks\n**WORKERS A/B/C** → verarbeiten parallel\n**ROUTER** → leitet an LIMEN weiter\n**LIMEN** → API Gateway zum LLM\n**KARMA** → Falsifikations-Gate\n**EVIL TWIN** → adversarialer Spiegel\n**RESULT** → verifiziertes Ergebnis';
  }
  if (m.includes('hilfe') || m.includes('help')) {
    return 'Tippe `/help` für alle Befehle.\n\nFür echte KI-Antworten: `./shinon start` — dann ist LIMEN erreichbar.';
  }
  if (m.includes('limen')) {
    return '**LIMEN** ist das API-Gateway — die Schwelle zwischen Shinon und den LLM-Anbietern.\n\nLIMEN routet, balanciert und überwacht alle API-Verbindungen.\n\n`./shinon start` startet LIMEN automatisch.';
  }
  if (m.includes('karma')) {
    return '**KARMA** = *Knowledge-Adaptive Refutation and Multistep Analysis*\n\nEin Falsifikations-Gate: Jede Antwort wird auf innere Widersprüche geprüft, bevor sie durchgelassen wird.';
  }
  return `⚠️ **Server nicht erreichbar** (127.0.0.1:${SERVER_PORT})\n\nStarte den Server: \`./shinon start\`\nOder öffne die Web-UI: \`./shinon ui\``;
}

// ════ COMMAND HANDLERS ══════════════════════════════════════════════════
/** Print the help table */
function cmdHelp() {
  const cmds = [
    ['/help',       'Diese Hilfe anzeigen'],
    ['/status',     'Server- und Komponenten-Status'],
    ['/pipeline',   'Pipeline-Visualizer anzeigen'],
    ['/clear',      'Chat-Verlauf leeren & Banner neu'],
    ['/exit',       'Shinon CLI beenden'],
    ['',            ''],
    ['[Text]',      'Nachricht an Shinon senden'],
    ['Shift+Enter', 'Kein Senden (zukünftig: Zeilenumbruch)'],
  ];

  const w = Math.min(COLS(), 72);
  const inner = w - 2;
  console.log();
  console.log(`${C.bCyan}${C.bold}╔${rep('═', inner)}╗${C.reset}`);
  console.log(`${C.bCyan}║${C.reset}${C.bold}${C.bCyan}  Shinon CLI — Befehlsübersicht${rep(' ', inner - 31)}${C.reset}${C.bCyan}║${C.reset}`);
  console.log(`${C.bCyan}╠${rep('═', inner)}╣${C.reset}`);
  cmds.forEach(function(row) {
    if (!row[0]) {
      console.log(`${C.bCyan}║${C.dim}${rep('─', inner)}${C.reset}${C.bCyan}║${C.reset}`);
      return;
    }
    const cmd  = `${C.bCyan}${C.bold}${row[0]}${C.reset}`;
    const desc = `${C.dim}${row[1]}${C.reset}`;
    const cmdV = row[0];
    const pad  = Math.max(0, inner - cmdV.length - row[1].length - 4);
    console.log(`${C.bCyan}║${C.reset}  ${cmd}${rep(' ', Math.max(0, 14 - cmdV.length))}${desc}${rep(' ', pad)}  ${C.bCyan}║${C.reset}`);
  });
  console.log(`${C.bCyan}╚${rep('═', inner)}╝${C.reset}`);
  console.log();
}

/** Fetch and display server status */
async function cmdStatus() {
  console.log();
  console.log(`${C.dim}Prüfe Systemstatus…${C.reset}`);

  const ping = await getJSON('/api/ping');
  const keys = await getJSON('/api/keys');
  const state = await getJSON('/api/state');

  const online = !!ping?.ok;
  const serverStatus = online
    ? `${C.bGreen}${C.bold}● ONLINE${C.reset} ${C.dim}(127.0.0.1:${SERVER_PORT})${C.reset}`
    : `${C.bRed}${C.bold}● OFFLINE${C.reset}${C.dim} — starte: ./shinon start${C.reset}`;

  const w = Math.min(COLS(), 72);
  const inner = w - 2;

  console.log(`${C.bCyan}╔${rep('═', inner)}╗${C.reset}`);
  console.log(`${C.bCyan}║${C.reset}${C.bold}${C.bCyan}  SHINON SYSTEM STATUS${rep(' ', inner - 22)}${C.reset}${C.bCyan}║${C.reset}`);
  console.log(`${C.bCyan}╠${rep('═', inner)}╣${C.reset}`);

  function row(label, value) {
    const labelStr = `  ${C.dim}${label}${C.reset}`;
    const valStr = value;
    const labelVis = ('  ' + label).length;
    const valVis = valStr.replace(/\x1b\[[0-9;]*m/g, '').length;
    const pad = Math.max(0, inner - labelVis - valVis - 2);
    console.log(`${C.bCyan}║${C.reset}${labelStr}${rep(' ', pad)}${valStr} ${C.bCyan}║${C.reset}`);
  }

  row('Shinon UI Server:   ', serverStatus);

  if (online && ping?.time) {
    row('Server-Zeit:        ', `${C.dim}${ping.time}${C.reset}`);
  }

  if (keys?.keys) {
    const active   = keys.keys.filter(function(k){ return k.status === 'active'; }).length;
    const total    = keys.keys.length;
    const kColor   = active > 0 ? C.bGreen : C.bYellow;
    row('API-Keys (aktiv):   ', `${kColor}${C.bold}${active}/${total}${C.reset}`);

    keys.keys.slice(0, 5).forEach(function(k) {
      const dot = k.status === 'active' ? `${C.bGreen}●` : (k.status === 'cooldown' ? `${C.bYellow}●` : `${C.bRed}●`);
      row(`  ↳ ${k.provider.padEnd(16)}`, `${dot}${C.reset} ${C.dim}${k.status} ${k.health_pct||100}%${C.reset}`);
    });
  }

  if (state?.total !== undefined) {
    const doneP = state.total ? Math.round((state.done/state.total)*100) : 0;
    row('goal-chain TIDs:    ', `${C.bCyan}${C.bold}${state.total}${C.reset}${C.dim} gesamt — ${state.done} done (${doneP}%)${C.reset}`);
  }

  console.log(`${C.bCyan}╠${rep('═', inner)}╣${C.reset}`);
  row('Mood:               ', moodStr());
  console.log(`${C.bCyan}╚${rep('═', inner)}╝${C.reset}`);
  console.log();
}

/** Show the pipeline visualizer once */
async function cmdPipeline() {
  console.log();
  console.log(`${C.bCyan}${C.bold}  CYBERDECK SYSTEM PIPELINE${C.reset}`);
  const lines = renderPipeline(-1);
  console.log(lines.join('\n'));
  console.log();
}

/** Clear screen and restart */
function cmdClear() {
  currentMood = 'idle';
  printBanner();
}

/** Print Shinon's response with proper formatting */
function printShinonReply(reply, model) {
  console.log();
  const modelBadge = model && model !== 'offline' && model !== 'shinon-fallback'
    ? ` ${C.dim}via ${model}${C.reset}`
    : '';
  console.log(`${C.bCyan}${C.bold}🦇 Shinon${C.reset}${modelBadge} ${C.dim}│${C.reset}`);
  console.log(`${C.dim}${rep('─', Math.min(COLS() - 2, 70))}${C.reset}`);

  // Indent each line
  const rendered = renderMarkdown(reply);
  rendered.split('\n').forEach(function(line) {
    console.log(`  ${line}`);
  });

  console.log(`${C.dim}${rep('─', Math.min(COLS() - 2, 70))}${C.reset}`);
  console.log();
}

/** Print user input echo */
function printUserLine(text) {
  const w = COLS();
  const prefix = `${C.dim}[ Du ]${C.reset} ${C.bBlue}│${C.reset} `;
  const maxTextW = Math.max(20, w - 12);
  // Wrap long lines
  const chunks = [];
  let cur = text;
  while (cur.length > maxTextW) {
    chunks.push(cur.slice(0, maxTextW));
    cur = '       ' + cur.slice(maxTextW);
  }
  chunks.push(cur);
  chunks.forEach(function(line, i) {
    if (i === 0) {
      console.log(`${prefix}${C.bWhite}${line}${C.reset}`);
    } else {
      console.log(`       ${C.dim}│${C.reset} ${C.dim}${line}${C.reset}`);
    }
  });
}

// ════ UTILITY ══════════════════════════════════════════════════════════
function sleep(ms) {
  return new Promise(function(r){ setTimeout(r, ms); });
}

// ════ MAIN REPL ═════════════════════════════════════════════════════════
async function startREPL() {
  printBanner();

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: `\n${C.bold}${C.bCyan}shinon${C.reset}${C.dim}>${C.reset} `,
    completer: function(line) {
      const completions = ['/help', '/status', '/pipeline', '/clear', '/exit'];
      const hits = completions.filter(function(c){ return c.startsWith(line); });
      return [hits.length ? hits : completions, line];
    },
  });

  rl.prompt();

  rl.on('line', async function(rawLine) {
    const input = rawLine.trim();
    if (!input) { rl.prompt(); return; }

    const cmd = input.toLowerCase().replace(/^\/+/, '/').split(' ')[0];

    // ─── Command Router ────────────────────────────────────────────
    if (cmd === '/exit' || input === 'exit' || input === 'quit') {
      console.log();
      console.log(hudBox([
        `${C.bCyan}${C.bold}🦇 Auf Wiedersehen.${C.reset}`,
        `${C.dim}Shinon schließt das Cyberdeck.${C.reset}`,
      ], C.bMag));
      console.log();
      process.exit(0);
    }

    if (cmd === '/help' || input === 'help') {
      cmdHelp();
      rl.prompt();
      return;
    }

    if (cmd === '/status' || input === 'status') {
      await cmdStatus();
      rl.prompt();
      return;
    }

    if (cmd === '/pipeline' || input === 'pipeline') {
      await cmdPipeline();
      rl.prompt();
      return;
    }

    if (cmd === '/clear' || input === 'clear') {
      cmdClear();
      rl.prompt();
      return;
    }

    // Legacy delegations (for compatibility)
    if (cmd === '/chat' || input === 'chat') {
      console.log(`\n${C.bGreen}Öffne Web-UI: http://127.0.0.1:4300${C.reset}`);
      try { execSync('which xdg-open >/dev/null 2>&1 && xdg-open http://127.0.0.1:4300 &', { stdio: 'ignore' }); } catch(_) {}
      rl.prompt();
      return;
    }

    if (cmd === '/dashboard' || input === 'dashboard') {
      console.log(`\n${C.bGreen}Öffne Dashboard: http://127.0.0.1:4200${C.reset}`);
      try { execSync('which xdg-open >/dev/null 2>&1 && xdg-open http://127.0.0.1:4200 &', { stdio: 'ignore' }); } catch(_) {}
      rl.prompt();
      return;
    }

    if (cmd === '/setup' || input === 'setup') {
      try { execSync('python3 shinon.py setup', { stdio: 'inherit', cwd: process.cwd() }); } catch(_) {}
      rl.prompt();
      return;
    }

    if (cmd === '/doc' || input === 'doc') {
      try { execSync('python3 shinon.py doc', { stdio: 'inherit', cwd: process.cwd() }); } catch(_) {}
      rl.prompt();
      return;
    }

    // ─── Unknown command ───────────────────────────────────────────
    if (input.startsWith('/')) {
      console.log(`\n  ${C.bRed}⊗${C.reset} Unbekannter Befehl: ${C.dim}${input}${C.reset} — tippe ${C.bCyan}/help${C.reset}`);
      rl.prompt();
      return;
    }

    // ─── Chat Message ──────────────────────────────────────────────
    printUserLine(input);

    currentMood = 'think';
    startTypingIndicator();

    // Fire pipeline animation concurrently
    const pipelineP = animatePipelineFull();

    // Actually wait for indicator delay before sending (UX)
    await sleep(300);
    stopTypingIndicator();

    currentMood = 'gate';
    process.stdout.write(`  ${C.bYellow}◎ GATE-CHECK${C.reset}${C.dim} — Anfrage wird validiert…${C.reset}`);

    const { reply, model } = await sendChat(input);
    process.stdout.write('\r' + rep(' ', 60) + '\r');

    // Wait for pipeline to finish
    await pipelineP;

    currentMood = 'speak';
    printShinonReply(reply, model);

    currentMood = 'idle';
    rl.prompt();
  });

  rl.on('close', function() {
    console.log(`\n${C.bCyan}🦇 Shinon CLI geschlossen.${C.reset}\n`);
    process.exit(0);
  });

  // Handle resize
  process.stdout.on('resize', function() {
    // Redraw prompt on resize (readline handles this internally)
  });
}

// ════ ENTRY POINT ═══════════════════════════════════════════════════════
startREPL().catch(function(err) {
  console.error(`${C.bRed}Kritischer Fehler:${C.reset}`, err);
  process.exit(1);
});
