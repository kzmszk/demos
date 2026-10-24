"""Citizens' Plaza (都民広場): paving with its rings and radial lines, the road-deck wall with the portals to No.1's
entrance, stairs up to the deck, sculptures, the rain pool, fallen colonnade columns; the pedestrian bridges to Chuo
Park; the other ground-level structures.
"""
import bpy, math, random
import numpy as np
from mathutils import Vector
import common as C
import uvmap as U
import materials as M
from buildings import PLAZA_C, PLAZA_R, seg

MC = U.MC; DC = U.DC


def wall_x(y, level=38.0, x0=8.0, x1=62.0):
    """x where the road deck drops to the plaza along a row y (first crossing of 'level' going east)"""
    prev = C.ground(x0, y)
    for x in np.arange(x0 + 0.5, x1, 0.5):
        g = C.ground(x, y)
        if prev >= level > g: return x - 0.25
        prev = g
    return None


def deck_wall():
    """polyline of the retaining wall between the road deck and the plaza"""
    pts = []
    for y in np.arange(14.0, 131.0, 3.0):
        x = wall_x(y)
        if x is not None: pts.append(Vector((x, y)))
    # smooth
    sm = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]; b = pts[i]; c = pts[min(i + 1, len(pts) - 1)]
        sm.append((a + b * 2 + c) / 4)
    return sm


def build(col, dec, rng=None):
    R = rng or random.Random(5)
    mats = M.all_mats()
    mb = C.MB()          # MAT atlas, lod both
    det = C.MB()         # MAT atlas, near only (small things)
    # ---------------------------------------------------------------- the wall under the road deck
    wl = deck_wall()
    top = 41.3; par = 1.05
    portals = [(52, 60), (64, 72), (76, 84)]       # y-ranges of the dark portals under the deck (No.1 entrance)
    for i in range(len(wl) - 1):
        a, b = wl[i], wl[i + 1]
        n = Vector((b.y - a.y, -(b.x - a.x))).normalized()      # faces east (toward the plaza)
        if n.x < 0: n = -n
        ga = min(C.ground(a.x + n.x * 1.5, a.y + n.y * 1.5), C.ground(a.x, a.y)) - 0.6
        gb = min(C.ground(b.x + n.x * 1.5, b.y + n.y * 1.5), C.ground(b.x, b.y)) - 0.6
        ym = (a.y + b.y) / 2
        inportal = any(p0 <= ym <= p1 for p0, p1 in portals)
        A = (a.x, a.y); B = (b.x, b.y)
        if inportal:
            ph = min(ga, gb) + 0.6 + 4.6
            mb.quad((A[0], A[1], ph), (B[0], B[1], ph), (B[0], B[1], top), (A[0], A[1], top), 0, MC['granite'])
            # recess into the deck: back wall, ceiling, floor stays ground
            d = -n * 6.0
            mb.quad((A[0] + d.x, A[1] + d.y, ga), (B[0] + d.x, B[1] + d.y, gb), (B[0] + d.x, B[1] + d.y, ph), (A[0] + d.x, A[1] + d.y, ph), 0, MC['interior'])
            mb.quad((A[0], A[1], ph), (A[0] + d.x, A[1] + d.y, ph), (B[0] + d.x, B[1] + d.y, ph), (B[0], B[1], ph), 0, MC['interior'])
        else:
            mb.quad((A[0], A[1], ga), (B[0], B[1], gb), (B[0], B[1], top), (A[0], A[1], top), 0, MC['granite'])
        # parapet
        t = 0.45
        mb.quad((A[0], A[1], top), (B[0], B[1], top), (B[0], B[1], top + par), (A[0], A[1], top + par), 0, MC['granite'])
        mb.quad((B[0] - n.x * t, B[1] - n.y * t, top + par), (B[0], B[1], top + par), (A[0], A[1], top + par), (A[0] - n.x * t, A[1] - n.y * t, top + par), 0, MC['concrete'])
        mb.quad((B[0] - n.x * t, B[1] - n.y * t, top), (B[0] - n.x * t, B[1] - n.y * t, top + par), (A[0] - n.x * t, A[1] - n.y * t, top + par), (A[0] - n.x * t, A[1] - n.y * t, top), 0, MC['granite'])
    # portal side walls
    for p0, p1 in portals:
        for yy, sgn in ((p0, 1), (p1, -1)):
            i = min(range(len(wl)), key=lambda k: abs(wl[k].y - yy))
            a = wl[i]; n = Vector((1, 0))
            g = C.ground(a.x, a.y) - 0.6
            mb.quad((a.x, a.y, g), (a.x - 6, a.y, g), (a.x - 6, a.y, g + 5.2), (a.x, a.y, g + 5.2), 0, MC['granite'])
    # ---------------------------------------------------------------- stairs up to the deck (south end)
    ys = 36.0
    xw = wall_x(ys) or 46.0
    run, w = 11.0, 4.6
    zt = C.ground(xw - 2.5, ys); zb = C.ground(xw + run + 1, ys)
    nst = max(8, int((zt - zb) / 0.17))
    for k in range(nst):
        x0 = xw + run * (1 - (k + 1) / nst); x1 = xw + run * (1 - k / nst)
        z = zb + (zt - zb) * (k + 1) / nst
        mb.box(((x0 + x1) / 2 + 0.0, ys, (z + zb - 0.6) / 2), (x1 - x0 + 0.02, w, z - zb + 0.6), 0, 0, MC['granite'], bottom=False)
    # cheek walls
    for side in (-1, 1):
        yy = ys + side * (w / 2 + 0.2)
        mb.quad((xw + run, yy, zb - 0.5), (xw, yy, zt - 0.5), (xw, yy, zt + 0.9), (xw + run, yy, zb + 0.9), 0, MC['granite'])
    # ---------------------------------------------------------------- sculptures (bronze figures on granite plinths)
    stat = C.MB()
    spots = [(-55, 46), (-30, 44), (-8, 47), (14, 45), (36, 44), (58, 46)]
    fallen = 3
    for i, (ang, r) in enumerate(spots):
        a = math.radians(ang)
        x = PLAZA_C.x + math.cos(a) * r; y = PLAZA_C.y + math.sin(a) * r
        g = C.ground_min(x, y, 1.0)
        mb.box((x, y, g + 0.55), (1.6, 1.6, 1.5), a, 0, MC['granite_dark'], bottom=False)
        fig_up = i != fallen
        figure(stat, Vector((x, y, g + 1.3)), a + math.pi + R.uniform(-0.3, 0.3), R, fallen=not fig_up)
    # ---------------------------------------------------------------- rain pool against the deck wall
    px, py = 52.0, 96.0
    pool = []
    for k in range(28):
        a = 2 * math.pi * k / 28
        rr = 1 + 0.25 * math.sin(a * 3 + 1) + 0.1 * math.sin(a * 7)
        pool.append((px + math.cos(a) * 7.5 * rr, py + math.sin(a) * 11.0 * rr))
    lvl = max(C.ground(x, y) for x, y in pool + [(px, py)]) + 0.03
    px -= 4
    wmb = C.MB()
    wmb.poly([(x, y, lvl) for x, y in pool], 0, 0, uv=[(0, 0)] * len(pool))
    water = wmb.build('water_pool', [M.water()], col)
    water['grp'] = 'water'; water['lod'] = 'both'
    # wet rim + mud around it
    dec.poly([(px + 4 + (x - px - 4) * 1.18, py + (y - py) * 1.12) for x, y in pool], DC['wet'], 0.045)
    dec.poly([(px + 4 + (x - px - 4) * 1.35, py + (y - py) * 1.25) for x, y in pool], DC['mud'], 0.042)
    # ---------------------------------------------------------------- plaza paving with rings and radial lines
    ring = []
    for k in range(0, 37):
        a = math.radians(-90 + 5 * k)
        ring.append((PLAZA_C.x + math.cos(a) * (PLAZA_R + 4.5), PLAZA_C.y + math.sin(a) * (PLAZA_R + 4.5)))
    edge = [(w.x + 0.4, w.y) for w in wl[::-1]]
    poly = [p for p in ring if p[0] > edge[0][0] - 2] + edge
    dec.poly(clip_to_wall(poly, wl), DC['paving'], 0.04)
    for rr in (14.0, 28.0, 42.0, 55.5):
        arc = [(PLAZA_C.x + math.cos(math.radians(a)) * rr, PLAZA_C.y + math.sin(math.radians(a)) * rr) for a in range(-88, 90, 4)]
        arc = [p for p in arc if p[0] > (wall_x(p[1]) or 0) + 0.6]
        if len(arc) > 2: dec.strip(arc, 0.55, DC['band'], 0.05)
    for a in range(-75, 90, 15):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        pts = [(PLAZA_C.x + ca * r, PLAZA_C.y + sa * r) for r in np.arange(6, 55.6, 3.0)]
        pts = [p for p in pts if p[0] > (wall_x(p[1]) or 0) + 0.6]
        if len(pts) > 2: dec.strip(pts, 0.4, DC['band'], 0.05)
    # weeds, moss and leaf litter breaking the pattern: the plaza is a clearing gone wild
    for i in range(70):
        a = math.radians(R.uniform(-85, 85)); r = math.sqrt(R.random()) * 56
        x = PLAZA_C.x + math.cos(a) * r; y = PLAZA_C.y + math.sin(a) * r
        if x < (wall_x(y) or 0) + 1: continue
        kind = R.choice(['grass', 'grass', 'grass', 'moss', 'litter', 'cracks', 'grass', 'leaves'])
        dec.disc(x, y, R.uniform(2.0, 6.5), DC[kind], 10, R, off=0.06, squash=R.uniform(0.5, 1), rot=R.uniform(0, 3))
    # ---------------------------------------------------------------- fallen colonnade columns
    import buildings
    for p, ang, h in buildings.FALLEN:
        d = Vector((math.cos(ang), math.sin(ang), 0))
        base = Vector((p.x, p.y, C.ground(p.x, p.y)))
        L = 0
        for k, ln in enumerate((h * 0.45, h * 0.3, h * 0.22)):
            q = base + d * (L + 0.6 * k + ln / 2)
            gz = C.ground(q.x, q.y)
            det.box((q.x, q.y, gz + 0.55), (ln, 1.2, 1.2), ang + R.uniform(-0.15, 0.15) * k, 0, MC['granite'], bottom=False)
            L += ln
        det.box((base.x, base.y, base.z + 0.6), (1.25, 1.25, 1.2), ang, 0, MC['broken'], bottom=False)
    cover_water(dec, R)
    out = []
    o = mb.build('plaza_mat', [mats['mat']], col); U.cut_and_map(o, U.MAT_CELLS); out.append(o)
    o = det.build('plaza_det', [mats['detail']], col); U.cut_and_map(o, U.MAT_CELLS); o['lod'] = 'near'; out.append(o)
    o = stat.build('plaza_statues', [mats['detail']], col); U.cut_and_map(o, U.MAT_CELLS); o['lod'] = 'near'; out.append(o)
    return out, dict(pool=(px + 4, py, lvl))


def cover_water(dec, R):
    """the land-cover raster marks the old water features along the podium as water (the game paints them as
    standing water on a slope): cover those 4 m cells with dry stone channels gone to moss"""
    im = bpy.data.images.load(C.SRC + 'cover.png')
    w, h = im.size
    px = np.array(im.pixels[:]).reshape(h, w, 4)          # row 0 = bottom = south
    bpy.data.images.remove(im)
    gx0, gy0 = C.GX0, C.GY0
    n = 0
    for j in range(h):
        for i in range(w):
            if px[j, i, 2] < 0.5: continue
            x0 = gx0 + i * 4.0; y0 = gy0 + j * 4.0
            if not (C.BOX[0] - 2 < x0 + 2 < C.BOX[2] + 2 and C.BOX[1] - 2 < y0 + 2 < C.BOX[3] + 2): continue
            e = 0.35
            dec.poly([(x0 - e, y0 - e), (x0 + 4 + e, y0 - e), (x0 + 4 + e, y0 + 4 + e), (x0 - e, y0 + 4 + e)], U.DC['tile'], 0.043)
            if R.random() < 0.7:
                dec.disc(x0 + 2 + R.uniform(-1, 1), y0 + 2 + R.uniform(-1, 1), R.uniform(1.5, 3.2), U.DC[R.choice(['moss', 'grass', 'leaves', 'mud'])], 8, R, off=0.058)
            n += 1
    return n


def clip_to_wall(poly, wl):
    """push polygon points that lie west of the deck wall onto it"""
    out = []
    for x, y in poly:
        xw = wall_x(y)
        if xw is not None and x < xw + 0.4: x = xw + 0.4
        out.append((x, y))
    return out


def figure(mb, base, facing, R, fallen=False):
    """an abstract standing bronze figure (rust-dark), ~2.4 m, or lying fallen beside its plinth"""
    f = Vector((math.cos(facing), math.sin(facing), 0)); s = Vector((-f.y, f.x, 0)); up = Vector((0, 0, 1))
    if fallen:
        up, f = f, -up
        base = base + Vector((0, 0, -0.9)) + up * 0.9 + s * 1.2
    parts = [  # (from, to, width) in (s, f, up) coords
        ((-0.18, 0, 0), (-0.14, 0.05, 1.1), 0.2), ((0.18, 0, 0), (0.15, -0.05, 1.1), 0.2),
        ((0, 0, 1.05), (0, 0.04, 1.85), 0.42), ((0, 0.04, 1.9), (0, 0.06, 2.25), 0.24),
        ((-0.3, 0, 1.8), (-0.42, 0.15, 1.15), 0.13), ((0.3, 0, 1.8), (0.55, 0.3, 2.3), 0.13)]
    for a, b, w in parts:
        pa = base + s * a[0] + f * a[1] + up * a[2]; pb = base + s * b[0] + f * b[1] + up * b[2]
        seg(mb, pa, pb, w, cell=MC['rust'])
