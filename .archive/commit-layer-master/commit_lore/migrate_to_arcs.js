#!/usr/bin/env node
'use strict';
const fs = require('fs');
const path = require('path');

const { findRepoRoot, getCommitLorePaths, loadJSON, saveJSON } = require('./utils');

const repoRoot = findRepoRoot();
const paths = getCommitLorePaths(repoRoot);
const LORE_DIR = path.dirname(paths.plotchain);
const ARCS_DIR = path.join(LORE_DIR, 'arcs');

// First, move existing PLOTCHAIN_FREEZE to archive
const oldFreezeFile = path.join(LORE_DIR, 'PLOTCHAIN_FREEZE_p1_to_p153.json');
if (fs.existsSync(oldFreezeFile)) {
  console.log('Moving old PLOTCHAIN_FREEZE to arcs/a1/frozen_plotchain.json');
  const a1Dir = path.join(ARCS_DIR, 'a1');
  if (!fs.existsSync(a1Dir)) fs.mkdirSync(a1Dir, { recursive: true });
  fs.copyFileSync(oldFreezeFile, path.join(a1Dir, 'frozen_plotchain.json'));
}

// Now update lore_arcs.json with p ranges
const loreArcs = loadJSON(paths.loreArcs, { description: '', active: '', arcs: {} });
const arcs = loreArcs.arcs;

// Assign approximate p ranges based on v0.20, etc.
if (arcs.a1) {
  arcs.a1.first_p = 'p1';
  arcs.a1.last_p = 'p153';
  arcs.a1.status = 'archived';
}
if (arcs.a2) {
  arcs.a2.first_p = 'p154';
  arcs.a2.last_p = 'p154';
  arcs.a2.status = 'archived';
}
if (arcs.a3) {
  arcs.a3.first_p = 'p155';
  arcs.a3.last_p = 'p159';
  arcs.a3.status = 'archived';
}
if (arcs.a4) {
  arcs.a4.first_p = 'p160';
  arcs.a4.last_p = 'p173';
  arcs.a4.status = 'archived';
}
if (arcs.a5) {
  arcs.a5.first_p = 'p174';
  arcs.a5.last_p = null; // current arc
  arcs.a5.status = 'active';
}

saveJSON(paths.loreArcs, loreArcs);
console.log('Updated lore_arcs.json with p ranges!');

console.log('Migration complete!');
