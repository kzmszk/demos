"""銀閣寺 helpers: small parts the kit does not have (walls with openings, shoji, 舞良戸, 桟唐戸, 花頭窓, 跳高欄, rocks with
a subdivision level, clipped hedges, rough stone walls, path ribbons, stone steps on the terrain).

All functions add to a jk Builder in the builder's current frame (x, y, z = u, v, w of the frame)."""
import math
import numpy as np
from jk import prim

def rng(seed):
    return np.random.default_rng(seed)

# ------------------------------------------------------------------ elementary faces
def quad(B, a, b, c, d, mat, tag='main', uv=None, out=None, both=False, **kw):
    """a planar quad a-b-c-d; out: a 3D vector it should face (else as given, counter-clockwise from the front);
    both: two-sided"""
    P = np.array([a, b, c, d], float)
    I = [[0, 1, 2], [0, 2, 3]]
    if out is not None:
        fn = np.cross(P[1] - P[0], P[2] - P[0]) + np.cross(P[2] - P[0], P[3] - P[0])
        if fn @ np.asarray(out, float) < 0: I = [[0, 2, 1], [0, 3, 2]]
    B.add(P, I, mat, UV=uv, tag=tag, **kw)
    if both: B.add(P, [t[::-1] for t in I], mat, UV=uv, tag=tag, **kw)

def oadd(B, P, I, mat, out, **kw):
    """add triangles, each flipped to face `out` (a 3D vector)"""
    P = np.asarray(P, float); I = np.array(I, np.int64).reshape(-1, 3)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    flip = fn @ np.asarray(out, float) < 0
    I[flip] = I[flip][:, ::-1]
    B.add(P, I, mat, **kw)

def wall_plane(B, p0, p1, z0, z1, n_out, mat, off=0.0, holes=(), tag='main', **kw):
    """vertical wall rectangle over p0->p1 (2D), z0..z1, facing n_out (2D unit), moved by `off` along n_out.
    holes: list of rings [(s, z)] with s = distance from p0 along the wall.  uv = (s, z)."""
    import mapbox_earcut as earcut
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); n = np.asarray(n_out, float)
    d = p1 - p0; L = float(np.linalg.norm(d)); d = d / L
    rings = [np.array([(0, z0), (L, z0), (L, z1), (0, z1)], float)] + [np.asarray(h, float) for h in holes]
    V = np.concatenate(rings)
    ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    I = earcut.triangulate_float64(V, ends).reshape(-1, 3)
    P = np.c_[p0[0] + d[0] * V[:, 0] + n[0] * off, p0[1] + d[1] * V[:, 0] + n[1] * off, V[:, 1]]
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    if (fn[:, :2] @ n).sum() < 0: I = I[:, ::-1]
    B.add(P, I, mat, UV=V.copy(), tag=tag, **kw)

def to3(p0, d, n, s, z, off=0.0):
    return np.array([p0[0] + d[0] * s + n[0] * off, p0[1] + d[1] * s + n[1] * off, z])

def katomado_ring(sc, w, z0, z1, k=14):
    """花頭窓 outline in (s, z): bell-shaped, the sides flaring out at the sill, an ogee arch with two cusps on top"""
    h = z1 - z0
    pts = []
    # right side bottom -> top (s offsets from the centre sc)
    for t in np.linspace(0, 1, 6):
        zz = z0 + t * 0.62 * h
        hw = w / 2 * (1.0 - 0.10 * math.sin(t * math.pi / 2) ** 0.8)
        pts.append((sc + hw, zz))
    # shoulder: quarter circle into the cusp
    hw0 = w / 2 * 0.90; zc = z0 + 0.62 * h
    for t in np.linspace(0, 1, k // 2)[1:]:
        a = t * math.pi * 0.55
        pts.append((sc + hw0 - (1 - math.cos(a)) * w * 0.16, zc + math.sin(a) * h * 0.22))
    # cusp notch and the ogee to the peak
    s_c, z_c = pts[-1]
    pts.append((s_c - w * 0.035, z_c - h * 0.015))
    for t in np.linspace(0, 1, k // 2)[1:]:
        ss = (s_c - w * 0.035) * (1 - t) + sc * t
        zz = (z_c - h * 0.015) + (z1 - (z_c - h * 0.015)) * (math.sin(t * math.pi / 2) ** 1.4)
        pts.append((ss, zz))
    right = pts
    left = [(2 * sc - s, z) for (s, z) in right[::-1]][1:]
    return right + left            # counter-clockwise starting at the bottom right

# ------------------------------------------------------------------ fittings between two pillars (vertical plane p0 -> p1, outward n)
class Bay:
    """a bay between pillar centres p0, p1 (2D) facing n_out; helpers for fittings in its plane"""
    def __init__(self, B, p0, p1, n_out, r=0.09):
        self.B = B; self.p0 = np.asarray(p0, float); self.p1 = np.asarray(p1, float)
        d = self.p1 - self.p0; self.L = float(np.linalg.norm(d)); self.d = d / self.L
        self.n = np.asarray(n_out, float); self.r = r
    def P(self, s, z, off=0.0):
        return to3(self.p0, self.d, self.n, s, z, off)
    def hbar(self, s0, s1, zc, h, dpt, mat, off=0.0, tag='main'):
        """horizontal member, centre height zc, height h, depth dpt (centred on the plane + off)"""
        a = self.P(s0, zc, off); b = self.P(s1, zc, off)
        prim.obox(self.B, a, b, h, dpt, mat, up=(self.n[0], self.n[1], 0), tag=tag)
    def vbar(self, s, z0, z1, w, dpt, mat, off=0.0, tag='main'):
        a = self.P(s, z0, off); b = self.P(s, z1, off)
        prim.obox(self.B, a, b, w, dpt, mat, up=(self.n[0], self.n[1], 0), tag=tag)
    def plane(self, s0, s1, z0, z1, mat, off=0.0, holes=(), tag='main', **kw):
        a = self.P(s0, 0, 0); b = self.P(s1, 0, 0)
        hs = [[(s - s0, z) for (s, z) in h] for h in holes]
        wall_plane(self.B, a[:2], b[:2], z0, z1, self.n, mat, off=off, holes=hs, tag=tag, **kw)
    def box(self, s0, s1, z0, z1, off0, off1, mat, tag='main'):
        """a block in the wall: s0..s1 along, z0..z1, from off0 to off1 along n"""
        cs = [(s0, off0), (s1, off0), (s1, off1), (s0, off1)]
        pts = [self.P(s, 0, o)[:2] for (s, o) in cs]
        pts = np.array(pts)
        # make it CCW
        a = 0.5 * np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])
        if a < 0: pts = pts[::-1]
        prim.prism(self.B, pts, z0, z1, mat, tag=tag, bottom=True)

    # ---- fittings ---------------------------------------------------------------
    def shoji(self, s0, s1, z0, z1, n=2, koshi=0.0, off=0.0, frame='wood_dark', kumiko=(3, 7), tag='main', open_=None):
        """腰高障子: n sliding panels (white paper, kumiko lattice, frame); koshi = height of the wooden lower panel.
        open_ = index of a panel left out (slid behind its neighbour)"""
        W = (s1 - s0) / n
        for i in range(n):
            if open_ is not None and i == open_: continue
            a = s0 + i * W; b = a + W
            o = off + (0.012 if i % 2 else -0.012)
            self.plane(a + 0.03, b - 0.03, z0 + koshi + 0.03, z1 - 0.03, 'white_paint', off=o - 0.01, tag=tag)
            if koshi > 0: self.plane(a + 0.03, b - 0.03, z0 + 0.03, z0 + koshi, frame, off=o - 0.005, tag=tag)
            for (sa, sb) in ((a, a + 0.035), (b - 0.035, b)):
                self.box(sa, sb, z0, z1, o - 0.025, o + 0.012, frame, tag=tag)
            for zz in (z0 + 0.0, z1 - 0.04) + ((z0 + koshi,) if koshi > 0 else ()):
                self.box(a + 0.035, b - 0.035, zz, zz + 0.04, o - 0.022, o + 0.01, frame, tag=tag)
            nv, nh = kumiko
            for k in range(1, nv):
                ss = a + 0.035 + (W - 0.07) * k / nv
                self.box(ss - 0.007, ss + 0.007, z0 + koshi + 0.04, z1 - 0.04, o - 0.012, o + 0.0, frame, tag='detail')
            for k in range(1, nh):
                zz = z0 + koshi + 0.04 + (z1 - z0 - koshi - 0.08) * k / nh
                self.box(a + 0.035, b - 0.035, zz - 0.007, zz + 0.007, o - 0.012, o + 0.0, frame, tag='detail')

    def mairado(self, s0, s1, z0, z1, n=2, off=0.0, mat='wood_dark', slat=0.09, tag='main'):
        """舞良戸: board sliding doors with close horizontal slats"""
        W = (s1 - s0) / n
        for i in range(n):
            a = s0 + i * W; b = a + W
            o = off + (0.015 if i % 2 else -0.015)
            self.plane(a, b, z0, z1, mat, off=o - 0.01, tag=tag)
            for (sa, sb) in ((a, a + 0.05), (b - 0.05, b)):
                self.box(sa, sb, z0, z1, o - 0.03, o + 0.015, mat, tag=tag)
            for zz in (z0, z1 - 0.06):
                self.box(a + 0.05, b - 0.05, zz, zz + 0.06, o - 0.025, o + 0.012, mat, tag=tag)
            for zz in np.arange(z0 + 0.12, z1 - 0.1, slat):
                self.box(a + 0.05, b - 0.05, zz, zz + 0.016, o - 0.018, o + 0.008, mat, tag='detail')

    def boards(self, s0, s1, z0, z1, off=0.0, mat='wood_dark', batten=0.42, tag='main', holes=()):
        """板壁: a board wall with vertical cover strips (押縁)"""
        self.plane(s0, s1, z0, z1, mat, off=off, holes=holes, tag=tag)
        if batten:
            for s in np.arange(s0 + batten, s1 - 0.1, batten):
                cut = None
                for h in holes:
                    hs = np.array(h)
                    if hs[:, 0].min() - 0.05 < s < hs[:, 0].max() + 0.05: cut = (hs[:, 1].min(), hs[:, 1].max())
                segs = [(z0, z1)] if cut is None else [(z0, cut[0] - 0.02), (cut[1] + 0.02, z1)]
                for (za, zb) in segs:
                    if zb - za > 0.05: self.box(s - 0.018, s + 0.018, za, zb, off, off + 0.02, mat, tag='detail')

    def plaster(self, s0, s1, z0, z1, off=0.0, tint=(236, 232, 222), tag='main'):
        self.plane(s0, s1, z0, z1, 'temple_wall', off=off, tag=tag, c0=(*tint, 35), c1=(0, 0, 0, 0))

    def koshi(self, s0, s1, z0, z1, off=0.0, mat='wood_dark', step=0.075, back='glass', tag='main'):
        """格子 / 連子: vertical bars in a frame with a dark backing"""
        self.plane(s0, s1, z0, z1, back, off=off - 0.06, tag=tag)
        for zz in (z0, z1 - 0.05):
            self.box(s0, s1, zz, zz + 0.05, off - 0.03, off + 0.02, mat, tag=tag)
        for (sa, sb) in ((s0, s0 + 0.045), (s1 - 0.045, s1)):
            self.box(sa, sb, z0, z1, off - 0.03, off + 0.02, mat, tag=tag)
        for s in np.arange(s0 + 0.045 + step / 2, s1 - 0.045, step):
            self.box(s - 0.014, s + 0.014, z0 + 0.05, z1 - 0.05, off - 0.025, off + 0.01, mat, tag='detail')

    def karado(self, s0, s1, z0, z1, off=0.0, mat='wood_dark', lattice=0.55, open_=False, tag='main'):
        """桟唐戸: two leaves, frame + rails, square lattice in the upper part, boards below"""
        W = (s1 - s0) / 2
        for i in range(2):
            a = s0 + i * W; b = a + W
            if open_ and i == 1: continue
            o = off
            zl = z0 + (z1 - z0) * (1 - lattice)
            self.plane(a, b, z0, zl, mat, off=o - 0.01, tag=tag)
            self.plane(a + 0.06, b - 0.06, zl, z1 - 0.07, 'glass', off=o - 0.05, tag=tag)
            for (sa, sb) in ((a, a + 0.07), (b - 0.07, b)):
                self.box(sa, sb, z0, z1, o - 0.035, o + 0.02, mat, tag=tag)
            for zz in (z0, zl - 0.03, z1 - 0.07, z0 + (zl - z0) * 0.5):
                self.box(a + 0.07, b - 0.07, zz, zz + 0.07, o - 0.03, o + 0.018, mat, tag=tag)
            st = 0.085
            for s in np.arange(a + 0.07 + st, b - 0.07, st):
                self.box(s - 0.012, s + 0.012, zl + 0.04, z1 - 0.07, o - 0.025, o + 0.008, mat, tag='detail')
            for zz in np.arange(zl + 0.04 + st, z1 - 0.07, st):
                self.box(a + 0.07, b - 0.07, zz - 0.012, zz + 0.012, o - 0.025, o + 0.008, mat, tag='detail')

    def katomado(self, s0, s1, z0, z1, wz=(0.75, 1.95), ww=0.95, off=0.0, wall='wood_dark', frame='black_lacquer', tag='main', batten=0.42):
        """花頭窓 in a board wall: hole + black frame + white shoji set back"""
        sc = (s0 + s1) / 2
        ring = katomado_ring(sc, ww, z0 + wz[0], z0 + wz[1])
        self.boards(s0, s1, z0, z1, off=off, mat=wall, batten=batten, holes=[ring], tag=tag)
        # the frame: sweep along the outline in the wall plane
        pts = np.array([self.P(s, z, off + 0.03) for (s, z) in ring + [ring[0]]])
        prim.sweep(self.B, pts, [(-0.035, -0.035), (0.035, -0.035), (0.035, 0.035), (-0.035, 0.035)], frame, up=(self.n[0], self.n[1], 0), tag=tag)
        # shoji behind: two panels (white) with a frame and a few kumiko
        zs0, zs1 = z0 + wz[0], z0 + wz[1]
        self.plane(sc - ww / 2 - 0.05, sc + ww / 2 + 0.05, zs0 - 0.02, zs1 + 0.02, 'white_paint', off=off - 0.12, tag=tag)
        self.box(sc - 0.02, sc + 0.02, zs0, zs1, off - 0.11, off - 0.08, 'wood_dark', tag='detail')
        for k in (1, 2, 3):
            zz = zs0 + (zs1 - zs0) * k / 4
            self.box(sc - ww / 2, sc + ww / 2, zz - 0.008, zz + 0.008, off - 0.11, off - 0.09, 'wood_dark', tag='detail')
        # the reveal (window jamb) inside the hole: a short tube
        ring3 = [(s, z) for (s, z) in ring]
        for i in range(len(ring3)):
            s_a, z_a = ring3[i]; s_b, z_b = ring3[(i + 1) % len(ring3)]
            A = self.P(s_a, z_a, off); Bq = self.P(s_b, z_b, off); C = self.P(s_b, z_b, off - 0.12); D = self.P(s_a, z_a, off - 0.12)
            quad(self.B, A, D, C, Bq, wall, tag='detail', both=True)

# ------------------------------------------------------------------ rocks
def rock(B, c, size, seed, mat='stone', tag='main', flat=0.6, sub=2, sink=0.25, aniso=(1.0, 1.0), tilt=0.0, **kw):
    """garden stone: displaced icosphere (sub = subdivision level 0..2), flattened, sunk a little"""
    r_ = np.random.default_rng(seed)
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
    d = 1 + 0.2 * np.sin(V @ r_.normal(0, 2.5, 3)) + 0.12 * np.sin(V @ r_.normal(0, 5, 3)) + 0.05 * np.sin(V @ r_.normal(0, 10, 3))
    V = V * d[:, None]
    V[:, 2] = np.where(V[:, 2] > 0.55, 0.55 + (V[:, 2] - 0.55) * 0.5, V[:, 2])     # a flatter top
    sx, sy, sz = size * aniso[0] * r_.uniform(0.85, 1.15), size * aniso[1] * r_.uniform(0.7, 1.0), size * flat * r_.uniform(0.8, 1.2)
    V = V * [sx, sy, sz]
    if tilt:
        a = r_.uniform(-tilt, tilt); ca, sa = math.cos(a), math.sin(a)
        V = V @ np.array([[1, 0, 0], [0, ca, -sa], [0, sa, ca]]).T
    yaw = r_.uniform(0, 2 * math.pi); cy, sy_ = math.cos(yaw), math.sin(yaw)
    V = V @ np.array([[cy, -sy_, 0], [sy_, cy, 0], [0, 0, 1]]).T
    V = V + np.asarray(c, float) - [0, 0, sz * sink]
    B.add(V, F, mat, smooth=True, tag=tag, **kw)
    return sz * (1 - sink)

# ------------------------------------------------------------------ polylines
def resample(path, step):
    path = np.asarray(path, float)
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    s = np.r_[0, np.cumsum(seg)]; L = s[-1]
    n = max(1, int(math.ceil(L / step)))
    t = np.linspace(0, L, n + 1)
    return np.c_[np.interp(t, s, path[:, 0]), np.interp(t, s, path[:, 1])], t

def normals2(path):
    T = np.gradient(path, axis=0); T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    return np.c_[-T[:, 1], T[:, 0]], T

def offset_line(path, d):
    p, _ = resample(path, 0.25)
    N, _ = normals2(p)
    return p + N * d

# ------------------------------------------------------------------ hedges, walls, fences
def hedge_mass(B, path, gz, h=5.0, w=1.2, seed=0, step=0.5, top_round=0.35, lean=0.04, tag='main', ends=True, zoff=0.0, noise=0.06):
    """a clipped hedge (生垣): swept rounded section along a polyline, slightly bulging, a little leaf-noise"""
    p, s = resample(path, step)
    N, T = normals2(p)
    r_ = np.random.default_rng(seed)
    k = len(p)
    z = np.array([gz(*q) for q in p]) + zoff
    # section (x across, y up) from the left foot over the top to the right foot
    prof = []
    for t in np.linspace(0, 1, 5):
        prof.append((-w / 2 * (1 - lean * t) - 0.04 * math.sin(t * math.pi), h * (1 - top_round / h) * t))
    for a in np.linspace(math.pi, 0, 7)[1:-1]:
        prof.append((math.cos(a) * (w / 2 * (1 - lean) - 0.02), h - top_round + math.sin(a) * top_round))
    for t in np.linspace(1, 0, 5):
        prof.append((w / 2 * (1 - lean * t) + 0.04 * math.sin(t * math.pi), h * (1 - top_round / h) * t))
    prof = np.array(prof); m = len(prof)
    nz = r_.normal(0, 1, (k, m));
    from scipy.ndimage import gaussian_filter
    nz = gaussian_filter(nz, (1.2, 0.8)) * noise * 3
    P = np.zeros((k, m, 3)); UV = np.zeros((k, m, 2))
    acc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    for i in range(k):
        for j, (x, y) in enumerate(prof):
            ex = x + np.sign(x) * nz[i, j] if abs(x) > 1e-6 else x
            ey = y + (nz[i, j] * 0.35 if y > h - top_round - 0.05 else 0)
            P[i, j] = (p[i, 0] + N[i, 0] * ex, p[i, 1] + N[i, 1] * ex, z[i] - 0.15 + ey + 0.15 * (j not in (0, m - 1)))
            UV[i, j] = (acc[i], j * 0.6)
    I = []
    for i in range(k - 1):
        for j in range(m - 1):
            a = i * m + j
            I += [[a, a + m, a + m + 1], [a, a + m + 1, a + 1]]
    I = np.array(I)
    PP = P.reshape(-1, 3)
    fn = np.cross(PP[I[:, 1]] - PP[I[:, 0]], PP[I[:, 2]] - PP[I[:, 0]])
    # orient outward: the top centre normal should point up
    mid = (k // 2) * m + m // 2
    tri = np.where((I == mid).any(1))[0]
    if len(tri) and fn[tri].sum(0)[2] < 0: I = I[:, ::-1]
    B.add(PP, I, 'hedge', UV=UV.reshape(-1, 2), smooth=True, tag=tag)
    if ends:
        for i, sg in ((0, -1), (k - 1, 1)):
            C = P[i].mean(0)
            Pc = np.r_[[C], P[i]]
            Ic = [[0, j + 1, j + 2] for j in range(m - 1)]
            fc = np.cross(Pc[Ic[0][1]] - Pc[0], Pc[Ic[0][2]] - Pc[0])
            if fc[:2] @ (T[i] * sg) < 0: Ic = [t[::-1] for t in Ic]
            B.add(Pc, Ic, 'hedge', tag=tag)
    return P

def stone_wall(B, path, gz, h=0.75, top_w=0.5, batter=0.12, seed=0, step=0.35, side=1, tag='main', zoff=0.0):
    """野面積み: a low rough-stone wall with a mossy top; `side` = which normal side is the face"""
    p, _ = resample(path, step)
    N, T = normals2(p); N = N * side
    r_ = np.random.default_rng(seed)
    k = len(p)
    z = np.array([gz(*q) for q in p]) + zoff
    rows = 6
    from scipy.ndimage import gaussian_filter
    nz = gaussian_filter(r_.normal(0, 1, (k, rows + 1)), (0.7, 0.5)) * 0.05
    P = []; UV = []
    acc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    for i in range(k):
        for j in range(rows + 1):
            t = j / rows
            # stone courses: a bulge per course
            bul = 0.035 * math.sin(t * rows * math.pi) ** 2
            o = batter * (1 - t) + bul + nz[i, j]
            P.append((p[i, 0] + N[i, 0] * o, p[i, 1] + N[i, 1] * o, z[i] - 0.15 + (h + 0.15) * t))
            UV.append((acc[i], t * h))
    P = np.array(P); UV = np.array(UV)
    I = []
    m = rows + 1
    for i in range(k - 1):
        for j in range(rows):
            a = i * m + j
            I += [[a, a + m, a + m + 1], [a, a + m + 1, a + 1]]
    I = np.array(I)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    if (fn[:, :2] * np.repeat(N[:-1], 2 * rows, axis=0)).sum() < 0: I = I[:, ::-1]
    B.add(P, I, 'stone', UV=UV, smooth=True, tag=tag)
    # mossy top
    top_a = np.c_[p + N * 0.0, z + h]; top_b = np.c_[p - N * top_w, z + h + 0.02]
    PT = np.concatenate([top_a, top_b]); IT = []
    for i in range(k - 1):
        IT += [[i, i + 1 + k, i + 1], [i, i + k, i + 1 + k]]
    IT = np.array(IT)
    fn = np.cross(PT[IT[:, 1]] - PT[IT[:, 0]], PT[IT[:, 2]] - PT[IT[:, 0]])
    if fn[:, 2].sum() < 0: IT = IT[:, ::-1]
    B.add(PT, IT, 'moss_mound', UV=PT[:, :2], tag=tag)
    return z

def kenninji(B, path, zf, h=1.4, tag='main', post=1.8, side=1):
    """建仁寺垣: split bamboo laid vertically, horizontal 押縁 ties (bamboo) on the face, a 玉縁 cap bundle on top.
    zf(s_index, xy) -> base z"""
    p, _ = resample(path, 0.6)
    N, T = normals2(p); N = N * side
    k = len(p)
    z = np.array([zf(q) for q in p])
    acc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    for sg in (-1, 1):
        P = np.concatenate([np.c_[p + N * sg * 0.03, z], np.c_[p + N * sg * 0.03, z + h]])
        I = []
        for i in range(k - 1):
            I += [[i, i + 1, i + 1 + k], [i, i + 1 + k, i + k]]
        I = np.array(I)
        fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
        if (fn[:, :2] * np.repeat(N[:-1] * sg, 2, axis=0)).sum() < 0: I = I[:, ::-1]
        UV = np.r_[np.c_[acc, np.zeros(k)], np.c_[acc, np.full(k, h)]]
        B.add(P, I, 'bamboo', UV=UV, tag=tag, c1=(0, 1, 0, 0))
    # ties (押縁): 4 rows of half bamboo on the face side + the cap
    for zt in (0.22, 0.55, 0.88, h - 0.18):
        pts = np.c_[p + N * 0.06, z + zt]
        prim.sweep(B, pts, [(0.022 * math.cos(a), 0.022 * math.sin(a)) for a in np.linspace(0, math.pi * 2, 7)[:-1]], 'bamboo', up=(0, 0, 1), tag='detail', smooth=True)
    cap = np.c_[p, z + h + 0.04]
    prim.sweep(B, cap, [(0.07 * math.cos(a), 0.05 * math.sin(a)) for a in np.linspace(0, math.pi * 2, 9)[:-1]], 'bamboo', up=(0, 0, 1), tag=tag, smooth=True)
    for t in np.arange(0, acc[-1] + 0.01, post):
        i = int(np.searchsorted(acc, t)); i = min(i, k - 1)
        prim.cyl(B, np.r_[p[i] - N[i] * 0.06, z[i] - 0.05], np.r_[p[i] - N[i] * 0.06, z[i] + h + 0.02], 0.04, 0.04, 6, 'wood_dark', tag='detail')

def ribbon(B, path, width, zf, mat='ground', c1=(0, 0, 0, 0), tag='main', step=0.5, off=0.03, walk=True, uv_along=True):
    """a strip along a polyline following zf(x, y) (path surface, bridges, walk ramps)"""
    p, _ = resample(path, step)
    N, T = normals2(p)
    k = len(p)
    L = p - N * width / 2; R = p + N * width / 2
    zl = np.array([zf(*q) for q in L]) + off; zr = np.array([zf(*q) for q in R]) + off
    P = np.concatenate([np.c_[L, zl], np.c_[R, zr]])
    I = []
    for i in range(k - 1):
        I += [[i, i + 1 + k, i + 1], [i, i + k, i + 1 + k]]
    I = np.array(I)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    if fn[:, 2].sum() < 0: I = I[:, ::-1]
    if mat: B.add(P, I, mat, UV=P[:, :2], c1=c1, smooth=True, tag=tag)
    if walk: B.add(P, I, 'stone', tag='walk')
    return P

def steps_along(B, path, width, zf, riser=0.16, mat='stone', tag='main', walk=True, side_stones=True, seed=0):
    """stone steps (石段) following the terrain profile along a polyline: treads at quantized heights, a walk ramp"""
    p, s = resample(path, 0.1)
    z = np.array([zf(*q) for q in p])
    # monotone envelope in the direction of the overall climb
    up = z[-1] >= z[0]
    if not up: p = p[::-1]; z = z[::-1]
    zm = np.maximum.accumulate(z)
    N, T = normals2(p)
    acc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    z0 = zm[0]; total = zm[-1] - z0
    n = max(1, int(round(total / riser)))
    rr = total / n
    r_ = np.random.default_rng(seed)
    edges = [0]
    for k in range(1, n + 1):
        i = int(np.searchsorted(zm, z0 + rr * (k - 0.5)))
        edges.append(min(max(i, edges[-1] + 1), len(p) - 1))
    edges.append(len(p) - 1)
    for k in range(len(edges) - 1):
        i0, i1 = edges[k], edges[k + 1]
        if i1 <= i0: continue
        zt = z0 + rr * k
        a = p[i0]; b = p[i1]
        d = b - a; L = np.linalg.norm(d)
        if L < 0.05: continue
        d /= L; nn = np.array([-d[1], d[0]])
        w = width * r_.uniform(0.95, 1.05)
        # tread slab: from a to b, top at zt (riser front at a)
        cs = [a - nn * w / 2, a + nn * w / 2, b + nn * w / 2, b - nn * w / 2]
        pts = np.array(cs)
        ar = 0.5 * np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])
        if ar < 0: pts = pts[::-1]
        prim.prism(B, pts, zt - rr - 0.12, zt + 0.02, mat, tag=tag)
    if walk:
        ribbon(B, p, width, lambda x, y: float(np.interp(np.argmin(np.hypot(p[:, 0] - x, p[:, 1] - y)), np.arange(len(p)), zm)) + 0.02, mat=None, walk=True, off=0.0)
