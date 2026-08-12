// Pattern Engine - Scope 0.3.0
// Regex-basierte Pattern-Erkennung fuer preference und relationship Typen

export type PatternType = "preference" | "commitment" | "relationship" | "contradiction";

export type Pattern = {
  readonly id: string;
  readonly anchor: string;
  readonly type: PatternType;
  readonly confidence: number;
  readonly examples: ReadonlyArray<{
    readonly factId: string;
    readonly content: string;
    readonly date: string;
  }>;
  readonly firstSeen: string;
  readonly lastReinforced: string;
  readonly reinforcementCount: number;
};

export type PersonalFact = {
  readonly id: string;
  readonly content: string;
  readonly category: "preference" | "event" | "commitment" | "relationship";
  readonly createdAt: string;
  readonly sessionId: string;
};

// Regex-Patterns fuer MVP (preference + relationship)
const PREFERENCE_KEYWORDS = /(?:ich\s+)?(?:mag|liebe|hasse|nicht\s+leiden\s+kann|bevorzuge|hasst|magst|liebst)/iu;
const RELATIONSHIP_KEYWORDS = /(?:meine?|mein|mit|freund|freundin|partner|partnerin|beziehung|date|trifft|treffen)/iu;

// Extrahiert Namen aus Text (einfache Heuristik: grossgeschriebene Woerter nach bestimmten Keywords)
const NAME_PATTERN = /(?:Freund|Freundin|Partner|Partnerin|mit|mit\s+der|mit\s+dem)\s+([A-Z][a-z]+)/gu;

/**
 * Extrahiert ein Pattern aus einem Personal Fact.
 * Unterstuetzt preference und relationship Typen (MVP).
 */
export function extractPattern(fact: PersonalFact): Pattern | null {
  const content = fact.content.toLowerCase();
  const now = fact.createdAt;

  // Pruefe auf preference Pattern
  if (PREFERENCE_KEYWORDS.test(fact.content)) {
    const anchor = extractPreferenceAnchor(fact.content);
    return {
      id: `pattern_pref_${fact.id}`,
      anchor,
      type: "preference",
      confidence: 0.6,
      examples: Object.freeze([{
        factId: fact.id,
        content: fact.content,
        date: now,
      }]),
      firstSeen: now,
      lastReinforced: now,
      reinforcementCount: 1,
    };
  }

  // Pruefe auf relationship Pattern
  if (RELATIONSHIP_KEYWORDS.test(fact.content)) {
    const personName = extractPersonName(fact.content);
    if (personName) {
      const anchor = `user-beziehung-${personName.toLowerCase()}`;
      return {
        id: `pattern_rel_${fact.id}`,
        anchor,
        type: "relationship",
        confidence: 0.7,
        examples: Object.freeze([{
          factId: fact.id,
          content: fact.content,
          date: now,
        }]),
        firstSeen: now,
        lastReinforced: now,
        reinforcementCount: 1,
      };
    }
  }

  return null;
}

/**
 * Findet Widersprueche zwischen zwei Fakten.
 * Erkennt Inkonsistenzen bei relationship Patterns (z.B. Anna vs Lisa).
 */
export function findContradictions(
  factA: PersonalFact,
  factB: PersonalFact
): boolean {
  // Nur relationship Fakten koennen Widersprueche haben (MVP)
  if (factA.category !== "relationship" && factB.category !== "relationship") {
    return false;
  }

  const patternA = extractPattern(factA);
  const patternB = extractPattern(factB);

  // Beide muessen relationship Patterns sein
  if (!patternA || !patternB) return false;
  if (patternA.type !== "relationship" || patternB.type !== "relationship") return false;

  // Extrahiere Personennamen aus den Anchors
  const nameA = extractNameFromAnchor(patternA.anchor);
  const nameB = extractNameFromAnchor(patternB.anchor);

  // Wenn beide relationship Patterns haben aber unterschiedliche Personen -> Widerspruch
  if (nameA && nameB && nameA !== nameB) {
    // Pruefe ob es zeitlich nah ist (max 30 Tage)
    const dateA = new Date(factA.createdAt).getTime();
    const dateB = new Date(factB.createdAt).getTime();
    const daysDiff = Math.abs(dateA - dateB) / (1000 * 60 * 60 * 24);
    
    if (daysDiff < 30) {
      return true;
    }
  }

  return false;
}

/**
 * Berechnet die Konfidenz eines Patterns basierend auf:
 * - reinforcementCount (Haeufigkeit)
 * - Zeit seit lastReinforced (Aktualitaet)
 * - Konsistenz der examples
 */
export function scoreConfidence(pattern: Pattern): number {
  const now = Date.now();
  const lastReinforced = new Date(pattern.lastReinforced).getTime();
  const firstSeen = new Date(pattern.firstSeen).getTime();
  
  // Faktor 1: Haeufigkeit (mehr Beispiele = hoehere Konfidenz)
  // Maximal 0.4 durch Haeufigkeit
  const frequencyScore = Math.min(0.4, pattern.reinforcementCount * 0.1);
  
  // Faktor 2: Aktualitaet (neuere Patterns sind relevanter)
  // Maximal 0.3 durch Aktualitaet
  const daysSinceLastReinforcement = (now - lastReinforced) / (1000 * 60 * 60 * 24);
  const recencyScore = Math.max(0, 0.3 - (daysSinceLastReinforcement * 0.01));
  
  // Faktor 3: Konsistenz (Zeitspanne zwischen firstSeen und lastReinforced)
  // Laengere, konsistente Patterns sind zuverlaessiger
  // Maximal 0.3 durch Konsistenz
  const patternAge = (lastReinforced - firstSeen) / (1000 * 60 * 60 * 24);
  const consistencyScore = Math.min(0.3, patternAge * 0.05);
  
  // Basiskonfidenz + gewichtete Faktoren
  const baseConfidence = 0.5;
  const totalConfidence = baseConfidence + frequencyScore + recencyScore + consistencyScore;
  
  // Clamp auf 0.0 - 1.0
  return Math.max(0.0, Math.min(1.0, totalConfidence));
}

// Hilfsfunktionen

function extractPreferenceAnchor(content: string): string {
  // Extrahiere Subjekt nach "mag", "liebe", "hasse", etc.
  const match = content.match(/(?:mag|liebe|hasse|bevorzuge)\s+(?:die|das|den|dem)?\s*([a-z\u00e4\u00f6\u00fc\u00df]+(?:\s+[a-z\u00e4\u00f6\u00fc\u00df]+)?)/iu);
  if (match) {
    return `user-pref-${match[1].toLowerCase().trim()}`;
  }
  return `user-pref-${content.slice(0, 20).toLowerCase().replace(/\s+/g, "-")}`;
}

function extractPersonName(content: string): string | null {
  const matches = [...content.matchAll(NAME_PATTERN)];
  if (matches.length > 0 && matches[0][1]) {
    return matches[0][1].trim();
  }
  
  // Fallback: Suche nach "mit [Name]" oder "Freund [Name]"
  const fallbackMatch = content.match(/(?:mit|Freund|Freundin)\s+([A-Z][a-z]+)/u);
  if (fallbackMatch) {
    return fallbackMatch[1].trim();
  }
  
  return null;
}

function extractNameFromAnchor(anchor: string): string | null {
  // Anchor Format: "user-beziehung-anna" -> "anna"
  const match = anchor.match(/user-beziehung-(.+)/u);
  return match ? match[1].toLowerCase() : null;
}
