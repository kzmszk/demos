"""南座 (Minami-za, 1929, Momoyama-revival theatre at the SE corner of 四条大橋): the five-bay front tower with the gilded
entrance doors, the wide tile pent roof, the red-railed balcony on brackets, the 唐破風 over the centre, the bracketed
main eave and the great 入母屋 gable (ridge N-S over the auditorium, PLATEAU 28.4 m) with the 櫓 banner; the
まねき看板 boards in two rows across the upper front (December kaomise), the big red lanterns, the lower west wing
with its corner 唐破風 entrance and balconies.  Local frame: u along Shijo (west +), v into the building (south), z up."""
import math
import numpy as np
from jk import prim, arch, roof, Frame
import sites.machiya as M

CREAM = (214, 206, 182)
FRAME_RED = M.paint_tint((120, 28, 26))
GREEN_GREY = (150, 156, 136)

def window(B, u0, u1, z0, z1, v=0.0):
    """a theatre window: dark red frame, glass (lit warm), a gilded lattice transom"""
    M.front_rect(B, u0, u1, z0, z1, v + 0.12, 'glass')
    zt = z1 - (z1 - z0) * 0.22
    M.front_rect(B, u0 + 0.06, u1 - 0.06, zt, z1 - 0.06, v + 0.1, 'gold', tag='detail')
    M.lattice(B, u0 + 0.06, u1 - 0.06, zt, z1 - 0.06, v + 0.07, pitch=0.09, sw=0.025, sd=0.02, mat='vermilion', back=None, rails=False, mid=False, c0=FRAME_RED)
    M.bars(B, [(u0, v + 0.05, z0), (u0, v + 0.05, z1), (u0, v + 0.05, zt)], [(u1, v + 0.05, z0), (u1, v + 0.05, z1), (u1, v + 0.05, zt)], (0, 0, 1), (0.1, 0.1, 0.06), 0.1, 'vermilion', tag='main', c0=FRAME_RED)
    M.bars(B, [(u0, v + 0.05, z0), (u1, v + 0.05, z0), ((u0 + u1) / 2, v + 0.06, z0)], [(u0, v + 0.05, z1), (u1, v + 0.05, z1), ((u0 + u1) / 2, v + 0.06, zt)], (1, 0, 0), (0.1, 0.1, 0.05), 0.1, 'vermilion', tag='main', c0=FRAME_RED)
    # white surround
    M.hbox(B, u0 - 0.18, u1 + 0.18, v - 0.04, v + 0.02, z0 - 0.18, z0 - 0.02, 'white_paint', tag='detail', faces='yZ')
    M.hbox(B, u0 - 0.18, u1 + 0.18, v - 0.04, v + 0.02, z1 + 0.02, z1 + 0.18, 'white_paint', tag='detail', faces='yZz')

def wall_with_windows(B, u0, u1, z0, z1, wins, v=0.0, tint=CREAM):
    M.wall_holes(B, u0, u1, z0, z1, v, wins, 'wall_plaster', c0=(*tint, 0))
    for (a, b, c, d) in wins:
        window(B, a, b, c, d, v)
        M.side_rect(B, v, v + 0.12, c, d, a, 'wall_plaster', facing=1, c0=(*tint, 0)); M.side_rect(B, v, v + 0.12, c, d, b, 'wall_plaster', facing=-1, c0=(*tint, 0))

def karahafu(B, uc, w, z0, h, d, v=0.0, mat='hongawara', board='black_lacquer', n=24):
    """唐破風: a cusped (cosine-bell) gable front, extruded back d into the facade; gilt bargeboard band and 懸魚"""
    xs = np.linspace(-1, 1, n + 1)
    s = (np.cos(np.pi * xs) + 1) / 2
    us = uc + xs * w / 2; zs = z0 + h * s
    P = []; UV = []
    for j, vv in enumerate((v - 0.45, v + d)):
        for i in range(n + 1):
            P.append((us[i], vv, zs[i])); UV.append((us[i] * 1.0, vv))
    I = []
    for i in range(n):
        f0, f1, b0, b1 = i, i + 1, n + 1 + i, n + 2 + i
        I += [[f0, f1, b1], [f0, b1, b0]]
    P = np.array(P); I = np.array(I)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    if fn[:, 2].sum() < 0: I = I[:, ::-1]
    B.add(P, I, mat, UV=np.array(UV), tag='main')
    # underside
    P2 = P.copy(); P2[:, 2] -= 0.35
    B.add(P2, I[:, ::-1], 'eave_wood', UV=np.array(UV), tag='main', c1=(0, 2, 0, 0))
    # the bargeboard (破風板): a band following the curve at the front, gilt edge
    pth = np.c_[us, np.full(n + 1, v - 0.47), zs - 0.05]
    prim.sweep(B, pth, [(-0.06, -0.42), (0.06, -0.42), (0.06, 0.02), (-0.06, 0.02)], board, up=(0, -1, 0), tag='main')
    prim.sweep(B, pth + [0, -0.07, -0.42], [(-0.03, -0.05), (0.03, -0.05), (0.03, 0.05), (-0.03, 0.05)], 'gold', up=(0, -1, 0), tag='detail')
    # the tympanum under the curve: plaster with a gilt 懸魚
    T = [(uc, v - 0.2, z0 - 0.4)] + [(us[i], v - 0.2, zs[i] - 0.45) for i in range(n + 1)]
    It = [[0, i + 2, i + 1] for i in range(n)]
    Pt = np.array(T); fn = np.cross(Pt[It[0][1]] - Pt[0], Pt[It[0][2]] - Pt[0])
    if fn[1] > 0: It = [t[::-1] for t in It]
    B.add(Pt, It, 'wall_plaster', tag='main', c0=(*CREAM, 0))
    M.hbox(B, uc - 0.5, uc + 0.5, v - 0.3, v - 0.22, z0 + h - 1.3, z0 + h - 0.6, 'gold', tag='detail')
    M.hbox(B, uc - 0.9, uc + 0.9, v - 0.28, v - 0.22, z0 + h * 0.35, z0 + h * 0.5, 'gold', tag='detail')
    # 鬼板 at the crown
    M.hbox(B, uc - 0.35, uc + 0.35, v - 0.5, v - 0.2, z0 + h, z0 + h + 0.5, 'ridge', tag='main')

def pent(B, u0, u1, z_edge, depth, v=0.0, pitch=0.45, mat='hongawara', brackets=None):
    zw = M.hisashi(B, u0, u1, z_edge, depth=depth, pitch=pitch, v=v, brackets=() if brackets is None else brackets, roof=mat)
    return zw

def maneki(B, u0, u1, z0, z1, v, seed=0):
    """まねき看板: tall cypress boards with a little gable top and black brush names, on a bamboo frame"""
    n = int((u1 - u0) / 0.66)
    us = np.linspace(u0, u1, n)
    rng = np.random.default_rng(seed)
    hgt = z1 - z0
    for i, u in enumerate(us):
        w = 0.56; zz0 = z0 + rng.uniform(-0.04, 0.04)
        M.hbox(B, u - w / 2, u + w / 2, v, v + 0.05, zz0, zz0 + hgt - 0.25, 'wood_natural', tag='detail')
        M.quad(B, (u - w / 2 + 0.03, v - 0.002, zz0 + 0.05), (u + w / 2 - 0.03, v - 0.002, zz0 + 0.05), (u + w / 2 - 0.03, v - 0.002, zz0 + hgt - 0.5), (u - w / 2 + 0.03, v - 0.002, zz0 + hgt - 0.5),
               'white_paint', tag='detail', uv=np.array([(0, 0), (1.0, 0), (1.0, 2.2), (0, 2.2)]), c1=(0, 7, (seed * 31 + i) % 251, 0))
        # gable cap
        P = np.array([(u - w / 2 - 0.03, v - 0.03, zz0 + hgt - 0.27), (u, v - 0.03, zz0 + hgt), (u + w / 2 + 0.03, v - 0.03, zz0 + hgt - 0.27),
                      (u - w / 2 - 0.03, v + 0.08, zz0 + hgt - 0.27), (u, v + 0.08, zz0 + hgt), (u + w / 2 + 0.03, v + 0.08, zz0 + hgt - 0.27)])
        B.add(P, [[0, 4, 1], [0, 3, 4], [1, 5, 2], [1, 4, 5], [0, 1, 2]], 'wood_natural', tag='detail')
        # a red-and-white crest disc near the top
        prim.cyl(B, (u, v - 0.004, zz0 + hgt - 0.62), (u, v - 0.02, zz0 + hgt - 0.62), 0.11, 0.11, 10, 'vermilion', tag='detail')
    # bamboo frame behind (horizontal poles) and evergreen garland (as hedge strips) along the rows
    for zz in (z0 + 0.3, z0 + hgt * 0.6):
        prim.cyl(B, (u0 - 0.4, v + 0.12, zz), (u1 + 0.4, v + 0.12, zz), 0.035, 0.035, 6, 'bamboo', tag='detail')
    M.hbox(B, u0 - 0.3, u1 + 0.3, v - 0.1, v + 0.15, z0 - 0.12, z0 + 0.06, 'hedge', tag='detail')

def big_lantern(B, u, v, z_top, r=0.62, h=1.6):
    """the great red 南座 lanterns at the entrance, under a small roof on a post"""
    M.chochin(B, u, v, z_top - 0.45, r=r, h=h, mat='lantern_paper', watts=40.0, seg=14)
    M.hbox(B, u - r - 0.3, u + r + 0.3, v - r - 0.3, v + r + 0.3, z_top - 0.45, z_top - 0.3, 'black_lacquer', tag='main')
    P = np.array([(u - r - 0.45, v - r - 0.45, z_top - 0.3), (u + r + 0.45, v - r - 0.45, z_top - 0.3), (u + r + 0.45, v + r + 0.45, z_top - 0.3), (u - r - 0.45, v + r + 0.45, z_top - 0.3), (u, v, z_top + 0.35)])
    B.add(P, [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]], 'hongawara', tag='main')

def build(B, S, used):
    a = np.array([1234.8, 1986.4]); b = np.array([1255.3, 1984.1])
    d = (a - b) / np.linalg.norm(a - b)                 # local +u: west along Shijo
    O = (a + b) / 2
    yaw = math.atan2(d[1], d[0])
    z0 = float(S.ground(O[0], O[1] + 1.0))
    HW = 10.25                                           # half width of the front tower
    with Frame(B, O[0], O[1], z0, yaw):
        # ---------------- auditorium block and the great roof (ridge along v)
        D0, D1 = 6.0, 44.0
        for (u0, u1, v0, v1) in ((-13.0, 13.0, D0, D1),):
            M.side_rect(B, v0, v1, -0.3, 19.6, u0, 'wall_plaster', facing=-1, c0=(*CREAM, 0))
            M.side_rect(B, v0, v1, -0.3, 19.6, u1, 'wall_plaster', facing=1, c0=(*CREAM, 0))
            M.front_rect(B, u0, u1, -0.3, 19.6, v1, 'wall_plaster', facing=1, c0=(*CREAM, 0))
        # windows along the river-facing (west, +u) side and the pent roof band there
        for k in range(7):
            vv = 10 + k * 4.6
            for (zz0, zz1) in ((7.6, 9.6), (12.4, 14.4)):
                M.quad(B, (13.02, vv + 1.4, zz0), (13.02, vv, zz0), (13.02, vv, zz1), (13.02, vv + 1.4, zz1), 'glass', tag='main')
                M.hbox(B, 13.0, 13.1, vv - 0.1, vv + 1.5, zz0 - 0.1, zz0, 'vermilion', tag='detail', c0=FRAME_RED)
        with Frame(B, 13.0, 0, 0, -math.pi / 2):
            M.hisashi(B, -D1, -8.0, 10.6, depth=1.4, pitch=0.45, v=0.0, roof='hongawara')
            M.hisashi(B, -D1, -8.0, 16.0, depth=1.0, pitch=0.45, v=0.0, roof='hongawara')
        with Frame(B, 0.0, (D1 - 0.5) / 2, 0, math.pi / 2):
            # local x' = v (south), y' = -u
            h = roof.roof(B, D1 + 0.5 - 1.0, 23.0, 20.0, 2.3, kind='irimoya', cover='hongawara', pitch=0.58, teri=1.5, sori=0.35, gable_frac=0.42,
                          verge=1.2, rafter=0.32, rafter_mat='wood_dark', rafter_end='white_paint', ends='oni', ridge_h=1.1, ridge_w=0.8)
        # the 櫓 banner (crest curtain) and the bonten under the front gable apex
        zr = h['z_ridge']
        M.hbox(B, -1.4, 1.4, -0.9, -0.75, zr - 6.2, zr - 3.6, 'white_paint', tag='main')
        M.quad(B, (-1.2, -0.92, zr - 6.0), (1.2, -0.92, zr - 6.0), (1.2, -0.92, zr - 3.8), (-1.2, -0.92, zr - 3.8), 'cloth', tag='main', c0=(196, 70, 66, 0))
        M.hbox(B, -0.5, 0.5, -0.95, -0.92, zr - 5.3, zr - 4.4, 'white_paint', tag='detail')
        for s in (-1, 1):
            M.quad(B, (s * 1.75 - 0.25, -0.93, zr - 6.0), (s * 1.75 + 0.25, -0.93, zr - 6.0), (s * 1.75 + 0.25, -0.93, zr - 3.8), (s * 1.75 - 0.25, -0.93, zr - 3.8), 'white_paint', tag='main', c1=(0, 7, 3 + s, 0))
            prim.cyl(B, (s * 0.9, -1.0, zr - 3.6), (s * 0.9, -1.0, zr - 1.9), 0.03, 0.03, 6, 'gold', tag='detail')
            prim.lathe(B, (s * 0.9, -1.0, zr - 2.0), [(0.0, 0.0), (0.25, 0.1), (0.3, 0.3), (0.2, 0.5), (0.0, 0.6)], 8, 'white_paint', tag='detail')
        # ---------------- front tower facade (v = 0), 5 bays
        bays = np.linspace(-HW + 0.6, HW - 0.6, 6)
        # 1F: granite piers and the gilded lattice doors
        for i in range(5):
            u0, u1 = bays[i] + 0.45, bays[i + 1] - 0.45
            M.front_rect(B, u0, u1, 0.0, 3.6, 0.6, 'glass', tag='main')
            M.front_rect(B, u0, u1, 2.5, 3.5, 0.55, 'gold', tag='detail')
            M.lattice(B, u0, u1, 2.5, 3.5, 0.5, pitch=0.11, sw=0.03, sd=0.03, mat='vermilion', back=None, rails=False, mid=False, c0=FRAME_RED)
            nn = 4
            uu = np.linspace(u0, u1, nn + 1)
            M.bars(B, np.c_[uu, np.full(nn + 1, 0.5), np.zeros(nn + 1)], np.c_[uu, np.full(nn + 1, 0.5), np.full(nn + 1, 3.6)], (1, 0, 0), 0.12, 0.08, 'vermilion', tag='main', c0=FRAME_RED)
            M.bars(B, [(u0, 0.5, 2.5), (u0, 0.5, 3.55)], [(u1, 0.5, 2.5), (u1, 0.5, 3.55)], (0, 0, 1), 0.1, 0.08, 'vermilion', tag='main', c0=FRAME_RED)
            for k in range(nn):
                M.front_rect(B, uu[k] + 0.12, uu[k + 1] - 0.12, 0.8, 2.3, 0.52, 'gold', tag='detail')
                M.lattice(B, uu[k] + 0.1, uu[k + 1] - 0.1, 0.8, 2.3, 0.47, pitch=0.12, sw=0.025, sd=0.02, mat='vermilion', back=None, rails=False, mid=False, c0=FRAME_RED)
            M.side_rect(B, 0.0, 0.6, 0.0, 3.6, u0, 'stone', facing=1); M.side_rect(B, 0.0, 0.6, 0.0, 3.6, u1, 'stone', facing=-1)
            M.front_rect(B, u0, u1, 3.6, 5.2, 0.0, 'wall_plaster', c0=(*CREAM, 0))
        for u in bays:
            M.hbox(B, u - 0.45, u + 0.45, -0.1, 0.6, 0.0, 3.6, 'stone', tag='main')
        M.hbox(B, -HW, HW, -0.2, 0.05, 3.6, 3.95, 'stone', tag='main')
        M.hbox(B, -HW, -HW + 0.6, -0.1, 0.6, 0.0, 5.2, 'stone', tag='main'); M.hbox(B, HW - 0.6, HW, -0.1, 0.6, 0.0, 5.2, 'stone', tag='main')
        # the purple 南座 curtain band and the wide pent roof over the 1F
        M.front_rect(B, -HW + 0.6, HW - 0.6, 3.95, 5.6, -0.25, 'cloth', c0=(52, 34, 110, 0))
        M.hbox(B, -0.9, 0.9, -0.27, -0.25, 4.3, 5.3, 'white_paint', tag='detail')
        pent(B, -HW - 0.3, HW + 0.3, 6.25, 1.6, v=0.0, pitch=0.4, brackets=bays)
        # 2F windows, the balcony on white brackets with the red railing, 3F windows
        wins2 = [(bays[i] + 0.7, bays[i + 1] - 0.7, 7.5, 9.7) for i in range(5)]
        wall_with_windows(B, -HW, HW, 6.6, 10.6, wins2)
        for u in bays:
            M.hbox(B, u - 0.22, u + 0.22, -0.12, 0.0, 6.6, 18.0, 'wall_plaster', tag='main', c0=(*GREEN_GREY, 0))
        M.hbox(B, -HW - 0.5, HW + 0.5, -1.3, 0.0, 10.55, 10.8, 'wall_plaster', tag='main', c0=(*CREAM, 0))
        for u in np.linspace(-HW, HW, 11):
            M.hbox(B, u - 0.15, u + 0.15, -1.15, 0.0, 9.95, 10.55, 'white_paint', tag='detail')
            M.hbox(B, u - 0.12, u + 0.12, -0.75, 0.0, 9.55, 9.95, 'white_paint', tag='detail')
        arch.railing(B, [(-HW - 0.4, -1.2), (HW + 0.4, -1.2)], 10.8, h=0.85, mat='vermilion', cap_mat='gold', tag='main')
        wins3 = [(bays[i] + 0.7, bays[i + 1] - 0.7, 11.5, 13.6) for i in range(5)]
        wall_with_windows(B, -HW, HW, 10.8, 14.6, wins3)
        # the narrow pent roof at 15 m with the 唐破風 over the centre three bays
        pent(B, -HW - 0.2, -4.6, 15.0, 0.9, v=0.0, pitch=0.5)
        pent(B, 4.6, HW + 0.2, 15.0, 0.9, v=0.0, pitch=0.5)
        karahafu(B, 0.0, 9.4, 15.0, 2.9, 1.0, v=0.0)
        wins4 = [(bays[i] + 0.8, bays[i + 1] - 0.8, 16.2, 18.2) for i in range(5)]
        wall_with_windows(B, -HW, HW, 14.6, 19.6, [w for w in wins4 if abs((w[0] + w[1]) / 2) > 3.0])
        # bracket sets under the great eave
        for u in np.linspace(-HW, HW, 9):
            arch.kumimono(B, u, -0.1, 19.0, (0, -1), (1, 0), 'demitsudo', s=0.9, mat='wood_dark', tag='detail')
        M.hbox(B, -HW - 0.6, HW + 0.6, -0.9, 0.05, 19.5, 19.8, 'wood_dark', tag='main')
        # tower sides
        M.side_rect(B, 0.0, D0 + 0.1, 0.0, 19.6, -HW, 'wall_plaster', facing=-1, c0=(*CREAM, 0))
        M.side_rect(B, 0.0, D0 + 0.1, 0.0, 19.6, HW, 'wall_plaster', facing=1, c0=(*CREAM, 0))
        # まねき看板: two rows across the upper front (above the pent roof, below the balcony; and above the balcony)
        maneki(B, -HW + 0.4, HW - 0.4, 7.25, 9.85, -1.75, seed=1)
        maneki(B, -HW + 0.4, HW - 0.4, 11.9, 14.5, -1.45, seed=2)
        # the great lanterns either side of the entrance
        big_lantern(B, -HW - 0.6, -1.4, 5.6)
        big_lantern(B, HW + 0.6, -1.4, 5.6)
        for s in (-1, 1):
            prim.cyl(B, (s * (HW + 0.6), -1.4, 0.0), (s * (HW + 0.6), -1.4, 3.0), 0.09, 0.09, 8, 'black_lacquer', tag='main')
        # ---------------- west wing (corner entrance, balconies), three storeys
        wu0, wu1, wv0, wv1 = HW, 22.0, 5.4, 23.0
        M.side_rect(B, wv0, wv1, -0.3, 12.2, wu1, 'wall_plaster', facing=1, c0=(*CREAM, 0))
        wall_with_windows(B, wu0, wu1, -0.3, 12.2, [(12.0, 14.2, 4.6, 6.4), (15.0, 17.2, 4.6, 6.4), (18.0, 20.2, 4.6, 6.4), (12.0, 14.2, 8.6, 10.4), (15.0, 17.2, 8.6, 10.4), (18.0, 20.2, 8.6, 10.4)], v=wv0)
        for zz in (4.1, 8.1):
            M.hbox(B, wu0, wu1 + 0.6, wv0 - 0.9, wv0, zz - 0.15, zz, 'wall_plaster', tag='main', c0=(*CREAM, 0))
            arch.railing(B, [(wu0 + 0.3, wv0 - 0.85), (wu1 + 0.5, wv0 - 0.85), (wu1 + 0.5, wv0 + 4.0)], zz, h=0.8, mat='vermilion', cap_mat='gold', giboshi=False, tag='main')
        # ground floor of the wing: ticket windows, the corner entrance under a 唐破風
        M.front_rect(B, wu0, wu1, 0.0, 3.4, wv0 + 0.3, 'glass')
        M.hbox(B, wu0, wu1, wv0 - 0.1, wv0 + 0.3, 3.4, 3.8, 'wall_plaster', tag='main', c0=(*CREAM, 0))
        with Frame(B, 0, 0, 0, 0):
            pent(B, wu0, wu1 + 0.6, 3.75, 1.2, v=wv0, pitch=0.45)
            karahafu(B, wu1 - 3.2, 4.6, 4.2, 1.6, 1.4, v=wv0 - 1.2)
        with Frame(B, (wu0 + wu1) / 2 + 0.3, (wv0 + wv1) / 2, 0, 0):
            roof.roof(B, wu1 - wu0 + 0.6, wv1 - wv0, 12.2, 1.4, kind='irimoya', cover='hongawara', pitch=0.55, rafter=0.35, rafter_mat='wood_dark',
                      rafter_end='white_paint', ends='oni')
        # blocker and the front steps
        prim.polygon(B, [(-13.2, 0.0), (HW, 0.0), (HW, wv0), (wu1, wv0), (wu1, wv1), (13.2, D1), (-13.2, D1)], 0.05, 'stone', tag='block')
    used.add('minamiza')
    from shapely.geometry import Polygon
    P = Polygon(S.osm_building(273471468)['poly'][0][0]).buffer(0)
    for pb in S.plateau:
        Q = Polygon(pb['poly'][0][0]).buffer(0)
        if Q.intersects(P) and Q.intersection(P).area > 0.3 * min(Q.area, P.area):
            S.exclude.append([list(map(float, c)) for c in np.asarray(Q.exterior.coords)[:-1]])
            used.add(pb['id'])
