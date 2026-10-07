"""伏見稲荷大社: the furniture of the shrine — 稲荷の狐 (seated foxes with a key / jewel / scroll / rice ear in the mouth
and red bibs), lanterns (石灯籠, vermilion post lanterns, the tunnel lamps), 手水舎, お塚 clusters (steles, votive
miniature torii, little lanterns, foxes, round-stone terraces), tea houses (茶屋) with red benches and parasols, the
四ツ辻 viewpoint terrace, おもかる石."""
import math
import numpy as np
import jk
from jk import prim, arch, roof, Frame
from . import fushimi_inari_torii as FT

# ------------------------------------------------------------------ shapes
def ellipsoid(B, c, r, mat, seg=10, ring=6, tag='main', c0=(255, 255, 255, 0), yaw=0.0):
    c = np.asarray(c, float); P = []; I = []
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    for j in range(ring + 1):
        ph = -math.pi / 2 + math.pi * j / ring
        for i in range(seg):
            t = 2 * math.pi * i / seg
            x, y, z = r[0] * math.cos(ph) * math.cos(t), r[1] * math.cos(ph) * math.sin(t), r[2] * math.sin(ph)
            P.append(c + [x * cy_ - y * sy_, x * sy_ + y * cy_, z])
    for j in range(ring):
        for i in range(seg):
            a = j * seg + i; b = j * seg + (i + 1) % seg
            I += [[a, b, b + seg], [a, b + seg, a + seg]]
    B.add(np.array(P), I, mat, smooth=True, tag=tag, c0=c0)

def loft(B, pts, rads, mat, seg=10, tag='main', side=(1.0, 0.0, 0.0), caps=(True, True), c0=(255, 255, 255, 0), arc=None):
    """rings of ellipses along a spine: pts (k,3), rads [(rx, ry)] (rx along `side`, ry along T x side); arc=(a0, a1)
    for a partial ring (open)"""
    pts = np.asarray(pts, float); k = len(pts)
    T = np.gradient(pts, axis=0); T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    sd = np.asarray(side, float)
    P = []
    n = seg if arc is None else seg + 1
    for i in range(k):
        X = sd - T[i] * (sd @ T[i]); X /= max(np.linalg.norm(X), 1e-9); Y = np.cross(T[i], X)
        for j in range(n):
            t = (2 * math.pi * j / seg) if arc is None else arc[0] + (arc[1] - arc[0]) * j / seg
            P.append(pts[i] + X * rads[i][0] * math.cos(t) + Y * rads[i][1] * math.sin(t))
    I = []
    for i in range(k - 1):
        for j in range(seg):
            a = i * n + j; b = i * n + (j + 1) % n if arc is None else i * n + j + 1
            I += [[a, b, b + n], [a, b + n, a + n]]
    P = np.array(P)
    if arc is None:
        for (ci, s) in ((0, -1), (k - 1, 1)):
            if not caps[0 if ci == 0 else 1]: continue
            if min(rads[ci]) < 1e-4: continue
            cidx = len(P); P = np.vstack([P, pts[ci]])
            for j in range(seg):
                a = ci * n + j; b = ci * n + (j + 1) % n
                I += [[cidx, b, a]] if s < 0 else [[cidx, a, b]]
    # orient outward: compare the first face with the spine
    I = np.array(I)
    fn = np.cross(P[I[0][1]] - P[I[0][0]], P[I[0][2]] - P[I[0][0]])
    if fn @ (P[I[0][0]] - pts[0]) < 0 and arc is None: I = I[:, ::-1]
    if arc is not None: I = np.concatenate([I, I[:, ::-1]])
    B.add(P, I, mat, smooth=arc is None, tag=tag, c0=c0)

def lowrock(B, c, size, seed, mat='stone', tag='main', flat=0.7):
    """a low-poly river stone (80 tris)"""
    rng = np.random.default_rng(seed)
    t = (1 + 5 ** 0.5) / 2
    V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    mid = {}; F2 = []; V = list(V)
    def m(a, b):
        k = (min(a, b), max(a, b))
        if k not in mid:
            p = (np.asarray(V[a]) + np.asarray(V[b])) / 2; V.append(p / np.linalg.norm(p)); mid[k] = len(V) - 1
        return mid[k]
    for a, b_, c_ in F:
        ab, bc, ca = m(a, b_), m(b_, c_), m(c_, a)
        F2 += [[a, ab, ca], [b_, bc, ab], [c_, ca, bc], [ab, bc, ca]]
    V = np.array(V)
    V = V * (1 + 0.12 * np.sin(V @ rng.normal(0, 3, 3)))[:, None]
    V = V * [size * rng.uniform(0.85, 1.15), size * rng.uniform(0.75, 1.0), size * flat]
    V = V + np.asarray(c, float)
    B.add(V, F2, mat, smooth=True, tag=tag)

# ------------------------------------------------------------------ the fox
def fox(B, item='key', mat='stone', bib=True, s=1.0):
    """稲荷の狐: seated, chest up, long snout, pointed ears, the bushy tail standing up behind like a flame; facing +y,
    sitting on z = 0; about s m tall.  item in the mouth: key (鍵), jewel (宝珠), scroll (巻物), rice (稲穂)"""
    S_ = lambda p: np.asarray(p, float) * s
    # haunches
    for sx in (-1, 1):
        ellipsoid(B, S_((sx * 0.095, -0.06, 0.13)), S_((0.085, 0.17, 0.13)), mat, 8, 4)
        # hind paws
        ellipsoid(B, S_((sx * 0.11, 0.07, 0.025)), S_((0.04, 0.07, 0.025)), mat, 6, 2)
    # torso: from the haunches up to the neck, leaning slightly forward at the chest
    spine = [(0, -0.09, 0.06), (0, -0.07, 0.22), (0, -0.02, 0.4), (0, 0.04, 0.55), (0, 0.07, 0.66), (0, 0.09, 0.76), (0, 0.11, 0.84)]
    rads = [(0.13, 0.15), (0.125, 0.14), (0.105, 0.12), (0.088, 0.1), (0.068, 0.075), (0.055, 0.06), (0.05, 0.055)]
    loft(B, [S_(p) for p in spine], [(a * s, b * s) for a, b in rads], mat, 9, caps=(True, False))
    # head + snout + ears
    ellipsoid(B, S_((0, 0.13, 0.885)), S_((0.068, 0.085, 0.066)), mat, 10, 6)
    loft(B, [S_((0, 0.17, 0.875)), S_((0, 0.24, 0.862)), S_((0, 0.31, 0.85))], [(0.05 * s, 0.042 * s), (0.034 * s, 0.03 * s), (0.012 * s, 0.01 * s)], mat, 8, caps=(False, True))
    for sx in (-1, 1):
        b0 = S_((sx * 0.038, 0.11, 0.93)); tip = S_((sx * 0.06, 0.09, 1.05))
        P = np.array([b0 + S_((-0.03, -0.015, 0)), b0 + S_((0.03, -0.015, 0)), b0 + S_((0, 0.03, -0.01)), tip])
        B.add(P, [[0, 1, 3], [1, 2, 3], [2, 0, 3], [0, 2, 1]], mat)
    # front legs: straight, from the chest to the paws
    for sx in (-1, 1):
        loft(B, [S_((sx * 0.05, 0.08, 0.5)), S_((sx * 0.052, 0.12, 0.26)), S_((sx * 0.052, 0.155, 0.04))], [(0.034 * s, 0.03 * s), (0.026 * s, 0.024 * s), (0.024 * s, 0.022 * s)], mat, 6)
        ellipsoid(B, S_((sx * 0.052, 0.18, 0.022)), S_((0.032, 0.045, 0.022)), mat, 6, 2)
    # the tail: from the rump up behind the back, bushy, pointed
    tail = [(0, -0.22, 0.07), (0, -0.31, 0.17), (0, -0.33, 0.33), (0, -0.3, 0.5), (0, -0.23, 0.64), (0, -0.16, 0.72), (0, -0.11, 0.76)]
    trad = [(0.045, 0.04), (0.075, 0.07), (0.095, 0.085), (0.095, 0.085), (0.075, 0.065), (0.04, 0.035), (0.004, 0.004)]
    loft(B, [S_(p) for p in tail], [(a * s, b * s) for a, b in trad], mat, 9)
    # the bib (よだれかけ): red cloth hanging from the neck over the chest
    if bib:
        ring = [S_((0, 0.075, 0.74)), S_((0, 0.085, 0.6))]
        loft(B, ring, [(0.066 * s, 0.07 * s), (0.135 * s, 0.13 * s)], 'cloth', 10, tag='main', arc=(-0.15 * math.pi, 1.15 * math.pi), c0=(196, 30, 26, 0),
             side=(1.0, 0.0, 0.0))
    # the thing in the mouth
    m = S_((0, 0.29, 0.845))
    if item == 'key':
        prim.obox(B, m + S_((-0.1, 0, 0)), m + S_((0.13, 0, 0)), 0.018 * s, 0.018 * s, 'gold', tag='detail')
        prim.lathe(B, m + S_((0.15, 0, -0.035)), [(0.0, 0.0), (0.035 * s, 0.01 * s), (0.035 * s, 0.06 * s), (0.0, 0.07 * s)], 8, 'gold', tag='detail')
        prim.obox(B, m + S_((-0.1, 0, 0)), m + S_((-0.1, 0, -0.06)), 0.016 * s, 0.03 * s, 'gold', tag='detail')
    elif item == 'jewel':
        prim.lathe(B, m + S_((0, 0.015, -0.03)), [(0.0, 0.0), (0.035 * s, 0.01 * s), (0.045 * s, 0.035 * s), (0.03 * s, 0.065 * s), (0.0, 0.095 * s)], 10, 'gold', tag='detail')
    elif item == 'scroll':
        prim.cyl(B, m + S_((-0.11, 0, 0)), m + S_((0.11, 0, 0)), 0.024 * s, 0.024 * s, 8, 'white_paint', tag='detail')
        for sx in (-1, 1):
            prim.cyl(B, m + S_((sx * 0.11, 0, 0)), m + S_((sx * 0.125, 0, 0)), 0.03 * s, 0.03 * s, 8, 'gold', tag='detail')
    else:   # rice ear (稲穂): a golden sheaf drooping to one side
        loft(B, [m, m + S_((0.05, 0.03, -0.06)), m + S_((0.08, 0.05, -0.18)), m + S_((0.085, 0.06, -0.3))],
             [(0.02 * s, 0.02 * s), (0.035 * s, 0.03 * s), (0.04 * s, 0.035 * s), (0.005 * s, 0.005 * s)], 'gold', 7, tag='detail')

def fox_on_pedestal(tpls, key, x, y, z, yaw, s, mat, item, ped=0.0, B=None):
    """instance a fox (template per (mat, item, scale)); a stone pedestal of height ped (built directly)"""
    k = (mat, item, round(s, 2))
    if k not in tpls: tpls[k] = FT.Template(fox, item, mat, True, s)
    if ped > 0 and B is not None:
        w = 0.2 * s + 0.08
        with Frame(B, x, y, z, yaw):
            prim.box(B, -w * 1.15, -w * 1.5, -0.25, w * 1.15, w * 1.5, ped * 0.75, 'stone', faces='xXyYZ')
            prim.box(B, -w, -w * 1.35, ped * 0.75, w, w * 1.35, ped, 'stone', faces='xXyYZ')
    tpls[k].add(x, y, z + ped, yaw)

# ------------------------------------------------------------------ lanterns
def post_lantern(B, x, y, z, h=3.0, lit=True):
    """the vermilion post lanterns of the approach (稲荷 style): vermilion post, a hexagonal fire box with a green copper
    roof and a gilt finial"""
    prim.cyl(B, (x, y, z - 0.1), (x, y, z + 0.5), 0.3, 0.26, 6, 'stone', caps=(False, True))
    prim.cyl(B, (x, y, z + 0.5), (x, y, z + h * 0.62), 0.11, 0.1, 8, 'vermilion', caps=(False, False))
    prim.cyl(B, (x, y, z + h * 0.62), (x, y, z + h * 0.66), 0.3, 0.3, 6, 'vermilion')
    prim.cyl(B, (x, y, z + h * 0.66), (x, y, z + h * 0.84), 0.24, 0.24, 6, 'lantern_paper', caps=(False, False))
    for k in range(6):
        t = 2 * math.pi * (k + 0.5) / 6
        prim.box(B, x + 0.25 * math.cos(t) - 0.025, y + 0.25 * math.sin(t) - 0.025, z + h * 0.66, x + 0.25 * math.cos(t) + 0.025, y + 0.25 * math.sin(t) + 0.025, z + h * 0.84, 'vermilion', faces='xXyY', tag='detail')
    prim.lathe(B, (x, y, z + h * 0.84), [(0.42, 0.0), (0.44, 0.04), (0.3, 0.14), (0.08, 0.26), (0.0, 0.3)], 6, 'copper', smooth=False)
    prim.lathe(B, (x, y, z + h * 0.84 + 0.28), [(0.0, 0.0), (0.05, 0.02), (0.06, 0.08), (0.0, 0.16)], 6, 'gold', tag='detail')
    if lit: B.lamp(x, y, z + h * 0.75, 12.0, (1.0, 0.6, 0.3))

def stone_lantern(B, x, y, z, h=2.0, lit=False):
    arch.ishidoro(B, x, y, z, h)
    if lit: B.lamp(x, y, z + h * 0.64, 6.0, (1.0, 0.6, 0.3))

def small_lantern(B, x, y, z, h=0.8):
    """the little stone lanterns of the お塚"""
    prim.box(B, x - 0.1, y - 0.1, z - 0.1, x + 0.1, y + 0.1, z + h * 0.55, 'stone', faces='xXyYZ')
    prim.box(B, x - 0.13, y - 0.13, z + h * 0.55, x + 0.13, y + 0.13, z + h * 0.8, 'stone', faces='xXyYZz')
    prim.lathe(B, (x, y, z + h * 0.8), [(0.22, 0.0), (0.16, 0.08), (0.02, 0.17), (0.0, 0.2)], 4, 'stone', smooth=False)

def path_lamp(B, x, y, z, yaw):
    """the lamps on posts along the mountain tunnels (a wooden post, a white paper box, lit)"""
    prim.box(B, x - 0.05, y - 0.05, z - 0.2, x + 0.05, y + 0.05, z + 1.45, 'wood_dark', faces='xXyY')
    with Frame(B, x, y, z + 1.45, yaw):
        prim.box(B, -0.13, -0.13, 0.0, 0.13, 0.13, 0.34, 'lantern_paper', faces='xXyY', tag='detail')
        prim.box(B, -0.15, -0.15, 0.34, 0.15, 0.15, 0.38, 'black_lacquer', faces='xXyYZz')
        prim.box(B, -0.15, -0.15, -0.03, 0.15, 0.15, 0.0, 'black_lacquer', faces='xXyYZz')
    B.lamp(x, y, z + 1.62, 5.0, (1.0, 0.62, 0.32))

# ------------------------------------------------------------------ 手水舎
def chozuya(B, x, y, z, yaw):
    """手水舎: an open pavilion on four vermilion pillars, a granite basin with water, a copper-roofed 切妻"""
    with Frame(B, x, y, z, yaw):
        prim.box(B, -2.4, -1.8, -0.3, 2.4, 1.8, 0.12, 'stone', faces='xXyYZ')
        for sx in (-1, 1):
            for sy in (-1, 1):
                arch.pillar(B, sx * 1.8, sy * 1.25, 0.12, 2.9, 0.12, 'vermilion')
        for sy in (-1, 1):
            prim.obox(B, (-2.1, sy * 1.25, 2.8), (2.1, sy * 1.25, 2.8), 0.12, 0.2, 'vermilion')
        prim.obox(B, (-1.8, -1.25, 2.4), (-1.8, 1.25, 2.4), 0.1, 0.14, 'vermilion'); prim.obox(B, (1.8, -1.25, 2.4), (1.8, 1.25, 2.4), 0.1, 0.14, 'vermilion')
        roof.roof(B, 3.6, 2.5, 3.0, 0.75, kind='irimoya', cover='copper', pitch=0.6, rafter=0.3, rafter_mat='vermilion', rafter_end='white_paint', bargeboard_mat='vermilion', sori=0.25)
        prim.box(B, -1.1, -0.45, 0.12, 1.1, 0.45, 0.85, 'stone', faces='xXyYz')
        prim.box(B, -1.1, -0.45, 0.82, 1.1, -0.35, 0.85, 'stone', faces='Z'); prim.box(B, -1.1, 0.35, 0.82, 1.1, 0.45, 0.85, 'stone', faces='Z')
        prim.box(B, -1.1, -0.35, 0.82, -1.0, 0.35, 0.85, 'stone', faces='Z'); prim.box(B, 1.0, -0.35, 0.82, 1.1, 0.35, 0.85, 'stone', faces='Z')
        prim.polygon(B, [(-1.0, -0.35), (1.0, -0.35), (1.0, 0.35), (-1.0, 0.35)], 0.78, 'water')
        # a bronze dragon spout (a simple bronze head on the basin's end) and the ladle rack
        prim.lathe(B, (0.9, 0.0, 0.85), [(0.0, 0.0), (0.12, 0.05), (0.1, 0.25), (0.05, 0.4), (0.0, 0.45)], 8, 'bronze', tag='detail')
        prim.box(B, -1.0, -0.42, 0.86, 1.0, -0.38, 0.9, 'bamboo', tag='detail')
        prim.polygon(B, [(-2.4, -1.8), (2.4, -1.8), (2.4, 1.8), (-2.4, 1.8)], 0.12, 'stone', tag='walk')

# ------------------------------------------------------------------ お塚
class Otsuka:
    """お塚 clusters: steles on a terrace of round river stones, rows of votive miniature torii, little lanterns"""
    def __init__(self):
        self.mini = [FT.Template(FT.mini_torii, h) for h in (0.32, 0.5, 0.75, 1.05)]
        self.n = 0
    def cluster(self, B, S, x, y, yaw, rng, size=1.0, foxes=None):
        """a mound centred at (x, y) facing yaw (+y local = the back, the steles face -y toward the path)"""
        z = float(S.ground(x, y))
        self.n += 1
        w = rng.uniform(2.2, 4.0) * size; d = rng.uniform(1.6, 2.6) * size
        with Frame(B, x, y, z, yaw):
            F = Frame(B, x, y, z, yaw)
            # terrace: a low wall of round stones along the front and a raised bed
            h = rng.uniform(0.35, 0.7)
            prim.box(B, -w / 2, -d / 2, -0.5, w / 2, d / 2, h, 'stone', faces='xXyYZ', c0=(150, 160, 140, 0))
            for k, t in enumerate(np.arange(-w / 2 + 0.2, w / 2, 0.42)):
                lowrock(B, (t, -d / 2 + 0.05, h * 0.45), 0.24, int(rng.integers(1 << 30)), 'stone', flat=0.85)
            # steles (石碑 of the 大神), the tallest at the back centre
            ns = int(rng.integers(2, 5))
            for i in range(ns):
                sx = (i - (ns - 1) / 2) * w / max(ns, 1) * 0.8 + rng.uniform(-0.1, 0.1)
                hh = rng.uniform(0.6, 1.6) * size * (1.3 if abs(sx) < 0.4 else 1.0)
                ww = rng.uniform(0.3, 0.55) * size
                sy = d / 2 - 0.35
                with Frame(B, sx, sy, h, rng.uniform(-0.15, 0.15)):
                    prim.box(B, -ww / 2 - 0.08, -0.22, -0.05, ww / 2 + 0.08, 0.22, 0.18, 'stone')
                    P = np.array([(-ww / 2, -0.1, 0.18), (ww / 2, -0.1, 0.18), (ww / 2, -0.1, hh), (0.0, -0.1, hh + ww * 0.35), (-ww / 2, -0.1, hh),
                                  (-ww / 2, 0.1, 0.18), (ww / 2, 0.1, 0.18), (ww / 2, 0.1, hh), (0.0, 0.1, hh + ww * 0.35), (-ww / 2, 0.1, hh)])
                    I = [[0, 1, 2], [0, 2, 4], [4, 2, 3], [5, 7, 6], [5, 9, 7], [9, 8, 7],
                         [1, 6, 7], [1, 7, 2], [2, 7, 8], [2, 8, 3], [3, 8, 9], [3, 9, 4], [4, 9, 5], [4, 5, 0]]
                    B.add(P, I, 'stone', c0=(140, 140, 130, 0))
            # rows of votive torii in front of the steles
            for row in range(int(rng.integers(1, 3))):
                yy = d / 2 - 0.9 - row * 0.45
                for xx in np.arange(-w / 2 + 0.3, w / 2 - 0.2, rng.uniform(0.32, 0.5)):
                    if rng.random() < 0.25: continue
                    k = int(rng.choice(4, p=[0.35, 0.35, 0.2, 0.1]))
                    p = F.world((xx + rng.uniform(-0.05, 0.05), yy, h))
                    self.mini[k].add(p[0], p[1], p[2], yaw + rng.uniform(-0.1, 0.1))
            # little lanterns at the front corners
            for sx in (-1, 1):
                if rng.random() < 0.7: small_lantern(B, sx * (w / 2 - 0.25), -d / 2 + 0.35, h, rng.uniform(0.6, 0.95))
        if foxes is not None and rng.random() < 0.35:
            for sx in (-1, 1):
                p = F.world((sx * (w / 2 - 0.6), -d / 2 + 0.6, h))
                foxes.append((p, yaw, rng.uniform(0.35, 0.5), 'stone', ['key', 'jewel', 'scroll', 'rice'][int(rng.integers(4))], 0.25))
    def flush(self, B):
        return sum(t.flush(B) for t in self.mini)

# ------------------------------------------------------------------ 茶屋
def chaya(B, S, oid, front=None, storeys=1, ex=None, benches=3, rng=None, avoid=None):
    """a mountain tea house: wooden frame, white plaster above, glazed / shoji front, 桟瓦 入母屋, red benches (縁台)
    under red parasols (野点傘) at the front, a lantern.  avoid: a polygon (the path corridors) the house is cut back from"""
    from .fushimi_inari_halls import rect_frame, world_ring, rect_pts
    b = S.osm_building(oid)
    if b is None: return
    cx, cy, L, D, th = rect_frame(S, oid, back=front if front is not None else (0.0, 1.0))
    if avoid is not None:
        # the paths sometimes run through the mapped footprint (eaves, passages): keep the largest free rectangle
        import shapely
        us_ = np.arange(-L / 2 + 0.25, L / 2, 0.5); vs_ = np.arange(-D / 2 + 0.25, D / 2, 0.5)
        U, V = np.meshgrid(us_, vs_)
        X = cx + U * math.cos(th) - V * math.sin(th); Y = cy + U * math.sin(th) + V * math.cos(th)
        free = ~shapely.contains_xy(avoid, X, Y)
        if not free.all():
            best = (0, None); hgt = np.zeros(len(us_), int)
            for j in range(len(vs_)):
                hgt = np.where(free[j], hgt + 1, 0)
                for i in range(len(us_)):
                    h = hgt[i]
                    if h == 0: continue
                    k = i
                    while k < len(us_) and hgt[k] >= h: k += 1
                    k0 = i
                    while k0 > 0 and hgt[k0 - 1] >= h: k0 -= 1
                    area = (k - k0) * h
                    if area > best[0]: best = (area, (k0, k, j - h + 1, j + 1))
            if best[1] is None: return
            k0, k1, j0, j1 = best[1]
            u0, u1 = us_[k0] - 0.25, us_[k1 - 1] + 0.25; v0, v1 = vs_[j0] - 0.25, vs_[j1 - 1] + 0.25
            if (u1 - u0) < 4.0 or (v1 - v0) < 3.5:
                print("  chaya", oid, "dropped: the path runs through it"); return
            uc, vc = (u0 + u1) / 2, (v0 + v1) / 2
            cx, cy = cx + uc * math.cos(th) - vc * math.sin(th), cy + uc * math.sin(th) + vc * math.cos(th)
            L, D = u1 - u0, v1 - v0
            benches = min(benches, max(1, int(L / 3.5)))
    # +v away from `front`: rect_frame puts +v toward `back`; we want the front (−v) toward the path
    z0 = float(min(S.ground(cx, cy), np.min([S.ground(*p) for p in world_ring(cx, cy, th, rect_pts(-L / 2, -D / 2, L / 2, D / 2))]))) + 0.05
    zg = float(max([S.ground(*p) for p in world_ring(cx, cy, th, rect_pts(-L / 2, -D / 2, L / 2, D / 2))]))
    Lb, Db = L - 1.4, D - 1.4
    zf = max(0.3, zg - z0 + 0.15)
    with Frame(B, cx, cy, z0, th):
        prim.box(B, -Lb / 2 - 0.3, -Db / 2 - 0.3, -0.6, Lb / 2 + 0.3, Db / 2 + 0.3, zf, 'stone', faces='xXyYZ')
        prim.polygon(B, rect_pts(-Lb / 2 - 0.3, -Db / 2 - 0.3, Lb / 2 + 0.3, Db / 2 + 0.3), zf, 'stone', tag='walk')
        H = 2.9
        us = np.linspace(-Lb / 2, Lb / 2, max(2, int(Lb / 1.8)) + 1); vs = np.linspace(-Db / 2, Db / 2, max(2, int(Db / 1.8)) + 1)
        from .fushimi_inari_halls import ring_pillars, bays
        ring_pillars(B, us, vs, zf, zf + H * storeys, 0.1, 'wood_dark', base=False, inner=False)
        for (p0, p1, side) in bays(us, vs):
            for st in range(storeys):
                zb = zf + st * H
                if side == 0 and st == 0:
                    _shop_front(B, p0, p1, zb, zb + 2.1)
                    arch.infill(B, p0, p1, zb + 2.1, zb + H - 0.15, 'plaster')
                else:
                    arch.infill(B, p0, p1, zb, zb + H - 0.15, 'plaster' if (side + st) % 2 else 'board', mat='wood_dark')
        for st in range(storeys):
            arch.nageshi(B, Lb, Db, zf + (st + 1) * H - 0.05, 'wood_dark', h=0.18, w=0.1, out=0.05)
        if storeys > 1:
            # a little pent roof between the storeys
            roof.roof(B, Lb, Db, zf + H + 0.05, 0.7, kind='yosemune', cover='sangawara', pitch=0.4, rafter=0, ends=None, truncate=0.65, edge=0.18, hip=False)
        roof.roof(B, Lb, Db, zf + storeys * H + 0.1, 0.8, kind='irimoya', cover='sangawara', pitch=0.55, rafter=0, ends='oni', sori=0.15, edge=0.2)
        # a noren over the door, benches and parasols in front
        prim.box(B, -0.8, -Db / 2 - 0.06, zf + 1.4, 0.8, -Db / 2 - 0.02, zf + 2.0, 'cloth', c0=(40, 50, 120, 0), tag='detail')
        rng = rng or np.random.default_rng(oid % 1000)
        for i in range(benches):
            bx = -Lb / 2 + 1.2 + i * max(1.0, (Lb - 2.4) / max(benches - 1, 1))
            by = -Db / 2 - 1.6
            gz = float(S.ground(*Frame(B, cx, cy, z0, th).world((bx, by, 0))[:2])) - z0
            prim.box(B, bx - 0.85, by - 0.3, gz + 0.38, bx + 0.85, by + 0.3, gz + 0.45, 'cloth', c0=(196, 28, 28, 0), faces='xXyYZ')
            for sx in (-1, 1):
                for sy in (-1, 1):
                    prim.box(B, bx + sx * 0.75 - 0.03, by + sy * 0.22 - 0.03, gz - 0.1, bx + sx * 0.75 + 0.03, by + sy * 0.22 + 0.03, gz + 0.38, 'wood_dark', faces='xXyY', tag='detail')
            if i % 2 == 0:
                prim.cyl(B, (bx, by + 0.45, gz - 0.2), (bx, by + 0.45, gz + 2.25), 0.025, 0.025, 6, 'bamboo', tag='detail')
                prim.lathe(B, (bx, by + 0.45, gz + 1.95), [(0.0, 0.42), (1.2, 0.0), (1.22, -0.05)], 16, 'cloth', c0=(200, 30, 30, 0), smooth=False)
                prim.lathe(B, (bx, by + 0.45, gz + 1.95), [(1.22, -0.05), (1.2, 0.0), (0.0, 0.42)], 16, 'cloth', c0=(200, 30, 30, 0), smooth=False, tag='detail')
        # a lantern by the door (lit)
        prim.box(B, Lb / 2 - 0.5, -Db / 2 - 0.4, zf + 1.9, Lb / 2 - 0.2, -Db / 2 - 0.1, zf + 2.4, 'lantern_paper', tag='detail')
        B.lamp(*Frame(B, cx, cy, z0, th).world((Lb / 2 - 0.35, -Db / 2 - 0.25, zf + 2.15)), 6.0, (1.0, 0.6, 0.3))
    if ex is not None: ex.append(world_ring(cx, cy, th, rect_pts(-L / 2, -D / 2, L / 2, D / 2)))

def _shop_front(B, p0, p1, z0, z1):
    """a glazed / shoji shop front between two posts: a pane, a transom rail, a few mullions"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); d = p1 - p0; L = np.linalg.norm(d); d /= L
    n = np.array([d[1], -d[0]])
    a = p0 + d * 0.1 - n * 0.08; b = p1 - d * 0.1 - n * 0.08
    P = np.array([np.r_[a, z0 + 0.25], np.r_[b, z0 + 0.25], np.r_[b, z1], np.r_[a, z1]])
    I = [[0, 1, 2], [0, 2, 3]]
    if np.cross(P[1] - P[0], P[2] - P[0]) @ np.r_[n, 0] < 0: I = [[0, 2, 1], [0, 3, 2]]
    B.add(P, I, 'glass')
    prim.obox(B, np.r_[a - n * 0.02, z0 + 0.25], np.r_[b - n * 0.02, z0 + 0.25], 0.08, 0.1, 'wood_dark', tag='detail')
    prim.obox(B, np.r_[a - n * 0.02, z0 + 1.6], np.r_[b - n * 0.02, z0 + 1.6], 0.06, 0.06, 'wood_dark', tag='detail')
    for t in np.linspace(0.25, 0.75, 3):
        q = a + (b - a) * t
        prim.obox(B, np.r_[q - n * 0.02, z0 + 0.25], np.r_[q - n * 0.02, z1], 0.05, 0.05, 'wood_dark', tag='detail', ends=False)

def railing_wood(B, pts, zfun, h=1.0, mat='wood_dark'):
    """a simple wooden railing (posts + two rails) following the ground"""
    pts = [np.asarray(p, float) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; L = np.linalg.norm(b - a)
        za, zb = zfun(*a), zfun(*b)
        for t in np.arange(0, L + 0.01, 1.8):
            q = a + (b - a) * t / L; zq = za + (zb - za) * t / L
            prim.box(B, q[0] - 0.05, q[1] - 0.05, zq - 0.2, q[0] + 0.05, q[1] + 0.05, zq + h, mat, faces='xXyYZ')
        for zz in (h * 0.5, h - 0.04):
            prim.obox(B, np.r_[a, za + zz], np.r_[b, zb + zz], 0.07, 0.07, mat)
