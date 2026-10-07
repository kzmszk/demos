"""三十三間堂: the grounds.  南大門 (1600, 三間一戸八脚門), 太閤塀 (築地塀 5.2 m x 92 m), 東大門 and the vermilion
galleries (1961), 北門, 西門, the bell tower (1988), 手水舎 with 夜泣泉, 久勢稲荷, two minor halls, the east garden
ponds, the precinct walls, gravel and stone paths, trees; site edits (exclude / cut / paint).

Positions from the OSM footprints (world frame).  `R(u, v)` maps the "rect frame" used in the analysis (centre and
axes of the hall footprint's bounding rectangle, u north, v west) to the world."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point
from jk import prim, arch, roof as jroof, Frame
from . import sanjusangendo_parts as P
from .sanjusangendo_parts import WOOD, PLASTER, slab, quad2, block_rect, block_line

VERM = 'vermilion'

def build(B, S, O, zfl, yaw, U, V):
    cx, cy, L, W_, ry = S.rect(S.osm_building(99185529)['poly'][0])
    Ur = np.array([math.cos(ry), math.sin(ry)]); Vr = np.array([-math.sin(ry), math.cos(ry)])
    C = np.array([cx, cy])
    R = lambda u, v: C + u * Ur + v * Vr
    G = lambda x, y: float(S.ground(x, y))
    ctx = dict(S=S, R=R, G=G, yaw=ry, Ur=Ur, Vr=Vr)
    nandaimon(B, ctx)
    taikobei(B, ctx)
    east_gate(B, ctx)
    galleries(B, ctx)
    north_gate(B, ctx)
    west_gate(B, ctx)
    bell_tower(B, ctx)
    chozuya(B, ctx)
    minor_buildings(B, ctx)
    reception(B, ctx)
    ponds(B, ctx)
    walls(B, ctx)
    paths_and_paint(B, ctx, O, zfl, U, V)
    trees(B, ctx)
    edits(S, ctx)

def osm_frame(ctx, bid):
    S = ctx['S']
    b = S.osm_building(bid)
    cx, cy, L, W, yaw = S.rect(b['poly'][0])
    return cx, cy, L, W, yaw, b['poly'][0][0]

# ------------------------------------------------------------------ 南大門
def nandaimon(B, ctx):
    """三間一戸八脚門, 切妻造, 本瓦葺 (1600).  Roof outline 22.2 x 13.4 (OSM); 12.4 m high (PLATEAU)."""
    cx, cy, L, W, yaw, _ = osm_frame(ctx, 99185517)
    z0 = min(ctx['G'](cx + dx, cy + dy) for dx in (-6, 0, 6) for dy in (-4, 0, 4))
    us = [-7.2, -2.8, 2.8, 7.2]; vs = [-3.3, 0.0, 3.3]
    H = 6.1
    with Frame(B, cx, cy, z0, yaw):
        for u in us:
            for v in vs:
                r = 0.42 if v == 0 else 0.33
                arch.pillar(B, u, v, 0.0, H, r, WOOD)
                block_rect(B, u - 0.45, v - 0.45, u + 0.45, v + 0.45, 0.0)
        # tie beams: 頭貫 round the rectangle and along the centre line, a lower 貫 front/back
        for v in vs:
            prim.obox(B, (us[0] - 0.5, v, H - 0.2), (us[-1] + 0.5, v, H - 0.2), 0.3, 0.42, WOOD)
            prim.obox(B, (us[0] - 0.3, v, 3.9), (us[-1] + 0.3, v, 3.9), 0.2, 0.32, WOOD)
        for u in us:
            prim.obox(B, (u, vs[0] - 0.5, H - 0.2), (u, vs[-1] + 0.5, H - 0.2), 0.3, 0.42, WOOD)
            P.arch_beam(B, (u, vs[0]), (u, vs[-1]), 4.3, 0.28, 0.45, 0.12)
        # plaster walls in the side bays on the centre line, with a 貫
        for (a, b) in ((us[0], us[1]), (us[2], us[3])):
            slab(B, a + 0.38, -0.12, b - 0.38, 0.12, 0.25, H - 0.4, 'temple_wall', c0=PLASTER['c0'])
            prim.obox(B, (a, 0, 2.2), (b, 0, 2.2), 0.3, 0.3, WOOD)
            prim.obox(B, (a, 0, 0.12), (b, 0, 0.12), 0.32, 0.24, WOOD)
            block_line(B, [(a, 0), (b, 0)], 0.0, 0.6)
        # the doors of the central bay stand open against the side walls
        for su in (-1, 1):
            hinge = np.array([su * 2.42, 0.18])
            P.plank_leaf(B, hinge, (-su, 0), (0, 1), 2.4, 0.15, 4.6, math.radians(90), th=0.12)
        top, reach = arch.bracket_row(B, 14.4, 6.6, H, 'degumi', 1.2, WOOD, 'white_paint', us=np.array(us), vs=np.array(vs))
        o = 2.1
        Lr, Dr = 14.4 + 2 * reach, 6.6 + 2 * reach
        c = Dr / 2 + o
        z_eave = top + 0.45
        apex = 11.4
        pitch = (apex - z_eave) / (c * (1 - (o / c) ** 1.4))
        vo = max(0.9, (L - Lr) / 2)
        jroof.roof(B, Lr, Dr, z_eave, o, kind='kirizuma', cover='hongawara', pitch=pitch, verge=vo, rafter=0.28,
                   rafter_mat=WOOD, rafter_end='white_paint', ridge_h=1.0, ridge_w=0.8, ends='oni', sori=0.0)

# ------------------------------------------------------------------ 太閤塀
def taikobei(B, ctx):
    """築地塀 (rammed earth on a stone footing, timber 寄柱, tiled 切妻 coping with 太閤桐 tile ends), 5.2-5.3 m high, 92 m"""
    R, G = ctx['R'], ctx['G']
    p0 = R(-95.9, -45.6); p1 = R(-97.95, 50.75)               # east end tucked under the 南大門's verge, west end at the precinct wall
    d = p1 - p0; Lw = float(np.linalg.norm(d)); yaw = math.atan2(d[1], d[0])
    m = (p0 + p1) / 2
    ts = np.linspace(0, 1, 40)
    gs = np.array([G(*(p0 + d * t)) for t in ts])
    z0 = float(np.percentile(gs, 70))
    gmin = float(gs.min())
    with Frame(B, m[0], m[1], z0, yaw):
        a = -Lw / 2; b = Lw / 2
        # stone footing
        slab(B, a, -1.15, b, 1.15, gmin - z0 - 0.3, 0.35, 'stone')
        # the earth body: a battered prism (1.9 m at the base, 1.5 m at the top)
        hb, ht, z1 = 0.95, 0.75, 4.15
        Pq = np.array([(a, -hb, 0.35), (b, -hb, 0.35), (b, -ht, z1), (a, -ht, z1), (a, hb, 0.35), (b, hb, 0.35), (b, ht, z1), (a, ht, z1)])
        tint = dict(c0=(212, 186, 138, 35), c1=(0, 0, 7, 0))
        B.add(Pq, [[0, 1, 2], [0, 2, 3]], 'temple_wall', **tint)
        B.add(Pq, [[4, 6, 5], [4, 7, 6]], 'temple_wall', **tint)
        B.add(Pq, [[0, 3, 7], [0, 7, 4], [1, 5, 6], [1, 6, 2]], 'temple_wall', **tint)
        # white lines (筋) and posts (寄柱) every ken, both faces
        for s in (-1, 1):
            for zz in (1.15, 2.6):
                t = (zz - 0.35) / (z1 - 0.35); off = hb + (ht - hb) * t + 0.01
                prim.obox(B, (a, s * off, zz), (b, s * off, zz), 0.012, 0.03, 'white_paint', tag='detail')
        nk = 29
        for i in range(nk + 1):
            u = a + (b - a) * i / nk
            for s in (-1, 1):
                prim.obox(B, (u, s * (hb - 0.02), 0.35), (u, s * (ht + 0.02), z1 + 0.05), 0.26, 0.18, WOOD, up=(1, 0, 0))
        block_rect(B, a, -1.1, b, 1.1, 0.0)
        # tiled coping: a small 切妻 roof with rafters and round tile ends
        jroof.roof(B, Lw - 0.2, 1.5, z1 + 0.45, 1.25, kind='kirizuma', cover='hongawara', pitch=0.62, verge=0.4, rafter=0.3, tiers=1,
                   rafter_mat=WOOD, rafter_end=WOOD, ridge_h=0.42, ridge_w=0.45, ends='oni', sori=0.0, edge=0.26)

# ------------------------------------------------------------------ 東大門 + 回廊
def east_gate(B, ctx):
    """東大門 (1961): vermilion five-bay gate, 入母屋 本瓦葺, doors in the three middle bays, on a stone platform"""
    cx, cy, L, W, yaw, _ = osm_frame(ctx, 510791007)
    # orient the frame so that -v points west (toward the hall): S.rect gives the long side's direction
    U = np.array([math.cos(yaw), math.sin(yaw)])
    if U[1] > 0: yaw += math.pi                       # u pointing south -> v = east, front (-v) = west
    z0 = min(ctx['G'](cx + dx, cy + dy) for dx in (-8, 0, 8) for dy in (-8, 0, 8))
    Lb, Db, H, hb = 16.5, 6.2, 4.3, 0.75
    with Frame(B, cx, cy, z0, yaw):
        arch.platform(B, [(-Lb / 2 - 1.6, -Db / 2 - 1.8), (Lb / 2 + 1.6, -Db / 2 - 1.8), (Lb / 2 + 1.6, Db / 2 + 1.8), (-Lb / 2 - 1.6, Db / 2 + 1.8)], -0.4, hb)
        for s in (-1, 1):
            arch.stairs(B, (0, s * (Db / 2 + 3.3)), (0, s * (Db / 2 + 1.8)), 0.0, hb, 9.5, 'stone', riser=0.19)
        us, vs = arch.grid(Lb, Db, 5, 2)
        for x in us:
            for y in vs: arch.pillar(B, x, y, hb, hb + H, 0.24, VERM)
        # infill on the centre line: doors in the middle three bays, plaster in the end bays
        for i in range(5):
            a, b = us[i], us[i + 1]
            if 1 <= i <= 3:
                w = (b - a - 0.5) / 2
                P.plank_leaf(B, (a + 0.25, 0.0), (1, 0), (0, -1), w, hb + 0.15, hb + H - 0.5, 0.0, mat=VERM, th=0.12)
                P.plank_leaf(B, (b - 0.25, 0.0), (-1, 0), (0, -1), w, hb + 0.15, hb + H - 0.5, 0.0, mat=VERM, th=0.12)
                slab(B, a + 0.2, -0.1, b - 0.2, 0.1, hb + H - 0.5, hb + H - 0.2, 'temple_wall', c0=PLASTER['c0'])
            else:
                slab(B, a + 0.22, -0.1, b - 0.22, 0.1, hb + 0.1, hb + H - 0.2, 'temple_wall', c0=PLASTER['c0'])
            # side walls (plaster) on the outer lines of the end bays
        for y in vs:
            prim.obox(B, (us[0] - 0.4, y, hb + H - 0.15), (us[-1] + 0.4, y, hb + H - 0.15), 0.24, 0.3, VERM)
            prim.obox(B, (us[0], y, hb + 0.08), (us[-1], y, hb + 0.08), 0.2, 0.16, VERM)
        for x in us:
            prim.obox(B, (x, vs[0] - 0.4, hb + H - 0.15), (x, vs[-1] + 0.4, hb + H - 0.15), 0.24, 0.3, VERM)
        for x in (us[0], us[-1]):
            for j in range(2):
                slab(B, x - 0.1, vs[j] + 0.22, x + 0.1, vs[j + 1] - 0.22, hb + 0.1, hb + H - 0.3, 'temple_wall', c0=PLASTER['c0'])
        block_line(B, [(us[0], 0), (us[-1], 0)], hb, 0.6)
        for x in (us[0], us[-1]): block_line(B, [(x, vs[0]), (x, vs[-1])], hb, 0.6)
        top, reach = arch.bracket_row(B, Lb, Db, hb + H, 'demitsudo', 1.0, VERM, 'white_paint', us=us, vs=vs)
        Lr, Dr = Lb + 2 * reach, Db + 2 * reach
        o = 2.6
        jroof.roof(B, Lr, Dr, top + 0.4, o, kind='irimoya', cover='hongawara', pitch=0.46, rafter=0.3, rafter_mat=VERM, rafter_end='white_paint',
                   ridge_h=0.8, ridge_w=0.6, ends='oni', sori=0.35, gable_frac=0.55)

def kairo(B, G, p0, p1, wall_side=1, z_floor=None, bay=3.0, depth=3.2, H=3.3, hb=0.36):
    """回廊 (1961 vermilion gallery): a single-aisle corridor from p0 to p1 (world 2D), outer wall on the
    `wall_side` (+1: left of p0->p1) with green 連子窓 over white plaster, open colonnade on the other side;
    切妻 roof with gray tiles, vermilion rafters; a raised stone floor (walkable)."""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; Lg = float(np.linalg.norm(d)); yaw = math.atan2(d[1], d[0])
    m = (p0 + p1) / 2
    zs = [G(*(p0 + d * t)) for t in np.linspace(0, 1, 12)]
    z0 = z_floor if z_floor is not None else max(zs) - hb + 0.05
    nb = max(1, int(round(Lg / bay)))
    us = np.linspace(-Lg / 2, Lg / 2, nb + 1)
    vw = wall_side * depth / 2; vo = -wall_side * depth / 2
    with Frame(B, m[0], m[1], z0, yaw):
        arch.platform(B, [(-Lg / 2 - 0.6, -depth / 2 - 1.0), (Lg / 2 + 0.6, -depth / 2 - 1.0), (Lg / 2 + 0.6, depth / 2 + 1.0), (-Lg / 2 - 0.6, depth / 2 + 1.0)],
                      min(zs) - z0 - 0.3, hb, mat='stone')
        for u in us:
            for v in (vw, vo): arch.pillar(B, u, v, hb, hb + H, 0.17, VERM)
            block_rect(B, u - 0.3, vo - 0.3, u + 0.3, vo + 0.3, hb)
        for v in (vw, vo):
            prim.obox(B, (us[0] - 0.3, v, hb + H - 0.13), (us[-1] + 0.3, v, hb + H - 0.13), 0.2, 0.26, VERM)
        # the outer wall: plaster below (with a vermilion rail), green 連子窓, plaster band, all between vermilion frames
        for a, b in zip(us[:-1], us[1:]):
            a2, b2 = a + 0.17, b - 0.17
            slab(B, a2, vw - 0.07, b2, vw + 0.07, hb, hb + 0.95, 'temple_wall', c0=PLASTER['c0'])
            prim.obox(B, (a2, vw, hb + 0.06), (b2, vw, hb + 0.06), 0.18, 0.12, VERM)
            prim.obox(B, (a2, vw, hb + 1.0), (b2, vw, hb + 1.0), 0.18, 0.12, VERM)
            P.renji(B, (a2 + 0.35, vw), (b2 - 0.35, vw), hb + 1.06, hb + 2.45, th=0.14, step=0.1, mat='copper')
            for (s0, s1) in ((a2, a2 + 0.35), (b2 - 0.35, b2)):
                slab(B, s0, vw - 0.06, s1, vw + 0.06, hb + 1.06, hb + 2.45, 'temple_wall', c0=PLASTER['c0'])
            prim.obox(B, (a2, vw, hb + 2.5), (b2, vw, hb + 2.5), 0.18, 0.12, VERM)
            slab(B, a2, vw - 0.06, b2, vw + 0.06, hb + 2.56, hb + H - 0.26, 'temple_wall', c0=PLASTER['c0'])
        block_line(B, [(us[0], vw), (us[-1], vw)], hb, 0.6)
        for u in us:
            prim.obox(B, (u, vw + wall_side * 0.25, hb + H - 0.4), (u, vo - wall_side * 0.25, hb + H - 0.4), 0.18, 0.24, VERM)
        top, reach = arch.bracket_row(B, Lg, depth, hb + H, 'hira', 0.75, VERM, us=us, vs=np.array([-depth / 2, depth / 2]), purlin=True)
        jroof.roof(B, Lg + 2 * reach, depth + 2 * reach, top + 0.3, 1.25, kind='kirizuma', cover='hongawara', pitch=0.5, verge=0.6,
                   rafter=0.3, tiers=1, rafter_mat=VERM, rafter_end='white_paint', ridge_h=0.45, ridge_w=0.5, ends='oni', sori=0.0, edge=0.26)
        # exposed ceiling under the roof inside the corridor (rafters on a sloped board)
        zt = top + 0.3
        for sv in (-1, 1):
            quad2(B, (-Lg / 2, sv * (depth / 2 + reach), zt - 0.25), (Lg / 2, sv * (depth / 2 + reach), zt - 0.25),
                  (Lg / 2, 0.0, zt + 0.55), (-Lg / 2, 0.0, zt + 0.55), VERM)

def galleries(B, ctx):
    R, G = ctx['R'], ctx['G']
    # north gallery: from the east gate to the north gate; south gallery: from the east gate to its south end
    kairo(B, G, R(12.9, -48.4), R(73.8, -48.7), wall_side=-1)
    kairo(B, G, R(-11.1, -47.4), R(-68.6, -47.3), wall_side=1)

# ------------------------------------------------------------------ 北門, 西門
def gate_small(B, cx, cy, z0, yaw, width, depth, H, mat, cover='hongawara', doors='closed', karahafu=False):
    """a small gate (四脚門 / 薬医門): two main posts, two rear posts, doors, 切妻 roof"""
    with Frame(B, cx, cy, z0, yaw):
        for su in (-1, 1):
            arch.pillar(B, su * width / 2, 0.0, 0.0, H, 0.24, mat)
            arch.pillar(B, su * width / 2, depth, 0.0, H - 0.4, 0.18, mat)
            prim.obox(B, (su * width / 2, -0.2, H - 0.9), (su * width / 2, depth + 0.2, H - 0.7), 0.22, 0.3, mat)
            block_rect(B, su * width / 2 - 0.35, -0.35, su * width / 2 + 0.35, depth + 0.35, 0.0)
        prim.obox(B, (-width / 2 - 0.6, 0, H - 0.18), (width / 2 + 0.6, 0, H - 0.18), 0.3, 0.36, mat)
        prim.obox(B, (-width / 2 - 0.3, 0, H - 1.2), (width / 2 + 0.3, 0, H - 1.2), 0.24, 0.3, mat)
        w = (width - 0.5) / 2
        if doors == 'closed':
            P.plank_leaf(B, (-width / 2 + 0.25, 0.08), (1, 0), (0, 1), w, 0.08, H - 1.4, 0.0, mat=mat, th=0.12)
            P.plank_leaf(B, (width / 2 - 0.25, 0.08), (-1, 0), (0, 1), w, 0.08, H - 1.4, 0.0, mat=mat, th=0.12)
            block_line(B, [(-width / 2, 0), (width / 2, 0)], 0.0, 0.6)
        else:
            P.plank_leaf(B, (-width / 2 + 0.25, 0.1), (1, 0), (0, 1), w, 0.08, H - 1.4, math.radians(88), mat=mat, th=0.12)
            P.plank_leaf(B, (width / 2 - 0.25, 0.1), (-1, 0), (0, 1), w, 0.08, H - 1.4, math.radians(88), mat=mat, th=0.12)
        with Frame(B, 0, depth / 2 - 0.4, 0, 0):
            jroof.roof(B, width + 0.6, depth + 1.0, H + 0.45, 1.3, kind='kirizuma', cover=cover, pitch=0.62, verge=0.9, rafter=0.26, tiers=1,
                       rafter_mat=mat, rafter_end='white_paint' if mat == VERM else mat, ridge_h=0.55, ridge_w=0.5, ends='oni', sori=0.0)

def north_gate(B, ctx):
    cx, cy, L, W, yaw, _ = osm_frame(ctx, 466943459)
    R = ctx['R']
    # the gate faces east (the street); frame u across the opening (N-S), +v = west (inside)
    p = R(78.0, -49.0)
    z0 = ctx['G'](*p)
    gate_small(B, p[0], p[1], z0, ctx['yaw'], 4.4, 2.6, 5.0, VERM)

def west_gate(B, ctx):
    R = ctx['R']
    p = R(76.5, 39.5)
    z0 = ctx['G'](*p)
    gate_small(B, p[0], p[1], z0, ctx['yaw'], 3.6, 2.2, 4.6, WOOD, doors='open')

# ------------------------------------------------------------------ 鐘楼
def bell_tower(B, ctx):
    cx, cy, L, W, yaw, _ = osm_frame(ctx, 466943458)
    z0 = ctx['G'](cx, cy)
    with Frame(B, cx, cy, z0, yaw):
        hb = 1.05
        slab(B, -3.75, -3.75, 3.75, 3.75, -0.3, hb, 'stone')
        prim.obox(B, (-3.8, -3.8, hb - 0.05), (3.8, -3.8, hb - 0.05), 0.16, 0.12, 'curb', tag='detail')
        slab(B, -4.3, -4.3, 4.3, 4.3, -0.3, 0.12, 'curb')
        block_rect(B, -4.0, -4.0, 4.0, 4.0, 0.0)
        a = 2.15; H = 3.9
        for sx in (-1, 1):
            for sy in (-1, 1):
                prim.cyl(B, (sx * (a + 0.12), sy * (a + 0.12), hb), (sx * a, sy * a, hb + H), 0.22, 0.2, 12, VERM)
                prim.cyl(B, (sx * (a + 0.12), sy * (a + 0.12), hb - 0.02), (sx * (a + 0.12), sy * (a + 0.12), hb + 0.1), 0.3, 0.28, 8, 'stone', tag='detail')
        for zz, h in ((hb + 0.5, 0.22), (hb + 2.4, 0.22), (hb + H - 0.12, 0.26)):
            for (p0, p1) in (((-a - 0.4, -a), (a + 0.4, -a)), ((-a - 0.4, a), (a + 0.4, a)), ((-a, -a - 0.4), (-a, a + 0.4)), ((a, -a - 0.4), (a, a + 0.4))):
                prim.obox(B, (*p0, zz), (*p1, zz), 0.18, h, VERM)
        # wooden fence between the lower ties
        for (p0, p1) in (((-a, -a), (a, -a)), ((-a, a), (a, a)), ((-a, -a), (-a, a)), ((a, -a), (a, a))):
            p0 = np.array(p0); p1 = np.array(p1)
            for t in np.linspace(0.08, 0.92, 15):
                q = p0 + (p1 - p0) * t
                prim.obox(B, (*q, hb), (*q, hb + 1.4), 0.07, 0.03, WOOD, tag='detail', up=(*(p1 - p0) / np.linalg.norm(p1 - p0), 0))
        # the bell on a beam
        prim.obox(B, (-a, 0, hb + H - 0.5), (a, 0, hb + H - 0.5), 0.26, 0.3, VERM)
        prim.lathe(B, (0, 0, hb + 1.3), [(0.78, 0.0), (0.8, 0.08), (0.72, 0.4), (0.68, 1.0), (0.66, 1.45), (0.55, 1.62), (0.25, 1.7), (0.12, 1.85), (0.0, 1.9)], 16, 'bronze')
        prim.obox(B, (0, 0, hb + 3.2), (0, 0, hb + H - 0.62), 0.1, 0.1, 'metal_dark', tag='detail')
        prim.cyl(B, (-1.6, 0.0, hb + 1.95), (-0.85, 0.0, hb + 1.95), 0.14, None, 10, 'wood_natural', tag='detail')        # 撞木
        top, reach = arch.bracket_row(B, 2 * a, 2 * a, hb + H, 'demitsudo', 0.85, VERM, 'white_paint')
        jroof.roof(B, 2 * a + 2 * reach, 2 * a + 2 * reach, top + 0.35, 1.55, kind='irimoya', cover='hongawara', pitch=0.7, rafter=0.26,
                   rafter_mat=VERM, rafter_end='white_paint', ridge_h=0.55, ridge_w=0.5, ends='oni', sori=0.4, gable_frac=0.5)

# ------------------------------------------------------------------ 手水舎 / 夜泣泉
def chozuya(B, ctx):
    cx, cy, L, W, yaw, _ = osm_frame(ctx, 466943456)
    z0 = ctx['G'](cx, cy)
    with Frame(B, cx, cy, z0, yaw):
        slab(B, -3.6, -3.0, 3.6, 3.0, -0.2, 0.08, 'stone')
        P.walk_rect(B, -3.6, -3.0, 3.6, 3.0, 0.08)
        a, b, H = 2.0, 1.55, 3.0
        for sx in (-1, 1):
            for sy in (-1, 1):
                prim.cyl(B, (sx * a, sy * b, 0.08), (sx * a, sy * b, H), 0.17, 0.16, 12, 'wood_natural')
                block_rect(B, sx * a - 0.3, sy * b - 0.3, sx * a + 0.3, sy * b + 0.3, 0.0)
        for sy in (-1, 1):
            prim.obox(B, (-a - 0.5, sy * b, H - 0.15), (a + 0.5, sy * b, H - 0.15), 0.2, 0.3, 'wood_natural')
        for sx in (-1, 1):
            P.arch_beam(B, (sx * a, -b - 0.3), (sx * a, b + 0.3), H - 0.55, 0.18, 0.3, 0.08, mat='wood_natural')
        jroof.roof(B, 2 * a + 0.4, 2 * b + 0.4, H + 0.35, 1.0, kind='kirizuma', cover='hongawara', pitch=0.55, verge=0.7, rafter=0.3, tiers=1,
                   rafter_mat='wood_natural', rafter_end='white_paint', ridge_h=0.5, ridge_w=0.45, ends='oni', sori=0.0)
        # 夜泣泉: the spring basin (a stone trough with water), bamboo pipe, ladles; three Jizō with red bibs behind
        slab(B, -1.5, -0.6, 1.5, 0.6, 0.08, 0.72, 'stone')
        slab(B, -1.32, -0.42, 1.32, 0.42, 0.62, 0.66, 'water')
        prim.cyl(B, (-1.4, 0.2, 0.95), (1.4, 0.2, 0.95), 0.05, None, 8, 'bamboo', tag='detail')
        for x in np.linspace(-1.0, 1.0, 5):
            prim.cyl(B, (x, 0.2, 0.95), (x, 0.0, 0.85), 0.03, None, 6, 'bamboo', tag='detail')
        for j, x in enumerate((-0.9, 0.0, 0.9)):
            yb = 1.0
            prim.rock(B, (x, yb, 0.35), 0.38, 30 + j, 'stone', flat=1.6)
            prim.lathe(B, (x, yb - 0.05, 0.45), [(0.3, 0.0), (0.33, 0.25), (0.22, 0.42), (0.0, 0.45)], 8, 'cloth', c0=(200, 30, 25, 0), tag='detail')
            prim.lathe(B, (x, yb, 0.85), [(0.0, 0.0), (0.18, 0.05), (0.2, 0.2), (0.14, 0.35), (0.0, 0.4)], 8, 'stone', tag='detail')
        block_rect(B, -1.6, -0.7, 1.6, 1.5, 0.08)

# ------------------------------------------------------------------ minor buildings
def minor_buildings(B, ctx):
    S, G = ctx['S'], ctx['G']
    # 久勢稲荷大明神: a small vermilion shrine with a torii in front
    cx, cy, L, W, yaw, _ = osm_frame(ctx, 466943467)
    z0 = G(cx, cy)
    with Frame(B, cx, cy, z0, yaw):
        P.small_hall(B, 4.4, 3.6, 2.5, kind='kirizuma', cover='hongawara', o=1.1, wood=VERM, pitch=0.62, base=0.35, nu=2, nv=1,
                     bracket='funa', rafter_mat=VERM, rafter_end='white_paint', front='karado', ridge_h=0.45)
        block_rect(B, -2.4, -2.0, 2.4, 2.0, 0.0)
    # torii on the east side of the shrine (toward the hall)
    Ur, Vr = ctx['Ur'], ctx['Vr']
    tp = np.array([cx, cy]) - Vr * 6.0
    arch.torii(B, tp[0], tp[1], G(*tp), ctx['yaw'], h=3.4, span=2.6)
    # two plain halls in the south-west and west parts of the precinct
    for bid, (Lb, Db, H, kind) in ((466943465, (10.6, 6.6, 3.5, 'irimoya')), (466943466, (5.0, 3.4, 2.8, 'kirizuma'))):
        cx, cy, L, W, yaw, _ = osm_frame(ctx, bid)
        z0 = G(cx, cy)
        with Frame(B, cx, cy, z0, yaw):
            P.small_hall(B, Lb, Db, H, kind=kind, cover='hongawara', o=1.3, wood=WOOD, pitch=0.6, base=0.4, bracket='funa', ridge_h=0.55)
            block_rect(B, -Lb / 2 - 0.2, -Db / 2 - 0.2, Lb / 2 + 0.2, Db / 2 + 0.2, 0.0)

# ------------------------------------------------------------------ the reception wings north of the hall and the covered way to its north end
def reception(B, ctx):
    """普門閣 / 参進閣 area (modern, traditional style): OSM way 99185523 wraps the hall's north-west corner, so it is
    replaced by two simple wings clear of the hall, and the roofed walkway (参拝入口) to the hall's north veranda"""
    R, G = ctx['R'], ctx['G']
    for (u0, u1, v0, v1, H) in ((67.0, 84.0, 0.6, 16.6, 4.0), (50.6, 76.6, 18.2, 26.9, 3.6)):
        c = R((u0 + u1) / 2, (v0 + v1) / 2)
        z0 = min(G(*R(u, v)) for u in (u0, u1) for v in (v0, v1))
        with Frame(B, c[0], c[1], z0, ctx['yaw']):
            Lb, Db = u1 - u0 - 1.6, v1 - v0 - 1.6
            P.small_hall(B, Lb, Db, H, kind='irimoya', cover='hongawara', o=1.5, wood=WOOD, pitch=0.62, base=0.3, bracket='funa', ridge_h=0.6)
            block_rect(B, -Lb / 2 - 0.2, -Db / 2 - 0.2, Lb / 2 + 0.2, Db / 2 + 0.2, 0.0)
    # covered walkway from the hall's north veranda (east bay) to the building north of it
    a = R(64.4, -3.9); b = R(84.0, -3.9)
    d = b - a; Lw = float(np.linalg.norm(d)); yw = math.atan2(d[1], d[0]); m = (a + b) / 2
    z0 = max(G(*a), G(*b)) + 0.1
    with Frame(B, m[0], m[1], z0, yw):
        slab(B, -Lw / 2, -1.6, Lw / 2, 1.6, -0.6, 0.0, 'stone')
        P.walk_rect(B, -Lw / 2, -1.6, Lw / 2, 1.6, 0.0)
        us = np.linspace(-Lw / 2 + 0.3, Lw / 2 - 0.3, int(Lw / 2.7) + 1)
        for u in us:
            for v in (-1.35, 1.35):
                prim.cyl(B, (u, v, 0.0), (u, v, 2.75), 0.12, None, 10, WOOD)
        for v in (-1.35, 1.35):
            prim.obox(B, (us[0] - 0.3, v, 2.68), (us[-1] + 0.3, v, 2.68), 0.18, 0.22, WOOD)
        for u in us:
            prim.obox(B, (u, -1.6, 2.6), (u, 1.6, 2.6), 0.16, 0.2, WOOD)
        jroof.roof(B, Lw, 2.9, 3.05, 0.75, kind='kirizuma', cover='sangawara', pitch=0.42, verge=0.3, rafter=0.45, tiers=1,
                   rafter_mat=WOOD, rafter_end=WOOD, ridge_h=0.3, ridge_w=0.35, ends=None, sori=0.0, edge=0.2)

# ------------------------------------------------------------------ ponds (east garden, 中根金作 1961)
POND_IDS = (466943457, -6890915)

def pond_rings(S):
    out = []
    for w in S.osm['water']:
        if w['id'] in POND_IDS:
            out.append(np.asarray(w['poly'][0][0], float))
    return out

def ponds(B, ctx):
    S, G = ctx['S'], ctx['G']
    for k, ring in enumerate(pond_rings(S)):
        poly = Polygon(ring).buffer(0)
        outer = poly.buffer(1.2)
        shore = [G(x, y) for (x, y) in np.asarray(poly.exterior.coords)]
        zw = min(shore) - 0.3                                       # water level
        # basin: a ground mesh over the buffered pond, deepening inward
        x0, y0, x1, y1 = outer.bounds
        res = 0.6
        xs = np.arange(x0, x1 + res, res); ys = np.arange(y0, y1 + res, res)
        X, Y = np.meshgrid(xs, ys)
        inside = shapely.contains_xy(outer.buffer(res), X, Y)
        dist = np.array([[poly.exterior.distance(Point(x, y)) * (1 if poly.contains(Point(x, y)) else -1) for x in xs] for y in ys])
        Zg = S.ground(X, Y)
        depth = np.clip((dist + 0.3) / 1.5, 0, 1)
        Z = np.where(dist > -1.2, np.minimum(Zg, zw + 0.25) - 0.9 * depth ** 0.7, Zg)
        Z = np.where(dist < -0.8, Zg - 0.02, Z)
        V3 = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1); nx = len(xs); I = []
        for j in range(len(ys) - 1):
            for i in range(nx - 1):
                if inside[j, i] and inside[j, i + 1] and inside[j + 1, i] and inside[j + 1, i + 1]:
                    a = j * nx + i
                    I += [[a, a + 1, a + nx + 1], [a, a + nx + 1, a + nx]]
        SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed']
        B.add(V3, I, 'ground', UV=V3[:, :2], smooth=True, c1=(0, 0, 0, SURF.index('riverbed')))
        S.cut.append([list(map(float, p)) for p in np.asarray(outer.exterior.coords)])
        # water surface
        prim.polygon(B, np.asarray(poly.exterior.coords)[:-1], zw, 'water')
        # the walk map: water is not walkable -> blocker over the pond
        prim.polygon(B, np.asarray(poly.buffer(-0.2).exterior.coords)[:-1], zw, 'stone', tag='block')
        # shore stones (護岸石組) and a few standing stones, an island of stones in the larger pond
        rng = np.random.default_rng(11 + k)
        Ls = poly.exterior.length
        for t in np.arange(0, Ls, 1.15):
            p = poly.exterior.interpolate(t + rng.uniform(-0.3, 0.3))
            sz = rng.uniform(0.35, 0.75)
            prim.rock(B, (p.x, p.y, max(zw + 0.15, G(p.x, p.y) - 0.1)), sz, int(rng.integers(1e6)), 'stone', flat=rng.uniform(0.45, 0.8))
        for _ in range(5):
            t = rng.uniform(0, Ls); p = poly.exterior.interpolate(t)
            prim.rock(B, (p.x, p.y, G(p.x, p.y) + 0.2), rng.uniform(0.7, 1.1), int(rng.integers(1e6)), 'stone', flat=1.3)
        if poly.area > 200:
            c = poly.centroid
            isl = Point(c.x, c.y).buffer(2.4)
            for t in np.arange(0, isl.exterior.length, 1.0):
                p = isl.exterior.interpolate(t)
                prim.rock(B, (p.x, p.y, zw + 0.2), rng.uniform(0.4, 0.7), int(rng.integers(1e6)), 'stone', flat=0.7)
            prim.polygon(B, np.asarray(isl.buffer(-0.3).exterior.coords)[:-1], zw + 0.45, 'moss_mound')
            B.tree('matsu', c.x, c.y, zw + 0.45, 0.8, 0.6)
            B.tree('tsutsuji', c.x + 1.2, c.y - 0.8, zw + 0.45, 0.8, 0.0)
        # a stone slab bridge across the narrow part of the south pond
        if k == 0:
            R = ctx['R']
            a = R(-36.0, -33.0); b = R(-36.2, -37.8)
            d = b - a; Lb = float(np.linalg.norm(d)); yw = math.atan2(d[1], d[0])
            with Frame(B, *(a + b) / 2, zw + 0.3, yw):
                slab(B, -Lb / 2 - 0.4, -0.55, Lb / 2 + 0.4, 0.55, 0.0, 0.22, 'stone')

# ------------------------------------------------------------------ precinct walls
def walls(B, ctx):
    S, G = ctx['S'], ctx['G']
    for b in S.osm['barriers']:
        if b['id'] not in (466943469, 466943460, 466943461, 466943462): continue
        for ln in b.get('line', []):
            pts = [np.asarray(p, float) for p in ln]
            arch.tsuiji(B, pts, 0.0, h=2.5, th=0.75, ground=G)
            for a, c in zip(pts[:-1], pts[1:]):
                block_line(B, [a, c], G(*(a + c) / 2), 1.0)

# ------------------------------------------------------------------ paths, gravel, garden beds (S.paint)
def paths_and_paint(B, ctx, O, zfl, U, V):
    S, R, G = ctx['S'], ctx['R'], ctx['G']
    prec = Polygon(S.polygon[0][0] if isinstance(S.polygon[0][0][0], (list, tuple)) else S.polygon[0])
    south = Polygon([R(-140, -80), R(47, -80), R(47, 80), R(-140, 80)])
    ground_area = prec.intersection(south)
    def add(poly, surf):
        if poly.is_empty: return
        for p in (poly.geoms if hasattr(poly, 'geoms') else [poly]):
            if p.geom_type == 'Polygon' and p.area > 0.5:
                S.paint.append({'poly': [list(map(float, q)) for q in np.asarray(p.exterior.coords)], 'surf': surf})
    add(ground_area, 'gravel')
    # garden beds round the ponds and along the galleries (moss / grass)
    beds = shapely.unary_union([Polygon(r).buffer(7.0) for r in pond_rings(S)] + [Polygon([R(12, -36), R(74, -36), R(74, -44.5), R(12, -44.5)]),
                                                                                 Polygon([R(-68, -24), R(-12, -24), R(-12, -43.5), R(-68, -43.5)])])
    keep_clear = shapely.unary_union([Polygon([R(-14, -36), R(16, -36), R(16, -14), R(-14, -14)])])
    add(beds.difference(keep_clear), 'moss')
    # stone paths: east gate -> 向拝 steps; along the front of the hall; to the bell tower and the 手水舎; north entrance
    def path(pts, w, surf='stone_slab', curb=True):
        ln = LineString([R(*p) for p in pts])
        add(ln.buffer(w / 2, cap_style='flat', join_style='mitre'), surf)
        if curb:
            for s in (-1, 1):
                off = ln.offset_curve(s * w / 2)
                cs = np.asarray(off.coords)
                for a, c in zip(cs[:-1], cs[1:]):
                    d = c - a; Ld = np.linalg.norm(d)
                    if Ld < 0.3: continue
                    for t0 in np.arange(0, Ld, 2.0):
                        t1 = min(Ld, t0 + 2.0)
                        q0 = a + d * t0 / Ld; q1 = a + d * t1 / Ld
                        z = G(*(q0 + q1) / 2)
                        prim.obox(B, (*q0, z + 0.02), (*q1, z + 0.02), 0.16, 0.12, 'curb', tag='detail')
    path([(0.9, -38.7), (0.9, -17.6)], 3.6)
    path([(-55.0, -18.0), (55.0, -18.0)], 2.4, curb=False)
    path([(18.6, -20.5), (18.6, -26.4)], 2.0, curb=False)
    path([(-56.4, -18.0), (-56.4, -28.8)], 2.0, curb=False)
    path([(62.0, -18.0), (78.0, -18.0), (78.0, -44.0)], 2.4, curb=False)

# ------------------------------------------------------------------ trees
def trees(B, ctx):
    S, R, G = ctx['S'], ctx['R'], ctx['G']
    hall = Polygon([R(-64, -16), R(64, -16), R(64, 16), R(-64, 16)])
    pondu = shapely.unary_union([Polygon(r).buffer(0.8) for r in pond_rings(S)])
    rng = np.random.default_rng(7)
    def inv(p):
        d = np.asarray(p, float) - np.array(R(0, 0)); return float(d @ ctx['Ur']), float(d @ ctx['Vr'])
    planted = []
    def plant(sp, x, y, sc=1.0):
        if hall.contains(Point(x, y)) or pondu.contains(Point(x, y)): return
        for (px, py) in planted:
            if (px - x) ** 2 + (py - y) ** 2 < 4.0: return
        planted.append((x, y))
        B.tree(sp, float(x), float(y), G(x, y), sc, float(rng.uniform(0, 2 * math.pi)))
    # OSM trees inside the modelled part of the precinct, species by zone
    for t in S.osm['trees']:
        x, y = t['xy']; u, v = inv((x, y))
        if not (-100 < u < 47 and -46 < v < 52): continue
        if v < -12:            # east garden
            sp = rng.choice(['matsu', 'momiji', 'matsu', 'sakura', 'momiji', 'kashi'])
        elif v > 30:           # along the west wall: big trees
            sp = rng.choice(['keyaki', 'kashi', 'keyaki', 'matsu'])
        else:
            sp = rng.choice(['matsu', 'sakura', 'momiji'])
        plant(sp, x, y, float(rng.uniform(0.85, 1.2)))
    # the garden round the ponds: pines, maples, azalea clumps, a weeping cherry or two
    for ring in pond_rings(S):
        poly = Polygon(ring)
        ext = poly.buffer(3.0).exterior
        for t in np.arange(0, ext.length, 3.2):
            p = ext.interpolate(t + rng.uniform(-0.6, 0.6))
            sp = rng.choice(['tsutsuji', 'tsutsuji', 'matsu', 'momiji', 'tsutsuji'])
            plant(sp, p.x, p.y, float(rng.uniform(0.7, 1.1)))
        ext2 = poly.buffer(6.5).exterior
        for t in np.arange(0, ext2.length, 6.0):
            p = ext2.interpolate(t + rng.uniform(-1, 1))
            plant(rng.choice(['momiji', 'matsu', 'sakura', 'keyaki']), p.x, p.y, float(rng.uniform(0.9, 1.25)))
    # pines along the front court and by the galleries (the photographs show trained black pines)
    for u in (-40, -26, 26, 40, 52):
        p = R(u, -26.0 + rng.uniform(-2, 2)); plant('matsu', p[0], p[1], 1.0)
    for u in np.arange(-62, 72, 9.0):
        p = R(u + rng.uniform(-2, 2), -40.5); plant(rng.choice(['matsu', 'sakura', 'momiji']), p[0], p[1], 0.95)
    # weeping cherries flanking the east gate (seen in spring photographs)
    for u in (-9.5, 11.5):
        p = R(u, -35.5); plant('sakura', p[0], p[1], 1.1)
    # the west side: big trees along the wall, the 通し矢 court kept open
    for u in np.arange(-92, 48, 8.5):
        p = R(u + rng.uniform(-2, 2), 47.0 + rng.uniform(-1.5, 1.5)); plant(rng.choice(['keyaki', 'kashi', 'matsu', 'sakura']), p[0], p[1], float(rng.uniform(1.0, 1.35)))
    # south: pines and cherries between the hall and the 太閤塀
    for u in np.arange(-88, -68, 6.0):
        for v in (-30, -12, 8, 28):
            p = R(u + rng.uniform(-1.5, 1.5), v + rng.uniform(-3, 3)); plant(rng.choice(['matsu', 'sakura', 'momiji', 'kashi']), p[0], p[1], 1.0)

# ------------------------------------------------------------------ site edits
def edits(S, ctx):
    R = ctx['R']
    prec = Polygon(S.polygon[0][0] if isinstance(S.polygon[0][0][0], (list, tuple)) else S.polygon[0])
    south = Polygon([R(-140, -80), R(47, -80), R(47, 80), R(-140, 80)])
    ex = [prec.intersection(south)]
    for bid in (510791010, 466943459, 99185534, 99185517, 510791012, 99185523):
        b = S.osm_building(bid)
        ex.append(Polygon(b['poly'][0][0]).buffer(1.0))
    g = shapely.unary_union(ex)
    for p in (g.geoms if hasattr(g, 'geoms') else [g]):
        S.exclude.append([list(map(float, q)) for q in np.asarray(p.exterior.coords)])
