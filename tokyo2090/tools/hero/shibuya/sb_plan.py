"""Per-building style and ruin plan for shibuya."""
import math
import random
import hashlib
import numpy as np

from sb_bldg import Ruin

P109 = np.array((-58.0, -43.0))
DOGEN = np.array((-115.0, -95.0))
XING = np.array((80.0, -50.0))


def intensity(x, y):
    d1 = math.hypot(x - P109[0], y - P109[1])
    d2 = math.hypot(x - DOGEN[0], y - DOGEN[1])
    d3 = math.hypot(x - XING[0], y - XING[1])
    v = 0.28 + 0.55 * math.exp(-(d1 / 85) ** 2) + 0.5 * math.exp(-(d2 / 75) ** 2) - 0.35 * math.exp(-(d3 / 55) ** 2)
    return max(0.05, min(1.0, v))


def seed_of(name):
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 100000


# signature buildings (ids from buildings.json; see NOTES)
SPECIAL = {
    'b003': 'qfront',     # QFRONT, NW corner of the crossing
    'b012': 'magnet',     # MAGNET by SHIBUYA109, NE corner
    'b007': '109',        # SHIBUYA109 at the fork
    'b006': 'ekimae',     # SW corner of the crossing
    'b021': 'centergai_s',
    'b008': 'seibu_a',
    'b009': 'seibu_b',
    'b000': 'collapse',   # big one south of Dogenzaka, partly collapsed into the street
    'b001': 'dogen_tall',
    'b002': 'bunka_tall',
}


def plan(name, info, V):
    s = seed_of(name)
    r = random.Random(s)
    cx, cy = info['cx'], info['cy']
    z0 = float(V[:, 2].min()); z1 = float(V[:, 2].max()); h = z1 - z0
    I = intensity(cx, cy)
    use = info.get('use', '')
    foot = np.ptp(V[:, 0]) * np.ptp(V[:, 1])
    ruin = Ruin(s)
    kw = dict(seed=s, breach=0.05 + 0.22 * I)
    sp = SPECIAL.get(name)

    if sp == 'qfront':
        style = 'qfront'
        ruin.wedge((47.3, -9.0), z0 + 30, k=1.2, amp=2.0)          # far west corner chewed
        kw['breach'] = 0.04
    elif sp == 'magnet':
        style = 'magnet'
        ruin.shear(z0 + h * 0.86, direction=(0, 1), slope=-0.25, origin=(116, 0), amp=4.0)
        kw['breach'] = 0.06
    elif sp == '109':
        style = 'silver'
        # main body sheared on the west, cylinder kept
        ruin.shear(z0 + 24, direction=(1, -0.2), slope=0.45, origin=(-80, -40), amp=4.0)
        ruin.core((-57.6, -43.8), (6.6, 6.6), 1e9)                 # the cylinder stands
        kw['breach'] = 0.10
    elif sp == 'ekimae':
        style = 'office'
        ruin.wedge((10.0, -106.0), z0 + 12, k=0.9, amp=2.5)
        kw['breach'] = 0.08
    elif sp == 'centergai_s':
        style = 'commercial'
        ruin.shear(z0 + h * 0.7, direction=(-1, 0.3), slope=0.3, origin=(26, -12), amp=4.0)
    elif sp in ('seibu_a', 'seibu_b'):
        style = 'fins'
        ruin.shear(z0 + h * 0.78, direction=(-1, 0.1), slope=0.18, origin=(cx, cy), amp=4.0)
        kw['breach'] = 0.08
    elif sp == 'collapse':
        style = 'glass'
        ruin.shear(z0 + 30, direction=(0.2, -1), slope=-0.55, origin=(-60, -100), amp=4.0)
        ruin.hole((-68, -80), 17, z0 + 4.0, amp=2.0)               # the bite that fell into Dogenzaka
        kw['breach'] = 0.16
    elif sp == 'dogen_tall':
        style = 'office'
        ruin.shear(z0 + 22, direction=(1, -0.4), slope=0.5, origin=(-124, -50), amp=4.0)
        ruin.wedge((-99, -79), z0 + 6, k=1.0, amp=2)
        kw['breach'] = 0.2
    elif sp == 'bunka_tall':
        style = 'glass'
        ruin.shear(z0 + h * 0.62, direction=(-1, -0.5), slope=0.45, origin=(-3, -9), amp=4.0)
        kw['breach'] = 0.12
    else:
        if h > 34 and foot > 700:
            style = r.choice(['office', 'glass', 'fins', 'commercial'])
        elif '住宅' in use:
            style = r.choice(['tile', 'mixed'])
        else:
            style = r.choice(['commercial', 'commercial', 'mixed', 'tile', 'office'])
        if h > 22 and r.random() < (0.2 + 0.7 * I if h > 34 else 0.1 + 0.55 * I):
            ang = r.random() * 2 * math.pi
            if r.random() < 0.5:
                slope = r.uniform(0.0, 0.12)                                  # ragged crown
            else:
                slope = math.tan(math.radians(r.uniform(32, 64)))             # a cliff across the building
            ruin.shear(z0 + h * (0.45 + 0.4 * r.random() * (1.2 - I)), direction=(math.cos(ang), math.sin(ang)),
                       slope=slope, origin=(cx, cy), amp=r.uniform(3.0, 4.5))
        if h > 14 and r.random() < 0.45 * I:
            i = r.randrange(len(V))
            ruin.wedge((V[i, 0], V[i, 1]), z0 + h * (0.15 + 0.4 * r.random()), k=0.7 + r.random(), amp=2.0)
    # a stair core standing proud of a sheared top
    if ruin.parts and ruin.parts[0][0] == 'shear' and h > 28 and (r.random() < 0.55 or sp in ('collapse', 'dogen_tall', 'bunka_tall')):
        zc = ruin.parts[0][1]
        cxp = cx + r.uniform(-6, 6); cyp = cy + r.uniform(-6, 6)
        ruin.core((cxp, cyp), (r.uniform(2.5, 3.5), r.uniform(3.0, 4.5)), min(z1, zc + r.uniform(5, 14)), ang=r.uniform(0, 3.14))
    return style, ruin, kw
