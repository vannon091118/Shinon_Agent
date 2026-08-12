import { strict as assert } from "node:assert";
import { pathToFileURL } from "node:url";

import { createChatRoute } from "../../backend/src/routes/chat";
import { sendChatRequest } from "../../frontend/src/lib/apiClient";

type ChatFlowSut = {
  chatRouteFactory?: typeof createChatRoute;
  sendChatRequestFn?: typeof sendChatRequest;
};

type ChatFlowFixtures = Readonly<{
  happyPath: Readonly<{
    state: Parameters<typeof sendChatRequest>[0]["state"];
    userText: string;
  }>;
  emptyMessage: Readonly<{
    state: Parameters<typeof sendChatRequest>[0]["state"];
    userText: string;
  }>;
  backendDirect: Readonly<{
    request: unknown;
  }>;
}>;

type ChatRequestResult = Awaited<ReturnType<typeof sendChatRequest>>;
type ChatRequestSuccess = Extract<ChatRequestResult, { ok: true }>;
type ChatRequestFailure = Extract<ChatRequestResult, { ok: false }>;

type InMemoryFetchResponse = {
  ok: boolean;
  status: number;
  json: () => Promise<unknown>;
  text: () => Promise<string>;
};

function buildFixtures(): ChatFlowFixtures {
  return Object.freeze({
    happyPath: Object.freeze({
      state: Object.freeze({
        sessionId: "session-flow-1",
        conversationId: "conversation-flow-1",
        requestId: "chat-flow-request-1",
        messages: Object.freeze([
          { id: "system-1", role: "system", content: "system context" },
          { id: "user-0", role: "user", content: "previous user turn" },
        ]),
        metadata: Object.freeze({
          source: "integration-test",
        }),
        endpoint: "/api/chat",
      }),
      userText: "Hello runtime",
    }),
    emptyMessage: Object.freeze({
      state: Object.freeze({
        requestId: "chat-flow-empty-1",
        endpoint: "/api/chat",
      }),
      userText: "   ",
    }),
    backendDirect: Object.freeze({
      request: Object.freeze({
        body: Object.freeze({
          message: "Direct route call",
          sessionId: "session-route-1",
          conversationId: "conversation-route-1",
          requestId: "route-request-1",
          messages: [
            { role: "system", content: "route system" },
            { role: "user", content: "Direct route call" },
          ],
        }),
      }),
    }),
  });
}

function createInMemoryFetch(
  routeFactory: typeof createChatRoute,
): (input: string, init: { body: string; [key: string]: unknown }) => Promise<InMemoryFetchResponse> {
  const chatRoute = routeFactory();

  return async (
    input: string,
    init: { body: string; method?: string; headers?: Record<string, string>; [key: string]: unknown },
  ) => {
    assert.equal(input === "/chat" || input === "/api/chat", true);

    const parsedBody = JSON.parse(init.body) as unknown;
    const response = await chatRoute.handle({ body: parsedBody });
    const status = response.ok ? 200 : response.error.code === "BAD_REQUEST" ? 400 : response.error.code === "ORCHESTRATION_FAILED" ? 502 : 500;

    return {
      ok: response.ok,
      status,
      json: async () => response,
      text: async () => JSON.stringify(response),
    };
  };
}

function assertSuccessResponse(value: unknown): asserts value is Readonly<{
  ok: true;
  status: "success";
  data: Readonly<{
    requestId: string;
    sessionId?: string;
    conversationId?: string;
    reply: string;
    message: Readonly<{
      role: "assistant";
      content: string;
    }>;
    source: "orchestrator" | "fallback";
  }>;
}> {
  assert.equal(typeof value, "object");
  assert.notEqual(value, null);
  assert.equal((value as { ok?: unknown }).ok, true);
  assert.equal((value as { status?: unknown }).status, "success");
}

function assertSendChatRequestSuccess(value: ChatRequestResult): asserts value is ChatRequestSuccess {
  assert.equal(value.ok, true);
}

function assertSendChatRequestFailure(value: ChatRequestResult): asserts value is ChatRequestFailure {
  assert.equal(value.ok, false);
}

export async function chatflowspecMain(
  sut: ChatFlowSut = {},
  fixtures: ChatFlowFixtures = buildFixtures(),
): Promise<void> {
  const chatRouteFactory = sut.chatRouteFactory ?? createChatRoute;
  const sendChatRequestFn = sut.sendChatRequestFn ?? sendChatRequest;

  const directRouteResponse = await chatRouteFactory().handle(fixtures.backendDirect.request);
  assertSuccessResponse(directRouteResponse);
  assert.equal(directRouteResponse.data.requestId, "route-request-1");
  assert.equal(directRouteResponse.data.sessionId, "session-route-1");
  assert.equal(directRouteResponse.data.conversationId, "conversation-route-1");
  assert.equal(directRouteResponse.data.reply, "Direct route call");
  assert.equal(directRouteResponse.data.message.role, "assistant");
  assert.equal(directRouteResponse.data.message.content, "Direct route call");
  assert.equal(directRouteResponse.data.source, "orchestrator");

  const fetchImpl = createInMemoryFetch(chatRouteFactory);
  const successResult = await sendChatRequestFn({
    state: fixtures.happyPath.state,
    userText: fixtures.happyPath.userText,
    fetchImpl,
    endpoint: "/api/chat",
  });

  assertSendChatRequestSuccess(successResult);
  assert.equal(successResult.requestPayload.requestId, "chat-flow-request-1");
  assert.equal(successResult.requestPayload.sessionId, "session-flow-1");
  assert.equal(successResult.requestPayload.conversationId, "conversation-flow-1");
  assert.equal(successResult.requestPayload.messages?.length, 3);
  assert.equal(successResult.requestPayload.messages?.at(-1)?.role, "user");
  assert.equal(successResult.requestPayload.messages?.at(-1)?.content, "Hello runtime");
  assert.equal(successResult.requestInit.method, "POST");
  assert.equal(successResult.requestInit.headers["content-type"], "application/json; charset=utf-8");
  assert.equal(successResult.uiEvents[0]?.type, "chat/request-prepared");
  assert.equal(successResult.uiEvents.at(-1)?.type, "chat/request-succeeded");
  assertSuccessResponse(successResult.response);
  assert.equal(successResult.response.data.reply, "Hello runtime");
  assert.equal(successResult.response.data.message.content, "Hello runtime");
  assert.equal(successResult.response.data.source, "orchestrator");

  const emptyResult = await sendChatRequestFn({
    state: fixtures.emptyMessage.state,
    userText: fixtures.emptyMessage.userText,
    fetchImpl,
    endpoint: "/api/chat",
  });

  assertSendChatRequestFailure(emptyResult);
  assert.equal(emptyResult.requestPayload.requestId, "chat-flow-empty-1");
  assert.equal(emptyResult.uiEvents.at(-1)?.type, "chat/request-failed");
  assert.equal(emptyResult.error.code, "EMPTY_MESSAGE");
  assert.equal(emptyResult.error.retryable, false);

  const memoryEntryCounts: number[] = [];
  const memoryAwareRoute = chatRouteFactory({
    orchestrateTurn: (input) => {
      const memoryEntries = Array.isArray((input.memoryContext as { entries?: unknown }).entries)
        ? ((input.memoryContext as { entries: unknown[] }).entries.length)
        : 0;
      memoryEntryCounts.push(memoryEntries);
      return {
        reply: `memory_entries=${memoryEntries}`,
        message: {
          role: "assistant",
          content: `memory_entries=${memoryEntries}`,
        },
        source: "orchestrator",
      };
    },
  });

  const firstMemoryTurn = await memoryAwareRoute.handle({
    body: {
      message: "first memory turn",
      sessionId: "memory-session-1",
      conversationId: "memory-conversation-1",
      requestId: "memory-req-1",
    },
  });
  assertSuccessResponse(firstMemoryTurn);
  assert.equal(firstMemoryTurn.data.reply, "memory_entries=0");

  const secondMemoryTurn = await memoryAwareRoute.handle({
    body: {
      message: "second memory turn",
      sessionId: "memory-session-1",
      conversationId: "memory-conversation-1",
      requestId: "memory-req-2",
    },
  });
  assertSuccessResponse(secondMemoryTurn);
  assert.equal(memoryEntryCounts[0], 0);
  assert.equal((memoryEntryCounts[1] ?? 0) >= 2, true);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await chatflowspecMain();
}
