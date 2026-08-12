export type ApiErrorEnvelope = {
  success: false;
  error: {
    code: string;
    message: string;
    requestId?: string;
  };
};

type RequestLike = {
  id?: string;
  requestId?: string;
  headers?: Record<string, string | string[] | undefined>;
};

type ResponseLike = {
  headersSent?: boolean;
  status(code: number): ResponseLike;
  json(body: ApiErrorEnvelope): unknown;
};

type NextFunctionLike = (err?: unknown) => void;

type BackendErrorLike = {
  code?: unknown;
  message?: unknown;
  status?: unknown;
  statusCode?: unknown;
  expose?: unknown;
};

const DEFAULT_ERROR_CODE = 'INTERNAL_SERVER_ERROR';
const DEFAULT_ERROR_MESSAGE = 'An unexpected error occurred.';

function toSafeString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : undefined;
}

function toSafeStatus(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isInteger(value) && value >= 400 && value <= 599
    ? value
    : undefined;
}

function getRequestId(request: RequestLike): string | undefined {
  return (
    toSafeString(request.requestId) ||
    toSafeString(request.id) ||
    toSafeString(request.headers?.['x-request-id']) ||
    toSafeString(request.headers?.['X-Request-Id'])
  );
}

function mapError(error: unknown): { status: number; envelope: ApiErrorEnvelope } {
  const fallback = {
    status: 500,
    envelope: {
      success: false as const,
      error: {
        code: DEFAULT_ERROR_CODE,
        message: DEFAULT_ERROR_MESSAGE,
      },
    },
  };

  if (!error || typeof error !== 'object') {
    return fallback;
  }

  const backendError = error as BackendErrorLike;
  const status = toSafeStatus(backendError.statusCode) ?? toSafeStatus(backendError.status) ?? 500;
  const code = toSafeString(backendError.code) ?? (status < 500 ? 'BAD_REQUEST' : DEFAULT_ERROR_CODE);
  const message =
    status < 500 && backendError.expose === true
      ? toSafeString(backendError.message) ?? 'Request failed.'
      : status < 500
        ? toSafeString(backendError.message) ?? 'Request failed.'
        : DEFAULT_ERROR_MESSAGE;

  return {
    status,
    envelope: {
      success: false,
      error: {
        code,
        message,
      },
    },
  };
}

export function apiErrorHandler(error: unknown, request: RequestLike, response: ResponseLike, next: NextFunctionLike): void {
  if (response.headersSent) {
    next(error);
    return;
  }

  const { status, envelope } = mapError(error);
  const requestId = getRequestId(request);

  response.status(status).json({
    ...envelope,
    error: {
      ...envelope.error,
      ...(requestId ? { requestId } : {}),
    },
  });
}