#!/usr/bin/env node
/**
 * author_system.js — Unified Narrative Commit Layer (v0.26.0)
 *
 * Das Autoren-System. Ein Aufruf ersetzt den gesamten manuellen Workflow.
 * Technisch korrekt: Composite-Derivation, Narrator aus Chain, CHANGELOG-Sync, Cross-Narrator, AUTOMATIC PLOT_LORE INTEGRATION!
 *
 * USAGE:
 *   node core/commit-layer/author_system.js \
 *     --impulse="Was wurde gemacht" \
 *     --model="mimo-v2" \
 *     --bodyfile="core/.body_text.txt" \
 *     [--narrator=Buffy]  (optional, sonst deterministisch aus Hash)
 *     [--category=HOTFIX]
 *     [--lore="Zusätzlicher Plot-Lore-Text (optional)]
 */

'use strict';
const fs   = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const WIN_HIDE = process.platform === 'win32' ? { windowsHide: true, creationFlags: 0x08000000 } : {};

// Import our new utils module
const {
  findRepoRoot,
  getCommitLorePaths,
  loadJSON,
  saveJSON,
  getShortHeadHash,
  getStagedFiles,
  getRecentCommits,
  getDiffStats,
  _selectNarrator,
  calculateFinalAttitudes,
  getCounts,
  getPrevComposite,
  getPrevNarratorFromPlotchain,
  validateCommitInput,
  checkConsistency,
  logAccess
} = require('./commit_lore/utils');

const { generateStory } = require('./commit_lore/story_generator');
const { freezePlotchain, KEEP_THRESHOLD } = require('./commit_lore/freeze_plotchain');
const TemplateEngine = require('./commit_lore/template_engine');

// Import RNG module
const LORE_DIR = path.join(__dirname, 'commit_lore');  const { derive, _decodeJ, parseComposite, XorShift128, djb2 } = require(path.join(LORE_DIR, 'rng'));

// ── Causal Signals Calculation Functions ─────────────────────────────────

function detectDomainsFromFiles(stagedFiles) {
  const domains = new Set();
  
  stagedFiles.forEach(file => {
    const path = file.toLowerCase();
    if (path.includes('gui') || path.includes('public') || path.includes('css') || path.includes('html')) {
      domains.add('GUI');
    }
    if (path.includes('db') || path.includes('database') || path.includes('sql')) {
      domains.add('DB');
    }
    if (path.includes('translation') || path.includes('lang') || path.includes('i18n')) {
      domains.add('Translation');
    }
    if (path.includes('architecture') || path.includes('core') || path.includes('utils')) {
      domains.add('Architecture');
    }
    if (path.includes('test') || path.includes('spec')) {
      domains.add('Testing');
    }
    if (path.includes('commit') || path.includes('lore')) {
      domains.add('CommitLayer');
    }
  });
  
  if (domains.size === 0) domains.add('General');
  
  return Array.from(domains);
}

function calculateRelationshipState(prevNarrator, currentNarrator, plotchain) {
  if (!prevNarrator) return 'fresh_pair';
  
  // Count co-occurrences in recent plotchain
  const recentCommits = plotchain.slice(-20);
  let coOccurrenceCount = 0;
  
  recentCommits.forEach(commit => {
    if (commit.narrator === prevNarrator && commit.prev_narrator === currentNarrator) {
      coOccurrenceCount++;
    }
    if (commit.narrator === currentNarrator && commit.prev_narrator === prevNarrator) {
      coOccurrenceCount++;
    }
  });
  
  if (coOccurrenceCount >= 5) return 'trusted_team';
  if (coOccurrenceCount >= 2) return 'established_duo';
  return 'fresh_pair';
}

function calculateDomainResonance(narrator, domains) {
  // Simple domain affinity mapping (could be enhanced with learning)
  const domainAffinity = {
    'Basher': { 'GUI': 0.9, 'DB': 0.3, 'Translation': 0.2 },
    'Buffy': { 'GUI': 0.7, 'Architecture': 0.9, 'DB': 0.5 },
    'Devin': { 'Architecture': 0.9, 'GUI': 0.6, 'DB': 0.4 },
    'Thinker': { 'Architecture': 0.8, 'DB': 0.7, 'Translation': 0.5 },
    'Vannon': { 'Architecture': 0.7, 'GUI': 0.5, 'All': 0.9 },
    'Squizzle': { 'DB': 0.8, 'GUI': 0.6, 'Translation': 0.4 },
    'Ghost': { 'All': 0.7 },
    'Glitch': { 'All': 0.5 },
    'Spark': { 'All': 0.6 },
    'Null': { 'All': 0.3 },
    'Echo': { 'All': 0.6 },
    'Flux': { 'All': 0.4 },
    'Sage': { 'All': 0.7 },
    'Argos': { 'GUI': 0.8, 'DB': 0.7, 'Translation': 0.6 }
  };
  
  const primaryDomain = domains[0] || 'Unknown';
  const affinity = domainAffinity[narrator]?.[primaryDomain] || 0.5;
  
  if (affinity >= 0.8) return 'native_domain';
  if (affinity >= 0.5) return 'cross_domain_expert';
  return 'foreign_domain';
}

function calculateSequencePhase(plotchain) {
  const recentCommits = plotchain.slice(-10);
  const moodChanges = recentCommits.filter(c => c.mood).map(c => c.mood);
  
  // Simple heuristic: if same mood repeats → arc_mid, else arc_opening
  if (moodChanges.length < 3) return 'arc_opening';
  
  const uniqueMoods = new Set(moodChanges);
  if (uniqueMoods.size === 1) return 'arc_climax';
  if (uniqueMoods.size <= 2) return 'arc_mid';
  return 'arc_resolution';
}

function detectCurrentTheme(plotchain) {
  const recentCommits = plotchain.slice(-10);
  const summaries = recentCommits.map(c => c.summary || '').join(' ').toLowerCase();
  
  if (summaries.includes('bug') || summaries.includes('fix')) return 'bug_hunt';
  if (summaries.includes('cleanup') || summaries.includes('refactor')) return 'cleanup_fatigue';
  if (summaries.includes('architecture') || summaries.includes('pattern')) return 'architecture_triumph';
  if (summaries.includes('feature') || summaries.includes('new')) return 'feature_development';
  return 'general';
}

function calculateArcProgress(plotchain) {
  // Simple heuristic: 0-100% based on recent commit density
  const recentCommits = plotchain.slice(-20);
  if (recentCommits.length < 5) return 20;
  if (recentCommits.length < 10) return 50;
  if (recentCommits.length < 15) return 80;
  return 95;
}

function classifyCodeChange(commitMessage, stagedFiles) {
  const msg = (commitMessage || '').toLowerCase();
  const files = stagedFiles.join(' ').toLowerCase();
  
  if (msg.includes('fix') || msg.includes('bug') || msg.includes('hotfix')) return 'bugfix';
  if (msg.includes('refactor') || msg.includes('cleanup') || msg.includes('rework')) return 'refactor';
  if (msg.includes('doc') || msg.includes('readme') || files.includes('.md')) return 'docs';
  return 'feature';
}

function calculateComplexity(diffStats) {
  const locDelta = (diffStats.insertions || 0) + (diffStats.deletions || 0);
  
  if (locDelta < 50) return 'low';
  if (locDelta < 200) return 'medium';
  return 'high';
}

function generateTechnicalSummary(diffStats, stagedFiles) {
  const fileCount = stagedFiles.length;
  const locDelta = (diffStats.insertions || 0) + (diffStats.deletions || 0);
  
  if (fileCount === 1) return `Änderung an ${stagedFiles[0]}`;
  if (fileCount <= 3) return `Änderungen an ${fileCount} Dateien`;
  return `Große Änderung: ${fileCount} Dateien, ${locDelta} LOC`;
}

// ── Main Workflow ───────────────────────────────────────────────────────────

(async () => {
  // ─── Repo Root & Paths ─────────────────────────────────────────────────────────
  const REPO_ROOT = findRepoRoot();
  process.chdir(REPO_ROOT);
  const PATHS = getCommitLorePaths(REPO_ROOT);

  // ─── Args ────────────────────────────────────────────────────────────────────
  const args = process.argv.slice(2);
  let impulse = null, model = null, forceNarrator = null, category = 'STANDARD', bodyFile = null, loreText = null;

  for (const arg of args) {
    if (arg.startsWith('--impulse='))   impulse       = arg.slice(10);
    else if (arg.startsWith('--model='))      model         = arg.slice(8);
    else if (arg.startsWith('--narrator='))   forceNarrator = arg.slice(11);
    else if (arg.startsWith('--category='))   category       = arg.slice(11).toUpperCase();
    else if (arg.startsWith('--bodyfile='))   bodyFile      = arg.slice(11);
    else if (arg.startsWith('--lore='))   loreText      = arg.slice(7);
  }

  const validationErrors = validateCommitInput({ impulse, model, bodyFile });
  if (validationErrors.length > 0) {
    console.error('FEHLER: Ungültige Eingaben:');
    validationErrors.forEach(err => console.error(`  - ${err}`));
    console.error('USAGE: node core/commit-layer/author_system.js --impulse="..." --model="..." --bodyfile="core/.body_text.txt"');
    process.exit(1);
  }

  logAccess('START', { impulse, model, bodyFile, forceNarrator, category });

  if (!fs.existsSync(bodyFile)) {
    console.error(`FEHLER: bodyfile nicht gefunden: ${bodyFile}`);
    process.exit(1);
  }

  // ─── 1. Staged Files prüfen ────────────────────────────────────────────────
  const stagedFiles = getStagedFiles();
  if (stagedFiles.length === 0) {
    console.error('FEHLER: Keine Dateien gestaged. Bitte vorher `git add` ausführen.');
    process.exit(1);
  }
  console.log(`📂 ${stagedFiles.length} Datei(en) gestaged.`);

  // ─── 2. State laden (using utils) ────────────────────────────────────────────
  const plotchain      = loadJSON(PATHS.plotchain, []);
  const charSheets     = loadJSON(PATHS.charSheets, { characters: {} });
  const narrativeParams= loadJSON(PATHS.narrativeParams, { mood_pool: [] });
  const compositeChain = loadJSON(PATHS.compositeChain, { chain: [], genesis_composite: 'c0j0n0a0p0', genesis_mood: 'genesis' });
  const sidejokePool   = loadJSON(PATHS.sidejokes, { general: [] });
  const loreArcs       = loadJSON(PATHS.loreArcs, { arcs: {} });

  // ─── 3. Composite deterministisch berechnen ────────────────────────────────
  const commitHash = getShortHeadHash();
  const { composite: prevComposite, mood: prevMood } = getPrevComposite(compositeChain);
  const { arcCount, plotCount } = getCounts(loreArcs, plotchain);
  const seed = djb2(prevComposite + commitHash);
  const derived = derive(prevComposite, commitHash, { a: arcCount, p: plotCount, moodPool: narrativeParams.mood_pool }, undefined, prevMood);
  const compositeHash = derived.composite;
  const rng = new XorShift128(seed);
  console.log(`🔑 Composite: ${compositeHash} (n=${derived.n}, mood=${derived.mood})`);

  // ─── 4. Narrator deterministisch auswählen ─────────────────────────────────
  let selectedNarrator = null;
  if (forceNarrator) {
    for (const [, char] of Object.entries(charSheets.characters)) {
      if (char.name.toLowerCase() === forceNarrator.toLowerCase()) {
        selectedNarrator = char;
        break;
      }
    }
  }
  if (!selectedNarrator) {
    const parsed = parseComposite(compositeHash);
    const nKey   = String(parsed ? parsed.n : derived.n);
    selectedNarrator = charSheets.characters[nKey] || charSheets.characters['2']; // fallback Basher
  }
  console.log(`🎭 Narrator: ${selectedNarrator.name} (${selectedNarrator.role})`);

  // ─── 4b. Finale Attitudes berechnen (using utils) ───────────────────────────
  const baseAtts = selectedNarrator.attitudes || {};
  const moodMods = narrativeParams?.attitude_modifiers?.[derived.mood] || {};
  const finalAttitudes = calculateFinalAttitudes(baseAtts, moodMods);
  const moodNarratorKey = `${selectedNarrator.name}+${derived.mood}`;
  const moodNarratorCombo = narrativeParams?.narrator_mood_combination?.examples?.[moodNarratorKey] || '';

  // ─── 4c. Narrator-Voice-Intro generieren ─────────────────────────────────
  function buildVoiceIntro(narrator, att, mood, combo, _impulse) {
    const name = narrator.name;
    const brief = narrator.tone_brief || '';
    const codeLove = att.code_love || 5;
    const cleanup = att.cleanup_resentment || 5;
    const doku = att.doku_irritation || 5;
    const critic = att.criticism_tendency || 5;
    const praise = att.praise_tendency || 5;
    const verbose = att.verbosity_bias || 5;
    const optimist = att.optimism || 5;

    const candidates = [];
    const rpick = arr => arr[rng.nextInt(0, arr.length)];

    if (codeLove >= 8) candidates.push({ dev: codeLove - 5, text: rpick(['Genau mein Ding. ', 'Endlich wieder Code. ', 'Das hier — das ist, wofür ich lebe. ', ]) });
    else if (codeLove <= 2) candidates.push({ dev: 5 - codeLove, text: rpick(['Code. Egal. ', 'Syntax, Semantik — who cares. ', ]) });

    if (cleanup >= 8) candidates.push({ dev: cleanup - 5, text: rpick(['Schon wieder hinterherräumen. ', 'Jedes Mal dasselbe: jemand macht Dreck, ich wisch auf. ', 'Aufräumen. Immer ich. ', ]) });
    else if (cleanup <= 2) candidates.push({ dev: 5 - cleanup, text: rpick(['Sauber. Aufgeräumt. ', 'Kein Dreck. So mag ich das. ', ]) });

    if (doku >= 8) candidates.push({ dev: doku - 5, text: rpick(['Und jetzt auch noch Doku. Na toll. ', 'Dokumentieren. Weil Code allein ja nicht reicht. ', 'Papierkram. Hasse ich. ', ]) });
    else if (doku <= 1) candidates.push({ dev: 5 - doku, text: rpick(['Dokumentiert. Nachvollziehbar. ', 'Sauber dokumentiert — wie es sich gehört. ', ]) });

    if (critic >= 8) candidates.push({ dev: critic - 5, text: rpick(['Das hätte man auch gleich richtig machen können. ', 'Nicht schlecht. Aber auch nicht gut. ', 'Ich seh was, das kaputtgehen wird. ', ]) });

    if (praise >= 8) candidates.push({ dev: praise - 5, text: rpick(['Richtig gut geworden! ', 'Das ist saubere Arbeit — Respekt. ', ]) });

    if (optimist >= 8) candidates.push({ dev: optimist - 5, text: rpick(['Wird schon halten. ', 'Läuft. Und wenn nicht — läuft\'s auch. ', 'Guter Commit. Keine Sorgen. ', ]) });
    else if (optimist <= 1) candidates.push({ dev: 5 - optimist, text: rpick(['Wird eh wieder kaputtgehen. ', 'Optimismus ist nur aufgeschobene Enttäuschung. ', 'Ich sag\'s ungern: das hält nicht. ', ]) });

    candidates.sort((a, b) => b.dev - a.dev);
    const lines = candidates.slice(0, 2).map(c => c.text);
    const introShort = lines.join('');
    const introLong = `${name} (${narrator.role}) — ${brief} Mood: ${mood}. ${introShort}`;

    if (verbose <= 0) return '';
    if (verbose <= 2) return `${introShort.trim()}\n\n`;
    if (verbose <= 5) return introShort ? `_${introShort.trim()}_\n\n` : '';
    const comboLine = combo ? ` ${combo}` : '';
    return `_${introLong.trim()}${comboLine}_\n\n`;
  }
  const voiceIntro = buildVoiceIntro(selectedNarrator, finalAttitudes, derived.mood, moodNarratorCombo, impulse);

  // ─── 5. Cross-Narrator aus Plotchain (using utils) ───────────────────────────
  const oldPrevNarrator = getPrevNarratorFromPlotchain(plotchain, selectedNarrator.name);
  const prevNarratorName = oldPrevNarrator?.name;
  if (prevNarratorName) console.log(`🔗 Cross-Narrator: ${prevNarratorName} → ${selectedNarrator.name}`);

  // ─── 5b. Richtungswechsel-Detection ──────────────────────────────────────────
  const lastPlotNode_prev = plotchain.length > 0 ? plotchain[plotchain.length - 1] : null;
  const prevSummary = lastPlotNode_prev?.summary || '';
  const isDocu     = t => /\b(doku|archiv|changelog|readme|plan|comment|docs)\b/i.test(t);
  const isFix      = t => /\b(fix|bug|hotfix|patch|repair|fehler|korr)\b/i.test(t);
  const isRefactor = t => /\b(restruktur|refactor|cleanup|aufr|modular|extract|dedupli)\b/i.test(t);
  const isBuild    = t => /\b(build|commit.layer|author.system|hook|verifier|pipeline)\b/i.test(t);
  const classifyImpulse = t => isDocu(t) ? 'DOKU' : isFix(t) ? 'FIX' : isRefactor(t) ? 'REFACTOR' : isBuild(t) ? 'BUILD' : 'CODE';
  const prevClass = classifyImpulse(prevSummary);
  const currClass = classifyImpulse(impulse);
  const isDirectionChange = prevSummary && prevClass !== currClass;
  if (isDirectionChange) console.log(`↩️  Richtungswechsel: ${prevClass} → ${currClass} (${prevNarratorName || 'kein Vorgänger'} → ${selectedNarrator.name})`);

  // ─── 6. Sidejoke auswählen ────────────────────────────────────────────────
  function resolvePlaceholders(text, ctx) {
    const file0 = ctx.stagedFiles.length > 0 ? path.basename(ctx.stagedFiles[0]) : 'dieser Datei';
    const count = ctx.stagedFiles.length;
    const hash  = ctx.commitHash || 'abc1234';
    return text
      .replace(/\{FILE\}/g, file0)
      .replace(/\{COUNT2?\}/g, String(count))
      .replace(/\{HASH\}/g, hash)
      .replace(/\{DATE\}/g, new Date().toISOString().substring(0, 10))
      .replace(/\{TIME\}/g, new Date().toISOString().substring(11, 19))
      .replace(/\{PASS\}/g, '0')
      .replace(/\{FAIL\}/g, '0')
      .replace(/\{STATUS\}/g, 'OK')
      .replace(/\{ROWS\}/g, String(count))
      .replace(/\{LOC\}/g, '?')
      .replace(/\{TIME2?\}/g, new Date().toISOString().substring(11, 16))
      .replace(/\{([A-Z])\}/g, (_, c) => {
        const map = { N: String(count), M: '?', H: '?' };
        return map[c] || '?';
      })
      .replace(/\{[A-Z][A-Z0-9_]*\}/g, 'X');
  }
  const HAS_PLACEHOLDER = /\{[A-Z][A-Z0-9_]*\}/;
  const jokeKey  = selectedNarrator.name.toLowerCase();
  const rawList = (sidejokePool[jokeKey] && sidejokePool[jokeKey].length > 0) ? sidejokePool[jokeKey] : (sidejokePool.general || []);
  const resolvedList = rawList.map(j => resolvePlaceholders(j, { stagedFiles, commitHash }));
  const jokeList = resolvedList.filter(j => !HAS_PLACEHOLDER.test(j));
  const joke = jokeList.length > 0 ? jokeList[rng.nextInt(0, jokeList.length)] : '';

  // ─── 7. Commit-Body zusammenbauen (mit Template-Engine oder Story-Generator!) ──────────
  const customBody = fs.readFileSync(bodyFile, 'utf8').trim();
  let commitBody = '';

  if (joke) commitBody += `${joke}\n\n`;
  if (voiceIntro) commitBody += voiceIntro;

  // ─── TEMPLATE-ENGINE INTEGRATION (NEW) ─────────────────────────────────────
  const templateEngine = new TemplateEngine();
  const templatePath = path.join(LORE_DIR, 'narrative_templates.json');
  const schemaPath = path.join(LORE_DIR, 'template_schema.json');
  
  templateEngine.loadTemplates(templatePath);
  templateEngine.loadSchema(schemaPath);
  
  // Calculate causal signals
  const causalPrevNarrator = getPrevNarratorFromPlotchain(plotchain, selectedNarrator.name);
  const diffStats = getDiffStats();
  const domains = detectDomainsFromFiles(stagedFiles);
  
  const causalSignals = {
    character: selectedNarrator.name,
    mood: derived.mood,
    relationship: {
      prev_narrator: causalPrevNarrator?.name || null,
      state: calculateRelationshipState(causalPrevNarrator?.name, selectedNarrator.name, plotchain)
    },
    domain: {
      primary: domains[0] || 'Unknown',
      secondary: domains[1] || null,
      resonance: calculateDomainResonance(selectedNarrator.name, domains)
    },
    sequence: {
      phase: calculateSequencePhase(plotchain),
      theme: detectCurrentTheme(plotchain),
      progress: calculateArcProgress(plotchain)
    },
    codeContext: {
      type: classifyCodeChange(impulse, stagedFiles),
      complexity: calculateComplexity(diffStats),
      files: stagedFiles,
      summary: generateTechnicalSummary(diffStats, stagedFiles),
      impulse: impulse
    }
  };
  
  // Generate narrative prompt via template engine — pure helper to avoid
  // eslint's no-useless-assignment false-positive on try/catch reassignment.
  async function renderNarrativePrompt() {
    try {
      const result = templateEngine.buildNarrativePrompt(
        causalSignals.character,
        causalSignals.mood,
        causalSignals.relationship,
        causalSignals.domain,
        causalSignals.sequence,
        causalSignals.codeContext
      );
      console.log('📜 Template-Engine Prompt generiert (kausal)');
      return result;
    } catch (templateError) {
      console.warn('⚠️ Template-Engine fehlgeschlagen, fallback zu story_generator:', templateError.message);
      return await generateStory({
        impulse,
        customBody,
        selectedNarrator,
        finalAttitudes,
        mood: derived.mood
      });
    }
  }
  const generatedStory = await renderNarrativePrompt();

  commitBody += generatedStory;

  // ─── Konsolidierungs-Patch 2026-07-03 ───────────────────────────────────────────
  // customBody (aus core/.body_text.txt) an commitBody anhaengen,
  // weil die neue Template-Engine das customBody sonst komplett ignoriert
  // und nur in PLOT_LORE.md schreibt (FIX fuer "Body fehlt im Commit"-Bug).
  if (customBody) {
    commitBody += `\n\n${customBody}`;
  }

  function buildSubject(narrator, impulseText, mood, files) {
    const name = narrator.name;
    const nFiles = files.length;
    let short = impulseText.replace(/[:;,]\s*$/, '').trim();
    if (short.length > 55) {
      const cut = short.substring(0, 50);
      const lastSpace = cut.lastIndexOf(' ');
      short = (lastSpace > 30 ? cut.substring(0, lastSpace) : cut) + '…';
    }
    const styles = {
      Buffy:   () => `[${name}] ${short}`,
      Basher:  () => `${name} (${nFiles} files): ${short}`,
      Vannon:  () => short.split(' ').slice(0, 4).join(' ') + (short.split(' ').length > 4 ? '…' : ''),
      Thinker: () => `${short} [Analyse: ${name}]`,
      Devin:   () => `${name} sagt: ${short}`,
      Ghost:   () => `${name} verzeichnet: ${short}`,
      Glitch:  () => `${name} ermittelt: ${short}`,
      Squizzle:() => `${name}s Fall: ${short}`,
      Echo:    () => `${name} erinnert: ${short}`,
      Spark:   () => `${name} entdeckt: ${short}`,
      Argos:   () => `${name}: ${nFiles} Dateien — ${short.length > 30 ? short.substring(0, 30) + '…' : short}`,
      Null:    () => `${name}: ${short.substring(0, 40)}${short.length > 40 ? '…' : ''}`,
      Flux:    () => {
        const words = short.split(' ').slice(0, 5).join(' ');
        return `${name} — also — ${words}${short.split(' ').length > 5 ? '…' : ''}`;
      },
      Sage:    () => `${name} lehrt: ${short}`,
    };
    const fn = styles[name] || styles['Buffy'];
    return fn ? fn() : `${name}: ${short}`;
  }
  const subjectLine = buildSubject(selectedNarrator, impulse, derived.mood, stagedFiles);

  const skipToken = stagedFiles.length > 20 ? '\n[FILES:SKIP]' : '';
  const catToken  = category !== 'STANDARD' ? ` [CATEGORY:${category}]` : '';

  const metadataFooter = `\n---\n[NARRATOR:${selectedNarrator.name}] [MODEL:${model}] [IMPULSE:${impulse}] [COMPOSITE:${compositeHash}]${catToken}${skipToken}`;

  const fullCommitMessage = `${subjectLine}\n\n${commitBody}${metadataFooter}\n`;

  const isoTimestamp = new Date().toISOString().substring(0, 19).replace('T', ' ');

  let changelog;
  let isDuplicate = false;
  if (fs.existsSync(PATHS.changelog)) {
    changelog = fs.readFileSync(PATHS.changelog, 'utf8');
    if (changelog.includes(`\`${compositeHash}\``)) {
      console.log(`📋 CHANGELOG: Composite \`${compositeHash}\` bereits vorhanden — überspringe Eintrag (Duplikat).`);
      isDuplicate = true;
    }
  }

  if (!isDuplicate) {
    const changelogEntry = `### [${isoTimestamp}] ${impulse}\n**Narrator:** ${selectedNarrator.name} | **Model:** ${model} | **Composite:** \`${compositeHash}\`\n- ${stagedFiles.length} Datei(en) geändert.\n\n`;
    if (fs.existsSync(PATHS.changelog)) {
      changelog = changelog.replace(/^(# .+?\n\n)/s, `$1${changelogEntry}`);
    } else {
      changelog = `# CHANGELOG\n\n${changelogEntry}`;
    }
    fs.writeFileSync(PATHS.changelog, changelog, 'utf8');
    execSync(`git add "${PATHS.changelog}"`, { stdio: 'inherit', ...WIN_HIDE });
    console.log(`📋 CHANGELOG aktualisiert + gestaged (SSoT: ${path.relative(REPO_ROOT, PATHS.changelog)})`);
  } else {
    execSync(`git add "${PATHS.changelog}"`, { stdio: 'inherit', ...WIN_HIDE });
  }

  const lastPlotNode = plotchain.length > 0 ? plotchain[plotchain.length - 1] : null;
  const pId = lastPlotNode && lastPlotNode.p_id ? `p${parseInt(lastPlotNode.p_id.slice(1)) + 1}` : 'p1';

  const recentCommits = getRecentCommits(5);
  const dataChanges = getDiffStats();
  const causalSummary = recentCommits.map(rc => `${rc.hash}: ${rc.subject}`);

  const newPlotNode = {
    p_id:      pId,
    id:        `plot-${isoTimestamp.replace(' ', 'T')}`,
    timestamp: isoTimestamp,
    summary:   impulse,
    narrator:  selectedNarrator.name,
    model_id:  model,
    composite: compositeHash,
    ref_to:    lastPlotNode ? lastPlotNode.id : 'none',
    prev_narrator: prevNarratorName || null,
    data_changes:  dataChanges,
    recent_commits: recentCommits,
    causal_chain_summary: causalSummary
  };
  plotchain.push(newPlotNode);
  saveJSON(PATHS.plotchain, plotchain);
  console.log(`📖 Plotchain: ${pId} hinzugefügt.`);

  // ── Auto-Freeze: Archiviere alte Nodes wenn Threshold überschritten ──
  if (plotchain.length > KEEP_THRESHOLD + 5) {
    try {
      freezePlotchain(KEEP_THRESHOLD, false);
    } catch (e) {
      console.warn(`⚠️  Plotchain-Freeze fehlgeschlagen: ${e.message}`);
    }
  }

  const chainEntries = compositeChain.chain || [];
  compositeChain.chain.push({
    seq:       chainEntries.length + 1,
    hash:      commitHash,
    composite: compositeHash,
    mood:      derived.mood,
    narrator:  selectedNarrator.name,
    model_id:  model,
    date:      isoTimestamp,
  });
  saveJSON(PATHS.compositeChain, compositeChain);
  console.log(`🔗 Composite Chain: seq ${chainEntries.length + 1} gespeichert.`);

  const consistencyIssues = checkConsistency(compositeChain, plotchain);
  if (consistencyIssues.length >0) {
    console.warn('⚠️ CONSISTENCY WARNINGS:');
    consistencyIssues.forEach(warn => console.warn(`  - ${warn}`));
  }

  // ─── AUTOMATIC PLOT_LORE INTEGRATION (NEW!)
  if (loreText || customBody.length > 10) {
    const plotLoreEntry = loreText || customBody;
    if (!fs.existsSync(PATHS.plotLore)) {
      const header = '# PLOT LORE — SyxBridge\n\nPersistenter Dokumentations-Layer. Jeder Commit kann einen Eintrag erzeugen.\n\n---\n';
      fs.writeFileSync(PATHS.plotLore, header, 'utf8');
    }
    let narratorTag = `[NARRATOR:${selectedNarrator.name}]`;
    let narratorVoice = '';
    if (charSheets && charSheets.characters) {
      for (const [, char] of Object.entries(charSheets.characters)) {
        if (char.name === selectedNarrator.name) {
          narratorVoice = char.voice_traits;
          break;
        }
      }
    }
    const headerParts = [`[${pId}]`, narratorTag, `[COMPOSITE:${compositeHash}]`];
    const headerLine = headerParts.join(' ');
    let entry;
    entry = `\n### [${isoTimestamp}] ${headerLine}\n**Erzähler:** ${selectedNarrator.name} | **Stimme:** ${narratorVoice || 'Siehe character_sheets.json'}\n**Perspektive:** Monolog — nur ${selectedNarrator.name}s Stimme.\n${plotLoreEntry}\n`;
    fs.appendFileSync(PATHS.plotLore, entry, 'utf8');
    console.log(`📜 PLOT_LORE: Eintrag hinzugefügt (${pId}).`);
  }

  // ─── Alle SSOT-Dateien vor dem Commit stagen! ────────────────────────────────
  const ssotFiles = [PATHS.plotchain, PATHS.compositeChain];
  if (fs.existsSync(PATHS.plotLore)) ssotFiles.push(PATHS.plotLore);
  // Staging durchführen
  execSync(`git add ${ssotFiles.map(f => `"${f}"`).join(' ')}`, { stdio: 'pipe', ...WIN_HIDE });

  fs.writeFileSync(PATHS.commitMsg, fullCommitMessage, 'utf8');
  console.log(`📝 Commit-Message: ${PATHS.commitMsg}`);

  console.log('\n═══════════════════════════════════════════');
  console.log('  COMMITTING...');
  console.log('═══════════════════════════════════════════\n');

  try {
    execSync(`git commit -F "${PATHS.commitMsg}"`, { stdio: 'inherit', ...WIN_HIDE });
    logAccess('SUCCESS', { impulse, model, compositeHash, narrator: selectedNarrator.name });
    console.log('\n✅ AUTHOR SYSTEM: Commit erfolgreich. Narrative aktualisiert.');
  } catch (e) {
    logAccess('ERROR', { impulse, model, error: e.message });
    console.error('\n❌ AUTHOR SYSTEM: Commit blockiert. Prüfe verify_commit_msg Errors oben.');
    process.exit(1);
  }
})();

