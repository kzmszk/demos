"""Plan-view map of the source package (debug aid). venv python: map.py out.png [scale px/m]"""
import json, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
from shapely.ops import unary_union
SRC = '/home/kazu/work/tokyo2090-assets/hero/roppongi/'
out = sys.argv[1]; S = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
X0, X1, Y0, Y1 = -200, 200, -210, 210
W, H = int((X1-X0)*S), int((Y1-Y0)*S)
def P(x, y): return ((x-X0)*S, (Y1-y)*S)
def read_obj(path):
    objs = {}; V = []; cur = None
    for line in open(path):
        if line.startswith('o '): cur = line[2:].strip(); objs[cur] = []
        elif line.startswith('v '): V.append(tuple(map(float, line.split()[1:4])))
        elif line.startswith('f '):
            objs[cur].append([int(t.split('/')[0])-1 for t in line.split()[1:]])
    return V, objs
g = np.load(SRC+'ground.npz'); h = g['h']; gx0, gy0, gs = float(g['x0']), float(g['y0']), float(g['s'])
img = Image.new('RGB', (W, H), (40, 40, 40)); d = ImageDraw.Draw(img)
# ground height shading
hmin, hmax = 8, 33
for j in range(h.shape[0]):
    for i in range(h.shape[1]):
        x = gx0 + i*gs; y = gy0 + j*gs
        if X0-10 <= x <= X1 and Y0-10 <= y <= Y1:
            t = (h[j, i]-hmin)/(hmax-hmin); c = int(60+150*t)
            a = P(x-gs/2, y+gs/2); b = P(x+gs/2, y-gs/2)
            d.rectangle([a, b], fill=(c, c, int(c*0.9)))
osm = json.load(open(SRC+'osm.json'))
for lu in osm['landuse']:
    if lu['kind'] in ('garden', 'park'):
        for pl in lu['polys']: d.polygon([P(*p) for p in pl['outer']], outline=(60, 200, 60))
for w in osm['water']:
    for pl in w['polys']: d.polygon([P(*p) for p in pl['outer']], fill=(60, 90, 200))
for r in osm['roads']:
    col = {'steps': (255, 140, 0), 'footway': (255, 255, 120), 'path': (255, 255, 120), 'service': (180, 180, 255)}.get(r['hw'], (255, 255, 255))
    if r['tunnel']: col = (120, 120, 120)
    wdt = max(1, int((r['width'] or 2)*S*0.5)) if r['hw'] not in ('steps', 'footway', 'path') else 2
    d.line([P(*p) for p in r['line']], fill=col, width=wdt)
V, objs = read_obj(SRC+'buildings.obj')
meta = {b['obj']: b for b in json.load(open(SRC+'buildings.json'))['buildings']}
try: font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', int(3*S))
except Exception: font = None
for name, fs in objs.items():
    polys = []
    for f in fs:
        pts = [(V[k][0], V[k][1]) for k in f]
        pg = Polygon(pts)
        if pg.is_valid and pg.area > 0.01: polys.append(pg)
    u = unary_union(polys)
    for pg in (u.geoms if hasattr(u, 'geoms') else [u]):
        d.polygon([P(*p) for p in pg.exterior.coords], outline=(255, 60, 60))
    m = meta[name]
    d.text(P(m['cx'], m['cy']), f"{name[1:]}\n{m['z0']:.0f}/{m['z1']:.0f}", fill=(255, 220, 220), font=font)
for p in osm['points']:
    t = p['tags']
    if 'artwork_type' in t or t.get('highway') in ('elevator',) or 'railway' in t:
        x, y = P(*p['xy']); d.ellipse([x-6, y-6, x+6, y+6], outline=(255, 0, 255), width=3)
# grid
for gxx in range(-200, 201, 50):
    d.line([P(gxx, Y0), P(gxx, Y1)], fill=(0, 255, 255) if gxx == 0 else (0, 120, 120), width=1)
for gyy in range(-200, 201, 50):
    d.line([P(X0, gyy), P(X1, gyy)], fill=(0, 255, 255) if gyy == 0 else (0, 120, 120), width=1)
    d.text(P(X0+1, gyy), str(gyy), fill=(0, 255, 255), font=font)
for gxx in range(-200, 201, 50): d.text(P(gxx, Y0+8), str(gxx), fill=(0, 255, 255), font=font)
img.save(out)
