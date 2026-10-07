"""鏡湖池 / 安民沢: the site's own ground around a pond (basin, islands, banks), the water surface, shore stones (護岸石組),
island stones.  Coordinates are garden-local (origin = the 舎利殿's centre, axes = world), z absolute.

The basin is built from the OSM pond (smoothed), plus extra water (e.g. the strip that reaches the Kinkaku's stone base)
and extra islands (rock islets that OSM does not have).  The banks follow a smoothed DEM, kept a little above the water."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, box
from shapely.ops import unary_union
from jk import prim
from . import kinkakuji_util as U

SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
        'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck']
SID = {n: i for i, n in enumerate(SURF)}

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

def polys(g):
    if g.is_empty: return []
    return [p for p in (g.geoms if hasattr(g, 'geoms') else [g]) if p.geom_type == 'Polygon']

def osm_rings(S, wid, ox, oy):
    R = []
    def rec(q):
        if isinstance(q[0][0], (int, float)): R.append(np.array(q, float) - [ox, oy]); return
        for r in q: rec(r)
    for w in S.osm['water']:
        if w['id'] == wid: rec(w['poly'])
    return R

class Pond:
    """outer: shapely Polygon of the water's outline (incl. islands), islands: list of Polygons; WL water level;
    gz(x, y) DEM (garden-local, vectorised); band: width of our own ground around the water"""
    def __init__(self, gz, outer, islands, WL, band=4.0, bank_min=0.28, depth=0.65, flat=None, isl_h=0.5, seed=0, smooth_m=6.0):
        self.gz = gz; self.WL = WL; self.bank_min = bank_min; self.depth = depth; self.isl_h = isl_h
        self.outer = outer.buffer(0)
        self.islands = [i.buffer(0) for i in islands if i.area > 0.5]
        self.water = self.outer.difference(unary_union(self.islands)) if self.islands else self.outer
        self.region = Polygon(self.outer.buffer(band, join_style=1).exterior).simplify(0.15)
        self.flat = flat or []          # [(polygon, z, blend)]: ground levelled to z inside, blended over `blend` m
        shapely.prepare(self.water); shapely.prepare(self.outer); shapely.prepare(self.region)
        for i in self.islands: shapely.prepare(i)
        self.isl_u = unary_union(self.islands) if self.islands else None
        if self.isl_u is not None: shapely.prepare(self.isl_u)
        # a smoothed DEM over the region (0.5 m grid, gaussian) for the banks
        from scipy.ndimage import gaussian_filter
        x0, y0, x1, y1 = self.region.bounds
        self.gx0, self.gy0 = x0 - 4, y0 - 4
        xs = np.arange(self.gx0, x1 + 4, 0.5); ys = np.arange(self.gy0, y1 + 4, 0.5)
        X, Y = np.meshgrid(xs, ys)
        self.Zs = gaussian_filter(gz(X, Y), smooth_m / 0.5 * 0.35)
        self.Zraw = gz(X, Y)
        self.nx = len(xs); self.ny = len(ys)
        self.rng = np.random.default_rng(seed)

    def smooth(self, x, y, raw=False):
        x = np.asarray(x, float); y = np.asarray(y, float)
        fx = (x - self.gx0) / 0.5; fy = (y - self.gy0) / 0.5
        ix = np.clip(np.floor(fx).astype(int), 0, self.nx - 2); iy = np.clip(np.floor(fy).astype(int), 0, self.ny - 2)
        ax = np.clip(fx - ix, 0, 1); ay = np.clip(fy - iy, 0, 1)
        Z = self.Zraw if raw else self.Zs
        return Z[iy, ix] * (1 - ax) * (1 - ay) + Z[iy, ix + 1] * ax * (1 - ay) + Z[iy + 1, ix] * (1 - ax) * ay + Z[iy + 1, ix + 1] * ax * ay

    def h(self, x, y):
        """ground height (vectorised): basin under the water, mounded islands, banks above the water"""
        x = np.atleast_1d(np.asarray(x, float)); y = np.atleast_1d(np.asarray(y, float))
        pts = shapely.points(x, y)
        in_out = shapely.contains(self.outer, pts) | shapely.touches(self.outer, pts)
        d_shore = shapely.distance(self.outer.exterior, pts)
        z = np.empty(len(x))
        # banks: the smoothed DEM, at least bank_min above the water, falling to the waterline over 0.9 m
        zb = np.maximum(self.smooth(x, y), self.WL + self.bank_min)
        # towards the region's edge go back to the raw DEM so the generic terrain meets us
        d_edge = shapely.distance(self.region.exterior, pts)
        w_edge = np.clip(d_edge / 1.5, 0, 1)
        zb = self.smooth(x, y, raw=True) * (1 - w_edge) + zb * w_edge
        k = np.clip(d_shore / 0.9, 0, 1)
        z_bank = self.WL + 0.06 + (zb - self.WL - 0.06) * (k * k * (3 - 2 * k))
        z[:] = z_bank
        # water: a basin deepening away from every shore
        if self.isl_u is not None:
            d_isl = shapely.distance(self.isl_u.boundary, pts)
            in_isl = shapely.contains(self.isl_u, pts)
        else:
            d_isl = np.full(len(x), 99.0); in_isl = np.zeros(len(x), bool)
        dd = np.minimum(d_shore, d_isl)
        zw = self.WL - 0.12 - self.depth * np.power(np.clip(dd / 2.5, 0, 1), 0.8)
        sel = in_out & ~in_isl
        z[sel] = zw[sel]
        # islands: low mounds
        zi = self.WL + 0.1 + self.isl_h * np.power(np.clip(d_isl / 2.0, 0, 1), 0.7)
        sel = in_out & in_isl
        z[sel] = zi[sel]
        for (poly, zf, blend) in self.flat:
            dist = shapely.distance(poly, pts)
            w = np.clip(1 - dist / blend, 0, 1)
            m = (w > 0) & ~(in_out & ~in_isl)
            z[m] = z[m] * (1 - w[m]) + zf * w[m]
        return z

def mesh_region(B, poly, hf, res, mat='ground', surf_of=None, walk_of=None, tag='main'):
    """our own ground over a polygon: a res grid clipped to it; each triangle gets surf_of(cx, cy) (vectorised, -> ids);
    walk_of(cx, cy) -> bool array adds those triangles to the walk mesh"""
    import mapbox_earcut as earcut
    x0, y0, x1, y1 = poly.bounds
    xs = np.arange(math.floor(x0 / res) * res, x1 + res, res); ys = np.arange(math.floor(y0 / res) * res, y1 + res, res)
    shapely.prepare(poly)
    nx, ny = len(xs) - 1, len(ys) - 1
    cells = shapely.box(*[a.ravel() for a in np.meshgrid(xs[:-1], ys[:-1])], *[a.ravel() for a in np.meshgrid(xs[1:], ys[1:])])
    inside = shapely.contains(poly, cells)
    touch = shapely.intersects(poly, cells) & ~inside
    tris = []
    ii = np.where(inside)[0]
    X0, Y0 = np.meshgrid(xs[:-1], ys[:-1]); X0 = X0.ravel(); Y0 = Y0.ravel()
    a = np.c_[X0[ii], Y0[ii]]; b = a + [res, 0]; c = a + [res, res]; d = a + [0, res]
    T = np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
    tris = [T]
    for k in np.where(touch)[0]:
        g = poly.intersection(cells[k])
        for p in polys(g):
            if p.area < 1e-4: continue
            V = np.array(p.exterior.coords)[:-1]
            I = earcut.triangulate_float64(V, np.array([len(V)], np.uint32)).reshape(-1, 3)
            if len(I): tris.append(V[I])
    T = np.concatenate(tris)
    key = np.round(T.reshape(-1, 2) * 1000).astype(np.int64)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    V2 = uniq / 1000.0
    Z = hf(V2[:, 0], V2[:, 1])
    P = np.c_[V2, Z]
    I = inv.reshape(-1, 3)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    I[fn[:, 2] < 0] = I[fn[:, 2] < 0][:, ::-1]
    A = np.linalg.norm(fn, axis=1); I = I[A > 1e-9]
    C = P[I].mean(1)
    sids = surf_of(C[:, 0], C[:, 1]) if surf_of else np.zeros(len(I), int)
    from jk.core import vertex_normals
    N = vertex_normals(P, I)
    for s in np.unique(sids):
        sel = I[sids == s]
        vid, inv2 = np.unique(sel.ravel(), return_inverse=True)
        B.add(P[vid], inv2.reshape(-1, 3), mat, UV=P[vid][:, :2], N=N[vid], tag=tag, c1=(0, 0, 0, int(s)))
    if walk_of is not None:
        w = walk_of(C[:, 0], C[:, 1])
        sel = I[w]
        if len(sel):
            vid, inv2 = np.unique(sel.ravel(), return_inverse=True)
            B.add(P[vid] + [0, 0, 0.01], inv2.reshape(-1, 3), 'stone', tag='walk')
    return P, I

def water(B, pond, block=True):
    for p in polys(pond.water):
        ext = np.array(p.exterior.coords)[:-1]
        holes = [np.array(r.coords)[:-1] for r in p.interiors]
        prim.polygon(B, ext, pond.WL, 'water', holes=holes)
        if block: prim.polygon(B, ext, pond.WL + 0.45, 'stone', holes=holes, tag='block')

def shore_stones(B, pond, seed=7, skip=None, mossy=0.3, big=0.1, run=(3, 10), gap=(1.2, 4.0), scale=1.0, isl_stones=4):
    """runs of stones along every shore, mixed sizes, mossy ones on the land side; a few big ones at the points.
    skip: shapely geometry where no stones go (the Kinkaku's base, landings)"""
    rng = np.random.default_rng(seed)
    shores = [pond.outer.exterior] + [i.exterior for i in pond.islands]
    n = 0
    for k, L in enumerate(shores):
        t = rng.uniform(0, 2)
        left = rng.uniform(*run); in_run = True
        while t < L.length:
            if not in_run:
                t += rng.uniform(*gap); in_run = True; left = rng.uniform(*run); continue
            r_ = rng.random()
            size = (rng.uniform(0.7, 1.05) if r_ < big else rng.uniform(0.42, 0.68) if r_ < 0.42 else rng.uniform(0.22, 0.4)) * scale
            q = np.array(L.interpolate(t).coords[0])
            if skip is not None and skip.contains(Point(q)):
                t += 0.6; continue
            q2 = np.array(L.interpolate(min(L.length, t + 0.3)).coords[0])
            d = q2 - q; d /= max(np.linalg.norm(d), 1e-6)
            nrm = np.array([-d[1], d[0]])
            water_side = pond.water.contains(Point(*(q + nrm * 0.4)))
            sgn = 1 if water_side else -1
            q = q + nrm * sgn * rng.uniform(-0.12, 0.3)
            zt = pond.WL + rng.uniform(-0.05, 0.12) + (0.1 if size > 0.6 else 0)
            U.rock(B, (q[0], q[1], zt + size * 0.15), size, seed * 1000 + n, flat=rng.uniform(0.4, 0.7), sub=2 if size > 0.6 else 1, sink=0.55, tilt=0.3,
                   aniso=(rng.uniform(1.0, 1.6), 1.0), mat='moss_mound' if rng.random() < mossy else 'stone')
            n += 1
            step = size * rng.uniform(1.0, 1.5)
            t += step; left -= step
            if left < 0: in_run = False
    for i, isl in enumerate(pond.islands):
        cc = isl.centroid
        for j in range(isl_stones):
            q = (cc.x + rng.uniform(-1.5, 1.5), cc.y + rng.uniform(-1.2, 1.2))
            if isl.buffer(-0.4).contains(Point(q)):
                U.rock(B, (q[0], q[1], float(pond.h(*q)[0]) + 0.15), rng.uniform(0.35, 0.75), 500 + seed * 50 + i * 10 + j, flat=0.75, sub=2, sink=0.35)
    return n
