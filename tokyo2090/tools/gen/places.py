"""Names on the map: landmark towers (balloons seen from far away), flat places (parks, shrines, stations) named when
you pass near, from OSM and PLATEAU.
  python -m gen.places     -> PUBLIC/data/places.json

towers: [name, en, x, y, top z, tier]   tier 1 = seen across the whole map, 2 = within ~3 km
areas:  [name, en, kind, x, y, ground z, radius, outline [[x, y]...] (simplified, <= 40 points)]"""
import os, json, glob, pickle
import numpy as np
from shapely.geometry import Point
from .frame import ASSETS, PUBLIC, X0, Y0, X1, Y1
from .city import decay, tag_landmarks
from . import osm
from .dem import Terrain

# (name, en, x, y, tier, search radius): the tallest PLATEAU building within the radius carries the label; its top is
# taken after the game's decay, so a broken tower is labelled at its broken top
TOWERS = [
    ('東京都庁', 'Tokyo Metropolitan Govt.', -800, 3341, 1, 40), ('六本木ヒルズ森タワー', 'Roppongi Hills Mori Tower', 2589, 84, 1, 60),
    ('東京ミッドタウン', 'Tokyo Midtown', 2784, 733, 1, 100), ('東京タワー', 'Tokyo Tower', 4066, -102, 1, 60),
    ('渋谷スクランブルスクエア', 'Shibuya Scramble Square', 153, -127, 1, 40), ('SHIBUYA109', 'SHIBUYA109', -168, 10, 2, 25),
    ('渋谷ヒカリエ', 'Shibuya Hikarie', 292, -44, 2, 40), ('セルリアンタワー', 'Cerulean Tower', -109, -353, 2, 40),
    ('ドコモタワー', 'NTT Docomo Yoyogi Bldg.', 234, 2761, 1, 40), ('コクーンタワー', 'Mode Gakuen Cocoon Tower', -325, 3560, 1, 40),
    ('新宿パークタワー', 'Shinjuku Park Tower', -864, 2846, 2, 50), ('東京オペラシティ', 'Tokyo Opera City', -1236, 2592, 2, 60),
    ('麻布台ヒルズ', 'Azabudai Hills', 3588, 128, 1, 50), ('虎ノ門ヒルズ', 'Toranomon Hills', 4406, 811, 2, 60),
    ('国立競技場', 'Japan National Stadium', 1267, 2018, 2, 120), ('国立代々木競技場', 'Yoyogi National Gymnasium', -74, 849, 2, 90),
    ('渋谷ストリーム', 'Shibuya Stream', 237, -257, 2, 30), ('京王プラザホテル', 'Keio Plaza Hotel', -560, 3377, 2, 40),
    ('アークヒルズ仙石山森タワー', 'Ark Hills Sengokuyama', 3737, 448, 2, 40),
]
# OSM polygons by exact name (landuse / areas), or a point and radius for places without one
AREAS = [
    ('明治神宮', 'Meiji Jingu', 'shrine'), ('代々木公園', 'Yoyogi Park', 'park'), ('新宿御苑', 'Shinjuku Gyoen', 'park'),
    ('明治神宮外苑', 'Jingu Gaien', 'park'), ('青山霊園', 'Aoyama Cemetery', 'park'), ('新宿中央公園', 'Shinjuku Central Park', 'park'),
    ('赤坂御用地', 'Akasaka Estate', 'park'), ('有栖川宮記念公園', 'Arisugawa Park', 'park'), ('芝公園', 'Shiba Park', 'park'),
    ('増上寺', 'Zojoji', 'shrine'), ('檜町公園', 'Hinokicho Park', 'park'), ('明治神宮野球場', 'Jingu Stadium', 'park'),
]
POINT_AREAS = [   # name, en, kind, x, y, radius
    ('スクランブル交差点', 'Shibuya Crossing', 'place', 0, 0, 40), ('表参道', 'Omotesando', 'street', 760, 950, 60), ('竹下通り', 'Takeshita-dori', 'street', 330, 1330, 40),
    ('六本木交差点', 'Roppongi Crossing', 'place', 2830, 420, 35), ('宮下公園', 'Miyashita Park', 'park', 120, 230, 40), ('東急本店跡', 'Bunkamura', 'place', -330, 120, 40), ('迎賓館', 'Akasaka Palace', 'place', 2560, 2440, 120),
]
STATIONS = [   # JR and private railway stations above ground: name, en, x, y
    ('渋谷駅', 'Shibuya Sta.', 112, -100), ('原宿駅', 'Harajuku Sta.', 172, 1188), ('代々木駅', 'Yoyogi Sta.', 140, 2712), ('新宿駅', 'Shinjuku Sta.', -1, 3412),
    ('恵比寿駅', 'Ebisu Sta.', 877, -1450), ('千駄ケ谷駅', 'Sendagaya Sta.', 981, 2414), ('信濃町駅', 'Shinanomachi Sta.', 1807, 2276), ('四ツ谷駅', 'Yotsuya Sta.', 2723, 2943),
    ('参宮橋駅', 'Sangubashi Sta.', -621, 2134), ('南新宿駅', 'Minami-Shinjuku Sta.', -151, 2685), ('代々木八幡駅', 'Yoyogi-Hachiman Sta.', -1058, 1122),
    ('神泉駅', 'Shinsen Sta.', -638, -255), ('駒場東大前駅', 'Komaba-Todaimae Sta.', -1456, -93), ('代官山駅', 'Daikanyama Sta.', 250, -1260),
    ('初台駅', 'Hatsudai Sta.', -1293, 2402), ('西武新宿駅', 'Seibu-Shinjuku Sta.', -46, 3982), ('田町駅', 'Tamachi Sta.', 4271, -1527),
]


def main():
    bs = []
    for f in sorted(glob.glob(os.path.join(ASSETS, 'cache', 'plateau', '*.pkl'))): bs += pickle.load(open(f, 'rb'))
    tags = tag_landmarks(bs)
    T = Terrain(); o = osm.load()
    towers = []
    for name, en, x, y, tier, r in TOWERS:
        near = [b for b in bs if abs(b['cx'] - x) < r and abs(b['cy'] - y) < r]
        if not near: print('no building for', name); continue
        b = max(near, key=lambda b: b['z1'] - b['z0'])
        V, F, kind, zcut = decay(b, tags.get(b['id'], 0))
        top = float(V[F].reshape(-1, 3)[:, 2].max()) if len(F) else b['z1']
        # the label sits over the highest part of what stands
        Vt = V[F].reshape(-1, 3); hi = Vt[Vt[:, 2] > top - 3]
        towers.append([name, en, round(float(hi[:, 0].mean()), 1), round(float(hi[:, 1].mean()), 1), round(top, 1), tier])
        print(f'{name:16s} {b.get("name")} H {b["z1"] - b["z0"]:.0f} top {top:.0f} (z0 {b["z0"]:.0f})')
    areas = []
    polys = {}
    for l in o['landuse'] + o['areas']:
        n = l['tags'].get('name')
        if n: polys.setdefault(n, []).append(l['poly'])
    for name, en, kind in AREAS:
        ps = polys.get(name)
        if not ps: print('no polygon for', name); continue
        from shapely.ops import unary_union
        g = unary_union(ps)
        if g.geom_type == 'MultiPolygon': g = max(g.geoms, key=lambda p: p.area)
        c = g.representative_point(); rad = (g.area / np.pi) ** 0.5
        ring = g.exterior.simplify(max(4.0, rad * 0.04))
        pts = np.asarray(ring.coords)
        if len(pts) > 40: pts = pts[np.linspace(0, len(pts) - 1, 40).astype(int)]
        areas.append([name, en, kind, round(c.x, 1), round(c.y, 1), round(float(T(c.x, c.y)), 1), round(rad, 0), np.round(pts, 0).tolist()])
        print(f'{name:12s} r {rad:.0f} at {c.x:.0f},{c.y:.0f} pts {len(pts)}')
    for name, en, kind, x, y, r in POINT_AREAS:
        areas.append([name, en, kind, x, y, round(float(T(x, y)), 1), r, []])
    for name, en, x, y in STATIONS:
        if X0 < x < X1 and Y0 < y < Y1: areas.append([name, en, 'station', x, y, round(float(T(x, y)), 1), 60, []])
    json.dump(dict(towers=towers, areas=areas), open(os.path.join(PUBLIC, 'data', 'places.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    print(len(towers), 'towers', len(areas), 'areas', os.path.getsize(os.path.join(PUBLIC, 'data', 'places.json')), 'bytes')


if __name__ == '__main__':
    main()
