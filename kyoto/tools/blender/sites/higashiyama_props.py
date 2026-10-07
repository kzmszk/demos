"""東山 street life and enclosures: the black lantern-headed street lamps of the 重伝建 lanes, walls (土塀 with stone
bases and tiled copings, 石垣 retaining walls, hedges) from OSM along ねねの道 and 石塀小路, the gate at the top of
台所坂 (高台寺), trees where the photographs show them (産寧坂's willow, maples, cherries, pines), and the lane
corridors added to the exclusions (no generic poles / vending machines / trees on the hero lanes)."""
import math
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
from jk import prim, arch
from jk.core import Frame
from jk import roof as jroof
import sites.machiya as M
import sites.higashiyama_houses as HH
import sites.higashiyama_front as HF
import sites.higashiyama_lanes as HL

# ------------------------------------------------------------------ street lamps
def street_lamp(B, x, y, z, yaw=0.0, h=3.4, lit=True):
    """the black cast-iron lamp of 産寧坂 / 二年坂 / 八坂通: a slim post on a moulded base, a square lantern head with
    glass panes under a small pyramid cap and finial"""
    with Frame(B, x, y, z, yaw):
        prim.lathe(B, (0, 0, 0), [(0.13, 0.0), (0.13, 0.12), (0.09, 0.2), (0.075, 0.5), (0.06, 0.6)], 8, 'metal_dark', tag='main')
        prim.cyl(B, (0, 0, 0.6), (0, 0, h - 0.55), 0.055, 0.045, 8, 'metal_dark', caps=(False, False), tag='main')
        prim.lathe(B, (0, 0, h - 0.6), [(0.05, 0.0), (0.12, 0.05), (0.16, 0.08), (0.17, 0.1)], 8, 'metal_dark', tag='detail')
        a = 0.17; zl0 = h - 0.5; zl1 = h - 0.02
        prim.box(B, -a + 0.02, -a + 0.02, zl0, a - 0.02, a - 0.02, zl1, 'lamp', tag='main', faces='xXyY')
        # frame posts and the cap
        for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            prim.box(B, sx * a - 0.015, sy * a - 0.015, zl0, sx * a + 0.015, sy * a + 0.015, zl1, 'metal_dark', tag='detail')
        prim.box(B, -a - 0.02, -a - 0.02, zl0 - 0.04, a + 0.02, a + 0.02, zl0, 'metal_dark', tag='main', faces='zZxXyY')
        P = np.array([(-a - 0.08, -a - 0.08, zl1), (a + 0.08, -a - 0.08, zl1), (a + 0.08, a + 0.08, zl1), (-a - 0.08, a + 0.08, zl1), (0, 0, zl1 + 0.2)])
        B.add(P, [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4], [0, 2, 1], [0, 3, 2]], 'metal_dark', tag='main')
        prim.lathe(B, (0, 0, zl1 + 0.18), [(0.03, 0.0), (0.05, 0.04), (0.0, 0.12)], 6, 'metal_dark', tag='detail')
        prim.polygon(B, [(-0.2, -0.2), (0.2, -0.2), (0.2, 0.2), (-0.2, 0.2)], 0.05, 'stone', tag='block')
    if lit: B.lamp(x, y, z + h - 0.26, 22.0, (1.0, 0.8, 0.55))

KEEP_CLEAR = [(1822.7, 1414.0, 5.0), (1866.6, 1400.5, 4.0)]      # 庚申堂 gate, the pagoda entrance

def lamps_along(B, S, lane, lz, spacing=21.0, start=8.0, inset=0.15, skip=()):
    """lamps along both edges of the lane, alternating, on the line of the roof edges (in front of the gutters)"""
    L = lane.line; s = start; side = 1; n = 0
    while s < L.length - 4:
        if any(a - 1.5 <= s <= b + 1.5 for (a, b) in skip):
            s += 4.0; continue
        p, d, nrm = lane.frame(s)
        off = (np.interp(s, lane.st, lane.left) if side > 0 else np.interp(s, lane.st, lane.right)) - inset
        q = p + nrm * side * off
        if any(math.hypot(q[0] - x, q[1] - y) < r for (x, y, r) in KEEP_CLEAR) or off < (1.3 if lane.key.startswith('ishibe') else 1.7):
            s += 3.0; continue
        street_lamp(B, q[0], q[1], lz(*q), yaw=math.atan2(d[1], d[0]))
        n += 1; s += spacing; side = -side
    return n

# ------------------------------------------------------------------ walls and retaining walls from OSM
def ishigaki(B, a, b, ztop, zbot, batter=0.18, tag='main'):
    """a 石垣 face from a to b: bottom at zbot(x, y), top at ztop(x, y) (the high side to the left of a->b), battered
    back; a cut-stone coping"""
    a = np.asarray(a, float); b = np.asarray(b, float)
    d = b - a; L = float(np.linalg.norm(d))
    if L < 0.2: return
    d /= L; n = np.array([-d[1], d[0]])            # n points to the high side
    k = max(1, int(L / 1.5))
    Q = []
    for j in range(k):
        p = a + d * L * j / k; q = a + d * L * (j + 1) / k
        tp = ztop(*p); tq = ztop(*q); bp = zbot(*p) - 0.2; bq = zbot(*q) - 0.2
        hp = max(0.1, tp - bp); hq = max(0.1, tq - bq)
        P = [np.r_[p, bp], np.r_[q, bq], np.r_[q + n * batter * hq, tq], np.r_[p + n * batter * hp, tp]]
        Q.append(P)
        prim.obox(B, np.r_[p + n * (batter * hp + 0.15), tp + 0.06], np.r_[q + n * (batter * hq + 0.15), tq + 0.06], 0.35, 0.14, 'curb', tag='detail')
    Q = np.array(Q)
    fn = np.cross(Q[0, 1] - Q[0, 0], Q[0, 2] - Q[0, 0])
    if fn[:2] @ (-n) < 0: Q = Q[:, [1, 0, 3, 2]]
    M.quads(B, Q, 'stone', tag=tag)

def osm_walls(B, S, lz, lanes, protect, near_keys=('nene', 'ishibe', 'ishibe_n', 'ishibe_w', 'daidokoro', 'ninen', 'ichinen')):
    """walls, retaining walls, hedges and fences near the given lanes, from OSM"""
    zone = unary_union([lanes[k].line.buffer(9.0) for k in near_keys if k in lanes])
    n = 0
    for f in S.osm['barriers']:
        kind = f['tags'].get('barrier')
        for l in f['line']:
            g = LineString(l)
            if not g.intersects(zone): continue
            if protect.contains(g.centroid): continue
            if g.bounds[3] > 1749.5:
                g = g.intersection(Polygon([(0, 0), (5000, 0), (5000, 1749.5), (0, 1749.5)]))
                if g.is_empty or g.geom_type != 'LineString': continue
                l = list(g.coords)
            pts = [np.array(p, float) for p in l]
            h = float(f['tags'].get('height', 0) or 0)
            for a, b in zip(pts[:-1], pts[1:]):
                if np.linalg.norm(b - a) < 0.3: continue
                if kind == 'wall':
                    HH.coping_wall(B, a, b, lz, h=min(2.6, h) if h > 1.0 else 2.3, base=0.55, tint=(214, 184, 128) if n % 3 else (226, 214, 186), th=0.42)
                elif kind == 'retaining_wall':
                    d = (b - a) / np.linalg.norm(b - a); nn = np.array([-d[1], d[0]]); m = (a + b) / 2
                    zl = float(S.ground(*(m + nn * 1.5))); zr = float(S.ground(*(m - nn * 1.5)))
                    if abs(zl - zr) < 0.25:
                        # a low stone wall (石積み) where the ground is level across
                        prim.obox(B, np.r_[a, lz(*a) + 0.3], np.r_[b, lz(*b) + 0.3], 0.45, 0.9, 'stone', tag='main')
                    elif zl > zr:
                        ishigaki(B, a, b, lambda x, y: float(S.ground(x + nn[0] * 1.2, y + nn[1] * 1.2)) + 0.25, lambda x, y: lz(x - nn[0] * 1.2, y - nn[1] * 1.2))
                    else:
                        ishigaki(B, b, a, lambda x, y: float(S.ground(x - nn[0] * 1.2, y - nn[1] * 1.2)) + 0.25, lambda x, y: lz(x + nn[0] * 1.2, y + nn[1] * 1.2))
                    prim.obox(B, np.r_[a, lz(*a) + 0.6], np.r_[b, lz(*b) + 0.6], 0.5, 0.2, 'stone', tag='block')
                elif kind == 'hedge':
                    arch.hedge(B, [a, b], 0, h=max(1.1, min(2.5, h or 1.4)), w=0.8, ground=lambda x, y: lz(x, y))
                    prim.obox(B, np.r_[a, lz(*a) + 0.6], np.r_[b, lz(*b) + 0.6], 0.8, 0.2, 'stone', tag='block')
                elif kind == 'fence':
                    if f['tags'].get('fence_type') == 'wood' or h >= 1.5:
                        board_fence(B, a, b, lz, h=max(1.2, min(2.0, h or 1.6)))
                    else:
                        arch.takegaki(B, [a, b], 0, h=1.2, kind='yotsume', ground=lambda x, y: lz(x, y))
                    prim.obox(B, np.r_[a, lz(*a) + 0.6], np.r_[b, lz(*b) + 0.6], 0.2, 0.2, 'stone', tag='block')
                else:
                    continue
                n += 1
    return n

def board_fence(B, a, b, zf, h=1.8):
    """板塀: dark vertical boards between posts, a little capping board"""
    a = np.asarray(a, float); b = np.asarray(b, float); d = b - a; L = float(np.linalg.norm(d))
    if L < 0.3: return
    ang = math.atan2(d[1], d[0])
    z = min(zf(*a), zf(*b))
    with Frame(B, a[0], a[1], z, ang):
        M.front_rect(B, 0.0, L, -0.2, h, 0.0, 'wall_board', c0=(58, 46, 36, 0))
        M.front_rect(B, 0.0, L, -0.2, h, 0.02, 'wall_board', facing=1, c0=(58, 46, 36, 0))
        k = max(1, int(L / 1.8))
        us = np.linspace(0, L, k + 1)
        M.bars(B, np.c_[us, np.full(k + 1, -0.03), np.zeros(k + 1)], np.c_[us, np.full(k + 1, -0.03), np.full(k + 1, h + 0.05)], (1, 0, 0), 0.09, 0.09, 'wood_dark', tag='main', caps=True)
        M.bars(B, [(0.0, 0.01, h + 0.04)], [(L, 0.01, h + 0.04)], (0, 0, 1), 0.16, 0.05, 'wood_dark', tag='main', caps=True)

# ------------------------------------------------------------------ a gate (薬医門) at the top of 台所坂
def yakuimon(B, x, y, z, yaw, w=3.0, h=3.3, wall=None):
    with Frame(B, x, y, z, yaw):
        for (u, v, r) in ((-w / 2, 0.55, 0.17), (w / 2, 0.55, 0.17), (-w / 2, -0.95, 0.11), (w / 2, -0.95, 0.11)):
            prim.cyl(B, (u, v, 0.0), (u, v, h), r, r * 0.95, 10, 'wood_dark', tag='main')
            prim.cyl(B, (u, v, -0.1), (u, v, 0.16), r * 1.5, r * 1.4, 8, 'stone', tag='main')
        prim.obox(B, (-w / 2 - 0.4, 0.55, h - 0.1), (w / 2 + 0.4, 0.55, h - 0.1), 0.2, 0.32, 'wood_dark')
        prim.obox(B, (-w / 2 - 0.3, -0.95, h - 0.1), (w / 2 + 0.3, -0.95, h - 0.1), 0.14, 0.24, 'wood_dark')
        for u in (-w / 2, w / 2):
            prim.obox(B, (u, -1.4, h + 0.15), (u, 1.3, h + 0.15), 0.16, 0.24, 'wood_dark')
        # the door leaves standing open against the posts
        for sgn in (-1, 1):
            u0 = sgn * (w / 2 - 0.1)
            P = np.array([(u0, 0.5, 0.05), (u0, -0.9, 0.05), (u0, -0.9, h - 0.4), (u0, 0.5, h - 0.4)])
            I = [[0, 1, 2], [0, 2, 3]]
            B.add(P, I, 'wood_dark', tag='main'); B.add(P, [t[::-1] for t in I], 'wood_dark', tag='main')
        jroof.roof(B, w + 0.8, 2.4, h + 0.35, 0.9, kind='kirizuma', cover='hongawara', pitch=0.62, teri=1.4, sori=0.0, verge=0.75, rafter=0.3, rafter_mat='wood_dark', ends='oni',
                   ridge_h=0.55, ridge_w=0.34, edge=0.26, gable_wall='temple_wall', tiers=1)
        prim.polygon(B, [(-w / 2, -1.0), (w / 2, -1.0), (w / 2, 0.8), (-w / 2, 0.8)], 0.06, 'stone', tag='main')
        for u in (-w / 2, w / 2):
            prim.polygon(B, [(u - 0.25, -1.0), (u + 0.25, -1.0), (u + 0.25, 0.8), (u - 0.25, 0.8)], 0.1, 'stone', tag='block')

def daidokoro(B, S, lz, lanes):
    """台所坂: the stepped approach from ねねの道 east up to 高台寺 — low stone walls on both sides, lanterns, the gate"""
    if 'daidokoro' not in lanes: return
    lane = lanes['daidokoro']; L = lane.line
    w = 3.2
    for side in (1, -1):
        pts = []
        for s in np.arange(1.0, L.length - 1.0, 2.0):
            p, d, nrm = lane.frame(s)
            pts.append(p + nrm * side * (w / 2 + 0.25))
        for a, b in zip(pts[:-1], pts[1:]):
            za = lz(*a); zb = lz(*b)
            prim.obox(B, np.r_[a, za + 0.2], np.r_[b, zb + 0.2], 0.4, 0.8, 'stone', tag='main')
            prim.obox(B, np.r_[a, za + 0.4], np.r_[b, zb + 0.4], 0.45, 0.2, 'stone', tag='block')
    # stone lanterns every ~12 m
    for s in np.arange(6.0, L.length - 4.0, 12.0):
        p, d, nrm = lane.frame(s)
        for side in (1, -1):
            q = p + nrm * side * (w / 2 + 0.9)
            arch.ishidoro(B, q[0], q[1], float(S.ground(*q)), h=1.8)
            B.lamp(q[0], q[1], float(S.ground(*q)) + 1.2, 3.0) if side > 0 else None
    # the gate at the top
    p, d, nrm = lane.frame(L.length - 0.5)
    yakuimon(B, p[0] + d[0] * 1.5, p[1] + d[1] * 1.5, lz(*(p - d * 0.5)) + 0.05, math.atan2(d[1], d[0]) - math.pi / 2 + math.pi, w=3.0)
    # a short tiled wall either side of the gate
    for side in (1, -1):
        a = p + d * 1.5 + nrm * side * 2.0; b = p + d * 1.5 + nrm * side * 9.0
        HH.coping_wall(B, a, b, lz, h=2.4, base=0.6, tint=(232, 228, 216))

# ------------------------------------------------------------------ trees
def trees(B, S, lz, lanes, rng, blocked, blocked_fp):
    from shapely.geometry import Point as _P
    def free(q, r, street=False):
        g = _P(q).buffer(r)
        return not (blocked_fp if street else blocked).intersects(g)
    def at_lane(key, s, side, extra, sp, sc):
        """a tree beside the lane at station s, on open ground (gardens, gaps): searched along and away from the lane"""
        if key not in lanes: return
        lane = lanes[key]; s = s if s >= 0 else lane.line.length + s
        r = 0.9 if sp in ('yanagi', 'sakura', 'momiji') else 1.2
        for ds in (0.0, 2.0, -2.0, 4.0, -4.0, 6.0, -6.0, 9.0, -9.0):
            ss = min(max(s + ds, 0.5), lane.line.length - 0.5)
            p, d, nrm = lane.frame(ss)
            base = (np.interp(ss, lane.st, lane.left) if side > 0 else np.interp(ss, lane.st, lane.right))
            for ex in ((extra, extra + 1.5, extra + 3.0) if sp != 'yanagi' else (-0.9, -0.6, extra)):
                q = p + nrm * side * (base + ex)
                if free(q, r, street=(sp == 'yanagi')):
                    B.tree(sp, float(q[0]), float(q[1]), float(S.ground(*q)), sc, float(rng.uniform(0, 2 * math.pi)))
                    return
        print('tree skipped (no room)', key, s, sp)
    # 産寧坂: the weeping willow at the foot of the long flight (east side), maples above the steps
    at_lane('sannen', 37.0, -1, -0.2, 'yanagi', 1.15)
    at_lane('sannen', 14.0, 1, 1.5, 'momiji', 1.0)
    at_lane('sannen', 120.0, -1, 2.0, 'momiji', 0.9)
    # 二年坂: maples and a pine over the wall at the top of the steps, a willow by the lane
    at_lane('ninen', 136.0, 1, 2.5, 'momiji', 1.2)
    at_lane('ninen', 131.0, 1, 4.0, 'matsu', 1.1)
    at_lane('ninen', 140.0, -1, 2.5, 'momiji', 1.0)
    at_lane('ninen', 80.0, -1, 1.2, 'yanagi', 1.0)
    # 一念坂 / 八坂通: a few maples, cherries in gardens behind
    at_lane('ichinen', 30.0, 1, 1.8, 'momiji', 0.9)
    at_lane('ichinen', 70.0, -1, 1.8, 'sakura', 0.9)
    at_lane('yasaka_up', 70.0, 1, 2.0, 'momiji', 1.0)
    # the pagoda's plot: cherries and a pine (photos: bare cherries in front, a pine by the fence)
    for (x, y, sp, sc) in ((1857.5, 1404.5, 'sakura', 1.0), (1880.5, 1403.5, 'sakura', 1.1), (1878.0, 1427.0, 'momiji', 1.0), (1856.5, 1426.0, 'matsu', 0.9), (1886.5, 1420.0, 'momiji', 0.9)):
        if free((x, y), 0.6): B.tree(sp, x, y, float(S.ground(x, y)), sc, float(rng.uniform(0, 6.28)))
    # ねねの道: cherries and maples along the park side (east), a weeping cherry at the 台所坂 foot
    if 'nene' in lanes:
        lane = lanes['nene']
        for s in np.arange(18.0, lane.line.length - 10, 13.0):
            if 128 < s < 150: continue
            sp = 'sakura' if rng.random() < 0.45 else ('momiji' if rng.random() < 0.7 else 'kashi')
            at_lane('nene', s + rng.uniform(-2, 2), -1, rng.uniform(1.8, 4.0), sp, rng.uniform(0.9, 1.25))
    at_lane('daidokoro', 3.0, 1, 2.5, 'sakura', 1.3)
    at_lane('daidokoro', 30.0, -1, 2.5, 'momiji', 1.1)
    at_lane('daidokoro', 45.0, 1, 2.5, 'momiji', 1.1)
    # 石塀小路: small maples behind the walls
    for (k, s, side) in (('ishibe', 20.0, 1), ('ishibe', 60.0, -1), ('ishibe', 100.0, 1), ('ishibe_n', 30.0, 1), ('ishibe_w', 30.0, -1)):
        at_lane(k, s, side, 1.6, 'momiji', 0.7)

# ------------------------------------------------------------------ all
LAMP_LANES = dict(yasaka=24.0, yasaka_up=22.0, ninen=20.0, sannen=20.0, kiyomizu=22.0, ichinen=22.0, nene=24.0, ishibe=18.0, ishibe_n=20.0, ishibe_w=20.0,
                  chawan=24.0, gojo=24.0, ishin=26.0)

def build(B, S, lanes, lz, protect, stats):
    rng = np.random.default_rng(7)
    n = 0
    for k, sp in LAMP_LANES.items():
        if k not in lanes: continue
        lane = lanes[k]
        n += lamps_along(B, S, lane, lz, spacing=sp, start=6.0 + (hash_(k) % 7), skip=[(min(a, b), max(a, b)) for (a, b, tr) in lane.flights])
    stats['street_lamps'] = n
    stats['walls'] = osm_walls(B, S, lz, lanes, protect)
    daidokoro(B, S, lz, lanes)
    # open ground for trees: not on footprints (PLATEAU, the houses built here), not in the lanes
    fps = [Polygon(b['poly'][0][0]).buffer(0) for b in S.plateau]
    lanesg = [l.corridor(extra=0.3) for l in lanes.values()]
    blocked_fp = unary_union(fps)
    blocked = unary_union([blocked_fp] + lanesg)
    trees(B, S, lz, lanes, rng, blocked, blocked_fp)
    # the lane corridors join the exclusions: no generic poles, vending machines or trees on the hero lanes
    for k, lane in lanes.items():
        g = lane.corridor(extra=0.5)
        S.exclude.append(HL.ring_of(g))
    stats['trees'] = len(B.trees)

def hash_(s):
    import zlib
    return zlib.crc32(s.encode())
