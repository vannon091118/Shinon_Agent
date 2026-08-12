/**
 * rng.js — Deterministischer PRNG für den Commit-Layer
 * 
 * Kein Math.random(), kein crypto — rein deterministisch, reproduzierbar.
 * XorShift-Variante (32-bit) — für Index-Selektion aus kleinen Pools optimiert.
 * djb2 Hash für String → 32-bit Seed.
 * derive() leitet nächsten Composite-Hash aus vorherigem + Commit-Hash ab.
 * decodeJ() dekodiert j-Werte in narrative Anweisungen (gespiegelt aus narrative_params.json).
 * 
 * Standalone: Keine Abhängigkeiten außer Node.js.
 * Verwendet von: derive_composite.js, verify_commit_msg.js
 */

// ─── djb2 Hash ───────────────────────────────────────────────────────
// Deterministischer String → 32-bit unsigned Integer.
// Gleicher Input → gleicher Output. Immer.

function djb2(str) {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash + str.charCodeAt(i)) >>> 0;
  }
  return hash;
}

// ─── XorShift128+ ────────────────────────────────────────────────────
// 128-bit State, 32-bit kompatibel.
// Periode: 2^128 − 1. Verteilung: gleichmäßig.

class XorShift128 {
  constructor(seed) {
    // seed ist ein 32-bit unsigned Integer
    this.s0 = seed >>> 0;
    // s1 aus Seed ableiten (SplitMix-Schritt) — kein hartcodiertes s1=1 mehr
    this.s1 = ((seed * 1812433253 + 1) >>> 0);

    // Aufwärmphase: 10 Iterationen für bessere Verteilung
    for (let i = 0; i < 10; i++) {
      this._step();
    }
  }

  _step() {
    let s1 = this.s0;
    const s0 = this.s1;
    this.s0 = s0;
    s1 ^= s1 << 23;
    s1 ^= s1 >>> 17;
    s1 ^= s0;
    s1 ^= s0 >>> 26;
    this.s1 = s1;
    return ((s0 + this.s1) >>> 0) / 4294967296;
  }

  /** Gibt Float in [0, 1) zurück */
  next() {
    return this._step();
  }

  /** Gibt Integer in [min, max) zurück (min inklusiv, max exklusiv) */
  nextInt(min, max) {
    return min + Math.floor(this.next() * (max - min));
  }
}

// ─── Composite Format ────────────────────────────────────────────────
// Erweiterbar: Neue Entitätstypen einfach hier ergänzen.
// Jeder Eintrag: { key, prefix, source } — source = 'sequence' | 'rng'

const COMPOSITE_FORMAT = [
  { key: 'c', prefix: 'c', source: 'sequence' },
  { key: 'j', prefix: 'j', source: 'rng', poolSize: 100 },
  { key: 'n', prefix: 'n', source: 'rng', poolSize: 14 },
  { key: 'a', prefix: 'a', source: 'rng' },
  { key: 'p', prefix: 'p', source: 'rng' }
];

/**
 * Parst einen Composite-String in seine Bestandteile.
 * @param {string} composite - z.B. "c5j3a2p8"
 * @returns {Object} Key-Value Map, z.B. {c:5, j:3, a:2, p:8}
 */
function parseComposite(composite) {
  const result = {};
  for (const field of COMPOSITE_FORMAT) {
    const regex = new RegExp(field.prefix + '(\\d+)');
    const match = composite.match(regex);
    result[field.key] = match ? parseInt(match[1]) : 0;
  }
  return result;
}

/**
 * Baut einen Composite-String aus einer Key-Value Map.
 * @param {Object} parts - z.B. {c:5, j:3, a:2, p:8}
 * @returns {string} "c5j3a2p8"
 */
function buildComposite(parts) {
  return COMPOSITE_FORMAT
    .filter(f => parts[f.key] !== undefined)
    .map(f => f.prefix + parts[f.key])
    .join('');
}

// ─── Composite Derivation ────────────────────────────────────────────

/**
 * Leitet den nächsten Composite aus dem vorherigen + Commit-Hash ab.
 * Nutzt COMPOSITE_FORMAT — neue Felder werden automatisch mitverarbeitet.
 *
 * @param {string} prevComposite - z.B. "c4j12a3p7" oder Genesis "c0j0a0p0"
 * @param {string} commitHash    - Aktueller Git-Commit-Hash
 * @param {Object} limits        - z.B. {a: 5, p: 17} — RNG-Felder bekommen ihre Pool-Größen
 * @param {string} [prevMood]    - Letzter Mood (um Wiederholung zu vermeiden)
 * @returns {{ composite: string, seed: number, mood: string }}
 */
function derive(prevComposite, commitHash, limitsOrArcCount, plotCount, prevMood) {
  if (!commitHash) {
    throw new Error('derive: commitHash ist Pflichtfeld. Kann nicht undefined oder leer sein.');
  }

  // Backward-Compat: alter Aufruf derive(prev, hash, arcCount, plotCount)
  let limits = limitsOrArcCount;
  if (typeof limitsOrArcCount === 'number') {
    limits = { a: limitsOrArcCount, p: plotCount || 1 };
  } else if (!limitsOrArcCount) {
    limits = {};
  }

  const prev = parseComposite(prevComposite);
  const seed = djb2(prevComposite + commitHash);
  const rng = new XorShift128(seed);

  const next = {};

  for (const field of COMPOSITE_FORMAT) {
    if (field.source === 'sequence') {
      next[field.key] = (prev[field.key] || 0) + 1;
    } else if (field.source === 'rng') {
      const max = (limits[field.key] !== undefined)
        ? limits[field.key]
        : (field.poolSize || 100);
      next[field.key] = max > 0 ? rng.nextInt(1, max + 1) : 1;
    }
  }

  // Mood selektieren — nie derselbe wie vorheriger
  const mood = selectMood(next.j, prevMood, limits.moodPool || null);

  return {
    composite: buildComposite(next),
    seed,
    mood,
    ...next
  };
}

// ─── Mood-Selektion ──────────────────────────────────────────────────

// Built-in Mood-Pool (gespiegelt aus narrative_params.json)
const DEFAULT_MOOD_POOL = ['sachlich', 'sarkastisch', 'erschöpft', 'triumphierend',
  'selbstironisch', 'neugierig', 'müde-zufrieden', 'alarmiert', 'trocken', 'warm'];

/**
 * Wählt einen Mood deterministisch aus dem Pool.
 * Garantiert: Mood[N] != Mood[N-1].
 *
 * @param {number} j - j-Wert aus dem Composite
 * @param {string} [prevMood] - Vorheriger Mood
 * @param {string[]} [moodPool] - Optionaler Pool (aus narrative_params.json)
 * @returns {string} Der ausgewählte Mood
 */
function selectMood(j, prevMood, moodPool) {
  const pool = moodPool || DEFAULT_MOOD_POOL;
  if (pool.length === 0) return 'neutral';

  let moodIndex = j % pool.length;

  // Wenn derselbe wie vorheriger: nimm den nächsten (deterministisch)
  if (pool[moodIndex] === prevMood) {
    moodIndex = (moodIndex + 1) % pool.length;
  }

  return pool[moodIndex];
}

// Built-in Defaults (gespiegelt aus narrative_params.json).
// Werden überschrieben wenn der Caller narrativeParams übergibt.
const DEFAULT_TONES = ['sachlich', 'sarkastisch', 'erschöpft', 'triumphierend',
  'selbstironisch', 'neugierig', 'müde-zufrieden', 'alarmiert', 'trocken', 'warm'];
const DEFAULT_STRUCTURES = ['chronologisch', 'problem_lösung', 'flashback',
  'dialog', 'faktenliste'];

/**
 * Dekodiert j-Wert in narrative Anweisung.
 *
 * @param {number} j - j-Wert (0 für Genesis, 1-99 für Commits)
 * @param {Object} [params] - Optional: geladen aus narrative_params.json.
 *   Wenn nicht übergeben, werden Built-in Defaults verwendet.
 *   Neue Töne/Strukturen in narrative_params.json werden automatisch genutzt.
 * @returns {{ tone: string, structure: string, callback: boolean }}
 */
function decodeJ(j, params) {
  if (j === 0) {
    return { tone: 'genesis', structure: 'genesis', callback: false };
  }

  // Töne: Entweder aus params oder Built-in Defaults
  let tones = DEFAULT_TONES;
  let structures = DEFAULT_STRUCTURES;

  if (params && params.decoding) {
    // Extrahiere Töne aus narrative_params.json (erweiterbar)
    if (params.decoding.tone && params.decoding.tone.values) {
      const toneKeys = Object.keys(params.decoding.tone.values).sort((a, b) => Number(a) - Number(b));
      tones = toneKeys.map(k => params.decoding.tone.values[k].tone);
    }
    // Extrahiere Strukturen aus narrative_params.json (erweiterbar)
    if (params.decoding.structure && params.decoding.structure.values) {
      const structKeys = Object.keys(params.decoding.structure.values).sort((a, b) => Number(a) - Number(b));
      structures = structKeys.map(k => params.decoding.structure.values[k].structure);
    }
  }

  return {
    tone: tones[j % tones.length],
    structure: structures[j % structures.length],
    callback: j > 50
  };
}

module.exports = { djb2, XorShift128, derive, decodeJ, selectMood, parseComposite, buildComposite, COMPOSITE_FORMAT };
