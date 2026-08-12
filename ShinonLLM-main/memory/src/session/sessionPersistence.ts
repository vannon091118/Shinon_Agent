export type PersistedSessionMemoryEntry = Readonly<{
  id: string;
  sessionId: string;
  conversationId: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: string;
  expiresAt?: string;
  metadata?: Readonly<Record<string, unknown>>;
}>;

export type SessionMemoryScope = Readonly<{
  sessionId: string;
  conversationId: string;
  limit?: number;
}>;

export type SessionMemoryAppendInput = Readonly<{
  sessionId: string;
  conversationId: string;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt?: string;
  ttlSeconds?: number;
  metadata?: Readonly<Record<string, unknown>>;
}>;

export type SessionMemoryDecayInput = Readonly<{
  now?: string;
  keepLatestPerConversation?: number;
}>;

export type SessionMemoryPersistence = Readonly<{
  load(scope: SessionMemoryScope): ReadonlyArray<PersistedSessionMemoryEntry>;
  append(entries: ReadonlyArray<SessionMemoryAppendInput>): number;
  decay(input?: SessionMemoryDecayInput): number;
  getConceptFrequencies?(scope: { conversationId?: string; sessionId?: string }): Record<string, number>;
}>;

export type SessionMemorySqliteAdapter = Readonly<{
  run: (sql: string, params?: ReadonlyArray<unknown>) => { changes?: number } | void;
  all: (sql: string, params?: ReadonlyArray<unknown>) => ReadonlyArray<Record<string, unknown>>;
}>;

const DEFAULT_LIMIT = 64;
const DEFAULT_KEEP_LATEST = 128;
const SQLITE_SCHEMA_VERSION = 2;

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function toIsoNow(): string {
  return new Date().toISOString();
}

function failClosed(message: string): never {
  throw {
    code: "BAD_REQUEST",
    message,
  };
}

function normalizeLimit(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return DEFAULT_LIMIT;
  }
  const normalized = Math.floor(value);
  return normalized > 0 ? normalized : DEFAULT_LIMIT;
}

function normalizeKeepLatest(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return DEFAULT_KEEP_LATEST;
  }
  const normalized = Math.floor(value);
  return normalized > 0 ? normalized : DEFAULT_KEEP_LATEST;
}

function createEntryId(seed: string): string {
  let hash = 2166136261;
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `mem_${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

function normalizeScope(scope: SessionMemoryScope): SessionMemoryScope {
  if (!isPlainObject(scope)) {
    failClosed("session memory scope must be a plain object");
  }
  if (!isNonEmptyString(scope.sessionId)) {
    failClosed("session memory scope.sessionId must be a non-empty string");
  }
  if (!isNonEmptyString(scope.conversationId)) {
    failClosed("session memory scope.conversationId must be a non-empty string");
  }

  return Object.freeze({
    sessionId: scope.sessionId.trim(),
    conversationId: scope.conversationId.trim(),
    limit: normalizeLimit(scope.limit),
  });
}

function normalizeAppendEntry(entry: SessionMemoryAppendInput): PersistedSessionMemoryEntry {
  if (!isPlainObject(entry)) {
    failClosed("session memory append entries must be plain objects");
  }
  if (!isNonEmptyString(entry.sessionId) || !isNonEmptyString(entry.conversationId)) {
    failClosed("session memory append requires sessionId and conversationId");
  }
  if (entry.role !== "user" && entry.role !== "assistant" && entry.role !== "system") {
    failClosed("session memory append role must be user, assistant, or system");
  }
  if (!isNonEmptyString(entry.content)) {
    failClosed("session memory append content must be a non-empty string");
  }

  const createdAt = isNonEmptyString(entry.createdAt) ? entry.createdAt.trim() : toIsoNow();
  const expiresAt =
    typeof entry.ttlSeconds === "number" && Number.isFinite(entry.ttlSeconds) && entry.ttlSeconds > 0
      ? new Date(new Date(createdAt).getTime() + Math.floor(entry.ttlSeconds * 1000)).toISOString()
      : undefined;
  const metadata = isPlainObject(entry.metadata) ? Object.freeze({ ...entry.metadata }) : undefined;

  const id = createEntryId(
    `${entry.sessionId.trim()}|${entry.conversationId.trim()}|${entry.role}|${entry.content.trim()}|${createdAt}`,
  );

  return Object.freeze({
    id,
    sessionId: entry.sessionId.trim(),
    conversationId: entry.conversationId.trim(),
    role: entry.role,
    content: entry.content.trim(),
    createdAt,
    expiresAt,
    metadata,
  });
}

function normalizePersistedRow(row: Record<string, unknown>): PersistedSessionMemoryEntry | null {
  if (
    !isNonEmptyString(row.id) ||
    !isNonEmptyString(row.session_id) ||
    !isNonEmptyString(row.conversation_id) ||
    !isNonEmptyString(row.role) ||
    !isNonEmptyString(row.content) ||
    !isNonEmptyString(row.created_at)
  ) {
    return null;
  }

  const role = row.role.trim();
  if (role !== "user" && role !== "assistant" && role !== "system") {
    return null;
  }

  let metadata: Readonly<Record<string, unknown>> | undefined;
  if (typeof row.metadata_json === "string" && row.metadata_json.trim().length > 0) {
    try {
      const parsed = JSON.parse(row.metadata_json);
      if (isPlainObject(parsed)) {
        metadata = Object.freeze({ ...parsed });
      }
    } catch {
      metadata = undefined;
    }
  }

  return Object.freeze({
    id: row.id.trim(),
    sessionId: row.session_id.trim(),
    conversationId: row.conversation_id.trim(),
    role,
    content: row.content.trim(),
    createdAt: row.created_at.trim(),
    expiresAt: isNonEmptyString(row.expires_at) ? row.expires_at.trim() : undefined,
    metadata,
  });
}

function normalizeSqliteUserVersion(value: unknown): number {
  if (typeof value === "number" && Number.isInteger(value) && value >= 0) {
    return value;
  }
  if (typeof value === "bigint") {
    return value >= 0n ? Number(value) : -1;
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number.parseInt(value.trim(), 10);
    if (Number.isInteger(parsed) && parsed >= 0) {
      return parsed;
    }
  }
  return -1;
}

export function createInMemorySessionMemoryPersistence(
  initialEntries: ReadonlyArray<SessionMemoryAppendInput> = [],
): SessionMemoryPersistence {
  let entries = initialEntries.map(normalizeAppendEntry);

  return Object.freeze({
    load(scope: SessionMemoryScope): ReadonlyArray<PersistedSessionMemoryEntry> {
      const normalized = normalizeScope(scope);
      return Object.freeze(
        entries
          .filter(
            (entry) =>
              entry.sessionId === normalized.sessionId &&
              entry.conversationId === normalized.conversationId,
          )
          .slice(-normalized.limit!),
      );
    },
    append(nextEntries: ReadonlyArray<SessionMemoryAppendInput>): number {
      if (!Array.isArray(nextEntries)) {
        failClosed("session memory append input must be an array");
      }
      const normalized = nextEntries.map(normalizeAppendEntry);
      entries = [...entries, ...normalized];
      return normalized.length;
    },
    decay(input: SessionMemoryDecayInput = {}): number {
      const now = isNonEmptyString(input.now) ? input.now.trim() : toIsoNow();
      const keepLatestPerConversation = normalizeKeepLatest(input.keepLatestPerConversation);
      const before = entries.length;

      const grouped = new Map<string, PersistedSessionMemoryEntry[]>();
      for (const entry of entries) {
        const key = `${entry.sessionId}|${entry.conversationId}`;
        const group = grouped.get(key) ?? [];
        group.push(entry);
        grouped.set(key, group);
      }

      const retained: PersistedSessionMemoryEntry[] = [];
      for (const group of grouped.values()) {
        const notExpired = group.filter((entry) => !entry.expiresAt || entry.expiresAt > now);
        retained.push(...notExpired.slice(-keepLatestPerConversation));
      }

      entries = retained;
      return Math.max(0, before - entries.length);
    },
  });
}

function createSqliteSchemaV2(adapter: SessionMemorySqliteAdapter): void {
  // Personal Facts (Tier 1) - konkrete Ereignisse, Zitate, Präferenzen
  adapter.run(
    [
      "CREATE TABLE IF NOT EXISTS personal_facts (",
      "  id TEXT PRIMARY KEY,",
      "  content TEXT NOT NULL,",
      "  category TEXT NOT NULL,", // preference, event, commitment, relationship
      "  session_id TEXT NOT NULL,",
      "  conversation_id TEXT NOT NULL,",
      "  created_at TEXT NOT NULL,",
      "  zone TEXT DEFAULT 'hot',", // hot, mid, cold
      "  relevance_score REAL DEFAULT 0.5,",
      "  metadata_json TEXT",
      ");",
    ].join("\n"),
  );
  adapter.run(
    "CREATE INDEX IF NOT EXISTS idx_personal_facts_session ON personal_facts(session_id, conversation_id, zone);",
  );
  adapter.run(
    "CREATE INDEX IF NOT EXISTS idx_personal_facts_score ON personal_facts(zone, relevance_score DESC);",
  );

  // Patterns (Tier 2) - generalisierte Muster mit Konfidenz
  adapter.run(
    [
      "CREATE TABLE IF NOT EXISTS patterns (",
      "  id TEXT PRIMARY KEY,",
      "  anchor TEXT NOT NULL UNIQUE,", // z.B. "user-beziehung-anna"
      "  type TEXT NOT NULL,", // preference, relationship
      "  confidence REAL NOT NULL DEFAULT 0.0,",
      "  examples_json TEXT NOT NULL,", // Array von {factId, content, date}
      "  first_seen TEXT NOT NULL,",
      "  last_reinforced TEXT NOT NULL,",
      "  reinforcement_count INTEGER DEFAULT 1,",
      "  metadata_json TEXT",
      ");",
    ].join("\n"),
  );
  adapter.run(
    "CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(type, confidence DESC);",
  );

  // Pattern Links - Verknüpfung Tier 1 ↔ Tier 2
  adapter.run(
    [
      "CREATE TABLE IF NOT EXISTS pattern_links (",
      "  pattern_id TEXT NOT NULL,",
      "  fact_id TEXT NOT NULL,",
      "  relation_type TEXT NOT NULL,", // supports, contradicts, example_of
      "  created_at TEXT NOT NULL,",
      "  PRIMARY KEY (pattern_id, fact_id),",
      "  FOREIGN KEY (pattern_id) REFERENCES patterns(id) ON DELETE CASCADE,",
      "  FOREIGN KEY (fact_id) REFERENCES personal_facts(id) ON DELETE CASCADE",
      ");",
    ].join("\n"),
  );

  // Attitudes - Haltungs-Tracking pro User
  adapter.run(
    [
      "CREATE TABLE IF NOT EXISTS attitudes (",
      "  user_id TEXT NOT NULL,",
      "  dimension TEXT NOT NULL,", // warmth, respect, patience, trust
      "  score REAL NOT NULL DEFAULT 0.0,", // -10 bis +10
      "  updated_at TEXT NOT NULL,",
      "  history_json TEXT,", // Array von {score, timestamp, trigger}
      "  PRIMARY KEY (user_id, dimension)",
      ");",
    ].join("\n"),
  );
}

function readSqliteUserVersion(adapter: SessionMemorySqliteAdapter): number {
  const rows = adapter.all("PRAGMA user_version");
  const firstRow = rows[0];
  if (!firstRow) {
    failClosed("sqlite user_version could not be read");
  }

  const value =
    firstRow.user_version ??
    firstRow.USER_VERSION ??
    firstRow.User_Version ??
    firstRow.value;

  const normalized = normalizeSqliteUserVersion(value);
  if (normalized < 0) {
    failClosed("sqlite user_version must be a non-negative integer");
  }
  return normalized;
}

function writeSqliteUserVersion(adapter: SessionMemorySqliteAdapter, nextVersion: number): void {
  adapter.run(`PRAGMA user_version = ${nextVersion}`);
}

function createSqliteSchemaV1(adapter: SessionMemorySqliteAdapter): void {
  adapter.run(
    [
      "CREATE TABLE IF NOT EXISTS session_memory_entries (",
      "  id TEXT PRIMARY KEY,",
      "  session_id TEXT NOT NULL,",
      "  conversation_id TEXT NOT NULL,",
      "  role TEXT NOT NULL,",
      "  content TEXT NOT NULL,",
      "  created_at TEXT NOT NULL,",
      "  expires_at TEXT,",
      "  metadata_json TEXT",
      ");",
    ].join("\n"),
  );
  adapter.run(
    "CREATE INDEX IF NOT EXISTS idx_session_memory_scope ON session_memory_entries(session_id, conversation_id, created_at);",
  );
  adapter.run(
    "CREATE INDEX IF NOT EXISTS idx_session_memory_expiry ON session_memory_entries(expires_at);",
  );
}

function migrateV1ToV2(adapter: SessionMemorySqliteAdapter): void {
  // Migration: Session-Einträge → Personal Facts
  const sessionEntries = adapter.all(
    "SELECT id, session_id, conversation_id, content, created_at, metadata_json FROM session_memory_entries WHERE role = 'user'",
  );
  
  for (const row of sessionEntries) {
    if (
      typeof row.id === "string" &&
      typeof row.session_id === "string" &&
      typeof row.conversation_id === "string" &&
      typeof row.content === "string" &&
      typeof row.created_at === "string"
    ) {
      adapter.run(
        [
          "INSERT OR IGNORE INTO personal_facts",
          "(id, content, category, session_id, conversation_id, created_at, zone, relevance_score)",
          "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ].join("\n"),
        [
          `fact_${row.id}`,
          row.content,
          "event",
          row.session_id,
          row.conversation_id,
          row.created_at,
          "hot",
          0.5,
        ],
      );
    }
  }
}

function ensureSqliteSchema(adapter: SessionMemorySqliteAdapter): void {
  const currentVersion = readSqliteUserVersion(adapter);
  if (currentVersion > SQLITE_SCHEMA_VERSION) {
    failClosed(
      `sqlite schema version ${currentVersion} is newer than supported version ${SQLITE_SCHEMA_VERSION}`,
    );
  }

  if (currentVersion === 0) {
    createSqliteSchemaV1(adapter);
    createSqliteSchemaV2(adapter); // Create v2 tables directly for fresh installs
    writeSqliteUserVersion(adapter, 2);
    return;
  }

  if (currentVersion === 1) {
    createSqliteSchemaV2(adapter);
    migrateV1ToV2(adapter);
    writeSqliteUserVersion(adapter, 2);
    return;
  }

  if (currentVersion === 2) {
    return;
  }

  failClosed(`sqlite schema version ${currentVersion} is unknown`);
}

/**
 * Constructs a SQLite-backed SessionMemoryPersistence implementation.
 *
 * @param adapter - SQLite adapter providing `run(sql, params?)` and `all(sql, params?)` for executing queries.
 * @returns A persistence object that implements `load`, `append`, `decay`, and `getConceptFrequencies`, storing session memory entries in a SQLite table.
 * @throws If `adapter` is not a plain object with `run` and `all` functions, or if schema creation/verification fails.
 */
export function createSqliteSessionMemoryPersistence(
  adapter: SessionMemorySqliteAdapter,
): SessionMemoryPersistence {
  if (!isPlainObject(adapter) || typeof adapter.run !== "function" || typeof adapter.all !== "function") {
    failClosed("sqlite session memory adapter requires run() and all()");
  }

  ensureSqliteSchema(adapter);

  return Object.freeze({
    load(scope: SessionMemoryScope): ReadonlyArray<PersistedSessionMemoryEntry> {
      const normalized = normalizeScope(scope);
      const rows = adapter.all(
        [
          "SELECT id, session_id, conversation_id, role, content, created_at, expires_at, metadata_json",
          "FROM session_memory_entries",
          "WHERE session_id = ? AND conversation_id = ?",
          "ORDER BY created_at ASC",
          "LIMIT ?",
        ].join("\n"),
        [normalized.sessionId, normalized.conversationId, normalized.limit ?? DEFAULT_LIMIT],
      );

      const normalizedRows = rows
        .map((row) => normalizePersistedRow(row))
        .filter((entry): entry is PersistedSessionMemoryEntry => entry !== null);
      return Object.freeze(normalizedRows);
    },
    append(nextEntries: ReadonlyArray<SessionMemoryAppendInput>): number {
      if (!Array.isArray(nextEntries)) {
        failClosed("session memory append input must be an array");
      }
      let inserted = 0;
      for (const item of nextEntries) {
        const entry = normalizeAppendEntry(item);
        const result = adapter.run(
          [
            "INSERT OR REPLACE INTO session_memory_entries",
            "(id, session_id, conversation_id, role, content, created_at, expires_at, metadata_json)",
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
          ].join("\n"),
          [
            entry.id,
            entry.sessionId,
            entry.conversationId,
            entry.role,
            entry.content,
            entry.createdAt,
            entry.expiresAt ?? null,
            entry.metadata ? JSON.stringify(entry.metadata) : null,
          ],
        );
        inserted += typeof result?.changes === "number" ? Math.max(0, result.changes) : 1;
      }
      return inserted;
    },
    decay(input: SessionMemoryDecayInput = {}): number {
      const now = isNonEmptyString(input.now) ? input.now.trim() : toIsoNow();
      const keepLatestPerConversation = normalizeKeepLatest(input.keepLatestPerConversation);

      const expireResult = adapter.run(
        "DELETE FROM session_memory_entries WHERE expires_at IS NOT NULL AND expires_at <= ?",
        [now],
      );

      adapter.run(
        [
          "DELETE FROM session_memory_entries",
          "WHERE id IN (",
          "  SELECT id FROM (",
          "    SELECT id, ROW_NUMBER() OVER (PARTITION BY session_id, conversation_id ORDER BY created_at DESC) AS rn",
          "    FROM session_memory_entries",
          "  ) ranked",
          "  WHERE rn > ?",
          ")",
        ].join("\n"),
        [keepLatestPerConversation],
      );

      return typeof expireResult?.changes === "number" ? Math.max(0, expireResult.changes) : 0;
    },
    getConceptFrequencies(scope: { conversationId?: string; sessionId?: string } = {}): Record<string, number> {
      let query = "SELECT metadata_json FROM session_memory_entries WHERE role = 'user' AND metadata_json IS NOT NULL";
      const params: string[] = [];
      if (scope.sessionId) {
        query += " AND session_id = ?";
        params.push(scope.sessionId);
      }
      if (scope.conversationId) {
        query += " AND conversation_id = ?";
        params.push(scope.conversationId);
      }
      const rows = adapter.all(query, params);
      const frequencies: Record<string, number> = {};
      for (const row of rows) {
        if (typeof row.metadata_json === "string") {
          try {
            const meta = JSON.parse(row.metadata_json);
            if (Array.isArray(meta.concepts)) {
              for (const concept of meta.concepts) {
                if (typeof concept === "string") {
                  frequencies[concept] = (frequencies[concept] || 0) + 1;
                }
              }
            }
          } catch {
            // ignore
          }
        }
      }
      return frequencies;
    }
  });
}
