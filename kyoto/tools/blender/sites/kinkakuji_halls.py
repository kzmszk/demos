"""金閣寺: the buildings other than the 舎利殿 — 方丈, 庫裏, 書院 and the annex behind, the connecting corridors, 総門 (with
its lodge, the stone bridge and the 筋塀), 唐門 (向唐門), 鐘楼, 不動堂, 夕佳亭, the tea house / shops / offices, walls.
Garden-local coordinates (origin = the 舎利殿's centre, world axes), z absolute; gz(x, y) = DEM height (garden-local).
The hall builder started from the 銀閣寺 site's, the karamon / gate / wall from the 永観堂 site's (copied, then edited)."""
import math
import numpy as np
from jk import prim, arch, Frame
from jk import roof as jroof
from . import kinkakuji_util as U

WD = 'wood_dark'
WHITE = (238, 234, 224, 35)
OCHRE = (206, 172, 116, 35)

def quad(B, a, b, c, d, mat, tag='main', **kw):
    U.quad(B, a, b, c, d, mat, tag=tag, **kw)

def roof_pitch(L, D, z_eave, o, ridge, teri, kind):
    c = D / 2 + o
    if kind == 'hogyo': c = max(L, D) / 2 + o
    g = (o / c) ** teri
    H = max(0.5, (ridge - z_eave) / (1 - g))
    return H / c

# ------------------------------------------------------------------ a traditional hall
def hall(B, cx, cy, yaw, z0, L, D, nb=(4, 3), fit=None, floor=0.6, wall=2.9, nage=1.8, ver=(), ver_w=1.0, roof='irimoya',
         cover='hiwada', o=1.5, ridge=None, teri=1.4, rafter=0.35, tiers=1, sori=0.2, sori_len=0.5, gable_frac=0.5, funa=True,
         pillar=0.1, mat=WD, ends='oni', detail=True, base_h=0.15, verge=0.9, edge=None, walls=True, rafter_end=None, grid=None):
    """u along L (the front at v = -D/2 faces -v).  fit(face, bay) -> fitting name for the bay; faces 0 front, 1 right (u+),
    2 back, 3 left.  Returns the roof heights."""
    with Frame(B, cx, cy, z0, yaw):
        us = np.linspace(-L / 2, L / 2, nb[0] + 1) if grid is None else np.asarray(grid[0])
        vs = np.linspace(-D / 2, D / 2, nb[1] + 1) if grid is None else np.asarray(grid[1])
        a, c = L / 2, D / 2
        FL = floor; NG = floor + nage; PL = floor + wall
        # base: stone curb, dark underfloor, floor
        ew = [ver_w if k in ver else 0.0 for k in range(4)]
        outer = [(-a - ew[3] - 0.15, -c - ew[0] - 0.15), (a + ew[1] + 0.15, -c - ew[0] - 0.15), (a + ew[1] + 0.15, c + ew[2] + 0.15), (-a - ew[3] - 0.15, c + ew[2] + 0.15)]
        prim.prism(B, outer, -0.25, base_h, 'stone')
        if FL > base_h + 0.1:
            prim.prism(B, [(-a + 0.02, -c + 0.02), (a - 0.02, -c + 0.02), (a - 0.02, c - 0.02), (-a + 0.02, c - 0.02)], base_h, FL - 0.1, mat, top=False)
        prim.polygon(B, [(-a, -c), (a, -c), (a, c), (-a, c)], FL, 'wood_natural', tag='walk')
        # pillars
        pts = set([(x, y) for x in us for y in (vs[0], vs[-1])] + [(x, y) for y in vs for x in (us[0], us[-1])])
        for (x, y) in pts:
            prim.box(B, x - pillar, y - pillar, base_h, x + pillar, y + pillar, PL, mat)
        faces = [((-a, -c), (a, -c), (0, -1), us), ((a, -c), (a, c), (1, 0), vs), ((a, c), (-a, c), (0, 1), us[::-1]), ((-a, c), (-a, -c), (-1, 0), vs[::-1])]
        for k, (p0, p1, n, sp) in enumerate(faces):
            p0 = np.array(p0, float); p1 = np.array(p1, float); d = (p1 - p0) / np.linalg.norm(p1 - p0)
            Lf = float(np.linalg.norm(p1 - p0))
            full = U.Bay(B, p0, p1, n)
            if walls:
                full.box(-0.1, Lf + 0.1, FL - 0.14, FL + 0.03, -0.07, 0.07, mat)                 # 敷居 / 足固
                full.box(-0.1, Lf + 0.1, NG, NG + 0.12, -0.05, 0.08, mat)                        # 内法長押
                full.plaster(0.1, Lf - 0.1, NG + 0.12, PL, off=-0.03)                            # 小壁
            full.box(-0.15, Lf + 0.15, PL, PL + 0.2, -0.09, 0.09, mat)                          # 桁
            if funa:
                for s in np.r_[0.0, np.abs(np.asarray(sp)[1:-1] - np.asarray(sp)[0]), Lf]:
                    full.box(s - 0.45, s + 0.45, PL - 0.13, PL, -0.07, 0.07, mat, tag='detail')
            if not walls: continue
            edges = np.abs(np.asarray(sp) - np.asarray(sp)[0])
            for i in range(len(edges) - 1):
                kind = fit(k, i) if fit else 'plaster'
                bay = U.Bay(B, p0 + d * edges[i], p0 + d * edges[i + 1], n)
                s0, s1 = pillar, bay.L - pillar
                z0_, z1_ = FL + 0.03, NG
                fitting(bay, kind, s0, s1, z0_, z1_, mat)
        # verandas (縁)
        for k in ver:
            w = ver_w
            r = {0: (-a - ew[3], -c - w, a + ew[1], -c), 1: (a, -c - ew[0], a + w, c + ew[2]), 2: (-a - ew[3], c, a + ew[1], c + w), 3: (-a - w, -c - ew[0], -a, c + ew[2])}[k]
            prim.box(B, r[0], r[1], FL - 0.17, r[2], r[3], FL - 0.08, 'eave_wood')
            prim.polygon(B, [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])], FL - 0.08, 'wood_natural', tag='walk')
            # boards
            if detail:
                along_u = k in (0, 2)
                if along_u:
                    yy = r[1] if k == 0 else r[3]
                    for x in np.arange(r[0] + 0.12, r[2], 0.24): prim.box(B, x - 0.006, r[1], FL - 0.08, x + 0.006, r[3], FL - 0.075, mat, tag='detail')
                else:
                    for y in np.arange(r[1] + 0.12, r[3], 0.24): prim.box(B, r[0], y - 0.006, FL - 0.08, r[2], y + 0.006, FL - 0.075, mat, tag='detail')
            # posts under the outer edge
            if k in (0, 2):
                yy = r[1] + 0.08 if k == 0 else r[3] - 0.08
                for x in np.linspace(r[0] + 0.08, r[2] - 0.08, max(2, int((r[2] - r[0]) / 1.9)) + 1):
                    prim.box(B, x - 0.06, yy - 0.06, base_h, x + 0.06, yy + 0.06, FL - 0.17, mat)
                prim.box(B, r[0], (r[1] if k == 0 else r[3] - 0.08), FL - 0.3, r[2], (r[1] + 0.08 if k == 0 else r[3]), FL - 0.17, mat)
            else:
                xx = r[2] - 0.08 if k == 1 else r[0] + 0.08
                for y in np.linspace(r[1] + 0.08, r[3] - 0.08, max(2, int((r[3] - r[1]) / 1.9)) + 1):
                    prim.box(B, xx - 0.06, y - 0.06, base_h, xx + 0.06, y + 0.06, FL - 0.17, mat)
                prim.box(B, (r[2] - 0.08 if k == 1 else r[0]), r[1], FL - 0.3, (r[2] if k == 1 else r[0] + 0.08), r[3], FL - 0.17, mat)
        # roof: its surface over the wall plate leaves room for the eave's thickness; a band closes the wall up to the soffit
        e_th = edge if edge is not None else (0.3 if cover in ('hiwada', 'kokera') else 0.32)
        z_eave = PL + 0.2 + e_th + 0.08
        if walls:
            for k, (p0, p1, n, sp) in enumerate(faces):
                U.Bay(B, p0, p1, n).plaster(-0.05, float(np.linalg.norm(np.subtract(p1, p0))) + 0.05, PL + 0.18, PL + 0.2 + e_th + 0.03, off=-0.06)
        ridge_rel = (ridge - z0) if ridge is not None else z_eave + 2.5
        pitch = roof_pitch(L, D, z_eave, o, ridge_rel, teri, roof)
        info = jroof.roof(B, L, D, z_eave, o, kind=roof, cover=cover, pitch=pitch, teri=teri, sori=sori, sori_len=sori_len, gable_frac=gable_frac,
                          rafter=rafter, tiers=tiers, rafter_mat=mat, rafter_end=rafter_end or mat, ends=ends, verge=verge,
                          edge=edge if edge is not None else (0.3 if cover in ('hiwada', 'kokera') else 0.32), bargeboard_mat=mat)
        info['FL'] = FL
        return info

def fitting(bay, kind, s0, s1, z0, z1, mat=WD):
    if kind == 'plaster': bay.plaster(s0, s1, z0, z1, off=-0.03)
    elif kind == 'shoji': bay.shoji(s0, s1, z0, z1, 2, koshi=0.3, off=-0.03)
    elif kind == 'shoji_k': bay.shoji(s0, s1, z0, z1, 2, koshi=0.62, off=-0.03)
    elif kind == 'shoji4': bay.shoji(s0, s1, z0, z1, 4, koshi=0.3, off=-0.03)
    elif kind == 'mairado': bay.mairado(s0, s1, z0, z1, 2, off=-0.02, mat=mat)
    elif kind == 'mairado4': bay.mairado(s0, s1, z0, z1, 4, off=-0.02, mat=mat)
    elif kind == 'board': bay.boards(s0, s1, z0, z1, off=-0.02, mat=mat, batten=0.45)
    elif kind == 'renji':
        bay.boards(s0, s1, z0, z0 + 0.75, off=-0.02, mat=mat, batten=0)
        bay.box(s0, s1, z0 + 0.75, z0 + 0.82, -0.05, 0.05, mat)
        bay.koshi(s0, s1, z0 + 0.82, z1, off=-0.02, mat=mat, step=0.11)
    elif kind == 'karado':
        bay.karado(s0 + 0.04, s1 - 0.04, z0, z1, off=-0.03, mat=mat, lattice=0.55)
    elif kind == 'karado_open':
        bay.karado(s0 + 0.04, s1 - 0.04, z0, z1, off=-0.03, mat=mat, lattice=0.55, open_=True)
        dark_room(bay, (s0 + s1) / 2, s1, z0, z1)
    elif kind == 'koshi': bay.koshi(s0, s1, z0, z1, off=-0.03, mat=mat, step=0.06)
    elif kind == 'shoji_open':
        bay.shoji(s0, s1, z0, z1, 2, koshi=0.3, off=-0.03, open_=1)
        dark_room(bay, (s0 + s1) / 2, s1, z0, z1)
    elif kind == 'open': pass
    elif kind == 'dark':
        bay.plane(s0, s1, z0, z1, 'glass', off=-0.6)

def dark_room(bay, s0, s1, z0, z1):
    """a glimpse of a room: tatami floor, a dim back wall"""
    a = bay.P(s0, 0, -0.05); b = bay.P(s1, 0, -0.05); a2 = bay.P(s0, 0, -1.8); b2 = bay.P(s1, 0, -1.8)
    quad(bay.B, (a[0], a[1], z0 - 0.02), (b[0], b[1], z0 - 0.02), (b2[0], b2[1], z0 - 0.02), (a2[0], a2[1], z0 - 0.02), 'tatami', out=(0, 0, 1))
    bay.plaster(s0, s1, z0, z1 + 0.3, off=-1.8, tint=(170, 160, 140))
    for s in (s0, s1):
        p = bay.P(s, 0, -0.05); q = bay.P(s, 0, -1.8)
        quad(bay.B, (p[0], p[1], z0), (q[0], q[1], z0), (q[0], q[1], z1 + 0.05), (p[0], p[1], z1 + 0.05), 'temple_wall', c0=(200, 196, 186, 35), both=True)
    quad(bay.B, (a[0], a[1], z1 + 0.05), (a2[0], a2[1], z1 + 0.05), (b2[0], b2[1], z1 + 0.05), (b[0], b[1], z1 + 0.05), 'wood_natural', out=(0, 0, -1))

# ------------------------------------------------------------------ frames, ribbons, footprints
class Loc:
    """a building frame: centre (cx, cy), yaw = direction of local +u (ccw from east); the front (v-) faces yaw - 90 deg"""
    def __init__(self, cx, cy, yaw):
        self.cx, self.cy, self.yaw = float(cx), float(cy), float(yaw)
        self.c, self.s = math.cos(yaw), math.sin(yaw)
    def w(self, u, v):
        return (self.cx + self.c * u - self.s * v, self.cy + self.s * u + self.c * v)
    def frame(self, B):
        return Frame(B, self.cx, self.cy, 0.0, self.yaw)

def ribbon(B, pts, w, tag, z=None, mat='stone', off=0.0):
    P = np.asarray(pts, float)
    if P.shape[1] == 2: P = np.c_[P, np.full(len(P), 0.0 if z is None else z)]
    V = []; I = []
    for i in range(len(P)):
        t = P[min(i + 1, len(P) - 1), :2] - P[max(i - 1, 0), :2]; t = t / max(np.linalg.norm(t), 1e-9); n = np.array([t[1], -t[0]])
        a = P[i, :2] + n * (off - w / 2); b = P[i, :2] + n * (off + w / 2)
        V += [[a[0], a[1], P[i, 2]], [b[0], b[1], P[i, 2]]]
    for i in range(len(P) - 1):
        k = 2 * i; I += [[k, k + 1, k + 3], [k, k + 3, k + 2]]
    V = np.array(V); I = np.array(I)
    fn = np.cross(V[I[:, 1]] - V[I[:, 0]], V[I[:, 2]] - V[I[:, 0]])
    if fn[:, 2].sum() < 0: I = I[:, ::-1]
    B.add(V, I, mat, tag=tag)

def block_box(B, loc, L, D, z0, h=3.0):
    """invisible blocker over a building's wall rectangle"""
    pts = [loc.w(u, v) for (u, v) in ((-L / 2, -D / 2), (L / 2, -D / 2), (L / 2, D / 2), (-L / 2, D / 2))]
    prim.prism(B, pts, z0 - 0.5, z0 + h, 'stone', tag='block')

def rect_of(ring):
    """minimum rotated rectangle of a local ring -> (cx, cy, length, width, yaw of the long side)"""
    from shapely.geometry import Polygon
    r = Polygon(ring).minimum_rotated_rectangle
    xs, ys = r.exterior.coords.xy
    e0 = np.array([xs[1] - xs[0], ys[1] - ys[0]]); e1 = np.array([xs[2] - xs[1], ys[2] - ys[1]])
    L0, L1 = np.linalg.norm(e0), np.linalg.norm(e1)
    d = e0 if L0 >= L1 else e1
    return r.centroid.x, r.centroid.y, max(L0, L1), min(L0, L1), math.atan2(d[1], d[0])

def zmin(gz, loc, L, D):
    return float(min(gz(*loc.w(u, v)) for u in (-L / 2, 0, L / 2) for v in (-D / 2, 0, D / 2)))

def H(B, gz, loc, L, D, block=True, zoff=-0.05, z0=None, **kw):
    """a hall in a Loc frame, standing on the lowest ground under it (or z0); blocked"""
    z0 = (zmin(gz, loc, L, D) + zoff) if z0 is None else z0
    ridge = kw.pop('ridge_h', None)
    if ridge is not None: kw['ridge'] = z0 + ridge
    info = hall(B, loc.cx, loc.cy, loc.yaw, z0, L, D, **kw)
    if block: block_box(B, loc, L + 0.4, D + 0.4, z0)
    info['z0'] = z0
    return info

# ------------------------------------------------------------------ walls (築地塀 / 筋塀 / white 塀), after the 永観堂 site
def wall(B, gz, pts, h=2.3, th=0.5, color=WHITE, stripes=0, lower=None, base_h=0.35, coping='kawara', step=1.8, tag='main', block=True):
    pts = [np.asarray(p, float) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; d = b - a; L = float(np.linalg.norm(d))
        if L < 0.2: continue
        d /= L; n = np.array([-d[1], d[0]])
        k = max(1, int(round(L / step)))
        for j in range(k):
            p = a + d * L * j / k; q = a + d * L * (j + 1) / k
            zz = float(min(gz(*p), gz(*q)))
            ztop = zz + h; ll = L / k
            for side in (-1, 1):
                A = p + n * side * th / 2; Bq = q + n * side * th / 2
                I = [[0, 1, 2], [0, 2, 3]] if side < 0 else [[0, 2, 1], [0, 3, 2]]
                Pz = np.array([np.r_[A, zz - 0.4], np.r_[Bq, zz - 0.4], np.r_[Bq, zz + base_h], np.r_[A, zz + base_h]])
                B.add(Pz, I, 'stone', UV=np.array([[0, 0], [ll, 0], [ll, base_h], [0, base_h]]), tag=tag)
                zl = zz + base_h
                if lower:
                    Pl = np.array([np.r_[A, zl], np.r_[Bq, zl], np.r_[Bq, zz + lower], np.r_[A, zz + lower]])
                    B.add(Pl, I, WD, UV=np.array([[0, 0], [ll, 0], [ll, lower], [0, lower]]), tag=tag)
                    zl = zz + lower
                Pw = np.array([np.r_[A, zl], np.r_[Bq, zl], np.r_[Bq, ztop], np.r_[A, ztop]])
                B.add(Pw, I, 'temple_wall', UV=np.array([[0, zl], [ll, zl], [ll, ztop], [0, ztop]]), tag=tag, c0=color)
                for s_ in range(stripes):
                    zs = ztop - 0.3 - 0.16 * s_
                    prim.obox(B, np.r_[p + n * side * (th / 2 + 0.006), zs], np.r_[q + n * side * (th / 2 + 0.006), zs], 0.012, 0.045, 'white_paint', tag='detail')
                A2 = p + n * side * (th / 2 + 0.28); B2 = q + n * side * (th / 2 + 0.28)
                P = np.array([np.r_[A2, ztop - 0.02], np.r_[B2, ztop - 0.02], np.r_[q, ztop + 0.36], np.r_[p, ztop + 0.36]])
                I2 = [[0, 1, 2], [0, 2, 3]] if side < 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I2, coping, UV=np.array([[0, 0], [ll, 0], [ll, 0.5], [0, 0.5]]), tag=tag)
                Pu = np.array([np.r_[A, ztop], np.r_[Bq, ztop], np.r_[B2, ztop - 0.03], np.r_[A2, ztop - 0.03]])
                U.oadd(B, Pu, [[0, 1, 2], [0, 2, 3]], WD, (0, 0, -1), tag=tag)
                prim.obox(B, np.r_[A2, ztop - 0.02], np.r_[B2, ztop - 0.02], 0.05, 0.12, coping, tag='detail')
            prim.obox(B, np.r_[p - d * 0.02, ztop + 0.42], np.r_[q + d * 0.02, ztop + 0.42], 0.24, 0.16, 'ridge', tag=tag)
        for e, pe in ((0, a), (1, b)):
            if (e == 0 and i > 0) or (e == 1 and i < len(pts) - 2): continue
            zz = float(gz(*pe)); sgn = -1 if e == 0 else 1
            A = pe + n * th / 2; Bq = pe - n * th / 2
            P = np.array([np.r_[A, zz - 0.4], np.r_[Bq, zz - 0.4], np.r_[Bq, zz + h], np.r_[A, zz + h]])
            U.oadd(B, P, [[0, 1, 2], [0, 2, 3]], 'temple_wall', (d[0] * sgn, d[1] * sgn, 0), tag=tag, c0=color)
        if block:
            zb = float(gz(*((a + b) / 2)))
            ribbon(B, [a, b], max(0.6, th + 0.1), 'block', z=zb + 1.0)

# ------------------------------------------------------------------ 向唐門 (after the 永観堂 site's karamon)
def karamon(B, gz, loc, span=2.9, depth=2.4, Hh=3.3, r=0.17, W=5.0, Dr=4.6, hump=1.25, mat=WD, cover='hiwada'):
    with loc.frame(B):
        zg = min(gz(*loc.w(u, v)) for u in (-2, 2) for v in (-2, 2))
        prim.box(B, -span / 2 - 1.0, -depth / 2 - 1.2, zg - 0.4, span / 2 + 1.0, depth / 2 + 1.2, zg + 0.16, 'stone')
        z0 = zg + 0.16
        for sx in (-1, 1):
            for sv in (-1, 1):
                x, v = sx * span / 2, sv * depth / 2
                prim.box(B, x - r * 1.5, v - r * 1.5, z0 - 0.02, x + r * 1.5, v + r * 1.5, z0 + 0.12, 'stone')
                prim.box(B, x - r, v - r, z0 + 0.1, x + r, v + r, z0 + Hh, mat)
                arch.kumimono(B, x, v, z0 + Hh, (0, sv), (1, 0), 'demitsudo', 0.6, mat, mat)
            prim.box(B, sx * span / 2 - r * 0.8, -r * 0.8, z0, sx * span / 2 + r * 0.8, r * 0.8, z0 + Hh - 0.5, mat)
            prim.obox(B, (sx * span / 2, -depth / 2, z0 + Hh - 0.75), (sx * span / 2, depth / 2, z0 + Hh - 0.75), 0.14, 0.28, mat)
        for sv in (-1, 1):
            prim.obox(B, (-span / 2 - 0.35, sv * depth / 2, z0 + Hh - 0.28), (span / 2 + 0.35, sv * depth / 2, z0 + Hh - 0.28), 0.2, 0.44, mat)
        dw = span / 2 - r * 0.8
        for sx in (-1, 1):                                   # doors (closed): boards, lattice upper panel
            x0, x1 = sorted((0.0, sx * dw))
            prim.box(B, x0 + 0.01, -0.06, z0 + 0.05, x1 - 0.01, 0.06, z0 + Hh - 0.55, mat)
            for xx in np.linspace(x0 + 0.16, x1 - 0.16, 6):
                prim.box(B, xx - 0.018, -0.1, z0 + Hh - 1.6, xx + 0.018, -0.07, z0 + Hh - 0.75, mat, tag='detail')
            for zz in np.linspace(z0 + 0.45, z0 + Hh - 1.7, 4):
                prim.box(B, x0 + 0.05, -0.1, zz - 0.04, x1 - 0.05, -0.06, zz + 0.04, 'metal_dark', tag='detail')
        zc = z0 + Hh + 0.62
        def zf_(u):
            t = min(abs(u) / (W / 2), 1.0)
            return zc + hump * (0.5 + 0.5 * math.cos(math.pi * t)) + 0.16 * max(0.0, (t - 0.8) / 0.2) ** 2
        us_ = np.linspace(-W / 2, W / 2, 33); vs_ = np.linspace(-Dr / 2, Dr / 2, 9)
        P = np.array([(u, v, zf_(u)) for v in vs_ for u in us_]); nu_ = len(us_) - 1
        I = []
        for j in range(len(vs_) - 1):
            for i in range(nu_):
                a_ = j * (nu_ + 1) + i; I += [[a_, a_ + nu_ + 2, a_ + 1], [a_, a_ + nu_ + 1, a_ + nu_ + 2]]
        I = np.array(I)
        fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
        if fn[:, 2].sum() < 0: I = I[:, ::-1]
        B.add(P, I, jroof.COVER_MAT[cover], UV=P[:, [0, 1]], smooth=True)
        S2 = P.copy(); S2[:, 2] -= 0.4
        B.add(S2, I[:, ::-1], 'eave_wood', UV=P[:, [0, 1]], smooth=True)
        for sv in (-1, 1):
            v = sv * Dr / 2
            top = np.array([(u, v, zf_(u)) for u in us_]); mid = top - [0, 0, 0.22]; bot = top - [0, 0, 0.4]
            for (A_, B_, m) in ((top, mid, jroof.COVER_MAT[cover]), (mid, bot, mat)):
                Pq = np.concatenate([A_, B_]); Iq = []
                for i in range(nu_): Iq += [[i, i + nu_ + 1, i + 1], [i + 1, i + nu_ + 1, i + nu_ + 2]]
                Iq = np.array(Iq)
                fn = np.cross(Pq[Iq[:, 1]] - Pq[Iq[:, 0]], Pq[Iq[:, 2]] - Pq[Iq[:, 0]])
                if (fn[:, 1].sum() * sv) < 0: Iq = Iq[:, ::-1]
                B.add(Pq, Iq, m)
            pts = np.array([(u, v - sv * 0.12, zf_(u) - 0.44) for u in us_])
            prim.sweep(B, pts, [(-0.07, -0.42), (0.07, -0.42), (0.07, 0.0), (-0.07, 0.0)], mat, up=(0, 1, 0))
            gp = [(-0.6, 0.0), (0.6, 0.0), (0.4, -0.45), (0.0, -0.68), (-0.4, -0.45)]
            Pg = np.array([(x, v - sv * 0.1, zc + hump - 0.45 + z) for (x, z) in gp]); Ig = [[0, 1, 2], [0, 2, 3], [0, 3, 4]]
            B.add(Pg, Ig, mat, tag='detail'); B.add(Pg, [t[::-1] for t in Ig], mat, tag='detail')
        for su in (-1, 1):
            u = su * W / 2
            prim.sweep(B, np.array([(u, v, zf_(u) - 0.08) for v in vs_]), [(-0.05, -0.32), (0.05, -0.32), (0.05, 0.0), (-0.05, 0.0)], mat, up=(1, 0, 0))
        for v in np.arange(-Dr / 2 + 0.2, Dr / 2 - 0.1, 0.24):
            for su in (-1, 1):
                prim.obox(B, (su * (W / 2 - 0.05), v, zf_(W / 2) - 0.47), (su * (span / 2 + 0.1), v, zf_(span / 2 + 0.1) - 0.52), 0.06, 0.08, mat, tag='detail')
        zt = zf_(0.0)
        prim.box(B, -0.22, -Dr / 2 + 0.25, zt - 0.1, 0.22, Dr / 2 - 0.25, zt + 0.42, 'ridge')
        prim.box(B, -0.26, -Dr / 2 + 0.25, zt + 0.42, 0.26, Dr / 2 - 0.25, zt + 0.52, 'ridge')
        for sv in (-1, 1):                                   # 鬼板 with a crest of three knobs (the photo's crown)
            v = sv * (Dr / 2 - 0.25)
            P2 = np.array([(-0.42, v, zt - 0.1), (0.42, v, zt - 0.1), (0.42, v, zt + 0.5), (0.22, v, zt + 0.86), (-0.22, v, zt + 0.86), (-0.42, v, zt + 0.5)])
            U.oadd(B, P2, [[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5]], 'ridge', (0, sv, 0), c1=(0, 1, 0, 0))
            for (x, z) in ((-0.32, 0.66), (0.0, 0.94), (0.32, 0.66)):
                prim.cyl(B, (x, v - sv * 0.02, zt + z), (x, v + sv * 0.08, zt + z), 0.1, 0.1, 10, 'ridge', tag='detail')
        ribbon(B, [(-span / 2, -depth / 2 - 0.5), (-span / 2, depth / 2 + 0.5)], 0.6, 'block', z=z0 + 1)
        ribbon(B, [(span / 2, -depth / 2 - 0.5), (span / 2, depth / 2 + 0.5)], 0.6, 'block', z=z0 + 1)
        ribbon(B, [(-span / 2, 0), (span / 2, 0)], 0.6, 'block', z=z0 + 1)
    return zg

# ------------------------------------------------------------------ 薬医門 (総門), after the 永観堂 site's gate
def yakuimon(B, gz, loc, span=3.6, depth=2.2, Hh=3.4, r=0.26, roof_L=7.2, roof_D=5.2, pitch=0.62, cover='hongawara', doors='open'):
    """main pillars on v = 0 (the front line), back pillars at v = +depth, a 切妻 roof with the ridge along u"""
    with loc.frame(B):
        zg = min(gz(*loc.w(u, v)) for u in (-span / 2, span / 2) for v in (0, depth))
        back_r = r * 0.72
        ze = zg + Hh + 0.75
        for sx in (-1, 1):
            x = sx * span / 2
            for (v, rr) in ((0.0, r), (depth, back_r)):
                prim.box(B, x - rr * 1.45, v - rr * 1.45, zg - 0.2, x + rr * 1.45, v + rr * 1.45, zg + 0.12, 'stone')
                prim.box(B, x - rr, v - rr, zg + 0.1, x + rr, v + rr, zg + Hh + 0.2, WD)
                if v == 0.0: prim.box(B, x - rr - 0.02, v - rr - 0.02, zg + 0.1, x + rr + 0.02, v + rr + 0.02, zg + 0.4, 'metal_dark', tag='detail')
            prim.obox(B, (x, -0.2, zg + Hh * 0.45), (x, depth + 0.2, zg + Hh * 0.45), 0.12, 0.26, WD)
        Lw = span + 2 * r + 0.3
        vo = max(0.3, (roof_L - Lw) / 2)
        o = (roof_D - depth) / 2
        R = jroof.Roof(Lw, depth, ze, o, kind='kirizuma', cover=cover, pitch=pitch, verge=vo, rafter=0.28, rafter_mat=WD,
                       rafter_end='white_paint', gable_wall=WD, ends='oni', sori=0.0)
        under = lambda s_: float(R.z(s_, R.a)) - R.edge - 0.12
        with Frame(B, 0, depth / 2, 0, 0):
            R.build(B)
        kab = 0.5
        prim.obox(B, (-span / 2 - 0.55, 0, zg + Hh - kab / 2), (span / 2 + 0.55, 0, zg + Hh - kab / 2), r * 1.1, kab, WD)
        prim.obox(B, (-span / 2 - 0.2, depth, zg + Hh - 0.3), (span / 2 + 0.2, depth, zg + Hh - 0.3), back_r * 1.1, 0.4, WD)
        s_p = 0.55; zp = under(s_p) - 0.12; zw = under(o) - 0.14
        for sx in (-1, 1):
            x = sx * span / 2
            for (v0, v1, sv) in ((-o + s_p - 0.25, 0.0, -1), (depth + o - s_p + 0.25, depth, 1)):
                prim.obox(B, (x, v0, zp - 0.2), (x, v1, zw - 0.2), 0.2, 0.26, WD)
                prim.obox(B, (x, v0, zp - 0.2), (x, v0 - sv * 0.03, zp - 0.2), 0.205, 0.265, 'white_paint', tag='detail')
            prim.obox(B, (x, 0.0, zw - 0.45), (x, depth, zw - 0.45), 0.18, 0.3, WD)
        for v in (-o + s_p, depth + o - s_p):
            prim.obox(B, (-roof_L / 2 + 0.7, v, zp), (roof_L / 2 - 0.7, v, zp), 0.2, 0.2, WD)
        zr_ = under(R.c) - 0.15
        prim.obox(B, (-roof_L / 2 + 0.6, depth / 2, zr_), (roof_L / 2 - 0.6, depth / 2, zr_), 0.22, 0.24, WD)
        for sx in (-1, 1):
            prim.obox(B, (sx * span / 2, depth / 2, zg + Hh - 0.1), (sx * span / 2, depth / 2, zr_), 0.18, 0.18, WD)
        prim.box(B, -0.4, -0.3, zg + Hh - 1.05, 0.4, -0.25, zg + Hh - 0.5, 'wood_natural')                        # 扁額
        dh = Hh - kab - 0.05; dw = span / 2 - r - 0.02
        for sx in (-1, 1):
            x = sx * (span / 2 - r - 0.06)
            prim.box(B, x - 0.05, 0.25, zg + 0.08, x + 0.05, 0.25 + dw, zg + dh, WD)
            for zz_ in np.linspace(zg + 0.5, zg + dh - 0.3, 4):
                prim.box(B, x - sx * 0.05 - 0.04, 0.3, zz_ - 0.05, x - sx * 0.05 + 0.04, 0.2 + dw, zz_ + 0.05, 'metal_dark', tag='detail')
        prim.polygon(B, [(-span / 2 + r, -roof_D / 2 + depth / 2), (span / 2 - r, -roof_D / 2 + depth / 2), (span / 2 - r, roof_D / 2 + depth / 2), (-span / 2 + r, roof_D / 2 + depth / 2)], zg + 0.04, 'stone', tag='walk')
        prim.box(B, -span / 2 + r, -0.3, zg - 0.3, span / 2 - r, depth + 0.3, zg + 0.04, 'stone')
        for sx in (-1, 1):
            ribbon(B, [(sx * span / 2, -0.3), (sx * span / 2, depth + 0.3)], 0.7, 'block', z=zg + 1)
    return zg

# ------------------------------------------------------------------ 鐘楼: tall battered stone base, four pillars, 入母屋 tiles, the bell
def shoro(B, gz, loc, L=3.3, D=3.0, Hh=3.6, base=1.25):
    with loc.frame(B):
        zg = min(gz(*loc.w(u, v)) for u in (-2.5, 2.5) for v in (-2.5, 2.5))
        a, c = L / 2 + 0.9, D / 2 + 0.9
        P = np.array([(-a - 0.3, -c - 0.3, zg - 0.3), (a + 0.3, -c - 0.3, zg - 0.3), (a + 0.3, c + 0.3, zg - 0.3), (-a - 0.3, c + 0.3, zg - 0.3),
                      (-a, -c, zg + base), (a, -c, zg + base), (a, c, zg + base), (-a, c, zg + base)])
        for k in range(4):
            j = (k + 1) % 4
            U.oadd(B, P[[k, j, j + 4, k + 4]], [[0, 1, 2], [0, 2, 3]], 'stone', (*(P[k, :2] + P[j, :2]) / 2, 0))
        prim.polygon(B, [(-a, -c), (a, -c), (a, c), (-a, c)], zg + base, 'stone')
        for k in range(int(2 * a / 0.9)):                    # stone courses
            x = -a + 0.45 + k * 0.9
            for (y, sv) in ((-c - 0.15, -1), (c + 0.15, 1)):
                prim.box(B, x - 0.43, y - 0.01, zg + base * 0.5 - 0.02, x + 0.43, y + 0.01, zg + base * 0.5 + 0.02, 'curb', tag='detail')
        z0 = zg + base
        for sx in (-1, 1):
            for sv in (-1, 1):
                prim.cyl(B, (sx * (L / 2 + 0.12), sv * (D / 2 + 0.12), z0), (sx * L / 2, sv * D / 2, z0 + Hh), 0.17, 0.15, 10, WD)
                prim.cyl(B, (sx * (L / 2 + 0.12), sv * (D / 2 + 0.12), z0 - 0.02), (sx * (L / 2 + 0.12), sv * (D / 2 + 0.12), z0 + 0.14), 0.27, 0.25, 8, 'stone')
        for zz in (z0 + 0.45, z0 + Hh * 0.62):
            arch.ring_beam(B, L + 0.18, D + 0.18, zz, 0.11, 0.18, WD)
        arch.ring_beam(B, L, D, z0 + Hh, 0.18, 0.28, WD)
        top, reach = arch.bracket_row(B, L, D, z0 + Hh, 'demitsudo', 0.62, WD, 'white_paint')
        jroof.roof(B, L + 2 * reach, D + 2 * reach, top + 0.3, 1.45, kind='irimoya', cover='hongawara', pitch=0.78, teri=1.5, sori=0.45,
                   rafter=0.26, tiers=2, rafter_mat=WD, rafter_end='white_paint', ends='oni', verge=0.7)
        prim.obox(B, (-L / 2, 0, z0 + Hh - 0.3), (L / 2, 0, z0 + Hh - 0.3), 0.18, 0.28, WD)
        zb = z0 + Hh - 0.45
        prim.lathe(B, (0, 0, zb - 1.45), [(0.56, 0.0), (0.54, 0.08), (0.5, 0.4), (0.47, 1.12), (0.38, 1.32), (0.14, 1.4), (0.0, 1.42)], 16, 'bronze')
        prim.obox(B, (-1.3, 0.0, zb - 0.95), (-0.62, 0.0, zb - 0.95), 0.15, 0.15, 'wood_natural', tag='detail')
        prim.prism(B, [(-a, -c), (a, -c), (a, c), (-a, c)], zg - 0.3, zg + base + 1.0, 'stone', tag='block')
    return zg

# ------------------------------------------------------------------ 向拝: a lean-to porch roof in front of a hall
def kohai(B, x0, x1, v_wall, z_top, depth, drop, zg, cover='hongawara', posts=True):
    """the hall frame: a shed roof from (v_wall, z_top) out to (v_wall - depth, z_top - drop), u from x0 to x1, slightly
    concave, tiles on top, boards under; two posts with a 虹梁 at the front"""
    mat = jroof.COVER_MAT[cover]
    us = np.linspace(x0, x1, 18); ts = np.linspace(0, 1, 8)
    P = np.array([(u, v_wall - depth * t, z_top - drop * (t ** 1.3)) for t in ts for u in us]); nu = len(us)
    I = []
    for j in range(len(ts) - 1):
        for i in range(nu - 1):
            a = j * nu + i; I += [[a, a + 1, a + nu + 1], [a, a + nu + 1, a + nu]]
    U.oadd(B, P, I, mat, (0, -0.3, 1), UV=P[:, [0, 1]])
    Ps = P.copy(); Ps[:, 2] -= 0.3
    U.oadd(B, Ps, I, 'eave_wood', (0, 0, -1), UV=P[:, [0, 1]])
    e = P[-nu:]
    U.oadd(B, np.r_[e, e - [0, 0, 0.32]], [[i, i + 1, i + nu + 1] for i in range(nu - 1)] + [[i, i + nu + 1, i + nu] for i in range(nu - 1)], WD, (0, -1, 0))
    if cover == 'hongawara':
        for u in np.arange(x0 + 0.15, x1, 0.3):
            prim.cyl(B, (u, v_wall - depth + 0.2, z_top - drop + 0.05), (u, v_wall - depth - 0.03, z_top - drop - 0.02), 0.085, None, 8, mat, caps=(False, True), tag='detail')
    for su in (x0, x1):
        prim.sweep(B, np.array([(su, v_wall - depth * t, z_top - drop * t ** 1.3 + 0.03) for t in ts]), [(-0.12, -0.2), (0.12, -0.2), (0.12, 0.06), (-0.12, 0.06)], mat, up=(0, 0, 1), caps=True)
    if posts:
        pv = v_wall - depth + 0.7
        zt = z_top - drop * ((depth - 0.7) / depth) ** 1.3 - 0.45
        for su in (x0 + 0.6, x1 - 0.6):
            prim.box(B, su - 0.13, pv - 0.13, zg, su + 0.13, pv + 0.13, zt, WD)
            prim.box(B, su - 0.2, pv - 0.2, zg - 0.05, su + 0.2, pv + 0.2, zg + 0.12, 'stone')
            prim.obox(B, (su, pv, zt - 0.2), (su, v_wall, zt + 0.2), 0.12, 0.22, WD)            # 海老虹梁
        prim.obox(B, (x0 + 0.4, pv, zt - 0.25), (x1 - 0.4, pv, zt - 0.25), 0.18, 0.4, WD)       # 虹梁

# ------------------------------------------------------------------ the 庫裏: a tall 切妻 with its gable to the south, white plaster + dark grid, an 入母屋 porch
def kuri(B, gz, loc, L=22.0, D=26.0, wall_h=6.4, pitch=0.62):
    """loc: u east, v north; the gable faces south (v-).  The ridge runs along v: built in a frame rotated 90 deg"""
    z0 = zmin(gz, loc, L, D) - 0.05
    # body: walls under a 切妻 whose ridge runs N-S -> a Loc rotated so its u runs north
    with loc.frame(B):
        a, c = L / 2, D / 2
        prim.prism(B, [(-a - 0.2, -c - 0.2), (a + 0.2, -c - 0.2), (a + 0.2, c + 0.2), (-a - 0.2, c + 0.2)], z0 - 0.3, z0 + 0.3, 'stone')
        # walls: dark lower boards with lattice windows, white upper plaster, a grid of dark posts and beams
        for (p, q, n) in ((( -a, -c), (a, -c), (0, -1)), ((a, -c), (a, c), (1, 0)), ((a, c), (-a, c), (0, 1)), ((-a, c), (-a, -c), (-1, 0))):
            bay = U.Bay(B, p, q, n); Lb = bay.L
            nb = max(1, int(round(Lb / 1.82)))
            bay.plane(0, Lb, z0 + 0.3, z0 + 1.2, WD, off=-0.02)
            bay.plaster(0, Lb, z0 + 1.2, z0 + wall_h, off=-0.03)
            for k in range(nb + 1):
                s = Lb * k / nb
                bay.box(s - 0.12, s + 0.12, z0 + 0.3, z0 + wall_h, -0.06, 0.06, WD)
            for zz in (z0 + 1.2, z0 + 2.3, z0 + 3.1, z0 + 4.6, z0 + wall_h - 0.2):
                bay.box(-0.12, Lb + 0.12, zz - 0.09, zz + 0.09, -0.07, 0.07, WD)
            for k in range(nb):
                s0 = Lb * k / nb + 0.15; s1 = Lb * (k + 1) / nb - 0.15
                if k % 3 == 1: bay.koshi(s0, s1, z0 + 3.35, z0 + 4.4, off=-0.02, step=0.13)
                elif k % 3 == 0 and (n[1] < 0): bay.mairado(s0, s1, z0 + 0.4, z0 + 2.2, 2, off=-0.02)
                elif k % 4 == 2: bay.koshi(s0, s1, z0 + 1.4, z0 + 2.2, off=-0.02, step=0.1)
    roofloc = Loc(loc.cx, loc.cy, loc.yaw + math.pi / 2)        # u north, v west
    with roofloc.frame(B):
        o = 1.25
        info = jroof.roof(B, D, L, z0 + wall_h + 0.25, o, kind='kirizuma', cover='sangawara', pitch=pitch, teri=1.12, sori=0.0, rafter=0.0,
                          ends='oni', verge=1.1, edge=0.3, bargeboard_mat=WD, gable_wall='temple_wall')
        # the south gable (u = -D/2): dark timber grid on the white plaster, a big 懸魚
        zr = info['z_ridge']; zE = z0 + wall_h
        u = -D / 2 - 0.05
        c_ = L / 2 + o
        for v in np.linspace(-L / 2 + 1.8, L / 2 - 1.8, 9):
            ztop = zE + (zr - zE) * max(0.0, 1 - abs(v) / c_) - 0.45
            if ztop > zE + 0.3: prim.obox(B, (u, v, zE), (u, v, ztop), 0.16, 0.14, WD)
        for (zz, half) in ((zE + 0.3, L / 2), (zE + 1.6, None), (zE + 2.9, None), (zE + 4.1, None)):
            hw = half if half else max(0.0, c_ * (1 - (zz - zE + 0.5) / (zr - zE)) - 0.4)
            if hw > 0.5: prim.obox(B, (u, -hw, zz), (u, hw, zz), 0.2, 0.22, WD)
        for v_, h_ in ((-3.0, 1.1), (3.0, 1.1), (0.0, 1.4)):
            prim.box(B, u - 0.12, v_ - 0.5, zE + 1.75, u - 0.05, v_ + 0.5, zE + 1.75 + h_, 'glass')
            for k in range(6):
                vv = v_ - 0.42 + k * 0.17
                prim.box(B, u - 0.16, vv - 0.025, zE + 1.75, u - 0.1, vv + 0.025, zE + 1.75 + h_, WD, tag='detail')
    block_box(B, loc, L + 0.4, D + 0.4, z0)
    return z0, info

# ------------------------------------------------------------------ 夕佳亭: thatched 寄棟 tea room (三畳 + 勝手 + 土間) and the shingled 鳳棲楼 wing
def sekkatei(B, gz, loc, L=6.2, D=4.3, wing=3.6):
    """loc: u along the long axis, the front (v-) faces the Kinkaku (south-west).  Main block u in [-L/2, L/2] - wing/2"""
    z0 = zmin(gz, loc, L + wing, D) - 0.05
    um = -wing / 2
    with loc.frame(B):
        a, c = L / 2, D / 2
        prim.prism(B, [(um - a - 0.3, -c - 0.6), (um + a + wing, -c - 0.6), (um + a + wing, c + 0.3), (um - a - 0.3, c + 0.3)], z0 - 0.4, z0 + 0.25, 'stone')
        with Frame(B, um, 0, z0, 0):
            FL = 0.55; NG = FL + 1.72; PL = FL + 2.2
            for (x, y) in [(x, y) for x in (-a, -a / 3, a / 3, a) for y in (-c, c)] + [(-a, 0), (a, 0)]:
                prim.box(B, x - 0.06, y - 0.06, 0.25, x + 0.06, y + 0.06, PL + 0.15, 'wood_natural')
            prim.polygon(B, [(-a, -c), (a, -c), (a, c), (-a, c)], FL, 'tatami')
            prim.box(B, -a, -c - 0.05, 0.25, a, c, FL - 0.02, WD)
            faces = [((-a, -c), (a, -c), (0, -1)), ((a, -c), (a, c), (1, 0)), ((a, c), (-a, c), (0, 1)), ((-a, c), (-a, -c), (-1, 0))]
            for k, (p, q, n) in enumerate(faces):
                bay = U.Bay(B, p, q, n); Lb = bay.L
                tint = (196, 170, 120)                                                       # 聚楽 earth wall
                if k == 0:
                    # front: a bamboo-lattice band over an open bay (the 床 inside), plank shutters at the left
                    bay.plane(0.06, Lb / 3, FL, PL, 'wood_natural', off=-0.03)
                    for zz in np.arange(FL + 0.3, PL, 0.42): bay.box(0.06, Lb / 3, zz, zz + 0.02, -0.01, 0.02, 'bamboo', tag='detail')
                    bay.plane(Lb / 3, Lb - 0.06, FL + 1.25, PL, 'temple_wall', off=-0.4, c0=(*tint, 35))
                    for s in np.arange(Lb / 3 + 0.08, Lb - 0.06, 0.12):
                        bay.box(s - 0.012, s + 0.012, NG - 0.05, PL - 0.1, -0.02, 0.02, 'bamboo', tag='detail')
                    bay.box(Lb / 3, Lb - 0.06, NG - 0.08, NG, -0.03, 0.03, 'wood_natural')
                    bay.plane(Lb / 3, Lb - 0.06, FL, NG - 0.08, 'glass', off=-1.6)
                    bay.plane(Lb * 0.62, Lb * 0.72, FL + 0.2, NG - 0.2, 'white_paint', off=-1.55)       # the hanging scroll
                else:
                    bay.plane(0.06, Lb - 0.06, FL - 0.3, PL, 'temple_wall', off=-0.03, c0=(*tint, 35))
                    if k == 2: bay.shoji(Lb * 0.55, Lb * 0.85, FL + 0.5, NG, 2, off=-0.02, frame='wood_natural')
                    else: bay.koshi(Lb * 0.3, Lb * 0.55, FL + 0.7, NG - 0.2, off=-0.02, mat='bamboo', step=0.07)
                bay.box(-0.06, Lb + 0.06, PL - 0.08, PL + 0.08, -0.05, 0.05, 'wood_natural')
            # thatched 寄棟 roof: thick, softly rounded eaves
            jroof.roof(B, L + 0.2, D + 0.2, PL + 0.85, 0.95, kind='yosemune', cover='thatch', pitch=1.1, teri=1.05, sori=0.05, sori_len=0.3,
                       edge=0.6, rafter=0.0, ends=None, hip=False, ridge_h=0.55, ridge_w=0.8)
        # the 鳳棲楼 wing: lower, 切妻, 杮葺, raised floor
        with Frame(B, um + a + wing / 2, 0.2, z0, 0):
            w2, d2 = wing - 0.2, D - 0.8
            for (x, y) in ((-w2 / 2, -d2 / 2), (w2 / 2, -d2 / 2), (w2 / 2, d2 / 2), (-w2 / 2, d2 / 2)):
                prim.box(B, x - 0.06, y - 0.06, 0.25, x + 0.06, y + 0.06, 2.45, 'wood_natural')
            for (p, q, n) in (((-w2 / 2, -d2 / 2), (w2 / 2, -d2 / 2), (0, -1)), ((w2 / 2, -d2 / 2), (w2 / 2, d2 / 2), (1, 0)), ((w2 / 2, d2 / 2), (-w2 / 2, d2 / 2), (0, 1))):
                bay = U.Bay(B, p, q, n)
                bay.plane(0.06, bay.L - 0.06, 0.25, 2.4, 'temple_wall', off=-0.03, c0=(196, 170, 120, 35))
                if n[1] < 0: bay.shoji(0.3, bay.L - 0.3, 0.75, 2.1, 2, off=-0.02, frame='wood_natural')
            jroof.roof(B, w2, d2, 2.75, 0.6, kind='kirizuma', cover='kokera', pitch=0.5, teri=1.2, sori=0.0, rafter=0.3, tiers=1,
                       rafter_mat='wood_natural', rafter_end='wood_natural', ends=None, verge=0.4, edge=0.18, bargeboard_mat='wood_natural', gable_wall='temple_wall')
    block_box(B, loc, L + wing + 0.6, D + 0.6, z0)
    return z0

# ------------------------------------------------------------------ simple buildings from a footprint ring (roof outline)
def simple(B, gz, ring, h_ridge=7.0, wall=3.0, cover='sangawara', o=0.9, kind=None, seed=0, floor=0.45, inset=None, detail=False, front=None, z0=None):
    cx, cy, L, Wd, yaw = rect_of(ring)
    ins = o * 0.85 if inset is None else inset
    L = max(2.0, L - 2 * ins); Wd = max(2.0, Wd - 2 * ins)
    if front is not None:                               # turn the frame so its front (v-) faces `front` (radians)
        yaw = front + math.pi / 2
        if abs(math.cos(yaw - rect_of(ring)[4])) < 0.7: L, Wd = Wd, L
    loc = Loc(cx, cy, yaw)
    kind = kind or ('irimoya' if L > 7 else 'kirizuma')
    nb = (max(1, int(round(L / 1.8))), max(1, int(round(Wd / 1.8))))
    pat = ['plaster', 'mairado', 'plaster', 'shoji', 'plaster', 'koshi']
    def fit(k, i):
        if k in (0, 2): return pat[(i + seed + k) % len(pat)]
        return 'plaster' if (i + seed) % 3 else 'mairado'
    return H(B, gz, loc, L, Wd, z0=z0, nb=nb, fit=fit, floor=floor, wall=wall, nage=1.8, roof=kind, cover=cover, o=o, ridge_h=h_ridge,
             teri=1.25, rafter=0 if not detail else 0.45, tiers=1, sori=0.05, funa=False, detail=False, verge=0.5, ends='oni')

def corridor(B, gz, a, b, w=2.2, h=2.6, cover='sangawara', walls=True, z=None):
    """渡廊下 between two buildings: floor, posts, white walls, a small gable roof"""
    a = np.asarray(a, float); b = np.asarray(b, float); d = b - a; Lc = float(np.linalg.norm(d)); yaw = math.atan2(d[1], d[0])
    c = (a + b) / 2
    zf = (z if z is not None else float(min(gz(*a), gz(*b)))) + 0.45
    with Frame(B, c[0], c[1], zf, yaw):
        prim.box(B, -Lc / 2, -w / 2, -0.6, Lc / 2, w / 2, 0.0, 'eave_wood')
        for x in np.linspace(-Lc / 2 + 0.1, Lc / 2 - 0.1, max(2, int(Lc / 1.8)) + 1):
            for s in (-1, 1):
                prim.box(B, x - 0.08, s * (w / 2 - 0.08) - 0.08, -0.6, x + 0.08, s * (w / 2 - 0.08) + 0.08, h, WD)
        for s in (-1, 1):
            prim.box(B, -Lc / 2, s * (w / 2 - 0.08) - 0.1, h, Lc / 2, s * (w / 2 - 0.08) + 0.1, h + 0.18, WD)
            if walls:
                bay = U.Bay(B, (-Lc / 2, s * (w / 2 - 0.08)), (Lc / 2, s * (w / 2 - 0.08)), (0, s))
                bay.plaster(0.1, Lc - 0.1, 0.9, h, off=-0.02)
                bay.plane(0.1, Lc - 0.1, 0.0, 0.9, WD, off=-0.02)
        jroof.roof(B, Lc, w, h + 0.2, 0.6, kind='kirizuma', cover=cover, pitch=0.62, teri=1.2, sori=0.0, rafter=0.0, ends='oni', verge=0.1, edge=0.25, bargeboard_mat=WD)

# ------------------------------------------------------------------ the placements
def build(B, S, gz, ring, line, terr):
    """ring(osm id) -> local footprint; line(cat, id) -> local polyline; terr: {osm id: terrace level} for buildings on slopes"""
    import shapely
    from shapely.geometry import Polygon
    # 方丈 (1678): 入母屋 桟瓦, veranda on the south and west, white rafter ends; joined to the 庫裏 on the east
    hoj = {0: ['mairado', 'shoji', 'mairado', 'shoji_open', 'shoji', 'mairado', 'shoji', 'mairado'], 1: ['plaster', 'mairado', 'plaster', 'plaster', 'plaster'],
           2: ['plaster', 'mairado', 'plaster', 'shoji', 'plaster', 'mairado', 'plaster', 'plaster'], 3: ['shoji', 'mairado', 'shoji', 'mairado', 'shoji']}
    H(B, gz, Loc(60.4, -17.6, 0.0), 20.9, 13.2, nb=(8, 5), fit=lambda k, i: hoj[k][i % len(hoj[k])], floor=0.8, wall=3.3, nage=1.95, ver=(0, 3, 2), ver_w=1.2,
      roof='irimoya', cover='sangawara', o=1.75, ridge_h=10.6, teri=1.4, rafter=0.42, tiers=1, sori=0.3, sori_len=0.6, rafter_end='white_paint')
    corridor(B, gz, (68.3, -27.4), (68.3, -33.2), w=3.0, h=2.7)
    # 書院 (大書院): 入母屋 桟瓦 north of the 方丈, a lower wing to its south; the connecting corridors
    sho = lambda k, i: ['shoji', 'mairado', 'plaster', 'shoji', 'plaster', 'mairado'][(i + k) % 6]
    H(B, gz, Loc(58.75, 3.65, 0.0), 24.1, 7.3, nb=(10, 3), fit=sho, floor=0.75, wall=3.1, ver=(0, 3), ver_w=1.0, roof='irimoya', cover='sangawara',
      o=1.4, ridge_h=8.3, teri=1.35, rafter=0.0, sori=0.2)
    H(B, gz, Loc(63.9, -3.6, 0.0), 15.0, 3.4, nb=(6, 1), fit=sho, floor=0.75, wall=2.8, roof='kirizuma', cover='sangawara', o=0.75, ridge_h=5.6, teri=1.2,
      rafter=0.0, sori=0.0, funa=False, verge=0.4)
    corridor(B, gz, (58.7, -9.6), (58.7, -5.0), w=3.2, h=2.8)
    corridor(B, gz, (69.5, -9.7), (69.5, -6.2), w=2.4, h=2.8)
    # 庫裏 (明応・文亀): the tall gable to the south, its 入母屋 porch (玄関) at the south-west
    kz0, _ = kuri(B, gz, Loc(84.4, -12.5, 0.0), L=21.8, D=26.0, wall_h=6.4)
    por = {0: ['koshi', 'karado', 'koshi'], 1: ['plaster', 'plaster'], 2: ['plaster', 'plaster', 'plaster'], 3: ['plaster', 'plaster']}
    H(B, gz, Loc(79.95, -28.3, math.pi / 2), 5.4, 6.9, z0=kz0, nb=(2, 3), fit=lambda k, i: {0: 'plaster', 1: ['koshi', 'karado', 'koshi'][i % 3], 2: 'plaster', 3: 'koshi'}[k],
      floor=0.35, wall=3.0, roof='irimoya', cover='sangawara', o=1.0, ridge_h=7.6, teri=1.3, rafter=0.35, sori=0.15, rafter_end='white_paint', gable_frac=0.55)
    # the annex behind the 庫裏 (345464006) and its north wing
    H(B, gz, Loc(84.4, 14.8, 0.0), 22.0, 21.4, z0=terr.get(345464006), nb=(8, 8), fit=lambda k, i: ['plaster', 'mairado', 'shoji', 'plaster'][(i + k) % 4], floor=0.6,
      wall=3.4, roof='irimoya', cover='sangawara', o=1.1, ridge_h=10.2, teri=1.3, rafter=0.0, sori=0.1)
    H(B, gz, Loc(86.5, 29.9, 0.0), 12.6, 5.2, z0=terr.get(345464006), nb=(5, 2), fit=lambda k, i: ['plaster', 'shoji'][(i + k) % 2], floor=0.6, wall=3.0,
      roof='kirizuma', cover='sangawara', o=0.6, ridge_h=6.2, teri=1.2, rafter=0.0, sori=0.0, funa=False, verge=0.4)
    # 唐門: the 方丈's 向唐門, facing the path to the south, white walls with tiled copings either side
    karamon(B, gz, Loc(70.2, -38.4, 0.0))
    wall(B, gz, [(67.3, -38.4), (58.0, -38.4), (58.0, -28.0)], h=2.3, th=0.45, color=WHITE)
    wall(B, gz, [(73.1, -38.4), (74.0, -38.4)], h=2.3, th=0.45, color=WHITE)
    # 鐘楼
    shoro(B, gz, Loc(107.9, -59.8, 0.0))
    # 総門: a 薬医門 facing east at the corner of the 筋塀, the gatekeeper's lodge on its north side
    r_ = Polygon(ring(345428773))
    cx, cy, Lg, Wg, yaw_long = rect_of(ring(345428773))
    yaw = yaw_long if math.sin(yaw_long) > 0 else yaw_long + math.pi                  # u runs north
    lg = Loc(cx, cy, yaw)
    gate_c = lg.w(-3.6, -1.6)
    yakuimon(B, gz, Loc(gate_c[0], gate_c[1], yaw), span=4.0, depth=2.4, Hh=3.65, roof_L=8.0, roof_D=6.0, pitch=0.6)
    lodge = Loc(*lg.w(3.2, 0.0), yaw)
    H(B, gz, lodge, 5.2, 5.6, nb=(3, 3), fit=lambda k, i: {0: 'koshi', 1: 'plaster', 2: 'plaster', 3: 'plaster'}[k] if not (k == 0 and i == 1) else 'koshi',
      floor=0.4, wall=2.6, roof='kirizuma', cover='sangawara', o=0.7, ridge_h=5.4, teri=1.2, rafter=0.0, sori=0.0, funa=False, verge=0.5)
    # support buildings (simple, on their footprints): ticket booth, the temple offices, kitchens, stores, tea house, shops
    simple(B, gz, ring(345428780), h_ridge=4.0, wall=2.4, o=0.6, kind='irimoya', seed=1, floor=0.2)
    simple(B, gz, ring(347012942), h_ridge=4.2, wall=2.5, o=0.5, kind='kirizuma', seed=2)
    simple(B, gz, ring(347012940), h_ridge=4.2, wall=2.5, o=0.5, kind='kirizuma', seed=3)
    simple(B, gz, ring(347395053), h_ridge=3.6, wall=2.2, o=0.4, kind='kirizuma', seed=4)
    simple(B, gz, ring(346872601), h_ridge=3.8, wall=2.3, o=0.5, kind='kirizuma', seed=5)
    simple(B, gz, ring(347012945), h_ridge=4.4, wall=2.5, o=0.6, kind='kirizuma', seed=6)
    simple(B, gz, ring(188772168), h_ridge=6.0, wall=3.0, o=0.8, kind='kirizuma', seed=7)
    simple(B, gz, ring(188772166), h_ridge=6.2, wall=2.9, o=0.9, kind='irimoya', seed=8)
    for k, (wid, h) in enumerate(((188772161, 6.8), (188772167, 7.4), (188772160, 7.8), (188772162, 7.6), (188772163, 5.6), (188772169, 6.0), (188772172, 6.4))):
        if ring(wid): simple(B, gz, ring(wid), h_ridge=h, wall=3.1, o=0.9, seed=10 + k)
    for k, (wid, h, kind) in enumerate(((188772158, 6.4, 'irimoya'), (188772173, 5.8, 'kirizuma'), (180453977, 4.6, 'kirizuma'), (180453978, 7.2, 'irimoya'),
                                        (346927279, 4.0, 'kirizuma'), (345443495, 4.4, 'kirizuma'), (345432675, 3.4, 'kirizuma'), (346922055, 3.6, 'kirizuma'),
                                        (552862313, 4.2, 'kirizuma'))):
        if ring(wid): simple(B, gz, ring(wid), h_ridge=h, wall=2.8, o=0.8 if h > 5 else 0.5, kind=kind, seed=30 + k, z0=terr.get(wid))
    # walls: the 筋塀 of the 総門's forecourt and towards the 庫裏, white walls round the 方丈 garden and the 書院, the precinct's outer wall
    for wid in (346872589, 346872591, 347012909):
        L = line('barriers', wid)
        if L is not None: wall(B, gz, L, h=2.5, th=0.6, color=OCHRE, stripes=5)
    for wid in (347012913, 347012911, 347012915, 347401917, 844133783):
        L = line('barriers', wid)
        if L is not None: wall(B, gz, L, h=2.2, th=0.42, color=WHITE)
    for wid in (347407424, 348438926):
        L = line('barriers', wid)
        if L is not None: wall(B, gz, L, h=1.6, th=0.4, color=OCHRE)
    L = line('barriers', 346573040)
    if L is not None: wall(B, gz, L, h=2.3, th=0.55, color=OCHRE, step=2.4)

    # 不動堂 (天正, 宇喜多秀家): 入母屋 本瓦 with a 向拝, facing south-south-east over its stone forecourt
    main = Polygon([(146.52, 85.13), (158.11, 80.87), (153.75, 69.12), (142.16, 73.4)])         # the hall's roof outline (OSM, less the 向拝)
    cx, cy = main.centroid.x, main.centroid.y
    front = math.radians(159.6)                                                                   # the 向拝 projects west-north-west
    zf = terr.get(337340500)
    Lh, Dh = 9.9, 9.8
    hl = Loc(cx, cy, front + math.pi / 2)
    # 妻入り: the 入母屋's gable faces the front, so the hall is built in a frame whose u runs toward the front (face 1 = front)
    fud = {1: ['koshi', 'karado', 'karado', 'koshi'], 0: ['board'] * 4, 2: ['board'] * 4, 3: ['board'] * 4}
    hg = Loc(cx, cy, front)
    info = H(B, gz, hg, Dh, Lh, z0=zf, nb=(4, 4), fit=lambda k, i: fud[k][i % 4], floor=0.9, wall=3.0, nage=2.0, ver=(1,), ver_w=1.2, roof='irimoya',
             cover='hongawara', o=1.3, ridge_h=9.4, teri=1.45, rafter=0.3, tiers=2, sori=0.45, sori_len=0.5, rafter_end='white_paint', gable_frac=0.5)
    with hl.frame(B):
        kohai(B, -2.9, 2.9, -Dh / 2 - 0.3, zf + info['z_edge'] - 0.1, 2.9, 0.75, zf)
        for sx in (-1, 1):                                     # stone lanterns, the incense burner, steps up to the veranda
            arch.ishidoro(B, sx * 3.6, -Dh / 2 - 5.2, zf, h=2.0)
            B.lamp(sx * 3.6, -Dh / 2 - 5.2, zf + 1.3, 4.0, (1.0, 0.62, 0.32))
            prim.box(B, sx * 3.6 - 0.35, -Dh / 2 - 5.55, zf - 0.3, sx * 3.6 + 0.35, -Dh / 2 - 4.85, zf + 1.6, 'stone', tag='block')
        prim.lathe(B, (0, -Dh / 2 - 4.2, zf), [(0.0, 0.0), (0.35, 0.0), (0.32, 0.4), (0.22, 0.45), (0.5, 0.6), (0.55, 0.9), (0.35, 1.0), (0.3, 1.3), (0.12, 1.45), (0.0, 1.6)], 12, 'bronze')
        arch.stairs(B, (0, -Dh / 2 - 2.0), (0, -Dh / 2 - 1.2), zf, zf + 0.82, 2.4, mat='stone')
        for sx in (-1, 1):                                     # the red paper lanterns hanging in the 向拝
            arch.chochin(B, sx * 1.3, -Dh / 2 - 1.6, zf + 2.2, r=0.22, h=0.6)
    # 夕佳亭: thatched tea room on the hill, the front to the Kinkaku (south-west)
    cx, cy, Ls, Ws, yl = rect_of(ring(180453976))
    sekkatei(B, gz, Loc(cx, cy, math.radians(-33.7)), L=6.2, D=4.3, wing=3.6) if terr.get(180453976) is None else None
    if terr.get(180453976) is not None:
        sekkatei_z(B, Loc(cx, cy, math.radians(-33.7)), terr[180453976])

def sekkatei_z(B, loc, z):
    """the 夕佳亭 on its terrace level z"""
    return sekkatei(B, lambda x, y: z + 0.05, loc, L=6.2, D=4.3, wing=3.6)
