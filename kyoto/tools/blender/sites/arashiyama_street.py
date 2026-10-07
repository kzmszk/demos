"""嵐山 street rows: 長辻通 from the bridge to 天龍寺's 総門 (both sides), the riverside road west of the bridge (the inns and
restaurants facing the river), the tea houses on 中之島; the Randen 嵐山駅 front; lamps, rickshaws, banners.

The PLATEAU buildings fronting these lines are replaced by sites.machiya town houses (walls set back from the roof
outlines) with the shop fronts of sites.arashiyama_front; the generic buildings they replace are excluded."""
import math, zlib
from contextlib import contextmanager
import numpy as np
import shapely
import shapely.ops
from shapely.geometry import Polygon, LineString, Point, box as sbox
from jk import prim, roof, Frame
import sites.machiya as M
import sites.arashiyama_front as AF
import sites.arashiyama_util as U

NAGATSUJI = 105574207       # 長辻通 (府道29号) from the 総門 (north) to the bridge (south)
RIVERSIDE = 47584215        # 二条停車場嵐山線 along the river west of the bridge
STATION = 'a076acfe'        # PLATEAU id prefix of the Randen 嵐山駅 building
SOMON = (-7468.0, 3348.0)   # 天龍寺 総門 (the tenryuji site's): our street stops short of it

@contextmanager
def patched_front():
    orig = M._front
    def f(B, s, rng, W, z_wp, o, z_edge, wall_t, wmat, wtint, seed, info):
        if s.get('hy') is not None: return AF.front(B, s, rng, W, z_wp, o, z_edge, wall_t, wmat, wtint, seed, info)
        return orig(B, s, rng, W, z_wp, o, z_edge, wall_t, wmat, wtint, seed, info)
    M._front = f
    try: yield
    finally: M._front = orig

def way(S, wid):
    for w in S.osm['ways']:
        if w['id'] == wid: return LineString(w['line'][0])
    raise KeyError(wid)

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
    return ((p.x - d[0] * 3, p.y - d[1] * 3), (p.x + d[0] * 3, p.y + d[1] * 3)), t

def side_of(P, L):
    c = P.representative_point(); t = L.project(c)
    a = np.array(L.interpolate(max(0, t - 1)).coords[0]); b = np.array(L.interpolate(min(L.length, t + 1)).coords[0])
    d = b - a; v = np.array([c.x, c.y]) - a
    return 1 if d[0] * v[1] - d[1] * v[0] > 0 else -1

def lot_slices(P, edge, target=6.0, rng=None):
    O, Uu, N, yaw, Lc = M._frame(np.asarray(P.exterior.coords), edge)
    W = float(Lc[:, 0][Lc[:, 1] < 0.9].max())
    k = int(round(W / target))
    if W < 9.0 or k < 2: return [np.asarray(P.exterior.coords)[:-1]]
    rng = rng or np.random.default_rng(0)
    cuts = np.linspace(0, W, k + 1); cuts[1:-1] += rng.uniform(-0.6, 0.6, k - 1)
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
        out.append(O + np.outer(loc[:, 0], Uu) + np.outer(loc[:, 1], N))
    return out

EAVE_SETBACK = 0.85          # PLATEAU outlines are roof outlines: the walls stand this far behind

def setback_ring(ring, edge, sb):
    O, Uu, N, yaw, Lc = M._frame(ring, edge)
    D = float(Lc[:, 1].max())
    if D - sb < 3.5: sb = max(0.0, D - 3.5)
    if sb <= 0.01: return np.asarray(ring, float), edge
    Pl = Polygon(Lc)
    if not Pl.is_valid: Pl = Pl.buffer(0)
    g = Pl.intersection(sbox(-500, sb, 500, 500))
    if g.is_empty: return np.asarray(ring, float), edge
    if g.geom_type != 'Polygon': g = max(g.geoms, key=lambda q: q.area)
    loc = np.asarray(g.exterior.coords)[:-1]
    return O + np.outer(loc[:, 0], Uu) + np.outer(loc[:, 1], N), (tuple(np.asarray(edge[0], float) + N * sb), tuple(np.asarray(edge[1], float) + N * sb))

# ------------------------------------------------------------------ street character
WALLS = [(205, 168, 98), (214, 186, 128), (222, 206, 172), (232, 224, 204), (196, 156, 92), (226, 214, 186), (184, 150, 104), (236, 232, 222)]
ROWS = {
    'nagatsuji': dict(shop=0.92, tea=0.18, kinds=dict(tsushi=0.35, ochaya=0.35, shop=0.3), awning=0.3, lanterns=0.45, sign=0.55, pots=0.3, banners=0.6, table=0.35),
    'riverside': dict(shop=0.35, tea=0.15, kinds=dict(ochaya=0.75, tsushi=0.25), awning=0.1, lanterns=0.5, sign=0.3, pots=0.5, banners=0.2),
    'island':    dict(shop=0.85, tea=0.75, kinds=dict(tsushi=0.5, ochaya=0.2, shop=0.3), awning=0.2, lanterns=0.7, sign=0.4, pots=0.4, banners=0.5),
}

def pick(rng, wd):
    ks = list(wd.keys()); ps = np.array([wd[k] for k in ks], float); ps /= ps.sum()
    return ks[int(rng.choice(len(ks), p=ps))]

def style_for(row, hh, rng):
    st = ROWS[row]
    if hh < 5.2: kind = 'hiraya'
    elif hh > 10.4: kind = 'sangai'
    else:
        kind = pick(rng, st['kinds'])
        if kind == 'tsushi' and hh > 8.4: kind = 'ochaya'
    s = dict(kind=kind, wall=WALLS[int(rng.integers(len(WALLS)))])
    s['party'] = 'wall_board' if rng.random() < 0.25 else 'wall_plaster'
    s['party_tint'] = (226, 220, 206) if rng.random() < 0.5 else s['wall']
    if rng.random() < 0.1: s['wood'] = 'bengara'
    hy = {}
    if rng.random() < st['shop']:
        hy['shop'] = ['open', 'glass', 'mixed'][int(rng.choice(3, p=[0.5, 0.15, 0.35]))]
        hy['goods'] = 'boxes'
        if rng.random() < st['awning']: hy['awning'] = AF.AWNING[int(rng.integers(len(AF.AWNING)))]; hy['awning_part'] = rng.random() < 0.4
        if rng.random() < st['lanterns']: hy['lanterns'] = int(rng.integers(1, 5)); hy['red_lanterns'] = rng.random() < 0.6
        if rng.random() < st['tea']: hy['bench'] = True; hy['parasol'] = rng.random() < 0.6
        if rng.random() < st['sign']: hy['sign'] = True
        if rng.random() < st.get('table', 0.0): hy['table'] = True
        if rng.random() < st.get('banners', 0.0): hy['banners'] = int(rng.integers(1, 3))
        hy['kanban'] = rng.random() < 0.7
        hy['hanging_sign'] = rng.random() < 0.35
        s.update(inuyarai=False, komayose=False, degoshi=False, chochin=False)
        s['noren'] = M.NOREN[int(rng.integers(len(M.NOREN)))] if rng.random() < 0.85 else False
    else:
        s['chochin'] = rng.random() < 0.6
        s['railing'] = True; s['sudare'] = rng.random() < 0.7
        s['noren'] = M.NOREN[int(rng.integers(len(M.NOREN)))]
    if rng.random() < st.get('pots', 0.3): hy['pots'] = int(rng.integers(1, 4))
    if row == 'riverside': s['eave'] = rng.uniform(1.0, 1.25)          # the inns' deep eaves toward the river
    s['hy'] = hy
    return s

# ------------------------------------------------------------------ rows
def select(S, L, dmax, used, forbid, side=None, xr=None, keep=None, max_h=13.0):
    out = []
    for b in S.plateau:
        if b['id'] in used or b['kind'] not in ('trad', 'house', 'mid', 'shed'): continue
        h = float(b['h'] or 0); st = int(b['st'] or 0)
        if h > max_h or st > 3 or h < 2.5: continue
        P = footprint(b)
        if P.area < 14: continue
        if P.distance(L) > dmax: continue
        rp = P.representative_point()
        if forbid is not None and forbid.intersects(P.buffer(-0.3)): continue
        if side is not None and side_of(P, L) != side: continue
        if xr is not None and not (xr[0] <= rp.x <= xr[1]): continue
        if keep is not None and not keep(P): continue
        out.append((b, P))
    return out

def build_row(B, S, picks, L, row, used, stats, forbid, need, built, lz=None):
    rng = np.random.default_rng(zlib.crc32(row.encode()))
    lz = lz or S.ground
    n = 0
    for (b, P) in picks:
        edge, t = front_of(P, L)
        rings = lot_slices(P, edge, rng=rng)
        for ring0 in rings:
            seed = int(rng.integers(1 << 30))
            try:
                ring, edge1 = setback_ring(ring0, edge, EAVE_SETBACK)
                O, Uu, N, yaw, Lc = M._frame(ring, edge1)
                Wq = float(Lc[:, 0][Lc[:, 1] < 0.9].max())
                dq = LineString([O, O + Uu * Wq]).distance(L)
                if dq < need: ring, edge1 = setback_ring(ring0, edge, EAVE_SETBACK + (need - dq) + 0.05)
                Pr = Polygon(ring)
                if not Pr.is_valid: Pr = Pr.buffer(0)
                if forbid is not None and Pr.intersects(forbid):
                    Pr = Pr.difference(forbid.buffer(0.3))
                    if Pr.is_empty or Pr.geom_type != 'Polygon': continue
                    ring = np.asarray(Pr.exterior.coords)[:-1]
                O, Uu, N, yaw, Lc = M._frame(ring, edge1)
                Wf = float(Lc[:, 0][Lc[:, 1] < 0.9].max())
                if Wf < 2.4: continue
            except Exception as e:
                print('frame fail', b['id'], e); continue
            pts = [O + Uu * u - N * 0.6 for u in np.linspace(0.25, Wf - 0.25, 5)]
            zl = np.array([lz(*p) for p in pts])
            z0 = float(zl.max()) + 0.04
            ridge = float(b['z0'] or zl.min()) + float(b['h'] or 7.5)
            hh = float(np.clip(ridge - z0, 4.4, 11.5))
            if len(rings) > 1: hh += rng.uniform(-0.4, 0.3)
            s = style_for(row, hh, rng)
            s['ground'] = S.ground
            if s.get('hy') is not None: s['hy']['lz'] = lz
            try:
                info = M.build(B, ring, edge1, z0, hh, 0, s, seed=seed)
                built.append((info, z0, seed, row))
                n += 1
            except Exception as e:
                import traceback; traceback.print_exc()
                print('machiya fail', b['id'], repr(e))
        S.exclude.append([list(map(float, c)) for c in np.asarray(P.exterior.coords)[:-1]])
        used.add(b['id'])
    stats[row] = stats.get(row, 0) + n
    return n

def build(B, S, river, forbid):
    stats = {}; used = set(); built = []
    nag = way(S, NAGATSUJI)
    # stop at the 総門: the part of the street south of it
    t_end = nag.project(Point(*SOMON))
    nag_s = shapely.ops.substring(nag, t_end + 3.0, nag.length)
    riv = way(S, RIVERSIDE)
    station = [b for b in S.plateau if b['id'][5:].startswith(STATION)]
    for b in station: used.add(b['id'])
    with patched_front():
        picks = select(S, nag_s, 11.0, used, forbid)
        build_row(B, S, picks, nag_s, 'nagatsuji', used, stats, forbid, need=6.3, built=built)
        picks = [(b, P) for (b, P) in select(S, riv, 12.0, used, forbid, side=side_of_north(riv), xr=(-7700.0, -7395.0)) if P.area < 420 or b['kind'] == 'trad']
        build_row(B, S, picks, riv, 'riverside', used, stats, forbid, need=4.6, built=built)
        # 三条通 east of the bridge, the north side facing the river bank
        san = way(S, 22727319)
        picks = [(b, P) for (b, P) in select(S, san, 11.0, used, forbid, side=side_of_north(san), xr=(-7386.0, -7275.0)) if P.area < 760]
        build_row(B, S, picks, san, 'nagatsuji', used, stats, forbid, need=5.6, built=built)
        # 中之島's tea houses: fronts to the path along them (north) or to the road
        isl_path = way(S, 209923785); isl_road = way(S, 59377344)
        def on_island(P): return river.all.buffer(-0.5).disjoint(P) and Point(P.centroid).y < 2905 and P.centroid.x > -7460 and P.centroid.x < -7285
        picks = select(S, isl_road, 9.0, used, forbid, keep=on_island)
        build_row(B, S, picks, isl_road, 'island', used, stats, forbid, need=4.8, built=built)
        picks = select(S, isl_path, 12.0, used, forbid, keep=on_island)
        build_row(B, S, picks, isl_path, 'island', used, stats, forbid, need=1.6, built=built)
    side_walls(B, S, built)
    for b in station: randen(B, S, b, nag_s)
    corridor(S, nag_s, used, forbid)
    street_lamps(B, S, nag_s)
    rickshaws(B, S, nag_s, riv)
    print('arashiyama street:', stats, 'houses', len(built), 'excluded', len(S.exclude))
    return built

def side_of_north(L):
    """the side (+1 left / -1 right of the line's direction) that lies north"""
    a = np.array(L.coords[0]); b = np.array(L.coords[-1]); d = b - a
    return 1 if d[0] * 1.0 - d[1] * 0.0 > 0 else -1

def corridor(S, L, used, forbid=None):
    """exclude ring over the street itself (between the house fronts): keeps the generic street trees, lamps and poles off
    it (we place our own).  Contains no generic building other than the ones replaced (checked)."""
    g = L.buffer(5.6, cap_style='flat')
    if forbid is not None: g = g.difference(forbid.buffer(0.5))
    for b in S.plateau:
        if b['id'] in used: continue
        P = footprint(b)
        if g.contains(P.representative_point()): g = g.difference(P.buffer(0.5))
    for p in U.polys(g):
        S.exclude.append(U.ring(p))

def side_walls(B, S, built):
    """exposed side walls get a dark board skirt, posts and a tie beam (as 東山 does)"""
    from shapely.strtree import STRtree
    fps = [footprint(b) for b in S.plateau]
    worlds = []
    for (info, z0, seed, row) in built:
        ox, oy, yaw = info['frame']; c, s_ = math.cos(yaw), math.sin(yaw)
        L = np.asarray(info['ring_local'])[:-1]
        worlds.append(Polygon(np.c_[ox + c * L[:, 0] - s_ * L[:, 1], oy + s_ * L[:, 0] + c * L[:, 1]]).buffer(0))
    allp = fps + worlds
    tree = STRtree(allp)
    for hi, (info, z0, seed, row) in enumerate(built):
        ox, oy, yaw = info['frame']; c, s_ = math.cos(yaw), math.sin(yaw)
        L = np.asarray(info['ring_local']); me = worlds[hi]
        rng = np.random.default_rng(seed + 5)
        tint = (52, 40, 30) if rng.random() < 0.7 else (70, 56, 44)
        for i in range(len(L) - 1):
            a, b = L[i], L[i + 1]
            if a[1] < 0.6 and b[1] < 0.6: continue
            ln = float(np.linalg.norm(b - a))
            if ln < 2.0: continue
            m = (a + b) / 2; d = (b - a) / ln; out = np.array([d[1], -d[0]])
            pm = m + out * 0.6
            pw = Point(ox + c * pm[0] - s_ * pm[1], oy + s_ * pm[0] + c * pm[1])
            if any(allp[k] is not me and allp[k].distance(pw) < 0.35 for k in tree.query(pw.buffer(0.35))): continue
            with Frame(B, ox, oy, z0, yaw):
                ga = float(S.ground(ox + c * a[0] - s_ * a[1], oy + s_ * a[0] + c * a[1])) - z0
                gb = float(S.ground(ox + c * b[0] - s_ * b[1], oy + s_ * b[0] + c * b[1])) - z0
                zt = 1.75; o2 = out * 0.025
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

# ------------------------------------------------------------------ the Randen station front
def randen(B, S, b, L):
    """嵐電 嵐山駅: the big hall replaced by a tiled hall whose street face carries the red vertical-louvre screen, the
    curved canopy over the entrance on two green columns, pink and white door curtains, red benches in the forecourt"""
    P = footprint(b)
    edge, t = front_of(P, L)
    O, Uu, N, yaw, Lc = M._frame(np.asarray(P.exterior.coords)[:-1], edge)
    fp = Polygon(Lc).buffer(0)
    x0, y0, x1, y1 = fp.bounds
    W = x1 - x0; D = y1 - y0
    zf = float(S.ground(*(O + Uu * W / 2 - N * 1.0)))
    S.exclude.append([list(map(float, c)) for c in np.asarray(P.exterior.coords)[:-1]])
    with Frame(B, O[0], O[1], zf, yaw):
        cx = (x0 + x1) / 2
        wall_c = (228, 218, 196)
        # the hall: walls and a big hipped roof
        hz = 7.6
        ring = np.asarray(shapely.geometry.polygon.orient(fp, 1.0).exterior.coords)[:-1]
        for i in range(len(ring)):
            a = ring[i]; c = ring[(i + 1) % len(ring)]
            if a[1] < 0.8 and c[1] < 0.8: continue                    # the front: below
            Q = np.array([[a[0], a[1], -0.3], [c[0], c[1], -0.3], [c[0], c[1], hz], [a[0], a[1], hz]])
            M.oquad(B, Q, (c[1] - a[1], -(c[0] - a[0]), 0), 'wall_plaster', c0=(*wall_c, 0))
        with Frame(B, cx, (y0 + y1) / 2, 0.0, 0.0):
            roof.roof(B, W - 1.0, D - 1.0, hz, 1.2, kind='yosemune', cover='sangawara', pitch=0.45, rafter=0, ends=None, edge=0.25)
        # the street face: a dark wall up to the canopy, the entrance opening where nothing stands in front of the hall
        others = [footprint(q) for q in S.plateau if q['id'] != b['id']]
        others = shapely.unary_union([q for q in others if q.distance(P) < 14.0]) if others else None
        us = np.arange(x0 + 0.5, x1 - 0.5, 0.5); free = []
        for u in us:
            w0 = O + Uu * u; w1 = O + Uu * u - N * 12.0
            free.append(others is None or not LineString([tuple(w0 - N * 0.3), tuple(w1)]).intersects(others))
        best = (0, 0); run = None
        for i, f in enumerate(free + [False]):
            if f and run is None: run = i
            if not f and run is not None:
                if i - run > best[1] - best[0]: best = (run, i)
                run = None
        if best[1] - best[0] >= 8:
            fa, fb = us[best[0]], us[best[1] - 1]; cx = (fa + fb) / 2; ew = min(10.0, fb - fa - 0.6)
        else:
            ew = min(11.0, W * 0.38)
        ea = cx - ew / 2; eb = cx + ew / 2
        M.wall_holes(B, x0, x1, -0.3, hz, 0.0, [(ea, eb, -0.3, 4.4)], 'wall_board', c0=(54, 44, 36, 0))
        # inside the entrance: a passage toward the platforms (dark, lit lanterns overhead)
        M.front_rect(B, ea, eb, 0.0, 4.4, 9.0, 'black_lacquer', facing=-1)
        M.side_rect(B, 0.0, 9.0, 0.0, 4.4, ea, 'wall_plaster', facing=1, c0=(200, 190, 170, 0)); M.side_rect(B, 0.0, 9.0, 0.0, 4.4, eb, 'wall_plaster', facing=-1, c0=(200, 190, 170, 0))
        M.quad(B, (ea, 9.0, 4.4), (eb, 9.0, 4.4), (eb, 0.0, 4.4), (ea, 0.0, 4.4), 'eave_wood', c1=(0, 2, 0, 0))
        prim.polygon(B, [(ea, 0.0), (eb, 0.0), (eb, 9.0), (ea, 9.0)], 0.02, 'stone')
        for k, u in enumerate(np.linspace(ea + 1.0, eb - 1.0, 5)):
            M.chochin(B, u, 3.0, 4.35, r=0.2, h=0.5, lamp=(k % 2 == 0))
        # pink and white curtains across the entrance top
        nk = max(4, int(ew / 1.2))
        for k in range(nk):
            a = ea + k * ew / nk + 0.02; c = ea + (k + 1) * ew / nk - 0.02
            tint = (226, 140, 150) if k % 2 == 0 else (238, 236, 230)
            M.quads(B, [[(a, -0.05, 2.9), (c, -0.05, 2.9), (c, -0.05, 4.3), (a, -0.05, 4.3)]], 'cloth', tag='detail', c0=(*tint, 0))
            M.quads(B, [[(c, -0.04, 2.9), (a, -0.04, 2.9), (a, -0.04, 4.3), (c, -0.04, 4.3)]], 'cloth', tag='detail', c0=(*tint, 0))
        # the station name board over the curtains
        M.hbox(B, cx - 1.6, cx + 1.6, -0.25, -0.05, 4.4, 4.95, 'black_lacquer', tag='main')
        M.quad(B, (cx - 1.5, -0.26, 4.45), (cx + 1.5, -0.26, 4.45), (cx + 1.5, -0.26, 4.9), (cx - 1.5, -0.26, 4.9), 'white_paint', tag='detail',
               uv=np.array([(0, 0), (3.0, 0), (3.0, 0.5), (0, 0.5)]), c1=(0, 7, 77, 0))
        # the canopy: a flat roof with a curved (唐破風-like) front edge on two green columns
        cw = ew + 2.0; ca = cx - cw / 2; cb = cx + cw / 2
        us = np.linspace(ca, cb, 25)
        bump = 0.55 * np.exp(-((us - cx) / (cw * 0.16)) ** 2)
        zc = 5.2 + bump
        front = np.c_[us, np.full(len(us), -3.2), zc]
        prim.sweep(B, front, [(-0.05, -0.55), (0.25, -0.55), (0.25, 0.12), (-0.05, 0.12)], 'black_lacquer', tag='main', up=(0, 0, 1), caps=True)
        top = []; I = []
        for i, u in enumerate(us):
            top += [(u, -3.2, zc[i] + 0.1), (u, 0.0, 5.6)]
        top = np.array(top)
        for i in range(len(us) - 1):
            a = 2 * i
            I += [[a, a + 2, a + 3], [a, a + 3, a + 1]]
        I = np.array(I)
        fn = np.cross(top[I[:, 1]] - top[I[:, 0]], top[I[:, 2]] - top[I[:, 0]])
        if fn[:, 2].sum() < 0: I = I[:, ::-1]
        B.add(top, I, 'roof_metal', tag='main', c0=(60, 58, 54, 0))
        B.add(top - [0, 0, 0.12], I[:, ::-1], 'eave_wood', tag='main', c1=(0, 2, 0, 0))
        for u in (ea + 0.3, eb - 0.3):
            prim.cyl(B, (u, -2.6, 0.0), (u, -2.6, 5.15), 0.32, 0.32, 14, 'copper', tag='main')
            prim.polygon(B, [(u - 0.4, -3.0), (u + 0.4, -3.0), (u + 0.4, -2.2), (u - 0.4, -2.2)], 0.2, 'stone', tag='block')
        # the red vertical louvre screen above (the upper street face, leaning back like a roof)
        zs0, zs1 = 5.9, 10.4
        vb = 2.6
        n = int((x1 - x0) / 0.16)
        uu = np.linspace(x0 + 0.1, x1 - 0.1, n)
        P0 = np.c_[uu, np.full(n, -0.6), np.full(n, zs0)]; P1 = np.c_[uu, np.full(n, vb), np.full(n, zs1)]
        M.bars(B, P0, P1, (1, 0, 0), 0.07, 0.07, 'vermilion', tag='detail', c0=M.paint_tint((150, 40, 32)))
        M.quad(B, (x0, -0.45, zs0), (x1, -0.45, zs0), (x1, vb + 0.15, zs1), (x0, vb + 0.15, zs1), 'vermilion', tag='main', c0=M.paint_tint((96, 30, 26)))
        M.quad(B, (x0, -0.6, zs0 - 0.4), (x1, -0.6, zs0 - 0.4), (x1, -0.6, zs0), (x0, -0.6, zs0), 'black_lacquer', tag='main')
        M.quad(B, (x0, -0.6, zs0 - 0.4), (x0, 0.0, zs0 - 0.4), (x1, 0.0, zs0 - 0.4), (x1, -0.6, zs0 - 0.4), 'eave_wood', tag='main')
        # the forecourt: red benches with felt, a sign stand
        rng = np.random.default_rng(3)
        for k in range(4):
            with Frame(B, ea - 2.6, -1.4 - k * 1.3, 0.0, 0.0):
                AF.bench(B, -0.9, 0.9, 0.0, rng)
        B.lamp(cx, -1.5, 4.8, 30.0, (1.0, 0.75, 0.5))
        prim.polygon(B, [(x0, 0.0), (ea, 0.0), (ea, D), (x0, D)], 0.1, 'stone', tag='block')
        prim.polygon(B, [(eb, 0.0), (x1, 0.0), (x1, D), (eb, D)], 0.1, 'stone', tag='block')
        prim.polygon(B, [(ea, 9.0), (eb, 9.0), (eb, D), (ea, D)], 0.1, 'stone', tag='block')

# ------------------------------------------------------------------ lamps, rickshaws
def street_lamps(B, S, L, spacing=21.0):
    side = 1
    for t in np.arange(8.0, L.length - 4.0, spacing):
        p = np.array(L.interpolate(t).coords[0]); d = U.tangent(L, t); n = np.array([-d[1], d[0]]) * side
        q = p + n * 4.9
        U.lamp_post(B, q[0], q[1], float(S.ground(*q)), h=4.6, yaw=math.atan2(-n[1], -n[0]), watts=26.0)
        side = -side

def rickshaw(B, S, x, y, yaw, rng, hood_up=False):
    """人力車: two big spoked wheels, the lacquered body with a red blanket, the folding hood, shafts down on the road"""
    z = float(S.ground(x, y))
    with Frame(B, x, y, z, yaw):
        R = 0.62
        for s in (-1, 1):
            v = s * 0.66
            ang = np.linspace(0, 2 * math.pi, 21)
            rim = np.c_[np.cos(ang) * R, np.full(len(ang), v), R + np.sin(ang) * R]
            prim.sweep(B, rim, [(-0.025, -0.03), (0.025, -0.03), (0.025, 0.03), (-0.025, 0.03)], 'black_lacquer', tag='detail', up=(0, 1, 0))
            for k in range(10):
                a = 2 * math.pi * k / 10
                M.bars(B, [(0, v, R)], [(math.cos(a) * (R - 0.03), v, R + math.sin(a) * (R - 0.03))], (0, 1, 0), 0.015, 0.015, 'vermilion', tag='detail', c0=M.paint_tint((140, 30, 24)))
            prim.cyl(B, (0, v - 0.08, R), (0, v + 0.08, R), 0.07, 0.07, 8, 'metal_dark', tag='detail')
        prim.cyl(B, (0, -0.62, R), (0, 0.62, R), 0.025, 0.025, 6, 'metal_dark', tag='detail')
        # body (seat box) and the footboard, lacquered black
        M.hbox(B, -0.35, 0.3, -0.5, 0.5, R + 0.05, R + 0.5, 'black_lacquer', tag='main')
        M.hbox(B, -0.55, -0.3, -0.5, 0.5, R + 0.45, R + 0.95, 'black_lacquer', tag='main')            # back rest
        M.hbox(B, 0.3, 0.75, -0.42, 0.42, 0.28, 0.33, 'black_lacquer', tag='main')                    # footboard
        M.bars(B, [(0.3, -0.42, R + 0.1), (0.3, 0.42, R + 0.1)], [(0.72, -0.42, 0.33), (0.72, 0.42, 0.33)], (0, 1, 0), 0.04, 0.04, 'black_lacquer', tag='detail')
        # red blanket over the seat and down the front
        M.quads(B, [[(-0.32, -0.52, R + 0.52), (0.33, -0.52, R + 0.52), (0.33, 0.52, R + 0.52), (-0.32, 0.52, R + 0.52)],
                    [(0.33, -0.52, R + 0.52), (0.6, -0.5, 0.45), (0.6, 0.5, 0.45), (0.33, 0.52, R + 0.52)]], 'cloth', tag='main', c0=(176, 22, 26, 0))
        M.quads(B, [[(0.33, 0.52, R + 0.52), (0.6, 0.5, 0.45), (0.6, -0.5, 0.45), (0.33, -0.52, R + 0.52)]], 'cloth', tag='detail', c0=(150, 18, 22, 0))
        # the hood (folded back, or up)
        prof = np.linspace(0, math.pi, 9)
        for k, sc in enumerate((1.0, 0.92, 0.84)):
            if hood_up:
                pts = np.array([(-0.5 + 0.28 * k, math.cos(a) * 0.55, R + 0.95 + math.sin(a) * 0.5) for a in prof])
            else:
                pts = np.array([(-0.55 - math.sin(a) * 0.35 * sc, math.cos(a) * 0.55, R + 0.9 + 0.1 * k) for a in prof])
            prim.sweep(B, pts, [(-0.12, -0.012), (0.12, -0.012), (0.12, 0.012), (-0.12, 0.012)], 'black_lacquer', tag='detail', up=(1, 0, 0), closed=True)
        # shafts (梶棒) from under the seat down to the road in front, the cross bar
        for s in (-1, 1):
            M.bars(B, [(-0.1, s * 0.45, R + 0.08)], [(2.1, s * 0.4, 0.05)], (0, 1, 0), 0.05, 0.06, 'black_lacquer', tag='main', caps=True)
        M.bars(B, [(2.05, -0.42, 0.08)], [(2.05, 0.42, 0.08)], (0, 0, 1), 0.06, 0.06, 'black_lacquer', tag='detail', caps=True)
        prim.polygon(B, [(-0.7, -0.75), (2.2, -0.75), (2.2, 0.75), (-0.7, 0.75)], 0.3, 'stone', tag='block')

def rickshaws(B, S, nag, riv):
    rng = np.random.default_rng(41)
    # at the corner by the bridge's north end, along the north kerb of the riverside road (a rank of four)
    for k in range(4):
        t = 9.0 + k * 1.7
        p = np.array(riv.interpolate(t).coords[0]); d = U.tangent(riv, t); n = np.array([-d[1], d[0]])
        if n[1] < 0: n = -n
        q = p + n * 4.4
        rickshaw(B, S, q[0], q[1], math.atan2(-n[1], -n[0]), rng, hood_up=(k == 2))
    # two on 長辻通 near the bridge, shafts toward the road
    for (t, side) in ((nag.length - 22.0, 1), (nag.length - 48.0, -1)):
        p = np.array(nag.interpolate(t).coords[0]); d = U.tangent(nag, t); n = np.array([-d[1], d[0]]) * side
        q = p + n * 3.9
        rickshaw(B, S, q[0], q[1], math.atan2(d[1], d[0]) + (0.0 if side > 0 else math.pi), rng)
