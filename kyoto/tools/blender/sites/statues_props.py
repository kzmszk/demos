"""statues_props — explicit (non-SDF) geometry for the statues: lotus pedestals, octagonal plinths, halos and
rod sunbursts, rods and staffs, ribbons (天衣, 冠繒), beads, small held attributes (法具), drums.

Everything goes into an XM: an accumulator of triangles with per-face LABELS (palette slots, see statues_body.L)
and smooth normals.  Builders take `q` (quality 0..1: 1 = LOD0, ~0.4 = LOD1, ~0.15 = LOD2) to choose segments."""
import math
import numpy as np
from .statues_body import L, A, nrm, frame, rot, spline

F32 = np.float32

class XM:
    def __init__(self):
        self.P = []; self.T = []; self.N = []; self.Lb = []; self.n = 0
    def add(self, P, T, lab, N=None, smooth=True):
        P = np.asarray(P, float).reshape(-1, 3); T = np.asarray(T, np.int64).reshape(-1, 3)
        if len(T) == 0: return
        if N is None:
            if smooth:
                fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
                N = np.zeros_like(P)
                for k in range(3): np.add.at(N, T[:, k], fn)
            else:
                fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
                P = P[T.reshape(-1)]; N = np.repeat(fn, 3, 0); T = np.arange(len(P)).reshape(-1, 3)
        N = np.asarray(N, float); l = np.linalg.norm(N, axis=1, keepdims=True); l[l == 0] = 1; N = N / l
        lab = L[lab] if isinstance(lab, str) else lab
        self.P.append(P); self.T.append(T); self.N.append(N); self.Lb.append(np.full(len(T), lab, np.int32)); self.n += len(P)
    def merge(self, o, R=None, t=None):
        for P, T, N, Lb in zip(o.P, o.T, o.N, o.Lb):
            PP = P if R is None else P @ np.asarray(R).T + (0 if t is None else np.asarray(t))
            NN = N if R is None else N @ np.asarray(R).T
            T0 = T[:, ::-1] if (R is not None and np.linalg.det(R) < 0) else T
            self.P.append(PP); self.T.append(T0.copy()); self.N.append(NN); self.Lb.append(Lb.copy()); self.n += len(PP)
    def shift(self, v):
        self.P = [p + np.asarray(v, float) for p in self.P]
    def arrays(self):
        if not self.P: return None
        off = np.cumsum([0] + [len(p) for p in self.P[:-1]])
        return (np.concatenate(self.P).astype(F32), np.concatenate([t + o for t, o in zip(self.T, off)]).astype(np.int32),
                np.concatenate(self.N).astype(F32), np.concatenate(self.Lb))
    def ntri(self): return int(sum(len(t) for t in self.T))

# ---------------------------------------------------------------------------------------------- shapes
def grid_tris(nu, nv, wrap_u=False):
    """triangles of a (nv+1) x (nu+1 or nu if wrap) vertex grid, rows along v"""
    cols = nu if wrap_u else nu + 1
    T = []
    for j in range(nv):
        for i in range(nu):
            a = j * cols + i; b = j * cols + (i + 1) % cols if wrap_u else j * cols + i + 1
            c = a + cols; d = b + cols
            T += [(a, b, d), (a, d, c)]
    return np.array(T, np.int64)

def lathe(xm, c, prof, seg, lab, phase=0.0, ngon=False, smooth=True):
    """surface of revolution about z through c; prof [(r, z)] bottom->top (outward facing). ngon: flat facets"""
    c = np.asarray(c, float); prof = np.asarray(prof, float)
    th = phase + 2 * math.pi * np.arange(seg) / seg
    if ngon:
        for i in range(seg):
            t0, t1 = th[i], th[(i + 1) % seg]
            P = [];
            for (r, z) in prof:
                P += [c + (r * math.cos(t0), r * math.sin(t0), z), c + (r * math.cos(t1), r * math.sin(t1), z)]
            T = []
            for j in range(len(prof) - 1):
                a = 2 * j; T += [(a, a + 1, a + 3), (a, a + 3, a + 2)]
            xm.add(P, T, lab, smooth=False)
        return
    P = np.array([c + (r * math.cos(t), r * math.sin(t), z) for (r, z) in prof for t in th])
    xm.add(P, grid_tris(seg, len(prof) - 1, wrap_u=True), lab, smooth=smooth)

def disc(xm, c, n, r, lab, seg=24, r_in=0.0):
    c = np.asarray(c, float); R = frame(z=n, x=np.cross(n, (0, 0, 1)) if abs(nrm(n)[2]) < 0.9 else (1, 0, 0))
    th = 2 * math.pi * np.arange(seg) / seg
    if r_in <= 0:
        P = np.vstack([c, [c + R @ (r * math.cos(t), r * math.sin(t), 0) for t in th]])
        T = [(0, 1 + i, 1 + (i + 1) % seg) for i in range(seg)]
    else:
        P = np.array([c + R @ (rr * math.cos(t), rr * math.sin(t), 0) for rr in (r_in, r) for t in th])
        T = grid_tris(seg, 1, wrap_u=True)
    xm.add(P, T, lab, N=np.tile(R[:, 2], (len(P), 1)))

def tube(xm, path, radius, seg, lab, caps=True, ups=None):
    """sweep a circle (seg sides) along a path; radius scalar or per point"""
    path = np.asarray(path, float); n = len(path)
    r = np.broadcast_to(np.asarray(radius, float), (n,))
    tang = np.gradient(path, axis=0); tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-9)
    # parallel transport frame
    u0 = np.cross(tang[0], (0, 0, 1)) if abs(tang[0][2]) < 0.95 else np.cross(tang[0], (1, 0, 0))
    u0 = nrm(u0); U = [u0]
    for i in range(1, n):
        u = U[-1] - tang[i] * (U[-1] @ tang[i]); U.append(nrm(u) if np.linalg.norm(u) > 1e-9 else U[-1])
    U = np.array(U); V = np.cross(tang, U)
    th = 2 * math.pi * np.arange(seg) / seg
    ct, st = np.cos(th), np.sin(th)
    ring = U[:, None, :] * ct[None, :, None] + V[:, None, :] * st[None, :, None]
    P = (path[:, None, :] + ring * r[:, None, None]).reshape(-1, 3)
    N = ring.reshape(-1, 3)
    xm.add(P, grid_tris(seg, n - 1, wrap_u=True), lab, N=N)
    if caps:
        for k, s in ((0, -1), (n - 1, 1)):
            if r[k] < 1e-5: continue
            C = np.vstack([path[k], path[k] + ring[k] * r[k]])
            T = [(0, 1 + (i + 1) % seg, 1 + i) if s < 0 else (0, 1 + i, 1 + (i + 1) % seg) for i in range(seg)]
            xm.add(C, T, lab, N=np.tile(tang[k] * s, (len(C), 1)))

def ribbon(xm, path, width, thick, ups, lab, twist=None):
    """a flat band (scarf) along a path: width/thick scalars or per point; ups: the band's normal direction per point"""
    path = np.asarray(path, float); n = len(path)
    def fit(v):
        v = np.atleast_1d(np.asarray(v, float))
        if len(v) == n: return v
        if len(v) == 1: return np.full(n, v[0])
        return np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(v)), v)
    w = fit(width); t = fit(thick)
    ups = np.asarray(ups, float); ups = np.tile(ups, (n, 1)) if ups.ndim == 1 else ups
    tang = np.gradient(path, axis=0); tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-9)
    up = ups - tang * (ups * tang).sum(1, keepdims=True); up /= np.maximum(np.linalg.norm(up, axis=1, keepdims=True), 1e-9)
    side = np.cross(tang, up)
    # 6 points around a lens-like section: (-w,0) (-w/2, t) (w/2, t) (w, 0) (w/2, -t) (-w/2, -t)
    sec = [(-1, 0), (-0.5, 1), (0.5, 1), (1, 0), (0.5, -1), (-0.5, -1)]
    nsec = [(-1, 0), (-0.25, 1), (0.25, 1), (1, 0), (0.25, -1), (-0.25, -1)]
    P = []; N = []
    for i in range(n):
        for (a, b), (na, nb) in zip(sec, nsec):
            P.append(path[i] + side[i] * a * w[i] + up[i] * b * t[i]); N.append(side[i] * na + up[i] * nb)
    xm.add(P, grid_tris(6, n - 1, wrap_u=True), lab, N=N)

def octa_plinth(xm, c, r, steps, lab, lab2=None, phase=math.pi / 8, sides=8):
    """stacked polygonal plates: steps [(r_rel, z0, z1)] -> flat-shaded slabs with tops"""
    c = np.asarray(c, float)
    for k, (rr, z0, z1) in enumerate(steps):
        R = r * rr
        prof = [(0.0, z0), (R, z0), (R, z1), (0.0, z1)]
        lathe(xm, c, prof, sides, lab if (lab2 is None or k % 2 == 0) else lab2, phase=phase, ngon=True)

def petal(xm, base, out, up, length, width, thick, lab, bend=0.4, nu=4, nv=6, tip=0.8):
    """a lotus petal: pointed, cupped, thick-edged (closed lens), from base toward `out` curving up by `bend`"""
    base = np.asarray(base, float); out = nrm(out); up = nrm(np.asarray(up, float) - out * (np.asarray(up, float) @ out)); side = np.cross(up, out)
    us = np.linspace(-1, 1, nu * 2 + 1); vs = np.linspace(0, 1, nv + 1)
    top = []; bot = []
    for v in vs:
        ang = bend * v * math.pi / 2
        d = out * math.cos(ang) + up * math.sin(ang); nn = -out * math.sin(ang) + up * math.cos(ang)
        cen = base + (out * math.sin(ang) + up * (1 - math.cos(ang))) * length / max(bend * math.pi / 2, 1e-6) if bend > 1e-3 else base + out * v * length
        hw = width * (math.sin(math.pi * min(v ** tip, 1.0)) ** 0.7 * 0.92 + 0.08 * (1 - v))
        for uu in us:
            cup = (uu * uu) * 0.25 * width
            th = thick * math.sqrt(max(1 - uu * uu, 0)) * (1 - 0.6 * v)
            p = cen + side * uu * hw + nn * (cup)
            top.append(p + nn * th); bot.append(p - nn * th)
    nu2 = len(us)
    P = np.array(top + bot)
    T1 = grid_tris(nu2 - 1, nv)
    T2 = grid_tris(nu2 - 1, nv)[:, ::-1] + len(top)
    xm.add(P, np.vstack([T1, T2]), lab)

def lotus_seat(xm, c, r_top, h, tiers, per, lab, q=1.0, flare=1.0, lab_core='ped'):
    """蓮華座: a bowl of petals in tiers (outer tiers lower and more open), a core drum under them"""
    c = np.asarray(c, float)
    nu = 2 if q > 0.6 else 1; nv = 4 if q > 0.6 else 2
    lathe(xm, c, [(0, 0), (r_top * 0.55, 0), (r_top * 0.85, h * 0.35), (r_top * 0.95, h * 0.85), (r_top * 0.92, h), (0, h)], 16 if q > 0.5 else 8, lab_core)
    for t in range(tiers):
        f = t / max(tiers - 1, 1)                  # 0 = innermost / top
        n = per
        for i in range(n):
            a = 2 * math.pi * (i + 0.5 * (t % 2)) / n
            dirr = np.array([math.cos(a), math.sin(a), 0])
            base = c + dirr * r_top * (0.45 + 0.25 * f) + np.array([0, 0, h * (0.55 - 0.5 * f)])
            L_ = h * (0.75 + 0.35 * f) * flare
            W = 2 * math.pi * r_top * (0.55 + 0.35 * f) / n * 0.75
            petal(xm, base, dirr * (0.35 + 0.4 * f) + np.array([0, 0, 1]) * (1 - 0.4 * f), np.array([0, 0, 1]) - dirr, L_, W, L_ * 0.05, lab, bend=0.35 + 0.2 * f, nu=nu, nv=nv)

def kaeribana(xm, c, r, h, n, lab, q=1.0):
    """反花: downward-turned petals around a low drum"""
    c = np.asarray(c, float)
    nu = 1; nv = 3 if q > 0.5 else 2
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        d = np.array([math.cos(a), math.sin(a), 0])
        petal(xm, c + d * r * 0.55 + np.array([0, 0, h * 0.9]), d * 1.0 - np.array([0, 0, 0.6]), np.array([0, 0, 1.0]), r * 0.62, 2 * math.pi * r * 0.6 / n * 0.7, h * 0.12, lab, bend=-0.25, nu=nu, nv=nv)
    lathe(xm, c, [(r * 0.7, 0), (r * 0.72, h * 0.3), (r * 0.5, h), (0, h)], 16 if q > 0.5 else 8, 'ped2')

def sunburst(xm, c, R, n_rods, r_in, r_out, rod_r, lab, q=1.0, ring_r=None, disc_r=None, seed=0, knob=True, up_long=1.25, tilt=0.0):
    """光背 of the standing Kannon: head-halo disc, a big ring and straight rods radiating from behind the head"""
    c = np.asarray(c, float); Rm = np.asarray(R, float)      # Rm columns: right, normal (backward-facing plane), up
    rng = np.random.default_rng(seed)
    seg = 4 if q < 0.5 else 5
    for i in range(n_rods):
        a = 2 * math.pi * (i + 0.5) / n_rods
        if abs(math.sin(a)) > 0 and math.sin(a) < -0.55: continue       # none straight down behind the body
        d = Rm @ np.array([math.cos(a), 0, math.sin(a)])
        lo = r_out * (1 + (up_long - 1) * max(math.sin(a), 0)) * (0.92 + 0.12 * rng.random())
        p0 = c + d * r_in; p1 = c + d * lo
        tube(xm, [p0, p1], rod_r, seg, lab, caps=False)
        if knob and q > 0.3:
            tube(xm, [p1 - d * 0.004, p1 + d * 0.022], [rod_r * 1.6, rod_r * 0.5], seg, lab, caps=True)
    if ring_r:
        th = np.linspace(0, 2 * math.pi, 49 if q > 0.5 else 25)
        path = [c + Rm @ np.array([math.cos(t), 0, math.sin(t)]) * ring_r for t in th]
        tube(xm, path, rod_r * 1.6, seg, lab, caps=False)
    if disc_r:
        nseg = 32 if q > 0.5 else 16
        disc(xm, c - Rm[:, 1] * 0.004, -Rm[:, 1], disc_r, lab, seg=nseg)
        disc(xm, c - Rm[:, 1] * 0.012, Rm[:, 1], disc_r, lab, seg=nseg)
        th = np.linspace(0, 2 * math.pi, nseg + 1)
        tube(xm, [c - Rm[:, 1] * 0.008 + Rm @ np.array([math.cos(t), 0, math.sin(t)]) * disc_r for t in th], 0.007, 6 if q > 0.5 else 4, lab, caps=False)

def flame_ring(xm, c, Rm, r, n, lab, q=1.0, size=0.08):
    """輪光 with flame clusters (Taishakuten, Kendatsuba...): a ring of tube plus flame tongues"""
    c = np.asarray(c, float)
    th = np.linspace(0, 2 * math.pi, 41 if q > 0.5 else 21)
    tube(xm, [c + Rm @ np.array([math.cos(t), 0, math.sin(t)]) * r for t in th], size * 0.09, 6 if q > 0.5 else 4, lab, caps=False)
    for (ang, sc) in ((90, 1.4), (20, 0.9), (160, 0.9))[:n]:
        a = math.radians(ang); d = Rm @ np.array([math.cos(a), 0, math.sin(a)])
        flame(xm, c + d * r, d, Rm[:, 1], size * sc, lab, q)

def flame(xm, base, up, normal, size, lab, q=1.0):
    """a cluster of flame tongues (火焔) as flattened tubes curling up"""
    base = np.asarray(base, float); up = nrm(up); nml = nrm(np.asarray(normal, float) - up * (np.asarray(normal, float) @ up)); side = np.cross(up, nml)
    for k, (dx, h, cur) in enumerate(((0, 1.0, 0.0), (-0.45, 0.7, -0.6), (0.45, 0.7, 0.6), (-0.8, 0.45, -1.0), (0.8, 0.45, 1.0))):
        pts = []
        for t in np.linspace(0, 1, 7 if q > 0.5 else 4):
            pts.append(base + side * size * (dx * 0.5 + cur * 0.35 * t * t + 0.12 * math.sin(t * 5 + k)) + up * size * h * t * 1.3)
        w = size * 0.22 * (1 - np.linspace(0, 1, len(pts)) ** 1.5) + 0.002
        ribbon(xm, pts, w, size * 0.04, nml, lab)

def beads(xm, path, r, lab, q=1.0, spacing=2.2):
    """a string of beads (瓔珞) as a tube with bulges"""
    path = np.asarray(path, float)
    if q < 0.3:
        tube(xm, path, r * 0.8, 3, lab, caps=False); return
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1); s = np.r_[0, np.cumsum(seg)]
    n = max(int(s[-1] / (r * spacing)), 2)
    ss = np.linspace(0, s[-1], n * 3 + 1)
    pts = np.stack([np.interp(ss, s, path[:, k]) for k in range(3)], 1)
    rad = r * (0.55 + 0.45 * np.abs(np.sin(np.arange(len(ss)) * math.pi / 3)))
    tube(xm, pts, rad, 5 if q > 0.6 else 4, lab, caps=False)

# ---------------------------------------------------------------------------------------------- held attributes (持物)
def attribute(xm, kind, M, t, s, lab='attr', q=1.0):
    """a small held object in a hand frame: M columns (finger dir, thumb side, back of hand), t = grip point; s = size (m)"""
    M = np.asarray(M, float); t = np.asarray(t, float)
    up = -M[:, 2]          # out of the palm
    ax = M[:, 1]           # through the fist (thumb side)
    fd = M[:, 0]
    seg = 5 if q > 0.6 else 4
    def W(v): return t + M @ np.asarray(v, float)
    if kind == 'rod':          # short staff / vajra-like rod through the fist
        tube(xm, [t - ax * s * 0.6, t + ax * s * 1.4], s * 0.05, seg, lab)
        tube(xm, [t + ax * s * 1.4, t + ax * s * 1.55], [s * 0.09, 0.001], seg, lab)
    elif kind == 'sword':
        tube(xm, [t - ax * s * 0.35, t + ax * s * 0.25], s * 0.06, seg, lab)
        tube(xm, [t + ax * s * 0.25, t + ax * s * 0.3], s * 0.16, seg, lab)
        bl = [t + ax * s * (0.3 + 1.6 * k / 6) for k in range(7)]
        ribbon(xm, bl, [s * 0.09] * 6 + [0.002], s * 0.02, up, lab)
    elif kind == 'vajra':
        tube(xm, [t - ax * s * 0.45, t + ax * s * 0.45], s * 0.07, seg, lab)
        for e in (-1, 1):
            for k in range(3):
                a = 2 * math.pi * k / 3
                o = (fd * math.cos(a) + up * math.sin(a)) * s * 0.12
                tube(xm, [t + ax * e * s * 0.45, t + ax * e * s * 0.55 + o, t + ax * e * s * 0.75], s * 0.03, 4, lab, caps=False)
    elif kind == 'jewel':      # 宝珠 on the palm
        c = t + up * s * 0.35
        lathe(xm, c, [(0, -0.3 * s), (0.2 * s, -0.25 * s), (0.3 * s, 0), (0.22 * s, 0.25 * s), (0.08 * s, 0.4 * s), (0, 0.5 * s)], seg, lab)
    elif kind == 'wheel':      # 宝輪
        c = t + ax * s * 0.5; n = nrm(fd)
        th = np.linspace(0, 2 * math.pi, 3 * seg + 1)
        Rr = frame(z=n, x=ax)
        tube(xm, [c + Rr @ (0.35 * s * math.cos(a), 0.35 * s * math.sin(a), 0) for a in th], s * 0.045, 4, lab, caps=False)
        for k in range(8 if q > 0.5 else 4):
            a = 2 * math.pi * k / (8 if q > 0.5 else 4)
            tube(xm, [c, c + Rr @ (0.35 * s * math.cos(a), 0.35 * s * math.sin(a), 0)], s * 0.025, 3, lab, caps=False)
        tube(xm, [t - ax * s * 0.1, c - Rr @ (0, 0.35 * s, 0)], s * 0.04, 4, lab)
    elif kind == 'disc':       # 日精 / 月精 / 宝鏡
        c = t + ax * s * 0.55; n = nrm(fd + up * 0.3)
        lathe(xm, c, [(0, -0.03 * s), (0.3 * s, -0.03 * s), (0.32 * s, 0.0), (0.3 * s, 0.03 * s), (0, 0.03 * s)], 3 * seg, lab) if False else None
        Rr = frame(z=n, x=ax)
        P = []; th = np.linspace(0, 2 * math.pi, 3 * seg, endpoint=False)
        disc(xm, c + n * 0.02 * s, n, 0.3 * s, lab, seg=3 * seg); disc(xm, c - n * 0.02 * s, -n, 0.3 * s, lab, seg=3 * seg)
        tube(xm, [c + Rr @ (0.3 * s * math.cos(a), 0.3 * s * math.sin(a), 0) for a in np.r_[th, th[:1]]], 0.03 * s, 4, lab, caps=False)
        tube(xm, [t - ax * s * 0.15, c - ax * 0.3 * s], s * 0.04, 4, lab)
    elif kind == 'lotus':      # 蓮華 on a stem
        top = t + ax * s * 1.1 + up * s * 0.2
        tube(xm, [t - ax * s * 0.2, t + ax * s * 0.5, top], s * 0.035, 4, lab, caps=False)
        for k in range(6 if q > 0.5 else 4):
            a = 2 * math.pi * k / (6 if q > 0.5 else 4)
            Rr = frame(z=nrm(top - t), x=fd)
            d = Rr @ (math.cos(a), math.sin(a), 0.0)
            petal(xm, top, d * 0.4 + nrm(top - t), nrm(top - t), s * 0.35, s * 0.18, s * 0.02, lab, bend=0.3, nu=1, nv=2)
    elif kind == 'vase':       # 宝瓶 / 鉢
        c = t + up * s * 0.05
        Rr = frame(z=up, x=fd)
        prof = [(0.0, 0), (0.18, 0.02), (0.3, 0.18), (0.28, 0.4), (0.12, 0.55), (0.1, 0.7), (0.16, 0.78), (0.0, 0.8)]
        P = []; th = 2 * math.pi * np.arange(seg) / seg
        for (r, z) in prof:
            for a in th: P.append(c + Rr @ (r * s * math.cos(a), r * s * math.sin(a), z * s))
        xm.add(P, grid_tris(seg, len(prof) - 1, wrap_u=True), lab)
    elif kind == 'bowl':
        c = t + up * s * 0.02
        Rr = frame(z=up, x=fd)
        prof = [(0.0, 0), (0.3, 0.02), (0.48, 0.15), (0.5, 0.3), (0.42, 0.3), (0.38, 0.18), (0.0, 0.12)]
        th = 2 * math.pi * np.arange(2 * seg) / (2 * seg); P = []
        for (r, z) in prof:
            for a in th: P.append(c + Rr @ (r * s * math.cos(a), r * s * math.sin(a), z * s))
        xm.add(P, grid_tris(2 * seg, len(prof) - 1, wrap_u=True), lab)
    elif kind == 'rosary':
        c = t - fd * s * 0.1
        Rr = frame(z=fd, x=ax)
        th = np.linspace(0, 2 * math.pi, 17)
        beads(xm, [c + Rr @ (0.22 * s * math.cos(a), 0.22 * s * math.sin(a) - 0.5 * s * max(0, -math.sin(a)), 0) for a in th], 0.03 * s, lab, q)
    elif kind == 'trident':    # 戟 head
        tube(xm, [t - ax * s * 0.4, t + ax * s * 1.3], s * 0.04, 4, lab)
        h = t + ax * s * 1.3
        tube(xm, [h, h + ax * s * 0.45], [s * 0.06, 0.001], 4, lab)
        for e in (-1, 1):
            tube(xm, [h - ax * s * 0.05, h + fd * e * s * 0.18, h + fd * e * s * 0.2 + ax * s * 0.3], [s * 0.035, s * 0.03, 0.001], 4, lab, caps=False)
    elif kind == 'bell':
        tube(xm, [t - ax * s * 0.3, t + ax * s * 0.5], s * 0.05, 4, lab)
        c = t + ax * s * 0.5
        Rr = frame(z=-ax, x=fd)
        prof = [(0.0, -0.05), (0.12, 0.0), (0.18, 0.25), (0.25, 0.45), (0.0, 0.45)]
        P = []; th = 2 * math.pi * np.arange(seg) / seg
        for (r, z) in prof:
            for a in th: P.append(c + Rr @ (r * s * math.cos(a), r * s * math.sin(a), -z * s - 0.0))
        xm.add(P, grid_tris(seg, len(prof) - 1, wrap_u=True), lab)
    elif kind == 'skull':
        c = t + up * s * 0.25
        lathe(xm, c, [(0, -0.2 * s), (0.17 * s, -0.12 * s), (0.22 * s, 0.05 * s), (0.15 * s, 0.2 * s), (0, 0.24 * s)], seg, lab)
    elif kind == 'branch':     # 楊柳
        tip = t + ax * s * 1.2 - up * s * 0.3
        tube(xm, [t - ax * s * 0.2, t + ax * s * 0.6, tip], s * 0.025, 3, lab, caps=False)
        for k in range(3):
            p0 = t + ax * s * (0.5 + 0.25 * k)
            ribbon(xm, [p0, p0 - up * s * 0.3 + fd * s * 0.1 * (k - 1), p0 - up * s * 0.6], [s * 0.05, s * 0.06, 0.002], s * 0.01, fd, lab)
    elif kind == 'conch':
        c = t + up * s * 0.2
        Rr = frame(z=fd, x=up)
        lathe(xm, c, [(0, -0.3 * s), (0.12 * s, -0.2 * s), (0.2 * s, 0.05 * s), (0.12 * s, 0.25 * s), (0, 0.4 * s)], seg, lab)
    elif kind == 'buddha':     # 化仏: tiny standing figure on the palm
        c = t + up * s * 0.05
        lathe(xm, c, [(0.0, 0), (0.12 * s, 0.0), (0.13 * s, 0.35 * s), (0.11 * s, 0.6 * s), (0.06 * s, 0.68 * s), (0.08 * s, 0.75 * s), (0.07 * s, 0.85 * s), (0, 0.9 * s)], seg, lab)
        disc(xm, c + np.array([0, -0.02 * s, 0.8 * s]), (0, 1, 0), 0.16 * s, lab, seg=12)
    elif kind == 'axe':
        tube(xm, [t - ax * s * 0.5, t + ax * s * 1.2], s * 0.04, 4, lab)
        h = t + ax * s * 1.1
        ribbon(xm, [h, h + fd * s * 0.35], [s * 0.15, s * 0.25], s * 0.03, up, lab)
    elif kind == 'arrow':
        tube(xm, [t - ax * s * 0.8, t + ax * s * 1.2], s * 0.025, 3, lab)
        tube(xm, [t + ax * s * 1.2, t + ax * s * 1.4], [s * 0.06, 0.001], 4, lab)
    elif kind == 'bow':
        pts = [t + ax * s * 1.5 * math.sin(a) + fd * s * 0.4 * (math.cos(a) - 1) * -1 for a in np.linspace(-1.2, 1.2, 9)]
        tube(xm, pts, s * 0.035, 4, lab, caps=True)
        tube(xm, [pts[0], pts[-1]], s * 0.008, 3, lab, caps=False)
    elif kind == 'sutra':
        c = t + up * s * 0.1
        Rr = frame(z=ax, x=fd)
        tube(xm, [c - ax * s * 0.35, c + ax * s * 0.35], s * 0.1, seg, lab)
    elif kind == 'cloud':
        c = t + up * s * 0.3
        for k in range(3):
            disc(xm, c + fd * s * 0.12 * (k - 1), up, s * 0.15, lab, seg=8)

ATTR_KINDS = ['jewel', 'wheel', 'disc', 'lotus', 'vase', 'rod', 'sword', 'vajra', 'rosary', 'trident', 'bell', 'skull',
              'branch', 'conch', 'buddha', 'axe', 'arrow', 'bow', 'sutra', 'cloud']
