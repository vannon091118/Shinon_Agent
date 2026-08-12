---
name: gaming-router
description: "Router für 9 gaming-Skills (game-studio). Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Routing-Tabelle im Body."
category: gaming
stack: AUTONOM + GOVERNANCE
risk: medium
side_effects: file_changes
requires_approval: true
version: 1.0.0
last_verified: 2026-08-12

---
# 🧭 Gaming Router — 9 Skills

> **Router für `gaming/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.

## 🗺️ Routing-Tabelle

| User sagt... | → Skill | Pfad |
|---|---|---|
| "Run browser-game playtests and frontend QA", "Use when the user asks for smoke tests, screenshot-based verification, browser automation, HUD or overlay review, or structured ..." | `game-playtest` | `gaming/game-studio/game-playtest` |
| "Route early browser-game work", "Use when the user needs stack selection and workflow planning across design, implementation, assets, and playtesting before moving to a ..." | `game-studio` | `gaming/game-studio/game-studio` |
| "Design UI surfaces for browser games", "Use when the user asks for HUDs, menus, overlays, responsive layouts, or visual direction that must protect the playfield" | `game-ui-frontend` | `gaming/game-studio/game-ui-frontend` |
| "Implement 2D browser games with Phaser", "Use when the user wants a Phaser, TypeScript, and Vite stack for scenes, gameplay systems, cameras, sprite animation, and DOM-overlay HUD ..." | `phaser-2d-game` | `gaming/game-studio/phaser-2d-game` |
| "Build React-hosted 3D browser games with React Three Fiber", "Use when the user wants pmndrs-based scene composition, shared React state, and 3D HUD integration inside a React app" | `react-three-fiber-game` | `gaming/game-studio/react-three-fiber-game` |
| "Generate and normalize 2D sprite animations", "Use when the user asks for full-strip generation from approved source frames, consistent anchor and scale normalization, or preview assets ..." | `sprite-pipeline` | `gaming/game-studio/sprite-pipeline` |
| "Implement browser-game runtimes with plain Three.js", "Use when the user wants imperative scene control in TypeScript or Vite with GLB assets, loaders, physics, and low-level WebGL debugging" | `three-webgl-game` | `gaming/game-studio/three-webgl-game` |
| "Prepare and optimize browser-game 3D assets", "Use when the user asks for GLB or glTF shipping work, including Blender cleanup and export, collision or LOD setup, compression, texture ..." | `web-3d-asset-pipeline` | `gaming/game-studio/web-3d-asset-pipeline` |
| "Set browser-game architecture before implementation", "Use when the user needs engine choice, simulation and render boundaries, input model, asset organization, or save/debug/performance strategy" | `web-game-foundations` | `gaming/game-studio/web-game-foundations` |

## 🔀 Routing-Logik

```
  "Game" → game-playtest
  "Game" → game-studio
  "Game" → game-ui-frontend
  "Phaser" → phaser-2d-game
  "React" → react-three-fiber-game
  "Sprite" → sprite-pipeline
  "Three" → three-webgl-game
  "Web" → web-3d-asset-pipeline
  "Web" → web-game-foundations
  Unklar? → Nachfrage: Welche Aufgabe, welcher Anbieter?
```

## 📋 Sub-Skill-Register

| # | Skill | Pfad |
|---|---|---|
| 1 | `game-playtest` | `gaming/game-studio/game-playtest` |
| 2 | `game-studio` | `gaming/game-studio/game-studio` |
| 3 | `game-ui-frontend` | `gaming/game-studio/game-ui-frontend` |
| 4 | `phaser-2d-game` | `gaming/game-studio/phaser-2d-game` |
| 5 | `react-three-fiber-game` | `gaming/game-studio/react-three-fiber-game` |
| 6 | `sprite-pipeline` | `gaming/game-studio/sprite-pipeline` |
| 7 | `three-webgl-game` | `gaming/game-studio/three-webgl-game` |
| 8 | `web-3d-asset-pipeline` | `gaming/game-studio/web-3d-asset-pipeline` |
| 9 | `web-game-foundations` | `gaming/game-studio/web-game-foundations` |

_9 Skills · gaming · 2026-08-12_
