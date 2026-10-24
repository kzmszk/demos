"""Placement of street props, rubble and the collapse ramp."""
import math
import random

import numpy as np

import sb_props as Pr
from sb_plan import intensity

XING = np.array((78.0, -52.0))
CAR_TOPS = []


def _road_lines(osm, kinds=('tertiary', 'primary', 'secondary', 'unclassified', 'residential', 'tertiary_link')):
    for r in osm['roads']:
        if r['hw'] not in kinds or r['tunnel'] or (r['layer'] or 0) < 0 or r['bridge']:
            continue
        yield r, np.array(r['line'], float)


def place(mb, bldgs, fp, ground, osm, rnd, collide):
    inbox = lambda x, y: -153 < x < 153 and -123 < y < 123
    from sb_stage import SPAWNS
    cars = [(sp['x'], sp['y']) for sp in SPAWNS for _ in range(1)]
    def free(x, y, r=3.2):
        if any((x - sp['x']) ** 2 + (y - sp['y']) ** 2 < 64 for sp in SPAWNS):
            return False
        return all((x - cx) ** 2 + (y - cy) ** 2 > r * r for cx, cy in cars)

    # ---- the bus caught mid-crossing and a jam on the scramble
    bx, by = 72.0, -49.5
    Pr.bus(mb, bx, by, ground(bx, by), -0.16 + 0.22, rnd, collide)
    cars += [(bx - 3, by), (bx, by), (bx + 3, by)]
    for (x, y, yaw) in ((90.0, -43.0, 1.75), (82.5, -49.0, -1.25), (63.0, -58.5, 0.05), (80.5, -64.0, 3.0),
                        (57.0, -45.0, -0.1), (96.0, -39.0, 1.9)):
        xf, roof = Pr.car(mb, x, y, ground(x, y), yaw + rnd.gauss(0, 0.15), rnd, collide=collide)
        CAR_TOPS.append(xf((0.3, 0, roof)))
        cars.append((x, y))
    # ---- cars along the roads
    for r, L in _road_lines(osm):
        w = r['width'] or 5.0
        if w < 4.5:
            continue
        seg = np.diff(L, axis=0)
        for i in range(len(seg)):
            p = L[i]; d = seg[i]; ln = float(np.hypot(*d))
            if ln < 1:
                continue
            t = d / ln; nrm = np.array([-t[1], t[0]])
            s = rnd.uniform(0, 8)
            while s < ln:
                c = p + t * s
                lane = rnd.choice((-1, 1)) * w * rnd.uniform(0.18, 0.3)
                q = c + nrm * lane
                x, y = float(q[0]), float(q[1])
                s += rnd.uniform(7, 22) * (1.6 if w < 8 else 1.0)
                if not inbox(x, y) or fp(x, y) or not fp.dist_free(x, y, 2.0) or not free(x, y):
                    continue
                if np.hypot(x - XING[0], y - XING[1]) < 26:
                    continue
                yaw = math.atan2(t[1], t[0]) + (math.pi if lane > 0 else 0) + rnd.gauss(0, 0.12)
                if rnd.random() < 0.1:
                    yaw += rnd.uniform(-0.8, 0.8)
                xf, roof = Pr.car(mb, x, y, ground(x, y), yaw, rnd, collide=collide)
                CAR_TOPS.append(xf((0.3, 0, roof)))
                cars.append((x, y))
    # ---- traffic signals: the scramble corners + OSM signal points
    poles = [((51.5, -36.5), -2.4), ((99.5, -31.5), 2.6), ((104.0, -67.0), 1.0), ((57.5, -69.0), -0.7),
             ((66.0, -35.5), -3.0), ((86.5, -74.5), 0.4)]
    for p in osm['points']:
        if p['tags'].get('highway') == 'traffic_signals':
            x, y = p['xy']
            if inbox(x, y) and all(np.hypot(x - a[0], y - a[1]) > 15 for a, _y in poles):
                poles.append(((x + rnd.uniform(-4, 4), y + rnd.uniform(-4, 4)), rnd.uniform(0, 6.28)))
    for (x, y), yaw in poles:
        if fp(x, y):
            continue
        u = rnd.random()
        Pr.signal_pole(mb, x, y, ground(x, y), yaw, rnd, arm=rnd.uniform(3.0, 6.0), fallen=u < 0.25,
                       lean=rnd.uniform(0.05, 0.3) if u < 0.6 else 0.0, collide=collide)
    # ---- street lamps along the wider roads
    for r, L in _road_lines(osm, ('tertiary', 'primary')):
        w = r['width'] or 6.0
        acc = rnd.uniform(0, 20)
        for i in range(len(L) - 1):
            p = L[i]; d = L[i + 1] - p; ln = float(np.hypot(*d))
            t = d / max(ln, 1e-6); nrm = np.array([-t[1], t[0]])
            while acc < ln:
                c = p + t * acc + nrm * (w / 2 + 0.6) * rnd.choice((-1, 1))
                acc += rnd.uniform(18, 30)
                x, y = float(c[0]), float(c[1])
                if inbox(x, y) and not fp(x, y) and np.hypot(x - XING[0], y - XING[1]) > 18:
                    side = 1 if np.dot(np.array([x, y]) - p, nrm) < 0 else -1
                    Pr.street_lamp(mb, x, y, ground(x, y), math.atan2(nrm[1], nrm[0]) * 1 + (0 if side > 0 else math.pi), rnd,
                                   lean=rnd.uniform(0, 0.25) if rnd.random() < 0.4 else 0.0)
            acc -= ln
    # ---- pedestrian fences along the big roads near the crossing
    for r, L in _road_lines(osm, ('tertiary',)):
        w = r['width'] or 6.0
        if w < 9:
            continue
        for i in range(len(L) - 1):
            p = L[i]; q = L[i + 1]
            d = q - p; ln = float(np.hypot(*d))
            if ln < 3:
                continue
            t = d / ln; nrm = np.array([-t[1], t[0]])
            for side in (-1, 1):
                a = p + nrm * side * (w / 2 + 0.3); b = q + nrm * side * (w / 2 + 0.3)
                m = (a + b) / 2
                if not inbox(*m) or np.hypot(*(m - XING)) < 24 or np.hypot(*(m - XING)) > 120:
                    continue
                Pr.ped_fence(mb, a, b, ground, rnd)
    # ---- vending machines against walls, bicycles on the pavements
    cand = []
    for b in bldgs.values():
        if not b.sections:
            continue
        for ring, hole in b.sections[0]:
            if hole:
                continue
            P = np.array(ring)
            for e in range(len(P)):
                p = P[e]; q = P[(e + 1) % len(P)]
                d = q - p; ln = float(np.hypot(*d))
                if ln < 4:
                    continue
                t = d / ln; nrm = np.array([t[1], -t[0]])
                m = p + t * rnd.uniform(1.5, ln - 1.5) + nrm * 0.45
                if fp(*(m + nrm * 2.5)) or not inbox(*m):
                    continue
                cand.append((m, t, nrm))
    rnd.shuffle(cand)
    for (m, t, nrm) in cand[:40]:
        yaw = math.atan2(-nrm[1], -nrm[0]) - math.pi / 2 + math.pi
        n = rnd.randint(1, 3)
        for k in range(n):
            c = m + t * (k * 1.05)
            Pr.vending(mb, c[0], c[1], ground(*c), math.atan2(nrm[1], nrm[0]) - math.pi / 2 + math.pi, rnd,
                       toppled=rnd.random() < 0.12, collide=collide)
    for (m, t, nrm) in cand[40:110]:
        n = rnd.randint(2, 7)
        for k in range(n):
            c = m + t * (k * 0.6) + nrm * rnd.uniform(0.5, 1.5)
            Pr.bicycle(mb, c[0], c[1], ground(*c), math.atan2(nrm[1], nrm[0]) + rnd.gauss(0, 0.2), rnd, lying=rnd.random() < 0.4)
    # ---- signboards on the facades
    for b in bldgs.values():
        I = intensity(b.info['cx'], b.info['cy'])
        Pr.facade_signs(mb, b, rnd, density=0.55 + 0.3 * (1 - abs(I - 0.5)))
    return cars


def rubble(mb, bldgs, fp, ground, rnd, collide_tris):
    """rubble cones at the feet of broken buildings and the collapse ramp into Dogenzaka"""
    for name, b in bldgs.items():
        if not b.ruin.parts or not b.sections:
            continue
        I = intensity(b.info['cx'], b.info['cy'])
        h = b.z1 - b.z0
        n = int((1 + h / 15) * (0.5 + I))
        S0 = b.sections[0]
        ring = max((r for r, hh in S0 if not hh), key=lambda r: abs(sum(1 for _ in r)), default=None)
        if ring is None:
            continue
        P = np.array(ring)
        for k in range(n):
            e = rnd.randrange(len(P))
            p = P[e]; q = P[(e + 1) % len(P)]
            d = q - p; ln = float(np.hypot(*d))
            if ln < 2:
                continue
            t = d / ln; nrm = np.array([t[1], -t[0]])
            c = p + t * rnd.uniform(0, ln) + nrm * rnd.uniform(0.5, 3.0)
            if np.hypot(*(c - XING)) < 28:
                continue
            rx = rnd.uniform(2.5, 4 + h / 8); ry = rnd.uniform(2, 3.5 + h / 10)
            Pr.rubble_heap(mb, c[0], c[1], ground, rx, ry, rnd.uniform(0.8, 1.6 + h / 25), rnd, rot=math.atan2(t[1], t[0]),
                           collide_tris=collide_tris)
            Pr.chunks(mb, c[0], c[1], 0, rnd.randint(3, 8), rx * 0.6, rnd, ground=ground)
    # rubble on the broken slabs
    for b in bldgs.values():
        for (x, y, z, top) in b.exposed[::7]:
            if rnd.random() < 0.25 and b.ruin.parts:
                Pr.rubble_heap(mb, x, y, ground, rnd.uniform(1.2, 2.5), rnd.uniform(1.0, 2.0), rnd.uniform(0.3, 0.8), rnd,
                               rot=rnd.uniform(0, 3), step=0.8, zbase=z, collide_tris=None)
    # the collapse of b000 into Dogenzaka: a climbable ramp from the street into the bite
    gx, gy = -66.0, -80.0
    Pr.rubble_heap(mb, gx, gy, ground, 12.0, 9.0, 10.0, rnd, rot=-math.pi / 2 + 0.12, step=1.2, profile='ramp',
                   collide_tris=collide_tris)
    Pr.chunks(mb, gx, gy + 6, 0, 26, 7.0, rnd, ground=ground, size=(0.6, 2.2))
    Pr.rubble_heap(mb, -58.0, -66.0, ground, 7.0, 5.0, 1.8, rnd, rot=0.3, collide_tris=collide_tris)
