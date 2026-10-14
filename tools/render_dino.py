#!/usr/bin/env python3
"""Render preview images of the raptor from assets/dino/dino.blend.

    python3 tools/render_dino.py [out_dir] [--views a,b,c] [--samples N]

Views: side, three_q, front, back, top, head, hand, foot, tail.
"""
import argparse
import math
import os
import sys

import bpy  # noqa: F401
from mathutils import Euler, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VIEWS = {
    # name: (camera location, look-at, focal length)
    "side": ((7.0, -0.05, 1.5), (0, -0.05, 1.12), 50),
    "three_q": ((-4.7, 5.2, 2.6), (0, 0.0, 1.1), 50),
    "front": ((0, 7.0, 1.5), (0, 0, 1.12), 50),
    "back": ((0, -7.0, 1.6), (0, 0, 1.0), 50),
    "top": ((0, -0.2, 8.5), (0, -0.2, 1.0), 50),
    "head": ((-1.6, 3.5, 2.3), (0, 1.55, 1.85), 60),
    "hand": ((-1.2, 2.2, 1.2), (0.3, 0.8, 0.85), 70),
    "foot": ((1.9, 1.4, 0.7), (0.4, -0.05, 0.3), 70),
    "tail": ((-3.6, -4.8, 1.9), (0, -1.4, 0.8), 50),
}


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=os.path.join(ROOT, "assets", "dino", "previews"))
    ap.add_argument("--pose", default="stand")
    ap.add_argument("--views", default="side,three_q,front,back,top,head,hand,foot,tail")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", type=int, default=900)
    ap.add_argument("--blend", default=os.path.join(ROOT, "assets", "dino", "dino.blend"))
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

    bpy.ops.wm.open_mainfile(filepath=args.blend)
    scene = bpy.context.scene
    arm = bpy.data.objects["DinoRig"]

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = args.res
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"

    # backdrop floor
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.001))
    floor = bpy.context.object
    fm = bpy.data.materials.new("floor")
    fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.80, 0.72, 0.56, 1)
    fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    floor.data.materials.append(fm)

    # world + lights
    world = bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.78, 0.84, 0.92, 1)
    bg.inputs["Strength"].default_value = 0.9
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.2
    sun.angle = math.radians(6)
    so = bpy.data.objects.new("sun", sun)
    scene.collection.objects.link(so)
    so.rotation_euler = Euler((math.radians(52), math.radians(8), math.radians(-35)))
    fill = bpy.data.lights.new("fill", "AREA")
    fill.energy = 120
    fill.size = 5
    fo = bpy.data.objects.new("fill", fill)
    scene.collection.objects.link(fo)
    fo.location = (-3, 3, 2.5)
    look_at(fo, (0, 0, 1))

    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    os.makedirs(args.out, exist_ok=True)
    for v in args.views.split(","):
        loc, tgt, fl = VIEWS[v]
        cam.location = Vector(loc)
        cam_data.lens = fl
        look_at(cam, tgt)
        scene.render.filepath = os.path.join(args.out, f"{args.pose}_{v}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)


if __name__ == "__main__":
    main()
