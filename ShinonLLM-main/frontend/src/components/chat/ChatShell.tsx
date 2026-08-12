"use client";

import { useCallback, useMemo, useState, useEffect, useRef } from "react";
import { Orb, OrbMood } from "./Orb";
import { ModelSelector, DevDebugPanel, DevProcessingPanel } from "../dev";
import type { ModelInfo } from "../dev/ModelSelector";
import "./ChatShell.css";

type ChatRole = "user" | "assistant";
type ChatModel = "runtime-default" | "llamacpp-qwen-0_5b" | "ollama-default" | string;

type ModelOption = {
  readonly value: string;
  readonly label: string;
  readonly isLocal?: boolean;
};

type ChatMessage = Readonly<{
  id: string;
  role: ChatRole;
  content: string;
}>;

type ChatUIErrorCode =
  | "EMPTY_MESSAGE"
  | "DUPLICATE_SEND"
  | "REQUEST_FAILED"
  | "INVALID_RESPONSE";

type ChatUIError = Readonly<{
  code: ChatUIErrorCode;
  message: string;
}>;

type ChatRequestPayload = Readonly<{
  message: string;
  sessionId?: string;
  conversationId?: string;
  requestId: string;
  messages: Array<{
    role: ChatRole;
    content: string;
    id: string;
  }>;
  metadata: Readonly<{
    source: "ChatShell";
    messageCount: number;
    model: ChatModel;
  }>;
}>;

type ChatResponsePayload = Readonly<{
  requestId: string;
  reply: string;
  source: string;
}>;

type ChatShellEvent =
  | Readonly<{
      type: "submit";
      payload: ChatRequestPayload;
    }>
  | Readonly<{
      type: "success";
      payload: ChatResponsePayload;
    }>
  | Readonly<{
      type: "error";
      error: ChatUIError;
    }>;

type ChatShellProps = Readonly<{
  sessionId?: string;
  conversationId?: string;
  initialMessages?: ReadonlyArray<ChatMessage>;
  apiBasePath?: string;
  onEvent?: (event: ChatShellEvent) => void;
}>;

type LogEntry = Readonly<{
  timestamp: string;
  type: "info" | "error" | "success" | "request" | "response";
  message: string;
}>;

type StoredData = Readonly<{
  sessionId: string;
  conversationId: string;
  messageCount: number;
  lastUpdated: string;
}>;

function createStableId(seed: string): string {
  let hash = 2166136261;

  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  return `chat_${(hash >>> 0).toString(16).padStart(8, "0")}`;
}

function normalizeText(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

function buildRequestPayload(
  messages: ReadonlyArray<ChatMessage>,
  userText: string,
  model: ChatModel,
  sessionId?: string,
  conversationId?: string
): ChatRequestPayload {
  const normalizedText = normalizeText(userText);
  const requestId = createStableId(
    [
      sessionId ?? "",
      conversationId ?? "",
      normalizedText,
      model,
      String(messages.length),
    ].join("|")
  );

  return {
    message: normalizedText,
    sessionId,
    conversationId,
    requestId,
    messages: [
      ...messages.map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content,
      })),
      {
        id: requestId,
        role: "user",
        content: normalizedText,
      },
    ],
    metadata: {
      source: "ChatShell",
      messageCount: messages.length + 1,
      model,
    },
  };
}

async function sendChatRequest(
  payload: ChatRequestPayload,
  apiBasePath: string,
  timeoutMs = 15_000
): Promise<ChatResponsePayload> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(apiBasePath, {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error(`Chat request timed out after ${timeoutMs}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }

  const data: unknown = await response.json().catch(() => null);

  if (!response.ok || typeof data !== "object" || data === null) {
    throw new Error("Chat request failed");
  }

  const candidate = data as {
    ok?: boolean;
    data?: {
      requestId?: unknown;
      reply?: unknown;
      source?: unknown;
    };
    error?: {
      message?: unknown;
    };
  };

  if (candidate.ok !== true || typeof candidate.data !== "object" || candidate.data === null) {
    throw new Error(
      typeof candidate.error?.message === "string" && candidate.error.message.trim().length > 0
        ? candidate.error.message.trim()
        : "Chat response was invalid"
    );
  }

  if (
    typeof candidate.data.requestId !== "string" ||
    typeof candidate.data.reply !== "string" ||
    candidate.data.reply.trim().length === 0
  ) {
    throw new Error("Chat response was invalid");
  }

  return {
    requestId: candidate.data.requestId,
    reply: candidate.data.reply.trim(),
    source: typeof candidate.data.source === "string" ? candidate.data.source : "unknown",
  };
}

function MessageList({ messages }: { messages: ReadonlyArray<ChatMessage> }) {
  return (
    <ul aria-label="Chat history" className="chat-shell__messages">
      {messages.length === 0 ? (
        <li className="chat-shell__empty">No messages yet.</li>
      ) : (
        messages.map((message) => (
          <li
            key={message.id}
            className={`chat-shell__message chat-shell__message--${message.role}`}
            data-role={message.role}
          >
            <span className="chat-shell__message-role">{message.role}</span>
            <span className="chat-shell__message-content">{message.content}</span>
          </li>
        ))
      )}
    </ul>
  );
}

function Composer(props: {
  model: ChatModel;
  onModelChange: (value: ChatModel) => void;
  availableModels?: ReadonlyArray<ModelInfo>;
  value: string;
  disableInput: boolean;
  disableSubmit: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}) {
  // Build options from available models + defaults
  const options: ModelOption[] = [
    { value: "runtime-default", label: "Runtime Default" },
    ...props.availableModels?.map(m => ({ 
      value: `llamacpp-${m.id}`, 
      label: `${m.name} (${m.sizeFormatted})`,
      isLocal: true 
    })) || [],
    { value: "ollama-default", label: "Ollama Default" },
  ];

  return (
    <form
      className="chat-shell__composer"
      onSubmit={(event) => {
        event.preventDefault();
        props.onSubmit();
      }}
    >
      <label className="chat-shell__model">
        <span>Model</span>
        <select
          aria-label="Model"
          disabled={props.disableInput}
          onChange={(event) => props.onModelChange(event.currentTarget.value as ChatModel)}
          value={props.model}
        >
          {options.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </label>
      <textarea
        aria-label="Message"
        disabled={props.disableInput}
        value={props.value}
        onChange={(event) => props.onChange(event.currentTarget.value)}
        placeholder="Type a message"
        rows={4}
      />
      <button disabled={props.disableSubmit} type="submit">
        Send
      </button>
    </form>
  );
}

/**
 * Render a chat UI that manages composing, sending, and displaying messages with model selection and simple mood-driven UI.
 *
 * The component maintains local chat state (messages, draft, model, sending state, error, and an Orb mood derived from the draft),
 * validates and submits user messages to the configured chat API, appends user and assistant messages to the history,
 * and reports lifecycle events via `onEvent`.
 *
 * @param sessionId - Optional session identifier to include in request payloads
 * @param conversationId - Optional conversation identifier to include in request payloads
 * @param initialMessages - Initial list of chat messages to populate the history
 * @param apiBasePath - Base path for the chat API endpoint (default: "/api/chat")
 * @param onEvent - Optional callback invoked with `"submit"`, `"success"`, and `"error"` events describing request lifecycle
 * @returns A React element rendering the chat shell UI
 */
export function ChatShell({
  sessionId,
  conversationId,
  initialMessages = [],
  apiBasePath = "/api/chat",
  onEvent,
}: ChatShellProps) {
  const [messages, setMessages] = useState<ReadonlyArray<ChatMessage>>(initialMessages);
  const [draft, setDraft] = useState("");
  const [model, setModel] = useState<ChatModel>("runtime-default");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<ChatUIError | null>(null);
  const [currentMood, setCurrentMood] = useState<OrbMood>("neutral");
  
  // DEV: Selected model from %APPDATA%
  const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(null);
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [showModelSelector, setShowModelSelector] = useState(true);
  
  // Debug state
  const [logs, setLogs] = useState<ReadonlyArray<LogEntry>>([]);
  const [showDebug, setShowDebug] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Logging helper with DEV integration
  const addLog = useCallback((type: LogEntry["type"], message: string) => {
    setLogs((prev) => [
      ...prev,
      Object.freeze({
        timestamp: new Date().toISOString(),
        type,
        message,
      }),
    ]);
    
    // [DEV] Send to DevDebugPanel
    const win = window as unknown as { 
      shinonDebug?: (level: "info" | "warn" | "error" | "debug", component: string, message: string) => void 
    };
    if (typeof win.shinonDebug === "function") {
      win.shinonDebug(type === "error" ? "error" : "info", "ChatShell", message);
    }
  }, []);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Log session info on mount
  useEffect(() => {
    addLog("info", `Session gestartet: ${sessionId}`);
    addLog("info", `Conversation: ${conversationId}`);
  }, [sessionId, conversationId, addLog]);

  // Log messages count
  useEffect(() => {
    addLog("info", `Messages: ${messages.length}`);
  }, [messages.length, addLog]);

  // Sehr simpler Live-Sentiment-Check auf dem Draft, damit der Orb sofort reagiert
  useEffect(() => {
    const text = draft.toLowerCase();
    if (/(fuck|scheiß|verdammt|idiot|digga|rotze|garbage|shit)/u.test(text)) {
      setCurrentMood("aggressive");
    } else if (/(schnell|now|sofort|asap|hurry|beeil)/u.test(text)) {
      setCurrentMood("impatient");
    } else if (/(haha|lol|lmao|geil|nice|cool|\^\^|:d)/u.test(text)) {
      setCurrentMood("cheerful");
    } else if (/(glaubst du|denkst du|warum|wieso|philosoph|sinn)/u.test(text)) {
      setCurrentMood("thoughtful");
    } else if (draft.length === 0) {
      setCurrentMood("neutral");
    }
  }, [draft]);

  const canSend = useMemo(() => normalizeText(draft).length > 0 && !isSending, [draft, isSending]);

  const emit = useCallback(
    (event: ChatShellEvent) => {
      onEvent?.(event);
    },
    [onEvent]
  );

  const submitMessage = useCallback(async () => {
    const normalizedText = normalizeText(draft);

    if (normalizedText.length === 0) {
      const nextError: ChatUIError = {
        code: "EMPTY_MESSAGE",
        message: "Message must not be empty.",
      };
      setError(nextError);
      emit({ type: "error", error: nextError });
      return;
    }

    if (normalizedText.length > 25000) {
      const nextError: ChatUIError = {
        code: "REQUEST_FAILED",
        message: "Message too long. Komm mal runter, Digga. Max 25000 Zeichen.",
      };
      setError(nextError);
      emit({ type: "error", error: nextError });
      return;
    }

    if (isSending) {
      const nextError: ChatUIError = {
        code: "DUPLICATE_SEND",
        message: "A chat request is already in flight.",
      };
      setError(nextError);
      emit({ type: "error", error: nextError });
      return;
    }

    const payload = buildRequestPayload(messages, normalizedText, model, sessionId, conversationId);

    setIsSending(true);
    setError(null);
    addLog("request", `Sende: ${normalizedText.substring(0, 50)}...`);
    emit({ type: "submit", payload });

    setMessages((current) => [
      ...current,
      {
        id: `${payload.requestId}-user`,
        role: "user",
        content: normalizedText,
      },
    ]);

    try {
      const response = await sendChatRequest(payload, apiBasePath);
      addLog("response", `Antwort: ${response.reply.substring(0, 50)}... (${response.source})`);
      const assistantMessage: ChatMessage = {
        id: `${response.requestId}-assistant`,
        role: "assistant",
        content: response.reply,
      };

      setMessages((current) => [...current, assistantMessage]);
      setDraft("");
      emit({
        type: "success",
        payload: {
          requestId: response.requestId,
          reply: response.reply,
          source: response.source,
        },
      });
    } catch (caughtError) {
      const message =
        caughtError instanceof Error && caughtError.message.trim().length > 0
          ? caughtError.message.trim()
          : "Chat request failed.";

      addLog("error", `Fehler: ${message}`);
      
      const nextError: ChatUIError = {
        code: message === "Chat response was invalid" ? "INVALID_RESPONSE" : "REQUEST_FAILED",
        message,
      };

      setError(nextError);
      emit({ type: "error", error: nextError });
    } finally {
      setIsSending(false);
    }
  }, [apiBasePath, conversationId, draft, emit, isSending, messages, model, sessionId]);

  return (
    <section className="chat-shell" aria-busy={isSending ? "true" : "false"} aria-label="Chat interface">
      <header className="chat-shell__header">
        <h2>Chat mit Shinon</h2>
        <p>{isSending ? "Denkt nach..." : "Bereit."}</p>
      </header>
      
      <Orb isThinking={isSending} mood={currentMood} />

      {error ? (
        <div aria-live="polite" className="chat-shell__error" role="alert">
          {error.message}
        </div>
      ) : null}

      <MessageList messages={messages} />

      <Composer
        model={model}
        onModelChange={setModel}
        availableModels={availableModels}
        disableInput={false}
        disableSubmit={!canSend}
        onChange={setDraft}
        onSubmit={() => {
          void submitMessage();
        }}
        value={draft}
      />
      
      {/* [DEV] Model Selector - Required Models from local storage */}
      {showModelSelector && (
        <div className="dev-model-selector">
          <div className="dev-model-selector__header">
            <span className="dev-model-selector__label">
              [DEV] Model Selection - Required: At least 1 model from ./models/
            </span>
            <button
              type="button"
              onClick={() => setShowModelSelector(false)}
              className="dev-model-selector__hide-btn"
            >
              Hide
            </button>
          </div>
          <ModelSelector
            onModelsLoaded={(models) => {
              setAvailableModels(models);
              addLog("info", `[DEV] Loaded ${models.length} models from local storage`);
            }}
            onModelSelect={(model) => {
              setSelectedModel(model);
              addLog("info", `[DEV] Selected model: ${model.name} (${model.sizeFormatted})`);
            }}
          />
          {selectedModel && (
            <div className="dev-model-selector__active">
              ✓ Active: {selectedModel.name} {selectedModel.required && "(Required)"}
            </div>
          )}
        </div>
      )}

      {/* Debug Toggle */}
      <button
        type="button"
        onClick={() => setShowDebug(!showDebug)}
        className="dev-debug-toggle"
      >
        {showDebug ? "▼ [DEV] Panels ausblenden" : "▲ [DEV] Panels anzeigen"}
      </button>

      {/* [DEV] Processing Pipeline - WAS verarbeitet wurde */}
      {showDebug && <DevProcessingPanel />}

      {/* [DEV] Debug Output */}
      {showDebug && <DevDebugPanel />}

      {/* [DEV] Legacy Debug Panels (WAS gespeichert) */}
      {showDebug && (
        <div className="dev-debug-grid">
          {/* Logs Panel */}
          <div className="dev-debug-panel">
            <div className="dev-debug-panel__title">[DEV] 📋 Internal Logs</div>
            {logs.map((log, i) => (
              <div key={i} className={`dev-debug-panel__log dev-debug-panel__log--${log.type}`}>
                [{log.timestamp.split("T")[1].split(".")[0]}] {log.message}
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>

          {/* WAS gespeichert Panel */}
          <div className="dev-debug-panel dev-debug-panel--storage">
            <div className="dev-debug-panel__title">[DEV] 💾 WAS gespeichert</div>
            <div>Session ID:</div>
            <div className="dev-debug-panel__muted">{sessionId}</div>
            <div className="dev-debug-panel__row">Conversation ID:</div>
            <div className="dev-debug-panel__muted">{conversationId}</div>
            <div className="dev-debug-panel__row">Messages:</div>
            <div className="dev-debug-panel__muted">{messages.length} Nachrichten</div>
            <div className="dev-debug-panel__row">Selected Model:</div>
            <div className="dev-debug-panel__muted">{selectedModel?.name || "None"}</div>
            <div className="dev-debug-panel__row">Letzte Antwort:</div>
            <div className="dev-debug-panel__muted">
              {messages.filter(m => m.role === "assistant").slice(-1)[0]?.content?.substring(0, 100) || "—"}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
