import { orchestrateTurn as defaultRuntimeOrchestrateTurn } from "../../../orchestrator/src/pipeline/orchestrateTurn.js";
import {
  createInMemorySessionMemoryPersistence,
  type SessionMemoryPersistence,
} from "../../../memory/src/session/sessionPersistence.js";

export type ChatRequestDto = {
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

export type ChatResponseDto =
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

type ChatErrorCode =
  | "BAD_REQUEST"
  | "ORCHESTRATION_FAILED"
  | "INTERNAL_SERVER_ERROR";

type ChatRole = "system" | "user" | "assistant";

type PlainObject = Record<string, unknown>;
type ChatRouteErrorLike = {
  code?: string;
  message?: string;
  error?: {
    code?: string;
    message?: string;
  };
};

type ChatHttpResponseLike = {
  status?: (code: number) => ChatHttpResponseLike;
  json?: (body: unknown) => unknown;
  send?: (body: unknown) => unknown;
  end?: (body?: unknown) => unknown;
  setHeader?: (name: string, value: string) => void;
};

type NormalizedChatTurn = {
  request: ChatRequestDto;
  userText: string;
  history: Array<{
    role: ChatRole;
    content: string;
  }>;
  memoryContext: Record<string, unknown>;
};

export type ChatRouteDependencies = {
  validateChatRequestMiddleware?: (request: unknown) => unknown;
  orchestrateTurn?: (
    input: NormalizedChatTurn
  ) => Promise<unknown> | unknown;
  memoryContext?: Record<string, unknown>;
  sessionMemoryPersistence?: SessionMemoryPersistence;
  memoryTtlSeconds?: number;
  memoryDecayKeepLatest?: number;
};

export type ChatRouteHandler = {
  (request: unknown, response?: ChatHttpResponseLike): Promise<ChatResponseDto> | ChatResponseDto;
  method: "POST";
  path: "/chat";
  routeName: "chat";
  handle: (request: unknown, response?: ChatHttpResponseLike) => Promise<ChatResponseDto> | ChatResponseDto;
};

const ERROR_STATUS_BY_CODE: Record<ChatErrorCode, number> = {
  BAD_REQUEST: 400,
  ORCHESTRATION_FAILED: 502,
  INTERNAL_SERVER_ERROR: 500,
};

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function readPayload(request: unknown): unknown {
  if (isPlainObject(request) && "body" in request) {
    return (request as { body?: unknown }).body;
  }
  return request;
}

function readValidatedRequest(
  middlewareResult: unknown,
  fallbackPayload: unknown
): ChatRequestDto {
  if (isPlainObject(middlewareResult)) {
    if ("ok" in middlewareResult && middlewareResult.ok === false) {
      const message =
        isPlainObject(middlewareResult.error) && isNonEmptyString(middlewareResult.error.message)
          ? middlewareResult.error.message.trim()
          : "Chat request rejected by middleware";
      throw {
        code: "BAD_REQUEST",
        message,
      } as ChatRouteErrorLike;
    }

    if (
      "body" in middlewareResult &&
      isPlainObject(middlewareResult.body) &&
      middlewareResult.body.ok === true &&
      isPlainObject(middlewareResult.body.data)
    ) {
      const payload = middlewareResult.body.data.payload;
      if (isPlainObject(payload)) {
        return payload as ChatRequestDto;
      }
      return isPlainObject(fallbackPayload) ? (fallbackPayload as ChatRequestDto) : ({} as ChatRequestDto);
    }

    return middlewareResult as ChatRequestDto;
  }

  return isPlainObject(fallbackPayload) ? (fallbackPayload as ChatRequestDto) : ({} as ChatRequestDto);
}

function toStringOrNull(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  return null;
}

function extractMessageContent(candidate: unknown): string | null {
  if (isNonEmptyString(candidate)) {
    return candidate.trim();
  }

  if (!isPlainObject(candidate)) {
    return null;
  }

  const directFields = ["message", "text", "prompt", "input", "content"] as const;
  for (const field of directFields) {
    const value = toStringOrNull(candidate[field]);
    if (value) {
      return value;
    }
  }

  const messages = candidate.messages;
  if (Array.isArray(messages)) {
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const item = messages[index];
      if (!isPlainObject(item)) {
        continue;
      }
      const content = toStringOrNull(item.content);
      if (content) {
        const role = typeof item.role === "string" ? item.role : "user";
        if (role === "user" || role === "assistant" || role === "system") {
          return content;
        }
      }
    }
  }

  return null;
}

function normalizeHistory(candidate: unknown): Array<{ role: ChatRole; content: string }> {
  if (!isPlainObject(candidate) || !Array.isArray(candidate.messages)) {
    return [];
  }

  const history: Array<{ role: ChatRole; content: string }> = [];
  for (const item of candidate.messages) {
    if (!isPlainObject(item)) {
      continue;
    }
    const content = toStringOrNull(item.content);
    if (!content) {
      continue;
    }
    const role = item.role === "system" || item.role === "assistant" ? item.role : "user";
    history.push({ role, content });
  }
  return history;
}

function createStableId(seed: string): string {
  let hash = 2166136261;
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return `chat_${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

function mapErrorCode(error: unknown): ChatErrorCode {
  if (isPlainObject(error)) {
    const directCode = typeof error.code === "string" ? error.code : null;
    const nestedCode = isPlainObject(error.error) && typeof error.error.code === "string" ? error.error.code : null;
    const code = directCode ?? nestedCode;
    if (code === "BAD_REQUEST" || code === "ORCHESTRATION_FAILED" || code === "INTERNAL_SERVER_ERROR") {
      return code;
    }
  }
  return "INTERNAL_SERVER_ERROR";
}

function getErrorMessage(error: unknown): string {
  if (isPlainObject(error)) {
    if (isNonEmptyString(error.message)) {
      return error.message.trim();
    }
    if (isPlainObject(error.error) && isNonEmptyString(error.error.message)) {
      return error.error.message.trim();
    }
  }
  if (error instanceof Error && isNonEmptyString(error.message)) {
    return error.message.trim();
  }
  return "Chat route failed";
}

function buildErrorResponse(
  code: ChatErrorCode,
  message: string,
  requestId?: string
): ChatResponseDto {
  return {
    ok: false,
    status: "error",
    error: {
      code,
      message,
      requestId,
    },
  };
}

function buildSuccessResponse(
  normalized: NormalizedChatTurn,
  assistantText: string,
  requestId: string,
  source: "orchestrator" | "fallback"
): ChatResponseDto {
  return {
    ok: true,
    status: "success",
    data: {
      requestId,
      sessionId: normalized.request.sessionId,
      conversationId: normalized.request.conversationId,
      reply: assistantText,
      message: {
        role: "assistant",
        content: assistantText,
      },
      source,
    },
  };
}

function resolveAssistantText(result: unknown, fallbackText: string): { text: string; source: "orchestrator" | "fallback" } {
  if (isNonEmptyString(result)) {
    return { text: result.trim(), source: "orchestrator" };
  }

  if (isPlainObject(result)) {
    const explicitFallback = result.source === "fallback";
    const directFields = ["reply", "response", "message", "content", "text"] as const;
    for (const field of directFields) {
      const value = toStringOrNull(result[field]);
      if (value) {
        return { text: value, source: explicitFallback ? "fallback" : "orchestrator" };
      }
    }

    if (isPlainObject(result.data)) {
      for (const field of directFields) {
        const value = toStringOrNull((result.data as PlainObject)[field]);
        if (value) {
          return { text: value, source: explicitFallback ? "fallback" : "orchestrator" };
        }
      }
      if (isPlainObject((result.data as PlainObject).message)) {
        const message = (result.data as PlainObject).message as PlainObject;
        const nested = toStringOrNull(message.content);
        if (nested) {
          return { text: nested, source: explicitFallback ? "fallback" : "orchestrator" };
        }
      }
    }
  }

  return { text: fallbackText, source: "fallback" };
}

function normalizeChatTurn(request: ChatRequestDto, memoryContext: Record<string, unknown>): NormalizedChatTurn {
  const userText = extractMessageContent(request);
  if (!userText) {
    throw {
      code: "BAD_REQUEST",
      message: "Chat request must include a non-empty message",
    } as ChatRouteErrorLike;
  }

  return {
    request,
    userText,
    history: normalizeHistory(request),
    memoryContext,
  };
}

function normalizeIdentifier(value: unknown): string | null {
  return isNonEmptyString(value) ? value.trim() : null;
}

function resolveRuntimeMemoryContext(
  request: ChatRequestDto,
  baseMemoryContext: Record<string, unknown>,
  persistence: SessionMemoryPersistence,
): Record<string, unknown> {
  const sessionId = normalizeIdentifier(request.sessionId);
  const conversationId = normalizeIdentifier(request.conversationId);

  if (!sessionId || !conversationId) {
    return Object.freeze({ ...baseMemoryContext });
  }

  const sessionEntries = persistence.load({
    sessionId,
    conversationId,
  });

  return Object.freeze({
    ...baseMemoryContext,
    entries: sessionEntries.map((entry) =>
      Object.freeze({
        id: entry.id,
        type: entry.role,
        content: entry.content,
        sessionId: entry.sessionId,
        conversationId: entry.conversationId,
        createdAt: entry.createdAt,
        expiresAt: entry.expiresAt,
        metadata: entry.metadata,
      }),
    ),
  });
}

function readRequestId(request: ChatRequestDto, userText: string, history: NormalizedChatTurn["history"]): string {
  if (isNonEmptyString(request.requestId)) {
    return request.requestId.trim();
  }
  return createStableId(`${request.sessionId ?? ""}|${request.conversationId ?? ""}|${userText}|${history.length}`);
}

function finalizeResponse(
  response: ChatHttpResponseLike | undefined,
  statusCode: number,
  body: ChatResponseDto
): ChatResponseDto {
  if (!response) {
    return body;
  }

  if (typeof response.setHeader === "function") {
    response.setHeader("content-type", "application/json; charset=utf-8");
  }

  if (typeof response.status === "function") {
    const next = response.status(statusCode);
    if (next && typeof next.json === "function") {
      next.json(body);
      return body;
    }
    if (next && typeof next.send === "function") {
      next.send(body);
      return body;
    }
    if (next && typeof next.end === "function") {
      next.end(JSON.stringify(body));
      return body;
    }
  }

  if (typeof response.json === "function") {
    response.json(body);
    return body;
  }

  if (typeof response.send === "function") {
    response.send(body);
    return body;
  }

  if (typeof response.end === "function") {
    response.end(JSON.stringify(body));
  }

  return body;
}

async function executeChatRoute(
  request: unknown,
  dependencies: ChatRouteDependencies
): Promise<ChatResponseDto> {
  const rawPayload = readPayload(request);
  const middlewareResult = dependencies.validateChatRequestMiddleware
    ? dependencies.validateChatRequestMiddleware(request)
    : rawPayload;
  const validatedRequest = readValidatedRequest(middlewareResult, rawPayload);

  const persistence = dependencies.sessionMemoryPersistence ?? createInMemorySessionMemoryPersistence();
  const memoryContext = resolveRuntimeMemoryContext(
    validatedRequest,
    dependencies.memoryContext ?? {},
    persistence,
  );
  const normalized = normalizeChatTurn(validatedRequest, memoryContext);
  const requestId = readRequestId(validatedRequest, normalized.userText, normalized.history);

  try {
    const runOrchestrator = dependencies.orchestrateTurn ?? defaultRuntimeOrchestrateTurn;
    const orchestratorResult = await runOrchestrator(normalized);

    const assistant = resolveAssistantText(orchestratorResult, normalized.userText);
    const sessionId = normalizeIdentifier(validatedRequest.sessionId);
    const conversationId = normalizeIdentifier(validatedRequest.conversationId);
    if (sessionId && conversationId) {
      persistence.append([
        {
          sessionId,
          conversationId,
          role: "user",
          content: normalized.userText,
          ttlSeconds: dependencies.memoryTtlSeconds,
        },
        {
          sessionId,
          conversationId,
          role: "assistant",
          content: assistant.text,
          ttlSeconds: dependencies.memoryTtlSeconds,
        },
      ]);
      persistence.decay({
        keepLatestPerConversation: dependencies.memoryDecayKeepLatest,
      });
    }

    return buildSuccessResponse(normalized, assistant.text, requestId, assistant.source);
  } catch (error) {
    const code = mapErrorCode(error);
    const message = getErrorMessage(error);
    if (code === "BAD_REQUEST") {
      return buildErrorResponse(code, message, requestId);
    }
    return buildErrorResponse(code, "Failed to process chat request", requestId);
  }
}

export function createChatRoute(
  dependencies: ChatRouteDependencies = {}
): ChatRouteHandler {
  const sessionMemoryPersistence =
    dependencies.sessionMemoryPersistence ?? createInMemorySessionMemoryPersistence();

  const handler = (async (request: unknown, response?: ChatHttpResponseLike) => {
    try {
      const body = await executeChatRoute(request, {
        ...dependencies,
        sessionMemoryPersistence,
      });
      const statusCode = body.ok ? 200 : ERROR_STATUS_BY_CODE[body.error.code];
      return finalizeResponse(response, statusCode, body);
    } catch (error) {
      const fallback = buildErrorResponse(
        mapErrorCode(error),
        "Failed to process chat request"
      );
      return finalizeResponse(response, ERROR_STATUS_BY_CODE[fallback.error.code], fallback);
    }
  }) as ChatRouteHandler;

  handler.method = "POST";
  handler.path = "/chat";
  handler.routeName = "chat";
  handler.handle = handler;

  return handler;
}
