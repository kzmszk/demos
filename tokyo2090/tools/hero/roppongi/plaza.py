"""66 Plaza and the podium decks: deck on a ruined podium mass, stairs (walkable routes Keyakizaka/arena -> plaza,
plaza -> Mohri Garden), Metro Hat skeleton, Roppongi Hills Arena canopy skeleton, Museum Cone skeleton, the curved
canopy walkway from Metro Hat to the plaza, railings."""
import math
import numpy as np
import lib, ruins
from lib import norm, vnoise

PZ = lib.PLAZA_Z
DECK = [(-30, 62), (-12, 56), (1, 57), (8, 63), (17, 64), (33, 64), (35, 100), (29, 110), (12, 120), (-4, 130),
        (-12, 142), (-20, 152), (-24, 158), (-40, 160), (-50, 150), (-64, 136), (-78, 122), (-86, 100), (-66, 80)]
# stairs: (bottom xyz-ground, top xy at deck), width
STAIR_A = ((10.6, 37.0), (1.8, 60.6), 3.8)     # arena level -> plaza (along b015's west side)
STAIR_B = ((39.5, 40.5), (25.5, 64.6), 5.0)    # plaza -> Mohri Garden (grand cascade)
CANOPY = [(-82, 96), (-75, 106), (-68, 115), (-58, 126), (-48, 137), (-38, 144), (-27, 149), (-14, 150), (-4, 145),
          (2, 137), (5, 130)]
METRO = (-26.4, 173.8, 13.4, 15.0)       # centre, radii
ARENA = (23.0, -32.5, 21.0, 26.0)
CONE = (-28.5, 106.5)


def stair(sc, col, b2, t2, width, ztop, G, tread=0.36, rise_max=0.18, side=True, mat='pave'):
    b2 = np.array(b2, float); t2 = np.array(t2, float)
    zb = float(G(b2[0], b2[1]))
    d = t2 - b2; L = float(np.linalg.norm(d)); u = d / L; nrm = np.array([-u[1], u[0]])
    dz = ztop - zb
    n = max(2, int(math.ceil(dz / rise_max)))
    n = max(n, int(L / 0.5))
    rise = dz / n; run = L / n
    P = sc[mat]; S = sc['conc']
    hw = width / 2
    for i in range(n):
        z = zb + rise * (i + 1)
        p0 = b2 + u * run * i; p1 = b2 + u * run * (i + 1)
        q = [p0 - nrm * hw, p1 - nrm * hw, p1 + nrm * hw, p0 + nrm * hw]
        # tread (top) + riser
        P.poly([(q[0][0], q[0][1], z), (q[1][0], q[1][1], z), (q[2][0], q[2][1], z), (q[3][0], q[3][1], z)],
               [(0, 0), (run / 2, 0), (run / 2, width / 2), (0, width / 2)])
        P.poly([(q[0][0], q[0][1], z - rise), (q[0][0], q[0][1], z), (q[3][0], q[3][1], z), (q[3][0], q[3][1], z - rise)],
               [(0, 0), (0, rise / 2), (width / 2, rise / 2), (width / 2, 0)])
        col.top([q[0], q[1], q[2], q[3]], z)
    if side:
        # stringer walls down to the ground on both sides (+ low parapet 0.9 m)
        for sgn in (-1, 1):
            o = nrm * (hw + 0.25) * sgn
            pts = []
            k = 8
            for i in range(k + 1):
                p = b2 + u * L * i / k + o
                z = zb + dz * i / k
                g = float(G(p[0], p[1])) - 0.5
                pts.append((p, z + 0.9, min(g, z - 1.0)))
            for i in range(k):
                (pa, za, ga), (pb, zb_, gb) = pts[i], pts[i + 1]
                quad = [(pa[0], pa[1], ga), (pb[0], pb[1], gb), (pb[0], pb[1], zb_), (pa[0], pa[1], za)]
                if sgn < 0:
                    quad = quad[::-1]
                S.poly(quad, [(0, ga / 4), (L / k / 4, gb / 4), (L / k / 4, zb_ / 4), (0, za / 4)])
                # top of parapet
                w2 = nrm * 0.25 * sgn
                S.poly([(pa[0], pa[1], za), (pb[0], pb[1], zb_), (pb[0] + w2[0], pb[1] + w2[1], zb_), (pa[0] + w2[0], pa[1] + w2[1], za)][::(1 if sgn > 0 else -1)])
        # underside/inner face visible from the side is covered by the stringers
    return n


def railing(sc, pts, z_of, gap_seed=0, post=1.8):
    """metal posts + top rail along a polyline; z_of(p) gives base height; random gaps (broken)"""
    M = sc['metal']
    rr = lib.rng(gap_seed)
    for i in range(len(pts) - 1):
        a = np.array(pts[i], float); b = np.array(pts[i + 1], float)
        L = float(np.linalg.norm(b - a)); n = max(1, int(L / post))
        for k in range(n):
            if rr.random() < 0.15:
                continue
            p = a + (b - a) * k / n; q = a + (b - a) * (k + 1) / n
            za = z_of(p); zb = z_of(q)
            lean = rr.uniform(-0.15, 0.15) if rr.random() < 0.3 else 0.0
            lib.tube(M, [(p[0], p[1], za), (p[0] + lean, p[1], za + 1.05)], [0.03, 0.03], sides=4)
            lib.tube(M, [(p[0] + lean, p[1], za + 1.05), (q[0], q[1], zb + 1.05)], [0.025, 0.025], sides=4)


def ellipse(cx, cy, rx, ry, n, rot=0.0):
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append(np.array([cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)]))
    return out


def build(sc, col, ctx):
    G = ctx['ground']
    rr = lib.rng(66)
    # ---------------- podium mass under the deck (2 ruined storeys) with the paved deck on top
    st = dict(upper='glass', ruin='glass_ruin', ground='shop', fh=5.6)
    poly = [np.array(p, float) for p in DECK]
    gmin = min(G(p[0], p[1]) for p in DECK) - 0.5
    ruins.ruin_prism(sc, col, DECK, gmin, PZ, st, ruins.Cut('none'), seed=6601, holes=0.02, seg=6.0,
                     top_mat='pave', parapet=False, rec=ctx, bid='deck')
    # broken deck edge railings (exposed east / north-east edges)
    for seg in ([(17, 64), (33, 64), (35, 100), (29, 110), (12, 120), (-4, 130), (-12, 142)],):
        if not lib.mid():
            railing(sc, seg, lambda p: PZ, 7)
    occ = ctx['occ']
    occ.fill_poly(DECK, 2)
    # ---------------- stairs
    for (b2, t2, w), sd in ((STAIR_A, 1), (STAIR_B, 2)):
        _b, _t = np.array(b2), np.array(t2); _u = norm(_t - _b); _n = np.array([-_u[1], _u[0]])
        occ.fill_poly([_b - _n * w, _t - _n * w, _t + _n * w, _b + _n * w], 3)
        stair(sc, col, b2, t2, w, PZ + 0.02, G)
        # landing pad joining the stair top to the deck
        t2 = np.array(t2); b2 = np.array(b2)
        u = norm(t2 - b2); nrm = np.array([-u[1], u[0]])
        q = [t2 - nrm * w / 2, t2 + u * 2.5 - nrm * w / 2, t2 + u * 2.5 + nrm * w / 2, t2 + nrm * w / 2]
        sc['pave'].poly([(p[0], p[1], PZ + 0.02) for p in q], [(p[0] / 4, p[1] / 4) for p in q])
        col.top(q, PZ + 0.02)
    # ---------------- Metro Hat skeleton: oval glass canopy over the escalator void, tilted roof
    cx, cy, rx, ry = METRO
    gz = max(PZ, float(G(cx, cy)))
    ring0 = ellipse(cx, cy, rx, ry, 28, math.radians(20))
    M = sc['metal']
    top_of = lambda p: gz + 10.0 + 11.0 * (0.5 + 0.5 * float(np.dot(norm(p - np.array([cx, cy])), [math.cos(math.radians(110)), math.sin(math.radians(110))])))
    tops = [np.r_[p, top_of(p)] for p in ring0]
    lib.tube(M, [np.r_[p, gz + 0.2] for p in ring0 + ring0[:1]], [0.25] * 29, sides=4)
    lib.tube(M, tops + tops[:1], [0.35] * 29, sides=5)
    for i, p in enumerate(ring0):
        t = tops[i]
        broken = rr.random() < 0.18
        if broken:
            # mullion snapped: stub + bent piece
            lib.tube(M, [np.r_[p, gz], np.r_[p, gz + rr.uniform(2, 6)]], [0.12, 0.12], sides=4)
            continue
        lib.tube(M, [np.r_[p, gz], t], [0.12, 0.12], sides=4)
        # horizontal transoms every 3.3 m
    for h in (3.4, 6.8):
        lib.tube(M, [np.r_[p, gz + h] for p in ring0 + ring0[:1]], [0.08] * 29, sides=4)
    # roof beams (parallel, along the long axis) and a few remaining glass panes
    for k in range(-5, 6):
        a = np.array([cx, cy]) + np.array([math.cos(math.radians(20)), math.sin(math.radians(20))]) * (k * 2.4)
        dirv = np.array([-math.sin(math.radians(20)), math.cos(math.radians(20))])
        L = ry * math.sqrt(max(0.0, 1 - (k * 2.4 / rx) ** 2))
        if L < 1 or rr.random() < 0.2:
            continue
        p0 = a - dirv * L; p1 = a + dirv * L
        lib.tube(M, [np.r_[p0, top_of(p0)], np.r_[p1, top_of(p1)]], [0.18, 0.18], sides=4)
    Gl = sc['glass_ruins']
    for i in range(len(ring0)):
        if rr.random() < 0.22:
            p, q = ring0[i], ring0[(i + 1) % len(ring0)]
            h0 = rr.uniform(0.3, 3.0); h1 = h0 + rr.uniform(1.5, 3.2)
            Gl.poly([(p[0], p[1], gz + h0), (q[0], q[1], gz + h0), (q[0], q[1], gz + h1), (p[0], p[1], gz + h1)])
    # escalator void: pit walls + a sloped escalator truss going down to B1
    pit = ellipse(cx, cy, rx * 0.55, ry * 0.6, 16, math.radians(20))
    W = sc['conc']
    for i in range(len(pit)):
        a, b = pit[i], pit[(i + 1) % len(pit)]
        W.poly([(b[0], b[1], gz - 8), (a[0], a[1], gz - 8), (a[0], a[1], gz), (b[0], b[1], gz)],
               [(0, 0), (1, 0), (1, 2), (0, 2)])
    sc['interior'].poly([(p[0], p[1], gz - 8) for p in pit], [(p[0] / 4, p[1] / 4) for p in pit])
    ring_in = [p for p in pit]
    # floor ring between pit and outer ring
    P = sc['pave']
    for i in range(len(ring0)):
        a, b = ring0[i], ring0[(i + 1) % len(ring0)]
        ia = pit[int(i * len(pit) / len(ring0)) % len(pit)]; ib = pit[int((i + 1) * len(pit) / len(ring0)) % len(pit)]
        P.poly([(a[0], a[1], gz + 0.05), (b[0], b[1], gz + 0.05), (ib[0], ib[1], gz + 0.05), (ia[0], ia[1], gz + 0.05)],
               [(a[0] / 4, a[1] / 4), (b[0] / 4, b[1] / 4), (ib[0] / 4, ib[1] / 4), (ia[0] / 4, ia[1] / 4)])
        col.top([a, b, ib, ia], gz + 0.05)
    col.top(pit, gz - 8)
    for k in range(2):
        o = np.array([math.cos(math.radians(20)), math.sin(math.radians(20))]) * (k * 2.2 - 1.1)
        dv = np.array([-math.sin(math.radians(20)), math.cos(math.radians(20))])
        a = np.array([cx, cy]) + o - dv * 7; b = np.array([cx, cy]) + o + dv * 7
        lib.box(sc['metal'], ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, gz - 8), (1.2, 14.0, 0.9), math.radians(20),
                tilt=_tilt_x(math.atan2(8, 14)))
    ctx['labels'].append({'name': 'メトロハット', 'x': cx, 'y': cy, 'z': gz + 23, 'kind': 'place'})
    # ---------------- curved canopy walkway (Metro Hat -> 66 Plaza): columns + bent roof ribs
    cl = lib.catmull(CANOPY, 3)
    zc = PZ + 9.6
    for i in range(0, len(cl) - 1, 2):
        p = np.asarray(cl[i]); q = np.asarray(cl[min(i + 1, len(cl) - 1)])
        u = norm(q - p); nrm = np.array([-u[1], u[0]])
        base = max(PZ, float(G(p[0], p[1])))
        if rr.random() < 0.15:
            continue
        for s in (-1, 1):
            c = p + nrm * 2.6 * s
            lib.tube(M, [np.r_[c, base], np.r_[c, zc]], [0.2, 0.17], sides=6)
        droop = 0.0 if rr.random() < 0.75 else rr.uniform(1.5, 4.0)
        lib.tube(M, [np.r_[p - nrm * 3.4, zc], np.r_[p, zc + 0.8 - droop], np.r_[p + nrm * 3.4, zc]], [0.12] * 3, sides=4)
    lib.tube(M, [np.r_[np.asarray(p) + 0 * np.asarray(p), zc + 0.4] for p in cl], [0.15] * len(cl), sides=4)
    for i in range(0, len(cl) - 1):
        if rr.random() < 0.12:
            p = np.asarray(cl[i]); q = np.asarray(cl[i + 1]); u = norm(q - p); nrm = np.array([-u[1], u[0]])
            g = sc['glass_ruins']
            g.poly([np.r_[p - nrm * 3, zc + 0.1], np.r_[q - nrm * 3, zc + 0.1], np.r_[q, zc + 0.75], np.r_[p, zc + 0.75]])
    # ---------------- Museum Cone (glass ellipse cone at the tower foot, lift shaft inside)
    cx2, cy2 = CONE
    r0 = ellipse(cx2, cy2, 5.5, 6.8, 22, math.radians(-30)); r1 = ellipse(cx2 + 1.0, cy2 + 0.5, 8.0, 9.2, 22, math.radians(-30))
    lib.tube(M, [np.r_[p, PZ] for p in r0 + r0[:1]], [0.2] * 23, sides=4)
    lib.tube(M, [np.r_[p, PZ + 15 + 1.5 * math.sin(i * 0.28)] for i, p in enumerate(r1 + r1[:1])], [0.28] * 23, sides=4)
    for i in range(len(r0)):
        if rr.random() < 0.2:
            continue
        lib.tube(M, [np.r_[r0[i], PZ], np.r_[r1[i], PZ + 15 + 1.5 * math.sin(i * 0.28)]], [0.1, 0.1], sides=4)
        if rr.random() < 0.3:
            a0, a1 = r0[i], r0[(i + 1) % len(r0)]; b0, b1 = r1[i], r1[(i + 1) % len(r1)]
            sc['glass_ruins'].poly([np.r_[a0, PZ + 1], np.r_[a1, PZ + 1], np.r_[(a1 + b1) / 2, PZ + 7], np.r_[(a0 + b0) / 2, PZ + 7]])
    for h in (5.0, 10.0):
        f = h / 15
        lib.tube(M, [np.r_[r0[i] * (1 - f) + r1[i] * f, PZ + h] for i in list(range(len(r0))) + [0]], [0.08] * 23, sides=4)
    lib.box(sc['conc'], (cx2, cy2, PZ), (3.6, 3.6, 19.0), math.radians(-30), uvscale=0.25)
    col.box((cx2, cy2, PZ), (3.6, 3.6, 19.0), math.radians(-30))
    # ---------------- Roppongi Hills Arena: ring of columns, elliptic ring truss, arched ribs, torn membrane
    ax, ay, arx, ary = ARENA
    ring = ellipse(ax, ay, arx, ary, 20)
    zt = 39.0
    for i, p in enumerate(ring):
        g = float(G(p[0], p[1]))
        if i in (3, 4):        # collapsed section: column fallen, ring sags
            lib.tube(M, [np.r_[p, g + 0.4], np.r_[p + norm(p - np.array([ax, ay])) * 15.0, g + 0.6]], [0.45, 0.4], sides=6)
            col.poly([np.r_[p, g + 0.85], np.r_[p + norm(p - np.array([ax, ay])) * 15.0, g + 1.0],
                      np.r_[p + norm(p - np.array([ax, ay])) * 15.0 + np.array([0.6, 0.6]), g + 1.0], np.r_[p + np.array([0.6, 0.6]), g + 0.85]])
            continue
        lib.tube(M, [np.r_[p, g], np.r_[p, zt]], [0.5, 0.42], sides=8)
        col.box((p[0], p[1], g), (0.9, 0.9, zt - g))
    rpts = []
    for i, p in enumerate(ring + ring[:1]):
        z = zt + 0.6 - (6.0 if (i % 20) in (3, 4) else 0.0)
        rpts.append(np.r_[p, z])
    lib.tube(M, rpts, [0.55] * len(rpts), sides=6)
    lib.tube(M, [q + np.array([0, 0, 1.6]) for q in rpts], [0.3] * len(rpts), sides=4)
    for i in range(0, 10):
        if i in (2,):
            continue
        a = ring[i]; b = ring[(i + 10) % 20]
        mid = (a + b) / 2
        path = [np.r_[a + (b - a) * f, zt + 1.0 + 7.0 * math.sin(math.pi * f)] for f in np.linspace(0, 1, 9)]
        if i == 3:
            path = path[:4]
        lib.tube(M, path, [0.32] * len(path), sides=5)
    # torn membrane shreds hanging from the ring (metal mat, double sided)
    for i in range(0, 20, 3):
        p = ring[i]; q = ring[(i + 1) % 20]
        L = rr.uniform(3, 9)
        sc['metal'].poly([np.r_[p, zt], np.r_[q, zt], np.r_[q * 0.9 + p * 0.1, zt - L], np.r_[p * 0.8 + q * 0.2, zt - L * 0.7]],
                         [(0, 0), (1, 0), (1, 1), (0, 1)])
    ctx['labels'].append({'name': '六本木ヒルズアリーナ', 'x': ax, 'y': ay, 'z': zt + 9, 'kind': 'place'})
    ctx['labels'].append({'name': '66プラザ', 'x': 14.0, 'y': 100.0, 'z': PZ + 3, 'kind': 'place'})
    # planter trees on the plaza (grown far past their planters, roots cracking the paving)
    import veg
    for k, (x, y, kind, h) in enumerate(((25.0, 84.0, 'zelkova', 15.0), (29.0, 101.0, 'broad', 13.0), (-2.0, 114.0, 'zelkova', 14.0),
                                          (17.0, 113.0, 'broad', 11.0), (-14.0, 128.0, 'zelkova', 13.0), (-40.0, 150.0, 'broad', 10.0))):
        for q in range(4):
            a = q * math.pi / 2 + math.pi / 4
            c = np.array([x, y]) + np.array([math.cos(a), math.sin(a)]) * 1.6
            lib.box(sc['conc'], (c[0], c[1], PZ), (3.2 if q % 2 == 0 else 0.35, 0.35 if q % 2 == 0 else 3.2, 0.6),
                    a - math.pi / 4, uvscale=0.25)
        col.box((x, y, PZ), (3.6, 3.6, 0.6))
        veg.tree(sc, col, (x, y, PZ + 0.5), kind, h, h * 0.42, 6600 + k, 'foliage_plaza')
        ctx['occ'].fill_circle(x, y, 2.5, 9)
    ctx['plaza_deck'] = DECK


def _tilt_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
