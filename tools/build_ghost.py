#!/usr/bin/env python3
"""Low-poly stone ghost with a zipper seam for Roblox, Steel Ball Run inspired hand-painted texture.
Built in Blender via bpy on the shared pipeline (tools/blocky.py + tools/build_horse.py).

    python3 tools/build_ghost.py        # writes assets/ghost/*   (needs bpy, numpy, pillow)

A tall faceted peanut-shaped body with a curled tail tip, painted oval eyes and an open screaming mouth, a row of
modelled zipper teeth down the front-right side, and two raised arms made of jointed segments ending in
three-fingered claw hands.

Rig names follow R15 so it can be driven like a Roblox character: HumanoidRootPart, UpperTorso (the body),
LowerTorso (the tail, so it can wag), Left/Right UpperArm, LowerArm, Hand. 1 unit = 1 m, +Z up, faces +Y,
tail tip near Z=0, 1.37 m tall ("Left" is -X). One 1024 atlas, one material.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import blocky  # noqa: E402
from blocky import INK, V, aa, add_block, add_loft, col, ellipse_mask, mix, ring, smooth, sphere, tube_pts  # noqa: E402
from build_horse import Part, X, Y, Z  # noqa: E402
from mathutils import Matrix  # noqa: E402

OUT = os.path.join(blocky.bh.ROOT, "assets", "ghost")

# body rows: (z, half width x, half depth y, centre x, centre y)
BODY_ROWS = [(0.30, .13, .12, 0.0, 0.0), (0.52, .215, .17, 0.0, 0.0), (0.88, .275, .215, 0.0, 0.0),
             (1.22, .26, .205, 0.0, 0.0), (1.33, .195, .16, 0.0, 0.0), (1.40, .105, .09, 0.0, 0.0)]
TAIL_ROWS = [(0.0, .012, .012, 0.10, -0.09), (0.10, .045, .045, 0.08, -0.07), (0.20, .09, .085, 0.04, -0.035),
             (0.30, .13, .12, 0.0, 0.0)]
CH = 0.45
ALL_ROWS = TAIL_ROWS[:-1] + BODY_ROWS

SHOULDER, ELBOW, WRIST = (0.235, 0.0, 0.93), (0.44, 0.02, 0.74), (0.58, 0.045, 1.02)
EYE_Z, MOUTH_Z = 1.06, 0.72

BONES = {
    "HumanoidRootPart": ((0, 0, 0.5), (0, 0.15, 0.5), None),
    "UpperTorso": ((0, 0, 0.5), (0, 0, 1.35), "HumanoidRootPart"),
    "LowerTorso": ((0, 0, 0.30), (0.05, -0.04, 0.0), "UpperTorso"),
}
for sx, side in ((1, "Right"), (-1, "Left")):
    BONES[f"{side}UpperArm"] = ((sx * SHOULDER[0], 0, SHOULDER[2]), (sx * ELBOW[0], ELBOW[1], ELBOW[2]), "UpperTorso")
    BONES[f"{side}LowerArm"] = ((sx * ELBOW[0], ELBOW[1], ELBOW[2]), (sx * WRIST[0], WRIST[1], WRIST[2]), f"{side}UpperArm")
    BONES[f"{side}Hand"] = ((sx * WRIST[0], WRIST[1], WRIST[2]), (sx * 0.60, 0.05, 1.20), f"{side}LowerArm")


def sec(r, ch=CH):
    z, hw, hd, cx, cy = r
    return ring(V((cx, cy, z)), X, Y, hw, hd, ch)


def row_at(z):
    """Interpolated (hw, hd, cx, cy) of the body at height z."""
    rows = ALL_ROWS
    for a, b in zip(rows, rows[1:]):
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return tuple(a[k] + (b[k] - a[k]) * t for k in range(1, 5))
    return rows[-1][1:]


def surface(z, phi):
    """Point, outward normal and tangent where a ray at angle phi (0 = front, + toward -X) leaves the body at z."""
    hw, hd, cx, cy = row_at(z)
    poly = [(p.x, p.y) for p in ring(V((cx, cy, z)), X, Y, hw, hd, CH)]
    # ring() lists the octagon in order; ray from the centre
    dx, dy = -math.sin(phi), math.cos(phi)
    best = None
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        ex, ey = x1 - x0, y1 - y0
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            continue
        t = ((x0 - cx) * ey - (y0 - cy) * ex) / den
        u = ((x0 - cx) * dy - (y0 - cy) * dx) / den
        if t > 0 and -1e-6 <= u <= 1 + 1e-6 and (best is None or t < best[0]):
            L = math.hypot(ex, ey)
            best = (t, V((ex / L, ey / L, 0)))
    t, tang = best
    nrm = V((tang.y, -tang.x, 0))
    if nrm.x * dx + nrm.y * dy < 0:
        nrm = -nrm
    return V((cx + dx * t, cy + dy * t, z)), nrm, tang


def segmented(part, p0, p1, n, r_big, r_small, mat, ch=0.25):
    """A jointed pipe: n beads along the line, alternately fat and thin."""
    p0, p1 = V(p0), V(p1)
    pts = [p0 + (p1 - p0) * (i / (2 * n)) for i in range(2 * n + 1)]
    hw = [r_big if i % 2 == 0 else r_small for i in range(len(pts))]
    tube_pts(part, pts, hw, [h * 1.05 for h in hw], mat, ch=ch, cap_mats=("stone_dk", "stone_dk"))


def build_parts():
    P = {}

    def part(name):
        P[name] = Part(name, name)
        return P[name]

    body, tail = part("UpperTorso"), part("LowerTorso")
    add_loft(body, [sec(r) for r in BODY_ROWS], "stone", cap_mats=("CULL", "stone"))
    add_loft(tail, [sec(r) for r in TAIL_ROWS], "stone", cap_mats=("stone", "CULL"))

    # ---- zipper seam: teeth interlock down the front-right side, from the shoulder to the tail ---------
    n = 10
    z_top, z_bot = 1.14, 0.10
    step = (z_top - z_bot) / n
    for i in range(n + 1):
        for side in (-1, 1):
            z = z_top - step * (i + (0.5 if side > 0 else 0.0))
            if z < z_bot:
                continue
            t = (z_top - z) / (z_top - z_bot)
            pos, nrm, tang = surface(z, math.radians(66 - 36 * t))
            theta = math.atan2(tang.y, tang.x)
            add_block(body if z >= 0.30 else tail, pos + tang * (0.027 * side) + nrm * 0.004, (0.046, 0.034, step * 0.8), "zip",
                      rot=Matrix.Rotation(theta, 3, Z))
        z = z_top - step * (i + 0.25)
        if z < z_bot:
            continue
        t = (z_top - z) / (z_top - z_bot)
        pos, nrm, tang = surface(z, math.radians(66 - 36 * t))
        add_block(body if z >= 0.30 else tail, pos + nrm * 0.002, (0.022, 0.028, step * 1.05), "zip_dk",
                  rot=Matrix.Rotation(math.atan2(tang.y, tang.x), 3, Z))

    # ---- arms: ball joints and jointed pipes, hands with three claw fingers + thumb ---------------------
    for sx, side in ((1, "Right"), (-1, "Left")):
        S, E, W = (V((sx * a[0], a[1], a[2])) for a in (SHOULDER, ELBOW, WRIST))
        ua = part(f"{side}UpperArm")
        sphere(ua, S, 0.075, "stone_dk")
        segmented(ua, S, E, 3, 0.058, 0.046, "stone_dk")
        sphere(ua, E, 0.066, "stone_dk")
        la = part(f"{side}LowerArm")
        segmented(la, E, W, 3, 0.056, 0.044, "stone_dk")
        sphere(la, W, 0.062, "stone_dk")
        hand = part(f"{side}Hand")
        palm = W + V((sx * 0.012, 0.005, 0.085))
        sphere(hand, palm, 0.066, "stone")
        for ang, ln1, ln2 in ((-34, .062, .052), (2, .07, .058), (36, .062, .052), (84, .05, .042)):
            a = math.radians(ang)
            d1 = V((sx * math.sin(a), 0.0, math.cos(a)))
            a2 = a + math.radians(18)
            d2 = V((sx * math.sin(a2), 0.0, math.cos(a2)))
            base = palm + d1 * 0.05
            mid = base + d1 * ln1
            tip = mid + d2 * ln2
            tube_pts(hand, [base, mid, tip], [.026, .026, .019], [.026, .026, .019], "stone", ch=0.3,
                     cap_mats=("CULL", "stone"))
            sphere(hand, mid, 0.033, "stone_dk", seg=6, lats=(-45, 0, 45))
    return P


# ----------------------------------------------------------------------------
# Painting: Steel Ball Run cel look in cold stone grey
# ----------------------------------------------------------------------------
TONES = {
    "stone": [col(.84, .83, .91), col(.66, .65, .76), col(.47, .46, .60), col(.30, .28, .44)],
    "stone_dk": [col(.70, .70, .79), col(.54, .54, .65), col(.39, .38, .52), col(.26, .24, .39)],
    "zip": [col(.97, .94, .86), col(.82, .79, .73), col(.60, .56, .58), col(.38, .34, .44)],
    "zip_dk": [col(.30, .27, .34), col(.22, .20, .27), col(.16, .14, .22), col(.11, .09, .16)],
}
HOLE = col(.06, .05, .09)
TOOTH = col(.93, .88, .76)


def toon(c, key, **kw):
    return blocky.toon(c, TONES[key], INK, **kw)


def overlay_face(c, colr, height, rough, metal, lum):
    """Painted eyes (tilted ovals) and the open screaming mouth with a pale lower lip."""
    if c.part != "UpperTorso" or float(c.N.y) < 0.35:
        return colr, height, rough, metal
    x, z = c.x, c.z
    for sx in (-1, 1):
        cx, cz = 0.035 + sx * 0.078, EYE_Z
        tilt = sx * 0.24  # tops lean toward the middle, like a wail
        dx, dz = x - cx, z - cz
        rx = dx * math.cos(tilt) + dz * math.sin(tilt)
        rz = -dx * math.sin(tilt) + dz * math.cos(tilt)
        r = np.hypot(rx / 0.046, rz / 0.072)
        inside = aa((1 - r) * 0.046, c.ppm)
        halo = aa((1.22 - r) * 0.046, c.ppm)
        colr = mix(colr, INK, halo * (1 - inside))
        # a darker top lid shadow and a faint glint low in the hole
        fill = mix(HOLE, col(.14, .12, .22), smooth(-0.03, 0.05, rz))
        colr = mix(colr, fill, inside)
        height = height - 0.8 * inside
    # mouth: tall dark oval, pale beige lip block along the bottom
    mx, mz = 0.035, MOUTH_Z
    r = np.hypot((x - mx) / 0.052, (z - mz) / 0.100)
    inside = aa((1 - r) * 0.052, c.ppm)
    halo = aa((1.2 - r) * 0.052, c.ppm)
    colr = mix(colr, INK, halo * (1 - inside))
    colr = mix(colr, col(.07, .04, .08), inside)
    lip = inside * smooth(mz - 0.048, mz - 0.060, z) * aa(0.040 - np.abs(x - mx), c.ppm)
    colr = mix(colr, TOOTH, lip)
    colr = mix(colr, INK, inside * aa(0.003 - np.abs(z - (mz - 0.054)), c.ppm) * 0.9)
    height = height - 0.8 * inside + 0.5 * lip
    return colr, height, rough, metal


def make_painters():
    def stone(c):
        def ov(c_, colr, h, r, m, lum):
            colr, h, r, m = overlay_face(c_, colr, h, r, m, lum)
            # chisel scratches on the big facets
            if c_.mind > 0.08:
                inset = smooth(0.0026, 0.001, np.abs(c_.ed - 0.016))
                colr = mix(colr, INK, inset * 0.35)
            return colr, h, r, m
        return toon(c, "stone", rough=0.85, overlay=ov)

    return {
        "stone": stone,
        "stone_dk": lambda c: toon(c, "stone_dk", rough=0.8),
        "zip": lambda c: toon(c, "zip", metal=0.45, rough=0.4),
        "zip_dk": lambda c: toon(c, "zip_dk", rough=0.8),
    }


def main():
    blocky.setup("ghost", "GhostRig", "GhostMat", OUT, 1024, BONES, make_painters(),
                 density={"zip": 0.7, "zip_dk": 0.4}, part_density={"UpperTorso": 1.5})
    blocky.build(build_parts(), OUT, "ghost")


if __name__ == "__main__":
    main()
