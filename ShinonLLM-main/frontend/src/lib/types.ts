export type UiMessage = {
  id: string;
  role: "system" | "user" | "assistant";
  content: string;
  status?: "idle" | "sending" | "streaming" | "sent" | "error";
  timestamp?: string;
};

export type UiErrorState = {
  code: "BAD_REQUEST" | "ORCHESTRATION_FAILED" | "INTERNAL_SERVER_ERROR" | (string & {});
  message: string;
  requestId?: string;
};
