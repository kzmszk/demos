"""三十三間堂 本堂 (蓮華王院本堂, 1266): the 35 x 5 bay hall with its veranda, 向拝, roof and the interior shell.
Built in the hall frame (see sanjusangendo_parts): u north along the axis, v west, z = 0 at the veranda deck."""
import math
import numpy as np
from jk import prim, arch
from . import sanjusangendo_parts as P
from .sanjusangendo_parts import (UL, VL, UO, VO, VI, BAY, NB, H_OUT, H_IN, FLI, VER, UC, WOOD, PLASTER, slab, quad, walk_rect,
                                  block_rect, block_line, arch_beam, kaerumata)

# heights of the wall members above the deck (FL = 0)
Z_SILL = (0.0, 0.32)          # 地長押
Z_KOSHI = (1.78, 1.98)        # 腰長押
Z_UCHI = (3.0, 3.26)          # 内法長押
Z_KASHIRA = (H_OUT - 0.28, H_OUT)   # 頭貫
Z_KETA = (H_OUT + 0.72, H_OUT + 0.94)   # 桁 on the wall line (inside), caps the bracket zone

EAST_OPEN = {1, 4, 7, 10, 13, 21, 24, 27, 30, 33}      # east bays whose plank doors stand open (shoji half open)
PORCH = range(14, 21)                                  # the 7 bays of the 向拝 (lattice doors)
WEST_DOORS = {3, 10, 17, 24, 31}                       # "back: 5 plank doors"
WEST_OPEN = {17}

def build(B, g_rel, gz=None, only=None):
    """g_rel: reference ground height relative to the deck (negative); gz(u, v): local ground height (relative).
    Returns a dict of useful levels."""
    info = {}
    zp = g_rel + 0.35                     # top of the stone base (基壇)
    info['z_base'] = zp
    base(B, g_rel, zp)
    veranda(B, zp)
    end_steps(B, zp, gz or (lambda u, v: g_rel))
    frame_and_walls(B, zp)
    r = roof(B)
    info.update(r)
    porch(B, zp, r, gz or (lambda u, v: g_rel))
    interior(B)
    return info

# ------------------------------------------------------------------ base, under-floor, veranda
def base(B, g, zp):
    ue, ve = UO + VER + 0.9, VO + VER + 0.9
    pts = [(-ue, -ve), (ue, -ve), (ue, ve), (-ue, ve)]
    prim.prism(B, pts, g - 0.5, zp, 'stone', top_mat='stone')
    # dressed edge stones (a slightly proud curb course)
    for (a, b) in zip(pts, pts[1:] + pts[:1]):
        a = np.asarray(a); b = np.asarray(b); d = (b - a) / np.linalg.norm(b - a); n = np.array([d[1], -d[0]])
        prim.obox(B, np.r_[a + n * 0.04, zp - 0.17], np.r_[b + n * 0.04, zp - 0.17], 0.36, 0.34, 'curb', tag='main')
    prim.polygon(B, pts, zp, 'stone', tag='walk')
    # under the floor: the plastered skirt (亀腹 style) between the platform and the floor, inset under the walls
    for (x0, y0, x1, y1) in ((-UO, -VO - 0.15, UO, -VO + 0.15), (-UO, VO - 0.15, UO, VO + 0.15), (-UO - 0.15, -VO, -UO + 0.15, VO), (UO - 0.15, -VO, UO + 0.15, VO)):
        slab(B, x0, y0, x1, y1, zp - 0.05, -0.3, 'temple_wall', c0=(214, 210, 200, 35))
    # the floor: one slab (boards on top), the interior walk surface
    slab(B, -UO, -VO, UO, VO, -0.3, FLI, WOOD)
    walk_rect(B, -UO, -VO, UO, VO, FLI)

def end_steps(B, zp, gz):
    """wooden steps from the gravel up to the end verandas, in front of the east-most bay (entrance north, exit south)"""
    for sgn in (-1, 1):
        u0 = sgn * (UO + VER); u1 = sgn * (UO + VER + 2.4)
        v = -VO + 1.6
        zf = gz(u1, v)
        k = 6
        for i in range(k):
            t0 = i / k; t1 = (i + 1) / k
            ua = u1 + (u0 - u1) * t0; ub = u1 + (u0 - u1) * t1
            zz = zf + (0.0 - zf) * (i + 1) / k
            slab(B, ua, v - 1.2, ub, v + 1.2, zz - 0.06, zz, 'wood_natural', c0=(150, 130, 110, 0))
        for sv in (-1, 1):
            prim.obox(B, (u1, v + sv * 1.25, zf + 0.05), (u0, v + sv * 1.25, 0.05), 0.08, 0.3, WOOD)
        P.quad2(B, (u1, v - 1.2, zf), (u1, v + 1.2, zf), (u0, v + 1.2, 0.0), (u0, v - 1.2, 0.0), 'stone', tag='walk')

def veranda(B, zp):
    """縁 on all four sides: deck boards on posts standing on round stones, an edge beam (縁葛)"""
    a, c, w = UO, VO, VER
    rects = [(-a - w, -c - w, a + w, -c), (-a - w, c, a + w, c + w), (-a - w, -c, -a, c), (a, -c, a + w, c)]
    for (x0, y0, x1, y1) in rects:
        slab(B, x0, y0, x1, y1, -0.1, 0.0, 'wood_natural', c0=(150, 130, 110, 0))
        walk_rect(B, x0, y0, x1, y1, 0.0)
    # edge beams and posts
    for sgn in (-1, 1):
        y = sgn * (c + w - 0.12)
        prim.obox(B, (-a - w + 0.1, y, -0.22), (a + w - 0.1, y, -0.22), 0.2, 0.24, WOOD)
        x = sgn * (a + w - 0.12)
        prim.obox(B, (x, -c - w + 0.1, -0.22), (x, c + w - 0.1, -0.22), 0.2, 0.24, WOOD)
    posts = []
    n = int(round(2 * (a + w) / 1.75))
    for t in np.linspace(-a - w + 0.15, a + w - 0.15, n + 1):
        for sgn in (-1, 1):
            posts.append((t, sgn * (c + w - 0.12))); posts.append((t, sgn * (c + 0.9)))
    m = int(round(2 * c / 1.75))
    for t in np.linspace(-c + 0.6, c - 0.6, m + 1):
        for sgn in (-1, 1):
            posts.append((sgn * (a + w - 0.12), t)); posts.append((sgn * (a + 0.9), t))
    for (x, y) in posts:
        prim.cyl(B, (x, y, zp - 0.05), (x, y, zp + 0.12), 0.2, 0.17, 8, 'stone', tag='detail')
        slab(B, x - 0.08, y - 0.08, x + 0.08, y + 0.08, zp + 0.12, -0.34, WOOD, tag='detail')

# ------------------------------------------------------------------ pillars, wall members, bays
def wall_sides():
    """(p0, p1, out-normal, pillar lines along the side) for the four outer walls, p0->p1 CCW seen from above"""
    return [((-UO, -VO), (UO, -VO), (0, -1), [(u, -VO) for u in UL]),          # east (front)
            ((UO, -VO), (UO, VO), (1, 0), [(UO, v) for v in VL]),               # north end
            ((UO, VO), (-UO, VO), (0, 1), [(u, VO) for u in UL[::-1]]),        # west (back)
            ((-UO, VO), (-UO, -VO), (-1, 0), [(-UO, v) for v in VL[::-1]])]     # south end

def frame_and_walls(B, zp):
    r = 0.25
    # outer pillars (from the base, through the floor)
    pts = set()
    for (_, _, _, pl) in wall_sides():
        for p in pl: pts.add((round(p[0], 3), round(p[1], 3)))
    for (x, y) in sorted(pts):
        arch.pillar(B, x, y, zp, H_OUT, r, WOOD)
    # wall members: continuous beams proud of the pillars on both faces
    for (p0, p1, out, pl) in wall_sides():
        p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); o = np.asarray(out, float)
        d = (p1 - p0) / np.linalg.norm(p1 - p0)
        q0 = p0 - d * 0.35; q1 = p1 + d * 0.35
        members = [(Z_SILL, 0.16), (Z_UCHI, 0.13), (Z_KASHIRA, 0.0)]
        if out[0] != 0 or out[1] > 0: members.append((Z_KOSHI, 0.12))       # 腰長押 on the west and the ends
        for (zz, off) in members:
            zc = (zz[0] + zz[1]) / 2; hh = zz[1] - zz[0]
            if off == 0:
                prim.obox(B, np.r_[q0, zc], np.r_[q1, zc], 0.3, hh, WOOD)
            else:
                for s in (1, -1):
                    prim.obox(B, np.r_[q0 + o * s * (r + off / 2 - 0.04), zc], np.r_[q1 + o * s * (r + off / 2 - 0.04), zc], off, hh, WOOD)
        # 桁 on the wall line (inside the bracket zone) and the plaster band between the brackets
        prim.obox(B, np.r_[q0, sum(Z_KETA) / 2], np.r_[q1, sum(Z_KETA) / 2], 0.3, Z_KETA[1] - Z_KETA[0], WOOD)
        # 釘隠 (nail covers) on the 長押 at each pillar, outside
        for p in pl:
            p = np.asarray(p, float)
            for zz in (Z_SILL, Z_UCHI):
                c = np.r_[p + o * (r + 0.13), (zz[0] + zz[1]) / 2]
                prim.cyl(B, c, c + np.r_[o * 0.05, 0], 0.09, 0.07, 8, 'metal_dark', tag='detail')
        # bays
        for i in range(len(pl) - 1):
            a = np.asarray(pl[i], float); b = np.asarray(pl[i + 1], float)
            side = {(0, -1): 'E', (1, 0): 'N', (0, 1): 'W', (-1, 0): 'S'}[tuple(out)]
            k = i if side == 'E' else (len(pl) - 2 - i if side == 'W' else i)
            bay(B, a, b, o, side, k, len(pl) - 1)
    # brackets on all outer pillars, 間斗束 and plaster between them
    top, reach = arch.bracket_row(B, 2 * UO, 2 * VO, H_OUT, 'demitsudo', 1.2, WOOD, 'white_paint', us=UL, vs=VL)
    for (p0, p1, out, pl) in wall_sides():
        o = np.asarray(out, float)
        for i in range(len(pl) - 1):
            a = np.asarray(pl[i], float); b = np.asarray(pl[i + 1], float)
            d = (b - a) / np.linalg.norm(b - a)
            # white plaster panels (小壁) between 頭貫 and 桁, both faces
            prim.obox(B, np.r_[a + d * 0.27, (H_OUT + Z_KETA[0]) / 2], np.r_[b - d * 0.27, (H_OUT + Z_KETA[0]) / 2], 0.14, Z_KETA[0] - H_OUT, 'temple_wall', c0=PLASTER['c0'])
            m = (a + b) / 2
            prim.obox(B, np.r_[m + o * 0.09, H_OUT], np.r_[m + o * 0.09, Z_KETA[0] - 0.12], 0.16, 0.12, WOOD, up=(d[0], d[1], 0), tag='detail')
            prim.box(B, *(np.r_[m + o * 0.09 - 0.14, Z_KETA[0] - 0.14]), *(np.r_[m + o * 0.09 + 0.14, Z_KETA[0]]), WOOD, tag='detail')
    # closing board under the bracket zone (from the wall plate out to the soffit of the eave)
    for sgn in (-1, 1):
        za, zb = H_OUT + 0.93, H_OUT + 1.25
        P.quad2(B, (-UO - 0.6, sgn * (VO + 0.15), za), (UO + 0.6, sgn * (VO + 0.15), za), (UO + 0.6, sgn * (VO + 0.62), zb), (-UO - 0.6, sgn * (VO + 0.62), zb), WOOD)
        P.quad2(B, (sgn * (UO + 0.15), -VO - 0.6, za), (sgn * (UO + 0.15), VO + 0.6, za), (sgn * (UO + 0.62), VO + 0.6, zb), (sgn * (UO + 0.62), -VO - 0.6, zb), WOOD)
    return top, reach

def bay(B, a, b, o, side, k, n):
    """the infill of one bay between pillar centres a, b on a wall with outward normal o"""
    d = (b - a) / np.linalg.norm(b - a); L = np.linalg.norm(b - a)
    r = 0.25
    qa = a + d * r; qb = b - d * r                       # clear opening between the pillar faces
    zc = lambda z0, z1: (z0 + z1) / 2
    # 小壁 above the 内法長押 (plaster, both faces)
    prim.obox(B, np.r_[qa, zc(Z_UCHI[1], Z_KASHIRA[0])], np.r_[qb, zc(Z_UCHI[1], Z_KASHIRA[0])], 0.14, Z_KASHIRA[0] - Z_UCHI[1], 'temple_wall', c0=PLASTER['c0'])
    walls = []          # blocker segments (open doorways are left out)
    def door_bay(open_, shoji_=True, lattice_=False):
        # 方立 (door posts) and the leaves
        fp = 0.12
        for q in (qa + d * fp / 2, qb - d * fp / 2):
            prim.obox(B, np.r_[q, Z_SILL[1]], np.r_[q, Z_UCHI[0]], 0.14, fp, WOOD, up=(d[0], d[1], 0))
        ca = qa + d * fp; cb = qb - d * fp; w = np.linalg.norm(cb - ca) / 2
        if lattice_:
            P.lattice(B, ca, cb, Z_SILL[1], Z_UCHI[0], cell=0.17)
            if k != 17:      # paper behind the lattice (the central bay is left open: the altar shows through)
                prim.obox(B, np.r_[ca - o * 0.09, (Z_SILL[1] + Z_UCHI[0]) / 2 + 0.2], np.r_[cb - o * 0.09, (Z_SILL[1] + Z_UCHI[0]) / 2 + 0.2], 0.02, Z_UCHI[0] - Z_SILL[1] - 0.6, 'white_paint')
            walls.append((a, b))
            return
        if not open_:
            P.plank_leaf(B, ca, d, o, w, Z_SILL[1] + 0.02, Z_UCHI[0] - 0.02, 0.0)
            P.plank_leaf(B, cb, -d, o, w, Z_SILL[1] + 0.02, Z_UCHI[0] - 0.02, 0.0)
            walls.append((a, b))
            return
        P.plank_leaf(B, ca + o * 0.1, d, o, w, Z_SILL[1] + 0.02, Z_UCHI[0] - 0.02, math.radians(97))
        P.plank_leaf(B, cb + o * 0.1, -d, o, w, Z_SILL[1] + 0.02, Z_UCHI[0] - 0.02, math.radians(97))
        if shoji_:
            # two shoji in the inner groove: one closed (b side), one slid behind it
            m = (ca + cb) / 2
            P.shoji(B, m - o * 0.06, cb - o * 0.06, Z_SILL[1], Z_UCHI[0])
            P.shoji(B, m - o * 0.12 + d * 0.05, cb - o * 0.12 - d * 0.05, Z_SILL[1], Z_UCHI[0])
            walls.append((m, b))
            walls.append((a, ca))
        else:
            walls.append((a, ca)); walls.append((cb, b))
    def window_bay():
        # 腰板 (boards) with a middle post, then the 連子窓 with plaster strips at the sides
        prim.obox(B, np.r_[qa, zc(Z_SILL[1], Z_KOSHI[0])], np.r_[qb, zc(Z_SILL[1], Z_KOSHI[0])], 0.08, Z_KOSHI[0] - Z_SILL[1], WOOD)
        m = (qa + qb) / 2
        prim.obox(B, np.r_[m, Z_SILL[1]], np.r_[m, Z_KOSHI[0]], 0.16, 0.14, WOOD, up=(d[0], d[1], 0))
        for zz in (0.75, 1.25):
            for s in (1, -1):
                prim.obox(B, np.r_[qa + o * s * 0.05, zz], np.r_[qb + o * s * 0.05, zz], 0.03, 0.08, WOOD, tag='detail')
        sw = 0.34
        for (s0, s1) in ((qa, qa + d * sw), (qb - d * sw, qb)):
            prim.obox(B, np.r_[s0, zc(Z_KOSHI[1], Z_UCHI[0])], np.r_[s1, zc(Z_KOSHI[1], Z_UCHI[0])], 0.12, Z_UCHI[0] - Z_KOSHI[1], 'temple_wall', c0=PLASTER['c0'])
        P.renji(B, qa + d * sw, qb - d * sw, Z_KOSHI[1], Z_UCHI[0], th=0.12, step=0.105)
        walls.append((a, b))
    if side == 'E':
        if k in PORCH: door_bay(False, lattice_=True)
        else: door_bay(k in EAST_OPEN)
    elif side == 'W':
        if k in WEST_DOORS: door_bay(k in WEST_OPEN)
        else: window_bay()
    else:
        # ends: the east-most bay is a door (the north one is the visitors' entrance, open, no shoji)
        east_most = (side == 'N' and k == 0) or (side == 'S' and k == n - 1)
        if east_most: door_bay(True, shoji_=(side == 'S'))
        else: window_bay()
    for (p, q) in walls:
        # the strip sits just outside the wall line: the walk map widens blockers by ~0.3 m and a cell, and the
        # visitors' aisle between the wall and the attendants' ledge is only ~2.3 m
        p, q = np.asarray(p, float), np.asarray(q, float); d = q - p; nrm = np.array([-d[1], d[0]]) / max(np.hypot(*d), 1e-9)
        if np.dot(nrm, (p + q) / 2) < 0: nrm = -nrm
        block_line(B, [p + nrm * 0.2, q + nrm * 0.2], 0.0, 0.5)

# ------------------------------------------------------------------ roof
Z_APEX = 11.9           # roof surface at the ridge above FL (PLATEAU 14.2 m to the ridge top from the ground)
ROOF = dict(teri=1.5, sori=0.6, sori_len=0.4, gable_frac=0.5, verge=0.9, rafter=0.3, ridge_h=1.0, ridge_w=0.85, ends='oni')
PORCH_U = 14.0          # half width of the 向拝 roof
PORCH_S = 2.0           # inward depth (from the main eave) where the 向拝 roof leaves the main roof
PORCH_POST_V = -12.0
PORCH_EAVE_V = -14.6

def roof(B):
    reach = 0.66; top = H_OUT + 1.0           # demitsudo s=1.2: 0.714 + purlin 0.288
    Lr, Dr = 2 * UO + 2 * reach, 2 * VO + 2 * reach
    o = 3.7 - reach
    z_eave = top + 0.5
    c = Dr / 2 + o
    pitch = (Z_APEX - z_eave) / (c * (1 - (o / c) ** ROOF['teri']))
    R = P.HallRoof(Lr, Dr, z_eave, o, kind='irimoya', cover='hongawara', rafter_mat=WOOD, rafter_end='white_paint',
                   cut=(-PORCH_U, PORCH_U, PORCH_S), pitch=pitch, **ROOF)
    out = R.build(B)
    out['R'] = R
    gable_ornament(B, R)
    # copper gutters along the east eave (either side of the 向拝)
    zg = R.zE0 - R.edge - 0.08
    for (u0, u1) in ((-R.a + 0.3, -PORCH_U), (PORCH_U, R.a - 0.3)):
        us = np.linspace(u0, u1, max(2, int((u1 - u0) / 1.5)))
        pts = [(u, -R.c - 0.08, float(R.zE(min(abs(u + R.a), abs(R.a - u)))) - R.edge - 0.08) for u in us]
        P.gutter(B, pts)
    for u in (-50.0, -30.0, 30.0, 50.0):
        prim.cyl(B, (u, -R.c - 0.08, zg), (u, -R.c - 0.08, -0.9), 0.045, None, 6, 'copper', tag='detail')
    return out

def gable_ornament(B, R):
    """妻飾り: lattice (木連格子) on the gable and two extra 懸魚 (降り懸魚)"""
    u_g = R.a - R.sg
    for sgn in (-1, 1):
        u = sgn * (u_g + 0.04)
        zb = float(R.z(R.sg, R.sg)) - 0.05
        ztop = lambda v: float(R.z(R.c - abs(v), R.c)) - R.edge - 0.12
        half = R.c - R.sg
        for v in np.arange(-half + 0.45, half - 0.2, 0.45):
            zt = ztop(v)
            if zt > zb + 0.2: prim.obox(B, (u, v, zb), (u, v, zt), 0.05, 0.06, WOOD, up=(0, 1, 0), tag='detail')
        for z in np.arange(zb + 0.45, float(R.z(R.c, R.c)) - 0.8, 0.45):
            # half width at this height
            vs = np.linspace(0, half, 60); zt = np.array([ztop(v) for v in vs]); ok = vs[zt > z]
            if len(ok) == 0: continue
            hw = ok.max()
            prim.obox(B, (u, -hw, z), (u, hw, z), 0.06, 0.05, WOOD, tag='detail')
        # 降り懸魚 on the bargeboards, halfway down each side
        for sv in (-1, 1):
            v = sv * half * 0.55
            z = ztop(v) - 0.25
            gp = [(-0.3, 0.2), (0.3, 0.2), (0.24, -0.25), (0.0, -0.48), (-0.24, -0.25)]
            Pp = np.array([(sgn * (u_g + R.verge + 0.08), v + y, z + zz) for (y, zz) in gp])
            I = [[0, 1, 2], [0, 2, 3], [0, 3, 4]]
            if sgn < 0: I = [t[::-1] for t in I]
            B.add(Pp, I, 'white_paint', tag='detail')
            B.add(Pp + [sgn * 0.03, 0, 0], [t[::-1] for t in I], 'white_paint', tag='detail')

# ------------------------------------------------------------------ 向拝 (7-bay porch, 葺き降ろし)
def porch(B, zp, r, gz):
    R = r['R']
    s_a = PORCH_S
    v_top = -R.c + s_a
    z_top = R.surf_z(s_a)
    k0 = R.slope(s_a)
    z_e = P.lean_to(B, -PORCH_U, PORCH_U, v_top, z_top, PORCH_EAVE_V, k0, rafter_mat=WOOD, soffit_to=-VO - 0.62, z_soffit_top=H_OUT + 1.25)
    # posts (8, square with chamfers), 虹梁 + 蟇股 between them, brackets, purlin, tie beams back to the facade pillars
    us = UL[14:22]
    vp = PORCH_POST_V
    zt = 3.3
    for u in us:
        slab(B, u - 0.2, vp - 0.2, u + 0.2, vp + 0.2, zp + 0.1, zt, WOOD)
        prim.cyl(B, (u, vp, zp - 0.05), (u, vp, zp + 0.12), 0.34, 0.3, 8, 'stone', tag='detail')
        # 海老虹梁 (curved tie beam) to the facade pillar
        pts = [(u, vp + 0.15, zt - 0.35), (u, vp + 1.4, zt - 0.1), (u, vp + 2.6, H_OUT - 0.75), (u, -VO - 0.3, H_OUT - 0.5)]
        prim.sweep(B, np.array(pts), [(-0.1, -0.16), (0.1, -0.16), (0.1, 0.16), (-0.1, 0.16)], WOOD, tag='main', caps=True)
        top_, _ = arch.kumimono(B, u, vp, zt, (0, -1), (1, 0), 'demitsudo', 0.9, WOOD)
    prim.obox(B, (us[0] - 0.5, vp, zt - 0.16), (us[-1] + 0.5, vp, zt - 0.16), 0.24, 0.32, WOOD)            # 頭貫
    for u0, u1 in zip(us[:-1], us[1:]):
        P.arch_beam(B, (u0, vp), (u1, vp), zt - 0.55, 0.26, 0.46, 0.1)                                    # 虹梁
        P.kaerumata(B, (u0 + u1) / 2, vp - 0.02, zt - 0.02, 1.3, 0.52, (1, 0))                            # 蟇股
    zpur = zt + 0.66
    prim.obox(B, (-PORCH_U + 0.3, vp - 0.55, zpur), (PORCH_U - 0.3, vp - 0.55, zpur), 0.24, 0.24, WOOD)    # 丸桁
    # porch deck (extends the veranda), lattice fence in front of the doors, steps
    slab(B, us[0] - 0.6, vp - 0.4, us[-1] + 0.6, -VO - VER, -0.1, 0.0, 'wood_natural', c0=(150, 130, 110, 0))
    walk_rect(B, us[0] - 0.6, vp - 0.4, us[-1] + 0.6, -VO - VER, 0.0)
    for u in np.linspace(us[0] - 0.4, us[-1] + 0.4, 12):
        prim.cyl(B, (u, vp - 0.25, zp - 0.05), (u, vp - 0.25, zp + 0.12), 0.2, 0.17, 8, 'stone', tag='detail')
        slab(B, u - 0.08, vp - 0.33, u + 0.08, vp - 0.17, zp + 0.12, -0.1, WOOD, tag='detail')
    slab(B, us[0] - 0.6, vp - 0.5, us[-1] + 0.6, vp - 0.3, -0.36, -0.1, WOOD)
    # the platform under the porch
    prim.prism(B, [(us[0] - 1.0, -VO - VER - 0.9), (us[0] - 1.0, vp - 0.9), (us[-1] + 1.0, vp - 0.9), (us[-1] + 1.0, -VO - VER - 0.9)][::-1], zp - 0.8, zp, 'stone')
    walk_rect(B, us[0] - 1.0, vp - 0.9, us[-1] + 1.0, -VO - VER - 0.9, zp)
    # wooden barrier (low fence) along the doors of the porch, and at the porch sides
    fence = [(us[0], -VO - 0.75), (us[-1], -VO - 0.75)]
    for u in np.arange(us[0], us[-1] + 0.01, 1.7):
        slab(B, u - 0.06, -VO - 0.81, u + 0.06, -VO - 0.69, 0.0, 0.62, 'wood_natural', tag='detail')
    prim.obox(B, (us[0], -VO - 0.75, 0.62), (us[-1], -VO - 0.75, 0.62), 0.22, 0.07, 'wood_natural')
    prim.obox(B, (us[0], -VO - 0.75, 0.32), (us[-1], -VO - 0.75, 0.32), 0.05, 0.1, 'wood_natural', tag='detail')
    block_line(B, fence, 0.0, 0.6)
    # stone steps (6 risers) from the gravel up to the porch deck
    sw = 6.0
    zf = min(gz(0.0, vp - 3.2), gz(-sw, vp - 3.2), gz(sw, vp - 3.2))
    arch.stairs(B, (0, vp - 3.2), (0, vp - 0.4), zf, 0.0, 2 * sw, 'stone', riser=0.2)
    for sgn in (-1, 1):
        # side cheek stones (袖石)
        pts = [(sgn * (sw + 0.3), vp - 3.3, zf + 0.1), (sgn * (sw + 0.3), vp - 0.4, 0.05)]
        prim.obox(B, pts[0], pts[1], 0.5, 0.3, 'stone')
    # porch roof gutter + downpipes at its corners
    pts = [(u, PORCH_EAVE_V - 0.08, z_e - 0.4) for u in np.linspace(-PORCH_U + 0.2, PORCH_U - 0.2, 12)]
    P.gutter(B, pts)
    for u in (-PORCH_U + 0.4, PORCH_U - 0.4):
        prim.cyl(B, (u, PORCH_EAVE_V - 0.08, z_e - 0.4), (u, PORCH_EAVE_V - 0.08, gz(u, PORCH_EAVE_V)), 0.045, None, 6, 'copper', tag='detail')

# ------------------------------------------------------------------ interior shell
Z_IN_NUKI = (4.25, 4.55)       # inner 内法貫, level of the tie beams
Z_IN_KASHIRA = (5.92, H_IN)    # inner 頭貫
Z_IN_PURLIN = 6.95             # top of the inner purlins (rafters of the 庇 and the 身舎 rest on them)
Z_HISASHI_OUT = H_OUT + 0.93   # 庇 ceiling (boards) at the outer wall line, on the 桁
Z_RIDGE_IN = 9.3               # 化粧屋根裏 at the ridge

def interior(B):
    r = 0.25
    inner = [(u, s * VI) for u in UL[1:-1] for s in (-1, 1)]
    for (x, y) in inner:
        arch.pillar(B, x, y, FLI, H_IN, r, WOOD, base=False)
    # inner members along both inner lines and across the end lines (u = ±UL[1])
    ui = UL[-2]
    rect = [(-ui, -VI), (ui, -VI), (ui, VI), (-ui, VI)]
    for (zz, w) in ((Z_IN_NUKI, 0.2), (Z_IN_KASHIRA, 0.28)):
        for (p0, p1) in zip(rect, rect[1:] + rect[:1]):
            prim.obox(B, (*p0, (zz[0] + zz[1]) / 2), (*p1, (zz[0] + zz[1]) / 2), w, zz[1] - zz[0], WOOD)
    # plaster panels (小壁) between 内法貫 and 頭貫 on the inner lines, with 間斗束
    for sgn in (-1, 1):
        for k in range(1, NB - 1):
            a, b = UL[k], UL[k + 1]
            prim.obox(B, (a + r, sgn * VI, (Z_IN_NUKI[1] + Z_IN_KASHIRA[0]) / 2), (b - r, sgn * VI, (Z_IN_NUKI[1] + Z_IN_KASHIRA[0]) / 2), 0.12,
                      Z_IN_KASHIRA[0] - Z_IN_NUKI[1], 'temple_wall', c0=PLASTER['c0'])
            m = (a + b) / 2
            prim.obox(B, (m, sgn * VI, Z_IN_NUKI[1]), (m, sgn * VI, Z_IN_KASHIRA[0]), 0.18, 0.16, WOOD, up=(1, 0, 0), tag='detail')
    for sgn in (-1, 1):
        for j in range(1, 4):
            a, b = VL[j], VL[j + 1]
            prim.obox(B, (sgn * ui, a + r, (Z_IN_NUKI[1] + Z_IN_KASHIRA[0]) / 2), (sgn * ui, b - r, (Z_IN_NUKI[1] + Z_IN_KASHIRA[0]) / 2), 0.12,
                      Z_IN_KASHIRA[0] - Z_IN_NUKI[1], 'temple_wall', c0=PLASTER['c0'])
    # brackets (平三斗) on the inner pillar tops and the inner purlins
    for (x, y) in inner:
        arch.kumimono(B, x, y, H_IN, (0, -np.sign(y)), (1, 0), 'hira', 1.0, WOOD)
    for (p0, p1) in zip(rect, rect[1:] + rect[:1]):
        prim.obox(B, (*p0, Z_IN_PURLIN - 0.11), (*p1, Z_IN_PURLIN - 0.11), 0.26, 0.22, WOOD)
    # 繋虹梁: tie beams across the 庇 from every outer pillar to the inner line
    for u in UL:
        for sgn in (-1, 1):
            uu = float(np.clip(u, -ui, ui))
            P.arch_beam(B, (u, sgn * (VO - 0.1)), (uu, sgn * (VI + 0.1)), Z_IN_NUKI[0] - 0.05, 0.24, 0.36, 0.1)
    for sgn in (-1, 1):
        for v in VL[1:-1]:
            P.arch_beam(B, (sgn * (UO - 0.1), v), (sgn * (ui + 0.1), v), Z_IN_NUKI[0] - 0.05, 0.24, 0.36, 0.1)
    hisashi_ceiling(B, ui)
    moya_ceiling(B, ui)

def hisashi_ceiling(B, ui):
    """the 庇's exposed sloping rafters (化粧垂木) and boards: a ring of four sloped planes from the outer wall line
    (z = Z_HISASHI_OUT) up to the inner line (z = Z_IN_PURLIN), meeting at the corner diagonals"""
    zo, zi = Z_HISASHI_OUT, Z_IN_PURLIN + 0.12
    O = [(-UO, -VO), (UO, -VO), (UO, VO), (-UO, VO)]
    I = [(-ui, -VI), (ui, -VI), (ui, VI), (-ui, VI)]
    for k in range(4):
        a0, a1 = O[k], O[(k + 1) % 4]; b0, b1 = I[k], I[(k + 1) % 4]
        Pq = np.array([(*a0, zo), (*a1, zo), (*b1, zi), (*b0, zi)])
        B.add(Pq, [[0, 2, 1], [0, 3, 2]], WOOD, tag='main')          # faces down (seen from inside)
        B.add(Pq + [0, 0, 0.04], [[0, 1, 2], [0, 2, 3]], WOOD, tag='main')
        # rafters, perpendicular to the side, cut at the corner diagonals
        a0 = np.array(a0, float); a1 = np.array(a1, float); b0 = np.array(b0, float); b1 = np.array(b1, float)
        d = (a1 - a0) / np.linalg.norm(a1 - a0); nin = np.array([-d[1], d[0]])
        Lside = np.linalg.norm(a1 - a0); depth = abs((b0 - a0) @ nin)
        for t in np.arange(0.25, Lside, 0.45):
            dd = min(t, Lside - t)
            if dd < 0.2: continue
            sd = min(depth, dd)
            p = a0 + d * t
            q0 = np.r_[p + nin * 0.05, zo - 0.06]; q1 = np.r_[p + nin * sd, zo + (zi - zo) * sd / depth - 0.06]
            prim.obox(B, q0, q1, 0.08, 0.1, WOOD, tag='detail')
        # a middle purlin
        m0 = (a0 + b0) / 2; m1 = (a1 + b1) / 2
        prim.obox(B, np.r_[m0, (zo + zi) / 2 - 0.2], np.r_[m1, (zo + zi) / 2 - 0.2], 0.2, 0.2, WOOD, tag='detail')

def moya_ceiling(B, ui):
    """身舎: 二重虹梁 + 蟇股 at every bay line, the exposed gable ceiling (化粧屋根裏) above; the central three bays get a
    raised coffered ceiling (折上組入天井)"""
    zi = Z_IN_PURLIN + 0.12; zr = Z_RIDGE_IN
    slope = (zr - zi) / VI
    zc = lambda v: zi + slope * (VI - abs(v))
    uc = P.UC
    spans = [(-ui, -uc), (uc, ui)]
    # trusses
    for k in range(1, NB):
        u = UL[k]
        if -uc + 0.1 < u < uc - 0.1: continue
        P.arch_beam(B, (u, -VI), (u, VI), 5.95, 0.34, 0.52, 0.16)
        for sv in (-1, 1):
            P.kaerumata(B, u, sv * 2.0, 6.58, 1.25, 0.72, (0, 1))
        P.arch_beam(B, (u, -2.75), (u, 2.75), 7.3, 0.3, 0.42, 0.08)
        P.kaerumata(B, u, 0.0, 7.75, 1.1, zr - 0.38 - 7.75, (0, 1))
    # purlins
    for (u0, u1) in spans:
        for (v, z) in ((0.0, zr - 0.2), (-2.6, zc(2.6) - 0.2), (2.6, zc(2.6) - 0.2)):
            prim.obox(B, (u0, v, z), (u1, v, z), 0.24, 0.24, WOOD)
        # boards (both faces) and rafters
        for sv in (-1, 1):
            Pq = np.array([(u0, sv * VI, zi), (u1, sv * VI, zi), (u1, 0.0, zr), (u0, 0.0, zr)])
            I = [[0, 1, 2], [0, 2, 3]]
            fn = np.cross(Pq[1] - Pq[0], Pq[2] - Pq[0])
            if fn[2] > 0: I = [t[::-1] for t in I]
            B.add(Pq, I, WOOD)
            B.add(Pq + [0, 0, 0.04], [t[::-1] for t in I], WOOD)
            for u in np.arange(u0 + 0.22, u1, 0.45):
                prim.obox(B, (u, sv * (VI - 0.05), zi - 0.06), (u, sv * 0.05, zr - 0.06), 0.08, 0.1, WOOD, tag='detail')
    # gable closures of the exposed ceiling at the ends and at the central section
    for u in (-ui, ui, -uc, uc):
        vs = np.linspace(-VI, VI, 9)
        zb = Z_IN_PURLIN if abs(u) > uc + 0.1 else 8.2
        Pg = np.array([(u, v, zb) for v in vs] + [(u, v, zc(v)) for v in vs[::-1]])
        n = len(vs)
        I = [[i, i + 1, 2 * n - 2 - i] for i in range(n - 1)] + [[i, 2 * n - 2 - i, 2 * n - 1 - i] for i in range(n - 1)]
        B.add(Pg, I, 'temple_wall', c0=PLASTER['c0'])
        B.add(Pg, [t[::-1] for t in I], 'temple_wall', c0=PLASTER['c0'])
    # central coffered ceiling: a cove (折上) from the inner line up to a flat grid
    zf = 8.2; ins = 0.8
    Oc = [(-uc, -VI), (uc, -VI), (uc, VI), (-uc, VI)]
    Ic = [(-uc + ins, -VI + ins), (uc - ins, -VI + ins), (uc - ins, VI - ins), (-uc + ins, VI - ins)]
    for k in range(4):
        a0, a1 = Oc[k], Oc[(k + 1) % 4]; b0, b1 = Ic[k], Ic[(k + 1) % 4]
        rows = []
        for t in np.linspace(0, 1, 6):
            ang = t * math.pi / 2
            f = 1 - math.cos(ang); zz = zi + (zf - zi) * math.sin(ang)
            rows.append([(*(np.array(a0) + (np.array(b0) - np.array(a0)) * f), zz), (*(np.array(a1) + (np.array(b1) - np.array(a1)) * f), zz)])
        Pc = np.array([p for row in rows for p in row]); I = []
        for j in range(5):
            i0 = 2 * j
            I += [[i0, i0 + 3, i0 + 1], [i0, i0 + 2, i0 + 3]]
        B.add(Pc, I, 'black_lacquer', smooth=True)
        B.add(Pc + [0, 0, 0.03], [t[::-1] for t in I], 'black_lacquer', smooth=True)
    x0, y0, x1, y1 = -uc + ins, -VI + ins, uc - ins, VI - ins
    quad(B, (x0, y0, zf), (x0, y1, zf), (x1, y1, zf), (x1, y0, zf), WOOD)
    quad(B, (x0, y0, zf + 0.03), (x1, y0, zf + 0.03), (x1, y1, zf + 0.03), (x0, y1, zf + 0.03), WOOD)
    for x in np.linspace(x0, x1, 15):
        prim.obox(B, (x, y0, zf - 0.06), (x, y1, zf - 0.06), 0.07, 0.1, 'black_lacquer', tag='detail')
    for y in np.linspace(y0, y1, 14):
        prim.obox(B, (x0, y, zf - 0.06), (x1, y, zf - 0.06), 0.07, 0.1, 'black_lacquer', tag='detail')
    # round bosses (釘隠) on the big tie beams either side of the central section (seen above the 中尊)
    for u in (-uc, uc):
        for v in np.linspace(-VI + 0.9, VI - 0.9, 5):
            for su in (-1, 1):
                prim.cyl(B, (u + su * 0.17, v, 6.25), (u + su * 0.24, v, 6.25), 0.12, 0.1, 10, 'metal_dark', tag='detail')
