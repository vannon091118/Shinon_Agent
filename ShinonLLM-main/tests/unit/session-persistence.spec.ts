import { strict as assert } from "node:assert";
import { pathToFileURL } from "node:url";

import {
  createInMemorySessionMemoryPersistence,
  createSqliteSessionMemoryPersistence,
} from "../../memory/src/session/sessionPersistence";

type SqlCall = Readonly<{
  kind: "run" | "all";
  sql: string;
  params: ReadonlyArray<unknown>;
}>;

function createSqliteAdapterHarness() {
  const calls: SqlCall[] = [];
  const rows: Array<Record<string, unknown>> = [];
  let userVersion = 0;

  const adapter = {
    run(sql: string, params: ReadonlyArray<unknown> = []) {
      calls.push({
        kind: "run",
        sql,
        params,
      });
      if (sql.includes("INSERT OR REPLACE INTO session_memory_entries")) {
        rows.push({
          id: String(params[0]),
          session_id: String(params[1]),
          conversation_id: String(params[2]),
          role: String(params[3]),
          content: String(params[4]),
          created_at: String(params[5]),
          expires_at: params[6] == null ? null : String(params[6]),
          metadata_json: params[7] == null ? null : String(params[7]),
        });
      }
      if (sql.startsWith("DELETE FROM session_memory_entries WHERE expires_at")) {
        const now = String(params[0]);
        const before = rows.length;
        for (let i = rows.length - 1; i >= 0; i -= 1) {
          const row = rows[i];
          if (typeof row.expires_at === "string" && row.expires_at.length > 0 && row.expires_at <= now) {
            rows.splice(i, 1);
          }
        }
        return { changes: before - rows.length };
      }
      if (sql.startsWith("PRAGMA user_version =")) {
        const parsed = Number.parseInt(sql.split("=").at(-1)?.trim() ?? "", 10);
        if (Number.isInteger(parsed) && parsed >= 0) {
          userVersion = parsed;
        }
        return { changes: 0 };
      }
      return { changes: 1 };
    },
    all(sql: string, params: ReadonlyArray<unknown> = []) {
      calls.push({
        kind: "all",
        sql,
        params,
      });
      if (sql.trim().startsWith("PRAGMA user_version")) {
        return [{ user_version: userVersion }];
      }
      const sessionId = String(params[0]);
      const conversationId = String(params[1]);
      const limit = Number(params[2]);
      return rows
        .filter((row) => row.session_id === sessionId && row.conversation_id === conversationId)
        .slice(-limit);
    },
  };

  return {
    adapter,
    calls,
    rows,
  };
}

export function sessionpersistencespecMain(): void {
  const inMemory = createInMemorySessionMemoryPersistence();
  const inserted = inMemory.append([
    {
      sessionId: "session-a",
      conversationId: "conversation-a",
      role: "user",
      content: "hello",
      ttlSeconds: 1,
    },
    {
      sessionId: "session-a",
      conversationId: "conversation-a",
      role: "assistant",
      content: "world",
      ttlSeconds: 1,
    },
  ]);
  assert.equal(inserted, 2);

  const loaded = inMemory.load({
    sessionId: "session-a",
    conversationId: "conversation-a",
    limit: 32,
  });
  assert.equal(loaded.length, 2);
  assert.equal(loaded[0]?.role, "user");
  assert.equal(loaded[1]?.role, "assistant");

  const decayed = inMemory.decay({
    now: new Date(Date.now() + 2000).toISOString(),
  });
  assert.equal(decayed > 0, true);

  const harness = createSqliteAdapterHarness();
  const sqlitePersistence = createSqliteSessionMemoryPersistence(harness.adapter);
  sqlitePersistence.append([
    {
      sessionId: "session-b",
      conversationId: "conversation-b",
      role: "user",
      content: "persist me",
    },
  ]);
  const sqliteLoaded = sqlitePersistence.load({
    sessionId: "session-b",
    conversationId: "conversation-b",
    limit: 8,
  });
  assert.equal(sqliteLoaded.length, 1);
  assert.equal(sqliteLoaded[0]?.content, "persist me");

  const schemaCalls = harness.calls.filter(
    (call) =>
      call.kind === "run" &&
      (call.sql.includes("CREATE TABLE IF NOT EXISTS session_memory_entries") ||
        call.sql.includes("CREATE INDEX IF NOT EXISTS idx_session_memory_scope") ||
        call.sql.startsWith("PRAGMA user_version = 1")),
  );
  assert.equal(schemaCalls.length >= 2, true);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  sessionpersistencespecMain();
}
