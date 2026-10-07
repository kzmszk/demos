"""一力亭 (Ichiriki-tei) at the SE corner of 四条通 / 花見小路: the long windowless 弁柄 red wall on a black board
skirt with the bamboo / black plank 犬矢来, the tile pent roof, the weathered board lattice screen of the upper floor,
the entrance with its noren on the Hanamikoji side.  Footprint: OSM w288051613 (PLATEAU 9.0 m, 2 storeys)."""
import numpy as np
import shapely
from shapely.geometry import Polygon, box as sbox
import sites.machiya as M

RED = (178, 66, 44)

def piece(P, bx):
    g = P.intersection(sbox(*bx))
    if g.geom_type != 'Polygon': g = max(g.geoms, key=lambda q: q.area)
    return np.asarray(g.exterior.coords)[:-1]

def build(B, S, used):
    b = S.osm_building(288051613)
    P = Polygon(b['poly'][0][0]).buffer(0)
    z0 = float(S.ground(1490.0, 1987.5))
    xw = 1496.6                                    # the main house (主屋) along Hanamikoji / the Shijo wing (座敷棟)
    yb = 1977.2                                    # depth of the Shijo wing
    base = dict(wall=RED, front1='redwall', upper='itagoshi', party='wall_plaster', party_tint=RED, wood='dark', chochin=False,
                nameboard=False, degoshi=False, komayose=False, lamps=True)
    # 主屋 on Hanamikoji (west front) incl. the corner, with the Shijo side dressed as a front too
    ring = piece(P, (1480, 1960, xw, 1990))
    st = dict(base, inuyarai='plank', noren=(96, 22, 26), door=1, chochin=True, eave=0.7,
              facade_edges=[((1485.8, 1986.2), (xw, 1986.1))], facade_style=dict(inuyarai='slope', door=-1, chochin=False))
    M.build(B, ring, ((1485.8, 1965.2), (1486.0, 1986.2)), z0, 8.9, 2, st, seed=1689)
    # 座敷棟 along Shijo
    ring = piece(P, (xw, yb, 1515, 1990))
    st = dict(base, inuyarai='slope', door=-1, eave=0.75)
    M.build(B, ring, ((xw, 1986.0), (1511.9, 1985.9)), z0 + 0.05, 9.0, 2, st, seed=1870)
    # 奥座敷 and the kura behind: low blocks, roofs only
    ring = piece(P, (xw, 1955, 1515, yb))
    st = dict(base, kind='hiraya', facade=False, eave=0.25, party_tint=(222, 214, 196))
    M.build(B, ring, ((xw, yb), (1511.7, yb)), z0 + 0.1, 6.4, 1, st, seed=1912)
    used.add('ichiriki')
    for pb in S.plateau:
        Q = Polygon(pb['poly'][0][0]).buffer(0)
        if Q.intersects(P) and Q.intersection(P).area > 0.3 * min(Q.area, P.area):
            S.exclude.append([list(map(float, c)) for c in np.asarray(Q.exterior.coords)[:-1]])
            used.add(pb['id'])
