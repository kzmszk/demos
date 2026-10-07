"""東寺の門: 南大門 (重文, 1601: the former west gate of 三十三間堂, moved here in 1895; 三間一戸八脚門, 切妻造, 本瓦葺,
the largest gate, ~18 m wide and ~13 m high, on the moat), 慶賀門 (重文, 鎌倉; east, on 大宮通), 東大門 (重文, 不開門,
1198 / 1605), 北大門 (重文), 蓮花門 (国宝, 鎌倉; west, the gate of 小子房), plus the small gates of 灌頂院 and the
south-west gate over the moat.  Footprints from OSM / PLATEAU (refs/toji/dossier.md)."""
import math
import numpy as np
from jk import prim, arch
from jk.core import Frame
from sites.toji_kit import (WOOD, PLASTER, rect, slab, quad, walk_poly, walk_rect, block_rect, block_line, beam, post, gate8, hanging_lantern,
                            stone_lantern, troof)

def gz(S, x, y, r=6.0):
    return float(np.mean([S.ground(x + dx, y + dy) for dx in (-r, 0, r) for dy in (-r, 0, r)]))

def nandaimon(B, S, stats):
    """南大門: bays 5.6 + 6.8 + 5.6 = 18.0 m, depth 2 x 4.3 m; posts 5.9 m, 二手先 sets, a steep concave 切妻 roof
    (ridge ~13 m above the floor, PLATEAU top 15.5 m above the street) with large 懸魚; doors open"""
    n0 = B.ntri()
    cx, cy = -1013.3, -693.6
    zf = float(S.ground(cx, cy)) - 0.02                 # the laser DEM has the gate's stone floor (23.4)
    info = {}
    gate8(B, cx, cy, zf, 0.0, bays=(5.6, 6.8, 5.6), depth=8.6, h=5.9, r_main=0.42, r_back=0.34, bracket=('futatesaki', 1.25), o=2.4, pitch=0.66, teri=1.5,
          sori=0.25, verge=1.4, side='board', door='open', plinth=(1.6, 0.0), ridge_h=1.0, ridge_w=0.75, edge=0.4, rafter=0.27, tiers=2,
          lanterns=True, lantern_r=0.55, info=info, gable_mat=WOOD, end_walls=True)
    with Frame(B, cx, cy, 0.0, 0.0):
        # the stone base round the gate (its south edge is the moat revetment; see toji_grounds.moat)
        slab(B, -11.0, -6.4, 11.0, 6.4, zf - 1.6, zf, 'stone', faces='xXyY')
        prim.polygon(B, rect(11.0, 6.4), zf, 'stone_slab' if False else 'stone')
        walk_rect(B, -11.0, -6.4, 11.0, 6.4, zf)
        # the 虹梁 and 蟇股 of the gable ends and the front, the 冠木 carving (main members only)
        for v in (-4.3, 4.3):
            for u in (-3.4, 3.4):
                prim.box(B, u - 0.5, v - 0.1, 5.95, u + 0.5, v + 0.1, 6.5, WOOD, tag='detail')
        # stone posts with the temple name at the gate (石標), west of the bridge
        prim.box(B, -9.0, -6.9, zf - 0.6, -8.4, -6.3, zf + 3.2, 'stone')
        block_rect(B, -9.3, -7.2, -8.1, -6.0, zf)
    S.exclude.append([[cx - 12.5, cy - 9.5], [cx + 12.5, cy - 9.5], [cx + 12.5, cy + 9.5], [cx - 12.5, cy + 9.5]])
    stats['nandaimon_tris'] = B.ntri() - n0
    stats['nandaimon_ridge'] = round(info.get('z_ridge', 0), 2)
    return zf

def keigamon(B, S, stats):
    """慶賀門 (east, on 大宮通): 11.0 x 5.6 m, white plaster in the side bays, 出三斗; the lanterns 「東寺」; open"""
    n0 = B.ntri()
    cx, cy = -888.6, -435.6
    zf = gz(S, cx, cy, 4.0) + 0.12
    info = {}
    gate8(B, cx, cy, zf, math.radians(90.0), bays=(3.25, 4.5, 3.25), depth=5.4, h=4.55, r_main=0.3, r_back=0.24, bracket=('demitsudo', 0.95), o=1.9,
          pitch=0.5, teri=1.4, sori=0.2, verge=0.95, side='plaster', door='open', plinth=(0.8, 0.12), ridge_h=0.62, ridge_w=0.5, edge=0.3, lanterns=True,
          lantern_r=0.45, info=info)
    with Frame(B, cx, cy, 0.0, math.radians(90.0)):
        for u in (-6.9, 6.9):            # the two big stone lanterns on 大宮通 (OSM toro)
            stone_lantern(B, u, -5.9, zf - 0.1, 3.0)
            block_rect(B, u - 0.5, -6.4, u + 0.5, -5.4, zf)
    S.exclude.append(rect_world(cx, cy, 9.0, 6.0, math.radians(90.0)))
    stats['keigamon_tris'] = B.ntri() - n0
    stats['keigamon_ridge'] = round(info.get('z_ridge', 0), 2)

def todaimon(B, S, stats):
    """東大門 (不開門, east): 11.6 x 6.0 m, doors shut, plaster side bays"""
    n0 = B.ntri()
    cx, cy = -888.1, -567.0
    zf = gz(S, cx, cy, 4.0) + 0.12
    info = {}
    gate8(B, cx, cy, zf, math.radians(90.0), bays=(3.4, 4.8, 3.4), depth=6.0, h=5.0, r_main=0.33, r_back=0.26, bracket=('demitsudo', 1.05), o=2.1,
          pitch=0.52, teri=1.4, sori=0.22, verge=1.0, side='plaster', door='closed', plinth=(0.8, 0.12), ridge_h=0.68, ridge_w=0.52, edge=0.32, info=info)
    S.exclude.append(rect_world(cx, cy, 9.0, 6.5, math.radians(90.0)))
    stats['todaimon_tris'] = B.ntri() - n0
    stats['todaimon_ridge'] = round(info.get('z_ridge', 0), 2)

def kitadaimon(B, S, stats):
    """北大門 (north): 11.5 x 5.8 m, faces north (to 櫛笥小路), open, white side bays, lanterns"""
    n0 = B.ntri()
    cx, cy = -1014.6, -417.0
    zf = gz(S, cx, cy, 4.0) + 0.12
    info = {}
    gate8(B, cx, cy, zf, math.radians(180.0), bays=(3.35, 4.8, 3.35), depth=5.8, h=4.45, r_main=0.31, r_back=0.25, bracket=('demitsudo', 0.95), o=1.95,
          pitch=0.47, teri=1.4, sori=0.2, verge=0.95, side='plaster', door='open', plinth=(0.8, 0.12), ridge_h=0.6, ridge_w=0.5, edge=0.3, lanterns=True,
          lantern_r=0.45, info=info)
    S.exclude.append(rect_world(cx, cy, 9.0, 6.5, 0.0))
    stats['kitadaimon_tris'] = B.ntri() - n0
    stats['kitadaimon_ridge'] = round(info.get('z_ridge', 0), 2)

def rengemon(B, S, stats):
    """蓮花門 (国宝, west, on 壬生通): a low, plain 八脚門; board doors shut, white side bays, 平三斗, a shallow roof"""
    n0 = B.ntri()
    cx, cy = -1139.3, -568.0
    zf = gz(S, cx, cy, 4.0) + 0.12
    info = {}
    gate8(B, cx, cy, zf, math.radians(-90.0), bays=(3.3, 4.5, 3.3), depth=5.9, h=4.6, r_main=0.33, r_back=0.27, bracket=('hira', 1.0), o=2.2,
          pitch=0.34, teri=1.3, sori=0.15, verge=1.0, side='plaster', door='closed', plinth=(0.8, 0.12), ridge_h=0.55, ridge_w=0.48, edge=0.3, info=info)
    S.exclude.append(rect_world(cx, cy, 9.0, 6.5, math.radians(-90.0)))
    stats['rengemon_tris'] = B.ntri() - n0
    stats['rengemon_ridge'] = round(info.get('z_ridge', 0), 2)

def small_gate(B, S, cx, cy, yaw, w=3.2, h=3.2, door='open', cover='hongawara', zf=None, mat=WOOD):
    """棟門 / 四脚門 for the inner precincts (灌頂院 北門 / 東門, the south-west gate): two posts, a 切妻 roof"""
    zf = zf if zf is not None else gz(S, cx, cy, 2.0) + 0.05
    with Frame(B, cx, cy, zf, yaw):
        for u in (-w / 2, w / 2):
            post(B, u, 0.0, 0.0, h, 0.17, mat, base='stone', base_h=0.2)
            for v in (-1.1, 1.1):
                post(B, u, v, 0.0, h - 0.6, 0.12, mat, base='stone', base_h=0.15)
            beam(B, (u, -1.1), (u, 1.1), h - 0.55, 0.12, 0.2, mat)
            block_rect(B, u - 0.3, -1.3, u + 0.3, 1.3, 0.0)
        beam(B, (-w / 2 - 0.4, 0.0), (w / 2 + 0.4, 0.0), h, 0.2, 0.32, mat)
        beam(B, (-w / 2 - 0.2, 0.0), (w / 2 + 0.2, 0.0), h * 0.82, 0.16, 0.24, mat)
        if door == 'closed':
            quad(B, (-w / 2 + 0.15, 0.0, 0.05), (w / 2 - 0.15, 0.0, 0.05), (w / 2 - 0.15, 0.0, h * 0.8), (-w / 2 + 0.15, 0.0, h * 0.8), mat, both=True)
            block_line(B, [(-w / 2, 0.0), (w / 2, 0.0)], 0.0, 0.6)
        troof(B, w, 2.6, h + 0.45, 0.6, kind='kirizuma', cover=cover, pitch=0.48, teri=1.3, sori=0.0, verge=0.5, edge=0.22, rafter=0.3, rafter_mat=WOOD,
              rafter_end=mat, fascia_mat=mat, ends='oni', ridge_h=0.38, ridge_w=0.3, tiers=1, bargeboard_mat=mat)
        walk_rect(B, -w / 2 - 0.3, -1.6, w / 2 + 0.3, 1.6, 0.0)

def rect_world(cx, cy, hu, hv, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return [[cx + c * u - s * v, cy + s * u + c * v] for (u, v) in ((-hu, -hv), (hu, -hv), (hu, hv), (-hu, hv))]

def gates(B, S, stats):
    nandaimon(B, S, stats)
    keigamon(B, S, stats)
    todaimon(B, S, stats)
    kitadaimon(B, S, stats)
    rengemon(B, S, stats)
    n0 = B.ntri()
    # 灌頂院 北門 (faces north) and 東門 (faces east): small 棟門 in the inner walls
    small_gate(B, S, -1105.7, -628.6, math.radians(180.0), w=3.0, h=3.3, door='closed', mat='vermilion')
    small_gate(B, S, -1076.3, -676.5, math.radians(90.0), w=3.4, h=3.5, door='open', mat='vermilion')
    small_gate(B, S, -1069.8, -694.3, math.radians(0.0), w=2.8, h=3.0, door='open')          # the south-west gate over the moat
    S.exclude.append(rect_world(-1105.7, -628.6, 3.5, 2.5, 0.0))
    S.exclude.append(rect_world(-1076.3, -676.5, 3.5, 2.8, math.radians(90.0)))
    S.exclude.append(rect_world(-1069.8, -694.3, 3.0, 2.2, 0.0))
    stats['small_gates_tris'] = B.ntri() - n0
