# SBR Game

Steel Ball Run racing game for Roblox. Fixed angled camera, 2D sprite map, 3D player and horse.

## Run it

1. Install [Rojo](https://rojo.space) and the Rojo Studio plugin.
2. `rojo serve` in this folder, then Connect in Studio.
3. Press Play.

## Layout

- `src/shared/Assets.luau` – all uploaded image IDs and sprite cut-outs
- `src/shared/Config.luau` – camera angle, distance, world size
- `src/shared/MapData.luau` – trail path and prop scatter rules
- `src/shared/SpriteFactory.luau` – builds a 2D sprite that faces the camera
- `src/server/Main.server.luau` – builds the map
- `src/client/Camera.client.luau` – fixed follow camera
- `assets/` – put source PNGs here
- `docs/asset-prompts.md` – ChatGPT prompts for new art

## Adding new sprites

1. Save the PNG in `assets/` and add it to `assets/manifest.json` (file, Roblox ID, pixels-per-stud, names).
2. `python3 tools/slice_sprites.py` (needs `numpy` and `pillow`).
3. Check `assets/_preview/<sheet>.png` to confirm the numbered boxes match the names.
4. Use the names in `src/shared/MapData.luau`.
