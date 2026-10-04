"""Basilica di San Marco, interior: a Greek cross of five domed bays (west = Pentecost, centre = Ascension,
east = Emmanuel, north = St John, south = St Leonard) on pendentives, joined by barrel vaults, with lower aisles
behind colonnades and galleries, gold mosaics above, marble revetment below, the opus sectile floor, the
iconostasis, the raised presbytery and hanging lamps.

The three domes photographed from the floor (Commons, see credits) are mapped back onto the hemispheres with the
camera's projection (crown medallion and window ring read off each photo); the other vault surfaces are
procedural gold mosaic.  Daylight enters through the ring of windows at the base of each dome (emissive panes in
the bake) and the great west window.

Piazza frame (u east along the nave, v north); floor 0.35 m above the piazza."""
import json, math, os
import numpy as np
from shapely.geometry import Polygon, Point
from vk import geom as G, arch as A
from ..world import GROUND_Z
from .common import place, pf as pf_piazza, wf as wf_piazza
from .basilica import statue, wf, pf, PU, PV      # the church's own (turned) frame

ART = json.load(open('/home/kazu/work/demos/venice/public/tex/art.json'))['items'] if os.path.exists('/home/kazu/work/demos/venice/public/tex/art.json') else {}
ZF = GROUND_Z + 0.35            # basilica floor
ZS = 15.0                       # springing of the great arches (above the floor)
AX = 29.7                       # nave axis (v)
HB = 6.2                        # half side of every domed bay (= inner dome radius); one size keeps arches and vaults flush
BAYS = {  # name: (u, v, half side h)
    'W': (65.0, AX, HB), 'C': (83.7, AX, HB), 'E': (101.5, AX, HB), 'N': (83.7, 49.2, HB), 'S': (83.7, 10.2, HB),
}
# photos: (art key, crown (x,y) and window-ring ellipse (cx, cy, rx, ry) in image width units, image aspect h/w)
DOME_PHOTO = {
    'W': ('dome_pentecost', (0.404, 0.51), (0.446, 0.494, 0.2875, 0.2875)),
    'E': ('dome_emmanuel', (0.505, 0.37), (0.503, 0.375, 0.346, 0.325)),
    'C': ('dome_ascension', (0.494, 0.244), (0.497, 0.415, 0.447, 0.303)),
}
U_WEST, U_EAST, V_SOUTH, V_NORTH = 45.0, 112.0, 1.0, 58.0
# the OSM outline of the church (piazza u, v; simplified 0.5 m, as the exterior massing): the interior is the box
# above clipped to it, 0.8 m inside, so no vault or wall pokes out at the stepped corners (Zen chapel, treasury, apse)
FOOT_UV = [(100.4, 54.1), (97.6, 54.3), (97.1, 44.3), (119.1, 43.2), (119.6, 41.0), (124.1, 40.6), (123.9, 38.7), (127.4, 38.6),
           (126.7, 29.4), (115.4, 29.5), (115.3, 26.2), (112.7, 21.8), (112.0, 12.7), (95.9, 13.7), (95.6, 8.2), (96.5, 8.2),
           (95.4, 5.3), (96.5, 4.6), (96.3, 2.9), (95.4, 2.8), (95.1, 1.5), (96.2, 0.3), (96.1, -2.7), (63.4, -0.4), (63.4, -1.1),
           (57.4, -0.7), (58.0, 7.4), (36.5, 9.0), (36.7, 10.9), (38.9, 11.1), (39.8, 12.4), (39.8, 16.0), (38.9, 17.0), (37.1, 17.4),
           (37.2, 18.6), (40.2, 18.4), (40.5, 25.0), (37.4, 25.2), (37.6, 27.5), (40.2, 28.1), (40.8, 30.0), (40.9, 35.8), (39.7, 37.2),
           (37.9, 37.6), (37.9, 40.1), (41.1, 40.0), (41.3, 46.3), (38.2, 46.5), (38.2, 47.6), (39.8, 47.7), (41.3, 48.9), (41.5, 52.9),
           (40.4, 54.4), (38.5, 54.7), (38.5, 56.8), (41.0, 56.7), (41.1, 58.6), (42.6, 58.5), (42.6, 57.3), (48.7, 57.0), (48.8, 58.3),
           (50.4, 58.3), (50.3, 56.9), (55.3, 56.7), (55.4, 58.1), (56.9, 58.1), (56.8, 56.6), (61.5, 56.3), (61.6, 57.9), (63.2, 57.9),
           (63.1, 56.2), (69.9, 55.9), (70.0, 57.7), (72.1, 57.6), (72.3, 62.5), (77.8, 62.2), (77.9, 64.6), (80.1, 64.5), (80.0, 62.8),
           (80.7, 62.1), (89.0, 61.6), (89.8, 63.9), (92.6, 63.8), (92.5, 61.4), (100.6, 60.7)]

FOOT_UV = [pf(wf_piazza(u, v)) for (u, v) in FOOT_UV]      # listed in the piazza frame -> church frame

def _interior():
    from shapely.geometry import box
    g = Polygon(FOOT_UV).buffer(0).buffer(-0.8, join_style=2).intersection(box(U_WEST, V_SOUTH, U_EAST, V_NORTH))
    if g.geom_type != 'Polygon': g = max(g.geoms, key=lambda q: q.area)
    return g.simplify(0.2, preserve_topology=True)
IN = _interior()                                  # interior outline (u, v)

def fill_geom(m, g, z, want, mat):
    """horizontal surface over a shapely (multi)polygon in (u, v), holes allowed."""
    for p in (g.geoms if hasattr(g, 'geoms') else [g]):
        if p.geom_type != 'Polygon' or p.area < 1e-4: continue
        L = [G.ccw(list(p.exterior.coords))] + [G.ccw(list(r.coords))[::-1] for r in p.interiors]
        flat = [q for l in L for q in l]
        for (a, b, c) in G.tess(L):
            quad(m, [W(flat[i][0], flat[i][1], z) for i in (a, b, c)], want, mat)

def fill(m, rect, z, want, mat):
    """horizontal surface over the box (ua, ua, va, vb) clipped to the interior outline; z a number or z(u, v)."""
    from shapely.geometry import box
    ua, ub, va, vb = rect
    g = box(min(ua, ub), min(va, vb), max(ua, ub), max(va, vb)).intersection(IN)
    for p in (g.geoms if hasattr(g, 'geoms') else [g]):
        if p.geom_type != 'Polygon' or p.area < 1e-4: continue
        L = [G.ccw(list(p.exterior.coords))] + [G.ccw(list(r.coords))[::-1] for r in p.interiors]
        flat = [q for l in L for q in l]
        for (a, b, c) in G.tess(L):
            quad(m, [W(flat[i][0], flat[i][1], z(*flat[i]) if callable(z) else z) for i in (a, b, c)], want, mat)

def W(u, v, z): p = wf(u, v); return (p[0], p[1], z)

def quad(m, pts, want, mat, uv=None):
    P = np.array(pts, float); n = np.cross(P[1] - P[0], P[2] - P[0])
    if np.dot(n, want) >= 0: m.poly(pts, mat, uv=uv)
    else: m.poly(pts[::-1], mat, uv=uv[::-1] if uv else None)

# ------------------------------------------------------------------ domes on pendentives
def dome_photo_uv(key, crown, ring, theta, phi):
    """uv in the art layer for dome angle theta (0 crown .. pi/2 base) and azimuth phi (0 = +u, ccw)."""
    D_R = 3.0                                  # camera ~3 dome radii below the base
    f = math.sin(theta) * D_R / (D_R + math.cos(theta))
    cx, cy, rx, ry = ring
    # the photographs look up with image-right ~ +u and image-up ~ +v (east domes) — azimuth sign fixed per photo
    # photographers stood west of the dome looking east and up: east -> image top, north -> image left
    bx, by = cx - rx * math.sin(phi), cy - ry * math.cos(phi)
    x = crown[0] + (bx - crown[0]) * f; y = crown[1] + (by - crown[1]) * f
    # art layers are square: x in width units, y in width units -> divide by the aspect (h/w) for v
    asp = ART[key]['aspect']                   # w/h
    return (x, 1.0 - y * asp)

def dome(name, m_list):
    u0, v0, h = BAYS[name]
    zb = ZF + ZS + h                            # dome base (top of the pendentives)
    m = G.Mesh()
    NT, NP = 14, 48
    ph = DOME_PHOTO.get(name)
    for i in range(NT):
        t0, t1 = (math.pi / 2) * i / NT, (math.pi / 2) * (i + 1) / NT
        for j in range(NP):
            p0, p1 = 2 * math.pi * j / NP, 2 * math.pi * (j + 1) / NP
            def P(t, p): return W(u0 + h * math.sin(t) * math.cos(p), v0 + h * math.sin(t) * math.sin(p), zb + h * math.cos(t))
            pts = [P(t0, p0), P(t0, p1), P(t1, p1), P(t1, p0)]
            c = np.mean(np.array(pts), axis=0); centre = np.array(W(u0, v0, zb))
            want = centre - c                    # inner surface faces the dome centre
            if ph:
                key = ph[0]
                uv = [dome_photo_uv(key, ph[1], ph[2], t, p) for (t, p) in ((t0, p0), (t0, p1), (t1, p1), (t1, p0))]
                quad(m, pts, want, 'painting', uv)
            else:
                quad(m, pts, want, 'mosaic_gold')
    if ph: m_list.append((m, ART[ph[0]]['layer']))
    else: m_list.append((m, 0))
    # ring of windows at the base: emissive daylight panes (light the interior in the bake)
    wm = G.Mesh()
    nw = 16 if name in ('W', 'C', 'E') else 12
    for k in range(nw):
        p = 2 * math.pi * (k + 0.5) / nw
        r = h * 0.985; ww = 0.55; hh = 1.35; z0 = zb + 0.15
        cx, cy = u0 + r * math.cos(p), v0 + r * math.sin(p)
        tx, ty = -math.sin(p), math.cos(p)
        pts = [W(cx - tx * ww / 2, cy - ty * ww / 2, z0), W(cx + tx * ww / 2, cy + ty * ww / 2, z0), W(cx + tx * ww / 2, cy + ty * ww / 2, z0 + hh), W(cx - tx * ww / 2, cy - ty * ww / 2, z0 + hh)]
        quad(wm, pts, (-math.cos(p) * PU[0] - math.sin(p) * PV[0], -math.cos(p) * PU[1] - math.sin(p) * PV[1], 0), 'daylight')
    m_list.append((wm, 0))
    # pendentives: sail vault (sphere radius h*sqrt2) between the dome circle (r = h) and the square, in polar
    # coordinates so the inner edge meets the dome base exactly and the outer edge follows the arches
    pm = G.Mesh(); rho = h * math.sqrt(2.0); NA, NR = 96, 8
    zc = ZF + ZS
    for j in range(NA):
        p0, p1 = 2 * math.pi * j / NA, 2 * math.pi * (j + 1) / NA
        def rsq(p): return h / max(abs(math.cos(p)), abs(math.sin(p)))
        for i in range(NR):
            def P(p, t):
                r = h + (rsq(p) - h) * t
                x, y = r * math.cos(p), r * math.sin(p)
                return W(u0 + x, v0 + y, zc + math.sqrt(max(0.0, rho * rho - x * x - y * y)))
            t0, t1 = i / NR, (i + 1) / NR
            pts = [P(p0, t0), P(p1, t0), P(p1, t1), P(p0, t1)]
            if np.linalg.norm(np.subtract(pts[0], pts[3])) < 1e-4 and np.linalg.norm(np.subtract(pts[1], pts[2])) < 1e-4: continue
            quad(pm, pts, (0, 0, -1), 'mosaic_gold')
    m_list.append((pm, 0))

def barrel(m, ua, ub, va, vb, axis, zs, mat='mosaic_gold', n=16):
    """semicircular barrel vault; axis 'u' (runs along u, spans v from va to vb) or 'v'."""
    if axis == 'u':
        r = (vb - va) / 2; vc = (va + vb) / 2
        for k in range(n):
            a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
            p = lambda u, a: W(u, vc + r * math.cos(a), zs + r * math.sin(a))
            pts = [p(ua, a0), p(ub, a0), p(ub, a1), p(ua, a1)]
            am = (a0 + a1) / 2
            quad(m, pts, (-(math.cos(am)) * PV[0], -(math.cos(am)) * PV[1], -math.sin(am)), mat)
    else:
        r = (ub - ua) / 2; uc = (ua + ub) / 2
        for k in range(n):
            a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
            p = lambda v, a: W(uc + r * math.cos(a), v, zs + r * math.sin(a))
            pts = [p(va, a0), p(vb, a0), p(vb, a1), p(va, a1)]
            am = (a0 + a1) / 2
            quad(m, pts, (-(math.cos(am)) * PU[0], -(math.cos(am)) * PU[1], -math.sin(am)), mat)

def wall_uv(m, u0, v0, u1, v1, z0, z1, want, mat):
    quad(m, [W(u0, v0, z0), W(u1, v1, z0), W(u1, v1, z1), W(u0, v0, z1)], want, mat)

def nrm(du, dv):
    return (du * PU[0] + dv * PV[0], du * PU[1] + dv * PV[1], 0.0)

def pier(m, u0, v0, u1, v1):
    """square pier: marble revetment to the gallery level, gold above, a cornice between."""
    zg = ZF + 9.6
    for (a, b, nn) in (((u0, v0), (u1, v0), (0, -1)), ((u1, v0), (u1, v1), (1, 0)), ((u1, v1), (u0, v1), (0, 1)), ((u0, v1), (u0, v0), (-1, 0))):
        wall_uv(m, a[0], a[1], b[0], b[1], ZF, zg, nrm(*nn), 'basilica_marble')
        wall_uv(m, a[0], a[1], b[0], b[1], zg + 0.45, ZF + ZS, nrm(*nn), 'mosaic_gold')
    m.merge(_box_uv(u0 - 0.2, v0 - 0.2, zg, u1 + 0.2, v1 + 0.2, zg + 0.45, 'marble_white'))

def _box_uv(u0, v0, z0, u1, v1, z1, mat):
    m = G.Mesh()
    P = [W(u0, v0, z0), W(u1, v0, z0), W(u1, v1, z0), W(u0, v1, z0), W(u0, v0, z1), W(u1, v0, z1), W(u1, v1, z1), W(u0, v1, z1)]
    o = m.add_v(P)
    # orientation follows the piazza frame (right-handed with z up), same as G.box
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        m.face([o + i for i in q], mat)
    return m

def colonnade(m, ua, va, ub, vb, z0, h, n, mats=('marble_verde', 'marble_red', 'marble_pink')):
    """columns with stilted arches between an arm and an aisle, gallery parapet above."""
    for k in range(n + 1):
        t = k / n; u = ua + (ub - ua) * t; v = va + (vb - va) * t
        c = A.column(0.5, h, order='corinthian', mat=mats[k % len(mats)], cap_mat='gilt', seg=10, detail=0.1)
        p = wf(u, v); m.merge(c.transformed(G.mat4((p[0], p[1], z0))))
    # architrave + gallery floor edge + parapet
    m.merge(_seg_box(ua, va, ub, vb, 0.35, z0 + h, z0 + h + 0.6, 'marble_white'))
    m.merge(_seg_box(ua, va, ub, vb, 0.25, z0 + h + 0.6, z0 + h + 1.65, 'basilica_marble'))
    m.merge(_seg_box(ua, va, ub, vb, 0.32, z0 + h + 1.65, z0 + h + 1.8, 'marble_white'))

def _seg_box(ua, va, ub, vb, half_t, z0, z1, mat):
    d = np.array([ub - ua, vb - va]); L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]])
    m = G.Mesh()
    c = [np.array([ua, va]) + n * half_t, np.array([ub, vb]) + n * half_t, np.array([ub, vb]) - n * half_t, np.array([ua, va]) - n * half_t]
    pts_lo = [W(p[0], p[1], z0) for p in c]; pts_hi = [W(p[0], p[1], z1) for p in c]
    o = m.add_v(pts_lo + pts_hi)
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    V = np.array(m.V); ctr = V.mean(0)
    for q in faces:
        f = [o + i for i in q]; P = V[[i - o for i in f]]
        nn = np.cross(P[1] - P[0], P[2] - P[0]); fc = P.mean(0)
        if np.dot(nn, fc - ctr) < 0: f = f[::-1]
        m.face(f, mat)
    return m

def lamp(m, u, v, ztop, zl):
    p = wf(u, v)
    m.merge(G.box(p[0] - 0.015, p[1] - 0.015, zl + 0.6, p[0] + 0.015, p[1] + 0.015, ztop, 'metal'))
    m.merge(G.lathe([(0.0, 0), (0.45, 0.15), (0.55, 0.35), (0.35, 0.55), (0.05, 0.6)], 12, mat='gilt').transformed(G.mat4((p[0], p[1], zl))))
    for k in range(8):
        a = 2 * math.pi * k / 8
        m.merge(G.lathe([(0.0, 0), (0.05, 0.0), (0.07, 0.16), (0.0, 0.18)], 6, mat='lamp_glass').transformed(G.mat4((p[0] + 0.5 * math.cos(a), p[1] + 0.5 * math.sin(a), zl + 0.35))))

def floor(m):
    """the whole interior floor (opus sectile pattern in the shader); presbytery raised 1.5 m."""
    poly = [(U_WEST, V_SOUTH), (U_EAST, V_SOUTH), (U_EAST, V_NORTH), (U_WEST, V_NORTH)]
    n = 40
    for a in range(n):
        for b in range(n):
            u0, u1 = U_WEST + (U_EAST - U_WEST) * a / n, U_WEST + (U_EAST - U_WEST) * (a + 1) / n
            v0, v1 = V_SOUTH + (V_NORTH - V_SOUTH) * b / n, V_SOUTH + (V_NORTH - V_SOUTH) * (b + 1) / n
            um, vm = (u0 + u1) / 2, (v0 + v1) / 2
            z = ZF + (1.5 if (um > 94.6 and abs(vm - AX) < 8.0) else 0.0)
            # gentle undulation of the old floor
            def zz(u, v): return z + 0.06 * math.sin(u * 0.7) * math.sin(v * 0.6)
            fill(m, (u0, u1, v0, v1), zz, (0, 0, 1), 'basilica_floor')
    # presbytery front step faces
    for k in range(5):
        u = 94.6 - k * 0.0; z0 = ZF + 0.3 * k; z1 = ZF + 0.3 * (k + 1)
        wall_uv(m, 94.6 - 0.35 * (4 - k), AX + 8.0, 94.6 - 0.35 * (4 - k), AX - 8.0, z0, z1, nrm(-1, 0), 'marble_white')

def iconostasis(m):
    """marble screen with eight columns, architrave, fourteen statues and the great cross."""
    u = 94.4; va, vb = AX - 7.5, AX + 7.5; z0 = ZF + 1.5
    m.merge(_seg_box(u, va, u, vb, 0.25, z0, z0 + 1.1, 'marble_red'))
    for k in range(8):
        v = va + (vb - va) * k / 7
        p = wf(u, v); m.merge(A.column(0.36, 3.6, order='corinthian', mat='marble_verde', cap_mat='gilt', seg=10, detail=0.1).transformed(G.mat4((p[0], p[1], z0))))
    m.merge(_seg_box(u, va - 0.3, u, vb + 0.3, 0.3, z0 + 3.6, z0 + 4.2, 'marble_white'))
    for k in range(14):
        v = va + (vb - va) * k / 13
        p = wf(u, v); m.merge(statue(1.6, 'marble_white').transformed(G.mat4((p[0], p[1], z0 + 4.2))))
    p = wf(u, AX)
    m.merge(G.box(p[0] - 0.07, p[1] - 0.07, z0 + 4.2, p[0] + 0.07, p[1] + 0.07, z0 + 7.6, 'bronze_gilt'))
    q0, q1 = wf(u, AX - 1.2), wf(u, AX + 1.2)
    m.merge(_seg_box(u, AX - 1.2, u, AX + 1.2, 0.07, z0 + 6.3, z0 + 6.5, 'bronze_gilt'))

def apse(m, m_list):
    """half dome over the apse with gold mosaic (Christ Pantocrator area), high altar and the Pala d'Oro."""
    u0, v0, r = U_EAST - 0.2, AX, HB
    zb = ZF + ZS
    for i in range(10):
        t0, t1 = (math.pi / 2) * i / 10, (math.pi / 2) * (i + 1) / 10
        for j in range(18):
            p0, p1 = math.pi / 2 + math.pi * j / 18, math.pi / 2 + math.pi * (j + 1) / 18
            def P(t, p): return W(u0 + r * math.sin(t) * math.cos(p) * -1 * -1, v0 + r * math.sin(t) * math.sin(p), zb + r * math.cos(t))
            pts = [P(t0, p0), P(t0, p1), P(t1, p1), P(t1, p0)]
            c = np.mean(np.array(pts), axis=0); want = np.array(W(u0, v0, zb)) - c
            quad(m, pts, want, 'mosaic_gold')
    # apse wall (semicircle) below the half dome
    for j in range(18):
        p0, p1 = math.pi / 2 + math.pi * j / 18, math.pi / 2 + math.pi * (j + 1) / 18
        pts = [W(u0 + r * math.cos(p0), v0 + r * math.sin(p0), ZF + 1.5), W(u0 + r * math.cos(p1), v0 + r * math.sin(p1), ZF + 1.5),
               W(u0 + r * math.cos(p1), v0 + r * math.sin(p1), zb), W(u0 + r * math.cos(p0), v0 + r * math.sin(p0), zb)]
        pm = (p0 + p1) / 2
        quad(m, pts, nrm(-math.cos(pm), -math.sin(pm)), 'basilica_marble' if True else 'mosaic_gold')
    # altar + Pala d'Oro
    p = wf(U_EAST - 3.5, AX)
    m.merge(G.box(p[0] - 1.1, p[1] - 1.6, ZF + 1.5, p[0] + 1.1, p[1] + 1.6, ZF + 2.6, 'marble_white'))
    m.merge(_seg_box(U_EAST - 2.9, AX - 1.75, U_EAST - 2.9, AX + 1.75, 0.08, ZF + 2.6, ZF + 4.7, 'bronze_gilt'))
    # ciborium on four columns
    for (du, dv) in ((-1.4, -1.9), (-1.4, 1.9), (1.4, -1.9), (1.4, 1.9)):
        q = wf(U_EAST - 3.5 + du, AX + dv)
        m.merge(A.column(0.36, 4.0, order='corinthian', mat='marble_white', cap_mat='gilt', seg=10, detail=0.1).transformed(G.mat4((q[0], q[1], ZF + 1.5))))
    m.merge(_box_uv(U_EAST - 5.1, AX - 2.2, ZF + 5.5, U_EAST - 1.9, AX + 2.2, ZF + 6.4, 'marble_verde'))

def build_mesh():
    """returns [(mesh, art layer)] — layer only matters for 'painting' faces."""
    out = []
    for name in BAYS: dome(name, out)
    m = G.Mesh()
    z_s = ZF + ZS
    W_, C_, E_, N_, S_ = (BAYS[k] for k in 'WCENS')
    # barrel vaults: between the bays and out to the end walls
    barrel(m, W_[0] + W_[2], C_[0] - C_[2], AX - W_[2], AX + W_[2], 'u', z_s)
    barrel(m, C_[0] + C_[2], E_[0] - E_[2], AX - E_[2], AX + E_[2], 'u', z_s)
    barrel(m, U_WEST, W_[0] - W_[2], AX - W_[2], AX + W_[2], 'u', z_s)
    barrel(m, C_[0] - N_[2], C_[0] + N_[2], C_[1] + C_[2], N_[1] - N_[2], 'v', z_s)
    barrel(m, C_[0] - S_[2], C_[0] + S_[2], S_[1] + S_[2], C_[1] - C_[2], 'v', z_s)
    barrel(m, C_[0] - N_[2], C_[0] + N_[2], N_[1] + N_[2], V_NORTH, 'v', z_s)
    barrel(m, C_[0] - S_[2], C_[0] + S_[2], V_SOUTH, S_[1] - S_[2], 'v', z_s)
    barrel(m, E_[0] + E_[2], U_EAST - 0.2, AX - E_[2], AX + E_[2], 'u', z_s)
    # lunette walls under the arches of the bays that open onto the aisles (above the springing, gold mosaic)
    def lunette_wall(cu, cv, side_axis, sgn, h):
        pts = [(math.cos(a), math.sin(a)) for a in np.linspace(0, math.pi, 17)]
        for k in range(16):
            (c0, s0), (c1, s1) = pts[k], pts[k + 1]
            if side_axis == 'v':        # wall in the plane v = cv + sgn*h, spanning u
                q = [W(cu, cv + sgn * h, z_s), W(cu + h * c0, cv + sgn * h, z_s + h * s0), W(cu + h * c1, cv + sgn * h, z_s + h * s1)]
                quad(m, q, nrm(0, -sgn), 'mosaic_gold')
            else:
                q = [W(cu + sgn * h, cv, z_s), W(cu + sgn * h, cv + h * c0, z_s + h * s0), W(cu + sgn * h, cv + h * c1, z_s + h * s1)]
                quad(m, q, nrm(-sgn, 0), 'mosaic_gold')
    for b in (W_, E_):
        for sgn in (-1, 1): lunette_wall(b[0], b[1], 'v', sgn, b[2])
    for b in (N_, S_):
        for sgn in (-1, 1): lunette_wall(b[0], b[1], 'u', sgn, b[2])
    # gable walls closing the barrel vaults at the ends (west wall with the great window; north, south)
    def end_wall_u(u, vlo, vhi, want_du):
        r = (vhi - vlo) / 2; vc = (vlo + vhi) / 2
        outline = [(vlo, ZF), (vhi, ZF)] + [(vc + r * math.cos(a), z_s + r * math.sin(a)) for a in np.linspace(0, math.pi, 17)]
        door = [(AX - 1.4, ZF), (AX + 1.4, ZF), (AX + 1.4, ZF + 4.8), (AX - 1.4, ZF + 4.8)]
        loops = [G.ccw(outline), G.ccw(door)[::-1]]
        flat = loops[0] + loops[1]
        for (a, b, c) in G.tess(loops):
            pts = [W(u, flat[i][0], flat[i][1]) for i in (a, b, c)]
            quad(m, pts, nrm(want_du, 0), 'mosaic_gold' if pts[0][2] > ZF + 6.0 or pts[1][2] > ZF + 6.0 or pts[2][2] > ZF + 6.0 else 'basilica_marble')
    end_wall_u(U_WEST + 0.01, AX - W_[2], AX + W_[2], 1)
    # the great west window (lunette above the central portal): bright lattice
    gw = G.Mesh()
    r = W_[2] * 0.8
    for k in range(12):
        a0, a1 = math.pi * k / 12, math.pi * (k + 1) / 12
        pts = [W(U_WEST + 0.05, AX, z_s + 0.3), W(U_WEST + 0.05, AX + r * math.cos(a0), z_s + 0.3 + r * math.sin(a0)), W(U_WEST + 0.05, AX + r * math.cos(a1), z_s + 0.3 + r * math.sin(a1))]
        quad(gw, pts, nrm(1, 0), 'daylight')
    out.append((gw, 0))
    def end_wall_v(v, ulo, uhi, want_dv):
        r = (uhi - ulo) / 2; uc = (ulo + uhi) / 2
        outline = [(ulo, ZF), (uhi, ZF)] + [(uc + r * math.cos(a), z_s + r * math.sin(a)) for a in np.linspace(0, math.pi, 17)]
        loops = [[(p[0], p[1]) for p in outline]]
        for (a, b, c) in G.tess(loops):
            pts = [W(loops[0][i][0], v, loops[0][i][1]) for i in (a, b, c)]
            quad(m, pts, nrm(0, want_dv), 'mosaic_gold')
    end_wall_v(V_NORTH - 0.01, C_[0] - N_[2], C_[0] + N_[2], -1)
    end_wall_v(V_SOUTH + 0.01, C_[0] - S_[2], C_[0] + S_[2], 1)
    # piers at the corners of the central bay and the arm bays
    ph = 1.6
    for (bu, bv, h) in (W_, C_, E_):
        for su in (-1, 1):
            for sv in (-1, 1):
                cu, cv = bu + su * (h + ph), bv + sv * (h + ph)
                pier(m, cu - ph, cv - ph, cu + ph, cv + ph)
    for (bu, bv, h) in (N_, S_):
        for su in (-1, 1):
            for sv in (-1, 1):
                cu, cv = bu + su * (h + ph), bv + sv * (h + ph)
                if abs(cv - AX) < 9: continue
                pier(m, cu - ph, cv - ph, cu + ph, cv + ph)
    # side walls of the arms above the colonnades (gold), outer walls of the aisles (marble below, gold above)
    zg = ZF + 9.6
    for (ua, ub) in ((U_WEST, W_[0] + W_[2]), (C_[0] + C_[2], E_[0] + E_[2])):
        for sv in (-1, 1):
            v = AX + sv * W_[2]
            wall_uv(m, ua, v, ub, v, zg + 1.8, z_s, nrm(0, -sv), 'mosaic_gold')
            colonnade(m, ua + 0.5, v + sv * 0.2, ub - 0.5, v + sv * 0.2, ZF, 6.6, int((ub - ua) / 3.2))
    for (va, vb) in ((V_SOUTH, S_[1] + S_[2]), (N_[1] - N_[2], V_NORTH)):
        for su in (-1, 1):
            u = C_[0] + su * N_[2]
            wall_uv(m, u, va, u, vb, zg + 1.8, z_s, nrm(-su, 0), 'mosaic_gold')
            colonnade(m, u + su * 0.2, va + 0.5, u + su * 0.2, vb - 0.5, ZF, 6.6, int((vb - va) / 3.2))
    # aisle ceilings (gallery floors) and the outer walls
    for (ua, ub, va, vb) in ((U_WEST, C_[0] - C_[2], V_SOUTH, AX - W_[2]), (U_WEST, C_[0] - C_[2], AX + W_[2], V_NORTH),
                             (C_[0] + C_[2], U_EAST, V_SOUTH, AX - E_[2]), (C_[0] + C_[2], U_EAST, AX + E_[2], V_NORTH)):
        fill(m, (ua, ub, va, vb), zg, (0, 0, -1), 'mosaic_gold')
    # outer walls along the interior outline (ccw: the inside is on the left of each edge)
    ring = G.ccw(list(IN.exterior.coords))
    for k in range(len(ring)):
        a, b = ring[k], ring[(k + 1) % len(ring)]
        du, dv = b[0] - a[0], b[1] - a[1]
        if math.hypot(du, dv) < 0.05: continue
        nn = (-dv, du)
        wall_uv(m, a[0], a[1], b[0], b[1], ZF, ZF + 6.0, nrm(*nn), 'basilica_marble')
        wall_uv(m, a[0], a[1], b[0], b[1], ZF + 6.0, zg, nrm(*nn), 'mosaic_gold')
        wall_uv(m, a[0], a[1], b[0], b[1], zg, z_s + 6.3, nrm(*nn), 'mosaic_gold')
    # narthex: the vestibule between the central portal and the nave (marble walls, a gold barrel vault)
    nu0, nu1 = 40.6, U_WEST
    for sv in (-1, 1):
        wall_uv(m, nu0, AX + sv * 5.5, nu1, AX + sv * 5.5, ZF, ZF + 5.5, nrm(0, -sv), 'basilica_marble')
    quad(m, [W(nu0, AX - 5.5, ZF), W(nu1, AX - 5.5, ZF), W(nu1, AX + 5.5, ZF), W(nu0, AX + 5.5, ZF)], (0, 0, 1), 'basilica_floor')
    barrel(m, nu0, nu1, AX - 5.5, AX + 5.5, 'u', ZF + 5.5, n=12)
    for (uu, want) in ((nu0 + 0.02, 1), (nu1 - 0.02, -1)):
        outline = [(AX - 5.5, ZF), (AX + 5.5, ZF)] + [(AX + 5.5 * math.cos(a), ZF + 5.5 + 5.5 * math.sin(a)) for a in np.linspace(0, math.pi, 13)]
        door = [(AX - 1.4, ZF), (AX + 1.4, ZF), (AX + 1.4, ZF + 4.8), (AX - 1.4, ZF + 4.8)]
        loops = [G.ccw(outline), G.ccw(door)[::-1]]; flat = loops[0] + loops[1]
        for (a, b, c) in G.tess(loops):
            quad(m, [W(uu, flat[i][0], flat[i][1]) for i in (a, b, c)], nrm(want, 0), 'mosaic_gold')
    lamp(m, (nu0 + nu1) / 2, AX, ZF + 10.5, ZF + 3.6)
    # gallery floors and ceilings in the four corner zones (seen from the arms between colonnades and vaults)
    zgal = ZF + 9.6
    for (ua, ub, va, vb) in ((U_WEST, C_[0] - C_[2], V_SOUTH, AX - W_[2]), (U_WEST, C_[0] - C_[2], AX + W_[2], V_NORTH),
                             (C_[0] + C_[2], U_EAST, V_SOUTH, AX - E_[2]), (C_[0] + C_[2], U_EAST, AX + E_[2], V_NORTH)):
        fill(m, (ua, ub, va, vb), zgal + 0.02, (0, 0, 1), 'basilica_floor')
        fill(m, (ua, ub, va, vb), z_s + 6.0, (0, 0, -1), 'mosaic_gold')
    # a closing ceiling just above every vault crown (z_s + h) with the five domes cut out: nothing seen past the
    # extrados of a barrel or a pendentive can reach the roof lid (whose underside is not drawn)
    from shapely.geometry import Point as _Pt
    lid = IN
    for (bu, bv, h) in BAYS.values(): lid = lid.difference(_Pt(bu, bv).buffer(h - 0.01, 48))
    fill_geom(m, lid, z_s + 6.3, (0, 0, -1), 'mosaic_gold')
    floor(m)
    iconostasis(m)
    apse(m, out)
    # hanging lamps
    for (u, v) in ((61, AX - 3.5), (69, AX + 3.5), (79.5, AX - 3.5), (88, AX + 3.5), (75, AX), (57, AX), (83.7, 45), (83.7, 14), (98, AX - 3.5), (105, AX + 3.5), (65, AX - 9), (65, AX + 9), (101.5, AX - 9), (101.5, AX + 9)):
        lamp(m, u, v, ZF + ZS + 2.0, ZF + 4.2)
    out.append((m, 0))
    return out

def build(mb):
    for (m, layer) in build_mesh():
        place(mb, m, np.eye(4), c1=(layer, 0, 0, 0), max_edge=1.5)
    return dict(interior=True)

def walk_area():
    """the interior floor (nave, transepts, aisles), the presbytery at +1.5, piers blocked, door from the narthex."""
    out = []
    from shapely.geometry import box
    g = IN.buffer(-0.5, join_style=2).intersection(box(U_WEST, V_SOUTH - 5, U_EAST - 7.0, V_NORTH + 5))
    if g.geom_type != 'Polygon': g = max(g.geoms, key=lambda q: q.area)
    out.append((Polygon([tuple(wf(u, v)) for (u, v) in g.exterior.coords]), ZF))
    pres = Polygon([tuple(wf(94.8, AX - 7.8)), tuple(wf(U_EAST - 1.0, AX - 7.8)), tuple(wf(U_EAST - 1.0, AX + 7.8)), tuple(wf(94.8, AX + 7.8))])
    out.append((pres, ZF + 1.5))
    ph = 1.6
    for (bu, bv, h) in (BAYS['W'], BAYS['C'], BAYS['E']):
        for su in (-1, 1):
            for sv in (-1, 1):
                cu, cv = bu + su * (h + ph), bv + sv * (h + ph)
                out.append((Polygon([tuple(wf(cu - ph - 0.2, cv - ph - 0.2)), tuple(wf(cu + ph + 0.2, cv - ph - 0.2)), tuple(wf(cu + ph + 0.2, cv + ph + 0.2)), tuple(wf(cu - ph - 0.2, cv + ph + 0.2))]), None))
    # iconostasis screen (with a central opening) and the altar
    out.append((Polygon([tuple(wf(94.1, AX - 7.6)), tuple(wf(94.7, AX - 7.6)), tuple(wf(94.7, AX - 0.9)), tuple(wf(94.1, AX - 0.9))]), None))
    out.append((Polygon([tuple(wf(94.1, AX + 0.9)), tuple(wf(94.7, AX + 0.9)), tuple(wf(94.7, AX + 7.6)), tuple(wf(94.1, AX + 7.6))]), None))
    out.append((Polygon([tuple(wf(U_EAST - 5.5, AX - 2.2)), tuple(wf(U_EAST - 1.5, AX - 2.2)), tuple(wf(U_EAST - 1.5, AX + 2.2)), tuple(wf(U_EAST - 5.5, AX + 2.2))]), None))
    # the way in: from the piazza through the central portal and the narthex
    out.append((Polygon([tuple(wf(36.0, AX - 1.6)), tuple(wf(U_WEST + 1.0, AX - 1.6)), tuple(wf(U_WEST + 1.0, AX + 1.6)), tuple(wf(36.0, AX + 1.6))]), ZF - 0.2))
    from .basilica import walk_blocks          # and outside on the Piazzetta side: the Pilastri Acritani, the Pietra del Bando
    return out + walk_blocks()

def interior_zone():
    from shapely.geometry import box
    g = IN.buffer(0.6, join_style=2).union(box(36.5, AX - 6.0, U_WEST + 1.0, AX + 6.0)).simplify(0.3)
    return [tuple(round(x, 2) for x in wf(u, v)) for (u, v) in list(g.exterior.coords)[:-1]]
