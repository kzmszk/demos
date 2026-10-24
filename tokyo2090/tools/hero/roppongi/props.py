"""Props: abandoned cars/vans/buses, street lamps, traffic signals, guard rails, vending machines, bicycles,
rubble heaps and concrete chunks.  build() scatters cars on the other roads in the box and rubble at collapses."""
import math
import numpy as np
import lib, veg
from lib import norm, vnoise

PAINT = 4


def _strip(k):
    return 0.5 + 0.125 * k + 0.004, 0.625 + 0.125 * k - 0.004


def car(sc, col, p, heading, rr, kind='sedan', tilt=0.0, plant=True):
    """p=(x,y,z ground). heading: math angle of the car's forward axis."""
    C = sc['car']
    L, Wd, H, cab0, cab1 = {'sedan': (4.6, 1.78, 1.42, 0.30, 0.78), 'van': (4.7, 1.80, 1.95, 0.12, 0.95),
                            'kei': (3.4, 1.48, 1.62, 0.15, 0.92), 'bus': (10.5, 2.5, 3.1, 0.02, 0.98),
                            'taxi': (4.7, 1.70, 1.50, 0.28, 0.76)}[kind]
    k = rr.randrange(PAINT)
    if kind == 'taxi':
        k = 3 if rr.random() < 0.5 else 0
    v0, v1 = _strip(k)
    ca, sa = math.cos(heading), math.sin(heading)
    sink = rr.uniform(0.12, 0.3)       # flat tyres, sunk into the litter
    x0, y0, z0 = p
    def P(x, y, z):
        return np.array([x0 + x * ca - y * sa, y0 + x * sa + y * ca, z0 + z - sink + tilt * x * 0.1])
    hl, hw = L / 2, Wd / 2
    zb = 0.32; zs = H * 0.55 if kind != 'bus' else 0.9     # sill / belt line
    ch = 0.12                                              # chamfer
    # lower body: 8-sided prism along x (chamfered box)
    prof = [(-hw, zb), (hw, zb), (hw, zs - ch), (hw - ch, zs), (-hw + ch, zs), (-hw, zs - ch)]
    xs = [-hl, -hl + 0.25, hl - 0.25, hl]
    def ring(x, shrink):
        return [P(x, y * shrink, z) for (y, z) in prof]
    rings = [ring(-hl, 0.92), ring(-hl + 0.25, 1.0), ring(hl - 0.25, 1.0), ring(hl, 0.92)]
    for r in range(3):
        for j in range(len(prof)):
            a, b = rings[r][j], rings[r][(j + 1) % len(prof)]
            c_, d = rings[r + 1][(j + 1) % len(prof)], rings[r + 1][j]
            u0 = (r / 3); u1 = (r + 1) / 3
            C.poly([a, b, c_, d], [(u0, v0), (u0, v1), (u1, v1), (u1, v0)])
    for r, rv in ((0, True), (3, False)):
        pts = rings[r][::-1] if rv else rings[r]
        C.poly(pts, [(0.2 + 0.1 * j, v0 + 0.01) for j in range(len(pts))])
    # cabin: trapezoid from cab0..cab1 of the length, windows = dark band
    cx0 = -hl + L * cab0; cx1 = -hl + L * cab1
    top_in = 0.18 if kind in ('sedan', 'taxi') else 0.05
    gs0, gs1 = 0.25, 0.5
    cab = [P(cx0, -hw * 0.92, zs), P(cx1, -hw * 0.92, zs), P(cx1, hw * 0.92, zs), P(cx0, hw * 0.92, zs),
           P(cx0 + L * top_in, -hw * 0.82, H), P(cx1 - L * top_in * 0.6, -hw * 0.82, H),
           P(cx1 - L * top_in * 0.6, hw * 0.82, H), P(cx0 + L * top_in, hw * 0.82, H)]
    gl = (0.02, gs0 + 0.01, 0.48, gs1 - 0.01)       # window (dark interior) region u0,v0,u1,v1
    for (a, b, c_, d) in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        C.poly([cab[a], cab[b], cab[c_], cab[d]], [(gl[0], gl[1]), (gl[2], gl[1]), (gl[2], gl[3]), (gl[0], gl[3])])
    C.poly([cab[4], cab[5], cab[6], cab[7]], [(0.1, v0 + 0.02), (0.5, v0 + 0.02), (0.5, v1 - 0.02), (0.1, v1 - 0.02)])
    # wheels: squashed 6-gons (flat tyres)
    for wx in (-hl + 0.75, hl - 0.75) if kind != 'bus' else (-hl + 1.8, hl - 2.2):
        for s in (-1, 1):
            c = (wx, s * (hw - 0.12))
            r = 0.33 if kind != 'bus' else 0.5
            pts = []
            for i in range(6):
                a = 2 * math.pi * i / 6
                pts.append((c[0] + math.cos(a) * r, max(0.0, r + math.sin(a) * r * 0.85) + 0.02))
            ring_o = [P(x, c[1] + s * 0.11, z) for x, z in pts]; ring_i = [P(x, c[1] - s * 0.11, z) for x, z in pts]
            for i in range(6):
                C.poly([ring_i[i], ring_i[(i + 1) % 6], ring_o[(i + 1) % 6], ring_o[i]][::s],
                       [(0.55, 0.26), (0.95, 0.26), (0.95, 0.49), (0.55, 0.49)])
            C.poly(ring_o if s > 0 else ring_o[::-1], [(0.6 + 0.05 * i, 0.3) for i in range(6)])
    col.box((x0, y0, z0 - 0.2), (L, Wd, H - sink + 0.2), heading)
    if plant and rr.random() < 0.45:
        F = sc['foliage_streets']
        veg.bush(F, (x0, y0, z0 + H * 0.7), rr.uniform(0.6, 1.2), rr)
        if rr.random() < 0.3:
            veg.tree(sc, col, (x0 + ca * 0.3, y0 + sa * 0.3, z0 + 0.3), 'young', rr.uniform(3.5, 6), 2.0, rr.randrange(1 << 30),
                     'foliage_streets', collide=False)


def lamp(sc, p, facing, rr, h=8.0, fallen=False):
    M = sc['metal']
    x, y, z = p
    if fallen:
        a = rr.uniform(0, 2 * math.pi)
        d = np.array([math.cos(a), math.sin(a)])
        lib.tube(M, [np.array([x, y, z + 0.15]), np.array([x + d[0] * h, y + d[1] * h, z + 0.2])], [0.1, 0.07], sides=5)
        lib.tube(M, [np.array([x, y, z]), np.array([x, y, z + 0.6])], [0.11, 0.1], sides=5)
        return
    d = np.array([math.cos(facing), math.sin(facing)])
    lean = np.array([rr.uniform(-0.2, 0.2), rr.uniform(-0.2, 0.2)]) if rr.random() < 0.3 else np.zeros(2)
    top = np.array([x + lean[0] * h * 0.1, y + lean[1] * h * 0.1, z + h])
    lib.tube(M, [np.array([x, y, z]), top], [0.11, 0.07], sides=5)
    arm = top + np.r_[d * 1.8, 0.25]
    lib.tube(M, [top, top + np.r_[d * 0.9, 0.3], arm], [0.05, 0.05, 0.05], sides=4)
    lib.box(M, (arm[0], arm[1], arm[2] - 0.25), (0.7, 0.35, 0.22), facing, 0.5)


def signal(sc, col, p, facing, rr, fallen=False):
    M = sc['metal']; S = sc['signs']
    x, y, z = p
    d = np.array([math.cos(facing), math.sin(facing)])
    if fallen:
        e = np.array([x, y, z + 0.2]) + np.r_[d * 6.0, 0.0]
        lib.tube(M, [np.array([x, y, z + 0.2]), e], [0.13, 0.1], sides=5)
        lib.box(M, (e[0], e[1], z), (1.2, 0.4, 0.4), facing, 0.5)
        return
    top = np.array([x, y, z + 5.6])
    lib.tube(M, [np.array([x, y, z]), top], [0.13, 0.11], sides=5)
    arm = top + np.r_[d * 4.0, 0]
    lib.tube(M, [top, arm], [0.07, 0.06], sides=4)
    lib.box(M, (arm[0], arm[1], arm[2] - 0.45), (1.2, 0.35, 0.4), facing + math.pi / 2, 0.5)
    col.box((x, y, z), (0.6, 0.6, 2.5))


def sign_board(sc, p, facing, w, h, cell, z_up):
    """flat sign facing direction `facing` (math angle).  cell = index in signs atlas (2 cols x 8 rows)"""
    S = sc['signs']
    d = np.array([math.cos(facing), math.sin(facing), 0]); t = np.array([-d[1], d[0], 0])
    c = np.array(p, float)
    u0 = (cell % 2) * 0.5 + 0.005; u1 = u0 + 0.49
    v1 = 1 - (cell // 2) * 0.125 - 0.004; v0 = v1 - 0.117
    q = [c - t * w / 2, c + t * w / 2, c + t * w / 2 + np.array([0, 0, h]), c - t * w / 2 + np.array([0, 0, h])]
    S.poly(q, [(u1, v0), (u0, v0), (u0, v1), (u1, v1)])


def guardrail(sc, pts, z_of, rr):
    M = sc['metal']
    for i in range(len(pts) - 1):
        a = np.array(pts[i]); b = np.array(pts[i + 1])
        L = float(np.linalg.norm(b - a)); n = max(1, int(L / 2.0))
        for k in range(n + 1):
            p = a + (b - a) * k / n
            z = z_of(p)
            lib.tube(M, [(p[0], p[1], z - 0.1), (p[0], p[1], z + 0.75)], [0.05, 0.05], sides=4)
        za, zb = z_of(a), z_of(b)
        if rr.random() < 0.85:
            sag = 0.0 if rr.random() < 0.8 else -0.4
            mid = (a + b) / 2
            lib.tube(M, [(a[0], a[1], za + 0.68), (mid[0], mid[1], (za + zb) / 2 + 0.68 + sag), (b[0], b[1], zb + 0.68)], [0.06] * 3, sides=4)


def vending(sc, col, p, facing, rr):
    x, y, z = p
    lib.box(sc['metal'], (x, y, z), (1.0, 0.8, 1.85), facing, 0.5)
    d = np.array([math.cos(facing), math.sin(facing)])
    sign_board(sc, (x + d[0] * 0.41, y + d[1] * 0.41, z + 1.3), facing, 0.9, 0.25, rr.choice([5, 6, 10]), True)
    col.box((x, y, z), (1.0, 0.8, 1.85), facing)


def bicycle(sc, p, facing, rr):
    M = sc['metal']
    x, y, z = p
    d = np.array([math.cos(facing), math.sin(facing), 0])
    up = np.array([0, 0, 1.0]) if rr.random() < 0.5 else np.array([-d[1], d[0], 0.0])  # lying or standing
    side = np.cross(d, up)
    for wx in (-0.55, 0.55):
        c = np.array([x, y, z + 0.05]) + d * wx + up * 0.34
        lib.tube(M, [c + (math.cos(a) * d + math.sin(a) * up) * 0.33 for a in np.linspace(0, 2 * math.pi, 9)], [0.02] * 9, sides=3)
    o = np.array([x, y, z + 0.05])
    lib.tube(M, [o - d * 0.55 + up * 0.34, o + up * 0.75, o + d * 0.55 + up * 0.34], [0.025] * 3, sides=3)


def rubble(sc, col, c, R, H, rr, G=None, base=None, chunks=True):
    """noisy mound of debris (mossy top), chunks, rebar; collision = mound"""
    x, y = c
    nr, ns = 5, 12
    verts = []; faces = []; uvs = []
    def gz(px, py):
        if base is not None:
            return base
        return G(px, py) if G is not None else 0.0
    for i in range(nr + 1):
        f = i / nr
        for j in range(ns):
            a = 2 * math.pi * j / ns
            r = R * f * (1 + 0.25 * (vnoise(math.cos(a) * 2 + x, math.sin(a) * 2 + y, 3) - 0.5))
            px, py = x + math.cos(a) * r, y + math.sin(a) * r
            hgt = H * (1 - f ** 1.6) * (0.75 + 0.5 * vnoise(px * 0.5, py * 0.5, 9))
            verts.append((px, py, gz(px, py) + hgt - (0.15 if i == nr else 0)))
            uvs.append((px / 4, py / 4))
    for i in range(nr):
        for j in range(ns):
            a = i * ns + j; b = i * ns + (j + 1) % ns
            faces.append([a, a + ns, b + ns, b] if i > 0 else [a, a + ns, b + ns, b])
    T = sc['top']
    T.mesh(verts, faces, uvs)
    for f in faces:
        col.poly([verts[k] for k in f])
    if chunks and not lib.mid():
        Cc = sc['conc']
        for k in range(int(4 + R * 1.5)):
            a = rr.uniform(0, 2 * math.pi); r = rr.uniform(0.1, 0.95) * R
            if base is not None and k % 2:
                continue
            px, py = x + math.cos(a) * r, y + math.sin(a) * r
            hgt = gz(px, py) + H * (1 - (r / R) ** 1.6) * 0.8
            s = rr.uniform(0.6, 2.2) * (0.55 if base is not None else 1.0)
            ang = rr.uniform(0.2, 0.9)
            tilt = np.array([[1, 0, 0], [0, math.cos(ang), -math.sin(ang)], [0, math.sin(ang), math.cos(ang)]])
            lib.box(Cc, (px, py, hgt - s * 0.3), (s * rr.uniform(1, 2.5), s, s * 0.35), rr.uniform(0, 3.14), 0.25, tilt=tilt)
        M = sc['metal']
        for k in range(int(R)):
            a = rr.uniform(0, 2 * math.pi); r = rr.uniform(0.1, 0.8) * R
            px, py = x + math.cos(a) * r, y + math.sin(a) * r
            hgt = gz(px, py) + H * (1 - (r / R) ** 1.6) * 0.8
            d = norm(np.array([rr.uniform(-1, 1), rr.uniform(-1, 1), rr.uniform(0.2, 1)]))
            lib.tube(M, [np.array([px, py, hgt - 0.2]), np.array([px, py, hgt]) + d * rr.uniform(1, 2.5)], [0.03, 0.025], sides=3)


def build(sc, col, ctx):
    G = ctx['ground']; occ = ctx['occ']
    rr = lib.rng(2030)
    O = lib.osm()
    # cars along other roads (stopped in the lanes as on the day), avoid keyakizaka (keyaki.py)
    n = 0
    for r in O['roads']:
        if r['tunnel'] or r['bridge'] or r['hw'] not in ('primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'primary_link'):
            continue
        if r['name'] == 'けやき坂':
            continue
        line = r['line']
        w = r['width'] or 6.0
        for i in range(len(line) - 1):
            a = np.array(line[i]); b = np.array(line[i + 1]); L = float(np.linalg.norm(b - a))
            if L < 4:
                continue
            u = (b - a) / L; nrm = np.array([-u[1], u[0]])
            k = rr.uniform(2, 20)
            while k < L - 2:
                q = a + u * k + nrm * (rr.choice([-1, 1]) * w * 0.22 + rr.uniform(-0.3, 0.3))
                if lib.BOX[0] + 3 < q[0] < lib.BOX[2] - 3 and lib.BOX[1] + 3 < q[1] < lib.BOX[3] - 3 and occ.free(q[0], q[1], 2.0) \
                        and rr.random() < 0.55:
                    hd = math.atan2(u[1], u[0]) + (math.pi if rr.random() < 0.5 else 0) + rr.uniform(-0.2, 0.2)
                    kind = rr.choice(['sedan', 'sedan', 'van', 'kei', 'taxi'])
                    car(sc, col, (q[0], q[1], G(q[0], q[1])), hd, rr, kind)
                    occ.fill_circle(q[0], q[1], 2.5, 6)
                    n += 1
                k += rr.uniform(8, 30)
    ctx['n_cars_other'] = n
    # rubble at the remains and at the feet of sheared buildings
    for (x, y, R, H, base) in ctx.get('rubble', []):
        rubble(sc, col, (x, y), R, H, rr, G, base=base)
    for (x, y, R, H, base) in ctx.get('falls', []):
        if occ.get(x, y) in (1, 2, 3, 4) or not (lib.BOX[0] < x < lib.BOX[2] and lib.BOX[1] < y < lib.BOX[3]):
            continue
        rubble(sc, col, (x, y), R, H, rr, G, base=base)
        occ.fill_circle(x, y, R * 0.7, 5)
