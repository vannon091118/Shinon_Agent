type ChatRole = "system" | "user" | "assistant";

type ChatUiMessage = {
  id?: string;
  role: ChatRole;
  content: string;
};

type ChatUiState = {
  sessionId?: string;
  conversationId?: string;
  requestId?: string;
  messages?: ReadonlyArray<ChatUiMessage>;
  metadata?: Record<string, string | number | boolean | null>;
  endpoint?: string;
  timeoutMs?: number;
  retries?: number;
  retryDelayMs?: number;
  headers?: Record<string, string>;
};

type ChatRequestDto = {
  message?: string;
  text?: string;
  prompt?: string;
  input?: string;
  content?: string;
  sessionId?: string;
  conversationId?: string;
  requestId?: string;
  messages?: Array<{
    role?: string;
    content?: unknown;
    id?: string;
  }>;
  metadata?: Record<string, string | number | boolean | null>;
};

type ChatResponseDto =
  | {
      ok: true;
      status: "success";
      data: {
        requestId: string;
        sessionId?: string;
        conversationId?: string;
        reply: string;
        message: {
          role: "assistant";
          content: string;
        };
        source: "orchestrator" | "fallback";
      };
    }
  | {
      ok: false;
      status: "error";
      error: {
        code:
          | "BAD_REQUEST"
          | "ORCHESTRATION_FAILED"
          | "INTERNAL_SERVER_ERROR";
        message: string;
        requestId?: string;
      };
    };

type BackendErrorCode =
  | "BAD_REQUEST"
  | "ORCHESTRATION_FAILED"
  | "INTERNAL_SERVER_ERROR";

type UiErrorCode =
  | "EMPTY_MESSAGE"
  | "NO_FETCH_IMPLEMENTATION"
  | "TIMEOUT"
  | "NETWORK_ERROR"
  | "HTTP_ERROR"
  | "INVALID_RESPONSE"
  | "BACKEND_ERROR";

type UiErrorState = {
  code: UiErrorCode;
  message: string;
  requestId: string;
  retryable: boolean;
  status?: number;
  apiCode?: BackendErrorCode;
  details?: string;
};

type UiEvent =
  | {
      type: "chat/request-prepared";
      requestId: string;
      payload: ChatRequestDto;
    }
  | {
      type: "chat/request-attempted";
      requestId: string;
      attempt: number;
      endpoint: string;
    }
  | {
      type: "chat/request-succeeded";
      requestId: string;
      reply: string;
      source: "orchestrator" | "fallback";
    }
  | {
      type: "chat/request-failed";
      requestId: string;
      error: UiErrorState;
    };

type SendChatRequestInput = {
  state: ChatUiState;
  userText: string;
  fetchImpl?: FetchLike;
  endpoint?: string;
  timeoutMs?: number;
  retries?: number;
  retryDelayMs?: number;
  headers?: Record<string, string>;
};

type SendChatRequestSuccess = {
  ok: true;
  requestPayload: ChatRequestDto;
  requestInit: RequestInitLike;
  uiEvents: UiEvent[];
  response: ChatResponseDto;
};

type SendChatRequestFailure = {
  ok: false;
  requestPayload: ChatRequestDto;
  requestInit: RequestInitLike;
  uiEvents: UiEvent[];
  error: UiErrorState;
};

export type SendChatRequestResult =
  | SendChatRequestSuccess
  | SendChatRequestFailure;

type RequestInitLike = {
  method: "POST";
  headers: Record<string, string>;
  body: string;
};

type FetchResponseLike = {
  ok?: boolean;
  status?: number;
  json?: () => Promise<unknown>;
  text?: () => Promise<string>;
};

type FetchLike = (
  input: string,
  init: RequestInitLike
) => Promise<FetchResponseLike>;

class ChatClientError extends Error {
  readonly requestId: string;
  readonly retryable: boolean;

  constructor(message: string, requestId: string, retryable: boolean) {
    super(message);
    this.name = "ChatClientError";
    this.requestId = requestId;
    this.retryable = retryable;
  }
}

class ChatTimeoutError extends ChatClientError {
  constructor(requestId: string, timeoutMs: number) {
    super(`Chat request timed out after ${timeoutMs}ms`, requestId, true);
    this.name = "ChatTimeoutError";
  }
}

class ChatNetworkError extends ChatClientError {
  constructor(requestId: string, message: string, retryable: boolean) {
    super(message, requestId, retryable);
    this.name = "ChatNetworkError";
  }
}

class ChatProtocolError extends ChatClientError {
  constructor(requestId: string, message: string) {
    super(message, requestId, false);
    this.name = "ChatProtocolError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function toPositiveInteger(value: unknown, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return fallback;
  }
  const normalized = Math.floor(value);
  return normalized >= 0 ? normalized : fallback;
}

function toNonEmptyString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function stableHash(seed: string): string {
  let hash = 2166136261;
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `chat_${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

function readUserText(input: string): string | null {
  return toNonEmptyString(input);
}

function normalizeMessages(
  messages: ReadonlyArray<ChatUiMessage> | undefined
): Array<{ role: string; content: unknown; id?: string }> {
  if (!messages || messages.length === 0) {
    return [];
  }

  const normalized: Array<{ role: string; content: unknown; id?: string }> = [];
  for (const message of messages) {
    const content = toNonEmptyString(message?.content);
    if (!content) {
      continue;
    }
    normalized.push({
      role:
        message.role === "system" || message.role === "assistant"
          ? message.role
          : "user",
      content,
      id: toNonEmptyString(message.id) ?? undefined,
    });
  }

  return normalized;
}

function buildRequestPayload(
  state: ChatUiState,
  userText: string,
  requestId: string
): ChatRequestDto {
  const payload: ChatRequestDto = {
    message: userText,
    text: userText,
    prompt: userText,
    input: userText,
    content: userText,
    sessionId: toNonEmptyString(state.sessionId) ?? undefined,
    conversationId: toNonEmptyString(state.conversationId) ?? undefined,
    requestId,
    messages: normalizeMessages(state.messages),
    metadata: state.metadata,
  };

  payload.messages = [...(payload.messages ?? []), { role: "user", content: userText }];
  return payload;
}

function buildRequestInit(
  payload: ChatRequestDto,
  headers: Record<string, string>
): RequestInitLike {
  return {
    method: "POST",
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...headers,
    },
    body: JSON.stringify(payload),
  };
}

function buildUiErrorState(
  code: UiErrorCode,
  message: string,
  requestId: string,
  options: {
    retryable?: boolean;
    status?: number;
    apiCode?: BackendErrorCode;
    details?: string;
  } = {}
): UiErrorState {
  return {
    code,
    message,
    requestId,
    retryable: options.retryable ?? false,
    status: options.status,
    apiCode: options.apiCode,
    details: options.details,
  };
}

function normalizeResponse(
  response: unknown,
  requestId: string
): ChatResponseDto {
  if (!isRecord(response)) {
    throw new ChatProtocolError(requestId, "Backend response is not an object");
  }

  const responseRecord = response as Record<string, any>;

  if (
    responseRecord.ok === true &&
    responseRecord.status === "success" &&
    isRecord(responseRecord.data)
  ) {
    const dataContainer = responseRecord.data as Record<string, any>;
    const data = isRecord(dataContainer.response)
      ? (dataContainer.response as Record<string, any>)
      : dataContainer;
    const reply = toNonEmptyString(data.reply);
    const message = isRecord(data.message)
      ? toNonEmptyString((data.message as Record<string, any>).content)
      : null;

    if (!reply || !message) {
      throw new ChatProtocolError(
        requestId,
        "Backend success response is missing reply content"
      );
    }

    return {
      ok: true,
      status: "success",
      data: {
        requestId: toNonEmptyString(data.requestId) ?? requestId,
        sessionId: toNonEmptyString(data.sessionId) ?? undefined,
        conversationId: toNonEmptyString(data.conversationId) ?? undefined,
        reply,
        message: {
          role: "assistant",
          content: message,
        },
        source: data.source === "fallback" ? "fallback" : "orchestrator",
      },
    };
  }

  if (
    responseRecord.ok === false &&
    responseRecord.status === "error" &&
    isRecord(responseRecord.error)
  ) {
    const error = responseRecord.error as Record<string, any>;
    const code =
      error.code === "BAD_REQUEST" ||
      error.code === "ORCHESTRATION_FAILED" ||
      error.code === "INTERNAL_SERVER_ERROR"
        ? (error.code as BackendErrorCode)
        : "INTERNAL_SERVER_ERROR";

    return {
      ok: false,
      status: "error",
      error: {
        code,
        message:
          toNonEmptyString(error.message) ??
          "Chat request failed on the backend",
        requestId: toNonEmptyString(error.requestId) ?? requestId,
      },
    };
  }

  throw new ChatProtocolError(requestId, "Backend response does not match contract");
}

function mapFailureToUiError(
  error: unknown,
  requestId: string,
  status?: number
): UiErrorState {
  if (error instanceof ChatTimeoutError) {
    return buildUiErrorState("TIMEOUT", error.message, error.requestId, {
      retryable: true,
      details: error.stack,
    });
  }

  if (error instanceof ChatNetworkError) {
    return buildUiErrorState("NETWORK_ERROR", error.message, error.requestId, {
      retryable: error.retryable,
      details: error.stack,
    });
  }

  if (error instanceof ChatProtocolError) {
    return buildUiErrorState("INVALID_RESPONSE", error.message, error.requestId, {
      retryable: false,
      details: error.stack,
    });
  }

  if (isRecord(error)) {
    const errorRecord = error as Record<string, any>;
    if (errorRecord.ok === false && errorRecord.status === "error" && isRecord(errorRecord.error)) {
      const backendError = errorRecord.error as Record<string, any>;
      const apiCode =
        backendError.code === "BAD_REQUEST" ||
        backendError.code === "ORCHESTRATION_FAILED" ||
        backendError.code === "INTERNAL_SERVER_ERROR"
          ? (backendError.code as BackendErrorCode)
          : "INTERNAL_SERVER_ERROR";
      return buildUiErrorState(
        "BACKEND_ERROR",
        toNonEmptyString(backendError.message) ?? "Chat request failed",
        requestId,
        {
          retryable: apiCode !== "BAD_REQUEST",
          status,
          apiCode,
        }
      );
    }
  }

  const fallbackMessage =
    error instanceof Error && toNonEmptyString(error.message)
      ? error.message
      : "Chat request failed";

  return buildUiErrorState("NETWORK_ERROR", fallbackMessage, requestId, {
    retryable: true,
    status,
    details: error instanceof Error ? error.stack : undefined,
  });
}

function sleep(ms: number): Promise<void> {
  if (ms <= 0) {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function withTimeout<T>(
  operation: Promise<T>,
  timeoutMs: number,
  requestId: string
): Promise<T> {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    return operation;
  }

  let timeoutHandle: ReturnType<typeof setTimeout> | undefined;
  return await new Promise<T>((resolve, reject) => {
    timeoutHandle = setTimeout(() => {
      reject(new ChatTimeoutError(requestId, timeoutMs));
    }, timeoutMs);

    operation.then(resolve, reject).finally(() => {
      if (timeoutHandle !== undefined) {
        clearTimeout(timeoutHandle);
      }
    });
  });
}

async function readResponseBody(
  response: FetchResponseLike,
  requestId: string
): Promise<unknown> {
  if (typeof response.json === "function") {
    try {
      return await response.json();
    } catch (error) {
      throw new ChatProtocolError(
        requestId,
        error instanceof Error ? error.message : "Unable to parse backend JSON"
      );
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
      return {
        ok: false,
        status: "error",
        error: {
          code: "INTERNAL_SERVER_ERROR",
          message: trimmed,
          requestId,
        },
      };
    }
  }

  return {};
}

async function performFetch(
  fetchImpl: FetchLike,
  endpoint: string,
  requestInit: RequestInitLike,
  requestId: string,
  timeoutMs: number
): Promise<ChatResponseDto> {
  const rawResponse = await withTimeout(
    fetchImpl(endpoint, requestInit),
    timeoutMs,
    requestId
  );

  if (!isRecord(rawResponse)) {
    throw new ChatNetworkError(
      requestId,
      "Fetch returned an invalid response object",
      true
    );
  }

  const response = rawResponse as FetchResponseLike;
  const body = await readResponseBody(response, requestId);
  const normalized = normalizeResponse(body, requestId);

  if (!response.ok && normalized.ok) {
    throw new ChatNetworkError(
      requestId,
      "Backend returned a success payload for a failing HTTP response",
      true
    );
  }

  return normalized;
}

function createFailureResult(
  requestPayload: ChatRequestDto,
  requestInit: RequestInitLike,
  uiEvents: UiEvent[],
  error: UiErrorState
): SendChatRequestFailure {
  return {
    ok: false,
    requestPayload,
    requestInit,
    uiEvents,
    error,
  };
}

function createSuccessResult(
  requestPayload: ChatRequestDto,
  requestInit: RequestInitLike,
  uiEvents: UiEvent[],
  response: ChatResponseDto
): SendChatRequestSuccess {
  return {
    ok: true,
    requestPayload,
    requestInit,
    uiEvents,
    response,
  };
}

export async function sendChatRequest(
  input: SendChatRequestInput
): Promise<SendChatRequestResult> {
  const userText = readUserText(input.userText);
  const state = input.state ?? {};
  const requestId =
    toNonEmptyString(state.requestId) ??
    stableHash(
      [
        toNonEmptyString(state.sessionId) ?? "",
        toNonEmptyString(state.conversationId) ?? "",
        userText ?? "",
        String(normalizeMessages(state.messages).length),
      ].join("|")
    );

  const payload = buildRequestPayload(state, userText ?? "", requestId);
  const requestInit = buildRequestInit(payload, {
    ...(state.headers ?? {}),
    ...(input.headers ?? {}),
  });

  const uiEvents: UiEvent[] = [
    {
      type: "chat/request-prepared",
      requestId,
      payload,
    },
  ];

  if (!userText) {
    const error = buildUiErrorState(
      "EMPTY_MESSAGE",
      "Chat message must not be empty",
      requestId,
      {
        retryable: false,
      }
    );
    uiEvents.push({
      type: "chat/request-failed",
      requestId,
      error,
    });
    return createFailureResult(payload, requestInit, uiEvents, error);
  }

  const fetchImpl =
    input.fetchImpl ??
    (typeof globalThis.fetch === "function"
      ? (globalThis.fetch.bind(globalThis) as unknown as FetchLike)
      : undefined);

  if (!fetchImpl) {
    const error = buildUiErrorState(
      "NO_FETCH_IMPLEMENTATION",
      "No fetch implementation is available",
      requestId,
      { retryable: true }
    );
    uiEvents.push({
      type: "chat/request-failed",
      requestId,
      error,
    });
    return createFailureResult(payload, requestInit, uiEvents, error);
  }

  const endpoint =
    toNonEmptyString(input.endpoint) ??
    toNonEmptyString(state.endpoint) ??
    "/api/chat";
  const timeoutMs = toPositiveInteger(input.timeoutMs ?? state.timeoutMs, 10_000);
  const retries = toPositiveInteger(input.retries ?? state.retries, 0);
  const retryDelayMs = toPositiveInteger(
    input.retryDelayMs ?? state.retryDelayMs,
    0
  );

  let lastError: unknown = undefined;

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    uiEvents.push({
      type: "chat/request-attempted",
      requestId,
      attempt: attempt + 1,
      endpoint,
    });

    try {
      const response = await performFetch(
        fetchImpl,
        endpoint,
        requestInit,
        requestId,
        timeoutMs
      );

      if (response.ok) {
        uiEvents.push({
          type: "chat/request-succeeded",
          requestId,
          reply: response.data.reply,
          source: response.data.source,
        });
        return createSuccessResult(payload, requestInit, uiEvents, response);
      }

      const error = mapFailureToUiError(response, requestId);
      uiEvents.push({
        type: "chat/request-failed",
        requestId,
        error,
      });
      return createFailureResult(payload, requestInit, uiEvents, error);
    } catch (error) {
      lastError = error;
      const uiError = mapFailureToUiError(error, requestId);
      const canRetry = uiError.retryable && attempt < retries;

      if (!canRetry) {
        uiEvents.push({
          type: "chat/request-failed",
          requestId,
          error: uiError,
        });
        return createFailureResult(payload, requestInit, uiEvents, uiError);
      }

      if (retryDelayMs > 0) {
        await sleep(retryDelayMs);
      }
    }
  }

  const fallbackError = mapFailureToUiError(lastError, requestId);
  uiEvents.push({
    type: "chat/request-failed",
    requestId,
    error: fallbackError,
  });
  return createFailureResult(payload, requestInit, uiEvents, fallbackError);
}


