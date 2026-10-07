"""曹源池庭園 (夢窓疎石, 特別名勝): the pond seen from the 大方丈's west veranda.

Our own ground over the pond and its banks (the 5 m DEM has the pond area ~1.5 m too high): the white sand strip in
front of the veranda, a lawn and a pebble beach (洲浜) on the near shore with the 出島 peninsula, the water (WL 42.45),
the far shore rising steeply into 亀山 with stone groups: 龍門の滝 (the dry waterfall, 鯉魚石 at (-7813.9, 3314.4)
per OSM) and the three-slab stone bridge before it, the 岩島 standing in the water, shore stones all round, clipped
shrubs, pines and maples; the garden path round the pond and up to 望京の丘; stone lanterns.  嵐山 and 亀山 stand
behind as borrowed scenery (generic terrain)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from jk import prim, arch
from . import tenryuji_kit as K
from .tenryuji_kit import ribbon, quad, WD

WL = 42.45
G0 = 42.95             # the near (hojo) bank
HOJO_X = -7775.6        # west edge of the hojo's 落縁

def pond_shapes(S):
    f = [w for w in S.osm['water'] if w['id'] == -3962914][0]
    R = K.rings(f['poly'])
    outer = Polygon(K.chaikin(R[0], 2)).buffer(0)
    isl = [Polygon(K.chaikin(r, 2)).buffer(0.1) for r in R[1:] if Polygon(r).area > 5]
    return outer, isl

def build(B, S):
    out = {}
    rng = np.random.default_rng(77)
    outer, islands = pond_shapes(S)
    pond = outer.difference(unary_union(islands)) if islands else outer
    garden = None
    for fl in S.osm['landuse']:
        if fl['id'] == 430449660: garden = K.osm_poly(fl)
    hojo_rect = box(HOJO_X, 3290.0, -7745.0, 3337.0)
    region = unary_union([outer.buffer(13.0), box(-7792.0, 3282.0, HOJO_X + 0.4, 3338.0)]).intersection(garden.buffer(2.0).union(box(-7800, 3280, HOJO_X + 0.4, 3340)))
    region = region.difference(box(HOJO_X + 0.4, 3200, -7700, 3400)).buffer(-0.5).buffer(0.5).simplify(0.3)
    if hasattr(region, 'geoms'): region = max(region.geoms, key=lambda g: g.area)
    shapely.prepare(region); shapely.prepare(outer)
    # distance fields on a grid (fast lookups)
    x0, y0, x1, y1 = region.bounds
    res = 0.5
    xs = np.arange(x0 - 1, x1 + 1, res); ys = np.arange(y0 - 1, y1 + 1, res)
    X, Y = np.meshgrid(xs, ys)
    pts = shapely.points(X.ravel(), Y.ravel())
    d_shore = shapely.distance(outer.exterior, pts).reshape(X.shape)
    inside = shapely.contains_xy(outer, X, Y)
    isl_u = unary_union(islands) if islands else None
    in_isl = shapely.contains_xy(isl_u, X, Y) if isl_u is not None else np.zeros_like(inside)
    d_isl = shapely.distance(isl_u.boundary, pts).reshape(X.shape) if isl_u is not None else np.full(X.shape, 99.0)
    frame = region.union(hojo_rect.buffer(3.0))
    d_edge = shapely.distance(frame.exterior, pts).reshape(X.shape)
    D = S.ground(X, Y)
    east = X > -7792.0                                  # the near bank between the hojo and the water
    # model height
    Hm = np.where(east, G0 - np.clip((-7781.0 - X) / 9.0, 0, 1) * 0.05, D)
    shore_far = WL + 0.3 + (D - WL - 0.3) * np.clip(d_shore / 7.0, 0, 1) ** 0.8
    Hm = np.where(~east & ~inside, np.maximum(shore_far, WL + 0.3), Hm)
    # the near shore: a pebble beach (洲浜) sloping into the water over ~2.5 m
    beach = east & ~inside & (d_shore < 2.8)
    Hm = np.where(beach, WL + 0.06 + (G0 - WL - 0.06) * np.clip(d_shore / 2.8, 0, 1) ** 1.2, Hm)
    basin = WL - 0.25 - 0.55 * np.clip(d_shore / 3.0, 0, 1)
    Hm = np.where(inside & ~in_isl, basin, Hm)
    Hm = np.where(in_isl, WL + 0.2 + 0.6 * np.clip(d_isl / 1.5, 0, 1) ** 0.7, Hm)
    # blend to the DEM along the outer edges of the region (not on the hojo side)
    w = np.clip(d_edge / 4.0, 0, 1); w = w * w * (3 - 2 * w)
    Hm = np.where(inside, Hm, D * (1 - w) + Hm * w)
    def hf(x, y):
        fx = (x - xs[0]) / res; fy = (y - ys[0]) / res
        i = int(np.clip(math.floor(fx), 0, len(xs) - 2)); j = int(np.clip(math.floor(fy), 0, len(ys) - 2))
        ax = min(max(fx - i, 0), 1); ay = min(max(fy - j, 0), 1)
        return float(Hm[j, i] * (1 - ax) * (1 - ay) + Hm[j, i + 1] * ax * (1 - ay) + Hm[j + 1, i] * (1 - ax) * ay + Hm[j + 1, i + 1] * ax * ay)
    out['hf'] = hf
    # surfaces: water bed, white sand strip, lawn, pebble beach, paths (gravel), moss
    paths = []
    for wy in S.osm['ways']:
        if wy['tags'].get('highway') in ('footway', 'path', 'steps'):
            for ln in wy['line']:
                if len(ln) > 1: paths.append(LineString(ln).buffer(1.1))
    paths = unary_union(paths).intersection(region) if paths else Polygon()
    shapely.prepare(paths)
    sand = box(-7786.5, 3284.0, HOJO_X + 0.4, 3334.0).difference(outer.buffer(4.2))
    lawn = box(-7792.0, 3282.0, -7783.0, 3338.0).difference(outer.buffer(1.8)).difference(sand)
    shapely.prepare(sand); shapely.prepare(lawn)
    SID = K.SID
    def surf(x, y):
        p = Point(x, y)
        if outer.contains(p) and not (isl_u is not None and isl_u.contains(p)): return SID['riverbed']
        if sand.contains(p): return SID['sand']
        if x > -7792 and outer.exterior.distance(p) < 2.8: return SID['riverbed']
        if paths.contains(p): return SID['gravel']
        if lawn.contains(p): return SID['grass']
        return SID['moss']
    inner = outer.buffer(-0.35); shapely.prepare(inner)
    def walk(x, y):
        p = Point(x, y)
        return not inner.contains(p) or (isl_u is not None and isl_u.contains(p))
    K.mesh_region(B, region, hf, 0.6, surf_of=surf, walk_of=walk)
    S.cut.append([list(map(list, region.exterior.coords))])
    # the water, and the pond edge blocked
    K.water(B, pond, WL)
    K.block_poly(B, pond.buffer(-0.15))
    # ---- 龍門の滝: the dry waterfall on the far shore, centre (鯉魚石) at (-7813.9, 3314.4)
    rx, ry = -7814.6, 3314.4
    zb = hf(rx, ry)
    fall = [  # (dx, dy, half-width, height/size, seed, mat) — two tall flanking stones, the 'mirror' stone behind, steps of stones
        (-1.4, -1.1, 0.55, 4.2, 1), (-1.4, 1.2, 0.6, 3.6, 2), (-2.6, 0.0, 0.85, 3.0, 3), (-0.6, -1.9, 0.5, 2.2, 4), (-0.7, 2.1, 0.55, 2.0, 5),
        (-3.6, -1.4, 0.7, 2.4, 6), (-3.5, 1.6, 0.75, 2.1, 7), (-4.6, 0.2, 0.9, 1.6, 8)]
    for (dx, dy, s, t, sd) in fall:
        x, y = rx + dx, ry + dy
        K.rock(B, (x, y, hf(x, y) - 0.1), s, 900 + sd, tall=t, angular=0.7, sink=0.12, lean=rng.uniform(-0.05, 0.05))
    # 鯉魚石: the carp stone at the foot of the fall, tilted as if leaping
    K.rock(B, (rx + 0.2, ry + 0.1, WL + 0.1), 0.42, 950, tall=2.4, angular=0.6, sink=0.1, lean=0.18)
    # the stone bridge (three long slabs) across the cove in front of the fall
    for k, (dy, L) in enumerate(((-0.5, 2.4), (0.0, 2.6), (0.5, 2.3))):
        xa = rx + 1.1; x_b = rx + 1.1
        a = (rx + 1.0, ry - 1.3 + dy * 0.2); b = (rx + 1.25, ry + 1.3 + dy * 0.2)
        cx = rx + 1.0 + k * 0.42; zt = WL + 0.38 + 0.03 * k
        prim.box(B, cx - 0.2, ry - L / 2, zt - 0.22, cx + 0.2, ry + L / 2, zt, 'stone', faces='zZxXyY')
    for sg in (-1, 1):
        K.rock(B, (rx + 1.4, ry + sg * 1.6, WL + 0.1), 0.45, 960 + sg, flat=0.7, angular=0.4)
    # 岩島: vertical pointed stones standing in the water (to the south-east of the fall) and a low flat cluster in the middle
    for k, (x, y, s, t) in enumerate(((-7806.5, 3302.5, 0.42, 3.4), (-7805.8, 3301.6, 0.3, 2.4), (-7807.3, 3301.9, 0.28, 2.1), (-7805.4, 3303.2, 0.25, 1.6),
                                     (-7806.9, 3303.4, 0.22, 1.3))):
        K.rock(B, (x, y, WL - 0.25), s, 1000 + k, tall=t, angular=0.7, sink=0.05)
    for k in range(9):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0.0, 2.2)
        x, y = -7798.5 + r * math.cos(a) * 1.4, 3310.5 + r * math.sin(a) * 0.6
        K.rock(B, (x, y, WL - 0.12), rng.uniform(0.35, 0.7), 1100 + k, flat=rng.uniform(0.45, 0.8), angular=0.5)
    K.rock(B, (-7801.6, 3318.6, WL - 0.15), 0.42, 1150, tall=1.6, angular=0.6)
    K.rock(B, (-7794.8, 3296.6, WL - 0.15), 0.38, 1151, tall=1.3, angular=0.6)
    # stone groups climbing the far bank (the 'mountain' behind the fall) and on the 出島
    for k in range(70):
        a = rng.uniform(0, 1)
        t = rng.uniform(0, outer.exterior.length)
        p = np.array(outer.exterior.interpolate(t).coords[0])
        if p[0] > -7795: continue
        n = np.array(outer.exterior.interpolate(t + 0.5).coords[0]) - p
        nn = np.array([n[1], -n[0]]); nn /= max(np.linalg.norm(nn), 1e-6)
        if outer.contains(Point(*(p + nn * 0.5))): nn = -nn
        q = p + nn * rng.uniform(1.0, 7.5)
        s = rng.uniform(0.3, 0.85)
        K.rock(B, (q[0], q[1], hf(*q) - 0.05), s, 1200 + k, flat=rng.uniform(0.5, 1.1), angular=0.5, tag='main' if s > 0.5 else 'detail')
    # shore stones (護岸石組) along the far and side shores; the near shore is the pebble beach
    L = outer.exterior
    t = 0.0; n = 0
    while t < L.length:
        p = np.array(L.interpolate(t).coords[0])
        if p[0] < -7789.0 or p[1] < 3289.0 or p[1] > 3334.0:
            size = rng.uniform(0.6, 0.95) if rng.random() < 0.12 else rng.uniform(0.28, 0.55)
            q2 = np.array(L.interpolate(min(L.length, t + 0.3)).coords[0])
            d = q2 - p; d /= max(np.linalg.norm(d), 1e-6); nn = np.array([-d[1], d[0]])
            q = p + nn * rng.uniform(-0.25, 0.25)
            K.rock(B, (q[0], q[1], WL + rng.uniform(-0.05, 0.12)), size, 1400 + n, flat=rng.uniform(0.5, 0.85), angular=0.4, tag='main' if size > 0.5 else 'detail')
            n += 1
            t += size * rng.uniform(1.1, 1.6)
        else:
            t += 0.8
    for isl in islands:
        c = isl.centroid
        for k in range(5):
            q = (c.x + rng.uniform(-1.6, 1.6), c.y + rng.uniform(-1.6, 1.6))
            if isl.contains(Point(q)): K.rock(B, (q[0], q[1], hf(*q)), rng.uniform(0.35, 0.7), 1700 + k, flat=0.7, angular=0.4)
    # clipped shrubs (刈込) on the near bank and round the peninsula, a few stones in the lawn
    for k in range(26):
        x = rng.uniform(-7791.5, -7783.5); y = rng.uniform(3285, 3336)
        p = Point(x, y)
        if outer.buffer(1.2).contains(p) or sand.contains(p): continue
        r = rng.uniform(0.6, 1.3)
        z = hf(x, y)
        prim.lathe(B, (x, y, z - 0.1), [(r, 0.0), (r * 1.02, r * 0.35), (r * 0.8, r * 0.75), (r * 0.35, r * 0.95), (0.0, r * 1.0)], 10, 'hedge')
        if rng.random() < 0.4: K.rock(B, (x + r * 0.9, y + rng.uniform(-0.5, 0.5), z), rng.uniform(0.3, 0.55), 1800 + k, flat=0.75, angular=0.4)
    # the low fence (posts + rope) along the sand strip, and the bamboo edging by the veranda
    fx = -7784.2
    for y in np.arange(3286.0, 3334.0, 2.4):
        z = hf(fx, y)
        prim.cyl(B, (fx, y, z - 0.1), (fx, y, z + 0.55), 0.04, 0.04, 6, WD, tag='detail')
    rope = np.array([(fx, y, hf(fx, y) + 0.45 - 0.06 * math.sin(((y - 3286.0) / 2.4 % 1) * math.pi)) for y in np.arange(3286.0, 3333.6, 0.4)])
    prim.sweep(B, rope, [(0.012 * math.cos(a), 0.012 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 5)[:-1]], 'cloth', tag='detail', c0=(90, 70, 50, 0))
    # stone lanterns at the path and the 洲浜
    for (x, y, h, kind) in ((-7790.5, 3285.5, 1.8, 'kasuga'), (-7784.5, 3338.5, 1.3, 'yukimi'), (-7825.5, 3337.0, 1.9, 'kasuga'), (-7797.6, 3373.5, 1.9, 'kasuga'),
                            (-7800.2, 3373.9, 1.9, 'kasuga'), (-7836.3, 3369.9, 2.0, 'kasuga')):
        K.lantern(B, x, y, (hf(x, y) if region.contains(Point(x, y)) else float(S.ground(x, y))), h=h, kind=kind)
    # 望京の丘 (-7884, 3377): a small level viewing spot with a bench
    vx, vy = -7884.0, 3377.0
    zv = float(S.ground(vx, vy))
    prim.box(B, vx - 0.9, vy - 0.25, zv - 0.2, vx + 0.9, vy + 0.25, zv + 0.42, 'stone')
    # planting: big pines at the ends of the near bank, maples and pines on the far bank, the hill beyond
    for (x, y, sc) in ((-7787.5, 3282.5, 1.5), (-7790.5, 3338.5, 1.35), (-7785.6, 3323.6, 1.1), (-7791.6, 3318.2, 0.95)):
        B.tree('matsu', x, y, hf(x, y) - 0.1, sc, rng.uniform(0, 6.28))
    far = region.difference(outer.buffer(1.5)).difference(box(-7795.0, 3270, -7700, 3400)).difference(paths.buffer(0.8))
    pts = K.poisson(far.difference(outer.buffer(3.0)), 5.2, rng, 400)
    near_rf = Point(rx, ry).buffer(4.5)
    for (x, y) in pts:
        if near_rf.contains(Point(x, y)): continue
        u = rng.random()
        sp = 'momiji' if u < 0.55 else 'matsu' if u < 0.78 else 'kashi' if u < 0.9 else 'sakura'
        sc = rng.uniform(0.85, 1.3)
        if K.blocks_view(sp, x, y, hf(x, y), sc, near=22.0): continue
        B.tree(sp, float(x), float(y), hf(x, y) - 0.1, sc, rng.uniform(0, 6.28))
    # trees right behind the fall (photo: pines and evergreens overhanging the stones)
    for (dx, dy, sp) in ((-6.0, -2.5, 'matsu'), (-6.5, 3.0, 'kashi'), (-8.5, 0.0, 'momiji'), (-5.0, 5.5, 'momiji'), (-5.5, -6.0, 'momiji')):
        x, y = rx + dx, ry + dy
        B.tree(sp, x, y, hf(x, y) - 0.1, 1.15, rng.uniform(0, 6.28))
    # clipped azaleas (the viewer's tsutsuji mounds) on both banks and among the far stones
    pz = region.difference(outer.buffer(0.6)).difference(sand).difference(paths.buffer(0.4))
    for (x, y) in K.poisson(pz, 2.6, rng, 160):
        p = Point(x, y)
        if x > -7792 and not outer.buffer(3.5).contains(p): continue
        if Point(rx, ry).buffer(2.5).contains(p): continue
        sc = rng.uniform(0.7, 1.05) if x > -7792 else rng.uniform(0.9, 1.5)
        if K.blocks_view('tsutsuji', x, y, hf(x, y), sc, near=9.0): continue
        B.tree('tsutsuji', float(x), float(y), hf(x, y) - 0.05, sc, rng.uniform(0, 6.28))
    # the 洲浜: flat pebbles strewn along the beach and into the shallows
    for k in range(260):
        t = rng.uniform(0, outer.exterior.length)
        p0 = np.array(outer.exterior.interpolate(t).coords[0])
        if p0[0] < -7792.0: continue
        q2 = np.array(outer.exterior.interpolate(t + 0.4).coords[0])
        dd = (q2 - p0) / max(np.linalg.norm(q2 - p0), 1e-6)
        nn = np.array([-dd[1], dd[0]])
        if outer.contains(Point(*(p0 + nn * 0.3))): nn = -nn
        q = p0 + nn * rng.uniform(-1.2, 2.4)
        sz = rng.uniform(0.07, 0.17)
        K.rock(B, (q[0], q[1], hf(*q) + 0.01), sz, 3000 + k, flat=0.45, tag='detail')
    out['region'] = region
    out['planted'] = region
    out['zones'] = []
    out['no_trees'] = [region]
    return out
