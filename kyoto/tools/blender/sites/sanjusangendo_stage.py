"""三十三間堂: the statue stage inside the hall and the statue slots.

Ten tiers rising toward the back on each side of the central 須弥壇 (15 bays each, 50 columns x 10 tiers, staggered),
the 須弥壇 of the seated 中尊 (Tankei) with the 天蓋 above, the ledge in front for the 28 attendants with 風神 at the
north end and 雷神 at the south end, the black railing, the back wall, the 1001st statue behind the 中尊.
Built in the hall frame (u north, v west, z = 0 at the veranda deck); slots are returned in the hall frame."""
import math
import numpy as np
from jk import prim
from . import sanjusangendo_parts as P
from .sanjusangendo_parts import UL, VI, FLI, UC, US0, US1, WOOD, slab, block_rect

NT = 10                    # tiers
TD = 0.94                  # tier depth (row spacing front to back)
T0 = 0.75                  # top of the front tier above the deck
TR = 0.20                  # rise per tier
NCOL = 50                  # columns per side
LEDGE = (-5.9, -4.7, 0.35)  # attendants' ledge: v0, v1, top
UI = UL[-2]                # 55.72: the stage ends (inner pillar line at the hall ends)

def tier_top(k): return T0 + k * TR
def tier_v(k): return -VI + k * TD, -VI + (k + 1) * TD

# 二十八部衆 (2018 arrangement), north end -> centre, then the four round the 中尊, then centre -> south end
NORTH = [('Narayana-kengo', '那羅延堅固', 1.67), ('Nanda-ryuo', '難陀龍王', 1.60), ('Magora', '摩睺羅', 1.59), ('Kinnara', '緊那羅', 1.65),
         ('Karura', '迦楼羅', 1.64), ('Kendatsuba', '乾闥婆', 1.64), ('Bishaja', '毘舎闍', 1.61), ('Sanshi-taisho', '散支大将', 1.64),
         ('Manzen-shahatsu', '満善車鉢', 1.59), ('Manibadara', '摩尼跋陀羅', 1.60), ('Bishamonten', '毘沙門天', 1.61), ('Daizurata-o', '提頭頼吒王', 1.66)]
CENTRE = [('Basu-sen', '婆藪仙', 1.56, 'CFN'), ('Daibon-tenno', '大梵天王', 1.70, 'CRN'), ('Taishaku-tenno', '帝釈天王', 1.68, 'CRS'),
          ('Daibenkudoku-ten', '大弁功徳天', 1.66, 'CFS')]
SOUTH = [('Birurokusha', '毘楼勒叉', 1.65), ('Birubakusha', '毘楼博叉', 1.59), ('Sasha-mawara', '薩遮摩和羅', 1.59), ('Gobu-jogo', '五部浄居', 1.62),
         ('Konjiki-kujaku-o', '金色孔雀王', 1.64), ('Jinmo-nyo', '神母女', 1.54), ('Konpira', '金毘羅', 1.55), ('Hibakara', '畢婆伽羅', 1.64),
         ('Ashura', '阿修羅', 1.65), ('Ihatsura', '伊鉢羅', 1.64), ('Sagara-ryuo', '娑伽羅龍王', 1.66), ('Misshaku-kongoshi', '密迹金剛士', 1.68)]

DAIS = dict(u=4.7, v0=-3.4, v1=3.9, h=0.9)      # 須弥壇 of the 中尊
NAKA = (0.0, 0.6)                                # 中尊 centre (u, v)

def kannon_columns():
    """column centres (|u|) of one side, from the centre outward, and the stagger"""
    p = (US1 - US0) / NCOL
    return np.array([US0 + (j + 0.5) * p for j in range(NCOL)]), p

def slots():
    """all statue slots in the hall frame: dict like the JSON (yaw: +1 / -1 = facing -v (east) / +v (west), converted later)"""
    cols, p = kannon_columns()
    standing = []
    # numbering: 1 = south end, top tier ... 10 = south end, front tier; 11 = 2nd column from the south ...; 1000 = north end, front
    for C in range(2 * NCOL):
        if C < NCOL: u = -cols[NCOL - 1 - C]          # south side, from the south end toward the centre
        else: u = cols[C - NCOL]                      # north side, from the centre toward the north end
        for r in range(NT):
            k = NT - 1 - r                            # r = 0: top (back) tier
            du = (-p / 4 if k % 2 == 0 else p / 4) * (1 if u > 0 else -1)
            v0, v1 = tier_v(k)
            standing.append((u + du, (v0 + v1) / 2, FLI + tier_top(k), 'E'))
    out = dict(kannon_standing=standing)
    out['kannon_seated'] = [(NAKA[0], NAKA[1], FLI + DAIS['h'], 'E')]
    out['kannon_rear'] = [(0.0, 5.3, FLI + 0.45, 'W')]
    att = []
    us = attendant_u()
    zl = FLI + LEDGE[2]; vl = (LEDGE[0] + LEDGE[1]) / 2
    for i, (n, j, h) in enumerate(NORTH):
        att.append(dict(pos='N%d' % (i + 1), name=n, jp=j, u=us[i], v=vl, z=zl, h=h))
    cpos = {'CFN': (3.4, -2.55), 'CRN': (3.95, -0.85), 'CRS': (-3.95, -0.85), 'CFS': (-3.4, -2.55)}
    for (n, j, h, ps) in CENTRE:
        att.append(dict(pos=ps, name=n, jp=j, u=cpos[ps][0], v=cpos[ps][1], z=FLI + DAIS['h'], h=h))
    for i, (n, j, h) in enumerate(SOUTH):
        att.append(dict(pos='S%d' % (i + 1), name=n, jp=j, u=-us[11 - i], v=vl, z=zl, h=h))
    out['attendants'] = att
    out['fujin'] = (54.95, vl, zl, 'E')
    out['raijin'] = (-54.95, vl, zl, 'E')
    return out

def attendant_u():
    """|u| of the 12 attendants of one side, centre (index 11) ... end (index 0), kept clear of the inner pillars"""
    raw = np.linspace(51.4, 7.0, 12)
    pil = UL[(UL > 0)]
    out = []
    for u in raw:
        d = pil - u; j = np.argmin(np.abs(d))
        if abs(d[j]) < 0.85: u = pil[j] - 0.85 * np.sign(d[j]) if d[j] != 0 else pil[j] + 0.85
        out.append(float(u))
    return out

def build(B):
    # ------------------------------------------------ the ten tiers on each side
    for side in (-1, 1):
        u0, u1 = sorted((side * (UC + 0.1), side * UI))
        for k in range(NT):
            v0, v1 = tier_v(k)
            zt = FLI + tier_top(k)
            faces = 'xXZ' + ('Y' if k == NT - 1 else '')
            prim.box(B, u0, v0, FLI, u1, v1, zt, WOOD, faces=faces)
            prim.box(B, u0, v0, FLI, u1, v1, zt, 'black_lacquer', faces='y')
            # a thin gilt-free edge moulding on each riser
            prim.obox(B, (u0, v0 - 0.015, zt - 0.03), (u1, v0 - 0.015, zt - 0.03), 0.03, 0.06, WOOD, tag='detail')
    # ------------------------------------------------ attendants' ledge, railings
    v0, v1, h = LEDGE
    for side in (-1, 1):
        a, b = sorted((side * (UC + 0.4), side * (UI + 0.3)))
        prim.box(B, a, v0, FLI, b, v1, FLI + h, WOOD, faces='xXZ')
        prim.box(B, a, v0, FLI, b, v1, FLI + h, 'black_lacquer', faces='y')
        # black railing between the ledge and the front tier (posts each half bay, top rail, mid rail)
        rv = v1 - 0.08; zr = FLI + h
        us = np.arange(a, b + 0.01, (b - a) / max(1, round((b - a) / 1.69)))
        for u in us:
            slab(B, u - 0.06, rv - 0.06, u + 0.06, rv + 0.06, zr, zr + 0.95, 'black_lacquer')
        prim.obox(B, (a, rv, zr + 0.95), (b, rv, zr + 0.95), 0.1, 0.08, 'black_lacquer')
        prim.obox(B, (a, rv, zr + 0.5), (b, rv, zr + 0.5), 0.06, 0.08, 'black_lacquer', tag='detail')
        prim.obox(B, (a, rv, zr + 0.06), (b, rv, zr + 0.06), 0.1, 0.12, 'black_lacquer')
        # low barrier along the aisle in front of the ledge
        bv = v0 - 0.15
        for u in us:
            slab(B, u - 0.05, bv - 0.05, u + 0.05, bv + 0.05, FLI, FLI + 0.55, 'black_lacquer', tag='detail')
        prim.obox(B, (a, bv, FLI + 0.55), (b, bv, FLI + 0.55), 0.07, 0.06, 'black_lacquer')
        # end panels closing the stage at the hall ends
        e = side * (UI + 0.3)
        prim.box(B, min(e, e + side * 0.08), v0, FLI, max(e, e + side * 0.08), v1, FLI + h + 0.95, 'black_lacquer')
    # ------------------------------------------------ the back wall behind the top tier (boards), the 中尊's gilded wall
    zw = 4.25
    for side in (-1, 1):
        a, b = sorted((side * UC, side * UI))
        slab(B, a, VI + 0.03, b, VI + 0.13, FLI, zw, WOOD)
    slab(B, -UC, VI + 0.03, UC, VI + 0.13, FLI, 5.92, 'temple_wall', c0=(196, 156, 86, 35))
    # ------------------------------------------------ 須弥壇 of the 中尊
    du, dv0, dv1, dh = DAIS['u'], DAIS['v0'], DAIS['v1'], DAIS['h']
    slab(B, -du - 0.12, dv0 - 0.12, du + 0.12, dv1 + 0.12, FLI, FLI + 0.18, 'black_lacquer')          # 下框
    slab(B, -du + 0.05, dv0 + 0.05, du - 0.05, dv1 - 0.05, FLI + 0.18, FLI + dh - 0.16, 'black_lacquer')   # 腰
    slab(B, -du - 0.15, dv0 - 0.15, du + 0.15, dv1 + 0.15, FLI + dh - 0.16, FLI + dh, 'black_lacquer')   # 上框
    for zz in (FLI + 0.18, FLI + dh - 0.16):
        prim.obox(B, (-du - 0.1, dv0 - 0.06, zz), (du + 0.1, dv0 - 0.06, zz), 0.04, 0.035, 'gold', tag='detail')
    # the dais continues to the side stages at the tier level (the 4 centre attendants stand at the corners)
    # 前机 (altar) and the worship step with a red carpet, candle stands
    slab(B, -1.6, dv0 - 1.0, 1.6, dv0 - 0.15, FLI, FLI + 1.15, 'vermilion')
    slab(B, -1.75, dv0 - 1.1, 1.75, dv0 - 0.05, FLI + 1.15, FLI + 1.22, 'gold')
    slab(B, -2.4, -5.95, 2.4, dv0 - 1.0, FLI, FLI + 0.25, 'black_lacquer', faces='xXyY')
    slab(B, -2.4, -5.95, 2.4, dv0 - 1.0, FLI, FLI + 0.25, 'cloth', faces='Z', c0=(150, 20, 18, 0))
    for su in (-1, 1):
        x = su * 1.25; y = dv0 - 0.55
        prim.lathe(B, (x, y, FLI + 1.22), [(0.12, 0.0), (0.04, 0.05), (0.03, 0.55), (0.08, 0.6), (0.02, 0.62), (0.025, 0.85)], 8, 'bronze', tag='detail')
        B.lamp(x, y, FLI + 2.12, 2.0, (1.0, 0.6, 0.3))
    # railings either side of the central section (between the ledges and the altar step)
    for su in (-1, 1):
        prim.obox(B, (su * 2.5, -5.95, FLI + 0.9), (su * 2.5, dv0 - 0.2, FLI + 0.9), 0.08, 0.08, 'black_lacquer')
        for y in (-5.9, dv0 - 0.25):
            slab(B, su * 2.5 - 0.06, y - 0.06, su * 2.5 + 0.06, y + 0.06, FLI, FLI + 0.95, 'black_lacquer', tag='detail')
    # ------------------------------------------------ 天蓋 (canopy) over the 中尊
    cu, cv = NAKA[0], NAKA[1] - 1.0
    zc = 7.75
    prim.lathe(B, (cu, cv, zc), [(1.4, -0.05), (1.6, 0.0), (1.55, 0.18), (1.25, 0.28), (0.5, 0.36), (0.0, 0.38)], 8, 'gold', smooth=False)
    prim.lathe(B, (cu, cv, zc - 0.05), [(0.0, 0.0), (1.4, 0.0)], 8, 'gold', smooth=False)
    for t in np.linspace(0, 2 * math.pi, 24, endpoint=False):
        x = cu + 1.5 * math.cos(t); y = cv + 1.5 * math.sin(t)
        L_ = 0.35 + 0.15 * (math.cos(4 * t) > 0)
        prim.obox(B, (x, y, zc), (x, y, zc - L_), 0.045, 0.045, 'gold', tag='detail')
        prim.lathe(B, (x, y, zc - L_ - 0.25), [(0.0, 0.0), (0.06, 0.07), (0.045, 0.17), (0.0, 0.25)], 6, 'gold', tag='detail')
    prim.cyl(B, (cu, cv, zc + 0.4), (cu, cv, 8.2), 0.03, None, 6, 'metal_dark', tag='detail')
    # ------------------------------------------------ the 1001st statue's step on the back side of the central wall
    slab(B, -0.85, VI + 0.13, 0.85, 5.95, FLI, FLI + 0.45, 'black_lacquer')
    # ------------------------------------------------ blockers: the whole stage, the central section, the rear step
    block_rect(B, -UI - 0.45, LEDGE[0] + 0.1, UI + 0.45, VI + 0.2, FLI)     # the walk map adds ~0.3 m + a cell
    block_rect(B, -2.5, -6.05, 2.5, LEDGE[0], FLI)
    block_rect(B, -0.95, VI, 0.95, 6.05, FLI)
    return slots()
