import { sha256Hex } from "../../../shared/src/utils/hash.js";
import { stableJson } from "../../../shared/src/utils/stableJson.js";
import { callLlamaCpp } from "../adapters/llamacppAdapter.js";
import { callOllama } from "../adapters/ollamaAdapter.js";
import { waitForBackend, resolveHealthUrl } from "../retry/backendRetry.js";

type PlainObject = Record<string, unknown>;

export type BackendName = "ollama" | "llamacpp";

export type BackendRouteDecision = Readonly<{
  backend: BackendName;
  fallbackBackend?: BackendName;
  allowFallback?: boolean;
  model: string;
  requestId?: string;
  sessionId?: string;
  conversationId?: string;
  baseUrl?: string;
  endpoint?: string;
  timeoutMs?: number;
  stream?: boolean;
  headers?: Readonly<Record<string, string>>;
  policyId?: string;
  options?: Readonly<Record<string, unknown>>;
}>;

export type PromptPayload = Readonly<{
  prompt?: string;
  userText?: string;
  systemPrompt?: string;
  messages?: ReadonlyArray<
    Readonly<{
      role: "system" | "user" | "assistant";
      content: string;
    }>
  >;
  requestId?: string;
  sessionId?: string;
  conversationId?: string;
  format?: string;
  options?: Readonly<Record<string, unknown>>;
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

export type BackendRouteErrorCode =
  | "BACKEND_ROUTE_INVALID"
  | "BACKEND_PROMPT_INVALID"
  | "BACKEND_UNSUPPORTED_BACKEND"
  | "BACKEND_FALLBACK_FAILED"
  | "BACKEND_INTERNAL_ERROR";

export type ClassifiedBackendError = Readonly<{
  ok: false;
  code: BackendRouteErrorCode;
  message: string;
  details?: Readonly<Record<string, unknown>>;
}>;

type OfflineEvaluation = Readonly<{
  mode: "offline-evaluator";
  planner: Readonly<{
    intent: "question" | "analysis" | "code" | "summary";
    nextAction: "answer" | "explain" | "propose_patch" | "summarize";
    confidence: number;
  }>;
  replayHash: string;
}>;

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isMessageArray(value: unknown): value is PromptPayload["messages"] {
  return Array.isArray(value) && value.every((entry) => {
    return (
      isPlainObject(entry) &&
      (entry.role === "system" || entry.role === "user" || entry.role === "assistant") &&
      isNonEmptyString(entry.content)
    );
  });
}

function classifyBackendError(
  code: BackendRouteErrorCode,
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
  code: BackendRouteErrorCode,
  message: string,
  details?: Readonly<Record<string, unknown>>,
): never {
  throw classifyBackendError(code, message, details);
}

function toInteger(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) && value > 0
    ? Math.floor(value)
    : fallback;
}

function normalizeBackendName(value: unknown): BackendName | null {
  if (value === "ollama" || value === "llamacpp") {
    return value;
  }
  return null;
}

function normalizeRouteDecision(candidate: unknown): BackendRouteDecision {
  if (!isPlainObject(candidate)) {
    failClosed("BACKEND_ROUTE_INVALID", "route decision must be a plain object");
  }

  const backend = normalizeBackendName(candidate.backend);
  if (backend === null) {
    failClosed("BACKEND_ROUTE_INVALID", "route decision.backend must be ollama or llamacpp", {
      backend: candidate.backend,
    });
  }

  if (!isNonEmptyString(candidate.model)) {
    failClosed("BACKEND_ROUTE_INVALID", "route decision.model must be a non-empty string");
  }

  if ((candidate.options as any)?.live === false) {
    failClosed("BACKEND_ROUTE_INVALID", "route decision.options.live=false is not allowed");
  }

  const fallbackBackend = candidate.fallbackBackend === undefined
    ? undefined
    : normalizeBackendName(candidate.fallbackBackend);
  if (candidate.fallbackBackend !== undefined && fallbackBackend === null) {
    failClosed("BACKEND_ROUTE_INVALID", "route decision.fallbackBackend must be ollama or llamacpp", {
      fallbackBackend: candidate.fallbackBackend,
    });
  }

  if (candidate.headers !== undefined && !isPlainObject(candidate.headers)) {
    failClosed("BACKEND_ROUTE_INVALID", "route decision.headers must be a plain object when provided");
  }
  if (candidate.options !== undefined && !isPlainObject(candidate.options)) {
    failClosed("BACKEND_ROUTE_INVALID", "route decision.options must be a plain object when provided");
  }

  const env = (globalThis as typeof globalThis & {
    process?: {
      env?: Record<string, string | undefined>;
    };
  }).process?.env;

  const baseUrl = isNonEmptyString(candidate.baseUrl)
    ? candidate.baseUrl.trim()
    : backend === "ollama"
      ? env?.OLLAMA_BASE_URL?.trim() || "http://127.0.0.1:11434"
      : env?.LLAMA_CPP_BASE_URL?.trim() || "http://127.0.0.1:8000";

  const endpoint = isNonEmptyString(candidate.endpoint)
    ? candidate.endpoint.trim()
    : baseUrl;

  return Object.freeze({
    backend,
    fallbackBackend: fallbackBackend ?? undefined,
    allowFallback: candidate.allowFallback !== false,
    model: candidate.model.trim(),
    requestId: isNonEmptyString(candidate.requestId) ? candidate.requestId.trim() : undefined,
    sessionId: isNonEmptyString(candidate.sessionId) ? candidate.sessionId.trim() : undefined,
    conversationId: isNonEmptyString(candidate.conversationId) ? candidate.conversationId.trim() : undefined,
    baseUrl,
    endpoint,
    timeoutMs: toInteger(candidate.timeoutMs, 0) || undefined,
    // FIX: stream defaults to false — adapters don't stream yet, true was a lying default
    stream: candidate.stream === true,
    headers: candidate.headers !== undefined ? Object.freeze({ ...(candidate.headers as Record<string, string>) }) : undefined,
    policyId: isNonEmptyString(candidate.policyId) ? candidate.policyId.trim() : undefined,
    options: candidate.options !== undefined ? Object.freeze({ ...candidate.options }) : undefined,
  });
}

function normalizeMessages(messages: unknown): PromptPayload["messages"] | undefined {
  if (messages === undefined) {
    return undefined;
  }

  if (!isMessageArray(messages)) {
    failClosed("BACKEND_PROMPT_INVALID", "prompt payload.messages must be an array of chat messages");
  }

  return Object.freeze(
    messages.map((entry) =>
      Object.freeze({
        role: entry.role,
        content: entry.content.trim(),
      }),
    ),
  );
}

function normalizePromptPayload(candidate: unknown): PromptPayload {
  if (!isPlainObject(candidate)) {
    failClosed("BACKEND_PROMPT_INVALID", "prompt payload must be a plain object");
  }

  const messages = normalizeMessages(candidate.messages);
  const prompt = isNonEmptyString(candidate.prompt) ? candidate.prompt.trim() : undefined;
  const userText = isNonEmptyString(candidate.userText) ? candidate.userText.trim() : undefined;
  const systemPrompt = isNonEmptyString(candidate.systemPrompt) ? candidate.systemPrompt.trim() : undefined;

  if (!prompt && !userText && !messages) {
    failClosed("BACKEND_PROMPT_INVALID", "prompt payload requires prompt text or messages");
  }

  if (candidate.options !== undefined && !isPlainObject(candidate.options)) {
    failClosed("BACKEND_PROMPT_INVALID", "prompt payload.options must be a plain object when provided");
  }

  return Object.freeze({
    prompt,
    userText,
    systemPrompt,
    messages,
    requestId: isNonEmptyString(candidate.requestId) ? candidate.requestId.trim() : undefined,
    sessionId: isNonEmptyString(candidate.sessionId) ? candidate.sessionId.trim() : undefined,
    conversationId: isNonEmptyString(candidate.conversationId) ? candidate.conversationId.trim() : undefined,
    format: isNonEmptyString(candidate.format) ? candidate.format.trim() : undefined,
    options: candidate.options !== undefined ? Object.freeze({ ...candidate.options }) : undefined,
  });
}

function resolveInvocation(
  routeDecisionOrInput: unknown,
  promptPayload: unknown,
): Readonly<{
  routeDecision: BackendRouteDecision;
  promptPayload: PromptPayload;
}> {
  if (
    promptPayload === undefined &&
    isPlainObject(routeDecisionOrInput) &&
    "routeDecision" in routeDecisionOrInput &&
    "promptPayload" in routeDecisionOrInput
  ) {
    return Object.freeze({
      routeDecision: normalizeRouteDecision(routeDecisionOrInput.routeDecision),
      promptPayload: normalizePromptPayload(routeDecisionOrInput.promptPayload),
    });
  }

  if (Array.isArray(routeDecisionOrInput) && routeDecisionOrInput.length === 2 && promptPayload === undefined) {
    return Object.freeze({
      routeDecision: normalizeRouteDecision(routeDecisionOrInput[0]),
      promptPayload: normalizePromptPayload(routeDecisionOrInput[1]),
    });
  }

  return Object.freeze({
    routeDecision: normalizeRouteDecision(routeDecisionOrInput),
    promptPayload: normalizePromptPayload(promptPayload),
  });
}

function toPromptText(promptPayload: PromptPayload): string {
  return promptPayload.prompt?.trim()
    || promptPayload.userText?.trim()
    || (promptPayload.messages && promptPayload.messages.length > 0
      ? promptPayload.messages.map((message) => `${message.role.toUpperCase()}: ${message.content}`).join("\n")
      : "");
}

function inferRuntimePlan(text: string): OfflineEvaluation["planner"] {
  const lower = text.toLowerCase();
  if (/(code|bug|error|typescript|javascript|python|sql|patch)/u.test(lower)) {
    return Object.freeze({ intent: "code", nextAction: "propose_patch", confidence: 0.86 });
  }
  if (/(summarize|summary|zusammenfass|tl;dr|tldr)/u.test(lower)) {
    return Object.freeze({ intent: "summary", nextAction: "summarize", confidence: 0.84 });
  }
  if (/(analy|compare|bewert|audit|review)/u.test(lower)) {
    return Object.freeze({ intent: "analysis", nextAction: "explain", confidence: 0.81 });
  }
  return Object.freeze({ intent: "question", nextAction: "answer", confidence: 0.73 });
}

function buildReplayHash(input: {
  routeDecision: BackendRouteDecision;
  promptPayload: PromptPayload;
  mode: string;
  backend: BackendName;
  content: string;
}): string {
  return sha256Hex(
    stableJson({
      routeDecision: input.routeDecision,
      promptPayload: input.promptPayload,
      mode: input.mode,
      backend: input.backend,
      content: input.content,
    }),
  );
}

function evaluateOffline(
  routeDecision: BackendRouteDecision,
  promptPayload: PromptPayload,
  backend: BackendName,
  content: string,
): OfflineEvaluation {
  const planner = inferRuntimePlan(content);
  const replayHash = buildReplayHash({
    routeDecision,
    promptPayload,
    mode: "offline-evaluator",
    backend,
    content,
  });
  return Object.freeze({
    mode: "offline-evaluator",
    planner,
    replayHash,
  });
}

async function callLiveBackend(
  decision: BackendRouteDecision,
  promptPayload: PromptPayload,
): Promise<NormalizedModelResponse> {
  const requestId = promptPayload.requestId ?? decision.requestId;
  const sessionId = promptPayload.sessionId ?? decision.sessionId;
  const conversationId = promptPayload.conversationId ?? decision.conversationId;
  const streamed = decision.stream === true;

  // Retry: probe backend health before committing to the adapter call.
  // This prevents the offline-fallback from silently echoing user input
  // when the backend is just slow to start rather than permanently down.
  const retryAttempts = 3;
  const healthUrl = decision.backend === "llamacpp" || decision.backend === "ollama"
    ? resolveHealthUrl(decision.backend)
    : null;

  if (healthUrl) {
    await waitForBackend({
      healthUrl,
      maxAttempts: retryAttempts,
      initialDelayMs: 800,
      maxDelayMs: 5000,
    });
  }

  if (decision.backend === "ollama") {
    const result = await callOllama(decision, promptPayload);
    const offlineEvaluation = evaluateOffline(decision, promptPayload, "ollama", result.content);
    return Object.freeze({
      backend: "ollama",
      model: result.model,
      content: result.content,
      message: Object.freeze({
        role: "assistant",
        content: result.content,
      }),
      streamed: result.streamed,
      ...(result.requestId ? { requestId: result.requestId } : {}),
      ...(result.sessionId ? { sessionId: result.sessionId } : {}),
      ...(result.conversationId ? { conversationId: result.conversationId } : {}),
      raw: Object.freeze({
        mode: "live",
        evaluator: offlineEvaluation,
        adapter: result.raw,
      }),
    });
  }

  if (decision.backend === "llamacpp") {
    const result = await callLlamaCpp({
      routeDecision: decision as unknown as {
        endpoint: string;
      },
      promptPayload: promptPayload as unknown as {
        prompt?: string;
      },
    });
    const offlineEvaluation = evaluateOffline(decision, promptPayload, "llamacpp", result.reply);
    return Object.freeze({
      backend: "llamacpp",
      model: result.model,
      content: result.reply,
      message: Object.freeze({
        role: "assistant",
        content: result.reply,
      }),
      streamed,
      ...(requestId ? { requestId } : {}),
      ...(sessionId ? { sessionId } : {}),
      ...(conversationId ? { conversationId } : {}),
      raw: Object.freeze({
        mode: "live",
        evaluator: offlineEvaluation,
        adapter: result.raw,
      }),
    });
  }

  failClosed("BACKEND_UNSUPPORTED_BACKEND", "unsupported backend requested", {
    backend: decision.backend,
  });
}

function buildOfflineFallback(
  decision: BackendRouteDecision,
  promptPayload: PromptPayload,
  reason: Readonly<Record<string, unknown>>,
): NormalizedModelResponse {
  const content = toPromptText(promptPayload);
  const requestId = promptPayload.requestId ?? decision.requestId;
  const sessionId = promptPayload.sessionId ?? decision.sessionId;
  const conversationId = promptPayload.conversationId ?? decision.conversationId;
  const streamed = decision.stream !== false;
  const evaluator = evaluateOffline(decision, promptPayload, decision.backend, content);

  return Object.freeze({
    backend: decision.backend,
    model: `${decision.model}-offline-eval`,
    content,
    message: Object.freeze({
      role: "assistant",
      content,
    }),
    streamed,
    ...(requestId ? { requestId } : {}),
    ...(sessionId ? { sessionId } : {}),
    ...(conversationId ? { conversationId } : {}),
    raw: Object.freeze({
      mode: "offline-evaluator",
      evaluator,
      reason,
      routeDecision: decision,
      promptPayload,
    }),
  });
}

export async function routeBackendCall(
  routeDecisionOrInput: unknown,
  promptPayload?: unknown,
): Promise<NormalizedModelResponse> {
  const normalized = resolveInvocation(routeDecisionOrInput, promptPayload);
  try {
    return await callLiveBackend(normalized.routeDecision, normalized.promptPayload);
  } catch (error) {
    if (isPlainObject(error) && error.ok === false && typeof error.code === "string" && typeof error.message === "string") {
      const routeError = error as ClassifiedBackendError;
      if (routeError.code === "BACKEND_ROUTE_INVALID" || routeError.code === "BACKEND_PROMPT_INVALID") {
        throw routeError;
      }

      if (
        normalized.routeDecision.allowFallback === true &&
        normalized.routeDecision.fallbackBackend &&
        normalized.routeDecision.fallbackBackend !== normalized.routeDecision.backend
      ) {
        try {
          const fallbackDecision = Object.freeze({
            ...normalized.routeDecision,
            backend: normalized.routeDecision.fallbackBackend,
          }) as BackendRouteDecision;
          return await callLiveBackend(fallbackDecision, normalized.promptPayload);
        } catch (fallbackError) {
          const fallbackReason = isPlainObject(fallbackError)
            ? fallbackError
            : { code: "BACKEND_FALLBACK_FAILED", message: "backend fallback failed" };
          return buildOfflineFallback(
            normalized.routeDecision,
            normalized.promptPayload,
            Object.freeze({
              primaryError: routeError,
              fallbackError: fallbackReason,
            }),
          );
        }
      }

      return buildOfflineFallback(
        normalized.routeDecision,
        normalized.promptPayload,
        Object.freeze({
          primaryError: routeError,
        }),
      );
    }

    return buildOfflineFallback(
      normalized.routeDecision,
      normalized.promptPayload,
      Object.freeze({
        primaryError: classifyBackendError("BACKEND_INTERNAL_ERROR", "backend routing failed"),
      }),
    );
  }
}
