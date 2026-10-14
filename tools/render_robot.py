#!/usr/bin/env python3
"""Render preview images of the robot from assets/robot/robot.blend.

    python3 tools/render_robot.py [out_dir] [--views a,b,c] [--samples N]

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
    "front": ((0, 3.6, 0.86), (0, 0, 0.78), 50),
    "three_q": ((-2.5, 2.7, 1.3), (0, 0, 0.76), 50),
    "side": ((3.6, 0.0, 0.86), (0, 0, 0.78), 50),
    "back": ((0, -3.6, 0.9), (0, 0, 0.78), 50),
    "three_q_back": ((2.5, -2.7, 1.3), (0, 0, 0.76), 50),
    "head": ((-0.9, 1.5, 1.4), (0, 0, 1.28), 55),
    "shoulder": ((-0.5, 0.95, 0.95), (0.2, 0.0, 0.80), 55),
    "hand": ((0.75, 0.55, 0.50), (0.225, 0.03, 0.43), 60),
    "foot": ((0.8, 0.9, 0.35), (0.17, 0.03, 0.18), 55),
    "wires": ((1.0, 1.2, 1.3), (0.3, 0, 1.28), 55),
}


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def apply_pose(arm, name):
    """Quick rig check: a few joint rotations (degrees) in each bone's local XYZ."""
    import math as _m
    poses = {
        "wave": {"RightUpperArm": (0, 0, -150), "RightLowerArm": (-30, 0, 0), "LeftUpperLeg": (-35, 0, 0),
                 "LeftLowerLeg": (55, 0, 0), "Head": (0, 0, 18), "UpperTorso": (0, 0, -8), "LeftUpperArm": (25, 0, 0),
                 "LeftLowerArm": (-45, 0, 0)},
    }
    for bone, rot in poses.get(name, {}).items():
        pb = arm.pose.bones[bone]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = tuple(_m.radians(a) for a in rot)
    bpy.context.view_layer.update()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default=os.path.join(ROOT, "assets", "robot", "previews"))
    ap.add_argument("--pose", default="stand")
    ap.add_argument("--views", default="front,three_q,side,back,three_q_back,head,shoulder,hand,foot,wires")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", type=int, default=900)
    ap.add_argument("--blend", default=os.path.join(ROOT, "assets", "robot", "robot.blend"))
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

    bpy.ops.wm.open_mainfile(filepath=args.blend)
    scene = bpy.context.scene
    arm = bpy.data.objects["RobotRig"]

    if args.pose != "stand":
        apply_pose(arm, args.pose)

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
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.80, 0.70, 0.52, 1)
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
