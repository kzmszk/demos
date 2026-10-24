"""Source packages for the hand-built (Blender) ruin districts: Shibuya crossing to 109, the Tocho, Roppongi Hills.
  python -m gen.hero_src      -> ASSETS/hero/<district>/  (buildings.obj, buildings_game.obj, context.obj, buildings.json,
                                  ground.obj, ground.npz, osm.json, cover.png, README.md), ASSETS/hero/exclude.json

Every building whose PLATEAU centroid lies in a district box is rebuilt by hand in Blender and left out of the procedural
city (gen.city reads exclude.json). Coordinates in the package are local to the district origin (ox, oy): x east,
y north, z = absolute height (T.P., metres) -- the same axes as Blender (z up): import the OBJs with forward_axis='Y',
up_axis='Z'. The game terrain is a 10 m grid of triangles; ground.obj is that exact surface."""
import os, sys, json, glob, pickle
import numpy as np
from PIL import Image
from .frame import ASSETS, PUBLIC, X0, Y0, X1, Y1
from .city import decay, roof_furniture, tag_landmarks, seed_of
from . import osm

OUT = os.path.join(ASSETS, 'hero')
# box = (x0, y0, x1, y1) in the city frame; origin = box centre rounded to 10 m so the 10 m terrain grid stays aligned
DISTRICTS = {
    'shibuya': dict(box=(-235, -75, 75, 175), title='渋谷 スクランブル交差点〜SHIBUYA109',
                    brief='the Shibuya scramble crossing (centre at 0,0), Hachiko square (statue at 9,-50), QFRONT, the old Seibu A/B, '
                          'MAGNET, Center-gai, Dogenzaka and Bunkamura-dori forking at SHIBUYA109 (-164, 9)'),
    'tocho': dict(box=(-880, 3100, -645, 3440), title='新宿 東京都庁',
                  brief='the Tokyo Metropolitan Government Building: No.1 main building (twin towers, 243 m) at (-800, 3341), '
                        'No.2 building (-765, 3157), the Assembly building and the semicircular Citizens\' Plaza between them'),
    'roppongi': dict(box=(2470, -140, 2830, 240), title='六本木ヒルズ',
                     brief='Roppongi Hills: Mori Tower (238 m) on its podium, 66 Plaza with the spider sculpture Maman (2657, 141), '
                           'Mohri Garden (2724, 94), TV Asahi, Keyakizaka street, the residences, Hollywood Plaza'),
}
MARGIN = 120.0


def origin(box):
    return round((box[0] + box[2]) / 2 / 10) * 10, round((box[1] + box[3]) / 2 / 10) * 10


def write_obj(path, objs, ox, oy, note=''):
    """objs: list of (name, V (n,3), F (m,3) 0-based)"""
    with open(path, 'w') as f:
        f.write(f'# TOKYO 2090 hero source. x east, y north, z up (T.P. m). local origin = city ({ox}, {oy}). {note}\n')
        base = 1
        for name, V, F in objs:
            f.write(f'o {name}\n')
            for x, y, z in V: f.write(f'v {x - ox:.3f} {y - oy:.3f} {z:.3f}\n')
            for a, b, c in F: f.write(f'f {a + base} {b + base} {c + base}\n')
            base += len(V)


def ground_grid():
    """the game's terrain ring 0: 10 m grid from X0-500, Y0-500, heights quantised to 0.1 m (terrain.bin)"""
    import gzip, struct
    raw = gzip.open(os.path.join(PUBLIC, 'data', 'terrain.bin')).read()
    n = struct.unpack('<I', raw[:4])[0]; head = json.loads(raw[4:4 + n]); r = head['rings'][0]
    h = np.frombuffer(raw[4 + n:4 + n + r['nx'] * r['ny'] * 2], np.int16).reshape(r['ny'], r['nx']).astype(np.float64) / 10
    return r, h


def ground_at(r, h, x, y):
    """the rendered surface: the 10 m cell split along the (c+1, w)-(c, w+1) diagonal, exactly like terrain.js"""
    fx = (np.asarray(x) - r['x0']) / r['s']; fy = (np.asarray(y) - r['y0']) / r['s']
    c = np.floor(fx).astype(int); w = np.floor(fy).astype(int); u = fx - c; v = fy - w
    h00 = h[w, c]; h10 = h[w, c + 1]; h01 = h[w + 1, c]; h11 = h[w + 1, c + 1]
    lo = h00 + u * (h10 - h00) + v * (h01 - h00)
    hi = h11 + (1 - u) * (h01 - h11) + (1 - v) * (h10 - h11)
    return np.where(u + v <= 1, lo, hi)


def main():
    bs = []
    for f in sorted(glob.glob(os.path.join(ASSETS, 'cache', 'plateau', '*.pkl'))): bs += pickle.load(open(f, 'rb'))
    tags = tag_landmarks(bs)
    o = osm.load()
    r, gh = ground_grid()
    cover = np.asarray(Image.open(os.path.join(PUBLIC, 'data', 'cover.png')))          # row 0 = north, 4 m
    exclude = {}
    for name, d in DISTRICTS.items():
        bx0, by0, bx1, by1 = d['box']; ox, oy = origin(d['box'])
        out = os.path.join(OUT, name); os.makedirs(out, exist_ok=True)
        inside = [b for b in bs if bx0 < b['cx'] < bx1 and by0 < b['cy'] < by1]
        ctx = [b for b in bs if bx0 - MARGIN < b['cx'] < bx1 + MARGIN and by0 - MARGIN < b['cy'] < by1 + MARGIN and b not in inside]
        exclude[name] = [b['id'] for b in inside]
        meta = []
        raw, game = [], []
        for k, b in enumerate(sorted(inside, key=lambda b: -(b['z1'] - b['z0']))):
            nm = f'b{k:03d}'
            meta.append(dict(obj=nm, id=b['id'], name=b.get('name'), use=b.get('use'), lod2=bool(b.get('lod2')), z0=round(b['z0'], 2), z1=round(b['z1'], 2),
                             height=round(b['z1'] - b['z0'], 1), cx=round(b['cx'] - ox, 1), cy=round(b['cy'] - oy, 1), tris=len(b['F'])))
            raw.append((nm, b['V'], b['F']))
            V, F, kind, zcut = decay(b, tags.get(b['id'], 0))
            if len(F): game.append((nm, V, F))
        cobj = []
        for b in ctx:
            V, F, kind, zcut = decay(b, tags.get(b['id'], 0))
            rng = np.random.default_rng(seed_of(b['id']) ^ 0x5bd1e995)
            ex = roof_furniture(b, V, F, kind, zcut, rng, tags.get(b['id'], 0))
            if ex is not None: V, F = np.concatenate([V, ex[0]]), np.concatenate([F, ex[1] + len(V)])
            if len(F): cobj.append(('c_' + str(seed_of(b['id']) & 0xffffff), V, F))
        write_obj(os.path.join(out, 'buildings.obj'), raw, ox, oy, 'PLATEAU LOD2 (2020s), the buildings to rebuild')
        write_obj(os.path.join(out, 'buildings_game.obj'), game, ox, oy, 'the same buildings as the procedural city decays them today')
        write_obj(os.path.join(out, 'context.obj'), cobj, ox, oy, 'the procedural neighbours that stay (do not export them)')
        json.dump(dict(district=name, title=d['title'], origin=[ox, oy], box=[bx0 - ox, by0 - oy, bx1 - ox, by1 - oy], buildings=meta), open(os.path.join(out, 'buildings.json'), 'w'), ensure_ascii=False, indent=1)
        # the ground: the exact game terrain triangles over box + margin, and the 10 m grid for scripts
        gx0 = r['x0'] + np.floor((bx0 - MARGIN - r['x0']) / 10) * 10; gy0 = r['y0'] + np.floor((by0 - MARGIN - r['y0']) / 10) * 10
        gx1 = r['x0'] + np.ceil((bx1 + MARGIN - r['x0']) / 10) * 10; gy1 = r['y0'] + np.ceil((by1 + MARGIN - r['y0']) / 10) * 10
        c0 = int((gx0 - r['x0']) / 10); w0 = int((gy0 - r['y0']) / 10); nc = int((gx1 - gx0) / 10) + 1; nw = int((gy1 - gy0) / 10) + 1
        H = gh[w0:w0 + nw, c0:c0 + nc]
        V = [(gx0 + c * 10, gy0 + w * 10, H[w, c]) for w in range(nw) for c in range(nc)]
        F = []
        for w in range(nw - 1):
            for c in range(nc - 1):
                a = w * nc + c; b_ = a + 1; cc = a + nc; dd = cc + 1
                F += [(a, b_, cc), (b_, dd, cc)]
        write_obj(os.path.join(out, 'ground.obj'), [('ground', np.asarray(V), np.asarray(F))], ox, oy, 'the game terrain, exactly as rendered')
        np.savez_compressed(os.path.join(out, 'ground.npz'), h=H.astype(np.float32), x0=gx0 - ox, y0=gy0 - oy, s=10.0)
        # OSM in the box + margin
        def near(g):
            b = g.bounds; return b[2] > bx0 - MARGIN and b[0] < bx1 + MARGIN and b[3] > by0 - MARGIN and b[1] < by1 + MARGIN
        L = lambda g: np.round(np.asarray(g.coords) - [ox, oy], 2).tolist()
        def polys(g):
            return [dict(outer=L(p.exterior), holes=[L(i) for i in p.interiors]) for p in (g.geoms if hasattr(g, 'geoms') else [g]) if p.geom_type == 'Polygon']
        js = dict(
            roads=[dict(hw=x['hw'], name=x['name'], width=round(x['width'], 1), bridge=x['bridge'], tunnel=x['tunnel'], layer=x['layer'],
                        footway=x['tags'].get('footway'), crossing=x['tags'].get('crossing'), line=L(x['line'])) for x in o['roads'] if near(x['line'])],
            areas=[dict(kind=x['kind'], name=x['tags'].get('name'), tags={k: v for k, v in x['tags'].items() if k in ('highway', 'area:highway', 'surface', 'layer')}, polys=polys(x['poly'])) for x in o['areas'] if near(x['poly'])],
            landuse=[dict(kind=x['kind'], name=x['tags'].get('name'), polys=polys(x['poly'])) for x in o['landuse'] if near(x['poly'])],
            water=[dict(polys=polys(x['poly'])) for x in o['water'] if near(x['poly'])],
            rails=[dict(rw=x['rw'], name=x['tags'].get('name'), bridge=x['bridge'], tunnel=x['tunnel'], layer=x['layer'], line=L(x['line'])) for x in o['rails'] if near(x['line'])],
            barriers=[dict(kind=x['kind'], height=x['height'], line=L(x['line'])) for x in o['barriers'] if near(x['line'])],
            trees=[np.round(np.asarray(x['xy']) - [ox, oy], 1).tolist() for x in o['trees'] if bx0 - MARGIN < x['xy'][0] < bx1 + MARGIN and by0 - MARGIN < x['xy'][1] < by1 + MARGIN],
            points=[dict(xy=np.round(np.asarray(x['xy']) - [ox, oy], 1).tolist(), tags={k: v for k, v in x['tags'].items() if not k.startswith(('addr', 'ref', 'opening', 'phone', 'website', 'check_date', 'source'))})
                    for x in o['points'] if bx0 - MARGIN < x['xy'][0] < bx1 + MARGIN and by0 - MARGIN < x['xy'][1] < by1 + MARGIN],
        )
        json.dump(js, open(os.path.join(out, 'osm.json'), 'w'), ensure_ascii=False)
        # cover crop (4 m/px, row 0 = north)
        H_ = cover.shape[0]
        px0 = int((bx0 - MARGIN - X0) / 4); px1 = int((bx1 + MARGIN - X0) / 4); py0 = H_ - int((by1 + MARGIN - Y0) / 4); py1 = H_ - int((by0 - MARGIN - Y0) / 4)
        Image.fromarray(cover[max(0, py0):py1, max(0, px0):px1]).save(os.path.join(out, 'cover.png'))
        print(name, 'origin', (ox, oy), len(inside), 'buildings', sum(len(b['F']) for b in inside), 'tris;', len(ctx), 'context;', {k: len(v) for k, v in js.items()})
    json.dump(exclude, open(os.path.join(OUT, 'exclude.json'), 'w'))


if __name__ == '__main__':
    main()
