"""東福寺 三門 (国宝, 1425): 五間三戸二階二重門、入母屋造、本瓦葺、両山廊付 — the oldest and largest Zen 三門; 大仏様
structure (挿肘木 stacked out of the pillars, white-tipped), deep flat eaves with a strong corner upsweep, an upper
storey with a balcony and railing, props (太閤柱) under the roof corners; in front the 思遠池 (stone revetments, a
granite bridge on the axis) and clipped hedges.

Frame: the OSM outline's centre, main grid (u east, v north), front = v- (south).  Plan 25.6 x 10.5 m (bays 4.85 /
5.15 / 5.6 / 5.15 / 4.85; 5.25 / 5.25), eaves 5.1 m (OSM roof outline 35.8 x 21.0); heights from the corner props
in the side photo and PLATEAU (top 22.0 m): lower eave edge 9.2, balcony 11.6, upper eave edge 14.8, ridge 20.4."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString
import jk
from jk import prim, arch, Frame
from jk import roof as jroof
from sites import tofukuji_lib as L
from sites import tofukuji_klib as K
from sites import tofukuji_ekit as EK

C = (1366.0, -1120.6)
BAYS_U = [4.85, 5.15, 5.6, 5.15, 4.85]
BAYS_V = [5.25, 5.25]
ZG = 48.75
Z0 = ZG + 0.3          # floor of the gate
O = 5.1                # eaves beyond the pillar lines
WD = 'wood_dark'

def grid():
    us = np.r_[0, np.cumsum(BAYS_U)]; us -= us[-1] / 2
    vs = np.r_[0, np.cumsum(BAYS_V)]; vs -= vs[-1] / 2
    return us, vs

def build(B, S):
    loc = L.Loc(C[0], C[1], L.ROT)
    us, vs = grid()
    Lp, Dp = us[-1] - us[0], vs[-1] - vs[0]
    a, c = Lp / 2, Dp / 2
    out = dict(loc=loc)
    with loc.frame(B):
        # ---------------- platform (基壇), floor, walk
        pa, pc = a + 2.2, c + 2.2
        prim.box(B, -pa, -pc, ZG - 0.4, pa, pc, Z0, 'stone', c1=(0, 3, 0, 0))
        L.poly_flat(B, [(-pa, -pc), (pa, -pc), (pa, pc), (-pa, pc)], Z0, 'stone', tag='walk')
        # ---------------- lower storey: pillars, tie beams, walls, doors
        zh = Z0 + 7.0                      # pillar head (頭貫)
        for x in us:
            for y in vs:
                prim.cyl(B, (x, y, Z0 - 0.05), (x, y, Z0 + 0.35), 0.66, 0.6, 12, 'stone')
                prim.cyl(B, (x, y, Z0 + 0.3), (x, y, zh + 0.15), 0.43, 0.41, 16, WD, caps=(False, True))
        for (zz, hh, ww) in ((zh - 0.18, 0.42, 0.26), (Z0 + 4.55, 0.36, 0.2)):     # 頭貫, 飛貫 (through all pillar lines)
            for y in vs:
                prim.obox(B, (us[0] - 0.75, y, zz), (us[-1] + 0.75, y, zz), ww, hh, WD)
                for sx in (-1, 1):                                                        # 木鼻 (white ends)
                    xe = sx * (a + 0.75)
                    prim.obox(B, (xe - sx * 0.04, y, zz), (xe + sx * 0.02, y, zz), ww + 0.01, hh + 0.01, 'white_paint', tag='detail')
            for x in us:
                prim.obox(B, (x, vs[0] - 0.75, zz), (x, vs[-1] + 0.75, zz), ww, hh, WD)
                for sy in (-1, 1):
                    ye = sy * (c + 0.75)
                    prim.obox(B, (x, ye - sy * 0.04, zz), (x, ye + sy * 0.02, zz), ww + 0.01, hh + 0.01, 'white_paint', tag='detail')
        # walls: the outer bays on the middle line, the two end walls; white plaster with a dark 腰 rail
        def wall(p0, p1, out_):
            EK.infill(B, p0, p1, Z0 + 0.35, Z0 + 4.35, 'white', out=out_, r=0.45)
            EK.infill(B, p0, p1, Z0 + 4.75, zh - 0.4, 'white', out=out_, r=0.45)
            p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
            prim.obox(B, np.r_[p0, Z0 + 1.05], np.r_[p1, Z0 + 1.05], 0.16, 0.2, WD)
            prim.obox(B, np.r_[p0, Z0 + 0.3], np.r_[p1, Z0 + 0.3], 0.3, 0.2, WD)
        for (x0, x1) in ((us[0], us[1]), (us[-2], us[-1])):
            wall((x0, 0.0), (x1, 0.0), (0, -1))
        for sx in (-1, 1):
            for (y0, y1) in ((vs[0], vs[1]), (vs[1], vs[2])):
                wall((sx * a, y0), (sx * a, y1), (sx, 0))
        # 三戸: door frames on the middle line, leaves open against the jambs, thresholds
        for (x0, x1) in zip(us[1:4], us[2:5]):
            w = x1 - x0
            prim.obox(B, (x0, 0, Z0 + 0.12), (x1, 0, Z0 + 0.12), 0.3, 0.24, WD)
            prim.obox(B, (x0, 0, Z0 + 5.6), (x1, 0, Z0 + 5.6), 0.28, 0.4, WD)
            for sx, xa in ((1, x0 + 0.45), (-1, x1 - 0.45)):
                prim.box(B, min(xa, xa + sx * 0.1), 0.05, Z0 + 0.25, max(xa, xa + sx * 0.1), 0.05 + w / 2 - 0.5, Z0 + 5.35, WD)
            EK.infill(B, (x0, 0), (x1, 0), Z0 + 5.8, zh - 0.4, 'white', out=(0, -1), r=0.45)
        # a board ceiling over the passage
        prim.box(B, -a, -c, zh + 0.05, a, c, zh + 0.15, 'wood_dark', faces='z')
        # ---------------- lower brackets (挿肘木), purlins, the lower ring roof
        z_st = zh - 0.25
        top1, reach1 = L.stack_row(B, us, vs, z_st, tiers=5, step_out=0.5, step_up=0.5, mat=WD, end_mat='white_paint', r=0.43)
        zE_lo = Z0 + 9.2
        rise_lo = 2.35
        R1 = L.RingRoof(Lp, Dp, 0.0, O, truncate=5.35, rise=rise_lo, cover='hongawara', sori=0.5, sori_len=0.4, edge=0.36, rafter=0.27,
                        rafter_mat=WD, rafter_end='white_paint', tiers=2, ends='oni')
        R1.zE0 = zE_lo
        R1.build(B)
        # soffit between the bracket tops and the wall (小天井)
        K.soffit_ring(B, 0, 0, a, c, reach1 + 0.1, top1 + 0.1, 'wood_dark')
        out['R1'] = R1
        # ---------------- upper storey: balcony on 腰組, railing, pillars, walls
        ZU = Z0 + 11.6
        bo = 1.45                                     # balcony beyond the pillar lines
        for x in us:
            for y in vs:
                if x in (us[0], us[-1]) or y in (vs[0], vs[-1]):
                    prim.cyl(B, (x, y, float(R1.z(O, O)) - 0.3), (x, y, ZU + 2.95), 0.34, 0.32, 14, WD, caps=(False, True))
        # 腰組: short arms under the balcony edge at each pillar and mid-bay
        for x in list(us) + [((us[i] + us[i + 1]) / 2) for i in range(len(us) - 1)]:
            for sy in (-1, 1):
                L.arm(B, (x, sy * c, ZU - 0.55), (x, sy * (c + bo - 0.1), ZU - 0.55), 0.18, 0.24, WD, 'white_paint')
                L.masu(B, (x, sy * (c + bo - 0.3), ZU - 0.43), 0.26, WD)
        for y in list(vs) + [((vs[i] + vs[i + 1]) / 2) for i in range(len(vs) - 1)]:
            for sx in (-1, 1):
                L.arm(B, (sx * a, y, ZU - 0.55), (sx * (a + bo - 0.1), y, ZU - 0.55), 0.18, 0.24, WD, 'white_paint')
                L.masu(B, (sx * (a + bo - 0.3), y, ZU - 0.43), 0.26, WD)
        rng = np.random.default_rng(2)
        ab, cb = a + bo, c + bo
        prim.box(B, -ab, -cb, ZU - 0.32, ab, cb, ZU - 0.12, WD, faces='xXyYz')
        for x in np.arange(-ab, ab - 1e-6, 0.3):
            for (y0, y1) in ((-cb, -c + 0.3), (c - 0.3, cb)):
                prim.box(B, x + 0.005, y0, ZU - 0.12, min(x + 0.3, ab) - 0.005, y1, ZU, 'wood_natural', faces='Z', c1=(0, 0, int(rng.integers(255)), 0))
        for (x0, x1) in ((-ab, -a + 0.3), (a - 0.3, ab)):
            prim.box(B, x0, -c + 0.3, ZU - 0.12, x1, c - 0.3, ZU, 'wood_natural', faces='Z')
        prim.box(B, -a, -c, ZU - 0.1, a, c, ZU, 'wood_dark', faces='Z')
        K.rail_line(B, [(-ab + 0.15, -cb + 0.15), (ab - 0.15, -cb + 0.15), (ab - 0.15, cb - 0.15), (-ab + 0.15, cb - 0.15), (-ab + 0.15, -cb + 0.15)], ZU,
                    h=0.92, mat='wood_natural', post_mat='wood_natural', giboshi_at=(0, 1, 2, 3, 4), cap_mat='wood_natural', post_every=1.6)
        # upper walls: 桟唐戸 in the central three bays (front and back), boards and 花頭窓 elsewhere
        zu1 = ZU + 2.95
        for sy, k in ((-1, 0), (1, 2)):
            for i, (x0, x1) in enumerate(zip(us[:-1], us[1:])):
                kind = 'karado' if 1 <= i <= 3 else 'board'
                p0, p1 = ((x0, sy * c), (x1, sy * c))
                EK.infill(B, p0, p1, ZU + 0.05, zu1 - 0.55, kind, out=(0, sy), r=0.36)
                EK.infill(B, p0, p1, zu1 - 0.5, zu1 - 0.05, 'board', out=(0, sy), r=0.36)
        for sx in (-1, 1):
            for (y0, y1) in ((vs[0], vs[1]), (vs[1], vs[2])):
                EK.infill(B, (sx * a, y0), (sx * a, y1), ZU + 0.05, zu1 - 0.55, 'board', out=(sx, 0), r=0.36)
                EK.infill(B, (sx * a, y0), (sx * a, y1), zu1 - 0.5, zu1 - 0.05, 'board', out=(sx, 0), r=0.36)
        for (zz, hh) in ((zu1 - 0.12, 0.3), (ZU + 0.1, 0.22)):
            arch.nageshi(B, Lp, Dp, zz, WD, h=hh, w=0.2, out=0.2)
        # ---------------- upper brackets and the upper 入母屋 roof
        top2, reach2 = L.stack_row(B, us, vs, zu1 - 0.2, tiers=4, step_out=0.5, step_up=0.45, mat=WD, end_mat='white_paint', r=0.34)
        K.soffit_ring(B, 0, 0, a, c, reach2 + 0.1, top2 + 0.1, 'wood_dark')
        zE_up = Z0 + 14.8; zR = Z0 + 20.4
        cc = c + O
        R2 = jroof.Roof(Lp, Dp, 0.0, O, kind='irimoya', cover='hongawara', pitch=(zR - zE_up) / cc, teri=1.55, sori=0.85, sori_len=0.42,
                        gable_frac=0.5, verge=0.9, edge=0.38, rafter=0.27, rafter_mat=WD, rafter_end='white_paint', tiers=2, ends='oni',
                        ridge_h=0.95, ridge_w=0.9, bargeboard_mat=WD, gable_wall='wood_dark')
        R2.zE0 = zE_up
        out.update(R2.build(B))
        out['R2'] = R2
        # 懸魚 (a big one) on both gables
        u_g = R2.a - R2.sg + R2.verge
        for su in (-1, 1):
            za = float(R2.z(R2.c, R2.c)) - 0.9
            P = np.array([(su * (u_g + 0.08), y, za + z) for (y, z) in ((-0.9, 0.3), (0.9, 0.3), (0.75, -0.5), (0.3, -1.1), (0.0, -1.3), (-0.3, -1.1), (-0.75, -0.5))])
            I = [[0, i, i + 1] for i in range(1, len(P) - 1)]
            L.oadd(B, P, I, 'white_paint', (su, 0, 0), tag='detail')
        # ---------------- props (太閤柱) under the corners of both roofs
        for sx in (-1, 1):
            for sy in (-1, 1):
                for (R, zbase, frac) in ((R1, ZG, 0.78), (R2, None, 0.7)):
                    d_ = O * frac
                    px, py = sx * (a + d_), sy * (c + d_)
                    s_in = O - d_
                    ztop_ = float(R.z(s_in, s_in)) - R.edge - 0.55
                    if zbase is None:
                        zbase = float(R1.z(O - d_ * 0.8, O - d_ * 0.8))
                    prim.box(B, px - 0.17, py - 0.17, zbase - 0.05, px + 0.17, py + 0.17, ztop_, WD)
                    if R is R1: prim.box(B, px - 0.3, py - 0.3, ZG - 0.2, px + 0.3, py + 0.3, ZG + 0.25, 'stone')
        # ---------------- 山廊 (stair houses) at both ends, gables outward
        for sx in (-1, 1):
            cx = sx * 20.3
            with Frame(B, cx, 0.4, 0, 0):
                hw_, hd_ = 1.8, 2.3
                zt_ = ZG + 4.6
                for x in (-hw_, hw_):
                    for y in (-hd_, hd_):
                        prim.box(B, x - 0.14, y - 0.14, ZG, x + 0.14, y + 0.14, zt_, WD)
                for (p0, p1, o_) in (((-hw_, -hd_), (hw_, -hd_), (0, -1)), ((-hw_, hd_), (hw_, hd_), (0, 1)), ((sx * hw_, -hd_), (sx * hw_, hd_), (sx, 0))):
                    EK.infill(B, p0, p1, ZG + 0.1, zt_ - 0.25, 'board', out=o_, r=0.15)
                # the stair inside, seen through the open inner side
                prim.obox(B, (-sx * 1.5, 0, ZG + 0.4), (sx * 1.2, 0, zt_ - 0.4), 1.2, 0.2, 'wood_natural', tag='detail')
                arch.nageshi(B, 2 * hw_, 2 * hd_, zt_ - 0.15, WD, h=0.24, w=0.14, out=0.05)
                roof_l = 2 * hw_ + 0.0
                with Frame(B, 0, 0, 0, 0):
                    jroof.Roof(roof_l, 2 * hd_, zt_ + 0.45, 0.85, kind='kirizuma', cover='hongawara', pitch=0.62, verge=0.7, rafter=0.26, rafter_mat=WD,
                               rafter_end='white_paint', gable_wall='wood_dark', ends='oni', sori=0.0, edge=0.26).build(B)
                K.block_poly(B, [(-hw_, -hd_), (hw_, -hd_), (hw_, hd_), (-hw_, hd_)])
        # ---------------- blockers: pillars, walls; the central three bays stay open
        for x in us:
            for y in vs:
                K.block_poly(B, K.rect(x, y, 0.5, 0.5))
        K.block_line(B, [(us[0], 0), (us[1], 0)]); K.block_line(B, [(us[-2], 0), (us[-1], 0)])
        for sx in (-1, 1):
            K.block_line(B, [(sx * a, vs[0]), (sx * a, vs[-1])])
        # lanterns (石灯籠) on the axis in front of the gate
        for sx in (-1, 1):
            EK.lantern(B, sx * 7.0, -c - 6.0, ZG, h=2.4)
    return out

# ====================================================================== 思遠池
POND_LEVEL = 47.75

def pond(B, S):
    ring = L.osm_poly(S, 'water', 775829465)
    wp = Polygon(ring).buffer(0)
    cutp = wp.buffer(1.0, join_style=2)
    EK.basin(B, S, [(wp, POND_LEVEL)], cutp, res=0.75, depth=0.8, bank_surf='moss')
    S.cut.append([list(map(float, p)) for p in cutp.exterior.coords])
    EK.water(B, wp, POND_LEVEL)
    # stone revetment (石積) all round: battered face from under the water to the bank top
    ext = np.array(wp.exterior.coords)
    if Polygon(ext).exterior.is_ccw: ext = ext[::-1]      # clockwise: the right of travel (the face) is the water side
    K.ishigaki(B, list(ext), lambda x, y: float(S.ground(x, y)) - 0.05, POND_LEVEL - 0.6, batter=0.18, seed=3, cap=True)
    # granite bridge across the neck, on the 三門 axis path
    EK.stone_bridge(B, S, (1364.55, -1159.2), (1364.75, -1148.6), float(S.ground(1364.55, -1159.2)) + 0.05, float(S.ground(1364.75, -1148.6)) + 0.05,
                    w=3.2, arch_h=0.35, piers=(0.3, 0.7), z_water=POND_LEVEL, post_step=1.5)
    # lotus / reeds: clumps of dry stalks in the water (thin sticks)
    rng = np.random.default_rng(12)
    inner = wp.buffer(-1.2)
    x0, y0, x1, y1 = wp.bounds
    n = 0
    while n < 70:
        x = rng.uniform(x0, x1); y = rng.uniform(y0, y1)
        if not inner.contains(shapely.geometry.Point(x, y)) or abs(x - 1364.6) < 3.0: continue
        n += 1
        for k in range(5):
            dx, dy = rng.normal(0, 0.18, 2)
            h = rng.uniform(0.5, 1.1)
            prim.obox(B, (x + dx, y + dy, POND_LEVEL - 0.05), (x + dx * 1.6, y + dy * 1.6, POND_LEVEL + h), 0.02, 0.02, 'wood_natural', tag='detail')
    # the water blocks walkers
    L.poly_flat(B, np.array(wp.exterior.coords)[:-1], 0.0, 'stone', tag='block')
    # hedges round the pond (OSM 775829462 / 775829463)
    for hid in (775829462, 775829463):
        try: line = L.osm_line(S, hid)
        except KeyError: continue
        arch.hedge(B, line, 0, h=1.15, w=0.75, ground=S.ground)
        EK.ribbon(B, line, 0.8, 'block')
    return wp
