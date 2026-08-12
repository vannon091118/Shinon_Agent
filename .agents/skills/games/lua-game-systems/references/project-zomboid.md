# Project Zomboid Modding Reference

## Engine: Kahlua Lua VM (Java-embedded Lua 5.1)

Project Zomboid embeds **Kahlua**, a Lua 5.1 interpreter written in Java.
The Java game engine exposes classes, methods, and globals to Lua scripts.

### Key Globals

| Function | Returns | Usage |
|---|---|---|
| `getPlayer()` | `IsoPlayer` | Current local player (client-side) or null |
| `getWorld()` | `IsoWorld` | The game world instance |
| `getCell()` | `IsoCell` | Current cell/chunk |
| `getGameTime()` | `GameTime` | World time instance (calendar, age) |
| `ZombRand(min, max)` | `number` | Pseudo-random integer in [min, max] |
| `getSpecificPlayer(id)` | `IsoPlayer` | Get player by ID (0-based index) |

### Java-Lua Bridge Rules

- **Instance methods:** Use `:` — e.g., `player:getX()`, `item:getFullType()`
- **Static methods:** Use `.` — e.g., `IsoPlayer.getPlayers()`
- **Constructors:** Use `.new()` — e.g., `IsoZombie.new(getCell())`
- **Java collections:** Are NOT Lua tables. Use `:size()` and `:get(index)`.
  Indexing is **0-based**. `ipairs()` and `#` do NOT work on Java lists.
- **Access modifiers:** Only `public` Java fields/methods are exposed to Lua.
  Private/protected members are invisible.
- **Inheritance:** `IsoZombie → IsoGameCharacter → IsoMovingObject → IsoObject`.
  Subclasses inherit all accessible parent methods and fields.

## Standard Lua Libraries Available

| Available | NOT Available |
|---|---|
| `table`, `string`, `math` | `io.*` (sandboxed) |
| `luautils` (PZ utility package) | `os.*` (sandboxed) |
| `require`, `dofile` | `loadfile`, `load` |
| `pcall`, `xpcall` | `debug.*` |

### Community Libraries

- **Starlit Library:** Reflection helper for accessing Java fields with dot notation
- **Events Plus API:** Extended event hooks beyond vanilla
- **Doggy's Library:** Additional modding utilities

## Mod Structure (Build 42)

```
MyMod/
├── mod.info                    # Required metadata
├── poster.png                  # 600x600+ preview
├── Contents/
│   └── mods/
│       └── MyMod/
│           ├── common/         # Shared large assets
│           └── 42.0.0/        # Version-specific
│               └── media/
│                   ├── lua/
│                   │   ├── shared/
│                   │   ├── client/
│                   │   └── server/
│                   └── scripts/
```

### mod.info Format
```
name=My Awesome Mod
id=MyAwesomeMod
description=Adds new weapons and crafting
poster=poster.png
url=https://steamcommunity.com/...
```

The `id` MUST be globally unique across the Workshop and other mods.

### Loading Order

1. **shared/** — Vanilla shared → Mod shared (alphabetical)
2. **client/** — Vanilla client → Mod client (alphabetical)
3. **server/** — Vanilla server → Mod server (on world enter)

Files with identical relative paths OVERWRITE based on load order.
Always nest your files in a mod-named subfolder to prevent conflicts.

## Event System

### Core Event Patterns

```lua
-- Register
Events.OnGameBoot.Add(myHandler)

-- Remove (MUST have reference to the exact function)
Events.OnGameBoot.Remove(myHandler)

-- One-shot
local function oneTimeHandler()
    -- do init work
    Events.OnGameBoot.Remove(oneTimeHandler)
end
Events.OnGameBoot.Add(oneTimeHandler)
```

### Critical Event Catalog

#### Initialization Events (fired once)
| Event | When | Use For |
|---|---|---|
| `OnGameBoot` | Game finishes booting | Global init, config caching |
| `OnGameStart` | World loaded and playable | World-dependent setup |
| `OnNewGame` | New world created | First-time setup |
| `OnInitGlobalModData` | Mod data structures ready | Cache sandbox options |
| `OnCreatePlayer` | Player character created | Per-player init |

#### Game Loop Events (HIGH frequency — optimize aggressively)
| Event | Frequency | Parameters |
|---|---|---|
| `OnTick` | Every game tick | `tick` (number) |
| `OnPlayerUpdate` | Per frame, per player | `player` (IsoPlayer) |

#### Player Events
| Event | Parameters |
|---|---|
| `OnPlayerDeath` | `player` |
| `OnEquipPrimary` | `player`, `item` |
| `OnEquipSecondary` | `player`, `item` |
| `OnNewWave` | (none) |

#### World/Container Events
| Event | Parameters | Notes |
|---|---|---|
| `OnFillContainer` | `roomType`, `containerType`, `container` | Server-side only! Not called for corpses |
| `OnContainerUpdate` | `container` | High frequency |
| `OnClimateManagerInit` | (none) | Weather system ready |

#### Vehicle Events
| Event | Use |
|---|---|
| `OnEnterVehicle` | Player enters vehicle |
| `OnExitVehicle` | Player exits vehicle |
| `Vehicles.Update.*` | Per-vehicle per-frame updates |
| `Vehicles.ContainerAccess` | Container access check |

#### Multiplayer Networking
| Function | Direction |
|---|---|
| `sendClientCommand(module, command, argsTable)` | Client → Server |
| `sendServerCommand(player, module, command, argsTable)` | Server → Client(s) |
| `Events.OnClientCommand.Add(handler)` | Server receives |

## Vehicle Physics Parameters

Vehicles defined in `.txt` scripts:

```
vehicle MyCustomCar {
    extents = { 1.5, 0.8, 0.6 },
    mass = 1200,
    engineForce = 4000,
    gearRatioCount = 5,
    brakingForce = 2500,
    steeringClamp = 0.4,
    wheelFriction = 0.8,
    suspensionStiffness = 50,
    suspensionDamping = 5,
    suspensionCompression = 3,
    centerOfMassOffset = { 0, 0, -0.3 },
    rollInfluence = 0.6,
    physicsChassisShape = "TruckFull",
}
```

**Anti-drift / handling tuning:**
- Lower `centerOfMassOffset.z` → more stable, less rollover
- Lower `rollInfluence` (0.0-1.0) → less physical body roll
- Higher `wheelFriction` → more grip, less slide
- `steeringClamp` → maximum wheel turn angle
- `suspensionStiffness` + `suspensionDamping` → how the car settles after bumps

## Loot Distribution

### ProceduralDistributions.lua Format

```lua
ProceduralDistributions.list.MyCustomLoot = {
    rolls = 3,
    items = {
        "Base.BaseballBat",   50,
        "Base.Hammer",        30,
        "Base.Pistol",        10,
        "MyMod.RareItem",      2,
    },
    -- Optional tags
    ignoreZombieDensity = false,
    isShop = false,
    stashChance = 5,
}
```

### Item Spawning Tags
| Tag | Effect |
|---|---|
| `ignoreZombieDensity` | Skip density-based loot reduction |
| `isShop` | Mark as shop container |
| `stashChance` | % chance container is a hidden stash |
| `isWorn` | Spawn clothing with wear |
| `isTrash` | Spawn items with dirt/trash condition |

### Avoiding Loot Bloat
- Don't `table.insert()` hundreds of items into vanilla tables
- Use `OnFillContainer` to inject items procedurally
- Use item variants/dynamic textures instead of duplicate item definitions

## Sandbox Options

### Defining Options (Build 41+/42)

```lua
-- shared/MyMod_Sandbox.lua
SandboxOptions.MyMod = {
    SpawnMultiplier = 1.0,
    EnableHardcoreMode = false,
    MaxCustomItems = 10,
}
```

### Caching Pattern

```lua
-- Cache at init — NEVER read SandboxVars in hot loops
local config = {
    spawnMult = 1.0,
    hardcore = false,
}

Events.OnInitGlobalModData.Add(function()
    if SandboxVars and SandboxVars.MyMod then
        config.spawnMult = SandboxVars.MyMod.SpawnMultiplier or 1.0
        config.hardcore = SandboxVars.MyMod.EnableHardcoreMode or false
    end
end)
```

## Anti-Cheat System (Server-Side)

### Type Overview (Types 1-24, configurable in servertest.ini)

| Type | What It Checks |
|---|---|
| 1 | PVP rules, god-mode, safety states, faction rules |
| 2 | Player/vehicle movement speed limits |
| 3 | Melee/ranged attack distance validation |
| 4 | Maximum damage per hit cap |
| 5-7 | Zombie interaction ownership and validity |
| 8, 10 | Packet type authorization |
| 9, 15 | XP gain rate monitoring |
| 12 | Access-level validation (often false-positive with mods) |
| 16-18 | Fire/smoke creation validation |
| 21-22 | Lua/recipe checksum verification |
| 23-24 | Client-server time synchronization |

### Modder Impact

- **Type 12** and **Type 21** commonly trigger false positives for mods
- Mods must be server-side trusted: actions configured with `Ban`, `Kick`, `Log`, or `Disable`
- Infraction points: 4 points = punishment, decay 1 point per ~2.5 hours

## Skill Progression Reference

### Standard XP Curve
- Level 1: 75 XP
- Level 2: 150 XP
- Level 3: 300 XP
- Level 5: 1,500 XP
- Level 10: 9,000 XP

### Passive Skills (Strength/Fitness)
- Use much steeper curves (Level 1: 1,500 XP)
- Exempt from character creation XP multipliers

### XP Multipliers
- Skill books: Volume 1-5, multiply training rate for specific level ranges
- Occupation starting levels: +75% XP (level 1 start) to +125% XP (level 3+ start)

## Common PZ-Specific Pitfalls

1. **Copying entire vanilla Lua files** → Breaks all other mods. Wrap individual functions instead.
2. **Client-side item spawning** → Items duplicate in MP. Always spawn server-side.
3. **Using `#` on Java ArrayLists** → Returns wrong length. Use `:size()`.
4. **Anonymous event handlers** → Can't be removed later. Always use named functions.
5. **Mod data pollution** → `getModData()` grows unbounded. Clean up stale entries.
6. **Direct field access on Java objects** → May fail due to reflection limits. Use getter methods or Starlit Library.
7. **Trusting `OnFillContainer` for corpses** → Never fires on corpses. Use alternative hooks.
