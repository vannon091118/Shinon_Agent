type PlainObject = Record<string, unknown>;

export type BackendErrorCode =
  | "UNREACHABLE"
  | "TIMEOUT"
  | "SCHEMA"
  | "CAPACITY"
  | "INTERNAL_SERVER_ERROR";

type BackendName = "ollama" | "llamacpp";

export type BackendRouteDecision = Readonly<{
  backend: BackendName | string;
  fallbackBackend?: BackendName | string;
  allowFallback?: boolean;
  model?: string;
  requestId?: string;
  sessionId?: string;
  conversationId?: string;
  stream?: boolean;
  policyId?: string;
}>;

type NormalizedBackendRouteDecision = Readonly<{
  backend: BackendName;
  fallbackBackend?: BackendName;
  allowFallback: boolean;
  model: string;
  requestId?: string;
  sessionId?: string;
  conversationId?: string;
  stream: boolean;
  policyId?: string;
}>;

export type PromptMessage = Readonly<{
  role: "system" | "user" | "assistant";
  content: string;
}>;

export type PromptPayload = Readonly<{
  prompt?: string;
  userText?: string;
  systemPrompt?: string;
  messages?: ReadonlyArray<PromptMessage>;
  requestId?: string;
  sessionId?: string;
  conversationId?: string;
}>;

export type NormalizedModelResponse = Readonly<{
  backend: BackendName;
  model: string;
  content: string;
  message: Readonly<{
    role: "assistant";
    content: string;
  }>;
  streamed: boolean;
  requestId?: string;
  sessionId?: string;
  conversationId?: string;
  raw: unknown;
}>;

export type ClassifiedBackendError = Readonly<{
  ok: false;
  code: BackendErrorCode;
  message: string;
  details?: Readonly<Record<string, unknown>>;
}>;

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isBackendName(value: unknown): value is BackendName {
  return value === "ollama" || value === "llamacpp";
}

function classifyError(
  code: BackendErrorCode,
  message: string,
  details?: Readonly<Record<string, unknown>>,
): ClassifiedBackendError {
  return Object.freeze({
    ok: false,
    code,
    message,
    ...(details ? { details: Object.freeze({ ...details }) } : {}),
  });
}

function failClosed(
  code: BackendErrorCode,
  message: string,
  details?: Readonly<Record<string, unknown>>,
): never {
  throw classifyError(code, message, details);
}

function normalizeInput(
  routeDecisionOrInput: unknown,
  promptPayload?: unknown,
): Readonly<{
  routeDecision: unknown;
  promptPayload: unknown;
}> {
  if (
    promptPayload === undefined &&
    isPlainObject(routeDecisionOrInput) &&
    "routeDecision" in routeDecisionOrInput &&
    "promptPayload" in routeDecisionOrInput
  ) {
    return Object.freeze({
      routeDecision: routeDecisionOrInput.routeDecision,
      promptPayload: routeDecisionOrInput.promptPayload,
    });
  }

  if (Array.isArray(routeDecisionOrInput) && routeDecisionOrInput.length === 2 && promptPayload === undefined) {
    return Object.freeze({
      routeDecision: routeDecisionOrInput[0],
      promptPayload: routeDecisionOrInput[1],
    });
  }

  return Object.freeze({
    routeDecision: routeDecisionOrInput,
    promptPayload,
  });
}

function normalizeBackendName(value: unknown): BackendName {
  if (!isBackendName(value)) {
    failClosed("SCHEMA", "unsupported backend requested", {
      backend: value,
    });
  }

  return value;
}

function normalizeMessages(messages: unknown): ReadonlyArray<PromptMessage> | undefined {
  if (messages === undefined) {
    return undefined;
  }

  if (!Array.isArray(messages)) {
    failClosed("SCHEMA", "prompt payload.messages must be an array of chat messages");
  }

  const normalized = messages.map((entry, index) => {
    if (!isPlainObject(entry)) {
      failClosed("SCHEMA", `prompt payload.messages[${index}] must be a plain object`);
    }

    if (entry.role !== "system" && entry.role !== "user" && entry.role !== "assistant") {
      failClosed("SCHEMA", `prompt payload.messages[${index}].role is invalid`);
    }

    if (!isNonEmptyString(entry.content)) {
      failClosed("SCHEMA", `prompt payload.messages[${index}].content must be a non-empty string`);
    }

    return Object.freeze({
      role: entry.role,
      content: entry.content.trim(),
    }) as PromptMessage;
  });

  return Object.freeze(normalized);
}

function normalizePromptPayload(candidate: unknown): PromptPayload {
  if (!isPlainObject(candidate)) {
    failClosed("SCHEMA", "prompt payload must be a plain object");
  }

  const messages = normalizeMessages(candidate.messages);
  const prompt = isNonEmptyString(candidate.prompt) ? candidate.prompt.trim() : undefined;
  const userText = isNonEmptyString(candidate.userText) ? candidate.userText.trim() : undefined;
  const systemPrompt = isNonEmptyString(candidate.systemPrompt) ? candidate.systemPrompt.trim() : undefined;

  if (!prompt && !userText && !messages) {
    failClosed("SCHEMA", "prompt payload requires prompt text or messages");
  }

  return Object.freeze({
    prompt,
    userText,
    systemPrompt,
    messages,
    requestId: isNonEmptyString(candidate.requestId) ? candidate.requestId.trim() : undefined,
    sessionId: isNonEmptyString(candidate.sessionId) ? candidate.sessionId.trim() : undefined,
    conversationId: isNonEmptyString(candidate.conversationId) ? candidate.conversationId.trim() : undefined,
  });
}

function normalizeRouteDecision(candidate: unknown): NormalizedBackendRouteDecision {
  if (!isPlainObject(candidate)) {
    failClosed("SCHEMA", "route decision must be a plain object");
  }

  const backend = normalizeBackendName(candidate.backend);
  const model = isNonEmptyString(candidate.model) ? candidate.model.trim() : "";
  if (!model) {
    failClosed("SCHEMA", "route decision.model must be a non-empty string");
  }

  const fallbackBackend =
    candidate.fallbackBackend === undefined ? undefined : normalizeBackendName(candidate.fallbackBackend);

  if (candidate.fallbackBackend !== undefined && fallbackBackend === undefined) {
    failClosed("SCHEMA", "route decision.fallbackBackend must be ollama or llamacpp", {
      fallbackBackend: candidate.fallbackBackend,
    });
  }

  return Object.freeze({
    backend,
    fallbackBackend,
    allowFallback: candidate.allowFallback !== false,
    model,
    requestId: isNonEmptyString(candidate.requestId) ? candidate.requestId.trim() : undefined,
    sessionId: isNonEmptyString(candidate.sessionId) ? candidate.sessionId.trim() : undefined,
    conversationId: isNonEmptyString(candidate.conversationId) ? candidate.conversationId.trim() : undefined,
    stream: candidate.stream !== false,
    policyId: isNonEmptyString(candidate.policyId) ? candidate.policyId.trim() : undefined,
  });
}

function buildPromptText(promptPayload: PromptPayload): string {
  if (isNonEmptyString(promptPayload.prompt)) {
    return promptPayload.prompt.trim();
  }

  if (isNonEmptyString(promptPayload.userText)) {
    return promptPayload.userText.trim();
  }

  if (promptPayload.messages && promptPayload.messages.length > 0) {
    return promptPayload.messages.map((entry) => `${entry.role.toUpperCase()}: ${entry.content}`).join("\n");
  }

  return "";
}

function resolveRequestMeta(
  decision: BackendRouteDecision,
  promptPayload: PromptPayload,
): Readonly<{
  requestId?: string;
  sessionId?: string;
  conversationId?: string;
}> {
  return Object.freeze({
    requestId: promptPayload.requestId ?? decision.requestId,
    sessionId: promptPayload.sessionId ?? decision.sessionId,
    conversationId: promptPayload.conversationId ?? decision.conversationId,
  });
}

function buildNormalizedResponse(
  routeDecision: NormalizedBackendRouteDecision,
  promptPayload: PromptPayload,
): NormalizedModelResponse {
  const promptText = buildPromptText(promptPayload);
  if (!isNonEmptyString(promptText)) {
    failClosed("SCHEMA", "prompt payload did not resolve to prompt text");
  }

  const requestMeta = resolveRequestMeta(routeDecision, promptPayload);
  const content = promptText.trim();

  return Object.freeze({
    backend: routeDecision.backend,
    model: routeDecision.model,
    content,
    message: Object.freeze({
      role: "assistant",
      content,
    }),
    streamed: routeDecision.stream !== false,
    ...(requestMeta.requestId ? { requestId: requestMeta.requestId } : {}),
    ...(requestMeta.sessionId ? { sessionId: requestMeta.sessionId } : {}),
    ...(requestMeta.conversationId ? { conversationId: requestMeta.conversationId } : {}),
    raw: Object.freeze({
      routeDecision,
      promptPayload,
      promptText: content,
      promptLength: content.length,
      messageCount: promptPayload.messages?.length ?? 0,
      policyId: routeDecision.policyId ?? "default",
    }),
  });
}

export function classifyBackendError(
  routeDecisionOrInput: unknown,
  promptPayload?: unknown,
): NormalizedModelResponse {
  try {
    const normalized = normalizeInput(routeDecisionOrInput, promptPayload);
    const routeDecision = normalizeRouteDecision(normalized.routeDecision);
    const normalizedPromptPayload = normalizePromptPayload(normalized.promptPayload);

    return buildNormalizedResponse(routeDecision, normalizedPromptPayload);
  } catch (error) {
    if (
      isPlainObject(error) &&
      error.ok === false &&
      typeof error.code === "string" &&
      typeof error.message === "string"
    ) {
      throw error as ClassifiedBackendError;
    }

    throw classifyError("INTERNAL_SERVER_ERROR", "backend error classification failed");
  }
}
