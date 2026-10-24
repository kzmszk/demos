"""Street level: ground decals (zebra crossings, lines, cracks, moss, litter) draped on the game ground."""
import math
import random
import numpy as np

from sb_mesh import MB, vnoise
from sb_tex_misc import decal_uv, DECALS
import sb_geom as G

DZ = 0.04


def drape(mb, ground, center, ax, ay, su, sv, uvf, mat='decal_ground', dz=DZ, step=1.0, col=(1, 1, 1, 1), keep=None):
    """A quad (su x sv metres, axes ax, ay unit 2D) subdivided to <= step and laid on the ground.
    uvf(s, t) with s, t in [0,1] -> uv.  keep(x, y) -> bool drops cells (e.g. inside buildings)."""
    nu = max(1, int(math.ceil(su / step)))
    nv = max(1, int(math.ceil(sv / step)))
    cx, cy = center
    P = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            s = i / nu; t = j / nv
            x = cx + ax[0] * (s - 0.5) * su + ay[0] * (t - 0.5) * sv
            y = cy + ax[1] * (s - 0.5) * su + ay[1] * (t - 0.5) * sv
            P[(i, j)] = (x, y, ground(x, y) + dz)
    for i in range(nu):
        for j in range(nv):
            if keep is not None:
                xm = cx + ax[0] * ((i + .5) / nu - 0.5) * su + ay[0] * ((j + .5) / nv - 0.5) * sv
                ym = cy + ax[1] * ((i + .5) / nu - 0.5) * su + ay[1] * ((j + .5) / nv - 0.5) * sv
                if not keep(xm, ym):
                    continue
            pts = [P[(i, j)], P[(i + 1, j)], P[(i + 1, j + 1)], P[(i, j + 1)]]
            uvs = [uvf(i / nu, j / nv), uvf((i + 1) / nu, j / nv), uvf((i + 1) / nu, (j + 1) / nv), uvf(i / nu, (j + 1) / nv)]
            # orientation: make the face point up
            a = (pts[1][0] - pts[0][0]) * (pts[3][1] - pts[0][1]) - (pts[1][1] - pts[0][1]) * (pts[3][0] - pts[0][0])
            if a < 0:
                pts = pts[::-1]; uvs = uvs[::-1]
            mb.face(pts, uvs, mat, col)


def zebra(mb, ground, a, b, width, rnd, pitch=0.9, bar=0.45, dz=DZ + 0.01, wear=0.15):
    """crosswalk from a to b (walking direction), bars across it."""
    a = np.array(a, float); b = np.array(b, float)
    d = b - a; L = float(np.hypot(*d))
    if L < 1:
        return
    d /= L
    n = np.array([-d[1], d[0]])
    nb = int(L / pitch)
    off = (L - (nb - 1) * pitch) / 2
    for k in range(nb):
        c = a + d * (off + k * pitch)
        # bar: bar (along d) x width (along n), in <= 4 m pieces
        pieces = int(math.ceil(width / 4.0))
        pl = width / pieces
        for p in range(pieces):
            if rnd.random() < wear:
                continue
            cc = c + n * (-width / 2 + (p + 0.5) * pl)
            var = rnd.choice(('zebra1', 'zebra2'))
            v0 = rnd.uniform(0, 1 - pl / 4.0) if pl < 4 else 0
            def uvf(s, t, var=var, v0=v0, pl=pl):
                return decal_uv(var, 0.05 + 0.9 * s, v0 + t * pl / 4.0)
            drape(mb, ground, cc, d, n, bar, pl, uvf, dz=dz, step=1.0)


def sheet(mb, ground, center, size, rot, name, dz=DZ, keep=None, col=(1, 1, 1, 1), step=1.0):
    ax = (math.cos(rot), math.sin(rot)); ay = (-math.sin(rot), math.cos(rot))
    def uvf(s, t):
        return decal_uv(name, s, t)
    drape(mb, ground, center, ax, ay, size, size, uvf, dz=dz, keep=keep, col=col, step=step)


SCRAMBLE = [
    # (a, b, width)  -- OSM crossings at the scramble (walking lines) + the second diagonal
    ((54.0, -39.7), (50.5, -57.1), 6.5),        # west, across Dogenzaka
    ((80.0, -31.0), (98.5, -35.2), 6.5),        # north, across Jingu-dori
    ((100.3, -63.6), (102.6, -46.0), 6.5),      # east
    ((60.5, -68.0), (86.5, -72.6), 6.5),        # south (Hachiko side)
    ((91.4, -64.8), (73.9, -38.0), 5.0),        # diagonal NNW-SSE (OSM)
    ((58.0, -60.0), (97.5, -40.0), 5.0),        # diagonal SW-NE
    ((54.0, -39.2), (66.6, -39.2), 4.0),        # Center-gai mouth
]


def build_decals(mb, ground, osm, inside_bldg, rnd):
    # scramble
    for a, b, w in SCRAMBLE:
        zebra(mb, ground, a, b, w, rnd, wear=0.2)
    # other signalised crossings in the box
    for r in osm['roads']:
        if r['footway'] != 'crossing' or r['crossing'] not in ('traffic_signals', 'marked', 'uncontrolled', 'pedestrian_signals'):
            continue
        l = np.array(r['line'])
        if not ((l[:, 0] > -150) & (l[:, 0] < 150) & (l[:, 1] > -120) & (l[:, 1] < 120)).all():
            continue
        a, b = l[0], l[-1]
        if np.hypot(*(b - a)) < 3:
            continue
        mid = (a + b) / 2
        if any(np.hypot(mid[0] - (sa[0] + sb[0]) / 2, mid[1] - (sa[1] + sb[1]) / 2) < 12 for sa, sb, _w in SCRAMBLE):
            continue
        zebra(mb, ground, a, b, 4.0, rnd, wear=0.2)
    # crack sheets and moss patches over the paved ground (outside buildings)
    keep = lambda x, y: not inside_bldg(x, y)
    for k in range(260):
        x = rnd.uniform(-150, 150); y = rnd.uniform(-120, 120)
        if inside_bldg(x, y):
            continue
        sheet(mb, ground, (x, y), 8.0, rnd.uniform(0, 6.28), rnd.choice(('cracks1', 'cracks2')), dz=DZ, keep=keep, step=2.0)
    for k in range(160):
        x = rnd.uniform(-150, 150); y = rnd.uniform(-120, 120)
        if inside_bldg(x, y):
            continue
        nm = rnd.choice(('moss1', 'moss2', 'moss1', 'leaves', 'puddle'))
        sheet(mb, ground, (x, y), rnd.uniform(1.5, 4.0), rnd.uniform(0, 6.28), nm, dz=DZ + 0.005, keep=keep, step=2.0)
