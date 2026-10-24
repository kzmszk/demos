"""Lightmap (UV1) layout: planar charts packed with uniform texel density.

Faces are grouped into charts by (quantised plane, 10 m spatial cell); each chart is projected onto its
plane and the chart rectangles are shelf-packed into the unit square at the largest density that fits.
"""
import math
import numpy as np


def _plane_key(P):
    P = np.asarray(P, float)
    n = np.zeros(3)
    for i in range(len(P)):
        a = P[i]; b = P[(i + 1) % len(P)]
        n += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])])
    ln = np.linalg.norm(n)
    if ln < 1e-12:
        n = np.array([0, 0, 1.0])
    else:
        n /= ln
    az = math.degrees(math.atan2(n[1], n[0]))
    el = math.degrees(math.asin(max(-1, min(1, n[2]))))
    c = P.mean(0)
    d = float(n @ c)
    return (round(az / 8.0) if abs(el) < 80 else 0, round(el / 8.0), round(d / 0.25)), n, c


def layout(faces, size=2048, margin_px=3, cell=10.0, max_density=40.0):
    """faces: list of point lists (3D). Returns list of per-corner uv lists and the density (px/m)."""
    charts = {}
    info = []
    for fi, P in enumerate(faces):
        key, n, c = _plane_key(P)
        if n[2] > 0.6:
            # upward faces (slabs, roofs, heaps): one top-down chart per 10 m cell and 3 m height band
            ck = ('up', int(math.floor(c[0] / cell)), int(math.floor(c[1] / cell)), int(math.floor(c[2] / 3.0)))
            n = np.array([0, 0, 1.0])
        else:
            ck = key + (int(math.floor(c[0] / cell)), int(math.floor(c[1] / cell)), int(math.floor(c[2] / cell)))
        charts.setdefault(ck, []).append(fi)
        info.append(n)
    # chart projections
    ch = []
    for ck, fl in charts.items():
        N = np.mean([info[f] for f in fl], axis=0)
        N /= max(np.linalg.norm(N), 1e-9)
        if abs(N[2]) < 0.9:
            T = np.cross([0, 0, 1.0], N); T /= np.linalg.norm(T)
        else:
            T = np.array([1.0, 0, 0])
            T = T - N * (T @ N); T /= np.linalg.norm(T)
        Bv = np.cross(N, T)
        pts = [np.array(faces[f], float) for f in fl]
        proj = [np.stack([p @ T, p @ Bv], 1) for p in pts]
        allp = np.concatenate(proj)
        mn = allp.min(0); mx = allp.max(0)
        ch.append([fl, proj, mn, mx - mn])
    # binary search density
    def pack(s):
        rects = sorted(range(len(ch)), key=lambda i: -ch[i][3][1])
        x = 0; y = 0; rowh = 0
        pos = {}
        for i in rects:
            w = int(math.ceil(ch[i][3][0] * s)) + 2 * margin_px
            h = int(math.ceil(ch[i][3][1] * s)) + 2 * margin_px
            if w > size or h > size:
                return None
            if x + w > size:
                x = 0; y += rowh; rowh = 0
            if y + h > size:
                return None
            pos[i] = (x, y)
            x += w
            rowh = max(rowh, h)
        return pos
    lo, hi = 0.01, max_density
    best = None
    for it in range(22):
        mid = math.sqrt(lo * hi)
        p = pack(mid)
        if p is None:
            hi = mid
        else:
            lo = mid; best = (mid, p)
    s, pos = best
    out = [None] * len(faces)
    for i, (fl, proj, mn, ext) in enumerate(ch):
        ox, oy = pos[i]
        for f, pr in zip(fl, proj):
            uv = ((pr - mn) * s + np.array([ox + margin_px, oy + margin_px])) / size
            out[f] = [tuple(t) for t in uv]
    return out, s
