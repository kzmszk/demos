"""Export the data a hero site script needs (venv python):  python site_data.py SITE [margin]
-> /home/kazu/work/kyoto-assets/sites/<SITE>/site.json + terrain.npz

site.json: {name, bounds [x0,y0,x1,y1] (local frame, metres), polygon (the OSM precinct, if any), osm: {buildings, ways,
water, barriers, trees, points, landuse}, plateau: [buildings with footprint, z0, h, roof polygons]} — coordinates in the
local frame (x east, y north, z = T.P.).  terrain.npz: H (2 m grid, rows = y), x0, y0, res."""
import sys, os, json, math
import numpy as np
import shapely
from shapely.geometry import box, mapping, Point
from gen import world as W
from gen.frame import ASSETS

SITES = {
    # name: (OSM polygon ids (union), extra box [x0, y0, x1, y1] or None, margin)
    'kiyomizu': ([336641107, 339352245], [1650, 750, 2560, 1460], 40),       # + 清水坂 / 産寧坂 / 二年坂 / 八坂の塔
    'fushimi_inari': ([96291583], [700, -2500, 2500, -1500], 30),
    'sanjusangendo': ([31842037], None, 60),
    'eikando': ([859305371], None, 60),
    'ginkakuji': ([105817561], [3330, 4430, 3800, 4700], 50),                 # + the approach from 銀閣寺橋
    'gion': ([328903218], [1180, 1750, 2120, 2700], 20),                     # 花見小路, 白川, 新橋, 四条通 to 八坂神社
    'station': ([], [-500, -250, 450, 350], 0),                              # 京都駅ビル, 京都タワー, 烏丸口
    'tofukuji': ([768987591], None, 40),                                       # 東福寺: 三門, 本堂, 方丈庭園, 通天橋と洗玉澗, 臥雲橋, 偃月橋
    'toji': ([359896810], None, 40),                                           # 東寺 (教王護国寺): 五重塔, 金堂, 講堂, 南大門, 堀
    'kinkakuji': ([98115917], None, 60),                                       # 金閣寺 (鹿苑寺): 舎利殿, 鏡湖池, 方丈, 夕佳亭 (the kinkaku enclave)
    'arashiyama': ([519319727], [-8100, 2650, -7000, 3360], 20),               # 渡月橋, 桂川 (大堰川) and 中之島, the banks, 長辻通 to 天龍寺's gate
    'tenryuji': ([409723494, -17656638, 925807376, 677236682, 319336216], [-8400, 3200, -7450, 3850], 20),  # 天龍寺, 竹林の小径, 野宮神社, 大河内山荘, 亀山, 常寂光寺
    'higashiyama': ([371717423, 1316622873], [1680, 1000, 2240, 1750], 20),  # 八坂通・八坂の塔, 二年坂, 産寧坂, 清水坂 (below the 仁王門), 石塀小路, ねねの道
}

def lines(geom):
    if geom.geom_type == 'LineString': return [list(map(list, geom.coords))]
    if hasattr(geom, 'geoms'): return [list(map(list, g.coords)) for g in geom.geoms if g.geom_type == 'LineString']
    return []

def polys(geom):
    out = []
    for g in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
        if g.geom_type == 'Polygon' and not g.is_empty:
            out.append([list(map(list, g.exterior.coords))[:-1]] + [list(map(list, r.coords))[:-1] for r in g.interiors])
    return out

def r2(x): return [[round(c, 3) for c in p] for p in x] if isinstance(x, list) else x

def main(name):
    w = W.load()
    ids, extra, margin = SITES[name]
    lu = {f['id']: f for f in w.osm['landuse']}
    g = shapely.unary_union([lu[i]['poly'] for i in ids if i in lu]) if ids else None
    if extra is not None:
        eb = box(*extra)
        bounds_geom = eb if g is None else shapely.unary_union([g, eb])
    else: bounds_geom = g
    bounds_geom = bounds_geom.buffer(margin)
    x0, y0, x1, y1 = bounds_geom.bounds
    R = box(x0, y0, x1, y1)
    out = dict(name=name, bounds=[x0, y0, x1, y1], polygon=polys(g) if g is not None else [], osm={}, plateau=[])
    o = w.osm
    out['osm']['buildings'] = [dict(id=f['id'], tags=f['tags'], poly=polys(f['poly'])) for f in o['buildings'] if f['poly'].intersects(R)]
    out['osm']['ways'] = [dict(id=r['id'], tags=r['tags'], line=lines(r['line'].intersection(R.buffer(30))), width=r['width']) for r in o['roads'] if r['line'].intersects(R)]
    out['osm']['water'] = [dict(id=f['id'], tags=f['tags'], poly=polys(f['poly'].intersection(R.buffer(30)))) for f in o['water'] if f['poly'].intersects(R)]
    out['osm']['waterways'] = [dict(id=f['id'], tags=f['tags'], line=lines(f['line'].intersection(R.buffer(30)))) for f in o['waterways'] if f['line'].intersects(R)]
    out['osm']['barriers'] = [dict(id=f['id'], kind=f['kind'], tags=f['tags'], line=lines(f['line'].intersection(R.buffer(10)))) for f in o['barriers'] if f['line'].intersects(R)]
    out['osm']['landuse'] = [dict(id=f['id'], kind=f['kind'], tags=f['tags'], poly=polys(f['poly'].intersection(R.buffer(30)))) for f in o['landuse'] if f['poly'].intersects(R)]
    out['osm']['trees'] = [dict(id=t['id'], xy=list(t['xy']), tags=t['tags']) for t in o['trees'] if R.contains(Point(t['xy']))]
    out['osm']['points'] = [dict(id=p['id'], xy=list(p['xy']), tags=p['tags']) for p in o['points'] if R.contains(Point(p['xy']))]
    for k in w.btree.query(R):
        b = w.buildings[k]
        rec = dict(id=b.id, kind=b.kind, z0=b.z0, h=b.h, st=b.st, year=b.year, struct=b.struct, tags=b.tags, poly=polys(b.poly))
        if b.lod2 and b.lod2.get('R'):
            rec['roof'] = [[np.asarray(r, float).round(3).tolist() for r in rings] for rings in b.lod2['R']]
        out['plateau'].append(rec)
    d = os.path.join(ASSETS, 'sites', name); os.makedirs(d, exist_ok=True)
    json.dump(out, open(os.path.join(d, 'site.json'), 'w'), ensure_ascii=False, separators=(',', ':'), default=float)
    T = w.terrain
    res = 1.0
    xs = np.arange(x0, x1 + res, res); ys = np.arange(y0, y1 + res, res)
    X, Y = np.meshgrid(xs, ys)
    H = T(X.ravel(), Y.ravel()).reshape(X.shape).astype(np.float32)
    np.savez_compressed(os.path.join(d, 'terrain.npz'), H=H, x0=xs[0], y0=ys[0], res=res)
    print(name, 'bounds', [round(v) for v in (x0, y0, x1, y1)], 'osm buildings', len(out['osm']['buildings']), 'ways', len(out['osm']['ways']), 'plateau', len(out['plateau']), 'H', H.shape)

if __name__ == '__main__':
    for n in (sys.argv[1:] or SITES):
        main(n)
