"""Procuratie Nuove (Scamozzi), Procuratie Vecchie, Ala Napoleonica: piazza facades built bay by bay
with the classical kit (Istrian stone), porticoes with floors, ceilings and shopfronts."""
import math
import numpy as np
from vk import geom as G, arch as A
from ..world import GROUND_Z
from ..materials import MAT
from .common import facade_frame, place, translate, compose, wf, pf, PU

STONE = 'trim'

def _arch_opening(x0, w, zs):
    return G.opening_shape(w, zs + w / 2, 'arch', n=14, x=x0, y=0)

def hanging_lantern(x, y, z_ceiling, drop=1.4):
    """lantern hanging from a portico ceiling on a rod: lit at night ('street_glass')."""
    m = G.Mesh()
    zt = z_ceiling - drop
    m.merge(G.box(x - 0.015, y - 0.015, zt + 0.55, x + 0.015, y + 0.015, z_ceiling, 'metal'))
    m.merge(G.lathe([(0.0, 0.0), (0.12, 0.04), (0.2, 0.35), (0.22, 0.45)], 6, mat='street_glass', center=(x, y, zt)))
    m.merge(G.lathe([(0.22, 0.45), (0.25, 0.48), (0.12, 0.58), (0.03, 0.6)], 6, mat='metal', center=(x, y, zt)))
    m.merge(G.lathe([(0.0, -0.05), (0.08, -0.04), (0.05, 0.0)], 6, mat='metal', center=(x, y, zt)))
    return m

def _glass_panel(pts, y, mat='glass'):
    """flat panel in the x-z plane at depth y facing -y."""
    return A.fix_orient(G.cap([pts], 0, mat, True, G.frame((0, y, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0))

# ------------------------------------------------------------------ Procuratie Nuove
NUOVE = dict(arch_w=2.62, arch_spring=4.75, g_ent=6.55, g_top=8.0, f1_ped=9.15, f1_win=(1.66, 3.95), f1_ent=13.65, f1_top=14.85,
             f2_ped=15.9, f2_win=(1.3, 2.45), f2_ent=20.25, top=21.8, portico=5.6)

def nuove_bay(W, idx, florian=False):
    P = NUOVE; m = G.Mesh()
    xc = W / 2
    # ---- ground storey: arcade wall with arch, engaged Doric half-columns at x=0, archivolt, keystone
    aw = P['arch_w']; zs = P['arch_spring']
    m.merge(G.wall(W, P['g_top'], 0.62, STONE, openings=[_arch_opening(xc - aw / 2, aw, zs)], back=True, sides=False))
    col = A.column(0.68, P['g_ent'], order='doric', mat=STONE, seg=14)
    m.merge(col.transformed(G.mat4((0, -0.02, 0))))
    m.merge(A.arch_moulding(xc, zs, aw / 2, 0.24, 0.07, STONE, y=0.0, n=14))
    m.merge(G.box(xc - 0.16, -0.12, zs + aw / 2 - 0.05, xc + 0.16, 0.0, zs + aw / 2 + 0.42, STONE))
    # impost blocks
    for x in (xc - aw / 2 - 0.12, xc + aw / 2 - 0.02):
        m.merge(G.box(x, -0.06, zs - 0.18, x + 0.14, 0.0, zs, STONE))
    m.merge(A.entablature(0, W, P['g_ent'], P['g_top'] - P['g_ent'], 0.55, STONE, kind='doric'))
    # portico: floor (stone), ceiling, back wall with a shopfront
    d = P['portico']
    m.merge(G.box(0, 0.62, -0.05, W, d, 0.0, 'portico_floor', faces=('+z',)))
    m.merge(G.box(0, 0.62, 6.9, W, d, 7.05, STONE, faces=('-z',)))
    # transverse arch (between bays) under the ceiling, and a hanging lantern in the middle of the bay
    m.merge(G.box(-0.25, 0.62, 5.9, 0.25, d, 6.9, STONE, faces=('-z', '-x', '+x')))
    m.merge(hanging_lantern(xc, (0.62 + d) / 2, 6.9))
    sw, sh = (2.7, 3.6)
    shop = [(xc - sw / 2, 0.0), (xc + sw / 2, 0.0), (xc + sw / 2, sh), (xc - sw / 2, sh)]
    back = G.wall(W, 6.9, 0.3, 'portico_wall', openings=[shop], back=False, sides=False)
    m.merge(back.transformed(G.mat4((0, d, 0))))
    # shopfront: dark wood frame + glass (Florian's are richer: handled by florian=True)
    fy = d + 0.12
    wood = 'shop_wood' if not florian else 'florian_wood'
    if not florian:
        m.merge(_glass_panel(shop, fy + 0.02))
        bars = ((xc - sw / 2, xc - sw / 2 + 0.12, 0, sh), (xc + sw / 2 - 0.12, xc + sw / 2, 0, sh), (xc - sw / 2, xc + sw / 2, sh - 0.14, sh),
                (xc - sw / 2, xc + sw / 2, 0, 0.55), (xc - 0.05, xc + 0.05, 0, sh), (xc - sw / 2, xc + sw / 2, 2.35, 2.45))
    else:
        # Florian: glazed side lights and transom, the double door standing open into the room
        for (x0, x1, z0, z1) in ((xc - sw / 2, xc - 0.62, 0.55, 2.35), (xc + 0.62, xc + sw / 2, 0.55, 2.35), (xc - sw / 2, xc + sw / 2, 2.45, sh)):
            m.merge(_glass_panel([(x0, z0), (x1, z0), (x1, z1), (x0, z1)], fy + 0.02))
        bars = ((xc - sw / 2, xc - sw / 2 + 0.12, 0, sh), (xc + sw / 2 - 0.12, xc + sw / 2, 0, sh), (xc - sw / 2, xc + sw / 2, sh - 0.14, sh),
                (xc - sw / 2, xc - 0.62, 0, 0.55), (xc + 0.62, xc + sw / 2, 0, 0.55), (xc - 0.7, xc - 0.6, 0, 2.45), (xc + 0.6, xc + 0.7, 0, 2.45), (xc - sw / 2, xc + sw / 2, 2.35, 2.45))
        for sx in (-1, 1):
            hx = xc + sx * 0.6
            m.merge(G.box(min(hx, hx - sx * 0.05), fy + 0.05, 0.02, max(hx, hx - sx * 0.05), fy + 0.62, 2.3, wood))
    for (x0, x1, z0, z1) in bars:
        m.merge(G.box(x0, fy - 0.06, z0, x1, fy + 0.02, z1, wood))
    # sign band above the shopfront
    m.merge(G.box(xc - sw / 2 - 0.1, d - 0.02, sh + 0.15, xc + sw / 2 + 0.1, d + 0.02, sh + 0.75, 'florian_sign' if florian else 'shop_sign'))
    # ---- first storey (Ionic): pedestal zone + balustrade, arched window, half columns, small window columns
    ww, wh = P['f1_win']; z0 = P['f1_ped']
    win = G.opening_shape(ww, wh, 'arch', n=12, x=xc - ww / 2, y=z0)
    m.merge(G.wall(W, P['f1_top'] - P['g_top'], 0.5, STONE, openings=[[(p[0], p[1] - P['g_top']) for p in win]], back=False, sides=False).transformed(G.mat4((0, 0, P['g_top']))))
    m.merge(A.balustrade(xc - ww / 2 - 0.25, xc + ww / 2 + 0.25, P['g_top'] + 0.05, z0 - P['g_top'] - 0.05, 0.26, STONE, y=-0.3, bal_seg=6))
    m.merge(G.box(-0.42, -0.36, P['g_top'], 0.42, 0.0, z0, STONE))                     # pedestal under the column
    m.merge(A.column(0.5, P['f1_ent'] - z0, order='ionic', mat=STONE, seg=12).transformed(G.mat4((0, -0.12, z0))))
    for x in (xc - ww / 2 - 0.2, xc + ww / 2 + 0.2):
        m.merge(A.column(0.24, wh - ww / 2 - 0.05, order='ionic', mat=STONE, seg=8).transformed(G.mat4((x, -0.08, z0))))
    m.merge(A.arch_moulding(xc, z0 + wh - ww / 2, ww / 2, 0.16, 0.05, STONE, y=0.0, n=12))
    m.merge(_glass_panel(win, 0.38))
    m.merge(A.entablature(0, W, P['f1_ent'], P['f1_top'] - P['f1_ent'], 0.5, STONE, kind='ionic'))
    # ---- second storey (Corinthian): balustrade, aedicule window with alternating pediments
    ww2, wh2 = P['f2_win']; z2 = P['f2_ped']
    win2 = G.opening_shape(ww2, wh2, 'rect', x=xc - ww2 / 2, y=z2 + 0.1)
    m.merge(G.wall(W, P['top'] - P['f1_top'], 0.5, STONE, openings=[[(p[0], p[1] - P['f1_top']) for p in win2]], back=False, sides=False).transformed(G.mat4((0, 0, P['f1_top']))))
    m.merge(A.balustrade(xc - ww2 / 2 - 0.3, xc + ww2 / 2 + 0.3, P['f1_top'] + 0.05, z2 - P['f1_top'] - 0.05, 0.24, STONE, y=-0.28, bal_seg=6))
    m.merge(G.box(-0.4, -0.34, P['f1_top'], 0.4, 0.0, z2, STONE))
    m.merge(A.column(0.48, P['f2_ent'] - z2, order='corinthian', mat=STONE, seg=10, detail=0.1).transformed(G.mat4((0, -0.12, z2))))
    m.merge(A.aedicule(xc, z2 + 0.1, ww2, wh2, STONE, kind='tri' if idx % 2 == 0 else 'seg', y=0.0, window=True))
    m.merge(A.entablature(0, W, P['f2_ent'], P['top'] - P['f2_ent'], 0.8, STONE))
    return m

def nuove_end(W):
    """closing half-columns at the last x = W."""
    m = G.Mesh(); P = NUOVE
    m.merge(A.column(0.68, P['g_ent'], order='doric', mat=STONE, seg=14).transformed(G.mat4((W, -0.02, 0))))
    m.merge(G.box(W - 0.42, -0.36, P['g_top'], W + 0.42, 0.0, P['f1_ped'], STONE))
    m.merge(A.column(0.5, P['f1_ent'] - P['f1_ped'], order='ionic', mat=STONE, seg=12).transformed(G.mat4((W, -0.12, P['f1_ped']))))
    m.merge(G.box(W - 0.4, -0.34, P['f1_top'], W + 0.4, 0.0, P['f2_ped'], STONE))
    m.merge(A.column(0.48, P['f2_ent'] - P['f2_ped'], order='corinthian', mat=STONE, seg=10, detail=0.1).transformed(G.mat4((W, -0.12, P['f2_ped']))))
    return m

def build_nuove(mb, florian_u=(-84.0, -60.0)):
    """Procuratie Nuove piazza facade from u=-142.3 (v=-23.0) to u=-5.7 (v=-18.7)."""
    a = wf(-142.3, -23.0); b = wf(-5.7, -18.7)
    d = (b - a) / np.linalg.norm(b - a); n_out = np.array([-d[1], d[0]])     # left of a->b = north = piazza
    M, L, flipped = facade_frame(a, b, n_out)
    nb = int(round(L / 4.02)); W = L / nb
    cache = {}
    for i in range(nb):
        # bay centre in piazza u (for Florian's shopfronts)
        t = (i + 0.5) / nb
        xw = (b if flipped else a) + (a - b if flipped else b - a) * t
        u = pf(xw)[0]
        flor = florian_u[0] <= u <= florian_u[1]
        key = (i % 2, flor)
        if key not in cache: cache[key] = nuove_bay(W, i, florian=flor)
        place(mb, cache[key], compose(M, translate(i * W)))
    place(mb, nuove_end(W), compose(M, translate((nb - 1) * W)))
    return dict(line=(a, b), height=NUOVE['top'], bays=nb, W=W)

# ------------------------------------------------------------------ Procuratie Vecchie
VECCHIE = dict(arch_w=2.25, spring=4.0, g_ent=5.6, g_top=6.55, f1=6.55, f1_top=11.55, f2_top=16.45, frieze_top=18.0, merlon=1.15, portico=5.2)

def vecchie_bay(W):
    """one ground bay (two upper bays) of the Procuratie Vecchie."""
    P = VECCHIE; m = G.Mesh(); xc = W / 2
    aw = P['arch_w']; zs = P['spring']
    m.merge(G.wall(W, P['g_top'], 0.55, STONE, openings=[_arch_opening(xc - aw / 2, aw, zs)], back=True, sides=False))
    m.merge(A.column(0.5, zs, order='corinthian', mat=STONE, seg=10, detail=0.1).transformed(G.mat4((0, -0.18, 0))))
    m.merge(A.arch_moulding(xc, zs, aw / 2, 0.2, 0.06, STONE, n=12))
    m.merge(A.entablature(0, W, P['g_ent'], P['g_top'] - P['g_ent'], 0.32, STONE))
    d = P['portico']
    m.merge(G.box(0, 0.55, -0.05, W, d, 0.0, 'portico_floor', faces=('+z',)))
    m.merge(G.box(0, 0.55, 5.3, W, d, 5.45, STONE, faces=('-z',)))
    m.merge(hanging_lantern(xc, (0.55 + d) / 2, 5.3, drop=1.2))
    sw, sh = 2.3, 3.4
    shop = [(xc - sw / 2, 0.0), (xc + sw / 2, 0.0), (xc + sw / 2, sh), (xc - sw / 2, sh)]
    m.merge(G.wall(W, 5.3, 0.3, 'portico_wall', openings=[shop], back=False, sides=False).transformed(G.mat4((0, d, 0))))
    m.merge(_glass_panel(shop, d + 0.14))
    for (x0, x1, z0, z1) in ((xc - sw / 2, xc - sw / 2 + 0.1, 0, sh), (xc + sw / 2 - 0.1, xc + sw / 2, 0, sh), (xc - sw / 2, xc + sw / 2, sh - 0.12, sh), (xc - sw / 2, xc + sw / 2, 0, 0.5)):
        m.merge(G.box(x0, d + 0.06, z0, x1, d + 0.14, z1, 'shop_wood'))
    m.merge(G.box(xc - sw / 2 - 0.1, d - 0.02, sh + 0.12, xc + sw / 2 + 0.1, d + 0.02, sh + 0.62, 'shop_sign'))
    # upper storeys: two arched windows per bay on each floor, small columns between them
    for (z0, z1) in ((P['f1'], P['f1_top']), (P['f1_top'], P['f2_top'])):
        h = z1 - z0; ww = 0.98; wh = h - 1.75
        wins = []
        for k in range(2):
            cx = W * (0.25 + 0.5 * k)
            wins.append(G.opening_shape(ww, wh, 'arch', n=10, x=cx - ww / 2, y=0.85))
        m.merge(G.wall(W, h, 0.45, STONE, openings=wins, back=False, sides=False).transformed(G.mat4((0, 0, z0))))
        for k in range(2):
            cx = W * (0.25 + 0.5 * k)
            m.merge(A.arch_moulding(cx, z0 + 0.85 + wh - ww / 2, ww / 2, 0.12, 0.05, STONE, n=10))
            m.merge(_glass_panel([(p[0], p[1] + z0) for p in wins[k]], 0.3))
            m.merge(G.box(cx - ww / 2 - 0.08, -0.12, z0 + 0.72, cx + ww / 2 + 0.08, 0.0, z0 + 0.85, STONE))      # sill
        for x in (0.0, W * 0.5):
            m.merge(A.column(0.3, wh - ww / 2 + 0.85 - 0.1, order='corinthian', mat=STONE, seg=8, detail=0.1).transformed(G.mat4((x, -0.1, z0 + 0.1))))
        m.merge(A.entablature(0, W, z1 - 0.62, 0.62, 0.22, STONE))
    # frieze with two oculi, cornice and the crenellation (merli)
    z0 = P['f2_top']; z1 = P['frieze_top']
    oc = [G.opening_shape(0.5, 0.5, 'circle', n=8, x=W * (0.25 + 0.5 * k) - 0.25, y=0.5) for k in range(2)]
    m.merge(G.wall(W, z1 - z0, 0.4, STONE, openings=oc, back=False, sides=False).transformed(G.mat4((0, 0, z0))))
    for k in range(2):
        m.merge(_glass_panel([(p[0], p[1] + z0) for p in oc[k]], 0.25, 'dark'))
    m.merge(A.straight(A.cornice_profile(0.3, 0.3), 0, W, z1 - 0.3, 0.0, STONE))
    for k in range(2):
        cx = W * (0.25 + 0.5 * k)
        m.merge(G.box(cx - 0.17, 0.0, z1, cx + 0.17, 0.3, z1 + 0.55, STONE))
        m.merge(G.lathe([(0.17, 0.0), (0.2, 0.08), (0.12, 0.3), (0.05, 0.55), (0.0, 0.6)], 6, mat=STONE).transformed(G.mat4((cx, 0.15, z1 + 0.55))))
    return m

VECCHIE_LINE = ((-143.22, 34.17), (8.22, 66.83))     # OSM facade edge (piazza frame)

def build_vecchie(mb):
    """north side along the OSM facade edge, from the Ala Napoleonica corner to the Torre dell'Orologio."""
    a = wf(*VECCHIE_LINE[0]); b = wf(*VECCHIE_LINE[1])
    d = (b - a) / np.linalg.norm(b - a); n_out = np.array([d[1], -d[0]])        # right of a->b = south = piazza
    M, L, flipped = facade_frame(a, b, n_out)
    nb = 50; W = L / nb
    bay = vecchie_bay(W)
    for i in range(nb): place(mb, bay, compose(M, translate(i * W)))
    place(mb, A.column(0.5, VECCHIE['spring'], order='corinthian', mat=STONE, seg=10, detail=0.1), compose(M, translate(nb * W, -0.18, 0)))
    return dict(line=(a, b), height=VECCHIE['frieze_top'] + VECCHIE['merlon'], bays=nb, W=W)

# ------------------------------------------------------------------ Ala Napoleonica (east-facing, u = -142.2)
def build_napoleonica(mb):
    a = wf(-142.2, -23.0); b = wf(-142.2, 37.0)
    n_out = PU_dir = wf(1.0, 0.0)
    M, L, flipped = facade_frame(a, b, n_out)
    nb = int(round(L / 4.02)); W = L / nb
    P = NUOVE
    for i in range(nb):
        m = G.Mesh(); xc = W / 2
        aw = P['arch_w']; zs = P['arch_spring']
        m.merge(G.wall(W, P['g_top'], 0.62, STONE, openings=[_arch_opening(xc - aw / 2, aw, zs)], back=True, sides=False))
        m.merge(A.column(0.68, P['g_ent'], order='doric', mat=STONE, seg=14).transformed(G.mat4((0, -0.02, 0))))
        m.merge(A.arch_moulding(xc, zs, aw / 2, 0.24, 0.07, STONE, n=14))
        m.merge(A.entablature(0, W, P['g_ent'], P['g_top'] - P['g_ent'], 0.55, STONE))
        m.merge(G.box(0, 0.62, -0.05, W, 5.2, 0.0, 'portico_floor', faces=('+z',)))
        m.merge(G.box(0, 0.62, 6.9, W, 5.2, 7.05, STONE, faces=('-z',)))
        m.merge(hanging_lantern(xc, (0.62 + 5.2) / 2, 6.9))
        m.merge(G.wall(W, 6.9, 0.3, 'portico_wall', back=False, sides=False).transformed(G.mat4((0, 5.2, 0))))
        ww, wh = P['f1_win']; z0 = P['f1_ped']
        win = G.opening_shape(ww, wh, 'arch', n=12, x=xc - ww / 2, y=z0)
        m.merge(G.wall(W, P['f1_top'] - P['g_top'], 0.5, STONE, openings=[[(p[0], p[1] - P['g_top']) for p in win]], back=False, sides=False).transformed(G.mat4((0, 0, P['g_top']))))
        m.merge(A.balustrade(xc - ww / 2 - 0.25, xc + ww / 2 + 0.25, P['g_top'] + 0.05, z0 - P['g_top'] - 0.05, 0.26, STONE, y=-0.3, bal_seg=6))
        m.merge(A.column(0.5, P['f1_ent'] - z0, order='ionic', mat=STONE, seg=12).transformed(G.mat4((0, -0.12, z0))))
        m.merge(G.box(-0.42, -0.36, P['g_top'], 0.42, 0.0, z0, STONE))
        m.merge(A.arch_moulding(xc, z0 + wh - ww / 2, ww / 2, 0.16, 0.05, STONE, n=12))
        m.merge(_glass_panel(win, 0.38))
        m.merge(A.entablature(0, W, P['f1_ent'], P['f1_top'] - P['f1_ent'], 0.5, STONE))
        # attic with a niche per bay
        m.merge(G.wall(W, 5.4, 0.5, STONE, back=False, sides=False).transformed(G.mat4((0, 0, P['f1_top']))))
        m.merge(A.niche(1.1, 2.6, 0.45, STONE).transformed(G.mat4((xc, 0.0, P['f1_top'] + 1.0))))
        m.merge(A.straight(A.cornice_profile(0.6, 0.45), 0, W, P['f1_top'] + 4.8, 0.0, STONE))
        place(mb, m, compose(M, translate(i * W)))
    return dict(line=(a, b), height=NUOVE['f1_top'] + 5.4, bays=nb, W=W)

# ------------------------------------------------------------------ walkable porticoes (for the walk raster)
def _portico(a, b, n_out, depth, nb, arch_w, pier_d):
    """portico strip behind a facade line a-b (n_out toward the piazza) + the piers between the arches."""
    from shapely.geometry import Polygon
    a = np.asarray(a, float); b = np.asarray(b, float); n = np.asarray(n_out, float); n /= np.linalg.norm(n)
    d = b - a; L = np.linalg.norm(d); d /= L
    out = [(Polygon([a + n * 0.05, b + n * 0.05, b - n * (depth - 0.25), a - n * (depth - 0.25)]), GROUND_Z)]
    W = L / nb
    for i in range(nb + 1):
        c = a + d * (i * W)
        hw = (W - arch_w) / 2
        out.append((Polygon([c - d * hw + n * 0.35, c + d * hw + n * 0.35, c + d * hw - n * pier_d, c - d * hw - n * pier_d]), None))
    return out

def walk_areas():
    out = []
    a = wf(-142.3, -23.0); b = wf(-5.7, -18.7); d = (b - a) / np.linalg.norm(b - a)
    L = np.linalg.norm(b - a); out += _portico(a, b, np.array([-d[1], d[0]]), NUOVE['portico'], int(round(L / 4.02)), NUOVE['arch_w'], 0.62)
    a = wf(*VECCHIE_LINE[0]); b = wf(*VECCHIE_LINE[1]); d = (b - a) / np.linalg.norm(b - a)
    out += _portico(a, b, np.array([d[1], -d[0]]), VECCHIE['portico'], 50, VECCHIE['arch_w'], 0.55)
    a = wf(-142.2, -23.0); b = wf(-142.2, 37.0); L = np.linalg.norm(b - a)
    out += _portico(a, b, wf(1.0, 0.0), 5.2, int(round(L / 4.02)), NUOVE['arch_w'], 0.62)
    return out
