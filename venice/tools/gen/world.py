"""World model for Venice built from OSM: land, water, buildings (heights), streets, bridges.
Local frame: origin = Campanile di San Marco centroid, x east, y north, metres; water level z = 0."""
import os, sys, math, pickle, hashlib
import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid

from .osm import OSMData, num
from . import land as L

CACHE = '/home/kazu/work/venice-assets/cache'
GROUND_Z = 1.10          # fondamenta / calli
PIAZZA_Z = 0.90          # Piazza San Marco is the lowest ground
WATER_BOTTOM = -1.8

def h32(*a):
    """deterministic hash in [0,1) — mirrors web/hash.js"""
    s = '|'.join(str(x) for x in a).encode()
    return int(hashlib.blake2b(s, digest_size=4).hexdigest(), 16) / 2**32

def polys_of(g):
    if g is None or g.is_empty: return []
    if g.geom_type == 'Polygon': return [g]
    if g.geom_type in ('MultiPolygon', 'GeometryCollection'):
        out = []
        for x in g.geoms: out += polys_of(x)
        return out
    return []

class Building:
    __slots__ = ('id', 'tags', 'poly', 'H', 'levels', 'kind', 'z0', 'seed', 'hero', 'roof', 'hero_cut', 'roof_h', 'parent', 'pmat')
    def __init__(self, bid, tags, poly):
        self.id = bid; self.tags = tags; self.poly = poly
        self.seed = h32('b', bid); self.hero = False; self.hero_cut = None
        self.kind = 'house'; self.H = 12.0; self.levels = 3; self.z0 = GROUND_Z; self.roof = 'hipped'
        self.roof_h = None; self.parent = None; self.pmat = None

def _height(b):
    t = b.tags
    kind = t.get('building', 'yes')
    if t.get('man_made') in ('tower', 'campanile') or kind in ('bell_tower', 'tower'): b.kind = 'tower'
    elif kind in ('church', 'cathedral', 'chapel', 'basilica'): b.kind = 'church'
    elif kind in ('roof', 'canopy', 'carport'): b.kind = 'roof'
    elif kind in ('industrial', 'warehouse', 'hangar', 'shed'): b.kind = 'shed'
    elif kind in ('palace',) or t.get('historic') == 'palace' or 'palazzo' in t.get('name', '').lower() or t.get('name', '').startswith("Ca'"): b.kind = 'palazzo'
    else: b.kind = 'house'
    h = num(t.get('height')); lv = num(t.get('building:levels'))
    r = b.seed
    if b.kind == 'tower':
        b.H = h if h and h > 15 else 38 + 20 * r; b.roof = 'pyramid'; b.levels = 0; return
    if b.kind == 'roof':
        b.H = 3.5; b.levels = 1; b.roof = 'flat'; return
    if lv and lv >= 1:
        b.levels = int(lv)
    elif h and h > 3:
        b.levels = max(1, int(round((h - 1.0) / 3.4)))
    else:
        a = b.poly.area
        if b.kind == 'church': b.levels = 0
        elif a < 25: b.levels = 1 if r < 0.6 else 2
        else: b.levels = 2 if r < 0.08 else 3 if r < 0.45 else 4 if r < 0.82 else 5 if r < 0.96 else 6
    if b.kind == 'church':
        b.H = h if h and h > 8 else 17 + 8 * r; b.roof = 'gable'; return
    gf = 4.0 if b.kind != 'palazzo' else 4.6
    up = 3.25 if b.kind != 'palazzo' else 4.0
    b.H = h if (h and h > 3 and not lv) else gf + max(0, b.levels - 1) * up + 0.45
    b.roof = 'flat' if t.get('roof:shape') == 'flat' else 'hipped'

class World:
    def __init__(self):
        self.o = OSMData()
        self.land = L.land(self.o)
        self.land_polys = polys_of(self.land)
        self.buildings = []
        for wid, w in self.o.ways.items():
            t = w.get('tags', {})
            if 'building' in t and w['nodes'][0] == w['nodes'][-1] and len(w['nodes']) > 3:
                if t.get('building') in ('no',) or t.get('layer', '0').startswith('-'): continue
                p = make_valid(Polygon(self.o.way_xy(wid)))
                for q in polys_of(p):
                    if q.area > 1.5: self.buildings.append(Building(f'w{wid}', t, q))
        for rid, r in self.o.rels.items():
            t = r.get('tags', {})
            if 'building' in t and t.get('type') == 'multipolygon':
                rr = self.o.rel_rings(rid)
                g = unary_union([make_valid(Polygon(x)) for x in rr['outer'] if len(x) > 2])
                if rr['inner']: g = g.difference(unary_union([make_valid(Polygon(x)) for x in rr['inner'] if len(x) > 2]))
                for q in polys_of(g):
                    if q.area > 1.5: self.buildings.append(Building(f'r{rid}', t, q))
        for b in self.buildings: _height(b)
        # piers are not buildings; the floating ones, and the stops and ships drawn as buildings in the water, become
        # pontoons with cabins and gangways, and boats (pontoons.py)
        self.piers = [b for b in self.buildings if b.tags.get('man_made') == 'pier']
        self.buildings = [b for b in self.buildings if b.tags.get('man_made') != 'pier']
        from . import pontoons
        self.stops, self.ships = pontoons.collect(self)
        # OSM 3D parts replace (or extend) the buildings they belong to
        self.btree = STRtree([b.poly for b in self.buildings])
        from . import parts
        self.nparts = parts.apply(self, Building, GROUND_Z)
        # calli drawn through outlines: trim buildings back from them, or make them sottoporteghi (streets.py)
        from . import streets
        self.soto, self.ntrim = streets.apply(self, parts.HERO_PARENTS, GROUND_Z)
        self.soto_by = {}
        for (sg, k) in self.soto: self.soto_by.setdefault(self.buildings[k].id, []).append(sg)
        # overlapping footprints: keep the larger; drop slivers fully inside others
        self.btree = STRtree([b.poly for b in self.buildings])
        self.bidx = {b.id: i for i, b in enumerate(self.buildings)}
        self.water = None

    def __getstate__(self):
        d = dict(self.__dict__); d.pop('btree', None); return d

    def __setstate__(self, d):
        self.__dict__.update(d)
        self.btree = STRtree([b.poly for b in self.buildings])
        shapely.prepare(self.land)

    def building_at(self, x, y, skip=None):
        p = Point(x, y)
        for i in self.btree.query(p):
            b = self.buildings[i]
            if b is not skip and b.poly.contains(p): return b
        return None

    def is_land(self, x, y):
        return self.land.contains(Point(x, y))

def load(force=False):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, 'world.pkl')
    if os.path.exists(f) and not force:
        return pickle.load(open(f, 'rb'))
    w = World()
    pickle.dump(w, open(f, 'wb'))
    return w

if __name__ == '__main__':
    import time
    t = time.time(); w = load(force=True)
    print('world', len(w.buildings), 'buildings', len(w.piers), 'piers', f'{time.time()-t:.1f}s')
    import collections
    print(collections.Counter(b.kind for b in w.buildings))
    print(collections.Counter(b.levels for b in w.buildings).most_common(10))
