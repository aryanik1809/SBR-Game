# Horse (3D)

Blocky saddled horse built procedurally in Blender (`tools/build_horse.py`), matching the concept sheet.
About 3.9k tris, 13 bones, one 2048² PBR atlas (~400 px/m).

| File | Use |
| --- | --- |
| `horse.blend` | Full scene: rigged meshes + PBR material |
| `horse_rigged.fbx` | Skinned meshes + armature (one mesh per body part, rigidly bound to a bone) |
| `horse_static.obj` / `.mtl` | Single merged static mesh, for a plain MeshPart |
| `horse.glb` | glTF with embedded textures |
| `horse_color.png`, `horse_normal.png`, `horse_roughness.png`, `horse_metalness.png` | Atlas maps. Normal map is OpenGL (+Y up). |
| `previews/` | Turnaround renders and `sheet.png` |

## Roblox

- Upload `horse_static.obj` (or the FBX) with the Studio 3D Importer, then add a `SurfaceAppearance` to the MeshPart and
  set `ColorMap`, `NormalMap`, `RoughnessMap` and `MetalnessMap` to the four PNGs once uploaded.
- Modelled at 1 unit = 1 m (1.9 tall). The importer's scale varies, so resize the MeshPart to fit your 5-stud character.
- The horse faces +Y in Blender. Files are exported with forward = -Z, up = Y. If it faces backwards in Studio,
  rotate the PrimaryPart 180°.
- Bones: `Root`, `Spine`, `Neck`, `Head`, `Tail`, and `FL/FR/BL/BR` `_Up` / `_Lo` legs.

## Rebuild

```
pip install bpy numpy pillow         # bpy 5.x needs Python 3.11+
python3 tools/build_horse.py         # regenerates everything in assets/horse/
python3 tools/render_horse.py        # previews (--pose gallop for the leaping pose)
python3 tools/make_horse_sheet.py    # previews/sheet.png
```
