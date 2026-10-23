"""Terrain for the viewer: nested regular grids ("rings") of heights from the IGN 5/25/200 m DEM
(CC BY 4.0 © Instituto Geográfico Nacional), relative to the plateau E0, blended into the hand-built
plateau and Generalife model, plus landcover colour rasters from OpenStreetMap (ODbL).

Output: public/data/terrain.bin.gz  (header JSON + int16 decimetre heights + uint8 RGB vertex colours)
        public/data/ground0.jpg / ground1.jpg (landcover colour for rings 0 and 1)."""
import gzip, json, math, os, struct, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter, distance_transform_edt, binary_dilation
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union
from shapely.prepared import prep
import dem, osm
from frame import E0, PUBLIC, ASSETS

# x0, x1, z0, z1, spacing. Each ring has a hole = the extent of the previous ring.
RINGS = [(-1200, 660, -1000, 500, 5),  # ring 0 spans the walkable old town too
          (-3000, 2400, -2400, 2200, 20), (-12000, 30000, -12000, 20000, 120), (-30000, 42000, -30000, 36000, 400)]

def perimeter():
    ctx = json.load(open(f'{PUBLIC}/data/context.json'))
    return Polygon(ctx['perimeter'])

def old_model(x, z):
    """The procedural ground the plateau/Generalife model was built on (navigation.js, before)."""
    center = 20 + np.maximum(0, x) * .43
    cliff = np.maximum(0, np.abs(z - center) - np.where(x < 0, 75, 85)) / 1.65 + np.maximum(0, -x - 260) / 3
    plateau = -np.minimum(66, cliff)
    g = np.exp(-(((x - 370) / 115) ** 4 + ((z + 52) / 155) ** 4))
    return np.maximum(plateau, -45 + 77 * g)

_W = {}
def model_weight(xs, zs, res=2.0):
    """1 inside the enclosure and the Generalife model zone, fading to 0 outside."""
    x0, z0 = -500, -400
    if 'w' not in _W: _W['w'] = _weight_raster(res)
    from scipy.ndimage import map_coordinates
    c = (np.asarray(xs) - x0) / res; r = (np.asarray(zs) - z0) / res
    return map_coordinates(_W['w'], [r, c], order=1, mode='constant', cval=0)

def _weight_raster(res):
    per = perimeter()
    gen = sbox(318, -132, 430, 200)
    x0, z0, x1, z1 = -500, -400, 700, 500
    W, H = int((x1 - x0) / res), int((z1 - z0) / res)
    img = Image.new('L', (W, H), 0); d = ImageDraw.Draw(img)
    for poly, v in ((per, 255), (gen, 255)):
        d.polygon([((x - x0) / res, (z - z0) / res) for x, z in poly.exterior.coords], fill=v)
    m = np.array(img) > 0
    dist = distance_transform_edt(~m) * res
    # inside: 1; outside the enclosure the plateau level holds for 4 m (wall foot), then fades over 10 m;
    # around the Generalife model the old hill fades over 70 m.
    gm = np.zeros_like(m); gi = Image.new('L', (W, H), 0); ImageDraw.Draw(gi).polygon([((x - x0) / res, (z - z0) / res) for x, z in gen.exterior.coords], fill=255)
    gdist = distance_transform_edt(~(np.array(gi) > 0)) * res
    w_per = np.clip(1 - (dist - 4) / 10, 0, 1)
    w_gen = np.clip(1 - gdist / 70, 0, 1) ** 1.5
    w = np.maximum(w_per, w_gen)
    return w * w * (3 - 2 * w)

def heights(xs, zs):
    e = dem.elevation(xs, zs) - E0
    e = np.where(np.isnan(e), -110.0, e)    # beyond the 200 m grid: the Vega level
    w = model_weight(xs, zs)
    return w * old_model(xs, zs) + (1 - w) * e

# ---------------------------------------------------------------- landcover
PALETTE = {
    'urban': (128, 122, 104), 'road': (112, 108, 102), 'path': (176, 156, 120), 'wood': (58, 60, 38),
    'scrub': (124, 116, 72), 'grass': (122, 128, 70), 'dry': (168, 148, 98), 'farm': (136, 132, 78),
    'orchard': (98, 110, 60), 'park': (90, 108, 56), 'water': (70, 88, 86), 'bare': (164, 128, 92),
    'rock': (150, 140, 128), 'plaza': (172, 160, 140), 'cemetery': (120, 118, 96),
}
def classify(t):
    lu, na, le = t.get('landuse'), t.get('natural'), t.get('leisure')
    if na in ('wood',) or lu == 'forest': return 'wood'
    if na in ('scrub', 'heath'): return 'scrub'
    if na in ('grassland',) or lu in ('meadow', 'greenfield', 'grass', 'village_green'): return 'grass'
    if na in ('water',) or lu in ('reservoir', 'basin'): return 'water'
    if na in ('bare_rock', 'scree', 'cliff'): return 'rock'
    if na in ('sand', 'shingle'): return 'bare'
    if lu in ('farmland', 'farmyard', 'allotments'): return 'farm'
    if lu in ('orchard', 'vineyard', 'plant_nursery'): return 'orchard'
    if le in ('park', 'garden', 'golf_course') or lu in ('recreation_ground', 'flowerbed'): return 'park'
    if lu == 'cemetery': return 'cemetery'
    if lu in ('residential', 'retail', 'commercial', 'industrial', 'railway', 'construction', 'brownfield', 'education', 'religious', 'military'): return 'urban'
    if le in ('pitch', 'playground', 'sports_centre', 'track'): return 'dry'
    if t.get('highway') == 'pedestrian' or t.get('place') == 'square': return 'plaza'
    return None
ORDER = ['urban', 'farm', 'dry', 'grass', 'scrub', 'orchard', 'wood', 'park', 'cemetery', 'plaza', 'bare', 'rock', 'water']
ROAD_W = {'motorway': 14, 'trunk': 12, 'primary': 10, 'secondary': 9, 'tertiary': 8, 'residential': 6, 'unclassified': 6, 'living_street': 5, 'service': 4, 'pedestrian': 5, 'footway': 2.2, 'path': 1.8, 'track': 3, 'steps': 2.2, 'cycleway': 2}

def landcover(x0, x1, z0, z1, res, h_fn, seed=1):
    """RGB raster (rows = z) of OSM landcover with slope- and noise-based variation."""
    W, H = int(round((x1 - x0) / res)), int(round((z1 - z0) / res))
    rng = np.random.default_rng(seed)
    # default: dry Mediterranean hillside, greener in valleys
    xs = x0 + (np.arange(W) + .5) * res; zs = z0 + (np.arange(H) + .5) * res
    X, Z = np.meshgrid(xs, zs)
    hh = h_fn(X.ravel(), Z.ravel()).reshape(H, W)
    gy, gx = np.gradient(hh, res); slope = np.hypot(gx, gy)
    base = np.zeros((H, W, 3), np.float32)
    n1 = gaussian_filter(rng.standard_normal((H, W)), 6 / res * 4 if res < 5 else 3)
    n1 = (n1 - n1.mean()) / (n1.std() + 1e-6)
    dry = np.array(PALETTE['dry']); scrub = np.array(PALETTE['scrub']); grass = np.array(PALETTE['grass'])
    t = np.clip(.5 + .35 * n1, 0, 1)[..., None]
    base[:] = dry * (1 - t) + scrub * t
    img = Image.fromarray(np.zeros((H, W), np.uint8)); dr = ImageDraw.Draw(img)
    data = osm.load(); bounds = sbox(x0, z0, x1, z1)
    cls_id = {c: i + 1 for i, c in enumerate(ORDER)}
    def poly_px(geom, v):
        polys = [geom] if geom.geom_type == 'Polygon' else list(getattr(geom, 'geoms', []))
        for p in polys:
            if p.geom_type != 'Polygon' or p.is_empty: continue
            dr.polygon([((x - x0) / res, (z - z0) / res) for x, z in p.exterior.coords], fill=v)
            for ring in p.interiors: dr.polygon([((x - x0) / res, (z - z0) / res) for x, z in ring.coords], fill=0)
    areas = [(a, classify(a['tags'])) for a in data['areas']]
    areas = [(a, c) for a, c in areas if c and a['g'].intersects(bounds)]
    areas.sort(key=lambda ac: (ORDER.index(ac[1]), -ac[0]['g'].area))
    for a, c in areas: poly_px(a['g'], cls_id[c])
    cls = np.array(img)
    out = base.copy()
    hz_ = None
    for c in ORDER:
        m = cls == cls_id[c]
        if not m.any(): continue
        col = np.array(PALETTE[c], np.float32)
        if c == 'urban':
            import city
            if hz_ is None: hz_ = city.historic(X, Z)
            t = hz_[m][:, None]
            out[m] = (np.array((122, 118, 110), np.float32) * (1 - t) + np.array((108, 106, 72), np.float32) * t) * (1 + .07 * n1[m][:, None])
            continue
        k = .10 if c in ('road', 'plaza', 'water') else .07 if c == 'urban' else .18
        out[m] = col * (1 + k * n1[m][:, None])
    # roads and paths
    rimg = Image.new('L', (W, H), 0); rd = ImageDraw.Draw(rimg)
    for l in data['lines']:
        hw = l['tags'].get('highway')
        if hw not in ROAD_W or not l['g'].intersects(bounds): continue
        wpx = max(1, ROAD_W[hw] / res)
        v = 1 if hw in ('footway', 'path', 'track', 'steps', 'cycleway') and l['tags'].get('surface') in (None, 'unpaved', 'dirt', 'ground', 'gravel', 'compacted', 'fine_gravel', 'earth') else 2
        rd.line([((x - x0) / res, (z - z0) / res) for x, z in l['g'].coords], fill=v, width=int(round(wpx)))
    r = np.array(rimg)
    out[r == 1] = np.array(PALETTE['path']) * (1 + .08 * n1[r == 1][:, None])
    out[r == 2] = np.array(PALETTE['road']) * (1 + .06 * n1[r == 2][:, None])
    # waterways (Darro, Genil)
    wimg = Image.new('L', (W, H), 0); wd = ImageDraw.Draw(wimg)
    for l in data['lines']:
        ww = l['tags'].get('waterway')
        if ww in ('river', 'stream', 'canal') and l['g'].intersects(bounds):
            wd.line([((x - x0) / res, (z - z0) / res) for x, z in l['g'].coords], fill=1, width=max(1, int((8 if ww == 'river' else 3) / res)))
    out[np.array(wimg) == 1] = PALETTE['water']
    # steep ground: bare earth / rock
    steep = np.clip((slope - .55) / .6, 0, 1)[..., None] * ((cls[..., None] != cls_id['urban']) & (cls[..., None] != cls_id['wood']))
    out = out * (1 - steep * .7) + np.array(PALETTE['bare'], np.float32) * steep * .7
    # fine grain
    out *= (1 + .07 * rng.standard_normal((H, W, 1)))
    return np.clip(out, 0, 255).astype(np.uint8), cls

def far_colour(xs, zs, hs):
    """Vertex colours for the outer rings: Vega fields, dry hills, pine/oak slopes, rock, snow."""
    e = hs + E0
    rng = np.random.default_rng(3)
    cell = (np.floor(xs / 350).astype(np.int64) * 73856093 ^ np.floor(zs / 280).astype(np.int64) * 19349663) % 997 / 997.0
    vega = np.stack([110 + 50 * cell, 116 + 26 * cell, 64 + 20 * (1 - cell)], -1)
    hills = np.array([160, 140, 96]) * (0.92 + .16 * cell[:, None])
    pines = np.array([78, 88, 56])
    rock = np.array([138, 128, 118]); snow = np.array([238, 240, 246])
    t_v = np.clip((e - 650) / 120, 0, 1)[:, None]
    c = vega * (1 - t_v) + hills * t_v
    t_p = (np.clip((e - 1100) / 300, 0, 1) * np.clip((2100 - e) / 300, 0, 1))[:, None] * .7
    c = c * (1 - t_p) + pines * t_p
    t_r = np.clip((e - 1900) / 400, 0, 1)[:, None]
    c = c * (1 - t_r) + rock * t_r
    # late-autumn snow on the high Sierra: patchy from ~2450 m, continuous above ~2800 m
    patch = .5 + .5 * np.sin(xs * .0031 + np.sin(zs * .0023) * 2.1) * np.cos(zs * .0027 - xs * .0011)
    t_s = np.clip((e - 2450 - 220 * patch) / 260, 0, 1)[:, None]
    c = c * (1 - t_s) + snow * t_s
    return np.clip(c, 0, 255).astype(np.uint8)

def main():
    rings = []
    blobs = []
    for i, (x0, x1, z0, z1, s) in enumerate(RINGS):
        nx, nz = int(round((x1 - x0) / s)) + 1, int(round((z1 - z0) / s)) + 1
        xs = x0 + np.arange(nx) * s; zs = z0 + np.arange(nz) * s
        X, Z = np.meshgrid(xs, zs)
        h = heights(X.ravel(), Z.ravel()).reshape(nz, nx)
        # Seam: the outer border of an inner ring follows the next ring's coarser edges linearly.
        if i + 1 < len(RINGS):
            S = RINGS[i + 1][4]; k = int(S // s)
            for edge in (h[0, :], h[-1, :]):
                for a in range(0, nx - 1, k):
                    b_ = min(a + k, nx - 1); edge[a:b_ + 1] = np.linspace(edge[a], edge[b_], b_ - a + 1)
            for edge in (h[:, 0], h[:, -1]):
                for a in range(0, nz - 1, k):
                    b_ = min(a + k, nz - 1); edge[a:b_ + 1] = np.linspace(edge[a], edge[b_], b_ - a + 1)
        q = np.clip(np.round(h * 10), -32767, 32767).astype('<i2')
        entry = {'x0': x0, 'z0': z0, 'nx': nx, 'nz': nz, 's': s}
        if i > 0:
            px0, px1, pz0, pz1, _ = RINGS[i - 1]
            entry['hole'] = [int(round((px0 - x0) / s)), int(round((px1 - x0) / s)), int(round((pz0 - z0) / s)), int(round((pz1 - z0) / s))]
        blobs.append(q.tobytes())
        if i >= 2:
            col = far_colour(X.ravel(), Z.ravel(), h.ravel())
            # the rest of Granada beyond the modelled city: roofs and streets seen from afar
            import shapely
            urb = unary_union([a['g'] for a in osm.load()['areas'] if a['tags'].get('landuse') in ('residential', 'retail', 'commercial', 'industrial', 'railway')])
            m = shapely.contains_xy(urb, X.ravel(), Z.ravel())
            jit = np.random.default_rng(5).uniform(.88, 1.1, (m.sum(), 1))
            col[m] = np.clip(np.array([150, 128, 112]) * jit, 0, 255).astype(np.uint8)
            col = col.reshape(nz, nx, 3)
            blobs.append(col.tobytes()); entry['colour'] = True
        rings.append(entry)
        print('ring', i, nx, nz, f'{h.min():.0f}..{h.max():.0f}', flush=True)
    header = json.dumps({'E0': E0, 'rings': rings, 'source': 'IGN MDT05/MDT25/MDT200 (CC BY 4.0) + model'}).encode()
    raw = struct.pack('<I', len(header)) + header + b''.join(blobs)
    open(f'{PUBLIC}/data/terrain.bin', 'wb').write(gzip.compress(raw, 9))
    print('terrain.bin', len(raw), '->', os.path.getsize(f'{PUBLIC}/data/terrain.bin'))
    # landcover colour rasters for rings 0 and 1
    def hfn(x, z): return heights(x, z)
    for i, res in ((0, 1.0), (1, 4.0)):
        x0, x1, z0, z1, _ = RINGS[i]
        rgb, _ = landcover(x0, x1, z0, z1, res, hfn, seed=10 + i)
        Image.fromarray(rgb).save(f'{PUBLIC}/data/ground{i}.jpg', quality=86)
        print('ground', i, rgb.shape, os.path.getsize(f'{PUBLIC}/data/ground{i}.jpg'))



def rivers():
    """Open river courses (Darro, Genil) as polylines with heights, for water ribbons."""
    data = osm.load(); x0, x1, z0, z1 = RINGS[1][:4]; out = []
    for l in data['lines']:
        t = l['tags']
        if t.get('waterway') != 'river' or t.get('tunnel') or t.get('layer', '0').startswith('-'): continue
        g = l['g'].intersection(sbox(x0, z0, x1, z1))
        for seg in getattr(g, 'geoms', [g]):
            if seg.is_empty or seg.length < 20: continue
            n = max(2, int(seg.length / 4))
            pts = np.array([[seg.interpolate(i / (n - 1), normalized=True).x, seg.interpolate(i / (n - 1), normalized=True).y] for i in range(n)])
            # water surface: the lowest ground nearby, never rising downstream of a lower point is not enforced
            h = np.min(np.stack([heights(pts[:, 0] + dx, pts[:, 1] + dz) for dx, dz in ((0, 0), (3, 0), (-3, 0), (0, 3), (0, -3))]), 0) + .25
            w = 18.0 if 'Genil' in t.get('name', '') else 6.5
            out.append({'name': t.get('name', ''), 'w': w, 'p': [[round(float(a), 2), round(float(c), 2), round(float(b), 2)] for (a, b), c in zip(pts, h)]})
    json.dump(out, open(f'{PUBLIC}/data/rivers.json', 'w'), separators=(',', ':'))
    print('rivers', len(out), sum(len(r['p']) for r in out))

if __name__ == '__main__':
    if len(sys.argv) == 1: main()
    rivers()
