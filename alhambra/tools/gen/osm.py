"""OpenStreetMap (ODbL) extract of Granada, downloaded via Overpass to ASSETS/osm/granada.json,
parsed into shapely geometry in the local frame and cached."""
import json, os, pickle
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union
from shapely.validation import make_valid
from frame import local, ASSETS

def _ring(geom):
    return [local(p['lon'], p['lat']) for p in geom if p]

def _poly(outers, inners=()):
    polys = []
    for o in outers:
        if len(o) < 3: continue
        p = Polygon(o, [i for i in inners if len(i) >= 3 and Polygon(i).within(Polygon(o).buffer(.5))])
        if not p.is_valid: p = make_valid(p)
        polys.append(p)
    if not polys: return None
    g = unary_union(polys)
    return g if not g.is_empty else None

def _join_rings(ways):
    """Join relation member ways into closed rings."""
    ways = [w[:] for w in ways if len(w) >= 2]
    rings = []
    while ways:
        r = ways.pop(0)
        changed = True
        while changed and r[0] != r[-1]:
            changed = False
            for i, w in enumerate(ways):
                if w[0] == r[-1]: r += w[1:]
                elif w[-1] == r[-1]: r += w[::-1][1:]
                elif w[-1] == r[0]: r = w[:-1] + r
                elif w[0] == r[0]: r = w[::-1][:-1] + r
                else: continue
                ways.pop(i); changed = True; break
        if len(r) >= 4: rings.append(r)
    return rings

def load():
    cache = f'{ASSETS}/cache/osm.pkl'
    if os.path.exists(cache): return pickle.load(open(cache, 'rb'))
    elements = json.load(open(f'{ASSETS}/osm/granada.json'))['elements']
    out = {'areas': [], 'lines': [], 'nodes': []}
    for e in elements:
        t = e.get('tags', {})
        if e['type'] == 'node':
            if 'lat' in e: out['nodes'].append({'id': e['id'], 'tags': t, 'p': Point(local(e['lon'], e['lat']))})
            continue
        if e['type'] == 'way':
            pts = _ring(e.get('geometry', []))
            if len(pts) < 2: continue
            closed = len(pts) > 3 and pts[0] == pts[-1]
            area_like = closed and not ('highway' in t and t.get('area') != 'yes') and not ('barrier' in t) and t.get('natural') not in ('tree_row', 'cliff') and 'waterway' not in t
            if area_like:
                g = _poly([pts])
                if g is not None: out['areas'].append({'id': e['id'], 'type': 'way', 'tags': t, 'g': g})
            else:
                out['lines'].append({'id': e['id'], 'tags': t, 'g': LineString(pts)})
            continue
        members = e.get('members', [])
        outers = _join_rings([_ring(m['geometry']) for m in members if m.get('role') in ('outer', '') and m.get('geometry')])
        inners = _join_rings([_ring(m['geometry']) for m in members if m.get('role') == 'inner' and m.get('geometry')])
        g = _poly(outers, inners)
        if g is not None: out['areas'].append({'id': e['id'], 'type': 'relation', 'tags': t, 'g': g})
    pickle.dump(out, open(cache, 'wb'))
    return out

if __name__ == '__main__':
    import collections
    d = load()
    print({k: len(v) for k, v in d.items()})
    c = collections.Counter()
    for a in d['areas']:
        t = a['tags']
        for k in ('landuse', 'natural', 'leisure'):
            if k in t: c[k + '=' + t[k]] += 1
    print(c.most_common(40))
