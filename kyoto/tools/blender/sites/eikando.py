"""永観堂 禅林寺 (Eikan-dō Zenrin-ji): gates, the 方丈 / 書院 group, 御影堂, 阿弥陀堂, the 臥龍廊 climbing to 開山堂,
the 多宝塔 on the knoll, the 放生池 with 弁天社 and its bridges, 画仙堂, walls, steps, lanterns and many maples.

World frame (x east, y north, z T.P.).  The hall grid of the precinct is turned about 8° clockwise; the halls face
west (the precinct opens to the west, the 東山 rises to the east).  Helpers in sites/eikando_kit.py; trees, paint and
the exclusion zone in sites/eikando_land.py."""
import math, sys
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point
from jk import prim, arch, Frame
from jk import roof as jroof
from sites import eikando_kit as K
from sites import eikando_land as LAND

ROT = math.radians(-8.0)
MIEIDO_C = (3351.3, 3102.7)
YW = math.radians(-98.0)        # front (v-) faces west (the halls)
YS = math.radians(-8.0)         # front faces south; u runs east
YN = math.radians(172.0)        # front faces north
YE = math.radians(82.0)         # front faces east

def EN(E, N):
    """the precinct grid (E along the halls' east axis, N north) -> world"""
    c, s = math.cos(ROT), math.sin(ROT)
    return (E * c - N * s, E * s + N * c)

SHOTS = [
    ('pond',        (3277.6, 3126.6, 64.1), (3276.0, 3152.0, 64.6), 28),      # across the pond to the 錦雲橋, torii, lantern, ginkgo (Eikando7356)
    ('somon',       (3187.5, 3201.6, 62.4), (3204.0, 3202.3, 65.4), 28),      # 総門 from the street (Haupttor 1)
    ('approach',    (3207.0, 3201.6, 62.7), (3268.0, 3199.0, 64.6), 32),      # the maple approach to the 中門 (Eingangsbereich 1)
    ('karamon',     (3312.9, 3151.6, 68.5), (3323.8, 3149.8, 70.0), 28),      # 唐門 (Karamon 2)
    ('amida',       (3330.0, 3070.2, 72.3), (3357.0, 3063.6, 79.5), 30),      # 阿弥陀堂 from the stone stair (Amida Hall 1)
    ('mieido',      (3318.0, 3092.0, 69.8), (3350.0, 3104.0, 78.0), 26),      # 御影堂 front corner
    ('garyuro',     (3368.7, 3107.6, 70.3), (3373.4, 3126.5, 75.4), 24),      # the 臥龍廊 climbing the slope (from the 御影堂 side)
    ('tahoto_up',   (3367.0, 3114.6, 71.5), (3382.0, 3135.0, 84.5), 36),      # 開山堂 and 多宝塔 from below (Tempelgebäude 07)
    ('tahoto_view', (3382.6, 3134.2, 90.4), (3345.0, 3104.0, 76.0), 30),      # from the 多宝塔 over the roofs (Dachlandschaft 5)
    ('hojo',        (3298.0, 3170.0, 68.0), (3325.0, 3175.0, 74.0), 28),      # 鶴寿台 gable from the court (Shaka Hall 1)
    ('aerial',      (3175.0, 3040.0, 160.0), (3300.0, 3130.0, 72.0), 30),
    ('aerial_e',    (3445.0, 3080.0, 140.0), (3315.0, 3130.0, 70.0), 32),
]

def ground_max(S, loc, L, D):
    us = np.linspace(-L / 2, L / 2, 7); vs = np.linspace(-D / 2, D / 2, 7)
    return max(loc.g(S, u, v) for u in us for v in vs)

def ground_med(S, loc, L, D):
    us = np.linspace(-L / 2, L / 2, 7); vs = np.linspace(-D / 2, D / 2, 7)
    return float(np.median([loc.g(S, u, v) for u in us for v in vs]))

# ====================================================================== gates
def gates(B, S):
    # 総門 (1840): massive 薬医門-style gate on the street, flanked by white walls with dark lower boards
    loc = K.Loc(3202.3, 3202.3, math.radians(-90.0))
    K.gate(B, S, loc, zg=61.05, span=5.2, depth=2.6, H=4.35, r=0.3, roof_L=9.6, roof_D=6.0, pitch=0.82, z_eave=61.05 + 5.55)
    # 中門 (薬医門, 1713)
    loc = K.Loc(3284.1, 3197.0, math.radians(-91.8))
    K.gate(B, S, loc, zg=65.4, span=4.4, depth=2.3, H=3.9, r=0.26, roof_L=8.4, roof_D=6.2, pitch=0.8, z_eave=65.4 + 5.0)
    # 勧学門 (former gate of the 勧学院): black, heavy 本瓦, faces south
    loc = K.Loc(3290.4, 3209.3, math.radians(0.0))
    K.gate(B, S, loc, zg=66.0, span=3.4, depth=2.1, H=3.6, r=0.22, mat='black_lacquer', roof_L=6.4, roof_D=5.4, pitch=0.85, z_eave=66.0 + 4.55, doors='open')
    # 南門 (遊心門, 高麗門-type) on the west street
    loc = K.Loc(3199.9, 3135.0, math.radians(-90.0))
    K.gate(B, S, loc, zg=59.6, span=3.2, depth=1.6, H=3.4, r=0.22, roof_L=6.4, roof_D=3.6, pitch=0.8, z_eave=59.6 + 4.2)
    # 唐門 (勅使門, 1830): 向唐門 with a cypress-bark karahafu roof, black lacquer, 筋塀 on both sides
    loc = K.Loc(3323.8, 3149.8, math.radians(-99.2))
    K.karamon(B, S, loc, zg=66.92, span=2.7, depth=2.1, H=3.3, W=4.7, Dr=4.4, hump=1.3)
    # walls
    white_low = dict(h=2.6, th=0.5, color=K.WHITE, lower=1.0)
    K.wall(B, S, [(3193.5, 3179.7), (3193.1, 3188.7), (3204.5, 3188.8), (3204.4, 3198.6)], **white_low)
    K.wall(B, S, [(3204.4, 3206.0), (3204.4, 3210.1), (3192.5, 3210.1), (3190.7, 3223.0)], **white_low)
    K.wall(B, S, [(3205.2, 3197.2), (3214.6, 3197.0)], h=2.3, th=0.45, color=K.WHITE)
    K.wall(B, S, [(3219.9, 3197.6), (3242.0, 3196.2)], h=2.3, th=0.45, color=K.WHITE)
    K.wall(B, S, [(3198.6, 3138.9), (3198.6, 3148.0)], h=2.3, th=0.45, color=K.WHITE)
    K.wall(B, S, [(3198.6, 3131.2), (3198.6, 3124.0)], h=2.3, th=0.45, color=K.WHITE)
    K.wall(B, S, [(3285.4, 3201.3), (3285.6, 3210.8), (3288.5, 3210.7)], h=2.2, th=0.45, color=K.WHITE, lower=0.9)
    K.wall(B, S, [(3292.3, 3210.6), (3297.0, 3210.4)], h=2.2, th=0.45, color=K.WHITE, lower=0.9)
    K.wall(B, S, [(3284.9, 3193.3), (3285.0, 3187.0)], h=2.2, th=0.45, color=K.WHITE)
    suji = dict(h=2.35, th=0.55, color=K.OCHRE, stripes=5)
    K.wall(B, S, [(3323.0, 3147.9), (3322.5, 3144.0), (3320.8, 3141.7), (3320.3, 3138.4)], **suji)
    K.wall(B, S, [(3323.8, 3151.8), (3324.2, 3152.7), (3322.4, 3153.1), (3322.9, 3155.8), (3319.4, 3157.9)], **suji)
    K.wall(B, S, [(3320.3, 3138.4), (3319.5, 3132.1), (3321.1, 3129.8), (3322.8, 3127.4), (3347.5, 3123.0)], h=2.2, th=0.5, color=K.WHITE)

# ====================================================================== 方丈 / 書院 group
def kuri(B, S, loc, zg, *, L=14.6, D=17.0, Hw=4.6, o=1.6, verge=1.5, pitch=0.78):
    """鶴寿台 (庫裏): a tall gabled hall, white plaster between dark posts, 花頭窓 along the west gable end; the ridge runs
    along u (gables at u-, u+)"""
    with loc.frame(B):
        zf = zg + 0.45
        prim.box(B, -L / 2 - 0.3, -D / 2 - 0.3, zg - 0.3, L / 2 + 0.3, D / 2 + 0.3, zf, 'stone')
        us = np.linspace(-L / 2, L / 2, 7); vs = np.linspace(-D / 2, D / 2, 8)
        ztop = zf + Hw
        for x in us:
            for y in (vs[0], vs[-1]): prim.box(B, x - 0.15, y - 0.15, zf, x + 0.15, y + 0.15, ztop, 'wood_dark')
        for y in vs[1:-1]:
            for x in (us[0], us[-1]): prim.box(B, x - 0.15, y - 0.15, zf, x + 0.15, y + 0.15, ztop, 'wood_dark')
        sides = {0: [(x, vs[0]) for x in us], 1: [(us[-1], y) for y in vs], 2: [(x, vs[-1]) for x in us[::-1]], 3: [(us[0], y) for y in vs[::-1]]}
        for k, kinds in ((0, ['white', 'katomado', 'white', 'katomado', 'white', 'white']), (2, ['white'] * 6),
                         (1, ['white'] * 7), (3, ['katomado', 'white', 'katomado', 'maira', 'katomado', 'white', 'katomado'])):
            sp = sides[k]
            for i in range(len(sp) - 1):
                K.infill(B, sp[i], sp[i + 1], zf + 0.05, zf + 2.6, kinds[i], mat='wood_dark', r=0.16)
                K.infill(B, sp[i], sp[i + 1], zf + 2.85, ztop - 0.3, 'white', r=0.16)
        for zz in (zf + 2.7, ztop):
            arch.nageshi(B, L, D, zz, 'wood_dark', h=0.24, w=0.12, out=0.17)
        top, reach = arch.bracket_row(B, L, D, ztop, 'funa', 1.0, 'wood_dark', 'white_paint')
        R = jroof.Roof(L, D, top + K.ROOF_LIFT, o, kind='kirizuma', cover='sangawara', pitch=pitch, verge=verge, rafter=0.3, rafter_mat='wood_dark',
                       rafter_end='white_paint', sori=0.0, gable_wall='temple_wall')
        zz = R.build(B)
        # gable timber: 虹梁 + 束 grid on both gable walls
        ys = np.linspace(0.0, R.c, 60)
        zrf = np.array([float(R.z(R.c - y, R.a)) - R.edge - 0.1 for y in ys])
        def half_at(z):
            ok = ys[zrf > z + 0.25]
            return float(ok.max()) - 0.15 if len(ok) else 0.0
        for sgn in (-1, 1):
            u = sgn * (L / 2 + 0.06)
            zb = top + 0.25
            for zz_ in (zb, zb + 1.7, zb + 3.3):
                hw = min(half_at(zz_), D / 2)
                if hw > 0.5: prim.obox(B, (u, -hw, zz_), (u, hw, zz_), 0.12, 0.3, 'wood_dark', tag='detail')
            for y in (-D / 4, 0.0, D / 4):
                zt = float(np.interp(abs(y), ys, zrf)) - 0.05
                if zt > zb + 0.3: prim.obox(B, (u, y, zb), (u, y, zt), 0.12, 0.22, 'wood_dark', tag='detail')
        K.ribbon(B, [(-L / 2, -D / 2), (L / 2, -D / 2), (L / 2, D / 2), (-L / 2, D / 2), (-L / 2, -D / 2)], 0.5, 'block')
    return zz

def simple_hall(B, S, loc, zg, *, L, D, nu, nv, H=3.4, zoff=0.75, kind='irimoya', cover='sangawara', o=2.0, pitch=0.68,
                walls=None, ver=0.9, ver_sides=(0, 1, 2, 3), bracket='funa', skirt='plaster', band='plaster', rail=False,
                pmat='wood_dark', curtains_sides=(), kohai=None, block_sides=(1, 2, 3), verge=0.9, ends='oni'):
    rk = dict(kind=kind, cover=cover, o=o, pitch=pitch, ends=ends)
    if kind == 'kirizuma': rk.update(verge=verge, sori=0.0)
    return K.hall(B, S, loc, L=L, D=D, nu=nu, nv=nv, zf=zg + zoff, H=H, r=0.15, pmat=pmat, walls=walls, band=band, ver=ver,
                  ver_sides=ver_sides, rail=rail, skirt=skirt, bracket=bracket, bs=1.0, roofkw=rk, pillar_round=False,
                  curtains_sides=curtains_sides, kohai=kohai, block_sides=block_sides)

def hojo(B, S):
    # 鶴寿台 (庫裏): gable end to the west court
    kuri(B, S, K.Loc(3325.3, 3175.6, YS), 67.2, L=16.6, D=18.6)
    # 大玄関: irimoya with a 唐破風 porch on its west end
    loc = K.Loc(3326.6, 3160.6, YS)
    simple_hall(B, S, loc, 66.95, L=11.6, D=6.0, nu=5, nv=3, H=3.6, zoff=0.6, o=1.25, pitch=0.8,
                walls={0: ['white'] * 5, 2: ['white'] * 5, 1: ['white'] * 3, 3: ['maira', 'dark', 'maira']}, ver=0, ver_sides=())
    porch = K.Loc(*loc.w(-5.8 - 1.5, 0.0), YS - math.pi / 2)
    K.karamon(B, S, porch, zg=66.8, span=2.9, depth=2.6, H=3.0, W=4.4, Dr=3.4, hump=1.0, mat='wood_dark', trim='wood_dark',
              cover='sangawara', doors=False, back=False)
    # 釈迦堂 (方丈, 1627): 入母屋 桟瓦, verandas, shoji and 舞良戸, faces west to the 唐門
    loc = K.Loc(3340.2, 3146.4, YW)
    fr = ['shoji', 'maira', 'shoji', 'shoji', 'shoji', 'shoji', 'maira', 'shoji']
    simple_hall(B, S, loc, 67.08, L=19.6, D=13.2, nu=8, nv=6, H=3.35, zoff=0.85, o=2.55, pitch=0.68,
                walls={0: fr, 1: ['shoji'] * 6, 2: ['maira'] * 8, 3: ['shoji', 'shoji', 'maira', 'maira', 'shoji', 'shoji']},
                ver=1.05, curtains_sides=(0,), block_sides=(2,))
    # 古方丈: faces south over the inner pond
    loc = K.Loc(3353.8, 3173.6, YS)
    simple_hall(B, S, loc, 67.45, L=14.6, D=15.2, nu=6, nv=6, H=3.2, zoff=0.8, o=2.15, pitch=0.7,
                walls={0: ['shoji'] * 6, 1: ['maira'] * 6, 3: ['maira'] * 6, 2: ['white'] * 6}, ver=1.0)
    # 瑞紫殿
    loc = K.Loc(3357.8, 3154.4, YW)
    simple_hall(B, S, loc, 67.3, L=10.2, D=5.4, nu=4, nv=2, H=3.1, zoff=0.8, o=1.4, pitch=0.72,
                walls={0: ['shoji'] * 4, 1: ['white'] * 2, 2: ['white'] * 4, 3: ['white'] * 2}, ver=0.9, ver_sides=(0,))
    # 千佛洞 (a long hall E-W) and the building behind (lift / passage)
    loc = K.Loc(3353.9, 3141.2, YS)
    simple_hall(B, S, loc, 67.4, L=10.4, D=3.4, nu=5, nv=1, H=3.0, zoff=1.0, kind='kirizuma', o=0.8, pitch=0.62, verge=0.75,
                walls={0: ['white'] * 5, 2: ['white'] * 5, 1: ['white'], 3: ['white']}, ver=0, ver_sides=())
    loc = K.Loc(3353.3, 3127.9, YW)
    simple_hall(B, S, loc, 67.6, L=9.8, D=7.0, nu=4, nv=3, H=3.0, zoff=1.0, kind='kirizuma', o=0.8, pitch=0.62, verge=0.8,
                walls={0: ['white', 'shoji', 'shoji', 'white'], 1: ['white'] * 3, 2: ['white'] * 4, 3: ['white'] * 3}, ver=0, ver_sides=())
    # connecting corridors of the 書院 group (渡り廊下)
    K.corridor(B, S, [(3334.4, 3163.4), (3337.6, 3165.0), (3338.2, 3172.5), (3337.4, 3179.0)], [67.85] * 4, w=3.0, h=2.5, skirt=True, rail=False,
               end_gables=(False, False))
    K.corridor(B, S, [(3336.6, 3186.0), (3344.0, 3184.9)], [67.95] * 2, w=3.2, h=2.5, rail=False, end_gables=(False, False))
    K.corridor(B, S, [(3346.6, 3157.6), (3348.2, 3162.8)], [67.95] * 2, w=2.4, h=2.4, rail=True, end_gables=(False, False))
    # 釈迦堂 -> 千佛洞 -> 御影堂: the visitors' corridor (curtained), north wing of the 御影堂 (316011116)
    K.corridor(B, S, [(3347.8, 3141.6), (3349.4, 3141.4)], [67.95] * 2, w=2.6, h=2.4, rail=False, end_gables=(False, False))
    K.corridor(B, S, [(3359.6, 3140.0), (3362.0, 3137.2), (3363.3, 3129.0), (3362.3, 3115.5)], [68.4, 68.6, 69.6, 69.8], w=2.6, h=2.45,
               curtains_on=True, passages=[(9.0, 13.5)], end_gables=(False, False), seed=1)
    K.corridor(B, S, [(3358.4, 3129.5), (3361.6, 3129.0)], [68.9, 69.0], w=2.4, h=2.4, rail=True, end_gables=(False, False))

# ====================================================================== 御影堂
def mieido(B, S):
    # the OSM outline (with verandas) is ~30 x 30 m: a 7 x 7 bay hall of 25 m on a 2.1 m veranda; PLATEAU 18 m high
    loc = K.Loc(MIEIDO_C[0], MIEIDO_C[1], YW)
    zg = ground_med(S, loc, 30, 30)
    zf = zg + 1.65
    front = ['karado'] * 7
    side = ['karado', 'karado', 'board', 'board', 'board', 'board', 'karado']
    res = K.hall(B, S, loc, L=25.0, D=25.0, nu=7, nv=7, zf=zf, H=5.7, r=0.36, pmat='wood_dark', bmat='wood_dark',
                 walls={0: front, 1: side, 3: side[::-1], 2: ['board'] * 7}, band='renji', ver=2.1, rail_mat='wood_dark',
                 skirt='board', bracket='degumi', bs=1.05, bend='white_paint',
                 roofkw=dict(kind='irimoya', cover='hongawara', o=3.3, pitch=0.52, rafter=0.28, gable_wall='wood_natural'),
                 kohai=dict(n=3, depth=4.6, ok=1.2, os=0.9, slope=0.34, drop=1.1, bs=0.9, beam_mat='wood_dark'),
                 curtains_sides=(0, 1, 3), curtain_h=1.7, block_sides=(2,),
                 rail_gaps=[(2, -0.9, 2.2), (3, 7.6, 10.6), (1, 12.3, 14.8), (2, 12.1, 14.8)])
    print('御影堂 floor %.2f ridge %.2f (%.1f m above ground %.2f)' % (zf, res['z_ridge'], res['z_ridge'] - zg, zg))
    # east wing: corridor to the foot of the 臥龍廊 (cut into the slope)
    zv = res['zv']
    pts = [(3365.2, 3100.1), (3369.0, 3099.6), (3374.4, 3098.9)]
    K.corridor(B, S, pts, [zv] * 3, w=3.0, h=2.6, curtains_on=True, end_gables=(False, False), seed=3)
    return res

# ====================================================================== 阿弥陀堂 + 位牌堂 + stair corridor + 鐘楼
def amida(B, S):
    loc = K.Loc(3364.1, 3061.7, YW)
    zg = 74.85
    zf = zg + 1.5
    front = ['lattice', 'lattice', 'lattice', 'dark', 'lattice', 'lattice', 'lattice']
    side = ['lattice', 'lattice', 'lattice', 'board', 'board', 'board']
    res = K.hall(B, S, loc, L=16.4, D=12.6, nu=7, nv=6, zf=zf, H=4.5, r=0.24, pmat='vermilion', bmat='vermilion', wall_mat='black_lacquer',
                 walls={0: front, 1: side, 3: side[::-1], 2: ['board'] * 7}, band='plaster', ver=1.5, rail_mat='wood_dark',
                 skirt='plaster', bracket='hira', bs=0.95, bend='white_paint', nageshi_mat='vermilion',
                 roofkw=dict(kind='irimoya', cover='hongawara', o=2.6, pitch=0.74, rafter=0.26),
                 kohai=dict(n=3, depth=3.4, ok=1.0, os=0.8, slope=0.4, drop=0.95, pmat='wood_dark', beam_mat='cloth', beam_c0=(60, 120, 150, 0), bs=0.8),
                 curtains_sides=(0, 1, 3), curtain_h=1.45, block_sides=(2,), rail_gaps=[(3, 1.0, 4.0)])
    # 位牌堂 on the slope east of the stair corridor
    lo2 = K.Loc(3374.6, 3083.9, YW)
    zg2 = 73.6
    with lo2.frame(B):
        prim.box(B, -7.2, -3.6, 70.6, 7.2, 3.6, zg2 + 0.3, 'stone')
    simple_hall(B, S, lo2, zg2 + 0.3, L=11.0, D=5.4, nu=5, nv=2, H=3.4, zoff=0.5, o=1.3, pitch=0.72, cover='hongawara',
                walls={0: ['shoji', 'karado', 'karado', 'karado', 'shoji'], 1: ['white'] * 2, 2: ['white'] * 5, 3: ['white'] * 2}, ver=0.9,
                ver_sides=(0,), skirt=None)
    # the covered stair corridor 御影堂 -> 阿弥陀堂 (between the retaining walls)
    zv_m = 68.25 + 1.65 - 0.05
    zv_a = res['zv']
    pts = [(3362.9, 3087.5), (3366.4, 3085.0), (3367.3, 3078.2), (3367.9, 3070.7)]
    K.corridor(B, S, pts, [zv_m, zv_m + 0.6, zv_m + 4.0, zv_a], w=2.6, h=2.55, curtains_on=True, end_gables=(False, False), seed=2)
    # 鐘楼 on its stone platform
    K.bell_tower(B, S, K.Loc(3346.8, 3046.0, math.radians(-22.0 - 90 + 90)), 75.4, L=3.4, D=2.8, H=4.0, base=1.25)
    # 手水舎 (water basin pavilion)
    lo3 = K.Loc(3324.3, 3080.5, math.radians(-12.0))
    with lo3.frame(B):
        zt = 67.3
        for sx in (-1, 1):
            for sv in (-1, 1):
                prim.box(B, sx * 1.1 - 0.08, sv * 0.8 - 0.08, zt, sx * 1.1 + 0.08, sv * 0.8 + 0.08, zt + 2.3, 'wood_dark')
        prim.box(B, -0.8, -0.45, zt, 0.8, 0.45, zt + 0.75, 'stone')
        prim.box(B, -0.7, -0.35, zt + 0.6, 0.7, 0.35, zt + 0.76, 'water')
        jroof.roof(B, 2.2, 1.6, zt + 2.35, 0.55, kind='kirizuma', cover='sangawara', pitch=0.7, verge=0.5, rafter=0.25, sori=0.0, edge=0.2)
    # small shrine / stone hall near the 鐘楼 path (858269696)
    lo4 = K.Loc(3338.8, 3053.0, math.radians(-105.6 + 90))
    simple_hall(B, S, lo4, 74.0, L=6.0, D=2.2, nu=3, nv=1, H=2.5, zoff=0.5, o=0.8, pitch=0.7, kind='kirizuma', cover='sangawara',
                walls={0: ['koshi'] * 3, 1: ['white'], 2: ['white'] * 3, 3: ['white']}, ver=0, ver_sides=(), skirt=None)
    return res

# ====================================================================== 臥龍廊, 開山堂, 鎮守社
GARYU_PTS = [(3374.4, 3100.6), (3373.0, 3104.2), (3372.5, 3108.6), (3373.9, 3113.6), (3373.1, 3119.0), (3373.9, 3124.2), (3372.6, 3128.8), (3372.2, 3131.4), (3371.8, 3135.4)]
GARYU_Z = [69.9, 70.05, 70.35, 71.0, 72.1, 73.5, 74.95, 76.4, 76.45]

def garyuro(B, S):
    cut = K.cutting(B, S, GARYU_PTS, GARYU_Z, 1.9)
    S.cut.append([list(cut.exterior.coords)])
    K.corridor(B, S, GARYU_PTS, GARYU_Z, w=2.2, bay=1.75, h=2.4, rise=0.75, o=0.62, cover='sangawara', smooth=1.2, curtains_on=True,
               end_gables=(False, True), seed=4)
    # 開山堂: a small copper-roofed 入母屋 hall standing right behind the corridor's upper run (the corridor, curtained,
    # passes along its front: the "lower roof" in the photos)
    loc = K.Loc(3376.0, 3131.6, YW)
    zg = 76.05
    L, D = 5.0, 4.2
    cut2 = K.cutting(B, S, [(3374.0, 3131.6), (3379.6, 3131.2)], [zg + 0.25, zg + 0.25], 3.4)
    S.cut.append([list(cut2.exterior.coords)])
    with loc.frame(B):
        prim.box(B, -L / 2 - 1.1, -D / 2 - 0.3, 74.6, L / 2 + 1.1, D / 2 + 1.0, zg - 0.05, 'stone')
    K.hall(B, S, loc, L=L, D=D, nu=3, nv=2, zf=GARYU_Z[-1] + 0.05, H=3.2, r=0.18, pmat='wood_dark', bmat='wood_dark',
           walls={0: ['katomado', 'karado', 'katomado'], 1: ['board', 'katomado'], 2: ['board'] * 3, 3: ['katomado', 'board']},
           band='plaster', ver=0.85, ver_sides=(1, 3), skirt='board', bracket='degumi', bs=0.62, bend='white_paint',
           roofkw=dict(kind='irimoya', cover='copper', o=1.25, pitch=0.8, rafter=0.22), block_sides=(2,))
    # exit of the corridor's north end: steps down toward the 鎮守社 and the pagoda stairs
    K.terrain_steps(B, S, [(3371.5, 3135.6), (3370.7, 3138.6)], 1.8, z0=GARYU_Z[-1], z1=75.7, rail=None)
    # 鎮守社 + small vermilion torii
    K.small_shrine(B, S, K.Loc(3373.5, 3143.0, 0.0), float(S.ground(3373.5, 3143.0)) - 0.15, w=1.4, d=1.3, h=1.5)
    arch.torii(B, 3373.5, 3139.6, float(S.ground(3373.5, 3139.6)), 0.0, h=2.3, span=1.6)
    # retaining wall beside the 開山堂 / shrine
    K.retaining(B, S, [(3374.0, 3145.3), (3375.0, 3145.1), (3375.7, 3144.0), (3376.4, 3136.0), (3376.9, 3134.8), (3377.3, 3134.4)], up=1)

# ====================================================================== 多宝塔
def tahoto(B, S):
    loc = K.Loc(3386.9, 3136.7, YW)
    cut = K.cutting(B, S, [(3386.9, 3130.0), (3386.9, 3143.4)], [88.4, 88.4], 5.2, surf='gravel')
    S.cut.append([list(cut.exterior.coords)])
    res = K.tahoto(B, S, loc, 88.45, L=4.2, H1=2.85)
    print('多宝塔 top %.2f (%.1f m above 87.9)' % (res['top'], res['top'] - 87.9))
    # zigzag steps from the 開山堂 terrace up to the pagoda (27 + 27 steps)
    K.terrain_steps(B, S, [(3369.6, 3141.4), (3369.4, 3144.4), (3374.4, 3153.2)], 2.0, z0=75.8, z1=79.6)
    K.terrain_steps(B, S, [(3374.4, 3153.2), (3382.2, 3146.3)], 2.0, z0=79.6, z1=86.0)
    K.terrain_steps(B, S, [(3382.2, 3146.3), (3381.6, 3141.2)], 2.0, z0=86.0, z1=87.9, rail=None)
    K.retaining(B, S, [(3381.0, 3131.5), (3381.2, 3142.0), (3384.0, 3143.4), (3392.5, 3142.0)], up=-1, z_top=88.05, drop=2.2)
    # stone fence of the platform front
    for (a, b) in (((3381.2, 3131.0), (3381.4, 3140.6)),):
        a = np.array(a); b = np.array(b)
        for t in np.linspace(0, 1, 8):
            p = a + (b - a) * t
            prim.box(B, p[0] - 0.12, p[1] - 0.12, 88.0, p[0] + 0.12, p[1] + 0.12, 88.95, 'curb')
        prim.obox(B, np.r_[a, 88.85], np.r_[b, 88.85], 0.18, 0.16, 'curb')
    return res

# ====================================================================== 放生池
POND_W = 62.25

def pond(B, S):
    w = [x for x in S.osm['water'] if x['id'] == -16642160][0]
    P = Polygon(w['poly'][0][0], w['poly'][0][1:])
    island = Polygon(w['poly'][0][1])
    main = P.intersection(shapely.box(3266.5, 3090, 3310, 3175))
    arm = P.intersection(shapely.box(3195, 3135, 3266.5, 3175))
    # own basin: the generic terrain is cut over the pond (+ banks); the western arm is a stream of cascading pools
    # down to the lower pond by the library
    cutp = P.buffer(1.2).difference(island.buffer(-0.8))
    S.cut.append([list(cutp.exterior.coords)] + [list(r.coords) for r in cutp.interiors])
    waters = [(main, POND_W)]
    steps = [(3252.0, 3266.5, 61.82), (3238.5, 3252.0, 61.48), (3225.5, 3238.5, 61.12), (3195.0, 3225.5, 59.85)]
    for (x0, x1, zw) in steps:
        seg = arm.intersection(shapely.box(x0, 3135, x1, 3175))
        if seg.is_empty or seg.area < 1: continue
        waters.append((seg, zw))
        for y in np.linspace(3140, 3170, 31):
            if seg.buffer(0.2).contains(Point(x1, y)):
                K.rock_lp(B, (x1 - 0.25, y, zw + 0.05), 0.45, int(x1 * 10 + y), 'stone', flat=0.6)
        K.shore_rocks(B, seg, zw, step=1.6, seed=int(x0), size=(0.3, 0.7))
    K.basin(B, S, waters, cutp, res=1.0)
    for (wp, zw) in waters: K.water(B, wp, zw)
    K.shore_rocks(B, main, POND_W, step=1.15, seed=3, size=(0.4, 0.95))
    # island: 弁天社 (1866), lanterns
    loc = K.Loc(3284.9, 3151.6, math.radians(202.3 + 90.0))
    K.small_shrine(B, S, loc, 63.1, w=1.5, d=1.4, h=1.7, color='vermilion', cover='copper')
    # 錦雲橋: the long humpback stone bridge from the west shore to the island
    K.stone_bridge(B, S, (3270.4, 3145.45), (3279.6, 3149.2), 62.65, 63.15, w=2.0, arch_h=0.75, piers=(0.22, 0.5, 0.78), z_water=POND_W)
    # stone torii at the bridge foot (OSM) and lanterns beside it
    ang = math.atan2(3149.1 - 3145.7, 3279.3 - 3271.0)
    arch.torii(B, 3268.9, 3144.85, 62.6, ang + math.pi / 2, h=3.1, span=2.3, color='stone', top='stone', base='stone')
    K.lantern(B, 3270.7, 3143.6, 62.6, h=1.9)
    K.lantern(B, 3269.4, 3147.2, 62.6, h=1.9)
    # the tall lantern behind the bridge (north bank) and a 雪見 on the island
    K.lantern(B, 3274.5, 3168.4, float(S.ground(3274.5, 3168.4)), h=3.8)
    K.yukimi(B, 3281.2, 3154.6, 63.0)
    # 極楽橋 over the southern inlet, small stone bridges on the stream (寿橋, 楓橋)
    K.stone_bridge(B, S, (3287.0, 3116.2), (3298.4, 3114.5), 62.85, 63.75, w=1.9, arch_h=0.6, piers=(0.3, 0.7), z_water=POND_W)
    K.slab_bridge(B, S, (3258.6, 3160.0), (3257.0, 3164.5), 62.35, w=1.8)
    K.slab_bridge(B, S, (3234.6, 3161.8), (3236.6, 3157.6), 61.85, w=1.8)
    # rocks in the pond: the pale rock east of the bridge, small islets
    prim.rock(B, (3288.6, 3140.6, POND_W + 0.2), 1.3, 11, 'curb', flat=0.55)
    prim.rock(B, (3289.6, 3141.4, POND_W), 0.5, 12, 'curb', flat=0.6)
    prim.rock(B, (3276.0, 3132.0, POND_W), 0.7, 13, 'stone', flat=0.5)
    return P

# ====================================================================== 画仙堂 (1914)
def gasendo(B, S):
    loc = K.Loc(3246.2, 3121.4, math.radians(-90.0))
    zg = 61.85
    with loc.frame(B):
        L, D = 9.8, 8.4
        zf = zg + 0.55
        prim.box(B, -L / 2 - 0.6, -D / 2 - 0.6, zg - 0.3, L / 2 + 0.6, D / 2 + 0.6, zf, 'stone')
        us = np.linspace(-L / 2, L / 2, 5); vs = np.linspace(-D / 2, D / 2, 4)
        H1 = 3.4; H2 = 6.4
        for x in us:
            for y in (vs[0], vs[-1]): prim.box(B, x - 0.14, y - 0.14, zf, x + 0.14, y + 0.14, zf + H2, 'wood_dark')
        for y in vs[1:-1]:
            for x in (us[0], us[-1]): prim.box(B, x - 0.14, y - 0.14, zf, x + 0.14, y + 0.14, zf + H2, 'wood_dark')
        sides = {0: [(x, vs[0]) for x in us], 1: [(us[-1], y) for y in vs], 2: [(x, vs[-1]) for x in us[::-1]], 3: [(us[0], y) for y in vs[::-1]]}
        for k in range(4):
            sp = sides[k]
            for i in range(len(sp) - 1):
                K.infill(B, sp[i], sp[i + 1], zf + 0.05, zf + H1 - 0.6, 'maira' if (k == 0 and i == 1) else 'white', mat='wood_dark', r=0.15)
                K.infill(B, sp[i], sp[i + 1], zf + H1 + 0.6, zf + H2 - 0.3, 'white', r=0.15)
                # 丸窓 (round windows) on the upper storey
                a = np.array(sp[i]); b = np.array(sp[i + 1]); m = (a + b) / 2; dd = K.nrm(b - a); n = np.array([dd[1], -dd[0]])
                ring = [np.r_[m + dd * 0.75 * math.cos(t) - n * 0.0, zf + H1 + 1.65 + 0.75 * math.sin(t)] for t in np.linspace(0, 2 * math.pi, 25)]
                prim.sweep(B, np.array(ring) + np.r_[n * 0.03, 0], [(-0.07, -0.07), (0.07, -0.07), (0.07, 0.07), (-0.07, 0.07)], 'wood_dark', up=(n[0], n[1], 0), tag='detail')
                disc = [np.r_[m + dd * 0.7 * math.cos(t) + n * 0.01, zf + H1 + 1.65 + 0.7 * math.sin(t)] for t in np.linspace(0, 2 * math.pi, 21)[:-1]]
                Pd = np.array([np.r_[m + n * 0.01, zf + H1 + 1.65]] + disc); Id = [[0, 1 + j, 1 + (j + 1) % 20] for j in range(20)]
                fn = np.cross(Pd[Id[0][1]] - Pd[0], Pd[Id[0][2]] - Pd[0])
                if fn[:2] @ n < 0: Id = [t[::-1] for t in Id]
                B.add(Pd, Id, 'glass', tag='detail')
        arch.nageshi(B, L, D, zf + H1 - 0.45, 'wood_dark', h=0.22, w=0.12, out=0.15)
        arch.nageshi(B, L, D, zf + H2, 'wood_dark', h=0.3, w=0.18, out=0.0)
        # lower pent roof (裳階) all round, upper irimoya
        mo = 1.3
        a, c = L / 2, D / 2
        for k in range(4):
            sp = sides[k]
            p0 = np.array(sp[0]); p1 = np.array(sp[-1]); dd = K.nrm(p1 - p0); n = np.array([dd[1], -dd[0]])
            zt = zf + H1 + 0.55; ze = zt - 0.75
            A = np.r_[p0 - dd * 0.0, zt]; Bq = np.r_[p1, zt]; C = np.r_[p1 + n * mo + dd * mo, ze]; Dq = np.r_[p0 + n * mo - dd * mo, ze]
            K.quad(B, Dq, C, Bq, A, 'kawara')
            K.quad(B, A, Bq, C, Dq, 'eave_wood')
            prim.obox(B, Dq - [0, 0, 0.1], C - [0, 0, 0.1], 0.08, 0.22, 'wood_dark')
        top, reach = arch.bracket_row(B, L, D, zf + H2, 'funa', 1.0, 'wood_dark', 'white_paint')
        jroof.roof(B, L, D, top + K.ROOF_LIFT, 1.7, kind='irimoya', cover='hongawara', pitch=0.72, rafter=0.3, rafter_mat='wood_dark', rafter_end='white_paint', ends='shibi')
        K.ribbon(B, [(-L / 2, -D / 2), (L / 2, -D / 2), (L / 2, D / 2), (-L / 2, D / 2), (-L / 2, -D / 2)], 0.6, 'block')

# ====================================================================== grounds: steps, retaining walls, lanterns
def grounds(B, S):
    # 総門 -> 中門 approach: the 7 steps before the 中門
    K.terrain_steps(B, S, [(3266.8, 3198.45), (3270.6, 3198.1)], 4.2, z0=63.65, z1=64.15 + 0.0, rail='center')
    # long stone stair to the 阿弥陀堂 (from the court by the やすらぎ観音)
    K.terrain_steps(B, S, [(3318.5, 3072.8), (3332.0, 3069.6), (3346.6, 3066.2)], 5.6, rail='center')
    # side stairs (staff) up along the 御影堂 south wall and to the 鐘楼
    K.terrain_steps(B, S, [(3335.7, 3084.3), (3345.1, 3082.7)], 1.8, rail=None)
    K.terrain_steps(B, S, [(3345.7, 3082.0), (3344.9, 3072.8)], 1.8, rail=None)
    K.terrain_steps(B, S, [(3359.9, 3044.0), (3352.2, 3048.2)], 2.0, rail=None)
    K.terrain_steps(B, S, [(3347.5, 3052.0), (3346.5, 3049.3)], 2.2, rail=None)
    # steps from the 極楽橋 up to the 御影堂 court
    K.terrain_steps(B, S, [(3299.2, 3114.3), (3309.9, 3112.1)], 2.2, rail=None)
    # retaining walls (石垣)
    K.retaining(B, S, [(3362.7, 3080.9), (3336.2, 3085.0)], up=1)
    K.retaining(B, S, [(3369.8, 3085.8), (3369.4, 3080.7)], up=1)
    K.retaining(B, S, [(3346.8, 3079.9), (3346.2, 3072.6)], up=1)
    K.retaining(B, S, [(3335.5, 3085.2), (3328.0, 3086.4)], up=1, drop=0.9)
    # lanterns at the OSM lamp nodes (灯籠)
    for p in S.osm['points']:
        t = p['tags']
        if t.get('man_made') == 'lamp' and (t.get('note') == '灯籠' or t.get('material') == 'stone'):
            x, y = p['xy']
            if math.hypot(x - 3270, y - 3145.5) < 3: continue        # by the torii (placed in pond())
            K.lantern(B, x, y, float(S.ground(x, y)), h=2.1)
    # lanterns along the approach and in the court
    for (x, y, h) in ((3211.5, 3204.6, 2.3), (3211.5, 3199.2, 2.3), (3262.5, 3201.4, 2.0), (3262.5, 3195.8, 2.0), (3300.2, 3186.0, 2.6),
                      (3312.6, 3156.6, 2.4), (3313.2, 3143.0, 2.2), (3331.0, 3088.6, 2.4), (3317.0, 3070.2, 2.3), (3321.8, 3076.3, 2.3)):
        K.lantern(B, x, y, float(S.ground(x, y)), h=h)
    # 盛砂 (sand mound) in the 唐門 garden and the 方丈 front garden
    lo = K.Loc(3327.4, 3149.6, YW)
    with lo.frame(B):
        zg = lo.g(S, 0, 0)
        R = [(1.4 * math.cos(t), 0.75 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 25)[:-1]]
        prim.prism(B, R, zg - 0.1, zg + 0.38, 'sand_raked')
    # the やすらぎ観音 statue on its lotus base (Treppe photo)
    x, y = 3312.0, 3077.7; zg = float(S.ground(x, y))
    prim.lathe(B, (x, y, zg), [(0.9, 0.0), (0.9, 0.35), (0.6, 0.45), (0.75, 0.75), (0.5, 0.95), (0.42, 1.2), (0.4, 2.2), (0.33, 2.9), (0.2, 3.25), (0.22, 3.45), (0.0, 3.6)], 12, 'stone')

# ====================================================================== build
def build(B, S, only=None):
    parts = only or ['gates', 'hojo', 'mieido', 'amida', 'garyuro', 'tahoto', 'pond', 'gasendo', 'grounds', 'land']
    if 'gates' in parts: gates(B, S)
    if 'hojo' in parts: hojo(B, S)
    if 'mieido' in parts: mieido(B, S)
    if 'amida' in parts: amida(B, S)
    if 'garyuro' in parts: garyuro(B, S)
    if 'tahoto' in parts: tahoto(B, S)
    P = pond(B, S) if 'pond' in parts else None
    if 'gasendo' in parts: gasendo(B, S)
    if 'grounds' in parts: grounds(B, S)
    if 'land' in parts or 'trees' in parts: LAND.land(B, S, trees=True, shots=SHOTS)
    # preview renders: tree proxies and tinted vertex colours (added after the .blend is saved)
    try:
        import render_scene
        if not getattr(render_scene, '_eik_patched', False):
            orig = render_scene.setup
            def setup2(*a, **kw):
                orig(*a, **kw)
                K.add_preview_proxies(B, S)
            render_scene.setup = setup2; render_scene._eik_patched = True
    except Exception as e:
        print('preview patch failed', e)
