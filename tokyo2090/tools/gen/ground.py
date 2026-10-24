"""Ground for TOKYO 2090: the terrain mesh (10 m grid from the 2 m DEM, with the far rings) and the land-cover raster
the ground shader reads (what was asphalt, rail, water, park... before the overgrowth), plus the road centrelines
the cars stand on.
  python -m gen.ground   -> PUBLIC/data/terrain.bin (gzip), PUBLIC/data/cover.png, PUBLIC/data/roads.json"""
import os, json, gzip, struct, pickle
import numpy as np
from PIL import Image, ImageDraw
from .frame import ASSETS, PUBLIC, X0, Y0, X1, Y1
from .dem import Terrain
from . import osm

COVER_RES = 4.0
# cover raster (RGBA, linear-filtered in the shader so edges are soft): R = road (major 255, minor 150, plaza 110,
# footway 80), G = green (park/forest 255, grass/garden 190), B = water, A = rail
def cover_raster(o):
    W = int((X1 - X0) / COVER_RES); H = int((Y1 - Y0) / COVER_RES)
    ims = [Image.new('L', (W, H), 0) for _ in range(4)]; drs = [ImageDraw.Draw(im) for im in ims]
    def P(xy): return [((x - X0) / COVER_RES, (y - Y0) / COVER_RES) for x, y in xy]
    def poly(ch, g, v):
        for p in (g.geoms if hasattr(g, 'geoms') else [g]):
            if p.is_empty or p.geom_type != 'Polygon': continue
            drs[ch].polygon(P(p.exterior.coords), fill=v)
            for r in p.interiors: drs[ch].polygon(P(r.coords), fill=0)
    for l in o['landuse']:
        k = l['kind']
        if k in ('park', 'forest', 'wood', 'cemetery', 'grave_yard'): poly(1, l['poly'], 255)
        elif k in ('garden', 'grass', 'scrub', 'meadow', 'orchard', 'recreation_ground', 'village_green', 'pitch', 'playground'): poly(1, l['poly'], 190)
    for l in o['landuse']:
        if l['kind'] in ('parking', 'parking_space'): poly(0, l['poly'], 150)
    for a in o['areas']:
        if a['kind'] == 'ped_area': poly(0, a['poly'], 110)
    for r in o['rails']:
        if r['tunnel']: continue
        drs[3].line(P(r['line'].coords), fill=255, width=max(1, int((4.5 if r['rw'] == 'rail' else 3.5) / COVER_RES)))
    for r in o['roads']:
        if r['tunnel']: continue
        v = 80 if r['hw'] in ('footway', 'path', 'steps', 'cycleway', 'corridor', 'bridleway', 'track') else 150 if r['hw'] in ('service', 'living_street', 'pedestrian') else 255
        drs[0].line(P(r['line'].coords), fill=v, width=max(1, int(round(r['width'] / COVER_RES))), joint='curve')
    for w in o['water']:
        if not w['pool']: poly(2, w['poly'], 255)
    for w in o['waterways']:
        if w['tunnel']: continue
        drs[2].line(P(w['line'].coords), fill=255, width=max(1, int((w['width'] or 6.0) / COVER_RES)))
    return np.stack([np.asarray(im, np.uint8) for im in ims], -1)

def terrain_mesh(T):
    rings = []
    # ring 0: the frame at 10 m; ring 1: 30 m out to 30 km; ring 2: 200 m to 90 km (the far npz)
    xs = np.arange(X0 - 500, X1 + 500 + 1, 10.0); ys = np.arange(Y0 - 500, Y1 + 500 + 1, 10.0)
    X, Y = np.meshgrid(xs, ys); Hh = T(X.ravel(), Y.ravel()).reshape(X.shape).astype(np.float32)
    rings.append(dict(x0=float(xs[0]), y0=float(ys[0]), s=10.0, nx=len(xs), ny=len(ys), h=Hh))
    far = np.load(os.path.join(ASSETS, 'build', 'dem_far.npz'))
    for name, step in (('far', 3), ('horizon', 2)):          # 90 m and 400 m: the far rings only need their shape
        o = far[name + '_o']; Hf = far[name][::step, ::step].astype(np.float32)
        rings.append(dict(x0=float(o[0]), y0=float(o[1]), s=float(o[2]) * step, nx=Hf.shape[1], ny=Hf.shape[0], h=Hf))
    head = [dict(x0=r['x0'], y0=r['y0'], s=r['s'], nx=r['nx'], ny=r['ny']) for r in rings]
    hb = json.dumps(dict(rings=head)).encode()
    body = struct.pack('<I', len(hb)) + hb + b''.join(np.clip(np.round(r['h'] * 10), -32768, 32767).astype(np.int16).tobytes() for r in rings)
    with gzip.open(os.path.join(PUBLIC, 'data', 'terrain.bin'), 'wb', compresslevel=6) as f: f.write(body)
    print('terrain rings', [(r['nx'], r['ny'], r['s']) for r in rings])

def roads_json(o):
    """major carriageways for the abandoned cars: polylines (x, y, width)"""
    out = []
    for r in o['roads']:
        if r['tunnel'] or r['hw'] not in ('motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'motorway_link', 'trunk_link', 'primary_link', 'secondary_link'): continue
        xy = np.asarray(r['line'].coords)
        if ((xy[:, 0] < X0) | (xy[:, 0] > X1) | (xy[:, 1] < Y0) | (xy[:, 1] > Y1)).all(): continue
        out.append(dict(w=round(float(r['width']), 1), hw=r['hw'], bridge=bool(r['bridge']), layer=r['layer'], xy=np.round(xy, 1).tolist()))
    json.dump(out, open(os.path.join(PUBLIC, 'data', 'roads.json'), 'w'), separators=(',', ':'))
    print('roads', len(out))

def trees_json(o):
    """where the city's trees were: park / forest polygons and OSM single trees (the viewer sows the rest)"""
    parks = []
    for l in o['landuse']:
        if l['kind'] in ('park', 'forest', 'wood', 'garden', 'grass', 'scrub', 'cemetery', 'grave_yard', 'meadow'):
            for p in (l['poly'].geoms if hasattr(l['poly'], 'geoms') else [l['poly']]):
                if p.geom_type == 'Polygon' and p.area > 200: parks.append(dict(kind=l['kind'], xy=np.round(np.asarray(p.exterior.coords), 1).tolist()))
    trees = [np.round(t['xy'], 1).tolist() for t in o['trees']]
    json.dump(dict(parks=parks, trees=trees), open(os.path.join(PUBLIC, 'data', 'green.json'), 'w'), separators=(',', ':'))
    print('parks', len(parks), 'trees', len(trees))

if __name__ == '__main__':
    os.makedirs(os.path.join(PUBLIC, 'data'), exist_ok=True)
    o = osm.load(); T = Terrain()
    cov = cover_raster(o)
    Image.fromarray(cov[::-1], 'RGBA').save(os.path.join(PUBLIC, 'data', 'cover.png'))        # row 0 = north; the viewer samples with flipY off
    print('cover', cov.shape, [(cov[..., k] > 0).mean().round(3) for k in range(4)])
    terrain_mesh(T); roads_json(o); trees_json(o)
