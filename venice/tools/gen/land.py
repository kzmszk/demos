"""Land / water partition of the historic centre from OSM island + water polygons (shapely)."""
import math
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union
from shapely.validation import make_valid

def _poly(ring):
    if len(ring) < 3: return None
    p = make_valid(Polygon(ring))
    return p if not p.is_empty else None

def islands(o):
    polys = []
    for rid, r in o.rels.items():
        t = r.get('tags', {})
        if t.get('place') in ('island', 'islet'):
            rr = o.rel_rings(rid)
            outer = [_poly(x) for x in rr['outer']]; inner = [_poly(x) for x in rr['inner']]
            g = unary_union([p for p in outer if p])
            if inner: g = g.difference(unary_union([p for p in inner if p]))
            polys.append(g)
    for wid, w in o.ways.items():
        t = w.get('tags', {})
        if t.get('place') in ('island', 'islet') and w['nodes'][0] == w['nodes'][-1]:
            p = _poly(o.way_xy(wid))
            if p: polys.append(p)
    return unary_union(polys)

def waters(o, exclude_lagoon=True):
    polys = []
    def is_water(t):
        return (t.get('natural') == 'water' or t.get('waterway') in ('riverbank', 'dock', 'canal')) and t.get('water') != 'lagoon'
    for wid, w in o.ways.items():
        t = w.get('tags', {})
        if is_water(t) and w['nodes'][0] == w['nodes'][-1]:
            p = _poly(o.way_xy(wid))
            if p: polys.append(p)
    for rid, r in o.rels.items():
        t = r.get('tags', {})
        # only areas: a type=waterway relation (e.g. "Canale della Giudecca") lists the canal's centre lines, and
        # closing those into a ring once swallowed half of Dorsoduro
        if is_water(t) and t.get('type') == 'multipolygon':
            rr = o.rel_rings(rid)
            g = unary_union([p for p in (_poly(x) for x in rr['outer']) if p])
            inn = [p for p in (_poly(x) for x in rr['inner']) if p]
            if inn: g = g.difference(unary_union(inn))
            polys.append(g)
    return unary_union(polys)

def land(o):
    return islands(o).difference(waters(o)).buffer(0)
