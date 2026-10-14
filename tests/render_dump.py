#!/usr/bin/env python3
"""Render the parts dumped by `python3 tests/run.py horse_model dump` as flat-coloured boxes.

    python3 tests/run.py horse_model dump > /tmp/rig.json
    python3 tests/render_dump.py /tmp/rig.json out_dir [view ...]      (needs bpy)

Roblox axes (y up, forward = -z) are mapped to Blender (z up, forward = +y).
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

src, out = sys.argv[1], sys.argv[2]
views = sys.argv[3:] or ["three_q", "side"]
parts = json.load(open(src))

bpy.ops.wm.read_factory_settings(use_empty=True)
P = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))  # roblox -> blender


def lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


mats = {}
meshes = {}
verts = [(x, y, z) for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)]
faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
for p in parts:
    key = (round(p["c"][0], 3), round(p["c"][1], 3), round(p["c"][2], 3), p["m"])
    if key not in mats:
        m = bpy.data.materials.new(str(key))
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (lin(p["c"][0]), lin(p["c"][1]), lin(p["c"][2]), 1)
        b.inputs["Roughness"].default_value = 0.35 if "Metal" in p["m"] else 0.75
        b.inputs["Metallic"].default_value = 0.8 if "Metal" in p["m"] else 0.0
        mats[key] = m
        mesh = bpy.data.meshes.new("cube")  # one mesh per colour so each box keeps its own material
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        mesh.materials.append(m)
        meshes[key] = mesh
    ob = bpy.data.objects.new(p["n"], meshes[key])
    r = p["r"]
    R = Matrix(((r[0], r[1], r[2]), (r[3], r[4], r[5]), (r[6], r[7], r[8])))
    Rb = P @ R @ P.inverted()
    pos = P @ Vector(p["p"])
    s = P @ Vector(p["s"])
    # box size is along the *part's* local axes (x, y, z); map them through the part rotation
    M = Matrix.Translation(pos) @ Rb.to_4x4() @ Matrix.Diagonal((p["s"][0], p["s"][2], p["s"][1], 1))
    ob.matrix_world = M
    bpy.context.scene.collection.objects.link(ob)

sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.samples = 48
sc.cycles.use_denoising = True
sc.render.resolution_x = sc.render.resolution_y = 900
sc.view_settings.view_transform = "Standard"
w = bpy.data.worlds.new("w")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.78, 0.84, 0.92, 1)
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.5
so = bpy.data.objects.new("sun", sun)
sc.collection.objects.link(so)
so.rotation_euler = (math.radians(50), 0, math.radians(-35))
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
fm = bpy.data.materials.new("f")
fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.5, 0.36, 0.2, 1)
bpy.context.object.data.materials.append(fm)
cam_d = bpy.data.cameras.new("c")
cam = bpy.data.objects.new("c", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
cam_d.lens = 50
VIEWS = {"three_q": ((13, 13, 9), (0, 0, 3.4)), "side": ((17, 0.5, 4.2), (0, 0, 3.4)),
         "front": ((0.5, 17, 4.5), (0, 0, 3.4)), "top": ((6, 8, 17), (0, 0, 3)),
         "game": ((0, 12 * 0.64 * 4.5, 12 * 0.77 * 4.5), (0, 0, 2.5))}
os.makedirs(out, exist_ok=True)
for v in views:
    loc, tgt = VIEWS[v]
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(tgt) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(out, f"rig_{v}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", sc.render.filepath)
