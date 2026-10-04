"""Open ground (calli, campi, fondamenta, courtyards), Istrian-stone copings and canal walls (rive)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, MultiLineString, box, Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, linemerge
from shapely.strtree import STRtree
from .world import GROUND_Z, WATER_BOTTOM, polys_of
from .mesh import MeshBuilder, triangulate
from .materials import MAT

COPING_W = 0.34
COPING_UP = 0.03
STREET_HW = ('pedestrian', 'footway', 'steps', 'living_street', 'residential', 'service', 'path', 'unclassified', 'cycleway', 'primary', 'secondary', 'tertiary')

class StreetDirs:
    """nearest street direction (for orienting the paving courses) and squares."""
    def __init__(self, world):
        o = world.o; segs = []; dirs = []
        for wid, w in o.ways.items():
            t = w.get('tags', {})
            if t.get('highway') in STREET_HW and t.get('area') != 'yes':
                P = o.way_xy(wid)
                for i in range(len(P) - 1):
                    a, b = P[i], P[i + 1]
                    if math.dist(a, b) < 0.3: continue
                    segs.append(LineString([a, b])); dirs.append(math.atan2(b[1] - a[1], b[0] - a[0]))
        self.segs = segs; self.dirs = np.array(dirs); self.tree = STRtree(segs)
        self.squares = []
        for wid, w in o.ways.items():
            t = w.get('tags', {})
            if (t.get('place') == 'square' or (t.get('highway') == 'pedestrian' and t.get('area') == 'yes')) and w['nodes'][0] == w['nodes'][-1] and len(w['nodes']) > 3:
                p = Polygon(o.way_xy(wid)).buffer(0)
                if p.area > 150:
                    r = p.minimum_rotated_rectangle; c = list(r.exterior.coords)
                    e = max(((c[i], c[i + 1]) for i in range(4)), key=lambda e: math.dist(*e))
                    self.squares.append((p, math.atan2(e[1][1] - e[0][1], e[1][0] - e[0][0])))
        self.sqtree = STRtree([s[0] for s in self.squares]) if self.squares else None

    def angle(self, x, y):
        pt = Point(x, y)
        if self.sqtree is not None:
            for i in self.sqtree.query(pt):
                if self.squares[i][0].contains(pt): return self.squares[i][1]
        i = self.tree.nearest(pt)
        return float(self.dirs[i]) if i is not None else 0.0

def _rot_uv(V, ang, ox, oy):
    c, s = math.cos(ang), math.sin(ang)
    x = V[:, 0] - ox; y = V[:, 1] - oy
    return np.c_[x * c + y * s, -x * s + y * c]

def gen_ground(world, region, mb, sd, bunion):
    """region: shapely box. bunion: union of building footprints near the region."""
    land = world.land.intersection(region)
    if land.is_empty: return {}
    open_ = land.difference(bunion) if bunion is not None else land
    open_ = open_.buffer(0)
    # rive: land boundary not under a building
    lb = world.land.boundary.intersection(region.buffer(0.5))
    if bunion is not None: lb = lb.difference(bunion.buffer(0.08))
    riva = linemerge(lb) if lb.geom_type in ('MultiLineString',) else lb
    coping = open_.intersection(riva.buffer(COPING_W, cap_style=2, join_style=2)).buffer(0) if not riva.is_empty else Polygon()
    main = open_.difference(coping).buffer(0) if not coping.is_empty else open_
    stats = dict(ground=0, coping=0, riva=0)
    # paving: one orientation per connected piece -> sub-split big pieces by streets
    for poly in polys_of(main):
        if poly.area < 0.05: continue
        poly = orient(poly.simplify(0.05, preserve_topology=True), 1.0)
        if poly.is_empty or poly.area < 0.05: continue
        rings = [list(poly.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in poly.interiors]
        rings = [_densify(R, 0.9) for R in rings]
        V, T = triangulate(rings, max_area=2.2)
        if len(T) == 0: continue
        C = V[T].mean(1)
        ang = np.array([sd.angle(c[0], c[1]) for c in C])
        # snap angle per triangle to the street; make uv per corner with that triangle's angle
        Pf = []; UVf = []
        for ti, tri in enumerate(T):
            a = ang[ti]; cc, ss = math.cos(a), math.sin(a)
            for k in tri:
                x, y = V[k]
                Pf.append((x, y, GROUND_Z)); UVf.append((x * cc + y * ss, -x * ss + y * cc))
        Pf = np.array(Pf)
        mb.add(Pf, np.arange(len(Pf)).reshape(-1, 3), N=np.tile([0, 0, 1.0], (len(Pf), 1)), UV=np.array(UVf), mat=MAT['ground'], c1=(0, 0, 0, 0))
        stats['ground'] += len(T)
    for poly in polys_of(coping):
        if poly.area < 0.01: continue
        po = orient(poly, 1.0)
        rings = [list(po.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in po.interiors]
        V, T = triangulate(rings, max_area=1.5)
        if len(T) == 0: continue
        V3 = np.c_[V, np.full(len(V), GROUND_Z + COPING_UP)]
        # uv along the nearest riva direction
        C = V.mean(0); a = sd.angle(C[0], C[1])
        mb.add(V3, T, N=np.tile([0, 0, 1.0], (len(V3), 1)), UV=_rot_uv(V, a, 0, 0), mat=MAT['coping'], c1=(0, 0, 0, 0))
        stats['coping'] += len(T)
    # canal walls
    lines = [riva] if riva.geom_type == 'LineString' else list(getattr(riva, 'geoms', []))
    for ln in lines:
        if ln.geom_type != 'LineString': continue
        cs = list(ln.coords)
        for i in range(len(cs) - 1):
            a = np.array(cs[i]); c = np.array(cs[i + 1]); L = np.linalg.norm(c - a)
            if L < 0.05: continue
            d = (c - a) / L; n = np.array([d[1], -d[0]])
            # outward normal must point to water
            mid = (a + c) / 2
            if world.land.contains(Point(*(mid + n * 0.4))): n = -n; a, c = c, a; d = -d
            ztop = GROUND_Z + COPING_UP; zs = GROUND_Z - 0.26
            u0 = float(np.dot(a, d))
            # stone coping face
            mb.add_planar([(*a, ztop), (*c, ztop), (*c, zs), (*a, zs)], [[0, 3, 2], [0, 2, 1]], (*n, 0),
                          [(u0, ztop), (u0 + L, ztop), (u0 + L, zs), (u0, zs)], mat=MAT['coping'], c1=(0, 0, 0, 0))
            # brick below, split at 0.0 and every ~2 m for the bake
            k = max(1, int(math.ceil(L / 1.5)))
            for j in range(k):
                p0 = a + d * L * j / k; p1 = a + d * L * (j + 1) / k
                zz = [zs, 0.6, 0.05, WATER_BOTTOM]
                for z0, z1 in zip(zz[:-1], zz[1:]):
                    mb.add_planar([(*p0, z0), (*p1, z0), (*p1, z1), (*p0, z1)], [[0, 3, 2], [0, 2, 1]], (*n, 0),
                                  [(u0 + L * j / k, z0), (u0 + L * (j + 1) / k, z0), (u0 + L * (j + 1) / k, z1), (u0 + L * j / k, z1)],
                                  mat=MAT['riva'], c1=(0, 0, 0, 0))
            stats['riva'] += 1
    return stats

def _densify(R, step):
    out = []
    n = len(R)
    for i in range(n):
        a = np.array(R[i][:2]); b = np.array(R[(i + 1) % n][:2]); L = np.linalg.norm(b - a)
        k = max(1, int(math.ceil(L / step)))
        for j in range(k): out.append(tuple(a + (b - a) * j / k))
    return out
