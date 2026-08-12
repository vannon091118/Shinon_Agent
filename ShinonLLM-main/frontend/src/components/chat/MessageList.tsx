import type { UiErrorState, UiMessage } from "../../lib/types";

export type MessageListProps = {
  messages: readonly UiMessage[];
  isStreaming?: boolean;
  error?: UiErrorState | null;
  userText?: string;
  onRetry?: () => void;
  onMessageSelect?: (message: UiMessage) => void;
  className?: string;
};

function normalizeText(value: string): string {
  return value.trim();
}

function resolveMessageState(message: UiMessage, isStreaming: boolean, isLast: boolean): string {
  if (message.status) {
    return message.status;
  }
  if (message.role === "assistant" && isStreaming && isLast) {
    return "streaming";
  }
  return "sent";
}

export function MessageList({
  messages,
  isStreaming = false,
  error = null,
  userText = "",
  onRetry,
  onMessageSelect,
  className = "",
}: MessageListProps) {
  const safeMessages = Array.isArray(messages) ? messages : [];
  const trimmedUserText = normalizeText(userText);

  return (
    <section className={className || undefined} aria-label="Chat messages" data-state={error ? "error" : isStreaming ? "streaming" : "ready"}>
      {error ? (
        <div role="alert" data-error-code={error.code} className="chat-error">
          <p>{normalizeText(error.message)}</p>
          {error.requestId ? <p data-request-id={error.requestId}>Request {error.requestId}</p> : null}
          {onRetry ? (
            <button type="button" onClick={onRetry}>
              Retry
            </button>
          ) : null}
        </div>
      ) : null}

      <ul role="list" className="chat-message-list">
        {safeMessages.map((message, index) => {
          const state = resolveMessageState(message, isStreaming, index === safeMessages.length - 1);
          const text = normalizeText(message.content);
          const key = message.id || `message-${index}`;

          return (
            <li
              key={key}
              data-message-id={message.id}
              data-message-role={message.role}
              data-message-state={state}
              className={`chat-message chat-message--${message.role} chat-message--${state}`}
              onClick={onMessageSelect ? () => onMessageSelect(message) : undefined}
            >
              <header className="chat-message__meta">
                <span>{message.role}</span>
                {message.timestamp ? <time dateTime={message.timestamp}>{message.timestamp}</time> : null}
              </header>
              <p className="chat-message__content">{text}</p>
            </li>
          );
        })}
      </ul>

      {isStreaming ? (
        <div aria-live="polite" className="chat-streaming">
          <span>Streaming</span>
          {trimmedUserText ? <span data-user-text={trimmedUserText}>{trimmedUserText}</span> : null}
        </div>
      ) : null}
    </section>
  );
}
