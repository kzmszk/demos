"""Shared helpers for the roppongi hero build (runs inside Blender's Python; numpy only).

Coordinates: local district frame, x east, y north, z up = absolute height (T.P. m).
Geometry is accumulated in Buckets (one per material) and turned into Blender meshes at the end.
"""
import json, math, os, random
import numpy as np

SRC = '/home/kazu/work/tokyo2090-assets/hero/roppongi/'
WORK = SRC + 'work/'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, '../../../public/hero/roppongi')) + '/'
LOD = 'near'           # 'near' | 'mid' (set by build.py --lod)


def mid():
    return LOD == 'mid'


CLEAR = []      # polygons kept free of plants (spawn view corridors)


def cleared(x, y):
    return any(point_in_poly(x, y, p) for p in CLEAR)


PLAZA_Z = 31.3          # 66 Plaza / Hollywood Plaza deck (Roppongi-dori level)
BOX = (-180, -190, 180, 190)


# ---------------------------------------------------------------- source data
def read_obj(path):
    """-> dict name -> (V (n,3) float array, faces list of index lists local to V)"""
    objs = {}
    V = []
    cur = None
    faces = {}
    for line in open(path):
        if line.startswith('o '):
            cur = line[2:].strip(); faces[cur] = []
        elif line.startswith('v '):
            V.append([float(t) for t in line.split()[1:4]])
        elif line.startswith('f '):
            faces[cur].append([int(t.split('/')[0]) - 1 for t in line.split()[1:]])
    V = np.array(V)
    for name, fs in faces.items():
        if not fs:
            continue
        idx = sorted({i for f in fs for i in f})
        remap = {g: k for k, g in enumerate(idx)}
        objs[name] = (V[idx], [[remap[i] for i in f] for f in fs])
    return objs


def meta():
    return {b['obj']: b for b in json.load(open(SRC + 'buildings.json'))['buildings']}


def osm():
    return json.load(open(SRC + 'osm.json'))


class Ground:
    """The game terrain exactly: 10 m grid, cells split along (x+10,y)-(x,y+10)."""
    def __init__(self):
        g = np.load(SRC + 'ground.npz')
        self.h = g['h'].astype(np.float64)
        self.x0 = float(g['x0']); self.y0 = float(g['y0']); self.s = float(g['s'])

    def __call__(self, x, y):
        x = np.asarray(x, float); y = np.asarray(y, float)
        fx = (x - self.x0) / self.s; fy = (y - self.y0) / self.s
        i = np.clip(np.floor(fx).astype(int), 0, self.h.shape[1] - 2)
        j = np.clip(np.floor(fy).astype(int), 0, self.h.shape[0] - 2)
        u = fx - i; v = fy - j
        h00 = self.h[j, i]; h10 = self.h[j, i + 1]; h01 = self.h[j + 1, i]; h11 = self.h[j + 1, i + 1]
        lo = h00 + u * (h10 - h00) + v * (h01 - h00)
        hi = h11 + (1 - u) * (h01 - h11) + (1 - v) * (h10 - h11)
        r = np.where(u + v <= 1.0, lo, hi)
        return float(r) if r.ndim == 0 else r

    def minmax(self, pts):
        z = self(np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
        return float(np.min(z)), float(np.max(z))


# ---------------------------------------------------------------- noise
def _hash(*a):
    h = np.zeros(np.broadcast(*a).shape, dtype=np.uint64) + np.uint64(0x9E3779B97F4A7C15)
    for k, v in enumerate(a):
        v = np.asarray(v).astype(np.int64).astype(np.uint64)
        h ^= v * np.uint64(0xBF58476D1CE4E5B9 + 2 * k)
        h = (h ^ (h >> np.uint64(31))) * np.uint64(0x94D049BB133111EB)
        h ^= h >> np.uint64(29)
    return (h & np.uint64(0xFFFFFF)).astype(np.float64) / float(0xFFFFFF)


def vnoise(x, y=0.0, seed=0, z=None):
    """value noise in [0,1], smooth; vectorised; 2D (or 3D if z given)"""
    x = np.asarray(x, float); y = np.asarray(y, float)
    xi = np.floor(x); yi = np.floor(y); xf = x - xi; yf = y - yi
    sx = xf * xf * (3 - 2 * xf); sy = yf * yf * (3 - 2 * yf)
    if z is None:
        a = _hash(xi, yi, seed); b = _hash(xi + 1, yi, seed)
        c = _hash(xi, yi + 1, seed); d = _hash(xi + 1, yi + 1, seed)
        r = (a + (b - a) * sx) + ((c + (d - c) * sx) - (a + (b - a) * sx)) * sy
        return r
    z = np.asarray(z, float); zi = np.floor(z); zf = z - zi; sz = zf * zf * (3 - 2 * zf)
    out = 0
    for dz, wz in ((0, 1 - sz), (1, sz)):
        a = _hash(xi, yi, zi + dz, seed); b = _hash(xi + 1, yi, zi + dz, seed)
        c = _hash(xi, yi + 1, zi + dz, seed); d = _hash(xi + 1, yi + 1, zi + dz, seed)
        out = out + wz * ((a + (b - a) * sx) + ((c + (d - c) * sx) - (a + (b - a) * sx)) * sy)
    return out


def fbm(x, y=0.0, seed=0, octaves=4, z=None):
    t = 0; amp = 0.5; norm = 0; f = 1.0
    for o in range(octaves):
        t = t + amp * vnoise(np.asarray(x) * f, np.asarray(y) * f, seed + 17 * o,
                             None if z is None else np.asarray(z) * f)
        norm += amp; amp *= 0.5; f *= 2.03
    return t / norm


# ---------------------------------------------------------------- geometry buckets
class Bucket:
    """Accumulates polygons for one material. uv = UV0 per corner. col = optional per-vertex colour."""
    def __init__(self, name):
        self.name = name
        self.V = []; self.F = []; self.UV = []; self.N = None; self.C = None
        self.nv = 0

    def poly(self, pts, uvs=None, normals=None, colors=None):
        n = len(pts)
        base = self.nv
        self.V.extend([tuple(map(float, p)) for p in pts])
        self.nv += n
        self.F.append(list(range(base, base + n)))
        self.UV.append([tuple(map(float, u)) for u in uvs] if uvs is not None else [(0.0, 0.0)] * n)
        if normals is not None:
            if self.N is None:
                self.N = [(0.0, 0.0, 1.0)] * base
            self.N.extend([tuple(map(float, q)) for q in normals])
        elif self.N is not None:
            self.N.extend([(0.0, 0.0, 1.0)] * n)
        if colors is not None:
            if self.C is None:
                self.C = [(1.0, 1.0, 1.0, 1.0)] * base
            self.C.extend([tuple(map(float, c)) for c in colors])
        elif self.C is not None:
            self.C.extend([(1.0, 1.0, 1.0, 1.0)] * n)
        return base

    def mesh(self, verts, faces, uvs_per_vertex=None, normals=None, colors=None):
        """add an indexed mesh; uvs_per_vertex (n,2) used for each corner"""
        base = self.nv
        verts = np.asarray(verts, float)
        self.V.extend(map(tuple, verts.tolist()))
        self.nv += len(verts)
        for f in faces:
            self.F.append([base + i for i in f])
            if uvs_per_vertex is not None:
                self.UV.append([tuple(uvs_per_vertex[i]) for i in f])
            else:
                self.UV.append([(0.0, 0.0)] * len(f))
        if normals is not None:
            if self.N is None:
                self.N = [(0.0, 0.0, 1.0)] * base
            self.N.extend(map(tuple, np.asarray(normals, float).tolist()))
        elif self.N is not None:
            self.N.extend([(0.0, 0.0, 1.0)] * len(verts))
        if colors is not None:
            if self.C is None:
                self.C = [(1.0, 1.0, 1.0, 1.0)] * base
            self.C.extend(map(tuple, np.asarray(colors, float).tolist()))
        elif self.C is not None:
            self.C.extend([(1.0, 1.0, 1.0, 1.0)] * len(verts))
        return base

    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    def merge(self, other):
        base = self.nv
        if other.N is not None and self.N is None:
            self.N = [(0.0, 0.0, 1.0)] * base
        if other.C is not None and self.C is None:
            self.C = [(1.0, 1.0, 1.0, 1.0)] * base
        self.V.extend(other.V); self.nv += other.nv
        self.F.extend([[base + i for i in f] for f in other.F]); self.UV.extend(other.UV)
        if self.N is not None:
            self.N.extend(other.N if other.N is not None else [(0.0, 0.0, 1.0)] * other.nv)
        if self.C is not None:
            self.C.extend(other.C if other.C is not None else [(1.0, 1.0, 1.0, 1.0)] * other.nv)


class Scene:
    """dict of buckets by material name"""
    def __init__(self):
        self.b = {}

    def __getitem__(self, k):
        if k not in self.b:
            self.b[k] = Bucket(k)
        return self.b[k]

    def stats(self):
        return {k: v.tris() for k, v in self.b.items()}


# ---------------------------------------------------------------- primitive helpers
def v3(x, y, z):
    return np.array([x, y, z], float)


def norm(v):
    v = np.asarray(v, float); n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def quad(b, p0, p1, p2, p3, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    b.poly([p0, p1, p2, p3], uv)


def box(b, c, size, rot=0.0, uvscale=1.0, tilt=None, skip_bottom=True):
    """axis-aligned (in its own z-rotation) box centred at c=(x,y,z-bottom-centre)? -> c is bottom centre"""
    sx, sy, sz = size
    cx, cy, cz = c
    ca, sa = math.cos(rot), math.sin(rot)
    def P(x, y, z):
        p = np.array([x * ca - y * sa, x * sa + y * ca, z])
        if tilt is not None:
            p = tilt @ p
        return p + np.array([cx, cy, cz])
    hx, hy = sx / 2, sy / 2
    c8 = [P(-hx, -hy, 0), P(hx, -hy, 0), P(hx, hy, 0), P(-hx, hy, 0),
          P(-hx, -hy, sz), P(hx, -hy, sz), P(hx, hy, sz), P(-hx, hy, sz)]
    u = uvscale
    quad(b, c8[4], c8[5], c8[6], c8[7], ((0, 0), (sx * u, 0), (sx * u, sy * u), (0, sy * u)))
    quad(b, c8[0], c8[1], c8[5], c8[4], ((0, 0), (sx * u, 0), (sx * u, sz * u), (0, sz * u)))
    quad(b, c8[1], c8[2], c8[6], c8[5], ((0, 0), (sy * u, 0), (sy * u, sz * u), (0, sz * u)))
    quad(b, c8[2], c8[3], c8[7], c8[6], ((0, 0), (sx * u, 0), (sx * u, sz * u), (0, sz * u)))
    quad(b, c8[3], c8[0], c8[4], c8[7], ((0, 0), (sy * u, 0), (sy * u, sz * u), (0, sz * u)))
    if not skip_bottom:
        quad(b, c8[3], c8[2], c8[1], c8[0])


def frame_from(t):
    """orthonormal frame with tangent t"""
    t = norm(t)
    a = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0, 0])
    n = norm(np.cross(t, a)); bn = np.cross(t, n)
    return n, bn


def tube(b, path, radii, sides=6, uv_v_scale=1.0, uv_u_scale=1.0, cap=False, twist=0.0, rough=None, seed=0):
    """sweep a circle along path (list of points) with per-point radius. parallel-transport frames.
    rough(i, k) -> radius multiplier (bark knobs).  UV: u around (0..uv_u_scale), v along length."""
    path = [np.asarray(p, float) for p in path]
    n = len(path)
    if n < 2:
        return
    T = []
    for i in range(n):
        if i == 0:
            t = path[1] - path[0]
        elif i == n - 1:
            t = path[-1] - path[-2]
        else:
            t = path[i + 1] - path[i - 1]
        T.append(norm(t))
    N0, B0 = frame_from(T[0])
    frames = [(N0, B0)]
    for i in range(1, n):
        Np, Bp = frames[-1]
        t = T[i]
        Nn = Np - t * np.dot(Np, t)
        if np.linalg.norm(Nn) < 1e-6:
            Nn, Bn = frame_from(t)
        else:
            Nn = norm(Nn); Bn = np.cross(t, Nn)
        frames.append((Nn, Bn))
    rings = []
    vacc = 0.0
    vs = [0.0]
    for i in range(1, n):
        vacc += np.linalg.norm(path[i] - path[i - 1]); vs.append(vacc)
    verts = []; uvs = []; nrm = []
    for i in range(n):
        Nn, Bn = frames[i]
        r = radii[i]
        for k in range(sides + 1):
            a = 2 * math.pi * k / sides + twist * i
            d = math.cos(a) * Nn + math.sin(a) * Bn
            rr = r * (rough(i, k % sides) if rough else 1.0)
            verts.append(path[i] + d * rr)
            uvs.append((k / sides * uv_u_scale, vs[i] * uv_v_scale))
            nrm.append(d)
    faces = []
    for i in range(n - 1):
        for k in range(sides):
            a = i * (sides + 1) + k
            faces.append([a, a + 1, a + sides + 2, a + sides + 1])
    base = b.mesh(verts, faces, uvs)
    if cap:
        c = path[-1]
        last = [(n - 1) * (sides + 1) + k for k in range(sides)]
        b.poly([verts[i] for i in last], [(0.5 + 0.5 * math.cos(2 * math.pi * k / sides),
                                           0.5 + 0.5 * math.sin(2 * math.pi * k / sides)) for k in range(sides)])
    return base


def catmull(pts, n_per=4):
    """Catmull-Rom resample through pts"""
    P = [np.asarray(p, float) for p in pts]
    if len(P) < 3:
        return P
    P = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in range(n_per):
            t = s / n_per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return out


# ---------------------------------------------------------------- 2D polygon helpers (no shapely in Blender)
def poly_area(pts):
    a = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i][:2]; x1, y1 = pts[(i + 1) % len(pts)][:2]
        a += x0 * y1 - x1 * y0
    return a / 2


def ccw(pts):
    return pts if poly_area(pts) > 0 else pts[::-1]


def point_in_poly(x, y, pts):
    inside = False
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i][:2]; xj, yj = pts[j][:2]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def points_in_poly(X, Y, pts):
    X = np.asarray(X, float); Y = np.asarray(Y, float)
    inside = np.zeros(X.shape, bool)
    n = len(pts)
    j = n - 1
    for i in range(n):
        xi, yi = pts[i][:2]; xj, yj = pts[j][:2]
        c = ((yi > Y) != (yj > Y)) & (X < (xj - xi) * (Y - yi) / (yj - yi + 1e-12) + xi)
        inside ^= c
        j = i
    return inside


def triangulate(pts):
    """ear clipping of a simple polygon (list of (x,y)) -> list of index triples (ccw input assumed)"""
    pts = [tuple(p[:2]) for p in pts]
    n = len(pts)
    if n < 3:
        return []
    idx = list(range(n))
    if poly_area(pts) < 0:
        idx.reverse()
    tris = []
    def is_convex(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 1e-12
    def inside(p, a, b, c):
        d1 = (p[0] - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (p[1] - b[1])
        d2 = (p[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (p[1] - c[1])
        d3 = (p[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (p[1] - a[1])
        neg = (d1 < 0) or (d2 < 0) or (d3 < 0); pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
        return not (neg and pos)
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        found = False
        m = len(idx)
        for k in range(m):
            i0, i1, i2 = idx[(k - 1) % m], idx[k], idx[(k + 1) % m]
            a, b_, c = pts[i0], pts[i1], pts[i2]
            if not is_convex(a, b_, c):
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                if inside(pts[j], a, b_, c):
                    ok = False; break
            if ok:
                tris.append((i0, i1, i2)); idx.pop(k); found = True; break
        if not found:
            # degenerate: fan the rest
            for k in range(1, len(idx) - 1):
                tris.append((idx[0], idx[k], idx[k + 1]))
            idx = idx[:0]
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


def offset_poly(pts, d):
    """naive miter offset of a ccw polygon (d>0 outward)."""
    pts = [np.asarray(p[:2], float) for p in pts]
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e0 = norm(p1 - p0); e1 = norm(p2 - p1)
        n0 = np.array([e0[1], -e0[0]]); n1 = np.array([e1[1], -e1[0]])
        m = norm(n0 + n1)
        c = max(np.dot(m, n0), 0.35)
        out.append(p1 + m * d / c)
    return out


def resample_ring(pts, step):
    """resample closed polygon to roughly uniform spacing; returns list of (x,y)"""
    pts = [np.asarray(p[:2], float) for p in pts]
    out = []
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        L = np.linalg.norm(b - a)
        k = max(1, int(round(L / step)))
        for j in range(k):
            out.append(a + (b - a) * j / k)
    return out


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy + 1e-12
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0, 1)
    return np.hypot(px - (ax + t * dx), py - (ay + t * dy))


def polyline_dist(px, py, line):
    d = np.full(np.shape(px), 1e9)
    for i in range(len(line) - 1):
        d = np.minimum(d, seg_dist(px, py, line[i][0], line[i][1], line[i + 1][0], line[i + 1][1]))
    return d


def rng(seed):
    return random.Random(seed)
