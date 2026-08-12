#!/usr/bin/env node
/**
 * annotate_plot_lore.js — PLOT_LORE.md Composite-Annotation (v0.23a)
 * 
 * Liest plotchain.json → baut p_id→composite Map.
 * Durchsucht PLOT_LORE.md nach [p{N}]-Tags und annotiert:
 *   [p18] → [p18][COMPOSITE:c1j94a5p12]  (wenn Composite existiert)
 *   [p1]  → [p1][pre-composite]          (wenn kein Composite)
 * 
 * Idempotent: Bereits annotierte Einträge werden nicht doppelt annotiert.
 * 
 * USAGE:
 *   node annotate_plot_lore.js
 *   node annotate_plot_lore.js --dry-run
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const WIN_HIDE = process.platform === 'win32' ? { windowsHide: true, creationFlags: 0x08000000 } : {};

// ─── Repo-Root finden ──────────────────────────────────────────────
let repoRoot;
try {
  repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8', ...WIN_HIDE }).trim();
  process.chdir(repoRoot);
} catch (e) {
  repoRoot = path.resolve(__dirname, '../../..');
  console.warn(`WARN: Kein Git-Repo. Fallback: ${repoRoot}`);
}

const plotchainPath = path.join(__dirname, 'plotchain.json');
const plotLorePath = path.join(repoRoot, 'core/commit-layer/PLOT_LORE.md');

const dryRun = process.argv.includes('--dry-run');

// ─── 1. Plotchain laden → p_id→composite Map ──────────────────────
if (!fs.existsSync(plotchainPath)) {
  console.error('FEHLER: plotchain.json nicht gefunden.');
  process.exit(1);
}

const plotchain = JSON.parse(fs.readFileSync(plotchainPath, 'utf8'));
const compositeMap = {};       // p_id → composite string
const compositeSet = new Set(); // alle composites, dedupliziert

for (const node of plotchain) {
  if (node.composite) {
    compositeMap[node.p_id] = node.composite;
    compositeSet.add(node.composite);
  }
}

console.log(`Plotchain geladen: ${plotchain.length} Nodes, ${Object.keys(compositeMap).length} mit Composite.`);
console.log(`Composites: ${[...compositeSet].join(', ') || '(keine)'}`);

// ─── 2. PLOT_LORE.md laden ────────────────────────────────────────
if (!fs.existsSync(plotLorePath)) {
  console.error('FEHLER: PLOT_LORE.md nicht gefunden.');
  process.exit(1);
}

const original = fs.readFileSync(plotLorePath, 'utf8');
const lines = original.split('\n');

// ─── 3. Annotieren ─────────────────────────────────────────────────
// Nur ###-Header annotieren: "### [...] [pN]" oder "### [...] [pN] am Ende"
// Bereits annotierte Header werden übersprungen.
// Nur Nodes mit echtem Composite werden annotiert — kein [pre-composite]-Noise.

const headerRegex = /^(###\s+\[.+?\]\s*.*?)(\[p(\d+)\])\s*$/;
const alreadyAnnotatedRegex = /\[p\d+\]\[(?:COMPOSITE:|pre-composite)/;

let changes = 0;
let skipped = 0;
let noComposite = 0;

const annotated = lines.map((line) => {
  // Nur ###-Header
  if (!line.startsWith('### ')) return line;
  
  // Bereits annotiert → überspringen
  if (alreadyAnnotatedRegex.test(line)) {
    skipped++;
    return line;
  }
  
  // Header-Match: ### [...] ...[pN]
  const match = line.match(headerRegex);
  if (!match) return line;
  
  const pNum = match[3];
  const pId = `p${pNum}`;
  const composite = compositeMap[pId];
  
  if (!composite) {
    noComposite++;
    return line; // Kein Composite → unverändert lassen
  }
  
  changes++;
  return `${match[1]}${match[2]}[COMPOSITE:${composite}]`;
});

// ─── 4. Ausgabe ────────────────────────────────────────────────────
const result = annotated.join('\n');

console.log(`\nAnnotationen: ${changes} Header annotiert, ${noComposite} ohne Composite (belassen), ${skipped} bereits annotiert (übersprungen).`);

if (dryRun) {
  console.log('\n--- DRY RUN (keine Änderungen geschrieben) ---');
  // Zeige erste 5 geänderte Zeilen
  let shown = 0;
  for (let i = 0; i < lines.length && shown < 5; i++) {
    if (lines[i] !== annotated[i]) {
      console.log(`\nZeile ${i + 1}:`);
      console.log(`  ALT: ${lines[i].substring(0, 120)}`);
      console.log(`  NEU: ${annotated[i].substring(0, 120)}`);
      shown++;
    }
  }
  console.log('\nFühre ohne --dry-run aus um zu schreiben.');
} else {
  fs.writeFileSync(plotLorePath, result, 'utf8');
  console.log('PLOT_LORE.md geschrieben.');
}

// ─── 5. Statistik ──────────────────────────────────────────────────
const compositeCount = (result.match(/\[COMPOSITE:c\d+j\d+a\d+p\d+\]/g) || []).length;
console.log('\nStatistik:');
console.log(`  [COMPOSITE:...] : ${compositeCount}`);
console.log(`  Ohne Composite   : ${noComposite} (nur p18/p19 haben Composites)`);
