import { hash } from "../../../shared/src/utils/hash.js";
import { stableStringify } from "../../../shared/src/utils/stableJson.js";

export type ReplayEvidenceArtifact = Readonly<{
  kind: "replay-fingerprint";
  run_id: string;
  revision: number;
  sequence: number;
  payload_hash: string;
  replay_hash: string;
}>;

export type ReplayHashResult = Readonly<{
  run_id: string;
  revision: number;
  sequence: number;
  payload: unknown;
  payload_hash: string;
  replay_hash: string;
  artifacts: ReadonlyArray<ReplayEvidenceArtifact>;
}>;

function assertValidRunId(run_id: unknown): asserts run_id is string {
  if (typeof run_id !== "string" || run_id.trim().length === 0) {
    throw new TypeError("run_id must be a non-empty string");
  }
}

function assertValidRevision(revision: unknown): asserts revision is number {
  if (typeof revision !== "number" || !Number.isInteger(revision) || revision < 1) {
    throw new TypeError("revision must be a positive integer");
  }
}

function assertValidSequence(sequence: unknown): asserts sequence is number {
  if (typeof sequence !== "number" || !Number.isInteger(sequence) || sequence < 0) {
    throw new TypeError("invalid sequence progression");
  }
}

export function computeReplayHash(
  run_id: unknown,
  revision: unknown,
  sequence: unknown,
  payload: unknown
): ReplayHashResult {
  assertValidRunId(run_id);
  assertValidRevision(revision);
  assertValidSequence(sequence);

  const payload_hash = hash(stableStringify(payload));
  const replay_hash = hash(
    stableStringify({
      run_id,
      revision,
      sequence,
      payload_hash,
    })
  );

  const artifact: ReplayEvidenceArtifact = {
    kind: "replay-fingerprint",
    run_id,
    revision,
    sequence,
    payload_hash,
    replay_hash,
  };

  return {
    run_id,
    revision,
    sequence,
    payload,
    payload_hash,
    replay_hash,
    artifacts: [artifact],
  };
}
