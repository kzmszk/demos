"""天龍寺 site: exclusions (the generic PLATEAU buildings replaced), ground paint, and the planting (maples above all in the
天龍寺 garden and at 常寂光寺; pines in the gardens; sugi / hinoki / evergreen oaks on 亀山 and 小倉山; sakura and maples
in 亀山公園).  The bamboo is planted by tenryuji_bamboo."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from . import tenryuji_kit as K

MIX = {
    'garden':   [('momiji', 0.55), ('matsu', 0.2), ('kashi', 0.12), ('sakura', 0.05), ('sugi', 0.04), ('hinoki', 0.04)],
    'hill':     [('kashi', 0.32), ('momiji', 0.22), ('sugi', 0.16), ('hinoki', 0.12), ('matsu', 0.1), ('sakura', 0.05), ('keyaki', 0.03)],
    'precinct': [('momiji', 0.4), ('matsu', 0.22), ('kashi', 0.15), ('sakura', 0.12), ('keyaki', 0.06), ('ichou', 0.05)],
    'park':     [('momiji', 0.34), ('sakura', 0.26), ('kashi', 0.16), ('matsu', 0.12), ('sugi', 0.06), ('hinoki', 0.06)],
    'jojakko':  [('momiji', 0.78), ('sugi', 0.06), ('kashi', 0.08), ('matsu', 0.05), ('hinoki', 0.03)],
    'okochi':   [('matsu', 0.3), ('momiji', 0.35), ('kashi', 0.15), ('sakura', 0.06), ('sugi', 0.07), ('hinoki', 0.07)],
}
SCALE = {'momiji': (0.95, 1.45), 'matsu': (0.8, 1.3), 'kashi': (0.8, 1.15), 'sugi': (0.8, 1.1), 'hinoki': (0.75, 1.05), 'keyaki': (0.7, 1.0),
         'sakura': (0.8, 1.15), 'ichou': (0.8, 1.05), 'tsutsuji': (0.8, 1.3)}

def landuse(S, lid):
    for f in S.osm['landuse']:
        if f['id'] == lid: return K.osm_poly(f)
    return None

def replaced_zone(S, osm_ids, extra_polys=()):
    """rings to exclude: the OSM footprints of the replaced buildings and every PLATEAU footprint that overlaps one of
    them (the generic city builds from PLATEAU; its building is dropped when its representative point is inside)"""
    polys = []
    for b in S.osm['buildings']:
        if b['id'] in osm_ids:
            polys.append(Polygon(K.outer(b['poly'])).buffer(0.8))
    U = unary_union(polys)
    add = []
    for p in S.plateau:
        try: P = Polygon(K.outer(p['poly'])).buffer(0)
        except Exception: continue
        if P.is_empty: continue
        inter = P.intersection(U).area
        if inter > 0.3 * P.area or inter > 25.0:
            add.append(P.buffer(0.5))
    Z = unary_union([U] + add + list(extra_polys))
    out = []
    for g in (Z.geoms if hasattr(Z, 'geoms') else [Z]):
        out.append([list(map(list, g.exterior.coords))] + [list(map(list, r.coords)) for r in g.interiors])
    return out, Z

def blocked_for_trees(S, extra=()):
    g = []
    for b in S.osm['buildings']:
        try: g.append(Polygon(K.outer(b['poly'])).buffer(1.8))
        except Exception: pass
    for w in S.osm['ways']:
        hw = w['tags'].get('highway', '')
        for ln in w['line']:
            if len(ln) < 2: continue
            g.append(LineString(ln).buffer((w.get('width') or 1.6) / 2 + (0.6 if hw in ('path', 'footway', 'steps') else 1.5)))
    for w in S.osm['water']:
        try: g.append(K.osm_poly(w).buffer(0.8))
        except Exception: pass
    g += list(extra)
    return unary_union(g)

def plant_zone(B, S, zone, spacing, mix, rng, scale_k=1.0, limit=6000, zf=None):
    zone = zone.difference(K.neighbour_zone())
    pts = K.poisson(zone, spacing, rng, limit)
    for (x, y) in pts:
        sp = K.pick(mix, rng.random())
        lo, hi = SCALE.get(sp, (0.8, 1.1))
        z = (zf(x, y) if zf else float(S.ground(x, y))) - 0.1
        sc = rng.uniform(lo, hi) * scale_k
        if K.blocks_view(sp, x, y, z, sc, near=23.0): continue
        B.tree(sp, float(x), float(y), z, sc, rng.uniform(0, 2 * math.pi))
    return len(pts)

def preview_ground(S):
    """a preview-only ground overlay (the run_site terrain is plain grey): painted surfaces as tinted cloth"""
    from jk.core import Builder
    import os
    if os.environ.get('TJ_NOPAINT'): return None
    G = Builder('preview_ground')
    # the river (drawn by the city / the arashiyama site in the viewer): a flat water plane for the previews
    for w in S.osm['water']:
        if w['tags'].get('water') == 'river':
            try:
                P = K.osm_poly(w).simplify(0.5)
                hf = lambda x, y: float(S.ground(x, y)) + 0.2
                from jk.core import Builder as _B
                K.mesh_region(G, P.intersection(box(*S.bounds)), hf, 4.0, mat='water')
            except Exception as e: print('river preview', e)
    COL = {'stone_slab': (150, 146, 138), 'gravel': (170, 165, 155), 'sand': (200, 196, 186), 'moss': (40, 70, 22), 'forest': (70, 52, 32), 'concrete': (150, 148, 140),
           'soil': (110, 88, 62), 'grass': (60, 90, 30)}
    for e in S.paint:
        try:
            P = Polygon(e['poly'][0], e['poly'][1:]).buffer(0)
        except Exception: continue
        col = COL.get(e['surf'], (120, 120, 120))
        for p in (P.geoms if hasattr(P, 'geoms') else [P]):
            if p.is_empty or p.area < 0.5 or p.area > 2500.0: continue
            q = p.simplify(0.3)
            if q.is_empty: continue
            x0, y0, x1, y1 = q.bounds
            res = 2.0
            xs = np.arange(x0, x1 + res, res); ys = np.arange(y0, y1 + res, res)
            from shapely.geometry import box as bx
            for i in range(len(xs) - 1):
                for j in range(len(ys) - 1):
                    c = bx(xs[i], ys[j], xs[i + 1], ys[j + 1]).intersection(q)
                    if c.is_empty or c.area < 0.01: continue
                    for cc in (c.geoms if hasattr(c, 'geoms') else [c]):
                        if cc.geom_type != 'Polygon': continue
                        V = np.array(cc.exterior.coords)[:-1]
                        if len(V) < 3: continue
                        Z = S.ground(V[:, 0], V[:, 1]) + 0.04
                        import mapbox_earcut as earcut
                        I = earcut.triangulate_float64(V, np.array([len(V)], np.uint32)).reshape(-1, 3)
                        Pp = np.c_[V, Z]
                        fn = np.cross(Pp[I[:, 1]] - Pp[I[:, 0]], Pp[I[:, 2]] - Pp[I[:, 0]])
                        I[fn[:, 2] < 0] = I[fn[:, 2] < 0][:, ::-1]
                        G.add(Pp, I, 'cloth', c0=col + (0,))
    return G

def build(B, S, parts, ctx, shots):
    from . import tenryuji_temple as T
    ids = list(T.REPLACED)
    extra = []
    if 'bamboo' in ctx: ids += ctx['bamboo'].get('replaced', []); extra += ctx['bamboo'].get('zones', [])
    if 'west' in ctx: ids += ctx['west'].get('replaced', []); extra += ctx['west'].get('zones', [])
    if 'garden' in ctx: extra += ctx['garden'].get('zones', [])
    if 'temple' in ctx: extra += ctx['temple'].get('zones', [])
    rings, Z = replaced_zone(S, ids, extra)
    S.exclude.extend(rings)
    if 'land' not in parts: return
    rng = np.random.default_rng(1339)
    # OSM tree nodes inside the zones we plant (枝垂梅, 桜, シャクナゲ ...)
    zones = [z for z in (landuse(S, i) for i in (409723494, 319336216, 677236682, 925807376)) if z is not None]
    Zall = unary_union(zones)
    named = []
    for t in S.osm['trees']:
        x, y = t['xy']; tg = t['tags']
        if not Zall.contains(Point(x, y)): continue
        g = (tg.get('genus') or '') + (tg.get('species') or '')
        if 'Nelumbo' in g: continue
        sp = 'sakura' if ('Prunus' in g or 'Cerasus' in g) else 'tsutsuji' if 'Rhododendron' in g else ('momiji' if len(named) % 2 else 'kashi')
        named.append(Point(x, y).buffer(3.0))
        if K.blocks_view(sp, x, y, float(S.ground(x, y)), 0.8 if sp == 'sakura' else 1.0): continue
        B.tree(sp, float(x), float(y), float(S.ground(x, y)) - 0.1, 0.8 if sp == 'sakura' else 1.0, rng.uniform(0, 6.28))
    blocked = blocked_for_trees(S, [Z.buffer(2.0)] + list(ctx.get('garden', {}).get('no_trees', [])) + list(ctx.get('west', {}).get('no_trees', []))
                                + list(ctx.get('bamboo', {}).get('no_trees', [])))
    if named: blocked = unary_union([blocked] + named)
    shapely.prepare(blocked)
    n = 0
    # 天龍寺: the precinct (minus the 曹源池 garden, planted by tenryuji_garden) and the hill behind (亀山's slope)
    tj = landuse(S, 409723494)
    garden = ctx.get('garden', {}).get('planted')
    zone = tj.difference(blocked)
    if garden is not None: zone = zone.difference(garden.buffer(1.0))
    bamboo = ctx.get('bamboo', {}).get('planted')
    if bamboo is not None: zone = zone.difference(bamboo)
    hill = zone.intersection(Polygon([(-7920, 3240), (-7835, 3240), (-7835, 3510), (-7920, 3510)]))
    flat = zone.difference(hill)
    n += plant_zone(B, S, hill, 5.0, MIX['hill'], rng)
    n += plant_zone(B, S, flat, 9.0, MIX['precinct'], rng)
    # 亀山公園 (嵐山公園 亀山地区)
    park = landuse(S, 319336216)
    if park is not None:
        pz = park.difference(blocked)
        if bamboo is not None: pz = pz.difference(bamboo)
        pz = pz.difference(ctx.get('west', {}).get('view_open', Polygon()))
        n += plant_zone(B, S, pz, 5.6, MIX['park'], rng)
    # 大河内山荘
    ok = landuse(S, 677236682)
    if ok is not None:
        oz = ok.difference(blocked)
        if bamboo is not None: oz = oz.difference(bamboo)
        n += plant_zone(B, S, oz, 5.2, MIX['okochi'], rng)
    # 常寂光寺: maples everywhere, dense
    jj = landuse(S, 925807376)
    if jj is not None:
        jz = jj.difference(blocked)
        n += plant_zone(B, S, jz, 4.6, MIX['jojakko'], rng, scale_k=0.85)
    ctx['n_trees'] = n
