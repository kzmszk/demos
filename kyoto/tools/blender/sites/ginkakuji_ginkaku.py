"""観音殿 (銀閣), 1489: two storeys under a 宝形 roof of 杮 shingles with a bronze phoenix.

Frame: u = north, v = west, w = up from the ground at the building; the front (v-) faces east over 錦鏡池.
1F 心空殿 (書院造): E/W faces 8.2 m (4 bays of 2.05), S face 5.9 m (3 bays), the N face 7.0 m with a 1.1 m bump on the
west (a board door under its own pent roof); 腰高障子, a plank door, a lattice window, white plaster 小壁; an open veranda
(落縁) on the east with a long 沓脱石.  Lower roof: a 杮葺 skirt with skewed hips up to the upper storey's base.
2F 潮音閣 (禅宗様): 3 x 3 bays, 5.6 m square; 花頭窓 3 on E and W, S = 花頭窓 / 桟唐戸 / 花頭窓, N = board / 桟唐戸 / board;
veranda with 跳高欄 all round; bracket sets in a dense row; 宝形 roof, deep eaves, two tiers of rafters; 露盤 box + 鳳凰.
Heights (above ground): 1F floor 0.6, eave edge 3.72, upper deck 4.98, upper eave edge 7.64, apex 10.2, phoenix top ~11.3."""
import math
import numpy as np
from jk import prim, arch, Frame
from jk import roof as jroof
from . import ginkakuji_util as U

WD = 'wood_dark'

# ------------------------------------------------------------------ the lower skirt roof (skewed hips)
def skirt_roof(B, ue, ve, ub, vb, z_edge, z_top, uw, vw, teri=1.5, sori=0.3, sori_len=0.45, th=0.32, mat='hiwada', rafter=0.3, tag='main'):
    """a hipped skirt roof: eave outline +-ue x +-ve, top edge at the box +-ub x +-vb (r = 1), wall rectangle +-uw x +-vw.
    Each face rises from z_edge to z_top with a concave profile; hips run from the eave corners to the box corners."""
    P = [np.array(p, float) for p in ((-ue, -ve), (ue, -ve), (ue, ve), (-ue, ve))]
    Q = [np.array(p, float) for p in ((-ub, -vb), (ub, -vb), (ub, vb), (-ub, vb))]
    H = z_top - z_edge
    def zf(t, r, E):
        dc = np.minimum(t, 1 - t) * E
        k = np.clip(1 - dc / (sori_len * E * 0.5), 0, 1)
        return z_edge + sori * k * k * (1 - r) ** 2 + H * np.power(np.clip(r, 0, 1), teri)
    hips = []
    for k in range(4):
        P0, P1, Q0, Q1 = P[k], P[(k + 1) % 4], Q[k], Q[(k + 1) % 4]
        E = float(np.linalg.norm(P1 - P0)); dE = (P1 - P0) / E
        n_in = np.array([-dE[1], dE[0]]); n_out = -n_in
        nt = max(8, int(E / 0.4)); nr = 7
        ts = np.linspace(0, 1, nt + 1); rs = np.linspace(0, 1, nr + 1) ** 0.85
        def pt(t, r):
            a = P0 + (P1 - P0) * t; b = Q0 + (Q1 - Q0) * t
            return a + (b - a) * r
        V = []; UV = []
        for r in rs:
            for t in ts:
                xy = pt(t, r); V.append((xy[0], xy[1], float(zf(t, r, E)))); UV.append((t * E, r * 2.5))
        V = np.array(V); UV = np.array(UV)
        I = []
        for j in range(nr):
            for i in range(nt):
                a = j * (nt + 1) + i
                I += [[a, a + 1, a + nt + 2], [a, a + nt + 2, a + nt + 1]]
        I = np.array(I)
        fn = np.cross(V[I[:, 1]] - V[I[:, 0]], V[I[:, 2]] - V[I[:, 0]])
        if fn[:, 2].sum() < 0: I = I[:, ::-1]
        B.add(V, I, mat, UV=UV, smooth=True, tag=tag)
        # soffit: the same surface lowered by the edge thickness (seen from below)
        Vs = V.copy(); Vs[:, 2] -= th + 0.02
        B.add(Vs, I[:, ::-1], WD, UV=UV, smooth=True, tag=tag)
        # eave edge: shingle courses on top, the fascia (茅負 / 鼻隠) below
        top = np.array([(*pt(t, 0), float(zf(t, 0, E))) for t in ts])
        for (dz0, dz1, m) in ((0.0, th * 0.5, mat), (th * 0.5, th + 0.02, WD)):
            A_ = top - [0, 0, dz0]; B_ = top - [0, 0, dz1]
            PP = np.concatenate([A_, B_]); II = []
            n_ = len(ts)
            for i in range(n_ - 1):
                II += [[i, i + n_, i + 1], [i + 1, i + n_, i + n_ + 1]]
            II = np.array(II)
            f2 = np.cross(PP[II[:, 1]] - PP[II[:, 0]], PP[II[:, 2]] - PP[II[:, 0]])
            if (f2[:, :2] @ n_out).sum() < 0: II = II[:, ::-1]
            B.add(PP, II, m, UV=np.c_[np.r_[ts, ts] * E, PP[:, 2]], tag=tag)
        # rafters (垂木): along n_in from the edge to the wall line or the hip
        if rafter:
            for x in np.arange(rafter * 0.5, E, rafter):
                t = x / E
                a = P0 + dE * x
                # inward distance to the wall line along n_in
                if abs(n_in[0]) > 0.5: wall_r = abs(abs(a[0]) - uw) if abs(a[1]) <= vw else 9
                else: wall_r = abs(abs(a[1]) - vw) if abs(a[0]) <= uw else 9
                # hips: from P0 -> Q0 and P1 -> Q1; intersect the ray a + n_in * s
                best = wall_r
                for (H0, H1) in ((P0, Q0), (P1, Q1)):
                    dh = H1 - H0; M = np.array([[n_in[0], -dh[0]], [n_in[1], -dh[1]]])
                    if abs(np.linalg.det(M)) < 1e-9: continue
                    s_, u_ = np.linalg.solve(M, H0 - a)
                    if s_ > 0 and 0 <= u_ <= 1: best = min(best, s_ - 0.06)
                depth_total = float(np.dot(Q0 - P0, n_in))
                best = min(best, depth_total - 0.05)
                if best < 0.2: continue
                r0, r1 = 0.03 / depth_total, best / depth_total
                q0 = a + n_in * 0.03; q1 = a + n_in * best
                z0 = float(zf(t, r0, E)) - th - 0.07; z1 = float(zf(t, r1, E)) - th - 0.07
                prim.obox(B, (q0[0], q0[1], z0), (q1[0], q1[1], z1), 0.065, 0.085, WD, up=(0, 0, 1), tag='detail')
        hips.append((P0, Q0, k, E))
    # hip caps: a low rounded roll of shingles along each hip
    for (P0, Q0, k, E) in hips:
        pts = []
        for r in np.linspace(0, 1, 10):
            xy = P0 + (Q0 - P0) * r
            pts.append((xy[0], xy[1], float(zf(0.0, r, E)) + 0.02))
        prim.sweep(B, np.array(pts), [(-0.09, -0.04), (0.09, -0.04), (0.06, 0.05), (-0.06, 0.05)], mat, up=(0, 0, 1), tag=tag, caps=True)

# ------------------------------------------------------------------ 跳高欄 (railing whose top rail ends curl up past the corners)
def hane_koran(B, half, z, h=0.72, mat=WD, post_every=None, tag='main'):
    """a square railing at +-half (centred), floor z: corner posts, struts, 地覆 / 平桁 / 架木; the 架木 crosses at the corners
    and runs on 0.28 m with an upturned end"""
    c = [(-half, -half), (half, -half), (half, half), (-half, half)]
    for k in range(4):
        a = np.array(c[k], float); b = np.array(c[(k + 1) % 4], float)
        d = (b - a) / np.linalg.norm(b - a)
        # 地覆 and 平桁 between the corners
        for (zz, w, hh) in ((z + 0.05, 0.1, 0.1), (z + h * 0.5, 0.07, 0.08)):
            prim.obox(B, np.r_[a, zz], np.r_[b, zz], w, hh, mat, tag=tag)
        # 架木 (round top rail) with the ends past both corners curling up
        ext = 0.3
        pts = []
        for s in np.linspace(-ext, np.linalg.norm(b - a) + ext, 24):
            q = a + d * s
            over = max(0.0, -s, s - np.linalg.norm(b - a))
            pts.append((q[0], q[1], z + h + 0.9 * over ** 2 + 0.25 * over))
        prim.sweep(B, np.array(pts), [(0.04 * math.cos(t), 0.04 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 9)[:-1]], mat, up=(0, 0, 1), tag=tag, smooth=True)
        # struts (束) and small blocks under the top rail
        L = float(np.linalg.norm(b - a))
        for s in np.linspace(0, L, max(2, int(L / 0.95)) + 1)[1:-1]:
            q = a + d * s
            prim.obox(B, np.r_[q, z + 0.1], np.r_[q, z + h - 0.03], 0.06, 0.06, mat, tag='detail')
            prim.obox(B, np.r_[q - d * 0.07, z + h - 0.04], np.r_[q + d * 0.07, z + h - 0.04], 0.07, 0.05, mat, tag='detail')
    for (x, y) in c:
        prim.obox(B, (x, y, z), (x, y, z + h + 0.04), 0.1, 0.1, mat, tag=tag)

# ------------------------------------------------------------------ the phoenix (鳳凰)
def phoenix(B, x, y, z, s=0.9, yaw=0.0, mat='bronze', tag='main'):
    """a standing bronze phoenix, wings raised, long tail sweeping back and down; faces +x of its own frame"""
    with Frame(B, x, y, z, yaw):
        # legs
        for sy in (-0.06, 0.06):
            prim.cyl(B, (0.0, sy * s, 0.0), (0.02 * s, sy * s, 0.3 * s), 0.018 * s, 0.022 * s, 6, mat, tag=tag)
        # body: an egg tilted up
        body = []
        for (r, zz) in ((0.0, 0.26), (0.07, 0.27), (0.11, 0.33), (0.12, 0.42), (0.1, 0.5), (0.07, 0.56), (0.045, 0.62)):
            body.append((r * s, zz * s))
        P = []; I = []
        seg = 10
        for j, (r, zz) in enumerate(body):
            tilt = (zz - 0.26 * s) * 0.35          # the breast leans forward
            for i in range(seg):
                a = 2 * math.pi * i / seg
                P.append((tilt + r * math.cos(a) * 1.15, r * math.sin(a), zz))
        for j in range(len(body) - 1):
            for i in range(seg):
                a0 = j * seg + i; a1 = j * seg + (i + 1) % seg
                I += [[a0, a1, a1 + seg], [a0, a1 + seg, a0 + seg]]
        B.add(np.array(P), I, mat, smooth=True, tag=tag)
        # neck and head (S-curve) + beak + crest
        neck = np.array([(0.13, 0, 0.6), (0.17, 0, 0.7), (0.16, 0, 0.8), (0.2, 0, 0.87)]) * s
        prim.sweep(B, neck, [(0.035 * s * math.cos(t), 0.035 * s * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 7)[:-1]], mat, up=(0, 1, 0), tag=tag, smooth=True)
        prim.lathe(B, (0.2 * s, 0, 0.84 * s), [(0.0, 0.0), (0.045 * s, 0.03 * s), (0.05 * s, 0.06 * s), (0.03 * s, 0.09 * s), (0.0, 0.1 * s)], 8, mat, tag=tag)
        prim.cyl(B, (0.24 * s, 0, 0.89 * s), (0.31 * s, 0, 0.86 * s), 0.016 * s, 0.003 * s, 5, mat, tag=tag)
        for k in range(3):
            prim.obox(B, (0.19 * s, 0, 0.93 * s), ((0.12 - 0.04 * k) * s, 0, (1.02 + 0.02 * k) * s), 0.012 * s, 0.03 * s, mat, tag='detail')
        # wings: raised feather fans on both sides
        for sg in (-1, 1):
            for f in range(6):
                a = 0.25 + f * 0.17
                root = np.array([0.02, sg * 0.08, 0.5]) * s
                tip = root + np.array([-0.18 - 0.05 * f, sg * (0.08 + 0.02 * f), 0.2 + 0.22 * math.cos(a - 0.25)]) * s
                mid = (root + tip) / 2 + np.array([0.0, sg * 0.04, 0.03]) * s
                pts = np.array([root, mid, tip])
                prim.sweep(B, pts, [(-0.035 * s, -0.004 * s), (0.035 * s, -0.004 * s), (0.02 * s, 0.006 * s), (-0.02 * s, 0.006 * s)], mat, up=(0, sg, 0.3), tag=tag)
        # tail: long feathers sweeping back and down in an arc
        for f in range(7):
            ang = -0.2 + f * 0.13
            pts = []
            for t in np.linspace(0, 1, 7):
                rr = 0.15 + 0.5 * t
                pts.append((-0.08 - rr * math.cos(ang + t * 0.9) * 0.9, (f - 3) * 0.02 * t, 0.4 + rr * math.sin(ang + t * 0.9) * 0.6 - 0.25 * t * t))
            pts = np.array(pts) * s
            prim.sweep(B, pts, [(-0.03 * s, -0.004 * s), (0.03 * s, -0.004 * s), (0.02 * s, 0.006 * s), (-0.02 * s, 0.006 * s)], mat, up=(0, 1, 0), tag=tag)

# ------------------------------------------------------------------ the building
def build(B, S, gx, gy, gz):
    """gx, gy: the garden-local position of the centre; gz(x, y) ground (garden-local)"""
    z0 = float(gz(gx, gy)) - 0.05
    with Frame(B, gx, gy, z0, math.pi / 2):
        _build(B)
    return z0

def _build(B):
    FL = 0.6                     # 1F floor
    NG = FL + 1.8                # 内法 (head of the fittings)
    KB = FL + 2.45               # top of the 小壁 (bottom of the plate)
    PL = FL + 2.62               # top of the plate (桁)
    us = np.array([-4.1, -2.05, 0.0, 2.05, 4.1]); vs = np.array([-2.95, -0.983, 0.983, 2.95])
    bump = (2.05, 4.1, 2.95, 4.05)          # u0, u1, v0, v1
    # ---- foundation: stone curb, dark underfloor, floor slab edge
    out = [(-4.25, -3.1), (4.25, -3.1), (4.25, 3.1), (bump[1] + 0.15, 3.1)]
    ring = [(-4.25, -3.1), (4.25, -3.1), (4.25, bump[3] + 0.15), (bump[0] - 0.15, bump[3] + 0.15), (bump[0] - 0.15, 3.1), (-4.25, 3.1)]
    prim.prism(B, ring, -0.15, 0.12, 'stone')
    inner = [(-4.1, -2.95), (4.1, -2.95), (4.1, bump[3]), (bump[0], bump[3]), (bump[0], 2.95), (-4.1, 2.95)]
    prim.prism(B, [(x * 0.995, y * 0.995) for (x, y) in inner], 0.12, FL - 0.12, WD)
    prim.prism(B, inner, FL - 0.12, FL, WD, top=False)
    prim.polygon(B, inner, FL - 0.005, 'wood_natural', tag='walk')
    # ---- pillars
    pil = set()
    for u in us:
        for v in (vs[0], vs[-1]): pil.add((u, v))
    for v in vs:
        for u in (us[0], us[-1]): pil.add((u, v))
    pil |= {(bump[0], bump[3]), (bump[1], bump[3]), (bump[1], bump[2])}
    pil.discard((bump[1], vs[-1])); pil.add((bump[1], vs[-1]))
    for (u, v) in pil:
        top = PL if not (v > 3.0) else FL + 2.3
        prim.box(B, u - 0.085, v - 0.085, 0.1, u + 0.085, v + 0.085, top, WD)
    # ---- horizontal members on every outer wall line: 敷居 / 内法長押 / 小壁 band / 桁
    walls = [((-4.1, -2.95), (4.1, -2.95), (0, -1)), ((4.1, -2.95), (4.1, bump[3]), (1, 0)), ((4.1, bump[3]), (bump[0], bump[3]), (0, 1)),
             ((bump[0], bump[3]), (bump[0], 2.95), (-1, 0)), ((bump[0], 2.95), (-4.1, 2.95), (0, 1)), ((-4.1, 2.95), (-4.1, -2.95), (-1, 0))]
    for (a, b, n) in walls:
        bay = U.Bay(B, a, b, n)
        L = bay.L
        top = KB if not (abs(a[1] - bump[3]) < 0.01 and abs(b[1] - bump[3]) < 0.01) and not (abs(a[0] - bump[0]) < 0.01 and abs(b[0] - bump[0]) < 0.01) else FL + 2.1
        bay.box(-0.09, L + 0.09, FL - 0.12, FL + 0.04, -0.06, 0.07, WD)                  # 敷居 / 縁葛
        bay.box(-0.09, L + 0.09, NG, NG + 0.11, -0.04, 0.07, WD)                          # 内法長押
        if top > NG + 0.3:
            bay.plaster(0.09, L - 0.09, NG + 0.11, top, off=-0.02)                       # 小壁 (white)
        bay.box(-0.12, L + 0.12, top, top + 0.18, -0.08, 0.08, WD)                        # 桁 / 頭貫
    # ---- fittings, bay by bay
    def face(a, b, n, kinds):
        a = np.array(a, float); b = np.array(b, float); d = (b - a) / np.linalg.norm(b - a)
        L = np.linalg.norm(b - a); k = len(kinds)
        edges = np.linspace(0, L, k + 1)
        for i, kind in enumerate(kinds):
            p0 = a + d * edges[i]; p1 = a + d * edges[i + 1]
            bay = U.Bay(B, p0, p1, n)
            s0, s1 = 0.085, bay.L - 0.085
            z0, z1 = FL + 0.04, NG
            if kind == 'shoji': bay.shoji(s0, s1, z0, z1, 2, koshi=0.62, off=-0.03)
            elif kind == 'shoji_open': bay.shoji(s0, s1, z0, z1, 2, koshi=0.62, off=-0.03, open_=1); interior(bay, (s0 + s1) / 2, s1, z0, z1)
            elif kind == 'shoji_door':
                bay.shoji(s0, (s0 + s1) / 2, z0, z1, 1, koshi=0.62, off=-0.03)
                m = (s0 + s1) / 2
                bay.plane(m, s1, z0, z1 - 0.62, WD, off=-0.05)
                bay.koshi(m + 0.05, s1 - 0.05, z1 - 0.6, z1 - 0.05, off=-0.04, step=0.1)
                for zz in np.arange(z0 + 0.2, z1 - 0.65, 0.3): bay.box(m, s1, zz, zz + 0.03, -0.06, -0.03, WD, tag='detail')
            elif kind == 'lattice_shoji':
                m = s0 + (s1 - s0) * 0.32
                bay.plaster(s0, m, z0, z1 - 0.95, off=-0.04)
                bay.koshi(s0 + 0.03, m - 0.03, z1 - 0.95, z1 - 0.1, off=-0.04, step=0.07)
                bay.shoji(m, s1, z0, z1, 1, koshi=0.62, off=-0.03)
            elif kind == 'plaster': bay.plaster(s0, s1, z0, z1, off=-0.03)
            elif kind == 'board_door':
                bay.plaster(s0, s0 + 0.25, z0, z1, off=-0.03); bay.plaster(s1 - 0.25, s1, z0, z1, off=-0.03)
                bay.mairado(s0 + 0.25, s1 - 0.25, z0, z1 - 0.25, 2, off=-0.04)
                bay.plaster(s0 + 0.25, s1 - 0.25, z1 - 0.25, z1, off=-0.03)
    face((-4.1, -2.95), (4.1, -2.95), (0, -1), ['shoji_door', 'shoji', 'shoji_open', 'lattice_shoji'])
    face((-4.1, 2.95), (-4.1, -2.95), (-1, 0), ['shoji', 'shoji', 'shoji'])
    face((bump[0], 2.95), (-4.1, 2.95), (0, 1), ['shoji', 'plaster', 'shoji'])
    face((4.1, -2.95), (4.1, bump[3]), (1, 0), ['plaster', 'plaster', 'plaster', 'plaster'])
    face((bump[1], bump[3]), (bump[0], bump[3]), (0, 1), ['board_door'])
    face((bump[0], bump[3]), (bump[0], 2.95), (-1, 0), ['plaster'])
    # ---- veranda (落縁) on the east + 沓脱石, and the pent roof over the bump
    prim.box(B, -4.2, -3.92, FL - 0.17, 4.2, -2.95, FL - 0.1, 'eave_wood')
    for u in np.linspace(-4.15, 4.15, 6): prim.box(B, u - 0.06, -3.88, 0.05, u + 0.06, -3.76, FL - 0.17, WD, tag='detail')
    prim.box(B, -4.2, -3.92, FL - 0.3, 4.2, -3.84, FL - 0.17, WD)
    for u in np.arange(-4.15, 4.2, 0.25): prim.box(B, u - 0.01, -3.93, FL - 0.17, u + 0.01, -2.96, FL - 0.162, WD, tag='detail')
    prim.polygon(B, [(-4.2, -3.92), (4.2, -3.92), (4.2, -2.95), (-4.2, -2.95)], FL - 0.1, 'wood_natural', tag='walk')
    prim.box(B, -1.6, -4.75, -0.1, 2.1, -4.0, 0.3, 'stone')                           # 沓脱石
    prim.polygon(B, [(-1.6, -4.75), (2.1, -4.75), (2.1, -4.0), (-1.6, -4.0)], 0.3, 'stone', tag='walk')
    pz0, pz1 = FL + 2.38, FL + 2.08
    U.quad(B, (bump[0] - 0.25, 2.95, pz0), (bump[0] - 0.25, bump[3] + 0.45, pz1), (bump[1] + 0.25, bump[3] + 0.45, pz1), (bump[1] + 0.25, 2.95, pz0), 'hiwada', out=(0, 0, 1))
    U.quad(B, (bump[0] - 0.25, 2.95, pz0 - 0.12), (bump[1] + 0.25, 2.95, pz0 - 0.12), (bump[1] + 0.25, bump[3] + 0.45, pz1 - 0.12), (bump[0] - 0.25, bump[3] + 0.45, pz1 - 0.12), WD, out=(0, 0, -1))
    for (u_, sg) in ((bump[0] - 0.25, -1), (bump[1] + 0.25, 1)):
        U.quad(B, (u_, 2.95, pz0 - 0.12), (u_, bump[3] + 0.45, pz1 - 0.12), (u_, bump[3] + 0.45, pz1), (u_, 2.95, pz0), WD, out=(sg, 0, 0))
    prim.obox(B, (bump[0] - 0.25, bump[3] + 0.45, pz1 - 0.06), (bump[1] + 0.25, bump[3] + 0.45, pz1 - 0.06), 0.06, 0.13, WD)
    # ---- lower roof (skirt) up to the upper storey's base
    Z_EDGE, Z_TOP, Z_DECK = 3.15, 4.22, 4.5
    # the wall above the plate on the east and west, up to the skirt's soffit (which meets these walls higher than the N / S ones)
    for (v, us_) in ((-2.95, [(-4.1, 4.1, PL + 0.16)]), (2.95, [(-4.1, bump[0], PL + 0.16), (bump[0], bump[1], FL + 2.25)])):
        for (u0, u1, z0_) in us_:
            U.quad(B, (u0, v, z0_), (u1, v, z0_), (u1, v, 3.86), (u0, v, 3.86), 'temple_wall', out=(0, np.sign(v), 0), c0=(236, 232, 222, 35))
    skirt_roof(B, 5.35, 4.2, 2.9, 2.9, Z_EDGE, Z_TOP, 4.1, 2.95, teri=1.45, sori=0.3, sori_len=1.0, th=0.32, mat='hiwada', rafter=0.3)
    # 腰組: the base of the upper storey, brackets under the veranda
    prim.prism(B, [(-2.9, -2.9), (2.9, -2.9), (2.9, 2.9), (-2.9, 2.9)], Z_TOP - 0.15, Z_DECK - 0.12, WD, top=False)
    prim.prism(B, [(-2.95, -2.95), (2.95, -2.95), (2.95, 2.95), (-2.95, 2.95)], Z_DECK - 0.42, Z_DECK - 0.3, WD, top=False)
    up_ = np.array([-2.8, -0.933, 0.933, 2.8])
    for x in up_:
        for (sx, sy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if sx: a = np.array([sx * 2.9, x]); b = np.array([sx * 3.55, x])
            else: a = np.array([x, sy * 2.9]); b = np.array([x, sy * 3.55])
            prim.obox(B, np.r_[a, Z_DECK - 0.2], np.r_[b, Z_DECK - 0.2], 0.12, 0.16, WD, tag='detail')
            prim.box(B, b[0] - 0.08, b[1] - 0.08, Z_DECK - 0.3, b[0] + 0.08, b[1] + 0.08, Z_DECK - 0.12, WD, tag='detail')
            q = (a + b) / 2
            prim.obox(B, np.r_[a, Z_DECK - 0.38], np.r_[q, Z_DECK - 0.27], 0.1, 0.1, WD, tag='detail')
    # ---- upper veranda: deck, fascia, railing
    D = 3.62
    prim.box(B, -D - 0.05, -D - 0.05, Z_DECK - 0.12, D + 0.05, D + 0.05, Z_DECK, 'eave_wood')
    prim.prism(B, [(-D - 0.08, -D - 0.08), (D + 0.08, -D - 0.08), (D + 0.08, D + 0.08), (-D - 0.08, D + 0.08)], Z_DECK - 0.26, Z_DECK - 0.1, WD, top=False, bottom=True)
    for x in np.arange(-D, D, 0.22): prim.box(B, x - 0.006, -D - 0.05, Z_DECK, x + 0.006, -2.8, Z_DECK + 0.004, WD, tag='detail')
    prim.polygon(B, [(-D, -D), (D, -D), (D, D), (-D, D)], Z_DECK + 0.005, 'wood_natural', tag='walk')
    hane_koran(B, D - 0.05, Z_DECK, 0.58)
    # railing blocker
    for (a, b) in (((-D, -D), (D, -D)), ((D, -D), (D, D)), ((D, D), (-D, D)), ((-D, D), (-D, -D))):
        prim.obox(B, np.r_[a, Z_DECK + 0.45], np.r_[b, Z_DECK + 0.45], 0.12, 0.9, 'stone', tag='block')
    # ---- upper storey 潮音閣
    H2 = 1.9                                      # floor to the top of the 頭貫
    TOP2 = Z_DECK + H2
    hw = 2.8
    for x in up_:
        for y in (-hw, hw):
            for (px, py) in ((x, y), (y, x)):
                prim.cyl(B, (px, py, Z_DECK), (px, py, TOP2), 0.105, 0.1, 12, WD, caps=(False, True))
    prim.polygon(B, [(-hw, -hw), (hw, -hw), (hw, hw), (-hw, hw)], Z_DECK + 0.01, 'eave_wood')
    side = [(((-hw, -hw), (hw, -hw)), (0, -1), ['kato', 'kato', 'kato']),           # east (front)
            (((hw, hw), (-hw, hw)), (0, 1), ['kato', 'kato', 'kato']),               # west
            (((-hw, hw), (-hw, -hw)), (-1, 0), ['kato', 'door', 'kato']),            # south
            (((hw, -hw), (hw, hw)), (1, 0), ['board', 'door', 'board'])]             # north
    for ((a, b), n, kinds) in side:
        a = np.array(a, float); b = np.array(b, float); d = (b - a) / np.linalg.norm(b - a)
        L = np.linalg.norm(b - a)
        full = U.Bay(B, a, b, n)
        full.box(-0.12, L + 0.12, Z_DECK, Z_DECK + 0.16, -0.07, 0.06, WD)                         # 地覆
        full.box(-0.12, L + 0.12, Z_DECK + 0.7, Z_DECK + 0.8, -0.05, 0.06, WD)                    # 腰貫
        full.box(-0.12, L + 0.12, TOP2 - 0.22, TOP2 - 0.02, -0.06, 0.07, WD)                     # 頭貫
        full.box(-0.3, L + 0.3, TOP2 - 0.02, TOP2 + 0.12, -0.12, 0.12, WD)                       # 台輪 (ends proud)
        for i, kind in enumerate(kinds):
            p0 = a + d * (L * i / 3); p1 = a + d * (L * (i + 1) / 3)
            bay = U.Bay(B, p0, p1, n)
            s0, s1 = 0.1, bay.L - 0.1
            if kind == 'kato':
                bay.katomado(s0, s1, Z_DECK + 0.16, TOP2 - 0.22, wz=(0.58, 1.45), ww=0.82, off=-0.02)
            elif kind == 'door':
                bay.karado(s0 + 0.05, s1 - 0.05, Z_DECK + 0.16, Z_DECK + 1.6, off=-0.03, lattice=0.5)
                bay.boards(s0, s1, Z_DECK + 1.6, TOP2 - 0.22, off=-0.02, batten=0)
                bay.box(s0, s1, Z_DECK + 1.6, Z_DECK + 1.68, -0.06, 0.04, WD)
            else:
                bay.boards(s0, s1, Z_DECK + 0.16, TOP2 - 0.22, off=-0.02)
    # ---- bracket sets (dense row) and the roof
    rows = np.linspace(-hw, hw, 7)
    top, reach = arch.bracket_row(B, 2 * hw, 2 * hw, TOP2 + 0.12, 'demitsudo', 0.5, WD, us=rows, vs=rows)
    c_out = 4.6                                                  # half size of the eave outline (9.2 m square)
    Lr = 2 * (hw + reach); o = c_out - Lr / 2
    Z_E2, Z_APEX = 6.7, 9.3
    ZR = top + 0.4                                 # roof surface over the purlin: its thickness sits on the brackets
    Hh = Z_APEX - Z_E2
    teri = math.log(max(0.05, (ZR - Z_E2)) / Hh) / math.log(o / c_out)
    teri = float(np.clip(teri, 1.2, 2.6))
    print(f'ginkaku: bracket top {top:.2f} reach {reach:.2f} overhang {o:.2f} teri {teri:.2f}')
    r = jroof.Roof(Lr, Lr, ZR, o, kind='hogyo', cover='kokera', pitch=Hh / c_out, teri=teri, sori=0.4, sori_len=1.0, edge=0.36,
                   rafter=0.26, tiers=2, rafter_mat=WD, rafter_end=WD, ends=None, hip=False, top=[(0.001, 0.0), (0.0, 0.002)])
    info = r.build(B)
    za = info['z_ridge']
    # close the eaves above the bracket row: boards between the sets at the wall line, a ceiling ring out to the soffit
    for k in range(4):
        ang = k * math.pi / 2
        cs, sn = math.cos(ang), math.sin(ang)
        rot = lambda x, y: (x * cs - y * sn, x * sn + y * cs)
        a = rot(-hw - 0.05, -hw + 0.02); b = rot(hw + 0.05, -hw + 0.02)
        U.quad(B, (*a, TOP2 + 0.1), (*b, TOP2 + 0.1), (*b, top + 0.12), (*a, top + 0.12), WD, out=(*rot(0, -1), 0))
        r0, r1 = hw - 0.05, Lr / 2 + 0.05
        U.quad(B, (*rot(-r0, -r0), top + 0.06), (*rot(r0, -r0), top + 0.06), (*rot(r1, -r1), top + 0.06), (*rot(-r1, -r1), top + 0.06), WD, out=(0, 0, -1))
    # hip rolls in shingle
    for k in range(4):
        hl = r.hip_line(k, c_out * 0.97, n=14, off=0.03)
        prim.sweep(B, hl, [(-0.1, -0.04), (0.1, -0.04), (0.07, 0.06), (-0.07, 0.06)], 'hiwada', up=(0, 0, 1), caps=True)
    # 露盤 (box) on a wooden plinth + the phoenix
    prim.box(B, -0.46, -0.46, za - 0.25, 0.46, 0.46, za + 0.06, WD)
    prim.box(B, -0.34, -0.34, za + 0.06, 0.34, 0.34, za + 0.34, 'metal_dark')
    prim.box(B, -0.37, -0.37, za + 0.33, 0.37, 0.37, za + 0.38, 'metal_dark')
    phoenix(B, 0.0, 0.0, za + 0.38, s=0.82, yaw=-math.pi / 2)      # facing east (-v)
    return za

def interior(bay, s0, s1, z0, z1):
    """a glimpse of a room behind an open panel: tatami, a white back wall, a dark ceiling"""
    dpt = 1.6
    a = bay.P(s0, 0, -0.05); b = bay.P(s1, 0, -0.05)
    a2 = bay.P(s0, 0, -dpt); b2 = bay.P(s1, 0, -dpt)
    U.quad(bay.B, (a[0], a[1], z0 - 0.02), (b[0], b[1], z0 - 0.02), (b2[0], b2[1], z0 - 0.02), (a2[0], a2[1], z0 - 0.02), 'tatami', out=(0, 0, 1))
    bay.plaster(s0, s1, z0, z1 + 0.3, off=-dpt, tint=(220, 214, 200))
    U.quad(bay.B, (a[0], a[1], z1 + 0.05), (a2[0], a2[1], z1 + 0.05), (b2[0], b2[1], z1 + 0.05), (b[0], b[1], z1 + 0.05), 'wood_natural', out=(0, 0, -1))
    for s in (s0, s1):
        p = bay.P(s, 0, -0.05); q = bay.P(s, 0, -dpt)
        U.quad(bay.B, (p[0], p[1], z0), (q[0], q[1], z0), (q[0], q[1], z1 + 0.05), (p[0], p[1], z1 + 0.05), 'temple_wall', both=True, c0=(226, 220, 206, 35))
