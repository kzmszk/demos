"""The spill from the fallen north crown: a walkable rubble ramp at the north-west foot of No.1, with slabs,
curtain-wall grids, granite panels and bent steel lying on it; debris on the setback roofs.

surface(x, y) is the ramp's height field; collide uses the same mesh.
"""
import bpy, math, random
import numpy as np
from mathutils import Vector, Matrix, Euler
import common as C
import uvmap as U
import materials as M
from buildings import seg, hnoise

MC = U.MC

# lobes: (x, y, peak height above ground, radius) -- the main pile leans on the north-west corner of No.1
LOBES = [(-62.0, 119.0, 17.0, 40.0), (-44.0, 121.0, 10.0, 26.0), (-80.0, 116.0, 8.0, 22.0), (-30.0, 125.0, 5.0, 16.0),
         (-72.0, 138.0, 3.5, 14.0)]


def _noise(x, y):
    return (math.sin(x * 0.21 + 1.3) * math.cos(y * 0.17 - 0.4) * 0.5 + math.sin(x * 0.53 + y * 0.41) * 0.3
            + math.sin(x * 1.3 - y * 1.1) * 0.12)


def pile_height(x, y):
    h = 0.0
    for lx, ly, ph, r in LOBES:
        d = math.hypot(x - lx, y - ly) / r
        if d < 1: h = max(h, ph * (1 - d) ** 1.35)
    if h > 0.05: h += _noise(x, y) * min(1.2, h * 0.3)
    return max(h, 0.0)


def surface(x, y):
    g = C.ground(x, y)
    h = pile_height(x, y)
    return g + h if h > 0.05 else g


def build(col, dec, R=None):
    R = R or random.Random(17)
    mats = M.all_mats()
    mound = C.MB(); pieces = C.MB(); grids = C.MB(); colmb = C.MB()
    # ---------------------------------------------------------------- the mound
    S = 1.7
    x0, x1, y0, y1 = -112, -14, 92, 160
    nx, ny = int((x1 - x0) / S) + 1, int((y1 - y0) / S) + 1
    H = np.zeros((ny, nx)); G = np.zeros((ny, nx))
    for j in range(ny):
        for i in range(nx):
            x, y = x0 + i * S, y0 + j * S
            H[j, i] = pile_height(x, y); G[j, i] = C.ground(x, y)
    idx = {}
    def V(i, j):
        if (i, j) not in idx:
            x, y = x0 + i * S, y0 + j * S
            # jitter interior points so the grid does not read
            jx = (hnoise(1, i, j) - 0.5) * S * 0.5 if H[j, i] > 0.3 else 0
            jy = (hnoise(2, i, j) - 0.5) * S * 0.5 if H[j, i] > 0.3 else 0
            h = pile_height(x + jx, y + jy)
            z = C.ground(x + jx, y + jy) + (h - 0.25 if h > 0.05 else -0.25)
            idx[(i, j)] = (mound.v((x + jx, y + jy, z)), colmb.v((x + jx, y + jy, z + 0.25 if h > 0.05 else z + 0.25)))
        return idx[(i, j)]
    for j in range(ny - 1):
        for i in range(nx - 1):
            if max(H[j, i], H[j, i + 1], H[j + 1, i], H[j + 1, i + 1]) < 0.06: continue
            a, b, c, d = V(i, j), V(i + 1, j), V(i + 1, j + 1), V(i, j + 1)
            hm = (H[j, i] + H[j + 1, i + 1]) / 2
            n = hnoise(3, i // 3, j // 3)
            cell = MC['broken'] if (hm > 6 and n < 0.55) or n < 0.25 else (MC['soil'] if n < 0.7 else MC['moss'])
            mound.face([a[0], b[0], c[0], d[0]], 0, cell)
            colmb.face([a[1], b[1], c[1], d[1]], 0, 0)
    # ---------------------------------------------------------------- big pieces lying on it
    def place_box(mb, x, y, size, cell, tilt=0.35, sink=0.35):
        z = surface(x, y)
        # slope-aligned tilt
        e = 0.8
        dzx = (surface(x + e, y) - surface(x - e, y)) / (2 * e); dzy = (surface(x, y + e) - surface(x, y - e)) / (2 * e)
        rz = R.uniform(0, math.pi)
        rx = math.atan(dzy) + R.uniform(-tilt, tilt); ry = -math.atan(dzx) + R.uniform(-tilt, tilt)
        M_ = Euler((rx, ry, 0), 'XYZ').to_matrix() @ Matrix.Rotation(rz, 3, 'Z')
        sx, sy, sz = size[0] / 2, size[1] / 2, size[2] / 2
        P = [Vector((x, y, z - sink + sz)) + M_ @ Vector((px, py, pz)) for pz in (-sz, sz) for py in (-sy, sy) for px in (-sx, sx)]
        i = [mb.v(p) for p in P]
        for f in [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)]:
            mb.face([i[k] for k in f], 0, cell if f != (4, 5, 7, 6) else (MC['panel'] if cell == MC['panel'] else cell))
        return P
    count = 0
    for k in range(260):
        x = R.uniform(-110, -16); y = R.uniform(94, 158)
        h = pile_height(x, y)
        if h < 0.6: continue
        kind = R.random()
        if kind < 0.32:   # floor slab fragments
            place_box(pieces, x, y, (R.uniform(3, 8), R.uniform(2.5, 6), R.uniform(0.35, 0.5)), MC['concrete'], 0.5)
        elif kind < 0.6:  # granite facade panels (with the Tange window pattern)
            place_box(pieces, x, y, (3.2, R.choice((4.0, 2.0)), 0.3), MC['panel'], 0.6)
        elif kind < 0.75:  # chunks
            s = R.uniform(0.8, 2.4)
            place_box(pieces, x, y, (s, s * R.uniform(0.6, 1), s * R.uniform(0.5, 0.9)), MC['broken'], 0.8, sink=0.2)
        elif kind < 0.88:  # bent steel
            z = surface(x, y)
            a = R.uniform(0, 6.28); L = R.uniform(4, 10)
            d = Vector((math.cos(a), math.sin(a), R.uniform(-0.1, 0.5)))
            p0 = Vector((x, y, z - 0.3)); pm = p0 + d * L * 0.5 + Vector((0, 0, R.uniform(0.3, 1.5)))
            seg(pieces, p0, pm, 0.4); seg(pieces, pm, pm + Vector((d.x, d.y, -0.6)).normalized() * L * 0.5, 0.36)
        else:   # curtain-wall grid sections, some propped up
            P = place_box(grids, x, y, (3.2, 4.0, 0.05), MC['grid'], 1.2, sink=-0.2)
        count += 1
    # ---------------------------------------------------------------- the crown fragment resting on the north setback roof
    for k in range(40):
        x = R.uniform(-66, -22); y = R.uniform(84, 112)
        z0 = 186.2
        s = R.uniform(1, 5)
        P = [Vector((x, y, z0 + s * 0.2)) + Euler((R.uniform(-0.4, 0.4), R.uniform(-0.4, 0.4), R.uniform(0, 3)), 'XYZ').to_matrix() @ Vector((px, py, pz))
             for pz in (-s * 0.2, s * 0.2) for py in (-s / 2, s / 2) for px in (-s * 0.7, s * 0.7)]
        i = [pieces.v(p) for p in P]
        for f in [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)]:
            pieces.face([i[k] for k in f], 0, R.choice((MC['broken'], MC['panel'], MC['concrete'])))
    # ---------------------------------------------------------------- decals at the toe of the pile: gravel and chunks
    for k in range(40):
        a = R.uniform(0, 6.28); lx, ly, ph, r = LOBES[R.randrange(len(LOBES))]
        x = lx + math.cos(a) * r * R.uniform(0.85, 1.25); y = ly + math.sin(a) * r * R.uniform(0.85, 1.25)
        dec.disc(x, y, R.uniform(2, 5), U.DC[R.choice(['rubble', 'gravel', 'rubble', 'mud'])], 9, R, off=0.05)
    out = []
    o = mound.build('rubble_mound', [mats['mat']], col); U.cut_and_map(o, U.MAT_CELLS); out.append(o)
    o = pieces.build('rubble_pieces', [mats['detail']], col); U.cut_and_map(o, U.MAT_CELLS); o['lod'] = 'near'; out.append(o)
    o = grids.build('rubble_grids', [mats['matcut']], col); U.cut_and_map(o, U.MAT_CELLS); o['lod'] = 'near'; out.append(o)
    cm = colmb.build('col_rubble', [], C.coll('collide'))
    return out, cm
