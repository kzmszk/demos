"""嵐山 banks: the north-bank promenade (lamps, the parapet and fence along the drop to the river, cherries and maples,
the big 榎 at the bridge's north end, the 史蹟 stones), 中之島 (the plaza, lawns behind low 四つ目垣, paths, the clock
post, benches, lanterns, pines and cherries), the trees along the banks."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box as sbox
from jk import prim, arch, Frame
import sites.machiya as M
import sites.arashiyama_util as U

def way(S, wid):
    for w in S.osm['ways']:
        if w['id'] == wid: return LineString(w['line'][0])
    raise KeyError(wid)

def lu_poly(S, fid):
    for f in S.osm['landuse']:
        if f['id'] == fid: return Polygon(f['poly'][0][0]).buffer(0)
    raise KeyError(fid)

def island(river):
    P = river.ch['main'].union(river.ch['south']).buffer(0.05).buffer(-0.05)
    return max([Polygon(r) for r in P.interiors], key=lambda q: q.area)

def build(B, S, river, bridges, forbid):
    rng = np.random.default_rng(31)
    isl = island(river)
    keep_out = shapely.unary_union([b.footprint(1.0) for b in bridges] + [river.ch['main'].union(river.ch['south']).buffer(1.8), river.ch['intake'].buffer(0.9)])
    if forbid is not None: keep_out = keep_out.union(forbid.buffer(1.0))
    fps = []
    for b in S.plateau:
        P = Polygon(b['poly'][0][0]).buffer(0)
        if P.is_valid and P.area > 4 and P.distance(river.all) < 80: fps.append(P.buffer(1.3))
    keep_out = keep_out.union(shapely.unary_union(fps))
    shapely.prepare(keep_out)
    trees = []
    def tree(sp, x, y, sc, yaw=None, dz=0.0):
        if keep_out.contains(Point(x, y)): return
        for (tx, ty, r) in trees:
            if (tx - x) ** 2 + (ty - y) ** 2 < r * r: return
        trees.append((x, y, 3.0 if sp != 'matsu' else 3.5))
        B.tree(sp, x, y, float(S.ground(x, y)) + dz, sc, rng.uniform(0, 6.28) if yaw is None else yaw)
    north_bank(B, S, river, bridges, rng, tree)
    nakanoshima(B, S, river, bridges, isl, rng, tree)
    return trees

# ------------------------------------------------------------------ the north bank
def north_bank(B, S, river, bridges, rng, tree):
    road = way(S, 47584215)                              # 二条停車場嵐山線 along the river, from the bridge west
    east = way(S, 22727319)                              # 三条通 east of the bridge
    W = river.ch['main']
    # lamps on the river side of the riverside road, every ~24 m (lantern heads, facing the road)
    for t in np.arange(14.0, road.length - 6.0, 24.0):
        p = np.array(road.interpolate(t).coords[0]); d = U.tangent(road, t); n = np.array([d[1], -d[0]])     # to the river (south)
        if n[1] > 0: n = -n
        q = p + n * 4.4
        if river.all.buffer(2.2).contains(Point(q)): q = p + n * 3.6
        U.lamp_post(B, q[0], q[1], float(S.ground(*q)), h=4.0, yaw=math.atan2(-n[1], -n[0]))
    # trees along the strip between the road and the river (cherries and maples, a pine near the bridge)
    k = 0
    for t in np.arange(6.0, road.length - 4.0, 8.5):
        p = np.array(road.interpolate(t).coords[0]); d = U.tangent(road, t); n = np.array([d[1], -d[0]])
        if n[1] > 0: n = -n
        ko = river.ch['main'].union(river.ch['south']).buffer(1.8).union(river.ch['intake'].buffer(0.9))
        q = None
        for off in np.arange(4.4, 15.0, 0.8):
            c = p + n * off
            if not ko.contains(Point(c)) and ko.distance(Point(c)) > 0.6: q = c; break
        if q is None: k += 1; continue
        sp = 'sakura' if k % 3 != 1 else 'momiji'
        if t < 30: sp = 'matsu' if k % 2 == 0 else 'yanagi'
        tree(sp, q[0], q[1], rng.uniform(0.85, 1.15))
        k += 1
    # the boat landing's open riverside west of the road end: cherries and maples
    for (x, y) in ((-7738, 3052), (-7726, 3044), (-7712, 3056), (-7660, 3052), (-7648, 3060), (-7724, 3061), (-7700, 3060)):
        tree('sakura' if (x + y) % 3 else 'momiji', x, y, rng.uniform(0.9, 1.2))
    # a low wooden fence on stone posts along the top of the bank above the pool (the landing reach)
    e = []
    for x in np.arange(-7775.0, -7530.0, 2.0):
        seg = LineString([(x, 2950), (x, 3120)]).intersection(W)
        ys = [c[1] for g in getattr(seg, 'geoms', [seg]) for c in g.coords]
        if ys: e.append((x, max(ys) + 1.9))
    e = np.array(e)
    if len(e) > 2:
        gap = (-7714.0, -7666.0)                         # the landing stairs
        for part in (e[e[:, 0] < gap[0]], e[e[:, 0] > gap[1]]):
            if len(part) < 2: continue
            z = np.array([float(S.ground(*p)) for p in part])
            posts = np.c_[part, z]
            M.bars(B, posts, posts + [0, 0, 0.75], (1, 0, 0), 0.16, 0.16, 'stone', tag='main', caps=True)
            prim.sweep(B, posts + [0, 0, 0.62], [(-0.05, -0.04), (0.05, -0.04), (0.05, 0.04), (-0.05, 0.04)], 'wood_dark', tag='detail')
            prim.sweep(B, posts + [0, 0, 0.32], [(-0.04, -0.03), (0.04, -0.03), (0.04, 0.03), (-0.04, 0.03)], 'wood_dark', tag='detail')
            U.block_strip(B, posts, float(z.mean()) + 0.4)
    # east of the bridge: the low bank with cherries, the big 榎, the 史蹟 stones, benches
    tree('keyaki', -7369.5, 3091.5, 1.75, 0.6)          # the old 榎 by the north end (keyaki is the closest species we have)
    for t in np.arange(12.0, 120.0, 10.5):
        x = -7375 + t
        seg = LineString([(x, 3000), (x, 3120)]).intersection(W)
        ys = [c[1] for g in getattr(seg, 'geoms', [seg]) for c in g.coords]
        if not ys: continue
        y = max(ys) + rng.uniform(4.0, 7.5)
        if Point(x, y).distance(east) < 6.0: y = east.interpolate(east.project(Point(x, y))).y - 6.0
        tree('sakura' if int(t / 10.5) % 4 else 'yanagi', x, y, rng.uniform(0.9, 1.2))
    for (x, y, h, w, seed) in ((-7381.0, 3087.0, 1.9, 0.45, 11), (-7366.0, 3086.0, 1.2, 0.35, 12)):
        z = float(S.ground(x, y))
        M.hbox(B, x - w / 2, x + w / 2, y - 0.6 * w / 2, y + 0.6 * w / 2, z - 0.2, z + 0.25, 'stone', tag='main')
        M.hbox(B, x - w * 0.4, x + w * 0.4, y - 0.22, y + 0.22, z + 0.25, z + h, 'stone', tag='main')
        M.oquad(B, [(x - w * 0.3, y - 0.225, z + 0.5), (x + w * 0.3, y - 0.225, z + 0.5), (x + w * 0.3, y - 0.225, z + h - 0.1), (x - w * 0.3, y - 0.225, z + h - 0.1)],
                (0, -1, 0), 'stone', tag='detail', uv=np.array([(0, 0), (0.6, 0), (0.6, h), (0, h)]), c1=(0, 7, seed, 0))
        prim.polygon(B, [(x - 0.4, y - 0.3), (x + 0.4, y - 0.3), (x + 0.4, y + 0.3), (x - 0.4, y + 0.3)], z + 0.2, 'stone', tag='block')
    # benches along the bank path east of the bridge
    for x in (-7350.0, -7330.0, -7305.0, -7280.0):
        seg = LineString([(x, 3000), (x, 3120)]).intersection(W)
        ys = [c[1] for g in getattr(seg, 'geoms', [seg]) for c in g.coords]
        if ys: bench(B, S, x, max(ys) + 3.0, 0.0)
    # lamps along the bank east of the bridge
    for x in (-7356.0, -7318.0, -7280.0):
        seg = LineString([(x, 3000), (x, 3120)]).intersection(W)
        ys = [c[1] for g in getattr(seg, 'geoms', [seg]) for c in g.coords]
        if ys: U.lamp_post(B, x, max(ys) + 4.5, float(S.ground(x, max(ys) + 4.5)), h=3.8, yaw=-math.pi / 2)

def bench(B, S, x, y, yaw, L=1.8):
    z = float(S.ground(x, y))
    with Frame(B, x, y, z, yaw):
        M.hbox(B, -L / 2, L / 2, -0.22, 0.22, 0.4, 0.46, 'wood_natural', tag='main', c0=(180, 160, 130, 0))
        for u in (-L / 2 + 0.15, L / 2 - 0.15):
            M.hbox(B, u - 0.06, u + 0.06, -0.2, 0.2, 0.0, 0.4, 'stone', tag='detail')
        prim.polygon(B, [(-L / 2, -0.25), (L / 2, -0.25), (L / 2, 0.25), (-L / 2, 0.25)], 0.2, 'stone', tag='block')

# ------------------------------------------------------------------ 中之島
def nakanoshima(B, S, river, bridges, isl, rng, tree):
    road = way(S, 59377344)
    west = isl.intersection(sbox(-7520, 2800, -7270, 3000))
    # ground surfaces: the compacted-earth plaza (gravel), lawns (the OSM gardens) behind low fences, setts on the paths,
    # granite slabs at the bridge foot; the road keeps its asphalt
    road_band = road.buffer(4.6, cap_style='flat')
    for p in U.polys(west.difference(road_band)):
        S.paint.append({'poly': U.ring(p), 'surf': 'gravel'})
    gardens = [428892521, 428892524, 428892526, 428892531, 428892540, 428892548, 428892542]
    for gid in gardens:
        try: g = lu_poly(S, gid)
        except KeyError: continue
        S.paint.append({'poly': U.ring(g), 'surf': 'grass'})
        # 四つ目垣 round the lawn, open where a path meets it
        ring = np.asarray(g.buffer(-0.3).exterior.coords)
        yots(B, S, ring, rng)
        # cherries and a maple inside
        c = g.representative_point()
        n = max(1, int(g.area / 110))
        for k in range(n):
            q = sample_in(g.buffer(-2.0), rng)
            if q is not None: tree('sakura' if k % 3 != 2 else 'momiji', q[0], q[1], rng.uniform(0.9, 1.25))
    for wid, surf in ((519319717, 'stone_sett'), (519319719, 'stone_sett'), (428892584, 'stone_sett'), (209923785, 'stone_sett'), (519319711, 'stone_sett'), (428916295, 'stone_sett')):
        try: L = way(S, wid)
        except KeyError: continue
        S.paint.append({'poly': U.ring(L.buffer(1.4, cap_style='flat')), 'surf': surf})
    foot = bridges[0].footprint(0.0)
    plaza = Point(bridges[0].world(-6.0, 0.0)).buffer(11.0).intersection(isl.buffer(-0.5)).difference(road.buffer(4.0, cap_style='flat'))
    for p in U.polys(plaza): S.paint.append({'poly': U.ring(p), 'surf': 'stone_slab'})
    # the clock post (OSM amenity=clock) and benches along the north edge (OSM benches)
    clock(B, S, -7367.0, 2920.0)
    for f in S.osm['points']:
        if f['tags'].get('amenity') != 'bench': continue
        x, y = f['xy']
        if not west.contains(Point(x, y)): continue
        # face the river (north)
        bench(B, S, x, y, math.radians(12))
    # pines and cherries along the north edge of the island, a few big pines by the tea houses
    for k, t in enumerate(np.arange(0.0, 1.0, 1.0 / 90)):
        p = isl.exterior.interpolate(t, normalized=True)
        if p.x > -7275 or p.y < 2905: continue
        q = np.array([p.x, p.y]); c = np.array(isl.centroid.coords[0])
        q = q + (c - q) / np.linalg.norm(c - q) * rng.uniform(4.0, 6.5)
        tree('sakura' if k % 4 else 'matsu', q[0], q[1], rng.uniform(0.9, 1.2))
    for (x, y) in ((-7392, 2878), (-7368, 2880), (-7346, 2880), (-7424, 2906), (-7455, 2905), (-7470, 2900), (-7440, 2914)):
        tree('matsu', x, y, rng.uniform(1.0, 1.35))
    for f in S.osm['trees']:
        x, y = f['xy']
        if west.contains(Point(x, y)): tree('sakura', x, y, 1.1)
    # stone lanterns and lamps on the plaza
    for (x, y) in ((-7395.0, 2915.0), (-7380.0, 2912.0)):
        arch.ishidoro(B, x, y, float(S.ground(x, y)), h=1.8)
    for (x, y) in ((-7352.0, 2930.0), (-7318.0, 2938.0), (-7420.0, 2915.0), (-7340.0, 2900.0)):
        U.lamp_post(B, x, y, float(S.ground(x, y)), h=3.6, yaw=math.pi / 2)

def sample_in(P, rng, tries=30):
    if P.is_empty: return None
    x0, y0, x1, y1 = P.bounds
    for _ in range(tries):
        q = (rng.uniform(x0, x1), rng.uniform(y0, y1))
        if P.contains(Point(q)): return q
    return None

def yots(B, S, ring, rng, h=0.75):
    """四つ目垣: a low open bamboo fence (posts, three rails, sparse uprights), the lawns' edging"""
    ring = np.asarray(ring, float)
    for a, b in zip(ring[:-1], ring[1:]):
        L = float(np.linalg.norm(b - a))
        if L < 0.5: continue
        d = (b - a) / L
        za = float(S.ground(*a)); zb = float(S.ground(*b))
        k = max(1, int(L / 1.8))
        ps = np.array([a + d * L * i / k for i in range(k + 1)])
        zs = np.array([float(S.ground(*p)) for p in ps])
        M.bars(B, np.c_[ps, zs - 0.1], np.c_[ps, zs + h + 0.05], (1, 0, 0), 0.06, 0.06, 'wood_dark', tag='detail', caps=True)
        for zz in (0.25, 0.5, h - 0.03):
            M.bars(B, [(a[0], a[1], za + zz)], [(b[0], b[1], zb + zz)], (0, 0, 1), 0.035, 0.035, 'bamboo', tag='detail')
        m = max(1, int(L / 0.45))
        us = np.array([a + d * L * (i + 0.5) / m for i in range(m)])
        zu = za + (zb - za) * (np.arange(m) + 0.5) / m
        M.bars(B, np.c_[us, zu], np.c_[us, zu + h - 0.06], (1, 0, 0), 0.025, 0.025, 'bamboo', tag='detail')

def clock(B, S, x, y):
    z = float(S.ground(x, y))
    prim.cyl(B, (x, y, z), (x, y, z + 3.2), 0.09, 0.08, 8, 'wood_dark', tag='main')
    with Frame(B, x, y, z + 3.2, 0.0):
        prim.cyl(B, (0, -0.06, 0.0), (0, 0.06, 0.0), 0.36, 0.36, 16, 'wood_dark', tag='main')
        for s in (-1, 1):
            prim.cyl(B, (0, s * 0.06, 0.0), (0, s * 0.065, 0.0), 0.31, 0.31, 16, 'white_paint', tag='detail', caps=(s < 0, s > 0))
    prim.polygon(B, [(x - 0.3, y - 0.3), (x + 0.3, y - 0.3), (x + 0.3, y + 0.3), (x - 0.3, y + 0.3)], z + 0.2, 'stone', tag='block')
