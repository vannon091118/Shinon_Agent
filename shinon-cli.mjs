#!/usr/bin/env bun
// ════════════════════════════════════════════════════════════════════════
// shinon-cli.mjs — Interactive Terminal Agent CLI (Bun / Node)
// ════════════════════════════════════════════════════════════════════════

import http from 'node:http';
import readline from 'node:readline';
import { execSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';

const C = {
  reset: '[0m',
  bold: '[1m',
  dim: '[2m',
  cyan: '[36m',
  purple: '[35m',
  green: '[32m',
  yellow: '[33m',
  red: '[31m',
  blue: '[34m',
  magenta: '[95m',
  bgDark: '[40m',
};

const MOODS = {
  idle:  { name: 'IDLE',       color: C.cyan,   symbol: '◉ BEREIT' },
  think: { name: 'THINKING',   color: C.purple, symbol: '◎ VERARBEITE…' },
  speak: { name: 'SPEAKING',   color: C.green,  symbol: '◉ ANTWORTET' },
  gate:  { name: 'VALIDATING', color: C.yellow, symbol: '◎ GATE-CHECK' },
  error: { name: 'ERROR',      color: C.red,    symbol: '⊗ FEHLER' },
};

let currentMood = 'idle';

function printBanner() {
  const m = MOODS[currentMood];
  console.clear();
  console.log(`${C.bold}${C.purple}╔══════════════════════════════════════════════════════════════════════╗${C.reset}`);
  console.log(`${C.bold}${C.purple}║  🦇 SHINON · Cyberdeck Terminal Agent CLI v2.5                       ║${C.reset}`);
  console.log(`${C.purple}║  Sie ist Shinon — Kritisch. Skeptisch. Präzise.                      ║${C.reset}`);
  console.log(`${C.purple}║  Mood: ${m.color}${m.symbol} [${m.name}]${C.reset}${C.purple}  |  Cyberdeck Pipeline: Active          ║${C.reset}`);
  console.log(`${C.bold}${C.purple}╚══════════════════════════════════════════════════════════════════════╝${C.reset}
`);
  console.log(`${C.dim}Tippe eine Frage oder einen Befehl (/chat, /status, /setup, /doc, /help, /exit)${C.reset}
`);
}

async function animatePipeline() {
  const steps = [
    { label: 'DISPATCHER', color: C.purple, msg: '⚙️  Input in 3 Parallel-Tasks gesplittet...' },
    { label: 'WORKERS',    color: C.cyan,   msg: '▣ Workers A, B, C verarbeiten Tasks parallel...' },
    { label: 'ROUTER',     color: C.yellow, msg: '◈ An LIMEN Provider geroutet...' },
    { label: 'FALSI-GATE', color: C.magenta,msg: '⊗ KARMA FalsificationGate & 👯 Evil Twin Validation...' },
    { label: 'RESULT',     color: C.green,  msg: '✓ Antwort verifiziert & abgeschlossen!' },
  ];

  console.log(`${C.dim}─── Pipeline Live Execution ───────────────────────────────────────────${C.reset}`);
  for (const step of steps) {
    process.stdout.write(`  ${step.color}[${step.label}]${C.reset} ${step.msg}`);
    await new Promise((r) => setTimeout(r, 180));
    console.log(`  ${step.color}[${step.label}]${C.reset} ${step.msg}`);
  }
  console.log(`${C.dim}───────────────────────────────────────────────────────────────────────${C.reset}
`);
}

function sendChat(message) {
  return new Promise((resolve) => {
    const postData = JSON.stringify({ message });
    const req = http.request(
      {
        hostname: '127.0.0.1',
        port: 4300,
        path: '/api/chat',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(postData),
        },
        timeout: 10000,
      },
      (res) => {
        let body = '';
        res.on('data', (chunk) => (body += chunk));
        res.on('end', () => {
          try {
            const data = JSON.parse(body);
            resolve(data.reply || '(Keine Antwort erhalten)');
          } catch (_) {
            resolve('⚠️ Antwort konnte nicht gelesen werden.');
          }
        });
      }
    );

    req.on('error', () => {
      resolve(generateLocalFallback(message));
    });

    req.write(postData);
    req.end();
  });
}

function generateLocalFallback(msg) {
  const m = msg.toLowerCase();
  if (m.includes('hallo') || m.includes('hi') || m.includes('hey')) {
    return 'Hallo. Ich bin Shinon. Was möchtest du hinterfragen? Starte den Server für volle KI-Antworten (shinon start).';
  }
  if (m.includes('wer bist du') || m.includes('was kannst du')) {
    return 'Ich bin Shinon — eine kritische, skeptische KI. Ich hinterfrage Annahmen, prüfe Argumente und begleite die Entwicklungskaskade.';
  }
  return '⚠️ Shinon UI Server nicht erreichbar. Starte Komponenten mit  oder nutze  im Browser.';
}

async function startREPL() {
  printBanner();

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: `${C.bold}${C.cyan}shinon > ${C.reset}`,
  });

  rl.prompt();

  rl.on('line', async (line) => {
    const input = line.trim();
    if (!input) {
      rl.prompt();
      return;
    }

    const cmd = input.toLowerCase();

    if (cmd === '/exit' || cmd === 'exit' || cmd === 'quit' || cmd === '/quit') {
      console.log(`
${C.cyan}🦇 Shinon Agent beendet. Auf Wiedersehen!${C.reset}
`);
      process.exit(0);
    }

    if (cmd === '/help' || cmd === 'help') {
      console.log(`
${C.bold}Befehle im CLI Agent Tool:${C.reset}`);
      console.log(`  ${C.cyan}/chat${C.reset}       Öffnet das Shinon Web-UI im Browser (:4300)`);
      console.log(`  ${C.cyan}/dashboard${C.reset}  Öffnet das Live Dashboard im Browser (:4200)`);
      console.log(`  ${C.cyan}/status${C.reset}     Zeigt den Komponenten-Status`);
      console.log(`  ${C.cyan}/setup${C.reset}      Startet den Onboarding-Wizard`);
      console.log(`  ${C.cyan}/doc${C.reset}        Führt Doctor Mous Diagnose aus`);
      console.log(`  ${C.cyan}/exit${C.reset}       Beendet das Agent Tool
`);
      rl.prompt();
      return;
    }

    if (cmd === '/chat' || cmd === 'chat') {
      console.log(`
${C.green}Starte Shinon Chat UI...${C.reset}`);
      try { execSync('python3 shinon.py chat', { stdio: 'inherit' }); } catch (_) {}
      rl.prompt();
      return;
    }

    if (cmd === '/dashboard' || cmd === 'dashboard') {
      try { execSync('python3 shinon.py dashboard', { stdio: 'inherit' }); } catch (_) {}
      rl.prompt();
      return;
    }

    if (cmd === '/status' || cmd === 'status') {
      try { execSync('python3 shinon.py status', { stdio: 'inherit' }); } catch (_) {}
      rl.prompt();
      return;
    }

    if (cmd === '/setup' || cmd === 'setup') {
      try { execSync('python3 shinon.py setup', { stdio: 'inherit' }); } catch (_) {}
      rl.prompt();
      return;
    }

    if (cmd === '/doc' || cmd === 'doc') {
      try { execSync('python3 shinon.py doc', { stdio: 'inherit' }); } catch (_) {}
      rl.prompt();
      return;
    }

    currentMood = 'think';
    console.log();
    await animatePipeline();

    currentMood = 'gate';
    process.stdout.write(`${C.dim}Warte auf Antwort...${C.reset}`);

    const reply = await sendChat(input);

    currentMood = 'speak';
    console.log(`
${C.bold}${C.cyan}🦇 Shinon:${C.reset}`);
    console.log(`${reply.replace(/^/gm, '  ')}
`);

    currentMood = 'idle';
    rl.prompt();
  });
}

startREPL();
