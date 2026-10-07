"""京町家 / お茶屋 generator: a detailed town house fitted to a PLATEAU footprint (reusable by every street site).

    import sites.machiya as M
    info = M.build(B, ring, street_edge, z0, height, storeys, style={...}, seed=0)

ring         the footprint, outer ring [(x, y), ...] in world metres (PLATEAU poly[0][0]); any shape, any orientation
street_edge  ((x0, y0), (x1, y1)): two points along the street front (order free; the street is the side away from the
             footprint).  The facade plane is the footprint's front-most line parallel to this edge.
z0           ground at the front (T.P., m)                         height  ridge above z0 (PLATEAU measured height)
storeys      PLATEAU storeys (0 = unknown: from the height)        seed    variation (bays, colours, which details)
style        dict, every key optional (defaults below; DEFAULT_STYLE documents them).  Main switch: kind =
             'ochaya'  総二階 tea house: 1F 千本格子 / 出格子, 一文字瓦の庇, 2F 縁 with board railing + 簾, 桟瓦 roof
             'tsushi'  厨子二階 machiya: low plastered 2F with 虫籠窓, deep eaves
             'sangai'  three storeys (2F as ochaya, 3F windows + 簾)
             'hiraya'  one storey
             'shop'    street shop: glazed shop front, sign boards, deep 庇, lattice / glazed upper floor
             back = 'plain' | 'canal' (rear rooms over a canal: balconies, glazed lattice, 簾, posts down to the water)

More style keys (see DEFAULT_STYLE): front1='redwall' / upper='itagoshi' (一力-type fronts), facade_edges (corner houses:
extra dressed fronts along other streets, limited to the front block), facade=False (rear blocks), z1 (uniform 庇 line
along a 重伝建 street), ground=z(x, y) (sloping lots: side / back walls reach down to the terrain), back='canal'.

Returns a dict: frame (ox, oy, yaw), W (frontage), D (depth), z_wp (main eave wall plate, local), z_ridge, z_hisashi,
ring_local, front_u (u0, u1) and 'lamps' (world positions of the lanterns).  Geometry tags: 'main' for walls, roofs,
lattice backings; 'detail' for slats, railings, brackets, sudare, noren; plus a 'block' footprint polygon.

Local frame: u along the front (0..W), v into the building (front plane v = 0, the street at v < 0), z up from z0.
Lattices are batched thin boxes without end caps (one B.add per lattice).  The helpers (bars, lattice, inuyarai,
komayose, hisashi, sudare, board_railing, noren, chochin, nameboard, wall_holes, RoofField) work in any Frame and are
used by the Gion landmarks too (一力亭, 南座, the shrine)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, box as sbox, LineString
from jk import prim
from jk.core import Frame

DEFAULT_STYLE = dict(
    kind='ochaya',
    wall=None,              # 2F plaster tint (sRGB); None: by seed from WALLS (聚楽 ochre / cream / white)
    wood='dark',            # timber colour: 'dark' (黒/焦茶) | 'bengara' (弁柄 red-brown lattice and posts)
    lattice='senbon',       # 1F lattice: 'senbon' 千本格子 (fine) | 'sakaya' 酒屋格子 (coarse) | 'none'
    degoshi=None,           # 出格子 bays (None: by seed)
    inuyarai=None,          # 犬矢来 at the foot (None: by seed); 'plank' = black plank slope (一力)
    komayose=None,          # 駒寄せ fence (None: by seed)
    hisashi=True,           # 一文字瓦の庇 over the ground floor
    railing=None, sudare=None,  # ochaya 2F board railing and bamboo blinds (None: by kind/seed)
    noren=None,             # door curtain tint (sRGB) or False; None: by seed
    chochin=None,           # entrance lantern (lit)
    nameboard=True,
    party='wall_plaster',   # side walls: 'wall_plaster' | 'wall_board' | 'wall_earth'
    party_tint=None,
    back='plain',           # 'plain' | 'canal'
    back_o=None,            # rear eave overhang (m); default 0 (0.7 for canal)
    roof='kawara',          # main roof cover: 'kawara' (桟瓦) | 'hongawara'
    eave=None,              # main eave overhang (m)
    z_wp=None,              # main wall plate height (local m), overrides the kind default
    sign=None,              # shop: sign board tint
    lamps=True,             # add B.lamp for lanterns
    front1='bays',          # ground floor front: 'bays' (lattice / 出格子 / door) | 'redwall' (一力: 弁柄 plaster panels on a black skirt)
    door=None,              # door bay index (None: by seed; -1: no door on this front)
    upper=None,             # 2F front override: None (by kind) | 'itagoshi' (board lattice screen, 一力)
    skirt=1.1,              # redwall: height of the black board skirt
    z1=None,                # 1F beam height (the 庇 line); a street with uniform 庇 (新橋通) passes one value
    facade=True,            # False: no street front (a rear block: walls all round, roof only)
    facade_edges=(),        # extra fronts (corner houses): world segments ((x0, y0), (x1, y1)) along footprint edges
    facade_style=None,      # style overrides for those extra fronts
    ground=None,            # optional z(x, y) (T.P.): on sloping lots the side / back walls reach down to the ground
)

WALLS = [(205, 168, 98), (196, 156, 92), (214, 186, 128), (222, 206, 172), (232, 224, 204), (188, 150, 96), (226, 214, 186)]
NOREN = [(36, 40, 92), (122, 32, 30), (30, 30, 34), (92, 26, 40), (60, 70, 52), (178, 150, 104), (44, 58, 96)]
BENGARA_LIN = (0.155, 0.026, 0.017)       # 弁柄 as linear rgb (what the eye should read)

def s2l(c): c = np.asarray(c, float) / 255.0; return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def l2s(c): c = np.clip(np.asarray(c, float), 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055) * 255.0

def paint_tint(target_srgb, base=(0.55, 0.10, 0.04)):
    """c0 tint for the 'vermilion' paint so that it reads as target (sRGB 0-255): the shader multiplies albedo by tint"""
    t = s2l(target_srgb) / np.asarray(base)
    t = t / max(1.0, t.max())
    return tuple(int(round(v)) for v in l2s(t)) + (0,)

BENGARA_TINT = paint_tint((112, 46, 34))

# ------------------------------------------------------------------ batched primitives
def bars(B, P0, P1, a, w, d, mat, tag='detail', hide=None, caps=False, **kw):
    """many thin boxes in one add: bar i from P0[i] to P1[i], section w along unit vector `a` x d along (axis x a).
    hide: a direction (local) — the long face whose normal points that way is left out (the back of a lattice slat
    against a backing, e.g. hide=(0, 1, 0)).  No end caps unless caps=True."""
    P0 = np.asarray(P0, float).reshape(-1, 3); P1 = np.asarray(P1, float).reshape(-1, 3)
    n = len(P0)
    if n == 0: return
    w = np.broadcast_to(np.asarray(w, float), (n,)); d = np.broadcast_to(np.asarray(d, float), (n,))
    ax = P1 - P0; L = np.linalg.norm(ax, axis=1, keepdims=True); ok = L[:, 0] > 1e-6
    if not ok.all():
        P0, P1, ax, L, w, d = P0[ok], P1[ok], ax[ok], L[ok], w[ok], d[ok]; n = len(P0)
        if n == 0: return
    ax = ax / L
    A = np.broadcast_to(np.asarray(a, float).reshape(-1, 3), (n, 3)).copy()
    A = A - (A * ax).sum(1, keepdims=True) * ax
    bad = np.linalg.norm(A, axis=1) < 1e-6
    if bad.any(): A[bad] = np.cross(ax[bad], [0.0, 0.0, 1.0]) if abs(ax[bad][0, 2]) < 0.9 else np.cross(ax[bad], [1.0, 0.0, 0.0])
    A /= np.maximum(np.linalg.norm(A, axis=1, keepdims=True), 1e-9)
    Bv = np.cross(ax, A)
    w = w[:, None, None]; d = d[:, None, None]
    sa = np.array([-1, 1, 1, -1], float)[None, :, None]; sb = np.array([-1, -1, 1, 1], float)[None, :, None]
    C0 = P0[:, None, :] + A[:, None, :] * sa * w / 2 + Bv[:, None, :] * sb * d / 2
    C1 = C0 + (P1 - P0)[:, None, :]
    V = np.concatenate([C0, C1], 1)
    fn = [-Bv[0], A[0], Bv[0], -A[0]]
    T = []
    for f in range(4):
        if hide is not None and float(np.dot(fn[f], hide)) > 0.7: continue
        i, j = f, (f + 1) % 4
        T += [[i, j, j + 4], [i, j + 4, i + 4]]
    if caps: T += [[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7]]
    T = np.array(T)
    I = (np.arange(n)[:, None, None] * 8 + T[None]).reshape(-1, 3)
    B.add(V.reshape(-1, 3), I, mat, tag=tag, **kw)

def oquad(B, P, normal, mat, tag='main', uv=None, **kw):
    """a quad oriented to face `normal`"""
    P = np.asarray(P, float)
    fn = np.cross(P[1] - P[0], P[2] - P[0])
    I = [[0, 1, 2], [0, 2, 3]] if fn @ np.asarray(normal, float) >= 0 else [[0, 2, 1], [0, 3, 2]]
    B.add(P, I, mat, UV=uv, tag=tag, **kw)

def quad(B, p0, p1, p2, p3, mat, tag='main', uv=None, **kw):
    """one quad (counter-clockwise seen from its front)"""
    P = np.array([p0, p1, p2, p3], float)
    B.add(P, [[0, 1, 2], [0, 2, 3]], mat, UV=uv, tag=tag, **kw)

def quads(B, Q, mat, tag='main', UV=None, **kw):
    """many quads (k, 4, 3) in one add"""
    Q = np.asarray(Q, float).reshape(-1, 4, 3)
    if len(Q) == 0: return
    I = (np.arange(len(Q))[:, None, None] * 4 + np.array([[0, 1, 2], [0, 2, 3]])[None]).reshape(-1, 3)
    B.add(Q.reshape(-1, 3), I, mat, UV=None if UV is None else np.asarray(UV, float).reshape(-1, 2), tag=tag, **kw)

def front_rect(B, u0, u1, z0, z1, v, mat, tag='main', facing=-1, **kw):
    """an axis-aligned rectangle in a plane of constant v facing -v (facing=-1, the street) or +v; uv (u, z)"""
    if u1 - u0 < 1e-4 or z1 - z0 < 1e-4: return
    if facing < 0: P = [(u0, v, z0), (u1, v, z0), (u1, v, z1), (u0, v, z1)]; UV = [(u0, z0), (u1, z0), (u1, z1), (u0, z1)]
    else: P = [(u1, v, z0), (u0, v, z0), (u0, v, z1), (u1, v, z1)]; UV = [(-u1, z0), (-u0, z0), (-u0, z1), (-u1, z1)]
    B.add(np.array(P, float), [[0, 1, 2], [0, 2, 3]], mat, UV=np.array(UV, float), tag=tag, **kw)

def side_rect(B, v0, v1, z0, z1, u, mat, facing=-1, tag='main', **kw):
    """rectangle in a plane of constant u facing -u (facing=-1) or +u"""
    if v1 - v0 < 1e-4 or z1 - z0 < 1e-4: return
    if facing < 0: P = [(u, v1, z0), (u, v0, z0), (u, v0, z1), (u, v1, z1)]
    else: P = [(u, v0, z0), (u, v1, z0), (u, v1, z1), (u, v0, z1)]
    B.add(np.array(P, float), [[0, 1, 2], [0, 2, 3]], mat, UV=np.array([(P[k][1], P[k][2]) for k in range(4)]), tag=tag, **kw)

def hbox(B, u0, u1, v0, v1, z0, z1, mat, tag='main', faces='all', **kw):
    prim.box(B, min(u0, u1), min(v0, v1), min(z0, z1), max(u0, u1), max(v0, v1), max(z0, z1), mat, tag=tag, faces=faces, **kw)

def wall_holes(B, u0, u1, z0, z1, v, holes, mat, tag='main', facing=-1, **kw):
    """a wall rectangle at plane v with rectangular holes [(hu0, hu1, hz0, hz1)] (non-overlapping), split into quads"""
    holes = sorted([h for h in holes if h[1] > u0 and h[0] < u1], key=lambda h: h[0])
    if not holes:
        front_rect(B, u0, u1, z0, z1, v, mat, tag, facing, **kw); return
    zs = sorted(set([z0, z1] + [h[2] for h in holes] + [h[3] for h in holes]))
    for za, zb in zip(zs[:-1], zs[1:]):
        if zb - za < 1e-4: continue
        cuts = [(h[0], h[1]) for h in holes if h[2] <= za + 1e-6 and h[3] >= zb - 1e-6]
        ua = u0
        for (ha, hb) in cuts:
            front_rect(B, ua, max(ua, ha), za, zb, v, mat, tag, facing, **kw); ua = max(ua, hb)
        front_rect(B, ua, u1, za, zb, v, mat, tag, facing, **kw)

# ------------------------------------------------------------------ facade parts (local frame, street at -v)
def lattice(B, u0, u1, z0, z1, v, pitch=0.046, sw=0.026, sd=0.04, mat='wood_dark', back='black_lacquer', back_dv=0.07,
            rails=True, mid=True, tag='detail', c0=(255, 255, 255, 0), skip_back=True):
    """千本格子: vertical slats at plane v (front faces at v - sd/2) between u0..u1, z0..z1; a dark backing behind
    (main tag: what the far view keeps); rails top and bottom; a thin 貫 behind at 2/3"""
    if u1 - u0 < 0.1 or z1 - z0 < 0.1: return
    n = max(1, int((u1 - u0) / pitch))
    us = u0 + (np.arange(n) + 0.5) * (u1 - u0) / n
    P0 = np.c_[us, np.full(n, v), np.full(n, z0)]; P1 = np.c_[us, np.full(n, v), np.full(n, z1)]
    bars(B, P0, P1, (1, 0, 0), sw, sd, mat, tag=tag, hide=(0, 1, 0) if skip_back else None, c0=c0)
    if back: front_rect(B, u0, u1, z0, z1, v + back_dv, back, tag='main')
    if rails:
        bars(B, [(u0, v - 0.005, z0 + 0.025), (u0, v - 0.005, z1 - 0.025)], [(u1, v - 0.005, z0 + 0.025), (u1, v - 0.005, z1 - 0.025)],
             (0, 0, 1), 0.05, sd + 0.02, mat, tag=tag, hide=(0, 1, 0), c0=c0)
    if mid:
        zm = z0 + (z1 - z0) * 0.62
        bars(B, [(u0, v + sd * 0.5 + 0.008, zm)], [(u1, v + sd * 0.5 + 0.008, zm)], (0, 0, 1), 0.03, 0.016, mat, tag=tag, c0=c0)

def side_lattice(B, v0, v1, z0, z1, u, pitch=0.05, sw=0.026, sd=0.04, mat='wood_dark', tag='detail', c0=(255, 255, 255, 0)):
    """lattice in a plane of constant u (the cheeks of a 出格子)"""
    n = max(1, int(abs(v1 - v0) / pitch))
    vs = v0 + (np.arange(n) + 0.5) * (v1 - v0) / n
    bars(B, np.c_[np.full(n, u), vs, np.full(n, z0)], np.c_[np.full(n, u), vs, np.full(n, z1)], (0, 1, 0), sw, sd, mat, tag=tag, c0=c0)

def inuyarai(B, u0, u1, h=0.95, out=0.45, v=0.0, seg=6, tag='main', kind='bamboo'):
    """犬矢来: a curved bamboo apron along the wall foot (convex, from `out` in front of the wall at the ground up to
    the wall at h); kind 'plank' = a straight black plank slope (一力亭)"""
    if u1 - u0 < 0.2: return
    if kind in ('plank', 'slope'):
        mt = 'wood_dark' if kind == 'plank' else 'bamboo'
        quad(B, (u0, v - out, 0.0), (u1, v - out, 0.0), (u1, v - 0.02, h), (u0, v - 0.02, h), mt, tag=tag,
             uv=np.array([(u0 * 3, 0), (u1 * 3, 0), (u1 * 3, 1.2), (u0 * 3, 1.2)]))
        if kind == 'slope':
            bars(B, [(u0, v - out * 0.62 - 0.015, h * 0.38), (u0, v - out * 0.25 - 0.015, h * 0.75)], [(u1, v - out * 0.62 - 0.015, h * 0.38), (u1, v - out * 0.25 - 0.015, h * 0.75)], (0, 0, 1), 0.03, 0.025, 'bamboo', tag='detail')
            return
        n = max(1, int((u1 - u0) / 0.11))
        us = u0 + (np.arange(n) + 0.5) * (u1 - u0) / n
        s = np.array([0.0, out - 0.02, -h]); s /= np.linalg.norm(s)
        bars(B, np.c_[us, np.full(n, v - out - 0.012), np.full(n, 0.0)], np.c_[us, np.full(n, v - 0.03), np.full(n, h - 0.01)], (1, 0, 0), 0.05, 0.02, 'wood_dark', tag='detail', hide=(0, 1, 0))
        side_rect(B, v - out, v, 0, h * 0.02 + 0.01, u0, 'wood_dark')
        return
    th = np.linspace(0, math.pi / 2, seg + 1)
    pv = v - out * np.cos(th); pz = h * np.sin(th)
    nu = max(1, int((u1 - u0) / 1.2))
    us = np.linspace(u0, u1, nu + 1)
    P = []; UV = []
    s = np.r_[0, np.cumsum(np.hypot(np.diff(pv), np.diff(pz)))]
    for j in range(seg + 1):
        for i in range(nu + 1):
            P.append((us[i], pv[j], pz[j])); UV.append((us[i] * 3.0, s[j]))
    I = []
    for j in range(seg):
        for i in range(nu):
            a = j * (nu + 1) + i
            I += [[a, a + 1, a + nu + 2], [a, a + nu + 2, a + nu + 1]]
    B.add(np.array(P), I, 'bamboo', UV=np.array(UV), tag=tag, smooth=True)
    # binding rods (割竹の押縁) and the foot rail
    for t in (0.28, 0.62):
        k = t * (seg); j = int(k); f = k - j
        pp = (pv[j] * (1 - f) + pv[min(j + 1, seg)] * f - 0.012, pz[j] * (1 - f) + pz[min(j + 1, seg)] * f)
        bars(B, [(u0, pp[0], pp[1])], [(u1, pp[0], pp[1])], (0, 0, 1), 0.03, 0.02, 'bamboo', tag='detail')
    bars(B, [(u0, v - out, 0.03)], [(u1, v - out, 0.03)], (0, 0, 1), 0.06, 0.05, 'bamboo', tag='detail')

def komayose(B, u0, u1, v=-0.45, h=1.0, pitch=0.13, tag='detail', mat='wood_dark', post=1.8):
    """駒寄せ: a low fence of vertical bars in front of the facade (posts, top and bottom rails)"""
    if u1 - u0 < 0.3: return
    n = max(1, int((u1 - u0) / pitch))
    us = u0 + (np.arange(n) + 0.5) * (u1 - u0) / n
    bars(B, np.c_[us, np.full(n, v), np.full(n, 0.06)], np.c_[us, np.full(n, v), np.full(n, h - 0.04)], (1, 0, 0), 0.04, 0.04, mat, tag=tag)
    bars(B, [(u0, v, h), (u0, v, 0.14)], [(u1, v, h), (u1, v, 0.14)], (0, 0, 1), (0.07, 0.05), (0.09, 0.06), mat, tag=tag, caps=True)
    np_ = max(1, int(round((u1 - u0) / post)))
    ps = np.linspace(u0, u1, np_ + 1)
    bars(B, np.c_[ps, np.full(len(ps), v), np.zeros(len(ps))], np.c_[ps, np.full(len(ps), v), np.full(len(ps), h + 0.05)], (1, 0, 0), 0.09, 0.09, mat, tag='main', caps=True)
    # the returns to the wall at both ends
    bars(B, [(u0, v, h), (u1, v, h)], [(u0, -0.02, h), (u1, -0.02, h)], (0, 0, 1), 0.07, 0.06, mat, tag=tag)

def hisashi(B, u0, u1, z_edge, depth=0.9, pitch=0.4, v=0.0, brackets=(), tag='main', ends=True, roof='kawara', manju=False):
    """一文字瓦の庇: a lean-to of tiles from the wall (at v) out to v - depth; the edge at z_edge; soffit with rafters,
    the 一文字 edge and fascia, a flashing at the wall, 腕木 brackets at the given u.  Returns the height at the wall."""
    zw = z_edge + pitch * depth
    sl = math.hypot(1, pitch)
    # tiles (uv: u along the eave, v up the slope)
    quad(B, (u0, v - depth, z_edge), (u1, v - depth, z_edge), (u1, v, zw), (u0, v, zw), roof, tag=tag,
         uv=np.array([(u0, 0), (u1, 0), (u1, depth * sl), (u0, depth * sl)]))
    th = 0.16
    # edge: tile line + fascia
    front_rect(B, u0, u1, z_edge - 0.06, z_edge, v - depth, roof, tag=tag)
    front_rect(B, u0, u1, z_edge - th, z_edge - 0.06, v - depth + 0.01, 'eave_wood', tag=tag, c1=(0, 1, 0, 0))
    # soffit (rafters drawn by the eave_wood program)
    quad(B, (u0, v - depth + 0.01, z_edge - th), (u0, v, zw - th), (u1, v, zw - th), (u1, v - depth + 0.01, z_edge - th), 'eave_wood', tag=tag,
         c1=(0, 2, 0, 0), uv=np.array([(u0, 0), (u0, depth), (u1, depth), (u1, 0)]))
    # flashing (水切り) where the tiles meet the wall
    bars(B, [(u0, v - 0.05, zw + 0.03)], [(u1, v - 0.05, zw + 0.03)], (0, 0, 1), 0.08, 0.1, 'ridge', tag='detail')
    if manju:
        # 饅頭 round tile ends along the edge (one batched lathe)
        n = max(1, int((u1 - u0) / 0.29))
        us = u0 + (np.arange(n) + 0.5) * (u1 - u0) / n
        seg = 7; r = 0.055
        ang = np.linspace(0, 2 * math.pi, seg + 1)[:-1]
        ring = np.c_[np.cos(ang) * r, np.zeros(seg), np.sin(ang) * r]
        V = []; I = []
        for k, u in enumerate(us):
            c = np.array([u, v - depth - 0.02, z_edge + 0.02])
            base = len(V)
            V += list(c + ring) + list(c + ring + [0, 0.12, 0.05]) + [c]
            for i in range(seg):
                j = (i + 1) % seg
                I += [[base + i, base + j, base + seg + j], [base + i, base + seg + j, base + seg + i], [base + 2 * seg, base + j, base + i]]
        B.add(np.array(V), np.array(I), roof, tag='detail')
    if ends:
        for (u, s) in ((u0, -1), (u1, 1)):
            P = np.array([(u, v - depth, z_edge - th), (u, v, zw - th), (u, v, zw), (u, v - depth, z_edge)])
            I = [[0, 1, 2], [0, 2, 3]] if s > 0 else [[0, 2, 1], [0, 3, 2]]
            B.add(P, I, 'wood_dark', tag='detail')
    if len(brackets):
        bu = np.asarray(brackets, float)
        bars(B, np.c_[bu, np.full(len(bu), v), np.full(len(bu), zw - th - 0.12)], np.c_[bu, np.full(len(bu), v - depth + 0.08), np.full(len(bu), z_edge - th - 0.06)],
             (1, 0, 0), 0.07, 0.1, 'wood_dark', tag='detail', caps=True)
        # 出桁 beam along the front under the brackets' ends
        bars(B, [(u0, v - depth + 0.12, z_edge - th - 0.05)], [(u1, v - depth + 0.12, z_edge - th - 0.05)], (0, 0, 1), 0.1, 0.09, 'wood_dark', tag='detail')
    return zw

def sudare(B, u0, u1, z_top, z_bot, v, tag='detail', mat='bamboo', seed=0):
    """簾: a bamboo blind hanging in front of a window (one quad, reeds by the uv: horizontal), the top batten"""
    if u1 - u0 < 0.2 or z_top - z_bot < 0.2: return
    P = np.array([(u0, v, z_bot), (u1, v, z_bot), (u1, v, z_top), (u0, v, z_top)])
    UV = np.array([(z_bot * 7, u0 * 0.35), (z_bot * 7, u1 * 0.35), (z_top * 7, u1 * 0.35), (z_top * 7, u0 * 0.35)])
    B.add(P, [[0, 1, 2], [0, 2, 3]], mat, UV=UV, tag=tag)
    B.add(P, [[0, 2, 1], [0, 3, 2]], mat, UV=UV, tag=tag)
    bars(B, [(u0, v - 0.012, z_top - 0.02), (u0, v - 0.01, z_bot + 0.012)], [(u1, v - 0.012, z_top - 0.02), (u1, v - 0.01, z_bot + 0.012)], (0, 0, 1), (0.04, 0.025), (0.025, 0.02), 'wood_dark', tag='detail')

def board_railing(B, u0, u1, v, z, h=0.85, mat='wood_natural', tag='detail', returns=0.0, board=0.1, gap=0.06):
    """板高欄 of a 2F veranda: posts, top rail (笠木), bottom rail, vertical boards with gaps; optional returns to the wall"""
    if u1 - u0 < 0.3: return
    n = max(1, int((u1 - u0) / (board + gap)))
    us = u0 + (np.arange(n) + 0.5) * (u1 - u0) / n
    bars(B, np.c_[us, np.full(n, v), np.full(n, z + 0.08)], np.c_[us, np.full(n, v), np.full(n, z + h - 0.06)], (1, 0, 0), board, 0.025, mat, tag=tag)
    bars(B, [(u0, v, z + h), (u0, v, z + 0.06)], [(u1, v, z + h), (u1, v, z + 0.06)], (0, 0, 1), (0.07, 0.07), (0.1, 0.06), mat, tag='main', caps=True)
    bars(B, [(u0, v, z - 0.25), (u1, v, z - 0.25)], [(u0, v, z + h + 0.05), (u1, v, z + h + 0.05)], (1, 0, 0), 0.09, 0.09, mat, tag='main', caps=True)
    if returns > 0:
        bars(B, [(u0, v, z + h), (u1, v, z + h)], [(u0, v + returns, z + h), (u1, v + returns, z + h)], (0, 0, 1), 0.07, 0.08, mat, tag=tag)
        bars(B, [(u0, v, z + 0.06), (u1, v, z + 0.06)], [(u0, v + returns, z + 0.06), (u1, v + returns, z + 0.06)], (0, 0, 1), 0.06, 0.06, mat, tag=tag)

def noren(B, u0, u1, z_top, length, v, tint, panels=None, tag='detail'):
    """暖簾: cloth panels with small gaps, hung at v from z_top, plus the pole"""
    W = u1 - u0
    if W < 0.3: return
    k = panels or max(2, min(5, int(round(W / 0.45))))
    g = 0.025; pw = (W - g * (k - 1)) / k
    Q = []
    for i in range(k):
        a = u0 + i * (pw + g); b = a + pw
        Q.append([(a, v, z_top - length), (b, v, z_top - length), (b, v, z_top), (a, v, z_top)])
    quads(B, Q, 'cloth', tag=tag, c0=(*tint, 0))
    quads(B, [[q[1], q[0], q[3], q[2]] for q in Q], 'cloth', tag=tag, c0=(*tint, 0))
    bars(B, [(u0 - 0.05, v, z_top + 0.02)], [(u1 + 0.05, v, z_top + 0.02)], (0, 0, 1), 0.03, 0.03, 'wood_natural', tag=tag)

def chochin(B, x, y, z_top, r=0.17, h=0.46, mat='lantern_paper', tag='main', lamp=True, watts=6.0, rgb=(1.0, 0.55, 0.25), seg=10):
    """提灯 hanging from z_top (local or world, the Builder's frame): paper body, black caps, lit (B.lamp honours Frames)"""
    z = z_top - h - 0.08
    prim.lathe(B, (x, y, z), [(r * 0.7, 0.0), (r * 0.95, h * 0.18), (r, h * 0.5), (r * 0.95, h * 0.82), (r * 0.7, h)], seg, mat, tag=tag)
    prim.cyl(B, (x, y, z - 0.035), (x, y, z + 0.01), r * 0.72, r * 0.72, seg, 'black_lacquer', tag='detail')
    prim.cyl(B, (x, y, z + h - 0.01), (x, y, z + h + 0.04), r * 0.72, r * 0.72, seg, 'black_lacquer', tag='detail')
    bars(B, [(x, y, z + h + 0.04)], [(x, y, z_top)], (1, 0, 0), 0.012, 0.012, 'metal_dark', tag='detail')
    if lamp: B.lamp(x, y, z + h / 2, watts, rgb)

def nameboard(B, u, z0, z1, v, w=0.2, seed=0, mat='white_paint', tag='detail'):
    """a name / shop board with brush strokes (paint program, param 7) in a dark frame"""
    hbox(B, u - w / 2 - 0.02, u + w / 2 + 0.02, v - 0.03, v, z0 - 0.02, z1 + 0.02, 'wood_dark', tag=tag)
    quad(B, (u - w / 2, v - 0.032, z0), (u + w / 2, v - 0.032, z0), (u + w / 2, v - 0.032, z1), (u - w / 2, v - 0.032, z1), mat, tag=tag,
         uv=np.array([(0.0, 0.0), (w * 2.2, 0.0), (w * 2.2, (z1 - z0) * 1.2), (0.0, (z1 - z0) * 1.2)]), c1=(0, 7, seed % 251, 0))

# ------------------------------------------------------------------ roof: a height field of gables over any footprint
class RoofField:
    """z(v) = max over gable sections (ridges parallel to u).  sections: [(va, vb, vr, zr, pitch)] — a gable over
    va..vb with the ridge at vr, height zr, z = zr - pitch * |v - vr|.  build() covers a polygon (local u, v) exactly:
    bands between the kinks of z(v) are clipped from the polygon and triangulated (earcut), so any footprint shape
    works.  Where a section ends above its neighbour (a higher front block over a lower rear roof) a step wall closes
    the gap."""
    def __init__(self, sections):
        self.S = [tuple(map(float, s)) for s in sections]
        self.bands = None
    def z(self, v):
        v = np.asarray(v, float); out = np.full(v.shape, -1e9)
        for (va, vb, vr, zr, p) in self.S:
            inside = (v >= va - 1e-6) & (v <= vb + 1e-6)
            out = np.where(inside, np.maximum(out, zr - p * np.abs(v - vr)), out)
        return out
    def breaks(self, v0, v1):
        c = {v0, v1}
        pieces = []
        for (va, vb, vr, zr, p) in self.S:
            c |= {va, vb, vr}
            pieces += [(va, vr, p, zr - p * vr), (vr, vb, -p, zr + p * vr)]
        for i in range(len(pieces)):
            for j in range(i + 1, len(pieces)):
                a0, a1, sa, ia = pieces[i]; b0, b1, sb, ib = pieces[j]
                if abs(sa - sb) < 1e-9: continue
                x = (ib - ia) / (sa - sb)
                if max(a0, b0) - 1e-6 <= x <= min(a1, b1) + 1e-6: c.add(x)
        out = []
        for x in sorted(c):
            if v0 - 1e-9 <= x <= v1 + 1e-9 and (not out or x - out[-1] > 1e-5): out.append(x)
        return out
    def prepare(self, v0, v1):
        self.cs = self.breaks(v0, v1)
        self.bands = []
        for a, b in zip(self.cs[:-1], self.cs[1:]):
            m = (a + b) / 2; dl = (b - a) * 0.25
            zm = float(self.z(m))
            if zm < -1e8: continue
            s = (float(self.z(m + dl)) - float(self.z(m - dl))) / (2 * dl)
            self.bands.append((a, b, zm, s, m))
        return self
    def zat(self, vq, v):
        """z at v on the linear piece of the band containing vq (vq picks the side at a discontinuity)"""
        for (a, b, zm, s, m) in self.bands:
            if a - 1e-9 <= vq <= b + 1e-9: return zm + s * (v - m)
        return None
    def slope(self, vq):
        for (a, b, zm, s, m) in self.bands:
            if a - 1e-9 <= vq <= b + 1e-9: return s
        return 0.0

    def _pieces(self, poly):
        for (a, b, zm, s, m) in self.bands:
            g = poly.intersection(sbox(poly.bounds[0] - 1, a, poly.bounds[2] + 1, b))
            for p in (g.geoms if hasattr(g, 'geoms') else [g]):
                if p.geom_type != 'Polygon' or p.area < 1e-5: continue
                yield p, zm, s, m

    def build(self, B, poly, mat='kawara', tag='main', thick=0.2, edge_mat='eave_wood', step_mat='wall_plaster', step_c0=(226, 220, 206, 0), c1=(0, 0, 0, 0)):
        """triangulate the roof over poly (shapely, local); edge strips (thick) along the boundary; step walls"""
        import mapbox_earcut as earcut
        if self.bands is None: self.prepare(poly.bounds[1], poly.bounds[3])
        allP = []; allI = []; allUV = []; off = 0
        for p, zm, s, m in self._pieces(poly):
            rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(r.coords)[:-1] for r in p.interiors]
            V = np.concatenate(rings)
            ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
            I = earcut.triangulate_float64(V, ends).reshape(-1, 3)
            if len(I) == 0: continue
            Z = zm + s * (V[:, 1] - m)
            P = np.c_[V, Z]
            fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
            if fn[:, 2].sum() < 0: I = I[:, ::-1]
            vv = Z * math.hypot(1, s) / abs(s) if abs(s) > 0.05 else V[:, 1]
            allP.append(P); allI.append(I + off); allUV.append(np.c_[V[:, 0], vv]); off += len(P)
        if allP:
            B.add(np.concatenate(allP), np.concatenate(allI), mat, UV=np.concatenate(allUV), tag=tag, c1=c1)
        if thick > 0:
            Q = []
            pz = shapely.geometry.polygon.orient(poly, 1.0)
            for ring in [pz.exterior] + list(pz.interiors):
                pts = np.asarray(ring.coords)
                for i in range(len(pts) - 1):
                    for (A, Bq, zA, zB) in self.split_edge(pts[i], pts[i + 1]):
                        Q.append([(A[0], A[1], zA - thick), (Bq[0], Bq[1], zB - thick), (Bq[0], Bq[1], zB), (A[0], A[1], zA)])
            if Q: quads(B, np.array(Q), edge_mat, tag=tag, c1=(0, 1, 0, 0))
        # step walls at discontinuities
        for c in self.cs[1:-1]:
            zl = self.zat(c - 1e-7, c); zr = self.zat(c + 1e-7, c)
            if zl is None or zr is None or abs(zl - zr) < 0.02: continue
            ln = LineString([(poly.bounds[0] - 1, c), (poly.bounds[2] + 1, c)]).intersection(poly)
            for seg in (ln.geoms if hasattr(ln, 'geoms') else [ln]):
                if seg.geom_type != 'LineString' or seg.length < 0.05: continue
                (ua, _), (ub, _) = seg.coords[0], seg.coords[-1]
                lo, hi = min(zl, zr), max(zl, zr)
                oquad(B, [(ua, c, lo - 0.05), (ub, c, lo - 0.05), (ub, c, hi), (ua, c, hi)], (0, 1 if zl > zr else -1, 0), step_mat, tag=tag,
                      uv=np.array([(ua, lo), (ub, lo), (ub, hi), (ua, hi)]), c0=step_c0)

    def split_edge(self, p, q):
        """a boundary segment p->q (interior on the left) split at the band breaks: [(A, B, zA, zB)]"""
        p = np.asarray(p, float); q = np.asarray(q, float)
        d = q - p; Ld = np.linalg.norm(d)
        if Ld < 1e-6: return []
        left = np.array([-d[1], d[0]]) / Ld
        ts = [0.0, 1.0]
        if abs(d[1]) > 1e-9:
            ts += [(c - p[1]) / d[1] for c in self.cs if 1e-6 < (c - p[1]) / d[1] < 1 - 1e-6]
        ts = sorted(ts); out = []
        for ta, tb in zip(ts[:-1], ts[1:]):
            A = p + d * ta; Bq = p + d * tb
            vq = ((A + Bq) / 2 + left * 1e-5)[1]
            zA = self.zat(vq, A[1]); zB = self.zat(vq, Bq[1])
            if zA is None or zB is None: continue
            out.append((A, Bq, zA, zB))
        return out

    def underside(self, B, poly, drop=0.2, mat='eave_wood', tag='main', c1=(0, 2, 0, 0)):
        """soffit under an overhang polygon (facing down), following the roof minus `drop`"""
        import mapbox_earcut as earcut
        if poly.is_empty: return
        for p, zm, s, m in self._pieces(poly):
            rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(r.coords)[:-1] for r in p.interiors]
            V = np.concatenate(rings); ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
            I = earcut.triangulate_float64(V, ends).reshape(-1, 3)
            if len(I) == 0: continue
            P = np.c_[V, zm + s * (V[:, 1] - m) - drop]
            fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
            if fn[:, 2].sum() > 0: I = I[:, ::-1]
            B.add(P, I, mat, UV=np.c_[V[:, 0], V[:, 1]], tag=tag, c1=c1)

    def ridges(self, B, poly, w=0.28, h=0.3, oni=True, tag='main'):
        for (va, vb, vr, zr, p) in self.S:
            if abs(float(self.z(vr)) - zr) > 0.01: continue          # buried under a higher section
            ln = LineString([(poly.bounds[0] - 1, vr), (poly.bounds[2] + 1, vr)]).intersection(poly)
            for seg in (ln.geoms if hasattr(ln, 'geoms') else [ln]):
                if seg.geom_type != 'LineString' or seg.length < 0.5: continue
                (ua, _), (ub, _) = seg.coords[0], seg.coords[-1]
                ua, ub = min(ua, ub) + 0.04, max(ua, ub) - 0.04
                prof = [(-w / 2, -0.12), (w / 2, -0.12), (w / 2, h * 0.65), (w * 0.3, h), (-w * 0.3, h), (-w / 2, h * 0.65)]
                prim.sweep(B, np.array([(ua, vr, zr), (ub, vr, zr)]), prof, 'ridge', tag=tag, caps=True)
                if oni:
                    for u in (ua, ub):
                        hbox(B, u - 0.04, u + 0.04, vr - 0.2, vr + 0.2, zr - 0.05, zr + h + 0.16, 'ridge', tag='detail', c1=(0, 1, 0, 0))

# ------------------------------------------------------------------ the house
KIND_WP = {'ochaya': 6.0, 'tsushi': 4.55, 'sangai': 8.9, 'hiraya': 3.25, 'shop': 6.1}

def _frame(ring, street_edge):
    ring = np.asarray(ring, float)
    if np.allclose(ring[0], ring[-1]): ring = ring[:-1]
    e0, e1 = np.asarray(street_edge[0], float), np.asarray(street_edge[1], float)
    d = e1 - e0; d /= np.linalg.norm(d)
    c = Polygon(ring).representative_point(); c = np.array([c.x, c.y])
    n = np.array([-d[1], d[0]])
    if (c - e0) @ n < 0: n = -n
    u = np.array([n[1], -n[0]])
    L = np.c_[(ring - e0) @ u, (ring - e0) @ n]
    vmin = L[:, 1].min()
    fr = L[L[:, 1] < vmin + 0.9]
    u0, u1 = fr[:, 0].min(), fr[:, 0].max()
    O = e0 + u * u0 + n * vmin
    L = L - [u0, vmin]
    return O, u, n, math.atan2(u[1], u[0]), L

def _style(style, seed, H, st):
    s = dict(DEFAULT_STYLE); s.update(style or {})
    r = np.random.default_rng(seed)
    if s['kind'] == 'auto':
        s['kind'] = 'hiraya' if (H < 5.6 or st == 1) else 'sangai' if (H > 11.5 or st >= 3) else ('tsushi' if H < 7.6 else 'ochaya')
    if s['wall'] is None: s['wall'] = WALLS[r.integers(len(WALLS))]
    if s['degoshi'] is None: s['degoshi'] = r.random() < 0.45
    if s['inuyarai'] is None: s['inuyarai'] = r.random() < 0.7
    if s['komayose'] is None: s['komayose'] = (not s['inuyarai']) and r.random() < 0.6
    if s['railing'] is None: s['railing'] = s['kind'] in ('ochaya', 'sangai') and r.random() < 0.8
    if s['sudare'] is None: s['sudare'] = s['kind'] in ('ochaya', 'sangai', 'shop') and r.random() < (0.85 if s['kind'] != 'shop' else 0.3)
    if s['noren'] is None: s['noren'] = NOREN[r.integers(len(NOREN))] if r.random() < 0.75 else False
    if s['chochin'] is None: s['chochin'] = s['kind'] in ('ochaya', 'sangai', 'tsushi') and r.random() < 0.6
    if s['eave'] is None: s['eave'] = {'tsushi': 0.95, 'hiraya': 0.9}.get(s['kind'], 0.72) + r.uniform(-0.05, 0.08)
    if s['back_o'] is None: s['back_o'] = 0.75 if s['back'] == 'canal' else 0.0
    return s, r

def build(B, ring, street_edge, z0, height, storeys=0, style=None, seed=0):
    O, U, N, yaw, L = _frame(ring, street_edge)
    H = float(height); st = int(storeys or 0)
    s, rng = _style(style, seed, H, st)
    kind = s['kind']
    fp = Polygon(L)
    if not fp.is_valid: fp = fp.buffer(0)
    if fp.geom_type != 'Polygon': fp = max(fp.geoms, key=lambda p: p.area)
    fp = shapely.geometry.polygon.orient(fp, 1.0)
    W = float(L[:, 0][L[:, 1] < 0.9].max())
    D = float(fp.bounds[3])
    info = dict(frame=(float(O[0]), float(O[1]), yaw), W=W, D=D, kind=kind, ring_local=np.asarray(fp.exterior.coords), lamps=[])
    # ---------------- heights
    z_wp = s['z_wp'] or KIND_WP.get(kind, 6.0) + rng.uniform(-0.25, 0.3)
    o = s['eave']; p_t = rng.uniform(0.42, 0.5)
    H = max(H, z_wp + 1.0)
    Df = 2 * (H - z_wp - 0.2) / p_t
    if Df > D:
        Df = D; p = (H - z_wp - 0.2) / max(D / 2, 0.5)
        if p > 0.62:
            p = 0.62; z_wp = H - 0.2 - p * D / 2
    elif Df < 3.0:
        Df = min(D, 7.0); p = p_t; z_wp = max(KIND_WP['hiraya'], H - 0.2 - p * Df / 2)
    else:
        p = p_t
    if kind == 'hiraya': z_wp = min(z_wp, 3.6)
    zr = z_wp + 0.2 + p * Df / 2
    secs = []
    rest = D - Df
    back_o = s['back_o']
    if rest < 2.5:
        secs.append((-o - 0.01, D + back_o + 0.01, Df / 2, zr, p))
    else:
        secs.append((-o - 0.01, Df, Df / 2, zr, p))
        k = max(1, int(round(rest / 9.0)))
        edges = np.linspace(Df, D, k + 1)
        for i in range(k):
            va, vb = edges[i], edges[i + 1]
            last = i == k - 1
            Ls = vb - va
            pr = rng.uniform(0.38, 0.46)
            two = rng.random() < (0.55 if kind != 'hiraya' else 0.0)
            ze = (z_wp - rng.uniform(0.0, 0.6)) if two else rng.uniform(3.0, 3.5)
            zrr = min(zr - 0.25, ze + 0.2 + pr * Ls / 2)
            secs.append((va, vb + (back_o + 0.01 if last else 0.0), (va + vb) / 2, zrr, pr))
    RF = RoofField(secs)
    zf = RF.z
    info.update(z_wp=z_wp, z_ridge=zr, pitch=p)
    seedc = (0, 0, int(seed) % 251, 0)
    wall_t = tuple(int(c) for c in s['wall'])
    wood = 'wood_dark'
    wtint = dict(c0=BENGARA_TINT) if s['wood'] == 'bengara' else {}
    wmat = 'vermilion' if s['wood'] == 'bengara' else 'wood_dark'
    party_t = s['party_tint'] or ((70, 58, 46) if s['party'] == 'wall_board' else (226, 220, 206) if rng.random() < 0.6 else wall_t)
    with Frame(B, O[0], O[1], z0, yaw):
        # ---------------- roof
        roofp = fp.union(sbox(0, -o, W, 0.02))
        if back_o > 0:
            bk = L[L[:, 1] > D - 0.9]
            roofp = roofp.union(sbox(bk[:, 0].min(), D - 0.02, bk[:, 0].max(), D + back_o))
        roofp = roofp.simplify(0.01)
        if roofp.geom_type != 'Polygon': roofp = max(roofp.geoms, key=lambda q: q.area)
        RF.prepare(-o - 0.02, D + back_o + 0.02)
        RF.build(B, roofp, mat=s['roof'], thick=0.22, c1=(0, 0, int(seed) % 251, 0), step_c0=(*party_t, 0))
        RF.ridges(B, roofp)
        # soffit under the front (and back) overhangs
        RF.underside(B, sbox(0, -o, W, 0.0), drop=0.22)
        if back_o > 0: RF.underside(B, roofp.difference(fp.buffer(0.01)).intersection(sbox(-50, D - 1, 200, D + back_o + 1)), drop=0.22)
        z_edge = RF.zat(-o + 1e-3, -o)
        zs = lambda v: RF.zat(v, v) - 0.22                    # soffit height
        # tile edge line on the eave (一文字), gutter, 出桁 and 腕木 under the main eave
        front_rect(B, 0, W, z_edge - 0.07, z_edge + 0.01, -o - 0.01, s['roof'], tag='main')
        bars(B, [(0.0, -o - 0.06, z_edge - 0.16)], [(W, -o - 0.06, z_edge - 0.16)], (0, 0, 1), 0.1, 0.1, 'bronze', tag='detail')
        nb2 = max(1, int(round(W / 1.95)))
        posts2 = np.linspace(0.06, W - 0.06, nb2 + 1)
        vb_ = -o + 0.24
        bars(B, [(0.0, vb_, zs(vb_) - 0.08)], [(W, vb_, zs(vb_) - 0.08)], (0, 0, 1), 0.14, 0.13, wood, tag='main', caps=True)
        bars(B, np.c_[posts2, np.zeros(len(posts2)), np.full(len(posts2), zs(0.0) - 0.2)], np.c_[posts2, np.full(len(posts2), -o + 0.14), np.full(len(posts2), zs(-o + 0.14) - 0.17)],
             (1, 0, 0), 0.09, 0.12, wood, tag='detail', caps=True)
        # ---------------- side and back walls (follow the roof)
        fe = []
        for (p0_, p1_) in s['facade_edges']:
            a_ = np.asarray(p0_, float) - O; b_ = np.asarray(p1_, float) - O
            fe.append(LineString([(a_ @ U, a_ @ N), (b_ @ U, b_ @ N)]))
        Q = []; UVq = []; extra_fronts = []
        v_front = secs[0][1] - 0.25                   # extra fronts only along the front block (rear sections are lower)
        pts = np.asarray(fp.exterior.coords)
        gfun = s['ground']
        def zfoot(p, zb0):
            if gfun is None or zb0 > -0.39: return zb0
            w = O + U * p[0] + N * p[1]
            return min(zb0, float(gfun(w[0], w[1])) - z0 - 0.3)
        def wall(pa, pb, zb0):
            acc = 0.0
            for (A, Bq, zA, zB) in RF.split_edge(pa, pb):
                l = np.linalg.norm(Bq - A)
                if zA - 0.12 > zb0 + 0.05 or zB - 0.12 > zb0 + 0.05:
                    fa, fb = zfoot(A, zb0), zfoot(Bq, zb0)
                    Q.append([(A[0], A[1], fa), (Bq[0], Bq[1], fb), (Bq[0], Bq[1], max(zb0, zB - 0.12)), (A[0], A[1], max(zb0, zA - 0.12))])
                    UVq.append([(acc, fa), (acc + l, fb), (acc + l, zB - 0.12), (acc, zA - 0.12)])
                acc += l
        for i in range(len(pts) - 1):
            pa, pb = pts[i], pts[i + 1]
            if s['facade'] and pa[1] < 0.6 and pb[1] < 0.6: continue     # the street front: built below
            if s['back'] == 'canal' and pa[1] > D - 0.9 and pb[1] > D - 0.9: continue   # rear elevation: built below
            mid_ = shapely.geometry.Point((pa + pb) / 2)
            if np.linalg.norm(pb - pa) > 1.5 and any(f.distance(mid_) < 0.5 for f in fe):
                # dressed part (v <= v_front) + plain rest, split along the edge keeping its direction
                d_ = pb - pa
                ts = [0.0, 1.0]
                if abs(d_[1]) > 1e-6:
                    t_ = (v_front - pa[1]) / d_[1]
                    if 0 < t_ < 1: ts = [0.0, t_, 1.0]
                for ta, tb in zip(ts[:-1], ts[1:]):
                    A = pa + d_ * ta; Bq = pa + d_ * tb
                    if max(A[1], Bq[1]) <= v_front + 1e-6 and np.linalg.norm(Bq - A) > 1.5:
                        wall(A, Bq, z_wp - 0.1); extra_fronts.append((A, Bq))
                    else:
                        wall(A, Bq, -0.4)
                continue
            wall(pa, pb, -0.4)
        if Q: quads(B, Q, s['party'], UV=UVq, c0=(*party_t, 0), c1=seedc)
        # ---------------- the street front(s)
        if s['facade']:
            info['z_hisashi'] = _front(B, s, rng, W, z_wp, o, z_edge, wall_t, wmat, wtint, seed, info)
            # blockers for what stands in front of the wall (犬矢来, 出格子, 駒寄せ), open at the door
            da, db = info.get('door', (W + 1, W + 1))
            for (a_, b_) in ((0.0, min(da, W)), (min(db, W), W)):
                if b_ - a_ > 0.3: prim.polygon(B, [(a_, -0.55), (b_, -0.55), (b_, 0.0), (a_, 0.0)], 0.05, 'stone', tag='block')
        for (pa, pb) in extra_fronts:
            s2 = dict(s); s2.update(s['facade_style'] or {})
            Wf = float(np.linalg.norm(pb - pa)); ang = math.atan2(pb[1] - pa[1], pb[0] - pa[0])
            with Frame(B, pa[0], pa[1], 0.0, ang):
                _front(B, s2, np.random.default_rng(seed + 17), Wf, z_wp, 0.3, z_wp + 0.1, wall_t, wmat, wtint, seed + 17, {'lamps': []})
        if s['back'] == 'canal':
            _canal_back(B, s, rng, L, D, z_wp, RF, wall_t, seed)
        # blocker: the footprint
        prim.polygon(B, np.asarray(fp.exterior.coords)[:-1], 0.05, 'stone', tag='block')
    return info

def _bays(W):
    nb = max(1, int(round(W / 1.85)))
    edges = np.linspace(0.0, W, nb + 1)
    return nb, edges

def _front(B, s, rng, W, z_wp, o, z_edge, wall_t, wmat, wtint, seed, info):
    kind = s['kind']
    nb, ed = _bays(W)
    pw = 0.12                                   # post width
    z1 = s['z1'] if s['z1'] else 2.72 + rng.uniform(-0.12, 0.15)        # 1F beam / underside of the 庇 at the wall
    if kind == 'hiraya': z1 = min(z1, z_wp - 0.25)
    door = int(rng.integers(nb)) if nb > 2 else (0 if rng.random() < 0.5 else nb - 1)
    if s['door'] is not None: door = s['door'] if s['door'] >= 0 else -99
    types = []
    for i in range(nb):
        if i == door: types.append('door')
        elif s['front1'] == 'redwall': types.append('red')
        elif kind == 'shop': types.append('shop')
        elif s['degoshi'] and rng.random() < 0.7 and s['lattice'] != 'none': types.append('degoshi')
        elif s['lattice'] == 'none' or rng.random() < 0.12: types.append('wall')
        else: types.append('lattice')
    pitch = 0.046 if s['lattice'] == 'senbon' else 0.09
    sw = 0.026 if s['lattice'] == 'senbon' else 0.055
    # stone sill along the front
    hbox(B, 0, W, -0.22, 0.02, -0.25, 0.06, 'stone', tag='main')
    # posts
    bars(B, np.c_[ed, np.full(nb + 1, -0.02), np.zeros(nb + 1)], np.c_[ed, np.full(nb + 1, -0.02), np.full(nb + 1, z1)], (1, 0, 0), pw, 0.14, wmat, tag='main', caps=True, **wtint)
    # 差鴨居 beam under the 庇
    bars(B, [(0, -0.03, z1 - 0.1)], [(W, -0.03, z1 - 0.1)], (0, 0, 1), 0.2, 0.12, wmat, tag='main', **wtint)
    hz = 2.42                                   # top of the lattice / door head
    iy = []                                     # 犬矢来 spans (merged into runs below)
    iykind = 'plank' if s['inuyarai'] == 'plank' else 'slope' if s['inuyarai'] == 'slope' else 'bamboo'
    for i, t in enumerate(types):
        a = ed[i] + pw / 2; b = ed[i + 1] - pw / 2
        if b - a < 0.3: continue
        if t == 'red':
            sk = s['skirt']
            front_rect(B, a, b, 0.05, sk, -0.01, 'wall_board', c0=(40, 33, 28, 0))
            front_rect(B, a, b, sk, z1 - 0.2, 0.025, 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
            bars(B, [(a, -0.02, sk), (a, -0.02, 2.05)], [(b, -0.02, sk), (b, -0.02, 2.05)], (0, 0, 1), (0.09, 0.05), 0.07, wmat, tag='detail', **wtint)
            nbt = max(1, int((b - a) / 0.3))
            bu = np.linspace(a, b, nbt + 1)[1:-1]
            bars(B, np.c_[bu, np.full(len(bu), -0.018), np.full(len(bu), 0.08)], np.c_[bu, np.full(len(bu), -0.018), np.full(len(bu), sk - 0.04)], (1, 0, 0), 0.035, 0.02, 'wood_dark', tag='detail')
            if s['inuyarai']: iy.append((a - pw / 2, b + pw / 2))
            continue
        # transom band between the opening heads and the beam
        front_rect(B, a, b, hz, z1 - 0.2, 0.02, 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
        if t == 'door':
            dw = min(b - a, 1.7); da = a + (b - a - dw) / 2 if b - a > 2.2 else a; db = da + dw
            zd = 1.98
            if da > a + 0.05: front_rect(B, a, da, 0.05, hz, 0.02, 'wall_board', c0=(70, 58, 46, 0))
            if db < b - 0.05: front_rect(B, db, b, 0.05, hz, 0.02, 'wall_board', c0=(70, 58, 46, 0))
            front_rect(B, da, db, zd, hz, 0.0, 'wall_board', c0=(60, 48, 38, 0))
            # recess: jambs, threshold, the 格子戸 at the back of the recess
            rd = 0.38
            side_rect(B, 0.0, rd, 0.0, zd, da, 'wood_dark', facing=1); side_rect(B, 0.0, rd, 0.0, zd, db, 'wood_dark', facing=-1)
            hbox(B, da, db, 0.0, rd, zd - 0.01, zd + 0.06, 'wood_dark', tag='detail')
            prim.polygon(B, [(da, -0.02), (db, -0.02), (db, rd), (da, rd)], 0.06, 'stone', tag='main')
            lattice(B, da + 0.04, db - 0.04, 0.55, zd - 0.06, rd - 0.03, pitch=0.07, sw=0.022, sd=0.03, mat='wood_dark', back='black_lacquer', back_dv=0.05, mid=False)
            front_rect(B, da + 0.04, db - 0.04, 0.08, 0.55, rd - 0.04, 'wood_dark')
            # step stone, noren, name board, lantern
            hbox(B, da + 0.1, db - 0.1, -0.5, -0.06, 0.0, 0.1, 'stone', tag='detail')
            if s['noren']:
                noren(B, da + 0.02, db - 0.02, zd - 0.02, 0.85 if rng.random() < 0.6 else 1.35, 0.06, s['noren'])
            if s['nameboard']:
                nu = da - 0.18 if da - a > 0.3 else (db + 0.18 if b - db > 0.3 else da + 0.15)
                nameboard(B, min(max(nu, a + 0.12), b - 0.12), 1.45, 1.95, -0.0 if da - a > 0.3 or b - db > 0.3 else 0.0, seed=seed)
            info['door'] = (da, db)
        elif t in ('lattice', 'degoshi', 'shop', 'wall'):
            if t == 'shop':
                front_rect(B, a, b, 0.05, 0.45, -0.01, 'wood_dark')
                front_rect(B, a, b, 0.45, 2.3, 0.08, 'glass', tag='main')
                nm = max(1, int((b - a) / 0.9))
                mu = np.linspace(a, b, nm + 1)
                bars(B, np.c_[mu, np.full(nm + 1, 0.06), np.full(nm + 1, 0.45)], np.c_[mu, np.full(nm + 1, 0.06), np.full(nm + 1, 2.3)], (1, 0, 0), 0.05, 0.05, 'wood_dark', tag='detail')
                bars(B, [(a, 0.06, 2.3), (a, 0.06, 0.45)], [(b, 0.06, 2.3), (b, 0.06, 0.45)], (0, 0, 1), 0.07, 0.06, 'wood_dark', tag='detail')
                front_rect(B, a, b, 2.3, hz, 0.0, 'wall_board', c0=(60, 48, 38, 0))
                continue
            if t == 'wall':
                front_rect(B, a, b, 0.05, 0.9, -0.01, 'wall_board', c0=(64, 52, 42, 0))
                wall_holes(B, a, b, 0.9, hz, 0.0, [], 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
                if s['inuyarai']: iy.append((a - pw / 2, b + pw / 2))
                continue
            if t == 'lattice':
                front_rect(B, a, b, 0.05, 0.46, -0.01, 'wall_board', c0=(64, 52, 42, 0))
                lattice(B, a, b, 0.46, hz, -0.03, pitch=pitch, sw=sw, mat=wmat, c0=wtint.get('c0', (255, 255, 255, 0)))
                if s['inuyarai']: iy.append((a - pw / 2, b + pw / 2))
                continue
            # 出格子: projecting lattice box
            dv = -0.42
            zt = 2.22
            front_rect(B, a, b, 0.2, 0.46, dv - 0.01, 'wall_board', c0=(64, 52, 42, 0))
            hbox(B, a, b, dv - 0.02, 0.0, 0.42, 0.47, wmat, tag='main', **wtint)               # sill
            hbox(B, a - 0.03, b + 0.03, dv - 0.06, 0.0, zt, zt + 0.05, wmat, tag='main', **wtint)  # top board
            lattice(B, a, b, 0.47, zt, dv, pitch=pitch, sw=sw, mat=wmat, back='black_lacquer', back_dv=-dv - 0.02, c0=wtint.get('c0', (255, 255, 255, 0)))
            for (u, f) in ((a + 0.015, -1), (b - 0.015, 1)):
                side_lattice(B, dv + 0.02, -0.02, 0.47, zt, u, mat=wmat, c0=wtint.get('c0', (255, 255, 255, 0)))
            side_rect(B, dv, 0.0, 0.2, 0.47, a, 'wall_board', facing=-1, c0=(64, 52, 42, 0)); side_rect(B, dv, 0.0, 0.2, 0.47, b, 'wall_board', facing=1, c0=(64, 52, 42, 0))
            front_rect(B, a, b, zt + 0.05, hz, 0.0, 'wall_plaster', c0=(*wall_t, 0))
            if s['komayose']: komayose(B, a - pw / 2, b + pw / 2, v=dv - 0.4, h=0.95)
    # 犬矢来 runs (continuous across posts, broken at doors and 出格子)
    runs = []
    for (a, b) in sorted(iy):
        if runs and a - runs[-1][1] < 0.25: runs[-1] = (runs[-1][0], b)
        else: runs.append((a, b))
    ih = (1.05 if iykind != 'bamboo' else 0.92) + rng.uniform(-0.04, 0.06)
    for (a, b) in runs:
        inuyarai(B, a + 0.02, b - 0.02, h=ih, out=0.45 if iykind == 'bamboo' else 0.75, kind=iykind)
    # the 庇
    zh = z1 + 0.1
    if s['hisashi'] and kind not in ('hiraya',):
        depth = 0.95 if kind != 'shop' else 1.25
        zh = z1 + 0.12 + (rng.uniform(-0.05, 0.05) if not s['z1'] else 0.0)
        zw = hisashi(B, -0.02, W + 0.02, zh, depth=depth, pitch=0.36, v=-0.02, brackets=ed[1:-1] if nb > 1 else [W / 2], manju=rng.random() < 0.5)
        # lantern at the door
        if s['chochin'] and 'door' in info:
            da, db = info['door']
            uu = da - 0.25 if da > 0.5 else db + 0.25
            chochin(B, uu, -0.45, zh - 0.18, lamp=s['lamps'])
            info['lamps'].append(uu)
        upper0 = zw + 0.05
    else:
        upper0 = z1 + 0.1
    if kind == 'hiraya':
        front_rect(B, 0, W, z1, z_wp, 0.0, 'wall_plaster', c0=(*wall_t, 0))
        return zh
    # ---------------- upper storeys
    floors = []
    if kind == 'tsushi':
        floors.append(('tsushi', upper0, z_wp))
    elif kind == 'sangai':
        zm = upper0 + (z_wp - upper0) * 0.5
        floors += [('ochaya', upper0, zm), ('third', zm, z_wp)]
    elif kind == 'shop' and z_wp > 8.0:
        zm = upper0 + (z_wp - upper0) * 0.5
        floors += [('shop2', upper0, zm), ('third', zm, z_wp)]
    else:
        floors.append(('ochaya' if kind != 'shop' else 'shop2', upper0, z_wp))
    nb2 = max(1, int(round(W / 1.95)))
    pu = np.linspace(0.0, W, nb2 + 1)
    bars(B, np.c_[pu, np.full(nb2 + 1, 0.0), np.full(nb2 + 1, upper0 - 0.3)], np.c_[pu, np.full(nb2 + 1, 0.0), np.full(nb2 + 1, z_wp)], (1, 0, 0), 0.12, 0.12, 'wood_dark', tag='main', caps=True)
    if s['upper'] == 'itagoshi':
        floors = [('itagoshi', upper0, z_wp)]
    for (ft, za, zb) in floors:
        if ft == 'itagoshi':
            # 一力: a continuous screen of vertical boards with cross rails standing proud of the 2F wall
            vz = -0.32
            front_rect(B, 0.0, W, za - 0.3, zb, 0.06, 'wall_plaster', c0=(*wall_t, 0))
            front_rect(B, 0.05, W - 0.05, za + 0.1, zb - 0.25, vz + 0.12, 'black_lacquer')
            n = max(2, int(W / 0.2))
            bu = np.linspace(0.08, W - 0.08, n)
            bars(B, np.c_[bu, np.full(n, vz), np.full(n, za)], np.c_[bu, np.full(n, vz), np.full(n, zb - 0.2)], (1, 0, 0), 0.12, 0.03, 'wood_dark', tag='detail', hide=(0, 1, 0))
            zz = np.arange(za + 0.35, zb - 0.3, 0.42)
            bars(B, np.c_[np.zeros(len(zz)), np.full(len(zz), vz - 0.025), zz], np.c_[np.full(len(zz), W), np.full(len(zz), vz - 0.025), zz], (0, 0, 1), 0.05, 0.03, 'wood_dark', tag='detail', hide=(0, 1, 0))
            hbox(B, 0.0, W, vz - 0.06, 0.06, za - 0.06, za + 0.02, 'wood_dark', tag='main')
            hbox(B, 0.0, W, vz - 0.06, 0.06, zb - 0.25, zb - 0.17, 'wood_dark', tag='main')
            side_rect(B, vz - 0.06, 0.06, za, zb - 0.2, 0.0, 'wood_dark', facing=-1); side_rect(B, vz - 0.06, 0.06, za, zb - 0.2, W, 'wood_dark', facing=1)
            continue
        if ft == 'tsushi':
            # plastered low storey with 虫籠窓
            nw = 1 if W < 4.5 else 2 if W < 8 else 3
            holes = []
            for k in range(nw):
                cu = W * (k + 0.5) / nw; ww = min(0.95, W / nw - 0.6); h0 = za + 0.35; h1 = min(zb - 0.3, h0 + 0.62)
                if ww > 0.4 and h1 - h0 > 0.3: holes.append((cu - ww / 2, cu + ww / 2, h0, h1))
            wall_holes(B, 0.0, W, za - 0.3, zb, 0.06, holes, 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
            for (ha, hb, h0, h1) in holes:
                front_rect(B, ha, hb, h0, h1, 0.16, 'black_lacquer')
                for (aa, bb, cc, dd) in ((ha, hb, h0 - 0.06, h0), (ha, hb, h1, h1 + 0.06)):
                    hbox(B, aa - 0.06, bb + 0.06, 0.0, 0.16, cc, dd, 'wall_plaster', tag='detail', c0=(*wall_t, 0), faces='yzZ')
                side_rect(B, 0.06, 0.16, h0, h1, ha, 'wall_plaster', facing=1, c0=(*wall_t, 0)); side_rect(B, 0.06, 0.16, h0, h1, hb, 'wall_plaster', facing=-1, c0=(*wall_t, 0))
                nbars = max(4, int((hb - ha) / 0.1))
                bu = np.linspace(ha + 0.05, hb - 0.05, nbars)
                bars(B, np.c_[bu, np.full(nbars, 0.1), np.full(nbars, h0)], np.c_[bu, np.full(nbars, 0.1), np.full(nbars, h1)], (1, 0, 0), 0.045, 0.06, 'wall_plaster', tag='detail', c0=(*wall_t, 0))
        elif ft in ('ochaya', 'third', 'shop2'):
            # windows (shoji / glass behind lattice) between posts, plaster bands, 簾, railing
            for i in range(nb2):
                a = pu[i] + 0.06; b = pu[i + 1] - 0.06
                wz0 = za + (0.35 if ft != 'third' else 0.5); wz1 = zb - 0.38
                if wz1 - wz0 < 0.5: wz1 = zb - 0.1
                front_rect(B, a, b, za - 0.3, wz0, 0.04, 'wall_board' if ft != 'shop2' else 'wall_plaster', c0=(70, 58, 46, 0) if ft != 'shop2' else (*wall_t, 0))
                front_rect(B, a, b, wz1, zb, 0.04, 'wall_plaster', c0=(*wall_t, 0), c1=(0, 0, int(seed) % 251, 0))
                glazed = ft == 'shop2' or rng.random() < 0.3
                front_rect(B, a, b, wz0, wz1, 0.1, 'glass' if glazed else 'wall_plaster', c0=(238, 232, 214, 0) if not glazed else (255, 255, 255, 0))
                # window frame + 格子 / mullions
                bars(B, [(a, 0.06, wz0), (a, 0.06, wz1)], [(b, 0.06, wz0), (b, 0.06, wz1)], (0, 0, 1), 0.06, 0.06, 'wood_dark', tag='detail')
                if ft == 'shop2' or (rng.random() < 0.5 and not s['sudare']):
                    lattice(B, a, b, wz0, wz1, 0.0, pitch=0.06, sw=0.02, sd=0.03, back=None, rails=False, mid=False)
                else:
                    nm = max(2, int((b - a) / 0.45))
                    mu = np.linspace(a, b, nm + 1)[1:-1]
                    bars(B, np.c_[mu, np.full(len(mu), 0.07), np.full(len(mu), wz0)], np.c_[mu, np.full(len(mu), 0.07), np.full(len(mu), wz1)], (1, 0, 0), 0.025, 0.03, 'wood_dark', tag='detail')
                    zz = np.linspace(wz0, wz1, 4)[1:-1]
                    bars(B, np.c_[np.full(len(zz), a), np.full(len(zz), 0.075), zz], np.c_[np.full(len(zz), b), np.full(len(zz), 0.075), zz], (0, 0, 1), 0.02, 0.025, 'wood_dark', tag='detail')
                if s['sudare'] and ft != 'shop2':
                    down = rng.uniform(0.55, 1.0)
                    sudare(B, a + 0.02, b - 0.02, zb - 0.12, zb - 0.12 - (zb - 0.12 - za - 0.25) * down, -0.12)
            if ft == 'ochaya' and s['railing']:
                board_railing(B, 0.12, W - 0.12, -0.58, za + 0.02, h=0.82, returns=0.5)
            if ft == 'third':
                bars(B, [(0, -0.03, za)], [(W, -0.03, za)], (0, 0, 1), 0.18, 0.1, 'wood_dark', tag='main', caps=True)
                if rng.random() < 0.6: board_railing(B, 0.12, W - 0.12, -0.35, za + 0.05, h=0.75, returns=0.3)
    # shop: sign board on the 庇 and a hanging sign
    if kind == 'shop':
        sw_ = min(W - 0.6, 3.6)
        if sw_ > 0.8:
            su = (W - sw_) / 2
            hbox(B, su, su + sw_, -0.2, -0.12, upper0 + 0.02, upper0 + 0.62, 'wood_dark', tag='main')
            quad(B, (su + 0.05, -0.205, upper0 + 0.07), (su + sw_ - 0.05, -0.205, upper0 + 0.07), (su + sw_ - 0.05, -0.205, upper0 + 0.57), (su + 0.05, -0.205, upper0 + 0.57),
                 s['sign'] or ('white_paint' if rng.random() < 0.5 else 'wood_natural'), tag='main', uv=np.array([(0, 0), (sw_ * 1.6, 0), (sw_ * 1.6, 0.8), (0, 0.8)]), c1=(0, 7, int(seed) % 251, 0))
        if rng.random() < 0.6:
            uu = 0.35 if rng.random() < 0.5 else W - 0.35
            hbox(B, uu - 0.03, uu + 0.03, -0.95, -0.02, upper0 + 2.1, upper0 + 2.16, 'metal_dark', tag='detail')
            hbox(B, uu - 0.03, uu + 0.03, -0.92, -0.18, upper0 + 0.35, upper0 + 2.1, 'wood_dark', tag='detail')
            for f in (-1, 1):
                P = np.array([(uu + f * 0.035, -0.9, upper0 + 0.4), (uu + f * 0.035, -0.2, upper0 + 0.4), (uu + f * 0.035, -0.2, upper0 + 2.05), (uu + f * 0.035, -0.9, upper0 + 2.05)])
                I = [[0, 1, 2], [0, 2, 3]] if f > 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I, 'white_paint', UV=np.array([(0, 0), (1.0, 0), (1.0, 2.2), (0, 2.2)]), tag='detail', c1=(0, 7, (int(seed) * 7) % 251, 0))
    # downpipe from the main eave
    if rng.random() < 0.7:
        uu = W - 0.18 if rng.random() < 0.5 else 0.18
        prim.cyl(B, (uu, -o + 0.05, z_edge - 0.2), (uu, -0.12, z_edge - 0.55), 0.035, 0.035, 6, 'bronze', tag='detail')
        prim.cyl(B, (uu, -0.12, z_edge - 0.55), (uu, -0.12, upper0 - 0.1), 0.035, 0.035, 6, 'bronze', tag='detail')
    return zh

def _canal_back(B, s, rng, L, D, z_wp, RF, wall_t, seed):
    """the rear elevation over a canal (白川の川端茶屋): 2F rooms with glazed lattice and 簾, a 1F board wall on posts
    standing on the canal wall, a small balcony with a railing; the back eave overhangs"""
    bk = L[L[:, 1] > D - 0.9]
    u0, u1 = bk[:, 0].min(), bk[:, 0].max()
    vb = D
    W = u1 - u0
    if W < 1.0: return
    # facing +v (the canal): use the facing=+1 rect helpers at plane v = vb
    z2 = 3.0 + rng.uniform(-0.15, 0.2)
    zt = RF.zat(vb - 0.01, vb) - 0.15
    front_rect(B, u0, u1, -1.6, z2, vb, 'wall_board', facing=1, c0=(58, 46, 36, 0))
    # posts down to the canal bed (the room overhangs the revetment)
    nb = max(1, int(round(W / 1.9)))
    pu = np.linspace(u0 + 0.06, u1 - 0.06, nb + 1)
    bars(B, np.c_[pu, np.full(nb + 1, vb + 0.06), np.full(nb + 1, -1.8)], np.c_[pu, np.full(nb + 1, vb + 0.06), np.full(nb + 1, zt)], (1, 0, 0), 0.12, 0.12, 'wood_dark', tag='main', caps=True)
    # 1F windows (small lattice) and the 2F glazed rooms
    for i in range(nb):
        a = pu[i] + 0.08; b = pu[i + 1] - 0.08
        if rng.random() < 0.6:
            lattice(B, a + 0.2, b - 0.2, 1.0, 2.2, vb + 0.03, pitch=0.06, sw=0.022, sd=0.03, back='black_lacquer', back_dv=-0.05, mid=False, rails=False)
        front_rect(B, a, b, z2 + 0.6, zt - 0.3, vb - 0.05, 'glass' if rng.random() < 0.5 else 'wall_plaster', facing=1, c0=(238, 232, 214, 0))
        front_rect(B, a, b, z2, z2 + 0.6, vb, 'wall_board', facing=1, c0=(58, 46, 36, 0))
        front_rect(B, a, b, zt - 0.3, zt, vb, 'wall_plaster', facing=1, c0=(*wall_t, 0))
        mu = np.linspace(a, b, max(3, int((b - a) / 0.5)) + 1)[1:-1]
        bars(B, np.c_[mu, np.full(len(mu), vb + 0.02), np.full(len(mu), z2 + 0.6)], np.c_[mu, np.full(len(mu), vb + 0.02), np.full(len(mu), zt - 0.3)], (1, 0, 0), 0.03, 0.03, 'wood_dark', tag='detail')
        if s['sudare'] or rng.random() < 0.7:
            sudare(B, a + 0.03, b - 0.03, zt - 0.2, zt - 0.2 - rng.uniform(0.6, 1.3), vb + 0.15)
    # balcony with a railing on part of the 2F
    if rng.random() < 0.7 and W > 2.5:
        ba = u0 + 0.3; bb = u0 + min(W - 0.3, rng.uniform(2.0, 4.0))
        hbox(B, ba, bb, vb, vb + 0.75, z2 - 0.08, z2 + 0.02, 'wood_natural', tag='main')
        bars(B, [(ba, vb + 0.72, z2 + 0.8), (ba, vb + 0.72, z2 + 0.15)], [(bb, vb + 0.72, z2 + 0.8), (bb, vb + 0.72, z2 + 0.15)], (0, 0, 1), 0.06, 0.06, 'wood_natural', tag='detail')
        n = max(2, int((bb - ba) / 0.2))
        bu = np.linspace(ba, bb, n)
        bars(B, np.c_[bu, np.full(n, vb + 0.72), np.full(n, z2)], np.c_[bu, np.full(n, vb + 0.72), np.full(n, z2 + 0.8)], (1, 0, 0), 0.035, 0.035, 'wood_natural', tag='detail')
        bars(B, [(ba, vb + 0.72, z2 - 0.1), (bb, vb + 0.72, z2 - 0.1)], [(ba, vb + 0.15, z2 - 1.0), (bb, vb + 0.15, z2 - 1.0)], (1, 0, 0), 0.07, 0.07, 'wood_dark', tag='detail')
    # the plaster gable/upper band under the back eave is covered by the roof's edge strip; a soffit gutter
    bars(B, [(u0, vb + s['back_o'] + 0.05, RF.zat(vb + s['back_o'] - 0.01, vb + s['back_o']) - 0.16)], [(u1, vb + s['back_o'] + 0.05, RF.zat(vb + s['back_o'] - 0.01, vb + s['back_o']) - 0.16)], (0, 0, 1), 0.09, 0.09, 'bronze', tag='detail')
