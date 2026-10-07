"""東寺 西院 御影堂 (大師堂, 国宝, 1380 / 1390): a residential-style (住宅風) hall of three parts under 檜皮葺 roofs —
the 後堂 (south, 1380: ridge E-W, 入母屋), the 前堂 (north, 1390: ridge N-S, 入母屋 with its big gable over the
entrance) and the 中門 (west wing, 切妻).  蔀戸, white plaster panels, a 縁 with a low railing, the copper-roofed
唐破風 canopy over the north entrance, stone paving (石畳) in front, a bronze 常香炉.

Heights from PLATEAU LOD2 roofs (above the ground, 22.75): 後堂 ridge 10.1 (x -1105.3..-1086.8 at y -467.2), eaves 6.6 /
5.7 (錣 break); 前堂 ridge 9.9 (x -1093.5, y -451.1..-466.8), eaves 6.0 / 4.9; 中門 ridge 6.2 (y -452.1), eaves 4.2."""
import math
import numpy as np
from jk import prim, arch
from jk.core import Frame
from jk import roof as jroof
from sites.toji_kit import (WOOD, PLASTER, rect, slab, quad, walk_poly, walk_rect, block_rect, block_line, beam, post, TRoof, troof, bronze_lantern,
                            skirt_roof)
from sites.toji_gates import rect_world

def walls_box(B, x0, y0, x1, y1, z0, z1, pattern, posts=2.4):
    """the outer walls of a part (in the current frame): pillars every ~posts m; each bay 蔀戸 (lattice) or plaster per
    pattern(side, i) -> 'shitomi' | 'plaster' | 'door' | 'open'"""
    sides = [((x0, y0), (x1, y0), (0, -1)), ((x1, y0), (x1, y1), (1, 0)), ((x1, y1), (x0, y1), (0, 1)), ((x0, y1), (x0, y0), (-1, 0))]
    for si, (a, b, n) in enumerate(sides):
        a = np.asarray(a, float); b = np.asarray(b, float); L = np.linalg.norm(b - a)
        k = max(1, int(round(L / posts)))
        pts = [a + (b - a) * j / k for j in range(k + 1)]
        for j, p in enumerate(pts[:-1]):
            post(B, p[0], p[1], z0, z1, 0.14, WOOD, base='stone', base_h=0.15)
            kind = pattern(si, j, k)
            if kind == 'open': continue
            q0, q1 = pts[j], pts[j + 1]
            if kind == 'shitomi':
                shitomi(B, q0, q1, z0 + 0.1, z0 + (z1 - z0) * 0.55, n)
                arch.infill(B, q0, q1, z0 + (z1 - z0) * 0.57, z1 - 0.1, 'plaster', out=n, mat=WOOD, seed=j)
            elif kind == 'door':
                arch.infill(B, q0, q1, z0 + 0.1, z0 + (z1 - z0) * 0.7, 'board', out=n, mat=WOOD)
                arch.infill(B, q0, q1, z0 + (z1 - z0) * 0.72, z1 - 0.1, 'plaster', out=n, mat=WOOD, seed=j)
            else:
                arch.infill(B, q0, q1, z0 + 0.1, z1 - 0.1, 'plaster', out=n, mat=WOOD, seed=j + 3)
        prim.obox(B, (*a, z1 - 0.1), (*b, z1 - 0.1), 0.16, 0.22, WOOD)
        prim.obox(B, (*a, z0 + (z1 - z0) * 0.56), (*b, z0 + (z1 - z0) * 0.56), 0.13, 0.16, WOOD)
    block_rect(B, x0 - 0.2, y0 - 0.2, x1 + 0.2, y1 + 0.2, z0)

def z_eave_for(zE, c, o, pitch, teri):
    """the kit's z_eave (roof surface over the wall plate) for a wanted eave-edge height zE"""
    return zE + c * pitch * (o / c) ** teri

def shitomi(B, p0, p1, z0, z1, out):
    """蔀戸: a fine square lattice (dark) over white paper, in a frame; the upper leaf of each bay"""
    a = np.asarray(p0, float); b = np.asarray(p1, float); d = (b - a) / np.linalg.norm(b - a); n = np.asarray(out, float)
    q0 = a + d * 0.15 + n * 0.0; q1 = b - d * 0.15
    quad(B, (*(q0 - n * 0.05), z0), (*(q1 - n * 0.05), z0), (*(q1 - n * 0.05), z1), (*(q0 - n * 0.05), z1), 'white_paint', both=True)
    L = float(np.linalg.norm(q1 - q0))
    for t in np.arange(0.12, L, 0.24):
        q = q0 + d * t
        prim.obox(B, (*(q + n * 0.0), z0), (*(q + n * 0.0), z1), 0.03, 0.04, WOOD, tag='detail', ends=False)
    for zz in np.arange(z0 + 0.12, z1, 0.24):
        prim.obox(B, (*(q0 + n * 0.0), zz), (*(q1 + n * 0.0), zz), 0.03, 0.04, WOOD, tag='detail', ends=False)
    for zz in (z0, z1, (z0 + z1) / 2):
        prim.obox(B, (*(q0 + n * 0.02), zz), (*(q1 + n * 0.02), zz), 0.08, 0.1, WOOD, tag='main')

def mieido(B, S, stats):
    n0 = B.ntri()
    zg = float(np.mean([S.ground(x, y) for x in (-1108, -1096, -1084) for y in (-476, -460, -446)]))
    zf = zg + 0.75                                      # the floor (縁 level)
    HW = 'hiwada'
    VER = 1.8                                           # the 縁 under the 庇
    # ---- 後堂 (south): core 18.0 x 9.2, a 庇 skirt (eave 5.7 above the ground) and the 入母屋 over the core (break 6.6, ridge 10.1)
    cx1, cy1 = -1096.05, -467.2
    Lc, Dc = 18.0, 9.2
    with Frame(B, cx1, cy1, 0.0, 0.0):
        slab(B, -Lc / 2 - VER - 0.9, -Dc / 2 - VER - 0.9, Lc / 2 + VER + 0.9, Dc / 2 + VER + 0.9, zg - 0.3, zf - 0.12, 'stone', faces='xXyYZ')
        slab(B, -Lc / 2 - VER, -Dc / 2 - VER, Lc / 2 + VER, Dc / 2 + VER, zf - 0.12, zf, 'wood_natural', faces='ZxXyY')
        walk_rect(B, -Lc / 2 - VER, -Dc / 2 - VER, Lc / 2 + VER, Dc / 2 + VER, zf)
        walls_box(B, -Lc / 2, -Dc / 2, Lc / 2, Dc / 2, zf, zf + 5.95, lambda si, j, k: 'shitomi' if si in (0, 1, 3) else 'plaster')
        for (x, y) in veranda_posts(Lc, Dc, VER):
            post(B, x, y, zf, zf + 4.75, 0.11, WOOD, base=None)
        rail(B, Lc, Dc, VER, zf, skip_side=None)
        sk = skirt_roof(B, Lc + 2 * VER, Dc + 2 * VER, z_eave_for(zf + 4.95, Dc / 2 + VER + 0.8, 0.8, 0.33, 1.1), 0.8, VER + 0.8, cover=HW, pitch=0.33,
                        teri=1.1, sori=0.15, edge=0.4, rafter=0.3, tiers=1)
        c = Dc / 2 + 1.2
        rf = TRoof(Lc, Dc, z_eave_for(zf + 5.85, c, 1.2, 3.5 / c, 1.3), 1.2, kind='irimoya', cover=HW, pitch=3.5 / c, teri=1.3, sori=0.3, sori_len=0.4,
                   gable_frac=0.45, verge=0.7, edge=0.46, rafter=0.24, rafter_mat=WOOD, rafter_end=WOOD, fascia_mat=WOOD, tiers=2, ends='oni', ridge_h=0.6,
                   ridge_w=0.55, bargeboard_mat=WOOD, gable_wall='temple_wall')
        r1 = rf.build(B)
    # ---- 前堂 (north): core 12.8 x 12.6 (ridge N-S), skirt on the north / east / west, the 入母屋 runs south into the 後堂 roof
    cx2, cy2 = -1093.2, -456.0
    yaw2 = math.radians(90.0)
    Lc2, Dc2 = 12.8, 12.6
    with Frame(B, cx2, cy2, 0.0, yaw2):
        slab(B, -Lc2 / 2, -Dc2 / 2 - VER - 0.9, Lc2 / 2 + VER + 0.9, Dc2 / 2 + VER + 0.9, zg - 0.3, zf - 0.12, 'stone', faces='xXyYZ')
        slab(B, -Lc2 / 2, -Dc2 / 2 - VER, Lc2 / 2 + VER, Dc2 / 2 + VER, zf - 0.12, zf, 'wood_natural', faces='ZxXyY')
        walk_rect(B, -Lc2 / 2, -Dc2 / 2 - VER, Lc2 / 2 + VER, Dc2 / 2 + VER, zf)
        walls_box(B, -Lc2 / 2, -Dc2 / 2, Lc2 / 2, Dc2 / 2, zf, zf + 5.35,
                  lambda si, j, k: ('door' if j == k // 2 else 'shitomi') if si == 1 else ('shitomi' if si in (0, 2) else 'open'))
        for (x, y) in veranda_posts(Lc2, Dc2, VER):
            if x < -Lc2 / 2 + 0.1: continue
            post(B, x, y, zf, zf + 3.95, 0.11, WOOD, base=None)
        rail(B, Lc2, Dc2, VER, zf, skip_side=3, gap_side=1)
        c2 = Dc2 / 2 + VER + 0.8
        sk2 = jroof.Roof(Lc2 + 2 * VER, Dc2 + 2 * VER, z_eave_for(zf + 4.15, c2, 0.8, 0.33, 1.1), 0.8, kind='yosemune', cover=HW, pitch=0.33, teri=1.1,
                         sori=0.15, sori_len=0.35, rafter=0.3, rafter_mat=WOOD, rafter_end=WOOD, fascia_mat=WOOD, tiers=1, ends=None, edge=0.4, truncate=VER + 0.8)
        smax = lambda xs, dc: np.minimum(np.minimum(dc, sk2.c), VER + 0.8)
        for k in (0, 1, 2):
            E = sk2.sides()[k][3]
            x0 = 0.0 if k != 2 else 0.0
            x1 = E if k != 0 else E
            if k == 0: sk2.face(B, 0, x0=VER + 2.0, x1=E, smax=smax); sk2.eave(B, 0, VER + 2.0, E)
            elif k == 2: sk2.face(B, 2, x0=0.0, x1=E - VER - 2.0, smax=smax); sk2.eave(B, 2, 0.0, E - VER - 2.0)
            else: sk2.face(B, k, smax=smax); sk2.eave(B, k, 0.0, E)
        for k in (1, 2):
            hl = sk2.hip_line(k, (VER + 0.8) * 0.97)
            sk2.ridge(B, hl[1:][::-1], 0.3, 0.25, ends=(None, None))
        c3 = Dc2 / 2 + 1.1
        rf2 = TRoof(Lc2 + 6.0, Dc2, z_eave_for(zf + 5.25, c3, 1.1, 3.9 / c3, 1.3), 1.1, kind='irimoya', cover=HW, pitch=3.9 / c3, teri=1.3, sori=0.3, sori_len=0.4,
                    gable_frac=0.36, verge=0.75, edge=0.46, rafter=0.24, rafter_mat=WOOD, rafter_end=WOOD, fascia_mat=WOOD, tiers=2, ends='oni', ridge_h=0.6,
                    ridge_w=0.55, bargeboard_mat=WOOD, gable_wall='temple_wall')
        with Frame(B, -3.0, 0.0, 0.0, 0.0):
            r2 = rf2.build(B)
        # steps up to the north 縁 under the 唐破風 canopy
        un = Lc2 / 2 + VER
        arch.stairs(B, (un + 2.2, 0.0), (un, 0.0), zg, zf, 3.6, 'stone', riser=0.15, walk=True)
        karahafu(B, un, 0.0, zf, zg)
        bronze_lantern(B, un + 7.5, -4.0, zg, 2.2, lit=True)
        prim.lathe(B, (un + 6.0, 3.5, zg), [(0.55, 0.0), (0.5, 0.45), (0.2, 0.55), (0.25, 0.9), (0.6, 1.1), (0.65, 1.4), (0.35, 1.55), (0.42, 1.7), (0.1, 1.95), (0.0, 2.05)], 12, 'bronze')
        block_rect(B, un + 5.3, 2.8, un + 6.7, 4.2, zg)
    # ---- 中門 (west wing): 切妻 檜皮, ridge E-W (eave 4.2, ridge 6.2 above the ground)
    cx3, cy3 = -1104.4, -452.6
    with Frame(B, cx3, cy3, 0.0, 0.0):
        slab(B, -3.5, -4.6, 3.5, 4.6, zg - 0.3, zf - 0.1, 'stone', faces='xXyYZ')
        walls_box(B, -3.0, -3.4, 3.0, 3.4, zf, zf + 3.0, lambda si, j, k: 'shitomi' if si in (0, 2) else 'plaster', posts=2.0)
        c4 = 3.4 + 1.15
        troof(B, 6.6, 6.8, z_eave_for(zf + 3.45, c4, 1.15, 2.0 / c4, 1.2), 1.15, kind='kirizuma', cover=HW, pitch=2.0 / c4, teri=1.2, sori=0.0, verge=0.7, edge=0.28,
              rafter=0.25, rafter_mat=WOOD, rafter_end=WOOD, fascia_mat=WOOD, ends='oni', ridge_h=0.45, ridge_w=0.45, tiers=1, bargeboard_mat=WOOD, gable_wall='temple_wall')
    S.exclude.append([[-1110.0, -477.0], [-1080.0, -477.0], [-1080.0, -443.5], [-1110.0, -443.5]])
    stats['mieido_tris'] = B.ntri() - n0
    stats['mieido'] = dict(ridge_s=round(r1['z_ridge'] - zg, 2), ridge_n=round(r2['z_ridge'] - zg, 2))

def veranda_posts(L, D, ver, step=3.4):
    out = []
    a, c = L / 2 + ver - 0.12, D / 2 + ver - 0.12
    for (p0, p1) in (((-a, -c), (a, -c)), ((a, -c), (a, c)), ((a, c), (-a, c)), ((-a, c), (-a, -c))):
        p0 = np.array(p0); p1 = np.array(p1); n = max(1, int(round(np.linalg.norm(p1 - p0) / step)))
        out += [tuple(p0 + (p1 - p0) * k / n) for k in range(n)]
    return out

def rail(B, L, D, ver, zf, skip_side=None, gap_side=None):
    """a low 縁 railing (擬宝珠 none) round the veranda edge; a gap in the middle of gap_side for the steps"""
    a, c = L / 2 + ver - 0.1, D / 2 + ver - 0.1
    sides = [((-a, -c), (a, -c)), ((a, -c), (a, c)), ((a, c), (-a, c)), ((-a, c), (-a, -c))]
    for k, (p0, p1) in enumerate(sides):
        if k == skip_side: continue
        p0 = np.array(p0); p1 = np.array(p1)
        segs = [(p0, p1)]
        if k == gap_side:
            m = (p0 + p1) / 2; d = (p1 - p0) / np.linalg.norm(p1 - p0)
            segs = [(p0, m - d * 2.0), (m + d * 2.0, p1)]
        for (a_, b_) in segs:
            arch.railing(B, [tuple(a_), tuple(b_)], zf, h=0.6, mat=WOOD, giboshi=False, tag='detail')
            block_line(B, [tuple(a_), tuple(b_)], zf, 0.45)

def karahafu(B, u0, v0, zf, zg, W=7.6, Dp=3.8, h=3.3):
    """the copper-roofed porch with a 唐破風 front: two posts, a 虹梁, a bowed (起り) copper roof whose front edge
    rises in the middle (local frame of the 前堂: +u is north, the porch projects to +u)"""
    for v in (-W / 2 + 0.4, W / 2 - 0.4):
        post(B, u0 + Dp - 0.5, v, zg, zf + h, 0.13, WOOD, base='stone', base_h=0.3)
        beam(B, (u0, v), (u0 + Dp - 0.5, v), zf + h, 0.13, 0.22, WOOD)
    beam(B, (u0 + Dp - 0.5, -W / 2), (u0 + Dp - 0.5, W / 2), zf + h, 0.16, 0.3, WOOD)
    zt = zf + h + 0.35
    nu, nv = 16, 10
    def f(x, t):
        # x across (v), t from the wall (0) to the front edge (1)
        bow = 0.75 * math.cos(math.pi * x / W) ** 2            # 唐破風: the front edge rises in the middle
        z = zt + 0.9 * (1 - t) - 0.35 * t * t + bow * t ** 3
        return (u0 - 0.2 + (Dp + 0.5) * t, x, z)
    P = prim.grid_surface(B, f, -W / 2 - 0.3, W / 2 + 0.3, 0.0, 1.0, nu, nv, 'copper', flip=True, tag='main')
    prim.grid_surface(B, lambda x, t: tuple(np.array(f(x, t)) - [0, 0, 0.12]), -W / 2 - 0.3, W / 2 + 0.3, 0.0, 1.0, nu, nv, WOOD, flip=False, tag='main')
    # the bargeboard of the 唐破風 (front edge) and its 兎毛通 (the hanging ornament)
    edge = np.array([f(x, 1.0) for x in np.linspace(-W / 2 - 0.3, W / 2 + 0.3, 24)])
    prim.sweep(B, edge - [0, 0, 0.06], [(-0.08, 0.0), (0.08, 0.0), (0.08, -0.38), (-0.08, -0.38)], WOOD, tag='main', caps=True)
    prim.box(B, u0 + Dp + 0.25, -0.35, zt + 0.2, u0 + Dp + 0.35, 0.35, zt + 0.6, 'bronze', tag='detail')
    for x in (-W / 2 - 0.3, W / 2 + 0.3):
        side = np.array([f(x, t) for t in np.linspace(0, 1, 10)])
        prim.sweep(B, side - [0, 0, 0.06], [(-0.06, 0.0), (0.06, 0.0), (0.06, -0.3), (-0.06, -0.3)], WOOD, tag='main', caps=True)
    walk_rect(B, u0, -W / 2, u0 + 2.2, W / 2, zg + 0.02)
    # the lanterns 「祈願所」 hung from the beam
    for v in (-W / 2 + 1.4, W / 2 - 1.4):
        prim.cyl(B, (u0 + Dp - 0.5, v, zf + h - 0.75), (u0 + Dp - 0.5, v, zf + h), 0.01, 0.01, 4, 'metal_dark', tag='detail')
        prim.lathe(B, (u0 + Dp - 0.5, v, zf + h - 1.75), [(0.22, 0.0), (0.3, 0.2), (0.31, 0.5), (0.3, 0.8), (0.22, 1.0)], 12, 'lantern_paper')
        B.lamp(u0 + Dp - 0.5, v, zf + h - 1.25, 7.0)
