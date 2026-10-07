"""伏見稲荷大社: placing the furniture along the routes and over the mountain (foxes, lanterns, お塚, tea houses, the
mountain shrines and their stone torii, the 四ツ辻 terrace), the forest, ground paint."""
import math
import numpy as np
import shapely
from shapely.geometry import Point, Polygon, LineString, box
import jk
from jk import prim, arch, roof, Frame
from . import fushimi_inari_torii as FT
from . import fushimi_inari_props as FX
from . import fushimi_inari_halls as FH
from . import fushimi_inari_mountain as FM

TEA = [301527736, 301527744, 301527777, 301527778, 301527780, 301527776, 626313775, 301527779, 301554311, 301554317, 626313722, 626313723,
       626313732, 626313740, 626313745, 626313752]
MOUNTAIN_SHRINES = [(626313751, 'nagare'), (626313736, 'nagare'), (626313728, 'nagare'), (626313742, 'nagare'), (626313725, 'nagare'),
                    (626313687, 'kasuga'), (342401488, 'kasuga'), (626342335, 'nagare'), (626342326, 'kasuga'), (626342298, 'kasuga'),
                    (626313734, 'kasuga'), (626342322, 'kasuga'), (626342324, 'kasuga'), (626342320, 'kasuga'), (626313719, 'kasuga'),
                    (1384916522, 'kasuga'), (1384916523, 'kasuga'), (626342329, 'kasuga'), (626342331, 'nagare'), (626342333, 'kasuga')]

class Ctx:
    """route geometry for placement: centrelines, corridor half widths, a union of the corridors"""
    def __init__(self, S, R, info):
        self.S = S; self.R = R; self.info = info
        self.lines = {k: LineString(r.P) for k, r in R.items()}
        self.o3 = {k: (float(np.max(info[k]['o2s'])) + 1.6 if info and k in info else 3.2) for k in R}
        self.corr = shapely.unary_union([self.lines[k].buffer(self.o3[k]) for k in R])
        shapely.prepare(self.corr)
        self.paths = shapely.unary_union([self.lines[k].buffer(self.o3[k] - 1.2) for k in R])
    def nearest(self, x, y):
        """(route, s, distance, side) of the nearest route centreline"""
        best = None
        for k, ln in self.lines.items():
            d = ln.distance(Point(x, y))
            if best is None or d < best[2]:
                s = ln.project(Point(x, y)); best = (k, s, d)
        k, s, d = best
        r = self.R[k]; px, py, pz, tx, ty = r.at(s)
        side = 1.0 if (-ty) * (x - px) + tx * (y - py) > 0 else -1.0
        return k, s, d, side
    def off_route(self, x, y, margin=0.6):
        """push a point that stands inside a corridor's shoulder band out beyond the pillars"""
        k, s, d, side = self.nearest(x, y)
        r = self.R[k]; i = r.idx(s)
        o2 = self.info[k]['o2s'][i] if self.info and k in self.info else 1.4
        if d < o2 + margin:
            px, py, pz, tx, ty = r.at(s)
            n = np.array([-ty, tx]) * side
            x, y = px + n[0] * (o2 + margin), py + n[1] * (o2 + margin)
        return x, y

def place_all(B, S, R, info, H, rng, ex):
    C = Ctx(S, R, info)
    foxes = []
    stats = {}
    # ---- foxes of the lower precinct (on the pedestals built with the halls)
    if H:
        for (p, yaw, s, mat, item) in H['foxes']: foxes.append((p, yaw, s, mat, item, 0.0))
    axis_yaw = -86.5 * math.pi / 180 + math.pi            # template +y facing west, down the axis
    prec = Polygon(S.polygon[0][0]).buffer(15)
    for p in S.osm['points']:
        t = p['tags']; x, y = p['xy']
        if t.get('tourism') == 'artwork' and t.get('artwork_type') == 'statue' and t.get('note', '狛狐') == '狛狐' and prec.contains(Point(x, y)):
            if x < 1420:
                yaw = axis_yaw; z = S.ground(x, y)
                foxes.append(((x, y, z), yaw, 0.85, 'stone', ['key', 'jewel', 'scroll', 'rice'][p['id'] % 4], 0.9))
            else:
                x, y = C.off_route(x, y, 0.7)
                k, s, d, side = C.nearest(x, y)
                r = C.R[k]; _, _, _, tx, ty = r.at(s)
                yaw = math.atan2(-ty, -tx) - math.pi / 2 + side * 0.35
                foxes.append(((x, y, S.ground(x, y)), yaw, 0.75, 'stone', ['key', 'jewel', 'scroll', 'rice'][p['id'] % 4], 0.8))
    # ---- lanterns (OSM lamps inside the precinct)
    nl = 0
    for p in S.osm['points']:
        t = p['tags']; x, y = p['xy']
        if t.get('man_made') != 'lamp' or not prec.contains(Point(x, y)): continue
        if x > 1420: x, y = C.off_route(x, y, 0.8)
        z = S.ground(x, y)
        if t.get('material') == 'wood': FX.post_lantern(B, x, y, z, 2.9, lit=True)
        else: FX.stone_lantern(B, x, y, z, 2.1 if x < 1420 else 1.6, lit=x < 1420)
        nl += 1
    if H:
        for p in H['lanterns']: FX.post_lantern(B, p[0], p[1], S.ground(p[0], p[1]), 3.0)
        # vermilion lanterns lining the 表参道 between the 一ノ鳥居 and the 二ノ鳥居
        for x in np.arange(1140.0, 1230.0, 18.0):
            for sg in (-1, 1):
                y = -2080.8 + (x - 1128.2) * math.tan(4.1 * math.pi / 180) + sg * 5.6
                FX.post_lantern(B, x, y, S.ground(x, y), 2.9)
        # 手水舎 by the gate
        FX.chozuya(B, 1259.7, -2055.8, S.ground(1259.7, -2055.8), -86.5 * math.pi / 180)
        ex.append([[1255.5, -2059.0], [1264.0, -2059.0], [1264.0, -2052.5], [1255.5, -2052.5]])
        # おもかる石: two small lanterns with the stone ball (空輪) on top
        for p in H['okusha']['omokaru']:
            z = S.ground(p[0], p[1])
            FX.small_lantern(B, p[0], p[1], z, 1.25)
            FX.ellipsoid(B, (p[0], p[1], z + 1.25 + 0.16), (0.16, 0.16, 0.15), 'stone', 10, 6)
    stats['lanterns'] = nl
    # ---- the mountain: tea houses, shrines, stone torii, お塚, path lamps, tunnel lanterns
    for oid in TEA:
        b = S.osm_building(oid)
        if b is None: continue
        c = Polygon(b['poly'][0][0]).centroid
        k, s, d, side = C.nearest(c.x, c.y)
        r = C.R[k]; px, py, _, _, _ = r.at(s)
        FX.chaya(B, S, oid, front=(c.x - px, c.y - py), storeys=2 if oid in (301527779, 626313732) else 1, ex=ex, benches=3, rng=rng, avoid=C.paths)
    for oid, kind in MOUNTAIN_SHRINES:
        b = S.osm_building(oid)
        if b is None: continue
        c = Polygon(b['poly'][0][0]).centroid
        k, s, d, side = C.nearest(c.x, c.y)
        r = C.R[k]; px, py, _, _, _ = r.at(s)
        cx, cy, Lf, Df, th = FH.rect_frame(S, oid, back=(c.x - px, c.y - py))
        big = Lf > 4.0
        FH.small_shrine(B, cx, cy, S.ground(cx, cy), th, min(Lf - 0.8, 4.4), min(Df - 0.8, 3.4), 2.2 if big else 1.4, kind=kind, base=0.7 if big else 0.5)
        ex.append(FH.world_ring(cx, cy, th, FH.rect_pts(-Lf / 2, -Df / 2, Lf / 2, Df / 2)))
    # 御膳谷奉拝所: a worship hall
    _hall(B, S, 301554315, C, ex)
    # OSM torii away from the tunnels: stone 明神 / vermilion
    tst = {}; tvm = {}
    for b in S.osm['barriers'] + S.osm['points']:
        t = b.get('tags', {})
        if t.get('man_made') != 'ceremonial_gate' or b['id'] in (359847609, 359847610): continue
        if 'line' in b:
            L = np.array(b['line'][0]); c = L.mean(0); w = float(t.get('width') or np.linalg.norm(L[-1] - L[0]))
            d_ = L[-1] - L[0]; yaw = math.atan2(d_[1], d_[0])
        else:
            c = np.array(b['xy']); w = float(t.get('width') or 2.6); yaw = None
        if not prec.contains(Point(*c)): continue
        k, s, d, side = C.nearest(*c)
        if d < 3.0 and c[0] > 1380: continue            # the tunnels carry their own
        r = C.R[k]; _, _, _, tx, ty = r.at(s)
        if yaw is None: yaw = math.atan2(ty, tx) - math.pi / 2
        # face downhill: +y uphill
        fy = np.array([-math.sin(yaw), math.cos(yaw)])
        if S.ground(*(c + fy * 2)) < S.ground(*(c - fy * 2)): yaw += math.pi
        w = max(1.0, min(w, 5.0)); z = S.ground(*c)
        if t.get('material') == 'stone' or t.get('material') == 'concrete' or t.get('colour') in ('gray', 'grey'):
            key = round(w * 2) / 2
            if key not in tst: tst[key] = FT.Template(FT.stone_torii, key * 1.0, key * 0.63, max(0.16, key * 0.075))
            tst[key].add(c[0], c[1], z, yaw)
        else:
            key = round(w * 2) / 2
            if key not in tvm: tvm[key] = FT.Template(FT.inari_torii, key * 1.1, key * 0.67, max(0.15, key * 0.07), 'M' if key < 3.5 else 'L')
            tvm[key].add(c[0], c[1], z, yaw, seed=int(rng.integers(250)))
    stats['osm_torii'] = sum(len(t.inst) for t in list(tst.values()) + list(tvm.values()))
    for t in list(tst.values()) + list(tvm.values()): t.flush(B)
    # the 四ツ辻 terrace
    _yottsu(B, S, ex, C.paths)
    # お塚 clusters
    oc = FX.Otsuka()
    bl = shapely.unary_union([Polygon(b['poly'][0][0]).buffer(1.5) for b in S.osm['buildings'] if prec.contains(Polygon(b['poly'][0][0]).centroid)])
    shapely.prepare(bl)
    plz = shapely.unary_union([Point(*c).buffer(r_ + 2) for (c, r_) in FM.PLAZAS]); shapely.prepare(plz)
    placed = []
    for name in ('okusha_kumataka', 'kumataka_mittsu', 'mittsu_yottsu', 'loop_a', 'loop_b'):
        r = C.R[name]
        s = float(rng.uniform(5, 15)); side = 1.0
        while s < r.L - 3:
            px, py, pz, tx, ty = r.at(s)
            n = np.array([-ty, tx]) * side
            size = float(rng.uniform(0.8, 1.15))
            dist = C.o3[name] + 1.5 * size + 0.25
            cx, cy = px + n[0] * dist, py + n[1] * dist
            fp = Point(cx, cy).buffer(1.35 * size)
            ok = not C.corr.intersects(fp) and not bl.intersects(fp) and not plz.intersects(fp) and all(math.hypot(cx - a, cy - b_) > 6 for (a, b_) in placed)
            zz = S.ground(*np.array(fp.exterior.coords).T)
            if not ok or zz.max() - zz.min() > 5.0:
                # try the other side of the path
                n = -n; cx, cy = px + n[0] * dist, py + n[1] * dist; fp = Point(cx, cy).buffer(1.35 * size)
                ok = not C.corr.intersects(fp) and not bl.intersects(fp) and not plz.intersects(fp) and all(math.hypot(cx - a, cy - b_) > 6 for (a, b_) in placed)
                zz = S.ground(*np.array(fp.exterior.coords).T)
            if ok and zz.max() - zz.min() < 5.0:
                yaw = math.atan2(n[1], n[0]) - math.pi / 2       # local +y away from the path: the steles face it
                oc.cluster(B, S, cx, cy, yaw, rng, size, foxes)
                placed.append((cx, cy)); side = -side
                s += float(rng.uniform(14, 30)) if name.startswith('loop') or name == 'mittsu_yottsu' else float(rng.uniform(22, 40))
            else:
                s += 3.0
    # at the OSM お塚 / wayside shrines on the mountain
    for p in S.osm['points']:
        if p['tags'].get('historic') != 'wayside_shrine': continue
        x, y = p['xy']
        if x < 1420 or not prec.contains(Point(x, y)): continue
        fp = Point(x, y).buffer(2.2)
        if C.corr.intersects(fp) or any(math.hypot(x - a, y - b_) < 5 for (a, b_) in placed): continue
        k, s, d, side = C.nearest(x, y)
        r = C.R[k]; px, py, _, _, _ = r.at(s)
        yaw = math.atan2(y - py, x - px) - math.pi / 2
        oc.cluster(B, S, x, y, yaw, rng, 1.1, foxes); placed.append((x, y))
    stats['otsuka'] = oc.n
    stats['mini_torii'] = sum(len(t.inst) for t in oc.mini)
    oc.flush(B)
    # path lamps along the mountain tunnels, lanterns hanging in the 千本鳥居
    nlamp = 0
    for name in ('okusha_kumataka', 'kumataka_mittsu', 'mittsu_yottsu', 'loop_a', 'loop_b', 'lower'):
        r = C.R[name]; side = 1.0
        for s in np.arange(8.0, r.L - 4, 21.0):
            px, py, pz, tx, ty = r.at(s); i = r.idx(s)
            o2 = info[name]['o2s'][i] if info else 1.4
            n = np.array([-ty, tx]) * side
            x, y = px + n[0] * (o2 + 0.3), py + n[1] * (o2 + 0.3)
            if bl.contains(Point(x, y)): continue
            FX.path_lamp(B, x, y, r.z[i] + 0.03, math.atan2(ty, tx)); side = -side; nlamp += 1
    for name in ('senbon_up', 'senbon_down'):
        r = C.R[name]
        for s in np.arange(6.0, r.L - 3, 13.0):
            px, py, pz, tx, ty = r.at(s)
            FH.hanging_lantern(B, px, py, pz + 0.03 + 2.42, 0.42, mat='metal_dark'); nlamp += 1
    stats['path_lamps'] = nlamp
    # foxes
    tpl = {}
    for (p, yaw, s, mat, item, ped) in foxes:
        FX.fox_on_pedestal(tpl, None, p[0], p[1], p[2], yaw, s, mat, item, ped=ped, B=B)
    stats['foxes'] = len(foxes)
    for t in tpl.values(): t.flush(B)
    return stats, placed

def _hall(B, S, oid, C, ex):
    """a mountain worship hall (御膳谷奉拝所): 3 x 2 bays, open front, vermilion, copper 入母屋"""
    b = S.osm_building(oid)
    c = Polygon(b['poly'][0][0]).centroid
    k, s, d, side = C.nearest(c.x, c.y)
    px, py, _, _, _ = C.R[k].at(s)
    cx, cy, Lf, Df, th = FH.rect_frame(S, oid, back=(c.x - px, c.y - py))
    z0 = S.ground(cx, cy)
    L, D = Lf - 3.0, Df - 3.0
    us = np.linspace(-L / 2, L / 2, 4); vs = np.linspace(-D / 2, D / 2, 3)
    with Frame(B, cx, cy, z0, th):
        arch.platform(B, FH.rect_pts(-L / 2 - 1.0, -D / 2 - 1.0, L / 2 + 1.0, D / 2 + 1.0), -0.8, 0.3)
        FH.ring_pillars(B, us, vs, 0.3, 3.8, 0.17, 'vermilion')
        for (p0, p1, sd) in FH.bays(us, vs):
            if sd == 0: arch.infill(B, p0, p1, 2.9, 3.6, 'plaster')
            else: arch.infill(B, p0, p1, 0.3, 3.6, 'plaster' if sd != 2 else 'koshi', mat='vermilion')
        arch.nageshi(B, L, D, 3.8, 'vermilion', h=0.26, w=0.12, out=0.12)
        roof.roof(B, L, D, 3.95, 1.4, kind='irimoya', cover='copper', pitch=0.55, rafter=0.3, rafter_mat='vermilion', rafter_end='white_paint',
                  bargeboard_mat='vermilion', sori=0.3)
        for x in (us[:-1] + us[1:]) / 2: FH.hanging_lantern(B, x, -D / 2 - 0.5, 3.8, 0.55, mat='bronze')
    ex.append(FH.world_ring(cx, cy, th, FH.rect_pts(-Lf / 2, -Df / 2, Lf / 2, Df / 2)))

def _yottsu(B, S, ex, avoid=None):
    """四ツ辻: the saddle at 162 m, the view west over Kyoto — a paved terrace with a stone edge, a wooden railing,
    red benches facing the view, lanterns"""
    poly = [(2057.5, -1846.0), (2072.0, -1846.0), (2075.0, -1853.0), (2073.0, -1862.5), (2057.5, -1862.5)]
    P = Polygon(poly)
    if avoid is not None:
        # the stairs up from 三ツ辻 arrive along the west edge: leave them their corridor
        g = P.difference(avoid.buffer(0.2))
        P = max(g.geoms, key=lambda q: q.area) if hasattr(g, 'geoms') else g
        P = P.simplify(0.2)
    zt = 162.25
    # the terrace surface (flat), the stone retaining edge on the west where the ground drops
    import mapbox_earcut as earcut
    xs = np.arange(2057.5, 2075.6, 0.5); ys = np.arange(-1862.5, -1845.4, 0.5)
    X, Y = np.meshgrid(xs, ys)
    inside = shapely.contains_xy(P.buffer(0.01), X, Y)
    Z = np.full(X.shape, zt)
    Vt = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1); nx = len(xs); I = []
    for j in range(len(ys) - 1):
        for i in range(nx - 1):
            a = j * nx + i
            if inside[j, i] and inside[j, i + 1] and inside[j + 1, i] and inside[j + 1, i + 1]:
                I += [[a, a + 1, a + nx + 1], [a, a + nx + 1, a + nx]]
    from .fushimi_inari_paths import SURF
    B.add(Vt, I, 'ground', UV=Vt[:, :2], N=np.tile([0, 0, 1.0], (len(Vt), 1)), c1=(0, 0, 0, SURF.index('stone_slab')))
    B.add(Vt, I, 'stone', tag='walk')
    # stone edge on the west (the drop) and the railing
    ring = list(P.exterior.coords)
    for a, b in zip(ring[:-1], ring[1:]):
        za = S.ground(*a); zb = S.ground(*b)
        P4 = np.array([(a[0], a[1], min(za, zb) - 0.6), (b[0], b[1], min(za, zb) - 0.6), (b[0], b[1], zt + 0.02), (a[0], a[1], zt + 0.02)])
        B.add(P4, [[0, 1, 2], [0, 2, 3], [0, 2, 1], [0, 3, 2]], 'stone')
    # the railing along the west-facing edges (the view), benches inside the terrace facing it
    ring = list(P.exterior.coords)
    if not P.exterior.is_ccw: ring = ring[::-1]
    west = []
    for a_, b_ in zip(ring[:-1], ring[1:]):
        d_ = np.subtract(b_, a_); L_ = np.linalg.norm(d_)
        if L_ < 0.5: continue
        nrm = np.array([d_[1], -d_[0]]) / L_
        if nrm[0] < -0.4:
            q0 = np.array(a_) - nrm * 0.25; q1 = np.array(b_) - nrm * 0.25
            FX.railing_wood(B, [q0, q1], lambda x, y: zt, h=1.0); west.append((q0, q1, nrm))
    # benches facing west, a stone lantern, a post lantern
    for y in (-1849.5, -1853.0, -1856.5):
        xs_ = [x_ for x_ in np.arange(2058.0, 2068.0, 0.25) if P.buffer(-0.9).contains(Point(x_, y))]
        if not xs_: continue
        x = xs_[0] + 0.6
        prim.box(B, x - 0.3, y - 0.85, zt + 0.38, x + 0.3, y + 0.85, zt + 0.45, 'cloth', c0=(196, 28, 28, 0), faces='xXyYZ')
        for sx in (-1, 1):
            for sy in (-1, 1):
                prim.box(B, x + sx * 0.22 - 0.03, y + sy * 0.75 - 0.03, zt, x + sx * 0.22 + 0.03, y + sy * 0.75 + 0.03, zt + 0.38, 'wood_dark', faces='xXyY', tag='detail')
    prim.cyl(B, (2061.0, -1858.6, zt), (2061.0, -1858.6, zt + 2.3), 0.025, 0.025, 6, 'bamboo', tag='detail')
    prim.lathe(B, (2061.0, -1858.6, zt + 2.0), [(0.0, 0.42), (1.25, 0.0), (1.27, -0.05)], 16, 'cloth', c0=(200, 30, 30, 0), smooth=False)
    prim.lathe(B, (2061.0, -1858.6, zt + 2.0), [(1.27, -0.05), (1.25, 0.0), (0.0, 0.42)], 16, 'cloth', c0=(200, 30, 30, 0), smooth=False, tag='detail')
    FX.stone_lantern(B, 2071.5, -1847.5, zt, 1.8, lit=True)
    FX.post_lantern(B, 2058.3, -1846.8, zt, 2.6)
    S.cut.append([list(map(list, P.buffer(0.3).exterior.coords))])

def forest(B, S, R, info, rng, keep_out):
    """the mountain forest: evergreen oak (kashi) and cedar / cypress (sugi, hinoki) on the slopes, maples near the
    paths, a few bamboo groves low down; trunks kept off the corridors, buildings and the lower precinct"""
    prec = Polygon(S.polygon[0][0])
    corr = shapely.unary_union([LineString(r.P).buffer((float(np.max(info[k]['o2s'])) + 1.6 if info and k in info else 3.2) + 0.6) for k, r in R.items()])
    blds = [Polygon(b['poly'][0][0]).buffer(2.0) for b in S.osm['buildings']]
    blds += [Polygon(p['poly'][0][0]).buffer(1.5) for p in S.plateau if p['poly']]
    water = [Polygon(w['poly'][0][0]) for w in S.osm['water'] if w['poly']]
    lower = box(1090, -2125, 1352, -2015)
    block = shapely.unary_union([corr, lower] + blds + water + keep_out)
    shapely.prepare(prec); shapely.prepare(block)
    x0, y0, x1, y1 = prec.bounds
    sp = 6.0
    X, Y = np.meshgrid(np.arange(x0, x1, sp), np.arange(y0, y1, sp))
    X = X.ravel() + rng.uniform(-2.4, 2.4, X.size); Y = Y.ravel() + rng.uniform(-2.4, 2.4, Y.size)
    ok = shapely.contains_xy(prec, X, Y) & ~shapely.contains_xy(block, X, Y)
    X, Y = X[ok], Y[ok]
    Z = S.ground(X, Y)
    # distance to the nearest route (maples close to the paths)
    lines = shapely.unary_union([LineString(r.P) for r in R.values()])
    D = shapely.distance(shapely.points(X, Y), lines)
    groves = [(1470.0, -2000.0, 30.0), (1700.0, -2060.0, 28.0), (1560.0, -1860.0, 26.0)]
    n = {}
    for x, y, z, d in zip(X, Y, Z, D):
        u = rng.random()
        if any(math.hypot(x - gx, y - gy) < gr for (gx, gy, gr) in groves): sp_ = 'take'
        elif d < 9 and u < 0.22: sp_ = 'momiji'
        elif z < 90:
            sp_ = ['kashi', 'kashi', 'kashi', 'sugi', 'hinoki', 'momiji', 'keyaki', 'sakura', 'kashi', 'sugi'][int(u * 10)]
        else:
            sp_ = ['sugi', 'sugi', 'hinoki', 'hinoki', 'kashi', 'kashi', 'kashi', 'momiji', 'matsu', 'sugi'][int(u * 10)]
        sc = float(rng.uniform(0.85, 1.25)) * (1.15 if sp_ in ('sugi', 'hinoki') else 1.0)
        B.tree(sp_, float(x), float(y), float(z), sc, float(rng.uniform(0, 2 * math.pi)))
        n[sp_] = n.get(sp_, 0) + 1
    # the lower precinct: a pine by the gate, a few trees about the courts
    for (sp_, x, y, sc) in (('matsu', 1275.0, -2088.0, 1.1), ('matsu', 1252.0, -2088.5, 0.9), ('sakura', 1238.0, -2058.0, 1.0), ('momiji', 1242.0, -2088.0, 0.9),
                            ('keyaki', 1215.0, -2058.0, 1.3), ('momiji', 1300.0, -2094.0, 0.9), ('matsu', 1309.0, -2036.0, 1.0), ('keyaki', 1350.0, -2100.0, 1.3),
                            ('sugi', 1350.0, -2040.0, 1.3), ('kashi', 1347.0, -2058.0, 1.2), ('momiji', 1150.0, -2088.0, 0.9), ('momiji', 1180.0, -2087.0, 1.0),
                            ('sakura', 1160.0, -2073.0, 1.0)):
        B.tree(sp_, x, y, float(S.ground(x, y)), sc, float(rng.uniform(0, 6.28)))
    return n

def paint(S):
    """ground surfaces of the lower precinct: the stone-paved 表参道, gravel courts, the paved axis through them"""
    ln = None
    for w in S.osm['ways']:
        if w['id'] == 105449722: ln = LineString(w['line'][0])
    if ln is not None:
        S.paint.append({'poly': [list(p) for p in ln.buffer(4.2, cap_style='flat').exterior.coords], 'surf': 'stone_slab'})
    courts = [(1250.0, -2100.0, 1300.0, -2042.0), (1300.0, -2112.0, 1345.0, -2030.0)]
    for (a, b, c, d) in courts:
        S.paint.append({'poly': [[a, b], [c, b], [c, d], [a, d]], 'surf': 'gravel'})
    # the paved axis (楼門 → 外拝殿 → 内拝殿 stairs) and the cross path north-south in front of the 外拝殿
    ax = LineString([(1259.0, -2071.4), (1300.0, -2068.6)])
    S.paint.append({'poly': [list(p) for p in ax.buffer(1.7, cap_style='flat').exterior.coords], 'surf': 'stone_slab'})
    cr = LineString([(1292.6, -2090.0), (1291.2, -2048.0)])
    S.paint.append({'poly': [list(p) for p in cr.buffer(1.4, cap_style='flat').exterior.coords], 'surf': 'stone_slab'})
