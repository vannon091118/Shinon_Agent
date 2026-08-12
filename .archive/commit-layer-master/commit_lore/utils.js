
/**
 * commit_lore/utils.js — Shared utilities for commit-layer scripts
 *
 * Eliminates redundant code across author_system.js, derive_composite.js, update_plot.js
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const WIN_HIDE = process.platform === 'win32' ? { windowsHide: true, creationFlags: 0x08000000 } : {};

// --- 1. Repo Root Helpers ---
function findRepoRoot() {
  try {
    return execSync('git rev-parse --show-toplevel', { encoding: 'utf8', ...WIN_HIDE }).trim();
  } catch (e) {
    const fallback = path.resolve(__dirname, '../../..');
    console.warn(`WARN: Kein Git-Repo. Fallback: ${fallback}`);
    return fallback;
  }
}

// --- 2. Path Constants ---
function getCommitLorePaths(repoRoot) {
  const LORE_DIR = path.join(repoRoot, 'core/commit-layer/commit_lore');
  return {
    plotchain: path.join(LORE_DIR, 'plotchain.json'),
    charSheets: path.join(LORE_DIR, 'character_sheets.json'),
    narrativeParams: path.join(LORE_DIR, 'narrative_params.json'),
    compositeChain: path.join(LORE_DIR, 'composite_chain.json'),
    sidejokes: path.join(LORE_DIR, 'sidejoke_pool.json'),
    loreArcs: path.join(LORE_DIR, 'lore_arcs.json'),
    crossRefs: path.join(LORE_DIR, 'cross_references.json'),
    plotLore: path.join(repoRoot, 'core/commit-layer/PLOT_LORE.md'),
    changelog: path.join(repoRoot, 'CHANGELOG.md'),
    commitMsg: path.join(repoRoot, 'core/.commit_msg.txt'),
    accessLog: path.join(LORE_DIR, 'author_system.log'),
    arcsDir: path.join(LORE_DIR, 'arcs')
  };
}

// --- Arc Helpers ---
function getArcPaths(repoRoot, arcId) {
  const paths = getCommitLorePaths(repoRoot);
  const arcDir = path.join(paths.arcsDir, arcId);
  return {
    arcDir,
    plotSnippet: path.join(arcDir, 'plot_snippet.md'),
    frozenPlotchain: path.join(arcDir, 'frozen_plotchain.json'),
    meta: path.join(arcDir, 'meta.json')
  };
}

// Helper to find which arc a p_id belongs to
function findArcForPid(loreArcs, pId) {
  if (!loreArcs?.arcs) return null;
  const pNum = parseInt(String(pId).replace('p', ''), 10);
  
  for (const [arcId, arc] of Object.entries(loreArcs.arcs)) {
    if (!arc.first_p) continue;
    
    const firstP = parseInt(String(arc.first_p).replace('p', ''), 10);
    let lastP = null;
    if (arc.last_p) {
      lastP = parseInt(String(arc.last_p).replace('p', ''), 10);
    }
    
    if (pNum >= firstP) {
      if (!lastP || pNum <= lastP) {
        return arcId;
      }
    }
  }
  return loreArcs.active || null;
}

// --- 3. Safe JSON Loaders ---
function loadJSON(pathToFile, fallback = null) {
  if (!fs.existsSync(pathToFile)) return fallback;
  try {
    return JSON.parse(fs.readFileSync(pathToFile, 'utf8'));
  } catch (e) {
    console.warn(`WARN: ${path.basename(pathToFile)} nicht lesbar (${e.message}).`);
    return fallback;
  }
}

function saveJSON(pathToFile, data) {
  fs.writeFileSync(pathToFile, JSON.stringify(data, null, 2), 'utf8');
}

// --- 4. Commit & Git Helpers ---
function getShortHeadHash() {
  return execSync('git rev-parse --short HEAD', { encoding: 'utf8', ...WIN_HIDE }).trim();
}

function getStagedFiles() {
  try {
    return execSync('git diff --cached --name-only', { encoding: 'utf8', ...WIN_HIDE })
      .trim().split('\n').filter(Boolean);
  } catch (_) {
    return [];
  }
}

function getRecentCommits(count = 5) {
  const commits = [];
  try {
    const logOutput = execSync(
      `git log -${count} --format="%h|||%s|||%ai|||%an" --no-merges`,
      { encoding: 'utf8', ...WIN_HIDE }
    ).trim();
    for (const line of logOutput.split('\n').filter(Boolean)) {
      const [hash, subject, date, author] = line.split('|||');
      if (!hash || !subject) continue;
      let files = [];
      try {
        files = execSync(`git diff-tree --no-commit-id --name-only -r ${hash}`, { encoding: 'utf8', ...WIN_HIDE })
          .trim().split('\n').filter(Boolean);
      } catch (_) { /* ignore */ }
      commits.push({
        hash: hash.trim(),
        subject: subject.trim().substring(0, 120),
        date: (date || '').trim(),
        author: (author || '').trim(),
        files_touched: files.slice(0, 15)
      });
    }
  } catch (_) { /* ignore */ }
  return commits;
}

function getDiffStats() {
  const stats = [];
  const tryCmd = (cmd) => {
    try {
      return execSync(cmd, { encoding: 'utf8', ...WIN_HIDE }).trim();
    } catch (_) { return null; }
  };
  let diffStat = tryCmd('git diff --cached --numstat');
  if (!diffStat) diffStat = tryCmd('git diff --numstat');
  if (diffStat) {
    for (const line of diffStat.split('\n').filter(Boolean)) {
      const [ins, del, file] = line.split('\t');
      if (file) {
        stats.push({
          file,
          insertions: ins === '-' ? 0 : parseInt(ins, 10) || 0,
          deletions: del === '-' ? 0 : parseInt(del, 10) || 0
        });
      }
    }
  }
  return stats;
}

// --- 5. Narrator & Attitude Helpers ---
function selectNarrator(characterSheets, nVal) {
  if (!characterSheets || !characterSheets.characters) return null;
  const nKey = String(nVal);
  return characterSheets.characters[nKey] || null;
}

function calculateFinalAttitudes(baseAttitudes, moodMods) {
  const final = {};
  if (!baseAttitudes) return final;
  for (const [key, val] of Object.entries(baseAttitudes)) {
    const mod = moodMods?.[key] || 0;
    final[key] = Math.max(0, Math.min(10, val + mod));
  }
  return final;
}

// --- 6. Arc & Plot Count Helpers ---
function getCounts(loreArcs, plotchain) {
  const arcCount = (loreArcs && loreArcs.arcs) ? Object.keys(loreArcs.arcs).length : 1;
  const plotCount = Array.isArray(plotchain) ? plotchain.length : 1;
  return { arcCount, plotCount };
}

// --- 7. Composite Chain Helpers ---
function getPrevComposite(compositeChain) {
  const entries = compositeChain?.chain || [];
  if (entries.length > 0) {
    return {
      composite: entries[entries.length - 1].composite || compositeChain.genesis_composite || 'c0j0n0a0p0',
      mood: entries[entries.length - 1].mood || compositeChain.genesis_mood || 'genesis',
      seq: entries[entries.length - 1].seq || entries.length
    };
  }
  return {
    composite: compositeChain?.genesis_composite || 'c0j0n0a0p0',
    mood: compositeChain?.genesis_mood || 'genesis',
    seq: 0
  };
}

// --- 8. Plotchain Helpers ---
function getPrevNarratorFromPlotchain(plotchain, currentNarratorName = null) {
  for (let i = plotchain.length - 1; i >= 0; i--) {
    const node = plotchain[i];
    if (node.narrator && (!currentNarratorName || node.narrator !== currentNarratorName)) {
      return { name: node.narrator, model: node.model_id };
    }
  }
  return null;
}

// --- 9. Quality Control Helpers ---
function validateCommitInput(options) {
  const errors = [];
  if (!options.impulse || options.impulse.trim().length === 0) errors.push('Missing or empty impulse');
  if (!options.model || options.model.trim().length === 0) errors.push('Missing or empty model');
  if (!options.bodyFile) errors.push('Missing bodyFile path');
  return errors;
}

function checkConsistency(compositeChain, plotchain) {
  const issues = [];
  if (compositeChain?.chain?.length > 0 && plotchain?.length > 0) {
    const lastComposite = compositeChain.chain[compositeChain.chain.length -1];
    const lastPlot = plotchain[plotchain.length -1];
    if (lastComposite.composite !== lastPlot.composite) {
      issues.push(`Composite mismatch: chain has ${lastComposite.composite}, plot has ${lastPlot.composite}`);
    }
    if (lastComposite.narrator !== lastPlot.narrator) {
      issues.push(`Narrator mismatch: chain has ${lastComposite.narrator}, plot has ${lastPlot.narrator}`);
    }
    if (lastComposite.model_id !== lastPlot.model_id) {
      issues.push(`Model mismatch: chain has ${lastComposite.model_id}, plot has ${lastPlot.model_id}`);
    }
  }
  return issues;
}

function logAccess(action, details) {
  const timestamp = new Date().toISOString();
  const logLine = `[${timestamp}] ${action}: ${JSON.stringify(details)}\n`;
  const logPath = getCommitLorePaths(findRepoRoot()).accessLog;
  try {
    fs.appendFileSync(logPath, logLine, 'utf8');
  } catch (e) {
    console.warn(`WARN: Could not write to access log: ${e.message}`);
  }
}

function sanitizePath(filePath) {
  return filePath.replace(/[^\w\-.\\/:]/g, '');
}

module.exports = {
  findRepoRoot,
  getCommitLorePaths,
  getArcPaths,
  findArcForPid,
  loadJSON,
  saveJSON,
  getShortHeadHash,
  getStagedFiles,
  getRecentCommits,
  getDiffStats,
  selectNarrator,
  calculateFinalAttitudes,
  getCounts,
  getPrevComposite,
  getPrevNarratorFromPlotchain,
  validateCommitInput,
  checkConsistency,
  logAccess,
  sanitizePath
};
