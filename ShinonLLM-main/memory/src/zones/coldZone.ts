// Cold Zone - Scope 0.3.0
// Archiv mit Pattern-Haertung mit SQLite Backend

import type { Pattern, PersonalFact, extractPattern } from "../../../character/src/experience/patterns.js";

export type ColdZoneEntry = {
  readonly patternId: string;
  readonly pattern: Pattern;
  readonly compressed: boolean;
  readonly originalFactCount: number;
  readonly archivedAt: string;
};

export type ColdZoneSqliteAdapter = Readonly<{
  run: (sql: string, params?: ReadonlyArray<unknown>) => { changes?: number } | void;
  all: (sql: string, params?: ReadonlyArray<unknown>) => ReadonlyArray<Record<string, unknown>>;
}>;

export type ColdZone = {
  readonly archive: (sessionIds: ReadonlyArray<string>) => Promise<number>;
  readonly extractPatterns: (sessionIds: ReadonlyArray<string>) => Promise<ReadonlyArray<Pattern>>;
  readonly loadPatterns: (anchors?: ReadonlyArray<string>) => ReadonlyArray<Pattern>;
};

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
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
    firstSeen: isNonEmptyString(row.first_seen) ? row.first_seen.trim() : new Date().toISOString(),
    lastReinforced: isNonEmptyString(row.last_reinforced) ? row.last_reinforced.trim() : new Date().toISOString(),
    reinforcementCount: typeof row.reinforcement_count === "number" ? row.reinforcement_count : 1,
  };
}

export function createColdZone(adapter: ColdZoneSqliteAdapter): ColdZone {
  return {
    archive: async (sessionIds: ReadonlyArray<string>): Promise<number> => {
      if (sessionIds.length === 0) return 0;
      
      // First extract patterns from cold zone facts
      const patterns = await createColdZone(adapter).extractPatterns(sessionIds);
      
      // Mark facts as archived
      const placeholders = sessionIds.map(() => "?").join(",");
      const result = adapter.run(
        `UPDATE personal_facts SET zone = 'cold', relevance_score = 0.2 WHERE zone = 'mid' AND session_id IN (${placeholders})`,
        [...sessionIds]
      );
      
      return typeof result?.changes === "number" ? result.changes : 0;
    },

    extractPatterns: async (sessionIds: ReadonlyArray<string>): Promise<ReadonlyArray<Pattern>> => {
      if (sessionIds.length === 0) return Object.freeze([]);
      
      const placeholders = sessionIds.map(() => "?").join(",");
      const rows = adapter.all(
        `SELECT id, content, category, session_id, created_at FROM personal_facts WHERE session_id IN (${placeholders}) AND (category = 'preference' OR category = 'relationship')`,
        [...sessionIds]
      );
      
      const patterns: Pattern[] = [];
      
      for (const row of rows) {
        if (!isNonEmptyString(row.id) || !isNonEmptyString(row.content) || !isNonEmptyString(row.created_at)) {
          continue;
        }
        
        const fact: PersonalFact = {
          id: row.id.trim(),
          content: row.content.trim(),
          category: (isNonEmptyString(row.category) ? row.category.trim() : "event") as PersonalFact["category"],
          createdAt: row.created_at.trim(),
          sessionId: isNonEmptyString(row.session_id) ? row.session_id.trim() : "default",
        };
        
        // Use extractPattern from patterns.ts
        const { extractPattern } = await import("../../../character/src/experience/patterns.js");
        const pattern = extractPattern(fact);
        
        if (pattern) {
          // Save pattern to database
          const now = new Date().toISOString();
          adapter.run(
            "INSERT OR REPLACE INTO patterns (id, anchor, type, confidence, examples_json, first_seen, last_reinforced, reinforcement_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
          patterns.push(pattern);
        }
      }
      
      return Object.freeze(patterns);
    },

    loadPatterns: (anchors?: ReadonlyArray<string>): ReadonlyArray<Pattern> => {
      let query = "SELECT id, anchor, type, confidence, examples_json, first_seen, last_reinforced, reinforcement_count FROM patterns";
      const params: unknown[] = [];
      
      if (anchors && anchors.length > 0) {
        const placeholders = anchors.map(() => "?").join(",");
        query += ` WHERE anchor IN (${placeholders})`;
        params.push(...anchors);
      }
      
      query += " ORDER BY confidence DESC, last_reinforced DESC";
      
      const rows = adapter.all(query, params);
      return Object.freeze(
        rows.map(normalizeRowToPattern).filter((p): p is Pattern => p !== null)
      );
    },
  };
}
