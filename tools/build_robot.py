#!/usr/bin/env python3
"""Low-poly Roblox-style robot (purple body, tan armour, green wires) with a Steel Ball Run inspired
hand-painted texture. Built in Blender via bpy, reusing the pipeline in tools/build_horse.py.

    python3 tools/build_robot.py        # writes assets/robot/*   (needs bpy, numpy, pillow)

Made for Roblox:
  * ~2.2k triangles, a single 1024x1024 atlas, one material.
  * Parts and bones use R15 names (Head, UpperTorso, LowerTorso, Left/RightUpperArm, ...LowerArm, ...Hand,
    ...UpperLeg, ...LowerLeg, ...Foot) with the joints where R15 has them, so it drops onto a Humanoid rig.
  * 1 unit = 1 metre, +Z up, faces +Y, feet on Z=0, 1.5 m tall (R15 is ~1.4 m). "Left" is -X.

Texture style (see docs in assets/robot/README.md): flat cel tones with hard-edged indigo shadows,
manga cross-hatching in the shadow, thick warm-brown ink outlines and a little paper grit.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import blocky  # noqa: E402
from blocky import INK, V, aa, add_block, add_loft, col, ellipse_mask, layers, mix, ring, smooth, sphere, tube_pts  # noqa: E402
from build_horse import Part, X, Y, Z  # noqa: E402
from mathutils import Matrix  # noqa: E402

OUT = os.path.join(blocky.bh.ROOT, "assets", "robot")
TAU = math.tau

# ----------------------------------------------------------------------------
# Skeleton (R15 joint layout). "Right" = +X, "Left" = -X; the robot faces +Y.
# ----------------------------------------------------------------------------
# The model is authored in a "design" height space and warped vertically at the end: the legs are
# shortened (the concept's legs are short and stout) and everything above the hips is moved down.
_WARP_IN = [0.0, 0.25, 0.42, 0.635, 1.60]
_WARP_OUT = [0.0, 0.21, 0.345, 0.52, 1.485]


def M(z):
    return float(np.interp(z, _WARP_IN, _WARP_OUT))


BONES = {
    "HumanoidRootPart": ((0, 0, M(0.66)), (0, 0.15, M(0.66)), None),
    "LowerTorso": ((0, 0, M(0.64)), (0, 0, M(0.74)), "HumanoidRootPart"),
    "UpperTorso": ((0, 0, M(0.74)), (0, 0, M(0.98)), "LowerTorso"),
    "Head": ((0, 0, M(0.99)), (0, 0, M(1.46)), "UpperTorso"),
}
for sx, side in ((1, "Right"), (-1, "Left")):
    BONES[f"{side}UpperArm"] = ((sx * 0.21, 0, M(0.92)), (sx * 0.23, 0, M(0.71)), "UpperTorso")
    BONES[f"{side}LowerArm"] = ((sx * 0.23, 0, M(0.71)), (sx * 0.225, 0.02, M(0.52)), f"{side}UpperArm")
    BONES[f"{side}Hand"] = ((sx * 0.225, 0.02, M(0.52)), (sx * 0.225, 0.03, M(0.38)), f"{side}LowerArm")
    BONES[f"{side}UpperLeg"] = ((sx * 0.08, 0, M(0.635)), (sx * 0.125, 0, M(0.42)), "LowerTorso")
    BONES[f"{side}LowerLeg"] = ((sx * 0.125, 0, M(0.42)), (sx * 0.17, 0, M(0.25)), f"{side}UpperLeg")
    BONES[f"{side}Foot"] = ((sx * 0.17, 0, M(0.25)), (sx * 0.17, 0.2, 0.05), f"{side}LowerLeg")


# ----------------------------------------------------------------------------
# Geometry helpers (shared ones live in tools/blocky.py)
# ----------------------------------------------------------------------------
def wire(part, pts, r, mat="green", n=6):
    """Thin 6-sided tube along a bent polyline."""
    P = [V(p) for p in pts]
    secs = []
    for j in range(len(P)):
        t = (P[min(j + 1, len(P) - 1)] - P[max(j - 1, 0)]).normalized()
        u = t.cross(Z if abs(t.z) < 0.95 else X)
        u.normalize()
        v = u.cross(t).normalized()
        secs.append([P[j] + (u * math.cos(TAU * i / n) + v * math.sin(TAU * i / n)) * r for i in range(n)])
    add_loft(part, secs, mat, cap_mats=("green", "green"))


# ----------------------------------------------------------------------------
# The robot
# ----------------------------------------------------------------------------
def build_parts():
    P = {}

    def part(name):
        P[name] = Part(name, name)
        return P[name]

    # ---- pelvis + waist ------------------------------------------------------------------------
    low = part("LowerTorso")
    layers(low, [(0.60, .13, .105), (0.665, .165, .125), (0.735, .14, .115)], "purple")
    add_block(low, V((0, -0.085, 0.665)), (0.17, 0.05, 0.10), "purple")  # rear plate
    # ---- chest, neck, collar -------------------------------------------------------------------------
    up = part("UpperTorso")
    layers(up, [(0.72, .08, .066), (0.78, .08, .066)], "gray", ch=0.35)  # waist cylinder
    layers(up, [(0.78, .135, .11), (0.83, .19, .135), (0.94, .20, .14), (1.0, .15, .115)], "purple", ch=0.4)
    for sx in (-1, 1):
        add_block(up, V((sx * 0.09, 0.133, 0.885)), (0.15, 0.03, 0.115), "purple")  # pec plate
        sphere(up, V((sx * 0.145, 0.105, 0.955)), 0.02, "green", seg=6, lats=(-45, 45))  # collar bead
    layers(up, [(0.995, .058, .056), (1.06, .058, .056)], "gray", ch=0.35, cap_mats=("CULL", "gray"))  # neck

    # ---- head ------------------------------------------------------------------------------------------
    head = part("Head")
    layers(head, [(1.09, .238, .20), (1.33, .244, .205), (1.46, .238, .198), (1.52, .18, .15)], "tan", ch=0.3,
           cap_mats=("CULL", "tan"))
    # chin tray: a thin lip plate with a raised wall on the robot's left (image right), like the concept
    add_block(head, V((0, 0.012, 1.063)), (0.50, 0.45, 0.035), "tan")
    add_block(head, V((-0.243, 0.012, 1.095)), (0.03, 0.45, 0.04), "tan")
    # mouth slot + eye holes + beads are painted (see overlay_head)
    for sx in (-1, 1):
        add_block(head, V((sx * 0.28, -0.012, 1.40)), (0.085, 0.095, 0.095), "green")  # side cube
        for j, y0 in enumerate((-0.042, -0.014, 0.014, 0.042)):
            out = 0.06 + 0.016 * j
            fall = 0.07 + 0.016 * (3 - j)
            p0 = V((sx * 0.288, y0, 1.355))
            p1 = p0 + V((sx * out, y0 * 0.6, -fall * 0.8))
            p2 = p1 + V((sx * (0.055 - 0.009 * j), y0 * 0.8, -0.035))
            p3 = p2 + V((sx * 0.016, y0 * 0.7, -(0.10 + 0.02 * j)))
            wire(head, [p0, p1, p2, p3], 0.0165)

    # ---- arms ----------------------------------------------------------------------------------------------
    for sx, side in ((1, "Right"), (-1, "Left")):
        ua = part(f"{side}UpperArm")
        sphere(ua, V((sx * 0.20, 0, 0.915)), 0.056, "gray")  # shoulder joint
        pad = [ring(V((sx * 0.245, 0, z)), X, Y, hw, hd, 0.42) for z, hw, hd in
               ((0.835, .06, .06), (0.895, .09, .086), (0.965, .086, .082), (1.01, .054, .054))]
        add_loft(ua, pad, "tan", cap_mats=("CULL", "tan"))  # faceted shoulder pad
        tube_pts(ua, [V((sx * 0.225, 0, 0.862)), V((sx * 0.23, 0, 0.745))], [.045, .037], [.047, .039], "purple", ch=0.35)
        la = part(f"{side}LowerArm")
        sphere(la, V((sx * 0.23, 0, 0.715)), 0.05, "gray")
        tube_pts(la, [V((sx * 0.23, 0, 0.675)), V((sx * 0.225, 0.02, 0.525))], [.058, .05], [.062, .054], "tan", ch=0.3)
        hand = part(f"{side}Hand")
        add_block(hand, V((sx * 0.225, 0.03, 0.49)), (0.10, 0.065, 0.088), "tan")  # palm
        for i in range(4):
            fx = sx * (0.225 + (i - 1.5) * 0.0225)
            add_block(hand, V((fx, 0.042, 0.422)), (0.02, 0.028, 0.058), "tan")
            add_block(hand, V((fx, 0.054, 0.375)), (0.019, 0.026, 0.046), "tan", rot=Matrix.Rotation(math.radians(24), 3, X))
        add_block(hand, V((sx * 0.162, 0.035, 0.47)), (0.026, 0.033, 0.072), "tan",
                  rot=Matrix.Rotation(math.radians(20), 3, X) @ Matrix.Rotation(math.radians(-sx * 18), 3, Z))

    # ---- legs ------------------------------------------------------------------------------------------------------
    for sx, side in ((1, "Right"), (-1, "Left")):
        ul = part(f"{side}UpperLeg")
        sphere(ul, V((sx * 0.08, 0, 0.64)), 0.06, "gray")
        tube_pts(ul, [V((sx * 0.085, 0, 0.595)), V((sx * 0.124, 0, 0.455))], [.068, .06], [.07, .062], "purple", ch=0.35)
        ll = part(f"{side}LowerLeg")
        sphere(ll, V((sx * 0.125, 0, 0.42)), 0.056, "gray")
        tube_pts(ll, [V((sx * 0.127, 0, 0.385)), V((sx * 0.17, 0, 0.29))], [.06, .052], [.064, .056], "purple", ch=0.35)
        ft = part(f"{side}Foot")
        sphere(ft, V((sx * 0.172, 0, 0.265)), 0.058, "gray")
        x = sx * 0.172
        boot = [ring(V((x, y, zc)), X, Z, hw, hv, 0.3) for y, hw, hv, zc in
                ((-0.11, .085, .10, .10), (0.0, .092, .10, .10), (0.12, .097, .072, .076), (0.25, .084, .042, .046))]
        add_loft(ft, boot, "tan")
        add_block(ft, V((x, -0.03, 0.155)), (0.175, 0.17, 0.13), "tan")  # ankle collar (overlaps the boot)
        add_block(ft, V((x, 0.06, 0.014)), (0.205, 0.43, 0.03), "tan")  # sole plate

    # vertical warp into final proportions (legs shorter, upper body lowered)
    for p in P.values():
        p.verts = [V((v.x, v.y, M(v.z))) for v in p.verts]
    return P


# ----------------------------------------------------------------------------
# Painting: Steel Ball Run inspired cel shading
# ----------------------------------------------------------------------------
INK = col(.19, .09, .12)  # warm brown-purple ink, never pure black
# tones from lit to deepest shadow; shadows lean indigo like the SBR palette
TONES = {
    "tan": [col(.97, .76, .42), col(.89, .61, .27), col(.74, .43, .24), col(.52, .29, .25)],
    "purple": [col(.68, .38, .74), col(.50, .22, .60), col(.29, .13, .47), col(.18, .08, .34)],
    "green": [col(.38, .84, .38), col(.16, .67, .25), col(.07, .42, .30), col(.04, .25, .24)],
    "gray": [col(.84, .84, .88), col(.56, .57, .62), col(.33, .34, .47), col(.20, .20, .34)],
}
TONES = {
    "tan": [col(.97, .76, .42), col(.89, .61, .27), col(.74, .43, .24), col(.52, .29, .25)],
    "purple": [col(.68, .38, .74), col(.50, .22, .60), col(.29, .13, .47), col(.18, .08, .34)],
    "green": [col(.38, .84, .38), col(.16, .67, .25), col(.07, .42, .30), col(.04, .25, .24)],
    "gray": [col(.84, .84, .88), col(.56, .57, .62), col(.33, .34, .47), col(.20, .20, .34)],
}


def toon(c, key, **kw):
    return blocky.toon(c, TONES[key], INK, **kw)


def overlay_head(c, colr, height, rough, metal, lum):
    """Eye holes, mouth slot and green beads painted on the face of the head."""
    if c.part != "Head" or float(c.N.y) < 0.6:
        return colr, height, rough, metal
    x, z = c.x, c.z
    black = col(.07, .04, .06)
    rim = col(.55, .33, .22)
    for cx, cz, rx, rz in ((0.088, M(1.345), 0.05, 0.066), (-0.076, M(1.34), 0.035, 0.038)):
        r = ellipse_mask(x, z, cx, cz, rx, rz)
        # cut edge: a crisp ink ring, then a lit tan bevel on the upper-left, then the black hole
        bevel = smooth(1.30, 1.14, r) * (1 - smooth(1.14, 1.10, r))
        lit = smooth(-0.6, 0.6, -(x - cx) / rx * 0.6 + (z - cz) / rz * 0.6)
        colr = mix(colr, mix(rim, col(.97, .76, .42), lit), bevel * 0.85)
        ink_r = aa((1.10 - r) * min(rx, rz), c.ppm) * (1 - aa((1.0 - r) * min(rx, rz), c.ppm))
        colr = mix(colr, INK, ink_r)
        hole = aa((1.0 - r) * min(rx, rz), c.ppm)
        colr = mix(colr, black, hole)
        height = height - 0.8 * hole
    # mouth: flat top, rounded bottom, just above the chin tray
    top = M(1.165)
    depth = 0.068 * np.sqrt(np.clip(1 - (x / 0.21) ** 2, 0, 1))
    inside = np.minimum.reduce([top - z, z - (top - depth), 0.21 - np.abs(x)])
    mouth = aa(inside, c.ppm)
    colr = mix(colr, black, mouth)
    height = height - 0.8 * mouth
    # green beads along the lip
    for i in range(6):
        bx = -0.15 + i * 0.06
        r = ellipse_mask(x, z, bx, M(1.19), 0.0115, 0.0115)
        bead = aa((1.0 - r) * 0.0115, c.ppm)
        shade = col(.16, .67, .25) * (0.8 + 0.4 * smooth(-1, 1, -(x - bx) / 0.0115 * 0.5 + (z - M(1.19)) / 0.0115 * 0.5))[..., None]
        colr = mix(colr, shade, bead)
        colr = mix(colr, INK, smooth(1.25, 1.0, r) * (1 - bead) * 0.9)
    return colr, height, rough, metal


def overlay_torso(c, colr, height, rough, metal, lum):
    if c.part != "UpperTorso" or float(c.N.y) < 0.5:
        return colr, height, rough, metal
    x, z = c.x, c.z
    # sternum line and pec under-curves, drawn in ink
    ln = smooth(0.0034, 0.0014, np.abs(x)) * smooth(M(0.82), M(0.86), z) * smooth(M(0.96), M(0.92), z)
    for sx in (-1, 1):
        r = ellipse_mask(x, z, sx * 0.09, M(0.885), 0.08, 0.07)
        arc = smooth(0.06, 0.02, np.abs(r - 1)) * (z < M(0.885))
        ln = np.maximum(ln, arc * 0.9)
    return mix(colr, INK, ln * 0.7), height - 0.3 * ln, rough, metal


def make_painters():
    def tan(c):
        def ov(c_, colr, h, r, m, lum):
            colr, h, r, m = overlay_head(c_, colr, h, r, m, lum)
            # an inset panel line on the big armour faces, like a hand-drawn bevel (not the boots: their blocks overlap)
            if c_.mind > 0.07 and "Foot" not in c_.part:
                inset = smooth(0.0030, 0.0012, np.abs(c_.ed - 0.015))
                colr = mix(colr, INK, inset * 0.55)
            return colr, h, r, m
        return toon(c, "tan", rough=0.6, overlay=ov)

    def purple(c):
        return toon(c, "purple", rough=0.65, overlay=overlay_torso)

    def green(c):
        return toon(c, "green", rough=0.5)

    def gray(c):
        def ov(c_, colr, h, r, m, lum):
            # glossy ball joint: a small hard white highlight where the light hits
            spot = smooth(0.93, 0.97, lum) * smooth(0.03, 0.012, np.abs(c_.ed - 0.014) * 0 + 0.0)
            if lum > 0.8 and c_.mind > 0.02:
                glint = smooth(0.012, 0.004, np.abs(c_.ed - 0.022))
                colr = mix(colr, col(.98, .98, 1.0), glint * 0.7)
            return colr, h, r, m
        return toon(c, "gray", metal=0.55, rough=0.3, overlay=ov)

    return {"tan": tan, "purple": purple, "green": green, "gray": gray}


def main():
    blocky.setup("robot", "RobotRig", "RobotMat", OUT, 1024, BONES, make_painters(),
                 density={"green": 0.6}, part_density={"Head": 1.6, "UpperTorso": 1.1})
    blocky.build(build_parts(), OUT, "robot")


if __name__ == "__main__":
    main()
