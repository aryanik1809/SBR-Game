# Robot (Roblox-style, Steel Ball Run texture)

Blocky purple-and-tan robot with green side cubes and wires, built from the concept sheet in Blender
(`tools/build_robot.py`). Made for Roblox: low poly, one small atlas, R15 part and bone names.

| | |
| --- | --- |
| Triangles | **1,892** (15 meshes) |
| Texture | one 1024x1024 atlas, one material (colour, normal, roughness, metalness) |
| Height | 1.405 m (R15 is about 1.4 m); 1 unit = 1 m, +Z up, faces +Y |
| Rig | 16 bones with R15 names and joints: `HumanoidRootPart`, `LowerTorso`, `UpperTorso`, `Head`, `Left/Right` `UpperArm`, `LowerArm`, `Hand`, `UpperLeg`, `LowerLeg`, `Foot`. "Left" is -X. |

Files: `robot.blend`, `robot_rigged.fbx` (one mesh per R15 part, bound to its bone), `robot_static.obj/.mtl`
(single mesh), `robot.glb`, `robot_color/normal/roughness/metalness.png`, `previews/`.

## Optimising choices
- Every body part is a chamfered loft or box, joints are 8-sided faceted balls, wires are 6-sided tubes.
- Faces hidden inside neighbouring parts are removed, and the eyes, mouth and beads are painted instead of modelled.
- The head gets the most texels (it is the face); undersides and the wires get fewer.

## Texture style: Steel Ball Run (hand-painted, not photo-real)
Made procedurally in `build_robot.py`, no lighting baked in:
- flat cel tones lit from the upper left, with hard-edged shadows that lean indigo/purple;
- a hard cast-shadow band on the lower part of every limb;
- manga cross-hatching on the shadow side, thick warm-brown ink outlines on every facet edge,
  a thin lighter rim stroke on lit edges, and a little paper grit and ink speckle.

## Roblox
Import `robot_rigged.fbx` with the Studio 3D Importer. Put the four maps in a `SurfaceAppearance`
(ColorMap, NormalMap, RoughnessMap, MetalnessMap). The normal map is OpenGL-style. The scale to match
a 5-stud R15 character is about 3.5 studs per metre. This has not been imported into Studio yet.

## Rebuild
```
python3 tools/build_robot.py                 # model + textures + exports
python3 tools/render_robot.py [dir]          # previews (needs bpy)
python3 tools/make_robot_sheet.py            # previews/sheet.png
```
