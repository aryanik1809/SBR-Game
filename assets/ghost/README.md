# Ghost (Roblox-style, Steel Ball Run texture)

Stone-grey ghost with a screaming face, a modelled zipper seam down the front-right side, jointed pipe arms and
three-fingered claw hands. Built in Blender (`tools/build_ghost.py`) for Roblox: low poly, one small atlas.

| | |
| --- | --- |
| Triangles | **1,984** (8 meshes) |
| Texture | one 1024x1024 atlas, one material (colour, normal, roughness, metalness) |
| Height | 1.40 m; 1 unit = 1 m, +Z up, faces +Y |
| Rig | 9 bones with R15 names: `HumanoidRootPart`, `UpperTorso` (body), `LowerTorso` (tail tip, to wag), `Left/Right` `UpperArm`, `LowerArm`, `Hand`. "Left" is -X. |

Files: `ghost.blend`, `ghost_rigged.fbx` (one mesh per part, bound to its bone), `ghost_static.obj/.mtl`
(single mesh), `ghost.glb`, `ghost_color/normal/roughness/metalness.png`, `previews/sheet.png`.

## Optimising choices
- The body is a chamfered 8-sided loft; arms are short pipes with fat/thin beads and faceted ball joints.
- Eyes and mouth are painted, not modelled. The zipper is the only extra geometry (24 small blocks).
- The face part of the body gets the most texels.

## Texture style
Same hand-painted Steel Ball Run look as the robot: flat cel tones lit from the upper left (cold lavender grey),
hard cast-shadow band at the bottom of each part, manga hatching on shadow faces, thick warm-brown ink outlines,
a bevel line inside big facets and some grit and speckle.

## Roblox
Import `ghost_rigged.fbx` with the Studio 3D Importer, then put the four maps in a `SurfaceAppearance`
(ColorMap, NormalMap, RoughnessMap, MetalnessMap). The normal map is OpenGL-style. Not yet imported into Studio
(I can't open Studio from a cloud session). Arms are posed raised in the rest pose.

## Rebuild
```
python3 tools/build_ghost.py                 # model + textures + exports
python3 tools/render_ghost.py [dir]          # previews (needs bpy)
python3 tools/make_ghost_sheet.py            # previews/sheet.png
```
