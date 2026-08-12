---
name: cloud-platforms-router
description: "Router für 89 Cloud-Platform-Skills (Vercel 46 + Render 21 + Netlify 12 + Cloudflare 9 + DigitalOcean 1). Leitet User-Intents automatisch an den richtigen Sub-Skill. Use bei Next.js, Deploy, Functions, Edge, AI-SDK, Workers, Durable Objects, Turborepo, v0, Droplets."
category: cloud-platforms
stack: AUTONOM + GOVERNANCE
risk: high
side_effects: deploy_changes
requires_approval: true
version: "1.0.0"
last_verified: "2026-08-11"

---
# ☁️ Cloud Platforms Router — 89 Skills

> **Router für `cloud-platforms/`** — Wählt automatisch den richtigen Sub-Skill.

---

## 🗺️ Routing-Tabelle

### Vercel (46 Skills) — `cloud-platforms/vercel/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Next.js", "App Router", "Server Component" | `nextjs` | `vercel/nextjs` |
| "deploy", "CI/CD", "Vercel deployment" | `deployments-cicd` | `vercel/deployments-cicd` |
| "AI SDK", "Vercel AI", "generateText" | `ai-sdk` | `vercel/ai-sdk` |
| "Vercel Functions", "serverless" | `vercel-functions` | `vercel/vercel-functions` |
| "Edge Functions", "edge runtime" | — (see nextjs) | `vercel/nextjs` |
| "Vercel CLI", "vercel command" | `vercel-cli` | `vercel/vercel-cli` |
| "env vars", "environment variables" | `env-vars` | `vercel/env-vars` |
| "Vercel storage", "KV", "Blob", "Postgres" | `vercel-storage` | `vercel/vercel-storage` |
| "Vercel Queues", "message queue" | `vercel-queues` | `vercel/vercel-queues` |
| "Vercel Cron Jobs", "scheduled" | `cron-jobs` | `vercel/cron-jobs` |
| "Vercel Firewall", "WAF" | `vercel-firewall` | `vercel/vercel-firewall` |
| "Vercel Flags", "feature flags" | `vercel-flags` | `vercel/vercel-flags` |
| "Vercel Analytics", "observability" | `observability` | `vercel/observability` |
| "Vercel Agent", "agent browser" | `vercel-agent` | `vercel/vercel-agent` |
| "Agent Browser", "browser agent" | `agent-browser` | `vercel/agent-browser` |
| "Agent Browser Verify" | `agent-browser-verify` | `vercel/agent-browser-verify` |
| "Turborepo", "monorepo" | `turborepo` | `vercel/turborepo` |
| "Turbopack", "bundler" | `turbopack` | `vercel/turbopack` |
| "shadcn/ui", "shadcn Vercel" | `shadcn` | `vercel/shadcn` |
| "v0", "v0 dev", "v0.dev" | `v0-dev` | `vercel/v0-dev` |
| "Geist", "Vercel design system" | `geist` | `vercel/geist` |
| "Geist docs", "Vercel docs theme" | `geistdocs` | `vercel/geistdocs` |
| "Vercel API", "REST API Vercel" | `vercel-api` | `vercel/vercel-api` |
| "Auth", "Vercel auth", "authentication" | `auth` | `vercel/auth` |
| "Sign in with Vercel" | `sign-in-with-vercel` | `vercel/sign-in-with-vercel` |
| "Payments", "Vercel payments" | `payments` | `vercel/payments` |
| "Email", "Vercel email", "Resend" | `email` | `vercel/email` |
| "CMS", "Vercel CMS", "content" | `cms` | `vercel/cms` |
| "Marketplace", "Vercel marketplace" | `marketplace` | `vercel/marketplace` |
| "Verification", "Vercel verify" | `verification` | `vercel/verification` |
| "Bootstrap", "Vercel start" | `bootstrap` | `vercel/bootstrap` |
| "Chat SDK", "Vercel chat" | `chat-sdk` | `vercel/chat-sdk` |
| "AI Elements", "Vercel AI components" | `ai-elements` | `vercel/ai-elements` |
| "AI Gateway", "Vercel AI gateway" | `ai-gateway` | `vercel/ai-gateway` |
| "AI Generation Persistence" | `ai-generation-persistence` | `vercel/ai-generation-persistence` |
| "Routing", "middleware", "proxy" | `routing-middleware` | `vercel/routing-middleware` |
| "Runtime cache", "cache" | `runtime-cache` | `vercel/runtime-cache` |
| "SWR", "stale while revalidate" | `swr` | `vercel/swr` |
| "Satori", "OG image" | `satori` | `vercel/satori` |
| "JSON Render" | `json-render` | `vercel/json-render` |
| "NCC", "ncc compile" | `ncc` | `vercel/ncc` |
| "Micro", "micro server" | `micro` | `vercel/micro` |
| "Next Forge", "next-forge" | `next-forge` | `vercel/next-forge` |
| "Investigation mode" | `investigation-mode` | `vercel/investigation-mode` |
| "Vercel Sandbox" | `vercel-sandbox` | `vercel/vercel-sandbox` |
| "Vercel Services" | `vercel-services` | `vercel/vercel-services` |
| "Workflow", "Vercel workflow" | `workflow` | `vercel/workflow` |

### Render (21 Skills) — `cloud-platforms/render/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Render deploy", "deploy on Render" | `render-deploy` | `render/render-deploy` |
| "Render web service", "Render service" | `render-web-services` | `render/render-web-services` |
| "Render static site" | `render-static-sites` | `render/render-static-sites` |
| "Render background worker" | `render-background-workers` | `render/render-background-workers` |
| "Render cron job", "Render scheduled" | `render-cron-jobs` | `render/render-cron-jobs` |
| "Render Postgres", "Render database" | `render-postgres` | `render/render-postgres` |
| "Render Docker", "Render container" | `render-docker` | `render/render-docker` |
| "Render private service" | `render-private-services` | `render/render-private-services` |
| "Render CLI", "Render command" | `render-cli` | `render/render-cli` |
| "Render Blueprints", "render.yaml" | `render-blueprints` | `render/render-blueprints` |
| "Render env vars" | `render-env-vars` | `render/render-env-vars` |
| "Render domains", "custom domain" | `render-domains` | `render/render-domains` |
| "Render scaling", "autoscale" | `render-scaling` | `render/render-scaling` |
| "Render networking" | `render-networking` | `render/render-networking` |
| "Render disks", "persistent storage" | `render-disks` | `render/render-disks` |
| "Render Key-Value", "Render KV" | `render-keyvalue` | `render/render-keyvalue` |
| "Render monitor", "Render metrics" | `render-monitor` | `render/render-monitor` |
| "Render workflows" | `render-workflows` | `render/render-workflows` |
| "Render MCP" | `render-mcp` | `render/render-mcp` |
| "Render debug", "Render troubleshoot" | `render-debug` | `render/render-debug` |
| "migrate from Heroku to Render" | `render-migrate-from-heroku` | `render/render-migrate-from-heroku` |

### Netlify (12 Skills) — `cloud-platforms/netlify/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Netlify deploy", "deploy Netlify" | `netlify-deploy` | `netlify/netlify-deploy` |
| "Netlify CLI", "netlify command" | `netlify-cli-and-deploy` | `netlify/netlify-cli-and-deploy` |
| "Netlify Functions", "serverless Netlify" | `netlify-functions` | `netlify/netlify-functions` |
| "Netlify Edge Functions" | `netlify-edge-functions` | `netlify/netlify-edge-functions` |
| "Netlify Forms" | `netlify-forms` | `netlify/netlify-forms` |
| "Netlify Identity", "Netlify auth" | `netlify-identity` | `netlify/netlify-identity` |
| "Netlify Blobs", "Netlify storage" | `netlify-blobs` | `netlify/netlify-blobs` |
| "Netlify caching" | `netlify-caching` | `netlify/netlify-caching` |
| "Netlify Image CDN" | `netlify-image-cdn` | `netlify/netlify-image-cdn` |
| "Netlify config", "netlify.toml" | `netlify-config` | `netlify/netlify-config` |
| "Netlify frameworks" | `netlify-frameworks` | `netlify/netlify-frameworks` |
| "Netlify AI Gateway" | `netlify-ai-gateway` | `netlify/netlify-ai-gateway` |

### Cloudflare (9 Skills) — `cloud-platforms/cloudflare/`

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Cloudflare Workers", "worker" | `workers-best-practices` | `cloudflare/workers-best-practices` |
| "Cloudflare Wrangler", "wrangler CLI" | `wrangler` | `cloudflare/wrangler` |
| "Durable Objects", "Cloudflare DO" | `durable-objects` | `cloudflare/durable-objects` |
| "Cloudflare AI Agent", "build agent CF" | `building-ai-agent-on-cloudflare` | `cloudflare/building-ai-agent-on-cloudflare` |
| "Cloudflare MCP server" | `building-mcp-server-on-cloudflare` | `cloudflare/building-mcp-server-on-cloudflare` |
| "Cloudflare Agents SDK" | `agents-sdk` | `cloudflare/agents-sdk` |
| "Cloudflare Sandbox SDK" | `sandbox-sdk` | `cloudflare/sandbox-sdk` |
| "Cloudflare general", "CF overview" | `cloudflare` | `cloudflare/cloudflare` |
| "Cloudflare web perf", "CF performance" | `web-perf` | `cloudflare/web-perf` |

### DigitalOcean (1 Skill)

| User sagt... | → Skill | Pfad |
|---|---|---|
| "DigitalOcean Droplet", "DO droplet", "provision droplet" | `provision-droplet` | `digitalocean/provision-droplet` |

---

## 🔀 Routing-Logik

```
User-Intent erkennen:
├─ "Next.js", "Vercel", "AI SDK", "Turborepo", "v0", "shadcn"
│  → cloud-platforms/vercel/<skill>
│
├─ "Render", "render.com", "Blueprint"
│  → cloud-platforms/render/<skill>
│
├─ "Netlify", "netlify.toml"
│  → cloud-platforms/netlify/<skill>
│
├─ "Cloudflare", "Workers", "Wrangler", "Durable Objects"
│  → cloud-platforms/cloudflare/<skill>
│
├─ "DigitalOcean", "Droplet"
│  → cloud-platforms/digitalocean/<skill>
│
├─ "deploy" ohne Plattform → Frage: "Vercel, Render, Netlify, oder Cloudflare?"
└─ Unklar? → Zeige Plattform-Übersicht
```

---

## Verwendung

```
User: "Ich will meine Next.js App auf Vercel deployen"
→ Router: vercel/nextjs + vercel/deployments-cicd

User: "Setze einen Cron Job auf Render auf"
→ Router: render/render-cron-jobs

User: "Cloudflare Worker mit Durable Objects"
→ Router: cloudflare/workers-best-practices + cloudflare/durable-objects
```

_89 Skills · Vercel 46 + Render 21 + Netlify 12 + Cloudflare 9 + DO 1 · August 2026_
