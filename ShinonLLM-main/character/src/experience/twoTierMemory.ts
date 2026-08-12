// Two-Tier Memory System - Scope 0.3.0
// Tier 1 (Fakten) + Tier 2 (Patterns) mit SQLite Backend

import type { Pattern, PersonalFact } from "./patterns.js";

export type Tier = 1 | 2;

export type TwoTierMemoryConfig = {
  readonly tier1Table: "personal_facts";
  readonly tier2Table: "patterns";
  readonly linkTable: "pattern_links";
  readonly enableCrossTierQueries: boolean;
};

export type TwoTierSqliteAdapter = Readonly<{
  run: (sql: string, params?: ReadonlyArray<unknown>) => { changes?: number } | void;
  all: (sql: string, params?: ReadonlyArray<unknown>) => ReadonlyArray<Record<string, unknown>>;
}>;

export const defaultTwoTierConfig: TwoTierMemoryConfig = {
  tier1Table: "personal_facts",
  tier2Table: "patterns",
  linkTable: "pattern_links",
  enableCrossTierQueries: true,
};

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeRowToFact(row: Record<string, unknown>): PersonalFact | null {
  if (!isNonEmptyString(row.id) || !isNonEmptyString(row.content) || !isNonEmptyString(row.created_at)) {
    return null;
  }
  return {
    id: row.id.trim(),
    content: row.content.trim(),
    category: (isNonEmptyString(row.category) ? row.category.trim() : "event") as PersonalFact["category"],
    createdAt: row.created_at.trim(),
    sessionId: isNonEmptyString(row.session_id) ? row.session_id.trim() : "default",
  };
}

function normalizeRowToPattern(row: Record<string, unknown>): Pattern | null {
  if (!isNonEmptyString(row.id) || !isNonEmptyString(row.anchor) || !isNonEmptyString(row.type)) {
    return null;
  }
  
  let examples: Pattern["examples"] = [];
  if (typeof row.examples_json === "string" && row.examples_json.trim().length > 0) {
    try {
      const parsed = JSON.parse(row.examples_json);
      if (Array.isArray(parsed)) {
        examples = parsed.map((ex: { factId?: string; content?: string; date?: string }) => ({
          factId: ex.factId ?? "",
          content: ex.content ?? "",
          date: ex.date ?? "",
        }));
      }
    } catch {
      // ignore
    }
  }
  
  return {
    id: row.id.trim(),
    anchor: row.anchor.trim(),
    type: row.type.trim() as Pattern["type"],
    confidence: typeof row.confidence === "number" ? row.confidence : 0.5,
    examples: Object.freeze(examples),
    firstSeen: isNonEmptyString(row.first_seen) ? row.first_seen.trim() : isNonEmptyString(row.created_at) ? row.created_at.trim() : new Date().toISOString(),
    lastReinforced: isNonEmptyString(row.last_reinforced) ? row.last_reinforced.trim() : isNonEmptyString(row.created_at) ? row.created_at.trim() : new Date().toISOString(),
    reinforcementCount: typeof row.reinforcement_count === "number" ? row.reinforcement_count : 1,
  };
}

/**
 * Fragt Tier 1 (Personal Facts) ab.
 * Unterstuetzt Filter nach sessionId, category, zone.
 */
export function queryTier1(
  adapter: TwoTierSqliteAdapter,
  filters: { sessionId?: string; category?: string; zone?: string; limit?: number } = {}
): ReadonlyArray<PersonalFact> {
  let query = "SELECT id, content, category, session_id, created_at FROM personal_facts WHERE 1=1";
  const params: unknown[] = [];
  
  if (filters.sessionId) {
    query += " AND session_id = ?";
    params.push(filters.sessionId);
  }
  if (filters.category) {
    query += " AND category = ?";
    params.push(filters.category);
  }
  if (filters.zone) {
    query += " AND zone = ?";
    params.push(filters.zone);
  }
  
  query += " ORDER BY created_at DESC";
  
  if (filters.limit && filters.limit > 0) {
    query += " LIMIT ?";
    params.push(filters.limit);
  }
  
  const rows = adapter.all(query, params);
  return Object.freeze(
    rows.map(normalizeRowToFact).filter((f): f is PersonalFact => f !== null)
  );
}

/**
 * Fragt Tier 2 (Patterns) ab.
 * Unterstuetzt Filter nach type, anchor, und Mindest-Konfidenz.
 */
export function queryTier2(
  adapter: TwoTierSqliteAdapter,
  filters: { type?: string; anchor?: string; minConfidence?: number; limit?: number } = {}
): ReadonlyArray<Pattern> {
  let query = "SELECT id, anchor, type, confidence, examples_json, first_seen, last_reinforced, reinforcement_count, created_at FROM patterns WHERE 1=1";
  const params: unknown[] = [];
  
  if (filters.type) {
    query += " AND type = ?";
    params.push(filters.type);
  }
  if (filters.anchor) {
    query += " AND anchor = ?";
    params.push(filters.anchor);
  }
  if (typeof filters.minConfidence === "number") {
    query += " AND confidence >= ?";
    params.push(filters.minConfidence);
  }
  
  query += " ORDER BY confidence DESC, last_reinforced DESC";
  
  if (filters.limit && filters.limit > 0) {
    query += " LIMIT ?";
    params.push(filters.limit);
  }
  
  const rows = adapter.all(query, params);
  return Object.freeze(
    rows.map(normalizeRowToPattern).filter((p): p is Pattern => p !== null)
  );
}

/**
 * Verknuepft ein Tier 1 Fakt mit einem Tier 2 Pattern.
 * Speichert die Verknuepfung in der pattern_links Tabelle.
 */
export function linkTier1ToTier2(
  adapter: TwoTierSqliteAdapter,
  factId: string,
  patternId: string,
  relation: "supports" | "contradicts" | "example_of" = "example_of"
): void {
  const now = new Date().toISOString();
  adapter.run(
    "INSERT OR REPLACE INTO pattern_links (pattern_id, fact_id, relation_type, created_at) VALUES (?, ?, ?, ?)",
    [patternId, factId, relation, now]
  );
}

/**
 * Speichert ein neues Pattern in Tier 2.
 * Extrahiert aus einem Personal Fact.
 */
export function savePattern(
  adapter: TwoTierSqliteAdapter,
  pattern: Pattern
): void {
  const now = new Date().toISOString();
  adapter.run(
    [
      "INSERT OR REPLACE INTO patterns",
      "(id, anchor, type, confidence, examples_json, first_seen, last_reinforced, reinforcement_count, created_at)",
      "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    ].join(" "),
    [
      pattern.id,
      pattern.anchor,
      pattern.type,
      pattern.confidence,
      JSON.stringify(pattern.examples),
      pattern.firstSeen,
      pattern.lastReinforced,
      pattern.reinforcementCount,
      now,
    ]
  );
}

/**
 * Speichert ein Personal Fact in Tier 1.
 */
export function saveFact(
  adapter: TwoTierSqliteAdapter,
  fact: PersonalFact,
  zone: "hot" | "mid" | "cold" = "hot"
): void {
  const now = new Date().toISOString();
  adapter.run(
    [
      "INSERT OR REPLACE INTO personal_facts",
      "(id, content, category, session_id, conversation_id, created_at, zone, relevance_score)",
      "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    ].join(" "),
    [
      fact.id,
      fact.content,
      fact.category,
      fact.sessionId,
      "default",
      fact.createdAt,
      zone,
      0.5,
    ]
  );
}
