"""二十八部衆: the 28 attendants of 三十三間堂 (Kamakura, mostly Kei school, hinoki yosegi, crystal eyes, faded polychrome).
Each is a spec (pose in head units, costume, head, attributes, palette) run through one generator.  They stand on
rock bases (岩座) on a low board.  Names, order and heights follow heroes/sanjusangendo_slots.json (2018 layout)."""
import math, zlib
import numpy as np
from . import statues_sdf as S
from . import statues_body as Bd
from . import statues_props as X
from .statues_sdf import Sphere, Ellipsoid, RCone, Capsule, Box, Torus, Cyl, Plane, Fn, Shell, Inter, Union, Diff, Displace, Tube, Loft, Field, frame, rot, euler, nrm, fbm, Offset
from .statues_body import L, A, Band, Sweep, spline

def sid(name): return name.lower().replace('-', '_')

# ---------------------------------------------------------------------------------------------- palettes
def mute(c, k=0.42, to=(66, 58, 50)):
    return tuple(int(round(v * (1 - k) + t * k)) for v, t in zip(c, to))

def att_palette(c):
    from .statues_build import palette
    c = {k: (mute(v) if isinstance(v, tuple) and len(v) == 3 and k not in ('skin',) else v) for k, v in c.items()}
    if 'skin' in c: c['skin'] = mute(c['skin'], 0.25)
    sk = c.get('skin', (84, 72, 60))
    p = palette(skin=sk, skin2=tuple(int(v * 0.85) for v in sk), hair=c.get('hair', (40, 36, 34)), eye=('glass', (0, 0, 0)), eyew=(128, 116, 96),
                lip=tuple(int(v * 0.9) for v in sk) if 'lip' not in c else c['lip'], teeth=(170, 160, 132), mouth=(100, 40, 30),
                robe=c.get('robe', mute((98, 58, 46))), robe2=c.get('robe2', mute((60, 78, 64))), robe3=c.get('robe3', mute((70, 72, 84))), lining=c.get('lining', mute((120, 70, 44))),
                scarf=c.get('scarf', mute((86, 70, 56))), armour=c.get('armour', mute((66, 62, 56))), armour2=c.get('armour2', mute((62, 64, 60))), armour3=c.get('armour3', mute((88, 62, 48))),
                trim='gold', boss='gold', jewel='gold', crown='gold', halo='gold', halo2=c.get('halo2', 'gold'), gold='gold',
                belt=c.get('belt', (78, 58, 44)), shoe=c.get('shoe', (44, 38, 34)), rock=c.get('rock', (74, 66, 58)), base='wood_dark', wood='wood_dark',
                rod='wood_dark', weapon='gold', attr='gold', attr2=c.get('attr2', (90, 70, 50)), snake=c.get('snake', (70, 84, 60)), feather=c.get('feather', (84, 70, 52)),
                beard=(150, 140, 120), cap=c.get('cap', (82, 66, 52)), drum=c.get('drum', (120, 80, 56)), nail=(60, 50, 40), dark='black_lacquer', bag=(80, 76, 62))
    return p

# ---------------------------------------------------------------------------------------------- pieces
def rock_base(f, rng, w, d, h, z_top, lab='rock'):
    """岩座: a lumpy rock slab whose top is at z_top (around the feet), on a board below"""
    def lump(P): return (0.018 * fbm(P, 0.09, 3, int(rng.integers(0, 999))) + 0.008 * fbm(P, 0.035, 2, 5)).astype(np.float32)
    rk = Box(A(0, 0.0, z_top - h / 2), A(w / 2, d / 2, h / 2), None, 0.05)
    f.add(Displace(rk, lump, 0.027), L[lab], 0.0)
    for i in range(6):
        a = rng.uniform(0, 2 * math.pi)
        p = A(math.cos(a) * w * 0.36, math.sin(a) * d * 0.33, z_top - h * rng.uniform(0.3, 0.7))
        f.add(Ellipsoid(p, A(rng.uniform(0.07, 0.12), rng.uniform(0.06, 0.1), h * 0.45)), L[lab], 0.04)

def eye_extra(f, R, O, hh, pos, vertical=True):
    """an extra (third) eye on the forehead"""
    P = O + R @ (A(*pos) * hh)
    f.sub(Ellipsoid(P + R @ A(0, 0.03, 0) * hh, A(0.04, 0.03, 0.065) * hh if vertical else A(0.065, 0.03, 0.04) * hh, R), 0.012 * hh)
    f.add(Ellipsoid(P, A(0.032, 0.03, 0.05) * hh if vertical else A(0.05, 0.03, 0.032) * hh, R), L['eyew'], 0.004 * hh)
    f.paint(Sphere(P + R @ A(0, 0.03, 0) * hh, 0.022 * hh), L['eye'])

def snake_tube(f, pts, r0, lab='snake', head=True):
    pts = spline(pts, max(12, 6 * len(pts)))
    rad = np.linspace(r0 * 0.7, r0, len(pts)); rad[-3:] = r0 * 1.15
    f.add(Tube(pts, rad), L[lab], r0 * 0.4)
    if head:
        d = nrm(pts[-1] - pts[-3]); e = pts[-1] + d * r0 * 1.2
        f.add(Ellipsoid(e, A(r0 * 1.25, r0 * 2.1, r0 * 0.9), frame(y=d, z=(0, 0, 1)) if abs(d[2]) < 0.9 else frame(y=d, x=(1, 0, 0))), L[lab], r0 * 0.5)
        for s in (1, -1):
            side = nrm(np.cross(d, (0, 0, 1))) if abs(d[2]) < 0.9 else A(1, 0, 0)
            f.add(Sphere(e + side * s * r0 * 0.9 + A(0, 0, r0 * 0.5), r0 * 0.35), L['eye'], 0.0)

def crown(f, R, O, hh, kind='flame', lab='crown'):
    """宝冠 on a topknot: a band at the hairline, a front ornament (flame / disc), side ornaments"""
    P = lambda v: O + R @ (A(*v) * hh)
    f.add(Band(P((0, -0.05, 0.25)), 0.37 * hh, 0.43 * hh, 0.016 * hh, 0.035 * hh, R @ rot((1, 0, 0), -0.08)), L[lab], 0.004 * hh)
    if kind in ('flame', 'tall'):
        tall = 1.0 if kind == 'flame' else 1.35
        # front ornament: a thin flame-shaped plate with two curling side lobes and a jewel
        f.add(Ellipsoid(P((0, 0.34, 0.4 + 0.04 * tall)), A(0.075, 0.014, 0.13 * tall) * hh, R @ rot((1, 0, 0), -0.22)), L[lab], 0.004 * hh)
        for s in (1, -1):
            f.add(Ellipsoid(P((s * 0.085, 0.33, 0.36)), A(0.05, 0.012, 0.08) * hh, R @ rot((1, 0, 0), -0.2) @ rot((0, 1, 0), -s * 0.6)), L[lab], 0.004 * hh)
        f.add(Sphere(P((0, 0.36, 0.33)), 0.035 * hh), L['jewel'], 0.004 * hh)
        for s in (1, -1):
            f.add(Ellipsoid(P((s * 0.33, 0.1, 0.36)), A(0.016, 0.08, 0.12) * hh, R @ rot((0, 1, 0), -s * 0.35)), L[lab], 0.004 * hh)
    elif kind == 'disc':
        f.add(Cyl(P((0, 0.3, 0.42)), P((0, 0.34, 0.42)), 0.12 * hh, 0.01 * hh), L[lab], 0.005 * hh)

def helmet(f, R, O, hh, lab='armour', crest=True):
    """兜 with flaring neck guard (錣) and a crest"""
    P = lambda v: O + R @ (A(*v) * hh)
    f.add(Inter([Ellipsoid(P((0, -0.05, 0.12)), A(0.41, 0.48, 0.5) * hh, R), Plane(P((0, 0.33, 0.18)), R @ nrm(A(0, 0.45, -1)))], 0.02 * hh), L[lab], 0.01 * hh)
    f.add(Band(P((0, -0.04, 0.2)), 0.42 * hh, 0.5 * hh, 0.02 * hh, 0.035 * hh, R @ rot((1, 0, 0), -0.25)), L['trim'], 0.005 * hh)
    # neck guard: a flared skirt round the back and sides
    def flare(P_):
        q = (P_ - O) @ R / hh
        r = np.sqrt(q[:, 0] ** 2 + (q[:, 1] + 0.08) ** 2)
        z = q[:, 2]
        rr = 0.44 + 0.35 * np.clip(-(z - 0.1) / 0.5, 0, 1)
        d1 = np.abs(r - rr) - 0.025
        d2 = np.maximum(z - 0.12, -0.42 - z)
        d3 = q[:, 1] - 0.15 + 0.3 * np.clip(-(z - 0.1), 0, 1)       # open in front of the face
        return (np.maximum(np.maximum(d1, d2), d3) * hh).astype(np.float32)
    f.add(Fn(flare, O - 1.0 * hh, O + 1.0 * hh), L[lab], 0.01 * hh)
    if crest:
        f.add(Ellipsoid(P((0, 0.25, 0.6)), A(0.05, 0.12, 0.22) * hh, R @ rot((1, 0, 0), -0.4)), L['trim'], 0.02 * hh)

def flaring_sleeve(f, fig, a, lab='robe2', size=1.0, swing=(0, -1, -0.4)):
    """広袖: the under-robe sleeve wraps the upper arm, opens at the elbow into a short flared cuff, and its loose end
    trails backward like a flag; the armoured forearm comes out of the cuff"""
    hh = fig.hh; S_, E, W = a['S'], a['E'], a['W']; s = a['s']
    up = nrm(E - S_); fore = nrm(W - E)
    f.add(RCone(S_ + up * 0.12 * hh, E, 0.28 * hh * size, 0.3 * hh * size), L[lab], 0.03 * hh)
    b0 = E - fore * 0.1 * hh; b1 = E + fore * 0.3 * hh * size
    cone = RCone(b0, b1, 0.29 * hh * size, 0.42 * hh * size)
    bell = Inter([Shell(cone, 0.02 * hh), Plane(b0 + fore * 0.04 * hh, -fore), Plane(b1 - fore * 0.03 * hh, fore)], 0.005 * hh)
    f.add(bell, L[lab], 0.015 * hh)
    # trailing flap from the back of the cuff
    sw = nrm(np.asarray(swing, float))
    back = nrm(np.cross(fore, (0, 0, 1)) * -s) if abs(fore[2]) < 0.9 else A(0, -1, 0)
    p0 = E + fore * 0.05 * hh - up * 0.25 * hh * size
    pts = spline([p0, p0 + (sw * 0.35 - up * 0.2) * hh * size, p0 + (sw * 0.7 - up * 0.25 + A(0, 0, 0.1)) * hh * size, p0 + (sw * 1.05 - up * 0.1 + A(0, 0, 0.25)) * hh * size], 24)
    nml = nrm(np.cross(sw, up)) if np.linalg.norm(np.cross(sw, up)) > 1e-3 else A(1, 0, 0)
    ws = np.linspace(0.3, 0.2, len(pts)) * hh * size
    def wave(P): return (0.012 * hh * np.sin((P @ sw) / hh * 12.0)).astype(np.float32)
    f.add(Displace(Sweep(pts, ws, 0.018 * hh, [nml] * len(pts)), wave, 0.013 * hh), L[lab], 0.02 * hh)

def hanging_sleeve(f, fig, a, lab='robe', length=1.6, width=0.55):
    """唐服 long sleeve: a wide sleeve over the arm whose cuff hangs as a long soft fold below the forearm"""
    hh = fig.hh; S_, E, W = a['S'], a['E'], a['W']; s = a['s']
    fore = nrm(W - E)
    f.add(RCone(S_, E, 0.29 * hh, 0.3 * hh), L[lab], 0.05 * hh)
    f.add(RCone(E, W - fore * 0.08 * hh, 0.3 * hh, 0.34 * hh), L[lab], 0.04 * hh)
    top = E + (W - E) * 0.55
    w = 0.2 * hh * width / 0.5
    pts = spline([top, top + A(s * 0.03, -0.04, -0.4 * length) * hh, W + A(s * 0.06, -0.08, -length) * hh], 9)
    out = nrm(A(s * 0.55, 1, 0))
    ws = np.linspace(0.75, 1.0, len(pts)) * w
    sl = Sweep(pts, ws, 0.075 * hh, [out] * len(pts))
    def folds(P): return (-0.004 * np.cos((P @ np.cross(out, (0, 0, 1))) / hh * 16.0)).astype(np.float32)
    f.add(Displace(sl, folds, 0.005), L[lab], 0.07 * hh)
    f.add(Torus(W - fore * 0.04 * hh, 0.3 * hh, 0.035 * hh, frame(z=fore, x=(0, 0, 1) if abs(fore[2]) < 0.9 else (1, 0, 0))), L['lining'], 0.02 * hh)

def stance_center(fig):
    kr, kl = fig.leg['r']['K'], fig.leg['l']['K']; ar, al = fig.leg['r']['A'], fig.leg['l']['A']
    return kr, kl, ar, al

def skirt_rows(fig, z_top, z_bot, extra=0.0, flare=0.25):
    """ellipse rows round the legs from z_bot up to z_top (follows the legs' spread)"""
    hh = fig.hh
    rows = []
    for z in np.linspace(z_bot, z_top, 6):
        xs = []; ys = []
        for nm, g in fig.leg.items():
            Hj, K, Ak = g['H'], g['K'], g['A']
            pts = [Hj, K, Ak]
            # point on the leg at this z
            if z >= K[2]: t = (z - K[2]) / max(Hj[2] - K[2], 1e-6); p = K + (Hj - K) * np.clip(t, 0, 1)
            else: t = (z - Ak[2]) / max(K[2] - Ak[2], 1e-6); p = Ak + (K - Ak) * np.clip(t, 0, 1)
            xs.append(p[0]); ys.append(p[1])
        cx = (xs[0] + xs[1]) / 2; cy = (ys[0] + ys[1]) / 2
        u = (z_top - z) / max(z_top - z_bot, 1e-6)
        rx = abs(xs[0] - xs[1]) / 2 + (0.42 + extra + flare * u) * hh
        ry = abs(ys[0] - ys[1]) / 2 + (0.36 + extra + flare * 0.6 * u) * hh
        rows.append((z, cx, cy, rx, ry))
    return rows

def panel_fn(c, n, amp, phase=0.0):
    c = np.asarray(c, np.float32)
    def f(P):
        th = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])
        w = np.cos(n * th + phase)
        return (-amp * np.tanh(3 * w)).astype(np.float32)
    return f

def fold_fn(c, n, amp, seed=0.0):
    c = np.asarray(c, np.float32)
    def f(P):
        th = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])
        return (-amp * (0.7 * np.cos(n * th + seed + 3.0 * P[:, 2]) + 0.3 * np.cos(2.3 * n * th + 1.7 * seed))).astype(np.float32)
    return f

# ---------------------------------------------------------------------------------------------- costumes
def costume_armour(f, fig, sp, rng):
    hh = fig.hh; Op = fig.Op; Rc, Oc = fig.Rc, fig.Oc
    zt = Op[2] + 0.32 * hh
    # under-skirt (裳) to mid-shin
    rows = skirt_rows(fig, zt, 1.05 * hh, extra=0.0, flare=0.3)
    c = (rows[0][1], rows[0][2])
    f.add(Displace(Loft(rows), fold_fn((c[0], c[1], 0), 11, 0.012 * hh / 0.27 * 0.27, rng.uniform(0, 6)), 0.015), L['robe'], 0.02 * hh)
    # armour skirt (腰甲) to above the knees, panelled
    rows2 = skirt_rows(fig, zt, Op[2] - 0.95 * hh, extra=0.08, flare=0.2)
    f.add(Displace(Loft(rows2), panel_fn((c[0], c[1], 0), 7, 0.012), 0.013), L['armour'], 0.01 * hh)
    # front apron (前楯)
    fy = rows2[-1][2] + rows2[-1][4] + 0.02 * hh
    ap_top = Op + A(0, 0, 0.12 * hh); ap_bot = A(c[0], fy + 0.04 * hh, Op[2] - 1.35 * hh)
    f.add(Box((ap_top + ap_bot) / 2 + A(0, fy - (ap_top[1] + ap_bot[1]) / 2 + 0.02 * hh, 0), A(0.26 * hh, 0.03 * hh, (ap_top[2] - ap_bot[2]) / 2), None, 0.02 * hh), L['armour2'], 0.01 * hh)
    # belt + lion-face buckle (獅噛)
    f.add(Band(Op + A(0, 0.02, 0.3 * hh), 0.7 * hh, 0.55 * hh, 0.05 * hh, 0.08 * hh, fig.Rp), L['belt'], 0.01 * hh)
    bk = Op + fig.Rp @ A(0, 0.6, 0.32) * hh
    f.add(Ellipsoid(bk, A(0.17, 0.06, 0.13) * hh, fig.Rp), L['boss'], 0.01 * hh)
    for s in (1, -1): f.add(Sphere(bk + fig.Rp @ A(s * 0.06, 0.05, 0.04) * hh, 0.03 * hh), L['boss'], 0.01 * hh)
    # cuirass: a shell round the chest, round bosses on the breast, a chest band
    chest = Ellipsoid(Oc + Rc @ A(0, 0.03, 0.02) * hh, A(0.76, 0.6, 0.8) * hh, Rc)
    f.add(Inter([Shell(chest, 0.035 * hh), Plane(Oc + Rc @ A(0, 0, 0.62) * hh, Rc[:, 2]), Plane(Oc + Rc @ A(0, 0, -0.62) * hh, -Rc[:, 2])], 0.01 * hh), L['armour'], 0.02 * hh)
    for s in (1, -1):
        f.add(Ellipsoid(Oc + Rc @ A(s * 0.3, 0.63, 0.12) * hh, A(0.13, 0.04, 0.13) * hh, Rc), L['boss'], 0.01 * hh)
    f.add(Band(Oc + Rc @ A(0, 0.04, -0.28) * hh, 0.77 * hh, 0.6 * hh, 0.035 * hh, 0.05 * hh, Rc), L['belt'], 0.008 * hh)
    # collar / neck guard
    f.add(Torus(fig.N + Rc @ A(0, 0.05, -0.05) * hh, 0.36 * hh, 0.07 * hh, Rc @ rot((1, 0, 0), -0.25)), L['armour2'], 0.03 * hh)
    # shoulder guards, sleeves, forearm guards
    for nm, a in fig.arm.items():
        s = a['s']
        up = nrm(a['E'] - a['S'])
        Rs = frame(z=up, x=A(s, 0, 0) - up * (up[0] * s))
        sh = Ellipsoid(a['S'] + up * 0.12 * hh + A(s * 0.02, 0, 0.02) * hh, A(0.33, 0.33, 0.4) * hh, Rs)
        f.add(Inter([Shell(sh, 0.02 * hh), Plane(a['S'] + up * 0.38 * hh, up), Plane(a['S'] + A(-s * 0.12, 0, 0) * hh, A(-s, 0, 0))], 0.008 * hh), L['armour'], 0.006 * hh)
        f.add(Ellipsoid(a['S'] + up * 0.1 * hh + A(s * 0.33, 0.04, 0.02) * hh, A(0.04, 0.1, 0.09) * hh, Rs), L['boss'], 0.01 * hh)
        flaring_sleeve(f, fig, a, 'robe2', size=sp.get('sleeve', 1.0), swing=(s * 0.4, -1, -0.5))
        f.add(RCone(a['E'] + nrm(a['W'] - a['E']) * 0.25 * hh, a['W'] - nrm(a['W'] - a['E']) * 0.02 * hh, 0.21 * hh, 0.17 * hh), L['armour'], 0.02 * hh)
    # greaves + boots
    for nm, g in fig.leg.items():
        K, Ak = g['K'], g['A']
        f.add(RCone(K + nrm(Ak - K) * 0.15 * hh, Ak + A(0, 0, 0.05) * hh, 0.25 * hh, 0.2 * hh), L['armour'], 0.02 * hh)
        fd = nrm(g['foot_dir'] * A(1, 1, 0))
        f.add(Ellipsoid(A(Ak[0], Ak[1], Ak[2] - 0.14 * hh) + fd * 0.25 * hh, A(0.26, 0.52, 0.18) * hh, frame(y=fd, z=(0, 0, 1))), L['shoe'], 0.05 * hh)

def costume_bare(f, fig, sp, rng):
    """裳 wrapped round the hips to below the knees, a folded-over waist cloth; bare torso (Nio and the like)"""
    hh = fig.hh; Op = fig.Op
    zt = Op[2] + 0.3 * hh
    rows = skirt_rows(fig, zt, sp.get('skirt_bot', 1.25) * hh, extra=0.02, flare=0.35)
    c = (rows[0][1], rows[0][2])
    f.add(Displace(Loft(rows), fold_fn((c[0], c[1], 0), 9, 0.02 * hh, rng.uniform(0, 6)), 0.02 * hh), L['robe'], 0.02 * hh)
    rows2 = skirt_rows(fig, zt + 0.05 * hh, Op[2] - 0.35 * hh, extra=0.1, flare=0.15)
    def hem(th): return (Op[2] - 0.35 * hh - 0.25 * hh * np.clip(np.sin(th), 0, 1) ** 2).astype(np.float32)
    from .statues_kannon import Over
    f.add(Over(rows2, hem, fold_fn((c[0], c[1], 0), 7, 0.012 * hh)), L['robe3'], 0.01 * hh)
    f.add(Band(Op + A(0, 0.02, 0.3 * hh), 0.68 * hh, 0.53 * hh, 0.04 * hh, 0.05 * hh, fig.Rp), L['belt'], 0.01 * hh)
    for nm, a in fig.arm.items():      # armlets, bracelets
        for (p, r) in ((a['S'] + (a['E'] - a['S']) * 0.45, 0.25), (a['W'] - nrm(a['W'] - a['E']) * 0.03 * hh, 0.19)):
            ax = nrm(a['E'] - a['S']) if r > 0.2 else nrm(a['W'] - a['E'])
            f.add(Torus(p, r * hh * (1 + 0.2 * fig.musc), 0.03 * hh, frame(z=ax, x=(0, 1, 0) if abs(ax[1]) < 0.9 else (1, 0, 0))), L['jewel'], 0.01 * hh)
    if sp.get('shoes', False):
        for nm, g in fig.leg.items():
            Ak = g['A']; fd = nrm(g['foot_dir'] * A(1, 1, 0))
            f.add(Ellipsoid(A(Ak[0], Ak[1], Ak[2] - 0.14 * hh) + fd * 0.25 * hh, A(0.25, 0.5, 0.17) * hh, frame(y=fd, z=(0, 0, 1))), L['shoe'], 0.05 * hh)

def costume_tang(f, fig, sp, rng):
    """唐服: long skirt to the floor, an upper robe with V collar, long hanging sleeves, shoe tips at the hem"""
    hh = fig.hh; Op = fig.Op; Rc, Oc = fig.Rc, fig.Oc
    zt = Op[2] + 0.4 * hh
    rows = skirt_rows(fig, zt, 0.04 * hh, extra=0.04, flare=0.3)
    c = (rows[0][1], rows[0][2])
    f.add(Displace(Loft(rows), fold_fn((c[0], c[1], 0), 13, 0.012 * hh, rng.uniform(0, 6)), 0.015 * hh), L['robe'], 0.02 * hh)
    # over-skirt / robe skirt to the knees with a curved hem
    rows2 = skirt_rows(fig, zt + 0.1 * hh, Op[2] - 1.4 * hh, extra=0.1, flare=0.15)
    def hem(th): return (Op[2] - 1.4 * hh + 0.35 * hh * np.clip(-np.sin(th), 0, 1) + 0.15 * hh * np.cos(2 * th) ** 2).astype(np.float32)
    from .statues_kannon import Over
    f.add(Over(rows2, hem, fold_fn((c[0], c[1], 0), 9, 0.012 * hh)), L['robe2'], 0.01 * hh)
    # upper robe over the torso
    f.add(Ellipsoid(Oc + Rc @ A(0, 0.03, 0.0) * hh, A(0.75, 0.6, 0.8) * hh, Rc), L['robe2'], 0.06 * hh)
    f.add(Ellipsoid(fig.W + A(0, 0.03, 0) * hh, A(0.68, 0.55, 0.6) * hh, fig.Rw), L['robe2'], 0.06 * hh)
    # V collar: two bands crossing at the chest
    for s in (1, -1):
        pts = [fig.N + Rc @ A(-s * 0.25, -0.05, 0.05) * hh, fig.N + Rc @ A(-s * 0.2, 0.42, -0.25) * hh, Oc + Rc @ A(s * 0.15, 0.68, -0.25) * hh, Oc + Rc @ A(s * 0.35, 0.6, -0.65) * hh]
        f.add(Sweep(spline(pts, 30), 0.075 * hh, 0.022 * hh, [Rc @ nrm(A(-s * 0.2, 1, 0.3))] * 30), L['lining'], 0.01 * hh)
    if sp.get('armour_under'):
        for s in (1, -1):
            f.add(Ellipsoid(Oc + Rc @ A(s * 0.3, 0.66, 0.15) * hh, A(0.14, 0.05, 0.14) * hh, Rc), L['boss'], 0.01 * hh)
    f.add(Band(Op + A(0, 0.02, 0.45 * hh), 0.7 * hh, 0.57 * hh, 0.05 * hh, 0.06 * hh, fig.Rp), L['belt'], 0.01 * hh)
    # sash ends (蔽膝) hanging in front
    f.add(Box(A(c[0], rows2[-1][2] + rows2[-1][4] + 0.05 * hh, (Op[2] + 0.4 * hh + 0.9 * hh) / 2), A(0.2 * hh, 0.025 * hh, (Op[2] + 0.4 * hh - 0.9 * hh) / 2), None, 0.02 * hh), L['lining'], 0.02 * hh)
    for nm, a in fig.arm.items():
        hanging_sleeve(f, fig, a, 'robe2', length=sp.get('sleeve_len', 1.5), width=sp.get('sleeve_w', 0.5))
    # shoe tips (沓)
    for nm, g in fig.leg.items():
        Ak = g['A']; fd = nrm(g['foot_dir'] * A(1, 1, 0))
        f.add(Ellipsoid(A(Ak[0], Ak[1], 0.12 * hh) + fd * 0.5 * hh, A(0.2, 0.3, 0.13) * hh, frame(y=fd, z=(0, 0, 1))), L['shoe'], 0.04 * hh)
        f.add(Ellipsoid(A(Ak[0], Ak[1], 0.2 * hh) + fd * 0.68 * hh, A(0.1, 0.12, 0.1) * hh, frame(y=fd, z=(0, 0, 1))), L['shoe'], 0.04 * hh)

def costume_ascetic(f, fig, sp, rng):
    """婆藪仙: a short wrap of hide round the hips with a pointed hem, a cloth over the left shoulder"""
    hh = fig.hh; Op = fig.Op; Rc, Oc = fig.Rc, fig.Oc
    zt = Op[2] + 0.35 * hh
    rows = skirt_rows(fig, zt, 1.45 * hh, extra=0.05, flare=0.25)
    c = (rows[0][1], rows[0][2])
    def hem(th):
        return (1.45 * hh + 0.55 * hh * np.abs(np.sin(2.5 * th + 0.4)) ** 2 + 0.3 * hh * np.clip(-np.sin(th), 0, 1)).astype(np.float32)
    from .statues_kannon import Over
    f.add(Over(rows, hem, fold_fn((c[0], c[1], 0), 8, 0.015 * hh)), L['robe'], 0.02 * hh)
    rows2 = skirt_rows(fig, zt + 0.08 * hh, Op[2] - 0.2 * hh, extra=0.12, flare=0.2)
    def hem2(th): return (Op[2] - 0.2 * hh - 0.3 * hh * np.clip(np.sin(th), 0, 1) ** 3).astype(np.float32)
    f.add(Over(rows2, hem2, fold_fn((c[0], c[1], 0), 6, 0.01 * hh)), L['robe2'], 0.01 * hh)
    # cloth over the left shoulder, across the chest to the right hip
    pts = spline([fig.arm['l']['S'] + A(0.05, -0.2, 0.25) * hh, fig.arm['l']['S'] + A(0.05, 0.35, 0.1) * hh, Oc + Rc @ A(0.0, 0.62, -0.15) * hh,
                  fig.W + A(0.55, 0.45, -0.1) * hh, fig.W + A(0.68, 0.0, -0.15) * hh], 56)
    f.add(Sweep(pts, 0.17 * hh, 0.025 * hh, [nrm(p - Oc) for p in pts]), L['robe2'], 0.03 * hh)

# ---------------------------------------------------------------------------------------------- the generator
def attendant(sp):
    from .statues_build import Model
    rng = np.random.default_rng(zlib.crc32(sp['name'].encode()) % 10000)
    h = sp['h']; kind = sp.get('kind', 'guard'); heads = sp.get('heads', 5.7)
    base_h = sp.get('base_h', 0.2)
    m = Model(sid(sp['name']), sp['jp'], f"{sp['name']} ({sp.get('en', '')})".replace(' ()', ''), budget=(80000, 16000, 2400), lift=base_h, figure_h=h)
    m.pal = att_palette(sp.get('col', {}))
    m.slot = dict(slot='attendants', slot_name=sp['name'], slot_pos=sp.get('pos'))
    H = h * sp.get('Hfrac', 0.93); hh = H / heads
    U = lambda *v: A(*v) * hh                            # head units -> metres
    pose = dict(sp.get('pose', {}))
    pose.setdefault('neck', {'nio': 0.06, 'guard': 0.08, 'deva': 0.14, 'female': 0.16, 'ascetic': 0.16}.get(kind, 0.1))
    pose.setdefault('head_scale', {'nio': 1.1, 'guard': 1.1, 'deva': 1.04, 'female': 1.0, 'ascetic': 1.0}.get(kind, 1.05))
    for k in ('hand_r', 'hand_l', 'foot_r', 'foot_l'):
        if k in pose: pose[k] = U(*pose[k])
    fig = Bd.Fig(H, heads, kind if kind in ('guard', 'nio', 'deva', 'female', 'ascetic', 'bodhi') else 'guard', **pose)
    O, R = fig.Oh, fig.Rh
    hb = hh; hh = fig.hhd           # head-drawing unit below; body parts use fig.hh
    f = Field('body')
    sk = 'skin'
    # body (feet: bare for nio/ascetic, else covered)
    Bd.add_body(f, fig, skin=sk)
    if kind == 'nio':
        for nm, a in fig.arm.items():   # veins on the forearms
            ax = nrm(a['W'] - a['E'])
            f.add(Capsule(a['E'] + ax * 0.15 * hb + A(0, 0.1, 0) * hb, a['W'] - ax * 0.2 * hb + A(0, 0.08, 0.03) * hb, 0.025 * hb), L[sk], 0.02 * hb)
    cost = sp.get('costume', 'armour')
    {'armour': costume_armour, 'bare': costume_bare, 'tang': costume_tang, 'ascetic': costume_ascetic}[cost](f, fig, sp, rng)
    # extra arms (Ashura)
    extra_arms = []
    for (s, tgt, pole, back) in sp.get('extra_arms', []):
        S0 = fig.arm['r' if s > 0 else 'l']['S'] + A(-s * 0.05, -0.08, -0.12) * hb
        E, W = Bd.ik2(S0, U(*tgt), 1.2 * hb, 1.02 * hb, pole)
        a = dict(S=S0, E=E, W=W, s=s); extra_arms.append((a, back))
        Bd.add_arm(f, fig, a, L[sk], deltoid=False)
        ax = nrm(W - E)
        f.add(Torus(W - ax * 0.03 * hb, 0.18 * hb, 0.03 * hb, frame(z=ax, x=(0, 0, 1) if abs(ax[2]) < 0.9 else (1, 0, 0))), L['jewel'], 0.01 * hb)
    # wings (Karura)
    if sp.get('wings'):
        hh = hb
        for s in (1, -1):
            b = fig.Oc + fig.Rc @ A(s * 0.35, -0.55, 0.35) * hh
            tip = b + A(s * 0.9, -0.45, 1.3) * hh
            def feathers(P, b=b): return (0.0035 * np.sin((P[:, 2] - b[2]) / hh * 22 + (P[:, 0] - b[0]) / hh * 6)).astype(np.float32)
            wp = spline([b, b + A(s * 0.4, -0.25, 0.5) * hh, tip, tip + A(s * 0.25, -0.05, -0.9) * hh], 48)
            wing = Sweep(wp, np.interp(np.linspace(0, 1, len(wp)), [0, 0.3, 0.6, 1.0], [0.22, 0.33, 0.2, 0.06]) * hh, 0.045 * hh, [A(0, 1, 0.1)] * len(wp))
            f.add(Displace(wing, feathers, 0.004), L['feather'], 0.03 * hh)
    # held things made in the field (dragon, snakes, biwa, drum)
    hh = hb
    for it in sp.get('field_items', []):
        it(f, fig, U, hh)
    m.field(f, 0.0026, 44.0, lods=(0, 1))
    hh = fig.hhd
    # ---- head
    g = Field('head')
    g.add(Inter([RCone(fig.N - fig.Rc @ A(0, 0, 0.15 * hb), O + R @ A(0, -0.06 * hh, -0.25 * hh), (0.3 + 0.06 * fig.musc) * hb, 0.27 * hh),
                 Plane(O + R @ A(0, 0, -0.62 * hh), -(R[:, 2]))]), L[sk], 0.0)
    hd = dict(sp.get('head', {}))
    hair = hd.pop('hair', 'bun'); hat = hd.pop('hat', 'crown_flame'); faces = hd.pop('faces', 1); split = hd.pop('split', False)
    eyes3 = hd.pop('eyes3', False); snakes = hd.pop('snakes', 0); fins = hd.pop('fins', False)
    hd.setdefault('eyes', 'crystal'); hd.setdefault('urna', False)
    Bd.add_head(g, R, O, hh, **hd)
    if faces == 3:
        for s in (1, -1):
            R2 = R @ rot((0, 0, 1), s * 1.25)
            O2 = O + R @ A(s * 0.12, -0.12, 0) * hh
            Bd.add_head(g, R2, O2, hh * 0.92, **hd)
    if split:
        # 金色孔雀王: the face splits open down the middle, a second face looks out
        g.sub(Ellipsoid(O + R @ A(0, 0.42, -0.05) * hh, A(0.1, 0.15, 0.36) * hh, R), 0.02 * hh, lab=L['mouth'])
        hd2 = dict(style='fierce', fierce=1.0, mouth='open', ears=None, eyes='crystal', urna=False)
        Bd.add_head(g, R, O + R @ A(0, 0.06, -0.06) * hh, hh * 0.5, **hd2)
    if eyes3:
        eye_extra(g, R, O, hh, (0, 0.39, 0.17))
        for s in (1, -1): eye_extra(g, R, O, hh, (s * 0.24, 0.31, 0.15), vertical=True)
    if hair not in ('none',):
        Bd.add_hair(g, R, O, hh, hair, seed=int(rng.integers(0, 99)))
    if fins:
        for s in (1, -1):
            for k in range(3):
                b = O + R @ A(s * 0.3, -0.05 - 0.12 * k, 0.25 + 0.05 * k) * hh
                g.add(Sweep([b, b + R @ A(s * 0.25, -0.1, 0.25) * hh, b + R @ A(s * 0.4, -0.25, 0.45) * hh], A(0.08, 0.06, 0.01) * hh, 0.012 * hh, [R @ A(0, 1, 0)] * 3), L['hair'], 0.01 * hh)
            g.add(Sweep([O + R @ A(s * 0.08, 0.4, 0.12) * hh, O + R @ A(s * 0.28, 0.33, 0.24) * hh, O + R @ A(s * 0.42, 0.2, 0.36) * hh], A(0.03, 0.04, 0.005) * hh, 0.012 * hh, [R @ A(0, 1, 0.3)] * 3), L['hair'], 0.01 * hh)
    if snakes:
        for k in range(snakes):
            a = math.pi / 2 + (k - (snakes - 1) / 2) * 0.45
            b = O + R @ A(0.25 * math.cos(a), 0.25 * math.sin(a) - 0.1, 0.42) * hh
            pts = [b, b + R @ A(0.1 * math.cos(a), 0.05, 0.25) * hh, b + R @ A(0.18 * math.cos(a), 0.12 + 0.02 * k, 0.45) * hh, b + R @ A(0.2 * math.cos(a), 0.3, 0.5) * hh]
            snake_tube(g, pts, 0.05 * hh)
    if hat == 'crown_flame': crown(g, R, O, hh, 'flame')
    elif hat == 'crown_tall': crown(g, R, O, hh, 'tall')
    elif hat == 'crown_disc': crown(g, R, O, hh, 'disc')
    elif hat == 'helmet': helmet(g, R, O, hh)
    elif hat == 'lioncap':
        P_ = lambda v: O + R @ (A(*v) * hh)
        g.add(Inter([Ellipsoid(P_((0, -0.05, 0.14)), A(0.42, 0.49, 0.48) * hh, R), Plane(P_((0, 0.35, 0.22)), R @ nrm(A(0, 0.4, -1)))], 0.02 * hh), L['cap'], 0.01 * hh)
        for k in range(5):
            a = -0.9 + 0.45 * k
            b = P_((0.3 * math.sin(a), 0.05 * math.cos(a), 0.45))
            g.add(Tube([b, b + R @ A(0.15 * math.sin(a), 0.05, 0.25) * hh, b + R @ A(0.12 * math.sin(a), -0.08, 0.42) * hh], A(0.13, 0.08, 0.015) * hh), L['cap'], 0.04 * hh)
    elif hat == 'snake_coil':
        P_ = lambda v: O + R @ (A(*v) * hh)
        pts = [P_((0.3 * math.cos(t), 0.36 * math.sin(t) - 0.05, 0.38 + 0.03 * t)) for t in np.linspace(0, 2 * math.pi * 1.3, 18)]
        pts.append(P_((0, 0.3, 0.7)))
        snake_tube(g, pts, 0.055 * hh)
    elif hat == 'dragon':
        crown(g, R, O, hh, 'disc')
        P_ = lambda v: O + R @ (A(*v) * hh)
        snake_tube(g, [P_((0.25, -0.2, 0.4)), P_((0.1, -0.1, 0.6)), P_((-0.1, 0.05, 0.62)), P_((-0.05, 0.25, 0.7))], 0.055 * hh)
    m.field(g, 0.0011, 26.0, lods=(0, 1))
    hh = hb
    # ---- base (rock on a board) + LOD2
    bf = Field('rock')
    rock_base(bf, rng, sp.get('base_w', 0.62), sp.get('base_d', 0.5), base_h - 0.05, 0.0)
    m.field(bf, 0.005, 8.0, lods=(0, 1))
    f2 = Field('lod2')
    Bd.add_body(f2, fig, skin=sk)
    rowsL = skirt_rows(fig, fig.Op[2] + 0.3 * hh, 0.3 * hh if cost != 'tang' else 0.02, extra=0.05, flare=0.3)
    f2.add(Loft(rowsL), L['robe'], 0.03)
    f2.add(Ellipsoid(O + R @ A(0, 0, 0.1) * hh, A(0.45, 0.5, 0.62) * hh, R), L['hair'], 0.03)
    f2.add(Box(A(0, 0, -base_h / 2 + 0.025), A(sp.get('base_w', 0.62) / 2, sp.get('base_d', 0.5) / 2, base_h / 2 - 0.025), None, 0.03), L['rock'], 0.0)
    m.field(f2, 0.009, 30.0, lods=(2,))
    # ---- hands
    hands = sp.get('hands', {})
    groups = {}
    allarms = [(nm, a, None) for nm, a in fig.arm.items()] + [(f'x{i}', a, back) for i, (a, back) in enumerate(extra_arms)]
    frames = {}
    for nm, a, back_x in allarms:
        s = a['s']; key = nm if nm in hands else ('r' if s > 0 else 'l')
        hs = hands.get(nm, hands.get(key, {}))
        pose_h = hs.get('pose', 'relaxed')
        ax = nrm(a['W'] - a['E'])
        if 'grip_axis' in hs:
            g_ = nrm(np.asarray(hs['grip_axis'], float))
            x_ = nrm(ax - g_ * (ax @ g_)) if abs(ax @ g_) < 0.98 else nrm(np.cross(g_, A(0, 0, 1)))
            if 'fdir' in hs: x_ = nrm(np.asarray(hs['fdir'], float) - g_ * (np.asarray(hs['fdir'], float) @ g_))
            back = np.cross(x_, g_ * s)
            xf = Bd.hand_xf(a['W'], x_, back, s)
        else:
            fd = nrm(np.asarray(hs.get('fdir', ax), float))
            back = np.asarray(hs.get('back', back_x if back_x is not None else (s, -0.3, 0.2)), float)
            xf = Bd.hand_xf(a['W'], fd, back, s)
        frames[nm] = (xf, hs)
        groups.setdefault(pose_h, []).append(xf)
    Lh = 0.7 * hh
    for pose_h, xfs in groups.items():
        m.instance('hand_' + pose_h, (lambda p=pose_h: (Bd.hand_field(p, Lh, musc=max(fig.musc, 0), lab='skin', bracelet=None), Lh / 110)), 1.6, xfs)
    # ---- explicit parts: board, weapons, scarves, halo
    def xm_fn(q):
        xm = X.XM()
        bw, bd = sp.get('base_w', 0.62) + 0.06, sp.get('base_d', 0.5) + 0.06
        X.octa_plinth(xm, (0, 0, -base_h), max(bw, bd) / 2 / math.cos(math.pi / 4), [(1.0, 0.0, 0.05)], 'base', sides=4, phase=math.pi / 4)
        for (nm, (xf, hs)) in frames.items():
            for it in hs.get('items', []):
                it(xm, xf, q, hh)
        for it in sp.get('items', []):
            it(xm, fig, q, hh)
        if q > 0.2 and sp.get('scarf', True):
            fl = sp.get('scarf_fly', 0.0 if sp.get('costume') == 'tang' else 0.3)
            for s in (1, -1):
                a = fig.arm['r' if s > 0 else 'l']
                sh = a['S']; E = a['E']
                ctrl = [sh + A(-s * 0.3, -0.35, 0.2) * hh, sh + A(0.0, -0.25, 0.32) * hh, sh + A(s * 0.32, 0.0, 0.05) * hh,
                        E + A(s * 0.3, -0.05, -0.1) * hh, E + A(s * (0.55 + 0.5 * fl), -0.25 - 0.2 * fl, -0.7 + 0.3 * fl) * hh,
                        E + A(s * (0.5 + 1.0 * fl), -0.55 - 0.3 * fl, -1.5 + 0.6 * fl) * hh, E + A(s * (0.85 + 1.4 * fl), -0.4 - 0.5 * fl, -2.2 + 1.0 * fl) * hh]
                pts = spline(ctrl, 34 if q > 0.6 else 14)
                n = len(pts)
                ups = [nrm(A(s * math.cos(1.6 * t), math.sin(1.6 * t) * 0.8 + 0.2, 0.25)) for t in np.linspace(0, 1, n)]
                ups[0] = ups[1] = nrm(A(0, 0, 1))
                X.ribbon(xm, pts, np.r_[np.linspace(0.06, 0.1, n // 2), np.linspace(0.1, 0.13, n - n // 2)] * hh, 0.014 * hh, ups, 'scarf')
        if sp.get('halo') and q > 0.2:
            hc = O + R @ A(0, -0.55, 0.15) * hh
            X.flame_ring(xm, hc, frame(x=(1, 0, 0), y=(0, 1, 0)), 0.62 * hh, 3, 'halo', q, size=0.32 * hh)
            X.tube(xm, [hc + A(0, -0.02, -0.62 * hh), fig.Oc + A(0, -0.55 * hh, -0.4 * hh)], 0.012, 5, 'rod')
        return xm
    m.xm_fn = xm_fn
    m.closeups = [('face', m.lift + O[2] + 0.02, 0.85, 0.3), ('front', m.lift + 0.85, 2.6, 0.0)]
    return m

# ---------------------------------------------------------------------------------------------- held things
def sword(length=0.75, guard=True, lab='weapon', up=1):
    """a straight sword (剣) gripped along the fist axis"""
    def it(xm, xf, q, hh):
        R, t = xf; ax = R[:, 1] * up; x_ = R[:, 0]
        c = t + R @ (A(0.5, 0.0, -0.1) * 0.7 * hh)
        seg = 8 if q > 0.6 else 5
        X.tube(xm, [c - ax * 0.09, c + ax * 0.07], 0.016, seg, 'rod')
        if guard: X.tube(xm, [c + ax * 0.07, c + ax * 0.085], 0.045, seg, lab)
        bl = [c + ax * (0.085 + length * k / 8) for k in range(9)]
        X.ribbon(xm, bl, np.r_[np.full(7, 0.026), 0.018, 0.002], 0.006, x_, lab)
    return it

def pole(length_down, length_up, head='halberd', r=0.016, lab='weapon'):
    """a long pole through the fist (halberd 戟 / staff / spear); axis = the fist axis"""
    def it(xm, xf, q, hh):
        R, t = xf; ax = R[:, 1]; x_ = R[:, 0]
        c = t + R @ (A(0.5, 0.0, -0.1) * 0.7 * hh)
        seg = 8 if q > 0.6 else 4
        a0 = c - ax * length_down; a1 = c + ax * length_up
        X.tube(xm, [a0, a1], r, seg, 'rod')
        if head == 'halberd' and q > 0.2:
            X.tube(xm, [a1, a1 + ax * 0.3], [r * 1.6, 0.002], seg, lab)
            for e in (-1, 1):
                X.tube(xm, [a1 + ax * 0.02, a1 + x_ * e * 0.12 + ax * 0.04, a1 + x_ * e * 0.14 + ax * 0.2], [r * 1.1, r, 0.002], seg, lab, caps=False)
            X.tube(xm, [a1 - ax * 0.05, a1 + ax * 0.02], r * 2.2, seg, lab)
        elif head == 'staff' and q > 0.2:
            th_ = np.linspace(0, 2 * math.pi, 17)
            X.tube(xm, [a1 + x_ * 0.08 * math.sin(tt) + ax * (0.1 + 0.1 * math.cos(tt)) for tt in th_], 0.007, 4, lab, caps=False)
    return it

def small(kind, s=0.12, lab='attr'):
    def it(xm, xf, q, hh):
        if q < 0.3 and kind not in ('wheel', 'disc'): return
        R, t = xf
        grip = {'vajra': (0.5, 0.0, -0.1), 'jewel': (0.35, 0, -0.15), 'vase': (0.35, 0, -0.15), 'disc': (0.5, 0.0, -0.1), 'wheel': (0.5, 0, -0.1),
                'arrow': (0.5, 0.0, -0.1), 'bow': (0.5, 0, -0.1), 'sutra': (0.5, 0, -0.1), 'buddha': (0.35, 0, -0.15), 'bell': (0.5, 0, -0.1), 'axe': (0.5, 0, -0.1)}.get(kind, (0.5, 0, -0.1))
        X.attribute(xm, kind, R, t + R @ (A(*grip) * 0.7 * hh), s, lab, q)
    return it

def pagoda(s=0.22):
    def it(xm, xf, q, hh):
        R, t = xf; up = A(0, 0, 1)
        c = t + R @ (A(0.35, 0, -0.18) * 0.7 * hh) + up * 0.01
        X.lathe(xm, c, [(0, 0), (0.07 * s / 0.22, 0), (0.07 * s / 0.22, 0.02)], 8, 'weapon', ngon=True)
        for k, (w_, z_) in enumerate(((0.06, 0.02), (0.05, 0.1), (0.04, 0.17))):
            w_ *= s / 0.22; z_ *= s / 0.22
            X.octa_plinth(xm, c + A(0, 0, z_), w_ * 0.8, [(1.0, 0.0, 0.05 * s / 0.22)], 'weapon', sides=4, phase=math.pi / 4)
            X.lathe(xm, c + A(0, 0, z_ + 0.05 * s / 0.22), [(w_ * 1.5, 0), (w_ * 0.4, 0.025 * s / 0.22), (0, 0.03 * s / 0.22)], 4, 'weapon', phase=math.pi / 4, ngon=True)
        X.tube(xm, [c + A(0, 0, 0.2 * s / 0.22), c + A(0, 0, 0.3 * s / 0.22)], [0.006, 0.002], 5, 'weapon')
    return it

def mirror(r=0.09):
    def it(xm, xf, q, hh):
        R, t = xf
        c = t + R @ (A(0.6, 0.1, -0.3) * 0.7 * hh); n = nrm(A(0, 1, 0.3))
        X.disc(xm, c, n, r, 'weapon', seg=24 if q > 0.5 else 10); X.disc(xm, c - n * 0.012, -n, r, 'weapon', seg=24 if q > 0.5 else 10)
        th = np.linspace(0, 2 * math.pi, 25 if q > 0.5 else 11); Rr = frame(z=n, x=(1, 0, 0))
        X.tube(xm, [c - n * 0.006 + Rr @ A(r * math.cos(a), r * math.sin(a), 0) for a in th], 0.008, 5 if q > 0.5 else 3, 'weapon', caps=False)
    return it

def hammer():
    def it(xm, xf, q, hh):
        R, t = xf; ax = R[:, 1]
        c = t + R @ (A(0.5, 0, -0.1) * 0.7 * hh)
        X.tube(xm, [c - ax * 0.06, c + ax * 0.2], 0.013, 6, 'rod')
        X.tube(xm, [c + ax * 0.2 - R[:, 0] * 0.06, c + ax * 0.2 + R[:, 0] * 0.06], 0.03, 8 if q > 0.5 else 5, 'weapon')
    return it

def flute():
    def it(xm, fig, q, hh):
        a, b = fig.arm['r']['W'], fig.arm['l']['W']
        d = nrm(a - b); c = (a + b) / 2 + A(0, 0.06, 0.02)
        X.tube(xm, [c - d * 0.3, c + d * 0.3], 0.013, 8 if q > 0.5 else 4, 'attr2')
    return it

def cymbals():
    def it(xm, fig, q, hh):
        for nm in ('r', 'l'):
            W = fig.arm[nm]['W']; s = fig.arm[nm]['s']
            c = W + A(-s * 0.07, 0.04, 0.05); n = A(-s, 0.0, 0.0)
            X.lathe(xm, A(0, 0, 0), [(0, 0), (0.0, 0)], 3, 'weapon') if False else None
            Rr = frame(z=n, x=(0, 0, 1))
            prof = [(0.0, 0.025), (0.025, 0.024), (0.03, 0.012), (0.085, 0.0), (0.085, -0.004), (0.03, 0.006), (0.0, 0.008)]
            seg = 16 if q > 0.5 else 8
            P = [c + Rr @ A(r_ * math.cos(2 * math.pi * k / seg), r_ * math.sin(2 * math.pi * k / seg), z_) for (r_, z_) in prof for k in range(seg)]
            xm.add(P, X.grid_tris(seg, len(prof) - 1, wrap_u=True), 'weapon')
    return it

def wheel_big():
    def it(xm, xf, q, hh):
        R, t = xf
        X.attribute(xm, 'wheel', R, t + R @ (A(0.4, 0.0, -0.12) * 0.7 * hh), 0.42, 'weapon', q)
    return it

def staff_ground(top_offset=(0, 0, 0), bend=0.03, lab='rod'):
    """a long crooked staff from the base to the hand"""
    def it(xm, xf, q, hh):
        R, t = xf
        top = t + R @ (A(0.5, 0, -0.1) * 0.7 * hh) + A(*top_offset)
        bot = A(top[0] + 0.05, top[1] + 0.02, 0.0)
        pts = [bot + (top - bot) * u + A(bend * math.sin(u * 7), bend * 0.5 * math.sin(u * 5), 0) for u in np.linspace(0, 1, 10)]
        pts.append(top + A(0, 0, 0.12))
        X.tube(xm, pts, 0.011, 6 if q > 0.5 else 3, lab)
    return it

def bird_staff():
    def it(xm, xf, q, hh):
        R, t = xf
        c = t + R @ (A(0.5, 0, -0.1) * 0.7 * hh)
        top = c + A(0, 0, 0.55); bot = A(c[0], c[1], 0.0)
        X.tube(xm, [bot, top], 0.012, 6 if q > 0.5 else 3, 'rod')
        if q > 0.3:
            X.lathe(xm, top + A(0, 0, 0.03), [(0, -0.03), (0.035, -0.015), (0.04, 0.01), (0.025, 0.04), (0, 0.05)], 8, 'weapon')
            X.lathe(xm, top + A(0, 0.04, 0.09), [(0, -0.025), (0.025, -0.01), (0.022, 0.015), (0, 0.025)], 8, 'weapon')
            X.tube(xm, [top + A(0, 0.06, 0.09), top + A(0, 0.1, 0.085)], [0.008, 0.001], 4, 'weapon')
            X.ribbon(xm, [top + A(0, -0.03, 0.04), top + A(0, -0.09, 0.08), top + A(0, -0.14, 0.13)], [0.03, 0.035, 0.02], 0.004, A(0, 0, 1), 'weapon')
    return it

def sword_planted(lab='weapon'):
    """提頭頼吒: a long sword planted point-down in front, the hands crossed on its pommel"""
    def it(xm, fig, q, hh):
        c = (fig.arm['r']['W'] + fig.arm['l']['W']) / 2 + A(0, 0.07, 0.03)
        X.tube(xm, [c - A(0, 0, 0.13), c + A(0, 0, 0.06)], 0.017, 8 if q > 0.5 else 4, 'rod')
        X.tube(xm, [c - A(0, 0, 0.15), c - A(0, 0, 0.13)], 0.06, 8 if q > 0.5 else 4, lab)
        bl = [c - A(0, 0, 0.15) + (A(c[0], c[1] + 0.04, 0.02) - (c - A(0, 0, 0.15))) * u for u in np.linspace(0, 1, 9)]
        X.ribbon(xm, bl, np.r_[np.full(7, 0.03), 0.02, 0.002], 0.007, A(0, 1, 0), lab)
    return it

def drum_hourglass(f, fig, U, hh):
    """羯鼓 (Kendatsuba): an hourglass drum across the belly"""
    a, b = fig.arm['r']['W'], fig.arm['l']['W']
    d = nrm(a - b); c = (a + b) / 2 + A(0, 0.07, -0.02)
    for e in (-1, 1):
        f.add(Cyl(c + d * e * 0.13, c + d * e * 0.17, 0.15, 0.01), L['drum'], 0.0)
        f.add(RCone(c, c + d * e * 0.14, 0.05, 0.11), L['attr2'], 0.01)
    f.add(Torus(c, 0.06, 0.012, frame(z=d, x=(0, 0, 1))), L['trim'], 0.004)

def biwa(f, fig, U, hh):
    """摩睺羅: a lute held diagonally, neck up to its left hand"""
    lw = fig.arm['l']['W']; rw = fig.arm['r']['W']
    body_c = rw + A(-0.08, 0.08, 0.02)
    up = nrm(lw - body_c + A(0, 0, 0.1))
    Rb = frame(z=up, x=nrm(np.cross(up, A(0, 1, 0))))
    f.add(Ellipsoid(body_c, A(0.15, 0.05, 0.22), Rb), L['attr2'], 0.01)
    f.add(Capsule(body_c + up * 0.18, lw + up * 0.08, 0.025), L['attr2'], 0.01)
    f.add(Box(lw + up * 0.16, A(0.03, 0.025, 0.07), Rb, 0.01), L['attr2'], 0.01)

def dragon_held(f, fig, U, hh):
    """難陀龍王: a dragon held in both hands, its head rearing over the right shoulder"""
    a, b = fig.arm['r']['W'], fig.arm['l']['W']
    pts = [b + A(-0.08, 0.02, -0.25), b + A(0.0, 0.06, 0.0), (a + b) / 2 + A(0, 0.15, 0.05), a + A(0, 0.06, 0.02), a + A(0.12, 0.0, 0.3), fig.arm['r']['S'] + A(0.08, 0.1, 0.25)]
    snake_tube(f, pts, 0.032)
    hp = pts[-1]
    for s in (1, -1):
        f.add(RCone(hp + A(s * 0.03, -0.03, 0.03), hp + A(s * 0.07, -0.1, 0.1), 0.012, 0.003), L['snake'], 0.006)

def snake_in_left(f, fig, U, hh):
    b = fig.arm['l']['W']
    snake_tube(f, [b + A(0.02, 0.03, -0.3), b + A(0.0, 0.05, -0.1), b + A(0.01, 0.06, 0.05), b + A(-0.06, 0.08, 0.17), b + A(0.0, 0.14, 0.24)], 0.02)

def snake_shoulder(f, fig, U, hh):
    a = fig.arm['l']['S']
    snake_tube(f, [a + A(0.1, -0.15, -0.3), a + A(0.05, -0.05, 0.1), a + A(-0.05, 0.12, 0.08), a + A(0.1, 0.25, -0.05), a + A(0.18, 0.3, 0.06)], 0.025)

# ---------------------------------------------------------------------------------------------- the 28 (2018 order, north -> south)
G = dict(costume='armour', kind='guard', heads=5.7)
POSE_STAND = dict(foot_r=(0.48, 0.15, 0.28), foot_l=(-0.5, 0.35, 0.28), hip_shift=(0.06, 0), pelvis_rot=(0, 0.04, -0.12), chest_rot=(0.02, -0.05, 0.12))

def P_(**kw):
    p = dict(POSE_STAND); p.update(kw); return p

SPECS = [
    dict(name='Narayana-kengo', jp='那羅延堅固', en='Nio, a-gyo', h=1.67, kind='nio', costume='bare', heads=5.6, scarf_fly=0.9,
         pose=dict(foot_r=(0.85, 0.2, 0.28), foot_l=(-0.55, 0.45, 0.28), hip_shift=(0.15, -0.02), pelvis_rot=(0.0, 0.08, -0.2), chest_rot=(0.05, -0.12, 0.3),
                   head_rot=(0.05, 0.05, 0.45), hand_r=(1.45, 0.75, 2.75), elbow_r=(1, -0.5, -0.2), hand_l=(-1.05, 0.55, 4.85), elbow_l=(-1, -0.2, -1)),
         head=dict(style='fierce', fierce=1.0, mouth='open', ears='normal', hair='bun', hat='crown_disc'),
         hands=dict(r=dict(pose='spread', fdir=(0.3, 0.3, -1), back=(0.2, -1, 0)), l=dict(pose='fist', fdir=(0, 0.3, 1), back=(0, -1, 0))),
         col=dict(skin=(86, 92, 98), robe=(74, 66, 60), robe3=(96, 70, 52), scarf=(86, 76, 66))),
    dict(G, name='Nanda-ryuo', jp='難陀龍王', en='Dragon King Nanda', h=1.60,
         pose=P_(head_rot=(0.0, 0, 0.2), hand_r=(0.45, 0.95, 3.75), elbow_r=(1, -0.4, -0.6), hand_l=(-0.4, 0.95, 3.25), elbow_l=(-1, -0.4, -0.6)),
         head=dict(style='fierce', fierce=0.7, mouth='closed', ears='normal', hair='bun', hat='dragon'),
         hands=dict(r=dict(pose='grip', grip_axis=(0.3, 0.2, 1)), l=dict(pose='grip', grip_axis=(0.4, 0.3, 1))),
         field_items=[dragon_held], col=dict(robe=(92, 60, 48), robe2=(66, 84, 70), armour=(72, 66, 58), snake=(64, 82, 62))),
    dict(G, name='Magora', jp='摩睺羅', en='Mahoraga, with a biwa', h=1.59, costume='tang', sleeve_len=1.1,
         pose=P_(head_rot=(0.15, 0, -0.15), hand_r=(0.35, 0.85, 3.3), elbow_r=(1, -0.3, -0.5), hand_l=(-0.85, 0.75, 4.35), elbow_l=(-1, -0.3, -0.7)),
         head=dict(style='fierce', fierce=0.55, mouth='closed', ears='normal', hair='bun', hat='snake_coil', eyes3=True),
         hands=dict(r=dict(pose='pinch', fdir=(-0.6, 0.4, 0.4), back=(0, -1, 0.3)), l=dict(pose='grip', grip_axis=(0.5, -0.2, 1))),
         field_items=[biwa], col=dict(robe=(70, 70, 82), robe2=(98, 64, 48), snake=(70, 80, 60))),
    dict(G, name='Kinnara', jp='緊那羅', en='Kinnara, with cymbals', h=1.65, kind='female', costume='tang', heads=6.1, scarf=True,
         pose=P_(foot_r=(0.38, 0.2, 0.28), foot_l=(-0.38, 0.32, 0.28), head_rot=(0.12, 0, 0.1), hand_r=(0.4, 0.95, 4.0), elbow_r=(1, -0.3, -0.8), hand_l=(-0.4, 0.95, 4.0), elbow_l=(-1, -0.3, -0.8)),
         head=dict(style='female', ears='long', hair='bodhi', hat='crown_tall', eyes='crystal'),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 1, 0.2)), l=dict(pose='grip', grip_axis=(0, 1, 0.2))),
         items=[cymbals()], col=dict(skin=(118, 98, 78), robe=(104, 62, 52), robe2=(72, 86, 76))),
    dict(G, name='Karura', jp='迦楼羅', en='Garuda, playing a flute', h=1.64, wings=True, scarf_fly=0.2,
         pose=P_(foot_r=(0.45, 0.4, 0.42), footdir_r=(0.1, 1, 0.5), head_rot=(0.05, 0, 0.25), hand_r=(0.35, 0.9, 4.55), elbow_r=(1, -0.3, -0.6), hand_l=(-0.55, 0.85, 4.45), elbow_l=(-1, -0.3, -0.7)),
         head=dict(style='bird', hair='none', hat='none'),
         hands=dict(r=dict(pose='pinch', fdir=(-0.4, 0.3, 0.6), back=(0.3, -0.5, -0.3)), l=dict(pose='pinch', fdir=(0.4, 0.3, 0.6), back=(-0.3, -0.5, -0.3))),
         items=[flute()], col=dict(skin=(80, 70, 58), lip=(110, 88, 50), feather=(72, 64, 54), robe=(98, 58, 46))),
    dict(G, name='Kendatsuba', jp='乾闥婆', en='Gandharva, with a drum', h=1.64, halo=True,
         pose=P_(head_rot=(0.1, 0, 0.12), hand_r=(0.62, 0.9, 3.15), elbow_r=(1, -0.4, -0.4), hand_l=(-0.6, 0.9, 3.15), elbow_l=(-1, -0.4, -0.4)),
         head=dict(style='fierce', fierce=0.45, mouth='closed', ears='normal', hair='bun', hat='lioncap'),
         hands=dict(r=dict(pose='open', fdir=(-0.6, 0.6, 0.3), back=(1, 0, 0.2)), l=dict(pose='open', fdir=(0.6, 0.6, 0.3), back=(-1, 0, 0.2))),
         field_items=[drum_hourglass], col=dict(skin=(92, 86, 74), armour=(66, 86, 72), armour2=(70, 74, 70), robe=(96, 76, 58), cap=(84, 86, 82), drum=(110, 86, 60))),
    dict(G, name='Bishaja', jp='毘舎闍', en='Pisaca, with a wheel', h=1.61, kind='nio', costume='bare', heads=5.7,
         pose=P_(head_rot=(0.0, 0.0, 0.25), hand_r=(1.05, 0.5, 5.25), elbow_r=(1, 0, -0.6), hand_l=(-1.1, 0.25, 3.0), elbow_l=(-1, -0.5, 0)),
         head=dict(style='fierce', fierce=0.9, mouth='clenched', ears='pointed', hair='flame', hat='none'),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0, 1), items=[wheel_big()]), l=dict(pose='fist', fdir=(0, 0.3, -1), back=(-1, 0, 0))),
         items=[], col=dict(skin=(98, 82, 66), robe=(84, 62, 48)),
         ),
    dict(G, name='Sanshi-taisho', jp='散支大将', en='General Sanshi', h=1.64,
         pose=P_(head_rot=(0.02, 0, -0.15), hand_r=(1.0, 0.45, 3.1), elbow_r=(1, -0.6, 0), hand_l=(-1.0, 0.6, 3.7), elbow_l=(-1, -0.4, -0.4)),
         head=dict(style='fierce', fierce=0.8, mouth='closed', ears='normal', hair='bun', hat='crown_flame', nose=7.0),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0.3, 1), items=[small('vajra', 0.22, 'weapon')]), l=dict(pose='grip', grip_axis=(0, 0, 1), items=[pole(1.0, 0.95)])),
         col=dict(robe=(92, 64, 50), robe2=(62, 72, 86), armour=(70, 60, 52))),
    dict(G, name='Manzen-shahatsu', jp='満善車鉢', en='Manzen-shahatsu', h=1.59,
         pose=P_(foot_r=(0.4, 0.3, 0.28), foot_l=(-0.55, 0.12, 0.28), hip_shift=(-0.06, 0), pelvis_rot=(0, -0.04, 0.12), chest_rot=(0.02, 0.05, -0.15),
                 head_rot=(0, 0, 0.2), hand_r=(0.85, 0.65, 4.4), elbow_r=(1, -0.3, -0.8), hand_l=(-1.15, 0.35, 2.6), elbow_l=(-1, -0.5, 0)),
         head=dict(style='fierce', fierce=0.9, mouth='open', ears='normal', hair='bun', hat='crown_flame'),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0.2, 1), items=[small('vajra', 0.22, 'weapon')]), l=dict(pose='relaxed', fdir=(0, 0.2, -1), back=(-1, 0, 0))),
         col=dict(robe=(70, 80, 66), robe2=(98, 60, 50), armour=(64, 62, 60))),
    dict(G, name='Manibadara', jp='摩尼跋陀羅', en='Manibhadra', h=1.60,
         pose=P_(head_rot=(0.05, 0, -0.1), hand_r=(0.35, 0.95, 3.85), elbow_r=(1, -0.3, -0.6), hand_l=(-1.1, 0.0, 3.05), elbow_l=(-1, -0.2, 0.1)),
         head=dict(style='fierce', fierce=0.75, mouth='closed', ears='normal', hair='bun', hat='crown_flame'),
         hands=dict(r=dict(pose='grip', grip_axis=(0.2, 0.3, 1), items=[small('vajra', 0.22, 'weapon')]), l=dict(pose='fist', fdir=(0.3, 0.6, -0.6), back=(-1, -0.2, 0))),
         col=dict(robe=(96, 62, 50), robe2=(72, 70, 88), armour=(68, 64, 58))),
    dict(G, name='Bishamonten', jp='毘沙門天', en='Vaisravana (Tamon-ten)', h=1.61,
         pose=P_(head_rot=(0.02, 0, 0.1), hand_r=(1.05, 0.55, 3.75), elbow_r=(1, -0.4, -0.5), hand_l=(-0.75, 0.75, 4.75), elbow_l=(-1, -0.2, -0.8)),
         head=dict(style='fierce', fierce=0.85, mouth='closed', ears='normal', hair='bun', hat='crown_flame'),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0, 1), items=[pole(1.0, 1.0)]), l=dict(pose='cup', fdir=(0.4, 0.3, 0.3), back=(0, 0, -1), items=[pagoda(0.24)])),
         col=dict(robe=(90, 62, 48), robe2=(64, 80, 70), armour=(72, 64, 54))),
    dict(G, name='Daizurata-o', jp='提頭頼吒王', en='Dhrtarastra (Jikoku-ten)', h=1.66,
         pose=P_(foot_r=(0.5, 0.2, 0.28), foot_l=(-0.5, 0.2, 0.28), hip_shift=(0, 0), pelvis_rot=(0, 0, 0), chest_rot=(0.03, 0, 0), head_rot=(0.12, 0, 0),
                 hand_r=(-0.12, 0.95, 3.05), elbow_r=(1, -0.3, -0.5), hand_l=(0.14, 0.98, 3.12), elbow_l=(-1, -0.3, -0.5)),
         head=dict(style='fierce', fierce=0.8, mouth='closed', ears='normal', hair='bun', hat='crown_flame'),
         hands=dict(r=dict(pose='fist', fdir=(-1, 0.3, 0), back=(0, 0.1, 1)), l=dict(pose='fist', fdir=(1, 0.3, 0), back=(0, 0.1, 1))),
         items=[sword_planted()], col=dict(robe=(88, 66, 52), robe2=(98, 58, 48), armour=(70, 66, 58))),
    dict(name='Basu-sen', jp='婆藪仙', en='Vasu the ascetic', h=1.56, kind='ascetic', costume='ascetic', heads=6.2, scarf=False,
         pose=dict(foot_r=(0.42, 0.25, 0.28), foot_l=(-0.42, 0.1, 0.28), chest_rot=(0.18, 0, 0.08), head_rot=(0.05, 0, -0.08), pelvis_rot=(0, 0.03, 0),
                   hand_r=(-0.75, 0.6, 3.15), elbow_r=(1, -0.2, -0.6), hand_l=(-0.85, 1.25, 4.1), elbow_l=(-1, -0.5, -0.6)),
         head=dict(style='old', age=1.0, fierce=0.1, mouth='open', ears='normal', hair='cap', hat='none', beard=True),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0, 1), items=[staff_ground()]), l=dict(pose='grip', grip_axis=(-1, 0.1, 0), items=[small('sutra', 0.3, 'attr2')])),
         col=dict(skin=(104, 90, 72), robe=(86, 72, 56), robe2=(96, 80, 60), cap=(78, 64, 52)), base_w=0.6, base_d=0.5),
    dict(name='Daibon-tenno', jp='大梵天王', en='Brahma', h=1.70, kind='deva', costume='tang', heads=6.1, sleeve_len=1.7,
         pose=dict(foot_r=(0.36, 0.22, 0.28), foot_l=(-0.36, 0.3, 0.28), head_rot=(0.12, 0, 0.0), chest_rot=(0.02, 0, 0.05),
                   hand_r=(0.35, 1.0, 3.95), elbow_r=(1, -0.3, -0.8), hand_l=(-0.95, 0.85, 3.0), elbow_l=(-1, -0.4, -0.3)),
         head=dict(style='deva', ears='long', hair='deva', hat='crown_tall', eyes='crystal', urna=True),
         hands=dict(r=dict(pose='mudra', fdir=(-0.2, 0.3, 1), back=(0.3, -1, 0)), l=dict(pose='cup', fdir=(0.2, 1, 0), back=(0, 0, -1), items=[small('vase', 0.16)])),
         col=dict(skin=(112, 96, 76), robe=(92, 62, 50), robe2=(64, 74, 84))),
    dict(name='Taishaku-tenno', jp='帝釈天王', en='Indra', h=1.68, kind='deva', costume='tang', heads=6.1, armour_under=True, halo=True, sleeve_len=1.6,
         pose=dict(foot_r=(0.36, 0.22, 0.28), foot_l=(-0.36, 0.32, 0.28), head_rot=(0.12, 0, -0.06), chest_rot=(0.02, 0, -0.05),
                   hand_r=(0.6, 1.0, 3.9), elbow_r=(1, -0.3, -0.8), hand_l=(-0.85, 0.6, 3.0), elbow_l=(-1, -0.4, -0.2)),
         head=dict(style='deva', ears='long', hair='deva', hat='crown_tall', eyes='crystal', urna=True),
         hands=dict(r=dict(pose='grip', grip_axis=(-0.3, 0.3, 1), items=[mirror()]), l=dict(pose='relaxed', fdir=(0, 0.3, -1), back=(-1, 0, 0))),
         col=dict(skin=(108, 92, 74), robe=(84, 70, 66), robe2=(78, 66, 60), lining=(96, 70, 48))),
    dict(name='Daibenkudoku-ten', jp='大弁功徳天', en='Mahasri / Kudokuten', h=1.66, kind='female', costume='tang', heads=6.2, sleeve_len=1.7, sleeve_w=0.55,
         pose=dict(foot_r=(0.34, 0.22, 0.28), foot_l=(-0.34, 0.3, 0.28), head_rot=(0.1, 0, 0.05), hand_r=(0.22, 1.0, 4.0), elbow_r=(1, -0.3, -0.8), hand_l=(-0.22, 1.0, 3.9), elbow_l=(-1, -0.3, -0.8)),
         head=dict(style='female', ears='long', hair='bodhi', hat='crown_tall', eyes='crystal', urna=True),
         hands=dict(r=dict(pose='cup', fdir=(-0.6, 0.5, 0.3), back=(0.4, -0.2, -0.8), items=[small('jewel', 0.14)]), l=dict(pose='open', fdir=(0.4, 0.4, 0.6), back=(-0.4, -1, 0))),
         col=dict(skin=(124, 104, 84), robe=(108, 66, 56), robe2=(86, 82, 66))),
    dict(G, name='Birurokusha', jp='毘楼勒叉', en='Virudhaka (Zocho-ten)', h=1.65,
         pose=P_(foot_r=(0.6, 0.12, 0.28), foot_l=(-0.42, 0.42, 0.28), head_rot=(0.0, 0, 0.3), hand_r=(0.9, 0.45, 5.55), elbow_r=(1, 0.2, -0.6), hand_l=(-1.1, 0.0, 3.05), elbow_l=(-1, -0.2, 0.1)),
         head=dict(style='fierce', fierce=1.0, mouth='open', ears='normal', hair='bun', hat='crown_flame'),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0.3, 1), items=[sword(0.62)]), l=dict(pose='fist', fdir=(0.3, 0.6, -0.6), back=(-1, -0.2, 0))),
         col=dict(robe=(98, 60, 48), robe2=(66, 82, 70), armour=(70, 62, 54))),
    dict(G, name='Birubakusha', jp='毘楼博叉', en='Virupaksa (Komoku-ten)', h=1.59,
         pose=P_(foot_r=(0.42, 0.35, 0.28), foot_l=(-0.55, 0.12, 0.28), hip_shift=(-0.06, 0), pelvis_rot=(0, -0.04, 0.12), chest_rot=(0.02, 0.05, -0.12),
                 head_rot=(0.05, 0, -0.2), hand_r=(0.55, 0.9, 3.25), elbow_r=(1, -0.4, -0.5), hand_l=(-1.05, 0.55, 3.75), elbow_l=(-1, -0.4, -0.5)),
         head=dict(style='fierce', fierce=0.7, mouth='closed', ears='normal', hair='bun', hat='helmet'),
         hands=dict(r=dict(pose='grip', grip_axis=(0.2, 0.3, 1), items=[small('vajra', 0.22, 'weapon')]), l=dict(pose='grip', grip_axis=(0, 0, 1), items=[pole(1.0, 0.95)])),
         col=dict(robe=(80, 66, 56), robe2=(96, 62, 50), armour=(66, 70, 64))),
    dict(name='Sasha-mawara', jp='薩遮摩和羅', en='Mahesvara', h=1.59, kind='nio', costume='bare', heads=5.8, scarf_fly=0.6,
         pose=dict(foot_r=(0.45, 0.25, 0.28), foot_l=(-0.48, 0.12, 0.28), hip_shift=(0.05, 0), chest_rot=(-0.05, 0, 0.1), head_rot=(-0.05, 0, 0.2),
                   hand_r=(0.75, 0.75, 4.55), elbow_r=(1, -0.3, -0.8), hand_l=(-1.0, 0.55, 3.45), elbow_l=(-1, -0.4, -0.4)),
         head=dict(style='fierce', fierce=0.6, mouth='open', ears='normal', hair='bun', hat='crown_disc', brow=0.0),
         hands=dict(r=dict(pose='open', fdir=(0, 0.2, 1), back=(0, -1, 0)), l=dict(pose='grip', grip_axis=(0, 0, 1), items=[bird_staff()])),
         col=dict(skin=(104, 86, 70), robe=(90, 66, 50))),
    dict(G, name='Gobu-jogo', jp='五部浄居', en='Gobu-jogo', h=1.62, halo=True,
         pose=P_(head_rot=(0.05, 0, 0.08), hand_r=(1.15, 0.3, 2.6), elbow_r=(1, -0.4, 0), hand_l=(-0.3, 0.95, 3.55), elbow_l=(-1, -0.4, -0.6)),
         head=dict(style='fierce', fierce=0.75, mouth='closed', ears='normal', hair='bun', hat='crown_flame'),
         hands=dict(r=dict(pose='relaxed', fdir=(0, 0.2, -1), back=(1, 0, 0)), l=dict(pose='grip', grip_axis=(0.05, 0.1, 1), items=[sword(0.55)])),
         col=dict(robe=(92, 62, 50), robe2=(70, 72, 86), armour=(66, 64, 58))),
    dict(G, name='Konjiki-kujaku-o', jp='金色孔雀王', en='Golden Peacock King', h=1.64,
         pose=P_(foot_r=(0.6, 0.12, 0.28), foot_l=(-0.42, 0.42, 0.28), head_rot=(0.0, 0, -0.1), hand_r=(0.95, 0.5, 5.4), elbow_r=(1, 0.2, -0.6), hand_l=(-1.1, 0.0, 3.05), elbow_l=(-1, -0.2, 0.1)),
         head=dict(style='fierce', fierce=0.6, mouth='closed', ears='normal', hair='bun', hat='crown_flame', split=True),
         hands=dict(r=dict(pose='grip', grip_axis=(0.1, 0.3, 1), items=[sword(0.6)]), l=dict(pose='fist', fdir=(0.3, 0.6, -0.6), back=(-1, -0.2, 0))),
         col=dict(robe=(96, 76, 48), robe2=(98, 60, 50), armour=(74, 66, 50))),
    dict(name='Jinmo-nyo', jp='神母女', en='Hariti (Kishimojin)', h=1.54, kind='female', costume='tang', heads=5.9, sleeve_len=1.5, scarf=False,
         pose=dict(foot_r=(0.32, 0.22, 0.28), foot_l=(-0.32, 0.28, 0.28), chest_rot=(0.22, 0, 0), head_rot=(0.15, 0, 0),
                   hand_r=(0.03, 1.05, 3.95), elbow_r=(1, -0.2, -0.9), hand_l=(-0.03, 1.05, 3.95), elbow_l=(-1, -0.2, -0.9)),
         head=dict(style='oldwoman', age=1.0, ears='normal', hair='hood', hat='none', eyes='crystal'),
         hands=dict(r=dict(pose='prayer', fdir=(0, 0.35, 1), back=(1, 0, 0)), l=dict(pose='prayer', fdir=(0, 0.35, 1), back=(-1, 0, 0))),
         col=dict(skin=(118, 100, 82), robe=(84, 70, 58), robe2=(72, 64, 58))),
    dict(G, name='Konpira', jp='金毘羅', en='Kumbhira, with bow and arrow', h=1.55,
         pose=P_(head_rot=(0.05, 0, 0.15), hand_r=(0.85, 0.7, 3.4), elbow_r=(1, -0.4, -0.5), hand_l=(-0.85, 0.75, 3.85), elbow_l=(-1, -0.4, -0.6)),
         head=dict(style='fierce', fierce=0.8, mouth='closed', ears='normal', hair='bun', hat='helmet'),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0.2, 1), items=[small('arrow', 0.35, 'weapon')]), l=dict(pose='grip', grip_axis=(0, 0, 1), items=[small('bow', 0.4, 'rod')])),
         col=dict(robe=(86, 62, 50), robe2=(68, 80, 66), armour=(72, 64, 54))),
    dict(G, name='Hibakara', jp='畢婆伽羅', en='Hibakara', h=1.64,
         pose=P_(foot_r=(0.42, 0.35, 0.28), foot_l=(-0.55, 0.12, 0.28), hip_shift=(-0.06, 0), pelvis_rot=(0, -0.04, 0.12), chest_rot=(0.02, 0.05, -0.12),
                 head_rot=(0.05, 0, -0.25), hand_r=(1.05, 0.15, 3.05), elbow_r=(1, -0.2, 0.1), hand_l=(-0.6, 0.85, 4.35), elbow_l=(-1, -0.3, -0.8)),
         head=dict(style='fierce', fierce=0.95, mouth='open', ears='normal', hair='bun', hat='crown_flame'),
         hands=dict(r=dict(pose='fist', fdir=(-0.3, 0.6, -0.6), back=(1, -0.2, 0)), l=dict(pose='grip', grip_axis=(0, 0.2, 1), items=[small('vajra', 0.22, 'weapon')])),
         col=dict(robe=(70, 70, 84), robe2=(98, 62, 50), armour=(70, 62, 56))),
    dict(name='Ashura', jp='阿修羅', en='Asura, three faces and six arms', h=1.65, kind='deva', costume='bare', heads=6.2, scarf_fly=0.4, skirt_bot=0.5, shoes=False,
         pose=dict(foot_r=(0.35, 0.25, 0.28), foot_l=(-0.35, 0.2, 0.28), head_rot=(0.05, 0, 0), hand_r=(0.04, 1.0, 3.95), elbow_r=(1, -0.2, -0.9), hand_l=(-0.04, 1.0, 3.95), elbow_l=(-1, -0.2, -0.9)),
         head=dict(style='deva', fierce=0.25, ears='normal', hair='bun', hat='crown_disc', faces=3, eyes='crystal'),
         extra_arms=[(1, (1.35, 0.35, 4.5), (1, -0.2, -0.6), (0.2, -1, 0.3)), (-1, (-1.35, 0.35, 4.5), (-1, -0.2, -0.6), (-0.2, -1, 0.3)),
                     (1, (0.85, 0.2, 6.05), (1, 0, 0), (0.3, -1, 0)), (-1, (-0.85, 0.2, 6.05), (-1, 0, 0), (-0.3, -1, 0))],
         hands=dict(r=dict(pose='prayer', fdir=(0, 0.35, 1), back=(1, 0, 0)), l=dict(pose='prayer', fdir=(0, 0.35, 1), back=(-1, 0, 0)),
                    x0=dict(pose='cup', fdir=(0.3, 0.3, 1), back=(0.2, -1, 0), items=[small('disc', 0.3, 'weapon')]),
                    x1=dict(pose='cup', fdir=(-0.3, 0.3, 1), back=(-0.2, -1, 0), items=[small('disc', 0.3, 'weapon')]),
                    x2=dict(pose='open', fdir=(0.2, 0.2, 1), back=(0, -1, 0)), x3=dict(pose='open', fdir=(-0.2, 0.2, 1), back=(0, -1, 0))),
         col=dict(skin=(110, 90, 72), robe=(96, 62, 50), robe3=(80, 76, 62))),
    dict(G, name='Ihatsura', jp='伊鉢羅', en='Ihatsura, with hammer and snake', h=1.64,
         pose=P_(head_rot=(0.05, 0, 0.12), hand_r=(0.45, 0.95, 4.0), elbow_r=(1, -0.3, -0.7), hand_l=(-0.45, 0.95, 3.95), elbow_l=(-1, -0.3, -0.7)),
         head=dict(style='fierce', fierce=0.9, mouth='closed', ears='normal', hair='bun', hat='none', fins=True),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0.2, 1), items=[hammer()]), l=dict(pose='grip', grip_axis=(0, 0, 1))),
         field_items=[snake_in_left], col=dict(robe=(92, 64, 50), robe2=(64, 78, 86), armour=(70, 64, 56))),
    dict(G, name='Sagara-ryuo', jp='娑伽羅龍王', en='Dragon King Sagara', h=1.66,
         pose=P_(head_rot=(0.05, 0, -0.15), hand_r=(0.9, 0.6, 4.25), elbow_r=(1, -0.3, -0.7), hand_l=(-0.7, 0.85, 3.6), elbow_l=(-1, -0.3, -0.6)),
         head=dict(style='fierce', fierce=0.8, mouth='open', ears='normal', hair='bun', hat='none', snakes=5),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0.3, 1), items=[sword(0.58)]), l=dict(pose='grip', grip_axis=(0, 0, 1))),
         field_items=[snake_in_left], col=dict(robe=(88, 64, 50), robe2=(66, 82, 70), armour=(70, 66, 58), snake=(66, 80, 62))),
    dict(name='Misshaku-kongoshi', jp='密迹金剛士', en='Nio, un-gyo', h=1.68, kind='nio', costume='bare', heads=5.6, scarf_fly=0.9,
         pose=dict(foot_r=(0.55, 0.45, 0.28), foot_l=(-0.85, 0.2, 0.28), hip_shift=(-0.15, -0.02), pelvis_rot=(0.0, -0.08, 0.2), chest_rot=(0.05, 0.12, -0.3),
                   head_rot=(0.05, -0.05, -0.45), hand_r=(0.85, 0.85, 3.15), elbow_r=(1, -0.5, -0.3), hand_l=(-1.15, 0.2, 3.0), elbow_l=(-1, -0.4, 0.1)),
         head=dict(style='fierce', fierce=1.0, mouth='clenched', ears='normal', hair='bun', hat='crown_disc'),
         hands=dict(r=dict(pose='spread', fdir=(0.2, 0.5, -0.8), back=(0.3, -1, 0.2)), l=dict(pose='fist', fdir=(0.2, 0.6, -0.6), back=(-1, -0.2, 0))),
         col=dict(skin=(90, 94, 98), robe=(74, 66, 60), robe3=(96, 70, 52), scarf=(86, 76, 66))),
]

POS = ['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8', 'N9', 'N10', 'N11', 'N12', 'CFN', 'CRN', 'CRS', 'CFS',
       'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10', 'S11', 'S12']
for _s, _p in zip(SPECS, POS): _s['pos'] = _p

def by_id():
    return {sid(s['name']): s for s in SPECS}
