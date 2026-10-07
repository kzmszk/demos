"""嵐山 boats and the boat landing: 屋形船 (open wooden pleasure boats of 嵐山通船: a long flat-bottomed hull with a raised
pointed bow, a light roof on thin posts, red lanterns), the glazed 屋形船, rowing boats (貸しボート, blue and yellow), the
north-bank landing (a stone quay at the water with stairs down from the promenade, the ticket booth) and the boats
moored in the south channel by 櫟谷宗像神社."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point
from jk import prim, Frame
import sites.machiya as M
import sites.arashiyama_util as U

LANDING_X = (-7712.0, -7668.0)        # the quay along the north bank above 葛野大堰 (ticket booth OSM 3259196464 at (-7687, 3049))

def bank_line(river, x0, x1, side='north'):
    """the water edge of the main channel between x0..x1 on one side (sampled), as (k, 2) points west -> east"""
    P = river.ch['main']
    pts = []
    for x in np.arange(x0, x1 + 0.01, 1.0):
        seg = LineString([(x, 2600), (x, 3400)]).intersection(P)
        ys = [c[1] for g in getattr(seg, 'geoms', [seg]) for c in g.coords]
        if not ys: continue
        pts.append((x, max(ys) if side == 'north' else min(ys)))
    return np.array(pts)

STAIRS = ((LANDING_X[0] + 1.0, LANDING_X[0] + 9.0), (LANDING_X[1] - 1.0, LANDING_X[1] - 9.0))

def stairs_ends(river, e, xa, xb):
    ya = float(np.interp(xa, e[:, 0], e[:, 1])); yb = float(np.interp(xb, e[:, 0], e[:, 1]))
    return np.array([xa, ya + 1.9]), np.array([xb, yb - 1.0])

def plan(S, river):
    """the landing: the quay polygon (in the water along the north bank) and the stairs down to it — both left open by
    the water and embankment blockers"""
    e = bank_line(river, *LANDING_X)
    if len(e) < 4: return None
    L = LineString(e)
    q = L.buffer(-3.6, single_sided=True)           # negative: to the right of west->east = south = into the water
    q = q.intersection(river.ch['main'].buffer(0.3))
    st = [LineString(stairs_ends(river, e, xa, xb)).buffer(1.1, cap_style='flat') for (xa, xb) in STAIRS]
    return shapely.unary_union([q] + st)

def hull(B, L=10.6, Bm=2.05, H=0.62, mat='wood_natural', c0=(255, 255, 255, 0), trim='wood_dark', tag='main'):
    """a flat-bottomed river boat (in the boat frame: u along the length, bow at +L/2, v across, z up from the keel):
    flared sides, a raised and narrowing bow, a square transom; floor and gunwale"""
    n = 13
    ts = np.linspace(0, 1, n)
    u = (ts - 0.5) * L
    hb = Bm / 2 * np.where(ts < 0.75, 0.86 + 0.14 * np.sin(np.minimum(ts / 0.75, 1) * math.pi / 2), 1 - 0.92 * np.clip((ts - 0.75) / 0.25, 0, 1) ** 1.6)
    hb = np.maximum(hb, 0.06)
    keel = np.where(ts > 0.7, 0.55 * ((ts - 0.7) / 0.3) ** 2, 0.0)          # rocker toward the bow
    sheer = H + np.where(ts > 0.72, 0.42 * np.clip((ts - 0.72) / 0.28, 0, 1) ** 1.5, 0.0) + np.where(ts < 0.1, 0.08 * (1 - ts / 0.1), 0.0)
    bottom_hw = hb * 0.82
    P = []
    for i in range(n):
        for (v, z) in ((-hb[i], sheer[i]), (-bottom_hw[i], keel[i]), (bottom_hw[i], keel[i]), (hb[i], sheer[i])):
            P.append((u[i], v, z))
    P = np.array(P); I = []
    for i in range(n - 1):
        a = 4 * i; b = a + 4
        for j in range(3):
            I += [[a + j, b + j, b + j + 1], [a + j, b + j + 1, a + j + 1]]
    I = np.array(I)
    # outward: the side normals point away from the centre line
    C = P[I].mean(1); fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    flip = (fn[:, 1] * C[:, 1] < 0) & (np.abs(C[:, 1]) > 0.05) | ((np.abs(C[:, 1]) <= 0.05) & (fn[:, 2] > 0))
    I[flip] = I[flip][:, ::-1]
    B.add(P, I, mat, tag=tag, c0=c0)
    B.add(P, I[:, ::-1], mat, tag='detail', c0=c0)                          # the inside of the hull
    # transom (stern)
    s = P[0:4]
    B.add(s, [[0, 1, 2], [0, 2, 3]], mat, tag=tag, c0=c0); B.add(s, [[0, 2, 1], [0, 3, 2]], mat, tag='detail', c0=c0)
    # gunwale rubbing strips
    for side in (0, 3):
        path = P[side::4]
        prim.sweep(B, path + [0, 0, 0.02], [(-0.05, -0.04), (0.05, -0.04), (0.05, 0.04), (-0.05, 0.04)], trim, tag='detail', caps=True)
    # floor boards
    fl = np.array([(u[i], -bottom_hw[i] * 0.95, keel[i] + 0.18) for i in range(1, n - 3)] + [(u[i], bottom_hw[i] * 0.95, keel[i] + 0.18) for i in range(n - 4, 0, -1)])
    prim.polygon(B, fl[:, :2], fl[:, 2].mean(), 'wood_natural', tag='detail', c0=(200, 180, 150, 0))
    return u, hb, sheer

def yakatabune(B, x, y, z, yaw, rng, roof_tint=(64, 86, 74), glazed=False, lanterns=2):
    """屋形船: the hull, a cabin roof on thin posts (or a glazed cabin), red lanterns at the eaves"""
    with Frame(B, x, y, z, yaw):
        if glazed:
            u, hb, sheer = hull(B, L=12.0, Bm=2.4, H=0.75, mat='black_lacquer', trim='wood_natural')
            M.hbox(B, -3.6, 3.0, -1.0, 1.0, 0.75, 0.9, 'wood_natural', tag='main')
            # glazed sides: thin frames + glass
            M.side_rect(B, -1.0, 1.0, 0.9, 2.0, 3.0, 'glass', facing=1); M.side_rect(B, -1.0, 1.0, 0.9, 2.0, -3.6, 'glass', facing=-1)
            for s in (-1, 1):
                P = np.array([(-3.6, s * 1.0, 0.9), (3.0, s * 1.0, 0.9), (3.0, s * 1.0, 2.0), (-3.6, s * 1.0, 2.0)])
                M.oquad(B, P, (0, s, 0), 'glass', tag='main')
                us = np.linspace(-3.6, 3.0, 8)
                M.bars(B, np.c_[us, np.full(8, s * 1.02), np.full(8, 0.9)], np.c_[us, np.full(8, s * 1.02), np.full(8, 2.0)], (1, 0, 0), 0.07, 0.05, 'wood_natural', tag='detail', caps=True)
            M.hbox(B, -3.9, 3.3, -1.25, 1.25, 2.0, 2.12, 'roof_metal', tag='main', c0=(52, 52, 50, 0))
            prim.box(B, -3.4, -0.9, 1.0, 2.8, 0.9, 1.6, 'lantern_paper', tag='detail', faces='z')
            B.lamp(-0.3, 0.0, 1.6, 6.0, (1.0, 0.7, 0.45))
            return
        u, hb, sheer = hull(B, L=rng.uniform(9.8, 11.2), Bm=rng.uniform(1.9, 2.15))
        zf = 0.18
        # posts and the roof (a shallow gable of dark green sheet with wooden eave boards)
        ua, ub = -3.4, 2.8
        Wr = 1.25
        for uu in np.linspace(ua, ub, 4):
            for s in (-1, 1):
                prim.cyl(B, (uu, s * 0.9, zf + 0.1), (uu, s * 0.9, zf + 1.9), 0.035, 0.035, 5, 'wood_natural', tag='detail')
        zr = zf + 1.9
        for s in (-1, 1):
            P = np.array([(ua - 0.35, s * Wr, zr), (ub + 0.35, s * Wr, zr), (ub + 0.35, 0.0, zr + 0.3), (ua - 0.35, 0.0, zr + 0.3)])
            M.oquad(B, P, (0, s, 1), 'roof_metal', tag='main', c0=(*roof_tint, 0))
            M.oquad(B, P - [0, 0, 0.04], (0, -s, -1), 'wood_natural', tag='main', c0=(190, 170, 140, 0))
            M.bars(B, [(ua - 0.35, s * Wr, zr - 0.05)], [(ub + 0.35, s * Wr, zr - 0.05)], (0, 0, 1), 0.04, 0.12, 'wood_natural', tag='detail', caps=True)
        for e in (ua - 0.35, ub + 0.35):
            P = np.array([(e, -Wr, zr), (e, Wr, zr), (e, 0.0, zr + 0.3)])
            B.add(P, [[0, 1, 2]], 'wood_natural', tag='detail'); B.add(P, [[0, 2, 1]], 'wood_natural', tag='detail')
        # low tables (座卓) and cushions
        for uu in np.linspace(ua + 0.6, ub - 0.6, 3):
            M.hbox(B, uu - 0.4, uu + 0.4, -0.35, 0.35, zf + 0.25, zf + 0.32, 'wood_dark', tag='detail')
        # red lanterns at the eaves (lit)
        for k in range(lanterns):
            uu = ua + 0.2 if k == 0 else ub - 0.2
            for s in ((1,) if k else (-1,)):
                prim.lathe(B, (uu, s * (Wr - 0.15), zr - 0.55), [(0.1, 0.0), (0.15, 0.08), (0.16, 0.2), (0.15, 0.32), (0.1, 0.4)], 8, 'vermilion', tag='detail', c0=M.paint_tint((205, 36, 28)))
                B.lamp(uu, s * (Wr - 0.15), zr - 0.35, 3.0, (1.0, 0.4, 0.2))
        # the boatman's pole along the roof
        prim.cyl(B, (ua - 0.2, 0.3, zr + 0.35), (ub + 2.5, 0.3, zr + 0.35), 0.03, 0.03, 5, 'bamboo', tag='detail')

def rowboat(B, x, y, z, yaw, tint):
    with Frame(B, x, y, z, yaw):
        c = M.paint_tint(tint, base=(0.7, 0.68, 0.62))
        u, hb, sheer = hull(B, L=3.7, Bm=1.35, H=0.42, mat='white_paint', c0=c, trim='white_paint')
        for uu in (-0.5, 0.6):
            M.hbox(B, uu - 0.12, uu + 0.12, -0.55, 0.55, 0.3, 0.34, 'white_paint', tag='detail', c0=M.paint_tint((235, 235, 230), base=(0.7, 0.68, 0.62)))
        for s in (-1, 1):
            prim.cyl(B, (-0.1, s * 0.6, 0.45), (0.9, s * 1.6, 0.05), 0.025, 0.02, 5, 'wood_natural', tag='detail')

def booth(B, S, x, y, yaw, w=3.2, d=2.4):
    """the landing's ticket booth: a little tiled hut with a counter, noren and a lantern"""
    z = float(S.ground(x, y))
    with Frame(B, x, y, z, yaw):
        M.hbox(B, -w / 2, w / 2, 0.0, d, -0.3, 0.05, 'stone', tag='main')
        M.front_rect(B, -w / 2, w / 2, 0.05, 1.0, 0.0, 'wall_board', c0=(70, 56, 42, 0))
        M.front_rect(B, -w / 2, w / 2, 1.0, 2.0, 0.25, 'glass')
        M.front_rect(B, -w / 2, w / 2, 2.0, 2.45, 0.0, 'wall_plaster', c0=(220, 210, 190, 0))
        M.hbox(B, -w / 2, w / 2, -0.3, 0.0, 0.95, 1.0, 'wood_natural', tag='detail')
        M.side_rect(B, 0.0, d, 0.05, 2.45, -w / 2, 'wall_plaster', facing=-1, c0=(220, 210, 190, 0))
        M.side_rect(B, 0.0, d, 0.05, 2.45, w / 2, 'wall_plaster', facing=1, c0=(220, 210, 190, 0))
        M.front_rect(B, -w / 2, w / 2, 0.05, 2.45, d, 'wall_plaster', facing=1, c0=(220, 210, 190, 0))
        o = 0.7
        for s in (-1, 1):
            P = np.array([(-w / 2 - 0.4, d / 2 + s * (d / 2 + o), 2.35), (w / 2 + 0.4, d / 2 + s * (d / 2 + o), 2.35), (w / 2 + 0.4, d / 2, 3.05), (-w / 2 - 0.4, d / 2, 3.05)])
            M.oquad(B, P, (0, s, 1), 'kawara', tag='main', uv=np.array([(0, 0), (w + 0.8, 0), (w + 0.8, 1.3), (0, 1.3)]))
            M.oquad(B, P - [0, 0, 0.08], (0, -s, -1), 'eave_wood', tag='main', c1=(0, 2, 0, 0))
        M.bars(B, [(-w / 2 - 0.45, d / 2, 3.1)], [(w / 2 + 0.45, d / 2, 3.1)], (0, 0, 1), 0.22, 0.15, 'ridge', tag='main', caps=True)
        for s in (-1, 1):
            P = np.array([(s * (w / 2 + 0.4), -o, 2.35), (s * (w / 2 + 0.4), d + o, 2.35), (s * (w / 2 + 0.4), d / 2, 3.05)])
            B.add(P, [[0, 1, 2]], 'wall_plaster', tag='main', c0=(220, 210, 190, 0)); B.add(P, [[0, 2, 1]], 'wall_plaster', tag='main', c0=(220, 210, 190, 0))
        M.noren(B, -w / 2 + 0.2, w / 2 - 0.2, 2.25, 0.5, -0.32, (40, 60, 110))
        M.chochin(B, w / 2 + 0.25, -0.5, 2.3, r=0.16, h=0.42)
        prim.polygon(B, [(-w / 2, 0), (w / 2, 0), (w / 2, d), (-w / 2, d)], 0.1, 'stone', tag='block')

def build(B, S, river, quay=None):
    rng = np.random.default_rng(23)
    # ---------------- the landing quay: a stone platform at the north bank, stairs down from the promenade
    e = bank_line(river, *LANDING_X)
    if len(e) >= 4 and quay is not None and not quay.is_empty:
        zw = river.zw('main', 0, e[:, 0].mean())
        zq = float(zw) + 0.55
        qq = LineString(e).buffer(-3.6, single_sided=True).intersection(river.ch['main'].buffer(0.3))
        for p in U.polys(qq):
            ring = np.asarray(shapely.geometry.polygon.orient(p, 1.0).exterior.coords)[:-1]
            prim.prism(B, ring, zw - 1.2, zq, 'stone', top_mat='stone', tag='main')
            prim.polygon(B, ring, zq, 'stone', tag='walk')
        # mooring posts along the quay edge
        L = LineString(e).offset_curve(-3.3)
        if not L.is_empty:
            for t in np.arange(1.0, L.length, 4.0):
                p = L.interpolate(t)
                prim.cyl(B, (p.x, p.y, zq), (p.x, p.y, zq + 0.55), 0.09, 0.09, 6, 'wood_dark', tag='detail')
        # stairs: from the promenade down the bank at both ends of the quay, along the bank
        for (xa, xb) in ((LANDING_X[0] + 1.0, LANDING_X[0] + 9.0), (LANDING_X[1] - 1.0, LANDING_X[1] - 9.0)):
            ya = float(np.interp(xa, e[:, 0], e[:, 1])); yb = float(np.interp(xb, e[:, 0], e[:, 1]))
            top = np.array([xa, ya + 0.8]); bot = np.array([xb, yb - 1.0])
            zt = float(S.ground(xa, ya + 2.0));
            from jk import arch
            arch.stairs(B, top, bot, zt, zq, 1.8, 'stone')
        # the moored boats along the quay (bows upstream = west)
        L2 = LineString(e).offset_curve(-5.0)
        k = 0
        if not L2.is_empty:
            for t in np.arange(5.5, L2.length - 4.0, 11.5):
                p = L2.interpolate(t); d = U.tangent(L2, t)
                yaw = math.atan2(d[1], d[0]) + math.pi
                z = float(river.zw('main', 0, p.x)) - 0.22
                if k == 1: yakatabune(B, p.x, p.y, z - 0.1, yaw, rng, glazed=True)
                else: yakatabune(B, p.x, p.y, z, yaw, rng)
                # a second rank further out
                q = np.array([p.x, p.y]) + np.array([d[1], -d[0]]) * 2.6
                if k % 2 == 0: yakatabune(B, q[0], q[1], z, yaw + rng.uniform(-0.05, 0.05), rng, roof_tint=(70, 76, 80))
                k += 1
        # rowing boats rafted east of the quay
        for j in range(6):
            x = LANDING_X[1] + 2.0 + j * 1.5
            yb = float(np.interp(min(x, e[-1, 0]), e[:, 0], e[:, 1])) - 2.6
            rowboat(B, x, yb, float(river.zw('main', 0, x)) - 0.12, -math.pi / 2 + rng.uniform(-0.06, 0.06), (52, 96, 170) if j % 3 else (230, 196, 60))
    # ticket booth on the promenade above the quay (replacing the generic 売店)
    booth(B, S, -7687.0, 3049.5, math.radians(-8.0) + math.pi)
    # ---------------- boats out on the pool above the weir
    W = river.ch['main']
    spots = [(-7600, 3010, 'row'), (-7585, 2990, 'row'), (-7620, 2975, 'row'), (-7650, 3000, 'row'), (-7560, 3025, 'row'), (-7700, 2985, 'row'),
             (-7740, 3000, 'row'), (-7630, 3018, 'yakata'), (-7575, 2955, 'yakata'), (-7720, 2960, 'row'), (-7680, 3005, 'row')]
    for k in range(16):                      # more rowing boats scattered over the pool (photos: dozens on a fine day)
        spots.append((rng.uniform(-7790, -7545), rng.uniform(2950, 3030), 'row'))
    for (x, y, kind) in spots:
        if not W.buffer(-4.0).contains(Point(x, y)): continue
        if int(river.zone_of('main', x, y)[0]) != 0: continue
        z = float(river.zw('main', 0, x))
        yaw = rng.uniform(0, 2 * math.pi)
        if kind == 'row': rowboat(B, x, y, z - 0.12, yaw, [(52, 96, 170), (230, 196, 60), (50, 120, 110)][int(rng.integers(3))])
        else: yakatabune(B, x, y, z - 0.22, math.pi + rng.uniform(-0.3, 0.3), rng)
    # ---------------- moored in the south channel by 櫟谷宗像神社 (along its south bank)
    Ps = river.ch['south']
    for x in np.arange(-7532.0, -7478.0, 11.0):
        seg = LineString([(x, 2700), (x, 3000)]).intersection(Ps)
        ys = [c[1] for g in getattr(seg, 'geoms', [seg]) for c in g.coords]
        if not ys: continue
        y = min(ys) + 2.2
        if not Ps.buffer(-1.2).contains(Point(x, y)): continue
        z = float(river.zw('south', 0, x)) - 0.22
        yakatabune(B, x, y, z, math.pi + rng.uniform(-0.04, 0.04), rng, roof_tint=(72, 84, 78) if x % 2 else (60, 70, 66))
