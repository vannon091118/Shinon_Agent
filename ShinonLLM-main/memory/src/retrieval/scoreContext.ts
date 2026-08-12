import { stableJson } from "../../../shared/src/utils/stableJson.js";

export type ScoreContextCandidate = {
  id?: string;
  type?: string;
  content?: unknown;
  tags?: readonly string[];
  updatedAt?: string;
  createdAt?: string;
  timestamp?: string;
};

export type ScoreContextInput = {
  userText: string;
  candidates: readonly ScoreContextCandidate[];
  maxResults?: number;
};

export type ScoredContextCandidate = {
  candidate: ScoreContextCandidate;
  index: number;
  score: number;
};

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function tokenize(value: string): string[] {
  return value
    .toLowerCase()
    .match(/[a-z0-9]+/gu) ?? [];
}

function extractText(candidate: ScoreContextCandidate): string {
  if (isNonEmptyString(candidate.content)) {
    return candidate.content.trim();
  }

  if (candidate.content === null || candidate.content === undefined) {
    return "";
  }

  return stableJson(candidate.content);
}

function readRecency(candidate: ScoreContextCandidate): number {
  const value = candidate.updatedAt ?? candidate.timestamp ?? candidate.createdAt;
  if (!isNonEmptyString(value)) {
    return 0;
  }

  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return 0;
  }

  return parsed;
}

function scoreCandidate(userTokens: readonly string[], candidate: ScoreContextCandidate, index: number): number {
  const candidateText = extractText(candidate);
  const candidateTokens = tokenize(candidateText);
  const tokenSet = new Set(candidateTokens);
  const tagSet = new Set((candidate.tags ?? []).map((tag) => tag.toLowerCase()));

  let overlap = 0;
  for (const token of userTokens) {
    if (tokenSet.has(token) || tagSet.has(token)) {
      overlap += 1;
    }
  }

  const relevance = userTokens.length > 0 ? overlap / userTokens.length : 0;
  const intentMatch = overlap > 0 ? 1 : 0;
  const recency = readRecency(candidate) / 1_000_000_000_000;
  const structural = isNonEmptyString(candidate.id) || isNonEmptyString(candidate.type) ? 0.05 : 0;

  return relevance * 0.7 + intentMatch * 0.2 + recency * 0.05 + structural + (1 / (index + 1)) * 0.01;
}

export function scoreContext(input: ScoreContextInput): ScoredContextCandidate[] {
  if (!input || typeof input !== "object") {
    throw {
      code: "BAD_REQUEST",
      message: "scoreContext requires a deterministic scoring input",
    };
  }

  if (!isNonEmptyString(input.userText)) {
    throw {
      code: "BAD_REQUEST",
      message: "scoreContext requires a non-empty userText",
    };
  }

  if (!Array.isArray(input.candidates)) {
    throw {
      code: "BAD_REQUEST",
      message: "scoreContext requires a candidate list",
    };
  }

  const maxResults = Number.isFinite(input.maxResults) && input.maxResults && input.maxResults > 0
    ? Math.floor(input.maxResults)
    : 10;

  const userTokens = tokenize(input.userText);
  return input.candidates
    .map((candidate, index) => ({
      candidate,
      index,
      score: scoreCandidate(userTokens, candidate, index),
    }))
    .sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      return left.index - right.index;
    })
    .slice(0, maxResults);
}
