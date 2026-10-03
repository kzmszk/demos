"""St Peter's Basilica — interior (basilica-local frame of build_basilica_ext: u east toward the facade,
v north, z above the floor; origin = dome axis).  Key dimensions: arms 26.5 m wide, cornice 31.5 m,
semicircular vaults to 44.75 m, crossing arch faces at 20.74 m (= drum inner radius), drum 50-72.8 m,
inner dome to the oculus at ~106 m, lantern to 117.5 m.  Interior length ~185 m (entrance wall u=115.5,
west apse end u=-69.25)."""
import math, sys
import numpy as np
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
from vb.geom import *
from vb.arch import *
from vb import site

HW = 13.25            # half width of nave / arms
D = 20.74             # crossing: arch faces and drum inner radius
Z_COR = 31.5          # top of the main cornice
Z_VC = Z_COR + HW     # vault crown 44.75
U_ENT = 115.5         # inner face of the entrance wall
APSE_C = 56.0         # centre of the three apses (u=-56 west, v=+-56 north/south)
Z_RING0, Z_RING1 = 46.8, 50.2    # inscription ring at the base of the drum
Z_DRUM1 = 72.8
Z_OCUL = 106.0; R_OCUL = 6.4
Z_LANT_IN = 117.5
MARBLE = 'marble_int'; STUCCO = 'stucco_white'; GOLD = 'gold'

PIL_W = 2.9; PIL_D = 0.45; Z_PED = 2.8; Z_PIL = 25.8

def nave_bays():
    n = 4; L = U_ENT - D
    return [D + L * (i + 0.5) / n for i in range(n)], L / n

# ------------------------------------------------------------------ helpers
def interior_wall(m, A, B, z0, z1, mat, holes=()):
    """wall face from A to B (2D) facing LEFT of travel (interior on the left)."""
    d = np.array([B[0] - A[0], B[1] - A[1], 0.0]); L = np.linalg.norm(d); d /= L
    n = np.array([-d[1], d[0], 0.0])   # left = into the room
    F = frame((A[0], A[1], z0), d, n * -1 * -1, (0, 0, 1))
    outer = [(0, 0), (L, 0), (L, z1 - z0), (0, z1 - z0)]
    g = cap([outer] + [list(h) for h in holes], 0, mat, True, frame((A[0], A[1], z0), d, (0, 0, 1), -n))
    return fix_orient(g, n)

def barrel(u0, u1, hw, z0, axis, mat, coffers=True):
    """semicircular barrel vault (inner surface, facing down/in) along `axis` ('u' or 'v') between u0..u1,
    centred on the other axis; optional coffer grid geometry (gilded frames + recessed stucco)."""
    m = Mesh(); n = 24
    def P(a, t):        # a along axis, t angle 0..pi across
        c = hw * math.cos(t); z = z0 + hw * math.sin(t)
        return (a, c, z) if axis == 'u' else (c, a, z)
    L = abs(u1 - u0); na = max(4, int(L / 2.5))
    for i in range(na):
        a0 = u0 + (u1 - u0) * i / na; a1 = u0 + (u1 - u0) * (i + 1) / na
        for j in range(n):
            t0, t1 = math.pi * j / n, math.pi * (j + 1) / n
            q = [P(a0, t0), P(a1, t0), P(a1, t1), P(a0, t1)]
            o = m.add_v(q)
            ctr = np.mean(q, axis=0); nrm = np.cross(np.array(q[1]) - q[0], np.array(q[3]) - q[0])
            axis_pt = np.array([ctr[0], 0, z0]) if axis == 'u' else np.array([0, ctr[1], z0])
            f = [o, o + 1, o + 2, o + 3] if np.dot(nrm, axis_pt - ctr) > 0 else [o + 3, o + 2, o + 1, o]
            if coffers:
                # coffer: outer gilded frame ring + recessed field (inset 0.35, depth 0.45) with a rosette
                m.face(f, GOLD if (i + j) % 2 == 0 else 'gold_dull', True)
            else:
                m.face(f, mat, True)
    if coffers:
        # recessed fields as separate inset quads slightly above the frame plane (gives the coffer depth)
        for i in range(na):
            a0 = u0 + (u1 - u0) * (i + 0.18) / na; a1 = u0 + (u1 - u0) * (i + 0.82) / na
            for j in range(1, n - 1):
                t0, t1 = math.pi * (j + 0.18) / n, math.pi * (j + 0.82) / n
                hh = hw + 0.45
                def Q(a, t):
                    c = hh * math.cos(t); z = z0 + hh * math.sin(t)
                    return (a, c, z) if axis == 'u' else (c, a, z)
                q = [Q(a0, t0), Q(a1, t0), Q(a1, t1), Q(a0, t1)]
                o = m.add_v(q); ctr = np.mean(q, axis=0); nrm = np.cross(np.array(q[1]) - q[0], np.array(q[3]) - q[0])
                axis_pt = np.array([ctr[0], 0, z0]) if axis == 'u' else np.array([0, ctr[1], z0])
                m.face([o, o + 1, o + 2, o + 3] if np.dot(nrm, axis_pt - ctr) > 0 else [o + 3, o + 2, o + 1, o], STUCCO, True)
                # coffer side walls (4 small quads) between frame plane and field
                def F0(a, t):
                    c = hw * math.cos(t); z = z0 + hw * math.sin(t)
                    return (a, c, z) if axis == 'u' else (c, a, z)
                ring_in = [F0(a0, t0), F0(a1, t0), F0(a1, t1), F0(a0, t1)]
                for k in range(4):
                    p0, p1 = ring_in[k], ring_in[(k + 1) % 4]; r0, r1 = q[k], q[(k + 1) % 4]
                    oo = m.add_v([p0, p1, r1, r0]); c2 = np.mean([p0, p1, r1, r0], axis=0)
                    nn = np.cross(np.array(p1) - p0, np.array(r0) - p0)
                    m.face([oo, oo + 1, oo + 2, oo + 3] if np.dot(nn, ctr - c2) > 0 else [oo + 3, oo + 2, oo + 1, oo], 'gold_dull')
                # rosette
                cc = Q((a0 + a1) / 2, (t0 + t1) / 2)
                m.merge(lathe([(0, 0), (0.42, 0.0), (0.3, -0.12), (0, -0.2)], 8, mat=GOLD).transformed(
                    frame(cc, (1, 0, 0) if axis == 'u' else (0, 1, 0), *(_tan_norm(cc, axis, z0)))))
    return m

def barrel_tex(u0, u1, hw, z0, axis):
    """semicircular barrel vault with the gilded coffer pattern as a texture (+ transverse gilded ribs)."""
    m = Mesh(); n = 32
    L = abs(u1 - u0); na = max(4, int(L / 2.0))
    arc = math.pi * hw
    for i in range(na):
        a0 = u0 + (u1 - u0) * i / na; a1 = u0 + (u1 - u0) * (i + 1) / na
        for j in range(n):
            t0, t1 = math.pi * j / n, math.pi * (j + 1) / n
            def P(a, t):
                c = hw * math.cos(t); z = z0 + hw * math.sin(t)
                return (a, c, z) if axis == 'u' else (c, a, z)
            q = [P(a0, t0), P(a1, t0), P(a1, t1), P(a0, t1)]
            uv = [((a0 - u0) / 4.0, t0 * hw / 4.0), ((a1 - u0) / 4.0, t0 * hw / 4.0), ((a1 - u0) / 4.0, t1 * hw / 4.0), ((a0 - u0) / 4.0, t1 * hw / 4.0)]
            o = m.add_v(q)
            m.face([o, o + 1, o + 2, o + 3], 'art:sp_vault', True, uv)
    # transverse ribs every ~12 m
    nr = max(1, int(L / 12))
    for k in range(nr + 1):
        a = u0 + (u1 - u0) * k / nr
        path = [((a, hw * 0.995 * math.cos(t), z0 + hw * 0.995 * math.sin(t)) if axis == 'u' else (hw * 0.995 * math.cos(t), a, z0 + hw * 0.995 * math.sin(t))) for t in np.linspace(0, math.pi, 25)]
        ctr = (a, 0, z0) if axis == 'u' else (0, a, z0)
        m.merge(sweep_radial([(-0.7, 0), (-0.7, -0.4), (0.7, -0.4), (0.7, 0)], path, ctr, GOLD))
    return m

def _tan_norm(p, axis, z0):
    if axis == 'u':
        r = np.array([0, p[1], p[2] - z0]); r /= np.linalg.norm(r)
        t = np.cross(np.array([1, 0, 0]), r)
        return tuple(t), tuple(-r * -1)
    r = np.array([p[0], 0, p[2] - z0]); r /= np.linalg.norm(r)
    t = np.cross(np.array([0, 1, 0]), r)
    return tuple(t), tuple(r)

# ------------------------------------------------------------------ elevations
def arm_side(m, A, B, inward, bays, arch_w=13.0, arch_crown=22.5, niches=True):
    """one side of an arm (nave/transept/west arm): pedestal, paired giant fluted pilasters between arches,
    arcade openings to the aisles, statues niches, entablature. A->B along the wall, interior on `inward` side."""
    d = np.array([B[0] - A[0], B[1] - A[1], 0.0]); L = np.linalg.norm(d); d /= L
    n = np.array(inward, float)
    F = frame((A[0], A[1], 0), d, -n, (0, 0, 1))       # arch-kit frame: x along, y into the wall (= away from room)
    g = Mesh()
    holes = []
    for (bc, bw) in bays:            # bc = bay centre distance from A along the wall
        if arch_w > 0:
            holes.append(opening_shape(arch_w, arch_crown, 'arch', x=bc - arch_w / 2, y=0.0))
    wall_face = cap([[(0, 0), (L, 0), (L, Z_COR), (0, Z_COR)]] + holes, 0, MARBLE, True, frame((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)))
    g.merge(fix_orient(wall_face, (0, -1, 0)))
    # arch reveals (thickness 4.5 m) so the aisles show through
    for h in holes:
        Lh = ccw(h); k = len(Lh)
        o = g.add_v([(p[0], 0, p[1]) for p in Lh] + [(p[0], 4.5, p[1]) for p in Lh])
        for i in range(k):
            j = (i + 1) % k
            g.face([o + i, o + k + i, o + k + j, o + j], STUCCO)
        for hb in holes: pass
    # archivolts
    for (bc, bw) in bays:
        if arch_w > 0:
            g.merge(arch_moulding(bc, arch_crown - arch_w / 2, arch_w / 2, 0.9, 0.35, GOLD, y=0.0))
    # piers between bays: paired fluted pilasters on pedestals + two tiers of niches with statues
    pier_xs = [0.0] + [(bays[i][0] + bays[i + 1][0]) / 2 for i in range(len(bays) - 1)] + [L]
    for xp in pier_xs:
        for s in (-1, 1):
            x = xp + s * 2.4
            if x < PIL_W / 2 or x > L - PIL_W / 2: continue
            g.merge(box(x - PIL_W / 2 - 0.25, -PIL_D - 0.3, 0, x + PIL_W / 2 + 0.25, 0, Z_PED, 'marble_dark'))
            g.merge(pilaster(PIL_W, Z_PIL - Z_PED, PIL_D, 'corinthian', 'marble_pil', cap_mat=GOLD, fluted=True).transformed(mat4((x, 0, Z_PED))))
        if niches and 0 < xp < L:
            for (zn, hn) in ((3.6, 6.2), (12.8, 6.2)):
                g.merge(niche(2.3, hn, 0.9, 'marble_dark').transformed(mat4((xp, 0, zn))))
    # entablature + frieze (mosaic inscription band) on the face
    g.merge(straight(architrave_profile(1.9, 0.35), 0, L, Z_PIL, -PIL_D, GOLD))
    g.merge(straight([(0, 0), (0.05, 0), (0.05, 1.9), (0, 1.9)], 0, L, Z_PIL + 1.9, -PIL_D, 'mosaic_blue'))
    g.merge(straight(cornice_profile(1.9, 1.4), 0, L, Z_PIL + 3.8, -PIL_D, GOLD))
    m.merge(g.transformed(F))
    return pier_xs

def nave():
    m = Mesh()
    bays_u, bw = nave_bays()
    # north side: wall at v=+HW from u=D to U_ENT, interior on -v side
    for sgn in (1, -1):
        A = (D, sgn * HW); B = (U_ENT, sgn * HW)
        if sgn < 0: A, B = B, A
        bays = [(abs(bu - A[0]), bw) for bu in bays_u]
        arm_side(m, A, B, (0, -sgn, 0), bays)
    m.merge(barrel_tex(D, U_ENT, HW, Z_COR, 'u'))
    # entrance wall with 3 doors (inner face at u=U_ENT facing -u)
    holes = [opening_shape(5.0, 10.0, 'rect', x=HW - 2.5, y=0), opening_shape(3.4, 7.5, 'rect', x=HW - 2.5 - 9.0, y=0), opening_shape(3.4, 7.5, 'rect', x=HW + 2.5 + 5.6, y=0)]
    F = frame((U_ENT, -HW, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0))
    prof = [(0, 0), (2 * HW, 0)] + [(HW + HW * math.cos(t), Z_COR + HW * math.sin(t)) for t in np.linspace(0, math.pi, 17)][0:] + [(0, Z_COR)]
    prof = [(0, 0), (2 * HW, 0), (2 * HW, Z_COR)] + [(HW + HW * math.cos(t), Z_COR + HW * math.sin(t)) for t in np.linspace(0, math.pi, 17)][1:-1] + [(0, Z_COR)]
    w = cap([prof] + holes, 0, MARBLE, True, F)
    m.merge(fix_orient(w, (-1, 0, 0)))
    for h in holes:   # dark doorways (the portico beyond)
        m.merge(fix_orient(cap([h], 0, 'bronze', True, frame((U_ENT + 0.6, -HW, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0))), (-1, 0, 0)))
    return m

def aisles():
    """side aisles behind the nave arcades: a sequence of domed bays (simplified: box room + oval domes)."""
    m = Mesh()
    bays_u, bw = nave_bays()
    for sgn in (1, -1):
        v0, v1 = sgn * (HW + 4.5), sgn * (HW + 4.5 + 12.5)
        lo, hi = min(v0, v1), max(v0, v1)
        # floor
        m.merge(grid_quad((D, lo, 0), (U_ENT - D, 0, 0), (0, hi - lo, 0), 24, 4, 'art:sp_floor', lambda s, t: (s * (U_ENT - D) / 8, t * (hi - lo) / 8)))
        # outer wall (with altars) faces the aisle
        wall_v = v1
        A, B = ((D, wall_v), (U_ENT, wall_v)) if sgn < 0 else ((U_ENT, wall_v), (D, wall_v))
        g = Mesh()
        g.merge(interior_wall(Mesh(), A, B, 0, 24.0, MARBLE))
        m.merge(g)
        # ceilings: oval domes over each bay + flat arches between
        for bu in bays_u:
            cu = bu; cv = (v0 + v1) / 2
            prof = [(1.0 * math.cos(t), 21.0 + 7.0 * math.sin(t)) for t in np.linspace(0, math.pi / 2, 9)]
            dm = lathe(prof[::-1], 24, mat='art:sp_aisle_dome')
            V = np.array(dm.V); V[:, 0] = V[:, 0] * 9.5 + cu; V[:, 1] = V[:, 1] * 5.8 + cv; dm.V = V.tolist()
            for fi in range(len(dm.F)):
                dm.UV[fi] = [((math.atan2(dm.V[v][1] - cv, dm.V[v][0] - cu) / (2 * math.pi)) % 1.0, (dm.V[v][2] - 21.0) / 7.0) for v in dm.F[fi]]
            dm.F = [f[::-1] for f in dm.F]
            m.merge(dm)
            m.merge(fix_orient(cap([[(cu - bw / 2, lo), (cu + bw / 2, lo), (cu + bw / 2, hi), (cu - bw / 2, hi)], [(cu + 9.5 * math.cos(t), cv + 5.8 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 24, endpoint=False)]], 21.0, STUCCO, True), (0, 0, -1)))
        # end walls of the aisle
        for uu, dirn in ((D, 1), (U_ENT, -1)):
            q = [(uu, lo, 0), (uu, hi, 0), (uu, hi, 21.0), (uu, lo, 21.0)]
            o = m.add_v(q); nrm = np.cross(np.array(q[1]) - q[0], np.array(q[3]) - q[0])
            m.face([o, o + 1, o + 2, o + 3] if nrm[0] * dirn > 0 else [o + 3, o + 2, o + 1, o], MARBLE)
    return m

def arms():
    """west arm and the two transepts: same elevation as the nave, one bay, ending in a semicircular apse."""
    m = Mesh()
    L = APSE_C - D
    for (axis, sgn) in (('u', -1), ('v', 1), ('v', -1)):
        # side walls of the arm
        for side in (1, -1):
            if axis == 'u':
                A = (-D, side * HW); B = (-APSE_C, side * HW)
                if side > 0: A, B = B, A
                inward = (0, -side, 0)
            else:
                A = (side * HW, sgn * D); B = (side * HW, sgn * APSE_C)
                if (side > 0) == (sgn > 0): A, B = B, A
                inward = (-side, 0, 0)
            arm_side(m, A, B, inward, [(L / 2, L)], arch_w=0, niches=True)
        # barrel vault over the arm
        if axis == 'u':
            m.merge(barrel_tex(-APSE_C, -D, HW, Z_COR, 'u'))
        else:
            a0, a1 = sorted((sgn * D, sgn * APSE_C))
            m.merge(barrel_tex(a0, a1, HW, Z_COR, 'v'))
        # apse: semicircular wall (radius HW) + half dome (coffered look via texture)
        ang0 = math.pi / 2 if axis == 'u' else (0 if sgn > 0 else math.pi)
        cu, cv = (-APSE_C, 0) if axis == 'u' else (0, sgn * APSE_C)
        out_dir = math.pi if axis == 'u' else (math.pi / 2 if sgn > 0 else -math.pi / 2)
        a0, a1 = out_dir - math.pi / 2, out_dir + math.pi / 2
        wall = lathe([(HW, 0), (HW, Z_COR)], 16, a0=a0, a1=a1, mat=MARBLE, center=(cu, cv, 0))
        wall.F = [f[::-1] for f in wall.F]
        m.merge(wall)
        hd = lathe([(HW * math.cos(t), Z_COR + HW * math.sin(t)) for t in np.linspace(0, math.pi / 2, 9)], 16, a0=a0, a1=a1, mat='art:sp_apse_dome', center=(cu, cv, 0))
        for fi in range(len(hd.F)):
            hd.UV[fi] = [(((math.atan2(hd.V[v][1] - cv, hd.V[v][0] - cu) - a0) / math.pi) % 1.0, (hd.V[v][2] - Z_COR) / HW) for v in hd.F[fi]]
        hd.F = [f[::-1] for f in hd.F]
        m.merge(hd)
        # pilasters around the apse
        for k in range(1, 6):
            a = a0 + (a1 - a0) * k / 6
            p = (cu + HW * math.cos(a), cv + HW * math.sin(a))
            tdir = (-math.sin(a), math.cos(a), 0); ndir = (-math.cos(a), -math.sin(a), 0)
            Fp = frame((p[0], p[1], 0), tdir, (-ndir[0], -ndir[1], 0), (0, 0, 1))
            g = Mesh()
            g.merge(box(-PIL_W / 2 - 0.25, -PIL_D - 0.3, 0, PIL_W / 2 + 0.25, 0, Z_PED, 'marble_dark'))
            g.merge(pilaster(PIL_W, Z_PIL - Z_PED, PIL_D, 'corinthian', 'marble_pil', cap_mat=GOLD, fluted=True).transformed(mat4((0, 0, Z_PED))))
            m.merge(g.transformed(Fp))
        m.merge(lathe([(HW - 0.45, Z_PIL), (HW - 0.8, Z_PIL + 1.9), (HW - 0.85, Z_PIL + 3.8), (HW - 2.0, Z_COR - 0.4), (HW - 2.0, Z_COR), (HW, Z_COR)], 16, a0=a0, a1=a1, mat=GOLD, center=(cu, cv, 0)))
    return m

# ------------------------------------------------------------------ crossing
def crossing():
    m = Mesh()
    # four chamfer faces (pier faces toward the crossing) with statue niches and relic loggias
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        c, s = math.cos(a), math.sin(a)
        # chamfer runs between (D, HW)-like points rotated into this quadrant
        sx, sy = (1 if c > 0 else -1), (1 if s > 0 else -1)
        A = (sx * D, sy * HW); B = (sx * HW, sy * D)
        if sx * sy < 0: A, B = B, A
        d = np.array([B[0] - A[0], B[1] - A[1], 0.0]); L = np.linalg.norm(d); d /= L
        inward = -np.array([c, s, 0.0])
        F = frame((A[0], A[1], 0), d, -inward, (0, 0, 1))
        g = Mesh()
        holes = [opening_shape(5.2, 10.6, 'arch', x=L / 2 - 2.6, y=1.2), opening_shape(4.2, 7.0, 'arch', x=L / 2 - 2.1, y=17.5)]
        wf = cap([[(0, 0), (L, 0), (L, Z_COR), (0, Z_COR)]] + holes, 0, MARBLE, True, frame((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)))
        g.merge(fix_orient(wf, (0, -1, 0)))
        g.merge(niche(5.2, 10.6, 2.0, 'marble_dark').transformed(mat4((L / 2, 0, 1.2))))
        g.merge(niche(4.2, 7.0, 1.4, 'marble_dark').transformed(mat4((L / 2, 0, 17.5))))
        # loggia balcony + twisted columns
        g.merge(box(L / 2 - 3.4, -1.5, 16.6, L / 2 + 3.4, 0, 17.5, 'marble_white'))
        g.merge(balustrade(L / 2 - 3.2, L / 2 + 3.2, 17.5, 1.1, 0.35, 'marble_white', y=-1.45, bal_seg=6))
        for sxx in (-1, 1):
            g.merge(solomonic(0.45, 6.2, 'marble_white').transformed(mat4((L / 2 + sxx * 2.75, -0.6, 17.5))))
        for xx in (1.5, L - 1.5):
            g.merge(box(xx - PIL_W / 2 - 0.25, -PIL_D - 0.3, 0, xx + PIL_W / 2 + 0.25, 0, Z_PED, 'marble_dark'))
            g.merge(pilaster(PIL_W, Z_PIL - Z_PED, PIL_D, 'corinthian', 'marble_pil', cap_mat=GOLD, fluted=True).transformed(mat4((xx, 0, Z_PED))))
        g.merge(straight(architrave_profile(1.9, 0.35), 0, L, Z_PIL, -PIL_D, GOLD))
        g.merge(straight([(0, 0), (0.05, 0), (0.05, 1.9), (0, 1.9)], 0, L, Z_PIL + 1.9, -PIL_D, 'mosaic_blue'))
        g.merge(straight(cornice_profile(1.9, 1.4), 0, L, Z_PIL + 3.8, -PIL_D, GOLD))
        m.merge(g.transformed(F))
    # pendentives: spherical surface between the four arches from the cornice up to the ring (radius D)
    m.merge(pendentives())
    m.merge(arch_faces())
    # inscription ring + drum + dome + lantern
    m.merge(lathe([(D + 1.6, Z_COR + 13.3), (D + 0.2, Z_RING0), (D, Z_RING0)], 64, mat=GOLD))
    ring = lathe([(D, Z_RING0), (D, Z_RING1)], 96, mat='art:sp_ring')
    for fi in range(len(ring.F)):
        ring.UV[fi] = [((math.atan2(ring.V[v][1], ring.V[v][0]) / (2 * math.pi)) % 1.0, (ring.V[v][2] - Z_RING0) / (Z_RING1 - Z_RING0)) for v in ring.F[fi]]
    ring.F = [f[::-1] for f in ring.F]
    m.merge(seam_fix(ring))
    m.merge(lathe([(D, Z_RING1), (D - 1.6, Z_RING1 + 0.6), (D - 1.6, Z_RING1 + 1.2), (D, Z_RING1 + 1.2)][::-1], 64, mat=GOLD))
    m.merge(drum())
    m.merge(inner_dome())
    return m

def seam_fix(m):
    """lathe faces crossing the u=0/1 seam: unwrap u so the face does not span the whole texture."""
    for fi, uv in enumerate(m.UV):
        if uv is None: continue
        us = [p[0] for p in uv]
        if max(us) - min(us) > 0.5:
            m.UV[fi] = [((p[0] + 1.0) if p[0] < 0.5 else p[0], p[1]) for p in uv]
    return m

def pend_z(x, y):
    R = D * math.sqrt(2) * 0.98
    zc = Z_RING0 - math.sqrt(max(0, R * R - D * D))
    return min(Z_RING0, zc + math.sqrt(max(0.0, R * R - x * x - y * y)))

def arch_faces():
    """wall in each crossing arch plane between the arm's barrel (below) and the pendentive edge (above)."""
    m = Mesh(); n = 40
    for k in range(4):
        a = k * math.pi / 2
        c, s_ = round(math.cos(a)), round(math.sin(a))
        for i in range(n):
            t0, t1 = -HW + 2 * HW * i / n, -HW + 2 * HW * (i + 1) / n
            zb0, zb1 = Z_COR + math.sqrt(max(0, HW * HW - t0 * t0)), Z_COR + math.sqrt(max(0, HW * HW - t1 * t1))
            def P(t, z):
                return (c * D - s_ * t * 1.0 if c else t * 1.0, s_ * D if s_ else 0, z) if False else ((D * c + (-t if s_ else 0) * 0, t, z) if c else (t, D * s_, z))
            zp0 = pend_z(*(P(t0, 0)[:2])); zp1 = pend_z(*(P(t1, 0)[:2]))
            if zp0 <= zb0 + 0.01 and zp1 <= zb1 + 0.01: continue
            q = [P(t0, zb0), P(t1, zb1), P(t1, max(zp1, zb1)), P(t0, max(zp0, zb0))]
            o = m.add_v(q)
            nrm = np.cross(np.array(q[1]) - q[0], np.array(q[3]) - q[0]); ctr = np.mean(q, axis=0)
            m.face([o, o + 1, o + 2, o + 3] if np.dot(nrm, -ctr * np.array([1, 1, 0])) > 0 else [o + 3, o + 2, o + 1, o], STUCCO)
    return m

def pendentives():
    """the spherical surface of radius R = D*sqrt(2) (through the square's corners) clipped by the four arch
    planes |u|<=D, |v|<=D, between the cornice and the ring; faces toward the centre."""
    m = Mesh(); R = D * math.sqrt(2) * 0.98
    zc = Z_RING0 - math.sqrt(max(0, R * R - D * D))   # sphere centre height so that it meets the ring at radius D
    n = 40
    for i in range(n):
        for j in range(n):
            x0, x1 = -D + 2 * D * i / n, -D + 2 * D * (i + 1) / n
            y0, y1 = -D + 2 * D * j / n, -D + 2 * D * (j + 1) / n
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if math.hypot(cx, cy) < D * 0.995: continue      # inside the ring: open to the drum
            def z(x, y):
                rr = R * R - x * x - y * y
                return zc + math.sqrt(max(0.0, rr))
            q = [(x0, y0, z(x0, y0)), (x1, y0, z(x1, y0)), (x1, y1, z(x1, y1)), (x0, y1, z(x0, y1))]
            if min(p[2] for p in q) < Z_COR: q = [(p[0], p[1], max(p[2], Z_COR)) for p in q]
            o = m.add_v(q)
            # roundel UV per quadrant (evangelist medallions), centred on the diagonal
            qx, qy = (1 if cx > 0 else -1), (1 if cy > 0 else -1)
            ang = math.atan2(cy, cx)
            key = 'art:sp_pendentive'
            def uv(p):
                # local coordinates around the medallion centre on the diagonal at radius ~ 0.86*D*sqrt2
                mc = np.array([qx, qy]) * D * 0.80
                rel = np.array(p[:2]) - mc
                t = np.array([-qy, qx]) / math.sqrt(2); r = np.array([qx, qy]) / math.sqrt(2)
                return (0.5 + np.dot(rel, t) / 16.0, 0.5 + np.dot(rel, r) / 16.0)
            m.face([o + 3, o + 2, o + 1, o], key, True, [uv(q[k]) for k in (3, 2, 1, 0)])
    return m

def drum():
    m = Mesh(); NB = 16
    # window openings aligned with the exterior drum windows (centred on angles 2*pi*k/16)
    for k in range(NB):
        a0 = 2 * math.pi * (k - 0.5) / NB; a1 = 2 * math.pi * (k + 0.5) / NB
        A = (D * math.cos(a0), D * math.sin(a0)); B = (D * math.cos(a1), D * math.sin(a1))
        d = np.array([B[0] - A[0], B[1] - A[1], 0.0]); L = np.linalg.norm(d); d /= L
        inward = -np.array([math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2), 0.0])
        F = frame((A[0], A[1], Z_RING1 + 1.2), d, -inward, (0, 0, 1))
        H = Z_DRUM1 - Z_RING1 - 1.2
        g = Mesh()
        win = opening_shape(3.2, 7.4, 'rect', x=L / 2 - 1.6, y=8.5)
        wf = cap([[(0, 0), (L, 0), (L, H), (0, H)], win], 0, 'stucco_white', True, frame((0, 0, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0)))
        g.merge(fix_orient(wf, (0, -1, 0)))
        # reveal through the drum (5.3 m to the exterior wall)
        Lw = ccw(win); kk = len(Lw)
        o = g.add_v([(p[0], 0, p[1]) for p in Lw] + [(p[0], 5.4, p[1]) for p in Lw])
        for i in range(kk):
            j = (i + 1) % kk
            g.face([o + i, o + kk + i, o + kk + j, o + j], 'stucco_white')
        g.merge(aedicule(L / 2, 8.5, 3.2, 7.4, GOLD, 'tri' if k % 2 else 'seg', y=0.0, window=False, frame_w=0.45, proj=0.25))
        # paired pilasters at the segment edges
        for xx in (0.9, L - 0.9):
            g.merge(pilaster(1.3, H - 2.2, 0.3, 'corinthian', 'stucco_white', cap_mat=GOLD).transformed(mat4((xx, 0, 0.6))))
        m.merge(g.transformed(F))
    m.merge(lathe([(D, Z_DRUM1 - 1.6), (D - 0.6, Z_DRUM1 - 1.0), (D - 0.6, Z_DRUM1 - 0.4), (D - 1.4, Z_DRUM1), (D - 1.4, Z_DRUM1 + 0.3), (D, Z_DRUM1 + 0.3)][::-1], 64, mat=GOLD))
    return m

def inner_profile():
    """raised (ogival) inner dome from (D, Z_DRUM1) to the oculus (R_OCUL, Z_OCUL)."""
    pts = []
    for t in np.linspace(0, 1, 20):
        r = D - (D - R_OCUL) * (t ** 1.55)
        z = Z_DRUM1 + 0.3 + (Z_OCUL - Z_DRUM1 - 0.3) * math.sin(t * math.pi / 2) ** 0.8
        pts.append((r, z))
    return pts

def inner_dome():
    m = Mesh()
    prof = inner_profile()
    dm = lathe(prof, 96, mat='art:sp_dome')
    # uv: u = angle, v = arc length along the profile (0 at springing, 1 at the oculus)
    arc = np.concatenate([[0], np.cumsum([math.dist(prof[i], prof[i + 1]) for i in range(len(prof) - 1)])]); arc /= arc[-1]
    def vz(z):
        zs = [p[1] for p in prof]
        return float(np.interp(z, zs, arc))
    for fi in range(len(dm.F)):
        dm.UV[fi] = [((-math.atan2(dm.V[v][1], dm.V[v][0]) / (2 * math.pi) + 0.5 / 16) % 1.0, vz(dm.V[v][2])) for v in dm.F[fi]]   # texture ribs under the gilded ribs
    dm.F = [f[::-1] for f in dm.F]
    m.merge(seam_fix(dm))
    # 16 gilded ribs
    for k in range(16):
        a = 2 * math.pi * (k + 0.5) / 16
        path = [(r * 0.995 * math.cos(a), r * 0.995 * math.sin(a), z) for (r, z) in prof]
        rib = sweep_normal([(-0.55, 0.0), (-0.55, -0.35), (0.55, -0.35), (0.55, 0.0)], path, (0, 0), GOLD)
        m.merge(rib)
    # oculus ring and lantern interior
    oc = lathe([(R_OCUL + 1.2, Z_OCUL - 0.4), (R_OCUL, Z_OCUL), (R_OCUL, Z_OCUL + 1.4)], 64, mat='art:sp_oculus')
    for fi in range(len(oc.F)):
        oc.UV[fi] = [((math.atan2(oc.V[v][1], oc.V[v][0]) / (2 * math.pi)) % 1.0, 0.1 + 0.8 * min(1, (oc.V[v][2] - (Z_OCUL - 0.4)) / 1.8)) for v in oc.F[fi]]
    oc.F = [f[::-1] for f in oc.F]
    m.merge(seam_fix(oc))
    lan = lathe([(R_OCUL, Z_OCUL + 1.4), (R_OCUL, Z_LANT_IN - 4.0)], 32, mat='stucco_white')
    lan.F = [f[::-1] for f in lan.F]
    m.merge(lan)
    cap_ = lathe([(R_OCUL, Z_LANT_IN - 4.0), (R_OCUL * 0.7, Z_LANT_IN - 1.0), (0, Z_LANT_IN)], 32, mat='art:sp_lantern')
    for fi in range(len(cap_.F)):
        cap_.UV[fi] = [(0.5 + cap_.V[v][0] / (2 * R_OCUL), 0.5 + cap_.V[v][1] / (2 * R_OCUL)) for v in cap_.F[fi]]
    cap_.F = [f[::-1] for f in cap_.F]
    m.merge(cap_)
    return m

# ------------------------------------------------------------------ furnishings
def solomonic(r, h, mat, turns=3.5, seg=18, rows=84):
    """twisted (Solomonic) column: straight axis, the shaft section offset and rotating so the silhouette
    undulates (3.5 turns), with a fine spiral fluting on the lower third."""
    m = Mesh()
    m.merge(lathe([(r * 1.35, 0), (r * 1.35, h * 0.025), (r * 1.15, h * 0.04), (r * 1.1, h * 0.06)], seg, mat=mat))
    z0, z1 = h * 0.06, h * 0.9
    rows_idx = []
    for i in range(rows + 1):
        t = i / rows; z = z0 + (z1 - z0) * t
        ph = t * turns * 2 * math.pi
        amp = r * 0.2 * math.sin(math.pi * min(1.0, t * 1.15 + 0.05)) ** 0.5
        cx, cy = amp * math.cos(ph), amp * math.sin(ph)
        rr = r * (1.0 - 0.12 * t)
        row = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            flute = 0.06 * math.sin(6 * a - ph * 2) if t < 0.33 else 0.05 * math.sin(4 * a + ph * 3 + 1.3)
            row.append((cx + rr * (1 + flute) * math.cos(a), cy + rr * (1 + flute) * math.sin(a), z))
        rows_idx.append(m.add_v(row))
    for i in range(rows):
        for k in range(seg):
            k1 = (k + 1) % seg
            m.face([rows_idx[i] + k, rows_idx[i] + k1, rows_idx[i + 1] + k1, rows_idx[i + 1] + k], mat, True)
    m.merge(corinthian_capital(r * 0.88, h * 0.1, mat if mat != 'bronze' else 'gold', 16).transformed(mat4((0, 0, z1))))
    return m

def baldacchino():
    """Bernini's baldachin: four bronze Solomonic columns on marble pedestals, canopy with valance,
    volutes, angels, orb and cross (29 m)."""
    m = Mesh(); s = 5.6   # half distance between the columns (centres)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * s, sy * s
            m.merge(box(x - 1.3, y - 1.3, 0.6, x + 1.3, y + 1.3, 2.9, 'marble_white').transformed(np.eye(4)))
            m.merge(box(x - 1.15, y - 1.15, 2.9, x + 1.15, y + 1.15, 3.3, 'marble_dark'))
            m.merge(solomonic(0.62, 13.8, 'bronze', turns=3.0).transformed(mat4((x, y, 3.3))))
    zc = 3.3 + 13.8
    # entablature blocks over the columns + continuous canopy frame
    m.merge(box(-s - 1.3, -s - 1.3, zc, s + 1.3, s + 1.3, zc + 1.2, 'bronze', faces=('-z', '+x', '-x', '+y', '-y')))
    m.merge(box(-s - 1.6, -s - 1.6, zc + 1.2, s + 1.6, s + 1.6, zc + 2.2, 'bronze'))
    # valance (lambrequins): scalloped bronze panels hanging below the canopy on all four sides
    for k in range(4):
        a = k * math.pi / 2
        for j in range(9):
            t = -s + 2 * s * (j + 0.5) / 9
            cx, cy = (s + 1.35) * math.cos(a) - t * math.sin(a), (s + 1.35) * math.sin(a) + t * math.cos(a)
            m.merge(box(-0.6, -0.04, -0.9, 0.6, 0.04, 0.0, 'gold').transformed(mat4((cx, cy, zc), rz=a + math.pi / 2)))
            m.merge(lathe([(0, 0), (0.12, 0.05), (0.08, 0.3), (0, 0.35)], 6, mat='gold', center=(cx, cy, zc - 1.25)))
    # four corner angels (statue proxies) and the volutes rising to the orb
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.merge(lathe([(0, 0), (0.6, 0), (0.55, 1.2), (0.35, 2.4), (0.2, 2.8), (0, 3.0)], 8, mat='gold', center=(sx * (s + 0.9), sy * (s + 0.9), zc + 2.2)))
            path = []
            for t in np.linspace(0, 0.84, 16):
                rr = (s + 0.6) * (1 - t); zz = zc + 2.2 + 5.0 * (1 - math.cos(t * math.pi / 0.84 * 0.5)) + 0.9 * math.sin(t * math.pi * 2.2)
                path.append((sx * rr, sy * rr, zz))
            m.merge(sweep([(-0.55, -0.45), (0.55, -0.45), (0.55, 0.45), (-0.55, 0.45)], path, 'bronze'))
            m.merge(lathe([(0, 0), (0.55, 0.05), (0.6, 0.6), (0.3, 1.0), (0, 1.05)], 10, mat='gold', center=(sx * (s + 0.6), sy * (s + 0.6), zc + 2.2)))
    m.merge(lathe([(1.5, zc + 7.0), (1.2, zc + 7.6), (0.6, zc + 8.0)], 12, mat='gold'))
    m.merge(lathe([(0.95 * math.sin(t), zc + 8.0 + 0.95 - 0.95 * math.cos(t)) for t in np.linspace(0.05, math.pi, 10)], 16, mat='gold'))
    m.merge(box(-0.12, -0.12, zc + 9.9, 0.12, 0.12, zc + 11.9, 'gold'))
    m.merge(box(-0.75, -0.1, zc + 11.0, 0.75, 0.1, zc + 11.3, 'gold'))
    # papal altar under it, on steps
    m.merge(box(-4.0, -3.0, 0, 4.0, 3.0, 0.3, 'marble_grey'))
    m.merge(box(-3.0, -2.2, 0.3, 3.0, 2.2, 0.6, 'marble_grey'))
    m.merge(box(-1.8, -1.0, 0.6, 1.8, 1.0, 1.65, 'marble_white'))
    # confessio: sunken horseshoe in front (east) with the balustrade and lamps
    cx = 9.5
    ring = [(cx + 3.6 * math.cos(t), 4.6 * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, 13)]
    m.merge(prism([[(cx - 3.0, -4.6)] + ring + [(cx - 3.0, 4.6)]], -2.4, -2.39, 'marble_grey', top=True))
    for t in np.linspace(-math.pi / 2, math.pi / 2, 25):
        x, y = cx + 3.9 * math.cos(t), 4.9 * math.sin(t)
        m.merge(lathe([(0.1, 0), (0.06, 0.5), (0.11, 0.85), (0.04, 0.95)], 6, mat='gold', center=(x, y, 0.9)))
    path = [(cx + 3.9 * math.cos(t), 4.9 * math.sin(t), 0.0) for t in np.linspace(-math.pi / 2, math.pi / 2, 17)]
    m.merge(sweep([(-0.25, 0), (-0.25, 0.9), (0.25, 0.9), (0.25, 0)], path, 'marble_white'))
    return m

def cathedra():
    """Bernini's Cathedra Petri in the west apse: bronze throne carried by four Doctors, the alabaster Gloria
    window with the dove, gilded rays/clouds."""
    m = Mesh(); cu = -APSE_C - HW + 1.2
    # altar + pedestal
    m.merge(box(cu, -4.0, 0, cu + 2.2, 4.0, 1.4, 'marble_dark'))
    m.merge(box(cu - 0.4, -2.8, 1.4, cu + 1.4, 2.8, 4.6, 'marble_grey'))
    # four Doctors (proxies, bronze) and the throne
    for (y, h) in ((-3.6, 5.2), (-1.7, 5.0), (1.7, 5.0), (3.6, 5.2)):
        m.merge(lathe([(0, 0), (0.75, 0), (0.85, 1.0), (0.6, 3.4), (0.4, 4.4), (0.28, 4.9), (0, h)], 10, mat='bronze', center=(cu + 1.6, y, 1.4)))
    m.merge(box(cu + 0.4, -2.3, 7.2, cu + 2.4, 2.3, 8.0, 'bronze'))
    m.merge(box(cu + 0.4, -2.0, 8.0, cu + 1.0, 2.0, 12.6, 'bronze'))
    m.merge(box(cu + 1.0, -2.0, 8.0, cu + 2.0, -1.8, 10.4, 'bronze'))
    m.merge(box(cu + 1.0, 1.8, 8.0, cu + 2.0, 2.0, 10.4, 'bronze'))
    # Gloria: alabaster oval window (glowing), rays, clouds
    zc = 18.5
    win = [(cu + 0.05, 2.0 * math.cos(t), zc + 2.4 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 32, endpoint=False)]
    o = m.add_v(win); m.face(list(range(o, o + 32))[::-1] if True else list(range(o, o + 32)), 'gloria')
    for k in range(40):
        a = 2 * math.pi * k / 40
        r0, r1 = 2.6, 6.5 + 2.0 * (k % 3) / 2
        p0 = (cu + 0.2, r0 * math.cos(a), zc + r0 * 1.1 * math.sin(a)); p1 = (cu + 0.25, r1 * math.cos(a), zc + r1 * 1.05 * math.sin(a))
        w = 0.12 + 0.18 * (k % 2)
        n = np.array([0, -math.sin(a), math.cos(a)])
        q = [np.array(p0) - n * w * 0.5, np.array(p1) - n * w, np.array(p1) + n * w, np.array(p0) + n * w * 0.5]
        oo = m.add_v(q); m.face([oo, oo + 1, oo + 2, oo + 3] if True else [], 'gold')
    for k in range(18):
        a = 2 * math.pi * k / 18
        m.merge(_cloud(cu + 0.6, 4.2 * math.cos(a), zc + 4.6 * math.sin(a), 1.2))
    return m

def _cloud(x, y, z, r):
    m = Mesh()
    for (dx, dy, dz, rr) in ((0, 0, 0, 1.0), (0.2, 0.6, 0.2, 0.7), (0.1, -0.6, -0.2, 0.75)):
        b = lathe([(rr * r * math.sin(t), rr * r * (1 - math.cos(t)) - rr * r) for t in np.linspace(0, math.pi, 7)], 8, mat='gold')
        m.merge(b.transformed(mat4((x + dx * r, y + dy * r, z + dz * r))))
    return m

def floor():
    m = Mesh()
    # nave, crossing, arms (one big polychrome marble floor in the cross shape)
    for (u0, u1, v0, v1) in ((D, U_ENT, -HW, HW), (-D, D, -D, D), (-APSE_C, -D, -HW, HW), (-HW, HW, D, APSE_C), (-HW, HW, -APSE_C, -D)):
        nu = max(2, int((u1 - u0) / 6)); nv = max(2, int((v1 - v0) / 6))
        m.merge(grid_quad((u0, v0, 0), (u1 - u0, 0, 0), (0, v1 - v0, 0), nu, nv, 'art:sp_floor', lambda s, t, a=u0, b=v0, du=u1 - u0, dv=v1 - v0: ((a + s * du) / 8.0, (b + t * dv) / 8.0)))
    # apse floors (half discs)
    for (cu, cv, ang) in ((-APSE_C, 0, math.pi), (0, APSE_C, math.pi / 2), (0, -APSE_C, -math.pi / 2)):
        disc = [(cu + HW * math.cos(ang + t), cv + HW * math.sin(ang + t)) for t in np.linspace(-math.pi / 2, math.pi / 2, 17)]
        g = cap([disc], 0, 'art:sp_floor', True)
        for fi in range(len(g.F)): g.UV[fi] = [(g.V[v][0] / 8.0, g.V[v][1] / 8.0) for v in g.F[fi]]
        m.merge(g)
    return m

def statues():
    from vb import statues as ST
    m = Mesh()
    # crossing niches: Longinus, Helena, Veronica, Andrew (stand-ins from the scan library)
    keys = ['niobid', 'ecclesia', 'polyhymnia', 'baptist']
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        r = (D + HW) / math.sqrt(2) * 1.0 + 0.4
        x, y = r * math.cos(a) * 1.0, r * math.sin(a) * 1.0
        m.merge(ST.place(keys[k], x, y, 1.2 + 0.2, 4.6, a + math.pi / 2, lod=1, mat='statue_marble'))
    # nave pier niches: founder saints (two tiers)
    bays_u, bw = nave_bays()
    pier_us = [D] + [(bays_u[i] + bays_u[i + 1]) / 2 for i in range(len(bays_u) - 1)] + [U_ENT]
    import random
    rnd = random.Random(3)
    for u in pier_us[1:-1]:
        for sgn in (1, -1):
            for zn in (3.6, 12.8):
                key = rnd.choice(ST.SAINTS)
                m.merge(ST.place(key, u, sgn * (HW + 0.35), zn + 0.15, 4.6, (-math.pi / 2 if sgn > 0 else math.pi / 2) + math.pi / 2, lod=1, mat='statue_marble'))
    # the Pietà: first chapel of the north aisle, near the entrance
    pu, pv = U_ENT - 9.0, HW + 4.5 + 10.6
    # chapel of the Pietà: raised altar, curved backdrop of coloured marble with gilded frame, cross above
    m.merge(box(pu - 3.2, pv - 1.6, 0, pu + 3.2, pv + 1.6, 0.35, 'marble_grey'))
    m.merge(box(pu - 2.2, pv - 1.1, 0.35, pu + 2.2, pv + 1.1, 1.3, 'marble_dark'))
    m.merge(box(pu - 1.9, pv - 1.0, 1.3, pu + 1.9, pv + 1.0, 2.35, 'marble_int'))
    wall_v = HW + 4.5 + 12.5 - 0.02
    m.merge(grid_quad((pu + 3.4, wall_v, 0.0), (-6.8, 0, 0), (0, 0, 9.5), 4, 6, 'art:pieta_back', lambda s_, t_: (s_, t_)))
    for sx in (-1, 1):
        m.merge(box(pu + sx * 3.4 - 0.45, wall_v - 0.6, 0, pu + sx * 3.4 + 0.45, wall_v, 9.5, 'marble_dark'))
    m.merge(box(pu - 3.9, wall_v - 0.7, 9.5, pu + 3.9, wall_v, 10.2, GOLD))
    m.merge(box(pu - 2.6, pv - 2.4, 0.35, pu + 2.6, pv - 2.36, 4.6, 'glass_pane'))
    m.merge(ST.place('pieta', pu, pv - 0.1, 2.35, 1.74, 0.0, lod=0, mat='statue_marble'))
    return m

def build_local():
    m = Mesh()
    m.merge(floor())
    m.merge(nave())
    m.merge(aisles())
    m.merge(arms())
    m.merge(crossing())
    m.merge(baldacchino())
    m.merge(cathedra())
    m.merge(statues())
    return m

def world_matrix():
    return site.basilica_matrix()

def viewpoints():
    """points inside the basilica's spaces (local) used to orient faces before baking."""
    P = []
    bays_u, bw = nave_bays()
    for u in np.arange(D + 2, U_ENT - 1, 6.0):
        for z in (1.7, 12, 24, 34, 41):
            P.append((u, 0, z))
            if z < 28:
                for sv in (-1, 1): P.append((u, sv * 7.5, z))
    for u in bays_u:
        for sv in (-1, 1):
            for z in (2, 10, 18, 24): P.append((u, sv * 24.0, z))
    for a in np.arange(-APSE_C - 8, APSE_C + 8.1, 6.0):
        for z in (1.7, 12, 24, 34, 41):
            P.append((a, 0, z)); P.append((0, a, z))
    prof = inner_profile()
    def r_in(z):
        if z <= Z_DRUM1: return D
        if z >= Z_OCUL: return R_OCUL
        zs = [p[1] for p in prof]; rs = [p[0] for p in prof]
        return float(np.interp(z, zs, rs))
    for z in (2, 15, 30, 45, 55, 65, 75, 85, 95, 100, 104, 109, 114):
        for frac in (0.0, 0.45, 0.8):
            r = frac * (r_in(z) - 1.5)
            for k in range(8 if r > 0.5 else 1):
                a = 2 * math.pi * k / 8 + 0.2
                P.append((r * math.cos(a), r * math.sin(a), z))
    for (cu, cv) in ((-APSE_C, 0), (0, APSE_C), (0, -APSE_C)):
        for z in (2, 15, 30, 40): P.append((cu, cv, z))
    return [tuple(apply(world_matrix(), np.array([p]))[0]) for p in P]

def build():
    return build_local().transformed(world_matrix())

if __name__ == '__main__':
    import bpy
    from vb import bl
    out = sys.argv[sys.argv.index('--') + 1]
    bl.clear_scene()
    m = build_local()
    print('interior', m.count(), sorted(set(x for x in m.M if x.startswith('art:'))))
    bl.to_object(m, 'interior')
    bl.setup_world()
    lt = bpy.data.lights.new('fill', 'AREA'); lt.energy = 3e6; lt.size = 60
    lo = bpy.data.objects.new('fill', lt); bpy.context.scene.collection.objects.link(lo); lo.location = (40, 0, 40)
    views = {'nave': ((112, 0, 1.7), (-60, 0, 14), 20), 'cross': ((26, -14, 2), (-10, 6, 40), 16), 'up': ((3, 0, 1.6), (0, 0, 100), 18)}
    only = [a for a in sys.argv if a.startswith('view=')]
    if only: views = {k: v for k, v in views.items() if k in only[0][5:].split(',')}
    for k, (p, t, lens) in views.items():
        bl.camera(p, t, lens); bl.render(out + f'-{k}.jpg', 1400, 800, 32)
