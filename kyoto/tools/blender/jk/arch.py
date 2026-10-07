"""Japanese architecture parts (local building frame: u along the front, v depth, w = z up).

pillars, tie beams (貫 nuki / 長押 nageshi / 頭貫), bracket sets (組物), wall infills (白壁, 板壁, 連子窓, 花頭窓, 蔀戸,
桟唐戸, 格子戸), verandas (縁) with railings (高欄, 擬宝珠), stairs, stone platforms (基壇), 亀腹, torii (明神鳥居),
lanterns (石灯籠, 釣灯籠, 提灯), walls and fences (築地塀, 竹垣, 生垣)."""
import math
import numpy as np
from . import prim

# ------------------------------------------------------------------ frame members
def pillar(B, x, y, z0, z1, r=0.22, mat='wood_dark', round_=True, base=True, base_mat='stone', tag='main'):
    if base: prim.cyl(B, (x, y, z0 - 0.05), (x, y, z0 + 0.12), r * 1.55, r * 1.4, 10, base_mat, tag=tag)     # 礎石
    if round_: prim.cyl(B, (x, y, z0 + 0.1), (x, y, z1), r, r * 0.97, 14, mat, caps=(False, True), tag=tag)
    else: prim.box(B, x - r, y - r, z0 + 0.1, x + r, y + r, z1, mat, tag=tag)

def grid(L, D, nu, nv):
    """pillar positions of an nu x nv bay plan (L along u, D along v), centred"""
    us = np.linspace(-L / 2, L / 2, nu + 1); vs = np.linspace(-D / 2, D / 2, nv + 1)
    return us, vs

def ring_beam(B, L, D, z, w, h, mat, tag='main', inset=0.0):
    """a beam around the pillar rectangle at height z (top at z)"""
    a, c = L / 2 - inset, D / 2 - inset
    for (p0, p1) in (((-a, -c), (a, -c)), ((a, -c), (a, c)), ((a, c), (-a, c)), ((-a, c), (-a, -c))):
        prim.obox(B, (p0[0], p0[1], z - h / 2), (p1[0], p1[1], z - h / 2), w, h, mat, tag=tag)

def beam(B, p0, p1, z, w, h, mat, tag='main'):
    prim.obox(B, (p0[0], p0[1], z - h / 2), (p1[0], p1[1], z - h / 2), w, h, mat, tag=tag)

# ------------------------------------------------------------------ bracket sets (組物)
def kumimono(B, x, y, z, out_dir, along, kind='demitsudo', s=1.0, mat='wood_dark', end_mat=None, tag='detail'):
    """a bracket set on a pillar top at (x, y, z): out_dir = unit vector (u, v) pointing out of the wall,
    along = unit vector along the wall.  kinds: 'funa' 舟肘木, 'hira' 平三斗, 'demitsudo' 出三斗, 'degumi' 出組,
    'futatesaki' 二手先, 'mitesaki' 三手先.  Returns the height of the top (where the purlin sits) and its outward reach."""
    o = np.array([out_dir[0], out_dir[1], 0.0]); a = np.array([along[0], along[1], 0.0])
    p = np.array([x, y, z])
    m = s * 0.26; mh = s * 0.17; hw = s * 0.15; hh = s * 0.17; arm = s * 0.55
    end_mat = end_mat or mat
    def masu(c, big=False):
        k = 1.5 if big else 1.0
        c = np.asarray(c, float)
        P = []
        # a block slightly wider at the top (斗): two rings
        for zz, sc in ((0.0, 0.8), (mh * k * 0.45, 0.8), (mh * k, 1.0)):
            for (du, dv) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                P.append(c + a * du * m * k * 0.5 * sc + o * dv * m * k * 0.5 * sc + [0, 0, zz])
        P = np.array(P); I = []
        for r in range(2):
            for i in range(4):
                j = (i + 1) % 4; b0 = r * 4
                I += [[b0 + i, b0 + j, b0 + 4 + j], [b0 + i, b0 + 4 + j, b0 + 4 + i]]
        I += [[8, 9, 10], [8, 10, 11]]
        B.add(P, I, mat, tag=tag)
        return c[2] + mh * k
    def hijiki(c, d, L):
        c = np.asarray(c, float)
        prim.obox(B, c - d * L / 2 + [0, 0, hh / 2], c + d * L / 2 + [0, 0, hh / 2], hw, hh, mat, tag=tag)
        # rounded ends: a short lower chamfer block at each end
        for e in (-1, 1):
            q = c + d * e * (L / 2 - hw * 0.4)
            prim.obox(B, q + [0, 0, 0.0], q + [0, 0, hh * 0.45], hw * 1.02, hw * 0.8, mat, up=tuple(d), tag=tag)
        return c[2] + hh
    if kind == 'funa':
        prim.obox(B, p - a * arm + [0, 0, hh / 2], p + a * arm + [0, 0, hh / 2], hw * 1.2, hh, mat, tag=tag)
        return z + hh, 0.0
    top = masu(p, big=True)
    if kind == 'hira':
        t = hijiki(p + [0, 0, top - z], a, arm * 2)
        for e in (-1, 0, 1): masu(p + a * e * arm * 0.9 + [0, 0, t - z])
        return t + mh, 0.0
    steps = {'demitsudo': 1, 'degumi': 1, 'futatesaki': 2, 'mitesaki': 3}[kind]
    zc = top
    reach = 0.0
    for k in range(steps + (0 if kind == 'demitsudo' else 1)):
        c = p + o * reach + [0, 0, zc - z]
        t1 = hijiki(c, a, arm * 2)                          # along the wall
        t2 = hijiki(c + o * arm * 0.5, o, arm * 1.4)        # outward
        for e in (-1, 1): masu(c + a * e * arm * 0.9 + [0, 0, t1 - c[2]])
        masu(c + o * arm * 1.0 + [0, 0, t2 - c[2]])
        zc = max(t1, t2) + mh
        reach += arm
    if steps >= 2:   # 尾垂木: a sloping tail rafter through the set
        q0 = p - o * 0.8 + [0, 0, zc - z + 0.4]; q1 = p + o * (reach + 0.4) + [0, 0, zc - z - 0.35]
        prim.obox(B, q0, q1, hw * 1.2, hh * 1.3, mat, tag=tag)
        prim.obox(B, q1, q1 + (q1 - q0) / np.linalg.norm(q1 - q0) * 0.04, hw * 1.22, hh * 1.32, end_mat, tag=tag)
    return zc, reach

def bracket_row(B, L, D, z, kind, s=1.0, mat='wood_dark', end_mat=None, us=None, vs=None, purlin=True, tag='detail'):
    """bracket sets on every outer pillar of an L x D rectangle; returns (top height, reach)"""
    us = us if us is not None else np.array([-L / 2, L / 2]); vs = vs if vs is not None else np.array([-D / 2, D / 2])
    top = z; reach = 0.0
    pts = []
    for x in us[1:-1]: pts += [((x, -D / 2), (0, -1), (1, 0)), ((x, D / 2), (0, 1), (-1, 0))]     # corners get the diagonal sets below
    for y in vs[1:-1]: pts += [((-L / 2, y), (-1, 0), (0, 1)), ((L / 2, y), (1, 0), (0, -1))]
    for (pt, od, al) in pts:
        t, r = kumimono(B, pt[0], pt[1], z, od, al, kind, s, mat, end_mat, tag)
        top = max(top, t); reach = max(reach, r)
    # corner sets point diagonally
    for sx in (-1, 1):
        for sy in (-1, 1):
            d = np.array([sx, sy]) / math.sqrt(2)
            t, r = kumimono(B, sx * L / 2, sy * D / 2, z, d, (-d[1], d[0]), kind, s, mat, end_mat, tag)
            top = max(top, t)
            if not pts: reach = max(reach, r / math.sqrt(2))      # corner pillars only: the diagonal sets carry the purlin
    if purlin:
        # 桁 / 丸桁 on top of the sets, at their outer reach
        a, c = L / 2 + reach, D / 2 + reach
        for (p0, p1) in (((-a, -c), (a, -c)), ((a, -c), (a, c)), ((a, c), (-a, c)), ((-a, c), (-a, -c))):
            prim.obox(B, (p0[0], p0[1], top + 0.12), (p1[0], p1[1], top + 0.12), 0.24 * s, 0.24 * s, mat, tag='main')
    return top + 0.24 * s, reach

# ------------------------------------------------------------------ wall infills between two pillars (in the wall plane)
def infill(B, p0, p1, z0, z1, kind='plaster', out=None, mat='wood_dark', tag='main', inset=0.06, seed=0):
    """fill the bay between pillar centres p0, p1 (2D) from z0 to z1.  out: outward 2D normal (defaults to the
    right of p0->p1).  kinds: plaster, board, renji (連子窓 band), katomado (花頭窓), shitomi (蔀戸), karado (桟唐戸
    double door), koshi (格子戸), open (nothing), noren (opening + cloth)"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L
    n = np.array([d[1], -d[0]]) if out is None else np.asarray(out, float)
    r = 0.2
    q0 = p0 + d * r; q1 = p1 - d * r; Lq = L - 2 * r
    def plane(a, b, za, zb, m, depth=inset, c0=(255, 255, 255, 0), c1=(0, 0, 0, 0)):
        A = np.r_[a + n * (-depth), za]; Bp = np.r_[b + n * (-depth), za]; C = np.r_[b + n * (-depth), zb]; D_ = np.r_[a + n * (-depth), zb]
        P = np.array([A, Bp, C, D_])
        tt = np.cross(np.r_[d, 0], [0, 0, 1.0])
        I = [[0, 1, 2], [0, 2, 3]]
        fn = np.cross(P[1] - P[0], P[2] - P[0])
        if fn @ np.r_[n, 0] < 0: I = [[0, 2, 1], [0, 3, 2]]
        UV = np.array([[0, za], [np.linalg.norm(b - a), za], [np.linalg.norm(b - a), zb], [0, zb]])
        B.add(P, I, m, UV=UV, tag=tag, c0=c0, c1=c1)
        B.add(P, [t[::-1] for t in I], m, UV=UV, tag=tag, c0=c0, c1=c1)       # and its inner side
    if kind == 'open': return
    if kind == 'plaster':
        plane(q0, q1, z0, z1, 'temple_wall', c0=(236, 232, 222, 35), c1=(0, 0, seed, 0))
    elif kind == 'board':
        plane(q0, q1, z0, z1, mat, depth=inset * 0.6)
        for x in np.arange(0.45, Lq, 0.9):                  # battens
            a = q0 + d * x
            prim.obox(B, np.r_[a + n * (-inset * 0.2), z0], np.r_[a + n * (-inset * 0.2), z1], 0.06, 0.05, mat, up=(0, 0, 1), tag='detail')
    elif kind in ('renji', 'koshi', 'shitomi'):
        # a frame; vertical (or lattice) bars with dark behind
        plane(q0, q1, z0, z1, 'glass' if kind == 'renji' else mat, depth=inset * 2.5)
        fz = [z0, z1]
        for zz in fz: prim.obox(B, np.r_[q0 - n * inset, zz], np.r_[q1 - n * inset, zz], 0.1, 0.1, mat, tag='detail')
        step = 0.11 if kind == 'renji' else 0.08
        for x in np.arange(step / 2, Lq, step):
            a = q0 + d * x
            prim.obox(B, np.r_[a - n * inset, z0], np.r_[a - n * inset, z1], 0.035, 0.035, mat, tag='detail', ends=False)
        if kind == 'shitomi':
            for zz in np.arange(z0 + 0.15, z1, 0.15):
                prim.obox(B, np.r_[q0 - n * inset * 0.8, zz], np.r_[q1 - n * inset * 0.8, zz], 0.03, 0.03, mat, tag='detail', ends=False)
    elif kind == 'katomado':
        # plastered wall with a bell-shaped (花頭) window frame
        plane(q0, q1, z0, z1, 'temple_wall', c0=(236, 232, 222, 35))
        cx = (q0 + q1) / 2; w = min(1.0, Lq * 0.35); h0 = z0 + (z1 - z0) * 0.25; h1 = z0 + (z1 - z0) * 0.8
        pts = []
        for t in np.linspace(0, 1, 18):
            ang = math.pi * t
            xx = -w / 2 * math.cos(ang); zz = h1 - 0.25 * (1 - math.sin(ang)) + 0.12 * math.sin(ang * 3) * (abs(math.cos(ang)) > 0.3)
            pts.append(np.r_[cx + d * xx - n * (inset + 0.02), zz])
        pts = [np.r_[cx - d * w / 2 - n * (inset + 0.02), h0]] + pts + [np.r_[cx + d * w / 2 - n * (inset + 0.02), h0], np.r_[cx - d * w / 2 - n * (inset + 0.02), h0]]
        prim.sweep(B, np.array(pts), [(-0.06, 0.0), (0.06, 0.0), (0.06, 0.06), (-0.06, 0.06)], mat, up=(n[0], n[1], 0), tag='detail')
    elif kind in ('karado', 'noren'):
        plane(q0, q1, z0, z1, 'glass' if kind == 'noren' else mat, depth=inset * (3 if kind == 'noren' else 1))
        if kind == 'karado':
            for x in (Lq * 0.25, Lq * 0.5, Lq * 0.75):
                a = q0 + d * x
                prim.obox(B, np.r_[a - n * inset * 0.2, z0], np.r_[a - n * inset * 0.2, z1], 0.08, 0.05, mat, tag='detail')
            for zz in np.linspace(z0 + 0.2, z1 - 0.1, 4):
                prim.obox(B, np.r_[q0 - n * inset * 0.2, zz], np.r_[q1 - n * inset * 0.2, zz], 0.06, 0.05, mat, tag='detail')
        else:
            plane(q0, q1, z1 - 0.9, z1, 'cloth', depth=-0.02, c0=(30, 40, 90, 0))

def nageshi(B, L, D, z, mat='wood_dark', h=0.22, w=0.12, sides=(0, 1, 2, 3), out=0.2, tag='main'):
    """長押 / 貫 around the outside of the pillar rectangle (proud of the pillars by `out`)"""
    a, c = L / 2, D / 2
    segs = [((-a - out, -c - out), (a + out, -c - out)), ((a + out, -c - out), (a + out, c + out)), ((a + out, c + out), (-a - out, c + out)), ((-a - out, c + out), (-a - out, -c - out))]
    for k in sides:
        p0, p1 = segs[k]
        prim.obox(B, (p0[0], p0[1], z - h / 2), (p1[0], p1[1], z - h / 2), w, h, mat, tag=tag)

# ------------------------------------------------------------------ verandas, railings, stairs, platforms
def veranda(B, L, D, z, width=1.2, mat='wood_natural', post_mat='wood_dark', sides=(0, 1, 2, 3), tag='main'):
    """縁: planks around the pillar rectangle at floor height z, on short posts"""
    a, c = L / 2, D / 2; w = width
    rects = {0: (-a - w, -c - w, a + w, -c), 1: (a, -c - w, a + w, c + w), 2: (-a - w, c, a + w, c + w), 3: (-a - w, -c - w, -a, c + w)}
    for k in sides:
        x0, y0, x1, y1 = rects[k]
        prim.box(B, x0, y0, z - 0.09, x1, y1, z, mat, tag=tag)
    for k in sides:
        x0, y0, x1, y1 = rects[k]
        for t in np.arange(0, 1.0001, 1 / max(1, round(max(x1 - x0, y1 - y0) / 1.8))):
            px = x0 + (x1 - x0) * t if (x1 - x0) > (y1 - y0) else (x0 + x1) / 2
            py = y0 + (y1 - y0) * t if (y1 - y0) >= (x1 - x0) else (y0 + y1) / 2
            if k in (0, 2): py = y0 if k == 0 else y1
            else: px = x1 if k == 1 else x0
            prim.box(B, px - 0.07, py - 0.07, 0.0 + z - 1.5, px + 0.07, py + 0.07, z - 0.09, post_mat, tag='detail')

def railing(B, pts, z, h=0.8, mat='vermilion', cap_mat='bronze', giboshi=True, tag='main', closed=False):
    """高欄 along a 2D polyline at floor height z: posts at the corners (擬宝珠 caps), top rail (架木), mid rail (平桁),
    bottom rail (地覆), short struts (束)"""
    pts = [np.asarray(p, float) for p in pts]
    if closed: pts = pts + [pts[0]]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        for zz, w, hh in ((z + h, 0.09, 0.09), (z + h * 0.55, 0.07, 0.08), (z + 0.06, 0.12, 0.12)):
            prim.obox(B, np.r_[a, zz - hh / 2], np.r_[b, zz - hh / 2], w, hh, mat, tag=tag)
        L = np.linalg.norm(b - a)
        for t in np.arange(0.6, L, 0.9):
            q = a + (b - a) * t / L
            prim.obox(B, np.r_[q, z + 0.12], np.r_[q, z + h * 0.55], 0.06, 0.06, mat, tag='detail')
    for p in pts:
        prim.cyl(B, np.r_[p, z], np.r_[p, z + h + 0.15], 0.07, 0.065, 8, mat, tag=tag)
        if giboshi:
            prim.lathe(B, np.r_[p, z + h + 0.15], [(0.08, 0.0), (0.09, 0.05), (0.06, 0.09), (0.1, 0.16), (0.08, 0.24), (0.03, 0.3), (0.0, 0.34)], 10, cap_mat, tag='detail')

def stairs(B, p0, p1, z0, z1, width, mat='stone', tag='main', riser=0.17, cheeks=None, walk=True):
    """straight flight from (p0, z0) to (p1, z1) (2D points), treads of equal rise; cheek boards if given a material"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]])
    k = max(1, int(round(abs(z1 - z0) / riser)))
    for i in range(k):
        t0, t1 = i / k, (i + 1) / k
        za = z0 + (z1 - z0) * (i + 1) / k
        a = p0 + d * L * t0; b = p0 + d * L * t1
        P = np.array([np.r_[a - n * width / 2, z0 - 0.3], np.r_[b - n * width / 2, z0 - 0.3], np.r_[b + n * width / 2, z0 - 0.3], np.r_[a + n * width / 2, z0 - 0.3]])
        # one block per step (top + front)
        P = np.array([np.r_[a - n * width / 2, za], np.r_[b - n * width / 2, za], np.r_[b + n * width / 2, za], np.r_[a + n * width / 2, za],
                      np.r_[a - n * width / 2, za - (z1 - z0) / k], np.r_[a + n * width / 2, za - (z1 - z0) / k]])
        B.add(P, [[0, 1, 2], [0, 2, 3], [4, 0, 3], [4, 3, 5]], mat, tag=tag)
        for sgn, (i0, i1) in ((-1, (0, 1)), (1, (3, 2))):
            S = np.array([P[i0], P[i1], np.r_[P[i1][:2], z0 - 0.2], np.r_[P[i0][:2], z0 - 0.2]])
            II = [[0, 2, 1], [0, 3, 2]] if sgn < 0 else [[0, 1, 2], [0, 2, 3]]
            B.add(S, II, mat, tag=tag)
    if walk:
        P = np.array([np.r_[p0 - n * width / 2, z0], np.r_[p1 - n * width / 2, z1], np.r_[p1 + n * width / 2, z1], np.r_[p0 + n * width / 2, z0]])
        B.add(P, [[0, 1, 2], [0, 2, 3]], 'stone', tag='walk')

def platform(B, pts, z0, z1, mat='stone', top_mat=None, tag='main', walk=True):
    """基壇: a stone platform over a polygon (CCW 2D)"""
    prim.prism(B, pts, z0, z1, mat, top_mat=top_mat or mat, tag=tag)
    if walk: prim.polygon(B, pts, z1, 'stone', tag='walk')

def kamebara(B, L, D, z0, h, mat='white_paint', tag='main'):
    """亀腹: the rounded plaster mound under a pagoda / gate"""
    a, c = L / 2, D / 2
    rings = [(1.18, 0.0), (1.15, 0.35), (1.08, 0.7), (1.0, 1.0)]
    P = []
    for (s, t) in rings:
        for (x, y) in ((-a, -c), (a, -c), (a, c), (-a, c)):
            P.append((x * s, y * s, z0 + h * t))
    I = []
    for r in range(len(rings) - 1):
        for i in range(4):
            j = (i + 1) % 4; b0 = r * 4
            I += [[b0 + i, b0 + j, b0 + 4 + j], [b0 + i, b0 + 4 + j, b0 + 4 + i]]
    B.add(np.array(P), I, mat, tag=tag)
    prim.polygon(B, [(-a, -c), (a, -c), (a, c), (-a, c)], z0 + h, mat, tag=tag)

# ------------------------------------------------------------------ torii, lanterns
def torii(B, x, y, z, yaw, h=4.0, span=3.4, r=None, color='vermilion', top='black_lacquer', base='black_lacquer', tag='main', inscription=False, lean=0.03):
    """明神鳥居 in its own frame: pillars at ±span/2 (centres), kasagi + shimaki with upturned ends, nuki, gakuzuka"""
    from .core import Frame
    r = r or max(0.06, h * 0.055)
    with Frame(B, x, y, z, yaw):
        for s in (-1, 1):
            top_x = s * (span / 2 - h * lean); bot_x = s * span / 2
            prim.cyl(B, (bot_x, 0, -0.1), (top_x, 0, h * 0.86), r, r * 0.9, 10, color, caps=(False, True), tag=tag)
            prim.cyl(B, (bot_x, 0, -0.1), (bot_x * 0.995 + top_x * 0.005, 0, h * 0.09), r * 1.18, r * 1.15, 10, base, tag=tag)     # 根巻
            prim.cyl(B, (top_x, 0, h * 0.86), (top_x, 0, h * 0.89), r * 1.25, r * 1.25, 10, color, tag='detail')                       # 台輪
        # 貫 (tie beam) through the pillars, slightly proud
        nz = h * 0.68
        prim.obox(B, (-span / 2 - r * 2.2, 0, nz), (span / 2 + r * 2.2, 0, nz), r * 0.9, r * 1.4, color, tag=tag)
        # 額束 (central strut)
        prim.obox(B, (0, 0, nz + r * 0.7), (0, 0, h * 0.89), r * 1.1, r * 0.8, color, tag=tag)
        # 島木 + 笠木 with 反り (upturned ends)
        ext = span / 2 + h * 0.18
        xs = np.linspace(-ext, ext, 13)
        lift = lambda xx: h * 0.035 * (abs(xx) / ext) ** 2.2
        z1 = h * 0.89
        pts = np.array([(xx, 0, z1 + r * 0.6 + lift(xx)) for xx in xs])
        prim.sweep(B, pts, [(-r * 1.0, -r * 0.6), (r * 1.0, -r * 0.6), (r * 1.0, r * 0.6), (-r * 1.0, r * 0.6)], color, up=(0, 0, 1), tag=tag, caps=True)
        pts2 = np.array([(xx * 1.04, 0, z1 + r * 1.2 + r * 0.55 + lift(xx) * 1.4) for xx in xs])
        prim.sweep(B, pts2, [(-r * 1.25, -r * 0.55), (r * 1.25, -r * 0.55), (r * 1.4, r * 0.55), (-r * 1.4, r * 0.55)], top, up=(0, 0, 1), tag=tag, caps=True)
        if inscription:
            # the donor's inscription panel on the back of the pillar (black ink on vermilion): a thin plate
            for s in (-1, 1):
                bx = s * span / 2
                P = np.array([(bx - r * 0.8, r * 1.02, h * 0.25), (bx + r * 0.8, r * 1.02, h * 0.25), (bx + r * 0.8, r * 1.02, h * 0.62), (bx - r * 0.8, r * 1.02, h * 0.62)])
                B.add(P, [[0, 2, 1], [0, 3, 2]], color, UV=np.array([[0, 0], [1, 0], [1, 1], [0, 1]]), tag='detail', c1=(0, 7, 0, 0))

def ishidoro(B, x, y, z, h=2.0, mat='stone', tag='main', lamp=True):
    """石灯籠 (kasuga style): base, pole, middle platform, fire box, hexagonal roof, jewel"""
    s = h / 2.0
    prim.cyl(B, (x, y, z), (x, y, z + 0.25 * s), 0.32 * s, 0.28 * s, 6, mat, tag=tag)
    prim.cyl(B, (x, y, z + 0.25 * s), (x, y, z + 0.95 * s), 0.11 * s, 0.1 * s, 10, mat, tag=tag)
    prim.cyl(B, (x, y, z + 0.95 * s), (x, y, z + 1.1 * s), 0.22 * s, 0.26 * s, 6, mat, tag=tag)
    prim.cyl(B, (x, y, z + 1.1 * s), (x, y, z + 1.45 * s), 0.2 * s, 0.2 * s, 6, mat, tag=tag)
    if lamp: prim.cyl(B, (x, y, z + 1.17 * s), (x, y, z + 1.38 * s), 0.205 * s, 0.205 * s, 6, 'lantern_paper', caps=(False, False), tag='detail')
    prim.lathe(B, (x, y, z + 1.45 * s), [(0.42 * s, 0.0), (0.44 * s, 0.05 * s), (0.3 * s, 0.18 * s), (0.08 * s, 0.3 * s), (0.1 * s, 0.38 * s), (0.0, 0.5 * s)], 6, mat, tag=tag, smooth=False)

def chochin(B, x, y, z, r=0.2, h=0.55, tag='main'):
    """提灯: a paper lantern (lit), black caps"""
    prim.lathe(B, (x, y, z), [(r * 0.75, 0.0), (r, h * 0.2), (r * 1.02, h * 0.5), (r, h * 0.8), (r * 0.75, h)], 12, 'lantern_paper', tag=tag)
    prim.cyl(B, (x, y, z - 0.04), (x, y, z + 0.01), r * 0.78, r * 0.78, 12, 'black_lacquer', tag='detail')
    prim.cyl(B, (x, y, z + h - 0.01), (x, y, z + h + 0.05), r * 0.78, r * 0.78, 12, 'black_lacquer', tag='detail')
    B.lamp(x, y, z + h / 2, 8.0, (1.0, 0.55, 0.25))

# ------------------------------------------------------------------ walls and fences
def tsuiji(B, pts, z0, h=2.4, th=0.6, stripes=0, tag='main', ground=None):
    """築地塀: earthen wall with a stone base, ochre or white plaster, tiled coping; `stripes` white lines (筋塀).
    ground(x, y) -> z follows the terrain."""
    pts = [np.asarray(p, float) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; d = b - a; L = np.linalg.norm(d)
        if L < 0.1: continue
        d /= L; n = np.array([-d[1], d[0]])
        k = max(1, int(L / 2.0))
        for j in range(k):
            p = a + d * L * j / k; q = a + d * L * (j + 1) / k
            zp = ground(*p) if ground else z0; zq = ground(*q) if ground else z0
            zz = min(zp, zq)
            for side in (-1, 1):
                A = p + n * side * th / 2; Bq = q + n * side * th / 2
                P = np.array([np.r_[A, zz - 0.3], np.r_[Bq, zz - 0.3], np.r_[Bq, zz + h], np.r_[A, zz + h]])
                I = [[0, 2, 1], [0, 3, 2]] if side > 0 else [[0, 1, 2], [0, 2, 3]]
                B.add(P, I, 'temple_wall', UV=np.array([[0, zz - 0.3], [L / k, zz - 0.3], [L / k, zz + h], [0, zz + h]]), tag=tag,
                      c0=(214, 184, 120, 35) if not stripes else (240, 236, 226, 35), c1=(0, 0, 0, 0))
            # coping: a small gable roof of tiles
            for side in (-1, 1):
                A = p + n * side * (th / 2 + 0.25); Bq = q + n * side * (th / 2 + 0.25)
                P = np.array([np.r_[A, zz + h - 0.05], np.r_[Bq, zz + h - 0.05], np.r_[q, zz + h + 0.35], np.r_[p, zz + h + 0.35]])
                I = [[0, 1, 2], [0, 2, 3]] if side < 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I, 'kawara', UV=np.array([[0, 0], [L / k, 0], [L / k, 0.5], [0, 0.5]]), tag=tag)
            prim.obox(B, np.r_[p, zz + h + 0.42], np.r_[q, zz + h + 0.42], 0.22, 0.14, 'ridge', tag=tag)
        if stripes:
            for s_ in range(stripes):
                zz = (ground(*a) if ground else z0) + h * (0.55 + 0.08 * s_)
                for side in (-1, 1):
                    prim.obox(B, np.r_[a + n * side * (th / 2 + 0.01), zz], np.r_[b + n * side * (th / 2 + 0.01), zz], 0.02, 0.05, 'white_paint', tag='detail')

def takegaki(B, pts, z0, h=1.5, kind='kenninji', tag='main', ground=None):
    """竹垣: 建仁寺垣 (close vertical split bamboo with horizontal ties) or 四つ目垣 (open grid)"""
    pts = [np.asarray(p, float) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; d = b - a; L = np.linalg.norm(d)
        if L < 0.1: continue
        d /= L; n = np.array([-d[1], d[0]])
        zz = ground(*((a + b) / 2)) if ground else z0
        for t in np.arange(0, L + 0.01, 1.8):
            q = a + d * t
            prim.cyl(B, np.r_[q, zz - 0.2], np.r_[q, zz + h + 0.05], 0.045, 0.045, 6, 'wood_dark', tag=tag)
        if kind == 'kenninji':
            for side in (-1, 1):
                P = np.array([np.r_[a + n * side * 0.03, zz], np.r_[b + n * side * 0.03, zz], np.r_[b + n * side * 0.03, zz + h], np.r_[a + n * side * 0.03, zz + h]])
                I = [[0, 1, 2], [0, 2, 3]] if side > 0 else [[0, 2, 1], [0, 3, 2]]
                B.add(P, I, 'bamboo', UV=np.array([[0, 0], [L, 0], [L, h], [0, h]]), tag=tag, c1=(0, 1, 0, 0))
            for zt in np.linspace(zz + 0.25, zz + h - 0.15, 4):
                for side in (-1, 1):
                    prim.cyl(B, np.r_[a + n * side * 0.06, zt], np.r_[b + n * side * 0.06, zt], 0.022, 0.022, 6, 'bamboo', tag='detail')
        else:
            for zt in np.linspace(zz + 0.3, zz + h - 0.1, 4):
                prim.cyl(B, np.r_[a, zt], np.r_[b, zt], 0.018, 0.018, 6, 'bamboo', tag='detail')
            for t in np.arange(0.15, L, 0.3):
                q = a + d * t
                prim.cyl(B, np.r_[q + n * 0.03, zz - 0.1], np.r_[q + n * 0.03, zz + h], 0.016, 0.016, 5, 'bamboo', tag='detail')

def hedge(B, pts, z0, h=1.2, w=0.7, tag='main', ground=None):
    """生垣: a clipped hedge (drawn with the hedge program)"""
    pts = [np.asarray(p, float) for p in pts]
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; d = b - a; L = np.linalg.norm(d)
        if L < 0.1: continue
        d /= L; n = np.array([-d[1], d[0]])
        zz = ground(*((a + b) / 2)) if ground else z0
        P = [np.r_[a + n * w / 2, zz - 0.1], np.r_[b + n * w / 2, zz - 0.1], np.r_[b - n * w / 2, zz - 0.1], np.r_[a - n * w / 2, zz - 0.1]]
        P += [np.r_[a + n * w * 0.42, zz + h], np.r_[b + n * w * 0.42, zz + h], np.r_[b - n * w * 0.42, zz + h], np.r_[a - n * w * 0.42, zz + h]]
        P = np.array(P)
        I = [[0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7], [4, 5, 6], [4, 6, 7]]
        B.add(P, I, 'hedge', tag=tag)
