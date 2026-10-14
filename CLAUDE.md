# SBR Game: notes for Claude Code

Steel Ball Run racing game for Roblox, built with Rojo (`default.project.json`, code in `src/`).
Fixed 3/4 camera, 2D sprite map, animated 3D horse and rider, theme song and SFX. See `README.md`.

## Rules for this repo
- **Do not change the world/map build** (`src/server/Main.server.luau` ground, trail, props, landmarks, border,
  lighting, spawn) unless asked. The player/avatar parts at the bottom of that file are fine to edit.
- Tuning values live in `src/shared/Config.luau`.
- Code is the source of truth. Edit files here and let `rojo serve` sync them; don't edit Rojo-synced scripts
  through the Studio MCP (they'd be overwritten). Use the Studio MCP to read Output, inspect, playtest, screenshot.
- Always save/publish a Studio version before larger MCP edits to the place.

## Checks
- `python3 tests/run.py` runs the Luau unit tests (needs the `luau` CLI; Roblox types are mocked): gait maths,
  horse model, animator foot planting, trail maths.
- `luau-analyze <file>`: ignore "Unknown type/global" for Roblox classes; anything else is real.

## Layout
- `src/shared/`: `HorseModel` (Part-built horse and rider + skeleton), `HorseAnimator` + `Gait` (procedural
  animation), `Sfx` + `AudioIds` (sound), `TrailMath`, plus the original map modules.
- `src/client/`: `Mounts` (a horse per player, controls, stamina), `Camera`, `Hud` (title + HUD), `Fx`,
  `AudioDirector`, `HoofPrints`, `Feel` (shared client state).
- `assets/horse/`: the Blender horse (reference/mesh source); `assets/audio/`: generated sound files.
- `tools/`: `build_horse.py` (needs `bpy`), `make_audio.py`, `upload_audio.py`.

## Audio
Sounds are found by name from `AudioIds.luau` or a `ReplicatedStorage.SBRAudio` folder of Sound objects
(drag imported audio in from Asset Manager). Missing sounds are silent, not errors. See `docs/audio.md`.

## Branch
Work happens on `claude/cool-ride-pzcuzv`.
