"""Calli that OSM draws through building outlines.

Venetian building outlines often swallow the fondamenta or the calle beside them, and many sottoporteghi are not
tagged; walking then hits walls, and bridges land in buildings.  Each piece of a pedestrian way inside a building:
- runs along the outline (never deeper than TRIM_DEPTH): the building is trimmed back from the calle;
- passes right through, deeper (an untagged sottoportego), or is tagged tunnel=building_passage / covered=yes:
  the building stays, the strip becomes a sottoportego (walkable; floor, walls and a beamed ceiling inside, the
  facade open below SOTO_H where the strip crosses it);
- anything else (a way ending deep inside a courtyard block) is left alone.
apply(world) trims world.buildings in place and returns the sottoportego strips [(polygon, building index)]."""
import shapely
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.validation import make_valid

HW = ('pedestrian', 'footway', 'path', 'living_street', 'residential', 'service', 'corridor')
TRIM_DEPTH = 2.0       # a piece never deeper than this inside the outline runs along it
TRIM_HALF = 1.2        # half width of the strip cut out of the building along such a calle
SOTO_HALF = 0.9        # half width of a sottoportego
SOTO_MAX = 30.0        # untagged through-passages longer than this are left alone
SOTO_H = 2.9           # clear height of a sottoportego above the calle

def _depth(poly, piece):
    n = max(2, int(piece.length / 0.5))
    return max(poly.exterior.distance(piece.interpolate(i / (n - 1), normalized=True)) for i in range(n))

def _extend(piece, d):
    """the piece prolonged by d at both ends along its end directions (so a strip clearly crosses the facade)."""
    c = list(piece.coords)
    (x0, y0), (x1, y1) = c[0], c[1]; L0 = max(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5, 1e-9)
    (xa, ya), (xb, yb) = c[-2], c[-1]; L1 = max(((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5, 1e-9)
    return LineString([(x0 - (x1 - x0) / L0 * d, y0 - (y1 - y0) / L0 * d)] + c[1:-1] + [(xb + (xb - xa) / L1 * d, yb + (yb - ya) / L1 * d)])

def apply(world, skip_ids=(), ground_z=1.1):
    o = world.o
    cand = [k for k, b in enumerate(world.buildings) if b.z0 < ground_z + 2.0 and b.id not in skip_ids and not b.parent]
    tree = shapely.STRtree([world.buildings[k].poly for k in cand])
    trims = {}; soto = []
    for wid, w in o.ways.items():
        t = w.get('tags', {})
        if t.get('highway') not in HW or t.get('bridge'): continue
        tagged = t.get('tunnel') in ('building_passage', 'yes') or t.get('covered') == 'yes'
        P = o.way_xy(wid)
        if len(P) < 2: continue
        L = LineString(P)
        for q in tree.query(L):
            k = cand[q]; poly = world.buildings[k].poly
            seg = L.intersection(poly)
            for pc in (seg.geoms if hasattr(seg, 'geoms') else [seg]):
                if pc.geom_type != 'LineString' or pc.length < 0.5: continue
                depth = _depth(poly, pc)
                through = all(poly.exterior.distance(Point(c)) < 0.3 for c in (pc.coords[0], pc.coords[-1]))
                if tagged or (depth > TRIM_DEPTH and through and pc.length <= SOTO_MAX):
                    strip = _extend(pc, 0.6).buffer(SOTO_HALF, cap_style=2)
                    soto.append((strip.intersection(poly.buffer(0.6, join_style=2)), k))
                elif depth <= TRIM_DEPTH:
                    trims.setdefault(k, []).append(_extend(pc, 0.3).buffer(TRIM_HALF, cap_style=2))
    ntrim = 0
    for k, strips in trims.items():
        b = world.buildings[k]
        g = make_valid(b.poly.difference(unary_union(strips)))
        g = g.buffer(-0.4, join_style=2).buffer(0.4, join_style=2)          # no slivers left along the cut
        parts = [p for p in (g.geoms if hasattr(g, 'geoms') else [g]) if p.geom_type == 'Polygon' and p.area > 1.0]
        if not parts: continue
        parts.sort(key=lambda p: -p.area)
        if parts[0].area < 0.3 * b.poly.area or (len(parts) > 1 and parts[1].area > 12.0): continue
        b.poly = parts[0]; ntrim += 1
    soto = [(s, k) for (s, k) in soto if not s.is_empty and s.area > 0.5]
    return soto, ntrim
