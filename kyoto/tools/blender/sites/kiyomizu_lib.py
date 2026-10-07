"""Kiyomizu-dera: shared helpers for the site modules (roof profiles, an envelope hip roof for asymmetric roofs,
the 懸造 post-and-貫 frame, stone stairs, 石垣, railings and fences, walk / block helpers, preview tree proxies).

Everything here works in the builder's current frame (jk.Frame) unless a function takes the Site `S` to follow the
terrain (those expect world coordinates, i.e. no Frame active)."""
import math
import numpy as np
from jk import prim, arch, Frame
from jk import roof as jroof

TAU = 2 * math.pi

# ------------------------------------------------------------------ small vector helpers
def v2(p): return np.asarray(p, float)[:2]
def unit(d):
    d = np.asarray(d, float); n = np.linalg.norm(d)
    return d / n if n > 1e-12 else d
def perp(d): return np.array([-d[1], d[0]])
def rot2(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s], [s, c]])
def to_world(fr, pts):
    """local (u, v) points of a frame (ox, oy, yaw) -> world xy"""
    ox, oy, yaw = fr
    return np.asarray(pts, float) @ rot2(yaw).T + [ox, oy]
def to_local(fr, pts):
    ox, oy, yaw = fr
    return (np.asarray(pts, float) - [ox, oy]) @ rot2(yaw)

# ------------------------------------------------------------------ roof profiles
def slope_profile(s0=0.3, smax=1.0, s1=0.45, d_flare=0.18, n=400):
    """g(t) on t in [0, 1] (0 = eave, 1 = ridge) from a slope curve: gentle at the eave (照り), steepest at d_flare,
    then easing toward the ridge (起り).  Normalised so g(1) = 1."""
    t = np.linspace(0, 1, n + 1)
    a = np.clip(t / d_flare, 0, 1); a = a * a * (3 - 2 * a)
    s = np.where(t < d_flare, s0 + (smax - s0) * a, smax + (s1 - smax) * (t - d_flare) / (1 - d_flare))
    g = np.concatenate([[0], np.cumsum((s[1:] + s[:-1]) / 2 * np.diff(t))])
    g /= g[-1]
    return lambda x: np.interp(np.clip(np.asarray(x, float), 0, 1), t, g)

def abs_profile(s0=0.28, smax=0.95, s1=0.4, d_flare=3.5, d_end=22.0, scale=1.0):
    """P(d): rise (m) at inward distance d (m) from the eave, for the envelope roof (same slope law on every face)"""
    d = np.linspace(-5, 60, 1301)
    a = np.clip(d / d_flare, 0, 1); a = a * a * (3 - 2 * a)
    s = np.where(d < d_flare, s0 + (smax - s0) * a, np.maximum(s1, smax + (s1 - smax) * (d - d_flare) / (d_end - d_flare)))
    s = np.where(d < 0, s0, s)
    P = np.concatenate([[0], np.cumsum((s[1:] + s[:-1]) / 2 * np.diff(d))])
    P -= np.interp(0.0, d, P)
    return lambda x: np.interp(np.asarray(x, float), d, P) * scale

class MRoof(jroof.Roof):
    """the kit's roof with an optional custom profile g(t) (起り / 照り mix) and a copper flashing strip on the eaves"""
    def __init__(self, L, D, z_eave, o, prof=None, flash=None, coarse=None, **kw):
        super().__init__(L, D, z_eave, o, **kw)
        if prof is not None:
            self.g = prof
            self.zE0 = z_eave - self.H * self.g(o / self.c)
        self.flash = flash
        self.coarse = coarse
    def face(self, B, k, x0=None, x1=None, smax=None, s0=0.0, nu=None, nt=None, offset=0.0, mat=None, flip=False, extend=0.0):
        if self.coarse:
            p0, p1, n_in, E = self.sides()[k]
            xa = -extend if x0 is None else x0; xb = E + extend if x1 is None else x1
            nu = max(3, int((xb - xa) / (0.6 * self.coarse))) if nu is None else max(3, int(nu / self.coarse))
            nt = max(3, int(self.c / (0.5 * self.coarse))) if nt is None else max(2, int(nt / self.coarse))
        return super().face(B, k, x0, x1, smax, s0, nu, nt, offset, mat, flip, extend)
    def eave(self, B, k, x0, x1, gable_side=False):
        super().eave(B, k, x0, x1, gable_side)
        if self.flash:
            p0, p1, n_in, E = self.sides()[k]
            d = (p1 - p0) / E
            xs = np.linspace(x0, x1, max(4, int((x1 - x0) / 0.5)) + 1)
            dcc = np.minimum(np.clip(xs, 0, E), np.clip(E - xs, 0, E))
            top = np.array([[*(p0 + d * x - n_in * 0.015), float(self.z(0.0, dc)) + 0.01] for x, dc in zip(xs, dcc)])
            ribbon(B, top, top - [0, 0, 0.09], self.flash, tag='detail')

def mroof(B, L, D, z_eave, o, **kw):
    return MRoof(L, D, z_eave, o, **kw).build(B)

def ribbon(B, A, Bp, mat, tag='main', **kw):
    """a strip between two polylines (same length)"""
    A = np.asarray(A, float); Bp = np.asarray(Bp, float); n = len(A)
    P = np.concatenate([A, Bp]); I = []
    for i in range(n - 1):
        I += [[i, i + n, i + 1], [i + 1, i + n, i + n + 1]]
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(A, axis=0), axis=1))]
    UV = np.c_[np.r_[L, L], np.r_[np.zeros(n), np.full(n, np.linalg.norm(A[0] - Bp[0]))]]
    B.add(P, I, mat, UV=UV, tag=tag, **kw)
    B.add(P, [t[::-1] for t in I], mat, UV=UV, tag=tag, **kw)

# ------------------------------------------------------------------ envelope roof (asymmetric hip roofs)
class EnvRoof:
    """A hip roof as the lower envelope of its faces: face k rises from its eave line (p0 -> p1, inward = left side)
    by z_k + sori_k(x) + P_k(d).  Faces with different eave heights / slopes meet in hips and a ridge that follow
    automatically (the 本堂: the front slope runs down over the 庇 far below the other three eaves).
    face dict: p0, p1, z, prof (P(d)), o (overhang to the wall line), sori, sori_len, dcap (lean-to: max depth),
    eave (bool: draw the eave edge / soffit / rafters)."""
    def __init__(self, faces, mat='hiwada', tag='main', edge=0.42, fascia='wood_dark', flash='copper', rafter=0.24, rafter_mat='wood_dark',
                 rafter_end=None, tiers=2, masks=(), res=0.55):
        self.F = []
        for f in faces:
            f = dict(f); p0 = v2(f['p0']); p1 = v2(f['p1'])
            t = p1 - p0; E = float(np.linalg.norm(t)); t /= E
            f.update(p0=p0, p1=p1, t=t, n=perp(t), E=E)
            f.setdefault('sori', 0.0); f.setdefault('sori_len', 5.0); f.setdefault('dcap', 1e9); f.setdefault('eave', True); f.setdefault('o', 2.0)
            self.F.append(f)
        self.mat = mat; self.tag = tag; self.edge = edge; self.fascia = fascia; self.flash = flash
        self.rafter = rafter; self.rafter_mat = rafter_mat; self.rafter_end = rafter_end or rafter_mat; self.tiers = tiers
        self.res = res
        import shapely
        from shapely.geometry import Polygon
        self.masks = [Polygon(m) for m in masks]
        self.mask_union = shapely.unary_union(self.masks) if self.masks else None

    def zk(self, k, P2):
        f = self.F[k]; P2 = np.atleast_2d(P2)
        rel = P2 - f['p0']; x = rel @ f['t']; d = rel @ f['n']
        dc = np.clip(np.minimum(x, f['E'] - x), 0, None)
        so = f['sori'] * np.clip(1 - dc / f['sori_len'], 0, 1) ** 2
        z = f['z'] + so + f['prof'](d)
        return np.where(d > f['dcap'] + 1e-6, 1e9, z)

    def env(self, P2, skip=None):
        Z = np.stack([self.zk(k, P2) if k != skip else np.full(len(np.atleast_2d(P2)), 1e9) for k in range(len(self.F))])
        return Z.min(0), Z.argmin(0)

    def depth(self, k, xs):
        """inward depth where face k stops being the lowest (bisection), and the winning face there"""
        f = self.F[k]
        base = f['p0'] + np.outer(xs, f['t'])
        lo = np.zeros(len(xs)); hi = np.full(len(xs), min(f['dcap'], 80.0))
        def ok(dd):
            P = base + np.outer(dd, f['n'])
            zo, _ = self.env(P, skip=k)
            return self.zk(k, P) <= zo + 1e-5
        # coarse march for the first crossing
        dd = np.zeros(len(xs)); found = np.zeros(len(xs), bool); step = 0.4
        cur = np.zeros(len(xs))
        for i in range(int(80 / step) + 1):
            nxt = np.minimum(cur + step, hi)
            good = ok(nxt)
            stop = ~good & ~found
            lo = np.where(stop, cur, lo); hi = np.where(stop, nxt, hi); found |= stop
            cur = np.where(found, cur, nxt)
            if found.all() or (cur >= hi).all(): break
        lo = np.where(found, lo, hi); hi2 = np.where(found, hi, hi)
        a = lo.copy(); b = hi2.copy()
        for _ in range(22):
            m = (a + b) / 2; g = ok(m) | ~found
            a = np.where(g, m, a); b = np.where(g, b, m)
        dstar = np.where(found, a, hi)
        P = base + np.outer(dstar + 0.05, f['n'])
        _, win = self.env(P, skip=k)
        win = np.where(found, win, -1)
        return dstar, win

    def build(self, B):
        out = {}
        import shapely
        for k, f in enumerate(self.F):
            nu = max(6, int(f['E'] / self.res))
            xs = np.linspace(0, f['E'], nu + 1)
            ds, win = self.depth(k, xs)
            f['_xs'] = xs; f['_ds'] = ds; f['_win'] = win
            nt = max(4, int(ds.max() / self.res))
            P = []; UV = []
            for j in range(nt + 1):
                tt = j / nt
                d = ds * tt
                xy = f['p0'] + np.outer(xs, f['t']) + np.outer(d, f['n'])
                z = self.zk(k, xy)
                P += [np.c_[xy, z]]; UV += [np.c_[xs, d * 1.12]]
            P = np.concatenate(P); UV = np.concatenate(UV)
            I = []
            for j in range(nt):
                for i in range(nu):
                    a = j * (nu + 1) + i
                    I += [[a, a + 1, a + nu + 2], [a, a + nu + 2, a + nu + 1]]
            I = np.array(I)
            A = np.linalg.norm(np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]]), axis=1)
            I = I[A > 1e-7]
            if self.mask_union is not None:
                C = P[I].mean(1)
                I = I[~shapely.contains_xy(self.mask_union, C[:, 0], C[:, 1])]
            B.add(P, I, self.mat, UV=UV, smooth=True, tag=self.tag)
            if f['eave']: self._eave(B, k)
            # lean-to top against a wall: a flashing strip
            if f['dcap'] < 1e8:
                m = ds >= f['dcap'] - 1e-3
                if m.sum() >= 2:
                    xy = f['p0'] + np.outer(xs[m], f['t']) + np.outer(ds[m], f['n'])
                    z = self.zk(k, xy - np.outer(np.full(m.sum(), 0.01), f['n']))
                    top = np.c_[xy, z + 0.12]; bot = np.c_[xy - np.outer(np.full(m.sum(), 0.25), f['n']), z + 0.02 - 0.25 * 0.3]
                    ribbon(B, top, bot, self.flash or self.mat, tag=self.tag)
        return out

    def _eave(self, B, k):
        f = self.F[k]; E = f['E']
        nu = max(4, int(E / 0.4))
        xs = np.linspace(0, E, nu + 1)
        xy = f['p0'] + np.outer(xs, f['t'])
        keep = np.ones(len(xs), bool)
        if self.mask_union is not None:
            import shapely
            keep = ~shapely.contains_xy(self.mask_union, xy[:, 0] + f['n'][0] * 0.3, xy[:, 1] + f['n'][1] * 0.3)
        q = xy + np.outer(np.full(len(xs), 0.03), f['n'])
        zenv, win = self.env(q)
        own = win == k
        z = self.zk(k, xy)
        out3 = np.r_[-f['n'], 0.0]
        th = self.edge
        # where another face wins at this outline (its side edge, like a verge): a verge band at the envelope height
        vr = []; cur = []
        for i in range(len(xs)):
            if keep[i] and not own[i]: cur.append(i)
            elif cur: vr.append(cur); cur = []
        if cur: vr.append(cur)
        for r in vr:
            if len(r) < 2: continue
            r = [max(0, r[0] - 1)] + r + ([r[-1] + 1] if r[-1] + 1 < len(xs) else [])
            top = np.c_[xy[r], np.minimum(zenv[r], z[r]) + 0.02]
            for (a, b, m) in ((0.0, 0.07, self.flash or self.mat), (0.07, th * 0.75, self.mat), (th * 0.75, th * 1.1, self.fascia)):
                ribbon(B, top - [0, 0, a], top - [0, 0, b], m, tag=self.tag)
        keep = keep & own
        # split into runs of kept samples
        runs = []; cur = []
        for i in range(len(xs)):
            if keep[i]: cur.append(i)
            elif cur: runs.append(cur); cur = []
        if cur: runs.append(cur)
        for r in runs:
            if len(r) < 2: continue
            top = np.c_[xy[r], z[r]]
            bands = [(0.0, 0.07, self.flash or self.mat), (0.07, th * 0.6, self.mat), (th * 0.6, th, self.fascia)]
            for (a, b, m) in bands:
                A_ = top - [0, 0, a]; B_ = top - [0, 0, b]; n = len(r)
                P = np.concatenate([A_, B_]); I = []
                for i in range(n - 1): I += [[i, i + n, i + 1], [i + 1, i + n, i + n + 1]]
                B.add(P, I, m, UV=np.c_[np.r_[xs[r], xs[r]], np.r_[A_[:, 2], B_[:, 2]]], N=np.tile(out3, (len(P), 1)), tag=self.tag)
            # soffit: offset copy of the cover from the edge to the wall line
            dmax = np.minimum(np.full(len(r), f['o'] + 0.25), np.clip(np.minimum(xs[r], E - xs[r]), 0, None))
            dmax = np.minimum(dmax, f['_ds'][np.clip(np.searchsorted(f['_xs'], xs[r]), 0, len(f['_xs']) - 1)])
            Ps = []
            ntt = 3
            for j in range(ntt + 1):
                d = dmax * j / ntt
                q = xy[r] + np.outer(d, f['n'])
                Ps.append(np.c_[q, self.zk(k, q) - th - 0.02])
            Ps = np.concatenate(Ps); n = len(r); I = []
            for j in range(ntt):
                for i in range(n - 1):
                    a = j * n + i
                    I += [[a, a + n + 1, a + 1], [a, a + n, a + n + 1]]
            B.add(Ps, I, self.fascia, smooth=True, tag=self.tag)
            # rafters, two tiers (地垂木 / 飛檐垂木)
            if self.rafter:
                o = f['o']
                tiers = ((0.0, o * 0.55, th + 0.07), (o * 0.45, o + 0.15, th + 0.24))[:self.tiers]
                for ti, (sa, sb, drop) in enumerate(tiers):
                    for x in np.arange(xs[r[0]] + self.rafter / 2, xs[r[-1]], self.rafter):
                        dc = min(x, E - x)
                        sbb = min(sb, dc - 0.1)
                        if sbb <= sa + 0.1: continue
                        q0 = f['p0'] + f['t'] * x + f['n'] * sa; q1 = f['p0'] + f['t'] * x + f['n'] * sbb
                        z0 = float(self.zk(k, q0)[0]) - drop; z1 = float(self.zk(k, q1)[0]) - drop
                        prim.obox(B, np.r_[q0, z0], np.r_[q1, z1], 0.085, 0.1, self.rafter_mat, tag='detail')
                        if ti == 0 and self.rafter_end != self.rafter_mat:
                            e = q0 + f['n'] * 0.025
                            prim.obox(B, np.r_[q0 - f['n'] * 0.004, z0], np.r_[e, z0 + (z1 - z0) * 0.025 / max(1e-3, sbb - sa)], 0.088, 0.102, self.rafter_end, tag='detail')

    def crease(self, k, j):
        """the boundary polyline between face k and face j (from face k's samples)"""
        f = self.F[k]
        m = (f['_win'] == j) & (f['_ds'] > 0.08)
        if m.sum() < 2: return None
        xs = f['_xs'][m]; ds = f['_ds'][m]
        xy = f['p0'] + np.outer(xs, f['t']) + np.outer(ds, f['n'])
        z = self.zk(k, xy)
        return np.c_[xy, z]

def ridge_cap(B, pts, w, h, mat='ridge', tag='main', ends=None, end_mat='ridge'):
    """a box ridge (箱棟) / hip cap along a 3D polyline"""
    pts = np.asarray(pts, float)
    if len(pts) < 2: return
    prof = [(-w / 2, -0.2), (w / 2, -0.2), (w / 2, h * 0.75), (w * 0.38, h), (-w * 0.38, h), (-w / 2, h * 0.75)]
    prim.sweep(B, pts, prof, mat, closed=True, tag=tag, caps=True)
    for e, p, q in (((ends or (None, None))[0], pts[0], pts[1]), ((ends or (None, None))[1], pts[-1], pts[-2])):
        if not e: continue
        dd = unit(p - q); side = unit(np.cross(dd, [0, 0, 1.0]))
        ww = w * 1.5; hh = h * 1.7
        R = [(-ww / 2, -0.15), (ww / 2, -0.15), (ww / 2, hh * 0.6), (ww * 0.28, hh), (-ww * 0.28, hh), (-ww / 2, hh * 0.6)]
        c0 = p + dd * 0.03
        P = [c0 + side * x + np.array([0, 0, y]) + dd * (y * 0.1) for x, y in R]
        Pb = [q_ - dd * 0.14 for q_ in P]
        Pall = np.array(P + Pb); n = len(R)
        I = [[0, j, j + 1] for j in range(1, n - 1)] + [[n, n + j + 1, n + j] for j in range(1, n - 1)]
        for j in range(n):
            k2 = (j + 1) % n
            I += [[j, j + n, k2 + n], [j, k2 + n, k2]]
        fn = np.cross(Pall[1] - Pall[0], Pall[2] - Pall[0])
        if fn @ dd < 0: I = [t[::-1] for t in I]
        B.add(Pall, I, end_mat, tag=tag, c1=(0, 1, 0, 0))

# ------------------------------------------------------------------ frame members
def post(B, x, y, z0, z1, r, mat='wood_dark', seg=12, base='stone', base_h=0.25, tag='main', square=False):
    if base:
        prim.cyl(B, (x, y, z0 - 0.3), (x, y, z0 + base_h), r * 1.55, r * 1.4, 8, base, tag=tag)
    if square:
        prim.box(B, x - r, y - r, z0 + (base_h if base else 0) - 0.02, x + r, y + r, z1, mat, tag=tag, faces='xXyYZ')
    else:
        prim.cyl(B, (x, y, z0 + (base_h if base else 0) - 0.02), (x, y, z1), r, r * 0.97, seg, mat, caps=(False, True), tag=tag)

def beam(B, p0, p1, z, w, h, mat, tag='main', ext=0.0):
    p0 = v2(p0); p1 = v2(p1); d = unit(p1 - p0)
    p0 = p0 - d * ext; p1 = p1 + d * ext
    prim.obox(B, (p0[0], p0[1], z - h / 2), (p1[0], p1[1], z - h / 2), w, h, mat, tag=tag)

def wall_panel(B, p0, p1, z0, z1, mat, inset=0.0, out=None, tag='main', both=True, c0=(255, 255, 255, 0), c1=(0, 0, 0, 0)):
    """a vertical quad between two plan points (both sides by default)"""
    p0 = v2(p0); p1 = v2(p1); d = unit(p1 - p0); n = perp(d) * -1 if out is None else unit(out)
    a = p0 - n * inset; b = p1 - n * inset
    P = np.array([np.r_[a, z0], np.r_[b, z0], np.r_[b, z1], np.r_[a, z1]])
    L = float(np.linalg.norm(p1 - p0))
    UV = np.array([[0, z0], [L, z0], [L, z1], [0, z1]])
    fn = np.cross(P[1] - P[0], P[2] - P[0])
    I = [[0, 1, 2], [0, 2, 3]]
    if fn[:2] @ n < 0: I = [[0, 2, 1], [0, 3, 2]]
    B.add(P, I, mat, UV=UV, tag=tag, c0=c0, c1=c1)
    if both: B.add(P, [t[::-1] for t in I], mat, UV=UV, tag=tag, c0=c0, c1=c1)

PLASTER = dict(c0=(238, 234, 224, 35), c1=(0, 0, 0, 0))

def lattice(B, p0, p1, z0, z1, mat='wood_dark', step=0.16, bar=0.035, back='glass', inset=0.05, tag='detail', diag=False, out=None, back_tag='main'):
    """格子 / 蔀戸 grid (square lattice) or 菱格子 (diagonal) in a bay between two plan points"""
    p0 = v2(p0); p1 = v2(p1); d = unit(p1 - p0); L = float(np.linalg.norm(p1 - p0))
    n = -perp(d) if out is None else unit(out)
    if back: wall_panel(B, p0 - n * (inset + 0.04), p1 - n * (inset + 0.04), z0, z1, back, tag=back_tag, both=True)
    prim.obox(B, np.r_[p0 - n * inset, z0], np.r_[p1 - n * inset, z0], 0.08, 0.08, mat, tag=tag)
    prim.obox(B, np.r_[p0 - n * inset, z1], np.r_[p1 - n * inset, z1], 0.08, 0.08, mat, tag=tag)
    if not diag:
        for x in np.arange(step / 2, L, step):
            q = p0 + d * x - n * inset
            prim.obox(B, np.r_[q, z0], np.r_[q, z1], bar, bar, mat, tag=tag, ends=False)
        for zz in np.arange(z0 + step / 2, z1, step):
            prim.obox(B, np.r_[p0 - n * inset, zz], np.r_[p1 - n * inset, zz], bar, bar, mat, tag=tag, ends=False)
    else:
        H = z1 - z0
        sp = step * 1.4
        for sgn in (1, -1):
            for c in np.arange(-H, L + H, sp):
                # the line x = c + sgn * z (z from 0 to H), clipped to 0 <= x <= L
                za, zb = 0.0, H
                xa, xb = c, c + sgn * H
                if sgn < 0: xa, xb = c + H, c; za, zb = 0.0, H
                def at(x):
                    return za + (zb - za) * (x - xa) / (xb - xa)
                lo_x, hi_x = max(0.0, min(xa, xb)), min(L, max(xa, xb))
                if hi_x - lo_x < 0.04: continue
                q0 = np.r_[p0 + d * lo_x - n * inset, z0 + at(lo_x)]; q1 = np.r_[p0 + d * hi_x - n * inset, z0 + at(hi_x)]
                prim.obox(B, q0, q1, bar, bar, mat, tag=tag, ends=False)

# ------------------------------------------------------------------ railings and fences
def rail_line(B, pts, z, h=1.0, mat='wood_natural', post_mat=None, giboshi_at=(), cap_mat='bronze', post_every=1.8, tag='main', struts=True, zfn=None, w=0.11):
    """a wooden 高欄 (stage railing): posts, top rail (笠木), mid rail, bottom rail; 擬宝珠 caps at the given vertex
    indices.  zfn(x, y) gives the floor height if it varies."""
    post_mat = post_mat or mat
    pts = [v2(p) for p in pts]
    zf = (lambda p: z) if zfn is None else (lambda p: float(zfn(p[0], p[1])))
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; L = float(np.linalg.norm(b - a))
        if L < 0.05: continue
        za, zb = zf(a), zf(b)
        for zz, ww, hh in ((h, w, w * 0.9), (h * 0.5, w * 0.7, w * 0.75), (0.08, w * 1.1, w * 1.1)):
            prim.obox(B, np.r_[a, za + zz - hh / 2], np.r_[b, zb + zz - hh / 2], ww, hh, mat, tag=tag)
        n = max(1, int(round(L / post_every)))
        for j in range(1, n):
            q = a + (b - a) * j / n; zq = za + (zb - za) * j / n
            prim.box(B, q[0] - 0.07, q[1] - 0.07, zq, q[0] + 0.07, q[1] + 0.07, zq + h + 0.02, post_mat, tag=tag)
        if struts:
            for t in np.arange(0.45, L, 0.9):
                q = a + (b - a) * t / L; zq = za + (zb - za) * t / L
                prim.obox(B, np.r_[q, zq + 0.12], np.r_[q, zq + h * 0.5], 0.05, 0.05, mat, tag='detail')
    for i, p in enumerate(pts):
        zp = zf(p)
        big = i in giboshi_at
        r = 0.11 if big else 0.075
        prim.box(B, p[0] - r, p[1] - r, zp, p[0] + r, p[1] + r, zp + h + (0.12 if big else 0.03), post_mat, tag=tag)
        if big:
            prim.lathe(B, np.r_[p, zp + h + 0.12], [(0.12, 0.0), (0.13, 0.08), (0.09, 0.14), (0.15, 0.26), (0.12, 0.38), (0.04, 0.46), (0.0, 0.52)], 12, cap_mat, tag='detail')

def fence_black(B, pts, S=None, z=None, h=1.2, step=0.22, tag='main'):
    """the black 透塀-like wooden fence of the Saimon / pagoda terraces"""
    for i in range(len(pts) - 1):
        a, b = v2(pts[i]), v2(pts[i + 1]); L = float(np.linalg.norm(b - a))
        if L < 0.1: continue
        d = unit(b - a)
        za = S.ground(*a) if S is not None else z; zb = S.ground(*b) if S is not None else z
        for zz in (h, h * 0.75, 0.15):
            prim.obox(B, np.r_[a, za + zz], np.r_[b, zb + zz], 0.08, 0.09, 'black_lacquer', tag=tag)
        for t in np.arange(0.0, L + 0.01, 1.8):
            q = a + d * t; zq = za + (zb - za) * t / L
            prim.box(B, q[0] - 0.06, q[1] - 0.06, zq - 0.2, q[0] + 0.06, q[1] + 0.06, zq + h + 0.08, 'black_lacquer', tag=tag)
        for t in np.arange(step / 2, L, step):
            q = a + d * t; zq = za + (zb - za) * t / L
            prim.obox(B, np.r_[q, zq + 0.15], np.r_[q, zq + h], 0.05, 0.035, 'black_lacquer', tag='detail', ends=False)

def tamagaki(B, pts, S=None, z=None, h=0.9, mat='stone', tag='main'):
    """石の玉垣 / stone balustrade: posts every ~1.8 m, top and bottom rails, short balusters"""
    for i in range(len(pts) - 1):
        a, b = v2(pts[i]), v2(pts[i + 1]); L = float(np.linalg.norm(b - a))
        if L < 0.1: continue
        d = unit(b - a)
        za = S.ground(*a) if S is not None else z; zb = S.ground(*b) if S is not None else z
        if callable(z): za, zb = z(*a), z(*b)
        prim.obox(B, np.r_[a, za + h - 0.06], np.r_[b, zb + h - 0.06], 0.2, 0.14, mat, tag=tag)
        prim.obox(B, np.r_[a, za + 0.1], np.r_[b, zb + 0.1], 0.24, 0.22, mat, tag=tag)
        n = max(1, int(round(L / 1.8)))
        for j in range(n + 1):
            q = a + (b - a) * j / n; zq = za + (zb - za) * j / n
            prim.box(B, q[0] - 0.12, q[1] - 0.12, zq - 0.1, q[0] + 0.12, q[1] + 0.12, zq + h + 0.12, mat, tag=tag)
            prim.lathe(B, np.r_[q, zq + h + 0.12], [(0.12, 0), (0.1, 0.06), (0.0, 0.1)], 4, mat, tag='detail', smooth=False)
        for t in np.arange(0.45, L, 0.45):
            q = a + d * t; zq = za + (zb - za) * t / L
            prim.obox(B, np.r_[q, zq + 0.2], np.r_[q, zq + h - 0.13], 0.09, 0.07, mat, tag='detail')

def handrail(B, pts3, h=0.85, mat='metal_dark', tag='detail', post_every=2.5):
    """an iron handrail along a 3D polyline (stairs)"""
    pts3 = np.asarray(pts3, float)
    top = pts3 + [0, 0, h]
    prim.sweep(B, top, [(0.025 * math.cos(a), 0.025 * math.sin(a)) for a in np.linspace(0, TAU, 7)[:-1]], mat, tag=tag)
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts3[:, :2], axis=0), axis=1))]
    for s in np.arange(0, L[-1] + 0.01, post_every):
        p = np.array([np.interp(s, L, pts3[:, k]) for k in range(3)])
        prim.cyl(B, p, p + [0, 0, h], 0.022, 0.022, 6, mat, tag=tag)

# ------------------------------------------------------------------ stone stairs and walls
def steps(B, p0, p1, z0, z1, width, mat='stone', riser=0.17, tag='main', walk=True, base=None, cheek=None, cheek_mat='stone', S=None, nosing=0.03):
    """a straight stone flight from (p0, z0) to (p1, z1) (plan points), equal risers; each tread a block down to
    `base` (or 0.6 m below its own top / the terrain if S is given).  cheek: width of side walls (袖石) or None.
    Adds a sloped walk ramp."""
    p0 = v2(p0); p1 = v2(p1)
    d = p1 - p0; L = float(np.linalg.norm(d)); d /= L; n = perp(d)
    k = max(1, int(round(abs(z1 - z0) / riser)))
    rise = (z1 - z0) / k
    for i in range(k):
        a = p0 + d * L * i / k; b = p0 + d * L * (i + 1) / k
        zt = z0 + rise * (i + 1)
        zb = base if base is not None else zt - abs(rise) - 0.5
        if S is not None:
            zb = min(zb, float(min(S.ground(*(a - n * width / 2)), S.ground(*(a + n * width / 2)), S.ground(*(b - n * width / 2)), S.ground(*(b + n * width / 2)))) - 0.3)
        a2 = a - d * nosing
        P = np.array([np.r_[a2 - n * width / 2, zb], np.r_[b - n * width / 2, zb], np.r_[b + n * width / 2, zb], np.r_[a2 + n * width / 2, zb],
                      np.r_[a2 - n * width / 2, zt], np.r_[b - n * width / 2, zt], np.r_[b + n * width / 2, zt], np.r_[a2 + n * width / 2, zt]])
        # top, front, two sides
        F = [[4, 5, 6], [4, 6, 7], [0, 4, 7], [0, 7, 3], [0, 1, 5], [0, 5, 4], [3, 7, 6], [3, 6, 2]]
        Pc = P.mean(0)
        F2 = []
        for t in F:
            fn = np.cross(P[t[1]] - P[t[0]], P[t[2]] - P[t[0]])
            F2.append(t if fn @ (P[t].mean(0) - Pc) > 0 else t[::-1])
        B.add(P, F2, mat, tag=tag)
    if cheek:
        for s in (-1, 1):
            off = n * s * (width / 2 + cheek / 2)
            q0 = p0 + off - d * 0.3; q1 = p1 + off + d * 0.1
            zz0 = z0 + 0.25; zz1 = z1 + 0.25
            zb0 = (S.ground(*q0) - 0.4) if S is not None else z0 - 0.6
            zb1 = (S.ground(*q1) - 0.4) if S is not None else min(z0, z1) - 0.6
            P = np.array([np.r_[q0 - n * s * cheek / 2, zb0], np.r_[q1 - n * s * cheek / 2, min(zb1, zz1 - 0.6)], np.r_[q1 - n * s * cheek / 2, zz1], np.r_[q0 - n * s * cheek / 2, zz0],
                          np.r_[q0 + n * s * cheek / 2, zb0], np.r_[q1 + n * s * cheek / 2, min(zb1, zz1 - 0.6)], np.r_[q1 + n * s * cheek / 2, zz1], np.r_[q0 + n * s * cheek / 2, zz0]])
            F = [[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6], [3, 2, 6], [3, 6, 7], [0, 3, 7], [0, 7, 4], [1, 5, 6], [1, 6, 2]]
            Pc = P.mean(0); F2 = []
            for t in F:
                fn = np.cross(P[t[1]] - P[t[0]], P[t[2]] - P[t[0]])
                F2.append(t if fn @ (P[t].mean(0) - Pc) > 0 else t[::-1])
            B.add(P, F2, cheek_mat, tag=tag)
    if walk:
        P = np.array([np.r_[p0 - n * width / 2, z0], np.r_[p1 - n * width / 2, z1], np.r_[p1 + n * width / 2, z1], np.r_[p0 + n * width / 2, z0]])
        B.add(P, [[0, 1, 2], [0, 2, 3]], 'stone', tag='walk')
    return k

def ishigaki(B, pts, ztop, zbot, batter=0.25, mat='stone', tag='main', seed=0, cap=True):
    """a battered stone retaining wall along a plan polyline: ztop(x, y) / zbot(x, y) callables (or numbers); the face
    leans back by `batter` (m per m).  Face to the right of the polyline direction (the low side)."""
    pts = [v2(p) for p in pts]
    zt = ztop if callable(ztop) else (lambda x, y: ztop)
    zb = zbot if callable(zbot) else (lambda x, y: zbot)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; L = float(np.linalg.norm(b - a))
        if L < 0.05: continue
        d = (b - a) / L; n = -perp(d)              # outward (right side)
        m = max(1, int(L / 1.5))
        for j in range(m):
            p = a + d * L * j / m; q = a + d * L * (j + 1) / m
            tp, tq = zt(*p), zt(*q); bp, bq = zb(*p), zb(*q)
            hp, hq = max(0.2, tp - bp), max(0.2, tq - bq)
            P = np.array([np.r_[p + n * batter * hp, bp - 0.2], np.r_[q + n * batter * hq, bq - 0.2], np.r_[q, tq], np.r_[p, tp]])
            I = [[0, 1, 2], [0, 2, 3]]
            fn = np.cross(P[1] - P[0], P[2] - P[0])
            if fn[:2] @ n < 0: I = [[0, 2, 1], [0, 3, 2]]
            Lq = L / m
            B.add(P, I, mat, UV=np.array([[0, bp], [Lq, bq], [Lq, tq], [0, tp]]), tag=tag, c1=(0, 3, seed % 251, 0))
            if cap:
                prim.obox(B, np.r_[p - n * 0.25, tp + 0.08], np.r_[q - n * 0.25, tq + 0.08], 0.6, 0.18, mat, tag=tag)

# ------------------------------------------------------------------ walk / block helpers
def walk_poly(B, ring, z):
    """a flat (or z(x, y)) walk surface over a polygon (earcut)"""
    import mapbox_earcut as earcut
    V = np.asarray(ring, float)[:, :2]
    I = earcut.triangulate_float64(V, np.array([len(V)], np.uint32)).reshape(-1, 3)
    Z = np.array([z(x, y) for x, y in V]) if callable(z) else np.full(len(V), z)
    B.add(np.c_[V, Z], I, 'stone', tag='walk')

def walk_grid(B, ring, zfn, res=0.5):
    """a walk surface following zfn(x, y) over a polygon, sampled on a grid"""
    import shapely
    from shapely.geometry import Polygon
    Pg = Polygon(ring)
    x0, y0, x1, y1 = Pg.bounds
    xs = np.arange(x0, x1 + res, res); ys = np.arange(y0, y1 + res, res)
    X, Y = np.meshgrid(xs, ys)
    Z = zfn(X, Y)
    ins = shapely.contains_xy(Pg.buffer(res * 0.75), X, Y)
    nx = len(xs); I = []
    for j in range(len(ys) - 1):
        for i in range(nx - 1):
            if ins[j, i] and ins[j, i + 1] and ins[j + 1, i] and ins[j + 1, i + 1]:
                a = j * nx + i
                I += [[a, a + 1, a + nx + 1], [a, a + nx + 1, a + nx]]
    if I: B.add(np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1), I, 'stone', tag='walk')

def block_line(B, pts, w=0.6, z=0.0):
    """a blocker strip along a plan polyline (railings, fences, walls)"""
    pts = [v2(p) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if np.linalg.norm(b - a) < 0.05: continue
        d = unit(b - a); n = perp(d) * w / 2
        e = d * w / 4
        P = np.array([np.r_[a - n - e, z], np.r_[b - n + e, z], np.r_[b + n + e, z], np.r_[a + n - e, z]])
        B.add(P, [[0, 1, 2], [0, 2, 3]], 'stone', tag='block')

def block_poly(B, ring, z=0.0):
    import mapbox_earcut as earcut
    V = np.asarray(ring, float)[:, :2]
    I = earcut.triangulate_float64(V, np.array([len(V)], np.uint32)).reshape(-1, 3)
    B.add(np.c_[V, np.full(len(V), z)], I, 'stone', tag='block')

def rect(cx, cy, hu, hv):
    return [(cx - hu, cy - hv), (cx + hu, cy - hv), (cx + hu, cy + hv), (cx - hu, cy + hv)]

def frame_ring(F, ring):
    """local ring -> world (uses the Frame's matrix)"""
    M = F.M
    return [tuple((M[:2, :2] @ np.asarray(p, float)) + M[:2, 3]) for p in ring]

# ------------------------------------------------------------------ preview tree proxies (Blender only, not exported)
TREE_LOOK = {0: ((0.75, 0.12, 0.04), 'dome', 6.5), 1: ((0.85, 0.65, 0.1), 'oval', 14), 2: ((0.25, 0.32, 0.12), 'spread', 7.5), 3: ((0.55, 0.35, 0.1), 'vase', 15),
             4: ((0.06, 0.16, 0.06), 'pads', 7.5), 5: ((0.05, 0.12, 0.05), 'cone', 22), 6: ((0.06, 0.13, 0.05), 'cone', 18), 7: ((0.07, 0.16, 0.05), 'round', 11),
             8: ((0.3, 0.4, 0.12), 'weep', 8.5), 9: ((0.12, 0.25, 0.08), 'mound', 1.1), 10: ((0.2, 0.35, 0.1), 'cone', 11)}

def preview_trees(trees, name='preview_trees'):
    """low-poly crowns for the EEVEE previews (the viewer draws its own trees)"""
    import bpy
    rng = np.random.default_rng(7)
    by = {}
    for (sp, x, y, z, s, yaw) in trees:
        col, shape, H = TREE_LOOK.get(int(sp), ((0.1, 0.2, 0.08), 'round', 9))
        if int(sp) == 0:
            col = [(0.78, 0.1, 0.03), (0.85, 0.3, 0.04), (0.7, 0.06, 0.04), (0.9, 0.5, 0.08)][int(rng.integers(4))]
        H = H * s
        R = {'cone': 0.22, 'dome': 0.55, 'spread': 0.6, 'vase': 0.42, 'oval': 0.3, 'pads': 0.45, 'round': 0.45, 'weep': 0.45, 'mound': 0.9}.get(shape, 0.45) * H
        zc = {'cone': 0.55, 'dome': 0.62, 'mound': 0.5}.get(shape, 0.6) * H
        hz = {'cone': 0.5, 'mound': 0.5}.get(shape, 0.4) * H
        key = tuple(np.round(col, 3))
        V, F, tr = by.setdefault(key, ([], [], []))
        base = len(V)
        nseg = 7
        prof = [(0.0, -1.0), (0.75, -0.6), (1.0, 0.0), (0.75, 0.6), (0.0, 1.0)] if shape != 'cone' else [(0.0, -1.0), (1.0, -0.8), (0.55, 0.0), (0.0, 1.0)]
        for (r, h) in prof:
            for i in range(nseg):
                a = TAU * i / nseg + yaw
                V.append((x + math.cos(a) * r * R, y + math.sin(a) * r * R, z + zc + h * hz))
        nr = len(prof)
        for j in range(nr - 1):
            for i in range(nseg):
                a = base + j * nseg + i; b = base + j * nseg + (i + 1) % nseg
                F.append((a, b, b + nseg, a + nseg))
        # trunk
        tb = len(V)
        for (zz, rr) in ((0, 0.12 * s + 0.08), (zc, 0.06 * s + 0.04)):
            for i in range(4):
                a = TAU * i / 4
                V.append((x + math.cos(a) * rr, y + math.sin(a) * rr, z + zz))
        for i in range(4):
            F.append((tb + i, tb + (i + 1) % 4, tb + 4 + (i + 1) % 4, tb + 4 + i))
    col = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(col)
    for key, (V, F, _) in by.items():
        me = bpy.data.meshes.new(name); me.from_pydata(V, [], F); me.update()
        mat = bpy.data.materials.new(f'{name}_{key}'); mat.use_nodes = True
        bs = mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value = (*key, 1); bs.inputs['Roughness'].default_value = 0.9
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    return col

# ------------------------------------------------------------------ roof intersections: keep the upper envelope
class TriZ:
    """z lookup on a set of triangles (k, 3, 3) by plan position: the max z of the triangles covering a point"""
    def __init__(self, T, cell=1.0):
        self.T = np.asarray(T, float); self.cell = cell
        mn = self.T[:, :, :2].min(1); mx = self.T[:, :, :2].max(1)
        self.grid = {}
        for i, (a, b) in enumerate(zip(mn, mx)):
            for gx in range(int(math.floor(a[0] / cell)), int(math.floor(b[0] / cell)) + 1):
                for gy in range(int(math.floor(a[1] / cell)), int(math.floor(b[1] / cell)) + 1):
                    self.grid.setdefault((gx, gy), []).append(i)
    def z(self, P):
        P = np.atleast_2d(P); out = np.full(len(P), -1e9)
        for k, p in enumerate(P):
            ids = self.grid.get((int(math.floor(p[0] / self.cell)), int(math.floor(p[1] / self.cell))))
            if not ids: continue
            t = self.T[ids]
            a, b, c = t[:, 0], t[:, 1], t[:, 2]
            v0 = c[:, :2] - a[:, :2]; v1 = b[:, :2] - a[:, :2]; v2_ = p[:2] - a[:, :2]
            d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2_ * v0).sum(1); d21 = (v2_ * v1).sum(1)
            den = d00 * d11 - d01 * d01; den[np.abs(den) < 1e-12] = 1e-12
            u = (d11 * d20 - d01 * d21) / den; v = (d00 * d21 - d01 * d20) / den
            ins = (u >= -1e-4) & (v >= -1e-4) & (u + v <= 1 + 1e-4)
            if ins.any():
                zz = a[:, 2] + u * (c[:, 2] - a[:, 2]) + v * (b[:, 2] - a[:, 2])
                out[k] = zz[ins].max()
        return out

def tris_of(Bsrc, mats=None, tags=('main',)):
    T = []
    for p in Bsrc.parts:
        if p['tag'] not in tags or (mats and p['mat'] not in mats): continue
        T.append(p['P'][p['I']])
    return np.concatenate(T) if T else np.zeros((0, 3, 3))

def cull_below(Bsrc, Z, mats=None, eps=0.02, tags=('main', 'detail')):
    """drop triangles of Bsrc (parts with the given materials) whose centroid lies below the surface Z (TriZ)"""
    for p in Bsrc.parts:
        if p['tag'] not in tags or (mats and p['mat'] not in mats): continue
        C = p['P'][p['I']].mean(1)
        zz = Z.z(C)
        keep = C[:, 2] >= zz - eps
        if not keep.all():
            compact(p, p['I'][keep])

def compact(p, I):
    """keep only the vertices a part's new index list uses"""
    vid, inv = np.unique(I.ravel(), return_inverse=True)
    for k in ('P', 'N', 'UV', 'c0', 'c1'): p[k] = p[k][vid]
    p['I'] = inv.reshape(-1, 3).astype(np.int64)

def merge_into(B, Bsrc):
    for p in Bsrc.parts:
        if len(p['I']): B.parts.append(p)
    B.lamps += Bsrc.lamps; B.trees += Bsrc.trees

def soffit_ring(B, uc, vc, a, c, w, z, mat, tag='main'):
    """a flat ceiling ring (軒天井) under the bracket zone: from the wall rectangle (half sizes a, c) out by w, facing down"""
    inner = [(uc - a, vc - c), (uc + a, vc - c), (uc + a, vc + c), (uc - a, vc + c)]
    outer = [(uc - a - w, vc - c - w), (uc + a + w, vc - c - w), (uc + a + w, vc + c + w), (uc - a - w, vc + c + w)]
    for i in range(4):
        j = (i + 1) % 4
        P = np.array([np.r_[inner[i], z], np.r_[inner[j], z], np.r_[outer[j], z], np.r_[outer[i], z]])
        I = [[0, 1, 2], [0, 2, 3]]
        if np.cross(P[1] - P[0], P[2] - P[0])[2] > 0: I = [[0, 2, 1], [0, 3, 2]]
        B.add(P, I, mat, tag=tag)

def restyle(Bsrc, mapping):
    """change materials of a builder's parts (e.g. a roof built with the kit, re-dressed in stone)"""
    for p in Bsrc.parts:
        if p['mat'] in mapping: p['mat'] = mapping[p['mat']]
