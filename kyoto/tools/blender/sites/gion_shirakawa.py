"""白川 / 新橋通 / 白川南通: the stone-walled canal with its water, the north-bank promenade (willows and cherries,
granite posts and rail, lamps), the bridges (巽橋, 新橋, 大和橋 and the small ones), 辰巳大明神 with its vermilion
name-board fence on the rubble base, the 新橋通 ochaya rows (重伝建: uniform 庇, 千本格子, 2F 縁 + 簾) and the
川端茶屋 on the south bank whose rear rooms stand over the water."""
import math
import numpy as np
import shapely
import shapely.ops
from shapely.geometry import Polygon, LineString, Point, box as sbox
from jk import prim, arch, roof, Frame
import sites.machiya as M
import sites.gion_streets as G

CANAL_WATER = 546580436
CANAL_LINE = 550582581
X_MAX = 1528.0                     # model the canal up to the Hanamikoji-dori crossing

def canal_geom(S):
    w = [f for f in S.osm['water'] if f['id'] == CANAL_WATER][0]
    P = Polygon(w['poly'][0][0]).buffer(0)
    P = P.intersection(sbox(1236.0, 2120.0, X_MAX, 2330.0))
    if P.geom_type != 'Polygon': P = max(P.geoms, key=lambda q: q.area)
    ln = [f for f in S.osm['waterways'] if f['id'] == CANAL_LINE][0]['line'][0]
    C = LineString(ln)            # flows from (1721, 2291) (upstream) to (1235, 2149)
    return P, C

def build(B, S, used, stats):
    P, C = canal_geom(S)
    zw = water_level(S, P, C)
    bridges = bridge_list(S)
    channel(B, S, P, C, zw, bridges)
    for br in bridges: bridge(B, S, br, zw)
    tatsumi_shrine(B, S)
    promenade(B, S, P, C)
    rows(B, S, P, used, stats)

# ------------------------------------------------------------------ the canal
def water_level(S, P, C):
    """water surface along the canal: the lower bank minus 1.25 m, never rising downstream; returns zw(x, y)"""
    ts = np.arange(0, C.length, 2.0)
    zb = []
    for t in ts:
        p = C.interpolate(t); q = C.interpolate(min(C.length, t + 1.0)); r = C.interpolate(max(0.0, t - 1.0))
        d = np.array([q.x - r.x, q.y - r.y]); d /= max(np.linalg.norm(d), 1e-9); n = np.array([-d[1], d[0]])
        hw = 6.0
        zb.append(min(float(S.ground(p.x + n[0] * hw, p.y + n[1] * hw)), float(S.ground(p.x - n[0] * hw, p.y - n[1] * hw))))
    zb = np.convolve(np.pad(np.array(zb), 6, mode='edge'), np.ones(13) / 13, mode='valid')
    z = np.minimum.accumulate(zb - 1.25)                 # upstream first: water only falls downstream
    def f(x, y):
        tt = C.project(Point(x, y))
        return float(np.interp(tt, ts, z))
    return f

def densify(ring, step=1.0):
    pts = []
    for a, b in zip(ring[:-1], ring[1:]):
        a = np.asarray(a); b = np.asarray(b); L = np.linalg.norm(b - a)
        k = max(1, int(math.ceil(L / step)))
        for i in range(k): pts.append(a + (b - a) * i / k)
    return np.array(pts)

def channel(B, S, P, C, zw, bridges):
    import mapbox_earcut as earcut
    ring = np.asarray(P.exterior.coords)
    D = densify(ring, 1.5)
    # water surface (slightly sloped along the flow)
    I = earcut.triangulate_float64(D, np.array([len(D)], np.uint32)).reshape(-1, 3)
    Z = np.array([zw(x, y) for x, y in D])
    Pw = np.c_[D, Z]
    fn = np.cross(Pw[I[:, 1]] - Pw[I[:, 0]], Pw[I[:, 2]] - Pw[I[:, 0]])
    if fn[:, 2].sum() < 0: I = I[:, ::-1]
    B.add(Pw, I, 'water', UV=D, N=np.tile([0, 0, 1.0], (len(D), 1)), tag='main')
    # stone revetment: from the bank down below the water, facing into the canal
    Pc = shapely.geometry.polygon.orient(P, 1.0)
    R = densify(np.asarray(Pc.exterior.coords), 1.2)
    R = np.vstack([R, R[:1]])
    Q = []; UV = []; acc = 0.0
    for a, b in zip(R[:-1], R[1:]):
        if a[0] > X_MAX - 0.5 and b[0] > X_MAX - 0.5: continue
        d = b - a; L = np.linalg.norm(d)
        if L < 1e-6: continue
        nrm = np.array([d[1], -d[0]]) / L                 # outward (ccw ring: right side)
        za = float(S.ground(*(a + nrm * 1.2))) + 0.05; zb_ = float(S.ground(*(b + nrm * 1.2))) + 0.05
        wa = zw(*a) - 0.45; wb = zw(*b) - 0.45
        # facing inward: wind so the normal points to -nrm (left of a->b)
        Q.append([(b[0], b[1], wb), (a[0], a[1], wa), (a[0], a[1], za), (b[0], b[1], zb_)])
        UV.append([(acc + L, wb), (acc, wa), (acc, za), (acc + L, zb_)]); acc += L
    M.quads(B, np.array(Q), 'stone', UV=np.array(UV), tag='main')
    # granite coping on the north / west banks (the promenade side), where no building stands on the wall
    builtup = shapely.unary_union([G.footprint(b).buffer(0.6) for b in S.plateau if G.footprint(b).distance(P) < 1.5]) if S.plateau else None
    cq = []
    for a, b in zip(R[:-1], R[1:]):
        m = Point((a + b) / 2)
        if builtup is not None and builtup.contains(m): continue
        if a[0] > X_MAX - 0.5 and b[0] > X_MAX - 0.5: continue
        d = b - a; L = np.linalg.norm(d)
        if L < 1e-6: continue
        nrm = np.array([d[1], -d[0]]) / L
        za = float(S.ground(*(a + nrm * 1.2))) + 0.12; zb_ = float(S.ground(*(b + nrm * 1.2))) + 0.12
        cq.append([(a[0], a[1], za), (b[0], b[1], zb_), (b[0] + nrm[0] * 0.35, b[1] + nrm[1] * 0.35, zb_), (a[0] + nrm[0] * 0.35, a[1] + nrm[1] * 0.35, za)])
    if cq:
        cq = np.array(cq)
        M.quads(B, cq, 'curb', tag='main')
        side = cq[:, [1, 0, 0, 1], :].copy(); side[:, 2, 2] -= 0.25; side[:, 3, 2] -= 0.25
        side = side[:, [3, 2, 1, 0], :]
        M.quads(B, np.array([[q[1], q[0], q[3], q[2]] for q in side]), 'curb', tag='detail')
    # the generic terrain goes; our canal is the ground here (water raster: riverbed); blockers except the bridges
    S.cut.append(ring_list(P.buffer(0.25)))
    S.paint.append({'poly': ring_list(P), 'surf': 'riverbed'})
    blk = P.buffer(-0.05)
    for br in bridges: blk = blk.difference(br['line'].buffer(br['w'] / 2 + 0.3, cap_style='flat'))
    for g in (blk.geoms if hasattr(blk, 'geoms') else [blk]):
        if g.geom_type == 'Polygon' and g.area > 1:
            zz = float(np.mean([zw(*c) for c in list(g.exterior.coords)[:4]]))
            pts = np.asarray(g.exterior.coords)[:-1]
            prim.polygon(B, pts, zz, 'stone', tag='block', holes=[np.asarray(h.coords)[:-1] for h in g.interiors])

def ring_list(g):
    if g.geom_type != 'Polygon': g = max(g.geoms, key=lambda p: p.area)
    return [list(map(float, c)) for c in list(g.exterior.coords)[:-1]]

# ------------------------------------------------------------------ bridges
def bridge_list(S):
    ways = {w['id']: w for w in S.osm['ways']}
    def ln(i): return LineString(ways[i]['line'][0])
    out = [
        dict(name='tatsumi', line=ln(190891717), w=2.2, kind='tatsumi'),
        dict(name='shinbashi', line=ln(190891723), w=5.4, kind='stone'),
        dict(name='yamato', line=LineString([(1289.9, 2155.6), (1289.0, 2166.6)]), w=10.5, kind='stone'),
        dict(name='service', line=ln(571007317), w=3.6, kind='plain'),
        dict(name='shinmonzen', line=ln(190891721), w=5.0, kind='stone'),
        dict(name='hanami_n', line=LineString([(1505.9, 2316.0), (1504.9, 2302.6)]), w=11.0, kind='stone'),
    ]
    for br in out:
        # extend the deck to land 1.5 m beyond the banks
        c = np.array(br['line'].coords); d = c[-1] - c[0]; d /= np.linalg.norm(d)
        br['line'] = LineString([c[0] - d * 1.2, c[-1] + d * 1.2])
    return out

def bridge(B, S, br, zw):
    c = np.array(br['line'].coords); a, b = c[0], c[-1]
    d = b - a; L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]])
    za = float(S.ground(*(a - d * 0.8))); zb = float(S.ground(*(b + d * 0.8)))
    w = br['w']
    rise = 0.22 if br['kind'] == 'tatsumi' else 0.12
    k = 10
    ts = np.linspace(0, 1, k + 1)
    zz = za + (zb - za) * ts + rise * np.sin(ts * math.pi)
    pts = a[None, :] + d[None, :] * (ts * L)[:, None]
    th = 0.45
    top = []; bot = []
    for i in range(k + 1):
        for s in (-1, 1):
            p = pts[i] + n * s * w / 2
            top.append((p[0], p[1], zz[i] + 0.04)); bot.append((p[0], p[1], zz[i] - th))
    top = np.array(top); bot = np.array(bot)
    I = []
    for i in range(k):
        q = 2 * i
        I += [[q, q + 2, q + 3], [q, q + 3, q + 1]]
    I = np.array(I)
    fn = np.cross(top[I[:, 1]] - top[I[:, 0]], top[I[:, 2]] - top[I[:, 0]])
    if fn[:, 2].sum() < 0: I = I[:, ::-1]
    deck_mat = 'stone' if br['kind'] in ('tatsumi', 'stone') else 'curb'
    UVt = np.c_[np.repeat(ts * L, 2), np.tile([-w / 2, w / 2], k + 1)]
    B.add(top, I, deck_mat, UV=UVt, tag='main')
    B.add(bot, I[:, ::-1], deck_mat, UV=UVt, tag='main')
    for s in (0, 1):                                       # the two side faces
        Q = []
        for i in range(k):
            q = 2 * i + s
            Q.append([bot[q], bot[q + 2], top[q + 2], top[q]])
        Q = np.array(Q)
        nrm = np.r_[n * (1 if s else -1), 0]
        for qq in Q: M.oquad(B, qq, nrm, deck_mat, tag='main')
    # walk surface
    B.add(top + [0, 0, 0.0], I, 'stone', tag='walk')
    # parapets
    if br['kind'] == 'tatsumi':
        # granite end posts with the names, a low wooden rail on short stone posts
        for s in (-1, 1):
            for e in (0, k):
                p = pts[e] + n * s * (w / 2 - 0.12)
                prim.box(B, p[0] - 0.16, p[1] - 0.16, zz[e], p[0] + 0.16, p[1] + 0.16, zz[e] + 1.05, 'stone', tag='main')
                prim.lathe(B, (p[0], p[1], zz[e] + 1.05), [(0.2, 0.0), (0.0, 0.18)], 4, 'stone', tag='detail', smooth=False)
            rail = np.array([(*(pts[i] + n * s * (w / 2 - 0.12)), zz[i] + 0.62) for i in range(k + 1)])
            prim.sweep(B, rail, [(-0.07, -0.05), (0.07, -0.05), (0.07, 0.05), (-0.07, 0.05)], 'wood_natural', tag='main')
            for i in range(2, k - 1, 3):
                p = pts[i] + n * s * (w / 2 - 0.12)
                prim.box(B, p[0] - 0.09, p[1] - 0.09, zz[i], p[0] + 0.09, p[1] + 0.09, zz[i] + 0.58, 'stone', tag='detail')
            # name plate on the posts (巽橋 / 白川)
            p = pts[0] + n * s * (w / 2 - 0.12) - d * 0.17
            M.oquad(B, [(p[0] - n[0] * 0.12, p[1] - n[1] * 0.12, zz[0] + 0.35), (p[0] + n[0] * 0.12, p[1] + n[1] * 0.12, zz[0] + 0.35),
                         (p[0] + n[0] * 0.12, p[1] + n[1] * 0.12, zz[0] + 0.95), (p[0] - n[0] * 0.12, p[1] - n[1] * 0.12, zz[0] + 0.95)], (-d[0], -d[1], 0), 'stone', tag='detail', c1=(0, 7, 0, 0))
    else:
        h = 0.85 if br['kind'] == 'stone' else 1.0
        mat = 'stone' if br['kind'] == 'stone' else 'rail'
        for s in (-1, 1):
            rail = np.array([(*(pts[i] + n * s * (w / 2 - 0.15)), zz[i] + h) for i in range(k + 1)])
            prim.sweep(B, rail, [(-0.12, -0.08), (0.12, -0.08), (0.12, 0.06), (-0.12, 0.06)], mat, tag='main', caps=True)
            posts0 = np.array([(*(pts[i] + n * s * (w / 2 - 0.15)), zz[i]) for i in range(0, k + 1, 2)])
            M.bars(B, posts0, posts0 + [0, 0, h], (d[0], d[1], 0), 0.24 if mat == 'stone' else 0.08, 0.24 if mat == 'stone' else 0.08, mat, tag='main', caps=True)
            if mat == 'stone':
                # balusters / panel between the posts
                Q = []
                for i in range(k):
                    p0 = pts[i] + n * s * (w / 2 - 0.15); p1 = pts[i + 1] + n * s * (w / 2 - 0.15)
                    Q.append([(*p0, zz[i] + 0.1), (*p1, zz[i + 1] + 0.1), (*p1, zz[i + 1] + h - 0.1), (*p0, zz[i] + h - 0.1)])
                for qq in Q:
                    M.oquad(B, qq, (n[0] * s, n[1] * s, 0), 'stone', tag='main'); M.oquad(B, qq, (-n[0] * s, -n[1] * s, 0), 'stone', tag='main')
            else:
                rail2 = rail - [0, 0, 0.5]
                prim.sweep(B, rail2, [(-0.03, -0.03), (0.03, -0.03), (0.03, 0.03), (-0.03, 0.03)], mat, tag='detail')
            # blockers along the parapets
            seg = LineString([tuple(pts[0] + n * s * (w / 2 - 0.15)), tuple(pts[-1] + n * s * (w / 2 - 0.15))]).buffer(0.3, cap_style='flat')
            prim.polygon(B, np.asarray(seg.exterior.coords)[:-1], float(np.mean(zz)) + 0.3, 'stone', tag='block')

# ------------------------------------------------------------------ 辰巳大明神
def tatsumi_shrine(B, S):
    b = S.osm_building(1232496244)
    P = Polygon(b['poly'][0][0]).buffer(0)
    P = shapely.geometry.polygon.orient(P, 1.0)
    zg = float(S.ground(1428.5, 2206.5))
    zb = zg + 0.85                                   # top of the rubble base
    pts = np.asarray(P.exterior.coords)[:-1]
    # rubble stone base (石積み) with a granite cap
    prim.prism(B, pts, zg - 0.3, zb, 'stone', top_mat='stone', tag='main')
    for g in [P.buffer(-0.15)]:
        q = np.asarray(g.exterior.coords)[:-1]
        prim.prism(B, q, zb, zb + 0.12, 'curb', tag='main')
    for i in range(len(pts)):
        a, c = pts[i], pts[(i + 1) % len(pts)]
        L = np.linalg.norm(c - a)
        for t in np.arange(0.4, L - 0.2, 0.75):
            p = a + (c - a) * t / L
            prim.rock(B, (p[0], p[1], zg + 0.15 + 0.35 * ((t * 7) % 1)), 0.32, int(t * 100) + i, 'stone', tag='detail', flat=0.8)
    # the vermilion 玉垣 of name boards with black tops, open on the east (towards the bridge plaza)
    ring = np.asarray(P.buffer(-0.35).exterior.coords)
    cx, cy = P.centroid.x, P.centroid.y
    for i in range(len(ring) - 1):
        a, c = ring[i], ring[i + 1]
        L = np.linalg.norm(c - a)
        if L < 0.5: continue
        dd = (c - a) / L; nn = np.array([dd[1], -dd[0]])
        n = int(L / 0.24)
        for j in range(n):
            p = a + dd * (j + 0.5) * L / n
            if p[0] > cx + 3.0 and abs(p[1] - cy) < 1.2: continue          # entrance
            h = 1.15
            u0, u1 = p - dd * 0.1, p + dd * 0.1
            M.oquad(B, [(*u0, zb + 0.1), (*u1, zb + 0.1), (*u1, zb + h), (*u0, zb + h)], (nn[0], nn[1], 0), 'vermilion', tag='detail', c1=(0, 7, (i * 31 + j) % 251, 0),
                    uv=np.array([(0, 0), (0.45, 0), (0.45, 1.2), (0, 1.2)]))
            M.oquad(B, [(*u0, zb + 0.1), (*u1, zb + 0.1), (*u1, zb + h), (*u0, zb + h)], (-nn[0], -nn[1], 0), 'vermilion', tag='detail')
            M.bars(B, [(*p, zb + h)], [(*p, zb + h + 0.14)], (dd[0], dd[1], 0), 0.2, 0.05, 'black_lacquer', tag='detail', caps=True)
        M.bars(B, [(*a, zb + 0.15), (*a, zb + 0.95)], [(*c, zb + 0.15), (*c, zb + 0.95)], (0, 0, 1), 0.06, 0.06, 'black_lacquer', tag='detail')
    # the hall: a small 流造 shrine facing east, vermilion with a dark roof, red curtain
    with Frame(B, cx - 1.2, cy + 0.6, zb + 0.1, 0.0):
        arch.platform(B, [(-1.4, -1.2), (1.4, -1.2), (1.4, 1.2), (-1.4, 1.2)], 0.0, 0.35, mat='stone', walk=False)
        for (x, y) in ((-1.0, -0.8), (1.0, -0.8), (1.0, 0.8), (-1.0, 0.8)):
            prim.box(B, x - 0.08, y - 0.08, 0.35, x + 0.08, y + 0.08, 2.25, 'vermilion', tag='main')
        M.side_rect(B, -0.8, 0.8, 0.35, 2.2, -1.0, 'vermilion', facing=-1)
        M.front_rect(B, -1.0, 1.0, 0.35, 2.2, 0.8, 'wood_dark', facing=1)
        M.front_rect(B, -1.0, 1.0, 0.35, 2.2, -0.8, 'wood_dark', facing=-1)
        M.side_rect(B, -0.8, 0.8, 1.5, 2.2, 1.05, 'cloth', facing=1, c0=(200, 30, 30, 0))
        with Frame(B, 0.3, 0, 0, math.pi / 2):
            roof.roof(B, 1.8, 2.2, 2.3, 0.7, kind='kirizuma', cover='copper', pitch=0.6, rafter=0.18, rafter_mat='vermilion', rafter_end='white_paint', ends=None, verge=0.4, edge=0.15)
    # the torii at the entrance and two stone lanterns, a hanging lantern
    arch.torii(B, cx + 3.4, cy + 0.1, zg, math.pi / 2, h=3.2, span=2.1)
    arch.ishidoro(B, cx + 2.6, cy - 1.6, zb + 0.1, h=1.4)
    M.chochin(B, cx + 1.0, cy - 0.2, zb + 2.6, r=0.18, h=0.42)
    # steps up from the plaza
    arch.stairs(B, (cx + 4.4, cy + 0.1), (cx + 3.2, cy + 0.1), zg, zb + 0.1, 1.6, 'stone')
    B.tree('matsu', cx - 2.5, cy + 2.6, zb, 1.25, 0.4)
    prim.polygon(B, np.asarray(P.exterior.coords)[:-1], zb + 0.1, 'stone', tag='walk')

# ------------------------------------------------------------------ promenade (白川南通 side)
def promenade(B, S, P, C):
    ways = {w['id']: w for w in S.osm['ways']}
    lane = G.way_line(S, 179736228)                         # 白川南通
    # north-bank planting strip between the canal and the lane: willows and cherries alternating, the hedges
    north = Polygon(P.exterior.coords).buffer(0)
    t = 3.0; k = 0
    while t < lane.length - 4:
        p = lane.interpolate(t)
        # the canal edge nearest the lane point
        q = shapely.ops.nearest_points(P.exterior, p)[0]
        v = np.array([p.x - q.x, p.y - q.y]); dist = np.linalg.norm(v)
        if 2.5 < dist < 9.0:
            pos = np.array([q.x, q.y]) + v / dist * 1.3
            z = float(S.ground(*pos))
            sp = 'yanagi' if k % 2 == 0 else 'sakura'
            B.tree(sp, pos[0], pos[1], z, 1.0 + 0.15 * ((k * 0.37) % 1), (k * 1.3) % 6.28)
            # granite posts with a wooden rail along the canal side
            k += 1
        t += 7.5
    # posts and rail along the north edge
    edge = P.exterior.intersection(lane.buffer(9.0))
    for g in (edge.geoms if hasattr(edge, 'geoms') else [edge]):
        if g.geom_type != 'LineString' or g.length < 3: continue
        # keep only the side facing the lane
        mid = g.interpolate(0.5, normalized=True)
        if lane.distance(mid) > 8.0: continue
        L = g.length; ts = np.arange(0.5, L, 2.0)
        posts = []
        for tt in ts:
            p = g.interpolate(tt); q = shapely.ops.nearest_points(lane, p)[0]
            v = np.array([q.x - p.x, q.y - p.y]); v /= max(np.linalg.norm(v), 1e-9)
            pp = np.array([p.x, p.y]) + v * 0.45
            posts.append((pp[0], pp[1], float(S.ground(*pp))))
        posts = np.array(posts)
        if len(posts) < 2: continue
        M.bars(B, posts, posts + [0, 0, 0.72], (1, 0, 0), 0.16, 0.16, 'stone', tag='main', caps=True)
        prim.sweep(B, posts + [0, 0, 0.62], [(-0.04, -0.04), (0.04, -0.04), (0.04, 0.04), (-0.04, 0.04)], 'bamboo', tag='detail')
        seg = LineString(posts[:, :2]).buffer(0.3, cap_style='flat')
        if seg.geom_type == 'Polygon':
            prim.polygon(B, np.asarray(seg.exterior.coords)[:-1], float(posts[:, 2].mean()) + 0.2, 'stone', tag='block')
    # lamps on wooden posts along the lane (the square paper lamps of the promenade)
    t = 10.0
    while t < lane.length - 3:
        p = lane.interpolate(t); q = lane.interpolate(min(lane.length, t + 1))
        d = np.array([q.x - p.x, q.y - p.y]); d /= np.linalg.norm(d); n = np.array([d[1], -d[0]])     # to the canal (south)
        x, y = p.x + n[0] * 2.8, p.y + n[1] * 2.8
        z = float(S.ground(x, y))
        prim.box(B, x - 0.1, y - 0.1, z, x + 0.1, y + 0.1, z + 3.0, 'wood_dark', tag='main')
        prim.box(B, x - 0.18, y - 0.18, z + 2.4, x + 0.18, y + 0.18, z + 2.95, 'lamp', tag='main')
        prim.box(B, x - 0.22, y - 0.22, z + 2.95, x + 0.22, y + 0.22, z + 3.05, 'wood_dark', tag='main')
        B.lamp(x, y, z + 2.7, 20.0, (1.0, 0.75, 0.5))
        t += 21.0
    # paving of the lanes
    for wid in (179736228, 28412344, 190891725, 190891723):
        g = G.way_line(S, wid).buffer(2.4, cap_style='flat')
        S.paint.append({'poly': ring_list(g), 'surf': 'stone_sett'})
    # the willows and cherries of the canal bend and the north leg (OSM trees there), the big trees by the shrine
    for t in S.osm['trees']:
        x, y = t['xy']
        if 1405 < x < 1470 and 2180 < y < 2270:
            B.tree('yanagi' if (int(x * 7 + y) % 3) else 'sakura', x, y, float(S.ground(x, y)), 1.0, (x * 0.7) % 6.28)

# ------------------------------------------------------------------ the rows
def rows(B, S, P, used, stats):
    shin = G.way_line(S, 28412344)                       # 新橋通 (重伝建)
    shinE = G.concat([G.way_line(S, 190891725), G.way_line(S, 27574758)])
    uniform = dict(z1=2.78, kind='ochaya', railing=True, sudare=True, lattice='senbon', komayose=False, degoshi=True, wall=(196, 160, 104))
    def shin_style(b, P_, ring, rng):
        st = dict(uniform)
        st['wall'] = [(196, 160, 104), (205, 168, 98), (178, 148, 104), (214, 186, 128)][rng.integers(4)]
        st['inuyarai'] = rng.random() < 0.6
        st['party'] = 'wall_board' if rng.random() < 0.6 else 'wall_plaster'
        h = float(b['h'] or 9)
        if h < 7.0: st['kind'] = 'tsushi'
        return st
    picks = G.select(S, shin, 5.6, used=used)
    G.build_row(B, S, picks, shin, prefer='ochaya', seed0=55, used=used, stats=stats, styler=shin_style, need=1.9, back_lines=[G.way_line(S, 179736228)])
    picks = [(b, Q) for (b, Q) in G.select(S, shinE, 5.6, used=used) if Q.centroid.x < 1520]
    G.build_row(B, S, picks, shinE, prefer='ochaya', seed0=56, used=used, stats=stats, styler=shin_style, need=1.9)
    # 川端茶屋: rear rooms over the canal; the front on 末吉町通 where the lot reaches it, else (an inner lot) no front
    canal_backed(B, S, P, used, stats, streets=[G.way_line(S, 547229146), G.way_line(S, 556617387)])

def canal_backed(B, S, P, used, stats, streets):
    rng = np.random.default_rng(77)
    n = 0
    Pc = P.exterior
    for b in S.plateau:
        if b['id'] in used: continue
        Q = G.footprint(b)
        if not Q.is_valid: Q = Q.buffer(0)
        if Q.geom_type != 'Polygon' or Q.area < 15 or Q.distance(P) > 3.5: continue
        if Q.centroid.x > X_MAX - 2 or Q.centroid.y > 2205 and Q.centroid.x < 1445: continue     # the south bank and the bend only
        h = float(b['h'] or 0); st = int(b['st'] or 0)
        if b['kind'] not in ('trad', 'house', 'mid') or h > 13.0 or st > 3: continue
        if Q.intersects(P.buffer(-0.5)): pass
        c = Q.centroid
        q = shapely.ops.nearest_points(Pc, c)[0]
        t = Pc.project(q)
        a1 = Pc.interpolate(max(0, t - 2.0)); a2 = Pc.interpolate(min(Pc.length, t + 2.0))
        d = np.array([a2.x - a1.x, a2.y - a1.y]); d /= max(np.linalg.norm(d), 1e-9)
        away = np.array([c.x - q.x, c.y - q.y]); away /= max(np.linalg.norm(away), 1e-9)
        st_ = dict(kind='ochaya' if h >= 7.0 else 'tsushi', back='canal', sudare=True, railing=rng.random() < 0.6, inuyarai=rng.random() < 0.6,
                   party='wall_board' if rng.random() < 0.5 else 'wall_plaster')
        front = None
        for L in streets:
            if Q.distance(L) < 4.0: front = L; break
        ring = np.asarray(Q.exterior.coords)[:-1]
        if front is not None:
            edge, side, tt = G.front_of(Q, front)
            ring, edge, ce, _b = G.wall_lot(ring, edge, front, 1.6)      # the street front: wall behind the roof outline
        else:
            e0 = np.array([c.x, c.y]) + away * 40.0
            edge = (tuple(e0 - d * 3), tuple(e0 + d * 3))
            st_['facade'] = False; st_['eave'] = 0.3
        # the canal side stays on the outline: these backs stand on the stone revetment, rooms and engawa over the water
        O, U, N, yaw, Lc = M._frame(ring, edge)
        Wf = float(Lc[:, 0][Lc[:, 1] < 0.9].max())
        fc = O + U * Wf / 2 - N * 0.5
        try:
            M.build(B, ring, edge, float(S.ground(*fc)), min(max(h, 5.0), 12.5), st, st_, seed=int(rng.integers(1 << 30)))
            n += 1
        except Exception as e:
            print('canal house fail', b['id'], repr(e))
        S.exclude.append([list(map(float, cc)) for cc in np.asarray(Q.exterior.coords)[:-1]])
        used.add(b['id'])
    stats['canal'] = n
