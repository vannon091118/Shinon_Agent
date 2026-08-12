/**
 * backendRetry.ts
 *
 * Polls the backend health endpoint before each live call attempt.
 * Retries up to maxAttempts times with exponential backoff.
 * If the backend never becomes reachable, throws so the router can
 * decide about fallback — it does NOT silently echo user input.
 */

type PlainObject = Record<string, unknown>;

export type RetryBackendName = "llamacpp" | "ollama";

export type BackendRetryOptions = Readonly<{
  /** How many total attempts (including first). Default: 3 */
  maxAttempts?: number;
  /** Initial wait between retries in ms. Doubled on each retry. Default: 800 */
  initialDelayMs?: number;
  /** Hard cap on single delay in ms. Default: 5000 */
  maxDelayMs?: number;
  /** Health endpoint to probe, e.g. "http://127.0.0.1:8000/health" */
  healthUrl: string;
  /** Optional: override the fetch implementation (for tests) */
  fetchImpl?: (url: string) => Promise<{ ok?: boolean; status?: number }>;
}>;

export type BackendRetryError = Readonly<{
  code: "BACKEND_UNREACHABLE_AFTER_RETRY";
  message: string;
  attempts: number;
  healthUrl: string;
}>;

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function toPositiveInteger(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value) && value > 0) {
    return Math.floor(value);
  }
  return fallback;
}

function resolveFetch(
  override: BackendRetryOptions["fetchImpl"],
): (url: string) => Promise<{ ok?: boolean; status?: number }> {
  if (typeof override === "function") {
    return override;
  }
  const globalFetch = (globalThis as { fetch?: unknown }).fetch;
  if (typeof globalFetch === "function") {
    return globalFetch as (url: string) => Promise<{ ok?: boolean; status?: number }>;
  }
  // No fetch available — always fail so the router knows
  return async () => ({ ok: false, status: 0 });
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Probe a health URL once. Returns true if the backend responded OK.
 */
async function probeHealth(
  healthUrl: string,
  fetchImpl: (url: string) => Promise<{ ok?: boolean; status?: number }>,
): Promise<boolean> {
  try {
    const response = await fetchImpl(healthUrl);
    if (!isPlainObject(response)) {
      return false;
    }
    const status = typeof (response as { status?: unknown }).status === "number"
      ? (response as { status: number }).status
      : 0;
    const ok = (response as { ok?: unknown }).ok;

    if (ok === true) {
      return true;
    }
    // llama.cpp returns { "status": "ok" } — status 200 is sufficient
    if (status >= 200 && status < 300) {
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/**
 * Waits until the backend health endpoint responds or maxAttempts is exhausted.
 *
 * Throws a typed `BackendRetryError` if the backend never becomes reachable,
 * so callers can propagate a real error instead of echoing user input.
 *
 * @example
 * await waitForBackend({ healthUrl: "http://127.0.0.1:8000/health", maxAttempts: 3 });
 */
export async function waitForBackend(options: BackendRetryOptions): Promise<void> {
  const maxAttempts = toPositiveInteger(options.maxAttempts, 3);
  const initialDelayMs = toPositiveInteger(options.initialDelayMs, 800);
  const maxDelayMs = toPositiveInteger(options.maxDelayMs, 5000);
  const { healthUrl } = options;
  const fetchImpl = resolveFetch(options.fetchImpl);

  let delayMs = initialDelayMs;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const healthy = await probeHealth(healthUrl, fetchImpl);
    if (healthy) {
      return; // Backend is up — caller can proceed with the real call
    }

    if (attempt < maxAttempts) {
      console.warn(
        `[backendRetry] Backend not reachable at ${healthUrl} — attempt ${attempt}/${maxAttempts}, retrying in ${delayMs}ms`,
      );
      await sleep(delayMs);
      delayMs = clamp(delayMs * 2, initialDelayMs, maxDelayMs);
    }
  }

  const err: BackendRetryError = Object.freeze({
    code: "BACKEND_UNREACHABLE_AFTER_RETRY",
    message: `Backend did not become reachable after ${maxAttempts} attempts (health: ${healthUrl})`,
    attempts: maxAttempts,
    healthUrl,
  });
  throw err;
}

/**
 * Resolve the health URL for a given backend from env or defaults.
 */
export function resolveHealthUrl(backend: RetryBackendName): string {
  const env = (globalThis as typeof globalThis & {
    process?: { env?: Record<string, string | undefined> };
  }).process?.env;

  if (backend === "llamacpp") {
    const base = env?.LLAMA_CPP_BASE_URL?.trim() || "http://127.0.0.1:8000";
    return `${base.replace(/\/+$/u, "")}/health`;
  }

  const base = env?.OLLAMA_BASE_URL?.trim() || "http://127.0.0.1:11434";
  return `${base.replace(/\/+$/u, "")}/api/tags`; // Ollama has no /health, /api/tags responds when ready
}
