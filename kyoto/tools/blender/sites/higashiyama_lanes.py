"""東山 lanes: centrelines from OSM, the open corridor between the house fronts (PLATEAU footprints), stone paving
(paint), stone step flights designed on the DEM (risers ~15-17 cm, treads that sit on the slope), cut-stone gutters
along the fronts, walk surfaces on the steps.  lane_z(x, y) gives the walking height (the DEM, or the treads)."""
import math
import numpy as np
import shapely
import shapely.ops
from shapely.geometry import Polygon, LineString, Point, MultiPolygon, box as sbox
from shapely.strtree import STRtree
import mapbox_earcut as earcut

# key, ways (in order along the lane), paving, nominal width (m), house-row distance, flights:
#   flights = list of (station range given by an OSM steps way id or 'auto'), riser, tread slope
LANES = [
    dict(key='yasaka', name='八坂通', ways=[24516359], surf='stone_sett', w=5.0, clip_x0=1693.0),
    dict(key='yasaka_up', name='八坂通 (塔より上)', ways=[710696944], surf='stone_slab', w=5.0),
    dict(key='ninen', name='二年坂', ways=[1491152444, 30913263, 30882783, 550360170], surf='stone_slab', w=5.0, steps=[30882783]),
    dict(key='sannen', name='産寧坂', ways=[526198271, 179116810, 1251544286], surf='stone_slab', w=5.0, steps=[179116810], auto=True, group=7),
    dict(key='kiyomizu', name='清水坂', ways=[28514434], surf='stone_slab', w=6.0, clip_x1=2192.0),
    dict(key='ichinen', name='一念坂', ways=[157527438], surf='stone_slab', w=4.0),
    dict(key='nene', name='ねねの道', ways=[30882780], surf='stone_slab', w=8.0, clip_y1=1748.0),
    dict(key='ishin', name='維新の道', ways=[522894750], surf='stone_slab', w=5.0, clip_x1=2060.0),
    dict(key='ishibe', name='石塀小路', ways=[526198278, (179958185, 0, 4), 179958183], surf='stone_sett', w=2.8, auto=True),
    dict(key='ishibe_n', name='石塀小路 (北)', ways=[371739402], surf='stone_sett', w=2.6, auto=True),
    dict(key='ishibe_w', name='石塀小路 (西)', ways=[371739400], surf='stone_sett', w=2.6, clip_x0=1812.0),
    dict(key='daidokoro', name='台所坂', ways=[527257260], surf='stone_slab', w=3.2, steps=[527257260], houses=False),
    dict(key='chawan', name='茶わん坂', ways=[191042141], surf='stone_slab', w=4.5, clip_x0=2088.0),
    dict(key='gojo', name='五条坂', ways=[409367262], surf='stone_slab', w=6.0, clip_len=120.0),
]

def way(S, wid):
    for w in S.osm['ways']:
        if w['id'] == wid: return w
    raise KeyError(wid)

def chain(S, ids):
    """merge the ways' polylines into one LineString in the order given (each reversed as needed)"""
    pts = []
    for wid in ids:
        sl = None
        if isinstance(wid, tuple): wid, i0, i1 = wid; sl = (i0, i1)
        for l in way(S, wid)['line']:
            c = [tuple(p) for p in l]
            if sl: c = c[sl[0]:sl[1]]
            if not pts: pts = c; continue
            e = np.array(pts[-1]); s0 = np.array(pts[0])
            a = np.array(c[0]); b = np.array(c[-1])
            d = [np.linalg.norm(e - a), np.linalg.norm(e - b), np.linalg.norm(s0 - b), np.linalg.norm(s0 - a)]
            k = int(np.argmin(d))
            if k == 0: pts += c[1:]
            elif k == 1: pts += c[::-1][1:]
            elif k == 2: pts = c[:-1] + pts
            else: pts = c[::-1][:-1] + pts
    L = LineString(pts)
    return L

def clip_line(L, lane):
    """clip a centreline by x / y limits or length"""
    if 'clip_len' in lane:
        L = shapely.ops.substring(L, 0, min(L.length, lane['clip_len']))
    box_ = [-1e9, -1e9, 1e9, 1e9]
    if 'clip_x0' in lane: box_[0] = lane['clip_x0']
    if 'clip_x1' in lane: box_[2] = lane['clip_x1']
    if 'clip_y1' in lane: box_[3] = lane['clip_y1']
    g = L.intersection(sbox(*box_))
    if g.geom_type == 'MultiLineString': g = max(g.geoms, key=lambda q: q.length)
    return g

class Lane:
    def __init__(self, S, spec, fps, tree):
        self.spec = spec; self.key = spec['key']; self.surf = spec['surf']
        self.line = clip_line(chain(S, spec['ways']), spec)
        self.S = S
        self.offsets(fps, tree)
        self.flights = []

    def frame(self, s):
        L = self.line
        s = min(max(s, 0.0), L.length)
        p = L.interpolate(s); q = L.interpolate(min(L.length, s + 0.8)); r = L.interpolate(max(0.0, s - 0.8))
        d = np.array([q.x - r.x, q.y - r.y]); d /= max(np.linalg.norm(d), 1e-9)
        return np.array([p.x, p.y]), d, np.array([-d[1], d[0]])

    def offsets(self, fps, tree, step=1.0):
        """left / right distance from the centreline to the first footprint (the house fronts), per station"""
        L = self.line; w = self.spec['w']
        maxw = max(4.0, w * 0.5 + 3.5)
        n = max(2, int(L.length / step) + 1)
        self.st = np.linspace(0, L.length, n)
        left = np.full(n, w / 2 + 0.6); right = np.full(n, w / 2 + 0.6)
        self.hitL = np.zeros(n, bool); self.hitR = np.zeros(n, bool)
        for i, s in enumerate(self.st):
            p, d, nrm = self.frame(s)
            for side, arr, hit in ((1, left, self.hitL), (-1, right, self.hitR)):
                ray = LineString([p + nrm * side * 0.3, p + nrm * side * maxw])
                best = None
                for k in tree.query(ray):
                    g = ray.intersection(fps[k])
                    if g.is_empty: continue
                    dd = Point(p).distance(g)
                    best = dd if best is None else min(best, dd)
                if best is not None: arr[i] = max(1.0, best); hit[i] = True
        # smooth (median of 5) and cap
        def med(a):
            out = a.copy()
            for i in range(len(a)):
                out[i] = np.median(a[max(0, i - 2):i + 3])
            return out
        self.left = np.minimum(med(left), maxw); self.right = np.minimum(med(right), maxw)

    def corridor(self, extra=0.0, s0=None, s1=None):
        """the open lane between the fronts (+ extra on each side) between stations s0..s1"""
        s0 = 0.0 if s0 is None else s0; s1 = self.line.length if s1 is None else s1
        m = (self.st >= s0) & (self.st <= s1)
        ss = np.r_[s0, self.st[m], s1]
        lft = np.interp(ss, self.st, self.left) + extra; rgt = np.interp(ss, self.st, self.right) + extra
        A = []; Bp = []
        for s, a, b in zip(ss, lft, rgt):
            p, d, nrm = self.frame(s)
            A.append(p + nrm * a); Bp.append(p - nrm * b)
        P = Polygon(A + Bp[::-1])
        if not P.is_valid: P = P.buffer(0)
        if P.geom_type == 'MultiPolygon': P = max(P.geoms, key=lambda q: q.area)
        return P

    def width_at(self, s):
        return float(np.interp(s, self.st, self.left) + np.interp(s, self.st, self.right))

    def profile(self, S, step=0.5):
        """max DEM across the corridor per station (what steps must stay above)"""
        n = max(2, int(self.line.length / step) + 1)
        ss = np.linspace(0, self.line.length, n)
        z = np.zeros(n)
        for i, s in enumerate(ss):
            p, d, nrm = self.frame(s)
            a = float(np.interp(s, self.st, self.left)); b = float(np.interp(s, self.st, self.right))
            ts = np.linspace(-b + 0.3, a - 0.3, 5)
            X = p[0] + nrm[0] * ts; Y = p[1] + nrm[1] * ts
            z[i] = float(np.max(S.ground(X, Y)))
        return ss, z

def unit(v): v = np.asarray(v, float); return v / max(np.linalg.norm(v), 1e-12)

# ------------------------------------------------------------------ step flights
class Flight:
    """treads [(a, b, h, g)] along a lane: from station a to b, top at h at a rising with slope g (toward b); dirn +1 if
    the flight rises with the station, -1 if it rises against it (then a > b)"""
    def __init__(self, lane, treads, polys):
        self.lane = lane; self.treads = treads; self.polys = polys

def design(ss, zp, sa, sb, riser=0.155, gt=0.02, nsteps=None, group=None, tread=0.62):
    """treads for the station range sa..sb (either order: the flight rises from the lower end).  Staircase above the
    slope: each tread runs until the ground reaches it, then a riser.  With nsteps the tread slope is fitted so the
    count matches (OSM step_count).  Returns [(s_start, s_end, z_start, slope)] in rising order (s may decrease)."""
    za = float(np.interp(sa, ss, zp)); zb = float(np.interp(sb, ss, zp))
    if za > zb: sa, sb, za, zb = sb, sa, zb, za
    sgn = 1.0 if sb > sa else -1.0
    Lr = abs(sb - sa); rise = zb - za
    if rise < 0.25 or Lr < 1.0: return []
    if nsteps:
        r = min(0.18, max(0.12, rise / nsteps))
        gt = max(0.0, (rise - nsteps * r) / Lr)
        riser = r
    def ground(t):                      # t: distance from the low end
        return float(np.interp(sa + sgn * t, ss, zp))
    # monotone envelope of the ground (a tread must stay above every later bump)
    ts = np.linspace(0, Lr, max(3, int(Lr / 0.1)))
    gz = np.maximum.accumulate(np.array([ground(t) for t in ts]))
    out = []
    t = 0.0; z = za; j = 0
    while t < Lr - 0.05 and z < zb - 0.02:
        h = min(z + riser, zb + 0.0)
        # the tread runs until the envelope rises above h + gt*(t' - t)
        k0 = np.searchsorted(ts, t)
        tt = ts[k0:]; gg = gz[k0:]
        over = np.nonzero(gg > h + gt * (tt - t) + 1e-3)[0]
        t1 = float(tt[over[0]]) if len(over) else Lr
        if group and (j % group) != group - 1:
            t1 = min(t1, t + tread)                    # within a flight: regular treads (rising above the slope)
        t1 = max(t1, t + 0.32)                         # a tread at least 32 cm
        j += 1
        if t1 > Lr - 0.25: t1 = Lr
        out.append((sa + sgn * t, sa + sgn * t1, h, gt))
        z = h + gt * (t1 - t); t = t1
    # close the top: the last tread meets the ground at sb (adjust its slope)
    if out:
        a, b, h, g = out[-1]
        L_ = abs(b - a)
        if L_ > 0.3: out[-1] = (a, b, h, (zb - h) / L_ if zb > h else 0.0)
    return out

def tread_poly(lane, corr, a, b, wide=12.0):
    """the corridor between the perpendiculars at stations a and b"""
    pa, da, na = lane.frame(a); pb, db, nb = lane.frame(b)
    q = Polygon([pa - na * wide, pa + na * wide, pb + nb * wide, pb - nb * wide])
    if not q.is_valid: q = q.buffer(0)
    g = corr.intersection(q)
    if g.is_empty: return None
    if g.geom_type != 'Polygon':
        gs = [x for x in getattr(g, 'geoms', []) if x.geom_type == 'Polygon']
        if not gs: return None
        g = max(gs, key=lambda x: x.area)
    return g if g.area > 0.05 else None

def build_flight(B, S, lane, treads, mat='stone', riser_mat='stone', cheeks=False):
    """stone treads (top faces following the tread slope), risers, side skirts down to the DEM; walk = the treads.
    The corridor offsets are to the roof outlines (PLATEAU): the treads run 1.1 m further, under the eaves to the plinths"""
    corr = lane.corridor(extra=1.1)
    L = lane.line
    polys = []
    prev_end = None
    for i, (a, b, h, g) in enumerate(treads):
        poly = tread_poly(lane, corr, a, b)
        if poly is None: prev_end = h + g * abs(b - a); continue
        poly = poly.simplify(0.02)
        rings = [np.asarray(poly.exterior.coords)[:-1]]
        V = rings[0]
        I = earcut.triangulate_float64(V, np.array([len(V)], np.uint32)).reshape(-1, 3)
        sv = shapely.line_locate_point(L, shapely.points(V[:, 0], V[:, 1]))
        Z = h + g * np.clip(np.abs(sv - a), 0, abs(b - a))
        P = np.c_[V, Z]
        fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
        if fn[:, 2].sum() < 0: I = I[:, ::-1]
        B.add(P, I, mat, UV=V.copy(), tag='main')
        B.add(P + [0, 0, 0.0], I, 'stone', tag='walk')
        # the nosing: a strip of lighter cut stone along the tread's front edge
        pa_, da_, na_ = lane.frame(a)
        fwd = da_ if b > a else -da_
        ln_ = LineString([pa_ - na_ * 12, pa_ + na_ * 12]).intersection(corr)
        for sg in ([ln_] if ln_.geom_type == 'LineString' else [x for x in getattr(ln_, 'geoms', []) if x.geom_type == 'LineString']):
            if sg.length < 0.3: continue
            (x0, y0), (x1, y1) = sg.coords[0], sg.coords[-1]
            q0 = np.array([x0, y0]); q1 = np.array([x1, y1])
            Qn = np.array([(*q0, h + 0.008), (*q1, h + 0.008), (*(q1 + fwd * 0.09), h + 0.008 + g * 0.09), (*(q0 + fwd * 0.09), h + 0.008 + g * 0.09)])
            fnn = np.cross(Qn[1] - Qn[0], Qn[2] - Qn[0])
            B.add(Qn, [[0, 1, 2], [0, 2, 3]] if fnn[2] > 0 else [[0, 2, 1], [0, 3, 2]], 'curb', tag='detail')
        polys.append((poly, a, b, h, g))
        # riser at a: from the previous tread's end (or the ground) up to h
        pa, da, na = lane.frame(a)
        cut = LineString([pa - na * 12, pa + na * 12]).intersection(corr)
        segs = [cut] if cut.geom_type == 'LineString' else [x for x in getattr(cut, 'geoms', []) if x.geom_type == 'LineString']
        z_lo = prev_end if prev_end is not None else float(np.interp(a, *lane.prof)) - 0.05
        z_lo = min(z_lo, h - 0.05)
        up = unit(np.r_[(da if b > a else -da), 0.0])          # the riser faces down the flight
        for sg in segs:
            if sg.length < 0.1: continue
            (x0, y0), (x1, y1) = sg.coords[0], sg.coords[-1]
            Q = np.array([(x0, y0, z_lo - 0.03), (x1, y1, z_lo - 0.03), (x1, y1, h), (x0, y0, h)])
            fnq = np.cross(Q[1] - Q[0], Q[2] - Q[0])
            I2 = [[0, 1, 2], [0, 2, 3]] if fnq @ (-up) >= 0 else [[0, 2, 1], [0, 3, 2]]
            ln = math.hypot(x1 - x0, y1 - y0)
            B.add(Q, I2, riser_mat, UV=np.array([(0, z_lo), (ln, z_lo), (ln, h), (0, h)]), tag='main')
        prev_end = h + g * abs(b - a)
        # side skirts along the corridor edges (hidden under the house plinths, visible where the side is open)
        ext = np.asarray(poly.exterior.coords)
        Q = []
        for j in range(len(ext) - 1):
            p0, p1 = ext[j], ext[j + 1]
            m = (p0 + p1) / 2
            sm = L.project(Point(m))
            if abs(sm - a) < 0.05 or abs(sm - b) < 0.05: continue
            if np.linalg.norm(p1 - p0) < 0.05: continue
            z0 = h + g * min(abs(L.project(Point(p0)) - a), abs(b - a)); z1 = h + g * min(abs(L.project(Point(p1)) - a), abs(b - a))
            gb = min(float(S.ground(*p0)), float(S.ground(*p1))) - 0.15
            if min(z0, z1) - gb < 0.06: continue
            Q.append([(p0[0], p0[1], gb), (p1[0], p1[1], gb), (p1[0], p1[1], z1), (p0[0], p0[1], z0)])
        if Q:
            # orientation: outward from the tread polygon (exterior ring orientation decides)
            ccw = poly.exterior.is_ccw
            Qa = np.array(Q, float)
            if not ccw: Qa = Qa[:, [1, 0, 3, 2]]
            Iq = (np.arange(len(Qa))[:, None, None] * 4 + np.array([[0, 1, 2], [0, 2, 3]])[None]).reshape(-1, 3)
            B.add(Qa.reshape(-1, 3), Iq, 'stone', tag='main')
    return polys

# ------------------------------------------------------------------ the lane height function
class LaneZ:
    """walking height: the DEM, raised to the stone treads where a flight is built"""
    def __init__(self, S):
        self.S = S; self.items = []; self.tree = None
    def add(self, lane, polys):
        for (poly, a, b, h, g) in polys: self.items.append((poly, lane, a, b, h, g))
    def done(self):
        self.tree = STRtree([it[0] for it in self.items]) if self.items else None
    def __call__(self, x, y):
        z = float(self.S.ground(x, y))
        if self.tree is None: return z
        pt = Point(x, y)
        for k in self.tree.query(pt.buffer(0.3)):
            poly, lane, a, b, h, g = self.items[k]
            if poly.buffer(0.3).contains(pt):
                s = lane.line.project(pt)
                z = max(z, h + g * min(abs(s - a), abs(b - a)))
        return z

# ------------------------------------------------------------------ gutters (cut-stone kerb + channel) along the fronts
def gutters(B, S, lane, lz, skip=()):
    """a channel of cut granite along both corridor edges: kerb strip (curb) + dark channel; follows the lane height"""
    L = lane.line
    n = len(lane.st)
    for side, off, hit in ((1, lane.left, lane.hitL), (-1, lane.right, lane.hitR)):
        P = []; Q = []
        for i in range(0, n, 1):
            s = lane.st[i]
            if any(a - 0.5 <= s <= b + 0.5 for (a, b) in skip) or not hit[max(0, i - 1):i + 2].all(): P.append(None); continue
            p, d, nrm = lane.frame(s)
            o = off[i]
            q0 = p + nrm * side * (o - 0.12); q1 = p + nrm * side * (o + 0.04); q2 = p + nrm * side * (o + 0.34)
            P.append((q0, q1, q2))
        runs = []; cur = []
        for k, it in enumerate(P):
            if it is None:
                if len(cur) > 1: runs.append(cur)
                cur = []
            else: cur.append(it)
        if len(cur) > 1: runs.append(cur)
        for run in runs:
            V = []; Vc = []
            for (q0, q1, q2) in run:
                z0 = lz(*q0) + 0.012; z1 = lz(*q1) + 0.012; z2 = lz(*q2) + 0.012
                V.append([(q0[0], q0[1], z0), (q1[0], q1[1], z1 - 0.0)])
                Vc.append([(q1[0], q1[1], z1 - 0.025), (q2[0], q2[1], z2 - 0.025)])
            for arr, mat in ((V, 'curb'), (Vc, 'stone')):
                A = np.array(arr, float)          # (k, 2, 3)
                k = len(A)
                Pv = A.reshape(-1, 3)
                I = []
                for j in range(k - 1):
                    a0 = 2 * j; I += [[a0, a0 + 2, a0 + 3], [a0, a0 + 3, a0 + 1]]
                I = np.array(I)
                fn = np.cross(Pv[I[:, 1]] - Pv[I[:, 0]], Pv[I[:, 2]] - Pv[I[:, 0]])
                if fn[:, 2].sum() < 0: I = I[:, ::-1]
                B.add(Pv, I, mat, UV=Pv[:, :2].copy(), tag='detail')

def ring_of(g):
    if g.geom_type != 'Polygon': g = max(g.geoms, key=lambda p: p.area)
    return [list(map(float, c)) for c in list(g.exterior.coords)[:-1]]

# ------------------------------------------------------------------ all lanes
def make(S, protect):
    """build the Lane objects (corridor offsets against the PLATEAU footprints)"""
    fps = []
    for b in S.plateau:
        P = Polygon(b['poly'][0][0])
        if not P.is_valid: P = P.buffer(0)
        if P.geom_type != 'Polygon' or P.area < 4: continue
        fps.append(P)
    # hero plots count as fronts too (walls)
    tree = STRtree(fps)
    lanes = {}
    for spec in LANES:
        try:
            lanes[spec['key']] = Lane(S, spec, fps, tree)
        except KeyError as e:
            print('lane missing way', spec['key'], e)
    return lanes

def build(B, S, lanes, lz, stats, protect=None):
    """flights, walk, paint, gutters (all kept out of the neighbouring hero sites: `protect`)"""
    for key, lane in lanes.items():
        lane.prof = lane.profile(S)
        spec = lane.spec
        flights = []
        for wid in [w if not isinstance(w, tuple) else w[0] for w in spec.get('steps', [])]:
            w = way(S, wid)
            Lw = LineString(w['line'][0])
            sa = lane.line.project(Point(Lw.coords[0])); sb = lane.line.project(Point(Lw.coords[-1]))
            n = int(w['tags'].get('step_count', 0) or 0) or None
            flights.append((min(sa, sb), max(sa, sb), n))
        if spec.get('auto'):
            ss, zp = lane.prof
            gr = np.abs(np.gradient(zp, ss))
            k = 7
            grs = np.convolve(gr, np.ones(k) / k, mode='same')
            steep = grs > 0.13
            i = 0
            while i < len(ss):
                if steep[i]:
                    j = i
                    while j < len(ss) and steep[j]: j += 1
                    a, b = ss[max(0, i - 2)], ss[min(len(ss) - 1, j + 1)]
                    if b - a > 2.5 and not any(a < fb and b > fa for (fa, fb, _) in flights):
                        flights.append((a, b, None))
                    i = j
                else: i += 1
        lane.flights = []
        for (a, b, n) in sorted(flights):
            grp = spec.get('group')
            tr = design(lane.prof[0], lane.prof[1], a, b, riser=0.155 if key != 'daidokoro' else 0.16, gt=0.02, nsteps=None if grp else n, group=grp)
            if not tr: continue
            polys = build_flight(B, S, lane, tr)
            lz.add(lane, polys)
            # the generic terrain is removed well inside the flight (the 2 m terrain mesh could poke through the treads);
            # the treads reach 1.1 m beyond the corridor and the cut stays 1.5 m inside them
            from shapely.ops import unary_union
            fl = unary_union([pp[0] for pp in polys]).buffer(-1.5)
            for gg in (fl.geoms if hasattr(fl, 'geoms') else [fl]):
                if gg.geom_type == 'Polygon' and gg.area > 1.0:
                    S.cut.append(ring_of(gg.simplify(0.2)))
            lane.flights.append((a, b, tr))
            print('flight', key, round(a, 1), round(b, 1), 'n', len(tr), 'rise', round(max(t[2] for t in tr) - min(t[2] for t in tr) + 0.155, 2), 'osm', n)
            stats['steps'] = stats.get('steps', 0) + len(tr)
    lz.done()
    for key, lane in lanes.items():
        # paving
        corr = lane.corridor(extra=0.9)
        if protect is not None: corr = corr.difference(protect.buffer(0.5))
        for g in (corr.geoms if hasattr(corr, 'geoms') else [corr]):
            if g.geom_type == 'Polygon' and g.area > 2.0:
                S.paint.append({'poly': ring_of(g), 'surf': lane.surf})
        if lane.spec.get('houses', True):
            sk = [(min(a, b), max(a, b)) for (a, b, tr) in lane.flights]
            if protect is not None:
                for s_ in lane.st:
                    p, d, nrm = lane.frame(s_)
                    if protect.buffer(4.0).contains(Point(p)): sk.append((s_ - 0.6, s_ + 0.6))
            gutters(B, S, lane, lz, skip=sk)
