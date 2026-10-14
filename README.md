# SBR Game

Steel Ball Run racing game for Roblox. Fixed angled camera, 2D sprite map, and a fully animated 3D horse and rider
with a Steel Ball Run–style theme song and sound effects.

## Controls

| Key | Action |
| --- | --- |
| WASD / arrows / thumbstick | Ride (the horse has momentum: it accelerates, carves turns and brakes) |
| Shift (or the GALLOP button) | Gallop. Burns stamina; run dry and you have to recover before galloping again |
| Space | Jump |
| Q / E | Rear up and neigh / toss head and snort |
| M | Mute music |

## Run it

1. Install [Rojo](https://rojo.space) and the Rojo Studio plugin.
2. `rojo serve` in this folder, then Connect in Studio.
3. Press Play.

## Layout

- `src/shared/Assets.luau` – all uploaded image IDs and sprite cut-outs
- `src/shared/Config.luau` – camera angle, distance, world size
- `src/shared/MapData.luau` – trail path and prop scatter rules
- `src/shared/SpriteFactory.luau` – builds a 2D sprite that faces the camera
- `src/shared/HorseModel.luau` – builds the saddled horse and rider from Parts (no upload needed) and owns the skeleton
- `src/shared/HorseAnimator.luau` / `Gait.luau` – procedural gait: walk/trot/gallop blend, planted-hoof IK, rearing, jumping, braking
- `src/shared/Sfx.luau` / `AudioIds.luau` – sound playback by name; `AudioIds` holds the uploaded Roblox asset IDs
- `src/client/Mounts.client.luau` – a mount per player, riding controls, stamina, dust, hoofbeats
- `src/client/Camera.client.luau`, `Hud.client.luau`, `Fx.client.luau`, `AudioDirector.client.luau` – camera feel, title screen + HUD, screen grading, music/ambience
- `src/server/Main.server.luau` – builds the map
- `src/client/Camera.client.luau` – fixed follow camera
- `assets/` – put source PNGs here
- `assets/horse/` – 3D horse (Blender-built, rigged, PBR textured); see its README
- `tools/build_horse.py` – regenerates the horse model and textures with `bpy`
- `assets/audio/` – generated soundtrack and SFX (`.ogg`); see `docs/audio.md` for uploading them to Roblox
- `assets/horse/` – the Blender horse model + textures (reference for the in-game horse)
- `docs/asset-prompts.md` – ChatGPT prompts for new art
- `tools/make_audio.py`, `tools/upload_audio.py` – synthesise the audio / upload it and record the IDs
- `tests/` – Luau unit tests (`python3 tests/run.py`, needs the `luau` CLI): gait maths, horse model, animator foot-planting

## Adding new sprites

1. Save the PNG in `assets/` and add it to `assets/manifest.json` (file, Roblox ID, pixels-per-stud, names).
2. `python3 tools/slice_sprites.py` (needs `numpy` and `pillow`).
3. Check `assets/_preview/<sheet>.png` to confirm the numbered boxes match the names.
4. Use the names in `src/shared/MapData.luau`.

## Sound

Nothing plays until the audio has been uploaded to Roblox, which needs one command, see
[docs/audio.md](docs/audio.md). Until then the game runs silently and says so in the Output window.

## Tests

`python3 tests/run.py` runs the Luau tests outside Studio with the plain [Luau CLI](https://github.com/luau-lang/luau/releases)
(Roblox types are mocked). They check the gait maths, build the whole horse and rider, and simulate the
animator at every speed to verify planted hooves don't slide, float or sink.
