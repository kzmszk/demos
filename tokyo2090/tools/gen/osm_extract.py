"""Extract OSM features for the frame (+ margin) from the Geofabrik Kanto PBF into the Overpass-like JSON that
osm.load() reads (tagged nodes; ways with node ids + geometry; relations with members).
  python -m gen.osm_extract            -> ASSETS/osm/tokyo.json"""
import os, json
import osmium
from .frame import ASSETS, bbox_lonlat

PBF = os.path.join(ASSETS, 'osm', 'kanto-latest.osm.pbf')
OUT = os.path.join(ASSETS, 'osm', 'tokyo.json')

class H(osmium.SimpleHandler):
    def __init__(self, bb):
        super().__init__(); self.bb = bb; self.el = []; self.ways = set()
    def inside(self, lon, lat):
        a, b, c, d = self.bb
        return a <= lon <= c and b <= lat <= d
    def node(self, n):
        if not n.tags or not n.location.valid(): return
        if self.inside(n.location.lon, n.location.lat):
            self.el.append({'type': 'node', 'id': n.id, 'lat': n.location.lat, 'lon': n.location.lon, 'tags': {t.k: t.v for t in n.tags}})
    def way(self, w):
        geom = []; hit = False
        for nd in w.nodes:
            if not nd.location.valid(): return
            geom.append({'lon': nd.location.lon, 'lat': nd.location.lat})
            if not hit and self.inside(nd.location.lon, nd.location.lat): hit = True
        if not hit: return
        self.ways.add(w.id)
        self.el.append({'type': 'way', 'id': w.id, 'tags': {t.k: t.v for t in w.tags}, 'nodes': [nd.ref for nd in w.nodes], 'geometry': geom})
    def relation(self, r):
        t = {x.k: x.v for x in r.tags}
        if t.get('type') != 'multipolygon': return
        mem = [{'type': m.type, 'ref': m.ref, 'role': m.role} for m in r.members]
        if not any(m['type'] == 'w' and m['ref'] in self.ways for m in mem): return
        self.el.append({'type': 'relation', 'id': r.id, 'tags': t, 'members': mem})

if __name__ == '__main__':
    bb = bbox_lonlat(800.0)
    h = H(bb)
    h.apply_file(PBF, locations=True, idx='flex_mem')
    json.dump({'elements': h.el}, open(OUT, 'w'))
    import collections
    print(len(h.el), 'elements', collections.Counter(e['type'] for e in h.el), '->', OUT)
