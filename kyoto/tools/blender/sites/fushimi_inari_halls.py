"""伏見稲荷大社: the halls of the lower precinct and the shrines on the way up.

All face west along the ceremonial axis (bearing ~086°: 一ノ鳥居 → 二ノ鳥居 → 楼門 → 外拝殿 → 内拝殿 → 本殿).  Built in each
footprint's frame (OSM rectangles: u along the front, +v toward the back (east), the front at -v), heights from PLATEAU.
Vermilion (丹塗り) frames, white (胡粉) plaster panels, gilt fittings, 檜皮葺 roofs (copper for the 内拝殿 and its 唐破風).
Custom roofs here: 流造 (the 本殿, 権殿, 奥宮: a gable roof whose front slope runs on over the porch) and 唐破風."""
import math
import numpy as np
import jk
from jk import prim, arch, roof, Frame
from . import fushimi_inari_torii as FT
from .fushimi_inari_kit import kumimono, bracket_row

# ------------------------------------------------------------------ frames
def rect_frame(S, oid, back=(1.0, 0.0)):
    """(cx, cy, Lu, Dv, theta): the footprint's rectangle with +v pointing to `back` (world direction)"""
    b = S.osm_building(oid)
    cx, cy, L, W, yaw = S.rect(b['poly'][0])
    best = None
    for k in range(4):
        th = yaw + k * math.pi / 2
        d = -math.sin(th) * back[0] + math.cos(th) * back[1]
        if best is None or d > best[0]: best = (d, th, k)
    _, th, k = best
    Lu, Dv = (L, W) if k % 2 == 0 else (W, L)
    return cx, cy, Lu, Dv, math.atan2(math.sin(th), math.cos(th))

def world_ring(cx, cy, th, pts):
    c, s = math.cos(th), math.sin(th)
    return [[cx + u * c - v * s, cy + u * s + v * c] for (u, v) in pts]

def rect_pts(u0, v0, u1, v1):
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]

# ------------------------------------------------------------------ members
def ring_pillars(B, us, vs, z0, z1, r, mat='vermilion', base=True, inner=False):
    pts = set()
    for x in us:
        for y in (vs[0], vs[-1]): pts.add((round(x, 3), round(y, 3)))
    for y in vs:
        for x in (us[0], us[-1]): pts.add((round(x, 3), round(y, 3)))
    if inner:
        for x in us:
            for y in vs: pts.add((round(x, 3), round(y, 3)))
    for (x, y) in sorted(pts):
        arch.pillar(B, x, y, z0, z1, r, mat, base=base)
    return sorted(pts)

def bays(us, vs):
    """the outer bays: (p0, p1, side) with side 0 front (v-), 1 right (u+), 2 back (v+), 3 left (u-); walls run so
    that the right of p0->p1 is outside"""
    out = []
    for i in range(len(us) - 1): out.append(((us[i], vs[0]), (us[i + 1], vs[0]), 0))
    for j in range(len(vs) - 1): out.append(((us[-1], vs[j]), (us[-1], vs[j + 1]), 1))
    for i in range(len(us) - 1, 0, -1): out.append(((us[i], vs[-1]), (us[i - 1], vs[-1]), 2))
    for j in range(len(vs) - 1, 0, -1): out.append(((us[0], vs[j]), (us[0], vs[j - 1]), 3))
    return out

def gold_caps(B, pts, z, r=0.07, h=0.04):
    for (x, y) in pts:
        prim.cyl(B, (x, y, z - h), (x, y, z + h), r, r, 8, 'gold', tag='detail')

def plaque(B, u, v, z, w, h, face=-1, ground='black_lacquer', frame='gold', tag='detail'):
    """a shrine plaque (扁額): a board in a gilt frame facing -v (face=-1)"""
    d = 0.06
    prim.box(B, u - w / 2, v - d / 2, z - h / 2, u + w / 2, v + d / 2, z + h / 2, frame, tag=tag)
    y = v - d / 2 - 0.005 if face < 0 else v + d / 2 + 0.005
    prim.box(B, u - w * 0.4, y - 0.004, z - h * 0.42, u + w * 0.4, y + 0.004, z + h * 0.42, ground, tag=tag, faces='y' if face < 0 else 'Y')

def hanging_lantern(B, x, y, z, s=1.0, mat='metal_dark', lamp=True):
    """釣灯籠: a hexagonal metal lantern on a short chain, lit"""
    prim.cyl(B, (x, y, z), (x, y, z - 0.25 * s), 0.012, 0.012, 4, mat, tag='detail')
    zt = z - 0.25 * s
    prim.lathe(B, (x, y, zt - 0.62 * s), [(0.12 * s, 0.0), (0.2 * s, 0.06 * s), (0.2 * s, 0.4 * s), (0.27 * s, 0.44 * s), (0.08 * s, 0.6 * s), (0.04 * s, 0.62 * s)], 6, mat, smooth=False)
    prim.cyl(B, (x, y, zt - 0.56 * s), (x, y, zt - 0.24 * s), 0.205 * s, 0.205 * s, 6, 'lantern_paper', caps=(False, False), tag='detail')
    if lamp: B.lamp(x, y, zt - 0.4 * s, 6.0, (1.0, 0.6, 0.3))

# ------------------------------------------------------------------ custom roofs
def nagare_roof(B, L, vb, vr, vf, zb, zr, zf, verge=0.9, cover='hiwada', th=0.34, teri=1.35, rafters=(0.0, 0.0), rafter_mat='vermilion',
                end_mat='gold', barge='vermilion', ridge_mat='copper', core=None, z_wall=None, gable=True, gegyo=True):
    """流造: ridge along u at v = vr (height zr), the back slope down to the edge at v = vb (zb), the long front slope over
    the porch down to v = vf (zf).  core = (v_front, v_back) of the walled 身舎 for the gable walls (妻壁) from z_wall up."""
    mat = roof.COVER_MAT[cover]
    ua = L / 2 + verge
    def zf_(v):
        v = np.asarray(v, float)
        tb = np.clip((vb - v) / (vb - vr), 0, 1); tf = np.clip((v - vf) / (vr - vf), 0, 1)
        return np.where(v >= vr, zb + (zr - zb) * tb ** teri, zf + (zr - zf) * tf ** teri)
    nu = max(6, int(2 * ua / 0.7))
    for (v0, v1, nv) in ((vr, vb, 7), (vf, vr, 11)):
        flip = v0 == vr
        prim.grid_surface(B, lambda u, v: (u, v, float(zf_(v))), -ua, ua, v0, v1, nu, nv, mat, flip=not flip)
        prim.grid_surface(B, lambda u, v: (u, v, float(zf_(v)) - th), -ua, ua, v0, v1, nu, nv, 'eave_wood', flip=flip)
    # eave edges: cover on top, fascia below
    for (ve, ze, sg) in ((vf, zf, -1), (vb, zb, 1)):
        P = np.array([(-ua, ve, ze), (ua, ve, ze), (ua, ve, ze - th * 0.5), (-ua, ve, ze - th * 0.5), (-ua, ve, ze - th), (ua, ve, ze - th)])
        I = [[0, 1, 2], [0, 2, 3]] if sg > 0 else [[0, 2, 1], [0, 3, 2]]
        B.add(P[:4], I, mat)
        I2 = [[3, 2, 5], [3, 5, 4]] if sg > 0 else [[3, 5, 2], [3, 4, 5]]
        B.add(P, I2, 'eave_wood', c1=(0, 1, 0, 0))
    # verge edges + 破風 (bargeboards) on both gable ends
    vs = np.concatenate([np.linspace(vf, vr, 12), np.linspace(vr, vb, 8)[1:]])
    for sg in (-1, 1):
        x = sg * ua
        top = np.array([(x, v, float(zf_(v))) for v in vs]); bot = top - [0, 0, th]
        V = np.concatenate([top, bot]); n = len(vs); I = []
        for i in range(n - 1):
            I += [[i, i + 1, n + i + 1], [i, n + i + 1, n + i]] if sg > 0 else [[i, n + i + 1, i + 1], [i, n + i, n + i + 1]]
        B.add(V, I, mat)
        bb = np.array([(x - sg * 0.04, v, float(zf_(v)) - th * 0.8) for v in vs])
        prim.sweep(B, bb, [(-0.05, 0.0), (0.05, 0.0), (0.05, -0.38), (-0.05, -0.38)], barge, up=(0, 0, 1), caps=True)
        # gilt fittings on the bargeboard (飾り金具): a few plates
        for v in (vf + 0.3, (vf + vr) / 2, vr, (vr + vb) / 2, vb - 0.25):
            zz = float(zf_(v)) - th * 0.8 - 0.19
            prim.box(B, x - sg * 0.1 - 0.02, v - 0.16, zz - 0.13, x - sg * 0.1 + 0.02, v + 0.16, zz + 0.13, 'gold', tag='detail')
    # ridge (箱棟) with gilt end caps
    rh = min(0.32, 0.12 + L * 0.02)
    prim.box(B, -ua + 0.1, vr - 0.2, zr - 0.15, ua - 0.1, vr + 0.2, zr + rh, ridge_mat, faces='xXyYZ')
    prim.box(B, -ua + 0.02, vr - 0.25, zr + rh - 0.02, ua - 0.02, vr + 0.25, zr + rh + 0.08, ridge_mat)
    for sg in (-1, 1):
        prim.box(B, sg * (ua - 0.03) - 0.1, vr - 0.26, zr - 0.05, sg * (ua - 0.03) + 0.1, vr + 0.26, zr + rh + 0.1, 'gold', tag='detail')
        # 鬼板: a dark plate at each end, gilt boss
        prim.box(B, sg * (ua + 0.02) - 0.04, vr - 0.32, zr - 0.2, sg * (ua + 0.02) + 0.04, vr + 0.32, zr + rh + 0.3, 'copper')
        prim.cyl(B, (sg * (ua + 0.07), vr, zr + rh * 0.5), (sg * (ua + 0.1), vr, zr + rh * 0.5), 0.12, 0.12, 8, 'gold', tag='detail')
    # rafters under the front eave (地垂木), vermilion with gilt ends
    if rafters[1] > 0:
        v_in = rafters[0]
        for x in np.arange(-L / 2 - verge + 0.25, L / 2 + verge - 0.1, rafters[1]):
            p0 = (x, vf + 0.05, float(zf_(vf + 0.05)) - th - 0.06); p1 = (x, v_in, float(zf_(v_in)) - th - 0.06)
            prim.obox(B, p0, p1, 0.09, 0.1, rafter_mat, tag='detail')
            prim.obox(B, (x, vf + 0.02, p0[2]), (x, vf + 0.06, p0[2] + (p1[2] - p0[2]) * 0.01), 0.095, 0.105, end_mat, tag='detail')
    # gable walls (妻壁): white plaster with painted posts / tie beams, up to the roof underside, and a gilt 懸魚
    if gable and core is not None and z_wall is not None:
        cf, cb = core
        for sg in (-1, 1):
            x = sg * L / 2
            vv = np.linspace(cf, cb, 10)
            top = [(x, v, float(zf_(v)) - th - 0.03) for v in vv]
            poly = [(x, cb, z_wall), (x, cf, z_wall)] + top
            P = np.array(poly); cen = P.mean(0)
            Pall = np.concatenate([[cen], P]); n = len(P)
            I = [[0, 1 + j, 1 + (j + 1) % n] for j in range(n)]
            fn = np.cross(Pall[I[0][1]] - Pall[0], Pall[I[0][2]] - Pall[0])
            if fn[0] * sg < 0: I = [t[::-1] for t in I]
            B.add(Pall, I, 'temple_wall', UV=np.c_[Pall[:, 1], Pall[:, 2]], c0=(238, 234, 224, 35), c1=(0, 4, 0, 0))
            # vermilion frame members on the gable: tie beam (虹梁) and a king post (束)
            prim.obox(B, (x + sg * 0.03, cf, z_wall + 0.15), (x + sg * 0.03, cb, z_wall + 0.15), 0.16, 0.3, 'vermilion')
            zc = float(zf_(vr)) - th
            prim.obox(B, (x + sg * 0.03, vr, z_wall + 0.3), (x + sg * 0.03, vr, zc), 0.16, 0.18, 'vermilion')
            if gegyo:
                zg = float(zf_(vr)) - th - 0.35
                prim.lathe(B, (sg * (ua - 0.12), vr, zg - 0.5), [(0.0, 0.0), (0.18, 0.08), (0.32, 0.3), (0.3, 0.45), (0.0, 0.55)], 8, 'gold', tag='detail', smooth=False)
    return zf_

def karahafu(B, w, v0, v1, z_end, z_crest, th=0.32, cover='copper', board='black_lacquer', under='vermilion', depth_drop=0.0, tymp=None):
    """唐破風: a cusped gable across u (front edge at v = v0, running back to v1 > v0): convex in the middle, concave
    toward the ends; a thick dark bargeboard on the front edge with gilt ornaments (兎毛通, 鰭)"""
    mat = roof.COVER_MAT[cover]
    T = np.array([0.0, 0.2, 0.4, 0.55, 0.68, 0.8, 0.9, 0.97, 1.0, 1.04])
    F = np.array([1.0, 0.975, 0.9, 0.78, 0.58, 0.36, 0.18, 0.07, 0.035, 0.07])
    hw = w / 2
    def zu(u):
        return z_end + (z_crest - z_end) * np.interp(abs(u) / hw, T, F)
    us = np.concatenate([-hw * T[::-1], hw * T[1:]])
    vs = np.linspace(v0, v1, 6)
    P = np.array([(u, v, zu(u) - depth_drop * (v1 - v) / (v1 - v0)) for v in vs for u in us])
    nu = len(us); nv = len(vs)
    I = []
    for j in range(nv - 1):
        for i in range(nu - 1):
            a = j * nu + i
            I += [[a, a + nu + 1, a + 1], [a, a + nu, a + nu + 1]]
    B.add(P, I, mat, smooth=True)
    Pu = P - [0, 0, th]
    B.add(Pu, [t[::-1] for t in I], 'vermilion', smooth=True)
    # the front bargeboard (唐破風板) following the curve; vermilion under-band; gilt crest ornament
    edge = np.array([(u, v0 - 0.04, zu(u) - depth_drop) for u in us])
    prim.sweep(B, edge, [(-0.06, 0.06), (0.06, 0.06), (0.06, -0.42), (-0.06, -0.42)], board, up=(0, 1, 0), caps=True)
    prim.sweep(B, edge - [0, -0.02, 0.42], [(-0.05, 0.0), (0.05, 0.0), (0.05, -0.12), (-0.05, -0.12)], 'white_paint', up=(0, 1, 0), tag='detail')
    zc = z_crest - depth_drop
    prim.lathe(B, (0, v0 - 0.12, zc - 1.25), [(0.0, 0.0), (0.25, 0.15), (0.42, 0.5), (0.36, 0.8), (0.0, 0.9)], 10, 'gold', tag='detail', smooth=False)
    for sg in (-1, 1):
        prim.box(B, sg * hw * 0.7 - 0.3, v0 - 0.12, zu(hw * 0.7) - 0.75, sg * hw * 0.7 + 0.3, v0 - 0.08, zu(hw * 0.7) - 0.3, 'gold', tag='detail')
    # the roof's ridge cap along the crest (copper)
    prim.obox(B, (0, v0, z_crest + 0.02), (0, v1, z_crest + 0.02), 0.3, 0.12, mat)
    if tymp is not None:
        # the gable face (妻) under the board between the porch pillars: white, a vermilion frame, carvings (gilt / green)
        wb, zbm = tymp
        uu = np.linspace(-wb / 2, wb / 2, 15)
        P = []
        for u in uu: P += [(u, v0 + 0.06, zbm), (u, v0 + 0.06, zu(u) - depth_drop - 0.44)]
        I = []
        for i in range(len(uu) - 1):
            a = 2 * i
            I += [[a, a + 2, a + 3], [a, a + 3, a + 1]]
        P = np.array(P)
        B.add(P, I, 'temple_wall', UV=np.c_[P[:, 0], P[:, 2]], c0=(240, 236, 228, 35))
        prim.sweep(B, np.array([(u, v0 + 0.02, zu(u) - depth_drop - 0.5) for u in uu]), [(-0.05, 0.06), (0.05, 0.06), (0.05, -0.06), (-0.05, -0.06)], 'vermilion', up=(0, 1, 0), tag='detail')
        zm = (zbm + zu(0) - depth_drop - 0.44) / 2
        prim.box(B, -0.12, v0 - 0.02, zbm, 0.12, v0 + 0.06, zu(0) - depth_drop - 0.44, 'vermilion')
        for sg in (-1, 1):
            prim.lathe(B, (sg * 0.75, v0 + 0.02, zm - 0.35), [(0.0, 0.0), (0.42, 0.1), (0.55, 0.35), (0.4, 0.6), (0.0, 0.7)], 8, 'copper', tag='detail', smooth=False)
            prim.lathe(B, (sg * 0.75, v0 - 0.05, zm - 0.1), [(0.0, 0.0), (0.18, 0.05), (0.2, 0.2), (0.0, 0.3)], 8, 'gold', tag='detail', smooth=False)
        prim.lathe(B, (0.0, v0 - 0.06, zm - 0.2), [(0.0, 0.0), (0.2, 0.05), (0.24, 0.25), (0.0, 0.4)], 8, 'gold', tag='detail', smooth=False)
    return zu

# ------------------------------------------------------------------ the halls
def romon(B, S, ex):
    """楼門 (1589, 三間一戸 two-storey gate, 入母屋 檜皮葺) with the 南北廻廊, stone stairs, fox statues"""
    cx, cy, Lf, Df, th = rect_frame(S, 105449733)
    z0 = 40.2
    us = [-4.95, -1.95, 1.95, 4.95]; vs = [-2.7, 0.0, 2.7]
    L, D = 9.9, 5.4
    with Frame(B, cx, cy, z0, th):
        arch.platform(B, rect_pts(-6.3, -4.0, 6.3, 4.0), -1.0, 0.0)
        # lower storey
        ring_pillars(B, us, vs, 0.0, 6.4, 0.29, 'vermilion')
        arch.pillar(B, us[1], 0.0, 0.0, 5.3, 0.27, 'vermilion'); arch.pillar(B, us[2], 0.0, 0.0, 5.3, 0.27, 'vermilion')
        for z, h in ((0.35, 0.2), (3.3, 0.24), (5.0, 0.34)):
            arch.nageshi(B, L, D, z, 'vermilion', h=h, w=0.14, out=0.18)
        for (p0, p1, side) in bays(us, vs):
            centre = side in (0, 2) and abs(p0[0] + p1[0]) < 0.1
            if centre: continue
            if side in (0, 2):
                # the 随身 bays: green lattice (連子) over a white-plastered dado, plaster above
                arch.infill(B, p0, p1, 0.35, 1.1, 'plaster')
                arch.infill(B, p0, p1, 1.1, 3.15, 'renji', mat='copper')
                arch.infill(B, p0, p1, 3.45, 4.8, 'plaster')
            else:
                arch.infill(B, p0, p1, 0.35, 4.8, 'plaster')
        # the balcony on two-step brackets
        top1, r1 = bracket_row(B, L, D, 5.2, 'futatesaki', 0.55, 'vermilion', 'white_paint', us=us, vs=vs)
        zb = top1 + 0.1
        a, c = L / 2 + 1.1, D / 2 + 1.1
        prim.box(B, -a, -c, zb - 0.12, a, c, zb, 'wood_natural', faces='xXyYzZ')
        prim.box(B, -a - 0.02, -c - 0.02, zb - 0.32, a + 0.02, c + 0.02, zb - 0.12, 'vermilion', faces='xXyYz')
        arch.railing(B, [(-a, -c), (a, -c), (a, c), (-a, c)], zb, h=0.75, mat='vermilion', cap_mat='gold', closed=True)
        # upper storey
        for z, h in ((zb + 0.25, 0.18), (zb + 1.55, 0.2), (zb + 2.15, 0.28)):
            arch.nageshi(B, L, D, z, 'vermilion', h=h, w=0.13, out=0.15)
        for (p0, p1, side) in bays(us, vs):
            arch.infill(B, p0, p1, zb + 0.3, zb + 1.4, 'plaster')
            arch.infill(B, p0, p1, zb + 1.6, zb + 1.95, 'plaster')
        plaque(B, 0.0, -2.95, zb + 0.95, 0.85, 1.2, ground='black_lacquer')
        top2, r2 = bracket_row(B, L, D, zb + 2.3, 'mitesaki', 0.62, 'vermilion', 'white_paint', us=us, vs=vs)
        o = 8.1 - L / 2 - r2
        rr = roof.roof(B, L + 2 * r2, D + 2 * r2, top2, o, kind='irimoya', cover='hiwada', pitch=0.78, rafter=0.26, rafter_mat='vermilion',
                       rafter_end='gold', sori=0.45, gable_wall='temple_wall', bargeboard_mat='wood_dark', ends='oni')
        # green copper eave gutter fittings (the dossier: 緑青 eave gutters) - a thin copper strip along the eaves
        # 南北廻廊: 5 bays x 1 bay, 切妻 檜皮葺, green lattice windows on the front
        for sg in (-1, 1):
            u0, u1 = sg * 4.95, sg * 14.0
            cu = (u0 + u1) / 2; Lc = abs(u1 - u0)
            with Frame(B, cu, 0.0, 0.0, 0.0):
                cus = np.linspace(-Lc / 2, Lc / 2, 6); cvs = [-1.3, 1.3]
                ring_pillars(B, cus[1:] if sg > 0 else cus[:-1], cvs, 0.0, 3.3, 0.17, 'vermilion')
                arch.nageshi(B, Lc, 2.6, 3.2, 'vermilion', h=0.22, w=0.12, out=0.12, sides=(0, 2))
                arch.nageshi(B, Lc, 2.6, 0.3, 'vermilion', h=0.16, w=0.12, out=0.1, sides=(0, 2))
                for i in range(5):
                    p0, p1 = (cus[i], cvs[0]), (cus[i + 1], cvs[0])
                    arch.infill(B, p0, p1, 0.3, 1.05, 'plaster')
                    arch.infill(B, p0, p1, 1.05, 2.45, 'renji', mat='copper')
                    arch.infill(B, p0, p1, 2.45, 3.05, 'plaster')
                    q0, q1 = (cus[i + 1], cvs[1]), (cus[i], cvs[1])
                    arch.infill(B, q0, q1, 0.3, 3.05, 'plaster')
                end = cus[-1] if sg > 0 else cus[0]
                arch.infill(B, (end, -1.3 * sg), (end, 1.3 * sg), 0.3, 3.05, 'plaster')
                roof.roof(B, Lc, 2.6, 3.4, 1.25, kind='kirizuma', cover='hiwada', pitch=0.55, verge=0.6, rafter=0.3, rafter_mat='vermilion', rafter_end='white_paint',
                          bargeboard_mat='wood_dark', ends=None, gable_wall='temple_wall')
        # stone stairs from the approach up to the gate platform, stone side walls
        zbot = S.ground(*Frame(B, cx, cy, z0, th).world((0, -11.6, 0))[:2]) - z0
        arch.stairs(B, (0, -11.6), (0, -4.0), zbot, 0.0, 8.0, 'stone', riser=0.165)
        for sg in (-1, 1):
            x0_, x1_ = sg * 4.0 - 0.35, sg * 4.0 + 0.35
            P = np.array([(x0_, -11.6, zbot - 0.3), (x1_, -11.6, zbot - 0.3), (x1_, -4.0, -0.3), (x0_, -4.0, -0.3),
                          (x0_, -11.6, zbot + 0.45), (x1_, -11.6, zbot + 0.45), (x1_, -4.0, 0.45), (x0_, -4.0, 0.45)])
            B.add(P, [[4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [3, 0, 4], [3, 4, 7]], 'stone')
            # the fox statues on tall pedestals flanking the top of the stairs
            prim.box(B, sg * 4.2 - 0.8, -6.0, -0.4, sg * 4.2 + 0.8, -4.4, 1.7, 'stone')
            prim.box(B, sg * 4.2 - 0.7, -5.9, 1.7, sg * 4.2 + 0.7, -4.5, 1.95, 'stone')
    ex.append(world_ring(cx, cy, th, rect_pts(-14.9, -5.9, 14.9, 5.9)))
    F = Frame(B, cx, cy, z0, th)
    return dict(foxes=[(F.world((sg * 4.2, -5.2, 1.95)), th + math.pi, 1.45, 'bronze', ('key', 'jewel')[sg > 0]) for sg in (-1, 1)],
                lanterns=[F.world((sg * 6.2, -13.0, 0.0)) for sg in (-1, 1)])

def gehaiden(B, S, ex):
    """外拝殿 (舞殿, 1840): 5 x 3 bays, open, 入母屋 檜皮葺 with a black lattice gable; railing, 12 iron lanterns, 玉垣"""
    cx, cy, Lf, Df, th = rect_frame(S, 105449674)
    z0 = 40.2
    L, D = 11.5, 7.2
    us = np.linspace(-L / 2, L / 2, 6); vs = np.linspace(-D / 2, D / 2, 4)
    zf = 1.15
    with Frame(B, cx, cy, z0, th):
        arch.platform(B, rect_pts(-L / 2 - 1.3, -D / 2 - 1.3, L / 2 + 1.3, D / 2 + 1.3), -0.4, zf - 0.12, mat='stone')
        prim.box(B, -L / 2 - 1.2, -D / 2 - 1.2, zf - 0.12, L / 2 + 1.2, D / 2 + 1.2, zf, 'wood_natural', faces='Z')
        ring_pillars(B, us, vs, zf, zf + 4.0, 0.2, 'vermilion')
        for z, h in ((zf + 2.55, 0.2), (zf + 3.55, 0.26)):
            arch.nageshi(B, L, D, z, 'vermilion', h=h, w=0.12, out=0.14)
        for (p0, p1, side) in bays(us, vs):
            arch.infill(B, p0, p1, zf + 2.65, zf + 3.4, 'plaster')
            # 水引幕 (blue valance) and 御簾 (bamboo blinds) hanging in the open bays
            d = np.subtract(p1, p0); n_out = np.array([d[1], -d[0]]) / np.linalg.norm(d)
            a = np.array(p0) + d / np.linalg.norm(d) * 0.2 - n_out * 0.05; b = np.array(p1) - d / np.linalg.norm(d) * 0.2 - n_out * 0.05
            for (za, zb_, m, c0) in ((zf + 2.12, zf + 2.45, 'cloth', (38, 42, 110, 0)), (zf + 1.45, zf + 2.12, 'bamboo', (255, 255, 255, 0))):
                P = np.array([(*a, za), (*b, za), (*b, zb_), (*a, zb_)])
                B.add(P, [[0, 1, 2], [0, 2, 3], [0, 2, 1], [0, 3, 2]], m, tag='detail', c0=c0)
        top, reach = bracket_row(B, L, D, zf + 4.0, 'degumi', 0.7, 'vermilion', 'white_paint', us=us, vs=vs)
        o = 8.45 - L / 2 - reach
        rr = roof.roof(B, L + 2 * reach, D + 2 * reach, top, o, kind='irimoya', cover='hiwada', pitch=0.72, rafter=0.26, rafter_mat='vermilion',
                       rafter_end='gold', sori=0.5, gable_wall='black_lacquer', bargeboard_mat='wood_dark', ends='oni')
        arch.veranda(B, L, D, zf, 0.9, mat='wood_natural', post_mat='vermilion')
        a, c = L / 2 + 0.85, D / 2 + 0.85
        arch.railing(B, [(-a, -c), (a, -c), (a, c), (-a, c)], zf, h=0.7, mat='vermilion', cap_mat='gold', closed=True)
        # the 玉垣 at ground level around the platform
        g = 1.9
        fence(B, [(-L / 2 - g, -D / 2 - g), (L / 2 + g, -D / 2 - g), (L / 2 + g, D / 2 + g), (-L / 2 - g, D / 2 + g), (-L / 2 - g, -D / 2 - g)], 0.0, 1.0)
        lan = []
        for x in (us[:-1] + us[1:]) / 2:
            lan += [(x, -D / 2 - reach * 0.5), (x, D / 2 + reach * 0.5)]
        lan += [(-L / 2 - reach * 0.5, 0.0), (L / 2 + reach * 0.5, 0.0)]
        for (x, y) in lan: hanging_lantern(B, x, y, top - 0.1, 0.9)
    ex.append(world_ring(cx, cy, th, rect_pts(-Lf / 2 - 1, -Df / 2 - 1, Lf / 2 + 1, Df / 2 + 1)))

def fence(B, pts, z0, h=1.0, mat='vermilion', ground=None, step=0.24, tag='main'):
    """玉垣 / 瑞垣: a vermilion paling fence: posts, two rails, close pales (z0 = ground, or ground(x, y))"""
    pts = [np.asarray(p, float) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; d = b - a; Ln = np.linalg.norm(d)
        if Ln < 0.2: continue
        d /= Ln
        za = ground(*a) if ground else z0; zb = ground(*b) if ground else z0
        for t in np.arange(0, Ln + 0.01, 1.8):
            q = a + d * t; zq = za + (zb - za) * t / Ln
            prim.box(B, q[0] - 0.07, q[1] - 0.07, zq - 0.2, q[0] + 0.07, q[1] + 0.07, zq + h + 0.08, mat, faces='xXyYZ', tag=tag)
        for zz in (0.22, h - 0.12):
            prim.obox(B, np.r_[a, za + zz], np.r_[b, zb + zz], 0.06, 0.07, mat, tag=tag)
        # pales (close square pales with gaps)
        n = np.array([-d[1], d[0]])
        P = []; I = []
        for t in np.arange(step / 2, Ln, step):
            q = a + d * t; zq = za + (zb - za) * t / Ln
            k = len(P)
            for (du, dn) in ((-0.05, -0.03), (0.05, -0.03), (0.05, 0.03), (-0.05, 0.03)):
                c_ = q + d * du + n * dn
                P += [np.r_[c_, zq + 0.05], np.r_[c_, zq + h]]
            for f in range(4):
                g = (f + 1) % 4
                I += [[k + 2 * f, k + 2 * g, k + 2 * g + 1], [k + 2 * f, k + 2 * g + 1, k + 2 * f + 1]]
            I += [[k + 1, k + 3, k + 5], [k + 1, k + 5, k + 7]]
        if P:
            P = np.array(P); I = np.array(I)
            # outward winding check on the first face
            fn = np.cross(P[I[0][1]] - P[I[0][0]], P[I[0][2]] - P[I[0][0]])
            if fn @ np.r_[-n, 0] < 0: I = I[:, ::-1]
            B.add(P, I, mat, tag=tag)

def naihaiden(B, S, ex):
    """内拝殿: 入母屋 copper roof, the great 唐破風 向拝 in front, broad stone stairs"""
    cx, cy, Lf, Df, th = rect_frame(S, 105449716)
    z0 = 42.35
    vc = 1.7
    L, D = 17.0, 8.4
    us = np.linspace(-L / 2, L / 2, 8); vs = vc + np.linspace(-D / 2, D / 2, 5)
    zf = 0.55
    with Frame(B, cx, cy, z0, th):
        arch.platform(B, rect_pts(-L / 2 - 1.2, vs[0] - 5.6, L / 2 + 1.2, vs[-1] + 0.5), -0.6, zf - 0.1)
        prim.box(B, -L / 2 - 1.0, vs[0] - 1.0, zf - 0.1, L / 2 + 1.0, vs[-1], zf, 'wood_natural', faces='Z')
        ring_pillars(B, us, vs, zf, zf + 4.2, 0.22, 'vermilion')
        for z, h in ((zf + 0.3, 0.16), (zf + 2.8, 0.22), (zf + 3.8, 0.28)):
            arch.nageshi(B, L, D, z, 'vermilion', h=h, w=0.12, out=0.15, sides=(1, 2, 3) if z < zf + 2.0 else (0, 1, 2, 3))
        for (p0, p1, side) in bays(us, vs):
            if side == 0:
                arch.infill(B, p0, p1, zf + 2.9, zf + 3.65, 'plaster')
                arch.infill(B, p0, p1, zf + 0.35, zf + 2.7, 'koshi', mat='wood_dark')
            else:
                arch.infill(B, p0, p1, zf + 0.35, zf + 3.65, 'plaster', seed=3)
        top, reach = bracket_row(B, L, D, zf + 4.2, 'degumi', 0.7, 'vermilion', 'white_paint', us=us, vs=vs - vc)
        o = 10.8 - L / 2 - reach
        with Frame(B, 0.0, vc, 0.0, 0.0):
            roof.roof(B, L + 2 * reach, D + 2 * reach, top, o, kind='irimoya', cover='copper', pitch=0.62, rafter=0.26, rafter_mat='vermilion',
                      rafter_end='gold', sori=0.5, gable_wall='temple_wall', bargeboard_mat='vermilion', ends='oni')
        # the 向拝 with the great 唐破風 (3 bays wide), on four pillars
        pu = [us[2], us[5]]; pv = -6.4
        for x in pu:
            arch.pillar(B, x, pv, zf, zf + 3.7, 0.2, 'vermilion')
            prim.obox(B, (x, pv, zf + 3.45), (x, vs[0], zf + 3.9), 0.18, 0.3, 'vermilion')     # 海老虹梁
        prim.obox(B, (pu[0] - 0.5, pv, zf + 3.6), (pu[1] + 0.5, pv, zf + 3.6), 0.2, 0.4, 'vermilion')
        prim.obox(B, (pu[0] - 0.4, pv, zf + 3.1), (pu[1] + 0.4, pv, zf + 3.1), 0.14, 0.2, 'vermilion')
        kumimono(B, pu[0], pv, zf + 3.8, (0, -1), (1, 0), 'demitsudo', 0.7, 'vermilion', 'white_paint')
        kumimono(B, pu[1], pv, zf + 3.8, (0, -1), (1, 0), 'demitsudo', 0.7, 'vermilion', 'white_paint')
        # 蟇股 between the porch beams (gilt + green): a block with a gold face
        prim.box(B, -0.55, pv - 0.12, zf + 3.85, 0.55, pv + 0.12, zf + 4.35, 'vermilion')
        prim.box(B, -0.45, pv - 0.14, zf + 3.9, 0.45, pv - 0.12, zf + 4.3, 'gold', tag='detail')
        wk = (pu[1] - pu[0]) + 2.6
        karahafu(B, wk, -7.6, vs[0] - 0.4, zf + 4.25, zf + 6.15, cover='copper', depth_drop=0.0, tymp=(pu[1] - pu[0] + 0.5, zf + 3.75))
        # 鈴 and 鈴緒: bells over the offering box, a 賽銭箱
        prim.box(B, -2.6, pv + 0.6, zf, 2.6, pv + 1.5, zf + 0.75, 'wood_dark')
        for x in (-1.2, 0.0, 1.2):
            prim.lathe(B, (x, pv + 0.2, zf + 2.95), [(0.0, 0.0), (0.16, 0.06), (0.2, 0.2), (0.12, 0.33), (0.0, 0.36)], 10, 'gold', tag='detail')
            prim.cyl(B, (x, pv + 0.2, zf + 1.0), (x, pv + 0.2, zf + 2.95), 0.035, 0.035, 6, 'cloth', tag='detail', c0=(200, 40, 40, 0))
        # the broad stone stairs (11 steps) from the courtyard and the terrace
        zb = S.ground(*Frame(B, cx, cy, z0, th).world((0, -17.3, 0))[:2]) - z0
        arch.stairs(B, (0, -17.4), (0, -13.4), zb, -0.05, 13.0, 'stone', riser=0.17)
        prim.box(B, -7.0, -13.4, -0.6, 7.0, vs[0] - 0.9, -0.03, 'stone', faces='xXyYZ')
        prim.polygon(B, rect_pts(-7.0, -13.4, 7.0, vs[0] - 0.9), -0.03, 'stone', tag='walk')
        for sg in (-1, 1):
            # the round fox pedestals beside the stairs
            prim.cyl(B, (sg * 7.9, -15.5, zb - 0.3), (sg * 7.9, -15.5, zb + 1.9), 0.75, 0.7, 12, 'stone')
            prim.cyl(B, (sg * 7.9, -15.5, zb + 1.9), (sg * 7.9, -15.5, zb + 2.15), 0.85, 0.85, 12, 'stone')
        prim.polygon(B, rect_pts(-L / 2 - 1.0, vs[0] - 1.0, L / 2 + 1.0, vs[-1]), zf, 'stone', tag='walk')
    ex.append(world_ring(cx, cy, th, rect_pts(-Lf / 2 - 0.5, -8.6, Lf / 2 + 0.5, Df - 7.6)))
    F = Frame(B, cx, cy, z0, th)
    return dict(foxes=[(F.world((sg * 7.9, -15.5, zb + 2.15)), th + math.pi, 1.5, 'bronze', ('rice', 'jewel')[sg > 0]) for sg in (-1, 1)])

def nagare_hall(B, S, ex, oid, z0, core_L, core_D, porch, nb=5, floor=1.3, h_wall=4.0, z_ridge=None, cover='hiwada', back=(1.0, 0.0), front_shift=0.0,
                eave_side=2.0, eave_back=1.7, eave_front=1.7, r=0.2, porch_h=None, lattice='koshi', lanterns=True, railing=True, stairs=True, scale_br=0.65,
                walls='plaster'):
    """a 流造 shrine (五間社 / 三間社): the walled 身舎 on a raised floor with a veranda and railing all round, the front
    庇 (porch) under the long front slope, 木階 stairs up from the porch"""
    cx, cy, Lf, Df, th = rect_frame(S, oid, back)
    L = core_L
    us = np.linspace(-L / 2, L / 2, nb + 1)
    vcf = -Df / 2 + eave_front + porch + front_shift; vcb = vcf + core_D
    vs = np.linspace(vcf, vcb, 3)
    pv = vcf - porch
    zw = floor + h_wall
    with Frame(B, cx, cy, z0, th):
        arch.platform(B, rect_pts(-L / 2 - 1.6, pv - 0.8, L / 2 + 1.6, vcb + 1.6), -0.6, 0.25, mat='stone', walk=True)
        ring_pillars(B, us, vs, 0.25, zw, r, 'vermilion', base=False)
        prim.box(B, -L / 2 - 1.1, vcf - 1.1, floor - 0.12, L / 2 + 1.1, vcb + 1.1, floor, 'wood_natural', faces='xXyYZ')
        prim.polygon(B, rect_pts(-L / 2 - 1.1, vcf - 1.1, L / 2 + 1.1, vcb + 1.1), floor, 'stone', tag='walk')
        # under-floor: dark lattice panels between the pillars (the black and white 格子 of the photos)
        for (p0, p1, side) in bays(us, vs):
            arch.infill(B, p0, p1, 0.3, floor - 0.15, lattice, mat='black_lacquer')
        for z, h in ((floor + 0.25, 0.16), (floor + h_wall * 0.62, 0.2), (zw - 0.15, 0.24)):
            arch.nageshi(B, L, core_D, z, 'vermilion', h=h, w=0.1, out=0.12)
        for (p0, p1, side) in bays(us, vs):
            if side == 0:
                # the front: vermilion board doors (板扉) with gilt fittings, plaster above
                arch.infill(B, p0, p1, floor + 0.3, floor + h_wall * 0.6, 'board', mat='vermilion')
                mid = ((p0[0] + p1[0]) / 2, p0[1] - 0.08)
                for dz in (0.35, h_wall * 0.3):
                    prim.box(B, mid[0] - 0.5, mid[1] - 0.02, floor + dz, mid[0] + 0.5, mid[1], floor + dz + 0.12, 'gold', tag='detail')
                arch.infill(B, p0, p1, floor + h_wall * 0.64, zw - 0.3, 'plaster')
            elif side == 2:
                arch.infill(B, p0, p1, floor + 0.3, zw - 0.3, 'plaster', seed=2)
            else:
                arch.infill(B, p0, p1, floor + 0.3, floor + h_wall * 0.6, 'plaster', seed=5)
                arch.infill(B, p0, p1, floor + h_wall * 0.64, zw - 0.3, 'plaster', seed=6)
                # a green-framed window (連子) on the sides
                q0 = np.array(p0) + (np.array(p1) - np.array(p0)) * 0.3; q1 = np.array(p0) + (np.array(p1) - np.array(p0)) * 0.7
                arch.infill(B, q0, q1, floor + h_wall * 0.36, floor + h_wall * 0.52, 'renji', mat='copper')
        for x in us:
            for y in (vcf, vcb):
                kumimono(B, x, y, zw, (0, -1 if y == vcf else 1), (1, 0), 'hira', scale_br, 'vermilion', 'white_paint')
        for y in (vcf, vcb):
            prim.obox(B, (-L / 2 - 0.3, y, zw + 0.5), (L / 2 + 0.3, y, zw + 0.5), 0.18, 0.2, 'vermilion')
        # porch (向拝 / 庇) pillars and beams
        ph = porch_h or (h_wall * 0.9 + floor * 0.4)
        for x in us:
            arch.pillar(B, x, pv, 0.25, ph, r * 0.8, 'vermilion', base=True)
            prim.obox(B, (x, pv, ph - 0.25), (x, vcf, zw - 0.2), 0.14, 0.24, 'vermilion')
        prim.obox(B, (us[0] - 0.3, pv, ph - 0.12), (us[-1] + 0.3, pv, ph - 0.12), 0.18, 0.24, 'vermilion')
        for x in us:
            kumimono(B, x, pv, ph, (0, -1), (1, 0), 'funa', scale_br, 'vermilion')
        # the roof: ridge over the 身舎, front slope down over the porch
        vr = (vcf + vcb) / 2
        vb = vcb + eave_back; vf = pv - eave_front
        zb_e = zw + 0.35
        zr = z_ridge if z_ridge is not None else zw + 0.55 + (vb - vr) * 0.62
        zf_e = ph + 0.45 - (pv - vf) * 0.25
        nagare_roof(B, L + 2 * (eave_side - 0.9), vb, vr, vf, zb_e, zr, zf_e, verge=0.9, cover=cover, rafters=(vcf, 0.3),
                    core=(vcf, vcb), z_wall=zw + 0.6)
        # veranda + railing all round (四方高欄), 木階 stairs from the porch
        if railing:
            a = L / 2 + 0.95
            arch.railing(B, [(-1.2, vcf - 1.05), (-a, vcf - 1.05), (-a, vcb + 1.05), (a, vcb + 1.05), (a, vcf - 1.05), (1.2, vcf - 1.05)], floor, h=0.75, mat='vermilion', cap_mat='gold')
        if stairs:
            arch.stairs(B, (0, pv + 0.3), (0, vcf - 1.1), 0.25, floor, 2.3, 'wood_natural', riser=0.2)
        if lanterns:
            for x in (us[:-1] + us[1:]) / 2:
                hanging_lantern(B, x, pv - 0.1, ph - 0.3, 0.6, mat='bronze')
    ex.append(world_ring(cx, cy, th, rect_pts(-Lf / 2 - 0.3, -Df / 2 - 0.3, Lf / 2 + 0.3, Df / 2 + 0.3)))
    return dict(frame=(cx, cy, th), pv=pv, vcf=vcf, vcb=vcb, L=L)

def kaguraden(B, S, ex):
    """神楽殿: a dark-stained hall, 入母屋 檜皮葺, the stage open to the north with a purple curtain (菊紋)"""
    cx, cy, Lf, Df, th = rect_frame(S, 952815193, back=(0.0, -1.0))
    z0 = S.ground(cx, cy) + 0.1
    L, D = 12.0, 8.0
    uc, vc = 1.5, -0.8
    us = uc + np.linspace(-L / 2, L / 2, 6); vs = vc + np.linspace(-D / 2, D / 2, 4)
    zf = 1.0
    with Frame(B, cx, cy, z0, th):
        arch.platform(B, rect_pts(us[0] - 1.2, vs[0] - 1.2, us[-1] + 1.2, vs[-1] + 1.2), -0.5, 0.2)
        ring_pillars(B, us, vs, 0.2, zf + 3.6, 0.19, 'wood_dark', base=False)
        prim.box(B, us[0] - 0.9, vs[0] - 0.9, zf - 0.12, us[-1] + 0.9, vs[-1] + 0.9, zf, 'wood_natural', faces='xXyYZ')
        for z, h in ((zf + 2.6, 0.22), (zf + 3.45, 0.26)):
            prim.box(B, us[0] - 0.15, vs[0] - 0.12, z - h, us[-1] + 0.15, vs[0] + 0.12, z, 'wood_dark')
            prim.box(B, us[0] - 0.15, vs[-1] - 0.12, z - h, us[-1] + 0.15, vs[-1] + 0.12, z, 'wood_dark')
        for (p0, p1, side) in bays(us, vs):
            if side == 0:
                # the purple curtain (幕) with the 菊紋 in the open front
                d = np.subtract(p1, p0) / np.linalg.norm(np.subtract(p1, p0))
                a = np.array(p0) + d * 0.1; b = np.array(p1) - d * 0.1
                P = np.array([(*a, zf + 1.75), (*b, zf + 1.75), (*b, zf + 2.55), (*a, zf + 2.55)]) - [0, 0.05, 0]
                B.add(P, [[0, 1, 2], [0, 2, 3], [0, 2, 1], [0, 3, 2]], 'cloth', c0=(70, 34, 110, 0))
                m = (a + b) / 2
                prim.cyl(B, (m[0], m[1] - 0.08, zf + 2.15), (m[0], m[1] - 0.1, zf + 2.15), 0.28, 0.28, 12, 'white_paint', tag='detail')
            elif side == 2:
                arch.infill(B, p0, p1, zf, zf + 2.4, 'board', mat='wood_dark')
            else:
                arch.infill(B, p0, p1, zf, zf + 2.4, 'board', mat='wood_dark')
        top, reach = bracket_row(B, L, D, zf + 3.6, 'demitsudo', 0.6, 'wood_dark', 'gold', us=us - uc, vs=vs - vc)
        with Frame(B, uc, vc, 0.0, 0.0):
            roof.roof(B, L + 2 * reach, D + 2 * reach, top, 1.9, kind='irimoya', cover='hiwada', pitch=0.66, rafter=0.3, rafter_mat='wood_dark',
                      rafter_end='gold', gable_wall='wood_dark', bargeboard_mat='wood_dark')
        a0, a1, c0_, c1_ = us[0] - 0.85, us[-1] + 0.85, vs[0] - 0.85, vs[-1] + 0.85
        arch.railing(B, [(a0, c0_), (a1, c0_), (a1, c1_), (a0, c1_)], zf, h=0.65, mat='black_lacquer', cap_mat='gold', closed=True)
        prim.polygon(B, rect_pts(a0, c0_, a1, c1_), zf, 'stone', tag='walk')
        # the west wing (楽屋): a lower 切妻 annex
        with Frame(B, -6.8, 0.6, 0.0, 0.0):
            wl, wd = 6.6, 6.4
            wus = np.linspace(-wl / 2, wl / 2, 4); wvs = np.linspace(-wd / 2, wd / 2, 3)
            ring_pillars(B, wus, wvs, 0.2, 3.4, 0.15, 'wood_dark', base=False)
            for (p0, p1, side) in bays(wus, wvs):
                arch.infill(B, p0, p1, 0.4, 3.1, 'board' if side != 0 else 'koshi', mat='wood_dark')
            roof.roof(B, wl, wd, 3.5, 1.1, kind='kirizuma', cover='hiwada', pitch=0.6, verge=0.7, rafter=0.3, rafter_mat='wood_dark', gable_wall='wood_dark', ends=None)
    ex.append(world_ring(cx, cy, th, rect_pts(-Lf / 2 - 0.5, -Df / 2 - 0.5, Lf / 2 + 0.5, Df / 2 + 0.5)))

def juyosho(B, S, ex):
    """授与所 (the amulet office on the north of the court): a long vermilion hall, white walls, copper 入母屋"""
    cx, cy, Lf, Df, th = rect_frame(S, 105449708, back=(0.0, 1.0))
    z0 = S.ground(cx, cy) + 0.05
    L, D = 26.4, 6.0
    vc = 1.4
    us = np.linspace(-L / 2, L / 2, 12); vs = vc + np.linspace(-D / 2, D / 2, 3)
    with Frame(B, cx, cy, z0, th):
        arch.platform(B, rect_pts(-L / 2 - 0.6, vs[0] - 0.6, L / 2 + 0.6, vs[-1] + 0.6), -0.4, 0.15)
        ring_pillars(B, us, vs, 0.15, 3.6, 0.16, 'vermilion', base=False)
        for (p0, p1, side) in bays(us, vs):
            if side == 0:
                arch.infill(B, p0, p1, 0.15, 0.95, 'board', mat='wood_dark')
                arch.infill(B, p0, p1, 0.95, 2.5, 'renji', mat='wood_dark')
                arch.infill(B, p0, p1, 2.55, 3.45, 'plaster')
            else:
                arch.infill(B, p0, p1, 0.15, 3.45, 'plaster', seed=4)
        for y in (vs[0], vs[-1]):
            prim.obox(B, (-L / 2 - 0.25, y, 2.5), (L / 2 + 0.25, y, 2.5), 0.12, 0.16, 'vermilion')
            prim.obox(B, (-L / 2 - 0.25, y, 3.45), (L / 2 + 0.25, y, 3.45), 0.14, 0.22, 'vermilion')
        with Frame(B, 0.0, vc, 0.0, 0.0):
            roof.roof(B, L, D, 3.75, 1.5, kind='irimoya', cover='copper', pitch=0.55, rafter=0.3, rafter_mat='vermilion', rafter_end='white_paint',
                      gable_wall='temple_wall', bargeboard_mat='vermilion', sori=0.3)
    ex.append(world_ring(cx, cy, th, rect_pts(-Lf / 2 - 0.3, -Df / 2 - 0.3, Lf / 2 + 0.3, Df / 2 + 0.3)))

def small_shrine(B, x, y, z, yaw, w=1.8, d=1.6, h=1.6, kind='nagare', base=0.6, roof_cover='hiwada', mat='vermilion'):
    """a small 一間社 (流造 / 春日造) on a stone base: box body, plank doors, a little roof"""
    with Frame(B, x, y, z, yaw):
        prim.box(B, -w / 2 - 0.3, -d / 2 - 0.5, -0.4, w / 2 + 0.3, d / 2 + 0.3, base, 'stone')
        prim.box(B, -w / 2, -d / 2, base, w / 2, d / 2, base + h, 'temple_wall', faces='xXYZ', c0=(238, 234, 224, 35))
        prim.box(B, -w / 2, -d / 2 - 0.01, base, w / 2, -d / 2 + 0.05, base + h, mat, faces='y')
        prim.box(B, -0.04, -d / 2 - 0.04, base + 0.1, 0.04, -d / 2 - 0.01, base + h - 0.1, 'gold', tag='detail')
        for sx in (-1, 1):
            for sy in (-1, 1):
                prim.box(B, sx * w / 2 - 0.07, sy * d / 2 - 0.07, base, sx * w / 2 + 0.07, sy * d / 2 + 0.07, base + h, mat, faces='xXyY')
        if kind == 'nagare':
            nagare_roof(B, w, d / 2 + 0.5, 0.0, -d / 2 - 0.9, base + h + 0.15, base + h + 0.95, base + h - 0.1, verge=0.35, cover=roof_cover, th=0.16,
                        rafters=(0, 0), gable=False)
            for sx in (-1, 1):
                prim.box(B, sx * w / 2 - 0.06, -d / 2 - 0.75, base, sx * w / 2 + 0.06, -d / 2 - 0.63, base + h - 0.05, mat)
        else:   # 春日造: gable to the front + a small front pent roof
            with Frame(B, 0, 0, 0, math.pi / 2):
                roof.roof(B, d, w, base + h + 0.05, 0.35, kind='kirizuma', cover=roof_cover, pitch=0.9, verge=0.4, rafter=0, ends=None, edge=0.14, ridge_h=0.15, ridge_w=0.2)
            prim.grid_surface(B, lambda u, v: (u, v, base + h - 0.05 + (v + d / 2 + 0.8) * 0.35), -w / 2 - 0.2, w / 2 + 0.2, -d / 2 - 0.8, -d / 2, 2, 2,
                              roof.COVER_MAT[roof_cover], flip=True)

def okusha(B, S, ex):
    """奥社奉拝所 (rebuilt after 1794; worship hall in front of the mountain, 14.1 x 7.5 m): a 3-bay open front under an
    入母屋 roof, the rear 本殿-like part; the おもかる石 lanterns behind on the right"""
    cx, cy, Lf, Df, th = rect_frame(S, 301527734, back=(1.0, 0.0))
    z0 = S.ground(cx - 3.0, cy) + 0.05
    with Frame(B, cx, cy, z0, th):
        # in this frame the long side runs east-west: front hall v in [-7, 0], rear part v in [0, 7] (narrower)
        L, D = 6.6, 5.0
        vc = -3.6
        us = np.linspace(-L / 2, L / 2, 4); vs = vc + np.linspace(-D / 2, D / 2, 3)
        arch.platform(B, rect_pts(-L / 2 - 1.2, vs[0] - 1.6, L / 2 + 1.2, vs[-1] + 0.8), -0.5, 0.2)
        ring_pillars(B, us, vs, 0.2, 3.6, 0.17, 'vermilion')
        for (p0, p1, side) in bays(us, vs):
            if side == 0:
                arch.infill(B, p0, p1, 2.75, 3.45, 'plaster')
            elif side == 2:
                arch.infill(B, p0, p1, 0.2, 3.45, 'koshi', mat='vermilion')
            else:
                arch.infill(B, p0, p1, 2.75, 3.45, 'plaster')
                arch.infill(B, p0, p1, 0.2, 1.0, 'koshi', mat='vermilion')
        arch.nageshi(B, L, D, 2.75, 'vermilion', h=0.2, w=0.1, out=0.12)
        arch.nageshi(B, L, D, 3.6, 'vermilion', h=0.26, w=0.12, out=0.12)
        a, c = L / 2 - 0.1, vs[0] - 0.6
        arch.railing(B, [(-a, c), (-0.9, c)], 0.2, h=0.8, mat='vermilion', giboshi=False)
        arch.railing(B, [(0.9, c), (a, c)], 0.2, h=0.8, mat='vermilion', giboshi=False)
        top, reach = bracket_row(B, L, D, 3.6, 'funa', 0.8, 'vermilion', us=us, vs=vs - vc)
        with Frame(B, 0.0, vc, 0.0, 0.0):
            roof.roof(B, L, D, top + 0.1, 1.5, kind='irimoya', cover='copper', pitch=0.5, rafter=0.3, rafter_mat='vermilion', rafter_end='white_paint',
                      gable_wall='temple_wall', bargeboard_mat='vermilion', sori=0.3, gable_frac=0.55)
        # shimenawa + shide over the front
        prim.sweep(B, np.array([(x, vs[0] - 0.15, 3.15 - 0.25 * math.cos(x / 2.2 * math.pi / 2)) for x in np.linspace(-2.3, 2.3, 9)]),
                   [(0.07 * math.cos(t), 0.07 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 7)[:-1]], 'bamboo', tag='detail')
        for x in (-1.2, -0.4, 0.4, 1.2):
            P = np.array([(x - 0.08, vs[0] - 0.16, 2.9), (x + 0.08, vs[0] - 0.16, 2.9), (x + 0.08, vs[0] - 0.16, 2.35), (x - 0.08, vs[0] - 0.16, 2.35)])
            B.add(P, [[0, 2, 1], [0, 3, 2], [0, 1, 2], [0, 2, 3]], 'white_paint', tag='detail')
        # the rear part: a walled 本殿-like block
        with Frame(B, 0.0, 3.4, 0.0, 0.0):
            prim.box(B, -1.9, -2.6, 0.2, 1.9, 2.6, 2.9, 'temple_wall', faces='xXYZ', c0=(238, 234, 224, 35), c1=(0, 4, 0, 0))
            for sx in (-1, 1):
                for sy in (-1, 1):
                    prim.box(B, sx * 1.9 - 0.1, sy * 2.6 - 0.1, 0.2, sx * 1.9 + 0.1, sy * 2.6 + 0.1, 2.95, 'vermilion', faces='xXyY')
            with Frame(B, 0, 0, 0, math.pi / 2):
                roof.roof(B, 5.2, 3.8, 3.0, 0.8, kind='kirizuma', cover='copper', pitch=0.55, verge=0.5, rafter=0, ends=None, edge=0.2)
        prim.polygon(B, rect_pts(-L / 2 - 1.2, vs[0] - 1.6, L / 2 + 1.2, vs[-1] + 0.8), 0.2, 'stone', tag='walk')
        # おもかる石: a pair of stone lanterns behind on the right (north), the stone ball on top
        F = Frame(B, cx, cy, z0, th)
    oks = []
    for du in (-1.1, 1.1):
        p = F.world((L / 2 + 2.6 + du * 0.0, -1.0 + du, 0.0))
        oks.append(p)
    ex.append(world_ring(cx, cy, th, rect_pts(-Lf / 2 - 0.5, -Df / 2 - 0.5, Lf / 2 + 0.5, Df / 2 + 0.5)))
    return dict(omokaru=oks, front=F.world((0.0, vs[0] - 3.0, 0.0)), th=th)

def kumataka(B, S, ex):
    """熊鷹社 on its stone peninsula into 新池: the worship shed with racks of candles (lit), vermilion"""
    cx, cy, Lf, Df, th = rect_frame(S, 301527741, back=(1.0, 0.3))
    z0 = S.ground(cx, cy) + 0.05
    with Frame(B, cx, cy, z0, th):
        L, D = Lf - 1.6, Df - 1.4
        us = np.linspace(-L / 2, L / 2, 4); vs = np.linspace(-D / 2, D / 2, 2)
        arch.platform(B, rect_pts(-L / 2 - 0.8, -D / 2 - 0.8, L / 2 + 0.8, D / 2 + 0.8), -0.6, 0.15)
        ring_pillars(B, us, vs, 0.15, 3.0, 0.13, 'vermilion')
        arch.nageshi(B, L, D, 2.95, 'vermilion', h=0.22, w=0.1, out=0.1)
        roof.roof(B, L, D, 3.1, 0.9, kind='kirizuma', cover='copper', pitch=0.5, verge=0.6, rafter=0.3, rafter_mat='vermilion', ends=None)
        # candle racks (lit)
        for k, x in enumerate(np.linspace(-L / 2 + 0.6, L / 2 - 0.6, 3)):
            prim.box(B, x - 0.6, D / 2 - 0.6, 0.15, x + 0.6, D / 2 - 0.2, 1.0, 'metal_dark')
            prim.box(B, x - 0.55, D / 2 - 0.55, 1.0, x + 0.55, D / 2 - 0.25, 1.06, 'lamp', tag='detail')
            B.lamp(x, D / 2 - 0.4, 1.2, 10.0, (1.0, 0.65, 0.3))
        small_shrine(B, 0.0, D / 2 + 1.3, 0.15, 0.0, 1.4, 1.2, 1.3, base=0.5)
        prim.polygon(B, rect_pts(-L / 2 - 0.8, -D / 2 - 0.8, L / 2 + 0.8, D / 2 + 0.8), 0.15, 'stone', tag='walk')
    ex.append(world_ring(cx, cy, th, rect_pts(-Lf / 2 - 0.5, -Df / 2 - 0.5, Lf / 2 + 0.5, Df / 2 + 0.5)))

def otorii(B, S, oid, H, span, d, gaku=False):
    """一ノ鳥居 / 二ノ鳥居 (concrete, 台輪鳥居): the gate line from OSM, +y toward the shrine (east)"""
    bar = [b for b in S.osm['barriers'] if b['id'] == oid][0]
    L = np.array(bar['line'][0]); c = L.mean(0)
    d_ = L[-1] - L[0]; yaw = math.atan2(d_[1], d_[0])
    # +y must point east
    if -math.sin(yaw) < 0: yaw += math.pi
    z = S.ground(*c)
    t = FT.Template(FT.inari_torii, H, span, d, 'XL', inscribe=False, plaque=gaku)
    t.add(c[0], c[1], z, yaw)
    t.flush(B)
    return (c[0], c[1], z, yaw)

def build(B, S, ex):
    """the lower precinct; returns positions for props (foxes, lanterns, おもかる石)"""
    out = dict(foxes=[], lanterns=[])
    out['torii1'] = otorii(B, S, 359847609, 8.3, 5.8, 0.7)
    out['torii2'] = otorii(B, S, 359847610, 7.9, 5.5, 0.66)
    r = romon(B, S, ex); out['foxes'] += r['foxes']; out['lanterns'] += r['lanterns']
    gehaiden(B, S, ex)
    r = naihaiden(B, S, ex); out['foxes'] += r['foxes']
    out['honden'] = nagare_hall(B, S, ex, 899425893, 42.45, 10.6, 5.2, 2.8, nb=5, floor=1.4, h_wall=4.2, z_ridge=8.9, eave_side=2.4,
                                eave_back=1.9, eave_front=2.2, r=0.22)
    out['gonden'] = nagare_hall(B, S, ex, 305214371, 42.55, 7.6, 3.8, 2.2, nb=5, floor=1.1, h_wall=3.3, eave_side=1.5, eave_back=1.4, eave_front=1.6, r=0.17)
    out['okumiya'] = nagare_hall(B, S, ex, 301527733, S.ground(1391.3, -2054.5) + 0.05, 5.6, 3.2, 2.0, nb=3, floor=1.0, h_wall=2.9, eave_side=1.4,
                                 eave_back=1.2, eave_front=1.4, r=0.15, scale_br=0.5)
    kaguraden(B, S, ex)
    juyosho(B, S, ex)
    # small shrines: 白狐社 (一間社春日造), 玉山稲荷社, 長者社, 荷田社 ...
    for oid, kind, back in ((301527731, 'kasuga', (1.0, 0.0)), (305214602, 'nagare', (1.0, 0.0)), (305214359, 'nagare', (0.0, 1.0)),
                            (305214367, 'nagare', (1.0, 0.0)), (305214364, 'nagare', (1.0, 0.0)), (626177617, 'nagare', (1.0, 0.0))):
        cx, cy, Lf, Df, th = rect_frame(S, oid, back)
        small_shrine(B, cx, cy, S.ground(cx, cy), th, min(Lf - 1.0, 3.2), min(Df - 1.0, 2.6), 1.8 if Lf > 3.5 else 1.4, kind=kind)
        ex.append(world_ring(cx, cy, th, rect_pts(-Lf / 2, -Df / 2, Lf / 2, Df / 2)))
    out['okusha'] = okusha(B, S, ex)
    kumataka(B, S, ex)
    return out
