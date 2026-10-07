"""錦鏡池 and its banks: the site's own ground around the pond (the DEM has spurious 3-6 m bumps in the water), the
water surface, islands (仙人洲, 白鶴島), the 大内石, shore stones, moss banks.  Garden-local coordinates (origin = 銀閣)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from jk import prim
from . import ginkakuji_util as U

def chaikin(pts, n=1, closed=True):
    P = np.asarray(pts, float)
    for _ in range(n):
        Q = []
        m = len(P)
        for i in range(m if closed else m - 1):
            a = P[i]; b = P[(i + 1) % m]
            Q += [a * 0.75 + b * 0.25, a * 0.25 + b * 0.75]
        P = np.array(Q)
    return P

class Ground:
    """the cleaned height field near the pond (garden-local), and the pond / island shapes"""
    def __init__(self, S, GX, GY):
        self.S = S; self.GX = GX; self.GY = GY
        R = []
        def rec(q):
            if isinstance(q[0][0], (int, float)): R.append(np.array(q) - [GX, GY]); return
            for r in q: rec(r)
        rec(S.osm['water'][0]['poly'])
        outer = R[0]
        isl = [r for r in R[1:] if Polygon(r).area > 5]
        self.osm_pond = Polygon(outer, isl)
        self.outer = Polygon(chaikin(outer, 2)).buffer(0)
        self.islands = [Polygon(chaikin(r, 2)).buffer(0.15) for r in isl]
        self.pond = self.outer.difference(unary_union(self.islands))
        self.ouchi = Polygon(R[2]).centroid if len(R) > 2 else Point(44.6, 12.2)
        # the region with our own ground: the pond and a band around it
        self.region = unary_union([self.outer.buffer(3.5), self.osm_pond.buffer(3.5)]).simplify(0.2)
        # a cleaned DEM on a 0.5 m grid over the region (morphological opening removes the bumps)
        from scipy.ndimage import grey_opening, gaussian_filter
        x0, y0, x1, y1 = self.region.bounds
        self.gx0, self.gy0 = x0 - 6, y0 - 6
        xs = np.arange(self.gx0, x1 + 6, 0.5); ys = np.arange(self.gy0, y1 + 6, 0.5)
        X, Y = np.meshgrid(xs, ys)
        Z = S.ground(X + GX, Y + GY)
        O = grey_opening(Z, size=(19, 19))
        O = gaussian_filter(O, 1.5)
        self.Zc = np.minimum(Z, O + 0.04)
        self.nx = len(xs); self.ny = len(ys)
        # the water level: a little under the cleaned bank along the edge
        edge = [self.outer.exterior.interpolate(t, normalized=True).coords[0] for t in np.linspace(0, 1, 200, endpoint=False)]
        zb = np.array([self.clean(x, y) for (x, y) in edge])
        self.WL = float(np.percentile(zb, 15)) - 0.22
        self.bank = float(np.median(zb))
        shapely.prepare(self.pond); shapely.prepare(self.outer)

    def clean(self, x, y):
        fx = (x - self.gx0) / 0.5; fy = (y - self.gy0) / 0.5
        ix = int(np.clip(math.floor(fx), 0, self.nx - 2)); iy = int(np.clip(math.floor(fy), 0, self.ny - 2))
        ax = min(max(fx - ix, 0), 1); ay = min(max(fy - iy, 0), 1)
        Z = self.Zc
        return float(Z[iy, ix] * (1 - ax) * (1 - ay) + Z[iy, ix + 1] * ax * (1 - ay) + Z[iy + 1, ix] * (1 - ax) * ay + Z[iy + 1, ix + 1] * ax * ay)

    def h(self, x, y):
        """ground height: the cleaned DEM on the banks, the pond basin below the water, mounded islands"""
        p = Point(x, y)
        zc = self.clean(x, y)
        if self.outer.contains(p):
            for isl in self.islands:
                if isl.contains(p):
                    d = isl.exterior.distance(p)
                    return self.WL + 0.18 + 0.55 * min(1.0, d / 1.8) ** 0.7
            d = self.outer.exterior.distance(p)
            dd = min([d] + [i.exterior.distance(p) for i in self.islands])
            return self.WL - 0.12 - 0.55 * min(1.0, dd / 2.2) ** 0.8
        # outside: blend down to the water at the shore (banks a little above the water)
        d = self.outer.exterior.distance(p)
        zb = max(zc, self.WL + 0.2)
        if d < 0.8: return self.WL + 0.12 + (zb - self.WL - 0.12) * (d / 0.8)
        return zb

def mesh_region(B, poly, hf, res, mat='ground', surf_of=None, walk_of=None, tag='main'):
    """our own ground over a polygon: a res grid clipped to the polygon; each triangle gets the surface id surf_of(cx, cy)
    (one sub-mesh per surface); walk_of(cx, cy) -> bool adds it to the walk mesh"""
    import mapbox_earcut as earcut
    x0, y0, x1, y1 = poly.bounds
    xs = np.arange(math.floor(x0 / res) * res, x1 + res, res); ys = np.arange(math.floor(y0 / res) * res, y1 + res, res)
    prep = poly; shapely.prepare(prep)
    tris = []                                            # list of (3,2) arrays
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            c = box(xs[i], ys[j], xs[i + 1], ys[j + 1])
            if prep.contains(c):
                a, b, cc, d = (xs[i], ys[j]), (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])
                tris += [np.array([a, b, cc]), np.array([a, cc, d])]
            elif prep.intersects(c):
                g = poly.intersection(c)
                for p in (g.geoms if hasattr(g, 'geoms') else [g]):
                    if p.geom_type != 'Polygon' or p.area < 1e-4: continue
                    V = np.array(p.exterior.coords)[:-1]
                    I = earcut.triangulate_float64(V, np.array([len(V)], np.uint32)).reshape(-1, 3)
                    for t in I: tris.append(V[t])
    T = np.array(tris)                                   # (k, 3, 2)
    # weld vertices
    key = np.round(T.reshape(-1, 2) * 1000).astype(np.int64)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    V2 = uniq / 1000.0
    Z = np.array([hf(x, y) for (x, y) in V2])
    P = np.c_[V2, Z]
    I = inv.reshape(-1, 3)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    I[fn[:, 2] < 0] = I[fn[:, 2] < 0][:, ::-1]
    C = P[I].mean(1)
    sids = np.array([surf_of(x, y) for (x, y, _) in C]) if surf_of else np.zeros(len(I), int)
    from jk.core import vertex_normals
    N = vertex_normals(P, I)
    for s in np.unique(sids):
        sel = I[sids == s]
        vid, inv2 = np.unique(sel.ravel(), return_inverse=True)
        B.add(P[vid], inv2.reshape(-1, 3), mat, UV=P[vid][:, :2], N=N[vid], tag=tag, c1=(0, 0, 0, int(s)))
    if walk_of:
        w = np.array([walk_of(x, y) for (x, y, _) in C])
        sel = I[w]
        if len(sel):
            vid, inv2 = np.unique(sel.ravel(), return_inverse=True)
            B.add(P[vid] + [0, 0, 0.01], inv2.reshape(-1, 3), 'stone', tag='walk')
    return P, I

SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
        'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck']
SID = {n: i for i, n in enumerate(SURF)}

def build(B, G, paths, seed=7):
    """the ground mesh in the region, the water, shore stones; paths = shapely geometry of the garden paths (garden-local)"""
    shapely.prepare(paths)
    def surf(x, y):
        p = Point(x, y)
        if G.outer.contains(p) and not any(i.contains(p) for i in G.islands): return SID['riverbed']
        if paths.contains(p): return SID['sand']
        return SID['moss']
    inner = G.outer.buffer(-0.3); shapely.prepare(inner)
    def walk(x, y):
        p = Point(x, y)
        return not inner.contains(p) or any(i.contains(p) for i in G.islands)
    mesh_region(B, G.region, G.h, 0.5, surf_of=surf, walk_of=walk)
    # water surface (flat), with the islands as holes
    for p in (G.pond.geoms if hasattr(G.pond, 'geoms') else [G.pond]):
        ext = np.array(p.exterior.coords)[:-1]
        holes = [np.array(r.coords)[:-1] for r in p.interiors]
        prim.polygon(B, ext, G.WL, 'water', holes=holes)
        prim.polygon(B, ext, G.WL + 0.4, 'stone', holes=holes, tag='block')
    # shore stones (護岸石組): runs of stones of mixed sizes with mossy gaps, a few large ones at the points
    rng = np.random.default_rng(seed)
    shores = [G.outer.exterior] + [i.exterior for i in G.islands]
    n = 0
    for k, L in enumerate(shores):
        t = rng.uniform(0, 2)
        run = rng.uniform(3, 9); in_run = True
        while t < L.length:
            if not in_run:
                t += rng.uniform(1.5, 4.5); in_run = True; run = rng.uniform(3, 10); continue
            r_ = rng.random()
            size = rng.uniform(0.65, 0.95) if r_ < 0.1 else rng.uniform(0.4, 0.65) if r_ < 0.4 else rng.uniform(0.2, 0.38)
            q = np.array(L.interpolate(t).coords[0])
            q2 = np.array(L.interpolate(min(L.length, t + 0.3)).coords[0])
            d = q2 - q; d /= max(np.linalg.norm(d), 1e-6)
            nrm = np.array([-d[1], d[0]])
            water_side = G.outer.contains(Point(*(q + nrm * 0.4)))
            if k > 0: water_side = not water_side
            sgn = 1 if water_side else -1
            q = q + nrm * sgn * rng.uniform(-0.15, 0.35)
            zt = G.WL + rng.uniform(-0.06, 0.12) + (0.1 if size > 0.6 else 0)
            U.rock(B, (q[0], q[1], zt + size * 0.15), size, seed * 1000 + n, flat=rng.uniform(0.4, 0.7), sub=2 if size > 0.55 else 1, sink=0.55, tilt=0.3,
                   aniso=(rng.uniform(1.0, 1.6), 1.0), mat='moss_mound' if (not water_side or k > 0) and rng.random() < 0.3 else 'stone')
            n += 1
            step = size * rng.uniform(1.0, 1.6)
            t += step; run -= step
            if run < 0: in_run = False
    # 大内石 (a big flat stone standing in the water) and stones on the islands
    c = G.ouchi
    U.rock(B, (c.x, c.y, G.WL + 0.4), 1.0, 77, flat=0.55, sub=2, sink=0.2)
    for i, isl in enumerate(G.islands):
        cc = isl.centroid
        for j in range(4):
            q = (cc.x + rng.uniform(-1.2, 1.2), cc.y + rng.uniform(-1.0, 1.0))
            if isl.contains(Point(q)): U.rock(B, (q[0], q[1], G.h(*q) + 0.2), rng.uniform(0.4, 0.8), 500 + i * 10 + j, flat=0.7, sub=2, sink=0.35)
    return n
