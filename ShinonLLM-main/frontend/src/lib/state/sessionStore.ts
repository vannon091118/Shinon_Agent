import type { UiErrorState, UiMessage } from "../types";

type ChatRole = UiMessage["role"];

type SessionMessage = UiMessage;

type SessionMetadata = Record<string, string | number | boolean | null>;

type SessionRequestMessage = {
  role: ChatRole;
  content: string;
  id?: string;
};

type SessionRequestPayload = {
  message: string;
  text: string;
  prompt: string;
  input: string;
  content: string;
  sessionId?: string;
  conversationId?: string;
  requestId: string;
  messages: SessionRequestMessage[];
  metadata?: SessionMetadata;
};

type SessionRequestInit = {
  method: "POST";
  headers: Record<string, string>;
  body: string;
};

type SessionUiEvent =
  | {
      type: "session/request-prepared";
      requestId: string;
      payload: SessionRequestPayload;
    }
  | {
      type: "session/message-appended";
      requestId: string;
      message: SessionMessage;
    }
  | {
      type: "session/request-failed";
      requestId: string;
      error: UiErrorState;
    };

type SessionStoreInput = {
  sessionId?: string;
  conversationId?: string;
  requestId?: string;
  draftText?: string;
  isSending?: boolean;
  messages?: ReadonlyArray<SessionMessage>;
  metadata?: SessionMetadata;
  endpoint?: string;
  timeoutMs?: number;
  retries?: number;
  retryDelayMs?: number;
  headers?: Record<string, string>;
  error?: UiErrorState | null;
  lastSubmittedText?: string;
};

type SessionStoreState = Required<
  Pick<
    SessionStoreInput,
    "draftText" | "isSending" | "endpoint" | "timeoutMs" | "retries" | "retryDelayMs"
  >
> &
  Omit<SessionStoreInput, "draftText" | "isSending" | "endpoint" | "timeoutMs" | "retries" | "retryDelayMs"> & {
    messages: ReadonlyArray<SessionMessage>;
    headers: Record<string, string>;
    metadata?: SessionMetadata;
    error: UiErrorState | null;
  };

type SessionActionResult = {
  ok: boolean;
  state: SessionStoreState;
  requestPayload: SessionRequestPayload | null;
  requestInit: SessionRequestInit | null;
  uiEvents: ReadonlyArray<SessionUiEvent>;
  error: UiErrorState | null;
};

type SessionAssistantReplyInput = {
  requestId: string;
  reply: string;
  source?: "orchestrator" | "fallback";
};

type SessionStore = {
  getState: () => SessionStoreState;
  reset: (nextState?: SessionStoreInput) => SessionStoreState;
  update: (patch: SessionStoreInput) => SessionStoreState;
  preview: (userText: string) => SessionActionResult;
  submit: (userText: string) => SessionActionResult;
  commitAssistantReply: (input: SessionAssistantReplyInput) => SessionActionResult;
  setDraftText: (draftText: string) => SessionStoreState;
  setError: (error: UiErrorState | null) => SessionStoreState;
  setSending: (isSending: boolean) => SessionStoreState;
};

const DEFAULT_ENDPOINT = "/api/chat";
const DEFAULT_TIMEOUT_MS = 10_000;
const DEFAULT_RETRIES = 0;
const DEFAULT_RETRY_DELAY_MS = 0;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeText(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

function toNonEmptyString(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const trimmed = normalizeText(value);
  return trimmed.length > 0 ? trimmed : null;
}

function toPositiveInteger(value: unknown, fallback: number): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return fallback;
  }

  const normalized = Math.floor(value);
  return normalized >= 0 ? normalized : fallback;
}

function stableHash(seed: string): string {
  let hash = 2166136261;

  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  return `session_${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

function normalizeHeaders(headers?: Record<string, string>): Record<string, string> {
  if (!isRecord(headers)) {
    return {};
  }

  const normalized: Record<string, string> = {};
  for (const [key, value] of Object.entries(headers)) {
    const normalizedKey = toNonEmptyString(key);
    const normalizedValue = toNonEmptyString(value);
    if (normalizedKey && normalizedValue) {
      normalized[normalizedKey] = normalizedValue;
    }
  }

  return normalized;
}

function normalizeMetadata(metadata?: SessionMetadata): SessionMetadata | undefined {
  if (!isRecord(metadata)) {
    return undefined;
  }

  const normalized: SessionMetadata = {};
  for (const [key, value] of Object.entries(metadata)) {
    const normalizedKey = toNonEmptyString(key);
    if (!normalizedKey) {
      continue;
    }

    if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean" ||
      value === null
    ) {
      normalized[normalizedKey] = value;
    }
  }

  return Object.keys(normalized).length > 0 ? normalized : undefined;
}

function normalizeMessage(message: SessionMessage): SessionMessage | null {
  const content = toNonEmptyString(message.content);
  if (!content) {
    return null;
  }

  const role: ChatRole =
    message.role === "system" || message.role === "assistant" ? message.role : "user";

  const normalized: SessionMessage = {
    id: toNonEmptyString(message.id) ?? stableHash([role, content].join("|")),
    role,
    content,
  };

  if (
    message.status === "idle" ||
    message.status === "sending" ||
    message.status === "streaming" ||
    message.status === "sent" ||
    message.status === "error"
  ) {
    normalized.status = message.status;
  }

  if (typeof message.timestamp === "string" && message.timestamp.trim().length > 0) {
    normalized.timestamp = message.timestamp.trim();
  }

  return normalized;
}

function normalizeMessages(messages?: ReadonlyArray<SessionMessage>): ReadonlyArray<SessionMessage> {
  if (!messages || messages.length === 0) {
    return [];
  }

  const normalized: SessionMessage[] = [];
  for (const message of messages) {
    const item = normalizeMessage(message);
    if (item) {
      normalized.push(item);
    }
  }

  return normalized;
}

function normalizeState(input: SessionStoreInput = {}): SessionStoreState {
  return {
    sessionId: toNonEmptyString(input.sessionId) ?? undefined,
    conversationId: toNonEmptyString(input.conversationId) ?? undefined,
    requestId: toNonEmptyString(input.requestId) ?? undefined,
    draftText: normalizeText(input.draftText ?? ""),
    isSending: input.isSending === true,
    messages: normalizeMessages(input.messages),
    metadata: normalizeMetadata(input.metadata),
    endpoint: toNonEmptyString(input.endpoint) ?? DEFAULT_ENDPOINT,
    timeoutMs: toPositiveInteger(input.timeoutMs, DEFAULT_TIMEOUT_MS),
    retries: toPositiveInteger(input.retries, DEFAULT_RETRIES),
    retryDelayMs: toPositiveInteger(input.retryDelayMs, DEFAULT_RETRY_DELAY_MS),
    headers: normalizeHeaders(input.headers),
    error: input.error ?? null,
    lastSubmittedText: toNonEmptyString(input.lastSubmittedText) ?? undefined,
  };
}

function cloneState(state: SessionStoreState): SessionStoreState {
  return {
    ...state,
    messages: state.messages.map((message) => ({ ...message })),
    headers: { ...state.headers },
    metadata: state.metadata ? { ...state.metadata } : undefined,
  };
}

function buildUiErrorState(
  code: UiErrorState["code"],
  message: string,
  requestId?: string
): UiErrorState {
  return {
    code,
    message: normalizeText(message),
    requestId: toNonEmptyString(requestId) ?? undefined,
  };
}

function deriveRequestId(state: SessionStoreState, userText: string): string {
  if (state.isSending && state.requestId) {
    return state.requestId;
  }

  return stableHash(
    [
      state.sessionId ?? "",
      state.conversationId ?? "",
      userText,
      String(state.messages.length),
      state.lastSubmittedText ?? "",
    ].join("|")
  );
}

function buildRequestPayload(
  state: SessionStoreState,
  userText: string,
  requestId: string
): SessionRequestPayload {
  const payloadMessages = [
    ...state.messages.map((message) => ({
      role: message.role,
      content: message.content,
      id: message.id,
    })),
    {
      role: "user" as const,
      content: userText,
      id: requestId,
    },
  ];

  return {
    message: userText,
    text: userText,
    prompt: userText,
    input: userText,
    content: userText,
    sessionId: state.sessionId,
    conversationId: state.conversationId,
    requestId,
    messages: payloadMessages,
    metadata: state.metadata,
  };
}

function buildRequestInit(
  payload: SessionRequestPayload,
  headers: Record<string, string>
): SessionRequestInit {
  return {
    method: "POST",
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...headers,
    },
    body: JSON.stringify(payload),
  };
}

function createResult(
  state: SessionStoreState,
  requestPayload: SessionRequestPayload | null,
  requestInit: SessionRequestInit | null,
  uiEvents: ReadonlyArray<SessionUiEvent>,
  error: UiErrorState | null,
  ok: boolean
): SessionActionResult {
  return {
    ok,
    state: cloneState(state),
    requestPayload,
    requestInit,
    uiEvents,
    error,
  };
}

function planSubmission(state: SessionStoreState, userText: string): SessionActionResult {
  const normalizedText = normalizeText(userText);
  const requestId = deriveRequestId(state, normalizedText);
  const uiEvents: SessionUiEvent[] = [];

  if (!normalizedText) {
    const error = buildUiErrorState("EMPTY_MESSAGE", "Session message must not be empty.", requestId);
    const nextState: SessionStoreState = {
      ...state,
      error,
    };
    uiEvents.push({
      type: "session/request-failed",
      requestId,
      error,
    });
    return createResult(nextState, null, null, uiEvents, error, false);
  }

  if (state.isSending) {
    const error = buildUiErrorState(
      "DUPLICATE_SEND",
      "A session request is already in flight.",
      requestId
    );
    const nextState: SessionStoreState = {
      ...state,
      error,
    };
    uiEvents.push({
      type: "session/request-failed",
      requestId,
      error,
    });
    return createResult(nextState, null, null, uiEvents, error, false);
  }

  if (state.lastSubmittedText && state.lastSubmittedText === normalizedText) {
    const error = buildUiErrorState(
      "DUPLICATE_SEND",
      "Duplicate session submission blocked.",
      requestId
    );
    const nextState: SessionStoreState = {
      ...state,
      error,
    };
    uiEvents.push({
      type: "session/request-failed",
      requestId,
      error,
    });
    return createResult(nextState, null, null, uiEvents, error, false);
  }

  const payload = buildRequestPayload(state, normalizedText, requestId);
  const requestInit = buildRequestInit(payload, state.headers);
  const userMessage: SessionMessage = {
    id: requestId,
    role: "user",
    content: normalizedText,
    status: "sending",
  };
  const nextState: SessionStoreState = {
    ...state,
    requestId,
    draftText: "",
    isSending: true,
    messages: [...state.messages, userMessage],
    error: null,
    lastSubmittedText: normalizedText,
  };

  uiEvents.push({
    type: "session/request-prepared",
    requestId,
    payload,
  });
  uiEvents.push({
    type: "session/message-appended",
    requestId,
    message: userMessage,
  });

  return createResult(nextState, payload, requestInit, uiEvents, null, true);
}

function planAssistantReply(
  state: SessionStoreState,
  input: SessionAssistantReplyInput
): SessionActionResult {
  const requestId = toNonEmptyString(input.requestId) ?? deriveRequestId(state, "");
  const reply = normalizeText(input.reply);

  if (!reply) {
    const error = buildUiErrorState("INVALID_RESPONSE", "Assistant reply must not be empty.", requestId);
    const nextState: SessionStoreState = {
      ...state,
      error,
    };
    return createResult(nextState, null, null, [], error, false);
  }

  if (!state.requestId || state.requestId !== requestId) {
    const error = buildUiErrorState(
      "INVALID_STATE",
      "Assistant reply does not match the active session request.",
      requestId
    );
    const nextState: SessionStoreState = {
      ...state,
      error,
    };
    return createResult(nextState, null, null, [], error, false);
  }

  const assistantMessage: SessionMessage = {
    id: stableHash([requestId, reply, String(state.messages.length)].join("|")),
    role: "assistant",
    content: reply,
    status: "sent",
  };

  const updatedMessages = state.messages.map((message) =>
    message.id === requestId && message.role === "user"
      ? { ...message, status: "sent" as const }
      : { ...message }
  );

  const nextState: SessionStoreState = {
    ...state,
    messages: [...updatedMessages, assistantMessage],
    isSending: false,
    error: null,
  };

  return createResult(
    nextState,
    null,
    null,
    [
      {
        type: "session/message-appended",
        requestId,
        message: assistantMessage,
      },
    ],
    null,
    true
  );
}

export function createSessionStore(initialState: SessionStoreInput = {}): SessionStore {
  let state = normalizeState(initialState);

  return {
    getState: () => cloneState(state),
    reset: (nextState: SessionStoreInput = {}) => {
      state = normalizeState(nextState);
      return cloneState(state);
    },
    update: (patch: SessionStoreInput) => {
      state = normalizeState({
        ...state,
        ...patch,
      });
      return cloneState(state);
    },
    preview: (userText: string) => planSubmission(state, userText),
    submit: (userText: string) => {
      const result = planSubmission(state, userText);
      state = result.state;
      return result;
    },
    commitAssistantReply: (input: SessionAssistantReplyInput) => {
      const result = planAssistantReply(state, input);
      state = result.state;
      return result;
    },
    setDraftText: (draftText: string) => {
      state = {
        ...state,
        draftText: normalizeText(draftText),
      };
      return cloneState(state);
    },
    setError: (error: UiErrorState | null) => {
      state = {
        ...state,
        error,
      };
      return cloneState(state);
    },
    setSending: (isSending: boolean) => {
      state = {
        ...state,
        isSending: isSending === true,
      };
      return cloneState(state);
    },
  };
}
