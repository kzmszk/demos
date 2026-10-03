"""OSM → local metric frame.  Origin = centre of the Vatican obelisk; x = east, y = north (metres)."""
import json, math
OSM = '/home/kazu/work/vatican-assets/osm/area.json'
LAT0, LON0 = 41.902168, 12.457380   # replaced at load by the obelisk centroid
R = 6378137.0

class OSMData:
    def __init__(self, path=OSM):
        d = json.load(open(path))
        self.nodes, self.ways, self.rels = {}, {}, {}
        for e in d['elements']:
            t = e['type']
            if t == 'node':
                if e['id'] in self.nodes and 'tags' not in e: continue
                self.nodes[e['id']] = e
            elif t == 'way':
                if e['id'] in self.ways and 'tags' not in e: continue
                self.ways[e['id']] = e
            else:
                if e['id'] in self.rels and 'tags' not in e: continue
                self.rels[e['id']] = e
        ob = self.ways[799694267]
        pts = [self.nodes[n] for n in ob['nodes'][:-1]]
        self.lat0 = sum(p['lat'] for p in pts) / len(pts)
        self.lon0 = sum(p['lon'] for p in pts) / len(pts)
        self.kx = math.cos(math.radians(self.lat0)) * R * math.pi / 180
        self.ky = R * math.pi / 180

    def xy(self, nid):
        n = self.nodes[nid]
        return ((n['lon'] - self.lon0) * self.kx, (n['lat'] - self.lat0) * self.ky)

    def ll2xy(self, lat, lon):
        return ((lon - self.lon0) * self.kx, (lat - self.lat0) * self.ky)

    def way_xy(self, wid):
        w = self.ways[wid]
        return [self.xy(n) for n in w['nodes'] if n in self.nodes]

    def rel_rings(self, rid):
        """outer/inner rings of a multipolygon relation (ways joined end to end)."""
        r = self.rels[rid]; out = {'outer': [], 'inner': []}
        segs = {'outer': [], 'inner': []}
        for m in r['members']:
            if m['type'] == 'way' and m['ref'] in self.ways:
                segs[m.get('role') or 'outer' if m.get('role') in ('outer', 'inner', '') else 'outer'].append(list(self.ways[m['ref']]['nodes']))
        for role, ss in segs.items():
            ss = [s for s in ss if s]
            while ss:
                ring = ss.pop(0)
                changed = True
                while ring[0] != ring[-1] and changed:
                    changed = False
                    for i, s in enumerate(ss):
                        if s[0] == ring[-1]: ring += s[1:]
                        elif s[-1] == ring[-1]: ring += s[::-1][1:]
                        elif s[-1] == ring[0]: ring = s[:-1] + ring
                        elif s[0] == ring[0]: ring = s[::-1][:-1] + ring
                        else: continue
                        ss.pop(i); changed = True; break
                out[role].append([self.xy(n) for n in ring if n in self.nodes])
        return out

def num(v, default=None):
    if v is None: return default
    try: return float(str(v).replace(',', '.').split()[0].rstrip('m'))
    except Exception: return default
