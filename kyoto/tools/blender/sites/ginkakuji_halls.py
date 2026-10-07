"""銀閣寺: the other buildings.  東求堂 (1486, 入母屋 檜皮葺, 6.9 m square, faces south), 本堂 (方丈, 1624), 宝処関, the
corridor between 本堂 and 東求堂, 弄清亭, 庫裏, 書院, 研修道場 and the support buildings of the precinct (their generic
boxes are dropped with the precinct), gates (総門, 中門, two small 棟門), white walls (築地塀 style), small shrines.
Garden-local coordinates (origin = 銀閣), z absolute."""
import math
import numpy as np
from jk import prim, arch, Frame
from jk import roof as jroof
from . import ginkakuji_util as U

WD = 'wood_dark'

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

# ------------------------------------------------------------------ gates
def yakuimon(B, cx, cy, yaw, z0, span=3.3, depth=1.9, h=3.1, ridge=4.5, cover='hongawara', doors=True, side_walls=2.2, wall_h=2.3):
    """薬医門: two main pillars on the front line with door leaves, two 控柱 behind, a 切妻 roof with the ridge along the
    front, plaque, short plaster walls with tiled copings either side.  u along the front, the gate faces -v."""
    with Frame(B, cx, cy, z0, yaw):
        for s in (-1, 1):
            x = s * span / 2
            prim.box(B, x - 0.18, -0.16, -0.1, x + 0.18, 0.16, h, WD)                         # 本柱
            prim.cyl(B, (x, -0.01, -0.05), (x, -0.01, 0.35), 0.3, 0.27, 8, 'stone')            # 礎石 (hidden mostly)
            prim.box(B, x - 0.12, depth - 0.12, -0.1, x + 0.12, depth + 0.12, h - 0.4, WD)     # 控柱
            prim.box(B, x - 0.1, 0.0, h - 0.65, x + 0.1, depth, h - 0.45, WD)                   # 貫 front-back
            prim.box(B, x - 0.13, -0.6, h, x + 0.13, depth + 0.5, h + 0.28, WD)                 # 腕木 / 男梁
        prim.box(B, -span / 2 - 0.5, -0.17, h - 0.35, span / 2 + 0.5, 0.17, h, WD)              # 冠木
        prim.box(B, -span / 2 - 0.2, depth - 0.12, h - 0.55, span / 2 + 0.2, depth + 0.12, h - 0.4, WD)
        prim.box(B, -0.35, -0.2, h - 0.95, 0.35, -0.16, h - 0.4, 'wood_natural')                # 扁額
        if doors:
            for s in (-1, 1):
                x0, x1 = (s * 0.02, s * (span / 2 - 0.18))
                lo, hi = min(x0, x1), max(x0, x1)
                # leaves opened inward (rotated 90 deg against the side)
                xx = s * (span / 2 - 0.25)
                prim.box(B, xx - 0.03, 0.18, 0.05, xx + 0.03, 0.18 + (hi - lo), h - 0.4, WD)
                for zz in np.linspace(0.3, h - 0.6, 5):
                    prim.box(B, xx - 0.05, 0.2, zz, xx + 0.05, 0.16 + (hi - lo), zz + 0.06, WD, tag='detail')
        # roof: a gable along u, ridge a little behind the front line
        L = span + 1.0; D = depth + 0.6
        with Frame(B, 0, depth / 2, 0, 0):
            pitch = roof_pitch(L, D, h + 0.4, 0.9, ridge, 1.3, 'kirizuma')
            jroof.roof(B, L, D, h + 0.4, 0.9, kind='kirizuma', cover=cover, pitch=pitch, teri=1.3, sori=0.0, rafter=0.28, tiers=1,
                       rafter_mat=WD, rafter_end=WD, ends='oni', verge=0.6, edge=0.25, bargeboard_mat=WD)
        prim.polygon(B, [(-span / 2, -0.4), (span / 2, -0.4), (span / 2, depth + 0.3), (-span / 2, depth + 0.3)], 0.05, 'stone', tag='walk')
        prim.box(B, -span / 2 + 0.2, -0.35, -0.2, span / 2 - 0.2, depth + 0.25, 0.04, 'stone')

def white_wall(B, pts, gz, h=2.2, th=0.42, tag='main', koshi=0.0, step=2.0):
    """塀: a stone footing, white plaster (or a wooden lower panel), a small tiled coping.  pts garden-local polyline"""
    pts = [np.asarray(p, float) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; d = b - a; L = float(np.linalg.norm(d))
        if L < 0.1: continue
        d /= L; n = np.array([-d[1], d[0]])
        k = max(1, int(math.ceil(L / step)))
        for j in range(k):
            p = a + d * L * j / k; q = a + d * L * (j + 1) / k
            zz = min(gz(*p), gz(*q))
            # footing
            prim.obox(B, np.r_[(p + q) / 2 - d * (L / k / 2 + 0.01), zz + 0.05], np.r_[(p + q) / 2 + d * (L / k / 2 + 0.01), zz + 0.05], th + 0.1, 0.5, 'stone', tag=tag)
            for side in (-1, 1):
                A = p + n * side * th / 2; Bq = q + n * side * th / 2
                z1 = zz + 0.3
                o3 = (n[0] * side, n[1] * side, 0.0)
                if koshi:
                    P = np.array([np.r_[A, z1], np.r_[Bq, z1], np.r_[Bq, z1 + koshi], np.r_[A, z1 + koshi]])
                    U.oadd(B, P, [[0, 1, 2], [0, 2, 3]], WD, o3, UV=np.array([[0, 0], [L / k, 0], [L / k, koshi], [0, koshi]]), tag=tag); z1 += koshi
                P = np.array([np.r_[A, z1], np.r_[Bq, z1], np.r_[Bq, zz + h], np.r_[A, zz + h]])
                U.oadd(B, P, [[0, 1, 2], [0, 2, 3]], 'temple_wall', o3, UV=np.array([[0, z1], [L / k, z1], [L / k, zz + h], [0, zz + h]]), tag=tag, c0=(238, 234, 224, 35), c1=(0, 0, 0, 0))
                # coping
                A2 = p + n * side * (th / 2 + 0.3); B2 = q + n * side * (th / 2 + 0.3)
                P = np.array([np.r_[A2, zz + h + 0.02], np.r_[B2, zz + h + 0.02], np.r_[q, zz + h + 0.32], np.r_[p, zz + h + 0.32]])
                I = [[0, 1, 2], [0, 2, 3]] if side < 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I, 'kawara', UV=np.array([[0, 0], [L / k, 0], [L / k, 0.5], [0, 0.5]]), tag=tag)
                P = np.array([np.r_[A2, zz + h + 0.02], np.r_[B2, zz + h + 0.02], np.r_[B2, zz + h - 0.06], np.r_[A2, zz + h - 0.06]])
                U.oadd(B, P, [[0, 1, 2], [0, 2, 3]], 'kawara', o3, tag=tag)
                Pu = np.array([np.r_[A, zz + h], np.r_[Bq, zz + h], np.r_[B2, zz + h - 0.04], np.r_[A2, zz + h - 0.04]])
                U.oadd(B, Pu, [[0, 1, 2], [0, 2, 3]], WD, (0, 0, -1), tag=tag)
            prim.obox(B, np.r_[p, zz + h + 0.38], np.r_[q, zz + h + 0.38], 0.2, 0.14, 'ridge', tag=tag)
        prim.obox(B, np.r_[a, gz(*a) + h / 2], np.r_[b, gz(*b) + h / 2], th + 0.1, h + 0.6, 'stone', tag='block')

def munemon(B, cx, cy, yaw, z0, span=1.8, h=2.6, cover='sangawara'):
    """棟門: two posts, a beam, a small gable roof; leaves open"""
    with Frame(B, cx, cy, z0, yaw):
        for s in (-1, 1):
            prim.box(B, s * span / 2 - 0.12, -0.12, 0, s * span / 2 + 0.12, 0.12, h, WD)
            prim.box(B, s * (span / 2 - 0.12) - 0.025, 0.12, 0.05, s * (span / 2 - 0.12) + 0.025, 0.12 + span / 2 - 0.1, h - 0.35, WD)
        prim.box(B, -span / 2 - 0.3, -0.12, h - 0.3, span / 2 + 0.3, 0.12, h, WD)
        prim.box(B, -0.1, -0.7, h, 0.1, 0.7, h + 0.2, WD)
        jroof.roof(B, span + 0.3, 0.5, h + 0.25, 0.55, kind='kirizuma', cover=cover, pitch=0.55, teri=1.2, sori=0.0, rafter=0.3, tiers=1,
                   rafter_mat=WD, rafter_end=WD, ends='oni', verge=0.35, edge=0.2, bargeboard_mat=WD)

def hokora(B, x, y, z, yaw, w=1.0, d=0.8, h=1.0, base=0.9, roofmat='copper'):
    """a small shrine (祠) on a stone base"""
    with Frame(B, x, y, z, yaw):
        for i in range(3):
            s = 1.0 - i * 0.12
            U.rock(B, (0.15 * (i - 1), 0.05 * i, base * (0.25 + 0.3 * i)), base * 0.75 * s, 900 + i, flat=0.7, sub=1, sink=0.3)
        prim.box(B, -w * 0.6, -d * 0.6, base, w * 0.6, d * 0.6, base + 0.12, 'stone')
        prim.box(B, -w / 2, -d / 2, base + 0.12, w / 2, d / 2, base + 0.12 + h, WD)
        prim.box(B, -w / 2 + 0.06, -d / 2 - 0.01, base + 0.25, w / 2 - 0.06, -d / 2 + 0.01, base + h - 0.05, 'wood_natural')
        jroof.roof(B, w, d, base + 0.12 + h + 0.05, 0.35, kind='kirizuma', cover='copper', pitch=0.55, teri=1.4, sori=0.1, rafter=0, tiers=1,
                   rafter_mat=WD, ends=None, verge=0.25, edge=0.08)

# ------------------------------------------------------------------ simple support buildings from a footprint rectangle
def simple_building(B, S, ring, gz, h_ridge=7.0, wall=3.0, cover='sangawara', o=0.9, kind=None, seed=0, front=None, detail=False):
    cx, cy, L, Wd, yaw = S.rect(ring)
    L = max(2.0, L - 2 * o * 0.8); Wd = max(2.0, Wd - 2 * o * 0.8)
    z0 = float(min(gz(x, y) for (x, y) in ring)) - 0.05
    kind = kind or ('irimoya' if L > 7 else 'kirizuma')
    rng = np.random.default_rng(seed)
    nb = (max(1, int(round(L / 1.8))), max(1, int(round(Wd / 1.8))))
    pat = ['plaster', 'mairado', 'plaster', 'shoji', 'plaster', 'koshi']
    def fit(k, i):
        if k in (0, 2): return pat[(i + seed + k) % len(pat)]
        return 'plaster' if (i + seed) % 3 else 'mairado'
    return hall(B, cx, cy, yaw, z0, L, Wd, nb=nb, fit=fit, floor=0.45, wall=wall, nage=1.8, roof=kind, cover=cover, o=o,
                ridge=z0 + h_ridge, teri=1.25, rafter=0 if not detail else 0.45, tiers=1, sori=0.05, funa=False, detail=False, verge=0.5,
                ends='oni')
