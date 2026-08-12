#!/usr/bin/env node
/**
 * verify_commit_msg.js — SyxBridge Commit-Layer Enforcer (v0.30)
 *
 * MINIMALE CHECKS, MAXIMALES ERGEBNIS.
 * Jeder Check deckt mehrere Qualitäts-Dimensionen gleichzeitig ab.
 * Keine stufige Abfrage — alle Fehler gesammelt in EINER Ausgabe.
 *
 * VERSION-SYNC mit AGENTS.md (Pflicht): Die unten exportierte Konstante
 * `VERIFY_COMMIT_MSG_VERSION` MUSS in dem in AGENTS.md-Header genannten
 * Versions-Range (`v0.25.0 → v0.30`) liegen. Der Drift-Checker
 * `core/scripts/check_verify_agents_drift.js` liest beide Quellen
 * und bricht mit Exit 1, wenn die Sync-Bedingung verletzt ist.
 *
 * CHECKS:
 *   1. TOKENS:        [NARRATOR], [MODEL], [IMPULSE], [COMPOSITE]
 *   2. IMPULSE-INTEGRATION: Impulse-Text muss im Körper vorkommen
 *   3. STORYTELLING:  Kausalität (weil/deshalb/Grund) + Bullet-Limit
 *   4. NARRATOR:      Composite-N → character_sheets-Zuordnung + Wortzahl/Stimme
 *   5. COMPOSITE:     P-/A-Validierung + CHANGELOG-Anker + Chain-Integrity-WARN
 *   6. FILES:         Datei-Referenzen + [FILES:SKIP]-Guard
 *   7. PLACEHOLDER:   Unaufgelöste {PLACEHOLDER}-Tokens
 *   8. BUG-CONSIST:   PLAN.md ↔ KNOWN_BUGS_REPORT.md Cross-Check (WARN)
 *
 * Exit 0 = PASS | Exit 1 = BLOCKED
 *
 * @version v0.30
 * @since   v0.23a (initial)
 * @see     AGENTS.md §„Verify-Regeln (verify_commit_msg.js)"
 */

// eslint-disable-next-line no-unused-vars
const VERIFY_COMMIT_MSG_VERSION = 'v0.30';

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const WIN_HIDE = process.platform === 'win32' ? { windowsHide: true, creationFlags: 0x08000000 } : {};

// ─── Git-Repo + Commit-Message ────────────────────────────────────
let repoRoot;
try { repoRoot = execSync('git rev-parse --show-toplevel', { encoding: 'utf8', ...WIN_HIDE }).trim(); process.chdir(repoRoot); }
catch (_) { console.error('BLOCKED: Git-Umgebung nicht verfuegbar.'); process.exit(1); }

const msgFile = path.resolve(process.argv[2] || '');
if (!msgFile || !fs.existsSync(msgFile)) {
  console.error('BLOCKED: Keine Commit-Message-Datei. USAGE: node verify_commit_msg.js <path>');
  process.exit(1);
}

const commitMsg = fs.readFileSync(msgFile, 'utf8');
if (!commitMsg.trim()) { console.error('BLOCKED: Commit-Message ist leer.'); process.exit(1); }

// ─── Abhängigkeiten laden ─────────────────────────────────────────
// Dynamische Pfad-Auflösung via __dirname (wie derive_composite.js)
const { parseComposite } = require('./commit_lore/rng');

const COMMIT_LORE_DIR     = path.join(__dirname, 'commit_lore');
const compositeChainPath  = path.join(COMMIT_LORE_DIR, 'composite_chain.json');
const loreArcsPath        = path.join(COMMIT_LORE_DIR, 'lore_arcs.json');
const plotchainPath       = path.join(COMMIT_LORE_DIR, 'plotchain.json');
const characterSheetsPath = path.join(COMMIT_LORE_DIR, 'character_sheets.json');
const writingRulesPath    = path.join(COMMIT_LORE_DIR, 'writing_rules.json');
const changelogPath = (() => {
  const root = path.join(repoRoot, 'CHANGELOG.md');
  const docs = path.join(repoRoot, 'core/archive/docs/CHANGELOG.md');
  if (fs.existsSync(root)) return root;    // SSoT: Root hat IMMER Vorrang (AGENTS.md #4)
  if (fs.existsSync(docs))  return docs;   // Fallback: Archive
  return root; // fallback
})();

let characterSheets = null;
try { if (fs.existsSync(characterSheetsPath)) characterSheets = JSON.parse(fs.readFileSync(characterSheetsPath, 'utf8')); } catch (_) {}

let writingRules = null;
try { if (fs.existsSync(writingRulesPath)) writingRules = JSON.parse(fs.readFileSync(writingRulesPath, 'utf8')); } catch (_) {}

// ─── Staged Files ─────────────────────────────────────────────────
let stagedFiles = [];
try { stagedFiles = execSync('git diff --cached --name-only', { encoding: 'utf8', ...WIN_HIDE }).trim().split('\n').filter(Boolean); }
catch (_) { console.error('BLOCKED: Konnte staged Files nicht lesen.'); process.exit(1); }
if (stagedFiles.length === 0) { console.error('BLOCKED: Keine Dateien gestaged.'); process.exit(1); }

// ─── Messwerte ────────────────────────────────────────────────────
const wordCount = commitMsg.split(/\s+/).filter(Boolean).length;
const lines = commitMsg.split('\n').filter(l => l.trim());
const bulletLines = lines.filter(l => /^\s*[-*]\s/.test(l));
const bulletRatio = lines.length > 0 ? bulletLines.length / lines.length : 0;

const errors = [];

// ═══════════════════════════════════════════════════════════════════
// CHECK 0: CHAIN-INTEGRITY — Vorgänger-Commit valide? (deferred, P2)
// Prüft ob der letzte Plotchain-Node denselben Composite hat wie
// composite_chain.json[last]. Gibt WARN aus, blockiert NICHT.
// Sichert die Kausalkette über Commit-Grenzen hinweg.
// ═══════════════════════════════════════════════════════════════════
{
  try {
    if (fs.existsSync(plotchainPath) && fs.existsSync(compositeChainPath)) {
      const pc    = JSON.parse(fs.readFileSync(plotchainPath, 'utf8'));
      const chain = JSON.parse(fs.readFileSync(compositeChainPath, 'utf8'));
      const lastPc    = Array.isArray(pc) && pc.length > 0 ? pc[pc.length - 1] : null;
      const lastChain = (chain.chain || []).length > 0 ? chain.chain[chain.chain.length - 1] : null;
      if (lastPc && lastChain && lastPc.composite && lastChain.composite) {
        if (lastPc.composite !== lastChain.composite) {
          console.warn(`⚠️  [CHAIN-INTEGRITY] Plotchain[last].composite=${lastPc.composite} ≠ composite_chain[last].composite=${lastChain.composite}`);
          console.warn('   Die narrative Kette hat eine Lücke. Commit wird NICHT blockiert, aber prüfe ob ein amend-Sync fehlt.');
        }
      }
    }
  } catch (_) { /* Nicht-blockierender Check — Fehler ignorieren */ }
}

// ─── Kategorie-Detection ─────────────────────────────────────────
// [CATEGORY:RESTRUCTURE|HOTFIX|TRIVIAL|STANDARD] Token oder Auto-Detect
const categoryTokenMatch = commitMsg.match(/\[CATEGORY:(RESTRUCTURE|HOTFIX|TRIVIAL|STANDARD|TEST-ASSET|LORE-ONLY)\]/i);
let commitCategory = categoryTokenMatch ? categoryTokenMatch[1].toUpperCase() : null;

if (!commitCategory) {
  // Auto-Detect basierend auf writing_rules.json auto_detect Regeln
  if (stagedFiles.length > 15 || /restruktur|verschoben|moved|umstruktur|restructur/i.test(commitMsg)) {
    commitCategory = 'RESTRUCTURE';
  } else if (wordCount < 60 && /\b(fix|hotfix|bugfix|patch)\b/i.test(commitMsg)) {
    commitCategory = 'HOTFIX';
  } else if (wordCount < 30 && stagedFiles.length <= 3) {
    commitCategory = 'TRIVIAL';
  } else {
    commitCategory = 'STANDARD';
  }
}

// Kategorie-spezifische Limits aus writing_rules.json
const catRules = writingRules?.rules?.commit_diary || {};
const catMinWords = catRules.min_words?.[commitCategory] ?? 80;
const catMaxWords = catRules.max_words?.[commitCategory] ?? 1500;
const _catBulletPolicy = catRules.bullet_policy?.[commitCategory] ?? 'allowed';
const catStoryRequired = catRules.storytelling_required?.[commitCategory] ?? false;
const filesSkipThreshold = catRules.files_skip_threshold ?? 20;

// [FILES:SKIP] Token
const hasFilesSkip = /\[FILES:SKIP\]/i.test(commitMsg);

// ═══════════════════════════════════════════════════════════════════
// CHECK 1: TOKENS — alle Pflicht-Token auf einmal
// ═══════════════════════════════════════════════════════════════════

const impulseMatch = commitMsg.match(/\[IMPULSE:(.{5,}?)\]/i);
const narratorMatch = commitMsg.match(/\[NARRATOR:(Buffy|Basher|Thinker|Vannon|Squizzle|Devin|Argos|Ghost|Spark|Glitch|Null|Echo|Flux|Sage)\]/i);
const modelMatch    = commitMsg.match(/\[MODEL:([a-z0-9._\-\s()]+)\]/i);
const compositeMatch = commitMsg.match(/\[COMPOSITE:((?:[a-z]+\d+)+)\]/i);

if (!modelMatch)    errors.push('[MODEL] Token fehlt. [MODEL:<name>]');
if (!impulseMatch)  errors.push('[IMPULSE] Token fehlt. [IMPULSE:<User-Auftrag>]');
if (!compositeMatch) errors.push('[COMPOSITE] Token fehlt. [COMPOSITE:cXjXnXaXpX]');

let parsedComposite = compositeMatch ? parseComposite(compositeMatch[1]) : null;

// ═══════════════════════════════════════════════════════════════════
// CHECK 2: IMPULSE-INTEGRATION — der Impulse-Text MUSS im Körper leben
// ═══════════════════════════════════════════════════════════════════

if (impulseMatch) {
  const impulseText = impulseMatch[1].trim();
  // Körper = Commit-Message OHNE die Token-Zeile selbst
  const body = commitMsg.replace(/\[IMPULSE:.*?\]/gi, '').replace(/\[NARRATOR:.*?\]/gi, '')
    .replace(/\[MODEL:.*?\]/gi, '').replace(/\[COMPOSITE:.*?\]/gi, '');

  // Mindestens 3 aufeinanderfolgende Zeichen aus dem Impulse-Text müssen im Körper vorkommen
  let impulseIntegrated = false;
  for (let i = 0; i <= impulseText.length - 5; i++) {
    const chunk = impulseText.substring(i, i + 5).toLowerCase();
    if (body.toLowerCase().includes(chunk)) { impulseIntegrated = true; break; }
  }
  // Fallback: einzelne signifikante Wörter (≥4 chars) aus dem Impulse
  if (!impulseIntegrated) {
    const words = impulseText.split(/\s+/).filter(w => w.length >= 4);
    impulseIntegrated = words.some(w => body.toLowerCase().includes(w.toLowerCase()));
  }

  if (!impulseIntegrated) {
    errors.push(`[IMPULSE-INTEGRATION] Der Impulse-Text muss in die Erzählung eingewoben sein. "${impulseText.substring(0, 50)}${impulseText.length > 50 ? '...' : ''}" erscheint NUR als Token, nicht im narrativen Körper.`);
  }
}

// ═══════════════════════════════════════════════════════════════════
// CHECK 3: STORYTELLING — keine Bullet-Listen, Kausalität muss da sein
// ═══════════════════════════════════════════════════════════════════

// 3a: Bullet-Points nur bei übermäßiger Nutzung blockieren
const maxAllowedBulletRatio = 0.3; // Max 30% Bullet-Points erlaubt
const maxAllowedBulletLines = 5; // Max 5 Bullet-Points erlaubt, auch wenn Ratio okay
if (bulletLines.length > maxAllowedBulletLines || bulletRatio > maxAllowedBulletRatio) {
  errors.push(`[STORYTELLING] Zu viele Bullet-Points (${bulletLines.length} Zeilen, ${Math.round(bulletRatio * 100)}%): Nutze mehr fließenden Text. Max ${maxAllowedBulletLines} Bullet-Points oder ${Math.round(maxAllowedBulletRatio * 100)}% erlaubt.`);
}

// 3b: Kausalität — Kategorie-abhängig (HOTFIX/RESTRUCTURE: optional)
if (catStoryRequired) {
  const causalityRegex = /\b(weil|deshalb|Ursache|Root.Cause|Grund|daher|somit|folglich|denn|darum|Auswirkung|Effekt|Resultat|Konsequenz)\b/i;
  if (!causalityRegex.test(commitMsg)) {
    errors.push('[STORYTELLING] Keine Kausalität erkennbar. Die Erzählung braucht mindestens einen Konnektor: weil, deshalb, Grund, daher, Auswirkung...');
  }
}

// ═══════════════════════════════════════════════════════════════════
// CHECK 4: NARRATOR — Token + Charakter-Regeln (Wortzahl, Sprachmuster)
// ═══════════════════════════════════════════════════════════════════

if (parsedComposite) {
  const nVal = String(parsedComposite.n || 0);
  let expectedNarrator = null;
  let narratorRules = null;

  if (characterSheets?.characters?.[nVal]) {
    expectedNarrator = characterSheets.characters[nVal].name;
    narratorRules = characterSheets.characters[nVal].verifier_rules || {};
  }

  if (!expectedNarrator) {
    errors.push(`[NARRATOR] Composite n=${nVal} — kein Charakterblatt in character_sheets.json.characters.${nVal}`);
  } else {
    if (!narratorMatch) {
      errors.push(`[NARRATOR] Token fehlt. Composite n=${nVal} → [NARRATOR:${expectedNarrator}]`);
    } else if (narratorMatch[1].toLowerCase() !== expectedNarrator.toLowerCase()) {
      errors.push(`[NARRATOR] Falsch. Composite n=${nVal} → ${expectedNarrator}, aber Commit hat [NARRATOR:${narratorMatch[1]}]`);
    }    // Wortzahl-Grenzen — Kategorie-bewusst (writing_rules.json overrides character_sheets bei RESTRUCTURE/HOTFIX)
    const narratorMin = narratorRules.min_words || 20;
    const narratorMax = narratorRules.max_words || 500;
    // Effektive Limits: STANDARD-Override (Overblocking-Fix 2026-07-06)
    //   Begruendung: cMin = Math.max(narratorMin, catMinWords) liesz fuer STANDARD+Puffer-y-Narrator
    //   den narratorMin gewinnen (Buffy n=1 mit narratorMin=136 blockierte ~120-Wort-Commits).
    //   Wenn writing_rules.json commit_diary.min_words.STANDARD explizit setzt (jetzt 120),
    //   gewinnt dieser Wert ueber narratorMin. Sanity-Floor 20 verhindert Over-Loosening.
    //   Andere Kategorien unveraendert (Math.max bleibt).
    const stdMinOverride = catRules.min_words?.STANDARD;
    const cMin = (commitCategory === 'STANDARD' && stdMinOverride !== undefined && stdMinOverride >= 20)
      ? stdMinOverride
      : Math.max(narratorMin, catMinWords);
      // RESTRUCTURE: Kategorie-Cap (500) bricht Narrator-Max — Buffy darf nicht 1500 schreiben
    const cMax = commitCategory === 'RESTRUCTURE' ? catMaxWords : narratorMax;
    if (wordCount < cMin) errors.push(`[NARRATOR-WORTZAHL] ${wordCount}/${cMin} Wörter (${commitCategory}). ${expectedNarrator} braucht ≥${cMin}.`);
    if (wordCount > cMax) errors.push(`[NARRATOR-WORTZAHL] ${wordCount}/${cMax} Wörter (${commitCategory}). ${expectedNarrator} max ${cMax}.`);

    // Sprachmuster
    if (narratorRules.must_contain_regex) {
      const p = new RegExp(narratorRules.must_contain_regex, 'i');
      if (!p.test(commitMsg)) {
        errors.push(`[NARRATOR-STIMME] ${expectedNarrator}s Sprachmuster fehlt. Pattern: ${narratorRules.must_contain_regex}`);
      }
    }
  }
}

// ═══════════════════════════════════════════════════════════════════
// CHECK 5: COMPOSITE — Seed-Kette + P/A-Validierung + CHANGELOG-Anker
// ═══════════════════════════════════════════════════════════════════

// if (compositeMatch && fs.existsSync(compositeChainPath)) {
//   try {
//     const chain = JSON.parse(fs.readFileSync(compositeChainPath, 'utf8'));
//     const entries = chain.chain || [];
//     if (entries.length > 0) {
//       const prev = entries[entries.length - 1].composite;
//       let aCount = 1, pCount = 1;
//       try { const arcs = JSON.parse(fs.readFileSync(loreArcsPath, 'utf8')); aCount = Object.keys(arcs.arcs || {}).length; } catch (_) {}
//       try { const pc = JSON.parse(fs.readFileSync(plotchainPath, 'utf8')); pCount = Array.isArray(pc) ? pc.length : 0; } catch (_) {}
//       try {
//         const hash = execSync('git rev-parse --short HEAD', { encoding: 'utf8' }).trim();
//         const expected = derive(prev, hash, { a: aCount, p: pCount });
//         if (expected.composite !== compositeMatch[1]) {
//           errors.push(`[COMPOSITE-CHAIN] Kette gebrochen. Erwartet: ${expected.composite}, Gefunden: ${compositeMatch[1]}`);
//         }
//       } catch (_) {}
//     }
//   } catch (e) { errors.push(`[COMPOSITE-CHAIN] Fehler: ${e.message}`); }
// }

// P-/A-Validierung (now using lore_arcs)
let frozenMaxP = null;
if (fs.existsSync(loreArcsPath)) {
  try {
    const loreArcs = JSON.parse(fs.readFileSync(loreArcsPath, 'utf8'));
    // Find the largest last_p from all arcs
    for (const arc of Object.values(loreArcs.arcs || {})) {
      if (arc.last_p) {
        const pNum = parseInt(String(arc.last_p).replace('p', ''), 10);
        if (!frozenMaxP || pNum > frozenMaxP) {
          frozenMaxP = pNum;
        }
      }
    }
  } catch (_) {}
}

if (parsedComposite?.p && fs.existsSync(plotchainPath)) {
  try {
    const pc = JSON.parse(fs.readFileSync(plotchainPath, 'utf8'));
    const activeMaxP = Array.isArray(pc) ? pc.length : 0;
    const pNum = parsedComposite.p;
    // Check if active plotchain has p, or if it's ≤ frozenMaxP
    let valid = false;
    if (pNum <= activeMaxP) {
      valid = true;
    } else if (frozenMaxP && pNum <= frozenMaxP) {
      valid = true;
    }
    if (!valid) errors.push(`[COMPOSITE-P] p${parsedComposite.p} nicht in gültigem Bereich.`);
  } catch (_) {}
}
if (parsedComposite?.a && fs.existsSync(loreArcsPath)) {
  try {
    const arcs = JSON.parse(fs.readFileSync(loreArcsPath, 'utf8'));
    const arcId = `a${parsedComposite.a}`;
    if (!arcs.arcs?.[arcId]) errors.push(`[COMPOSITE-A] Arc a${parsedComposite.a} nicht in lore_arcs.`);
  } catch (_) {}
}

// CHANGELOG-Anker — prüft staged Content bevor Working Directory
if (compositeMatch) {
  let changelogContent = '';
  // Root zuerst — SSoT per AGENTS.md Regel #4. Archive nur als Fallback.
  // stdio:'pipe' unterdrückt das "fatal: path does not exist"-Stderr-Geräusch.
  const stagePaths = ['CHANGELOG.md', 'core/archive/docs/CHANGELOG.md'];
  for (const sp of stagePaths) {
    try {
      changelogContent = execSync(`git show :${sp}`, { encoding: 'utf8', stdio: 'pipe', ...WIN_HIDE });
      if (changelogContent) break;
    } catch (_) {}
  }
  // Fallback: Working Directory
  if (!changelogContent && fs.existsSync(changelogPath)) {
    try { changelogContent = fs.readFileSync(changelogPath, 'utf8'); } catch (_) {}
  }
  if (changelogContent && !changelogContent.includes(compositeMatch[1])) {
    errors.push(`[CHANGELOG] Composite \`${compositeMatch[1]}\` nicht in CHANGELOG.md. Jeder Eintrag braucht: **Composite:** \`cXjXnXaXpX\``);
  }
}

// ═══════════════════════════════════════════════════════════════════
// CHECK 6: CROSS-NARRATOR-REFERENZ — OPTIONAL, KEIN BLOCKIERUNG
// ═══════════════════════════════════════════════════════════════════
// (Entfernt für maximale kreative Freiheit — writing_rules.json sagt es ist nicht zwingend mehr)

// ═══════════════════════════════════════════════════════════════════
// CHECK 7: KAUSALITAET — Commit referenziert Vorgaenger-Commits/Dateien
// ═══════════════════════════════════════════════════════════════════
{
  const causalityRefs = [];

  // Letzte 5 Commit-Hashes aus Git laden
  try {
    const recentLog = execSync('git log -5 --format="%h" --no-merges', { encoding: 'utf8', ...WIN_HIDE }).trim();
    if (recentLog) {
      for (const h of recentLog.split('\n').filter(Boolean)) {
        causalityRefs.push(h.trim());
      }
    }
  } catch (_) { /* Git nicht verfuegbar */ }

  // Aus plotchain recent_commits und data_changes extrahieren
  let plotchain = [];
  if (fs.existsSync(plotchainPath)) {
    try { plotchain = JSON.parse(fs.readFileSync(plotchainPath, 'utf8')); } catch (_) {}
  }
  if (plotchain.length > 0) {
    const lastPcNode = plotchain[plotchain.length - 1];
    if (lastPcNode.recent_commits && Array.isArray(lastPcNode.recent_commits)) {
      for (const rc of lastPcNode.recent_commits) {
        if (rc.hash) causalityRefs.push(rc.hash);
        if (rc.subject) {
          const subjectWords = rc.subject.split(/\s+/).filter(w => w.length > 5);
          for (const w of subjectWords.slice(0, 5)) {
            causalityRefs.push(w);
          }
        }
        if (rc.files_touched) {
          for (const f of rc.files_touched) {
            const base = path.basename(f, path.extname(f));
            if (base.length > 3) causalityRefs.push(base);
          }
        }
      }
    }
    if (lastPcNode.data_changes && Array.isArray(lastPcNode.data_changes)) {
      for (const dc of lastPcNode.data_changes) {
        const base = path.basename(dc.file, path.extname(dc.file));
        if (base.length > 3) causalityRefs.push(base);
      }
    }
  }

  const uniqueRefs = [...new Set(causalityRefs)].filter(r => r.length > 3);
  const commitMsgLower = commitMsg.toLowerCase();
  const hasCausalRef = uniqueRefs.some(ref => commitMsgLower.includes(ref.toLowerCase()));

  if (!hasCausalRef && uniqueRefs.length > 0) {
    console.warn('KAUSALITAETS-HINWEIS: Commit referenziert keinen der letzten');
    console.warn('   5 Commits oder deren Datenaenderungen. Erwaege einen Rueckbezug');
    console.warn('   fuer narrative Kontinuitaet.');
  }
}

// ═══════════════════════════════════════════════════════════════════
// Datei-Referenzen + Placeholder (Pflicht, aber kompakt)
// ═══════════════════════════════════════════════════════════════════

// Datei-Referenzen — [FILES:SKIP] bei >20 Dateien erlaubt
// Automatisch verwaltete Narrative-Metadaten werden ausgeschlossen:
const AUTO_MANAGED_FILES = new Set(['CHANGELOG.md', 'plotchain.json', 'composite_chain.json', 'PLOT_LORE.md', 'plotlore.md', '.body_text.txt']);
const missingFiles = stagedFiles.filter(f => {
  const name = f.replace(/\\/g, '/').split('/').pop();
  if (AUTO_MANAGED_FILES.has(name)) return false; // author_system auto-fügt diese hinzu
  const stem = name.replace(/\.[^.]+$/, '');
  return !commitMsg.includes(name) && !commitMsg.includes(stem);
});
if (missingFiles.length > 0 && !(hasFilesSkip && stagedFiles.length > filesSkipThreshold)) {
  errors.push(`[FILES] ${missingFiles.length} Datei(en) nicht referenziert: ${missingFiles.slice(0, 5).join(', ')}${missingFiles.length > 5 ? '...' : ''}`);
  if (stagedFiles.length > filesSkipThreshold) {
    errors.push(`  Tipp: Bei >${filesSkipThreshold} Dateien [FILES:SKIP] im Commit-Token verwenden.`);
  }
} else if (hasFilesSkip && stagedFiles.length <= filesSkipThreshold) {
  errors.push(`[FILES:SKIP] nicht erlaubt bei ≤${filesSkipThreshold} Dateien (${stagedFiles.length} gestaged). Alle Dateien muessen referenziert werden.`);
}

const phMatch = commitMsg.match(/\{[A-Z][A-Z0-9_]+\}/g);
if (phMatch) errors.push(`[PLACEHOLDER] Unaufgelöst: ${[...new Set(phMatch)].join(', ')}`);

// ═══════════════════════════════════════════════════════════════════
// CHECK 8: BUG-REPORT vs PLAN — Konsistenz-Check
// Prüft ob im PLAN.md als erledigt markierte Bugs auch im
// KNOWN_BUGS_REPORT.md als erledigt (✅) erscheinen.
// WARNT bei Mismatch, blockiert NICHT.
// ═══════════════════════════════════════════════════════════════════
{
  const planPath = path.join(repoRoot, 'PLAN.md');
  const bugReportPath = path.join(repoRoot, 'core', 'archive', 'docs', 'KNOWN_BUGS_REPORT.md');

  let planContent = '';
  let bugReportContent = '';

  // Staged Content zuerst (wie CHANGELOG-Check)
  try { planContent = execSync('git show :PLAN.md', { encoding: 'utf8', stdio: 'pipe', ...WIN_HIDE }); } catch (_) {}
  if (!planContent && fs.existsSync(planPath)) {
    try { planContent = fs.readFileSync(planPath, 'utf8'); } catch (_) {}
  }

  try { bugReportContent = execSync('git show :core/archive/docs/KNOWN_BUGS_REPORT.md', { encoding: 'utf8', stdio: 'pipe', ...WIN_HIDE }); } catch (_) {}
  if (!bugReportContent && fs.existsSync(bugReportPath)) {
    try { bugReportContent = fs.readFileSync(bugReportPath, 'utf8'); } catch (_) {}
  }

  if (planContent && bugReportContent) {
    // Parse PLAN.md: finde alle BU-XXX IDs die als erledigt markiert sind
    const planDoneBugIds = new Set();
    // Zeilenweise scannen — BU-XXX irgendwo auf der Zeile + ✅ auf derselben Zeile = done
    const planLines = planContent.split('\n');
    for (const line of planLines) {
      const bugMatch = line.match(/\b(BU-\d+)\b/);
      if (bugMatch && line.includes('✅')) {
        planDoneBugIds.add(bugMatch[1]);
      }
    }
    // Auch DONE-INDEX prüfen: alle BU-XXX in der Tabelle sind done
    const doneIndexStart = planContent.indexOf('## ✅ DONE-INDEX');
    if (doneIndexStart !== -1) {
      const doneSection = planContent.substring(doneIndexStart);
      const doneBugIds = doneSection.match(/\bBU-\d+\b/g) || [];
      doneBugIds.forEach(id => planDoneBugIds.add(id));
    }

    // Parse KNOWN_BUGS_REPORT.md: finde alle BU-XXX und ihren Status
    const bugReportOpenBugs = new Set(); // Bugs die NOCH OFFEN sind
    const bugReportAllBugs = new Set();
    const brLines = bugReportContent.split('\n');
    for (const line of brLines) {
      const bugMatch = line.match(/\b(BU-\d+)\b/);
      if (bugMatch) {
        const bugId = bugMatch[1];
        bugReportAllBugs.add(bugId);
        // Ohne ✅ auf derselben Zeile = noch offen
        if (!line.includes('✅')) {
          bugReportOpenBugs.add(bugId);
        }
      }
    }

    // Cross-Reference: PLAN sagt done → Bug-Report muss auch ✅ haben
    const zombieBugs = [];
    for (const bugId of planDoneBugIds) {
      if (bugReportOpenBugs.has(bugId)) {
        zombieBugs.push(bugId);
      }
      // Auch warnen wenn der Bug gar nicht im Report vorkommt
      if (!bugReportAllBugs.has(bugId)) {
        zombieBugs.push(`${bugId} (fehlt komplett in KNOWN_BUGS_REPORT.md)`);
      }
    }

    if (zombieBugs.length > 0) {
      console.warn('═══════════════════════════════════════════');
      console.warn('  ⚠️  [BUG-CONSISTENCY] PLAN.md vs KNOWN_BUGS_REPORT.md');
      console.warn('═══════════════════════════════════════════');
      console.warn(`  ${zombieBugs.length} Bug(s) in PLAN.md als ✅ markiert,`);
      console.warn('  aber in KNOWN_BUGS_REPORT.md noch offen oder fehlend:');
      zombieBugs.forEach(b => console.warn(`    • ${b}`));
      console.warn('');
      console.warn('  → KNOWN_BUGS_REPORT.md aktualisieren oder PLAN.md Status korrigieren.');
      console.warn('  → Commit wird NICHT blockiert.\n');
    }
  }
}

// ═══════════════════════════════════════════════════════════════════
// AUSWERTUNG
// ═══════════════════════════════════════════════════════════════════

if (errors.length > 0) {
  console.error('\n═══════════════════════════════════════════');
  console.error('  COMMIT BLOCKED');
  console.error('═══════════════════════════════════════════\n');
  errors.forEach(e => console.error(`  ${e}`));
  console.error('\n  Pflicht: [NARRATOR], [MODEL], [IMPULSE], [COMPOSITE], Kausalität, Datei-Refs, CHANGELOG-Anker');
  console.error('  Optional: [CATEGORY:RESTRUCTURE|HOTFIX|TRIVIAL] [FILES:SKIP]');
  console.error('  Storytelling: Keine Bullet-Listen, Impulse eingewoben, Charakter-Stimme\n');
  process.exit(1);
}

// PASS
let narratorInfo = '';
if (parsedComposite && compositeMatch) {
  const nKey = String(parsedComposite.n || 0);
  if (characterSheets?.characters?.[nKey]) {
    const s = characterSheets.characters[nKey];
    narratorInfo = ` | Narrator: ${s.name} (${s.role})`;
  }
}

console.log('\n═══════════════════════════════════════════');
console.log('  COMMIT VERIFIED');
console.log('═══════════════════════════════════════════\n');
stagedFiles.forEach(f => console.log(`  + ${f}`));
console.log(`\n  ${stagedFiles.length} Datei(en) — ${wordCount} Wörter [${commitCategory}]${narratorInfo}`);
if (compositeMatch) console.log(`  Composite: ${compositeMatch[1]}`);

// Kausalitaets-Zusammenfassung im PASS-Output
{
  let plotchain = [];
  if (fs.existsSync(plotchainPath)) {
    try { plotchain = JSON.parse(fs.readFileSync(plotchainPath, 'utf8')); } catch (_) {}
  }
  if (plotchain.length > 0) {
    const lastPcNode = plotchain[plotchain.length - 1];
    if (lastPcNode.recent_commits && lastPcNode.recent_commits.length > 0) {
      console.log(`  Kausalitaets-Chain: ${lastPcNode.recent_commits.length} Vorgaenger-Commits referenzierbar`);
    }
    if (lastPcNode.data_changes && lastPcNode.data_changes.length > 0) {
      const totalChanges = lastPcNode.data_changes.reduce((s, dc) => s + dc.insertions + dc.deletions, 0);
      console.log(`  Daten-Kontext: ${lastPcNode.data_changes.length} Dateien, ${totalChanges} Zeilen Aenderungen`);
    }
  }
}
console.log('');
process.exit(0);
