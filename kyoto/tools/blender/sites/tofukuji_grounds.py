"""東福寺 grounds: gravel courts and moss (S.paint on the generic terrain), the stone rain gutter round the 方丈, steps up to its
west veranda (the way in from the 西唐門), stone lanterns and hanging lanterns lit at dusk, columnar junipers in front of
the 三門, maples and pines round the halls."""
import math
import numpy as np
from shapely.geometry import Polygon, box
from jk import prim, arch
from sites import tofukuji_lib as L
from sites import tofukuji_klib as K
from sites import tofukuji_ekit as EK
from sites import tofukuji_halls as HL
from sites import tofukuji_bridges as BR

def paint(S):
    P = lambda ring, surf: S.paint.append({'poly': [list(map(float, p)) for p in ring], 'surf': surf})
    P([(1338, -1142), (1394, -1142), (1394, -1066), (1338, -1066)], 'gravel')           # 三門 - 本堂 court
    P([(1350, -1034), (1446, -1034), (1446, -995.5), (1350, -995.5)], 'gravel')         # between 本堂 and 方丈 / 庫裏
    P([(1290, -1050), (1338, -1050), (1338, -1032), (1290, -1032)], 'gravel')           # from the 日下門
    for lid in (775463664, 775463665):                                                    # the hedged lawns in front of the 本堂
        try: P(L.osm_poly(S, 'landuse', lid), 'moss')
        except KeyError: pass
    P([(1362.8, -1142.5), (1366.6, -1142.5), (1366.6, -1126.5), (1362.8, -1126.5)], 'stone_slab')   # the axis path to the 三門

def hojo_extras(B, S):
    lc = L.Loc(*HL.HOJO_C, L.ROT)
    a, c, w = HL.HOJO_L / 2, HL.HOJO_D / 2, HL.HOJO_VER
    zv = HL.HOJO_FLOOR - 0.05
    with lc.frame(B):
        # 雨落ち: a band of dark river stones / slabs under the eaves round the veranda
        outer = box(-a - w - 1.0, -c - w - 1.0, a + w + 1.0, c + w + 1.0); inner = box(-a - w + 0.1, -c - w + 0.1, a + w - 0.1, c + w - 0.1)
        ring = outer.difference(inner)
        from sites import tofukuji_garden as GD
        GD.flat_poly(B, ring, GD.ZGARD - 0.07, 'stone', c1=(0, 3, 0, 0))
        # steps up to the west veranda (from the 西唐門)
        zg = lc.g(S, -a - w - 1.8, -5.0)
        K.steps(B, (-a - w - 1.9, -5.0), (-a - w, -5.0), zg, zv, 2.2, mat='stone', riser=0.17, cheek=0.3)
        # stepping stones from the 西唐門 to those steps
        rng = np.random.default_rng(3)
        for u in np.arange(-26.0, -a - w - 2.0, 0.9):
            prim.cyl(B, (u, -5.0 + rng.uniform(-0.1, 0.1), lc.g(S, u, -5.0) - 0.1), (u, -5.0, lc.g(S, u, -5.0) + 0.06), 0.36, 0.34, 10, 'stone', tag='detail')
        EK.ribbon(B, np.array([(u, -5.0, lc.g(S, u, -5.0) + 0.06) for u in np.linspace(-27.5, -a - w - 1.9, 8)]), 1.4, 'walk')

def lanterns(B, S):
    """stone lanterns along the approaches (lit), hanging paper lanterns in the corridors"""
    for (x, y) in ((1293.0, -1033.4), (1293.0, -1028.0), (1340.2, -1036.0), (1349.5, -1036.5), (1361.5, -1104.5), (1370.5, -1104.8),
                   (1352.0, -1000.0), (1362.0, -982.5), (1362.0, -972.5), (1430.5, -1012.0), (1404.0, -1012.0), (1290.2, -936.5), (1290.6, -910.5),
                   (1455.5, -991.0), (1465.0, -991.0)):
        EK.lantern(B, x, y, float(S.ground(x, y)), h=2.0)
    # hanging lanterns (提灯) along the corridors: south corridor and the north one
    way = L.osm_line(S, 775463879)
    loc = BR.tsu_loc()
    pts = []
    for yy in np.arange(-1022.0, -962.0, 8.0):
        idx = np.argsort(way[:, 1])
        x = float(np.interp(yy, way[idx, 1], way[idx, 0]))
        pts.append((x, yy))
    for yy in np.arange(-924.0, -898.0, 8.0):
        pts.append((float(np.interp(yy, [-931.7, -899.9], [1359.0, 1360.5])), yy))
    for (x, y) in pts:
        zf = float(S.ground(x, y)) + 0.2
        zf = max(zf, BR.ZB)
        arch.chochin(B, x, y, zf + 2.15, r=0.15, h=0.42, tag='detail')

def trees(B, S):
    rng = np.random.default_rng(23)
    T = lambda sp, x, y, sc: B.tree(sp, x, y, float(S.ground(x, y)), sc, rng.uniform(0, 6.28))
    # columnar junipers (カイヅカイブキ) flanking the 三門 court and the 本堂 approach
    for (x, y) in ((1344.0, -1107.5), (1388.5, -1108.5), (1346.0, -1137.0), (1386.5, -1138.5), (1352.0, -1068.0), (1387.5, -1069.0)):
        T('hinoki', x, y, rng.uniform(0.42, 0.55))
    # pines by the 庫裏 forecourt and the 禅堂
    for (x, y) in ((1402.0, -1016.0), (1336.0, -1052.0), (1336.0, -1088.0), (1318.0, -1100.0)):
        T('matsu', x, y, rng.uniform(0.9, 1.2))
    # maples round the 方丈 (east side, toward the 偃月橋) and along the 開山堂 approach west of the corridor
    for (x, y) in ((1432.0, -966.0), (1440.0, -972.0), (1426.0, -962.0), (1447.0, -1000.0), (1452.0, -1010.0),
                   (1340.0, -905.0), (1348.0, -910.0), (1332.0, -890.0), (1372.0, -905.0), (1376.0, -912.0)):
        T('momiji', x, y, rng.uniform(1.0, 1.4))
    # cedars behind the 開山堂 and the 鐘楼
    for (x, y) in ((1412.0, -830.0), (1420.0, -838.0), (1372.0, -825.0), (1465.0, -1100.0), (1470.0, -1115.0)):
        T('sugi', x, y, rng.uniform(0.75, 0.95))

def build(B, S):
    paint(S)
    hojo_extras(B, S)
    lanterns(B, S)
    trees(B, S)
