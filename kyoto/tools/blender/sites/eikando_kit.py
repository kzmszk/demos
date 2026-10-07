"""永観堂 helpers (own module; the shared kit jk/* is not edited): building frames, halls with verandas, 向拝 and
curtains, gates (薬医門 / 四脚門, 向唐門), corridors (flat, stepped, curved: 渡り廊下, 臥龍廊), walls (築地塀 / 筋塀 /
土塀 with tile coping), retaining walls, steps that follow the terrain, stone bridges, lanterns, small shrines, the
pond basin and its water, walk / block ribbons."""
import math
import numpy as np
from jk import prim, arch, Frame
from jk import roof as jroof

ROOF_LIFT = 0.3          # arch.bracket_row returns the purlin top: the roof's plate line sits above it (rafters + covering)
CURTAIN = [(38, 140, 64), (230, 168, 28), (200, 36, 28), (236, 234, 226), (92, 52, 128)]     # 五色幕
WHITE = (238, 234, 224, 35)
OCHRE = (222, 196, 138, 35)

def nrm(v):
    v = np.asarray(v, float); l = np.linalg.norm(v)
    return v / l if l > 1e-12 else v

# ------------------------------------------------------------------ frames
class Loc:
    """a building frame: centre (cx, cy), yaw = direction of local +u (ccw from east); local v = u rotated +90°.
    Side 0 (front) is v-; build inside `with loc.frame(B):` with absolute z."""
    def __init__(self, cx, cy, yaw):
        self.cx, self.cy, self.yaw = float(cx), float(cy), float(yaw)
        self.c, self.s = math.cos(yaw), math.sin(yaw)
    def w(self, u, v):
        return (self.cx + self.c * u - self.s * v, self.cy + self.s * u + self.c * v)
    def l(self, x, y):
        dx, dy = x - self.cx, y - self.cy
        return (self.c * dx + self.s * dy, -self.s * dx + self.c * dy)
    def frame(self, B):
        return Frame(B, self.cx, self.cy, 0.0, self.yaw)
    def g(self, S, u, v):
        x, y = self.w(u, v); return float(S.ground(x, y))

def facing(front_deg):
    """yaw of a frame whose front (v-) faces the world direction front_deg (deg ccw from east)"""
    return math.radians(front_deg + 90.0)

# ------------------------------------------------------------------ walk / block helpers
def ribbon(B, pts, w, tag, z=None, mat='stone', off=0.0):
    """a horizontal ribbon along a 2D/3D polyline, width w, centre offset `off` to the right"""
    P = np.asarray(pts, float)
    if P.shape[1] == 2: P = np.c_[P, np.full(len(P), 0.0 if z is None else z)]
    V = []; I = []
    for i in range(len(P)):
        if i == 0: t = P[1, :2] - P[0, :2]
        elif i == len(P) - 1: t = P[-1, :2] - P[-2, :2]
        else: t = P[i + 1, :2] - P[i - 1, :2]
        t = nrm(t); n = np.array([t[1], -t[0]])
        a = P[i, :2] + n * (off - w / 2); b = P[i, :2] + n * (off + w / 2)
        V += [[a[0], a[1], P[i, 2]], [b[0], b[1], P[i, 2]]]
    for i in range(len(P) - 1):
        k = 2 * i
        I += [[k, k + 1, k + 3], [k, k + 3, k + 2]]
    V = np.array(V); I = np.array(I)
    fn = np.cross(V[I[:, 1]] - V[I[:, 0]], V[I[:, 2]] - V[I[:, 0]])
    if fn[:, 2].sum() < 0: I = I[:, ::-1]
    B.add(V, I, mat, tag=tag)

def quad(B, a, b, c, d, mat, tag='main', both=False, **kw):
    P = np.array([a, b, c, d], float)
    B.add(P, [[0, 1, 2], [0, 2, 3]], mat, tag=tag, **kw)
    if both: B.add(P, [[0, 2, 1], [0, 3, 2]], mat, tag=tag, **kw)

def rect_walk(B, x0, y0, x1, y1, z, tag='walk'):
    prim.polygon(B, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z, 'stone', tag=tag)

# ------------------------------------------------------------------ cloth: 五色幕
def curtains(B, p0, p1, z_top, h=1.2, panel=0.85, seed=0, z_top1=None, out=None, tag='detail'):
    """coloured temple curtains hanging along p0 -> p1 (2D, current frame) from z_top (z_top1 at p1 for slopes)"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d)
    if L < 0.3: return
    d /= L; n = np.array([d[1], -d[0]]) if out is None else nrm(out)
    z_top1 = z_top if z_top1 is None else z_top1
    k = max(1, int(round(L / panel))); w = L / k
    for i in range(k):
        ta, tb = i / k, (i + 1) / k
        a = p0 + d * L * ta; b = p0 + d * L * tb; m = (a + b) / 2 + n * 0.035
        za = z_top + (z_top1 - z_top) * ta; zb = z_top + (z_top1 - z_top) * tb; zm = (za + zb) / 2
        P = np.array([[a[0], a[1], za], [m[0], m[1], zm], [b[0], b[1], zb], [a[0], a[1], za - h], [m[0], m[1], zm - h - 0.04], [b[0], b[1], zb - h]])
        I = [[0, 3, 4], [0, 4, 1], [1, 4, 5], [1, 5, 2]]
        col = CURTAIN[(i + seed) % len(CURTAIN)] + (0,)
        B.add(P, I, 'cloth', tag=tag, c0=col)
        B.add(P, [t[::-1] for t in I], 'cloth', tag=tag, c0=col)

# ------------------------------------------------------------------ wall infills (in the current frame)
def _plane(B, a, b, za, zb, n, depth, mat, tag='main', **kw):
    A = np.r_[a - n * depth, za]; Bp = np.r_[b - n * depth, za]; C = np.r_[b - n * depth, zb]; D_ = np.r_[a - n * depth, zb]
    P = np.array([A, Bp, C, D_])
    fn = np.cross(P[1] - P[0], P[2] - P[0])
    I = [[0, 1, 2], [0, 2, 3]] if fn @ np.r_[n, 0] >= 0 else [[0, 2, 1], [0, 3, 2]]
    L = np.linalg.norm(b - a)
    B.add(P, I, mat, UV=np.array([[0, za], [L, za], [L, zb], [0, zb]]), tag=tag, **kw)

def infill(B, p0, p1, z0, z1, kind, out=None, mat='wood_dark', r=0.2, tag='main', seed=0):
    """bay infill: plaster, board, lattice (black square grid on shoji), shoji, maira (舞良戸), karado, katomado,
    renji, koshi, shitomi, open, glass"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L
    n = np.array([d[1], -d[0]]) if out is None else np.asarray(out, float)
    q0 = p0 + d * r; q1 = p1 - d * r; Lq = L - 2 * r
    if kind in ('plaster', 'board', 'katomado', 'renji', 'koshi', 'shitomi', 'karado', 'open', 'noren'):
        arch.infill(B, p0, p1, z0, z1, kind, out=n, mat=mat, tag=tag, seed=seed); return
    if kind == 'white':
        _plane(B, q0, q1, z0, z1, n, 0.06, 'temple_wall', tag=tag, c0=WHITE); return
    if kind == 'lattice':
        _plane(B, q0, q1, z0, z1, n, 0.12, 'white_paint', tag=tag)
        for zz in (z0 + 0.04, z1 - 0.04):
            prim.obox(B, np.r_[q0 - n * 0.06, zz], np.r_[q1 - n * 0.06, zz], 0.09, 0.08, mat, tag='detail')
        st = 0.17
        for x in np.arange(st / 2, Lq, st):
            a = q0 + d * x
            prim.obox(B, np.r_[a - n * 0.06, z0], np.r_[a - n * 0.06, z1], 0.04, 0.04, mat, tag='detail', ends=False)
        for zz in np.arange(z0 + st, z1 - 0.05, st):
            prim.obox(B, np.r_[q0 - n * 0.065, zz], np.r_[q1 - n * 0.065, zz], 0.04, 0.04, mat, tag='detail', ends=False)
        return
    if kind == 'shoji':
        _plane(B, q0, q1, z0, z1, n, 0.08, 'white_paint', tag=tag)
        for x in np.arange(0.0, Lq + 0.01, Lq / max(1, round(Lq / 0.9))):
            a = q0 + d * x
            prim.obox(B, np.r_[a - n * 0.06, z0], np.r_[a - n * 0.06, z1], 0.06, 0.04, 'wood_natural', tag='detail', ends=False)
        for zz in np.arange(z0 + 0.3, z1, 0.45):
            prim.obox(B, np.r_[q0 - n * 0.065, zz], np.r_[q1 - n * 0.065, zz], 0.03, 0.03, 'wood_natural', tag='detail', ends=False)
        prim.obox(B, np.r_[q0 - n * 0.06, z0 + 0.15], np.r_[q1 - n * 0.06, z0 + 0.15], 0.06, 0.3, 'wood_natural', tag='detail')
        return
    if kind == 'maira':
        _plane(B, q0, q1, z0, z1, n, 0.07, mat, tag=tag)
        for x in np.arange(0.0, Lq + 0.01, Lq / max(1, round(Lq / 0.9))):
            a = q0 + d * x
            prim.obox(B, np.r_[a - n * 0.05, z0], np.r_[a - n * 0.05, z1], 0.07, 0.04, mat, tag='detail', ends=False)
        for zz in np.arange(z0 + 0.2, z1, 0.22):
            prim.obox(B, np.r_[q0 - n * 0.055, zz], np.r_[q1 - n * 0.055, zz], 0.025, 0.025, mat, tag='detail', ends=False)
        return
    if kind == 'glass':
        _plane(B, q0, q1, z0, z1, n, 0.1, 'glass', tag=tag); return
    if kind == 'dark':
        _plane(B, q0, q1, z0, z1, n, 0.4, 'wood_dark', tag=tag)
        for sg in (0, 1):
            a = q0 if sg == 0 else q1
            _plane(B, a, a, z0, z1, n, 0.0, 'wood_dark', tag=tag)
        return
    raise ValueError(kind)

# ------------------------------------------------------------------ halls
def _ring_pieces(L, D, w, sides, gaps):
    """outer edge of a veranda ring (w wide around the L x D pillar rect) as pieces (2D polylines) minus gaps;
    gaps: list of (side, t0, t1) in the side's own coordinate (u for sides 0 / 2, v for 1 / 3)"""
    a, c = L / 2 + w, D / 2 + w
    edges = {0: ((-a, -c), (a, -c)), 1: ((a, -c), (a, c)), 2: ((a, c), (-a, c)), 3: ((-a, c), (-a, -c))}
    out = []
    for k in (0, 1, 2, 3):
        if k not in sides: continue
        p0, p1 = np.array(edges[k][0]), np.array(edges[k][1])
        if k == 0 and 3 not in sides: p0 = np.array([-L / 2, -c])
        if k == 0 and 1 not in sides: p1 = np.array([L / 2, -c])
        if k == 2 and 1 not in sides: p0 = np.array([L / 2, c])
        if k == 2 and 3 not in sides: p1 = np.array([-L / 2, c])
        if k == 1 and 0 not in sides: p0 = np.array([a, -D / 2])
        if k == 1 and 2 not in sides: p1 = np.array([a, D / 2])
        if k == 3 and 2 not in sides: p0 = np.array([-a, D / 2])
        if k == 3 and 0 not in sides: p1 = np.array([-a, -D / 2])
        ax = 0 if k in (0, 2) else 1
        segs = [(p0, p1)]
        for (sd, t0, t1) in gaps:
            if sd != k: continue
            nsegs = []
            for (q0, q1) in segs:
                lo, hi = min(q0[ax], q1[ax]), max(q0[ax], q1[ax])
                if t1 <= lo or t0 >= hi: nsegs.append((q0, q1)); continue
                inc = q1[ax] > q0[ax]
                a0 = q0.copy(); a1 = q1.copy()
                first = (q0, np.where(np.arange(2) == ax, t0 if inc else t1, q0))
                second = (np.where(np.arange(2) == ax, t1 if inc else t0, q0), q1)
                for (x0, x1) in (first, second):
                    if np.linalg.norm(x1 - x0) > 0.3: nsegs.append((x0, x1))
            segs = nsegs
        out += segs
    return out

def railing_run(B, a, b, z, h=0.78, mat='wood_dark', cap='metal_dark', giboshi=True, post_step=2.4):
    a = np.asarray(a, float); b = np.asarray(b, float)
    L = np.linalg.norm(b - a); k = max(1, int(round(L / post_step)))
    arch.railing(B, [a, b], z, h=h, mat=mat, cap_mat=cap, giboshi=giboshi)
    for i in range(1, k):
        p = a + (b - a) * i / k
        prim.cyl(B, np.r_[p, z], np.r_[p, z + h + 0.05], 0.06, 0.06, 8, mat, tag='detail')

def hall(B, S, loc, *, L, D, nu, nv, zf, H, r=0.24, pmat='wood_dark', bmat=None, walls=None, wall_mat=None,
         head=None, band='plaster', ver=1.2, ver_sides=(0, 1, 2, 3), ver_drop=0.05, rail=True, rail_mat='wood_dark',
         rail_cap='metal_dark', rail_gaps=(), skirt='plaster', bracket='hira', bs=1.0, bend='white_paint', roofkw=None,
         kohai=None, curtains_sides=(), curtain_h=1.3, curtain_seed=0, block_sides=(1, 2, 3), floor_mat='wood_natural',
         ver_mat='wood_natural', nageshi_mat=None, pillar_round=True, extra_stairs=(), hip_ends='oni'):
    """a temple hall on a raised floor; returns dict with heights and the roof object"""
    us, vs = arch.grid(L, D, nu, nv)
    bmat = bmat or pmat; wall_mat = wall_mat or pmat; nageshi_mat = nageshi_mat or pmat
    head = head if head is not None else zf + H * 0.72
    ztop = zf + H
    zv = zf - ver_drop
    walls = walls or {}
    res = {}
    gaps = list(rail_gaps)
    with loc.frame(B):
        # --- pillars (perimeter)
        pts = set()
        for x in us: pts.add((round(x, 4), round(vs[0], 4))); pts.add((round(x, 4), round(vs[-1], 4)))
        for y in vs: pts.add((round(us[0], 4), round(y, 4))); pts.add((round(us[-1], 4), round(y, 4)))
        for (x, y) in pts:
            zg = loc.g(S, x, y)
            zb = min(zg, zf - 0.35)
            prim.cyl(B, (x, y, zb - 0.05), (x, y, zb + 0.14), r * 1.55, r * 1.4, 10, 'stone')
            if pillar_round: prim.cyl(B, (x, y, zb + 0.1), (x, y, ztop), r, r * 0.97, 12, pmat, caps=(False, True))
            else: prim.box(B, x - r, y - r, zb + 0.1, x + r, y + r, ztop, pmat)
        # --- floor and under-floor skirt
        prim.polygon(B, [(-L / 2, -D / 2), (L / 2, -D / 2), (L / 2, D / 2), (-L / 2, D / 2)], zf, floor_mat)
        prim.polygon(B, [(-L / 2, -D / 2), (L / 2, -D / 2), (L / 2, D / 2), (-L / 2, D / 2)], zf, 'stone', tag='walk')
        sides_pts = {0: [(x, vs[0]) for x in us], 1: [(us[-1], y) for y in vs], 2: [(x, vs[-1]) for x in us[::-1]], 3: [(us[0], y) for y in vs[::-1]]}
        if skirt:
            for k in range(4):
                sp = sides_pts[k]
                for i in range(len(sp) - 1):
                    a = np.array(sp[i]); b = np.array(sp[i + 1]); dd = nrm(b - a); n = np.array([dd[1], -dd[0]])
                    zb = min(loc.g(S, *a), loc.g(S, *b)) - 0.3
                    if zf - 0.12 - zb < 0.15: continue
                    a2 = a + dd * r * 0.9; b2 = b - dd * r * 0.9
                    if skirt == 'plaster': _plane(B, a2, b2, zb, zf - 0.12, n, 0.02, 'temple_wall', c0=WHITE)
                    else: _plane(B, a2, b2, zb, zf - 0.12, n, 0.02, 'wood_dark')
        # --- walls
        for k in range(4):
            kinds = walls.get(k)
            if not kinds: continue
            sp = sides_pts[k]
            for i in range(len(sp) - 1):
                kd = kinds[i] if i < len(kinds) else kinds[-1]
                a = sp[i]; b = sp[i + 1]
                if kd != 'open': infill(B, a, b, zf + 0.04, head, kd, mat=wall_mat, r=r * 0.9, seed=i + 7 * k)
                if band and kd != 'none':
                    infill(B, a, b, head + 0.2, ztop - 0.32, band, mat=wall_mat, r=r * 0.9, seed=i)
        arch.nageshi(B, L, D, head + 0.2, nageshi_mat, h=0.22, w=0.11, out=r * 0.75)
        arch.nageshi(B, L, D, ztop, nageshi_mat, h=0.32, w=0.2, out=0.0)
        arch.nageshi(B, L, D, zf + 0.12, nageshi_mat, h=0.16, w=0.1, out=r * 0.75)
        # --- veranda
        if ver and ver_sides:
            a_, c_ = L / 2, D / 2; w = ver
            w1 = w if 1 in ver_sides else 0; w3 = w if 3 in ver_sides else 0
            rects = {0: (-a_ - w3, -c_ - w, a_ + w1, -c_), 2: (-a_ - w3, c_, a_ + w1, c_ + w), 1: (a_, -c_, a_ + w, c_), 3: (-a_ - w, -c_, -a_, c_)}
            for k in ver_sides:
                x0, y0, x1, y1 = rects[k]
                prim.box(B, x0, y0, zv - 0.11, x1, y1, zv, ver_mat)
                rect_walk(B, x0, y0, x1, y1, zv)
                # posts along the outer edge
                if k in (0, 2):
                    yy = y0 if k == 0 else y1; xs = np.linspace(x0 + 0.1, x1 - 0.1, max(2, int(round((x1 - x0) / 1.9)) + 1))
                    pp = [(x, yy + (0.08 if k == 0 else -0.08)) for x in xs]
                else:
                    xx = x1 if k == 1 else x0; ys = np.linspace(y0 + 0.1, y1 - 0.1, max(2, int(round((y1 - y0) / 1.9)) + 1))
                    pp = [(xx + (-0.08 if k == 1 else 0.08), y) for y in ys]
                for (px, py) in pp:
                    zg = loc.g(S, px, py)
                    if zv - 0.11 - zg > 0.12:
                        prim.box(B, px - 0.07, py - 0.07, zg - 0.1, px + 0.07, py + 0.07, zv - 0.11, 'wood_dark', tag='detail')
            res['zv'] = zv
        # --- brackets and roof
        rk = dict(kind='irimoya', cover='hongawara', o=2.6, pitch=0.7, rafter_mat=bmat, rafter_end=bend)
        rk.update(roofkw or {})
        o = rk.pop('o')
        top, reach = arch.bracket_row(B, L, D, ztop, bracket, bs, bmat, bend, us=us, vs=vs)
        R = jroof.Roof(L + 2 * reach, D + 2 * reach, top + ROOF_LIFT, o, **rk)
        zz = R.build(B)
        res.update(roof=R, top=top, reach=reach, ztop=ztop, head=head, **zz)
        # --- 向拝 (porch roof on the front)
        if kohai:
            kz = kohai_build(B, S, loc, R, L, D, us, vs, zf, zv, ver, head, ztop, r, pmat, bmat, bend, kohai)
            gaps.append((0, -kz['w'] / 2 + 0.1, kz['w'] / 2 - 0.1))
            res['kohai'] = kz
        for st in extra_stairs:
            side, t0, t1 = st['gap']
            gaps.append((side, t0, t1))
            stairs_build(B, S, loc, st, zv)
        # --- railing
        if rail and ver and ver_sides:
            for (a, b) in _ring_pieces(L, D, ver - 0.06, ver_sides, gaps):
                railing_run(B, a, b, zv, mat=rail_mat, cap=rail_cap)
                ribbon(B, [a, b], 0.55, 'block', z=zv, off=0.0)
        # --- curtains
        for k in curtains_sides:
            sp = sides_pts[k]
            a = np.array(sp[0]); b = np.array(sp[-1]); dd = nrm(b - a); n = np.array([dd[1], -dd[0]])
            curtains(B, a + n * (r + 0.12), b + n * (r + 0.12), ztop - 0.36, h=curtain_h, seed=curtain_seed + k)
        # --- blockers on closed walls
        for k in block_sides:
            sp = sides_pts[k]
            ribbon(B, [sp[0], sp[-1]], 0.5, 'block', z=zf)
    res['zf'] = zf
    return res

def stairs_build(B, S, loc, st, z_top):
    """wooden / stone stairs in the current frame: st = dict(p0=(u,v) ground end, p1=(u,v) top end, w, mat, z0=None)"""
    p0 = np.asarray(st['p0'], float); p1 = np.asarray(st['p1'], float)
    z0 = st.get('z0'); z0 = loc.g(S, *p0) if z0 is None else z0
    arch.stairs(B, p0, p1, z0, z_top, st['w'], st.get('mat', 'wood_natural'), riser=0.18)
    if st.get('cheek'):
        d = nrm(p1 - p0); n = np.array([-d[1], d[0]])
        for sgn in (-1, 1):
            q0 = p0 + n * sgn * (st['w'] / 2 + 0.06); q1 = p1 + n * sgn * (st['w'] / 2 + 0.06)
            prim.obox(B, np.r_[q0, z0 + 0.15], np.r_[q1, z_top + 0.1], 0.1, 0.32, st['cheek'])

def kohai_build(B, S, loc, R, L, D, us, vs, zf, zv, ver, head, ztop, r, pmat, bmat, bend, k):
    """向拝 over the central bays of the front: pillars on the ground, beam, brackets, a lean-to roof continuing the main
    roof's front slope, stairs up to the veranda"""
    n = k.get('n', 3); depth = k.get('depth', 3.2); ok = k.get('ok', 1.0); os_ = k.get('os', 0.8); sk = k.get('slope', 0.42)
    kmat = k.get('pmat', pmat); beam_mat = k.get('beam_mat', bmat); cover = jroof.COVER_MAT[k.get('cover', R.cover)]
    c0 = (len(us) - 1 - n) // 2
    kx = us[c0:c0 + n + 1]
    x_l, x_r = kx[0], kx[-1]; kw = x_r - x_l
    vk = -D / 2 - depth
    zE = float(R.zE(R.a))
    ext = (D / 2 + depth + ok) - R.c
    zkE = zE + 0.06 - sk * max(ext, 0.3)
    zkp = zkE - k.get('drop', 0.95)
    # pillars + bases
    for x in kx:
        zg = loc.g(S, x, vk)
        prim.cyl(B, (x, vk, zg - 0.05), (x, vk, zg + 0.22), r * 1.5, r * 1.35, 8, 'stone')
        prim.box(B, x - r * 0.8, vk - r * 0.8, zg + 0.18, x + r * 0.8, vk + r * 0.8, zkp, kmat)
    # 虹梁 + 木鼻, brackets
    prim.obox(B, (x_l - 0.45, vk, zkp - 0.25), (x_r + 0.45, vk, zkp - 0.25), 0.24, 0.5, beam_mat, **({'c0': k['beam_c0']} if 'beam_c0' in k else {}))
    for x in kx:
        arch.kumimono(B, x, vk, zkp, (0, -1), (1, 0), 'demitsudo', k.get('bs', 0.75), bmat, bend)
        # 海老虹梁 / 繋虹梁 to the main pillar
        prim.obox(B, (x, vk + 0.15, zkp - 0.35), (x, -D / 2 - 0.2, head + 0.55), 0.16, 0.3, beam_mat, tag='detail')
    prim.obox(B, (x_l - os_ * 0.6, vk, zkp + 0.45), (x_r + os_ * 0.6, vk, zkp + 0.45), 0.22, 0.22, bmat)        # 桁
    # roof surface: from the kohai eave up onto the main roof
    vE = vk - ok; ul, ur = x_l - os_, x_r + os_
    nv_ = 14; nu_ = max(4, int((ur - ul) / 0.6))
    vv = np.linspace(vE, -R.c + 0.7, nv_ + 1)
    def zs(v):
        if v <= -R.c: return zE + 0.06 - sk * (-R.c - v) - 0.03 * (-R.c - v) ** 2
        return float(R.z(v + R.c, R.a)) + 0.06
    P = []; UV = []
    for j, v in enumerate(vv):
        for i, u in enumerate(np.linspace(ul, ur, nu_ + 1)):
            P.append((u, v, zs(v))); UV.append((u, v))
    P = np.array(P); I = []
    for j in range(nv_):
        for i in range(nu_):
            a_ = j * (nu_ + 1) + i
            I += [[a_, a_ + 1, a_ + nu_ + 2], [a_, a_ + nu_ + 2, a_ + nu_ + 1]]
    I = np.array(I)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    if fn[:, 2].sum() < 0: I = I[:, ::-1]
    B.add(P, I, cover, UV=np.array(UV), smooth=True)
    # soffit + rafters, edge, bargeboards
    sof = P.copy(); sof[:, 2] -= 0.28
    B.add(sof, I[:, ::-1], 'eave_wood', UV=np.array(UV), smooth=True)
    zedge = zs(vE)
    for (z_a, z_b, m) in ((zedge, zedge - 0.14, cover), (zedge - 0.14, zedge - 0.34, bmat)):
        quad(B, (ul, vE, z_b), (ur, vE, z_b), (ur, vE, z_a), (ul, vE, z_a), m)
    if R.cover == 'hongawara':
        for u in np.arange(ul + 0.15, ur, 0.3):
            prim.cyl(B, (u, vE + 0.25, zedge - 0.02), (u, vE - 0.02, zedge - 0.06), 0.085, None, 8, cover, caps=(False, True), tag='detail')
    for u in np.arange(ul + 0.15, ur, 0.32):
        v1 = -D / 2 - 0.2
        prim.obox(B, (u, vE + 0.05, zs(vE) - 0.4), (u, v1, zs(v1) - 0.4 if v1 <= -R.c else zE - 0.3), 0.08, 0.1, bmat, tag='detail')
        prim.obox(B, (u, vE - 0.01, zs(vE) - 0.4), (u, vE + 0.02, zs(vE) - 0.4), 0.085, 0.102, bend, tag='detail')
    vb = np.linspace(vE, -R.c - 0.1, 8)
    for u in (ul, ur):
        pts = np.array([(u, v, zs(v) - 0.05) for v in vb])
        prim.sweep(B, pts, [(-0.06, -0.38), (0.06, -0.38), (0.06, -0.02), (-0.06, -0.02)], bmat, up=(1, 0, 0))
    # stairs up to the veranda + walk
    zg = loc.g(S, 0.0, vk + 0.3)
    nst = max(1, int(math.ceil((zv - zg) / 0.18))); run = nst * 0.28
    v_top = -D / 2 - ver
    stairs_build(B, S, loc, dict(p0=(0.0, v_top - run), p1=(0.0, v_top), w=kw - 0.5, mat=k.get('stair_mat', 'wood_natural'), z0=zg, cheek='wood_dark'), zv)
    rect_walk(B, x_l, vk - 0.6, x_r, v_top - run, zg + 0.05)
    if k.get('curtains', True):
        curtains(B, (x_l, vk - 0.22), (x_r, vk - 0.22), zkp - 0.45, h=1.05, seed=2)
    return dict(w=kw, vk=vk, zkE=zkE, zkp=zkp)

def pent(B, u0, u1, v_wall, z_top, depth, drop, *, post_u=(), zg=None, cover='copper', mat='wood_dark', tag='main'):
    """庇: a lean-to roof along a front wall (current frame, wall at v = v_wall, roof running out toward v-)"""
    vE = v_wall - depth; zE = z_top - drop
    cm = jroof.COVER_MAT[cover]
    quad(B, (u0 - 0.3, vE, zE), (u1 + 0.3, vE, zE), (u1 + 0.3, v_wall, z_top), (u0 - 0.3, v_wall, z_top), cm, tag=tag)
    quad(B, (u0 - 0.3, v_wall, z_top - 0.18), (u1 + 0.3, v_wall, z_top - 0.18), (u1 + 0.3, vE, zE - 0.18), (u0 - 0.3, vE, zE - 0.18), 'eave_wood', tag=tag)
    quad(B, (u0 - 0.3, vE, zE - 0.22), (u1 + 0.3, vE, zE - 0.22), (u1 + 0.3, vE, zE + 0.02), (u0 - 0.3, vE, zE + 0.02), mat, tag=tag)
    for su, u in ((-1, u0 - 0.3), (1, u1 + 0.3)):
        P = np.array([(u, vE, zE + 0.02), (u, v_wall, z_top + 0.02), (u, v_wall, z_top - 0.2), (u, vE, zE - 0.22)])
        I = [[0, 1, 2], [0, 2, 3]] if su < 0 else [[0, 2, 1], [0, 3, 2]]
        B.add(P, I, mat, tag=tag)
    for u in np.arange(u0 - 0.15, u1 + 0.3, 0.3):
        prim.obox(B, (u, vE + 0.02, zE - 0.28), (u, v_wall, z_top - 0.28), 0.07, 0.08, mat, tag='detail')
    prim.obox(B, (u0 - 0.3, vE + 0.35, zE - 0.4), (u1 + 0.3, vE + 0.35, zE - 0.4), 0.16, 0.2, mat)
    if zg is not None:
        for u in post_u:
            prim.box(B, u - 0.11, vE + 0.24, zg - 0.1, u + 0.11, vE + 0.46, zE - 0.4, mat)

# ------------------------------------------------------------------ gates
def gate(B, S, loc, *, zg=None, span=5.0, depth=2.4, H=4.2, r=0.28, mat='wood_dark', roof_L=8.8, roof_D=5.4, pitch=0.78,
         cover='hongawara', z_eave=None, back_r=None, doors='open', bend='white_paint', kabuki_h=0.5, side_door=None,
         gable_wall='wood_dark', ridge_end='oni', walk=True, steps=None):
    """薬医門 / 四脚門 in its frame: main pillars on v = 0 (front line), back pillars on v = +depth; kirizuma roof
    centred over the pillars, ridge along u.  Doors (open, swung inward) between the main pillars."""
    with loc.frame(B):
        if zg is None: zg = loc.g(S, 0, depth / 2)
        back_r = back_r or r * 0.72
        ze = z_eave if z_eave is not None else zg + H + 0.75
        for sx in (-1, 1):
            x = sx * span / 2
            for (v, rr) in ((0.0, r), (depth, back_r)):
                zgg = loc.g(S, x, v)
                prim.box(B, x - rr * 1.45, v - rr * 1.45, min(zgg, zg) - 0.2, x + rr * 1.45, v + rr * 1.45, zg + 0.12, 'stone')
                prim.box(B, x - rr, v - rr, zg + 0.1, x + rr, v + rr, zg + H + 0.2, mat)
                # 根巻 metal at the foot of the main pillars
                if v == 0.0: prim.box(B, x - rr - 0.02, v - rr - 0.02, zg + 0.1, x + rr + 0.02, v + rr + 0.02, zg + 0.42, 'metal_dark', tag='detail')
            # 貫 between main and back pillar
            prim.obox(B, (x, -0.2, zg + H * 0.45), (x, depth + 0.2, zg + H * 0.45), 0.12, 0.26, mat)
        # the roof first (its underside places the arms and purlins)
        Lw = span + 2 * r + 0.3
        vo = max(0.3, (roof_L - Lw) / 2)
        o = (roof_D - depth) / 2
        R = jroof.Roof(Lw, depth, ze, o, kind='kirizuma', cover=cover, pitch=pitch, verge=vo, rafter=0.28, rafter_mat=mat,
                       rafter_end=bend, gable_wall=gable_wall, ends=ridge_end, sori=0.0)
        under = lambda s_: float(R.z(s_, R.a)) - R.edge - 0.12          # underside of the covering at inward distance s_
        with Frame(B, 0, depth / 2, 0, 0):
            zz = R.build(B)
        # 冠木 (head beam) across the main pillars, 虹梁 at the back
        prim.obox(B, (-span / 2 - 0.55, 0, zg + H - kabuki_h / 2), (span / 2 + 0.55, 0, zg + H - kabuki_h / 2), r * 1.1, kabuki_h, mat)
        prim.obox(B, (-span / 2 - 0.2, depth, zg + H - 0.3), (span / 2 + 0.2, depth, zg + H - 0.3), back_r * 1.1, 0.4, mat)
        # 腕木 (arms) along v on each pillar line, white-painted ends; 出桁 on the arm ends; 棟木 + 束
        s_p = 0.55                                       # purlin: inward from the eave edge
        zp = under(s_p) - 0.12
        zw = under(o) - 0.14                              # at the pillar line
        for sx in (-1, 1):
            x = sx * span / 2
            for (v0, v1, sv) in ((-o + s_p - 0.25, 0.0, -1), (depth + o - s_p + 0.25, depth, 1)):
                prim.obox(B, (x, v0, zp - 0.2), (x, v1, zw - 0.2), 0.2, 0.26, mat)
                prim.obox(B, (x, v0, zp - 0.2), (x, v0 - sv * 0.03, zp - 0.2), 0.205, 0.265, bend, tag='detail')
            prim.obox(B, (x, 0.0, zw - 0.45), (x, depth, zw - 0.45), 0.18, 0.3, mat)
        for v in (-o + s_p, depth + o - s_p):
            prim.obox(B, (-roof_L / 2 + 0.7, v, zp), (roof_L / 2 - 0.7, v, zp), 0.2, 0.2, mat)
        zr_ = under(R.c) - 0.15
        prim.obox(B, (-roof_L / 2 + 0.6, depth / 2, zr_), (roof_L / 2 - 0.6, depth / 2, zr_), 0.22, 0.24, mat)
        for sx in (-1, 1):
            prim.obox(B, (sx * span / 2, depth / 2, zg + H - 0.1), (sx * span / 2, depth / 2, zr_), 0.18, 0.18, mat)
        prim.obox(B, (-span / 2, depth / 2, zg + H - 0.05), (span / 2, depth / 2, zg + H - 0.05), 0.2, 0.24, mat)
        # doors
        if doors:
            dh = H - kabuki_h - 0.05; dw = span / 2 - r - 0.02
            for sx in (-1, 1):
                x = sx * (span / 2 - r - 0.06)
                if doors == 'open':
                    prim.box(B, x - 0.05, 0.25, zg + 0.08, x + 0.05, 0.25 + dw, zg + dh, 'wood_dark')
                    for zz_ in np.linspace(zg + 0.5, zg + dh - 0.3, 4):
                        prim.box(B, x - sx * 0.05 - 0.04, 0.3, zz_ - 0.05, x - sx * 0.05 + 0.04, 0.2 + dw, zz_ + 0.05, 'metal_dark', tag='detail')
                else:
                    x0 = sx * (span / 2 - r); x1 = 0.0
                    prim.box(B, min(x0, x1), 0.0, zg + 0.08, max(x0, x1), 0.1, zg + dh, 'wood_dark')
        if walk:
            rect_walk(B, -span / 2 + r, -roof_D / 2 + depth / 2, span / 2 - r, roof_D / 2 + depth / 2, zg + 0.04)
        for sx in (-1, 1):
            ribbon(B, [(sx * span / 2, -0.3), (sx * span / 2, depth + 0.3)], 0.7, 'block')
    return zz

def side_wall_door(B, x0, x1, zg, h, mat='wood_dark'):
    prim.box(B, x0, -0.05, zg, x1, 0.05, zg + h, mat)

# ------------------------------------------------------------------ 向唐門
def karamon(B, S, loc, *, zg=None, span=2.7, depth=2.0, H=3.35, r=0.17, W=4.6, Dr=4.3, hump=1.25, mat='black_lacquer',
            trim='vermilion', cover='hiwada', doors=True, base=True, back=True, block=True):
    """向唐門 (or, with doors / back False, a 唐破風 entrance porch whose back side is v+)"""
    with loc.frame(B):
        if zg is None: zg = loc.g(S, 0, 0)
        if base:
            prim.box(B, -span / 2 - 1.2, -depth / 2 - 1.3, zg - 0.4, span / 2 + 1.2, depth / 2 + 1.3, zg + 0.14, 'stone')
            rect_walk(B, -span / 2 - 1.2, -depth / 2 - 1.3, span / 2 + 1.2, depth / 2 + 1.3, zg + 0.14)
        z0 = zg + 0.14
        for sx in (-1, 1):
            for sv in ((-1, 1) if back else (-1,)):
                x, v = sx * span / 2, sv * depth / 2
                prim.box(B, x - r * 1.5, v - r * 1.5, z0 - 0.02, x + r * 1.5, v + r * 1.5, z0 + 0.12, 'stone')
                prim.box(B, x - r, v - r, z0 + 0.1, x + r, v + r, z0 + H, mat)
                prim.box(B, x - r - 0.02, v - r - 0.02, z0 + 0.1, x + r + 0.02, v + r + 0.02, z0 + 0.3, 'metal_dark', tag='detail')
                arch.kumimono(B, x, v, z0 + H, (0, sv), (1, 0), 'demitsudo', 0.62, mat, 'white_paint')
            # 門柱 (door posts) and tie beams
            if doors: prim.box(B, sx * (span / 2) - r * 0.8, -r * 0.8, z0, sx * (span / 2) + r * 0.8, r * 0.8, z0 + H - 0.5, mat)
            prim.obox(B, (sx * span / 2, -depth / 2, z0 + H - 0.75), (sx * span / 2, depth / 2, z0 + H - 0.75), 0.14, 0.28, mat)
        for sv in ((-1, 1) if back else (-1,)):
            # 虹梁 front / back with a vermilion edge line
            prim.obox(B, (-span / 2 - 0.35, sv * depth / 2, z0 + H - 0.28), (span / 2 + 0.35, sv * depth / 2, z0 + H - 0.28), 0.2, 0.44, mat)
            prim.obox(B, (-span / 2 + 0.2, sv * (depth / 2 + 0.105), z0 + H - 0.47), (span / 2 - 0.2, sv * (depth / 2 + 0.105), z0 + H - 0.47), 0.02, 0.03, trim, tag='detail')
        # doors (closed) with lattice upper panels
        dw = span / 2 - r * 0.8
        for sx in ((-1, 1) if doors else ()):
            x0, x1 = sorted((0.0, sx * dw))
            prim.box(B, x0 + 0.01, -0.06, z0 + 0.05, x1 - 0.01, 0.06, z0 + H - 0.55, mat)
            prim.box(B, x0 + 0.12, -0.07, z0 + H - 1.6, x1 - 0.12, -0.065, z0 + H - 0.75, 'wood_natural', tag='detail')
            for xx in np.linspace(x0 + 0.16, x1 - 0.16, 7):
                prim.box(B, xx - 0.018, -0.1, z0 + H - 1.6, xx + 0.018, -0.07, z0 + H - 0.75, mat, tag='detail')
            for zz in np.linspace(z0 + H - 1.58, z0 + H - 0.77, 9):
                prim.box(B, x0 + 0.12, -0.1, zz - 0.018, x1 - 0.12, -0.07, zz + 0.018, mat, tag='detail')
            for zz in np.linspace(z0 + 0.45, z0 + H - 1.7, 4):
                prim.box(B, x0 + 0.05, -0.1, zz - 0.04, x1 - 0.05, -0.06, zz + 0.04, mat, tag='detail')
        # roof: the karahafu profile swept along v
        zc = z0 + H + 0.62
        def zf_(u):
            t = min(abs(u) / (W / 2), 1.0)
            return zc + hump * (0.5 + 0.5 * math.cos(math.pi * t)) + 0.16 * max(0.0, (t - 0.8) / 0.2) ** 2
        us_ = np.linspace(-W / 2, W / 2, 33)
        vs_ = np.linspace(-Dr / 2, Dr / 2, 9)
        P = np.array([(u, v, zf_(u)) for v in vs_ for u in us_]); nu_ = len(us_) - 1
        I = []
        for j in range(len(vs_) - 1):
            for i in range(nu_):
                a_ = j * (nu_ + 1) + i
                I += [[a_, a_ + nu_ + 2, a_ + 1], [a_, a_ + nu_ + 1, a_ + nu_ + 2]]
        I = np.array(I)
        fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
        if fn[:, 2].sum() < 0: I = I[:, ::-1]
        B.add(P, I, jroof.COVER_MAT[cover], UV=P[:, [0, 1]], smooth=True)
        S2 = P.copy(); S2[:, 2] -= 0.38
        B.add(S2, I[:, ::-1], 'eave_wood', UV=P[:, [0, 1]], smooth=True)
        # thick bark edge (koba) at front / back, bargeboards (破風) with a vermilion line, side fascia
        for sv in ((-1, 1) if back else (-1,)):
            v = sv * Dr / 2
            top = np.array([(u, v, zf_(u)) for u in us_]); mid = top - [0, 0, 0.2]; bot = top - [0, 0, 0.38]
            for (A_, B_, m) in ((top, mid, jroof.COVER_MAT[cover]), (mid, bot, mat)):
                Pq = np.concatenate([A_, B_]); Iq = []
                for i in range(nu_): Iq += [[i, i + nu_ + 1, i + 1], [i + 1, i + nu_ + 1, i + nu_ + 2]]
                Iq = np.array(Iq)
                fn = np.cross(Pq[Iq[:, 1]] - Pq[Iq[:, 0]], Pq[Iq[:, 2]] - Pq[Iq[:, 0]])
                if (fn[:, 1].sum() * sv) < 0: Iq = Iq[:, ::-1]
                B.add(Pq, Iq, m)
            pts = np.array([(u, v - sv * 0.12, zf_(u) - 0.42) for u in us_])
            prim.sweep(B, pts, [(-0.07, -0.42), (0.07, -0.42), (0.07, 0.0), (-0.07, 0.0)], mat, up=(0, 1, 0))
            pts2 = np.array([(u, v + sv * 0.0, zf_(u) - 0.45) for u in us_])
            prim.sweep(B, pts2, [(-0.075, -0.04), (0.075, -0.04), (0.075, 0.0), (-0.075, 0.0)], trim, up=(0, 1, 0), tag='detail')
            # 兎の毛通し (carved pendant) under the hump
            gp = [(-0.55, 0.0), (0.55, 0.0), (0.35, -0.42), (0.0, -0.62), (-0.35, -0.42)]
            Pg = np.array([(x, v - sv * 0.1, zc + hump - 0.45 + z) for (x, z) in gp])
            Ig = [[0, 1, 2], [0, 2, 3], [0, 3, 4]]
            B.add(Pg, Ig, mat, tag='detail'); B.add(Pg, [t[::-1] for t in Ig], mat, tag='detail')
            prim.cyl(B, (0, v - sv * 0.08, zc + hump - 0.75), (0, v - sv * 0.16, zc + hump - 0.75), 0.11, 0.11, 10, 'gold', tag='detail')
        for su in (-1, 1):
            u = su * W / 2
            pts = np.array([(u, v, zf_(u) - 0.08) for v in vs_])
            prim.sweep(B, pts, [(-0.05, -0.3), (0.05, -0.3), (0.05, 0.0), (-0.05, 0.0)], mat, up=(1, 0, 0))
        # rafters under the side eaves
        for v in np.arange(-Dr / 2 + 0.2, Dr / 2 - 0.1, 0.24):
            for su in (-1, 1):
                prim.obox(B, (su * (W / 2 - 0.05), v, zf_(W / 2) - 0.45), (su * (span / 2 + 0.1), v, zf_(span / 2 + 0.1) - 0.5), 0.06, 0.08, mat, tag='detail')
        # box ridge (箱棟) with 鬼板 and a crest
        zt = zf_(0.0)
        prim.box(B, -0.22, -Dr / 2 + 0.25, zt - 0.1, 0.22, Dr / 2 - 0.25, zt + 0.42, 'ridge')
        prim.box(B, -0.26, -Dr / 2 + 0.25, zt + 0.42, 0.26, Dr / 2 - 0.25, zt + 0.52, 'ridge')
        for sv in (-1, 1):
            v = sv * (Dr / 2 - 0.25)
            P2 = np.array([(-0.36, v, zt - 0.1), (0.36, v, zt - 0.1), (0.36, v, zt + 0.45), (0.2, v, zt + 0.78), (-0.2, v, zt + 0.78), (-0.36, v, zt + 0.45)])
            I2 = [[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5]]
            if sv > 0: I2 = [t[::-1] for t in I2]
            B.add(P2, I2, 'ridge', c1=(0, 1, 0, 0))
            for (x, z) in ((-0.3, 0.6), (0.0, 0.84), (0.3, 0.6)):
                prim.cyl(B, (x, v - sv * 0.02, zt + z), (x, v + sv * 0.08, zt + z), 0.09, 0.09, 10, 'ridge', tag='detail')
        if block:
            ribbon(B, [(-span / 2, -depth / 2 - 0.5), (-span / 2, depth / 2 + 0.5)], 0.6, 'block')
            ribbon(B, [(span / 2, -depth / 2 - 0.5), (span / 2, depth / 2 + 0.5)], 0.6, 'block')
            if doors: ribbon(B, [(-span / 2, 0), (span / 2, 0)], 0.6, 'block')

# ------------------------------------------------------------------ walls
def wall(B, S, pts, *, h=2.3, th=0.5, color=WHITE, stripes=0, lower=None, base_h=0.35, coping='kawara', ridge=True,
         step=1.8, posts=0, tag='main', block=True, zfix=None):
    """築地塀 / 土塀 along a world polyline: stone base, plaster (tinted), optional lower boards, white stripes (筋塀),
    tiled coping; follows the terrain in short steps"""
    pts = [np.asarray(p, float) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; d = b - a; L = np.linalg.norm(d)
        if L < 0.2: continue
        d /= L; n = np.array([-d[1], d[0]])
        k = max(1, int(round(L / step)))
        for j in range(k):
            p = a + d * L * j / k; q = a + d * L * (j + 1) / k
            zz = zfix if zfix is not None else float(min(S.ground(*p), S.ground(*q)))
            ztop = zz + h
            for side in (-1, 1):
                A = p + n * side * th / 2; Bq = q + n * side * th / 2
                I = [[0, 1, 2], [0, 2, 3]] if side < 0 else [[0, 2, 1], [0, 3, 2]]          # outward
                ll = L / k
                Pz = np.array([np.r_[A, zz - 0.4], np.r_[Bq, zz - 0.4], np.r_[Bq, zz + base_h], np.r_[A, zz + base_h]])
                B.add(Pz, I, 'stone', UV=np.array([[0, 0], [ll, 0], [ll, base_h], [0, base_h]]), tag=tag)
                zl = zz + base_h
                if lower:
                    Pl = np.array([np.r_[A, zl], np.r_[Bq, zl], np.r_[Bq, zz + lower], np.r_[A, zz + lower]])
                    B.add(Pl, I, 'wood_dark', UV=np.array([[0, 0], [ll, 0], [ll, lower], [0, lower]]), tag=tag)
                    zl = zz + lower
                Pw = np.array([np.r_[A, zl], np.r_[Bq, zl], np.r_[Bq, ztop], np.r_[A, ztop]])
                B.add(Pw, I, 'temple_wall', UV=np.array([[0, zl], [ll, zl], [ll, ztop], [0, ztop]]), tag=tag, c0=color)
                for s_ in range(stripes):
                    zs = ztop - 0.25 - 0.17 * s_
                    prim.obox(B, np.r_[p + n * side * (th / 2 + 0.006), zs], np.r_[q + n * side * (th / 2 + 0.006), zs], 0.012, 0.045, 'white_paint', tag='detail')
            # ends (caps) every segment would be hidden; cap the first / last
            for side in (-1, 1):
                A = p + n * side * (th / 2 + 0.28); Bq = q + n * side * (th / 2 + 0.28)
                P = np.array([np.r_[A, ztop - 0.02], np.r_[Bq, ztop - 0.02], np.r_[q, ztop + 0.36], np.r_[p, ztop + 0.36]])
                I = [[0, 1, 2], [0, 2, 3]] if side < 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I, coping, UV=np.array([[0, 0], [L / k, 0], [L / k, 0.5], [0, 0.5]]), tag=tag)
                prim.obox(B, np.r_[A, ztop - 0.02], np.r_[Bq, ztop - 0.02], 0.05, 0.12, coping, tag='detail')
            prim.obox(B, np.r_[p - d * 0.02, ztop + 0.42], np.r_[q + d * 0.02, ztop + 0.42], 0.24, 0.16, 'ridge', tag=tag)
        for e, pe in ((0, a), (1, b)):
            if (e == 0 and i > 0) or (e == 1 and i < len(pts) - 2): continue
            zz = zfix if zfix is not None else float(S.ground(*pe))
            sgn = -1 if e == 0 else 1
            A = pe + n * th / 2; Bq = pe - n * th / 2
            P = np.array([np.r_[A, zz - 0.4], np.r_[Bq, zz - 0.4], np.r_[Bq, zz + h], np.r_[A, zz + h]])
            I = [[0, 1, 2], [0, 2, 3]]
            fn = np.cross(P[1] - P[0], P[2] - P[0])
            if fn[:2] @ (d * sgn) < 0: I = [[0, 2, 1], [0, 3, 2]]
            B.add(P, I, 'temple_wall', tag=tag, c0=color)
        if block:
            ribbon(B, [a, b], max(0.6, th + 0.1), 'block')

def retaining(B, S, pts, *, up=1, batter=0.25, z_top=None, z_bot=None, drop=None, coping=True, tag='main'):
    """石垣: a battered stone face along a world polyline; `up` = +1 if the upper terrace is on the left of travel"""
    P = [np.asarray(p, float) for p in pts]
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]; d = b - a; L = np.linalg.norm(d)
        if L < 0.2: continue
        d /= L; nl = np.array([-d[1], d[0]]) * up      # toward the upper side
        k = max(1, int(L / 1.0))
        V = []
        for j in range(k + 1):
            p = a + d * L * j / k
            zt = z_top if z_top is not None else float(S.ground(*(p + nl * 0.8)))
            zb = z_bot if z_bot is not None else (zt - drop if drop is not None else float(S.ground(*(p - nl * 1.2))))
            hgt = max(0.3, zt - zb)
            pb = p - nl * batter * hgt
            V += [np.r_[p, zt], np.r_[pb, zb - 0.3]]
        V = np.array(V); I = []
        for j in range(k):
            q = 2 * j
            I += [[q, q + 1, q + 3], [q, q + 3, q + 2]]
        I = np.array(I)
        fn = np.cross(V[I[:, 1]] - V[I[:, 0]], V[I[:, 2]] - V[I[:, 0]])
        if (fn[:, :2] @ (-nl)).sum() < 0: I = I[:, ::-1]
        B.add(V, I, 'stone', tag=tag, c1=(0, 3, 0, 0))
        if coping:
            T = V[0::2]
            prim.sweep(B, T + [0, 0, 0.0], [(-0.3, -0.05), (0.3, -0.05), (0.3, 0.12), (-0.3, 0.12)], 'curb', tag='detail')
        ribbon(B, [a, b], 0.6, 'block')

# ------------------------------------------------------------------ steps that follow the terrain
def terrain_steps(B, S, pts, w, *, rise=0.165, mat='stone', rail='center', curb=True, z0=None, z1=None, tag='main'):
    """stone steps along a world polyline: a riser wherever the profile climbs `rise` (from the DEM, or linear z0 -> z1)"""
    P = np.asarray(pts, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]; Lt = s[-1]
    ts = np.arange(0, Lt + 0.01, 0.05)
    X = np.interp(ts, s, P[:, 0]); Y = np.interp(ts, s, P[:, 1])
    if z0 is not None:
        Z = z0 + (z1 - z0) * ts / Lt
    else:
        Z = S.ground(X, Y)
        Z = np.maximum.accumulate(Z) if Z[-1] >= Z[0] else np.minimum.accumulate(Z)
    up = Z[-1] >= Z[0]
    zc = Z[0]; t_last = 0.0; treads = []
    for i in range(1, len(ts)):
        if (Z[i] - zc >= rise) if up else (zc - Z[i] >= rise):
            treads.append((t_last, ts[i], zc)); zc = zc + (rise if up else -rise); t_last = ts[i]
    treads.append((t_last, Lt, zc))
    def at(t):
        x = np.interp(t, s, P[:, 0]); y = np.interp(t, s, P[:, 1])
        i = min(max(np.searchsorted(s, t) - 1, 0), len(P) - 2)
        dd = nrm(P[i + 1] - P[i]); return np.array([x, y]), dd
    zprev = None
    for (ta, tb, z) in treads:
        pa, da = at(ta); pb, db = at(tb)
        na = np.array([-da[1], da[0]]); nb = np.array([-db[1], db[0]])
        V = np.array([np.r_[pa - na * w / 2, z], np.r_[pa + na * w / 2, z], np.r_[pb + nb * w / 2, z], np.r_[pb - nb * w / 2, z]])
        I = [[0, 2, 1], [0, 3, 2]] if np.cross(V[1] - V[0], V[2] - V[0])[2] < 0 else [[0, 1, 2], [0, 2, 3]]
        B.add(V, I, mat, tag=tag)
        if zprev is not None and abs(z - zprev) > 0.01:
            lo, hi = min(z, zprev), max(z, zprev)
            R_ = np.array([np.r_[pa - na * w / 2, lo - 0.05], np.r_[pa + na * w / 2, lo - 0.05], np.r_[pa + na * w / 2, hi], np.r_[pa - na * w / 2, hi]])
            face = -da if z > zprev else da
            I2 = [[0, 1, 2], [0, 2, 3]]
            if np.cross(R_[1] - R_[0], R_[2] - R_[0])[:2] @ face < 0: I2 = [[0, 2, 1], [0, 3, 2]]
            B.add(R_, I2, mat, tag=tag)
        # sides down to the ground
        for sg in (-1, 1):
            qa = pa + na * sg * w / 2; qb = pb + nb * sg * w / 2
            zga = min(float(S.ground(*qa)), z) - 0.25; zgb = min(float(S.ground(*qb)), z) - 0.25
            V3 = np.array([np.r_[qa, zga], np.r_[qb, zgb], np.r_[qb, z], np.r_[qa, z]])
            I3 = [[0, 1, 2], [0, 2, 3]]
            if np.cross(V3[1] - V3[0], V3[2] - V3[0])[:2] @ (na * sg) < 0: I3 = [[0, 2, 1], [0, 3, 2]]
            B.add(V3, I3, mat, tag=tag)
        zprev = z
    # walk ramp
    W = np.c_[X[::4], Y[::4], np.interp(ts[::4], [t[0] for t in treads] + [Lt], [t[2] for t in treads] + [treads[-1][2]])]
    ribbon(B, W, w, 'walk')
    if curb:
        for sg in (-1, 1):
            C = []
            for (ta, tb, z) in treads:
                for t in (ta, tb):
                    p, dd = at(t); n = np.array([-dd[1], dd[0]])
                    C.append(np.r_[p + n * sg * (w / 2 + 0.15), z + 0.12])
            C = np.array(C)
            keep = np.r_[True, np.linalg.norm(np.diff(C, axis=0), axis=1) > 0.02]
            C = C[keep]
            if len(C) > 1: prim.sweep(B, C, [(-0.15, -0.3), (0.15, -0.3), (0.15, 0.0), (-0.15, 0.0)], 'curb', tag='detail')
    if rail == 'center':
        R = []
        for t in np.arange(0, Lt + 0.01, max(0.5, Lt / 40)):
            p, dd = at(t)
            zt = [tr[2] for tr in treads if tr[0] <= t <= tr[1] + 1e-6]
            R.append(np.r_[p, (zt[-1] if zt else treads[-1][2]) + 0.85])
        R = np.array(R)
        if len(R) > 1:
            prim.sweep(B, R, [(-0.025, -0.025), (0.025, -0.025), (0.025, 0.025), (-0.025, 0.025)], 'metal_dark', tag='detail')
            for i in range(0, len(R), 3):
                prim.cyl(B, R[i] - [0, 0, 0.85], R[i], 0.02, 0.02, 6, 'metal_dark', tag='detail')
    return treads

# ------------------------------------------------------------------ corridors
def corridor(B, S, pts, zs, *, w=2.4, bay=2.1, h=2.5, rise=0.85, o=0.7, cover='kawara', mat='wood_dark',
             floor_mat='wood_natural', rail=True, rail_h=0.72, skirt=True, curtains_on=False, step=0.18,
             end_gables=(True, True), passages=(), rail_gaps=(), smooth=1.5, roof_steps=False, block=True, tag='main',
             tile_ends=True, seed=0):
    """a roofed corridor along a world polyline; zs = floor heights at the points (stairs inside where it climbs)"""
    P = np.asarray(pts, float); zs = np.asarray(zs, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]; Lt = s[-1]
    def pos(t): return np.array([np.interp(t, s, P[:, 0]), np.interp(t, s, P[:, 1])])
    def tan(t):
        e = 0.6
        return nrm(pos(min(t + e, Lt)) - pos(max(t - e, 0)))
    zfl = lambda t: float(np.interp(t, s, zs))
    # quantised floor (treads)
    tt = np.arange(0, Lt + 1e-6, 0.05)
    zq = []; z_cur = zfl(0.0)
    for t in tt:
        z = zfl(t)
        while z - z_cur >= step * 0.999: z_cur += step
        while z_cur - z >= step * 0.999: z_cur -= step
        zq.append(z_cur)
    zq = np.array(zq)
    def zqf(t): return float(zq[min(int(round(t / 0.05)), len(zq) - 1)])
    # smooth floor for the roof / beams
    ker = max(1, int(smooth / 0.05))
    zp = np.pad(np.array([zfl(t) for t in tt]), ker, mode='edge')
    zsm = np.convolve(zp, np.ones(2 * ker + 1) / (2 * ker + 1), mode='same')[ker:-ker]
    def zr(t): return float(np.interp(t, tt, zsm)) + h
    # treads
    edges = [0] + [i for i in range(1, len(tt)) if zq[i] != zq[i - 1]] + [len(tt) - 1]
    prev = None
    for k in range(len(edges) - 1):
        i0, i1 = edges[k], edges[k + 1]
        ta, tb = tt[i0], tt[i1]; z = zq[i0]
        samp = [ta] + [x for x in s if ta < x < tb] + [tb]
        L_ = []; R_ = []
        for t in samp:
            p = pos(t); d = tan(t); n = np.array([-d[1], d[0]])
            L_.append(np.r_[p + n * w / 2, z]); R_.append(np.r_[p - n * w / 2, z])
        V = np.array(L_ + R_); m = len(samp); I = []
        for j in range(m - 1): I += [[j, m + j, m + j + 1], [j, m + j + 1, j + 1]]
        I = np.array(I)
        if np.cross(V[I[0, 1]] - V[I[0, 0]], V[I[0, 2]] - V[I[0, 0]])[2] < 0: I = I[:, ::-1]
        B.add(V, I, floor_mat, tag=tag)
        for side in (L_, R_):
            Q = np.array(side); D_ = Q - [0, 0, 0.22]
            V2 = np.concatenate([Q, D_]); I2 = []
            for j in range(m - 1): I2 += [[j, j + 1, m + j + 1], [j, m + j + 1, m + j]]
            B.add(V2, I2, mat, tag=tag); B.add(V2, [t[::-1] for t in I2], mat, tag=tag)
        if prev is not None and abs(prev - z) > 0.01:
            p = pos(ta); d = tan(ta); n = np.array([-d[1], d[0]])
            lo, hi = min(prev, z), max(prev, z)
            Rr = np.array([np.r_[p + n * w / 2, lo - 0.2], np.r_[p - n * w / 2, lo - 0.2], np.r_[p - n * w / 2, hi], np.r_[p + n * w / 2, hi]])
            B.add(Rr, [[0, 1, 2], [0, 2, 3]], floor_mat, tag=tag); B.add(Rr, [[0, 2, 1], [0, 3, 2]], floor_mat, tag=tag)
        prev = z
    # walk (smooth ramp)
    wt = np.arange(0, Lt + 1e-6, 0.5)
    if wt[-1] < Lt: wt = np.r_[wt, Lt]
    ribbon(B, np.array([np.r_[pos(t), zfl(t)] for t in wt]), w - 0.25, 'walk')
    # stations
    ns = max(1, int(round(Lt / bay))); st = np.linspace(0, Lt, ns + 1)
    in_pass = lambda t: any(a <= t <= b for (a, b) in passages)
    for t in st:
        p = pos(t); d = tan(t); n = np.array([-d[1], d[0]])
        for sg in (-1, 1):
            q = p + n * sg * w / 2
            zg = float(S.ground(*q))
            zb = min(zg - 0.05, zqf(t) - 0.2)
            prim.obox(B, np.r_[q, zb], np.r_[q, zr(t)], 0.15, 0.15, mat, up=(1, 0, 0), tag=tag)
            if zqf(t) - zg > 0.4:
                prim.cyl(B, np.r_[q, zg - 0.1], np.r_[q, zg + 0.12], 0.17, 0.15, 6, 'stone', tag='detail')
        prim.obox(B, np.r_[p + n * w / 2, zr(t) - 0.12], np.r_[p - n * w / 2, zr(t) - 0.12], 0.14, 0.24, mat, tag=tag)
        prim.obox(B, np.r_[p, zr(t)], np.r_[p, zr(t) + rise * 0.6], 0.12, 0.12, mat, tag='detail')
    # side beams + ridge purlin
    fine = np.arange(0, Lt + 1e-6, 0.4)
    if fine[-1] < Lt: fine = np.r_[fine, Lt]
    for sg in (-1, 1):
        Q = np.array([np.r_[pos(t) + np.array([-tan(t)[1], tan(t)[0]]) * sg * w / 2, zr(t) - 0.1] for t in fine])
        prim.sweep(B, Q, [(-0.09, -0.12), (0.09, -0.12), (0.09, 0.12), (-0.09, 0.12)], mat, tag=tag)
    # roof
    E = w / 2 + o; ye = -rise * o / (w / 2)
    prof = []
    for x in np.linspace(-E, E, 9):
        tx = 1 - abs(x) / E
        y = ye + (rise - ye) * (tx ** 1.25)
        prof.append((x, y))
    C = np.array([np.r_[pos(t), zr(t)] for t in fine])
    prim.sweep(B, C, prof[::-1], jroof.COVER_MAT.get(cover, cover), closed=False, tag=tag, smooth=True)        # right -> left: faces up
    prim.sweep(B, C, [(x, y - 0.16) for (x, y) in prof], 'eave_wood', closed=False, tag=tag, smooth=True)
    prim.sweep(B, C + [0, 0, rise], [(-0.18, -0.12), (0.18, -0.12), (0.18, 0.2), (0.11, 0.26), (-0.11, 0.26), (-0.18, 0.2)], 'ridge', tag=tag, caps=True)
    for sg in (-1, 1):
        Q = []
        for t in fine:
            n = np.array([-tan(t)[1], tan(t)[0]])
            Q.append(np.r_[pos(t) + n * sg * E, zr(t) + ye])
        Q = np.array(Q)
        prim.sweep(B, Q, [(-0.05, -0.2), (0.05, -0.2), (0.05, 0.03), (-0.05, 0.03)], mat, tag=tag)
        if tile_ends and cover in ('hongawara', 'kawara', 'sangawara'):
            for t in np.arange(0.15, Lt, 0.3):
                p = pos(t); d = tan(t); n = np.array([-d[1], d[0]])
                q = np.r_[p + n * sg * E, zr(t) + ye]
                prim.cyl(B, q - np.r_[n * sg * 0.2, -0.0], q + np.r_[n * sg * 0.02, -0.04], 0.07, None, 6, jroof.COVER_MAT.get(cover, cover), caps=(False, True), tag='detail')
        for t in np.arange(0.2, Lt, 0.36):
            p = pos(t); d = tan(t); n = np.array([-d[1], d[0]])
            a_ = np.r_[p + n * sg * (E - 0.05), zr(t) + ye - 0.2]; b_ = np.r_[p + n * sg * (w / 2 - 0.1), zr(t) - 0.16]
            prim.obox(B, a_, b_, 0.07, 0.08, mat, tag='detail')
    # end gables
    for e, flag in ((0, end_gables[0]), (1, end_gables[1])):
        if not flag: continue
        t = 0.0 if e == 0 else Lt
        p = pos(t); d = tan(t); n = np.array([-d[1], d[0]])
        zz = zr(t)
        G = np.array([np.r_[p + n * w / 2, zz], np.r_[p - n * w / 2, zz], np.r_[p, zz + rise - 0.05]])
        B.add(G, [[0, 1, 2]], 'wood_dark', tag=tag); B.add(G, [[0, 2, 1]], 'wood_dark', tag=tag)
        for sg in (-1, 1):
            Bq = np.array([np.r_[p + n * sg * E, zz + ye - 0.02], np.r_[p, zz + rise - 0.02]])
            prim.obox(B, Bq[0], Bq[1], 0.08, 0.3, mat, up=tuple(np.r_[n * sg * 0.3, 1.0]), tag='detail')
    # railings, skirts, curtains
    for sg in (-1, 1):
        if rail:
            pieces = [(0.0, Lt)]
            for (sd, a, b) in rail_gaps:
                if sd != sg: continue
                np_ = []
                for (x0, x1) in pieces:
                    if b <= x0 or a >= x1: np_.append((x0, x1)); continue
                    if a - x0 > 0.3: np_.append((x0, a))
                    if x1 - b > 0.3: np_.append((b, x1))
                pieces = np_
            for (x0, x1) in pieces:
                rt = np.arange(x0, x1 + 1e-6, 0.4)
                if rt[-1] < x1: rt = np.r_[rt, x1]
                for (dz, wd, hh) in ((rail_h, 0.1, 0.08), (rail_h * 0.45, 0.06, 0.06), (0.05, 0.1, 0.1)):
                    Q = np.array([np.r_[pos(t) + np.array([-tan(t)[1], tan(t)[0]]) * sg * (w / 2 - 0.02), (zfl(t) if dz > 0.06 else zqf(t)) + dz] for t in rt])
                    prim.sweep(B, Q, [(-wd / 2, -hh / 2), (wd / 2, -hh / 2), (wd / 2, hh / 2), (-wd / 2, hh / 2)], mat, tag='detail')
                for t in np.arange(x0 + 0.3, x1, 0.55):
                    q = pos(t) + np.array([-tan(t)[1], tan(t)[0]]) * sg * (w / 2 - 0.02)
                    prim.obox(B, np.r_[q, zfl(t) + 0.06], np.r_[q, zfl(t) + rail_h * 0.45], 0.05, 0.05, mat, tag='detail', ends=False)
                if block:
                    ribbon(B, np.array([np.r_[pos(t), 0] for t in rt]), 0.5, 'block', off=-sg * (w / 2 + 0.12))
        if skirt:
            for k in range(len(st) - 1):
                ta, tb = st[k], st[k + 1]
                if in_pass((ta + tb) / 2): continue
                n_a = np.array([-tan(ta)[1], tan(ta)[0]]); n_b = np.array([-tan(tb)[1], tan(tb)[0]])
                qa = pos(ta) + n_a * sg * w / 2; qb = pos(tb) + n_b * sg * w / 2
                za = zqf(ta) - 0.22; zb_ = zqf(tb) - 0.22
                ga = float(S.ground(*qa)) - 0.2; gb = float(S.ground(*qb)) - 0.2
                if min(za - ga, zb_ - gb) < 0.2: continue
                V = np.array([np.r_[qa, ga], np.r_[qb, gb], np.r_[qb, zb_], np.r_[qa, za]])
                B.add(V, [[0, 1, 2], [0, 2, 3]], 'wood_dark', tag=tag); B.add(V, [[0, 2, 1], [0, 3, 2]], 'wood_dark', tag=tag)
        if curtains_on:
            for k in range(len(st) - 1):
                ta, tb = st[k], st[k + 1]
                n_a = np.array([-tan(ta)[1], tan(ta)[0]]); n_b = np.array([-tan(tb)[1], tan(tb)[0]])
                qa = pos(ta) + n_a * sg * (w / 2 + 0.1); qb = pos(tb) + n_b * sg * (w / 2 + 0.1)
                curtains(B, qa, qb, zr(ta) - 0.3, h=0.95, z_top1=zr(tb) - 0.3, seed=k + seed, out=np.r_[n_a * sg])
    return dict(Lt=Lt, zr=zr, pos=pos, tan=tan, zfl=zfl)

# ------------------------------------------------------------------ bridges
def stone_bridge(B, S, p0, p1, z0, z1, *, w=2.0, arch_h=0.55, piers=(0.25, 0.5, 0.75), z_water=None, post_step=1.4,
                 mat='stone', rail_mat='curb'):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]])
    nt = max(8, int(L / 0.4))
    ts = np.linspace(0, 1, nt + 1)
    zc = lambda t: z0 + (z1 - z0) * t + arch_h * 4 * t * (1 - t)
    th = 0.32
    top_l = np.array([np.r_[p0 + d * L * t + n * w / 2, zc(t)] for t in ts]); top_r = np.array([np.r_[p0 + d * L * t - n * w / 2, zc(t)] for t in ts])
    m = len(ts)
    for (A_, B_) in ((top_r, top_l),):
        V = np.concatenate([A_, B_]); I = []
        for j in range(m - 1): I += [[j, j + 1, m + j + 1], [j, m + j + 1, m + j]]
        I = np.array(I)
        if np.cross(V[I[0, 1]] - V[I[0, 0]], V[I[0, 2]] - V[I[0, 0]])[2] < 0: I = I[:, ::-1]
        B.add(V, I, mat)
        Vb = V - [0, 0, th]; B.add(Vb, I[:, ::-1], mat)
    for side in (top_l, top_r):
        V = np.concatenate([side, side - [0, 0, th]]); I = []
        for j in range(m - 1): I += [[j, j + 1, m + j + 1], [j, m + j + 1, m + j]]
        B.add(V, I, mat); B.add(V, [t[::-1] for t in I], mat)
    ribbon(B, np.array([np.r_[p0 + d * L * t, zc(t)] for t in ts]), w - 0.2, 'walk')
    # parapets: posts and two rails
    npst = max(2, int(round(L / post_step)) + 1)
    for sg in (-1, 1):
        R1 = []; R2 = []
        for t in np.linspace(0, 1, npst):
            q = p0 + d * L * t + n * sg * (w / 2 - 0.1)
            prim.box(B, q[0] - 0.09, q[1] - 0.09, zc(t) - 0.05, q[0] + 0.09, q[1] + 0.09, zc(t) + 0.78, rail_mat)
            R1.append(np.r_[q, zc(t) + 0.66]); R2.append(np.r_[q, zc(t) + 0.28])
        fine = np.linspace(0, 1, nt + 1)
        R1 = np.array([np.r_[p0 + d * L * t + n * sg * (w / 2 - 0.1), zc(t) + 0.66] for t in fine])
        R2 = np.array([np.r_[p0 + d * L * t + n * sg * (w / 2 - 0.1), zc(t) + 0.3] for t in fine])
        prim.sweep(B, R1, [(-0.08, -0.07), (0.08, -0.07), (0.08, 0.07), (-0.08, 0.07)], rail_mat, caps=True)
        prim.sweep(B, R2, [(-0.06, -0.06), (0.06, -0.06), (0.06, 0.06), (-0.06, 0.06)], rail_mat, caps=True, tag='detail')
        ribbon(B, np.array([np.r_[p0 + d * L * t, 0] for t in fine]), 0.5, 'block', off=-sg * (w / 2 + 0.1))
    zw = z_water if z_water is not None else min(z0, z1) - 0.5
    for t in piers:
        q = p0 + d * L * t
        zt = zc(t) - th
        for sg in (-1, 1):
            c = q + n * sg * (w / 2 - 0.3)
            prim.box(B, c[0] - 0.16, c[1] - 0.16, zw - 0.8, c[0] + 0.16, c[1] + 0.16, zt, mat)
        prim.obox(B, np.r_[q + n * (w / 2), zt - 0.12], np.r_[q - n * (w / 2), zt - 0.12], 0.28, 0.24, mat)

def slab_bridge(B, S, p0, p1, z, *, w=1.6, mat='stone'):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = nrm(p1 - p0); n = np.array([-d[1], d[0]])
    V = np.array([np.r_[p0 - n * w / 2, z], np.r_[p1 - n * w / 2, z], np.r_[p1 + n * w / 2, z], np.r_[p0 + n * w / 2, z]])
    prim.prism(B, V[:, :2] if np.cross(V[1] - V[0], V[2] - V[0])[2] > 0 else V[::-1, :2], z - 0.3, z, mat)
    ribbon(B, np.array([np.r_[p0, z], np.r_[p1, z]]), w, 'walk')

# ------------------------------------------------------------------ lanterns, shrines
def lantern(B, x, y, z, h=2.1, kind='kasuga', lamp=True):
    arch.ishidoro(B, x, y, z, h=h, lamp=lamp)
    if lamp: B.lamp(x, y, z + h * 0.65, 4.0, (1.0, 0.62, 0.32))
    ribbon(B, [(x - 0.3, y), (x + 0.3, y)], 0.6, 'block')

def yukimi(B, x, y, z, h=1.4):
    """雪見灯籠: low, wide umbrella roof on three legs"""
    s = h / 1.4
    for k in range(3):
        a = 2 * math.pi * k / 3
        prim.cyl(B, (x + 0.35 * s * math.cos(a), y + 0.35 * s * math.sin(a), z), (x + 0.22 * s * math.cos(a), y + 0.22 * s * math.sin(a), z + 0.55 * s), 0.06 * s, 0.05 * s, 6, 'stone')
    prim.cyl(B, (x, y, z + 0.55 * s), (x, y, z + 0.65 * s), 0.32 * s, 0.32 * s, 6, 'stone')
    prim.cyl(B, (x, y, z + 0.65 * s), (x, y, z + 0.92 * s), 0.2 * s, 0.2 * s, 6, 'stone')
    prim.lathe(B, (x, y, z + 0.92 * s), [(0.62 * s, 0.0), (0.6 * s, 0.06 * s), (0.3 * s, 0.22 * s), (0.08 * s, 0.32 * s), (0.1 * s, 0.4 * s), (0.0, 0.48 * s)], 6, 'stone', smooth=False)

def small_shrine(B, S, loc, zg, *, w=1.5, d=1.4, h=1.6, color='vermilion', cover='copper', base=0.5, front_ext=0.9):
    """a small 流造 shrine: stone base, painted body, gable roof extended over the front"""
    with loc.frame(B):
        prim.box(B, -w / 2 - 0.5, -d / 2 - 0.6, zg - 0.3, w / 2 + 0.5, d / 2 + 0.45, zg + base, 'stone')
        z0 = zg + base
        for sx in (-1, 1):
            for sv in (-1, 1):
                prim.box(B, sx * w / 2 - 0.07, sv * d / 2 - 0.07, z0, sx * w / 2 + 0.07, sv * d / 2 + 0.07, z0 + h, color)
            prim.box(B, sx * w / 2 - 0.06, -d / 2 - front_ext - 0.06, z0, sx * w / 2 + 0.06, -d / 2 - front_ext + 0.06, z0 + h - 0.15, color)
        prim.box(B, -w / 2 + 0.05, -d / 2 + 0.04, z0, w / 2 - 0.05, d / 2 - 0.04, z0 + h - 0.1, 'wood_dark')
        prim.box(B, -w / 2 + 0.15, -d / 2 - 0.0, z0 + 0.2, w / 2 - 0.15, -d / 2 + 0.05, z0 + h - 0.3, 'gold', tag='detail')
        prim.box(B, -w / 2 - 0.25, -d / 2 - front_ext - 0.1, z0, w / 2 + 0.25, d / 2 + 0.2, z0 + 0.12, 'wood_natural')
        with Frame(B, 0, -front_ext / 2, 0, 0):
            jroof.roof(B, w + 0.2, d + front_ext, z0 + h, 0.45, kind='kirizuma', cover=cover, pitch=0.62, verge=0.35, rafter=0.18,
                       rafter_mat=color, rafter_end='white_paint', gable_wall='wood_dark', ends=None, sori=0.0, edge=0.16)
        ribbon(B, [(-w / 2 - 0.5, 0), (w / 2 + 0.5, 0)], d + 1.0, 'block')

def bell_tower(B, S, loc, zg, *, L=3.6, D=3.0, H=4.2, base=1.3):
    with loc.frame(B):
        prim.box(B, -L / 2 - 1.0, -D / 2 - 1.0, zg - 0.4, L / 2 + 1.0, D / 2 + 1.0, zg + base, 'stone')
        z0 = zg + base
        rect_walk(B, -L / 2 - 1.0, -D / 2 - 1.0, L / 2 + 1.0, D / 2 + 1.0, z0)
        for sx in (-1, 1):
            for sv in (-1, 1):
                prim.cyl(B, (sx * (L / 2 + 0.15), sv * (D / 2 + 0.15), z0), (sx * L / 2, sv * D / 2, z0 + H), 0.2, 0.18, 10, 'wood_dark')
                prim.cyl(B, (sx * (L / 2 + 0.15), sv * (D / 2 + 0.15), z0 - 0.02), (sx * (L / 2 + 0.15), sv * (D / 2 + 0.15), z0 + 0.15), 0.3, 0.28, 8, 'stone')
        for zz in (z0 + 0.5, z0 + H * 0.62):
            arch.ring_beam(B, L + 0.2, D + 0.2, zz, 0.12, 0.2, 'wood_dark')
        arch.ring_beam(B, L, D, z0 + H, 0.2, 0.3, 'wood_dark')
        top, reach = arch.bracket_row(B, L, D, z0 + H, 'demitsudo', 0.7, 'wood_dark', 'white_paint')
        jroof.roof(B, L + 2 * reach, D + 2 * reach, top + ROOF_LIFT, 1.5, kind='irimoya', cover='hongawara', pitch=0.75, rafter_mat='wood_dark', rafter_end='white_paint')
        # the bell + beam
        prim.obox(B, (-L / 2, 0, z0 + H - 0.3), (L / 2, 0, z0 + H - 0.3), 0.2, 0.3, 'wood_dark')
        zb = z0 + H - 0.45
        prim.lathe(B, (0, 0, zb - 1.55), [(0.62, 0.0), (0.6, 0.08), (0.55, 0.4), (0.52, 1.2), (0.42, 1.42), (0.15, 1.5), (0.0, 1.52)], 16, 'bronze')
        prim.obox(B, (-1.2, 0.0, zb - 1.0), (-0.65, 0.0, zb - 1.0), 0.16, 0.16, 'wood_natural', tag='detail')

# ------------------------------------------------------------------ 多宝塔
def sorin(B, x, y, z, *, Hs=4.6, s=1.0, chains_to=None):
    """相輪: 露盤, 伏鉢, 請花, 九輪, 水煙, 竜車, 宝珠; chains from the 九輪 to the roof corners"""
    prim.box(B, x - 0.42 * s, y - 0.42 * s, z - 0.1, x + 0.42 * s, y + 0.42 * s, z + 0.32 * s, 'bronze')
    prim.lathe(B, (x, y, z + 0.32 * s), [(0.36 * s, 0.0), (0.38 * s, 0.12 * s), (0.3 * s, 0.32 * s), (0.12 * s, 0.4 * s)], 12, 'bronze')
    prim.lathe(B, (x, y, z + 0.72 * s), [(0.1 * s, 0.0), (0.3 * s, 0.1 * s), (0.34 * s, 0.2 * s), (0.08 * s, 0.22 * s)], 12, 'bronze')
    zr0 = z + 0.94 * s; zr1 = z + Hs * 0.72
    prim.cyl(B, (x, y, z + 0.3 * s), (x, y, z + Hs - 0.2), 0.07 * s, 0.05 * s, 8, 'bronze')
    for k in range(9):
        zz = zr0 + (zr1 - zr0) * k / 8.6
        prim.lathe(B, (x, y, zz), [(0.08 * s, 0.0), (0.26 * s, 0.02 * s), (0.27 * s, 0.07 * s), (0.08 * s, 0.09 * s)], 12, 'bronze', tag='detail')
    zw = zr1 + 0.15 * s
    for k in range(4):                          # 水煙: four flame panels
        a = math.pi * k / 4
        c, sn = math.cos(a), math.sin(a)
        P = np.array([(x - 0.3 * s * c, y - 0.3 * s * sn, zw), (x + 0.3 * s * c, y + 0.3 * s * sn, zw), (x + 0.22 * s * c, y + 0.22 * s * sn, zw + 0.75 * s), (x, y, zw + 0.95 * s), (x - 0.22 * s * c, y - 0.22 * s * sn, zw + 0.75 * s)])
        I = [[0, 1, 2], [0, 2, 3], [0, 3, 4]]
        B.add(P, I, 'bronze', tag='detail'); B.add(P, [t[::-1] for t in I], 'bronze', tag='detail')
    prim.lathe(B, (x, y, zw + 1.0 * s), [(0.05 * s, 0.0), (0.16 * s, 0.05 * s), (0.16 * s, 0.12 * s), (0.05 * s, 0.17 * s), (0.11 * s, 0.25 * s), (0.12 * s, 0.33 * s), (0.06 * s, 0.42 * s), (0.0, 0.46 * s)], 10, 'bronze')
    if chains_to:
        top = np.array([x, y, zr1 - 0.1])
        for c in chains_to:
            c = np.asarray(c, float)
            pts = [top + (c - top) * t + np.array([0, 0, -0.35 * 4 * t * (1 - t)]) for t in np.linspace(0, 1, 7)]
            for i in range(len(pts) - 1):
                prim.cyl(B, pts[i], pts[i + 1], 0.022, 0.022, 4, 'metal_dark', caps=(False, False), tag='detail')
            prim.lathe(B, c - [0, 0, 0.45], [(0.0, 0.0), (0.09, 0.05), (0.1, 0.25), (0.05, 0.32), (0.0, 0.35)], 8, 'bronze', tag='detail')

def ring_railing(B, cx, cy, z, R, h=0.6, n=24, mat='wood_dark'):
    pts = [(cx + R * math.cos(2 * math.pi * k / n), cy + R * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
    for zz, wd in ((z + h, 0.07), (z + h * 0.45, 0.05), (z + 0.04, 0.08)):
        Q = np.array([np.r_[p, zz] for p in pts])
        prim.sweep(B, Q, [(-wd / 2, -wd / 2), (wd / 2, -wd / 2), (wd / 2, wd / 2), (-wd / 2, wd / 2)], mat, tag='detail')
    for p in pts[:-1:2]:
        prim.cyl(B, np.r_[p, z], np.r_[p, z + h + 0.04], 0.04, 0.04, 6, mat, tag='detail')

def tahoto(B, S, loc, zp, *, L=4.2, H1=2.85, r=0.17, o1=1.1, o2=1.25, L2=3.0, s1=0.75, s2=0.55, cover='hiwada'):
    """多宝塔 on a platform whose top is zp (floor), front = v-"""
    out = {}
    with loc.frame(B):
        Pl = L / 2 + 1.7
        zgs = [loc.g(S, sx * Pl, sv * Pl) for sx in (-1, 1) for sv in (-1, 1)]
        prim.box(B, -Pl, -Pl, min(zgs) - 0.5, Pl, Pl, zp - 0.4, 'stone')
        rect_walk(B, -Pl, -Pl, Pl, Pl, zp - 0.4)
        zf = zp
        # 縁 (veranda) around the body + floor
        prim.box(B, -L / 2 - 0.9, -L / 2 - 0.9, zp - 0.4, L / 2 + 0.9, L / 2 + 0.9, zf - 0.08, 'stone')
        prim.box(B, -L / 2 - 0.75, -L / 2 - 0.75, zf - 0.12, L / 2 + 0.75, L / 2 + 0.75, zf, 'wood_natural')
        rect_walk(B, -L / 2 - 0.75, -L / 2 - 0.75, L / 2 + 0.75, L / 2 + 0.75, zf)
        us, vs = arch.grid(L, L, 3, 3)
        pts = set()
        for x in us: pts.add((round(x, 3), round(vs[0], 3))); pts.add((round(x, 3), round(vs[-1], 3)))
        for y in vs: pts.add((round(us[0], 3), round(y, 3))); pts.add((round(us[-1], 3), round(y, 3)))
        for (x, y) in pts:
            prim.cyl(B, (x, y, zf - 0.02), (x, y, zf + H1), r, r * 0.97, 12, 'wood_dark', caps=(False, True))
        sides = {0: [(x, vs[0]) for x in us], 1: [(us[-1], y) for y in vs], 2: [(x, vs[-1]) for x in us[::-1]], 3: [(us[0], y) for y in vs[::-1]]}
        head = zf + H1 * 0.74
        for k in range(4):
            sp = sides[k]
            for i in range(3):
                kd = 'karado' if i == 1 else ('board' if k else 'renji')
                infill(B, sp[i], sp[i + 1], zf + 0.04, head, kd, mat='wood_dark', r=r * 0.9)
                infill(B, sp[i], sp[i + 1], head + 0.18, zf + H1 - 0.28, 'white', r=r * 0.9)
        arch.nageshi(B, L, L, head + 0.18, 'wood_dark', h=0.18, w=0.1, out=r * 0.7)
        arch.nageshi(B, L, L, zf + H1, 'wood_dark', h=0.28, w=0.18, out=0.0)
        curtains(B, (us[0], vs[0] - r - 0.1), (us[-1], vs[0] - r - 0.1), head + 0.05, h=1.05, panel=0.62)
        top1, reach1 = arch.bracket_row(B, L, L, zf + H1, 'degumi', s1, 'wood_dark', 'white_paint', us=us, vs=vs)
        R1 = jroof.Roof(L + 2 * reach1, L + 2 * reach1, top1 + ROOF_LIFT, o1, kind='hogyo', cover=cover, pitch=0.42, teri=1.6, sori=0.32,
                        truncate=None, rafter=0.22, rafter_mat='wood_dark', rafter_end='white_paint', edge=0.22)
        a1 = R1.a
        s_t = a1 - 1.55
        R1.truncate = s_t
        R1.build(B)
        z_ring = float(R1.z(s_t, a1))
        rt = 1.55 * 1.42
        # 亀腹 (white dome) and the round upper body
        prim.lathe(B, (0, 0, z_ring - 0.15), [(rt, 0.0), (rt * 0.99, 0.16), (rt * 0.9, 0.42), (rt * 0.78, 0.6), (1.42, 0.68)], 24, 'white_paint')
        zb = z_ring + 0.53
        prim.polygon(B, [(1.42 * math.cos(a), 1.42 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 25)[:-1]], zb + 0.02, 'wood_dark')
        prim.cyl(B, (0, 0, zb), (0, 0, zb + 0.35), 1.48, 1.48, 24, 'wood_dark')
        for k in range(12):
            a = 2 * math.pi * (k + 0.5) / 12
            c, sn = math.cos(a), math.sin(a)
            prim.box(B, 1.5 * c - 0.09, 1.5 * sn - 0.09, zb + 0.35, 1.5 * c + 0.09, 1.5 * sn + 0.09, zb + 0.52, 'wood_dark', tag='detail')
        prim.cyl(B, (0, 0, zb + 0.5), (0, 0, zb + 0.62), 1.62, 1.62, 24, 'wood_dark')
        ring_railing(B, 0, 0, zb + 0.62, 1.58, h=0.42)
        zu = zb + 0.62
        H2 = 1.35
        prim.cyl(B, (0, 0, zu), (0, 0, zu + H2), 1.32, 1.3, 24, 'white_paint', caps=(False, False))
        for k in range(8):
            a = 2 * math.pi * k / 8
            prim.cyl(B, (1.33 * math.cos(a), 1.33 * math.sin(a), zu), (1.33 * math.cos(a), 1.33 * math.sin(a), zu + H2), 0.1, 0.1, 6, 'wood_dark')
        prim.cyl(B, (0, 0, zu + H2 - 0.25), (0, 0, zu + H2), 1.36, 1.36, 24, 'wood_dark')
        arch.ring_beam(B, L2, L2, zu + H2 + 0.12, 0.24, 0.24, 'wood_dark')
        u2 = np.linspace(-L2 / 2, L2 / 2, 4)
        top2, reach2 = arch.bracket_row(B, L2, L2, zu + H2 + 0.12, 'mitesaki', s2, 'wood_dark', 'white_paint', us=u2, vs=u2)
        R2 = jroof.Roof(L2 + 2 * reach2, L2 + 2 * reach2, top2 + ROOF_LIFT, o2, kind='hogyo', cover=cover, pitch=0.5, teri=1.6, sori=0.36,
                        rafter=0.22, rafter_mat='wood_dark', rafter_end='white_paint', top=[(0.01, 0.0)], edge=0.22)
        zz = R2.build(B)
        a2 = R2.a
        corners = [np.array([sx * a2, sy * a2, float(R2.zE(0.0)) + 0.05]) for sx in (-1, 1) for sy in (-1, 1)]
        sorin(B, 0, 0, zz['z_ridge'] - 0.15, Hs=4.6, s=1.0, chains_to=corners)
        out.update(zf=zf, top=zz['z_ridge'] + 4.6)
    return out

# ------------------------------------------------------------------ cuttings (corridors dug into the slope)
def cutting(B, S, line_pts, line_z, half_w, *, res=0.7, surf='moss', margin=4.6):
    """lower the ground along a corridor dug into the hillside: inside the strip (half_w around the polyline) the ground
    is min(DEM, floor - 0.3); returns the strip polygon (to be added to S.cut)"""
    import shapely
    from shapely.geometry import LineString
    SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
            'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck']
    ln = LineString(line_pts)
    seg = np.linalg.norm(np.diff(np.asarray(line_pts, float), axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
    strip = ln.buffer(half_w, cap_style='flat')
    region = strip.buffer(margin)
    x0, y0, x1, y1 = region.bounds
    xs = np.arange(x0, x1 + res, res); ys = np.arange(y0, y1 + res, res)
    X, Y = np.meshgrid(xs, ys)
    pts = shapely.points(X.ravel(), Y.ravel())
    t = shapely.line_locate_point(ln, pts).reshape(X.shape)
    zf = np.interp(t, s, line_z) - 0.3
    D = S.ground(X, Y)
    d = shapely.distance(strip, pts).reshape(X.shape)
    Z = np.where(d <= 0, np.minimum(D, zf), np.minimum(D, zf + np.maximum(d - 0.0, 0) * 1.6) )
    Z = np.where(d > 2.2, D + 0.03, Z)
    inside = shapely.contains_xy(region, X, Y)
    V = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    nx = len(xs); I = []
    for j in range(len(ys) - 1):
        for i in range(nx - 1):
            if inside[j, i] and inside[j, i + 1] and inside[j + 1, i] and inside[j + 1, i + 1]:
                a = j * nx + i
                I += [[a, a + 1, a + nx + 1], [a, a + nx + 1, a + nx]]
    B.add(V, I, 'ground', UV=V[:, :2], smooth=True, c1=(0, 0, 0, SURF.index(surf)))
    B.add(V, I, 'ground', UV=V[:, :2], smooth=True, tag='walk')
    return region.buffer(-1.7)

# ------------------------------------------------------------------ pond basin + water
def basin(B, S, waters, cut_poly, *, res=1.0, depth=0.7, bank_surf='moss', tag='main'):
    """own ground inside cut_poly (+ a 2.2 m margin lifted 3 cm over the generic terrain): basins under the waters
    [(polygon, level)] (riverbed) and banks kept above the nearest water level.  The generic terrain must be cut with
    cut_poly."""
    import shapely
    SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
            'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck']
    region = cut_poly.buffer(2.2)
    x0, y0, x1, y1 = region.bounds
    xs = np.arange(x0, x1 + res, res); ys = np.arange(y0, y1 + res, res)
    X, Y = np.meshgrid(xs, ys)
    pts = shapely.points(X.ravel(), Y.ravel())
    inside = shapely.contains_xy(region, X, Y)
    incut = shapely.contains_xy(cut_poly, X, Y)
    D = S.ground(X, Y)
    Z = D + 0.03
    wet = np.zeros(X.shape, bool)
    dmin = np.full(X.shape, 1e9); Wn = np.zeros(X.shape)
    for (wp, W) in waters:
        dd = shapely.distance(wp, pts).reshape(X.shape)
        closer = dd < dmin
        dmin = np.where(closer, dd, dmin); Wn = np.where(closer, W, Wn)
    for (wp, W) in waters:
        inw = shapely.contains_xy(wp, X, Y)
        din = shapely.distance(wp.boundary, pts).reshape(X.shape)
        Z = np.where(inw, W - np.minimum(0.25 + din * 0.45, depth), Z)
        wet |= inw
    bank = incut & ~wet
    Z = np.where(bank, np.maximum(D, Wn + 0.12 + 0.1 * np.minimum(dmin, 1.0)), Z)
    V = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    nx = len(xs); I = []; C = []
    for j in range(len(ys) - 1):
        for i in range(nx - 1):
            if inside[j, i] and inside[j, i + 1] and inside[j + 1, i] and inside[j + 1, i + 1]:
                a = j * nx + i
                w_ = wet[j, i] or wet[j, i + 1] or wet[j + 1, i] or wet[j + 1, i + 1]
                for tri in ([a, a + 1, a + nx + 1], [a, a + nx + 1, a + nx]):
                    I.append(tri); C.append(SURF.index('riverbed' if w_ else bank_surf))
    I = np.array(I); C = np.array(C)
    for sid in np.unique(C):
        B.add(V, I[C == sid], 'ground', UV=V[:, :2], smooth=True, tag=tag, c1=(0, 0, 0, int(sid)))
    dry = I[C != SURF.index('riverbed')]
    if len(dry): B.add(V, dry, 'ground', smooth=True, tag='walk')

def water(B, poly, z, tag='main'):
    """flat water surface over a shapely polygon (holes allowed)"""
    polys = poly.geoms if hasattr(poly, 'geoms') else [poly]
    for p in polys:
        if p.is_empty or p.area < 0.5: continue
        ext = list(p.exterior.coords)[:-1]
        holes = [list(r.coords)[:-1] for r in p.interiors]
        prim.polygon(B, ext, z, 'water', holes=holes, tag=tag)

_ICO = None
def rock_lp(B, c, size, seed, mat='stone', flat=0.55, tag='main'):
    """a garden stone with one subdivision (80 triangles)"""
    global _ICO
    if _ICO is None:
        t = (1 + 5 ** 0.5) / 2
        V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
        F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
        V /= np.linalg.norm(V, axis=1, keepdims=True)
        mid = {}; F2 = []; V = list(V)
        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                p = (np.asarray(V[a]) + np.asarray(V[b])) / 2; V.append(p / np.linalg.norm(p)); mid[k] = len(V) - 1
            return mid[k]
        for a, b_, c_ in F:
            ab, bc, ca = m(a, b_), m(b_, c_), m(c_, a)
            F2 += [[a, ab, ca], [b_, bc, ab], [c_, ca, bc], [ab, bc, ca]]
        _ICO = (np.array(V), np.array(F2))
    V, F = _ICO
    rng = np.random.default_rng(seed)
    d = 1 + 0.2 * np.sin(V @ rng.normal(0, 3, 3)) + 0.12 * np.sin(V @ rng.normal(0, 6, 3))
    W = V * d[:, None] * [size * rng.uniform(0.8, 1.2), size * rng.uniform(0.7, 1.1), size * flat * rng.uniform(0.7, 1.2)]
    yaw = rng.uniform(0, 2 * math.pi); cy, sy = math.cos(yaw), math.sin(yaw)
    W = W @ np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]]).T + np.asarray(c, float) - [0, 0, size * flat * 0.25]
    B.add(W, F, mat, smooth=True, tag=tag)

def shore_rocks(B, poly, z, *, step=1.1, seed=1, size=(0.35, 0.85), mat='stone', skip=None):
    rng = np.random.default_rng(seed)
    for ring in [poly.exterior] + list(poly.interiors):
        L = ring.length; k = int(L / step)
        for i in range(k):
            p = ring.interpolate(i * step + rng.uniform(-0.2, 0.2))
            if skip is not None and skip.contains(p): continue
            sz = rng.uniform(*size)
            rock_lp(B, (p.x, p.y, z + sz * 0.15), sz, int(rng.integers(1 << 30)), mat, flat=0.55)

# ------------------------------------------------------------------ preview-only: tree proxies, colours
TREE_COL = {'momiji': (0.62, 0.07, 0.03), 'ichou': (0.85, 0.62, 0.05), 'sakura': (0.55, 0.25, 0.1), 'keyaki': (0.5, 0.28, 0.08),
            'matsu': (0.06, 0.16, 0.06), 'sugi': (0.05, 0.12, 0.05), 'hinoki': (0.06, 0.14, 0.06), 'kashi': (0.08, 0.18, 0.06),
            'yanagi': (0.3, 0.42, 0.1), 'tsutsuji': (0.55, 0.12, 0.05), 'take': (0.25, 0.4, 0.1)}
TREE_SIZE = {'momiji': (6.5, 0.62, 'dome'), 'ichou': (14.0, 0.28, 'oval'), 'sakura': (7.5, 0.7, 'dome'), 'keyaki': (16.0, 0.46, 'dome'),
             'matsu': (7.5, 0.45, 'pads'), 'sugi': (23.0, 0.17, 'cone'), 'hinoki': (18.0, 0.22, 'cone'), 'kashi': (11.0, 0.48, 'dome'),
             'yanagi': (8.5, 0.5, 'dome'), 'tsutsuji': (1.1, 0.9, 'dome'), 'take': (11.0, 0.18, 'cone')}

def cut_preview_terrain(S):
    """the preview terrain of run_site is not cut where the site models its own ground (pond basin, cuttings): drop its
    faces inside S.cut, as the tile builder does"""
    import bpy, shapely
    from shapely.geometry import Polygon
    if not S.cut: return
    cut = shapely.unary_union([Polygon(c[0], c[1:]) for c in S.cut])
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or not ob.name.startswith('terrain'): continue
        me = ob.data
        n = len(me.polygons)
        C = np.zeros(n * 3); me.polygons.foreach_get('center', C); C = C.reshape(-1, 3)
        inside = shapely.contains_xy(cut, C[:, 0], C[:, 1])
        if not inside.any(): continue
        import bmesh
        bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.faces[i] for i in np.nonzero(inside)[0]], context='FACES_ONLY')
        bm.to_mesh(me); bm.free(); me.update()

def add_preview_proxies(B, S=None):
    """Blender objects for the preview renders only (added after the .blend is saved): tree proxies and the tinted
    vertex colours of cloth / plaster"""
    import bpy
    if S is not None: cut_preview_terrain(S)
    from jk.core import Builder, to_objects
    import os
    names = Builder.TREE_SPECIES
    T = Builder('tree_proxies')
    rng = np.random.default_rng(7)
    for (sp, x, y, z, sc, yaw) in ([] if os.environ.get('EIK_NOTREES') else B.trees):
        name = names[int(sp)]
        H0, R0, shape = TREE_SIZE[name]
        Hh = H0 * sc; Rr = max(0.4, R0 * Hh)
        prim.cyl(T, (x, y, z - 0.2), (x, y, z + Hh * 0.45), max(0.08, Hh * 0.018), max(0.05, Hh * 0.012), 5, 'wood_dark')
        if shape == 'cone':
            prof = [(0.0, Hh * 0.25), (Rr, Hh * 0.35), (Rr * 0.6, Hh * 0.7), (0.0, Hh)]
        elif shape == 'pads':
            prof = [(0.0, Hh * 0.45), (Rr * 1.1, Hh * 0.55), (Rr * 0.9, Hh * 0.8), (0.0, Hh * 0.88)]
        elif shape == 'oval':
            prof = [(0.0, Hh * 0.15), (Rr, Hh * 0.35), (Rr * 1.05, Hh * 0.6), (Rr * 0.6, Hh * 0.88), (0.0, Hh)]
        else:
            prof = [(0.0, Hh * 0.3), (Rr * 0.85, Hh * 0.38), (Rr, Hh * 0.6), (Rr * 0.7, Hh * 0.88), (0.0, Hh)]
        prof = [(rr * rng.uniform(0.9, 1.1), zz) for (rr, zz) in prof]
        prim.lathe(T, (x, y, z), prof, 9, 'cloth', c0=tuple(int(255 * c) for c in TREE_COL[name]) + (0,))
    objs = to_objects(T, name='tree_proxies') if T.parts else []
    # vertex colours: multiply cloth / temple_wall by C0
    for ob in list(bpy.data.objects):
        if not ob.type == 'MESH': continue
        src = T if ob.name.startswith('tree_proxies') else (B if ob.get('jk_tag') in ('main', 'detail') and not ob.name.startswith('terrain') else None)
        if src is None: continue
        M = src.merged((ob['jk_tag'],)) if 'jk_tag' in ob else None
        if M is None or len(M['P']) != len(ob.data.vertices): continue
        col = (M['C0'][:, :3].astype(np.float32) / 255.0) ** 2.2
        attr = ob.data.color_attributes.new('C0', 'FLOAT_COLOR', 'POINT')
        attr.data.foreach_set('color', np.c_[col, np.ones(len(col))].ravel().astype(np.float32))
    for m in bpy.data.materials:
        if m.name.startswith('jk_') and m.name not in ('jk_water',): m.use_backface_culling = True      # as the viewer draws
    for nm in ('jk_cloth', 'jk_temple_wall'):
        m = bpy.data.materials.get(nm)
        if m is None: continue
        nt = m.node_tree; bs = nt.nodes.get('Principled BSDF')
        at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'C0'
        if nm == 'jk_cloth':
            nt.links.new(at.outputs['Color'], bs.inputs['Base Color'])
        else:
            mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0
            mix.inputs['A'].default_value = (0.85, 0.84, 0.8, 1)
            nt.links.new(at.outputs['Color'], mix.inputs['B']); nt.links.new(mix.outputs['Result'], bs.inputs['Base Color'])
    return objs
