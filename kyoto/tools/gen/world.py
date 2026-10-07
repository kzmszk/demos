"""The Kyoto world: terrain, PLATEAU buildings (with OSM tags), OSM roads / water / landuse / trees / points, hero sites.
World() is cached (ASSETS/cache/world.pkl)."""
import os, pickle, glob, math, time, hashlib
import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon, box, Point, LineString
from shapely.ops import unary_union
from .frame import ASSETS, X0, Y0, X1, Y1, REGIONS
from .dem import Terrain
from . import osm as OSM

CACHE = os.path.join(ASSETS, 'cache', 'world.pkl')
MARGIN = 150.0

def h32(*a):
    return int(hashlib.md5('|'.join(map(str, a)).encode()).hexdigest()[:8], 16)

def rnd(*a):
    return h32(*a) / 2 ** 32

# hero sites: OSM polygons whose generic buildings are replaced by hand-built models (Blender)
HERO_OSM = {'kiyomizu': [336641107, 339352245], 'sanjusangendo': [31842037], 'eikando': [859305371], 'ginkakuji': [105817561],
            'yasaka_shrine': [328903218], 'hokanji': [371717423]}

class Building:
    __slots__ = ('id', 'poly', 'z0', 'z1', 'h', 'st', 'struct', 'use', 'year', 'cls', 'lod2', 'tags', 'seed', 'hero', 'kind', 'zone', 'idx', '_L', '_zg')
    def __init__(self, **k):
        for s in self.__slots__: setattr(self, s, k.get(s))

def _footprint(b):
    """2D footprint: LOD2 ground surface if any, else the lod0 roof edge."""
    polys = []
    src = b['lod2'].get('G') if b['lod2'] else None
    if src:
        for rings in src:
            if len(rings[0]) >= 3: polys.append(Polygon(rings[0][:, :2], [r[:, :2] for r in rings[1:] if len(r) >= 3]))
    if not polys:
        for rings in b['edge']:
            if len(rings[0]) >= 3: polys.append(Polygon(rings[0], [r for r in rings[1:] if len(r) >= 3]))
    if not polys: return None
    g = unary_union([p if p.is_valid else p.buffer(0) for p in polys])
    if g.is_empty: return None
    if g.geom_type == 'MultiPolygon': g = max(g.geoms, key=lambda p: p.area)
    return g

def classify(b, tags):
    """kind of building for the generator: 'shrine' / 'temple' (OSM), 'trad' (wooden, low, old: machiya / old houses),
    'house' (wooden or light steel, low), 'mid' (RC/steel mid-rise), 'tall', 'shed', 'station'"""
    bt = (tags or {}).get('building')
    if bt in ('temple', 'shrine') or (tags or {}).get('amenity') == 'place_of_worship': return bt if bt in ('temple', 'shrine') else 'temple'
    if bt == 'train_station': return 'station'
    h = b['h'] or 0.0; st = b['st'] or 0; s = b['struct']; y = b['year'] or 0
    if b['cls'] in (3003, 3004) or (h < 3.2 and st <= 1): return 'shed'
    if s in (602, 603, 606) or h > 14 or st >= 4: return 'tall' if (h > 31 or st >= 10) else 'mid'
    if s == 601 or (s in (0, 611) and h < 10.5):
        if 1000 < y < 1960: return 'trad'
        return 'house' if h < 10.5 else 'mid'
    if s in (604, 605): return 'house' if (h < 9.5 and st <= 2) else 'mid'
    return 'house' if h < 9 else 'mid'

def terrain_forest(T, landuse, regions=('kinkaku', 'arashiyama'), cell=10.0):
    """forest that OSM does not draw (e.g. 嵐山 itself), as in tools/far_build.py: unbuilt land that is steep (> 14 deg) or well above the
    valley floor (> 35 m over the lowest ground within ~1.5 km), outside every OSM landuse area.  Only for the western enclaves, so the
    core keeps exactly what it was built with.  -> landuse entries {kind: 'forest', source: terrain}"""
    import cv2
    from scipy import ndimage
    out = []
    for k, rn in enumerate(regions):
        a, b, c, d = REGIONS[rn]
        xs = np.arange(a - 200, c + 200, cell); ys = np.arange(b - 200, d + 200, cell)
        X, Y = np.meshgrid(xs, ys)
        Z = T(X.ravel(), Y.ravel()).reshape(X.shape)
        gy, gx = np.gradient(Z, cell)
        slope = np.degrees(np.arctan(np.hypot(gx, gy)))
        floor = ndimage.minimum_filter(ndimage.uniform_filter(Z, 5), size=int(1500 / cell))
        m = (ndimage.uniform_filter(slope, 3) > 14.0) | (Z - floor > 35.0)
        # not where OSM already says what the land is (towns, fields, parks, temples ...)
        others = unary_union([f['poly'] for f in landuse if f['poly'].intersects(box(a, b, c, d))])
        if not others.is_empty:
            img = np.zeros(m.shape, np.uint8)
            for p in (others.geoms if hasattr(others, 'geoms') else [others]):
                if p.geom_type != 'Polygon': continue
                ring = np.array([((x - xs[0]) / cell, (y - ys[0]) / cell) for x, y in p.exterior.coords], np.int32)
                cv2.fillPoly(img, [ring], 1)
            m &= img == 0
        m = ndimage.binary_opening(m, iterations=2)
        lab, n = ndimage.label(m)
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.nonzero(sizes * cell * cell > 4000)[0])
        cs, hier = cv2.findContours(keep.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        polys = []
        if hier is not None:
            for ci, cc in enumerate(cs):
                if hier[0][ci][3] != -1 or len(cc) < 4: continue
                ext = [(xs[0] + p[0][0] * cell, ys[0] + p[0][1] * cell) for p in cc]
                holes = [[(xs[0] + p[0][0] * cell, ys[0] + p[0][1] * cell) for p in cs[h]] for h in range(len(cs)) if hier[0][h][3] == ci and len(cs[h]) >= 4]
                pg = Polygon(ext, holes).buffer(0).simplify(cell * 0.6)
                if not pg.is_empty: polys.append(pg)
        for q, pg in enumerate(polys):
            for pp in (pg.geoms if hasattr(pg, 'geoms') else [pg]):
                if pp.geom_type == 'Polygon' and pp.area > 4000:
                    out.append(dict(id=-(9_000_000_000 + k * 100_000 + len(out)), kind='forest', poly=pp, tags={'landuse': 'forest', 'source': 'terrain'}))
    print('terrain forest', len(out), 'areas', round(sum(f['poly'].area for f in out) / 1e6, 2), 'km2', flush=True)
    return out

class World:
    def __init__(self):
        t0 = time.time()
        self.terrain = Terrain()
        self.osm = OSM.load()
        self.osm['landuse'] += terrain_forest(self.terrain, self.osm['landuse'])
        area = unary_union([box(a - MARGIN, b - MARGIN, c + MARGIN, d + MARGIN) for (a, b, c, d) in REGIONS.values()])
        shapely.prepare(area)
        # hero sites
        self.sites = {}
        lu = {f['id']: f for f in self.osm['landuse']}
        for name, ids in HERO_OSM.items():
            g = unary_union([lu[i]['poly'] for i in ids if i in lu])
            if not g.is_empty: self.sites[name] = g
        # OSM building tags by location
        ob = [f for f in self.osm['buildings'] if not f['part']]
        otree = shapely.STRtree([f['poly'] for f in ob])
        bl = []
        for fn in sorted(glob.glob(os.path.join(ASSETS, 'cache', 'plateau', '*.pkl'))):
            for b in pickle.load(open(fn, 'rb')):
                fp = _footprint(b)
                if fp is None or fp.area < 2.0: continue
                c = fp.representative_point()
                if not area.contains(c): continue
                tags = None
                hit = otree.query(c, predicate='within')
                if len(hit):
                    best = max(hit, key=lambda k: ob[k]['poly'].intersection(fp).area)
                    tags = ob[best]['tags']
                kind = classify(b, tags)
                bb = Building(id=b['id'], poly=fp, z0=b['z0'] if b['z0'] is not None else float(self.terrain(c.x, c.y)), z1=b['z1'], h=b['h'] or max(3.0, (b['z1'] or 0) - (b['z0'] or 0)),
                              st=b['st'], struct=b['struct'], use=b['use'], year=b['year'], cls=b['cls'], lod2=b['lod2'] or None, tags=tags or {}, seed=rnd(b['id']),
                              hero=None, kind=kind)
                bl.append(bb)
        for i, b in enumerate(bl): b.idx = i
        self.buildings = bl
        self.btree = shapely.STRtree([b.poly for b in bl])
        for name, g in self.sites.items():
            for k in self.btree.query(g, predicate='intersects'):
                b = bl[k]
                if g.contains(b.poly.representative_point()): b.hero = name
        print(f'world: {len(bl)} buildings ({sum(1 for b in bl if b.lod2)} LOD2), hero sites {[(n, sum(1 for b in bl if b.hero == n)) for n in self.sites]} {time.time()-t0:.1f}s', flush=True)

def load(force=False):
    deps = [OSM.CACHE, __file__, os.path.join(ASSETS, 'build', 'dem_core.npz')]
    if not force and os.path.exists(CACHE) and all(os.path.getmtime(CACHE) > os.path.getmtime(p) for p in deps):
        return pickle.load(open(CACHE, 'rb'))
    w = World()
    pickle.dump(w, open(CACHE, 'wb'), protocol=5)
    return w

if __name__ == '__main__':
    import collections
    w = load(force=True)
    print(collections.Counter(b.kind for b in w.buildings))
