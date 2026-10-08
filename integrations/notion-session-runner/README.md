# Notion Session Runner (preflight scaffold)

This Cloudflare Worker is an intentionally **read-only preflight scaffold** for the Notion Agent Sessions database. It is not an autonomous agent yet and does not change session statuses or call an LLM.

## What exists

- `GET /health`: reports whether secrets are configured, never reveals secret values.
- `POST /preflight` (or `POST /webhook`): checks a bearer secret, reads a Notion session page, and validates required fields.
- `POST` with `action: "start"` is deliberately rejected with HTTP 501 until an execution engine, approval gates, idempotency, and write/readback logic are implemented.
- No session mutation, background polling, or false "running" status.

## Required setup

1. Create an internal Notion integration in Notion's integration settings.
2. Grant it only the minimum needed read access initially. Share the **Agent Sessions — Live-Steuerung** database with that integration. Share additional context sources only when the runner actually needs them.
3. Store the integration token as a Cloudflare secret, not in Notion, Git, or a public variable:
   `npx wrangler secret put NOTION_TOKEN`
4. Generate a long random webhook secret and store it:
   `npx wrangler secret put WEBHOOK_SECRET`
5. Install dependencies and run locally:
   `npm install`
   `cp .dev.vars.example .dev.vars`
   Replace the placeholders in the untracked local `.dev.vars` file, then `npm run dev`.
6. Deploy only after the read-only test passes:
   `npm run deploy`

## Request contract

Send `Authorization: Bearer <WEBHOOK_SECRET>` and JSON:

```json
{
  "action": "preflight",
  "page_id": "UUID_OF_NOTION_SESSION_PAGE",
  "request_id": "unique-caller-generated-id"
}
```

The session page ID is the Notion page UUID, **not** the human-readable `Session ID` property such as `SES-1`.

## Manual smoke test

```sh
curl -sS https://YOUR_WORKER_DOMAIN/health
curl -sS -X POST https://YOUR_WORKER_DOMAIN/preflight \
  -H "Authorization: Bearer $WEBHOOK_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"action":"preflight","page_id":"UUID_OF_NOTION_SESSION_PAGE","request_id":"manual-smoke-001"}'
```

Expected: the first response reports configuration booleans only. The second reports the session's current status and required-field checks. It must not claim execution has started.

## Before enabling agent execution

- Verify webhook source authentication; do not assume an arbitrary HTTP request is a trusted Notion action.
- Confirm the chosen Notion API version and data-source access against the real workspace.
- Add durable idempotency storage (e.g. a Cloudflare Durable Object or database), so duplicate triggers cannot repeat mutations.
- Add explicit approval checks and a strict allowlist of allowed actions.
- Add one bounded execution step at a time, with persisted checkpoint and Notion readback.
- Add LLM provider configuration and budget limits in secret/config storage.
- Implement tests for missing context, conflicting sources, timeouts, duplicate requests, Notion write failure, and resume-after-crash.
- Do not set a session to `Läuft` until a real worker has taken ownership and started the actual execution loop.
