import { strict as assert } from "node:assert";
import { pathToFileURL } from "node:url";

import { orchestrateTurn } from "../../orchestrator/src/pipeline/orchestrateTurn";

type OrchestratorSut = typeof orchestrateTurn;

type OrchestratorFixtures = Readonly<{
  routedByHint: Readonly<{
    input: Parameters<OrchestratorSut>[0];
    expected: Readonly<{
      reply: string;
      model: string;
      prompt: string;
    }>;
  }>;
  routedByDefault: Readonly<{
    input: Parameters<OrchestratorSut>[0];
    expected: Readonly<{
      reply: string;
      model: string;
      prompt: string;
    }>;
  }>;
  invalidHistoryRole: Parameters<OrchestratorSut>[0];
  circularMemoryContext: Parameters<OrchestratorSut>[0];
}>;

type ClassifiedOrchestratorError = Readonly<{
  code: "BAD_REQUEST" | "ORCHESTRATION_FAILED" | "INTERNAL_SERVER_ERROR";
  message: string;
}>;

function isClassifiedOrchestratorError(value: unknown): value is ClassifiedOrchestratorError {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as { code?: unknown }).code === "string" &&
    typeof (value as { message?: unknown }).message === "string"
  );
}

function buildFixtures(): OrchestratorFixtures {
  return Object.freeze({
    routedByHint: Object.freeze({
      input: Object.freeze({
        request: Object.freeze({
          sessionId: "session-1",
          conversationId: "conversation-1",
          requestId: "request-1",
        }),
        userText: "  Hello runtime  ",
        history: Object.freeze([
          Object.freeze({ role: "system", content: "  system context  " }),
          Object.freeze({ role: "user", content: "  prior question  " }),
          Object.freeze({ role: "assistant", content: "  previous answer  " }),
        ]),
        memoryContext: Object.freeze({
          modelHint: "custom-model",
          alpha: "zed",
          beta: 2,
          nested: Object.freeze({ b: 2, a: 1 }),
        }),
      }),
      expected: Object.freeze({
        reply: "Hello runtime",
        model: "custom-model",
        prompt: [
          "SYSTEM: Produce a concise, valid assistant response.",
          "PLAN: intent=question next_action=answer",
          "USER: Hello runtime",
          "SYSTEM: system context",
          "USER: prior question",
          "ASSISTANT: previous answer",
          'MEMORY: alpha="zed" | beta=2 | modelHint="custom-model" | nested={"a":1,"b":2}',
        ].join("\n"),
      }),
    }),
    routedByDefault: Object.freeze({
      input: Object.freeze({
        userText: "  Plain request  ",
        history: Object.freeze([]),
        memoryContext: Object.freeze({}),
      }),
      expected: Object.freeze({
        reply: "Plain request",
        model: "orchestrator-default",
        prompt: [
          "SYSTEM: Produce a concise, valid assistant response.",
          "PLAN: intent=question next_action=answer",
          "USER: Plain request",
          "HISTORY: <empty>",
          "MEMORY: <empty>",
        ].join("\n"),
      }),
    }),
    invalidHistoryRole: Object.freeze({
      userText: "bad turn",
      history: Object.freeze([
        Object.freeze({ role: "tool", content: "invalid" }),
      ]),
      memoryContext: Object.freeze({}),
    }),
    circularMemoryContext: Object.freeze({
      userText: "circular",
      history: Object.freeze([]),
      memoryContext: (() => {
        const memoryContext: Record<string, unknown> = { modelHint: "custom-model" };
        memoryContext.self = memoryContext;
        return memoryContext;
      })(),
    }),
  });
}

async function assertOrchestrateSuccess(
  sut: OrchestratorSut,
  input: Parameters<OrchestratorSut>[0],
  expected: Readonly<{
    reply: string;
    model: string;
    prompt: string;
  }>,
): Promise<void> {
  const output = await sut(input);
  assert.ok(typeof output.reply === "string" && output.reply.length > 0, "reply must be a non-empty string");
  assert.equal(output.message.role, "assistant");
  assert.equal(output.message.content.length > 0, true);
  assert.equal(output.source, "orchestrator");
  assert.ok(typeof output.model === "string", "model must be a string");
  assert.ok(typeof output.prompt === "string", "prompt must be a string");
  assert.equal(output.guardrailStatus, "validated");
}

async function assertOrchestrateFailure(
  sut: OrchestratorSut,
  input: Parameters<OrchestratorSut>[0],
  expectedCode: ClassifiedOrchestratorError["code"],
  expectedMessageFragment: string,
): Promise<void> {
  await assert.rejects(
    async () => {
      await sut(input);
    },
    (error: unknown) =>
      isClassifiedOrchestratorError(error) &&
      error.code === expectedCode &&
      error.message.includes(expectedMessageFragment),
  );
}

export async function orchestratorspecMain(
  sut: OrchestratorSut = orchestrateTurn,
  fixtures: OrchestratorFixtures = buildFixtures(),
): Promise<void> {
  await assertOrchestrateSuccess(sut, fixtures.routedByHint.input, fixtures.routedByHint.expected);
  await assertOrchestrateSuccess(sut, fixtures.routedByDefault.input, fixtures.routedByDefault.expected);

  await assertOrchestrateFailure(
    sut,
    fixtures.invalidHistoryRole,
    "BAD_REQUEST",
    "history entry role is invalid",
  );

  await assertOrchestrateFailure(
    sut,
    fixtures.circularMemoryContext,
    "BAD_REQUEST",
    "memoryContext contains a circular reference",
  );
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  void orchestratorspecMain().catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });
}
