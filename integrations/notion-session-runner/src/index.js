const NOTION_VERSION = "2022-06-28";
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

function readProperty(page, name) {
  const property = page?.properties?.[name];
  if (!property) return null;
  if (property.type === "title") return (property.title || []).map((part) => part.plain_text || "").join("");
  if (property.type === "rich_text") return (property.rich_text || []).map((part) => part.plain_text || "").join("");
  if (property.type === "status") return property.status?.name || null;
  if (property.type === "select") return property.select?.name || null;
  if (property.type === "url") return property.url || null;
  if (property.type === "checkbox") return Boolean(property.checkbox);
  return null;
}

function hasBearer(request, secret) {
  if (!secret) return false;
  const value = request.headers.get("authorization") || "";
  return value === `Bearer ${secret}`;
}

async function notionGetPage(pageId, env) {
  const response = await fetch(`https://api.notion.com/v1/pages/${pageId}`, {
    headers: {
      authorization: `Bearer ${env.NOTION_TOKEN}`,
      "notion-version": env.NOTION_VERSION || NOTION_VERSION,
      accept: "application/json",
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body?.message || `Notion API returned HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return body;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: { "access-control-allow-methods": "GET, POST, OPTIONS", "access-control-allow-headers": "authorization, content-type" } });
    }

    if (request.method === "GET" && url.pathname === "/health") {
      return json({
        ok: true,
        component: "notion-session-runner",
        mode: "preflight-only",
        notionConfigured: Boolean(env.NOTION_TOKEN),
        webhookSecretConfigured: Boolean(env.WEBHOOK_SECRET),
        executionEnabled: false,
      });
    }

    if (request.method !== "POST" || !["/preflight", "/webhook"].includes(url.pathname)) {
      return json({ error: "not_found" }, 404);
    }
    if (!hasBearer(request, env.WEBHOOK_SECRET)) {
      return json({ error: "unauthorized" }, 401);
    }
    if (!env.NOTION_TOKEN) {
      return json({ error: "notion_token_not_configured" }, 503);
    }

    let input;
    try {
      input = await request.json();
    } catch {
      return json({ error: "invalid_json" }, 400);
    }

    const pageId = String(input?.page_id || input?.session_page_id || "");
    const requestId = String(input?.request_id || "");
    const action = String(input?.action || "preflight");
    if (!UUID_RE.test(pageId)) return json({ error: "invalid_page_id", hint: "Send the Notion session page UUID as page_id." }, 400);
    if (!requestId || requestId.length > 160) return json({ error: "request_id_required" }, 400);
    if (action !== "preflight") {
      return json({
        error: "execution_not_configured",
        mode: "preflight-only",
        message: "This scaffold intentionally performs read-only preflight. It does not start an agent, mutate a session, or claim work is running.",
      }, 501);
    }

    try {
      const page = await notionGetPage(pageId, env);
      const status = readProperty(page, "Status");
      const fields = {
        session: readProperty(page, "Session") || readProperty(page, "Name") || page.id,
        status,
        phase: readProperty(page, "Phase"),
        goal: readProperty(page, "Ziel"),
        doneCriterion: readProperty(page, "Done-Kriterium"),
        scope: readProperty(page, "Scope"),
        notScope: readProperty(page, "Nicht-Scope"),
        nextAction: readProperty(page, "Nächste Aktion"),
      };

      const missing = [];
      if (!fields.goal) missing.push("Ziel");
      if (!fields.doneCriterion) missing.push("Done-Kriterium");
      if (!fields.scope) missing.push("Scope");
      if (!fields.notScope) missing.push("Nicht-Scope");

      return json({
        ok: missing.length === 0,
        mode: "preflight-only",
        request_id: requestId,
        session_page_id: page.id,
        session_url: page.url,
        status,
        fields,
        missing_required_fields: missing,
        may_start: false,
        reason: missing.length ? "required_fields_missing" : "read_only_preflight_passed_but_execution_is_not_configured",
      }, missing.length ? 422 : 200);
    } catch (error) {
      const status = Number.isInteger(error?.status) ? error.status : 502;
      return json({ error: "notion_read_failed", http_status: status, message: error?.message || "Unknown Notion API error" }, 502);
    }
  },
};

export { readProperty, UUID_RE };