export type EnvConfig = Readonly<{
  nodeEnv: "development" | "test" | "production";
  port: number;
  host: string;
  appName: string;
  logLevel: "debug" | "info" | "warn" | "error";
  databaseUrl: string;
  jwtSecret: string;
  corsOrigin: string | null;
  trustProxy: boolean;
}>;

type EnvSource = Record<string, string | undefined>;

const ALLOWED_NODE_ENVS = new Set(["development", "test", "production"] as const);
const ALLOWED_LOG_LEVELS = new Set(["debug", "info", "warn", "error"] as const);

function readRequired(source: EnvSource, key: string): string {
  const value = source[key];
  if (value == null || value.trim() === "") {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value.trim();
}

function readOptional(source: EnvSource, key: string, fallback: string): string {
  const value = source[key];
  return value == null || value.trim() === "" ? fallback : value.trim();
}

function parseNodeEnv(value: string): EnvConfig["nodeEnv"] {
  if (!ALLOWED_NODE_ENVS.has(value as EnvConfig["nodeEnv"])) {
    throw new Error(`Invalid NODE_ENV: ${value}`);
  }
  return value as EnvConfig["nodeEnv"];
}

function parseLogLevel(value: string): EnvConfig["logLevel"] {
  if (!ALLOWED_LOG_LEVELS.has(value as EnvConfig["logLevel"])) {
    throw new Error(`Invalid LOG_LEVEL: ${value}`);
  }
  return value as EnvConfig["logLevel"];
}

function parsePort(value: string): number {
  const port = Number.parseInt(value, 10);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid PORT: ${value}`);
  }
  return port;
}

function parseBoolean(value: string): boolean {
  const normalized = value.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) {
    return true;
  }
  if (["0", "false", "no", "off"].includes(normalized)) {
    return false;
  }
  throw new Error(`Invalid boolean value: ${value}`);
}

function normalizeCorsOrigin(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" || trimmed === "*" ? null : trimmed;
}

export function loadEnvConfig(source: EnvSource = process.env): EnvConfig {
  const nodeEnv = parseNodeEnv(readOptional(source, "NODE_ENV", "development"));
  const port = parsePort(readRequired(source, "PORT"));
  const host = readOptional(source, "HOST", "0.0.0.0");
  const appName = readOptional(source, "APP_NAME", "backend");
  const logLevel = parseLogLevel(readOptional(source, "LOG_LEVEL", "info"));
  const databaseUrl = readRequired(source, "DATABASE_URL");
  const jwtSecret = readRequired(source, "JWT_SECRET");
  const corsOriginRaw = source["CORS_ORIGIN"];
  const trustProxy = parseBoolean(readOptional(source, "TRUST_PROXY", "false"));

  return Object.freeze({
    nodeEnv,
    port,
    host,
    appName,
    logLevel,
    databaseUrl,
    jwtSecret,
    corsOrigin: corsOriginRaw == null ? null : normalizeCorsOrigin(corsOriginRaw),
    trustProxy,
  });
}
