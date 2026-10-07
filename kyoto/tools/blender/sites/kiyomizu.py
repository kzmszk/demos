"""清水寺 (Kiyomizu-dera): the temple precinct from the 仁王門 forecourt to the 奥の院, 音羽の滝 and 子安塔, for the KYOTO
demo.  Parts (--only): hondo (本堂 + 舞台 + 懸造), halls (the other buildings), ground (exclusion, paint, stairs, walls,
lanterns, plain secondary buildings), trees.  Helpers: kiyomizu_lib, kiyomizu_hondo, kiyomizu_halls, kiyomizu_ground."""
import sys, time
import numpy as np
from sites import kiyomizu_lib as K
from sites import kiyomizu_hondo as HONDO
from sites import kiyomizu_halls as HALLS
from sites import kiyomizu_ground as GROUND

# preview cameras matching the reference photos (refs/kiyomizu/*)
SHOTS = [
    ('stage_from_okunoin', (2432.6, 970.4, 118.4), (2396.0, 987.0, 114.5), 28),     # the classic view (okunoin__*d1c7, postcards)
    ('niomon_from_below', (2221.5, 1076.8, 101.9), (2240.0, 1068.4, 110.0), 22),     # niomon__Kyoto-08 (between the komainu)
    ('pagoda', (2249.5, 1057.5, 106.4), (2281.0, 1031.0, 121.0), 26),               # saimon__Saimon_1 (up the stairs to 西門 and the 三重塔)
    ('stage_from_below', (2398.5, 946.0, 99.6), (2394.5, 989.0, 110.0), 26),         # honden-stage__GregTheBusker / 13310637593
    ('aerial', (2255.0, 890.0, 215.0), (2345.0, 1010.0, 112.0), 28),
    ('otowa', (2406.3, 953.8, 98.0), (2417.0, 956.6, 99.8), 26),                     # otowa-taki__At_Kyoto_2024_492
    ('from_stage', (2387.0, 984.0, 117.2), (2340.0, 950.0, 108.0), 28),               # honden-stage__13310856244 (the stage looking to the city)
    ('hall_east', (2432.0, 1012.0, 117.0), (2392.0, 1002.0, 123.5), 30),              # honden-front__13310851334
]

def lower_terrain(S, ring, zmax):
    import shapely
    from shapely.geometry import Polygon
    pg = Polygon(ring).buffer(-0.2)
    x0, y0, x1, y1 = pg.bounds
    i0 = max(0, int((x0 - S.x0) / S.res)); i1 = min(S.H.shape[1] - 1, int((x1 - S.x0) / S.res) + 1)
    j0 = max(0, int((y0 - S.y0) / S.res)); j1 = min(S.H.shape[0] - 1, int((y1 - S.y0) / S.res) + 1)
    J, I = np.mgrid[j0:j1 + 1, i0:i1 + 1]
    ins = shapely.contains_xy(pg, S.x0 + I * S.res, S.y0 + J * S.res)
    sub = S.H[j0:j1 + 1, i0:i1 + 1]
    sub[ins] = np.minimum(sub[ins], zmax)

def build(B, S, only=None):
    want = lambda p: only is None or p in only
    info = {}
    t0 = time.time()
    if want('hondo'):
        hi = HONDO.build(B, S); info['hondo_frame'] = hi['frame']
    else:
        info['hondo_frame'] = HONDO.hall_frame(S)
    if want('halls'):
        HALLS.niomon(B, S, info)
        HALLS.saimon(B, S, info)
        HALLS.sanjunoto(B, S, info)
        HALLS.shoro(B, S, info)
        HALLS.zuigudo(B, S, info)
        HALLS.kyodo(B, S, info)
        HALLS.tamurado(B, S, info)
        HALLS.asakurado(B, S, info)
        HALLS.todorokimon(B, S, info)
        HALLS.kairo(B, S, info, info['hondo_frame'])
        HALLS.shakado(B, S, info)
        HALLS.amidado(B, S, info)
        HALLS.okunoin(B, S, info)
        HALLS.koyasuto(B, S, info)
        HALLS.jishu(B, S, info)
        HALLS.otowa(B, S, info)
    if want('ground'):
        GROUND.build(B, S, info)
    if want('trees'):
        if 'okunoin' not in info:
            cx, cy, yaw, _, _ = HALLS.bframe(S, 102164641, 176.6); info['okunoin'] = (cx, cy, yaw)
        GROUND.trees(B, S, info)
    # the preview terrain (run_site renders S.ground) follows the cuts, like the viewer: push it under the modelled ground
    for ring, zmax in info.get('cuts', []):
        lower_terrain(S, ring, zmax)
    # preview renders (run_site --shots): low-poly crowns for the trees, in their own collection (the viewer draws its own trees)
    if '--shots' in sys.argv and B.trees:
        try: K.preview_trees(B.trees, name='preview_trees_not_exported')
        except Exception as e: print('preview trees:', e)
    print(f'kiyomizu: {B.ntri()} tris, {len(B.trees)} trees, info {sorted(k for k in info if not k.endswith("frame"))} {time.time()-t0:.1f}s', flush=True)
    return info
