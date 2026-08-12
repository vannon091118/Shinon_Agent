// Hot Zone - Scope 0.3.0
// Aktuelle Session (ungefilterter Zugriff) mit SQLite Backend

export type HotZoneEntry = {
  readonly id: string;
  readonly sessionId: string;
  readonly conversationId: string;
  readonly role: "user" | "assistant" | "system";
  readonly content: string;
  readonly createdAt: string;
  readonly metadata?: Record<string, unknown>;
};

export type HotZoneSqliteAdapter = Readonly<{
  run: (sql: string, params?: ReadonlyArray<unknown>) => { changes?: number } | void;
  all: (sql: string, params?: ReadonlyArray<unknown>) => ReadonlyArray<Record<string, unknown>>;
}>;

export type HotZone = {
  readonly load: (scope: { sessionId: string; conversationId: string }) => ReadonlyArray<HotZoneEntry>;
  readonly append: (entry: HotZoneEntry) => void;
  readonly onSessionEnd: (callback: () => void) => void;
  readonly transitionToMid: () => number; // Returns count of transitioned entries
};

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeRowToEntry(row: Record<string, unknown>): HotZoneEntry | null {
  if (!isNonEmptyString(row.id) || !isNonEmptyString(row.session_id) || 
      !isNonEmptyString(row.conversation_id) || !isNonEmptyString(row.role) || 
      !isNonEmptyString(row.content) || !isNonEmptyString(row.created_at)) {
    return null;
  }
  const role = row.role.trim();
  if (role !== "user" && role !== "assistant" && role !== "system") {
    return null;
  }
  let metadata: Record<string, unknown> | undefined;
  if (typeof row.metadata_json === "string" && row.metadata_json.trim().length > 0) {
    try {
      metadata = JSON.parse(row.metadata_json);
    } catch {
      // ignore
    }
  }
  return {
    id: row.id.trim(),
    sessionId: row.session_id.trim(),
    conversationId: row.conversation_id.trim(),
    role,
    content: row.content.trim(),
    createdAt: row.created_at.trim(),
    metadata,
  };
}

export function createHotZone(adapter: HotZoneSqliteAdapter): HotZone {
  const sessionEndCallbacks: Array<() => void> = [];

  return {
    load: (scope: { sessionId: string; conversationId: string }) => {
      const rows = adapter.all(
        "SELECT id, session_id, conversation_id, role, content, created_at, metadata_json FROM personal_facts WHERE session_id = ? AND conversation_id = ? AND zone = 'hot' ORDER BY created_at ASC",
        [scope.sessionId, scope.conversationId]
      );
      return Object.freeze(
        rows.map(normalizeRowToEntry).filter((e): e is HotZoneEntry => e !== null)
      );
    },

    append: (entry: HotZoneEntry) => {
      adapter.run(
        "INSERT OR REPLACE INTO personal_facts (id, content, category, session_id, conversation_id, created_at, zone, relevance_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
          entry.id,
          entry.content,
          entry.role === "user" ? "event" : "response",
          entry.sessionId,
          entry.conversationId,
          entry.createdAt,
          "hot",
          1.0,
        ]
      );
    },

    onSessionEnd: (callback: () => void) => {
      sessionEndCallbacks.push(callback);
    },

    transitionToMid: () => {
      // Move all hot entries to mid zone
      const result = adapter.run(
        "UPDATE personal_facts SET zone = 'mid', relevance_score = 0.8 WHERE zone = 'hot'"
      );
      // Notify callbacks
      sessionEndCallbacks.forEach((cb) => cb());
      return typeof result?.changes === "number" ? result.changes : 0;
    },
  };
}
