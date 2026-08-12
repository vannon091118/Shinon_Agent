import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

type PlainObject = Record<string, unknown>;

export type AppendEventInput = Readonly<{
  run_id: string;
  revision: number;
  sequence: number;
  payload: unknown;
}>;

export type AppendEventArtifact = Readonly<{
  path: string;
  bytesWritten: number;
}>;

export type AppendEventResult = Readonly<{
  artifact: AppendEventArtifact;
  event: Readonly<{
    run_id: string;
    revision: number;
    sequence: number;
    payload: unknown;
  }>;
}>;

const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_EVIDENCE_DIR = path.resolve(MODULE_DIR, "../../../evidence");

const EVENT_SCHEMA = Object.freeze({
  required: Object.freeze(["run_id", "revision", "sequence", "payload"]),
  minRevision: 1,
  minSequence: 1,
});

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function failClosed(message: string): never {
  throw new Error(`eventWriter: ${message}`);
}

function isSafeRunId(value: string): boolean {
  return /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/u.test(value);
}

function normalizeRunId(value: unknown): string {
  if (typeof value !== "string") {
    failClosed("run_id must be a non-empty string");
  }

  const runId = value.trim();
  if (runId.length === 0) {
    failClosed("run_id must be a non-empty string");
  }

  if (!isSafeRunId(runId)) {
    failClosed("run_id contains unsupported path characters");
  }

  return runId;
}

function normalizePositiveInteger(value: unknown, fieldName: "revision" | "sequence"): number {
  if (typeof value !== "number" || !Number.isFinite(value) || !Number.isInteger(value)) {
    failClosed(`${fieldName} must be a positive integer`);
  }

  if (value < 1) {
    failClosed(`${fieldName} must be a positive integer`);
  }

  return value;
}

function validateSerializable(value: unknown, seen: WeakSet<object>): void {
  if (value === null) {
    return;
  }

  const valueType = typeof value;
  if (
    valueType === "string" ||
    valueType === "boolean" ||
    valueType === "undefined"
  ) {
    return;
  }

  if (valueType === "number") {
    if (!Number.isFinite(value)) {
      failClosed("payload contains a non-finite number");
    }
    return;
  }

  if (valueType === "bigint" || valueType === "symbol" || valueType === "function") {
    failClosed("payload contains a non-serializable value");
  }

  if (Array.isArray(value)) {
    for (const entry of value) {
      validateSerializable(entry, seen);
    }
    return;
  }

  if (!isPlainObject(value)) {
    return;
  }

  if (seen.has(value)) {
    failClosed("payload contains a circular reference");
  }

  seen.add(value);
  for (const key of Object.keys(value)) {
    validateSerializable(value[key], seen);
  }
  seen.delete(value);
}

function stableSerialize(value: unknown, seen: WeakSet<object> = new WeakSet<object>()): string {
  if (value === null) {
    return "null";
  }

  const valueType = typeof value;
  if (valueType === "string") {
    return JSON.stringify(value);
  }
  if (valueType === "number") {
    if (!Number.isFinite(value)) {
      failClosed("payload contains a non-finite number");
    }
    return String(value);
  }
  if (valueType === "boolean") {
    return value ? "true" : "false";
  }
  if (valueType === "bigint" || valueType === "symbol" || valueType === "function" || valueType === "undefined") {
    return JSON.stringify(String(value));
  }

  if (Array.isArray(value)) {
    return `[${value.map((entry) => stableSerialize(entry, seen)).join(",")}]`;
  }

  if (!isPlainObject(value)) {
    return JSON.stringify(String(value));
  }

  if (seen.has(value)) {
    failClosed("payload contains a circular reference");
  }

  seen.add(value);
  const serializedEntries = Object.keys(value)
    .sort((left, right) => left.localeCompare(right))
    .map((key) => `${JSON.stringify(key)}:${stableSerialize(value[key], seen)}`);
  seen.delete(value);
  return `{${serializedEntries.join(",")}}`;
}

function buildEvidenceDir(baseDir: string, runId: string): string {
  return path.join(baseDir, runId);
}

function buildArtifactPath(baseDir: string, runId: string, sequence: number): string {
  const fileName = `${String(sequence).padStart(12, "0")}.json`;
  return path.join(buildEvidenceDir(baseDir, runId), fileName);
}

function parseSequenceFromFileName(fileName: string): number | null {
  const match = /^(\d+)\.json$/u.exec(fileName);
  if (!match) {
    return null;
  }

  const sequence = Number.parseInt(match[1], 10);
  return Number.isInteger(sequence) && sequence > 0 ? sequence : null;
}

async function readLastSequence(runDir: string): Promise<number | null> {
  let entries: Array<{ name: string }> = [];

  try {
    const result = await readdir(runDir, { withFileTypes: true });
    entries = result
      .filter((entry) => entry.isFile())
      .map((entry) => ({ name: entry.name }));
  } catch (error) {
    if (error instanceof Error && (error as NodeJS.ErrnoException).code === "ENOENT") {
      return null;
    }
    throw error;
  }

  const sequences = entries
    .map((entry) => parseSequenceFromFileName(entry.name))
    .filter((sequence): sequence is number => sequence !== null)
    .sort((left, right) => left - right);

  if (sequences.length === 0) {
    return null;
  }

  const lastSequence = sequences[sequences.length - 1];
  const lastArtifactPath = path.join(runDir, `${String(lastSequence).padStart(12, "0")}.json`);

  let content: string;
  try {
    content = await readFile(lastArtifactPath, "utf8");
  } catch (error) {
    failClosed("existing evidence artifact could not be read");
  }

  try {
    const parsed = JSON.parse(content) as PlainObject;
    if (!isPlainObject(parsed) || parsed.sequence !== lastSequence) {
      failClosed("existing evidence artifact is malformed");
    }
  } catch {
    failClosed("existing evidence artifact is malformed");
  }

  return lastSequence;
}

function normalizeInput(input: unknown): Readonly<{
  run_id: string;
  revision: number;
  sequence: number;
  payload: unknown;
}> {
  if (!isPlainObject(input)) {
    failClosed("input must be a plain object");
  }

  for (const field of EVENT_SCHEMA.required) {
    if (!(field in input)) {
      failClosed(`${field} is required`);
    }
  }

  const run_id = normalizeRunId(input.run_id);
  const revision = normalizePositiveInteger(input.revision, "revision");
  const sequence = normalizePositiveInteger(input.sequence, "sequence");
  validateSerializable(input.payload, new WeakSet<object>());

  return Object.freeze({
    run_id,
    revision,
    sequence,
    payload: input.payload,
  });
}

export async function appendEvent(input: unknown): Promise<AppendEventResult> {
  const event = normalizeInput(input);
  const evidenceDir = DEFAULT_EVIDENCE_DIR;
  const runDir = buildEvidenceDir(evidenceDir, event.run_id);
  const expectedSequence = (await readLastSequence(runDir)) ?? 0;

  if (event.sequence !== expectedSequence + 1) {
    failClosed(`invalid sequence progression: expected ${expectedSequence + 1}, received ${event.sequence}`);
  }

  const artifactPath = buildArtifactPath(evidenceDir, event.run_id, event.sequence);
  const payload = Object.freeze({
    run_id: event.run_id,
    revision: event.revision,
    sequence: event.sequence,
    payload: event.payload,
  });
  const body = `${stableSerialize(payload)}\n`;

  await mkdir(runDir, { recursive: true });

  try {
    await writeFile(artifactPath, body, { flag: "wx" });
  } catch (error) {
    failClosed("evidence artifact could not be written atomically");
  }

  return Object.freeze({
    artifact: Object.freeze({
      path: artifactPath,
      bytesWritten: Buffer.byteLength(body, "utf8"),
    }),
    event,
  });
}
