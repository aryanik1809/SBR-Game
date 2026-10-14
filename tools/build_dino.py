#!/usr/bin/env python3
"""Build the teal/blue faceted raptor from the concept sheet in Blender, with a painted PBR atlas.

    python3 tools/build_dino.py          # writes assets/dino/*   (needs bpy, numpy, pillow)

Reuses the geometry / atlas / bake / rig / export pipeline of tools/build_horse.py. Model space matches
the horse: 1 unit = 1 metre, +Z up, faces +Y, feet on Z=0. About 2.3 m tall to the crest and 4 m nose to
tail tip, i.e. a little bigger than the horse.

Outputs (assets/dino/): dino.blend, dino_rigged.fbx, dino_static.obj/.mtl, dino.glb and the four
dino_{color,normal,roughness,metalness}.png maps.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import build_horse as bh  # noqa: E402  (imports bpy)
from build_horse import Part, X, Y, Z, add_block, add_loft, col, fbm, finish, frame_z, mix, ring, smooth  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

OUT = os.path.join(bh.ROOT, "assets", "dino")
bh.OUT = OUT
bh.NAME = "dino"
bh.RIG_NAME = "DinoRig"
bh.MAT_NAME = "DinoMat"
bh.ATLAS = int(os.environ.get("DINO_ATLAS", "2048"))

V = Vector
TAU = math.tau

# ----------------------------------------------------------------------------
# Skeleton + body path (y forward, z up; the body is symmetric about x = 0)
# ----------------------------------------------------------------------------
# spine centre line from the rear of the hips, over the chest, up the neck: (y, z, half-width, half-height)
SPINE = [(-0.28, 1.47, .30, .36), (0.10, 1.46, .42, .44), (0.50, 1.47, .42, .44), (0.85, 1.50, .36, .39),
         (1.00, 1.68, .26, .28), (1.18, 1.90, .20, .22), (1.30, 2.04, .19, .21)]
# tail centre line: sweeps back, curls down toward the ground and hooks forward at the tip
TAIL = [(-0.28, 1.47, .30, .36), (-0.70, 1.50, .27, .32), (-1.20, 1.42, .21, .25), (-1.62, 1.20, .155, .19),
        (-1.90, 0.88, .11, .135), (-2.05, 0.55, .07, .088), (-2.10, 0.25, .038, .048), (-1.93, 0.16, .009, .012)]

BONES = {
    # name: (head, tail, parent)
    "Root": ((0, 0, 0.9), (0, -0.3, 0.9), None),
    "Hips": ((0, -0.1, 1.45), (0, 0.4, 1.46), "Root"),
    "Chest": ((0, 0.5, 1.47), (0, 0.9, 1.52), "Hips"),
    "Neck1": ((0, 0.85, 1.50), (0, 1.18, 1.90), "Chest"),
    "Neck2": ((0, 1.18, 1.90), (0, 1.28, 2.02), "Neck1"),
    "Head": ((0, 1.22, 2.0), (0, 1.85, 1.90), "Neck2"),
    "Jaw": ((0, 1.30, 1.84), (0, 1.74, 1.35), "Head"),
    "Tail1": ((0, -0.28, 1.47), (0, -1.20, 1.42), "Hips"),
    "Tail2": ((0, -1.20, 1.42), (0, -1.90, 0.88), "Tail1"),
    "Tail3": ((0, -1.90, 0.88), (0, -2.10, 0.25), "Tail2"),
    "Tail4": ((0, -2.10, 0.25), (0, -1.93, 0.16), "Tail3"),
}
LEG = {  # per side sx: hip, knee, ankle
    "hip": (0.38, -0.14, 1.36), "knee": (0.46, 0.10, 0.90), "ankle": (0.44, -0.22, 0.40), "heel": (0.44, -0.16, 0.11),
}
ARM = {"shoulder": (0.33, 0.62, 1.28), "elbow": (0.38, 0.50, 0.95), "wrist": (0.36, 0.80, 0.82)}
for sx, side in ((1, "R"), (-1, "L")):
    h, k, a = (V((sx * p[0], p[1], p[2])) for p in (LEG["hip"], LEG["knee"], LEG["ankle"]))
    BONES[f"Thigh_{side}"] = (tuple(h), tuple(k), "Hips")
    BONES[f"Shin_{side}"] = (tuple(k), tuple(a), f"Thigh_{side}")
    BONES[f"Foot_{side}"] = (tuple(a), tuple(a + V((0, 0.35, -0.3))), f"Shin_{side}")
    s_, e_, w_ = (V((sx * p[0], p[1], p[2])) for p in (ARM["shoulder"], ARM["elbow"], ARM["wrist"]))
    BONES[f"ArmUp_{side}"] = (tuple(s_), tuple(e_), "Chest")
    BONES[f"ArmLo_{side}"] = (tuple(e_), tuple(w_ + V((0, 0.15, -0.1))), f"ArmUp_{side}")
bh.BONES = BONES


# ----------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------
def catmull(pts, i, t):
    p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


def refine(ctrl, per):
    """Catmull-Rom through control rows (y, z, hw, hv); `per` = subdivisions per span. Returns rows + control index."""
    pts = [V((0, r[0], r[1])) for r in ctrl]
    P, W, H, idx = [], [], [], []
    for i in range(len(ctrl) - 1):
        for k in range(per[i]):
            t = k / per[i]
            P.append(catmull(pts, i, t))
            W.append(ctrl[i][2] + (ctrl[i + 1][2] - ctrl[i][2]) * t)
            H.append(ctrl[i][3] + (ctrl[i + 1][3] - ctrl[i][3]) * t)
            idx.append(i + t)
    P.append(pts[-1])
    W.append(ctrl[-1][2])
    H.append(ctrl[-1][3])
    idx.append(len(ctrl) - 1)
    return P, W, H, idx


def tube(part, P, W, H, idx, a, b, mat, ch=0.38, cap_mats=("CULL", "CULL")):
    """Loft over the refined samples whose control index is within [a, b]."""
    sel = [j for j, i in enumerate(idx) if a - 1e-9 <= i <= b + 1e-9]
    secs = []
    for j in sel:
        j0, j1 = max(j - 1, 0), min(j + 1, len(P) - 1)
        t = (P[j1] - P[j0]).normalized()
        u = t.cross(Z)
        if u.length < 1e-4:
            u = X.copy()
        u.normalize()
        v = u.cross(t).normalized()
        secs.append(ring(P[j], u, v, W[j], H[j], ch))
    add_loft(part, secs, mat, cap_mats=cap_mats)


def tube_pts(part, pts, hw, hv, mat, ch=0.38, cap_mats=("CULL", "CULL")):
    """Loft along an explicit polyline."""
    P = [V(p) for p in pts]
    secs = []
    for j in range(len(P)):
        t = (P[min(j + 1, len(P) - 1)] - P[max(j - 1, 0)]).normalized()
        u = t.cross(Z)
        if u.length < 1e-4:
            u = X.copy()
        u.normalize()
        v = u.cross(t).normalized()
        secs.append(ring(P[j], u, v, hw[j], hv[j], ch))
    add_loft(part, secs, mat, cap_mats=cap_mats)


def claw(part, base, d, length, width, curl_deg, mat="claw", segs=4, ref=None):
    """Curved, tapering gold claw built from short tapered blocks that bend downward."""
    d = V(d).normalized()
    axis = d.cross(Z)
    if axis.length < 1e-4:
        axis = X.copy()
    axis.normalize()
    pos = V(base)
    for i in range(segs):
        L = length / segs
        w0 = width * (1 - i / segs) + 0.008
        w1 = width * (1 - (i + 1) / segs) + 0.004
        add_block(part, pos + d * L * 0.5, (w0, w0 * 0.92, L * 1.12), mat, rot=frame_z(d, ref or Z), ts=(w1 / w0, w1 / w0))
        pos = pos + d * L
        d = (Matrix.Rotation(-math.radians(curl_deg / segs), 3, axis) @ d).normalized()


def tooth(part, base, d, length, w):
    d = V(d).normalized()
    add_block(part, base + d * length / 2, (w, w * 0.8, length), "tooth", rot=frame_z(d, X), ts=(0.08, 0.08))


def rod(part, base, d, length, r):
    """Gold crest rod: shaft, a flange near the tip and a small end cap."""
    d = V(d).normalized()
    u = d.cross(X).normalized()
    v = u.cross(d).normalized()

    def seg(t0, t1, rr):
        add_loft(part, [ring(base + d * length * t0, u, v, rr, rr, 0.38), ring(base + d * length * t1, u, v, rr, rr, 0.38)], "gold")

    seg(0.0, 0.78, r * 0.78)  # shaft
    seg(0.78, 0.86, r * 1.35)  # collar
    seg(0.86, 0.93, r * 0.78)
    seg(0.93, 1.0, r * 1.05)  # cap


# ----------------------------------------------------------------------------
# Build the parts
# ----------------------------------------------------------------------------
def build_parts():
    P = {}

    def part(name, bone=None):
        P[name] = Part(name, bone or name)
        return P[name]

    # ---- torso + neck -----------------------------------------------------------------------
    pS, wS, hS, iS = refine(SPINE, [3, 3, 3, 2, 2, 2])
    tube(part("Hips"), pS, wS, hS, iS, 0, 2, "skin", cap_mats=("CULL", "CULL"))
    tube(part("Chest"), pS, wS, hS, iS, 2, 3, "skin")
    tube(part("Neck1"), pS, wS, hS, iS, 3, 5, "skin")
    tube(part("Neck2"), pS, wS, hS, iS, 5, 6, "skin")

    # ---- tail -------------------------------------------------------------------------------------
    pT, wT, hT, iT = refine(TAIL, [3, 4, 3, 3, 3, 3, 2])
    tube(part("Tail1"), pT, wT, hT, iT, 0, 2, "skin")
    tube(part("Tail2"), pT, wT, hT, iT, 2, 4, "skin")
    tube(part("Tail3"), pT, wT, hT, iT, 4, 6, "skin")
    tube(part("Tail4"), pT, wT, hT, iT, 6, 7, "skin", cap_mats=("CULL", "skin"))

    # ---- head ----------------------------------------------------------------------------------------
    head = part("Head")
    tube_pts(head, [(0, 1.14, 2.00), (0, 1.34, 2.00), (0, 1.56, 1.98), (0, 1.74, 1.94), (0, 1.88, 1.90)],
             [.25, .24, .19, .145, .11], [.27, .25, .19, .14, .10], "skin", cap_mats=("CULL", "skin"))
    # brow ridges, cheek plates, nostrils, eyes
    for sx in (-1, 1):
        add_block(head, V((sx * 0.18, 1.40, 2.15)), (0.13, 0.26, 0.06), "skin", rot=Matrix.Rotation(math.radians(-8), 3, X))
        add_block(head, V((sx * 0.235, 1.34, 1.90)), (0.08, 0.36, 0.26), "skin", rot=Matrix.Rotation(math.radians(-5), 3, X))
        add_block(head, V((sx * 0.064, 1.89, 1.99)), (0.04, 0.08, 0.014), "pupil")  # nostril
        eye = V((sx * 0.236, 1.43, 2.065))
        add_block(head, eye, (0.016, 0.075, 0.066), "eye")
        add_block(head, eye + V((sx * 0.008, 0, 0.05)), (0.05, 0.13, 0.03), "skin")  # upper lid / brow
    # roof of the mouth is the (down-facing) underside of the upper jaw; add the maroon palate behind the teeth
    # upper teeth
    for sx in (-1, 1):
        for i in range(10):
            t = 0.10 + 0.88 * i / 9
            y = 1.30 + 0.56 * t
            hw = np.interp(y, [1.14, 1.34, 1.56, 1.74, 1.88], [.25, .24, .19, .145, .11])
            zc = np.interp(y, [1.14, 1.56, 1.88], [2.0, 1.98, 1.90]) - np.interp(y, [1.14, 1.34, 1.56, 1.74, 1.88], [.27, .25, .19, .14, .10]) * 0.84
            L = 0.115 - 0.06 * t if i < 8 else 0.07
            tooth(head, V((sx * hw * 0.80, y, zc + 0.012)), V((sx * 0.04, 0.10, -1)), L * 1.15, 0.05 - 0.016 * t)
    # crest rods: perpendicular to the nape, leaning back; biggest nearest the skull
    rods = [(V((0, 1.13, 2.19)), V((0, -0.55, 0.84)), 0.33, 0.031),
            (V((0, 1.19, 2.07)), V((0, -0.78, 0.62)), 0.29, 0.030),
            (V((0, 1.15, 1.93)), V((0, -0.88, 0.48)), 0.25, 0.028),
            (V((0, 1.07, 1.79)), V((0, -0.92, 0.34)), 0.21, 0.026)]
    for i, (b, d, L, r) in enumerate(rods):
        rod(P["Neck2"] if i < 2 else P["Neck1"], b, d, L, r)

    # ---- lower jaw (hinged, open) -----------------------------------------------------------------
    jaw = part("Jaw")
    jp = [(0, 1.27, 1.86), (0, 1.39, 1.74), (0, 1.55, 1.57), (0, 1.74, 1.35)]
    jhw = [.18, .155, .12, .075]
    jhv = [.12, .105, .085, .06]
    tube_pts(jaw, jp, jhw, jhv, "skin", cap_mats=("CULL", "skin"))
    add_block(jaw, V((0, 1.30, 1.84)), (0.38, 0.18, 0.12), "skin", rot=Matrix.Rotation(math.radians(-38), 3, X))
    # tongue: a flat pink slab lying in the jaw
    tube_pts(jaw, [(0, 1.34, 1.93), (0, 1.48, 1.80), (0, 1.62, 1.66), (0, 1.76, 1.50)], [.105, .10, .085, .05],
             [.03, .03, .028, .02], "tongue", ch=0.25, cap_mats=("tongue", "tongue"))
    for sx in (-1, 1):
        for i in range(9):
            t = 0.12 + 0.86 * i / 8
            y = 1.36 + 0.36 * t
            zc = np.interp(y, [1.27, 1.39, 1.55, 1.74], [1.86, 1.74, 1.57, 1.35]) + np.interp(y, [1.27, 1.39, 1.55, 1.74], jhv) * 0.7
            hw = np.interp(y, [1.27, 1.39, 1.55, 1.74], jhw)
            tooth(jaw, V((sx * hw * 0.78, y, zc)), V((sx * 0.03, 0.12, 1)), 0.085 - 0.03 * t, 0.04 - 0.012 * t)

    # ---- legs -------------------------------------------------------------------------------------------
    for sx, side in ((1, "R"), (-1, "L")):
        hip, knee, ankle, heel = (V((sx * p[0], p[1], p[2])) for p in (LEG["hip"], LEG["knee"], LEG["ankle"], LEG["heel"]))
        thigh = part(f"Thigh_{side}")
        tube_pts(thigh, [hip + V((0, 0.02, 0.05)), hip.lerp(knee, 0.5) + V((sx * 0.02, 0.05, 0)), knee],
                 [.22, .21, .15], [.31, .29, .19], "skin", cap_mats=("CULL", "CULL"))
        add_block(thigh, hip.lerp(knee, 0.42) + V((sx * 0.13, 0.0, 0.0)), (0.09, 0.36, 0.42), "skin", rot=Matrix.Rotation(math.radians(8), 3, X))
        shin = part(f"Shin_{side}")
        tube_pts(shin, [knee + V((0, 0.02, 0.04)), knee.lerp(ankle, 0.5), ankle], [.145, .13, .10], [.165, .14, .105], "skin",
                 cap_mats=("CULL", "CULL"))
        add_block(shin, knee + V((0, 0.08, -0.02)), (0.19, 0.16, 0.19), "skin")  # knee cap
        foot = part(f"Foot_{side}")
        tube_pts(foot, [ankle + V((0, 0.0, 0.03)), ankle.lerp(heel, 0.55), heel], [.115, .125, .145], [.12, .13, .155], "skin",
                 cap_mats=("CULL", "CULL"))
        add_block(foot, ankle + V((0, -0.11, -0.02)), (0.14, 0.15, 0.2), "skin")  # heel / ankle knob
        # three chunky toes with big gold claws
        for k, yaw in enumerate((-24, 0, 24)):
            d = (Matrix.Rotation(math.radians(yaw), 3, Z) @ V((0, 1, 0))).normalized()
            base = heel + V((sx * 0.0, 0.0, 0.0)) + V((d.x * 0.02, 0, 0))
            b0 = V((heel.x + sx * 0.0 + (yaw / 24) * 0.14, heel.y + 0.03, 0.09))
            b1 = b0 + d * 0.20 + V((0, 0, -0.012))
            b2 = b1 + d * 0.13 + V((0, 0, -0.006))
            tube_pts(foot, [b0, b1, b2], [.093, .085, .072], [.088, .078, .066], "skin", ch=0.3, cap_mats=("CULL", "skin"))
            add_block(foot, b1, (0.19, 0.05, 0.15), "skin")  # knuckle plate
            claw(foot, b2 + V((0, 0, 0.004)), d + V((0, 0, -0.1)), 0.24, 0.095, 62)

    # ---- arms ---------------------------------------------------------------------------------------------
    for sx, side in ((1, "R"), (-1, "L")):
        sh, el, wr = (V((sx * p[0], p[1], p[2])) for p in (ARM["shoulder"], ARM["elbow"], ARM["wrist"]))
        up = part(f"ArmUp_{side}")
        tube_pts(up, [sh + V((0, 0, 0.04)), sh.lerp(el, 0.5) + V((sx * 0.02, 0.03, 0)), el], [.12, .115, .095], [.125, .12, .10], "skin",
                 cap_mats=("CULL", "CULL"))
        lo = part(f"ArmLo_{side}")
        tube_pts(lo, [el + V((0, 0.0, 0.02)), el.lerp(wr, 0.5), wr], [.095, .09, .085], [.10, .09, .085], "skin", cap_mats=("CULL", "CULL"))
        add_block(lo, el, (0.21, 0.19, 0.19), "skin")  # elbow
        add_block(lo, wr + V((0, 0.06, -0.02)), (0.22, 0.17, 0.14), "skin")  # palm
        for k, yaw in enumerate((-22, 0, 22)):
            d = (Matrix.Rotation(math.radians(sx * yaw), 3, Z) @ V((0, 1, -0.45))).normalized()
            f0 = wr + V((sx * 0.0 + (yaw / 22) * 0.07, 0.11, -0.04))
            f1 = f0 + d * 0.11
            f2 = f1 + d * 0.09
            tube_pts(lo, [f0, f1, f2], [.05, .046, .04], [.05, .046, .04], "skin", ch=0.3, cap_mats=("CULL", "skin"))
            add_block(lo, f1, (0.095, 0.09, 0.07), "skin")
            claw(lo, f2, d + V((0, 0, -0.35)), 0.19, 0.055, 70)
    return P


# ----------------------------------------------------------------------------
# Painting
# ----------------------------------------------------------------------------
TEAL, TEAL_LT, TEAL_DK = col(.36, .78, .82), col(.55, .90, .92), col(.08, .38, .46)
BLUE, BLUE_LT, BLUE_DK = col(.11, .28, .80), col(.24, .45, .92), col(.05, .15, .55)
CREAM, CREAM_DK = col(.90, .83, .56), col(.62, .54, .32)
GOLD, GOLD_DK = col(.97, .77, .16), col(.62, .40, .04)


class Line2D:
    """Centre line in the (y, z) plane with per-point half sizes, used to map a pixel to
    (arc length, normalised height across the body, local half sizes)."""

    def __init__(self, rows, flip):
        self.p = np.array([(r[0], r[1]) for r in rows], dtype=np.float32)
        d = np.diff(self.p, axis=0)
        self.len = np.hypot(d[:, 0], d[:, 1])
        self.t = d / self.len[:, None]
        self.arc = np.concatenate([[0], np.cumsum(self.len)])
        self.hw = np.array([r[2] for r in rows], dtype=np.float32)
        self.hv = np.array([r[3] for r in rows], dtype=np.float32)
        # "up" side normal (tail: toward the outside of its curve; spine: dorsal)
        self.n = np.stack([self.t[:, 1], -self.t[:, 0]], axis=1) if flip else np.stack([-self.t[:, 1], self.t[:, 0]], axis=1)

    def query(self, y, z):
        best = np.full(y.shape, 1e9, np.float32)
        arc = np.zeros_like(y)
        off = np.zeros_like(y)
        for i in range(len(self.len)):
            ty, tz = self.t[i]
            a = self.p[i]
            proj = np.clip((y - a[0]) * ty + (z - a[1]) * tz, 0, self.len[i])
            cy, cz = a[0] + ty * proj, a[1] + tz * proj
            dd = np.hypot(y - cy, z - cz)
            m = dd < best
            o = (y - cy) * self.n[i][0] + (z - cz) * self.n[i][1]
            best = np.where(m, dd, best)
            arc = np.where(m, self.arc[i] + proj, arc)
            off = np.where(m, o, off)
        hv = np.interp(arc, self.arc, self.hv)
        hw = np.interp(arc, self.arc, self.hw)
        return arc, off / hv, hw, hv


SPINE_LINE = Line2D(SPINE, flip=False)
TAIL_LINE = Line2D(TAIL, flip=True)


def lens_ring(u, v, cu, cv, a, b, w, rot=0.0):
    """Gold almond (pointed-ellipse) outline; (u, v) in metres. a/b = half length/height, w = line width."""
    du, dv = u - cu, v - cv
    if rot:
        c, s = math.cos(rot), math.sin(rot)
        du, dv = c * du + s * dv, -s * du + c * dv
    t = np.clip(1 - (du / a) ** 2, 0, 1)
    h = b * t
    slope = 2 * b * du / (a * a)
    sd = (np.abs(dv) - h) / np.sqrt(1 + slope ** 2)
    tip = np.hypot(np.maximum(np.abs(du) - a, 0), dv)
    sd = np.where(np.abs(du) > a, tip, sd)
    return smooth(w, w * 0.45, np.abs(sd))


def ellipse_ring(u, v, cu, cv, a, b, w):
    r = np.hypot((u - cu) / a, (v - cv) / b)
    return smooth(w, w * 0.45, np.abs(r - 1) * np.minimum(a, b))


def paint_skin(c):
    part = c.part
    x, y, z = c.x, c.y, c.z
    s = c.seed
    nzv = float(c.N.z)
    nxv = float(c.N.x)
    n1 = fbm(x * 8, y * 8, z * 8, s, 3)
    n2 = fbm(x * 40, y * 40, z * 40, s + 1, 2)
    wob = fbm(x * 3.2, y * 3.2, z * 3.2, s + 5, 2) - 0.5

    is_tail = part.startswith("Tail")
    is_torso = part in ("Hips", "Chest")
    is_neck = part.startswith("Neck")
    is_head = part in ("Head", "Jaw")
    is_arm = part.startswith("Arm")
    is_leg = part.startswith("Thigh") or part.startswith("Shin")
    is_foot = part.startswith("Foot")

    # pixel -> body frame
    if is_tail:
        arc, v, hwl, hvl = TAIL_LINE.query(y, z)
        ux = x / hwl
    elif is_torso or is_neck:
        arc, v, hwl, hvl = SPINE_LINE.query(y, z)
        ux = x / hwl
    else:
        arc = np.zeros_like(y)
        v = np.zeros_like(y)
        ux = np.zeros_like(y)

    # ---- region weights ---------------------------------------------------------------------------------
    one = np.ones_like(y)
    if is_head or is_neck or is_arm:
        tw = one
    elif is_torso:
        cut = 0.02 + 0.55 * (0.5 - 0.5 * np.clip(v, -1, 1))  # blue starts further back on the upper back
        tw = smooth(0.03, -0.05, cut + 0.18 * wob - y)
    else:
        tw = np.zeros_like(y)
    cream = np.zeros_like(y)
    if is_tail:
        cream = smooth(-0.24, -0.29, v + 0.08 * wob)
    elif is_torso:
        cream = smooth(-0.60, -0.66, v + 0.08 * wob) * smooth(0.55, 0.30, y)
    elif is_neck:
        cream = smooth(-0.46, -0.52, v + 0.08 * wob) * (smooth(1.25, 0.9, y) if part == "Neck1" else 0.0)
    # ---- base colours -------------------------------------------------------------------------------------
    teal = mix(TEAL, TEAL_LT, 0.65 * smooth(0.25, 0.75, n1))
    blue = mix(BLUE, BLUE_LT, 0.55 * smooth(0.25, 0.8, n1))
    base = mix(blue, teal, tw)
    base = mix(base, mix(CREAM, CREAM_DK, 0.4 * smooth(0.3, 0.8, n2)), cream)
    # ---- dark stripes (teal region only) --------------------------------------------------------------------
    if is_torso or is_neck:
        phase = arc / 0.25 + 0.30 * v + 0.55 * wob + 0.14 * np.sin(arc * 6 + ux * 2.0)
        band = 0.5 + 0.5 * np.sin(phase * TAU)
        dorsal = smooth(-0.62, -0.18, v + 0.10 * wob)
        stripe = smooth(0.50, 0.58, band) * dorsal * tw * (1 - cream)
        base = mix(base, mix(TEAL_DK, TEAL, 0.25 * n2), stripe * 0.95)
    elif is_head:
        # slanted bands on the cheek and back of the skull, plain snout
        ph = (y * 0.8 + z * -0.6) / 0.115 + 0.8 * wob
        band = 0.5 + 0.5 * np.sin(ph * TAU)
        stripe = smooth(0.66, 0.76, band) * smooth(1.62, 1.36, y) * smooth(1.70, 1.88, z) * (0.0 if part == "Jaw" else 1.0)
        base = mix(base, TEAL_DK, stripe * 0.9)
    elif is_arm:
        ph = (y * 0.0 + z) / 0.12 + 0.6 * wob
        band = 0.5 + 0.5 * np.sin(ph * TAU)
        base = mix(base, TEAL_DK, smooth(0.78, 0.88, band) * 0.35)
        base = mix(base, TEAL_DK, smooth(0.30, 0.20, z) * 0.0)
    # ---- gold markings -------------------------------------------------------------------------------------
    gold = np.zeros_like(y)
    side_face = abs(nxv) >= abs(nzv)
    if is_tail:
        # one row of rounded rings down the upper side, one down the centre of the back
        k = np.floor(arc / 0.135 + 0.5)
        au = (arc - k * 0.135)
        if side_face:
            gold = ellipse_ring(au, v * hvl, 0.0, 0.32 * hvl, 0.032 + 0.010 * hvl, 0.050 * 0.7 + 0.30 * hvl, 0.0085)
        else:
            gold = ellipse_ring(au, x, 0.0, 0.0, 0.034 + 0.004 * hvl, 0.30 * hwl + 0.01, 0.0085) * smooth(0.0, 0.25, v)
        gold = gold * (1 - cream)
    elif is_torso and side_face:
        blue_w = 1 - tw
        k = np.floor((y + 0.40) / 0.185 + 0.5)
        au = (y + 0.40) - k * 0.185
        gold = lens_ring(au, z - 1.62, 0.0, 0.0, 0.045, 0.115, 0.011, rot=0.08) * blue_w * smooth(-0.1, 0.25, v)
    if part.startswith("Thigh") and side_face:
        sxn = 1.0 if float(c.N.x) > 0 else -1.0
        # two big almonds on the outer thigh
        g1 = lens_ring(y, z, -0.05, 1.16, 0.075, 0.22, 0.014, rot=0.16)
        g2 = lens_ring(y, z, 0.12, 1.07, 0.06, 0.17, 0.013, rot=0.10)
        gold = np.maximum(g1, g2) * smooth(0.45, 0.8, abs(nxv))
    if gold is not None:
        base = mix(base, mix(GOLD, col(1.0, 0.9, 0.4), 0.3 * smooth(0.5, 0.9, n2)), gold)
    # ---- plate seams (the reference is built from little stone-like plates) -----------------------------------
    seam = fbm(c.pu * 6, c.pv * 6, np.full_like(y, s * 0.17), s + 7, 2)
    cr = (1 - smooth(0.0, 0.016, np.abs(seam - 0.5))) * smooth(0.45, 0.65, fbm(x * 3, y * 3, z * 3, s + 8, 2))
    base = base * (1 - 0.30 * cr)[..., None]
    base = base * (0.93 + 0.14 * n2)[..., None]
    # cracks / chips
    chip = smooth(0.70, 0.86, fbm(x * 18, y * 18, z * 18, s + 9, 2))
    base = mix(base, base * 0.78, chip * 0.5)
    height = 0.5 + 0.3 * n2 - 0.5 * cr - 0.25 * gold
    rough = np.full_like(y, 0.74)
    rough = np.where(gold > 0.5, 0.35, rough)
    metal = np.where(gold > 0.5, 0.5, 0.0)
    outline = mix(col(.03, .08, .26), col(.02, .16, .22), tw)
    return finish(c, base, height, rough, metal, True, 0.0038, outline, hilite=0.12)


def paint_claw(c):
    x, y, z = c.x, c.y, c.z
    s = c.seed
    n1 = fbm(x * 30, y * 30, z * 30, s, 2)
    grad = 0.5 + 0.5 * np.sin((c.pu + c.pv) * 40)
    base = mix(col(.80, .56, .08), col(1.0, .86, .30), 0.6 * grad + 0.4 * n1)
    base = base * (1 + 0.2 * smooth(0.8, 1.0, grad))[..., None]
    return finish(c, base, 0.5 + 0 * n1, np.full_like(x, 0.34), np.full_like(x, 0.6), True, 0.0032, col(.40, .25, .03), 0.35)


def paint_tooth(c):
    n1 = fbm(c.x * 40, c.y * 40, c.z * 40, c.seed, 2)
    base = mix(col(.95, .90, .72), col(.99, .96, .84), smooth(0.3, 0.8, n1))
    return finish(c, base, 0.5 + 0 * n1, np.full_like(c.x, 0.4), np.zeros_like(c.x), True, 0.0025, col(.35, .28, .2), 0.2)


def paint_tongue(c):
    n1 = fbm(c.x * 14, c.y * 14, c.z * 14, c.seed, 3)
    base = mix(col(.86, .38, .42), col(.96, .52, .54), smooth(0.25, 0.8, n1))
    seam = 1 - smooth(0.0, 0.03, np.abs(fbm(c.pu * 9, c.pv * 9, np.full_like(c.x, c.seed * 0.1), c.seed + 3, 2) - 0.5))
    base = base * (1 - 0.2 * seam)[..., None]
    return finish(c, base, 0.5 + 0.2 * n1, np.full_like(c.x, 0.5), np.zeros_like(c.x), True, 0.004, col(.4, .1, .14), 0.1)


def paint_eye(c):
    # pale iris with a brown swirl, like the concept art
    cx = (c.pu - (c.pu.min() + c.pu.max()) / 2)
    cy = (c.pv - (c.pv.min() + c.pv.max()) / 2)
    r = np.hypot(cx, cy) / max(0.035, 0.45 * min(c.pu.max() - c.pu.min(), c.pv.max() - c.pv.min()))
    ang = np.arctan2(cy, cx)
    swirl = 0.5 + 0.5 * np.sin(ang * 1.0 + r * 9.0)
    base = mix(col(.95, .90, .72), col(.62, .46, .22), smooth(0.55, 0.9, swirl) * smooth(1.0, 0.3, r) * 0.9)
    base = mix(base, col(.12, .09, .07), smooth(0.28, 0.12, r))
    return finish(c, base, 0.5 + 0 * r, np.full_like(r, 0.25), np.zeros_like(r), True, 0.003, col(.05, .12, .14))


def paint_pupil(c):
    return finish(c, np.tile(col(.10, .04, .06), c.x.shape + (1,)), 0.5 + 0 * c.x, np.full_like(c.x, 0.6), np.zeros_like(c.x), True, 0.002, col(0, 0, 0))


# inside of the mouth: dark maroon with pinker patches, used for the down-facing underside of the upper jaw
def paint_mouth(c):
    n1 = fbm(c.x * 12, c.y * 12, c.z * 12, c.seed, 3)
    base = mix(col(.30, .06, .09), col(.55, .13, .17), smooth(0.3, 0.8, n1))
    return finish(c, base, 0.5 + 0.2 * n1, np.full_like(c.x, 0.55), np.zeros_like(c.x), True, 0.004, col(.12, .02, .04), 0.1)


_orig_skin = paint_skin


def paint_skin_wrapper(c):
    # mouth interior: the underside of the upper jaw and the inside faces of the lower jaw
    if c.part == "Head" and float(c.N.z) < -0.55 and float(c.y.mean()) > 1.30:
        return paint_mouth(c)
    if c.part == "Jaw" and float(c.N.z) > 0.55:
        return paint_mouth(c)
    return _orig_skin(c)


bh.PAINTERS.update({
    "skin": paint_skin_wrapper,
    "claw": paint_claw,
    "tooth": paint_tooth,
    "tongue": paint_tongue,
    "eye": paint_eye,
    "pupil": paint_pupil,
})
bh.MAT_KEYS[:] = list(bh.PAINTERS) + ["CULL"]
bh.DENSITY.update({"tooth": 0.6})


def main():
    os.makedirs(OUT, exist_ok=True)
    bh.PARTS = build_parts()
    prepared = bh.prepare_faces(bh.PARTS)
    recs, ppm = bh.build_atlas(prepared)
    color, nrm, rough, metal = bh.bake_textures(recs, ppm)
    imgs = {k: os.path.join(OUT, f"dino_{k}.png") for k in ("color", "normal")}
    imgs["rough"] = os.path.join(OUT, "dino_roughness.png")
    imgs["metal"] = os.path.join(OUT, "dino_metalness.png")
    bh.save_png(color, imgs["color"])
    bh.save_png(nrm, imgs["normal"])
    bh.save_png(rough, imgs["rough"], gray=True)
    bh.save_png(metal, imgs["metal"], gray=True)
    arm, objs, mat = bh.build_scene(prepared, recs, ppm, imgs)
    bh.export_all(arm, objs)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
