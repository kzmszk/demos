"""伏見稲荷大社: the pilgrim routes up 稲荷山 with their torii tunnels.

Routes (all oriented uphill, so every torii faces the worshipper coming up and shows its donor panels to those going
down): 本殿 → the stairs behind → the path of large torii in front of 奥宮 → the fork → 千本鳥居 (two one-way tunnels)
→ 奥社奉拝所 → 熊鷹社 (新池) → 三ツ辻 → 四ツ辻 → the summit loop (三ノ峰, 間ノ峰, 二ノ峰, 一ノ峰 and back by 御劔社,
御膳谷, 眼力社).  Densities from the dossier (F9 / F10 surveys, OSM notes): 千本鳥居 ~390 per branch at ~0.22 m pitch,
奥社→新池 543, 新池→三ツ辻 303 (densest), 三ツ辻→四ツ辻 235 (larger, spaced), the loop: spaced torii and the 神蹟."""
import math
import numpy as np
from . import fushimi_inari_paths as FP
from . import fushimi_inari_torii as FT

# landmarks on the OSM path graph (local metres)
LM = dict(honden=(1338.0, -2074.9), fork=(1456.7, -2087.9), okusha=(1517.2, -2139.5), kumataka=(1812.5, -1924.9),
          mittsu=(1823.5, -1735.6), yottsu=(2064.5, -1857.9), summit=(2439.1, -2081.6))
# plazas where the tunnels break (centre, radius)
PLAZAS = [((1528.0, -2137.5), 9.0),      # 奥社奉拝所 + おもかる石
          ((1811.0, -1930.0), 9.0),      # 熊鷹社 / 新池
          ((1829.0, -1741.0), 11.0),     # 三ツ辻 (tea houses)
          ((2064.5, -1859.0), 13.0),     # 四ツ辻 (the view, tea house)
          ((2149.0, -1990.0), 8.0),      # 三ノ峰
          ((2206.0, -2068.0), 6.0),      # 間ノ峰 荷田社
          ((2306.0, -2066.0), 9.0),      # 二ノ峰
          ((2439.0, -2084.0), 10.0),     # 一ノ峰
          ((2470.0, -1898.0), 8.0),      # 御劔社
          ((2256.0, -1812.0), 14.0),     # 御膳谷奉拝所
          ((2249.0, -1840.0), 6.0),      # 眼力社
          ]

# torii sizes (号: pillar diameter = 3 cm x 号): class, height (笠木 top), span (pillar centres), diameter
SIZES = {
    'S5': ('S', 2.75, 2.0, 0.15), 'S6': ('S', 2.95, 2.15, 0.18),
    'M7': ('M', 3.3, 2.45, 0.21), 'M8': ('M', 3.6, 2.7, 0.24),
    'L9': ('L', 4.1, 3.05, 0.27), 'L10': ('L', 4.5, 3.35, 0.30),
    'XLs': ('XL', 4.9, 2.9, 0.42),      # the 3 "huge" ones in the 千本鳥居
}

def make_routes(S):
    net = FP.Net(S)
    R = {}
    def mk(name, a, b, **kw):
        st = net.route(LM[a] if isinstance(a, str) else a, LM[b] if isinstance(b, str) else b, **kw)
        R[name] = FP.Route(net, st, S, name)
        return st
    mk('lower', 'honden', 'fork')
    mk('senbon_up', 'fork', 'okusha', prefer=lambda e: 0.3 if e[2] == 260121328 else 1.0)
    mk('senbon_down', 'fork', 'okusha', prefer=lambda e: 0.3 if e[2] == 377968455 else 1.0)
    mk('okusha_kumataka', 'okusha', 'kumataka')
    mk('kumataka_mittsu', 'kumataka', 'mittsu')
    mk('mittsu_yottsu', 'mittsu', 'yottsu')
    _separate(R['senbon_up'], R['senbon_down'], 3.0)
    st = mk('loop_a', 'yottsu', 'summit')
    used = set(e for n, e in st if e is not None)
    mk('loop_b', 'yottsu', 'summit', avoid=used, avoid_pen=50)
    return net, R

def _separate(a, b, gap):
    """the two 千本鳥居 branches share their end nodes in OSM and diverge slowly: push them apart (each half the
    shortfall, along its normal) so that the two tunnels stand side by side, `gap` metres centre to centre"""
    from shapely.geometry import LineString, Point
    for (r, o) in ((a, b), (b, a)):
        lo = LineString(o.P)
        P = r.P.copy()
        for i, p in enumerate(r.P):
            d = lo.distance(Point(p))
            if d >= gap: continue
            q = np.array(lo.interpolate(lo.project(Point(p))).coords[0])
            n = np.array([-r.T[i][1], r.T[i][0]])
            side = 1.0 if n @ (p - q) >= 0 else -1.0
            if d < 1e-3:
                # at the shared node: decide by the side the branch goes to a little further on
                j = min(i + int(8 / r.ds), len(r.P) - 1)
                pj = r.P[j]; qj = np.array(lo.interpolate(lo.project(Point(pj))).coords[0])
                side = 1.0 if n @ (pj - qj) >= 0 else -1.0
            P[i] = p + n * side * (gap - d) / 2
        r.P2 = P
    for r in (a, b):
        r.P = r.P2
        Ps = np.stack([FP._smooth(r.P[:, 0], 1.5 / r.ds), FP._smooth(r.P[:, 1], 1.5 / r.ds)], 1)
        T = np.gradient(Ps, axis=0); T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9); r.T = T
        r.z_raw = r.S.ground(r.P[:, 0], r.P[:, 1]); r.z = FP._smooth(r.z_raw, 0.8 / r.ds)

def _gaps(r, extra=(), jgap=1.8, rng=None, every=None, glen=(2.5, 6.0)):
    """s-intervals with no torii: junctions, plazas, random breathers"""
    g = [(s - jgap, s + jgap) for s in r.junctions]
    for (c, rad) in PLAZAS:
        d = np.hypot(r.P[:, 0] - c[0], r.P[:, 1] - c[1])
        ins = np.where(d < rad)[0]
        if len(ins): g.append((r.s[ins[0]] - 1.0, r.s[ins[-1]] + 1.0))
    g += list(extra)
    if rng is not None and every:
        s = rng.uniform(0.3, 1.0) * every[0]
        while s < r.L:
            L = rng.uniform(*glen); g.append((s, s + L))
            s += L + rng.uniform(*every)
    return g

def _in(s, gaps):
    return any(a <= s <= b for (a, b) in gaps)

class Tunnels:
    """collects torii instances per size (templates), the s-ranges they cover per route, pillar feet for blockers"""
    def __init__(self):
        self.tpl = {}; self.count = {}; self.feet = []; self.cover = {}
    def template(self, size):
        if size not in self.tpl:
            cls, H, sp, d = SIZES[size]
            self.tpl[size] = FT.Template(FT.inari_torii, H, sp, d, cls)
            self.count[size] = 0
        return self.tpl[size]

def program(R, rng):
    """[(route, s0, s1, pitch, sizes, weights, dense, jitter, gaps)] — the torii stretches"""
    P = []
    r = R['lower']
    # the path of large torii (way 260121354, 3 m wide) in front of 奥宮: ~66 torii, 9-10号 (the dossier's "first 14 + 66")
    s_a = r.s_near(1390.4, -2067.8); s_b = r.s_near(1453.2, -2085.4)
    P.append(('lower', s_a + 1.5, s_b - 1.2, 0.95, ['L9', 'L10'], [0.5, 0.5], True, 0.0, []))
    # the first ones: up the stairs behind the honden to the 奥宮 level
    s_c = r.s_near(1367.9, -2081.1)
    P.append(('lower', s_c + 2.0, s_a - 3.0, 1.6, ['M8', 'L9'], [0.6, 0.4], False, 0.0, []))
    # 千本鳥居: two one-way tunnels of 5号 torii, pillars almost touching
    for name, cnt in (('senbon_up', 390), ('senbon_down', 393)):
        rr = R[name]; s0, s1 = 1.0, rr.L - 1.5
        P.append((name, s0, s1, (s1 - s0 - (2.4 if name == 'senbon_down' else 0.0)) / cnt, ['S5'], [1.0], True, 0.0, [(39.8, 42.2)] if name == 'senbon_down' else []))
    P.append(('senbon_down', 40.0, 42.0, 0.75, ['XLs'], [1.0], True, 0.0, []))
    # 奥社 -> 新池 (熊鷹社): 543 torii over ~450 m with breaks
    P.append(('okusha_kumataka', 0.0, R['okusha_kumataka'].L, 0.62, ['S6', 'M7', 'M8', 'S5'], [0.35, 0.35, 0.15, 0.15], True, 0.08,
              _gaps(R['okusha_kumataka'], rng=rng, every=(30, 60))))
    # 新池 -> 三ツ辻: the densest after the 千本鳥居 (303 over 196 m), on steps
    P.append(('kumataka_mittsu', 0.0, R['kumataka_mittsu'].L, 0.52, ['S6', 'M7', 'S5'], [0.45, 0.35, 0.2], True, 0.06,
              _gaps(R['kumataka_mittsu'], rng=rng, every=(45, 80), glen=(2.0, 4.0))))
    # 三ツ辻 -> 四ツ辻: larger and spaced (235 over 304 m)
    P.append(('mittsu_yottsu', 0.0, R['mittsu_yottsu'].L, 1.2, ['L9', 'M8', 'L10'], [0.4, 0.35, 0.25], True, 0.12,
              _gaps(R['mittsu_yottsu'], rng=rng, every=(50, 90), glen=(3.0, 6.0))))
    # the summit loop: spaced torii, denser runs near the shrines
    for name in ('loop_a', 'loop_b'):
        rr = R[name]
        P.append((name, 0.0, rr.L, 2.3, ['M7', 'M8', 'S6'], [0.4, 0.3, 0.3], False, 0.35, _gaps(rr, rng=rng, every=(35, 70), glen=(4.0, 12.0))))
    return P

def _band_widths(r, R, name):
    """for the two 千本鳥居 branches: where the other tunnel runs alongside, a thin blocker on the midline between them
    instead of a band reaching into it"""
    if not name.startswith('senbon'): return None, None
    from shapely.geometry import LineString, Point
    other = R['senbon_down' if name == 'senbon_up' else 'senbon_up']
    lo = LineString(other.P)
    n = len(r.s); sp = SIZES['S5'][2]
    inner = [np.full(n, sp / 2 + 0.55), np.full(n, sp / 2 + 0.55)]; outer = [np.full(n, sp / 2 + 1.1), np.full(n, sp / 2 + 1.1)]
    for i in range(n):
        p = r.P[i]; d = lo.distance(Point(p))
        if d > 4.4: continue
        q = np.array(lo.interpolate(lo.project(Point(p))).coords[0])
        nn = np.array([-r.T[i][1], r.T[i][0]])
        k = 0 if nn @ (q - p) > 0 else 1
        inner[k][i] = d / 2 - 0.04; outer[k][i] = d / 2 + 0.04
    return (inner[0], inner[1]), (outer[0], outer[1])

def build_tunnels(B, S, R, rng):
    """routes -> corridors, steps, torii, blockers, walk surfaces; returns the Tunnels record + per-route info"""
    T = Tunnels()
    prog = program(R, rng)
    # per route: widths from the torii standing on it
    info = {}
    for name, r in R.items():
        n = len(r.s)
        o1 = np.full(n, 0.95); o2 = np.full(n, 1.35)
        surf = []
        for w in r.way:
            t = r.net.ways[w]['tags']; sf = t.get('surface', '')
            surf.append({'sett': 'stone_sett', 'concrete': 'concrete', 'compacted': 'soil', 'ground': 'soil', 'dirt': 'soil', 'gravel': 'gravel',
                         'unpaved': 'soil', 'asphalt': 'asphalt'}.get(sf, 'stone_slab'))
        info[name] = dict(o1=o1, o2=o2, pave=np.array(surf), recs=[])
    # pick the torii positions first (they set the corridor widths)
    for (name, s0, s1, pitch, sizes, wts, dense, jit, gaps) in prog:
        r = R[name]; inf = info[name]
        s = s0 + pitch / 2
        recs = []
        while s < s1:
            if not _in(s, gaps):
                size = sizes[int(rng.choice(len(sizes), p=np.array(wts) / sum(wts)))]
                recs.append((s, size))
            s += pitch * (1.0 + jit * rng.uniform(-1, 1))
        inf['recs'] += [(s_, sz, dense) for (s_, sz) in recs]
        for (s_, sz) in recs:
            sp = SIZES[sz][2]
            k = r.sub(s_ - 1.5, s_ + 1.5)
            inf['o2'][k] = np.maximum(inf['o2'][k], sp / 2 + 0.45)
            inf['o1'][k] = np.minimum(inf['o1'][k], max(0.6, sp / 2 - 0.4))
    cuts = []
    for name, r in R.items():
        inf = info[name]
        o1 = FP._smooth(inf['o1'], 4.0); o2 = FP._smooth(inf['o2'], 4.0)
        zc, risers = FP.step_levels(r)
        inf['zc'] = zc; inf['risers'] = risers
        FP.corridor(B, r, zc, risers, o1, o2, inf['pave'], shoulder='gravel' if name.startswith(('senbon', 'lower')) else 'soil',
                    bank='forest', cut=cuts)
        inf['o1s'] = o1; inf['o2s'] = o2
    # torii
    for name, r in R.items():
        inf = info[name]
        dense_ranges = []
        recs = sorted(inf['recs'])
        for (s_, sz, dense) in recs:
            x, y, z, tx, ty = r.at(s_)
            k = r.idx(s_)
            yaw = math.atan2(ty, tx) - math.pi / 2
            base = r.z[k] + 0.03
            foot = min(inf['zc'][k] + 0.03, base) - 0.02
            T.template(sz).add(x, y, base, yaw, foot - base, foot - base, seed=int(rng.integers(0, 250)))
            T.count[sz] += 1
            sp = SIZES[sz][2]
            if not dense:
                c, s = math.cos(yaw), math.sin(yaw)
                T.feet += [(x - c * sp / 2, y - s * sp / 2, base), (x + c * sp / 2, y + s * sp / 2, base)]
            else:
                if dense_ranges and s_ - dense_ranges[-1][1] < 2.0 and abs(dense_ranges[-1][2] - sp) < 0.8:
                    dense_ranges[-1][1] = s_; dense_ranges[-1][2] = max(dense_ranges[-1][2], sp)
                else:
                    dense_ranges.append([s_, s_, sp])
        # blockers: continuous bands along the dense runs, squares at the sparse feet
        inner, outer = _band_widths(r, R, name)
        for (a, b, sp) in dense_ranges:
            if b - a < 0.5:
                continue
            # the walk map marks ~0.3 m (+ a cell) around block edges: keep the bands beyond the pillars
            if inner is None: FP.block_bands(B, r, [(a - 0.1, b + 0.1)], sp / 2 + 0.55, sp / 2 + 1.1)
            else: FP.block_bands(B, r, [(a - 0.1, b + 0.1)], inner, outer)
        inf['dense'] = dense_ranges
    FT.block_feet(B, T.feet)
    ntri = 0
    for sz, t in T.tpl.items():
        ntri += t.flush(B)
    T.ntri = ntri
    return T, info, cuts
