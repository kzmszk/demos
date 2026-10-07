"""東寺: the precinct ground — the 築地塀 (大垣 and the inner walls of 西院, 本坊 / 小子房 and 灌頂院, the latter a 五本線
筋塀), the moat (堀) on 九条通 with its stone revetment, the stone bridge to 南大門 and the small bridge at the south-west
gate, the 瓢箪池 and the garden round the pagoda, the moat round the 宝蔵, gravel courts, paths, lanterns and trees.

Everything is placed from OSM (walls 363554424 / 363251168 / 363251167 / 363554416 / 187657264 / 364945346 / 187657269,
the moat water 269856746-8, ponds 187657270 / 187657261, the 宝蔵 moat -2526311) and the laser DEM."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from jk import prim, arch
from jk.core import Frame
from sites.toji_kit import (WOOD, PLASTER, EARTH, rect, slab, quad, walk_poly, walk_rect, block_poly, block_rect, block_line, beam, post, tsuiji,
                            stone_lantern, bronze_lantern, rock)

SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
        'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck']

def outer(poly):
    while isinstance(poly[0][0], (list, tuple)): poly = poly[0]
    return poly

def barrier(S, i):
    for b in S.osm['barriers']:
        if b['id'] == i: return [list(map(tuple, l)) for l in b['line']]
    return []

def water(S, i):
    for w in S.osm['water']:
        if w['id'] == i: return w
    return None

def rings_of(g):
    for p in (g.geoms if hasattr(g, 'geoms') else [g]):
        if p.geom_type != 'Polygon' or p.is_empty: continue
        yield p

def band(B, S, inner, outer_g, z_in, z_out_off=0.03, surf='grass', seg=1.5, tag='main'):
    """a ground band (outer_g minus inner) following the DEM (outer boundary) with the inner boundary at z_in(x, y):
    earcut over densified rings; drawn by the ground program with the given surface"""
    g = outer_g.difference(inner)
    for p in rings_of(g):
        p = orient(p.segmentize(seg), 1.0)
        rings = [np.array(p.exterior.coords[:-1])] + [np.array(r.coords[:-1]) for r in p.interiors]
        V = np.concatenate(rings)
        Z = np.array([float(S.ground(x, y)) + z_out_off for x, y in V])
        if z_in is not None:
            d_in = shapely.distance(inner, shapely.points(V))
            near = d_in < 0.05
            Z[near] = np.array([z_in(x, y) for x, y in V[near]])
        import mapbox_earcut as earcut
        ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
        I = earcut.triangulate_float64(V, ends).reshape(-1, 3)
        if not len(I): continue
        P = np.c_[V, Z]
        fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
        I[fn[:, 2] < 0] = I[fn[:, 2] < 0][:, ::-1]
        B.add(P, I, 'ground', UV=V, smooth=True, tag=tag, c1=(0, 0, 0, SURF.index(surf)))

# ------------------------------------------------------------------ walls
OUTER = [  # (polyline, gaps as (x, y) points of gates with half widths) — the 大垣
    [(-887.5, -693.6), (-990.9, -693.5), (-1004.0, -693.7)],
    [(-1022.6, -693.9), (-1068.4, -694.3)],
    [(-1071.2, -694.3), (-1138.2, -694.4), (-1139.1, -612.3), (-1139.75, -573.3)],
    [(-1139.95, -562.7), (-1140.2, -528.2), (-1140.4, -495.8), (-1141.0, -437.6), (-1141.1, -417.6), (-1115.6, -417.5)],
    [(-1073.8, -417.2), (-1020.1, -416.95)],
    [(-1009.1, -417.0), (-960.5, -415.6), (-924.2, -414.9), (-905.9, -415.0), (-906.0, -419.9)],
    [(-888.0, -420.2), (-888.2, -430.4)],
    [(-888.45, -440.8), (-888.4, -503.8), (-888.3, -561.5)],
    [(-888.3, -572.5), (-887.5, -693.6)],
]

def walls(B, S, stats):
    n0 = B.ntri()
    # the 大垣: 3.2 m, battered from 1.7 to 0.9 m, posts on the street side
    for pl in OUTER:
        # posts outward: the street side is to the right of these polylines (they run counter-clockwise round the precinct... mixed): pick by centre
        c = np.array([-1013.0, -555.0])
        a = np.array(pl[0]); b = np.array(pl[1]); d = b - a; n = np.array([-d[1], d[0]])
        outer_ = 1 if n @ (a - c) > 0 else -1
        tsuiji(B, S, pl, h=3.2, base=1.7, top=0.9, post_every=2.9, tint=EARTH, outer=outer_)
    # inner walls: 西院 / 本坊 (2.6 m), 灌頂院 (筋塀, five white lines)
    inner = [(187657260, 0), (187657262, 0), (364715536, 0), (364715535, 0), (466050528, 0), (466050529, 0), (364715527, 0), (364715530, 0),
             (187657272, 0), (364939561, 5), (187657268, 5), (364939558, 5)]
    for (i, lines) in inner:
        for l in barrier(S, i):
            if len(l) < 2: continue
            tsuiji(B, S, l, h=2.6, base=1.0, top=0.65, post_every=2.7, tint=EARTH, lines=lines, outer=1)
    # exclusion corridors along every wall (generic OSM walls / fences there are replaced)
    for pl in OUTER:
        S.exclude.append(list(map(list, LineString(pl).buffer(1.6, cap_style='flat').exterior.coords)))
    for (i, _) in inner:
        for l in barrier(S, i):
            if len(l) >= 2: S.exclude.append(list(map(list, LineString(l).buffer(1.1, cap_style='flat').exterior.coords)))
    stats['walls_tris'] = B.ntri() - n0

# ------------------------------------------------------------------ the moat on 九条通
WL_MOAT = 21.05

def moat(B, S, stats, nandaimon_floor):
    n0 = B.ntri()
    polys = [Polygon(outer(water(S, i)['poly'])) for i in (269856746, 269856747, 269856748)]
    culvert = box(-1017.4, -707.6, -1008.6, -703.2)
    westgap = box(-1072.7, -709.4, -1066.6, -699.4)
    g = unary_union(polys + [culvert, westgap]).buffer(0.05, join_style='mitre').buffer(-0.05, join_style='mitre')
    g = orient(max(rings_of(g), key=lambda p: p.area).simplify(0.08), 1.0)
    WL = WL_MOAT
    ring = np.array(g.exterior.coords[:-1])
    n = len(ring)
    # bank top along the edge (sampled outward, beyond the interpolated laser surface of the water)
    def ztop(p, nout):
        return float(S.ground(*(p + nout * 1.6))) + 0.06
    seg_n = []
    for k in range(n):
        a = ring[k]; b = ring[(k + 1) % n]; d = b - a; L = np.linalg.norm(d)
        if L < 1e-6: seg_n.append(np.array([0.0, 1.0])); continue
        seg_n.append(np.array([d[1], -d[0]]) / L)            # CCW ring: outward normal on the right
    vn = []
    for k in range(n):
        m = seg_n[k - 1] + seg_n[k]; m /= max(np.linalg.norm(m), 1e-9)
        vn.append(m)
    # the revetment: battered rough-stone walls (WL - 0.7 .. bank top) and a dressed coping
    for k in range(n):
        a = ring[k]; b = ring[(k + 1) % n]; L = float(np.linalg.norm(b - a))
        if L < 0.05: continue
        m = max(1, int(L / 2.0))
        for j in range(m):
            p = a + (b - a) * j / m; q = a + (b - a) * (j + 1) / m
            na = seg_n[k]; zp_ = ztop(p, na); zq_ = ztop(q, na)
            P = np.array([np.r_[p - na * 0.35, WL - 0.7], np.r_[q - na * 0.35, WL - 0.7], np.r_[q, zq_ - 0.18], np.r_[p, zp_ - 0.18]])
            B.add(P, [[0, 2, 1], [0, 3, 2]], 'stone', UV=np.array([[0, WL], [L / m, WL], [L / m, zq_], [0, zp_]]) + [[float(np.linalg.norm(p - a)), 0]] * 4)
            # coping stones: top + front face
            P = np.array([np.r_[p, zp_ - 0.18], np.r_[q, zq_ - 0.18], np.r_[q, zq_], np.r_[p, zp_]])
            B.add(P, [[0, 2, 1], [0, 3, 2]], 'curb')
            P = np.array([np.r_[p, zp_], np.r_[q, zq_], np.r_[q + na * 0.5, zq_], np.r_[p + na * 0.5, zp_]])
            B.add(P, [[0, 2, 1], [0, 3, 2]], 'curb')
    # the water and the bank bands (my own ground, the generic terrain is cut away round the moat)
    prim.polygon(B, ring, WL, 'water')
    cut = g.buffer(0.5, join_style='mitre')
    S.cut.append([list(map(float, c)) for c in cut.exterior.coords])
    # banks: the precinct side (north: lawn) and the street side (south: the sidewalk's paving)
    xs = np.linspace(g.bounds[0] - 5, g.bounds[2] + 5, 80)
    def ymid(x):
        line = LineString([(x, -800), (x, -600)]).intersection(g)
        if line.is_empty: return None
        return 0.5 * (line.bounds[1] + line.bounds[3])
    mids = [(x, ymid(x)) for x in xs]
    mids = [(x, y) for x, y in mids if y is not None]
    north = Polygon(mids + [(mids[-1][0] + 20, -600), (mids[0][0] - 20, -600)])
    south = Polygon(mids + [(mids[-1][0] + 20, -800), (mids[0][0] - 20, -800)])
    big = g.buffer(2.7, join_style='mitre'); inner_ = g.buffer(0.5, join_style='mitre')
    band(B, S, inner_, big.intersection(north), None, 0.035, 'grass')
    band(B, S, inner_, big.intersection(south), None, 0.035, 'sidewalk')
    bridges = unary_union([box(-1016.4, -709.0, -1010.2, -702.6), box(-1071.2, -711.0, -1068.4, -698.6)])
    block_area(B, g.buffer(0.35, join_style='mitre').difference(bridges), WL + 1.0)
    # the sidewalk's stone posts and iron rails along the south edge
    for k in range(n):
        na = seg_n[k]
        if na[1] > -0.6: continue
        a = ring[k]; b = ring[(k + 1) % n]; L = float(np.linalg.norm(b - a))
        if L < 1.0: continue
        d = (b - a) / L
        for t in np.arange(0.4, L - 0.2, 1.8):
            p = a + d * t + na * 0.3
            z = ztop(a + d * t, na)
            prim.box(B, p[0] - 0.12, p[1] - 0.12, z - 0.1, p[0] + 0.12, p[1] + 0.12, z + 0.85, 'curb')
        for hh in (0.45, 0.78):
            prim.obox(B, np.r_[a + na * 0.3, ztop(a, na) + hh], np.r_[b + na * 0.3, ztop(b, na) + hh], 0.035, 0.035, 'metal_dark', tag='detail')
    # ---- the bridge to 南大門: steps up from the sidewalk, a flat stone deck over the culvert, the forecourt
    zf = nandaimon_floor
    zs = float(S.ground(-1013.3, -710.0)) + 0.02
    xa, xb = -1015.9, -1010.7
    deck = zf - 0.12
    slab(B, xa, -705.6, xb, -703.0, deck - 0.45, deck, 'stone')
    walk_rect(B, xa, -705.6, xb, -703.0, deck)
    arch.stairs(B, (-1013.3, -708.4), (-1013.3, -705.6), zs, deck, xb - xa, 'stone', riser=0.17, walk=True)
    for x in (xa - 0.2, xb + 0.2):
        prim.obox(B, (x, -708.4, zs + 0.15), (x, -703.0, deck + 0.3), 0.38, 0.4, 'curb')
        block_line(B, [(x, -708.4), (x, -703.0)], zs, 0.5)
    # the gate's forecourt over the moat bank (the 南大門 stands on it), down to the courtyard on the north
    slab(B, -1029.0, -703.4, -997.0, -700.0, zf - 2.3, zf, 'stone', faces='xXyZ')
    walk_rect(B, -1029.0, -703.4, -997.0, -700.0, zf)
    zin = float(S.ground(-1013.3, -684.5))
    arch.stairs(B, (-1013.3, -684.0), (-1013.3, -687.2), zin, zf, 8.0, 'stone', riser=0.15, walk=True)
    # ---- the small bridge at the south-west gate
    zb0 = float(S.ground(-1069.8, -696.5)); zb1 = float(S.ground(-1069.8, -711.6))
    pts = [(-1071.0, -710.2), (-1068.6, -710.2), (-1068.6, -698.9), (-1071.0, -698.9)]
    P = np.array([(-1071.0, -710.2, zb1), (-1068.6, -710.2, zb1), (-1068.6, -698.9, zb0), (-1071.0, -698.9, zb0)])
    B.add(P, [[0, 1, 2], [0, 2, 3]], 'stone')
    B.add(P - [0, 0, 0.4], [[0, 2, 1], [0, 3, 2]], 'stone')
    for x in (-1071.0, -1068.6):
        quad(B, (x, -710.2, zb1 - 0.4), (x, -698.9, zb0 - 0.4), (x, -698.9, zb0), (x, -710.2, zb1), 'stone', both=True)
        prim.obox(B, (x, -710.2, zb1 + 0.25), (x, -698.9, zb0 + 0.25), 0.22, 0.5, 'curb')
        block_line(B, [(x, -710.2), (x, -698.9)], zb0, 0.45)
    B.add(P + [0, 0, 0.0], [[0, 1, 2], [0, 2, 3]], 'stone', tag='walk')
    S.exclude.append([list(map(float, c)) for c in g.buffer(3.0, join_style='mitre').exterior.coords])
    stats['moat_tris'] = B.ntri() - n0
    stats['moat'] = dict(water=WL, length=round(g.length / 2, 1), area=round(g.area))

# ------------------------------------------------------------------ ponds
def block_area(B, g, z):
    """blockers over an area (polygons with holes allowed)"""
    import mapbox_earcut as earcut
    for p in rings_of(g):
        rings = [np.array(p.exterior.coords[:-1])] + [np.array(r.coords[:-1]) for r in p.interiors]
        V = np.concatenate(rings); ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
        I = earcut.triangulate_float64(V, ends).reshape(-1, 3)
        if len(I): B.add(np.c_[V, np.full(len(V), z)], I, 'stone', tag='block')

def pond(B, S, g, drop=0.5, rocks=True, seed=1, surf='moss', stone_edge=False, rng=None, keep=None):
    """a garden pond: water `drop` below its rim, an earth bank (moss) sloping into the water, rocks along the rim (or
    a stone revetment for the 宝蔵 moat), the generic terrain cut out under it, a blocker over the water"""
    rng = rng or np.random.default_rng(seed)
    g = orient(g, 1.0)
    rim = [float(S.ground(*c)) for c in np.array(g.buffer(1.8).exterior.segmentize(3.0).coords)]
    WL = float(np.median(rim)) - drop
    prim.polygon(B, np.array(g.exterior.coords[:-1]), WL, 'water', holes=[np.array(r.coords[:-1]) for r in g.interiors])
    gc = g.buffer(0.35)
    for pc in rings_of(gc):
        if pc.interiors: S.cut.append([[list(map(float, c)) for c in pc.exterior.coords]] + [[list(map(float, c)) for c in r.coords] for r in pc.interiors])
        else: S.cut.append([list(map(float, c)) for c in pc.exterior.coords])
    if stone_edge:
        for ring in [np.array(g.exterior.coords)] + [np.array(r.coords) for r in g.interiors]:
            for a, b in zip(ring[:-1], ring[1:]):
                L = float(np.linalg.norm(b - a))
                if L < 0.05: continue
                d = (b - a) / L; nout = np.array([d[1], -d[0]])
                # for the holes (islands) the CCW orientation of the polygon makes their rings CW: the normal still points to land
                za = float(S.ground(*(a + nout * 1.5))) + 0.04; zb = float(S.ground(*(b + nout * 1.5))) + 0.04
                P = np.array([np.r_[a - nout * 0.25, WL - 0.6], np.r_[b - nout * 0.25, WL - 0.6], np.r_[b, zb], np.r_[a, za]])
                B.add(P, [[0, 2, 1], [0, 3, 2]], 'stone')
                P = np.array([np.r_[a, za], np.r_[b, zb], np.r_[b + nout * 0.4, zb], np.r_[a + nout * 0.4, za]])
                B.add(P, [[0, 2, 1], [0, 3, 2]], 'curb')
        inner = g.buffer(0.4, join_style='mitre')
        band(B, S, inner, g.buffer(2.6, join_style='mitre'), None, 0.035, surf)
    else:
        z_in = lambda x, y: WL - 0.12
        band(B, S, g, g.buffer(2.6), z_in, 0.035, surf, seg=1.0)
        if rocks:
            # 護岸石: clusters of stones of mixed sizes with stretches of bare (moss) bank between them, a few big
            # upright stones (景石) at the turns of the shore, flat stepping stones here and there
            ring = g.exterior
            L = ring.length; t = float(rng.uniform(0, 2))
            pts = np.array(ring.coords)
            while t < L:
                p = ring.interpolate(t)
                q = ring.interpolate(min(L, t + 0.5))
                d = np.array([q.x - p.x, q.y - p.y]); dl = np.linalg.norm(d)
                nout = np.array([d[1], -d[0]]) / max(dl, 1e-9)
                # how sharply the shore turns here (bigger stones at the turns)
                a = ring.interpolate(max(0, t - 2.5)); b = ring.interpolate(min(L, t + 2.5))
                turn = 1.0 - np.hypot(b.x - a.x, b.y - a.y) / 5.0
                ncl = int(rng.integers(1, 4))
                for k in range(ncl):
                    big = rng.random() < 0.08 + 1.2 * max(0.0, turn)
                    size = float(rng.uniform(1.0, 1.7)) if big else float(rng.uniform(0.3, 0.75))
                    off = float(rng.normal(0.0, 0.25))
                    c = np.array([p.x, p.y]) + nout * (size * 0.2 + off) + d / max(dl, 1e-9) * k * 0.7
                    rock(B, (c[0], c[1], WL + size * (0.32 if big else 0.16)), size, int(rng.integers(1 << 30)), 'stone', flat=0.85 if big else 0.5)
                t += float(rng.uniform(1.8, 5.5)) if rng.random() < 0.55 else float(rng.uniform(0.9, 1.8))
    gb = g.buffer(0.25)
    if keep is not None: gb = gb.difference(keep)          # bridges stay walkable
    block_area(B, gb, WL + 0.5)
    return WL

def ponds(B, S, stats):
    n0 = B.ntri()
    rng = np.random.default_rng(7)
    hyo = Polygon(outer(water(S, 187657270)['poly'])).buffer(0)
    small = Polygon(outer(water(S, 187657261)['poly'])).buffer(0)
    stream = LineString([(-948.6, -552.6), (-946.8, -556.5), (-945.7, -560.6)]).buffer(1.1)
    g = unary_union([hyo, small, stream]).buffer(0.2).buffer(-0.2)
    WL = None
    keep = LineString([(-944.0, -555.6), (-949.6, -557.9)]).buffer(0.7, cap_style='flat')
    for p in rings_of(g):
        WL = pond(B, S, p, drop=0.55, rng=rng, keep=keep)
    # the stone slab bridge over the stream (OSM 360114362)
    a = np.array([-944.4, -555.8]); b = np.array([-949.2, -557.7]); d = (b - a) / np.linalg.norm(b - a); nn = np.array([-d[1], d[0]])
    za = float(S.ground(*a)) + 0.12; zb = float(S.ground(*b)) + 0.12
    P = np.array([np.r_[a - nn * 0.7, za], np.r_[b - nn * 0.7, zb], np.r_[b + nn * 0.7, zb], np.r_[a + nn * 0.7, za]])
    B.add(P, [[0, 1, 2], [0, 2, 3]], 'stone'); B.add(P - [0, 0, 0.3], [[0, 2, 1], [0, 3, 2]], 'stone')
    for s_ in (-1, 1):
        quad(B, P[0] if s_ < 0 else P[3], P[1] if s_ < 0 else P[2], (P[1] if s_ < 0 else P[2]) - [0, 0, 0.3], (P[0] if s_ < 0 else P[3]) - [0, 0, 0.3], 'stone', both=True)
    B.add(P + [0, 0, 0.01], [[0, 1, 2], [0, 2, 3]], 'stone', tag='walk')
    # the 宝蔵 moat (a ring round the island) with a stone revetment, the bridge on the west
    w = water(S, -2526311)
    rings = w['poly'][0]
    hg = Polygon(rings[0], rings[1:]).buffer(0)
    WL2 = pond(B, S, hg, drop=0.85, rocks=False, stone_edge=True, surf='grass', rng=rng, keep=box(-945.6, -474.0, -935.2, -472.2))
    zb0 = float(S.ground(-946.0, -473.1)) + 0.1; zb1 = float(S.ground(-934.5, -473.2)) + 0.1
    P = np.array([(-945.2, -474.2, zb0), (-935.6, -474.2, zb1), (-935.6, -472.0, zb1), (-945.2, -472.0, zb0)])
    B.add(P, [[0, 1, 2], [0, 2, 3]], 'wood_natural'); B.add(P - [0, 0, 0.25], [[0, 2, 1], [0, 3, 2]], WOOD)
    for y in (-474.2, -472.0):
        for x in np.linspace(-945.0, -935.8, 5):
            z = zb0 + (zb1 - zb0) * (x + 945.2) / 9.6
            prim.box(B, x - 0.08, y - 0.08, WL2 - 0.4, x + 0.08, y + 0.08, z + 0.85, WOOD, tag='detail')
        prim.obox(B, (-945.2, y, zb0 + 0.85), (-935.6, y, zb1 + 0.85), 0.1, 0.1, WOOD, tag='detail')
        block_line(B, [(-945.2, y), (-935.6, y)], zb0, 0.4)
    B.add(P + [0, 0, 0.01], [[0, 1, 2], [0, 2, 3]], 'stone', tag='walk')
    S.exclude.append([list(map(float, c)) for c in Polygon(rings[0]).buffer(1.0).exterior.coords])
    stats['ponds_tris'] = B.ntri() - n0
    stats['ponds'] = dict(hyotan_water=round(WL, 2), hozo_water=round(WL2, 2))

# ------------------------------------------------------------------ ground surfaces, paths
PRECINCT = [(-887.0, -693.2), (-1138.6, -694.0), (-1140.6, -418.0), (-888.0, -420.0)]
GARDEN = [(-985.0, -506.0), (-944.5, -504.4), (-888.8, -504.2), (-888.6, -628.0), (-940.0, -628.0), (-985.0, -628.0)]

def paint(B, S, stats):
    S.paint.append({'poly': [list(p) for p in PRECINCT], 'surf': 'gravel'})
    S.paint.append({'poly': [list(p) for p in GARDEN], 'surf': 'moss'})
    # the lawn of the moat bank (between the 大垣 and the moat) and of the strip outside the east wall
    S.paint.append({'poly': [[-887.0, -693.6], [-1139.0, -694.6], [-1139.5, -700.0], [-887.0, -699.0]], 'surf': 'grass'})
    S.paint.append({'poly': [[-887.0, -693.0], [-887.6, -421.0], [-881.0, -421.0], [-881.2, -693.0]], 'surf': 'grass'})
    # the 灌頂院 garden: moss with gravel round the hall; 小子房's garden: moss
    S.paint.append({'poly': [[-1137.0, -693.0], [-1077.0, -693.0], [-1077.0, -630.5], [-1137.0, -630.5]], 'surf': 'moss'})
    S.paint.append({'poly': [[-1124.0, -684.0], [-1090.0, -684.0], [-1090.0, -647.0], [-1124.0, -647.0]], 'surf': 'gravel'})
    S.paint.append({'poly': [[-1138.5, -612.0], [-1122.5, -612.0], [-1122.5, -575.0], [-1138.5, -575.0]], 'surf': 'moss'})
    # paths: the garden walks (OSM footways) as packed gravel over the moss, the stone paving of 西院 and of the gates
    for wid in (187658652, 196174800, 187658651, 187658648, 187658659, 196174802, 365615726, 365615728, 519351118, 519351120, 1551357040, 365615730):
        for w in S.osm['ways']:
            if w['id'] != wid: continue
            for l in w['line']:
                if len(l) < 2: continue
                gq = LineString(l).buffer(1.2, cap_style='round')
                S.paint.append({'poly': [list(c) for c in gq.exterior.coords], 'surf': 'gravel'})
    S.paint.append({'poly': [[-1112.0, -446.0], [-1072.0, -446.0], [-1072.0, -438.0], [-1112.0, -438.0]], 'surf': 'stone_slab'})
    S.paint.append({'poly': [[-1082.0, -478.0], [-1073.5, -478.0], [-1073.5, -438.0], [-1082.0, -438.0]], 'surf': 'stone_slab'})
    for (cx, cy, hu, hv) in ((-888.6, -435.6, 9.0, 3.0), (-1014.6, -417.0, 3.0, 9.0), (-1013.3, -688.0, 4.0, 5.0)):
        S.paint.append({'poly': [[cx - hu, cy - hv], [cx + hu, cy - hv], [cx + hu, cy + hv], [cx - hu, cy + hv]], 'surf': 'stone_slab'})
    # the main axis: stone paving from 南大門 to the 金堂 steps
    S.paint.append({'poly': [[-1016.0, -686.0], [-1010.6, -686.0], [-1010.6, -619.5], [-1016.0, -619.5]], 'surf': 'stone_slab'})
    # the pagoda's surroundings: gravel
    S.paint.append({'poly': [[-940.0, -677.0], [-900.0, -677.0], [-900.0, -637.0], [-940.0, -637.0]], 'surf': 'gravel'})
    # the precinct exclusion for the garden (the generic hedges, ropes, lamps and huts there are replaced by the model)
    S.exclude.append([list(p) for p in GARDEN])

# ------------------------------------------------------------------ garden furniture: lanterns, fences, benches
def lanterns(B, S, stats):
    n0 = B.ntri()
    pts = [  # stone lanterns (lit), garden and courts; the OSM 灯籠
        (-1020.8, -443.7, 2.6), (-1020.6, -431.9, 2.6), (-1083.1, -419.7, 2.4), (-998.6, -667.1, 2.2), (-998.8, -672.7, 2.2),
        (-944.0, -566.5, 2.3), (-929.0, -556.0, 2.0), (-952.5, -588.0, 2.4), (-918.6, -598.5, 2.0), (-931.0, -620.5, 2.3), (-958.5, -612.0, 2.0),
        (-962.0, -545.0, 2.2), (-938.0, -534.0, 2.0), (-905.0, -560.0, 2.2), (-972.0, -600.0, 2.0),
        (-937.5, -640.5, 2.4), (-902.5, -640.5, 2.4), (-937.5, -673.5, 2.4), (-902.5, -673.5, 2.4),
        (-1048.0, -470.0, 2.4), (-980.0, -470.0, 2.4), (-1120.0, -640.0, 2.2), (-1084.0, -687.0, 2.2),
    ]
    wet = unary_union([Polygon(outer(water(S, i)['poly'])).buffer(1.4) for i in (187657270, 187657261, 269856746, 269856747, 269856748)])
    for (x, y, h) in pts:
        if wet.contains(Point(x, y)): continue
        z = float(S.ground(x, y))
        stone_lantern(B, x, y, z - 0.05, h)
        block_rect(B, x - 0.45, y - 0.45, x + 0.45, y + 0.45, z)
    # the 拝観 fences: low bamboo / wood fences along the garden paths (OSM split rails) are left to the generic props outside
    stats['lanterns_tris'] = B.ntri() - n0
    stats['lanterns'] = len(pts)

# ------------------------------------------------------------------ trees
def trees(B, S, stats):
    rng = np.random.default_rng(11)
    T = []
    def add(sp, x, y, sc=1.0):
        T.append((sp, x, y, sc))
    # OSM trees: the rows along the moat bank (pines) and the street (ginkgo on 九条通), the named ones
    for t in S.osm['trees']:
        x, y = t['xy']; nm = t['tags'].get('name', '')
        if 'ケヤキ' in nm: add('keyaki', x, y, 1.5)
        elif '不二桜' in nm: add('sakura', x, y, 1.3)
        elif '柳' in nm: add('yanagi', x, y, 1.1)
        elif -700.0 < y < -694.0: add('matsu', x, y, float(rng.uniform(0.85, 1.15)))
        elif y < -704.0: add('ichou', x, y, float(rng.uniform(0.9, 1.1)))
        else: add('kashi', x, y, 1.2)
    # the pond garden: maples, pines by the water, cherries, clipped azaleas
    hyo = Polygon(outer(water(S, 187657270)['poly']))
    ring = hyo.buffer(4.0).exterior
    for k, t in enumerate(np.arange(0, ring.length, 7.5)):
        p = ring.interpolate(t)
        add('matsu' if k % 3 == 0 else 'momiji', p.x + rng.normal(0, 0.8), p.y + rng.normal(0, 0.8), float(rng.uniform(0.8, 1.15)))
    ring = hyo.buffer(1.6).exterior
    for t in np.arange(0, ring.length, 3.2):
        p = ring.interpolate(t)
        if rng.random() < 0.55: add('tsutsuji', p.x, p.y, float(rng.uniform(0.6, 1.0)))
    garden = Polygon(GARDEN).difference(hyo.buffer(6.0)).difference(box(-940, -680, -900, -634))
    for p in poisson(garden, 9.5, rng):
        sp = rng.choice(['momiji', 'momiji', 'sakura', 'matsu', 'kashi', 'momiji'])
        add(str(sp), p[0], p[1], float(rng.uniform(0.8, 1.2)))
    for p in poisson(garden, 6.0, rng):
        if rng.random() < 0.35: add('tsutsuji', p[0], p[1], float(rng.uniform(0.6, 1.1)))
    # round the pagoda: pines and maples outside its fence
    for ang in np.linspace(0, 2 * math.pi, 14, endpoint=False):
        r = 17.5 + rng.uniform(0, 3)
        add('momiji' if rng.random() < 0.6 else 'sakura', -920.05 + r * math.cos(ang), -657.05 + r * math.sin(ang), float(rng.uniform(0.85, 1.2)))
    # the camphor trees of the courts (楠: 'kashi' is the closest broadleaf evergreen of the viewer's species)
    for (x, y, sc) in ((-1038.0, -632.0, 1.6), (-989.0, -632.0, 1.6), (-1041.0, -655.0, 1.4), (-986.0, -652.0, 1.5), (-1045.0, -585.0, 1.4),
                       (-982.0, -583.0, 1.4), (-1046.0, -530.0, 1.5), (-981.0, -532.0, 1.4), (-1048.0, -450.0, 1.5), (-975.0, -440.0, 1.4)):
        add('kashi', x, y, sc)
    # 西院, 灌頂院, 小子房: pines, maples
    for (x0, y0, x1, y1, n, sps) in ((-1138, -690, -1080, -632, 14, ['matsu', 'momiji', 'kashi']), (-1137, -611, -1124, -576, 6, ['matsu', 'momiji']),
                                      (-1138, -494, -1112, -420, 8, ['matsu', 'kashi', 'momiji']), (-1072, -500, -1046, -420, 8, ['kashi', 'ichou', 'sakura']),
                                      (-985, -500, -960, -425, 7, ['sakura', 'momiji', 'kashi'])):
        for k in range(n):
            x = rng.uniform(x0, x1); y = rng.uniform(y0, y1)
            add(str(rng.choice(sps)), x, y, float(rng.uniform(0.85, 1.2)))
    # the 宝蔵 island: maples and pines; the lotus pond round it is open water
    for (x, y) in ((-930, -470), (-925, -490), (-921, -462), (-933, -482), (-905, -462), (-903, -492)):
        add('momiji' if rng.random() < 0.6 else 'matsu', x, y, float(rng.uniform(0.85, 1.1)))
    # keep trees off buildings, water, platforms and paths' middle
    blocked = unary_union([box(-1036, -620, -991, -587), box(-1035, -571, -992, -548), box(-1033, -484, -995, -456), box(-1121, -681, -1093, -651),
                           box(-1122, -601, -1099, -570), box(-1109, -476, -1082, -444), box(-918, -484, -904, -471), box(-1026, -704, -1000, -683),
                           box(-930, -667, -910, -647), hyo.buffer(0.8), box(-1018, -700, -1008, -560)])
    W = [Polygon(outer(water(S, i)['poly'])) for i in (269856746, 269856747, 269856748, 187657261)]
    blocked = unary_union([blocked] + [w.buffer(0.5) for w in W])
    n = 0
    for (sp, x, y, sc) in T:
        if blocked.contains(Point(x, y)) and sp != 'tsutsuji': continue
        if any(w.contains(Point(x, y)) for w in W): continue
        if hyo.contains(Point(x, y)): continue
        B.tree(sp, float(x), float(y), float(S.ground(x, y)), sc, float(rng.uniform(0, 2 * math.pi)))
        n += 1
    stats['trees'] = n

def poisson(poly, r, rng, k=20):
    x0, y0, x1, y1 = poly.bounds
    pts = []
    for _ in range(int(poly.area / (r * r) * 3) + 10):
        for _ in range(k):
            p = (rng.uniform(x0, x1), rng.uniform(y0, y1))
            if not poly.contains(Point(p)): continue
            if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > r * r for q in pts):
                pts.append(p); break
    return pts

# ------------------------------------------------------------------ the garden's small buildings (rest house, toilets, sheds)
HUTS = [  # (cx, cy, length, width, yaw deg, eave h, ridge h, open): PLATEAU footprints / heights inside the garden exclusion
    (-898.6, -549.2, 12.6, 8.0, 90.0, 2.9, 4.0, False), (-912.8, -546.3, 9.5, 6.3, 0.0, 2.5, 3.0, False), (-946.3, -599.0, 7.6, 5.0, 90.0, 2.7, 4.2, True),
    (-900.9, -535.4, 5.0, 4.0, 0.0, 1.8, 2.6, False), (-895.8, -524.1, 7.5, 6.0, 0.0, 3.2, 5.1, False), (-916.7, -516.3, 10.0, 7.1, 0.0, 3.4, 5.4, False),
    (-908.1, -513.2, 3.6, 2.8, 0.0, 2.2, 2.8, False),
]

def huts(B, S, stats):
    from sites.toji_kit import troof
    n0 = B.ntri()
    for (cx, cy, L, D, yd, he, hr, opn) in HUTS:
        zg = float(S.ground(cx, cy)); yaw = math.radians(yd)
        with Frame(B, cx, cy, 0.0, yaw):
            Lw, Dw = L - 1.4, D - 1.4
            slab(B, -Lw / 2, -Dw / 2, Lw / 2, Dw / 2, zg - 0.2, zg + 0.15, 'stone', faces='xXyYZ')
            for (a, b, nn) in (((-Lw / 2, -Dw / 2), (Lw / 2, -Dw / 2), (0, -1)), ((Lw / 2, -Dw / 2), (Lw / 2, Dw / 2), (1, 0)), ((Lw / 2, Dw / 2), (-Lw / 2, Dw / 2), (0, 1)),
                              ((-Lw / 2, Dw / 2), (-Lw / 2, -Dw / 2), (-1, 0))):
                if not opn: quad(B, (*a, zg + 0.15), (*b, zg + 0.15), (*b, zg + he - 0.2), (*a, zg + he - 0.2), 'temple_wall', both=False, c0=PLASTER)
                for t in (np.linspace(0, 1, max(2, int(np.hypot(b[0] - a[0], b[1] - a[1]) / 1.8)) + 1) if not opn else (0.0,)):
                    p = np.array(a) + (np.array(b) - np.array(a)) * t
                    prim.box(B, p[0] - 0.07, p[1] - 0.07, zg + 0.15, p[0] + 0.07, p[1] + 0.07, zg + he - 0.15, WOOD, tag='detail')
            prim.obox(B, (-Lw / 2, -Dw / 2 - 0.02, zg + he - 0.25), (Lw / 2, -Dw / 2 - 0.02, zg + he - 0.25), 0.12, 0.2, WOOD)
            pitch = (hr - he) / (Dw / 2 + 0.7)
            troof(B, Lw, Dw, zg + he, 0.7, kind='kirizuma', cover='sangawara', pitch=max(0.3, pitch), teri=1.2, sori=0.0, verge=0.5, edge=0.2, rafter=0.0,
                  rafter_mat=WOOD, rafter_end=WOOD, fascia_mat=WOOD, ends=None, ridge_h=0.3, ridge_w=0.28, tiers=1, bargeboard_mat=WOOD)
            if opn:
                for (x, y) in ((-Lw / 2, -Dw / 2), (Lw / 2, -Dw / 2), (Lw / 2, Dw / 2), (-Lw / 2, Dw / 2)):
                    prim.box(B, x - 0.1, y - 0.1, zg + 0.15, x + 0.1, y + 0.1, zg + he, WOOD)
                    block_rect(B, x - 0.3, y - 0.3, x + 0.3, y + 0.3, zg)
                walk_rect(B, -Lw / 2, -Dw / 2, Lw / 2, Dw / 2, zg + 0.15)
                slab(B, -Lw / 2 + 0.6, -0.3, Lw / 2 - 0.6, 0.3, zg + 0.15, zg + 0.55, WOOD)
            else:
                block_rect(B, -Lw / 2 - 0.2, -Dw / 2 - 0.2, Lw / 2 + 0.2, Dw / 2 + 0.2, zg)
    stats['huts_tris'] = B.ntri() - n0
