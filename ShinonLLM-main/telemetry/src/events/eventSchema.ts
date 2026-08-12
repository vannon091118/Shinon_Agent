import type { RuntimeEvent } from "../../shared/src/types/events";

type PlainObject = Record<string, unknown>;

type EvidenceArtifact = Readonly<{
  artifactType: "telemetry.evidence";
  run_id: string;
  revision: number;
  sequence: number;
  payload: unknown;
  evidence_id: string;
}>;

type EventSchemaParseResult =
  | Readonly<{ success: true; data: ReadonlyArray<EvidenceArtifact> }>
  | Readonly<{ success: false; error: Error }>;

type ProgressMarker = Readonly<{
  revision: number;
  sequence: number;
}>;

const lastProgressByRun = new Map<string, ProgressMarker>();

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isSafeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && Number.isSafeInteger(value);
}

function failClosed(message: string): never {
  throw new Error(`eventSchema: ${message}`);
}

function normalizeRuntimeEvent(input: unknown): RuntimeEvent {
  if (!isPlainObject(input)) {
    failClosed("input must be a plain object");
  }

  if (!("run_id" in input)) {
    failClosed("run_id is required");
  }
  if (!("revision" in input)) {
    failClosed("revision is required");
  }
  if (!("sequence" in input)) {
    failClosed("sequence is required");
  }
  if (!("payload" in input)) {
    failClosed("payload is required");
  }

  if (!isNonEmptyString(input.run_id)) {
    failClosed("run_id must be a non-empty string");
  }
  if (!isSafeInteger(input.revision) || input.revision < 0) {
    failClosed("revision must be a non-negative safe integer");
  }
  if (!isSafeInteger(input.sequence) || input.sequence < 1) {
    failClosed("sequence must be a positive safe integer");
  }

  return Object.freeze({
    run_id: input.run_id.trim(),
    revision: input.revision,
    sequence: input.sequence,
    payload: input.payload,
  });
}

function stableSerialize(value: unknown, seen: WeakSet<object>): string {
  if (value === null) {
    return "null";
  }

  const valueType = typeof value;
  if (valueType === "string") {
    return JSON.stringify(value);
  }
  if (valueType === "number" || valueType === "boolean") {
    return String(value);
  }
  if (valueType === "bigint") {
    return JSON.stringify(value.toString());
  }
  if (valueType === "undefined" || valueType === "function" || valueType === "symbol") {
    return JSON.stringify(String(value));
  }

  if (Array.isArray(value)) {
    return `[${value.map((entry) => stableSerialize(entry, seen)).join(",")}]`;
  }

  if (!isPlainObject(value)) {
    return JSON.stringify(String(value));
  }

  if (seen.has(value)) {
    failClosed("payload must not contain circular references");
  }

  seen.add(value);
  const entries = Object.keys(value)
    .sort((left, right) => left.localeCompare(right))
    .map((key) => `${JSON.stringify(key)}:${stableSerialize(value[key], seen)}`);
  seen.delete(value);
  return `{${entries.join(",")}}`;
}

function buildEvidenceArtifact(event: RuntimeEvent): EvidenceArtifact {
  const evidenceId = `evidence:${event.run_id}:${event.revision}:${event.sequence}:${stableSerialize(
    event.payload,
    new WeakSet<object>(),
  )}`;

  return Object.freeze({
    artifactType: "telemetry.evidence",
    run_id: event.run_id,
    revision: event.revision,
    sequence: event.sequence,
    payload: event.payload,
    evidence_id: evidenceId,
  });
}

function enforceSequenceProgression(event: RuntimeEvent): void {
  const previous = lastProgressByRun.get(event.run_id);
  if (previous === undefined) {
    return;
  }

  if (event.revision < previous.revision) {
    failClosed("revision must not move backwards");
  }

  if (event.revision === previous.revision && event.sequence <= previous.sequence) {
    failClosed("sequence progression must be strictly increasing within a revision");
  }
}

function recordProgress(event: RuntimeEvent): void {
  lastProgressByRun.set(event.run_id, Object.freeze({ revision: event.revision, sequence: event.sequence }));
}

function parseEventOrThrow(input: unknown): ReadonlyArray<EvidenceArtifact> {
  const event = normalizeRuntimeEvent(input);
  enforceSequenceProgression(event);
  const artifact = buildEvidenceArtifact(event);
  recordProgress(event);
  return Object.freeze([artifact]);
}

export const EVENT_SCHEMA = Object.freeze({
  name: "EVENT_SCHEMA",
  parse(input: unknown): ReadonlyArray<EvidenceArtifact> {
    return parseEventOrThrow(input);
  },
  safeParse(input: unknown): EventSchemaParseResult {
    try {
      return Object.freeze({
        success: true,
        data: parseEventOrThrow(input),
      });
    } catch (error) {
      return Object.freeze({
        success: false,
        error: error instanceof Error ? error : new Error("eventSchema: parse failed"),
      });
    }
  },
});
