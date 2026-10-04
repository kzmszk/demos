"""OSM 3D building parts (building:part).  Buildings mapped in 3D are replaced by their parts: each part becomes
a sub-building with its own base (min_height), wall top and roof shape.  Parts that only add a taller volume to
an otherwise plain building (a tower, a dome, an altana) are added on top of it.

Part semantics (OSM Simple 3D Buildings): height = top of the roof above ground, min_height = bottom of the
walls, roof:height = vertical extent of the roof (the walls end at height - roof:height)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.validation import make_valid
from .osm import num

# buildings replaced by hand-modelled heroes (their parts are ignored)
HERO_PARENTS = {
    'w138800932',   # Basilica di San Marco
    'w410344923',   # Procuratie Vecchie
    'w138803888',   # Procuratie Nuove
    'w252637693', 'w252637694',   # Campanile, Loggetta
    'w138803915',   # Palazzo Ducale
    'w206333242',   # Libreria / Biblioteca Marciana
    'w430963095', 'w431003750',   # the two columns of the Piazzetta
}

SHAPES = {'flat': 'flat', 'gabled': 'gabled', 'hipped': 'hipped', 'half-hipped': 'hipped', 'crosspitched': 'hipped',
          'gambrel': 'gabled', 'mansard': 'hipped', 'saltbox': 'gabled', 'pyramidal': 'pyramid', 'cone': 'pyramid',
          'skillion': 'skillion', 'lean_to': 'skillion', 'dome': 'dome', 'onion': 'onion', 'round': 'round'}

def _colour(s):
    if not s: return None
    s = s.strip().lower()
    named = {'white': (240, 240, 235), 'grey': (150, 150, 150), 'gray': (150, 150, 150), 'red': (170, 70, 50), 'brown': (120, 80, 60),
             'green': (80, 130, 100), 'beige': (225, 205, 170), 'yellow': (225, 200, 120), 'black': (40, 40, 40), 'darkgrey': (90, 90, 90)}
    if s in named: return named[s]
    if s.startswith('#') and len(s) in (4, 7):
        h = s[1:]
        if len(h) == 3: h = ''.join(c * 2 for c in h)
        try: return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError: return None
    return None

def _lum(c): return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255.0

def part_polys(o):
    out = []
    for wid, w in o.ways.items():
        t = w.get('tags', {})
        if 'building:part' not in t or w['nodes'][0] != w['nodes'][-1] or len(w['nodes']) < 4: continue
        try: p = make_valid(Polygon(o.way_xy(wid)))
        except Exception: continue
        for q in (p.geoms if hasattr(p, 'geoms') else [p]):
            if q.geom_type == 'Polygon' and q.area > 0.5: out.append((f'p{wid}', t, q))
    for rid, r in o.rels.items():
        t = r.get('tags', {})
        if 'building:part' not in t: continue
        rr = o.rel_rings(rid)
        try:
            g = shapely.union_all([make_valid(Polygon(x)) for x in rr['outer'] if len(x) > 2])
            if rr['inner']: g = g.difference(shapely.union_all([make_valid(Polygon(x)) for x in rr['inner'] if len(x) > 2]))
        except Exception: continue
        for q in (g.geoms if hasattr(g, 'geoms') else [g]):
            if q.geom_type == 'Polygon' and q.area > 0.5: out.append((f'pr{rid}', t, q))
    return out

def roof_defaults(shape, poly, wall_h):
    """roof height when the part does not say."""
    mrr = poly.minimum_rotated_rectangle
    xs, ys = mrr.exterior.coords.xy
    e = sorted([math.dist((xs[i], ys[i]), (xs[i + 1], ys[i + 1])) for i in range(2)])
    short = max(e[0], 0.5)
    if shape in ('gabled', 'hipped', 'skillion'): return min(4.5, short / 2 * math.tan(math.radians(22)))
    if shape == 'pyramid': return min(short * 1.2, 14.0)
    if shape in ('dome', 'round'): return short / 2
    if shape == 'onion': return short * 1.1
    return 0.0

def apply(world, Building, GROUND_Z):
    """replace/extend world.buildings with parts; returns the number of parts used."""
    parts = part_polys(world.o)
    tree = world.btree
    by = {}
    for pid, t, p in parts:
        rp = p.representative_point()
        hit = [i for i in tree.query(rp) if world.buildings[i].poly.contains(rp)]
        if not hit: continue
        bi = max(hit, key=lambda i: world.buildings[i].poly.area)
        by.setdefault(bi, []).append((pid, t, p))
    drop = set(); new = []
    for bi, ps in by.items():
        par = world.buildings[bi]
        if par.id in HERO_PARENTS: continue
        cov = shapely.union_all([p for _, _, p in ps]).intersection(par.poly).area / max(par.poly.area, 1e-6)
        replace = cov > 0.5
        made = []
        for pid, t, p in ps:
            top = num(t.get('height'))
            lv = num(t.get('building:levels'))
            if top is None and lv: top = lv * 3.3 + 0.5
            if top is None: top = par.H if replace else None
            if top is None: continue
            base = num(t.get('min_height'), 0.0)
            if base == 0.0 and num(t.get('building:min_level')): base = num(t.get('building:min_level')) * 3.3
            shape = SHAPES.get(t.get('roof:shape', 'flat'), 'flat')
            rh = num(t.get('roof:height'))
            if rh is None: rh = roof_defaults(shape, p, top - base) if shape != 'flat' else 0.0
            rh = max(0.0, min(rh, top - base))
            wall_top = top - rh
            if not replace and top < par.H + 1.0: continue          # only taller volumes extend a plain building
            if top - base < 0.4: continue
            b = Building(pid, {**{k: v for k, v in par.tags.items() if k in ('building', 'name', 'amenity', 'historic')}, **t}, make_valid(p))
            if b.poly.geom_type != 'Polygon':
                gs = [g for g in getattr(b.poly, 'geoms', []) if g.geom_type == 'Polygon']
                if not gs: continue
                b.poly = max(gs, key=lambda g: g.area)
            b.seed = par.seed
            b.kind = par.kind if par.kind in ('church', 'palazzo', 'house', 'shed') else 'house'
            narrow = math.sqrt(p.area)
            if t.get('man_made') in ('tower', 'campanile') or t.get('tower:type') == 'bell_tower' or (top - base > 2.6 * narrow and top > 18 and p.area < 200):
                b.kind = 'tower'
            if shape in ('dome', 'onion') and b.kind != 'tower': b.kind = 'church' if par.kind == 'church' else b.kind
            b.z0 = GROUND_Z + base
            b.H = wall_top
            b.roof = shape
            b.roof_h = rh
            b.parent = par.id
            b.levels = int(lv) if lv else (0 if b.kind in ('church', 'tower') else max(1, int(round((wall_top - base) / 3.4))))
            # materials from tags
            wc = _colour(t.get('building:colour')); rc = _colour(t.get('roof:colour'))
            wmat = t.get('building:material', ''); rmat = t.get('roof:material', '')
            pm = {}
            if wmat == 'brick' or (wc and wc[0] > wc[2] + 40 and _lum(wc) < 0.55): pm['wall'] = 'wall_brick'
            elif wmat in ('stone', 'marble') or (wc and _lum(wc) > 0.72): pm['wall'] = 'wall_stone'
            elif wc: pm['wall'] = 'wall_plaster'; pm['tint'] = list(wc)
            green = rc is not None and rc[1] > rc[0] + 25 and rc[1] > rc[2] + 10 and _lum(rc) < 0.65
            if shape in ('dome', 'onion'):
                pm['roof'] = 'copper' if green or rmat == 'copper' else 'lead'
            elif rmat in ('metal', 'lead', 'copper') or (rc and abs(rc[0] - rc[2]) < 30 and _lum(rc) > 0.3):
                pm['roof'] = 'copper' if (rmat == 'copper' or green) else 'lead'
            elif shape == 'pyramid' and b.kind == 'tower' and not rmat:
                pm['roof'] = 'roof_old'
            b.pmat = pm
            made.append(b)
        if not made: continue
        # parts without their own wall colour take the most common one of their siblings
        walls = [m.pmat.get('wall') for m in made if m.pmat and m.pmat.get('wall')]
        if walls:
            dom = max(set(walls), key=walls.count)
            tint = next((m.pmat.get('tint') for m in made if m.pmat and m.pmat.get('wall') == dom and m.pmat.get('tint')), None)
            for m in made:
                if not m.pmat.get('wall'):
                    m.pmat['wall'] = dom
                    if tint: m.pmat['tint'] = tint
        if replace:
            drop.add(bi)
            # the part of the footprint no part covers keeps the parent's own height
            rest = par.poly.difference(shapely.union_all([m.poly for m in made]).buffer(0.05))
            for q in (rest.geoms if hasattr(rest, 'geoms') else [rest]):
                if q.geom_type == 'Polygon' and q.area > 25 and q.area / max(q.length, 1e-6) > 1.2:
                    b = Building(par.id + '_r%d' % len(made), par.tags, q.buffer(0))
                    b.seed = par.seed; b.kind = par.kind; b.H = par.H; b.levels = par.levels; b.roof = par.roof; b.parent = par.id
                    b.pmat = {'wall': dom} if walls else {}
                    made.append(b)
        new += made
    world.buildings = [b for i, b in enumerate(world.buildings) if i not in drop] + new
    return len(new)
