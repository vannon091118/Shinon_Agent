import { strict as assert } from "node:assert";
import { pathToFileURL } from "node:url";

import { appendEvent } from "../../telemetry/src/events/eventWriter.js";
import { computeReplayHash } from "../../telemetry/src/replay/replayHash.js";

type ReplayGateSut = Readonly<{
  computeReplayHash: typeof computeReplayHash;
  appendEvent: typeof appendEvent;
}>;

type ReplayGateFixtures = Readonly<{
  deterministicHash: Readonly<{
    first: Parameters<typeof computeReplayHash>;
    second: Parameters<typeof computeReplayHash>;
  }>;
  sequenceIntegrity: Readonly<{
    input: Parameters<typeof appendEvent>[0];
    expectedMessage: RegExp;
  }>;
}>;

type ReplayGateResult = Readonly<{
  passed: true;
  checks: ReadonlyArray<string>;
}>;

function buildFixtures(): ReplayGateFixtures {
  return Object.freeze({
    deterministicHash: Object.freeze({
      first: [
        "replay-gate-run",
        1,
        7,
        Object.freeze({
          alpha: 1,
          beta: Object.freeze(["x", Object.freeze({ nested: true })]),
          gamma: Object.freeze({ left: "L", right: "R" }),
        }),
      ] as Parameters<typeof computeReplayHash>,
      second: [
        "replay-gate-run",
        1,
        7,
        Object.freeze({
          gamma: Object.freeze({ right: "R", left: "L" }),
          beta: Object.freeze(["x", Object.freeze({ nested: true })]),
          alpha: 1,
        }),
      ] as Parameters<typeof computeReplayHash>,
    }),
    sequenceIntegrity: Object.freeze({
      input: Object.freeze({
        run_id: "replay-gate-sequence-20260402",
        revision: 1,
        sequence: 2,
        payload: Object.freeze({
          gate: "replay",
          expected: "strict",
        }),
      }) as Parameters<typeof appendEvent>[0],
      expectedMessage: /eventWriter: invalid sequence progression/i,
    }),
  });
}

async function assertDeterministicReplayHash(
  sut: ReplayGateSut,
  firstInput: Parameters<typeof computeReplayHash>,
  secondInput: Parameters<typeof computeReplayHash>,
): Promise<void> {
  const first = sut.computeReplayHash(...firstInput);
  const second = sut.computeReplayHash(...secondInput);
  const sequenceVariant = sut.computeReplayHash(
    first.run_id,
    first.revision,
    first.sequence + 1,
    first.payload,
  );

  assert.equal(first.run_id, second.run_id);
  assert.equal(first.revision, second.revision);
  assert.equal(first.sequence, second.sequence);
  assert.equal(first.payload_hash, second.payload_hash);
  assert.equal(first.replay_hash, second.replay_hash);
  assert.notEqual(first.replay_hash, sequenceVariant.replay_hash);
  assert.equal(sequenceVariant.sequence, first.sequence + 1);
  assert.equal(first.artifacts.length, 1);
  assert.equal(second.artifacts.length, 1);
  const firstArtifact = first.artifacts[0];
  const secondArtifact = second.artifacts[0];
  assert.ok(firstArtifact);
  assert.ok(secondArtifact);
  assert.equal(firstArtifact.replay_hash, first.replay_hash);
  assert.equal(secondArtifact.replay_hash, second.replay_hash);
}

async function assertSequenceIntegrity(
  sut: ReplayGateSut,
  input: Parameters<typeof appendEvent>[0],
  expectedMessage: RegExp,
): Promise<void> {
  await assert.rejects(
    async () => {
      await sut.appendEvent(input);
    },
    (error: unknown) =>
      error instanceof Error &&
      expectedMessage.test(error.message) &&
      error.message.includes("expected 1, received 2"),
  );
}

export async function replaygatespecMain(
  sut: ReplayGateSut = Object.freeze({
    computeReplayHash,
    appendEvent,
  }),
  fixtures: ReplayGateFixtures = buildFixtures(),
): Promise<ReplayGateResult> {
  await assertDeterministicReplayHash(
    sut,
    fixtures.deterministicHash.first,
    fixtures.deterministicHash.second,
  );

  await assertSequenceIntegrity(
    sut,
    fixtures.sequenceIntegrity.input,
    fixtures.sequenceIntegrity.expectedMessage,
  );

  return Object.freeze({
    passed: true as const,
    checks: Object.freeze([
      "deterministic replay hash",
      "sequence integrity",
    ]),
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await replaygatespecMain();
}
