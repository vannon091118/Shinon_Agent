---
name: web-dev-router
description: "Router für 16 web-dev-Skills (build-web-apps, superpowers). Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Routing-Tabelle im Body."
category: web-dev
stack: AUTONOM + GOVERNANCE
risk: medium
side_effects: file_changes
requires_approval: true
version: 1.0.0
last_verified: 2026-08-12

---
# 🧭 Web-Dev Router — 16 Skills

> **Router für `web-dev/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.

## 🗺️ Routing-Tabelle

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Use for new frontend applications, dashboards, games, creative websites, hero sections, and visually driven UI from scratch, or when the ...", "Builds from clean, airy, high-taste, readable image-generated concept design with section-specific references, faithful implementation, and ..." | `frontend-app-builder` | `web-dev/build-web-apps/frontend-app-builder` |
| "testing", "debugging", "or making targeted improvements to rendered frontend apps through the Build Web Apps or web dev plugin: local dev servers", "UI regressions" | `frontend-testing-debugging` | `web-dev/build-web-apps/frontend-testing-debugging` |
| "React and Next.js performance optimization guidelines from Vercel Engineering", "This skill should be used when writing, reviewing, or refactoring React/Next.js code to ensure optimal performance patterns" | `react-best-practices` | `web-dev/build-web-apps/react-best-practices` |
| "Manages shadcn components and projects — composition rules, critical patterns, and best practices for shadcn/ui in frontend applications", "Distinct from vercel-shadcn which covers CLI, deployment, and Vercel-specific shadcn workflows" | `shadcn-best-practices` | `web-dev/build-web-apps/shadcn-best-practices` |
| "Postgres performance optimization and best practices from Supabase — web-dev context", "Use this when working in frontend/Next.js projects" | `supabase-postgres-best-practices-web` | `web-dev/build-web-apps/supabase-best-practices` |
| "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior", "Explores user intent, requirements and design before implementation.\" | `brainstorming` | `web-dev/superpowers/brainstorming` |
| "facing 2+ independent tasks that can be worked on without shared state or sequential dependencies" | `dispatching-parallel-agents` | `web-dev/superpowers/dispatching-parallel-agents` |
| "you have a written implementation plan to execute in a separate session with review checkpoints" | `executing-plans` | `web-dev/superpowers/executing-plans` |
| "implementation is complete", "all tests pass", "and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge", "PR" | `finishing-a-development-branch` | `web-dev/superpowers/finishing-a-development-branch` |
| "completing tasks", "implementing major features", "or before merging to verify work meets requirements" | `requesting-code-review` | `web-dev/superpowers/requesting-code-review` |
| "executing implementation plans with independent tasks in the current session" | `subagent-driven-development` | `web-dev/superpowers/subagent-driven-development` |
| "implementing any feature or bugfix", "before writing implementation code" | `test-driven-development` | `web-dev/superpowers/test-driven-development` |
| "starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via native tools or git worktree fallback" | `using-git-worktrees` | `web-dev/superpowers/using-git-worktrees` |
| "starting any conversation - establishes how to find and use skills", "requiring Skill tool invocation before ANY response including clarifying questions" | `using-superpowers` | `web-dev/superpowers/using-superpowers` |
| "about to claim work is complete", "fixed", "or passing", "before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always" | `verification-before-completion` | `web-dev/superpowers/verification-before-completion` |
| "creating new skills", "editing existing skills", "or verifying skills work before deployment" | `writing-skills` | `web-dev/superpowers/writing-skills` |

## 🔀 Routing-Logik

```
  "Frontend" → frontend-app-builder
  "Frontend" → frontend-testing-debugging
  "React" → react-best-practices
  "Shadcn" → shadcn-best-practices
  "Supabase" → supabase-postgres-best-practices-web
  "Brainstorming" → brainstorming
  "Dispatching" → dispatching-parallel-agents
  "Executing" → executing-plans
  "Finishing" → finishing-a-development-branch
  "Requesting" → requesting-code-review
  "Subagent" → subagent-driven-development
  "Test" → test-driven-development
  "Using" → using-git-worktrees
  "Using" → using-superpowers
  "Verification" → verification-before-completion
  "Writing" → writing-skills
  Unklar? → Nachfrage: Welche Aufgabe, welcher Anbieter?
```

## 📋 Sub-Skill-Register

| # | Skill | Pfad |
|---|---|---|
| 1 | `frontend-app-builder` | `web-dev/build-web-apps/frontend-app-builder` |
| 2 | `frontend-testing-debugging` | `web-dev/build-web-apps/frontend-testing-debugging` |
| 3 | `react-best-practices` | `web-dev/build-web-apps/react-best-practices` |
| 4 | `shadcn-best-practices` | `web-dev/build-web-apps/shadcn-best-practices` |
| 5 | `supabase-postgres-best-practices-web` | `web-dev/build-web-apps/supabase-best-practices` |
| 6 | `brainstorming` | `web-dev/superpowers/brainstorming` |
| 7 | `dispatching-parallel-agents` | `web-dev/superpowers/dispatching-parallel-agents` |
| 8 | `executing-plans` | `web-dev/superpowers/executing-plans` |
| 9 | `finishing-a-development-branch` | `web-dev/superpowers/finishing-a-development-branch` |
| 10 | `requesting-code-review` | `web-dev/superpowers/requesting-code-review` |
| 11 | `subagent-driven-development` | `web-dev/superpowers/subagent-driven-development` |
| 12 | `test-driven-development` | `web-dev/superpowers/test-driven-development` |
| 13 | `using-git-worktrees` | `web-dev/superpowers/using-git-worktrees` |
| 14 | `using-superpowers` | `web-dev/superpowers/using-superpowers` |
| 15 | `verification-before-completion` | `web-dev/superpowers/verification-before-completion` |
| 16 | `writing-skills` | `web-dev/superpowers/writing-skills` |

_16 Skills · web-dev · 2026-08-12_
