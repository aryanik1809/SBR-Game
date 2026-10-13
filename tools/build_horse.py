#!/usr/bin/env python3
"""Build the blocky SBR horse in Blender (bpy) with a painted PBR texture atlas.

Run with a Python that has `bpy`, `numpy` and `pillow` installed:

    python3 tools/build_horse.py            # writes assets/horse/*

Outputs (assets/horse/):
    horse.blend            full scene: rigged mesh + PBR material
    horse_rigged.fbx       skinned meshes + armature (Roblox / Unity / Unreal)
    horse_static.obj/.mtl  single merged static mesh (Roblox MeshPart)
    horse.glb              glTF binary with embedded textures
    horse_color.png        albedo atlas
    horse_normal.png       tangent-space normal (OpenGL, +Y up)
    horse_roughness.png
    horse_metalness.png

Model space: 1 unit = 1 metre, +Z up, horse faces +Y, hooves on Z=0.
Every surface is a flat-shaded polygon. Each polygon gets its own rectangle in
the atlas at a uniform texel density and is painted from 3D procedural noise,
so patterns continue across neighbouring facets.
"""
import math
import os
import random
import sys

import bpy  # noqa: F401  (must come before bmesh)
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "horse")
ATLAS = 2048
PAD = 4

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
rng = random.Random(7)


# ----------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------
class Part:
    """Collection of polygons that share one bone / one Blender object."""

    def __init__(self, name, bone):
        self.name, self.bone = name, bone
        self.verts, self.faces = [], []  # faces: (vertex indices, material key)


def axes(fwd):
    fwd = Vector(fwd).normalized()
    u = fwd.cross(Z).normalized()
    v = u.cross(fwd).normalized()
    return u, v


def ring(c, u, v, hu, hv, ch=0.3):
    """Cross-section: rectangle (ch=0) or chamfered octagon."""
    if ch <= 0:
        pts = [(-hu, hv), (hu, hv), (hu, -hv), (-hu, -hv)]
    else:
        k = ch * min(hu, hv)
        pts = [(-hu + k, hv), (hu - k, hv), (hu, hv - k), (hu, -hv + k),
               (hu - k, -hv), (-hu + k, -hv), (-hu, -hv + k), (-hu, hv - k)]
    return [Vector(c) + u * a + v * b for a, b in pts]


def add_loft(part, secs, mat, caps=(True, True), cap_mats=(None, None), side_mats=None):
    n, base = len(secs[0]), len(part.verts)
    for s in secs:
        part.verts += [Vector(p) for p in s]

    def idx(i, j):
        return base + i * n + (j % n)

    for i in range(len(secs) - 1):
        for j in range(n):
            m = side_mats[j] if side_mats and side_mats[j] else mat
            part.faces.append(([idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)], m))
    if caps[0]:
        part.faces.append(([idx(0, j) for j in range(n)][::-1], cap_mats[0] or mat))
    if caps[1]:
        part.faces.append(([idx(len(secs) - 1, j) for j in range(n)], cap_mats[1] or mat))


def add_polygon_prism(part, polys, mat):
    """Loft between two arbitrary same-length polygons (used for drapes)."""
    add_loft(part, polys, mat)


def frame_z(d, ref=X):
    z = Vector(d).normalized()
    x = Vector(ref) - z * Vector(ref).dot(z)
    if x.length < 1e-6:
        x = Y - z * Y.dot(z)
    x.normalize()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def add_block(part, c, size, mat, rot=None, ts=(1, 1), bs=(1, 1), cap_mats=(None, None)):
    """Box centred on c; local Z is the long axis; ts/bs taper top/bottom."""
    sx, sy, sz = size
    R = rot if rot is not None else Matrix.Identity(3)

    def rect(z, s):
        return [R @ Vector((x * sx / 2 * s[0], y * sy / 2 * s[1], z)) + Vector(c)
                for x, y in [(-1, 1), (1, 1), (1, -1), (-1, -1)]]

    add_loft(part, [rect(-sz / 2, bs), rect(sz / 2, ts)], mat, cap_mats=cap_mats)


def add_strap(part, p0, p1, width, thick, mat, ref=X, ext=0.0):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    dn = d / L
    c = (p0 + p1) / 2
    add_block(part, c, (thick, width, L + ext), mat, rot=frame_z(dn, ref))


def add_ring3d(part, c, normal, R, thick, mat, n=8):
    c, normal = Vector(c), Vector(normal).normalized()
    a = normal.cross(Z)
    if a.length < 1e-4:
        a = normal.cross(X)
    a.normalize()
    b = normal.cross(a)
    pts = [c + (a * math.cos(2 * math.pi * i / n) + b * math.sin(2 * math.pi * i / n)) * R for i in range(n)]
    for i in range(n):
        radial = (pts[i] - c).normalized()
        add_strap(part, pts[i], pts[(i + 1) % n], thick, thick, mat, ref=radial, ext=thick * 0.6)


def add_buckle(part, c, size, mat="gold", normal=X, up=Z, t=0.012):
    """Rectangular gold buckle frame with a tongue. size = (width, height)."""
    c, normal, up = Vector(c), Vector(normal).normalized(), Vector(up).normalized()
    side = up.cross(normal).normalized()
    w, h = size
    bar = max(0.011, min(w, h) * 0.22)
    for sgn in (-1, 1):
        add_strap(part, c + up * (sgn * (h / 2 - bar / 2)) - side * w / 2,
                  c + up * (sgn * (h / 2 - bar / 2)) + side * w / 2, bar, t, mat, ref=normal, ext=0)
        add_strap(part, c + side * (sgn * (w / 2 - bar / 2)) - up * h / 2,
                  c + side * (sgn * (w / 2 - bar / 2)) + up * h / 2, bar, t, mat, ref=normal, ext=0)
    add_strap(part, c - up * h * 0.38, c + up * h * 0.38, bar * 0.6, t * 1.2, mat, ref=normal)


def add_chain(part, pts, mat="gold", link=0.036, wid=0.022, bar=0.0075):
    """Chunky chain links alternately rotated 90 degrees along a polyline."""
    pts = [Vector(p) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = (b - a).normalized()
        m = d.cross(Z)
        if m.length < 1e-4:
            m = d.cross(X)
        m.normalize()
        m2 = d.cross(m).normalized()
        m = m if i % 2 == 0 else m2
        c = (a + b) / 2
        for s in (-1, 1):
            add_strap(part, c - d * link / 2 + m * s * wid / 2, c + d * link / 2 + m * s * wid / 2,
                      bar, bar, mat, ref=m, ext=bar)
            add_strap(part, c + d * s * link / 2 - m * wid / 2, c + d * s * link / 2 + m * wid / 2,
                      bar, bar, mat, ref=d, ext=bar)


# ----------------------------------------------------------------------------
# Horse shape data
# ----------------------------------------------------------------------------
# (y, width, height, centre z) of the torso cross-sections, back to front
TORSO = [(-0.80, 0.46, 0.52, 0.96), (-0.62, 0.64, 0.70, 0.96), (-0.25, 0.60, 0.70, 0.89),
         (0.20, 0.60, 0.76, 0.88), (0.58, 0.58, 0.76, 0.92), (0.82, 0.46, 0.62, 0.98)]
TORSO_CH = 0.38


def tdim(y):
    for (y0, *a), (y1, *b) in zip(TORSO, TORSO[1:]):
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            return tuple(p + (q - p) * t for p, q in zip(a, b))
    return tuple(TORSO[0][1:]) if y < TORSO[0][0] else tuple(TORSO[-1][1:])


def torso_sec(y, off=0.0, ch=TORSO_CH):
    w, h, zc = tdim(y)
    k = ch * min(w / 2, h / 2)  # chamfer is fixed by the *unoffset* body
    pts = [(-w / 2 + k, h / 2 + off), (w / 2 - k, h / 2 + off), (w / 2 + off, h / 2 - k),
           (w / 2 + off, -h / 2 + k), (w / 2 - k, -h / 2 - off), (-w / 2 + k, -h / 2 - off),
           (-w / 2 - off, -h / 2 + k), (-w / 2 - off, h / 2 - k)]
    return [Vector((a, y, zc + b)) for a, b in pts]


def drape(part, ys, lows, off_in, off_out, mat):
    """Thin C-shaped cloth/leather skin over the back following the torso."""
    secs = []
    for y, low in zip(ys, lows):
        w, h, zc = tdim(y)
        k = TORSO_CH * min(w / 2, h / 2)

        def contour(o):
            a, b = w / 2 + o, h / 2 + o
            zl = zc - low
            return [Vector((-a, y, zl)), Vector((-a, y, zc + h / 2 - k)), Vector((-w / 2 + k, y, zc + b)),
                    Vector((w / 2 - k, y, zc + b)), Vector((a, y, zc + h / 2 - k)), Vector((a, y, zl))]

        outer, inner = contour(off_out), contour(off_in)
        secs.append(outer + inner[::-1])
    add_loft(part, secs, mat, side_mats=[None] * 6 + ['CULL'] * 5 + [None])


def band(part, y, width, off, mat, thick=0.012):
    """Strap ring wrapped around the torso with chamfered edges."""
    y0, y1 = y - width / 2, y + width / 2
    s = []
    for yy, o in ((y0, 0.0), (y0 + 0.006, off), (y1 - 0.006, off), (y1, 0.0)):
        s.append(torso_sec(yy, o))
    add_loft(part, s, mat, caps=(False, False))


def head_band(part, c0, hf, t0, t1, w_of, h_of, off, mat):
    """Strap ring around the head between param t0..t1 (0 skull .. 1 nose end)."""
    u, v = axes(hf)
    L = HEAD_LEN
    s = []
    for t, o in ((t0, 0.0), (t0 + 0.012, off), (t1 - 0.012, off), (t1, 0.0)):
        c = c0 + hf * L * t
        s.append(ring(c, u, v, w_of(t) / 2 + o, h_of(t) / 2 + o, 0.3))
    add_loft(part, s, mat, caps=(False, False))


HEAD_C0 = Vector((0.0, 0.97, 1.60))
HEAD_F = Vector((0.0, 0.82, -0.57)).normalized()
HEAD_LEN = 0.50


def head_w(t):
    return 0.40 + (0.31 - 0.40) * t


def head_h(t):
    return 0.46 + (0.35 - 0.46) * t


def head_pt(t, side=0.0, up=0.0, out=0.0):
    u, v = axes(HEAD_F)
    c = HEAD_C0 + HEAD_F * HEAD_LEN * t
    return c + u * (side * (head_w(t) / 2 + out)) + v * (up * (head_h(t) / 2))


# ----------------------------------------------------------------------------
# Build parts
# ----------------------------------------------------------------------------
def build_parts():
    P = {}

    def part(name, bone):
        P[name] = Part(name, bone)
        return P[name]

    # ---- body ---------------------------------------------------------------
    body = part("Body", "Spine")
    add_loft(body, [torso_sec(t[0]) for t in TORSO], "hide")

    # blanket
    b_ys = [-0.31, -0.28, -0.20, 0.08, 0.17, 0.22, 0.25]
    b_low = [0.02, 0.06, 0.11, 0.11, 0.11, 0.07, 0.03]
    drape(body, b_ys, b_low, 0.002, 0.016, "blanket")
    # saddle skirt
    s_ys = [-0.18, -0.15, -0.06, 0.04, 0.10, 0.13]
    s_low = [0.0, 0.0, -0.01, -0.01, -0.01, 0.0]
    drape(body, s_ys, s_low, 0.018, 0.038, "saddle")
    zt = tdim(-0.02)[2] + tdim(-0.02)[1] / 2 + 0.038  # top of the saddle skin
    add_block(body, (0, -0.02, zt + 0.014), (0.24, 0.26, 0.028), "saddle", ts=(0.96, 0.98))
    # cantle (raised back) and pommel (raised front, with horn)
    add_block(body, (0, -0.165, zt + 0.045), (0.27, 0.05, 0.09), "saddle",
              rot=Matrix.Rotation(math.radians(-14), 3, "X"), ts=(0.9, 1.0))
    add_block(body, (0, 0.115, zt + 0.045), (0.15, 0.06, 0.09), "saddle",
              rot=Matrix.Rotation(math.radians(12), 3, "X"), ts=(0.7, 1.0))
    add_block(body, (0, 0.125, zt + 0.105), (0.055, 0.05, 0.05), "saddle", ts=(1.25, 1.25))
    # edge roll of the saddle seat in dark leather
    add_block(body, (0, -0.02, zt + 0.031), (0.255, 0.275, 0.006), "leather_dark")
    # girth strap, breast collar
    band(body, 0.19, 0.05, 0.028, "leather")
    band(body, 0.66, 0.045, 0.026, "leather")
    # hanging billets + buckles on both flanks
    for sx in (-1, 1):
        for y, lo in ((-0.045, 0.19), (0.05, 0.19)):
            w, h, zc = tdim(y)
            x = sx * (w / 2 + 0.019)
            add_block(body, (x, y, zc - 0.02 - lo / 2 + 0.005), (0.032, 0.036, lo + 0.04), "leather")
        w, h, zc = tdim(0.19)
        add_buckle(body, (sx * (w / 2 + 0.036), 0.19, zc - 0.13), (0.052, 0.07), normal=X * sx, up=Z)
        w, h, zc = tdim(0.05)
        add_buckle(body, (sx * (w / 2 + 0.040), 0.05, zc - 0.16), (0.05, 0.06), normal=X * sx, up=Z)
    # chest buckle
    add_buckle(body, (0.0, 0.775, tdim(0.775)[2] - 0.12), (0.08, 0.06), normal=Y, up=Z, t=0.014)
    # saddlebags (right: tan, left: dark)
    for sx, mat in ((1, "leather"), (-1, "leather_dark")):
        w, h, zc = tdim(-0.16)
        x = sx * (w / 2 + 0.038 + 0.05)
        add_block(body, (x, -0.17, zc + 0.12), (0.095, 0.15, 0.13), mat, ts=(1.0, 1.0), bs=(0.9, 0.95))
        add_block(body, (x + sx * 0.003, -0.17, zc + 0.185), (0.105, 0.162, 0.034), mat)  # flap
        add_buckle(body, (x + sx * 0.052, -0.17, zc + 0.15), (0.034, 0.05), normal=X * sx, up=Z, t=0.01)
        add_strap(body, (sx * (w / 2 + 0.03), -0.17, zc + 0.14), (sx * (w / 2 + 0.035), -0.17, zc + 0.04),
                  0.03, 0.012, "leather")

    # ---- neck ---------------------------------------------------------------
    neck = part("Neck", "Neck")
    nf = Vector((0, 0.6, 0.8)).normalized()
    nu, nv = axes(nf)
    n_secs = [ring(Vector(c), nu, nv, w / 2, h / 2, 0.34)
              for c, w, h in (((0, 0.58, 0.98), 0.46, 0.64), ((0, 0.78, 1.22), 0.40, 0.52),
                              ((0, 0.95, 1.46), 0.38, 0.46))]
    add_loft(neck, n_secs, "hide", cap_mats=("CULL", "CULL"))
    # mane: two rows of chunky slabs along the crest, falling to both sides
    crest0, crest1 = Vector((0, 0.38, 1.18)), Vector((0, 0.84, 1.68))
    for row in range(2):
        for i in range(11):
            t = i / 10
            c = crest0.lerp(crest1, t) + Vector((0, 0, 0.0))
            for sx in (-1, 1):
                size = (0.075 + rng.random() * 0.03, 0.05 + rng.random() * 0.02, 0.16 + rng.random() * 0.09)
                d = Vector((sx * (0.55 + rng.random() * 0.25), -0.25 - rng.random() * 0.35,
                            0.15 + rng.random() * 0.35 - 0.55 * row))
                pos = c + Vector((sx * (0.03 + 0.03 * row), -0.02 - 0.03 * row, 0.0 - 0.04 * row))
                R = frame_z(d, Vector((rng.uniform(-1, 1), rng.uniform(-.3, .3), rng.uniform(-.5, .5))))
                add_block(neck, pos + d.normalized() * size[2] * 0.4, size, "mane", rot=R, ts=(0.7, 0.8), cap_mats=("CULL", None))

    # ---- head ---------------------------------------------------------------
    head = part("Head", "Head")
    hu, hv = axes(HEAD_F)
    sections = []
    for t in (-0.10, 0.0, 0.35, 0.7, 1.0):
        w = head_w(t) + (0.02 if t < 0 else 0)
        sections.append(ring(HEAD_C0 + HEAD_F * HEAD_LEN * t, hu, hv, w / 2, head_h(t) / 2, 0.3))
    add_loft(head, sections, "hide", cap_mats=(None, "CULL"))
    # muzzle block
    mc0 = HEAD_C0 + HEAD_F * HEAD_LEN * 0.97
    mlen = 0.31
    msecs = [ring(mc0, hu, hv, 0.27 / 2, 0.30 / 2, 0.14),
             ring(mc0 + HEAD_F * mlen, hu, hv, 0.285 / 2, 0.31 / 2, 0.14)]
    add_loft(head, msecs, "muzzle", cap_mats=("CULL", "muzzle_front"))
    # eyes
    for sx in (-1, 1):
        ec = head_pt(0.46, side=sx, up=0.34)
        er = frame_z(HEAD_F, X)
        add_block(head, ec, (0.022, 0.10, 0.10), "eye_white", rot=Matrix((hu, hv, HEAD_F)).transposed())
        add_block(head, ec + hu * sx * 0.008 + hv * -0.004, (0.022, 0.06, 0.066), "eye_pupil",
                  rot=Matrix((hu, hv, HEAD_F)).transposed())
    # ears
    for sx in (-1, 1):
        base = head_pt(0.0, side=sx * 0.55, up=1.0) + Vector((0, -0.02, -0.01))
        R = Matrix.Rotation(math.radians(-18), 3, "X") @ Matrix.Rotation(math.radians(sx * -10), 3, "Y")
        add_block(head, base + R @ Vector((0, 0, 0.055)), (0.115, 0.065, 0.13), "hide", rot=R, ts=(0.2, 0.45))
        add_block(head, base + R @ Vector((0, 0.028, 0.05)), (0.055, 0.02, 0.09), "ear_inner", rot=R, ts=(0.2, 0.5))
    # forelock
    for i, sx in enumerate((-1, 0, 1, 0.5)):
        c = head_pt(0.08, side=sx * 0.4, up=1.0) + Vector((0, 0.03, 0.015))
        d = Vector((sx * 0.25, 0.55 + 0.1 * i, -0.65 - 0.1 * (i % 2)))
        size = (0.07, 0.05, 0.17 + 0.03 * (i % 2))
        add_block(head, c + d.normalized() * 0.07, size, "mane", rot=frame_z(d, X), ts=(0.65, 0.8), cap_mats=("CULL", None))
    # bridle: noseband, crown/throat straps, cheek straps, brow band
    head_band(head, HEAD_C0, HEAD_F, 0.80, 0.90, head_w, head_h, 0.016, "leather")
    head_band(head, HEAD_C0, HEAD_F, 0.06, 0.15, head_w, head_h, 0.016, "leather")
    for sx in (-1, 1):
        low = head_pt(0.84, side=sx, up=-0.30, out=0.014)
        mid = head_pt(0.20, side=sx, up=-0.30, out=0.014)
        top = head_pt(0.10, side=sx, up=0.95, out=0.014)
        add_strap(head, low, mid, 0.03, 0.012, "leather", ref=X, ext=0.012)
        add_strap(head, mid, top, 0.03, 0.012, "leather", ref=X, ext=0.012)
        # gold ring where the cheek strap meets the noseband
        add_ring3d(head, head_pt(0.85, side=sx, up=-0.30, out=0.021), X * sx, 0.036, 0.013, "gold")
        add_buckle(head, head_pt(0.20, side=sx, up=0.30, out=0.017), (0.04, 0.05), normal=X * sx,
                   up=HEAD_F.cross(X * sx).normalized(), t=0.01)
    # bit ring + chain + reins (right and left)
    for sx in (-1, 1):
        mouth = mc0 + HEAD_F * 0.16 + hu * sx * (0.275 / 2 + 0.012) + hv * -0.075
        add_ring3d(head, mouth, X * sx, 0.036, 0.012, "gold")
        start = mouth + Vector((sx * 0.01, 0.0, -0.035))
        pts = [start]
        for i in range(1, 7):
            pts.append(start + Vector((sx * 0.012 * i, -0.028 * i, -0.030 * i + 0.002 * i * i)))
        add_chain(head, pts)
        add_ring3d(head, pts[-1] + Vector((sx * 0.004, -0.02, -0.02)), X * sx, 0.026, 0.01, "gold")
        # rein: leather strap swinging back to the pommel
        p = mouth
        end = Vector((sx * 0.05, 0.14, zt + 0.12))
        prev = p
        for i in range(1, 8):
            t = i / 7
            q = p.lerp(end, t) + Vector((sx * 0.04 * math.sin(math.pi * t) + 0.0, 0.0, -0.10 * math.sin(math.pi * t)))
            add_strap(head, prev, q, 0.022, 0.008, "leather", ref=Z, ext=0.01)
            prev = q

    # ---- tail ---------------------------------------------------------------
    tail = part("Tail", "Tail")
    add_block(tail, (0, -0.80, 0.98), (0.17, 0.13, 0.22), "hide")
    n = 11
    for i in range(n):
        a = (i / (n - 1) - 0.5) * 2  # -1 .. 1
        d = Vector((a * 0.45, -0.70 - rng.random() * 0.2, -0.38 - 0.45 * (1 - abs(a)) - rng.random() * 0.25))
        L = 0.50 + 0.20 * (1 - abs(a)) + rng.random() * 0.1
        size = (0.125 + rng.random() * 0.03, 0.085 + rng.random() * 0.02, L)
        base = Vector((a * 0.07, -0.83, 1.02 + rng.random() * 0.07 - 0.04 * abs(a)))
        add_block(tail, base + d.normalized() * L / 2, size, "mane", rot=frame_z(d, Vector((rng.uniform(-1, 1), rng.uniform(-.4, .4), rng.uniform(-.3, .3)))), ts=(0.55, 0.6), cap_mats=("CULL", None))
    for i in range(4):  # inner dark layer for volume
        a = (i / 3 - 0.5) * 1.1
        d = Vector((a * 0.35, -0.5, -0.7 - rng.random() * 0.15))
        L = 0.55 + rng.random() * 0.1
        base = Vector((a * 0.06, -0.86, 0.98))
        add_block(tail, base + d.normalized() * L / 2, (0.10, 0.07, L), "mane", rot=frame_z(d, X), ts=(0.6, 0.6), cap_mats=("CULL", None))

    # ---- legs ---------------------------------------------------------------
    def leg(name, sx, front):
        up = part(f"Leg_{name}_Up", f"{name}_Up")
        lo = part(f"Leg_{name}_Lo", f"{name}_Lo")
        x0 = sx * (0.165 if front else 0.20)
        if front:
            U = [(1.00, 0.17, 0.30, 0.52), (0.72, 0.23, 0.28, 0.52), (0.50, 0.19, 0.21, 0.53)]
            Lw = [(0.52, 0.18, 0.20, 0.53), (0.36, 0.145, 0.16, 0.535), (0.22, 0.155, 0.175, 0.535)]
            yh = 0.535
        else:
            U = [(1.00, 0.15, 0.34, -0.50), (0.78, 0.26, 0.36, -0.57), (0.54, 0.20, 0.26, -0.64)]
            Lw = [(0.56, 0.19, 0.24, -0.64), (0.38, 0.145, 0.17, -0.60), (0.22, 0.155, 0.18, -0.55)]
            yh = -0.55
        add_loft(up, [ring((x0, y, z), X, Y, w / 2, d / 2, 0.30) for z, w, d, y in U], "hide", caps=(False, True))
        add_loft(lo, [ring((x0, y, z), X, Y, w / 2, d / 2, 0.30) for z, w, d, y in Lw], "hide", caps=(True, False))
        # fetlock sock band
        add_loft(lo, [ring((x0, yh, 0.225), X, Y, 0.172 / 2, 0.192 / 2, 0.28),
                      ring((x0, yh, 0.125), X, Y, 0.182 / 2, 0.202 / 2, 0.28)], "sock", caps=(True, False))
        # hoof
        add_loft(lo, [ring((x0, yh, 0.130), X, Y, 0.200 / 2, 0.220 / 2, 0.22),
                      ring((x0, yh, 0.0), X, Y, 0.240 / 2, 0.265 / 2, 0.22)], "hoof", caps=(True, True))

    leg("FL", 1, True)
    leg("FR", -1, True)
    leg("BL", 1, False)
    leg("BR", -1, False)
    return P


# ----------------------------------------------------------------------------
# Procedural painting
# ----------------------------------------------------------------------------
def hash3(ix, iy, iz, seed):
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 +
         iz.astype(np.int64) * 1442695041 + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return (h & 0xFFFF) / 65535.0


def vnoise(x, y, z, seed=0):
    ix, iy, iz = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (fx if dx else 1 - fx) * (fy if dy else 1 - fy) * (fz if dz else 1 - fz)
                out = out + w * hash3(ix + dx, iy + dy, iz + dz, seed)
    return out


def fbm(x, y, z, seed=0, octaves=3):
    tot, amp, norm = 0, 0.5, 0
    for o in range(octaves):
        tot = tot + amp * vnoise(x * 2 ** o, y * 2 ** o, z * 2 ** o, seed + 17 * o)
        norm += amp
        amp *= 0.5
    return tot / norm


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def col(r, g, b):
    return np.array([r, g, b], dtype=np.float32)


def mix(a, b, t):
    t = np.asarray(t, dtype=np.float32)
    if t.ndim == 2:
        t = t[..., None]
    return a + (b - a) * t


class Ctx:
    pass


def finish(c, color, height, rough, metal, outline, line_w, outline_col, hilite=0.0):
    """Common post: facet tint, baked top-light, ground AO, outlined edges."""
    tint = 1.0 + (hash3(np.array(c.seed), np.array(3), np.array(5), 9) - 0.5) * 0.10
    nz = float(c.N.z)
    bake = 0.90 + 0.17 * nz
    ao = 0.80 + 0.20 * smooth(0.0, 0.45, c.z)
    color = color * (tint * bake)[..., None] if np.ndim(bake) else color * (tint * bake)
    color = color * ao[..., None]
    w = min(line_w, 0.2 * c.mind) if outline else 0
    if outline and w > 1e-4:
        ln = smooth(w, w * 0.3, c.ed)
        color = mix(color, outline_col, 0.72 * ln)
        height = height - 0.7 * ln
        if hilite:
            hl = smooth(w * 2.4, w * 1.2, c.ed) * (1 - ln)
            color = color * (1 + hilite * hl)[..., None]
    return np.clip(color, 0, 1), height, rough, metal


def paint_hide(c, muzzle=False, front=False):
    x, y, z = c.x, c.y, c.z
    s = c.seed
    n1 = fbm(x * (13 if not muzzle else 24), y * (13 if not muzzle else 24), z * (13 if not muzzle else 24), s, 3)
    n2 = fbm(x * 45, y * 45, z * 45, s + 1, 2)
    if not muzzle:
        base = mix(col(.40, .205, .095), col(.62, .36, .165), 0.6 * smooth(.30, .70, n1))
        crackcol = col(.25, .12, .05)
        outl = col(.17, .085, .04)
    else:
        base = mix(col(.60, .62, .66), col(.75, .77, .81), 0.5 * smooth(.25, .75, n1))
        crackcol = col(.30, .31, .35)
        outl = col(.22, .23, .27)
    base = base * (0.93 + 0.14 * n2)[..., None]
    # hairline cracks, sparse
    cr = 1 - smooth(0.0, 0.010, np.abs(fbm(x * 6, y * 6, z * 6, s + 2, 2) - 0.5))
    sparse = smooth(0.50, 0.70, fbm(x * 2.5, y * 2.5, z * 2.5, s + 3, 2))
    crack = cr * sparse
    base = mix(base, crackcol, 0.5 * crack)
    # dry-brush streaks along the face
    streak = fbm(c.pv * 60, c.pu * 5, np.full_like(x, s * 0.31), s + 4, 3)
    base = base * (0.90 + 0.20 * streak)[..., None]
    height = 0.5 + 0.3 * n2 - 0.4 * crack
    rough = np.full_like(x, 0.55 if muzzle else 0.82)
    metal = np.zeros_like(x)
    if front:
        for sx in (-1, 1):
            d = ((c.pu - sx * 0.055) / 0.030) ** 2 + ((c.pv + 0.02) / 0.016) ** 2
            nost = smooth(1.0, 0.6, d)
            base = mix(base, col(.13, .12, .14), nost)
            height = height - 0.6 * nost
    return finish(c, base, height, rough, metal, True, 0.0048 if not muzzle else 0.007, outl,
                  hilite=0.14 if muzzle else 0.08)


def paint_hoof(c):
    x, y, z = c.x, c.y, c.z
    s = c.seed
    n1 = fbm(x * 14, y * 14, z * 14, s, 3)
    base = mix(col(.20, .19, .22), col(.36, .35, .39), smooth(.25, .75, n1))
    scuff = smooth(0.62, 0.8, fbm(x * 30, y * 30, z * 30, s + 5, 2))
    base = mix(base, col(.45, .44, .48), 0.4 * scuff)
    cr = 1 - smooth(0.0, 0.014, np.abs(fbm(x * 8, y * 8, z * 8, s + 2, 2) - 0.5))
    base = mix(base, col(.10, .09, .11), 0.5 * cr)
    if c.N.z < -0.5:
        base = base * 0.55
    height = 0.5 + 0.3 * n1 - 0.4 * cr
    return finish(c, base, height, np.full_like(x, 0.7), np.zeros_like(x), True, 0.007, col(.08, .07, .09), 0.15)


def paint_sock(c):
    x, y, z = c.x, c.y, c.z
    s = c.seed
    n1 = fbm(x * 12, y * 12, z * 12, s, 3)
    base = mix(col(.50, .52, .57), col(.72, .74, .79), smooth(.25, .75, n1))
    g = smooth(0.12, 0.22, z)  # lighter toward the top
    base = base * (0.88 + 0.18 * g)[..., None]
    cr = 1 - smooth(0.0, 0.014, np.abs(fbm(x * 9, y * 9, z * 9, s + 2, 2) - 0.5))
    base = mix(base, col(.28, .29, .33), 0.5 * cr)
    return finish(c, base, 0.5 + 0.2 * n1 - 0.4 * cr, np.full_like(x, 0.6), np.zeros_like(x), True, 0.006,
                  col(.20, .21, .25), 0.15)


def paint_mane(c, tail=False):
    x, y, z = c.x, c.y, c.z
    s = c.seed
    grain = fbm(c.pv * 85, c.pu * 7, np.full_like(x, s * 0.37), s, 3)
    n1 = fbm(x * 10, y * 10, z * 10, s + 1, 2)
    base = mix(col(.11, .085, .075), col(.26, .19, .15), smooth(.3, .8, grain) * 0.8 + 0.2 * n1)
    base = mix(base, col(.34, .25, .19), smooth(.78, .95, grain) * 0.5)
    cr = 1 - smooth(0.0, 0.02, np.abs(fbm(x * 12, y * 12, z * 12, s + 3, 2) - 0.5))
    base = mix(base, col(.05, .04, .04), 0.55 * cr)
    height = 0.5 + 0.35 * grain - 0.3 * cr
    return finish(c, base, height, np.full_like(x, 0.9), np.zeros_like(x), True, 0.006, col(.05, .04, .04), 0.55)


# blanket border extents (set from the drape parameters in build_parts)
BL_YMIN, BL_YMAX = -0.31, 0.25
BL_LOW = ([-0.31, -0.28, -0.20, 0.08, 0.17, 0.22, 0.25], [0.02, 0.06, 0.11, 0.11, 0.11, 0.07, 0.03])


def paint_blanket(c):
    x, y, z = c.x, c.y, c.z
    s = c.seed
    w, h, zc = np.vectorize(lambda yy: tdim(yy), otypes=[float, float, float])(np.clip(y, -0.31, 0.25))
    zlow = zc - np.interp(y, BL_LOW[0], BL_LOW[1])
    # distance to the free edge of the cloth
    dy = np.minimum(y - BL_YMIN, BL_YMAX - y)
    dz = np.where(np.abs(x) > 0.18, z - zlow, 9.0)
    dist = np.minimum(dy, dz)
    weave = 0.5 + 0.5 * np.sin(x * 900) * np.sin((y + z) * 900)
    n1 = fbm(x * 14, y * 14, z * 14, s, 3)
    red = mix(col(.60, .07, .08), col(.80, .15, .13), smooth(.25, .75, n1))
    red = red * (0.94 + 0.06 * weave)[..., None]
    cream = mix(col(.86, .76, .62), col(.96, .90, .78), smooth(.3, .7, n1))
    cream = cream * (0.95 + 0.05 * weave)[..., None]
    base = mix(red, cream, smooth(0.034, 0.030, dist))
    # thin gold pinstripe just inside the border
    stripe = smooth(0.0035, 0.0012, np.abs(dist - 0.050))
    base = mix(base, col(.92, .70, .18), stripe * 0.9)
    # soft darkening where the cloth is shadowed under the saddle
    dark = 0.9 + 0.1 * smooth(0.04, 0.14, dist)
    base = base * dark[..., None]
    # border seam line
    seam = smooth(0.0018, 0.0006, np.abs(dist - 0.034))
    base = mix(base, col(.45, .30, .22), seam * 0.6)
    height = 0.5 + 0.12 * weave + 0.3 * smooth(0.034, 0.030, dist)
    return finish(c, base, height, np.full_like(x, 0.95), np.zeros_like(x), True, 0.004, col(.30, .08, .07))


def paint_leather(c, dark=False, saddle=False):
    x, y, z = c.x, c.y, c.z
    s = c.seed
    n1 = fbm(x * 11, y * 11, z * 11, s, 3)
    grain = fbm(x * 90, y * 90, z * 90, s + 1, 2)
    if dark:
        base = mix(col(.26, .15, .09), col(.42, .26, .15), smooth(.25, .75, n1))
        edge = col(.12, .07, .04)
    elif saddle:
        base = mix(col(.55, .28, .10), col(.78, .42, .16), smooth(.25, .75, n1))
        edge = col(.30, .14, .05)
    else:
        base = mix(col(.58, .27, .07), col(.78, .40, .12), smooth(.25, .75, n1))
        edge = col(.30, .13, .04)
    base = base * (0.93 + 0.14 * grain)[..., None]
    # worn scuffs
    scuff = smooth(0.66, 0.85, fbm(x * 20, y * 20, z * 20, s + 4, 2))
    base = mix(base, col(.90, .62, .35), 0.18 * scuff)
    base, height, rough, metal = finish(c, base, 0.5 + 0.25 * grain, np.full_like(x, 0.6),
                                        np.zeros_like(x), True, 0.0055, edge, 0.12)
    # stitching: dashed light line inset from the edge on larger faces
    if c.mind > 0.032:
        st = smooth(0.0016, 0.0006, np.abs(c.ed - 0.0115))
        dash = (np.sin(c.pu * 520 + c.pv * 520) > 0.1).astype(np.float32)
        st = st * dash
        base = mix(base, col(.93, .78, .55), 0.85 * st)
        height = height - 0.35 * st
    return base, height, rough, metal


def paint_gold(c):
    x, y, z = c.x, c.y, c.z
    s = c.seed
    n1 = fbm(x * 30, y * 30, z * 30, s, 2)
    grad = 0.5 + 0.5 * np.sin((c.pu + c.pv) * 55)
    base = mix(col(.78, .55, .08), col(1.0, .84, .28), 0.55 * grad + 0.45 * n1)
    base = base * (1.0 + 0.2 * smooth(0.85, 1.0, grad))[..., None]
    base, height, rough, metal = finish(c, base, 0.5 + 0.0 * n1, np.full_like(x, 0.32), np.ones_like(x), True,
                                        0.0018, col(.62, .40, .06), 0.3)
    return base, height, rough, metal


def paint_flat(c, rgb, rough=0.35, line=0.003, outl=None):
    x = c.x
    n1 = fbm(c.x * 25, c.y * 25, c.z * 25, c.seed, 2)
    base = np.tile(col(*rgb), x.shape + (1,)) * (0.97 + 0.06 * n1)[..., None]
    outl = col(*(outl if outl else [v * 0.5 for v in rgb]))
    return finish(c, base, 0.5 + 0 * n1, np.full_like(x, rough), np.zeros_like(x), True, line, outl)


PAINTERS = {
    "hide": lambda c: paint_hide(c),
    "muzzle": lambda c: paint_hide(c, muzzle=True),
    "muzzle_front": lambda c: paint_hide(c, muzzle=True, front=True),
    "hoof": paint_hoof,
    "sock": paint_sock,
    "mane": paint_mane,
    "blanket": paint_blanket,
    "leather": paint_leather,
    "leather_dark": lambda c: paint_leather(c, dark=True),
    "saddle": lambda c: paint_leather(c, saddle=True),
    "gold": paint_gold,
    "eye_white": lambda c: paint_flat(c, (.96, .95, .90), 0.3, 0.003, (.35, .3, .25)),
    "eye_pupil": lambda c: paint_flat(c, (.05, .045, .05), 0.25, 0.0015, (.0, .0, .0)),
    "ear_inner": lambda c: paint_flat(c, (.42, .21, .13), 0.8, 0.003, (.2, .08, .05)),
}


MAT_KEYS = list(PAINTERS) + ["CULL"]


# ----------------------------------------------------------------------------
# Atlas packing + baking
# ----------------------------------------------------------------------------
def polygon_edge_dist(poly, pu, pv):
    """Distance to the polygon outline in metres, 0 outside the polygon."""
    n = len(poly)
    best = np.full(pu.shape, 1e9, dtype=np.float32)
    inside = np.zeros(pu.shape, dtype=bool)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        L2 = ex * ex + ey * ey + 1e-12
        t = np.clip(((pu - ax) * ex + (pv - ay) * ey) / L2, 0, 1)
        d = np.hypot(pu - (ax + t * ex), pv - (ay + t * ey))
        best = np.minimum(best, d)
        cond = (ay > pv) != (by > pv)
        xint = ax + (pv - ay) * ex / (ey if abs(ey) > 1e-12 else 1e-12)
        inside ^= cond & (pu < xint)
    return np.where(inside, best, 0.0).astype(np.float32)


def prepare_faces(parts):
    """Fix winding with bmesh, then compute per-face tangent frames."""
    out = {}
    for part in parts.values():
        bm = bmesh.new()
        bv = [bm.verts.new(v) for v in part.verts]
        bm.verts.ensure_lookup_table()
        for idx, mat in part.faces:
            f = bm.faces.new([bv[i] for i in idx])
            f.material_index = MAT_KEYS.index(mat)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        data = []
        for f in bm.faces:
            vs = [v.index for v in f.verts]
            mat = MAT_KEYS[f.material_index]
            if mat == "CULL":
                continue
            data.append((vs, mat, f.normal.copy()))
        used = sorted({i for vs, _, _ in data for i in vs})
        remap = {old: new for new, old in enumerate(used)}
        data = [([remap[i] for i in vs], mat, n) for vs, mat, n in data]
        out[part.name] = ([bm.verts[i].co.copy() for i in used], data)
        bm.free()
    return out


def face_frame(pts, N):
    best, bi = 0, 0
    for i in range(len(pts)):
        e = pts[(i + 1) % len(pts)] - pts[i]
        if e.length > best:
            best, bi = e.length, i
    e = pts[(bi + 1) % len(pts)] - pts[bi]
    U = (e - N * e.dot(N)).normalized()
    V = N.cross(U)
    return U, V


# texel-density multipliers: plain dark hair and undersides need fewer pixels
DENSITY = {"mane": 0.55, "hoof": 0.9}


def build_atlas(prepared):
    recs = []
    for pname, (verts, faces) in prepared.items():
        for fi, (vs, mat, N) in enumerate(faces):
            pts = [verts[i] for i in vs]
            U, V = face_frame(pts, N)
            o = pts[0]
            loc = [((p - o).dot(U), (p - o).dot(V)) for p in pts]
            umin, umax = min(a for a, _ in loc), max(a for a, _ in loc)
            vmin, vmax = min(b for _, b in loc), max(b for _, b in loc)
            recs.append(dict(part=pname, fi=fi, mat=mat, N=N, U=U, V=V, o=o, loc=loc,
                             umin=umin, umax=umax, vmin=vmin, vmax=vmax))

    ppm = 700.0
    while True:
        for r in recs:
            r["ppm"] = ppm * DENSITY.get(r["mat"], 1.0) * (0.4 if r["N"].z < -0.6 else 1.0)
            r["w"] = max(3, int(math.ceil((r["umax"] - r["umin"]) * r["ppm"]))) + 2 * PAD
            r["h"] = max(3, int(math.ceil((r["vmax"] - r["vmin"]) * r["ppm"]))) + 2 * PAD
        order = sorted(recs, key=lambda r: -r["h"])
        x = y = rowh = 0
        ok = True
        for r in order:
            if x + r["w"] > ATLAS:
                x, y, rowh = 0, y + rowh, 0
            if rowh == 0:
                rowh = r["h"]
            r["x"], r["y"] = x, y
            x += r["w"]
            if y + r["h"] > ATLAS:
                ok = False
                break
        if ok:
            break
        ppm *= 0.95
    print(f"atlas: {len(recs)} faces, {ppm:.0f} px/m, used height {y + rowh}/{ATLAS}")
    return recs, ppm


def bake_textures(recs, ppm):
    color = np.zeros((ATLAS, ATLAS, 3), np.float32) + col(.4, .22, .1)
    nrm = np.zeros((ATLAS, ATLAS, 3), np.float32) + col(.5, .5, 1.0)
    rough = np.full((ATLAS, ATLAS), 0.8, np.float32)
    metal = np.zeros((ATLAS, ATLAS), np.float32)
    for k, r in enumerate(recs):
        w, h = r["w"], r["h"]
        cols = np.arange(w, dtype=np.float32)
        rows = np.arange(h, dtype=np.float32)
        pu1 = r["umin"] + (cols - PAD + 0.5) / r["ppm"]
        pv1 = r["vmax"] - (rows - PAD + 0.5) / r["ppm"]
        pu, pv = np.meshgrid(pu1, pv1)
        c = Ctx()
        c.pu, c.pv = pu.astype(np.float32), pv.astype(np.float32)
        Pw = (np.array(r["o"], dtype=np.float32)[None, None, :] + pu[..., None] * np.array(r["U"], dtype=np.float32)
              + pv[..., None] * np.array(r["V"], dtype=np.float32))
        c.x, c.y, c.z = Pw[..., 0], Pw[..., 1], Pw[..., 2]
        c.N = r["N"]
        c.seed = (k * 7919) % 100003
        c.ed = polygon_edge_dist(r["loc"], pu, pv)
        c.mind = min(r["umax"] - r["umin"], r["vmax"] - r["vmin"])
        cc, hh, rr, mm = PAINTERS[r["mat"]](c)
        gy, gx = np.gradient(hh.astype(np.float32))
        STR = 5.0
        n = np.stack([-gx * STR, gy * STR, np.ones_like(gx)], axis=-1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        sl = (slice(r["y"], r["y"] + h), slice(r["x"], r["x"] + w))
        color[sl] = cc
        nrm[sl] = n * 0.5 + 0.5
        rough[sl] = rr
        metal[sl] = mm
        if k % 500 == 0:
            print(f"  painted {k}/{len(recs)}")
    return color, nrm, rough, metal


def save_png(arr, path, gray=False):
    a = (np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(a, "L" if gray else "RGB").save(path, optimize=True)


# ----------------------------------------------------------------------------
# Blender scene
# ----------------------------------------------------------------------------
BONES = {
    # name: (head, tail, parent)
    "Root": ((0, 0, 0.02), (0, -0.25, 0.02), None),
    "Spine": ((0, -0.5, 0.92), (0, 0.5, 0.92), "Root"),
    "Neck": ((0, 0.58, 0.98), (0, 0.95, 1.46), "Spine"),
    "Head": ((0, 0.95, 1.46), (0, 1.45, 1.20), "Neck"),
    "Tail": ((0, -0.82, 1.00), (0, -1.1, 0.80), "Spine"),
    "FL_Up": ((0.165, 0.52, 0.98), (0.165, 0.53, 0.54), "Spine"),
    "FL_Lo": ((0.165, 0.53, 0.54), (0.165, 0.535, 0.0), "FL_Up"),
    "FR_Up": ((-0.165, 0.52, 0.98), (-0.165, 0.53, 0.54), "Spine"),
    "FR_Lo": ((-0.165, 0.53, 0.54), (-0.165, 0.535, 0.0), "FR_Up"),
    "BL_Up": ((0.20, -0.50, 1.0), (0.20, -0.64, 0.57), "Spine"),
    "BL_Lo": ((0.20, -0.64, 0.57), (0.20, -0.55, 0.0), "BL_Up"),
    "BR_Up": ((-0.20, -0.50, 1.0), (-0.20, -0.64, 0.57), "Spine"),
    "BR_Lo": ((-0.20, -0.64, 0.57), (-0.20, -0.55, 0.0), "BR_Up"),
}


def make_material(imgs):
    mat = bpy.data.materials.new("HorseMat")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    def tex(name, path, srgb):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(path)
        n.image.colorspace_settings.name = "sRGB" if srgb else "Non-Color"
        n.interpolation = "Linear"
        n.label = name
        return n

    c = tex("color", imgs["color"], True)
    nm = tex("normal", imgs["normal"], False)
    ro = tex("roughness", imgs["rough"], False)
    me = tex("metalness", imgs["metal"], False)
    nt.links.new(c.outputs["Color"], bsdf.inputs["Base Color"])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 0.8
    nt.links.new(nm.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(ro.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(me.outputs["Color"], bsdf.inputs["Metallic"])
    return mat


def build_scene(prepared, recs, ppm, imgs):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    mat = make_material(imgs)
    by_part = {}
    for r in recs:
        by_part.setdefault(r["part"], {})[r["fi"]] = r

    # armature
    arm_data = bpy.data.armatures.new("HorseRig")
    arm = bpy.data.objects.new("HorseRig", arm_data)
    scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (h, t, par) in BONES.items():
        b = arm_data.edit_bones.new(name)
        b.head, b.tail = Vector(h), Vector(t)
        if par:
            b.parent = arm_data.edit_bones[par]
    bpy.ops.object.mode_set(mode="OBJECT")

    objs = []
    for pname, (verts, faces) in prepared.items():
        mesh = bpy.data.meshes.new(pname)
        mesh.from_pydata([tuple(v) for v in verts], [], [f[0] for f in faces])
        mesh.update()
        uv = mesh.uv_layers.new(name="UVMap")
        for fi, poly in enumerate(mesh.polygons):
            r = by_part[pname][fi]
            for li, vi in zip(poly.loop_indices, faces[fi][0]):
                p = verts[vi]
                pu = (p - r["o"]).dot(r["U"])
                pv = (p - r["o"]).dot(r["V"])
                px = r["x"] + PAD + (pu - r["umin"]) * r["ppm"]
                py = r["y"] + PAD + (r["vmax"] - pv) * r["ppm"]
                uv.data[li].uv = (px / ATLAS, 1.0 - py / ATLAS)
            poly.use_smooth = False
        mesh.materials.append(mat)
        obj = bpy.data.objects.new(pname, mesh)
        scene.collection.objects.link(obj)
        # rigid skin to one bone
        bone = [p for p in PARTS.values() if p.name == pname][0].bone
        vg = obj.vertex_groups.new(name=bone)
        vg.add(list(range(len(verts))), 1.0, "REPLACE")
        mod = obj.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        obj.parent = arm
        objs.append(obj)
    return arm, objs, mat


def export_all(arm, objs):
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "horse.blend"), compress=True)

    def select(sel):
        bpy.ops.object.select_all(action="DESELECT")
        for o in sel:
            o.select_set(True)
        bpy.context.view_layer.objects.active = sel[0]

    # rigged FBX
    select([arm] + objs)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "horse_rigged.fbx"), use_selection=True,
                             object_types={"ARMATURE", "MESH"}, add_leaf_bones=False,
                             axis_forward="-Z", axis_up="Y", mesh_smooth_type="FACE",
                             bake_anim=False, path_mode="AUTO")
    # glb
    select([arm] + objs)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "horse.glb"), export_format="GLB", use_selection=True,
                              export_yup=True)
    # static OBJ: join copies of every part
    copies = []
    for o in objs:
        c = o.copy()
        c.data = o.data.copy()
        c.modifiers.clear()
        c.parent = None
        bpy.context.scene.collection.objects.link(c)
        copies.append(c)
    select(copies)
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = "HorseStatic"
    bpy.ops.wm.obj_export(filepath=os.path.join(OUT, "horse_static.obj"), export_selected_objects=True,
                          forward_axis="NEGATIVE_Z", up_axis="Y", export_materials=True,
                          path_mode="RELATIVE")
    print("tris (static):", sum(len(p.vertices) - 2 for p in joined.data.polygons))
    bpy.data.objects.remove(joined, do_unlink=True)


PARTS = {}


def main():
    global PARTS
    PARTS = build_parts()
    prepared = prepare_faces(PARTS)
    recs, ppm = build_atlas(prepared)
    color, nrm, rough, metal = bake_textures(recs, ppm)
    os.makedirs(OUT, exist_ok=True)
    imgs = {k: os.path.join(OUT, f"horse_{k}.png") for k in ("color", "normal", "rough", "metal")}
    imgs["rough"] = os.path.join(OUT, "horse_roughness.png")
    imgs["metal"] = os.path.join(OUT, "horse_metalness.png")
    save_png(color, imgs["color"])
    save_png(nrm, imgs["normal"])
    save_png(rough, imgs["rough"], gray=True)
    save_png(metal, imgs["metal"], gray=True)
    arm, objs, mat = build_scene(prepared, recs, ppm, imgs)
    export_all(arm, objs)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
