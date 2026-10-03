"""Vegetation + land cover from OSM: green areas, water, and trees (individual nodes, rows, scattered
in woods/parks).  Species are Roman: umbrella pine, holm oak, cypress, plane tree, palm."""
import math, random
import numpy as np
from .geom import Mesh, lathe, mat4

GREEN = {('leisure', 'park'), ('leisure', 'garden'), ('landuse', 'grass'), ('landuse', 'forest'), ('natural', 'wood'),
         ('landuse', 'meadow'), ('leisure', 'pitch'), ('natural', 'scrub'), ('leisure', 'dog_park'), ('leisure', 'playground'), ('landuse', 'cemetery')}
WOODY = {('landuse', 'forest'), ('natural', 'wood'), ('leisure', 'park'), ('leisure', 'garden'), ('natural', 'scrub')}


def polygons(o):
    """returns (green_polys, woody_polys, water_polys) as lists of [(x,y)...] rings (outer only)."""
    green, woody, water = [], [], []
    for wid, w in o.ways.items():
        t = w.get('tags', {})
        if 'building' in t or w['nodes'][0] != w['nodes'][-1]: continue
        P = o.way_xy(wid)[:-1]
        if len(P) < 3: continue
        kv = [(k, t[k]) for k in ('leisure', 'landuse', 'natural') if k in t]
        if any(x in GREEN for x in kv): green.append(P)
        if any(x in WOODY for x in kv): woody.append(P)
        if t.get('natural') == 'water' or t.get('waterway') == 'riverbank': water.append(P)
    for rid, r in o.rels.items():
        t = r.get('tags', {})
        if t.get('natural') == 'water' or t.get('waterway') == 'riverbank':
            for ring in o.rel_rings(rid)['outer']:
                if len(ring) > 3: water.append(ring[:-1] if ring[0] == ring[-1] else ring)
        kv = [(k, t[k]) for k in ('leisure', 'landuse', 'natural') if k in t]
        if any(x in GREEN for x in kv):
            for ring in o.rel_rings(rid)['outer']:
                if len(ring) > 3: green.append(ring)
    return green, woody, water


class PolyIndex:
    """fast point-in-any-polygon via a coarse grid of candidate polygons."""
    def __init__(self, polys, cell=50.0):
        self.polys = polys; self.cell = cell; self.grid = {}
        for i, P in enumerate(polys):
            xs = [p[0] for p in P]; ys = [p[1] for p in P]
            for gx in range(int(math.floor(min(xs) / cell)), int(math.floor(max(xs) / cell)) + 1):
                for gy in range(int(math.floor(min(ys) / cell)), int(math.floor(max(ys) / cell)) + 1):
                    self.grid.setdefault((gx, gy), []).append(i)
    def inside(self, x, y):
        for i in self.grid.get((int(math.floor(x / self.cell)), int(math.floor(y / self.cell))), ()):
            P = self.polys[i]; c = False
            for k in range(len(P)):
                x0, y0 = P[k]; x1, y1 = P[(k + 1) % len(P)]
                if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0): c = not c
            if c: return True
        return False


def _blob(cx, cy, cz, rx, ry, rz, rnd, mat='foliage', n=8):
    """irregular canopy blob (lathe sphere with noise)."""
    prof = [(math.sin(t) * (1 + rnd.uniform(-0.12, 0.12)), -math.cos(t)) for t in np.linspace(0, math.pi, 6)]
    prof[0] = (0, -1); prof[-1] = (0, 1)
    m = lathe(prof, n, mat=mat)
    V = np.array(m.V)
    noise = 1 + 0.18 * np.sin(V[:, 0] * 7.1 + rnd.random() * 6) * np.cos(V[:, 1] * 5.3 + rnd.random() * 6)
    V[:, 0] *= rx * noise; V[:, 1] *= ry * noise; V[:, 2] *= rz
    V += np.array([cx, cy, cz])
    m.V = V.tolist()
    return m


def tree(kind, x, y, z, rnd, scale=1.0):
    m = Mesh(); s = scale * rnd.uniform(0.8, 1.2)
    if kind == 'pine':          # Pinus pinea: tall leaning bare trunk + flat umbrella crown
        h = 13 * s; lean = rnd.uniform(-0.12, 0.12); dirn = rnd.uniform(0, 2 * math.pi)
        tx, ty = x + math.cos(dirn) * lean * h, y + math.sin(dirn) * lean * h
        trunk = lathe([(0.35 * s, 0), (0.25 * s, h * 0.9), (0.1, h)], 6, mat='bark')
        V = np.array(trunk.V); f = V[:, 2] / h
        V[:, 0] = V[:, 0] + x + (tx - x) * f; V[:, 1] = V[:, 1] + y + (ty - y) * f; V[:, 2] += z
        trunk.V = V.tolist(); m.merge(trunk)
        for k in range(rnd.randint(3, 5)):
            a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(0, 2.5 * s)
            m.merge(_blob(tx + math.cos(a) * d, ty + math.sin(a) * d, z + h + rnd.uniform(-0.6, 0.6), 4.2 * s, 4.2 * s, 1.6 * s, rnd))
    elif kind == 'oak':         # Quercus ilex: short trunk, dense round dark crown
        h = 3 * s
        m.merge(lathe([(0.3 * s, 0), (0.22 * s, h + 1), (0, h + 1.2)], 6, mat='bark', center=(x, y, z)))
        for k in range(rnd.randint(2, 4)):
            a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(0, 1.5 * s)
            m.merge(_blob(x + math.cos(a) * d, y + math.sin(a) * d, z + h + 3.2 * s + rnd.uniform(-0.5, 0.8), 3.6 * s, 3.6 * s, 3.2 * s, rnd, 'foliage_dark'))
    elif kind == 'cypress':
        h = 16 * s
        m.merge(lathe([(0.2, 0), (1.1 * s, h * 0.15), (1.25 * s, h * 0.45), (0.8 * s, h * 0.8), (0.0, h)], 7, mat='foliage_dark', center=(x, y, z)))
    elif kind == 'plane':       # Platanus along the Tiber and avenues: tall trunk, broad crown
        h = 7 * s
        m.merge(lathe([(0.4 * s, 0), (0.3 * s, h + 2), (0, h + 2.5)], 6, mat='bark_light', center=(x, y, z)))
        for k in range(rnd.randint(3, 5)):
            a = rnd.uniform(0, 2 * math.pi); d = rnd.uniform(0, 2.4 * s)
            m.merge(_blob(x + math.cos(a) * d, y + math.sin(a) * d, z + h + 3.5 * s + rnd.uniform(-1, 1), 4.5 * s, 4.5 * s, 4.0 * s, rnd, 'foliage_light'))
    elif kind == 'palm':
        h = 9 * s
        m.merge(lathe([(0.3, 0), (0.25, h), (0, h + 0.3)], 6, mat='bark', center=(x, y, z)))
        for k in range(10):
            a = 2 * math.pi * k / 10
            for j in range(3):
                t0, t1 = j / 3, (j + 1) / 3
                p0 = (x + math.cos(a) * 4 * s * t0, y + math.sin(a) * 4 * s * t0, z + h + 1.2 * math.sin(math.pi * t0 * 0.8))
                p1 = (x + math.cos(a) * 4 * s * t1, y + math.sin(a) * 4 * s * t1, z + h + 1.2 * math.sin(math.pi * t1 * 0.8))
                w0, w1 = 0.6 * (1 - t0 * 0.7), 0.6 * (1 - t1 * 0.7)
                nx, ny = -math.sin(a), math.cos(a)
                q = [(p0[0] - nx * w0, p0[1] - ny * w0, p0[2]), (p1[0] - nx * w1, p1[1] - ny * w1, p1[2]), (p1[0] + nx * w1, p1[1] + ny * w1, p1[2]), (p0[0] + nx * w0, p0[1] + ny * w0, p0[2])]
                o = m.add_v(q); m.face([o, o + 1, o + 2, o + 3], 'foliage'); o2 = m.add_v(q); m.face([o2 + 3, o2 + 2, o2 + 1, o2], 'foliage')
    return m


def trees(o, height_fn, exclude_fn, woody_idx=None, seed=11, extra=None):
    rnd = random.Random(seed)
    m = Mesh(); pts = []
    for nid, n in o.nodes.items():
        t = n.get('tags', {})
        if t.get('natural') != 'tree': continue
        x, y = o.xy(nid)
        if exclude_fn(x, y): continue
        lt = t.get('leaf_type') or ''
        if t.get('species', '').lower().startswith('pinus') or lt == 'needleleaved': kind = 'pine' if rnd.random() < 0.8 else 'cypress'
        elif lt == 'palm' or 'palm' in t.get('species', '').lower(): kind = 'palm'
        else:
            r = rnd.random(); kind = 'oak' if r < 0.38 else 'pine' if r < 0.72 else 'plane' if r < 0.85 else 'cypress' if r < 0.96 else 'palm'
        pts.append((x, y, kind))
    for wid, w in o.ways.items():
        t = w.get('tags', {})
        if t.get('natural') != 'tree_row': continue
        P = o.way_xy(wid)
        for i in range(len(P) - 1):
            L = math.dist(P[i], P[i + 1]); n = max(1, int(L / 9))
            for k in range(n):
                x = P[i][0] + (P[i + 1][0] - P[i][0]) * (k + 0.5) / n; y = P[i][1] + (P[i + 1][1] - P[i][1]) * (k + 0.5) / n
                if not exclude_fn(x, y): pts.append((x, y, 'plane'))
    if woody_idx is not None:   # scatter in woods / parks where no mapped trees are near
        have = {}
        for (x, y, k) in pts: have[(int(x // 12), int(y // 12))] = 1
        for P in woody_idx.polys:
            xs = [p[0] for p in P]; ys = [p[1] for p in P]
            area = abs(sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P)))) / 2
            nn = int(area / 160)
            for _ in range(min(nn, 4000)):
                x = rnd.uniform(min(xs), max(xs)); y = rnd.uniform(min(ys), max(ys))
                if (int(x // 12), int(y // 12)) in have or exclude_fn(x, y): continue
                c = False
                for k in range(len(P)):
                    x0, y0 = P[k]; x1, y1 = P[(k + 1) % len(P)]
                    if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0): c = not c
                if not c: continue
                have[(int(x // 12), int(y // 12))] = 1
                r = rnd.random(); pts.append((x, y, 'oak' if r < 0.5 else 'pine' if r < 0.85 else 'cypress'))
    if extra is not None:     # extra scatter (the Vatican Gardens): holm oaks, pines, cypresses, palms
        have = {}
        for (x, y, k) in pts: have[(int(x // 9), int(y // 9))] = 1
        for (x, y) in extra(rnd):
            c = (int(x // 9), int(y // 9))
            if c in have or exclude_fn(x, y): continue
            have[c] = 1
            r = rnd.random(); pts.append((x, y, 'oak' if r < 0.45 else 'pine' if r < 0.78 else 'cypress' if r < 0.93 else 'palm'))
    for (x, y, kind) in pts:
        m.merge(tree(kind, x, y, height_fn(x, y), rnd))
    return m, len(pts)
