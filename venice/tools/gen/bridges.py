"""Venetian footbridges from OSM: stepped brick arches with Istrian-stone nosings, archivolts and parapet caps.

Each bridge: straight chord between the ends of a merged OSM bridge line; the canal span is where the line
crosses water.  Profile: steps (rise ~0.15 m, tread ~0.42 m) up to a short landing over a segmental arch
(springing 0.5 m above the water, crown soffit 2.2-3.0 m)."""
import math
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import linemerge, unary_union
from shapely.strtree import STRtree
from .world import GROUND_Z, h32
from .mesh import MeshBuilder, triangulate
from .materials import MAT

TREAD = 0.42
RISE = 0.15
TREAD_MIN = 0.27      # steepest steps, where a bank leaves little room (a wall or a narrow fondamenta beyond it)
RISE_MAX = 0.19
ARCH_MAX = 40.0       # wider crossings get a timber footbridge on piles instead of a brick arch
LONG_MAX = 120.0

def find_bridges(world):
    o = world.o
    lines = []
    named = []           # lines of footways called "Ponte ...": the only ones allowed a long timber crossing
    for wid, way in o.ways.items():
        t = way.get('tags', {})
        if t.get('bridge') in ('yes', 'arch', 'covered') and t.get('highway') and t.get('highway') not in ('motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'service', 'residential'):
            P = o.way_xy(wid)
            if len(P) >= 2:
                lines.append(LineString(P))
                if t.get('highway') in ('footway', 'pedestrian', 'steps', 'path') and str(t.get('name', '')).startswith('Ponte'): named.append(LineString(P))
    named_u = unary_union(named) if named else None
    def is_named(g): return named_u is not None and g.buffer(0.5).intersection(named_u).length > 0.5 * min(g.length, 30.0)
    merged = linemerge(unary_union(lines))
    groups = list(merged.geoms) if hasattr(merged, 'geoms') else [merged]
    mm = []
    for wid, way in o.ways.items():
        if way.get('tags', {}).get('man_made') == 'bridge' and way['nodes'][0] == way['nodes'][-1] and len(way['nodes']) > 3:
            p = Polygon(o.way_xy(wid)).buffer(0)
            if p.area > 1: mm.append(p)
    mtree = STRtree(mm) if mm else None
    out = []
    def width_at(mid):
        if mtree is not None:
            for i in mtree.query(mid.buffer(1.0)):
                p = mm[i]
                if p.distance(mid) < 1.0:
                    r = p.minimum_rotated_rectangle; c = list(r.exterior.coords)
                    e = sorted(math.dist(c[k], c[k + 1]) for k in range(4))
                    return float(np.clip(p.area / max(e[-1], 1.0), 1.8, 5.5))
        return 2.6
    def dirn(p):
        q = np.array(p.coords[-1]) - np.array(p.coords[0]); return q / max(float(np.linalg.norm(q)), 1e-9)
    for g in groups:
        if g.length < 2: continue
        wat = g.difference(world.land)
        if wat.is_empty: continue
        pieces = [p for p in (wat.geoms if hasattr(wat, 'geoms') else [wat]) if p.length >= 1.0]
        a = np.array(g.coords[0]); b = np.array(g.coords[-1])
        L = float(np.linalg.norm(b - a))
        if L < 2: continue
        d = (b - a) / L
        if len(pieces) == 1 and abs(float(np.dot(dirn(pieces[0]), d))) > 0.995:
            # a straight line crossing once: the chord between its ends (unchanged geometry for these)
            if wat.length < 1.2 or wat.length > LONG_MAX: continue
            pts = []
            for seg in (wat.geoms if hasattr(wat, 'geoms') else [wat]):
                for c in seg.coords: pts.append(float(np.dot(np.array(c) - a, d)))
            sa, sb = max(0.0, min(pts)), min(L, max(pts))
            if sb - sa < 1.0: continue
            mid = Point(*(a + d * (sa + sb) / 2))
            if (sb - sa) > ARCH_MAX and not is_named(g): continue
            out.append(dict(a=a, b=b, d=d, L=L, sa=sa, sb=sb, w=width_at(mid), seed=h32('br', round(a[0], 1), round(a[1], 1)), long=(sb - sa) > ARCH_MAX))
        else:
            # bent or merged lines (two bridges meeting at an angle, a bridge continuing a fondamenta): the chord of
            # the whole line cut diagonally across the canal; one bridge per water crossing, along that crossing
            for p in pieces:
                p0 = np.array(p.coords[0]); p1 = np.array(p.coords[-1]); wc = float(np.linalg.norm(p1 - p0))
                if wc < 1.2 or wc > LONG_MAX or p.length > 1.25 * wc + 1.0: continue
                dd = (p1 - p0) / wc
                mid = Point(*((p0 + p1) / 2))
                if wc > ARCH_MAX and not is_named(p): continue
                out.append(dict(a=p0, b=p1, d=dd, L=wc, sa=0.0, sb=wc, w=width_at(mid), seed=h32('br', round(p0[0], 1), round(p0[1], 1)), long=wc > ARCH_MAX))
    _free_ends(world, out)
    return out

def _free_ends(world, brs, maxd=6.0, step=0.1):
    """br['free'] = open ground beyond each bank along the axis, up to the first building (unless a calle passes
    through it) or water: the steps stop short of it instead of running into a wall."""
    from .walk import Passages
    bl = [b.poly for b in world.buildings if b.z0 < GROUND_Z + 2.0]; bt = STRtree(bl)
    pas = Passages(world)                                  # the same calli through buildings the walk raster opens
    land = world.land
    shapely.prepare(land)
    def open_at(p):
        q = Point(float(p[0]), float(p[1]))
        if not land.contains(q): return False
        for i in bt.query(q):
            if bl[i].contains(q): return any(g.contains(q) for g in pas.within(q))
        return True
    for br in brs:
        fr = []
        gp = []
        for sv, sg in ((br['sa'], -1.0), (br['sb'], 1.0)):
            p0 = br['a'] + br['d'] * sv; f = maxd; on = False; g = 0.0
            for k in range(1, int(maxd / step) + 1):
                o = open_at(p0 + br['d'] * (sg * k * step))
                if not on:                                 # an OSM bridge line can stop short of the mapped bank
                    if o: on = True; g = (k - 1) * step
                    elif k * step >= 3.0: f = 0.0; break
                    continue
                if not o: f = (k - 1) * step; break
            fr.append(f); gp.append(g if on else 0.0)
        br['free'] = tuple(fr); br['gap'] = tuple(gp)

def _fit_steps(span_half, E0, F, nst, rise, ztop, landing, landing_min=0.6, gap=0.0):
    """one side's flight: (steps, rise, tread, landing half length) so that it ends E <= F - 0.25 beyond the bank,
    and at least 0.4 m onto land when the OSM line stopped `gap` short of it.  span_half: centre to bank.  Short of
    room: steeper treads first, then a shorter landing, then higher risers; with room to spare the landing grows."""
    lo = gap + 0.4 if gap > 0 else 0.0
    E = min(max(E0, lo), max(F - 0.25, min(F, 0.35), lo))
    avail = span_half + E
    n, r, l = nst, rise, landing
    t = (avail - l) / n
    if t < TREAD_MIN:
        l = max(landing_min, avail - n * TREAD_MIN); t = (avail - l) / n
    if t < TREAD_MIN:
        n = max(2, int(math.ceil((ztop - GROUND_Z) / RISE_MAX))); r = (ztop - GROUND_Z) / n
        t = max(TREAD_MIN, (avail - l) / n)
    if t > TREAD: t = TREAD; l = avail - n * TREAD
    return n, r, t, l

def gen_long_bridge(mb, br):
    """a long timber footbridge (Ponte San Pietro, Quintavalle, Ponte Longo...): stone steps up from both banks,
    a flat plank deck over the water on pairs of piles with cap beams, posts and rails along both sides."""
    a, d, sa, sb, W = br['a'], br['d'], br['sa'], br['sb'], max(2.4, min(br['w'], 4.0))
    n_ = np.array([-d[1], d[0]]); rnd = br['seed']
    ztop = GROUND_Z + 1.65
    nst = max(2, int(round((ztop - GROUND_Z) / RISE))); rise = (ztop - GROUND_Z) / nst
    fr = br.get('free', (9.0, 9.0)); gp = br.get('gap', (0.0, 0.0))
    # the deck reaches 0.6 m onto each bank (further where OSM stops short of it); flights from its ends inland, as far
    # as the open ground allows
    fl = {sd: _fit_steps(0.0, 0.6 + nst * TREAD, f, nst, rise, ztop, 0.6, 0.6, gap=g) for sd, f, g in ((-1, fr[0], gp[0]), (1, fr[1], gp[1]))}
    s_l0, s_l1 = sa - fl[-1][3], sb + fl[1][3]
    s_lo, s_hi = s_l0 - fl[-1][0] * fl[-1][2], s_l1 + fl[1][0] * fl[1][2]
    hw = W / 2; ti = hw - 0.14
    P = lambda s, t, z: (a[0] + d[0] * s + n_[0] * t, a[1] + d[1] * s + n_[1] * t, z)
    wood = MAT['wood_raw']; stone = MAT['bridge_stone']; tread_m = MAT['ground']
    c1 = (0, 0, int(rnd * 255), 0)
    def quad(p0, p1, p2, p3, uv, mat, nrm):
        e1 = np.subtract(p1, p0); e2 = np.subtract(p2, p0)
        idx = [[0, 1, 2], [0, 2, 3]] if np.dot(np.cross(e1, e2), nrm) >= 0 else [[0, 2, 1], [0, 3, 2]]
        mb.add_planar([p0, p1, p2, p3], idx, nrm, uv, mat=mat, c1=c1)
    def box(s0, s1, t0, t1, z0, z1, mat):
        up = (0, 0, 1.0); fw = (d[0], d[1], 0.0); lf = (n_[0], n_[1], 0.0)
        quad(P(s0, t0, z1), P(s1, t0, z1), P(s1, t1, z1), P(s0, t1, z1), [(s0, t0), (s1, t0), (s1, t1), (s0, t1)], mat, up)
        quad(P(s0, t0, z0), P(s1, t0, z0), P(s1, t1, z0), P(s0, t1, z0), [(s0, t0), (s1, t0), (s1, t1), (s0, t1)], mat, (0, 0, -1.0))
        quad(P(s0, t1, z0), P(s1, t1, z0), P(s1, t1, z1), P(s0, t1, z1), [(s0, z0), (s1, z0), (s1, z1), (s0, z1)], mat, lf)
        quad(P(s0, t0, z0), P(s1, t0, z0), P(s1, t0, z1), P(s0, t0, z1), [(s0, z0), (s1, z0), (s1, z1), (s0, z1)], mat, (-lf[0], -lf[1], 0.0))
        quad(P(s1, t0, z0), P(s1, t1, z0), P(s1, t1, z1), P(s1, t0, z1), [(t0, z0), (t1, z0), (t1, z1), (t0, z1)], mat, fw)
        quad(P(s0, t0, z0), P(s0, t1, z0), P(s0, t1, z1), P(s0, t0, z1), [(t0, z0), (t1, z0), (t1, z1), (t0, z1)], mat, (-fw[0], -fw[1], 0.0))
    # steps on both banks (stone risers, trachyte treads), the full width
    for side in (-1, 1):
        n_s, r_s, t_s, _ = fl[side]
        for k in range(n_s):
            s_r = (s_lo + k * t_s) if side < 0 else (s_hi - k * t_s)
            s_t = s_r + t_s * (1 if side < 0 else -1)
            lo, hi = min(s_r, s_t), max(s_r, s_t)
            box(lo, hi, -hw, hw, GROUND_Z - 0.05, GROUND_Z + r_s * (k + 1), stone if k == n_s - 1 else tread_m)
    # the deck: planks on two side beams
    box(s_l0, s_l1, -hw, hw, ztop - 0.12, ztop, wood)
    for side in (-1, 1):
        box(s_l0, s_l1, side * hw - (0.18 if side > 0 else 0), side * hw + (0.18 if side < 0 else 0), ztop - 0.5, ztop - 0.12, wood)
    # piles in pairs with a cap beam every ~6 m over the water
    npile = max(1, int(round((sb - sa) / 6.0)))
    for k in range(1, npile):
        s = sa + (sb - sa) * k / npile
        for side in (-1, 1):
            t = side * (hw - 0.25)
            box(s - 0.13, s + 0.13, t - 0.13, t + 0.13, -0.6, ztop - 0.5, wood)
        box(s - 0.15, s + 0.15, -hw, hw, ztop - 0.75, ztop - 0.5, wood)
    # railings: posts every ~1.6 m, a top rail and a mid rail, along the deck and the steps
    def zwalk(s):
        if s <= s_lo or s >= s_hi: return GROUND_Z
        if s_l0 <= s <= s_l1: return ztop
        if s < s_l0: return GROUND_Z + (s - s_lo) / (s_l0 - s_lo) * (ztop - GROUND_Z)
        return GROUND_Z + (s_hi - s) / (s_hi - s_l1) * (ztop - GROUND_Z)
    for side in (-1, 1):
        t = side * (hw - 0.06)
        npost = max(2, int((s_hi - s_lo) / 1.6))
        ss = [s_lo + (s_hi - s_lo) * k / npost for k in range(npost + 1)]
        for s in ss: box(s - 0.05, s + 0.05, t - 0.05, t + 0.05, zwalk(s), zwalk(s) + 1.05, wood)
        for i in range(npost):
            s0, s1 = ss[i], ss[i + 1]
            for (h, th) in ((1.05, 0.07), (0.55, 0.04)):
                za, zb = zwalk(s0) + h, zwalk(s1) + h
                q = [P(s0, t - 0.06, za), P(s1, t - 0.06, zb), P(s1, t + 0.06, zb), P(s0, t + 0.06, za)]
                quad(*q, [(s0, 0), (s1, 0), (s1, 0.12), (s0, 0.12)], wood, (0, 0, 1.0))
                q2 = [P(s0, t + side * 0.06, za - th), P(s1, t + side * 0.06, zb - th), P(s1, t + side * 0.06, zb), P(s0, t + side * 0.06, za)]
                quad(*q2, [(s0, 0), (s1, 0), (s1, th), (s0, th)], wood, (n_[0] * side, n_[1] * side, 0.0))
    return dict(lo=P(s_lo, 0, GROUND_Z), hi=P(s_hi, 0, GROUND_Z), ztop=ztop, w=W,
                walk=dict(a=[float(a[0]), float(a[1])], d=[float(d[0]), float(d[1])], ti=float(ti), s=[float(s_lo), float(s_l0), float(s_l1), float(s_hi)], ztop=float(ztop)))

def gen_bridge(mb, br):
    if br.get('long'): return gen_long_bridge(mb, br)
    a, d, L, sa, sb, W = br['a'], br['d'], br['L'], br['sa'], br['sb'], br['w']
    n_ = np.array([-d[1], d[0]])           # left of travel
    rnd = br['seed']
    Wc = sb - sa; sc = (sa + sb) / 2
    zsp = 0.5
    zcr = float(np.clip(0.5 + Wc * 0.24, 2.1, 3.0))
    ztop = zcr + 0.42
    nst = max(2, int(round((ztop - GROUND_Z) / RISE)))
    rise = (ztop - GROUND_Z) / nst
    lh = max(0.7, Wc * 0.16, Wc / 2 + 1.2 - nst * TREAD)     # the steps always start on the banks (wide canals)
    E0 = lh + nst * TREAD - Wc / 2                            # how far they reach inland where there is room
    fr = br.get('free', (9.0, 9.0))
    gp = br.get('gap', (0.0, 0.0))
    fl = {sd: _fit_steps(Wc / 2, E0, f, nst, rise, ztop, lh, gap=g) for sd, f, g in ((-1, fr[0], gp[0]), (1, fr[1], gp[1]))}
    s_l0, s_l1 = sc - fl[-1][3], sc + fl[1][3]
    s_lo, s_hi = s_l0 - fl[-1][0] * fl[-1][2], s_l1 + fl[1][0] * fl[1][2]
    P = lambda s, t, z: (a[0] + d[0] * s + n_[0] * t, a[1] + d[1] * s + n_[1] * t, z)
    hw = W / 2; pw = 0.24                  # parapet thickness
    stone = MAT['bridge_stone']; brick = MAT['bridge_brick']; tread_m = MAT['ground']
    c1 = (0, 0, int(rnd * 255), 0)
    def quad(p0, p1, p2, p3, uv, mat, nrm):
        # winding follows the requested normal
        e1 = np.subtract(p1, p0); e2 = np.subtract(p2, p0)
        idx = [[0, 1, 2], [0, 2, 3]] if np.dot(np.cross(e1, e2), nrm) >= 0 else [[0, 2, 1], [0, 3, 2]]
        mb.add_planar([p0, p1, p2, p3], idx, nrm, uv, mat=mat, c1=c1)
    up = (0, 0, 1.0); fwd = (d[0], d[1], 0.0); bwd = (-d[0], -d[1], 0.0)
    ti = hw - pw
    # ---- steps (both sides) and landing
    for side in (-1, 1):
        n_s, r_s, t_s, _ = fl[side]
        for k in range(n_s):
            # step k: riser at s_r, tread from s_r to s_r + t_s toward the centre
            s_r = (s_lo + k * t_s) if side < 0 else (s_hi - k * t_s)
            s_t = s_r + t_s * (1 if side < 0 else -1)
            z0, z1 = GROUND_Z + r_s * k, GROUND_Z + r_s * (k + 1)
            nr = bwd if side < 0 else fwd
            # riser (stone)
            if side < 0:
                quad(P(s_r, ti, z0), P(s_r, -ti, z0), P(s_r, -ti, z1), P(s_r, ti, z1), [(-ti, z0), (ti, z0), (ti, z1), (-ti, z1)], stone, nr)
            else:
                quad(P(s_r, -ti, z0), P(s_r, ti, z0), P(s_r, ti, z1), P(s_r, -ti, z1), [(-ti, z0), (ti, z0), (ti, z1), (-ti, z1)], stone, nr)
            # nosing strip (stone) then tread (trachyte)
            s_n = s_r + 0.08 * (1 if side < 0 else -1)
            for (q0, q1, m) in ((s_r, s_n, stone), (s_n, s_t, tread_m)):
                lo, hi = (q0, q1) if q0 < q1 else (q1, q0)
                nt = max(1, int(round(2 * ti / 0.8)))
                for j in range(nt):
                    ta, tb = -ti + 2 * ti * j / nt, -ti + 2 * ti * (j + 1) / nt
                    quad(P(lo, ta, z1), P(hi, ta, z1), P(hi, tb, z1), P(lo, tb, z1), [(lo, ta), (hi, ta), (hi, tb), (lo, tb)], m, up)
    quad(P(s_l0, -ti, ztop), P(s_l1, -ti, ztop), P(s_l1, ti, ztop), P(s_l0, ti, ztop), [(s_l0, -ti), (s_l1, -ti), (s_l1, ti), (s_l0, ti)], tread_m, up)
    # ---- arch soffit (brick) between the abutments
    R = ((Wc / 2) ** 2 + (zcr - zsp) ** 2) / (2 * (zcr - zsp)); zc = zcr - R
    def zarch(s): return zc + math.sqrt(max(0.0, R * R - (s - sc) ** 2))
    K = max(8, int(Wc / 0.5))
    ss = [sa + (sb - sa) * i / K for i in range(K + 1)]
    for i in range(K):
        s0, s1 = ss[i], ss[i + 1]; za, zb = zarch(s0), zarch(s1)
        nz = ((sc - (s0 + s1) / 2), (zc - (za + zb) / 2))
        ln = math.hypot(*nz); nrm = (d[0] * nz[0] / ln, d[1] * nz[0] / ln, nz[1] / ln)
        quad(P(s0, -hw, za), P(s0, hw, za), P(s1, hw, zb), P(s1, -hw, zb), [(s0, -hw), (s0, hw), (s1, hw), (s1, -hw)], brick, nrm)
    # ---- side faces (spandrel + parapet as one brick wall per side), outer and inner
    def ztread(s):
        if s <= s_lo or s >= s_hi: return GROUND_Z
        if s_l0 <= s <= s_l1: return ztop
        if s < s_l0: return GROUND_Z + (s - s_lo) / (s_l0 - s_lo) * (ztop - GROUND_Z)
        return GROUND_Z + (s_hi - s) / (s_hi - s_l1) * (ztop - GROUND_Z)
    PAR = 0.95
    top = [(s, ztread(s) + PAR) for s in np.linspace(s_lo, s_hi, 24)]
    bottom = [(s_lo, GROUND_Z - 0.02), (sa, GROUND_Z - 0.02), (sa, zsp)] + [(s, zarch(s)) for s in ss[1:-1]] + [(sb, zsp), (sb, GROUND_Z - 0.02), (s_hi, GROUND_Z - 0.02)]
    outline = bottom + top[::-1]
    V, T = triangulate([outline], max_area=0.5)
    if len(T):
        for side in (-1, 1):
            t = side * hw
            P3 = np.array([P(v[0], t, v[1]) for v in V])
            nrm = (n_[0] * side, n_[1] * side, 0.0)
            tri = T if side > 0 else T[:, ::-1]
            # winding: for side +1 the outward normal is +n_; check orientation and flip if needed
            e1 = P3[tri[0][1]] - P3[tri[0][0]]; e2 = P3[tri[0][2]] - P3[tri[0][0]]
            if np.dot(np.cross(e1, e2), nrm) < 0: tri = tri[:, ::-1]
            mb.add(P3, tri, N=np.tile(nrm, (len(P3), 1)), UV=V, mat=brick, c1=c1)
    # inner parapet faces (from the tread line up to the cap)
    for side in (-1, 1):
        t = side * ti; nrm = (-n_[0] * side, -n_[1] * side, 0.0)
        for i in range(len(top) - 1):
            s0, s1 = top[i][0], top[i + 1][0]
            q = [P(s0, t, ztread(s0) - 0.02), P(s1, t, ztread(s1) - 0.02), P(s1, t, top[i + 1][1]), P(s0, t, top[i][1])]
            uv = [(s0, ztread(s0)), (s1, ztread(s1)), (s1, top[i + 1][1]), (s0, top[i][1])]
            if side > 0: mb.add_planar(q, [[0, 2, 1], [0, 3, 2]], nrm, uv, mat=brick, c1=c1)
            else: mb.add_planar(q, [[0, 1, 2], [0, 2, 3]], nrm, uv, mat=brick, c1=c1)
        # stone cap on the parapet (top face + outer lip)
        for i in range(len(top) - 1):
            s0, z0 = top[i]; s1, z1 = top[i + 1]
            t0, t1 = (ti - 0.03, hw + 0.04) if side > 0 else (-hw - 0.04, -ti + 0.03)
            quad(P(s0, t0, z0 + 0.1), P(s1, t0, z1 + 0.1), P(s1, t1, z1 + 0.1), P(s0, t1, z0 + 0.1), [(s0, t0), (s1, t0), (s1, t1), (s0, t1)], stone, up) if side > 0 else \
            quad(P(s0, t0, z0 + 0.1), P(s1, t0, z1 + 0.1), P(s1, t1, z1 + 0.1), P(s0, t1, z0 + 0.1), [(s0, t0), (s1, t0), (s1, t1), (s0, t1)], stone, up)
            to = t1 if side > 0 else t0; no = (n_[0] * side, n_[1] * side, 0.0)
            q = [P(s0, to, z0 - 0.02), P(s1, to, z1 - 0.02), P(s1, to, z1 + 0.1), P(s0, to, z0 + 0.1)]
            if side > 0: mb.add_planar(q, [[0, 1, 2], [0, 2, 3]], no, [(s0, z0), (s1, z1), (s1, z1 + .12), (s0, z0 + .12)], mat=stone, c1=c1)
            else: mb.add_planar(q, [[0, 2, 1], [0, 3, 2]], no, [(s0, z0), (s1, z1), (s1, z1 + .12), (s0, z0 + .12)], mat=stone, c1=c1)
    # archivolt: Istrian stone ring on both faces
    for side in (-1, 1):
        t = side * (hw + 0.03); no = (n_[0] * side, n_[1] * side, 0.0)
        for i in range(K):
            s0, s1 = ss[i], ss[i + 1]
            def ring(s, r):
                ang = math.atan2(zarch(s) - zc, s - sc)
                return (sc + math.cos(ang) * (R + r), zc + math.sin(ang) * (R + r))
            a0, a1 = ring(s0, 0.0), ring(s1, 0.0); b0, b1 = ring(s0, 0.32), ring(s1, 0.32)
            q = [P(a0[0], t, a0[1]), P(a1[0], t, a1[1]), P(b1[0], t, b1[1]), P(b0[0], t, b0[1])]
            if side > 0: mb.add_planar(q, [[0, 2, 1], [0, 3, 2]], no, [a0, a1, b1, b0], mat=stone, c1=c1)
            else: mb.add_planar(q, [[0, 1, 2], [0, 2, 3]], no, [a0, a1, b1, b0], mat=stone, c1=c1)
    return dict(lo=P(s_lo, 0, GROUND_Z), hi=P(s_hi, 0, GROUND_Z), ztop=ztop, w=W,
                walk=dict(a=[float(a[0]), float(a[1])], d=[float(d[0]), float(d[1])], ti=float(ti), s=[float(s_lo), float(s_l0), float(s_l1), float(s_hi)], ztop=float(ztop)))
