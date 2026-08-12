import { sha256Hex } from "../../../shared/src/utils/hash.js";
import { stableJson } from "../../../shared/src/utils/stableJson.js";
import { scoreContext, type ScoreContextCandidate } from "../retrieval/scoreContext.js";

export type LongTermMemorySqliteAdapter = Readonly<{
  run: (sql: string, params?: ReadonlyArray<unknown>) => { changes?: number } | void;
  all: (sql: string, params?: ReadonlyArray<unknown>) => ReadonlyArray<Record<string, unknown>>;
}>;

export type LongTermMemoryEntry = {
  id?: string;
  type?: string;
  content?: unknown;
  tags?: readonly string[];
  updatedAt?: string;
  createdAt?: string;
  timestamp?: string;
};

export type LongTermMemoryRetrievalInput = {
  query: string;
  entries: readonly LongTermMemoryEntry[];
  maxResults?: number;
  maxTokens?: number;
};

export type LongTermMemoryRetrievedEntry = {
  id?: string;
  type?: string;
  content: string;
  tags?: readonly string[];
  score: number;
};

export type LongTermMemoryRetrievalOutput = {
  query: string;
  entries: ReadonlyArray<LongTermMemoryRetrievedEntry>;
  tokenBudget: number;
  usedTokens: number;
  truncated: boolean;
};

export type LongTermMemoryStoreInput = {
  entries?: readonly LongTermMemoryEntry[];
  seedEntries?: readonly LongTermMemoryEntry[];
};

export type LongTermMemoryStoreSnapshot = {
  entries: ReadonlyArray<LongTermMemoryEntry & { integrityHash: string }>;
};

export type LongTermMemoryStore = {
  snapshot: () => LongTermMemoryStoreSnapshot;
  upsert: (entry: LongTermMemoryEntry) => LongTermMemoryStoreSnapshot;
  ingest: (entries: readonly LongTermMemoryEntry[]) => LongTermMemoryStoreSnapshot;
  retrieve: (input: LongTermMemoryRetrievalInput) => LongTermMemoryRetrievalOutput;
};

type LongTermMemoryStoreState = {
  entries: Array<LongTermMemoryEntry & { integrityHash: string }>;
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isRetrievalInput(value: unknown): value is LongTermMemoryRetrievalInput {
  return isPlainObject(value) && isNonEmptyString(value.query) && Array.isArray(value.entries);
}

function tokenize(value: string): string[] {
  return value.toLowerCase().match(/[a-z0-9]+/gu) ?? [];
}

function estimateTokens(value: string): number {
  const tokens = tokenize(value);
  return Math.max(1, Math.ceil(tokens.length * 1.25));
}

function toText(value: unknown): string {
  if (isNonEmptyString(value)) {
    return value.trim();
  }

  if (value === null || value === undefined) {
    return "";
  }

  if (Array.isArray(value)) {
    return value.map(toText).filter(Boolean).join("\n");
  }

  if (isPlainObject(value)) {
    if (isNonEmptyString(value.content)) {
      return value.content.trim();
    }
    if (isNonEmptyString(value.text)) {
      return value.text.trim();
    }
    if (isNonEmptyString(value.message)) {
      return value.message.trim();
    }
  }

  return String(value);
}

function normalizeEntry(entry: LongTermMemoryEntry, index: number): LongTermMemoryEntry & { integrityHash: string } {
  const content = entry.content ?? "";
  const integrityHash = sha256Hex({
    id: isNonEmptyString(entry.id) ? entry.id.trim() : "",
    type: isNonEmptyString(entry.type) ? entry.type.trim() : "",
    content: stableJson(content),
    tags: Array.isArray(entry.tags) ? [...entry.tags] : [],
    updatedAt: isNonEmptyString(entry.updatedAt) ? entry.updatedAt.trim() : "",
    createdAt: isNonEmptyString(entry.createdAt) ? entry.createdAt.trim() : "",
    timestamp: isNonEmptyString(entry.timestamp) ? entry.timestamp.trim() : "",
    index,
  });

  return {
    ...(isNonEmptyString(entry.id) ? { id: entry.id.trim() } : {}),
    ...(isNonEmptyString(entry.type) ? { type: entry.type.trim() } : {}),
    content,
    ...(Array.isArray(entry.tags) ? { tags: entry.tags.filter(isNonEmptyString) } : {}),
    ...(isNonEmptyString(entry.updatedAt) ? { updatedAt: entry.updatedAt.trim() } : {}),
    ...(isNonEmptyString(entry.createdAt) ? { createdAt: entry.createdAt.trim() } : {}),
    ...(isNonEmptyString(entry.timestamp) ? { timestamp: entry.timestamp.trim() } : {}),
    integrityHash,
  };
}

function cloneSnapshot(state: LongTermMemoryStoreState): LongTermMemoryStoreSnapshot {
  return {
    entries: state.entries.map((entry) => ({ ...entry, tags: entry.tags ? [...entry.tags] : undefined })),
  };
}

function collectCandidates(entries: readonly LongTermMemoryEntry[]): ScoreContextCandidate[] {
  return entries.map((entry) => ({
    id: entry.id,
    type: entry.type,
    content: entry.content,
    tags: entry.tags,
    updatedAt: entry.updatedAt,
    createdAt: entry.createdAt,
    timestamp: entry.timestamp,
  }));
}

function retrieveFromEntries(
  entries: readonly LongTermMemoryEntry[],
  input: Omit<LongTermMemoryRetrievalInput, "entries">
): LongTermMemoryRetrievalOutput {
  if (!isNonEmptyString(input.query)) {
    throw {
      code: "BAD_REQUEST",
      message: "createLongTermMemoryStore requires a non-empty query for retrieval",
    };
  }

  const tokenBudget = Number.isFinite(input.maxTokens) && input.maxTokens && input.maxTokens > 0
    ? Math.floor(input.maxTokens)
    : 800;
  const maxResults = Number.isFinite(input.maxResults) && input.maxResults && input.maxResults > 0
    ? Math.floor(input.maxResults)
    : 12;

  const ranked = scoreContext({
    userText: input.query,
    candidates: collectCandidates(entries),
    maxResults,
  });

  const selected: LongTermMemoryRetrievedEntry[] = [];
  let usedTokens = 0;

  for (const item of ranked) {
    const content = toText(item.candidate.content);
    if (!content) {
      continue;
    }

    const chunkTokens = estimateTokens(content);
    if (usedTokens + chunkTokens > tokenBudget) {
      break;
    }

    selected.push({
      id: item.candidate.id,
      type: item.candidate.type,
      content,
      tags: item.candidate.tags,
      score: item.score,
    });
    usedTokens += chunkTokens;
  }

  return {
    query: input.query.trim(),
    entries: selected,
    tokenBudget,
    usedTokens,
    truncated: selected.length < ranked.length,
  };
}

function initializeState(input: LongTermMemoryStoreInput = {}): LongTermMemoryStoreState {
  const source = input.entries ?? input.seedEntries ?? [];
  return {
    entries: source.map((entry, index) => normalizeEntry(entry, index)),
  };
}

function upsertIntoState(state: LongTermMemoryStoreState, entry: LongTermMemoryEntry): LongTermMemoryStoreState {
  const nextEntry = normalizeEntry(entry, state.entries.length);
  const nextEntries = state.entries.filter((item) => {
    if (isNonEmptyString(nextEntry.id) && isNonEmptyString(item.id)) {
      return item.id !== nextEntry.id;
    }

    return item.integrityHash !== nextEntry.integrityHash;
  });

  return {
    entries: [...nextEntries, nextEntry],
  };
}

export function createLongTermMemoryStore(
  input: LongTermMemoryStoreInput | LongTermMemoryRetrievalInput = {}
): LongTermMemoryStore | LongTermMemoryRetrievalOutput {
  if (isRetrievalInput(input)) {
    return retrieveFromEntries(input.entries, {
      query: input.query,
      maxResults: input.maxResults,
      maxTokens: input.maxTokens,
    });
  }

  let state = initializeState(input as LongTermMemoryStoreInput);

  return {
    snapshot: () => cloneSnapshot(state),
    upsert: (entry: LongTermMemoryEntry) => {
      state = upsertIntoState(state, entry);
      return cloneSnapshot(state);
    },
    ingest: (entries: readonly LongTermMemoryEntry[]) => {
      for (const entry of entries) {
        state = upsertIntoState(state, entry);
      }
      return cloneSnapshot(state);
    },
    retrieve: (retrievalInput: LongTermMemoryRetrievalInput) =>
      retrieveFromEntries(state.entries, {
        query: retrievalInput.query,
        maxResults: retrievalInput.maxResults,
        maxTokens: retrievalInput.maxTokens,
      }),
  };
}

function normalizeEntryToFact(entry: LongTermMemoryEntry, index: number): {
  id: string;
  content: string;
  type: string;
  integrityHash: string;
  tags?: string[];
} {
  const content = toText(entry.content);
  const id = isNonEmptyString(entry.id) ? entry.id.trim() : `mem_${index}`;
  const type = isNonEmptyString(entry.type) ? entry.type.trim() : "fact";
  const integrityHash = sha256Hex({
    id,
    type,
    content: stableJson(content),
    tags: Array.isArray(entry.tags) ? [...entry.tags] : [],
    index,
  });
  return {
    id,
    content,
    type,
    integrityHash,
    ...(Array.isArray(entry.tags) ? { tags: entry.tags.filter(isNonEmptyString) } : {}),
  };
}

function rowToEntry(row: Record<string, unknown>): LongTermMemoryEntry & { integrityHash: string } | null {
  if (!isNonEmptyString(row.id) || !isNonEmptyString(row.content)) {
    return null;
  }
  const integrityHash = isNonEmptyString(row.integrity_hash) ? row.integrity_hash.trim() : "";
  let tags: string[] | undefined;
  if (typeof row.tags_json === "string" && row.tags_json.trim().length > 0) {
    try {
      const parsed = JSON.parse(row.tags_json);
      if (Array.isArray(parsed)) {
        tags = parsed.filter(isNonEmptyString);
      }
    } catch {
      // ignore
    }
  }
  return {
    id: row.id.trim(),
    type: isNonEmptyString(row.type) ? row.type.trim() : undefined,
    content: row.content.trim(),
    ...(tags ? { tags } : {}),
    createdAt: isNonEmptyString(row.created_at) ? row.created_at.trim() : undefined,
    integrityHash,
  };
}

export function createSqliteLongTermMemoryStore(
  adapter: LongTermMemorySqliteAdapter
): LongTermMemoryStore {
  if (!isPlainObject(adapter) || typeof adapter.run !== "function" || typeof adapter.all !== "function") {
    throw {
      code: "BAD_REQUEST",
      message: "sqlite long-term memory adapter requires run() and all()",
    };
  }

  return {
    snapshot: (): LongTermMemoryStoreSnapshot => {
      const rows = adapter.all(
        "SELECT id, type, content, tags_json, created_at, integrity_hash FROM personal_facts ORDER BY created_at DESC LIMIT 1000"
      );
      const entries = rows
        .map((row) => rowToEntry(row))
        .filter((entry): entry is LongTermMemoryEntry & { integrityHash: string } => entry !== null);
      return { entries };
    },

    upsert: (entry: LongTermMemoryEntry): LongTermMemoryStoreSnapshot => {
      const normalized = normalizeEntryToFact(entry, Date.now());
      const now = new Date().toISOString();
      adapter.run(
        [
          "INSERT OR REPLACE INTO personal_facts",
          "(id, content, category, session_id, conversation_id, created_at, zone, relevance_score, metadata_json)",
          "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ].join("\n"),
        [
          normalized.id,
          normalized.content,
          normalized.type,
          "default",
          "default",
          now,
          "hot",
          0.5,
          JSON.stringify({ integrityHash: normalized.integrityHash, tags: normalized.tags }),
        ]
      );
      return createSqliteLongTermMemoryStore(adapter).snapshot();
    },

    ingest: (entries: readonly LongTermMemoryEntry[]): LongTermMemoryStoreSnapshot => {
      const now = new Date().toISOString();
      for (let i = 0; i < entries.length; i++) {
        const normalized = normalizeEntryToFact(entries[i], i);
        adapter.run(
          [
            "INSERT OR REPLACE INTO personal_facts",
            "(id, content, category, session_id, conversation_id, created_at, zone, relevance_score, metadata_json)",
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
          ].join("\n"),
          [
            normalized.id,
            normalized.content,
            normalized.type,
            "default",
            "default",
            now,
            "hot",
            0.5,
            JSON.stringify({ integrityHash: normalized.integrityHash, tags: normalized.tags }),
          ]
        );
      }
      return createSqliteLongTermMemoryStore(adapter).snapshot();
    },

    retrieve: (input: LongTermMemoryRetrievalInput): LongTermMemoryRetrievalOutput => {
      if (!isNonEmptyString(input.query)) {
        throw {
          code: "BAD_REQUEST",
          message: "createSqliteLongTermMemoryStore requires a non-empty query for retrieval",
        };
      }

      const tokenBudget = Number.isFinite(input.maxTokens) && input.maxTokens && input.maxTokens > 0
        ? Math.floor(input.maxTokens)
        : 800;
      const maxResults = Number.isFinite(input.maxResults) && input.maxResults && input.maxResults > 0
        ? Math.floor(input.maxResults)
        : 12;

      // Load entries from SQLite for scoring
      const rows = adapter.all(
        "SELECT id, type, content, tags_json, created_at, integrity_hash FROM personal_facts WHERE zone = 'hot' OR zone = 'mid' ORDER BY created_at DESC LIMIT ?",
        [maxResults * 2]
      );
      const entries = rows
        .map((row) => rowToEntry(row))
        .filter((entry): entry is LongTermMemoryEntry & { integrityHash: string } => entry !== null);

      const ranked = scoreContext({
        userText: input.query,
        candidates: entries.map((e) => ({
          id: e.id,
          type: e.type,
          content: e.content,
          tags: e.tags,
          createdAt: e.createdAt,
        })),
        maxResults,
      });

      const selected: LongTermMemoryRetrievedEntry[] = [];
      let usedTokens = 0;

      for (const item of ranked) {
        const content = toText(item.candidate.content);
        if (!content) continue;

        const chunkTokens = estimateTokens(content);
        if (usedTokens + chunkTokens > tokenBudget) break;

        selected.push({
          id: item.candidate.id,
          type: item.candidate.type,
          content,
          tags: item.candidate.tags,
          score: item.score,
        });
        usedTokens += chunkTokens;
      }

      return {
        query: input.query.trim(),
        entries: selected,
        tokenBudget,
        usedTokens,
        truncated: selected.length < ranked.length,
      };
    },
  };
}
