export type NormalizedChatTurn = {
  role: "user" | "assistant" | "system";
  content: string;
  turnId?: string;
  createdAt?: string;
};

export type MemoryContextEntry = {
  id: string;
  type: string;
  content: string;
  score?: number;
  tags?: string[];
};

export type MemoryContext = {
  entries: MemoryContextEntry[];
  tokenBudget?: number;
};

export type AssistantPayload = {
  role: "assistant";
  content: string;
  actions?: unknown[];
  metadata?: Record<string, unknown>;
};

type GuardrailsInput = {
  turn: NormalizedChatTurn;
  memoryContext: MemoryContext;
  assistantPayload: unknown;
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function failClosed(message: string): never {
  throw new Error(`applyGuardrails: ${message}`);
}

function assertNormalizedChatTurn(turn: unknown): asserts turn is NormalizedChatTurn {
  if (!isPlainObject(turn)) {
    failClosed("turn must be an object");
  }
  if (turn.role !== "user" && turn.role !== "assistant" && turn.role !== "system") {
    failClosed("turn.role must be user, assistant, or system");
  }
  if (typeof turn.content !== "string" || turn.content.trim().length === 0) {
    failClosed("turn.content must be a non-empty string");
  }
  if (turn.turnId !== undefined && typeof turn.turnId !== "string") {
    failClosed("turn.turnId must be a string when present");
  }
  if (turn.createdAt !== undefined && typeof turn.createdAt !== "string") {
    failClosed("turn.createdAt must be a string when present");
  }
}

function assertMemoryContext(memoryContext: unknown): asserts memoryContext is MemoryContext {
  if (!isPlainObject(memoryContext)) {
    failClosed("memoryContext must be an object");
  }
  if (!Array.isArray(memoryContext.entries)) {
    failClosed("memoryContext.entries must be an array");
  }

  for (const entry of memoryContext.entries) {
    if (!isPlainObject(entry)) {
      failClosed("memoryContext.entries must contain objects");
    }
    if (typeof entry.id !== "string" || entry.id.length === 0) {
      failClosed("memoryContext entry.id must be a non-empty string");
    }
    if (typeof entry.type !== "string" || entry.type.length === 0) {
      failClosed("memoryContext entry.type must be a non-empty string");
    }
    if (typeof entry.content !== "string") {
      failClosed("memoryContext entry.content must be a string");
    }
    if (entry.score !== undefined && typeof entry.score !== "number") {
      failClosed("memoryContext entry.score must be a number when present");
    }
    if (entry.tags !== undefined && (!Array.isArray(entry.tags) || entry.tags.some((tag) => typeof tag !== "string"))) {
      failClosed("memoryContext entry.tags must be an array of strings when present");
    }
  }

  if (memoryContext.tokenBudget !== undefined && typeof memoryContext.tokenBudget !== "number") {
    failClosed("memoryContext.tokenBudget must be a number when present");
  }
}

function assertAssistantPayload(payload: unknown): asserts payload is AssistantPayload {
  if (!isPlainObject(payload)) {
    failClosed("assistantPayload must be an object");
  }
  if (payload.role !== "assistant") {
    failClosed("assistantPayload.role must be assistant");
  }
  if (typeof payload.content !== "string" || payload.content.trim().length === 0) {
    failClosed("assistantPayload.content must be a non-empty string");
  }
  if (payload.actions !== undefined && !Array.isArray(payload.actions)) {
    failClosed("assistantPayload.actions must be an array when present");
  }
  if (payload.metadata !== undefined && !isPlainObject(payload.metadata)) {
    failClosed("assistantPayload.metadata must be a plain object when present");
  }
}

function assertNoForbiddenActions(payload: AssistantPayload, memoryContext: MemoryContext): void {
  for (const action of payload.actions ?? []) {
    if (!isPlainObject(action)) {
      failClosed("actions must contain plain objects");
    }
    if (typeof action.type !== "string" || action.type.length === 0) {
      failClosed("each action must declare a non-empty type");
    }
    if (action.args !== undefined && !isPlainObject(action.args)) {
      failClosed("each action.args must be a plain object when present");
    }
  }

  if (
    typeof memoryContext.tokenBudget === "number" &&
    payload.content.length > memoryContext.tokenBudget
  ) {
    failClosed("assistant payload content exceeds memoryContext tokenBudget");
  }
}

export function applyGuardrails(input: GuardrailsInput): AssistantPayload {
  if (!isPlainObject(input)) {
    failClosed("input must be an object");
  }

  assertNormalizedChatTurn(input.turn);
  assertMemoryContext(input.memoryContext);
  assertAssistantPayload(input.assistantPayload);
  assertNoForbiddenActions(input.assistantPayload, input.memoryContext);

  return input.assistantPayload;
}
