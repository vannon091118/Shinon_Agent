import { strict as assert } from "node:assert";
import { pathToFileURL } from "node:url";

import { actionSchema } from "../../orchestrator/src/contracts/actionSchema";
import { computeReplayHash } from "../../telemetry/src/replay/replayHash";
import { inputSchema } from "../../orchestrator/src/contracts/inputSchema";
import { outputSchema } from "../../orchestrator/src/contracts/outputSchema";

type BaselineIntegrityResult = Readonly<{
  line: string;
}>;

function buildSeedPayloadA(): Readonly<{
  alpha: number;
  beta: ReadonlyArray<string | Readonly<{ nested: boolean }>>;
  gamma: Readonly<{ left: string; right: string }>;
}> {
  return Object.freeze({
    alpha: 1,
    beta: Object.freeze(["x", Object.freeze({ nested: true })]),
    gamma: Object.freeze({ left: "L", right: "R" }),
  });
}

function buildSeedPayloadB(): Readonly<{
  gamma: Readonly<{ right: string; left: string }>;
  beta: ReadonlyArray<string | Readonly<{ nested: boolean }>>;
  alpha: number;
}> {
  return Object.freeze({
    gamma: Object.freeze({ right: "R", left: "L" }),
    beta: Object.freeze(["x", Object.freeze({ nested: true })]),
    alpha: 1,
  });
}

function buildValidActionInput(): unknown {
  return Object.freeze({
    turn: Object.freeze({
      requestId: "action-request",
      sessionId: "action-session",
      conversationId: "action-conversation",
      userText: "action payload",
      history: Object.freeze([
        Object.freeze({
          role: "assistant",
          content: "prior assistant turn",
        }),
      ]),
    }),
    memoryContext: Object.freeze({
      modelHint: "action-model",
      allowedActions: Object.freeze(["send_message", "log_event"]),
      actions: Object.freeze([
        Object.freeze({
          type: "send_message",
          args: Object.freeze({ channel: "inbox" }),
          target: "queue-1",
        }),
      ]),
    }),
  });
}

function buildInvalidActionInput(): unknown {
  return Object.freeze({
    turn: Object.freeze({
      requestId: "action-invalid-request",
      sessionId: "action-invalid-session",
      conversationId: "action-invalid-conversation",
      userText: "action should fail",
      history: Object.freeze([
        Object.freeze({
          role: "system",
          content: "this turn is valid but actions are blocked",
        }),
      ]),
    }),
    memoryContext: Object.freeze({
      modelHint: "action-invalid-model",
      actions: Object.freeze([
        Object.freeze({
          type: "blocked_action",
        }),
      ]),
    }),
  });
}

export function baselineintegrityspecMain(): BaselineIntegrityResult {
  const first = computeReplayHash("replay-gate-run", 1, 7, buildSeedPayloadA());
  const second = computeReplayHash("replay-gate-run", 1, 7, buildSeedPayloadB());
  const sequenceVariant = computeReplayHash("replay-gate-run", 1, 8, buildSeedPayloadA());

  assert.equal(first.replay_hash, second.replay_hash);
  assert.notEqual(first.replay_hash, sequenceVariant.replay_hash);

  const validAction = actionSchema.safeParse(buildValidActionInput());
  const invalidAction = actionSchema.safeParse(buildInvalidActionInput());

  assert.equal(validAction.success, true);
  assert.equal(invalidAction.success, false);
  if (!invalidAction.success) {
    assert.equal(
      invalidAction.error.message.startsWith(
        "actionSchema: memoryContext.actions are not allowed without memoryContext.allowedActions",
      ),
      true,
    );
  }

  // Fail-closed replay invariants: invalid identifiers and counters must be rejected.
  assert.throws(
    () => computeReplayHash("", 1, 7, buildSeedPayloadA()),
    (error: unknown) => error instanceof TypeError && error.message.includes("run_id must be a non-empty string"),
  );
  assert.throws(
    () => computeReplayHash("replay-gate-run", 0, 7, buildSeedPayloadA()),
    (error: unknown) => error instanceof TypeError && error.message.includes("revision must be a positive integer"),
  );
  assert.throws(
    () => computeReplayHash("replay-gate-run", 1, -1, buildSeedPayloadA()),
    (error: unknown) => error instanceof TypeError && error.message.includes("invalid sequence progression"),
  );

  // Fail-closed contract invariants: missing mandatory fields must never parse.
  const missingTurnInput = Object.freeze({
    memoryContext: Object.freeze({
      modelHint: "broken-model",
    }),
  });
  const missingTurnInputResult = inputSchema.safeParse(missingTurnInput);
  const missingTurnOutputResult = outputSchema.safeParse(missingTurnInput);
  assert.equal(missingTurnInputResult.success, false);
  assert.equal(missingTurnOutputResult.success, false);
  if (!missingTurnInputResult.success) {
    assert.equal(
      missingTurnInputResult.error.message.startsWith("inputSchema: input.turn is required"),
      true,
    );
  }
  if (!missingTurnOutputResult.success) {
    assert.equal(
      missingTurnOutputResult.error.message.startsWith("outputSchema: output.turn is required"),
      true,
    );
  }

  // Fail-closed action invariants: malformed allowedActions and action payloads are blocked.
  const malformedAllowedActions = Object.freeze({
    turn: Object.freeze({
      requestId: "action-malformed-request",
      sessionId: "action-malformed-session",
      conversationId: "action-malformed-conversation",
      userText: "action malformed",
      history: Object.freeze([
        Object.freeze({
          role: "assistant",
          content: "prior assistant turn",
        }),
      ]),
    }),
    memoryContext: Object.freeze({
      modelHint: "action-model",
      allowedActions: Object.freeze([123]),
      actions: Object.freeze([
        Object.freeze({
          type: "send_message",
        }),
      ]),
    }),
  });
  const malformedActionsResult = actionSchema.safeParse(malformedAllowedActions);
  assert.equal(malformedActionsResult.success, false);
  if (!malformedActionsResult.success) {
    assert.equal(
      malformedActionsResult.error.message.startsWith(
        "actionSchema: memoryContext.allowedActions[0] must be a non-empty string",
      ),
      true,
    );
  }

  const line = [
    "testline",
    "seed_pair=replay-gate-run|rev=1|seq=7",
    `replay_hash_equal=${first.replay_hash === second.replay_hash ? "1" : "0"}`,
    `sequence_variant_diff=${first.replay_hash !== sequenceVariant.replay_hash ? "1" : "0"}`,
    "action_set_declared=send_message,log_event",
    `action_send_message=${validAction.success ? "accepted" : "rejected"}`,
    `action_blocked_action=${invalidAction.success ? "accepted" : "rejected"}`,
  ].join(" | ");

  console.log(line);
  return Object.freeze({ line });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  baselineintegrityspecMain();
}
