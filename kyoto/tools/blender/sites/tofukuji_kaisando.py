"""東福寺 常楽庵: the 樓門 at the top of the covered stair from the 通天橋, the 昭堂 (重文, 1826) with the two-storey 伝衣閣
rising out of its roof (one of the 京の五閣: balcony, shoji and lattice windows, a 宝形 roof of dark shingles with a
copper 露盤 and a gilt flaming jewel), the 開山堂 behind, and the garden in front: raked sand west of the axis path,
a narrow pond with a slab bridge, rocks and clipped azaleas on a hillock to the east.

Frame: the OSM 開山堂 rectangle (1393.5, -845.1), turned 11.1° clockwise (u ≈ east, v ≈ north); the axis path runs
along u = 0.2 from the 樓門 (v -43 .. -33) to the 昭堂 (front at v -4)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
import jk
from jk import prim, arch, Frame
from jk import roof as jroof
from sites import tofukuji_lib as L
from sites import tofukuji_klib as K
from sites import tofukuji_ekit as EK
from sites import tofukuji_halls as HL

O = (1393.5, -845.1)
ZG = 54.25
ZF = 54.85
WD = 'wood_dark'
AX = 0.2                 # the axis path (u)

def loc():
    return L.Loc(O[0], O[1], L.ROT_K)

def cull_region(Bsrc, poly_world, zmin):
    """drop triangles whose centroid lies inside poly_world (plan) and above zmin"""
    for p in Bsrc.parts:
        C = p['P'][p['I']].mean(1)
        bad = shapely.contains_xy(poly_world, C[:, 0], C[:, 1]) & (C[:, 2] > zmin)
        if bad.any(): K.compact(p, p['I'][~bad])

def shodo(B, S):
    lc = loc()
    us = HL.bays([3.0, 3.0, 3.0, 4.0, 3.0, 3.0, 3.0]) + AX
    vs = HL.bays([2.6, 2.7, 2.6]) - 0.2
    Lh, Dh = us[-1] - us[0], vs[-1] - vs[0]
    zt = ZF + 3.75
    zbal = ZF + 6.55
    pw = 2.5                 # 伝衣閣 half width (pillar lines)
    Bl = jk.Builder('shodo_roof')
    with lc.frame(B):
        Bl.xf = B.xf
        # platform, steps on the axis
        pa, pc = Lh / 2 + 1.6, Dh / 2 + 1.6
        prim.box(B, -pa + AX, vs[0] - 1.6, ZG - 0.4, pa + AX, vs[-1] + 1.6, ZF, 'stone', c1=(0, 3, 0, 0))
        L.poly_flat(B, [(-pa + AX, vs[0] - 1.6), (pa + AX, vs[0] - 1.6), (pa + AX, vs[-1] + 1.6), (-pa + AX, vs[-1] + 1.6)], ZF, 'stone', tag='walk')
        K.steps(B, (AX, vs[0] - 2.8), (AX, vs[0] - 1.6), ZG, ZF, 4.6, mat='stone', riser=0.15)
        HL.pillars(B, us, vs, ZF, zt, 0.15, round_=False)
        front = ['maira', 'maira', 'maira', 'koshi', 'maira', 'maira', 'maira']
        HL.walls(B, us, vs, ZF + 0.05, ZF + 2.55, {0: front, 1: 'board', 2: 'board', 3: 'board'}, r=0.15)
        HL.walls(B, us, vs, ZF + 2.75, zt - 0.15, {k: 'white' for k in range(4)}, r=0.15)
        for zz, hh in ((ZF + 2.65, 0.2), (zt, 0.28), (ZF + 0.15, 0.14)):
            arch.nageshi(B, Lh, Dh, zz, WD, h=hh, w=0.12, out=0.16) if False else None
        with Frame(B, AX, (vs[0] + vs[-1]) / 2, 0, 0):
            for zz, hh in ((ZF + 2.65, 0.2), (zt, 0.28), (ZF + 0.15, 0.14)):
                arch.nageshi(B, Lh, Dh, zz, WD, h=hh, w=0.12, out=0.16)
            top, reach = arch.bracket_row(B, Lh, Dh, zt, 'demitsudo', 0.7, WD, 'white_paint', us=us - AX, vs=vs - (vs[0] + vs[-1]) / 2)
        # 扁額
        prim.box(B, AX - 0.5, vs[0] - 0.24, ZF + 2.9, AX + 0.5, vs[0] - 0.16, ZF + 3.55, WD, tag='detail')
        # lower 入母屋 roof (桟瓦), ridge through the 伝衣閣
        with Frame(Bl, AX, (vs[0] + vs[-1]) / 2, 0, 0):
            o = 1.9; cc = Dh / 2 + reach + o
            R = jroof.Roof(Lh + 2 * reach, Dh + 2 * reach, 0.0, o, kind='irimoya', cover='sangawara', pitch=(ZF + 8.0 - (ZF + 4.1)) / cc, teri=1.35,
                           sori=0.45, sori_len=0.4, gable_frac=0.4, verge=0.8, edge=0.3, rafter=0.27, rafter_mat=WD, rafter_end='white_paint', tiers=1,
                           ends='oni', ridge_h=0.7, ridge_w=0.6, gable_wall='wood_dark')
            R.zE0 = ZF + 4.1
            R.build(Bl)
        # 伝衣閣: posts from the 昭堂 floor up through the roof, 腰組, balcony + railing, walls, brackets, 宝形 roof
        pu = np.array([-pw, -0.8, 0.8, pw]) + AX; pv = np.array([-pw, -0.8, 0.8, pw]) + (vs[0] + vs[-1]) / 2
        vm = (vs[0] + vs[-1]) / 2
        z2 = zbal + 2.25
        for x in pu:
            for y in (pv[0], pv[-1]):
                prim.box(B, x - 0.13, y - 0.13, ZF, x + 0.13, y + 0.13, z2, WD)
        for y in pv[1:-1]:
            for x in (pu[0], pu[-1]):
                prim.box(B, x - 0.13, y - 0.13, ZF, x + 0.13, y + 0.13, z2, WD)
        bo = 0.95
        with Frame(B, AX, vm, 0, 0):
            # 腰組 under the balcony
            for t in (-pw, -0.8, 0.8, pw):
                for sg in (-1, 1):
                    L.arm(B, (t, sg * pw, zbal - 0.45), (t, sg * (pw + bo - 0.05), zbal - 0.45), 0.14, 0.2, WD, 'white_paint')
                    L.arm(B, (sg * pw, t, zbal - 0.45), (sg * (pw + bo - 0.05), t, zbal - 0.45), 0.14, 0.2, WD, 'white_paint')
            prim.box(B, -pw - bo, -pw - bo, zbal - 0.3, pw + bo, pw + bo, zbal, 'wood_natural', faces='xXyYZz')
            prim.box(B, -pw - bo - 0.05, -pw - bo - 0.05, zbal - 0.55, pw + bo + 0.05, pw + bo + 0.05, zbal - 0.3, WD, faces='xXyY')
            K.rail_line(B, [(-pw - bo + 0.1, -pw - bo + 0.1), (pw + bo - 0.1, -pw - bo + 0.1), (pw + bo - 0.1, pw + bo - 0.1), (-pw - bo + 0.1, pw + bo - 0.1), (-pw - bo + 0.1, -pw - bo + 0.1)],
                        zbal, h=0.62, mat=WD, giboshi_at=(0, 1, 2, 3, 4), cap_mat='gold', post_every=1.2)
            p3 = np.array([-pw, -0.8, 0.8, pw])
            for k, (pts, o_) in enumerate(((([(x, -pw) for x in p3]), (0, -1)), (([(pw, y) for y in p3]), (1, 0)), (([(x, pw) for x in p3[::-1]]), (0, 1)), (([(-pw, y) for y in p3[::-1]]), (-1, 0)))):
                kinds = ['renji', 'shoji', 'renji'] if k == 0 else ['renji', 'board', 'renji']
                for i in range(3):
                    EK.infill(B, pts[i], pts[i + 1], zbal + 0.05, z2 - 0.4, kinds[i], out=o_, r=0.13)
                    EK.infill(B, pts[i], pts[i + 1], z2 - 0.35, z2 - 0.05, 'board', out=o_, r=0.13)
            arch.nageshi(B, 2 * pw, 2 * pw, z2, WD, h=0.24, w=0.16, out=0.0)
            top2, reach2 = arch.bracket_row(B, 2 * pw, 2 * pw, z2, 'demitsudo', 0.6, WD, 'white_paint', us=p3, vs=p3)
            R2 = jroof.Roof(2 * pw + 2 * reach2, 2 * pw + 2 * reach2, 0.0, 1.75, kind='hogyo', cover='hiwada', pitch=0.48, teri=1.7, sori=0.55, sori_len=0.45,
                            edge=0.42, rafter=0.24, rafter_mat=WD, rafter_end='white_paint', tiers=2, ends=None, hip=False, top=[(0.0, 0.0)])
            R2.zE0 = z2 + 0.5
            rr = R2.build(B)
            zr = rr['z_ridge']
            prim.box(B, -0.55, -0.55, zr - 0.25, 0.55, 0.55, zr + 0.45, 'copper')                 # 露盤
            prim.lathe(B, (0, 0, zr + 0.45), [(0.4, 0.0), (0.45, 0.08), (0.2, 0.18), (0.12, 0.25)], 12, 'copper')
            prim.lathe(B, (0, 0, zr + 0.7), [(0.0, 0.0), (0.22, 0.08), (0.3, 0.25), (0.25, 0.45), (0.12, 0.65), (0.0, 0.85)], 12, 'gold')   # 宝珠 (flaming jewel)
            for k in range(8):
                a = 2 * math.pi * k / 8
                prim.obox(B, (0.22 * math.cos(a), 0.22 * math.sin(a), zr + 0.85), (0.3 * math.cos(a), 0.3 * math.sin(a), zr + 1.25), 0.07, 0.04, 'gold', tag='detail')
            prim.cyl(B, (0, 0, zr + 1.4), (0, 0, zr + 2.0), 0.015, 0.01, 4, 'metal_dark', tag='detail')
        # the 開山堂 behind (a smaller 入母屋 hall)
        with Frame(B, -3.0, 16.0, 0, 0):
            us2 = HL.bays([2.6, 3.2, 3.2, 2.6]); vs2 = HL.bays([2.6, 3.0, 2.6])
            HL.pillars(B, us2, vs2, ZF + 0.3, ZF + 4.0, 0.16, round_=True)
            HL.walls(B, us2, vs2, ZF + 0.35, ZF + 3.8, {0: ['board', 'karado', 'karado', 'board'], 1: 'board', 2: 'board', 3: 'board'}, r=0.16)
            prim.box(B, us2[0] - 0.8, vs2[0] - 0.8, ZG - 0.3, us2[-1] + 0.8, vs2[-1] + 0.8, ZF + 0.3, 'stone')
            t3, r3 = arch.bracket_row(B, us2[-1] - us2[0], vs2[-1] - vs2[0], ZF + 4.0, 'degumi', 0.7, WD, 'white_paint', us=us2, vs=vs2)
            jroof.roof(B, us2[-1] - us2[0] + 2 * r3, vs2[-1] - vs2[0] + 2 * r3, t3 + 0.35, 1.8, kind='irimoya', cover='sangawara', pitch=0.7, sori=0.5,
                       rafter=0.27, rafter_mat=WD, rafter_end='white_paint', ends='oni', gable_wall='wood_dark')
            K.block_poly(B, [(us2[0], vs2[0]), (us2[-1], vs2[0]), (us2[-1], vs2[-1]), (us2[0], vs2[-1])])
        # a covered link from the 昭堂 to the 開山堂
        HL.pillars(B, np.array([-4.2, -1.8]), np.array([vs[-1] + 0.4, 11.6]), ZF, ZF + 2.8, 0.12, round_=False)
        with Frame(B, -3.0, (vs[-1] + 11.6) / 2 + 0.2, 0, math.pi / 2):
            jroof.roof(B, 11.6 - vs[-1] - 0.4, 2.4, ZF + 3.2, 0.8, kind='kirizuma', cover='sangawara', pitch=0.55, sori=0.0, verge=0.4, rafter=0.3,
                       rafter_mat=WD, rafter_end='white_paint', ends=None, gable_wall='wood_dark')
        HL.block_sides(B, us, vs)
    # the lower roof gives way to the 伝衣閣 above its balcony
    foot = Polygon([lc.w(AX + du, vm + dv) for (du, dv) in ((-pw - 0.9, -pw - 0.9), (pw + 0.9, -pw - 0.9), (pw + 0.9, pw + 0.9), (-pw - 0.9, pw + 0.9))])
    cull_region(Bl, foot, zbal - 0.35)
    K.merge_into(B, Bl)
    B.lamp(*lc.w(AX, vs[0] - 1.0), ZF + 3.3, 6.0)

def romon(B, S):
    """樓門: a two-storey gate with an 入母屋 roof, side wings with white walls and lattice windows"""
    lc = loc()
    cg = (AX, -38.1)
    zg = 53.75
    us = np.array([-2.8, -1.2, 1.2, 2.8]); vs = np.array([-1.8, 0.0, 1.8])
    with lc.frame(B):
        with Frame(B, cg[0], cg[1], 0, 0):
            prim.box(B, -3.6, -2.6, zg - 0.4, 3.6, 2.6, zg + 0.12, 'stone')
            L.poly_flat(B, [(-3.6, -2.6), (3.6, -2.6), (3.6, 2.6), (-3.6, 2.6)], zg + 0.12, 'stone', tag='walk')
            z1 = zg + 3.4
            for x in us:
                for y in vs:
                    prim.cyl(B, (x, y, zg + 0.05), (x, y, z1 + 0.3), 0.2, 0.19, 12, WD, caps=(False, True))
            for (x0, x1) in ((us[0], us[1]), (us[2], us[3])):
                EK.infill(B, (x0, 0), (x1, 0), zg + 0.15, z1 - 0.6, 'white', out=(0, -1), r=0.2)
            prim.obox(B, (-3.2, 0, z1 - 0.3), (3.2, 0, z1 - 0.3), 0.18, 0.36, WD)
            for y in (vs[0], vs[-1]):
                prim.obox(B, (-3.3, y, z1 - 0.1), (3.3, y, z1 - 0.1), 0.2, 0.4, WD)
            for x in us:
                prim.obox(B, (x, -2.2, z1 - 0.1), (x, 2.2, z1 - 0.1), 0.2, 0.4, WD)
            # 腰組 + balcony + railing
            zb = z1 + 0.85
            top0, reach0 = arch.bracket_row(B, 5.6, 3.6, z1 + 0.1, 'demitsudo', 0.6, WD, 'white_paint', us=us, vs=vs, purlin=False)
            prim.box(B, -3.5, -2.5, zb - 0.25, 3.5, 2.5, zb, 'wood_natural', faces='xXyYZz')
            K.rail_line(B, [(-3.4, -2.4), (3.4, -2.4), (3.4, 2.4), (-3.4, 2.4), (-3.4, -2.4)], zb, h=0.75, mat=WD, giboshi_at=(0, 1, 2, 3, 4), post_every=1.2)
            z2 = zb + 2.3
            for x in us:
                for y in (vs[0], vs[-1]):
                    prim.box(B, x - 0.15, y - 0.15, zb, x + 0.15, y + 0.15, z2, WD)
            for y in vs[1:-1]:
                for x in (us[0], us[-1]):
                    prim.box(B, x - 0.15, y - 0.15, zb, x + 0.15, y + 0.15, z2, WD)
            HL.walls(B, us, vs, zb + 0.05, z2 - 0.2, {0: ['board', 'karado', 'board'], 2: 'board', 1: 'board', 3: 'board'}, r=0.15)
            arch.nageshi(B, 5.6, 3.6, z2, WD, h=0.26, w=0.16, out=0.0)
            top, reach = arch.bracket_row(B, 5.6, 3.6, z2, 'demitsudo', 0.7, WD, 'white_paint', us=us, vs=vs)
            jroof.roof(B, 5.6 + 2 * reach, 3.6 + 2 * reach, top + 0.32, 1.75, kind='irimoya', cover='sangawara', pitch=0.78, sori=0.5, sori_len=0.4,
                       gable_frac=0.45, rafter=0.26, rafter_mat=WD, rafter_end='white_paint', tiers=2, ends='oni', gable_wall='wood_dark')
            # wings (white walls with lattice windows, tiled lean-to roofs)
            for sx in (-1, 1):
                x0, x1 = sorted((sx * 3.0, sx * 8.5))
                for y in (-1.1, 1.1):
                    for x in np.linspace(x0, x1, 4):
                        prim.box(B, x - 0.11, y - 0.11, zg, x + 0.11, y + 0.11, zg + 2.7, WD)
                EK.infill(B, (x0, -1.1), (x1, -1.1), zg + 0.1, zg + 1.0, 'white', out=(0, -1), r=0.1)
                EK.infill(B, (x0, -1.1), (x1, -1.1), zg + 1.0, zg + 2.0, 'koshi', out=(0, -1), r=0.1)
                EK.infill(B, (x0, -1.1), (x1, -1.1), zg + 2.0, zg + 2.6, 'white', out=(0, -1), r=0.1)
                EK.infill(B, (x0, 1.1), (x1, 1.1), zg + 0.1, zg + 2.6, 'white', out=(0, 1), r=0.1)
                with Frame(B, (x0 + x1) / 2, 0, 0, 0):
                    jroof.roof(B, x1 - x0, 2.2, zg + 3.0, 0.8, kind='kirizuma', cover='sangawara', pitch=0.55, sori=0.0, verge=0.35, rafter=0.3,
                               rafter_mat=WD, rafter_end='white_paint', ends=None, gable_wall='temple_wall')
                K.block_poly(B, [(x0, -1.2), (x1, -1.2), (x1, 1.2), (x0, 1.2)])
            for x in us:
                for y in vs:
                    K.block_poly(B, K.rect(x, y, 0.3, 0.3))
            K.block_line(B, [(us[0], 0), (us[1], 0)]); K.block_line(B, [(us[2], 0), (us[3], 0)])
            B.lamp(0, -2.0, zg + 2.6, 5.0)

def garden(B, S):
    """the 開山堂 garden: axis path, raked sand with moss squares to the west, pond + rocks + azaleas to the east"""
    lc = loc()
    rng = np.random.default_rng(41)
    with lc.frame(B):
        # axis path: stone slabs with cobble edges, from the 樓門 to the 昭堂 steps
        v0, v1 = -35.5, -9.5
        zz = lambda u, v: lc.g(S, u, v)
        for v in np.arange(v0, v1, 1.1):
            z = max(zz(AX, v), zz(AX, v + 1.1)) + 0.06
            prim.box(B, AX - 0.85, v + 0.02, z - 0.15, AX + 0.85, v + 1.08, z, 'stone', faces='xXyYZ', c1=(0, 3, int(rng.integers(255)), 0))
        for sg in (-1, 1):
            pts = np.array([(AX + sg * 1.2, v, zz(AX + sg * 1.2, v) + 0.04) for v in np.linspace(v0, v1, 14)])
            prim.sweep(B, pts, [(-0.35, -0.12), (0.35, -0.12), (0.35, 0.0), (-0.35, 0.0)], 'curb', closed=True)
        EK.ribbon(B, np.array([(AX, v, zz(AX, v) + 0.06) for v in np.linspace(v0 - 1.0, v1, 16)]), 2.6, 'walk')
        # west: raked sand with a checker of moss squares and a standing stone
        wz = max(zz(-6, -20), zz(-2.5, -9), zz(-9.5, -31)) + 0.05
        west = box(-10.0, -32.0, -2.4, -7.6)
        moss = []
        for i in range(4):
            for j in range(12):
                if (i + j) % 3 == 0 and rng.random() < 0.8:
                    x = -10.0 + i * 1.9; y = -32.0 + j * 2.0
                    moss.append(box(x + 0.1, y + 0.1, x + 1.8, y + 1.9))
        mossu = shapely.unary_union(moss).intersection(west) if moss else Polygon()
        from sites import tofukuji_garden as GD
        GD.flat_poly(B, west.difference(mossu), wz, 'sand_raked', uvfn=lambda V: np.c_[V[:, 1], V[:, 0]])
        GD.flat_poly(B, mossu, wz + 0.04, 'moss_mound')
        GD.kerb(B, west, wz)
        GD.gstone(B, -8.6, -10.2, wz, 0.75, 2.2, 501)
        GD.gstone(B, -7.4, -10.6, wz, 0.4, 0.6, 502, shape='round')
        K.block_poly(B, [(-10.0, -32.0), (-2.6, -32.0), (-2.6, -7.6), (-10.0, -7.6)])
        # east: the pond (OSM 897964330) with rocks, a slab bridge, the hillock
        pr = [lc.l(x, y) for (x, y) in L.osm_poly(S, 'water', 897964330)]
        pond = Polygon(pr).buffer(0.6)
        zw = min(zz(*p) for p in pr) - 0.55
        EK.water(B, pond, zw)
        # the pond bed and banks: a ring of stones round the edge, a dark bed under the water
        GD.flat_poly(B, pond.buffer(0.2), zw - 0.45, 'stone')
        ring = np.array(pond.exterior.coords)
        for i, p in enumerate(ring[:-1:2]):
            L.stone(B, (p[0], p[1], zw + 0.15), rng.uniform(0.35, 0.6), 600 + i, flat=0.7, sub=1, sink=0.3)
        # banks rising from the water to the ground
        bank = []
        for p in ring[:-1]:
            bank.append(p)
        EK.slab_bridge(B, S, (2.0, -21.5), (11.0, -21.0), zz(6.5, -21.2) + 0.05, w=1.1)
        L.poly_flat(B, list(ring[:-1]), 0.0, 'stone', tag='block')
        # the hillock: moss mounds with rocks and clipped azaleas, maples behind
        from sites import tofukuji_garden as GD2
        for (u, v, rx, ry, h, sd) in ((14.5, -12.0, 4.0, 3.2, 1.6, 1), (16.5, -19.5, 3.8, 3.5, 2.1, 2), (15.0, -27.0, 3.5, 3.0, 1.5, 3), (11.5, -16.0, 2.2, 2.0, 0.8, 4)):
            GD2.mound(B, u, v, rx, ry, h, zz(u, v), 700 + sd)
        for k in range(26):
            u = rng.uniform(9.5, 19.5); v = rng.uniform(-30.5, -9.0)
            if pond.buffer(0.8).contains(Point(u, v)): continue
            z = zz(u, v) + 0.4
            if rng.random() < 0.45:
                GD.gstone(B, u, v, z - 0.3, rng.uniform(0.4, 0.8), rng.uniform(0.7, 1.9), 800 + k, shape='stand' if rng.random() < 0.6 else 'round')
            else:
                B.tree('tsutsuji', u, v, z - 0.2, rng.uniform(1.0, 1.6), rng.uniform(0, 6.28))
        for k in range(14):
            u = rng.uniform(3.0, 9.5); v = rng.uniform(-32.0, -9.0)
            if pond.buffer(0.5).contains(Point(u, v)): continue
            B.tree('tsutsuji', u, v, zz(u, v), rng.uniform(0.9, 1.3), rng.uniform(0, 6.28))
        for (u, v) in ((20.0, -10.0), (21.0, -22.0), (19.0, -32.5), (-12.0, -12.0), (-12.5, -28.0)):
            B.tree('momiji', u, v, zz(u, v), rng.uniform(1.0, 1.35), rng.uniform(0, 6.28))
        B.tree('matsu', 7.5, -9.5, zz(7.5, -9.5), 0.8, 0.3)
        K.block_poly(B, [(2.6, -33.0), (21.0, -33.0), (21.0, -7.6), (2.6, -7.6)])
        # rope fences along the path
        for sg in (-1, 1):
            u = AX + sg * 1.75
            for v in np.arange(v0 + 0.5, v1, 2.2):
                prim.cyl(B, (u, v, zz(u, v) - 0.1), (u, v, zz(u, v) + 0.45), 0.04, 0.035, 6, WD, tag='detail')
    S.paint.append({'poly': [list(map(float, lc.w(u, v))) for (u, v) in ((-11, -34), (22, -34), (22, -6), (-11, -6))], 'surf': 'moss'})

def fumonin(B, S):
    """普門院 (客殿 + 庫裏, 重文): stands in for the generic PLATEAU block it shares with the 開山堂 — a plain 入母屋 客殿 and
    a 切妻 庫裏 west of the 開山堂 garden"""
    lc = loc()
    with lc.frame(B):
        for (cu, cv, Lw, Dw, kind, nu, nv) in ((-21.0, -14.0, 17.0, 11.0, 'irimoya', 7, 4), (-25.0, -26.5, 12.0, 6.5, 'kirizuma', 5, 3)):
            with Frame(B, cu, cv, 0, 0):
                zg = lc.g(S, cu, cv)
                zf = zg + 0.55
                us = np.linspace(-Lw / 2, Lw / 2, nu + 1); vs = np.linspace(-Dw / 2, Dw / 2, nv + 1)
                prim.box(B, -Lw / 2 - 0.9, -Dw / 2 - 0.9, zg - 0.3, Lw / 2 + 0.9, Dw / 2 + 0.9, zf, 'wood_dark', faces='xXyYZ')
                HL.pillars(B, us, vs, zf, zf + 3.0, 0.12, round_=False, base=False)
                HL.walls(B, us, vs, zf + 0.05, zf + 1.9, {0: 'maira', 1: 'maira', 2: 'board', 3: 'maira'}, r=0.12)
                HL.walls(B, us, vs, zf + 2.05, zf + 2.85, {k: 'white' for k in range(4)}, r=0.12)
                arch.nageshi(B, Lw, Dw, zf + 3.0, WD, h=0.24, w=0.14, out=0.0)
                jroof.roof(B, Lw, Dw, zf + 3.5, 1.5, kind=kind, cover='sangawara', pitch=0.72, sori=0.35 if kind == 'irimoya' else 0.0, verge=0.8,
                           rafter=0.3, rafter_mat=WD, rafter_end='white_paint', ends='oni', gable_wall='temple_wall')
                K.block_poly(B, [(-Lw / 2, -Dw / 2), (Lw / 2, -Dw / 2), (Lw / 2, Dw / 2), (-Lw / 2, Dw / 2)])

def build(B, S):
    shodo(B, S)
    romon(B, S)
    garden(B, S)
    fumonin(B, S)
