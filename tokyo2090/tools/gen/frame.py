"""Local metric frame for TOKYO 2090: origin at the centre of the Shibuya scramble crossing, x east, y north (metres),
z = elevation above Tokyo Peil (T.P., metres), the same heights as the GSI DEM and PLATEAU."""
import numpy as np
from pyproj import Transformer

LAT0, LON0 = 35.65951, 139.70053
ASSETS = '/home/kazu/work/tokyo2090-assets'
PUBLIC = '/home/kazu/work/demos/tokyo2090/public'
_tm = f'+proj=tmerc +lat_0={LAT0} +lon_0={LON0} +k=1 +x_0=0 +y_0=0 +ellps=GRS80 +units=m'
_fwd = Transformer.from_crs('EPSG:4326', _tm, always_xy=True)
_inv = Transformer.from_crs(_tm, 'EPSG:4326', always_xy=True)
_ecef = Transformer.from_crs('EPSG:4978', 'EPSG:4979', always_xy=True)   # ECEF (3D Tiles) -> lon lat h(ellipsoid)

def to_xy(lon, lat):
    return _fwd.transform(np.asarray(lon, np.float64), np.asarray(lat, np.float64))

def to_lonlat(x, y):
    return _inv.transform(np.asarray(x, np.float64), np.asarray(y, np.float64))

def ecef_to_local(X, Y, Z, geoid=36.7):
    """ECEF metres -> local x, y, z (T.P.).  PLATEAU 3D Tiles carry orthometric heights baked into ECEF via the
    ellipsoid, so the geoid height of central Tokyo (~36.7 m, GSI GSIGEO2011) is subtracted back out."""
    lon, lat, h = _ecef.transform(np.asarray(X, np.float64), np.asarray(Y, np.float64), np.asarray(Z, np.float64))
    x, y = to_xy(lon, lat)
    return x, y, h - geoid

# the built area: Shibuya in the middle, Shinjuku to the north, Roppongi / Tokyo Tower to the east
X0, Y0, X1, Y1 = -2400.0, -2000.0, 4600.0, 4400.0
TILE = 250.0
NTX, NTY = int((X1 - X0) // TILE), int((Y1 - Y0) // TILE)

def tile_of(x, y): return int((x - X0) // TILE), int((y - Y0) // TILE)
def tile_bounds(i, j): return (X0 + i * TILE, Y0 + j * TILE, X0 + (i + 1) * TILE, Y0 + (j + 1) * TILE)
def bbox_lonlat(margin=0.0):
    lo = []; la = []
    for x, y in ((X0 - margin, Y0 - margin), (X1 + margin, Y0 - margin), (X0 - margin, Y1 + margin), (X1 + margin, Y1 + margin)):
        a, b = to_lonlat(x, y); lo.append(float(a)); la.append(float(b))
    return min(lo), min(la), max(lo), max(la)

if __name__ == '__main__':
    print('bbox lon/lat', bbox_lonlat(), 'tiles', NTX, 'x', NTY)
    for name, lat, lon in (('tocho', 35.68963, 139.69167), ('tokyo_tower', 35.65858, 139.74543), ('mori_tower', 35.66046, 139.72921),
                           ('azabudai', 35.66066, 139.74015), ('cocoon', 35.69150, 139.69748), ('hikarie', 35.65913, 139.70378)):
        x, y = to_xy(lon, lat); print(f'{name:12s} {float(x):8.0f} {float(y):8.0f}')
