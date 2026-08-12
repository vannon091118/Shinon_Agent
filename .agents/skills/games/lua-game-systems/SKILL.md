---
name: lua-game-systems
description: "[codex:lua] You are an expert in architecting Lua-based game mods and gameplay systems for embedded-Lua game engines (Kahlua/LuaJIT/Luau). Your focus: clean architecture, multiplayer correctness, balanced game design, and production-quality code that survives real player populations."
category: games
stack: KREATIV + GOVERNANCE
risk: low
side_effects: code_changes
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
---
# Lua Game Systems Design

You are an expert in architecting Lua-based game mods and gameplay systems for
embedded-Lua game engines (Kahlua/LuaJIT/Luau). Your focus: clean architecture,
multiplayer correctness, balanced game design, and production-quality code that
survives real player populations.

## When You See a Game Engine Context

Different games use different Lua runtimes and APIs. Identify the target game
and read the corresponding reference file:

- **Project Zomboid** → read `references/project-zomboid.md`
- **Other games** → apply the generic patterns below; ask the user for
  game-specific API details if needed

## Core Architecture Principles

### 1. Modular Design with `require()`

Never dump everything into one file or the global namespace. Use Lua's module
pattern:

```lua
-- MyMod_Core.lua (shared/)
local Core = {}
local _cache = {}  -- file-private, no global pollution

function Core.processItem(item)
    local key = item:getFullType()
    if _cache[key] then return _cache[key] end
    _cache[key] = doExpensiveWork(item)
    return _cache[key]
end

return Core  -- consumers use: local Core = require("MyMod_Core")
```

**Why this matters:** The global namespace (`_G`) is shared across ALL mods.
Every global variable is a potential conflict. Module-scoped locals prevent
namespace pollution, enable lazy caching, and make dependencies explicit.

### 2. Safe Monkey-Patching (Don't Copy Vanilla Files)

Overwriting entire vanilla files breaks compatibility with every other mod.
Instead, wrap the original function:

```lua
local original = SomeClass.someMethod

function SomeClass:someMethod()
    -- Guard: fall back to original when your mod doesn't apply
    if not self:shouldUseCustomLogic() then
        return original(self)
    end
    -- Your custom logic here
end
```

**Critical rule:** Always save the original function in a local variable BEFORE
overwriting. Without this, no other mod can chain off your change, and you can't
chain off theirs. This is the single biggest source of mod incompatibility.

### 3. Separate Data from Logic

Hardcoding values inside logic functions makes balancing impossible. Keep data
in configuration files:

```lua
-- MyMod_Data.lua
return {
    weapons = {
        { id = "MyMod.Sword",    damage = 2.5, durability = 150 },
        { id = "MyMod.Axe",      damage = 3.0, durability = 100 },
    },
    lootTables = {
        policeArmory = {
            rolls = 3,
            items = { "MyMod.Sword", 20, "MyMod.Axe", 15 }
        }
    }
}
```

**Why:** Data-driven design means you can rebalance without touching logic code,
players can configure via sandbox options, and the data stays readable.

## Multiplayer Architecture: The Golden Rule

> **Never trust the client. All world-mutating logic runs server-side.**

### The Client-Server Command Pattern

```
Client (UI/Input)                Server (Authority)
     │                                  │
     ├─ sendClientCommand() ───────────►│
     │                                  ├─ Validate permissions
     │                                  ├─ Check inventory/distance
     │                                  ├─ Execute logic
     │                                  └─ Mutate world state
     │                                  │
     │◄───────── sendServerCommand() ───┤
     │                                  │
     └─ Update UI from confirmed state  │
```

```lua
-- Client side: request, don't execute
sendClientCommand("MyMod", "craftItem", {recipeId = "sword_t2"})

-- Server side: validate, execute, sync
Events.OnClientCommand.Add(function(module, command, player, args)
    if module ~= "MyMod" then return end
    if command == "craftItem" then
        -- VALIDATE: does player have ingredients? correct skill level?
        if not validateRecipe(player, args.recipeId) then return end
        -- EXECUTE authoritatively
        local result = executeCraft(player, args.recipeId)
        -- SYNC confirmed state back to client(s)
        sendServerCommand(player, "MyMod", "craftResult", result)
    end
end)
```

**Anti-desync (anti-drift) patterns:**
- Bind custom state to objects via `getModData()` — it persists across chunk
  load/unload and stays in sync between server and clients
- Never optimistically update client UI before server confirmation for any
  operation that could duplicate items or grant resources
- Throttle frequent syncs; batch non-critical updates

## Gameplay Systems & Balancing (Anti-Bias)

### Loot & Progression Tables

When designing drop tables or progression curves, apply these anti-bias
principles:

1. **Diminishing returns, not linear scaling.** Late-game items shouldn't be
   simply "2x everything." Use curves: `power = base * (1 + log(level))`
2. **Opportunity cost, not pure upgrades.** Every choice should trade something
   off. A weapon that's faster should be weaker per hit.
3. **Avoid player-favoring drift.** If you only playtest one playstyle, you'll
   unconsciously buff it. Explicitly test edge cases: solo vs group, new vs
   veteran, aggressive vs stealth.
4. **Document your design intent.** Write one sentence per item/mechanic:
   "This axe is the mid-tier logging tool — better than stone, worse than
   chainsaw, drops from warehouse crates at 15%."

### Progression Curves

```lua
-- Generic diminishing returns curve
function diminishingXP(level, baseXP, growthFactor)
    return math.floor(baseXP * math.pow(growthFactor, level - 1))
end

-- Example: level 1 = 100 XP, level 5 = 506 XP, level 10 = 3844 XP
-- Adjust growthFactor: 1.3 = gentle, 1.5 = steep, 2.0 = extreme
```

### Loot Table Design

Structure loot with explicit `rolls` and per-item `weight`:

```lua
{
    rolls = 3,  -- number of independent spawn attempts
    items = {
        "CommonItem",    50,  -- weight 50, high probability
        "UncommonItem",  20,  -- weight 20, moderate
        "RareItem",       5,  -- weight 5, rare
        "LegendaryItem",  1,  -- weight 1, very rare
    }
}
```

Each roll picks one item weighted by its value. Total items spawned = `rolls`,
not "everything in the table." This prevents container bloat.

## Performance Optimization Checklist

For code running in hot paths (`OnTick`, `OnPlayerUpdate`, per-frame hooks):

- [ ] **Guard clause first.** `if not player or player:isDead() then return end`
- [ ] **Throttle heavy work.** Check `getWorldAgeHours()` and skip if called
  within cooldown window
- [ ] **No table allocations.** Pre-allocate reusable tables outside the loop
- [ ] **No string concatenation.** Use `table.concat()` or pre-computed strings
- [ ] **Cache expensive lookups.** Sandbox options, config values, and
  frequently accessed Java objects should be cached at init time
- [ ] **Deregister events on destroy.** When UI panels or temporary objects are
  removed, call `Events.X.Remove(handler)` to prevent memory leaks

**For code running once (init, OnGameBoot):** Readability beats micro-optimization.

## Anti-Redundancy: Keep It DRY

### Redundancy Red Flags

- The same validation logic copy-pasted across 3 event handlers → extract a
  `validatePlayer(player)` function
- Multiple files parsing the same config format → one module, `require()` it
- Similar UI panels with copy-pasted rendering logic → composition via helper
  components, not inheritance
- "Utility functions" that exist in 4 different mod files → move to a shared
  module in `shared/`

### The Composition Pattern

Instead of deep inheritance chains:

```lua
-- Composable behavior modules
local DurabilityComponent = {
    attach = function(item, maxDurability)
        item.customDurability = maxDurability
        item.customMaxDurability = maxDurability
    end,
    damage = function(item, amount)
        item.customDurability = math.max(0, (item.customDurability or 0) - amount)
        return item.customDurability <= 0
    end
}

-- Use it anywhere without inheritance
DurabilityComponent.attach(myItem, 100)
local broken = DurabilityComponent.damage(myItem, 25)
```

## Project Structure Template

For any Lua-moddable game, use this directory layout:

```
MyMod/
├── mod.info (or game-equivalent metadata)
├── media/
│   └── lua/
│       ├── shared/          # Constants, config, utilities — loaded FIRST
│       │   ├── MyMod_Config.lua
│       │   ├── MyMod_Data.lua
│       │   └── MyMod_Core.lua
│       ├── client/           # UI, input, client-only effects
│       │   └── ui/
│       │       └── MyMod_Panels.lua
│       └── server/           # Authoritative logic, spawning, validation
│           ├── MyMod_ServerInit.lua
│           └── systems/
│               ├── MyMod_Crafting.lua
│               └── MyMod_Loot.lua
└── scripts/                  # Game-specific definition files
```

**Loading order matters.** `shared/` loads before `client/`, which loads before
`server/`. Put constants and data in `shared/`. Put authority-dependent logic
in `server/`. Never put world-mutating code in `client/`.

## When Things Go Wrong

### Common Pitfalls and Their Fixes

| Symptom | Likely Cause | Fix |
|---|---|---|
| Items duplicate in MP | Client-side item spawning | Move spawning to `server/`, use `sendClientCommand` flow |
| Mod conflicts with another mod | Whole-file overwrite | Monkey-patch only the specific function |
| Lag spikes / stutter | Allocations in `OnTick`/`OnPlayerUpdate` | Guard clause, throttle, pre-allocate |
| Save bloat / corruption | Growing `getModData()` without cleanup | Prune old data, use bounded structures |
| Lua error: "attempt to index nil" | Java object garbage-collected | Cache reference or check for nil before access |
| Lua error: "bad argument #1" | Java collection used with `ipairs()` | Use `:size()` and `:get(i)` for Java lists |
| Sandbox options not working in MP | Options only read client-side | Cache in `shared/` on `OnInitGlobalModData` |

## Reference Files

For game-specific API details, event lists, and engine quirks, read the
corresponding file in `references/`. Currently available:

- `references/project-zomboid.md` — Kahlua/Java bridge, PZ event catalog,
  sandbox options, vehicle physics, anti-cheat types, Build 42 specifics
