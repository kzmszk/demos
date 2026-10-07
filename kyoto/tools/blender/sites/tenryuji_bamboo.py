"""竹林の小径 and 野宮神社.

The path: OSM 105574212 (野宮神社 → the 天龍寺 north-gate junction, ~5 m) and its continuation 1150077273 (the track up
to 大河内山荘), 410 m, rising from 46.6 m to 70.3 m.  Both sides: brown brushwood fences (柴垣, ~1.4 m, two green
bamboo rails on the path side), gaps where paths join; behind them a dense 孟宗竹 grove (B.tree('take'), clumps of
5-8 culms, 13-22 m) in a band along the path and the OSM bamboo polygons.

野宮神社: the 黒木鳥居 (bark-covered 神明 torii with a thick shimenawa) at the top of a few rough steps from the path,
the 小柴垣 to both sides, a gravel court, the 本殿 between two smaller shrines behind a vermilion fence with red lanterns,
the じゅうたん苔 moss garden behind."""
import math
import numpy as np
import shapely
import shapely.ops
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, box
from shapely.ops import unary_union
from jk import prim, arch, Frame
from jk import roof as jroof
from . import tenryuji_kit as K
from .tenryuji_kit import Loc, facing, ribbon, quad, rect_walk, WD, nrm

PATH = [(-7703.0, 3535.0), (-7719.3, 3531.7), (-7730.2, 3534.9), (-7741.6, 3536.9), (-7758.5, 3537.0), (-7777.0, 3535.7), (-7803.2, 3529.5),
        (-7825.7, 3523.7), (-7900.4, 3501.0), (-7908.9, 3496.9), (-7914.6, 3494.0), (-7920.6, 3489.7), (-7924.6, 3485.6), (-7948.8, 3453.4),
        (-7955.9, 3447.0), (-7962.3, 3444.4), (-7968.4, 3443.7), (-7981.6, 3445.6), (-7989.1, 3444.2), (-8075.8, 3407.8)]
T_JUNCTION = 212.7          # the north gate path joins (south side)
NONOMIYA_REPLACED = [319336312, 319572979, 319572951, 319572973, 319572944]

def smooth_line(pts, n=3):
    return K.chaikin(pts, n, closed=False)

def half_width(t):
    """half the walkable width between the fences at station t (m): the road part ~4.6 m, the track ~3.8 m"""
    return 2.35 if t < T_JUNCTION + 6 else 2.1

def offset_side(line, ts, side, off_fn):
    """points offset to the left (side=+1) or right (-1) of the line at stations ts by off_fn(t)"""
    out = []
    for t in ts:
        p = np.array(line.interpolate(t).coords[0])
        a = np.array(line.interpolate(max(0, t - 1.0)).coords[0]); b = np.array(line.interpolate(min(line.length, t + 1.0)).coords[0])
        d = nrm(b - a); n = np.array([-d[1], d[0]])
        out.append(p + n * side * off_fn(t))
    return np.array(out)

# ------------------------------------------------------------------ 柴垣 (brushwood fence)
GZ = None              # the path's own ground (set by path_ground); None -> the DEM
def gz(S, x, y):
    return GZ(x, y) if GZ is not None else float(S.ground(x, y))

def shibagaki(B, S, pts, side_out, *, h=1.42, th=0.2, seed=0, rails=(0.32, 0.86), dark=False, rail_mat='bamboo', post_mat=None, cap=False):
    """a brushwood fence along a 2D polyline (already sampled every ~0.3 m): a slab of upright twigs (wood_natural with
    the grain up and squeezed: fine vertical streaks) with a ragged top and a fringe of twig spikes, horizontal bamboo
    rails on the path side.  side_out: +1 if the path is on the left of travel (rails go on that side)."""
    rng = np.random.default_rng(seed)
    P = np.asarray(pts, float); m = len(P)
    if m < 2: return
    mat = 'wood_dark' if dark else 'wood_natural'
    T = np.gradient(P, axis=0); T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    Nn = np.c_[-T[:, 1], T[:, 0]] * side_out            # towards the path
    zg = np.array([gz(S, x, y) for (x, y) in P])
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    top = zg + h + rng.uniform(-0.08, 0.1, m) + 0.06 * np.sin(s * 0.9 + seed)
    front = P + Nn * 0.0; back = P - Nn * th
    # faces: front (path side), back, top strip
    V = []
    for i in range(m):
        V += [np.r_[front[i], zg[i] - 0.15], np.r_[front[i], top[i]], np.r_[back[i], top[i] - 0.05], np.r_[back[i], zg[i] - 0.15]]
    V = np.array(V)
    if dark:      # old_planks: vertical boards -> fine vertical streaks when squeezed along the fence
        UV = np.array([[s[i] * 5.0, z] for i in range(m) for z in (zg[i] - 0.15, top[i], top[i] + th, top[i] + th + h)])
    else:         # hinoki_planks: horizontal boards -> turn the grain upright, the board joints become twig lines
        UV = np.array([[z, s[i] * 4.0] for i in range(m) for z in (zg[i] - 0.15, top[i], top[i] + th, top[i] + th + h)])
    I = []
    for i in range(m - 1):
        a = 4 * i; b = a + 4
        I += [[a, b, b + 1], [a, b + 1, a + 1]]            # front
        I += [[a + 1, b + 1, b + 2], [a + 1, b + 2, a + 2]]  # top
        I += [[a + 2, b + 2, b + 3], [a + 2, b + 3, a + 3]]  # back
    I = np.array(I)
    # orient the front faces toward the path
    fn = np.cross(V[I[:, 1]] - V[I[:, 0]], V[I[:, 2]] - V[I[:, 0]])
    c = V[I].mean(1)
    want = np.zeros_like(fn)
    for k in range(len(I)):
        i = I[k, 0] // 4; part = k % 6 // 2
        want[k] = np.r_[Nn[i], 0] if part == 0 else (np.array([0, 0, 1.0]) if part == 1 else np.r_[-Nn[i], 0])
    flip = (fn * want).sum(1) < 0
    I[flip] = I[flip][:, ::-1]
    B.add(V, I, mat, UV=UV)
    # fringe: thin twig spikes above the top, leaning both ways
    for i in range(0, m - 1):
        for k in range(4):
            t = rng.uniform(0, 1)
            p = front[i] + (front[i + 1] - front[i]) * t - Nn[i] * rng.uniform(0.02, th - 0.02)
            z0 = top[i] + (top[i + 1] - top[i]) * t - 0.08
            hh = rng.uniform(0.07, 0.26); w = rng.uniform(0.04, 0.09)
            lean = T[i] * rng.uniform(-0.12, 0.12) + Nn[i] * rng.uniform(-0.08, 0.08)
            a = np.r_[p - T[i] * w / 2, z0]; b = np.r_[p + T[i] * w / 2, z0]; tip = np.r_[p + lean, z0 + hh]
            Pq = np.array([a, b, tip])
            uvq = np.array([[0, 0], [w * 5, 0], [w * 2.5, hh]]) if dark else np.array([[z0, 0], [z0, w * 4], [z0 + hh, w * 2]])
            B.add(Pq, [[0, 1, 2]], mat, UV=uvq, tag='detail')
            B.add(Pq, [[0, 2, 1]], mat, UV=uvq, tag='detail')
    # rails on the path side (split bamboo poles), tied every ~1.8 m; posts behind
    for zr in rails:
        R = np.c_[front + Nn * 0.04, zg + zr]
        step = max(1, int(1.6 / max(s[-1] / (m - 1), 0.05)))
        for i0 in range(0, m - 1, step):
            i1 = min(m - 1, i0 + step)
            prim.cyl(B, R[i0], R[i1] + (R[i1] - R[i0]) * 0.02, 0.032, 0.032, 6, rail_mat, caps=(False, False), tag='detail' if zr != rails[0] else 'main')
    if not post_mat:
        for i in range(0, m, max(1, int(1.8 / max(s[-1] / (m - 1), 0.05)))):
            q = front[i] + Nn[i] * 0.07
            prim.cyl(B, np.r_[q, zg[i] - 0.15], np.r_[q, zg[i] + rails[-1] + 0.12], 0.028, 0.026, 6, rail_mat, tag='detail')
    if post_mat:
        for i in range(0, m, max(1, int(1.8 / max(s[-1] / (m - 1), 0.05)))):
            q = front[i] + Nn[i] * 0.06
            prim.cyl(B, np.r_[q, zg[i] - 0.2], np.r_[q, top[i] + 0.05], 0.06, 0.055, 7, post_mat)
    if cap:
        Cp = np.c_[front - Nn * th / 2, top + 0.02]
        prim.sweep(B, Cp, [(-th * 0.7, -0.04), (th * 0.7, -0.04), (th * 0.4, 0.06), (-th * 0.4, 0.06)], mat, tag='detail')
    ribbon(B, np.c_[front - Nn * th / 2, np.zeros(m)], 0.35, 'block')

# ------------------------------------------------------------------ the path, fences, bamboo
def path_ground(B, S, line):
    """the path's own ground: level across the walk (the centreline height, smoothed along the path), blending back to
    the DEM 3.5 m behind the fences (the grove floor banks up behind them); returns the height function"""
    global GZ
    Lt = line.length
    ts = np.arange(0.0, Lt + 1.0, 1.0)
    P = np.array([line.interpolate(t).coords[0] for t in ts])
    zc = S.ground(P[:, 0], P[:, 1])
    k = 7
    zs = np.convolve(np.pad(zc, k, mode='edge'), np.ones(2 * k + 1) / (2 * k + 1), mode='same')[k:-k]
    zs = np.clip(zs, zc - 0.5, zc + 0.5)
    region = shapely.ops.substring(line, 1.5, Lt - 1.0).buffer(half_width(0) + 4.2, cap_style='flat').simplify(0.2)
    shapely.prepare(region)
    def smooth01(u):
        u = min(max(u, 0.0), 1.0); return u * u * (3 - 2 * u)
    def hf(x, y):
        p = Point(x, y)
        t = line.project(p); d = line.distance(p)
        z0 = float(np.interp(t, ts, zs)) + 0.02
        hw = half_width(t) + 0.5
        w = smooth01((d - hw) / 3.4)
        w = max(w, 1.0 - smooth01(min(t - 1.5, Lt - 1.0 - t) / 4.0))
        D = float(S.ground(x, y))
        return z0 * (1 - w) + D * w if w < 1 else D
    def hf2(x, y):
        return hf(x, y) if region.contains(Point(x, y)) else float(S.ground(x, y))
    def surf(x, y):
        p = Point(x, y)
        return K.SID['soil'] if line.distance(p) < half_width(line.project(p)) + 0.05 else K.SID['forest']
    K.mesh_region(B, region, hf, 0.8, surf_of=surf, walk_of=lambda x, y: True)
    S.cut.append([list(map(list, region.exterior.coords))])
    GZ = hf2
    return hf2, region

def path_and_fences(B, S):
    line = LineString(smooth_line(PATH, 2))
    Lt = line.length
    path_ground(B, S, line)
    tt = lambda x, y: line.project(Point(x, y))
    t_torii = tt(-7721.9, 3539.0); t_fw = tt(-7825.7, 3523.7); t_gate = tt(-7908.9, 3496.9)
    # side +1 = left of the west-bound travel = south (the 天龍寺 north gate); -1 = north (野宮神社, the footway north)
    gaps = {-1: [(-5, 3.0), (t_torii - 12.8, t_torii + 12.8), (t_fw - 2.6, t_fw + 2.6), (Lt - 7.5, Lt + 5)],
            1: [(-5, 3.0), (t_gate - 3.6, t_gate + 3.0), (Lt - 14.0, Lt + 5)]}
    globals()['GAPS'] = gaps
    # left side of travel (west-bound) is north on the first part; the shrine sits there at t ≈ 18-24
    ts_all = np.arange(0.0, Lt, 0.32)
    fences = []
    for side in (1, -1):
        runs = []; cur = []
        for t in ts_all:
            if any(a <= t <= b for (a, b) in gaps[side]):
                if len(cur) > 3: runs.append(cur)
                cur = []
            else: cur.append(t)
        if len(cur) > 3: runs.append(cur)
        for k, run in enumerate(runs):
            pts = offset_side(line, run, side, lambda t: half_width(t) + 0.12)
            shibagaki(B, S, pts, -side, seed=17 * k + (side > 0) * 5)
            fences.append((side, run))
    # the path surface (paint) and a walk ribbon only where the DEM is rough? (generic terrain is walkable)
    return line, fences

def bamboo_planting(B, S, line, rng):
    """the grove: a band 3 - 30 m either side of the path (minus buildings, roads, the railway, the shrine court) plus
    the OSM bamboo polygons (-17656638, two parts).  Clumps of the viewer's 'take' (5-8 culms each)."""
    near = line.buffer(14.0, cap_style='flat').difference(line.buffer(3.0, cap_style='flat'))
    far = line.buffer(32.0, cap_style='flat').difference(line.buffer(14.0, cap_style='flat'))
    osm = None
    for f in S.osm['landuse']:
        if f['id'] == -17656638: osm = K.osm_poly(f)
    if osm is not None: far = unary_union([far, osm.difference(line.buffer(14.0, cap_style='flat'))])
    blk = []
    for b in S.osm['buildings']:
        try: blk.append(Polygon(K.outer(b['poly'])).buffer(1.5))
        except Exception: pass
    for w in S.osm['ways']:
        if w['id'] in (105574212, 1150077273): continue
        for ln in w['line']:
            if len(ln) > 1: blk.append(LineString(ln).buffer((w.get('width') or 2.0) / 2 + 0.8))
    for w in S.osm['water']:
        try: blk.append(K.osm_poly(w).buffer(1.0))
        except Exception: pass
    # the railway (嵯峨野観光線 / old 山陰線) north of the track
    rail = LineString([(-7344.0, 3684.0), (-7540.0, 3657.0), (-7716.0, 3593.0), (-7933.0, 3511.0), (-8064.0, 3460.0), (-8090.0, 3450.0)])
    blk.append(rail.buffer(4.5))
    # the shrine court and the moss garden of 野宮神社, the 天龍寺 garden near the north gate
    blk.append(Polygon([(-7738, 3536.5), (-7703, 3536.5), (-7700, 3575), (-7740, 3575)]))
    blk.append(Polygon([(-7728.5, 3532.5), (-7714.5, 3532.0), (-7714.0, 3541.0), (-7729.5, 3542.0)]))      # the torii steps
    blk.append(Point(-7905.0, 3490.0).buffer(7.0))                                                          # the north gate
    blk.append(Point(-8083.0, 3414.8).buffer(8.0))                                                          # the 大河内山荘 gate
    blocked = unary_union(blk)
    near = near.difference(blocked); far = far.difference(blocked).difference(K.neighbour_zone())
    # keep the grove out of the 天龍寺 garden's lower part (it is planted with maples) and the 大河内山荘 grounds west of the gate
    okochi = None
    for f in S.osm['landuse']:
        if f['id'] == 677236682: okochi = K.osm_poly(f)
    if okochi is not None:
        okc = okochi.difference(Polygon([(-8090, 3395), (-7990, 3395), (-7990, 3520), (-8090, 3520)]))
        near = near.difference(okc); far = far.difference(okc)
    zone_near, zone_far = near, far
    pts_n = K.poisson(near, 1.85, rng, 20000)
    pts_f = K.poisson(far, 2.7, rng, 20000)
    # a ragged outer edge: drop far points beyond 22-31 m (smooth noise) unless they are in the OSM grove
    def noise(x, y):
        return (math.sin(x * 0.11 + 1.3) * math.cos(y * 0.13 - 0.4) + 0.6 * math.sin((x + y) * 0.07 + 2.1)) / 1.6
    keep = []
    for (x, y) in pts_f:
        d = line.distance(Point(x, y))
        if (osm is not None and osm.contains(Point(x, y))) or d < 26.0 + 6.0 * noise(x, y): keep.append((x, y))
    pts_f = np.array(keep) if keep else np.zeros((0, 2))
    n = 0
    for (pts, k) in ((pts_n, 0), (pts_f, 1)):
        for (x, y) in pts:
            if k == 1 and rng.random() < 0.04:
                sp = 'kashi' if rng.random() < 0.6 else 'momiji'
                B.tree(sp, float(x), float(y), float(S.ground(x, y)) - 0.1, rng.uniform(0.8, 1.1), rng.uniform(0, 6.28))
            else:
                B.tree('take', float(x), float(y), gz(S, x, y) - 0.15, rng.uniform(1.32, 1.62), rng.uniform(0, 6.28))
            n += 1
    # a wall of culms right behind the fences
    Lt = line.length
    for side in (1, -1):
        for t in np.arange(1.0, Lt - 2.0, 1.25):
            if any(a - 0.5 <= t <= b + 0.5 for (a, b) in GAPS[side]): continue
            off = half_width(t) + 0.12 + rng.uniform(0.75, 1.6)
            p = offset_side(line, [t + rng.uniform(-0.4, 0.4)], side, lambda _t: off)[0]
            if blocked.contains(Point(p)): continue
            B.tree('take', float(p[0]), float(p[1]), gz(S, *p) - 0.15, rng.uniform(1.38, 1.62), rng.uniform(0, 6.28))
            n += 1
    planted = unary_union([zone_near, zone_far]).buffer(0.5)
    # the grove floor: forest (dry leaves) where OSM has no landuse
    for g in (planted.geoms if hasattr(planted, 'geoms') else [planted]):
        if g.area < 20: continue
        gg = g.simplify(0.8)
        S.paint.append({'poly': [list(map(list, gg.exterior.coords))] + [list(map(list, r.coords)) for r in gg.interiors], 'surf': 'forest'})
    return n, planted

# ------------------------------------------------------------------ 野宮神社
def kuroki_torii(B, x, y, z, yaw, h=3.75, span=3.1, r=0.16, seed=3):
    """黒木鳥居: bark-covered (dark) 神明-type: straight log kasagi, a log nuki through the pillars, no gakuzuka; a
    thick shimenawa with shide and straw tassels"""
    rng = np.random.default_rng(seed)
    with Frame(B, x, y, z, yaw):
        for s in (-1, 1):
            xs = s * span / 2
            pts = np.array([(xs + 0.02 * math.sin(k * 1.3 + s), 0.02 * math.cos(k * 0.9), -0.2 + (h + 0.25) * k / 6) for k in range(7)])
            rr = np.linspace(r * 1.08, r * 0.92, 7)
            for i in range(6):
                prim.cyl(B, pts[i], pts[i + 1], rr[i], rr[i + 1], 10, WD, caps=(False, i == 5))
            prim.cyl(B, (xs, 0, -0.05), (xs, 0, 0.08), r * 1.6, r * 1.5, 8, 'stone')
        # nuki (log, slightly proud)
        prim.cyl(B, (-span / 2 - 0.32, 0, h * 0.74), (span / 2 + 0.32, 0, h * 0.74 + 0.02), 0.105, 0.1, 9, WD)
        # kasagi: a straight log, ends cut, lying on the pillar tops
        prim.cyl(B, (-span / 2 - 0.7, 0, h + 0.12), (span / 2 + 0.7, 0, h + 0.14), r * 1.05, r * 1.02, 10, WD)
        # shimenawa: a thick rope sagging between the pillars just under the nuki, with 4 straw tassels and shide
        zr = h * 0.74 - 0.18
        rope = [(-span / 2 + r, 0.0, zr), (-span / 4, -0.03, zr - 0.18), (0.0, -0.04, zr - 0.24), (span / 4, -0.03, zr - 0.18), (span / 2 - r, 0.0, zr)]
        rope = K.chaikin(rope, 2, closed=False)
        rope = np.array([(p[0], p[1], p[2]) for p in rope])
        prim.sweep(B, rope, [(0.075 * math.cos(a), 0.075 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 7)[:-1]], 'bamboo', smooth=True, tag='main')
        for xx in np.linspace(-span / 2 + 0.55, span / 2 - 0.55, 4):
            zz = float(np.interp(xx, rope[:, 0], rope[:, 2]))
            prim.cyl(B, (xx, -0.02, zz - 0.06), (xx, -0.02, zz - 0.42), 0.05, 0.08, 6, 'bamboo', tag='detail')
        for xx in np.linspace(-span / 2 + 0.3, span / 2 - 0.3, 7):
            zz = float(np.interp(xx, rope[:, 0], rope[:, 2]))
            zig = [(xx - 0.06, zz - 0.05), (xx + 0.06, zz - 0.05), (xx + 0.06, zz - 0.2), (xx - 0.03, zz - 0.22), (xx - 0.03, zz - 0.36), (xx + 0.06, zz - 0.38), (xx + 0.06, zz - 0.52), (xx - 0.06, zz - 0.52)]
            P = np.array([(a, -0.09, b) for (a, b) in zig])
            I = [[0, 1, 2], [0, 2, 3], [3, 4, 5], [3, 5, 2], [4, 5, 6], [4, 6, 7]]
            B.add(P, I, 'white_paint', tag='detail'); B.add(P, [t[::-1] for t in I], 'white_paint', tag='detail')
    # blockers at the pillar feet
    c, s_ = math.cos(yaw), math.sin(yaw)
    for sx in (-1, 1):
        px, py = x + c * sx * span / 2, y + s_ * sx * span / 2
        ribbon(B, [(px - 0.2, py), (px + 0.2, py)], 0.4, 'block')

def small_shrine(B, loc, zg, *, w=2.4, d=2.2, h=2.2, color=WD, cover='copper', base=0.45, front_ext=1.0, ridge=True, lanterns=0):
    """a small 流造 / 切妻 shrine on a stone base, gable front (u along the front), roof extended over the front"""
    with loc.frame(B):
        prim.box(B, -w / 2 - 0.4, -d / 2 - 0.5, zg - 0.3, w / 2 + 0.4, d / 2 + 0.35, zg + base, 'stone')
        z0 = zg + base
        for sx in (-1, 1):
            for sv in (-1, 1):
                prim.box(B, sx * w / 2 - 0.08, sv * d / 2 - 0.08, z0, sx * w / 2 + 0.08, sv * d / 2 + 0.08, z0 + h, color)
            prim.box(B, sx * w / 2 - 0.07, -d / 2 - front_ext - 0.07, z0, sx * w / 2 + 0.07, -d / 2 - front_ext + 0.07, z0 + h - 0.15, color)
        prim.box(B, -w / 2 + 0.05, -d / 2 + 0.05, z0, w / 2 - 0.05, d / 2 - 0.05, z0 + h - 0.1, WD)
        prim.box(B, -w / 2 + 0.2, -d / 2 - 0.01, z0 + 0.3, w / 2 - 0.2, -d / 2 + 0.04, z0 + h - 0.4, 'wood_natural', tag='detail')
        prim.box(B, -w / 2 - 0.2, -d / 2 - front_ext - 0.15, z0, w / 2 + 0.2, d / 2 + 0.2, z0 + 0.1, 'wood_natural')
        with Frame(B, 0, -front_ext / 2, 0, math.pi / 2):
            jroof.roof(B, d + front_ext, w + 0.1, z0 + h, 0.5, kind='kirizuma', cover=cover, pitch=0.62, verge=0.45, rafter=0.2,
                       rafter_mat=color, rafter_end='white_paint' if color == WD else 'white_paint', gable_wall=WD, ends=None, sori=0.0, edge=0.16)
        for k in range(lanterns):
            x = -w / 2 + (k + 0.5) * w / lanterns
            arch.chochin(B, x, -d / 2 - front_ext + 0.15, z0 + h - 0.95, r=0.16, h=0.48)
        ribbon(B, [(-w / 2 - 0.4, 0), (w / 2 + 0.4, 0)], d + 0.8, 'block')

def red_fence(B, pts, z_of, h=1.0, step=0.14):
    """玉垣 of vermilion slats: posts, two rails, close slats"""
    P = [np.asarray(p, float) for p in pts]
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]; L = np.linalg.norm(b - a)
        if L < 0.1: continue
        d = (b - a) / L
        za = z_of(*a); zb = z_of(*b)
        for t in np.arange(0, L + 0.01, 1.2):
            q = a + d * t; z = za + (zb - za) * t / L
            prim.box(B, q[0] - 0.06, q[1] - 0.06, z - 0.05, q[0] + 0.06, q[1] + 0.06, z + h + 0.08, 'vermilion')
        for zr in (0.15, h - 0.08):
            prim.obox(B, np.r_[a, za + zr], np.r_[b, zb + zr], 0.06, 0.07, 'vermilion')
        for t in np.arange(step / 2, L, step):
            q = a + d * t; z = za + (zb - za) * t / L
            prim.obox(B, np.r_[q, z + 0.1], np.r_[q, z + h], 0.07, 0.025, 'vermilion', up=(d[0], d[1], 0), tag='detail')
        ribbon(B, [a, b], 0.3, 'block')

def nonomiya(B, S, line):
    out = {}
    tx, ty = -7721.9, 3539.0
    yaw = math.radians(17.0)            # the shrine axis faces SSE (front_deg -73)
    fwd = np.array([math.cos(yaw - math.pi / 2), math.sin(yaw - math.pi / 2)])      # towards the path
    zt = 47.35
    # steps from the path (rough stones) up to the torii
    p_path = np.array([tx, ty]) + fwd * 4.6
    p_top = np.array([tx, ty]) + fwd * 0.8
    K.terrain_steps(B, S, [p_path, p_top], 4.0, rise=0.16, z0=gz(S, *p_path) + 0.02, z1=zt, mat='stone', curb=False, rough=0.06, seed=4)
    for k in range(5):
        t = np.array([tx, ty]) + fwd * (1.0 + 0.75 * k)
        for sx in np.linspace(-1.9, 1.9, 6):
            q = t + np.array([math.cos(yaw), math.sin(yaw)]) * sx
            K.rock(B, (q[0], q[1], float(S.ground(*q)) + 0.05), 0.32, 100 + k * 7 + int(sx * 3), flat=0.35, tag='detail')
    kuroki_torii(B, tx, ty, zt, yaw)
    # 小柴垣 both sides of the torii along the path (dark brushwood, green bamboo rails, bark posts), with a cap
    u = np.array([math.cos(yaw), math.sin(yaw)])
    for sgn in (-1, 1):
        a = np.array([tx, ty]) + u * sgn * 2.15 - fwd * 0.2
        b = a + u * sgn * 9.5 + fwd * (-0.6 if sgn > 0 else 0.4)
        n = max(2, int(np.linalg.norm(b - a) / 0.3))
        pts = np.array([a + (b - a) * k / n for k in range(n + 1)])
        side = 1 if sgn < 0 else -1
        shibagaki(B, S, pts, side, h=1.75, th=0.16, seed=50 + sgn, rails=(0.28, 0.82, 1.38), dark=True, post_mat=WD, cap=True)
    # the sign board (源氏物語の旧跡 / 嵯峨野の宮) between two bark posts, right of the torii
    sb = np.array([tx, ty]) + u * 4.8 + fwd * 0.35
    zs = float(S.ground(*sb))
    for sx in (-0.75, 0.75):
        q = sb + u * sx
        prim.cyl(B, (q[0], q[1], zs - 0.2), (q[0], q[1], zs + 1.9), 0.09, 0.085, 8, WD)
    q0 = sb - u * 0.62; q1 = sb + u * 0.62
    prim.obox(B, (q0[0], q0[1], zs + 1.25), (q1[0], q1[1], zs + 1.25), 1.0, 0.06, 'wood_natural', up=(fwd[0], fwd[1], 0))
    prim.obox(B, (q0[0] - u[0] * 0.2, q0[1] - u[1] * 0.2, zs + 1.82), (q1[0] + u[0] * 0.2, q1[1] + u[1] * 0.2, zs + 1.82), 0.14, 0.14, WD)
    # the court (gravel) and the 本殿 group: a central shrine (gable front, copper) between two smaller ones, steps,
    # a vermilion 玉垣 with red lanterns
    court = Polygon([np.array([tx, ty]) + u * a_ + fwd * b_ for (a_, b_) in ((-9, 0.8), (9, 0.8), (9, -14), (-9, -14))])
    S.paint.append({'poly': [list(map(list, court.exterior.coords))], 'surf': 'gravel'})
    hc = np.array([tx, ty]) - fwd * 10.2
    zh = float(S.ground(*hc)) + 0.1
    loc_h = Loc(hc[0], hc[1], yaw)
    with loc_h.frame(B):
        prim.box(B, -6.6, -2.4, zh - 0.3, 6.6, 2.6, zh + 0.38, 'stone')
        K.stairs_build(B, (0, -3.6), (0, -2.4), zh - 0.05, zh + 0.38, 2.4, 'stone', riser=0.15)
    small_shrine(B, Loc(*loc_h.w(0, 0.3), yaw), zh + 0.38, w=3.0, d=2.6, h=2.5, cover='copper', base=0.35, front_ext=1.5, lanterns=0)
    small_shrine(B, Loc(*loc_h.w(-4.3, 0.6), yaw), zh + 0.38, w=2.2, d=1.9, h=2.0, cover='copper', base=0.3, front_ext=0.9, lanterns=4)
    small_shrine(B, Loc(*loc_h.w(4.3, 0.6), yaw), zh + 0.38, w=2.2, d=1.9, h=2.0, cover='copper', base=0.3, front_ext=0.9, lanterns=4)
    # 玉垣 in front of the group with an opening at the centre
    fz = lambda x, y: zh + 0.38
    red_fence(B, [loc_h.w(-6.4, -2.2), loc_h.w(-1.3, -2.2)], fz)
    red_fence(B, [loc_h.w(1.3, -2.2), loc_h.w(6.4, -2.2)], fz)
    # 賽銭箱 and two big lanterns (御神燈)
    with loc_h.frame(B):
        prim.box(B, -0.7, -2.2, zh + 0.38, 0.7, -1.5, zh + 1.25, 'metal_grey')
        for x in (-1.0, 1.0):
            arch.chochin(B, x, -1.3, zh + 2.3, r=0.24, h=0.65)
    # 白福稲荷 (east, vermilion with red torii) and 大黒天 (west) as small shrines
    st = np.array([tx, ty]) + u * 7.0 - fwd * 4.5
    small_shrine(B, Loc(st[0], st[1], yaw - math.pi / 2), float(S.ground(*st)), w=1.6, d=1.5, h=1.7, color='vermilion', cover='copper', base=0.35, front_ext=0.7, lanterns=2)
    arch.torii(B, *(st + u * -1.8), float(S.ground(*(st + u * -1.8))), yaw - math.pi / 2, h=2.2, span=1.5)
    sd = np.array([tx, ty]) - u * 6.8 - fwd * 4.0
    small_shrine(B, Loc(sd[0], sd[1], yaw + math.pi / 2), float(S.ground(*sd)), w=1.6, d=1.5, h=1.7, cover='copper', base=0.35, front_ext=0.7, lanterns=2)
    # 社務所 / 授与所: a low hipped-roof office on the east side of the court
    so = np.array([tx, ty]) + u * 9.5 - fwd * 6.0
    zs2 = float(S.ground(*so))
    loc_s = Loc(so[0], so[1], yaw - math.pi / 2)
    K.hall(B, S, loc_s, L=6.0, D=3.6, nu=3, nv=2, zf=zs2 + 0.45, H=2.5, r=0.12, walls={0: ['glass', 'glass', 'glass'], 1: ['white'], 2: ['white'] * 3, 3: ['white']},
           head=zs2 + 2.3, band=None, ver=0, ver_sides=(), skirt='white', bracket=None, roofkw=dict(kind='yosemune', cover='copper', o=1.0, pitch=0.5, rafter=0.0, sori=0.0))
    # the moss garden behind (じゅうたん苔), lanterns at the torii
    moss = Polygon([np.array([tx, ty]) + u * a_ + fwd * b_ for (a_, b_) in ((-12, -14), (12, -14), (14, -32), (-12, -32))])
    S.paint.append({'poly': [list(map(list, moss.exterior.coords))], 'surf': 'moss'})
    for sx in (-1.3, 1.3):
        q = np.array([tx, ty]) + u * sx * 1.6 - fwd * 2.0
        K.lantern(B, q[0], q[1], float(S.ground(*q)), h=1.6)
    out['court'] = court; out['moss'] = moss
    out['zones'] = [court.buffer(1.0)]
    return out

def build(B, S, parts):
    out = {'replaced': [], 'zones': [], 'no_trees': []}
    rng = np.random.default_rng(2024)
    line = LineString(smooth_line(PATH, 2))
    if 'bamboo' in parts:
        line, fences = path_and_fences(B, S)
        n, planted = bamboo_planting(B, S, line, rng)
        out['planted'] = planted; out['n_bamboo'] = n
        out['no_trees'].append(line.buffer(3.0))
    if 'nonomiya' in parts:
        nm = nonomiya(B, S, line)
        out['replaced'] += NONOMIYA_REPLACED
        out['zones'] += nm['zones']
        out['no_trees'].append(nm['court'])
        # a few maples by the shrine and in the moss garden (the 浩宮 maple by the 社号標)
        mg = nm['moss']
        for (x, y) in K.poisson(mg.buffer(-1.0), 5.0, rng, 30):
            B.tree('momiji', float(x), float(y), float(S.ground(x, y)) - 0.1, rng.uniform(0.9, 1.3), rng.uniform(0, 6.28))
    out['line'] = line
    return out
