import { createChatRoute } from "./routes/chat.js";
import { createHealthRoute, type HealthRouteOptions, type HealthRouteResult, type ValidatedHealthRequest, type HealthResponseDto } from "./routes/health.js";
import { scanModels } from "./routes/models.js";

export type ServerRequest = Readonly<{
  method?: string;
  url?: string;
  headers?: Readonly<Record<string, string | undefined>>;
  body?: unknown;
  requestId?: string;
}>;

export type ServerResponseEnvelope<T = unknown> =
  | {
      ok: true;
      status: "success";
      data: {
        route: "chat" | "health";
        response: T;
        requestId?: string;
      };
    }
  | {
      ok: false;
      status: "error";
      error: {
        code: string;
        message: string;
        requestId?: string;
      };
      data?: {
        route: "chat" | "health";
        response?: T;
      };
    };

export type ServerResponse<T = unknown> = Readonly<{
  status: number;
  headers: Readonly<Record<string, string>>;
  body: T;
}>;

export type ServerMainOptions = Readonly<{
  now?: () => Date;
  backendHealth?: HealthRouteOptions["backendHealth"];
  chatRouteFactory?: typeof createChatRoute;
  healthRouteFactory?: typeof createHealthRoute;
}>;

const JSON_HEADERS = Object.freeze({
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
});

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function toSafeMethod(value: unknown): string {
  return typeof value === "string" ? value.trim().toUpperCase() : "";
}

function normalizePath(url: string | undefined): string {
  if (!isNonEmptyString(url)) {
    return "";
  }

  try {
    const parsed = new URL(url, "http://localhost");
    const pathname = parsed.pathname.replace(/\/+$/u, "");
    if (pathname.startsWith("/api/")) {
      return pathname.slice(4) || "/";
    }
    return pathname || "/";
  } catch {
    const trimmed = url.trim();
    if (trimmed.startsWith("/api/")) {
      return trimmed.slice(4).replace(/\/+$/u, "") || "/";
    }
    return trimmed.replace(/\/+$/u, "") || "/";
  }
}

function readRequestId(request: ServerRequest): string | undefined {
  if (isNonEmptyString(request.requestId)) {
    return request.requestId.trim();
  }

  const headerCandidates = [
    request.headers?.["x-request-id"],
    request.headers?.["X-Request-Id"],
  ];

  for (const candidate of headerCandidates) {
    if (isNonEmptyString(candidate)) {
      return candidate.trim();
    }
  }

  return undefined;
}

function failClosed(
  status: number,
  code: string,
  message: string,
  requestId?: string,
  route?: "chat" | "health",
  response?: unknown,
): ServerResponse<ServerResponseEnvelope> {
  return {
    status,
    headers: JSON_HEADERS,
    body: {
      ok: false,
      status: "error",
      error: {
        code,
        message,
        ...(requestId ? { requestId } : {}),
      },
      ...(route ? { data: { route, ...(response !== undefined ? { response } : {}) } } : {}),
    },
  };
}

function toSuccess(route: "chat" | "health", response: unknown, requestId?: string, status = 200): ServerResponse<ServerResponseEnvelope> {
  return {
    status,
    headers: JSON_HEADERS,
    body: {
      ok: true,
      status: "success",
      data: {
        route,
        response,
        ...(requestId ? { requestId } : {}),
      },
    },
  };
}

function isHealthResult(value: unknown): value is HealthRouteResult {
  if (!isPlainObject(value)) {
    return false;
  }
  return typeof value.status === "number" && isPlainObject(value.body) && isPlainObject(value.headers);
}

function mapHealthResult(result: HealthRouteResult, requestId?: string): ServerResponse<HealthResponseDto> {
  if (result.status >= 200 && result.status < 300) {
    return {
      status: result.status,
      headers: result.headers ?? JSON_HEADERS,
      body: result.body,
    };
  }

  return {
    status: result.status,
    headers: result.headers ?? JSON_HEADERS,
    body: {
      ...result.body,
      ok: false,
    },
  };
}

function mapChatResult(result: unknown, requestId?: string): ServerResponse<unknown> {
  if (isPlainObject(result) && result.ok === true && result.status === "success" && isPlainObject(result.data)) {
    return {
      status: 200,
      headers: JSON_HEADERS,
      body: result,
    };
  }

  if (isPlainObject(result) && result.ok === false && result.status === "error" && isPlainObject(result.error)) {
    const errorCode = typeof result.error.code === "string" ? result.error.code : "INTERNAL_SERVER_ERROR";
    const errorMessage = isNonEmptyString(result.error.message) ? result.error.message.trim() : "Chat route failed";
    return {
      status: errorCode === "BAD_REQUEST" ? 400 : errorCode === "ORCHESTRATION_FAILED" ? 502 : 500,
      headers: JSON_HEADERS,
      body: {
        ok: false,
        status: "error",
        error: {
          code: errorCode,
          message: errorMessage,
          ...(requestId ? { requestId } : {}),
        },
      },
    };
  }

  return {
    status: 500,
    headers: JSON_HEADERS,
    body: {
      ok: false,
      status: "error",
      error: {
        code: "INTERNAL_SERVER_ERROR",
        message: "Chat route failed",
        ...(requestId ? { requestId } : {}),
      },
    },
  };
}

function normalizeValidatedHealthRequest(request: ServerRequest): ValidatedHealthRequest | null {
  const method = toSafeMethod(request.method);
  if (method !== "GET" && method !== "HEAD") {
    return null;
  }

  return {
    method,
    headers: request.headers,
    requestId: readRequestId(request),
  };
}

function normalizeChatRequest(request: ServerRequest): ServerRequest | null {
  const method = toSafeMethod(request.method);
  if (method !== "POST") {
    return null;
  }

  return {
    ...request,
    body: request.body,
    requestId: readRequestId(request),
  };
}

export async function serverMain(
  request: ServerRequest,
  options: ServerMainOptions = {},
): Promise<ServerResponse> {
  if (!isPlainObject(request)) {
    return failClosed(400, "INVALID_REQUEST", "validated HTTP request is required");
  }

  const requestId = readRequestId(request);
  const method = toSafeMethod(request.method);
  const path = normalizePath(request.url);

  if (!method || !path) {
    return failClosed(400, "INVALID_REQUEST", "validated HTTP request is required", requestId);
  }

  const healthRoute = (options.healthRouteFactory ?? createHealthRoute)({
    now: options.now,
    backendHealth: options.backendHealth,
  });
  const chatRoute = (options.chatRouteFactory ?? createChatRoute)();

  if (path === "/health") {
    const validatedHealthRequest = normalizeValidatedHealthRequest(request);
    if (!validatedHealthRequest) {
      return failClosed(405, "METHOD_NOT_ALLOWED", "health route only accepts GET or HEAD", requestId, "health");
    }

    try {
      const result = await healthRoute(validatedHealthRequest);
      if (isHealthResult(result)) {
        return mapHealthResult(result, requestId);
      }
      return failClosed(500, "INTERNAL_SERVER_ERROR", "Health route failed", requestId, "health", result as HealthRouteResult);
    } catch {
      return failClosed(503, "BACKEND_HEALTH_ERROR", "backend health check failed", requestId, "health");
    }
  }

  if (path === "/chat") {
    const chatRequest = normalizeChatRequest(request);
    if (!chatRequest) {
      return failClosed(405, "METHOD_NOT_ALLOWED", "chat route only accepts POST", requestId, "chat");
    }

    try {
      const result = await chatRoute(chatRequest);
      return mapChatResult(result, requestId);
    } catch {
      return failClosed(500, "INTERNAL_SERVER_ERROR", "Chat route failed", requestId, "chat");
    }
  }

  if (path === "/api/models" || path === "/models") {
    if (method !== "GET") {
      return failClosed(405, "METHOD_NOT_ALLOWED", "models route only accepts GET", requestId);
    }
    
    try {
      const result = await scanModels();
      if (result.ok) {
        return {
          status: 200,
          headers: JSON_HEADERS,
          body: result,
        };
      }
      return failClosed(500, "MODEL_SCAN_ERROR", result.error, requestId);
    } catch {
      return failClosed(500, "INTERNAL_SERVER_ERROR", "Model scan failed", requestId);
    }
  }

  return failClosed(404, "NOT_FOUND", "route not found", requestId);
}
