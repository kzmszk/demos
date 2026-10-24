"""Street props: abandoned cars and a bus, traffic signals, guard rails, vending machines, bicycles,
street lamps, signboards on the facades, rubble heaps."""
import math
import random

import numpy as np
from mathutils import Matrix, Vector

from sb_mesh import MB, vnoise, fbm
from sb_tex_props import props_uv, signs_uv, PROPS, SIGNS
import sb_geom as G


class X:
    """local -> world transform for props"""

    def __init__(self, x, y, z, yaw=0.0, pitch=0.0, roll=0.0, s=1.0):
        self.M = (Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(pitch, 4, 'Y')
                  @ Matrix.Rotation(roll, 4, 'X') @ Matrix.Scale(s, 4))

    def __call__(self, p):
        v = self.M @ Vector(p)
        return (v.x, v.y, v.z)


def box(mb, xf, x0, x1, y0, y1, z0, z1, uvs, mat='props', col=(1, 1, 1, 1), skip=()):
    """uvs: dict face -> (cell, table) or callable(face)->4 uvs. faces: 'px','nx','py','ny','pz','nz'"""
    V = {
        'nx': [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
        'px': [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        'ny': [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        'py': [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
        'pz': [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        'nz': [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)],
    }
    for f, pts in V.items():
        if f in skip:
            continue
        u = uvs.get(f, uvs.get('*'))
        if u is None:
            continue
        if callable(u):
            uv = u(f)
        else:
            cell, fn = u
            uv = [fn(cell, 0, 0), fn(cell, 1, 0), fn(cell, 1, 1), fn(cell, 0, 1)]
        mb.face([xf(p) for p in pts], uv, mat, col)


def cylinder(mb, xf, c, r, z0, z1, sides, cell, fn=props_uv, mat='props', col=(1, 1, 1, 1), axis='z', caps=True, capcell=None):
    pts0 = []; pts1 = []
    for k in range(sides):
        a = 2 * math.pi * k / sides
        if axis == 'z':
            pts0.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), z0)); pts1.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), z1))
        else:   # along y (wheels): c = (x, z)
            pts0.append((c[0] + r * math.cos(a), z0, c[1] + r * math.sin(a))); pts1.append((c[0] + r * math.cos(a), z1, c[1] + r * math.sin(a)))
    for k in range(sides):
        a, b = k, (k + 1) % sides
        P = [pts0[a], pts0[b], pts1[b], pts1[a]] if axis == 'z' else [pts0[b], pts0[a], pts1[a], pts1[b]]
        mb.face([xf(p) for p in P], [fn(cell, k / sides, 0), fn(cell, (k + 1) / sides, 0), fn(cell, (k + 1) / sides, 1), fn(cell, k / sides, 1)], mat, col)
    if caps:
        cc = capcell or cell
        for ring, flip in ((pts0, True), (pts1, False)):
            uv = [fn(cc, 0.5 + 0.5 * math.cos(2 * math.pi * k / sides), 0.5 + 0.5 * math.sin(2 * math.pi * k / sides)) for k in range(sides)]
            P = [xf(p) for p in ring]
            if (flip and axis == 'z') or (not flip and axis != 'z'):
                P = P[::-1]; uv = uv[::-1]
            mb.face(P, uv, mat, col)


# ------------------------------------------------------------------ vehicles
CAR_TYPES = {
    #           L     W     belt  roof  cab0 cab1 (fractions of L)
    'sedan':  (4.6, 1.75, 0.85, 1.42, 0.30, 0.78),
    'kei':    (3.4, 1.48, 0.85, 1.65, 0.18, 0.95),
    'van':    (4.7, 1.70, 0.95, 1.90, 0.12, 0.97),
    'hatch':  (4.0, 1.70, 0.85, 1.50, 0.25, 0.92),
}
CAR_COLS = ['car_white', 'car_white', 'car_silver', 'car_silver', 'car_black', 'car_red', 'car_blue', 'car_green', 'car_brown']


def car(mb, x, y, z, yaw, rnd, kind=None, paint=None, collide=None):
    kind = kind or rnd.choice(['sedan', 'sedan', 'kei', 'van', 'hatch', 'kei'])
    L, W, belt, roof, c0, c1 = CAR_TYPES[kind]
    paint = paint or rnd.choice(CAR_COLS)
    sink = rnd.uniform(0.06, 0.16)
    xf = X(x, y, z - sink, yaw, rnd.uniform(-0.04, 0.04), rnd.uniform(-0.05, 0.05))
    g = rnd.uniform(0.75, 1.0)
    col = (g, g * rnd.uniform(0.95, 1.02), g * rnd.uniform(0.88, 1.0), 1)
    hx = L / 2; hy = W / 2
    pu = lambda cell: (cell, props_uv)
    side = lambda f: [props_uv(paint, 0, 0.15), props_uv(paint, 1, 0.15), props_uv(paint, 1, 0.55), props_uv(paint, 0, 0.55)]
    # lower body (chamfered front and back tops)
    zb = 0.32
    P = {
        'fl': (-hx, -hy, zb), 'fr': (-hx, hy, zb), 'bl': (hx, -hy, zb), 'br': (hx, hy, zb),
        'flt': (-hx + 0.12, -hy, belt - 0.12), 'frt': (-hx + 0.12, hy, belt - 0.12),
        'blt': (hx - 0.1, -hy, belt - 0.06), 'brt': (hx - 0.1, hy, belt - 0.06),
        'fl2': (-hx + 0.5, -hy, belt), 'fr2': (-hx + 0.5, hy, belt), 'bl2': (hx - 0.35, -hy, belt), 'br2': (hx - 0.35, hy, belt),
    }
    T = lambda k: xf(P[k])
    U = lambda c, us: [props_uv(c, u, v) for u, v in us]
    # sides (pentagons)
    mb.face([T('fl'), T('bl'), T('blt'), T('bl2'), T('fl2'), T('flt')],
            U(paint, [(0, 0), (1, 0), (0.98, 0.5), (0.92, 0.6), (0.1, 0.6), (0.03, 0.5)]), 'props', col)
    mb.face([T('br'), T('fr'), T('frt'), T('fr2'), T('br2'), T('brt')],
            U(paint, [(0, 0), (1, 0), (0.97, 0.5), (0.9, 0.6), (0.08, 0.6), (0.02, 0.5)]), 'props', col)
    # front, back, hood, trunk, bottom
    mb.face([T('fr'), T('fl'), T('flt'), T('frt')], U('car_front', [(0, 0), (1, 0), (1, 1), (0, 1)]), 'props', col)
    mb.face([T('bl'), T('br'), T('brt'), T('blt')], U('car_rear', [(0, 0), (1, 0), (1, 1), (0, 1)]), 'props', col)
    mb.face([T('flt'), T('fl2'), T('fr2'), T('frt')], U(paint, [(0, 0.6), (0.2, 0.6), (0.2, 1), (0, 1)]), 'props', col)
    mb.face([T('bl2'), T('blt'), T('brt'), T('br2')], U(paint, [(0.8, 0.6), (1, 0.6), (1, 1), (0.8, 1)]), 'props', col)
    mb.face([T('fl'), T('fr'), T('br'), T('bl')], U('car_under', [(0, 0), (1, 0), (1, 1), (0, 1)]), 'props', col)
    # cabin frustum
    a0 = -hx + c0 * L; a1 = -hx + c1 * L
    t0 = a0 + (0.45 if kind in ('sedan', 'hatch') else 0.2); t1 = a1 - (0.3 if kind == 'sedan' else 0.1)
    ib = 0.05; it = 0.16
    C = {'a': (a0, -hy + ib, belt), 'b': (a1, -hy + ib, belt), 'c': (a1, hy - ib, belt), 'd': (a0, hy - ib, belt),
         'e': (t0, -hy + it, roof), 'f': (t1, -hy + it, roof), 'g': (t1, hy - it, roof), 'h': (t0, hy - it, roof)}
    Tc = lambda k: xf(C[k])
    gl = [(0, 0), (1, 0), (1, 1), (0, 1)]
    mb.face([Tc('a'), Tc('b'), Tc('f'), Tc('e')], U('car_glass', gl), 'props', col)
    mb.face([Tc('c'), Tc('d'), Tc('h'), Tc('g')], U('car_glass', gl), 'props', col)
    mb.face([Tc('d'), Tc('a'), Tc('e'), Tc('h')], U('car_glass', gl), 'props', col)
    mb.face([Tc('b'), Tc('c'), Tc('g'), Tc('f')], U('car_glass', gl), 'props', col)
    mb.face([Tc('e'), Tc('f'), Tc('g'), Tc('h')], U(paint, [(0.3, 0.7), (0.7, 0.7), (0.7, 0.95), (0.3, 0.95)]), 'props', col)
    # pillars as thin paint strips are in the texture; wheels (flat tyres)
    for wx in (-hx + 0.75, hx - 0.75):
        for sy in (-1, 1):
            r = 0.31
            cx, cz = wx, 0.27 + sink * 0.3
            y0 = sy * (hy - 0.22); y1 = sy * (hy - 0.02)
            if sy < 0:
                y0, y1 = y1, y0
            cylinder(mb, xf, (cx, cz), r, y0, y1, 8, 'car_tyre', axis='y', caps=True, col=col)
    if collide is not None:
        collide.append(('box', xf, (-hx, hx, -hy, hy, 0.0, roof)))
    return xf, roof


def bus(mb, x, y, z, yaw, rnd, collide=None):
    L, W, H = 10.8, 2.5, 3.05
    sink = 0.15
    xf = X(x, y, z - sink, yaw, rnd.uniform(-0.03, 0.03), rnd.uniform(-0.04, 0.04))
    hx, hy = L / 2, W / 2
    col = (0.95, 0.95, 0.92, 1)
    U = lambda c, us: [props_uv(c, u, v) for u, v in us]
    zb = 0.35
    # sides
    mb.face([xf((-hx, -hy, zb)), xf((hx, -hy, zb)), xf((hx, -hy, H)), xf((-hx, -hy, H))], U('bus_side', [(0, 0.08), (1, 0.08), (1, 1), (0, 1)]), 'props', col)
    mb.face([xf((hx, hy, zb)), xf((-hx, hy, zb)), xf((-hx, hy, H)), xf((hx, hy, H))], U('bus_side', [(1, 0.08), (0, 0.08), (0, 1), (1, 1)]), 'props', col)
    mb.face([xf((-hx, hy, zb)), xf((-hx, -hy, zb)), xf((-hx, -hy, H)), xf((-hx, hy, H))], U('bus_front', [(0, 0.08), (1, 0.08), (1, 1), (0, 1)]), 'props', col)
    mb.face([xf((hx, -hy, zb)), xf((hx, hy, zb)), xf((hx, hy, H)), xf((hx, -hy, H))], U('bus_front', [(0, 0.08), (1, 0.08), (1, 0.4), (0, 0.4)]), 'props', col)
    mb.face([xf((-hx, -hy, H)), xf((hx, -hy, H)), xf((hx, hy, H)), xf((-hx, hy, H))], U('paint_white', [(0, 0), (1, 0), (1, 1), (0, 1)]), 'props', col)
    mb.face([xf((-hx, hy, zb)), xf((hx, hy, zb)), xf((hx, -hy, zb)), xf((-hx, -hy, zb))], U('car_under', [(0, 0), (1, 0), (1, 1), (0, 1)]), 'props', col)
    for wx in (-hx + 1.9, hx - 2.3):
        for sy in (-1, 1):
            y0 = sy * (hy - 0.3); y1 = sy * (hy - 0.02)
            if sy < 0:
                y0, y1 = y1, y0
            cylinder(mb, xf, (wx, 0.42), 0.48, y0, y1, 10, 'car_tyre', axis='y', col=col)
    if collide is not None:
        collide.append(('box', xf, (-hx, hx, -hy, hy, 0.0, H)))
    return xf, H


# ------------------------------------------------------------------ street furniture
def signal_pole(mb, x, y, z, yaw, rnd, arm=4.5, fallen=False, lean=0.0, collide=None):
    """Japanese traffic signal: pole, cantilever arm, horizontal 3-lamp head, pedestrian heads on the pole"""
    if fallen:
        xf = X(x, y, z + 0.15, yaw, math.radians(rnd.uniform(80, 88)), 0)
    else:
        xf = X(x, y, z, yaw, lean, rnd.uniform(-0.03, 0.03))
    H = 5.6
    cylinder(mb, xf, (0, 0), 0.11, -0.5, H, 6, 'paint_grey', caps=False)
    # arm
    box(mb, xf, 0.0, arm, -0.05, 0.05, H - 0.4, H - 0.3, {'*': ('paint_grey', props_uv)})
    # car signal head at the arm end, facing -y
    hx = arm - 0.7
    box(mb, xf, hx - 0.65, hx + 0.65, -0.18, 0.12, H - 0.75, H - 0.3,
        {'ny': ('sig_car', props_uv), '*': ('paint_grey', props_uv)})
    # visors: thin
    # pedestrian heads on the pole facing +y and -x
    box(mb, xf, -0.2, 0.2, 0.12, 0.42, 2.4, 3.2, {'py': ('sig_ped', props_uv), '*': ('paint_grey', props_uv)})
    box(mb, xf, -0.42, -0.12, -0.2, 0.2, 2.4, 3.2, {'nx': ('sig_ped', props_uv), '*': ('paint_grey', props_uv)})
    if collide is not None:
        if fallen:
            collide.append(('box', xf, (-0.15, 0.15, -0.15, 0.15, 0.0, H)))
        else:
            collide.append(('box', xf, (-0.3, 0.3, -0.3, 0.3, 0.0, 2.2)))


def street_lamp(mb, x, y, z, yaw, rnd, lean=0.0):
    xf = X(x, y, z, yaw, lean, rnd.uniform(-0.04, 0.04))
    cylinder(mb, xf, (0, 0), 0.08, -0.3, 7.5, 5, 'paint_grey', caps=False)
    box(mb, xf, 0.0, 1.8, -0.04, 0.04, 7.3, 7.4, {'*': ('paint_grey', props_uv)})
    box(mb, xf, 1.5, 2.2, -0.15, 0.15, 7.1, 7.32, {'*': ('paint_grey', props_uv)})


def vending(mb, x, y, z, yaw, rnd, toppled=False, collide=None):
    cell = rnd.choice(['vend_a', 'vend_b', 'vend_c'])
    if toppled:
        xf = X(x, y, z + 0.35, yaw, 0, math.radians(-88))
    else:
        xf = X(x, y, z - 0.05, yaw, 0, rnd.uniform(-0.03, 0.03))
    g = rnd.uniform(0.8, 1.0)
    box(mb, xf, -0.5, 0.5, -0.35, 0.35, 0, 1.85, {'ny': (cell, props_uv), 'pz': ('paint_grey', props_uv), '*': ('vend_side', props_uv)},
        col=(g, g, g, 1), skip=('nz',))
    if collide is not None:
        collide.append(('box', xf, (-0.5, 0.5, -0.35, 0.35, 0, 1.85)))


def bicycle(mb, x, y, z, yaw, rnd, lying=False):
    cell = rnd.choice(['bike', 'bike2'])
    xf = X(x, y, z + (0.05 if lying else 0), yaw, 0, math.radians(84) if lying else rnd.uniform(-0.15, 0.15))
    P = [(-0.9, 0, 0), (0.9, 0, 0), (0.9, 0, 1.35), (-0.9, 0, 1.35)]
    mb.face([xf(p) for p in P], [props_uv(cell, 0, 0), props_uv(cell, 1, 0), props_uv(cell, 1, 1), props_uv(cell, 0, 1)], 'props')


def ped_fence(mb, a, b, ground, rnd, h=0.8, broken=0.15):
    """white tubular pedestrian fence along a-b (double-sided alpha quads)"""
    a = np.array(a, float); b = np.array(b, float)
    L = float(np.hypot(*(b - a)))
    n = max(1, int(L / 4.0))
    for i in range(n):
        if rnd.random() < broken:
            continue
        p = a + (b - a) * (i / n); q = a + (b - a) * ((i + 1) / n)
        zp = ground(*p); zq = ground(*q)
        tilt = rnd.uniform(0, 0.25) if rnd.random() < 0.25 else 0.0
        d = (q - p) / max(1e-6, np.hypot(*(q - p)))
        nrm = np.array([-d[1], d[0]]) * tilt * h
        P = [(p[0], p[1], zp), (q[0], q[1], zq), (q[0] + nrm[0], q[1] + nrm[1], zq + h * math.cos(tilt)), (p[0] + nrm[0], p[1] + nrm[1], zp + h * math.cos(tilt))]
        mb.face(P, [props_uv('pedrail', 0, 0), props_uv('pedrail', 1, 0), props_uv('pedrail', 1, 1), props_uv('pedrail', 0, 1)], 'props')


def guard_rail(mb, a, b, ground, rnd):
    a = np.array(a, float); b = np.array(b, float)
    L = float(np.hypot(*(b - a)))
    n = max(1, int(L / 4.0))
    for i in range(n):
        p = a + (b - a) * (i / n); q = a + (b - a) * ((i + 1) / n)
        zp = ground(*p); zq = ground(*q)
        sag = rnd.uniform(0, 0.25)
        P = [(p[0], p[1], zp + 0.4), (q[0], q[1], zq + 0.4 - sag), (q[0], q[1], zq + 0.85 - sag), (p[0], p[1], zp + 0.85)]
        mb.face(P, [props_uv('rail', 0, 0.1), props_uv('rail', 1, 0.1), props_uv('rail', 1, 0.9), props_uv('rail', 0, 0.9)], 'props')
        # post
        xf = X(p[0], p[1], zp, 0)
        box(mb, xf, -0.05, 0.05, -0.05, 0.05, 0, 0.8, {'*': ('paint_white', props_uv)}, skip=('nz', 'pz'))


# ------------------------------------------------------------------ facade signs
def facade_signs(mb, building, rnd, density=0.5):
    """projecting vertical signboards and flat box signs on the street-facing walls of floors 1..5"""
    if not building.sections:
        return
    S0 = building.sections[0]
    nf = len(building.floors)
    for ring, hole in S0:
        if hole:
            continue
        P = np.array(ring)
        for e in range(len(P)):
            p = P[e]; q = P[(e + 1) % len(P)]
            d = q - p; L = float(np.hypot(*d))
            if L < 4:
                continue
            t = d / L; nrm = np.array([t[1], -t[0]])
            k = 0.0
            while k < L - 2:
                k += rnd.uniform(3.0, 9.0) / density
                if k > L - 1:
                    break
                fl = rnd.randint(1, min(5, nf - 1)) if nf > 2 else 1
                if fl >= nf:
                    continue
                z0 = building.floors[fl][0]
                m = p + t * k
                # the wall must still stand there
                if building.ruin(np.array([m - nrm * 0.8]))[0] < z0 + 4.6:
                    continue
                if rnd.random() < 0.55:
                    # projecting vertical sign
                    cell = f'vert{rnd.randrange(8)}'
                    out = rnd.uniform(0.15, 0.35)
                    a0 = m + nrm * out; a1 = m + nrm * (out + 0.9)
                    h = 4.5 * rnd.uniform(0.7, 1.0)
                    zt = z0 + h + rnd.uniform(0, 1.0)
                    sag = rnd.uniform(-0.2, 0.2) if rnd.random() < 0.3 else 0.0
                    Pp = [(a0[0], a0[1], zt - h), (a1[0], a1[1], zt - h + sag), (a1[0], a1[1], zt + sag), (a0[0], a0[1], zt)]
                    uv = [signs_uv(cell, 0, 0), signs_uv(cell, 1, 0), signs_uv(cell, 1, 1), signs_uv(cell, 0, 1)]
                    mb.face(Pp, uv, 'signs')
                    # brackets
                    for zz in (zt - h + 0.3, zt - 0.3):
                        mb.quad((m[0], m[1], zz), (a0[0], a0[1], zz), (a0[0], a0[1], zz + 0.06), (m[0], m[1], zz + 0.06),
                                [(0, 0), (0.1, 0), (0.1, 0.03), (0, 0.03)], 'metal')
                else:
                    cell = f'hor{rnd.randrange(8)}'
                    w = 3.0; h = 0.9
                    c = m + nrm * 0.12
                    a0 = c - t * w / 2; a1 = c + t * w / 2
                    zb = z0 + rnd.uniform(0.2, 2.4)
                    Pp = [(a0[0], a0[1], zb), (a1[0], a1[1], zb), (a1[0], a1[1], zb + h), (a0[0], a0[1], zb + h)]
                    mb.face(Pp, [signs_uv(cell, 0, 0), signs_uv(cell, 1, 0), signs_uv(cell, 1, 1), signs_uv(cell, 0, 1)], 'signs')


# ------------------------------------------------------------------ rubble
HEAP_PTS = []


def rubble_heap(mb, cx, cy, ground, rx, ry, h, rnd, rot=0.0, step=1.0, zbase=None, collide_tris=None, col=(1, 1, 1, 1),
                profile='cone', toward=None):
    """noise-displaced heap on the ground (rubble material). profile 'cone' or 'ramp' (rises linearly toward
    'toward' (unit 2D) to height h at the far end)."""
    nx = max(2, int(2 * rx / step)); ny = max(2, int(2 * ry / step))
    ca, sa = math.cos(rot), math.sin(rot)
    seed = rnd.randint(0, 9999)
    Z = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            u = (i / nx) * 2 - 1; v = (j / ny) * 2 - 1
            x = cx + (u * rx) * ca - (v * ry) * sa
            y = cy + (u * rx) * sa + (v * ry) * ca
            r = math.sqrt(u * u + v * v)
            n = fbm(x, y, 3.0, seed, 3)
            if profile == 'cone':
                f = max(0.0, 1 - r) ** 1.3
                hh = h * f * (0.75 + 0.5 * n)
            else:
                along = (u + 1) / 2
                edge = max(0.0, 1 - abs(v) ** 3)
                hh = h * along * edge * (0.85 + 0.3 * n) * min(1.0, (1 - r * 0.55) * 1.6)
            gz = ground(x, y) if zbase is None else zbase
            Z[(i, j)] = (x, y, gz + max(-0.3, hh - 0.25))
    for i in range(nx):
        for j in range(ny):
            pts = [Z[(i, j)], Z[(i + 1, j)], Z[(i + 1, j + 1)], Z[(i, j + 1)]]
            if all(p[2] < (ground(p[0], p[1]) if zbase is None else zbase) - 0.05 for p in pts):
                continue
            uvs = [(p[0] / 4.0, p[1] / 4.0) for p in pts]
            mb.face(pts, uvs, 'rubble', col)
    HEAP_PTS.extend(v for v in Z.values() if v[2] > (ground(v[0], v[1]) if zbase is None else zbase) + 0.3)
    if collide_tris is not None:
        # a coarser copy for the collision proxy (every second grid line)
        for i in range(0, nx, 2):
            for j in range(0, ny, 2):
                i2 = min(nx, i + 2); j2 = min(ny, j + 2)
                pts = [Z[(i, j)], Z[(i2, j)], Z[(i2, j2)], Z[(i, j2)]]
                if all(p[2] < (ground(p[0], p[1]) if zbase is None else zbase) - 0.05 for p in pts):
                    continue
                collide_tris.append(pts)


def chunks(mb, cx, cy, z, n, spread, rnd, ground=None, size=(0.3, 1.4)):
    for k in range(n):
        x = cx + rnd.gauss(0, spread); y = cy + rnd.gauss(0, spread)
        zz = ground(x, y) if ground else z
        s = rnd.uniform(*size)
        xf = X(x, y, zz - s * 0.2, rnd.uniform(0, 6.28), rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5))
        sx, sy, sz = s * rnd.uniform(0.6, 1.4), s * rnd.uniform(0.6, 1.4), s * rnd.uniform(0.25, 0.6)
        uvf = lambda f, s=s: [(0, 0), (s / 4, 0), (s / 4, s / 8), (0, s / 8)]
        box(mb, xf, -sx / 2, sx / 2, -sy / 2, sy / 2, 0, sz, {'*': uvf}, mat='concrete', col=(0.85, 0.84, 0.8, 1), skip=('nz',))
