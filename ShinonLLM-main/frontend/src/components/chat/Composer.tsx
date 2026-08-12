export type UiErrorState = {
  code: "empty_input" | "too_long" | "duplicate_submit" | "sending_locked";
  message: string;
  recoverable: boolean;
};

export type UiMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "draft" | "sent" | "failed";
};

export type ComposerUiState = {
  draftText: string;
  isSending: boolean;
  lastSubmittedText?: string;
  maxLength?: number;
  error?: UiErrorState | null;
};

export type ComposerUiEvent =
  | {
      type: "composer/change";
      text: string;
    }
  | {
      type: "composer/submit";
      text: string;
    }
  | {
      type: "composer/error";
      error: UiErrorState;
    };

export type ComposerApiPayload = {
  message: string;
  normalizedMessage: string;
  length: number;
};

export type ComposerResult = {
  normalizedText: string;
  event: ComposerUiEvent | null;
  payload: ComposerApiPayload | null;
  error: UiErrorState | null;
  duplicateSendBlocked: boolean;
};

export type ComposerProps = {
  state: ComposerUiState;
  userText: string;
  onEvent?: (event: ComposerUiEvent) => void;
  onPayload?: (payload: ComposerApiPayload) => void;
  onError?: (error: UiErrorState) => void;
};

function normalizeText(value: string) {
  return value.trim().replace(/\s+/g, " ");
}

function createError(code: UiErrorState["code"], message: string): UiErrorState {
  return {
    code,
    message,
    recoverable: code !== "sending_locked",
  };
}

function finalizeError(
  error: UiErrorState,
  onError?: (error: UiErrorState) => void,
): ComposerResult {
  onError?.(error);
  return {
    normalizedText: "",
    event: { type: "composer/error", error },
    payload: null,
    error,
    duplicateSendBlocked: error.code === "duplicate_submit",
  };
}

export function Composer({
  state,
  userText,
  onEvent,
  onPayload,
  onError,
}: ComposerProps): ComposerResult {
  const normalizedText = normalizeText(userText);
  const maxLength =
    typeof state.maxLength === "number" && Number.isFinite(state.maxLength)
      ? Math.max(0, Math.floor(state.maxLength))
      : undefined;

  if (state.isSending) {
    return finalizeError(
      createError("sending_locked", "Composer is locked while a send is in progress."),
      onError,
    );
  }

  if (!normalizedText) {
    return finalizeError(
      createError("empty_input", "Composer input must contain non-whitespace text."),
      onError,
    );
  }

  if (typeof maxLength === "number" && normalizedText.length > maxLength) {
    return finalizeError(
      createError("too_long", "Composer input exceeds the configured maximum length."),
      onError,
    );
  }

  if (state.lastSubmittedText !== undefined && state.lastSubmittedText === normalizedText) {
    return finalizeError(
      createError("duplicate_submit", "Duplicate submission blocked."),
      onError,
    );
  }

  const payload: ComposerApiPayload = {
    message: normalizedText,
    normalizedMessage: normalizedText,
    length: normalizedText.length,
  };

  const event: ComposerUiEvent = {
    type: "composer/submit",
    text: normalizedText,
  };

  onEvent?.(event);
  onPayload?.(payload);

  return {
    normalizedText,
    event,
    payload,
    error: null,
    duplicateSendBlocked: false,
  };
}
