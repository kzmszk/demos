"""The west of the site: 大河内山荘 (the entrance gate at the end of the bamboo path, the thatched 中門, the 大乗閣, the
tea house 滴水庵, paths and lanterns), 亀山公園 (嵐山公園 亀山地区: stone steps, the 頂上展望台 over the 保津川 gorge with the
角倉了以像), and 常寂光寺 (山門, the thatched 仁王門 with its 仁王, the stone stair to the 本堂, 本堂, 妙見宮, 鐘楼, 開山堂,
the 多宝塔 (重要文化財, 1620, 12 m, 方三間, 檜皮葺) on the hillside, all among maples)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from jk import prim, arch, Frame
from jk import roof as jroof
from . import tenryuji_kit as K
from .tenryuji_kit import Loc, facing, ribbon, quad, rect_walk, WD, WHITE, nrm

OKOCHI_REPLACED = [560557236, 560557238, 319185154]
JOJAKKO_REPLACED = [880956276, 880956277, 729932696, 729932697, 880956252, 880956258, 925797407, 880956251]

def osm_steps(S, bbox, width=2.0, skip=(), rise=0.16):
    B0 = box(*bbox)
    out = []
    for w in S.osm['ways']:
        if w['tags'].get('highway') != 'steps' or w['id'] in skip: continue
        for ln in w['line']:
            if len(ln) > 1 and LineString(ln).intersects(B0): out.append((w['id'], ln))
    return out

# ------------------------------------------------------------------ 大河内山荘
def thatch_arch_gate(B, S, x, y, yaw, span=2.4, depth=1.6, h=2.4, rise=0.7):
    """the 中門: two posts each side, a tie beam with a plaque, a barrel-vaulted thatched roof"""
    loc = Loc(x, y, yaw)
    zg = float(S.ground(x, y))
    with loc.frame(B):
        for sx in (-1, 1):
            for sv in (-1, 1):
                prim.box(B, sx * span / 2 - 0.09, sv * depth / 2 - 0.09, zg - 0.2, sx * span / 2 + 0.09, sv * depth / 2 + 0.09, zg + h, 'wood_natural')
            prim.obox(B, (sx * span / 2, -depth / 2 - 0.2, zg + h - 0.15), (sx * span / 2, depth / 2 + 0.2, zg + h - 0.15), 0.12, 0.16, 'wood_natural')
        prim.obox(B, (-span / 2 - 0.3, -depth / 2, zg + h - 0.3), (span / 2 + 0.3, -depth / 2, zg + h - 0.3), 0.14, 0.2, 'wood_natural')
        prim.box(B, -0.35, -depth / 2 - 0.12, zg + h - 0.05, 0.35, -depth / 2 - 0.06, zg + h + 0.5, 'wood_dark', tag='detail')
        # barrel roof: thatch thickness 0.35 m, arched across u
        W = span / 2 + 0.75
        us = np.linspace(-W, W, 15); vs = np.linspace(-depth / 2 - 0.65, depth / 2 + 0.65, 5)
        arc = lambda u: zg + h + 0.15 + rise * (1 - (u / W) ** 2)
        for (off, mat) in ((0.38, 'hiwada'), (0.0, 'wood_natural')):
            P = np.array([(u, v, arc(u) + off) for v in vs for u in us]); nu = len(us) - 1
            I = []
            for j in range(len(vs) - 1):
                for i in range(nu):
                    a = j * (nu + 1) + i
                    I += [[a, a + 1, a + nu + 2], [a, a + nu + 2, a + nu + 1]]
            I = np.array(I)
            if off == 0.0: I = I[:, ::-1]
            B.add(P, I, mat, smooth=True)
        for sv in (-1, 1):
            v = vs[0] if sv < 0 else vs[-1]
            top = np.array([(u, v, arc(u) + 0.38) for u in us]); bot = np.array([(u, v, arc(u)) for u in us])
            Pq = np.concatenate([top, bot]); nu = len(us) - 1
            Iq = np.array([[i, i + 1, i + nu + 2] for i in range(nu)] + [[i, i + nu + 2, i + nu + 1] for i in range(nu)])
            fn = np.cross(Pq[Iq[:, 1]] - Pq[Iq[:, 0]], Pq[Iq[:, 2]] - Pq[Iq[:, 0]])
            if (fn[:, 1].sum() * sv) < 0: Iq = Iq[:, ::-1]
            B.add(Pq, Iq, 'hiwada')
        for su in (-1, 1):
            u = us[0] if su < 0 else us[-1]
            quad(B, (u, vs[0], arc(u)), (u, vs[-1], arc(u)), (u, vs[-1], arc(u) + 0.38), (u, vs[0], arc(u) + 0.38), 'hiwada', out=(su, 0, 0))
        for sx in (-1, 1):
            ribbon(B, [(sx * span / 2, -depth / 2 - 0.3), (sx * span / 2, depth / 2 + 0.3)], 0.4, 'block')
    return loc

def okochi(B, S):
    out = {'replaced': list(OKOCHI_REPLACED), 'zones': [], 'no_trees': []}
    rng = np.random.default_rng(31)
    # the entrance gate (with the ticket window) where the bamboo path ends, facing east
    gx, gy = -8083.0, 3414.8
    loc = Loc(gx, gy, facing(-5.0))
    K.gate(B, S, loc, span=2.8, depth=1.6, H=3.0, r=0.17, roof_L=5.0, roof_D=3.6, pitch=0.7, cover='hiwada', doors='open', bend='wood_natural', wings=(1.4, 2.0))
    for sgn in (-1, 1):
        a = loc.w(sgn * 3.0, 0.8); b = loc.w(sgn * 11.0, 0.8 + (2.0 if sgn > 0 else -1.0))
        n = max(2, int(np.linalg.norm(np.array(b) - np.array(a)) / 0.3))
        pts = np.array([np.array(a) + (np.array(b) - np.array(a)) * k / n for k in range(n + 1)])
        from .tenryuji_bamboo import shibagaki
        shibagaki(B, S, pts, 1 if sgn < 0 else -1, h=1.6, seed=300 + sgn, dark=True, rails=(0.3, 0.9, 1.4), post_mat=WD)
    # the 中門 (thatched barrel roof) up the path
    out['zones'].append(Point(gx, gy).buffer(7.0))
    thatch_arch_gate(B, S, -8102.5, 3416.7, facing(-30.0))
    out['zones'].append(Point(-8102.5, 3416.7).buffer(5.0))
    # 大乗閣: a hillside villa, two roofs (hipped-gable kokera over the main block, a hiwada 入母屋 wing), white walls
    # with shoji, a veranda on posts over the slope
    cx, cy = -8117.5, 3397.3
    yaw = math.radians(-59.0 + 180.0)
    lc = Loc(cx, cy, yaw)
    zg = float(S.ground(cx, cy)) + 0.6
    K.hall(B, S, Loc(*lc.w(-5.0, 0.0), yaw), L=14.0, D=8.4, nu=6, nv=4, zf=zg, H=3.0, r=0.13, walls={0: ['shoji'] * 6, 1: ['white', 'shoji', 'shoji', 'white'], 2: ['white', 'shoji'] * 3, 3: ['white'] * 4},
           head=zg + 1.9, ver=1.0, ver_sides=(0, 1), rail=True, rail_h=0.65, bracket=None,
           roofkw=dict(kind='irimoya', cover='kokera', o=1.4, pitch=0.62, teri=1.4, sori=0.25, rafter=0.22, rafter_end='wood_natural', gable_wall=WD), pillar_round=False)
    K.hall(B, S, Loc(*lc.w(8.5, 0.6), yaw), L=8.4, D=8.4, nu=3, nv=3, zf=zg + 0.4, H=3.2, r=0.14, walls={0: ['shoji'] * 3, 1: ['shoji'] * 3, 2: ['white'] * 3, 3: ['white'] * 3},
           head=zg + 2.3, ver=1.1, ver_sides=(0, 1), rail=True, rail_h=0.65, bracket='funa', bs=0.6,
           roofkw=dict(kind='irimoya', cover='hiwada', o=1.6, pitch=0.75, teri=1.7, sori=0.55, rafter=0.2, rafter_end='wood_natural', gable_wall=WD))
    # the tea house 滴水庵: a small thatched-and-shingled hut with a doma and a round window
    tx, ty = -8131.7, 3366.8
    lt = Loc(tx, ty, math.radians(-153.0 + 180.0))
    zt = float(S.ground(tx, ty)) + 0.45
    K.hall(B, S, lt, L=5.0, D=4.0, nu=2, nv=2, zf=zt, H=2.3, r=0.08, walls={0: ['shoji', 'white'], 1: ['white', 'lattice'], 2: ['white', 'white'], 3: ['white', 'shoji']},
           head=zt + 1.7, band='white', ver=0, ver_sides=(), skirt='white', bracket=None,
           roofkw=dict(kind='irimoya', cover='thatch', o=0.9, pitch=0.95, teri=1.2, sori=0.0, rafter=0.0, gable_wall=WD, edge=0.35, ridge_h=0.4, ridge_w=0.5), walk_floor=False)
    with lt.frame(B):
        K.pent(B, -2.4, 2.4, -2.0, zt + 2.05, 1.0, 0.45, cover='copper', mat='wood_natural')
    # paths: gravel paint, stone lanterns, the 小倉池 side viewpoint deck (bench)
    lu = None
    for f in S.osm['landuse']:
        if f['id'] == 677236682: lu = K.osm_poly(f)
    paths = []
    for w in S.osm['ways']:
        if w['tags'].get('highway') in ('footway', 'path'):
            for ln in w['line']:
                if len(ln) > 1 and lu is not None and LineString(ln).intersects(lu):
                    paths.append(LineString(ln).buffer(0.9))
    if paths:
        P = unary_union(paths).intersection(lu.buffer(1.0))
        for g in (P.geoms if hasattr(P, 'geoms') else [P]):
            if g.geom_type == 'Polygon' and g.area > 2:
                gg = g.simplify(0.4)
                S.paint.append({'poly': [list(map(list, gg.exterior.coords))] + [list(map(list, r.coords)) for r in gg.interiors], 'surf': 'gravel'})
    for (x, y) in ((-8096.0, 3418.5), (-8108.0, 3413.0), (-8124.0, 3383.0), (-8140.0, 3372.0), (-8150.0, 3398.0)):
        K.lantern(B, x, y, float(S.ground(x, y)), h=1.7, kind='kasuga' if rng.random() < 0.6 else 'yukimi')
    out['no_trees'].append(Point(cx, cy).buffer(17.0)); out['no_trees'].append(Point(tx, ty).buffer(5.0))
    return out

# ------------------------------------------------------------------ 亀山公園
def kameyama(B, S):
    out = {'zones': [], 'no_trees': []}
    # stone steps on the OSM steps of the park (walk ramps + treads)
    nb = K.neighbour_zone()
    for wid, ln in osm_steps(S, (-8220, 3060, -7850, 3330)):
        if LineString(ln).intersects(nb) or min(p[1] for p in ln) < 3195.0: continue
        try: K.terrain_steps(B, S, ln, 2.0, rise=0.17, mat='stone', curb=False, rough=0.05, seed=wid % 997)
        except Exception as e: print('steps', wid, e)
    # the summit (頂上展望台, OSM node (-8116, 3281)): a gravel terrace with benches and the 角倉了以像; the deck over
    # the gorge stands ~25 m further west at the cliff edge, where the 保津川 comes into view below
    vx, vy = -8116.0, 3281.0
    zv = float(S.ground(vx, vy))
    terr = Point(vx, vy).buffer(7.0)
    S.paint.append({'poly': [list(map(list, terr.exterior.coords))], 'surf': 'gravel'})
    cx, cy = -8137.0, 3283.5
    d = nrm(np.array([-8286.0 - cx, 3312.0 - cy]))          # towards the gorge (upstream, W)
    n = np.array([-d[1], d[0]])
    P0 = np.array([cx, cy])
    zd = float(S.ground(*P0)) + 0.15
    W2, Dd = 3.6, 4.2
    deck = [P0 + n * W2 - d * 0.6, P0 - n * W2 - d * 0.6, P0 - n * W2 + d * Dd, P0 + n * W2 + d * Dd]
    dk = np.array(deck)
    if np.cross(np.r_[dk[1] - dk[0], 0], np.r_[dk[2] - dk[0], 0])[2] < 0: dk = dk[::-1]
    prim.polygon(B, dk, zd, 'wood_natural')
    prim.polygon(B, dk, zd, 'stone', tag='walk')
    for (a, b) in zip(dk, np.roll(dk, -1, axis=0)):
        quad(B, (a[0], a[1], zd - 0.18), (b[0], b[1], zd - 0.18), (b[0], b[1], zd), (a[0], a[1], zd), 'wood_dark', both=True)
    for u in np.linspace(-W2 + 0.2, W2 - 0.2, 5):
        for v in np.linspace(-0.4, Dd - 0.2, 4):
            q = P0 + n * u + d * v
            zg = float(S.ground(*q))
            if zd - zg > 0.25: prim.box(B, q[0] - 0.09, q[1] - 0.09, zg - 0.2, q[0] + 0.09, q[1] + 0.09, zd - 0.18, 'wood_dark', tag='detail')
    rail = [P0 + n * W2 + d * (-0.3), P0 + n * W2 + d * (Dd - 0.1), P0 - n * W2 + d * (Dd - 0.1), P0 - n * W2 + d * (-0.3)]
    K.simple_rail(B, rail, lambda x, y: zd, h=1.0, post=1.5, rails=2, r=0.06, mat='wood_natural')
    q = P0 - d * 0.1
    for t in (-2.0, 2.0):
        q = np.array([vx, vy]) + n * t
        prim.box(B, q[0] - 0.9, q[1] - 0.22, zv - 0.1, q[0] + 0.9, q[1] + 0.22, zv + 0.42, 'wood_natural')
    # 角倉了以像 on a big rock, looking over the river he opened
    sx, sy = vx - d[0] * 2.0 + n[0] * 5.0, vy - d[1] * 2.0 + n[1] * 5.0
    zs = float(S.ground(sx, sy))
    K.rock(B, (sx, sy, zs), 1.6, 4242, tall=1.15, angular=0.7, sink=0.1)
    prim.box(B, sx - 0.6, sy - 0.5, zs + 1.75, sx + 0.6, sy + 0.5, zs + 1.95, 'bronze')
    prim.lathe(B, (sx, sy, zs + 1.95), [(0.38, 0.0), (0.42, 0.25), (0.34, 0.9), (0.26, 1.35), (0.24, 1.55), (0.12, 1.62), (0.13, 1.72), (0.11, 1.85), (0.0, 1.9)], 10, 'bronze')
    prim.cyl(B, (sx + 0.35, sy, zs + 2.0), (sx + 0.42, sy, zs + 3.2), 0.025, 0.025, 6, 'bronze', tag='detail')
    ribbon(B, [(sx - 1.6, sy), (sx + 1.6, sy)], 3.0, 'block')
    out['view_open'] = Polygon([P0 + d * a + n * b for (a, b) in ((-2, -8), (70, -40), (70, 40), (-2, 8))])
    out['no_trees'] += [terr, Polygon(dk).buffer(2.5)]
    out['deck'] = (cx, cy, zd, d)
    return out

# ------------------------------------------------------------------ 常寂光寺
def niomon(B, S):
    """仁王門 (貞和年間, moved here 1616): 三間一戸 八脚門 with a thick thatched (藁葺) roof; 仁王 in the side bays behind
    lattice; white walls in the end bays"""
    cx, cy = -8180.1, 3754.3
    loc = Loc(cx, cy, facing(0.0))
    zg = 69.0
    L, D = 6.6, 3.8
    us = np.array([-3.3, -1.1, 1.1, 3.3]); vs = np.array([-1.9, 0.0, 1.9])
    with loc.frame(B):
        prim.box(B, -L / 2 - 0.7, -D / 2 - 0.9, zg - 0.6, L / 2 + 0.7, D / 2 + 0.9, zg + 0.15, 'stone')
        rect_walk(B, -1.1, -D / 2 - 0.9, 1.1, D / 2 + 0.9, zg + 0.15)
        z0 = zg + 0.15
        for u in us:
            for v in vs:
                prim.box(B, u - 0.24, v - 0.24, z0 - 0.02, u + 0.24, v + 0.24, z0 + 0.12, 'stone')
                prim.cyl(B, (u, v, z0 + 0.1), (u, v, z0 + 3.4), 0.15, 0.14, 10, WD)
        arch.nageshi(B, L, D, z0 + 3.4, WD, h=0.3, w=0.18, out=0.0)
        arch.nageshi(B, L, D, z0 + 2.5, WD, h=0.2, w=0.12, out=0.1)
        # side bays: the 仁王 behind lattice (front), plaster at the back half
        for sx in (-1, 1):
            u0, u1 = (us[0], us[1]) if sx < 0 else (us[2], us[3])
            K.infill(B, (u0, -D / 2), (u1, -D / 2), z0 + 0.1, z0 + 2.4, 'lattice', out=(0, -1), r=0.15)
            K.infill(B, (u0, 0.0), (u1, 0.0), z0 + 0.1, z0 + 3.3, 'white', out=(0, -1), r=0.15)
            K.infill(B, (u0, D / 2), (u1, D / 2), z0 + 0.1, z0 + 3.3, 'white', out=(0, 1), r=0.15)
            uc = (u0 + u1) / 2
            K.infill(B, (us[0] if sx < 0 else us[3], -D / 2), (us[0] if sx < 0 else us[3], D / 2), z0 + 0.1, z0 + 3.3, 'white', out=(sx, 0), r=0.15)
            # the guardian figure (a stylised standing 仁王)
            prim.box(B, uc - 0.6, -0.8, z0, uc + 0.6, -0.1, z0 + 0.5, 'stone')
            prim.lathe(B, (uc, -0.45, z0 + 0.5), [(0.35, 0.0), (0.42, 0.6), (0.36, 1.0), (0.45, 1.35), (0.3, 1.6), (0.16, 1.68), (0.18, 1.9), (0.0, 2.05)], 10, 'wood_dark')
            ribbon(B, [(u0, -D / 2), (u1, -D / 2)], 0.4, 'block'); ribbon(B, [(u0, 0.0), (u1, 0.0)], 0.4, 'block')
        # the thatched roof: very thick (0.7 m at the eave), hipped-and-gabled, steep
        R = jroof.Roof(L + 0.5, D + 0.5, z0 + 3.75, 1.5, kind='irimoya', cover='thatch', pitch=1.05, teri=1.15, sori=0.15, gable_frac=0.62, edge=0.75,
                       rafter=0.0, rafter_mat=WD, gable_wall=WD, ridge_h=0.55, ridge_w=0.85, ends=None, hip=False)
        R.build(B)
        for sx in (-1, 1):
            ribbon(B, [(us[0 if sx < 0 else 3], -D / 2), (us[0 if sx < 0 else 3], D / 2)], 0.5, 'block')
    return loc

def tahoto(B, S, loc, zp, *, L=4.4, H1=2.9, r=0.18, o1=1.2, o2=1.3, L2=3.1, s1=0.78, s2=0.58):
    """多宝塔 (copied from the 永観堂 kit and tuned): 方三間, 檜皮葺 hogyo roofs, white 亀腹, round body, 三手先 above"""
    out = {}
    with loc.frame(B):
        Pl = L / 2 + 1.5
        zgs = [loc.g(S, sx * Pl, sv * Pl) for sx in (-1, 1) for sv in (-1, 1)]
        prim.box(B, -Pl, -Pl, min(zgs) - 0.5, Pl, Pl, zp - 0.45, 'stone')
        rect_walk(B, -Pl, -Pl, Pl, Pl, zp - 0.45)
        zf = zp
        prim.box(B, -L / 2 - 0.9, -L / 2 - 0.9, zp - 0.45, L / 2 + 0.9, L / 2 + 0.9, zf - 0.1, 'stone')
        prim.box(B, -L / 2 - 0.8, -L / 2 - 0.8, zf - 0.12, L / 2 + 0.8, L / 2 + 0.8, zf, 'wood_natural')
        rect_walk(B, -L / 2 - 0.8, -L / 2 - 0.8, L / 2 + 0.8, L / 2 + 0.8, zf)
        for k in range(4):            # the veranda railing (高欄) round the lower storey
            a = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]])[k] * (L / 2 + 0.72); b = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]])[(k + 1) % 4] * (L / 2 + 0.72)
            if k == 0:
                for (p, q) in ((a, a + (b - a) * 0.38), (a + (b - a) * 0.62, b)): K.railing_run(B, p, q, zf, h=0.62, cap='bronze', giboshi=True, post_step=1.6)
            else: K.railing_run(B, a, b, zf, h=0.62, cap='bronze', giboshi=True, post_step=1.6)
        us, vs = arch.grid(L, L, 3, 3)
        pts = set()
        for x in us: pts.add((round(x, 3), round(vs[0], 3))); pts.add((round(x, 3), round(vs[-1], 3)))
        for y in vs: pts.add((round(us[0], 3), round(y, 3))); pts.add((round(us[-1], 3), round(y, 3)))
        for (x, y) in pts:
            prim.cyl(B, (x, y, zf - 0.02), (x, y, zf + H1), r, r * 0.97, 12, WD, caps=(False, True))
        sides = {0: [(x, vs[0]) for x in us], 1: [(us[-1], y) for y in vs], 2: [(x, vs[-1]) for x in us[::-1]], 3: [(us[0], y) for y in vs[::-1]]}
        head = zf + H1 * 0.76
        for k in range(4):
            sp = sides[k]
            for i in range(3):
                kd = 'karado' if i == 1 else 'renji'
                K.infill(B, sp[i], sp[i + 1], zf + 0.04, head, kd, mat=WD, r=r * 0.9)
                K.infill(B, sp[i], sp[i + 1], head + 0.18, zf + H1 - 0.28, 'board', mat=WD, r=r * 0.9)
        arch.nageshi(B, L, L, head + 0.18, WD, h=0.18, w=0.1, out=r * 0.7)
        arch.nageshi(B, L, L, zf + H1, WD, h=0.28, w=0.18, out=0.0)
        prim.box(B, -0.7, -L / 2 - 0.28, head + 0.35, 0.7, -L / 2 - 0.2, head + 0.95, 'wood_natural', tag='detail')      # 並尊閣 plaque
        top1, reach1 = arch.bracket_row(B, L, L, zf + H1, 'futatesaki', s1, WD, WD, us=us, vs=vs)
        R1 = jroof.Roof(L + 2 * reach1, L + 2 * reach1, top1 + 0.3, o1, kind='hogyo', cover='hiwada', pitch=0.42, teri=1.6, sori=0.34,
                        truncate=None, rafter=0.22, rafter_mat=WD, rafter_end=WD, edge=0.24)
        a1 = R1.a
        s_t = a1 - 1.6
        R1.truncate = s_t
        R1.build(B)
        z_ring = float(R1.z(s_t, a1))
        rt = 1.6 * 1.42
        prim.lathe(B, (0, 0, z_ring - 0.15), [(rt, 0.0), (rt * 0.99, 0.16), (rt * 0.9, 0.42), (rt * 0.78, 0.6), (1.45, 0.68)], 24, 'white_paint')
        zb = z_ring + 0.53
        prim.polygon(B, [(1.45 * math.cos(a), 1.45 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)[:-1]], zb + 0.02, WD)
        prim.cyl(B, (0, 0, zb), (0, 0, zb + 0.35), 1.5, 1.5, 24, WD)
        for k in range(12):
            a = 2 * math.pi * (k + 0.5) / 12
            c, sn = math.cos(a), math.sin(a)
            prim.box(B, 1.52 * c - 0.09, 1.52 * sn - 0.09, zb + 0.35, 1.52 * c + 0.09, 1.52 * sn + 0.09, zb + 0.52, WD, tag='detail')
        prim.cyl(B, (0, 0, zb + 0.5), (0, 0, zb + 0.62), 1.64, 1.64, 24, WD)
        K.ring_railing(B, 0, 0, zb + 0.62, 1.6, h=0.42)
        zu = zb + 0.62
        H2 = 1.4
        prim.cyl(B, (0, 0, zu), (0, 0, zu + H2), 1.34, 1.32, 24, WD, caps=(False, False))
        for k in range(8):
            a = 2 * math.pi * k / 8
            prim.cyl(B, (1.35 * math.cos(a), 1.35 * math.sin(a), zu), (1.35 * math.cos(a), 1.35 * math.sin(a), zu + H2), 0.1, 0.1, 6, WD)
        prim.cyl(B, (0, 0, zu + H2 - 0.25), (0, 0, zu + H2), 1.38, 1.38, 24, WD)
        arch.ring_beam(B, L2, L2, zu + H2 + 0.12, 0.24, 0.24, WD)
        u2 = np.linspace(-L2 / 2, L2 / 2, 4)
        top2, reach2 = arch.bracket_row(B, L2, L2, zu + H2 + 0.12, 'mitesaki', s2, WD, WD, us=u2, vs=u2)
        R2 = jroof.Roof(L2 + 2 * reach2, L2 + 2 * reach2, top2 + 0.3, o2, kind='hogyo', cover='hiwada', pitch=0.5, teri=1.6, sori=0.38,
                        rafter=0.22, rafter_mat=WD, rafter_end=WD, top=[(0.01, 0.0)], edge=0.24)
        zz = R2.build(B)
        a2 = R2.a
        corners = [np.array([sx * a2, sy * a2, float(R2.zE(0.0)) + 0.05]) for sx in (-1, 1) for sy in (-1, 1)]
        Hs = max(3.6, (zp + 12.0 - 0.3) - zz['z_ridge'])
        K.sorin(B, 0, 0, zz['z_ridge'] - 0.15, Hs=Hs, s=0.95, chains_to=corners)
        ribbon(B, [(-L / 2, 0), (L / 2, 0)], L, 'block')
        out.update(zf=zf, top=zz['z_ridge'] + Hs)
    return out

def jojakkoji(B, S):
    out = {'replaced': list(JOJAKKO_REPLACED), 'zones': [], 'no_trees': []}
    rng = np.random.default_rng(57)
    lu = None
    for f in S.osm['landuse']:
        if f['id'] == 925807376: lu = K.osm_poly(f)
    if lu is not None:
        S.paint.append({'poly': [list(map(list, lu.exterior.coords))], 'surf': 'moss'})
    # 山門 (east, on the lane): a small 薬医門 with 本瓦
    K.gate(B, S, Loc(-8126.0, 3754.3, facing(0.0)), span=2.6, depth=1.6, H=3.0, r=0.17, roof_L=5.2, roof_D=3.6, pitch=0.72, cover='hongawara', doors='open', wings=(1.2, 2.1))
    niomon(B, S)
    out['zones'].append(Point(-8180.1, 3754.3).buffer(6.0))
    # the stone stair on the axis from the 仁王門 to the 本堂 (OSM 963156718), and every other flight
    K.terrain_steps(B, S, [(-8188.8, 3754.4), (-8209.3, 3754.5)], 2.6, rise=0.16, mat='stone', curb=True, z0=70.55, z1=73.85, seed=11)
    for wid, ln in osm_steps(S, (-8320, 3700, -8110, 3810), skip=(963156718,)):
        try: K.terrain_steps(B, S, ln, 1.8, rise=0.16, mat='stone', curb=False, rough=0.06, seed=wid % 991)
        except Exception as e: print('steps', wid, e)
    # stone-slab paths (the lane from the 山門 to the 仁王門 and on to the stair)
    for ln, w in ((LineString([(-8126.0, 3754.0), (-8174.5, 3754.3)]), 2.6), (LineString([(-8183.5, 3754.4), (-8189.0, 3754.4)]), 2.6), (LineString([(-8209.3, 3754.5), (-8216.0, 3754.5)]), 3.0)):
        g = ln.buffer(w / 2, cap_style='flat')
        S.paint.append({'poly': [list(map(list, g.exterior.coords))], 'surf': 'stone_slab'})
    # 本堂 (伏見城客殿 移築, 慶長): 入母屋 桟瓦, facing east, a raised floor with a veranda
    hx, hy = -8226.5, 3756.2
    loc = Loc(hx, hy, facing(-8.0))
    zh = 76.45
    K.hall(B, S, loc, L=15.6, D=10.4, nu=6, nv=4, zf=zh + 0.75, H=3.4, r=0.17, walls={0: ['white', 'shoji', 'shoji', 'shoji', 'shoji', 'white'], 1: ['white', 'maira', 'maira', 'white'],
           2: ['white'] * 6, 3: ['white', 'maira', 'maira', 'white']}, head=zh + 0.75 + 2.1, ver=1.1, ver_sides=(0, 1, 3), bracket='funa', bs=0.7,
           roofkw=dict(kind='irimoya', cover='sangawara', o=2.2, pitch=0.66, teri=1.5, sori=0.35, rafter=0.24, rafter_end='white_paint', gable_wall=WD), block_sides=(0, 1, 2, 3))
    with loc.frame(B):
        K.stairs_build(B, (0, -10.4 / 2 - 1.1 - 1.7), (0, -10.4 / 2 - 1.1), zh, zh + 0.7, 2.4, 'wood_natural', cheek=WD, riser=0.18)
        prim.box(B, -1.0, -10.4 / 2 - 0.25, zh + 0.75 + 2.6, 1.0, -10.4 / 2 - 0.18, zh + 0.75 + 3.15, 'black_lacquer', tag='detail')      # 御祈祷処
    # 妙見宮 (拝殿 + 本殿), 鐘楼, 開山堂, 歌仙祠 (small halls)
    K.hall(B, S, Loc(-8226.4, 3731.0, facing(17.0)), L=5.6, D=8.0, nu=3, nv=4, zf=78.4, H=2.8, r=0.14, walls={0: ['open', 'karado', 'open'], 1: ['white'] * 4, 2: ['white'] * 3, 3: ['white'] * 4},
           head=80.5, ver=0.9, ver_sides=(0,), bracket='hira', bs=0.6, roofkw=dict(kind='irimoya', cover='copper', o=1.5, pitch=0.62, sori=0.4, rafter=0.2, rafter_end='white_paint'))
    bl = Loc(-8211.3, 3772.2, math.radians(98.0))
    zb_ = float(S.ground(-8211.3, 3772.2))
    with bl.frame(B):
        prim.box(B, -2.6, -2.4, zb_ - 0.4, 2.6, 2.4, zb_ + 0.9, 'stone')
        z0 = zb_ + 0.9
        for sx in (-1, 1):
            for sv in (-1, 1):
                prim.cyl(B, (sx * 1.7, sv * 1.5, z0), (sx * 1.6, sv * 1.4, z0 + 3.6), 0.17, 0.15, 10, WD)
        arch.ring_beam(B, 3.2, 2.8, z0 + 3.6, 0.18, 0.28, WD)
        arch.ring_beam(B, 3.4, 3.0, z0 + 2.3, 0.1, 0.18, WD)
        jroof.roof(B, 3.6, 3.2, z0 + 3.95, 1.4, kind='irimoya', cover='hongawara', pitch=0.72, rafter=0.22, rafter_mat=WD, rafter_end='white_paint')
        prim.lathe(B, (0, 0, z0 + 2.15), [(0.55, 0.0), (0.53, 0.08), (0.48, 0.35), (0.46, 1.0), (0.36, 1.2), (0.12, 1.28), (0.0, 1.3)], 14, 'bronze')
        ribbon(B, [(-2.6, 0), (2.6, 0)], 4.8, 'block')
    K.hall(B, S, Loc(-8271.3, 3767.1, facing(-90.0)), L=3.6, D=3.4, nu=1, nv=1, zf=86.4, H=2.4, r=0.12, walls={0: ['karado'], 1: ['white'], 2: ['white'], 3: ['white']},
           head=88.2, ver=0.6, ver_sides=(0,), bracket='funa', bs=0.5, roofkw=dict(kind='hogyo', cover='hiwada', o=1.0, pitch=0.6, sori=0.3, rafter=0.18, rafter_end=WD))
    K.hall(B, S, Loc(-8291.0, 3723.6, facing(-90.0)), L=2.4, D=2.2, nu=1, nv=1, zf=95.6, H=2.0, r=0.1, walls={0: ['karado'], 1: ['white'], 2: ['white'], 3: ['white']},
           head=97.1, ver=0, ver_sides=(), bracket=None, roofkw=dict(kind='kirizuma', cover='copper', o=0.7, pitch=0.6, verge=0.5, rafter=0.16, rafter_end=WD))
    # 多宝塔 on its terrace (floor ~87.4)
    tx, ty = -8271.2, 3746.0
    tahoto(B, S, Loc(tx, ty, facing(0.0)), 87.6)
    arch.torii(B, -8210.4, 3736.0, float(S.ground(-8210.4, 3736.0)), facing(17.0) - math.pi / 2 + math.pi / 2, h=3.0, span=2.1)
    out['no_trees'] += [Point(hx, hy).buffer(13.0), Point(tx, ty).buffer(6.5), Point(-8226.4, 3731.0).buffer(6.0), Point(-8211.3, 3772.2).buffer(4.0)]
    # lanterns (OSM: 灯籠 points)
    for p in S.osm['points']:
        if p['tags'].get('man_made') == 'lamp' and lu is not None and lu.buffer(5).contains(Point(p['xy'])):
            x, y = p['xy']
            K.lantern(B, x, y, float(S.ground(x, y)), h=1.8)
    return out

def build(B, S, parts):
    out = {'replaced': [], 'zones': [], 'no_trees': []}
    if 'west' in parts:
        ok = okochi(B, S)
        km = kameyama(B, S)
        for d in (ok, km):
            out['replaced'] += d.get('replaced', []); out['zones'] += d.get('zones', []); out['no_trees'] += d.get('no_trees', [])
        out['view_open'] = km['view_open']
    if 'jojakkoji' in parts:
        jj = jojakkoji(B, S)
        out['replaced'] += jj['replaced']; out['zones'] += jj['zones']; out['no_trees'] += jj['no_trees']
    return out
