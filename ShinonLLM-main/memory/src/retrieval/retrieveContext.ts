import { scoreContext, type ScoreContextCandidate } from "./scoreContext.js";

export type RetrievalContextInput = {
  userText: string;
  memoryContext: unknown;
  maxResults?: number;
  maxTokens?: number;
};

export type RetrievedContextEntry = {
  id?: string;
  type?: string;
  content: string;
  tags?: readonly string[];
  score: number;
};

export type RetrievalContextOutput = {
  query: string;
  entries: ReadonlyArray<RetrievedContextEntry>;
  tokenBudget: number;
  usedTokens: number;
  truncated: boolean;
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function tokenize(value: string): string[] {
  return value
    .toLowerCase()
    .match(/[a-z0-9]+/gu) ?? [];
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

function collectCandidates(memoryContext: unknown): ScoreContextCandidate[] {
  if (Array.isArray(memoryContext)) {
    return memoryContext.filter(isPlainObject) as ScoreContextCandidate[];
  }

  if (!isPlainObject(memoryContext)) {
    return [];
  }

  const candidates = memoryContext.entries ?? memoryContext.items ?? memoryContext.context ?? memoryContext.memory;
  if (Array.isArray(candidates)) {
    return candidates.filter(isPlainObject) as ScoreContextCandidate[];
  }

  return [];
}

export function retrieveContext(input: RetrievalContextInput): RetrievalContextOutput {
  if (!input || typeof input !== "object") {
    throw {
      code: "BAD_REQUEST",
      message: "retrieveContext requires a deterministic retrieval input",
    };
  }

  if (!isNonEmptyString(input.userText)) {
    throw {
      code: "BAD_REQUEST",
      message: "retrieveContext requires a non-empty userText",
    };
  }

  if (input.memoryContext !== null && !Array.isArray(input.memoryContext) && !isPlainObject(input.memoryContext)) {
    throw {
      code: "BAD_REQUEST",
      message: "retrieveContext requires object or array memory context",
    };
  }

  const tokenBudget = Number.isFinite(input.maxTokens) && input.maxTokens && input.maxTokens > 0
    ? Math.floor(input.maxTokens)
    : 800;
  const maxResults = Number.isFinite(input.maxResults) && input.maxResults && input.maxResults > 0
    ? Math.floor(input.maxResults)
    : 12;
  const candidates = collectCandidates(input.memoryContext);
  const ranked = scoreContext({
    userText: input.userText,
    candidates,
    maxResults,
  });

  const entries: RetrievedContextEntry[] = [];
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

    entries.push({
      id: item.candidate.id,
      type: item.candidate.type,
      content,
      tags: item.candidate.tags,
      score: item.score,
    });
    usedTokens += chunkTokens;
  }

  return {
    query: input.userText.trim(),
    entries,
    tokenBudget,
    usedTokens,
    truncated: entries.length < ranked.length,
  };
}
