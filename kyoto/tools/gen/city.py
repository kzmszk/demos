"""Generic Kyoto buildings from PLATEAU (LOD2 roofs and walls where surveyed, LOD1 boxes elsewhere with inferred roofs).

Walls carry a facade program for the shader (web/kyomat.js): u = distance along the wall plane (consistent for every
polygon of one plane), v = height above the building's ground.  C0 = tint rgb + a (floor height, dm);
C1 = (y window style, z seed, w flags: 1 street-facing, 2 party wall, 4 shop ground floor, 8 lit at dusk).
Roofs: u along the eave, v up the slope from the eave line.  Eaves (overhang strip, fascia, soffit), verges, ridge caps
with 鬼瓦, the machiya 庇 over the street front, parapets and rooftop plant on flat roofs."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point
from shapely.geometry.polygon import orient
from scipy.spatial import Voronoi
from shapely.ops import linemerge
from shapely.geometry import MultiLineString
from .mesh import MeshBuilder, triangulate
from .materials import MAT, PLASTER, EARTH, SIDING, TILE, ROOF_METAL, BENGARA

F_STREET, F_PARTY, F_SHOP, F_LIT = 1, 2, 4, 8
COARSE = [False]          # set while building the far LOD: no subdivision, no details
WS_NONE, WS_HOUSE, WS_OFFICE, WS_FLATS, WS_TEMPLE, WS_STATION = 0, 1, 2, 3, 4, 5

def _rng(seed):
    return np.random.default_rng(int(seed * 2 ** 31) + 7)

def newell(R):
    n = np.zeros(3)
    for i in range(len(R)):
        a = R[i]; b = R[(i + 1) % len(R)]
        n += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])])
    l = np.linalg.norm(n)
    return n / l if l > 1e-9 else np.array([0, 0, 1.0])

def plane_tri(rings, n, max_area):
    """triangulate planar 3D rings (exterior first) in their plane; returns V (k,3), T (m,3) wound along n."""
    R0 = np.asarray(rings[0], np.float64)
    o = R0[0]
    a = np.cross(n, [0, 0, 1.0]) if abs(n[2]) < 0.9 else np.cross(n, [1.0, 0, 0])
    a /= np.linalg.norm(a); b = np.cross(n, a)
    r2 = [[((p - o) @ a, (p - o) @ b) for p in np.asarray(R, np.float64)] for R in rings if len(R) >= 3]
    V2, T = triangulate(r2, max_area=max_area)
    if len(T) == 0: return None, None
    V = o + V2[:, :1] * a + V2[:, 1:2] * b
    # project back onto the plane exactly (input rings are planar within mm) and fix winding
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    flip = fn @ n < 0
    T = T.copy(); T[flip] = T[flip][:, ::-1]
    return V, T

class Ctx:
    """per-tile context: roads (for street-facing walls), neighbouring footprints (party walls), terrain."""
    def __init__(self, w, region, road_geom):
        self.w = w; self.T = w.terrain
        self.road = road_geom
        shapely.prepare(self.road) if road_geom is not None and not road_geom.is_empty else None
        self.btree = w.btree

    def street(self, pts):
        if self.road is None or self.road.is_empty or len(pts) == 0: return np.zeros(len(pts), bool)
        return shapely.contains_xy(self.road, pts[:, 0], pts[:, 1])

    def party(self, b, pts):
        out = np.zeros(len(pts), bool)
        if len(pts) == 0: return out
        P = shapely.points(pts)
        ii, jj = self.btree.query(P, predicate='within')
        for i, j in zip(ii, jj):
            if self.w.buildings[j] is not b: out[i] = True
        return out

def edge_classes(ctx, b, R2):
    """per outline edge (ring R2, CCW): street-facing and party flags (sampled at a few points along the edge)."""
    n = len(R2); st = np.zeros(n, bool); pa = np.zeros(n, bool)
    S = []; Q = []; idx = []
    for i in range(n):
        a = np.asarray(R2[i]); c = np.asarray(R2[(i + 1) % n]); L = np.linalg.norm(c - a)
        if L < 0.3: continue
        d = (c - a) / L; no = np.array([d[1], -d[0]])           # CCW ring: right normal is outward
        for t in (0.25, 0.5, 0.75):
            m = a + (c - a) * t
            S += [m + no * 1.6, m + no * 3.5]; Q.append(m + no * 0.45); idx.append(i)
    if not idx: return st, pa
    S = np.array(S); Q = np.array(Q); idx = np.array(idx)
    s = ctx.street(S).reshape(-1, 2).any(1)
    p = ctx.party(b, Q)
    for i in range(n):
        m = idx == i
        if m.any():
            st[i] = s[m].sum() >= 2; pa[i] = p[m].sum() >= 2
    return st, pa

# ------------------------------------------------------------------ appearance per building
def look(b):
    r = _rng(b.seed)
    k = b.kind
    L = dict(wall='wall_plaster', tint=PLASTER[r.integers(len(PLASTER))], roof='kawara', rtint=(255, 255, 255), ws=WS_HOUSE, fh=2.9, overhang=0.55,
             party_wall='wall_plaster', ptint=(170, 168, 162), shop=False, lit=r.random() < 0.45)
    if k == 'trad':
        L.update(wall='wall_plaster' if r.random() < 0.6 else 'wall_earth', tint=(PLASTER + EARTH)[r.integers(len(PLASTER) + len(EARTH))], ws=WS_NONE, fh=2.8, overhang=0.6,
                 machiya=True, bengara=r.random() < 0.18, party_wall='wall_board' if r.random() < 0.5 else 'wall_metal')
    elif k == 'house':
        modern = (b.year or 0) > 1985 or b.struct in (604, 605)
        L.update(wall='wall_siding' if modern or r.random() < 0.5 else 'wall_plaster', tint=SIDING[r.integers(len(SIDING))], fh=2.8,
                 roof=('roof_metal' if r.random() < 0.35 else 'kawara') if modern else ('kawara' if r.random() < 0.9 else 'roof_metal'),
                 rtint=ROOF_METAL[r.integers(len(ROOF_METAL))], overhang=0.5, party_wall='wall_metal' if r.random() < 0.5 else 'wall_siding')
    elif k in ('mid', 'tall'):
        flats = b.use in (412, 414) or (b.use == 461 and r.random() < 0.4)
        L.update(wall='wall_tile' if r.random() < 0.55 else 'wall_concrete', tint=TILE[r.integers(len(TILE))], roof='roof_flat', ws=WS_FLATS if flats else WS_OFFICE,
                 fh=3.0 if flats else 3.4, overhang=0.0, shop=b.use in (402, 404, 413, 414) or (not flats and r.random() < 0.5), party_wall='wall_concrete')
        if k == 'tall' and r.random() < 0.3: L.update(wall='glass_curtain', tint=(90, 110, 130))
    elif k == 'shed':
        L.update(wall='wall_metal', tint=SIDING[r.integers(len(SIDING))], roof='roof_metal', rtint=ROOF_METAL[r.integers(len(ROOF_METAL))], ws=WS_NONE, overhang=0.25, lit=False)
    elif k in ('temple', 'shrine'):
        L.update(wall='temple_wall', tint=(232, 228, 216), roof='hongawara' if k == 'temple' else 'copper', ws=WS_TEMPLE, fh=3.5, overhang=1.1, lit=False)
    elif k == 'station':
        L.update(wall='glass_curtain', tint=(110, 130, 150), roof='roof_flat', ws=WS_STATION, fh=4.0, overhang=0.0)
    return L

# ------------------------------------------------------------------ walls
def add_wall_poly(mb, rings, n, zg, zb, L, flags, seed):
    """a vertical wall polygon: subdivided for the bake, bottom extended down to zb (below the terrain)."""
    rings = [np.array(R, np.float64) for R in rings]
    zmin = min(R[:, 2].min() for R in rings)
    for R in rings:
        low = R[:, 2] < zmin + 0.05
        R[low, 2] = min(zmin, zb)
    V, T = plane_tri(rings, n, None if COARSE[0] else 5.0)
    if V is None: return
    t = np.array([-n[1], n[0]]); tl = np.linalg.norm(t)
    if tl < 1e-6: return
    t /= tl
    U = V[:, :2] @ t
    UV = np.stack([U, V[:, 2] - zg], 1)
    N = np.tile([n[0], n[1], 0.0], (len(V), 1))
    mat = MAT[L['wall_mat']]
    mb.add(V, T, N=N, UV=UV, mat=mat, c0=(*L['wall_tint'], int(round(L['fh'] * 10))), c1=(0, L['ws'], int(seed * 255), flags))

def wall_quad(mb, a, c, z0, z1, zg, mat, tint, fh, ws, flags, seed, n=None):
    """vertical wall over the segment a->c (outward = right of a->c), subdivided ~1.5 x 1.5 m."""
    a = np.asarray(a, float); c = np.asarray(c, float); L = np.linalg.norm(c - a)
    if L < 0.05 or z1 - z0 < 0.02: return
    d = (c - a) / L; no = np.array([d[1], -d[0]])
    nu = 1 if COARSE[0] else max(1, int(math.ceil(L / 3.0))); nz = 1 if COARSE[0] else max(1, int(math.ceil((z1 - z0) / 2.0)))
    us = np.linspace(0, 1, nu + 1); zs = np.linspace(z0, z1, nz + 1)
    P = np.array([(a[0] + (c[0] - a[0]) * u, a[1] + (c[1] - a[1]) * u, z) for z in zs for u in us])
    T = []
    for j in range(nz):
        for i in range(nu):
            p = j * (nu + 1) + i
            T += [[p, p + 1, p + nu + 2], [p, p + nu + 2, p + nu + 1]]
    T = np.array(T)
    t = np.array([-no[1], no[0]])
    UV = np.stack([P[:, :2] @ t, P[:, 2] - zg], 1)
    mb.add(P, T, N=np.tile([no[0], no[1], 0.0], (len(P), 1)), UV=UV, mat=MAT[mat], c0=(*tint, int(round(fh * 10))), c1=(0, ws, int(seed * 255), flags))

# ------------------------------------------------------------------ roofs
def slope_frame(n):
    """horizontal eave direction t (u) and the up-slope direction s (v) of a roof plane with normal n (up)."""
    h = np.array([n[0], n[1], 0.0]); hl = np.linalg.norm(h)
    if hl < 1e-6: return np.array([1.0, 0, 0]), np.array([0, 1.0, 0])
    h /= hl
    t = np.array([-h[1], h[0], 0.0])
    s = np.cross(n, t); s /= np.linalg.norm(s)
    if s[2] < 0: s = -s
    return t, s

def add_roof_poly(mb, rings, L, seed, flat_mat='roof_flat'):
    rings = [np.asarray(R, np.float64) for R in rings if len(R) >= 3]
    if not rings: return None
    n = newell(rings[0])
    if n[2] < 0: n = -n
    flat = n[2] > 0.985
    V, T = plane_tri(rings, n, None if COARSE[0] else 8.0)
    if V is None: return None
    if flat:
        UV = V[:, :2].copy(); mat = MAT[flat_mat]; c0 = (200, 200, 200, 0)
    else:
        t, s = slope_frame(n)
        z0 = min(R[:, 2].min() for R in rings)
        UV = np.stack([V @ t, (V[:, 2] - z0) / max(s[2], 0.05)], 1)
        mat = MAT[L['roof']]; c0 = (*L['rtint'], 0)
    mb.add(V, T, N=np.tile(n, (len(V), 1)), UV=UV, mat=mat, c0=c0, c1=(0, 0, int(seed * 255), 0))
    return dict(n=n, flat=flat, rings=rings)

def eave_strip(mb, a, c, n_roof, o, L, seed, ext=(0.0, 0.0), fascia=0.16, soffit=True):
    if COARSE[0]: return
    """overhang continuing the roof plane past the edge a->c (3D, horizontal), outward horizontally, by o metres."""
    a = np.asarray(a, float); c = np.asarray(c, float)
    E = c - a; El = np.linalg.norm(E[:2])
    if El < 0.2 or o < 0.05: return
    d = E / np.linalg.norm(E)
    no = np.array([d[1], -d[0], 0.0])
    t, s = slope_frame(n_roof)
    if no @ s > 0: no = -no                                       # outward = down the slope
    # move down-slope in the roof plane so that the horizontal reach is o
    dn = -s * (o / max(np.hypot(s[0], s[1]), 0.2))
    a0 = a - d * ext[0]; c0 = c + d * ext[1]
    a1 = a0 + dn - d * 0.0; c1 = c0 + dn
    P = np.array([a0, c0, c1, a1])
    zr = a[2]
    UV = np.stack([P @ t, (P[:, 2] - zr) / max(s[2], 0.05)], 1)
    mb.add(P, [[0, 1, 2], [0, 2, 3]], N=np.tile(n_roof, (4, 1)), UV=UV, mat=MAT[L['roof']], c0=(*L['rtint'], 0), c1=(0, 0, int(seed * 255), 0))
    # fascia (鼻隠し) under the outer edge and the soffit back to the wall
    f0 = a1; f1 = c1; f2 = c1 - np.array([0, 0, fascia]); f3 = a1 - np.array([0, 0, fascia])
    nf = np.array([no[0], no[1], 0.0])
    tf = np.array([-nf[1], nf[0], 0.0])
    Pf = np.array([f0, f1, f2, f3])
    mb.add(Pf, [[0, 1, 2], [0, 2, 3]], N=np.tile(nf, (4, 1)), UV=np.stack([Pf @ tf, Pf[:, 2]], 1), mat=MAT['eave_wood'], c0=(255, 255, 255, 0), c1=(0, 1, int(seed * 255), 0))
    if soffit:
        s0 = a0 - np.array([0, 0, fascia]); s1 = c0 - np.array([0, 0, fascia])
        Ps = np.array([s0, s1, f2, f3])
        mb.add(Ps, [[0, 2, 1], [0, 3, 2]], N=np.tile([0, 0, -1.0], (4, 1)), UV=np.stack([Ps @ t, Ps @ np.array([no[0], no[1], 0])], 1), mat=MAT['eave_wood'],
               c0=(255, 255, 255, 0), c1=(0, 2, int(seed * 255), 0))

def ridge_cap(mb, a, c, w, h, seed, ends=(False, False), oni=0.0):
    if COARSE[0]: return
    """棟: a capped stack along a->c (3D), w wide, h tall above the line; 鬼瓦 plates at the ends when asked."""
    a = np.asarray(a, float); c = np.asarray(c, float); E = c - a; Lx = np.linalg.norm(E)
    if Lx < 0.2: return
    d = E / Lx
    side = np.cross(d, [0, 0, 1.0]); sl = np.linalg.norm(side)
    side = side / sl if sl > 1e-6 else np.array([1.0, 0, 0])
    up = np.cross(side, d); up /= np.linalg.norm(up)
    if up[2] < 0: up = -up
    prof = [(-w * 0.5, -0.05), (-w * 0.5, h * 0.75), (-w * 0.32, h), (w * 0.32, h), (w * 0.5, h * 0.75), (w * 0.5, -0.05)]
    k = len(prof)
    P = []; UV = []
    for t, p in ((0.0, a), (Lx, c)):
        for (x, y) in prof:
            P.append(p + side * x + up * y); UV.append((t, y + x))
    P = np.array(P); T = []
    for i in range(k - 1):
        T += [[i, k + i, k + i + 1], [i, k + i + 1, i + 1]]
    T = np.array(T)
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    cen = P[T].mean(1); mid = (a + c) / 2 + up * h * 0.4
    if (np.einsum('ij,ij->i', fn, cen - mid) < 0).mean() > 0.5: T = T[:, ::-1]
    mb.add_flat(P, T, np.array(UV), mat=MAT['ridge'], c0=(255, 255, 255, 0), c1=(0, 0, int(seed * 255), 0))
    # end caps / 鬼瓦
    for e, p, sgn in ((ends[0], a, -1), (ends[1], c, 1)):
        hh = h + (oni if e else 0.0); ww = w * (1.5 if e else 1.0)
        q = p + d * sgn * (0.06 if e else 0.0)
        Q = np.array([q - side * ww / 2 - up * 0.05, q + side * ww / 2 - up * 0.05, q + side * ww / 2 + up * hh * 0.8, q + side * ww * 0.3 + up * hh, q - side * ww * 0.3 + up * hh, q - side * ww / 2 + up * hh * 0.8])
        TT = np.array([[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5]])
        nn = d * sgn
        f = np.cross(Q[1] - Q[0], Q[2] - Q[0])
        if f @ nn < 0: TT = TT[:, ::-1]
        mb.add(Q, TT, N=np.tile(nn, (6, 1)), UV=np.stack([Q @ side, Q @ up], 1), mat=MAT['ridge'], c0=(255, 255, 255, 0), c1=(0, 1 if e else 0, int(seed * 255), 0))

def _key(p): return (round(float(p[0]) * 20), round(float(p[1]) * 20), round(float(p[2]) * 20))

def roof_details(mb, b, P2, roofs, L, ctx, st_edges):
    if COARSE[0]: return
    """eaves along the outline, ridge caps on shared upper edges of LOD2 roof polygons."""
    o = L['overhang']
    seed = b.seed
    pitched = [r for r in roofs if r and not r['flat']]
    if not pitched: return
    edges = {}
    for ri, r in enumerate(pitched):
        R = r['rings'][0]; m = len(R)
        for i in range(m):
            a = R[i]; c = R[(i + 1) % m]
            k = tuple(sorted([_key(a), _key(c)]))
            edges.setdefault(k, []).append((ri, a, c))
    party_poly = None
    for k, lst in edges.items():
        if len(lst) >= 2:
            # shared: ridge or hip if the edge is the top of both polygons locally (valleys are left alone)
            (r0, a, c), (r1, _, _) = lst[0], lst[1]
            mz = (a[2] + c[2]) / 2
            hi = all(mz >= pitched[r]['rings'][0][:, 2].mean() - 0.05 for r in (r0, r1))
            if not hi: continue
            horiz = abs(a[2] - c[2]) < 0.15
            if horiz:
                ends = []
                for p in (a, c):
                    ends.append(not shapely.contains_xy(P2, p[0], p[1]) or shapely.distance(P2.exterior, Point(p[0], p[1])) < 0.6)
                big = b.kind in ('trad', 'temple', 'shrine')
                ridge_cap(mb, a, c, 0.30 if big else 0.24, 0.36 if big else 0.2, seed, ends=tuple(ends), oni=0.25 if big else 0.1)
            else:
                ridge_cap(mb, a, c, 0.22, 0.14, seed)
        elif o > 0.05:
            ri, a, c = lst[0]
            n = pitched[ri]['n']
            mid = (a + c) / 2
            E = c - a; El = np.linalg.norm(E[:2])
            if El < 0.4: continue
            d2 = E[:2] / El; no = np.array([d2[1], -d2[0]])
            t, s = slope_frame(n)
            if no @ s[:2] > 0: no = -no
            q = mid[:2] + no * 0.45
            if shapely.contains_xy(P2, q[0], q[1]): continue                 # an inner edge (roof step)
            if ctx.party(b, q[None, :])[0]: continue                          # a neighbour's roof: no overhang
            if abs(a[2] - c[2]) < 0.12:                                       # eave
                if abs(mid[2] - pitched[ri]['rings'][0][:, 2].min()) > 0.3: continue
                eave_strip(mb, a, c, n, o, L, seed, ext=(o * 0.5, o * 0.5))
            else:                                                             # verge (けらば): extend sideways in the roof plane
                vo = min(0.4, o * 0.7)
                nh = np.array([no[0], no[1], 0.0])
                P = np.array([a, c, c + nh * vo, a + nh * vo])
                UV = np.stack([P @ t, (P[:, 2] - min(a[2], c[2])) / max(s[2], 0.05)], 1)
                mb.add(P, [[0, 1, 2], [0, 2, 3]], N=np.tile(n, (4, 1)), UV=UV, mat=MAT[L['roof']], c0=(*L['rtint'], 0), c1=(0, 0, int(seed * 255), 0))
                # bargeboard (破風) under the verge
                B = np.array([a + nh * vo, c + nh * vo, c + nh * vo - [0, 0, 0.2], a + nh * vo - [0, 0, 0.2]])
                tf = np.array([-nh[1], nh[0], 0.0])
                mb.add(B, [[0, 1, 2], [0, 2, 3]], N=np.tile(nh, (4, 1)), UV=np.stack([B @ tf, B[:, 2]], 1), mat=MAT['eave_wood'], c0=(255, 255, 255, 0), c1=(0, 1, int(seed * 255), 0))

# ------------------------------------------------------------------ inferred roofs (LOD1)
def medial_axis(poly, spacing=0.4):
    rings = [list(poly.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in poly.interiors]
    pts = []; own = []; eid = 0
    for R in rings:
        n = len(R)
        for i in range(n):
            a = np.array(R[i]); c = np.array(R[(i + 1) % n]); L = np.linalg.norm(c - a)
            k = max(2, int(L / spacing))
            for j in range(k):
                pts.append(a + (c - a) * (j + 0.5) / k); own.append(eid)
            eid += 1
    pts = np.array(pts)
    if len(pts) < 4: return []
    vor = Voronoi(pts)
    V = vor.vertices
    inside = shapely.contains_xy(poly, V[:, 0], V[:, 1]) if len(V) else np.zeros(0, bool)
    segs = []
    for (pa, pb), (va, vb) in zip(vor.ridge_points, vor.ridge_vertices):
        if va < 0 or vb < 0 or own[pa] == own[pb] or not (inside[va] and inside[vb]): continue
        segs.append((tuple(V[va]), tuple(V[vb])))
    if not segs: return []
    ml = linemerge(MultiLineString(segs))
    lines = [ml] if ml.geom_type == 'LineString' else list(ml.geoms)
    return [list(l.simplify(0.15).coords) for l in lines if l.length > 0.3]

def hip_roof(mb, b, P, ze, pitch, L, ctx, st, pa):
    """寄棟-like roof from the medial axis (exact for rectangles), eaves on free edges, ridge caps on the axis."""
    P = orient(P.simplify(0.15, preserve_topology=True), 1.0)
    if P.is_empty or P.area < 4: return
    ma = medial_axis(P)
    rings = [list(P.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in P.interiors]
    V, T = triangulate(rings, segments_extra=ma, max_area=None if COARSE[0] else 8.0)
    if len(T) == 0: return
    d = shapely.distance(P.boundary, shapely.points(V))
    Z = ze + d * pitch
    V3 = np.c_[V, Z]
    # per triangle: plane normal -> uv frame; flat-shaded
    Pf = V3[T.reshape(-1)]; I = np.arange(len(Pf)).reshape(-1, 3)
    fn = np.cross(Pf[I[:, 1]] - Pf[I[:, 0]], Pf[I[:, 2]] - Pf[I[:, 0]]); fl = np.linalg.norm(fn, axis=1, keepdims=True); fl[fl == 0] = 1; fn /= fl
    fn[fn[:, 2] < 0] *= -1
    UV = np.zeros((len(Pf), 2))
    for k in range(len(I)):
        t, s = slope_frame(fn[k]); q = Pf[I[k]]
        UV[I[k]] = np.stack([q @ t, (q[:, 2] - ze) / max(s[2], 0.05)], 1)
    mb.add(Pf, I, N=np.repeat(fn, 3, axis=0), UV=UV, mat=MAT[L['roof']], c0=(*L['rtint'], 0), c1=(0, 0, int(b.seed * 255), 0))
    # ridges along the axis
    for l in ma:
        for i in range(len(l) - 1):
            a = np.array(l[i]); c = np.array(l[i + 1])
            za, zc = ze + shapely.distance(P.boundary, Point(a)) * pitch, ze + shapely.distance(P.boundary, Point(c)) * pitch
            horiz = abs(za - zc) < 0.1
            ridge_cap(mb, np.r_[a, za], np.r_[c, zc], 0.28 if horiz else 0.2, 0.3 if horiz and b.kind == 'trad' else 0.16, b.seed)
    # eaves
    R = rings[0]; n = len(R)
    for i in range(n):
        if pa[i] if i < len(pa) else False: continue
        a = np.r_[R[i], ze]; c = np.r_[R[(i + 1) % n], ze]
        E = c - a; El = np.linalg.norm(E)
        if El < 0.4: continue
        d2 = E[:2] / El; no = np.array([d2[1], -d2[0]])
        nr = np.array([no[0] * pitch, no[1] * pitch, 1.0]); nr /= np.linalg.norm(nr)
        eave_strip(mb, a, c, nr, L['overhang'], L, b.seed, ext=(L['overhang'] * 0.5, L['overhang'] * 0.5))

def gable_roof(mb, b, P, ze, pitch, L, ctx, st, pa):
    """切妻 over the footprint: ridge along the street when the building faces one, else along the long axis."""
    P = orient(P.simplify(0.15, preserve_topology=True), 1.0)
    if P.is_empty or P.area < 4: return
    R = list(P.exterior.coords)[:-1]
    d = None
    if st.any():
        # the longest street-facing edge sets the ridge direction (平入り)
        best = -1
        for i in range(len(R)):
            if i < len(st) and st[i]:
                a = np.array(R[i]); c = np.array(R[(i + 1) % len(R)]); l = np.linalg.norm(c - a)
                if l > best: best = l; d = (c - a) / max(l, 1e-6)
    if d is None:
        mrr = P.minimum_rotated_rectangle; xs, ys = mrr.exterior.coords.xy
        e0 = np.array([xs[1] - xs[0], ys[1] - ys[0]]); e1 = np.array([xs[2] - xs[1], ys[2] - ys[1]])
        d = e0 if np.linalg.norm(e0) >= np.linalg.norm(e1) else e1; d = d / np.linalg.norm(d)
    n = np.array([-d[1], d[0]])
    pts = np.array(R)
    tv = pts @ n; t0, t1 = tv.min(), tv.max(); tc = (t0 + t1) / 2; hw = max((t1 - t0) / 2, 0.5)
    sv = pts @ d; s0, s1 = sv.min() - 1, sv.max() + 1
    line = LineString([tuple(d * s0 + n * tc), tuple(d * s1 + n * tc)]).intersection(P)
    extra = [list(g.coords) for g in (line.geoms if hasattr(line, 'geoms') else [line]) if g.geom_type == 'LineString' and g.length > 0.1]
    V, T = triangulate([R] + [list(r.coords)[:-1] for r in P.interiors], segments_extra=extra, max_area=None if COARSE[0] else 8.0)
    if len(T) == 0: return
    zf = lambda q: ze + pitch * (hw - np.abs(q @ n - tc))
    Z = zf(V)
    V3 = np.c_[V, Z]
    Pf = V3[T.reshape(-1)]; I = np.arange(len(Pf)).reshape(-1, 3)
    fn = np.cross(Pf[I[:, 1]] - Pf[I[:, 0]], Pf[I[:, 2]] - Pf[I[:, 0]]); fl = np.linalg.norm(fn, axis=1, keepdims=True); fl[fl == 0] = 1; fn /= fl
    fn[fn[:, 2] < 0] *= -1
    UV = np.zeros((len(Pf), 2))
    for k in range(len(I)):
        t, s = slope_frame(fn[k]); q = Pf[I[k]]
        UV[I[k]] = np.stack([q @ t, (q[:, 2] - ze) / max(s[2], 0.05)], 1)
    mb.add(Pf, I, N=np.repeat(fn, 3, axis=0), UV=UV, mat=MAT[L['roof']], c0=(*L['rtint'], 0), c1=(0, 0, int(b.seed * 255), 0))
    # gable infill walls + eaves / verges per edge
    n_ = len(R)
    for i in range(n_):
        a2 = np.array(R[i]); c2 = np.array(R[(i + 1) % n_]); E = c2 - a2; El = np.linalg.norm(E)
        if El < 0.3: continue
        za, zc = float(zf(a2[None])[0]), float(zf(c2[None])[0])
        # gable wall above the eave line (a triangle / trapezoid with the ridge point if the edge crosses it)
        ta, tcc = (a2 @ n) - tc, (c2 @ n) - tc
        pts3 = [np.r_[a2, ze], np.r_[c2, ze], np.r_[c2, zc]]
        if ta * tcc < 0:
            f = ta / (ta - tcc); m = a2 + (c2 - a2) * f
            pts3 += [np.r_[m, ze + pitch * hw]]
        pts3 += [np.r_[a2, za]]
        Q = np.array(pts3)
        if Q[:, 2].max() > ze + 0.05:
            no = np.array([E[1], -E[0], 0.0]) / El
            tt = np.array([-no[1], no[0], 0.0])
            k = len(Q); TT = np.array([[0, j, j + 1] for j in range(1, k - 1)])
            fnq = np.cross(Q[TT[:, 1]] - Q[TT[:, 0]], Q[TT[:, 2]] - Q[TT[:, 0]])
            if (fnq @ no).mean() < 0: TT = TT[:, ::-1]
            mb.add(Q, TT, N=np.tile(no, (k, 1)), UV=np.stack([Q @ tt, Q[:, 2] - b._zg], 1), mat=MAT[L['wall_mat']], c0=(*L['wall_tint'], int(L['fh'] * 10)), c1=(0, 0, int(b.seed * 255), 0))
        if i < len(pa) and pa[i]: continue
        a3 = np.r_[a2, za]; c3 = np.r_[c2, zc]
        if abs(za - zc) < 0.1 and abs(za - ze) < 0.1:
            no2 = np.array([E[1], -E[0]]) / El
            nr = np.array([no2[0] * pitch, no2[1] * pitch, 1.0]); nr /= np.linalg.norm(nr)
            eave_strip(mb, a3, c3, nr, L['overhang'], L, b.seed, ext=(0.35, 0.35))
    # ridge cap
    for g in extra:
        a = np.array(g[0]); c = np.array(g[-1])
        ridge_cap(mb, np.r_[a, ze + pitch * hw], np.r_[c, ze + pitch * hw], 0.3, 0.36 if b.kind == 'trad' else 0.22, b.seed, ends=(True, True), oni=0.22)

# ------------------------------------------------------------------ the machiya street front: 庇 (lean-to) over the ground floor
def hisashi(mb, b, a, c, zg, L, depth=0.85, z=2.75):
    if COARSE[0]: return
    a = np.asarray(a, float); c = np.asarray(c, float); E = c - a; El = np.linalg.norm(E)
    if El < 1.5: return
    d = E / El; no = np.array([d[1], -d[0]])
    drop = depth * 0.32
    a0 = np.r_[a + d * 0.02, zg + z]; c0 = np.r_[c - d * 0.02, zg + z]
    a1 = np.r_[a + d * 0.02 + no * depth, zg + z - drop]; c1 = np.r_[c - d * 0.02 + no * depth, zg + z - drop]
    n = np.array([no[0] * 0.32, no[1] * 0.32, 1.0]); n /= np.linalg.norm(n)
    t, s = slope_frame(n)
    P = np.array([a0, c0, c1, a1])
    UV = np.stack([P @ t, (P[:, 2] - (zg + z - drop)) / max(s[2], 0.05)], 1)
    Lk = dict(L); Lk['roof'] = 'kawara'; Lk['rtint'] = (255, 255, 255)
    mb.add(P, [[0, 1, 2], [0, 2, 3]], N=np.tile(n, (4, 1)), UV=UV, mat=MAT['kawara'], c0=(255, 255, 255, 0), c1=(0, 0, int(b.seed * 255), 0))
    # 一文字瓦 edge + fascia, soffit
    f = 0.12
    F = np.array([a1, c1, c1 - [0, 0, f], a1 - [0, 0, f]])
    nf = np.array([no[0], no[1], 0.0]); tf = np.array([-nf[1], nf[0], 0.0])
    mb.add(F, [[0, 1, 2], [0, 2, 3]], N=np.tile(nf, (4, 1)), UV=np.stack([F @ tf, F[:, 2]], 1), mat=MAT['ridge'], c0=(255, 255, 255, 0), c1=(0, 2, int(b.seed * 255), 0))
    S = np.array([a0 - [0, 0, f], c0 - [0, 0, f], c1 - [0, 0, f], a1 - [0, 0, f]])
    mb.add(S, [[0, 2, 1], [0, 3, 2]], N=np.tile([0, 0, -1.0], (4, 1)), UV=np.stack([S @ t, S @ nf], 1), mat=MAT['eave_wood'], c0=(255, 255, 255, 0), c1=(0, 2, int(b.seed * 255), 0))
    # the end boards
    for p, q in ((a0, a1), (c0, c1)):
        Q = np.array([p, q, q - [0, 0, f], p - [0, 0, f + 0.05]])
        nn = np.r_[-d, 0] if p is a0 else np.r_[d, 0]
        TT = np.array([[0, 1, 2], [0, 2, 3]])
        if np.cross(Q[1] - Q[0], Q[2] - Q[0]) @ nn < 0: TT = TT[:, ::-1]
        mb.add(Q, TT, N=np.tile(nn, (4, 1)), UV=np.stack([Q @ np.r_[no, 0], Q[:, 2]], 1), mat=MAT['eave_wood'], c0=(255, 255, 255, 0), c1=(0, 1, int(b.seed * 255), 0))

# ------------------------------------------------------------------ flat-roof extras
def parapet(mb, b, R, zt, L, h=0.9, th=0.2):
    if COARSE[0]: return
    n = len(R)
    for i in range(n):
        a = np.array(R[i]); c = np.array(R[(i + 1) % n]); E = c - a; El = np.linalg.norm(E)
        if El < 0.3: continue
        d = E / El; no = np.array([d[1], -d[0]])
        wall_quad(mb, a, c, zt, zt + h, b._zg, L['wall_mat'], L['wall_tint'], L['fh'], WS_NONE, 0, b.seed)
        ai = a - no * th; ci = c - no * th
        wall_quad(mb, ci, ai, zt, zt + h, b._zg, 'wall_concrete', (170, 168, 162), 3.0, WS_NONE, 0, b.seed)
        Q = np.array([np.r_[a, zt + h], np.r_[c, zt + h], np.r_[ci, zt + h], np.r_[ai, zt + h]])
        mb.add(Q, [[0, 2, 1], [0, 3, 2]], N=np.tile([0, 0, 1.0], (4, 1)), UV=Q[:, :2], mat=MAT['curb'], c0=(255, 255, 255, 0), c1=(0, 0, int(b.seed * 255), 0))

def box(mb, cx, cy, z0, sx, sy, sz, yaw, mat, tint=(200, 200, 200), seed=0.0, top=True):
    c, s = math.cos(yaw), math.sin(yaw)
    R = [(-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2)]
    R = [(cx + x * c - y * s, cy + x * s + y * c) for x, y in R]
    for i in range(4):
        wall_quad(mb, R[i], R[(i + 1) % 4], z0, z0 + sz, z0, mat, tint, 3.0, WS_NONE, 0, seed)
    if top:
        Q = np.array([(*p, z0 + sz) for p in R])
        mb.add(Q, [[0, 1, 2], [0, 2, 3]], N=np.tile([0, 0, 1.0], (4, 1)), UV=Q[:, :2], mat=MAT['roof_flat'], c0=(*tint, 0), c1=(0, 0, int(seed * 255), 0))

def rooftop(mb, b, P, zt):
    if COARSE[0]: return
    r = _rng(b.seed + 0.37)
    if P.area < 60: return
    inner = P.buffer(-1.5)
    if inner.is_empty: return
    x0, y0, x1, y1 = inner.bounds
    yaw = math.atan2(*np.diff(np.array(P.minimum_rotated_rectangle.exterior.coords)[:2], axis=0)[0][::-1])
    k = 0
    for _ in range(12):
        if k >= 1 + int(P.area / 250): break
        x, y = r.uniform(x0, x1), r.uniform(y0, y1)
        if not inner.contains(Point(x, y)): continue
        kind = r.random()
        if kind < 0.45: box(mb, x, y, zt, 1.0, 0.45, 0.9, yaw, 'metal_grey', seed=b.seed)                     # AC units
        elif kind < 0.7: box(mb, x, y, zt, 2.6, 3.2, 2.8, yaw, b._L['wall_mat'], b._L['wall_tint'], b.seed)   # stair / lift house
        else: box(mb, x, y, zt, 1.6, 1.6, 1.8, yaw, 'metal_grey', seed=b.seed)                                # water tank
        k += 1

# ------------------------------------------------------------------ one building
def gen_building(ctx, b, mb):
    L = look(b)
    L['wall_mat'] = L['wall']; L['wall_tint'] = L['tint']
    b._L = L
    P = orient(b.poly, 1.0)
    ext = np.array(P.exterior.coords)[:-1]
    tz = ctx.T(ext[:, 0], ext[:, 1])
    zg = float(b.z0); b._zg = zg
    zb = float(min(tz.min(), zg)) - 0.4
    st, pa = edge_classes(ctx, b, ext)
    flags_e = st.astype(int) * F_STREET + pa.astype(int) * F_PARTY
    lit = F_LIT if L['lit'] else 0
    info = dict(kind=b.kind)
    if b.lod2 and b.lod2.get('R'):
        roofs = []
        for rings in b.lod2['R']:
            try: roofs.append(add_roof_poly(mb, rings, L, b.seed))
            except Exception: roofs.append(None)
        # walls: PLATEAU's own polygons, flagged by the nearest outline edge
        for rings in b.lod2.get('W', []):
            R = np.asarray(rings[0], np.float64)
            if len(R) < 3: continue
            n = newell(R)
            if abs(n[2]) > 0.3: continue
            n[2] = 0; n /= max(np.linalg.norm(n), 1e-9)
            c = R.mean(0)
            # nearest outline edge -> flags; outward check: flip if the test point lies inside the footprint low down
            dists = [Point(c[0], c[1]).distance(LineString([ext[i], ext[(i + 1) % len(ext)]])) for i in range(len(ext))]
            ei = int(np.argmin(dists)); fl = int(flags_e[ei]) if dists[ei] < 0.8 else 0
            q = c[:2] + n[:2] * 0.35
            if dists[ei] < 0.8 and shapely.contains_xy(P, q[0], q[1]) and not shapely.contains_xy(P, c[0] - n[0] * 0.35, c[1] - n[1] * 0.35): n = -n
            LL = dict(L)
            if fl & F_PARTY: LL['wall_mat'] = L['party_wall']; LL['wall_tint'] = L['ptint'] if L['party_wall'] == 'wall_plaster' else L['tint']
            if L.get('machiya') and fl & F_STREET:
                LL['wall_mat'] = 'machiya_front'; LL['wall_tint'] = BENGARA if L.get('bengara') else (88, 60, 40)
            shop = F_SHOP if (L['shop'] and fl & F_STREET) else 0
            add_wall_poly(mb, rings, n, zg, zb, LL, fl | shop | lit, b.seed)
        roof_details(mb, b, P, roofs, L, ctx, st)
        zt = max(R[:, 2].max() for rings in b.lod2['R'] for R in [np.asarray(rings[0])])
        if all(r is not None and r['flat'] for r in roofs if r is not None) and b.kind in ('mid', 'tall', 'station'):
            parapet(mb, b, ext, float(zt), L, h=0.9 if b.kind != 'station' else 0.4)
            rooftop(mb, b, P, float(zt))
    else:
        # LOD1: walls from the footprint, roof inferred
        H = float(b.h) if b.h and b.h > 2 else 6.0
        pitched = b.kind in ('trad', 'house', 'temple', 'shrine') or (b.kind == 'shed' and P.area > 30)
        if pitched:
            mrr = P.minimum_rotated_rectangle; xs, ys = mrr.exterior.coords.xy
            w1 = math.dist((xs[0], ys[0]), (xs[1], ys[1])); w2 = math.dist((xs[1], ys[1]), (xs[2], ys[2]))
            hw = min(w1, w2) / 2
            pitch = 0.45 if L['roof'] in ('kawara', 'hongawara') else 0.3
            if b.kind in ('temple', 'shrine'): pitch = 0.6
            rise = min(hw * pitch, H * 0.45)
            ze = zg + max(2.3, H - rise)
        else:
            ze = zg + H
        R = ext; n = len(R)
        for i in range(n):
            fl = int(flags_e[i])
            mat, tint = L['wall'], L['tint']
            if fl & F_PARTY: mat = L['party_wall']; tint = L['ptint'] if mat == 'wall_plaster' else L['tint']
            if L.get('machiya') and fl & F_STREET: mat = 'machiya_front'; tint = BENGARA if L.get('bengara') else (88, 60, 40)
            shop = F_SHOP if (L['shop'] and fl & F_STREET) else 0
            wall_quad(mb, R[i], R[(i + 1) % n], zb, ze, zg, mat, tint, L['fh'], L['ws'], fl | shop | lit, b.seed)
        for hole in P.interiors:
            H2 = np.array(hole.coords)[:-1][::-1]
            for i in range(len(H2)):
                wall_quad(mb, H2[i], H2[(i + 1) % len(H2)], zb, ze, zg, L['wall'], L['tint'], L['fh'], L['ws'], lit, b.seed)
        if pitched:
            if b.kind == 'trad' or (P.minimum_rotated_rectangle.area > 0 and (max(w1, w2) / max(min(w1, w2), 0.1) > 1.5 and b.kind != 'temple')):
                gable_roof(mb, b, P, ze, pitch, L, ctx, st, pa)
            else:
                hip_roof(mb, b, P, ze, pitch, L, ctx, st, pa)
        else:
            rings = [list(P.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in P.interiors]
            V, T = triangulate(rings, max_area=None if COARSE[0] else 8.0)
            if len(T):
                mb.add(np.c_[V, np.full(len(V), ze)], T, N=np.tile([0, 0, 1.0], (len(V), 1)), UV=V, mat=MAT['roof_flat'], c0=(200, 200, 200, 0), c1=(0, 0, int(b.seed * 255), 0))
            if b.kind in ('mid', 'tall'):
                parapet(mb, b, ext, ze, L)
                rooftop(mb, b, P, ze)
    # machiya: 庇 over street-facing fronts of two-storey wooden houses
    if L.get('machiya') and (b.h or 0) >= 5.2:
        for i in range(len(ext)):
            if st[i] and not pa[i]:
                hisashi(mb, b, ext[i], ext[(i + 1) % len(ext)], zg, L)
    return info
