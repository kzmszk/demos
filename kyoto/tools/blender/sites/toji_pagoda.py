"""東寺 五重塔 (国宝, 1644, 家光寄進): 三間五重塔婆, 本瓦葺, 総高 54.8 m — the tallest wooden pagoda in Japan.

Working values (refs/toji/dossier.md): PLATEAU measures the top of the 相輪 at 55.0 m above the ground and the 5th
roof at 35.6 m (eave) .. 40.2 m (露盤); 初重 9.5 m square (3 bays); the roofs taper only a little (eave spans
19.6 -> 17.0 m); eave edges 6.55 m apart; deep 三手先 bracket sets with 尾垂木 on every pillar, double rafters,
本瓦 with 鬼瓦 on the hips and 風鐸 at the corners; every upper storey has a 縁 with 高欄 on a 腰組; unpainted, very
dark weathered timber; a bronze 相輪 (露盤, 伏鉢, 請花, 九輪, 水煙, 竜車, 宝珠) of ~14.6 m.  It stands on a cut-stone
基壇 (1.2 m) with a flight of steps on each face, inside a low fence."""
import math
import numpy as np
from jk import prim, arch
from jk.core import Frame
from jk import roof as jroof
from sites.toji_kit import (WOOD, rect, slab, quad, walk_poly, walk_rect, block_poly, block_rect, block_line, beam, post, furin,
                            bracket_h, nakazonae, stone_lantern)

PX, PY = -920.05, -657.05          # PLATEAU / OSM footprint centre
YAW = math.radians(0.6)
W = [9.5, 9.12, 8.74, 8.37, 8.0]                  # pillar-line squares (bodies taper little: far photo, deck5 ≈ 0.58 span5)
SPAN = [20.2, 19.6, 19.0, 18.4, 17.8]             # eave span (plan, mid-side); eave spacing / span5 = 0.36 (photo)
EAVE = [9.15, 15.6, 22.05, 28.5, 34.95]           # eave edge (mid-side) above the ground (PLATEAU: 5th eave 35.6)
S_BR = [1.6, 1.42, 1.41, 1.4, 1.39]               # bracket scale per storey (the sets are ~2.6-3 m tall)
APEX = 40.5                                        # 露盤 base above the ground
TOP = 55.0                                         # 宝珠 tip
PLAT = 1.2                                         # 基壇 height
PLAT_HALF = 7.6

def pagoda(B, S, stats):
    zg = float(np.mean([S.ground(PX + dx, PY + dy) for dx in (-8, 0, 8) for dy in (-8, 0, 8)]))
    zlow = float(min(S.ground(PX + dx, PY + dy) for dx in (-9, 9) for dy in (-9, 9)))
    n0 = B.ntri()
    zp = zg + PLAT
    with Frame(B, PX, PY, 0.0, YAW):
        platform(B, zg, zlow, zp)
        floor = zp
        top_z = None
        for k in range(5):
            w = W[k]; c = SPAN[k] / 2; s = S_BR[k]
            bh, reach = bracket_h('mitesaki', s)
            teri = 1.2 if k < 4 else 1.3
            pitch = 0.5 if k < 4 else (APEX - EAVE[4] + 0.1) / c
            o = c - (w / 2 + reach)                          # rafter overhang beyond the purlin line
            H = c * pitch
            e_abs = zg + EAVE[k]
            z_eave = e_abs + H * (o / c) ** teri               # roof surface over the purlin line
            top = z_eave - 0.32
            plate = top - bh
            deck = floor
            if k > 0:
                deck = floor + 0.3
                engawa(B, w, floor, deck, prev_roof)
            body(B, w, deck, plate, k)
            btop, breach = arch.bracket_row(B, w, w, plate, 'mitesaki', s=s, mat=WOOD, end_mat=WOOD, us=np.array(pillars(w)), vs=np.array(pillars(w)))
            us = pillars(w)
            tooshi(B, w, plate, s)
            odaruki_ends(B, w, plate, s)
            for side in range(4):
                R = rot(side)
                for i in range(3):
                    nakazonae(B, R((us[i], -w / 2)), R((us[i + 1], -w / 2)), plate, s, R((0, -1)), WOOD, n=1)
            shirin(B, w, plate, btop)
            ceiling_ring(B, w, breach, btop - 0.1)
            kw = dict(kind='hogyo', cover='hongawara', pitch=pitch, teri=teri, sori=0.62, sori_len=0.45, rafter=0.22, rafter_mat=WOOD, rafter_end=WOOD,
                      fascia_mat=WOOD, tiers=2, ends='oni', ridge_h=0.8, ridge_w=0.55, edge=0.44)
            Lr = w + 2 * reach
            if k < 4:
                nb = W[k + 1]
                trunc = c - nb / 2 + 0.15
                rf = jroof.Roof(Lr, Lr, z_eave, o, truncate=trunc, **kw)
                rf.build(B)
                floor = float(rf.z(trunc - 0.15, c)) + 0.1
                prev_roof = rf
            else:
                rf = jroof.Roof(Lr, Lr, z_eave, o, top=[(0.01, 0.0)], **kw)
                res = rf.build(B)
                top_z = res['z_ridge']
            zc = float(rf.zE(0.0)) - rf.edge
            for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                furin(B, sx * (c - 0.3), sy * (c - 0.3), zc, 1.2)
            stats.setdefault('pagoda_levels', []).append(dict(storey=k + 1, deck=round(deck - zg, 2), plate=round(plate - zg, 2), wall=round(plate - deck, 2),
                                                               eave=round(e_abs - zg, 2), corner=round(float(rf.zE(0.0)) - zg, 2)))
        sorin(B, top_z - 0.3, zg + TOP)
    stats['pagoda_tris'] = B.ntri() - n0
    stats['pagoda_apex'] = round(top_z - zg, 2)
    stats['pagoda_top'] = round(TOP, 2)
    return zg

def pillars(w):
    b = w * 0.36 / 2
    return [-w / 2, -b, b, w / 2]

def rot(side):
    ang = side * math.pi / 2
    c, s_ = math.cos(ang), math.sin(ang)
    return lambda p: (c * p[0] - s_ * p[1], s_ * p[0] + c * p[1])

# ------------------------------------------------------------------ 基壇, steps, fence
def platform(B, zg, zlow, zp):
    h = PLAT_HALF
    slab(B, -h, -h, h, h, zlow - 0.4, zp - 0.16, 'stone', faces='xXyY')
    slab(B, -h - 0.06, -h - 0.06, h + 0.06, h + 0.06, zp - 0.16, zp, 'curb', faces='xXyYZ')
    walk_poly(B, rect(h), zp)
    # a flight of steps in the middle of each face (5 risers), with cheek stones
    for side in range(4):
        R = rot(side)
        nst = 5; run = 0.36; wst = 3.2
        for i in range(nst):
            v0 = -h - run * (i + 1); v1 = -h - run * i
            zt = zp - (zp - zg) * (i + 1) / (nst + 0.0) + (zp - zg) / nst
            pts = [R((-wst / 2, v0)), R((wst / 2, v0)), R((wst / 2, v1)), R((-wst / 2, v1))]
            prim.prism(B, pts, zg - 0.2, zt, 'stone')
        for sx in (-1, 1):
            pts = [R((sx * wst / 2, -h - run * nst)), R((sx * (wst / 2 + 0.35), -h - run * nst)), R((sx * (wst / 2 + 0.35), -h)), R((sx * wst / 2, -h))]
            if sx < 0: pts = pts[::-1]
            prim.prism(B, [p for p in pts], zg - 0.2, zg + 0.25, 'curb')
        walk_poly(B, [R((-wst / 2, -h - run * nst - 0.3)), R((wst / 2, -h - run * nst - 0.3)), R((wst / 2, -h)), R((-wst / 2, -h))], zg + 0.0)
        a = np.array(R((-wst / 2, -h - run * nst - 0.3))); b = np.array(R((wst / 2, -h)))
        # the ramp of the steps (walk surface sloping from the gravel to the platform)
        P = np.array([np.r_[R((-wst / 2, -h - run * nst - 0.2)), zg], np.r_[R((wst / 2, -h - run * nst - 0.2)), zg], np.r_[R((wst / 2, -h)), zp], np.r_[R((-wst / 2, -h)), zp]])
        B.add(P, [[0, 1, 2], [0, 2, 3]], 'stone', tag='walk')
    # the body is not enterable: block the 初重 plan (the platform around it stays walkable)
    block_poly(B, rect(W[0] / 2 + 0.3), zp + 0.05)
    # the low fence round the platform (2.6 m out), open nowhere: visitors walk around it
    f = h + 2.6
    ring = [(-f, -f), (f, -f), (f, f), (-f, f), (-f, -f)]
    for a, b in zip(ring[:-1], ring[1:]):
        a = np.array(a); b = np.array(b); L = np.linalg.norm(b - a); d = (b - a) / L
        for t in np.arange(0, L + 0.01, 1.85):
            q = a + d * t
            prim.box(B, q[0] - 0.06, q[1] - 0.06, zg - 0.1, q[0] + 0.06, q[1] + 0.06, zg + 1.05, WOOD, tag='detail')
        prim.obox(B, np.r_[a, zg + 1.0], np.r_[b, zg + 1.0], 0.08, 0.08, WOOD, tag='detail')
        prim.obox(B, np.r_[a, zg + 0.55], np.r_[b, zg + 0.55], 0.05, 0.06, WOOD, tag='detail')
    block_line(B, ring, zg, 0.6)

# ------------------------------------------------------------------ a storey's body
def body(B, w, z0, z1, k):
    """pillars (round), 地覆 / 腰長押 / 内法長押 / 頭貫, the bays: 板扉 in the middle, 連子窓 over boards at the sides"""
    us = pillars(w)
    r = 0.24 if k == 0 else 0.2
    for u in us:
        for v in us:
            if u in (us[0], us[-1]) or v in (us[0], us[-1]):
                prim.cyl(B, (u, v, z0), (u, v, z1), r, r * 0.96, 12, WOOD, caps=(False, True))
    hh = z1 - z0
    for zz, h_, out in ((z0 + 0.14, 0.28, 0.1), (z0 + hh * 0.25, 0.2, 0.12), (z0 + hh * 0.8, 0.24, 0.12), (z1 - 0.02, 0.3, 0.06)):
        arch.nageshi(B, w, w, zz + h_ / 2, h=h_, w=0.12, out=out - 0.06, mat=WOOD)
    for side in range(4):
        R = rot(side)
        out = R((0, -1))
        for i in range(3):
            p0 = R((us[i], -w / 2)); p1 = R((us[i + 1], -w / 2))
            if i == 1:
                arch.infill(B, p0, p1, z0 + 0.28, z0 + hh * 0.78, 'board', out=out, mat=WOOD)
                # door leaves: two boards with iron bands and studs
                d = np.array(p1) - np.array(p0); L_ = np.linalg.norm(d); d /= L_; n = np.array(out)
                for zz in np.linspace(z0 + 0.6, z0 + hh * 0.7, 4):
                    prim.obox(B, np.r_[np.array(p0) + d * 0.25 + n * 0.02, zz], np.r_[np.array(p1) - d * 0.25 + n * 0.02, zz], 0.04, 0.06, 'metal_dark', tag='detail')
                prim.obox(B, np.r_[(np.array(p0) + np.array(p1)) / 2 + n * 0.03, z0 + 0.3], np.r_[(np.array(p0) + np.array(p1)) / 2 + n * 0.03, z0 + hh * 0.77], 0.05, 0.05, WOOD, tag='detail')
            else:
                arch.infill(B, p0, p1, z0 + 0.28, z0 + hh * 0.24, 'board', out=out, mat=WOOD)
                arch.infill(B, p0, p1, z0 + hh * 0.26, z0 + hh * 0.79, 'renji' if k > 0 else 'board', out=out, mat=WOOD)
            arch.infill(B, p0, p1, z0 + hh * 0.81, z1 - 0.18, 'board', out=out, mat=WOOD)
        # 釘隠 on the 内法長押 at the pillars (初重)
        if k == 0:
            for u in us:
                c = np.array(R((u, -w / 2 - 0.13)))
                prim.cyl(B, np.r_[c, z0 + hh * 0.8 + 0.12], np.r_[c + np.array(out) * 0.05, z0 + hh * 0.8 + 0.12], 0.1, 0.08, 8, 'metal_dark', tag='detail')

def odaruki_ends(B, w, plate, s):
    """the square ends of the 尾垂木 (and the 3rd-tier arms) that stand out under every eave of the 東寺 pagoda"""
    mh = 0.17 * s; hh = 0.17 * s; arm = 0.55 * s
    zc = plate + mh * 1.5 + 4 * (hh + mh)
    us = pillars(w)
    for side in range(4):
        R = rot(side)
        for u in us[1:-1]:
            # the kit's 尾垂木 end: p + o * (reach + 0.4) at zc - 0.35
            q = R((u, -w / 2 - (4 * arm + 0.4)))
            prim.box(B, q[0] - 0.17 * s, q[1] - 0.17 * s, zc - 0.35 - 0.18 * s, q[0] + 0.17 * s, q[1] + 0.17 * s, zc - 0.35 + 0.16 * s, WOOD, tag='detail')
            q = R((u, -w / 2 - 3 * arm - 0.35))
            prim.box(B, q[0] - 0.13 * s, q[1] - 0.13 * s, zc - mh - hh - 0.02, q[0] + 0.13 * s, q[1] + 0.13 * s, zc - mh + 0.02, WOOD, tag='detail')

def tooshi(B, w, plate, s):
    """通肘木: the continuous wall-parallel members of the 三手先 sets, one per tier at each tier's offset, meeting at
    the corners (they make the bracket zone read as horizontal bands, as in the photographs)"""
    mh = 0.17 * s; hh = 0.17 * s; arm = 0.55 * s
    for k in range(4):
        z0 = plate + mh * 1.5 + k * (hh + mh)
        d = k * arm
        for side in range(4):
            R = rot(side)
            a = w / 2 + d
            prim.obox(B, (*R((-a, -a)), z0 + hh / 2), (*R((a, -a)), z0 + hh / 2), 0.13 * s, hh, WOOD, tag='detail' if k else 'main')
            if k:   # the 小天井 board between this tier and the wall (a narrow ceiling strip)
                a0 = w / 2 + (k - 1) * arm
                P = [(*R((-a0, -a0)), z0 - 0.02), (*R((a0, -a0)), z0 - 0.02), (*R((a, -a)), z0 - 0.02), (*R((-a, -a)), z0 - 0.02)]
                B.add(np.array(P), [[0, 2, 1], [0, 3, 2]], WOOD, tag='detail')

def shirin(B, w, plate, btop):
    """the boards behind the bracket sets (小壁 / 支輪) on the wall plane, up to the purlin level"""
    a_ = w / 2 + 0.02
    for side in range(4):
        R = rot(side)
        q0 = R((-a_, -a_)); q1 = R((a_, -a_))
        P = np.array([(*q0, plate - 0.15), (*q1, plate - 0.15), (*q1, btop - 0.1), (*q0, btop - 0.1)])
        o_ = np.array([*R((0, -1)), 0.0])
        fn = np.cross(P[1] - P[0], P[2] - P[0])
        B.add(P, [[0, 1, 2], [0, 2, 3]] if fn @ o_ > 0 else [[0, 2, 1], [0, 3, 2]], WOOD)

def ceiling_ring(B, w, reach, z):
    """軒天井 under the bracket zone: a square ring (facing down) from the wall to just beyond the purlin, with
    a coffer grid (detail) under it"""
    a = w / 2 - 0.05; b = w / 2 + reach + 0.35
    outer = [(-b, -b), (b, -b), (b, b), (-b, b)]; inner = [(-a, -a), (a, -a), (a, a), (-a, a)]
    P = []; I = []
    for i in range(4):
        j = (i + 1) % 4
        q = [(*outer[i], z), (*outer[j], z), (*inner[j], z), (*inner[i], z)]
        k = len(P); P += q; I += [[k, k + 2, k + 1], [k, k + 3, k + 2]]
    B.add(np.array(P), I, WOOD, c1=(0, 2, 0, 0))
    for side in range(4):
        R = rot(side)
        for t in np.linspace(-b + 0.5, b - 0.5, max(4, int(2 * b / 0.9))):
            p0 = R((t, -a)); p1 = R((t, -b))
            if abs(t) > a + 0.2: continue
            prim.obox(B, (*p0, z - 0.04), (*p1, z - 0.04), 0.06, 0.07, WOOD, tag='detail')

def engawa(B, w, z_roof, deck, rf):
    """縁 (deck) of an upper storey on its 腰組, with a 高欄; the skirt boards reach down to the roof below"""
    dk = w / 2 + 0.68
    slab(B, -dk, -dk, dk, dk, deck - 0.12, deck, WOOD, faces='ZxXyY')
    # 腰組 band: from the deck down to the roof surface under the deck edge (the roof falls away outward)
    c = rf.c
    s_edge = c - dk
    z_bot = float(rf.z(s_edge, c)) - 0.05
    for side in range(4):
        R = rot(side)
        P = np.array([(*R((-dk, -dk)), z_bot), (*R((dk, -dk)), z_bot), (*R((dk, -dk)), deck - 0.12), (*R((-dk, -dk)), deck - 0.12)])
        o_ = np.array([*R((0, -1)), 0.0]); fn = np.cross(P[1] - P[0], P[2] - P[0])
        B.add(P, [[0, 1, 2], [0, 2, 3]] if fn @ o_ > 0 else [[0, 2, 1], [0, 3, 2]], WOOD)
        # bracket ends under the deck edge (腰組の肘木)
        for t in np.linspace(-dk + 0.4, dk - 0.4, 7):
            p0 = R((t, -dk + 0.4)); p1 = R((t, -dk - 0.12))
            prim.obox(B, (*p0, deck - 0.24), (*p1, deck - 0.24), 0.14, 0.18, WOOD, tag='detail')
    rl = [(-dk + 0.12, -dk + 0.12), (dk - 0.12, -dk + 0.12), (dk - 0.12, dk - 0.12), (-dk + 0.12, dk - 0.12), (-dk + 0.12, -dk + 0.12)]
    arch.railing(B, rl, deck, h=0.82, mat='wood_natural', cap_mat='bronze', giboshi=True, tag='detail')

# ------------------------------------------------------------------ 相輪
def sorin(B, z, ztop):
    """露盤 + 伏鉢 + 請花 + 九輪 + 水煙 + 竜車 + 宝珠 (bronze) from z to ztop.  Proportions from the distant photograph
    (5th roof span = 480 px): 露盤 2.7 m wide x 0.7 m, 伏鉢 + 請花 2.2 m, nine rings Ø 1.3 m over 7.0 m, 水煙 2.6 m,
    竜車 + 宝珠 1.85 m"""
    H = ztop - z
    k = H / 14.35
    # 露盤: a square box on the apex, with a lid
    prim.box(B, -1.3, -1.3, z - 0.15, 1.3, 1.3, z + 0.55 * k, 'bronze')
    prim.box(B, -1.38, -1.38, z + 0.52 * k, 1.38, 1.38, z + 0.7 * k, 'bronze')
    z1 = z + 0.7 * k
    # 伏鉢 (inverted bowl) and 請花 (lotus)
    prim.lathe(B, (0, 0, z1), [(0.85, 0.0), (0.86, 0.3 * k), (0.7, 0.75 * k), (0.3, 1.0 * k), (0.22, 1.15 * k)], 16, 'bronze')
    prim.lathe(B, (0, 0, z1 + 1.15 * k), [(0.2, 0.0), (0.55, 0.3 * k), (0.78, 0.6 * k), (0.66, 0.72 * k), (0.2, 0.8 * k)], 16, 'bronze')
    for a in range(8):          # lotus petals
        ang = a * math.pi / 4 + math.pi / 8
        d = np.array([math.cos(ang), math.sin(ang), 0.0])
        prim.obox(B, np.array([0, 0, z1 + 1.25 * k]) + d * 0.45, np.array([0, 0, z1 + 1.85 * k]) + d * 0.8, 0.3, 0.06, 'bronze', up=tuple(d), tag='detail')
    zc = z1 + 2.2 * k
    # the shaft (擦管) through the rings
    prim.cyl(B, (0, 0, zc - 0.3), (0, 0, ztop - 1.0 * k), 0.15, 0.1, 10, 'bronze')
    # 九輪: nine rings
    step = 0.78 * k
    for i in range(9):
        zi = zc + 0.2 * k + i * step
        rr = 0.66 * (1 - i * 0.012)
        prim.lathe(B, (0, 0, zi), [(0.15, 0.0), (rr * 0.88, 0.05 * k), (rr, 0.11 * k), (rr, 0.2 * k), (rr * 0.88, 0.26 * k), (0.15, 0.3 * k)], 18, 'bronze',
                   tag='main' if i % 3 == 0 else 'detail')
        if i % 2 == 0:          # tiny bells (宝鐸) at the ring corners
            for a in range(4):
                ang = a * math.pi / 2 + math.pi / 4
                x, y = rr * math.cos(ang), rr * math.sin(ang)
                prim.cyl(B, (x, y, zi - 0.12 * k), (x, y, zi + 0.03), 0.045, 0.035, 5, 'bronze', tag='detail')
    zs = zc + 9 * step + 0.05
    # 水煙: four openwork flame panels round the shaft (two bars + a plate each)
    hs = 2.6 * k
    for a in range(4):
        ang = a * math.pi / 2
        d = np.array([math.cos(ang), math.sin(ang), 0.0]); t = np.array([-d[1], d[0], 0.0])
        prof = [(0.12, 0.0), (0.36, 0.15), (0.52, 0.45), (0.56, 0.8), (0.48, 1.1), (0.3, 1.32), (0.1, 1.42)]
        for side in (-1, 1):
            pts = np.array([[0, 0, zs] + d * r_ + t * side * r_ * 0.38 + [0, 0, hs * f / 1.42] for (r_, f) in prof])
            prim.sweep(B, pts, [(-0.035, -0.035), (0.035, -0.035), (0.035, 0.035), (-0.035, 0.035)], 'bronze', up=tuple(d), tag='main' if side < 0 else 'detail')
        P = []
        for (r_, f) in prof:
            for side in (-1, 1):
                P.append(np.array([0, 0, zs]) + d * r_ + t * side * r_ * 0.38 + [0, 0, hs * f / 1.42])
        P = np.array(P); I = []
        for j in range(len(prof) - 1):
            a_ = 2 * j
            I += [[a_, a_ + 1, a_ + 3], [a_, a_ + 3, a_ + 2]]
        B.add(P, I, 'bronze', tag='detail', c1=(0, 3, 0, 0))
        B.add(P, [t_[::-1] for t_ in I], 'bronze', tag='detail', c1=(0, 3, 0, 0))
    zr = zs + hs + 0.05
    # 竜車 and 宝珠
    prim.lathe(B, (0, 0, zr), [(0.1, 0.0), (0.34, 0.1 * k), (0.36, 0.28 * k), (0.12, 0.4 * k), (0.1, 0.62 * k)], 14, 'bronze')
    zb = zr + 0.62 * k
    prim.lathe(B, (0, 0, zb), [(0.1, 0.0), (0.26, 0.1 * k), (0.3, 0.32 * k), (0.22, 0.56 * k), (0.09, 0.74 * k), (0.03, 0.82 * k)], 14, 'bronze')
    prim.cyl(B, (0, 0, zb + 0.8 * k), (0, 0, ztop), 0.03, 0.01, 6, 'bronze')
