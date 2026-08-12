export type ChatMessage = Readonly<{
  role: "system" | "user" | "assistant";
  content: string;
  id?: string;
}>;

export type ChatRequest = Readonly<{
  message?: string;
  text?: string;
  prompt?: string;
  input?: string;
  content?: string;
  sessionId?: string;
  conversationId?: string;
  requestId?: string;
  messages?: ReadonlyArray<ChatMessage>;
  metadata?: Readonly<Record<string, string | number | boolean | null>>;
}>;

export type ChatResponse =
  | Readonly<{
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
    }>
  | Readonly<{
      ok: false;
      status: "error";
      error: Readonly<{
        code:
          | "BAD_REQUEST"
          | "ORCHESTRATION_FAILED"
          | "INTERNAL_SERVER_ERROR";
        message: string;
        requestId?: string;
      }>;
    }>;
