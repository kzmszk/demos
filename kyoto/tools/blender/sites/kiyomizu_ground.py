"""清水寺: the precinct's ground — exclusion of the generic buildings, surface paint (stone paths, terraces, forest
slopes), the stone stairs and walls from OSM, fences, lanterns, plain versions of the secondary buildings, and the
trees (maples in the 錦雲渓 valley under the stage, cedars / oaks on the upper slopes)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from jk import prim, arch, Frame
from sites import kiyomizu_lib as K
from sites import kiyomizu_halls as HALLS

# OSM buildings modelled by hand (their footprints keep generic / plain buildings and trees away)
HERO_IDS = [102164608, 102164575, 102164638, 102164614, 102164570, 102164586, 102164632, 102164640, 102164595, 102164617, 102164590, 340294693,
            102164574, 102164636, 102164641, 893859575, 333894528, 102164588, 102164583, 102164635, 337096697, 102164597, 337096699, 1450387649]

# steps modelled from OSM: id -> width (others in the precinct get 2.4 m); None = skip (modelled elsewhere)
STEP_W = {179958180: 5.0, 191038772: 4.0, 339358818: None, 191041222: 2.6, 339178065: 3.2, 191041217: 2.4, 191041219: 2.4, 339551496: 3.0, 191039563: 2.4,
          340393745: 2.0, 1272415028: 2.0, 1272415076: 2.0, 191039228: None, 340294694: None}

# open plazas / terraces kept free of trees (world xy rings)
CLEAR = [[(2200, 1060), (2232, 1048), (2246, 1064), (2236, 1090), (2205, 1092)],          # 仁王門 forecourt and stairs
         [(2246, 1052), (2262, 1036), (2300, 1004), (2342, 990), (2350, 1002), (2300, 1022), (2270, 1060)],   # 西門 - 三重塔 - 轟門 terraces
         [(2400, 1004), (2426, 1004), (2442, 1016), (2420, 1024), (2402, 1020)],          # 本堂 east plaza
         [(2404, 944), (2422, 944), (2424, 968), (2404, 970)],                            # 音羽の滝
         [(2386, 932), (2404, 930), (2410, 944), (2404, 962), (2392, 966), (2384, 950)]]  # the court below the stage (tea houses, view up)

def precinct(S):
    return Polygon(S.polygon[0][0])

def hero_union(S, extra=()):
    gs = []
    for i in HERO_IDS:
        b = S.osm_building(i)
        if b: gs.append(Polygon(b['poly'][0][0]))
    return unary_union(gs + list(extra))

def build(B, S, info):
    prec = precinct(S)
    ring = [list(map(float, p)) for p in S.polygon[0][0]]
    S.exclude.append(ring)
    paths = path_geom(S, prec)
    info['paths'] = paths
    stairs(B, S, prec)
    walls(B, S, prec)
    lanterns(B, S, info)
    others(B, S, prec, info)
    paint(S, prec, paths, info)

# ------------------------------------------------------------------ paths
def path_geom(S, prec):
    gs = []
    for w in S.osm['ways']:
        hw = w['tags'].get('highway')
        if hw not in ('footway', 'path', 'steps', 'pedestrian', 'service'): continue
        for l in w['line']:
            L = LineString(l)
            if not L.intersects(prec): continue
            wd = {'pedestrian': 5.0, 'service': 3.5, 'steps': 2.6}.get(hw, 2.4)
            gs.append(L.buffer(wd / 2, cap_style='round'))
    return unary_union(gs).intersection(prec.buffer(2))

# ------------------------------------------------------------------ stairs
def stairs(B, S, prec):
    for w in S.osm['ways']:
        if w['tags'].get('highway') != 'steps': continue
        if w['id'] in STEP_W and STEP_W[w['id']] is None: continue
        for l in w['line']:
            L = LineString(l)
            if not L.intersects(prec.buffer(2)): continue
            a = np.array(l, float)
            z = np.array([float(S.ground(*p)) for p in a])
            if abs(z[-1] - z[0]) < 0.3: continue
            wd = STEP_W.get(w['id'], 2.4)
            for i in range(len(a) - 1):
                p0, p1 = a[i], a[i + 1]
                z0, z1 = z[i] + 0.05, z[i + 1] + 0.05
                if np.linalg.norm(p1 - p0) < 0.8: continue
                if z1 < z0: p0, p1, z0, z1 = p1, p0, z1, z0
                if z1 - z0 < 0.12:
                    continue
                K.steps(B, p0, p1, z0, z1, wd, 'stone', riser=0.18, S=S, cheek=0.3 if wd >= 3 else None)
                if w['tags'].get('handrail') == 'yes' or wd < 3:
                    d = K.unit(p1 - p0); n = K.perp(d)
                    for sgn in (-1, 1):
                        q = [np.r_[p0 + n * sgn * (wd / 2 - 0.15), z0], np.r_[p1 + n * sgn * (wd / 2 - 0.15), z1]]
                        K.handrail(B, q)

# ------------------------------------------------------------------ walls, fences, hedges
def walls(B, S, prec):
    for b in S.osm['barriers']:
        kind = b['tags'].get('barrier')
        for l in b['line']:
            L = LineString(l)
            if not L.intersects(prec.buffer(1)): continue
            pts = [np.array(p, float) for p in l]
            if kind in ('wall', 'retaining_wall'):
                # a retaining wall where the ground differs across it, else a low stone wall
                for a, c in zip(pts[:-1], pts[1:]):
                    d = K.unit(c - a); n = -K.perp(d)
                    m = (a + c) / 2
                    zl = float(S.ground(*(m + n * 1.5))); zr = float(S.ground(*(m - n * 1.5)))
                    if abs(zl - zr) > 0.8:
                        if zl > zr: seg = [a, c]; side = 1
                        else: seg = [c, a]; side = -1
                        ishigaki_seg(B, S, seg)
                    else:
                        ga = float(S.ground(*a)); gc = float(S.ground(*c))
                        prim.obox(B, np.r_[a, ga + 0.6], np.r_[c, gc + 0.6], 0.5, 1.6, 'stone')
                K.block_line(B, pts)
            elif kind == 'fence':
                ft = b['tags'].get('fence_type', '')
                if ft == 'split_rail':
                    arch.takegaki(B, pts, 0, h=1.0, kind='yotsume', ground=lambda x, y: float(S.ground(x, y)))
                else:
                    K.fence_black(B, pts, S=S, h=1.15)
                K.block_line(B, pts)
            elif kind == 'hedge':
                arch.hedge(B, pts, 0, h=1.1, w=0.8, ground=lambda x, y: float(S.ground(x, y)))
                K.block_line(B, pts, w=0.8)

def ishigaki_seg(B, S, seg):
    """a 石垣 along seg (the high ground on its left): top = high-side ground, bottom = low-side ground"""
    a, c = seg
    d = K.unit(c - a); n = -K.perp(d)            # outward = low side
    K.ishigaki(B, [a, c], lambda x, y: float(S.ground(x - n[0] * 1.2, y - n[1] * 1.2)) + 0.15,
               lambda x, y: float(S.ground(x + n[0] * 1.5, y + n[1] * 1.5)), batter=0.2)

# ------------------------------------------------------------------ lanterns along the main route
def lanterns(B, S, info):
    route = [((2252.0, 1052.5), (2270.0, 1045.0)),       # Niomon terrace -> Saimon stair
             ((2296.0, 1012.0), (2338.0, 995.0)),         # pagoda -> 轟門
             ((2414.0, 1019.0), (2414.5, 1025.0)),        # 地主神社 stair foot
             ((2440.0, 1012.0), (2440.0, 989.0))]         # 釈迦堂 -> 阿弥陀堂
    for (a, c) in route:
        a = np.array(a); c = np.array(c); L = np.linalg.norm(c - a); d = K.unit(c - a); n = K.perp(d)
        for t in np.arange(2.0, L, 8.0):
            for s in (-1, 1):
                p = a + d * t + n * s * 2.6
                zg = float(S.ground(*p))
                arch.ishidoro(B, p[0], p[1], zg, h=2.1)
                B.lamp(p[0], p[1], zg + 1.35, 4.0)
                K.block_line(B, [p - d * 0.3, p + d * 0.3], w=0.7)

# ------------------------------------------------------------------ the precinct's other buildings (plain)
def others(B, S, prec, info):
    hero = hero_union(S).buffer(1.5)
    done = 0
    for p in S.plateau:
        poly = Polygon(p['poly'][0][0])
        if poly.area < 8 or not prec.contains(poly.representative_point()): continue
        if poly.intersection(hero).area > 0.25 * poly.area: continue
        if poly.intersects(Polygon(CLEAR[3])): continue
        cx, cy, L, W, yaw = S.rect(p['poly'][0])
        zg = float(min(S.ground(*q) for q in poly.exterior.coords))
        top = p['z0'] + p['h'] if p['h'] else zg + 6.0
        htot = max(3.0, min(16.0, top - zg))
        if poly.area < 25:            # small shrines, sheds
            H = min(2.4, htot * 0.6); kind = 'kirizuma'
        else:
            H = max(2.6, min(7.5, htot * 0.55)); kind = 'irimoya' if L / max(W, 1) < 2.2 else 'kirizuma'
        with Frame(B, cx, cy, 0.0, yaw):
            HALLS.plain(B, L - 1.0, W - 1.0, zg, H, kind, 'kawara', pitch=min(0.75, max(0.35, (htot - H) / max(1.0, W / 2))), o=0.9)
        done += 1
    info['plain_buildings'] = done

# ------------------------------------------------------------------ ground paint
def paint(S, prec, paths, info):
    """forest floor on the slopes, stone slabs on the main paths and terraces"""
    x0, y0, x1, y1 = prec.bounds
    res = 3.0
    xs = np.arange(x0, x1, res); ys = np.arange(y0, y1, res)
    X, Y = np.meshgrid(xs + res / 2, ys + res / 2)
    Z = S.ground(X, Y)
    gy, gx = np.gradient(Z, res)
    slope = np.hypot(gx, gy)
    ins = shapely.contains_xy(prec, X, Y)
    hero = hero_union(S).buffer(3.0)
    keep = ins & (slope > 0.42)
    cells = [box(x - res / 2, y - res / 2, x + res / 2, y + res / 2) for x, y in zip(X[keep], Y[keep])]
    forest = unary_union(cells).buffer(0.8).buffer(-0.8).difference(paths.buffer(0.5)).difference(hero).intersection(prec)
    for g in (forest.geoms if hasattr(forest, 'geoms') else [forest]):
        if g.geom_type == 'Polygon' and g.area > 20:
            g = g.simplify(0.6)
            S.paint.append({'poly': [list(map(float, c)) for c in g.exterior.coords], 'surf': 'forest'})
    info['forest'] = forest
    # main stone-paved routes (石畳): the approach from the 仁王門 to the 轟門, the 本堂 east side, to the 奥の院
    main = [[(2228.0, 1073.0), (2240.0, 1068.0), (2252.0, 1062.0), (2262.0, 1050.0), (2272.0, 1046.0)],
            [(2272.0, 1034.0), (2290.0, 1016.0), (2318.0, 1008.5), (2338.0, 999.0), (2347.0, 996.0)],
            [(2408.5, 1006.5), (2440.0, 1002.0)], [(2440.4, 1001.9), (2441.5, 985.0)]]
    for l in main:
        g = LineString(l).buffer(2.2, cap_style='round', join_style='round').intersection(prec)
        for gg in (g.geoms if hasattr(g, 'geoms') else [g]):
            if gg.geom_type == 'Polygon':
                S.paint.append({'poly': [list(map(float, c)) for c in gg.simplify(0.3).exterior.coords], 'surf': 'stone_slab'})

# ------------------------------------------------------------------ trees
def trees(B, S, info):
    rng = np.random.default_rng(11)
    prec = precinct(S)
    paths = info.get('paths') or path_geom(S, prec)
    stairs_ = [LineString(l).buffer(4.5) for w in S.osm['ways'] if w['tags'].get('highway') == 'steps' for l in w['line']]
    clear = [Polygon(r) for r in CLEAR]
    blocked = unary_union([hero_union(S).buffer(2.5), paths.buffer(1.2)] + stairs_ + clear +
                          [Polygon(p['poly'][0][0]).buffer(1.5) for p in S.plateau if prec.contains(Polygon(p['poly'][0][0]).representative_point())])
    # the 懸造 frame and the stage: keep the trees off the posts (the maples stand in front, below)
    if 'hondo_frame' in info:
        fr = info['hondo_frame']
        blocked = unary_union([blocked, Polygon(K.to_world(fr, [(-20, -24.0), (20, -24.0), (20, 18), (-20, 18)]))])
    if 'okunoin' in info:
        fr = info['okunoin']
        blocked = unary_union([blocked, Polygon(K.to_world(fr, [(-11, -15.5), (11, -15.5), (11, 10), (-11, 10)]))])
    shapely.prepare(blocked)
    x0, y0, x1, y1 = prec.bounds
    # Poisson-ish sampling on a jittered grid
    sp = 4.6
    xs = np.arange(x0, x1, sp); ys = np.arange(y0, y1, sp)
    X, Y = np.meshgrid(xs, ys)
    P = np.stack([X.ravel(), Y.ravel()], 1) + rng.uniform(-sp * 0.42, sp * 0.42, (X.size, 2))
    P = P[shapely.contains_xy(prec.buffer(-1.0), P[:, 0], P[:, 1])]
    P = P[~shapely.contains_xy(blocked, P[:, 0], P[:, 1])]
    Z = S.ground(P[:, 0], P[:, 1])
    gy, gx = np.gradient(S.H, S.res)
    ix = np.clip(((P[:, 0] - S.x0) / S.res).astype(int), 0, S.H.shape[1] - 1); iy = np.clip(((P[:, 1] - S.y0) / S.res).astype(int), 0, S.H.shape[0] - 1)
    slope = np.hypot(gx[iy, ix], gy[iy, ix])
    hf = info.get('hondo_frame'); of = info.get('okunoin')
    # the view from the 奥の院 stage to the 本堂 stage: a fan in which only maples grow, their crowns kept below the line
    # of sight; close to the 奥の院 stage nothing rises above its deck
    fan = near_oku = None
    if hf and of:
        a = K.to_world(of, [(-9.0, -13.0), (9.0, -13.0)]); c = K.to_world(hf, [(-12.0, -24.0), (12.0, -24.0)])
        fan = Polygon([a[0], a[1], c[1], c[0]]).convex_hull.buffer(3.0)
        near_oku = Polygon(K.to_world(of, [(-12, -24), (12, -24), (12, -7), (-12, -7)]))
    pathd = paths.buffer(5.0); shapely.prepare(pathd)
    for (x, y), z, sl in zip(P, Z, slope):
        u = rng.uniform()
        pt = Point(x, y)
        # zones: the 錦雲渓 valley and the slopes south of the halls -> maples; the hill east of the 奥の院 and the north
        # -> cedars, cypress and evergreen oaks; flat terraces -> few trees, away from the paths (pines, maples, cherries)
        valley = y < 1000 and x < 2440 and z < 116
        east = x > 2458 or y > 1085 or (y < 905 and x > 2405)
        flat = sl < 0.3
        if flat and (u < 0.7 or pathd.contains(pt)): continue
        zmax = 1e9
        if fan is not None and fan.contains(pt): zmax = 113.8
        if near_oku is not None and near_oku.contains(pt): zmax = min(zmax, 114.5)
        if zmax < 1e8:
            sp_ = 'momiji' if u < 0.9 else 'sakura'
            sc = rng.uniform(1.0, 1.45)
            if z + 7.0 * sc > zmax:
                if zmax - z < 4.0: continue
                sc = (zmax - z) / 7.0
        elif valley:
            sp_ = 'momiji' if u < 0.8 else ('kashi' if u < 0.9 else ('sakura' if u < 0.96 else 'keyaki'))
            sc = rng.uniform(1.15, 1.7) if sp_ == 'momiji' else rng.uniform(0.9, 1.2)
        elif east:
            sp_ = 'sugi' if u < 0.3 else ('hinoki' if u < 0.45 else ('kashi' if u < 0.8 else 'momiji'))
            sc = rng.uniform(0.85, 1.2)
        elif flat:
            sp_ = 'matsu' if u < 0.8 else ('momiji' if u < 0.93 else 'sakura')
            sc = rng.uniform(0.9, 1.2)
        else:
            sp_ = 'momiji' if u < 0.55 else ('kashi' if u < 0.8 else ('sakura' if u < 0.87 else ('sugi' if u < 0.93 else 'keyaki')))
            sc = rng.uniform(1.0, 1.5) if sp_ == 'momiji' else rng.uniform(0.85, 1.15)
        B.tree(sp_, float(x), float(y), float(z), float(sc), float(rng.uniform(0, 2 * math.pi)))
    # OSM trees in the precinct (地主の桜 etc.)
    for t in S.osm['trees']:
        if not prec.contains(Point(t['xy'])): continue
        tg = ' '.join(str(v) for v in t['tags'].values())
        sp_ = 'sakura' if ('桜' in tg or 'prunus' in tg.lower() or 'cherry' in tg.lower()) else ('matsu' if ('松' in tg or 'pinus' in tg.lower()) else 'momiji')
        x, y = t['xy']
        if paths.buffer(1.0).contains(Point(x, y)) or blocked.contains(Point(x, y)): continue
        B.tree(sp_, float(x), float(y), float(S.ground(x, y)), 1.0, float(rng.uniform(0, 2 * math.pi)))
