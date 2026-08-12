export type BackendName = "ollama" | "llamacpp";

export type BackendRouteDecision = Readonly<{
  backend: BackendName | string;
  model?: string;
  requestId?: string;
  healthMode?: "liveness" | "readiness";
  endpoint?: string;
}>;

export type PromptPayload = Readonly<{
  prompt: string;
  systemPrompt?: string;
  messages?: ReadonlyArray<Readonly<{
    role: "system" | "user" | "assistant";
    content: string;
  }>>;
  metadata?: Readonly<Record<string, unknown>>;
}>;

export type NormalizedModelResponse = Readonly<{
  ok: true;
  backend: BackendName;
  model: string;
  prompt: string;
  message: Readonly<{
    role: "assistant";
    content: string;
  }>;
  health: "healthy" | "degraded";
  requestId?: string;
  validated: true;
  metadata: Readonly<{
    healthMode: "liveness" | "readiness";
    endpoint?: string;
    messageCount: number;
    promptLength: number;
  }>;
}>;

export type ClassifiedBackendErrorCode =
  | "BACKEND_ROUTE_INVALID"
  | "BACKEND_PROMPT_INVALID"
  | "BACKEND_HEALTH_UNAVAILABLE";

export type ClassifiedBackendError = Readonly<{
  ok: false;
  code: ClassifiedBackendErrorCode;
  message: string;
  details?: Readonly<Record<string, unknown>>;
}>;

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function classifyBackendError(
  code: ClassifiedBackendErrorCode,
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

function normalizeBackendName(value: unknown): BackendName | null {
  if (value === "ollama" || value === "llamacpp") {
    return value;
  }
  return null;
}

function normalizeHealthMode(value: unknown): "liveness" | "readiness" {
  return value === "readiness" ? "readiness" : "liveness";
}

function normalizeMessageCount(messages: PromptPayload["messages"]): number {
  return Array.isArray(messages) ? messages.length : 0;
}

function buildPromptText(payload: PromptPayload): string {
  const prompt = payload.prompt.trim();
  const systemPrompt = isNonEmptyString(payload.systemPrompt) ? payload.systemPrompt.trim() : "";
  const messageText = Array.isArray(payload.messages)
    ? payload.messages
        .map((entry) => `${entry.role}:${entry.content.trim()}`)
        .join("\n")
    : "";

  return [systemPrompt, messageText, prompt].filter((part) => part.length > 0).join("\n");
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
    ("routeDecision" in routeDecisionOrInput || "promptPayload" in routeDecisionOrInput)
  ) {
    return {
      routeDecision: routeDecisionOrInput.routeDecision,
      promptPayload: routeDecisionOrInput.promptPayload,
    };
  }

  return {
    routeDecision: routeDecisionOrInput,
    promptPayload: promptPayload,
  };
}

function validateRouteDecision(value: unknown): BackendRouteDecision {
  if (!isPlainObject(value)) {
    throw classifyBackendError(
      "BACKEND_ROUTE_INVALID",
      "route decision must be a plain object",
    );
  }

  const backend = normalizeBackendName(value.backend);
  if (backend === null) {
    throw classifyBackendError(
      "BACKEND_ROUTE_INVALID",
      "route decision.backend must be ollama or llamacpp",
      { backend: value.backend },
    );
  }

  return Object.freeze({
    backend,
    model: isNonEmptyString(value.model) ? value.model.trim() : undefined,
    requestId: isNonEmptyString(value.requestId) ? value.requestId.trim() : undefined,
    healthMode: normalizeHealthMode(value.healthMode),
    endpoint: isNonEmptyString(value.endpoint) ? value.endpoint.trim() : undefined,
  });
}

function validatePromptPayload(value: unknown): PromptPayload {
  if (!isPlainObject(value)) {
    throw classifyBackendError(
      "BACKEND_PROMPT_INVALID",
      "prompt payload must be a plain object",
    );
  }

  if (!isNonEmptyString(value.prompt)) {
    throw classifyBackendError(
      "BACKEND_PROMPT_INVALID",
      "prompt payload.prompt must be a non-empty string",
    );
  }

  if (value.messages !== undefined && !Array.isArray(value.messages)) {
    throw classifyBackendError(
      "BACKEND_PROMPT_INVALID",
      "prompt payload.messages must be an array when provided",
    );
  }

  if (Array.isArray(value.messages)) {
    for (const [index, entry] of value.messages.entries()) {
      if (!isPlainObject(entry)) {
        throw classifyBackendError(
          "BACKEND_PROMPT_INVALID",
          `prompt payload.messages[${index}] must be a plain object`,
        );
      }
      if (entry.role !== "system" && entry.role !== "user" && entry.role !== "assistant") {
        throw classifyBackendError(
          "BACKEND_PROMPT_INVALID",
          `prompt payload.messages[${index}].role is invalid`,
        );
      }
      if (!isNonEmptyString(entry.content)) {
        throw classifyBackendError(
          "BACKEND_PROMPT_INVALID",
          `prompt payload.messages[${index}].content must be a non-empty string`,
        );
      }
    }
  }

  return Object.freeze({
    prompt: value.prompt.trim(),
    systemPrompt: isNonEmptyString(value.systemPrompt) ? value.systemPrompt.trim() : undefined,
    messages: Array.isArray(value.messages)
      ? Object.freeze(
          value.messages.map((entry) =>
            Object.freeze({
              role: entry.role,
              content: entry.content.trim(),
            }),
          ),
        )
      : undefined,
    metadata: isPlainObject(value.metadata) ? Object.freeze({ ...value.metadata }) : undefined,
  });
}

function normalizeResponse(
  routeDecision: BackendRouteDecision,
  promptPayload: PromptPayload,
): NormalizedModelResponse {
  const backend = normalizeBackendName(routeDecision.backend);
  if (backend === null) {
    throw classifyBackendError(
      "BACKEND_ROUTE_INVALID",
      "route decision backend is unsupported",
      { backend: routeDecision.backend },
    );
  }

  const prompt = buildPromptText(promptPayload);
  const model = isNonEmptyString(routeDecision.model) ? routeDecision.model.trim() : `${backend}-health`;

  return Object.freeze({
    ok: true,
    backend,
    model,
    prompt,
    message: Object.freeze({
      role: "assistant",
      content: `health:${backend}:${prompt.length > 0 ? "ok" : "empty"}`,
    }),
    health: routeDecision.healthMode === "readiness" ? "healthy" : "degraded",
    requestId: isNonEmptyString(routeDecision.requestId) ? routeDecision.requestId.trim() : undefined,
    validated: true,
    metadata: Object.freeze({
      healthMode: normalizeHealthMode(routeDecision.healthMode),
      endpoint: isNonEmptyString(routeDecision.endpoint) ? routeDecision.endpoint.trim() : undefined,
      messageCount: normalizeMessageCount(promptPayload.messages),
      promptLength: prompt.length,
    }),
  });
}

export async function getBackendHealth(
  routeDecisionOrInput: unknown,
  promptPayload?: unknown,
): Promise<NormalizedModelResponse> {
  try {
    const normalized = normalizeInput(routeDecisionOrInput, promptPayload);
    const routeDecision = validateRouteDecision(normalized.routeDecision);
    const promptPayload = validatePromptPayload(normalized.promptPayload);

    return normalizeResponse(routeDecision, promptPayload);
  } catch (error) {
    if (
      isPlainObject(error) &&
      error["ok"] === false &&
      typeof error["code"] === "string" &&
      typeof error["message"] === "string"
    ) {
      throw error;
    }

    throw classifyBackendError(
      "BACKEND_HEALTH_UNAVAILABLE",
      "backend health check failed",
    );
  }
}
