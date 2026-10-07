"""statues_relief — 2D ornament rasters (openwork halos, scrolls, flames) turned into 3D relief fields.
Strokes are rasterised with numpy, the signed 2D distance comes from scipy's Euclidean distance transform, and a
Relief prim extrudes it (rounded edges) on a gently curved slab."""
import math
import numpy as np
from scipy import ndimage
from .statues_sdf import Prim

F32 = np.float32

class Canvas:
    def __init__(self, x0, z0, x1, z1, px):
        self.x0, self.z0, self.px = x0, z0, px
        self.nx = int(math.ceil((x1 - x0) / px)) + 1; self.nz = int(math.ceil((z1 - z0) / px)) + 1
        self.m = np.zeros((self.nz, self.nx), bool)
        self.X = None
    def _ij(self, x, z): return (np.asarray(z) - self.z0) / self.px, (np.asarray(x) - self.x0) / self.px
    def stroke(self, pts, w):
        """thick polyline: pts [(x, z)], half-width w (scalar or per point)"""
        pts = np.asarray(pts, float); n = len(pts)
        w = np.broadcast_to(np.asarray(w, float), (n,))
        for k in range(n - 1):
            a, b = pts[k], pts[k + 1]; wa, wb = w[k], w[k + 1]; wm = max(wa, wb)
            lo = np.minimum(a, b) - wm; hi = np.maximum(a, b) + wm
            i0 = max(int((lo[1] - self.z0) / self.px), 0); i1 = min(int((hi[1] - self.z0) / self.px) + 2, self.nz)
            j0 = max(int((lo[0] - self.x0) / self.px), 0); j1 = min(int((hi[0] - self.x0) / self.px) + 2, self.nx)
            if i1 <= i0 or j1 <= j0: continue
            Z, Xg = np.mgrid[i0:i1, j0:j1]
            px = self.x0 + Xg * self.px; pz = self.z0 + Z * self.px
            ab = b - a; l2 = ab @ ab + 1e-12
            t = np.clip(((px - a[0]) * ab[0] + (pz - a[1]) * ab[1]) / l2, 0, 1)
            dx = px - (a[0] + t * ab[0]); dz = pz - (a[1] + t * ab[1])
            ww = wa + (wb - wa) * t
            self.m[i0:i1, j0:j1] |= (dx * dx + dz * dz) <= ww * ww
    def cut(self, pts, w):
        """carve a thick polyline out of the mask (piercing)"""
        keep = self.m.copy(); self.m[:] = False
        self.stroke(pts, w); hole = self.m.copy(); self.m = keep & ~hole
    def fill(self, inside_fn):
        Z, Xg = np.mgrid[0:self.nz, 0:self.nx]
        px = self.x0 + Xg * self.px; pz = self.z0 + Z * self.px
        self.m |= inside_fn(px, pz)
    def clip(self, inside_fn):
        Z, Xg = np.mgrid[0:self.nz, 0:self.nx]
        px = self.x0 + Xg * self.px; pz = self.z0 + Z * self.px
        self.m &= inside_fn(px, pz)
    def sdf(self):
        out = ndimage.distance_transform_edt(~self.m) * self.px
        ins = ndimage.distance_transform_edt(self.m) * self.px
        return (out - ins).astype(F32)

class Relief(Prim):
    """extrude a 2D signed distance (x, z grid) into a slab: centre plane y = y0 + bend * x^2 (+ tilt * z), half
    thickness t, edge rounding r"""
    def __init__(self, D, x0, z0, px, y0, t, r=0.005, bend=0.0, tilt=0.0, zbend=0.0, zc=0.0):
        self.D = D; self.x0, self.z0, self.px = x0, z0, px; self.y0, self.t, self.r = y0, t, r
        self.bend, self.tilt, self.zbend, self.zc = bend, tilt, zbend, zc
        nz, nx = D.shape
        x1 = x0 + (nx - 1) * px; z1 = z0 + (nz - 1) * px
        ys = [y0 + bend * max(x0 * x0, x1 * x1) + tilt * z for z in (z0, z1)] + [y0 + tilt * z for z in (z0, z1)]
        ys += [y0 + zbend * (z0 - zc) ** 2, y0 + zbend * (z1 - zc) ** 2]
        self.lo = np.array([x0, min(ys) - t - r, z0], F32); self.hi = np.array([x1, max(ys) + t + r + 0.0, z1], F32)
    def d(self, P):
        j = (P[:, 0] - self.x0) / self.px; i = (P[:, 2] - self.z0) / self.px
        d2 = ndimage.map_coordinates(self.D, [i, j], order=1, mode='nearest')
        out = np.maximum(np.maximum(self.x0 - P[:, 0], P[:, 0] - (self.x0 + (self.D.shape[1] - 1) * self.px)), 0)
        out = np.maximum(out, np.maximum(np.maximum(self.z0 - P[:, 2], P[:, 2] - (self.z0 + (self.D.shape[0] - 1) * self.px)), 0))
        d2 = d2 + out
        yc = self.y0 + self.bend * P[:, 0] ** 2 + self.tilt * P[:, 2] + self.zbend * (P[:, 2] - self.zc) ** 2
        dy = np.abs(P[:, 1] - yc) - self.t
        a = d2 + self.r; b = dy + self.r
        return (np.sqrt(np.maximum(a, 0) ** 2 + np.maximum(b, 0) ** 2) + np.minimum(np.maximum(a, b), 0) - self.r).astype(F32)

def spiral(c, r0, turns, dirn=1, start=0.0, n=40, shrink=0.75):
    """a scroll (渦): logarithmic-ish spiral from radius r0 inward"""
    pts = []
    for k in range(n):
        t = k / (n - 1)
        a = start + dirn * t * turns * 2 * math.pi
        r = r0 * (1 - shrink * t)
        pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    return pts

def tendril_field(cv, seeds, rng, w=0.012, r=0.12, links=1):
    """唐草: at each seed a spiral with a leaf; stems link each seed to its nearest neighbours with curving S strokes"""
    seeds = np.asarray(seeds, float)
    starts = []
    for k, c in enumerate(seeds):
        dirn = 1 if rng.random() < 0.5 else -1
        st = rng.uniform(0, 2 * math.pi)
        sp = spiral(c, r * rng.uniform(0.8, 1.1), rng.uniform(1.1, 1.6), dirn, st, 36)
        cv.stroke(sp, np.linspace(w, w * 0.45, len(sp)))
        starts.append(np.array(sp[0]))
        # a leaf: a pointed lobe off the spiral's outer end
        a = st - dirn * 0.6
        p0 = np.array(sp[0]); d = np.array([math.cos(a), math.sin(a)])
        nrm_ = np.array([-d[1], d[0]])
        leaf = [p0 + d * r * 0.9 * t + nrm_ * r * 0.25 * math.sin(math.pi * t) for t in np.linspace(0, 1, 8)]
        leaf2 = [p0 + d * r * 0.9 * t - nrm_ * r * 0.12 * math.sin(math.pi * t) for t in np.linspace(0, 1, 8)]
        cv.stroke(leaf, w * 0.7); cv.stroke(leaf2, w * 0.6)
    starts = np.array(starts)
    for k, p0 in enumerate(starts):
        d = np.linalg.norm(seeds - p0, axis=1); d[k] = 1e9
        for j in np.argsort(d)[:links]:
            q = seeds[j]; v = q - p0; L = np.linalg.norm(v)
            if L > r * 3.2: continue
            nn = np.array([-v[1], v[0]]) / max(L, 1e-9)
            bow = rng.uniform(-0.3, 0.3) * L
            path = [p0 + v * t + nn * bow * math.sin(math.pi * t) * (1 - 0.5 * t) for t in np.linspace(0, 0.8, 12)]
            cv.stroke(path, w * 0.85)
