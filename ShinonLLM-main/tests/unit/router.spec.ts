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
  fallbackMetadata: Readonly<{
    routeDecision: Parameters<RouterSut>[0];
    promptPayload: Parameters<RouterSut>[1];
  }>;
}>;

function isClassifiedBackendError(value: unknown): value is Readonly<{
  ok: false;
  code: string;
  message: string;
  details?: Readonly<Record<string, unknown>>;
}> {
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
        model: "  router-primary  ",
        requestId: "  route-req  ",
        sessionId: "  route-session  ",
        conversationId: "  route-conversation  ",
        stream: true,
        timeoutMs: 12.8,
      }),
      promptPayload: Object.freeze({
        prompt: "  hello world  ",
        requestId: "  prompt-req  ",
        sessionId: "  prompt-session  ",
        conversationId: "  prompt-conversation  ",
      }),
    }),
    messageChain: Object.freeze({
      routeDecision: Object.freeze({
        backend: "llamacpp",
        model: "  router-message  ",
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
      model: "router-invalid",
    }),
    fallbackMetadata: Object.freeze({
      routeDecision: Object.freeze({
        backend: "llamacpp",
        fallbackBackend: "ollama",
        allowFallback: true,
        model: "  router-fallback  ",
        stream: true,
        policyId: "  policy-alpha  ",
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

export async function routerspecMain(
  sut: RouterSut = routeBackendCall,
  fixtures: RouterFixtures = buildFixtures(),
): Promise<void> {
  await assertRouteSuccess(
    sut,
    fixtures.primary.routeDecision,
    fixtures.primary.promptPayload,
    {
      backend: "ollama",
      model: "router-primary",
      content: "hello world",
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
      model: "router-message",
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

  const fallbackResponse = await sut(fixtures.fallbackMetadata.routeDecision, fixtures.fallbackMetadata.promptPayload);
  assert.equal(fallbackResponse.backend, "llamacpp");
  assert.equal(fallbackResponse.model.startsWith("router-fallback"), true);
  assert.equal(fallbackResponse.content, "fallback metadata");
  assert.equal(fallbackResponse.streamed, true);
  assert.equal(
    isNonEmptyString((fallbackResponse.raw as { evaluator?: { replayHash?: string } }).evaluator?.replayHash),
    true,
  );
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  void routerspecMain().catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  });
}
