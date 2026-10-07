"""八坂神社 (Yasaka-jinja): 西楼門 (vermilion 三間一戸楼門 at the end of 四条通, 1497) with its L-shaped wings (翼廊) and
the wide stone stairs up from the 祇園 crossing; 舞殿 (三間 x 三間 入母屋 copper, hung with rows of lit lanterns);
本殿 (祇園造: one great 入母屋 檜皮葺 roof over honden + haiden, 又庇 on the sides, the vermilion 向拝 with bells and
ropes); 南楼門; 能舞台, 絵馬堂, 神輿庫, 疫神社 and the small shrines; stone lanterns, the precinct gravel and its trees.
Footprints from OSM (orientation, size), heights from PLATEAU / the dossier."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box as sbox
from jk import prim, arch, roof, Frame
import sites.machiya as M
import sites.gion_streets as G

GREEN = (40, 120, 92)            # the green lattice / 連子 of the shrine (緑青)

def osm_rect(S, oid):
    b = S.osm_building(oid)
    P = Polygon(b['poly'][0][0]).buffer(0)
    cx, cy, L, W, yaw = S.rect(b['poly'][0][0])
    return P, cx, cy, L, W, yaw

def exclude_matching(S, P, used, frac=0.3):
    for pb in S.plateau:
        Q = Polygon(pb['poly'][0][0]).buffer(0)
        if Q.intersects(P) and Q.intersection(P).area > frac * min(Q.area, P.area):
            S.exclude.append([list(map(float, c)) for c in np.asarray(Q.exterior.coords)[:-1]])
            used.add(pb['id'])

def build(B, S, used):
    rng = np.random.default_rng(8)
    nishiromon(B, S, used)
    buden(B, S, used)
    honden(B, S, used)
    minamiromon(B, S, used)
    minor_halls(B, S, used)
    precinct(B, S, used)

# ------------------------------------------------------------------ shared: walls, lattice windows between pillars
def wall_bay(B, p0, p1, z0, z1, kind='plaster', out=None, mat='vermilion'):
    """between pillar centres p0, p1 (local 2D): white plaster, green 連子窓, or vermilion boards"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L
    n = np.array([d[1], -d[0]]) if out is None else np.asarray(out, float)
    a = p0 + d * 0.18; b = p1 - d * 0.18
    def quadv(pa, pb, za, zb, m, off=0.0, **kw):
        A = np.r_[pa - n * off, za]; Bq = np.r_[pb - n * off, za]; C = np.r_[pb - n * off, zb]; D = np.r_[pa - n * off, zb]
        M.oquad(B, [A, Bq, C, D], (n[0], n[1], 0), m, uv=np.array([(0, za), (L, za), (L, zb), (0, zb)]), **kw)
        M.oquad(B, [A, Bq, C, D], (-n[0], -n[1], 0), m, uv=np.array([(0, za), (L, za), (L, zb), (0, zb)]), **kw)
    if kind == 'plaster':
        quadv(a, b, z0, z1, 'temple_wall', c0=(240, 236, 228, 35))
    elif kind == 'renji':
        zm0 = z0 + (z1 - z0) * 0.35; zm1 = z1 - (z1 - z0) * 0.12
        quadv(a, b, z0, zm0, 'temple_wall', c0=(240, 236, 228, 35)); quadv(a, b, zm1, z1, 'temple_wall', c0=(240, 236, 228, 35))
        quadv(a, b, zm0, zm1, 'black_lacquer', off=-0.06)
        k = max(2, int(L / 0.12))
        us = np.linspace(0.08, L - 0.36, k)
        P0 = np.array([np.r_[a + d * u, zm0] for u in us]); P1 = P0 + [0, 0, zm1 - zm0]
        M.bars(B, P0, P1, (d[0], d[1], 0), 0.05, 0.05, 'vermilion', tag='detail', c0=M.paint_tint((40, 120, 92)))
        M.bars(B, [np.r_[a, zm0], np.r_[a, zm1]], [np.r_[b, zm0], np.r_[b, zm1]], (n[0], n[1], 0), 0.12, 0.09, mat, tag='main')
    elif kind == 'board':
        quadv(a, b, z0, z1, mat)

def pillars(B, us, vs, z0, z1, r=0.2, mat='vermilion', ring_only=False, base=True):
    for i, x in enumerate(us):
        for j, y in enumerate(vs):
            if ring_only and 0 < i < len(us) - 1 and 0 < j < len(vs) - 1: continue
            arch.pillar(B, x, y, z0, z1, r, mat, base=base)

def frame_beams(B, us, vs, z, h=0.3, w=0.22, mat='vermilion'):
    L = us[-1] - us[0]; D = vs[-1] - vs[0]
    arch.ring_beam(B, L, D, z, w, h, mat)

# ------------------------------------------------------------------ 楼門 (two-storey gate)
def romon(B, L, D, h1, h2, o_roof=2.2, pitch=0.6, scale=1.0, wings=None):
    """a 三間一戸楼門 in the local frame (u along the front, v through the passage, z from the gate floor).
    L, D: pillar rectangle; h1 lower storey pillar height; h2 upper storey pillar height."""
    us = np.linspace(-L / 2, L / 2, 4); vs = np.linspace(-D / 2, D / 2, 3)
    # lower storey: 12 pillars (the middle row carries the doors), tie beams, the bays either side walled (随身 rooms)
    pillars(B, us, vs, 0.0, h1, r=0.21 * scale)
    for z in (h1 - 0.15, 0.9):
        if z > 1: frame_beams(B, us, vs, z, h=0.32 * scale)
    arch.nageshi(B, L, D, h1 - 0.9, 'vermilion', h=0.2, w=0.12, out=0.0)
    for i in (0, 2):
        # side bays: white plaster above, vermilion lattice fence (the 随身 rooms behind)
        for y in (vs[0], vs[-1]):
            wall_bay(B, (us[i], y), (us[i + 1], y), h1 - 1.6, h1 - 0.95, 'plaster', out=(0, -1 if y < 0 else 1))
            k = int((us[i + 1] - us[i]) / 0.16)
            xs = np.linspace(us[i] + 0.25, us[i + 1] - 0.25, k)
            M.bars(B, np.c_[xs, np.full(k, y), np.full(k, 0.15)], np.c_[xs, np.full(k, y), np.full(k, 1.2)], (1, 0, 0), 0.05, 0.05, 'vermilion', tag='detail')
            M.bars(B, [(us[i] + 0.2, y, 1.2), (us[i] + 0.2, y, 0.18)], [(us[i + 1] - 0.2, y, 1.2), (us[i + 1] - 0.2, y, 0.18)], (0, 0, 1), 0.07, 0.07, 'vermilion', tag='detail')
        wall_bay(B, (us[i], vs[1]), (us[i + 1], vs[1]), 0.1, h1 - 0.95, 'board', mat='vermilion')
        x_end = us[0] if i == 0 else us[3]
        wall_bay(B, (x_end, vs[0]), (x_end, vs[-1]), 0.1, h1 - 0.95, 'plaster', out=(-1 if i == 0 else 1, 0))
    # floor of the passage
    prim.box(B, us[0] - 0.4, vs[0] - 0.6, -0.25, us[-1] + 0.4, vs[-1] + 0.6, 0.02, 'stone', tag='main')
    # bracket sets on the lower pillars carrying the balcony (出組), the balcony floor and its railing
    top, reach = arch.bracket_row(B, L, D, h1, 'degumi', 0.85 * scale, 'vermilion', 'white_paint', us=us, vs=vs, purlin=False)
    zf = top + 0.05
    ew = 1.0 * scale
    prim.box(B, us[0] - ew, vs[0] - ew, zf - 0.12, us[-1] + ew, vs[-1] + ew, zf, 'vermilion', tag='main')
    prim.box(B, us[0] - ew - 0.05, vs[0] - ew - 0.05, zf - 0.32, us[-1] + ew + 0.05, vs[-1] + ew + 0.05, zf - 0.12, 'gold', tag='detail', faces='xXyY')
    a, c = L / 2 + ew - 0.1, D / 2 + ew - 0.1
    arch.railing(B, [(-a, -c), (a, -c), (a, c), (-a, c)], zf, h=0.75, mat='vermilion', cap_mat='gold', closed=True)
    # upper storey: pillars, white walls with green windows in the middle bays, brackets, the 入母屋 roof
    pillars(B, us, vs[[0, 2]], zf, zf + h2, r=0.19 * scale, base=False)
    for y in (vs[0], vs[-1]):
        for i in range(3):
            wall_bay(B, (us[i], y), (us[i + 1], y), zf + 0.1, zf + h2 - 0.25, 'renji' if i == 1 else 'plaster', out=(0, -1 if y < 0 else 1))
    for x in (us[0], us[-1]):
        wall_bay(B, (x, vs[0]), (x, vs[-1]), zf + 0.1, zf + h2 - 0.25, 'plaster', out=(-1 if x < 0 else 1, 0))
    frame_beams(B, us, vs[[0, 2]], zf + h2 - 0.05, h=0.3 * scale)
    top2, reach2 = arch.bracket_row(B, L, D, zf + h2, 'degumi', 0.85 * scale, 'vermilion', 'white_paint', us=us, vs=vs[[0, 2]])
    h = roof.roof(B, L + 2 * reach2, D + 2 * reach2, top2, o_roof * scale, kind='irimoya', cover='hongawara', pitch=pitch, teri=1.6, sori=0.45,
                  rafter=0.26, rafter_mat='vermilion', rafter_end='gold', fascia_mat='vermilion', bargeboard_mat='vermilion', ends='oni', gable_frac=0.45)
    return dict(z_floor2=zf, z_ridge=h['z_ridge'], us=us, vs=vs)

def wing(B, pts, z0, depth=2.2, h=3.4, side=1):
    """翼廊: a one-bay-deep corridor wing along a polyline (local), white walls, vermilion posts, green windows, 切妻 roof"""
    pts = [np.asarray(p, float) for p in pts]
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]
        d = b - a; L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]]) * side
        nb = max(1, int(round(L / 2.1)))
        for i in range(nb + 1):
            p = a + d * L * i / nb
            for s in (0, 1):
                q = p + n * depth * s
                prim.box(B, q[0] - 0.13, q[1] - 0.13, z0, q[0] + 0.13, q[1] + 0.13, z0 + h, 'vermilion', tag='main')
        for i in range(nb):
            p0 = a + d * L * i / nb; p1 = a + d * L * (i + 1) / nb
            for s in (0, 1):
                wall_bay(B, p0 + n * depth * s, p1 + n * depth * s, z0 + 0.15, z0 + h - 0.2, 'renji' if (i % 2 == 0 and s == 0) else 'plaster')
        # base and beams
        c0 = a; c1 = b
        Q = np.array([np.r_[c0 - n * 0.3, z0], np.r_[c1 - n * 0.3, z0], np.r_[c1 + n * (depth + 0.3), z0], np.r_[c0 + n * (depth + 0.3), z0]])
        M.oquad(B, Q, (0, 0, 1), 'stone', tag='main')
        for (e0, e1, nn) in ((Q[0], Q[1], -n), (Q[3], Q[2], n)):
            M.oquad(B, [e0 - [0, 0, 1.6], e1 - [0, 0, 1.6], e1, e0], (nn[0], nn[1], 0), 'stone', tag='main')
        for s in (0, 1):
            M.bars(B, [np.r_[a + n * depth * s, z0 + h - 0.1]], [np.r_[b + n * depth * s, z0 + h - 0.1]], (0, 0, 1), 0.2, 0.25, 'vermilion', tag='main', caps=True)
        # roof: 切妻 along the wing
        mid = (a + b) / 2 + n * depth / 2
        ang = math.atan2(d[1], d[0])
        with Frame(B, mid[0], mid[1], z0, ang):
            roof.roof(B, L + 0.6, depth, h + 0.1, 1.0, kind='kirizuma', cover='hongawara', pitch=0.55, verge=0.6, rafter=0.3, rafter_mat='vermilion', rafter_end='gold',
                      fascia_mat='vermilion', bargeboard_mat='vermilion', ends='oni', ridge_h=0.4, ridge_w=0.4, edge=0.25)
        poly = LineString([tuple(a + n * depth / 2), tuple(b + n * depth / 2)]).buffer(depth / 2 + 0.2, cap_style='flat')
        prim.polygon(B, np.asarray(poly.exterior.coords)[:-1], z0 + 0.05, 'stone', tag='block')

# ------------------------------------------------------------------ 西楼門
def nishiromon(B, S, used):
    P, cx, cy, Ll, Ww, yaw = osm_rect(S, 105449683)
    # the long side runs N-S; the gate faces west (front u along N-S, v east through the passage)
    front_yaw = math.atan2(1.0, 0.1)
    # take the rect's own long-axis direction, pointing north
    d = np.array([math.cos(yaw), math.sin(yaw)])
    if d[1] < 0: d = -d
    ang = math.atan2(d[1], d[0])                       # local u -> north; local v -> rotate +90 = west... flip:
    ang = ang + math.pi                                # u -> south, v -> east (into the precinct)
    zf = float(S.ground(cx + 3.0, cy)) + 0.15          # gate floor at the top of the steps
    with Frame(B, cx, cy, zf, ang):
        info = romon(B, 7.9, 4.6, 3.95, 2.0, o_roof=2.1, pitch=0.62, scale=0.95)
        # 随身 statues in the side bays (simple seated figures)
        for s in (-1, 1):
            u = s * 7.9 / 3
            prim.box(B, u - 0.5, -0.4, 0.0, u + 0.5, 0.4, 0.6, 'wood_dark', tag='detail')
            prim.lathe(B, (u, 0.0, 0.6), [(0.4, 0.0), (0.42, 0.4), (0.3, 0.9), (0.18, 1.1), (0.16, 1.35), (0.0, 1.45)], 10, 'vermilion', tag='detail')
        # wings: from the gate's north and south ends, 5 bays then bending forward (west, -v)
        wing(B, [(-5.2, 1.0), (-12.6, 1.0), (-12.6, -5.2)], 0.0, depth=2.0, h=3.3, side=-1)
        wing(B, [(5.2, 1.0), (12.6, 1.0), (12.6, -5.2)], 0.0, depth=2.0, h=3.3, side=1)
        # gate floor walk + blockers on the side bays
        prim.polygon(B, [(-4.4, -3.4), (4.4, -3.4), (4.4, 3.4), (-4.4, 3.4)], 0.02, 'stone', tag='walk')
        for s in (-1, 1):
            prim.polygon(B, [(s * 1.4, -2.4), (s * 4.0, -2.4), (s * 4.0, 2.4), (s * 1.4, 2.4)], 0.05, 'stone', tag='block')
        # the landing in front and the stairs down to the 祇園 crossing
        prim.box(B, -6.5, -4.8, -2.9, 6.5, -2.2, 0.0, 'stone', tag='main', faces='yZ')
        prim.polygon(B, [(-6.5, -4.8), (6.5, -4.8), (6.5, -2.2), (-6.5, -2.2)], 0.0, 'stone', tag='walk')
    # stairs: west from the landing down to the pavement (global)
    zl = zf
    p_top = np.array([cx, cy]) + np.array([math.cos(ang + math.pi / 2), math.sin(ang + math.pi / 2)]) * -4.8
    dirw = -np.array([math.cos(ang + math.pi / 2), math.sin(ang + math.pi / 2)])
    zbot = float(S.ground(*(p_top + dirw * 9.5)))
    run = (zl - zbot) / 0.16 * 0.36
    p_bot = p_top + dirw * run
    arch.stairs(B, tuple(p_bot), tuple(p_top), zbot, zl, 11.5, 'stone')
    # 社号標 (the stone pillar 八坂神社) and the komainu
    side = np.array([-dirw[1], dirw[0]])
    q = p_bot + side * 7.4 + dirw * 0.8
    prim.box(B, q[0] - 0.45, q[1] - 0.45, zbot, q[0] + 0.45, q[1] + 0.45, zbot + 4.6, 'stone', tag='main')
    M.oquad(B, [(q[0] + dirw[0] * 0.46 - side[0] * 0.3, q[1] + dirw[1] * 0.46 - side[1] * 0.3, zbot + 0.6), (q[0] + dirw[0] * 0.46 + side[0] * 0.3, q[1] + dirw[1] * 0.46 + side[1] * 0.3, zbot + 0.6),
                (q[0] + dirw[0] * 0.46 + side[0] * 0.3, q[1] + dirw[1] * 0.46 + side[1] * 0.3, zbot + 4.3), (q[0] + dirw[0] * 0.46 - side[0] * 0.3, q[1] + dirw[1] * 0.46 - side[1] * 0.3, zbot + 4.3)],
            (dirw[0], dirw[1], 0), 'stone', tag='detail', c1=(0, 7, 3, 0))
    for (x, y) in ((1703.0, 1996.4), (1701.0, 1983.6)):
        z = zl
        prim.box(B, x - 0.6, y - 0.6, z - 0.1, x + 0.6, y + 0.6, z + 1.3, 'stone', tag='main')
        prim.lathe(B, (x, y, z + 1.3), [(0.45, 0.0), (0.5, 0.3), (0.42, 0.8), (0.3, 1.2), (0.36, 1.45), (0.2, 1.7), (0.0, 1.75)], 10, 'bronze', tag='main')
        prim.polygon(B, [(x - 0.7, y - 0.7), (x + 0.7, y - 0.7), (x + 0.7, y + 0.7), (x - 0.7, y + 0.7)], z + 0.1, 'stone', tag='block')
    # clipped azalea mounds either side of the stairs above the street wall, the vermilion fence along the pavement
    for (a, b) in (((1699.0, 1997.5), (1702.0, 2007.0)), ((1698.0, 1983.0), (1693.0, 1956.0))):
        arch.hedge(B, [a, b], 0.0, h=1.6, w=4.5, ground=lambda x, y: float(S.ground(x, y)))
    for (a, b) in (((1692.6, 1997.5), (1695.6, 2012.0)), ((1692.2, 1984.0), (1687.6, 1956.0))):
        fence(B, S, a, b)
    exclude_matching(S, P, used)
    for b_ in S.osm['barriers']:
        if b_['id'] in (288051722, 288051937):
            for l in b_['line']:
                if len(l) >= 3:
                    Pw = Polygon(l).buffer(0.5)
                    exclude_matching(S, Pw, used, frac=0.2)

def fence(B, S, a, b, h=0.9):
    """the vermilion wooden fence on the stone wall along the 東大路通 pavement"""
    a = np.asarray(a, float); b = np.asarray(b, float); d = b - a; L = np.linalg.norm(d); d /= L
    n = max(2, int(L / 1.6))
    pts = [a + d * L * i / n for i in range(n + 1)]
    zs = [float(S.ground(*p)) for p in pts]
    for p, z in zip(pts, zs):
        prim.box(B, p[0] - 0.07, p[1] - 0.07, z, p[0] + 0.07, p[1] + 0.07, z + h + 0.1, 'vermilion', tag='main')
    for k in range(n):
        p, q = pts[k], pts[k + 1]
        for zz in (0.35, h):
            M.bars(B, [(p[0], p[1], zs[k] + zz)], [(q[0], q[1], zs[k + 1] + zz)], (0, 0, 1), 0.08, 0.06, 'vermilion', tag='main')
    seg = LineString([tuple(a), tuple(b)]).buffer(0.3, cap_style='flat')
    prim.polygon(B, np.asarray(seg.exterior.coords)[:-1], float(np.mean(zs)) + 0.2, 'stone', tag='block')

# ------------------------------------------------------------------ 舞殿
def buden(B, S, used):
    P, cx, cy, Ll, Ww, yaw = osm_rect(S, 105449709)
    zg = float(S.ground(cx, cy))
    zst = 1.05                                   # stage floor
    with Frame(B, cx, cy, zg, yaw):
        L, D = 8.4, 7.4
        us = np.linspace(-L / 2, L / 2, 4); vs = np.linspace(-D / 2, D / 2, 4)
        # stone base and the stage platform (wooden floor)
        arch.platform(B, [(-L / 2 - 0.9, -D / 2 - 0.9), (L / 2 + 0.9, -D / 2 - 0.9), (L / 2 + 0.9, D / 2 + 0.9), (-L / 2 - 0.9, D / 2 + 0.9)], -0.2, 0.25, mat='stone', walk=False)
        prim.box(B, -L / 2 - 0.5, -D / 2 - 0.5, zst - 0.18, L / 2 + 0.5, D / 2 + 0.5, zst, 'wood_natural', tag='main')
        for x in np.linspace(-L / 2, L / 2, 7):
            for y in (-D / 2 - 0.3, D / 2 + 0.3):
                prim.box(B, x - 0.1, y - 0.1, 0.25, x + 0.1, y + 0.1, zst - 0.18, 'wood_dark', tag='detail')
        pillars(B, us, vs, zst, zst + 3.6, r=0.17, mat='vermilion', ring_only=True, base=False)
        frame_beams(B, us, vs, zst + 3.55, h=0.32)
        arch.nageshi(B, L, D, zst + 2.9, 'vermilion', h=0.18, w=0.1, out=0.0)
        # low railing around the stage
        a, c = L / 2 + 0.4, D / 2 + 0.4
        arch.railing(B, [(-a, -c), (a, -c), (a, c), (-a, c)], zst, h=0.55, mat='vermilion', cap_mat='gold', giboshi=False, closed=True)
        top, reach = arch.bracket_row(B, L, D, zst + 3.6, 'demitsudo', 0.8, 'vermilion', 'white_paint', us=us, vs=vs)
        h = roof.roof(B, L + 2 * reach, D + 2 * reach, top, 2.0, kind='irimoya', cover='copper', pitch=0.62, teri=1.6, sori=0.4,
                      rafter=0.25, rafter_mat='vermilion', rafter_end='gold', fascia_mat='vermilion', bargeboard_mat='vermilion', ends='oni', gable_frac=0.5)
        # the lanterns: three rows on a frame under the eaves on all four sides, lit
        lantern_rows(B, L, D, zst + 3.05, rows=3)
        prim.polygon(B, [(-L / 2 - 0.9, -D / 2 - 0.9), (L / 2 + 0.9, -D / 2 - 0.9), (L / 2 + 0.9, D / 2 + 0.9), (-L / 2 - 0.9, D / 2 + 0.9)], 0.3, 'stone', tag='block')
    exclude_matching(S, P, used)

def lantern_rows(B, L, D, z_top, rows=3, r=0.15, h=0.42, gap=0.035, seg=8):
    """rows of white paper lanterns hung edge to edge on rails between the pillars (batched lathe, one add)"""
    prof = [(r * 0.72, 0.0), (r * 0.96, h * 0.2), (r, h * 0.5), (r * 0.96, h * 0.8), (r * 0.72, h)]
    th = np.linspace(0, 2 * math.pi, seg + 1)
    ring = np.array([(pr * math.cos(t), pr * math.sin(t), pz) for (pr, pz) in prof for t in th])
    nr = len(prof); m = seg + 1
    It = []
    for j in range(nr - 1):
        for i in range(seg):
            a = j * m + i
            It += [[a, a + 1, a + m + 1], [a, a + m + 1, a + m]]
    It = np.array(It)
    centres = []
    a, c = L / 2 + 0.45, D / 2 + 0.45
    sides = [((-a, -c), (a, -c)), ((a, -c), (a, c)), ((a, c), (-a, c)), ((-a, c), (-a, -c))]
    for k in range(rows):
        zt = z_top - k * (h + 0.16)
        for (p0, p1) in sides:
            p0 = np.array(p0); p1 = np.array(p1); L_ = np.linalg.norm(p1 - p0)
            n = int(L_ / (2 * r + gap))
            for i in range(n):
                p = p0 + (p1 - p0) * (i + 0.5) / n
                centres.append((p[0], p[1], zt - h - 0.05))
        # the rail they hang from
        M.bars(B, [(-a, -c, zt + 0.03), (a, -c, zt + 0.03), (a, c, zt + 0.03), (-a, c, zt + 0.03)], [(a, -c, zt + 0.03), (a, c, zt + 0.03), (-a, c, zt + 0.03), (-a, -c, zt + 0.03)],
               (0, 0, 1), 0.05, 0.06, 'wood_dark', tag='detail')
    C = np.array(centres)
    V = (C[:, None, :] + ring[None, :, :]).reshape(-1, 3)
    I = (np.arange(len(C))[:, None, None] * len(ring) + It[None]).reshape(-1, 3)
    UV = np.tile(np.c_[np.tile(th, nr) * r, np.repeat([p[1] for p in prof], m)], (len(C), 1))
    B.add(V, I, 'lamp', UV=UV, smooth=True, tag='main')
    # black caps (top and bottom rings) as thin bars around each lantern row would cost a lot: one dark band per row
    for k in range(rows):
        zt = z_top - k * (h + 0.16)
        for zz in (zt - 0.05, zt - h - 0.05):
            M.bars(B, [(-a, -c, zz), (a, -c, zz), (a, c, zz), (-a, c, zz)], [(a, -c, zz), (a, c, zz), (-a, c, zz), (-a, -c, zz)], (0, 0, 1), 0.03, 2 * r * 0.75, 'black_lacquer', tag='detail')
    for (x, y) in ((-a, -c), (a, -c), (a, c), (-a, c), (0, -c), (0, c), (-a, 0), (a, 0)):
        B.lamp(x, y, z_top - 0.6, 30.0, (1.0, 0.78, 0.55))

# ------------------------------------------------------------------ 本殿 (祇園造)
def honden(B, S, used):
    P, cx, cy, Ll, Ww, yaw = osm_rect(S, 88108397)
    # long axis E-W, the front (向拝) to the south: local u east, v north (into the hall from the front)
    d = np.array([math.cos(yaw), math.sin(yaw)])
    if d[0] < 0: d = -d
    ang = math.atan2(d[1], d[0])
    zg = float(S.ground(cx, cy - 8.0))
    zf = 1.25                                        # floor of the hall
    with Frame(B, cx, cy, zg, ang):
        L, D = 21.0, 15.0                            # 七間 x 六間 (the main body under the great roof)
        us = np.linspace(-L / 2, L / 2, 8); vs = np.linspace(-D / 2, D / 2, 7)
        arch.platform(B, [(-L / 2 - 3.6, -D / 2 - 2.6), (L / 2 + 3.6, -D / 2 - 2.6), (L / 2 + 3.6, D / 2 + 3.2), (-L / 2 - 3.6, D / 2 + 3.2)], -0.3, 0.4, mat='stone', walk=False)
        prim.box(B, -L / 2 - 1.2, -D / 2 - 1.2, zf - 0.15, L / 2 + 1.2, D / 2 + 1.2, zf, 'wood_natural', tag='main')
        prim.box(B, -L / 2 + 0.3, -D / 2 + 0.3, 0.4, L / 2 - 0.3, D / 2 - 0.3, zf - 0.15, 'black_lacquer', tag='main', faces='xXyY')
        for x in np.linspace(-L / 2 - 1.0, L / 2 + 1.0, 12):
            for y in (-D / 2 - 1.0, D / 2 + 1.0):
                prim.box(B, x - 0.08, y - 0.08, 0.4, x + 0.08, y + 0.08, zf - 0.15, 'wood_dark', tag='detail')
        pillars(B, us, vs, zf, zf + 4.6, r=0.22, mat='vermilion', ring_only=True, base=False)
        frame_beams(B, us, vs, zf + 4.55, h=0.38)
        arch.nageshi(B, L, D, zf + 3.6, 'vermilion', h=0.22, w=0.12, out=0.0)
        arch.nageshi(B, L, D, zf + 0.6, 'vermilion', h=0.22, w=0.12, out=0.0)
        # front: 蔀戸 (black lattice) between vermilion pillars, white walls with gold fittings on the sides
        for i in range(7):
            arch.infill(B, (us[i], vs[0]), (us[i + 1], vs[0]), zf + 0.65, zf + 3.55, 'shitomi', out=(0, -1), mat='black_lacquer')
            arch.infill(B, (us[i], vs[0]), (us[i + 1], vs[0]), zf + 3.62, zf + 4.4, 'plaster', out=(0, -1))
            arch.infill(B, (us[i + 1], vs[-1]), (us[i], vs[-1]), zf + 0.65, zf + 4.4, 'plaster', out=(0, 1))
        for j in range(6):
            for (x, o) in ((us[0], -1), (us[-1], 1)):
                arch.infill(B, (x, vs[j]), (x, vs[j + 1]), zf + 0.65, zf + 4.4, 'plaster' if j % 2 else 'board', out=(o, 0), mat='vermilion')
        top, reach = arch.bracket_row(B, L, D, zf + 4.6, 'demitsudo', 0.9, 'vermilion', 'gold', us=us, vs=vs)
        # the great 入母屋 roof of cypress bark, very deep eaves (it covers the side 又庇 too)
        h = roof.roof(B, L + 2 * reach, D + 2 * reach, top, 3.4, kind='irimoya', cover='hiwada', pitch=0.82, teri=1.7, sori=0.55, sori_len=0.35,
                      gable_frac=0.38, verge=1.4, edge=0.45, rafter=0.3, rafter_mat='vermilion', rafter_end='gold', fascia_mat='vermilion',
                      bargeboard_mat='vermilion', ends='oni', ridge_h=0.9, ridge_w=0.75)
        # 又庇: lower lean-to roofs along the east, west and back (north) sides over the corridors
        for (side, u0, u1) in (('e', -D / 2 - 1.0, D / 2 + 1.0), ('w', -D / 2 - 1.0, D / 2 + 1.0)):
            s = 1 if side == 'e' else -1
            with Frame(B, s * (L / 2 + reach + 0.6), 0.0, 0.0, math.pi / 2 if s > 0 else -math.pi / 2):
                M.hisashi(B, u0, u1, zf + 3.0, depth=3.2, pitch=0.55, v=0.0, roof='hiwada', brackets=np.linspace(u0 + 0.5, u1 - 0.5, 6))
            for y in np.linspace(-D / 2, D / 2, 4):
                arch.pillar(B, s * (L / 2 + reach + 3.0), y, zf - 0.6, zf + 2.75, 0.17, 'vermilion', base=True)
        with Frame(B, 0.0, D / 2 + reach + 0.6, 0.0, math.pi):
            M.hisashi(B, -L / 2 - 1.0, L / 2 + 1.0, zf + 3.0, depth=3.0, pitch=0.55, v=0.0, roof='hiwada', brackets=np.linspace(-L / 2, L / 2, 8))
        # the 向拝: three bays on the front, its own curved lean-to roof, vermilion pillars, the bells and ropes
        hu = np.linspace(-L / 2 + 3.0, L / 2 - 3.0, 4)
        vf = -D / 2 - reach - 5.4
        zk = zf + 2.6                                 # the 向拝 eave
        for x in hu:
            arch.pillar(B, x, vf, 0.4, zk - 0.25, 0.2, 'vermilion', base=True)
            prim.box(B, x - 0.1, vf, zk - 0.6, x + 0.1, -D / 2, zk - 0.38, 'vermilion', tag='main')      # 海老虹梁 (as a beam)
        M.bars(B, [(hu[0] - 0.4, vf, zk - 0.25)], [(hu[-1] + 0.4, vf, zk - 0.25)], (0, 0, 1), 0.3, 0.4, 'vermilion', tag='main', caps=True)
        M.bars(B, [(hu[0] - 0.4, vf - 0.21, zk - 0.25)], [(hu[-1] + 0.4, vf - 0.21, zk - 0.25)], (0, 0, 1), 0.1, 0.02, 'gold', tag='detail')
        with Frame(B, 0.0, -D / 2 - reach - 2.6, 0.0, 0.0):
            M.hisashi(B, hu[0] - 1.6, hu[-1] + 1.6, zk, depth=3.8, pitch=0.42, v=0.0, roof='hiwada', brackets=hu)
        for i in range(3):
            xm = (hu[i] + hu[i + 1]) / 2
            prim.lathe(B, (xm, vf + 0.6, zk - 0.9), [(0.0, 0.0), (0.2, 0.05), (0.26, 0.25), (0.18, 0.45), (0.06, 0.5), (0.0, 0.55)], 10, 'gold', tag='detail')
            prim.cyl(B, (xm, vf + 0.6, 0.45), (xm, vf + 0.6, zk - 0.9), 0.05, 0.05, 6, 'white_paint', tag='detail')
            prim.cyl(B, (xm + 0.12, vf + 0.6, 0.6), (xm + 0.12, vf + 0.6, zk - 0.9), 0.035, 0.035, 6, 'vermilion', tag='detail')
        # a twisted straw rope (注連縄) across the front of the 向拝
        rope = np.array([(x, vf - 0.05, zk - 0.7 - 0.25 * math.sin((x - hu[0]) / (hu[-1] - hu[0]) * math.pi * 3) ** 2) for x in np.linspace(hu[0], hu[-1], 25)])
        prim.sweep(B, rope, [(0.09 * math.cos(t), 0.09 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 7)[:-1]], 'bamboo', tag='detail', smooth=True)
        # offering box
        prim.box(B, -2.0, vf + 1.2, 0.4, 2.0, vf + 2.2, 1.4, 'wood_dark', tag='main')
        # steps up to the hall floor behind the offering box
        arch.stairs(B, (0.0, -D / 2 - 2.6), (0.0, -D / 2 - 1.2), 0.4, zf, 5.0, 'wood_natural')
        prim.polygon(B, [(-L / 2 - 3.6, -D / 2 - 2.6), (L / 2 + 3.6, -D / 2 - 2.6), (L / 2 + 3.6, D / 2 + 3.2), (-L / 2 - 3.6, D / 2 + 3.2)], 0.45, 'stone', tag='block')
    exclude_matching(S, P, used)

# ------------------------------------------------------------------ 南楼門
def minamiromon(B, S, used):
    P, cx, cy, Ll, Ww, yaw = osm_rect(S, 88108386)
    d = np.array([math.cos(yaw), math.sin(yaw)])
    if d[0] < 0: d = -d
    ang = math.atan2(d[1], d[0])                     # u east, v north (into the precinct)
    zf = float(S.ground(cx, cy)) + 0.2
    with Frame(B, cx, cy, zf, ang):
        romon(B, 9.6, 5.4, 4.6, 2.5, o_roof=2.5, pitch=0.66, scale=1.1)
        prim.polygon(B, [(-5.0, -3.5), (5.0, -3.5), (5.0, 3.5), (-5.0, 3.5)], 0.02, 'stone', tag='walk')
        for s in (-1, 1):
            prim.polygon(B, [(s * 1.7, -2.8), (s * 4.9, -2.8), (s * 4.9, 2.8), (s * 1.7, 2.8)], 0.05, 'stone', tag='block')
    # the stone torii (正保3) on the approach south of the gate
    tz = float(S.ground(1798.5, 1884.0))
    stone_torii(B, 1798.5, 1884.0, tz, ang, h=9.0, span=6.6)
    exclude_matching(S, P, used)

def stone_torii(B, x, y, z, yaw, h=9.0, span=6.6):
    r = 0.42
    with Frame(B, x, y, z, yaw):
        for s in (-1, 1):
            prim.cyl(B, (s * span / 2, 0, 0), (s * (span / 2 - h * 0.025), 0, h * 0.86), r, r * 0.92, 14, 'stone', caps=(False, True))
            prim.cyl(B, (s * span / 2, 0, 0), (s * span / 2, 0, 0.5), r * 1.35, r * 1.3, 14, 'stone')
        prim.obox(B, (-span / 2 - 0.8, 0, h * 0.68), (span / 2 + 0.8, 0, h * 0.68), r * 0.9, r * 1.3, 'stone')
        prim.obox(B, (0, 0, h * 0.68 + 0.6), (0, 0, h * 0.86), 0.5, 0.4, 'stone')
        xs = np.linspace(-span / 2 - 1.3, span / 2 + 1.3, 13)
        lift = lambda xx: 0.35 * (abs(xx) / xs[-1]) ** 2.2
        pts = np.array([(xx, 0, h * 0.87 + 0.3 + lift(xx)) for xx in xs])
        prim.sweep(B, pts, [(-0.4, -0.3), (0.4, -0.3), (0.4, 0.3), (-0.4, 0.3)], 'stone', caps=True)
        pts2 = np.array([(xx * 1.05, 0, h * 0.87 + 0.95 + lift(xx) * 1.3) for xx in xs])
        prim.sweep(B, pts2, [(-0.5, -0.32), (0.5, -0.32), (0.55, 0.32), (-0.55, 0.32)], 'stone', caps=True)
        for s in (-1, 1):
            prim.polygon(B, [(s * span / 2 - 0.6, -0.6), (s * span / 2 + 0.6, -0.6), (s * span / 2 + 0.6, 0.6), (s * span / 2 - 0.6, 0.6)], 0.1, 'stone', tag='block')

# ------------------------------------------------------------------ the other halls
def small_shrine(B, S, oid, used, face=None, h_roof=1.0, scale=1.0, cover='copper'):
    """a 流造 small shrine fitted to an OSM footprint; faces `face` (unit vector) or the long side's south/west"""
    P, cx, cy, Ll, Ww, yaw = osm_rect(S, oid)
    zg = float(S.ground(cx, cy))
    L = max(1.8, Ll - 1.2); D = max(1.4, Ww - 1.2)
    with Frame(B, cx, cy, zg, yaw):
        arch.platform(B, [(-L / 2 - 0.5, -D / 2 - 0.8), (L / 2 + 0.5, -D / 2 - 0.8), (L / 2 + 0.5, D / 2 + 0.5), (-L / 2 - 0.5, D / 2 + 0.5)], -0.2, 0.35, walk=False)
        nb = max(1, int(round(L / 2.0)))
        us = np.linspace(-L / 2, L / 2, nb + 1)
        for x in us:
            for y in (-D / 2, D / 2):
                arch.pillar(B, x, y, 0.35, 0.35 + 2.4 * scale, 0.12, 'vermilion', base=False)
        for i in range(nb):
            arch.infill(B, (us[i], -D / 2), (us[i + 1], -D / 2), 0.5, 0.35 + 2.3 * scale, 'koshi', out=(0, -1), mat='vermilion')
            arch.infill(B, (us[i + 1], D / 2), (us[i], D / 2), 0.5, 0.35 + 2.3 * scale, 'plaster', out=(0, 1))
        for (x, o) in ((-L / 2, -1), (L / 2, 1)):
            arch.infill(B, (x, -D / 2) if o < 0 else (x, D / 2), (x, D / 2) if o < 0 else (x, -D / 2), 0.5, 0.35 + 2.3 * scale, 'plaster', out=(o, 0))
        prim.box(B, -L / 2 - 0.3, -D / 2 - 0.3, 0.3, L / 2 + 0.3, D / 2 + 0.3, 0.42, 'wood_natural', tag='main')
        arch.ring_beam(B, L, D, 0.35 + 2.4 * scale, 0.16, 0.24, 'vermilion')
        # 流造: the front slope runs long over a 向拝 (an asymmetric gable): two lean-tos
        with Frame(B, 0, -0.25, 0, 0):
            roof.roof(B, L + 0.2, D + 0.5, 0.35 + 2.55 * scale, 1.1, kind='kirizuma', cover=cover, pitch=0.55, verge=0.5, rafter=0.2, rafter_mat='vermilion', rafter_end='gold',
                      fascia_mat='vermilion', bargeboard_mat='vermilion', ends=None, ridge_h=0.3, ridge_w=0.35, edge=0.18)
        M.hisashi(B, -L / 2 - 0.5, L / 2 + 0.5, 0.35 + 2.0 * scale, depth=1.3, pitch=0.35, v=-D / 2 - 1.05, roof='copper' if cover == 'copper' else 'hiwada')
        for x in (-L / 2 + 0.2, L / 2 - 0.2):
            arch.pillar(B, x, -D / 2 - 2.0, 0.35, 0.35 + 2.0 * scale - 0.15, 0.1, 'vermilion', base=False)
        prim.polygon(B, [(-L / 2 - 0.5, -D / 2 - 0.8), (L / 2 + 0.5, -D / 2 - 0.8), (L / 2 + 0.5, D / 2 + 0.5), (-L / 2 - 0.5, D / 2 + 0.5)], 0.4, 'stone', tag='block')
    exclude_matching(S, P, used)

def open_hall(B, S, oid, used, h=4.0, cover='hongawara', pitch=0.6, kind='irimoya', walls=False):
    """an open pillared hall (絵馬堂 / 能舞台) on a low platform"""
    P, cx, cy, Ll, Ww, yaw = osm_rect(S, oid)
    zg = float(S.ground(cx, cy))
    L = Ll - 3.0; D = Ww - 3.0
    with Frame(B, cx, cy, zg, yaw):
        arch.platform(B, [(-L / 2 - 0.8, -D / 2 - 0.8), (L / 2 + 0.8, -D / 2 - 0.8), (L / 2 + 0.8, D / 2 + 0.8), (-L / 2 - 0.8, D / 2 + 0.8)], -0.2, 0.3)
        nb = max(1, int(round(L / 3.0))); nd = max(1, int(round(D / 3.0)))
        us, vs = arch.grid(L, D, nb, nd)
        pillars(B, us, vs, 0.3, h, r=0.18, ring_only=True, base=True)
        frame_beams(B, us, vs, h - 0.05, h=0.32)
        if walls:
            for i in range(nb):
                arch.infill(B, (us[i + 1], vs[-1]), (us[i], vs[-1]), 0.4, h - 0.4, 'plaster', out=(0, 1))
        top, reach = arch.bracket_row(B, L, D, h, 'funa', 0.8, 'vermilion', 'white_paint', us=us, vs=vs)
        roof.roof(B, L + 2 * reach, D + 2 * reach, top, 1.6, kind=kind, cover=cover, pitch=pitch, rafter=0.28, rafter_mat='vermilion', rafter_end='white_paint',
                  fascia_mat='vermilion', bargeboard_mat='vermilion', ends='oni')
        for x in us:
            for y in (vs[0], vs[-1]):
                prim.polygon(B, [(x - 0.3, y - 0.3), (x + 0.3, y - 0.3), (x + 0.3, y + 0.3), (x - 0.3, y + 0.3)], 0.35, 'stone', tag='block')
        prim.polygon(B, [(-L / 2 - 0.8, -D / 2 - 0.8), (L / 2 + 0.8, -D / 2 - 0.8), (L / 2 + 0.8, D / 2 + 0.8), (-L / 2 - 0.8, D / 2 + 0.8)], 0.3, 'stone', tag='walk')
    exclude_matching(S, P, used)

def minor_halls(B, S, used):
    open_hall(B, S, 288051766, used, h=4.2, cover='hongawara', kind='irimoya')            # 絵馬堂
    open_hall(B, S, 328903229, used, h=3.6, cover='hiwada', kind='irimoya', pitch=0.7)    # 能舞台
    # 神輿庫 (1928 storehouse): white walls, vermilion posts, 入母屋 tiles
    P, cx, cy, Ll, Ww, yaw = osm_rect(S, 328903339)
    zg = float(S.ground(cx, cy))
    with Frame(B, cx, cy, zg, yaw):
        L, D = Ll - 2.6, Ww - 2.6
        prim.box(B, -L / 2, -D / 2, -0.3, L / 2, D / 2, 0.4, 'stone', tag='main', faces='xXyYZ')
        for side in range(4):
            pass
        us, vs = arch.grid(L, D, max(1, int(L / 2.4)), max(1, int(D / 2.4)))
        pillars(B, us, vs, 0.4, 5.0, r=0.18, ring_only=True, base=False)
        for i in range(len(us) - 1):
            for (y, o) in ((vs[0], (0, -1)), (vs[-1], (0, 1))):
                arch.infill(B, (us[i], y) if o[1] < 0 else (us[i + 1], y), (us[i + 1], y) if o[1] < 0 else (us[i], y), 0.45, 4.9, 'plaster', out=o)
        for j in range(len(vs) - 1):
            for (x, o) in ((us[0], (-1, 0)), (us[-1], (1, 0))):
                arch.infill(B, (x, vs[j + 1]) if o[0] < 0 else (x, vs[j]), (x, vs[j]) if o[0] < 0 else (x, vs[j + 1]), 0.45, 4.9, 'plaster', out=o)
        frame_beams(B, us, vs, 5.0, h=0.35)
        roof.roof(B, L, D, 5.1, 1.3, kind='irimoya', cover='hongawara', pitch=0.6, rafter=0.3, rafter_mat='vermilion', rafter_end='white_paint', fascia_mat='vermilion',
                  bargeboard_mat='vermilion', ends='oni')
        prim.polygon(B, [(-L / 2, -D / 2), (L / 2, -D / 2), (L / 2, D / 2), (-L / 2, D / 2)], 0.45, 'stone', tag='block')
    exclude_matching(S, P, used)
    for oid in (288051962, 328903341, 288051736, 288051700, 328903342):                   # 疫神社, 美御前社, 大国主社, 太田社, 蛭子社
        try: small_shrine(B, S, oid, used, scale=1.0 if oid in (288051962, 328903341) else 0.8)
        except Exception as e: print('small shrine fail', oid, repr(e))

# ------------------------------------------------------------------ the precinct: ground, lanterns, trees
def precinct(B, S, used):
    poly = Polygon(S.polygon[0][0], S.polygon[0][1:]) if S.polygon else None
    if poly is None: return
    poly = poly.buffer(0)
    S.paint.append({'poly': [list(map(float, c)) for c in list(poly.exterior.coords)[:-1]], 'surf': 'gravel'})
    # stone-slab paths (the OSM footways of the precinct)
    paths = []
    for w in S.osm['ways']:
        if w['tags'].get('highway') not in ('footway', 'steps', 'path', 'pedestrian'): continue
        for l in w['line']:
            if len(l) < 2: continue
            g = LineString(l)
            if g.intersects(poly): paths.append(g.intersection(poly.buffer(2)))
    for g in paths:
        for gg in (g.geoms if hasattr(g, 'geoms') else [g]):
            if gg.geom_type != 'LineString' or gg.length < 1: continue
            S.paint.append({'poly': [list(map(float, c)) for c in list(gg.buffer(1.6, cap_style='flat').exterior.coords)[:-1]], 'surf': 'stone_slab'})
    # the main axes: from the 西楼門 east to the 本殿 court, and 南楼門 north to the 舞殿
    axes = [LineString([(1716.0, 1989.0), (1733.0, 1987.0), (1740.0, 1964.0), (1753.0, 1956.0), (1792.0, 1953.0)]),
            LineString([(1799.0, 1906.0), (1800.0, 1925.0), (1801.0, 1944.0)])]
    for ax in axes:
        S.paint.append({'poly': [list(map(float, c)) for c in list(ax.buffer(2.6, cap_style='flat').exterior.coords)[:-1]], 'surf': 'stone_slab'})
        # stone lanterns in pairs along the axis
        t = 4.0
        while t < ax.length - 3:
            p = ax.interpolate(t); q = ax.interpolate(min(ax.length, t + 1))
            d = np.array([q.x - p.x, q.y - p.y]); d /= max(np.linalg.norm(d), 1e-9); n = np.array([-d[1], d[0]])
            for s in (-1, 1):
                x, y = p.x + n[0] * s * 4.0, p.y + n[1] * s * 4.0
                if any(Polygon(S.osm_building(o)['poly'][0][0]).buffer(1.5).contains(Point(x, y)) for o in (105449709, 88108397, 288051962)): continue
                z = float(S.ground(x, y))
                arch.ishidoro(B, x, y, z, h=2.2)
                prim.polygon(B, [(x - 0.4, y - 0.4), (x + 0.4, y - 0.4), (x + 0.4, y + 0.4), (x - 0.4, y + 0.4)], z + 0.1, 'stone', tag='block')
            t += 7.0
    # trees: OSM trees of the precinct + the wooded edges (keyaki / kashi / sugi / momiji), keeping the courts open
    rng = np.random.default_rng(3)
    blocked = shapely.unary_union([Polygon(b['poly'][0][0]).buffer(3.0) for b in S.osm['buildings'] if Polygon(b['poly'][0][0]).intersects(poly)] +
                                  [g.buffer(2.0) for g in paths] + [ax.buffer(5.0) for ax in axes] +
                                  [Point(1803, 1960).buffer(22.0), Point(1712, 1989).buffer(12.0)])
    pts = []
    for t in S.osm['trees']:
        x, y = t['xy']
        if poly.contains(Point(x, y)):
            pts.append((x, y))
    for lu in S.osm['landuse']:
        if lu['kind'] not in ('forest', 'wood', 'scrub', 'grass', 'park', 'garden'): continue
        for pp in lu['poly']:
            g = Polygon(pp[0]).buffer(0).intersection(poly)
            if g.is_empty: continue
            n = int(g.area / 45.0)
            x0, y0, x1, y1 = g.bounds
            for _ in range(n * 3):
                x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
                if g.contains(Point(x, y)): pts.append((x, y))
    # the precinct's outer band (inside the boundary) is wooded
    band = poly.difference(poly.buffer(-12.0))
    x0, y0, x1, y1 = band.bounds
    for _ in range(900):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if band.contains(Point(x, y)): pts.append((x, y))
    placed = []
    for (x, y) in pts:
        if blocked.contains(Point(x, y)): continue
        if any((x - a) ** 2 + (y - b) ** 2 < 36 for (a, b) in placed): continue
        placed.append((x, y))
    sp = ['keyaki', 'kashi', 'sugi', 'momiji', 'kashi', 'ichou', 'matsu']
    for k, (x, y) in enumerate(placed):
        B.tree(sp[rng.integers(len(sp))], x, y, float(S.ground(x, y)), rng.uniform(0.9, 1.3), rng.uniform(0, 6.28))
    print('shrine trees', len(placed))
