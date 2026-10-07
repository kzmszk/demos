"""清水寺 本堂 (National Treasure, 1633) with its 舞台 on the 懸造 frame, the two 翼廊 and the west 車寄.

Hall frame: u (here U) along the front (east), v north (into the hall), z absolute (T.P.).  The origin is the centre
of the 身舎 axis: the OSM outline (w102164590) shifted 2.95 m east (its rectangle includes the west 車寄).
Plan (module 3.3 m): 身舎 9 x 7 bays (U ±14.85, v -9.3 .. 13.8), 裳階 2.7 m on E / W / N (outer line U ±17.55,
v 16.5), 庇 one bay to the south (v -12.6), the stage between the wings: U ±9.0, v -12.6 .. -23.3 (18 x 10.7 m,
~190 m2), 18 main posts 6 x 3 at 3.3 m (U ±1.65, ±4.95, ±8.25; v -22.5, -19.2, -15.9), the wings U ±9.0 .. ±17.55,
v -15.9 .. -9.3.  Floor 115.6, deck 115.5 (13-14 m above the cliff foot), ridge ~131 (PLATEAU top 131.9)."""
import math
import numpy as np
import jk
from jk import prim, arch, Frame
from sites import kiyomizu_lib as K

ZF = 115.6          # floor of the 外陣 / 庇 / wings
ZEAVE = 9.8         # main eave (N / E / W) above the floor
ROOF_SCALE = 0.78   # slope scale of the main roof (ridge ~131.3)
ZD = 115.5          # stage deck top
Z_PT = 114.7        # post tops under the 大引
ROWS = [-22.5, -19.2, -15.9, -12.6, -9.3]
STAGE_U = [-8.25, -4.95, -1.65, 1.65, 4.95, 8.25]
SIDE_U = [11.55, 14.85, 17.55]
FULL_U = [-u for u in SIDE_U[::-1]] + STAGE_U + SIDE_U
GRID_U = [-14.85 + 3.3 * i for i in range(10)]          # 身舎 columns
GRID_V = [-9.3 + 3.3 * j for j in range(8)]             # 身舎 rows (v -9.3 .. 13.8)
DECK = (-9.0, 9.0, -23.3, -12.6)
WING_U = (9.0, 13.275, 17.55)
WING_V = (-15.9, -12.6, -9.3)

def hall_frame(S):
    b = S.osm_building(102164590)
    cx, cy, L, W, yaw = S.rect(b['poly'][0])
    if math.cos(yaw) < 0: yaw += math.pi
    return (cx + 2.95 * math.cos(yaw), cy + 2.95 * math.sin(yaw), yaw)

def build(B, S):
    fr = hall_frame(S)
    ox, oy, yaw = fr
    gl = lambda U, v: float(S.ground(*K.to_world(fr, [(U, v)])[0]))
    info = dict(frame=fr)
    R = main_roof()
    with Frame(B, ox, oy, 0.0, yaw) as F:
        substructure(B, gl)
        deck(B)
        wings(B)
        body(B, R)
        roofs(B, R)
        kurumayose(B)
        walks(B, gl)
    return info

# ------------------------------------------------------------------ the 懸造 frame
def substructure(B, gl):
    posts = {}
    for v in ROWS:
        cols = STAGE_U if v < -16 else FULL_U
        for U in cols:
            zg = gl(U, v)
            if zg > Z_PT - 0.7: continue
            r = 0.33 if v == ROWS[0] else 0.29
            K.post(B, U, v, zg, Z_PT, r, 'wood_dark', seg=16 if v == ROWS[0] else 12, base='stone', base_h=0.3)
            posts[(U, v)] = zg
    # stone footings: a stepped 石垣 at the foot of the front rows (the 2010 / 2015 photos)
    # 大引 (E-W) on each post row, 頭貫 below, 根太 (N-S) on top, cantilevered to the deck edge
    for v in ROWS:
        us = sorted(U for (U, vv) in posts if vv == v)
        if len(us) < 2: continue
        K.beam(B, (us[0] - 0.5, v), (us[-1] + 0.5, v), Z_PT + 0.45, 0.36, 0.45, 'wood_dark')
        K.beam(B, (us[0] - 0.35, v), (us[-1] + 0.35, v), Z_PT - 0.35, 0.2, 0.32, 'wood_dark')      # 頭貫
    # N-S 梁 over every column line, projecting to the deck front (the beam ends seen under the deck edge)
    for U in FULL_U:
        vs = sorted(v for (UU, v) in posts if UU == U)
        if not vs: continue
        v0 = DECK[2] + 0.05 if U in STAGE_U else vs[0] - 0.6
        K.beam(B, (U, v0), (U, max(vs[-1], -9.3) + 0.3), Z_PT + 0.45, 0.3, 0.42, 'wood_dark')
    for U in np.arange(DECK[0] + 0.3, DECK[1] - 0.2, 0.9):
        K.beam(B, (U, DECK[2] + 0.02), (U, -9.3), ZD - 0.1, 0.13, 0.22, 'wood_dark', tag='detail')
    # 貫 tiers: E-W in the row planes, N-S in the column planes, at alternating heights every ~1 m
    EW = [Z_PT - 1.25 - 2.0 * k for k in range(8)]
    NS = [Z_PT - 2.25 - 2.0 * k for k in range(8)]
    def runs(keys, zt):
        out = []; cur = []
        for k_ in keys:
            if k_ is not None and posts[k_] + 0.55 < zt: cur.append(k_)
            else:
                if len(cur) >= 2: out.append(cur)
                cur = []
        if len(cur) >= 2: out.append(cur)
        return out
    caps = []
    for v in ROWS:
        cols = STAGE_U if v < -16 else FULL_U
        keys = [(U, v) if (U, v) in posts else None for U in cols]
        for zt in EW:
            for run in runs(keys, zt):
                a = run[0][0] - 0.5; b = run[-1][0] + 0.5
                K.beam(B, (a, v), (b, v), zt, 0.16, 0.38, 'wood_dark')
                caps += [((U, v), zt, (1, 0)) for (U, _) in run]
    for U in FULL_U:
        vs = [v for v in ROWS if (U, v) in posts]
        keys = [(U, v) for v in vs]
        for zt in NS:
            for run in runs(keys, zt):
                a = run[0][1] - 0.5; b = run[-1][1] + 0.5
                K.beam(B, (U, a), (U, b), zt, 0.16, 0.38, 'wood_dark')
                caps += [((U, run_v), zt, (0, 1)) for (_, run_v) in run]
        # 筋違 (diagonal braces) in the lower bays between the stage rows
        for i in range(len(vs) - 1):
            va, vb = vs[i], vs[i + 1]
            if vb > -12: continue
            for k in range(len(NS) - 1):
                zl, zh = NS[k + 1], NS[k]
                if posts[(U, va)] + 0.6 < zl and posts[(U, vb)] + 0.6 < zl and k >= 2:
                    prim.obox(B, (U, va, zl - 0.2), (U, vb, zh - 0.2), 0.14, 0.26, 'wood_dark', tag='detail')
    # small rain caps (小屋根) on the 貫 where they pierce the posts
    for ((U, v), zt, d) in caps:
        d = np.array(d, float); n = K.perp(d)
        for s in (-1, 1):
            c = np.array([U, v]) + d * s * 0.42
            for side in (-1, 1):
                P = np.array([np.r_[c - d * 0.17, zt + 0.03], np.r_[c + d * 0.17, zt + 0.03], np.r_[c + d * 0.17 + n * side * 0.17, zt - 0.03], np.r_[c - d * 0.17 + n * side * 0.17, zt - 0.03]])
                B.add(P, [[0, 1, 2], [0, 2, 3]], 'wood_dark', tag='detail')
                B.add(P, [[0, 2, 1], [0, 3, 2]], 'wood_dark', tag='detail')
    # stone footings under the slope: stepped retaining walls (石垣) in front of / under the posts
    return posts

# ------------------------------------------------------------------ the stage deck, railings
def deck(B):
    U0, U1, v0, v1 = DECK
    rng = np.random.default_rng(3)
    w = 0.45
    j = 0
    v = v0
    while v < v1 - 0.01:
        vb = min(v1, v + w)
        off = (j % 3) * 1.8
        xs = [U0] + [x for x in np.arange(U0 + 1.6 + off, U1 - 0.8, 5.4)] + [U1]
        for a, b in zip(xs[:-1], xs[1:]):
            prim.box(B, a + 0.004, v + 0.006, ZD - 0.1, b - 0.004, vb - 0.006, ZD, 'wood_natural', faces='Zxyz' if v == v0 else 'Z', c1=(0, 0, int(rng.integers(255)), 0))
        v = vb; j += 1
    # the deck's edge board (縁葛) and a dark gap layer under the boards
    prim.box(B, U0, v0 - 0.08, ZD - 0.42, U1, v0 + 0.05, ZD - 0.08, 'wood_dark')
    for U in (U0, U1):
        prim.box(B, U - 0.05, v0, ZD - 0.42, U + 0.05, -15.9, ZD - 0.08, 'wood_dark')
    prim.box(B, U0, v0, ZD - 0.14, U1, v1, ZD - 0.1, 'wood_dark', faces='Z')
    # 庇 floor, one step up
    for v in np.arange(-12.6, -9.3 - 0.01, 0.45):
        prim.box(B, -9.0, v + 0.006, ZF - 0.1, 9.0, min(-9.3, v + 0.45) - 0.006, ZF, 'wood_natural', faces='Zy', c1=(0, 0, int(rng.integers(255)), 0))
    # railing: front and the two sides up to the wings, bronze 擬宝珠 at the corners
    a = U1 - 0.12
    K.rail_line(B, [(-a, -15.9), (-a, v0 + 0.12), (a, v0 + 0.12), (a, -15.9)], ZD, h=0.95, mat='wood_natural', giboshi_at=(0, 1, 2, 3), post_every=1.85)
    K.block_line(B, [(-a, -15.6), (-a, v0 + 0.12), (a, v0 + 0.12), (a, -15.6)], w=0.6)

# ------------------------------------------------------------------ the 翼廊 (east / west wings)
def wings(B):
    for s in (-1, 1):
        us = [s * u for u in WING_U]
        z1 = ZF + 4.3
        for U in us:
            for v in WING_V:
                if abs(U) < 9.5 and v == -9.3: continue
                K.post(B, U, v, ZF, z1, 0.25, 'wood_dark', base=None)
        # floor
        ua, ub = sorted((us[0], us[-1]))
        for v in np.arange(-15.9, -9.3 - 0.01, 0.45):
            prim.box(B, ua - 0.3, v + 0.006, ZF - 0.1, ub + 0.3, min(-9.3, v + 0.45) - 0.006, ZF, 'wood_natural', faces='Zy')
        prim.box(B, ua - 0.3, -16.3, ZF - 0.45, ub + 0.3, -15.9, ZF - 0.1, 'wood_dark')
        # beams: 頭貫, 長押, a 虹梁 across the front
        for v in WING_V:
            K.beam(B, (us[0], v), (us[-1], v), z1 - 0.1, 0.18, 0.3, 'wood_dark', ext=0.3)
        for U in us:
            K.beam(B, (U, WING_V[0]), (U, WING_V[-1]), z1 - 0.1, 0.18, 0.3, 'wood_dark', ext=0.3)
            K.beam(B, (U, WING_V[0]), (U, WING_V[-1]), ZF + 2.9, 0.12, 0.2, 'wood_dark', ext=0.2)
        K.beam(B, (us[0], -15.9), (us[-1], -15.9), ZF + 2.9, 0.12, 0.2, 'wood_dark', ext=0.2)
        # brackets (平三斗) on the pillar tops
        for U in us:
            for v in WING_V:
                if abs(U) < 9.5 and v == -9.3: continue
                arch.kumimono(B, U, v, z1, (0, -1) if v == -15.9 else (s, 0), (1, 0) if v == -15.9 else (0, 1), 'hira', 0.8, 'wood_dark')
        # ceiling (化粧屋根裏) under the wing roof
        prim.box(B, ua - 0.3, -16.2, z1 + 0.42, ub + 0.3, -9.3, z1 + 0.5, 'wood_dark', faces='zZ')
        # railings on the wing front (south) and its outer side
        uo = s * 17.55; ui = s * 9.4
        K.rail_line(B, [(ui, -16.05), (uo + s * 0.12, -16.05), (uo + s * 0.12, -9.6)], ZF, h=0.9, mat='wood_natural', giboshi_at=(1,), post_every=2.15)
        K.block_line(B, [(ui, -16.05), (uo + s * 0.12, -16.05), (uo + s * 0.12, -9.6)])
        # musicians' hall back wall (boards) toward the 身舎 / 裳階
        K.wall_panel(B, (us[1], -9.3), (s * 14.85 if s > 0 else us[-1], -9.3), ZF, z1 - 0.25, 'wall_board')

# ------------------------------------------------------------------ the 庇, 外陣 front, 身舎 and 裳階 walls
def body(B, R):
    # 庇 pillars and beams
    hU = [-9.0, -4.95, -1.65, 1.65, 4.95, 9.0]
    zt = ZF + 4.3
    for U in hU[1:-1]:
        K.post(B, U, -12.6, ZF, zt, 0.27, 'wood_dark', base=None)
    K.beam(B, (-9.0, -12.6), (9.0, -12.6), zt - 0.1, 0.22, 0.34, 'wood_dark', ext=0.2)
    K.beam(B, (-9.0, -12.6), (9.0, -12.6), ZF + 3.2, 0.13, 0.22, 'wood_dark', ext=0.2)
    for U in hU:
        K.beam(B, (U, -12.6), (U, -9.3), zt + 0.05, 0.2, 0.36, 'wood_dark')         # 繋虹梁
        if abs(U) < 9.0: arch.kumimono(B, U, -12.6, zt, (0, -1), (1, 0), 'demitsudo', 0.85, 'wood_dark')
    # 庇 ceiling and the band up to the 外陣 ceiling
    prim.box(B, -9.0, -12.9, zt + 0.95, 9.0, -9.3, zt + 1.0, 'wood_dark', faces='z')
    # hanging bronze lanterns (釣灯籠) in the 庇
    for U in (-6.6, -3.3, 0.0, 3.3, 6.6):
        prim.cyl(B, (U, -11.4, ZF + 2.5), (U, -11.4, zt + 0.95), 0.012, 0.012, 4, 'metal_dark', tag='detail')
        prim.lathe(B, (U, -11.4, ZF + 1.95), [(0.0, 0.0), (0.16, 0.02), (0.2, 0.15), (0.2, 0.45), (0.3, 0.5), (0.12, 0.62), (0.0, 0.66)], 8, 'bronze', tag='detail')
        B.lamp(U, -11.4, ZF + 2.2, 6.0)
    # 外陣 front (v -9.3): pillars, open bays with a lattice 欄間, the 外陣 ceiling and the dark inner wall (v -2.7)
    zb = ZF + ZEAVE - 0.8               # 身舎 wall plate
    for U in GRID_U:
        K.post(B, U, -9.3, ZF, min(zb, float(R.env(np.array([[U, -9.3]]))[0][0]) - 1.2), 0.3, 'wood_dark', base=None)
    K.beam(B, (-14.85, -9.3), (14.85, -9.3), ZF + 4.0, 0.22, 0.32, 'wood_dark', ext=0.25)
    for a, b in zip(GRID_U[:-1], GRID_U[1:]):
        if abs((a + b) / 2) < 9.0:
            K.lattice(B, (a + 0.3, -9.3), (b - 0.3, -9.3), ZF + 4.15, ZF + 5.0, step=0.14, back=None)
    K.wall_panel(B, (-14.85, -9.3), (14.85, -9.3), ZF + 5.0, ZF + 6.2, 'wall_board')
    prim.box(B, -14.85, -9.3, ZF + 6.2, 14.85, -2.7, ZF + 6.3, 'wood_dark', faces='z')
    prim.box(B, -14.85, -2.75, ZF, 14.85, -2.65, ZF + 6.2, 'wall_board', faces='y')
    for U in GRID_U[1:-1]:
        K.post(B, U, -2.7, ZF, ZF + 6.2, 0.33, 'black_lacquer', base=None)
    for U in (-5.0, 0.0, 5.0):          # gilt hanging lanterns in the 外陣
        prim.lathe(B, (U, -5.5, ZF + 3.6), [(0.0, 0.0), (0.3, 0.05), (0.38, 0.3), (0.38, 0.75), (0.5, 0.8), (0.2, 1.0), (0.0, 1.05)], 8, 'gold', tag='detail')
        B.lamp(U, -5.5, ZF + 4.0, 10.0)
    prim.box(B, -14.85, -9.3, ZF - 0.12, 14.85, -2.7, ZF, 'wood_natural', faces='Z')
    # 身舎 perimeter pillars (E / W / N lines) up to the wall plate (kept 1.2 m under the roof where the low front
    # slope passes over them), a board band above the 裳階 roof, bracket sets (出組) and the purlin on N / E / W
    def top(U, v): return min(zb, float(R.env(np.array([[U, v]]))[0][0]) - 1.25)
    perim = [(14.85, v) for v in GRID_V[1:]] + [(-14.85, v) for v in GRID_V[1:]] + [(U, 13.8) for U in GRID_U[1:-1]]
    for (U, v) in perim:
        K.post(B, U, v, ZF, top(U, v), 0.3, 'wood_dark', base=None)
    ring = [(14.85, -9.3), (14.85, 13.8), (-14.85, 13.8), (-14.85, -9.3)]
    for a, b in zip(ring[:-1], ring[1:]):
        a = np.array(a, float); b = np.array(b, float)
        L = float(np.linalg.norm(b - a)); n = max(2, int(L / 1.0))
        pts = [a + (b - a) * i / n for i in range(n + 1)]
        tops = [top(*p) for p in pts]
        for i in range(n):
            P = np.array([np.r_[pts[i], ZF], np.r_[pts[i + 1], ZF], np.r_[pts[i + 1], tops[i + 1]], np.r_[pts[i], tops[i]]])
            B.add(P, [[0, 1, 2], [0, 2, 3]], 'wall_board'); B.add(P, [[0, 2, 1], [0, 3, 2]], 'wall_board')
        for i in range(n):
            prim.obox(B, np.r_[pts[i], tops[i] - 0.18], np.r_[pts[i + 1], tops[i + 1] - 0.18], 0.26, 0.36, 'wood_dark')
    for (U, v, od, al) in [(U, 13.8, (0, 1), (1, 0)) for U in GRID_U] + [(14.85, v, (1, 0), (0, 1)) for v in GRID_V[1:-1]] + [(-14.85, v, (-1, 0), (0, 1)) for v in GRID_V[1:-1]]:
        if top(U, v) < zb - 0.01: continue
        if abs(U) == 14.85 and v == 13.8:
            od = (math.copysign(0.7071, U), 0.7071); al = (-od[1], od[0])
        arch.kumimono(B, U, v, zb, od, al, 'degumi', 0.95, 'wood_dark')
    for (p0, p1) in (((15.4, -4.0), (15.4, 14.35)), ((15.4, 14.35), (-15.4, 14.35)), ((-15.4, 14.35), (-15.4, -4.0))):
        K.beam(B, p0, p1, zb + 1.05, 0.24, 0.24, 'wood_dark')
    # 裳階: outer pillars, lattice walls, ceiling
    zm = ZF + 4.4
    outer_v = [-9.3, -6.0, -2.7, 0.6, 3.9, 7.2, 10.5, 13.8, 16.5]
    outer_u = [-17.55] + GRID_U + [17.55]
    for s in (-1, 1):
        for v in outer_v:
            K.post(B, s * 17.55, v, ZF, zm, 0.24, 'wood_dark', base='stone', base_h=0.15)
        for a, b in zip(outer_v[:-1], outer_v[1:]):
            door = (s > 0 and a == 0.6)
            mid = (a + b) / 2
            p0, p1 = (s * 17.55, a + 0.25), (s * 17.55, b - 0.25)
            if door:
                continue
            K.wall_panel(B, p0, p1, ZF, ZF + 0.9, 'wall_board')
            K.lattice(B, p0, p1, ZF + 0.9, ZF + 3.5, step=0.15, back='glass', out=(s, 0))
            K.wall_panel(B, p0, p1, ZF + 3.5, zm, 'wall_board')
        K.beam(B, (s * 17.55, -9.3), (s * 17.55, 16.5), zm, 0.2, 0.3, 'wood_dark', ext=0.25)
        K.beam(B, (s * 17.55, -9.3), (s * 17.55, 16.5), ZF + 3.5, 0.13, 0.2, 'wood_dark')
        for v in outer_v:
            arch.kumimono(B, s * 17.55, v, zm, (s, 0), (0, 1), 'funa', 0.8, 'wood_dark')
            K.beam(B, (s * 17.55, v), (s * 14.85, v), zm - 0.15, 0.16, 0.26, 'wood_dark')     # 繋梁
        prim.box(B, min(s * 14.85, s * 17.55), -9.3, zm + 0.3, max(s * 14.85, s * 17.55), 16.5, zm + 0.36, 'wood_dark', faces='z')
        prim.box(B, min(s * 14.85, s * 17.55) - 0.3, -9.3, ZF - 0.12, max(s * 14.85, s * 17.55) + 0.3, 16.5, ZF, 'wood_natural', faces='Z')
    for U in outer_u:
        K.post(B, U, 16.5, ZF, zm, 0.24, 'wood_dark', base='stone', base_h=0.15)
    for a, b in zip(outer_u[:-1], outer_u[1:]):
        p0, p1 = (b - 0.25, 16.5), (a + 0.25, 16.5)
        K.wall_panel(B, p0, p1, ZF, ZF + 0.9, 'wall_board')
        K.lattice(B, p0, p1, ZF + 0.9, ZF + 3.5, step=0.15, back='glass', out=(0, 1))
        K.wall_panel(B, p0, p1, ZF + 3.5, zm, 'wall_board')
    K.beam(B, (-17.55, 16.5), (17.55, 16.5), zm, 0.2, 0.3, 'wood_dark', ext=0.25)
    for U in outer_u:
        arch.kumimono(B, U, 16.5, zm, (0, 1), (1, 0), 'funa', 0.8, 'wood_dark')
    prim.box(B, -17.55, 13.8, zm + 0.3, 17.55, 16.5, zm + 0.36, 'wood_dark', faces='z')
    prim.box(B, -17.85, 13.8, ZF - 0.12, 17.85, 16.8, ZF, 'wood_natural', faces='Z')
    # the stone plinth (基壇) under the 裳階 where the hall stands on the ground (N / E / W)
    for ring_ in ([(17.9, -9.0), (17.9, 16.85), (-17.9, 16.85), (-17.9, -9.0)],):
        for a, b in zip(ring_[:-1], ring_[1:]):
            K.wall_panel(B, a, b, ZF - 1.2, ZF - 0.12, 'stone', both=False, out=K.perp(K.unit(np.subtract(b, a))) * -1)

# ------------------------------------------------------------------ roofs
def main_roof():
    P = K.abs_profile(0.3, 1.0, 0.42, 3.5, 18.0, ROOF_SCALE)
    zN = ZF + ZEAVE; zS = ZF + 4.6
    a, n_, s_ = 17.35, 16.3, -15.1
    faces = [dict(p0=(-a, s_), p1=(a, s_), z=zS, prof=P, o=2.5, sori=0.35, sori_len=5.0),
             dict(p0=(a, s_), p1=(a, n_), z=zN, prof=P, o=2.5, sori=0.55, sori_len=6.0),
             dict(p0=(a, n_), p1=(-a, n_), z=zN, prof=P, o=2.5, sori=0.55, sori_len=6.0),
             dict(p0=(-a, n_), p1=(-a, s_), z=zN, prof=P, o=2.5, sori=0.55, sori_len=6.0)]
    return K.EnvRoof(faces, mat='hiwada', edge=0.45, fascia='wood_dark', flash='copper', rafter=0.24, tiers=2, res=0.5)

def roofs(B, R):
    Bm = jk.Builder('main_roof'); Bm.xf = B.xf
    Bw = jk.Builder('wing_roofs'); Bw.xf = B.xf
    R.build(Bm)
    ridge = R.crease(0, 2)
    if ridge is not None:
        ridge = ridge[np.argsort(ridge[:, 0])]
        K.ridge_cap(Bm, ridge + [0, 0, 0.05], 0.75, 0.95, mat='ridge', ends=('oni', 'oni'))
    for (k, j) in ((1, 0), (1, 2), (3, 0), (3, 2)):
        c = R.crease(k, j)
        if c is None or len(c) < 2: continue
        c = c[np.argsort(c[:, 2])]
        K.ridge_cap(Bm, c + [0, 0, 0.03], 0.42, 0.42, mat='ridge', ends=('oni', None))
    # 裳階 lean-to roofs (E, N, W)
    Pm = K.abs_profile(0.32, 0.62, 0.62, 2.0, 10.0, 1.0)
    zm = ZF + 5.0; e = 19.05; nn = 18.0
    mf = [dict(p0=(e, -9.6), p1=(e, nn), z=zm, prof=Pm, o=1.5, dcap=e - 14.85, sori=0.25, sori_len=3.0),
          dict(p0=(e, nn), p1=(-e, nn), z=zm, prof=Pm, o=1.5, dcap=nn - 13.8, sori=0.25, sori_len=3.0),
          dict(p0=(-e, nn), p1=(-e, -9.6), z=zm, prof=Pm, o=1.5, dcap=e - 14.85, sori=0.25, sori_len=3.0)]
    Rm = K.EnvRoof(mf, mat='hiwada', edge=0.34, fascia='wood_dark', flash='copper', rafter=0.27, tiers=1, res=0.5)
    Rm.build(Bm)
    for (k, j) in ((0, 1), (2, 1)):
        c = Rm.crease(k, j)
        if c is not None and len(c) >= 2:
            c = c[np.argsort(c[:, 2])]
            K.ridge_cap(Bm, c + [0, 0, 0.02], 0.3, 0.3, mat='ridge')
    # the wings: 入母屋, gable to the south (妻入), ridge running back into the main roof
    for s in (-1, 1):
        uc = s * 13.275
        with Frame(Bw, uc, -10.4, 0.0, math.pi / 2):
            K.mroof(Bw, 10.9, 8.55, ZF + 5.3, 1.6, kind='irimoya', cover='hiwada', pitch=0.92, teri=1.5, sori=0.45, gable_frac=0.42, verge=0.7,
                    rafter=0.24, rafter_mat='wood_dark', ends='oni', bargeboard_mat='wood_dark', gable_wall='wall_board', flash='copper',
                    prof=K.slope_profile(0.32, 1.15, 0.75, 0.25))
    with Frame(Bw, -20.0, -3.25, 0.0, 0.0):
        K.mroof(Bw, 7.4, 9.5, ZF + 4.45, 1.25, kind='irimoya', cover='hiwada', pitch=0.8, teri=1.4, sori=0.3, gable_frac=0.45, verge=0.6,
                rafter=0.26, rafter_mat='wood_dark', ends='oni', gable_wall='wall_board', flash='copper')
    # keep the upper envelope where the roofs run into each other
    Zw = K.TriZ(K.tris_of(Bw, mats=('hiwada',)))
    Zm = K.TriZ(K.tris_of(Bm, mats=('hiwada',)))
    K.cull_below(Bm, Zw, mats=('hiwada', 'wood_dark', 'copper', 'ridge'), eps=0.05)
    K.cull_below(Bw, Zm, mats=('hiwada', 'wood_dark', 'copper', 'ridge', 'wall_board'), eps=0.05)
    K.merge_into(B, Bm); K.merge_into(B, Bw)

# ------------------------------------------------------------------ the west porch (車寄), entered from the 回廊
def kurumayose(B):
    zt = ZF + 3.9
    us = (-23.4, -20.5)
    vs = (-8.0, -3.25, 1.5)
    for U in us:
        for v in vs:
            K.post(B, U, v, ZF, zt, 0.24, 'wood_dark', base='stone', base_h=0.2)
    for v in vs:
        K.beam(B, (us[0], v), (-17.55, v), zt - 0.1, 0.18, 0.3, 'wood_dark', ext=0.3)
    for U in us:
        K.beam(B, (U, vs[0]), (U, vs[-1]), zt - 0.1, 0.18, 0.3, 'wood_dark', ext=0.3)
        for v in vs:
            arch.kumimono(B, U, v, zt, (-1, 0), (0, 1), 'funa', 0.8, 'wood_dark')
    prim.box(B, us[0] - 0.4, vs[0] - 0.4, ZF - 0.12, -17.55, vs[-1] + 0.4, ZF, 'wood_natural', faces='Zxy')
    prim.box(B, us[0] - 0.4, vs[0] - 0.4, zt + 0.35, -17.55, vs[-1] + 0.4, zt + 0.4, 'wood_dark', faces='z')

# ------------------------------------------------------------------ walk surfaces and blockers
def walks(B, gl):
    U0, U1, v0, v1 = DECK
    K.walk_poly(B, K.rect(0, (v0 + 0.3 + v1) / 2, U1 - 0.1, (v1 - v0 - 0.3) / 2), ZD)          # stage
    K.walk_poly(B, [(-14.85, -12.6), (14.85, -12.6), (14.85, -5.5), (-14.85, -5.5)], ZF)        # 庇 + 外陣 front
    for s in (-1, 1):
        K.walk_poly(B, [(s * 9.0, -16.0), (s * 17.7, -16.0), (s * 17.7, -9.3), (s * 9.0, -9.3)], ZF)   # wings
    K.walk_poly(B, [(14.85, -9.3), (17.6, -9.3), (17.6, 13.8), (14.85, 13.8)], ZF)               # east 裳階 aisle
    K.walk_poly(B, [(-23.8, -8.4), (-14.85, -8.4), (-14.85, 1.9), (-23.8, 1.9)], ZF)            # 車寄
    K.walk_poly(B, [(-17.55, -9.3), (-14.85, -9.3), (-14.85, -5.5), (-17.55, -5.5)], ZF)
    # the east door: a few steps down to the path
    K.walk_poly(B, [(17.6, 0.6), (19.6, 0.6), (19.6, 3.9), (17.6, 3.9)], lambda x, y: ZF - (x - 17.6) / 2.0 * max(0.0, ZF - gl(19.6, 2.2)))
    prim.box(B, 17.6, 0.6, ZF - 0.5, 18.6, 3.9, ZF - 0.12, 'stone')
    # blockers: the 身舎 interior beyond the 外陣 front strip, the 裳階 outer walls (but the east door), the west aisle
    K.block_poly(B, [(-14.6, -5.3), (14.6, -5.3), (14.6, 13.6), (-14.6, 13.6)])
    K.block_line(B, [(17.75, -9.0), (17.75, 0.6)]); K.block_line(B, [(17.75, 3.9), (17.75, 16.7), (-17.75, 16.7), (-17.75, -5.3)])
    K.block_line(B, [(-17.55, -9.3), (-17.55, -8.4)])
