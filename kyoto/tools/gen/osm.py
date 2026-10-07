"""OpenStreetMap features for the Kyoto build (ODbL, © OpenStreetMap contributors), projected to the local frame.
load() -> dict of lists, cached in ASSETS/cache/osm.pkl"""
import os, json, pickle, math
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, Point, MultiPolygon
from shapely.ops import polygonize, unary_union
from .frame import ASSETS, to_xy

SRC = os.path.join(ASSETS, 'osm', 'kyoto.json')
SRCS = [SRC, os.path.join(ASSETS, 'osm', 'kyoto_west.json')]       # the core extract + the western enclaves (gen.osm_extract)
CACHE = os.path.join(ASSETS, 'cache', 'osm.pkl')

# carriageway widths (m) when OSM has no width / lanes
ROAD_W = {'motorway': 18.0, 'motorway_link': 7.0, 'trunk': 16.0, 'trunk_link': 7.0, 'primary': 14.0, 'primary_link': 7.0, 'secondary': 11.0,
          'secondary_link': 6.0, 'tertiary': 8.0, 'tertiary_link': 5.0, 'unclassified': 5.0, 'residential': 4.5, 'living_street': 4.0,
          'service': 3.5, 'pedestrian': 5.0, 'footway': 2.0, 'path': 1.6, 'steps': 2.0, 'track': 3.0, 'cycleway': 2.0, 'busway': 7.0, 'corridor': 2.0, 'bridleway': 2.0}
ROAD_RANK = {'motorway': 9, 'trunk': 8, 'primary': 7, 'secondary': 6, 'tertiary': 5, 'busway': 5, 'unclassified': 4, 'residential': 3, 'living_street': 3,
             'service': 2, 'pedestrian': 2, 'track': 1, 'footway': 0, 'path': 0, 'steps': 0, 'cycleway': 0, 'corridor': 0, 'bridleway': 0}

def _num(s, default=None):
    if s is None: return default
    try: return float(str(s).replace('m', '').replace(',', '.').split(';')[0].strip())
    except Exception: return default

def _proj(geom):
    lon = np.array([g['lon'] for g in geom]); lat = np.array([g['lat'] for g in geom])
    x, y = to_xy(lon, lat)
    return np.stack([x, y], 1)

def _poly(c):
    if len(c) < 4: return None
    p = Polygon(c)
    if not p.is_valid: p = p.buffer(0)
    if p.is_empty: return None
    return p

def load(force=False):
    srcs = [p for p in SRCS if os.path.exists(p)]
    if not force and os.path.exists(CACHE) and all(os.path.getmtime(CACHE) > os.path.getmtime(p) for p in srcs) and os.path.getmtime(CACHE) > os.path.getmtime(__file__):
        return pickle.load(open(CACHE, 'rb'))
    ways = {}; nodes = []; rels = []; seen_n = set(); seen_r = set()
    for src in srcs:                                   # the core first, so its features keep their order
        for e in json.load(open(src))['elements']:
            if e['type'] == 'node':
                if e['id'] not in seen_n: seen_n.add(e['id']); nodes.append(e)
            elif e['type'] == 'way':
                if e['id'] not in ways: ways[e['id']] = e
            elif e['id'] not in seen_r: seen_r.add(e['id']); rels.append(e)
    # node coords
    if nodes:
        x, y = to_xy(np.array([n['lon'] for n in nodes]), np.array([n['lat'] for n in nodes]))
        for n, a, b in zip(nodes, x, y): n['xy'] = (float(a), float(b))
    for w in ways.values(): w['xy'] = _proj(w['geometry'])
    out = dict(roads=[], areas=[], water=[], waterways=[], rails=[], barriers=[], trees=[], tree_rows=[], points=[], buildings=[], landuse=[])
    def closed(w): return len(w['nodes']) > 3 and w['nodes'][0] == w['nodes'][-1]
    # multipolygon relations -> polygons
    relpolys = []
    for r in rels:
        t = r.get('tags', {})
        if t.get('type') != 'multipolygon': continue
        outer = [LineString(ways[m['ref']]['xy']) for m in r['members'] if m['type'] == 'w' and m['ref'] in ways and m['role'] != 'inner' and len(ways[m['ref']]['xy']) > 1]
        inner = [LineString(ways[m['ref']]['xy']) for m in r['members'] if m['type'] == 'w' and m['ref'] in ways and m['role'] == 'inner' and len(ways[m['ref']]['xy']) > 1]
        po = list(polygonize(unary_union(outer))) if outer else []
        pi = list(polygonize(unary_union(inner))) if inner else []
        if not po: continue
        # even-odd: a face is inside when an odd number of the member rings encloses it (moats mapped as two
        # 'outer' rings, like Nijo Castle's 外濠, would otherwise fill the castle with water)
        rings = [Polygon(r.exterior) for r in po]
        keep = [f for f in po if sum(1 for r in rings if r.buffer(1e-6).contains(f.representative_point())) % 2 == 1]
        g = unary_union(keep or po)
        if pi: g = g.difference(unary_union(pi))
        if g.is_empty: continue
        relpolys.append((r['id'], t, g))
    for w in ways.values():
        t = w.get('tags', {})
        if not t: continue
        xy = w['xy']
        hw = t.get('highway')
        if hw and hw not in ('proposed', 'construction', 'platform', 'elevator', 'raceway', 'bus_stop'):
            if t.get('area') == 'yes' and closed(w):
                p = _poly(xy)
                if p is not None: out['areas'].append(dict(id=w['id'], kind='ped_area', poly=p, tags=t))
                continue
            width = _num(t.get('width'))
            lanes = _num(t.get('lanes'))
            if width is None:
                width = ROAD_W.get(hw, 4.0)
                if lanes and hw not in ('footway', 'path', 'steps', 'pedestrian'): width = max(width * 0.6, lanes * 3.1 + (0.8 if lanes > 2 else 0.4))
            out['roads'].append(dict(id=w['id'], hw=hw, line=LineString(xy), width=width, surface=t.get('surface'), layer=int(_num(t.get('layer'), 0) or 0),
                                     bridge=t.get('bridge') not in (None, 'no'), tunnel=t.get('tunnel') not in (None, 'no'), covered=t.get('covered'),
                                     name=t.get('name'), sidewalk=t.get('sidewalk'), footway=t.get('footway'), oneway=t.get('oneway'), lanes=lanes, tags=t))
            continue
        if 'building' in t or 'building:part' in t:
            p = _poly(xy) if closed(w) else None
            if p is not None: out['buildings'].append(dict(id=w['id'], poly=p, tags=t, part='building:part' in t))
            continue
        ww = t.get('waterway')
        if ww in ('river', 'stream', 'canal', 'ditch', 'drain', 'weir') and not closed(w):
            out['waterways'].append(dict(id=w['id'], ww=ww, line=LineString(xy), width=_num(t.get('width')), tunnel=t.get('tunnel'), name=t.get('name'), tags=t))
            continue
        if t.get('natural') == 'water' or t.get('waterway') == 'riverbank' or t.get('landuse') in ('reservoir', 'basin') or t.get('leisure') == 'swimming_pool':
            p = _poly(xy) if closed(w) else None
            if p is not None: out['water'].append(dict(id=w['id'], poly=p, tags=t, pool=t.get('leisure') == 'swimming_pool'))
            continue
        rw = t.get('railway')
        if rw in ('rail', 'light_rail', 'subway', 'tram', 'narrow_gauge', 'monorail'):
            out['rails'].append(dict(id=w['id'], rw=rw, line=LineString(xy), bridge=t.get('bridge') not in (None, 'no'), tunnel=t.get('tunnel') not in (None, 'no'),
                                     layer=int(_num(t.get('layer'), 0) or 0), tags=t))
            continue
        if rw == 'platform' and closed(w):
            p = _poly(xy)
            if p is not None: out['areas'].append(dict(id=w['id'], kind='platform', poly=p, tags=t))
            continue
        br = t.get('barrier')
        if br in ('wall', 'fence', 'hedge', 'retaining_wall', 'city_wall', 'guard_rail', 'kerb', 'rope', 'handrail'):
            out['barriers'].append(dict(id=w['id'], kind=br, line=LineString(xy), height=_num(t.get('height')), material=t.get('material'), tags=t))
            continue
        if t.get('natural') == 'tree_row':
            out['tree_rows'].append(dict(id=w['id'], line=LineString(xy), tags=t)); continue
        lu = t.get('landuse') or t.get('leisure') or t.get('natural') or t.get('amenity')
        if lu and closed(w):
            p = _poly(xy)
            if p is not None: out['landuse'].append(dict(id=w['id'], kind=lu, poly=p, tags=t))
            continue
        if t.get('man_made') == 'ceremonial_gate' or t.get('historic') == 'wayside_shrine' or t.get('man_made') in ('bridge', 'embankment', 'tower'):
            if closed(w):
                p = _poly(xy)
                if p is not None: out['landuse'].append(dict(id=w['id'], kind=t.get('man_made') or t.get('historic'), poly=p, tags=t))
            else:
                out['barriers'].append(dict(id=w['id'], kind=t.get('man_made') or t.get('historic'), line=LineString(xy), height=None, material=None, tags=t))
    for (rid, t, g) in relpolys:
        if t.get('water') == 'moat' and g.geom_type == 'Polygon' and not g.interiors and g.area > 20000:
            g = g.difference(g.buffer(-24.0))          # a moat drawn as its outer edge only: keep a band of water
        if t.get('natural') == 'water' or t.get('waterway') == 'riverbank' or t.get('water'):
            out['water'].append(dict(id=-rid, poly=g, tags=t, pool=False))
        elif 'building' in t:
            for p in (g.geoms if hasattr(g, 'geoms') else [g]): out['buildings'].append(dict(id=-rid, poly=p, tags=t, part=False))
        elif t.get('landuse') or t.get('leisure') or t.get('natural') or t.get('amenity'):
            out['landuse'].append(dict(id=-rid, kind=t.get('landuse') or t.get('leisure') or t.get('natural') or t.get('amenity'), poly=g, tags=t))
        elif t.get('highway') or t.get('area:highway'):
            out['areas'].append(dict(id=-rid, kind='ped_area', poly=g, tags=t))
    for n in nodes:
        t = n['tags']
        if t.get('natural') == 'tree': out['trees'].append(dict(id=n['id'], xy=n['xy'], tags=t)); continue
        out['points'].append(dict(id=n['id'], xy=n['xy'], tags=t))
    pickle.dump(out, open(CACHE, 'wb'), protocol=5)
    return out

if __name__ == '__main__':
    import time; t = time.time()
    o = load(force=True)
    print({k: len(v) for k, v in o.items()}, round(time.time() - t, 1), 's')
