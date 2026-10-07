"""京都タワー + 京都駅ビル (north side) + 烏丸口 bus plaza -- the start point of the KYOTO demo.

  station_tower  the Kyoto Tower Building (31 m) and the 100 m tower
  station_hall   the station building: gate, arcade + atrium glass, notch tower, podium + blue tower, Hotel Granvia, Isetan wing
  station_plaza  forecourt paving, bus canopies A/B/C/JR/D, taxi rank, lamps, trees, blockers
  station_util   vectorised helpers;  station_preview  preview-only tweaks (tints, sun)

Site frame = metres from the station's central exit (x east, y north), z = T.P.  Run:
  blender -b --python blender/run_site.py -- station --shots"""
import numpy as np
from . import station_util as U
from . import station_tower as T
from . import station_hall as H
from . import station_plaza as P
from . import station_preview  # noqa: F401  (preview-only: honour vertex tints, higher sun)

# camera heights are absolute (T.P.): the plaza is ~28.2 m, eye height 1.7 m -> 29.9
SHOTS = [
    ('01_tower_from_plaza', (39.0, 64.0, 29.9), (47.0, 194.0, 76.0), 22),                  # the demo's first view
    ('02_station_from_shiokoji', (-3.0, 164.0, 31.0), (-14.0, 40.0, 46.0), 20),
    ('03_tower_top', (30.0, 140.0, 126.0), (48.3, 194.4, 128.0), 55),
    ('04_plaza_aerial', (-60.0, 215.0, 95.0), (-10.0, 90.0, 28.0), 28),
    ('05_concourse_entrance', (-47.0, 84.0, 30.0), (-47.0, 50.0, 30.0), 22),
    ('06_atrium_arcade', (40.0, 80.0, 31.0), (15.0, 40.0, 38.0), 22),
    ('07_station_aerial', (-80.0, 175.0, 140.0), (-10.0, 20.0, 40.0), 30),
    ('08_tower_base', (10.0, 120.0, 42.0), (48.0, 190.0, 44.0), 40),
    ('09_granvia', (150.0, 112.0, 36.0), (100.0, 45.0, 30.0), 22),
    ('10_west_wing', (-170.0, 130.0, 60.0), (-150.0, 20.0, 35.0), 24),
    ('11_from_karasuma', (92.0, 146.0, 31.0), (-30.0, 40.0, 38.0), 24),
    ('12_air_north', (-20.0, 330.0, 190.0), (-20.0, 20.0, 40.0), 30),
    ('13_tower_night', (39.0, 64.0, 29.9), (47.0, 194.0, 76.0), 22),
    ('14_plaza_night', (-47.0, 84.0, 30.0), (-47.0, 50.0, 30.0), 22),
]

KEEP = {'76b9f0de'}                      # the bus information building stays generic
def exclusions(S):
    from shapely.geometry import Polygon, box
    island = box(-97, 67, 37, 148); forecourt = box(-103, 40, 60, 68)
    east = box(37, 68, 72, 112)            # the low kiosks / mall entrances east of the terminal (they block the first view)
    for p in S.plateau:
        pid = p['id'][-8:]
        ring = p['poly'][0][0]
        pg = Polygon(ring)
        if pg.is_empty: continue
        rp = pg.representative_point()
        ex = pid in ('e87c8c7f', '53421b83', '0f173d5d')
        if not ex and island.contains(rp) and pid not in KEEP: ex = True
        if not ex and (forecourt.contains(rp) or east.contains(rp)) and p['kind'] in ('shed', 'house', 'mid'): ex = True
        if ex:
            S.exclude.append([[float(x), float(y)] for (x, y) in pg.buffer(0.6).exterior.coords])

def service_building(B, S):
    """the bus terminal's service building (OSM 159160294), 4.5 m, grey"""
    ring = U.ccw(np.array([(-46.0, 118.8), (7.2, 119.5), (7.3, 108.0), (-1.7, 107.9), (-1.7, 111.8), (-15.1, 111.6), (-15.0, 107.7), (-45.9, 107.4)]))
    z = float(S.ground(-20, 113))
    U.wall_ring(B, ring, z - 0.3, z + 4.6, 'wall_concrete', zg=z, c0=(176, 176, 172, 30), c1=(0, 0, 6, 0))
    H.roof(B, ring, z + 4.6, z, (130, 128, 124), 0.5)

def build(B, S, only=None):
    parts = set(only) if only else {'tower', 'hall', 'plaza'}
    stats = {}
    n0 = B.ntri()
    if 'tower' in parts:
        zb = T.build_building(B, S)
        T.build_tower(B, S, zb)
        stats['tower'] = B.ntri() - n0; n0 = B.ntri()
    if 'hall' in parts:
        H.build_front(B, S)
        H.build_east(B, S)
        H.build_west(B, S)
        H.build_middle(B, S)
        H.build_facades(B, S)
        H.evening_lights(B, S)
        stats['station'] = B.ntri() - n0; n0 = B.ntri()
    if 'plaza' in parts:
        P.build_plaza(B, S)
        service_building(B, S)
        stats['plaza'] = B.ntri() - n0; n0 = B.ntri()
        P.blockers(B, S)
    exclusions(S)
    B.paint_debug = [(e['poly'], e['surf'], max(float(S.ground(x, y)) for (x, y) in e['poly']) + 0.2) for e in S.paint]
    print('station parts (tris):', stats, 'excluded generic buildings:', len(S.exclude), flush=True)
