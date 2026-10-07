"""statues_wood — aged-wood finishing for the 二十八部衆 / 風神雷神 (from the temple's official photographs):

* tints: the viewer (tools/web/statues.js) shades 'wood_natural' / 'cloth' / 'vermilion' as albedo * c0^2 * 2.2, so a
  target albedo maps to a c0 with tint_for().  Near-black aged hinoki ~0.05-0.09, lighter on worn high points,
  darker in the folds; faint polychrome only where a photo shows it; gold only for real traces.
* shading(): per-vertex cavity / convexity from the SDF (evaluated a little off the surface along the normal) that
  darkens the folds and lightens the worn ridges — the 'sculpted' look of old wood under a dim light.
* halo(): 輪光 — a thin ring on a rod with openwork flame clusters (火焔) as 2D-raster reliefs.
* rock(): 岩座 — a rugged, striated carved-rock base with flat pads under the feet, on a black lacquered plinth."""
import math
import numpy as np
from . import statues_sdf as S
from .statues_sdf import Sphere, Ellipsoid, RCone, Capsule, Box, Torus, Cyl, Plane, Fn, Inter, Union, Displace, Xf, Tube, Field, frame, rot, nrm, fbm, vnoise
from .statues_body import L, A
from . import statues_relief as RL

ALB = {'wood_natural': (0.35, 0.25, 0.16), 'cloth': (0.2, 0.1, 0.08), 'vermilion': (0.55, 0.1, 0.04)}

def tint_for(alb, mat='wood_natural'):
    """c0 (0-255) that makes the viewer render `alb` (linear albedo) with a tinted material"""
    b = np.asarray(ALB[mat], float)
    c = 255.0 * np.sqrt(np.clip(np.asarray(alb, float) / (b * 2.2), 0, 1))
    return tuple(int(round(v)) for v in c)

def wood(alb):
    return ('wood_natural', tint_for(alb) + (0,))

# the finishes seen in the photographs (linear albedo)
DARK = (0.062, 0.052, 0.045)        # aged hinoki, the body of every figure
DARKER = (0.045, 0.038, 0.034)
HAIR = (0.028, 0.026, 0.025)
ROCK = (0.078, 0.074, 0.068)         # the weathered grey of the rock and cloud bases (lighter than the figures, not pale)
ROCK2 = (0.06, 0.057, 0.052)
BOOT = (0.03, 0.028, 0.027)
EYEW = (0.17, 0.16, 0.14)
LIPS = (0.085, 0.05, 0.042)
REDT = (0.085, 0.05, 0.04)           # faint red pigment traces
GREENT = (0.055, 0.066, 0.058)       # faint green / malachite traces
WHITET = (0.11, 0.1, 0.09)           # gofun traces

def wood_palette(**over):
    from .statues_build import palette
    base = dict(skin=wood(DARK), skin2=wood(DARKER), skin3=wood((0.07, 0.058, 0.05)), hair=wood(HAIR), eye=('glass', (0, 0, 0, 0)), eyew=wood(EYEW),
                lip=wood(LIPS), teeth=wood((0.2, 0.18, 0.15)), mouth=wood((0.06, 0.03, 0.025)), nail=wood(DARKER),
                robe=wood(DARK), robe2=wood((0.058, 0.05, 0.044)), robe3=wood((0.066, 0.056, 0.048)), lining=wood(REDT),
                scarf=wood((0.066, 0.056, 0.048)), armour=wood((0.058, 0.05, 0.045)), armour2=wood((0.064, 0.055, 0.048)), armour3=wood(DARKER),
                belt=wood(DARKER), boss=wood((0.07, 0.06, 0.05)), trim='gold', gold='gold', jewel='gold', crown=wood((0.08, 0.065, 0.045)),
                halo=wood((0.06, 0.05, 0.042)), halo2='gold', shoe=wood(BOOT),
                rock=wood(ROCK), base='black_lacquer', wood=wood(DARK), rod=wood(DARKER), weapon=wood((0.07, 0.06, 0.05)),
                attr=wood((0.07, 0.06, 0.05)), attr2=wood((0.08, 0.065, 0.05)), snake=wood((0.06, 0.055, 0.045)), feather=wood(DARK),
                beard=wood((0.08, 0.072, 0.065)), cap=wood(DARK), drum=wood((0.08, 0.066, 0.05)), bag=wood(DARK), cloud=wood(ROCK), dark='black_lacquer',
                worn=wood((0.09, 0.075, 0.06)), flame=wood((0.06, 0.05, 0.042)), glass=('glass', (0, 0, 0, 0)))
    base = {k: v for k, v in base.items() if v is not None}
    for k, v in over.items():
        if isinstance(v, tuple) and len(v) == 3 and all(isinstance(x, float) for x in v): v = wood(v)
        base[k] = v
    return palette(**base)

# ---------------------------------------------------------------------------------------------- per-vertex shading
def smooth_vertex(v, T, iters=6):
    """low-pass a per-vertex value over the mesh (neighbour averaging)"""
    v = np.asarray(v, np.float32).copy(); T = np.asarray(T, np.int64)
    E = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]])
    deg = np.bincount(E[:, 0], minlength=len(v)).astype(np.float32) + np.bincount(E[:, 1], minlength=len(v)).astype(np.float32)
    deg = np.maximum(deg, 1)
    for _ in range(iters):
        acc = np.zeros_like(v)
        np.add.at(acc, E[:, 0], v[E[:, 1]]); np.add.at(acc, E[:, 1], v[E[:, 0]])
        v = 0.5 * v + 0.5 * acc / deg
    return v

def shading(field, P, N, h=0.002, T=None):
    """form-following tint multiplier for c0 (kept within +-12 %): darker deep in folds and under overhangs, lighter on
    worn ridges; smoothed over the mesh so it never breaks into blotches (the viewer squares c0)"""
    P = np.asarray(P, np.float32); N = np.asarray(N, np.float32)
    d1 = field.eval_grouped(P + N * 0.012, h)
    d2 = field.eval_grouped(P + N * 0.03, h)
    d3 = field.eval_grouped(P + N * 0.06, h)
    conv = np.clip((d1 - 0.012) / 0.012, -1.0, 1.0)            # >0 on ridges
    occ = 0.6 * np.clip((0.03 - d2) / 0.03, 0, 1) + 0.4 * np.clip((0.06 - d3) / 0.06, 0, 1)   # folds, under overhangs
    s = 1.0 + 0.06 * conv - 0.16 * occ
    if T is not None: s = smooth_vertex(s, T, 8)
    return np.clip(s, 0.88, 1.12).astype(np.float32)

def wood_c0fn(seed=0, amount=1.0):
    """per-vertex tint: c0 * the form shading (within +-12 %), plus a very faint, very low-frequency patina"""
    def fn(PP, c0, shade=None):
        P = np.asarray(PP, np.float32)
        m = 1.0 + 0.02 * amount * S.fbm(P, 0.35, 2, seed)
        if shade is not None: m = m * shade
        m = np.clip(m, 0.88, 1.12)
        base = np.asarray(c0[:3], np.float32)[None, :]
        col = base * m[:, None]
        out = np.zeros((len(P), 4), np.uint8); out[:, :3] = np.clip(col, 0, 255); out[:, 3] = c0[3] if len(c0) > 3 else 0
        return out
    return fn

# ---------------------------------------------------------------------------------------------- halo (輪光 + 火焔)
_FLAME = {}
def _tongue(cv, p0, d, L_, w, bend):
    d = np.asarray(d, float); d = d / np.linalg.norm(d); nn = np.array([d[1], -d[0]])
    pts = []; ws = []
    for t in np.linspace(0, 1, 16):
        pts.append(np.asarray(p0, float) + d * L_ * t + nn * bend * math.sin(t * math.pi * 1.5))
        ws.append(w * (1 - t) ** 0.9 + 0.0012)
    cv.stroke(pts, ws)

def flame_canvas(seed=0, px=0.0015):
    """one openwork flame cluster (火焔) as in the photographs: a thick curling scroll with flame tongues bristling up
    and out from its rim, three tall tongues on top; canvas 0.28 x 0.32 m, the base (stem) at the origin"""
    if (seed, px) in _FLAME: return _FLAME[(seed, px)]
    rng = np.random.default_rng(seed)
    cv = RL.Canvas(-0.14, -0.01, 0.14, 0.31, px)
    c = np.array([0.0, 0.1]); R0 = 0.06
    sp = RL.spiral(c, R0, 1.25, -1, -math.pi / 2, 40, shrink=0.8)
    cv.stroke(sp, np.linspace(0.013, 0.006, len(sp)))
    cv.stroke([c + np.array([0, -R0]), (0.0, 0.0)], 0.011)
    for i in range(17):
        a = math.radians(-115 + 230 * i / 16) + rng.uniform(-0.06, 0.06)
        out = np.array([math.sin(a), math.cos(a)])
        rim = c + out * (R0 + 0.004)
        L_ = (0.05 + 0.06 * math.cos(a * 0.8) ** 2) * rng.uniform(0.8, 1.15)
        _tongue(cv, rim, out * 0.55 + np.array([0, 0.45]), L_, 0.009, 0.01 * (1 if i % 2 else -1))
    for x, L_ in ((-0.02, 0.13), (0.015, 0.16), (0.045, 0.11)):
        _tongue(cv, c + np.array([x, R0 * 0.8]), (x * 2.5, 1), L_, 0.011, 0.014 * (1 if x > 0 else -1))
    cv.stroke(RL.spiral(c, 0.025, 1.0, 1, 0.5, 16, shrink=0.7), 0.006)
    D = cv.sdf()
    _FLAME[(seed, px)] = (D, cv.x0, cv.z0, px)
    return _FLAME[(seed, px)]

def halo(f, c, Rm, ring_r, lab='halo', flames=((90, 1.0), (40, 0.65), (140, 0.65)), tube=0.007, rod_to=None, scale=1.0, seed=0):
    """輪光: ring of radius ring_r in the plane of Rm (columns: right, normal(back->front), up) centred at c, flame clusters at
    the given angles (deg, 90 = top) and scales, a support rod down to rod_to"""
    c = np.asarray(c, float); Rm = np.asarray(Rm, float)
    pts = [c + Rm @ A(ring_r * math.cos(t), 0, ring_r * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 49)]
    f.add(Tube(pts, np.full(len(pts), tube)), L[lab], 0.0)
    D, x0, z0, px = flame_canvas(seed)
    rel = RL.Relief(D, x0, z0, px, 0.0, 0.003, r=0.0012)
    for (ang, sc) in flames:
        a = math.radians(ang)
        d = Rm @ A(math.cos(a), 0, math.sin(a))
        base = c + d * (ring_r - 0.006)
        # local frame of the flame: x along the ring tangent, y the ring normal, z outward from the ring centre (+ a little up)
        up = nrm(d + Rm[:, 2] * (0.35 if abs(ang - 90) > 10 else 0.0))
        xx = nrm(np.cross(Rm[:, 1], up)); yy = np.cross(up, xx)
        Rf = np.stack([xx, yy, up], 1) * (sc * scale)
        f.add(_scaled(rel, Rf, base), L[lab], 0.0)
    if rod_to is not None:
        bot = c - Rm[:, 2] * ring_r
        f.add(Tube([np.asarray(rod_to, float), bot + (np.asarray(rod_to, float) - bot) * 0.0], [0.008, 0.007]), L[lab], 0.003)

class _scaled(S.Prim):
    """prim in a scaled+rotated local frame: world = t + M @ local (M = R * s); distance scaled by s"""
    def __init__(self, p, M, t):
        self.p = p; self.M = np.asarray(M, np.float32); self.t = np.asarray(t, np.float32)
        self.Mi = np.linalg.inv(self.M).astype(np.float32); self.s = float(np.cbrt(abs(np.linalg.det(self.M))))
        c = np.array([[x, y, z] for x in (p.lo[0], p.hi[0]) for y in (p.lo[1], p.hi[1]) for z in (p.lo[2], p.hi[2])], np.float32)
        w = c @ self.M.T + self.t
        self.lo = w.min(0); self.hi = w.max(0)
    def d(self, P):
        return self.p.d((P - self.t) @ self.Mi.T) * self.s

# ---------------------------------------------------------------------------------------------- rock base (岩座)
def rock(f, rng, w, d, h, pads=(), lab='rock', z_top=0.0, lean=0.0, c=(0.0, 0.0)):
    """a carved rock: lumpy, striated, overhanging a little, top around z_top, bottom at z_top - h.
    pads: [(x, y, z, r)] flat tops where the feet stand (z = sole height)"""
    zb = z_top - h
    seed = int(rng.integers(0, 9999))
    def strata(P):
        Q = P * np.array([1.0, 1.0, 3.2], np.float32)
        ridge = 1.0 - np.abs(fbm(Q, 0.07, 3, seed + 9))
        return (0.022 * fbm(Q, 0.12, 3, seed) + 0.014 * ridge ** 3 + 0.009 * fbm(P, 0.03, 2, seed + 3) + 0.006 * np.sin(P[:, 2] * 140 + 6 * fbm(P, 0.08, 2, seed + 5))).astype(np.float32)
    cx_, cy_ = c
    lumps = [Box(A(cx_, cy_, zb + h * 0.45), A(w * 0.42, d * 0.4, h * 0.45), None, 0.05)]
    for i in range(9):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0.15, 0.42)
        p = A(cx_ + math.cos(a) * w * r, cy_ + math.sin(a) * d * r * 0.9, zb + h * rng.uniform(0.35, 0.75))
        lumps.append(Ellipsoid(p, A(rng.uniform(0.09, 0.17), rng.uniform(0.08, 0.14), h * rng.uniform(0.3, 0.55)), rot((0, 0, 1), rng.uniform(0, 3))))
    for (x, y, z, r) in pads:
        lumps.append(Ellipsoid(A(x, y, z - 0.06), A(r * 1.25, r * 1.1, 0.065), rot((0, 0, 1), rng.uniform(0, 3))))
    body = Union(lumps, 0.05)
    clip = Inter([body, Plane(A(0, 0, zb), A(0, 0, -1))])
    f.add(Displace(clip, strata, 0.055), L[lab], 0.0)
    for i in range(7):        # eroded hollows
        a = rng.uniform(0, 2 * math.pi)
        p = A(cx_ + math.cos(a) * w * 0.45, cy_ + math.sin(a) * d * 0.45, zb + h * rng.uniform(0.25, 0.7))
        f.sub(Ellipsoid(p, A(rng.uniform(0.03, 0.06), rng.uniform(0.03, 0.06), rng.uniform(0.02, 0.04)), rot((0, 0, 1), a)), 0.015)
    for (x, y, z, r) in pads:      # flat standing pads, exactly at the sole height
        f.add(Inter([Cyl(A(x, y, z - 0.05), A(x, y, z), r, 0.01), Plane(A(0, 0, zb), A(0, 0, -1))]), L[lab], 0.02)
