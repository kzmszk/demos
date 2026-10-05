"""Mesh builder with per-vertex attributes for the Venice pipeline (pure numpy; runs in the venv).

Every add_* call creates its own vertices (no sharing across calls), so flat and smooth shading are
decided per call.  Attributes per vertex:
  P   float32 xyz (metres, world frame, z up)
  N   float32 normal
  UV  float32 (metres-based; the material decides the texture scale)
  MAT uint8   material id (see materials.py)
  C0  uint8x4 tint rgb + a = decay (exposed brick / peeling)
  C1  uint8x4 x = dirt, y = damp, z = seed, w = flags
"""
import math
import numpy as np
import triangle as tr

class MeshBuilder:
    def __init__(self):
        self.parts = []          # list of dicts of arrays
        self.nv = 0

    def add(self, P, I, N=None, UV=None, mat=0, c0=(255, 255, 255, 0), c1=(0, 0, 0, 0), smooth=False):
        P = np.asarray(P, np.float64).reshape(-1, 3); I = np.asarray(I, np.int64).reshape(-1, 3)
        if len(I) == 0: return
        if N is None and not smooth:      # flat: unshare corners
            fn = face_normals(P, I)
            idx = I.reshape(-1)
            P = P[idx]
            if UV is not None: UV = np.asarray(UV, np.float64).reshape(-1, 2)[idx]
            if not np.isscalar(mat): mat = np.asarray(mat)[idx]
            if np.asarray(c0).ndim == 2: c0 = np.asarray(c0)[idx]
            if np.asarray(c1).ndim == 2: c1 = np.asarray(c1)[idx]
            I = np.arange(len(P)).reshape(-1, 3)
            N = np.repeat(fn, 3, axis=0)
        elif N is None:
            N = vertex_normals(P, I)
        else:
            # explicit normals: make every triangle's winding agree with them (renderer culling + bake origin)
            Nn = np.asarray(N, np.float64).reshape(-1, 3)
            fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
            bad = np.einsum('ij,ij->i', fn, Nn[I].sum(1)) < 0
            if bad.any(): I = I.copy(); I[bad] = I[bad][:, ::-1]
        # a triangle with a repeated corner (a sliver welded shut) draws nothing and crashes Blender's custom normals
        I = I[(I[:, 0] != I[:, 1]) & (I[:, 1] != I[:, 2]) & (I[:, 0] != I[:, 2])]
        if len(I) == 0: return
        n = len(P)
        if UV is None: UV = np.zeros((n, 2))
        UV = np.asarray(UV, np.float64).reshape(-1, 2)
        mat = np.full(n, mat, np.uint8) if np.isscalar(mat) else np.asarray(mat, np.uint8)
        c0 = np.broadcast_to(np.asarray(c0, np.uint8), (n, 4)).copy() if np.asarray(c0).ndim == 1 else np.asarray(c0, np.uint8)
        c1 = np.broadcast_to(np.asarray(c1, np.uint8), (n, 4)).copy() if np.asarray(c1).ndim == 1 else np.asarray(c1, np.uint8)
        self.parts.append(dict(P=P.astype(np.float32), N=np.asarray(N, np.float32), UV=UV.astype(np.float32), MAT=mat, C0=c0, C1=c1, I=(I + self.nv).astype(np.uint32)))
        self.nv += n

    def ntri(self):
        return int(sum(len(p['I']) for p in self.parts))

    def add_flat(self, P, I, UV, **kw):
        """flat-shaded triangles with per-corner uv: P (n,3), I (m,3), UV (n,2) indexed like P."""
        P = np.asarray(P, np.float64).reshape(-1, 3); I = np.asarray(I, np.int64).reshape(-1, 3); UV = np.asarray(UV, np.float64).reshape(-1, 2)
        Pf = P[I.reshape(-1)]; UVf = UV[I.reshape(-1)]
        fn = face_normals(P, I)
        self.add(Pf, np.arange(len(Pf)).reshape(-1, 3), N=np.repeat(fn, 3, axis=0), UV=UVf, **kw)

    def add_planar(self, P, I, normal, UV, **kw):
        """planar piece with a known normal (shared vertices)."""
        P = np.asarray(P, np.float64).reshape(-1, 3)
        N = np.broadcast_to(np.asarray(normal, np.float64), P.shape)
        self.add(P, I, N=N, UV=UV, **kw)

    def merge(self, other):
        off = self.nv
        base = 0
        for p in other.parts:
            q = dict(p); q['I'] = (p['I'].astype(np.int64) - base + off).astype(np.uint32)
            n = len(p['P']); self.parts.append(q); off += n; base += n
        self.nv = off

    def arrays(self):
        if not self.parts:
            return dict(P=np.zeros((0, 3), np.float32), N=np.zeros((0, 3), np.float32), UV=np.zeros((0, 2), np.float32), MAT=np.zeros(0, np.uint8),
                        C0=np.zeros((0, 4), np.uint8), C1=np.zeros((0, 4), np.uint8), I=np.zeros((0, 3), np.uint32))
        out = {k: np.concatenate([p[k] for p in self.parts]) for k in ('P', 'N', 'UV', 'MAT', 'C0', 'C1', 'I')}
        return out

    def counts(self):
        return self.nv, sum(len(p['I']) for p in self.parts)


def face_normals(P, I):
    a, b, c = P[I[:, 0]], P[I[:, 1]], P[I[:, 2]]
    n = np.cross(b - a, c - a)
    l = np.linalg.norm(n, axis=1, keepdims=True); l[l == 0] = 1
    return n / l

def vertex_normals(P, I):
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    N = np.zeros_like(P)
    for k in range(3): np.add.at(N, I[:, k], fn)
    l = np.linalg.norm(N, axis=1, keepdims=True); l[l == 0] = 1
    return N / l


# ------------------------------------------------------------------ 2D triangulation (Shewchuk's Triangle)
def triangulate(rings, segments_extra=(), max_area=None, quality=False, holes_pts=None):
    """rings: [outer, hole1, ...] lists of 2D points (no closing duplicate). segments_extra: list of
    polylines (constraints inside).  Returns (V (n,2), T (m,3))."""
    import shapely
    from shapely.geometry import LineString
    holes = []
    lines = []
    for i, R in enumerate(rings):
        if len(R) < 3: continue
        lines.append(LineString([tuple(p[:2]) for p in R] + [tuple(R[0][:2])]))
        if i > 0: holes.append(interior_point(R))
    for pl in segments_extra:
        if len(pl) >= 2: lines.append(LineString([tuple(p[:2]) for p in pl]))
    if holes_pts: holes.extend(holes_pts)
    # node everything (splits crossings) and snap to 0.1 mm so the PSLG is clean for Triangle
    noded = shapely.node(shapely.GeometryCollection(lines))
    vid = {}; verts = []; segs = set()
    def V(c):
        k = (round(c[0] * 1e4), round(c[1] * 1e4))
        if k not in vid: vid[k] = len(verts); verts.append((k[0] * 1e-4, k[1] * 1e-4))
        return vid[k]
    for g in (noded.geoms if hasattr(noded, 'geoms') else [noded]):
        cs = list(g.coords)
        for j in range(len(cs) - 1):
            a, b = V(cs[j]), V(cs[j + 1])
            if a != b: segs.add((min(a, b), max(a, b)))
    if len(verts) < 3 or not segs: return np.zeros((0, 2)), np.zeros((0, 3), np.int64)
    A = dict(vertices=np.array(verts, np.float64), segments=np.array(sorted(segs), np.int32))
    if holes: A['holes'] = np.array(holes, np.float64)
    opts = 'p'
    if quality: opts += 'q20'
    if max_area: opts += f'a{max_area:.4f}'
    opts += 'Q'
    try:
        B = tr.triangulate(A, opts)
    except Exception:
        return np.zeros((0, 2)), np.zeros((0, 3), np.int64)
    if 'triangles' not in B: return np.zeros((0, 2)), np.zeros((0, 3), np.int64)
    return B['vertices'], B['triangles'].astype(np.int64)

def interior_point(R):
    from shapely.geometry import Polygon
    p = Polygon(R)
    if not p.is_valid: p = p.buffer(0)
    q = p.representative_point()
    return (q.x, q.y)

def poly_rings(poly, simplify=0.0):
    """shapely Polygon -> [outer, holes...] as lists of tuples (CCW outer, CW holes), no duplicate end."""
    from shapely.geometry.polygon import orient
    if simplify: poly = poly.simplify(simplify, preserve_topology=True)
    poly = orient(poly, 1.0)
    out = [list(poly.exterior.coords)[:-1]]
    for r in poly.interiors: out.append(list(r.coords)[:-1])
    return out

def tangents(P, N, UV, I):
    """per-vertex tangent (xyz, w handedness) from uv derivatives."""
    t = np.zeros_like(P); b = np.zeros_like(P)
    p0, p1, p2 = P[I[:, 0]], P[I[:, 1]], P[I[:, 2]]
    w0, w1, w2 = UV[I[:, 0]], UV[I[:, 1]], UV[I[:, 2]]
    e1, e2 = p1 - p0, p2 - p0; d1, d2 = w1 - w0, w2 - w0
    r = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    r = np.where(np.abs(r) < 1e-12, 1e-12, r)
    sd = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / r[:, None]
    td = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / r[:, None]
    for k in range(3):
        np.add.at(t, I[:, k], sd); np.add.at(b, I[:, k], td)
    t = t - N * np.sum(N * t, axis=1, keepdims=True)
    l = np.linalg.norm(t, axis=1, keepdims=True)
    bad = l[:, 0] < 1e-9
    # fallback: any vector perpendicular to n
    alt = np.cross(N, np.array([0.0, 0.0, 1.0]))
    alt2 = np.cross(N, np.array([1.0, 0.0, 0.0]))
    la = np.linalg.norm(alt, axis=1, keepdims=True)
    alt = np.where(la > 1e-6, alt, alt2)
    t[bad] = alt[bad]; l = np.linalg.norm(t, axis=1, keepdims=True); l[l == 0] = 1
    t = t / l
    w = np.where(np.sum(np.cross(N, t) * b, axis=1) < 0, -1.0, 1.0)
    return np.concatenate([t, w[:, None]], axis=1)
