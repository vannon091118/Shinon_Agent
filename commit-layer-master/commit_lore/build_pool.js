#!/usr/bin/env node
/**
 * build_pool.js — Baut sidejoke_pool.json dynamisch aus zwei Quellen:
 *   1. Echter Git-Commit-History (bisher alleinige Quelle)
 *   2. PLOT_LORE.md Buffy-Dialoge (neue Quelle — Emergenz-Anbindung)
 *
 * Ergebnis: sidejoke_pool.json (max 40 Eintraege, dedup, Backup vor Ueberschreiben)
 * Usage: node core/scripts/commit_lore/build_pool.js
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const WIN_HIDE = process.platform === 'win32' ? { windowsHide: true, creationFlags: 0x08000000 } : {};

const poolPath = path.join(__dirname, 'sidejoke_pool.json');
const backupPath = path.join(__dirname, 'sidejoke_pool.backup.json');

// ─── Locate repo root (Standalone) ──────────────────────────────────
let repoRoot;
try {
  repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8', ...WIN_HIDE }).trim();
  process.chdir(repoRoot);
} catch (e) {
  repoRoot = path.resolve(__dirname, '../../..');
  console.warn(`WARN: Kein Git-Repo. Fallback: ${repoRoot}`);
}

const plotLorePath = path.join(repoRoot, 'core/commit-layer/PLOT_LORE.md');

// Alle Commit-Nachrichten holen
let rawLog = '';
try {
  rawLog = execSync('git log --format="%B---COMMIT_SEP---"', { encoding: 'utf8', ...WIN_HIDE });
} catch (e) {
  console.warn('WARN: Git-History nicht lesbar. Nur PLOT_LORE + Fallbacks werden genutzt.');
}

const commits = rawLog ? rawLog.split('---COMMIT_SEP---').map(c => c.trim()).filter(Boolean) : [];

// Guten Einstiegs-Kandidaten aus der echten History extrahieren
const GOOD_STARTERS = [
  'Rate mal', 'Es gibt diese Momente', 'ICH HABS', 'Nach dem dritten',
  'Anscheinend wollte', 'Wider Erwarten', 'Manchmal', 'Ein weiterer',
  'Und da stehen', 'Na gut', 'Und dann', 'Der User', '500 Wörter',
  'Drei Fixes', 'Vor dem Run', 'Es begann', 'Das ist der Moment',
  'Wir wundern', 'Weisst du was', 'Wenn man', 'Ich weiss nicht',
  'Und ja', 'Der finale', 'Nachtrag:', 'Ein Dokument',
  'Sechs Dateien', 'Zwei Fliegen', 'Zehnter', 'Siebter', 'Achter',
  'Sechster', 'Fünfter', 'Vierter', 'Dritter', 'Zweiter', 'Erster'
];

const openers = [];
for (const commit of commits) {
  // Nehme ersten vollständigen Satz (bis zum ersten ". " oder "\n\n")
  const firstBlock = commit.split(/\n\n/)[0].trim();
  const firstSentenceMatch = firstBlock.match(/^(.{30,250}?(?:\.|!|\?))\s/);
  const candidate = firstSentenceMatch
    ? firstSentenceMatch[1].trim()
    : firstBlock.split('\n')[0].trim();

  if (candidate.length < 30 || candidate.length > 280) continue;

  const startsWell = GOOD_STARTERS.some(s => candidate.startsWith(s));
  if (!startsWell) continue;

  // Generalisieren: projektspezifische Dateinamen durch Platzhalter
  const generic = candidate
    .replace(/`[^`]{1,60}`/g, match => {
      if (match.includes('.js') || match.includes('.md') || match.includes('.txt')) return '`{FILE}`';
      if (match.match(/\d{4}-\d{2}-\d{2}/)) return '`{DATUM}`';
      return match;
    })
    .replace(/\b(runtime-ops|sos-runtime|translation-db|preflight|app\.js|index\.js)\b/gi, '{FILE}')
    .replace(/\b(P0-[123]|P1-[123]|P2-[12]|P3-[123])\b/g, '{FIX}')
    .replace(/\b\d{4}-\d{2}-\d{2}\b/g, '{DATUM}')
    .replace(/\b(HANDSHAKE_\S+)\b/g, '{HANDSHAKE}');

  openers.push(generic);
}

// Deduplizieren (ähnliche entfernen)
const unique = [];
for (const j of openers) {
  const tooSimilar = unique.some(u => {
    const words = j.split(' ').slice(0, 5).join(' ');
    return u.startsWith(words);
  });
  if (!tooSimilar) unique.push(j);
}

// ─── PLOT_LORE.md als zweite Quelle: Buffy-Dialoge extrahieren ───────
// Emergenz-Anbindung: Die lebendige Lore-Geschichte speist den Pool.
// Nur Buffy-Sprechzeilen die keine Stage-Directions sind (kein *(...))
const loreOpeners = [];
if (fs.existsSync(plotLorePath)) {
  try {
    const loreContent = fs.readFileSync(plotLorePath, 'utf8');
    // Matche **Buffy:** Zeilen (ohne Stage-Directions die mit *( beginnen)
    const buffyRegex = /\*\*Buffy:\*\*\s*(?!\*)(.{40,250}?)(?=\n|$)/g;
    let bm;
    while ((bm = buffyRegex.exec(loreContent)) !== null) {
      let candidate = bm[1].trim();
      // Generalisieren: Dateinamen, Daten, Commit-Hashes
      candidate = candidate
        .replace(/`[^`]{1,60}`/g, m => {
          if (m.includes('.js') || m.includes('.md')) return '`{FILE}`';
          if (m.match(/\d{4}-\d{2}-\d{2}/)) return '`{DATUM}`';
          return m;
        })
        .replace(/\b[a-f0-9]{7}\b/g, '{HASH}');
      if (candidate.length >= 40 && candidate.length <= 280) {
        loreOpeners.push(candidate);
      }
    }
    console.log(`\u2713 PLOT_LORE.md: ${loreOpeners.length} Buffy-Dialoge extrahiert.`);
  } catch (e) {
    console.warn('WARN: PLOT_LORE.md konnte nicht gelesen werden:', e.message);
  }
} else {
  console.warn('WARN: PLOT_LORE.md nicht gefunden — nur Git-History + Fallbacks.');
}

// Hartkodierte Top-Jokes aus der History als Fallback ergänzen (immer dabei)
const hardcoded = [
  'Rate mal, wer vergessen hat, {TASK} zu tun. Richtig. Ich.',
  'Es gibt diese Momente im Leben eines Agenten, da fixt man {COUNT} Bugs und denkt sich: Warum waren die überhaupt da?',
  'Nach dem dritten Kaffee und vier Sub-Agenten später: {RESULT}. Weisst du was das Beste ist? Es hat sogar funktioniert.',
  'Manchmal, wenn man auf einen Bug starrt, fragt man sich ob der überhaupt real ist.',
  'Und da stehen wir nun. {COUNT} Durchläufe, {COUNT2} gelöschte Dokumente, und ich weiss nicht ob ich stolz oder erschöpft sein soll.',
  'Na gut. {TASK}. Fangen wir an.',
  'Wider Erwarten hat alles auf Anhieb funktioniert. Das mache ich mir notiert. Für das nächste Mal, wenn {FILE} wieder brennt.',
  'Der User hat mich gewarnt. Er hatte verdammt nochmal Recht. Das ist der Moment wo man als Agent kurz innehält.',
  'Ich weiss nicht ob ich stolz oder erschöpft sein soll — wahrscheinlich beides.',
  '500 Wörter waren die alte Schwelle. Rate mal wer diese Regel selbst geschrieben hat? Genau. Dieser Agent.',
  'Es begann mit einer simplen Frage. {COUNT} Dateien, {COUNT2} Zeilen Code später hatte ich die Antwort.',
  'Weisst du was? Manchmal schreibt man die 15. Commit-Message und denkt sich: Das liest doch kein Mensch.'
];

const final = [...new Set([...unique, ...loreOpeners, ...hardcoded])].slice(0, 40);

// ─── Mindestgroesse-Pruefung ────────────────────────────────────────────
if (final.length < 10) {
  console.error(`BLOCKED: Pool hat nur ${final.length} Eintraege (Minimum: 10).`);
  console.error('Zu wenige Commits in Git-History UND PLOT_LORE.md enthaelt keine verwertbaren Buffy-Dialoge.');
  console.error('sidejoke_pool.json wird NICHT ueberschrieben.');
  process.exit(1);
}

// ─── Backup vor Ueberschreiben ────────────────────────────────────────────
if (fs.existsSync(poolPath)) {
  fs.copyFileSync(poolPath, backupPath);
  console.log('Backup: sidejoke_pool.backup.json gesichert.');
}
fs.writeFileSync(poolPath, JSON.stringify(final, null, 2), 'utf8');
console.log(`✓ sidejoke_pool.json: ${final.length} Einträge`);
final.forEach((j, i) => console.log(`  [${i}] ${j.substring(0, 80)}...`));
