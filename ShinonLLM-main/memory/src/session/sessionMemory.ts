import { retrieveContext, type RetrievalContextOutput } from "../retrieval/retrieveContext.js";

type SessionMemoryEntry = Readonly<{
  id?: string;
  type?: string;
  content?: unknown;
  tags?: ReadonlyArray<string>;
  sessionId?: string;
  conversationId?: string;
  updatedAt?: string;
  createdAt?: string;
  timestamp?: string;
  revision?: number;
}>;

type SessionMemoryQuery = Readonly<{
  userText: string;
  sessionId?: string;
  conversationId?: string;
  maxResults?: number;
  maxTokens?: number;
}>;

type SessionMemoryState = Readonly<{
  entries: ReadonlyArray<SessionMemoryEntry>;
  windowSize: number;
  maxResults: number;
  maxTokens: number;
  revision: number;
}>;

type SessionMemoryStoreInput = Readonly<{
  entries?: ReadonlyArray<SessionMemoryEntry>;
  windowSize?: number;
  maxResults?: number;
  maxTokens?: number;
}>;

type SessionMemoryStore = {
  (query: SessionMemoryQuery): RetrievalContextOutput;
  getState: () => SessionMemoryState;
  reset: (nextState?: SessionMemoryStoreInput) => SessionMemoryState;
  update: (patch?: SessionMemoryStoreInput) => SessionMemoryState;
  record: (entryOrEntries: SessionMemoryEntry | ReadonlyArray<SessionMemoryEntry>) => SessionMemoryState;
  window: (query?: Pick<SessionMemoryQuery, "sessionId" | "conversationId">) => ReadonlyArray<SessionMemoryEntry>;
};

const DEFAULT_WINDOW_SIZE = 32;
const DEFAULT_MAX_RESULTS = 12;
const DEFAULT_MAX_TOKENS = 800;

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function failClosed(message: string): never {
  throw {
    code: "BAD_REQUEST",
    message,
  };
}

function toNonEmptyString(value: unknown): string | undefined {
  if (!isNonEmptyString(value)) {
    return undefined;
  }

  return value.trim();
}

function normalizeInteger(value: unknown, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return fallback;
  }

  const normalized = Math.floor(value);
  return normalized > 0 ? normalized : fallback;
}

function stableHash(seed: string): string {
  let hash = 2166136261;
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `sm_${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

function describeValue(value: unknown): string {
  if (typeof value === "string") {
    return value.trim();
  }

  if (
    value === null ||
    value === undefined ||
    typeof value === "number" ||
    typeof value === "boolean" ||
    typeof value === "bigint"
  ) {
    return String(value);
  }

  try {
    return JSON.stringify(value) ?? String(value);
  } catch {
    return String(value);
  }
}

function normalizeTags(tags: unknown): ReadonlyArray<string> | undefined {
  if (!Array.isArray(tags)) {
    return undefined;
  }

  const normalized = tags
    .map((tag) => toNonEmptyString(tag))
    .filter((tag): tag is string => Boolean(tag));

  return normalized.length > 0 ? normalized : undefined;
}

function normalizeEntry(entry: SessionMemoryEntry, revision: number): SessionMemoryEntry {
  if (!isPlainObject(entry)) {
    failClosed("session memory entries must be plain objects");
  }

  const content = entry.content;
  const normalizedId =
    toNonEmptyString(entry.id) ??
    stableHash(
      [
        toNonEmptyString(entry.type) ?? "memory",
        describeValue(content),
        String(revision),
      ].join("|"),
    );

  const tags = normalizeTags(entry.tags);

  return Object.freeze({
    id: normalizedId,
    type: toNonEmptyString(entry.type),
    content,
    tags: tags ? Object.freeze([...tags]) : undefined,
    sessionId: toNonEmptyString(entry.sessionId),
    conversationId: toNonEmptyString(entry.conversationId),
    updatedAt: toNonEmptyString(entry.updatedAt),
    createdAt: toNonEmptyString(entry.createdAt),
    timestamp: toNonEmptyString(entry.timestamp),
    revision,
  });
}

function cloneEntries(entries: ReadonlyArray<SessionMemoryEntry>): SessionMemoryEntry[] {
  return entries.map((entry) =>
    Object.freeze({
      ...entry,
      tags: entry.tags ? Object.freeze([...entry.tags]) : undefined,
    }),
  );
}

function normalizeState(input: SessionMemoryStoreInput | null | undefined = {}): SessionMemoryState {
  if (!isPlainObject(input)) {
    failClosed("session memory store input must be an object");
  }

  const windowSize = normalizeInteger(input.windowSize, DEFAULT_WINDOW_SIZE);
  const maxResults = normalizeInteger(input.maxResults, DEFAULT_MAX_RESULTS);
  const maxTokens = normalizeInteger(input.maxTokens, DEFAULT_MAX_TOKENS);

  const entries = Array.isArray(input.entries)
    ? input.entries.reduce<SessionMemoryEntry[]>((accumulator, entry, index) => {
        if (!isPlainObject(entry)) {
          return accumulator;
        }
        accumulator.push(normalizeEntry(entry, index + 1));
        return accumulator;
      }, [])
    : [];

  return Object.freeze({
    entries: Object.freeze(entries),
    windowSize,
    maxResults,
    maxTokens,
    revision: entries.length,
  });
}

function selectWindow(entries: ReadonlyArray<SessionMemoryEntry>, windowSize: number): SessionMemoryEntry[] {
  const boundedSize = normalizeInteger(windowSize, DEFAULT_WINDOW_SIZE);
  return cloneEntries(entries.slice(-boundedSize));
}

function filterBySession(
  entries: ReadonlyArray<SessionMemoryEntry>,
  query?: Pick<SessionMemoryQuery, "sessionId" | "conversationId">,
): SessionMemoryEntry[] {
  const sessionId = toNonEmptyString(query?.sessionId);
  const conversationId = toNonEmptyString(query?.conversationId);

  return entries.filter((entry) => {
    if (sessionId && entry.sessionId !== sessionId) {
      return false;
    }
    if (conversationId && entry.conversationId !== conversationId) {
      return false;
    }
    return true;
  });
}

function normalizeQuery(query: SessionMemoryQuery): SessionMemoryQuery {
  if (!isPlainObject(query)) {
    failClosed("session memory query must be an object");
  }

  const userText = toNonEmptyString(query.userText);
  if (!userText) {
    failClosed("session memory query requires a non-empty userText");
  }

  return {
    userText,
    sessionId: toNonEmptyString(query.sessionId),
    conversationId: toNonEmptyString(query.conversationId),
    maxResults: normalizeInteger(query.maxResults, DEFAULT_MAX_RESULTS),
    maxTokens: normalizeInteger(query.maxTokens, DEFAULT_MAX_TOKENS),
  };
}

function createBoundedRetriever(getState: () => SessionMemoryState): SessionMemoryStore {
  const retrieve = ((query: SessionMemoryQuery) => {
    const normalizedQuery = normalizeQuery(query);
    const state = getState();
    const scopedEntries = filterBySession(state.entries, normalizedQuery);
    const boundedWindow = selectWindow(scopedEntries, state.windowSize);

    return retrieveContext({
      userText: normalizedQuery.userText,
      memoryContext: boundedWindow,
      maxResults: normalizedQuery.maxResults ?? state.maxResults,
      maxTokens: normalizedQuery.maxTokens ?? state.maxTokens,
    });
  }) as SessionMemoryStore;

  retrieve.getState = getState;
  retrieve.reset = () => {
    failClosed("session memory store is read-only; create a new store to reset state");
  };
  retrieve.update = () => {
    failClosed("session memory store is read-only; create a new store to update state");
  };
  retrieve.record = () => {
    failClosed("session memory store is read-only; create a new store to record entries");
  };
  retrieve.window = (query?: Pick<SessionMemoryQuery, "sessionId" | "conversationId">) => {
    const state = getState();
    return selectWindow(filterBySession(state.entries, query), state.windowSize);
  };

  return retrieve;
}

export function createSessionMemoryStore(
  initialState: SessionMemoryStoreInput = {},
): SessionMemoryStore {
  let state = normalizeState(initialState);

  const readState = (): SessionMemoryState => state;

  const applyEntries = (entries: ReadonlyArray<SessionMemoryEntry>): SessionMemoryState => {
    const normalizedEntries: SessionMemoryEntry[] = [];
    let revision = state.revision;

    for (const entry of entries) {
      if (!isPlainObject(entry)) {
        continue;
      }
      revision += 1;
      normalizedEntries.push(normalizeEntry(entry, revision));
    }

    const merged = [...state.entries, ...normalizedEntries];
    const bounded = selectWindow(merged, state.windowSize);
    state = Object.freeze({
      ...state,
      entries: Object.freeze(bounded),
      revision,
    });
    return state;
  };

  const store = createBoundedRetriever(readState);

  store.getState = () => readState();
  store.reset = (nextState: SessionMemoryStoreInput = {}) => {
    state = normalizeState(nextState);
    return readState();
  };
  store.update = (patch: SessionMemoryStoreInput = {}) => {
    const safePatch = patch ?? {};

    if (!isPlainObject(safePatch)) {
      failClosed("session memory store patch must be an object");
    }

    const nextEntries = Array.isArray(safePatch.entries) ? safePatch.entries : state.entries;

    state = normalizeState({
      entries: nextEntries,
      windowSize: safePatch.windowSize ?? state.windowSize,
      maxResults: safePatch.maxResults ?? state.maxResults,
      maxTokens: safePatch.maxTokens ?? state.maxTokens,
    });
    return readState();
  };
  store.record = (entryOrEntries: SessionMemoryEntry | ReadonlyArray<SessionMemoryEntry>) => {
    const entries = Array.isArray(entryOrEntries) ? entryOrEntries : [entryOrEntries];
    return applyEntries(entries);
  };
  store.window = (query?: Pick<SessionMemoryQuery, "sessionId" | "conversationId">) => {
    const scopedEntries = filterBySession(state.entries, query);
    return selectWindow(scopedEntries, state.windowSize);
  };

  return store;
}
