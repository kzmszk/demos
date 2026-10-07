"""東寺 金堂 (国宝, 1603, 豊臣秀頼再建): 入母屋造, 本瓦葺, 一重裳階付 — it looks two-storeyed; 和様 and 大仏様 (天竺様)
mixed: deep bracket tiers (挿肘木) under both eaves, the 裳階 cut up over the middle of the front (切り上げ) with a
small roof of its own over a window (the 観相窓).

Plan (photographs + PLATEAU, refs/toji/dossier.md): the 裳階 wall 7 x 5 bays, 34.0 x 18.6 m (bays 4.0 4.9 5.3 5.6
5.3 4.9 4.0 / 4.0 3.53 3.53 3.53 4.0), the 身舎 inside it 5 x 3 bays (26.0 x 10.6); the 裳階 roof outline 44 x 28.6
(PLATEAU 44.5 x 29.1), the upper eave ~36.5 x 21 m; heights above the platform: 裳階 eave 7.6, upper eave 15.3,
ridge 22.1 (PLATEAU top 24.9 above the ground incl. the 鬼瓦); 基壇 1.35 m (laser DEM), 43 x 31 m with steps
in front of the three front doors and on the other three sides.  Doors: front bays 2, 4, 6; back and ends the
middle bay; the other bays tall 連子 panels over boards.  Unpainted dark timber, white plaster in the bracket
zones, a bronze lantern in front."""
import math
import numpy as np
from jk import prim, arch
from jk.core import Frame
from jk import roof as jroof
from sites.toji_kit import (WOOD, PLASTER, rect, slab, quad, walk_poly, walk_rect, block_rect, block_line, beam, post, furin, bracket_h,
                            nakazonae, TRoof, stone_platform, bronze_lantern)

CX, CY = -1013.5, -603.75
YAW = 0.0
US = np.cumsum([-17.0, 4.0, 4.9, 5.3, 5.6, 5.3, 4.9, 4.0])
VS = np.cumsum([-9.3, 4.0, 3.53, 3.54, 3.53, 4.0])
UI = US[1:-1]; VI = VS[1:-1]                    # 身舎 pillar lines
PANEL = 'wood_natural'                          # the door / window panels read lighter than the frame (photographs)

def kondo(B, S, stats):
    n0 = B.ntri()
    zg = float(np.mean([S.ground(CX + dx, CY + dy) for dx in (-23, 0, 23) for dy in (-17, 17)]))
    zp = float(S.ground(CX, CY)) - 0.02             # the platform top is in the laser DEM (23.98)
    plat = rect(21.5, 15.5)
    steps = [(-10.55, -15.5, 0, -2.6, 4.6), (0.0, -15.5, 0, -2.6, 5.4), (10.55, -15.5, 0, -2.6, 4.6), (0.0, 15.5, 0, 2.6, 5.0),
             (21.5, 0.0, 2.6, 0, 4.0), (-21.5, 0.0, -2.6, 0, 4.0)]
    stone_platform(B, CX, CY, YAW, plat, zg, zp, steps)
    with Frame(B, CX, CY, 0.0, YAW):
        info = body(B, zp)
        bronze_lantern(B, 0.0, -13.2, zp, 2.6)
        # incense burner (常香炉) in front of the middle door
        prim.lathe(B, (0.0, -11.6, zp), [(0.5, 0.0), (0.42, 0.35), (0.25, 0.45), (0.55, 0.7), (0.62, 1.0), (0.4, 1.15), (0.45, 1.35), (0.15, 1.55), (0.0, 1.7)], 12, 'bronze')
        block_rect(B, -0.7, -12.3, 0.7, -10.9, zp)
    S.exclude.append([[CX - 22.5, CY - 16.5], [CX + 22.5, CY - 16.5], [CX + 22.5, CY + 16.5], [CX - 22.5, CY + 16.5]])
    stats['kondo_tris'] = B.ntri() - n0
    stats['kondo'] = {k: round(v - zg, 2) for k, v in info.items() if isinstance(v, float)}
    return zp

def body(B, zp):
    info = {}
    # ---- 裳階: pillars, wall members, bays
    MOK_EAVE = zp + 7.5
    kind_m, s_m = 'mitesaki', 1.4
    bh_m, reach_m = bracket_h(kind_m, s_m)
    Lm, Dm = US[-1] - US[0], VS[-1] - VS[0]
    o_m = (44.0 - (US[-1] - US[0]) - 2 * reach_m) / 2           # the 裳階 roof outline is ~44 x 28.6 m (PLATEAU 44.5 x 29.1)
    Lr, Dr = Lm + 2 * reach_m, Dm + 2 * reach_m
    c_m = Dr / 2 + o_m
    d_in = (VS[-1] - VI[-1]) + reach_m + o_m              # eave line -> 身舎 wall (same on all sides: the 裳階 is one 4 m bay)
    z_junc = zp + 10.8
    teri_m = 1.8
    H_m = (z_junc - MOK_EAVE) / (d_in / c_m) ** teri_m
    z_eave_m = MOK_EAVE + H_m * (o_m / c_m) ** teri_m
    top_m = z_eave_m - 0.32
    h_m = top_m - bh_m
    info.update(mokoshi_plate=h_m, mokoshi_eave=MOK_EAVE)
    for u in US:
        for v in VS:
            if u in (US[0], US[-1]) or v in (VS[0], VS[-1]):
                post(B, u, v, zp, h_m, 0.3, WOOD, seg=14, base='stone', base_h=0.2)
    for (zz, hh) in ((zp + 0.3, 0.3), (zp + 1.55, 0.22), (zp + (h_m - zp) * 0.8, 0.26)):
        arch.nageshi(B, Lm, Dm, zz, h=hh, w=0.13, out=0.08, mat=WOOD)
    arch.nageshi(B, Lm, Dm, h_m, h=0.32, w=0.22, out=0.02, mat=WOOD)
    z_in = zp + (h_m - zp) * 0.8 - 0.26
    fronts = {0: {1, 3, 5}, 2: {3}, 1: {2}, 3: {2}}
    sides = [(0, [((US[i], VS[0]), (US[i + 1], VS[0])) for i in range(7)], (0, -1)),
             (2, [((US[i + 1], VS[-1]), (US[i], VS[-1])) for i in range(7)], (0, 1)),
             (1, [((US[-1], VS[i]), (US[-1], VS[i + 1])) for i in range(5)], (1, 0)),
             (3, [((US[0], VS[i + 1]), (US[0], VS[i])) for i in range(5)], (-1, 0))]
    for (side, segs, nrm) in sides:
        for i, (p0, p1) in enumerate(segs):
            idx = i if side in (0, 1) else len(segs) - 1 - i
            if side == 0 and idx == 3:
                # the middle bay of the front rises to the 切り上げ: door below, 観相窓 above
                door(B, p0, p1, nrm, zp, z_in)
                arch.infill(B, p0, p1, z_in + 0.3, h_m - 0.2, 'board', out=nrm, mat=WOOD)
                continue
            if idx in fronts[side]:
                door(B, p0, p1, nrm, zp, z_in)
            else:
                window(B, p0, p1, nrm, zp, z_in)
            arch.infill(B, p0, p1, z_in + 0.3, h_m - 0.2, 'board', out=nrm, mat=WOOD)
    # 裳階 bracket zone: 三手先-like 挿肘木 tiers on the pillars, 平三斗 between, two rows of white plaster, 通肘木
    top2, _ = arch.bracket_row(B, Lm, Dm, h_m, kind_m, s_m, WOOD, WOOD, us=US, vs=VS, purlin=True)
    for (side, segs, nrm) in sides:
        for (p0, p1) in segs:
            a = np.asarray(p0, float); b = np.asarray(p1, float); d = (b - a) / np.linalg.norm(b - a)
            m = (a + b) / 2
            arch.kumimono(B, m[0], m[1], h_m, nrm, d, 'hira', 0.95, WOOD)
            zmid = h_m + (top_m - h_m) * 0.5
            for (za, zb) in ((h_m + 0.02, zmid - 0.12), (zmid + 0.12, top_m - 0.15)):
                quad(B, (*(a + d * 0.3), za), (*(b - d * 0.3), za), (*(b - d * 0.3), zb), (*(a + d * 0.3), zb), 'temple_wall', both=True, c0=PLASTER)
            prim.obox(B, (*(a - d * 0.1 + np.array(nrm) * 0.02), zmid), (*(b + d * 0.1 + np.array(nrm) * 0.02), zmid), 0.2, 0.24, WOOD)
    # 裳階 ceiling (from the wall out to beyond the purlin)
    ring(B, Lm / 2, Dm / 2, Lm / 2 + reach_m + 0.3, Dm / 2 + reach_m + 0.3, top_m - 0.12)
    # 裳階 roof: a hip roof cut off at the 身舎 wall, opened over the middle of the front for the raised section
    rf = jroof.Roof(Lr, Dr, z_eave_m, o_m, kind='yosemune', cover='hongawara', pitch=H_m / c_m, teri=teri_m, sori=0.5, sori_len=0.35, rafter=0.27,
                    rafter_mat=WOOD, rafter_end=WOOD, fascia_mat=WOOD, tiers=2, ends='oni', edge=0.36, ridge_h=0.6, ridge_w=0.5, truncate=d_in + 0.1)
    smax = lambda xs, dc: np.minimum(np.minimum(dc, rf.c), d_in + 0.1)
    RAISE = 5.6                                     # half width of the 切り上げ
    for k in range(4):
        E = rf.sides()[k][3]
        if k == 0:
            cut0, cut1 = E / 2 - RAISE, E / 2 + RAISE
            rf.face(B, 0, x0=0.0, x1=cut0, smax=smax); rf.face(B, 0, x0=cut1, x1=E, smax=smax)
            rf.eave(B, 0, 0.0, cut0); rf.eave(B, 0, cut1, E)
            # the cut ends: bargeboards up the slope
            for xc in (cut0, cut1):
                pts = np.array([(-rf.a + xc, -rf.c + s_, float(rf.z(s_, min(xc, E - xc))) - 0.05) for s_ in np.linspace(0, d_in, 8)])
                prim.sweep(B, pts, [(-0.06, 0.0), (0.06, 0.0), (0.06, -0.38), (-0.06, -0.38)], WOOD, tag='main', caps=True)
                rf.ridge(B, pts[::-1] + [0, 0, 0.1], 0.32, 0.3, ends=(None, 'oni'))
        else:
            rf.face(B, k, smax=smax); rf.eave(B, k, 0.0, E)
    for k in range(4):
        hl = rf.hip_line(k, (d_in + 0.1) * 0.97)
        rf.ridge(B, hl[1:][::-1], rf.ridge_w * 0.6, rf.ridge_h * 0.55, ends=(None, 'oni'))
    zc = float(rf.zE(0.0)) - rf.edge
    for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        furin(B, sx * (rf.a - 0.3), sy * (rf.c - 0.3), zc, 1.1)
    # ---- 切り上げ: the middle of the front rises over a window to its own small hip roof
    zr0 = zp + 10.3                               # its eave (at the 裳階 roof's top, photographs)
    u0, u1 = -RAISE, RAISE
    for u in (u0, u1):
        post(B, u, VS[0], h_m, zr0 - 1.2, 0.26, WOOD, base=None)
    beam(B, (u0 - 0.3, VS[0]), (u1 + 0.3, VS[0]), zr0 - 1.1, 0.24, 0.34, WOOD)
    beam(B, (u0, VS[0]), (u1, VS[0]), top_m + 0.1, 0.2, 0.3, WOOD)
    # 観相窓: a framed opening with shutters (boards) and a lattice; plaster around
    arch.infill(B, (-2.8, VS[0]), (2.8, VS[0]), top_m + 0.25, zr0 - 1.3, 'renji', out=(0, -1), mat=WOOD)
    for (ua, ub) in ((u0, -2.8), (2.8, u1)):
        arch.infill(B, (ua, VS[0]), (ub, VS[0]), top_m + 0.25, zr0 - 1.3, 'plaster', out=(0, -1), mat=WOOD, seed=3)
    for u in (u0, u1):           # side walls of the raised bay, back to the 身舎
        quad(B, (u, VS[0], top_m), (u, VI[0], top_m), (u, VI[0], zr0 - 0.95), (u, VS[0], zr0 - 0.95), 'temple_wall', both=True, c0=PLASTER)
    for u in np.linspace(u0, u1, 5):
        arch.kumimono(B, u, VS[0], zr0 - 1.2, (0, -1), (1, 0), 'degumi', 0.85, WOOD)
    rr = jroof.Roof(2 * RAISE + 1.4, 2 * (VI[0] - VS[0]) + 2 * 1.0, zr0 + 0.22, 1.6, kind='yosemune', cover='hongawara', pitch=0.26, teri=1.5, sori=0.35,
                    rafter=0.26, rafter_mat=WOOD, rafter_end=WOOD, fascia_mat=WOOD, tiers=2, ends='oni', edge=0.32, ridge_h=0.5, ridge_w=0.42)
    with Frame(B, 0.0, VI[0], 0.0, 0.0):
        rr.build(B)
    info.update(raised_eave=zr0)
    # ---- 身舎: pillars up to the upper wall plate, walls, the upper bracket zone, the upper roof
    kind_u, s_u = 'mitesaki', 1.5
    bh_u, reach_u = bracket_h(kind_u, s_u)
    Li, Di = UI[-1] - UI[0], VI[-1] - VI[0]
    UP_EAVE = zp + 15.0
    o_u = (38.0 - (UI[-1] - UI[0]) - 2 * reach_u) / 2            # the upper eave ~38 m wide (0.86 of the 裳階 roof, photographs)
    Lu, Du = Li + 2 * reach_u, Di + 2 * reach_u
    c_u = Du / 2 + o_u
    RIDGE = zp + 22.0
    teri_u = 1.5
    pitch_u = (RIDGE - UP_EAVE) / c_u
    z_eave_u = UP_EAVE + c_u * pitch_u * (o_u / c_u) ** teri_u
    top_u = z_eave_u - 0.32
    h_u = top_u - bh_u
    info.update(upper_plate=h_u, upper_eave=UP_EAVE, ridge=RIDGE)
    for u in UI:
        for v in VI:
            if u in (UI[0], UI[-1]) or v in (VI[0], VI[-1]):
                prim.cyl(B, (u, v, zp), (u, v, h_u), 0.36, 0.35, 14, WOOD, caps=(False, True))
    # the 身舎 walls (boards) from the 裳階 ceiling up, 長押 and 頭貫
    for (a, b, nrm) in (((UI[0], VI[0]), (UI[-1], VI[0]), (0, -1)), ((UI[-1], VI[0]), (UI[-1], VI[-1]), (1, 0)), ((UI[-1], VI[-1]), (UI[0], VI[-1]), (0, 1)),
                        ((UI[0], VI[-1]), (UI[0], VI[0]), (-1, 0))):
        quad(B, (*a, top_m - 0.2), (*b, top_m - 0.2), (*b, h_u - 0.2), (*a, h_u - 0.2), WOOD, both=True)
    arch.nageshi(B, Li, Di, h_u, h=0.34, w=0.24, out=0.02, mat=WOOD)
    arch.nageshi(B, Li, Di, h_u - 0.9, h=0.26, w=0.14, out=0.1, mat=WOOD)
    top_u2, _ = arch.bracket_row(B, Li, Di, h_u, kind_u, s_u, WOOD, WOOD, us=UI, vs=VI, purlin=True)
    for (a, b, nrm) in (((UI[i], VI[0]), (UI[i + 1], VI[0]), (0, -1)) for i in range(5)):
        nakazonae(B, a, b, h_u, s_u, nrm, WOOD, n=1)
    for (a, b, nrm) in (((UI[i], VI[-1]), (UI[i + 1], VI[-1]), (0, 1)) for i in range(5)):
        nakazonae(B, a, b, h_u, s_u, nrm, WOOD, n=1)
    for (a, b, nrm) in (((UI[-1], VI[i]), (UI[-1], VI[i + 1]), (1, 0)) for i in range(3)):
        nakazonae(B, a, b, h_u, s_u, nrm, WOOD, n=1)
    for (a, b, nrm) in (((UI[0], VI[i]), (UI[0], VI[i + 1]), (-1, 0)) for i in range(3)):
        nakazonae(B, a, b, h_u, s_u, nrm, WOOD, n=1)
    tooshi_rect(B, Li, Di, h_u, s_u)
    for (a, b) in (((UI[0], VI[0]), (UI[-1], VI[0])), ((UI[-1], VI[0]), (UI[-1], VI[-1])), ((UI[-1], VI[-1]), (UI[0], VI[-1])), ((UI[0], VI[-1]), (UI[0], VI[0]))):
        quad(B, (*a, h_u), (*b, h_u), (*b, top_u - 0.12), (*a, top_u - 0.12), WOOD, both=True)
    ring(B, Li / 2, Di / 2, Li / 2 + reach_u + 0.35, Di / 2 + reach_u + 0.35, top_u - 0.12)
    rf2 = TRoof(Lu, Du, z_eave_u, o_u, kind='irimoya', cover='hongawara', pitch=pitch_u, teri=teri_u, sori=0.65, sori_len=0.38, gable_frac=0.6, verge=0.9,
                edge=0.42, rafter=0.27, rafter_mat=WOOD, rafter_end=WOOD, fascia_mat=WOOD, tiers=2, ends='oni', ridge_h=1.15, ridge_w=0.75,
                bargeboard_mat=WOOD, gable_wall='temple_wall')
    res = rf2.build(B)
    zc = float(rf2.zE(0.0)) - rf2.edge
    for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        furin(B, sx * (rf2.a - 0.3), sy * (rf2.c - 0.3), zc, 1.3)
    info.update(ridge_built=res['z_ridge'])
    block_rect(B, US[0] - 0.4, VS[0] - 0.4, US[-1] + 0.4, VS[-1] + 0.4, zp + 0.05)
    return info

def ring(B, a0, c0, a1, c1, z, mat=WOOD):
    outer = [(-a1, -c1), (a1, -c1), (a1, c1), (-a1, c1)]; inner = [(-a0, -c0), (a0, -c0), (a0, c0), (-a0, c0)]
    for i in range(4):
        j = (i + 1) % 4
        P = np.array([(*outer[i], z), (*outer[j], z), (*inner[j], z), (*inner[i], z)])
        B.add(P, [[0, 2, 1], [0, 3, 2]], mat)

def tooshi_rect(B, L, D, plate, s):
    """通肘木 bands of a 三手先 row on a rectangle (see toji_pagoda.tooshi)"""
    mh = 0.17 * s; hh = 0.17 * s; arm = 0.55 * s
    for k in range(4):
        z0 = plate + mh * 1.5 + k * (hh + mh)
        d = k * arm
        a, c = L / 2 + d, D / 2 + d
        for (p0, p1) in (((-a, -c), (a, -c)), ((a, -c), (a, c)), ((a, c), (-a, c)), ((-a, c), (-a, -c))):
            prim.obox(B, (*p0, z0 + hh / 2), (*p1, z0 + hh / 2), 0.13 * s, hh, WOOD, tag='detail' if k else 'main')

def door(B, p0, p1, nrm, z0, z1):
    """桟唐戸 pair: lighter panels in a dark frame with rails"""
    arch.infill(B, p0, p1, z0 + 0.32, z1, 'karado', out=nrm, mat=PANEL)
    a = np.asarray(p0, float); b = np.asarray(p1, float); d = (b - a) / np.linalg.norm(b - a); n = np.asarray(nrm, float)
    m = (a + b) / 2
    prim.obox(B, np.r_[m + n * 0.03, z0 + 0.35], np.r_[m + n * 0.03, z1], 0.1, 0.06, WOOD, tag='detail')
    for zz in (z0 + 0.35, z1 - 0.05):
        prim.obox(B, np.r_[a + d * 0.3 + n * 0.03, zz], np.r_[b - d * 0.3 + n * 0.03, zz], 0.08, 0.08, WOOD, tag='detail')

def window(B, p0, p1, nrm, z0, z1):
    """tall 連子 panel over a board 腰 (the front bays without doors)"""
    zk = z0 + 1.55
    arch.infill(B, p0, p1, z0 + 0.32, zk - 0.12, 'board', out=nrm, mat=WOOD)
    arch.infill(B, p0, p1, zk + 0.1, z1, 'renji', out=nrm, mat=PANEL)
