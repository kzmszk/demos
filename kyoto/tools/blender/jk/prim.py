"""Primitive shapes into a jk Builder (numpy only).  All take a material name; UVs are metres."""
import math
import numpy as np

def _frame(d):
    d = np.asarray(d, float); d = d / max(np.linalg.norm(d), 1e-12)
    up = np.array([0, 0, 1.0]) if abs(d[2]) < 0.95 else np.array([1.0, 0, 0])
    a = np.cross(d, up); a /= np.linalg.norm(a); b = np.cross(a, d)
    return d, a, b

def box(B, x0, y0, z0, x1, y1, z1, mat, tag='main', faces='all', **kw):
    """axis-aligned box (in the builder's current frame).  faces: 'all' or a string of letters from 'xXyYzZ' to keep"""
    P = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    F = {'z': [0, 3, 2, 1], 'Z': [4, 5, 6, 7], 'y': [0, 1, 5, 4], 'Y': [2, 3, 7, 6], 'x': [3, 0, 4, 7], 'X': [1, 2, 6, 5]}
    I = []
    for k, q in F.items():
        if faces != 'all' and k not in faces: continue
        I += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    B.add(P, I, mat, tag=tag, **kw)

def obox(B, p0, p1, w, h, mat, up=(0, 0, 1), tag='main', ends=True, **kw):
    """a beam from p0 to p1 with a w x h section; 'up' orients the h side"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d)
    if L < 1e-6: return
    d /= L; up = np.asarray(up, float)
    a = np.cross(d, up)
    if np.linalg.norm(a) < 1e-6: a = np.cross(d, [1.0, 0, 0])
    a /= np.linalg.norm(a); b = np.cross(a, d)
    c = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    P = [p0 + a * x + b * y for x, y in c] + [p1 + a * x + b * y for x, y in c]
    I = []
    for i in range(4):
        j = (i + 1) % 4
        I += [[i, j, j + 4], [i, j + 4, i + 4]]
    if ends: I += [[0, 3, 2], [0, 2, 1], [4, 5, 6], [4, 6, 7]]
    I = [t[::-1] for t in I]                      # outward (the list above winds inward)
    P = np.array(P)
    # uv: along the beam and around
    UV = np.array([[0, 0], [w, 0], [w + h, 0], [2 * w + h, 0]] * 2, float); UV[4:, 1] = L
    UV = UV[:, ::-1]
    B.add(P, I, mat, UV=None, tag=tag, **kw)

def cyl(B, p0, p1, r0, r1=None, seg=12, mat='wood_dark', caps=(True, True), tag='main', smooth=True, **kw):
    """tapered cylinder (pillar, post) from p0 to p1"""
    r1 = r0 if r1 is None else r1
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d, a, b = _frame(p1 - p0); L = np.linalg.norm(p1 - p0)
    P = []; UV = []
    for k, (p, r) in enumerate(((p0, r0), (p1, r1))):
        for i in range(seg + 1):
            t = 2 * math.pi * i / seg
            P.append(p + (a * math.cos(t) + b * math.sin(t)) * r); UV.append((t * r0, k * L))
    I = []
    for i in range(seg):
        I += [[i, seg + 2 + i, i + 1], [i, seg + 1 + i, seg + 2 + i]]      # outward
    P = np.array(P); UV = np.array(UV)
    N = None
    if smooth:
        N = np.array([(q - (p0 if k < seg + 1 else p1)) for k, q in enumerate(P)])
        N = N - np.outer(N @ d, d); N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
        if abs(r0 - r1) > 1e-6:
            N = N + d * ((r0 - r1) / L); N /= np.linalg.norm(N, axis=1, keepdims=True)
    B.add(P, I, mat, UV=UV, N=N, tag=tag, **kw)
    for cap, p, r, s in ((caps[0], p0, r0, -1), (caps[1], p1, r1, 1)):
        if not cap: continue
        C = [p] + [p + (a * math.cos(2 * math.pi * i / seg) + b * math.sin(2 * math.pi * i / seg)) * r for i in range(seg)]
        I2 = [[0, 1 + i, 1 + (i + 1) % seg] if s < 0 else [0, 1 + (i + 1) % seg, 1 + i] for i in range(seg)]   # outward
        B.add(np.array(C), I2, mat, tag=tag, **kw)

def lathe(B, c, prof, seg=16, mat='metal_dark', tag='main', smooth=True, **kw):
    """surface of revolution about the vertical axis through c: prof = [(r, z), ...] bottom to top"""
    c = np.asarray(c, float)
    P = []; UV = []
    acc = 0.0
    for j, (r, z) in enumerate(prof):
        if j: acc += math.hypot(r - prof[j - 1][0], z - prof[j - 1][1])
        for i in range(seg + 1):
            t = 2 * math.pi * i / seg
            P.append(c + [r * math.cos(t), r * math.sin(t), z]); UV.append((t * max(r, 0.05), acc))
    I = []
    n = seg + 1
    for j in range(len(prof) - 1):
        for i in range(seg):
            a = j * n + i
            I += [[a, a + 1, a + n + 1], [a, a + n + 1, a + n]]
    B.add(np.array(P), I, mat, UV=np.array(UV), smooth=smooth, tag=tag, **kw)

def sweep(B, path, prof, mat, up=(0, 0, 1), closed=True, tag='main', smooth=False, caps=False, **kw):
    """sweep a 2D profile [(x, y)] (x across, y up) along a 3D path (k,3)"""
    path = np.asarray(path, float); k = len(path)
    if k < 2: return
    T = np.gradient(path, axis=0); T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    up = np.asarray(up, float)
    P = []; UV = []
    m = len(prof)
    acc = 0.0
    for i in range(k):
        if i: acc += np.linalg.norm(path[i] - path[i - 1])
        a = np.cross(T[i], up); al = np.linalg.norm(a)
        a = a / al if al > 1e-6 else np.array([1.0, 0, 0])
        b = np.cross(a, T[i])
        s = 0.0
        for j, (x, y) in enumerate(prof):
            if j: s += math.hypot(x - prof[j - 1][0], y - prof[j - 1][1])
            P.append(path[i] + a * x + b * y); UV.append((acc, s))
    I = []
    mm = m if closed else m - 1
    for i in range(k - 1):
        for j in range(mm):
            a0 = i * m + j; a1 = i * m + (j + 1) % m
            I += [[a0, a1 + m, a1], [a0, a0 + m, a1 + m]]          # a CCW profile (x across, y up) faces outward
    B.add(np.array(P), I, mat, UV=np.array(UV), smooth=smooth, tag=tag, **kw)
    if caps and closed:
        for i, s in ((0, -1), (k - 1, 1)):
            base = i * m
            I2 = [[base, base + j + 1, base + j] if s > 0 else [base, base + j, base + j + 1] for j in range(1, m - 1)]
            B.add(np.array(P), I2, mat, tag=tag, **kw)

def polygon(B, pts, z, mat, up=True, tag='main', holes=(), **kw):
    """flat polygon (2D points, optional holes) at height z; earcut"""
    import mapbox_earcut as earcut
    rings = [np.asarray(pts, float)] + [np.asarray(h, float) for h in holes]
    V = np.concatenate(rings)
    ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    I = earcut.triangulate_float64(V, ends).reshape(-1, 3)
    P = np.c_[V, np.full(len(V), z) if np.isscalar(z) else z]
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    if (fn[:, 2].sum() < 0) == up: I = I[:, ::-1]
    B.add(P, I, mat, UV=V, tag=tag, **kw)

def prism(B, pts, z0, z1, mat, top_mat=None, top=True, bottom=False, tag='main', **kw):
    """vertical extrusion of a CCW 2D polygon"""
    pts = np.asarray(pts, float); n = len(pts)
    for i in range(n):
        a = pts[i]; c = pts[(i + 1) % n]
        L = np.linalg.norm(c - a)
        if L < 1e-6: continue
        P = np.array([[a[0], a[1], z0], [c[0], c[1], z0], [c[0], c[1], z1], [a[0], a[1], z1]])
        B.add(P, [[0, 1, 2], [0, 2, 3]], mat, UV=np.array([[0, z0], [L, z0], [L, z1], [0, z1]]), tag=tag, **kw)
    if top: polygon(B, pts, z1, top_mat or mat, up=True, tag=tag, **kw)
    if bottom: polygon(B, pts, z0, top_mat or mat, up=False, tag=tag, **kw)

def grid_surface(B, f, u0, u1, v0, v1, nu, nv, mat, tag='main', flip=False, smooth=True, **kw):
    """a surface P(u, v) = f(u, v) -> (x, y, z), sampled nu x nv; uv = (u, v)"""
    us = np.linspace(u0, u1, nu + 1); vs = np.linspace(v0, v1, nv + 1)
    P = np.array([f(u, v) for v in vs for u in us], float)
    UV = np.array([(u, v) for v in vs for u in us], float)
    I = []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            I += ([[a, a + 1, a + nu + 2], [a, a + nu + 2, a + nu + 1]] if not flip else [[a, a + nu + 2, a + 1], [a, a + nu + 1, a + nu + 2]])
    B.add(P, I, mat, UV=UV, smooth=smooth, tag=tag, **kw)
    return P.reshape(nv + 1, nu + 1, 3)

def rock(B, c, size, seed, mat='stone', tag='main', flat=0.6, **kw):
    """a garden stone: a displaced icosphere, flattened, sunk a little"""
    rng = np.random.default_rng(seed)
    t = (1 + 5 ** 0.5) / 2
    V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    for _ in range(2):           # subdivide
        mid = {}; F2 = []; V = list(V)
        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                p = (np.asarray(V[a]) + np.asarray(V[b])) / 2; V.append(p / np.linalg.norm(p)); mid[k] = len(V) - 1
            return mid[k]
        for a, b_, c_ in F:
            ab, bc, ca = m(a, b_), m(b_, c_), m(c_, a)
            F2 += [[a, ab, ca], [b_, bc, ab], [c_, ca, bc], [ab, bc, ca]]
        F = F2; V = np.array(V)
    d = 1 + 0.18 * np.sin(V @ rng.normal(0, 3, 3)) + 0.12 * np.sin(V @ rng.normal(0, 6, 3))
    V = V * d[:, None]
    sx, sy, sz = size * rng.uniform(0.8, 1.2), size * rng.uniform(0.7, 1.1), size * flat * rng.uniform(0.7, 1.2)
    V = V * [sx, sy, sz]
    yaw = rng.uniform(0, 2 * math.pi); cy, sy_ = math.cos(yaw), math.sin(yaw)
    V = V @ np.array([[cy, -sy_, 0], [sy_, cy, 0], [0, 0, 1]]).T
    V = V + np.asarray(c, float) - [0, 0, sz * 0.25]
    B.add(V, F, mat, smooth=True, tag=tag, **kw)
