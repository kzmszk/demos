"""天龍寺 site helpers (own module; the shared kit jk/* is not edited).  Pieces adapted from eikando_kit / ginkakuji_util
(copied, not imported, so the other sites can change freely): building frames, walk / block ribbons, wall infills,
halls with verandas, gates, walls, steps on the terrain, garden stones, lanterns, the 相輪, ground meshes over
polygons, Poisson planting, and preview-only tree proxies."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from jk import prim, arch, Frame
from jk import roof as jroof

WD = 'wood_dark'
WHITE = (238, 234, 224, 35)
ROOF_LIFT = 0.3
SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
        'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck']
SID = {n: i for i, n in enumerate(SURF)}

def nrm(v):
    v = np.asarray(v, float); l = np.linalg.norm(v)
    return v / l if l > 1e-12 else v

def rings(poly):
    """all rings of an OSM nested poly list"""
    out = []
    def rec(p):
        if isinstance(p[0][0], (int, float)): out.append(np.array(p, float)); return
        for q in p: rec(q)
    rec(poly); return out

def outer(poly):
    while isinstance(poly[0][0], (list, tuple)): poly = poly[0]
    return np.array(poly, float)

def osm_poly(f):
    """shapely polygon of an OSM feature (outer ring + holes of the first part; multipolygons merged)"""
    p = f['poly']
    parts = []
    def rec(q):
        if isinstance(q[0][0][0], (int, float)): parts.append(Polygon(q[0], q[1:]).buffer(0)); return
        for r in q: rec(r)
    if isinstance(p[0][0], (int, float)): return Polygon(p).buffer(0)
    if isinstance(p[0][0][0], (int, float)): return Polygon(p[0], p[1:]).buffer(0)
    rec(p)
    return shapely.unary_union(parts)

# ------------------------------------------------------------------ frames
class Loc:
    """a building frame: centre (cx, cy), yaw = direction of local +u (ccw from east); local v = u rotated +90°.
    Side 0 (front) is v-; build inside `with loc.frame(B):` with absolute z."""
    def __init__(self, cx, cy, yaw):
        self.cx, self.cy, self.yaw = float(cx), float(cy), float(yaw)
        self.c, self.s = math.cos(yaw), math.sin(yaw)
    def w(self, u, v):
        return (self.cx + self.c * u - self.s * v, self.cy + self.s * u + self.c * v)
    def l(self, x, y):
        dx, dy = x - self.cx, y - self.cy
        return (self.c * dx + self.s * dy, -self.s * dx + self.c * dy)
    def frame(self, B):
        return Frame(B, self.cx, self.cy, 0.0, self.yaw)
    def g(self, S, u, v):
        x, y = self.w(u, v); return float(S.ground(x, y))
    def ring(self, pts):
        return [self.w(u, v) for (u, v) in pts]

def facing(front_deg):
    """yaw of a frame whose front (v-) faces the world direction front_deg (deg ccw from east)"""
    return math.radians(front_deg + 90.0)

# ------------------------------------------------------------------ walk / block helpers
def ribbon(B, pts, w, tag, z=None, mat='stone', off=0.0, **kw):
    """a horizontal ribbon along a 2D/3D polyline, width w, centre offset `off` to the right"""
    P = np.asarray(pts, float)
    if len(P) < 2: return
    if P.shape[1] == 2: P = np.c_[P, np.full(len(P), 0.0 if z is None else z)]
    V = []; I = []
    for i in range(len(P)):
        if i == 0: t = P[1, :2] - P[0, :2]
        elif i == len(P) - 1: t = P[-1, :2] - P[-2, :2]
        else: t = P[i + 1, :2] - P[i - 1, :2]
        t = nrm(t); n = np.array([t[1], -t[0]])
        a = P[i, :2] + n * (off - w / 2); b = P[i, :2] + n * (off + w / 2)
        V += [[a[0], a[1], P[i, 2]], [b[0], b[1], P[i, 2]]]
    for i in range(len(P) - 1):
        k = 2 * i
        I += [[k, k + 1, k + 3], [k, k + 3, k + 2]]
    V = np.array(V); I = np.array(I)
    fn = np.cross(V[I[:, 1]] - V[I[:, 0]], V[I[:, 2]] - V[I[:, 0]])
    if fn[:, 2].sum() < 0: I = I[:, ::-1]
    B.add(V, I, mat, tag=tag, **kw)

def quad(B, a, b, c, d, mat, tag='main', both=False, out=None, uv=None, **kw):
    P = np.array([a, b, c, d], float)
    I = [[0, 1, 2], [0, 2, 3]]
    if out is not None:
        fn = np.cross(P[1] - P[0], P[2] - P[0]) + np.cross(P[2] - P[0], P[3] - P[0])
        if fn @ np.asarray(out, float) < 0: I = [[0, 2, 1], [0, 3, 2]]
    B.add(P, I, mat, tag=tag, UV=uv, **kw)
    if both: B.add(P, [t[::-1] for t in I], mat, tag=tag, UV=uv, **kw)

def rect_walk(B, x0, y0, x1, y1, z, tag='walk'):
    prim.polygon(B, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z, 'stone', tag=tag)

def poly_walk(B, poly, z, tag='walk'):
    for p in (poly.geoms if hasattr(poly, 'geoms') else [poly]):
        if p.is_empty or p.area < 0.05: continue
        prim.polygon(B, np.array(p.exterior.coords)[:-1], z, 'stone', holes=[np.array(r.coords)[:-1] for r in p.interiors], tag=tag)

def block_line(B, pts, w=0.5):
    ribbon(B, pts, w, 'block', z=0.0)

def block_poly(B, poly):
    for p in (poly.geoms if hasattr(poly, 'geoms') else [poly]):
        if p.is_empty or p.area < 0.05: continue
        prim.polygon(B, np.array(p.exterior.coords)[:-1], 0.0, 'stone', holes=[np.array(r.coords)[:-1] for r in p.interiors], tag='block')

# ------------------------------------------------------------------ wall infills (in the current frame)
def _plane(B, a, b, za, zb, n, depth, mat, tag='main', both=False, **kw):
    A = np.r_[a - n * depth, za]; Bp = np.r_[b - n * depth, za]; C = np.r_[b - n * depth, zb]; D_ = np.r_[a - n * depth, zb]
    P = np.array([A, Bp, C, D_])
    fn = np.cross(P[1] - P[0], P[2] - P[0])
    I = [[0, 1, 2], [0, 2, 3]] if fn @ np.r_[n, 0] >= 0 else [[0, 2, 1], [0, 3, 2]]
    L = np.linalg.norm(b - a)
    UV = np.array([[0, za], [L, za], [L, zb], [0, zb]])
    B.add(P, I, mat, UV=UV, tag=tag, **kw)
    if both: B.add(P, [t[::-1] for t in I], mat, UV=UV, tag=tag, **kw)

def infill(B, p0, p1, z0, z1, kind, out=None, mat=WD, r=0.2, tag='main', seed=0):
    """bay infill: plaster, white, board, lattice, shoji, maira (舞良戸), karado, katomado, renji, koshi, shitomi, open,
    glass, dark (an open bay looking into a dark room)"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L
    n = np.array([d[1], -d[0]]) if out is None else np.asarray(out, float)
    q0 = p0 + d * r; q1 = p1 - d * r; Lq = L - 2 * r
    if kind == 'open': return
    if kind in ('plaster', 'board', 'renji', 'koshi', 'shitomi', 'karado', 'noren'):
        arch.infill(B, p0, p1, z0, z1, kind, out=n, mat=mat, tag=tag, seed=seed); return
    if kind == 'white':
        _plane(B, q0, q1, z0, z1, n, 0.06, 'temple_wall', tag=tag, both=True, c0=WHITE, c1=(0, 0, seed % 255, 0)); return
    if kind == 'katomado':
        # white wall with a bell-shaped window (a dark recess with a lattice), frame proud
        _plane(B, q0, q1, z0, z1, n, 0.06, 'temple_wall', tag=tag, both=True, c0=WHITE)
        c = (q0 + q1) / 2; w = min(0.95, Lq * 0.42); h0 = z0 + (z1 - z0) * 0.3; h1 = min(z1 - 0.15, h0 + w * 1.55)
        pts = katomado_ring(w, h0, h1)
        V = np.array([np.r_[c + d * s - n * 0.03, zz] for (s, zz) in pts])
        cen = np.r_[c - n * 0.03, (h0 + h1) / 2]
        P = np.vstack([cen, V]); m = len(V)
        I = [[0, 1 + j, 1 + (j + 1) % m] for j in range(m)]
        fn = np.cross(P[I[0][1]] - P[0], P[I[0][2]] - P[0])
        if fn[:2] @ n < 0: I = [t[::-1] for t in I]
        B.add(P, I, 'glass', tag=tag)
        prim.sweep(B, np.vstack([V, V[:1]]), [(-0.05, -0.02), (0.05, -0.02), (0.05, 0.05), (-0.05, 0.05)], mat, up=(n[0], n[1], 0), tag='detail')
        for s in np.linspace(-w / 2 + 0.08, w / 2 - 0.08, 6):
            prim.obox(B, np.r_[c + d * s - n * 0.035, h0], np.r_[c + d * s - n * 0.035, h0 + (h1 - h0) * (0.78 if abs(s) > w * 0.3 else 0.95)], 0.035, 0.035, mat, tag='detail', ends=False)
        return
    if kind == 'lattice':
        _plane(B, q0, q1, z0, z1, n, 0.12, 'white_paint', tag=tag)
        for zz in (z0 + 0.04, z1 - 0.04):
            prim.obox(B, np.r_[q0 - n * 0.06, zz], np.r_[q1 - n * 0.06, zz], 0.09, 0.08, mat, tag='detail')
        st = 0.17
        for x in np.arange(st / 2, Lq, st):
            a = q0 + d * x
            prim.obox(B, np.r_[a - n * 0.06, z0], np.r_[a - n * 0.06, z1], 0.04, 0.04, mat, tag='detail', ends=False)
        for zz in np.arange(z0 + st, z1 - 0.05, st):
            prim.obox(B, np.r_[q0 - n * 0.065, zz], np.r_[q1 - n * 0.065, zz], 0.04, 0.04, mat, tag='detail', ends=False)
        return
    if kind == 'shoji':
        _plane(B, q0, q1, z0, z1, n, 0.08, 'white_paint', tag=tag)
        for x in np.arange(0.0, Lq + 0.01, Lq / max(1, round(Lq / 0.9))):
            a = q0 + d * x
            prim.obox(B, np.r_[a - n * 0.06, z0], np.r_[a - n * 0.06, z1], 0.06, 0.04, 'wood_natural', tag='detail', ends=False)
        for zz in np.arange(z0 + 0.3, z1, 0.45):
            prim.obox(B, np.r_[q0 - n * 0.065, zz], np.r_[q1 - n * 0.065, zz], 0.03, 0.03, 'wood_natural', tag='detail', ends=False)
        prim.obox(B, np.r_[q0 - n * 0.06, z0 + 0.15], np.r_[q1 - n * 0.06, z0 + 0.15], 0.06, 0.3, 'wood_natural', tag='detail')
        return
    if kind == 'maira':
        _plane(B, q0, q1, z0, z1, n, 0.07, mat, tag=tag)
        for x in np.arange(0.0, Lq + 0.01, Lq / max(1, round(Lq / 0.9))):
            a = q0 + d * x
            prim.obox(B, np.r_[a - n * 0.05, z0], np.r_[a - n * 0.05, z1], 0.07, 0.04, mat, tag='detail', ends=False)
        for zz in np.arange(z0 + 0.2, z1, 0.22):
            prim.obox(B, np.r_[q0 - n * 0.055, zz], np.r_[q1 - n * 0.055, zz], 0.025, 0.025, mat, tag='detail', ends=False)
        return
    if kind == 'glass':
        _plane(B, q0, q1, z0, z1, n, 0.1, 'glass', tag=tag); return
    if kind == 'dark':
        _plane(B, q0, q1, z0, z1, n, 0.6, 'wood_dark', tag=tag)
        return
    if kind == 'tatami_room':
        # an open bay showing the room: dark back wall, tatami floor strip, fusuma
        _plane(B, q0, q1, z0, z1, n, 2.2, 'white_paint', tag=tag)
        return
    raise ValueError(kind)

def katomado_ring(w, z0, z1, k=14):
    """花頭窓 outline in (s, z) around s = 0: bell shaped, flared sides, ogee top with two cusps"""
    h = z1 - z0
    pts = []
    for t in np.linspace(0, 1, 6):
        zz = z0 + t * 0.62 * h
        hw = w / 2 * (1.0 - 0.10 * math.sin(t * math.pi / 2) ** 0.8)
        pts.append((hw, zz))
    hw0 = w / 2 * 0.90; zc = z0 + 0.62 * h
    for t in np.linspace(0, 1, k // 2)[1:]:
        a = t * math.pi * 0.55
        pts.append((hw0 - (1 - math.cos(a)) * w * 0.16, zc + math.sin(a) * h * 0.22))
    s_c, z_c = pts[-1]
    pts.append((s_c - w * 0.035, z_c - h * 0.015))
    for t in np.linspace(0, 1, k // 2)[1:]:
        ss = (s_c - w * 0.035) * (1 - t)
        zz = (z_c - h * 0.015) + (z1 - (z_c - h * 0.015)) * (math.sin(t * math.pi / 2) ** 1.4)
        pts.append((ss, zz))
    right = pts
    left = [(-s, z) for (s, z) in right[::-1]][1:]
    return right + left[:-1]

# ------------------------------------------------------------------ railings
def railing_run(B, a, b, z, h=0.78, mat=WD, cap='metal_dark', giboshi=False, post_step=2.0):
    a = np.asarray(a, float); b = np.asarray(b, float)
    L = np.linalg.norm(b - a); k = max(1, int(round(L / post_step)))
    arch.railing(B, [a, b], z, h=h, mat=mat, cap_mat=cap, giboshi=giboshi)
    for i in range(1, k):
        p = a + (b - a) * i / k
        prim.cyl(B, np.r_[p, z], np.r_[p, z + h + 0.05], 0.05, 0.05, 6, mat, tag='detail')

def simple_rail(B, pts, z_of, h=0.75, mat=WD, post=1.8, rails=2, block=True, r=0.05):
    """a plain wooden rail fence (posts + rails) along a polyline; z_of(x, y) -> ground"""
    P = [np.asarray(p, float) for p in pts]
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]; L = np.linalg.norm(b - a)
        if L < 0.1: continue
        k = max(1, int(math.ceil(L / post)))
        for j in range(k + 1):
            if j == 0 and i > 0: continue
            q = a + (b - a) * j / k; zg = z_of(*q)
            prim.box(B, q[0] - r, q[1] - r, zg - 0.1, q[0] + r, q[1] + r, zg + h, mat, tag='detail')
        for m in range(rails):
            zz = h * (1.0 - 0.45 * m) - 0.04
            za, zb = z_of(*a) + zz, z_of(*b) + zz
            prim.obox(B, np.r_[a, za], np.r_[b, zb], r * 1.2, r * 1.2, mat, tag='detail')
    if block: block_line(B, [p for p in P], 0.4)

# ------------------------------------------------------------------ halls
def hall(B, S, loc, *, L, D, nu, nv, zf, H, r=0.22, pmat=WD, bmat=None, walls=None, wall_mat=None, head=None, band='white', ver=1.2,
         ver_sides=(0, 1, 2, 3), ver_drop=0.05, rail=False, rail_h=0.75, rail_gaps=(), skirt='white', bracket='funa', bs=1.0, bend='white_paint',
         roofkw=None, block_sides=(0, 1, 2, 3), floor_mat='wood_natural', ver_mat='wood_natural', pillar_round=False, ochien=None,
         grid_pts=None, us=None, vs=None, nageshi_mat=None, extra_band=None, plinth=None, walk_floor=True, roof=True):
    """a hall on a raised floor (walls per side per bay, verandas, brackets and a jk roof) in the frame `loc`;
    ochien = (width, drop): a lower veranda (落縁) outside the main one; plinth = (z_base, margin) a stone 基壇 under
    everything (floor pillars standing on it).  Returns a dict with heights and the roof."""
    if us is None or vs is None:
        us, vs = arch.grid(L, D, nu, nv)
    bmat = bmat or pmat; wall_mat = wall_mat or pmat; nageshi_mat = nageshi_mat or pmat
    head = head if head is not None else zf + H * 0.72
    ztop = zf + H
    zv = zf - ver_drop
    walls = walls or {}
    res = dict(us=us, vs=vs)
    with loc.frame(B):
        pts = set()
        for x in us: pts.add((round(x, 4), round(vs[0], 4))); pts.add((round(x, 4), round(vs[-1], 4)))
        for y in vs: pts.add((round(us[0], 4), round(y, 4))); pts.add((round(us[-1], 4), round(y, 4)))
        zbase = None
        if plinth is not None:
            zbase, mg = plinth
        for (x, y) in pts:
            zg = loc.g(S, x, y) if zbase is None else zbase
            zb = min(zg, zf - 0.35)
            if pillar_round:
                prim.cyl(B, (x, y, zb - 0.05), (x, y, zb + 0.14), r * 1.55, r * 1.4, 8, 'stone')
                prim.cyl(B, (x, y, zb + 0.1), (x, y, ztop), r, r * 0.97, 10, pmat, caps=(False, True))
            else:
                prim.box(B, x - r * 1.45, y - r * 1.45, zb - 0.1, x + r * 1.45, y + r * 1.45, zb + 0.12, 'stone')
                prim.box(B, x - r, y - r, zb + 0.1, x + r, y + r, ztop, pmat)
        ring = [(-L / 2, -D / 2), (L / 2, -D / 2), (L / 2, D / 2), (-L / 2, D / 2)]
        prim.polygon(B, ring, zf, floor_mat)
        if walk_floor: prim.polygon(B, ring, zf, 'stone', tag='walk')
        sides_pts = {0: [(x, vs[0]) for x in us], 1: [(us[-1], y) for y in vs], 2: [(x, vs[-1]) for x in us[::-1]], 3: [(us[0], y) for y in vs[::-1]]}
        if skirt and plinth is None:
            for k in range(4):
                sp = sides_pts[k]
                for i in range(len(sp) - 1):
                    a = np.array(sp[i]); b = np.array(sp[i + 1]); dd = nrm(b - a); n = np.array([dd[1], -dd[0]])
                    zb = min(loc.g(S, *a), loc.g(S, *b)) - 0.3
                    if zf - 0.12 - zb < 0.15: continue
                    a2 = a + dd * r * 0.9; b2 = b - dd * r * 0.9
                    if skirt == 'white': _plane(B, a2, b2, zb, zf - 0.12, n, 0.02, 'temple_wall', c0=WHITE)
                    else: _plane(B, a2, b2, zb, zf - 0.12, n, 0.02, skirt)
        for k in range(4):
            kinds = walls.get(k)
            if not kinds: continue
            sp = sides_pts[k]
            for i in range(len(sp) - 1):
                kd = kinds[i] if i < len(kinds) else kinds[-1]
                a = sp[i]; b = sp[i + 1]
                if kd not in ('open', 'none'): infill(B, a, b, zf + 0.04, head, kd, mat=wall_mat, r=r * 0.9, seed=i + 7 * k)
                if band and kd != 'none':
                    infill(B, a, b, head + 0.2, ztop - 0.32, band, mat=wall_mat, r=r * 0.9, seed=i)
        arch.nageshi(B, L, D, head + 0.2, nageshi_mat, h=0.22, w=0.11, out=r * 0.75)
        arch.nageshi(B, L, D, ztop, nageshi_mat, h=0.32, w=0.2, out=0.0)
        arch.nageshi(B, L, D, zf + 0.12, nageshi_mat, h=0.16, w=0.1, out=r * 0.75)
        if extra_band:
            for zz in extra_band: arch.nageshi(B, L, D, zz, nageshi_mat, h=0.2, w=0.1, out=r * 0.7)
        # verandas
        if ver and ver_sides:
            a_, c_ = L / 2, D / 2; w = ver
            w1 = w if 1 in ver_sides else 0; w3 = w if 3 in ver_sides else 0
            rects = {0: (-a_ - w3, -c_ - w, a_ + w1, -c_), 2: (-a_ - w3, c_, a_ + w1, c_ + w), 1: (a_, -c_, a_ + w, c_), 3: (-a_ - w, -c_, -a_, c_)}
            for k in ver_sides:
                x0, y0, x1, y1 = rects[k]
                prim.box(B, x0, y0, zv - 0.11, x1, y1, zv, ver_mat, faces='zZxXyY')
                rect_walk(B, x0, y0, x1, y1, zv)
                if k in (0, 2):
                    yy = y0 if k == 0 else y1; xs = np.linspace(x0 + 0.1, x1 - 0.1, max(2, int(round((x1 - x0) / 1.9)) + 1))
                    pp = [(x, yy + (0.08 if k == 0 else -0.08)) for x in xs]
                else:
                    xx = x1 if k == 1 else x0; ys = np.linspace(y0 + 0.1, y1 - 0.1, max(2, int(round((y1 - y0) / 1.9)) + 1))
                    pp = [(xx + (-0.08 if k == 1 else 0.08), y) for y in ys]
                for (px, py) in pp:
                    zg = loc.g(S, px, py) if zbase is None else zbase
                    if zv - 0.11 - zg > 0.12:
                        prim.box(B, px - 0.07, py - 0.07, zg - 0.1, px + 0.07, py + 0.07, zv - 0.11, WD, tag='detail')
            res['zv'] = zv
            if ochien:
                ow, od = ochien
                zo = zv - od
                a2, c2 = a_ + w, c_ + w
                orects = {0: (-a2 - (ow if 3 in ver_sides else 0), -c2 - ow, a2 + (ow if 1 in ver_sides else 0), -c2), 2: (-a2 - (ow if 3 in ver_sides else 0), c2, a2 + (ow if 1 in ver_sides else 0), c2 + ow),
                          1: (a2, -c2, a2 + ow, c2), 3: (-a2 - ow, -c2, -a2, c2)}
                for k in ver_sides:
                    x0, y0, x1, y1 = orects[k]
                    prim.box(B, x0, y0, zo - 0.1, x1, y1, zo, ver_mat, faces='zZxXyY')
                    rect_walk(B, x0, y0, x1, y1, zo)
                    if k in (0, 2):
                        yy = y0 + 0.1 if k == 0 else y1 - 0.1
                        for x in np.linspace(x0 + 0.1, x1 - 0.1, max(2, int(round((x1 - x0) / 1.8)) + 1)):
                            zg = loc.g(S, x, yy) if zbase is None else zbase
                            if zo - zg > 0.15: prim.box(B, x - 0.06, yy - 0.06, zg - 0.1, x + 0.06, yy + 0.06, zo - 0.1, WD, tag='detail')
                    else:
                        xx = x1 - 0.1 if k == 1 else x0 + 0.1
                        for y in np.linspace(y0 + 0.1, y1 - 0.1, max(2, int(round((y1 - y0) / 1.8)) + 1)):
                            zg = loc.g(S, xx, y) if zbase is None else zbase
                            if zo - zg > 0.15: prim.box(B, xx - 0.06, y - 0.06, zg - 0.1, xx + 0.06, y + 0.06, zo - 0.1, WD, tag='detail')
                res['zo'] = zo
            if rail:
                for k in ver_sides:
                    x0, y0, x1, y1 = rects[k]
                    if k == 0: seg = [(x0 + 0.08, y0 + 0.08), (x1 - 0.08, y0 + 0.08)]
                    elif k == 2: seg = [(x0 + 0.08, y1 - 0.08), (x1 - 0.08, y1 - 0.08)]
                    elif k == 1: seg = [(x1 - 0.08, y0 + 0.08), (x1 - 0.08, y1 - 0.08)]
                    else: seg = [(x0 + 0.08, y0 + 0.08), (x0 + 0.08, y1 - 0.08)]
                    gaps = [g for g in rail_gaps if g[0] == k]
                    pieces = [seg]
                    for (_, t0, t1) in gaps:
                        new = []
                        for (pa, pb) in pieces:
                            pa = np.array(pa); pb = np.array(pb); ax = 0 if k in (0, 2) else 1
                            lo, hi = min(pa[ax], pb[ax]), max(pa[ax], pb[ax])
                            if t1 <= lo or t0 >= hi: new.append((pa, pb)); continue
                            if t0 > lo + 0.3: q = pa.copy(); q[ax] = t0; new.append((np.where(np.arange(2) == ax, lo, pa), q))
                            if t1 < hi - 0.3: q = pb.copy(); q[ax] = t1; new.append((q, np.where(np.arange(2) == ax, hi, pb)))
                        pieces = new
                    for (pa, pb) in pieces:
                        railing_run(B, pa, pb, zv, h=rail_h)
                        ribbon(B, [pa, pb], 0.5, 'block', z=zv)
        # brackets and roof
        if roof:
            rk = dict(kind='irimoya', cover='hongawara', o=2.4, pitch=0.7, rafter_mat=bmat, rafter_end=bend)
            rk.update(roofkw or {})
            o = rk.pop('o')
            if bracket:
                top, reach = arch.bracket_row(B, L, D, ztop, bracket, bs, bmat, bend, us=us, vs=vs)
            else:
                top, reach = ztop + 0.3, 0.0
            R = jroof.Roof(L + 2 * reach, D + 2 * reach, top + ROOF_LIFT, o, **rk)
            zz = R.build(B)
            res.update(roof=R, top=top, reach=reach, **zz)
        res.update(ztop=ztop, head=head)
        for k in block_sides:
            sp = sides_pts[k]
            ribbon(B, [sp[0], sp[-1]], 0.5, 'block', z=zf)
    res['zf'] = zf
    return res

def stairs_build(B, p0, p1, z0, z1, w, mat='stone', cheek=None, riser=0.17):
    """straight flight (current frame) from (p0, z0) to (p1, z1) with a walk ramp; cheek boards in `cheek`"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    arch.stairs(B, p0, p1, z0, z1, w, mat, riser=riser)
    if cheek:
        d = nrm(p1 - p0); n = np.array([-d[1], d[0]])
        for sgn in (-1, 1):
            q0 = p0 + n * sgn * (w / 2 + 0.06); q1 = p1 + n * sgn * (w / 2 + 0.06)
            prim.obox(B, np.r_[q0, z0 + 0.15], np.r_[q1, z1 + 0.1], 0.1, 0.32, cheek)

def pent(B, u0, u1, v_wall, z_top, depth, drop, *, cover='sangawara', mat=WD, tag='main', rafters=True):
    """庇: a lean-to roof along a wall (current frame, wall at v = v_wall, the roof running out toward v-)"""
    vE = v_wall - depth; zE = z_top - drop
    cm = jroof.COVER_MAT[cover]
    quad(B, (u0 - 0.3, vE, zE), (u1 + 0.3, vE, zE), (u1 + 0.3, v_wall, z_top), (u0 - 0.3, v_wall, z_top), cm, tag=tag, out=(0, -drop, depth))
    quad(B, (u0 - 0.3, v_wall, z_top - 0.18), (u1 + 0.3, v_wall, z_top - 0.18), (u1 + 0.3, vE, zE - 0.18), (u0 - 0.3, vE, zE - 0.18), 'eave_wood', tag=tag, out=(0, drop, -depth))
    quad(B, (u0 - 0.3, vE, zE - 0.22), (u1 + 0.3, vE, zE - 0.22), (u1 + 0.3, vE, zE + 0.02), (u0 - 0.3, vE, zE + 0.02), mat, tag=tag, out=(0, -1, 0))
    for su, u in ((-1, u0 - 0.3), (1, u1 + 0.3)):
        P = np.array([(u, vE, zE + 0.02), (u, v_wall, z_top + 0.02), (u, v_wall, z_top - 0.2), (u, vE, zE - 0.22)])
        quad(B, *P, mat, tag=tag, out=(su, 0, 0))
    if cover in ('hongawara', 'sangawara'):
        for u in np.arange(u0 - 0.15, u1 + 0.3, 0.3):
            prim.cyl(B, (u, vE + 0.2, zE + 0.0), (u, vE - 0.02, zE - 0.03), 0.08, None, 6, cm, caps=(False, True), tag='detail')
    if rafters:
        for u in np.arange(u0 - 0.15, u1 + 0.3, 0.32):
            prim.obox(B, (u, vE + 0.02, zE - 0.28), (u, v_wall, z_top - 0.28), 0.07, 0.08, mat, tag='detail')
    prim.obox(B, (u0 - 0.3, vE + 0.35, zE - 0.4), (u1 + 0.3, vE + 0.35, zE - 0.4), 0.16, 0.2, mat)

# ------------------------------------------------------------------ gates
def gate(B, S, loc, *, zg=None, span=4.0, depth=2.2, H=4.0, r=0.25, mat=WD, roof_L=7.6, roof_D=5.0, pitch=0.78,
         cover='hongawara', z_eave=None, back_r=None, doors='open', bend='white_paint', kabuki_h=0.45, gable_wall=WD, ridge_end='oni',
         walk=True, sori=0.0, teri=1.4, wings=None, block_doors=False, verge=None):
    """薬医門 / 四脚門 in its frame: main pillars on v = 0, back pillars on v = +depth; kirizuma roof centred over the
    pillars, ridge along u.  wings = (width, h): low walls with doors to the sides"""
    with loc.frame(B):
        if zg is None: zg = loc.g(S, 0, depth / 2)
        back_r = back_r or r * 0.72
        ze = z_eave if z_eave is not None else zg + H + 0.75
        for sx in (-1, 1):
            x = sx * span / 2
            for (v, rr) in ((0.0, r), (depth, back_r)):
                zgg = loc.g(S, x, v)
                prim.box(B, x - rr * 1.45, v - rr * 1.45, min(zgg, zg) - 0.2, x + rr * 1.45, v + rr * 1.45, zg + 0.12, 'stone')
                prim.box(B, x - rr, v - rr, zg + 0.1, x + rr, v + rr, zg + H + 0.2, mat)
                if v == 0.0: prim.box(B, x - rr - 0.02, v - rr - 0.02, zg + 0.1, x + rr + 0.02, v + rr + 0.02, zg + 0.42, 'metal_dark', tag='detail')
            prim.obox(B, (x, -0.2, zg + H * 0.45), (x, depth + 0.2, zg + H * 0.45), 0.12, 0.26, mat)
        Lw = span + 2 * r + 0.3
        vo = verge if verge is not None else max(0.3, (roof_L - Lw) / 2)
        o = (roof_D - depth) / 2
        R = jroof.Roof(Lw, depth, ze, o, kind='kirizuma', cover=cover, pitch=pitch, verge=vo, rafter=0.28, rafter_mat=mat,
                       rafter_end=bend, gable_wall=gable_wall, ends=ridge_end, sori=sori, teri=teri)
        under = lambda s_: float(R.z(s_, R.a)) - R.edge - 0.12
        with Frame(B, 0, depth / 2, 0, 0):
            zz = R.build(B)
        prim.obox(B, (-span / 2 - 0.55, 0, zg + H - kabuki_h / 2), (span / 2 + 0.55, 0, zg + H - kabuki_h / 2), r * 1.1, kabuki_h, mat)
        prim.obox(B, (-span / 2 - 0.2, depth, zg + H - 0.3), (span / 2 + 0.2, depth, zg + H - 0.3), back_r * 1.1, 0.4, mat)
        s_p = 0.55
        zp = under(s_p) - 0.12
        zw = under(o) - 0.14
        for sx in (-1, 1):
            x = sx * span / 2
            for (v0, v1, sv) in ((-o + s_p - 0.25, 0.0, -1), (depth + o - s_p + 0.25, depth, 1)):
                prim.obox(B, (x, v0, zp - 0.2), (x, v1, zw - 0.2), 0.2, 0.26, mat)
                prim.obox(B, (x, v0, zp - 0.2), (x, v0 - sv * 0.03, zp - 0.2), 0.205, 0.265, bend, tag='detail')
            prim.obox(B, (x, 0.0, zw - 0.45), (x, depth, zw - 0.45), 0.18, 0.3, mat)
        for v in (-o + s_p, depth + o - s_p):
            prim.obox(B, (-roof_L / 2 + 0.7, v, zp), (roof_L / 2 - 0.7, v, zp), 0.2, 0.2, mat)
        zr_ = under(R.c) - 0.15
        prim.obox(B, (-roof_L / 2 + 0.6, depth / 2, zr_), (roof_L / 2 - 0.6, depth / 2, zr_), 0.22, 0.24, mat)
        for sx in (-1, 1):
            prim.obox(B, (sx * span / 2, depth / 2, zg + H - 0.1), (sx * span / 2, depth / 2, zr_), 0.18, 0.18, mat)
        prim.obox(B, (-span / 2, depth / 2, zg + H - 0.05), (span / 2, depth / 2, zg + H - 0.05), 0.2, 0.24, mat)
        if doors:
            dh = H - kabuki_h - 0.05; dw = span / 2 - r - 0.02
            for sx in (-1, 1):
                x = sx * (span / 2 - r - 0.06)
                if doors == 'open':
                    prim.box(B, x - 0.05, 0.25, zg + 0.08, x + 0.05, 0.25 + dw, zg + dh, WD)
                    for zz_ in np.linspace(zg + 0.5, zg + dh - 0.3, 4):
                        prim.box(B, x - sx * 0.05 - 0.04, 0.3, zz_ - 0.05, x - sx * 0.05 + 0.04, 0.2 + dw, zz_ + 0.05, 'metal_dark', tag='detail')
                else:
                    x0, x1 = sorted((sx * (span / 2 - r), 0.0))
                    prim.box(B, x0, -0.05, zg + 0.08, x1, 0.05, zg + dh, WD)
                    for zz_ in np.linspace(zg + 0.4, zg + dh - 0.3, 5):
                        prim.box(B, x0 + 0.05, -0.09, zz_ - 0.04, x1 - 0.05, -0.05, zz_ + 0.04, WD, tag='detail')
        if wings:
            ww, wh = wings
            for sx in (-1, 1):
                x0 = sx * (span / 2 + r); x1 = sx * (span / 2 + r + ww)
                prim.box(B, min(x0, x1), -0.12, zg - 0.2, max(x0, x1), 0.12, zg + wh, WD)
        if walk:
            rect_walk(B, -span / 2 + r, -roof_D / 2 + depth / 2, span / 2 - r, roof_D / 2 + depth / 2, zg + 0.04)
        for sx in (-1, 1):
            ribbon(B, [(sx * span / 2, -0.3), (sx * span / 2, depth + 0.3)], 0.7, 'block')
        if doors != 'open' and block_doors:
            ribbon(B, [(-span / 2, 0), (span / 2, 0)], 0.5, 'block')
    return zz

# ------------------------------------------------------------------ walls
def wall(B, S, pts, *, h=2.3, th=0.5, color=WHITE, stripes=0, base_h=0.35, coping='kawara', step=1.8, tag='main', block=True, zfix=None, zoff=0.0):
    """築地塀 / 土塀 along a world polyline: stone base, plaster (tinted), white stripes (筋塀), tiled coping; follows
    the terrain in short steps"""
    pts = [np.asarray(p, float) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; d = b - a; L = np.linalg.norm(d)
        if L < 0.2: continue
        d /= L; n = np.array([-d[1], d[0]])
        k = max(1, int(round(L / step)))
        for j in range(k):
            p = a + d * L * j / k; q = a + d * L * (j + 1) / k
            zz = zfix if zfix is not None else float(min(S.ground(*p), S.ground(*q))) + zoff
            ztop = zz + h
            ll = L / k
            for side in (-1, 1):
                A = p + n * side * th / 2; Bq = q + n * side * th / 2
                I = [[0, 1, 2], [0, 2, 3]] if side < 0 else [[0, 2, 1], [0, 3, 2]]
                Pz = np.array([np.r_[A, zz - 0.4], np.r_[Bq, zz - 0.4], np.r_[Bq, zz + base_h], np.r_[A, zz + base_h]])
                B.add(Pz, I, 'stone', UV=np.array([[0, 0], [ll, 0], [ll, base_h], [0, base_h]]), tag=tag)
                zl = zz + base_h
                Pw = np.array([np.r_[A, zl], np.r_[Bq, zl], np.r_[Bq, ztop], np.r_[A, ztop]])
                B.add(Pw, I, 'temple_wall', UV=np.array([[0, zl], [ll, zl], [ll, ztop], [0, ztop]]), tag=tag, c0=color)
                for s_ in range(stripes):
                    zs = ztop - 0.25 - 0.17 * s_
                    prim.obox(B, np.r_[p + n * side * (th / 2 + 0.006), zs], np.r_[q + n * side * (th / 2 + 0.006), zs], 0.012, 0.045, 'white_paint', tag='detail')
            for side in (-1, 1):
                A = p + n * side * (th / 2 + 0.28); Bq = q + n * side * (th / 2 + 0.28)
                P = np.array([np.r_[A, ztop - 0.02], np.r_[Bq, ztop - 0.02], np.r_[q, ztop + 0.36], np.r_[p, ztop + 0.36]])
                I = [[0, 1, 2], [0, 2, 3]] if side < 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I, coping, UV=np.array([[0, 0], [ll, 0], [ll, 0.5], [0, 0.5]]), tag=tag)
                quad(B, np.r_[A, ztop - 0.02], np.r_[Bq, ztop - 0.02], np.r_[Bq - n * side * 0.28, ztop - 0.02], np.r_[A - n * side * 0.28, ztop - 0.02], 'eave_wood', tag=tag, out=(0, 0, -1))
            prim.obox(B, np.r_[p - d * 0.02, ztop + 0.42], np.r_[q + d * 0.02, ztop + 0.42], 0.24, 0.16, 'ridge', tag=tag)
        for e, pe in ((0, a), (1, b)):
            if (e == 0 and i > 0) or (e == 1 and i < len(pts) - 2): continue
            zz = zfix if zfix is not None else float(S.ground(*pe)) + zoff
            sgn = -1 if e == 0 else 1
            A = pe + n * th / 2; Bq = pe - n * th / 2
            quad(B, np.r_[A, zz - 0.4], np.r_[Bq, zz - 0.4], np.r_[Bq, zz + h], np.r_[A, zz + h], 'temple_wall', tag=tag, out=(d[0] * sgn, d[1] * sgn, 0), c0=color)
        if block:
            ribbon(B, [a, b], max(0.6, th + 0.1), 'block')

def earth_wall(B, S, pts, **kw):
    kw.setdefault('color', (206, 172, 112, 35))
    wall(B, S, pts, **kw)

# ------------------------------------------------------------------ steps that follow the terrain
def terrain_steps(B, S, pts, w, *, rise=0.16, mat='stone', curb=True, z0=None, z1=None, zf=None, tag='main', rough=0.0, seed=0, walk=True):
    """stone steps along a world polyline: a riser wherever the profile climbs `rise` (from the DEM / zf(x, y), or
    linear z0 -> z1).  rough > 0 jitters the tread edges (natural stone steps)."""
    rng = np.random.default_rng(seed)
    gz = zf or (lambda x, y: S.ground(x, y))
    P = np.asarray(pts, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]; Lt = s[-1]
    ts = np.arange(0, Lt + 0.01, 0.05)
    X = np.interp(ts, s, P[:, 0]); Y = np.interp(ts, s, P[:, 1])
    if z0 is not None:
        Z = z0 + (z1 - z0) * ts / Lt
    else:
        Z = np.array([gz(x, y) for x, y in zip(X, Y)])
        Z = np.maximum.accumulate(Z) if Z[-1] >= Z[0] else np.minimum.accumulate(Z)
    up = Z[-1] >= Z[0]
    zc = Z[0]; t_last = 0.0; treads = []
    for i in range(1, len(ts)):
        if (Z[i] - zc >= rise) if up else (zc - Z[i] >= rise):
            treads.append((t_last, ts[i], zc)); zc = zc + (rise if up else -rise); t_last = ts[i]
    treads.append((t_last, Lt, zc))
    def at(t):
        x = np.interp(t, s, P[:, 0]); y = np.interp(t, s, P[:, 1])
        i = min(max(np.searchsorted(s, t) - 1, 0), len(P) - 2)
        dd = nrm(P[i + 1] - P[i]); return np.array([x, y]), dd
    zprev = None
    for (ta, tb, z) in treads:
        pa, da = at(ta); pb, db = at(tb)
        na = np.array([-da[1], da[0]]); nb = np.array([-db[1], db[0]])
        ja = rng.uniform(-rough, rough, 2) if rough else (0, 0)
        V = np.array([np.r_[pa - na * w / 2 + da * ja[0], z], np.r_[pa + na * w / 2 + da * ja[1], z], np.r_[pb + nb * w / 2, z], np.r_[pb - nb * w / 2, z]])
        I = [[0, 2, 1], [0, 3, 2]] if np.cross(V[1] - V[0], V[2] - V[0])[2] < 0 else [[0, 1, 2], [0, 2, 3]]
        B.add(V, I, mat, tag=tag)
        if zprev is not None and abs(z - zprev) > 0.01:
            lo, hi = min(z, zprev), max(z, zprev)
            R_ = np.array([np.r_[V[0][:2], lo - 0.05], np.r_[V[1][:2], lo - 0.05], np.r_[V[1][:2], hi], np.r_[V[0][:2], hi]])
            face = -da if z > zprev else da
            I2 = [[0, 1, 2], [0, 2, 3]]
            if np.cross(R_[1] - R_[0], R_[2] - R_[0])[:2] @ face < 0: I2 = [[0, 2, 1], [0, 3, 2]]
            B.add(R_, I2, mat, tag=tag)
        for sg in (-1, 1):
            qa = pa + na * sg * w / 2; qb = pb + nb * sg * w / 2
            zga = min(float(gz(*qa)), z) - 0.25; zgb = min(float(gz(*qb)), z) - 0.25
            V3 = np.array([np.r_[qa, zga], np.r_[qb, zgb], np.r_[qb, z], np.r_[qa, z]])
            I3 = [[0, 1, 2], [0, 2, 3]]
            if np.cross(V3[1] - V3[0], V3[2] - V3[0])[:2] @ (na * sg) < 0: I3 = [[0, 2, 1], [0, 3, 2]]
            B.add(V3, I3, mat, tag=tag)
        zprev = z
    if walk:
        W = np.c_[X[::4], Y[::4], np.interp(ts[::4], [t[0] for t in treads] + [Lt], [t[2] for t in treads] + [treads[-1][2]])]
        ribbon(B, W, w, 'walk')
    if curb:
        for sg in (-1, 1):
            C = []
            for (ta, tb, z) in treads:
                for t in (ta, tb):
                    p, dd = at(t); n = np.array([-dd[1], dd[0]])
                    C.append(np.r_[p + n * sg * (w / 2 + 0.15), z + 0.1])
            C = np.array(C)
            keep = np.r_[True, np.linalg.norm(np.diff(C, axis=0), axis=1) > 0.02]
            C = C[keep]
            if len(C) > 1: prim.sweep(B, C, [(-0.15, -0.3), (0.15, -0.3), (0.15, 0.0), (-0.15, 0.0)], 'curb', tag='detail')
    return treads

# ------------------------------------------------------------------ stones, lanterns, water
_ICO = None
def _ico():
    global _ICO
    if _ICO is None:
        t = (1 + 5 ** 0.5) / 2
        V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
        F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
        V /= np.linalg.norm(V, axis=1, keepdims=True)
        mid = {}; F2 = []; V = list(V)
        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                p = (np.asarray(V[a]) + np.asarray(V[b])) / 2; V.append(p / np.linalg.norm(p)); mid[k] = len(V) - 1
            return mid[k]
        for a, b_, c_ in F:
            ab, bc, ca = m(a, b_), m(b_, c_), m(c_, a)
            F2 += [[a, ab, ca], [b_, bc, ab], [c_, ca, bc], [ab, bc, ca]]
        _ICO = (np.array(V), np.array(F2))
    return _ICO

def rock(B, c, size, seed, mat='stone', flat=0.55, tag='main', tall=None, yaw=None, sink=0.25, lean=0.0, angular=0.0):
    """a garden stone (80 triangles): size = half-width; tall = height/size for standing stones (立石); angular adds
    facets (a quarried / split look)"""
    V, F = _ico()
    rng = np.random.default_rng(seed)
    d = 1 + 0.2 * np.sin(V @ rng.normal(0, 3, 3)) + 0.12 * np.sin(V @ rng.normal(0, 6, 3))
    if angular:
        for _ in range(3):
            nn = nrm(rng.normal(0, 1, 3)); cut = rng.uniform(0.55, 0.85)
            proj = V @ nn
            d = np.where(proj > cut, d * (cut / np.maximum(proj, 1e-3)) ** angular, d)
    hz = size * (tall if tall else flat) * rng.uniform(0.85, 1.15)
    W = V * d[:, None] * [size * rng.uniform(0.85, 1.2), size * rng.uniform(0.7, 1.05), hz]
    if lean:
        W[:, 0] += W[:, 2] * lean
    a = rng.uniform(0, 2 * math.pi) if yaw is None else yaw
    cy, sy = math.cos(a), math.sin(a)
    W = W @ np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]]).T + np.asarray(c, float) + [0, 0, hz * (1 - sink) - hz * 0.0]
    B.add(W, F, mat, smooth=True, tag=tag)
    return hz

def lantern(B, x, y, z, h=2.0, lamp=True, kind='kasuga', block=True):
    if kind == 'kasuga':
        arch.ishidoro(B, x, y, z, h=h, lamp=lamp)
        if lamp: B.lamp(x, y, z + h * 0.65, 4.0, (1.0, 0.62, 0.32))
    elif kind == 'yukimi':
        s = h / 1.4
        for k in range(3):
            a = 2 * math.pi * k / 3
            prim.cyl(B, (x + 0.35 * s * math.cos(a), y + 0.35 * s * math.sin(a), z), (x + 0.22 * s * math.cos(a), y + 0.22 * s * math.sin(a), z + 0.55 * s), 0.06 * s, 0.05 * s, 6, 'stone')
        prim.cyl(B, (x, y, z + 0.55 * s), (x, y, z + 0.65 * s), 0.32 * s, 0.32 * s, 6, 'stone')
        prim.cyl(B, (x, y, z + 0.65 * s), (x, y, z + 0.92 * s), 0.2 * s, 0.2 * s, 6, 'stone')
        if lamp:
            prim.cyl(B, (x, y, z + 0.7 * s), (x, y, z + 0.88 * s), 0.205 * s, 0.205 * s, 6, 'lantern_paper', caps=(False, False), tag='detail')
            B.lamp(x, y, z + 0.8 * s, 3.0, (1.0, 0.62, 0.32))
        prim.lathe(B, (x, y, z + 0.92 * s), [(0.62 * s, 0.0), (0.6 * s, 0.06 * s), (0.3 * s, 0.22 * s), (0.08 * s, 0.32 * s), (0.1 * s, 0.4 * s), (0.0, 0.48 * s)], 6, 'stone', smooth=False)
    elif kind == 'oki':
        # 置灯籠: a small lantern without a post
        s = h / 0.9
        prim.cyl(B, (x, y, z), (x, y, z + 0.18 * s), 0.25 * s, 0.22 * s, 6, 'stone')
        prim.cyl(B, (x, y, z + 0.18 * s), (x, y, z + 0.45 * s), 0.16 * s, 0.16 * s, 6, 'stone')
        if lamp:
            prim.cyl(B, (x, y, z + 0.22 * s), (x, y, z + 0.42 * s), 0.165 * s, 0.165 * s, 6, 'lantern_paper', caps=(False, False), tag='detail')
            B.lamp(x, y, z + 0.32 * s, 2.0, (1.0, 0.62, 0.32))
        prim.lathe(B, (x, y, z + 0.45 * s), [(0.34 * s, 0.0), (0.33 * s, 0.04 * s), (0.18 * s, 0.14 * s), (0.05 * s, 0.22 * s), (0.07 * s, 0.28 * s), (0.0, 0.34 * s)], 6, 'stone', smooth=False)
    if block: ribbon(B, [(x - 0.3, y), (x + 0.3, y)], 0.6, 'block')

def water(B, poly, z, tag='main'):
    polys = poly.geoms if hasattr(poly, 'geoms') else [poly]
    for p in polys:
        if p.is_empty or p.area < 0.5: continue
        ext = list(p.exterior.coords)[:-1]
        holes = [list(r.coords)[:-1] for r in p.interiors]
        prim.polygon(B, ext, z, 'water', holes=holes, tag=tag)

def chaikin(pts, n=1, closed=True):
    P = np.asarray(pts, float)
    for _ in range(n):
        Q = []
        m = len(P)
        for i in range(m if closed else m - 1):
            a = P[i]; b = P[(i + 1) % m]
            Q += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        if not closed: Q = [P[0]] + Q + [P[-1]]
        P = np.array(Q)
    return P

def mesh_region(B, poly, hf, res, mat='ground', surf_of=None, walk_of=None, tag='main'):
    """own ground over a polygon: a res grid clipped to the polygon; each triangle gets the surface id surf_of(x, y)
    (one sub-mesh per surface); walk_of(x, y) -> bool adds it to the walk mesh"""
    import mapbox_earcut as earcut
    x0, y0, x1, y1 = poly.bounds
    xs = np.arange(math.floor(x0 / res) * res, x1 + res, res); ys = np.arange(math.floor(y0 / res) * res, y1 + res, res)
    prep = poly; shapely.prepare(prep)
    tris = []
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            c = box(xs[i], ys[j], xs[i + 1], ys[j + 1])
            if prep.contains(c):
                a, b, cc, d = (xs[i], ys[j]), (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])
                tris += [np.array([a, b, cc]), np.array([a, cc, d])]
            elif prep.intersects(c):
                g = poly.intersection(c)
                for p in (g.geoms if hasattr(g, 'geoms') else [g]):
                    if p.geom_type != 'Polygon' or p.area < 1e-4: continue
                    V = np.array(p.exterior.coords)[:-1]
                    rr = [V] + [np.array(r.coords)[:-1] for r in p.interiors]
                    A = np.concatenate(rr); ends = np.cumsum([len(r) for r in rr]).astype(np.uint32)
                    I = earcut.triangulate_float64(A, ends).reshape(-1, 3)
                    for t in I: tris.append(A[t])
    T = np.array(tris)
    key = np.round(T.reshape(-1, 2) * 1000).astype(np.int64)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    V2 = uniq / 1000.0
    Z = np.array([hf(x, y) for (x, y) in V2])
    P = np.c_[V2, Z]
    I = inv.reshape(-1, 3)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    I[fn[:, 2] < 0] = I[fn[:, 2] < 0][:, ::-1]
    C = P[I].mean(1)
    sids = np.array([surf_of(x, y) for (x, y, _) in C]) if surf_of else np.zeros(len(I), int)
    from jk.core import vertex_normals
    N = vertex_normals(P, I)
    for s in np.unique(sids):
        sel = I[sids == s]
        vid, inv2 = np.unique(sel.ravel(), return_inverse=True)
        B.add(P[vid], inv2.reshape(-1, 3), mat, UV=P[vid][:, :2], N=N[vid], tag=tag, c1=(0, 0, 0, int(s)))
    if walk_of:
        w = np.array([walk_of(x, y) for (x, y, _) in C])
        sel = I[w]
        if len(sel):
            vid, inv2 = np.unique(sel.ravel(), return_inverse=True)
            B.add(P[vid] + [0, 0, 0.01], inv2.reshape(-1, 3), 'stone', tag='walk')
    return P, I

# ------------------------------------------------------------------ 相輪
def sorin(B, x, y, z, *, Hs=4.6, s=1.0, chains_to=None):
    prim.box(B, x - 0.42 * s, y - 0.42 * s, z - 0.1, x + 0.42 * s, y + 0.42 * s, z + 0.32 * s, 'bronze')
    prim.lathe(B, (x, y, z + 0.32 * s), [(0.36 * s, 0.0), (0.38 * s, 0.12 * s), (0.3 * s, 0.32 * s), (0.12 * s, 0.4 * s)], 12, 'bronze')
    prim.lathe(B, (x, y, z + 0.72 * s), [(0.1 * s, 0.0), (0.3 * s, 0.1 * s), (0.34 * s, 0.2 * s), (0.08 * s, 0.22 * s)], 12, 'bronze')
    zr0 = z + 0.94 * s; zr1 = z + Hs * 0.72
    prim.cyl(B, (x, y, z + 0.3 * s), (x, y, z + Hs - 0.2), 0.07 * s, 0.05 * s, 8, 'bronze')
    for k in range(9):
        zz = zr0 + (zr1 - zr0) * k / 8.6
        prim.lathe(B, (x, y, zz), [(0.08 * s, 0.0), (0.26 * s, 0.02 * s), (0.27 * s, 0.07 * s), (0.08 * s, 0.09 * s)], 12, 'bronze', tag='detail')
    zw = zr1 + 0.15 * s
    for k in range(4):
        a = math.pi * k / 4
        c, sn = math.cos(a), math.sin(a)
        P = np.array([(x - 0.3 * s * c, y - 0.3 * s * sn, zw), (x + 0.3 * s * c, y + 0.3 * s * sn, zw), (x + 0.22 * s * c, y + 0.22 * s * sn, zw + 0.75 * s), (x, y, zw + 0.95 * s), (x - 0.22 * s * c, y - 0.22 * s * sn, zw + 0.75 * s)])
        I = [[0, 1, 2], [0, 2, 3], [0, 3, 4]]
        B.add(P, I, 'bronze', tag='detail'); B.add(P, [t[::-1] for t in I], 'bronze', tag='detail')
    prim.lathe(B, (x, y, zw + 1.0 * s), [(0.05 * s, 0.0), (0.16 * s, 0.05 * s), (0.16 * s, 0.12 * s), (0.05 * s, 0.17 * s), (0.11 * s, 0.25 * s), (0.12 * s, 0.33 * s), (0.06 * s, 0.42 * s), (0.0, 0.46 * s)], 10, 'bronze')
    if chains_to:
        top = np.array([x, y, zr1 - 0.1])
        for c in chains_to:
            c = np.asarray(c, float)
            pts = [top + (c - top) * t + np.array([0, 0, -0.35 * 4 * t * (1 - t)]) for t in np.linspace(0, 1, 7)]
            for i in range(len(pts) - 1):
                prim.cyl(B, pts[i], pts[i + 1], 0.022, 0.022, 4, 'metal_dark', caps=(False, False), tag='detail')
            prim.lathe(B, c - [0, 0, 0.45], [(0.0, 0.0), (0.09, 0.05), (0.1, 0.25), (0.05, 0.32), (0.0, 0.35)], 8, 'bronze', tag='detail')

def ring_railing(B, cx, cy, z, R, h=0.6, n=24, mat=WD):
    pts = [(cx + R * math.cos(2 * math.pi * k / n), cy + R * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
    for zz, wd in ((z + h, 0.07), (z + h * 0.45, 0.05), (z + 0.04, 0.08)):
        Q = np.array([np.r_[p, zz] for p in pts])
        prim.sweep(B, Q, [(-wd / 2, -wd / 2), (wd / 2, -wd / 2), (wd / 2, wd / 2), (-wd / 2, wd / 2)], mat, tag='detail')
    for p in pts[:-1:2]:
        prim.cyl(B, np.r_[p, z], np.r_[p, z + h + 0.04], 0.04, 0.04, 6, mat, tag='detail')

# ------------------------------------------------------------------ the neighbour (arashiyama: 長辻通, the river, 渡月橋)
_NB = None
def neighbour_zone():
    """the arashiyama site's own ground and replaced buildings (its EDITS cut + exclude): we keep out of them"""
    global _NB
    if _NB is None:
        import json, os
        f = '/home/kazu/work/kyoto-assets/heroes/arashiyama.npz'
        polys = []
        if os.path.exists(f):
            try:
                ed = json.loads(bytes(np.load(f)['EDITS']).decode())
                for r in ed.get('cut', []) + ed.get('exclude', []):
                    polys.append((Polygon(r[0], r[1:]) if isinstance(r[0][0], (list, tuple)) else Polygon(r)).buffer(0))
            except Exception as e:
                print('neighbour edits unreadable', e)
        _NB = shapely.unary_union(polys).buffer(1.5) if polys else Polygon()
    return _NB

# ------------------------------------------------------------------ planting
def poisson(poly, spacing, rng, limit=20000):
    if poly is None or poly.is_empty: return np.zeros((0, 2))
    x0, y0, x1, y1 = poly.bounds
    n = min(limit, int(poly.area / (spacing * spacing) * 1.3) + 1)
    cand = np.column_stack([rng.uniform(x0, x1, n * 8), rng.uniform(y0, y1, n * 8)])
    cand = cand[shapely.contains_xy(poly, cand[:, 0], cand[:, 1])]
    out = []; grid = {}
    s2 = spacing * spacing
    for p in cand:
        k = (int(p[0] // spacing), int(p[1] // spacing)); ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for q in grid.get((k[0] + dx, k[1] + dy), ()):
                    if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < s2: ok = False; break
                if not ok: break
            if not ok: break
        if ok:
            out.append(p); grid.setdefault(k, []).append(p)
            if len(out) >= limit: break
    return np.array(out) if out else np.zeros((0, 2))

SHOTS = []           # the site's preview cameras (set by tenryuji.build): planting keeps their foreground open
CROWN = {'momiji': (6.5, 0.62), 'ichou': (14.0, 0.28), 'sakura': (7.5, 0.7), 'keyaki': (16.0, 0.46), 'matsu': (7.5, 0.45), 'sugi': (23.0, 0.17),
         'hinoki': (18.0, 0.22), 'kashi': (11.0, 0.48), 'yanagi': (8.5, 0.5), 'tsutsuji': (1.1, 0.9), 'take': (11.5, 0.12)}

def blocks_view(name, x, y, z, sc, near=16.0, shots=None):
    """True if the tree's crown would fill the foreground (closer than `near`) of one of the preview viewpoints"""
    H0, R0 = CROWN[name]
    H = H0 * sc; r = R0 * H * 0.85
    C = np.array([x, y, z + 0.6 * H])
    for (_, cam, tgt, lens) in (shots if shots is not None else SHOTS):
        cam = np.asarray(cam, float); tgt = np.asarray(tgt, float)
        if np.linalg.norm(cam[:2] - C[:2]) > near + r + 5: continue
        d = tgt - cam; d /= np.linalg.norm(d)
        right = np.cross(d, [0, 0, 1.0]); right /= max(np.linalg.norm(right), 1e-6); up = np.cross(right, d)
        v = C - cam; a = v @ d
        if np.linalg.norm(v) < r + 2.5 and a > -2.0: return True          # a crown right over / beside the camera
        if a < -r or a > near + r: continue
        th = 18.0 / lens * 1.1; tv = 10.125 / lens * 1.1
        if abs(v @ right) - r < max(a, 0) * th + 0.5 and abs(v @ up) - r * 0.9 < max(a, 0) * tv + 0.5: return True
    return False

def pick(mix, u):
    acc = 0.0
    for n, w in mix:
        acc += w
        if u < acc: return n
    return mix[-1][0]

# ------------------------------------------------------------------ preview-only: tree proxies, vertex colours
TREE_COL = {'momiji': (0.62, 0.07, 0.03), 'ichou': (0.85, 0.62, 0.05), 'sakura': (0.55, 0.25, 0.1), 'keyaki': (0.5, 0.28, 0.08),
            'matsu': (0.06, 0.16, 0.06), 'sugi': (0.05, 0.12, 0.05), 'hinoki': (0.06, 0.14, 0.06), 'kashi': (0.08, 0.18, 0.06),
            'yanagi': (0.3, 0.42, 0.1), 'tsutsuji': (0.07, 0.2, 0.06), 'take': (0.22, 0.38, 0.1)}
TREE_SIZE = {'momiji': (6.5, 0.62, 'dome'), 'ichou': (14.0, 0.28, 'oval'), 'sakura': (7.5, 0.7, 'dome'), 'keyaki': (16.0, 0.46, 'dome'),
             'matsu': (7.5, 0.45, 'pads'), 'sugi': (23.0, 0.17, 'cone'), 'hinoki': (18.0, 0.22, 'cone'), 'kashi': (11.0, 0.48, 'dome'),
             'yanagi': (8.5, 0.5, 'dome'), 'tsutsuji': (1.1, 0.9, 'dome'), 'take': (11.5, 0.18, 'bamboo')}

def cut_preview_terrain(S):
    import bpy, bmesh
    if not S.cut: return
    cut = shapely.unary_union([Polygon(c[0], c[1:]) if isinstance(c[0][0], (list, tuple)) else Polygon(c) for c in S.cut])
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or not ob.name.startswith('terrain'): continue
        me = ob.data
        n = len(me.polygons)
        C = np.zeros(n * 3); me.polygons.foreach_get('center', C); C = C.reshape(-1, 3)
        inside = shapely.contains_xy(cut, C[:, 0], C[:, 1])
        if not inside.any(): continue
        bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(inside)[0]], context='FACES_ONLY')
        bm.to_mesh(me); bm.free(); me.update()

def add_preview_proxies(B, S=None, extra=None):
    """Blender objects for the preview renders only (added after the .blend is saved): tree proxies (bamboo as clumps of
    culms), the tinted vertex colours of cloth / plaster, back-face culling as the viewer draws"""
    import bpy, os
    if S is not None: cut_preview_terrain(S)
    from jk.core import Builder, to_objects
    names = Builder.TREE_SPECIES
    T = Builder('tree_proxies')
    rng = np.random.default_rng(7)
    for (sp, x, y, z, sc, yaw) in ([] if os.environ.get('TJ_NOTREES') else B.trees):
        name = names[int(sp)]
        H0, R0, shape = TREE_SIZE[name]
        Hh = H0 * sc; Rr = max(0.4, R0 * Hh)
        col = tuple(int(255 * c) for c in TREE_COL[name]) + (0,)
        if shape == 'bamboo':
            for k in range(int(rng.integers(5, 8))):
                off = rng.normal(0, 0.35, 2); h = Hh * rng.uniform(0.75, 1.0); bend = rng.normal(0, 0.05, 2) * h
                p0 = np.array([x + off[0], y + off[1], z - 0.2]); p1 = p0 + np.array([bend[0], bend[1], h])
                prim.cyl(T, p0, p1, 0.045 * sc, 0.025 * sc, 4, 'cloth', caps=(False, False), c0=(120, 140, 70, 0))
                pm = p0 + (p1 - p0) * 0.62
                prim.cyl(T, pm, p1 + (p1 - p0) * 0.04, 0.55 * sc, 0.12 * sc, 5, 'cloth', caps=(True, False), c0=col)
            continue
        prim.cyl(T, (x, y, z - 0.2), (x, y, z + Hh * 0.45), max(0.08, Hh * 0.018), max(0.05, Hh * 0.012), 5, 'wood_dark')
        if shape == 'cone':
            prof = [(0.0, Hh * 0.25), (Rr, Hh * 0.35), (Rr * 0.6, Hh * 0.7), (0.0, Hh)]
        elif shape == 'pads':
            prof = [(0.0, Hh * 0.45), (Rr * 1.1, Hh * 0.55), (Rr * 0.9, Hh * 0.8), (0.0, Hh * 0.88)]
        elif shape == 'oval':
            prof = [(0.0, Hh * 0.15), (Rr, Hh * 0.35), (Rr * 1.05, Hh * 0.6), (Rr * 0.6, Hh * 0.88), (0.0, Hh)]
        else:
            prof = [(0.0, Hh * 0.3), (Rr * 0.85, Hh * 0.38), (Rr, Hh * 0.6), (Rr * 0.7, Hh * 0.88), (0.0, Hh)]
        prof = [(rr * rng.uniform(0.9, 1.1), zz) for (rr, zz) in prof]
        prim.lathe(T, (x, y, z), prof, 9, 'cloth', c0=col)
    objs = to_objects(T, name='tree_proxies') if T.parts else []
    if extra is not None and extra.parts:
        objs += to_objects(extra, name='preview_ground')
    for ob in list(bpy.data.objects):
        if not ob.type == 'MESH': continue
        if ob.name.startswith('tree_proxies'): src = T
        elif ob.name.startswith('preview_ground'): src = extra
        elif ob.get('jk_tag') in ('main', 'detail') and not ob.name.startswith('terrain'): src = B
        else: continue
        M = src.merged((ob['jk_tag'],)) if 'jk_tag' in ob else None
        if M is None or len(M['P']) != len(ob.data.vertices): continue
        col = (M['C0'][:, :3].astype(np.float32) / 255.0) ** 2.2
        attr = ob.data.color_attributes.new('C0', 'FLOAT_COLOR', 'POINT')
        attr.data.foreach_set('color', np.c_[col, np.ones(len(col))].ravel().astype(np.float32))
    for m in bpy.data.materials:
        if m.name.startswith('jk_') and m.name not in ('jk_water',): m.use_backface_culling = True
    for nm in ('jk_cloth', 'jk_temple_wall'):
        m = bpy.data.materials.get(nm)
        if m is None: continue
        nt = m.node_tree; bs = nt.nodes.get('Principled BSDF')
        at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'C0'
        if nm == 'jk_cloth':
            nt.links.new(at.outputs['Color'], bs.inputs['Base Color'])
        else:
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0
            mix.inputs['A'].default_value = (0.85, 0.84, 0.8, 1)
            nt.links.new(at.outputs['Color'], mix.inputs['B']); nt.links.new(mix.outputs['Result'], bs.inputs['Base Color'])
    return objs
