type ChatRole = "system" | "user" | "assistant";

type ChatHistoryEntry = Readonly<{
  role: ChatRole;
  content: string;
}>;

type NormalizedChatTurn = Readonly<{
  requestId?: string;
  sessionId?: string;
  conversationId?: string;
  userText: string;
  history: ReadonlyArray<ChatHistoryEntry>;
}>;

type MemoryContext = Readonly<Record<string, unknown>>;

type ValidatedAssistantPayload = Readonly<{
  reply: string;
  message: Readonly<{
    role: "assistant";
    content: string;
  }>;
  source: "orchestrator";
  model: string;
  prompt: string;
  guardrailStatus: "validated";
}>;

type ActionSchemaParseResult =
  | Readonly<{ success: true; data: ValidatedAssistantPayload }>
  | Readonly<{ success: false; error: Error }>;

type PlainObject = Record<string, unknown>;

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function failClosed(message: string): never {
  throw new Error(`actionSchema: ${message}`);
}

function normalizeString(value: unknown, fieldName: string): string {
  if (!isNonEmptyString(value)) {
    failClosed(`${fieldName} must be a non-empty string`);
  }
  return value.trim();
}

function normalizeRequest(request: unknown): void {
  if (request === undefined) {
    return;
  }
  if (!isPlainObject(request)) {
    failClosed("turn.request must be a plain object when present");
  }
  if (request.sessionId !== undefined && !isNonEmptyString(request.sessionId)) {
    failClosed("turn.request.sessionId must be a non-empty string when present");
  }
  if (request.conversationId !== undefined && !isNonEmptyString(request.conversationId)) {
    failClosed("turn.request.conversationId must be a non-empty string when present");
  }
  if (request.requestId !== undefined && !isNonEmptyString(request.requestId)) {
    failClosed("turn.request.requestId must be a non-empty string when present");
  }
}

function normalizeHistoryEntry(entry: unknown, index: number): ChatHistoryEntry {
  if (!isPlainObject(entry)) {
    failClosed(`turn.history[${index}] must be a plain object`);
  }
  if (entry.role !== "system" && entry.role !== "user" && entry.role !== "assistant") {
    failClosed(`turn.history[${index}].role must be system, user, or assistant`);
  }
  return Object.freeze({
    role: entry.role,
    content: normalizeString(entry.content, `turn.history[${index}].content`),
  });
}

function normalizeTurn(candidate: unknown): NormalizedChatTurn {
  if (!isPlainObject(candidate)) {
    failClosed("turn must be a plain object");
  }

  const userText = normalizeString(candidate.userText, "turn.userText");
  if (!Array.isArray(candidate.history)) {
    failClosed("turn.history must be an array");
  }

  const history = candidate.history.map((entry, index) => normalizeHistoryEntry(entry, index));

  if (candidate.request !== undefined) {
    normalizeRequest(candidate.request);
  }

  return Object.freeze({
    requestId: isNonEmptyString(candidate.requestId) ? candidate.requestId.trim() : undefined,
    sessionId: isNonEmptyString(candidate.sessionId) ? candidate.sessionId.trim() : undefined,
    conversationId: isNonEmptyString(candidate.conversationId) ? candidate.conversationId.trim() : undefined,
    userText,
    history: Object.freeze(history),
  });
}

function normalizeMemoryContext(candidate: unknown): MemoryContext {
  if (!isPlainObject(candidate)) {
    failClosed("memoryContext must be a plain object");
  }
  return Object.freeze({ ...candidate });
}

function sortKeys(value: PlainObject): string[] {
  return Object.keys(value).sort((left, right) => left.localeCompare(right));
}

function stableSerialize(value: unknown, seen: WeakSet<object>): string {
  if (value === null) {
    return "null";
  }

  const valueType = typeof value;
  if (valueType === "string") {
    return JSON.stringify(value);
  }
  if (valueType === "number" || valueType === "boolean") {
    return String(value);
  }
  if (valueType === "bigint") {
    return JSON.stringify(value.toString());
  }
  if (valueType === "undefined" || valueType === "function" || valueType === "symbol") {
    return JSON.stringify(String(value));
  }

  if (Array.isArray(value)) {
    return `[${value.map((entry) => stableSerialize(entry, seen)).join(",")}]`;
  }

  if (!isPlainObject(value)) {
    return JSON.stringify(String(value));
  }

  if (seen.has(value)) {
    failClosed("memoryContext contains a circular reference");
  }

  seen.add(value);
  const parts = sortKeys(value).map((key) => `${JSON.stringify(key)}:${stableSerialize(value[key], seen)}`);
  seen.delete(value);
  return `{${parts.join(",")}}`;
}

function summarizeMemoryContext(memoryContext: MemoryContext): string {
  const entries = sortKeys(memoryContext as PlainObject).map(
    (key) => `${key}=${stableSerialize(memoryContext[key], new WeakSet<object>())}`,
  );
  return entries.join(" | ");
}

function normalizeAllowedActions(memoryContext: MemoryContext): ReadonlyArray<string> {
  const candidate = memoryContext.allowedActions;
  if (candidate === undefined) {
    return Object.freeze([]);
  }

  if (!Array.isArray(candidate)) {
    failClosed("memoryContext.allowedActions must be an array when present");
  }

  const normalized = candidate.map((entry, index) => {
    if (!isNonEmptyString(entry)) {
      failClosed(`memoryContext.allowedActions[${index}] must be a non-empty string`);
    }
    return entry.trim();
  });

  return Object.freeze(normalized);
}

function validateDeclaredActions(memoryContext: MemoryContext): void {
  const allowedActions = normalizeAllowedActions(memoryContext);
  const candidate = memoryContext.actions;

  if (candidate === undefined) {
    return;
  }

  if (!Array.isArray(candidate)) {
    failClosed("memoryContext.actions must be an array when present");
  }

  if (candidate.length === 0) {
    return;
  }

  if (allowedActions.length === 0) {
    failClosed("memoryContext.actions are not allowed without memoryContext.allowedActions");
  }

  for (const [index, action] of candidate.entries()) {
    if (!isPlainObject(action)) {
      failClosed(`memoryContext.actions[${index}] must be a plain object`);
    }
    if (!isNonEmptyString(action.type)) {
      failClosed(`memoryContext.actions[${index}].type must be a non-empty string`);
    }
    const type = action.type.trim();
    if (!allowedActions.includes(type)) {
      failClosed(`memoryContext.actions[${index}].type is not allowed`);
    }
    if (action.args !== undefined && !isPlainObject(action.args)) {
      failClosed(`memoryContext.actions[${index}].args must be a plain object when present`);
    }
    if (action.target !== undefined && !isNonEmptyString(action.target)) {
      failClosed(`memoryContext.actions[${index}].target must be a non-empty string when present`);
    }
  }
}

function buildPrompt(turn: NormalizedChatTurn, memoryContext: MemoryContext): string {
  const historyBlock = turn.history.length
    ? turn.history.map((entry) => `${entry.role.toUpperCase()}: ${entry.content}`).join("\n")
    : "HISTORY: <empty>";
  const memorySummary = summarizeMemoryContext(memoryContext);

  return [
    "SYSTEM: Validate assistant payload and allowed actions.",
    `USER: ${turn.userText}`,
    historyBlock,
    memorySummary.length > 0 ? `MEMORY: ${memorySummary}` : "MEMORY: <empty>",
  ].join("\n");
}

function buildModelName(memoryContext: MemoryContext, prompt: string): string {
  const modelHint =
    typeof memoryContext.modelHint === "string" && memoryContext.modelHint.trim().length > 0
      ? memoryContext.modelHint.trim()
      : "";

  return modelHint || (prompt.length > 1800 ? "orchestrator-long" : "orchestrator-default");
}

function buildValidatedAssistantPayload(
  turn: NormalizedChatTurn,
  memoryContext: MemoryContext,
): ValidatedAssistantPayload {
  const prompt = buildPrompt(turn, memoryContext);
  const reply = turn.userText;
  const model = buildModelName(memoryContext, prompt);

  return Object.freeze({
    reply,
    message: Object.freeze({
      role: "assistant",
      content: reply,
    }),
    source: "orchestrator",
    model,
    prompt,
    guardrailStatus: "validated",
  });
}

export const actionSchema = Object.freeze({
  name: "actionSchema",
  parse(input: unknown): ValidatedAssistantPayload {
    return assertAllowedActions(input);
  },
  safeParse(input: unknown): ActionSchemaParseResult {
    try {
      return Object.freeze({
        success: true,
        data: assertAllowedActions(input),
      });
    } catch (error) {
      return Object.freeze({
        success: false,
        error: error instanceof Error ? error : new Error("actionSchema: parse failed"),
      });
    }
  },
});

export function assertAllowedActions(input: unknown): ValidatedAssistantPayload {
  if (!isPlainObject(input)) {
    failClosed("input must be a plain object");
  }
  if (!("turn" in input)) {
    failClosed("input.turn is required");
  }
  if (!("memoryContext" in input)) {
    failClosed("input.memoryContext is required");
  }

  const turn = normalizeTurn(input.turn);
  const memoryContext = normalizeMemoryContext(input.memoryContext);
  validateDeclaredActions(memoryContext);
  return buildValidatedAssistantPayload(turn, memoryContext);
}
