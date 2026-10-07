"""statues_sdf — a small signed-distance sculpting kit (numpy) meshed with OpenVDB.

A Field is an ordered list of operations on primitives: add (smooth union), sub (smooth subtraction), inter
(smooth intersection) and paint (relabel a region without changing the surface).  Every primitive carries a
LABEL (small int, a palette slot) so the meshed surface knows its material.

Evaluation is block-sparse: the domain is cut into BS^3-voxel blocks, block centres are classified with the full
field, only blocks near the surface are evaluated voxel by voxel (with the operations whose bounding boxes touch
the block), the narrow band goes into an OpenVDB FloatGrid and is polygonised (convertToPolygons)."""
import math, time
import numpy as np

F32 = np.float32
BIG = 1e3

def nrm(v):
    v = np.asarray(v, float); n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v

def frame(x=None, y=None, z=None):
    """rotation matrix whose COLUMNS are the local x, y, z axes (world), from any two (the third is derived)"""
    if x is not None: x = nrm(x)
    if y is not None: y = nrm(y)
    if z is not None: z = nrm(z)
    if x is None: x = nrm(np.cross(y, z)); y = np.cross(z, x)
    elif y is None: y = nrm(np.cross(z, x)); z = np.cross(x, y)
    else: z = nrm(np.cross(x, y)); y = np.cross(z, x)
    return np.stack([x, y, z], 1)

def rot(axis, ang):
    a = nrm(axis); c, s = math.cos(ang), math.sin(ang)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K

def euler(rx=0, ry=0, rz=0):
    """rotation about x, then y, then z (radians)"""
    return rot((0, 0, 1), rz) @ rot((0, 1, 0), ry) @ rot((1, 0, 0), rx)

# ---------------------------------------------------------------------------------------------- primitives
class Prim:
    lo = None; hi = None
    def d(self, P): raise NotImplementedError
    def bbox(self): return self.lo, self.hi

class Sphere(Prim):
    def __init__(self, c, r):
        self.c = np.asarray(c, F32); self.r = float(r)
        self.lo = self.c - r; self.hi = self.c + r
    def d(self, P):
        return np.sqrt(((P - self.c) ** 2).sum(1)) - self.r

class Ellipsoid(Prim):
    """iq's approximate ellipsoid distance; R columns = local axes"""
    def __init__(self, c, r, R=None):
        self.c = np.asarray(c, F32); self.r = np.maximum(np.asarray(r, F32), 1e-5)
        self.R = None if R is None else np.asarray(R, F32)
        if self.R is None: e = self.r
        else: e = np.abs(self.R) @ self.r
        self.lo = self.c - e; self.hi = self.c + e
    def d(self, P):
        q = P - self.c
        if self.R is not None: q = q @ self.R
        k0 = np.sqrt(((q / self.r) ** 2).sum(1)); k1 = np.sqrt(((q / (self.r * self.r)) ** 2).sum(1))
        return np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -self.r.min())

class RCone(Prim):
    """round cone (capsule with different end radii) from a (radius ra) to b (radius rb)"""
    def __init__(self, a, b, ra, rb=None):
        rb = ra if rb is None else rb
        self.a = np.asarray(a, F32); self.b = np.asarray(b, F32); self.ra = float(ra); self.rb = float(rb)
        ba = self.b - self.a; self.ba = ba; self.l2 = float(ba @ ba) + 1e-12
        self.rr = self.ra - self.rb; self.a2 = self.l2 - self.rr * self.rr; self.il2 = 1.0 / self.l2
        m = max(ra, rb)
        self.lo = np.minimum(self.a - ra, self.b - rb); self.hi = np.maximum(self.a + ra, self.b + rb)
        self.degenerate = self.a2 <= 1e-12
    def d(self, P):
        if self.degenerate:      # one sphere swallows the other
            return Sphere(self.a if self.ra >= self.rb else self.b, max(self.ra, self.rb)).d(P)
        pa = P - self.a
        y = pa @ self.ba; z = y - self.l2
        x2v = pa * self.l2 - self.ba[None, :] * y[:, None]
        x2 = (x2v * x2v).sum(1); y2 = y * y * self.l2; z2 = z * z * self.l2
        k = math.copysign(1.0, self.rr) * self.rr * self.rr * x2 if self.rr != 0 else np.zeros_like(x2)
        d3 = (np.sqrt(np.maximum(x2 * self.a2 * self.il2, 0)) + y * self.rr) * self.il2 - self.ra
        d1 = np.sqrt(x2 + z2) * self.il2 - self.rb
        d2 = np.sqrt(x2 + y2) * self.il2 - self.ra
        out = np.where(np.sign(y) * self.a2 * y2 < k, d2, d3)
        out = np.where(np.sign(z) * self.a2 * z2 > k, d1, out)
        return out

def Capsule(a, b, r): return RCone(a, b, r, r)

class Box(Prim):
    """rounded box: centre c, half sizes h, rotation R (columns local axes), rounding rr"""
    def __init__(self, c, h, R=None, rr=0.0):
        self.c = np.asarray(c, F32); self.h = np.asarray(h, F32); self.R = None if R is None else np.asarray(R, F32); self.rr = float(rr)
        e = self.h if self.R is None else np.abs(self.R) @ self.h
        self.lo = self.c - e; self.hi = self.c + e
    def d(self, P):
        q = P - self.c
        if self.R is not None: q = q @ self.R
        q = np.abs(q) - (self.h - self.rr)
        return np.sqrt((np.maximum(q, 0) ** 2).sum(1)) + np.minimum(q.max(1), 0) - self.rr

class Torus(Prim):
    """torus in the local xy plane (z = axis): major R, minor r; optional ellipse scale of the ring (sx, sy)"""
    def __init__(self, c, R, r, M=None, sx=1.0, sy=1.0):
        self.c = np.asarray(c, F32); self.Rm = float(R); self.r = float(r); self.M = None if M is None else np.asarray(M, F32)
        self.sx = sx; self.sy = sy
        e = np.array([R * sx + r, R * sy + r, r], F32)
        e = e if self.M is None else np.abs(self.M) @ e
        self.lo = self.c - e; self.hi = self.c + e
    def d(self, P):
        q = P - self.c
        if self.M is not None: q = q @ self.M
        ring = np.sqrt((q[:, 0] / self.sx) ** 2 + (q[:, 1] / self.sy) ** 2) * min(self.sx, self.sy) - self.Rm * min(self.sx, self.sy)
        return np.sqrt(ring ** 2 + q[:, 2] ** 2) - self.r

class Cyl(Prim):
    """capped cylinder from a to b, radius r, edge rounding rr"""
    def __init__(self, a, b, r, rr=0.0):
        self.a = np.asarray(a, F32); self.b = np.asarray(b, F32); self.r = float(r); self.rr = float(rr)
        self.ax = nrm(self.b - self.a).astype(F32); self.L = float(np.linalg.norm(self.b - self.a))
        self.lo = np.minimum(self.a, self.b) - r; self.hi = np.maximum(self.a, self.b) + r
    def d(self, P):
        pa = P - self.a; y = pa @ self.ax
        x = np.sqrt(np.maximum((pa * pa).sum(1) - y * y, 0))
        qx = x - (self.r - self.rr); qy = np.abs(y - self.L / 2) - (self.L / 2 - self.rr)
        return np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - self.rr

class Plane(Prim):
    """half-space: inside where (P - c) . n < 0"""
    def __init__(self, c, n):
        self.c = np.asarray(c, F32); self.n = nrm(n).astype(F32)
        self.lo = np.full(3, -BIG, F32); self.hi = np.full(3, BIG, F32)
    def d(self, P): return (P - self.c) @ self.n

class Fn(Prim):
    """arbitrary distance function with a bbox"""
    def __init__(self, f, lo, hi):
        self.f = f; self.lo = np.asarray(lo, F32); self.hi = np.asarray(hi, F32)
    def d(self, P): return self.f(P)

# ---- composites
class Shell(Prim):
    def __init__(self, p, t, off=0.0):
        self.p = p; self.t = t; self.off = off
        self.lo = p.lo - off - t; self.hi = p.hi + off + t
    def d(self, P): return np.abs(self.p.d(P) - self.off) - self.t

class Offset(Prim):
    def __init__(self, p, r):
        self.p = p; self.r = r; self.lo = p.lo - max(r, 0); self.hi = p.hi + max(r, 0)
    def d(self, P): return self.p.d(P) - self.r

class Inter(Prim):
    """smooth intersection of prims; bbox of the first (or given)"""
    def __init__(self, ps, k=0.0, lo=None, hi=None):
        self.ps = ps; self.k = k
        los = [p.lo for p in ps if p.lo[0] > -BIG / 2]; his = [p.hi for p in ps if p.hi[0] < BIG / 2]
        self.lo = np.asarray(lo, F32) if lo is not None else np.max(los, 0); self.hi = np.asarray(hi, F32) if hi is not None else np.min(his, 0)
    def d(self, P):
        d = self.ps[0].d(P)
        for p in self.ps[1:]: d = smax(d, p.d(P), self.k)
        return d

class Union(Prim):
    def __init__(self, ps, k=0.0):
        self.ps = ps; self.k = k
        self.lo = np.min([p.lo for p in ps], 0) - k; self.hi = np.max([p.hi for p in ps], 0) + k
    def d(self, P):
        d = self.ps[0].d(P)
        for p in self.ps[1:]: d = smin(d, p.d(P), self.k)
        return d

class Diff(Prim):
    def __init__(self, a, bs, k=0.0):
        self.a = a; self.bs = bs; self.k = k; self.lo = a.lo; self.hi = a.hi
    def d(self, P):
        d = self.a.d(P)
        for b in self.bs: d = smax(d, -b.d(P), self.k)
        return d

class Displace(Prim):
    """d(P) + f(P) with |f| <= amp"""
    def __init__(self, p, f, amp):
        self.p = p; self.f = f; self.amp = amp; self.lo = p.lo - amp; self.hi = p.hi + amp
    def d(self, P): return self.p.d(P) + self.f(P)

class Warp(Prim):
    """domain warp: d(P) = p.d(P - fn(P)), fn -> displacement vectors (|fn| <= amp): bends thin plates into folds
    without changing their thickness"""
    def __init__(self, p, fn, amp):
        self.p = p; self.fn = fn; self.amp = amp; self.lo = p.lo - amp; self.hi = p.hi + amp
    def d(self, P): return self.p.d(P - self.fn(P).astype(F32)) * 0.9

class Xf(Prim):
    """a primitive defined in a local frame: world P -> local (P - t) @ R"""
    def __init__(self, p, R, t):
        self.p = p; self.R = np.asarray(R, F32); self.t = np.asarray(t, F32)
        # bbox: transform the 8 corners of the local bbox
        c = np.array([[x, y, z] for x in (p.lo[0], p.hi[0]) for y in (p.lo[1], p.hi[1]) for z in (p.lo[2], p.hi[2])], F32)
        w = c @ self.R.T + self.t
        self.lo = w.min(0); self.hi = w.max(0)
    def d(self, P): return self.p.d((P - self.t) @ self.R)

class Tube(Prim):
    """chain of round cones through points with radii (hard union) — limbs, tails, ropes"""
    def __init__(self, pts, radii, k=0.0):
        self.segs = [RCone(pts[i], pts[i + 1], radii[i], radii[i + 1]) for i in range(len(pts) - 1)]
        self.k = k
        self.lo = np.min([s.lo for s in self.segs], 0) - k; self.hi = np.max([s.hi for s in self.segs], 0) + k
    def d(self, P):
        d = self.segs[0].d(P)
        for s in self.segs[1:]: d = smin(d, s.d(P), self.k) if self.k > 0 else np.minimum(d, s.d(P))
        return d

class Loft(Prim):
    """a vertical loft of ellipses (skirts, robes): rows of (z, cx, cy, rx, ry) from bottom to top.
    folds: list of (amp, n, phase, z0, z1) vertical fold waves (amp in metres, n = waves around)."""
    def __init__(self, rows, folds=(), cap=0.01, front_flat=0.0, tilt=None):
        rows = np.asarray(rows, float); self.rows = rows[np.argsort(rows[:, 0])]
        self.folds = folds; self.cap = cap
        z0, z1 = self.rows[0, 0], self.rows[-1, 0]
        amp = sum(abs(f[0]) for f in folds)
        self.lo = np.array([np.min(rows[:, 1] - rows[:, 3]) - amp, np.min(rows[:, 2] - rows[:, 4]) - amp, z0 - amp], F32)
        self.hi = np.array([np.max(rows[:, 1] + rows[:, 3]) + amp, np.max(rows[:, 2] + rows[:, 4]) + amp, z1 + amp], F32)
    def d(self, P):
        z = P[:, 2]; R = self.rows
        cx = np.interp(z, R[:, 0], R[:, 1]); cy = np.interp(z, R[:, 0], R[:, 2])
        rx = np.interp(z, R[:, 0], R[:, 3]); ry = np.interp(z, R[:, 0], R[:, 4])
        qx = P[:, 0] - cx; qy = P[:, 1] - cy
        k0 = np.sqrt((qx / rx) ** 2 + (qy / ry) ** 2); k1 = np.sqrt((qx / rx ** 2) ** 2 + (qy / ry ** 2) ** 2)
        dxy = np.where(k1 > 1e-9, k0 * (k0 - 1) / np.maximum(k1, 1e-9), -np.minimum(rx, ry))
        if self.folds:
            th = np.arctan2(qy, qx)
            for (amp, n, ph, fz0, fz1) in self.folds:
                w = np.clip((z - fz0) / max(fz1 - fz0, 1e-6), 0, 1)
                w = np.sin(w * math.pi) ** 0.5 if fz1 > fz0 else 1.0
                dxy = dxy - amp * w * np.cos(n * th + ph + 0.0 * z)
        dz = np.maximum(R[0, 0] - z, z - R[-1, 0])
        return np.maximum(dxy, dz)

# ---------------------------------------------------------------------------------------------- blending
def smin(a, b, k):
    if k <= 0: return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.minimum(a, b) - h * h * k * 0.25

def smax(a, b, k):
    if k <= 0: return np.maximum(a, b)
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.maximum(a, b) + h * h * k * 0.25

# ---------------------------------------------------------------------------------------------- noise
def _hash3(ix, iy, iz, seed=0):
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 144269504) & 0xffffffff
    h = (h ^ (h >> 13)) * 1274126177 & 0xffffffff
    return ((h ^ (h >> 16)) & 0xffff).astype(F32) / 65535.0

def vnoise(P, scale, seed=0):
    """value noise in [-1, 1] at frequency 1/scale"""
    Q = P / scale; I = np.floor(Q).astype(np.int64); f = Q - I; u = f * f * (3 - 2 * f)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (u[:, 0] if dx else 1 - u[:, 0]) * (u[:, 1] if dy else 1 - u[:, 1]) * (u[:, 2] if dz else 1 - u[:, 2])
                out = out + w * _hash3(I[:, 0] + dx, I[:, 1] + dy, I[:, 2] + dz, seed)
    return out * 2 - 1

def fbm(P, scale, oct=3, seed=0):
    s = 0; a = 1.0; t = 0
    for o in range(oct):
        s = s + a * vnoise(P, scale / (2 ** o), seed + o * 17); t += a; a *= 0.5
    return s / t

# ---------------------------------------------------------------------------------------------- fields
class Field:
    def __init__(self, name='field'):
        self.name = name; self.ops = []
    def add(self, p, lab, k=0.0):
        self.ops.append(('a', p, float(k), lab)); return p
    def sub(self, p, k=0.0, lab=None):
        self.ops.append(('s', p, float(k), lab)); return p
    def inter(self, p, k=0.0):
        self.ops.append(('i', p, float(k), None)); return p
    def paint(self, p, lab):
        self.ops.append(('p', p, 0.0, lab)); return p
    def extend(self, other):
        self.ops += other.ops

    def bounds(self):
        lo = np.full(3, BIG, F32); hi = np.full(3, -BIG, F32)
        for (kd, p, k, lab) in self.ops:
            if kd == 'a': lo = np.minimum(lo, p.lo - k); hi = np.maximum(hi, p.hi + k)
        return lo, hi

    def _arrays(self):
        LO = np.array([p.lo - k for (kd, p, k, lab) in self.ops], F32); HI = np.array([p.hi + k for (kd, p, k, lab) in self.ops], F32)
        glob = np.array([kd == 'i' for (kd, p, k, lab) in self.ops])
        LO[glob] = -BIG; HI[glob] = BIG
        return LO, HI

    def eval(self, P, idx=None, labels=False):
        P = np.asarray(P, F32)
        d = np.full(len(P), BIG, F32); lab = np.zeros(len(P), np.int16) if labels else None
        ops = self.ops if idx is None else [self.ops[i] for i in idx]
        for (kd, p, k, lb) in ops:
            if kd == 'p':
                if labels: lab[p.d(P) < 0] = lb
                continue
            dp = p.d(P).astype(F32)
            if kd == 'a':
                if labels: lab = np.where(dp < d, np.int16(lb), lab)
                d = smin(d, dp, k)
            elif kd == 's':
                if labels and lb is not None: lab = np.where(-dp > d, np.int16(lb), lab)
                d = smax(d, -dp, k)
            else:
                d = smax(d, dp, k)
        return (d, lab) if labels else d

    def relevant(self, LO, HI, blo, bhi, m):
        return np.nonzero(np.all(LO - m <= bhi, 1) & np.all(HI + m >= blo, 1))[0]

    def mesh(self, h, adapt=0.0, bs=16, clip=None, verbose=True):
        """polygonise at voxel size h -> (P (n,3) float32, T (m,3) int32, LAB per vertex int16)"""
        import openvdb as vdb
        t0 = time.time()
        lo, hi = self.bounds()
        if clip is not None: lo = np.maximum(lo, clip[0]); hi = np.minimum(hi, clip[1])
        lo = lo - 2 * h; hi = hi + 2 * h
        n = np.ceil((hi - lo) / h).astype(int) + 1
        nb = np.ceil(n / bs).astype(int)
        LO, HI = self._arrays()
        bw = 3.0 * h
        g = vdb.FloatGrid(float(bw))
        # classify blocks by their centres
        bi = np.stack(np.meshgrid(np.arange(nb[0]), np.arange(nb[1]), np.arange(nb[2]), indexing='ij'), -1).reshape(-1, 3)
        bc = lo + (bi * bs + (bs - 1) / 2.0) * h
        hd = math.sqrt(3) * (bs / 2.0) * h
        dc = np.empty(len(bc), F32)
        CH = 200000
        for s in range(0, len(bc), CH):
            dc[s:s + CH] = self.eval(bc[s:s + CH])
        near = np.abs(dc) < 1.6 * hd + bw
        inside = dc <= -(1.6 * hd + bw)
        ar = np.arange(bs)
        G = np.stack(np.meshgrid(ar, ar, ar, indexing='ij'), -1).reshape(-1, 3).astype(F32)
        nnear = 0
        for b in np.nonzero(inside)[0]:
            i0 = bi[b] * bs
            g.fill(tuple(int(v) for v in i0), tuple(int(v) for v in i0 + bs - 1), float(-bw), True)
        for b in np.nonzero(near)[0]:
            i0 = bi[b] * bs
            blo = lo + i0 * h; bhi = blo + (bs - 1) * h
            idx = self.relevant(LO, HI, blo, bhi, bw + h)
            if len(idx) == 0: continue
            P = blo + G * h
            d = self.eval(P, idx)
            d = np.clip(d, -bw, bw).astype(F32).reshape(bs, bs, bs)
            if d.min() >= bw: continue
            g.copyFromArray(d, tuple(int(v) for v in i0), 0.0)
            nnear += 1
        pts, tris, quads = g.convertToPolygons(0.0, adapt)
        P = (lo + pts.astype(F32) * h).astype(F32)
        T = np.concatenate([tris.reshape(-1, 3), quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]]).astype(np.int32)
        LAB = self.labels_at(P, h)
        if verbose:
            print(f'  field {self.name}: {len(self.ops)} ops, grid {n.tolist()} h={h*1000:.1f}mm, {nnear} near blocks, '
                  f'{len(T)} tris in {time.time()-t0:.1f}s', flush=True)
        return P, T, LAB

    def eval_grouped(self, P, h=0.01, cell=0.06):
        """field distance at arbitrary points (grouped by cells for culling)"""
        LO, HI = self._arrays()
        P = np.asarray(P, F32); out = np.full(len(P), BIG, F32)
        if len(P) == 0: return out
        c = np.floor(P / cell).astype(np.int64)
        key = (c[:, 0] * 73856093) ^ (c[:, 1] * 19349663) ^ (c[:, 2] * 83492791)
        order = np.argsort(key, kind='stable'); ks = key[order]
        cuts = np.nonzero(np.diff(ks))[0] + 1
        for grp in np.split(order, cuts):
            Q = P[grp]; blo = Q.min(0); bhi = Q.max(0)
            idx = self.relevant(LO, HI, blo, bhi, 0.05)
            if len(idx) == 0: continue
            out[grp] = self.eval(Q, idx)
        return out

    def labels_at(self, P, h=0.01, cell=0.06):
        """label of the surface at points P (evaluated with the ops that touch each cell)"""
        LO, HI = self._arrays()
        lab = np.zeros(len(P), np.int16)
        if len(P) == 0: return lab
        c = np.floor(P / cell).astype(np.int64)
        key = (c[:, 0] * 73856093) ^ (c[:, 1] * 19349663) ^ (c[:, 2] * 83492791)
        order = np.argsort(key, kind='stable'); ks = key[order]
        cuts = np.nonzero(np.diff(ks))[0] + 1
        for grp in np.split(order, cuts):
            Q = P[grp]; blo = Q.min(0); bhi = Q.max(0)
            idx = self.relevant(LO, HI, blo, bhi, 3 * h)
            if len(idx) == 0: continue
            _, lb = self.eval(Q, idx, labels=True)
            lab[grp] = lb
        return lab
