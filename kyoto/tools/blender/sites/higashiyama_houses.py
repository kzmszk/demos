"""東山 town houses: the PLATEAU buildings fronting the lanes are replaced by machiya.build (Gion's town-house
builder) with 東山 shop fronts (higashiyama_front), sitting level on stone plinths where the lane slopes (the eave lines
step down the hill), door steps, 石塀小路's walled houses (石垣 + plaster wall + tiled coping + gate) and the
generic buildings they replace excluded."""
import math, zlib
from contextlib import contextmanager
import numpy as np
import shapely
import shapely.ops
from shapely.geometry import Polygon, LineString, Point, box as sbox
from jk import prim
from jk.core import Frame
import sites.machiya as M
import sites.higashiyama_front as HF

@contextmanager
def patched_front():
    """machiya.build draws the street front with machiya._front; for the 東山 shop fronts (style['hy']) use ours"""
    orig = M._front
    def f(B, s, rng, W, z_wp, o, z_edge, wall_t, wmat, wtint, seed, info):
        if s.get('hy') is not None: return HF.front(B, s, rng, W, z_wp, o, z_edge, wall_t, wmat, wtint, seed, info)
        return orig(B, s, rng, W, z_wp, o, z_edge, wall_t, wmat, wtint, seed, info)
    M._front = f
    try: yield
    finally: M._front = orig

# ------------------------------------------------------------------ helpers (after gion_streets)
def footprint(b):
    P = Polygon(b['poly'][0][0])
    if not P.is_valid: P = P.buffer(0)
    if P.geom_type != 'Polygon': P = max(P.geoms, key=lambda q: q.area)
    return P

def front_of(P, L):
    pP, pL = shapely.ops.nearest_points(P, L)
    t = L.project(pL)
    p = L.interpolate(t); q = L.interpolate(min(L.length, t + 1.0)); r = L.interpolate(max(0.0, t - 1.0))
    d = np.array([q.x - r.x, q.y - r.y]); d /= max(np.linalg.norm(d), 1e-9)
    e0 = (p.x - d[0] * 3, p.y - d[1] * 3); e1 = (p.x + d[0] * 3, p.y + d[1] * 3)
    return (e0, e1), t

def lot_slices(P, edge, target=6.0, rng=None):
    O, U, N, yaw, Lc = M._frame(np.asarray(P.exterior.coords), edge)
    W = float(Lc[:, 0][Lc[:, 1] < 0.9].max())
    k = int(round(W / target))
    if W < 9.0 or k < 2: return [np.asarray(P.exterior.coords)[:-1]]
    rng = rng or np.random.default_rng(0)
    cuts = np.linspace(0, W, k + 1)
    cuts[1:-1] += rng.uniform(-0.6, 0.6, k - 1)
    Pl = Polygon(Lc)
    if not Pl.is_valid: Pl = Pl.buffer(0)
    out = []
    for i in range(k):
        a = cuts[i] if i > 0 else -100.0; b = cuts[i + 1] if i < k - 1 else 100.0
        g = Pl.intersection(sbox(a, -100, b, 300))
        if g.is_empty: continue
        if g.geom_type != 'Polygon': g = max(g.geoms, key=lambda q: q.area)
        if g.area < 8: continue
        loc = np.asarray(g.exterior.coords)[:-1]
        out.append(O + np.outer(loc[:, 0], U) + np.outer(loc[:, 1], N))
    return out

EAVE_SETBACK = 0.85      # PLATEAU LOD2 footprints are roof outlines: the front wall stands this far behind the edge

def setback_ring(ring, edge, sb):
    """cut the front strip (v < sb in the house frame) off a lot: (ring, edge) of the wall line; None if too shallow"""
    O, U, N, yaw, Lc = M._frame(ring, edge)
    D = float(Lc[:, 1].max())
    if D - sb < 3.5: sb = max(0.0, D - 3.5)
    if sb <= 0.01: return ring, edge
    Pl = Polygon(Lc)
    if not Pl.is_valid: Pl = Pl.buffer(0)
    g = Pl.intersection(sbox(-500, sb, 500, 500))
    if g.is_empty: return ring, edge
    if g.geom_type != 'Polygon': g = max(g.geoms, key=lambda q: q.area)
    loc = np.asarray(g.exterior.coords)[:-1]
    ring2 = O + np.outer(loc[:, 0], U) + np.outer(loc[:, 1], N)
    e2 = (tuple(np.asarray(edge[0], float) + N * sb), tuple(np.asarray(edge[1], float) + N * sb))
    return ring2, e2

def beyond_end(P, L):
    """True if the footprint lies past either end of the lane (around a corner, not along it)"""
    pP, pL = shapely.ops.nearest_points(P, L)
    t = L.project(pL)
    if 0.4 < t < L.length - 0.4: return False
    a = np.array(L.interpolate(t).coords[0])
    b = np.array(L.interpolate(min(L.length, t + 1.0) if t < 1 else max(0.0, t - 1.0)).coords[0])
    out = a - b; out /= max(np.linalg.norm(out), 1e-9)
    c = np.array(P.centroid.coords[0])
    return float((c - a) @ out) > 1.0

# ------------------------------------------------------------------ street character
WALLS_HY = [(205, 168, 98), (214, 186, 128), (222, 206, 172), (232, 224, 204), (196, 156, 92), (226, 214, 186), (184, 150, 104), (236, 232, 222)]
STREET = {
    # shop share, tea shops (benches), kinds (upper floor) weights, awnings, lanterns, goods
    'sannen':    dict(shop=0.88, tea=0.18, kinds=dict(tsushi=0.55, ochaya=0.3, shop=0.15), awning=0.35, lanterns=0.35, sign=0.4, pots=0.4),
    'ninen':     dict(shop=0.85, tea=0.15, kinds=dict(tsushi=0.4, ochaya=0.45, shop=0.15), awning=0.3, lanterns=0.3, sign=0.4, pots=0.5),
    'kiyomizu':  dict(shop=0.95, tea=0.1, kinds=dict(tsushi=0.35, ochaya=0.25, shop=0.4), awning=0.55, lanterns=0.3, sign=0.6, pots=0.2, table=0.3),
    'yasaka':    dict(shop=0.35, tea=0.06, kinds=dict(tsushi=0.45, ochaya=0.45, shop=0.1), awning=0.12, lanterns=0.2, sign=0.25, pots=0.6),
    'yasaka_up': dict(shop=0.65, tea=0.12, kinds=dict(tsushi=0.35, ochaya=0.5, shop=0.15), awning=0.25, lanterns=0.3, sign=0.35, pots=0.5),
    'ichinen':   dict(shop=0.6, tea=0.12, kinds=dict(tsushi=0.35, ochaya=0.55, shop=0.1), awning=0.2, lanterns=0.3, sign=0.3, pots=0.5),
    'nene':      dict(shop=0.7, tea=0.15, kinds=dict(tsushi=0.2, ochaya=0.6, shop=0.2), awning=0.2, lanterns=0.4, sign=0.4, pots=0.5),
    'ishin':     dict(shop=0.35, tea=0.08, kinds=dict(tsushi=0.3, ochaya=0.6, shop=0.1), awning=0.15, lanterns=0.2, sign=0.3, pots=0.5),
    'chawan':    dict(shop=0.9, tea=0.05, kinds=dict(tsushi=0.3, ochaya=0.3, shop=0.4), awning=0.45, lanterns=0.2, sign=0.5, pots=0.3, table=0.5, goods='bowls'),
    'gojo':      dict(shop=0.9, tea=0.05, kinds=dict(tsushi=0.3, ochaya=0.3, shop=0.4), awning=0.45, lanterns=0.2, sign=0.5, pots=0.3, table=0.5, goods='bowls'),
    'ishibe':    dict(shop=0.0, tea=0.0, kinds=dict(ochaya=0.7, tsushi=0.3), walled=0.65),
    'ishibe_n':  dict(shop=0.0, tea=0.0, kinds=dict(ochaya=0.7, tsushi=0.3), walled=0.65),
    'ishibe_w':  dict(shop=0.0, tea=0.0, kinds=dict(ochaya=0.7, tsushi=0.3), walled=0.65),
}

def pick(rng, wd):
    ks = list(wd.keys()); ps = np.array([wd[k] for k in ks], float); ps /= ps.sum()
    return ks[int(rng.choice(len(ks), p=ps))]

def style_for(lane_key, hh, rng, z_drop):
    st = STREET.get(lane_key, STREET['yasaka'])
    if hh < 5.4: kind = 'hiraya'
    elif hh > 10.6: kind = 'sangai'
    else:
        kind = pick(rng, st['kinds'])
        if kind == 'tsushi' and hh > 8.4: kind = 'ochaya'
    s = dict(kind=kind, wall=WALLS_HY[int(rng.integers(len(WALLS_HY)))])
    s['party'] = 'wall_board' if rng.random() < 0.15 else 'wall_plaster'
    s['party_tint'] = (226, 220, 206) if rng.random() < 0.5 else s['wall']
    if rng.random() < 0.12: s['wood'] = 'bengara'
    shop = rng.random() < st['shop']
    hy = {}
    if shop:
        hy['shop'] = ['open', 'glass', 'mixed'][int(rng.choice(3, p=[0.45, 0.2, 0.35]))]
        hy['goods'] = st.get('goods', 'boxes') if rng.random() < 0.7 else 'boxes'
        if rng.random() < st['awning']: hy['awning'] = HF.AWNING[int(rng.integers(len(HF.AWNING)))]; hy['awning_part'] = rng.random() < 0.4
        if rng.random() < st['lanterns']: hy['lanterns'] = int(rng.integers(1, 5)); hy['red_lanterns'] = rng.random() < 0.6
        if rng.random() < st['tea']: hy['bench'] = True; hy['parasol'] = rng.random() < 0.5
        if rng.random() < st['sign']: hy['sign'] = True
        if rng.random() < st.get('table', 0.0): hy['table'] = True
        hy['kanban'] = rng.random() < 0.55
        hy['hanging_sign'] = rng.random() < 0.35
        s.update(inuyarai=False, komayose=False, degoshi=False, chochin=False)
        s['noren'] = M.NOREN[int(rng.integers(len(M.NOREN)))] if rng.random() < 0.8 else False
    else:
        if rng.random() < st.get('lanterns', 0.3) * 0.6: s['chochin'] = True
    if rng.random() < st.get('pots', 0.3): hy['pots'] = int(rng.integers(1, 4))
    s['hy'] = hy
    return s

# ------------------------------------------------------------------ plinth, door steps
def plinth(B, info, z0, lz):
    """the stone base under the front where the lane falls along the frontage; side returns; door steps"""
    ox, oy, yaw = info['frame']; W = info['W']
    c, s_ = math.cos(yaw), math.sin(yaw)
    def world(u, v): return (ox + c * u - s_ * v, oy + s_ * u + c * v)
    us = np.linspace(0.0, W, max(2, int(W / 0.8) + 1))
    zb = np.array([lz(*world(u, -0.45)) for u in us]) - z0
    out = 0
    with Frame(B, ox, oy, z0, yaw):
        if zb.min() < -0.27:
            Q = []; UV = []
            for i in range(len(us) - 1):
                a, b = us[i], us[i + 1]; za, zbb = min(zb[i] - 0.12, -0.25), min(zb[i + 1] - 0.12, -0.25)
                Q.append([(a, -0.22, za), (b, -0.22, zbb), (b, -0.22, -0.24), (a, -0.22, -0.24)]); UV.append([(a, za), (b, zbb), (b, -0.24), (a, -0.24)])
            M.quads(B, Q, 'stone', UV=UV)
            for (u, zz, f) in ((0.0, zb[0], -1), (W, zb[-1], 1)):
                if zz < -0.27:
                    M.side_rect(B, -0.22, 0.02, zz - 0.12, -0.24, u, 'stone', facing=f)
            # a coping line (笠石) on top of the base
            M.bars(B, [(0.0, -0.24, -0.26)], [(W, -0.24, -0.26)], (0, 0, 1), 0.06, 0.05, 'curb', tag='detail')
            out = float(-zb.min())
        if 'door' in info:
            da, db = info['door']
            zg = lz(*world((da + db) / 2, -0.7)) - z0
            if zg < -0.22:
                n = max(1, int(round(-zg / 0.17)) - 1)
                r_ = -zg / (n + 1)
                for k in range(1, n + 1):
                    top = zg + (n - k + 1) * r_
                    M.hbox(B, da + 0.05, db - 0.05, -0.22 - 0.3 * k, -0.22 - 0.3 * (k - 1) + 0.02, zg - 0.1, top, 'stone', tag='main', faces='yZxX')
                prim.polygon(B, [(da, -0.22 - 0.3 * n), (db, -0.22 - 0.3 * n), (db, -0.1), (da, -0.1)], zg + 0.05, 'stone', tag='walk')
    return out

# ------------------------------------------------------------------ 石塀小路: stone-based walls with tiled coping, gates
def coping_wall(B, p0, p1, zfun, h=2.2, base=0.9, th=0.32, tint=(232, 226, 210), stone_mat='stone', gate=None, coping=True, tag='main'):
    """a wall along p0->p1 (world, the outer face on the right of p0->p1... both faces drawn): a 石垣 base of `base` m, a
    plastered wall above to h, a small tiled coping.  Built in sections of <= 2 m, each level at the ground of its
    lowest end (zfun).  gate=(t0, t1) leaves an opening along the run (distances from p0)."""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = float(np.linalg.norm(d))
    if L < 0.3: return
    d /= L; n = np.array([-d[1], d[0]])
    ts = [0.0, L]
    if gate: ts = sorted(set([0.0, L, max(0.0, gate[0]), min(L, gate[1])]))
    for ta, tb in zip(ts[:-1], ts[1:]):
        if gate and ta >= gate[0] - 1e-6 and tb <= gate[1] + 1e-6: continue
        k = max(1, int(math.ceil((tb - ta) / 2.0)))
        for j in range(k):
            a = p0 + d * (ta + (tb - ta) * j / k); b = p0 + d * (ta + (tb - ta) * (j + 1) / k)
            zz = min(zfun(*a), zfun(*b))
            zlow = zz - 0.3
            ls = float(np.linalg.norm(b - a))
            for side in (-1, 1):
                A = a + n * side * th / 2; Bq = b + n * side * th / 2
                I = [[0, 2, 1], [0, 3, 2]] if side > 0 else [[0, 1, 2], [0, 2, 3]]
                if base > 0:
                    B.add(np.array([np.r_[A, zlow], np.r_[Bq, zlow], np.r_[Bq, zz + base], np.r_[A, zz + base]]), I, stone_mat,
                          UV=np.array([[0, zlow], [ls, zlow], [ls, zz + base], [0, zz + base]]), tag=tag)
                B.add(np.array([np.r_[A, zz + base], np.r_[Bq, zz + base], np.r_[Bq, zz + h], np.r_[A, zz + h]]), I, 'wall_plaster',
                      UV=np.array([[0, zz + base], [ls, zz + base], [ls, zz + h], [0, zz + h]]), tag=tag, c0=(*tint, 0))
            # ends of the section (where the next is at another level)
            for e, f in ((a, -1), (b, 1)):
                P = np.array([np.r_[e - n * th / 2, zlow], np.r_[e + n * th / 2, zlow], np.r_[e + n * th / 2, zz + h], np.r_[e - n * th / 2, zz + h]])
                fn = np.cross(P[1] - P[0], P[2] - P[0])
                I = [[0, 1, 2], [0, 2, 3]] if fn @ np.r_[d * f, 0] > 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I, 'wall_plaster', tag='detail', c0=(*tint, 0))
            if coping:
                for side in (-1, 1):
                    A = a + n * side * (th / 2 + 0.2); Bq = b + n * side * (th / 2 + 0.2)
                    P = np.array([np.r_[A, zz + h - 0.06], np.r_[Bq, zz + h - 0.06], np.r_[b, zz + h + 0.24], np.r_[a, zz + h + 0.24]])
                    I = [[0, 1, 2], [0, 2, 3]] if side < 0 else [[0, 2, 1], [0, 3, 2]]
                    B.add(P, I, 'kawara', UV=np.array([[0, 0], [ls, 0], [ls, 0.45], [0, 0.45]]), tag=tag)
                prim.obox(B, np.r_[a, zz + h + 0.28], np.r_[b, zz + h + 0.28], 0.18, 0.1, 'ridge', tag=tag)
                if base > 0:
                    prim.obox(B, np.r_[a, zz + base + 0.02], np.r_[b, zz + base + 0.02], th + 0.06, 0.06, 'curb', tag='detail')
    # blocker along the whole run (open at the gate)
    if gate:
        for (ta, tb) in ((0.0, gate[0]), (gate[1], L)):
            if tb - ta > 0.2: prim.obox(B, np.r_[p0 + d * ta, zfun(*p0) + 0.5], np.r_[p0 + d * tb, zfun(*p0) + 0.5], 0.3, 0.2, 'stone', tag='block')
    else:
        prim.obox(B, np.r_[p0, zfun(*p0) + 0.5], np.r_[p1, zfun(*p1) + 0.5], 0.3, 0.2, 'stone', tag='block')

def munemon(B, c, d, zg, w=1.6, h=2.5, rng=None, noren=None, lantern=True):
    """棟門: a small roofed gate at c facing -n (d = direction along the wall): two posts, a tie beam, a little gable roof
    of tiles, a door pair (open), noren and a lantern"""
    c = np.asarray(c, float); d = np.asarray(d, float); n = np.array([-d[1], d[0]])
    ang = math.atan2(d[1], d[0])
    with Frame(B, c[0], c[1], zg, ang):
        for u in (-w / 2, w / 2):
            M.hbox(B, u - 0.08, u + 0.08, -0.08, 0.08, 0.0, h, 'wood_dark', tag='main')
        M.hbox(B, -w / 2 - 0.15, w / 2 + 0.15, -0.1, 0.1, h - 0.25, h - 0.05, 'wood_dark', tag='main')
        # gable roof along u (ridge along the wall), small
        o = 0.55; zr = h + 0.55
        for sgn in (-1, 1):
            P = np.array([(-w / 2 - 0.45, sgn * o, h - 0.05), (w / 2 + 0.45, sgn * o, h - 0.05), (w / 2 + 0.45, 0.0, zr), (-w / 2 - 0.45, 0.0, zr)])
            I = [[0, 1, 2], [0, 2, 3]] if sgn < 0 else [[0, 2, 1], [0, 3, 2]]
            B.add(P, I, 'kawara', UV=np.array([(0, 0), (w + 0.9, 0), (w + 0.9, 0.7), (0, 0.7)]), tag='main')
            Q = np.array([(-w / 2 - 0.45, sgn * o, h - 0.13), (w / 2 + 0.45, sgn * o, h - 0.13), (w / 2 + 0.45, 0.0, zr - 0.08), (-w / 2 - 0.45, 0.0, zr - 0.08)])
            B.add(Q, [t[::-1] for t in I], 'eave_wood', tag='main', c1=(0, 2, 0, 0))
        prim.obox(B, (-w / 2 - 0.5, 0, zr + 0.05), (w / 2 + 0.5, 0, zr + 0.05), 0.2, 0.16, 'ridge', tag='main')
        for u in (-w / 2 - 0.5, w / 2 + 0.5):
            M.hbox(B, u - 0.03, u + 0.03, -0.14, 0.14, zr - 0.05, zr + 0.3, 'ridge', tag='detail', c1=(0, 1, 0, 0))
        if noren is not None:
            M.noren(B, -w / 2 + 0.1, w / 2 - 0.1, h - 0.3, 0.75, -0.02, noren)
        if lantern:
            M.chochin(B, w / 2 + 0.35, -0.3, h - 0.1, r=0.14, h=0.4, lamp=True)

def walled_house(B, S, ring, edge, z0, hh, s, seed, lz, setback=1.3):
    """石塀小路: the house set back behind a stone-based plaster wall along the lane, entered by a small gate"""
    O, U, N, yaw, Lc = M._frame(ring, edge)
    W = float(Lc[:, 0][Lc[:, 1] < 0.9].max())
    D = float(Lc[:, 1].max())
    rng = np.random.default_rng(seed)
    Pl = Polygon(Lc)
    if not Pl.is_valid: Pl = Pl.buffer(0)
    inner = Pl.intersection(sbox(-100, setback, 100, 300)) if D - setback > 5.5 else Pl
    if inner.geom_type != 'Polygon': inner = max(inner.geoms, key=lambda q: q.area)
    loc = np.asarray(inner.exterior.coords)[:-1]
    ring2 = O + np.outer(loc[:, 0], U) + np.outer(loc[:, 1], N)
    sb = setback if D - setback > 5.5 else 0.0
    e2 = (tuple(np.asarray(edge[0]) + N * sb), tuple(np.asarray(edge[1]) + N * sb))
    zh = z0
    info = M.build(B, ring2, e2, zh, hh, 0, s, seed=seed)
    if sb > 0:
        # the wall on the lane front, gate somewhere along it
        p0 = O + U * 0.0 - N * 0.05; p1 = O + U * W - N * 0.05
        gw = 1.5
        g0 = rng.uniform(0.4, max(0.41, W - gw - 0.4))
        tint = WALLS_HY[int(rng.integers(len(WALLS_HY)))] if rng.random() < 0.6 else (234, 230, 218)
        base = rng.uniform(0.6, 1.2)
        coping_wall(B, p1, p0, lz, h=rng.uniform(2.0, 2.4), base=base, tint=tint, gate=(W - g0 - gw, W - g0))
        gc = O + U * (g0 + gw / 2) - N * 0.05
        munemon(B, gc, U, lz(*(gc - N * 0.5)) + 0.02, w=gw - 0.1, h=2.45, noren=M.NOREN[int(rng.integers(len(M.NOREN)))] if rng.random() < 0.6 else None)
        # the garden strip: gravel and a shrub
        if rng.random() < 0.6:
            q = O + U * rng.uniform(0.5, W - 0.5) + N * sb * 0.5
            HF.blob(B, (q[0], q[1], lz(*q) + 0.6), 1.3, rng, mat='hedge', tag='main')
    return info

def drop_front_blocks(B, npart, info):
    """remove machiya's blockers in front of the facade (the 0.55 m strip for 犬矢来 / 出格子) from the parts added since
    npart: on the narrow lanes they would close the walk"""
    ox, oy, yaw = info['frame']
    c, s_ = math.cos(yaw), math.sin(yaw)
    keep = []
    for i, p in enumerate(B.parts):
        if i < npart or p['tag'] != 'block': keep.append(p); continue
        P = p['P'].astype(float)
        v = -s_ * (P[:, 0] - ox) + c * (P[:, 1] - oy)
        if v.max() < 0.05 and v.min() > -0.6: continue
        keep.append(p)
    B.parts[:] = keep

def side_walls(B, S, built):
    """exposed side walls (no neighbour against them: corners, gaps, a lower neighbour's roof) get the timber-framed
    look of the photographs: a dark board skirt (腰板), posts every bay and a tie beam at the first floor"""
    from shapely.strtree import STRtree
    fps = []
    for b in S.plateau:
        P = Polygon(b['poly'][0][0])
        if P.is_valid and P.area > 4: fps.append(P)
    worlds = []
    for (info, z0, seed) in built:
        ox, oy, yaw = info['frame']; c, s_ = math.cos(yaw), math.sin(yaw)
        L = np.asarray(info['ring_local'])[:-1]
        Wd = np.c_[ox + c * L[:, 0] - s_ * L[:, 1], oy + s_ * L[:, 0] + c * L[:, 1]]
        worlds.append(Polygon(Wd))
    tree = STRtree(fps + worlds)
    allp = fps + worlds
    n = 0
    for hi, (info, z0, seed) in enumerate(built):
        ox, oy, yaw = info['frame']; c, s_ = math.cos(yaw), math.sin(yaw)
        L = np.asarray(info['ring_local'])
        me = worlds[hi]
        rng = np.random.default_rng(seed + 5)
        tint = (52, 40, 30) if rng.random() < 0.7 else (70, 56, 44)
        for i in range(len(L) - 1):
            a, b = L[i], L[i + 1]
            if a[1] < 0.6 and b[1] < 0.6: continue                    # the front
            ln = float(np.linalg.norm(b - a))
            if ln < 2.0: continue
            m = (a + b) / 2; d = (b - a) / ln
            out = np.array([d[1], -d[0]])                              # outward for a ccw ring
            pm = m + out * 0.6
            pw = Point(ox + c * pm[0] - s_ * pm[1], oy + s_ * pm[0] + c * pm[1])
            hit = False
            for k in tree.query(pw.buffer(0.35)):
                g = allp[k]
                if g is me or g.equals(me): continue
                if g.distance(pw) < 0.35: hit = True; break
            if hit: continue
            # the skirt and frame, in the house frame (z from the house base)
            with Frame(B, ox, oy, z0, yaw):
                ang = math.atan2(d[1], d[0])
                ga = float(S.ground(ox + c * a[0] - s_ * a[1], oy + s_ * a[0] + c * a[1])) - z0
                gb = float(S.ground(ox + c * b[0] - s_ * b[1], oy + s_ * b[0] + c * b[1])) - z0
                zt = 1.75
                o2 = out * 0.025
                A = np.r_[a + o2, min(ga, 0.0) - 0.25]; Bq = np.r_[b + o2, min(gb, 0.0) - 0.25]
                P = np.array([A, Bq, np.r_[b + o2, zt], np.r_[a + o2, zt]])
                fn = np.cross(P[1] - P[0], P[2] - P[0])
                I = [[0, 1, 2], [0, 2, 3]] if fn[:2] @ out > 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I, 'wall_board', UV=np.array([(0, A[2]), (ln, Bq[2]), (ln, zt), (0, zt)]), c0=(*tint, 0), tag='main')
                k_ = max(1, int(round(ln / 1.85)))
                ts = np.linspace(0, 1, k_ + 1)
                P0 = np.array([np.r_[a + (b - a) * t + out * 0.05, min(ga, gb, 0.0) - 0.1] for t in ts])
                P1 = np.array([np.r_[a + (b - a) * t + out * 0.05, 2.95] for t in ts])
                M.bars(B, P0, P1, (d[0], d[1], 0.0), 0.12, 0.1, 'wood_dark', tag='detail', caps=True)
                M.bars(B, [np.r_[a + out * 0.06, 2.85], np.r_[a + out * 0.045, zt]], [np.r_[b + out * 0.06, 2.85], np.r_[b + out * 0.045, zt]], (0, 0, 1), (0.2, 0.06), (0.12, 0.05), 'wood_dark', tag='detail', caps=True)
            n += 1
    return n

# ------------------------------------------------------------------ selection and build
def select(S, lanes, protect):
    rows = {k: [] for k in lanes}
    for b in S.plateau:
        if b['kind'] not in ('trad', 'house', 'mid', 'shed'): continue
        h = float(b['h'] or 0); st = int(b['st'] or 0)
        if h > 15.5 or st >= 4: continue
        P = footprint(b)
        if P.area < 10: continue
        rp = P.representative_point()
        if rp.y > 1749.0: continue
        if P.bounds[3] > 1749.5 or protect.intersection(P).area > 0.5: continue
        best = None
        for k, lane in lanes.items():
            if not lane.spec.get('houses', True): continue
            d = P.distance(lane.line)
            if d > 9.0: continue
            s = lane.line.project(rp)
            thr = 0.5 * lane.width_at(s) + (2.6 if not k.startswith('ishibe') else 2.0)
            if d > thr: continue
            if beyond_end(P, lane.line): continue
            if best is None or d < best[0]: best = (d, k)
        if best: rows[best[1]].append((b, P))
    return rows

def build(B, S, lanes, lz, protect, stats, only_lanes=None):
    rows = select(S, lanes, protect)
    lane_lines = {k: l.line for k, l in lanes.items()}
    n = 0; nfail = 0
    from shapely.ops import unary_union
    clear = unary_union([l.line.buffer(1.0 if kk.startswith('ishibe') else 1.7, cap_style='flat') for kk, l in lanes.items()])
    built = []
    with patched_front():
        for k, picks in rows.items():
            if only_lanes and k not in only_lanes: continue
            lane = lanes[k]
            rng = np.random.default_rng(zlib.crc32(k.encode()))
            for (b, P) in picks:
                edge, t = front_of(P, lane.line)
                rings = lot_slices(P, edge, rng=rng)
                for ring0 in rings:
                    seed = int(rng.integers(1 << 30))
                    walled = bool(STREET.get(k, {}).get('walled')) and rng.random() < STREET[k]['walled']
                    if walled:
                        # only lots whose front runs along the lane, wide and deep enough for a wall + garden strip
                        O_, U_, N_, y_, L_ = M._frame(ring0, edge)
                        Wf_ = float(L_[:, 0][L_[:, 1] < 0.9].max()); D_ = float(L_[:, 1].max())
                        e_ = np.asarray(edge[1], float) - np.asarray(edge[0], float); e_ /= np.linalg.norm(e_)
                        walled = abs(float(U_ @ e_)) > 0.94 and Wf_ >= 4.0 and D_ >= 7.5
                    try:
                        ring, edge1 = setback_ring(ring0, edge, EAVE_SETBACK)
                        # keep the front off the lane's centre line (some roof outlines reach over the OSM line)
                        O, U, N, yaw, Lc = M._frame(ring, edge1)
                        Wq = float(Lc[:, 0][Lc[:, 1] < 0.9].max())
                        need = 1.25 if k.startswith('ishibe') else 1.9
                        dq = LineString([O, O + U * Wq]).distance(lane.line)
                        if dq < need:
                            ring, edge1 = setback_ring(ring0, edge, EAVE_SETBACK + (need - dq) + 0.05)
                        # nothing may stand on a lane's walking line (roof outlines at bends, corner lots)
                        Pr = Polygon(ring)
                        if not Pr.is_valid: Pr = Pr.buffer(0)
                        if Pr.intersects(clear):
                            Pc = Pr.difference(clear)
                            if Pc.is_empty or Pc.area < 0.55 * Pr.area:
                                print('house skipped (on a lane)', b['id']); continue
                            if Pc.geom_type != 'Polygon': Pc = max(Pc.geoms, key=lambda q: q.area)
                            ring = np.asarray(Pc.simplify(0.05).exterior.coords)[:-1]
                    except Exception as e:
                        print('frame fail', b['id'], e); continue
                    Wf = float(Lc[:, 0][Lc[:, 1] < 0.9].max())
                    if Wf < 2.2: continue
                    pts = [O + U * u - N * 0.6 for u in np.linspace(0.25, Wf - 0.25, 5)]
                    zl = np.array([lz(*p) for p in pts])
                    z0 = float(zl.max()) + 0.04
                    ridge = float(b['z0'] or zl.min()) + float(b['h'] or 7.5)
                    hh = float(np.clip(ridge - z0, 4.6, 12.0))
                    if len(rings) > 1: hh += rng.uniform(-0.4, 0.3)
                    s = style_for(k, hh, rng, float(zl.max() - zl.min()))
                    s['ground'] = S.ground
                    if s.get('hy') is not None: s['hy']['lz'] = lz
                    # corner houses: extra dressed fronts along other lanes
                    ce = corner_edges(ring, [lane_lines[j] for j in lane_lines if j != k], lane.line)
                    if ce:
                        s['facade_edges'] = ce
                        s['facade_style'] = dict(door=-1, degoshi=False, chochin=False, nameboard=False, hy=None)
                    try:
                        if walled:
                            s['kind'] = 'ochaya' if hh > 6.0 else 'hiraya'
                            s['hy'] = None; s['inuyarai'] = False; s['komayose'] = False; s['degoshi'] = False
                            info = walled_house(B, S, ring, edge1, z0, hh, s, seed, lz, setback=1.4)
                        else:
                            if k.startswith('ishibe'):
                                s['hy'] = None; s['inuyarai'] = False; s['komayose'] = False; s['degoshi'] = False
                            npart = len(B.parts)
                            info = M.build(B, ring, edge1, z0, hh, 0, s, seed=seed)
                            if k.startswith('ishibe'): drop_front_blocks(B, npart, info)
                            plinth(B, info, z0, lz)
                            built.append((info, z0, seed))
                        n += 1
                    except Exception as e:
                        nfail += 1
                        import traceback; traceback.print_exc()
                        print('machiya fail', b['id'], repr(e))
                S.exclude.append([list(map(float, c)) for c in np.asarray(P.exterior.coords)[:-1]])
    stats['houses'] = n; stats['house_fail'] = nfail
    stats['rows'] = {k: len(v) for k, v in rows.items() if v}
    stats['side_walls'] = side_walls(B, S, built)
    return rows

def corner_edges(ring, lines, main, tol=3.2):
    ring = np.asarray(ring, float)
    out = []
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        d = b - a; L = np.linalg.norm(d)
        if L < 3.0: continue
        m = Point((a + b) / 2)
        if main.distance(m) < 2.5: continue
        for ln in lines:
            if ln.distance(m) > tol + 2.3: continue
            t = ln.project(m); p = ln.interpolate(max(0, t - 1)); q = ln.interpolate(min(ln.length, t + 1))
            e = np.array([q.x - p.x, q.y - p.y]); e /= max(np.linalg.norm(e), 1e-9)
            if abs(np.dot(e, d / L)) > 0.85:
                out.append((tuple(a), tuple(b))); break
    return out
