export type HealthCheckOutcome = {
  ok: boolean;
  code: string;
  message?: string;
  details?: Record<string, unknown>;
};

export type HealthResponseDto = {
  ok: boolean;
  status: "healthy" | "unhealthy";
  code: string;
  timestamp: string;
  backend: {
    ok: boolean;
    code: string;
    message?: string;
    details?: Record<string, unknown>;
  };
};

export type ValidatedHealthRequest = {
  method: "GET" | "HEAD";
  headers?: Readonly<Record<string, string | undefined>>;
  requestId?: string;
};

export type HealthRouteResult = {
  status: number;
  body: HealthResponseDto;
  headers: Readonly<Record<string, string>>;
};

export type HealthRouteOptions = {
  backendHealth?: (request: ValidatedHealthRequest) => Promise<HealthCheckOutcome> | HealthCheckOutcome;
  now?: () => Date;
};

const JSON_HEADERS = Object.freeze({
  "content-type": "application/json; charset=utf-8",
});

function toIsoString(now: () => Date): string {
  return now().toISOString();
}

function normalizeBackendOutcome(outcome: HealthCheckOutcome | null | undefined): HealthCheckOutcome {
  if (!outcome || typeof outcome !== "object") {
    return {
      ok: false,
      code: "BACKEND_HEALTH_UNAVAILABLE",
      message: "backend health check did not return a valid outcome",
    };
  }

  return {
    ok: outcome.ok === true,
    code: typeof outcome.code === "string" && outcome.code.length > 0 ? outcome.code : "BACKEND_HEALTH_ERROR",
    message: typeof outcome.message === "string" && outcome.message.length > 0 ? outcome.message : undefined,
    details:
      outcome.details && typeof outcome.details === "object" && !Array.isArray(outcome.details)
        ? outcome.details
        : undefined,
  };
}

function createBody(now: () => Date, backend: HealthCheckOutcome): HealthResponseDto {
  const healthy = backend.ok === true;

  return {
    ok: healthy,
    status: healthy ? "healthy" : "unhealthy",
    code: healthy ? "HEALTH_OK" : backend.code,
    timestamp: toIsoString(now),
    backend: {
      ok: backend.ok,
      code: backend.code,
      message: backend.message,
      details: backend.details,
    },
  };
}

function failClosed(now: () => Date, code: string, message: string): HealthRouteResult {
  return {
    status: code === "METHOD_NOT_ALLOWED" ? 405 : 503,
    body: {
      ok: false,
      status: "unhealthy",
      code,
      timestamp: toIsoString(now),
      backend: {
        ok: false,
        code,
        message,
      },
    },
    headers: JSON_HEADERS,
  };
}

export function createHealthRoute(options: HealthRouteOptions = {}) {
  const now = options.now ?? (() => new Date());

  return async function healthRoute(request: ValidatedHealthRequest): Promise<HealthRouteResult> {
    if (!request || typeof request !== "object") {
      return failClosed(now, "INVALID_REQUEST", "validated request is required");
    }

    if (request.method !== "GET" && request.method !== "HEAD") {
      return failClosed(now, "METHOD_NOT_ALLOWED", "health route only accepts GET or HEAD");
    }

    try {
      const outcome = normalizeBackendOutcome(
        options.backendHealth ? await options.backendHealth(request) : {
          ok: false,
          code: "BACKEND_HEALTH_UNAVAILABLE",
          message: "no backend health checker configured",
        },
      );

      return {
        status: outcome.ok ? 200 : 503,
        body: createBody(now, outcome),
        headers: JSON_HEADERS,
      };
    } catch {
      return failClosed(now, "BACKEND_HEALTH_ERROR", "backend health check failed");
    }
  };
}
