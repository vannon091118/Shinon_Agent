
const fs = require('fs');

const {
  findRepoRoot,
  getCommitLorePaths,
  loadJSON,
  getStagedFiles,
  getRecentCommits,
  getPrevComposite,
  getPrevNarratorFromPlotchain
} = require('./utils');

async function collectStoryContext(options) {
  const repoRoot = findRepoRoot();
  const lorePaths = getCommitLorePaths(repoRoot);
  
  const stagedFiles = getStagedFiles();
  const plotchain = loadJSON(lorePaths.plotchain, []);
  const compositeChain = loadJSON(lorePaths.compositeChain, { chain: [] });
  const _characterSheets = loadJSON(lorePaths.charSheets, { characters: {} });
  const loreArcs = loadJSON(lorePaths.loreArcs, { arcs: {} });
  const recentCommits = getRecentCommits(5);
  const prevNarrator = getPrevNarratorFromPlotchain(plotchain, options.selectedNarrator?.name);
  const sidejokePool = loadJSON(lorePaths.sidejokes, { general: [] });
  const crossReferences = loadJSON(lorePaths.crossRefs, {});
  const narrativeParams = loadJSON(lorePaths.narrativeParams, { mood_pool: [] });
  
  let plotLoreContent = '';
  if (fs.existsSync(lorePaths.plotLore)) {
    plotLoreContent = fs.readFileSync(lorePaths.plotLore, 'utf8');
  }
  
  const prevComposite = getPrevComposite(compositeChain);
  
  return {
    impulse: options.impulse,
    customBody: options.customBody,
    selectedNarrator: options.selectedNarrator,
    finalAttitudes: options.finalAttitudes,
    mood: options.mood,
    stagedFiles,
    recentCommits,
    prevNarrator,
    plotchain,
    prevComposite,
    plotLoreContent: plotLoreContent.substring(0, 5000),
    loreArcs,
    sidejokePool,
    crossReferences,
    narrativeParams
  };
}

function buildStoryPrompt(context) {
  let narratorPrompt = '';
  if (context.selectedNarrator?.voice_traits) {
    narratorPrompt = `Sprich im Stil von ${context.selectedNarrator.name}: ${context.selectedNarrator.voice_traits}`;
  }
  if (context.finalAttitudes) {
    narratorPrompt += ` Aktuelle Laune: ${context.mood}. Einstellungen: ${JSON.stringify(context.finalAttitudes)}`;
  }

  const filesStr = context.stagedFiles.length > 0 
    ? context.stagedFiles.map(f => `- ${f}`).join('\n') 
    : '(keine Dateien gestaged)';

  const prevCommitsStr = context.recentCommits.length > 0 
    ? context.recentCommits.map(c => `- ${c.hash}: ${c.subject}`).join('\n') 
    : '(keine vorherigen Commits)';
  
  let loreArcsStr = '(keine Lore-Arcs verfügbar)';
  if (context.loreArcs?.arcs && Object.keys(context.loreArcs.arcs).length > 0) {
    loreArcsStr = Object.entries(context.loreArcs.arcs).map(([key, arc]) => `- ${key}: ${arc.description || 'Keine Beschreibung'}`).join('\n');
  }

  return `
Du bist ein narrativer Commit-Autor für das Projekt SyxBridge.

${narratorPrompt}

Schreibe eine **ORGANISCHE, DEUTSCHE GESCHICHTE** als Commit-Text! KEINE BULLET-POINTS, KEINE AUFLISTUNGEN!

Wichtige Regeln:
- SCHREIBE DEUTSCH!
- KEINE BULLET-POINTS!
- KEINE AUFLISTUNGEN!
- Nutze nur fließenden Prosa-Text!
- Baue ALLE gestagten Dateien NATÜRLICH in die Geschichte ein!
- Mache kausale Bezüge zu vorherigen Commits oder dem Plot-Lore!
- Erwähne den vorherigen Erzähler (${context.prevNarrator?.name || 'keiner'})!
- Behalte die Charakter-Stimme bei!
- Nutze Lore-Arcs als kontextuelle Hintergrundinformationen!
- Du kannst Sidejokes aus dem Sidejoke-Pool als Einstieg verwenden, falls passend!

Kontext:
USER-IMPULS (der Auftrag, der den Commit ausgelöst hat): "${context.impulse}"

GESTAGTE DATEIEN (müssen alle in die Geschichte eingebaut werden):
${filesStr}

ZUSÄTZLICHER KONTEXT (aus .body_text.txt):
${context.customBody || '(kein zusätzlicher Kontext)'}

LETZTE COMMITS (für kausale Bezüge):
${prevCommitsStr}

LORE-ARCS (als Hintergrundkontext):
${loreArcsStr}

NARRATOR-KONTEXT:
- Aktueller Erzähler: ${context.selectedNarrator?.name}
- Vorheriger Erzähler: ${context.prevNarrator?.name || 'keiner'}
- Laune: ${context.mood}

Erzeuge NUR den narrativen Commit-Text (keine Metadaten, keine Token)!
  `.trim();
}

async function generateStory(options) {
  const context = await collectStoryContext(options);

  console.log('📜 Generiere narrative Commit-Geschichte...');

  return generateNarrativeStory(context);
}

// ── Deterministic index from string hash (no RNG dependency) ──────────
function _deterministicIndex(str, len) {
  if (len <= 0) return 0;
  let h = 5381;
  for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) >>> 0;
  return h % len;
}

// ── File sentence: describe staged files in natural prose ─────────────
function _fileSentence(files) {
  if (!files || files.length === 0) return '';
  const names = files.map(f => f.split(/[\\/]/).pop());
  if (names.length === 1) return `Die zentrale Änderung betraf ${names[0]}. `;
  if (names.length <= 4) {
    const allButLast = names.slice(0, -1).join(', ');
    return `Im Fokus standen ${allButLast} und ${names.at(-1)}. `;
  }
  return `Über ${names.length} Dateien wurden in diesem Commit berührt — von ${names[0]} bis ${names.at(-1)}. `;
}

// ── Narrator-specific story closings ──────────────────────────────────
const NARRATOR_CLOSINGS = {
  Buffy:   (ctx) => `Die Strategie ist klar: ${ctx.impulse.substring(0, 50)}. Nächster Schritt.`,
  Basher:  (_ctx) => 'Funktioniert. Getestet. Weiter geht\'s.',
  Vannon:  (ctx) => `${ctx.impulse.substring(0, 40)}. Das war der Plan. Oder auch nicht.`,
  Thinker: (ctx) => `Die Analyse zeigt: ${ctx.mood}. Konsequenzen werden sich zeigen.`,
  Devin:   (ctx) => `Architektur steht. ${ctx.stagedFiles.length} Dateien. Sauber.`,
  Ghost:   (ctx) => `Die Chronik verzeichnet: ${ctx.impulse.substring(0, 50)}. Datum: ${new Date().toISOString().substring(0, 10)}.`,
  Glitch:  (ctx) => `Verbindung? ${ctx.prevNarrator?.name || 'Niemand'} → ${ctx.selectedNarrator?.name}. Zufall? Ich denke nicht.`,
  Squizzle: (ctx) => `Aktenzeichen abgeschlossen. Beweise gesichert. Fall: ${ctx.mood}.`,
  Echo:    (ctx) => `${ctx.prevNarrator?.name || 'Der Letzte'} wusste das schon. Alles hängt zusammen.`,
  Spark:   (ctx) => `Neue Erkenntnis: ${ctx.impulse.substring(0, 50)}. Spannend!`,
  Argos:   (ctx) => `Lokal gelöst. ${ctx.stagedFiles.length} Dateien. Kein externer Aufwand nötig.`,
  Null:    (ctx) => `Erledigt. ${ctx.mood}.`,
  Flux:    (ctx) => `Also — ${ctx.impulse.substring(0, 40)}. Und weiter.`,
  Sage:    (ctx) => `Die Lektion: ${ctx.impulse.substring(0, 50)}. Gemerkt.`
};

// ── Main narrative generator (no external LLM needed) ────────────────
function generateNarrativeStory(context) {
  let story = '';
  const narratorName = context.selectedNarrator?.name || 'Unbekannt';
  const prevName = context.prevNarrator?.name;

  // 1. Cross-narrator transition
  if (prevName) {
    const transitions = [
      `Wo ${prevName} den Stift niedergelegt hat, setze ich an. `,
      `${prevName} hat den Grundstein gelegt — jetzt bauen wir weiter. `,
      `Die Spur, die ${prevName} hinterlassen hat, führt direkt hierher. `,
      `Nach ${prevName}s Arbeit liegt der nächste Schritt auf der Hand. `
    ];
    story += transitions[_deterministicIndex(narratorName + (context.impulse || ''), transitions.length)];
  }

  // 2. Impulse-driven opening
  story += `Der Impuls: "${context.impulse}". `;

  // 3. File descriptions
  story += _fileSentence(context.stagedFiles);

  // 4. Custom body (from .body_text.txt)
  if (context.customBody) {
    story += context.customBody.replace(/\n+/g, ' ').trim() + ' ';
  }

  // 5. Narrator-specific closing
  const closingFn = NARRATOR_CLOSINGS[narratorName];
  if (closingFn) {
    story += closingFn(context);
  } else {
    story += `${narratorName} dokumentiert: ${context.mood}.`;
  }

  return story;
}

module.exports = {
  collectStoryContext,
  buildStoryPrompt,
  generateStory
};
