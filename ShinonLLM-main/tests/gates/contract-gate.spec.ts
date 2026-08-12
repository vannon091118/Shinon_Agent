import { strict as assert } from "node:assert";
import { pathToFileURL } from "node:url";

import { actionSchema } from "../../orchestrator/src/contracts/actionSchema";
import { inputSchema } from "../../orchestrator/src/contracts/inputSchema";
import { outputSchema } from "../../orchestrator/src/contracts/outputSchema";

type ValidatedAssistantPayload = Readonly<{
  reply: string;
  message: Readonly<{
    role: "assistant";
    content: string;
  }>;
  source: "orchestrator";
  model: string;
  prompt: string;
  guardrailStatus: "validated";
}>;

type ContractGateSut = Readonly<{
  inputSchema: typeof inputSchema;
  outputSchema: typeof outputSchema;
  actionSchema: typeof actionSchema;
}>;

type ContractGateFixtures = Readonly<{
  validInput: Readonly<{
    turn: Readonly<{
      requestId: string;
      sessionId: string;
      conversationId: string;
      userText: string;
      history: ReadonlyArray<Readonly<{
        role: "system" | "user" | "assistant";
        content: string;
      }>>;
    }>;
    memoryContext: Readonly<Record<string, unknown>>;
  }>;
  validActionInput: Readonly<{
    turn: Readonly<{
      requestId: string;
      sessionId: string;
      conversationId: string;
      userText: string;
      history: ReadonlyArray<Readonly<{
        role: "system" | "user" | "assistant";
        content: string;
      }>>;
    }>;
    memoryContext: Readonly<Record<string, unknown>>;
  }>;
  invalidMissingTurn: Readonly<{
    memoryContext: Readonly<Record<string, unknown>>;
  }>;
  invalidActionInput: Readonly<{
    turn: Readonly<{
      requestId: string;
      sessionId: string;
      conversationId: string;
      userText: string;
      history: ReadonlyArray<Readonly<{
        role: "system" | "user" | "assistant";
        content: string;
      }>>;
    }>;
    memoryContext: Readonly<Record<string, unknown>>;
  }>;
}>;

function buildFixtures(): ContractGateFixtures {
  return Object.freeze({
    validInput: Object.freeze({
      turn: Object.freeze({
        requestId: "  gate-request  ",
        sessionId: "  gate-session  ",
        conversationId: "  gate-conversation  ",
        userText: "  contract payload  ",
        history: Object.freeze([
          Object.freeze({
            role: "system",
            content: "  keep this deterministic  ",
          }),
          Object.freeze({
            role: "user",
            content: "  acknowledge the guardrail  ",
          }),
        ]),
      }),
      memoryContext: Object.freeze({
        modelHint: "  contract-model  ",
        policyId: "policy-alpha",
      }),
    }),
    validActionInput: Object.freeze({
      turn: Object.freeze({
        requestId: "  action-request  ",
        sessionId: "  action-session  ",
        conversationId: "  action-conversation  ",
        userText: "  action payload  ",
        history: Object.freeze([
          Object.freeze({
            role: "assistant",
            content: "  prior assistant turn  ",
          }),
        ]),
      }),
      memoryContext: Object.freeze({
        modelHint: "  action-model  ",
        allowedActions: Object.freeze(["send_message", "log_event"]),
        actions: Object.freeze([
          Object.freeze({
            type: " send_message ",
            args: Object.freeze({
              channel: "inbox",
            }),
            target: "  queue-1  ",
          }),
        ]),
      }),
    }),
    invalidMissingTurn: Object.freeze({
      memoryContext: Object.freeze({
        modelHint: "broken-model",
      }),
    }),
    invalidActionInput: Object.freeze({
      turn: Object.freeze({
        requestId: "  action-invalid-request  ",
        sessionId: "  action-invalid-session  ",
        conversationId: "  action-invalid-conversation  ",
        userText: "  action should fail  ",
        history: Object.freeze([
          Object.freeze({
            role: "system",
            content: "  this turns valid, the actions do not  ",
          }),
        ]),
      }),
      memoryContext: Object.freeze({
        modelHint: "  action-invalid-model  ",
        actions: Object.freeze([
          Object.freeze({
            type: "blocked_action",
          }),
        ]),
      }),
    }),
  });
}

function assertValidatedAssistantPayload(
  actual: ValidatedAssistantPayload,
  expected: Readonly<{
    reply: string;
    model: string;
    requestId: string;
    sessionId: string;
    conversationId: string;
  }>,
): void {
  assert.equal(actual.reply, expected.reply);
  assert.equal(actual.message.role, "assistant");
  assert.equal(actual.message.content, expected.reply);
  assert.equal(actual.source, "orchestrator");
  assert.equal(actual.model, expected.model);
  assert.equal(actual.guardrailStatus, "validated");
  assert.equal(actual.prompt.includes("SYSTEM: Validate assistant payload"), true);
  assert.equal(actual.prompt.includes(`USER: ${expected.reply}`), true);
  assert.equal(actual.prompt.includes(`requestId=${expected.requestId}`), false);
  assert.equal(actual.prompt.length > 0, true);
}

function assertSchemaSuccess(
  schema: {
    parse(input: unknown): ValidatedAssistantPayload;
    safeParse(input: unknown): Readonly<{ success: true; data: ValidatedAssistantPayload }> | Readonly<{ success: false; error: Error }>;
  },
  input: unknown,
  expectedReply: string,
  expectedModel: string,
): void {
  const parsed = schema.parse(input);
  assertValidatedAssistantPayload(parsed, {
    reply: expectedReply,
    model: expectedModel,
    requestId: "gate-request",
    sessionId: "gate-session",
    conversationId: "gate-conversation",
  });

  const safeParsed = schema.safeParse(input);
  assert.equal(safeParsed.success, true);
  if (safeParsed.success) {
    assertValidatedAssistantPayload(safeParsed.data, {
      reply: expectedReply,
      model: expectedModel,
      requestId: "gate-request",
      sessionId: "gate-session",
      conversationId: "gate-conversation",
    });
  }
}

function assertSchemaFailure(
  schema: {
    parse(input: unknown): ValidatedAssistantPayload;
    safeParse(input: unknown): Readonly<{ success: true; data: ValidatedAssistantPayload }> | Readonly<{ success: false; error: Error }>;
  },
  input: unknown,
  expectedMessagePrefix: string,
): void {
  assert.throws(() => schema.parse(input), (error: unknown) => {
    return error instanceof Error && error.message.startsWith(expectedMessagePrefix);
  });

  const safeParsed = schema.safeParse(input);
  assert.equal(safeParsed.success, false);
  if (!safeParsed.success) {
    assert.equal(safeParsed.error.message.startsWith(expectedMessagePrefix), true);
  }
}

const defaultSut: ContractGateSut = Object.freeze({
  inputSchema,
  outputSchema,
  actionSchema,
});

export function contractgatespecMain(
  sut: ContractGateSut = defaultSut,
  fixtures: ContractGateFixtures = buildFixtures(),
): void {
  assertSchemaSuccess(
    sut.inputSchema,
    fixtures.validInput,
    "contract payload",
    "contract-model",
  );

  assertSchemaSuccess(
    sut.outputSchema,
    fixtures.validInput,
    "contract payload",
    "contract-model",
  );

  assertSchemaSuccess(
    sut.actionSchema,
    fixtures.validActionInput,
    "action payload",
    "action-model",
  );

  assertSchemaFailure(
    sut.inputSchema,
    fixtures.invalidMissingTurn,
    "inputSchema: input.turn is required",
  );

  assertSchemaFailure(
    sut.outputSchema,
    fixtures.invalidMissingTurn,
    "outputSchema: output.turn is required",
  );

  assertSchemaFailure(
    sut.actionSchema,
    fixtures.invalidMissingTurn,
    "actionSchema: input.turn is required",
  );

  assertSchemaFailure(
    sut.actionSchema,
    fixtures.invalidActionInput,
    "actionSchema: memoryContext.actions are not allowed without memoryContext.allowedActions",
  );

  assertSchemaSuccess(
    sut.inputSchema,
    fixtures.invalidActionInput,
    "action should fail",
    "action-invalid-model",
  );

  assertSchemaSuccess(
    sut.outputSchema,
    fixtures.invalidActionInput,
    "action should fail",
    "action-invalid-model",
  );
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  contractgatespecMain();
}
