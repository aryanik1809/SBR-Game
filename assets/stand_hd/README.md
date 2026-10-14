# Stand (high-detail, Steel Ball Run texture)

A detail-first remake of the yellow stand figure: not limited to Roblox budgets, with a fully modelled and
painted face. Built in Blender (`tools/build_stand_hd.py`, body from `tools/build_stand.py`).

- About 2,200 triangles, 15 meshes, 2048x2048 atlas (colour, normal, roughness, metalness); the head gets most texels.
- Face: almond ellipsoid eyeballs with a painted iris, pupil, glint and lash line; heavy slanted lids; a two-part angry
  brow ridge; tapered nose with nostril wings; upper and lower lips over a dark mouth gap; cheekbones, ears, V chin;
  painted brow furrows, forehead creases, under-eye lines, nasolabial folds and cheek hatching.
- Rig: same bone names as the Roblox version (`HumanoidRootPart`, `Head`, `UpperTorso`, ...), nothing depends on
  them. 1 unit = 1 m, +Z up, faces +Y, about 1.7 m tall.

Files: `stand_hd.blend`, `stand_hd_rigged.fbx`, `stand_hd_static.obj/.mtl`, `stand_hd.glb`, the four maps,
`previews/sheet.png`.

The reference image was not available to me when I built this (only my earlier description of it), so the design
is an interpretation. Send the image again and I can match it more closely.

```
python3 tools/build_stand_hd.py
python3 tools/render_stand.py assets/stand_hd/previews --rig StandHDRig --blend assets/stand_hd/stand_hd.blend
```
