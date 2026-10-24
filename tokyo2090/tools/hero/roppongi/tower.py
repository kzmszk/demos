"""Roppongi Hills Mori Tower: rounded armour-plate plan with overlapping curved bays and vertical fins,
crown with the glass gallery (Tokyo City View) and Sky Deck.  Ruin: crown and upper floors torn open on the
W-NW-N side (lit by the low WSW sun, seen in silhouette from 66 Plaza), fins peeled and hanging, slabs exposed."""
import math
import numpy as np
import lib
from lib import vnoise, fbm, norm

C = np.array([-49.6, 49.4])
Z0 = 19.6
ZR = 263.0          # main roof
NF = 54 if not lib.mid() else 27
FH = (ZR - Z0) / NF
NB = 28             # curved bays around
# radial samples of the PLATEAU outline (deg -> m), smoothed by a Fourier fit
_RAD = [39.75, 39.75, 42.0, 45.75, 49.25, 48.5, 44.75, 42.25, 40.0, 41.0, 44.5, 45.0, 41.5, 40.75, 42.0, 45.25,
        48.5, 48.5, 45.0, 42.5, 40.0, 42.25, 46.0, 46.0]


def _fourier():
    a = np.radians(np.arange(0, 360, 15))
    r = np.array(_RAD)
    co = [r.mean()]
    for k in range(1, 5):
        co.append((2 * np.mean(r * np.cos(k * a)), 2 * np.mean(r * np.sin(k * a))))
    def R(t):
        v = co[0]
        for k in range(1, 5):
            v = v + co[k][0] * np.cos(k * t) + co[k][1] * np.sin(k * t)
        return v - 1.0
    return R


Rbase = _fourier()
TEARS = [  # (centre azimuth deg (math angle, ccw from east), half width deg, depth m)
    (156.0, 78.0, 128.0),    # the big bite: NW..W..WSW, faces Shinjuku and Shibuya, lit by the low WSW sun
    (228.0, 22.0, 60.0),     # a second deep gash on the SW (Shibuya side)
    (318.0, 16.0, 17.0),     # a bitten corner on the SE so the crown reads broken from Keyakizaka too
]


def tear_depth(t):
    """how far down from the roof the tear reaches at azimuth t (m), 0 outside"""
    best = 0.0
    for k, (c, w, dep) in enumerate(TEARS):
        d = math.atan2(math.sin(t - math.radians(c)), math.cos(t - math.radians(c)))
        x = abs(d) / math.radians(w)
        if x >= 1:
            continue
        base = (1 - x ** 1.5) * dep + (1 - x) * 8.0
        j = (vnoise(t * 9.0, 3.0 + k, 71) - 0.5) * dep * 0.25 + (vnoise(t * 31.0, 7.0 + k, 72) - 0.5) * 5.0
        best = max(best, base + j * (1 - x * 0.5))
    return best


def cut_at(t):
    return ZR + 3.0 - tear_depth(t)


def outline(nper=None):
    nper = nper or (10 if not lib.mid() else 4)
    """bay outline points: list of (pt2, t, bay index, frac).  Bays are convex arcs; each bay ends proud of
    the next by STEP, so the facade reads as overlapping plates."""
    STEP = 2.3; BULGE = 1.9
    pts = []
    for i in range(NB):
        t0 = 2 * math.pi * i / NB; t1 = 2 * math.pi * (i + 1) / NB
        for k in range(nper + 1):
            f = k / nper
            t = t0 + (t1 - t0) * f
            r = Rbase(t) + BULGE * math.sin(math.pi * f) + STEP * f
            pts.append((C + r * np.array([math.cos(t), math.sin(t)]), t, i, f))
    return pts


def build(sc, col, ctx):
    rr = lib.rng(4242)
    W = sc['tower']; S = sc['tconc']; I = sc['interior']; M = sc['metal']
    pts = outline()
    n = len(pts)
    # ---------------- curtain wall
    s_acc = [0.0]
    for k in range(1, n):
        s_acc.append(s_acc[-1] + float(np.linalg.norm(pts[k][0] - pts[k - 1][0])))
    from ruins import row_uv, FAC_ROWS
    floor_open = {}
    for k in range(n - 1):
        (p0, t0, b0, f0), (p1, t1, b1, f1) = pts[k], pts[k + 1]
        if b0 != b1:
            continue
        s0, s1 = s_acc[k], s_acc[k + 1]
        tm = 0.5 * (t0 + t1)
        c0, c1 = cut_at(t0), cut_at(t1)
        for j in range(NF + 1):
            zb = Z0 + j * FH; zt = zb + FH
            if j == NF:   # parapet of the crown (glass gallery rail) 3 m
                zt = zb + 3.0
            if zb >= max(c0, c1) - 0.3:
                break
            near = max(0.0, 1 - (min(c0, c1) - zt) / 14.0)
            crown = j >= NF - (5 if not lib.mid() else 2)
            hn = vnoise(tm * 14.0, zb / 9.0, 91)
            west = max(0.0, math.cos(tm - math.radians(165)))
            if near > 0 and hn < 0.25 + 0.5 * near:
                floor_open[j] = True
                continue
            # the west face below the bite is blown out in irregular patches (floors visible far below the tear)
            if zb > 95 and hn < 0.16 * west * min(1.0, (zb - 95) / 60) and j < NF - 1:
                floor_open[j] = True
                continue
            if crown:
                row = 'glass' if rr.random() > 0.3 + near else 'glass_ruin'
            else:
                # clustered broken panes (dark bands of empty floors), heavier on the west, not a uniform grid
                cl = vnoise(tm * 7.0, zb / 22.0, 93)
                row = 'mori_ruin' if (rr.random() < 0.06 + 0.7 * near or cl > 0.68 - 0.25 * west or
                                      (zb < 32 and rr.random() < 0.5)) else 'mori'
            t0z = min(zt, max(zb, c0)); t1z = min(zt, max(zb, c1))
            if max(t0z, t1z) - zb < 0.4:
                continue
            fz = (zt - zb)
            fo = 6.4 * int(float(lib._hash(77, j)) * 5)
            uv = row_uv(row, s0 + fo, s1 + fo, (0, 0), ((t1z - zb) / fz, (t0z - zb) / fz))
            W.poly([(p0[0], p0[1], zb), (p1[0], p1[1], zb), (p1[0], p1[1], t1z), (p0[0], p0[1], t0z)], uv)
    # notch faces between bays (radial step) + fins
    crown_tips = []
    for i in range(NB):
        kA = i * (len(pts) // NB) + (len(pts) // NB - 1)    # last point of bay i
        kB = (kA + 1) % n                                      # first point of bay i+1
        pA, tA = pts[kA][0], pts[kA][1]; pB = pts[kB][0]
        c = cut_at(tA)
        ztop = min(ZR + 3.0, c)
        # notch face
        _fin(W, pB, norm(pA - pB), float(np.linalg.norm(pA - pB)), Z0, ztop, 0.01)
        # fins: a deep blade at every notch (rising 9 m above the roof as the crown comb) and a shallow one mid-bay
        out = norm(pA - C)
        intact = tear_depth(tA) < 1
        fin_top = ZR + 9.0 if intact else ztop - rr.uniform(0, 8)
        _fin(W, pA, out, 2.6, Z0 + 6.0, fin_top, 0.22)
        kM = i * (len(pts) // NB) + (len(pts) // NB) // 2
        pM, tM = pts[kM][0], pts[kM][1]
        outM = norm(pM - C)
        topM = ZR + 3.2 if tear_depth(tM) < 1 else cut_at(tM) - rr.uniform(0, 5)
        if not lib.mid():
            _fin(W, pM, outM, 1.0, Z0 + 6.0, topM, 0.12)
        crown_tips.append((pA + out * 2.6, intact))
        tan = np.array([-out[1], out[0]])
        # peeled fins: in the tear zone a blade hangs off, bent outward and down
        westA = max(0.0, math.cos(tA - math.radians(160)))
        if (0 < tear_depth(tA) or rr.random() < 0.5 * westA) and rr.random() < (1.0 if not lib.mid() else 0.5):
            zatt = (c - rr.uniform(2, 10)) if tear_depth(tA) > 0 else rr.uniform(110, ZR - 20)
            L = rr.uniform(12, 30)
            path = []
            ang0 = rr.uniform(0.3, 0.9)
            for q in range(9):
                f = q / 8
                ang = ang0 + f * rr.uniform(0.8, 1.6)      # bending outward then down
                path.append(pA + out * (0.5 + math.sin(ang) * L * f * 0.6))
                path[-1] = np.array([path[-1][0], path[-1][1], zatt - math.cos(ang) * L * f])
            for q in range(8):
                a3 = path[q]; b3 = path[q + 1]
                w = 0.8
                M.poly([a3 - np.r_[tan * w, 0], b3 - np.r_[tan * w, 0], b3 + np.r_[tan * w, 0], a3 + np.r_[tan * w, 0]],
                       [(0, q / 2), (0, (q + 1) / 2), (0.4, (q + 1) / 2), (0.4, q / 2)])
    if 'occ' in ctx:
        ctx['occ'].fill_poly([p[0] for p in pts[::3]], 1)
    # crown ring beams (top of the comb + Sky Deck rail), broken where the tear is
    for zr_, off, rad in ((ZR + 8.6, 0.0, 0.35), (ZR + 3.0, -1.6, 0.18)):
        run = []
        for (p, ok) in crown_tips + crown_tips[:1]:
            if ok:
                run.append(np.r_[p + norm(p - C) * off, zr_])
            else:
                if len(run) > 1:
                    lib.tube(M, run, [rad] * len(run), sides=4)
                run = []
        if len(run) > 1:
            lib.tube(M, run, [rad] * len(run), sides=4)
    # ---------------- slabs: full plates only near the tear (bitten), roof, crown floors
    ring = [p[0] for p in pts]
    slab_regs = {}
    edge_pts = []
    tring = [p[1] for p in pts]
    core_w, core_d = 30.0, 26.0
    for j in range(1, NF + 1):
        z = Z0 + j * FH
        reg = []
        bit = False
        for p, t in zip(ring, tring):
            d = z - cut_at(t)
            if d > -1.0:
                bit = True
                r = np.linalg.norm(p - C)
                depth = min(r * 0.78, (d + 1.0) * 0.55 + 2.0 + (vnoise(t * 20, z * 0.3, 5) - 0.5) * 4)
                p = C + (p - C) * (1 - depth / r)
                edge_pts.append((p, t, z))
            reg.append(p)
        if not (bit or j == NF or j in floor_open):
            continue
        # thin out the ring for slabs (every 2nd point)
        reg = reg[::3]
        if not bit and j != NF:
            reg = reg[::2]
        mat_top = 'top' if (bit or j == NF) else 'interior'
        _slab(sc, reg, z, 0.45, mat_top)
        if bit:
            slab_regs[j] = reg
        if bit or j == NF:
            col.top(reg, z)
        # sagging slab fragments at the bite edge
        if bit and j < NF and rr.random() < 0.55 and not lib.mid():
            k0 = rr.randrange(len(reg))
            t = tring[(k0 * 2) % len(tring)]
            if tear_depth(t) > 5:
                p = reg[k0]; q = reg[(k0 + 1) % len(reg)]
                out = norm(np.r_[(p + q) / 2 - C, 0])
                sag = rr.uniform(0.6, 1.3); L = rr.uniform(3, 7)
                dv = out * math.cos(sag) * L + np.array([0, 0, -math.sin(sag) * L])
                a3 = np.r_[p, z]; b3 = np.r_[q, z]
                S.poly([a3, b3, b3 + dv, a3 + dv], [(0, 0), (1, 0), (1, 1), (0, 1)])
                S.poly([a3 + dv, b3 + dv, b3, a3], [(0, 0), (1, 0), (1, 1), (0, 1)])
                # rebar whiskers
                for w in range(6):
                    f = rr.random()
                    s = a3 + (b3 - a3) * f + dv
                    M.poly([s, s + np.array([0.05, 0.05, 0]), s + dv * 0.25 + np.array([0.05, 0.05, -0.6]), s + dv * 0.25 + np.array([0, 0, -0.6])])
    # exposed structure in the tear: columns between the bitten slabs, curtain-wall sheets peeled off the edge
    if not lib.mid():
        grid = []
        for gx in np.arange(-36, 37, 9.0):
            for gy in np.arange(-36, 37, 9.0):
                p = C + np.array([gx, gy])
                t = math.atan2(gy, gx)
                if 0.0 < tear_depth(t) and np.hypot(gx, gy) < Rbase(t) - 2.5 and np.hypot(gx, gy) > 12:
                    grid.append(p)
        for j, reg in slab_regs.items():
            z = Z0 + j * FH
            if j + 1 > NF:
                continue
            for p in grid:
                if lib.point_in_poly(p[0], p[1], reg) and rr.random() < 0.8:
                    hgt = FH - 0.45 if (j + 1) in slab_regs and lib.point_in_poly(p[0], p[1], slab_regs[j + 1]) else rr.uniform(0.8, 3.0)
                    lib.box(S, (p[0], p[1], z), (0.9, 0.9, hgt), 0.0, uvscale=0.25)
        # peeled curtain-wall sheets hanging from the torn edge
        for k in range(0, n - 1, 3):
            p0, t0 = pts[k][0], pts[k][1]
            if tear_depth(t0) < 4 or rr.random() < 0.45:
                continue
            p1 = pts[k + 1][0]
            zc = cut_at(t0) - rr.uniform(0.0, 3.0)
            out = norm(np.r_[(p0 + p1) / 2 - C, 0.0])
            Lh = rr.uniform(4.0, 13.0); ang = rr.uniform(0.15, 0.7)
            dv = out * math.sin(ang) * Lh + np.array([0, 0, -math.cos(ang) * Lh])
            w = rr.uniform(2.5, 5.0)
            tn = norm(np.r_[p1 - p0, 0.0])
            A = np.r_[p0, zc]; B = A + tn * w
            row = rr.choice(['mori', 'mori_ruin'])
            from ruins import row_uv
            uv = row_uv(row, 0.0, w)
            W.poly([A + dv, B + dv, B, A], [uv[0], uv[1], (uv[2][0], uv[0][1] + (uv[2][1] - uv[0][1]) * min(1, Lh / FH)), (uv[3][0], uv[0][1] + (uv[3][1] - uv[0][1]) * min(1, Lh / FH))])
    # green spilling from the torn floors: shrubs along every bitten slab edge, saplings, vines over the edge
    import veg
    Fh = sc['foliage_high']
    keep = 1.0 if not lib.mid() else 0.25
    for (p, t, z) in edge_pts[::2]:
        if rr.random() > keep:
            continue
        inward = norm(C - p)
        out2 = -inward
        if rr.random() < 0.55:
            q = p + inward * rr.uniform(0.5, 3.0)
            veg.bush(Fh, (q[0], q[1], z), rr.uniform(0.9, 2.2), rr)
        if rr.random() < 0.10:
            q = p + inward * rr.uniform(2.0, 6.0)
            veg.tree(sc, col, (q[0], q[1], z), rr.choice(['young', 'fig']), rr.uniform(3, 7), rr.uniform(2, 3.5),
                     rr.randrange(1 << 30), 'foliage_high', collide=False)
        if rr.random() < 0.38:
            veg.hang(Fh, (p[0], p[1], z + 0.2), out2, rr.uniform(2.5, 5.0), rr.uniform(8, 45) if rr.random() < 0.5 else rr.uniform(4, 14),
                     rr.choice(['vine', 'vine2']), 1.0, rr.randrange(1 << 30))
    # the face below the bite: peeled curtain-wall sheets hanging off floor edges, weathering streaks, long vines
    W2 = sc['decal_ground']
    from decals import cuv
    from ruins import row_uv
    nstreak = 0
    for k in range(0, n - 4, 2):
        p0, t0 = pts[k][0], pts[k][1]
        west = max(0.0, math.cos(t0 - math.radians(160)))
        cz = cut_at(t0)
        # streaks: from the crown / tear edge down, everywhere but denser on the west
        if rr.random() < (0.22 + 0.35 * west) * (1.0 if not lib.mid() else 0.5):
            kk = min(n - 1, k + rr.randrange(2, 5))
            if pts[kk][2] != pts[k][2]:
                kk = k + 1
            ztop = min(ZR + 2.0, cz) - rr.uniform(0.0, 40.0 if rr.random() < 0.5 else 6.0)
            L = rr.uniform(18, 75)
            strip = [pts[q][0] + norm(pts[q][0] - C) * 0.07 for q in range(k, kk + 1)]
            for q in range(len(strip) - 1):
                a3, b3 = strip[q], strip[q + 1]
                fu0, fu1 = q / (len(strip) - 1), (q + 1) / (len(strip) - 1)
                W2.poly([(a3[0], a3[1], ztop - L), (b3[0], b3[1], ztop - L), (b3[0], b3[1], ztop), (a3[0], a3[1], ztop)],
                        [cuv('streak', fu0, 0.0), cuv('streak', fu1, 0.0), cuv('streak', fu1, 1.0), cuv('streak', fu0, 1.0)])
            nstreak += 1
        if lib.mid():
            continue
        # hanging sheets
        if rr.random() < 0.30 * west:
            p1 = pts[k + 1][0]
            jz = rr.randrange(int((110 - Z0) / FH), NF - 2)
            zc = min(Z0 + jz * FH, cz - 2)
            out = norm(np.r_[(p0 + p1) / 2 - C, 0.0])
            Lh = rr.uniform(4.0, 14.0); ang = rr.uniform(0.08, 0.5)
            dv = out * math.sin(ang) * Lh + np.array([0, 0, -math.cos(ang) * Lh])
            tn = norm(np.r_[p1 - p0, 0.0]); w = rr.uniform(3.0, 6.0)
            A = np.r_[p0, zc] + out * 0.15; B = A + tn * w
            uv = row_uv(rr.choice(['mori', 'mori_ruin']), 0.0, w)
            fr = min(1.0, Lh / FH)
            W.poly([A + dv, B + dv, B, A], [uv[0], uv[1], (uv[2][0], uv[0][1] + (uv[2][1] - uv[0][1]) * fr),
                                            (uv[3][0], uv[0][1] + (uv[3][1] - uv[0][1]) * fr)])
        # long vine curtains from the bite down the west face
        if tear_depth(t0) > 3 and rr.random() < 0.35:
            veg.hang(Fh, (p0[0], p0[1], cz - rr.uniform(0, 4)), norm(p0 - C), rr.uniform(3.0, 6.0),
                     rr.uniform(20, 70), rr.choice(['vine', 'vine2']), 1.0, rr.randrange(1 << 30))
    # green on the setbacks: the Sky Deck block and the crown rim
    for k in range(40 if not lib.mid() else 10):
        a_ = rr.uniform(0, 2 * math.pi); r_ = rr.uniform(4, 34)
        q = C + np.array([2.0, -1.0]) + np.array([math.cos(a_), math.sin(a_)]) * r_
        tq = math.atan2(q[1] - C[1], q[0] - C[0])
        if tear_depth(tq) > 1:
            continue
        zq = 269.5 if (abs(q[0] - C[0] - 2) < 19 and abs(q[1] - C[1] + 1) < 23) else ZR
        veg.bush(Fh, (q[0], q[1], zq), rr.uniform(1.0, 2.6), rr)
    # roof: Sky Deck, helipad block, crown rail
    roof_reg = []
    for p, t in zip(ring[::2], tring[::2]):
        if tear_depth(t) > 1.0:
            continue
        roof_reg.append(p)
    # central roof block (gallery/helipad) 269, offset NE like PLATEAU's 269 region
    hc = C + np.array([2.0, -1.0])
    zc_top = 269.5
    blk = [hc + np.array(v) for v in ((-20, -24), (20, -24), (22, 0), (20, 24), (-20, 24), (-22, 0))]
    # the tear eats the W part of the block too
    blk2 = []
    for p in blk:
        t = math.atan2(p[1] - C[1], p[0] - C[0])
        if tear_depth(t) > 25:
            p = C + (p - C) * 0.35
        blk2.append(p)
    _prism(sc, blk2, ZR, zc_top, 'tconc', 'top')
    col.top(blk2, zc_top)
    # helipad H-ring on top: low ring
    lib.tube(M, [np.r_[hc + 9 * np.array([math.cos(a), math.sin(a)]), zc_top + 0.6] for a in np.linspace(0, 2 * math.pi, 25)],
             [0.12] * 25, sides=4)
    # stair/lift core rising out of the tear
    core_top = ZR + 5.5
    for (dx, dy, w, d) in ((-6, 4, 12, 10), (8, -6, 10, 12)):
        cc = C + np.array([dx, dy])
        lib.box(S, (cc[0], cc[1], Z0), (w, d, core_top - Z0 - rr.uniform(0, 9)), 0.0, uvscale=0.25)
    col.box((C[0] - 6, C[1] + 4, Z0), (12, 10, core_top - Z0 - 4.0))
    # collision: the tower mass (roof plate where intact)
    col.top(roof_reg, ZR)
    # ---------------- vegetation spills: anchors for vines and trees (consumed by veg.py)
    anchors = []
    for j in range(NF - 16, NF + 1):
        z = Z0 + j * FH
        for p, t in zip(ring[::6], tring[::6]):
            if 1.0 < tear_depth(t) and abs(z - cut_at(t)) < FH * 1.5:
                anchors.append((float(p[0]), float(p[1]), float(z), float(t)))
    ctx.setdefault('vine_anchors', []).extend([(a[0], a[1], a[2], math.cos(a[3]), math.sin(a[3])) for a in anchors])
    ctx['tower_top'] = ZR
    ctx['tower_center'] = C
    ctx['tower_R'] = Rbase


def _fin(M, p, out, depth, z0, z1, th):
    """aluminium blade: mapped on the silver spandrel band of the 'mori' facade row (u runs along the height)"""
    from ruins import FAC_ROWS
    r = FAC_ROWS.index('mori'); vb = 1 - (r + 1) / 8 + 0.006; vt = vb + 0.11 / 8
    tan = np.array([-out[1], out[0]])
    a = p + out * 0.05; b = p + out * depth
    q = [a - tan * th, b - tan * th, b + tan * th, a + tan * th]
    u0 = z0 / 32.0; u1 = z1 / 32.0
    uv = [(u0, vb), (u0, vt), (u1, vt), (u1, vb)]
    M.poly([(q[0][0], q[0][1], z0), (q[1][0], q[1][1], z0), (q[1][0], q[1][1], z1), (q[0][0], q[0][1], z1)], uv)
    M.poly([(q[2][0], q[2][1], z0), (q[3][0], q[3][1], z0), (q[3][0], q[3][1], z1), (q[2][0], q[2][1], z1)], uv)
    M.poly([(q[1][0], q[1][1], z0), (q[2][0], q[2][1], z0), (q[2][0], q[2][1], z1), (q[1][0], q[1][1], z1)], uv)
    M.poly([(q[0][0], q[0][1], z1), (q[1][0], q[1][1], z1), (q[2][0], q[2][1], z1), (q[3][0], q[3][1], z1)], uv)


def _slab(sc, reg, z, th, top):
    import ruins
    ruins.slab(sc, [np.asarray(p) for p in reg], z, th, top if top != 'top' else 'top', 'interior', 'tconc')


def _prism(sc, poly, z0, z1, wall, top):
    import ruins
    poly = [np.asarray(p) for p in lib.ccw([tuple(p) for p in poly])]
    n = len(poly)
    s = 0
    for i in range(n):
        a = poly[i]; b = poly[(i + 1) % n]
        L = float(np.linalg.norm(b - a))
        sc[wall].poly([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)],
                      [(s / 4, z0 / 4), ((s + L) / 4, z0 / 4), ((s + L) / 4, z1 / 4), (s / 4, z1 / 4)])
        s += L
    ruins.slab(sc, poly, z1, 0.3, top, 'interior', wall)
