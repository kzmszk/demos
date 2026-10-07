"""東福寺 halls: 本堂 (仏殿兼法堂, 1934: 裳階付 入母屋, 本屋三手先・裳階出組, 7 x 5 bays outside), 方丈 (1890; verandas, 庇 +
入母屋 with a 木連格子 gable), 恩賜門 / 西唐門 (平唐門), 庫裏 (1910: 切妻 gable to the west, 唐破風 porch), 禅堂 (1347: 単層裳階付
切妻造), 東司, 経蔵 (裳階 + 宝形), 浴室, 鐘楼, the gates 日下門 / 六波羅門 / 勅使門 / 月下門, garden walls.
Frames on the precinct grid (L.ROT); front = v- unless stated."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon
import jk
from jk import prim, arch, Frame
from jk import roof as jroof
from sites import tofukuji_lib as L
from sites import tofukuji_klib as K
from sites import tofukuji_ekit as EK

WD = 'wood_dark'
HOJO_FLOOR = 50.75

def mid_insert(xs):
    out = []
    for a, b in zip(xs[:-1], xs[1:]): out += [a, (a + b) / 2]
    return np.array(out + [xs[-1]])

def bays(widths):
    xs = np.r_[0, np.cumsum(widths)]; return xs - xs[-1] / 2

def sides_pts(us, vs):
    return {0: [(x, vs[0]) for x in us], 1: [(us[-1], y) for y in vs], 2: [(x, vs[-1]) for x in us[::-1]], 3: [(us[0], y) for y in vs[::-1]]}

def pillars(B, us, vs, z0, z1, r, round_=True, base=True, inner=False):
    pts = set()
    for x in us: pts.add((round(float(x), 4), round(float(vs[0]), 4))); pts.add((round(float(x), 4), round(float(vs[-1]), 4)))
    for y in vs: pts.add((round(float(us[0]), 4), round(float(y), 4))); pts.add((round(float(us[-1]), 4), round(float(y), 4)))
    if inner:
        for x in us:
            for y in vs: pts.add((round(float(x), 4), round(float(y), 4)))
    for (x, y) in pts:
        if base: prim.cyl(B, (x, y, z0 - 0.05), (x, y, z0 + 0.14), r * 1.5, r * 1.38, 10, 'stone', tag='detail')
        if round_: prim.cyl(B, (x, y, z0 + 0.1), (x, y, z1), r, r * 0.97, 12, WD, caps=(False, True))
        else: prim.box(B, x - r, y - r, z0, x + r, y + r, z1, WD)

def walls(B, us, vs, z0, z1, kinds, r=0.25, mat=WD):
    """kinds: {side: [kind per bay] or kind}"""
    sp = sides_pts(us, vs)
    for k, kd in kinds.items():
        pts = sp[k]
        for i in range(len(pts) - 1):
            kk = kd[i] if isinstance(kd, (list, tuple)) else kd
            if kk in (None, 'open'): continue
            EK.infill(B, pts[i], pts[i + 1], z0, z1, kk, mat=mat, r=r, seed=i + 5 * k)

def block_sides(B, us, vs, sides=(0, 1, 2, 3), gaps=()):
    sp = sides_pts(us, vs)
    for k in sides:
        a, b = sp[k][0], sp[k][-1]
        K.block_line(B, [a, b], w=0.5)

def gable_slats(B, R, u_g, zb, step=0.18, mat=WD):
    """木連格子 on the gable walls of a kit roof (irimoya / kirizuma) at u = ±u_g: vertical slats + a few rails"""
    c = R.c
    for su in (-1, 1):
        u = su * (u_g + 0.04)
        for y in np.arange(-c + 0.6, c - 0.6, step):
            s = c - abs(y)
            zt = float(R.z(s, c)) - R.edge - 0.12
            if zt - zb < 0.3: continue
            prim.obox(B, (u, y, zb), (u, y, zt), 0.04, 0.03, mat, tag='detail', ends=False)
        for zz in np.arange(zb + 0.3, float(R.z(c, c)) - 0.6, 0.6):
            ys = [y for y in np.linspace(-c, c, 200) if float(R.z(c - abs(y), c)) - R.edge - 0.12 > zz]
            if len(ys) < 2: continue
            prim.obox(B, (u, ys[0], zz), (u, ys[-1], zz), 0.04, 0.035, mat, tag='detail', ends=False)

# ====================================================================== 本堂
def hondo(B, S):
    loc = L.Loc(1370.0, -1048.9, L.ROT)
    us = bays([4.2, 4.6, 5.2, 6.4, 5.2, 4.6, 4.2]); vs = bays([3.9, 4.8, 6.1, 4.8, 3.9])
    ui, vi = us[1:-1], vs[1:-1]                     # 身舎
    ZG = 49.0; ZF = 50.2
    with loc.frame(B):
        # 基壇 with front / back / side steps
        pa, pc = us[-1] + 2.4, vs[-1] + 2.4
        prim.box(B, -pa, -pc, ZG - 0.5, pa, pc, ZF, 'stone', c1=(0, 3, 0, 0))
        prim.box(B, -pa - 0.1, -pc - 0.1, ZF - 0.12, pa + 0.1, pc + 0.1, ZF + 0.02, 'curb', faces='xXyYZ')
        L.poly_flat(B, [(-pa, -pc), (pa, -pc), (pa, pc), (-pa, pc)], ZF, 'stone', tag='walk')
        K.steps(B, (0, -pc - 2.2), (0, -pc), ZG, ZF, 9.5, mat='stone', riser=0.17, cheek=0.5)
        for su in (-1, 1):
            K.steps(B, (su * (pa + 1.6), 0.0), (su * pa, 0.0), ZG, ZF, 3.0, mat='stone', riser=0.17)
        # 裳階 and 身舎 pillars (round, large)
        zm = ZF + 4.9                                   # 裳階 pillar top
        pillars(B, us, vs, ZF, zm, 0.3)
        zb = ZF + 13.0                                  # 身舎 pillar top
        pillars(B, ui, vi, ZF, zb, 0.42)
        # 裳階 walls: front doors (center lattice), sides doors + windows, back boards; white 小壁 above
        front = ['karado', 'karado', 'karado', 'koshi', 'karado', 'karado', 'karado']
        walls(B, us, vs, ZF + 0.08, ZF + 3.55, {0: front, 2: 'board', 1: ['board', 'karado', 'renji', 'karado', 'board'], 3: ['board', 'karado', 'renji', 'karado', 'board']}, r=0.3)
        walls(B, us, vs, ZF + 3.75, zm - 0.3, {0: 'white', 1: 'white', 2: 'white', 3: 'white'}, r=0.3)
        Lm, Dm = us[-1] - us[0], vs[-1] - vs[0]
        arch.nageshi(B, Lm, Dm, ZF + 3.7, WD, h=0.26, w=0.12, out=0.32)
        arch.nageshi(B, Lm, Dm, zm, WD, h=0.36, w=0.24, out=0.0)
        arch.nageshi(B, Lm, Dm, ZF + 0.3, WD, h=0.2, w=0.12, out=0.32)
        # 裳階 brackets (出組, 詰組 also between the pillars) and its ring roof
        top_m, reach_m = arch.bracket_row(B, Lm, Dm, zm, 'degumi', 0.85, WD, 'white_paint', us=mid_insert(us), vs=mid_insert(vs))
        o_m = 4.0
        Rm = L.RingRoof(Lm, Dm, 0.0, o_m, truncate=o_m + 3.85, rise=4.1, cover='hongawara', sori=0.55, sori_len=0.4, edge=0.34, rafter=0.26,
                        rafter_mat=WD, rafter_end='white_paint', tiers=2, ends='oni', teri=1.25)
        Rm.zE0 = ZF + 5.25
        Rm.build(B)
        K.soffit_ring(B, 0, 0, Lm / 2, Dm / 2, reach_m + 0.2, top_m + 0.12, 'wood_dark')
        # 身舎 walls above the 裳階 roof: boards with a 連子 band, 長押
        Li, Di = ui[-1] - ui[0], vi[-1] - vi[0]
        zr_m = Rm.zE0 + 4.1
        walls(B, ui, vi, zr_m - 0.6, zb - 1.3, {k: 'board' for k in range(4)}, r=0.42)
        walls(B, ui, vi, zb - 1.25, zb - 0.35, {k: 'renji' for k in range(4)}, r=0.42)
        arch.nageshi(B, Li, Di, zb, WD, h=0.4, w=0.26, out=0.0)
        arch.nageshi(B, Li, Di, zb - 1.3, WD, h=0.24, w=0.14, out=0.42)
        # 扁額 on the front
        prim.box(B, -1.1, vi[0] - 0.5, zb - 3.4, 1.1, vi[0] - 0.42, zb - 1.5, WD)
        prim.box(B, -0.9, vi[0] - 0.53, zb - 3.2, 0.9, vi[0] - 0.5, zb - 1.7, 'gold', tag='detail')
        # 三手先 brackets with 詰組
        top_b, reach_b = arch.bracket_row(B, Li, Di, zb, 'mitesaki', 1.15, WD, 'white_paint', us=mid_insert(ui), vs=mid_insert(vi))
        K.soffit_ring(B, 0, 0, Li / 2, Di / 2, reach_b + 0.2, top_b + 0.1, 'wood_dark')
        # main 入母屋 roof (ridge to PLATEAU 72.8)
        o_b = 4.7; cb = Di / 2 + o_b
        zE_b = ZF + 14.1; zR = 71.35
        Rb = jroof.Roof(Li, Di, 0.0, o_b, kind='irimoya', cover='hongawara', pitch=(zR - zE_b) / cb, teri=1.5, sori=0.8, sori_len=0.4,
                        gable_frac=0.45, verge=1.0, edge=0.42, rafter=0.27, rafter_mat=WD, rafter_end='white_paint', tiers=2, ends='oni',
                        ridge_h=1.35, ridge_w=1.0, gable_wall='wood_dark')
        Rb.zE0 = zE_b
        rb = Rb.build(B)
        gable_slats(B, Rb, Rb.a - Rb.sg + Rb.verge * 0.3, rb['z_break'] + 0.4)
        # blockers (walls), lanterns
        block_sides(B, us, vs)
        for su in (-1, 1):
            EK.lantern(B, su * 6.2, -pc - 4.5, ZG, h=2.6)
    return dict(loc=loc)

# ====================================================================== 方丈
HOJO_C = (1395.6, -972.15)
HOJO_L, HOJO_D = 31.2, 17.6
HOJO_VER = 1.65

def hojo(B, S):
    loc = L.Loc(HOJO_C[0], HOJO_C[1], L.ROT)
    us = np.linspace(-HOJO_L / 2, HOJO_L / 2, 17); vs = np.linspace(-HOJO_D / 2, HOJO_D / 2, 10)
    ZF = HOJO_FLOOR
    a, c = HOJO_L / 2, HOJO_D / 2
    w = HOJO_VER
    with loc.frame(B):
        # floor platform (dark skirt), square pillars, walls
        prim.box(B, -a, -c, ZF - 0.95, a, c, ZF, 'wood_dark', faces='xXyYZ')
        prim.box(B, -a + 0.05, -c + 0.05, ZF - 0.02, a - 0.05, c - 0.05, ZF, 'tatami', faces='Z')
        zt = ZF + 3.15
        pillars(B, us, vs, ZF - 0.95, zt, 0.13, round_=False, base=True)
        walls(B, us, vs, ZF + 0.03, ZF + 1.95, {0: 'maira', 1: 'maira', 2: ['maira', 'shoji'] * 8, 3: 'maira'}, r=0.13)
        walls(B, us, vs, ZF + 2.15, zt - 0.2, {0: 'white', 1: 'white', 2: 'white', 3: 'white'}, r=0.13)
        arch.nageshi(B, HOJO_L, HOJO_D, ZF + 2.08, WD, h=0.2, w=0.1, out=0.16)
        arch.nageshi(B, HOJO_L, HOJO_D, zt, WD, h=0.3, w=0.2, out=0.0)
        # verandas (縁) all round with posts, a low railing on the south / east / west, steps to the gardens
        rng = np.random.default_rng(6)
        zv = ZF - 0.05
        for (x0, y0, x1, y1, along) in ((-a - w, -c - w, a + w, -c, 'u'), (-a - w, c, a + w, c + w, 'u'), (-a - w, -c, -a, c, 'v'), (a, -c, a + w, c, 'v')):
            if along == 'u':
                for y in np.arange(y0, y1 - 1e-6, 0.3):
                    prim.box(B, x0, y + 0.004, zv - 0.06, x1, min(y + 0.3, y1) - 0.004, zv, 'wood_natural', faces='Z', c1=(0, 0, int(rng.integers(255)), 0))
            else:
                for x in np.arange(x0, x1 - 1e-6, 0.3):
                    prim.box(B, x + 0.004, y0, zv - 0.06, min(x + 0.3, x1) - 0.004, y1, zv, 'wood_natural', faces='Z', c1=(0, 0, int(rng.integers(255)), 0))
            prim.box(B, x0, y0, zv - 0.24, x1, y1, zv - 0.06, 'wood_dark', faces='xXyYz')
        K.walk_poly(B, [(-a - w, -c - w), (a + w, -c - w), (a + w, c + w), (-a - w, c + w)], zv)
        for t in np.linspace(-a - w + 0.1, a + w - 0.1, 18):
            for yy in (-c - w + 0.1, c + w - 0.1):
                zg = loc.g(S, t, yy)
                prim.box(B, t - 0.07, yy - 0.07, zg - 0.1, t + 0.07, yy + 0.07, zv - 0.24, WD, tag='detail')
        # railing south (gap for the steps), steps down to the south garden at the centre
        K.rail_line(B, [(-a - w + 0.1, -c - w + 0.12), (-2.2, -c - w + 0.12)], zv, h=0.72, mat=WD, giboshi_at=(), post_every=1.95)
        K.rail_line(B, [(2.2, -c - w + 0.12), (a + w - 0.1, -c - w + 0.12)], zv, h=0.72, mat=WD, giboshi_at=(), post_every=1.95)
        K.block_line(B, [(-a - w + 0.1, -c - w + 0.12), (-2.2, -c - w + 0.12)], w=0.4)
        K.block_line(B, [(2.2, -c - w + 0.12), (a + w - 0.1, -c - w + 0.12)], w=0.4)
        zg_s = loc.g(S, 0, -c - w - 1.5)
        K.steps(B, (0, -c - w - 1.6), (0, -c - w), zg_s, zv, 3.6, mat='wood_natural', riser=0.18)
        # the 通天台 opening on the north side (gap) at u = HOJO 通天台 axis; elsewhere the garden edges block
        ut = L.Loc(*HOJO_C, L.ROT).l(1383.0, -957.0)[0]
        K.block_line(B, [(-a - w + 0.1, c + w - 0.1), (ut - 2.4, c + w - 0.1)], w=0.4)
        K.block_line(B, [(ut + 2.4, c + w - 0.1), (a + w - 0.1, c + w - 0.1)], w=0.4)
        K.block_line(B, [(-a - w + 0.1, -c - w + 0.1), (-a - w + 0.1, -6.2)], w=0.4)       # gap: steps from the 西唐門
        K.block_line(B, [(-a - w + 0.1, -3.8), (-a - w + 0.1, c + w - 0.1)], w=0.4)
        K.block_line(B, [(a + w - 0.1, -c - w + 0.1), (a + w - 0.1, c - 1.5)], w=0.4)
        block_sides(B, us, vs)
        # 舟肘木 on the pillars, 庇 ring roof, main 入母屋 roof with a 木連格子 gable
        for k, pts in sides_pts(us, vs).items():
            for (x, y) in pts:
                prim.obox(B, (x - (0.45 if k in (0, 2) else 0), y - (0.45 if k in (1, 3) else 0), zt + 0.08), (x + (0.45 if k in (0, 2) else 0), y + (0.45 if k in (1, 3) else 0), zt + 0.08), 0.16, 0.16, WD, tag='detail')
        o_h = 3.4
        Rh = L.RingRoof(HOJO_L, HOJO_D, 0.0, o_h, truncate=o_h + 2.3, rise=1.75, cover='hongawara', sori=0.3, sori_len=0.35, edge=0.3, rafter=0.3,
                        rafter_mat=WD, rafter_end='white_paint', tiers=1, ends='oni', teri=1.15)
        Rh.zE0 = ZF + 3.05
        Rh.build(B)
        L2, D2 = HOJO_L - 4.6, HOJO_D - 4.6
        zE2 = Rh.zE0 + 1.75 + 0.45
        walls(B, np.linspace(-L2 / 2, L2 / 2, 14), np.linspace(-D2 / 2, D2 / 2, 7), Rh.zE0 + 1.2, zE2 + 0.2, {k: 'board' for k in range(4)}, r=0.1)
        o2 = 1.7; c2 = D2 / 2 + o2
        zR = 61.6
        R2 = jroof.Roof(L2, D2, 0.0, o2, kind='irimoya', cover='hongawara', pitch=(zR - zE2) / c2, teri=1.3, sori=0.45, sori_len=0.35, gable_frac=0.32,
                        verge=0.9, edge=0.34, rafter=0.3, rafter_mat=WD, rafter_end='white_paint', tiers=1, ends='oni', ridge_h=1.05, ridge_w=0.85,
                        gable_wall='wood_natural')
        R2.zE0 = zE2
        r2 = R2.build(B)
        gable_slats(B, R2, R2.a - R2.sg, r2['z_break'] + 0.2, mat='wood_natural')
        for su in (-1, 1):                    # big 懸魚 on the gables
            u_ = su * (R2.a - R2.sg + R2.verge + 0.06)
            za = float(R2.z(R2.c, R2.c)) - 0.6
            P = np.array([(u_, y, za + z) for (y, z) in ((-0.8, 0.2), (0.8, 0.2), (0.6, -0.5), (0.25, -1.0), (0.0, -1.2), (-0.25, -1.0), (-0.6, -0.5))])
            L.oadd(B, P, [[0, i, i + 1] for i in range(1, len(P) - 1)], WD, (su, 0, 0), tag='detail')
    return dict(loc=loc, zv=zv, a=a, c=c, w=w)

# ====================================================================== 唐門 (恩賜門, 西唐門)
def karamon_gates(B, S):
    # 恩賜門: in the south wall of the 南庭, a 平唐門 (karahafu on its ends), cypress bark
    # (向唐門: the 唐破風 faces the garden and the forecourt; dark timber, a vermilion line under the bargeboard, cypress bark)
    loc = L.Loc(1395.3, -995.25, L.ROT)
    EK.karamon(B, S, loc, zg=float(S.ground(1395.3, -995.25)), span=3.2, depth=2.6, H=3.3, r=0.18, W=6.9, Dr=4.9, hump=1.45, mat=WD,
               trim='vermilion', cover='hiwada', doors=True, base=True, back=True, block=True)
    # 西唐門: west of the 方丈, facing the corridor (front = west)
    loc = L.Loc(1368.65, -977.4, L.ROT - math.pi / 2)
    L.hira_karamon(B, S, loc, zg=float(S.ground(1368.65, -977.4)), span=3.2, depth=2.4, H=3.15, r=0.16, W=7.5, Dr=4.9, hump=1.2, mat=WD, cover='hiwada', doors='open')

# ====================================================================== 方丈 - 庫裏 corridor
def hojo_kuri_corridor(B, S):
    """the covered corridor from the 方丈's south-east corner to the 庫裏 (the visitors' way into the 方丈)"""
    from sites import tofukuji_bridges as BR
    pts = np.array([(1413.6, -982.35), (1416.6, -982.5), (1416.2, -993.4)])
    z = HOJO_FLOOR - 0.05
    BR.corridor(B, S, pts, [z, z, z], w=2.6, h=2.6, rise=0.95, o=0.8, end_gables=(False, False), rail=False, skirt=True,
                cover='sangawara', floor_mat='wood_natural', seed=11)

# ====================================================================== garden walls round the 方丈
def hojo_walls(B, S):
    """白壁 with posts and tile coping: south (with the 恩賜門 gap), west and east ends of the 南庭, the 西庭 west wall"""
    W = lambda pts: L.post_wall(B, S, pts, h=2.45, th=0.34, post=1.98)
    loc = L.Loc(*HOJO_C, L.ROT)
    yS = -995.0
    pts = lambda P: [loc.w(*loc.l(*p)) for p in P]
    W([(1369.3, -993.0), (1391.3, -994.0)])
    W([(1399.4, -994.4), (1413.3, -995.0)])
    W([(1369.6, -992.8), (1370.3, -976.8)])
    W([(1370.5, -973.6), (1371.0, -959.4)])
    W([(1413.3, -995.0), (1413.9, -985.0)])

# ====================================================================== 庫裏
def kuri(B, S):
    loc = L.Loc(1425.9, -1007.3, L.ROT - math.pi / 2)        # u south, v east; front (v-) = west
    ZG = 50.0
    Lk, Dk = 19.6, 22.0                                       # gable width (u), depth (v)
    us = np.linspace(-Lk / 2, Lk / 2, 9); vs = np.linspace(-Dk / 2, Dk / 2, 9)
    with loc.frame(B):
        zf = ZG + 0.35
        prim.box(B, -Lk / 2 - 0.5, -Dk / 2 - 0.5, ZG - 0.3, Lk / 2 + 0.5, Dk / 2 + 0.5, zf, 'stone')
        zt = ZG + 7.4
        pillars(B, us, vs, zf, zt, 0.15, round_=False, base=False)
        # front (gable end): white plaster in a grid of dark posts and 貫, the 唐破風 porch; sides plaster + windows
        walls(B, us, vs, zf + 0.05, zf + 2.6, {0: ['koshi', 'white', 'white', 'maira', 'maira', 'white', 'renji', 'koshi'], 1: 'white', 2: 'white', 3: 'white'}, r=0.15)
        walls(B, us, vs, zf + 2.9, zt - 0.2, {0: 'white', 1: 'white', 2: 'white', 3: 'white'}, r=0.15)
        for zz in (zf + 2.75, zt - 2.0, zt):
            arch.nageshi(B, Lk, Dk, zz, WD, h=0.24, w=0.14, out=0.08)
        o = 1.4
        R = jroof.Roof(Dk, Lk, 0.0, o, kind='kirizuma', cover='hongawara', pitch=0.72, teri=1.2, sori=0.0, verge=1.5, edge=0.34, rafter=0.3,
                       rafter_mat=WD, rafter_end='white_paint', ends='oni', gable_wall='temple_wall', ridge_h=1.0, ridge_w=0.8)
        # the kit roof's ridge runs along its u: rotate it so the ridge runs along v (gables to the front / back)
        with Frame(B, 0, 0, 0, math.pi / 2):
            R.zE0 = zt + 0.35
            R.build(B)
            # gable timbers: 虹梁, 大瓶束 and a grid of posts / 貫 over the plaster on both gables
            for sg in (-1, 1):
                x = sg * (Dk / 2 + 0.07)
                zg0 = R.zE0 - 0.1
                for zz in (zg0 + 0.2, zg0 + 1.7, zg0 + 3.3, zg0 + 4.7):
                    ys = [y for y in np.linspace(-R.c, R.c, 160) if float(R.z(R.c - abs(y), R.a)) - R.edge - 0.15 > zz]
                    if len(ys) > 1: prim.obox(B, (x, ys[0], zz), (x, ys[-1], zz), 0.12, 0.28, WD, tag='detail')
                for y in np.linspace(-Lk / 2 + 2.45, Lk / 2 - 2.45, 7):
                    ztop = float(R.z(R.c - abs(y), R.a)) - R.edge - 0.15
                    if ztop > zg0 + 0.3: prim.obox(B, (x, y, zg0), (x, y, ztop), 0.12, 0.2, WD, tag='detail')
                prim.box(B, x - 0.06, -0.45, zg0 + 3.3, x + 0.06, 0.45, zg0 + 4.7, WD, tag='detail')
                # 懸魚
                za = float(R.z(R.c, R.a)) - 0.7
                P = np.array([(x + sg * 0.06, y, za + z) for (y, z) in ((-0.8, 0.2), (0.8, 0.2), (0.6, -0.5), (0.25, -1.0), (0.0, -1.2), (-0.25, -1.0), (-0.6, -0.5))])
                L.oadd(B, P, [[0, i, i + 1] for i in range(1, len(P) - 1)], 'white_paint', (sg, 0, 0), tag='detail')
        # lean-to roofs (庇) along the front and the two sides
        EK.pent(B, -Lk / 2, Lk / 2, -Dk / 2, zf + 3.2, 2.6, 0.9, post_u=list(np.linspace(-Lk / 2 + 1.2, Lk / 2 - 1.2, 6)), zg=ZG, cover='sangawara')
        K.block_poly(B, [(-Lk / 2, -Dk / 2), (Lk / 2, -Dk / 2), (Lk / 2, Dk / 2), (-Lk / 2, Dk / 2)])
    # 唐破風 porch at the centre of the front
    EK.karamon(B, S, L.Loc(*loc.w(0.0, -Dk / 2 - 2.4), loc.yaw), zg=ZG, span=3.0, depth=2.2, H=3.0, r=0.17, W=5.2, Dr=4.6, hump=1.1,
               mat=WD, trim=WD, cover='hongawara', doors=False, back=False, block=False)
    return dict(loc=loc)

# ====================================================================== 禅堂, 東司, 経蔵, 浴室, 鐘楼
def zendo(B, S):
    loc = L.Loc(1307.1, -1070.4, L.ROT + math.pi / 2)        # u north, v west; front (v-) = east
    ZG = 47.6; ZF = ZG + 0.45
    us = bays([2.96] * 14); vs = bays([3.27] * 9)               # 裳階 41.4 x 29.4
    ui, vi = us[1:-1], vs[1:-1]
    with loc.frame(B):
        pa, pc = us[-1] + 1.4, vs[-1] + 1.4
        prim.box(B, -pa, -pc, ZG - 0.4, pa, pc, ZF, 'stone', c1=(0, 3, 0, 0))
        L.poly_flat(B, [(-pa, -pc), (pa, -pc), (pa, pc), (-pa, pc)], ZF, 'stone', tag='walk')
        zm = ZF + 3.55
        pillars(B, us, vs, ZF, zm, 0.2, round_=False)
        wk = {0: ['white'] + ['katomado'] * 12 + ['white'], 2: ['white'] + ['katomado'] * 12 + ['white'], 1: ['white', 'katomado', 'katomado', 'white', 'karado', 'white', 'katomado', 'katomado', 'white'],
              3: ['white', 'katomado', 'katomado', 'white', 'karado', 'white', 'katomado', 'katomado', 'white']}
        walls(B, us, vs, ZF + 0.05, ZF + 2.7, wk, r=0.2)
        walls(B, us, vs, ZF + 2.9, zm - 0.2, {k: 'white' for k in range(4)}, r=0.2)
        Lm, Dm = us[-1] - us[0], vs[-1] - vs[0]
        for zz, hh in ((ZF + 2.8, 0.2), (zm, 0.3), (ZF + 0.25, 0.18)):
            arch.nageshi(B, Lm, Dm, zz, WD, h=hh, w=0.14, out=0.22)
        top_m, reach_m = arch.bracket_row(B, Lm, Dm, zm, 'demitsudo', 0.7, WD, 'white_paint', us=us, vs=vs)
        Rm = L.RingRoof(Lm, Dm, 0.0, 2.4, truncate=2.4 + 3.25, rise=1.7, cover='hongawara', sori=0.45, sori_len=0.35, edge=0.3, rafter=0.27,
                        rafter_mat=WD, rafter_end='white_paint', tiers=1, ends='oni', teri=1.2)
        Rm.zE0 = ZF + 3.2
        Rm.build(B)
        # 身舎 above: boards and a 連子 band, then the big 切妻
        Li, Di = ui[-1] - ui[0], vi[-1] - vi[0]
        zb = ZF + 5.0
        pillars(B, ui, vi, ZF, zb, 0.25, round_=True, base=False)
        walls(B, ui, vi, Rm.zE0 + 1.6, zb - 0.9, {k: 'board' for k in range(4)}, r=0.25)
        walls(B, ui, vi, zb - 0.85, zb - 0.2, {k: 'renji' for k in range(4)}, r=0.25)
        arch.nageshi(B, Li, Di, zb, WD, h=0.34, w=0.2, out=0.0)
        top_b, reach_b = arch.bracket_row(B, Li, Di, zb, 'degumi', 0.8, WD, 'white_paint', us=ui, vs=vi)
        o = 2.0; cc = Di / 2 + o
        R = jroof.Roof(Li, Di, 0.0, o, kind='kirizuma', cover='hongawara', pitch=(60.4 - 0.9 - (ZF + 5.2)) / cc, teri=1.25, sori=0.0, verge=1.6,
                       edge=0.38, rafter=0.28, rafter_mat=WD, rafter_end='white_paint', ends='oni', gable_wall='temple_wall', ridge_h=0.9, ridge_w=0.8)
        R.zE0 = ZF + 5.2
        R.build(B)
        # gable timbers: 虹梁 x 3, 大瓶束, white panels between
        for sg in (-1, 1):
            x = sg * (Li / 2 + 0.07)
            for zz in (R.zE0 + 0.4, R.zE0 + 2.2, R.zE0 + 4.0):
                ys = [y for y in np.linspace(-R.c, R.c, 200) if float(R.z(R.c - abs(y), R.a)) - R.edge - 0.15 > zz]
                if len(ys) > 1: prim.obox(B, (x, ys[0], zz), (x, ys[-1], zz), 0.16, 0.42, WD)
            for y in np.linspace(-Di / 2 + 2.8, Di / 2 - 2.8, 5):
                ztop = float(R.z(R.c - abs(y), R.a)) - R.edge - 0.15
                if ztop > R.zE0 + 0.6: prim.obox(B, (x, y, R.zE0 + 0.4), (x, y, ztop), 0.16, 0.26, WD)
        block_sides(B, us, vs)
    return dict(loc=loc)

def tosu(B, S):
    loc = L.Loc(1294.6, -1124.0, L.ROT + math.pi / 2)        # u north, v west; front = east
    ZG = 47.0
    us = bays([3.75] * 7); vs = bays([3.2] * 4)               # 26.3 x 12.8
    with loc.frame(B):
        zf = ZG + 0.3
        prim.box(B, us[0] - 0.6, vs[0] - 0.6, ZG - 0.3, us[-1] + 0.6, vs[-1] + 0.6, zf, 'stone')
        zt = zf + 4.1
        pillars(B, us, vs, zf, zt, 0.2, round_=True)
        walls(B, us, vs, zf + 0.05, zf + 1.5, {k: 'white' for k in range(4)}, r=0.2)
        walls(B, us, vs, zf + 1.6, zf + 2.6, {0: 'renji', 2: 'renji', 1: ['white', 'karado', 'karado', 'white'], 3: 'white'}, r=0.2)
        walls(B, us, vs, zf + 2.75, zt - 0.2, {k: 'white' for k in range(4)}, r=0.2)
        Lt, Dt = us[-1] - us[0], vs[-1] - vs[0]
        for zz, hh in ((zf + 2.68, 0.18), (zt, 0.3), (zf + 1.55, 0.16)):
            arch.nageshi(B, Lt, Dt, zz, WD, h=hh, w=0.14, out=0.2)
        top, reach = arch.bracket_row(B, Lt, Dt, zt, 'hira', 0.8, WD, 'white_paint', us=us, vs=vs)
        R = jroof.Roof(Lt, Dt, 0.0, 1.5, kind='kirizuma', cover='hongawara', pitch=0.62, teri=1.25, sori=0.0, verge=1.1, edge=0.32, rafter=0.28,
                       rafter_mat=WD, rafter_end='white_paint', ends='oni', gable_wall='temple_wall', ridge_h=0.75, ridge_w=0.7)
        R.zE0 = top + 0.1
        R.build(B)
        block_sides(B, us, vs)

def kyozo(B, S):
    loc = L.Loc(1322.4, -1005.9, L.ROT)
    ZG = 48.45; ZF = ZG + 0.55
    us = bays([3.6, 3.8, 3.6]); vs = bays([3.6, 3.8, 3.6])
    with loc.frame(B):
        pa = us[-1] + 1.3
        prim.box(B, -pa, -pa, ZG - 0.3, pa, pa, ZF, 'stone', c1=(0, 3, 0, 0))
        K.steps(B, (0, -pa - 1.0), (0, -pa), ZG, ZF, 2.2, mat='stone', riser=0.18)
        zm = ZF + 3.9
        pillars(B, us, vs, ZF, zm, 0.2, round_=False)
        walls(B, us, vs, ZF + 0.05, ZF + 2.9, {0: ['white', 'koshi', 'white'], 1: 'white', 2: 'white', 3: 'white'}, r=0.2)
        walls(B, us, vs, ZF + 3.05, zm - 0.15, {k: 'white' for k in range(4)}, r=0.2)
        Lm = us[-1] - us[0]
        for zz, hh in ((ZF + 2.98, 0.2), (zm, 0.3), (ZF + 0.6, 0.16)):
            arch.nageshi(B, Lm, Lm, zz, WD, h=hh, w=0.14, out=0.22)
        # 円窓 on the front side bays
        for x in (us[0] + 1.8, us[-1] - 1.8):
            pts = np.array([(x + 0.75 * math.cos(t), vs[0] - 0.25, ZF + 1.6 + 0.75 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 25)])
            prim.sweep(B, pts, [(-0.08, -0.06), (0.08, -0.06), (0.08, 0.06), (-0.08, 0.06)], 'white_paint', up=(0, 1, 0), tag='detail')
            prim.cyl(B, (x, vs[0] - 0.12, ZF + 1.6), (x, vs[0] - 0.2, ZF + 1.6), 0.7, 0.7, 20, WD, tag='detail')
        top_m, reach_m = arch.bracket_row(B, Lm, Lm, zm, 'demitsudo', 0.65, WD, 'white_paint', us=us, vs=vs)
        Rm = L.RingRoof(Lm, Lm, 0.0, 2.2, truncate=2.2 + 2.0, rise=1.5, cover='hongawara', sori=0.45, sori_len=0.4, edge=0.3, rafter=0.26,
                        rafter_mat=WD, rafter_end='white_paint', tiers=1, ends='oni', teri=1.2)
        Rm.zE0 = ZF + 3.7
        Rm.build(B)
        # upper body: 7.4 square with cusped openings (white panels), 宝形 roof, 露盤 + 宝珠
        Li = 7.4; zb0 = Rm.zE0 + 1.4; zb1 = ZF + 7.0
        ui = bays([2.4, 2.6, 2.4])
        pillars(B, ui, ui, zb0 - 0.6, zb1, 0.17, round_=False, base=False)
        walls(B, ui, ui, zb0 - 0.6, zb1 - 0.15, {k: 'katomado' for k in range(4)}, r=0.17)
        arch.nageshi(B, Li, Li, zb1, WD, h=0.28, w=0.18, out=0.0)
        top_b, reach_b = arch.bracket_row(B, Li, Li, zb1, 'demitsudo', 0.7, WD, 'white_paint', us=ui, vs=ui)
        R = jroof.Roof(Li + 2 * reach_b, Li + 2 * reach_b, 0.0, 1.8, kind='hogyo', cover='hongawara', pitch=0.62, teri=1.35, sori=0.55, sori_len=0.45,
                       edge=0.3, rafter=0.26, rafter_mat=WD, rafter_end='white_paint', ends='oni', top=[(0.0, 0.0)])
        R.zE0 = top_b + 0.1
        rr = R.build(B)
        zr = rr['z_ridge']
        prim.box(B, -0.75, -0.75, zr - 0.2, 0.75, 0.75, zr + 0.55, 'bronze')          # 露盤
        prim.lathe(B, (0, 0, zr + 0.55), [(0.55, 0.0), (0.62, 0.12), (0.45, 0.35), (0.12, 0.45), (0.2, 0.55), (0.32, 0.75), (0.22, 1.0), (0.0, 1.15)], 14, 'bronze')
        K.block_poly(B, [(us[0], vs[0]), (us[-1], vs[0]), (us[-1], vs[-1]), (us[0], vs[-1])])

def yokushitsu(B, S):
    loc = L.Loc(1418.7, -1143.1, L.ROT + math.pi / 2)        # gable to the south: u north
    ZG = 50.25
    us = bays([3.2] * 4); vs = bays([3.4] * 3)
    with loc.frame(B):
        zf = ZG + 0.25
        prim.box(B, us[0] - 0.5, vs[0] - 0.5, ZG - 0.3, us[-1] + 0.5, vs[-1] + 0.5, zf, 'stone')
        zt = zf + 3.7
        pillars(B, us, vs, zf, zt, 0.17, round_=False)
        walls(B, us, vs, zf + 0.05, zt - 0.2, {0: 'white', 1: ['white', 'karado', 'white'], 2: 'white', 3: ['white', 'renji', 'white']}, r=0.17)
        arch.nageshi(B, us[-1] - us[0], vs[-1] - vs[0], zt, WD, h=0.28, w=0.16, out=0.0)
        R = jroof.Roof(us[-1] - us[0], vs[-1] - vs[0], zt + 1.1, 1.3, kind='kirizuma', cover='hongawara', pitch=0.75, sori=0.0, verge=1.0, edge=0.3,
                       rafter=0.28, rafter_mat=WD, rafter_end='white_paint', ends='oni', gable_wall='temple_wall')
        R.build(B)
        K.block_poly(B, [(us[0], vs[0]), (us[-1], vs[0]), (us[-1], vs[-1]), (us[0], vs[-1])])

def shoro(B, S):
    loc = L.Loc(1454.3, -1108.7, L.ROT)
    EK.bell_tower(B, S, loc, 56.0, L=4.6, D=3.8, H=4.6, base=1.4)

# ====================================================================== gates
def gates(B, S):
    # 日下門 (west gate on the lane), 薬医門 facing west
    loc = L.Loc(1286.2, -1030.6, L.ROT + math.pi / 2)        # u north, v west -> front (v-) faces east; flip: front west
    loc = L.Loc(1286.2, -1030.6, L.ROT - math.pi / 2)
    EK.gate(B, S, loc, zg=45.2, span=3.6, depth=2.3, H=3.9, r=0.25, roof_L=7.6, roof_D=6.6, pitch=0.8, z_eave=45.2 + 5.2, doors='open')
    # 六波羅門 (Kamakura, the south-most gate), facing south
    loc = L.Loc(1319.5, -1156.3, L.ROT)
    EK.gate(B, S, loc, zg=47.95, span=3.2, depth=2.6, H=3.3, r=0.24, roof_L=6.6, roof_D=6.4, pitch=0.85, z_eave=47.95 + 4.4, doors='open')
    # 勅使門, closed
    loc = L.Loc(1337.0, -1167.0, L.ROT)
    EK.gate(B, S, loc, zg=48.55, span=3.4, depth=2.6, H=3.2, r=0.22, roof_L=6.8, roof_D=6.4, pitch=0.85, z_eave=48.55 + 4.2, doors='closed', mat='wood_dark')
    # 月下門, the small north gate on the lane past 臥雲橋, facing west
    loc = L.Loc(1303.8, -901.0, L.ROT - math.pi / 2)
    EK.gate(B, S, loc, zg=44.1, span=2.4, depth=1.8, H=2.9, r=0.18, roof_L=5.0, roof_D=4.0, pitch=0.85, z_eave=44.1 + 3.7, doors='open')
