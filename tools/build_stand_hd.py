#!/usr/bin/env python3
"""High-detail yellow "stand" figure (not limited to Roblox budgets) with a fully modelled, hand-painted face.

    python3 tools/build_stand_hd.py        # writes assets/stand_hd/*   (needs bpy, numpy, pillow)

Reuses the body from tools/build_stand.py and replaces the head with a detailed one: ellipsoid eyeballs with a painted
iris, pupil and glint set under heavy slanted lids and a two-part angry brow ridge, a bridged nose with nostril wings,
upper and lower lips over a dark mouth gap, cheekbones, ears and a V chin. A 2048 atlas gives the head most texels.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import blocky  # noqa: E402
import build_stand as bs  # noqa: E402
from blocky import INK, V, aa, add_block, add_loft, col, layers, mix, smooth  # noqa: E402
from build_horse import Part, X, Y, Z  # noqa: E402
from mathutils import Matrix  # noqa: E402

OUT = os.path.join(blocky.bh.ROOT, "assets", "stand_hd")

EYE_X, EYE_Z, EYE_Y = 0.086, 1.532, 0.146
EYE_RX, EYE_RZ, EYE_RY = 0.054, 0.027, 0.03
EYE_TILT = 0.30  # outer corner higher
FACE_Y = 0.155  # flat front of the head at eye height


def eyeball(part, c, sx, mat="eye", seg=14):
    """Almond ellipsoid facing +Y, tilted so the outer corner is higher."""
    t = sx * EYE_TILT
    ct, st = math.cos(t), math.sin(t)
    secs = []
    for a in (-72, -44, -16, 16, 44, 72):
        ar = math.radians(a)
        rad, y = math.cos(ar), EYE_RY * math.sin(ar)
        ring = []
        for i in range(seg):
            th = math.tau * i / seg
            px, pz = EYE_RX * rad * math.cos(th), EYE_RZ * rad * math.sin(th)
            ring.append(V((c[0] + px * ct - pz * st, c[1] + y, c[2] + px * st + pz * ct)))
        secs.append(ring)
    add_loft(part, secs, mat)


def rotY(a):
    return Matrix.Rotation(a, 3, Y)


def rotZ(a):
    return Matrix.Rotation(a, 3, Z)


def build_head():
    head = Part("Head", "Head")
    # skull and jaw: stacked rings from the V chin up to a flat top
    layers(head, [(1.335, .035, .045, .035), (1.37, .07, .08, .028), (1.415, .112, .112, .018), (1.47, .15, .138, .008),
                  (1.54, .185, .155, 0.0), (1.60, .198, .16, 0.0), (1.66, .205, .166, 0.0), (1.70, .205, .166, 0.0)],
           "yellow", ch=0.32, cap_mats=("yellow", "yellow"))
    add_block(head, V((0, 0.152, 1.668)), (0.30, 0.03, 0.07), "yellow")  # forehead plate
    for sx in (-1, 1):
        t = sx * EYE_TILT
        eyeball(head, (sx * EYE_X, EYE_Y, EYE_Z), sx)
        # heavy slanted upper lid, thin lower lid, brow ridge in two angled halves (inner ends lower)
        add_block(head, V((sx * (EYE_X + 0.002), 0.166, EYE_Z + 0.026)), (0.128, 0.038, 0.016), "yellow", rot=rotY(-t))
        add_block(head, V((sx * 0.098, 0.15, 1.592)), (0.17, 0.075, 0.042), "yellow", rot=rotY(-t * 1.1))
        # cheekbone and ear
        add_block(head, V((sx * 0.118, 0.14, 1.468)), (0.06, 0.05, 0.034), "yellow", rot=rotZ(sx * 0.35))
        add_block(head, V((sx * 0.212, 0.0, 1.52)), (0.032, 0.07, 0.105), "yellow_dk")
    # nose: tapered bridge, tip, nostril wings
    add_block(head, V((0, 0.172, 1.505)), (0.052, 0.07, 0.125), "yellow", ts=(0.62, 0.7))
    add_block(head, V((0, 0.208, 1.452)), (0.058, 0.064, 0.042), "yellow")
    for sx in (-1, 1):
        add_block(head, V((sx * 0.032, 0.186, 1.447)), (0.03, 0.055, 0.032), "yellow", rot=rotZ(sx * 0.3))
    # mouth: dark gap with upper and lower lips in front of it
    add_block(head, V((0, 0.152, 1.397)), (0.092, 0.03, 0.01), "dark")
    add_block(head, V((0, 0.162, 1.411)), (0.098, 0.05, 0.02), "yellow_dk")
    add_block(head, V((0, 0.16, 1.384)), (0.082, 0.045, 0.019), "yellow_dk")
    return head


# ----------------------------------------------------------------------------
# Painting
# ----------------------------------------------------------------------------
SCLERA = [col(1.0, .98, .90), col(.94, .90, .78), col(.78, .70, .60), col(.52, .44, .46)]
DARK = [col(.16, .08, .08), col(.12, .06, .07), col(.09, .05, .06), col(.06, .03, .05)]
IRIS = col(.55, .30, .06)
IRIS_D = col(.20, .09, .04)
PUPIL = col(.04, .02, .03)


def overlay_head(c, colr, height, rough, metal, lum):
    """Skin details on the front of the head: furrows, creases, cheek hatching, nasolabial lines, mouth corners."""
    if c.part != "Head" or float(c.N.y) < 0.3:
        return colr, height, rough, metal
    x, z = c.x, c.z
    ln = np.zeros_like(x)
    # furrows between the brows and creases across the forehead plate
    for fx in (-0.014, 0.014):
        ln = np.maximum(ln, aa(np.minimum(0.0022 - np.abs(x - fx), 0.03 - np.abs(z - 1.60)), c.ppm))
    for k in range(3):
        ln = np.maximum(ln, aa(np.minimum(0.0016 - np.abs(z - (1.665 + k * 0.012)), 0.09 - np.abs(x)), c.ppm) * 0.7)
    for sx in (-1, 1):
        # nasolabial fold: a curved line from the nostril wing around the mouth
        r = np.hypot(x - sx * 0.02, z - 1.43)
        fold = aa(0.0022 - np.abs(r - 0.075), c.ppm)
        mask = (sx * (x - sx * 0.02) > 0.0) & (z < 1.455) & (z > 1.385)
        ln = np.maximum(ln, fold * mask * 0.9)
        # bags under the eye and cheek hatching (short parallel strokes)
        under = aa(np.minimum(0.0017 - np.abs(z - (1.495 - (np.abs(x) - 0.086) * 0.3)), 0.05 - np.abs(x - sx * 0.09)), c.ppm)
        ln = np.maximum(ln, under * 0.8)
        hx = (x * 0.7 + z * sx * 0.7) / 0.011
        hatch = (np.abs(hx - np.floor(hx) - 0.5) < 0.13) & (np.abs(x - sx * 0.14) < 0.04) & (z < 1.485) & (z > 1.43)
        ln = np.maximum(ln, hatch * 0.55)
        # mouth corner
        ln = np.maximum(ln, aa(np.minimum(0.0016 - np.abs(z - 1.397), 0.012 - np.abs(x - sx * 0.052)), c.ppm) * 0.9)
    colr = mix(colr, INK, np.clip(ln, 0, 1) * 0.75)
    return colr, height - 0.35 * ln, rough, metal


def overlay_eye(c, colr, height, rough, metal, lum):
    """Painted iris, pupil, glint and lid shadow on the eyeball (world-space, facing +Y)."""
    if float(c.N.y) < 0.05:
        return colr, height, rough, metal
    sx = 1 if float(np.mean(c.x)) > 0 else -1
    t = sx * EYE_TILT
    dx, dz = c.x - sx * EYE_X, c.z - EYE_Z
    u = dx * math.cos(t) + dz * math.sin(t)
    v = -dx * math.sin(t) + dz * math.cos(t)
    iu = u + 0.009  # the iris sits toward the inner corner
    r = np.hypot(iu, v)
    iris = aa(0.0185 - r, c.ppm)
    colr = mix(colr, mix(IRIS, IRIS_D, smooth(0.004, 0.0185, r)), iris)
    colr = mix(colr, INK, aa(0.0022 - np.abs(r - 0.0185), c.ppm) * 0.9)
    pupil = aa(0.0072 - r, c.ppm)
    colr = mix(colr, PUPIL, pupil)
    glint = aa(0.0028 - np.hypot(iu + 0.006, v - 0.007), c.ppm)
    colr = mix(colr, col(1, 1, 1), glint)
    # lid shadow across the top third of the eye
    shade = smooth(0.002, 0.014, v)
    colr = colr * (1 - 0.34 * shade)[..., None]
    re = np.hypot(u / EYE_RX, v / EYE_RZ)
    colr = mix(colr, INK, smooth(0.80, 0.96, re) * 0.85)  # dark lash line around the eye
    return colr, height - 0.3 * iris, rough, metal


def make_painters():
    base = bs.make_painters()

    def eye(c):
        # no per-facet outline on the eyeball: a smooth painted eye reads far better than a spoked one
        shade = 0.72 + 0.28 * float(np.clip(c.N.y, 0, 1))
        colr = np.broadcast_to(SCLERA[0] * shade, c.x.shape + (3,)).copy().astype(np.float32)
        colr = colr * (0.97 + 0.03 * blocky.fbm(c.x * 90, c.z * 90, c.y * 90, c.seed, 1))[..., None]
        height = np.full_like(c.x, 0.5)
        rough = np.full_like(c.x, 0.25)
        metal = np.zeros_like(c.x)
        colr, height, rough, metal = overlay_eye(c, colr, height, rough, metal, 0.0)
        # soft ink edge only where the eyeball meets the lids (its outer rim)
        edge = smooth(0.004, 0.0, c.ed) * 0.0
        return np.clip(colr, 0, 1), height, rough, metal

    base["eye"] = eye
    base["dark"] = lambda c: blocky.toon(c, DARK, INK, rough=0.7)
    return base


def main():
    bs.overlay_head = overlay_head  # make_painters() resolves this at call time
    parts = bs.build_parts()
    parts["Head"] = build_head()
    blocky.setup("stand_hd", "StandHDRig", "StandHDMat", OUT, 2048, bs.BONES, make_painters(),
                 density={"gold": 0.8, "eye": 2.4, "dark": 0.4},
                 part_density={"Head": 2.2, "UpperTorso": 1.3, "LeftLowerArm": 1.2, "RightLowerArm": 1.2})
    blocky.build(parts, OUT, "stand_hd")


if __name__ == "__main__":
    main()
