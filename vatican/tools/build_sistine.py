"""Sistine Chapel — interior with the real frescoes + the brick shell.  Local frame: origin = centre of
the interior floor, x along the axis toward the ENTRANCE (east), y north, z up.  Interior 40.23 x 13.40 m,
20.70 m to the vault crown.  Frescoes are 'art:<key>' materials with explicit UVs."""
import math, sys, json
import numpy as np
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
from vb.geom import *
from vb.arch import *

L, W, H = 40.23, 13.40, 20.70
HL, HW = L / 2, W / 2
NB = 6; BAY = L / NB
Z_SPRING = 15.2          # vault springing at the side walls
Z_PEN = 19.2             # apex of the lunette penetrations
PEN_HW = 2.95            # half width of a penetration at the wall
WALL_T = 3.0
CENTER_W = (-236.7, 77.25); ROT = math.radians(0.8); Z0 = 14.0

def z_main(y):
    t = min(1.0, abs(y) / HW)
    return Z_SPRING + (H - Z_SPRING) * math.sqrt(max(0.0, 1 - t * t))

def bay_x(b):            # centre of bay b (0 = altar end)
    return -HL + BAY * (b + 0.5)

def z_pen(x):
    best = None
    for b in range(NB):
        d = abs(x - bay_x(b))
        if d < PEN_HW:
            z = Z_SPRING + (Z_PEN - Z_SPRING) * math.sqrt(max(0.0, 1 - (d / PEN_HW) ** 2))
            best = z if best is None else min(best, z)
    return best

END_TOP = {'altar': 16.7, 'entrance': 17.0}     # where the end pendentives meet the short walls
END_RUN = 2.6                                      # horizontal run of the end pendentives

def z_end(x):
    da, de = x + HL, HL - x
    za = END_TOP['altar'] + (H - END_TOP['altar']) * min(1.0, da / END_RUN) ** 0.8
    ze = END_TOP['entrance'] + (H - END_TOP['entrance']) * min(1.0, de / END_RUN) ** 0.8
    return min(za, ze)

def ceil_z(x, y):
    z = z_main(y)
    zp = z_pen(x)
    if zp is not None and zp > z: z = zp       # window penetrations rise above the main vault near the walls
    return min(z, max(z_end(x), z_main(y) if abs(y) > HW - 0.01 else 0))   # end pendentives (Jonah / Zechariah)

def arc_len_table(n=400):
    ys = np.linspace(-HW, HW, n + 1)
    zs = np.array([z_main(y) for y in ys])
    s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(ys), np.diff(zs)))])
    return ys, s

YS, SS = arc_len_table()
S_TOT = SS[-1]

def ceil_uv(x, y):
    # image left = entrance (x=+HL), right = altar (x=-HL); top = north wall? (image top edge = one long wall)
    u = (HL - x) / L
    s = np.interp(y, YS, SS) / S_TOT
    return (u, s)

def ceiling():
    m = Mesh(); nx, ny = 160, 64
    xs = np.linspace(-HL, HL, nx + 1); ys = np.linspace(-HW, HW, ny + 1)
    P = [[(x, y, ceil_z(x, y)) for x in xs] for y in ys]
    for j in range(ny):
        for i in range(nx):
            q = [P[j][i], P[j + 1][i], P[j + 1][i + 1], P[j][i + 1]]       # faces point down (into the room)
            uv = [ceil_uv(p[0], p[1]) for p in q]
            o = m.add_v(q)
            cx, cy = (q[0][0] + q[2][0]) / 2, (q[0][1] + q[2][1]) / 2; zt = ceil_z(cx, cy)
            d02 = abs((q[0][2] + q[2][2]) / 2 - zt); d13 = abs((q[1][2] + q[3][2]) / 2 - zt)
            for t in (((0, 1, 2), (0, 2, 3)) if d02 <= d13 else ((0, 1, 3), (1, 2, 3))):
                m.face([o + k for k in t], 'art:sistine_ceiling', True, [uv[k] for k in t])
    return m

def wall_art(sgn, x0, x1, z0, z1, d, key, nu=8, nv=4, uv0=(0, 0), uv1=(1, 1)):
    """art quad on the long wall y = sgn*HW (offset d into the room), facing the room, image upright and
    unmirrored as seen from inside (south wall runs right-to-left in +x)."""
    y = sgn * HW - sgn * d
    if sgn > 0:
        return quad_art((x0, y, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0), key, nu, nv, uv0, uv1)
    return quad_art((x1, y, z0), (x0 - x1, 0, 0), (0, 0, z1 - z0), key, nu, nv, uv0, uv1)

def quad_art(p0, pu, pv, key, nu=8, nv=8, uv0=(0, 0), uv1=(1, 1)):
    """textured grid quad p0 + s*pu + t*pv (s,t in 0..1), uv mapped linearly; faces toward pu x pv."""
    return grid_quad(p0, pu, pv, nu, nv, f'art:{key}', lambda s, t: (uv0[0] + (uv1[0] - uv0[0]) * s, uv0[1] + (uv1[1] - uv0[1]) * t))

# fresco cycles: order from the altar (bay 0) to the entrance (bay 5)
SOUTH = ['moses_journey', 'moses_trials', 'red_sea', 'sinai', 'korah', 'moses_testament']   # Moses cycle
NORTH = ['baptism', 'temptations', 'calling', 'sermon', 'keys', 'last_supper']           # Christ cycle

Z_DRAPE = 5.55; Z_FR0 = 5.85; Z_FR1 = 9.35; Z_CORN = 9.75; Z_WIN0 = 10.6; Z_WIN_SPR = 13.8; WIN_W = 2.5

def side_wall(sgn):
    """long wall on the side y = sgn*HW, inner face toward the centre. Built in a wall frame then placed."""
    m = Mesh()
    # wall frame: x along the chapel (-HL..HL), 'y' into the wall (outward), z up.  Inner face at y=0.
    # we construct points directly in chapel coords:
    yin = sgn * HW
    def P(x, z, d=0.0):     # d = offset toward the room (positive = into the room)
        return (x, yin - sgn * d, z)
    # plain wall face with window holes: build as per-bay pieces
    for b in range(NB):
        x0, x1 = -HL + BAY * b, -HL + BAY * (b + 1); xc = (x0 + x1) / 2
        # wall below the windows (behind frescoes/drapery) — art quads cover it
        seg = Mesh()
        # drapery (painted curtains) 0..Z_DRAPE
        seg.merge(wall_art(sgn, x0, x1, 0, Z_DRAPE, 0.0, 'sistine_drapery', 6, 4, uv0=(0, 0), uv1=(3, 1)))
        seg.merge(wall_art(sgn, x0, x1, Z_DRAPE, Z_FR0, 0.0, 'sistine_band', 4, 1, uv0=(0, 0), uv1=(4, 1)))
        pw = 0.45
        key = (SOUTH if sgn < 0 else NORTH)[b]
        # panels read toward the altar on both walls? they read left->right as seen from inside
        seg.merge(wall_art(sgn, x0 + pw, x1 - pw, Z_FR0, Z_FR1, 0.02, key, 8, 4))
        seg.merge(wall_art(sgn, x0, x0 + pw, Z_FR0, Z_FR1, 0.0, 'sistine_pilaster', 1, 4))
        seg.merge(wall_art(sgn, x1 - pw, x1, Z_FR0, Z_FR1, 0.0, 'sistine_pilaster', 1, 4))
        seg.merge(wall_art(sgn, x0, x1, Z_FR1, Z_CORN, 0.0, 'sistine_band', 4, 1, uv0=(0, 0), uv1=(4, 1)))
        # upper zone: wall with an arched window, painted pope niches either side, up to the lunette
        zt = Z_SPRING
        win = opening_shape(WIN_W, (Z_WIN_SPR - Z_WIN0) + WIN_W / 2, 'arch', x=xc - WIN_W / 2, y=Z_WIN0)
        outer = [(x0, Z_CORN), (x1, Z_CORN), (x1, zt)] + [(x, Z_SPRING) for x in ()] + [(x0, zt)]
        # lunette field above zt, bounded by the penetration curve
        lun = [(xc + PEN_HW * math.cos(a), Z_SPRING + (Z_PEN - Z_SPRING) * math.sin(a)) for a in np.linspace(0, math.pi, 25)]
        upper = [(x0, Z_CORN), (x1, Z_CORN), (x1, Z_SPRING)] + [(xc + PEN_HW, Z_SPRING)] + lun[1:-1] + [(xc - PEN_HW, Z_SPRING), (x0, Z_SPRING)]
        # map 2D (x,z) on the inner wall plane
        F = frame((0, yin, 0), (1, 0, 0), (0, 0, 1), (0, sgn, 0)) if sgn > 0 else frame((0, yin, 0), (1, 0, 0), (0, 0, 1), (0, sgn, 0))
        wl = fix_orient(cap([upper, win], 0, 'art:sistine_upper', True, F), (0, -sgn, 0))
        # uv for the upper wall: x along, z up (tile per bay)
        for fi in range(len(wl.F)):
            wl.UV[fi] = [(((wl.V[v][0] - x0) / BAY) if sgn > 0 else ((x1 - wl.V[v][0]) / BAY), (wl.V[v][2] - Z_CORN) / (Z_PEN - Z_CORN)) for v in wl.F[fi]]
        seg.merge(wl)
        # lunette painting fills the lunette arc (above the window head) – texture per bay
        lk = f'lunette_{"s" if sgn < 0 else "n"}{b}'
        lunpoly = [(xc + PEN_HW * math.cos(a), Z_SPRING + (Z_PEN - Z_SPRING) * math.sin(a)) for a in np.linspace(0, math.pi, 25)]
        win_top = [(xc + WIN_W / 2 * math.cos(a), Z_WIN_SPR + WIN_W / 2 * math.sin(a)) for a in np.linspace(0, math.pi, 13)]
        lp = [(xc + PEN_HW, Z_SPRING)] + lunpoly[1:-1] + [(xc - PEN_HW, Z_SPRING), (xc - WIN_W / 2, Z_SPRING)] + [p for p in win_top[::-1]][::-1][::-1] + [(xc + WIN_W / 2, Z_SPRING)]
        # simpler: lunette field as a half-disc above the window head
        F2 = frame((0, yin - sgn * 0.01, 0), (1, 0, 0), (0, 0, 1), (0, sgn, 0))
        ld = fix_orient(cap([lunpoly], 0, f'art:{lk}', True, F2), (0, -sgn, 0))
        for fi in range(len(ld.F)):
            ld.UV[fi] = [(((ld.V[v][0] - (xc - PEN_HW)) / (2 * PEN_HW)) if sgn > 0 else (((xc + PEN_HW) - ld.V[v][0]) / (2 * PEN_HW)), (ld.V[v][2] - Z_SPRING) / (Z_PEN - Z_SPRING)) for v in ld.F[fi]]
        seg.merge(ld)
        # window reveal (deep, splayed) through the 3 m wall
        rv = Mesh()
        Lw = ccw(win); n = len(Lw)
        oo = rv.add_v([(p[0], yin, p[1]) for p in Lw] + [(xc + (p[0] - xc) * 0.75, yin + sgn * WALL_T, Z_WIN0 + (p[1] - Z_WIN0) * 0.9) for p in Lw])
        for i in range(n):
            j = (i + 1) % n
            rv.face([oo + i, oo + j, oo + n + j, oo + n + i], 'plaster_white')
        seg.merge(fix_orient_inward(rv, (xc, 0, (Z_WIN0 + Z_WIN_SPR) / 2), sgn))
        m.merge(seg)
    # cornice walkway (projecting ledge) with an iron railing
    for x0, x1 in ((-HL, HL),):
        m.merge(box(x0, yin - sgn * 0.9 if sgn > 0 else yin, Z_CORN - 0.35, x1, yin if sgn > 0 else yin - sgn * 0.9, Z_CORN, 'marble_grey') if sgn > 0 else
                box(x0, yin, Z_CORN - 0.35, x1, yin + 0.9, Z_CORN, 'marble_grey'))
        yr = yin - sgn * 0.85
        for k in range(int(L / 1.2) + 1):
            x = -HL + k * L / int(L / 1.2)
            m.merge(box(x - 0.02, yr - 0.02, Z_CORN, x + 0.02, yr + 0.02, Z_CORN + 1.0, 'iron'))
        m.merge(box(-HL, yr - 0.025, Z_CORN + 0.97, HL, yr + 0.025, Z_CORN + 1.02, 'iron'))
    return m

def fix_orient_inward(mesh, centre, sgn):
    V = np.array(mesh.V)
    for i, f in enumerate(mesh.F):
        a, b, c = V[f[0]], V[f[1]], V[f[2]]
        n = np.cross(b - a, c - a); ctr = V[f].mean(0)
        if np.dot(n, np.array(centre) - ctr) < 0: mesh.F[i] = f[::-1]
    return mesh

def end_top(xw, y):
    return min(z_main(y), END_TOP['altar' if xw < 0 else 'entrance'])

def end_wall(xw, key, z0=0.0):
    """short wall at x = xw (altar: -HL, entrance: +HL), inner face toward the room; art rectangle and plain wall
    clipped to the vault arch."""
    m = Mesh(); sx = 1 if xw < 0 else -1      # direction into the room
    ny, nz = 40, 60
    ys = np.linspace(-HW, HW, ny + 1); zs = np.linspace(0, H, nz + 1)
    for j in range(nz):
        for i in range(ny):
            ya, yb = ys[i], ys[i + 1]; za, zb = zs[j], zs[j + 1]
            if za >= max(end_top(xw, ya), end_top(xw, yb)) - 1e-6: continue
            q = [(xw, ya, za), (xw, yb, za), (xw, yb, zb), (xw, ya, zb)]
            q = [(p[0], p[1], min(p[2], end_top(xw, p[1]))) for p in q]
            # uv: the fresco covers y in [-6.1, 6.1], z in [z0, z0+13.7] on the altar wall
            def uv(p):
                return ((p[1] + 6.1) / 12.2 if sx > 0 else (6.1 - p[1]) / 12.2, (p[2] - z0) / 13.7)
            o = m.add_v(q)
            f = [o, o + 1, o + 2, o + 3] if sx > 0 else [o + 3, o + 2, o + 1, o]
            zc = (za + zb) / 2
            yc = (ya + yb) / 2
            if key == 'last_judgment' and (zc < z0 or zc > z0 + 13.7 or abs(yc) > 6.1):
                mk = 'art:sistine_upper' if zc > z0 else 'marble_grey'
                m.face(f, mk, False, [((q[k - o][1] + HW) / BAY, (q[k - o][2]) / 6.0) for k in f])
            elif key == 'sistine_entrance':
                m.face(f, f'art:{key}', False, [((HW - q[k - o][1]) / W, q[k - o][2] / H) for k in f])
            else:
                m.face(f, f'art:{key}', False, [uv(q[k - o]) for k in f])
    return m

def floor_and_furnishings():
    m = Mesh()
    # cosmatesque floor (UV in metres / 4)
    g = grid_quad((-HL, -HW, 0), (L, 0, 0), (0, W, 0), 40, 14, 'art:sistine_floor', lambda s, t: (s * L / 6.7, t * W / 6.7))
    m.merge(g)
    # transenna (marble screen) ~ 14.5 m from the entrance wall
    xt = HL - 14.4
    for y0, y1 in ((-HW, -1.1), (1.1, HW)):
        m.merge(box(xt - 0.18, y0, 0, xt + 0.18, y1, 1.35, 'marble_white'))
        n = int((y1 - y0) / 1.2)
        for k in range(n + 1):
            y = y0 + (y1 - y0) * k / n
            m.merge(box(xt - 0.14, y - 0.12, 1.35, xt + 0.14, y + 0.12, 3.25, 'marble_white'))
        m.merge(box(xt - 0.2, y0, 3.25, xt + 0.2, y1, 3.5, 'marble_white'))
    # seven candelabra on top
    for k in range(7):
        y = -HW + 0.9 + (W - 1.8) * k / 6
        if abs(y) < 1.2: continue
        m.merge(lathe([(0.16, 0), (0.07, 0.2), (0.1, 0.45), (0.045, 0.8), (0.12, 1.0), (0.17, 1.08), (0.02, 1.12)], 10, mat='marble_grey', center=(xt, y, 3.5)))
    # altar platform + altar
    m.merge(box(-HL, -HW, 0, -HL + 5.5, HW, 0.5, 'marble_grey'))
    m.merge(box(-HL + 5.5, -3.5, 0, -HL + 6.3, 3.5, 0.25, 'marble_grey'))
    m.merge(box(-HL + 0.8, -1.6, 0.5, -HL + 1.8, 1.6, 1.5, 'marble_white'))
    # cantoria (singers' gallery) on the north wall
    xc = bay_x(3) + 0.6
    m.merge(box(xc - 2.4, HW - 1.3, 4.2, xc + 2.4, HW, 4.5, 'marble_white'))
    m.merge(balustrade(xc - 2.4, xc + 2.4, 4.5, 1.1, 0.25, 'marble_white', y=HW - 1.3, bal_seg=6))
    # benches along the side walls
    for sgn in (-1, 1):
        m.merge(box(-HL + 6, sgn * HW - (0.6 if sgn > 0 else -0.6), 0, HL - 0.5, sgn * HW, 0.45, 'wood') if sgn > 0 else
                box(-HL + 6, -HW, 0, HL - 0.5, -HW + 0.6, 0.45, 'wood'))
    return m

def shell():
    """brick exterior shell (walls 3 m, closed) around the interior, low gabled roof."""
    m = Mesh()
    ox, oy = HL + WALL_T, HW + WALL_T + 0.8
    zb = -14.0; zt = H + 3.0
    # outer faces (with window holes on the long sides)
    for sgn in (-1, 1):
        y = sgn * oy
        holes = []
        for b in range(NB):
            xc = bay_x(b)
            holes.append([(xc + (p[0]) * 0.75, p[1]) for p in []])
        F = frame((-ox, y, zb), (1, 0, 0), (0, 0, 1), (0, sgn, 0))
        ws = [opening_shape(WIN_W * 0.75, (Z_WIN_SPR - Z_WIN0) * 0.9 + WIN_W * 0.375, 'arch', x=(bay_x(b) + ox) - WIN_W * 0.375, y=Z_WIN0 - zb) for b in range(NB)]
        wo = fix_orient(cap([[(0, 0), (2 * ox, 0), (2 * ox, zt - zb), (0, zt - zb)]] + ws, 0, 'brick', True, F), (0, sgn, 0))
        m.merge(wo)
        # window glass recessed (dark) is omitted: the reveal is open so light reaches the bake
    for sx in (-1, 1):
        F = frame((sx * ox, -oy, zb), (0, 1, 0), (0, 0, 1), (sx, 0, 0))
        m.merge(fix_orient(cap([[(0, 0), (2 * oy, 0), (2 * oy, zt - zb), (0, zt - zb)]], 0, 'brick', True, F), (sx, 0, 0)))
    # roof slab over the vault + tiled gable roof
    m.merge(box(-ox, -oy, zt - 0.6, ox, oy, zt, 'brick', faces=('+z',)))
    ridge = zt + 3.4
    for sgn in (-1, 1):
        q = [(-ox - 0.5, sgn * (oy + 0.6), zt), (ox + 0.5, sgn * (oy + 0.6), zt), (ox + 0.5, 0, ridge), (-ox - 0.5, 0, ridge)]
        o = m.add_v(q); m.face([o, o + 1, o + 2, o + 3] if sgn < 0 else [o + 3, o + 2, o + 1, o], 'roof_tile')
    for sx in (-1, 1):
        tri = [(sx * (ox + 0.5), -oy - 0.6, zt), (sx * (ox + 0.5), oy + 0.6, zt), (sx * (ox + 0.5), 0, ridge)]
        o = m.add_v(tri); m.face([o, o + 1, o + 2] if sx > 0 else [o + 2, o + 1, o], 'brick')
    # crenellated cornice band (the chapel's fortress-like top)
    for sgn in (-1, 1):
        for k in range(int(2 * ox / 2.4)):
            x = -ox + 1.2 + k * 2.4
            m.merge(box(x - 0.6, sgn * oy - 0.35, zt - 1.6, x + 0.6, sgn * oy + 0.25, zt - 0.2, 'brick'))
    # inner closure of the wall thickness between interior faces and the exterior (top of walls)
    m.merge(box(-ox, -oy, H, ox, -HW, H + 0.3, 'brick', faces=('+z', '-z')))
    m.merge(box(-ox, HW, H, ox, oy, H + 0.3, 'brick', faces=('+z', '-z')))
    # vault extrados cover (so no light leaks in from above)
    m.merge(box(-HL, -HW, H + 0.25, HL, HW, H + 0.3, 'brick', faces=('-z', '+z')))
    return m

def build_local():
    m = Mesh()
    m.merge(ceiling())
    for sgn in (-1, 1): m.merge(side_wall(sgn))
    m.merge(end_wall(-HL, 'last_judgment', z0=3.3))
    m.merge(end_wall(HL, 'sistine_entrance', z0=0.0))
    m.merge(floor_and_furnishings())
    m.merge(shell())
    return m

def world_matrix():
    return mat4((CENTER_W[0], CENTER_W[1], Z0), rz=ROT)

def build_parts():
    """(interior, shell) meshes in world coordinates."""
    inner = Mesh()
    inner.merge(ceiling())
    for sgn in (-1, 1): inner.merge(side_wall(sgn))
    inner.merge(end_wall(-HL, 'last_judgment', z0=3.3))
    inner.merge(end_wall(HL, 'sistine_entrance', z0=0.0))
    inner.merge(floor_and_furnishings())
    M = world_matrix()
    return inner.transformed(M), shell().transformed(M)

def led_lights():
    """LED strips on the cornice ledges lighting the vault (world-space area lights for the bake)."""
    out = []
    M = world_matrix()
    for sgn in (-1, 1):
        for kind, rot, z, e in (('up', 0.0, Z_CORN + 0.15, 1700.0), ('down', math.pi, Z_CORN - 0.4, 650.0)):
            p = apply(M, np.array([[0, sgn * (HW - 0.55), z]]))[0]
            out.append(dict(loc=tuple(p), size=(L - 1.0, 0.35), rot=(rot + (-0.35 * sgn if kind == 'up' else 0.25 * sgn), 0, ROT), energy=e))
    return out

def viewpoints():
    P = []
    for x in np.arange(-HL + 1.5, HL - 1.0, 3.0):
        for y in (-4.5, 0, 4.5):
            for z in (1.7, 7, 12, 15.5, 17.5, 19.5):
                if z < ceil_z(x, y) - 0.5: P.append((x, y, z))
    return [tuple(apply(world_matrix(), np.array([p]))[0]) for p in P]

def build():
    a, b = build_parts(); a.merge(b); return a

if __name__ == '__main__':
    import bpy
    from vb import bl
    out = sys.argv[sys.argv.index('--') + 1]
    bl.clear_scene()
    m = build_local()
    print('sistine', m.count(), 'arts', sorted(set(x for x in m.M if x.startswith('art:'))))
    bl.to_object(m, 'sistine')
    bl.setup_world()
    lt = bpy.data.lights.new('fill', 'AREA'); lt.energy = 60000; lt.size = 30
    lo = bpy.data.objects.new('fill', lt); bpy.context.scene.collection.objects.link(lo); lo.location = (0, 0, 9.5); lo.rotation_euler = (0, 0, 0)
    for k, (p, t, lens) in {'in': ((18.5, 0, 7.5), (-20, 0, 10), 18), 'up': ((0, -2, 1.7), (0, 0.5, 20), 12), 'n': ((0, -5.5, 3), (0, 6.7, 8), 16)}.items():
        bl.camera(p, t, lens); bl.render(out + f'-{k}.jpg', 1400, 800, 32)
