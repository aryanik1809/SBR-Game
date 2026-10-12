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
