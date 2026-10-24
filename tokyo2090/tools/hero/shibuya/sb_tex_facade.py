"""Facade band atlases: facade_a / facade_b (2048 x 2048, 8 bands of one floor each, tileable in u).

One band = 4 bays x 3.6 m = 14.4 m wide, one storey (3.8 m) tall. Built as small scenes and rendered.
"""
import math
import random
import numpy as np

import sb_surf as S
from sb_texlib import Shot, save_png, resize
from sb_common import TEX

W = 14.4
HB = 3.8
PADPX = 6
ROWPX = 256
PADM = HB * PADPX / (ROWPX - 2 * PADPX)

SHOP_WORDS = ['ラーメン', 'カラオケ', '居酒屋', 'くすり', '焼肉', '寿司', 'メガネ', 'カフェ', '書店', '靴',
              '古着', 'ゲーム', '不動産', '歯科', '整体', 'ネイル', '美容室', '中古', '牛丼', 'うどん', '餃子',
              '24H', 'SALE', 'OPEN', '喫茶', '質', 'たばこ', '酒', '花', 'パン', '時計', 'CD', 'DVD',
              'ビッグエコー', '大盛堂書店', '不二家', 'マツモトキヨシ', 'ドラッグ', 'BAR', '英会話', 'ヘアサロン',
              'クリニック', '漫画喫茶', 'ネットカフェ', '宝くじ', '金券', 'チケット', '整骨院', '雀荘']
FADED = [(0.42, 0.10, 0.07), (0.10, 0.20, 0.40), (0.50, 0.38, 0.06), (0.10, 0.28, 0.14), (0.45, 0.20, 0.05),
         (0.32, 0.10, 0.25), (0.55, 0.52, 0.48), (0.08, 0.08, 0.09), (0.40, 0.05, 0.05), (0.06, 0.25, 0.32)]


def new_shot(name, seed=0):
    s = Shot(name, 0.0, W, -PADM, HB + PADM, 2048, plane='XZ', period=W, samples=10)
    s.rnd = random.Random(seed)
    return s


def slab(s, conc, z0=-1.0, z1=0.35, d=-0.02):
    s.box(-0.5, W + 0.5, z0, z1, d, 0.6, conc, 'slab')


def interior_back(s, surf, z0=-1, z1=HB + 1, d=2.5):
    s.box(-0.5, W + 0.5, z0, z1, d, d + 0.2, surf, 'int')


def junk(s, rnd, surf, n=10, z0=0.3, z1=1.4, d=(0.8, 2.3)):
    """dark silhouettes of furniture / fallen ceiling boards inside"""
    for i in range(n):
        x = rnd.uniform(0, W)
        w = rnd.uniform(0.3, 1.6)
        h = rnd.uniform(0.2, z1 - z0)
        dd = rnd.uniform(*d)
        s.box(x, x + w, z0, z0 + h, dd, dd + 0.3, surf, 'junk')


def ceiling_board(s, rnd, surf, n=6):
    for i in range(n):
        x = rnd.uniform(0, W)
        w = rnd.uniform(0.4, 1.2)
        s.box(x, x + w, HB - 0.75 - rnd.uniform(0, 0.8), HB - 0.42, rnd.uniform(0.6, 2.0), 2.2, surf, 'board')


LEAF_COLS = [(0.030, 0.050, 0.012), (0.045, 0.070, 0.016), (0.06, 0.09, 0.02), (0.085, 0.115, 0.028),
             (0.11, 0.14, 0.035), (0.07, 0.085, 0.03), (0.13, 0.12, 0.045), (0.05, 0.06, 0.03)]
_leafsurf = None


def ivy_leaves(rnd, x, top, length, spread=1.0, strands=10, size=(0.06, 0.12), dens=26, d=-0.12, bottom=-9):
    """hanging ivy curtain from (x, top): random-walk strands with leaves -> leaf tuples"""
    out = []
    for k in range(strands):
        px = x + rnd.gauss(0, spread * 0.45)
        pz = top + rnd.uniform(-0.2, 0.1)
        L = length * rnd.uniform(0.35, 1.0)
        vx = 0.0
        n = int(L * dens)
        for i in range(n):
            vx = vx * 0.9 + rnd.gauss(0, 0.012)
            px += vx
            pz -= 1.0 / dens
            if pz < bottom:
                break
            for m in range(rnd.choice((1, 1, 2))):
                sz = rnd.uniform(*size) * (1.0 - 0.4 * i / max(n, 1))
                c = rnd.choice(LEAF_COLS)
                out.append((px + rnd.gauss(0, sz * 0.8), pz + rnd.gauss(0, sz * 0.5), d - rnd.uniform(0, 0.08), sz,
                            rnd.uniform(-0.9, 0.9) + math.pi, rnd.uniform(-0.9, 0.9), c))
    return out


def vine_patch(s, rnd, n=2, z=(0.0, HB), surf=None, big=1.0):
    global _leafsurf
    leaves = []
    for i in range(n):
        x = rnd.uniform(0, W)
        top = rnd.uniform(z[0] + 1.0, z[1] + 0.6)
        leaves += ivy_leaves(rnd, x, top, rnd.uniform(1.2, 4.0) * big, spread=rnd.uniform(0.5, 1.8) * big,
                             strands=int(rnd.uniform(5, 14) * big), bottom=z[0] - 0.5)
    if leaves:
        s.leafmesh(leaves, S.leafattr(seed=rnd.random()), 'ivy')


# ------------------------------------------------------------------ bands
def band_shopA(seed=1):
    """ground floor: shops with rolling shutters (half open), fascia sign band, columns"""
    s = new_shot('shopA', seed); r = s.rnd
    conc = S.concrete((0.46, 0.45, 0.42), streak=0.6, moss=0.35, seed=seed)
    col_tile = S.tiles((0.38, 0.37, 0.35), (0.33, 0.32, 0.30), (0.25, 0.25, 0.24), seed=seed)
    inter = S.interior(seed=seed)
    interior_back(s, inter)
    s.box(-0.5, W + 0.5, -1, 0.05, 0.0, 3.0, S.concrete((0.2, 0.19, 0.17), moss=0.6, seed=3), 'floor')
    junk(s, r, S.interior((0.022, 0.02, 0.018), seed=2), 14, 0.05, 1.3)
    s.box(-0.5, W + 0.5, 3.55, HB + 1, -0.05, 0.6, conc, 'slab')
    for b in range(4):
        x0 = b * 3.6
        s.box(x0 - 0.25, x0 + 0.25, -1, 3.6, -0.08, 0.5, col_tile, 'col')
        # fascia sign
        c = r.choice(S.__dict__ and FADED)
        sign = S.paint(c, chip=0.5, fade=0.5, seed=r.random() * 10)
        s.box(x0 + 0.25, x0 + 3.35, 2.85, 3.55, -0.22, -0.05, sign, 'fascia')
        word = r.choice(SHOP_WORDS)
        tc = (0.62, 0.6, 0.55) if sum(c) < 1.2 else (0.12, 0.1, 0.09)
        s.text(word, x0 + 1.8, 3.2, 0.55 if len(word) <= 4 else 0.4, S.paint(tc, chip=0.6, fade=0.3, seed=r.random() * 9),
               d=-0.235, name='t')
        # shutter: from 2.85 down to a random height, rusty corrugated
        zb = r.choice([0.0, 0.0, 0.9, 1.4, 1.9, 2.3, 2.6])
        shut = S.paint(r.choice([(0.40, 0.40, 0.38), (0.30, 0.32, 0.33), (0.45, 0.43, 0.38)]), chip=0.7, fade=0.2,
                       seed=r.random() * 10, streak=0.6)
        if zb < 2.84:
            for k in range(int((2.85 - zb) / 0.09)):
                z = zb + k * 0.09
                s.box(x0 + 0.3, x0 + 3.3, z, z + 0.085, 0.05, 0.1 + 0.015 * (k % 2), shut, 'sh')
            # bottom bar
            s.box(x0 + 0.3, x0 + 3.3, zb - 0.06, zb + 0.02, 0.02, 0.12, S.rust(seed=r.random()), 'shb')
        # shutter box
        s.box(x0 + 0.25, x0 + 3.35, 2.75, 2.88, -0.05, 0.25, S.rust(seed=r.random()), 'sbox')
    vine_patch(s, r, 2, (0.0, 3.6))
    return s


def band_shopB(seed=2):
    """ground floor: glass shopfront gone, aluminium frames, transom, dark interior"""
    s = new_shot('shopB', seed); r = s.rnd
    stone = S.flat_color((0.36, 0.35, 0.33), mottle=0.3, streak=0.4, moss=0.2, seed=seed)
    alu = S.metal((0.38, 0.38, 0.37), seed=seed, rust=0.05)
    inter = S.interior(seed=seed)
    interior_back(s, inter, d=3.5)
    s.box(-0.5, W + 0.5, -1, 0.1, 0.0, 3.5, S.concrete((0.2, 0.19, 0.17), moss=0.6, seed=4), 'floor')
    junk(s, r, S.interior((0.026, 0.024, 0.02), seed=4), 18, 0.1, 1.2, (0.5, 3.2))
    ceiling_board(s, r, S.flat_color((0.055, 0.054, 0.05)), 8)
    s.box(-0.5, W + 0.5, 3.15, HB + 1, -0.05, 0.6, S.concrete((0.48, 0.47, 0.44), seed=seed, moss=0.3), 'slab')
    for b in range(4):
        x0 = b * 3.6
        s.box(x0 - 0.35, x0 + 0.35, -1, 3.2, -0.1, 0.5, stone, 'col')
        # transom
        s.box(x0 + 0.35, x0 + 3.25, 2.6, 2.75, 0.1, 0.2, alu, 'tr')
        for k in (1, 2):
            xm = x0 + 0.35 + k * (2.9 / 3)
            if r.random() < 0.7:
                s.box(xm - 0.03, xm + 0.03, 0.0, 2.7 if r.random() < 0.8 else r.uniform(0.6, 2.2), 0.1, 0.16, alu, 'mu')
        # surviving glass shards
        for k in range(r.randint(0, 3)):
            gx = x0 + 0.4 + r.uniform(0, 2.6)
            gz = r.choice([0.1, 2.0])
            pts = [(gx, gz), (gx + r.uniform(0.2, 0.7), gz), (gx + r.uniform(0.0, 0.5), gz + r.uniform(0.2, 0.7))]
            s.poly(pts, 0.12, S.glass(seed=r.random() * 9), 'shard')
        # small sign plate
        if r.random() < 0.6:
            c = r.choice(FADED)
            s.box(x0 + 0.5, x0 + 3.1, 2.78, 3.12, -0.15, -0.05, S.paint(c, chip=0.5, seed=r.random() * 9), 'plate')
            s.text(r.choice(SHOP_WORDS), x0 + 1.8, 2.95, 0.24, S.paint((0.6, 0.58, 0.54), chip=0.5, seed=1), d=-0.16)
    vine_patch(s, r, 2, (0.0, 3.0))
    return s


def band_office(seed=3):
    """punched windows in concrete, frames mostly empty"""
    s = new_shot('office', seed); r = s.rnd
    conc = S.concrete((0.53, 0.52, 0.49), streak=0.7, moss=0.3, seed=seed)
    alu = S.metal((0.36, 0.37, 0.36), seed=seed)
    inter = S.interior(seed=seed)
    interior_back(s, inter)
    junk(s, r, S.interior((0.022, 0.02, 0.018), seed=5), 10, 0.4, 1.3)
    ceiling_board(s, r, S.flat_color((0.055, 0.054, 0.05)), 6)
    wall = conc
    # wall with 8 window holes: build as boxes around openings
    wx = [(b * 3.6 + o, b * 3.6 + o + 1.25) for b in range(4) for o in (0.45, 1.9)]
    z0, z1 = 1.05, 2.75
    s.box(-0.5, W + 0.5, -1, z0, 0.0, 0.3, wall, 'w_lo')
    s.box(-0.5, W + 0.5, z1, HB + 1, 0.0, 0.3, wall, 'w_hi')
    edges = [-0.5] + [v for p in wx for v in p] + [W + 0.5]
    for i in range(0, len(edges), 2):
        s.box(edges[i], edges[i + 1], z0, z1, 0.0, 0.3, wall, 'pier')
    # sills (protruding) with moss
    sill = S.concrete((0.5, 0.49, 0.46), moss=0.8, moss_scale=1.5, seed=seed + 1)
    for (a, b) in wx:
        s.box(a - 0.05, b + 0.05, z0 - 0.08, z0, -0.08, 0.3, sill, 'sill')
        # frames: some windows keep a frame and a pane
        st = r.random()
        if st < 0.55:
            s.box(a, b, z0, z0 + 0.05, 0.12, 0.18, alu, 'f'); s.box(a, b, z1 - 0.05, z1, 0.12, 0.18, alu, 'f')
            s.box(a, a + 0.05, z0, z1, 0.12, 0.18, alu, 'f'); s.box(b - 0.05, b, z0, z1, 0.12, 0.18, alu, 'f')
            m = 0.5 * (a + b)
            s.box(m - 0.025, m + 0.025, z0, z1, 0.12, 0.18, alu, 'f')
            if st < 0.25:
                s.box(a + 0.05, m - 0.02, z0 + 0.05, z1 - 0.05, 0.15, 0.16, S.glass(seed=r.random() * 9), 'g')
            if 0.25 <= st < 0.4:
                pts = [(m, z0 + 0.05), (b - 0.05, z0 + 0.05), (b - 0.05, z0 + r.uniform(0.3, 1.2))]
                s.poly(pts, 0.15, S.glass(seed=r.random() * 9), 'shard')
        # rust streak below some sills
    vine_patch(s, r, 1)
    return s


def band_ribbon(seed=4):
    """tiled spandrel + continuous ribbon window with mullions"""
    s = new_shot('ribbon', seed); r = s.rnd
    tile = S.tiles((0.52, 0.47, 0.40), (0.47, 0.42, 0.36), (0.36, 0.35, 0.33), tw=W / 64, th=0.065, seed=seed)
    alu = S.metal((0.40, 0.40, 0.39), seed=seed)
    inter = S.interior(seed=seed)
    interior_back(s, inter)
    junk(s, r, S.interior((0.022, 0.02, 0.018), seed=7), 10, 1.0, 1.6)
    ceiling_board(s, r, S.flat_color((0.055, 0.054, 0.05)), 8)
    s.box(-0.5, W + 0.5, -1, 1.0, 0.0, 0.3, tile, 'span')
    s.box(-0.5, W + 0.5, 3.05, HB + 1, 0.0, 0.3, tile, 'top')
    s.box(-0.5, W + 0.5, 0.95, 1.02, -0.06, 0.3, S.concrete((0.45, 0.44, 0.41), moss=0.7, moss_scale=1.2, seed=9), 'sill')
    for k in range(13):
        x = k * 1.2
        if r.random() < 0.85:
            s.box(x - 0.04, x + 0.04, 1.0, 3.05, 0.08, 0.16, alu, 'mu')
        if r.random() < 0.2:
            s.box(x + 0.04, x + 1.16, 1.02, 3.0, 0.12, 0.13, S.glass(seed=r.random() * 9), 'g')
        elif r.random() < 0.25:
            h = r.uniform(0.2, 0.9)
            s.poly([(x + 0.04, 1.02), (x + 1.16, 1.02), (x + r.uniform(0.1, 1.1), 1.02 + h)], 0.12, S.glass(seed=r.random() * 9), 'sh')
    s.box(-0.5, W + 0.5, 2.3, 2.36, 0.08, 0.16, alu, 'tran')
    vine_patch(s, r, 2)
    return s


def band_tile(seed=5):
    """brown tile walls, single windows, AC units, small balconies"""
    s = new_shot('tile', seed); r = s.rnd
    tile = S.tiles((0.30, 0.20, 0.14), (0.26, 0.17, 0.12), (0.30, 0.29, 0.27), tw=W / 64, th=0.065, seed=seed)
    alu = S.metal((0.42, 0.42, 0.41), seed=seed)
    inter = S.interior(seed=seed)
    interior_back(s, inter)
    junk(s, r, S.interior((0.022, 0.02, 0.018), seed=8), 6, 0.9, 1.4)
    z0, z1 = 0.95, 2.55
    wx = [(b * 3.6 + 0.9, b * 3.6 + 2.6) for b in range(4)]
    s.box(-0.5, W + 0.5, -1, z0, 0, 0.3, tile, 'lo'); s.box(-0.5, W + 0.5, z1, HB + 1, 0, 0.3, tile, 'hi')
    ed = [-0.5] + [v for p in wx for v in p] + [W + 0.5]
    for i in range(0, len(ed), 2):
        s.box(ed[i], ed[i + 1], z0, z1, 0, 0.3, tile, 'p')
    for (a, b) in wx:
        s.box(a - 0.05, b + 0.05, z0 - 0.06, z0, -0.06, 0.3, S.concrete((0.45, 0.44, 0.41), moss=0.8, moss_scale=1.4, seed=2), 's')
        if r.random() < 0.6:
            s.box(a, b, z0, z0 + 0.04, 0.1, 0.15, alu, 'f'); s.box(a, b, z1 - 0.04, z1, 0.1, 0.15, alu, 'f')
            s.box(a, a + 0.04, z0, z1, 0.1, 0.15, alu, 'f'); s.box(b - 0.04, b, z0, z1, 0.1, 0.15, alu, 'f')
            if r.random() < 0.4:
                s.box(a + 0.04, b - 0.04, z0 + 0.04, z1 - 0.04, 0.12, 0.13, S.glass(seed=r.random() * 9), 'g')
        # AC unit
        if r.random() < 0.5:
            x = r.choice([a - 0.85, b + 0.05])
            ac = S.paint((0.55, 0.54, 0.5), chip=0.3, fade=0.2, seed=r.random() * 9, streak=0.7)
            s.box(x, x + 0.8, 0.25, 0.85, -0.3, 0.0, ac, 'ac')
            s.box(x + 0.15, x + 0.65, 0.35, 0.75, -0.31, -0.3, S.interior((0.06, 0.06, 0.06)), 'grill')
    vine_patch(s, r, 2)
    return s


def band_blind(seed=6):
    """precast concrete panels, billboard frames"""
    s = new_shot('blind', seed); r = s.rnd
    pan = S.concrete((0.56, 0.55, 0.52), streak=0.8, moss=0.25, seed=seed)
    for i in range(8):
        x = i * 1.8
        s.box(x + 0.012, x + 1.8 - 0.012, -1, HB + 1, 0.0, 0.2, pan, 'pan')
    s.box(-0.5, W + 0.5, -1, HB + 1, 0.02, 0.3, S.interior((0.05, 0.05, 0.05)), 'joint')
    # billboard frame with tattered remains
    if True:
        x0 = r.uniform(0.5, 5.0); x1 = x0 + r.uniform(5.0, 8.0)
        rs = S.rust(seed=seed)
        for z in (0.3, HB - 0.3):
            s.box(x0, x1, z - 0.08, z + 0.08, -0.3, -0.15, rs, 'bf')
        for x in np.linspace(x0, x1, 5):
            s.box(x - 0.06, x + 0.06, 0.2, HB - 0.2, -0.3, -0.15, rs, 'bf')
        c = r.choice(FADED)
        poster = S.paint(c, chip=0.8, fade=0.7, under=(0.35, 0.34, 0.31), seed=seed + 3)
        for k in range(r.randint(2, 4)):
            a = r.uniform(x0, x1 - 1.0); b = min(x1, a + r.uniform(0.8, 2.5))
            zt = HB - 0.3; zb = r.uniform(0.5, 2.6)
            s.poly([(a, zt), (b, zt), (b - r.uniform(0, 0.4), zb), (a + r.uniform(0, 0.4), zb + r.uniform(0, 0.8))], -0.31, poster, 'po')
    vine_patch(s, r, 3)
    return s


def band_gutted(seed=7):
    """an open storey: columns, slab edges, dark interior with debris"""
    s = new_shot('gutted', seed); r = s.rnd
    conc = S.concrete((0.48, 0.47, 0.44), streak=0.5, moss=0.45, seed=seed)
    inter = S.interior(seed=seed, var=0.8)
    s.box(-0.5, W + 0.5, -1, HB + 1, 4.0, 4.2, inter, 'back')
    # floor slab edge + top slab edge (jagged lower edge)
    s.box(-0.5, W + 0.5, -1, 0.32, -0.02, 4.0, conc, 'sl')
    s.box(-0.5, W + 0.5, HB - 0.38, HB + 1, -0.02, 4.0, conc, 'st')
    floorc = S.concrete((0.16, 0.15, 0.13), moss=0.7, seed=seed + 2)
    junk(s, r, S.interior((0.03, 0.028, 0.025), seed=1), 16, 0.32, 1.1, (0.5, 3.5))
    # rubble lumps on the slab front
    for k in range(10):
        x = r.uniform(0, W); w = r.uniform(0.2, 0.9)
        s.box(x, x + w, 0.3, 0.3 + r.uniform(0.08, 0.45), r.uniform(-0.05, 0.6), 1.2, S.concrete((0.4, 0.39, 0.36), moss=0.5, seed=k), 'rb')
    # columns at 3.6 m (some missing), interior columns darker
    for b in range(4):
        x = b * 3.6 + 1.8
        if r.random() < 0.85:
            s.box(x - 0.35, x + 0.35, 0.3, HB - 0.36, 0.1, 0.8, conc, 'c')
        x2 = b * 3.6 + r.uniform(0.5, 3.0)
        s.box(x2 - 0.3, x2 + 0.3, 0.3, HB - 0.36, 2.8, 3.4, S.concrete((0.12, 0.12, 0.11), seed=9), 'ci')
    # rebar hanging from the top slab
    rb = S.rust(seed=seed)
    for k in range(18):
        x = r.uniform(0, W); L = r.uniform(0.1, 0.9)
        s.box(x, x + 0.02, HB - 0.38 - L, HB - 0.38, -0.05, -0.03, rb, 'rb')
    # hanging vine curtains
    vine_patch(s, r, 3, (0.4, HB))
    return s


def band_silver(seed=8):
    """SHIBUYA109 cylinder cladding: vertical aluminium panels with ribs, some peeled off"""
    s = new_shot('silver', seed); r = s.rnd
    alu = S.metal((0.50, 0.51, 0.50), ox=0.5, seed=seed, streak=0.65, rust=0.08)
    alu2 = S.metal((0.44, 0.45, 0.44), ox=0.5, seed=seed + 1, streak=0.65, rust=0.1)
    struct = S.metal((0.14, 0.12, 0.10), seed=seed + 2, rust=0.4)
    inter = S.interior((0.03, 0.03, 0.03), seed=seed)
    interior_back(s, inter, d=1.5)
    for k in range(13):
        s.box(k * 1.2 - 0.06, k * 1.2 + 0.06, -1, HB + 1, 0.3, 0.45, struct, 'stud')
    s.box(-0.5, W + 0.5, 1.6, 1.75, 0.3, 0.45, struct, 'girt')
    for k in range(16):
        x = k * 0.9
        st = r.random()
        if st < 0.04:
            continue
        z0 = -1.0; z1 = HB + 1
        if st < 0.1:
            z0 = r.uniform(0.5, 2.5)          # lower part torn off
        m = alu if k % 2 else alu2
        s.box(x + 0.01, x + 0.89, z0, z1, 0.0, 0.08, m, 'pnl')
        s.box(x + 0.4, x + 0.5, z0, z1, -0.06, 0.0, m, 'rib')
    # horizontal joint bands every storey
    s.box(-0.5, W + 0.5, HB - 0.06, HB + 0.06, -0.02, 0.05, S.interior((0.08, 0.08, 0.08)), 'joint')
    return s


def band_curtain(seed=9, intact=0.18, name='curtain', tint=(0.030, 0.040, 0.048)):
    s = new_shot(name, seed); r = s.rnd
    alu = S.metal((0.34, 0.35, 0.35), seed=seed)
    inter = S.interior(seed=seed)
    interior_back(s, inter, d=3.0)
    junk(s, r, S.interior((0.022, 0.022, 0.02), seed=3), 12, 0.7, 1.5, (0.6, 2.8))
    ceiling_board(s, r, S.flat_color((0.055, 0.054, 0.05)), 8)
    # spandrel: dark panel + slab
    s.box(-0.5, W + 0.5, -1, 0.7, 0.05, 0.6, S.flat_color((0.11, 0.12, 0.13), streak=0.6, seed=seed), 'span')
    s.box(-0.5, W + 0.5, HB - 0.05, HB + 1, 0.05, 0.6, S.flat_color((0.11, 0.12, 0.13), streak=0.6, seed=seed), 'span2')
    for k in range(9):
        x = k * 1.8
        s.box(x - 0.05, x + 0.05, -1, HB + 1, -0.12, 0.05, alu, 'mul')
        u = r.random()
        if u < intact:
            s.box(x + 0.05, x + 1.75, 0.72, HB - 0.07, 0.0, 0.02, S.glass(tint, seed=r.random() * 9, crack=0.6), 'g')
        elif u < intact + 0.3:
            pts = [(x + 0.05, 0.72), (x + 1.75, 0.72), (x + 1.75, 0.72 + r.uniform(0.2, 2.2)), (x + r.uniform(0.2, 1.5), 0.72 + r.uniform(0.1, 1.0))]
            s.poly(pts, 0.01, S.glass(tint, seed=r.random() * 9), 'sh')
            if r.random() < 0.5:
                pts = [(x + 0.05, HB - 0.07), (x + 1.75, HB - 0.07), (x + r.uniform(0.3, 1.5), HB - r.uniform(0.3, 1.4))]
                s.poly(pts, 0.01, S.glass(tint, seed=r.random() * 9), 'sh2')
    s.box(-0.5, W + 0.5, 0.66, 0.74, -0.08, 0.05, alu, 'tr')
    s.box(-0.5, W + 0.5, HB - 0.1, HB - 0.02, -0.08, 0.05, alu, 'tr2')
    vine_patch(s, r, 1)
    return s


def band_qfront(seed=10):
    """QFRONT: storey-high glass with silver horizontal bands"""
    s = new_shot('qfront', seed); r = s.rnd
    alu = S.metal((0.55, 0.56, 0.55), seed=seed, ox=0.3, streak=0.5)
    inter = S.interior(seed=seed)
    interior_back(s, inter, d=3.5)
    junk(s, r, S.interior((0.022, 0.022, 0.02), seed=3), 14, 0.4, 1.4, (0.6, 3.2))
    ceiling_board(s, r, S.flat_color((0.055, 0.054, 0.05)), 10)
    s.box(-0.5, W + 0.5, -1, 0.55, -0.15, 0.6, alu, 'band')
    s.box(-0.5, W + 0.5, HB - 0.08, HB + 1, -0.15, 0.6, alu, 'band2')
    for k in range(5):
        x = k * 3.6
        s.box(x - 0.04, x + 0.04, 0.55, HB, -0.05, 0.05, alu, 'mul')
        if r.random() < 0.15:
            s.box(x + 0.04, x + 3.56, 0.55, HB - 0.08, 0.0, 0.02, S.glass(seed=r.random() * 9, crack=0.7), 'g')
        elif r.random() < 0.4:
            s.poly([(x + 0.04, 0.55), (x + 3.56, 0.55), (x + r.uniform(0.5, 3.0), 0.55 + r.uniform(0.3, 1.5))], 0.01, S.glass(seed=r.random() * 9), 'sh')
    return s


def band_fins(seed=11):
    """white vertical fins / louvres (Seibu-like) with windows behind"""
    s = new_shot('fins', seed); r = s.rnd
    fin = S.concrete((0.62, 0.61, 0.58), streak=0.85, moss=0.25, seed=seed)
    inter = S.interior(seed=seed)
    interior_back(s, inter, d=2.5)
    junk(s, r, S.interior((0.022, 0.022, 0.02), seed=3), 8, 0.6, 1.4)
    s.box(-0.5, W + 0.5, -1, 0.5, 0.3, 0.6, S.concrete((0.5, 0.49, 0.46), seed=2), 'sl')
    for k in range(16):
        x = k * 0.9
        if r.random() < 0.06:
            continue
        s.box(x + 0.3, x + 0.6, -1, HB + 1, -0.35, 0.3, fin, 'fin')
    s.box(-0.5, W + 0.5, HB - 0.2, HB + 1, -0.4, 0.3, fin, 'cap')
    vine_patch(s, r, 2)
    return s


def band_signwall(seed=12):
    """wall covered in signboards (Shibuya side streets): horizontal and vertical panels with text"""
    s = new_shot('signwall', seed); r = s.rnd
    conc = S.concrete((0.48, 0.47, 0.44), streak=0.7, moss=0.3, seed=seed)
    inter = S.interior(seed=seed)
    interior_back(s, inter)
    s.box(-0.5, W + 0.5, -1, 0.9, 0, 0.3, conc, 'lo'); s.box(-0.5, W + 0.5, 2.7, HB + 1, 0, 0.3, conc, 'hi')
    for b in range(4):
        s.box(b * 3.6 - 0.6, b * 3.6 + 0.6, 0.9, 2.7, 0, 0.3, conc, 'p')
    x = 0.0
    while x < W - 0.8:
        w = r.uniform(1.6, 4.2)
        w = min(w, W - x)
        c = r.choice(FADED)
        sg = S.paint(c, chip=0.45, fade=0.55, seed=r.random() * 9, streak=0.6)
        z0 = r.uniform(0.6, 1.3); z1 = min(HB - 0.15, z0 + r.uniform(0.9, 2.2))
        s.box(x + 0.05, x + w - 0.05, z0, z1, -0.18, -0.02, sg, 'sg')
        tc = (0.66, 0.64, 0.58) if sum(c) < 1.2 else (0.1, 0.09, 0.08)
        word = r.choice(SHOP_WORDS)
        size = min(0.62 * (z1 - z0), (w - 0.3) / max(1, len(word)) * 1.0)
        s.text(word, x + w / 2, 0.5 * (z0 + z1), size, S.paint(tc, chip=0.5, fade=0.3, seed=r.random() * 9), d=-0.19)
        if r.random() < 0.5:
            s.text(r.choice(['2F', '3F', '4F', 'B1', '5F', '営業中', 'OPEN']), x + w - 0.35, z0 + 0.18, 0.18,
                   S.paint(tc, chip=0.5, seed=1), d=-0.19)
        x += w + r.uniform(0.0, 0.6)
    vine_patch(s, r, 2)
    return s


def band_balcony(seed=13):
    s = new_shot('balcony', seed); r = s.rnd
    conc = S.concrete((0.56, 0.55, 0.52), streak=0.8, moss=0.35, seed=seed)
    inter = S.interior(seed=seed)
    interior_back(s, inter, d=3.0)
    # sliding doors (dark) recessed
    s.box(-0.5, W + 0.5, -1, 0.1, 0.0, 1.8, S.concrete((0.3, 0.3, 0.28), seed=1), 'bfloor')
    s.box(-0.5, W + 0.5, 2.6, HB + 1, 1.4, 1.6, conc, 'lintel')
    for b in range(4):
        x = b * 3.6
        s.box(x - 0.12, x + 0.12, -1, HB + 1, -0.1, 1.8, conc, 'wall')
        if r.random() < 0.5:
            s.box(x + 0.2, x + 1.7, 0.1, 2.5, 1.5, 1.52, S.glass(seed=r.random() * 9), 'door')
        if r.random() < 0.5:
            ac = S.paint((0.55, 0.54, 0.5), chip=0.3, fade=0.2, seed=r.random() * 9, streak=0.7)
            s.box(x + 2.4, x + 3.2, 1.05, 1.65, 0.6, 1.0, ac, 'ac')
    # balcony slab edge + parapet (concrete lower, railing upper)
    s.box(-0.5, W + 0.5, -1, 0.25, -0.15, 0.0, conc, 'edge')
    s.box(-0.5, W + 0.5, 0.25, 0.7, -0.1, 0.0, conc, 'par')
    rl = S.paint((0.38, 0.38, 0.36), chip=0.8, seed=seed)
    s.box(-0.5, W + 0.5, 1.05, 1.1, -0.08, -0.02, rl, 'rail')
    for k in range(int(W / 0.12)):
        if r.random() < 0.9:
            x = k * 0.12
            s.box(x, x + 0.018, 0.7, 1.05, -0.06, -0.04, rl, 'bar')
    s.box(-0.5, W + 0.5, HB - 0.25, HB + 1, -0.15, 0.0, conc, 'edge2')
    vine_patch(s, r, 3)
    return s


def band_shopC(seed=14):
    """ground floor: closed shutters, vending niche, posters, entrance to stairs"""
    s = new_shot('shopC', seed); r = s.rnd
    conc = S.concrete((0.44, 0.43, 0.40), streak=0.6, moss=0.4, seed=seed)
    s.box(-0.5, W + 0.5, 3.0, HB + 1, -0.1, 0.5, conc, 'top')
    inter = S.interior(seed=seed)
    interior_back(s, inter)
    for b in range(4):
        x0 = b * 3.6
        s.box(x0 - 0.3, x0 + 0.3, -1, 3.0, -0.05, 0.5, conc, 'c')
        kind = r.choice(['shut', 'shut', 'stairs', 'open'])
        if kind == 'shut':
            shut = S.paint(r.choice([(0.38, 0.38, 0.36), (0.32, 0.33, 0.34), (0.42, 0.4, 0.36)]), chip=0.75, fade=0.2,
                           seed=r.random() * 10, streak=0.7)
            for k in range(int(2.8 / 0.09)):
                z = k * 0.09
                s.box(x0 + 0.3, x0 + 3.3, z, z + 0.085, 0.05, 0.1 + 0.015 * (k % 2), shut, 'sh')
            # posters
            for k in range(r.randint(0, 3)):
                px = x0 + r.uniform(0.4, 2.6); pz = r.uniform(0.6, 1.8)
                s.box(px, px + r.uniform(0.4, 0.7), pz, pz + r.uniform(0.5, 0.9), 0.02, 0.04,
                      S.paint(r.choice(FADED), chip=0.8, fade=0.7, under=(0.4, 0.39, 0.36), seed=r.random() * 9), 'po')
        elif kind == 'stairs':
            for k in range(8):
                s.box(x0 + 0.6, x0 + 3.0, k * 0.18, k * 0.18 + 0.18, 0.4 + k * 0.28, 3.0, S.concrete((0.3, 0.29, 0.27), moss=0.5, seed=k), 'st')
            s.text(r.choice(SHOP_WORDS), x0 + 1.8, 2.75, 0.2, S.paint((0.6, 0.58, 0.5), seed=2), d=-0.06)
        s.box(x0 + 0.3, x0 + 3.3, 2.85, 3.0, -0.05, 0.3, S.rust(seed=r.random()), 'sb')
    vine_patch(s, r, 3, (0.0, 3.0))
    return s


def band_overgrown(seed=15):
    s = new_shot('overgrown', seed); r = s.rnd
    conc = S.concrete((0.42, 0.42, 0.38), streak=0.6, moss=0.9, moss_scale=0.9, seed=seed)
    inter = S.interior(seed=seed)
    interior_back(s, inter)
    z0, z1 = 1.0, 2.7
    wx = [(b * 3.6 + 0.7, b * 3.6 + 2.9) for b in range(4)]
    s.box(-0.5, W + 0.5, -1, z0, 0, 0.3, conc, 'lo'); s.box(-0.5, W + 0.5, z1, HB + 1, 0, 0.3, conc, 'hi')
    ed = [-0.5] + [v for p in wx for v in p] + [W + 0.5]
    for i in range(0, len(ed), 2):
        s.box(ed[i], ed[i + 1], z0, z1, 0, 0.3, conc, 'p')
    vine_patch(s, r, 10, (-0.5, HB + 0.5), big=1.6)
    return s


BANDS_A = [band_shopA, band_shopB, band_office, band_ribbon, band_tile, band_blind, band_gutted, band_silver]
BANDS_B = [band_curtain, lambda: band_curtain(19, 0.55, 'curtain2', (0.035, 0.05, 0.055)), band_qfront, band_fins,
           band_signwall, band_balcony, band_shopC, band_overgrown]


def build_atlas(name, bands, only=None):
    alb_atlas = np.zeros((2048, 2048, 4), np.float32)
    nrm_atlas = np.zeros((2048, 2048, 4), np.float32)
    nrm_atlas[..., :3] = (0.5, 0.5, 1.0)
    for row, fn in enumerate(bands):
        if only is not None and row not in only:
            continue
        s = fn()
        alb, nrm = s.render()
        s.cleanup()
        a = resize(alb, ROWPX, 2048)
        n = resize(nrm, ROWPX, 2048)
        ln = np.linalg.norm(n[..., :3] * 2 - 1, axis=-1, keepdims=True)
        n[..., :3] = ((n[..., :3] * 2 - 1) / np.maximum(ln, 1e-4)) * 0.5 + 0.5
        alb_atlas[row * ROWPX:(row + 1) * ROWPX] = a
        nrm_atlas[row * ROWPX:(row + 1) * ROWPX] = n
    alb_atlas[..., 3] = 1
    nrm_atlas[..., 3] = 1
    save_png(alb_atlas, f'{TEX}/{name}.png')
    save_png(nrm_atlas, f'{TEX}/{name}_n.png', colorspace='Non-Color', encode_srgb=False)


def main():
    build_atlas('facade_a', BANDS_A)
    build_atlas('facade_b', BANDS_B)
