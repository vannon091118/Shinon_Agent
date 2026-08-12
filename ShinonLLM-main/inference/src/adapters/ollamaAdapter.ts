type PlainObject = Record<string, unknown>;

export type BackendErrorCode =
  | "BAD_REQUEST"
  | "TIMEOUT"
  | "NETWORK_ERROR"
  | "UPSTREAM_ERROR"
  | "INVALID_RESPONSE"
  | "INTERNAL_SERVER_ERROR";

export type BackendRouteDecision = Readonly<{
  backend?: "ollama";
  model?: string;
  baseUrl?: string;
  endpoint?: string;
  timeoutMs?: number;
  stream?: boolean;
  headers?: Readonly<Record<string, string>>;
  policyId?: string;
  options?: Readonly<Record<string, unknown>>;
}>;

export type OllamaMessage = Readonly<{
  role: "system" | "user" | "assistant";
  content: string;
}>;

export type OllamaPromptPayload = Readonly<{
  prompt?: string;
  messages?: ReadonlyArray<OllamaMessage>;
  systemPrompt?: string;
  userText?: string;
  requestId?: string;
  sessionId?: string;
  conversationId?: string;
  format?: string;
  options?: Readonly<Record<string, unknown>>;
}>;

export type NormalizedModelResponse = Readonly<{
  backend: "ollama";
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
  code: BackendErrorCode;
  message: string;
  status: number;
  details?: Readonly<Record<string, unknown>>;
}>;

const DEFAULT_BASE_URL = "http://127.0.0.1:11434";
const DEFAULT_ENDPOINT = "/api/chat";
const DEFAULT_TIMEOUT_MS = 60_000;

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isMessageArray(value: unknown): value is ReadonlyArray<OllamaMessage> {
  return Array.isArray(value) && value.every((entry) => {
    return (
      isPlainObject(entry) &&
      (entry.role === "system" || entry.role === "user" || entry.role === "assistant") &&
      isNonEmptyString(entry.content)
    );
  });
}

function trimSlash(value: string): string {
  return value.replace(/\/+$/u, "");
}

function normalizeUrl(baseUrl: string, endpoint: string): string {
  return `${trimSlash(baseUrl)}/${endpoint.replace(/^\/+/u, "")}`;
}

function toInteger(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) && value > 0
    ? Math.floor(value)
    : fallback;
}

function resolveInvocation(
  first: unknown,
  second: unknown,
): { routeDecision: PlainObject; promptPayload: unknown } {
  if (second === undefined && isPlainObject(first) && ("routeDecision" in first || "promptPayload" in first)) {
    return {
      routeDecision: isPlainObject(first.routeDecision) ? first.routeDecision : first,
      promptPayload: "promptPayload" in first ? first.promptPayload : undefined,
    };
  }

  return {
    routeDecision: isPlainObject(first) ? first : {},
    promptPayload: second,
  };
}

function readRequestId(promptPayload: unknown): {
  requestId?: string;
  sessionId?: string;
  conversationId?: string;
} {
  if (!isPlainObject(promptPayload)) {
    return {};
  }

  return {
    requestId: isNonEmptyString(promptPayload.requestId) ? promptPayload.requestId.trim() : undefined,
    sessionId: isNonEmptyString(promptPayload.sessionId) ? promptPayload.sessionId.trim() : undefined,
    conversationId: isNonEmptyString(promptPayload.conversationId) ? promptPayload.conversationId.trim() : undefined,
  };
}

function extractPromptText(promptPayload: unknown): string {
  if (isNonEmptyString(promptPayload)) {
    return promptPayload.trim();
  }

  if (!isPlainObject(promptPayload)) {
    return "";
  }

  if (isNonEmptyString(promptPayload.prompt)) {
    return promptPayload.prompt.trim();
  }

  if (isNonEmptyString(promptPayload.userText)) {
    return promptPayload.userText.trim();
  }

  if (isMessageArray(promptPayload.messages)) {
    return promptPayload.messages.map((message) => `${message.role.toUpperCase()}: ${message.content.trim()}`).join("\n");
  }

  return "";
}

function buildMessages(promptPayload: unknown): ReadonlyArray<OllamaMessage> | undefined {
  if (!isPlainObject(promptPayload) || !isMessageArray(promptPayload.messages)) {
    return undefined;
  }

  const messages: OllamaMessage[] = [];

  if (isNonEmptyString(promptPayload.systemPrompt)) {
    messages.push({ role: "system", content: promptPayload.systemPrompt.trim() });
  }

  for (const message of promptPayload.messages) {
    messages.push({
      role: message.role,
      content: message.content.trim(),
    });
  }

  if (messages.length === 0) {
    return undefined;
  }

  return Object.freeze(messages);
}

function buildBody(
  routeDecision: BackendRouteDecision,
  promptPayload: unknown,
): PlainObject {
  const messages = buildMessages(promptPayload);
  const promptText = extractPromptText(promptPayload);
  const stream = routeDecision.stream !== false;

  const body: PlainObject = {
    model: routeDecision.model?.trim(),
    stream,
  };

  if (messages && messages.length > 0) {
    body.messages = messages;
  } else if (promptText.length > 0) {
    body.prompt = promptText;
  }

  if (isPlainObject(promptPayload) && isPlainObject(promptPayload.options)) {
    body.options = {
      ...promptPayload.options,
      ...(isPlainObject(routeDecision.options) ? routeDecision.options : {}),
    };
  } else if (isPlainObject(routeDecision.options)) {
    body.options = { ...routeDecision.options };
  }

  if (isPlainObject(promptPayload) && isNonEmptyString(promptPayload.format)) {
    body.format = promptPayload.format.trim();
  }

  return body;
}

function classifyBackendError(
  code: BackendErrorCode,
  message: string,
  status: number,
  details?: Readonly<Record<string, unknown>>,
): ClassifiedBackendError {
  return Object.freeze({
    code,
    message,
    status,
    ...(details ? { details } : {}),
  });
}

function failClosed(
  code: BackendErrorCode,
  message: string,
  status: number,
  details?: Readonly<Record<string, unknown>>,
): never {
  throw classifyBackendError(code, message, status, details);
}

function toResponseContent(payload: unknown): string {
  if (isNonEmptyString(payload)) {
    return payload.trim();
  }

  if (!isPlainObject(payload)) {
    return "";
  }

  const direct = [
    payload.content,
    payload.response,
    payload.text,
  ];

  for (const candidate of direct) {
    if (isNonEmptyString(candidate)) {
      return candidate.trim();
    }
  }

  if (isPlainObject(payload.message) && isNonEmptyString(payload.message.content)) {
    return payload.message.content.trim();
  }

  if (isPlainObject(payload.data)) {
    return toResponseContent(payload.data);
  }

  return "";
}

async function readStreamedResponse(response: Response): Promise<{ raw: unknown; content: string }> {
  const reader = response.body?.getReader();
  if (!reader) {
    const raw = await response.json().catch(() => null);
    const content = toResponseContent(raw);
    return { raw, content };
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let raw: unknown = null;
  let content = "";

  const drainLine = (line: string): void => {
    if (!line) {
      return;
    }

    const parsed = JSON.parse(line) as unknown;
    raw = parsed;
    const chunk = toResponseContent(parsed);
    if (chunk.length > 0) {
      content += chunk;
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      let newlineIndex = buffer.indexOf("\n");
      while (newlineIndex >= 0) {
        const line = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);
        if (line.length > 0) {
          drainLine(line);
        }
        newlineIndex = buffer.indexOf("\n");
      }
    }

    const tail = buffer.trim();
    if (tail.length > 0) {
      drainLine(tail);
    }
  } finally {
    reader.releaseLock();
  }

  return { raw, content };
}

function buildNormalizedResponse(
  routeDecision: BackendRouteDecision,
  promptPayload: unknown,
  raw: unknown,
  content: string,
  streamed: boolean,
): NormalizedModelResponse {
  const requestMeta = readRequestId(promptPayload);
  const model = routeDecision.model?.trim() ?? "";

  if (!isNonEmptyString(model)) {
    failClosed("BAD_REQUEST", "route decision requires a model", 400);
  }

  if (!isNonEmptyString(content)) {
    failClosed("INVALID_RESPONSE", "ollama response did not contain assistant content", 502, {
      model,
    });
  }

  return Object.freeze({
    backend: "ollama",
    model,
    content: content.trim(),
    message: Object.freeze({
      role: "assistant",
      content: content.trim(),
    }),
    streamed,
    raw,
    ...(requestMeta.requestId ? { requestId: requestMeta.requestId } : {}),
    ...(requestMeta.sessionId ? { sessionId: requestMeta.sessionId } : {}),
    ...(requestMeta.conversationId ? { conversationId: requestMeta.conversationId } : {}),
  });
}

function normalizeRouteDecision(candidate: unknown): BackendRouteDecision {
  if (!isPlainObject(candidate)) {
    failClosed("BAD_REQUEST", "route decision must be a plain object", 400);
  }

  const model = isNonEmptyString(candidate.model) ? candidate.model.trim() : "";
  if (!isNonEmptyString(model)) {
    failClosed("BAD_REQUEST", "route decision requires a non-empty model", 400);
  }

  const env = (globalThis as typeof globalThis & {
    process?: {
      env?: Record<string, string | undefined>;
    };
  }).process?.env;

  const baseUrl = isNonEmptyString(candidate.baseUrl)
    ? candidate.baseUrl.trim()
    : env?.OLLAMA_BASE_URL?.trim() || DEFAULT_BASE_URL;

  const endpoint = isNonEmptyString(candidate.endpoint) ? candidate.endpoint.trim() : DEFAULT_ENDPOINT;

  return Object.freeze({
    backend: "ollama",
    model,
    baseUrl,
    endpoint,
    timeoutMs: toInteger(candidate.timeoutMs, DEFAULT_TIMEOUT_MS),
    stream: candidate.stream !== false,
    headers: isPlainObject(candidate.headers) ? Object.freeze({ ...candidate.headers }) : undefined,
    policyId: isNonEmptyString(candidate.policyId) ? candidate.policyId.trim() : undefined,
    options: isPlainObject(candidate.options) ? Object.freeze({ ...candidate.options }) : undefined,
  });
}

function validatePromptPayload(promptPayload: unknown): void {
  if (promptPayload === undefined || promptPayload === null) {
    failClosed("BAD_REQUEST", "prompt payload is required", 400);
  }

  const promptText = extractPromptText(promptPayload);
  if (!isNonEmptyString(promptText) && !isMessageArray(isPlainObject(promptPayload) ? promptPayload.messages : undefined)) {
    failClosed("BAD_REQUEST", "prompt payload requires prompt text or messages", 400);
  }
}

async function performRequest(
  routeDecision: BackendRouteDecision,
  promptPayload: unknown,
): Promise<NormalizedModelResponse> {
  validatePromptPayload(promptPayload);

  const controller = new AbortController();
  const timeout = globalThis.setTimeout(() => controller.abort(), routeDecision.timeoutMs ?? DEFAULT_TIMEOUT_MS);

  try {
    const body = buildBody(routeDecision, promptPayload);
    const response = await fetch(normalizeUrl(routeDecision.baseUrl ?? DEFAULT_BASE_URL, routeDecision.endpoint ?? DEFAULT_ENDPOINT), {
      method: "POST",
      signal: controller.signal,
      headers: {
        "content-type": "application/json; charset=utf-8",
        ...(routeDecision.headers ?? {}),
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const details = {
        status: response.status,
        statusText: response.statusText,
      };

      failClosed(
        response.status === 400 ? "BAD_REQUEST" : "UPSTREAM_ERROR",
        `ollama request failed with status ${response.status}`,
        response.status,
        details,
      );
    }

    if (routeDecision.stream) {
      const streamed = await readStreamedResponse(response);
      return buildNormalizedResponse(routeDecision, promptPayload, streamed.raw, streamed.content, true);
    }

    const raw = await response.json().catch(async () => response.text());
    const content = toResponseContent(raw);
    return buildNormalizedResponse(routeDecision, promptPayload, raw, content, false);
  } catch (error) {
    if (isPlainObject(error) && typeof error.code === "string" && typeof error.message === "string" && typeof error.status === "number") {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      failClosed("TIMEOUT", "ollama request timed out", 504);
    }

    if (error instanceof TypeError) {
      failClosed("NETWORK_ERROR", error.message || "ollama request failed", 502);
    }

    failClosed("INTERNAL_SERVER_ERROR", "ollama request failed", 500);
  } finally {
    globalThis.clearTimeout(timeout);
  }
}

export async function callOllama(
  routeDecisionOrInput: unknown,
  promptPayload?: unknown,
): Promise<NormalizedModelResponse> {
  const invocation = resolveInvocation(routeDecisionOrInput, promptPayload);
  const routeDecision = normalizeRouteDecision(invocation.routeDecision);
  return performRequest(routeDecision, invocation.promptPayload);
}
