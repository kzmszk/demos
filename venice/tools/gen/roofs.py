"""Roof shapes for OSM 3D parts: gabled, skillion, round (barrel), pyramid, dome and onion; gable-end infill
walls where a roof rises above the wall top along an edge."""
import math
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon
from .mesh import triangulate
from .materials import MAT

def _frame(P, across=False, direction=None):
    """(d, n): ridge direction and its normal for a footprint; direction (compass deg) overrides."""
    if direction is not None:
        a = math.radians(direction)
        n = np.array([math.sin(a), math.cos(a)])          # downslope
        return np.array([n[1], -n[0]]), n
    mrr = P.minimum_rotated_rectangle
    xs, ys = mrr.exterior.coords.xy
    e0 = np.array([xs[1] - xs[0], ys[1] - ys[0]]); e1 = np.array([xs[2] - xs[1], ys[2] - ys[1]])
    d = e0 if np.linalg.norm(e0) >= np.linalg.norm(e1) else e1
    if across: d = e1 if d is e0 else e0
    d = d / max(np.linalg.norm(d), 1e-9)
    return d, np.array([-d[1], d[0]])

def _rings(P):
    return [list(P.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in P.interiors]

def _infill(mb, rings, zfun, ze, wall_mat, tint, seed, samples=1):
    """vertical walls between the wall top ze and the roof surface along every footprint edge."""
    for R in rings:
        n = len(R)
        for i in range(n):
            a = np.array(R[i], float); c = np.array(R[(i + 1) % n], float)
            L = float(np.linalg.norm(c - a))
            if L < 0.05: continue
            k = max(1, samples if samples > 1 else 1)
            ts = list(np.linspace(0, 1, k + 1))
            pts = [a + (c - a) * t for t in ts]
            zs = [zfun(p) for p in pts]
            if max(zs) < ze + 0.05: continue
            # extra vertex where the edge crosses a ridge/kink: refine by sampling
            fine = [a + (c - a) * t for t in np.linspace(0, 1, 9)]
            zf = [zfun(p) for p in fine]
            if samples == 1:
                j = int(np.argmax(zf))
                if 0 < j < 8 and zf[j] > max(zs) + 0.02:
                    pts = [a, fine[j], c]; zs = [zfun(a), zf[j], zfun(c)]
            V = []; T = []; UV = []
            for q, z in zip(pts, zs):
                V.append((q[0], q[1], ze)); V.append((q[0], q[1], max(z, ze)))
                u = float(np.linalg.norm(q - a)); UV += [(u, ze), (u, max(z, ze))]
            for j in range(len(pts) - 1):
                o = 2 * j
                T += [[o, o + 2, o + 3], [o, o + 3, o + 1]]
            dr = (c - a) / L; nout = np.array([dr[1], -dr[0]])     # CCW ring: right normal points out
            N = np.tile([nout[0], nout[1], 0.0], (len(V), 1))
            mb.add(np.array(V), np.array(T), N=N, UV=np.array(UV), mat=MAT[wall_mat], c0=(*tint, 0), c1=(0, 0, seed, 0))

def gabled(mb, P, ze, rh, mat, wall_mat, tint, seed, across=False, direction=None, kind='gabled'):
    """gabled / skillion / round roofs over footprint P (CCW) with ridge height rh above the wall top ze."""
    d, n = _frame(P, across, direction if kind == 'skillion' else None)
    rings = _rings(P)
    allp = np.array([p for R in rings for p in R])
    tv = allp @ n; sv = allp @ d
    t0, t1 = tv.min(), tv.max(); tc = (t0 + t1) / 2; hw = max((t1 - t0) / 2, 0.1)
    s0, s1 = sv.min() - 1, sv.max() + 1
    if kind == 'skillion':
        zfun = lambda p: ze + rh * (1.0 - (float(np.dot(p, n)) - t0) / max(t1 - t0, 0.1))
        lines_t = []
    elif kind == 'round':
        zfun = lambda p: ze + rh * math.sqrt(max(0.0, 1.0 - ((float(np.dot(p, n)) - tc) / hw) ** 2))
        lines_t = [tc + hw * math.sin(a) for a in np.linspace(-math.pi / 2, math.pi / 2, 11)[1:-1]]
    else:
        zfun = lambda p: ze + rh * (1.0 - abs(float(np.dot(p, n)) - tc) / hw)
        lines_t = [tc]
    extra = []
    for tt in lines_t:
        l = LineString([tuple(d * s0 + n * tt), tuple(d * s1 + n * tt)]).intersection(P)
        for g in (l.geoms if hasattr(l, 'geoms') else [l]):
            if g.geom_type == 'LineString' and g.length > 0.05: extra.append(list(g.coords))
    V, T = triangulate(rings, segments_extra=extra, max_area=30.0)
    if len(T) == 0: return
    Z = np.array([zfun(v) for v in V])
    P3 = np.c_[V, Z]
    # uv: along the ridge, and down the slope (slant length)
    slope = math.hypot(rh, hw) / hw if kind != 'skillion' else math.hypot(rh, t1 - t0) / max(t1 - t0, 0.1)
    UV = np.c_[V @ d, np.abs(V @ n - tc) * slope]
    mb.add_flat(P3, T, UV, mat=MAT[mat], c0=(255, 255, 255, 0), c1=(0, 0, seed, 0)) if kind != 'round' else \
        mb.add(P3, T, UV=UV, mat=MAT[mat], c1=(0, 0, seed, 0), smooth=True)
    _infill(mb, rings, zfun, ze, wall_mat, tint, seed, samples=10 if kind == 'round' else 1)

def pyramid(mb, P, ze, rh, mat, seed):
    R = _rings(P)[0]; c = P.centroid
    apex = (c.x, c.y, ze + rh)
    V = []; UV = []
    for i in range(len(R)):
        a = R[i]; b = R[(i + 1) % len(R)]
        V += [(a[0], a[1], ze), (b[0], b[1], ze), apex]
        L = math.dist(a, b); h = math.hypot(math.dist(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), (c.x, c.y)), rh)
        UV += [(0, 0), (L, 0), (L / 2, h)]
    V = np.array(V)
    mb.add(V, np.arange(len(V)).reshape(-1, 3), UV=np.array(UV), mat=MAT[mat], c1=(0, 0, seed, 0))

DOME = [(1.0, 0.0)] + [(math.cos(a), math.sin(a)) for a in np.linspace(0, math.pi / 2, 10)[1:]]
ONION = [(1.0, 0.0), (1.10, 0.10), (1.16, 0.22), (1.12, 0.36), (0.96, 0.50), (0.72, 0.64), (0.46, 0.76), (0.26, 0.86), (0.14, 0.93), (0.08, 0.98), (0.0, 1.0)]

def dome(mb, P, ze, rh, mat, seed, profile='dome'):
    """dome / onion over any footprint: rings scaled toward the centroid along the profile."""
    prof = DOME if profile == 'dome' else ONION
    R = np.array(_rings(P)[0], float)
    if len(R) < 3: return
    # resample the ring to at least 24 points so small domes stay round
    ring = shapely.LinearRing(R)
    m = max(24, len(R))
    R = np.array([ring.interpolate(t, normalized=True).coords[0] for t in np.linspace(0, 1, m, endpoint=False)])
    c = np.array([P.centroid.x, P.centroid.y])
    n = len(R); k = len(prof)
    V = []; UV = []
    per = np.r_[0, np.cumsum(np.linalg.norm(np.roll(R, -1, 0) - R, axis=1))]
    acc = 0.0
    for j, (s, h) in enumerate(prof):
        if j: acc += math.hypot((prof[j][0] - prof[j - 1][0]) * 6, (prof[j][1] - prof[j - 1][1]) * rh)
        for i in range(n + 1):
            q = c + (R[i % n] - c) * max(s, 1e-3)
            V.append((q[0], q[1], ze + rh * h)); UV.append((per[i] * max(s, 0.15), acc))
    T = []
    for j in range(k - 1):
        for i in range(n):
            a = j * (n + 1) + i; b = a + 1; cc = a + (n + 1) + 1; dd = a + (n + 1)
            T += [[a, b, cc], [a, cc, dd]]
    V = np.array(V); T = np.array(T)
    # outward-facing: footprint ring is CCW, so (b-a) x (up) points out -> check one triangle and flip if needed
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    cen = V[T].mean(1); out = cen - np.c_[np.tile(c, (len(T), 1)), np.full(len(T), ze + rh * 0.3)]
    if np.einsum('ij,ij->i', fn, out).mean() < 0: T = T[:, ::-1]
    mb.add(V, T, UV=np.array(UV), mat=MAT[mat], c1=(0, 0, seed, 0), smooth=True)
    # lantern finial
    top = ze + rh
    if profile == 'onion' or rh > 4:
        L = []
        r0 = 0.08 * math.sqrt(P.area)
        for j, (s, h) in enumerate([(1.0, 0.0), (1.0, 0.6), (0.4, 0.75), (0.15, 1.0), (0.0, 1.05)]):
            L.append((r0 * s, h * r0 * 2.2))
        _lathe(mb, c, top, L, 'gold' if profile == 'onion' else mat, seed)

def _lathe(mb, c, z0, prof, mat, seed, seg=12):
    V = []; T = []
    for j, (r, h) in enumerate(prof):
        for i in range(seg):
            a = 2 * math.pi * i / seg
            V.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), z0 + h))
    for j in range(len(prof) - 1):
        for i in range(seg):
            a = j * seg + i; b = j * seg + (i + 1) % seg
            T += [[a, b, b + seg], [a, b + seg, a + seg]]
    mb.add(np.array(V), np.array(T), mat=MAT[mat], c1=(0, 0, seed, 0), smooth=True)
