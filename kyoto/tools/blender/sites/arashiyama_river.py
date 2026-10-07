"""嵐山: the 大堰川 / 桂川 as the site models it — water surfaces at their own levels (the pool above 葛野大堰, the rapids
below it, the sill under 渡月橋, the lower weir, the south channel round 中之島, the 西高瀬川 intake along the north
bank), the river bed, sloped stone revetments on every land edge, the weirs with their white cascades, gravel bars and
grassy islands.  The generic terrain and water are cut away under all of it (S.cut).

Levels are set per reach (no survey data): knots in x, clamped under the banks (DEM 1.6 m outside the water edge) and
never rising downstream.  The ends meet the generic water at the bounds (west, the gorge) and at x = -7080 (east)."""
import math
import numpy as np
import shapely
import shapely.ops
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, box as sbox
from jk import prim
import sites.machiya as M
import sites.arashiyama_util as U

X_W, X_E = -8114.0, -7080.0          # modelled reach (the cut ends exactly here, generic water continues beyond)
MAIN_IDS = [519319738, 519319739, 519319741, 209937000]
SOUTH_ID = 519319768
INTAKE_ID = 297972444
BAND = 1.6                            # revetment band beyond the water edge (generic terrain cut there too)

def poly_of(S, cat, fid):
    for f in S.osm[cat]:
        if f['id'] == fid: return Polygon(f['poly'][0][0]).buffer(0)
    raise KeyError(fid)

def way_line(S, cat, fid):
    for f in S.osm[cat]:
        if f['id'] == fid: return LineString(f['line'][0])
    raise KeyError(fid)

def extend(L, d):
    c = np.asarray(L.coords, float)
    a = c[0] - c[1]; a /= np.linalg.norm(a); b = c[-1] - c[-2]; b /= np.linalg.norm(b)
    return LineString(np.vstack([c[0] + a * d, c[1:-1], c[-1] + b * d]) if len(c) > 2 else np.vstack([c[0] + a * d, c[-1] + b * d]))

def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == 'Polygon': return [g]
    return [p for p in getattr(g, 'geoms', []) if p.geom_type == 'Polygon' and p.area > 1e-3]

def ring_list(g):
    g = max(polys(g), key=lambda p: p.area)
    return [[float(x), float(y)] for x, y in list(g.exterior.coords)[:-1]]

def densify(coords, step):
    c = np.asarray(coords, float); out = []
    for a, b in zip(c[:-1], c[1:]):
        L = np.linalg.norm(b - a); k = max(1, int(math.ceil(L / step)))
        for i in range(k): out.append(a + (b - a) * i / k)
    out.append(c[-1])
    return np.array(out)

def cell_union(g, cell=2.0):
    """the union of the grid cells (even metres, the generic terrain's grid) that g touches"""
    x0, y0, x1, y1 = g.bounds
    xs = np.arange(math.floor(x0 / cell) * cell, x1 + cell, cell); ys = np.arange(math.floor(y0 / cell) * cell, y1 + cell, cell)
    X, Y = np.meshgrid(xs[:-1], ys[:-1])
    boxes = shapely.box(X.ravel(), Y.ravel(), X.ravel() + cell, Y.ravel() + cell)
    shapely.prepare(g)
    hit = shapely.intersects(g, boxes)
    ov = shapely.area(shapely.intersection(boxes[hit], g)) > 0.02
    return shapely.unary_union(boxes[hit][ov])

def grid_mesh(P, cell=4.0):
    """exact triangulation of polygon P (with holes) on a square grid: cells clipped to P, each piece earcut.
    -> (V (n,2), I (m,3)) with shared vertices merged per piece"""
    import mapbox_earcut as earcut
    x0, y0, x1, y1 = P.bounds
    xs = np.arange(math.floor(x0 / cell) * cell, x1 + cell, cell); ys = np.arange(math.floor(y0 / cell) * cell, y1 + cell, cell)
    X, Y = np.meshgrid(xs[:-1], ys[:-1])
    boxes = shapely.box(X.ravel(), Y.ravel(), X.ravel() + cell, Y.ravel() + cell)
    shapely.prepare(P)
    hit = shapely.intersects(P, boxes)
    Vs = []; Is = []; off = 0
    inside = shapely.contains(P, boxes)
    for bx, full in zip(boxes[hit], inside[hit]):
        if full:
            q = np.asarray(bx.exterior.coords)[:-1]
            Vs.append(q); Is.append(np.array([[0, 1, 2], [0, 2, 3]]) + off); off += 4
            continue
        g = P.intersection(bx)
        for p in polys(g):
            rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(r.coords)[:-1] for r in p.interiors]
            V = np.concatenate(rings)
            if len(V) < 3: continue
            ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
            I = earcut.triangulate_float64(V, ends).reshape(-1, 3)
            if len(I) == 0: continue
            Vs.append(V); Is.append(I + off); off += len(V)
    if not Vs: return np.zeros((0, 2)), np.zeros((0, 3), int)
    V = np.concatenate(Vs); I = np.concatenate(Is)
    # face up
    a = V[I[:, 1]] - V[I[:, 0]]; b = V[I[:, 2]] - V[I[:, 0]]
    cz = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    I[cz < 0] = I[cz < 0][:, ::-1]
    return V, I

class River:
    def __init__(self, S, forbid=None):
        self.S = S
        self.forbid = forbid                       # the neighbour's polygons: nothing of ours inside
        clip = sbox(X_W, 2600.0, X_E, 3400.0)
        main = shapely.unary_union([poly_of(S, 'water', i) for i in MAIN_IDS]).buffer(0.05).buffer(-0.05).intersection(clip)
        south = poly_of(S, 'water', SOUTH_ID).intersection(clip)
        # the intake channel: OSM draws it 2 m wide; the channel is ~3.4 m between concrete walls, widened to the north
        it = poly_of(S, 'water', INTAKE_ID)
        self.intake_line = self.centreline(it)
        intake = self.intake_line.buffer(1.7, cap_style='flat').difference(main.buffer(1.2))
        intake = max(polys(intake), key=lambda p: p.area)
        main = main.difference(south.buffer(0.01))
        self.ch = {'main': max(polys(main), key=lambda p: p.area), 'south': max(polys(south), key=lambda p: p.area), 'intake': intake}
        self.clip = clip
        self.all = shapely.unary_union(list(self.ch.values())).buffer(0.02).buffer(-0.02)
        # weirs (OSM), extended through the water
        self.kadono = extend(way_line(S, 'waterways', 154492060), 25.0)
        self.sill = extend(way_line(S, 'waterways', 1246863418), 12.0)
        self.lower = extend(way_line(S, 'waterways', 519319733), 12.0)
        self.sw1 = extend(way_line(S, 'waterways', 519319703), 6.0)
        self.sw2 = extend(way_line(S, 'waterways', 519319702), 6.0)
        # knots (x, z) per reach; clamped below
        # (the GSI 10 m DEM's interpolated water surface at y=3000, lowered ~1.3 m so the deck of 渡月橋 stands ~4 m above
        # the water as in the photographs, the step at each weir; the lowering tapers to 0 at the east end)
        self.knots = {
            ('main', 0): [(X_W, None), (-7880.0, 35.8), (-7520.0, 35.8)],
            ('main', 1): [(-7525.0, 35.0), (-7450.0, 34.25), (-7420.0, 33.6), (-7395.0, 33.0), (-7360.0, 32.85)],
            ('main', 2): [(-7385.0, 32.45), (-7330.0, 31.9), (-7300.0, 31.55), (-7250.0, 30.95), (-7205.0, 30.65)],
            ('main', 3): [(-7215.0, 30.25), (-7160.0, 30.12), (X_E, None)],
            ('south', 0): [(-7560.0, 35.8), (-7480.0, 35.6), (-7440.0, 35.2), (-7400.0, 34.7), (-7330.0, 34.1)],
            ('south', 1): [(-7340.0, 33.6), (-7280.0, 32.9), (-7240.0, 32.3), (-7190.0, 31.7)],
            ('south', 2): [(-7200.0, 31.2), (-7160.0, 30.8), (-7120.0, 30.4), (-7060.0, 30.2)],
            ('intake', 0): [(-7530.0, 35.6), (-7390.0, 35.5)],
        }
        self.pieces = self.split()
        self.levels()

    @staticmethod
    def centreline(P):
        """a long thin polygon's centre line: midpoints of the minimum rectangle's long axis, sampled"""
        cx, cy = P.centroid.x, P.centroid.y
        r = P.minimum_rotated_rectangle
        xs, ys = r.exterior.coords.xy
        e0 = np.array([xs[1] - xs[0], ys[1] - ys[0]]); e1 = np.array([xs[2] - xs[1], ys[2] - ys[1]])
        d = e0 if np.linalg.norm(e0) > np.linalg.norm(e1) else e1
        d = d / np.linalg.norm(d); n = np.array([-d[1], d[0]])
        L = max(np.linalg.norm(e0), np.linalg.norm(e1))
        pts = []
        for t in np.linspace(-L / 2 + 0.5, L / 2 - 0.5, max(3, int(L / 4))):
            c = np.array([cx, cy]) + d * t
            seg = LineString([c - n * 20, c + n * 20]).intersection(P)
            if seg.is_empty: continue
            pts.append((seg.centroid.x, seg.centroid.y))
        return LineString(pts)

    # ---------------------------------------------------------------- reaches
    def zone_of(self, ch, x, y):
        """reach index of points (vectorised): which side of the weir lines"""
        x = np.atleast_1d(np.asarray(x, float)); y = np.atleast_1d(np.asarray(y, float))
        def west_of(L):
            # signed side by the line's x at the point's y (the weirs run roughly north-south)
            c = np.asarray(L.coords)
            o = np.argsort(c[:, 1])
            return x < np.interp(y, c[o, 1], c[o, 0])
        if ch == 'main':
            z = np.full(len(x), 3)
            z[west_of(self.lower)] = 2
            z[west_of(self.sill)] = 1
            z[west_of(self.kadono)] = 0
            return z
        if ch == 'south':
            z = np.full(len(x), 2)
            z[west_of(self.sw2)] = 1
            z[west_of(self.sw1)] = 0
            return z
        return np.zeros(len(x), int)

    def split(self):
        out = []
        for ch, P in self.ch.items():
            lines = {'main': [self.kadono, self.sill, self.lower], 'south': [self.sw1, self.sw2], 'intake': []}[ch]
            parts = [P]
            for L in lines:
                nxt = []
                for p in parts:
                    try: g = shapely.ops.split(p, L)
                    except Exception: g = p
                    nxt += polys(g)
                parts = nxt
            for p in parts:
                c = p.representative_point()
                out.append((ch, int(self.zone_of(ch, c.x, c.y)[0]), p))
        return out

    def bank_min(self, ch):
        """lowest bank top along x (DEM BAND outside the land edges of this channel), smoothed; -> (xs, z)"""
        P = self.ch[ch]
        others = shapely.unary_union([q for k, q in self.ch.items() if k != ch]).buffer(1.0)
        pts = []
        for ring in [P.exterior] + list(P.interiors):
            c = densify(np.asarray(ring.coords), 2.0)
            for a, b in zip(c[:-1], c[1:]):
                m = (a + b) / 2
                if others.contains(Point(m)) or m[0] < X_W + 1 or m[0] > X_E - 1: continue
                d = b - a; L = np.linalg.norm(d)
                if L < 1e-6: continue
                n = np.array([d[1], -d[0]]) / L
                q = m + n * BAND
                if P.contains(Point(q)): q = m - n * BAND
                pts.append((m[0], float(self.S.ground(*q))))
        pts = np.array(pts)
        xs = np.arange(X_W, X_E + 5, 5.0)
        z = np.full(len(xs), 99.0)
        for i, x in enumerate(xs):
            sel = np.abs(pts[:, 0] - x) < 9.0
            if sel.any(): z[i] = np.percentile(pts[sel, 1], 15)
        return xs, z

    def levels(self):
        S = self.S
        # the generic water level at the open ends (DEM at the banks minus 0.35, as gen/ground.py)
        def gen_level(x):
            P = self.ch['main']
            seg = LineString([(x, 2600), (x, 3400)]).intersection(P.buffer(3.0))
            ys = [c[1] for g in (getattr(seg, 'geoms', [seg])) for c in g.coords]
            return 0.5 * (float(S.ground(x, min(ys))) + float(S.ground(x, max(ys)))) - 0.35
        # west: the generic river level in the enclave above the weir (pipeline): 35.8 + max(-7880 - x, 0) * 0.003
        self.gen_w = 35.8 + max(-7880.0 - X_W, 0.0) * 0.003; self.gen_e = gen_level(X_E - 0.5)
        self.knots[('main', 0)] = [(X_W, self.gen_w), (-7880.0, 35.8), (-7520.0, 35.8)]
        self.knots[('main', 3)][-1] = (X_E, self.gen_e)
        self.prof = {}
        for ch in self.ch:
            xs, zb = self.bank_min(ch)
            for (c, zi), kn in self.knots.items():
                if c != ch: continue
                kx = np.array([k[0] for k in kn]); kz = np.array([k[1] for k in kn])
                z = np.interp(xs, kx, kz)
                # under the banks (not at the open ends where the generic level rules)
                clampz = zb - 0.3
                if ch == 'main' and zi == 0: clampz = np.where(xs < -7860, 99.0, clampz)
                if ch == 'main' and zi == 3: clampz = np.where(xs > X_E - 25, 99.0, clampz)
                z = np.minimum(z, clampz)
                # never rising downstream (except the gorge ramp, which falls toward the pool anyway)
                z = np.minimum.accumulate(z) if not (ch == 'main' and zi == 0) else z
                self.prof[(ch, zi)] = (xs, z)
        print('river levels: gen west %.2f east %.2f' % (self.gen_w, self.gen_e),
              {k: (round(float(np.interp(-7395, *v)), 2)) for k, v in self.prof.items()})

    def zw(self, ch, zi, x):
        xs, z = self.prof[(ch, zi)]
        return np.interp(np.asarray(x, float), xs, z)

    def level_at(self, x, y):
        """water level at a point (the channel whose water contains it, else the nearest)"""
        p = Point(x, y)
        best = None
        for ch, zi, P in self.pieces:
            d = P.distance(p)
            if best is None or d < best[0]: best = (d, ch, zi)
        return float(self.zw(best[1], best[2], x))

    # ---------------------------------------------------------------- geometry
    def build(self, B, bridges=()):
        S = self.S
        self.water_and_bed(B)
        foot = self.revetments(B)
        self.weirs(B)
        self.shoals(B)
        self.intake_walls(B)
        # site edits: the generic terrain goes in whole 2 m cells of its grid (no triangles straddle the edge), the
        # generic water with it; our own ground fills the cells beyond the revetments
        need = shapely.unary_union([foot, self.all, self.ch['intake'].buffer(0.3)]).intersection(sbox(X_W, 2600, X_E, 3400))
        cells = cell_union(need, 2.0).intersection(sbox(X_W, 2600, X_E, 3400))
        if self.forbid is not None: cells = cells.difference(self.forbid.buffer(0.05))
        self.cut = cells
        for p in polys(cells):
            S.cut.append([[[float(a), float(b)] for a, b in list(p.exterior.coords)[:-1]]] + [[[float(a), float(b)] for a, b in list(r.coords)[:-1]] for r in p.interiors])
        fill = cells.difference(foot.buffer(-0.01)).difference(self.all).difference(self.ch['intake'].buffer(0.3))
        U.ground_mesh(B, S, fill, 'grass', cell=2.0, dz=0.02)
        # blockers over the water and on the embankments (the walk map blocks generic water too; this keeps it so under
        # our cut), open under the bridges and at the landing
        blk = self.all.buffer(-0.2).union(foot.buffer(-0.05)).union(self.ch['intake'].buffer(0.25))
        for g in bridges: blk = blk.difference(g)
        for p in polys(blk):
            V, I = grid_mesh(p, 12.0)
            if len(V): B.add(np.c_[V, np.full(len(V), self.level_at(*p.representative_point().coords[0]) + 0.3)], I, 'stone', tag='block')

    def water_and_bed(self, B):
        for ch, zi, P in self.pieces:
            V, I = grid_mesh(P, 4.0)
            if len(V) == 0: continue
            Z = self.zw(ch, zi, V[:, 0])
            B.add(np.c_[V, Z], I, 'water', UV=V.copy(), N=np.tile([0, 0, 1.0], (len(V), 1)), tag='main')
            # the bed: deeper away from the banks
            dmax = {('main', 0): 3.2, ('main', 1): 1.0, ('main', 2): 1.1, ('main', 3): 1.3}.get((ch, zi), 0.8 if ch == 'south' else 0.7)
            Vb, Ib = grid_mesh(P.buffer(0.6).intersection(self.clip), 6.0)
            if len(Vb) == 0: continue
            Zb = self.bed_at(ch, zi, Vb, P, dmax)
            B.add(np.c_[Vb, Zb], Ib, 'ground', UV=Vb.copy(), smooth=True, tag='main', c1=(0, 0, 0, 10))

    def bed_at(self, ch, zi, V, P, dmax):
        Z = self.zw(ch, zi, V[:, 0])
        d = shapely.distance(shapely.points(V), P.exterior)
        for r in P.interiors: d = np.minimum(d, shapely.distance(shapely.points(V), r))
        inside = shapely.contains_xy(P, V[:, 0], V[:, 1])
        d = np.where(inside, d, 0.0)
        return Z - (np.clip(0.35 + d * 0.22, 0.35, dmax) if ch != 'intake' else 0.8)

    def revetments(self, B):
        """sloped stone banks on every land edge: from the band edge (generic ground height) down below the water;
        a granite coping where a promenade runs along (north bank, 中之島)"""
        S = self.S
        P = self.ch['main'].union(self.ch['south']).buffer(0.02).buffer(-0.02)
        Q = []; UV = []; acc = 0.0
        forbid = self.forbid
        intake = self.ch['intake']
        for ring in [P.exterior] + list(P.interiors):
            pts = densify(np.asarray(ring.coords), 1.5)
            for a, b in zip(pts[:-1], pts[1:]):
                m = (a + b) / 2
                if m[0] < X_W + 0.3 or m[0] > X_E - 0.3: continue                # open ends
                d = b - a; L = np.linalg.norm(d)
                if L < 1e-6: continue
                n = np.array([d[1], -d[0]]) / L
                if P.contains(Point(m + n * 0.3)): n = -n                           # outward (to land)
                band = BAND
                if forbid is not None: band = min(band, forbid.distance(Point(m)) - 0.1)
                band = max(0.2, min(band, intake.distance(Point(m)) - 0.4))
                ta, tb = a + n * band, b + n * band
                za, zb = float(S.ground(*ta)) + 0.02, float(S.ground(*tb)) + 0.02
                wa = self.level_at(*a) ; wb = wa
                ba, bb = a - n * 0.8, b - n * 0.8
                # face: band edge (top) -> water edge -> under water
                Q.append([(ta[0], ta[1], za), (tb[0], tb[1], zb), (b[0], b[1], wb - 0.15), (a[0], a[1], wa - 0.15)])
                UV.append([(acc, za), (acc + L, zb), (acc + L, wb - 0.15 - band), (acc, wa - 0.15 - band)])
                Q.append([(a[0], a[1], wa - 0.15), (b[0], b[1], wb - 0.15), (bb[0], bb[1], wb - 1.0), (ba[0], ba[1], wa - 1.0)])
                UV.append([(acc, wa - 0.15 - band), (acc + L, wb - 0.15 - band), (acc + L, wb - 1.0 - band - 0.8), (acc, wa - 1.0 - band - 0.8)])
                acc += L
        Q = np.array(Q); UV = np.array(UV)
        foot = shapely.unary_union([Polygon(q[:2, :2].tolist() + q[2:, :2].tolist()).buffer(0.01) for q in Q[0::2]])
        # orient each quad to face up/out (toward the water side): normal z > 0
        I = []
        for k in range(len(Q)):
            q = Q[k]; fn = np.cross(q[1] - q[0], q[2] - q[0])
            if fn[2] < 0: Q[k] = q[[1, 0, 3, 2]]; UV[k] = UV[k][[1, 0, 3, 2]]
        M.quads(B, Q, 'stone', UV=UV, tag='main')
        return foot

    def weirs(self, B):
        """葛野大堰: a concrete crest with the white cascade down its downstream face, a rubble apron, the line of stakes
        in the pool above it, the fish pass / intake gate blocks at the north end; the ground sill below the bridge
        and the lower weir: low riffles"""
        S = self.S
        for (L, ch, zu, zd, face, stakes) in ((self.kadono, 'main', 0, 1, 3.0, True), (self.sill, 'main', 1, 2, 1.2, False), (self.lower, 'main', 2, 3, 2.4, False),
                                             (self.sw1, 'south', 0, 1, 1.2, False), (self.sw2, 'south', 1, 2, 1.2, False)):
            W = self.ch[ch]
            seg = L.intersection(W.buffer(0.3))
            for g in (getattr(seg, 'geoms', [seg])):
                if g.geom_type != 'LineString' or g.length < 1.0: continue
                c = densify(np.asarray(g.coords), 1.0)
                P0 = []; P1 = []; P2 = []; P3 = []
                for i, p in enumerate(c):
                    t = c[min(i + 1, len(c) - 1)] - c[max(i - 1, 0)]; t /= max(np.linalg.norm(t), 1e-9)
                    n = np.array([t[1], -t[0]])
                    if n[0] < 0: n = -n                                  # downstream = east
                    z_up = float(self.zw(ch, zu, p[0] - 1.0)); z_dn = float(self.zw(ch, zd, p[0] + face))
                    P0.append((*(p - n * 0.6), z_up - 0.12)); P1.append((*(p + n * 0.25), z_up - 0.08))
                    P2.append((*(p + n * face), z_dn - 0.05)); P3.append((*(p + n * (face + 2.5)), z_dn - 0.25))
                P0, P1, P2, P3 = map(np.array, (P0, P1, P2, P3))
                k = len(c)
                def strip(A, Bq, mat, tag='main', c0=(255, 255, 255, 0)):
                    Q = np.stack([A[:-1], A[1:], Bq[1:], Bq[:-1]], 1)
                    for j in range(len(Q)):
                        fn = np.cross(Q[j][1] - Q[j][0], Q[j][2] - Q[j][0])
                        if fn[2] < 0: Q[j] = Q[j][[1, 0, 3, 2]]
                    M.quads(B, Q, mat, tag=tag, c0=c0)
                strip(P0, P1, 'curb')                                     # concrete crest
                bright = (235, 240, 238) if face > 2.0 else (150, 166, 168)
                strip(P1, P2, 'white_paint', c0=M.paint_tint(bright, base=(0.7, 0.68, 0.62)))   # the cascade sheet
                strip(P2 + [0, 0, 0.06], P3 + [0, 0, 0.04], 'white_paint', tag='detail', c0=M.paint_tint((200, 214, 212), base=(0.7, 0.68, 0.62)))   # foam
                if stakes:
                    # the line of stakes ~16 m upstream in the pool (aerial photos)
                    for i in range(0, k, 3):
                        p = c[i]
                        t = c[min(i + 1, k - 1)] - c[max(i - 1, 0)]; t /= max(np.linalg.norm(t), 1e-9)
                        n = np.array([t[1], -t[0]]);  n = n if n[0] > 0 else -n
                        q = p - n * 16.0
                        if not W.contains(Point(q)): continue
                        zz = float(self.zw(ch, zu, q[0]))
                        prim.cyl(B, (q[0], q[1], zz - 1.5), (q[0], q[1], zz + 0.45), 0.09, 0.08, 6, 'wood_dark', tag='detail')
            if L is self.kadono:
                self.kadono_gate(B)
                self.apron_rocks(B, L, W, zd)

    def kadono_gate(self, B):
        """the intake gate and fish-pass blocks at the north end of 葛野大堰 (concrete), next to the 西高瀬川 intake"""
        c = np.asarray(self.kadono.coords)
        top = c[np.argmax(c[:, 1])]
        W = self.ch['main']
        p = np.array(shapely.ops.nearest_points(W.exterior, Point(top))[0].coords[0])
        z = float(self.zw('main', 0, p[0] - 2))
        with __import__('jk').Frame(B, p[0], p[1] - 3.0, z, math.radians(-8)):
            M.hbox(B, -3.5, 3.5, -1.2, 1.2, -1.5, 1.3, 'curb')
            M.hbox(B, -1.0, 4.5, -4.0, -1.2, -1.5, 0.9, 'curb')
            M.hbox(B, -3.6, 3.6, -1.3, 1.3, 1.3, 1.45, 'curb', tag='detail')
            for u in (-2.5, 0.0, 2.5):
                M.hbox(B, u - 0.15, u + 0.15, -0.15, 0.15, 1.45, 2.6, 'metal_grey', tag='detail')
            M.hbox(B, -3.0, 3.0, -0.2, 0.2, 2.6, 2.8, 'metal_grey', tag='detail')

    def apron_rocks(self, B, L, W, zd):
        rng = np.random.default_rng(5)
        seg = L.intersection(W)
        for g in getattr(seg, 'geoms', [seg]):
            if g.geom_type != 'LineString': continue
            for t in np.arange(1.0, g.length, 2.2):
                p = np.array(g.interpolate(t).coords[0]) + [rng.uniform(4.5, 7.0), rng.uniform(-0.8, 0.8)]
                if not W.contains(Point(p)) or rng.random() < 0.35: continue
                z = float(self.zw('main', 1, p[0]))
                prim.rock(B, (p[0], p[1], z - 0.05), rng.uniform(0.5, 1.0), int(rng.integers(1 << 20)), 'stone', tag='detail', flat=0.5)

    def shoals(self, B):
        """gravel bars and grassy islands in the rapids (between the weir and the bridge, along 中之島 under the bridge)"""
        S = self.S
        W = self.ch['main']
        specs = [  # centre, half sizes (along, across), yaw (deg), surface, height above water
            ((-7452.0, 3008.0), (24.0, 6.5), -5, 'grass', 0.25),
            ((-7470.0, 2955.0), (9.0, 4.0), 10, 'gravel', 0.12),
            ((-7425.0, 2975.0), (7.0, 3.0), 0, 'gravel', 0.1),
            ((-7402.0, 2948.0), (8.0, 5.0), 80, 'grass', 0.3),      # under the bridge's south end (the reed bank)
            ((-7355.0, 2958.0), (16.0, 4.5), 8, 'grass', 0.25),
            ((-7330.0, 3040.0), (11.0, 3.5), 4, 'gravel', 0.12),
            ((-7280.0, 2982.0), (14.0, 4.0), 12, 'gravel', 0.12),
        ]
        self.shoal_polys = []
        rng = np.random.default_rng(11)
        for (c, (a, b), yaw, surf, h) in specs:
            ang = np.linspace(0, 2 * math.pi, 28, endpoint=False)
            r = 1 + 0.12 * np.sin(ang * 3 + rng.uniform(0, 6)) + 0.08 * np.sin(ang * 5 + rng.uniform(0, 6))
            cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
            pts = np.c_[a * r * np.cos(ang), b * r * np.sin(ang)]
            pts = pts @ np.array([[cy, sy], [-sy, cy]]) + c
            P = Polygon(pts).intersection(W.buffer(-1.0))
            for p in polys(P):
                self.shoal_polys.append(p)
                V, I = grid_mesh(p, 2.0)
                zi = int(self.zone_of('main', *p.centroid.coords[0])[0])
                zwv = self.zw('main', zi, V[:, 0])
                d = shapely.distance(shapely.points(V), p.exterior)
                Z = zwv - 0.25 + np.clip(d * 0.35, 0, h + 0.25)
                sid = {'grass': 7, 'gravel': 5}[surf]
                B.add(np.c_[V, Z], I, 'ground', UV=V.copy(), smooth=True, tag='main', c1=(0, 0, 0, sid))
                if surf == 'grass':
                    # reeds: a few low clumps
                    for k in range(int(p.area / 12)):
                        q = np.array(p.representative_point().coords[0]) + rng.normal(0, [a * 0.35, b * 0.3])
                        if not p.buffer(-0.8).contains(Point(q)): continue
                        U.blob(B, (q[0], q[1], float(Z.mean()) + 0.2), rng.uniform(0.9, 1.6), rng, mat='hedge', tag='detail', flat=0.6)

    def intake_walls(self, B):
        """西高瀬川 intake: vertical concrete walls with a coping, 0.7 m above its water"""
        P = self.ch['intake']
        L = self.intake_line
        for side in (-1, 1):
            off = L.offset_curve(side * 1.75)
            if off.is_empty: continue
            c = densify(np.asarray(off.coords), 2.0)
            z = np.array([float(self.zw('intake', 0, p[0])) for p in c])
            top = z + 0.75
            for zz, mat in ((top, 'curb'),):
                Q = np.stack([np.c_[c[:-1], z[:-1] - 0.9], np.c_[c[1:], z[1:] - 0.9], np.c_[c[1:], top[1:]], np.c_[c[:-1], top[:-1]]], 1)
                M.quads(B, Q, 'curb', tag='main')
                M.quads(B, Q[:, [1, 0, 3, 2]], 'curb', tag='main')
                M.bars(B, np.c_[c[:-1], top[:-1] + 0.05], np.c_[c[1:], top[1:] + 0.05], (0, 0, 1), 0.3, 0.1, 'curb', tag='detail', caps=True)
        # end walls (the gate at the west end, the culvert under the bridge abutment at the east end)
        c = np.asarray(L.coords)
        for e, f in ((c[0], c[1]), (c[-1], c[-2])):
            d = (e - f) / np.linalg.norm(e - f); n = np.array([-d[1], d[0]])
            z = float(self.zw('intake', 0, e[0]))
            Qe = np.array([[np.r_[e - n * 1.8, z - 0.9], np.r_[e + n * 1.8, z - 0.9], np.r_[e + n * 1.8, z + 0.8], np.r_[e - n * 1.8, z + 0.8]]])
            M.quads(B, Qe, 'curb'); M.quads(B, Qe[:, [1, 0, 3, 2]], 'curb')
