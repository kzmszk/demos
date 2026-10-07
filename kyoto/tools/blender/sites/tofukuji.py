"""東福寺 (臨済宗東福寺派大本山) — the hero site: 洗玉澗 and its three bridges (通天橋 with the 舞台, 臥雲橋, 偃月橋), the
corridors to the 本堂 and to the 常楽庵, the 三門 (国宝) with the 思遠池, the 本堂, the 方丈 with 重森三玲's 八相の庭,
庫裏, 開山堂 / 伝衣閣 and 樓門, 禅堂, 東司, 経蔵, 浴室, 鐘楼, the gates (日下門, 六波羅門, 勅使門, 月下門, 恩賜門, 西唐門), walls,
lanterns, and the 通天もみじ in the ravine.

Modules: tofukuji_lib (helpers), tofukuji_valley (ravine ground, stream, valley paths, trees), tofukuji_bridges (bridges,
corridors, 通天台), tofukuji_sanmon (三門, 思遠池), tofukuji_halls (本堂, 方丈, 庫裏, 禅堂, 東司, 経蔵, 浴室, 鐘楼, gates,
walls), tofukuji_garden (八相の庭), tofukuji_kaisando (常楽庵: 昭堂 + 伝衣閣, 開山堂, 樓門, garden).
Parts for run_site --only: valley, bridges, sanmon, halls, garden, kaisando, trees.
References: /home/kazu/work/kyoto-assets/refs/tofukuji (dossier.md, manifest.json, photos)."""
import sys, time, math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from sites import tofukuji_lib as L
from sites import tofukuji_klib as K
from sites import tofukuji_valley as VAL
from sites import tofukuji_bridges as BR
from sites import tofukuji_sanmon as SAN
from sites import tofukuji_halls as HL
from sites import tofukuji_garden as GD
from sites import tofukuji_kaisando as KS
from sites import tofukuji_grounds as GR

# preview cameras (x, y, z world) matching the reference photos
SHOTS = [
    ('tsutenkyo_from_gaun', (1287.5, -925.8, 43.45), (1356.0, -944.5, 48.2), 50),     # tsuten_from_gaun.jpg (CC0): the bridge across a sea of maples
    ('valley_from_stage', (1354.0, -944.4, 49.4), (1300.0, -926.0, 40.5), 26),       # from the 舞台 west over the ravine (valley_from_bridge.jpg)
    ('tsutenkyo_side', (1382.6, -951.8, 52.3), (1356.0, -944.5, 48.6), 30),          # tsuten_side_green.jpg: the bridge from the 通天台
    ('sanmon_front', (1364.6, -1153.5, 50.8), (1366.0, -1120.6, 57.5), 24),          # sanmon_front.jpg (from the pond bridge)
    ('sanmon_pond', (1346.0, -1164.2, 50.9), (1372.0, -1126.0, 56.0), 22),           # sanmon_oblique_pond.jpg (across the 思遠池)
    ('hondo', (1370.0, -1094.0, 50.6), (1370.5, -1049.0, 61.0), 24),                 # hondo_front.jpg
    ('hondo_oblique', (1408.0, -1086.0, 50.8), (1372.0, -1050.0, 60.0), 24),       # hondo_oblique.jpg
    ('kuri', (1392.0, -1008.5, 51.6), (1420.0, -1007.0, 57.5), 26),                 # kuri_front.jpg
    ('zendo', (1336.0, -1104.0, 49.6), (1307.0, -1071.0, 54.0), 26),                # zendo.jpg (from the south-east)
    ('kyozo', (1322.0, -1031.0, 50.2), (1322.4, -1005.9, 55.0), 26),               # kyozo.jpg
    ('garden_south', (1412.0, -983.5, 51.2), (1380.0, -990.5, 49.0), 24),            # garden_south_west.jpg (from the east end of the veranda)
    ('garden_west', (1378.3, -960.8, 52.0), (1373.0, -969.0, 48.5), 24),             # garden_west.jpg (Hiro2006)
    ('garden_north', (1389.5, -960.6, 51.0), (1405.0, -957.0, 48.5), 26),            # garden_north.jpg (Zairon)
    ('garden_east', (1418.0, -982.0, 51.6), (1425.5, -987.0, 48.6), 26),             # garden_east.jpg
    ('kaisando', (1387.6, -876.0, 55.9), (1393.4, -846.0, 58.6), 26),                # kaizando.jpg (from the path by the 樓門)
    ('aerial', (1262.0, -1145.0, 128.0), (1382.0, -998.0, 46.0), 24),
]

import os
if os.environ.get('TOFU_SHOTS'):        # render a subset while iterating: TOFU_SHOTS=name,name
    SHOTS = [s_ for s_ in SHOTS if s_[0] in os.environ['TOFU_SHOTS'].split(',')]

COUNTS = []
def step(B, name, fn, *a, **kw):
    n0 = B.ntri('main') + B.ntri('detail')
    r = fn(*a, **kw)
    COUNTS.append((name, B.ntri('main') + B.ntri('detail') - n0))
    return r

def build(B, S, only=None):
    want = lambda p: only is None or p in only
    t0 = time.time()
    info = {}
    # repair the DEM over the 思遠池 (bogus 53-55 m heights over the water)
    L.fill_dem(S, Polygon(L.osm_poly(S, 'water', 775829465)).buffer(0), margin=1.5, band=3.0)
    V = VAL.Valley(S); info['valley'] = V
    # keep the ravine's trees off the bridges / corridors / platforms
    loc = BR.tsu_loc()
    ko = [Polygon([loc.w(u, v) for (u, v) in ((-3.2, BR.V0 - 1), (3.2, BR.V0 - 1), (3.2, BR.V1 + 1), (-3.2, BR.V1 + 1))]),
          Polygon([loc.w(u, v) for (u, v) in ((BR.ST_U - 1.6, BR.ST_V[0] - 2.4), (-2.0, BR.ST_V[0] - 2.4), (-2.0, BR.ST_V[1] + 2.4), (BR.ST_U - 1.6, BR.ST_V[1] + 2.4))]),
          LineString([(1285.55, -933.4), (1287.85, -911.4)]).buffer(2.4), LineString([(1459.65, -988.4), (1461.75, -967.6)]).buffer(2.2),
          Polygon([(1378, -961), (1388, -961), (1388, -948.5), (1378, -948.5)]),
          LineString([(1360.5, -929), (1360.6, -894)]).buffer(3.0)]
    keep_out = unary_union(ko)
    decks = unary_union([ko[0], ko[1], LineString([(1285.55, -933.4), (1287.85, -911.4)]).buffer(1.6), LineString([(1459.65, -988.4), (1461.75, -967.6)]).buffer(1.4)])
    if want('valley'):
        step(B, 'valley_ground', V.build_ground, B); step(B, 'stream', V.build_stream, B, skip=decks); step(B, 'valley_paths', V.build_paths, B)
        print(f'valley {B.ntri()} tris {time.time()-t0:.1f}s', flush=True)
    if want('bridges'):
        info['tsu'] = step(B, 'tsutenkyo', BR.tsutenkyo, B, S, V)
        info['cor'] = step(B, 'corridors', BR.corridors, B, S)
        step(B, 'tsutendai', BR.tsutendai, B, S)
        info['gaun'] = step(B, 'gaunkyo', BR.gaunkyo, B, S, V)
        info['engetsu'] = step(B, 'engetsukyo', BR.engetsukyo, B, S, V)
        print(f'bridges {B.ntri()} tris {time.time()-t0:.1f}s', flush=True)
    if want('sanmon'):
        info['sanmon'] = step(B, 'sanmon', SAN.build, B, S)
        info['pond'] = step(B, 'pond', SAN.pond, B, S)
        print(f'sanmon {B.ntri()} tris {time.time()-t0:.1f}s', flush=True)
    if want('halls'):
        info['hondo'] = step(B, 'hondo', HL.hondo, B, S)
        info['hojo'] = step(B, 'hojo', HL.hojo, B, S)
        step(B, 'karamon', HL.karamon_gates, B, S); step(B, 'hojo_walls', HL.hojo_walls, B, S); step(B, 'hojo_kuri', HL.hojo_kuri_corridor, B, S)
        info['kuri'] = step(B, 'kuri', HL.kuri, B, S)
        info['zendo'] = step(B, 'zendo', HL.zendo, B, S)
        for nm in ('tosu', 'kyozo', 'yokushitsu', 'shoro', 'gates'):
            step(B, nm, getattr(HL, nm), B, S)
        print(f'halls {B.ntri()} tris {time.time()-t0:.1f}s', flush=True)
    if want('garden'):
        info['garden'] = step(B, 'gardens', GD.build, B, S)
    if want('kaisando'):
        step(B, 'shodo', KS.shodo, B, S); step(B, 'romon', KS.romon, B, S); step(B, 'kaisan_garden', KS.garden, B, S); step(B, 'fumonin', KS.fumonin, B, S)
    if want('grounds'):
        step(B, 'grounds', GR.build, B, S)
    if want('trees'):
        tr = V.plant(B, keep_out, deck_z=BR.ZB, views=[((1287.5, -925.8, 43.45), (1356.0, -944.5, 46.6), 5.0)])
        print(f'valley trees {len(tr)}', flush=True)
    # site edits
    finish(B, S, info)
    if '--shots' in sys.argv and B.trees and not os.environ.get('TOFU_NOTREES'):
        try: K.preview_trees(B.trees, name='preview_trees_not_exported')
        except Exception as e: print('preview trees:', e)
    print('drawn triangles by part: ' + ', '.join(f'{n} {c // 1000}k' for n, c in COUNTS), flush=True)
    print(f'tofukuji: {B.ntri()} tris ({B.ntri("main")} main, {B.ntri("detail")} detail), {len(B.trees)} trees, {len(B.lamps)} lamps {time.time()-t0:.1f}s', flush=True)
    return info

# generic buildings replaced here (OSM ids; the generic PLATEAU building whose point lies in the buffered outline is dropped)
REPLACED = [223970374, 766621673, 766621661, 766621628, 766621670, 775463884, 766621637, 766621632, 223970375, 223970394, 223970402,
            223970386, 770974026, 770973993, 770973994, 770973996, 766621667, 766621664, 770973992]
EXTRA_EXCLUDE = [
    [(1352.0, -1031.0), (1360.0, -1031.0), (1361.0, -958.0), (1352.5, -958.0)],          # 通天橋 south corridor (ticket booth, gate)
    [(1355.5, -931.0), (1365.0, -931.0), (1365.2, -899.5), (1388.0, -900.5), (1389.0, -884.0), (1382.0, -883.0), (1381.5, -893.5), (1355.5, -892.5)],   # north corridor + covered stair
    [(1376.0, -964.0), (1390.0, -964.0), (1390.0, -948.0), (1376.0, -948.0)],              # 通天台
    [(1410.0, -980.5), (1419.5, -980.5), (1419.5, -994.5), (1410.0, -994.5)],              # 方丈 - 庫裏 corridor (PLATEAU 269ef48b)
    # open areas this site models itself (no generic buildings inside): keep the generic hedges / walls / trees out
    [(1341.5, -1168.0), (1389.0, -1168.0), (1389.0, -1139.5), (1341.5, -1139.5)],          # 思遠池 with its hedges
    [(1366.0, -998.0), (1434.0, -998.0), (1434.0, -978.6), (1416.0, -978.6), (1416.0, -954.0), (1366.0, -954.0)],   # 方丈 and the 八相の庭
]
KAISAN_OPEN = [(-11.5, -34.5), (22.5, -34.5), (22.5, -6.5), (-11.5, -6.5)]                 # 開山堂 garden (local frame of tofukuji_kaisando)

def finish(B, S, info):
    """exclusions; the preview terrain (run_site renders S.ground) follows the cuts, like the viewer"""
    for b in S.osm['buildings']:
        if b['id'] in REPLACED:
            pg = Polygon(L.ring_of(b)).buffer(2.0, join_style=2)
            S.exclude.append([list(map(float, p)) for p in pg.exterior.coords])
    for r in EXTRA_EXCLUDE:
        S.exclude.append([list(map(float, p)) for p in r])
    lk = KS.loc()
    S.exclude.append([list(map(float, lk.w(u, v))) for (u, v) in KAISAN_OPEN])
    # the PLATEAU block that joins 開山堂, 普門院 and their annexes (modelled in tofukuji_kaisando), the 樓門 wings
    for pb in S.plateau:
        if pb['id'].startswith('bldg_7dd2addd') or pb['id'].startswith('bldg_dd4882f6') or pb['id'].startswith('bldg_49f50208') or pb['id'].startswith('bldg_850c9c04'):
            pg = Polygon(L.ring_of(pb)).buffer(1.0, join_style=2)
            S.exclude.append([list(map(float, p)) for p in pg.exterior.coords])
    # preview terrain (not exported): under the own grounds
    V = info.get('valley')
    if V is not None:
        zv = V.zfn                                   # evaluate before the DEM changes
        L.lower_preview_terrain(S, V.poly, None, fn=lambda x, y: zv(x, y) - 0.35, shrink=-1.0)
    if info.get('pond') is not None:
        L.lower_preview_terrain(S, info['pond'], SAN.POND_LEVEL - 0.9, shrink=1.0)
