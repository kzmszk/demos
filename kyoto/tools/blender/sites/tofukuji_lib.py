"""東福寺 helpers (own module; the shared kit jk/* is not edited): frames on the precinct grids, garden stones, 大仏様
inserted-bracket stacks (三門), ring roofs (裳階 / the lower roof of a 二重門), halls with 裳階, white walls with posts and
a tiled coping, 平唐門, ground meshes with per-triangle surfaces, polyline utilities.

Uses tofukuji_klib (a copy of kiyomizu_lib) and tofukuji_ekit (a copy of eikando_kit) so that this site does not depend
on the other sites' files."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point
from jk import prim, arch, Frame
from jk import roof as jroof
from sites import tofukuji_klib as K
from sites import tofukuji_ekit as EK

ROT = math.radians(-2.4)          # the main grid (三門 - 本堂 - 方丈 - 庫裏) is turned 2.4° clockwise
ROT_K = math.radians(-11.1)       # 常楽庵 (開山堂, 昭堂, 樓門, 普門院)
WHITE = (238, 234, 224, 35)
SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
        'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck']
SID = {n: i for i, n in enumerate(SURF)}
Loc = EK.Loc
nrm = EK.nrm

def gl(x, y, yaw=ROT):
    """a Loc on a grid"""
    return Loc(x, y, yaw)

def ring_of(feature):
    p = feature['poly'] if 'poly' in feature else feature['line']
    while isinstance(p[0][0], (list, tuple)): p = p[0]
    return [tuple(q) for q in p]

def line_of(feature):
    p = feature['line']
    while isinstance(p[0][0], (list, tuple)): p = p[0]
    return np.array(p, float)

def osm_line(S, wid):
    for w in S.osm['ways'] + S.osm['waterways'] + S.osm['barriers']:
        if w['id'] == wid: return line_of(w)
    raise KeyError(wid)

def osm_poly(S, cat, wid):
    for w in S.osm[cat]:
        if w['id'] == wid: return ring_of(w)
    raise KeyError(wid)

# ------------------------------------------------------------------ faces
def quad(B, a, b, c, d, mat, tag='main', out=None, both=False, **kw):
    P = np.array([a, b, c, d], float)
    I = [[0, 1, 2], [0, 2, 3]]
    if out is not None:
        fn = np.cross(P[1] - P[0], P[2] - P[0]) + np.cross(P[2] - P[0], P[3] - P[0])
        if fn @ np.asarray(out, float) < 0: I = [[0, 2, 1], [0, 3, 2]]
    B.add(P, I, mat, tag=tag, **kw)
    if both: B.add(P, [t[::-1] for t in I], mat, tag=tag, **kw)

def oadd(B, P, I, mat, out, **kw):
    P = np.asarray(P, float); I = np.array(I, np.int64).reshape(-1, 3)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    flip = fn @ np.asarray(out, float) < 0
    I[flip] = I[flip][:, ::-1]
    B.add(P, I, mat, **kw)

def poly_flat(B, ring, z, mat, tag='main', holes=(), up=True, **kw):
    prim.polygon(B, [tuple(p[:2]) for p in ring], z, mat, tag=tag, holes=[[tuple(p[:2]) for p in h] for h in holes], up=up, **kw)

# ------------------------------------------------------------------ stones
_ICO = {}
def _ico(sub):
    if sub in _ICO: return _ICO[sub]
    t = (1 + 5 ** 0.5) / 2
    V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    for _ in range(sub):
        mid = {}; F2 = []; V = list(V)
        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                p = (np.asarray(V[a]) + np.asarray(V[b])) / 2; V.append(p / np.linalg.norm(p)); mid[k] = len(V) - 1
            return mid[k]
        for a, b_, c_ in F:
            ab, bc, ca = m(a, b_), m(b_, c_), m(c_, a)
            F2 += [[a, ab, ca], [b_, bc, ab], [c_, ca, bc], [ab, bc, ca]]
        F = F2; V = np.array(V)
    _ICO[sub] = (np.array(V), np.array(F))
    return _ICO[sub]

def stone(B, c, size, seed, mat='stone', tag='main', flat=0.6, sub=2, sink=0.25, aniso=(1.0, 1.0), tilt=0.0, yaw=None, shape='round', **kw):
    """a garden stone: displaced icosphere. shape: 'round', 'stand' (tall, tapering, for 立石), 'slab' (flat top),
    'long' (a lying log-like stone). size = horizontal radius; flat = height / size."""
    r_ = np.random.default_rng(seed)
    V, F = _ico(sub)
    V = V.copy()
    d = 1 + 0.2 * np.sin(V @ r_.normal(0, 2.5, 3)) + 0.12 * np.sin(V @ r_.normal(0, 5, 3)) + 0.05 * np.sin(V @ r_.normal(0, 10, 3))
    V = V * d[:, None]
    if shape == 'stand':
        V[:, :2] *= (1.15 - 0.55 * np.clip((V[:, 2] + 1) / 2, 0, 1) ** 1.3)[:, None]
        V[:, 0] += 0.25 * np.clip(V[:, 2], 0, 1) * r_.uniform(-1, 1)
    elif shape == 'slab':
        V[:, 2] = np.where(V[:, 2] > 0.35, 0.35 + (V[:, 2] - 0.35) * 0.15, V[:, 2])
    else:
        V[:, 2] = np.where(V[:, 2] > 0.55, 0.55 + (V[:, 2] - 0.55) * 0.5, V[:, 2])
    sx, sy, sz = size * aniso[0] * r_.uniform(0.9, 1.1), size * aniso[1] * r_.uniform(0.75, 1.0), size * flat * r_.uniform(0.9, 1.1)
    V = V * [sx, sy, sz]
    if tilt:
        a = r_.uniform(-tilt, tilt); ca, sa = math.cos(a), math.sin(a)
        V = V @ np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]).T
    yw = r_.uniform(0, 2 * math.pi) if yaw is None else yaw
    cy, sy_ = math.cos(yw), math.sin(yw)
    V = V @ np.array([[cy, -sy_, 0], [sy_, cy, 0], [0, 0, 1]]).T
    V = V + np.asarray(c, float) - [0, 0, sz * sink]
    B.add(V, F, mat, smooth=True, tag=tag, **kw)
    return sz * (1 - sink)

# ------------------------------------------------------------------ polylines
def resample(path, step):
    path = np.asarray(path, float)
    seg = np.linalg.norm(np.diff(path[:, :2], axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]; L = s[-1]
    n = max(1, int(math.ceil(L / step)))
    t = np.linspace(0, L, n + 1)
    return np.stack([np.interp(t, s, path[:, k]) for k in range(path.shape[1])], 1), t

def chaikin(pts, it=2, closed=False):
    P = np.asarray(pts, float)
    for _ in range(it):
        Q = []
        n = len(P)
        rng_ = range(n) if closed else range(n - 1)
        if not closed: Q.append(P[0])
        for i in rng_:
            a, b = P[i], P[(i + 1) % n]
            Q.append(a * 0.75 + b * 0.25); Q.append(a * 0.25 + b * 0.75)
        if not closed: Q.append(P[-1])
        P = np.array(Q)
    return P

# ------------------------------------------------------------------ 大仏様 / 禅宗様 bracket stacks (white-tipped)
def arm(B, p0, p1, w, h, mat, end_mat='white_paint', tag='detail', cut=0.35):
    """a bracket arm (肘木) from p0 to p1 (3D), its far end painted, the lower end edge chamfered (繰形)"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d)
    if L < 0.05: return
    d /= L
    prim.obox(B, p0, p1 - d * 0.025, w, h, mat, tag=tag)
    prim.obox(B, p1 - d * 0.025, p1, w * 1.01, h * 1.01, end_mat, tag=tag)
    if cut:      # a curved lower cut under the end: a small sloped block
        q = p1 - d * min(L * 0.5, 0.3) - np.array([0, 0, h * 0.5])
        prim.obox(B, q, p1 - d * 0.03 - np.array([0, 0, h * 0.25]), w * 0.98, h * 0.4, mat, tag=tag)

def masu(B, c, s, mat, end_mat=None, h=None, tag='detail'):
    """斗: a block slightly wider at the top"""
    c = np.asarray(c, float); h = h or s * 0.62
    P = []
    for zz, sc in ((0.0, 0.72), (h * 0.45, 0.72), (h, 1.0)):
        for (du, dv) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            P.append(c + [du * s * 0.5 * sc, dv * s * 0.5 * sc, zz])
    P = np.array(P); I = []
    for r in range(2):
        for i in range(4):
            j = (i + 1) % 4; b0 = r * 4
            I += [[b0 + i, b0 + j, b0 + 4 + j], [b0 + i, b0 + 4 + j, b0 + 4 + i]]
    I += [[8, 9, 10], [8, 10, 11], [0, 2, 1], [0, 3, 2]]
    B.add(P, I, end_mat or mat, tag=tag)
    return c[2] + h

def sashi_stack(B, p, out, along, z0, tiers=4, step_out=0.55, step_up=0.42, w=0.26, h=0.3, mat='wood_dark', end_mat='white_paint',
                r=0.4, lateral=True, lat_len=1.1, tag='detail'):
    """大仏様 挿肘木: arms inserted into the pillar at p (2D) projecting along `out`, one per tier, each longer by step_out,
    a 斗 on each arm end; lateral arms (along the wall) on the arm ends.  Returns (top z, reach from the pillar axis)."""
    p = np.asarray(p, float); o = nrm(np.asarray(out, float)); a = nrm(np.asarray(along, float))
    o3 = np.r_[o, 0]; a3 = np.r_[a, 0]
    zt = z0
    for k in range(tiers):
        z = z0 + k * step_up
        reach = r + (k + 1) * step_out
        p0 = np.r_[p + o * (r * 0.6), z + h / 2]; p1 = np.r_[p + o * reach, z + h / 2]
        arm(B, p0, p1, w, h, mat, end_mat, tag=tag)
        c = np.r_[p + o * (reach - 0.18), z + h]
        top = masu(B, c, 0.36, mat, tag=tag)
        if lateral and k < tiers - 1:
            arm(B, c + np.r_[-a * lat_len, 0] + [0, 0, 0.13], c + np.r_[a * lat_len, 0] + [0, 0, 0.13], w * 0.85, 0.24, mat, end_mat, tag=tag, cut=0.2)
            arm(B, c + np.r_[a * lat_len, 0] + [0, 0, 0.13], c + np.r_[-a * lat_len, 0] + [0, 0, 0.13], w * 0.85, 0.24, mat, end_mat, tag=tag, cut=0)
        zt = max(zt, top)
    return zt, r + tiers * step_out - 0.18

def stack_row(B, us, vs, z0, tiers=4, step_out=0.55, step_up=0.42, mat='wood_dark', end_mat='white_paint', r=0.4, mid=True,
              beams=True, beam_mat='wood_dark', tag='detail'):
    """挿肘木 stacks on every perimeter pillar of the grid (us, vs) (+ intermediate stacks at mid-bay on the upper tiers);
    通肘木 / 桁 running along the walls on each tier's arm ends.  Returns (top z, reach)."""
    us = np.asarray(us, float); vs = np.asarray(vs, float)
    x0, x1, y0, y1 = us[0], us[-1], vs[0], vs[-1]
    sets = []
    for x in us[1:-1]: sets += [((x, y0), (0, -1), (1, 0), False), ((x, y1), (0, 1), (1, 0), False)]
    for y in vs[1:-1]: sets += [((x0, y), (-1, 0), (0, 1), False), ((x1, y), (1, 0), (0, 1), False)]
    if mid:
        for xa, xb in zip(us[:-1], us[1:]):
            xm = (xa + xb) / 2; sets += [((xm, y0), (0, -1), (1, 0), True), ((xm, y1), (0, 1), (1, 0), True)]
        for ya, yb in zip(vs[:-1], vs[1:]):
            ym = (ya + yb) / 2; sets += [((x0, ym), (-1, 0), (0, 1), True), ((x1, ym), (1, 0), (0, 1), True)]
    top = z0; reach = 0
    for (p, o, a, is_mid) in sets:
        if is_mid:
            t, rr = sashi_stack(B, np.asarray(p) + np.asarray(o) * 0.0, o, a, z0 + step_up * 1, tiers - 1, step_out, step_up, mat=mat, end_mat=end_mat, r=r + step_out * 0.0, tag=tag)
        else:
            t, rr = sashi_stack(B, p, o, a, z0, tiers, step_out, step_up, mat=mat, end_mat=end_mat, r=r, tag=tag)
        top = max(top, t); reach = max(reach, rr)
    # corner stacks: diagonal arms + both lateral directions
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = np.array([x0 if sx < 0 else x1, y0 if sy < 0 else y1])
            d = np.array([sx, sy]) / math.sqrt(2)
            t, rr = sashi_stack(B, p, d, (-d[1], d[0]), z0, tiers, step_out * 1.41, step_up, mat=mat, end_mat=end_mat, r=r, lateral=False, tag=tag)
            for o_ in ((sx, 0), (0, sy)):
                sashi_stack(B, p, o_, (o_[1], o_[0]), z0, tiers, step_out, step_up, mat=mat, end_mat=end_mat, r=r, lateral=False, tag=tag)
            top = max(top, t)
    # 通肘木 along the walls on the tiers (main): a continuous member at each arm-end line
    if beams:
        for k in range(tiers):
            off = r + (k + 1) * step_out - 0.18
            zb = z0 + k * step_up + 0.3 + 0.36 * 0.62 + 0.12
            a_, c_ = (x1 - x0) / 2 + off, (y1 - y0) / 2 + off
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            for (p0, p1) in (((cx - a_, cy - c_), (cx + a_, cy - c_)), ((cx + a_, cy - c_), (cx + a_, cy + c_)), ((cx + a_, cy + c_), (cx - a_, cy + c_)), ((cx - a_, cy + c_), (cx - a_, cy - c_))):
                prim.obox(B, (p0[0], p0[1], zb), (p1[0], p1[1], zb), 0.22, 0.24, beam_mat, tag='main' if k == tiers - 1 else tag)
    return top + 0.25, reach

# ------------------------------------------------------------------ roofs
class RingRoof(K.MRoof):
    """a hip ring roof truncated at inward depth `truncate` (from the eave edge): 裳階 / the lower roof of a 二重門.
    rise = height gained from the eave edge to the truncation line (with the 照り exponent teri)."""
    def __init__(self, L, D, z_eave, o, truncate, rise, teri=1.35, **kw):
        c = D / 2 + o
        prof = lambda t: np.power(np.clip(np.asarray(t, float) * c / truncate, 0, 1.5), teri)
        kw.setdefault('kind', 'yosemune')
        super().__init__(L, D, z_eave, o, prof=prof, pitch=rise / c, truncate=truncate, **kw)
    def build(self, B):
        smax = lambda xs_, dc_: np.minimum(np.minimum(dc_, self.c), self.truncate)
        for k in range(4): self.face(B, k, smax=smax)
        for k in range(4):
            E = self.sides()[k][3]; self.eave(B, k, 0.0, E)
        if self.hip:
            for k in range(4):
                hl = self.hip_line(k, self.truncate * 0.97)
                self.ridge(B, hl[1:][::-1], self.ridge_w * 0.6, self.ridge_h * 0.55, ends=(None, 'oni' if self.ends else None))
        return dict(z_edge=self.zE0, z_top=float(self.z(self.truncate, self.c)))

def roof_of(L, D, z_eave, o, **kw):
    R = K.MRoof(L, D, z_eave, o, **kw)
    return R

# ------------------------------------------------------------------ white walls with posts and a tiled coping (方丈 garden walls, 塀)
def post_wall(B, S, pts, *, h=2.55, th=0.36, post=1.95, base=0.3, coping='kawara', eave=0.42, zfix=None, tag='main', block=True,
              rafters=True, color=WHITE, lower_board=0.0):
    """白壁 between dark square posts, a stone footing, a small tiled roof on top with an eave on both sides"""
    pts = [np.asarray(p, float) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; d = b - a; L = np.linalg.norm(d)
        if L < 0.3: continue
        d /= L; n = np.array([-d[1], d[0]])
        k = max(1, int(round(L / post)))
        for j in range(k):
            p = a + d * L * j / k; q = a + d * L * (j + 1) / k
            zz = zfix if zfix is not None else float(min(S.ground(*p), S.ground(*q)))
            zt = zz + h
            ll = L / k
            for side in (-1, 1):
                A = p + n * side * th / 2; Bq = q + n * side * th / 2
                quad(B, np.r_[A, zz - 0.3], np.r_[Bq, zz - 0.3], np.r_[Bq, zz + base], np.r_[A, zz + base], 'stone', out=np.r_[n * side, 0], tag=tag)
                z1 = zz + base
                if lower_board:
                    quad(B, np.r_[A, z1], np.r_[Bq, z1], np.r_[Bq, zz + lower_board], np.r_[A, zz + lower_board], 'wood_dark', out=np.r_[n * side, 0], tag=tag)
                    z1 = zz + lower_board
                B.add(np.array([np.r_[A, z1], np.r_[Bq, z1], np.r_[Bq, zt], np.r_[A, zt]]), [[0, 1, 2], [0, 2, 3]] if side < 0 else [[0, 2, 1], [0, 3, 2]],
                      'temple_wall', UV=np.array([[0, z1], [ll, z1], [ll, zt], [0, zt]]), tag=tag, c0=color)
            # the post at p (and q for the last)
            for pp in ([p, q] if j == k - 1 else [p]):
                prim.box(B, pp[0] - 0.13, pp[1] - 0.13, zz + base - 0.02, pp[0] + 0.13, pp[1] + 0.13, zt + 0.05, 'wood_dark', tag=tag)
            # beam under the coping, coping roof
            prim.obox(B, np.r_[p, zt + 0.08], np.r_[q, zt + 0.08], th + 0.08, 0.16, 'wood_dark', tag=tag)
            for side in (-1, 1):
                A = p + n * side * (th / 2 + eave); Bq = q + n * side * (th / 2 + eave)
                quad(B, np.r_[A, zt + 0.12], np.r_[Bq, zt + 0.12], np.r_[q, zt + 0.5], np.r_[p, zt + 0.5], coping, out=np.r_[n * side * 0.5, 1], tag=tag)
                quad(B, np.r_[A, zt + 0.06], np.r_[Bq, zt + 0.06], np.r_[q + n * side * th / 2, zt + 0.14], np.r_[p + n * side * th / 2, zt + 0.14], 'eave_wood', out=np.r_[0, 0, -1], tag=tag)
                prim.obox(B, np.r_[A, zt + 0.1], np.r_[Bq, zt + 0.1], 0.06, 0.1, coping, tag='detail')
                if rafters:
                    for t in np.arange(0.15, ll, 0.3):
                        c0 = p + d * t
                        prim.obox(B, np.r_[c0 + n * side * (th / 2 + eave - 0.03), zt + 0.05], np.r_[c0 + n * side * th / 2, zt + 0.12], 0.05, 0.05, 'wood_dark', tag='detail')
            prim.obox(B, np.r_[p - d * 0.02, zt + 0.56], np.r_[q + d * 0.02, zt + 0.56], 0.2, 0.14, 'ridge', tag=tag)
        if block:
            EK.ribbon(B, [a, b], max(0.6, th + 0.2), 'block')

# ------------------------------------------------------------------ 平唐門 (唐破風 on the gable ends: the roof section is cusped)
def karahafu_profile(halfw, hump, n=16):
    """section across the ridge: x in [-halfw, halfw] -> z rise: concave from the eaves, convex hump at the ridge"""
    xs = np.linspace(-halfw, halfw, n * 2 + 1)
    t = 1 - np.abs(xs) / halfw
    z = hump * (np.where(t < 0.55, 0.62 * (t / 0.55) ** 2, 0.62 + 0.38 * np.sin((t - 0.55) / 0.45 * math.pi / 2)))
    return xs, z

def hira_karamon(B, S, loc, *, zg=None, span=3.4, depth=2.4, H=3.4, r=0.2, W=7.4, Dr=4.8, hump=1.6, mat='wood_dark', cover='hiwada',
                 doors='closed', walk=True):
    """平唐門: four (or six) posts, a roof whose ridge runs along the gate (u) and whose section is a 唐破風 curve, so both
    gable ends show the cusped bargeboard; doors between the main posts"""
    cm = jroof.COVER_MAT.get(cover, cover)
    with loc.frame(B):
        if zg is None: zg = loc.g(S, 0, 0)
        prim.box(B, -span / 2 - 0.9, -depth / 2 - 0.7, zg - 0.3, span / 2 + 0.9, depth / 2 + 0.7, zg + 0.18, 'stone')
        z0 = zg + 0.18
        for sx in (-1, 1):
            for sv in (-1, 1):
                x, y = sx * span / 2, sv * depth / 2
                prim.box(B, x - r, y - r, z0, x + r, y + r, z0 + H, mat)
            # side tie beams
            prim.obox(B, (sx * span / 2, -depth / 2 - 0.3, z0 + H - 0.25), (sx * span / 2, depth / 2 + 0.3, z0 + H - 0.25), 0.2, 0.32, mat)
        for sv in (-1, 1):
            prim.obox(B, (-span / 2 - 0.6, sv * depth / 2, z0 + H - 0.2), (span / 2 + 0.6, sv * depth / 2, z0 + H - 0.2), 0.24, 0.4, mat)
            # 木鼻 ends white
            for sx in (-1, 1):
                prim.obox(B, (sx * (span / 2 + 0.55), sv * depth / 2, z0 + H - 0.2), (sx * (span / 2 + 0.62), sv * depth / 2, z0 + H - 0.2), 0.245, 0.405, 'white_paint', tag='detail')
        # brackets (出三斗) on the posts, 蟇股 between
        for sx in (-1, 1):
            for sv in (-1, 1):
                arch.kumimono(B, sx * span / 2, sv * depth / 2, z0 + H, (0, sv), (1, 0), 'demitsudo', 0.7, mat)
        zb = z0 + H + 0.62
        for sv in (-1, 1):
            prim.obox(B, (-W / 2 + 0.3, sv * depth / 2, zb), (W / 2 - 0.3, sv * depth / 2, zb), 0.2, 0.22, mat)
            masu(B, (0, sv * depth / 2, z0 + H + 0.05), 0.5, mat, tag='detail')
        # the roof: section along v is the karahafu curve, swept along u
        xs, zz = karahafu_profile(Dr / 2, hump)
        ze = zb + 0.15
        top = [(x, z + ze) for x, z in zip(xs, zz)]
        bot = [(x, z + ze - 0.22) for x, z in zip(xs, zz)]
        for (prof, m) in ((top, cm), (bot, 'eave_wood')):
            P = []; I = []; UV = []
            for u in (-W / 2, W / 2):
                for (x, z) in prof: P.append((u, x, z)); UV.append((u, x))
            n = len(prof)
            for i in range(n - 1): I += [[i, i + 1, n + i + 1], [i, n + i + 1, n + i]]
            P = np.array(P); I = np.array(I)
            fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
            want_up = m == cm
            if (fn[:, 2].sum() > 0) != want_up: I = I[:, ::-1]
            B.add(P, I, m, UV=np.array(UV), smooth=True)
        # gable boards (the cusped bargeboard + a gable wall under it)
        for su in (-1, 1):
            u = su * W / 2
            Pb = [(u, x, z - 0.02) for x, z in top] + [(u, x, z - 0.42) for x, z in top][::-1]
            Pb = np.array(Pb); nn = len(top)
            I = [[i, i + 1, 2 * nn - 2 - i] for i in range(nn - 1)] + [[i, 2 * nn - 2 - i, 2 * nn - 1 - i] for i in range(nn - 1)]
            oadd(B, Pb, I, mat, (su, 0, 0))
            # the gable wall (妻) under the roof at the wall line
            ug = su * (W / 2 - 0.9)
            G = [(ug, x, z - 0.3) for x, z in top if abs(x) <= depth / 2 + 0.3]
            G = [(ug, -depth / 2 - 0.3, zb)] + G + [(ug, depth / 2 + 0.3, zb)]
            G = np.array(G); I = [[0, i, i + 1] for i in range(1, len(G) - 1)]
            oadd(B, G, I, mat, (su, 0, 0))
            # 懸魚 at the apex
            za = ze + hump - 0.45
            prim.box(B, u - su * 0.05 - 0.04, -0.3, za - 0.5, u - su * 0.05 + 0.04, 0.3, za, 'gold' if cover == 'copper' else mat, tag='detail')
        # ridge: a low ridge with 鬼板 at the ends
        K.ridge_cap(B, np.array([(-W / 2 + 0.05, 0, ze + hump + 0.05), (W / 2 - 0.05, 0, ze + hump + 0.05)]), 0.4, 0.35, mat='ridge' if cover != 'copper' else 'copper', ends=('oni', 'oni'))
        # doors
        dh = H - 0.5
        if doors == 'closed':
            prim.box(B, -span / 2 + r, -0.06, z0, span / 2 - r, 0.06, z0 + dh, 'wood_dark')
            for x in np.linspace(-span / 2 + r + 0.2, span / 2 - r - 0.2, 5):
                prim.box(B, x - 0.04, -0.1, z0 + 0.2, x + 0.04, -0.06, z0 + dh - 0.2, 'metal_dark', tag='detail')
            EK.ribbon(B, [(-span / 2 - 0.4, 0), (span / 2 + 0.4, 0)], 0.6, 'block')
        else:
            for sx in (-1, 1):
                x = sx * (span / 2 - r - 0.05)
                prim.box(B, x - 0.05, 0.1, z0, x + 0.05, 0.1 + span / 2 - r, z0 + dh, 'wood_dark')
            if walk: EK.rect_walk(B, -span / 2 + r, -depth / 2 - 0.7, span / 2 - r, depth / 2 + 0.7, z0)
        for sx in (-1, 1):
            EK.ribbon(B, [(sx * span / 2, -depth / 2 - 0.3), (sx * span / 2, depth / 2 + 0.3)], 0.6, 'block')

# ------------------------------------------------------------------ ground with per-triangle surfaces
def ground_mesh(B, S, poly, res=1.0, surf_fn=None, zfn=None, tag='main', walk=True, walk_mask=None, offset=0.0):
    """the site's own ground over a shapely polygon: z = zfn(X, Y) (default S.ground), surfaces per triangle from
    surf_fn(cx, cy) -> SURF id array; adds a walk surface (except where walk_mask(cx, cy) is True)"""
    x0, y0, x1, y1 = poly.bounds
    xs = np.arange(x0 - res, x1 + res * 1.5, res); ys = np.arange(y0 - res, y1 + res * 1.5, res)
    X, Y = np.meshgrid(xs, ys)
    Z = (zfn(X, Y) if zfn else S.ground(X, Y)) + offset
    inside = shapely.contains_xy(poly.buffer(res * 0.75), X, Y)
    nx = len(xs)
    V = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    a = (np.arange(len(ys) - 1)[:, None] * nx + np.arange(nx - 1)[None, :]).ravel()
    ok = (inside[:-1, :-1] & inside[:-1, 1:] & inside[1:, :-1] & inside[1:, 1:]).ravel()
    a = a[ok]
    # split along the shorter diagonal-ish: alternate for a nicer look
    I = np.concatenate([np.stack([a, a + 1, a + nx + 1], 1), np.stack([a, a + nx + 1, a + nx], 1)])
    C = V[I].mean(1)
    sid = surf_fn(C[:, 0], C[:, 1]) if surf_fn else np.full(len(I), SID['forest'])
    for s_ in np.unique(sid):
        sel = sid == s_
        B.add(V, I[sel], 'ground', UV=V[:, :2], smooth=True, tag=tag, c1=(0, 0, 0, int(s_)))
    if walk:
        keep = np.ones(len(I), bool) if walk_mask is None else ~walk_mask(C[:, 0], C[:, 1])
        if keep.any(): B.add(V, I[keep], 'ground', smooth=True, tag='walk')
    return V, I

def lower_preview_terrain(S, ring, zmax, fn=None, shrink=0.2):
    """keep run_site's preview terrain under the modelled ground (like kiyomizu): inside the ring the DEM becomes
    min(DEM, zmax) or min(DEM, fn(x, y)) (fn: the own ground minus a margin)"""
    pg = Polygon(ring).buffer(-shrink) if not hasattr(ring, 'exterior') else ring.buffer(-shrink)
    x0, y0, x1, y1 = pg.bounds
    i0 = max(0, int((x0 - S.x0) / S.res)); i1 = min(S.H.shape[1] - 1, int((x1 - S.x0) / S.res) + 1)
    j0 = max(0, int((y0 - S.y0) / S.res)); j1 = min(S.H.shape[0] - 1, int((y1 - S.y0) / S.res) + 1)
    J, I = np.mgrid[j0:j1 + 1, i0:i1 + 1]
    ins = shapely.contains_xy(pg, S.x0 + I * S.res, S.y0 + J * S.res)
    sub = S.H[j0:j1 + 1, i0:i1 + 1]
    if fn is not None:
        X = (S.x0 + I * S.res)[ins]; Y = (S.y0 + J * S.res)[ins]
        zt = np.asarray(fn(X, Y), float)
        sub[ins] = np.minimum(sub[ins], zt)
    else:
        sub[ins] = np.minimum(sub[ins], zmax)

# ------------------------------------------------------------------ misc
def lamp_post(B, x, y, z, h=1.6):
    """a short stone lantern (石灯籠, lit)"""
    EK.lantern(B, x, y, z, h=h)

def pillar_base(B, x, y, z, r, h=0.25, mat='stone'):
    prim.cyl(B, (x, y, z - 0.25), (x, y, z + h), r * 1.6, r * 1.45, 8, mat)

def fill_dem(S, poly, margin=2.0, band=4.0):
    """the GSI DEM has bogus heights over some water bodies (思遠池: 53-55 m in a 48 m court): replace the cells
    inside poly.buffer(margin) by an inverse-distance blend of the cells in the band around it (modifies S.H)"""
    inner = poly.buffer(margin); outer = inner.buffer(band)
    x0, y0, x1, y1 = outer.bounds
    i0 = max(0, int((x0 - S.x0) / S.res)); i1 = min(S.H.shape[1] - 1, int((x1 - S.x0) / S.res) + 1)
    j0 = max(0, int((y0 - S.y0) / S.res)); j1 = min(S.H.shape[0] - 1, int((y1 - S.y0) / S.res) + 1)
    J, I = np.mgrid[j0:j1 + 1, i0:i1 + 1]
    X = S.x0 + I * S.res; Y = S.y0 + J * S.res
    ins = shapely.contains_xy(inner, X, Y)
    ring = shapely.contains_xy(outer, X, Y) & ~ins
    sub = S.H[j0:j1 + 1, i0:i1 + 1]
    rx, ry, rz = X[ring], Y[ring], sub[ring]
    qx, qy = X[ins], Y[ins]
    d2 = (qx[:, None] - rx[None, :]) ** 2 + (qy[:, None] - ry[None, :]) ** 2
    w = 1.0 / np.maximum(d2, 0.25) ** 1.5
    sub[ins] = (w * rz[None, :]).sum(1) / w.sum(1)
