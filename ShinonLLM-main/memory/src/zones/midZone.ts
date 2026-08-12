// Mid Zone - Scope 0.3.0
// Letzte 10 Sessions (selektiver Zugriff) mit SQLite Backend

export type MidZoneEntry = {
  readonly id: string;
  readonly sessionId: string;
  readonly conversationId: string;
  readonly score: number;
  readonly content: string;
  readonly createdAt: string;
};

export type MidZoneSqliteAdapter = Readonly<{
  run: (sql: string, params?: ReadonlyArray<unknown>) => { changes?: number } | void;
  all: (sql: string, params?: ReadonlyArray<unknown>) => ReadonlyArray<Record<string, unknown>>;
}>;

export type MidZone = {
  readonly load: (scope: { sessionId?: string; maxResults?: number }) => ReadonlyArray<MidZoneEntry>;
  readonly promoteFromHot: (sessionId: string) => number;
  readonly demoteToCold: (sessionIds: ReadonlyArray<string>) => number;
};

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeRowToEntry(row: Record<string, unknown>): MidZoneEntry | null {
  if (!isNonEmptyString(row.id) || !isNonEmptyString(row.session_id) || 
      !isNonEmptyString(row.conversation_id) || !isNonEmptyString(row.content) || 
      !isNonEmptyString(row.created_at)) {
    return null;
  }
  return {
    id: row.id.trim(),
    sessionId: row.session_id.trim(),
    conversationId: row.conversation_id.trim(),
    score: typeof row.relevance_score === "number" ? row.relevance_score : 0.5,
    content: row.content.trim(),
    createdAt: row.created_at.trim(),
  };
}

export function createMidZone(adapter: MidZoneSqliteAdapter): MidZone {
  return {
    load: (scope: { sessionId?: string; maxResults?: number } = {}) => {
      let query = "SELECT id, session_id, conversation_id, content, created_at, relevance_score FROM personal_facts WHERE zone = 'mid'";
      const params: unknown[] = [];
      
      if (scope.sessionId) {
        query += " AND session_id = ?";
        params.push(scope.sessionId);
      }
      
      query += " ORDER BY relevance_score DESC, created_at DESC";
      
      if (scope.maxResults && scope.maxResults > 0) {
        query += " LIMIT ?";
        params.push(scope.maxResults);
      }
      
      const rows = adapter.all(query, params);
      return Object.freeze(
        rows.map(normalizeRowToEntry).filter((e): e is MidZoneEntry => e !== null)
      );
    },

    promoteFromHot: (sessionId: string) => {
      const result = adapter.run(
        "UPDATE personal_facts SET zone = 'mid', relevance_score = 0.8 WHERE zone = 'hot' AND session_id = ?",
        [sessionId]
      );
      return typeof result?.changes === "number" ? result.changes : 0;
    },

    demoteToCold: (sessionIds: ReadonlyArray<string>) => {
      if (sessionIds.length === 0) return 0;
      
      const placeholders = sessionIds.map(() => "?").join(",");
      const result = adapter.run(
        `UPDATE personal_facts SET zone = 'cold', relevance_score = 0.3 WHERE zone = 'mid' AND session_id IN (${placeholders})`,
        [...sessionIds]
      );
      return typeof result?.changes === "number" ? result.changes : 0;
    },
  };
}
