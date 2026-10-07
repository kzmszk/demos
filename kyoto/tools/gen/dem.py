"""Terrain from the GSI elevation tiles (国土地理院 標高タイル, PNG encoding: h = (R*65536 + G*256 + B) * 0.01 m,
2^23 = no data, values >= 2^23 are negative).  dem5a (airborne laser, z15) over the core, gaps (water surfaces)
from dem5b and the 10 m DEM (z14); the far view from the 10 m DEM (z14) and z12.

build_core(): a 2 m grid over the tile area (+ margin) in the local frame -> ASSETS/build/dem_core.npz
build_far():  a 30 m grid over ±24 km and a 150 m grid over ±60 km -> ASSETS/build/dem_far.npz"""
import os, math, numpy as np
from PIL import Image
from scipy import ndimage
from .frame import to_lonlat, X0, Y0, X1, Y1, BX0, BY0, BX1, BY1, ASSETS

DEM = os.path.join(ASSETS, 'dem')

def _tile(layer, z, x, y):
    p = f'{DEM}/{layer}/{z}/{x}/{y}.png'
    if not os.path.exists(p): return None
    a = np.asarray(Image.open(p).convert('RGB'), np.int64)
    v = a[..., 0] * 65536 + a[..., 1] * 256 + a[..., 2]
    h = np.where(v < 2 ** 23, v, v - 2 ** 24).astype(np.float64) * 0.01
    h[v == 2 ** 23] = np.nan
    return h

def sample(layer, z, lon, lat):
    """bilinear sample of a tile layer at lon/lat arrays (web mercator pixel space); NaN where no data."""
    n = 2 ** z
    px = (lon + 180) / 360 * n * 256
    py = (1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / np.pi) / 2 * n * 256
    x0 = int(np.floor(px.min() / 256)); x1 = int(np.floor(px.max() / 256)); y0 = int(np.floor(py.min() / 256)); y1 = int(np.floor(py.max() / 256))
    M = np.full(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), np.nan)
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            h = _tile(layer, z, tx, ty)
            if h is not None: M[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = h
    # pixel centres are at +0.5
    fx = px - x0 * 256 - 0.5; fy = py - y0 * 256 - 0.5
    ix = np.clip(np.floor(fx).astype(np.int64), 0, M.shape[1] - 2); iy = np.clip(np.floor(fy).astype(np.int64), 0, M.shape[0] - 2)
    ax = np.clip(fx - ix, 0, 1); ay = np.clip(fy - iy, 0, 1)
    a = M[iy, ix]; b = M[iy, ix + 1]; c = M[iy + 1, ix]; d = M[iy + 1, ix + 1]
    # nan-aware bilinear: weights of valid corners only
    W = np.stack([(1 - ax) * (1 - ay), ax * (1 - ay), (1 - ax) * ay, ax * ay]); V = np.stack([a, b, c, d])
    ok = np.isfinite(V); W = np.where(ok, W, 0); V = np.where(ok, V, 0)
    s = W.sum(0)
    return np.where(s > 0.2, (W * V).sum(0) / np.maximum(s, 1e-9), np.nan)

def fill_nan(H):
    """fill holes by nearest valid value, then smooth only the filled cells a little."""
    bad = ~np.isfinite(H)
    if not bad.any(): return H
    idx = ndimage.distance_transform_edt(bad, return_distances=False, return_indices=True)
    F = H[tuple(idx)]
    S = ndimage.gaussian_filter(F, 2.0)
    return np.where(bad, S, H)

def grid(x0, y0, x1, y1, res):
    xs = np.arange(x0, x1 + res * 0.5, res); ys = np.arange(y0, y1 + res * 0.5, res)
    X, Y = np.meshgrid(xs, ys)
    lon, lat = to_lonlat(X.ravel(), Y.ravel())
    return xs, ys, lon, lat

def build_core(res=2.0, margin=300.0):
    xs, ys, lon, lat = grid(BX0 - margin, BY0 - margin, BX1 + margin, BY1 + margin, res)     # all built regions (and the gaps)
    H = np.full(len(lon), np.nan)
    for (layer, z) in (('dem5a_png', 15), ('dem5b_png', 15), ('dem_png', 14)):
        m = ~np.isfinite(H)
        if not m.any(): break
        # chunked: the sampler builds a mosaic per call
        idx = np.nonzero(m)[0]
        for s0 in range(0, len(idx), 4_000_000):
            sl = idx[s0:s0 + 4_000_000]
            H[sl] = sample(layer, z, lon[sl], lat[sl])
        print(layer, 'filled ->', int(np.isfinite(H).sum()), '/', len(H), flush=True)
    H = fill_nan(H.reshape(len(ys), len(xs)))
    out = os.path.join(ASSETS, 'build', 'dem_core.npz')
    np.savez_compressed(out, H=H.astype(np.float32), x0=xs[0], y0=ys[0], res=res)
    print('core', H.shape, float(np.nanmin(H)), float(np.nanmax(H)), '->', out)

def build_far():
    out = {}
    for name, R, res, layer, z in (('far', 24000.0, 30.0, 'dem_png', 14), ('horizon', 60000.0, 150.0, 'dem_png', 12)):
        cx, cy = (BX0 + BX1) / 2, (BY0 + BY1) / 2          # centred on all built regions (as tools/far_build.py)
        xs, ys, lon, lat = grid(cx - R, cy - R, cx + R, cy + R, res)
        H = sample(layer, z, lon, lat).reshape(len(ys), len(xs))
        H = fill_nan(H)
        out[name] = H.astype(np.float32); out[name + '_o'] = np.array([xs[0], ys[0], res])
        print(name, H.shape, float(H.min()), float(H.max()), flush=True)
    np.savez_compressed(os.path.join(ASSETS, 'build', 'dem_far.npz'), **out)

class Terrain:
    """bilinear lookups in the core grid."""
    def __init__(self):
        d = np.load(os.path.join(ASSETS, 'build', 'dem_core.npz'))
        self.H = d['H'].astype(np.float64); self.x0 = float(d['x0']); self.y0 = float(d['y0']); self.res = float(d['res'])
    def __call__(self, x, y):
        x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
        fx = (x - self.x0) / self.res; fy = (y - self.y0) / self.res
        ix = np.clip(np.floor(fx).astype(np.int64), 0, self.H.shape[1] - 2); iy = np.clip(np.floor(fy).astype(np.int64), 0, self.H.shape[0] - 2)
        ax = np.clip(fx - ix, 0, 1); ay = np.clip(fy - iy, 0, 1)
        H = self.H
        return (H[iy, ix] * (1 - ax) * (1 - ay) + H[iy, ix + 1] * ax * (1 - ay) + H[iy + 1, ix] * (1 - ax) * ay + H[iy + 1, ix + 1] * ax * ay)

if __name__ == '__main__':
    import sys
    os.makedirs(os.path.join(ASSETS, 'build'), exist_ok=True)
    if 'core' in sys.argv: build_core()
    if 'far' in sys.argv: build_far()
