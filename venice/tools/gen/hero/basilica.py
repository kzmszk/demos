"""Basilica di San Marco, exterior: massing from the OSM footprint, five lead domes with onion lanterns from
the OSM building:parts, and the west front (five portals with column clusters and mosaic lunettes, the
loggia with the horses, the upper arches with ogee crests, statues and Gothic tabernacles)."""
import math
import numpy as np
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from vk import geom as G, arch as A
from ..world import GROUND_Z
from .common import place, translate, compose, rotated_frame
# the church is turned ~3.5 deg clockwise from the piazza axis (OSM domes, outline and the central arch agree):
# its own frame, u along the nave (east), v north, pivot = the central dome; same numbers as the piazza frame there
wf, pf, PU, PV = rotated_frame(-3.5, (83.7, 29.7))

MARBLE = 'basilica_front'
import json as _json, os as _os
ART = _json.load(open('/home/kazu/work/demos/venice/public/tex/art.json'))['items'] if _os.path.exists('/home/kazu/work/demos/venice/public/tex/art.json') else {}
LUN_PANELS = []          # (mesh, art key) collected by west_front(): mosaic photos placed with their own art layer

def photo_panel(pts, y, key):
    """flat panel in the kit's x-z plane at depth y facing -y, uv spanning the outline's bounding box."""
    m = G.Mesh()
    P = list(pts)
    if G.signed_area(P) < 0: P = P[::-1]
    xs = [p[0] for p in P]; zs = [p[1] for p in P]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    for (a, b, c) in G.tess([P]):
        tri = [P[a], P[b], P[c]]
        V = [(q[0], y, q[1]) for q in tri]
        uv = [((q[0] - x0) / (x1 - x0), (q[1] - z0) / (z1 - z0)) for q in tri]
        n = np.cross(np.subtract(V[1], V[0]), np.subtract(V[2], V[0]))
        if n[1] > 0: V = V[::-1]; uv = uv[::-1]
        o = m.add_v(V); m.face([o, o + 1, o + 2], 'painting', uv=uv)
    LUN_PANELS.append((m, key))
    return m
FRONT_U = 37.4            # west front plane (church u)
V_N, V_S = 55.4, 5.4      # north and south ends of the west front (church v): the main portal on the nave axis

def kit_frame_west():
    """x from north to south along the front, facade faces -u (the piazza), z up."""
    x = -PV; y = PU
    o = wf(FRONT_U, V_N)
    M = np.eye(4); M[:3, 0] = (x[0], x[1], 0); M[:3, 1] = (y[0], y[1], 0); M[:3, 2] = (0, 0, 1); M[:3, 3] = (o[0], o[1], GROUND_Z)
    return M

def column_cluster(xc, side, z0, h, n, d, mats, depth0=0.25):
    """n columns stepping back into an arch's jamb (side = -1 left jamb, +1 right jamb)."""
    m = G.Mesh()
    for k in range(n):
        x = xc + side * (d * 0.55 + k * d * 1.05)
        y = -depth0 + k * d * 0.9
        mat = mats[k % len(mats)]
        m.merge(A.column(d, h, order='corinthian', mat=mat, cap_mat=MARBLE, seg=8, detail=0.1).transformed(G.mat4((x, y, z0))))
    return m

def ogee_crest(xc, zs, half, rise, n=14):
    """inflected-arch crest line (left half then right half) from the springers to the apex."""
    pts = []
    for i in range(n + 1):
        t = i / n
        x = xc - half + half * t
        # S curve: concave near the base, convex toward the apex
        z = zs + rise * (0.5 - 0.5 * math.cos(math.pi * t)) ** 1.6
        pts.append((x, z))
    right = [(2 * xc - x, z) for (x, z) in reversed(pts[:-1])]
    return pts + right

def crest_mesh(xc, zs, half, rise, y=-0.1):
    """marble crest following an ogee line with crockets (leafy knobs) and a finial statue base at the apex."""
    m = G.Mesh()
    pts = ogee_crest(xc, zs, half, rise)
    for i in range(len(pts) - 1):
        (x0, z0), (x1, z1) = pts[i], pts[i + 1]
        dx, dz = x1 - x0, z1 - z0; L = math.hypot(dx, dz)
        nx, nz = -dz / L, dx / L
        th = 0.45
        q = [(x0, z0), (x1, z1), (x1 + nx * th, z1 + nz * th), (x0 + nx * th, z0 + nz * th)]
        m.merge(G.extrude_xsection(q, 0.35, MARBLE, M=G.mat4((0, y - 0.35, 0))))
        if i % 2 == 0 and 1 < i < len(pts) - 2:
            cx, cz = x0 + nx * th, z0 + nz * th
            m.merge(G.lathe([(0.0, 0), (0.2, 0.08), (0.24, 0.25), (0.12, 0.42), (0.0, 0.46)], 6, mat=MARBLE).transformed(G.mat4((cx, y - 0.17, cz))))
    return m

def statue(h=2.4, mat=MARBLE):
    """stylised standing figure (plinth, robed body, head) — reads as a statue against the sky."""
    m = G.Mesh()
    m.merge(G.box(-0.35, -0.35, 0, 0.35, 0.35, 0.3, mat))
    m.merge(G.lathe([(0.32, 0.3), (0.36, 0.9), (0.30, h * 0.55), (0.24, h * 0.72), (0.27, h * 0.78), (0.12, h * 0.82), (0.0, h * 0.84)], 8, mat=mat))
    m.merge(G.lathe([(0.0, h * 0.84), (0.13, h * 0.86), (0.14, h * 0.93), (0.08, h * 0.99), (0.0, h)], 8, mat=mat))
    return m

def tabernacle(x, z0, mat=MARBLE):
    """Gothic pinnacle: square niche with statue, gables and a pointed spire (~5 m)."""
    m = G.Mesh()
    w = 1.25
    for (sx, sy) in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        m.merge(G.box(x + sx * w / 2 - 0.12, -w / 2 + sy * w / 2 - 0.12, z0, x + sx * w / 2 + 0.12, -w / 2 + sy * w / 2 + 0.12, z0 + 2.6, mat))
    m.merge(G.box(x - w / 2 - 0.1, -w - 0.1, z0 - 0.3, x + w / 2 + 0.1, 0.1, z0, mat))
    m.merge(statue(1.9, mat).transformed(G.mat4((x, -w / 2, z0))))
    m.merge(G.box(x - w / 2 - 0.12, -w - 0.12, z0 + 2.6, x + w / 2 + 0.12, 0.12, z0 + 2.85, mat))
    m.merge(G.lathe([(w * 0.62, 0), (w * 0.5, 0.6), (0.18, 2.6), (0.0, 3.0)], 4, mat=mat, center=(x, -w / 2, z0 + 2.85)))
    m.merge(G.lathe([(0.0, 0), (0.12, 0.1), (0.0, 0.35)], 6, mat='gold', center=(x, -w / 2, z0 + 5.85)))
    return m

def tube(path, radii, mat, n=10, lateral=(0.0, 1.0, 0.0), caps=True):
    """smooth tube along a polyline lying in the plane normal to `lateral`; radii [(a, b)]: a = half-width across
    the plane, b = half-depth in it (elliptic sections, e.g. a horse's deep narrow neck)."""
    m = G.Mesh(); P = [np.array(p, float) for p in path]; Y = np.array(lateral, float)
    rings = []
    for i, c in enumerate(P):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]); d /= np.linalg.norm(d)
        Nn = np.cross(d, Y); Nn /= np.linalg.norm(Nn); Yy = np.cross(Nn, d)
        a, b = radii[i]
        rings.append(m.add_v([c + Yy * (a * math.cos(t)) + Nn * (b * math.sin(t)) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]))
    for i in range(len(P) - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(n):
            j1 = (j + 1) % n
            m.face([A + j, A + j1, B + j1, B + j], mat, True)
    if caps:
        for (R, c, sg) in ((rings[0], P[0], -1), (rings[-1], P[-1], 1)):
            o = m.add_v([c]); 
            for j in range(n):
                j1 = (j + 1) % n
                m.face([R + j, R + j1, o] if sg > 0 else [R + j1, R + j, o], mat, True)
    return m

def horse(mat='bronze_gilt', raise_right=True):
    """one of the four horses of St Mark: a striding horse, one foreleg lifted, head bowed and turned a little;
    ~2.3 m to the ears, ~2.5 m long, facing +x, hooves at z = 0."""
    m = G.Mesh()
    # barrel: rump -> chest (sections deepen at the belly, the chest is narrower)
    body = [(-1.06, 0, 1.33), (-0.95, 0, 1.36), (-0.70, 0, 1.33), (-0.35, 0, 1.27), (0.05, 0, 1.26), (0.40, 0, 1.30), (0.66, 0, 1.38), (0.80, 0, 1.47)]
    br = [(0.10, 0.12), (0.27, 0.30), (0.33, 0.37), (0.32, 0.38), (0.31, 0.39), (0.29, 0.38), (0.24, 0.33), (0.13, 0.18)]
    m.merge(tube(body, br, mat, n=14))
    # neck (deep, narrow, arched) and head (bowed, muzzle down)
    neck = [(0.55, 0, 1.52), (0.74, 0, 1.78), (0.88, 0, 2.00), (0.98, 0.02, 2.16), (1.04, 0.04, 2.24)]
    nr = [(0.20, 0.30), (0.17, 0.27), (0.14, 0.22), (0.12, 0.17), (0.11, 0.14)]
    m.merge(tube(neck, nr, mat, n=12))
    head = [(1.00, 0.04, 2.30), (1.12, 0.06, 2.18), (1.25, 0.08, 2.04), (1.35, 0.09, 1.92), (1.40, 0.09, 1.86)]
    hr = [(0.11, 0.13), (0.11, 0.13), (0.09, 0.11), (0.08, 0.09), (0.07, 0.07)]
    m.merge(tube(head, hr, mat, n=10))
    for sy in (-1, 1):   # ears
        m.merge(G.lathe([(0.035, 0.0), (0.025, 0.08), (0.0, 0.15)], 6, mat=mat).transformed(G.mat4((0.99, 0.04 + sy * 0.07, 2.36), ry=-0.3)))
    # cropped mane: a low crest along the top of the neck
    crest = [(0.58, 0, 1.80), (0.74, 0, 2.02), (0.88, 0, 2.18), (0.98, 0.02, 2.33)]
    m.merge(tube(crest, [(0.04, 0.05), (0.05, 0.06), (0.05, 0.06), (0.04, 0.04)], mat, n=6))
    # tail, knotted short
    m.merge(tube([(-1.02, 0, 1.40), (-1.14, 0, 1.22), (-1.18, 0, 1.00), (-1.15, 0, 0.82)], [(0.06, 0.07), (0.07, 0.08), (0.07, 0.08), (0.04, 0.05)], mat, n=8))
    # legs: thigh/forearm -> knee/hock -> cannon -> fetlock -> hoof
    def leg(pts, rr): m.merge(tube(pts, rr, mat, n=8))
    fr = [(0.11, 0.13), (0.075, 0.08), (0.05, 0.055), (0.055, 0.06), (0.065, 0.07)]
    hr2 = [(0.13, 0.18), (0.09, 0.10), (0.06, 0.07), (0.05, 0.055), (0.055, 0.06), (0.065, 0.07)]
    for sy in (-1, 1):
        y = sy * 0.17
        if raise_right and sy < 0:   # lifted foreleg, knee bent
            leg([(0.52, y, 1.12), (0.74, y, 0.80), (0.62, y, 0.58), (0.64, y, 0.47), (0.69, y, 0.40)], fr)
        else:
            leg([(0.50, y, 1.12), (0.53, y, 0.62), (0.54, y, 0.26), (0.56, y, 0.10), (0.58, y, 0.03)], fr)
        leg([(-0.70, y, 1.18), (-0.56, y, 0.82), (-0.80, y, 0.50), (-0.77, y, 0.20), (-0.75, y, 0.10), (-0.73, y, 0.03)], hr2)
    return m

def lion_mesh(h=2.2, mat='bronze_gilt'):
    """the winged lion of St Mark, a gilt relief silhouette in the x-z plane facing -y (x right, z up)."""
    s = h / 2.2
    body = [(-1.25, 0.55), (-1.0, 0.7), (-0.2, 0.75), (0.45, 0.85), (0.75, 1.15), (0.95, 1.5), (1.25, 1.55), (1.35, 1.35),
            (1.15, 1.2), (1.05, 0.95), (0.95, 0.6), (1.05, 0.0), (0.85, 0.0), (0.7, 0.55), (0.35, 0.55), (0.3, 0.0), (0.1, 0.0),
            (0.05, 0.55), (-0.75, 0.5), (-0.8, 0.0), (-1.0, 0.0), (-1.05, 0.45), (-1.4, 0.95), (-1.55, 1.2), (-1.45, 1.25), (-1.3, 0.95)]
    wing = [(-0.1, 0.8), (-0.5, 1.3), (-0.9, 1.75), (-1.1, 2.05), (-0.6, 1.95), (-0.15, 1.75), (0.25, 1.4), (0.4, 0.95)]
    book = [(1.15, 0.55), (1.75, 0.65), (1.7, 1.25), (1.1, 1.15)]
    m = G.Mesh()
    for (pts, th) in ((body, 0.12), (wing, 0.08), (book, 0.10)):
        P = [(x * s, z * s) for (x, z) in pts]
        m.merge(A.fix_orient(G.prism([P], 0.0, th, mat, top=True), (0, 0, 1)).transformed(G.mat4((0, 0, 0), rx=math.pi / 2)))
    return m

def _bar(p0, p1, y, t, mat='cast_iron'):
    """a square bar in the facade plane (x, z) from p0 to p1 at depth y."""
    (x0, z0), (x1, z1) = p0, p1
    L = math.hypot(x1 - x0, z1 - z0); a = math.atan2(z1 - z0, x1 - x0)
    b = G.box(0.0, y - t / 2, -t / 2, L, y + t / 2, t / 2, mat)
    M = np.eye(4); M[0, 0], M[0, 2], M[2, 0], M[2, 2] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a); M[:3, 3] = (x0, 0.0, z0)
    return b.transformed(M)

def west_front():
    m = G.Mesh()
    W = (V_N - V_S)                     # 50.0 (the OSM outline's front)
    xc = W / 2; K = W / 51.8            # bay layout drawn for 51.8 m
    bays = [(xc - 18.6 * K, 6.0 * K, 'side'), (xc - 9.9 * K, 6.4 * K, 'side'), (xc, 8.2 * K, 'main'), (xc + 9.9 * K, 6.4 * K, 'side'), (xc + 18.6 * K, 6.0 * K, 'side')]
    ztop = 11.4
    # lower register wall (marble revetment) with the five portal arches
    holes = []
    for (bx, bw, kind) in bays:
        zs = 6.6 if kind == 'main' else 5.4
        holes.append(G.opening_shape(bw, zs + bw / 2, 'arch', n=16, x=bx - bw / 2, y=0.0))
    m.merge(G.wall(W, ztop, 0.6, MARBLE, openings=holes, back=False, sides=True, top=False))
    cmats = ['marble_verde', 'marble_red', 'marble_white', 'marble_pink', 'marble_verde']
    lun = 0
    for (bx, bw, kind) in bays:
        zs = 6.6 if kind == 'main' else 5.4
        depth = 3.4 if kind == 'main' else 2.6
        r = bw / 2
        # recess: barrel vault soffit + side walls + back wall with the door and the mosaic lunette
        pts = [(bx + r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(0, math.pi, 17)]
        for i in range(len(pts) - 1):
            (x0, z0), (x1, z1) = pts[i], pts[i + 1]
            q = [(x0, 0.0, z0), (x1, 0.0, z1), (x1, depth, z1), (x0, depth, z0)]
            o = m.add_v(q); m.face([o + 3, o + 2, o + 1, o], 'mosaic_gold')
        for sx in (-1, 1):
            q = [(bx + sx * r, 0.0, 0.0), (bx + sx * r, depth, 0.0), (bx + sx * r, depth, zs), (bx + sx * r, 0.0, zs)]
            o = m.add_v(q); m.face([o, o + 1, o + 2, o + 3] if sx < 0 else [o + 3, o + 2, o + 1, o], MARBLE)
        back = [(bx - r, 0.0), (bx + r, 0.0)] + [(bx + r * math.cos(a), zs + r * math.sin(a)) for a in np.linspace(0, math.pi, 17)]
        door_w, door_h = (2.6, 4.6) if kind == 'main' else (2.1, 3.9)
        door = [(bx - door_w / 2, 0.0), (bx + door_w / 2, 0.0), (bx + door_w / 2, door_h), (bx - door_w / 2, door_h)]
        m.merge(A.fix_orient(G.cap([back, door], 0, MARBLE, True, G.frame((0, depth, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
        if kind == 'main':
            # the main portal stands open: bronze leaves swung back into the narthex
            for sx in (-1, 1):
                hx = bx + sx * door_w / 2
                m.merge(G.box(min(hx, hx - sx * 0.08), depth + 0.05, 0.0, max(hx, hx - sx * 0.08), depth + 0.05 + door_w / 2, door_h - 0.05, 'bronze'))
        else:
            m.merge(A.fix_orient(G.cap([door], 0, 'bronze', True, G.frame((0, depth + 0.15, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
        # lunette (mosaic) filling the semicircle above the springing, slightly in front of the back wall
        lunp = [(bx - r * 0.92, zs - 0.4)] + [(bx + r * 0.92 * math.cos(a), zs + r * 0.92 * math.sin(a)) for a in np.linspace(math.pi, 0, 17)] + [(bx + r * 0.92, zs - 0.4)]
        lunp = lunp[::-1]
        photo_panel(lunp, depth - 0.05, f'lun{lun}')
        lun += 1
        # column clusters on both jambs: two tiers
        n = 4 if kind == 'main' else 3
        for sx in (-1, 1):
            m.merge(column_cluster(bx + sx * (r + 0.05), sx, 0.0, 4.4, n, 0.38, cmats))
            m.merge(column_cluster(bx + sx * (r + 0.05), sx, 4.55, zs - 4.55, n, 0.32, cmats[1:]))
            m.merge(G.box(bx + sx * r - 0.9 * (sx < 0) - 0.0, -0.6, 4.4, bx + sx * r + 0.9 * (sx > 0), 0.3, 4.55, MARBLE))
        m.merge(A.arch_moulding(bx, zs, r, 0.5, 0.12, MARBLE, y=0.0, n=16))
    # terrace: cornice, floor, balustrade, the four horses on the central arch
    m.merge(A.straight(A.cornice_profile(0.5, 0.45), -0.3, W + 0.3, ztop - 0.5, 0.0, MARBLE))
    m.merge(G.box(0.0, 0.0, ztop, W, 3.2, ztop + 0.12, 'portico_floor', faces=('+z',)))
    m.merge(A.balustrade(0.3, W - 0.3, ztop, 1.0, 0.24, MARBLE, y=-0.1, pier_every=3.2, bal_seg=6))
    for k, dx in enumerate((-3.6, -1.2, 1.2, 3.6)):
        m.merge(G.box(xc + dx - 0.9, 0.3, ztop, xc + dx + 0.9, 1.6, ztop + 1.0, MARBLE))
        # two pairs turned toward each other (outer horses look in, inner ones out), each lifting the inner foreleg
        rz = -math.pi / 2 + (0.32 if dx < 0 else -0.32) * (1 if abs(dx) > 2 else -1)
        m.merge(horse(raise_right=dx < 0).transformed(G.mat4((xc + dx, 0.95, ztop + 1.0), rz=rz)))
    # upper register: wall set back 3.2 m with the five upper arches
    yb = 3.2; zt2 = 22.0
    uppers = [(xc - 18.8 * K, 5.6 * K), (xc - 10.4 * K, 5.8 * K), (xc, 11.2 * K), (xc + 10.4 * K, 5.8 * K), (xc + 18.8 * K, 5.6 * K)]
    holes2 = []
    for (bx, bw) in uppers:
        zs2 = 13.0 if bw > 8 else 13.4
        holes2.append([(p[0], p[1]) for p in G.opening_shape(bw, zs2 + bw / 2 - ztop, 'arch', n=16, x=bx - bw / 2, y=0.0)])
    m.merge(G.wall(W, zt2 - ztop, 0.8, MARBLE, openings=holes2, back=False, sides=True, top=True).transformed(G.mat4((0, yb, ztop))))
    for k, (bx, bw) in enumerate(uppers):
        zs2 = 13.0 if bw > 8 else 13.4
        r = bw / 2
        if bw > 8:
            # central arch: great window (lattice) with the blue starry field and the winged lion above
            rw = r - 0.02
            win = [(bx - rw, ztop + 0.3), (bx + rw, ztop + 0.3)] + [(bx + rw * math.cos(a), zs2 + rw * math.sin(a)) for a in np.linspace(0, math.pi, 25)]
            m.merge(A.fix_orient(G.cap([win], 0, 'glass_lattice', True, G.frame((0, yb + 0.7, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
            # the iron lattice: a square grid clipped to the arch, a heavier frame on the semicircle and the transom
            g = 0.62; yl = yb + 0.64
            for i in range(-int(rw / g), int(rw / g) + 1):
                x = bx + i * g; h = math.sqrt(max(rw * rw - (x - bx) ** 2, 0.0))
                m.merge(G.box(x - 0.03, yl - 0.04, ztop + 0.3, x + 0.03, yl + 0.04, zs2 + h, 'cast_iron'))
            zz = ztop + 0.3 + g
            while zz < zs2 + rw:
                hw = rw if zz <= zs2 else math.sqrt(max(rw * rw - (zz - zs2) ** 2, 0.0))
                m.merge(G.box(bx - hw, yl - 0.04, zz - 0.03, bx + hw, yl + 0.04, zz + 0.03, 'cast_iron'))
                zz += g
            for k in range(24):
                a0, a1 = math.pi * k / 24, math.pi * (k + 1) / 24
                p0 = (bx + rw * math.cos(a0), zs2 + rw * math.sin(a0)); p1 = (bx + rw * math.cos(a1), zs2 + rw * math.sin(a1))
                m.merge(_bar(p0, p1, yl, 0.09))
            m.merge(G.box(bx - rw, yl - 0.05, zs2 - 0.06, bx + rw, yl + 0.05, zs2 + 0.06, 'cast_iron'))
        else:
            lunp = [(bx - r, zs2 - 1.6)] + [(bx + r * math.cos(a), zs2 + r * math.sin(a)) for a in np.linspace(math.pi, 0, 17)] + [(bx + r, zs2 - 1.6)]
            photo_panel(lunp[::-1], yb + 0.6, f'lun{5 + (k if k < 2 else k - 1)}')
            low = [(bx - r, ztop + 0.2), (bx + r, ztop + 0.2), (bx + r, zs2 - 1.6), (bx - r, zs2 - 1.6)]
            m.merge(A.fix_orient(G.cap([low[::-1]], 0, MARBLE, True, G.frame((0, yb + 0.62, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
        m.merge(A.arch_moulding(bx, zs2, r, 0.55, 0.15, MARBLE, y=yb, n=16))
        # ogee crest with crockets and a statue at the apex
        rise = 4.6 if bw > 8 else 2.8
        m.merge(crest_mesh(bx, zs2 + 0.2, r + 0.55, r + rise, y=yb))
        m.merge(statue(3.0 if bw > 8 else 2.2).transformed(G.mat4((bx, yb - 0.1, zs2 + r + rise + 0.6))))
    # the blue field with gold stars and the winged lion inside the central arch, above the window
    bx, bw = uppers[2]; r = bw / 2; z0 = 13.0 + r + 0.75
    field = [(bx - 2.9, z0), (bx + 2.9, z0), (bx + 2.0, z0 + 1.7), (bx + 0.9, z0 + 2.8), (bx, z0 + 3.3), (bx - 0.9, z0 + 2.8), (bx - 2.0, z0 + 1.7)]
    m.merge(A.fix_orient(G.cap([field], 0, 'lion_field', True, G.frame((0, yb - 0.04, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
    for (sx, sz) in ((-1.9, 0.4), (-0.9, 0.3), (1.0, 0.35), (2.0, 0.45), (-1.3, 1.3), (1.4, 1.25), (0.0, 2.6), (-0.6, 2.2), (0.7, 2.15)):
        m.merge(G.box(bx + sx - 0.07, yb - 0.08, z0 + sz - 0.07, bx + sx + 0.07, yb - 0.05, z0 + sz + 0.07, 'bronze_gilt'))
    m.merge(lion_mesh(1.7).transformed(G.mat4((bx - 0.1, yb - 0.06, z0 + 0.65))))
    # tabernacles between and at the ends of the upper arches
    for x in (xc - 23.0 * K, xc - 14.6 * K, xc - 5.9 * K, xc + 5.9 * K, xc + 14.6 * K, xc + 23.0 * K):
        m.merge(tabernacle(x, ztop + 5.4).transformed(G.mat4((0, yb, 0))))
    return m

def domes(world, M_unused=None):
    """the five domes from the OSM building:parts (drum height 30 m in OSM, dome to 41/45 m, lantern 46.5/50.5)."""
    o = world.o; m = G.Mesh(); out = []
    for wid, wy in o.ways.items():
        t = wy.get('tags', {})
        if t.get('building:part') and t.get('roof:shape') == 'onion':
            P = np.array(o.way_xy(wid)); c = P[:-1].mean(0); rl = float(np.linalg.norm(P[:-1] - c, axis=1).mean())
            top = float(t.get('height', 46.5)); out.append((c, rl, top))
    for wid, wy in o.ways.items():
        t = wy.get('tags', {})
        if t.get('building:part') and t.get('roof:shape') == 'dome' and float(t.get('height', 0)) >= 40:
            P = np.array(o.way_xy(wid)); c = P[:-1].mean(0); R = float(np.linalg.norm(P[:-1] - c, axis=1).mean())
            H = float(t.get('height')); base = 26.5
            lt = min(out, key=lambda e: np.linalg.norm(e[0] - c)) if out else (c, 1.2, H + 5.5)
            prof = [(R + 0.4, base - 4.5), (R + 0.4, base - 0.4), (R + 0.7, base - 0.2), (R + 0.7, base)]          # drum
            for k in range(13):                                                                                  # raised lead helmet
                a = k / 12
                rr = (R + 0.6) * math.sin(math.pi / 2 * (1 - a) ** 0.9) * (1.0 + 0.08 * math.sin(math.pi * a))
                prof.append((max(rr, lt[1] * 0.75), base + (H - base) * (1 - (1 - a) ** 1.35)))
            m.merge(G.lathe(prof, 32, mat='lead').transformed(G.mat4((c[0], c[1], GROUND_Z))))
            # drum windows (dark rectangles)
            for k in range(12):
                a = 2 * math.pi * k / 12
                x, y = c[0] + math.cos(a) * (R + 0.42), c[1] + math.sin(a) * (R + 0.42)
                m.merge(G.box(-0.35, -0.04, -1.5, 0.35, 0.04, 0.0, 'dark').transformed(G.mat4((x, y, GROUND_Z + base - 1.2), rz=a + math.pi / 2)))
            # onion lantern + cross
            lr = lt[1] * 0.9; z0 = GROUND_Z + H - 0.2
            m.merge(G.lathe([(lr * 0.5, 0), (lr * 0.55, 0.9), (lr * 1.05, 1.6), (lr * 1.15, 2.4), (lr * 0.6, 3.6), (0.12, 4.6), (0.08, 5.2), (0.0, 5.3)], 16, mat='lead').transformed(G.mat4((c[0], c[1], z0))))
            m.merge(G.box(-0.05, -0.05, 5.2, 0.05, 0.05, 7.4, 'gold').transformed(G.mat4((c[0], c[1], z0))))
            m.merge(G.box(-0.05, -0.55, 6.5, 0.05, 0.55, 6.62, 'gold').transformed(G.mat4((c[0], c[1], z0))))
            m.merge(G.lathe([(0.0, 0), (0.22, 0.2), (0.0, 0.42)], 8, mat='gold').transformed(G.mat4((c[0], c[1], z0 + 7.3))))
    return m

def body(world, poly):
    """massing of the church from the OSM footprint: marble-clad walls to the roof terraces, lead roofs
    (the lid is open where the domes rise, so the interior domes see up into the outer shells)."""
    m = G.Mesh()
    from shapely.geometry import Polygon as SP
    # the massing starts behind the west front (whose upper register is set back 3.2 m): cut the footprint at u = 44
    strip = SP([tuple(wf(-60, -60)), tuple(wf(44.0, -60)), tuple(wf(44.0, 130)), tuple(wf(-60, 130))])
    P = orient(poly.simplify(0.5, preserve_topology=True).difference(strip).buffer(0), 1.0)
    if P.geom_type != 'Polygon': P = max(P.geoms, key=lambda g: g.area)
    ring = G.ccw(list(P.exterior.coords)[:-1])
    # the walls (as G.prism), except that the west one (u = 44) is open where the narthex runs through it, up to the
    # narthex vault's crown: it stood as a blank wall 3 m inside the main portal
    from . import basilica_int as BI
    nv0, nv1, zn = BI.AX - 5.5, BI.AX + 5.5, BI.ZF + 11.1
    z0, z1 = GROUND_Z - 0.1, GROUND_Z + 22.0
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        (ua, va), (ub, vb) = pf(a), pf(b)
        lo, hi = max(min(va, vb), nv0), min(max(va, vb), nv1)
        runs = [(a, b, z0)]
        if abs(ua - 44.0) < 0.05 and abs(ub - 44.0) < 0.05 and hi - lo > 0.01:
            s0, s1 = (lo, hi) if va < vb else (hi, lo)
            p0, p1 = tuple(wf(44.0, s0)), tuple(wf(44.0, s1))
            runs = [(a, p0, z0), (p0, p1, zn), (p1, b, z0)]
        for (p, q, zb) in runs:
            if math.dist(p[:2], q[:2]) < 0.01: continue
            o = m.add_v([(p[0], p[1], zb), (q[0], q[1], zb), (q[0], q[1], z1), (p[0], p[1], z1)])
            m.face([o, o + 1, o + 2, o + 3], 'basilica_wall')
    # close the zone between the facade's upper register and the massing: a back wall at u = 44 and a lead lid
    front = poly.intersection(strip)
    if not front.is_empty:
        fv = [pf(c)[1] for c in front.exterior.coords] if front.geom_type == 'Polygon' else [pf(c)[1] for g in front.geoms for c in g.exterior.coords]
        v0, v1 = min(fv), max(fv)
        lid = [tuple(wf(FRONT_U + 3.0, v0)), tuple(wf(44.0, v0)), tuple(wf(44.0, v1)), tuple(wf(FRONT_U + 3.0, v1))]
        m.merge(G.cap([lid], GROUND_Z + 22.0, 'lead', True))
    from . import basilica_int as BI
    holes = []
    for (u, v, h) in BI.BAYS.values():
        c = wf(u, v); holes.append([(c[0] + (h + 0.3) * math.cos(a), c[1] + (h + 0.3) * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 32, endpoint=False)])
    m.merge(G.cap([ring] + holes, GROUND_Z + 22.0, 'lead', True))
    m.merge(side_arcades(world, ring))
    return m

def side_arcades(world, ring):
    """the free side walls (Piazzetta, Leoncini, apse): blind arcades on pilasters below, arched windows above,
    cornices at the terrace and the roof line.  Walls shared with neighbours and the west front are skipped."""
    from shapely.geometry import Point
    from .common import facade_frame
    out = G.Mesh()
    n = len(ring)
    for i in range(n):
        a = np.array(ring[i][:2]); b = np.array(ring[(i + 1) % n][:2])
        L = float(np.linalg.norm(b - a))
        if L < 4.0: continue
        d = (b - a) / L; nout = np.array([d[1], -d[0]])                     # ccw ring: outside on the right
        mid = (a + b) / 2
        if pf(mid)[0] < 44.5: continue                                       # behind the west front
        probe = Point(*(mid + nout * 1.5))
        if any(world.buildings[j].poly.contains(probe) for j in world.btree.query(probe) if world.buildings[j].id != 'w138800932'): continue
        M, _, _ = facade_frame(a, b, nout)
        m = G.Mesh()
        nb = max(1, int(round(L / 3.9))); w = L / nb
        for k in range(nb + 1):                                             # pilasters
            x = min(max(k * w, 0.25), L - 0.25)
            m.merge(G.box(x - 0.25, -0.16, 0.0, x + 0.25, 0.0, 10.6, MARBLE))
            m.merge(G.box(x - 0.2, -0.12, 11.4, x + 0.2, 0.0, 21.2, MARBLE))
        for k in range(nb):
            xc = (k + 0.5) * w; r = w / 2 - 0.25
            if r < 0.7: continue
            zs = 10.3 - r
            m.merge(A.arch_moulding(xc, zs, r, 0.28, 0.12, MARBLE, y=0.0, n=12))
            panel = [(xc - r + 0.15, 0.35), (xc + r - 0.15, 0.35)] + [(xc + (r - 0.15) * math.cos(t), zs + (r - 0.15) * math.sin(t)) for t in np.linspace(0, math.pi, 13)]
            m.merge(A.fix_orient(G.cap([panel], 0, 'marble_pink' if k % 3 == 1 else 'basilica_marble_ext', True, G.frame((0, -0.03, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
            # upper register: a round-headed window
            ww = min(1.5, w * 0.38); zw = 13.2; hw = 3.2
            win = [(xc - ww / 2, zw), (xc + ww / 2, zw)] + [(xc + ww / 2 * math.cos(t), zw + hw + ww / 2 * math.sin(t)) for t in np.linspace(0, math.pi, 11)]
            m.merge(A.fix_orient(G.cap([win], 0, 'glass', True, G.frame((0, -0.04, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
            m.merge(A.arch_moulding(xc, zw + hw, ww / 2 + 0.12, 0.2, 0.08, MARBLE, y=-0.04, n=10))
            m.merge(G.box(xc - ww / 2 - 0.2, -0.22, zw - 0.18, xc + ww / 2 + 0.2, 0.0, zw, MARBLE))
        m.merge(A.straight(A.cornice_profile(0.6, 0.45), 0.0, L, 10.6, 0.0, MARBLE, end_caps=True))
        m.merge(A.straight(A.cornice_profile(0.7, 0.5), 0.0, L, 21.3, 0.0, MARBLE, end_caps=True))
        out.merge(m, M)
    return out

# the Piazzetta side: the two Pilastri Acritani, the Pietra del Bando at the south-west corner, the Tetrarchs set
# into the corner of the treasury (church frame; the south wall of the west part runs at v = 6.0, the treasury's
# west face at u = 59.35 down to its corner at v = -2.25)
ACRITANI = [(49.8, 2.9), (53.6, 2.9)]
BANDO = (38.7, 5.0)

def south_monuments():
    m = G.Mesh()
    z0 = GROUND_Z - 0.2
    for (u, v) in ACRITANI:
        c = wf(u, v); x, y = c
        m.merge(G.box(x - 0.55, y - 0.55, z0, x + 0.55, y + 0.55, z0 + 0.6, MARBLE))                 # base
        m.merge(G.box(x - 0.42, y - 0.42, z0 + 0.6, x + 0.42, y + 0.42, z0 + 4.9, 'marble_white'))    # carved shaft
        for k in range(6):                                                                            # bands of carved vine scroll
            zz = z0 + 1.0 + k * 0.65
            m.merge(G.box(x - 0.45, y - 0.45, zz, x + 0.45, y + 0.45, zz + 0.12, MARBLE))
        m.merge(G.box(x - 0.52, y - 0.52, z0 + 4.9, x + 0.52, y + 0.52, z0 + 5.5, MARBLE))           # capital block
        m.merge(G.box(x - 0.6, y - 0.6, z0 + 5.5, x + 0.6, y + 0.6, z0 + 5.7, MARBLE))
    c = wf(*BANDO)
    m.merge(G.cylinder(0.48, z0, z0 + 1.45, 20, 'porphyry', top=True).transformed(G.mat4((c[0], c[1], 0))))
    # the Tetrarchs: two embracing pairs in porphyry on a bracket, on the treasury's west face near its corner
    ang = math.atan2(-PU[1], -PU[0])
    for k, dv in enumerate((-1.75, -1.35, -0.85, -0.45)):
        p = wf(59.0, dv)
        m.merge(statue(1.3, 'porphyry').transformed(G.mat4((p[0], p[1], GROUND_Z + 1.7), rz=ang + math.pi / 2 + (0.25 if k % 2 == 0 else -0.25))))
    q0, q1 = wf(58.75, -2.1), wf(59.35, -0.25)
    m.merge(G.box(min(q0[0], q1[0]), min(q0[1], q1[1]), GROUND_Z + 1.5, max(q0[0], q1[0]), max(q0[1], q1[1]), GROUND_Z + 1.7, 'porphyry'))
    return m

def walk_blocks():
    """the monuments block the way (the pillars, the stump)."""
    from shapely.geometry import Point
    out = [(Point(*wf(u, v)).buffer(0.75, 8), None) for (u, v) in ACRITANI]
    out.append((Point(*wf(*BANDO)).buffer(0.6, 12), None))
    return out

def build(mb, world, poly):
    place(mb, body(world, poly), np.eye(4))
    place(mb, south_monuments(), np.eye(4))
    place(mb, domes(world), np.eye(4))
    LUN_PANELS.clear()
    M = kit_frame_west()
    place(mb, west_front(), M)
    for (pm, key) in LUN_PANELS:
        if key in ART: place(mb, pm, M, c1=(ART[key]['layer'], 0, 0, 0), max_edge=1.0)
    from . import basilica_int
    basilica_int.build(mb)
    return dict(height=50.5)
