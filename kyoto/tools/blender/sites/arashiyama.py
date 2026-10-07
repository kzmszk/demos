"""嵐山 (Arashiyama) riverside: 渡月橋 with 嵐山 behind it, the 大堰川 / 桂川 (葛野大堰, the rapids, the sill under the
bridge, the south channel), 中之島 with 渡月小橋 and 中ノ島橋, the north bank promenade with its inns and the boat landing,
長辻通 from the bridge to 天龍寺's 総門 (the gate and the precinct are the tenryuji site's), the Randen station front.

Run: blender -b --python blender/run_site.py -- arashiyama --shots [--no-save] [--only river,bridge,banks,street,boats]
References: kyoto-assets/refs/arashiyama (dossier.md, manifest.json)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point
from jk.site import Site

# the tenryuji site's polygons: 天龍寺 precinct, the bamboo grove, 嵐山公園 亀山地区, 大河内山荘 — nothing of ours inside
NEIGHBOUR = [409723494, -17656638, 319336216, 677236682]

_S = None
def _gz(x, y, dz):
    global _S
    if _S is None: _S = Site('arashiyama')
    return round(float(_S.ground(x, y)) + dz, 2)

SHOTS = [
    # the classic view: 渡月橋 from the north bank downstream, looking upstream with 嵐山 behind (refs: Togetsukyo east side view, hdsr 2024)
    ('bridge', (-7318.0, 3085.0, _gz(-7318.0, 3085.0, 1.6)), (-7420.0, 2990.0, 37.0), 30),
    # on the deck, west sidewalk, walking south toward 中之島 and 嵐山 (ref: Togetsukyo Bridge at dusk, reversed)
    ('deck', (-7394.8, 3070.5, 38.7), (-7405.9, 2960.5, 38.5), 30),
    # 中之島: the plaza west of the bridge foot, tea houses and 渡月小橋 (ref: Nakanoshima Park at dusk)
    ('nakanoshima', (-7340.0, 2884.0, _gz(-7340.0, 2884.0, 1.6)), (-7402.0, 2872.0, 37.3), 30),
    # 長辻通 looking north from the bridge's north end
    ('nagatsuji', (-7392.0, 3101.0, _gz(-7392.0, 3101.0, 1.6)), (-7428.0, 3240.0, 40.0), 32),
    # the boat landing on the north bank above 葛野大堰, seen from a boat on the pool
    ('landing', (-7652.0, 3006.0, 38.6), (-7692.0, 3031.0, 36.8), 32),
    # aerial from the south-east over 中之島: the bridge, the weir, the north bank and 長辻通
    ('aerial', (-7230.0, 2830.0, 150.0), (-7420.0, 3030.0, 38.0), 30),
]

def forbidden(S):
    lu = {f['id']: f for f in S.osm['landuse']}
    g = shapely.unary_union([Polygon(lu[i]['poly'][0][0]).buffer(0) for i in NEIGHBOUR if i in lu])
    shapely.prepare(g)
    return g

def build(B, S, only=None):
    parts = only or ['river', 'bridge', 'banks', 'street', 'boats']
    forbid = forbidden(S)
    import sites.arashiyama_river as R
    river = R.River(S, forbid)
    bridges = []
    if 'bridge' in parts:
        import sites.arashiyama_bridge as BR
        bridges = BR.build(B, S, river)
    import sites.arashiyama_boats as BT
    quay = BT.plan(S, river) if 'boats' in parts else None
    if 'river' in parts:
        river.build(B, bridges=[b.opening() for b in bridges] + ([quay] if quay is not None else []))
    if 'banks' in parts:
        import sites.arashiyama_banks as BK
        BK.build(B, S, river, bridges, forbid)
    if 'boats' in parts:
        BT.build(B, S, river, quay)
    if 'street' in parts:
        import sites.arashiyama_street as ST
        ST.build(B, S, river, forbid)
    check_forbidden(B, forbid)
    preview_ground(S, river)

def check_forbidden(B, forbid):
    """nothing of ours inside the neighbour's polygons (report triangles whose centroid falls inside)"""
    n = 0
    for p in B.parts:
        P = p['P'][p['I']].mean(1)
        n += int(shapely.contains_xy(forbid, P[:, 0], P[:, 1]).sum())
    print('arashiyama: triangles inside the neighbour polygons:', n)

def preview_ground(S, river):
    """run_site renders the previews over the plain DEM; under our cut the viewer has our river bed instead, so the
    preview terrain sinks there (export and site edits are already done when the previews are made)"""
    if not S.cut: return
    def pg(p): return Polygon(p[0], p[1:]) if isinstance(p[0][0], (list, tuple)) else Polygon(p)
    cut = shapely.unary_union([pg(r) for r in S.cut]).buffer(-2.1)
    shapely.prepare(cut)
    g0 = S.ground
    def g(x, y):
        z = g0(x, y)
        xa = np.atleast_1d(np.asarray(x, float)); ya = np.atleast_1d(np.asarray(y, float))
        m = shapely.contains_xy(cut, xa.ravel(), ya.ravel()).reshape(np.shape(z) if np.ndim(z) else (1,))
        zz = np.where(m, np.asarray(z) - 4.0, z)
        return float(zz) if np.ndim(z) == 0 else zz
    S.ground = g
