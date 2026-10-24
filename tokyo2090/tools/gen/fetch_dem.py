"""Fetch the GSI elevation tiles (国土地理院 標高タイル, PNG) that cover the frame: dem5a/dem5b at z15 for the core
(+ margin) and dem_png (10 m) at z14 / z12 for the far view.  -> ASSETS/dem/<layer>/<z>/<x>/<y>.png"""
import os, math, sys, time, urllib.request
from .frame import ASSETS, bbox_lonlat, to_lonlat, X0, Y0, X1, Y1

BASE = 'https://cyberjapandata.gsi.go.jp/xyz'

def xy_tiles(lon0, lat0, lon1, lat1, z):
    n = 2 ** z
    def tx(lon): return int((lon + 180) / 360 * n)
    def ty(lat): return int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
    return [(x, y) for x in range(tx(lon0), tx(lon1) + 1) for y in range(ty(lat1), ty(lat0) + 1)]

def fetch(layer, z, tiles):
    got = 0; miss = 0
    for (x, y) in tiles:
        p = f'{ASSETS}/dem/{layer}/{z}/{x}/{y}.png'
        if os.path.exists(p): got += 1; continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        try:
            urllib.request.urlretrieve(f'{BASE}/{layer}/{z}/{x}/{y}.png', p); got += 1
        except Exception as e:
            miss += 1
        time.sleep(0.05)
    print(layer, z, len(tiles), 'tiles', got, 'ok', miss, 'missing', flush=True)

if __name__ == '__main__':
    lo0, la0, lo1, la1 = bbox_lonlat(600.0)
    for layer in ('dem5a_png', 'dem5b_png'): fetch(layer, 15, xy_tiles(lo0, la0, lo1, la1, 15))
    cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
    for R, z in ((30000.0, 14), (90000.0, 12)):
        a, b = to_lonlat(cx - R, cy - R); c, d = to_lonlat(cx + R, cy + R)
        fetch('dem_png', z, xy_tiles(float(a), float(b), float(c), float(d), z))
