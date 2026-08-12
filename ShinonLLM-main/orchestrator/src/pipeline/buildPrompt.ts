import { retrieveContext, type RetrievalContextOutput } from "../../../memory/src/retrieval/retrieveContext.js";

export type NormalizedChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

export type NormalizedChatTurn = {
  request?: Record<string, unknown>;
  userText: string;
  history: ReadonlyArray<NormalizedChatMessage>;
  memoryContext: unknown;
};

export type BuildPromptInput = {
  chatTurn?: NormalizedChatTurn;
  turn?: NormalizedChatTurn;
  normalizedTurn?: NormalizedChatTurn;
  userText?: string;
  history?: ReadonlyArray<NormalizedChatMessage>;
  memoryContext?: unknown;
  tokenBudget?: number;
};

export type BuiltPrompt = {
  systemPrompt: string;
  messages: ReadonlyArray<NormalizedChatMessage>;
  memoryContext: unknown;
  retrievalContext: RetrievalContextOutput;
  tokenBudget: {
    limit: number;
    used: number;
    remaining: number;
  };
  assistantPayload: {
    role: "assistant";
    content: string;
    messages: ReadonlyArray<NormalizedChatMessage>;
    systemPrompt: string;
    retrievalContext: RetrievalContextOutput;
    tokenBudget: {
      limit: number;
      used: number;
      remaining: number;
    };
  };
};

const SYSTEM_POLICY = [
  "You are a deterministic orchestration layer.",
  "Use only the provided user turn, history, and retrieved memory context.",
  "Do not invent facts when the context is empty or incomplete.",
  "Fail closed on any contract break.",
].join(" ");

const DEFAULT_TOKEN_BUDGET = 800;

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeMessage(candidate: unknown): NormalizedChatMessage | null {
  if (!isPlainObject(candidate)) {
    return null;
  }

  const role = candidate.role;
  if (role !== "system" && role !== "user" && role !== "assistant") {
    return null;
  }

  if (!isNonEmptyString(candidate.content)) {
    return null;
  }

  return {
    role,
    content: candidate.content.trim(),
  };
}

function resolveChatTurn(input: BuildPromptInput): NormalizedChatTurn {
  const candidate = input.normalizedTurn ?? input.chatTurn ?? input.turn ?? (isPlainObject(input) ? input : undefined);
  if (!candidate || typeof candidate !== "object") {
    throw {
      code: "BAD_REQUEST",
      message: "buildPrompt requires a normalized chat turn",
    };
  }

  const userText = isNonEmptyString(candidate.userText)
    ? candidate.userText.trim()
    : isNonEmptyString(input.userText)
      ? input.userText.trim()
      : "";

  const historySource = Array.isArray(candidate.history)
    ? candidate.history
    : Array.isArray(input.history)
      ? input.history
      : [];

  const memoryContext = "memoryContext" in candidate ? candidate.memoryContext : input.memoryContext;

  const history = historySource
    .map(normalizeMessage)
    .filter((message): message is NormalizedChatMessage => message !== null);

  if (!userText) {
    throw {
      code: "BAD_REQUEST",
      message: "buildPrompt requires a non-empty userText",
    };
  }

  if (
    memoryContext === undefined ||
    (memoryContext !== null && !Array.isArray(memoryContext) && !isPlainObject(memoryContext))
  ) {
    throw {
      code: "BAD_REQUEST",
      message: "buildPrompt requires object or array memory context",
    };
  }

  return {
    request: isPlainObject((candidate as Record<string, unknown>).request)
      ? (candidate as NormalizedChatTurn).request
      : undefined,
    userText,
    history,
    memoryContext,
  };
}

function estimateTokens(value: string): number {
  const words = value.trim().match(/[^\s]+/gu) ?? [];
  return Math.max(1, words.length);
}

function normalizeBudget(value: unknown): number {
  if (Number.isFinite(value) && typeof value === "number" && value > 0) {
    return Math.floor(value);
  }
  return DEFAULT_TOKEN_BUDGET;
}

export function buildPrompt(input: BuildPromptInput): BuiltPrompt {
  const turn = resolveChatTurn(input);
  const tokenBudget = normalizeBudget(input.tokenBudget);
  const retrievalContext = retrieveContext({
    userText: turn.userText,
    memoryContext: turn.memoryContext,
    maxTokens: tokenBudget,
  });

  const memorySummary = retrievalContext.entries
    .map((entry) => `${entry.type ?? "memory"}: ${entry.content}`)
    .join("\n");

  const systemPrompt = memorySummary.length > 0
    ? `${SYSTEM_POLICY}\n\nRetrieved memory:\n${memorySummary}`
    : SYSTEM_POLICY;

  const messages: NormalizedChatMessage[] = [
    { role: "system", content: systemPrompt },
    ...turn.history,
    { role: "user", content: turn.userText },
  ];

  const usedTokens = messages.reduce((total, message) => total + estimateTokens(message.content), 0);
  const tokenState = {
    limit: tokenBudget,
    used: usedTokens,
    remaining: Math.max(0, tokenBudget - usedTokens),
  };

  return {
    systemPrompt,
    messages,
    memoryContext: turn.memoryContext,
    retrievalContext,
    tokenBudget: tokenState,
    assistantPayload: {
      role: "assistant",
      content: systemPrompt,
      messages,
      systemPrompt,
      retrievalContext,
      tokenBudget: tokenState,
    },
  };
}
