"""金閣寺 garden features: 龍門滝 with the 鯉魚石, 銀河泉, 巌下水 (with its little umbrella roof), 白蛇の塚 (stone pagoda on the
安民沢 islet), 榊雲 (small shrine), 富士形手水鉢 and 貴人榻 at the 夕佳亭, the 陸舟の松's props, stone steps on the hill, the low
log / bamboo rails along the paths, the 総門's stone bridge over its ditch, stone lanterns.
Garden-local coordinates (origin = the 舎利殿's centre, world axes), z absolute."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, MultiLineString, box
from shapely.ops import unary_union
from jk import prim, arch, Frame
from jk import roof as jroof
from . import kinkakuji_util as U

WD = 'wood_dark'

def lantern(B, x, y, z, h=2.0, lit=True, kind='kasuga'):
    if kind == 'yukimi':
        s = h / 1.4
        for k in range(3):
            a = 2 * math.pi * k / 3 + 0.3
            prim.cyl(B, (x + 0.35 * s * math.cos(a), y + 0.35 * s * math.sin(a), z), (x + 0.22 * s * math.cos(a), y + 0.22 * s * math.sin(a), z + 0.55 * s), 0.06 * s, 0.05 * s, 6, 'stone')
        prim.cyl(B, (x, y, z + 0.55 * s), (x, y, z + 0.65 * s), 0.32 * s, 0.32 * s, 6, 'stone')
        prim.cyl(B, (x, y, z + 0.65 * s), (x, y, z + 0.92 * s), 0.2 * s, 0.2 * s, 6, 'stone')
        if lit: prim.cyl(B, (x, y, z + 0.7 * s), (x, y, z + 0.87 * s), 0.205 * s, 0.205 * s, 6, 'lantern_paper', caps=(False, False), tag='detail')
        prim.lathe(B, (x, y, z + 0.92 * s), [(0.62 * s, 0.0), (0.6 * s, 0.06 * s), (0.3 * s, 0.22 * s), (0.08 * s, 0.32 * s), (0.1 * s, 0.4 * s), (0.0, 0.48 * s)], 6, 'stone', smooth=False)
        zl = z + 0.78 * s
    else:
        arch.ishidoro(B, x, y, z, h=h, lamp=lit)
        zl = z + h * 0.63
    if lit: B.lamp(x, y, zl, 3.5, (1.0, 0.62, 0.32))
    prim.box(B, x - 0.35, y - 0.35, z - 0.2, x + 0.35, y + 0.35, z + h * 0.8, 'stone', tag='block')

# ------------------------------------------------------------------ path rails (the low log rails along the gravel paths)
def rails(B, path, gz, h=0.45, post=1.8, mat='wood_natural', block=True):
    p, _ = U.resample(path, 0.6)
    if len(p) < 2: return
    acc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    z = np.array([float(gz(*q)) for q in p])
    for t in np.arange(0, acc[-1] + 0.01, post):
        i = min(int(np.searchsorted(acc, t)), len(p) - 1)
        prim.cyl(B, np.r_[p[i], z[i] - 0.15], np.r_[p[i], z[i] + h + 0.05], 0.05, 0.045, 6, 'wood_dark', tag='detail')
    pts = np.c_[p, z + h]
    prim.sweep(B, pts, [(0.03 * math.cos(a), 0.03 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 7)[:-1]], 'bamboo', up=(0, 0, 1), tag='detail', smooth=True)
    if block:
        for i in range(len(p) - 1):
            prim.obox(B, np.r_[p[i], z[i] + 0.5], np.r_[p[i + 1], z[i + 1] + 0.5], 0.3, 1.2, 'stone', tag='block')

def kenninji(B, path, gz, h=1.5):
    U.kenninji(B, path, lambda q: float(gz(*q)), h=h)
    p, _ = U.resample(path, 0.6)
    for i in range(len(p) - 1):
        prim.obox(B, np.r_[p[i], float(gz(*p[i])) + 0.7], np.r_[p[i + 1], float(gz(*p[i + 1])) + 0.7], 0.3, 1.6, 'stone', tag='block')

# ------------------------------------------------------------------ stone steps on the hill (OSM steps), walk ramps
def steps(B, path, gz, width=1.8, seed=0):
    U.steps_along(B, path, width, lambda x, y: float(gz(x, y)), riser=0.16, mat='stone', seed=seed)
    # rough stone edging along both sides
    p, _ = U.resample(path, 0.9)
    N, T = U.normals2(p)
    rng = np.random.default_rng(seed)
    for i in range(len(p)):
        for sg in (-1, 1):
            if rng.random() < 0.55:
                q = p[i] + N[i] * sg * (width / 2 + 0.25)
                U.rock(B, (q[0], q[1], float(gz(*q)) + 0.08), rng.uniform(0.22, 0.38), seed * 100 + i * 2 + (sg > 0), flat=0.6, sub=1, sink=0.45)

# ------------------------------------------------------------------ 龍門滝 (2.3 m) and the 鯉魚石
def ryumon(B, gz, x, y, facing, z_pool):
    """a fall over a dark rock face into a small pool; facing = direction the fall faces (radians); the 鯉魚石 (carp stone)
    leans at the foot as if leaping up"""
    with Frame(B, x, y, 0.0, facing - math.pi / 2):
        # rock face behind the fall: a stack of big stones (v+ is into the hill)
        # the dark face the water slides down (a flat-fronted stone), flanked and topped by big stones
        prim.box(B, -0.55, 0.5, z_pool - 0.2, 0.55, 1.6, z_pool + 2.3, 'stone')
        for k, (u, v, zz, s, sd) in enumerate(((-1.25, 1.1, z_pool + 1.0, 1.1, 12), (1.3, 1.2, z_pool + 1.1, 1.2, 13), (-0.3, 1.9, z_pool + 2.4, 1.0, 14),
                                               (0.9, 2.0, z_pool + 2.5, 0.9, 15), (-2.3, 0.8, z_pool + 0.6, 0.9, 16), (2.4, 0.9, z_pool + 0.6, 0.95, 17),
                                               (-1.4, 1.6, z_pool + 2.0, 0.8, 18), (1.6, 1.7, z_pool + 2.1, 0.8, 19))):
            U.rock(B, (u, v, zz), s, 7700 + sd, flat=1.1, sub=2, sink=0.4, aniso=(0.9, 0.7), mat='stone' if k % 3 else 'moss_mound')
        # the fall: a thin pale ribbon from the lip into the pool, a little foam at the foot
        lip = z_pool + 2.3
        zs = np.linspace(lip, z_pool + 0.02, 9)
        path = np.array([(0.0, 0.46 - 0.16 * ((lip - zz) / 2.3) ** 1.5, zz) for zz in zs])
        for w, off in ((0.34, 0.0), (0.16, 0.03)):
            P = np.concatenate([path + [-w / 2, -off, 0], path + [w / 2, -off, 0]]); n_ = len(path)
            I = [[i, i + n_, i + 1] for i in range(n_ - 1)] + [[i + 1, i + n_, i + n_ + 1] for i in range(n_ - 1)]
            U.oadd(B, P, I, 'white_paint', (0, -1, 0), UV=np.c_[P[:, 0], P[:, 2]])
        U.rock(B, (0.05, 0.05, z_pool + 0.05), 0.35, 7790, flat=0.5, sub=1, sink=0.3, mat='white_paint')
        # 鯉魚石: an upright stone in the pool, leaning toward the fall
        U.rock(B, (0.25, -0.35, z_pool + 0.35), 0.42, 7801, flat=1.7, sub=2, sink=0.15, aniso=(0.6, 0.45), tilt=0.25)
        # the pool: a small basin of water with stones round it
        ring_ = [(1.9 * math.cos(a) * (1.0 + 0.15 * math.sin(3 * a)), -0.8 + 1.3 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 18, endpoint=False)]
        prim.polygon(B, ring_, z_pool, 'water')
        prim.polygon(B, [(x_ * 1.02, y_ * 1.02 - 0.0) for (x_, y_) in ring_], z_pool - 0.35, 'ground', c1=(0, 0, 0, 10))
        rng = np.random.default_rng(78)
        for k, (a) in enumerate(np.linspace(0, 2 * math.pi, 14, endpoint=False)):
            if math.sin(a) > 0.6: continue
            r = 1.9 * (1.0 + 0.15 * math.sin(3 * a)) + 0.1
            U.rock(B, (r * math.cos(a), -0.8 + 1.35 * math.sin(a), z_pool + 0.05), rng.uniform(0.28, 0.5), 7810 + k, flat=0.6, sub=1, sink=0.4, mat='stone' if k % 3 else 'moss_mound')
        prim.prism(B, [(-2.4, -2.4), (2.4, -2.4), (2.4, 1.8), (-2.4, 1.8)], z_pool - 0.3, z_pool + 1.4, 'stone', tag='block')

# ------------------------------------------------------------------ springs
def gingasen(B, gz, x, y, facing):
    """銀河泉: a spring in a niche of rough stones under a flat lintel, a small pool in front"""
    z = float(gz(x, y))
    with Frame(B, x, y, z, facing - math.pi / 2):
        for k, (u, v, zz, s) in enumerate(((-0.75, 0.35, 0.35, 0.55), (0.75, 0.35, 0.35, 0.55), (-0.65, 0.95, 0.6, 0.6), (0.7, 0.9, 0.6, 0.55), (0.0, 1.1, 0.8, 0.65))):
            U.rock(B, (u, v, zz), s, 7900 + k, flat=0.9, sub=2, sink=0.3)
        prim.box(B, -0.95, 0.1, 0.92, 0.95, 0.9, 1.12, 'stone')                                 # the lintel slab
        prim.box(B, -0.45, 0.3, -0.05, 0.45, 0.9, 0.85, 'metal_dark')                          # the dark niche
        prim.polygon(B, [(-0.55, -0.6), (0.55, -0.6), (0.6, 0.3), (-0.6, 0.3)], -0.12, 'water')
        for k, u in enumerate(np.linspace(-0.8, 0.8, 5)):
            U.rock(B, (u, -0.75, 0.0), 0.22, 7910 + k, flat=0.6, sub=1, sink=0.4)
        prim.box(B, 0.95, -0.4, 0.0, 1.0, -0.36, 1.25, 'wood_natural')                          # the name post + board
        prim.box(B, 0.82, -0.42, 1.0, 1.13, -0.34, 1.35, 'wood_natural')
        prim.prism(B, [(-1.2, -1.0), (1.2, -1.0), (1.2, 1.3), (-1.2, 1.3)], -0.3, 1.2, 'stone', tag='block')

def gankasui(B, gz, x, y, facing):
    """巌下水: a spring among rocks under a small shingled umbrella roof on four posts"""
    z = float(gz(x, y))
    with Frame(B, x, y, z, facing - math.pi / 2):
        for k, (u, v, zz, s) in enumerate(((-1.0, 0.9, 0.3, 0.7), (0.8, 1.0, 0.35, 0.65), (0.0, 1.5, 0.55, 0.8), (-1.5, -0.2, 0.15, 0.45), (1.4, -0.1, 0.15, 0.5))):
            U.rock(B, (u, v, zz), s, 7950 + k, flat=0.8, sub=2, sink=0.3)
        prim.polygon(B, [(-0.7, -0.5), (0.7, -0.5), (0.8, 0.6), (-0.8, 0.6)], -0.1, 'water')
        for (u, v) in ((-1.1, -0.9), (1.1, -0.9), (1.1, 1.0), (-1.1, 1.0)):
            prim.cyl(B, (u, v, -0.1), (u, v, 1.95), 0.05, 0.05, 6, 'wood_natural')
        prim.obox(B, (-1.1, -0.9, 0.9), (1.1, -0.9, 0.9), 0.06, 0.06, 'wood_natural', tag='detail')
        prim.obox(B, (-1.1, 1.0, 0.9), (1.1, 1.0, 0.9), 0.06, 0.06, 'wood_natural', tag='detail')
        jroof.roof(B, 2.2, 1.9, 2.05, 0.55, kind='hogyo', cover='kokera', pitch=0.55, teri=1.15, sori=0.05, edge=0.12, rafter=0.0, ends=None, hip=False,
                   top=[(0.12, 0.0), (0.14, 0.08), (0.06, 0.18), (0.0, 0.2)])
        prim.prism(B, [(-1.6, -1.1), (1.6, -1.1), (1.6, 1.6), (-1.6, 1.6)], -0.3, 1.2, 'stone', tag='block')

def hakuja(B, x, y, z):
    """白蛇の塚: a five-tier stone pagoda (五輪 / 層塔 style, ~3 m) on a carved base, on its islet"""
    prim.box(B, x - 0.55, y - 0.55, z - 0.1, x + 0.55, y + 0.55, z + 0.2, 'stone')
    prim.box(B, x - 0.36, y - 0.36, z + 0.2, x + 0.36, y + 0.36, z + 0.85, 'stone')                    # 塔身 with the reliefs
    for k in range(4):
        a = k * math.pi / 2
        c, s = math.cos(a), math.sin(a)
        prim.box(B, x + c * 0.36 - 0.02 * abs(c) - 0.17 * abs(s), y + s * 0.36 - 0.02 * abs(s) - 0.17 * abs(c), z + 0.35,
                 x + c * 0.36 + 0.02 * abs(c) + 0.17 * abs(s), y + s * 0.36 + 0.02 * abs(s) + 0.17 * abs(c), z + 0.72, 'stone', tag='detail')
    zz = z + 0.85
    for k in range(5):
        r = 0.62 - 0.07 * k; h = 0.16
        prim.lathe(B, (x, y, zz), [(r * 0.98, 0.0), (r, 0.05), (r * 0.75, h), (0.0, h)], 4, 'stone', smooth=False)
        if k < 4: prim.box(B, x - 0.22 + 0.02 * k, y - 0.22 + 0.02 * k, zz + h, x + 0.22 - 0.02 * k, y + 0.22 - 0.02 * k, zz + h + 0.24, 'stone')
        zz += h + 0.24
    prim.lathe(B, (x, y, zz - 0.24), [(0.08, 0.0), (0.12, 0.08), (0.06, 0.18), (0.1, 0.28), (0.0, 0.42)], 8, 'stone')

def sakaki_shrine(B, x, y, z, facing):
    """榊雲: a small shrine on a stone base"""
    with Frame(B, x, y, z, facing - math.pi / 2):
        prim.box(B, -0.8, -0.8, -0.2, 0.8, 0.8, 0.6, 'stone')
        prim.box(B, -0.45, -0.4, 0.6, 0.45, 0.4, 1.45, WD)
        prim.box(B, -0.35, -0.42, 0.75, 0.35, -0.4, 1.35, 'wood_natural')
        jroof.roof(B, 0.9, 0.8, 1.55, 0.35, kind='kirizuma', cover='copper', pitch=0.6, teri=1.3, sori=0.05, rafter=0.0, ends=None, verge=0.25, edge=0.08)
        prim.box(B, -0.9, -0.9, -0.3, 0.9, 0.9, 1.4, 'stone', tag='block')

def fuji_chozubachi(B, x, y, z):
    """富士形手水鉢: a basin carved as Mt Fuji (a truncated cone with a water hollow), a ladle stone, stepping stones"""
    prim.lathe(B, (x, y, z), [(0.55, -0.1), (0.5, 0.15), (0.32, 0.6), (0.22, 0.75), (0.2, 0.78), (0.0, 0.78)], 12, 'stone')
    prim.cyl(B, (x, y, z + 0.74), (x, y, z + 0.79), 0.14, 0.14, 10, 'water', caps=(False, True))
    U.rock(B, (x + 0.7, y - 0.3, z + 0.05), 0.3, 7990, flat=0.5, sub=1, sink=0.4)
    prim.box(B, x - 0.6, y - 0.6, z - 0.2, x + 0.6, y + 0.6, z + 1.0, 'stone', tag='block')

def kijinto(B, x, y, z):
    """貴人榻: the flat 'nobleman's seat' stone"""
    U.rock(B, (x, y, z + 0.18), 0.9, 7995, flat=0.35, sub=2, sink=0.2, aniso=(1.4, 0.8))

# ------------------------------------------------------------------ the 総門's ditch and stone bridge
def somon_bridge(B, a, b, z_deck, w=3.2, ditch_w=2.2):
    """a granite slab bridge with low stone parapets and posts (the 総門 photo), from a to b (local 2D)"""
    a = np.asarray(a, float); b = np.asarray(b, float); d = b - a; L = float(np.linalg.norm(d)); yaw = math.atan2(d[1], d[0])
    c = (a + b) / 2
    with Frame(B, c[0], c[1], z_deck, yaw):
        # slabs, slightly arched
        for k in range(4):
            v0 = -w / 2 + k * w / 4
            prim.box(B, -L / 2, v0 + 0.01, -0.3, L / 2, v0 + w / 4 - 0.01, 0.06 + 0.02 * (k % 2), 'stone')
        prim.polygon(B, [(-L / 2, -w / 2), (L / 2, -w / 2), (L / 2, w / 2), (-L / 2, w / 2)], 0.08, 'stone', tag='walk')
        for s in (-1, 1):
            v = s * (w / 2 + 0.15)
            for u in (-L / 2 + 0.2, L / 2 - 0.2):
                prim.box(B, u - 0.17, v - 0.17, -0.2, u + 0.17, v + 0.17, 0.85, 'stone')
                prim.lathe(B, (u, v, 0.85), [(0.17, 0.0), (0.1, 0.12), (0.0, 0.16)], 4, 'stone', smooth=False)
            pts = np.array([(u, v, 0.55 + 0.06 * math.cos(math.pi * u / L)) for u in np.linspace(-L / 2 + 0.35, L / 2 - 0.35, 9)])
            prim.sweep(B, pts, [(-0.1, -0.12), (0.1, -0.12), (0.1, 0.08), (-0.1, 0.08)], 'stone', up=(0, 0, 1), caps=True)
            for u in np.linspace(-L / 2 + 0.6, L / 2 - 0.6, 3):
                prim.box(B, u - 0.07, v - 0.07, 0.06, u + 0.07, v + 0.07, 0.5, 'stone', tag='detail')
            prim.obox(B, (-L / 2, v, 0.5), (L / 2, v, 0.5), 0.3, 1.2, 'stone', tag='block')
