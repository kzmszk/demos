"""東福寺 洗玉澗: the maple ravine north of the 方丈 from the 臥雲橋 (west) to the 偃月橋 (east).

The GSI 5 m DEM smooths the ravine into a broad V: the site cuts the generic terrain inside VALLEY and models its own
ground (0.75 m grid) with a stream channel carved along the OSM waterways (stone revetments, a stepped bed with small
weirs so every pool of water is flat), the valley-floor paths and stone steps of the 通天橋 loop walk, the little
bridge over the stream, rocks, and the 通天もみじ: a dense canopy of maples whose tops reach the bridge decks.
World coordinates (x east, y north, z T.P.)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union
from jk import prim
from sites import tofukuji_lib as L
from sites import tofukuji_ekit as EK

# the generic terrain is removed inside VALLEY (S.cut); the own ground covers VALLEY.buffer(EDGE) (lifted 3 cm outside)
VALLEY = [(1240, -934), (1262, -936), (1283.2, -934.6), (1290.6, -936.5), (1290, -990), (1300, -996), (1340, -996), (1352.3, -994),
          (1353.0, -962), (1354.2, -960.6), (1361.5, -960.6), (1385, -960.3), (1390, -957.8), (1416, -958.8), (1430, -962), (1440, -970),
          (1452, -986), (1466, -990), (1482, -996), (1482, -968), (1470, -960), (1456, -948), (1446, -935), (1428, -916), (1408, -906),
          (1388, -903.5), (1364, -902.5), (1362.8, -929.6), (1356, -929.6), (1355, -922), (1344, -916), (1336, -912.5), (1306, -912.5),
          (1290.6, -911), (1283.2, -911.0), (1262, -908), (1240, -910)]
EDGE = 1.6
RES = 0.75
HW = 1.15                   # half width of the stream channel (m)
X_IN, X_OUT = 1482.0, 1240.0  # the stream enters / leaves the modelled valley

# OSM ways of the valley walk (paths and steps), drawn on the own ground
PATHS = [768987596, 775463875, 768987595, 902014325, 902014327, 775670786, 781179142, 781179143, 775670787, 902014345, 901989777, 901989775,
         901989774, 893922127, 902014339, 902014340, 902014332]
STEPS = [768987597, 768987598, 902014326, 781179141, 781179144, 902014346, 901989780, 901989776, 902014333, 902014338, 902014341, 902014342]

class Valley:
    def __init__(self, S):
        self.S = S
        self.poly = Polygon(VALLEY).buffer(0)
        self.region = self.poly.buffer(EDGE)
        self._stream()
        self._paths()

    # ------------------------------------------------------------------ stream centreline and bed
    def _stream(self):
        S = self.S
        a = L.osm_line(S, 83332572); b = L.osm_line(S, 750993439)
        line = np.concatenate([a, b[1:]])                     # east (upstream) -> west (downstream)
        ln = LineString(line)
        clip = ln.intersection(shapely.geometry.box(X_OUT - 8, -1060, X_IN + 8, -880))
        if clip.geom_type == 'MultiLineString': clip = max(clip.geoms, key=lambda g: g.length)
        P = np.array(clip.coords)
        if P[0, 0] < P[-1, 0]: P = P[::-1]
        P = L.chaikin(P, 3)
        P, s = L.resample(P, 0.5)
        self.cl = P; self.s = s
        self.line = LineString(P)
        # bed: running min of the DEM around the centreline, monotonic downstream, 0.8 m under it
        z = S.ground(P[:, 0], P[:, 1])
        k = 6
        zm = np.array([z[max(0, i - k):i + k + 1].min() for i in range(len(z))]) - 0.8
        zm = np.minimum.accumulate(zm)                      # never rises downstream
        # stepped bed: weirs where the bed dropped 0.38 m since the last weir
        weirs = []; level = []
        zc = zm[0]
        for i in range(len(zm)):
            if zc - zm[i] >= 0.38:
                weirs.append(i); zc = zm[i]
        self.weir_idx = weirs
        bounds = [0] + weirs + [len(zm) - 1]
        bed = np.zeros(len(zm)); wl = np.zeros(len(zm))
        for a_, b_ in zip(bounds[:-1], bounds[1:]):
            crest = zm[b_] + 0.38 + 0.05
            bed[a_:b_ + 1] = zm[b_] - 0.12
            wl[a_:b_ + 1] = crest - 0.08
        self.bed = bed; self.wl = wl; self.pool_bounds = bounds
        # fade the carve near the ends of the modelled valley
        xs = P[:, 0]
        self.fade = np.clip((xs - X_OUT) / 10.0, 0, 1) * np.clip((X_IN - xs) / 10.0, 0, 1)

    def at(self, X, Y):
        """(distance to the centreline, index of the nearest centreline sample) for arrays"""
        pts = shapely.points(np.ravel(X), np.ravel(Y))
        d = shapely.distance(self.line, pts)
        t = shapely.line_locate_point(self.line, pts)
        i = np.clip(np.searchsorted(self.s, t), 0, len(self.s) - 1)
        return d.reshape(np.shape(X)), i.reshape(np.shape(X))

    def zfn(self, X, Y):
        """the own valley ground: the DEM with the stream channel carved in; DEM + 3 cm outside the cut"""
        X = np.asarray(X, float); Y = np.asarray(Y, float)
        D = self.S.ground(X, Y)
        d, i = self.at(X, Y)
        bed = self.bed[i]; f = self.fade[i]
        rise = np.where(d < HW, 0.0, 0.95 * np.clip((d - HW) / 0.35, 0, 1) + 0.55 * np.maximum(d - HW - 0.35, 0))
        zc = bed + rise
        Z = np.where(f > 0, np.minimum(D, D * (1 - f) + np.minimum(D, zc) * f), D)
        ins = shapely.contains_xy(self.poly, X, Y)
        return np.where(ins, Z, D + 0.03)

    # ------------------------------------------------------------------ paths
    def _paths(self):
        S = self.S
        segs = []; steps = []
        for wid in PATHS:
            try: segs.append(L.osm_line(S, wid))
            except KeyError: pass
        for wid in STEPS:
            try: steps.append(L.osm_line(S, wid))
            except KeyError: pass
        self.path_lines = segs; self.step_lines = steps
        g = [LineString(p).buffer(0.9) for p in segs if len(p) > 1] + [LineString(p).buffer(0.95) for p in steps if len(p) > 1]
        self.path_poly = unary_union(g).intersection(self.region) if g else Polygon()

    def surf(self, X, Y):
        d, i = self.at(X, Y)
        Z = self.zfn(X, Y)
        bed = self.bed[i]
        out = np.full(np.shape(X), L.SID['forest'])
        out = np.where((Z - bed < 2.2) & (d < 7.0), L.SID['moss'], out)
        out = np.where(d < HW + 0.45, L.SID['riverbed'], out)
        onp = shapely.contains_xy(self.path_poly, X, Y) if not self.path_poly.is_empty else np.zeros(np.shape(X), bool)
        out = np.where(onp & (d > HW + 0.3), L.SID['soil'], out)
        return out

    # ------------------------------------------------------------------ build
    def build_ground(self, B):
        S = self.S
        wmask = lambda x, y: self.at(x, y)[0] < HW + 0.15
        L.ground_mesh(B, S, self.region, res=RES, surf_fn=self.surf, zfn=self.zfn, walk=True, walk_mask=wmask)
        S.cut.append([list(map(float, p)) for p in self.poly.exterior.coords])

    def build_stream(self, B, skip=None):
        """flat pools between weirs, weir stones, revetment stones along both banks, a few stones in the bed; a blocker
        over the water"""
        P = self.cl; s = self.s
        N = np.gradient(P, axis=0); N /= np.linalg.norm(N, axis=1, keepdims=True); N = np.c_[-N[:, 1], N[:, 0]]
        rng = np.random.default_rng(11)
        ok = self.fade > 0.05
        for a_, b_ in zip(self.pool_bounds[:-1], self.pool_bounds[1:]):
            idx = [i for i in range(a_, b_ + 1) if ok[i]]
            if len(idx) < 2: continue
            w = self.wl[idx[0]]
            Lr = P[idx] + N[idx] * (HW + 0.25); Rr = P[idx] - N[idx] * (HW + 0.25)
            ring = np.concatenate([Lr, Rr[::-1]])
            pg = Polygon(ring).buffer(0)
            if pg.area < 0.3: continue
            EK.water(B, pg, w)
        # weirs: a row of stones across the channel at each weir
        for i in self.weir_idx:
            if not ok[i]: continue
            for t in np.linspace(-HW - 0.2, HW + 0.2, 5):
                c = P[i] + N[i] * t
                L.stone(B, (c[0], c[1], self.wl[i] - 0.05), 0.32, 9000 + i * 7 + int(t * 10), flat=0.75, sub=1, sink=0.35)
        # revetment stones (石積) on both banks
        k = 0
        for i in range(0, len(P), 3):
            if not ok[i]: continue
            for sg in (-1, 1):
                c = P[i] + N[i] * sg * (HW + 0.15 + rng.uniform(-0.05, 0.1))
                sz = rng.uniform(0.32, 0.5)
                L.stone(B, (c[0], c[1], self.bed[i] + sz * 0.6), sz, 7000 + k, flat=1.1, sub=1, sink=0.3, mat='stone')
                k += 1
                if rng.random() < 0.55:
                    c2 = P[i] + N[i] * sg * (HW + 0.45)
                    L.stone(B, (c2[0], c2[1], self.bed[i] + 0.95), rng.uniform(0.3, 0.45), 7500 + k, flat=0.9, sub=1, sink=0.3,
                            mat='moss_mound' if rng.random() < 0.4 else 'stone')
            if rng.random() < 0.18:     # a stone in the water
                c = P[i] + N[i] * rng.uniform(-0.5, 0.5)
                L.stone(B, (c[0], c[1], self.wl[i]), rng.uniform(0.2, 0.35), 8000 + i, flat=0.7, sub=1, sink=0.4)
        # keep walkers out of the water (the walk map is 2.5D: no blockers under the bridge decks)
        strip = self.line.buffer(HW + 0.1, cap_style='flat').intersection(self.poly)
        if skip is not None: strip = strip.difference(skip)
        for g in (strip.geoms if hasattr(strip, 'geoms') else [strip]):
            if g.area < 0.5: continue
            ext = np.array(g.exterior.coords)[:-1]
            L.poly_flat(B, ext, 0.0, 'stone', tag='block')

    def build_paths(self, B):
        """stone steps along the OSM steps of the valley walk; stepping stones / slabs at the stream crossing"""
        class GS:            # the own ground for the kit-copy helpers that call S.ground
            pass
        gs = GS(); gs.ground = lambda x, y: self.zfn(x, y)
        for st in self.step_lines:
            if len(st) < 2: continue
            try: EK.terrain_steps(B, gs, st, 1.5, rise=0.16, rail=None, curb=False)
            except Exception as e: print('valley steps', e)
        # the little bridge over the stream (OSM 775670787): two granite slabs on stones
        try:
            br = L.osm_line(self.S, 775670787)
        except KeyError:
            br = None
        if br is not None:
            a = br[0]; b = br[-1]
            d = (b - a) / np.linalg.norm(b - a)
            a2 = a - d * 1.2; b2 = b + d * 1.2
            za = float(self.zfn(*a2)); zb = float(self.zfn(*b2))
            z = max(za, zb) + 0.05
            EK.slab_bridge(B, self.S, a2, b2, z, w=1.3)
            for p in (a2, b2):
                L.stone(B, (p[0], p[1], z - 0.25), 0.55, int(p[0] * 7), flat=0.8, sub=1, sink=0.2)

    # ------------------------------------------------------------------ trees
    def plant(self, B, keep_out, deck_z=47.8, n_max=760, spacing=4.1, seed=5, views=()):
        """the 通天もみじ: maples over the whole ravine (tops near the bridge decks), a few pines, oaks and cedars on the
        rims; keep_out: shapely geometry (bridges, corridors, buildings)"""
        S = self.S
        rng = np.random.default_rng(seed)
        free = self.poly.difference(keep_out).difference(self.line.buffer(HW + 0.6))
        x0, y0, x1, y1 = self.poly.bounds
        pts = []
        tries = 0
        cell = spacing / math.sqrt(2)
        grid = {}
        while len(pts) < n_max and tries < 60000:
            tries += 1
            x = rng.uniform(x0, x1); y = rng.uniform(y0, y1)
            if not free.contains(Point(x, y)): continue
            gx, gy = int(x // cell), int(y // cell)
            bad = False
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    q = grid.get((gx + dx, gy + dy))
                    if q and (q[0] - x) ** 2 + (q[1] - y) ** 2 < spacing ** 2 * rng.uniform(0.75, 1.0): bad = True; break
                if bad: break
            if bad: continue
            grid[(gx, gy)] = (x, y); pts.append((x, y))
        out = []
        for (x, y) in pts:
            z = float(self.zfn(x, y))
            d, i = self.at(np.array([x]), np.array([y])); d = float(d[0]); bed = float(self.bed[int(i[0])])
            depth = z - bed
            r = rng.random()
            if depth > 6.5 and r < 0.10: sp = 'sugi'
            elif depth > 5.5 and r < 0.16: sp = 'kashi'
            elif r < 0.06: sp = 'matsu'
            elif r < 0.08: sp = 'keyaki'
            else: sp = 'momiji'
            dk = float(keep_out.distance(Point(x, y))) if not keep_out.is_empty else 99.0
            if sp == 'momiji':
                # near the bridges the canopy stays just under the deck (one looks down on it from the 舞台); further off it rises
                top = deck_z + rng.uniform(-2.8, 0.6) + 2.0 * min(max((dk - 12.0) / 20.0, 0.0), 1.0)
                top = min(top, z + rng.uniform(7.0, 11.5))
                sc = float(np.clip((top - z) / 6.5, 0.75, 1.75))
            elif sp == 'sugi': sc = rng.uniform(0.75, 1.0)
            elif sp == 'matsu': sc = rng.uniform(0.9, 1.3)
            else: sc = rng.uniform(0.7, 1.0)
            # keep the classic sightlines open (e.g. 臥雲橋 -> 通天橋): crowns stay under the line
            H0 = {'momiji': 6.5, 'sugi': 23.0, 'matsu': 7.5, 'kashi': 11.0, 'keyaki': 16.0}[sp]
            skip = False
            # crowns may brush the bridges and corridors (1 m) but not fill them
            Rc = {'momiji': 0.62, 'sugi': 0.17, 'matsu': 0.45, 'kashi': 0.48, 'keyaki': 0.46}[sp] * H0
            if Rc * sc > dk + 1.0:
                if z + H0 * sc < deck_z - 0.5: pass
                else:
                    sc = (dk + 1.0) / Rc
                    if sc < 0.5: continue
            for (eye, tgt, hw) in views:
                e = np.asarray(eye, float); t_ = np.asarray(tgt, float)
                d2 = t_[:2] - e[:2]; Lv = float(np.linalg.norm(d2)); d2 /= Lv
                rel = np.array([x, y]) - e[:2]
                tt = float(rel @ d2); lat = abs(float(rel @ np.array([-d2[1], d2[0]])))
                if tt < -3 or tt > Lv - 4: continue
                if lat > hw + 0.35 * H0 * sc: continue
                if tt < 9 or float(np.hypot(x - e[0], y - e[1])) < 0.62 * H0 * sc + 1.5: skip = True; break
                zl = e[2] + (t_[2] - e[2]) * tt / Lv - 0.6
                if sp != 'momiji' and z + H0 * sc > zl: skip = True; break
                sc = min(sc, (zl - z) / H0)
                if sc < 0.5: skip = True; break
            if skip: continue
            B.tree(sp, x, y, z - 0.1, sc, rng.uniform(0, 2 * math.pi))
            out.append((sp, x, y, z))
        return out
