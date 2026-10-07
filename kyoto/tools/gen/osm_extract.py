"""Extract OSM features for boxes of the local frame from the Geofabrik Kansai PBF into the Overpass-like JSON that
osm.load() reads (tagged nodes; ways with node ids + geometry; relations with members).
  python -m gen.osm_extract OUT.json REGION [REGION ...]      (regions from gen.frame.REGIONS, + 600 m margin)"""
import sys, os, json
import osmium
from .frame import REGIONS, ASSETS, to_lonlat

PBF = os.path.join(ASSETS, 'osm', 'kansai-261004.osm.pbf')
MARGIN = 600.0

def boxes(names):
    out = []
    for n in names:
        a, b, c, d = REGIONS[n]
        lo0, la0 = to_lonlat(a - MARGIN, b - MARGIN); lo1, la1 = to_lonlat(c + MARGIN, d + MARGIN)
        lo2, la2 = to_lonlat(a - MARGIN, d + MARGIN); lo3, la3 = to_lonlat(c + MARGIN, b - MARGIN)
        out.append((float(min(lo0, lo2)), float(min(la0, la3)), float(max(lo1, lo3)), float(max(la1, la2))))
    return out

class H(osmium.SimpleHandler):
    def __init__(self, bb):
        super().__init__(); self.bb = bb; self.el = []; self.ways = set()
    def inside(self, lon, lat):
        return any(a <= lon <= c and b <= lat <= d for (a, b, c, d) in self.bb)
    def node(self, n):
        if not n.tags or not n.location.valid(): return
        if self.inside(n.location.lon, n.location.lat):
            self.el.append({'type': 'node', 'id': n.id, 'lat': n.location.lat, 'lon': n.location.lon, 'tags': {t.k: t.v for t in n.tags}})
    def way(self, w):
        geom = []
        hit = False
        for nd in w.nodes:
            if not nd.location.valid(): return
            geom.append({'lon': nd.location.lon, 'lat': nd.location.lat})
            if not hit and self.inside(nd.location.lon, nd.location.lat): hit = True
        if not hit: return
        self.ways.add(w.id)
        self.el.append({'type': 'way', 'id': w.id, 'tags': {t.k: t.v for t in w.tags}, 'nodes': [nd.ref for nd in w.nodes], 'geometry': geom})
    def relation(self, r):
        mem = [{'type': m.type, 'ref': m.ref, 'role': m.role} for m in r.members]
        if not any(m['type'] == 'w' and m['ref'] in self.ways for m in mem): return
        self.el.append({'type': 'relation', 'id': r.id, 'tags': {t.k: t.v for t in r.tags}, 'members': mem})

def main():
    out, names = sys.argv[1], sys.argv[2:]
    bb = boxes(names)
    h = H(bb)
    h.apply_file(PBF, locations=True, idx='flex_mem')
    json.dump({'bbox': bb, 'source': 'Geofabrik ' + os.path.basename(PBF), 'regions': names, 'elements': h.el}, open(out, 'w'))
    from collections import Counter
    print(out, Counter(e['type'] for e in h.el), bb)

if __name__ == '__main__':
    main()
