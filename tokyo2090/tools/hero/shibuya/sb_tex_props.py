"""Props atlas (vehicles, vending machines, signals, rails, road signs) and signs atlas (signboards,
billboards, landmark signs). Cells are rendered as small facade-style shots."""
import math
import random
import numpy as np

import sb_surf as S
from sb_texlib import Shot, save_png, resize
from sb_tex_facade import SHOP_WORDS, FADED
from sb_common import TEX

# name: (x, y, w, h) px in a 2048 atlas (y from the top), metres (w, h)
PROPS = {}
SIGNS = {}


def _grid(table, cells):
    for name, (x, y, w, h, mw, mh) in cells.items():
        table[name] = ((x, y, w, h), (mw, mh))


_grid(PROPS, {
    # car body side panels by colour (one cell = 4.4 m x 1.5 m side, used for all sides / roof by UV)
    'car_white': (0, 0, 512, 192, 4.4, 1.6), 'car_silver': (512, 0, 512, 192, 4.4, 1.6),
    'car_black': (1024, 0, 512, 192, 4.4, 1.6), 'car_red': (1536, 0, 512, 192, 4.4, 1.6),
    'car_blue': (0, 192, 512, 192, 4.4, 1.6), 'car_taxi': (512, 192, 512, 192, 4.4, 1.6),
    'car_green': (1024, 192, 512, 192, 4.4, 1.6), 'car_brown': (1536, 192, 512, 192, 4.4, 1.6),
    'car_glass': (0, 384, 256, 128, 2.0, 1.0), 'car_tyre': (256, 384, 128, 128, 0.7, 0.7),
    'car_front': (384, 384, 384, 128, 1.8, 0.6), 'car_rear': (768, 384, 384, 128, 1.8, 0.6),
    'car_under': (1152, 384, 256, 128, 2.0, 1.0), 'car_seat': (1408, 384, 128, 128, 0.6, 0.6),
    'bus_side': (0, 512, 1536, 384, 11.0, 2.9), 'bus_front': (1536, 512, 384, 384, 2.5, 2.9),
    'vend_a': (0, 896, 256, 512, 1.0, 1.85), 'vend_b': (256, 896, 256, 512, 1.0, 1.85),
    'vend_c': (512, 896, 256, 512, 1.0, 1.85), 'vend_side': (768, 896, 128, 512, 0.7, 1.85),
    'sig_car': (896, 896, 384, 128, 1.3, 0.45), 'sig_ped': (896, 1024, 128, 256, 0.4, 0.8),
    'sign_blue1': (1024, 1024, 512, 256, 3.0, 1.5), 'sign_blue2': (1536, 1024, 512, 256, 3.0, 1.5),
    'rail': (896, 1280, 1024, 128, 4.0, 0.5), 'pedrail': (896, 1408, 1024, 128, 4.0, 0.8),
    'bike': (0, 1408, 256, 192, 1.8, 1.35), 'bike2': (256, 1408, 256, 192, 1.8, 1.35),
    'koban': (512, 1408, 384, 128, 3.0, 1.0), 'paint_white': (1920, 1280, 128, 128, 1.0, 1.0),
    'paint_grey': (1920, 1408, 128, 128, 1.0, 1.0), 'rust': (1536, 1536, 256, 256, 2.0, 2.0),
    'phone': (512, 1536, 256, 512, 0.9, 1.8), 'mailbox': (768, 1536, 128, 256, 0.45, 0.9),
    'cone': (896, 1536, 128, 128, 0.4, 0.4), 'stopsign': (1024, 1536, 256, 256, 0.9, 0.9),
    'nopark': (1280, 1536, 256, 256, 0.6, 0.6), 'ped_sign': (1792, 1536, 256, 256, 0.6, 0.6),
    'dark': (1792, 1792, 128, 128, 1.0, 1.0),
})

_grid(SIGNS, {
    # vertical signboards (tate-kanban) 0.9 x 4.5 m
    **{f'vert{i}': (i * 128, 0, 128, 640, 0.9, 4.5) for i in range(8)},
    # horizontal box signs 3 x 0.9 m
    **{f'hor{i}': (1024 + (i % 2) * 512, (i // 2) * 160, 512, 160, 3.0, 0.9) for i in range(8)},
    # billboards 8 x 4 m, faded posters
    'bill0': (0, 640, 512, 256, 8.0, 4.0), 'bill1': (512, 640, 512, 256, 8.0, 4.0),
    'bill2': (1024, 640, 512, 256, 8.0, 4.0), 'bill3': (1536, 640, 512, 256, 8.0, 4.0),
    # QFRONT big screen (dead LED modules) 20 x 26 m -> 512 x 640 px
    'qscreen': (0, 896, 512, 640, 20.0, 25.0),
    # Center-gai arch sign
    'centergai': (512, 896, 1024, 192, 16.0, 3.0),
    'magnet': (512, 1088, 1024, 192, 16.0, 3.0),
    'screen2': (1536, 896, 512, 384, 12.0, 9.0),
    # posters / small plates
    **{f'plate{i}': (512 + i * 128, 1280, 128, 128, 0.8, 0.8) for i in range(8)},
    'koban_sign': (1536, 1280, 512, 128, 4.0, 1.0),
    'hachi_plate': (1536, 1408, 256, 128, 0.8, 0.4),
    'grate': (1792, 1408, 256, 128, 2.0, 1.0),
})


def props_uv(name, u, v):
    (x, y, w, h), _m = PROPS[name]
    return ((x + u * w) / 2048.0, 1.0 - (y + (1 - v) * h) / 2048.0)


def signs_uv(name, u, v):
    (x, y, w, h), _m = SIGNS[name]
    return ((x + u * w) / 2048.0, 1.0 - (y + (1 - v) * h) / 2048.0)


def _shot(table, name, samples=10):
    (x, y, w, h), (mw, mh) = table[name]
    s = Shot(name, 0, mw, 0, mh, w, plane='XZ', samples=samples)
    s.rnd = random.Random(hash(name) & 0xfff)
    return s


def _put(atlas, table, name, a):
    (x, y, w, h), _ = table[name]
    atlas[y:y + h, x:x + w] = resize(a, h, w)


# ------------------------------------------------------------------ props
CAR_COLS = {'car_white': (0.55, 0.54, 0.50), 'car_silver': (0.36, 0.37, 0.37), 'car_black': (0.035, 0.035, 0.038),
            'car_red': (0.32, 0.05, 0.04), 'car_blue': (0.06, 0.12, 0.25), 'car_taxi': (0.48, 0.36, 0.06),
            'car_green': (0.08, 0.16, 0.10), 'car_brown': (0.18, 0.10, 0.06)}


def car_paint(c, seed):
    return S.paint(c, chip=0.8, fade=0.45, under=(0.12, 0.06, 0.03), seed=seed, streak=0.75, moss=0.3)


def build_props():
    atlas = np.zeros((2048, 2048, 4), np.float32)
    atlas[..., 3] = 1
    for i, (nm, c) in enumerate(CAR_COLS.items()):
        s = _shot(PROPS, nm)
        s.box(-1, 6, -1, 3, 0, 0.2, car_paint(c, i * 3.1))
        # panel seams and door lines
        for x in (1.3, 2.4, 3.4):
            s.box(x, x + 0.012, 0.1, 1.5, -0.01, 0.0, S.interior((0.02, 0.02, 0.02)))
        s.box(0, 4.4, 0.9, 0.912, -0.01, 0.0, S.interior((0.03, 0.03, 0.03)))
        if nm == 'car_taxi':
            s.box(0, 4.4, 0.55, 0.62, -0.01, 0.0, S.paint((0.4, 0.05, 0.04), seed=2))
        a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, nm, a)
    # empty windows: dark interior with a seat back, a few shards
    s = _shot(PROPS, 'car_glass')
    s.box(-1, 3, -1, 2, 0.5, 0.6, S.interior((0.035, 0.035, 0.032)))
    s.box(0.3, 0.9, 0.0, 0.7, 0.3, 0.4, S.flat_color((0.12, 0.10, 0.08), streak=0, moss=0.4))
    s.box(1.1, 1.7, 0.0, 0.7, 0.3, 0.4, S.flat_color((0.12, 0.10, 0.08), streak=0, moss=0.4))
    s.box(-0.1, 2.1, 0.92, 1.0, -0.01, 0.0, S.paint((0.3, 0.3, 0.29), seed=3))
    for x in (0.0, 0.95, 1.9):
        s.box(x, x + 0.1, 0.0, 1.0, -0.01, 0.0, S.paint((0.3, 0.3, 0.29), seed=4))
    s.poly([(0, 0), (0.6, 0), (0.1, 0.35)], 0.0, S.glass(seed=3))
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'car_glass', a)
    s = _shot(PROPS, 'car_tyre')
    N = 24
    s.mesh([(0.35, 0, 0.35)] + [(0.35 + 0.34 * math.cos(2 * math.pi * k / N), 0, 0.35 + 0.34 * math.sin(2 * math.pi * k / N)) for k in range(N)],
           [(0, 1 + k, 1 + (k + 1) % N) for k in range(N)], S.flat_color((0.03, 0.03, 0.03), streak=0, moss=0.2))
    s.mesh([(0.35, -0.01, 0.35)] + [(0.35 + 0.2 * math.cos(2 * math.pi * k / N), -0.01, 0.35 + 0.2 * math.sin(2 * math.pi * k / N)) for k in range(N)],
           [(0, 1 + k, 1 + (k + 1) % N) for k in range(N)], S.rust(seed=4))
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'car_tyre', a)
    for nm, lc in (('car_front', (0.5, 0.48, 0.42)), ('car_rear', (0.3, 0.04, 0.03))):
        s = _shot(PROPS, nm)
        s.box(-1, 3, -1, 2, 0, 0.2, car_paint((0.3, 0.3, 0.29), 7))
        s.box(0.1, 0.45, 0.25, 0.45, -0.02, 0, S.paint(lc, chip=0.3, seed=1))
        s.box(1.35, 1.7, 0.25, 0.45, -0.02, 0, S.paint(lc, chip=0.3, seed=2))
        if nm == 'car_front':
            s.box(0.55, 1.25, 0.2, 0.42, -0.02, 0, S.interior((0.03, 0.03, 0.03)))
        s.box(0.0, 1.8, 0.0, 0.14, -0.03, 0, S.rust(seed=5))
        s.box(0.7, 1.1, 0.16, 0.28, -0.04, -0.02, S.paint((0.55, 0.54, 0.5), seed=6))
        a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, nm, a)
    s = _shot(PROPS, 'car_under'); s.box(-1, 3, -1, 2, 0, 0.1, S.rust(seed=8)); a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'car_under', a)
    s = _shot(PROPS, 'car_seat'); s.box(-1, 2, -1, 2, 0, 0.1, S.flat_color((0.08, 0.065, 0.05), streak=0, moss=0.5)); a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'car_seat', a)
    # bus (Tokyu-like livery: ivory body, red band), windows empty
    s = _shot(PROPS, 'bus_side')
    body = S.paint((0.55, 0.53, 0.47), chip=0.5, fade=0.3, seed=11, streak=0.7, moss=0.25)
    s.box(-1, 12, -1, 4, 0, 0.2, body)
    s.box(-1, 12, 0.55, 0.85, -0.01, 0, S.paint((0.36, 0.05, 0.04), chip=0.5, seed=12))
    s.box(-1, 12, 2.55, 2.62, -0.01, 0, S.paint((0.36, 0.05, 0.04), chip=0.5, seed=13))
    for k in range(7):
        x = 0.4 + k * 1.45
        if 3.0 < x < 4.6:
            continue
        s.box(x, x + 1.3, 1.25, 2.4, -0.005, 0.0, S.interior((0.012, 0.012, 0.011)))
    s.box(3.0, 4.2, 0.1, 2.4, -0.005, 0, S.interior((0.015, 0.015, 0.014)))   # door
    for x in (1.2, 8.6):   # wheel arches
        s.box(x, x + 1.1, -0.2, 0.55, -0.005, 0, S.interior((0.02, 0.02, 0.02)))
    s.text('東急バス', 6.5, 0.7, 0.24, S.paint((0.5, 0.48, 0.42), seed=3), d=-0.012)
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'bus_side', a)
    s = _shot(PROPS, 'bus_front')
    s.box(-1, 4, -1, 4, 0, 0.2, body)
    s.box(0.15, 2.35, 1.2, 2.5, -0.005, 0, S.interior((0.012, 0.012, 0.011)))
    s.box(0.3, 2.2, 2.55, 2.8, -0.006, 0, S.interior((0.03, 0.03, 0.03)))
    s.text('渋谷駅', 1.25, 2.67, 0.16, S.paint((0.45, 0.35, 0.1), seed=4), d=-0.01)
    s.box(-1, 4, 0.55, 0.85, -0.01, 0, S.paint((0.36, 0.05, 0.04), chip=0.5, seed=12))
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'bus_front', a)
    # vending machines
    for nm, c in (('vend_a', (0.40, 0.05, 0.04)), ('vend_b', (0.05, 0.12, 0.30)), ('vend_c', (0.55, 0.54, 0.5))):
        s = _shot(PROPS, nm)
        s.box(-1, 2, -1, 3, 0, 0.2, S.paint(c, chip=0.5, fade=0.5, seed=len(nm), streak=0.6, moss=0.2))
        s.box(0.06, 0.94, 0.95, 1.75, -0.005, 0, S.flat_color((0.20, 0.21, 0.21), streak=0.2))   # display window
        rnd = random.Random(len(nm) + 7)
        for row in range(3):
            for col in range(8):
                x = 0.1 + col * 0.105; z = 1.02 + row * 0.24
                dc = rnd.choice(FADED)
                s.box(x, x + 0.07, z, z + 0.17, -0.01, -0.005, S.paint(dc, chip=0.2, fade=0.6, seed=row * 9 + col))
                s.box(x + 0.02, x + 0.05, z - 0.04, z - 0.02, -0.01, -0.005, S.flat_color((0.15, 0.15, 0.15)))
        s.box(0.06, 0.94, 0.12, 0.4, -0.005, 0, S.interior((0.02, 0.02, 0.02)))     # pick-up slot
        s.box(0.7, 0.85, 0.6, 0.85, -0.008, 0, S.metal((0.3, 0.3, 0.3)))
        a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, nm, a)
    s = _shot(PROPS, 'vend_side'); s.box(-1, 2, -1, 3, 0, 0.2, S.paint((0.45, 0.44, 0.4), chip=0.6, seed=3, streak=0.7, moss=0.3))
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'vend_side', a)
    # traffic signal heads (dead lamps)
    s = _shot(PROPS, 'sig_car')
    s.box(-1, 2, -1, 1, 0, 0.2, S.paint((0.32, 0.32, 0.30), chip=0.5, seed=1, streak=0.6))
    for k, lc in enumerate(((0.03, 0.07, 0.05), (0.09, 0.07, 0.02), (0.09, 0.025, 0.02))):
        x = 0.22 + k * 0.43
        N = 18
        s.mesh([(x, -0.01, 0.225)] + [(x + 0.15 * math.cos(2 * math.pi * i / N), -0.01, 0.225 + 0.15 * math.sin(2 * math.pi * i / N)) for i in range(N)],
               [(0, 1 + i, 1 + (i + 1) % N) for i in range(N)], S.glass(lc, seed=k))
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'sig_car', a)
    s = _shot(PROPS, 'sig_ped')
    s.box(-1, 1, -1, 1, 0, 0.2, S.paint((0.32, 0.32, 0.30), chip=0.5, seed=2))
    s.box(0.05, 0.35, 0.43, 0.75, -0.01, 0, S.glass((0.08, 0.02, 0.02), seed=1))
    s.box(0.05, 0.35, 0.05, 0.37, -0.01, 0, S.glass((0.02, 0.06, 0.06), seed=2))
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'sig_ped', a)
    # blue direction boards
    for nm, lines in (('sign_blue1', ('渋谷駅', 'Shibuya Sta.', '道玄坂 ←')), ('sign_blue2', ('原宿 Harajuku ↑', '青山 →', '代々木公園'))):
        s = _shot(PROPS, nm)
        s.box(-1, 4, -1, 2, 0, 0.2, S.paint((0.06, 0.13, 0.30), chip=0.4, fade=0.5, seed=len(nm), streak=0.5))
        s.box(0.05, 2.95, 0.05, 1.45, -0.004, 0, S.paint((0.06, 0.13, 0.30), chip=0.3, fade=0.5, seed=2))
        for i, ln in enumerate(lines):
            s.text(ln, 1.5, 1.15 - i * 0.42, 0.42, S.paint((0.55, 0.55, 0.52), chip=0.4, seed=i), d=-0.01)
        a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, nm, a)
    # guard rails
    s = _shot(PROPS, 'rail')
    s.box(-1, 5, -1, 1, 0.1, 0.2, S.interior((0.0, 0.0, 0.0)))
    s.box(-1, 5, 0.08, 0.42, 0, 0.05, S.paint((0.52, 0.51, 0.48), chip=0.6, fade=0.2, seed=3, streak=0.8))
    s.box(-1, 5, 0.22, 0.27, -0.02, 0, S.paint((0.45, 0.44, 0.41), chip=0.6, seed=4))
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'rail', a)
    s = _shot(PROPS, 'pedrail')   # tubular white pedestrian fence, alpha
    tub = S.paint((0.5, 0.49, 0.46), chip=0.6, fade=0.2, seed=5, streak=0.4)
    s.box(-1, 5, 0.72, 0.78, 0, 0.05, tub); s.box(-1, 5, 0.1, 0.15, 0, 0.05, tub)
    for k in range(0, 41):
        x = k * 0.1
        s.box(x, x + 0.025, 0.12, 0.75, 0, 0.05, tub)
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'pedrail', a)
    # bicycles (alpha silhouettes)
    for nm, fc in (('bike', (0.25, 0.04, 0.03)), ('bike2', (0.30, 0.31, 0.30))):
        s = _shot(PROPS, nm)
        fr = S.paint(fc, chip=0.6, seed=len(nm)); tyre = S.flat_color((0.03, 0.03, 0.03))
        for cx in (0.35, 1.45):
            N = 28
            for i in range(N):
                a0 = 2 * math.pi * i / N; a1 = 2 * math.pi * (i + 1) / N
                r0, r1 = 0.33, 0.30
                s.mesh([(cx + r0 * math.cos(a0), 0, 0.36 + r0 * math.sin(a0)), (cx + r0 * math.cos(a1), 0, 0.36 + r0 * math.sin(a1)),
                        (cx + r1 * math.cos(a1), 0, 0.36 + r1 * math.sin(a1)), (cx + r1 * math.cos(a0), 0, 0.36 + r1 * math.sin(a0))], [(0, 1, 2, 3)], tyre)
        def bar(p, q, w=0.025, m=fr):
            dx, dz = q[0] - p[0], q[1] - p[1]; L = math.hypot(dx, dz); nx, nz = -dz / L * w, dx / L * w
            s.mesh([(p[0] - nx, 0, p[1] - nz), (q[0] - nx, 0, q[1] - nz), (q[0] + nx, 0, q[1] + nz), (p[0] + nx, 0, p[1] + nz)], [(0, 1, 2, 3)], m)
        bar((0.35, 0.36), (0.8, 0.36)); bar((0.8, 0.36), (0.7, 0.85)); bar((0.35, 0.36), (0.7, 0.75)); bar((0.7, 0.75), (1.25, 0.8))
        bar((0.8, 0.36), (1.25, 0.8)); bar((1.25, 0.8), (1.45, 0.36)); bar((1.25, 0.8), (1.2, 1.05)); bar((1.1, 1.05), (1.35, 1.08), 0.02)
        bar((0.6, 0.88), (0.85, 0.88), 0.035, S.flat_color((0.04, 0.04, 0.04)))
        if nm == 'bike':
            bar((1.25, 1.0), (1.55, 1.0), 0.06, S.metal((0.3, 0.3, 0.3)))   # basket
        a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, nm, a)
    for nm, c in (('paint_white', (0.5, 0.49, 0.46)), ('paint_grey', (0.25, 0.25, 0.24))):
        s = _shot(PROPS, nm); s.box(-1, 2, -1, 2, 0, 0.1, S.paint(c, chip=0.5, seed=len(nm), streak=0.6, moss=0.2))
        a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, nm, a)
    s = _shot(PROPS, 'rust'); s.box(-1, 3, -1, 3, 0, 0.1, S.rust(seed=3, moss=0.2)); a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'rust', a)
    s = _shot(PROPS, 'dark'); s.box(-1, 2, -1, 2, 0, 0.1, S.interior()); a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'dark', a)
    s = _shot(PROPS, 'koban')
    s.box(-1, 4, -1, 2, 0, 0.1, S.paint((0.5, 0.49, 0.45), chip=0.4, seed=2))
    s.text('KOBAN  交番', 1.5, 0.5, 0.75, S.paint((0.08, 0.10, 0.25), chip=0.4, seed=3), d=-0.01)
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'koban', a)
    s = _shot(PROPS, 'phone')   # public phone booth panel (green)
    s.box(-1, 2, -1, 3, 0, 0.1, S.paint((0.08, 0.20, 0.10), chip=0.5, seed=4))
    s.box(0.08, 0.82, 0.3, 1.6, -0.005, 0, S.interior((0.02, 0.025, 0.02)))
    s.text('公衆電話', 0.45, 1.7, 0.13, S.paint((0.5, 0.5, 0.45), seed=1), d=-0.01)
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'phone', a)
    s = _shot(PROPS, 'mailbox'); s.box(-1, 2, -1, 2, 0, 0.1, S.paint((0.36, 0.05, 0.04), chip=0.5, seed=5))
    s.box(0.08, 0.37, 0.6, 0.66, -0.005, 0, S.interior()); a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'mailbox', a)
    s = _shot(PROPS, 'cone'); s.box(-1, 2, -1, 2, 0, 0.1, S.paint((0.45, 0.12, 0.03), chip=0.4, seed=6)); s.box(-1, 2, 0.15, 0.25, -0.005, 0, S.paint((0.5, 0.5, 0.48), seed=7))
    a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, 'cone', a)
    for nm, c, t in (('stopsign', (0.38, 0.04, 0.03), '止まれ'), ('nopark', (0.06, 0.12, 0.30), ''), ('ped_sign', (0.06, 0.12, 0.30), '')):
        s = _shot(PROPS, nm)
        (x, y, w, h), (mw, mh) = PROPS[nm]
        N = 3 if nm == 'stopsign' else 32
        r = mw * 0.48
        cxp, czp = mw / 2, mh / 2
        ang0 = -math.pi / 2 if N == 3 else 0
        pts = [(cxp + r * math.cos(ang0 + 2 * math.pi * i / N + (math.pi if N == 3 else 0)), 0, czp + r * math.sin(ang0 + 2 * math.pi * i / N + (math.pi if N == 3 else 0))) for i in range(N)]
        s.mesh([(cxp, 0, czp)] + pts, [(0, 1 + i, 1 + (i + 1) % N) for i in range(N)], S.paint(c, chip=0.4, fade=0.5, seed=len(nm)))
        if t:
            s.text(t, cxp, czp + 0.08, 0.17, S.paint((0.55, 0.55, 0.52), seed=1), d=-0.01)
        if nm == 'nopark':
            s.box(cxp - 0.24, cxp + 0.24, czp - 0.03, czp + 0.03, -0.01, 0, S.paint((0.38, 0.04, 0.03), seed=2))
        a, _n = s.render(); s.cleanup(); _put(atlas, PROPS, nm, a)
    save_png(atlas, f'{TEX}/props.png')


# ------------------------------------------------------------------ signs
VERT_WORDS = ['カラオケ', 'ラーメン', '居酒屋', '焼肉', 'まんが喫茶', 'ゲームセンター', '中古ブランド', 'くすり', '英会話',
              'メガネ', '牛丼', '整体', 'ネイル', '美容室', 'パチンコ', '質', 'たばこ', 'ホテル']


def build_signs():
    atlas = np.zeros((2048, 2048, 4), np.float32)
    rnd = random.Random(77)
    for i in range(8):
        nm = f'vert{i}'
        s = _shot(SIGNS, nm)
        c = rnd.choice(FADED)
        s.box(0.02, 0.88, 0.02, 4.48, 0, 0.1, S.paint(c, chip=0.45, fade=0.3, seed=i, streak=0.7, moss=0.15))
        s.box(0.0, 0.9, 0.0, 4.5, 0.05, 0.12, S.rust(seed=i))
        w = rnd.choice(VERT_WORDS)
        tc = (0.62, 0.6, 0.55) if sum(c) < 1.2 else (0.1, 0.09, 0.08)
        size = min(0.95, 4.0 / max(1, len(w)) * 1.1)
        s.text(w, 0.45, 2.25, size, S.paint(tc, chip=0.5, fade=0.3, seed=i + 3), d=-0.01, vertical=True)
        if rnd.random() < 0.5:
            s.text(rnd.choice(['2F', '3F', 'B1F', '4F']), 0.45, 0.25, 0.22, S.paint(tc, seed=1), d=-0.01)
        a, _n = s.render(); s.cleanup(); _put(atlas, SIGNS, nm, a)
    for i in range(8):
        nm = f'hor{i}'
        s = _shot(SIGNS, nm)
        c = rnd.choice(FADED)
        s.box(0.02, 2.98, 0.02, 0.88, 0, 0.1, S.paint(c, chip=0.45, fade=0.3, seed=i + 20, streak=0.6, moss=0.15))
        s.box(0.0, 3.0, 0.0, 0.9, 0.05, 0.12, S.rust(seed=i))
        w = rnd.choice(SHOP_WORDS)
        tc = (0.62, 0.6, 0.55) if sum(c) < 1.2 else (0.1, 0.09, 0.08)
        size = min(0.95, 2.6 / max(1, len(w)) * 1.6)
        s.text(w, 1.5, 0.45, size, S.paint(tc, chip=0.5, fade=0.3, seed=i + 33), d=-0.01)
        a, _n = s.render(); s.cleanup(); _put(atlas, SIGNS, nm, a)
    # faded billboards: big soft shapes (a face, a bottle, a phone) washed out by the sun
    for i in range(4):
        nm = f'bill{i}'
        s = _shot(SIGNS, nm)
        base = rnd.choice([(0.45, 0.42, 0.38), (0.35, 0.40, 0.45), (0.45, 0.35, 0.30), (0.40, 0.42, 0.36)])
        s.box(0.05, 7.95, 0.05, 3.95, 0, 0.1, S.paint(base, chip=0.8, fade=0.8, under=(0.3, 0.3, 0.28), seed=i + 50, streak=0.8))
        for k in range(rnd.randint(2, 4)):
            cx = rnd.uniform(1, 7); cz = rnd.uniform(0.8, 3.2); r = rnd.uniform(0.5, 1.6)
            N = 20
            s.mesh([(cx, -0.01, cz)] + [(cx + r * math.cos(2 * math.pi * j / N), -0.01, cz + r * 1.2 * math.sin(2 * math.pi * j / N)) for j in range(N)],
                   [(0, 1 + j, 1 + (j + 1) % N) for j in range(N)], S.paint(rnd.choice(FADED), chip=0.7, fade=0.75, seed=k + i * 7))
        s.text(rnd.choice(['SHIBUYA', 'NEW', '2030 SUMMER', 'COLLECTION', '新発売', 'LIVE']), 4, 0.6, 0.55,
               S.paint((0.55, 0.53, 0.5), chip=0.7, fade=0.5, seed=i), d=-0.02)
        # torn: holes are alpha (no geometry) -> leave a few gaps by not covering parts
        a, _n = s.render(); s.cleanup()
        # tear the bottom edge
        h, w = a.shape[:2]
        cols = np.arange(w)
        tear = (h * (0.65 + 0.3 * np.abs(np.sin(cols * 0.05 + i) * np.cos(cols * 0.013 * (i + 1))))).astype(int)
        for x in range(w):
            if rnd.random() < 0.7:
                a[tear[x]:, x, 3] = 0
        _put(atlas, SIGNS, nm, a)
    # QFRONT screen: a dead LED board, black modules, some fallen out showing the rusty lattice behind
    s = _shot(SIGNS, 'qscreen')
    lat = S.rust(seed=7)
    for xi in range(0, 21):
        s.box(xi - 0.05, xi + 0.05, 0, 25, 0.25, 0.35, lat)
    for zi in range(0, 26):
        s.box(0, 20, zi - 0.05, zi + 0.05, 0.25, 0.35, lat)
    for xi in range(20):
        for zi in range(25):
            miss = 0.06 + 0.35 * (zi < 6) * (xi > 9) + 0.12 * (zi > 20)
            if rnd.random() < miss:
                continue
            x = xi + 0.01; z = zi + 0.01
            g = rnd.uniform(0.012, 0.03)
            s.box(x, x + 0.98, z, z + 0.98, 0.0, 0.05, S.flat_color((g, g, g * 1.1), streak=0.5, mottle=0.3, seed=xi * 31 + zi))
    a, _n = s.render(); s.cleanup(); _put(atlas, SIGNS, 'qscreen', a)
    # other screen (MAGNET / station side), dark grid
    s = _shot(SIGNS, 'screen2')
    s.box(0, 12, 0, 9, 0.3, 0.4, S.interior((0.01, 0.01, 0.01)))
    for xi in range(12):
        for zi in range(9):
            if rnd.random() < 0.3:
                continue
            s.box(xi + 0.03, xi + 0.97, zi + 0.03, zi + 0.97, 0, 0.05, S.flat_color((0.03, 0.03, 0.032), seed=xi + zi * 13))
    a, _n = s.render(); s.cleanup(); _put(atlas, SIGNS, 'screen2', a)
    # Center-gai arch sign: SHIBUYA CENTER GAI with the red/white style, faded
    s = _shot(SIGNS, 'centergai')
    s.box(0.1, 15.9, 0.1, 2.9, 0, 0.1, S.paint((0.50, 0.49, 0.46), chip=0.5, fade=0.3, seed=9, streak=0.7))
    s.box(0.1, 15.9, 2.55, 2.9, -0.005, 0.0, S.paint((0.38, 0.05, 0.04), chip=0.5, seed=8))
    s.box(0.1, 15.9, 0.1, 0.45, -0.005, 0.0, S.paint((0.38, 0.05, 0.04), chip=0.5, seed=7))
    s.text('SHIBUYA CENTER GAI', 8.0, 1.6, 1.9, S.paint((0.36, 0.05, 0.04), chip=0.5, fade=0.3, seed=6), d=-0.01, spacing=1.05)
    s.text('渋谷センター街', 8.0, 0.75, 0.75, S.paint((0.1, 0.09, 0.08), chip=0.5, seed=5), d=-0.01)
    a, _n = s.render(); s.cleanup(); _put(atlas, SIGNS, 'centergai', a)
    s = _shot(SIGNS, 'magnet')
    s.box(0.1, 15.9, 0.1, 2.9, 0, 0.1, S.paint((0.06, 0.06, 0.065), chip=0.4, fade=0.2, seed=19, streak=0.6))
    s.text('MAGNET by SHIBUYA109', 8.0, 1.5, 2.0, S.paint((0.52, 0.5, 0.46), chip=0.55, fade=0.3, seed=16), d=-0.01)
    a, _n = s.render(); s.cleanup(); _put(atlas, SIGNS, 'magnet', a)
    for i in range(8):
        nm = f'plate{i}'
        s = _shot(SIGNS, nm)
        c = rnd.choice(FADED)
        s.box(0.0, 0.8, 0.0, 0.8, 0, 0.1, S.paint(c, chip=0.5, fade=0.6, seed=i + 70))
        s.text(rnd.choice(['P', '¥', '薬', '酒', 'ATM', '〒', '駐輪', '禁煙']), 0.4, 0.4, 0.36, S.paint((0.6, 0.58, 0.54), seed=i), d=-0.01)
        a, _n = s.render(); s.cleanup(); _put(atlas, SIGNS, nm, a)
    s = _shot(SIGNS, 'koban_sign')
    s.box(0, 4, 0, 1, 0, 0.1, S.paint((0.5, 0.49, 0.45), chip=0.4, seed=91))
    s.text('渋谷駅前交番', 2, 0.5, 0.75, S.paint((0.1, 0.1, 0.2), seed=92), d=-0.01)
    a, _n = s.render(); s.cleanup(); _put(atlas, SIGNS, 'koban_sign', a)
    s = _shot(SIGNS, 'hachi_plate')
    s.box(0, 0.8, 0, 0.4, 0, 0.1, S.metal((0.12, 0.10, 0.07), ox=0.6, seed=4, rust=0.2))
    s.text('忠犬ハチ公', 0.4, 0.2, 0.2, S.paint((0.30, 0.26, 0.16), seed=93), d=-0.01, fnt=None)
    a, _n = s.render(); s.cleanup(); _put(atlas, SIGNS, 'hachi_plate', a)
    s = _shot(SIGNS, 'grate')   # rebar mesh / grating (alpha)
    rb = S.rust(seed=5)
    for k in range(21):
        s.box(k * 0.1, k * 0.1 + 0.02, 0, 1, 0, 0.02, rb)
    for k in range(11):
        s.box(0, 2, k * 0.1, k * 0.1 + 0.02, -0.01, 0.01, rb)
    a, _n = s.render(); s.cleanup(); _put(atlas, SIGNS, 'grate', a)
    # bleed colour into transparent texels (mip halos)
    rgb = atlas[..., :3]; A = atlas[..., 3:4]
    m = (A > 0.5).astype(np.float32)
    for it in range(4):
        acc = np.zeros_like(rgb); cnt = np.zeros_like(A)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(rgb * m, dy, 0), dx, 1); cnt += np.roll(np.roll(m, dy, 0), dx, 1)
        fill = (m == 0) & (cnt > 0)
        rgb = np.where(fill, acc / np.maximum(cnt, 1e-6), rgb)
        m = np.where(fill, 1.0, m)
    atlas[..., :3] = rgb
    save_png(atlas, f'{TEX}/signs.png')


def main():
    build_props()
    build_signs()
