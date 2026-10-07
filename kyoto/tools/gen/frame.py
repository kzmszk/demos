"""Local metric frame for the Kyoto build: origin at Kyoto Station's Karasuma central exit, x east, y north (metres),
z = elevation above Tokyo Peil (T.P., metres) — the same heights as the GSI DEM and PLATEAU, so nothing is shifted."""
import numpy as np
from pyproj import Transformer

LAT0, LON0 = 34.98580, 135.75880
ASSETS = '/home/kazu/work/kyoto-assets'
_fwd = Transformer.from_crs('EPSG:4326', f'+proj=tmerc +lat_0={LAT0} +lon_0={LON0} +k=1 +x_0=0 +y_0=0 +ellps=GRS80 +units=m', always_xy=True)
_inv = Transformer.from_crs(f'+proj=tmerc +lat_0={LAT0} +lon_0={LON0} +k=1 +x_0=0 +y_0=0 +ellps=GRS80 +units=m', 'EPSG:4326', always_xy=True)

def to_xy(lon, lat):
    x, y = _fwd.transform(np.asarray(lon, np.float64), np.asarray(lat, np.float64))
    return x, y

def to_lonlat(x, y):
    return _inv.transform(np.asarray(x, np.float64), np.asarray(y, np.float64))

# the core of the build (metres in this frame); tile names count from its corner (X0, Y0)
X0, Y0, X1, Y1 = -1200.0, -3200.0, 4600.0, 5400.0
TILE = 200.0
NTX, NTY = int((X1 - X0) // TILE), int((Y1 - Y0) // TILE)
# everything that has city tiles: the core and two enclaves to the west (tiles there have negative i); the gaps between
# them are drawn by the far field only
REGIONS = {
    'core': (X0, Y0, X1, Y1),
    'kinkaku': (-4400.0, 4600.0, -1200.0, 6600.0),       # 金閣寺, 龍安寺, 仁和寺, 北野天満宮 (meets the core at x = -1200)
    'arashiyama': (-8800.0, 2400.0, -6600.0, 4600.0),    # 渡月橋, 天龍寺, 竹林の小径, 野宮神社, 常寂光寺, 嵐山
}
# the box around all regions (DEM grid, the viewer's surface lookup)
BX0, BY0 = min(r[0] for r in REGIONS.values()), min(r[1] for r in REGIONS.values())
BX1, BY1 = max(r[2] for r in REGIONS.values()), max(r[3] for r in REGIONS.values())

def tile_of(x, y): return int((x - X0) // TILE), int((y - Y0) // TILE)
def tile_bounds(i, j): return (X0 + i * TILE, Y0 + j * TILE, X0 + (i + 1) * TILE, Y0 + (j + 1) * TILE)
def region_of(i, j):
    """the region a tile belongs to (None outside all of them)"""
    x, y = X0 + (i + 0.5) * TILE, Y0 + (j + 0.5) * TILE
    for n, (a, b, c, d) in REGIONS.items():
        if a <= x < c and b <= y < d: return n
    return None
def region_tiles(names=None):
    """every tile (i, j) of the given regions (all by default)"""
    out = []
    for n, (a, b, c, d) in REGIONS.items():
        if names and n not in names: continue
        i0, j0 = tile_of(a + 1, b + 1); i1, j1 = tile_of(c - 1, d - 1)
        out += [(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)]
    return sorted(set(out))
def tiles_in(x0, y0, x1, y1):
    """tiles of the built regions that touch a box"""
    i0, j0 = tile_of(x0, y0); i1, j1 = tile_of(x1, y1)
    return [(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1) if region_of(i, j)]
