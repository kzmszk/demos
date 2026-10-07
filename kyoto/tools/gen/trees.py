"""Tree placements per tile: OSM trees and tree rows, street trees on the avenues, the Kamo's banks, parks, temple
grounds and the forests of the hills.  Each instance: species index (treegen.NAMES), variant, x, y, z (ground), scale,
yaw.  Hero sites place their own trees (excluded here)."""
import math
import numpy as np
import shapely
from shapely.geometry import Point
from .treegen import NAMES
from .world import h32

SP = {n: i for i, n in enumerate(NAMES)}
NVAR = 3

def pick(table, u):
    acc = 0.0
    for name, w in table:
        acc += w
        if u < acc: return name
    return table[-1][0]

MIX = {
    'forest': [('kashi', 0.34), ('sugi', 0.2), ('hinoki', 0.13), ('momiji', 0.15), ('keyaki', 0.06), ('sakura', 0.06), ('matsu', 0.06)],
    # tended ground (temples, parks, gardens, streets, banks) is planted with trees that colour in autumn; tall evergreens
    # (cedar, cypress, pine) stay; evergreen oaks only in the forest
    'temple': [('momiji', 0.44), ('ichou', 0.18), ('sakura', 0.1), ('keyaki', 0.06), ('matsu', 0.12), ('sugi', 0.1)],   # big ginkgos in the precincts
    'park':   [('sakura', 0.26), ('momiji', 0.28), ('ichou', 0.2), ('keyaki', 0.2), ('matsu', 0.06)],
    'street': [('ichou', 0.6), ('keyaki', 0.25), ('sakura', 0.15)],
    'river':  [('sakura', 0.55), ('yanagi', 0.45)],
    'garden': [('momiji', 0.5), ('matsu', 0.22), ('tsutsuji', 0.18), ('ichou', 0.1)],          # azaleas as dōdan-tsutsuji: red
    'grave':  [('momiji', 0.4), ('sugi', 0.3), ('sakura', 0.15), ('kashi', 0.15)],
}
TAGS = [('ginkgo', 'ichou'), ('イチョウ', 'ichou'), ('銀杏', 'ichou'), ('prunus', 'sakura'), ('サクラ', 'sakura'), ('桜', 'sakura'), ('acer', 'momiji'), ('モミジ', 'momiji'),
        ('カエデ', 'momiji'), ('楓', 'momiji'), ('pinus', 'matsu'), ('マツ', 'matsu'), ('松', 'matsu'), ('cryptomeria', 'sugi'), ('スギ', 'sugi'), ('杉', 'sugi'),
        ('chamaecyparis', 'hinoki'), ('ヒノキ', 'hinoki'), ('zelkova', 'keyaki'), ('ケヤキ', 'keyaki'), ('欅', 'keyaki'), ('salix', 'yanagi'), ('ヤナギ', 'yanagi'),
        ('柳', 'yanagi'), ('quercus', 'kashi'), ('castanopsis', 'kashi'), ('cinnamomum', 'kashi'), ('クスノキ', 'kashi'), ('楠', 'kashi'), ('bamboo', 'take'), ('竹', 'take')]

WILD = 8                      # variant flag: a tree of the forest (the viewer lets it stay green)

def wild_at(landuse, x, y):
    """forest ground (OSM forest / wood / scrub and the hills' terrain forest): trees there are wild"""
    p = Point(x, y)
    return any(f['kind'] in ('forest', 'wood', 'scrub') and f['poly'].contains(p) for f in landuse)

def species_from_tags(t):
    s = ' '.join(str(t.get(k, '')) for k in ('species', 'genus', 'taxon', 'species:ja', 'species:en', 'name', 'name:ja', 'denotation')).lower()
    for k, v in TAGS:
        if k.lower() in s: return v
    if t.get('leaf_type') == 'needleleaved': return 'matsu'
    return None

def poisson(poly, spacing, seed, limit=4000):
    """dart-throwing Poisson disc inside poly"""
    r = np.random.default_rng(seed)
    x0, y0, x1, y1 = poly.bounds
    area = poly.area
    n = min(limit, int(area / (spacing * spacing) * 1.1))
    if n <= 0: return np.zeros((0, 2))
    cand = np.column_stack([r.uniform(x0, x1, n * 3), r.uniform(y0, y1, n * 3)])
    cand = cand[shapely.contains_xy(poly, cand[:, 0], cand[:, 1])]
    out = []
    from scipy.spatial import cKDTree
    grid = {}
    cs = spacing
    for p in cand:
        k = (int(p[0] // cs), int(p[1] // cs)); ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for q in grid.get((k[0] + dx, k[1] + dy), ()):
                    if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < spacing * spacing * 0.8: ok = False; break
                if not ok: break
            if not ok: break
        if ok:
            out.append(p); grid.setdefault(k, []).append(p)
            if len(out) >= n: break
    return np.array(out).reshape(-1, 2)

def place(w, tg, R, buildings, road_polys, water_geom, hero_zone=None):
    """returns array (k, 7): species, variant, x, y, z, scale, yaw"""
    big = R.buffer(5)
    out = []
    def add(x, y, name, sc_seed, scale=None, wild=False):
        u = h32(round(x, 1), round(y, 1), 'tree') / 2 ** 32
        s = scale if scale is not None else 0.8 + 0.4 * ((u * 7.3) % 1)
        # variant + 8: a wild tree (forest): it may still be green in autumn; tended ones have all turned
        out.append((SP[name], int(u * 997) % NVAR + (WILD if wild else 0), x, y, s, (u * 13.7 % 1) * 2 * math.pi))
    o = w.osm
    # blocked: buildings (+1 m), carriageways, water, hero sites
    blocks = [b.poly.buffer(1.0) for b in buildings]
    car = [g for (rank, s, g, r) in road_polys if s in ('asphalt', 'asphalt_lane')]
    blocked = shapely.unary_union(blocks + car + ([water_geom] if water_geom is not None else []) + [g for g in w.sites.values() if g.intersects(big)]
                                  + ([hero_zone.intersection(big)] if hero_zone is not None and hero_zone.intersects(big) else []))
    shapely.prepare(blocked)
    lu = [f for f in tg.landuse]
    def ctx_mix(x, y):
        for f in lu:
            if f['poly'].contains(Point(x, y)):
                k = f['kind']
                if k in ('religious', 'place_of_worship'): return 'temple'
                if k in ('forest', 'wood', 'scrub'): return 'forest'
                if k in ('cemetery', 'grave_yard'): return 'grave'
                if k == 'garden': return 'garden'
                if k in ('park', 'grass', 'village_green'): return 'park'
        return 'park'
    # OSM trees
    for t in o['trees']:
        x, y = t['xy']
        if not R.contains(Point(x, y)): continue
        if hero_zone is not None and hero_zone.contains(Point(x, y)): continue
        cm = ctx_mix(x, y)
        name = species_from_tags(t['tags']) or pick(MIX[cm], h32(t['id'], 's') / 2 ** 32)
        add(x, y, name, t['id'], wild=cm == 'forest')
    for tr in o['tree_rows']:
        ln = tr['line']
        if not ln.intersects(big): continue
        name0 = species_from_tags(tr['tags']) or pick(MIX['street'], h32(tr['id'], 's') / 2 ** 32)
        for d in np.arange(3.0, ln.length, 8.0):
            p = ln.interpolate(d)
            if R.contains(p) and not blocked.contains(p): add(p.x, p.y, name0, tr['id'])
    # street trees on the avenues: one species per road
    for r in tg.roads:
        if r['hw'] not in ('primary', 'secondary', 'trunk') or r['bridge']: continue
        ln = r['line']
        if not ln.intersects(big): continue
        name0 = pick(MIX['street'], h32(r['name'] or r['id'], 'st') / 2 ** 32)
        off = r['width'] / 2 + 1.4
        for side in (-1, 1):
            try: sl = ln.offset_curve(side * off)
            except Exception: continue
            if sl.is_empty: continue
            for d in np.arange(4.0, sl.length, 9.0):
                p = sl.interpolate(d)
                if R.contains(p) and not blocked.contains(p): add(p.x, p.y, name0, r['id'], 0.9)
    # the river banks: cherries and willows along big water bodies
    for f in tg.water:
        if f.get('pool') or f['poly'].area < 3000: continue
        for side in (6.0, 11.0):
            gb = f['poly'].buffer(side)
            for pg in (gb.geoms if hasattr(gb, 'geoms') else [gb]):
                if pg.geom_type != 'Polygon': continue
                sl = pg.exterior
                for d in np.arange(0.0, sl.length, 11.0):
                    p = sl.interpolate(d)
                    if R.contains(p) and not blocked.contains(p):
                        u = h32(round(p.x), round(p.y), 'rv') / 2 ** 32
                        if u < 0.75: add(p.x, p.y, pick(MIX['river'], u / 0.75), 0)
    # areas: forests dense, parks / gardens / temple grounds sparse
    for f in lu:
        k = f['kind']
        if k in ('forest', 'wood', 'scrub'): mix, sp, keep = 'forest', 5.5, 1.0
        elif k in ('park', 'village_green'): mix, sp, keep = 'park', 10.0, 0.7
        elif k == 'garden': mix, sp, keep = 'garden', 7.0, 0.8
        elif k in ('religious', 'place_of_worship'): mix, sp, keep = 'temple', 9.0, 0.6
        elif k in ('cemetery', 'grave_yard'): mix, sp, keep = 'grave', 12.0, 0.5
        else: continue
        g = f['poly'].intersection(R)
        if g.is_empty or g.area < 30: continue
        for poly in (g.geoms if hasattr(g, 'geoms') else [g]):
            if poly.geom_type != 'Polygon': continue
            pts = poisson(poly, sp, h32(f['id'], 'poi'))
            for (x, y) in pts:
                if blocked.contains(Point(x, y)): continue
                u = h32(round(x, 1), round(y, 1), 'k') / 2 ** 32
                if u > keep: continue
                add(x, y, pick(MIX[mix], (u * 5.17) % 1), f['id'], 0.85 + 0.35 * ((u * 3.1) % 1) if mix == 'forest' else None, wild=mix == 'forest')
    if not out: return np.zeros((0, 7), np.float32)
    A = np.array(out, np.float64)
    z = tg.T(A[:, 2], A[:, 3])
    return np.column_stack([A[:, 0], A[:, 1], A[:, 2], A[:, 3], z, A[:, 4], A[:, 5]]).astype(np.float32)
