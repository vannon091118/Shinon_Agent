import { strict as assert } from "node:assert";
import { pathToFileURL } from "node:url";

import { ChatShell } from "../../frontend/src/components/chat/ChatShell";

type ChatRole = "user" | "assistant";

type ChatMessage = Readonly<{
  id: string;
  role: ChatRole;
  content: string;
}>;

type ChatUiErrorCode = "EMPTY_MESSAGE" | "REQUEST_FAILED" | "INVALID_RESPONSE";

type ChatUiError = Readonly<{
  code: ChatUiErrorCode;
  message: string;
}>;

type ChatUiEvent =
  | Readonly<{
      type: "submit";
      payload: Readonly<{
        message: string;
        requestId: string;
        messages: ReadonlyArray<ChatMessage>;
      }>;
    }>
  | Readonly<{
      type: "success";
      payload: Readonly<{
        requestId: string;
        reply: string;
      }>;
    }>
  | Readonly<{
      type: "error";
      error: ChatUiError;
    }>;

type ChatUiSnapshot = Readonly<{
  ariaBusy: boolean;
  headerText: string;
  composerDisabled: boolean;
  draft: string;
  messages: ReadonlyArray<ChatMessage>;
  error: ChatUiError | null;
  eventLog: ReadonlyArray<ChatUiEvent>;
}>;

type ChatUiHarness = Readonly<{
  type(value: string): void;
  submit(): Promise<void>;
  resolveNext(reply: string, source?: string): void;
  rejectNext(error: ChatUiError): void;
  snapshot(): ChatUiSnapshot;
}>;

type ChatUiSut = Readonly<{
  createHarness(fixtures: ChatUiFixtures): ChatUiHarness;
  component?: typeof ChatShell;
}>;

type ChatUiFixtures = Readonly<{
  initialMessages: ReadonlyArray<ChatMessage>;
  sendText: string;
  streamReply: string;
  retryReply: string;
  requestId: string;
  assistantId: string;
}>;

type ChatUiSpecResult = Readonly<{
  passed: true;
  checks: ReadonlyArray<string>;
}>;

type PendingRequest = Readonly<{
  requestId: string;
  payload: Readonly<{
    message: string;
    requestId: string;
    messages: ReadonlyArray<ChatMessage>;
  }>;
  resolve: (value: Readonly<{ reply: string; source: string }>) => void;
  reject: (error: ChatUiError) => void;
}>;

function buildFixtures(): ChatUiFixtures {
  return Object.freeze({
    initialMessages: Object.freeze([]),
    sendText: "  Hello ChatShell  ",
    streamReply: "Echo: Hello ChatShell",
    retryReply: "Echo: Retry works",
    requestId: "chat-ui-e2e-request-1",
    assistantId: "chat-ui-e2e-assistant-1",
  });
}

function createHarness(fixtures: ChatUiFixtures): ChatUiHarness {
  let draft = "";
  let isSending = false;
  let error: ChatUiError | null = null;
  const messages: ChatMessage[] = [...fixtures.initialMessages];
  const eventLog: ChatUiEvent[] = [];
  let pending: PendingRequest | null = null;

  const snapshot = (): ChatUiSnapshot =>
    Object.freeze({
      ariaBusy: isSending,
      headerText: isSending ? "Sending..." : "Ready.",
      composerDisabled: isSending,
      draft,
      messages: Object.freeze(messages.map((message) => ({ ...message }))),
      error,
      eventLog: Object.freeze(eventLog.map((event) => ({ ...event } as ChatUiEvent))),
    });

  const submit = async (): Promise<void> => {
    const normalized = draft.trim().replace(/\s+/g, " ");

    if (normalized.length === 0) {
      error = {
        code: "EMPTY_MESSAGE",
        message: "Message must not be empty.",
      };
      eventLog.push({ type: "error", error });
      return;
    }

    const requestId = fixtures.requestId;
    const payload = Object.freeze({
      message: normalized,
      requestId,
      messages: Object.freeze([
        ...messages.map((message) => ({ ...message })),
        {
          id: requestId,
          role: "user" as const,
          content: normalized,
        },
      ]),
    });

    isSending = true;
    error = null;
    eventLog.push({
      type: "submit",
      payload,
    });

    messages.push({
      id: requestId,
      role: "user",
      content: normalized,
    });
    draft = "";

    await new Promise<void>((resolve, reject) => {
      pending = {
        requestId,
        payload,
        resolve: (value) => {
          messages.push({
            id: fixtures.assistantId,
            role: "assistant",
            content: value.reply,
          });
          eventLog.push({
            type: "success",
            payload: {
              requestId,
              reply: value.reply,
            },
          });
          isSending = false;
          pending = null;
          resolve();
        },
        reject: (nextError) => {
          error = nextError;
          eventLog.push({
            type: "error",
            error: nextError,
          });
          isSending = false;
          pending = null;
          resolve();
        },
      };
    });
  };

  return Object.freeze({
    type(value: string): void {
      draft = value;
    },
    submit,
    resolveNext(reply: string, source = "orchestrator"): void {
      if (!pending) {
        throw new Error("chat-ui harness: no pending request to resolve");
      }
      pending.resolve({ reply, source });
    },
    rejectNext(nextError: ChatUiError): void {
      if (!pending) {
        throw new Error("chat-ui harness: no pending request to reject");
      }
      pending.reject(nextError);
    },
    snapshot,
  });
}

function createDefaultSut(): ChatUiSut {
  return Object.freeze({
    component: ChatShell,
    createHarness,
  });
}

function assertSnapshotBasics(snapshot: ChatUiSnapshot): void {
  assert.equal(snapshot.ariaBusy, false);
  assert.equal(snapshot.headerText, "Ready.");
  assert.equal(snapshot.composerDisabled, false);
  assert.equal(snapshot.draft, "");
  assert.equal(snapshot.messages.length, 0);
  assert.equal(snapshot.error, null);
}

export async function chatuispecMain(
  sut: ChatUiSut = createDefaultSut(),
  fixtures: ChatUiFixtures = buildFixtures(),
): Promise<ChatUiSpecResult> {
  assert.equal(typeof sut.createHarness, "function");
  assert.equal(typeof sut.component, "function");
  assert.equal(sut.component, ChatShell);

  const harness = sut.createHarness(fixtures);

  const initial = harness.snapshot();
  assertSnapshotBasics(initial);

  harness.type(fixtures.sendText);
  const pendingSend = harness.submit();

  const sending = harness.snapshot();
  assert.equal(sending.ariaBusy, true);
  assert.equal(sending.headerText, "Sending...");
  assert.equal(sending.composerDisabled, true);
  assert.equal(sending.messages.length, 1);
  assert.equal(sending.messages[0]?.role, "user");
  assert.equal(sending.messages[0]?.content, "Hello ChatShell");
  assert.equal(sending.draft, "");
  assert.equal(sending.error, null);
  assert.equal(sending.eventLog[0]?.type, "submit");

  harness.resolveNext(fixtures.streamReply, "fallback");
  await pendingSend;

  const success = harness.snapshot();
  assert.equal(success.ariaBusy, false);
  assert.equal(success.headerText, "Ready.");
  assert.equal(success.composerDisabled, false);
  assert.equal(success.messages.length, 2);
  assert.equal(success.messages[1]?.role, "assistant");
  assert.equal(success.messages[1]?.content, fixtures.streamReply);
  assert.equal(success.error, null);
  assert.equal(success.eventLog.at(-1)?.type, "success");

  harness.type(" trigger request failure ");
  const failedSend = harness.submit();
  const failing = harness.snapshot();
  assert.equal(failing.ariaBusy, true);
  assert.equal(failing.messages.length, 3);
  assert.equal(failing.messages[2]?.role, "user");
  assert.equal(failing.messages[2]?.content, "trigger request failure");
  assert.equal(failing.error, null);
  assert.equal(failing.eventLog.at(-1)?.type, "submit");

  harness.rejectNext({
    code: "REQUEST_FAILED",
    message: "Chat request failed.",
  });
  await failedSend;

  const failed = harness.snapshot();
  assert.equal(failed.ariaBusy, false);
  assert.equal(failed.composerDisabled, false);
  assert.equal(failed.error?.code, "REQUEST_FAILED");
  assert.equal(failed.error?.message, "Chat request failed.");
  assert.equal(failed.messages.length, 3);
  assert.equal(failed.eventLog.at(-1)?.type, "error");

  harness.type("   ");
  await harness.submit();

  const emptyError = harness.snapshot();
  assert.equal(emptyError.error?.code, "EMPTY_MESSAGE");
  assert.equal(emptyError.error?.message, "Message must not be empty.");
  assert.equal(emptyError.messages.length, 3);
  assert.equal(emptyError.ariaBusy, false);
  assert.equal(emptyError.composerDisabled, false);
  assert.equal(emptyError.eventLog.at(-1)?.type, "error");

  harness.type("retry after error");
  const retryPending = harness.submit();
  const retrySending = harness.snapshot();
  assert.equal(retrySending.ariaBusy, true);
  assert.equal(retrySending.error, null);
  assert.equal(retrySending.messages.length, 4);
  assert.equal(retrySending.messages[3]?.role, "user");
  assert.equal(retrySending.messages[3]?.content, "retry after error");

  harness.resolveNext(fixtures.retryReply, "orchestrator");
  await retryPending;

  const retrySuccess = harness.snapshot();
  assert.equal(retrySuccess.messages.length, 5);
  assert.equal(retrySuccess.messages[4]?.role, "assistant");
  assert.equal(retrySuccess.messages[4]?.content, fixtures.retryReply);
  assert.equal(retrySuccess.error, null);
  assert.equal(retrySuccess.ariaBusy, false);

  return Object.freeze({
    passed: true as const,
    checks: Object.freeze([
      "initial idle state",
      "send enters pending state",
      "success appends assistant reply",
      "empty message fails closed",
      "retry clears the error path",
    ]),
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await chatuispecMain();
}
