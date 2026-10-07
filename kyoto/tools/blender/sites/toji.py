"""東寺 (教王護国寺) — the hero site: 五重塔, 金堂, 講堂, 食堂, 南大門 and the moat on 九条通, 慶賀門, 東大門, 北大門, 蓮花門,
御影堂 (大師堂), 宝蔵, 灌頂院, 小子房, 瓢箪池 and the garden, the 築地塀 (大垣), courtyards, paths, lanterns and trees.
References: /home/kazu/work/kyoto-assets/refs/toji/ (dossier.md, manifest.json).

Modules: toji_kit (shared parts: roofs with cut gables, 八脚門, halls, platforms, 築地塀, lanterns), toji_pagoda, toji_kondo,
toji_halls (講堂 食堂 灌頂院 小子房 宝蔵 夜叉神堂 手水舎), toji_mieido, toji_gates, toji_grounds (walls, moat, ponds, paint,
lanterns, trees, garden huts).  build(only=...) parts: pagoda kondo halls mieido gates walls moat ponds paint lanterns trees huts"""
import json, sys
import numpy as np
from sites import toji_pagoda as PG
from sites import toji_kondo as KD
from sites import toji_halls as HL
from sites import toji_mieido as MD
from sites import toji_gates as GT
from sites import toji_grounds as GR

SHOTS = [
    ('pagoda_pond', (-936.0, -576.5, 24.0), (-921.0, -657.0, 34.0), 22),
    ('pagoda_kujo', (-990.0, -709.4, 23.85), (-925.0, -662.0, 30.0), 18),
    ('kondo_front', (-1013.4, -690.5, 25.0), (-1013.5, -603.0, 33.0), 35),
    ('kodo', (-984.0, -588.0, 24.3), (-1013.6, -559.8, 31.0), 26),
    ('nandaimon', (-1032.0, -712.3, 23.8), (-1012.5, -693.5, 29.0), 24),
    ('daishido', (-1078.5, -436.5, 24.4), (-1094.0, -453.0, 27.5), 22),
    ('aerial', (-805.0, -790.0, 175.0), (-1012.0, -560.0, 22.0), 26),
    ('pagoda_far', (-1135.0, -722.0, 30.0), (-920.0, -657.0, 40.0), 70),
]
TEST = [
    ('t_pag16', (-946.0, -700.0, 23.5), (-920.0, -657.0, 30.0), 60),
    ('t_pag13', (-928.0, -688.0, 24.2), (-920.0, -657.0, 27.0), 20),
]
import os
if os.environ.get('TOJI_TEST'): SHOTS = TEST

def build(B, S, only=None):
    stats = {}
    want = lambda k: only is None or k in only
    if want('pagoda'): PG.pagoda(B, S, stats)
    if want('kondo'): KD.kondo(B, S, stats)
    if want('halls'): HL.halls(B, S, stats)
    if want('mieido'): MD.mieido(B, S, stats)
    if want('gates'): GT.gates(B, S, stats)
    if want('walls'): GR.walls(B, S, stats)
    if want('moat'): GR.moat(B, S, stats, float(S.ground(-1013.3, -693.6)) - 0.02)
    if want('ponds'): GR.ponds(B, S, stats)
    if want('paint'): GR.paint(B, S, stats)
    if want('lanterns'): GR.lanterns(B, S, stats)
    if want('huts'): GR.huts(B, S, stats)
    if want('trees'): GR.trees(B, S, stats)
    stats['total'] = dict(tris=B.ntri(), main=B.ntri('main'), detail=B.ntri('detail'), walk=B.ntri('walk'), block=B.ntri('block'), lamps=len(B.lamps),
                          trees=len(B.trees), exclude=len(S.exclude), cut=len(S.cut), paint=len(S.paint))
    print('TOJI', json.dumps(stats, ensure_ascii=False))
    if '--shots' in sys.argv: preview_cut(S)

def preview_cut(S):
    """preview renders only: run_site.py draws the context terrain from S.ground after build() without applying S.cut,
    so the moat and the ponds would sit under it.  Sink the terrain inside the cut polygons for the previews (the npz
    and the .blend are written before this is used)."""
    import shapely
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    gs = []
    for c in S.cut:
        gs.append(Polygon(c[0], c[1:]) if isinstance(c[0][0], (list, tuple)) else Polygon(c))
    if not gs: return
    U = unary_union(gs); shapely.prepare(U)
    g0 = S.ground
    def ground(x, y):
        z = g0(x, y)
        if np.ndim(z) == 0: return z - (4.0 if U.contains(shapely.Point(float(x), float(y))) else 0.0)
        return z - 4.0 * shapely.contains_xy(U, np.asarray(x, float), np.asarray(y, float))
    S.ground = ground
