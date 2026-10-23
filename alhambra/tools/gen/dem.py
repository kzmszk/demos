"""IGN MDT elevation grids (ETRS89 / UTM 30N, CC BY 4.0 © Instituto Geográfico Nacional) in the
demo's local frame: x east, z south, metres from 37.17725 N, 3.5897 W (x = dlon*88700, z = -dlat*111320).
Three resolutions (5 m near, 25 m mid, 200 m far); `height(x, z)` uses the finest grid covering a point."""
import glob, os
import numpy as np
from pyproj import Transformer
from scipy.ndimage import map_coordinates

ASSETS = os.environ.get('ALHAMBRA_ASSETS', '/home/kazu/work/alhambra-assets')
LAT0, LON0 = 37.17725, -3.5897
_to_utm = Transformer.from_crs(4326, 25830, always_xy=True)

def to_utm(x, z):
    return _to_utm.transform(LON0 + np.asarray(x) / 88700, LAT0 - np.asarray(z) / 111320)

def _read(path):
    with open(path, 'rb') as f:
        raw = f.read().decode('latin-1')
    i = raw.index('ncols')
    lines = raw[i:].split('\n')
    hdr = {}
    for k in range(6):
        key, val = lines[k].split()[:2]
        hdr[key.lower()] = float(val)
        if key.lower() == 'cellsize': start = k + 1; break
    if 'nodata_value' in lines[start].lower(): hdr['nodata'] = float(lines[start].split()[1]); start += 1
    data = []
    for l in lines[start:]:
        if l.startswith('--'): break
        data.append(l)
    body = ' '.join(data)
    vals = np.array(body.split(), dtype=np.float32)
    nr, nc = int(hdr['nrows']), int(hdr['ncols'])
    return hdr, vals[:nr * nc].reshape(nr, nc)

class Grid:
    def __init__(self, folder):
        tiles = [_read(p) for p in sorted(glob.glob(f'{folder}/*.asc'))]
        cs = tiles[0][0]['cellsize']
        x0 = min(h['xllcorner'] for h, _ in tiles); y0 = min(h['yllcorner'] for h, _ in tiles)
        x1 = max(h['xllcorner'] + h['ncols'] * cs for h, _ in tiles); y1 = max(h['yllcorner'] + h['nrows'] * cs for h, _ in tiles)
        nc, nr = int(round((x1 - x0) / cs)), int(round((y1 - y0) / cs))
        a = np.full((nr, nc), np.nan, np.float32)
        for h, v in tiles:
            c = int(round((h['xllcorner'] - x0) / cs)); r = int(round((y1 - h['yllcorner'] - h['nrows'] * cs) / cs))
            v = np.where(v < -1000, np.nan, v)
            a[r:r + v.shape[0], c:c + v.shape[1]] = v
        self.cs, self.x0, self.y1, self.a = cs, x0, y1, a
    def sample(self, ux, uy):
        # cell centres: column c at x0 + (c+.5)cs, row r at y1 - (r+.5)cs
        c = (np.asarray(ux) - self.x0) / self.cs - .5; r = (self.y1 - np.asarray(uy)) / self.cs - .5
        inside = (c >= 0) & (r >= 0) & (c <= self.a.shape[1] - 1) & (r <= self.a.shape[0] - 1)
        out = map_coordinates(np.nan_to_num(self.a, nan=-9999), [np.clip(r, 0, None), np.clip(c, 0, None)], order=1, mode='nearest')
        out = np.where(inside & (out > -1000), out, np.nan)
        return out

_cache = {}
def grids():
    if not _cache:
        npz = f'{ASSETS}/cache/dem.npz'
        if os.path.exists(npz):
            d = np.load(npz)
            for k in ('near5', 'mid25', 'far200'):
                g = Grid.__new__(Grid); g.a = d[k]; g.cs, g.x0, g.y1 = d[k + '_h']; _cache[k] = g
        else:
            for k in ('near5', 'mid25', 'far200'): _cache[k] = Grid(f'{ASSETS}/dem/{k}')
            np.savez_compressed(npz, **{k: g.a for k, g in _cache.items()}, **{k + '_h': np.array([g.cs, g.x0, g.y1]) for k, g in _cache.items()})
    return _cache

def elevation(x, z):
    """Absolute elevation (m) at local x, z (arrays)."""
    ux, uy = to_utm(x, z)
    g = grids(); out = g['far200'].sample(ux, uy)
    for k in ('mid25', 'near5'):
        v = g[k].sample(ux, uy); out = np.where(np.isnan(v), out, v)
    return out
