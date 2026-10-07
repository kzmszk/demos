"""Ground of a tile: the terrain mesh (2 m grid from the GSI DEM, river beds lowered), the surface raster (0.5 m: what
the ground is made of, drawn by the ground program in the shader), water surfaces, generic road bridges.

Surface raster ids: materials.SURF.  The raster also feeds the walk map (walk.py)."""
import math
import numpy as np
import shapely
from shapely.geometry import box, Polygon, MultiPolygon, LineString, Point
from shapely.ops import unary_union
from PIL import Image, ImageDraw
from .materials import MAT, SID
from .osm import ROAD_RANK
from .mesh import triangulate

RES = 0.5            # surface raster (m / px)
GRID = 2.0           # terrain mesh spacing (m)

LANDUSE_SURF = {'forest': 'forest', 'wood': 'forest', 'scrub': 'forest', 'grass': 'grass', 'park': 'grass', 'garden': 'moss', 'grassland': 'grass',
                'meadow': 'grass', 'village_green': 'grass', 'cemetery': 'graves', 'grave_yard': 'graves', 'farmland': 'farm', 'farmyard': 'soil',
                'orchard': 'farm', 'religious': 'gravel', 'place_of_worship': 'gravel', 'parking': 'asphalt_lane', 'pitch': 'soil', 'playground': 'sand',
                'school': 'soil', 'construction': 'soil', 'brownfield': 'soil', 'railway': 'ballast', 'flowerbed': 'soil', 'kindergarten': 'soil',
                'university': 'concrete', 'industrial': 'concrete', 'commercial': 'concrete', 'retail': 'concrete'}
LANDUSE_ORDER = ['residential', 'commercial', 'retail', 'industrial', 'university', 'school', 'kindergarten', 'railway', 'religious', 'place_of_worship',
                 'cemetery', 'grave_yard', 'farmland', 'farmyard', 'orchard', 'grassland', 'meadow', 'forest', 'wood', 'scrub', 'park', 'grass', 'village_green',
                 'garden', 'pitch', 'playground', 'construction', 'brownfield', 'flowerbed', 'parking']
CAR = {'motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link', 'busway'}

def road_surface(r):
    s = r['surface']; hw = r['hw']
    if hw == 'steps': return 'stone_slab'
    if s in ('paving_stones', 'sett', 'cobblestone', 'unhewn_cobblestone', 'pebblestone'): return 'stone_sett'
    if s in ('unpaved', 'ground', 'dirt', 'compacted', 'earth', 'mud'): return 'soil'
    if s in ('gravel', 'fine_gravel'): return 'gravel'
    if s == 'wood': return 'wood_deck'
    if s == 'sand': return 'sand'
    if hw in CAR: return 'asphalt'
    if hw in ('footway', 'pedestrian', 'cycleway', 'corridor'):
        return 'sidewalk' if (r.get('footway') == 'sidewalk' or s in ('paved', 'concrete', 'concrete:plates', None)) else 'sidewalk'
    if hw in ('path', 'track', 'bridleway'): return 'soil' if s is None else 'sidewalk'
    return 'asphalt_lane'

class TileGround:
    def __init__(self, w, i, j, bounds):
        self.w = w; self.T = w.terrain
        from .frame import region_of
        self.region = region_of(i, j)
        x0, y0, x1, y1 = bounds
        self.b = bounds; self.R = box(*bounds)
        self.big = self.R.buffer(60.0)
        o = w.osm
        q = lambda lst, key='poly': [f for f in lst if f[key].intersects(self.big)]
        self.roads = [r for r in q(o['roads'], 'line') if not r['tunnel'] and r['layer'] >= 0 and r['hw'] != 'corridor']
        self.areas = q(o['areas'])
        self.landuse = q(o['landuse'])
        self.water = [f for f in q(o['water']) if not f['tags'].get('tunnel')]
        self.waterways = [f for f in q(o['waterways'], 'line') if not f['tunnel'] and f['ww'] in ('river', 'stream', 'canal', 'ditch', 'drain')]
        self.rails = [r for r in q(o['rails'], 'line') if not r['tunnel'] and r['rw'] in ('rail', 'light_rail', 'tram', 'narrow_gauge')]

    # ---------------------------------------------------------- shapes
    def road_polys(self):
        """[(rank, surface, polygon, road)] carriageways + automatic sidewalks on big roads; bridges are kept for their decks."""
        out = []
        for r in self.roads:
            w = max(1.0, r['width'])
            g = r['line'].buffer(w / 2, cap_style='flat' if r['hw'] in CAR else 'round', join_style='round')
            out.append((ROAD_RANK.get(r['hw'], 0), road_surface(r), g, r))
            if r['hw'] in CAR and ROAD_RANK.get(r['hw'], 0) >= 5 and r.get('sidewalk') not in ('no', 'none', 'separate') and not r['bridge']:
                sw = 3.5 if ROAD_RANK[r['hw']] >= 7 else 2.5
                out.append((-1, 'sidewalk', r['line'].buffer(w / 2 + sw, cap_style='flat').difference(g), r))
        return out

    def street_geom(self):
        """everything a facade can face as a street: roads, pedestrian areas, squares, parkings."""
        gs = [p for (_, _, p, r) in self.road_polys()] + [a['poly'] for a in self.areas] + [l['poly'] for l in self.landuse if l['kind'] in ('parking',)]
        return unary_union([g for g in gs if g.intersects(self.big)]) if gs else None

    def water_geom(self):
        gs = [f['poly'] for f in self.water if not f.get('pool')]
        for ww in self.waterways:
            wd = ww['width'] or {'river': 8.0, 'canal': 4.5, 'stream': 2.5, 'ditch': 1.2, 'drain': 1.2}[ww['ww']]
            gs.append(ww['line'].buffer(wd / 2, cap_style='flat'))
        return unary_union(gs).intersection(self.big) if gs else None

    # ---------------------------------------------------------- surface raster
    def surface(self, buildings):
        x0, y0, x1, y1 = self.b
        n = int(round((x1 - x0) / RES))
        img = Image.new('L', (n, n), SID['none'])
        dr = ImageDraw.Draw(img)
        def draw(g, sid):
            if g is None or g.is_empty: return
            for p in (g.geoms if hasattr(g, 'geoms') else [g]):
                if p.geom_type != 'Polygon' or p.is_empty: continue
                ex = [((x - x0) / RES, (y1 - y) / RES) for x, y in p.exterior.coords]
                if len(ex) >= 3: dr.polygon(ex, fill=sid)
                for r in p.interiors:
                    ii = [((x - x0) / RES, (y1 - y) / RES) for x, y in r.coords]
                    if len(ii) >= 3: dr.polygon(ii, fill=SID['none'])
        lu = sorted(self.landuse, key=lambda f: LANDUSE_ORDER.index(f['kind']) if f['kind'] in LANDUSE_ORDER else -1)
        for f in lu:
            s = LANDUSE_SURF.get(f['kind'])
            if s: draw(f['poly'].intersection(self.big), SID[s])
        wg = self.water_geom()
        draw(wg, SID['riverbed'])
        for r in self.rails:
            draw(r['line'].buffer(1.6, cap_style='flat').intersection(self.big), SID['ballast'])
        rp = sorted(self.road_polys(), key=lambda t: t[0])
        for rank, s, g, r in rp:
            if r['bridge']: continue
            draw(g.intersection(self.big), SID[s])
        for a in self.areas:
            t = a['tags']; s = t.get('surface')
            draw(a['poly'].intersection(self.big), SID['stone_sett'] if s in ('paving_stones', 'sett') else SID['soil'] if s in ('ground', 'dirt', 'unpaved') else SID['gravel'] if s in ('gravel', 'fine_gravel') else SID['stone_slab'] if a['kind'] == 'platform' else SID['sidewalk'])
        A = np.asarray(img, np.uint8)[::-1].copy()        # row 0 = south edge (y0), like the terrain grids
        self.riverside(A, wg)
        return A

    def riverside(self, A, wg):
        """the rivers' floodplains (the Kamo, the Takano, the Ōi): grass down to a pebbly edge and the riverside paths in
        decomposed granite (まさ土), as at the Kamo delta, all along the banks; the embankment slopes above them grass"""
        big = [f['poly'] for f in self.water if f['poly'].area > 15000 and not f.get('pool')]
        if not big or wg is None: return
        bw = shapely.unary_union(big)
        zone = bw.buffer(40.0).difference(bw).intersection(self.big)
        if zone.is_empty: return
        x0, y0, x1, y1 = self.b; n = A.shape[0]
        def mask(g):
            img = Image.new('L', (n, n), 0); dr = ImageDraw.Draw(img)
            for p in (g.geoms if hasattr(g, 'geoms') else [g]):
                if p.geom_type != 'Polygon' or p.is_empty: continue
                dr.polygon([((x - x0) / RES, (y1 - y) / RES) for x, y in p.exterior.coords], fill=255)
                for r in p.interiors: dr.polygon([((x - x0) / RES, (y1 - y) / RES) for x, y in r.coords], fill=0)
            return np.asarray(img)[::-1] > 0
        Z = mask(zone)
        if not Z.any(): return
        lvl = self.water_level(wg)
        jj, ii = np.nonzero(Z)
        X = x0 + (ii + 0.5) * RES; Y = y0 + (jj + 0.5) * RES
        zt = self.T(X, Y); zl = lvl(np.c_[X, Y]) if lvl is not None else zt
        flood = np.zeros_like(Z); flood[jj, ii] = zt < zl + 3.2
        none, grass = SID['none'], SID['grass']
        A[Z & ~flood & (A == none)] = grass                                    # the embankment slopes
        A[flood & np.isin(A, [none, SID['concrete'], SID['sand']])] = grass
        paths = [r['line'].buffer(max(r['width'], 2.5) / 2, cap_style='flat') for r in self.roads
                 if r['hw'] in ('footway', 'path', 'cycleway', 'track', 'bridleway') and not r['bridge']
                 and r['surface'] in (None, 'unpaved', 'ground', 'dirt', 'compacted', 'fine_gravel', 'gravel')]
        if paths:
            P = mask(shapely.unary_union(paths).intersection(self.big))
            A[flood & P] = SID['masa']
        edge = mask(bw.buffer(1.6).difference(bw).intersection(self.big))
        A[flood & edge & (A == grass)] = SID['riverbed']

    def paint(self, A, poly, sname):
        """paint a ground surface (materials.SURF name) into a surface raster (row 0 = south)"""
        x0, y0, x1, y1 = self.b; n = A.shape[0]
        img = Image.new('L', (n, n), 0); dr = ImageDraw.Draw(img)
        for p in (poly.geoms if hasattr(poly, 'geoms') else [poly]):
            if p.geom_type != 'Polygon': continue
            dr.polygon([((x - x0) / RES, (y1 - y) / RES) for x, y in p.exterior.coords], fill=255)
            for r in p.interiors: dr.polygon([((x - x0) / RES, (y1 - y) / RES) for x, y in r.coords], fill=0)
        m = np.asarray(img)[::-1] > 0
        A[m] = SID[sname]

    # ---------------------------------------------------------- water level field
    def water_level(self, wg):
        """water surface height at the polygon's points: DEM along the water's edge minus a little, spread inward."""
        if wg is None or wg.is_empty: return None
        pts = []
        for p in (wg.geoms if hasattr(wg, 'geoms') else [wg]):
            if p.geom_type != 'Polygon': continue
            L = p.exterior
            k = max(8, int(L.length / 3.0))
            pts += [L.interpolate(t, normalized=True).coords[0] for t in np.linspace(0, 1, k, endpoint=False)]
        if not pts: return None
        pts = np.array(pts)
        # the bank: sample a metre outside the water and take the lower of inside/outside
        z = self.T(pts[:, 0], pts[:, 1])
        if self.region not in (None, 'core'):
            # the enclaves (保津峡): a gorge's edge sits on the cliff; also look a little way into the water (the DEM there is the
            # interpolated water surface) and take the lowest.  The core keeps its levels as built.
            inner = []
            for d_ in (3.0, 8.0):
                sh = wg.buffer(-d_)
                if sh.is_empty: continue
                q_ = np.array([sh.boundary.interpolate(sh.boundary.project(Point(x, y))).coords[0] for x, y in pts])
                inner.append(self.T(q_[:, 0], q_[:, 1]))
            for zi in inner: z = np.minimum(z, zi)
        from scipy.spatial import cKDTree
        tree = cKDTree(pts)
        gorge = self.region == 'arashiyama'
        def f(q):
            q = np.atleast_2d(q)
            d, k = tree.query(q, k=min(12, len(pts)))
            w = 1.0 / np.maximum(d, 0.5) ** 2
            zl = (w * z[k]).sum(1) / w.sum(1) - 0.35
            if gorge:
                # 保津川 in its gorge: the DEM over the water is interpolated from the cliffs.  The river is ~35.8 m above
                # 葛野大堰 (x ~ -7880) and rises ~3 m per km upstream (Kameoka 80 m, 16 km away)
                g = q[:, 0] < -7700
                zl[g] = np.minimum(zl[g], 35.8 + np.maximum(-7880.0 - q[g, 0], 0) * 0.003)
            return zl
        return f

    # ---------------------------------------------------------- terrain mesh
    def terrain_mesh(self, mb, wg, wl, cut=None, grid=GRID):
        x0, y0, x1, y1 = self.b
        n = int(round((x1 - x0) / grid))
        xs = np.linspace(x0, x1, n + 1); ys = np.linspace(y0, y1, n + 1)
        X, Y = np.meshgrid(xs, ys)
        Z = self.T(X.ravel(), Y.ravel()).reshape(X.shape)
        if wg is not None and not wg.is_empty and wl is not None:
            inw = shapely.contains_xy(wg.buffer(0.5), X.ravel(), Y.ravel()).reshape(X.shape)
            if inw.any():
                zw = wl(np.stack([X[inw], Y[inw]], 1))
                Z[inw] = np.minimum(Z[inw], zw - 0.7)
        P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
        idx = np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
        a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel(); c = idx[1:, 1:].ravel(); d = idx[1:, :-1].ravel()
        # split along the shorter diagonal in height (follows ridges and gutters better)
        dz1 = np.abs(Z.ravel()[a] - Z.ravel()[c]); dz2 = np.abs(Z.ravel()[b] - Z.ravel()[d])
        alt = dz2 < dz1
        T1 = np.where(alt[:, None], np.stack([a, b, d], 1), np.stack([a, b, c], 1))
        T2 = np.where(alt[:, None], np.stack([b, c, d], 1), np.stack([a, c, d], 1))
        T = np.concatenate([T1, T2])
        if cut is not None and not cut.is_empty:
            C = P[T].mean(1)
            keep = ~shapely.contains_xy(cut, C[:, 0], C[:, 1])
            T = T[keep]
        # smooth normals from the grid
        gy, gx = np.gradient(Z, grid)
        N = np.stack([-gx.ravel(), -gy.ravel(), np.ones(P.shape[0])], 1); N /= np.linalg.norm(N, axis=1, keepdims=True)
        mb.add(P, T, N=N, UV=P[:, :2] - [x0, y0], mat=MAT['ground'], c0=(255, 255, 255, 0), c1=(0, 0, 0, 0))
        return Z

    def water_mesh(self, mb, wg, wl):
        if wg is None or wg.is_empty or wl is None: return
        g = wg.intersection(self.R)
        for p in (g.geoms if hasattr(g, 'geoms') else [g]):
            if p.geom_type != 'Polygon' or p.area < 1: continue
            rings = [list(p.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in p.interiors]
            V, T = triangulate(rings, max_area=40.0)
            if len(T) == 0: continue
            Z = wl(V)
            mb.add(np.c_[V, Z], T, N=np.tile([0, 0, 1.0], (len(V), 1)), UV=V, mat=MAT['water'], c0=(255, 255, 255, 0), c1=(0, 0, 0, 0))

    def bridges(self, mb):
        """generic road bridges: deck between the banks' heights, parapets."""
        out = []
        for r in self.roads:
            if not r['bridge']: continue
            line = r['line']
            if not line.intersects(self.R): continue
            cs = np.array(line.coords)
            za = float(self.T(cs[0, 0], cs[0, 1])); zc = float(self.T(cs[-1, 0], cs[-1, 1]))
            Lt = line.length
            if Lt < 3: continue
            w = max(2.0, r['width']) + (4.0 if r['hw'] in CAR and ROAD_RANK.get(r['hw'], 0) >= 5 else 0.6)
            k = max(2, int(Lt / 3.0))
            ts = np.linspace(0, Lt, k + 1)
            pts = np.array([line.interpolate(t).coords[0] for t in ts])
            camber = np.sin(ts / Lt * math.pi) * min(0.6, Lt * 0.01)
            zz = za + (zc - za) * ts / Lt + camber
            # skip bridges that are really embankments (deck right on the ground the whole way)
            zg = self.T(pts[:, 0], pts[:, 1])
            if (zz - zg).max() < 1.2: continue
            dirs = np.gradient(pts, axis=0); dirs /= np.maximum(np.linalg.norm(dirs, axis=1, keepdims=True), 1e-9)
            nrm = np.stack([-dirs[:, 1], dirs[:, 0]], 1)
            L_ = pts + nrm * w / 2; R_ = pts - nrm * w / 2
            top = []; UV = []
            for m in range(len(pts)):
                top += [(*L_[m], zz[m]), (*R_[m], zz[m])]; UV += [(ts[m], w / 2), (ts[m], -w / 2)]
            top = np.array(top); T = []
            for m in range(len(pts) - 1):
                a = 2 * m; T += [[a, a + 2, a + 3], [a, a + 3, a + 1]]
            T = np.array(T)
            fn = np.cross(top[T[:, 1]] - top[T[:, 0]], top[T[:, 2]] - top[T[:, 0]])
            if fn[:, 2].mean() < 0: T = T[:, ::-1]
            mb.add(top, T, N=np.tile([0, 0, 1.0], (len(top), 1)), UV=np.array(UV), mat=MAT['ground'], c0=(255, 255, 255, 0), c1=(0, 0, 0, SID['asphalt'] if r['hw'] in CAR else SID['stone_slab']))
            # underside + sides (concrete), parapets
            th = 1.1
            for side, S in ((1, L_), (-1, R_)):
                Q = []
                for m in range(len(pts)):
                    Q += [(*S[m], zz[m] + 1.0), (*S[m], zz[m] - th)]
                Q = np.array(Q); TT = []
                for m in range(len(pts) - 1):
                    a = 2 * m; TT += [[a, a + 1, a + 3], [a, a + 3, a + 2]]
                TT = np.array(TT)
                nn = np.c_[nrm * side, np.zeros(len(pts))].repeat(2, 0)
                fn2 = np.cross(Q[TT[:, 1]] - Q[TT[:, 0]], Q[TT[:, 2]] - Q[TT[:, 0]])
                if (fn2 * nn[TT[:, 0]]).sum(1).mean() < 0: TT = TT[:, ::-1]
                mb.add(Q, TT, N=nn, UV=np.c_[np.repeat(ts, 2), Q[:, 2]], mat=MAT['wall_concrete'], c0=(190, 188, 182, 30), c1=(0, 0, 0, 0))
            bot = top.copy(); bot[:, 2] -= th
            mb.add(bot, T[:, ::-1], N=np.tile([0, 0, -1.0], (len(bot), 1)), UV=np.array(UV), mat=MAT['wall_concrete'], c0=(160, 158, 152, 30), c1=(0, 0, 0, 0))
            out.append(dict(line=line, w=w, z=(za, zc), pts=pts, zz=zz))
        return out
