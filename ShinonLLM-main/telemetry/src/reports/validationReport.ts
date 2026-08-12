type PlainObject = Record<string, unknown>;

export type ValidationReportArtifact = Readonly<{
  artifactType: "telemetry.evidence";
  kind: "validation-report.evidence";
  run_id: string;
  revision: number;
  sequence: number;
  payload: unknown;
  evidence_id: string;
}>;

export type ValidationReportResult = ReadonlyArray<ValidationReportArtifact> &
  Readonly<{
    run_id: string;
    revision: number;
    sequence: number;
    payload: unknown;
    artifact: ValidationReportArtifact;
    artifacts: ReadonlyArray<ValidationReportArtifact>;
    report_id: string;
  }>;

type ProgressMarker = Readonly<{
  revision: number;
  sequence: number;
}>;

const lastProgressByRun = new Map<string, ProgressMarker>();
const artifactsByRun = new Map<string, Array<ValidationReportArtifact>>();

function failClosed(message: string): never {
  throw new Error(`validationReport: ${message}`);
}

function isPlainObject(value: unknown): value is PlainObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isSafeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && Number.isSafeInteger(value);
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

function serializeForEvidence(value: unknown, seen: WeakSet<object> = new WeakSet<object>()): string {
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
  if (valueType === "bigint" || valueType === "undefined" || valueType === "function" || valueType === "symbol") {
    return JSON.stringify(String(value));
  }

  if (Array.isArray(value)) {
    return `[${value.map((entry) => serializeForEvidence(entry, seen)).join(",")}]`;
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
    .map((key) => `${JSON.stringify(key)}:${serializeForEvidence(value[key], seen)}`);
  seen.delete(value);
  return `{${entries.join(",")}}`;
}

function buildEvidenceId(input: Readonly<{
  run_id: string;
  revision: number;
  sequence: number;
  payload: unknown;
}>): string {
  return `validation-report:${input.run_id}:${input.revision}:${input.sequence}:${serializeForEvidence(input.payload)}`;
}

function enforceSequenceProgression(run_id: string, revision: number, sequence: number): void {
  const previous = lastProgressByRun.get(run_id);
  if (previous === undefined) {
    return;
  }

  if (revision < previous.revision) {
    failClosed("revision must not move backwards");
  }

  if (revision === previous.revision && sequence <= previous.sequence) {
    failClosed("sequence progression must be strictly increasing within a revision");
  }
}

function appendArtifact(run_id: string, artifact: ValidationReportArtifact): ReadonlyArray<ValidationReportArtifact> {
  const history = artifactsByRun.get(run_id) ?? [];
  history.push(artifact);
  artifactsByRun.set(run_id, history);
  return history;
}

function recordProgress(run_id: string, revision: number, sequence: number): void {
  lastProgressByRun.set(run_id, Object.freeze({ revision, sequence }));
}

export function buildValidationReport(input: unknown): ValidationReportResult {
  const event = normalizeInput(input);
  enforceSequenceProgression(event.run_id, event.revision, event.sequence);

  const artifact: ValidationReportArtifact = Object.freeze({
    artifactType: "telemetry.evidence",
    kind: "validation-report.evidence",
    run_id: event.run_id,
    revision: event.revision,
    sequence: event.sequence,
    payload: event.payload,
    evidence_id: buildEvidenceId(event),
  });

  const history = appendArtifact(event.run_id, artifact);
  recordProgress(event.run_id, event.revision, event.sequence);
  const artifacts = Object.freeze([...history]);

  const result = Object.assign([...history], {
    run_id: event.run_id,
    revision: event.revision,
    sequence: event.sequence,
    payload: event.payload,
    artifact,
    artifacts,
    report_id: artifact.evidence_id,
  }) as ValidationReportResult;

  return Object.freeze(result);
}
