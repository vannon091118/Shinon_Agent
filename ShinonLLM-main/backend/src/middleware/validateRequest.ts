export type BackendErrorCode =
  | "BAD_REQUEST"
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "METHOD_NOT_ALLOWED"
  | "PAYLOAD_TOO_LARGE"
  | "UNSUPPORTED_MEDIA_TYPE"
  | "UNPROCESSABLE_ENTITY"
  | "INTERNAL_SERVER_ERROR";

export interface StableJsonEnvelope<T> {
  ok: boolean;
  data?: T;
  error?: {
    code: BackendErrorCode;
    message: string;
  };
}

export interface ValidatedHttpRequest {
  method?: string;
  url?: string;
  headers?: Record<string, string | string[] | undefined>;
  body?: unknown;
  rawBody?: string | ArrayBuffer | Uint8Array;
}

export interface MiddlewareResponse<T> {
  status: number;
  headers: Record<string, string>;
  body: StableJsonEnvelope<T>;
}

const MAX_BODY_BYTES = 64 * 1024;
const MAX_TOP_LEVEL_KEYS = 50;
const MAX_STRING_LENGTH = 4096;

function makeErrorResponse(
  status: number,
  code: BackendErrorCode,
  message: string,
): MiddlewareResponse<never> {
  return {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
    body: {
      ok: false,
      error: {
        code,
        message,
      },
    },
  };
}

function estimateBodySize(input: ValidatedHttpRequest): number {
  const rawBody = input.rawBody;
  if (typeof rawBody === "string") {
    return Buffer.byteLength(rawBody, "utf8");
  }
  if (rawBody instanceof Uint8Array) {
    return rawBody.byteLength;
  }
  if (rawBody instanceof ArrayBuffer) {
    return rawBody.byteLength;
  }
  if (input.body === undefined) {
    return 0;
  }

  try {
    return Buffer.byteLength(JSON.stringify(input.body) ?? "", "utf8");
  } catch {
    return Number.POSITIVE_INFINITY;
  }
}

function hasUnsafeKey(value: Record<string, unknown>): boolean {
  for (const key of Object.keys(value)) {
    if (key === "__proto__" || key === "prototype" || key === "constructor") {
      return true;
    }
  }
  return false;
}

function validatePayloadShape(body: unknown): body is Record<string, unknown> {
  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    return false;
  }

  const record = body as Record<string, unknown>;
  if (Object.keys(record).length > MAX_TOP_LEVEL_KEYS) {
    return false;
  }
  if (hasUnsafeKey(record)) {
    return false;
  }

  for (const value of Object.values(record)) {
    if (typeof value === "string" && value.length > MAX_STRING_LENGTH) {
      return false;
    }
    if (Array.isArray(value) && value.length > MAX_TOP_LEVEL_KEYS) {
      return false;
    }
  }

  return true;
}

function sanitizeMessage(message: string): string {
  return message.replace(/[\r\n\t]+/g, " ").trim();
}

export function validateChatRequestMiddleware(
  request: ValidatedHttpRequest,
): MiddlewareResponse<{
  accepted: true;
  method: string;
  url: string;
  payload: Record<string, unknown>;
}> {
  if (!request || typeof request !== "object") {
    return makeErrorResponse(400, "BAD_REQUEST", "Invalid request envelope.");
  }

  const method = typeof request.method === "string" ? request.method.toUpperCase() : "";
  const url = typeof request.url === "string" ? request.url : "";
  const contentType = request.headers?.["content-type"];
  const normalizedContentType = Array.isArray(contentType)
    ? contentType.join(",")
    : typeof contentType === "string"
      ? contentType
      : "";

  const bodySize = estimateBodySize(request);
  if (bodySize > MAX_BODY_BYTES) {
    return makeErrorResponse(413, "PAYLOAD_TOO_LARGE", "Request body exceeds limit.");
  }

  if (method && !["POST", "PUT", "PATCH"].includes(method)) {
    return makeErrorResponse(405, "METHOD_NOT_ALLOWED", "Method not allowed.");
  }

  if (normalizedContentType && !normalizedContentType.toLowerCase().includes("application/json")) {
    return makeErrorResponse(415, "UNSUPPORTED_MEDIA_TYPE", "JSON content type required.");
  }

  if (!validatePayloadShape(request.body)) {
    return makeErrorResponse(422, "UNPROCESSABLE_ENTITY", "Payload rejected by schema guard.");
  }

  return {
    status: 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
    body: {
      ok: true,
      data: {
        accepted: true,
        method: method || "POST",
        url: sanitizeMessage(url || "/"),
        payload: request.body as Record<string, unknown>,
      },
    },
  };
}
