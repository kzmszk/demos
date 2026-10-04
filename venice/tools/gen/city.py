"""Generic Venetian buildings from OSM footprints: party-wall classification, facade layouts
(openings as descriptors for the viewer), hipped roofs from a medial-axis skeleton, eaves.

Facade descriptor (consumed by web/facade.js):
  { b: building index, p0:[x,y], p1:[x,y], n:[nx,ny], zb, zt, zg, L,
    mat, tint:[r,g,b], dec, sh:[r,g,b], st (style), seed,
    base: z top of stone base course (or null), bands: [z...] string courses, cor: cornice type,
    open: [[type, u, z, w, h, flags], ...] }
"""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, MultiLineString, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, linemerge
from scipy.spatial import Voronoi
from .world import GROUND_Z, WATER_BOTTOM, h32, polys_of
from .osm import num
from .mesh import MeshBuilder, triangulate
from .materials import MAT, PALETTE, SHUTTERS

PITCH = math.radians(21.0)
TANP = math.tan(PITCH)
RISE_MAX = 3.6
EAVE_OUT = 0.38

# opening types (shared with web/facade.js)
OT = dict(R=1, A=2, G=3, S=4, D=5, DA=6, WG=7, P=8, PA=9, SH=10, GR=11)
# flags bits: 0-1 shutter (0 none, 1 open, 2 closed, 3 half), 2-3 balcony (0 none, 1 iron, 2 stone), 4 stone frame, 5 grate, 6 flower box, 7 lit-at-night

def srgb(c): return [int(v) for v in c]

# ------------------------------------------------------------------ building parameters
def bparams(b):
    r = lambda k: h32(b.id, k)
    p = {}
    kind = b.kind
    if kind == 'tower' or kind == 'church':
        p['mat'] = 'wall_brick' if r('m') < 0.72 else 'wall_stone'
    elif kind == 'palazzo':
        x = r('m'); p['mat'] = 'wall_plaster' if x < 0.62 else 'wall_stone' if x < 0.84 else 'wall_brick'
    elif kind == 'shed':
        p['mat'] = 'wall_brick' if r('m') < 0.6 else 'wall_plaster'
    else:
        x = r('m'); p['mat'] = 'wall_plaster' if x < 0.86 else 'wall_brick'
    pm = b.pmat or {}
    if pm.get('wall'): p['mat'] = pm['wall']
    p['tint'] = srgb(PALETTE[int(r('t') * len(PALETTE)) % len(PALETTE)]) if p['mat'] == 'wall_plaster' else [255, 255, 255]
    if pm.get('tint') and p['mat'] == 'wall_plaster': p['tint'] = srgb(pm['tint'])
    d = r('d'); p['dec'] = 0.0 if d < 0.35 else (d - 0.35) / 0.65 * 0.9
    p['sh'] = srgb(SHUTTERS[int(r('s') * len(SHUTTERS)) % len(SHUTTERS)])
    if kind == 'palazzo':
        p['style'] = 'gothic' if r('st') < 0.55 else 'renaiss'
        p['gf'] = 4.6 + 0.8 * r('gf'); p['nob'] = 4.6 + 0.6 * r('nob'); p['up'] = 3.8 + 0.4 * r('up')
        p['pitch'] = 3.2 + 0.7 * r('pi'); p['ww'] = 1.0 + 0.2 * r('ww'); p['wh'] = 2.1 + 0.4 * r('wh')
    elif kind == 'church':
        p['style'] = 'church'; p['gf'] = 6.0; p['nob'] = 6.0; p['up'] = 6.0; p['pitch'] = 6.0; p['ww'] = 1.6; p['wh'] = 4.0
    else:
        x = r('st'); p['style'] = 'rect' if x < 0.66 else 'arch' if x < 0.86 else 'gothic'
        p['gf'] = 3.7 + 0.6 * r('gf'); p['nob'] = 3.2 + 0.4 * r('nob'); p['up'] = 3.0 + 0.4 * r('up')
        p['pitch'] = 2.5 + 0.8 * r('pi'); p['ww'] = 0.85 + 0.2 * r('ww'); p['wh'] = 1.55 + 0.35 * r('wh')
    p['irreg'] = kind == 'house' and r('irr') < 0.45
    p['stonebase'] = (kind in ('palazzo', 'church') or r('sb') < 0.35)
    return p

def floors(b, p):
    """bottom z of each storey (from ground), and the top (eave) z."""
    z0 = b.z0; zt = GROUND_Z + b.H
    n = max(1, b.levels)
    zs = [z0]
    if n >= 2:
        hs = [p['gf']] + [p['nob']] + [p['up']] * (n - 3) if n >= 3 else [p['gf']]
        hs = hs[:n - 1]
        tot = sum(hs) + 2.9          # last storey ~2.9 + 0.45 parapet/cornice
        s = (zt - z0 - 0.45) / tot if tot > 0 else 1
        s = min(1.25, max(0.8, s))
        z = z0
        for h in hs:
            z += h * s; zs.append(z)
    return zs, zt


# ------------------------------------------------------------------ party-wall classification
class Classifier:
    def __init__(self, world):
        self.w = world
        self.tree = world.btree
        self.polys = [b.poly for b in world.buildings]

    def classify(self, b, ring, step=0.5, off=0.7):
        """for each edge of ring (list of pts, building b), return list of segments
        (t0, t1, cls, neighbour_H) with cls in 'B' (party), 'W' (water), 'G' (ground)."""
        out = []
        n = len(ring)
        for i in range(n):
            a = np.array(ring[i], float); c = np.array(ring[(i + 1) % n], float)
            L = float(np.linalg.norm(c - a))
            if L < 0.05: out.append([]); continue
            d = (c - a) / L; nrm = np.array([d[1], -d[0]])
            k = max(1, int(math.ceil(L / step)))
            ts = (np.arange(k) + 0.5) / k
            Q = a[None, :] + ts[:, None] * (c - a)[None, :] + nrm[None, :] * off
            pts = shapely.points(Q)
            cls = np.full(k, 'G', dtype=object); nh = np.zeros(k)
            ii, jj = self.tree.query(pts, predicate='within')
            for q, j in zip(ii, jj):
                nb = self.w.buildings[j]
                if nb is b: continue
                if cls[q] != 'B' or nb.H > nh[q]:
                    cls[q] = 'B'; nh[q] = nb.H
            free = cls != 'B'
            if free.any():
                inl = shapely.contains_xy(self.w.land, Q[free, 0], Q[free, 1])
                idx = np.nonzero(free)[0]
                for q, il in zip(idx, inl):
                    if not il: cls[q] = 'W'
            # run-length
            segs = []; s0 = 0
            for q in range(1, k + 1):
                if q == k or cls[q] != cls[s0] or (cls[q] == 'B' and abs(nh[q] - nh[s0]) > 0.3):
                    segs.append([s0 / k * L, q / k * L, cls[s0], float(nh[s0:q].max()) if cls[s0] == 'B' else 0.0])
                    s0 = q
            # absorb tiny runs (< 0.6 m) into neighbours
            j = 0
            while len(segs) > 1 and j < len(segs):
                if segs[j][1] - segs[j][0] < 0.6:
                    if j > 0: segs[j - 1][1] = segs[j][1]
                    else: segs[1][0] = segs[0][0]
                    segs.pop(j); continue
                j += 1
            out.append(segs)
        return out


# ------------------------------------------------------------------ facade layout
def layout(b, p, zs, zt, L, cls, zb, rnd):
    """openings for one open facade segment of length L. cls 'G' street or 'W' water."""
    ops = []
    style = p['style']; pitch = p['pitch']; ww = p['ww']; wh = p['wh']
    margin = 0.75
    if L < 1.5: return ops
    nc = max(1, int((L - 2 * margin + pitch * 0.35) / pitch)) if L >= 2.2 else 1
    us = [L / 2 + (i - (nc - 1) / 2) * pitch for i in range(nc)]
    if nc == 1: us = [L / 2]
    nfl = len(zs)
    wtype = {'rect': 'R', 'arch': 'A', 'gothic': 'G', 'renaiss': 'A', 'church': 'A'}[style]
    shut = lambda k: 0 if style == 'church' else (1 if rnd(k) < 0.55 else 2 if rnd(k) < 0.8 else 3 if rnd(k) < 0.88 else 0)
    # ---------- upper floors
    poli = None
    if style in ('gothic', 'renaiss') and nfl >= 3 and L >= 8:
        m = 4 if L < 14 else 5 if L < 20 else 6
        lw = 0.78 if style == 'gothic' else 0.9; gap = 0.24
        W = m * lw + (m - 1) * gap
        poli = (L / 2 - W / 2, L / 2 + W / 2, m, lw, gap)
    for f in range(1, nfl):
        z0 = zs[f]
        z1 = zs[f + 1] if f + 1 < nfl else zt - 0.45
        hfl = z1 - z0
        if hfl < 2.0: continue
        nob = (f == 1 and b.kind == 'palazzo') or (f == 1 and style == 'church')
        h = min(hfl - 1.1, wh * (1.15 if nob else 1.0) * (0.82 if (f == nfl - 1 and p['irreg']) else 1.0))
        w = ww * (1.08 if nob else 1.0)
        sill = z0 + max(0.75, min(1.0, hfl - h - 0.45))
        for ci, u in enumerate(us):
            if poli and f == 1 and poli[0] - 0.8 < u < poli[1] + 0.8: continue
            if p['irreg']:
                if rnd(('m', f, ci)) < 0.1: continue
                u = u + (rnd(('j', f, ci)) - 0.5) * 0.4
            if u - w / 2 < 0.45 or u + w / 2 > L - 0.45: continue
            fl = shut(('s', f, ci)) | (16 if (style != 'rect' or rnd(('fr', ci)) < 0.7) else 0)
            if nob and rnd(('bal', ci)) < 0.45: fl |= (1 << 2)          # iron balcony
            elif rnd(('bal', f, ci)) < 0.06: fl |= (1 << 2)
            if rnd(('fl', f, ci)) < 0.12: fl |= 64
            if rnd(('lit', f, ci)) < 0.32: fl |= 128
            ops.append([OT[wtype], round(u, 3), round(sill, 3), round(w, 3), round(h, 3), fl])
        if poli and f == 1:
            a0, a1, m, lw, gap = poli
            for k in range(m):
                u = a0 + lw / 2 + k * (lw + gap)
                fl = 16 | (2 << 2 if k == 0 else 0) | (128 if rnd(('pl', k)) < 0.5 else 0)
                ops.append([OT['P' if style == 'gothic' else 'PA'], round(u, 3), round(sill - 0.25, 3), lw, round(h + 0.45, 3), fl | (m << 8) if k == 0 else fl])
    # ---------- ground floor
    gz = zs[0]
    if cls == 'W':
        has_gate = (b.kind == 'palazzo' or rnd('wg') < 0.35) and L >= 4
        gate_u = L / 2 if has_gate else None
        if has_gate:
            gw = 2.0 + 0.6 * rnd('gw') if b.kind == 'palazzo' else 1.5 + 0.4 * rnd('gw')
            ops.append([OT['WG'], round(gate_u, 3), 0.25, round(gw, 3), round(min(zs[1] - 0.6 if nfl > 1 else 3.2, gw * 0.5 + 2.4), 3), 16])
        for ci, u in enumerate(us):
            if gate_u is not None and abs(u - gate_u) < 2.0: continue
            if rnd(('gw', ci)) < 0.55 and nfl > 1:
                ops.append([OT['GR'], round(u, 3), round(gz + 1.1, 3), 0.8, 1.1, 32 | 16])
    else:
        nd = max(1, int(round(L / 9.0))) if L >= 2.6 else 0
        if style == 'church': nd = 1
        dcols = set()
        if nd:
            order = sorted(range(len(us)), key=lambda i: rnd(('d', i)))
            if style == 'church' or b.kind == 'palazzo': order = sorted(range(len(us)), key=lambda i: abs(us[i] - L / 2))
            dcols = set(order[:nd])
        shop = b.kind == 'house' and rnd('shop') < 0.25 and L > 5
        for ci, u in enumerate(us):
            if ci in dcols:
                if style == 'church':
                    ops.append([OT['DA'], round(u, 3), round(gz, 3), 2.2, 4.2, 16])
                elif shop and rnd(('sd', ci)) < 0.6:
                    ops.append([OT['SH'], round(u, 3), round(gz, 3), round(min(2.6, pitch - 0.4), 3), 2.6, 128 if rnd(('ls', ci)) < 0.8 else 0])
                else:
                    t = 'DA' if (style in ('gothic', 'renaiss', 'arch') and rnd(('da', ci)) < 0.5) else 'D'
                    ops.append([OT[t], round(u, 3), round(gz, 3), round(1.1 + 0.3 * rnd(('dw', ci)), 3), round(2.3 + 0.3 * rnd(('dh', ci)), 3), 16 if rnd(('df', ci)) < 0.7 else 0])
            elif shop and rnd(('sh', ci)) < 0.5:
                ops.append([OT['SH'], round(u, 3), round(gz, 3), round(min(2.4, pitch - 0.5), 3), 2.5, 128 if rnd(('ls2', ci)) < 0.8 else 0])
            elif rnd(('g', ci)) < 0.7 and nfl > 1:
                ops.append([OT['GR'], round(u, 3), round(gz + 1.3, 3), 0.8, 1.2, 32 | 16])
    # remove overlaps (keep first)
    keep = []
    for o in ops:
        ok = True
        for k in keep:
            if abs(o[1] - k[1]) < (o[3] + k[3]) / 2 + 0.15 and not (o[2] + o[4] < k[2] - 0.1 or k[2] + k[4] < o[2] - 0.1): ok = False; break
        if ok: keep.append(o)
    return keep


# ------------------------------------------------------------------ roof: medial-axis hip roof
def medial_axis(poly, spacing=0.35):
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
        if va < 0 or vb < 0: continue
        if own[pa] == own[pb]: continue
        if not (inside[va] and inside[vb]): continue
        segs.append((tuple(V[va]), tuple(V[vb])))
    if not segs: return []
    ml = linemerge(MultiLineString(segs))
    lines = [ml] if ml.geom_type == 'LineString' else list(ml.geoms)
    out = []
    for l in lines:
        s = l.simplify(0.12)
        if s.length > 0.25: out.append(list(s.coords))
    return out

def roof(mb, b, poly, ze, eave_edges, roof_mat='roof', tint=(255, 255, 255, 0), rh=None):
    """hipped roof over poly at eave height ze.  eave_edges: list of (p0, p1) (outer wall lines) that get an overhang.
    rh: explicit ridge height (OSM roof:height) -> the pitch follows from the footprint's inscribed radius."""
    P = orient(poly.simplify(0.12, preserve_topology=True), 1.0)
    if P.is_empty or P.area < 1.0: return
    if b.roof == 'flat' or P.area < 6:
        rings = [list(P.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in P.interiors]
        V, T = triangulate(rings, max_area=12.0)
        if len(T):
            V3 = np.c_[V, np.full(len(V), ze + 0.05)]
            mb.add(V3, T[:, ::1], N=np.tile([0, 0, 1.0], (len(V3), 1)), UV=V, mat=MAT['flat_roof'], c1=(40, 0, int(b.seed * 255), 0))
        return
    tanp = TANP; dcap = RISE_MAX / TANP
    ma = medial_axis(P)
    if rh is not None and rh > 0.2 and ma:
        pts = np.array([q for l in ma for q in l])
        dmax = float(shapely.distance(P.boundary, shapely.points(pts)).max())
        if dmax > 0.3: tanp = rh / dmax; dcap = dmax + 0.01
    inset = P.buffer(-dcap, join_style=2)
    cons = []
    if not inset.is_empty and inset.area > 2.0:
        cl = []
        for q in polys_of(inset):
            cl.append(list(q.exterior.coords)); cl += [list(r.coords) for r in q.interiors]
        cons += [c[:-1] + [c[0]] for c in cl]
        ma = [list(g.coords) for l in ma for g in [LineString(l).difference(inset.buffer(0.05))] if not g.is_empty for g in (g.geoms if hasattr(g, 'geoms') else [g]) if g.length > 0.2]
    rings = [list(P.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in P.interiors]
    V, T = triangulate(rings, segments_extra=ma + cons, max_area=10.0)
    if len(T) == 0: return
    bd = P.boundary
    d = shapely.distance(bd, shapely.points(V))
    d = np.minimum(d, dcap)
    Z = ze + d * tanp
    # per-triangle nearest boundary edge -> uv frame
    ring_edges = []
    for R in rings:
        n = len(R)
        for i in range(n): ring_edges.append((np.array(R[i]), np.array(R[(i + 1) % n])))
    E0 = np.array([e[0] for e in ring_edges]); E1 = np.array([e[1] for e in ring_edges])
    ED = E1 - E0; EL = np.linalg.norm(ED, axis=1); EL[EL == 0] = 1; ED = ED / EL[:, None]
    C = V[T].mean(axis=1)
    # distance from centroids to each edge segment (vectorised in chunks)
    best = np.zeros(len(T), int)
    for s in range(0, len(T), 2048):
        c = C[s:s + 2048][:, None, :]
        t = np.clip(np.sum((c - E0[None]) * ED[None], axis=2), 0, EL[None])
        q = E0[None] + t[..., None] * ED[None]
        dd = np.linalg.norm(c - q, axis=2)
        best[s:s + 2048] = np.argmin(dd, axis=1)
    flat = d[T].min(axis=1) >= dcap - 1e-3
    Pf = []; UVf = []; Mf = []
    cosp = math.cos(math.atan(tanp))
    for ti, tri in enumerate(T):
        e = best[ti]; a = E0[e]; dr = ED[e]; nin = np.array([-dr[1], dr[0]])
        for k in tri:
            v = V[k]
            Pf.append((v[0], v[1], Z[k]))
            if flat[ti]: UVf.append((v[0], v[1]))
            else: UVf.append((float(np.dot(v - a, dr)), float(np.dot(v - a, nin)) / cosp))
        Mf.append(MAT['flat_roof'] if flat[ti] else MAT[roof_mat])
    Pf = np.array(Pf); I = np.arange(len(Pf)).reshape(-1, 3)
    mats = np.repeat(np.array(Mf, np.uint8), 3)
    mb.add(Pf, I, UV=np.array(UVf), mat=mats, c0=tint, c1=(0, 0, int(b.seed * 255), 0))
    # eaves: overhang strip + fascia + soffit on exposed outer edges
    o = EAVE_OUT; dz = o * tanp
    for (p0, p1) in eave_edges:
        a = np.array(p0, float); c = np.array(p1, float); L = np.linalg.norm(c - a)
        if L < 0.3: continue
        dr = (c - a) / L; nout = np.array([dr[1], -dr[0]])
        a2 = a - dr * 0.02; c2 = c + dr * 0.02
        q0 = (*a2, ze); q1 = (*c2, ze); q2 = (*(c2 + nout * o + dr * o), ze - dz); q3 = (*(a2 + nout * o - dr * o), ze - dz)
        uv = [(0, 0), (L, 0), (L + o, -o / cosp), (-o, -o / cosp)]
        mb.add([q0, q1, q2, q3], [[0, 1, 2], [0, 2, 3]], UV=uv, mat=MAT[roof_mat], c0=tint, c1=(0, 0, int(b.seed * 255), 0))
        th = 0.14
        f0 = (*(a2 + nout * o - dr * o), ze - dz); f1 = (*(c2 + nout * o + dr * o), ze - dz)
        f2 = (*(c2 + nout * o + dr * o), ze - dz - th); f3 = (*(a2 + nout * o - dr * o), ze - dz - th)
        mb.add([f0, f1, f2, f3], [[0, 2, 1], [0, 3, 2]], UV=[(0, ze - dz), (L, ze - dz), (L, ze - dz - th), (0, ze - dz - th)], mat=MAT['trim'], c1=(60, 0, 0, 0))
        s0 = (*a2, ze - dz - th); s1 = (*c2, ze - dz - th)
        mb.add([s0, s1, f2, f3], [[0, 1, 2], [0, 2, 3]], UV=[(0, 0), (L, 0), (L, o), (0, o)], mat=MAT['wood_raw'], c1=(60, 0, 0, 0))


# ------------------------------------------------------------------ per-building generation
def belfry(b, L, zt, rnd):
    """campanile openings: arched belfry lights under the top, a few narrow slits down the shaft."""
    ops = []
    if L < 2.2: return ops
    H = zt - b.z0
    if H > 14:
        n = 1 if L < 4.2 else 2 if L < 7.5 else 3
        w = min(1.5, L / (n * 1.7 + 0.6)); h = min(4.2, max(2.2, w * 2.6))
        z = zt - h - 1.4
        for k in range(n):
            u = L / 2 + (k - (n - 1) / 2) * (L / (n + 0.4))
            ops.append([OT['A'], round(u, 3), round(z, 3), round(w, 3), round(h, 3), 16 | 128])
        zz = b.z0 + 6.0
        while zz < z - 4.0:
            if rnd(('sl', round(zz))) < 0.6: ops.append([OT['R'], round(L / 2, 3), round(zz, 3), 0.32, 0.9, 16])
            zz += 6.5
    return ops

GROUND_ONLY = (OT['D'], OT['DA'], OT['SH'], OT['GR'], OT['WG'])

def gen_building(world, cls_, b, mb, facades, bi):
    rnd = lambda k: h32(b.id, k)
    p = bparams(b)
    zs, zt = floors(b, p)
    elevated = b.z0 > GROUND_Z + 0.5
    poly = orient(b.poly.simplify(0.08, preserve_topology=True), 1.0)
    rings = [list(poly.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in poly.interiors]
    eave_edges = []
    # sottoporteghi through this building (streets.py): the facade opens below soto_top where they cross it
    soto = [] if elevated else getattr(world, 'soto_by', {}).get(b.id, [])
    soto_top = GROUND_Z + min(3.1, max(2.4, (zs[1] - GROUND_Z - 0.3) if len(zs) > 1 else 2.9))
    for ring in rings:
        segs_all = cls_.classify(b, ring)
        n = len(ring)
        for i in range(n):
            segs = segs_all[i]
            if not segs: continue
            a = np.array(ring[i], float); c = np.array(ring[(i + 1) % n], float)
            Le = float(np.linalg.norm(c - a)); dr = (c - a) / Le; nrm = np.array([dr[1], -dr[0]])
            exposed = any(s[2] != 'B' or s[3] < zt - GROUND_Z - 0.3 for s in segs)
            cut = getattr(b, 'hero_cut', None)
            if cut and any(LineString([tuple(a), tuple(c)]).hausdorff_distance(l) < 3.0 or l.distance(Point(*((a + c) / 2))) < 2.0 for l in cut):
                continue                      # replaced by a hand-modelled hero facade
            if exposed and b.kind not in ('tower',): eave_edges.append((tuple(a), tuple(c)))
            for (t0, t1, cl, nh) in segs:
                L = t1 - t0
                if L < 0.3: continue
                p0 = a + dr * t0; p1 = a + dr * t1
                if cl == 'B':
                    zlow = GROUND_Z + nh
                    zb = zlow - 0.3
                    if elevated: zb = max(zb, b.z0)
                    if zb >= zt - 0.25 or zlow >= zt - 0.25: continue
                    ops = []
                    if b.kind == 'tower':
                        ops = [o for o in belfry(b, L, zt, lambda k: rnd(('bf', i, k))) if o[2] > zb + 0.4]
                    elif zt - zb > 3.4 and L > 2.5:
                        zz = [z for z in zs if z >= zb + 0.6]
                        if zz:
                            sub = layout(b, p, [zb] + zz, zt, L, 'G', zb, lambda k: rnd(('pw', i, round(t0, 1), k)))
                            ops = [o for o in sub if o[0] not in GROUND_ONLY and o[2] > zb + 0.4]
                    zg = max(zlow, zb)
                else:
                    if elevated:
                        zb = b.z0; zg = b.z0
                        if b.kind == 'tower': ops = belfry(b, L, zt, lambda k: rnd(('bf', i, k)))
                        else: ops = [o for o in layout(b, p, zs, zt, L, 'G', zb, lambda k: rnd((i, round(t0, 1), k))) if o[0] not in GROUND_ONLY and o[2] > zb + 0.4]
                    else:
                        zb = WATER_BOTTOM if cl == 'W' else GROUND_Z - 0.05
                        zg = 0.0 if cl == 'W' else GROUND_Z
                        ops = layout(b, p, zs, zt, L, cl, zb, lambda k: rnd((i, round(t0, 1), k))) if b.kind != 'tower' else belfry(b, L, zt, lambda k: rnd(('bf', i, k)))
                base = (1.45 if cl == 'W' else GROUND_Z + 0.45) if (p['stonebase'] and not elevated) else None
                pieces = [(0.0, L, False)]
                if soto and cl != 'B':
                    ivs = []
                    seg_line = LineString([tuple(p0), tuple(p1)])
                    for sg in soto:
                        g = seg_line.intersection(sg)
                        for gg in (g.geoms if hasattr(g, 'geoms') else [g]):
                            if gg.is_empty or gg.length < 0.3: continue
                            us = [float(np.dot(np.array(c) - p0, dr)) for c in gg.coords]
                            ivs.append([max(0.0, min(us) - 0.02), min(L, max(us) + 0.02)])
                    if ivs:
                        ivs.sort(); mg = [ivs[0]]
                        for iv in ivs[1:]:
                            if iv[0] <= mg[-1][1] + 0.3: mg[-1][1] = max(mg[-1][1], iv[1])
                            else: mg.append(iv)
                        pieces = []; u = 0.0
                        for (ua, ub) in mg:
                            if ua - u > 0.3: pieces.append((u, ua, False))
                            pieces.append((ua, ub, True)); u = ub
                        if L - u > 0.3: pieces.append((u, L, False))
                for (ua, ub, is_soto) in pieces:
                    if ub - ua < 0.3: continue
                    q0 = p0 + dr * ua; q1 = p0 + dr * ub
                    sops = [[o[0], round(o[1] - ua, 3)] + list(o[2:]) for o in ops if o[1] - o[3] / 2 >= ua + 0.05 and o[1] + o[3] / 2 <= ub - 0.05] if len(pieces) > 1 else ops
                    zb2, zg2 = zb, zg
                    if is_soto:
                        zb2 = max(zb, soto_top); zg2 = zb2; sops = [o for o in sops if o[2] >= zb2 + 0.3]
                        if zb2 >= zt - 0.25: continue
                    facades.append(dict(b=bi, p0=[round(q0[0], 3), round(q0[1], 3)], p1=[round(q1[0], 3), round(q1[1], 3)], n=[round(nrm[0], 5), round(nrm[1], 5)],
                                        zb=round(zb2, 3), zt=round(zt, 3), zg=round(zg2, 3), L=round(ub - ua, 3), u0=round(t0 + ua, 3), cls=cl,
                                        mat=MAT[p['mat']], tint=p['tint'], dec=round(p['dec'], 3), sh=p['sh'], st=p['style'], seed=round(b.seed, 5),
                                        base=None if is_soto else base,
                                        bands=[round(z, 3) for z in zs[1:]] if b.kind == 'palazzo' else [],
                                        cor=1 if b.kind in ('palazzo', 'church') else 0, open=sops))
    for sg in soto: sottoportego(mb, b, poly, sg, soto_top)
    pm = b.pmat or {}
    rm = pm.get('roof') or ('roof_old' if rnd('ro') < 0.3 else 'roof')
    seed = int(b.seed * 255)
    shape = b.roof
    if b.roof_h is None and b.kind == 'tower':
        tower_top(mb, b, poly, zt)
    elif shape in ('gabled', 'skillion', 'round') and b.roof_h:
        from . import roofs
        t = b.tags
        roofs.gabled(mb, poly, zt, b.roof_h, rm, p['mat'], p['tint'], seed, across=t.get('roof:orientation') == 'across',
                     direction=num(t.get('roof:direction')), kind=shape)
    elif shape == 'pyramid' and b.roof_h:
        from . import roofs
        roofs.pyramid(mb, poly, zt, b.roof_h, rm, seed)
    elif shape in ('dome', 'onion') and b.roof_h:
        from . import roofs
        roofs.dome(mb, poly, zt, b.roof_h, rm, seed, profile=shape)
    else:
        if shape not in ('hipped', 'flat'): b.roof = 'hipped'
        roof(mb, b, poly, zt, eave_edges if b.roof_h is None else [], roof_mat=rm, rh=b.roof_h)
    return dict(p=p, eave_edges=eave_edges, poly=poly, zt=zt)

def sottoportego(mb, b, poly, strip, ztop):
    """a covered passage through the building: masegni floor, plastered side walls, a wooden beamed ceiling."""
    inner = strip.intersection(poly)
    seed = int(b.seed * 255)
    for g in (inner.geoms if hasattr(inner, 'geoms') else [inner]):
        if g.geom_type != 'Polygon' or g.area < 0.3: continue
        g = orient(g, 1.0)
        ring = list(g.exterior.coords)[:-1]
        try:
            V, T = triangulate([ring])
        except Exception:
            continue
        V = np.asarray(V, float); T = np.asarray(T, np.int64)
        for (z, nz, mat) in ((GROUND_Z + 0.012, 1.0, MAT['ground']), (ztop, -1.0, MAT['wood_raw'])):
            P = np.c_[V, np.full(len(V), z)]
            I = T if nz > 0 else T[:, ::-1]
            mb.add_planar(P, I, (0, 0, nz), V.copy(), mat=mat, c1=(0, 0, seed, 0))
        # side walls: the edges of the strip inside the building (not the ones on the outline, where it opens)
        n = len(ring)
        for i in range(n):
            a = np.array(ring[i]); c = np.array(ring[(i + 1) % n])
            m = (a + c) / 2; L = float(np.linalg.norm(c - a))
            if L < 0.05 or poly.exterior.distance(Point(*m)) < 0.08: continue
            d = (c - a) / L; nin = np.array([-d[1], d[0]])               # ccw ring: inside on the left
            P = [(a[0], a[1], GROUND_Z), (c[0], c[1], GROUND_Z), (c[0], c[1], ztop), (a[0], a[1], ztop)]
            mb.add_planar(P, [[0, 2, 1], [0, 3, 2]], (nin[0], nin[1], 0.0), [(0, GROUND_Z), (L, GROUND_Z), (L, ztop), (0, ztop)], mat=MAT['portico_wall'], c1=(0, 0, seed, 0))   # faces the passage
        # beams across the ceiling every 0.9 m
        mrr = g.minimum_rotated_rectangle; cc = list(mrr.exterior.coords)
        e0 = np.subtract(cc[1], cc[0]); e1 = np.subtract(cc[2], cc[1])
        lng, sht, o = (e0, e1, np.array(cc[0])) if np.linalg.norm(e0) >= np.linalg.norm(e1) else (e1, e0, np.array(cc[1]))
        Ll = float(np.linalg.norm(lng)); du = lng / max(Ll, 1e-9)
        for k in range(1, int(Ll / 0.9)):
            c0 = o + du * (k * 0.9 - 0.07); c1_ = o + du * (k * 0.9 + 0.07)
            q = [(c0[0], c0[1]), (c1_[0], c1_[1]), (c1_[0] + sht[0], c1_[1] + sht[1]), (c0[0] + sht[0], c0[1] + sht[1])]
            beam = shapely.geometry.Polygon(q).intersection(g)
            if beam.is_empty or beam.geom_type != 'Polygon' or beam.area < 0.02: continue
            br = list(orient(beam, 1.0).exterior.coords)[:-1]
            try:
                BV, BT = triangulate([br])
            except Exception:
                continue
            BV = np.asarray(BV, float); BT = np.asarray(BT, np.int64)
            mb.add_planar(np.c_[BV, np.full(len(BV), ztop - 0.16)], BT[:, ::-1], (0, 0, -1.0), BV.copy(), mat=MAT['wood_raw'], c1=(0, 0, seed, 0))

def tower_top(mb, b, poly, zt):
    """campanile: belfry openings handled by facades; pyramid roof here."""
    c = poly.centroid; R = list(poly.exterior.coords)[:-1]
    apex = (c.x, c.y, zt + max(4.0, math.sqrt(poly.area) * 1.1))
    P = []; UV = []
    for i in range(len(R)):
        a = R[i]; d = R[(i + 1) % len(R)]
        P += [(a[0], a[1], zt), (d[0], d[1], zt), apex]
        L = math.dist(a, d); UV += [(0, 0), (L, 0), (L / 2, math.dist((a[0], a[1]), (c.x, c.y)))]
    P = np.array(P); mb.add(P, np.arange(len(P)).reshape(-1, 3), UV=UV, mat=MAT['roof'], c1=(0, 0, 0, 0))
