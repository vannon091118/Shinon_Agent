import { randomUUID } from "node:crypto";
import { ChatShell } from "../components/chat/ChatShell";

/**
 * Render the chat UI with freshly generated session and conversation identifiers.
 *
 * @returns A React element that renders `ChatShell` with new UUID-based `sessionId` and `conversationId` props.
 */
export default function Page() {
  return (
    <ChatShell
      sessionId={randomUUID()}
      conversationId={randomUUID()}
    />
  );
}
