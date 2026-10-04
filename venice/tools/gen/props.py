"""Props: instanced templates (mooring poles, bricole, wall lanterns, chimneys, wellheads, moored boats and
covered gondolas) and their placement from facades, roofs, rive and OSM points.

Template geometry is built here once (local frame: x forward, y left, z up, origin at the base / hinge).
Instances: (template, x, y, z, yaw, sx, sy, sz, tint rgb, probe normal)."""
import math
import numpy as np
import shapely
from shapely.geometry import Point, LineString
from .world import GROUND_Z, WATER_BOTTOM, h32
from .mesh import MeshBuilder
from .materials import MAT

# ------------------------------------------------------------------ primitives
def lathe(mb, prof, seg, mat, c0=(255, 255, 255, 0), c1=(0, 0, 0, 0), x=0.0, y=0.0, z=0.0, cap_top=False, uvh=1.0):
    """profile [(r, z)] bottom->top revolved around the local z axis."""
    P = []; UV = []; N = []
    for i, (r, zz) in enumerate(prof):
        for k in range(seg + 1):
            a = k / seg * 2 * math.pi
            P.append((x + r * math.cos(a), y + r * math.sin(a), z + zz))
            UV.append((k / seg * 2 * math.pi * max(r, 0.05), zz * uvh))
    nk = seg + 1
    I = []
    for i in range(len(prof) - 1):
        for k in range(seg):
            a = i * nk + k; b = a + 1; c = a + nk + 1; d = a + nk
            I += [[a, b, c], [a, c, d]]
    P = np.array(P); I = np.array(I)
    # smooth normals from the profile slope
    Nn = []
    for i, (r, zz) in enumerate(prof):
        i0 = max(0, i - 1); i1 = min(len(prof) - 1, i + 1)
        dr = prof[i1][0] - prof[i0][0]; dz = prof[i1][1] - prof[i0][1]
        nr, nz = dz, -dr; l = math.hypot(nr, nz) or 1; nr /= l; nz /= l
        for k in range(seg + 1):
            a = k / seg * 2 * math.pi
            Nn.append((nr * math.cos(a), nr * math.sin(a), nz))
    mb.add(P, I, N=np.array(Nn), UV=np.array(UV), mat=mat, c0=c0, c1=c1)
    if cap_top:
        r, zz = prof[-1]
        Pc = [(x, y, z + zz)] + [(x + r * math.cos(k / seg * 2 * math.pi), y + r * math.sin(k / seg * 2 * math.pi), z + zz) for k in range(seg)]
        Ic = [[0, 1 + k, 1 + (k + 1) % seg] for k in range(seg)]
        mb.add(np.array(Pc), np.array(Ic), N=np.tile([0, 0, 1.0], (len(Pc), 1)), UV=np.array([(p[0], p[1]) for p in Pc]), mat=mat, c0=c0, c1=c1)

def box(mb, x0, y0, z0, x1, y1, z1, mat, c0=(255, 255, 255, 0), c1=(0, 0, 0, 0), skip=''):
    F = {'-z': ((x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (0, 0, -1)), '+z': ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (0, 0, 1)),
         '-y': ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (0, -1, 0)), '+y': ((x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (0, 1, 0)),
         '-x': ((x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (-1, 0, 0)), '+x': ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (1, 0, 0))}
    for k, (a, b, c, d, n) in F.items():
        if k in skip: continue
        P = np.array([a, b, c, d], float)
        if n[2] != 0: uv = P[:, :2]
        elif n[1] != 0: uv = P[:, [0, 2]]
        else: uv = P[:, [1, 2]]
        mb.add_planar(P, [[0, 1, 2], [0, 2, 3]], n, uv, mat=mat, c0=c0, c1=c1)

def loft(mb, sections, mat, c0=(255, 255, 255, 0), c1=(0, 0, 0, 0), closed=False, uvs=1.0):
    """sections: list of (x, [(y,z) ...]) rings with equal point counts; quads between consecutive sections."""
    n = len(sections[0][1]); P = []; UV = []
    for (x, pts) in sections:
        acc = 0
        for j, (y, z) in enumerate(pts):
            if j: acc += math.dist(pts[j - 1], pts[j])
            P.append((x, y, z)); UV.append((x * uvs, acc * uvs))
    I = []
    m = n if closed else n - 1
    for i in range(len(sections) - 1):
        for j in range(m):
            a = i * n + j; b = i * n + (j + 1) % n; c = a + n; d = b + n
            I += [[a, c, d], [a, d, b]]
    mb.add(np.array(P), np.array(I), UV=np.array(UV), mat=mat, c0=c0, c1=c1, smooth=True)


# ------------------------------------------------------------------ templates
T_NAMES = ['palina', 'palo', 'bricola', 'lantern', 'chimney_funnel', 'chimney_box', 'wellhead', 'sandolo', 'motorboat', 'gondola_cov']
T = {n: i for i, n in enumerate(T_NAMES)}

def tpl_palina():
    mb = MeshBuilder()
    # striped pole: shader draws spiral stripes (flag 6) in the instance tint over white
    lathe(mb, [(0.12, -1.8), (0.115, 0.0), (0.105, 3.6), (0.10, 4.1)], 10, MAT['wood_paint'], c1=(0, 0, 0, 6))
    lathe(mb, [(0.12, 4.1), (0.13, 4.16), (0.06, 4.2), (0.11, 4.28), (0.13, 4.38), (0.11, 4.48), (0.06, 4.55), (0.0, 4.6)], 10, MAT['metal'], c1=(0, 0, 0, 7))
    return mb

def tpl_palo():
    mb = MeshBuilder()
    lathe(mb, [(0.14, -1.8), (0.135, 0.0), (0.125, 2.6), (0.10, 2.75)], 9, MAT['wood_raw'])
    return mb

def tpl_bricola():
    mb = MeshBuilder()
    for (dx, dy, h) in ((0.0, 0.17, 3.9), (-0.15, -0.09, 3.6), (0.15, -0.09, 3.4)):
        lathe(mb, [(0.16, -2.0), (0.15, 0.0), (0.13, h), (0.08, h + 0.12)], 9, MAT['wood_raw'], x=dx, y=dy)
    lathe(mb, [(0.33, 2.2), (0.34, 2.32), (0.33, 2.45)], 12, MAT['metal'])
    return mb

def tpl_lantern():
    """wall lantern: origin on the wall face, +x out of the wall."""
    mb = MeshBuilder()
    box(mb, 0.0, -0.05, -0.15, 0.03, 0.05, 0.15, MAT['metal'])                     # wall plate
    for i in range(8):                                                             # curved bracket
        a0 = i / 8 * math.pi / 2; a1 = (i + 1) / 8 * math.pi / 2
        x0, z0 = 0.03 + 0.55 * (1 - math.cos(a0)), 0.0 + 0.35 * math.sin(a0)
        x1, z1 = 0.03 + 0.55 * (1 - math.cos(a1)), 0.0 + 0.35 * math.sin(a1)
        box(mb, min(x0, x1), -0.012, min(z0, z1) - 0.012, max(x0, x1) + 0.01, 0.012, max(z0, z1) + 0.012, MAT['metal'])
    lathe(mb, [(0.0, -0.62), (0.05, -0.62), (0.16, -0.30), (0.17, -0.27)], 6, MAT['glass'], x=0.55, c1=(0, 0, 0, 9))   # glass body (lit at night)
    lathe(mb, [(0.17, -0.27), (0.19, -0.25), (0.10, -0.12), (0.03, -0.05), (0.02, 0.0)], 6, MAT['metal'], x=0.55)
    lathe(mb, [(0.012, 0.0), (0.012, 0.35)], 4, MAT['metal'], x=0.55)
    return mb

def tpl_chimney(kind):
    mb = MeshBuilder()
    box(mb, -0.25, -0.25, -0.6, 0.25, 0.25, 1.5, MAT['wall_brick'], skip='-z')
    if kind == 'funnel':
        lathe(mb, [(0.22, 1.5), (0.28, 1.62), (0.48, 2.05), (0.5, 2.12), (0.46, 2.14)], 12, MAT['wall_plaster'], c0=(214, 170, 130, 0))
        lathe(mb, [(0.44, 2.13), (0.40, 2.10), (0.0, 1.95)], 12, MAT['dark'])
    else:
        box(mb, -0.33, -0.33, 1.5, 0.33, 0.33, 1.58, MAT['trim'])
        for (x, y) in ((-0.22, -0.22), (0.22, -0.22), (-0.22, 0.22), (0.22, 0.22)):
            box(mb, x - 0.08, y - 0.08, 1.58, x + 0.08, y + 0.08, 1.88, MAT['wall_brick'])
        box(mb, -0.36, -0.36, 1.88, 0.36, 0.36, 1.98, MAT['trim'])
    return mb

def tpl_wellhead():
    mb = MeshBuilder()
    lathe(mb, [(1.25, 0.0), (1.25, 0.14), (0.95, 0.14), (0.95, 0.28)], 16, MAT['trim'], cap_top=False)
    box(mb, -0.96, -0.96, 0.27, 0.96, 0.96, 0.28, MAT['trim'], skip='-z-x+x-y+y')
    # octagonal drum with a moulded rim
    lathe(mb, [(0.62, 0.28), (0.66, 0.32), (0.60, 0.40), (0.60, 0.98), (0.68, 1.04), (0.70, 1.12), (0.62, 1.14)], 8, MAT['trim'])
    lathe(mb, [(0.60, 1.14), (0.0, 1.12)], 8, MAT['metal'])
    return mb

def hull_sections(L, B, D, rocker, sheer, n=24, asym=0.0, bow_up=0.0, stern_up=0.0):
    secs = []
    for i in range(n + 1):
        t = i / n; x = (t - 0.5) * L
        w = B / 2 * (1 - abs(2 * t - 1) ** 2.2) ** 0.75 + 0.02
        keel = rocker * (2 * t - 1) ** 2 + (bow_up * max(0, (t - 0.85) / 0.15) ** 2) + (stern_up * max(0, (0.15 - t) / 0.15) ** 2)
        top = D + sheer * (2 * t - 1) ** 2 + keel * 0.6
        yoff = asym * math.sin(t * math.pi) * B
        pts = []
        for k in range(9):
            a = k / 8 * math.pi                              # from port gunwale around the bottom to starboard
            y = -math.cos(a) * w; z = keel + (1 - math.sin(a) ** 0.6) * (top - keel)
            pts.append((y + yoff, z))
        secs.append((x, pts))
    return secs

def tpl_boat(kind):
    mb = MeshBuilder()
    if kind == 'sandolo':
        secs = hull_sections(7.0, 1.35, 0.55, 0.18, 0.12)
        loft(mb, secs, MAT['wood_paint'], c0=(60, 70, 64, 0), c1=(0, 0, 0, 8))
        # tarp over the hull (blue canvas)
        tarp = [(x, [(y * 0.98, z + 0.03) for (y, z) in pts][::-1]) for (x, pts) in secs[2:-2]]
        tarp = [(x, [pts[0]] + [(0.0, max(p[1] for p in pts) + 0.18)] + [pts[-1]]) for (x, pts) in tarp]
        loft(mb, tarp, MAT['wood_paint'], c0=(40, 70, 120, 0), c1=(0, 0, 0, 10))
    elif kind == 'motor':
        secs = hull_sections(7.6, 2.0, 0.85, 0.22, 0.1, bow_up=0.25)
        loft(mb, secs, MAT['wood_paint'], c0=(236, 232, 222, 0), c1=(0, 0, 0, 8))
        box(mb, -3.2, -0.9, 0.8, 2.6, 0.9, 0.86, MAT['wood_raw'])
        box(mb, 0.2, -0.85, 0.86, 0.5, 0.85, 1.25, MAT['glass'])
    else:   # covered gondola: black lacquer hull, blue cover, ferro
        secs = hull_sections(10.8, 1.38, 0.5, 0.42, 0.25, asym=0.06, bow_up=0.55, stern_up=0.45)
        loft(mb, secs, MAT['wood_paint'], c0=(14, 14, 16, 0), c1=(0, 0, 0, 11))
        cov = [(x, [(y * 0.97, z + 0.04) for (y, z) in pts]) for (x, pts) in secs[5:-5]]
        cov = [(x, [pts[0], (pts[0][0] * 0.5, max(p[1] for p in pts) + 0.12), (0.0, max(p[1] for p in pts) + 0.16), (pts[-1][0] * 0.5, max(p[1] for p in pts) + 0.12), pts[-1]]) for (x, pts) in cov]
        loft(mb, cov, MAT['wood_paint'], c0=(30, 60, 105, 0), c1=(0, 0, 0, 10))
        # ferro (bow iron): flat comb blade
        fx = 10.8 / 2 - 0.1
        box(mb, fx, -0.015, 0.95, fx + 0.12, 0.015, 1.75, MAT['metal'], c1=(0, 0, 0, 12))
        for k in range(6):
            box(mb, fx + 0.1, -0.012, 1.0 + k * 0.08, fx + 0.32, 0.012, 1.04 + k * 0.08, MAT['metal'], c1=(0, 0, 0, 12))
        box(mb, fx - 0.05, -0.02, 1.75, fx + 0.3, 0.02, 1.95, MAT['metal'], c1=(0, 0, 0, 12))
    return mb

def templates():
    out = {}
    out['palina'] = tpl_palina(); out['palo'] = tpl_palo(); out['bricola'] = tpl_bricola(); out['lantern'] = tpl_lantern()
    out['chimney_funnel'] = tpl_chimney('funnel'); out['chimney_box'] = tpl_chimney('box'); out['wellhead'] = tpl_wellhead()
    out['sandolo'] = tpl_boat('sandolo'); out['motorboat'] = tpl_boat('motor'); out['gondola_cov'] = tpl_boat('gondola')
    return out


# ------------------------------------------------------------------ placement
POLE_COLS = [(28, 64, 140), (170, 30, 32), (24, 110, 70), (210, 160, 40), (20, 20, 22), (120, 30, 90)]

def place_facade_props(fac, rnd, inst):
    """poles and boats in front of water gates; lanterns on street facades."""
    p0 = np.array(fac['p0']); p1 = np.array(fac['p1']); L = fac['L']; d = (p1 - p0) / max(L, 1e-6); n = np.array(fac['n'])
    yaw_out = math.atan2(n[1], n[0])
    for o in fac['open']:
        t, u, z, w, h, fl = o
        if t == 7 and fac['cls'] == 'W':                       # water gate
            striped = fac['st'] in ('gothic', 'renaiss') or rnd(('pc', u)) < 0.35
            col = POLE_COLS[int(rnd(('col', 0)) * len(POLE_COLS))]
            npl = 2 if not striped else (2 + int(rnd(('np', u)) * 2.5))
            dist = 1.8 + rnd(('dp', u)) * 0.8
            for k in range(npl):
                uu = u + (k - (npl - 1) / 2) * (1.0 + w / max(npl - 1, 1) * 0.6)
                q = p0 + d * uu + n * dist
                inst.append(dict(t=T['palina'] if striped else T['palo'], p=(q[0], q[1], 0.0), yaw=rnd(('py', k)) * 6.28, s=(1, 1, 0.92 + 0.16 * rnd(('ps', k))), c=col if striped else (255, 255, 255), n=(0, 0, 1)))
            if rnd(('boat', u)) < 0.55:
                kind = 'gondola_cov' if (striped and rnd(('bk', u)) < 0.45) else 'motorboat' if rnd(('bk2', u)) < 0.55 else 'sandolo'
                q = p0 + d * (u + (rnd(('bo', u)) - 0.5) * 2) + n * (dist - 0.95)
                inst.append(dict(t=T[kind], p=(q[0], q[1], 0.0), yaw=math.atan2(d[1], d[0]) + (math.pi if rnd(('bf', u)) < 0.5 else 0), s=(1, 1, 1), c=(255, 255, 255), n=(0, 0, 1)))
    if fac['cls'] == 'G' and L > 4 and rnd('lamp') < 0.22:
        u = 0.6 if rnd('lu') < 0.5 else L - 0.6
        q = p0 + d * u
        inst.append(dict(t=T['lantern'], p=(q[0], q[1], fac['zg'] + 3.7), yaw=yaw_out, s=(1, 1, 1), c=(255, 255, 255), n=(n[0], n[1], 0.3)))

def place_chimneys(b, poly, ze, eave_edges, rnd, inst):
    if b.kind in ('tower', 'church', 'roof', 'shed') or not eave_edges: return
    area = poly.area
    nch = max(1, int(area / 70 + rnd('nch')))
    for k in range(nch):
        e = eave_edges[int(rnd(('ce', k)) * len(eave_edges)) % len(eave_edges)]
        a = np.array(e[0]); c = np.array(e[1]); L = np.linalg.norm(c - a)
        if L < 1.5: continue
        dr = (c - a) / L; nin = np.array([-dr[1], dr[0]])
        q = a + dr * (0.6 + rnd(('cu', k)) * (L - 1.2)) + nin * (0.55 + rnd(('cd', k)) * 0.8)
        if not poly.contains(Point(*q)): continue
        dist = poly.boundary.distance(Point(*q))
        zr = ze + min(dist, 3.6 / 0.3839) * 0.3839
        kind = 'chimney_funnel' if rnd(('ck', k)) < 0.7 else 'chimney_box'
        inst.append(dict(t=T[kind], p=(q[0], q[1], zr), yaw=math.atan2(dr[1], dr[0]), s=(1, 1, 0.9 + 0.4 * rnd(('cs', k))), c=(255, 255, 255), n=(0, 0, 1)))

def place_osm_points(world, region, inst):
    o = world.o
    x0, y0, x1, y1 = region.bounds
    for nid, nd in o.nodes.items():
        t = nd.get('tags')
        if not t: continue
        mm = t.get('man_made'); sm = t.get('seamark:type')
        if mm not in ('water_well', 'dolphin') and sm != 'pile': continue
        x, y = o.xy(nid)
        if not (x0 <= x < x1 and y0 <= y < y1): continue
        r = h32('osm', nid)
        if mm == 'water_well':
            if world.is_land(x, y) and world.building_at(x, y) is None:
                inst.append(dict(t=T['wellhead'], p=(x, y, GROUND_Z), yaw=r * 6.28, s=(1, 1, 1), c=(255, 255, 255), n=(0, 0, 1)))
        elif not world.is_land(x, y):
            inst.append(dict(t=T['bricola'] if mm == 'dolphin' else T['palo'], p=(x, y, 0.0), yaw=r * 6.28, s=(1, 1, 1), c=(255, 255, 255), n=(0, 0, 1)))
