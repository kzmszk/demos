"""Keyakizaka-dori: the sloping avenue south of the tower.  Zelkova rows grown into one huge canopy, the day's
traffic stopped under it (rusted, tyres flat, plants through), lamp posts, guard rails, shop signs."""
import math
import numpy as np
import lib, veg, props
from lib import norm

CW = 6.5       # half width of the carriageway (m)
TREE_OFF = 8.2


def road_line():
    O = lib.osm()
    segs = [r['line'] for r in O['roads'] if r['name'] == 'けやき坂']
    main = max(segs, key=len)              # (163,-83) ... (-113,-74)
    return [np.array(p) for p in main]


def build(sc, col, ctx):
    G = ctx['ground']; occ = ctx['occ']
    rr = lib.rng(2003)
    line = road_line()
    # extend west along the upper part toward the Grand Hyatt
    O = lib.osm()
    for r in O['roads']:
        if r['name'] == 'けやき坂' and r['line'][0][0] < -100 and len(r['line']) == 6:
            line = line + [np.array(p) for p in r['line'][1:]]
    pts = lib.resample_ring(line, 1.0)[:-1] if False else None
    # walk the polyline at fixed spacing
    def walk(step, offset, jitter=0.0):
        out = []
        acc = 0.0
        for i in range(len(line) - 1):
            a, b = line[i], line[i + 1]
            L = float(np.linalg.norm(b - a)); u = (b - a) / L; nrm = np.array([-u[1], u[0]])
            while acc < L:
                q = a + u * acc + nrm * offset
                out.append((q, u, nrm))
                acc += step + rr.uniform(-jitter, jitter)
            acc -= L
        return out
    # zelkova rows, both sides
    n = 0
    for side in (-1, 1):
        for (q, u, nrm) in walk(10.5, side * TREE_OFF, 1.0):
            if not (lib.BOX[0] - 5 < q[0] < lib.BOX[2] + 5 and lib.BOX[1] - 5 < q[1] < lib.BOX[3] + 5):
                continue
            if occ.get(q[0], q[1]) == 1:
                continue
            h = rr.uniform(19, 25); R = rr.uniform(8.5, 11.0)
            veg.tree(sc, col, (q[0], q[1], G(q[0], q[1])), 'zelkova', h, R, 3000 + n, 'foliage_keyaki', density=1.0)
            occ.fill_circle(q[0], q[1], 2.0, 9)
            n += 1
    mid = lib.mid()
    # lamp posts between the trees (Keyakizaka's slim posts), some fallen
    for side in (-1, 1):
        for (q, u, nrm) in (walk(21.0, side * (TREE_OFF - 0.6), 0.0) if not mid else []):
            q2 = q + u * 5.0
            if occ.get(q2[0], q2[1]) not in (0, 9):
                continue
            props.lamp(sc, (q2[0], q2[1], G(q2[0], q2[1])), math.atan2(-nrm[1] * side, -nrm[0] * side), rr, 7.5,
                       fallen=rr.random() < 0.2)
    # guard rails along the kerbs (broken runs)
    for side in ((-1, 1) if not mid else ()):
        run = []
        for (q, u, nrm) in walk(2.0, side * (CW + 0.4)):
            if rr.random() < 0.04:
                if len(run) > 2:
                    props.guardrail(sc, run, lambda p: G(p[0], p[1]), rr)
                run = []
            elif lib.BOX[0] < q[0] < lib.BOX[2]:
                run.append(q)
        if len(run) > 2:
            props.guardrail(sc, run, lambda p: G(p[0], p[1]), rr)
    # the stopped traffic: two lanes, some bunched, a bus, taxis
    lanes = (-CW * 0.45, CW * 0.45)
    k = 0
    for (q, u, nrm) in walk(7.5, 0.0, 2.5):
        if not (lib.BOX[0] + 4 < q[0] < lib.BOX[2] - 4):
            continue
        if rr.random() < 0.35:
            continue
        lane = rr.choice(lanes)
        p = q + nrm * (lane + rr.uniform(-0.4, 0.4))
        if not occ.free(p[0], p[1], 2.0):
            continue
        hd = math.atan2(u[1], u[0]) + (0 if lane > 0 else math.pi) + rr.uniform(-0.25, 0.25)
        kind = 'bus' if (k == 6) else rr.choice(['sedan', 'sedan', 'taxi', 'van', 'kei', 'sedan'])
        props.car(sc, col, (p[0], p[1], G(p[0], p[1])), hd, rr, kind)
        occ.fill_circle(p[0], p[1], 3.0 if kind != 'bus' else 6.0, 6)
        k += 1
    ctx['n_cars_keyaki'] = k
    # undergrowth along the kerbs and in the median cracks
    F = sc['foliage_keyaki']
    for side in ((-1, 1) if not mid else ()):
        for (q, u, nrm) in walk(3.0, side * (CW + 1.2), 1.0):
            if occ.get(q[0], q[1]) in (0, 9) and rr.random() < 0.7:
                veg.bush(F, (q[0], q[1], G(q[0], q[1])), rr.uniform(0.5, 1.3), rr)
    # signs: street name plates + shop signs on the shopfronts facing the street
    for i, (q, u, nrm) in enumerate(walk(36.0, CW + 5.5) if not mid else []):
        for side in (-1, 1):
            p = q + nrm * (side - 1) * (CW + 5.5)
            if occ.get(p[0], p[1]) != 0:
                continue
            fac = math.atan2(-nrm[1] * side, -nrm[0] * side)
            props.sign_board(sc, (p[0], p[1], G(p[0], p[1]) + 2.6), fac, 2.2, 0.55, rr.choice([0, 1, 5, 6, 10, 7]), True)
            lib.tube(sc['metal'], [(p[0], p[1], G(p[0], p[1])), (p[0], p[1], G(p[0], p[1]) + 3.2)], [0.05, 0.05], sides=4)
    # pedestrian crossing at the arena steps (decals added by decals.py from ctx)
    ctx['crossings'] = ctx.get('crossings', []) + [((18.5, -84.5), (0.0, 1.0), 2 * CW)]
    ctx['keyaki_line'] = [tuple(p) for p in line]
    ctx['labels'].append({'name': 'けやき坂', 'x': 20.0, 'y': -85.0, 'z': 45.0, 'kind': 'place'})
