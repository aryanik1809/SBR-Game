#!/usr/bin/env python3
"""Low-poly yellow "stand" figure for Roblox with a Steel Ball Run inspired hand-painted texture.
Built in Blender via bpy on the shared pipeline (tools/blocky.py + tools/build_horse.py).

    python3 tools/build_stand.py        # writes assets/stand/*   (needs bpy, numpy, pillow)

Same treatment as the robot: R15 part and bone names (Head, UpperTorso, LowerTorso, Left/Right UpperArm ...
Foot), one 1024 atlas, ~2k triangles, 1 unit = 1 m, +Z up, faces +Y, feet on Z=0 ("Left" is -X). 1.7 m tall:
a heroic, broad-shouldered figure a little bigger than an R15 avatar.

The Steel Ball Run look: flat cel tones lit from the upper left with hard-edged shadows, manga hatching,
thick warm ink outlines; details (eyes, brow, muscle lines, slots) are painted rather than modelled.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import blocky  # noqa: E402
from blocky import INK, V, aa, add_block, add_loft, col, disc, ellipse_mask, heart_outline, layers, mix, prism, ring, smooth, tube_pts  # noqa: E402
from build_horse import Part, X, Y, Z  # noqa: E402
from mathutils import Matrix  # noqa: E402

OUT = os.path.join(blocky.bh.ROOT, "assets", "stand")
TAU = math.tau

# ----------------------------------------------------------------------------
# Skeleton (R15 layout)
# ----------------------------------------------------------------------------
BONES = {
    "HumanoidRootPart": ((0, 0, 0.76), (0, 0.15, 0.76), None),
    "LowerTorso": ((0, 0, 0.74), (0, 0, 0.86), "HumanoidRootPart"),
    "UpperTorso": ((0, 0, 0.86), (0, 0, 1.30), "LowerTorso"),
    "Head": ((0, 0, 1.32), (0, 0, 1.70), "UpperTorso"),
}
for sx, side in ((1, "Right"), (-1, "Left")):
    BONES[f"{side}UpperArm"] = ((sx * 0.32, 0, 1.22), (sx * 0.335, 0, 0.96), "UpperTorso")
    BONES[f"{side}LowerArm"] = ((sx * 0.335, 0, 0.96), (sx * 0.335, 0.01, 0.66), f"{side}UpperArm")
    BONES[f"{side}Hand"] = ((sx * 0.335, 0.01, 0.66), (sx * 0.335, 0.02, 0.50), f"{side}LowerArm")
    BONES[f"{side}UpperLeg"] = ((sx * 0.105, 0, 0.76), (sx * 0.11, 0, 0.47), "LowerTorso")
    BONES[f"{side}LowerLeg"] = ((sx * 0.11, 0, 0.47), (sx * 0.115, 0, 0.14), f"{side}UpperLeg")
    BONES[f"{side}Foot"] = ((sx * 0.115, 0, 0.14), (sx * 0.115, 0.18, 0.05), f"{side}LowerLeg")

ARM_X = 0.335
BOX_Z = (0.95, 0.78)  # beige forearm box: top / bottom
KNEE_Z = 0.465


def d_outline(w, h, n=8):
    """The 'D' of the knee plates: flat on the left, rounded on the right, as (x, z) pairs."""
    pts = [(-w / 2, -h / 2), (-w / 2, h / 2), (0, h / 2)]
    for i in range(1, n):
        a = math.pi / 2 - math.pi * i / n
        pts.append((w / 2 * math.cos(a) * 1.0, h / 2 * math.sin(a)))
    pts.append((0, -h / 2))
    return pts


# ----------------------------------------------------------------------------
# The figure
# ----------------------------------------------------------------------------
def build_parts():
    P = {}

    def part(name):
        P[name] = Part(name, name)
        return P[name]

    # ---- pelvis + belt ------------------------------------------------------------------------------
    low = part("LowerTorso")
    layers(low, [(0.66, .17, .105), (0.72, .205, .125), (0.79, .20, .12)], "yellow", ch=0.3)
    layers(low, [(0.785, .21, .128), (0.865, .21, .128)], "beige_dk", ch=0.25)  # belt
    prism(low, heart_outline(0.14, 0.13), V((0, 0.136, 0.822)), X, Z, 0.022, "beige")  # heart buckle
    add_block(low, V((0, -0.125, 0.78)), (0.13, 0.03, 0.07), "beige")  # back clasp

    # ---- chest, straps, neck ---------------------------------------------------------------------------------
    up = part("UpperTorso")
    layers(up, [(0.86, .175, .105), (0.93, .22, .12), (1.17, .25, .132), (1.285, .225, .115)], "yellow", ch=0.35)
    for sx in (-1, 1):
        for face in (1, -1):  # front and back straps, each in four stacked blocks
            y = face * 0.152
            top, bot = 1.27, 0.89
            n = 4
            step = (top - bot) / n
            for k in range(n):
                zc = top - step * (k + 0.5)
                add_block(up, V((sx * 0.187, y, zc)), (0.072, 0.034, step - 0.012), "beige")
    layers(up, [(1.275, .078, .072), (1.35, .075, .07)], "yellow_dk", ch=0.3, cap_mats=("CULL", "yellow_dk"))  # neck

    # ---- head: tall angular helmet, overhanging brow, V chin ---------------------------------------------------------
    head = part("Head")
    layers(head, [(1.70, .205, .168, 0.0), (1.585, .202, .168, 0.0), (1.50, .185, .152, 0.004),
                  (1.42, .13, .125, 0.01), (1.335, .05, .075, 0.02)], "yellow", ch=0.18, cap_mats=("yellow", "yellow"))
    add_block(head, V((0, 0.13, 1.60)), (0.41, 0.115, 0.095), "yellow")  # brow overhang
    add_block(head, V((0, 0.148, 1.465)), (0.045, 0.05, 0.075), "yellow")  # nose ridge
    # slope the top: front edge lower than the back, like the concept's wedge
    head.verts = [V((v.x, v.y, v.z - 0.075 * (v.y + 0.17) / 0.34)) if v.z > 1.69 else v for v in head.verts]

    # ---- arms --------------------------------------------------------------------------------------------------------------
    for sx, side in ((1, "Right"), (-1, "Left")):
        ua = part(f"{side}UpperArm")
        cap = [ring(V((sx * 0.31, 0, z)), X, Y, hw, hd, 0.4) for z, hw, hd in
               ((1.115, .088, .09), (1.19, .125, .12), (1.265, .115, .11), (1.305, .07, .07))]
        add_loft(ua, cap, "yellow", cap_mats=("CULL", "yellow"))  # shoulder cap
        disc(ua, V((sx * 0.405, 0, 1.235)), V((sx * 0.92, 0, 0.39)), 0.082, 0.03, "gold", n=24, scallop=0.12)  # rosette
        disc(ua, V((sx * 0.425, 0, 1.243)), V((sx * 0.92, 0, 0.39)), 0.046, 0.02, "gold", n=16)
        tube_pts(ua, [V((sx * ARM_X, 0, 1.17)), V((sx * ARM_X, 0, 0.955))], [.078, .075], [.088, .085], "yellow", ch=0.25)
        la = part(f"{side}LowerArm")
        zc = (BOX_Z[0] + BOX_Z[1]) / 2
        add_block(la, V((sx * ARM_X, 0.005, zc)), (0.176, 0.19, BOX_Z[0] - BOX_Z[1]), "beige")  # forearm box with a slot
        tube_pts(la, [V((sx * ARM_X, 0.008, 0.785)), V((sx * ARM_X, 0.012, 0.655))], [.07, .068], [.08, .078], "yellow", ch=0.25)
        disc(la, V((sx * (ARM_X + 0.074), 0.008, 0.715)), V((sx, 0, 0)), 0.044, 0.024, "gold", n=16, scallop=0.1)
        hand = part(f"{side}Hand")
        add_block(hand, V((sx * ARM_X, 0.018, 0.585)), (0.15, 0.17, 0.145), "yellow")  # fist
        add_block(hand, V((sx * ARM_X, 0.11, 0.60)), (0.13, 0.04, 0.06), "yellow")  # knuckle row
        add_block(hand, V((sx * (ARM_X - 0.095), 0.045, 0.60)), (0.045, 0.1, 0.075), "yellow",
                  rot=Matrix.Rotation(math.radians(-sx * 12), 3, Z))  # thumb

    # ---- legs ------------------------------------------------------------------------------------------------------------------
    for sx, side in ((1, "Right"), (-1, "Left")):
        ul = part(f"{side}UpperLeg")
        tube_pts(ul, [V((sx * 0.105, 0, 0.765)), V((sx * 0.11, 0, 0.52))], [.105, .098], [.115, .108], "yellow", ch=0.25)
        ll = part(f"{side}LowerLeg")
        add_block(ll, V((sx * 0.11, 0, KNEE_Z + 0.005)), (0.205, 0.225, 0.115), "yellow")  # knee block
        prism(ll, d_outline(0.085, 0.095), V((sx * 0.11, 0.1195, KNEE_Z + 0.012)), X, Z, 0.022, "yellow")  # D plate
        disc(ll, V((sx * 0.222, 0.0, KNEE_Z)), V((sx, 0, 0)), 0.05, 0.028, "gold", n=16, scallop=0.1)
        tube_pts(ll, [V((sx * 0.11, 0, 0.43)), V((sx * 0.115, 0, 0.16))], [.092, .078], [.105, .09], "yellow", ch=0.25)
        ft = part(f"{side}Foot")
        x = sx * 0.115
        boot = [ring(V((x, y, zc)), X, Z, hw, hv, 0.3) for y, hw, hv, zc in
                ((-0.09, .08, .075, .075), (0.02, .086, .075, .075), (0.12, .09, .05, .055), (0.19, .077, .03, .036))]
        add_loft(ft, boot, "yellow")
        add_block(ft, V((x, -0.02, 0.12)), (0.17, 0.17, 0.07), "yellow")  # ankle collar
        add_block(ft, V((x, 0.04, 0.012)), (0.19, 0.31, 0.026), "yellow_dk")  # sole slab
    return P


# ----------------------------------------------------------------------------
# Painting: same Steel Ball Run cel look, in yellow
# ----------------------------------------------------------------------------
TONES = {
    "yellow": [col(1.00, .91, .36), col(.97, .79, .08), col(.82, .58, .13), col(.54, .34, .26)],
    "yellow_dk": [col(.90, .70, .10), col(.78, .55, .08), col(.62, .40, .14), col(.42, .26, .24)],
    "beige": [col(.95, .90, .70), col(.83, .74, .52), col(.63, .52, .42), col(.40, .31, .35)],
    "beige_dk": [col(.78, .66, .38), col(.64, .52, .26), col(.50, .38, .26), col(.34, .24, .28)],
    "gold": [col(1.00, .82, .22), col(.94, .67, .05), col(.74, .45, .08), col(.47, .27, .18)],
}
SLOT = col(.26, .17, .07)
EYE_W = col(.96, .94, .86)
BROWN = col(.22, .12, .06)


def toon(c, key, **kw):
    return blocky.toon(c, TONES[key], INK, **kw)


def slot_rect(c, colr, height, cx, cz, hw, hh, depth_axis):
    """A dark rectangular window, painted in world coordinates on faces whose normal is `depth_axis` (x or y)."""
    if depth_axis == "y":
        if float(c.N.y) < 0.6:
            return colr, height
        u = c.x - cx
    else:
        if abs(float(c.N.x)) < 0.6:
            return colr, height
        u = c.y - cx
    inside = np.minimum(hw - np.abs(u), hh - np.abs(c.z - cz))
    m = aa(inside, c.ppm)
    # darker toward the top inner edge, like a recess
    shade = SLOT * (0.75 + 0.5 * smooth(-hh, hh, -(c.z - cz)))[..., None]
    ring_ink = aa(inside + 0.006, c.ppm) * (1 - m)
    colr = mix(colr, INK, ring_ink * 0.9)
    colr = mix(colr, shade, m)
    return colr, height - 0.7 * m


def overlay_head(c, colr, height, rough, metal, lum):
    if c.part != "Head" or float(c.N.y) < 0.45:
        return colr, height, rough, metal
    x, z = c.x, c.z
    for sx in (-1, 1):
        # slanted almond eye under the brow: white, dark iris, heavy upper lid
        cx, cz = sx * 0.078, 1.508
        tilt = sx * 0.28  # outer corner higher: an angry look
        dx, dz = x - cx, z - cz
        rx_, rz_ = dx * math.cos(tilt) + dz * math.sin(tilt), -dx * math.sin(tilt) + dz * math.cos(tilt)
        r = np.hypot(rx_ / 0.036, rz_ / 0.0145)
        white = aa((1 - r) * 0.0145, c.ppm)
        colr = mix(colr, EYE_W, white)
        iris = aa((0.0125 - np.hypot(rx_ + sx * 0.002, rz_ - 0.001)), c.ppm) * white
        colr = mix(colr, col(.12, .08, .06), iris)
        lid = aa((0.0105 - (rz_ - 0.006)) * 1.0, c.ppm) * white  # lid shadow over the top of the eye
        colr = mix(colr, mix(colr, BROWN, 0.85), lid * 0.7)
        ring_ink = aa((1.18 - r) * 0.0145, c.ppm) * (1 - aa((1.0 - r) * 0.0145, c.ppm))
        colr = mix(colr, INK, ring_ink)
        # brow: a slanted dark bar above the eye, thickest at the outer end
        bx, bz = x - sx * 0.082, z - 1.545
        ang = -sx * 0.30
        u = bx * math.cos(ang) - bz * math.sin(ang)
        v = bx * math.sin(ang) + bz * math.cos(ang)
        thick = 0.0085 + 0.004 * smooth(-0.045, 0.045, sx * (x - sx * 0.082) * -1)
        brow = aa(np.minimum(0.05 - np.abs(u), thick - np.abs(v)), c.ppm)
        colr = mix(colr, BROWN, brow)
    # a thin mouth line near the chin and a nose-bridge line
    mouth = aa(np.minimum(0.04 - np.abs(x), 0.0028 - np.abs(z - 1.392)), c.ppm)
    colr = mix(colr, BROWN, mouth * 0.8)
    nose = aa(np.minimum(0.0025 - np.abs(x - 0.022), 0.04 - np.abs(z - 1.47)), c.ppm)
    colr = mix(colr, BROWN, nose * 0.5)
    return colr, height, rough, metal


def overlay_chest(c, colr, height, rough, metal, lum):
    if c.part != "UpperTorso" or float(c.N.y) < 0.5:
        return colr, height, rough, metal
    x, z = c.x, c.z
    ln = smooth(0.0032, 0.0012, np.abs(x)) * smooth(0.93, 0.97, z) * smooth(1.17, 1.13, z)  # sternum
    for sx in (-1, 1):
        r = ellipse_mask(x, z, sx * 0.085, 1.07, 0.088, 0.075)
        ln = np.maximum(ln, smooth(0.06, 0.02, np.abs(r - 1)) * (z < 1.07) * 0.9)  # under-pec curve
        for k in range(3):  # abs: short horizontal bars either side of the centre line
            zz = 0.995 - k * 0.04 - 0.07
            ln = np.maximum(ln, smooth(0.0028, 0.0011, np.abs(z - zz)) * smooth(0.075, 0.07, np.abs(x)) * smooth(0.01, 0.014, np.abs(x)) * 0.8)
    return mix(colr, INK, ln * 0.65), height - 0.3 * ln, rough, metal


def overlay_arm(c, colr, height, rough, metal, lum):
    """Slot windows on the beige forearm boxes (front and outer faces) + hand finger lines."""
    if c.part.endswith("LowerArm"):
        sx = 1 if c.part.startswith("Right") else -1
        zc = (BOX_Z[0] + BOX_Z[1]) / 2
        if c.mind > 0.1:
            colr, height = slot_rect(c, colr, height, sx * ARM_X, zc, 0.019, 0.047, "y")
            colr, height = slot_rect(c, colr, height, 0.005, zc, 0.019, 0.047, "x")
    elif c.part.endswith("Hand") and float(c.N.y) > 0.5:
        sx = 1 if c.part.startswith("Right") else -1
        for k in range(3):
            ln = smooth(0.0022, 0.0009, np.abs(c.x - sx * (ARM_X - 0.037 + k * 0.037))) * smooth(0.60, 0.575, c.z) * (c.z > 0.52)
            colr = mix(colr, INK, ln * 0.7)
    return colr, height, rough, metal


def overlay_leg(c, colr, height, rough, metal, lum):
    """The vertical slot below each knee's D plate."""
    if c.part.endswith("LowerLeg") and float(c.N.y) > 0.6:
        sx = 1 if c.part.startswith("Right") else -1
        colr, height = slot_rect(c, colr, height, sx * 0.11, 0.375, 0.0135, 0.052, "y")
    return colr, height, rough, metal


def gold_overlay(c, colr, height, rough, metal, lum):
    """Rosette discs: a concentric ink ring and a little petal shading."""
    if c.mind < 0.02:
        return colr, height, rough, metal
    cu, cv = (c.pu.min() + c.pu.max()) / 2, (c.pv.min() + c.pv.max()) / 2
    R = max(0.5 * min(c.pu.max() - c.pu.min(), c.pv.max() - c.pv.min()), 1e-3)
    r = np.hypot(c.pu - cu, c.pv - cv) / R
    ang = np.arctan2(c.pv - cv, c.pu - cu)
    ring_m = smooth(0.05, 0.015, np.abs(r - 0.62))
    petals = smooth(0.0, 0.12, np.sin(ang * 12)) * smooth(0.95, 0.7, r) * smooth(0.55, 0.7, r)
    colr = mix(colr, INK, ring_m * 0.55)
    colr = colr * (1 - 0.14 * petals)[..., None]
    return colr, height, rough, metal


def make_painters():
    def yellow(c):
        def ov(c_, colr, h, r, m, lum):
            colr, h, r, m = overlay_head(c_, colr, h, r, m, lum)
            colr, h, r, m = overlay_chest(c_, colr, h, r, m, lum)
            colr, h, r, m = overlay_arm(c_, colr, h, r, m, lum)
            colr, h, r, m = overlay_leg(c_, colr, h, r, m, lum)
            # a hand-drawn bevel line inside the big flat faces
            if c_.mind > 0.09 and "Foot" not in c_.part:
                inset = smooth(0.0030, 0.0012, np.abs(c_.ed - 0.014))
                colr = mix(colr, INK, inset * 0.45)
            return colr, h, r, m
        return toon(c, "yellow", rough=0.55, overlay=ov)

    def beige(c):
        def ov(c_, colr, h, r, m, lum):
            colr, h, r, m = overlay_arm(c_, colr, h, r, m, lum)
            return colr, h, r, m
        return toon(c, "beige", rough=0.7, overlay=ov)

    return {
        "yellow": yellow,
        "yellow_dk": lambda c: toon(c, "yellow_dk", rough=0.6),
        "beige": beige,
        "beige_dk": lambda c: toon(c, "beige_dk", rough=0.7),
        "gold": lambda c: toon(c, "gold", metal=0.35, rough=0.4, overlay=gold_overlay),
    }


def main():
    blocky.setup("stand", "StandRig", "StandMat", OUT, 1024, BONES, make_painters(),
                 density={"gold": 0.8}, part_density={"Head": 1.5, "UpperTorso": 1.2, "LeftLowerArm": 1.2, "RightLowerArm": 1.2})
    blocky.build(build_parts(), OUT, "stand")


if __name__ == "__main__":
    main()
