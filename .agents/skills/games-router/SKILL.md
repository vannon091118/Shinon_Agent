---
name: games-router
description: "Router für 2 games-Skills (lua-game-systems, playcanvas-engine). Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Routing-Tabelle im Body."
category: games
stack: AUTONOM + GOVERNANCE
risk: medium
side_effects: file_changes
requires_approval: true
version: 1.0.0
last_verified: 2026-08-12

---
# 🧭 Games Router — 2 Skills

> **Router für `games/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.

## 🗺️ Routing-Tabelle

| User sagt... | → Skill | Pfad |
|---|---|---|
| "You are an expert in architecting Lua-based game mods and gameplay systems for embedded-Lua game engines (Kahlua/LuaJIT/Luau", "Your focus: clean architecture, multiplayer correctness, balanced game design, and production-quality code that survives real player ..." | `lua-game-systems` | `games/lua-game-systems` |
| "Lightweight WebGL/WebGPU game engine with entity-component architecture and visual editor integration", "Use this skill when building browser-based games, interactive 3D applications, or performance-critical web experiences" | `playcanvas-engine` | `games/playcanvas-engine` |

## 🔀 Routing-Logik

```
  "Lua" → lua-game-systems
  "Playcanvas" → playcanvas-engine
  Unklar? → Nachfrage: Welche Aufgabe, welcher Anbieter?
```

## 📋 Sub-Skill-Register

| # | Skill | Pfad |
|---|---|---|
| 1 | `lua-game-systems` | `games/lua-game-systems` |
| 2 | `playcanvas-engine` | `games/playcanvas-engine` |

_2 Skills · games · 2026-08-12_
