"""東寺: 講堂 (重文, 1491), 食堂 (1933 再建), 灌頂院 (重文, 1634), 小子房 (1934), 宝蔵 (重文, 平安後期, 校倉), 夜叉神堂,
手水舎.  Dimensions from OSM / PLATEAU footprints and heights, the laser DEM for the platforms (refs/toji/dossier.md)."""
import math
import numpy as np
from jk import prim, arch
from jk.core import Frame
from jk import roof as jroof
from sites.toji_kit import (WOOD, PLASTER, rect, slab, quad, walk_poly, walk_rect, block_rect, block_line, beam, post, furin, bracket_h,
                            nakazonae, TRoof, troof, hall, stone_platform, bronze_lantern, stone_lantern)
from sites.toji_gates import rect_world

def ground_mean(S, cx, cy, hu, hv):
    return float(np.mean([S.ground(cx + dx, cy + dy) for dx in (-hu, 0, hu) for dy in (-hv, hv)]))

# ------------------------------------------------------------------ 講堂
def kodo(B, S, stats):
    """講堂: 9 x 5 bays (36.5 x 16.8 m), 入母屋 本瓦, 二手先, vermilion (丹塗り) frame and white walls, three 桟唐戸 in
    the middle of the front; eave 6.9 m and ridge 17.7 m above the ground (PLATEAU); platform 0.7 m (DEM)"""
    n0 = B.ntri()
    cx, cy = -1013.6, -559.8
    zg = ground_mean(S, cx, cy, 22.0, 12.0)
    zp = float(S.ground(cx, cy)) - 0.02
    us = list(np.cumsum([-18.25, 3.6, 4.0, 4.0, 4.2, 4.9, 4.2, 4.0, 4.0, 3.6]))
    vs = list(np.cumsum([-8.4, 3.2, 3.47, 3.46, 3.47, 3.2]))
    stone_platform(B, cx, cy, 0.0, rect(20.9, 11.0), zg, zp, [(0.0, -11.0, 0, -2.2, 12.5), (0.0, 11.0, 0, 2.2, 4.5), (20.9, 0.0, 2.2, 0, 3.0), (-20.9, 0.0, -2.2, 0, 3.0)])
    def infill(B, side, i, n, p0, p1, out, z0, z1, frame):
        doors = {0: (3, 4, 5), 2: (4,), 1: (2,), 3: (2,)}[side]
        if i in doors:
            arch.infill(B, p0, p1, z0 + 0.3, z0 + (z1 - z0) * 0.74, 'karado', out=out, mat='vermilion')
            arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.62, z0 + (z1 - z0) * 0.74, 'renji', out=out, mat='vermilion')
            arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.78, z1, 'plaster', out=out, mat='vermilion', seed=i)
        else:
            arch.infill(B, p0, p1, z0 + 0.3, z0 + (z1 - z0) * 0.3, 'plaster', out=out, mat='vermilion', seed=i + 3)
            arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.34, z1, 'plaster', out=out, mat='vermilion', seed=i + 5)
    info = hall(B, cx, cy, 0.0, zp, us, vs, zg + 6.95, bracket=('futatesaki', 1.15), o=2.68, pillar_mat='vermilion', frame_mat='vermilion', r=0.3,
                roof_kw=dict(kind='irimoya', cover='hongawara', pitch=10.7 / 12.98, teri=1.55, sori=0.5, sori_len=0.35, gable_frac=0.52, verge=0.9, edge=0.38,
                             ridge_h=1.0, ridge_w=0.7, rafter=0.26),
                infill=infill, nageshi=((0.03, 0.26), (0.3, 0.2), (0.76, 0.24)), rafter_end='white_paint')
    with Frame(B, cx, cy, 0.0, 0.0):
        bronze_lantern(B, 0.0, -12.6, zg, 2.4)
        block_rect(B, -0.6, -13.2, 0.6, -12.0, zg)
    S.exclude.append(rect_world(cx, cy, 23.5, 13.5, 0.0))
    stats['kodo_tris'] = B.ntri() - n0
    stats['kodo'] = dict(ridge=round(info['z_ridge'] - zg, 2), plate=round(info['h'] - zg, 2))

# ------------------------------------------------------------------ 食堂
def jikido(B, S, stats):
    """食堂: 7 x 5 bays (31.7 x 22.3 m) with the front bay an open aisle (吹放し), 入母屋 本瓦, 出組; eave 6.9, ridge 18.2
    above the ground (PLATEAU); platform 0.8 m"""
    n0 = B.ntri()
    cx, cy = -1014.4, -470.2
    zg = ground_mean(S, cx, cy, 19.0, 14.0)
    zp = float(S.ground(cx, cy - 3)) - 0.02
    us = list(np.cumsum([-15.85, 4.1, 4.5, 4.6, 5.3, 4.6, 4.5, 4.1]))
    vs = list(np.cumsum([-11.15, 4.3, 4.5, 4.5, 4.5, 4.5]))
    stone_platform(B, cx, cy, 0.0, rect(18.0, 13.2), zg, zp, [(0.0, -13.2, 0, -2.2, 9.0), (18.0, -7.0, 2.2, 0, 3.0), (-18.0, -7.0, -2.2, 0, 3.0), (0.0, 13.2, 0, 2.2, 3.5)])
    def infill(B, side, i, n, p0, p1, out, z0, z1, frame):
        aisle = (side == 0) or (side == 1 and i == 0) or (side == 3 and i == n - 1)
        if aisle: return
        if side == 2 and i == n // 2:
            arch.infill(B, p0, p1, z0 + 0.3, z0 + (z1 - z0) * 0.75, 'karado', out=out, mat=frame)
            arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.78, z1, 'plaster', out=out, mat=frame, seed=i)
            return
        arch.infill(B, p0, p1, z0 + 0.3, z0 + (z1 - z0) * 0.32, 'plaster', out=out, mat=frame, seed=i)
        arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.34, z0 + (z1 - z0) * 0.74, 'renji', out=out, mat=frame)
        arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.78, z1, 'plaster', out=out, mat=frame, seed=i + 2)
    info = hall(B, cx, cy, 0.0, zp, us, vs, zg + 6.9, bracket=('degumi', 1.05), o=2.88, pillar_mat=WOOD, frame_mat=WOOD, r=0.3,
                roof_kw=dict(kind='irimoya', cover='hongawara', pitch=11.3 / 15.13, teri=1.55, sori=0.5, sori_len=0.35, gable_frac=0.5, verge=0.9, edge=0.36,
                             ridge_h=1.0, ridge_w=0.7, rafter=0.26),
                infill=infill, nageshi=((0.03, 0.24), (0.33, 0.2), (0.76, 0.22)), block=False, rafter_end='white_paint')
    h = info['h']
    with Frame(B, cx, cy, 0.0, 0.0):
        # the inner front wall behind the aisle: doors in the middle three bays, windows at the sides
        v1 = vs[1]
        for i in range(7):
            p0, p1 = (us[i], v1), (us[i + 1], v1)
            z0, z1 = zp, h - 0.3
            if i in (2, 3, 4):
                arch.infill(B, p0, p1, z0 + 0.3, z0 + (z1 - z0) * 0.72, 'karado', out=(0, -1), mat=WOOD)
            else:
                arch.infill(B, p0, p1, z0 + 0.3, z0 + (z1 - z0) * 0.32, 'board', out=(0, -1), mat=WOOD)
                arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.34, z0 + (z1 - z0) * 0.72, 'renji', out=(0, -1), mat=WOOD)
            arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.76, z1, 'plaster', out=(0, -1), mat=WOOD, seed=i)
        for u in us[1:-1]:
            post(B, u, v1, zp, h, 0.3, WOOD, base='stone', base_h=0.2)
        beam(B, (us[0], v1), (us[-1], v1), h, 0.2, 0.3, WOOD, ext=0.2)
        # the aisle ceiling (化粧屋根裏)
        slab(B, us[0], vs[0], us[-1], v1, h + 0.5, h + 0.58, WOOD, faces='z')
        block_rect(B, us[0] - 0.3, v1 - 0.3, us[-1] + 0.3, vs[-1] + 0.3, zp + 0.05)
        for u in us:
            block_rect(B, u - 0.4, vs[0] - 0.4, u + 0.4, vs[0] + 0.4, zp + 0.05)
        # an offertory box and hanging lanterns in the aisle
        slab(B, -1.4, v1 - 1.2, 1.4, v1 - 0.4, zp, zp + 0.8, WOOD)
        for u in (-6.9, 6.9):
            prim.lathe(B, (u, (vs[0] + v1) / 2, h - 1.6), [(0.0, 0.0), (0.18, 0.02), (0.22, 0.15), (0.22, 0.5), (0.32, 0.55), (0.12, 0.7), (0.0, 0.74)], 8, 'bronze', tag='detail')
            prim.cyl(B, (u, (vs[0] + v1) / 2, h - 0.86), (u, (vs[0] + v1) / 2, h + 0.5), 0.012, 0.012, 4, 'metal_dark', tag='detail')
            B.lamp(u, (vs[0] + v1) / 2, h - 1.3, 6.0)
    S.exclude.append(rect_world(cx, cy, 20.5, 16.0, 0.0))
    stats['jikido_tris'] = B.ntri() - n0
    stats['jikido'] = dict(ridge=round(info['z_ridge'] - zg, 2), plate=round(info['h'] - zg, 2))

# ------------------------------------------------------------------ 灌頂院
def kanjoin(B, S, stats):
    """灌頂院: 7 x 5 bays (23.1 x 21.0 m), 入母屋 本瓦, ridge N-S, low eaves (~4.6 m) under a tall roof (ridge 16 m,
    PLATEAU), 出組; faces east; white walls, 連子窓, 板扉"""
    n0 = B.ntri()
    cx, cy = -1107.2, -665.9
    zg = ground_mean(S, cx, cy, 14.0, 14.0)
    zp = zg + 0.6
    yaw = math.radians(90.0)
    us = list(np.cumsum([-11.55] + [3.3] * 7))
    vs = list(np.cumsum([-10.5] + [4.2] * 5))
    stone_platform(B, cx, cy, yaw, rect(13.2, 12.2), zg, zp, [(0.0, -12.2, 0, -1.6, 4.0), (13.2, 0.0, 1.6, 0, 3.0)])
    def infill(B, side, i, n, p0, p1, out, z0, z1, frame):
        if (side == 0 and i in (2, 3, 4)) or (side == 1 and i == 2):
            arch.infill(B, p0, p1, z0 + 0.25, z0 + (z1 - z0) * 0.8, 'board', out=out, mat=frame)
            arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.82, z1, 'plaster', out=out, mat=frame, seed=i)
        elif side in (0, 2):
            arch.infill(B, p0, p1, z0 + 0.25, z0 + (z1 - z0) * 0.35, 'plaster', out=out, mat=frame, seed=i)
            arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.38, z0 + (z1 - z0) * 0.78, 'renji', out=out, mat=frame)
            arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.82, z1, 'plaster', out=out, mat=frame, seed=i + 1)
        else:
            arch.infill(B, p0, p1, z0 + 0.25, z1, 'plaster', out=out, mat=frame, seed=i + 4)
    info = hall(B, cx, cy, yaw, zp, us, vs, zg + 4.7, bracket=('degumi', 1.0), o=2.1, pillar_mat=WOOD, frame_mat=WOOD, r=0.27,
                roof_kw=dict(kind='irimoya', cover='hongawara', pitch=11.3 / 13.7, teri=1.6, sori=0.45, sori_len=0.35, gable_frac=0.55, verge=0.8, edge=0.34,
                             ridge_h=0.95, ridge_w=0.65, rafter=0.27),
                infill=infill, nageshi=((0.03, 0.22), (0.78, 0.2)), rafter_end='white_paint')
    S.exclude.append(rect_world(cx, cy, 15.0, 14.5, 0.0))
    stats['kanjoin_tris'] = B.ntri() - n0
    stats['kanjoin'] = dict(ridge=round(info['z_ridge'] - zg, 2))

# ------------------------------------------------------------------ 小子房
def shoji_infill(B, p0, p1, z0, z1, out, frame=WOOD):
    """障子 / 舞良戸 bay: white paper panels in a thin wooden grid, a 腰板 below"""
    arch.infill(B, p0, p1, z0, z0 + 0.45, 'board', out=out, mat=frame)
    a = np.asarray(p0, float); b = np.asarray(p1, float); d = (b - a) / np.linalg.norm(b - a); n = np.asarray(out, float)
    L = np.linalg.norm(b - a) - 0.36
    q0 = a + d * 0.18 - n * 0.06; q1 = b - d * 0.18 - n * 0.06
    quad(B, (*q0, z0 + 0.45), (*q1, z0 + 0.45), (*q1, z1), (*q0, z1), 'white_paint', both=True)
    for t in np.linspace(0, 1, max(3, int(L / 0.45)) + 1):
        q = q0 + (q1 - q0) * t
        prim.obox(B, (*(q + n * 0.02), z0 + 0.45), (*(q + n * 0.02), z1), 0.03, 0.03, frame, tag='detail', ends=False)
    for zz in np.linspace(z0 + 0.45, z1, 6):
        prim.obox(B, (*(q0 + n * 0.02), zz), (*(q1 + n * 0.02), zz), 0.025, 0.025, frame, tag='detail', ends=False)

def koshibo(B, S, stats):
    """小子房 (1934, 書院): 9 x 6 bays (25.5 x 17.4 m), 入母屋 桟瓦, 舟肘木, a veranda with 障子 / white walls; ridge 11.8 m"""
    n0 = B.ntri()
    cx, cy = -1110.4, -585.9
    zg = ground_mean(S, cx, cy, 12.0, 15.0)
    zp = zg + 0.75
    yaw = math.radians(90.0)
    us = list(np.cumsum([-12.75] + [25.5 / 9] * 9))
    vs = list(np.cumsum([-8.7] + [17.4 / 6] * 6))
    def infill(B, side, i, n, p0, p1, out, z0, z1, frame):
        if side in (0, 1, 3):
            shoji_infill(B, p0, p1, z0 + 0.05, z0 + (z1 - z0) * 0.72, out, frame)
            arch.infill(B, p0, p1, z0 + (z1 - z0) * 0.76, z1, 'plaster', out=out, mat=frame, seed=i)
        else:
            arch.infill(B, p0, p1, z0 + 0.05, z1, 'plaster', out=out, mat=frame, seed=i + 2)
    with Frame(B, cx, cy, 0.0, yaw):
        # the low stone base and the veranda (縁) round three sides
        slab(B, -13.8, -9.8, 13.8, 9.8, zg - 0.3, zg + 0.25, 'stone', faces='xXyYZ')
        arch.veranda(B, us[-1] - us[0], vs[-1] - vs[0], zp, width=1.1, mat='wood_natural', post_mat=WOOD, sides=(0, 1, 3))
        walk_rect(B, -13.85, -9.85, 13.85, -8.7, zp)
        for (x0, x1) in ((-13.85, -12.75), (12.75, 13.85)):
            walk_rect(B, x0, -9.85, x1, 8.7, zp)
        arch.stairs(B, (0.0, -11.6), (0.0, -9.85), zg, zp, 2.4, 'stone', riser=0.16, walk=True)
    info = hall(B, cx, cy, yaw, zp, us, vs, zg + 4.45, bracket=('funa', 1.0), o=2.05, pillar_mat=WOOD, frame_mat=WOOD, r=0.13,
                roof_kw=dict(kind='irimoya', cover='sangawara', pitch=7.4 / 10.75, teri=1.4, sori=0.3, sori_len=0.35, gable_frac=0.5, verge=0.7, edge=0.26,
                             ridge_h=0.65, ridge_w=0.45, rafter=0.36, tiers=1),
                infill=infill, nageshi=((0.72, 0.16),), plaster_band=False, ceiling=False)
    S.exclude.append(rect_world(cx, cy, 15.0, 11.0, yaw))
    stats['koshibo_tris'] = B.ntri() - n0

# ------------------------------------------------------------------ 宝蔵
def hozo(B, S, stats):
    """宝蔵 (校倉造): 3 x 3 bays (8.6 x 7.8 m) raised on 16 round posts (floor 2.4 m), walls of horizontal triangular logs
    (校木), 寄棟 本瓦 (eave 7.2, ridge 9.4 m above the ground: PLATEAU); stands on the island of its moat"""
    n0 = B.ntri()
    cx, cy = -911.4, -477.95
    zg = ground_mean(S, cx, cy, 6.0, 6.0)
    L, D = 8.6, 7.8
    zf = zg + 2.4
    with Frame(B, cx, cy, 0.0, 0.0):
        for u in np.linspace(-L / 2 + 0.3, L / 2 - 0.3, 4):
            for v in np.linspace(-D / 2 + 0.3, D / 2 - 0.3, 4):
                post(B, u, v, zg, zf - 0.25, 0.26, WOOD, base='stone', base_h=0.3)
                block_rect(B, u - 0.4, v - 0.4, u + 0.4, v + 0.4, zg)
        slab(B, -L / 2 - 0.1, -D / 2 - 0.1, L / 2 + 0.1, D / 2 + 0.1, zf - 0.3, zf, WOOD)
        # 校木: stacked triangular logs, each course 0.3 m, corners crossing
        zt = zf + 3.9
        nc = int((zt - zf) / 0.3)
        for k in range(nc):
            z0 = zf + k * 0.3
            for (p0, p1, nrm) in (((-L / 2, -D / 2), (L / 2, -D / 2), (0, -1)), ((L / 2, -D / 2), (L / 2, D / 2), (1, 0)), ((L / 2, D / 2), (-L / 2, D / 2), (0, 1)),
                                  ((-L / 2, D / 2), (-L / 2, -D / 2), (-1, 0))):
                a = np.asarray(p0, float); b = np.asarray(p1, float); d = (b - a) / np.linalg.norm(b - a); n = np.asarray(nrm, float)
                ext = 0.25 if k % 2 == (0 if nrm[1] else 1) else 0.0
                a2 = a - d * ext; b2 = b + d * ext
                # a triangular section: the ridge of each log faces out
                P = np.array([(*(a2 - n * 0.15), z0), (*(b2 - n * 0.15), z0), (*(b2 + n * 0.1), z0 + 0.15), (*(a2 + n * 0.1), z0 + 0.15),
                              (*(b2 - n * 0.15), z0 + 0.3), (*(a2 - n * 0.15), z0 + 0.3)])
                I = [[0, 1, 2], [0, 2, 3], [3, 2, 4], [3, 4, 5]]
                fn = np.cross(P[1] - P[0], P[2] - P[0])
                if fn @ np.r_[n, 0] < 0: I = [t[::-1] for t in I]
                B.add(P, I, WOOD, tag='main' if k % 2 == 0 else 'detail')
        slab(B, -L / 2 + 0.1, -D / 2 + 0.1, L / 2 - 0.1, D / 2 - 0.1, zf, zt, WOOD, faces='xXyY')
        for (u, v) in ((-L / 2, -D / 2), (L / 2, -D / 2), (L / 2, D / 2), (-L / 2, D / 2)):
            arch.kumimono(B, u, v, zt, (u / abs(u) * 0.7071, v / abs(v) * 0.7071), (-v / abs(v) * 0.7071, u / abs(u) * 0.7071), 'funa', 1.0, WOOD)
        jroof.roof(B, L + 0.4, D + 0.4, zt + 0.55, 1.6, kind='yosemune', cover='hongawara', pitch=0.48, teri=1.4, sori=0.25, rafter=0.3, rafter_mat=WOOD,
                   rafter_end=WOOD, fascia_mat=WOOD, tiers=1, ends='oni', edge=0.3, ridge_h=0.55, ridge_w=0.45)
        # stairs (removable wooden ladder steps) on the west
        arch.stairs(B, (-L / 2 - 2.6, 0.0), (-L / 2 - 0.1, 0.0), zg, zf, 1.2, 'wood_dark', riser=0.2, walk=False)
    S.exclude.append(rect_world(cx, cy, 7.0, 6.5, 0.0))
    stats['hozo_tris'] = B.ntri() - n0

# ------------------------------------------------------------------ small halls
def small_hall(B, S, cx, cy, yaw, L, D, h, kind='kirizuma', cover='hongawara', front='karado', mat=WOOD, zp=None, pitch=0.55, o=1.2, plinth=0.45):
    zg = ground_mean(S, cx, cy, L / 2 + 1, D / 2 + 1)
    zp = zp if zp is not None else zg + plinth
    with Frame(B, cx, cy, 0.0, yaw):
        slab(B, -L / 2 - 0.7, -D / 2 - 0.7, L / 2 + 0.7, D / 2 + 0.7, zg - 0.3, zp, 'stone', faces='xXyYZ')
        walk_rect(B, -L / 2 - 0.7, -D / 2 - 0.7, L / 2 + 0.7, D / 2 + 0.7, zp)
        arch.stairs(B, (0, -D / 2 - 1.7), (0, -D / 2 - 0.7), zg, zp, 1.6, 'stone', riser=0.15, walk=True)
        for u in (-L / 2, L / 2):
            for v in (-D / 2, D / 2):
                post(B, u, v, zp, zp + h, 0.13, mat, base=None)
        arch.nageshi(B, L, D, zp + h, h=0.2, w=0.14, out=0.02, mat=mat)
        arch.infill(B, (-L / 2, -D / 2), (L / 2, -D / 2), zp + 0.1, zp + h - 0.25, front, out=(0, -1), mat=mat)
        for (p0, p1, n) in (((L / 2, -D / 2), (L / 2, D / 2), (1, 0)), ((L / 2, D / 2), (-L / 2, D / 2), (0, 1)), ((-L / 2, D / 2), (-L / 2, -D / 2), (-1, 0))):
            arch.infill(B, p0, p1, zp + 0.1, zp + h - 0.25, 'plaster', out=n, mat=mat)
        for u in (-L / 2, L / 2):
            for v in (-D / 2, D / 2):
                arch.kumimono(B, u, v, zp + h, (u / abs(u) * 0.7071, v / abs(v) * 0.7071), (-v / abs(v) * 0.7071, u / abs(u) * 0.7071), 'funa', 0.7, mat)
        troof(B, L, D, zp + h + 0.45, o, kind=kind, cover=cover, pitch=pitch, teri=1.4, sori=0.15 if kind != 'kirizuma' else 0.0, verge=0.6, edge=0.24, rafter=0.3,
              rafter_mat=mat, rafter_end=mat, fascia_mat=mat, ends='oni', ridge_h=0.4, ridge_w=0.32, tiers=1, bargeboard_mat=mat)
        block_rect(B, -L / 2 - 0.2, -D / 2 - 0.2, L / 2 + 0.2, D / 2 + 0.2, zp)

def yasha(B, S, stats):
    """夜叉神堂: two small halls (雄夜叉 east, 雌夜叉 west) between the 講堂 and the 食堂, facing south"""
    n0 = B.ntri()
    for (cx, cy) in ((-1017.65, -496.1), (-1009.9, -496.0)):
        small_hall(B, S, cx, cy, 0.0, 3.3, 3.2, 2.9, kind='irimoya', cover='hongawara', front='koshi', mat='vermilion', pitch=0.6, o=1.0)
        S.exclude.append(rect_world(cx, cy, 3.0, 3.0, 0.0))
    stats['yasha_tris'] = B.ntri() - n0

def chozuya(B, S, stats):
    """手水舎 (north of the 食堂): four posts, a 切妻 roof, a stone basin"""
    n0 = B.ntri()
    cx, cy = -1008.3, -438.4
    zg = ground_mean(S, cx, cy, 3.0, 3.0)
    with Frame(B, cx, cy, 0.0, 0.0):
        for u in (-3.2, 3.2):
            for v in (-1.8, 1.8):
                post(B, u, v, zg, zg + 2.9, 0.14, WOOD, base='stone', base_h=0.25)
                block_rect(B, u - 0.3, v - 0.3, u + 0.3, v + 0.3, zg)
        arch.nageshi(B, 6.4, 3.6, zg + 2.9, h=0.22, w=0.14, out=0.02, mat=WOOD)
        troof(B, 6.4, 3.6, zg + 3.35, 1.0, kind='kirizuma', cover='hongawara', pitch=0.5, teri=1.3, sori=0.0, verge=0.6, edge=0.24, rafter=0.3, rafter_mat=WOOD,
              rafter_end=WOOD, fascia_mat=WOOD, ends='oni', ridge_h=0.42, ridge_w=0.34, tiers=1, bargeboard_mat=WOOD)
        slab(B, -1.6, -0.6, 1.6, 0.6, zg - 0.1, zg + 0.75, 'stone')
        slab(B, -1.4, -0.45, 1.4, 0.45, zg + 0.72, zg + 0.76, 'water', faces='Z')
        block_rect(B, -1.8, -0.8, 1.8, 0.8, zg)
    S.exclude.append(rect_world(cx, cy, 4.5, 3.0, 0.0))
    stats['chozuya_tris'] = B.ntri() - n0

def halls(B, S, stats):
    kodo(B, S, stats)
    jikido(B, S, stats)
    kanjoin(B, S, stats)
    koshibo(B, S, stats)
    hozo(B, S, stats)
    yasha(B, S, stats)
    chozuya(B, S, stats)
