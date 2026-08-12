import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { mkdir } from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";

import { createChatRoute } from "./routes/chat.js";
import { createHealthRoute } from "./routes/health.js";
import { scanModels } from "./routes/models.js";
import {
  createInMemorySessionMemoryPersistence,
  createSqliteSessionMemoryPersistence,
  type SessionMemoryPersistence,
  type SessionMemorySqliteAdapter,
} from "../../memory/src/session/sessionPersistence.js";
import { getDatabase } from "../../memory/src/adapters/sqliteAdapter.js";

const DEFAULT_HOST = "127.0.0.1";
const DEFAULT_PORT = 3001;

type ParsedRequest = Readonly<{
  method: string;
  url: string;
  headers: Readonly<Record<string, string | undefined>>;
  body?: unknown;
}>;

function toMethod(value: string | undefined): string {
  return (value ?? "GET").trim().toUpperCase();
}

function toPath(value: string | undefined): string {
  const raw = value?.trim() ?? "/";
  try {
    const parsed = new URL(raw, "http://localhost");
    return parsed.pathname.replace(/\/+$/u, "") || "/";
  } catch {
    return raw.replace(/\/+$/u, "") || "/";
  }
}

function toHeaders(headers: IncomingMessage["headers"]): Readonly<Record<string, string | undefined>> {
  const normalized: Record<string, string | undefined> = {};
  for (const [key, value] of Object.entries(headers)) {
    if (Array.isArray(value)) {
      normalized[key.toLowerCase()] = value.join(", ");
      continue;
    }
    normalized[key.toLowerCase()] = value;
  }
  return normalized;
}

async function readBody(request: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk)));
  }

  const raw = Buffer.concat(chunks).toString("utf8").trim();
  if (raw.length === 0) {
    return undefined;
  }

  try {
    return JSON.parse(raw);
  } catch {
    throw new Error("Invalid JSON body");
  }
}

async function toParsedRequest(request: IncomingMessage): Promise<ParsedRequest> {
  const method = toMethod(request.method);
  const url = request.url ?? "/";
  const headers = toHeaders(request.headers);
  const needsBody = method === "POST" || method === "PUT" || method === "PATCH";
  const body = needsBody ? await readBody(request) : undefined;

  return Object.freeze({
    method,
    url,
    headers,
    body,
  });
}

function writeJson(response: ServerResponse, status: number, body: unknown): void {
  response.statusCode = status;
  response.setHeader("content-type", "application/json; charset=utf-8");
  response.setHeader("cache-control", "no-store");
  response.end(JSON.stringify(body));
}

/**
 * Converts a trimmed base-10 integer string into a positive integer.
 *
 * @param value - The input value expected to be a non-empty string containing a base-10 integer
 * @returns The parsed integer if it is an integer greater than 0, `undefined` otherwise
 */
function toPositiveInteger(value: unknown): number | undefined {
  if (typeof value !== "string" || value.trim().length === 0) {
    return undefined;
  }
  const parsed = Number.parseInt(value, 10);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    return undefined;
  }
  return parsed;
}

/**
 * Indicates whether SQLite-backed session memory persistence is enabled.
 *
 * This implementation forces SQLite to be enabled (used for production and smoke tests).
 *
 * @returns `true` when SQLite persistence is enabled; this implementation always returns `true`.
 */
function isSqliteExplicitlyEnabled(): boolean {
  return true; // Erzwungen für Produktion / Smoke-Tests
}

/**
 * Compute a platform-appropriate filesystem path for the default SQLite session-memory database.
 *
 * On Windows this uses `LOCALAPPDATA` when set, otherwise `~\\AppData\\Local`. On macOS it uses
 * `~/Library/Application Support`. On other systems it uses `XDG_DATA_HOME` when set, otherwise
 * `~/.local/share`. The final filename is `session-memory.sqlite` inside a `ShinonLLM` subdirectory.
 *
 * @returns An absolute filesystem path to `session-memory.sqlite` in the OS-appropriate application data directory.
 */
function toDefaultSqlitePath(): string {
  const homeDirectory = homedir();

  if (process.platform === "win32") {
    const localAppData = process.env.LOCALAPPDATA?.trim();
    if (localAppData) {
      return join(localAppData, "ShinonLLM", "session-memory.sqlite");
    }
    return join(homeDirectory, "AppData", "Local", "ShinonLLM", "session-memory.sqlite");
  }

  if (process.platform === "darwin") {
    return join(homeDirectory, "Library", "Application Support", "ShinonLLM", "session-memory.sqlite");
  }

  const xdgDataHome = process.env.XDG_DATA_HOME?.trim();
  if (xdgDataHome) {
    return join(xdgDataHome, "ShinonLLM", "session-memory.sqlite");
  }
  return join(homeDirectory, ".local", "share", "ShinonLLM", "session-memory.sqlite");
}

function toErrorMessage(value: unknown): string {
  if (value instanceof Error) {
    return value.message;
  }
  if (typeof value === "object" && value !== null && "message" in value) {
    const candidate = (value as { message?: unknown }).message;
    if (typeof candidate === "string" && candidate.trim().length > 0) {
      return candidate;
    }
  }
  return String(value);
}

async function createSessionMemoryPersistence(): Promise<SessionMemoryPersistence> {
  const sqlitePathOverride = process.env.SHINON_MEMORY_SQLITE_PATH?.trim();
  const sqliteEnabled = isSqliteExplicitlyEnabled() || Boolean(sqlitePathOverride);
  if (!sqliteEnabled) {
    return createInMemorySessionMemoryPersistence();
  }
  const sqlitePath = sqlitePathOverride || toDefaultSqlitePath();

  try {
    await mkdir(dirname(sqlitePath), { recursive: true });

    const sqliteModule = await import("node:sqlite");
    const DatabaseSyncCtor = (sqliteModule as { DatabaseSync?: unknown }).DatabaseSync;
    if (typeof DatabaseSyncCtor !== "function") {
      if (isSqliteExplicitlyEnabled()) {
        throw new Error("node:sqlite is unavailable in this Node.js runtime");
      }
      return createInMemorySessionMemoryPersistence();
    }

    const database = new (DatabaseSyncCtor as new (filename: string) => {
      prepare: (sql: string) => {
        run: (...params: unknown[]) => { changes?: number };
        all: (...params: unknown[]) => unknown[];
      };
    })(sqlitePath);

    const adapter: SessionMemorySqliteAdapter = Object.freeze({
      run(sql: string, params: ReadonlyArray<unknown> = []) {
        const statement = database.prepare(sql);
        return statement.run(...params);
      },
      all(sql: string, params: ReadonlyArray<unknown> = []) {
        const statement = database.prepare(sql);
        const rows = statement.all(...params);
        return Array.isArray(rows) ? (rows as ReadonlyArray<Record<string, unknown>>) : [];
      },
    });

    return createSqliteSessionMemoryPersistence(adapter);
  } catch (error) {
    if (isSqliteExplicitlyEnabled()) {
      throw new Error(
        `SQLite session memory initialization failed for path "${sqlitePath}": ${toErrorMessage(error)}`,
      );
    }
    return createInMemorySessionMemoryPersistence();
  }
}

/**
 * Start and run the HTTP backend server, exposing health and chat endpoints and initializing runtime configuration and session persistence.
 *
 * Initializes runtime and memory configuration from environment variables, creates session-memory persistence, registers health and chat routes, and starts an HTTP listener. Handles:
 * - GET/HEAD /health and /api/health by returning the health route response;
 * - POST /chat and /api/chat by invoking the chat route, mapping chat outcomes to HTTP status codes, and returning JSON responses;
 * - unknown paths with a 404 JSON error.
 *
 * Side effects include binding a network listener to the configured host and port and writing JSON responses for each request.
 */
async function main(): Promise<void> {
  const host = process.env.BACKEND_HOST?.trim() || DEFAULT_HOST;
  const portCandidate = Number.parseInt(process.env.BACKEND_PORT ?? `${DEFAULT_PORT}`, 10);
  const port = Number.isInteger(portCandidate) && portCandidate > 0 ? portCandidate : DEFAULT_PORT;
  const runtimeBackend =
    process.env.SHINON_RUNTIME_BACKEND?.trim() === "ollama" ? "ollama" : "llamacpp";
  const runtimeFallbackBackend =
    runtimeBackend === "llamacpp" ? "ollama" : "llamacpp";
  const runtimeModel = process.env.SHINON_RUNTIME_MODEL?.trim() || "qwen2.5:0.5b";

  const memoryTtlSeconds = toPositiveInteger(process.env.SHINON_MEMORY_TTL_SECONDS);
  const sessionMemoryPersistence = await createSessionMemoryPersistence();
  const chatRoute = createChatRoute({
    memoryContext: Object.freeze({
      backend: runtimeBackend,
      fallbackBackend: runtimeFallbackBackend,
      modelHint: runtimeModel,
      allowFallback: true,
    }),
    sessionMemoryPersistence,
    memoryTtlSeconds,
    memoryDecayKeepLatest: toPositiveInteger(process.env.SHINON_MEMORY_KEEP_LATEST_PER_CONVERSATION),
  });
  const healthRoute = createHealthRoute({
    backendHealth: () =>
      Object.freeze({
        ok: true,
        code: "BACKEND_OK",
        message: "runtime backend is ready",
      }),
  });

  const server = createServer(async (request, response) => {
    try {
      const parsed = await toParsedRequest(request);
      const path = toPath(parsed.url);

      if (path === "/health" || path === "/api/health") {
        const health = await healthRoute({
          method: parsed.method === "HEAD" ? "HEAD" : "GET",
          headers: parsed.headers,
          requestId: parsed.headers["x-request-id"],
        });
        writeJson(response, health.status, health.body);
        return;
      }

      if (path === "/chat" || path === "/api/chat") {
        if (parsed.method !== "POST") {
          writeJson(response, 405, {
            ok: false,
            status: "error",
            error: {
              code: "METHOD_NOT_ALLOWED",
              message: "chat route only accepts POST",
            },
          });
          return;
        }

        console.log(`[Session-Memory] Request UUID: ${parsed.headers["x-request-id"] || "none"}`);
        console.log(`[Session-Memory] Body Session ID: ${(parsed.body as any)?.sessionId || "none"}`);
        
        const chatResponse = await chatRoute.handle({
          method: parsed.method,
          url: parsed.url,
          headers: parsed.headers,
          body: parsed.body,
        });

        console.log(`[Session-Memory] Persisted successfully in SQLite für Session ${(parsed.body as any)?.sessionId || "none"}`);

        const status = chatResponse.ok
          ? 200
          : chatResponse.error.code === "BAD_REQUEST"
            ? 400
            : chatResponse.error.code === "ORCHESTRATION_FAILED"
              ? 502
              : 500;

        writeJson(response, status, chatResponse);
        return;
      }

      // [DEV] Model Scanner Route - Scans %APPDATA% for .gguf models
      if (path === "/api/models" || path === "/models") {
        if (parsed.method !== "GET") {
          writeJson(response, 405, {
            ok: false,
            status: "error",
            error: {
              code: "METHOD_NOT_ALLOWED",
              message: "models route only accepts GET",
            },
          });
          return;
        }

        try {
          const result = await scanModels();
          writeJson(response, result.ok ? 200 : 500, result);
          return;
        } catch {
          writeJson(response, 500, {
            ok: false,
            status: "error",
            error: {
              code: "INTERNAL_SERVER_ERROR",
              message: "Model scan failed",
            },
          });
          return;
        }
      }

      writeJson(response, 404, {
        ok: false,
        status: "error",
        error: {
          code: "NOT_FOUND",
          message: "route not found",
        },
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "unknown backend error";
      writeJson(response, 400, {
        ok: false,
        status: "error",
        error: {
          code: "BAD_REQUEST",
          message,
        },
      });
    }
  });

  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, host, () => {
      resolve();
    });
  });

  const address = server.address();
  const printableAddress =
    typeof address === "string"
      ? address
      : address == null
        ? `${host}:${port}`
        : `${address.address}:${address.port}`;

  console.log(`backend-runtime listening on http://${printableAddress}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  void main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
