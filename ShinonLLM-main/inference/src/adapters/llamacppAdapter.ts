type ChatRole = "system" | "user" | "assistant";

type PlainObject = Record<string, unknown>;

type FetchResponseLike = Readonly<{
  ok?: boolean;
  status?: number;
  json?: () => Promise<unknown>;
  text?: () => Promise<string>;
}>;

type FetchLike = (
  input: string,
  init: PlainObject
) => Promise<FetchResponseLike>;

type BackendErrorCode =
  | "BAD_REQUEST"
  | "UNREACHABLE"
  | "TIMEOUT"
  | "SCHEMA"
  | "CAPACITY"
  | "INTERNAL_SERVER_ERROR";

type BackendError = Readonly<{
  code: BackendErrorCode;
  message: string;
  status?: number;
  details?: string;
}>;

type RouteDecision = Readonly<{
  endpoint: string;
  path?: string;
  model?: string;
  slot?: string;
  headers?: Readonly<Record<string, string>>;
  timeoutMs?: number;
  temperature?: number;
  topP?: number;
  maxTokens?: number;
  stream?: boolean;
  apiKey?: string;
  authorization?: string;
  fetchImpl?: FetchLike;
}>;

type PromptMessage = Readonly<{
  role: ChatRole;
  content: string;
}>;

type PromptPayload = Readonly<{
  prompt?: string;
  systemPrompt?: string;
  userText?: string;
  content?: string;
  messages?: ReadonlyArray<PromptMessage>;
  assistantPayload?: {
    content?: string;
    systemPrompt?: string;
    messages?: ReadonlyArray<PromptMessage>;
  };
  model?: string;
  metadata?: PlainObject;
}>;

type LlamaCppRequest = Readonly<{
  routeDecision: RouteDecision;
  promptPayload: PromptPayload;
}>;

type NormalizedModelResponse = Readonly<{
  backend: "llamacpp";
  model: string;
  slot: string;
  reply: string;
  message: Readonly<{
    role: "assistant";
    content: string;
  }>;
  source: "llama.cpp";
  prompt: string;
  usage: Readonly<{
    promptTokens?: number;
    completionTokens?: number;
    totalTokens?: number;
  }>;
  raw: unknown;
}>;

const DEFAULT_CHAT_PATH = "/v1/chat/completions";
const DEFAULT_TIMEOUT_MS = 30_000;

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function failClosed(code: BackendErrorCode, message: string, details?: string, status?: number): never {
  throw Object.freeze({
    code,
    message,
    status,
    details,
  } as BackendError);
}

function toPositiveInteger(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value) && value > 0) {
    return Math.floor(value);
  }
  return fallback;
}

function normalizeHeaders(input: unknown): Record<string, string> {
  if (!isPlainObject(input)) {
    return {};
  }

  const headers: Record<string, string> = {};
  for (const [key, value] of Object.entries(input)) {
    if (typeof value === "string" && value.trim().length > 0) {
      headers[key] = value.trim();
    }
  }
  return headers;
}

function normalizeMessages(input: unknown): PromptMessage[] {
  if (!Array.isArray(input)) {
    return [];
  }

  const messages: PromptMessage[] = [];
  for (const entry of input) {
    if (!isPlainObject(entry)) {
      continue;
    }

    const role = entry.role === "system" || entry.role === "assistant" ? entry.role : "user";
    if (!isNonEmptyString(entry.content)) {
      continue;
    }

    messages.push(
      Object.freeze({
        role,
        content: entry.content.trim(),
      })
    );
  }

  return messages;
}

function extractPromptText(payload: PromptPayload): string {
  if (isNonEmptyString(payload.prompt)) {
    return payload.prompt.trim();
  }

  if (isNonEmptyString(payload.systemPrompt)) {
    return payload.systemPrompt.trim();
  }

  if (isNonEmptyString(payload.userText)) {
    return payload.userText.trim();
  }

  if (isNonEmptyString(payload.content)) {
    return payload.content.trim();
  }

  if (isPlainObject(payload.assistantPayload)) {
    const assistantContent = payload.assistantPayload.content;
    if (isNonEmptyString(assistantContent)) {
      return assistantContent.trim();
    }
    if (isNonEmptyString(payload.assistantPayload.systemPrompt)) {
      return payload.assistantPayload.systemPrompt.trim();
    }
  }

  return "";
}

function buildRequestMessages(payload: PromptPayload): PromptMessage[] {
  const directMessages = normalizeMessages(payload.messages);
  if (directMessages.length > 0) {
    return directMessages;
  }

  if (isPlainObject(payload.assistantPayload)) {
    const assistantMessages = normalizeMessages(payload.assistantPayload.messages);
    if (assistantMessages.length > 0) {
      return assistantMessages;
    }
  }

  const promptText = extractPromptText(payload);
  if (!promptText) {
    return [];
  }

  const messages: PromptMessage[] = [];

  if (isNonEmptyString(payload.systemPrompt)) {
    messages.push(
      Object.freeze({
        role: "system",
        content: payload.systemPrompt.trim(),
      })
    );
  } else if (isPlainObject(payload.assistantPayload) && isNonEmptyString(payload.assistantPayload.systemPrompt)) {
    messages.push(
      Object.freeze({
        role: "system",
        content: payload.assistantPayload.systemPrompt.trim(),
      })
    );
  }

  messages.push(
    Object.freeze({
      role: "user",
      content: promptText,
    })
  );

  return messages;
}

function resolveEndpoint(routeDecision: RouteDecision): string {
  if (!isNonEmptyString(routeDecision.endpoint)) {
    failClosed("BAD_REQUEST", "routeDecision.endpoint must be a non-empty string");
  }

  const trimmedEndpoint = routeDecision.endpoint.trim();
  const normalizedPath = isNonEmptyString(routeDecision.path) ? routeDecision.path.trim() : DEFAULT_CHAT_PATH;

  if (/\/v1\/chat\/completions(?:[?#].*)?$/u.test(trimmedEndpoint) || /\/completion(?:[?#].*)?$/u.test(trimmedEndpoint)) {
    return trimmedEndpoint;
  }

  if (normalizedPath.startsWith("/")) {
    return `${trimmedEndpoint.replace(/\/+$/u, "")}${normalizedPath}`;
  }

  return `${trimmedEndpoint.replace(/\/+$/u, "")}/${normalizedPath}`;
}

function resolveModel(routeDecision: RouteDecision, payload: PromptPayload): string {
  const model = [routeDecision.model, routeDecision.slot, payload.model].find(isNonEmptyString);
  return model ? model.trim() : "llamacpp-default";
}

function buildRequestInit(routeDecision: RouteDecision, payload: PromptPayload): PlainObject {
  const messages = buildRequestMessages(payload);
  const model = resolveModel(routeDecision, payload);
  const body: PlainObject = {
    model,
    stream: routeDecision.stream === true,
  };

  if (messages.length > 0) {
    body.messages = messages;
  } else {
    const prompt = extractPromptText(payload);
    if (!prompt) {
      failClosed("BAD_REQUEST", "prompt payload must include prompt text or messages");
    }
    body.prompt = prompt;
  }

  if (typeof routeDecision.temperature === "number" && Number.isFinite(routeDecision.temperature)) {
    body.temperature = routeDecision.temperature;
  }
  if (typeof routeDecision.topP === "number" && Number.isFinite(routeDecision.topP)) {
    body.top_p = routeDecision.topP;
  }
  if (typeof routeDecision.maxTokens === "number" && Number.isFinite(routeDecision.maxTokens) && routeDecision.maxTokens > 0) {
    body.max_tokens = Math.floor(routeDecision.maxTokens);
  }

  const headers = {
    "content-type": "application/json; charset=utf-8",
    ...normalizeHeaders(routeDecision.headers),
  };

  if (isNonEmptyString(routeDecision.apiKey)) {
    headers.authorization = `Bearer ${routeDecision.apiKey.trim()}`;
  } else if (isNonEmptyString(routeDecision.authorization)) {
    headers.authorization = routeDecision.authorization.trim();
  }

  return {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  };
}

function isTimeoutError(error: unknown): boolean {
  return error instanceof Error && /timeout|aborted/i.test(error.message);
}

function classifyStatus(status: number): BackendErrorCode {
  if (status === 429 || status === 503 || status === 529) {
    return "CAPACITY";
  }
  if (status >= 500) {
    return "UNREACHABLE";
  }
  if (status >= 400) {
    return "BAD_REQUEST";
  }
  return "INTERNAL_SERVER_ERROR";
}

function readErrorMessage(body: unknown, fallback: string): string {
  if (isPlainObject(body)) {
    if (isNonEmptyString(body.message)) {
      return body.message.trim();
    }
    if (isPlainObject(body.error) && isNonEmptyString(body.error.message)) {
      return body.error.message.trim();
    }
    if (isNonEmptyString(body.error)) {
      return body.error.trim();
    }
  }

  if (isNonEmptyString(body)) {
    return body.trim();
  }

  return fallback;
}

function extractUsage(body: unknown): NormalizedModelResponse["usage"] {
  if (!isPlainObject(body) || !isPlainObject(body.usage)) {
    return Object.freeze({});
  }

  const usage: {
    promptTokens?: number;
    completionTokens?: number;
    totalTokens?: number;
  } = {};

  if (typeof body.usage.prompt_tokens === "number" && Number.isFinite(body.usage.prompt_tokens)) {
    usage.promptTokens = Math.floor(body.usage.prompt_tokens);
  }
  if (typeof body.usage.completion_tokens === "number" && Number.isFinite(body.usage.completion_tokens)) {
    usage.completionTokens = Math.floor(body.usage.completion_tokens);
  }
  if (typeof body.usage.total_tokens === "number" && Number.isFinite(body.usage.total_tokens)) {
    usage.totalTokens = Math.floor(body.usage.total_tokens);
  }

  return Object.freeze(usage);
}

function extractReply(body: unknown): string | null {
  if (isNonEmptyString(body)) {
    return body.trim();
  }

  if (!isPlainObject(body)) {
    return null;
  }

  if (isNonEmptyString(body.reply)) {
    return body.reply.trim();
  }
  if (isNonEmptyString(body.response)) {
    return body.response.trim();
  }
  if (isNonEmptyString(body.content)) {
    return body.content.trim();
  }
  if (isNonEmptyString(body.text)) {
    return body.text.trim();
  }

  if (Array.isArray(body.choices) && body.choices.length > 0) {
    const firstChoice = body.choices[0];
    if (isPlainObject(firstChoice)) {
      if (isPlainObject(firstChoice.message) && isNonEmptyString(firstChoice.message.content)) {
        return firstChoice.message.content.trim();
      }
      if (isNonEmptyString(firstChoice.text)) {
        return firstChoice.text.trim();
      }
      if (isNonEmptyString(firstChoice.content)) {
        return firstChoice.content.trim();
      }
    }
  }

  if (isPlainObject(body.message) && isNonEmptyString(body.message.content)) {
    return body.message.content.trim();
  }

  return null;
}

async function readResponseBody(response: FetchResponseLike): Promise<unknown> {
  if (typeof response.json === "function") {
    try {
      return await response.json();
    } catch {
      // fall through to text parsing
    }
  }

  if (typeof response.text === "function") {
    const text = await response.text();
    const trimmed = text.trim();
    if (!trimmed) {
      return {};
    }
    try {
      return JSON.parse(trimmed);
    } catch {
      return trimmed;
    }
  }

  return {};
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    return promise;
  }

  let timeoutHandle: ReturnType<typeof setTimeout> | undefined;
  return await new Promise<T>((resolve, reject) => {
    timeoutHandle = setTimeout(() => {
      reject(
        Object.freeze({
          code: "TIMEOUT",
          message: `llama.cpp request timed out after ${timeoutMs}ms`,
        } as BackendError)
      );
    }, timeoutMs);

    promise.then(resolve, reject).finally(() => {
      if (timeoutHandle !== undefined) {
        clearTimeout(timeoutHandle);
      }
    });
  });
}

function normalizeSuccessResponse(
  body: unknown,
  routeDecision: RouteDecision,
  payload: PromptPayload,
  raw: unknown
): NormalizedModelResponse {
  const reply = extractReply(body);
  if (!reply) {
    failClosed("SCHEMA", "llama.cpp response does not contain assistant text");
  }

  const model = isPlainObject(body) && isNonEmptyString(body.model)
    ? body.model.trim()
    : resolveModel(routeDecision, payload);

  const prompt = extractPromptText(payload);
  if (!prompt) {
    failClosed("BAD_REQUEST", "prompt payload must contain text");
  }

  return Object.freeze({
    backend: "llamacpp",
    model,
    slot: isNonEmptyString(routeDecision.slot) ? routeDecision.slot.trim() : model,
    reply,
    message: Object.freeze({
      role: "assistant",
      content: reply,
    }),
    source: "llama.cpp",
    prompt,
    usage: extractUsage(body),
    raw,
  });
}

function normalizeFailureResponse(body: unknown, status: number): BackendError {
  const code = classifyStatus(status);
  const fallbackMessage =
    code === "CAPACITY"
      ? "llama.cpp backend is at capacity"
      : code === "BAD_REQUEST"
        ? "llama.cpp rejected the request"
        : code === "UNREACHABLE"
          ? "llama.cpp backend is unreachable"
          : "llama.cpp request failed";

  return Object.freeze({
    code,
    message: readErrorMessage(body, fallbackMessage),
    status,
  });
}

function isFetchLike(value: unknown): value is FetchLike {
  return typeof value === "function";
}

export async function callLlamaCpp(input: LlamaCppRequest): Promise<NormalizedModelResponse> {
  if (!isPlainObject(input)) {
    failClosed("BAD_REQUEST", "callLlamaCpp requires a request object");
  }

  if (!isPlainObject(input.routeDecision)) {
    failClosed("BAD_REQUEST", "callLlamaCpp requires a route decision object");
  }

  if (!isPlainObject(input.promptPayload)) {
    failClosed("BAD_REQUEST", "callLlamaCpp requires a prompt payload object");
  }

  const routeDecision = input.routeDecision as RouteDecision;
  const promptPayload = input.promptPayload as PromptPayload;
  const endpoint = resolveEndpoint(routeDecision);
  const requestInit = buildRequestInit(routeDecision, promptPayload);
  const timeoutMs = toPositiveInteger(routeDecision.timeoutMs, DEFAULT_TIMEOUT_MS);
  const fetchImpl = routeDecision.fetchImpl ?? (globalThis as { fetch?: unknown }).fetch;

  if (!isFetchLike(fetchImpl)) {
    failClosed("BAD_REQUEST", "No fetch implementation is available for llama.cpp");
  }

  try {
    const response = await withTimeout(fetchImpl(endpoint, requestInit), timeoutMs);
    if (!isPlainObject(response)) {
      failClosed("UNREACHABLE", "llama.cpp fetch returned an invalid response object");
    }

    const fetchResponse = response as FetchResponseLike;
    const body = await readResponseBody(fetchResponse);
    const status = typeof fetchResponse.status === "number" ? fetchResponse.status : 0;

    if (fetchResponse.ok === false || (status >= 400 && status !== 0)) {
      throw normalizeFailureResponse(body, status);
    }

    return normalizeSuccessResponse(body, routeDecision, promptPayload, body);
  } catch (error) {
    if (isPlainObject(error) && isNonEmptyString(error.code) && isNonEmptyString(error.message)) {
      throw Object.freeze({
        code: error.code,
        message: error.message,
        status: typeof error.status === "number" ? error.status : undefined,
        details: isNonEmptyString(error.details) ? error.details : undefined,
      } as BackendError);
    }

    if (isTimeoutError(error)) {
      throw Object.freeze({
        code: "TIMEOUT",
        message: error.message.trim(),
      } as BackendError);
    }

    if (error instanceof Error) {
      throw Object.freeze({
        code: "UNREACHABLE",
        message: error.message.trim().length > 0 ? error.message.trim() : "llama.cpp backend is unreachable",
        details: error.stack,
      } as BackendError);
    }

    throw Object.freeze({
      code: "INTERNAL_SERVER_ERROR",
      message: "llama.cpp adapter failed",
    } as BackendError);
  }
}
