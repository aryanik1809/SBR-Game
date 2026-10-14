"""Shared helpers for the small low-poly Roblox-style characters (tools/build_robot.py, build_stand.py).

Geometry: chamfered lofts, faceted balls, scalloped discs, extruded outlines.
Painting: the Steel Ball Run cel-shading look (flat tones lit from the upper left, hard-edged shadows,
manga hatching, thick warm ink outlines).
Pipeline: `setup()` points tools/build_horse.py's atlas/bake/rig/export code at a new model and `build()` runs it.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402

import build_horse as bh  # noqa: E402  (imports bpy)
from build_horse import X, Y, Z, add_block, add_loft, col, fbm, mix, ring, smooth  # noqa: E402
from mathutils import Vector  # noqa: E402

V = Vector
TAU = math.tau

# ----------------------------------------------------------------------------
# Geometry
# ----------------------------------------------------------------------------


def tube_pts(part, pts, hw, hd, mat, ch=0.3, cap_mats=("CULL", "CULL")):
    """Chamfered loft along a polyline; hw/hd are half sizes along X / the other horizontal axis."""
    P = [V(p) for p in pts]
    secs = []
    for j in range(len(P)):
        t = (P[min(j + 1, len(P) - 1)] - P[max(j - 1, 0)]).normalized()
        u = t.cross(Z)
        if u.length < 1e-4:
            u = X.copy()
        u.normalize()
        v = u.cross(t).normalized()
        secs.append(ring(P[j], u, v, hw[j], hd[j], ch))
    add_loft(part, secs, mat, cap_mats=cap_mats)


def layers(part, rows, mat, ch=0.3, cap_mats=("CULL", "CULL")):
    """Stack of horizontal rings: rows of (z, half_width_x, half_depth_y[, centre_y])."""
    secs = [ring(V((0, r[3] if len(r) > 3 else 0, r[0])), X, Y, r[1], r[2], ch) for r in rows]
    add_loft(part, secs, mat, cap_mats=cap_mats)


def sphere(part, c, r, mat, seg=8, lats=(-58, -18, 18, 58)):
    """Faceted ball: stacked rings capped with flat polygons."""
    c = V(c)
    secs = []
    for lat in lats:
        a = math.radians(lat)
        rr, zz = r * math.cos(a), r * math.sin(a)
        secs.append([c + V((rr * math.cos(TAU * i / seg), rr * math.sin(TAU * i / seg), zz)) for i in range(seg)])
    add_loft(part, secs, mat)


def disc(part, c, axis, r, thick, mat, n=16, scallop=0.0, caps=("auto", "auto")):
    """Flat round plate facing `axis`. scallop > 0 alternates the radius to give a flower-like edge."""
    c, axis = V(c), V(axis).normalized()
    u = axis.cross(Z)
    if u.length < 1e-4:
        u = axis.cross(X)
    u.normalize()
    v = axis.cross(u).normalized()

    def pts(centre):
        return [centre + (u * math.cos(TAU * i / n) + v * math.sin(TAU * i / n)) * (r * (1 - scallop * (i % 2)))
                for i in range(n)]

    add_loft(part, [pts(c - axis * thick / 2), pts(c + axis * thick / 2)], mat,
             cap_mats=tuple(None if k == "auto" else k for k in caps))


def prism(part, outline, c, u, v, depth, mat):
    """Extrude a 2D outline (points in the u/v plane around centre c) along u x v by `depth`."""
    c, u, v = V(c), V(u).normalized(), V(v).normalized()
    n = u.cross(v).normalized()
    front = [c + u * a + v * b + n * depth / 2 for a, b in outline]
    back = [c + u * a + v * b - n * depth / 2 for a, b in outline]
    add_loft(part, [back, front], mat)


def heart_outline(width, height, n=18):
    """Heart silhouette (point down) centred on the origin, as (x, z) pairs."""
    pts = []
    for i in range(n):
        t = TAU * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x / 32 * width, (y + 2) / 30 * height))
    return pts


# ----------------------------------------------------------------------------
# Painting: Steel Ball Run inspired cel shading
# ----------------------------------------------------------------------------
INK = col(.19, .09, .12)  # warm brown-purple ink, never pure black
LIGHT = np.array([0.50, 0.42, 0.76])
LIGHT = LIGHT / np.linalg.norm(LIGHT)  # from the upper left of the viewer, in front
PART_BB = {}  # part name -> (z min, z max), filled by build()


def tone_index(lum):
    return 0 if lum > 0.62 else (1 if lum > -0.10 else (2 if lum > -0.50 else 3))


def toon(c, tones, ink=INK, metal=0.0, rough=0.7, overlay=None):
    """Flat cel colour for the face + hard-edged cast shadow near the part bottom + ink hatching + outline.

    tones = [lit, base, shadow, deepest]; overlay(c, colour, height, rough, metal, lum) paints details on top.
    """
    x, y, z = c.x, c.y, c.z
    s = c.seed
    N = c.N
    lum = float(N.x * LIGHT[0] + N.y * LIGHT[1] + N.z * LIGHT[2])
    idx = tone_index(lum)
    n2 = fbm(x * 70, y * 70, z * 70, s + 1, 2)
    # hard-edged shadow shape: the lower part of every body part falls into the next tone
    lo, hi = PART_BB.get(c.part, (0.0, 1.5))
    t = (z - lo) / max(hi - lo, 1e-3)
    wobble = (fbm(x * 5, y * 5, z * 5, s + 3, 2) - 0.5) * 0.14
    low_band = (t + wobble) < 0.13
    base = np.where(low_band[..., None], tones[min(idx + 1, 3)], tones[idx]).astype(np.float32)
    deep = np.logical_or(low_band, idx >= 2)
    # manga hatching: diagonal ink lines on shadow, a second crossing set on the deepest tone
    h1 = ((c.pu * 0.8 + c.pv * 0.6) / 0.021)
    line1 = (np.abs(h1 - np.floor(h1) - 0.5) < 0.17)
    h2 = ((c.pu * 0.8 - c.pv * 0.6) / 0.021)
    line2 = (np.abs(h2 - np.floor(h2) - 0.5) < 0.15)
    hatch = np.zeros_like(x)
    hatch = np.where(deep & (idx >= 2), line1 * 0.30, hatch)
    hatch = np.where(((idx >= 3) | (low_band & (idx >= 2))), np.maximum(hatch, line2 * 0.30), hatch)
    colr = mix(base, ink * 1.2, hatch)
    # rim light: a thin lighter stroke just inside the edge of lit faces
    w = min(0.0068, 0.2 * c.mind)
    if idx <= 1 and w > 1e-4:
        rim = smooth(w * 2.7, w * 1.8, c.ed) * smooth(w * 1.2, w * 1.9, c.ed)
        colr = colr * (1 + 0.16 * rim)[..., None]
    # paper grit + speckles
    colr = colr * (0.965 + 0.07 * n2)[..., None]
    sp = fbm(c.pu * 90, c.pv * 90, np.full_like(x, s * 0.1), s + 4, 1)
    colr = mix(colr, ink * 1.6, smooth(0.9, 0.97, sp) * 0.5)
    height = 0.5 + 0.12 * n2 - 0.25 * hatch
    rough_a = np.full_like(x, rough)
    metal_a = np.full_like(x, metal)
    if overlay is not None:
        colr, height, rough_a, metal_a = overlay(c, colr, height, rough_a, metal_a, lum)
    # thick ink outline on every facet edge, softened toward the inside
    if w > 1e-4:
        ln = smooth(w, w * 0.35, c.ed)
        colr = mix(colr, ink, 0.92 * ln)
        height = height - 0.6 * ln
    return np.clip(colr, 0, 1), height, rough_a, metal_a


def ellipse_mask(x, z, cx, cz, rx, rz):
    return np.hypot((x - cx) / rx, (z - cz) / rz)


def aa(dist, ppm, width=1.4):
    """Anti-aliased coverage from a signed distance in metres (positive = inside), ~`width` texels wide."""
    return np.clip(0.5 + dist * ppm / width, 0.0, 1.0)


# ----------------------------------------------------------------------------
# Pipeline glue
# ----------------------------------------------------------------------------
def setup(name, rig_name, mat_name, out, atlas, bones, painters, density=None, part_density=None, pad=3):
    """Point tools/build_horse.py's atlas/bake/rig/export code at a new model."""
    bh.OUT = out
    bh.NAME = name
    bh.RIG_NAME = rig_name
    bh.MAT_NAME = mat_name
    bh.ATLAS = atlas
    bh.PAD = pad
    bh.BONES = bones
    bh.PAINTERS.clear()
    bh.PAINTERS.update(painters)
    bh.MAT_KEYS[:] = list(bh.PAINTERS) + ["CULL"]
    bh.DENSITY.clear()
    bh.DENSITY.update(density or {})
    bh.PART_DENSITY.clear()
    bh.PART_DENSITY.update(part_density or {})


def build(parts, out, name):
    """Atlas, bake, scene and exports for a dict of Parts."""
    os.makedirs(out, exist_ok=True)
    bh.PARTS = parts
    prepared = bh.prepare_faces(parts)
    for pname, (verts, faces) in prepared.items():
        zs = [v.z for v in verts]
        PART_BB[pname] = (min(zs), max(zs))
    recs, ppm = bh.build_atlas(prepared)
    color, nrm, rough, metal = bh.bake_textures(recs, ppm)
    imgs = {k: os.path.join(out, f"{name}_{k}.png") for k in ("color", "normal")}
    imgs["rough"] = os.path.join(out, f"{name}_roughness.png")
    imgs["metal"] = os.path.join(out, f"{name}_metalness.png")
    bh.save_png(color, imgs["color"])
    bh.save_png(nrm, imgs["normal"])
    bh.save_png(rough, imgs["rough"], gray=True)
    bh.save_png(metal, imgs["metal"], gray=True)
    arm, objs, mat = bh.build_scene(prepared, recs, ppm, imgs)
    bh.export_all(arm, objs)
    print("parts:", len(objs), "done ->", out)
