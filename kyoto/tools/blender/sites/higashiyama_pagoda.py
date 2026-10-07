"""八坂の塔 (法観寺五重塔, 1440, 三間五重塔婆 本瓦葺) and 八坂庚申堂 (金剛寺).

The pagoda (dossier refs/yasaka_pagoda): total 38.8 m incl. the 相輪 (the dossier's working value: PLATEAU's measured
28.7 m to the top of the body + a 相輪 of ~1/3; the "46 m" of the tourist pages does not fit the photographs), first
storey 6.4 m square (3 bays), roof spans 15.3 -> 13.3 m (PLATEAU's roof outline is 15.3 m; ~4 % less per storey),
eave edges ~4.2 m apart, deep 三手先 brackets with 尾垂木, double rafters, 本瓦 roofs with 鬼瓦 on the hips, 風鐸 at
the corners, only the 5th storey has a 縁 with 高欄; unpainted dark timber, bronze 相輪 with 9 rings, 水煙, 宝珠.
Stands on a stone platform in a small plot with a tiled-coping lattice fence (透塀) and the entrance from the lane
south of it."""
import math
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from jk import prim, arch
from jk.core import Frame
from jk import roof as jroof
import sites.machiya as M
import sites.higashiyama_front as HF

PAG_C = (1866.6, 1415.3)          # centre of the OSM / PLATEAU footprints
PAG_YAW = math.radians(1.7)       # the footprint's edges are ~2 degrees off the grid

H_TOTAL = 38.8
SPANS = [15.3, 14.8, 14.3, 13.8, 13.3]          # eave tip to tip (m)
BODY = [6.4, 6.0, 5.6, 5.2, 4.8]                # pillar line squares
EAVES = [6.5, 10.7, 14.9, 19.1, 23.3]           # eave edge heights above the platform base ground

def rect(hu, hv=None):
    hv = hu if hv is None else hv
    return [(-hu, -hv), (hu, -hv), (hu, hv), (-hu, hv)]

def bracket_h(kind, s):
    """height of arch.kumimono / bracket_row (incl. its purlin) and its reach, for planning"""
    mh = 0.17 * s; hh = 0.17 * s; arm = 0.55 * s
    steps = {'mitesaki': 3, 'futatesaki': 2, 'degumi': 1}[kind]
    zc = mh * 1.5
    for k in range(steps + 1): zc += hh + mh
    return zc + 0.24 * s, (steps + 1) * arm

def ring_ceiling(B, w, reach, z, mat='eave_wood'):
    """the ceiling of the bracket zone: a square ring (facing down) from the wall to just beyond the purlin"""
    a = w / 2 - 0.05; b = w / 2 + reach + 0.3
    P = []; I = []
    for k, (sx, sy) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
        pass
    outer = [(-b, -b), (b, -b), (b, b), (-b, b)]; inner = [(-a, -a), (a, -a), (a, a), (-a, a)]
    for i in range(4):
        j = (i + 1) % 4
        q = [(*outer[i], z), (*outer[j], z), (*inner[j], z), (*inner[i], z)]
        k = len(P); P += q; I += [[k, k + 2, k + 1], [k, k + 3, k + 2]]           # facing down
    B.add(np.array(P), I, mat, tag='main', c1=(0, 2, 0, 0))

def body(B, w, z0, z1, k, bscale):
    """pillars, tie beams, walls of one storey (square, 3 bays): storey 1 doors (板唐戸) in the middle bays and 連子窓 at
    the sides; upper storeys a small 連子窓 in the middle, boards at the sides"""
    b1 = w * 0.17
    us = [-w / 2, -b1, b1, w / 2]
    r = 0.2 if k == 0 else 0.16
    for u in us:
        for v in us:
            if u in (us[0], us[-1]) or v in (us[0], us[-1]):
                prim.cyl(B, (u, v, z0), (u, v, z1), r, r * 0.96, 10, 'wood_dark', caps=(False, True), tag='main')
    # 地覆, 腰長押, 内法長押, 頭貫
    for zz, hh, out in ((z0 + 0.12, 0.24, 0.12), (z0 + (z1 - z0) * 0.78, 0.2, 0.13), (z1 - 0.1, 0.26, 0.1)):
        arch.nageshi(B, w, w, zz + hh / 2, h=hh, w=0.12, out=out - 0.06, mat='wood_dark')
    for side in range(4):
        ang = side * math.pi / 2
        c, s_ = math.cos(ang), math.sin(ang)
        R = lambda p: (c * p[0] - s_ * p[1], s_ * p[0] + c * p[1])
        for i in range(3):
            p0 = R((us[i], -w / 2)); p1 = R((us[i + 1], -w / 2))
            out = R((0, -1))
            if k == 0:
                kind = 'karado' if i == 1 else 'renji'
                if kind == 'renji':
                    arch.infill(B, p0, p1, z0 + 0.24, z0 + (z1 - z0) * 0.32, 'board', out=out, mat='wood_dark')
                    arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.32, z0 + (z1 - z0) * 0.76, 'renji', out=out, mat='wood_dark')
                    arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.8, z1 - 0.14, 'board', out=out, mat='wood_dark')
                else:
                    arch.infill(B, p0, p1, z0 + 0.24, z0 + (z1 - z0) * 0.76, 'karado', out=out, mat='wood_dark')
                    arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.8, z1 - 0.14, 'board', out=out, mat='wood_dark')
            else:
                if i == 1:
                    zm0 = z0 + (z1 - z0) * 0.3; zm1 = z0 + (z1 - z0) * 0.72
                    arch.infill(B, p0, p1, z0 + 0.24, zm0, 'board', out=out, mat='wood_dark')
                    arch.infill(B, p0, p1, zm0, zm1, 'renji', out=out, mat='wood_dark')
                    arch.infill(B, p0, p1, zm1, z1 - 0.14, 'board', out=out, mat='wood_dark')
                else:
                    arch.infill(B, p0, p1, z0 + 0.24, z1 - 0.14, 'board', out=out, mat='wood_dark')
    return us

def nakazonae(B, w, z, s):
    """間斗束: a short post with a bearing block between the bracket sets, each bay of each side"""
    b1 = w * 0.17
    for side in range(4):
        ang = side * math.pi / 2
        c, s_ = math.cos(ang), math.sin(ang)
        for u in ((-w / 2 - b1) / 2 * 1.0, 0.0, (w / 2 + b1) / 2):
            x, y = c * u - s_ * (-w / 2), s_ * u + c * (-w / 2)
            prim.box(B, x - 0.07 * s, y - 0.07 * s, z, x + 0.07 * s, y + 0.07 * s, z + 0.5 * s, 'wood_dark', tag='detail')
            prim.box(B, x - 0.14 * s, y - 0.14 * s, z + 0.5 * s, x + 0.14 * s, y + 0.14 * s, z + 0.66 * s, 'wood_dark', tag='detail')

def furin(B, x, y, z):
    """風鐸: a small bronze bell under a roof corner"""
    prim.cyl(B, (x, y, z - 0.35), (x, y, z), 0.012, 0.012, 4, 'metal_dark', tag='detail')
    prim.lathe(B, (x, y, z - 0.75), [(0.0, 0.0), (0.16, 0.02), (0.14, 0.2), (0.1, 0.38), (0.0, 0.42)], 8, 'bronze', tag='detail')

def sorin(B, z, h):
    """相輪: 露盤, 伏鉢, 請花, 九輪, 水煙, 竜車, 宝珠 (bronze)"""
    prim.box(B, -0.95, -0.95, z, 0.95, 0.95, z + 0.55, 'bronze')
    prim.box(B, -1.05, -1.05, z + 0.5, 1.05, 1.05, z + 0.62, 'bronze')
    k = h / 12.0
    z1 = z + 0.62
    prim.lathe(B, (0, 0, z1), [(0.62, 0.0), (0.64, 0.3 * k), (0.48, 0.65 * k), (0.15, 0.75 * k), (0.42, 0.95 * k), (0.5, 1.1 * k), (0.14, 1.2 * k)], 12, 'bronze')
    zc = z1 + 1.2 * k
    top = z + h
    prim.cyl(B, (0, 0, zc), (0, 0, top - 1.0 * k), 0.1, 0.07, 8, 'bronze')
    for i in range(9):
        zi = zc + 0.3 * k + i * 0.62 * k
        rr = 0.66 * (1 - i * 0.02)
        prim.lathe(B, (0, 0, zi), [(0.1, 0), (rr, 0.06 * k), (rr, 0.17 * k), (0.1, 0.23 * k)], 14, 'bronze', tag='main' if i % 2 == 0 else 'detail')
    zs = zc + 0.3 * k + 9 * 0.62 * k
    for a in range(4):
        ang = a * math.pi / 2 + math.pi / 4
        d = np.array([math.cos(ang), math.sin(ang), 0.0])
        P = np.array([[0, 0, zs], d * 0.75 + [0, 0, zs + 0.3 * k], d * 0.82 + [0, 0, zs + 1.0 * k], d * 0.55 + [0, 0, zs + 1.6 * k], d * 0.15 + [0, 0, zs + 1.75 * k], [0, 0, zs + 1.7 * k]])
        I = [[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5]]
        B.add(P, I, 'bronze', tag='main'); B.add(P, [t[::-1] for t in I], 'bronze', tag='main')
        continue
        I = [[0, 1, 2], [0, 2, 3], [0, 3, 4]]
        B.add(P, I, 'bronze', tag='main'); B.add(P, [t[::-1] for t in I], 'bronze', tag='main')
    zr = zs + 1.75 * k
    prim.lathe(B, (0, 0, zr), [(0.08, 0.0), (0.26, 0.12 * k), (0.08, 0.28 * k), (0.2, 0.45 * k), (0.24, 0.62 * k), (0.12, 0.85 * k), (0.0, 1.0 * k)], 12, 'bronze')

def pagoda(B, S, lz, stats):
    cx, cy = PAG_C
    # the platform: OSM's 13.2 m square; its base at the lowest ground around it
    zgs = [float(S.ground(cx + dx, cy + dy)) for dx in (-6.6, 0, 6.6) for dy in (-6.6, 0, 6.6)]
    zg = max(zgs); zlow = min(zgs)
    zp = zg + 0.75
    ntri0 = B.ntri()
    with Frame(B, cx, cy, 0.0, PAG_YAW):
        hp = 6.6
        arch.platform(B, rect(hp), zlow - 0.4, zp, 'stone', walk=True)
        # a coping band and steps on the south (the entrance side)
        prim.box(B, -hp - 0.05, -hp - 0.05, zp - 0.12, hp + 0.05, hp + 0.05, zp, 'curb', faces='xXyY')
        for i in range(4):
            prim.box(B, -1.5, -hp - 0.32 * (i + 1), zg - 0.3, 1.5, -hp - 0.32 * i, zp - 0.19 * (i + 1) + 0.0, 'stone', faces='yZxX')
        prim.polygon(B, [(-1.5, -hp - 1.3), (1.5, -hp - 1.3), (1.5, -hp), (-1.5, -hp)], zg + 0.35, 'stone', tag='walk')
        # blocker: the body of the pagoda (the platform itself is walkable)
        prim.polygon(B, rect(BODY[0] / 2 + 0.25), zp + 0.05, 'stone', tag='block')
        floor = zp + 0.06
        top_z = None
        for k in range(5):
            w = BODY[k]; span = SPANS[k]
            s = 0.9 if k == 0 else 0.84
            bh, reach = bracket_h('mitesaki', s)
            c = span / 2
            pitch = 0.42 if k < 4 else 0.5
            teri = 1.6
            o = c - (w / 2 + reach)
            H = c * pitch
            e_abs = zg + EAVES[k]
            z_eave = e_abs + H * (o / c) ** teri                 # roof surface over the purlin line
            top = z_eave - 0.3
            plate = top - bh
            z0 = floor
            if plate - z0 < 1.3:                                 # keep a minimal wall (should not happen)
                plate = z0 + 1.3
            # the 5th storey: 縁 + 高欄 on the roof of the 4th
            if k == 4:
                dk = w / 2 + 0.95
                prim.box(B, -dk, -dk, z0 - 0.12, dk, dk, z0, 'wood_dark', faces='ZxXyY')
                prim.box(B, -dk + 0.02, -dk + 0.02, z0 - 0.75, dk - 0.02, dk - 0.02, z0 - 0.12, 'wood_dark', faces='xXyY')
                rl = [(-dk + 0.1, -dk + 0.1), (dk - 0.1, -dk + 0.1), (dk - 0.1, dk - 0.1), (-dk + 0.1, dk - 0.1), (-dk + 0.1, -dk + 0.1)]
                arch.railing(B, rl, z0, h=0.75, mat='wood_dark', cap_mat='bronze', giboshi=True)
            us = body(B, w, z0, plate, k, s)
            # brackets on every pillar (corner sets diagonal), the purlin
            btop, breach = arch.bracket_row(B, w, w, plate, 'mitesaki', s=s, mat='wood_dark', end_mat='wood_dark', us=np.array(us), vs=np.array(us))
            nakazonae(B, w, plate, s)
            # the boards behind the bracket sets (小壁 / 支輪) up to the purlin, the ceiling of the bracket zone over them
            a_ = w / 2 + 0.02
            for side_ in range(4):
                ang = side_ * math.pi / 2; c_, s2 = math.cos(ang), math.sin(ang)
                R = lambda p: (c_ * p[0] - s2 * p[1], s2 * p[0] + c_ * p[1])
                q0 = R((-a_, -a_)); q1 = R((a_, -a_))
                P = np.array([(*q0, plate - 0.15), (*q1, plate - 0.15), (*q1, btop - 0.1), (*q0, btop - 0.1)])
                fn = np.cross(P[1] - P[0], P[2] - P[0])
                o_ = np.array([*R((0, -1)), 0.0])
                B.add(P, [[0, 1, 2], [0, 2, 3]] if fn @ o_ > 0 else [[0, 2, 1], [0, 3, 2]], 'wood_dark', tag='main')
            ring_ceiling(B, w, breach, btop - 0.12)
            # the roof
            kw = dict(kind='hogyo', cover='hongawara', pitch=pitch, teri=teri, sori=0.55, sori_len=0.42, rafter=0.21, rafter_mat='wood_dark',
                      rafter_end='wood_dark', fascia_mat='wood_dark', tiers=2, ends='oni', ridge_h=0.75, ridge_w=0.5, edge=0.34)
            Lr = w + 2 * reach
            if k < 4:
                nb = BODY[k + 1]
                trunc = c - nb / 2 + 0.12
                rf = jroof.Roof(Lr, Lr, z_eave, o, truncate=trunc, **kw)
                rf.build(B)
                floor = float(rf.z(trunc - 0.12, c)) + 0.12
            else:
                rf = jroof.Roof(Lr, Lr, z_eave, o, top=[(0.01, 0.0)], **kw)
                res = rf.build(B)
                top_z = res['z_ridge']
            # 風鐸 at the four corners
            zc = float(rf.zE(0.0)) - rf.edge
            for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                furin(B, sx * (c - 0.25), sy * (c - 0.25), zc)
        # 露盤 + 相輪 to the total height
        z_r = top_z - 0.35
        sorin(B, z_r, zg + H_TOTAL - z_r)
    S.exclude.append([[1874.0, 1407.8], [1858.7, 1407.5], [1858.4, 1422.5], [1873.7, 1422.8]])
    stats['pagoda_tris'] = B.ntri() - ntri0
    stats['pagoda_top'] = round(zg + H_TOTAL, 2)
    fence(B, S)

def fence(B, S):
    """透塀: stone posts, a dark lattice between, a little tiled coping, along the plot's west and south sides (OSM
    fences 371717412 / 371717409), open at the entrance south of the pagoda"""
    lines = [[(1854.6, 1428.8), (1855.6, 1402.8), (1867.2, 1401.0)], [(1868.8, 1400.7), (1888.4, 1396.2)]]
    for pts in lines:
        for a, b in zip(pts[:-1], pts[1:]):
            a = np.array(a); b = np.array(b); d = b - a; L = float(np.linalg.norm(d)); d /= L
            n = np.array([-d[1], d[0]])
            k = max(1, int(round(L / 1.8)))
            for j in range(k + 1):
                p = a + d * L * j / k
                z = float(S.ground(*p))
                prim.box(B, p[0] - 0.11, p[1] - 0.11, z - 0.2, p[0] + 0.11, p[1] + 0.11, z + 1.75, 'stone', tag='main')
            for j in range(k):
                p = a + d * L * j / k; q = a + d * L * (j + 1) / k
                z = min(float(S.ground(*p)), float(S.ground(*q)))
                ang = math.atan2(d[1], d[0])
                ls = L / k
                with Frame(B, p[0], p[1], z, ang):
                    M.front_rect(B, 0.1, ls - 0.1, 0.0, 0.35, 0.0, 'wood_dark')
                    M.front_rect(B, 0.1, ls - 0.1, 0.0, 0.35, 0.0, 'wood_dark', facing=1)
                    M.lattice(B, 0.1, ls - 0.1, 0.35, 1.45, 0.0, pitch=0.11, sw=0.035, sd=0.035, back=None, rails=True, mid=True)
                    M.bars(B, [(0.0, 0.0, 1.5)], [(ls, 0.0, 1.5)], (0, 0, 1), 0.12, 0.12, 'wood_dark', tag='main')
                    for sg in (-1, 1):
                        P = np.array([(0.0, sg * 0.32, 1.52), (ls, sg * 0.32, 1.52), (ls, 0.0, 1.74), (0.0, 0.0, 1.74)])
                        I = [[0, 1, 2], [0, 2, 3]] if sg < 0 else [[0, 2, 1], [0, 3, 2]]
                        B.add(P, I, 'kawara', UV=np.array([(0, 0), (ls, 0), (ls, 0.4), (0, 0.4)]), tag='main')
                    prim.obox(B, (0.0, 0.0, 1.78), (ls, 0.0, 1.78), 0.14, 0.1, 'ridge', tag='main')
                prim.obox(B, np.r_[p, z + 0.6], np.r_[q, z + 0.6], 0.3, 0.2, 'stone', tag='block')

# ------------------------------------------------------------------ 八坂庚申堂 (金剛寺)
SARU = [(214, 36, 30), (236, 120, 30), (240, 200, 40), (90, 160, 60), (60, 110, 190), (150, 70, 160), (230, 120, 160), (40, 150, 150), (245, 240, 230)]

def kukurizaru(B, cx, cy, z_top, rng, n=None, r=0.07, spread=0.55, drop=1.3):
    """くくり猿: a hanging bundle of small cloth balls (the monkeys with bound limbs), many colours, on strings"""
    n = n or int(rng.integers(14, 30))
    P = []; I = []; C = []
    t = (1 + 5 ** 0.5) / 2
    V0 = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    V0 /= np.linalg.norm(V0, axis=1, keepdims=True)
    F0 = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]])
    for i in range(n):
        x = cx + rng.uniform(-spread, spread) * 0.5; y = cy + rng.uniform(-spread, spread) * 0.5
        z = z_top - rng.uniform(0.15, drop)
        rr = r * rng.uniform(0.8, 1.2)
        k = len(P)
        P += list(V0 * [rr, rr, rr * 0.9] + [x, y, z]); I += list(F0 + k)
        col = SARU[int(rng.integers(len(SARU)))]
        C += [HF.ptint(col)] * 12
    HF.add_flat(B, P, I, 'white_paint', C, tag='detail')

def koshindo(B, S, lz, stats):
    """the gate on 八坂通, the courtyard with rows of くくり猿, the 本堂 (入母屋, 向拝) facing north"""
    rng = np.random.default_rng(1316622873)
    ntri0 = B.ntri()
    # gate: OSM 1550470795 (1820.8-1824.7 x 1409.7-1413.2), front on 八坂通 (north)
    gx, gy = 1822.75, 1411.6
    zg = lz(gx, gy + 2.0)
    yaw = math.radians(-3.0)          # the lane runs ~ -5 degrees here; the gate faces north
    with Frame(B, gx, gy, zg, yaw):
        # 薬医門-like: 2 main posts at the front, 2 back posts, a gable roof (切妻 本瓦)
        for (u, v, r) in ((-1.2, 0.6, 0.15), (1.2, 0.6, 0.15), (-1.2, -0.9, 0.1), (1.2, -0.9, 0.1)):
            prim.cyl(B, (u, v, 0.0), (u, v, 3.1), r, r * 0.95, 10, 'wood_dark', tag='main')
            prim.cyl(B, (u, v, -0.1), (u, v, 0.18), r * 1.5, r * 1.4, 8, 'stone', tag='main')
        prim.obox(B, (-1.6, 0.6, 3.0), (1.6, 0.6, 3.0), 0.18, 0.3, 'wood_dark')
        prim.obox(B, (-1.6, -0.9, 3.0), (1.6, -0.9, 3.0), 0.14, 0.22, 'wood_dark')
        for u in (-1.2, 1.2):
            prim.obox(B, (u, -1.3, 3.25), (u, 1.4, 3.25), 0.16, 0.22, 'wood_dark')
        jroof.roof(B, 3.0, 2.4, 3.42, 0.7, kind='kirizuma', cover='hongawara', pitch=0.5, teri=1.4, sori=0.0, verge=0.55, rafter=0.3, rafter_mat='wood_dark', ends='oni',
                   ridge_h=0.42, ridge_w=0.3, edge=0.22, gable_wall='temple_wall', tiers=1)
        # the doors open, a big red-and-white lantern pair, くくり猿 bundles at the gate
        M.chochin(B, -0.75, 0.75, 2.85, r=0.2, h=0.55, lamp=True)
        M.chochin(B, 0.75, 0.75, 2.85, r=0.2, h=0.55, lamp=False)
        for u in (-1.75, -1.45, 1.45, 1.75):
            kukurizaru(B, u, 0.75, 2.6, rng, n=20, drop=1.5, spread=0.4)
        prim.polygon(B, [(-1.3, -1.0), (1.3, -1.0), (1.3, 0.8), (-1.3, 0.8)], 0.05, 'stone', tag='main')
        prim.polygon(B, [(-1.3, -1.0), (1.3, -1.0), (1.3, 0.8), (-1.3, 0.8)], 0.05, 'stone', tag='walk')
        for u in (-1.2, 1.2):
            prim.polygon(B, [(u - 0.2, -1.0), (u + 0.2, -1.0), (u + 0.2, 0.8), (u - 0.2, 0.8)], 0.1, 'stone', tag='block')
    # walls either side of the gate along the street front (plaster with coping), to the plot corners
    import sites.higashiyama_houses as HH
    w0 = (1818.7, 1413.5); w1 = (1826.4, 1413.0)
    HH.coping_wall(B, w0, (gx - 1.5, gy + 1.6), lz, h=2.2, base=0.5, tint=(232, 228, 216))
    HH.coping_wall(B, (gx + 1.5, gy + 1.6), w1, lz, h=2.2, base=0.5, tint=(232, 228, 216))
    # the courtyard: stone paving, racks of くくり猿 along both sides, a 手水鉢
    cz = lz(1822.5, 1402.0)
    for x in (1819.6, 1825.6):
        for y in np.arange(1397.5, 1408.5, 2.2):
            prim.box(B, x - 0.05, y - 0.05, cz - 0.1, x + 0.05, y + 0.05, cz + 2.3, 'wood_dark', tag='detail')
            kukurizaru(B, x, y, cz + 2.25, rng, n=26, drop=1.2, spread=0.7)
        prim.obox(B, (x, 1397.2, cz + 2.28), (x, 1408.6, cz + 2.28), 0.06, 0.06, 'wood_dark', tag='detail')
        prim.obox(B, (x, 1397.2, cz + 1.2), (x, 1408.6, cz + 1.2), 0.3, 0.3, 'stone', tag='block')
    prim.box(B, 1823.6, 1404.0, cz - 0.1, 1824.6, 1404.8, cz + 0.6, 'stone')
    # the main hall (OSM 568614154 ~ 1815-1825 x 1383-1395): 3 x 3 bays, 入母屋 本瓦, a 向拝 toward the courtyard (north)
    hx, hy = 1820.0, 1389.0
    zh = lz(hx, 1397.0) + 0.15
    with Frame(B, hx, hy, 0.0, math.pi - math.radians(5.0)):          # local -v = north (the front)
        plat = [(-4.6, -6.7), (4.6, -6.7), (4.6, 5.0), (-4.6, 5.0)]
        arch.platform(B, plat, zh - 0.8, zh + 0.45, 'stone', walk=True)
        for i in range(3):
            prim.box(B, -1.6, -6.7 - 0.36 * (i + 1), zh - 0.4, 1.6, -6.7 - 0.36 * i, zh + 0.45 - 0.15 * (i + 1), 'stone', faces='yZxX')
        prim.polygon(B, [(-1.6, -7.8), (1.6, -7.8), (1.6, -6.7), (-1.6, -6.7)], zh + 0.1, 'stone', tag='walk')
        z0 = zh + 0.5
        L, D = 7.2, 7.6
        with Frame(B, 0.0, 0.9, 0.0, 0.0):
            us = np.linspace(-L / 2, L / 2, 4); vs = np.linspace(-D / 2, D / 2, 4)
            for u in us:
                for v in vs:
                    if u in (us[0], us[-1]) or v in (vs[0], vs[-1]):
                        arch.pillar(B, u, v, z0, z0 + 3.3, r=0.17, mat='wood_dark')
            arch.nageshi(B, L, D, z0 + 3.2, h=0.24, w=0.12, out=0.04)
            arch.nageshi(B, L, D, z0 + 2.3, h=0.18, w=0.1, out=0.08)
            for i in range(3):
                arch.infill(B, (us[i], -D / 2), (us[i + 1], -D / 2), z0 + 0.1, z0 + 2.2, 'koshi' if i != 1 else 'karado', out=(0, -1))
                arch.infill(B, (us[i], -D / 2), (us[i + 1], -D / 2), z0 + 2.4, z0 + 3.1, 'plaster', out=(0, -1))
                arch.infill(B, (us[i], D / 2), (us[i + 1], D / 2), z0 + 0.1, z0 + 3.1, 'board', out=(0, 1))
                arch.infill(B, (us[0], vs[i]), (us[0], vs[i + 1]), z0 + 0.1, z0 + 3.1, 'plaster', out=(-1, 0))
                arch.infill(B, (us[-1], vs[i]), (us[-1], vs[i + 1]), z0 + 0.1, z0 + 3.1, 'plaster', out=(1, 0))
            top, reach = arch.bracket_row(B, L, D, z0 + 3.3, 'demitsudo', s=0.62, us=us, vs=vs)
            jroof.roof(B, L + 2 * reach, D + 2 * reach, top + 0.25, 1.35, kind='irimoya', cover='hongawara', pitch=0.66, teri=1.5, sori=0.4, gable_frac=0.5, verge=0.6,
                       rafter=0.3, rafter_mat='wood_dark', ends='oni', ridge_h=0.65, ridge_w=0.4, edge=0.3, gable_wall='temple_wall', tiers=1)
            prim.polygon(B, rect(L / 2 + 0.3, D / 2 + 0.3), z0 + 0.05, 'stone', tag='block')
        # 向拝: two posts in front of the hall, a lean-to roof from the hall's eave
        vk = 0.9 - D / 2 - 2.2
        for u in (-1.6, 1.6):
            prim.cyl(B, (u, vk, zh + 0.45), (u, vk, z0 + 2.9), 0.13, 0.12, 10, 'wood_dark', tag='main')
            prim.cyl(B, (u, vk, zh + 0.4), (u, vk, zh + 0.6), 0.2, 0.18, 8, 'stone', tag='main')
            prim.polygon(B, [(u - 0.25, vk - 0.25), (u + 0.25, vk - 0.25), (u + 0.25, vk + 0.25), (u - 0.25, vk + 0.25)], zh + 0.5, 'stone', tag='block')
        prim.obox(B, (-2.1, vk, z0 + 2.95), (2.1, vk, z0 + 2.95), 0.16, 0.24, 'wood_dark')
        M.hisashi(B, -2.3, 2.3, z0 + 3.05, depth=2.7, pitch=0.42, v=0.9 - D / 2 + 0.1, brackets=[-1.6, 1.6], manju=True, roof='hongawara')
        # the curtain of くくり猿 hung across the front of the 向拝
        for u in np.linspace(-2.1, 2.1, 10):
            kukurizaru(B, u, vk - 0.15, z0 + 2.8, rng, n=30, drop=1.7, spread=0.5)
        M.chochin(B, 0.0, vk + 0.9, z0 + 3.0, r=0.32, h=0.9, lamp=True)
        prim.box(B, -0.8, vk + 1.3, z0 - 0.5, 0.8, vk + 1.9, z0 + 0.25, 'wood_dark')
    # courtyard paving
    S.paint.append({'poly': [[1818.2, 1396.3], [1826.9, 1396.0], [1826.4, 1413.0], [1818.7, 1413.5]], 'surf': 'stone_slab'})
    S.exclude.append([[1813.4, 1371.7], [1829.7, 1371.7], [1829.7, 1415.6], [1813.4, 1415.6]])
    stats['koshindo_tris'] = B.ntri() - ntri0
