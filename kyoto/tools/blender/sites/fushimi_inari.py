"""伏見稲荷大社 Fushimi Inari Taisha: the lower precinct (一ノ鳥居 … 楼門, 外拝殿, 内拝殿, 本殿, 権殿, 神楽殿 …), the 千本鳥居
and the torii tunnels up 稲荷山 to 四ツ辻 and the summit loop.

Parts (--only): mountain (routes, corridors, steps, torii tunnels), halls (the lower precinct), props (foxes, lanterns,
fences, お塚, tea houses), trees.  Helpers: fushimi_inari_paths / _torii / _mountain / _halls / _props."""
import math
import numpy as np
from . import fushimi_inari_mountain as FM
from . import fushimi_inari_halls as FH
from . import fushimi_inari_place as FPL

SHOTS = []

def _eye(r, s, ahead=12.0, h=1.6, dz=0.0, side=0.0):
    x, y, z, tx, ty = r.at(s)
    x2, y2, z2, _, _ = r.at(min(r.L, s + ahead))
    return ((x - ty * side, y + tx * side, z + h), (x2, y2, z2 + h + dz))

def build(B, S, only=None):
    global SHOTS
    want = lambda k: only is None or k in only
    rng = np.random.default_rng(7)
    net, R = FM.make_routes(S)
    T = None; info = None
    if want('mountain'):
        T, info, cuts = FM.build_tunnels(B, S, R, rng)
        for g in cuts:
            for p in (g.geoms if hasattr(g, 'geoms') else [g]):
                S.cut.append([list(map(list, p.exterior.coords))] + [list(map(list, i.coords)) for i in p.interiors])
        print('torii:', {k: v for k, v in T.count.items()}, 'total', sum(T.count.values()), 'tris', T.ntri)
    H = None
    if want('halls'):
        n0 = B.ntri()
        H = FH.build(B, S, S.exclude)
        print('halls tris', B.ntri() - n0)
    if want('props'):
        n0 = B.ntri()
        stats, placed = FPL.place_all(B, S, R, info, H, rng, S.exclude)
        print('props', stats, 'tris', B.ntri() - n0)
    if want('trees'):
        n = FPL.forest(B, S, R, info, rng, [])
        print('trees', sum(n.values()), n)
    if want('halls') or want('props'):
        FPL.paint(S)
    shots = []
    # 楼門 from the approach (by the 二ノ鳥居), 本殿 from the south-west, an aerial over the lower precinct
    shots.append(('romon', (1214.0, -2072.6, 37.6), (1265.0, -2071.0, 45.0), 30))
    shots.append(('romon_close', (1241.0, -2073.5, 38.9), (1265.0, -2071.0, 46.2), 24))
    shots.append(('honden', (1338.0, -2093.0, 45.0), (1329.0, -2066.0, 47.0), 28))
    shots.append(('naihaiden', (1290.0, -2073.0, 41.9), (1314.0, -2068.0, 46.0), 30))
    shots.append(('aerial', (1180.0, -2160.0, 115.0), (1300.0, -2068.0, 40.0), 32))
    ru = R['senbon_up']
    shots.append(('senbon_tunnel', *_eye(ru, 30.0, 14.0), 24))
    rl = R['lower']
    sf = rl.L
    c, t = _eye(rl, sf - 9.0, 9.0, dz=-0.2)
    shots.append(('senbon_fork', c, t, 24))
    rk = R['kumataka_mittsu']
    shots.append(('mountain_steps', *_eye(rk, 40.0, 12.0, dz=0.5), 24))
    x, y, z, _, _ = ru.at(40.0)
    shots.append(('senbon_aerial', (x - 40, y - 45, z + 45), (x, y, z), 35))
    ry = R['mittsu_yottsu']
    shots.append(('mittsu_yottsu', *_eye(ry, 120.0, 14.0, dz=0.8), 24))
    shots.append(('yottsu_view', (2067.5, -1853.5, 164.0), (2010.0, -1843.0, 152.5), 26))
    shots.append(('okusha', (1512.5, -2134.0, 61.9), (1532.7, -2137.5, 62.6), 30))
    SHOTS = shots
    _carve_preview(S)

def _carve_preview(S, depth=1.2):
    """the preview renders draw the site's terrain without the cuts: lower it inside them (S.H is not exported)"""
    import shapely
    from shapely.geometry import Polygon
    if not S.cut: return
    g = shapely.unary_union([Polygon(c[0], c[1:]) for c in S.cut])
    x0, y0, x1, y1 = g.bounds
    i0 = max(0, int((x0 - S.x0) / S.res) - 2); i1 = min(S.H.shape[1], int((x1 - S.x0) / S.res) + 3)
    j0 = max(0, int((y0 - S.y0) / S.res) - 2); j1 = min(S.H.shape[0], int((y1 - S.y0) / S.res) + 3)
    X, Y = np.meshgrid(S.x0 + np.arange(i0, i1) * S.res, S.y0 + np.arange(j0, j1) * S.res)
    m = shapely.contains_xy(g.buffer(2.5), X, Y)
    S.H[j0:j1, i0:i1][m] -= depth
