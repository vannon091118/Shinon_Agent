import { strict as assert } from "node:assert";
import { pathToFileURL } from "node:url";

import { routeBackendCall } from "../../inference/src/router/backendRouter";

type RouterSut = typeof routeBackendCall;

type RouterFixtures = Readonly<{
  primary: Readonly<{
    routeDecision: Parameters<RouterSut>[0];
    promptPayload: Parameters<RouterSut>[1];
  }>;
  messageChain: Readonly<{
    routeDecision: Parameters<RouterSut>[0];
    promptPayload: Parameters<RouterSut>[1];
  }>;
  invalidPromptPayload: Parameters<RouterSut>[1];
  invalidRouteDecision: Parameters<RouterSut>[0];
  fallback: Readonly<{
    routeDecision: Parameters<RouterSut>[0];
    promptPayload: Parameters<RouterSut>[1];
  }>;
}>;

type ClassifiedBackendError = Readonly<{
  ok: false;
  code: string;
  message: string;
  details?: Readonly<Record<string, unknown>>;
}>;

type FallbackHarness = (
  routeDecisionOrInput: Parameters<RouterSut>[0],
  promptPayload?: Parameters<RouterSut>[1],
) => Promise<Awaited<ReturnType<RouterSut>>>;

function isClassifiedBackendError(value: unknown): value is ClassifiedBackendError {
  return (
    typeof value === "object" &&
    value !== null &&
    (value as { ok?: unknown }).ok === false &&
    typeof (value as { code?: unknown }).code === "string" &&
    typeof (value as { message?: unknown }).message === "string"
  );
}

function buildFixtures(): RouterFixtures {
  return Object.freeze({
    primary: Object.freeze({
      routeDecision: Object.freeze({
        backend: "ollama",
        model: "  fallback-primary  ",
        requestId: "  fallback-req  ",
        sessionId: "  fallback-session  ",
        conversationId: "  fallback-conversation  ",
        stream: true,
      }),
      promptPayload: Object.freeze({
        prompt: "  primary route  ",
        requestId: "  prompt-req  ",
        sessionId: "  prompt-session  ",
        conversationId: "  prompt-conversation  ",
      }),
    }),
    messageChain: Object.freeze({
      routeDecision: Object.freeze({
        backend: "llamacpp",
        model: "  fallback-message  ",
        stream: false,
        allowFallback: false,
      }),
      promptPayload: Object.freeze({
        messages: [
          { role: "system", content: "  system notice  " },
          { role: "user", content: "  user prompt  " },
        ],
        requestId: "  chain-req  ",
      }),
    }),
    invalidPromptPayload: Object.freeze({
      format: "json",
    }),
    invalidRouteDecision: Object.freeze({
      backend: "unsupported-backend",
      model: "fallback-invalid",
    }),
    fallback: Object.freeze({
      routeDecision: Object.freeze({
        backend: "ollama",
        fallbackBackend: "llamacpp",
        allowFallback: true,
        model: "  fallback-target  ",
        stream: true,
        policyId: "  policy-beta  ",
        headers: Object.freeze({
          "x-trace-id": "  trace-123  ",
        }),
        options: Object.freeze({
          mode: "test",
        }),
      }),
      promptPayload: Object.freeze({
        userText: "  fallback metadata  ",
      }),
    }),
  });
}

function createFailClosedPrimary(): RouterSut {
  return (async () => {
    throw Object.freeze({
      ok: false,
      code: "BACKEND_INTERNAL_ERROR",
      message: "primary backend unavailable",
    } as ClassifiedBackendError);
  }) as RouterSut;
}

function createFallbackHarness(primary: RouterSut, fallback: RouterSut): FallbackHarness {
  return async (routeDecisionOrInput: Parameters<RouterSut>[0], promptPayload?: Parameters<RouterSut>[1]) => {
    try {
      await primary(routeDecisionOrInput, promptPayload);
      throw new Error("primary backend was expected to fail");
    } catch (error) {
      if (!isClassifiedBackendError(error)) {
        throw error;
      }

      if (error.code === "BACKEND_ROUTE_INVALID" || error.code === "BACKEND_PROMPT_INVALID") {
        throw error;
      }

      const routeDecision = Array.isArray(routeDecisionOrInput)
        ? routeDecisionOrInput[0]
        : routeDecisionOrInput;

      if (typeof routeDecision !== "object" || routeDecision === null || Array.isArray(routeDecision)) {
        throw error;
      }

      const fallbackCandidate = routeDecision as Readonly<Record<string, unknown>>;
      const fallbackBackend =
        typeof fallbackCandidate.fallbackBackend === "string" && fallbackCandidate.fallbackBackend.trim().length > 0
          ? fallbackCandidate.fallbackBackend.trim()
          : "llamacpp";

      const fallbackDecision = Object.freeze({
        ...fallbackCandidate,
        backend: fallbackBackend,
      });

      return fallback(fallbackDecision as Parameters<RouterSut>[0], promptPayload);
    }
  };
}

async function assertRouteSuccess(
  sut: RouterSut,
  routeDecision: Parameters<RouterSut>[0],
  promptPayload: Parameters<RouterSut>[1],
  expected: Readonly<{
    backend: "ollama" | "llamacpp";
    model: string;
    content: string;
    streamed: boolean;
    requestId?: string;
    sessionId?: string;
    conversationId?: string;
  }>,
): Promise<void> {
  const response = await sut(routeDecision, promptPayload);
  assert.equal(response.backend, expected.backend);
  assert.equal(response.model.startsWith(expected.model), true);
  assert.equal(response.content, expected.content);
  assert.equal(response.message.role, "assistant");
  assert.equal(response.message.content, expected.content);
  assert.equal(response.streamed, expected.streamed);
  assert.equal(response.requestId, expected.requestId);
  assert.equal(response.sessionId, expected.sessionId);
  assert.equal(response.conversationId, expected.conversationId);
  const mode = (response.raw as { mode?: string }).mode;
  assert.equal(mode === "live" || mode === "offline-evaluator", true);
  assert.equal(
    isNonEmptyString((response.raw as { evaluator?: { replayHash?: string } }).evaluator?.replayHash),
    true,
  );
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

async function assertRouteFailure(
  sut: RouterSut,
  routeDecision: Parameters<RouterSut>[0],
  promptPayload: Parameters<RouterSut>[1],
  expectedCode: string,
): Promise<void> {
  await assert.rejects(
    async () => {
      await sut(routeDecision, promptPayload);
    },
    (error: unknown) => isClassifiedBackendError(error) && error.code === expectedCode,
  );
}

export async function fallbackspecMain(
  sut: RouterSut = routeBackendCall,
  fixtures: RouterFixtures = buildFixtures(),
): Promise<void> {
  await assertRouteSuccess(
    sut,
    fixtures.primary.routeDecision,
    fixtures.primary.promptPayload,
    {
      backend: "ollama",
      model: "fallback-primary",
      content: "primary route",
      streamed: true,
      requestId: "prompt-req",
      sessionId: "prompt-session",
      conversationId: "prompt-conversation",
    },
  );

  await assertRouteSuccess(
    sut,
    fixtures.messageChain.routeDecision,
    fixtures.messageChain.promptPayload,
    {
      backend: "llamacpp",
      model: "fallback-message",
      content: "SYSTEM: system notice\nUSER: user prompt",
      streamed: false,
      requestId: "chain-req",
    },
  );

  await assertRouteFailure(
    sut,
    fixtures.primary.routeDecision,
    fixtures.invalidPromptPayload,
    "BACKEND_PROMPT_INVALID",
  );

  await assertRouteFailure(
    sut,
    fixtures.invalidRouteDecision,
    fixtures.primary.promptPayload,
    "BACKEND_ROUTE_INVALID",
  );

  const fallbackHarness = createFallbackHarness(createFailClosedPrimary(), sut);
  const fallbackResponse = await fallbackHarness(fixtures.fallback.routeDecision, fixtures.fallback.promptPayload);

  assert.equal(fallbackResponse.backend, "llamacpp");
  assert.equal(fallbackResponse.model.startsWith("fallback-target"), true);
  assert.equal(fallbackResponse.content, "fallback metadata");
  assert.equal(fallbackResponse.streamed, true);
  assert.equal(
    isNonEmptyString((fallbackResponse.raw as { evaluator?: { replayHash?: string } }).evaluator?.replayHash),
    true,
  );
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await fallbackspecMain();
}
