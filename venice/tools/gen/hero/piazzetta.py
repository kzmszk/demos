"""The Piazzetta and the north side of the piazza: Sansovino's Libreria (east front, 21 bays), the columns of
San Marco (winged lion) and San Todaro, and the Torre dell'Orologio with its wings."""
import math
import numpy as np
from shapely.geometry import Polygon
from vk import geom as G, arch as A
from ..world import GROUND_Z
from .common import facade_frame, place, translate, compose, wf, pf
from .basilica import statue

STONE = 'istrian'

def _arch_opening(x0, w, zs):
    return G.opening_shape(w, zs + w / 2, 'arch', n=14, x=x0, y=0)

def _glass_panel(pts, y, mat='glass'):
    return A.fix_orient(G.cap([pts], 0, mat, True, G.frame((0, y, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0))

# ------------------------------------------------------------------ Libreria (Sansovino, 1537-88)
LIB_A = np.array([41.7, -89.3]); LIB_B = np.array([14.0, -18.1])       # south -> north along the Piazzetta
LIB = dict(arch_w=2.25, spring=4.45, g_ent=6.6, g_top=8.1, ped=9.25, win=(1.45, 3.05), ent=14.1, frieze=16.35, cor=17.0, bal=18.15, portico=5.4)

def libreria_bay(W, end=False):
    P = LIB; m = G.Mesh(); xc = W / 2
    aw = P['arch_w']; zs = P['spring']
    m.merge(G.wall(W, P['g_top'], 0.65, STONE, openings=[_arch_opening(xc - aw / 2, aw, zs)], back=True, sides=False))
    m.merge(A.column(0.74, P['g_ent'], order='doric', mat=STONE, seg=12).transformed(G.mat4((0, -0.05, 0))))
    m.merge(A.arch_moulding(xc, zs, aw / 2, 0.22, 0.07, STONE, n=14))
    m.merge(G.box(xc - 0.15, -0.12, zs + aw / 2 - 0.05, xc + 0.15, 0.0, zs + aw / 2 + 0.45, STONE))       # keystone
    m.merge(A.entablature(0, W, P['g_ent'], P['g_top'] - P['g_ent'], 0.55, STONE, kind='doric'))
    for k in range(2):                                                                                   # triglyphs
        x = W * (0.25 + 0.5 * k) if k else 0.0
        for xx in (0.0, xc):
            m.merge(G.box(xx - 0.16, -0.08, P['g_ent'] + 0.45, xx + 0.16, 0.0, P['g_ent'] + 0.95, STONE))
    d = P['portico']
    m.merge(G.box(0, 0.65, -0.05, W, d, 0.0, 'portico_floor', faces=('+z',)))
    m.merge(G.box(0, 0.65, 7.0, W, d, 7.15, STONE, faces=('-z',)))
    door = [(xc - 0.9, 0.0), (xc + 0.9, 0.0), (xc + 0.9, 3.4), (xc - 0.9, 3.4)]
    m.merge(G.wall(W, 7.0, 0.3, 'portico_wall', openings=[door], back=False, sides=False).transformed(G.mat4((0, d, 0))))
    m.merge(_glass_panel(door, d + 0.15, 'shop_wood'))
    # first storey: balustrade pedestal, Ionic half column, serliana-like arched window on small columns
    ww, wh = P['win']; z0 = P['ped']
    win = G.opening_shape(ww, wh, 'arch', n=12, x=xc - ww / 2, y=z0)
    m.merge(G.wall(W, P['frieze'] - P['g_top'], 0.5, STONE, openings=[[(p[0], p[1] - P['g_top']) for p in win]], back=False, sides=False).transformed(G.mat4((0, 0, P['g_top']))))
    m.merge(A.balustrade(xc - ww / 2 - 0.3, xc + ww / 2 + 0.3, P['g_top'] + 0.05, z0 - P['g_top'] - 0.05, 0.26, STONE, y=-0.3, bal_seg=6))
    m.merge(A.column(0.56, P['ent'] - z0, order='ionic', mat=STONE, seg=12).transformed(G.mat4((0, -0.12, z0))))
    m.merge(G.box(-0.45, -0.38, P['g_top'], 0.45, 0.0, z0, STONE))
    for sx in (-1, 1):
        m.merge(A.column(0.24, wh - ww / 2, order='ionic', mat=STONE, seg=8).transformed(G.mat4((xc + sx * (ww / 2 + 0.2), -0.2, z0))))
    m.merge(A.arch_moulding(xc, z0 + wh - ww / 2, ww / 2, 0.16, 0.05, STONE, n=12))
    m.merge(_glass_panel(win, 0.38))
    # Ionic architrave, tall frieze with putti and garlands (relief) and an oval window, cornice
    m.merge(A.straight(A.architrave_profile(0.4, 0.06), 0, W, P['ent'], 0.0, STONE))
    m.merge(G.box(0.25, -0.08, P['ent'] + 0.5, W - 0.25, 0.0, P['frieze'] - 0.1, 'relief'))
    ov = G.opening_shape(1.0, 0.62, 'oval', n=8, x=xc - 0.5, y=P['ent'] + 0.9)
    m.merge(_glass_panel(ov, -0.1, 'dark'))
    m.merge(A.straight(A.cornice_profile(P['cor'] - P['frieze'], 0.6), 0, W, P['frieze'], 0.0, STONE))
    # balustrade with statues over the columns
    m.merge(A.balustrade(0, W, P['cor'], P['bal'] - P['cor'], 0.3, STONE, y=0.0, bal_seg=6))
    m.merge(G.box(-0.35, -0.02, P['cor'], 0.35, 0.36, P['bal'] + 0.1, STONE))
    m.merge(statue(2.2).transformed(G.mat4((0, 0.15, P['bal'] + 0.1))))
    return m

def build_libreria(mb):
    d = (LIB_B - LIB_A) / np.linalg.norm(LIB_B - LIB_A); n_out = np.array([d[1], -d[0]])     # right of S->N = east
    M, L, flipped = facade_frame(LIB_A, LIB_B, n_out)
    nb = 21; W = L / nb
    bay = libreria_bay(W)
    for i in range(nb): place(mb, bay, compose(M, translate(i * W)))
    end = G.Mesh()
    end.merge(A.column(0.74, LIB['g_ent'], order='doric', mat=STONE, seg=12).transformed(G.mat4((L, -0.05, 0))))
    end.merge(A.column(0.56, LIB['ent'] - LIB['ped'], order='ionic', mat=STONE, seg=12).transformed(G.mat4((L, -0.12, LIB['ped']))))
    # corner obelisks
    for x in (0.0, L):
        end.merge(G.box(x - 0.5, -0.1, LIB['bal'], x + 0.5, 0.9, LIB['bal'] + 0.5, STONE))
        end.merge(G.lathe([(0.42, 0), (0.30, 0.2), (0.24, 3.4), (0.0, 3.9)], 4, mat=STONE, center=(x, 0.4, LIB['bal'] + 0.5)))
    place(mb, end, M)
    return dict(height=LIB['bal'] + 4.0, bays=nb, W=W)

def libreria_walk():
    d = (LIB_B - LIB_A) / np.linalg.norm(LIB_B - LIB_A); n = np.array([d[1], -d[0]])
    from .ducale import portico_walk
    L = float(np.linalg.norm(LIB_B - LIB_A))
    return portico_walk(LIB_A, LIB_B, n, LIB['portico'], 21, LIB['arch_w'], 0.65)

# ------------------------------------------------------------------ the two columns of the Piazzetta
COL_MARCO = np.array([69.2, -79.5]); COL_TODARO = np.array([49.4, -86.7])

def winged_lion(mat='bronze'):
    """stylised winged lion of St Mark (~4 m long), facing +x."""
    m = G.Mesh()
    m.merge(G.lathe([(0.0, 0), (0.55, 0.3), (0.62, 1.2), (0.5, 2.2), (0.0, 2.5)], 10, mat=mat).transformed(G.mat4((-1.2, 0, 1.15), ry=math.pi / 2, s=(1.0, 0.75, 1.0))))
    m.merge(G.lathe([(0.0, 0), (0.42, 0.15), (0.5, 0.5), (0.36, 0.95), (0.0, 1.05)], 10, mat=mat).transformed(G.mat4((1.15, 0, 1.75))))      # head + mane
    m.merge(G.box(1.4, -0.22, 1.55, 1.95, 0.22, 1.95, mat))
    for (x, y) in ((-0.9, -0.3), (-0.9, 0.3), (0.8, -0.3), (0.8, 0.3)):
        m.merge(G.box(x - 0.13, y - 0.12, 0.0, x + 0.13, y + 0.12, 1.2, mat))
    for s in (-1, 1):                                                                         # raised wings
        o = m.add_v([(-0.6, s * 0.35, 1.9), (0.6, s * 0.35, 2.0), (0.1, s * 1.5, 3.3), (-1.2, s * 1.3, 3.0)])
        m.face([o, o + 1, o + 2, o + 3] if s > 0 else [o + 3, o + 2, o + 1, o], mat)
        m.face([o + 3, o + 2, o + 1, o] if s > 0 else [o, o + 1, o + 2, o + 3], mat)
    m.merge(G.lathe([(0.0, 0), (0.22, 0.4), (0.0, 0.8)], 8, mat='gold').transformed(G.mat4((1.5, 0.45, 1.2))))     # the book
    return m

def column_monument(kind):
    m = G.Mesh()
    # stepped base (three steps) + pedestal with reliefs
    for k, (r, h) in enumerate(((3.1, 0.35), (2.7, 0.35), (2.3, 0.35))):
        m.merge(G.lathe([(r, k * 0.35), (r, (k + 1) * 0.35), (0, (k + 1) * 0.35)], 8, mat=STONE, a0=math.pi / 8, a1=math.pi / 8 + math.tau))
    z = 1.05
    m.merge(G.box(-1.3, -1.3, z, 1.3, 1.3, z + 0.4, STONE))
    m.merge(G.box(-1.15, -1.15, z + 0.4, 1.15, 1.15, z + 2.2, 'relief'))
    m.merge(G.box(-1.3, -1.3, z + 2.2, 1.3, 1.3, z + 2.55, STONE))
    z += 2.55
    shaft_mat = 'granite_grey' if kind == 'marco' else 'granite_pink'
    m.merge(G.lathe([(0.95, 0), (0.95, 0.25), (0.82, 0.4), (0.78, 9.8), (0.72, 10.6), (0.82, 10.75)], 20, mat=shaft_mat).transformed(G.mat4((0, 0, z))))
    z += 10.75
    m.merge(G.lathe([(0.82, 0), (0.95, 0.4), (1.2, 1.0), (1.25, 1.35)], 12, mat=STONE).transformed(G.mat4((0, 0, z))))     # capital
    m.merge(G.box(-1.3, -1.3, z + 1.35, 1.3, 1.3, z + 1.9, STONE))
    z += 1.9
    if kind == 'marco':
        m.merge(winged_lion().transformed(G.mat4((0, 0, z), rz=math.radians(-20))))
    else:
        m.merge(G.box(-1.4, -0.4, z, 1.4, 0.4, z + 0.5, 'marble_white'))                    # the dragon (crocodile)
        m.merge(statue(3.2, 'marble_white').transformed(G.mat4((0.3, 0, z + 0.3))))
        m.merge(G.box(0.8, -0.04, z + 1.2, 0.86, 0.04, z + 3.6, 'metal'))                    # spear
    return m

def build_columns(mb):
    place(mb, column_monument('marco'), G.mat4((COL_MARCO[0], COL_MARCO[1], GROUND_Z - 0.05)))
    place(mb, column_monument('todaro'), G.mat4((COL_TODARO[0], COL_TODARO[1], GROUND_Z - 0.05), rz=0.6))
    return dict(height=20.0)

def columns_walk():
    out = []
    for c in (COL_MARCO, COL_TODARO):
        out.append((Polygon([(c[0] + 2.4 * math.cos(a), c[1] + 2.4 * math.sin(a)) for a in np.linspace(0, math.tau, 9)[:-1]]), None))
    return out

# ------------------------------------------------------------------ Torre dell'Orologio (Codussi, 1496-99)
TW_U = (16.8, 22.8)            # tower span along the piazza north line (piazza u)
TORRE_LINE = (wf(8.22, 66.83), wf(30.2, 71.5))

def torre():
    """kit frame: x along the north line from u=8.22 (Vecchie end), facade faces the piazza (-y)."""
    a, b = TORRE_LINE
    L = float(np.linalg.norm(b - a))
    t0 = (TW_U[0] - 8.22) / (30.2 - 8.22) * L; t1 = (TW_U[1] - 8.22) / (30.2 - 8.22) * L
    m = G.Mesh(); w = t1 - t0; xc = (t0 + t1) / 2
    # wings: four storeys, arcaded ground floor, arched windows, terrace with balustrade
    for (x0, x1) in ((0.0, t0), (t1, L)):
        W = x1 - x0; nb = max(2, int(round(W / 3.3))); bw = W / nb
        ops = []
        for k in range(nb):
            cx = x0 + bw * (k + 0.5)
            ops.append(G.opening_shape(2.0, 3.6, 'arch', n=10, x=cx - 1.0 - x0, y=0.0))
        m.merge(G.wall(W, 4.4, 0.6, STONE, openings=ops, back=True, sides=False).transformed(G.mat4((x0, 0, 0))))
        for k in range(nb):
            cx = x0 + bw * (k + 0.5)
            m.merge(_glass_panel([(p[0] + x0, p[1]) for p in ops[k]], 0.45, 'shop_wood'))
        for (z0, z1) in ((4.4, 8.4), (8.4, 12.1), (12.1, 15.6)):
            wops = []
            for k in range(nb):
                cx = x0 + bw * (k + 0.5)
                wops.append(G.opening_shape(1.1, 2.3, 'arch', n=8, x=cx - 0.55 - x0, y=0.8))
            m.merge(G.wall(W, z1 - z0, 0.5, 'portico_wall', openings=wops, back=False, sides=False).transformed(G.mat4((x0, 0, z0))))
            for k in range(nb):
                m.merge(_glass_panel([(p[0] + x0, p[1] + z0) for p in wops[k]], 0.3))
                cx = x0 + bw * (k + 0.5)
                m.merge(G.box(cx - 0.75, -0.12, z0 + 0.65, cx + 0.75, 0.0, z0 + 0.8, STONE))
            m.merge(A.straight(A.string_course(0.25, 0.15), x0, x1, z1 - 0.25, 0.0, STONE))
        m.merge(A.straight(A.cornice_profile(0.6, 0.45), x0 - 0.1, x1 + 0.1, 15.6, 0.0, STONE))
        m.merge(A.balustrade(x0, x1, 16.2, 1.0, 0.25, STONE, y=0.0, bal_seg=6))
        m.merge(G.box(x0, 0, 16.15, x1, 7.5, 16.2, 'flat_roof', faces=('+z',)))
    # the tower: arch over the Mercerie, clock dial, Madonna, lion on a starry field, Moors and the bell
    H = 24.0
    op = G.opening_shape(3.4, 6.2, 'arch', n=14, x=w / 2 - 1.7, y=0.0)
    m.merge(G.wall(w, H, 0.8, STONE, openings=[op], back=False, sides=True, top=True).transformed(G.mat4((t0, -0.3, 0))))
    m.merge(A.arch_moulding(xc, 4.5, 1.7, 0.3, 0.1, STONE, y=-0.3, n=14))
    for (z0, z1) in ((7.2, 7.6), (13.0, 13.4), (16.4, 16.8), (21.4, 21.9)):
        m.merge(A.straight(A.string_course(z1 - z0, 0.2), t0 - 0.2, t1 + 0.2, z0, -0.3, STONE))
    # clock: blue enamel ring with gold numerals band, sun hand, square marble frame
    cz = 10.3; R = 2.35
    m.merge(G.box(xc - 2.75, -0.42, cz - 2.75, xc + 2.75, -0.3, cz + 2.75, 'marble_white'))
    dial = G.lathe([(R, 0), (0.0, 0)], 32, mat='clock_blue', center=(0, 0, 0)).transformed(G.mat4((xc, -0.5, cz), rx=-math.pi / 2))
    m.merge(dial)
    m.merge(G.lathe([(R + 0.18, 0), (R, 0)], 32, mat='gold').transformed(G.mat4((xc, -0.52, cz), rx=-math.pi / 2)))
    m.merge(G.lathe([(R * 0.62, 0), (R * 0.55, 0)], 24, mat='gold').transformed(G.mat4((xc, -0.53, cz), rx=-math.pi / 2)))
    m.merge(G.box(xc - 0.05, -0.62, cz - 0.05, xc + R * 0.95, -0.56, cz + 0.05, 'gold'))
    m.merge(G.lathe([(0.0, 0), (0.32, 0.0)], 12, mat='gold').transformed(G.mat4((xc + R * 0.95, -0.63, cz), rx=-math.pi / 2)))
    # Madonna in a gilded niche flanked by two blue doors (the Magi)
    m.merge(A.niche(1.5, 2.9, 0.5, 'gold').transformed(G.mat4((xc, -0.31, 13.45))))
    m.merge(statue(1.6, 'gold').transformed(G.mat4((xc, -0.5, 13.55))))
    for sx in (-1, 1):
        m.merge(G.box(xc + sx * 1.9 - 0.55, -0.36, 13.6, xc + sx * 1.9 + 0.55, -0.3, 15.8, 'clock_blue'))
    # lion on the blue starry field
    m.merge(G.box(xc - 2.5, -0.36, 17.0, xc + 2.5, -0.3, 21.2, 'lion_field'))
    m.merge(winged_lion('gold').transformed(G.mat4((xc, -0.62, 18.0), rz=0.0, s=(0.8, 0.25, 0.8))))
    # terrace: balustrade, bell on its frame, the two Moors
    m.merge(A.straight(A.cornice_profile(0.7, 0.5), t0 - 0.3, t1 + 0.3, H - 0.7, -0.3, STONE))
    m.merge(A.balustrade(t0, t1, H, 1.0, 0.25, STONE, y=-0.3, bal_seg=6))
    m.merge(G.box(t0, -0.3, H - 0.05, t1, 7.6, H, 'flat_roof', faces=('+z',)))
    for sx in (-1, 1):
        m.merge(G.box(xc + sx * 1.2 - 0.12, 2.6, H, xc + sx * 1.2 + 0.12, 2.9, H + 3.4, 'metal'))
    m.merge(G.lathe([(0.0, 0), (0.9, 0.05), (0.85, 0.6), (0.55, 1.4), (0.2, 1.6), (0.0, 1.62)], 16, mat='bronze').transformed(G.mat4((xc, 2.75, H + 2.0))))
    for sx in (-1, 1):
        m.merge(statue(2.6, 'bronze').transformed(G.mat4((xc + sx * 2.1, 2.75, H))))
    return m

def build_torre(mb):
    a, b = TORRE_LINE
    d = (b - a) / np.linalg.norm(b - a); n_out = np.array([d[1], -d[0]])      # toward the piazza (south)
    M, L, flipped = facade_frame(a, b, n_out)
    m = torre()
    if flipped:
        # facade_frame runs x from b: mirror the kit so x=0 stays at the Vecchie end
        F = np.eye(4); F[0, 0] = -1; F[0, 3] = L
        m = m.transformed(F)
        m.F = [f[::-1] for f in m.F]
    place(mb, m, M)
    return dict(height=30.0)
