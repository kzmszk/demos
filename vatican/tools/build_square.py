"""Piazza San Pietro: Bernini's colonnade (fitted to the OSM columns), obelisk, the two fountains,
paving pattern, Piazza Retta with the sagrato steps, Braccio di Costantino / Carlo Magno.
World coordinates (x east, y north, z above the obelisk base)."""
import math, sys, json
import numpy as np
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
from vb.geom import *
from vb.arch import *
from vb import site, terrain

TRAV = 'travertine'; FIT = json.load(open('/home/kazu/work/demos/vatican/tools/ref/colonnade_fit.json'))
SQ = json.load(open('/home/kazu/work/demos/vatican/tools/ref/square_osm.json'))

# colonnade geometry (symmetrised fit of the OSM columns)
CY = (FIT['north']['centre'][1] - FIT['south']['centre'][1]) / 2          # ~32.1
RADII = [(a + b) / 2 for a, b in zip(FIT['north']['radii'], FIT['south']['radii'])]   # 4 rows
DA = math.radians(3.655)
A0 = math.radians(17.9); A1 = math.radians(164.0)       # angular extent of the columns (north arm, from +x)
NCOL = int(round((A1 - A0) / DA)) + 1
COL_H = 13.8; ENT_H = 2.6; BAL_H = 1.9
DIAM = [1.62, 1.68, 1.74, 1.80]
Z_COL = 0.45                                             # colonnade floor above the piazza (3 low steps)
PAV_K = {0, 1, NCOL // 2, NCOL - 2, NCOL - 1}            # pavilion positions (piers instead of columns)


def arm_xy(r, a, sgn):
    return (r * math.cos(a), sgn * (CY + r * math.sin(a)))


def colonnade_arm(sgn):
    m = Mesh()
    z0 = Z_COL
    r_in = RADII[0] - DIAM[0] / 2 - 0.9; r_out = RADII[3] + DIAM[3] / 2 + 0.9
    # floor platform with steps on the piazza side
    def ring_poly(r0, r1, a0, a1, n=80):
        inner = [arm_xy(r0, a0 + (a1 - a0) * i / n, sgn) for i in range(n + 1)]
        outer = [arm_xy(r1, a1 - (a1 - a0) * i / n, sgn) for i in range(n + 1)]
        return inner + outer
    ea = math.radians(1.6)
    for k, dz in enumerate((0.15, 0.3, 0.45)):
        m.merge(prism([ring_poly(r_in - 1.2 + k * 0.4, r_out + 0.6, A0 - ea - 0.004 * k, A1 + ea + 0.004 * k)], -2.0, dz, TRAV, mat_top='travertine_light'))
    # columns (Tuscan) and pavilion piers
    for k in range(NCOL):
        a = A0 + k * DA
        for row, r in enumerate(RADII):
            x, y = arm_xy(r, a, sgn)
            if k in PAV_K:
                if row in (0, 3):
                    rot = math.atan2(y - sgn * CY * 1, x)
                    m.merge(box(-1.1, -1.1, 0, 1.1, 1.1, COL_H, TRAV).transformed(mat4((x, y, z0), rz=rot)))
                continue
            m.merge(column(DIAM[row], COL_H, 'tuscan', TRAV, seg=20).transformed(mat4((x, y, z0), rz=a)))
    # entablature along inner and outer faces + end walls, then roof + balustrade
    zE = z0 + COL_H
    n = 96
    def arc_path(r, a0, a1):
        return [(*arm_xy(r, a0 + (a1 - a0) * i / n, sgn), 0.0) for i in range(n + 1)]
    # inner face (facing the piazza): profile projects toward the piazza = toward the arc centre
    ent_prof = [(0, 0)] + architrave_profile(1.0, 0.25)[1:-1] + [(0.25, 1.0), (0.2, 1.0), (0.2, 1.75)] + \
               [(s + 0.2, 1.75 + t) for (s, t) in cornice_profile(0.85, 1.0)[1:]] + [(0, 2.6)]
    for r, inward in ((r_in + 0.9 - 0.3, True), (r_out - 0.9 + 0.3, False)):
        P = arc_path(r, A0 - ea, A1 + ea)
        if sgn < 0: P = P[::-1]
        if inward ^ (sgn < 0): P = P[::-1]
        g = sweep(ent_prof, [(p[0], p[1], zE) for p in P], TRAV)
        m.merge(g)
    # roof slab and gabled roof between the balustrades
    rin, rout = r_in + 0.9 - 0.3, r_out - 0.9 + 0.3
    m.merge(prism([ring_poly(rin, rout, A0 - ea, A1 + ea, 96)], zE, zE + ENT_H, TRAV, mat_top='roof_flat'))
    mid = (rin + rout) / 2
    for a0_, a1_ in ((A0 - ea, A1 + ea),):
        nn = 96; pts_in = []; pts_mid = []; pts_out = []
        for i in range(nn + 1):
            a = a0_ + (a1_ - a0_) * i / nn
            pts_in.append((*arm_xy(rin + 1.6, a, sgn), zE + ENT_H)); pts_mid.append((*arm_xy(mid, a, sgn), zE + ENT_H + 2.4)); pts_out.append((*arm_xy(rout - 1.6, a, sgn), zE + ENT_H))
        for i in range(nn):
            for A, B in ((pts_in, pts_mid), (pts_mid, pts_out)):
                q = [A[i], A[i + 1], B[i + 1], B[i]]
                o = m.add_v(q)
                nrm = np.cross(np.array(q[1]) - q[0], np.array(q[3]) - q[0])
                m.face([o, o + 1, o + 2, o + 3] if nrm[2] > 0 else [o + 3, o + 2, o + 1, o], 'roof_tile')
    # balustrades on both edges (piers over every column line)
    zb = zE + ENT_H
    for r, side in ((rin + 0.15, 0), (rout - 0.95, 1)):
        P = [arm_xy(r, A0 - ea + (A1 - A0 + 2 * ea) * i / n, sgn) for i in range(n + 1)]
        for i in range(n):
            (xa, ya), (xb, yb) = P[i], P[i + 1]
            L = math.dist(P[i], P[i + 1]); ang = math.atan2(yb - ya, xb - xa)
            g = balustrade(0, L, 0, BAL_H, 0.8, TRAV, y=0, pier_every=None, bal_seg=6)
            m.merge(g.transformed(mat4((xa, ya, zb), rz=ang)))
    # ceilings: barrel vault over the central aisle, flat over the side aisles
    rc = (RADII[1] + RADII[2]) / 2; hw = (RADII[2] - RADII[1]) / 2 - 0.6
    nvault = 8
    for i in range(n):
        a_ = A0 - ea + (A1 - A0 + 2 * ea) * i / n; b_ = A0 - ea + (A1 - A0 + 2 * ea) * (i + 1) / n
        for j in range(nvault):
            t0, t1 = math.pi * j / nvault, math.pi * (j + 1) / nvault
            quad = []
            for (aa, tt) in ((a_, t0), (b_, t0), (b_, t1), (a_, t1)):
                rr = rc + hw * math.cos(tt); zz = zE - 0.6 + hw * 0.55 * math.sin(tt) - hw * 0.55 * 0
                quad.append((*arm_xy(rr, aa, sgn), zz))
            o = m.add_v(quad)
            nrm = np.cross(np.array(quad[1]) - quad[0], np.array(quad[3]) - quad[0])
            m.face([o, o + 1, o + 2, o + 3] if nrm[2] < 0 else [o + 3, o + 2, o + 1, o], 'stucco', True)
    for (r0, r1) in ((rin + 0.5, RADII[1] + 0.2), (RADII[2] - 0.2, rout - 0.5)):
        poly = ring_poly(r0, r1, A0 - ea, A1 + ea, 96)
        m.merge(fix_orient(cap([poly], zE - 0.6, 'stucco', True), (0, 0, -1)))
    # pavilions.  Middle: a temple front facing the obelisk (radially).  Ends: the whole end face of
    # the arm (all four rows) is a temple front facing along the arc, as in the photos.
    def temple(F, W, depth, piers=4):
        g = Mesh()
        if piers == 4:      # open end face: paired corner piers; the row columns stand between
            for x in (-W / 2 + 1.1, W / 2 - 1.1):
                g.merge(box(x - 1.1, -0.55, 0, x + 1.1, 2.4, COL_H, TRAV))
        else:
            g.merge(box(-W / 2, 0, 0, W / 2, depth, COL_H, TRAV, faces=('-y', '-x', '+x')))
            for x in (-W / 2 + 1.0, W / 2 - 1.0):
                g.merge(box(x - 0.95, -0.55, 0, x + 0.95, 0, COL_H, TRAV))
            g.merge(fix_orient(cap([opening_shape(min(5.6, W * 0.32), 10.0, 'arch', x=-min(5.6, W * 0.32) / 2, y=0)], 0, 'glass', True, frame((0, -0.01, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
        g.merge(entablature(-W / 2 - 0.3, W / 2 + 0.3, COL_H, ENT_H, 1.0, TRAV, y=-0.55))
        rise = W * 0.17
        g.merge(pediment_tri(-W / 2 - 0.5, W / 2 + 0.5, COL_H + ENT_H, rise, depth * 0.5, 1.0, 1.1, TRAV, y=-0.55))
        g.merge(box(-W / 2 - 0.3, -0.55, COL_H + ENT_H, W / 2 + 0.3, depth * 0.6, COL_H + ENT_H + 0.25, TRAV))
        g.merge(box(-1.6, -0.2, COL_H + ENT_H + rise - 0.6, 1.6, 1.4, COL_H + ENT_H + rise + 2.6, TRAV))   # base of the Chigi arms
        return g, COL_H + ENT_H + rise
    up = (0, 0, 1)
    k = NCOL // 2
    a = A0 + k * DA
    ci = arm_xy(rin, a, sgn); co = arm_xy(rout, a, sgn)
    inward = np.array([ci[0] - co[0], ci[1] - co[1], 0.0]); inward /= np.linalg.norm(inward)
    xdir = np.cross(inward, np.array(up))
    F = frame((ci[0], ci[1], z0), -xdir, -inward, up)
    g, _ = temple(F, 10.6, 3.0, 2)
    m.merge(g.transformed(F))
    for k, a in ((0, A0 - ea), (1, A1 + ea)):
        p_in = arm_xy(rin, a, sgn); p_out = arm_xy(rout, a, sgn)
        mid = ((p_in[0] + p_out[0]) / 2, (p_in[1] + p_out[1]) / 2)
        W = math.dist(p_in, p_out)
        # facing: away from the arm along the tangent
        a2 = a + (-0.02 if k == 0 else 0.02)
        q = arm_xy((rin + rout) / 2, a2, sgn)
        out_dir = np.array([q[0] - mid[0], q[1] - mid[1], 0.0]); out_dir /= np.linalg.norm(out_dir)
        xdir = np.cross(np.array(up), out_dir)
        F = frame((mid[0], mid[1], z0), xdir, -out_dir, up)
        g, ztop = temple(F, W, 4.0, 4)
        m.merge(g.transformed(F))
    return m


def statue_spots(sgn):
    """positions + facing (toward the piazza) for statues on the inner balustrade, one per inner column."""
    out = []
    rin = RADII[0] - DIAM[0] / 2 - 0.3
    for k in range(NCOL):
        if k in PAV_K: continue
        a = A0 + k * DA
        x, y = arm_xy(rin + 0.55, a, sgn)
        face = math.atan2(sgn * CY - y + (0 if True else 0), -x)     # look toward the arc centre
        out.append((x, y, Z_COL + COL_H + ENT_H + BAL_H, face))
    return out


# --------------------------------------------------------------------------- obelisk
def obelisk():
    m = Mesh()
    z = 0.0
    m.merge(prism([[(-6.5, -6.5), (6.5, -6.5), (6.5, 6.5), (-6.5, 6.5)]], -1, 0.25, 'granite'))
    m.merge(prism([[(-4.6, -4.6), (4.6, -4.6), (4.6, 4.6), (-4.6, 4.6)]], 0.25, 0.55, 'granite'))
    # pedestal (granite) with base and cornice mouldings
    m.merge(box(-3.2, -3.2, 0.55, 3.2, 3.2, 1.5, 'granite'))
    m.merge(box(-2.7, -2.7, 1.5, 2.7, 2.7, 5.6, 'granite'))
    m.merge(box(-3.0, -3.0, 5.6, 3.0, 3.0, 6.0, 'granite'))
    m.merge(box(-3.3, -3.3, 6.0, 3.3, 3.3, 6.5, 'granite'))
    # four bronze lions (crouching) at the corners carrying the shaft on astragals
    for sx in (-1, 1):
        for sy in (-1, 1):
            body = lathe([(0, 0), (0.55, 0.05), (0.6, 0.4), (0.5, 0.8), (0.3, 1.0), (0, 1.05)], 10, mat='bronze')
            V = np.array(body.V); V[:, 0] *= 1.9; body.V = V.tolist()
            ang = math.atan2(sy, sx)
            m.merge(body.transformed(mat4((sx * 1.9, sy * 1.9, 6.5), rz=ang)))
            m.merge(lathe([(0, 0), (0.45, 0), (0.5, 0.4), (0.35, 0.75), (0, 0.8)], 10, mat='bronze').transformed(mat4((sx * 2.75, sy * 2.75, 6.9))))
    m.merge(box(-1.5, -1.5, 7.3, 1.5, 1.5, 7.6, 'bronze'))
    # shaft: 25.3 m, 2.6 -> 1.7 m, pyramidion
    z0 = 7.6; h = 25.3
    a0, a1 = 1.3, 0.85
    m.merge(prism([[(-a0, -a0), (a0, -a0), (a0, a0), (-a0, a0)]], z0, z0, 'obelisk', top=False))
    sh = Mesh()
    o = sh.add_v([(-a0, -a0, z0), (a0, -a0, z0), (a0, a0, z0), (-a0, a0, z0), (-a1, -a1, z0 + h), (a1, -a1, z0 + h), (a1, a1, z0 + h), (-a1, a1, z0 + h)])
    for q in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)): sh.face([o + i for i in q], 'obelisk')
    tip = sh.add_v([(0, 0, z0 + h + 1.1)])
    for i in range(4): sh.face([o + 4 + i, o + 4 + (i + 1) % 4, tip], 'obelisk')
    m.merge(sh)
    # bronze garland + eagle at the foot of the shaft (as a band)
    m.merge(box(-1.38, -1.38, z0 + 0.2, 1.38, 1.38, z0 + 1.3, 'bronze'))
    # top: Chigi mounts + star + cross
    zt = z0 + h + 1.0
    m.merge(lathe([(0.0, 0), (0.55, 0), (0.6, 0.3), (0.3, 0.5), (0.45, 0.9), (0.15, 1.3), (0, 1.35)], 10, mat='bronze').transformed(mat4((0, 0, zt))))
    for k in range(8):
        a = k * math.pi / 4
        m.merge(box(-0.06, -0.06, 0, 0.06, 0.06, 0.6, 'bronze').transformed(mat4((0, 0, zt + 1.6), rx=0, ry=math.pi / 2 * 0, rz=0) @ mat4((0, 0, 0), ry=a)))
    m.merge(box(-0.08, -0.08, zt + 1.3, 0.08, 0.08, zt + 3.6, 'bronze'))
    m.merge(box(-0.6, -0.07, zt + 2.8, 0.6, 0.07, zt + 3.0, 'bronze'))
    # granite bollards around
    for k in range(16):
        a = k * math.pi / 8
        x, y = 8.2 * math.cos(a), 8.2 * math.sin(a)
        m.merge(lathe([(0.32, 0), (0.32, 0.75), (0.25, 0.95), (0, 1.0)], 8, mat='granite', center=(x, y, 0)))
    return m


# --------------------------------------------------------------------------- fountains
def fountain():
    m = Mesh()
    R0 = 4.6   # basin outer radius (granite)
    m.merge(lathe([(R0 + 0.6, -0.5), (R0 + 0.6, 0.18), (R0 + 0.1, 0.18), (R0 + 0.1, 0.32)], 48, mat='travertine_light', smooth=False))
    m.merge(lathe([(R0, 0.32), (R0 + 0.12, 0.5), (R0 + 0.2, 0.75), (R0 + 0.05, 0.95), (R0 - 0.3, 0.98), (R0 - 0.3, 0.6)], 48, mat='granite'))
    m.merge(lathe([(R0 - 0.3, 0.6), (0, 0.6)], 48, mat='water'))
    # octagonal travertine pedestal with reliefs
    oc = [(1.55 * math.cos(math.pi / 8 + k * math.pi / 4), 1.55 * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]
    m.merge(prism([oc], 0.3, 1.0, TRAV))
    oc2 = [(1.35 * math.cos(math.pi / 8 + k * math.pi / 4), 1.35 * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]
    m.merge(prism([oc2], 1.0, 3.2, TRAV))
    m.merge(prism([oc], 3.2, 3.55, TRAV))
    # lower large bowl (saucer)
    bowl = [(0.7, 3.55), (1.2, 3.75), (2.4, 4.2), (3.3, 4.6), (3.55, 4.95), (3.5, 5.1), (3.2, 5.05), (2.6, 4.85), (0, 4.85)]
    m.merge(lathe(bowl, 48, mat=TRAV))
    m.merge(lathe([(3.15, 5.0), (0, 5.0)], 48, mat='water'))
    # stem with carved balusters
    m.merge(lathe([(0.9, 4.85), (0.75, 5.4), (0.95, 5.9), (0.6, 6.5), (0.7, 6.8), (1.0, 7.0)], 24, mat=TRAV))
    # upper "mushroom": inverted bowl, water sheets spill from its rim
    mush = [(0.9, 7.0), (1.6, 7.05), (2.4, 7.25), (2.75, 7.6), (2.6, 7.95), (1.8, 8.15), (0.6, 8.25), (0, 8.27)]
    m.merge(lathe(mush, 48, mat='granite'))
    # water: veil from the mushroom rim down to the big bowl, and from the bowl rim into the basin
    veil1 = [(2.78, 7.55), (2.9, 7.0), (3.05, 6.2), (3.15, 5.3)]
    veil2 = [(3.56, 4.95), (3.75, 4.3), (3.95, 3.2), (4.05, 1.8), (4.08, 0.6)]
    for v in (veil1, veil2):
        m.merge(lathe(v[::-1], 48, mat='water_fall'))
    return m


# --------------------------------------------------------------------------- paving
def paving():
    """sampietrini ground over the whole square + Piazza Retta with travertine strips."""
    m = Mesh()
    step = 2.0
    # ground grid covering the square (terrain-following)
    x0, x1, y0, y1 = -190, 115, -125, 125
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    g = Mesh()
    o = g.add_v([(x0 + i * step, y0 + j * step, terrain.height(x0 + i * step, y0 + j * step)) for j in range(ny + 1) for i in range(nx + 1)])
    for j in range(ny):
        for i in range(nx):
            a = o + j * (nx + 1) + i
            g.face([a, a + 1, a + nx + 2, a + nx + 1], 'sampietrini', True)
    m.merge(g)
    def strip(p0, p1, w, mat='travertine_light', lift=0.02):
        d = np.array(p1) - np.array(p0); L = np.linalg.norm(d)
        if L < 0.01: return
        d /= L; nrm = np.array([-d[1], d[0]])
        nseg = max(1, int(L / 4))
        for i in range(nseg):
            a = np.array(p0) + d * L * i / nseg; b = np.array(p0) + d * L * (i + 1) / nseg
            q = [a + nrm * w / 2, b + nrm * w / 2, b - nrm * w / 2, a - nrm * w / 2]
            pts = [(p[0], p[1], terrain.height(p[0], p[1]) + lift) for p in q]
            oo = m.add_v(pts); m.face([oo + 3, oo + 2, oo + 1, oo], mat)
    # ring around the obelisk and 16 radial rays toward the colonnade edge
    for k in range(64):
        a0, a1 = 2 * math.pi * k / 64, 2 * math.pi * (k + 1) / 64
        strip((19 * math.cos(a0), 19 * math.sin(a0)), (19 * math.cos(a1), 19 * math.sin(a1)), 0.9)
    def piazza_edge(a):
        """distance from the obelisk to the colonnade steps along direction a (approx)."""
        dx, dy = math.cos(a), math.sin(a)
        sgn = 1 if dy >= 0 else -1
        # solve |p - c| = r_in for p = t*(dx,dy), c = (0, sgn*CY)
        r = RADII[0] - DIAM[0] / 2 - 2.4
        b = -2 * sgn * CY * dy; c = CY * CY - r * r
        t = (-b + math.sqrt(max(0, b * b - 4 * c))) / 2
        return min(t, 120 / max(1e-3, abs(dx)) if abs(dx) > 0.01 else t)
    for k in range(16):
        a = 2 * math.pi * k / 16 + math.pi / 16
        if abs(math.cos(a)) > 0.92 and math.cos(a) < 0: continue     # leave the axis toward the basilica open
        t1 = piazza_edge(a)
        strip((19.5 * math.cos(a), 19.5 * math.sin(a)), (t1 * math.cos(a), t1 * math.sin(a)), 0.7)
    # wind-rose marble roundels on the ring
    for k in range(16):
        a = 2 * math.pi * k / 16
        cx, cy = 19 * math.cos(a), 19 * math.sin(a)
        disk = [(cx + 0.9 * math.cos(t), cy + 0.9 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
        m.merge(cap([disk], terrain.height(cx, cy) + 0.03, 'marble_white', True))
    # rings around the fountains and the colonnade centre disks
    for (fx, fy) in ((0, 60.0), (0, -60.0)):
        for k in range(48):
            a0, a1 = 2 * math.pi * k / 48, 2 * math.pi * (k + 1) / 48
            strip((fx + 7.5 * math.cos(a0), fy + 7.5 * math.sin(a0)), (fx + 7.5 * math.cos(a1), fy + 7.5 * math.sin(a1)), 0.8)
    for sgn in (1, -1):
        cx, cy = 0.0, sgn * CY
        disk = [(cx + 1.0 * math.cos(t), cy + 1.0 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
        m.merge(cap([disk], terrain.height(cx, cy) + 0.03, 'marble_white', True))
    # Piazza Retta: longitudinal strips toward the basilica
    for v in (-30, -15, 0, 15, 30):
        p0 = site.B2W(180, v)[:2]; p1 = site.B2W(250, v)[:2]
        strip(p0, p1, 0.7)
    for u in (180, 200, 220, 240):
        strip(site.B2W(u, -36)[:2], site.B2W(u, 36)[:2], 0.7)
    return m


# --------------------------------------------------------------------------- sagrato (steps) + statues of Peter and Paul
def sagrato():
    """stepped platform in front of the facade, in basilica-local coordinates, transformed to world."""
    m = Mesh()
    F0 = site.FLOOR
    U_FACW = 133.6
    # upper platform (portico level) 16 m deep, 74 m wide; three flights down to the piazza
    top = [(U_FACW, -37.0), (U_FACW + 16.0, -37.0), (U_FACW + 16.0, 37.0), (U_FACW, 37.0)]
    loc = Mesh()
    loc.merge(prism([top], -6, 0, 'travertine_light'))
    # middle landing and flights
    n1 = 12; rise = F0 - 1.2 - 0.0
    def flight(u0, u1, v0, v1, z_top, z_bot, n):
        g = Mesh()
        for i in range(n):
            zt = z_top - (z_top - z_bot) * i / n
            ua = u0 + (u1 - u0) * i / n
            g.merge(box(ua, v0, -6, u1, v1, zt, 'travertine_light', faces=('+z', '+x', '-y', '+y')))
        return g
    # local z here is relative to the floor (0); the piazza at the foot is ~ -(FLOOR - PIAZZA_AT_STEPS)
    zp = site.PIAZZA_AT_STEPS - F0
    loc.merge(flight(U_FACW + 16.0, U_FACW + 22.0, -30.0, 30.0, 0.0, -2.4, 14))
    loc.merge(prism([[(U_FACW + 22.0, -40.0), (U_FACW + 28.0, -40.0), (U_FACW + 28.0, 40.0), (U_FACW + 22.0, 40.0)]], -6, -2.4, 'travertine_light'))
    loc.merge(flight(U_FACW + 28.0, U_FACW + 34.0, -44.0, 44.0, -2.4, zp, 14))
    # pedestals for St Peter (south) and St Paul (north)
    for v in (-38.0, 38.0):
        loc.merge(box(U_FACW + 33.0, v - 2.0, zp, U_FACW + 37.0, v + 2.0, zp + 3.2, TRAV))
    M = site.basilica_matrix()
    m.merge(loc.transformed(M))
    spots = [tuple(site.B2W(U_FACW + 35.0, v, F0 + zp + 3.2)) + (site.AXIS_ANG,) for v in (-38.0, 38.0)]
    return m, spots


# --------------------------------------------------------------------------- the two corridors (bracci)
def braccio(way_pts, statues_out):
    m = Mesh()
    R = ccw(way_pts[:-1] if way_pts[0] == way_pts[-1] else way_pts)
    zb = min(terrain.height(p[0], p[1]) for p in R)
    m.merge(prism([R], zb - 3, zb + 14.5, TRAV, mat_top='roof_flat'))
    n = len(R)
    for i in range(n):
        A, B = R[i], R[(i + 1) % n]
        L = math.dist(A, B)
        if L < 8: continue
        d = np.array([B[0] - A[0], B[1] - A[1], 0]) / L; nrm = np.array([d[1], -d[0], 0])
        F = frame((A[0], A[1], zb), d, -nrm, (0, 0, 1))
        g = Mesh()
        nb = max(1, int(L / 5.2))
        for k in range(nb + 1):
            x = min(max(L * k / nb, 1.0), L - 1.0)
            g.merge(box(x - 0.9, -0.45, 0, x + 0.9, 0, 12.0, TRAV))
        for k in range(nb):
            xc = L * (k + 0.5) / nb
            g.merge(aedicule(xc, 5.0, 1.6, 2.6, TRAV, 'flat'))
        g.merge(straight(architrave_profile(1.0, 0.25), 0, L, 12.0, -0.45, TRAV))
        g.merge(straight(cornice_profile(1.5, 1.0), 0, L, 13.0, -0.45, TRAV))
        g.merge(balustrade(0, L, 14.5, 1.9, 0.8, TRAV, y=0.2, bal_seg=6))
        m.merge(g.transformed(F))
        # statues on the side facing the piazza retta (the side whose normal points toward the axis)
        mid = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2)
        if nrm[1] * mid[1] < 0:
            for k in range(nb + 1):
                x = min(max(L * k / nb, 1.0), L - 1.0)
                p = np.array(A) + d[:2] * x + nrm[:2] * (-0.6)
                statues_out.append((p[0], p[1], zb + 14.5 + 1.9, math.atan2(nrm[1], nrm[0])))
    return m


def build():
    m = Mesh(); statues = []
    for sgn in (1, -1):
        m.merge(colonnade_arm(sgn))
        statues += statue_spots(sgn)
    ob = obelisk(); m.merge(ob)
    for fy in (60.0, -60.0):
        m.merge(fountain().transformed(mat4((0.0, fy, terrain.height(0, fy)))))
    m.merge(paving())
    sg, spots = sagrato(); m.merge(sg)
    for w in SQ['braccio']:
        m.merge(braccio(w, statues))
    return m, statues, spots


if __name__ == '__main__':
    import bpy
    from vb import bl
    out = sys.argv[sys.argv.index('--') + 1]
    bl.clear_scene()
    m, st, spots = build()
    print('square', m.count(), 'statues', len(st))
    # placeholder statues
    proxy = lathe([(0, 0), (0.45, 0), (0.5, 0.3), (0.42, 1.6), (0.3, 2.3), (0.22, 2.5), (0.2, 2.6), (0.17, 2.75), (0.15, 2.95), (0, 3.05)], 10, mat='statue')
    for (x, y, z, a) in st + spots:
        m.merge(proxy.transformed(mat4((x, y, z), rz=a)))
    bl.to_object(m, 'square')
    sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
    import build_basilica_ext as BE
    bl.to_object(BE.build(), 'basilica')
    bl.setup_world()
    views = {'end': ((95, 20, 8), (60, 70, 12), 30), 'sq': ((120, -40, 45), (-120, 10, 10), 28), 'col': ((-10, 40, 3.0), (30, 95, 9), 24), 'top': ((40, -230, 230), (-60, 0, 0), 30),
             'fount': ((12, 50, 2.5), (0, 60, 4), 35)}
    only = [a for a in sys.argv if a.startswith('view=')]
    if only: views = {k: v for k, v in views.items() if k in only[0][5:].split(',')}
    for k, (p, t, lens) in views.items():
        bl.camera(p, t, lens)
        bl.render(out + f'-{k}.jpg', 1400, 800, 32)
