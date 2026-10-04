"""Caffè Florian (1720): six small rooms behind the Procuratie Nuove portico, each with its own decoration, and
the terrace with the orchestra stage in the piazza.

Rooms (one per arcade bay, enfilade through doorways near the back): Sala Liberty, Sala degli Uomini Illustri
(walnut, the ten portraits), Sala del Senato (gilt panels, allegories, painted ceiling), Sala Cinese (pale blue,
chinoiseries), Sala Orientale (gilt mirrors, oriental figures), Sala delle Stagioni (cream and gold, oval
mirrors, Rosalba Carriera's Four Seasons).  Red velvet banquettes, marble tables on carved legs, cane chairs,
gilt sconces and Murano chandeliers whose glass is emissive in the bake (the café is lamp-lit day and night).

Geometry is built in the Procuratie Nuove kit frame: x along the facade, -y toward the piazza, +y into the
building; the portico back wall (shopfronts) is at y = 5.6..5.9."""
import json, math, os
import numpy as np
from shapely.geometry import Polygon
from vk import geom as G, arch as A
from ..world import GROUND_Z
from .common import facade_frame, place, translate, compose, wf, pf
from . import procuratie as PR

ART = json.load(open('/home/kazu/work/demos/venice/public/tex/art.json'))['items'] if os.path.exists('/home/kazu/work/demos/venice/public/tex/art.json') else {}
Y0 = 5.9; DEPTH = 8.2; Y1 = Y0 + DEPTH; H = 4.5
THEMES = ['stagioni', 'illustri', 'senato', 'cinese', 'orientale', 'liberty']

def nuove_frame():
    a = wf(-142.3, -23.0); b = wf(-5.7, -18.7)
    d = (b - a) / np.linalg.norm(b - a); n_out = np.array([-d[1], d[0]])
    M, L, flipped = facade_frame(a, b, n_out)
    nb = int(round(L / 4.02)); W = L / nb
    return M, L, nb, W, flipped, a, b

def florian_bays():
    M, L, nb, W, flipped, a, b = nuove_frame()
    out = []
    for i in range(nb):
        t = (i + 0.5) / nb
        xw = (b if flipped else a) + (a - b if flipped else b - a) * t
        u = pf(xw)[0]
        if -84.0 <= u <= -60.0: out.append(i)
    return out

def quad(m, pts, want, mat):
    P = np.array(pts, float); n = np.cross(P[1] - P[0], P[2] - P[0])
    m.poly(pts if np.dot(n, want) >= 0 else pts[::-1], mat)

def painting(m_list, key, cx, cy, cz, w, h, normal, frame_mat='gilt', fw=0.09):
    """framed painting centred at (cx, cy, cz) on a wall facing `normal` (+-x or +-y), size w x h (art aspect kept)."""
    it = ART.get(key)
    if it is None: return
    asp = it['aspect']
    if w / h > asp: w = h * asp
    else: h = w / asp
    nx, ny = normal
    tx, ty = -ny, nx                               # along the wall (right when facing the wall from the room)
    m = G.Mesh()
    def P(u, v, d): return (cx + tx * u + nx * d, cy + ty * u + ny * d, cz + v)
    o = m.add_v([P(-w / 2, -h / 2, 0.03), P(w / 2, -h / 2, 0.03), P(w / 2, h / 2, 0.03), P(-w / 2, h / 2, 0.03)])
    q = [o, o + 1, o + 2, o + 3]
    V = np.array(m.V); n = np.cross(V[1] - V[0], V[2] - V[0])
    uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    if np.dot(n, (nx, ny, 0)) < 0: q = q[::-1]; uv = uv[::-1]
    m.face(q, 'painting', uv=uv)
    m_list.append((m, it['layer']))
    # frame: four bars
    fr = G.Mesh()
    for (u0, u1, v0, v1) in ((-w / 2 - fw, w / 2 + fw, -h / 2 - fw, -h / 2), (-w / 2 - fw, w / 2 + fw, h / 2, h / 2 + fw), (-w / 2 - fw, -w / 2, -h / 2, h / 2), (w / 2, w / 2 + fw, -h / 2, h / 2)):
        for (a0, a1, b0, b1, d0, d1) in ((u0, u1, v0, v1, 0.0, 0.07),):
            pts = [P(a0, b0, d1), P(a1, b0, d1), P(a1, b1, d1), P(a0, b1, d1)]
            quad(fr, pts, (nx, ny, 0), frame_mat)
            quad(fr, [P(a0, b0, 0), P(a1, b0, 0), P(a1, b0, d1), P(a0, b0, d1)], (0, 0, -1), frame_mat)
            quad(fr, [P(a0, b1, 0), P(a1, b1, 0), P(a1, b1, d1), P(a0, b1, d1)], (0, 0, 1), frame_mat)
    m_list.append((fr, 0))

def oval_mirror(m, cx, cy, cz, w, h, normal):
    nx, ny = normal; tx, ty = -ny, nx
    pts = [(cx + tx * (w / 2) * math.cos(a) + nx * 0.04, cy + ty * (w / 2) * math.cos(a) + ny * 0.04, cz + (h / 2) * math.sin(a)) for a in np.linspace(0, math.tau, 24, endpoint=False)]
    quad(m, pts, (nx, ny, 0), 'mirror')
    ring = []
    for k in range(24):
        a0, a1 = math.tau * k / 24, math.tau * (k + 1) / 24
        def p(a, s, d): return (cx + tx * (w / 2 * s) * math.cos(a) + nx * d, cy + ty * (w / 2 * s) * math.cos(a) + ny * d, cz + (h / 2 * s) * math.sin(a))
        quad(m, [p(a0, 1.0, 0.05), p(a1, 1.0, 0.05), p(a1, 1.16, 0.08), p(a0, 1.16, 0.08)], (nx, ny, 0), 'gilt')
    # crest on top
    m.merge(G.box(min(cx - tx * 0.25, cx + tx * 0.25) - abs(nx) * 0.05, min(cy - ty * 0.25, cy + ty * 0.25) - abs(ny) * 0.05, cz + h / 2 + 0.05,
                  max(cx - tx * 0.25, cx + tx * 0.25) + abs(nx) * 0.08, max(cy - ty * 0.25, cy + ty * 0.25) + abs(ny) * 0.08, cz + h / 2 + 0.35, 'gilt'))

def sconce(m, x, y, z, normal):
    nx, ny = normal
    m.merge(G.box(x - 0.04 + nx * 0.0, y - 0.04, z - 0.25, x + 0.04, y + 0.04, z + 0.1, 'gilt').transformed(np.eye(4)))
    for s in (-1, 1):
        tx, ty = -ny * s * 0.16, nx * s * 0.16
        bx, by = x + nx * 0.18 + tx, y + ny * 0.18 + ty
        m.merge(G.box(min(x, bx) - 0.015, min(y, by) - 0.015, z - 0.02, max(x, bx) + 0.015, max(y, by) + 0.015, z + 0.02, 'gilt'))
        m.merge(G.lathe([(0.0, 0), (0.035, 0.0), (0.075, 0.13), (0.06, 0.16)], 8, mat='lamp_glass', center=(bx, by, z + 0.02)))

def chandelier(m, x, y, z):
    m.merge(G.box(x - 0.02, y - 0.02, z, x + 0.02, y + 0.02, H - 0.02, 'gilt'))
    m.merge(G.lathe([(0.0, 0), (0.12, 0.05), (0.1, 0.18), (0.0, 0.25)], 10, mat='gilt', center=(x, y, z - 0.2)))
    for k in range(6):
        a = math.tau * k / 6
        bx, by = x + 0.38 * math.cos(a), y + 0.38 * math.sin(a)
        m.merge(G.box(min(x, bx) - 0.012, min(y, by) - 0.012, z - 0.1, max(x, bx) + 0.012, max(y, by) + 0.012, z - 0.07, 'gilt'))
        m.merge(G.lathe([(0.0, 0), (0.03, 0.0), (0.07, 0.12), (0.055, 0.15)], 8, mat='lamp_glass', center=(bx, by, z - 0.07)))

def banquette(m, x0, x1, y0, y1, side):
    """red velvet banquette against a side wall at x0 (side=+1, seat toward +x) or x1 (side=-1)."""
    d = 0.55
    if side > 0: a, b = x0, x0 + d
    else: a, b = x1 - d, x1
    m.merge(G.box(a, y0, 0.0, b, y1, 0.14, 'walnut'))
    m.merge(G.box(a, y0, 0.14, b, y1, 0.46, 'velvet'))
    bk0, bk1 = (x0, x0 + 0.14) if side > 0 else (x1 - 0.14, x1)
    m.merge(G.box(bk0, y0, 0.46, bk1, y1, 1.12, 'velvet'))
    m.merge(G.box(bk0 - 0.01, y0, 1.12, bk1 + 0.01, y1, 1.17, 'walnut'))

def table(m, x, y, rect=True):
    if rect:
        m.merge(G.box(x - 0.28, y - 0.36, 0.72, x + 0.28, y + 0.36, 0.76, 'marble_white'))
        m.merge(G.box(x - 0.25, y - 0.33, 0.62, x + 0.25, y + 0.33, 0.72, 'walnut'))
        for sx in (-1, 1):
            for sy in (-1, 1):
                m.merge(G.lathe([(0.025, 0), (0.03, 0.3), (0.022, 0.5), (0.03, 0.62)], 6, mat='walnut', center=(x + sx * 0.22, y + sy * 0.29, 0)))
    else:
        m.merge(G.lathe([(0.0, 0.73), (0.32, 0.73), (0.32, 0.765), (0.0, 0.765)], 14, mat='marble_white', center=(x, y, 0)))
        m.merge(G.lathe([(0.18, 0.0), (0.05, 0.08), (0.035, 0.4), (0.05, 0.66), (0.12, 0.73)], 8, mat='cast_iron', center=(x, y, 0)))

def chair(m, x, y, facing):
    """cane-back wooden chair; facing = +-1 along x (the sitter looks toward +x * facing)."""
    m.merge(G.box(x - 0.21, y - 0.21, 0.44, x + 0.21, y + 0.21, 0.48, 'walnut'))
    m.merge(G.box(x - 0.19, y - 0.19, 0.48, x + 0.19, y + 0.19, 0.5, 'linen'))
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.merge(G.box(x + sx * 0.18 - 0.02, y + sy * 0.18 - 0.02, 0.0, x + sx * 0.18 + 0.02, y + sy * 0.18 + 0.02, 0.44, 'walnut'))
    bx = x - facing * 0.2
    m.merge(G.box(bx - 0.025, y - 0.2, 0.48, bx + 0.025, y + 0.2, 0.95, 'walnut'))
    m.merge(G.box(bx - 0.03, y - 0.15, 0.6, bx + 0.035, y + 0.15, 0.88, 'linen'))

def tableware(m, x, y):
    m.merge(G.lathe([(0.0, 0), (0.06, 0.0), (0.065, 0.005), (0.0, 0.006)], 12, mat='mirror', center=(x, y, 0.765)))
    m.merge(G.lathe([(0.0, 0), (0.025, 0.0), (0.035, 0.05), (0.0, 0.048)], 10, mat='linen', center=(x + 0.02, y, 0.77)))
    m.merge(G.lathe([(0.0, 0), (0.03, 0.0), (0.034, 0.12), (0.0, 0.118)], 10, mat='glass', center=(x - 0.1, y + 0.08, 0.765)))

def room(i, W, theme):
    """one room; returns (mesh, [(painting mesh, art layer)])."""
    m = G.Mesh(); arts = []
    x0, x1 = i * W + 0.13, (i + 1) * W - 0.13
    xc = (x0 + x1) / 2
    wall = {'liberty': 'cream', 'illustri': 'walnut', 'senato': 'gilt', 'cinese': 'pale_blue', 'orientale': 'cream', 'stagioni': 'cream'}[theme]
    low = {'liberty': 'walnut', 'illustri': 'walnut', 'senato': 'walnut', 'cinese': 'walnut', 'orientale': 'walnut', 'stagioni': 'walnut'}[theme]
    floor = 'terrazzo' if theme in ('liberty', 'cinese') else 'parquet'
    m.merge(G.box(x0, Y0, -0.02, x1, Y1, 0.0, floor, faces=('+z',)))
    if theme != 'senato' or 'senato_ceiling' not in ART:            # (the Senato's painted ceiling is added in build_interior)
        m.merge(G.box(x0, Y0, H, x1, Y1, H + 0.02, 'cream' if theme != 'illustri' else 'walnut', faces=('-z',)))
    # side walls (partitions) with a doorway near the back; back wall; inner face of the shopfront wall
    door_y = (Y1 - 1.9, Y1 - 0.7)
    for (x, nrm) in ((x0, (1, 0)), (x1, (-1, 0))):
        segs = [(Y0, door_y[0], 0.0, H), (door_y[1], Y1, 0.0, H), (door_y[0], door_y[1], 2.6, H)]
        for (ya, yb, za, zb) in segs:
            quad(m, [(x, ya, za), (x, yb, za), (x, yb, zb), (x, ya, zb)], (nrm[0], 0, 0), wall)
        for (ya, yb) in ((Y0, door_y[0]), (door_y[1], Y1)):
            quad(m, [(x + nrm[0] * 0.02, ya, 0.0), (x + nrm[0] * 0.02, yb, 0.0), (x + nrm[0] * 0.02, yb, 0.95), (x + nrm[0] * 0.02, ya, 0.95)], (nrm[0], 0, 0), low)
            m.merge(G.box(min(x, x + nrm[0] * 0.06), ya, 0.95, max(x, x + nrm[0] * 0.06), yb, 1.0, 'gilt' if theme != 'illustri' else 'walnut'))
        m.merge(G.box(min(x, x + nrm[0] * 0.12), Y0, H - 0.25, max(x, x + nrm[0] * 0.12), Y1, H, 'gilt' if theme != 'illustri' else 'walnut'))
        # doorway reveal
        quad(m, [(x, door_y[0], 0), (x - nrm[0] * 0.26, door_y[0], 0), (x - nrm[0] * 0.26, door_y[0], 2.6), (x, door_y[0], 2.6)], (0, 1, 0), low)
        quad(m, [(x, door_y[1], 0), (x - nrm[0] * 0.26, door_y[1], 0), (x - nrm[0] * 0.26, door_y[1], 2.6), (x, door_y[1], 2.6)], (0, -1, 0), low)
        quad(m, [(x, door_y[0], 2.6), (x - nrm[0] * 0.26, door_y[0], 2.6), (x - nrm[0] * 0.26, door_y[1], 2.6), (x, door_y[1], 2.6)], (0, 0, -1), low)
    quad(m, [(x0, Y1, 0), (x1, Y1, 0), (x1, Y1, H), (x0, Y1, H)], (0, -1, 0), wall)
    m.merge(G.box(x0, Y1 - 0.03, 0, x1, Y1, 0.95, low))
    # inner face of the shopfront wall, with the opening (2.7 x 3.6)
    xcb = i * W + W / 2
    front = [(x0, 0), (x1, 0), (x1, H), (x0, H)]
    hole = [(xcb - 1.35, 0.0), (xcb + 1.35, 0.0), (xcb + 1.35, 3.6), (xcb - 1.35, 3.6)]
    m.merge(A.fix_orient(G.cap([front, hole], 0, wall, True, G.frame((0, Y0, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))), (0, 1, 0)))
    # furniture: banquettes along both side walls, tables, chairs facing them, tableware
    by0, by1 = Y0 + 0.5, door_y[0] - 0.15
    banquette(m, x0, x1, by0, by1, +1); banquette(m, x0, x1, by0, by1, -1)
    n = max(2, int((by1 - by0) / 1.25))
    for k in range(n):
        y = by0 + (by1 - by0) * (k + 0.5) / n
        for side in (+1, -1):
            tx = x0 + 0.55 + 0.32 if side > 0 else x1 - 0.55 - 0.32
            table(m, tx, y, rect=(theme != 'liberty'))
            chair(m, tx + side * 0.58, y, -side)
            if (k + i + (side > 0)) % 2 == 0: tableware(m, tx, y)
    # wall decoration per theme
    keys = {'liberty': ['longhi1', 'longhi2', 'longhi3', 'pescivendola'], 'illustri': [f'ui{k}' for k in range(1, 11)],
            'senato': ['progress', 'vigilance', 'charity', 'pescivendola'], 'cinese': ['chin1', 'chin2', 'chin3', 'chin4', 'chin5', 'chin3'],
            'orientale': ['orient1', 'orient2', 'orient3', 'orient1'], 'stagioni': ['spring', 'summer', 'autumn', 'winter']}[theme]
    per_side = 5 if theme == 'illustri' else 3 if theme == 'cinese' else 2
    span0, span1 = Y0 + 0.7, door_y[0] - 0.3
    kk = 0
    for (x, nrm) in ((x0, (1, 0)), (x1, (-1, 0))):
        for k in range(per_side):
            y = span0 + (span1 - span0) * (k + 0.5) / per_side
            key = keys[kk % len(keys)]; kk += 1
            if theme == 'illustri': painting(arts, key, x, y, 2.35, 1.0, 1.55, nrm, frame_mat='walnut', fw=0.02)
            elif theme == 'stagioni': painting(arts, key, x, y, 2.45, 1.05, 1.6, nrm)
            else: painting(arts, key, x, y, 2.45, 1.15, 1.45, nrm)
            if theme in ('stagioni', 'orientale', 'liberty') and k < per_side - 1:
                oval_mirror(m, x + nrm[0] * 0.01, y + (span1 - span0) / per_side * 0.5, 2.5, 0.75, 1.2, nrm)
        for yy in (span0 + 0.2, span1 - 0.2):
            sconce(m, x, yy, 2.05, nrm)
    # back wall: a large gilt-framed mirror (Orientale, Stagioni) or a painting, flanked by sconces
    if theme in ('orientale', 'stagioni', 'senato'):
        oval_mirror(m, xc, Y1 - 0.01, 2.5, 1.5, 2.0, (0, -1))
    else:
        painting(arts, keys[0], xc, Y1, 2.5, 1.6, 1.7, (0, -1), frame_mat='gilt' if theme != 'illustri' else 'walnut')
    for xx in (xc - 1.15, xc + 1.15):
        sconce(m, xx, Y1, 2.1, (0, -1))
    chandelier(m, xc, (Y0 + Y1) / 2, H - 0.75)
    return m, arts

def build_interior(mb):
    M, L, nb, W, flipped, a, b = nuove_frame()
    bays = florian_bays()
    for k, i in enumerate(bays):
        theme = THEMES[k % len(THEMES)]
        m, arts = room(i, W, theme)
        place(mb, m, M, max_edge=1.0)
        for (pm, layer) in arts:
            place(mb, pm, M, c1=(layer, 0, 0, 0), max_edge=1.0)
        if theme == 'senato' and 'senato_ceiling' in ART:
            cm = G.Mesh(); x0, x1 = i * W + 0.13, (i + 1) * W - 0.13
            o = cm.add_v([(x0, Y0, H), (x1, Y0, H), (x1, Y1, H), (x0, Y1, H)])
            cm.face([o + 3, o + 2, o + 1, o], 'painting', uv=[(0, 1), (1, 1), (1, 0), (0, 0)])
            place(mb, cm, M, c1=(ART['senato_ceiling']['layer'], 0, 0, 0), max_edge=1.0)
    return dict(rooms=len(bays))

# ------------------------------------------------------------------ terrace and orchestra stage (in the piazza)
def terrace():
    M, L, nb, W, flipped, a, b = nuove_frame()
    bays = florian_bays()
    xa, xb = min(bays) * W + 0.4, (max(bays) + 1) * W - 0.4
    m = G.Mesh()
    rows = [(-2.6), (-4.4), (-6.2), (-8.0), (-9.8)]
    stage_x = (xa + xb) / 2
    for r, y in enumerate(rows):
        x = xa + 0.6
        while x < xb - 0.6:
            if not (r >= 3 and abs(x - stage_x) < 4.5):
                table(m, x, y, rect=False)
                for (dx, dy, f) in ((-0.62, 0.0, 1), (0.62, 0.0, -1)):
                    chair(m, x + dx, y + dy, f)
                if (int(x * 3) + r) % 3 == 0: tableware(m, x + 0.05, y)
            x += 2.0
    # orchestra stage: platform, low balustrade, grand piano, chairs and music stands
    sx0, sx1, sy0, sy1 = stage_x - 3.6, stage_x + 3.6, -14.4, -10.6
    m.merge(G.box(sx0, sy0, 0.0, sx1, sy1, 0.45, 'parquet'))
    m.merge(G.box(sx0 - 0.02, sy0 - 0.02, 0.0, sx1 + 0.02, sy1 + 0.02, 0.3, 'walnut', faces=('-x', '+x', '-y', '+y')))
    for (xa_, xb_, ya_, yb_) in ((sx0, sx1, sy0, sy0 + 0.05), (sx0, sx0 + 0.05, sy0, sy1 - 0.8), (sx1 - 0.05, sx1, sy0, sy1 - 0.8)):
        m.merge(G.box(xa_, ya_, 0.45, xb_, yb_, 1.15, 'cast_iron'))
    m.merge(G.box(sx0, sy0, 1.12, sx1, sy0 + 0.08, 1.18, 'gilt'))
    # piano: case, lid open, legs
    px, py = stage_x - 1.6, sy0 + 1.6
    case = [(px - 0.75, py - 0.7), (px + 0.75, py - 0.7), (px + 0.75, py + 0.2), (px + 0.4, py + 0.9), (px - 0.1, py + 1.1), (px - 0.75, py + 0.9)]
    m.merge(G.prism([case], 1.05, 1.35, 'cast_iron', top=True, bottom=True))
    for (lx, ly) in ((px - 0.65, py - 0.6), (px + 0.65, py - 0.6), (px, py + 0.9)):
        m.merge(G.box(lx - 0.06, ly - 0.06, 0.45, lx + 0.06, ly + 0.06, 1.05, 'cast_iron'))
    lid = G.Mesh(); o = lid.add_v([(px - 0.75, py - 0.7, 1.35), (px + 0.75, py - 0.7, 1.35), (px + 0.75, py + 0.6, 2.25), (px - 0.75, py + 0.6, 2.25)])
    lid.face([o, o + 1, o + 2, o + 3], 'cast_iron'); lid.face([o + 3, o + 2, o + 1, o], 'cast_iron'); m.merge(lid)
    m.merge(G.box(px - 0.7, py - 0.95, 1.0, px + 0.7, py - 0.7, 1.08, 'linen'))                  # keys
    m.merge(G.box(px - 0.3, py - 1.35, 0.45, px + 0.3, py - 1.05, 0.95, 'velvet'))               # bench
    for k, dx in enumerate((-0.2, 0.9, 2.0, 3.0)):
        cx = stage_x + dx; cy = sy0 + 1.4 + (0.4 if k % 2 else 0)
        chair(m, cx, cy, -1)
        m.merge(G.box(cx - 0.02, cy - 0.65, 0.45, cx + 0.02, cy - 0.61, 1.65, 'cast_iron'))
        m.merge(G.box(cx - 0.25, cy - 0.66, 1.45, cx + 0.25, cy - 0.6, 1.75, 'cast_iron'))
    # double bass leaning on its stand
    bx, by = stage_x + 3.0, sy1 - 0.6
    m.merge(G.lathe([(0.0, 0.5), (0.32, 0.6), (0.36, 0.95), (0.24, 1.25), (0.3, 1.6), (0.2, 1.85), (0.04, 1.95), (0.035, 2.4), (0.0, 2.45)], 10, mat='parquet', center=(bx, by, 0.0)).transformed(G.mat4((0, 0, 0))))
    return m, M

def build_terrace(mb):
    m, M = terrace()
    place(mb, m, M)
    return dict(terrace=True)

def walk_areas():
    """rooms + doorways (walkable) inside the café; banquettes and the stage blocked, tables passable."""
    M, L, nb, W, flipped, a, b = nuove_frame()
    def wp(x, y): v = M @ np.array([x, y, 0, 1.0]); return (v[0], v[1])
    out = []
    bays = florian_bays()
    for i in bays:
        x0, x1 = i * W + 0.13, (i + 1) * W - 0.13
        out.append((Polygon([wp(x0 + 0.6, Y0 - 0.35), wp(x1 - 0.6, Y0 - 0.35), wp(x1 - 0.6, Y1 - 0.1), wp(x0 + 0.6, Y1 - 0.1)]), GROUND_Z))
        xcb = i * W + W / 2
        out.append((Polygon([wp(xcb - 0.6, Y0 - 0.9), wp(xcb + 0.6, Y0 - 0.9), wp(xcb + 0.6, Y0 + 0.3), wp(xcb - 0.6, Y0 + 0.3)]), GROUND_Z))
        # doorway through the partition to the next room
        out.append((Polygon([wp(x1 - 0.7, Y1 - 1.85), wp(x1 + 0.4, Y1 - 1.85), wp(x1 + 0.4, Y1 - 0.75), wp(x1 - 0.7, Y1 - 0.75)]), GROUND_Z))
    # tables and chairs do not block: the rooms are narrow and the visitor should get close to the paintings
    # (the banquettes along the walls stay outside the walkable floor, which keeps 0.6 m off the walls)
    # the stage
    xa, xb = min(bays) * W + 0.4, (max(bays) + 1) * W - 0.4; sx = (xa + xb) / 2
    out.append((Polygon([wp(sx - 3.7, -14.5), wp(sx + 3.7, -14.5), wp(sx + 3.7, -10.5), wp(sx - 3.7, -10.5)]), None))
    return out
