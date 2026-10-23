"""Tree positions and species around the Alhambra from OpenStreetMap (ODbL): mapped trees and
tree rows, woods and forests (the Bosque de la Alhambra, pine plantations on the hills), parks and
gardens, the cármenes of the Albaicín (gaps between houses), olive groves and scattered holm oaks.

Output: public/data/trees.bin (gzip): uint32 count + per tree int16 x, z (dm), uint8 species,
uint8 size (height in 0.1 m units / 1.0), uint8 seed."""
import gzip, math, os, struct
import numpy as np
from shapely.geometry import Point, Polygon, box as sbox
from shapely.prepared import prep
from shapely.ops import unary_union
from shapely.strtree import STRtree
import osm, terrain, city
from frame import PUBLIC

# species ids shared with tools/web/trees.js
CYPRESS, ELM, PLANE, HOLM, OLIVE, PINE, STONEPINE, ORANGE, PALM, SHRUB, POPLAR = range(11)
H_RANGE = {CYPRESS: (8, 17), ELM: (12, 21), PLANE: (13, 22), HOLM: (5, 9), OLIVE: (3.5, 6), PINE: (9, 15),
           STONEPINE: (10, 16), ORANGE: (3, 4.5), PALM: (7, 14), SHRUB: (1.2, 2.6), POPLAR: (14, 22)}
EXTENT = city.EXTENT

def sample_poly(poly, spacing, rng, jitter=.45):
    """Jittered grid points inside a polygon."""
    x0, z0, x1, z1 = poly.bounds
    xs = np.arange(x0 + rng.random() * spacing, x1, spacing); zs = np.arange(z0 + rng.random() * spacing, z1, spacing)
    if not len(xs) or not len(zs): return np.zeros((0, 2))
    X, Z = np.meshgrid(xs, zs); P = np.stack([X.ravel(), Z.ravel()], -1)
    P = P + (rng.random(P.shape) - .5) * spacing * 2 * jitter
    import shapely
    inside = shapely.contains_xy(poly, P[:, 0], P[:, 1])
    return P[inside]

def main():
    rng = np.random.default_rng(42)
    data = osm.load()
    x0, x1, z0, z1 = EXTENT
    ext = sbox(x0, z0, x1, z1)
    hero = city.hero_zone()
    per = terrain.perimeter()
    # obstacles: buildings (+1.2 m), roads (+ half width), water
    bld = [a['g'] for a in data['areas'] if 'building' in a['tags'] and a['g'].intersects(ext)]
    roads = []
    for l in data['lines']:
        hw = l['tags'].get('highway')
        if hw and l['g'].intersects(ext):
            w = {'motorway': 9, 'trunk': 8, 'primary': 7, 'secondary': 6, 'tertiary': 5, 'residential': 3.5, 'unclassified': 3.5, 'service': 2.5, 'pedestrian': 3}.get(hw, 1.3)
            roads.append(l['g'].buffer(w))
    water = [a['g'] for a in data['areas'] if a['tags'].get('natural') == 'water' or a['tags'].get('leisure') == 'swimming_pool']
    print('obstacles', len(bld), len(roads), flush=True)
    obst = STRtree([g.buffer(1.2) for g in bld] + roads + water)
    pts, spc, srcs = [], [], []
    src = [0]
    def add(P, sp):
        if len(P): pts.append(np.asarray(P, float)); spc.append(np.broadcast_to(np.asarray(sp), (len(P),)).copy()); srcs.append(np.full(len(P), src[0]))
    def pick(n, table):
        ids, w = zip(*table); w = np.array(w) / sum(w)
        return rng.choice(ids, size=n, p=w)
    # mapped trees and rows
    T = [n['p'] for n in data['nodes'] if n['tags'].get('natural') == 'tree' and n['p'].within(ext)]
    TT = [n['tags'] for n in data['nodes'] if n['tags'].get('natural') == 'tree' and n['p'].within(ext)]
    P = np.array([[p.x, p.y] for p in T])
    sp = []
    for t, p in zip(TT, P):
        s = (t.get('species') or t.get('genus') or '').lower()
        if 'citrus' in s: sp.append(ORANGE)
        elif 'pinus' in s or t.get('leaf_type') == 'needleleaved': sp.append(PINE)
        elif 'cupressus' in s: sp.append(CYPRESS)
        elif 'phoenix' in s or 'washingtonia' in s or 'palm' in s: sp.append(PALM)
        else: sp.append(int(rng.choice([PLANE, ELM, ORANGE, ELM, PLANE, HOLM])))
    add(P, np.array(sp))
    src[0] = 1
    for l in data['lines']:
        if l['tags'].get('natural') != 'tree_row' or not l['g'].intersects(ext): continue
        g = l['g']; n = max(2, int(g.length / 7))
        Q = np.array([[g.interpolate(i / (n - 1), normalized=True).x, g.interpolate(i / (n - 1), normalized=True).y] for i in range(n)])
        add(Q, int(rng.choice([PLANE, ELM, ORANGE, CYPRESS])))
    # woods
    src[0] = 2
    for a in data['areas']:
        t = a['tags']; g = a['g']
        if not g.intersects(ext): continue
        if t.get('natural') == 'wood' or t.get('landuse') == 'forest':
            needle = t.get('leaf_type') == 'needleleaved'
            c = g.centroid
            # the Bosque de la Alhambra and the Darro / Sacromonte gullies: deciduous groves
            alhambra_wood = -500 < c.x < 600 and -350 < c.y < 450 and not needle
            spacing = 5.5 if alhambra_wood else 7.5
            Q = sample_poly(g.intersection(ext), spacing, rng)
            if alhambra_wood: table = [(ELM, .45), (PLANE, .25), (POPLAR, .08), (HOLM, .1), (CYPRESS, .07), (SHRUB, .05)]
            elif needle: table = [(PINE, .62), (STONEPINE, .18), (HOLM, .1), (SHRUB, .1)]
            else: table = [(HOLM, .4), (PINE, .25), (ELM, .15), (SHRUB, .2)]
            add(Q, pick(len(Q), table))
        elif t.get('natural') in ('scrub', 'heath'):
            Q = sample_poly(g.intersection(ext), 16, rng, .5); add(Q, pick(len(Q), [(SHRUB, .55), (HOLM, .25), (OLIVE, .1), (PINE, .1)]))
        elif t.get('landuse') == 'orchard':
            # olive groves in rows
            Q = sample_poly(g.intersection(ext), 7.5, rng, .06); add(Q, pick(len(Q), [(OLIVE, .9), (HOLM, .1)]))
        elif t.get('leisure') in ('park', 'garden') or t.get('landuse') in ('grass', 'recreation_ground', 'cemetery'):
            if g.area < 40: continue
            spacing = 11 if t.get('landuse') != 'cemetery' else 6
            Q = sample_poly(g.intersection(ext), spacing, rng, .5)
            table = [(CYPRESS, .9)] if t.get('landuse') == 'cemetery' else [(PLANE, .2), (ELM, .15), (ORANGE, .2), (CYPRESS, .2), (PALM, .12), (SHRUB, .13)]
            add(Q, pick(len(Q), table))
    src[0] = 6
    # cármenes: gaps among the houses of the Albaicín, Sacromonte and Realejo
    gx = np.arange(x0, x1, 9.0); gz = np.arange(z0, z1, 9.0)
    X, Z = np.meshgrid(gx, gz); G = np.stack([X.ravel(), Z.ravel()], -1) + (rng.random((X.size, 2)) - .5) * 8
    hz = city.historic(G[:, 0], G[:, 1])
    keep = rng.random(len(G)) < hz * .55
    G = G[keep]
    add(G, pick(len(G), [(CYPRESS, .3), (ORANGE, .22), (ELM, .08), (PALM, .1), (OLIVE, .1), (HOLM, .05), (SHRUB, .15)]))
    src[0] = 7
    # the open hills: scattered holm oaks, olives, shrubs, pines (dry hillside default)
    H = np.stack([rng.uniform(x0, x1, 26000), rng.uniform(z0, z1, 26000)], -1)
    add(H, pick(len(H), [(SHRUB, .4), (HOLM, .25), (OLIVE, .2), (PINE, .15)]))
    P = np.concatenate(pts); S = np.concatenate(spc).astype(int); SRC = np.concatenate(srcs)
    print('candidates', len(P), flush=True)
    import shapely
    # drop: outside extent, inside the enclosure/hero zones, on obstacles, too dense
    ok = (P[:, 0] > x0) & (P[:, 0] < x1) & (P[:, 1] > z0) & (P[:, 1] < z1)
    # the Generalife's hill keeps its trees; the viewer drops those standing on modelled floors/walls
    hero_nogen = hero.difference(sbox(316, -142, 442, 208))
    ok &= ~shapely.contains_xy(hero_nogen, P[:, 0], P[:, 1])
    # keep crowns off the enclosure walls and towers (and off the Partal's north face)
    ok &= ~shapely.contains_xy(per.buffer(7), P[:, 0], P[:, 1])
    ok &= ~shapely.contains_xy(sbox(84, -36, 132, -18), P[:, 0], P[:, 1])
    P, S, SRC = P[ok], S[ok], SRC[ok]
    hit = np.zeros(len(P), bool)
    qi, gi = obst.query(shapely.points(P), predicate='intersects')
    hit[qi] = True
    # mapped trees (first block) may stand on pavements: keep them
    mapped = SRC <= 1
    keep = ~hit | mapped
    P, S, SRC = P[keep], S[keep], SRC[keep]
    # urban hillside default points only where the ground is not urban landuse
    urb = unary_union([a['g'] for a in data['areas'] if a['tags'].get('landuse') in ('residential', 'retail', 'commercial', 'industrial', 'railway') and a['g'].intersects(ext)])
    hz = city.historic(P[:, 0], P[:, 1])
    inurb = shapely.contains_xy(urb, P[:, 0], P[:, 1])
    dense = (SRC == 7) & inurb
    P, S = P[~dense], S[~dense]
    # thin to a minimum distance of 2.5 m
    from scipy.spatial import cKDTree
    order = rng.permutation(len(P)); P, S = P[order], S[order]
    tree = cKDTree(P); pairs = tree.query_pairs(2.5)
    drop = np.zeros(len(P), bool)
    for i, j in pairs:
        if not drop[i]: drop[j] = True
    P, S = P[~drop], S[~drop]
    n = len(P)
    h = np.array([rng.uniform(*H_RANGE[s]) for s in S])
    out = struct.pack('<I', n)
    q = np.clip(np.round(P * 10), -32767, 32767).astype('<i2')
    rec = np.zeros(n, dtype=[('x', '<i2'), ('z', '<i2'), ('s', 'u1'), ('h', 'u1'), ('seed', 'u1')])
    rec['x'], rec['z'], rec['s'] = q[:, 0], q[:, 1], S
    rec['h'] = np.clip(np.round(h * 10), 0, 255); rec['seed'] = rng.integers(0, 256, n)
    open(f'{PUBLIC}/data/trees.bin', 'wb').write(gzip.compress(out + rec.tobytes(), 9))
    import collections
    print('trees', n, dict(collections.Counter(S.tolist())), os.path.getsize(f'{PUBLIC}/data/trees.bin'))

if __name__ == '__main__':
    main()
