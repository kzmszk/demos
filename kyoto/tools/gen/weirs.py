"""The weirs across the big rivers (落差工 on the Kamo and the Takano, the Ōi's 葛野大堰) for the viewer's white water
(venv python):  python -m gen.weirs ../public/data/weirs.json
Each: the line (points every metre), the water level there (from the packed walk maps) and the downstream direction
(the flow field, gen/flowfield.py)."""
import sys, os, json
import numpy as np
import shapely
from PIL import Image
from . import world as W
from .flowfield import OUT as FLOW

CITY = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'public', 'data', 'city')

def main(out):
    w = W.load(); o = w.osm
    big = shapely.unary_union([f['poly'] for f in o['water'] if f['poly'].area > 15000 and not f.get('pool') and not f['tags'].get('tunnel')])
    F = np.load(FLOW)
    from scipy.spatial import cKDTree
    ft = cKDTree(F['P'])
    cache = {}
    def walk(x, y):
        i = int(np.floor((x + 1200) / 200)); j = int(np.floor((y + 3200) / 200)); n = f't_{i}_{j}'
        if n not in cache:
            p = os.path.join(CITY, n + '.walk.png')
            cache[n] = np.asarray(Image.open(p).convert('RGBA')).astype(int) if os.path.exists(p) else None
        im = cache[n]
        if im is None: return None
        N = im.shape[0]; rr = 200 / N
        px = min(N - 1, int((x - (-1200 + i * 200)) / rr)); py = min(N - 1, int(((-3200 + (j + 1) * 200) - y) / rr))
        R, G, B, A = im[py, px]
        return ((R * 256 + G) / 100 - 20, bool(B & 64))
    res = []
    for f in o['waterways']:
        if f['ww'] != 'weir' or not f['line'].intersects(big): continue
        ln = f['line'].intersection(big.buffer(1.0))
        for part in (ln.geoms if hasattr(ln, 'geoms') else [ln]):
            if part.geom_type != 'LineString' or part.length < 4: continue
            pts = [part.interpolate(d) for d in np.arange(0, part.length + 0.01, 1.0)]
            zs = [walk(p.x, p.y) for p in pts]
            zw = [z for z in zs if z and z[1]]
            if not zw: continue
            zl = float(np.median([z[0] for z in zw]))
            c = part.interpolate(0.5, normalized=True)
            _, k = ft.query([c.x, c.y], k=6)
            d = F['D'][k].mean(0); d /= max(np.linalg.norm(d), 1e-9)
            res.append({'pts': [[round(p.x, 2), round(p.y, 2)] for p in pts], 'z': round(zl, 2), 'dir': [round(float(d[0]), 3), round(float(d[1]), 3)]})
    json.dump(res, open(out, 'w'), separators=(',', ':'))
    print(out, len(res), 'weirs')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(CITY, '..', 'weirs.json'))
