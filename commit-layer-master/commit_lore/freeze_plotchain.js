#!/usr/bin/env node
/**
 * freeze_plotchain.js — Plotchain Freeze Mechanismus
 *
 * Analog zu CHANGELOG_FREEZE: Archiviert alte plotchain-Nodes in eine
 * komprimierte Freeze-Datei, um die Ladezeit von plotchain.json zu schützen.
 *
 * Archivierte Nodes verlieren: recent_commits, data_changes, causal_chain_summary
 * Archivierte Nodes behalten: p_id, id, timestamp, summary, narrator, model_id, composite, ref_to, prev_narrator, prev_model
 *
 * USAGE:
 *   node core/commit-layer/commit_lore/freeze_plotchain.js [--keep=20] [--dry-run]
 *
 * Auto-Trigger: Wird von author_system.js aufgerufen wenn Nodes > KEEP_THRESHOLD.
 */

'use strict';
const fs = require('fs');

const {
  findRepoRoot,
  getCommitLorePaths,
  getArcPaths,
  findArcForPid,
  loadJSON,
  saveJSON
} = require('./utils');

const KEEP_THRESHOLD = 20;   // Letzte N Nodes bleiben in plotchain.json
const ARCHIVE_FIELDS = [     // Felder die im Archiv entfernt werden
  'recent_commits',
  'data_changes',
  'causal_chain_summary',
  'data_changes_legacy'   // Vor-v0.22 Legacy-Feld, in aelteren Nodes noch vorhanden — defensiv strippen
];

// Kern-Felder die im Frozen erhaeltlich bleiben (Single-Source-of-Truth fuer Schema-Tests).
// ARCHIVE_FIELDS ∩ CORE_FIELDS = Ø per Design.
const CORE_FIELDS = [
  'p_id',
  'id',
  'timestamp',
  'summary',
  'narrator',
  'model_id',
  'composite',
  'ref_to',
  'prev_narrator'
];

/**
 * Komprimiert einen Plotchain-Node für das Archiv.
 * Entfernt Bulk-Felder, behält Chain-Struktur.
 */
function _compressNode(node) {
  const compressed = {};
  for (const [key, value] of Object.entries(node)) {
    if (!ARCHIVE_FIELDS.includes(key)) {
      compressed[key] = value;
    }
  }
  return compressed;
}

/**
 * Führt den Freeze durch.
 * @param {number} keepCount - Anzahl der Nodes die in plotchain.json bleiben
 * @param {boolean} dryRun - Nur anzeigen, nicht schreiben
 * @returns {{ archived: number, kept: number, freezeFile: string|null }}
 */
function freezePlotchain(keepCount = KEEP_THRESHOLD, dryRun = false) {
  const repoRoot = findRepoRoot();
  const paths    = getCommitLorePaths(repoRoot);
  const pcPath   = paths.plotchain;
  const loreArcs = loadJSON(paths.loreArcs, { active: '', arcs: {} });

  if (!fs.existsSync(pcPath)) {
    console.log('❄️  Plotchain: Keine Datei gefunden — kein Freeze nötig.');
    return { archived: 0, kept: 0, freezeFile: null };
  }

  const plotchain = loadJSON(pcPath, []);
  if (!Array.isArray(plotchain) || plotchain.length <= keepCount) {
    console.log(`❄️  Plotchain: ${plotchain.length} Nodes (≤ ${keepCount}) — kein Freeze nötig.`);
    return { archived: 0, kept: plotchain.length, freezeFile: null };
  }

  const archiveCount = plotchain.length - keepCount;
  const toArchive    = plotchain.slice(0, archiveCount);
  const toKeep       = plotchain.slice(archiveCount);

  // Group nodes by arc
  const groupedByArc = {};
  for (const node of toArchive) {
    const arcId = findArcForPid(loreArcs, node.p_id);
    if (!groupedByArc[arcId]) {
      groupedByArc[arcId] = [];
    }
    groupedByArc[arcId].push(_compressNode(node));
  }

  if (dryRun) {
    const firstPId = toArchive[0].p_id || 'p1';
    const lastPId = toArchive[toArchive.length - 1].p_id || `p${archiveCount}`;
    console.log(`❄️  [DRY-RUN] Würde ${archiveCount} Nodes archivieren (${firstPId}–${lastPId}).`);
    console.log(`   Gruppen nach Arcs: ${Object.keys(groupedByArc).join(', ')}.`);
    const origSize = JSON.stringify(plotchain).length;
    const newSize  = JSON.stringify(toKeep).length;
    const archSize = JSON.stringify(toArchive.map(_compressNode)).length;
    console.log(`   Größe: ${(origSize/1024).toFixed(1)}KB → ${(newSize/1024).toFixed(1)}KB aktiv + ${(archSize/1024).toFixed(1)}KB archiviert.`);
    return { archived: archiveCount, kept: toKeep.length, freezeFile: null };
  }

  // Write each group to its arc
  for (const [arcId, nodes] of Object.entries(groupedByArc)) {
    const arcPaths = getArcPaths(repoRoot, arcId);
    if (!fs.existsSync(arcPaths.arcDir)) {
      fs.mkdirSync(arcPaths.arcDir, { recursive: true });
    }
    let existing = [];
    if (fs.existsSync(arcPaths.frozenPlotchain)) {
      existing = loadJSON(arcPaths.frozenPlotchain, []);
    }
    const merged = existing.concat(nodes);
    saveJSON(arcPaths.frozenPlotchain, merged);
    console.log(`❄️  Freeze: ${nodes.length} Nodes added to arc ${arcId} → frozen_plotchain.json (total ${merged.length}).`);
  }

  // Update active plotchain
  saveJSON(pcPath, toKeep);
  console.log(`❄️  Plotchain: ${toKeep.length} Nodes verbleibend (von ${plotchain.length}).`);

  return { archived: archiveCount, kept: toKeep.length, freezeFile: null };
}

// ── CLI Entry Point ───────────────────────────────────────────────────
if (require.main === module) {
  const args = process.argv.slice(2);
  let keep = KEEP_THRESHOLD;
  let dryRun = false;

  for (const arg of args) {
    if (arg.startsWith('--keep='))  keep   = parseInt(arg.slice(7), 10) || KEEP_THRESHOLD;
    if (arg === '--dry-run')        dryRun = true;
  }

  freezePlotchain(keep, dryRun);
}

module.exports = { freezePlotchain, KEEP_THRESHOLD, ARCHIVE_FIELDS, CORE_FIELDS, compressNode: _compressNode };

