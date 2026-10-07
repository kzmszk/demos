"""二十八部衆 — second version, modelled from the temple's official photographs (refs/sanjusangendo/official/nijuhachibushu,
one front photo per figure; reference only).  Kamakura realism: slender tall bodies, weight on one leg, turned heads;
aged dark hinoki with faint traces of colour and gold; crystal eyes; ring halos with openwork flames; rugged rock bases
on black plinths; scarves hanging close to the body.

Statue frame: x = the statue's right (the viewer's LEFT in the photos), y = forward, z up; z = 0 at the main sole."""
import math, zlib
import numpy as np
from . import statues_sdf as S
from . import statues_body as Bd
from . import statues_props as X
from . import statues_wood as W
from .statues_sdf import (Sphere, Ellipsoid, RCone, Capsule, Box, Torus, Cyl, Plane, Fn, Shell, Inter, Union, Diff, Displace, Tube, Loft,
                          Field, frame, rot, euler, nrm, fbm, Offset)
from .statues_body import L, A, Band, Sweep, spline
from .statues_attendants import (sid, snake_tube, eye_extra, crown, helmet, sword, pole, small, pagoda, mirror, hammer, cymbals, flute,
                                 bird_staff, staff_ground, drum_hourglass, biwa, dragon_held, snake_in_left, skirt_rows, fold_fn, panel_fn)
from .statues_kannon import Over

PHOTO = '/home/kazu/work/kyoto-assets/refs/sanjusangendo/official/nijuhachibushu/img{:02d}.jpg'
PHOTO_NO = ['narayana_kengo', 'nanda_ryuo', 'magora', 'kinnara', 'karura', 'kendatsuba', 'bishaja', 'sanshi_taisho', 'manzen_shahatsu',
            'manibadara', 'bishamonten', 'daizurata_o', 'basu_sen', 'daibenkudoku_ten', 'taishaku_tenno', 'daibon_tenno', 'birurokusha',
            'birubakusha', 'sasha_mawara', 'gobu_jogo', 'konjiki_kujaku_o', 'jinmo_nyo', 'konpira', 'hibakara', 'ashura', 'ihatsura',
            'sagara_ryuo', 'misshaku_kongoshi']

def gold_patches(f, region, scale=0.05, amount=0.25, seed=0, lab='gold'):
    """remnants of gilding / kirikane inside a region (paint only); amount ~ the fraction left"""
    amount *= 0.55; scale *= 0.55
    thr = 0.55 - 1.1 * amount
    def fn(P): return ((thr - fbm(P, scale, 3, seed)) * 0.05).astype(np.float32)
    f.paint(Inter([Fn(fn, region.lo, region.hi), region]), L[lab])

def bow_knot(f, c, R, hh, lab='belt', size=1.0):
    """結び: a bow with two loops and two hanging ends"""
    u = hh * size
    for s in (1, -1):
        f.add(Ellipsoid(c + R @ A(s * 0.1, 0.02, 0.0) * u, A(0.1, 0.035, 0.06) * u, R @ rot((0, 1, 0), s * 0.35)), L[lab], 0.01 * u)
        f.add(Sweep([c + R @ A(s * 0.03, 0.02, -0.02) * u, c + R @ A(s * 0.08, 0.04, -0.2) * u, c + R @ A(s * 0.1, 0.03, -0.38) * u], A(0.04, 0.045, 0.035) * u, 0.01 * u, [R @ A(0, 1, 0)] * 3), L[lab], 0.008 * u)
    f.add(Sphere(c + R @ A(0, 0.03, 0) * u, 0.04 * u), L[lab], 0.01 * u)

def lion_face(f, c, R, hh, lab='boss', size=1.0):
    """獅噛: a lion mask boss (belly plate, belt)"""
    u = hh * size
    f.add(Ellipsoid(c, A(0.2, 0.05, 0.15) * u, R), L[lab], 0.01 * u)
    for s in (1, -1):
        f.add(Sphere(c + R @ A(s * 0.07, 0.04, 0.04) * u, 0.035 * u), L[lab], 0.01 * u)                  # eyes
        f.add(Ellipsoid(c + R @ A(s * 0.13, 0.02, 0.08) * u, A(0.06, 0.02, 0.04) * u, R @ rot((0, 1, 0), s * 0.5)), L[lab], 0.01 * u)   # brows
    f.add(Ellipsoid(c + R @ A(0, 0.05, -0.0) * u, A(0.035, 0.03, 0.04) * u, R), L[lab], 0.01 * u)       # nose
    f.sub(Ellipsoid(c + R @ A(0, 0.05, -0.08) * u, A(0.1, 0.03, 0.025) * u, R), 0.006 * u)              # mouth

def scarf_side(xm, fig, s, q, hh, out=0.0, back=0.0, end_curl=1.0, z_end=0.12, width=0.13):
    """天衣 hanging close to the body on one side: from behind the shoulder over the upper arm, down beside the hip in an
    S-curve, its end flicking outward at the knee"""
    a = fig.arm['r' if s > 0 else 'l']; sh = a['S']; E = a['E']
    hip = fig.Op
    knee_z = min(g['K'][2] for g in fig.leg.values())
    xo = hip[0] + s * (0.82 + out * 0.6) * hh
    ctrl = [sh + A(-s * 0.35, -0.3, 0.12) * hh, sh + A(s * 0.08, -0.25, 0.18) * hh, sh + A(s * 0.32, -0.08, -0.25) * hh,
            A(xo - s * 0.05 * hh, hip[1] - 0.05 * hh, (sh[2] + hip[2]) / 2),
            A(xo + s * 0.08 * hh, hip[1] + 0.05 * hh, hip[2] - 0.4 * hh),
            A(xo - s * 0.02 * hh, hip[1] + 0.1 * hh, (hip[2] + knee_z) / 2),
            A(xo + s * (0.25 + 0.3 * end_curl) * hh, hip[1] + 0.15 * hh, knee_z + 0.15 * hh),
            A(xo + s * (0.45 + 0.4 * end_curl) * hh, hip[1] + 0.05 * hh, knee_z + 0.35 * hh)]
    pts = spline(ctrl, 40 if q > 0.6 else 14)
    n = len(pts)
    ups = []
    for k, p in enumerate(pts):
        t = k / max(n - 1, 1)
        o = nrm(A(p[0] - fig.Op[0], p[1] - fig.Op[1], 0.0))
        ups.append(nrm(o * (0.9 - 0.5 * math.sin(t * math.pi)) + A(0, 0.5 + 0.6 * math.sin(t * math.pi * 2.0 + s), 0.0)))
    ws = np.interp(np.linspace(0, 1, n), [0, 0.3, 0.75, 1.0], [0.55, 0.85, 1.0, 0.7]) * width * hh
    X.ribbon(xm, pts, ws, 0.01 * hh, ups, 'scarf')

def hanging_drape(f, fig, a, hh, lab='robe2', length=1.3, width=0.48):
    """the sleeve of a raised forearm hanging below it as a big soft drape (img 10, 21)"""
    S_, E, Wr = a['S'], a['E'], a['W']; s = a['s']
    top = E + (Wr - E) * 0.3
    low = A(top[0] + s * 0.2 * hh, top[1] - 0.05 * hh, top[2] - length * hh)
    pts = spline([top, (top + low) / 2 + A(s * 0.12, -0.08, 0) * hh, low, low + A(s * 0.25, 0.1, 0.15) * hh], 16)
    out = nrm(A(s * 0.7, 1, 0))
    def folds(P): return (-0.004 * np.cos((P @ np.cross(out, (0, 0, 1))) / hh * 18.0 + 1.0)).astype(np.float32)
    f.add(Displace(Sweep(pts, np.interp(np.linspace(0, 1, len(pts)), [0, 0.7, 1], [0.5, 1.0, 0.7]) * width * hh, 0.03 * hh, [out] * len(pts)), folds, 0.005), L[lab], 0.04 * hh)

def flared_cuff(f, fig, a, hh, lab='robe2', size=1.0):
    """the under-robe sleeve at the elbow: a short flared cuff, its loose end swinging back and down"""
    S_, E, Wr = a['S'], a['E'], a['W']; s = a['s']
    up = nrm(E - S_); fore = nrm(Wr - E)
    f.add(RCone(S_ + up * 0.15 * hh, E, 0.22 * hh, 0.24 * hh), L[lab], 0.03 * hh)
    b0 = E - fore * 0.08 * hh; b1 = E + fore * 0.2 * hh * size
    cone = RCone(b0, b1, 0.24 * hh * size, 0.34 * hh * size)
    f.add(Inter([Shell(cone, 0.018 * hh), Plane(b0 + fore * 0.04 * hh, -fore), Plane(b1 - fore * 0.03 * hh, fore)], 0.005 * hh), L[lab], 0.012 * hh)
    sw = nrm(A(s * 0.35, -1, -0.9))
    p0 = E - up * 0.18 * hh
    pts = spline([p0, p0 + sw * 0.3 * hh, p0 + (sw * 0.6 + A(0, 0, -0.05)) * hh, p0 + (sw * 0.85 + A(s * 0.1, 0, 0.0)) * hh], 16)
    nml = nrm(np.cross(sw, up)) if np.linalg.norm(np.cross(sw, up)) > 1e-3 else A(1, 0, 0)
    f.add(Sweep(pts, np.linspace(0.26, 0.16, len(pts)) * hh * size, 0.016 * hh, [nml] * len(pts)), L[lab], 0.02 * hh)

# ---------------------------------------------------------------------------------------------- costumes

def dragon_head(f, p, fwd, up, size, lab='snake', jaw=0.35):
    """龍頭: long snout with an open jaw and teeth, bulging eyes under heavy brows, two swept-back horns, whiskers,
    a mane of flame tufts behind the head"""
    fwd = nrm(np.asarray(fwd, float)); up = nrm(np.asarray(up, float) - fwd * (np.asarray(up, float) @ fwd)); side = np.cross(fwd, up)
    R = np.stack([side, fwd, up], 1); u = size
    Q = lambda v: p + R @ (A(*v) * u)
    f.add(Ellipsoid(Q((0, 0, 0)), A(0.45, 0.55, 0.45) * u, R), L[lab], 0.1 * u)                         # skull
    f.add(Ellipsoid(Q((0, 0.7, 0.05)), A(0.28, 0.6, 0.22) * u, R), L[lab], 0.15 * u)                    # upper snout
    f.add(Ellipsoid(Q((0, 1.15, 0.12)), A(0.26, 0.18, 0.18) * u, R), L[lab], 0.08 * u)                  # nose pad
    ja = R @ rot((1, 0, 0), -jaw)
    f.add(Ellipsoid(Q((0, 0.55, -0.32)), A(0.22, 0.55, 0.1) * u, ja), L[lab], 0.06 * u)                 # lower jaw
    for s_ in (1, -1):
        f.add(Sphere(Q((s_ * 0.24, 0.28, 0.28)), 0.13 * u), L['eye'], 0.02 * u)
        f.add(Ellipsoid(Q((s_ * 0.24, 0.3, 0.42)), A(0.16, 0.12, 0.07) * u, R), L[lab], 0.05 * u)        # brow
        f.add(Tube([Q((s_ * 0.2, -0.1, 0.4)), Q((s_ * 0.32, -0.55, 0.65)), Q((s_ * 0.35, -1.0, 0.75)), Q((s_ * 0.28, -1.3, 0.95))], A(0.08, 0.06, 0.04, 0.015) * u), L[lab], 0.04 * u)   # horns
        f.add(Tube([Q((s_ * 0.18, 1.05, 0.05)), Q((s_ * 0.5, 1.2, 0.0)), Q((s_ * 0.8, 1.0, -0.15)), Q((s_ * 0.95, 0.75, -0.3))], A(0.03, 0.022, 0.015, 0.008) * u), L[lab], 0.01 * u)   # whiskers
        for t in (0.35, 0.6, 0.85):
            f.add(RCone(Q((s_ * 0.17, 0.25 + 0.75 * t, -0.08)), Q((s_ * 0.16, 0.25 + 0.75 * t, -0.2)), 0.035 * u, 0.006 * u), L['teeth'], 0.0)
        for k in range(3):
            b = Q((s_ * 0.3, -0.35 - 0.1 * k, 0.1 - 0.25 * k))
            f.add(Tube([b, b + R @ A(s_ * 0.35, -0.35, 0.15) * u, b + R @ A(s_ * 0.45, -0.75, 0.4) * u], A(0.1, 0.06, 0.01) * u), L[lab], 0.04 * u)   # mane
    f.sub(Ellipsoid(Q((0, 0.75, -0.13)), A(0.2, 0.5, 0.1) * u, R @ rot((1, 0, 0), -jaw * 0.5)), 0.03 * u, lab=L['mouth'])

def dragon_body(f, pts, r0, lab='snake'):
    """a scaled body: a tube with a dorsal ridge of small spines"""
    pts = spline(pts, max(16, 6 * len(pts)))
    n = len(pts)
    rad = np.interp(np.linspace(0, 1, n), [0, 0.15, 0.8, 1], [r0 * 0.35, r0 * 0.9, r0, r0 * 0.85])
    f.add(Tube(pts, rad), L[lab], r0 * 0.3)
    for k in range(2, n - 1, 2):
        d = nrm(pts[k + 1] - pts[k - 1]); up = nrm(np.cross(d, np.cross(A(0, 0, 1), d)) + A(0, 0, 0.01)) if abs(d[2]) < 0.95 else A(1, 0, 0)
        f.add(RCone(pts[k] + up * rad[k] * 0.7, pts[k] + up * rad[k] * 1.5 - d * rad[k] * 0.5, rad[k] * 0.35, rad[k] * 0.05), L[lab], rad[k] * 0.2)

def dragon_held2(f, fig, U, hh):
    """難陀龍王: a dragon held up in the right hand by the neck, its head reared beside the face, the body coiling down
    across the chest to the left hand at the waist and its tail hanging"""
    a, b = fig.arm['r']['W'], fig.arm['l']['W']
    head = a + A(-0.02, 0.06, 0.13)
    body = [head + A(0.0, -0.02, -0.06), a + A(0.0, 0.05, -0.02), a + A(-0.1, 0.12, -0.15), (a + b) / 2 + A(0.02, 0.16, 0.0),
            b + A(0.08, 0.1, 0.05), b + A(0.0, 0.06, -0.02), b + A(-0.06, 0.06, -0.2), b + A(-0.02, 0.1, -0.38)]
    dragon_body(f, body, 0.03)
    dragon_head(f, head, nrm(A(-0.3, 0.6, 0.6)), A(0, 0, 1), 0.075, jaw=0.45)

def lion_head_cap(g, R, O, hh):
    """乾闥婆's helmet: a lion's head worn over the head — its brow, eyes and upper jaw with teeth over the forehead, ears,
    and the mane flaring up and out in flame-like tufts"""
    P = lambda v: O + R @ (A(*v) * hh)
    g.add(Inter([Ellipsoid(P((0, -0.04, 0.16)), A(0.43, 0.5, 0.5) * hh, R), Plane(P((0, 0.33, 0.24)), R @ nrm(A(0, 0.3, -1)))], 0.02 * hh), L['cap'], 0.01 * hh)
    g.add(Ellipsoid(P((0, 0.32, 0.45)), A(0.3, 0.22, 0.2) * hh, R), L['cap'], 0.06 * hh)               # the lion's face
    g.add(Ellipsoid(P((0, 0.48, 0.38)), A(0.15, 0.12, 0.1) * hh, R), L['cap'], 0.05 * hh)               # muzzle
    g.add(Sphere(P((0, 0.58, 0.42)), 0.055 * hh), L['cap'], 0.02 * hh)                                    # nose
    for s in (1, -1):
        g.add(Sphere(P((s * 0.13, 0.46, 0.52)), 0.05 * hh), L['eye'], 0.01 * hh)
        g.add(Ellipsoid(P((s * 0.14, 0.45, 0.6)), A(0.1, 0.06, 0.04) * hh, R @ rot((0, 1, 0), -s * 0.4)), L['cap'], 0.03 * hh)
        g.add(Ellipsoid(P((s * 0.3, 0.2, 0.62)), A(0.06, 0.04, 0.1) * hh, R @ rot((0, 1, 0), s * 0.5)), L['cap'], 0.03 * hh)    # ears
        for k in range(3):     # teeth of the upper jaw over the forehead
            g.add(RCone(P((s * (0.05 + 0.07 * k), 0.46, 0.28)), P((s * (0.05 + 0.07 * k), 0.47, 0.2)), 0.02 * hh, 0.005 * hh), L['teeth'], 0.0)
    for k in range(9):         # the mane
        a = -1.3 + 2.6 * k / 8
        b = P((0.38 * math.sin(a), 0.05 + 0.15 * math.cos(a), 0.45))
        o = R @ nrm(A(math.sin(a), 0.2 * math.cos(a), 0.9))
        side = R @ nrm(A(math.cos(a), 0, -math.sin(a) * 0.3))
        g.add(Tube([b, b + o * 0.2 * hh + side * 0.05 * hh, b + o * 0.34 * hh - side * 0.04 * hh, b + o * 0.4 * hh + side * 0.03 * hh], A(0.07, 0.05, 0.03, 0.01) * hh), L['cap'], 0.03 * hh)

def feather_wing(f, b, s, hh, lab='feather'):
    """迦楼羅's wing: three overlapping rows of pointed feathers (coverts, secondaries, primaries) along an arm that rises
    from the shoulder blade, bends out at the wrist and sweeps down"""
    arm = spline([b, b + A(s * 0.55, -0.2, 0.5) * hh, b + A(s * 1.15, -0.25, 0.55) * hh, b + A(s * 1.55, -0.2, 0.15) * hh], 24)
    f.add(Tube(arm, np.linspace(0.09, 0.04, len(arm)) * hh), L[lab], 0.03 * hh)
    nrm_w = nrm(A(-s * 0.3, 1, 0.05))
    rows = [(0.35, 0.28, 10, 0.05), (0.75, 0.6, 9, 0.11), (1.35, 1.0, 8, 0.17)]
    for ri, (Lf, wv, nf, off) in enumerate(rows):
        for k in range(nf):
            t = (k + 0.5) / nf
            j = int(t * (len(arm) - 1)); p = arm[j] - nrm_w * 0.012 * hh * ri
            dn = nrm(A(s * (0.15 + 0.6 * t), -0.1, -1.0))
            Lk = Lf * hh * (0.75 + 0.35 * t if ri == 2 else 1.0)
            pts = [p + dn * Lk * u + A(s * 0.04, 0, 0) * hh * u * u for u in np.linspace(0, 1, 6)]
            ws = np.interp(np.linspace(0, 1, 6), [0, 0.3, 0.75, 1], [0.04, 0.085, 0.07, 0.006]) * hh * (1.1 if ri == 2 else 1.0)
            f.add(Sweep(pts, ws, 0.012 * hh, [nrm_w] * 6), L[lab], 0.006 * hh)
            f.add(Capsule(pts[0], pts[-2], 0.008 * hh), L[lab], 0.004 * hh)       # the shaft


def nio_relief(f, fig, hh):
    """the carved musculature of the Niō: pectorals with a hard lower edge, a six-pack crossed by tendinous lines,
    serratus fingers, obliques, the iliac V, the ribcage edge"""
    Rc, Oc, Rw, Wp = fig.Rc, fig.Oc, fig.Rw, fig.W
    c = lambda v: Oc + Rc @ (A(*v) * hh); w = lambda v: Wp + Rw @ (A(*v) * hh)
    for s in (1, -1):
        f.add(Ellipsoid(c((s * 0.3, 0.38, 0.12)), A(0.33, 0.13, 0.25) * hh, Rc @ rot((0, 1, 0), -s * 0.25) @ rot((1, 0, 0), 0.2)), L['skin'], 0.03 * hh)
        f.sub(Tube([c((s * 0.03, 0.52, -0.08)), c((s * 0.28, 0.48, -0.16)), c((s * 0.55, 0.3, -0.04))], A(0.025, 0.03, 0.02) * hh), 0.025 * hh)
        f.sub(Tube([c((s * 0.6, 0.18, 0.4)), c((s * 0.5, 0.36, 0.15)), c((s * 0.45, 0.4, 0.0))], A(0.015, 0.02, 0.015) * hh), 0.02 * hh)   # pec / deltoid
        for i in range(4):      # serratus fingers
            f.add(Ellipsoid(c((s * 0.52, 0.28 - 0.02 * i, -0.2 - 0.12 * i)), A(0.06, 0.06, 0.04) * hh, Rc @ rot((0, 1, 0), s * 0.5)), L['skin'], 0.012 * hh)
        f.add(Ellipsoid(w((s * 0.42, 0.25, -0.35)), A(0.14, 0.2, 0.26) * hh, Rw), L['skin'], 0.04 * hh)        # obliques
        f.sub(Tube([w((s * 0.5, 0.3, -0.55)), w((s * 0.3, 0.45, -0.8)), w((s * 0.1, 0.5, -0.95))], A(0.02, 0.025, 0.02) * hh), 0.025 * hh)     # iliac V
        f.sub(Tube([c((s * 0.12, 0.5, -0.45)), c((s * 0.35, 0.4, -0.55)), c((s * 0.5, 0.3, -0.5))], A(0.015, 0.018, 0.015) * hh), 0.02 * hh)   # ribcage edge
        for zz in (-0.15, -0.42, -0.68):       # rectus blocks
            f.add(Ellipsoid(w((s * 0.11, 0.48, zz + 0.12)), A(0.1, 0.06, 0.1) * hh, Rw), L['skin'], 0.015 * hh)
    for zz in (-0.02, -0.29, -0.56):          # tendinous intersections
        f.sub(Tube([w((-0.22, 0.48, zz + 0.12)), w((0, 0.53, zz + 0.1)), w((0.22, 0.48, zz + 0.12))], A(0.012, 0.015, 0.012) * hh), 0.015 * hh)
    f.sub(Capsule(w((0, 0.55, 0.3)), w((0, 0.53, -0.75)), 0.018 * hh), 0.02 * hh)
    f.sub(Sphere(w((0, 0.56, -0.62)), 0.025 * hh), 0.01 * hh)                     # navel

def emaciated(f, fig, hh):
    """婆籔仙: ribs standing out under thin skin, sharp collarbones, a sunken belly"""
    Rc, Oc = fig.Rc, fig.Oc
    c = lambda v: Oc + Rc @ (A(*v) * hh)
    for i in range(6):
        for s in (1, -1):
            pts = [c((s * 0.06, 0.46 - 0.01 * i, 0.32 - 0.14 * i)), c((s * 0.3, 0.4, 0.26 - 0.15 * i)), c((s * 0.52, 0.18, 0.18 - 0.16 * i)), c((s * 0.58, -0.05, 0.12 - 0.16 * i))]
            f.add(Tube(pts, A(0.022, 0.026, 0.024, 0.02) * hh), L['skin'], 0.012 * hh)
    for s in (1, -1):
        f.add(Capsule(c((s * 0.05, 0.4, 0.62)), c((s * 0.5, 0.15, 0.62)), 0.035 * hh), L['skin'], 0.012 * hh)
        f.sub(Ellipsoid(c((s * 0.28, 0.42, 0.52)), A(0.15, 0.06, 0.06) * hh, Rc), 0.03 * hh)       # hollows above the clavicles
    f.add(Capsule(c((0, 0.47, 0.35)), c((0, 0.46, -0.3)), 0.03 * hh), L['skin'], 0.012 * hh)      # sternum


def leg_skirt(f, fig, hh, z_top, hem, r_hip, r_knee, r_hem, lab, k=0.03, folds=(9, 0.008), seed=0.0, hip_rx=0.66, hip_ry=0.5):
    """a skirt that follows the legs: a ring round the hips from z_top down to the crotch, and from each hip a tube
    along the thigh, over the knee and dropping to the hem (hem: z, or {'r': z, 'l': z}); folds round each leg"""
    Op = fig.Op
    zc = Op[2] - 0.38 * hh
    xs = [g['H'][0] for g in fig.leg.values()]; cx = sum(xs) / 2
    rows = [(zc, cx, Op[1] - 0.02 * hh, (abs(xs[0] - xs[1]) / 2 + r_hip * 0.95) * 1.0, r_hip * 1.15), (z_top, Op[0], Op[1], hip_rx * hh, hip_ry * hh)]
    f.add(Loft(rows), L[lab], k)
    for nm, g in fig.leg.items():
        H, K = g['H'], g['K']
        zh = hem[nm] if isinstance(hem, dict) else hem
        drop = A(K[0], K[1] + 0.04 * hh, min(zh - 0.15 * hh, K[2] - 0.05 * hh))
        tube = Tube([H + A(0, 0, 0.15 * hh), K + A(0, 0.03 * hh, 0.02 * hh), drop], [r_hip, r_knee, r_hem])
        n_, amp = folds
        def fd(P, K=K): 
            th = np.arctan2(P[:, 1] - K[1], P[:, 0] - K[0])
            w = np.clip((K[2] + 0.6 * hh - P[:, 2]) / (0.8 * hh), 0, 1)
            return (-amp * w * (0.7 * np.cos(n_ * th + seed + 3 * P[:, 2] / hh) + 0.3 * np.cos(2.2 * n_ * th + seed))).astype(np.float32)
        piece = Inter([Displace(tube, fd, amp), Plane(A(0, 0, zh), A(0, 0, -1))])
        f.add(piece, L[lab], k)

def boots_shaped(f, fig, hh, lab='shoe', rim='armour'):
    """沓: boots that follow the leg — shaft from below the knee, calf swelling behind, narrowing ankle, a foot with an
    upturned toe"""
    for nm, g in fig.leg.items():
        K, Ak = g['K'], g['A']
        ax = nrm(Ak - K)
        fd = g['foot_dir'] * A(1, 1, 0); fd = nrm(fd)
        back = nrm(-fd + ax * (fd @ ax))
        top = K + ax * 0.26 * hh
        f.add(RCone(top, Ak + ax * 0.03 * hh, 0.205 * hh, 0.145 * hh), L[lab], 0.02 * hh)
        f.add(Ellipsoid(K + (Ak - K) * 0.36 + back * 0.05 * hh, A(0.2, 0.2, 0.42) * hh, frame(z=ax, y=-back)), L[lab], 0.06 * hh)
        f.add(Torus(top + ax * 0.01 * hh, 0.205 * hh, 0.022 * hh, frame(z=ax, x=(1, 0, 0) if abs(ax[0]) < 0.9 else (0, 1, 0))), L[rim], 0.01 * hh)
        sole = Ak[2] - 0.26 * hh
        f.add(Ellipsoid(A(Ak[0], Ak[1], sole + 0.12 * hh) + fd * 0.24 * hh, A(0.21, 0.52, 0.13) * hh, frame(y=fd, z=(0, 0, 1))), L[lab], 0.06 * hh)
        toe = A(Ak[0], Ak[1], sole + 0.13 * hh) + fd * 0.66 * hh
        f.add(Ellipsoid(toe, A(0.14, 0.15, 0.09) * hh, frame(y=fd, z=(0, 0, 1))), L[lab], 0.05 * hh)
        f.add(Ellipsoid(toe + fd * 0.08 * hh + A(0, 0, 0.05 * hh), A(0.07, 0.07, 0.05) * hh, frame(y=nrm(fd + A(0, 0, 0.6)), z=(0, 0, 1))), L[lab], 0.04 * hh)   # upturned tip

def trousers(f, fig, hh, lab='robe2', tie='belt'):
    """袴 over the thighs, gathered and tied below the knee where they puff over the boot tops"""
    for nm, g in fig.leg.items():
        H, K = g['H'], g['K']; ax = nrm(g['A'] - K); ax1 = nrm(K - H)
        f.add(RCone(H, K, 0.33 * hh, 0.23 * hh), L[lab], 0.06 * hh)
        puff = K + ax * 0.12 * hh
        def pf(P, c=puff): return (-0.008 * hh / 0.21 * np.cos(9 * np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0]))).astype(np.float32)
        f.add(Displace(Ellipsoid(puff + A(0, 0.02 * hh, 0), A(0.25, 0.26, 0.2) * hh), pf, 0.01), L[lab], 0.05 * hh)
        f.add(Torus(K + ax * 0.24 * hh, 0.21 * hh, 0.022 * hh, frame(z=ax, x=(1, 0, 0) if abs(ax[0]) < 0.9 else (0, 1, 0))), L[tie], 0.01 * hh)

def boots(f, fig, hh, lab='shoe', greave=True):
    for nm, g in fig.leg.items():
        K, Ak = g['K'], g['A']
        ax = nrm(Ak - K)
        f.add(RCone(K + ax * 0.22 * hh, Ak + A(0, 0, 0.02) * hh, 0.3 * hh, 0.24 * hh), L[lab], 0.02 * hh)
        f.add(Torus(K + ax * 0.23 * hh, 0.3 * hh, 0.025 * hh, frame(z=-ax, x=(1, 0, 0))), L['armour'], 0.01 * hh)
        fd = nrm(g['foot_dir'] * A(1, 1, 0))
        sole = Ak[2] - 0.26 * hh
        f.add(Ellipsoid(A(Ak[0], Ak[1], sole + 0.13 * hh) + fd * 0.3 * hh, A(0.28, 0.6, 0.16) * hh, frame(y=fd, z=(0, 0, 1))), L[lab], 0.07 * hh)
        f.add(Ellipsoid(A(Ak[0], Ak[1], sole + 0.17 * hh) + fd * 0.7 * hh, A(0.17, 0.2, 0.12) * hh, frame(y=fd, z=(0, 0, 1))), L[lab], 0.06 * hh)

def costume_armour(f, fig, sp, rng, hh):
    """甲冑 after the photographs (img 9, 10, 17, 20, 24 ...)"""
    Op = fig.Op; Rc, Oc, Rw, Wp, Rp = fig.Rc, fig.Oc, fig.Rw, fig.W, fig.Rp
    c = lambda v: Oc + Rc @ (A(*v) * hh); w = lambda v: Wp + Rw @ (A(*v) * hh); p = lambda v: Op + Rp @ (A(*v) * hh)
    zb = Op[2] + 0.3 * hh                                        # belt
    rng_seed = rng.uniform(0, 6)
    trousers(f, fig, hh)
    boots_shaped(f, fig, hh)
    knee_z = min(g['K'][2] for g in fig.leg.values())
    ks = {nm: g['K'] for nm, g in fig.leg.items()}
    def knee_hem(base, lift_front=0.0, wave=0.0, nw=5):
        # hem height round the skirt: lower over each knee (the cloth breaks over it), higher between and behind
        def fn(th):
            z = np.full(len(th), base, np.float32)
            for K in ks.values():
                a_k = math.atan2(K[1] - Op[1], K[0] - Op[0])
                dth = np.angle(np.exp(1j * (th - a_k)))
                z = z - 0.18 * hh * np.exp(-(dth / 0.5) ** 2)
            z = z + lift_front * hh * np.clip(np.sin(th), 0, 1) ** 2 + 0.12 * hh * np.clip(-np.sin(th), 0, 1)
            return (z + wave * hh * np.cos(nw * th + rng_seed)).astype(np.float32)
        return fn
    # under-skirt (裳): flares from the belt over the thighs, breaking over the knees
    rows = skirt_rows(fig, zb, knee_z + sp.get('skirt_knee', -0.15) * hh, extra=0.03, flare=0.3)
    cc = (rows[0][1], rows[0][2], 0)
    f.add(Over(rows, knee_hem(knee_z + sp.get('skirt_knee', -0.15) * hh + 0.1 * hh, 0.25, 0.04, 7), fold_fn(cc, 11, 0.012 * hh, rng_seed)), L['robe'], 0.02 * hh)
    # waist armour (表甲): two flared layers ending on the thighs, the lower one split in front
    rows1 = skirt_rows(fig, zb, Op[2] - 0.75 * hh, extra=0.08, flare=0.32)
    f.add(Over(rows1, knee_hem(Op[2] - 0.62 * hh, 0.0, 0.05, 6), panel_fn(cc, 6, 0.007 * hh)), L['armour'], 0.01 * hh)
    rows2 = skirt_rows(fig, zb - 0.2 * hh, Op[2] - 1.15 * hh, extra=0.05, flare=0.36)
    f.add(Over(rows2, knee_hem(Op[2] - 1.0 * hh, 0.35, 0.05, 5), fold_fn(cc, 6, 0.006 * hh, rng_seed + 1)), L['armour2'], 0.01 * hh)
    fy = max(r[2] + r[4] for r in rows1) + 0.015 * hh
    ap_top = zb - 0.05 * hh; ap_bot = Op[2] - sp.get('apron', 1.15) * hh
    apron = Box(A(cc[0], fy, (ap_top + ap_bot) / 2), A(0.24 * hh, 0.025 * hh, (ap_top - ap_bot) / 2), None, 0.02 * hh)
    f.add(apron, L['armour3'], 0.01 * hh)
    f.add(Ellipsoid(A(cc[0], fy, ap_bot + 0.02 * hh), A(0.24, 0.025, 0.08) * hh), L['armour3'], 0.03 * hh)
    if sp.get('gold_apron'): gold_patches(f, Offset(apron, 0.02), 0.03, sp['gold_apron'], 3)
    # belt, belly plate with a lion mask, bow knot
    f.add(Band(Op + A(0, 0.02, 0.3 * hh), 0.66 * hh, 0.52 * hh, 0.05 * hh, 0.06 * hh, Rp), L['belt'], 0.01 * hh)
    belly = Ellipsoid(w((0, 0.06, -0.05)), A(0.66, 0.56, 0.62) * hh, Rw)
    f.add(Inter([Shell(Offset(belly, 0.04 * hh), 0.025 * hh), Box(w((0, 0.55, 0.02)), A(0.5, 0.45, 0.36) * hh, Rw, 0.12 * hh)], 0.01 * hh), L['armour2'], 0.015 * hh)
    lion_face(f, w((0, 0.7, 0.02)), Rw, hh, 'boss', 1.1)
    bow_knot(f, Op + Rp @ A(0, 0.62, 0.28) * hh, Rp, hh, 'belt', 1.0)
    # breast plates, a central strap with ring loops, the chest band with a bow
    chest = Ellipsoid(c((0, 0.03, 0.02)), A(0.74, 0.58, 0.78) * hh, Rc)
    for s in (1, -1):
        f.add(Inter([Shell(Offset(chest, 0.035 * hh), 0.022 * hh), Box(c((s * 0.3, 0.55, 0.12)), A(0.26, 0.4, 0.24) * hh, Rc, 0.1 * hh)], 0.008 * hh), L['armour'], 0.01 * hh)
        f.add(Torus(c((s * 0.12, 0.66, 0.28)), 0.05 * hh, 0.012 * hh, Rc @ frame(z=(0, 1, 0), x=(1, 0, 0))), L['trim'], 0.004 * hh)
    f.add(Box(c((0, 0.64, 0.25)), A(0.035, 0.02, 0.3) * hh, Rc, 0.01 * hh), L['belt'], 0.008 * hh)
    f.add(Band(c((0, 0.04, -0.3)), 0.76 * hh, 0.6 * hh, 0.035 * hh, 0.04 * hh, Rc), L['belt'], 0.008 * hh)
    bow_knot(f, c((0, 0.64, -0.3)), Rc, hh, 'belt', 0.7)
    # collar cape (襟甲) over the shoulders with standing lapels
    N = fig.N
    cape = Ellipsoid(N + Rc @ A(0, -0.03, -0.3) * hh, A(0.92, 0.64, 0.34) * hh, Rc)
    f.add(Diff(Inter([Shell(cape, 0.026 * hh), Plane(N + Rc @ A(0, 0, -0.48) * hh, -Rc[:, 2])], 0.01 * hh),
               [Cyl(N - Rc[:, 2] * 0.3 * hh, N + Rc[:, 2] * 0.5 * hh, 0.3 * hh, 0.02 * hh)], 0.01 * hh), L['armour2'], 0.01 * hh)
    for s in (1, -1):
        f.add(Ellipsoid(N + Rc @ A(s * 0.24, 0.12, 0.08) * hh, A(0.05, 0.16, 0.16) * hh, Rc @ rot((0, 0, 1), s * 0.6) @ rot((1, 0, 0), -0.3)), L['armour2'], 0.015 * hh)
    # shoulder guards, sleeves, forearm guards
    for nm, a in fig.arm.items():
        s = a['s']; up = nrm(a['E'] - a['S'])
        Rs = frame(z=up, x=A(s, 0, 0) - up * (up[0] * s))
        sh = Ellipsoid(a['S'] + up * 0.12 * hh + A(s * 0.02, 0, 0.02) * hh, A(0.27, 0.27, 0.36) * hh, Rs)
        f.add(Inter([Shell(sh, 0.018 * hh), Plane(a['S'] + up * 0.38 * hh, up), Plane(a['S'] + A(-s * 0.05, 0, 0) * hh, A(-s, 0, 0))], 0.008 * hh), L['armour'], 0.006 * hh)
        raised = a['W'][2] > a['E'][2] - 0.1 * hh
        if raised and sp.get('drapes', True): hanging_drape(f, fig, a, hh, 'robe2', length=sp.get('drape_len', 1.1))
        flared_cuff(f, fig, a, hh, 'robe2', size=sp.get('sleeve', 1.0))
        ax = nrm(a['W'] - a['E'])
        f.add(RCone(a['E'] + ax * 0.2 * hh, a['W'] - ax * 0.04 * hh, 0.19 * hh, 0.16 * hh), L['armour'], 0.02 * hh)
    if sp.get('gold_skirt'): gold_patches(f, Offset(Loft(rows), 0.02), 0.04, sp['gold_skirt'], 5)

def costume_nio(f, fig, sp, rng, hh):
    """裙 of the Niō: wrapped round the hips, a rolled waist, falling to the knee and lower on one side, long flaps
    between and behind the legs fluttering out"""
    Op = fig.Op
    zt = Op[2] + 0.25 * hh
    hs = sp.get('hem_side', 1)
    hem = {nm: g['K'][2] + (0.25 if g['s'] == hs else -0.25) * hh for nm, g in fig.leg.items()}
    leg_skirt(f, fig, hh, zt, hem, 0.46 * hh, 0.42 * hh, 0.5 * hh, 'robe', k=0.03 * hh, folds=(8, 0.014 * hh), seed=rng.uniform(0, 6))
    rows = skirt_rows(fig, zt, Op[2] - 0.5 * hh, extra=0.0, flare=0.2)
    cc = (rows[0][1], rows[0][2], 0)
    # rolled waist (腰巻の折り返し) and the knot in front
    f.add(Band(Op + A(0, 0.02, 0.25 * hh), 0.66 * hh, 0.52 * hh, 0.07 * hh, 0.08 * hh, fig.Rp), L['robe3'], 0.03 * hh)
    k = Op + fig.Rp @ A(-0.1 * hs, 0.58, 0.22) * hh
    f.add(Ellipsoid(k, A(0.16, 0.08, 0.1) * hh, fig.Rp), L['robe3'], 0.03 * hh)
    # long flaps: one hanging between the legs to the ankles, one blown out sideways
    mid = A(cc[0], cc[1] + 0.45 * hh, Op[2] - 0.1 * hh)
    pts = spline([k, mid, A(cc[0] + 0.05 * hh, cc[1] + 0.35 * hh, 1.5 * hh), A(cc[0] - 0.1 * hh, cc[1] + 0.3 * hh, 0.55 * hh)], 16)
    f.add(Displace(Sweep(pts, np.linspace(0.18, 0.3, 16) * hh, 0.03 * hh, [A(0, 1, 0.1)] * 16), lambda P: (-0.006 * np.cos(P[:, 0] / hh * 20)).astype(np.float32), 0.007), L['robe'], 0.03 * hh)
    so = sp.get('flap_side', -hs)
    pts = spline([Op + A(so * 0.4, -0.2, -0.3) * hh, Op + A(so * 0.9, -0.1, -1.4) * hh, A(Op[0] + so * 1.5 * hh, Op[1] + 0.0, 1.4 * hh), A(Op[0] + so * 2.3 * hh, Op[1] + 0.1 * hh, 1.25 * hh)], 18)
    f.add(Sweep(pts, np.linspace(0.3, 0.12, 18) * hh, 0.025 * hh, [nrm(A(0, 1, 0.3))] * 18), L['robe'], 0.03 * hh)
    pts = spline([Op + A(-so * 0.3, -0.35, -0.2) * hh, Op + A(-so * 0.6, -0.4, -1.4) * hh, A(Op[0] - so * 0.9 * hh, Op[1] - 0.2 * hh, 0.9 * hh), A(Op[0] - so * 1.3 * hh, Op[1] - 0.05 * hh, 0.5 * hh)], 16)
    f.add(Sweep(pts, np.linspace(0.3, 0.15, 16) * hh, 0.025 * hh, [nrm(A(-so * 0.3, 1, 0.2))] * 16), L['robe'], 0.03 * hh)
    if sp.get('gold_skirt'): gold_patches(f, Offset(Loft(rows), 0.03), 0.04, sp['gold_skirt'], 5)

def costume_bare(f, fig, sp, rng, hh):
    """bare torso, a long skirt to the shins with a folded-over waist cloth and an apron (毘舎闍, 薩遮摩和羅, 阿修羅)"""
    Op = fig.Op
    zt = Op[2] + 0.3 * hh
    hem = {nm: g['A'][2] + (sp.get('skirt_bot', 0.7) - 0.28) * hh for nm, g in fig.leg.items()}
    leg_skirt(f, fig, hh, zt, hem, 0.46 * hh, 0.4 * hh, 0.42 * hh, 'robe', k=0.03 * hh, folds=(10, 0.01 * hh), seed=rng.uniform(0, 6))
    rows = skirt_rows(fig, zt, sp.get('skirt_bot', 0.7) * hh, extra=0.02, flare=0.3)
    cc = (rows[0][1], rows[0][2], 0)
    rows2 = skirt_rows(fig, zt + 0.05 * hh, Op[2] - 0.55 * hh, extra=0.1, flare=0.15)
    def hem(th): return (Op[2] - 0.55 * hh - 0.35 * hh * np.clip(np.sin(th), 0, 1) ** 2).astype(np.float32)
    f.add(Over(rows2, hem, fold_fn(cc, 7, 0.01 * hh)), L['robe3'], 0.01 * hh)
    f.add(Band(Op + A(0, 0.02, 0.3 * hh), 0.64 * hh, 0.5 * hh, 0.04 * hh, 0.05 * hh, fig.Rp), L['belt'], 0.01 * hh)
    fy = max(r[2] + r[4] for r in rows2)
    apron = Box(A(cc[0], fy + 0.02 * hh, (zt + 0.9 * hh) / 2), A(0.2 * hh, 0.02 * hh, (zt - 0.9 * hh) / 2), None, 0.02 * hh)
    f.add(apron, L['robe2'], 0.02 * hh)
    if sp.get('gold_skirt'): gold_patches(f, Offset(Loft(rows), 0.03), 0.035, sp['gold_skirt'], 5)
    if sp.get('gold_skirt'): gold_patches(f, Offset(apron, 0.02), 0.03, sp['gold_skirt'], 6)
    for nm, a in fig.arm.items():
        for (pp, r) in ((a['S'] + (a['E'] - a['S']) * 0.45, 0.21), (a['W'] - nrm(a['W'] - a['E']) * 0.03 * hh, 0.17)):
            ax = nrm(a['E'] - a['S']) if r > 0.2 else nrm(a['W'] - a['E'])
            f.add(Torus(pp, r * hh, 0.025 * hh, frame(z=ax, x=(0, 1, 0) if abs(ax[1]) < 0.9 else (1, 0, 0))), L['jewel'], 0.01 * hh)
    if sp.get('neck_scarf'):
        Rc, Oc = fig.Rc, fig.Oc
        k = fig.N + Rc @ A(0, 0.32, -0.12) * hh
        f.add(Torus(fig.N + Rc @ A(0, 0.05, -0.08) * hh, 0.36 * hh, 0.07 * hh, Rc @ rot((1, 0, 0), -0.35)), L['scarf'], 0.03 * hh)
        f.add(Ellipsoid(k, A(0.14, 0.08, 0.1) * hh, Rc), L['scarf'], 0.03 * hh)
        for s in (1, -1):
            f.add(Sweep(spline([k, k + Rc @ A(s * 0.2, 0.05, -0.2) * hh, k + Rc @ A(s * 0.3, 0.02, -0.45) * hh], 8), A(0.08, 0.1, 0.09, 0.07, 0.06, 0.05, 0.05, 0.04) * hh, 0.015 * hh, [Rc @ A(0, 1, 0)] * 8), L['scarf'], 0.015 * hh)
    if sp.get('necklace'):
        Rc, Oc = fig.Rc, fig.Oc
        f.add(Torus(fig.N + Rc @ A(0, 0.12, -0.25) * hh, 0.38 * hh, 0.025 * hh, Rc @ rot((1, 0, 0), -0.55)), L['jewel'], 0.01 * hh)

def costume_tang(f, fig, sp, rng, hh):
    """唐服: long skirt to the feet, a robe with a crossed collar, long sleeves hanging to the knees, shoe tips"""
    Op = fig.Op; Rc, Oc = fig.Rc, fig.Oc
    zt = Op[2] + 0.45 * hh
    rows = skirt_rows(fig, zt, 0.03 * hh, extra=0.06, flare=0.32)
    cc = (rows[0][1], rows[0][2], 0)
    f.add(Displace(Loft(rows), fold_fn(cc, 15, 0.011 * hh, rng.uniform(0, 6)), 0.013 * hh), L['robe'], 0.02 * hh)
    rows2 = skirt_rows(fig, zt + 0.1 * hh, Op[2] - 1.2 * hh, extra=0.12, flare=0.18)
    def hem(th): return (Op[2] - 1.2 * hh + 0.3 * hh * np.clip(-np.sin(th), 0, 1) + 0.12 * hh * np.cos(2 * th) ** 2).astype(np.float32)
    f.add(Over(rows2, hem, fold_fn(cc, 10, 0.01 * hh)), L['robe2'], 0.01 * hh)
    f.add(Ellipsoid(Oc + Rc @ A(0, 0.02, 0.0) * hh, A(0.62, 0.48, 0.74) * hh, Rc), L['robe2'], 0.06 * hh)
    f.add(Ellipsoid(fig.W + A(0, 0.03, 0) * hh, A(0.56, 0.46, 0.56) * hh, fig.Rw), L['robe2'], 0.06 * hh)
    for s in (1, -1):
        pts = [fig.N + Rc @ A(s * 0.28, -0.05, 0.02) * hh, fig.N + Rc @ A(s * 0.25, 0.32, -0.15) * hh, Oc + Rc @ A(s * 0.04, 0.55, -0.2) * hh,
               Oc + Rc @ A(-s * 0.12, 0.54, -0.42) * hh]
        f.add(Sweep(spline(pts, 30), 0.065 * hh, 0.02 * hh, [Rc @ nrm(A(s * 0.25, 1, 0.3))] * 30), L['lining'], 0.01 * hh)
    if sp.get('armour_under'):
        for s in (1, -1):
            f.add(Ellipsoid(Oc + Rc @ A(s * 0.3, 0.6, 0.15) * hh, A(0.14, 0.05, 0.14) * hh, Rc), L['boss'], 0.01 * hh)
    f.add(Band(Op + A(0, 0.02, 0.45 * hh), 0.68 * hh, 0.55 * hh, 0.05 * hh, 0.06 * hh, fig.Rp), L['belt'], 0.01 * hh)
    fy = rows2[-1][2] + rows2[-1][4]
    f.add(Box(A(cc[0], fy + 0.04 * hh, (Op[2] + 0.45 * hh + 0.7 * hh) / 2), A(0.17 * hh, 0.022 * hh, (Op[2] + 0.45 * hh - 0.7 * hh) / 2), None, 0.02 * hh), L['lining'], 0.02 * hh)
    for nm, a in fig.arm.items():
        s = a['s']; S_, E, Wr = a['S'], a['E'], a['W']
        fore = nrm(Wr - E)
        f.add(RCone(S_, E, 0.22 * hh, 0.23 * hh), L['robe2'], 0.05 * hh)
        f.add(RCone(E, Wr - fore * 0.08 * hh, 0.23 * hh, 0.27 * hh), L['robe2'], 0.04 * hh)
        top = E + (Wr - E) * 0.55
        ln = sp.get('sleeve_len', 1.9)
        low = A(top[0] + s * 0.12 * hh, top[1] - 0.12 * hh, max(top[2] - ln * hh, 0.8 * hh))
        pts = spline([top, (top + low) / 2 + A(s * 0.05, -0.06, 0) * hh, low, low + A(s * 0.08, 0.05, 0.12) * hh], 14)
        out = nrm(A(s * 0.7, 1, 0))
        def folds(P, out=out): return (-0.004 * np.cos((P @ np.cross(out, (0, 0, 1))) / hh * 16.0)).astype(np.float32)
        sw_ = sp.get('sleeve_w', 1.0)
        f.add(Displace(Sweep(pts, np.interp(np.linspace(0, 1, len(pts)), [0, 0.7, 1], [0.15, 0.27, 0.22]) * hh * sw_, 0.05 * hh, [out] * len(pts)), folds, 0.005), L['robe2'], 0.07 * hh)
        f.add(Torus(Wr - fore * 0.04 * hh, 0.3 * hh, 0.03 * hh, frame(z=fore, x=(0, 0, 1) if abs(fore[2]) < 0.9 else (1, 0, 0))), L['lining'], 0.02 * hh)
    for nm, g in fig.leg.items():
        Ak = g['A']; fd = nrm(g['foot_dir'] * A(1, 1, 0))
        f.add(Ellipsoid(A(Ak[0], Ak[1], 0.1 * hh) + fd * 0.55 * hh, A(0.2, 0.3, 0.12) * hh, frame(y=fd, z=(0, 0, 1))), L['shoe'], 0.04 * hh)
        f.add(Ellipsoid(A(Ak[0], Ak[1], 0.18 * hh) + fd * 0.74 * hh, A(0.1, 0.1, 0.1) * hh, frame(y=fd, z=(0, 0, 1))), L['shoe'], 0.04 * hh)
    if sp.get('gold_skirt'):
        gold_patches(f, Offset(Loft(rows), 0.03), 0.03, sp['gold_skirt'], 7)
        gold_patches(f, Offset(Ellipsoid(Oc, A(0.8, 0.65, 0.9) * hh, Rc), 0.02), 0.03, sp['gold_skirt'], 8)

def costume_ascetic(f, fig, sp, rng, hh):
    """婆籔仙: a tattered wrap round the hips to below the knees"""
    Op = fig.Op
    zt = Op[2] + 0.3 * hh
    rows = skirt_rows(fig, zt, 1.35 * hh, extra=0.05, flare=0.25)
    cc = (rows[0][1], rows[0][2], 0)
    def hem(th):
        return (1.35 * hh + 0.45 * hh * np.abs(np.sin(3.5 * th + 0.4)) ** 3 + 0.2 * hh * np.abs(np.sin(7 * th)) + 0.3 * hh * np.clip(-np.sin(th), 0, 1)).astype(np.float32)
    f.add(Over(rows, hem, fold_fn(cc, 8, 0.016 * hh)), L['robe'], 0.02 * hh)
    rows2 = skirt_rows(fig, zt + 0.08 * hh, Op[2] - 0.35 * hh, extra=0.1, flare=0.2)
    def hem2(th): return (Op[2] - 0.35 * hh - 0.25 * hh * np.abs(np.sin(2.5 * th)) ** 2).astype(np.float32)
    f.add(Over(rows2, hem2, fold_fn(cc, 6, 0.012 * hh)), L['robe2'], 0.01 * hh)
    f.add(Band(Op + A(0, 0.02, 0.32 * hh), 0.6 * hh, 0.46 * hh, 0.04 * hh, 0.04 * hh, fig.Rp), L['belt'], 0.01 * hh)

def costume_hooded(f, fig, sp, rng, hh):
    """神母女: one long robe from the head to the feet, wide sleeves falling from the joined hands"""
    Op = fig.Op; Rc, Oc = fig.Rc, fig.Oc
    rows = skirt_rows(fig, Op[2] + 0.4 * hh, 0.02 * hh, extra=0.1, flare=0.35)
    cc = (rows[0][1], rows[0][2], 0)
    f.add(Displace(Loft(rows), fold_fn(cc, 11, 0.012 * hh, 1.0), 0.013 * hh), L['robe'], 0.02 * hh)
    f.add(Ellipsoid(Oc + Rc @ A(0, 0.0, 0.05) * hh, A(0.78, 0.6, 0.85) * hh, Rc), L['robe'], 0.08 * hh)
    f.add(Ellipsoid(fig.W + A(0, 0.02, 0) * hh, A(0.7, 0.56, 0.62) * hh, fig.Rw), L['robe'], 0.08 * hh)
    for nm, a in fig.arm.items():
        s = a['s']
        f.add(RCone(a['S'], a['E'], 0.3 * hh, 0.32 * hh), L['robe'], 0.05 * hh)
        f.add(RCone(a['E'], a['W'] - nrm(a['W'] - a['E']) * 0.1 * hh, 0.32 * hh, 0.36 * hh), L['robe'], 0.04 * hh)
        top = a['E'] + (a['W'] - a['E']) * 0.4
        low = A(top[0] + s * 0.12 * hh, top[1] + 0.05 * hh, 1.6 * hh)
        out = nrm(A(s * 0.7, 1, 0))
        f.add(Sweep(spline([top, (top + low) / 2 + A(s * 0.05, 0, 0) * hh, low], 12), np.linspace(0.2, 0.3, 12) * hh, 0.07 * hh, [out] * 12), L['robe'], 0.07 * hh)
    # the front opening of the robe: two edges down the front
    for s in (1, -1):
        pts = spline([fig.N + Rc @ A(s * 0.18, 0.2, -0.1) * hh, Oc + Rc @ A(s * 0.1, 0.62, -0.3) * hh, fig.W + A(s * 0.08, 0.6, -0.4) * hh, A(s * 0.1 * hh, 0.55 * hh, 0.3 * hh)], 24)
        f.add(Sweep(pts, 0.06 * hh, 0.02 * hh, [A(0, 1, 0)] * 24), L['robe2'], 0.01 * hh)

COSTUMES = {'armour': costume_armour, 'nio': costume_nio, 'bare': costume_bare, 'tang': costume_tang, 'ascetic': costume_ascetic, 'hooded': costume_hooded}

# ---------------------------------------------------------------------------------------------- heads & headgear
def topknot_flames(g, R, O, hh):
    """the Niō's knot with two flame-like tendrils rising from it"""
    P = lambda v: O + R @ (A(*v) * hh)
    g.add(Ellipsoid(P((0, -0.08, 0.6)), A(0.13, 0.13, 0.12) * hh, R), L['hair'], 0.04 * hh)
    for s in (1, -1):
        pts = [P((s * 0.04, -0.08, 0.66)), P((s * 0.12, -0.06, 0.85)), P((s * 0.05, -0.05, 1.0)), P((s * 0.13, -0.04, 1.15)), P((s * 0.08, -0.04, 1.3)), P((s * 0.15, -0.03, 1.42))]
        g.add(Tube(spline(pts, 18), np.linspace(0.03, 0.006, 18) * hh), L['hair'], 0.01 * hh)

def flame_hair(g, R, O, hh, seed=0):
    """炎髪: the hair rising round the head in curling locks of flame (散支大将, 伊鉢羅, 毘舎闍)"""
    rng = np.random.default_rng(seed)
    P = lambda v: O + R @ (A(*v) * hh)
    g.add(Inter([Ellipsoid(P((0, -0.05, 0.1)), A(0.39, 0.46, 0.46) * hh, R), Plane(P((0, 0.37, 0.2)), R @ nrm(A(0, 0.5, -0.72)))], 0.02 * hh), L['hair'], 0.02 * hh)
    for i in range(13):
        a = -1.4 + 2.8 * i / 12
        base = P((0.33 * math.sin(a), -0.05 + 0.36 * math.cos(a), 0.3 + 0.06 * math.cos(a)))
        out = R @ nrm(A(math.sin(a) * 0.5, math.cos(a) * 0.35, 1.0))
        side = R @ nrm(A(math.cos(a), -math.sin(a), 0))
        L_ = (0.3 + 0.12 * math.cos(a)) * rng.uniform(0.85, 1.1)
        curl = 1 if (i % 2) else -1
        pts = [base + out * L_ * hh * t + side * curl * 0.08 * hh * math.sin(t * math.pi * 1.2) for t in np.linspace(0, 1, 7)]
        tip = pts[-1]
        pts += [tip + (side * curl * math.cos(th) + out * math.sin(th)) * 0.05 * hh for th in np.linspace(0.6, 3.2, 4)]
        g.add(Tube(pts, np.r_[np.linspace(0.075, 0.03, 7), np.linspace(0.025, 0.012, 4)] * hh), L['hair'], 0.03 * hh)

def lion_helmet(g, R, O, hh):
    """乾闥婆's lion helmet: a cap with the lion's brow and mane points flaring up"""
    P = lambda v: O + R @ (A(*v) * hh)
    g.add(Inter([Ellipsoid(P((0, -0.04, 0.15)), A(0.42, 0.5, 0.48) * hh, R), Plane(P((0, 0.35, 0.2)), R @ nrm(A(0, 0.35, -1)))], 0.02 * hh), L['cap'], 0.01 * hh)
    g.add(Tube([P((-0.3, 0.32, 0.25)), P((0, 0.42, 0.3)), P((0.3, 0.32, 0.25))], A(0.05, 0.06, 0.05) * hh), L['cap'], 0.03 * hh)      # brow ridge of the lion
    for s in (1, -1):
        g.add(Sphere(P((s * 0.13, 0.42, 0.36)), 0.045 * hh), L['cap'], 0.02 * hh)
    for k in range(7):
        a = -1.2 + 0.4 * k
        b = P((0.32 * math.sin(a), 0.1 * math.cos(a) - 0.05, 0.42))
        g.add(Tube([b, b + R @ A(0.12 * math.sin(a), 0.06, 0.2) * hh, b + R @ A(0.2 * math.sin(a), -0.02, 0.35) * hh], A(0.09, 0.06, 0.012) * hh), L['cap'], 0.03 * hh)
    for s in (1, -1):    # ear flaps
        g.add(Ellipsoid(P((s * 0.4, -0.05, -0.05)), A(0.05, 0.16, 0.22) * hh, R @ rot((0, 1, 0), s * 0.3)), L['cap'], 0.03 * hh)

def pointed_cap(g, R, O, hh):
    """摩睺羅's pointed cap with a lion ruff below the chin"""
    P = lambda v: O + R @ (A(*v) * hh)
    g.add(Inter([Ellipsoid(P((0, -0.05, 0.16)), A(0.42, 0.48, 0.5) * hh, R), Plane(P((0, 0.35, 0.18)), R @ nrm(A(0, 0.35, -1)))], 0.02 * hh), L['cap'], 0.01 * hh)
    g.add(RCone(P((0, -0.05, 0.5)), P((0.0, 0.02, 0.9)), 0.22 * hh, 0.02 * hh), L['cap'], 0.05 * hh)
    for s in (1, -1):
        g.add(Ellipsoid(P((s * 0.36, -0.05, 0.25)), A(0.06, 0.18, 0.12) * hh, R @ rot((0, 1, 0), -s * 0.7)), L['cap'], 0.03 * hh)

def wing_crown(g, R, O, hh):
    """満善車鉢's crown with upswept wing-like flaps"""
    crown(g, R, O, hh, 'flame')
    P = lambda v: O + R @ (A(*v) * hh)
    for s in (1, -1):
        g.add(Sweep([P((s * 0.3, 0.05, 0.3)), P((s * 0.48, 0.0, 0.45)), P((s * 0.55, -0.05, 0.62))], A(0.1, 0.09, 0.03) * hh, 0.015 * hh, [R @ A(0, 1, 0)] * 3), L['crown'], 0.015 * hh)

def bird_crest(g, R, O, hh):
    """迦楼羅: a topknot with a crown band above the bird face"""
    P = lambda v: O + R @ (A(*v) * hh)
    g.add(Ellipsoid(P((0, -0.1, 0.5)), A(0.14, 0.14, 0.16) * hh, R), L['hair'], 0.05 * hh)
    g.add(Band(P((0, -0.05, 0.32)), 0.36 * hh, 0.42 * hh, 0.015 * hh, 0.04 * hh, R), L['crown'], 0.004 * hh)

def dragon_crest(g, R, O, hh):
    """難陀龍王: a dragon rising from behind the crown, its horned head reared above"""
    crown(g, R, O, hh, 'disc')
    P = lambda v: O + R @ (A(*v) * hh)
    pts = [P((0.2, -0.3, 0.25)), P((0.28, -0.25, 0.55)), P((0.05, -0.15, 0.85)), P((-0.1, -0.05, 1.05)), P((0.0, 0.08, 1.2))]
    dragon_body(g, pts, 0.07 * hh)
    dragon_head(g, P((0.02, 0.15, 1.28)), R @ nrm(A(0.1, 1.0, 0.25)), R[:, 2], 0.2 * hh, jaw=0.5)

def snake_crown(g, R, O, hh, n=5):
    crown(g, R, O, hh, 'disc')
    for k in range(n):
        a = math.pi / 2 + (k - (n - 1) / 2) * 0.42
        b = O + R @ A(0.24 * math.cos(a), 0.24 * math.sin(a) - 0.1, 0.42) * hh
        pts = [b, b + R @ A(0.12 * math.cos(a), 0.04, 0.3) * hh, b + R @ A(0.2 * math.cos(a), 0.1 + 0.02 * k, 0.55) * hh, b + R @ A(0.22 * math.cos(a), 0.28, 0.62) * hh]
        snake_tube(g, pts, 0.045 * hh)

def band(g, R, O, hh):
    P = lambda v: O + R @ (A(*v) * hh)
    g.add(Band(P((0, -0.05, 0.26)), 0.358 * hh, 0.422 * hh, 0.013 * hh, 0.035 * hh, R @ rot((1, 0, 0), -0.1)), L['crown'], 0.004 * hh)
    g.add(Ellipsoid(P((0, 0.37, 0.3)), A(0.06, 0.02, 0.05) * hh, R), L['crown'], 0.006 * hh)

HATS = {'band': band, 'crown': lambda g, R, O, hh: crown(g, R, O, hh, 'flame'), 'crown_tall': lambda g, R, O, hh: crown(g, R, O, hh, 'tall'),
        'crown_disc': lambda g, R, O, hh: crown(g, R, O, hh, 'disc'), 'helmet': helmet, 'lion': lion_helmet, 'pointed': pointed_cap,
        'wing': wing_crown, 'bird': bird_crest, 'dragon': dragon_crest, 'snakes': snake_crown, 'lionhead': lion_head_cap, 'none': lambda *a: None}

# ---------------------------------------------------------------------------------------------- traced joints
PHOTO2X = '/home/kazu/work/kyoto-assets/refs/sanjusangendo/official/nijuhachibushu/2x/img{:02d}.jpg'

def apply_trace(fig, sp, m):
    """set the skeleton from points read off the 2x front photo (928x1340): each joint (px, py[, depth m]); the scale
    from the figure height between 'top' (top of the head / topknot, py) and 'sole' (py).  Returns the head unit."""
    t = sp['trace']
    K = (t['sole'] - t['top']) / sp['h']
    CX = t.get('cx', 464.0); SOLE = t['sole']
    def P(key, dflt_y=0.0):
        v = t[key]; y = v[2] if len(v) > 2 else dflt_y
        return A((CX - v[0]) / K, y, (SOLE - v[1]) / K)
    hh = t['hh_px'] / K
    fig.hh = hh; fig.hhd = hh; fig.hs = 1.0
    S_R, S_L = P('S_R', -0.02), P('S_L', -0.02)
    E_R, E_L = P('E_R', 0.0), P('E_L', 0.0)
    W_R, W_L = P('W_R', 0.08), P('W_L', 0.08)
    H_R, H_L = P('H_R'), P('H_L')
    K_R, K_L = P('K_R', 0.06), P('K_L', 0.06)
    A_R, A_L = P('A_R', 0.02), P('A_L', 0.02)
    fig.Rc = frame(x=nrm(S_R - S_L), z=nrm(np.asarray(t.get('chest_up', (0.0, 0.08, 1.0)), float)))
    fig.Oc = (S_R + S_L) / 2 - fig.Rc @ A(0, -0.1 * hh, 0.5 * hh)
    fig.N = fig.Oc + fig.Rc @ A(0, -0.08 * hh, 0.72 * hh)
    fig.Op = (H_R + H_L) / 2 + A(0, 0, 0.22 * hh)
    fig.Rp = frame(x=nrm(H_R - H_L), z=(0, 0, 1))
    fig.W = (fig.Op + fig.Oc) / 2 + A(0, 0.02 * hh, 0.0)
    fig.Rw = frame(x=nrm(fig.Rp[:, 0] + fig.Rc[:, 0]), z=nrm(fig.Rc[:, 2] + A(0, 0, 1)))
    fig.Oh = P('head', -0.0)
    tr_ = t.get('head_rot', (0, 0, 0))
    fig.Rh = rot((0, 0, 1), tr_[2]) @ rot((0, 1, 0), tr_[1]) @ rot((1, 0, 0), tr_[0])
    fig.arm = {'r': dict(S=S_R, E=E_R, W=W_R, s=1), 'l': dict(S=S_L, E=E_L, W=W_L, s=-1)}
    fd_r = np.asarray(t.get('foot_r', (0.45, 1, 0)), float); fd_l = np.asarray(t.get('foot_l', (-0.45, 1, 0)), float)
    fig.leg = {'r': dict(H=H_R, K=K_R, A=A_R, s=1, foot_dir=fd_r), 'l': dict(H=H_L, K=K_L, A=A_L, s=-1, foot_dir=fd_l)}
    m.photo = PHOTO2X.format(PHOTO_NO.index(sid(sp['name'])) + 1)
    m.trace = (K, CX, SOLE, 928, 1340)
    m.check_views = ['q34', 'trace']
    return hh

# ---------------------------------------------------------------------------------------------- the generator
def guardian(sp):
    from .statues_build import Model
    name = sp['name']; gid = sid(name)
    rng = np.random.default_rng(zlib.crc32(name.encode()) % 10000)
    h = sp['h']; kind = sp.get('kind', 'guard'); cost = sp.get('costume', 'armour')
    heads = sp.get('heads', {'armour': 7.5, 'nio': 7.0, 'tang': 7.4, 'bare': 7.3, 'ascetic': 7.0, 'hooded': 7.0}.get(sp.get('costume', 'armour'), 7.3))
    hh = h / (heads + sp.get('top', 0.32))
    H = heads * hh
    rock_h = sp.get('rock_h', 0.2); plinth = sp.get('plinth', 0.1)
    m = Model(gid, sp['jp'], f"{name} ({sp.get('en', '')})", budget=(80000, 16000, 2400), lift=rock_h + plinth, figure_h=h)
    m.pal = W.wood_palette(**sp.get('col', {}))
    m.shade = True
    m.weather = W.wood_c0fn(zlib.crc32(name.encode()) % 997, 1.0)
    m.slot = dict(slot='attendants', slot_name=name, slot_pos=sp.get('pos'))
    if gid in PHOTO_NO: m.photo = PHOTO.format(PHOTO_NO.index(gid) + 1)
    U = lambda *v: A(*v) * hh
    pose = dict(sp.get('pose', {}))
    pose.setdefault('neck', 0.12)
    pose.setdefault('leg_len', (heads - 3.5) * 1.004)
    crouch = pose.pop('crouch', 0.0)
    pose['pelvis_z'] = (heads - 3.0 - crouch) * hh
    dz = heads - 6.6 - crouch             # hand targets were authored for a 6.6-head upright body: keep them on the torso
    for k in ('hand_r', 'hand_l'):
        if k in pose: v = list(pose[k]); v[2] += dz; pose[k] = U(*v)
    for k in ('foot_r', 'foot_l'):
        if k in pose: pose[k] = U(*pose[k])
    for k in ('foot_r', 'foot_l'):
        if k not in pose: pose[k] = U((0.42 if k == 'foot_r' else -0.42), 0.15, 0.28)
    fig = Bd.Fig(H, heads, kind if kind in ('guard', 'nio', 'deva', 'female', 'ascetic', 'bodhi') else 'guard', **pose)
    if 'musc' in sp: fig.musc = sp['musc']
    if 'trace' in sp: hh = apply_trace(fig, sp, m)
    O, R = fig.Oh, fig.Rh
    f = Field('body')
    bare_legs = cost in ('nio', 'bare', 'ascetic')
    legs = fig.leg
    if not bare_legs: fig.leg = {}
    Bd.add_body(f, fig, skin='skin')
    fig.leg = legs
    if not bare_legs:
        for nm, g in fig.leg.items(): Bd.add_leg(f, fig, g, L['skin'], foot=False)
    if 'trace' in sp:      # the traced torso is longer than the generator's: bridge chest and pelvis
        tl = np.linalg.norm(fig.Oc - fig.Op)
        f.add(RCone(fig.Oc - fig.Rc[:, 2] * 0.2 * hh, fig.Op + A(0, 0, 0.1 * hh), (0.6 + 0.08 * max(fig.musc, 0)) * hh, 0.58 * hh), L['skin'], 0.15 * hh)
        if cost == 'armour':
            f.add(Inter([Shell(Ellipsoid(fig.W + A(0, 0.02 * hh, 0), A(0.7, 0.56, tl / hh * 0.45) * hh, fig.Rw), 0.03 * hh),
                         Box(fig.W + A(0, 0.3 * hh, 0), A(0.66, 0.4, tl / hh * 0.3) * hh, fig.Rw, 0.1 * hh)], 0.01 * hh), L['armour2'], 0.015 * hh)
    if kind == 'nio': nio_relief(f, fig, hh)
    if kind == 'ascetic': emaciated(f, fig, hh)
    COSTUMES[cost](f, fig, sp, rng, hh)
    extra_arms = []
    tex = sp.get('trace', {}).get('extra')
    for xi, (s, tgt, pole, back) in enumerate(sp.get('extra_arms', [])):
        S0 = fig.arm['r' if s > 0 else 'l']['S'] + A(-s * 0.05, -0.08, -0.12) * hh
        if tex:
            t_ = sp['trace']; K_ = (t_['sole'] - t_['top']) / sp['h']; CX_ = t_.get('cx', 464.0)
            pt = lambda v: A((CX_ - v[0]) / K_, v[2] if len(v) > 2 else 0.0, (t_['sole'] - v[1]) / K_)
            E, Wr = pt(tex[xi][1]), pt(tex[xi][2])
        else:
            E, Wr = Bd.ik2(S0, U(tgt[0], tgt[1], tgt[2] + dz), 1.2 * hh, 1.02 * hh, pole)
        a = dict(S=S0, E=E, W=Wr, s=s); extra_arms.append((a, back))
        Bd.add_arm(f, fig, a, L['skin'], deltoid=False)
        ax = nrm(Wr - E)
        f.add(Torus(Wr - ax * 0.03 * hh, 0.17 * hh, 0.025 * hh, frame(z=ax, x=(0, 0, 1) if abs(ax[2]) < 0.9 else (1, 0, 0))), L['jewel'], 0.01 * hh)
    if sp.get('wings'):
        for s in (1, -1):
            feather_wing(f, fig.Oc + fig.Rc @ A(s * 0.3, -0.5, 0.3) * hh, s, hh)
    for it in sp.get('field_items', []):
        it(f, fig, U, hh)
    m.field(f, 0.0024, 34.0, lods=(0, 1))
    # ---- head
    g = Field('head')
    g.add(Inter([RCone(fig.N - fig.Rc @ A(0, 0, 0.15 * hh), O + R @ A(0, -0.06 * hh, -0.25 * hh), (0.3 + 0.06 * max(fig.musc, 0)) * hh, 0.27 * hh),
                 Plane(O + R @ A(0, 0, -0.62 * hh), -(R[:, 2]))]), L['skin'], 0.0)
    hd = dict(sp.get('head', {}))
    hair = hd.pop('hair', 'bun'); hat = hd.pop('hat', 'crown'); faces = hd.pop('faces', 1); split = hd.pop('split', False)
    eyes3 = hd.pop('eyes3', False)
    hd.setdefault('eyes', 'crystal'); hd.setdefault('urna', False)
    Bd.add_head(g, R, O, hh, **hd)
    if faces == 3:
        for s in (1, -1):
            R2 = R @ rot((0, 0, 1), s * 1.35); O2 = O + R @ A(s * 0.3, -0.18, -0.02) * hh
            hd2 = dict(hd); hd2['mouth'] = 'closed'; hd2['fierce'] = 0.5 if s > 0 else 0.8
            Bd.add_head(g, R2, O2, hh * 0.86, **hd2)
            band(g, R2, O2, hh * 0.86)
    if split:
        g.sub(Ellipsoid(O + R @ A(0, 0.42, -0.05) * hh, A(0.1, 0.15, 0.36) * hh, R), 0.02 * hh, lab=L['mouth'])
        Bd.add_head(g, R, O + R @ A(0, 0.06, -0.06) * hh, hh * 0.5, style='fierce', fierce=1.0, mouth='open', ears=None, eyes='crystal', urna=False)
    if eyes3:
        eye_extra(g, R, O, hh, (0, 0.39, 0.17))
    if hair == 'flames': flame_hair(g, R, O, hh, seed=int(rng.integers(0, 99)))
    elif hair == 'nio': Bd.add_hair(g, R, O, hh, 'short'); topknot_flames(g, R, O, hh)
    elif hair != 'none': Bd.add_hair(g, R, O, hh, hair, seed=int(rng.integers(0, 99)))
    HATS[hat](g, R, O, hh)
    m.field(g, 0.00085, 38.0, lods=(0, 1))
    # ---- rock base (on the plinth) + halo
    bf = Field('rock')
    pads = []
    for nm, g_ in fig.leg.items():
        Ak = g_['A']; fd = nrm(g_['foot_dir'] * A(1, 1, 0))
        c_ = A(Ak[0], Ak[1], 0) + fd * 0.25 * hh
        pads.append((c_[0], c_[1], Ak[2] - 0.26 * hh, 0.42 * hh))
    rock_w = sp.get('rock_w', 0.66); rock_d = sp.get('rock_d', 0.52)
    W.rock(bf, rng, rock_w, rock_d, rock_h, pads=pads, z_top=0.0)
    m.field(bf, 0.004, 6.0, lods=(0, 1))
    if sp.get('halo', True):
        hf = Field('halo')
        hc = O + R @ A(0, -0.6, 0.18) * hh
        W.halo(hf, hc, frame(x=(1, 0, 0), y=(0, 1, 0)), sp.get('halo_r', 1.18) * hh, 'halo',
               flames=sp.get('halo_flames', ((90, 1.0), (32, 0.62), (148, 0.62))), tube=0.028 * hh, rod_to=fig.Oc + A(0, -0.62 * hh, -0.6 * hh), seed=0)
        if sp.get('halo_gold'): gold_patches(hf, Box(hc, A(0.6, 0.2, 0.6), None, 0.0), 0.03, sp['halo_gold'], 11)
        m.field(hf, 0.0018, 8.0, lods=(0, 1))
    # ---- LOD2: one coarse field
    f2 = Field('lod2')
    Bd.add_body(f2, fig, skin='skin')
    rowsL = skirt_rows(fig, fig.Op[2] + 0.3 * hh, 0.3 * hh if cost not in ('tang', 'hooded') else 0.02, extra=0.08, flare=0.3)
    f2.add(Loft(rowsL), L['robe'], 0.03)
    f2.add(Ellipsoid(O + R @ A(0, 0, 0.1) * hh, A(0.45, 0.5, 0.62) * hh, R), L['skin'], 0.03)
    f2.add(Box(A(0, 0, -rock_h / 2), A(rock_w / 2, rock_d / 2, rock_h / 2), None, 0.04), L['rock'], 0.02)
    if sp.get('halo', True):
        f2.add(Torus(O + R @ A(0, -0.6, 0.18) * hh, 1.18 * hh, 0.04 * hh, frame(z=(0, 1, 0), x=(1, 0, 0))), L['halo'], 0.0)
    m.field(f2, 0.009, 30.0, lods=(2,))
    # ---- hands
    hands = sp.get('hands', {})
    groups = {}; frames = {}
    allarms = [(nm, a, None) for nm, a in fig.arm.items()] + [(f'x{i}', a, back) for i, (a, back) in enumerate(extra_arms)]
    for nm, a, back_x in allarms:
        s = a['s']; hs = hands.get(nm, {})
        pose_h = hs.get('pose', 'relaxed')
        ax = nrm(a['W'] - a['E'])
        if 'grip_axis' in hs:
            g_ = nrm(np.asarray(hs['grip_axis'], float))
            x_ = nrm(ax - g_ * (ax @ g_)) if abs(ax @ g_) < 0.98 else nrm(np.cross(g_, A(0, 0, 1)))
            if 'fdir' in hs: x_ = nrm(np.asarray(hs['fdir'], float) - g_ * (np.asarray(hs['fdir'], float) @ g_))
            xf = Bd.hand_xf(a['W'], x_, np.cross(x_, g_ * s), s)
        else:
            fd = nrm(np.asarray(hs.get('fdir', ax), float))
            back = np.asarray(hs.get('back', back_x if back_x is not None else (s, -0.3, 0.2)), float)
            xf = Bd.hand_xf(a['W'], fd, back, s)
        frames[nm] = (xf, hs)
        groups.setdefault(pose_h, []).append(xf)
    Lh = 0.68 * hh
    for pose_h, xfs in groups.items():
        m.instance('hand_' + pose_h, (lambda p=pose_h: (Bd.hand_field(p, Lh, musc=max(fig.musc, 0) * 0.6, lab='skin'), Lh / 140)), 3.4, xfs)
    # ---- explicit parts: plinth, held things, scarves
    def xm_fn(q):
        xm = X.XM()
        pw = max(rock_w, rock_d) + 0.16
        X.octa_plinth(xm, (0, 0, -rock_h - plinth), pw / 2 / math.cos(math.pi / 4), [(1.0, 0.0, plinth), (1.04, 0.0, 0.025)], 'base', sides=4, phase=math.pi / 4)
        for (nm, (xf, hs)) in frames.items():
            for it in hs.get('items', []): it(xm, xf, q, hh)
        for it in sp.get('items', []): it(xm, fig, q, hh)
        if q > 0.2:
            sc = sp.get('scarf', 'sides')
            if sc == 'sides':
                for s in (1, -1):
                    scarf_side(xm, fig, s, q, hh, out=sp.get('scarf_out', 0.25) * (1 if s > 0 else sp.get('scarf_asym', 1.0)), back=sp.get('scarf_back', 0.15),
                               z_end=sp.get('scarf_end', 0.5) * hh, end_curl=1.0)
            elif callable(sc):
                sc(xm, fig, q, hh)
        return xm
    m.xm_fn = xm_fn
    m.closeups = [('face', m.lift + O[2] + 0.02, 0.85, 0.3)]
    return m

# ---------------------------------------------------------------------------------------------- Niō scarves
def nio_scarf(kind):
    """the long 天衣 of the Niō: a wide band arching over and behind the head from the hands, falling in front of the
    body and hanging to the knees / rock"""
    def it(xm, fig, q, hh):
        O = fig.Oh; n = 44 if q > 0.6 else 16
        if kind == 'a':     # 那羅延堅固: from the raised left fist over the head, down the right side of the chest to the knee
            fist = fig.arm['l']['W']
            ctrl = [fist + A(0, 0.02, -0.25) * hh, fist + A(0.05, -0.05, 0.25) * hh, O + A(-0.2, -0.35, 0.95) * hh, O + A(0.35, -0.3, 1.0) * hh,
                    O + A(0.65, -0.1, 0.3) * hh, fig.arm['r']['S'] + A(-0.15, 0.25, -0.2) * hh, fig.Oc + A(0.35, 0.65, -0.6) * hh,
                    fig.Op + A(0.6, 0.55, 0.0) * hh, fig.Op + A(0.8, 0.4, -1.2) * hh, A(fig.Op[0] + 1.0 * hh, fig.Op[1] + 0.3 * hh, 0.9 * hh)]
            ctrl2 = [fist + A(0.0, -0.02, -0.3) * hh, fist + A(0.0, 0.05, -0.8) * hh, fig.Oc + A(-0.9, 0.3, -0.2) * hh, fig.Op + A(-0.8, 0.3, -0.5) * hh, A(fig.Op[0] - 1.1 * hh, fig.Op[1] + 0.2 * hh, 1.0 * hh)]
        else:               # 密迹金剛士: a loop over the head from the left shoulder to the right hip, held at the left hip
            hip = fig.arm['l']['W']
            ctrl = [hip + A(0.05, 0.05, -0.15) * hh, fig.arm['l']['S'] + A(0.0, 0.1, 0.2) * hh, O + A(-0.45, -0.3, 0.75) * hh, O + A(0.05, -0.4, 1.05) * hh,
                    O + A(0.5, -0.35, 0.65) * hh, fig.arm['r']['S'] + A(0.2, -0.2, 0.1) * hh, fig.Oc + A(0.85, -0.1, -0.7) * hh,
                    fig.Op + A(0.95, 0.1, -0.6) * hh, A(fig.Op[0] + 1.2 * hh, fig.Op[1] + 0.2 * hh, 1.0 * hh)]
            ctrl2 = [hip + A(0.0, 0.05, -0.2) * hh, hip + A(-0.2, 0.15, -0.9) * hh, fig.Op + A(-1.1, 0.3, -1.0) * hh, A(fig.Op[0] - 1.25 * hh, fig.Op[1] + 0.25 * hh, 1.0 * hh)]
        for cc, wd in ((ctrl, 0.2), (ctrl2, 0.17)):
            pts = spline(cc, n)
            ups = []
            for k, p in enumerate(pts):
                o = nrm(A(p[0] - fig.Oc[0], p[1] - fig.Oc[1], (p[2] - fig.Oc[2]) * 0.3))
                ups.append(nrm(o + A(0, 0, 0.2 * math.sin(k * 0.25))))
            X.ribbon(xm, pts, np.full(len(pts), wd * hh) * np.r_[np.linspace(0.6, 1.0, 4), np.ones(len(pts) - 4)][:len(pts)], 0.012 * hh, ups, 'scarf')
    return it

# ---------------------------------------------------------------------------------------------- specs (from the photos; x = statue's right = viewer's LEFT)
P_ARM = dict(foot_r=(0.95, 0.15, 0.28), foot_l=(-0.9, 0.32, 0.28), footdir_r=(0.5, 1, 0), footdir_l=(-0.45, 1, 0), crouch=0.22,
             knee_r=(0.6, 1, 0), knee_l=(-0.6, 1, 0), hip_shift=(0.12, 0), pelvis_rot=(0, 0.07, -0.12), chest_rot=(0.03, -0.06, 0.14))
P_LUNGE = dict(P_ARM, foot_r=(1.25, 0.1, 0.28), foot_l=(-1.2, 0.35, 0.28), crouch=0.5, hip_shift=(0.18, 0), pelvis_rot=(0, 0.1, -0.15), chest_rot=(0.05, -0.08, 0.18))

def Pl(**kw):
    p = dict(P_LUNGE); p.update(kw); return p

def Pz(**kw):
    p = dict(P_ARM); p.update(kw); return p

def trident(length_down=1.05, length_up=1.25, banner=False):
    base = pole(length_down, length_up, 'halberd', r=0.012)
    def it(xm, xf, q, hh):
        base(xm, xf, q, hh)
        if banner and q > 0.3:
            R, t = xf; ax = R[:, 1]; x_ = R[:, 0]
            c = t + R @ (A(0.5, 0.0, -0.1) * 0.7 * hh) + ax * (length_up - 0.15)
            pts = [c + ax * (-0.25 * u) + x_ * (0.02 + 0.06 * u) - A(0, 0, 0.0) for u in np.linspace(0, 1, 8)]
            X.ribbon(xm, pts, np.linspace(0.05, 0.035, 8), 0.004, A(0, 1, 0), 'weapon')
    return it

def long_sword_down():
    """提頭頼吒王: the long sword held by its hilt at the waist, the point on the rock"""
    def it(xm, xf, q, hh):
        R, t = xf
        c = t + R @ (A(0.5, 0.0, -0.1) * 0.7 * hh)
        X.tube(xm, [c + A(0, 0, 0.1), c - A(0, 0, 0.05)], 0.015, 6, 'rod')
        X.tube(xm, [c - A(0, 0, 0.05), c - A(0, 0, 0.065)], 0.045, 6, 'weapon')
        tip = A(c[0] + 0.03, c[1] + 0.05, 0.0)
        bl = [c - A(0, 0, 0.065) + (tip - (c - A(0, 0, 0.065))) * u for u in np.linspace(0, 1, 9)]
        X.ribbon(xm, bl, np.r_[np.full(7, 0.024), 0.016, 0.002], 0.006, A(0, 1, 0), 'weapon')
    return it

def short_sword_h():
    def it(xm, xf, q, hh):
        R, t = xf; ax = R[:, 1]
        c = t + R @ (A(0.5, 0.0, -0.1) * 0.7 * hh)
        X.tube(xm, [c - ax * 0.06, c + ax * 0.06], 0.014, 6, 'rod')
        bl = [c + ax * (0.07 + 0.35 * k / 8) for k in range(9)]
        X.ribbon(xm, bl, np.r_[np.full(7, 0.02), 0.014, 0.002], 0.005, R[:, 0], 'weapon')
    return it

def scroll():
    def it(xm, xf, q, hh):
        R, t = xf; ax = R[:, 1]
        c = t + R @ (A(0.45, 0.0, -0.12) * 0.7 * hh)
        X.tube(xm, [c - ax * 0.09, c + ax * 0.13], 0.022, 8 if q > 0.5 else 4, 'attr2')
    return it

def wheel_small():
    def it(xm, xf, q, hh):
        R, t = xf
        X.attribute(xm, 'wheel', R, t + R @ (A(0.4, 0.0, -0.12) * 0.7 * hh), 0.3, 'weapon', q)
    return it

def bow_held():
    def it(xm, fig, q, hh):
        a, b = fig.arm['r']['W'], fig.arm['l']['W']
        c = (a + b) / 2 + A(0, 0.1, 0.0)
        pts = [c + A(0.32 * math.sin(t), 0.06 * (math.cos(t) - 1) - 0.0, 0.0) + A(0, 0.1 * math.cos(t), 0) for t in np.linspace(-1.3, 1.3, 11)]
        X.tube(xm, pts, 0.011, 6 if q > 0.5 else 4, 'rod')
        X.tube(xm, [pts[0], pts[-1]], 0.003, 3, 'rod', caps=False)
        X.tube(xm, [c + A(-0.2, -0.02, 0.02), c + A(0.3, 0.02, 0.04)], 0.006, 4, 'rod')
    return it

def staff_jewel():
    """大弁功徳天's staff (a long wand with a gilded finial)"""
    def it(xm, xf, q, hh):
        R, t = xf; ax = R[:, 1]
        c = t + R @ (A(0.5, 0.0, -0.1) * 0.7 * hh)
        X.tube(xm, [c - ax * 0.45, c + ax * 0.55], 0.008, 6 if q > 0.5 else 3, 'gold')
        if q > 0.3:
            tp = c + ax * 0.55
            th_ = np.linspace(0, 2 * math.pi, 17)
            Rr = frame(z=ax, x=R[:, 0])
            X.tube(xm, [tp + Rr @ A(0.035 * math.sin(a_), 0, 0.04 + 0.035 * math.cos(a_)) for a_ in th_], 0.004, 4, 'gold', caps=False)
    return it

def jewel_flame():
    def it(xm, xf, q, hh):
        R, t = xf
        X.attribute(xm, 'jewel', R, t + R @ (A(0.35, 0, -0.15) * 0.7 * hh), 0.13, 'gold', q)
    return it

def vase_small():
    def it(xm, xf, q, hh):
        R, t = xf
        X.attribute(xm, 'vase', R, t + R @ (A(0.35, 0, -0.15) * 0.7 * hh), 0.12, 'attr2', q)
    return it

def drum_small(f, fig, U, hh):
    """乾闥婆's hourglass drum (羯鼓) carried across the belly, the left hand on one head"""
    b = fig.arm['l']['W']
    c = fig.W + A(0.02, 0.5 * fig.hh, 0.05)
    d = nrm(A(1, 0.12, 0.0))
    for e in (-1, 1):
        f.add(Cyl(c + d * e * 0.1, c + d * e * 0.125, 0.085, 0.006), L['drum'], 0.0)
        f.add(RCone(c, c + d * e * 0.105, 0.035, 0.07), L['attr2'], 0.008)
        f.add(Torus(c + d * e * 0.112, 0.085, 0.007, frame(z=d, x=(0, 0, 1))), L['gold'], 0.002)
    f.add(Torus(c, 0.04, 0.008, frame(z=d, x=(0, 0, 1))), L['gold'], 0.003)

def snake_at_shoulder(f, fig, U, hh):
    b = fig.arm['l']['W']
    snake_tube(f, [b + A(0.0, 0.02, -0.25), b + A(0.02, 0.05, -0.05), b + A(-0.02, 0.06, 0.1), b + A(0.05, 0.08, 0.2), b + A(0.02, 0.13, 0.27)], 0.018)

SPECS = [
    # 01 那羅延堅固: Niō a-gyō, bare chested, mouth open; right hand down at the hip, palm open; left fist raised at the head
    dict(name='Narayana-kengo', jp='那羅延堅固', en='Nio, a-gyo', h=1.67, kind='nio', costume='nio', musc=1.0, halo=False,
         rock_h=0.14, plinth=0.13, rock_w=0.7, rock_d=0.55, hem_side=1, flap_side=1, scarf=nio_scarf('a'),
         pose=dict(foot_r=(0.6, 0.15, 0.28), foot_l=(-0.48, 0.25, 0.28), hip_shift=(-0.1, 0), pelvis_rot=(0.0, -0.06, 0.12), chest_rot=(0.05, 0.1, -0.15),
                   head_rot=(0.15, 0.1, 0.35), hand_r=(1.25, 0.55, 3.25), elbow_r=(1, -0.3, 0.2), hand_l=(-1.05, 0.0, 6.2), elbow_l=(-1, -0.2, 0.3)),
         head=dict(style='fierce', fierce=1.0, mouth='open', ears='normal', hair='nio', hat='none'),
         hands=dict(r=dict(pose='spread', fdir=(0.3, 0.2, -1), back=(0.4, -1, 0.2)), l=dict(pose='fist', fdir=(0.4, 0, 0.6), back=(0, -1, 0)))),
    # 02 難陀龍王: armoured, a long tunic, a dragon held up in both hands, a dragon on the crown
    dict(name='Nanda-ryuo', jp='難陀龍王', en='Dragon King Nanda', h=1.60, rock_h=0.2, apron=1.6,
         pose=Pz(head_rot=(0.05, 0, 0.12), hand_r=(0.5, 0.85, 4.85), elbow_r=(1, -0.2, -0.8), hand_l=(-0.4, 0.85, 3.55), elbow_l=(-1, -0.3, -0.6)),
         head=dict(style='fierce', fierce=0.55, mouth='closed', ears='normal', hair='bun', hat='dragon'),
         hands=dict(r=dict(pose='grip', grip_axis=(0.4, 0.2, 1)), l=dict(pose='grip', grip_axis=(0.5, 0.3, 1))),
         field_items=[dragon_held], gold_apron=0.15),
    # 03 摩睺羅: a biwa held across the body, its neck to the statue's left; a pointed cap; on a tall rock
    dict(name='Magora', jp='摩睺羅', en='Mahoraga, with a biwa', h=1.59, rock_h=0.3, rock_w=0.6,
         pose=Pz(head_rot=(0.05, 0, 0.0), hand_r=(0.45, 0.8, 3.2), elbow_r=(1, -0.3, -0.4), hand_l=(-0.95, 0.8, 3.45), elbow_l=(-1, -0.3, -0.5)),
         head=dict(style='fierce', fierce=0.75, mouth='closed', ears='normal', hair='bun', hat='pointed', eyes3=True),
         hands=dict(r=dict(pose='pinch', fdir=(-0.5, 0.4, 0.3), back=(0.2, -1, 0.3)), l=dict(pose='grip', grip_axis=(0.3, 0.0, 1))),
         field_items=[biwa]),
    # 04 緊那羅: female, calm, long robes, small cymbals held up before the chest
    dict(name='Kinnara', jp='緊那羅', en='Kinnara, with cymbals', h=1.65, kind='female', costume='tang', rock_h=0.2, scarf_out=0.0,
         pose=dict(foot_r=(0.3, 0.2, 0.28), foot_l=(-0.3, 0.28, 0.28), head_rot=(0.08, 0, 0.0), hand_r=(0.35, 0.95, 4.65), elbow_r=(1, -0.3, -0.8), hand_l=(-0.35, 0.95, 4.65), elbow_l=(-1, -0.3, -0.8)),
         head=dict(style='female', ears='long', hair='bun', hat='crown_tall', eyes='crystal'),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 1, 0.3)), l=dict(pose='grip', grip_axis=(0, 1, 0.3))),
         items=[cymbals()], gold_skirt=0.3),
    # 05 迦楼羅: bird head, wings spread low, a flute to the statue's right, armour, boots
    dict(name='Karura', jp='迦楼羅', en='Garuda, playing a flute', h=1.64, wings=True, rock_h=0.2,
         pose=Pz(head_rot=(0.05, 0, 0.2), hand_r=(0.5, 0.8, 5.2), elbow_r=(1, -0.3, -0.6), hand_l=(-0.15, 0.85, 5.2), elbow_l=(-1, -0.3, -0.7)),
         head=dict(style='bird', hair='none', hat='bird'),
         hands=dict(r=dict(pose='pinch', fdir=(-0.4, 0.3, 0.6), back=(0.3, -0.5, -0.3)), l=dict(pose='pinch', fdir=(0.4, 0.3, 0.6), back=(-0.3, -0.5, -0.3))),
         items=[flute()], col=dict(lip=(0.09, 0.055, 0.04))),
    # 06 乾闥婆: lion helmet, an hourglass drum at the belly, right hand open out to the side
    dict(name='Kendatsuba', jp='乾闥婆', en='Gandharva, with a drum', h=1.64, rock_h=0.25,
         pose=Pz(head_rot=(0.08, 0, 0.05), hand_r=(1.25, 0.75, 3.55), elbow_r=(1, -0.4, -0.3), hand_l=(-0.6, 0.9, 3.25), elbow_l=(-1, -0.4, -0.4)),
         head=dict(style='fierce', fierce=0.5, mouth='closed', ears='normal', hair='bun', hat='lion'),
         hands=dict(r=dict(pose='open', fdir=(0.6, 0.6, 0.2), back=(0, -1, 0.3)), l=dict(pose='open', fdir=(0.6, 0.6, 0.3), back=(-1, 0, 0.2))),
         field_items=[drum_small], gold_skirt=0.3),
    # 07 毘舍闍: bare upper body, a small wheel raised in the right hand, the left at the chest
    dict(name='Bishaja', jp='毘舍闍', en='Pisaca, with a wheel', h=1.61, kind='deva', costume='bare', musc=0.4, rock_h=0.25, skirt_bot=0.9, gold_skirt=0.2,
         pose=dict(foot_r=(0.38, 0.15, 0.28), foot_l=(-0.38, 0.25, 0.28), head_rot=(0.0, 0.0, 0.15), hand_r=(0.95, 0.6, 5.15), elbow_r=(1, 0, -0.7), hand_l=(-0.3, 0.9, 4.6), elbow_l=(-1, -0.3, -0.8)),
         head=dict(style='fierce', fierce=0.85, mouth='closed', ears='normal', hair='flames', hat='none'),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0.2, 1), items=[wheel_small()]), l=dict(pose='pinch', fdir=(0.4, 0.5, 0.6), back=(-0.3, -1, 0))),
         neck_scarf=True),
    # 08 散支大将: flame hair, a trident with a banner in the left hand, the right at the belt
    dict(name='Sanshi-taisho', jp='散支大将', en='General Sanshi', h=1.64, rock_h=0.2,
         pose=Pz(head_rot=(0.03, 0, -0.1), hand_r=(0.7, 0.75, 3.35), elbow_r=(1, -0.5, -0.1), hand_l=(-0.95, 0.55, 4.35), elbow_l=(-1, -0.3, -0.6)),
         head=dict(style='fierce', fierce=1.0, mouth='open', ears='normal', hair='flames', hat='none', nose=6.0),
         hands=dict(r=dict(pose='fist', fdir=(-0.3, 0.6, -0.5), back=(1, -0.2, 0)), l=dict(pose='grip', grip_axis=(0, 0, 1), items=[trident(1.25, 1.35, banner=True)]))),
    # 09 満善車鉢: a short vajra raised at the right shoulder, the left hand down open; a winged crown
    dict(name='Manzen-shahatsu', jp='満善車鉢', en='Manzen-shahatsu', h=1.59, rock_h=0.18,
         pose=Pl(head_rot=(0.05, 0, 0.12), hand_r=(0.75, 0.75, 4.95), elbow_r=(1, -0.3, -0.8), hand_l=(-1.15, 0.3, 3.0), elbow_l=(-1, -0.4, 0)),
         head=dict(style='fierce', fierce=0.85, mouth='closed', ears='normal', hair='bun', hat='wing'),
         hands=dict(r=dict(pose='grip', grip_axis=(1, 0.3, 0.1), items=[small('vajra', 0.22, 'weapon')]), l=dict(pose='open', fdir=(0, 0.2, -1), back=(-1, 0, 0)))),
    # 10 摩尼跋陀羅: vajra at the chest pointing out to its right, left fist on the hip; one foot higher on the rock
    dict(name='Manibadara', jp='摩尼跋陀羅', en='Manibhadra', h=1.60, rock_h=0.22, gold_apron=0.15,
         pose=Pz(foot_l=(-0.42, 0.3, 0.5), knee_l=(-0.3, 1, 0.2), head_rot=(0.05, 0, 0.05), hand_r=(0.75, 0.9, 4.6), elbow_r=(1, -0.3, -0.7), hand_l=(-1.0, 0.3, 3.25), elbow_l=(-1, -0.3, 0.1)),
         head=dict(style='fierce', fierce=0.9, mouth='open', ears='normal', hair='bun', hat='band'),
         hands=dict(r=dict(pose='grip', grip_axis=(1, 0.2, 0.1), items=[small('vajra', 0.22, 'weapon')]), l=dict(pose='fist', fdir=(0.3, 0.6, -0.6), back=(-1, -0.2, 0)))),
    # 11 毘沙門天: a trident in the right hand, a pagoda raised on the left palm
    dict(name='Bishamonten', jp='毘沙門天', en='Vaisravana (Tamon-ten)', h=1.61, rock_h=0.2,
         pose=Pz(head_rot=(0.02, 0, 0.05), hand_r=(0.95, 0.6, 3.85), elbow_r=(1, -0.4, -0.5), hand_l=(-0.75, 0.75, 5.0), elbow_l=(-1, -0.2, -0.8)),
         head=dict(style='fierce', fierce=0.7, mouth='closed', ears='normal', hair='bun', hat='crown'),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0, 1), items=[trident(1.15, 1.45)]), l=dict(pose='cup', fdir=(0.4, 0.3, 0.3), back=(0, 0, -1), items=[pagoda(0.24)]))),
    # 12 提頭頼吒王: a long sword held point-down at its left, a short sword across the chest in the right
    dict(name='Daizurata-o', jp='提頭頼吒王', en='Dhrtarastra (Jikoku-ten)', h=1.66, rock_h=0.2,
         pose=Pz(head_rot=(0.1, 0, 0.0), hand_r=(0.35, 0.95, 4.2), elbow_r=(1, -0.3, -0.6), hand_l=(-0.6, 0.6, 3.3), elbow_l=(-1, -0.3, -0.3)),
         head=dict(style='fierce', fierce=0.85, mouth='closed', ears='normal', hair='bun', hat='crown'),
         hands=dict(r=dict(pose='grip', grip_axis=(1, 0.2, 0.0), items=[short_sword_h()]), l=dict(pose='grip', grip_axis=(0, 0, 1), items=[long_sword_down()]))),
    # 13 婆籔仙: an emaciated old ascetic, stooping; a scroll held up in the right hand, a cane in the left
    dict(name='Basu-sen', jp='婆籔仙', en='Vasu the ascetic', h=1.56, kind='ascetic', costume='ascetic', musc=-0.8, halo=False, rock_h=0.15, scarf=None,
         pose=dict(foot_r=(0.42, 0.38, 0.28), foot_l=(-0.36, -0.02, 0.28), crouch=0.18, hip_shift=(-0.04, 0.06), pelvis_rot=(0.06, 0.03, 0.08),
                   chest_rot=(0.5, 0.04, 0.1), head_rot=(-0.3, 0.0, 0.05), neck=0.05,
                   hand_r=(-0.6, 0.85, 3.2), elbow_r=(1, -0.1, -0.7), hand_l=(-0.3, 1.15, 4.55), elbow_l=(-1, -0.4, -0.7)),
         head=dict(style='old', age=1.0, fierce=0.15, mouth='open', ears='normal', hair='cap', hat='none', beard=True),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0, 1), items=[staff_ground(bend=0.02)]), l=dict(pose='grip', grip_axis=(1, 0.2, 0.3), items=[scroll()]))),
    # 14 大弁功徳天: a goddess in long robes, a gilded flaming halo, a staff in the right hand, a flaming jewel on the left palm
    dict(name='Daibenkudoku-ten', jp='大弁功徳天', en='Mahasri / Kudokuten', h=1.66, kind='female', costume='tang', rock_h=0.18, scarf_out=0.0, halo_gold=0.75, gold_skirt=0.35,
         sleeve_w=1.3,
         pose=dict(foot_r=(0.3, 0.25, 0.28), foot_l=(-0.32, 0.32, 0.28), hip_shift=(0.05, 0), pelvis_rot=(0, 0.04, -0.06), chest_rot=(0.02, -0.04, 0.07),
                   head_rot=(0.12, 0.03, 0.06), hand_r=(0.5, 0.85, 4.3), elbow_r=(1, -0.3, -0.7), hand_l=(-1.0, 0.8, 4.65), elbow_l=(-1, -0.3, -0.5)),
         head=dict(style='female', ears='long', hair='bun', hat='crown_tall', eyes='crystal', urna=True),
         hands=dict(r=dict(pose='grip', grip_axis=(0.4, 0.1, 1), items=[staff_jewel()]), l=dict(pose='cup', fdir=(0.2, 0.8, 0.1), back=(0, 0.1, -1), items=[jewel_flame()])),
         col=dict(crown='gold')),
    # 15 帝釈天王: robes over armour, a disc (mirror) raised in the right hand, the left hand down; flaming crown and halo
    dict(name='Taishaku-tenno', jp='帝釈天王', en='Indra', h=1.68, kind='deva', costume='tang', armour_under=True, rock_h=0.18, scarf_out=0.0, gold_skirt=0.4, sleeve_w=1.35,
         pose=dict(foot_r=(0.28, 0.26, 0.28), foot_l=(-0.3, 0.3, 0.28), hip_shift=(-0.05, 0), pelvis_rot=(0, -0.04, 0.06), chest_rot=(0.02, 0.04, -0.07),
                   head_rot=(0.14, -0.05, 0.16), hand_r=(0.62, 0.95, 4.8), elbow_r=(1, -0.3, -0.8), hand_l=(-0.55, 0.55, 3.3), elbow_l=(-1, -0.3, -0.2)),
         head=dict(style='deva', ears='long', hair='deva', hat='crown_tall', eyes='crystal', urna=True),
         hands=dict(r=dict(pose='grip', grip_axis=(-0.3, 0.3, 1), items=[mirror(0.085)]), l=dict(pose='relaxed', fdir=(0, 0.4, -1), back=(-1, 0, 0)))),
    # 16 大梵天王: robes, no halo; the right hand raised at the chest, a small jar on the left palm
    dict(name='Daibon-tenno', jp='大梵天王', en='Brahma', h=1.70, kind='deva', costume='tang', halo=False, rock_h=0.18, scarf_out=0.0, gold_skirt=0.2, sleeve_w=1.35,
         pose=dict(foot_r=(0.3, 0.28, 0.28), foot_l=(-0.32, 0.26, 0.28), hip_shift=(0.05, 0), pelvis_rot=(0, 0.04, -0.06), chest_rot=(0.02, -0.03, 0.05),
                   head_rot=(0.12, 0.03, -0.14), hand_r=(0.5, 0.85, 4.85), elbow_r=(1, -0.3, -0.9), hand_l=(-0.5, 0.95, 3.95), elbow_l=(-1, -0.4, -0.4)),
         head=dict(style='deva', ears='long', hair='deva', hat='crown_disc', eyes='crystal', urna=True),
         hands=dict(r=dict(pose='open', fdir=(-0.15, 0.25, 1), back=(0.2, -1, 0)), l=dict(pose='cup', fdir=(0.3, 1, 0), back=(0, 0, -1), items=[vase_small()]))),
    # 17 毘楼勒叉: the right fist raised high above the head, the left hand on the hip
    dict(name='Birurokusha', jp='毘楼勒叉', en='Virudhaka (Zocho-ten)', h=1.65, rock_h=0.2, drape_len=1.4,
         pose=Pl(foot_r=(0.5, 0.15, 0.28), foot_l=(-0.42, 0.35, 0.28), head_rot=(0.0, 0, 0.12), hand_r=(0.95, 0.35, 6.6), elbow_r=(1, 0.0, -0.5), hand_l=(-1.05, 0.15, 3.35), elbow_l=(-1, -0.3, 0.2)),
         head=dict(style='fierce', fierce=0.9, mouth='closed', ears='normal', hair='bun', hat='crown'),
         hands=dict(r=dict(pose='fist', fdir=(0, 0.3, 1), back=(0, -1, 0)), l=dict(pose='fist', fdir=(0.3, 0.6, -0.6), back=(-1, -0.2, 0)))),
    # 18 毘楼博叉: helmet, a halberd held high in the left hand, the right hand low before the body; a wide stance on a tall rock
    dict(name='Birubakusha', jp='毘楼博叉', en='Virupaksa (Komoku-ten)', h=1.59, rock_h=0.3, scarf_out=0.35,
         pose=Pl(foot_r=(0.55, 0.25, 0.28), foot_l=(-0.5, 0.15, 0.45), hip_shift=(0.06, 0), head_rot=(0.05, 0, 0.15),
                 hand_r=(0.7, 0.85, 3.3), elbow_r=(1, -0.4, -0.3), hand_l=(-0.85, 0.35, 5.55), elbow_l=(-1, 0, -0.6)),
         head=dict(style='fierce', fierce=1.0, mouth='open', ears='normal', hair='bun', hat='helmet'),
         hands=dict(r=dict(pose='relaxed', fdir=(-0.3, 0.6, -0.5), back=(1, -0.3, 0.2)), l=dict(pose='grip', grip_axis=(0, 0, 1), items=[pole(1.6, 0.9)]))),
    # 19 薩遮摩和羅: bare upper body, a scarf knotted at the throat; the right palm open at the shoulder, a bird-topped staff in the left
    dict(name='Sasha-mawara', jp='薩遮摩和羅', en='Mahesvara', h=1.59, kind='deva', costume='bare', musc=0.35, rock_h=0.22, skirt_bot=0.95, neck_scarf=True, gold_skirt=0.35,
         pose=dict(foot_r=(0.38, 0.2, 0.28), foot_l=(-0.4, 0.15, 0.28), chest_rot=(-0.05, 0, 0.08), head_rot=(-0.05, 0, 0.12),
                   hand_r=(0.8, 0.7, 5.0), elbow_r=(1, -0.3, -0.8), hand_l=(-0.6, 0.65, 4.2), elbow_l=(-1, -0.4, -0.4)),
         head=dict(style='fierce', fierce=0.55, mouth='open', ears='normal', hair='bun', hat='crown', brow=0.0),
         hands=dict(r=dict(pose='spread', fdir=(0, 0.2, 1), back=(0, -1, 0)), l=dict(pose='grip', grip_axis=(0, 0, 1), items=[bird_staff()]))),
    # 20 五部浄居: the right arm down, hand open; a sword upright before the left shoulder; tall boots
    dict(name='Gobu-jogo', jp='五部浄居', en='Gobu-jogo', h=1.62, rock_h=0.18, gold_apron=0.5,
         pose=Pz(head_rot=(0.05, 0, 0.05), hand_r=(1.15, 0.45, 3.05), elbow_r=(1, -0.3, 0), hand_l=(-0.45, 0.85, 4.35), elbow_l=(-1, -0.4, -0.6)),
         head=dict(style='fierce', fierce=0.85, mouth='closed', ears='normal', hair='bun', hat='crown'),
         hands=dict(r=dict(pose='open', fdir=(0.1, 0.2, -1), back=(1, 0, 0)), l=dict(pose='grip', grip_axis=(0.05, 0.1, 1), items=[sword(0.55)]))),
    # 21 金色孔雀王: the right arm raised high in a great sleeve, the left fist at the waist; the face splits to show another
    dict(name='Konjiki-kujaku-o', jp='金色孔雀王', en='Golden Peacock King', h=1.64, rock_h=0.25, gold_skirt=0.4, drape_len=1.5,
         pose=Pl(head_rot=(0.0, 0, -0.08), hand_r=(0.75, 0.4, 6.2), elbow_r=(1, 0.2, -0.6), hand_l=(-0.95, 0.4, 3.4), elbow_l=(-1, -0.3, 0.1)),
         head=dict(style='fierce', fierce=0.6, mouth='closed', ears='normal', hair='bun', hat='crown', split=True),
         hands=dict(r=dict(pose='grip', grip_axis=(0.1, 0.3, 1), items=[sword(0.55)]), l=dict(pose='fist', fdir=(0.3, 0.6, -0.6), back=(-1, -0.2, 0)))),
    # 22 神母女: an old woman in a hooded robe, palms joined
    dict(name='Jinmo-nyo', jp='神母女', en='Hariti (Kishimojin)', h=1.54, kind='female', costume='hooded', halo=False, rock_h=0.22, scarf=None,
         pose=dict(foot_r=(0.3, 0.22, 0.28), foot_l=(-0.3, 0.26, 0.28), chest_rot=(0.12, 0, 0), head_rot=(0.08, 0, 0),
                   hand_r=(0.03, 1.0, 4.65), elbow_r=(1, -0.2, -0.9), hand_l=(-0.03, 1.0, 4.65), elbow_l=(-1, -0.2, -0.9)),
         head=dict(style='oldwoman', age=1.0, ears='normal', hair='hood', hat='none', eyes='crystal'),
         hands=dict(r=dict(pose='prayer', fdir=(0, 0.35, 1), back=(1, 0, 0)), l=dict(pose='prayer', fdir=(0, 0.35, 1), back=(-1, 0, 0)))),
    # 23 金毘羅: a crested helmet; a bow held across the belly; the right sleeve flaring out
    dict(name='Konpira', jp='金毘羅', en='Kumbhira, with a bow', h=1.55, rock_h=0.28, sleeve=1.25,
         pose=Pl(foot_l=(-0.45, 0.3, 0.42), head_rot=(0.12, 0, 0.12), hand_r=(0.35, 0.85, 3.55), elbow_r=(1, -0.4, -0.3), hand_l=(-0.4, 0.85, 3.7), elbow_l=(-1, -0.4, -0.3)),
         head=dict(style='fierce', fierce=0.9, mouth='closed', ears='normal', hair='bun', hat='helmet'),
         hands=dict(r=dict(pose='grip', grip_axis=(1, 0.1, 0.1)), l=dict(pose='grip', grip_axis=(1, 0.1, 0.1))),
         items=[bow_held()]),
    # 24 畢婆伽羅: the right fist down at the side, the left fist at the chest; gilded skirt
    dict(name='Hibakara', jp='畢婆伽羅', en='Hibakara', h=1.64, rock_h=0.22, gold_skirt=0.35, gold_apron=0.45,
         pose=Pl(head_rot=(0.05, 0, -0.1), hand_r=(1.05, 0.4, 3.15), elbow_r=(1, -0.3, 0.1), hand_l=(-0.4, 0.85, 4.55), elbow_l=(-1, -0.3, -0.8)),
         head=dict(style='fierce', fierce=0.95, mouth='closed', ears='normal', hair='bun', hat='crown'),
         hands=dict(r=dict(pose='fist', fdir=(0, 0.3, -1), back=(1, 0, 0)), l=dict(pose='fist', fdir=(0.4, 0.4, 0.6), back=(-0.3, -1, 0)))),
    # 25 阿修羅: three faces, six arms (upper pair raised to the sides, palms up; middle pair out; front pair joined), bare torso, tall rock
    dict(name='Ashura', jp='阿修羅', en='Asura, three faces and six arms', h=1.65, kind='deva', costume='bare', heads=7.6, musc=0.1, rock_h=0.36, rock_w=0.55,
         skirt_bot=0.35, necklace=True, gold_skirt=0.4, scarf_out=0.0,
         pose=dict(foot_r=(0.28, 0.25, 0.28), foot_l=(-0.28, 0.2, 0.28), head_rot=(0.02, 0, 0), hand_r=(0.04, 1.0, 4.75), elbow_r=(1, -0.2, -0.9), hand_l=(-0.04, 1.0, 4.75), elbow_l=(-1, -0.2, -0.9)),
         head=dict(style='fierce', fierce=0.65, mouth='closed', ears='normal', hair='bun', hat='crown_disc', faces=3, eyes='crystal'),
         extra_arms=[(1, (1.65, 0.35, 5.9), (1, -0.2, -0.3), (0.2, -1, 0.3)), (-1, (-1.65, 0.35, 5.9), (-1, -0.2, -0.3), (-0.2, -1, 0.3)),
                     (1, (1.45, 0.55, 4.1), (1, -0.2, -0.6), (0, 0, -1)), (-1, (-1.45, 0.55, 4.1), (-1, -0.2, -0.6), (0, 0, -1))],
         hands=dict(r=dict(pose='prayer', fdir=(0, 0.35, 1), back=(1, 0, 0)), l=dict(pose='prayer', fdir=(0, 0.35, 1), back=(-1, 0, 0)),
                    x0=dict(pose='open', fdir=(0.6, 0.3, 0.7), back=(0, -0.4, -1)), x1=dict(pose='open', fdir=(-0.6, 0.3, 0.7), back=(0, -0.4, -1)),
                    x2=dict(pose='relaxed', fdir=(0.8, 0.4, 0.1), back=(0, 0, -1)), x3=dict(pose='relaxed', fdir=(-0.8, 0.4, 0.1), back=(0, 0, -1)))),
    # 26 伊鉢羅: flame hair, a hammer raised in the right hand, a snake held at the chest in the left
    dict(name='Ihatsura', jp='伊鉢羅', en='Ihatsura, with hammer and snake', h=1.64, rock_h=0.2, gold_skirt=0.4,
         pose=Pz(head_rot=(0.05, 0, 0.05), hand_r=(0.85, 0.8, 4.75), elbow_r=(1, -0.3, -0.7), hand_l=(-0.65, 0.85, 4.25), elbow_l=(-1, -0.3, -0.7)),
         head=dict(style='fierce', fierce=1.0, mouth='open', ears='normal', hair='flames', hat='none'),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0.3, 1), items=[hammer()]), l=dict(pose='grip', grip_axis=(0, 0, 1))),
         field_items=[snake_in_left]),
    # 27 娑伽羅龍王: snakes rising from the crown, a sword upright before the chest in the right hand, a snake in the left at the shoulder
    dict(name='Sagara-ryuo', jp='娑伽羅龍王', en='Dragon King Sagara', h=1.66, rock_h=0.25, gold_skirt=0.3,
         pose=Pz(head_rot=(0.05, 0, -0.08), hand_r=(0.35, 0.95, 4.0), elbow_r=(1, -0.3, -0.6), hand_l=(-0.75, 0.75, 5.0), elbow_l=(-1, -0.3, -0.8)),
         head=dict(style='fierce', fierce=0.8, mouth='closed', ears='normal', hair='bun', hat='snakes'),
         hands=dict(r=dict(pose='grip', grip_axis=(0, 0.15, 1), items=[sword(0.6)]), l=dict(pose='grip', grip_axis=(0, 0, 1))),
         field_items=[snake_at_shoulder]),
    # 28 密迹金剛士: Niō un-gyō, mouth shut; the right palm raised forward at the shoulder, the left hand at the hip holding the scarf
    dict(name='Misshaku-kongoshi', jp='密迹金剛士', en='Nio, un-gyo', h=1.68, kind='nio', costume='nio', musc=1.0, halo=False,
         rock_h=0.14, plinth=0.13, rock_w=0.7, rock_d=0.55, hem_side=-1, flap_side=-1, scarf=nio_scarf('b'),
         pose=dict(foot_r=(0.5, 0.3, 0.28), foot_l=(-0.6, 0.1, 0.28), hip_shift=(0.08, 0), pelvis_rot=(0.0, 0.06, -0.12), chest_rot=(0.05, -0.08, 0.15),
                   head_rot=(0.1, -0.05, -0.3), hand_r=(1.25, 0.95, 4.35), elbow_r=(1, -0.3, -0.5), hand_l=(-1.1, 0.25, 3.3), elbow_l=(-1, -0.4, 0.1)),
         head=dict(style='fierce', fierce=1.0, mouth='clenched', ears='normal', hair='nio', hat='none'),
         hands=dict(r=dict(pose='spread', fdir=(0.2, 0.3, 1), back=(0.3, -1, 0)), l=dict(pose='grip', grip_axis=(0, 0.3, 1)))),
]
POS = ['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8', 'N9', 'N10', 'N11', 'N12', 'CFN', 'CRN', 'CRS', 'CFS',
       'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10', 'S11', 'S12']
_POS_BY_NAME = {'Narayana-kengo': 'N1', 'Nanda-ryuo': 'N2', 'Magora': 'N3', 'Kinnara': 'N4', 'Karura': 'N5', 'Kendatsuba': 'N6', 'Bishaja': 'N7',
                'Sanshi-taisho': 'N8', 'Manzen-shahatsu': 'N9', 'Manibadara': 'N10', 'Bishamonten': 'N11', 'Daizurata-o': 'N12', 'Basu-sen': 'CFN',
                'Daibon-tenno': 'CRN', 'Taishaku-tenno': 'CRS', 'Daibenkudoku-ten': 'CFS', 'Birurokusha': 'S1', 'Birubakusha': 'S2', 'Sasha-mawara': 'S3',
                'Gobu-jogo': 'S4', 'Konjiki-kujaku-o': 'S5', 'Jinmo-nyo': 'S6', 'Konpira': 'S7', 'Hibakara': 'S8', 'Ashura': 'S9', 'Ihatsura': 'S10',
                'Sagara-ryuo': 'S11', 'Misshaku-kongoshi': 'S12'}
for _s in SPECS: _s['pos'] = _POS_BY_NAME[_s['name']]

def by_id():
    return {sid(s['name']): s for s in SPECS}

# ---------------------------------------------------------------------------------------------- traces (2x photos, px)
# joint: (px, py[, depth m forward of the body plane]); top / sole: py; hh_px: chin..vertex; head_rot (pitch, roll, yaw)
TRACES = {
    'Basu-sen': dict(top=104, sole=1160, hh_px=165, head=(410, 192, 0.12), head_rot=(-0.2, 0.05, 0.05), chest_up=(0.0, 0.4, 1.0),
                     S_R=(333, 327, 0.02), S_L=(587, 320, 0.0), E_R=(347, 533, 0.04), W_R=(572, 488, 0.14), E_L=(567, 467, 0.02), W_L=(528, 350, 0.16),
                     H_R=(380, 640), H_L=(480, 640), K_R=(392, 900, 0.06), K_L=(510, 900, 0.06), A_R=(395, 1122), A_L=(515, 1122),
                     foot_r=(0.3, 1, 0), foot_l=(-0.25, 1, 0)),
    'Daibenkudoku-ten': dict(top=215, sole=1165, hh_px=122, head=(440, 285, 0.02), head_rot=(0.05, 0.0, 0.0),
                     S_R=(392, 402), S_L=(482, 396), E_R=(378, 470, -0.03), W_R=(372, 515, 0.1), E_L=(512, 520, -0.02), W_L=(548, 458, 0.1),
                     H_R=(408, 645), H_L=(472, 645), K_R=(410, 875), K_L=(468, 875), A_R=(410, 1122), A_L=(470, 1122)),
    'Taishaku-tenno': dict(top=250, sole=1170, hh_px=125, head=(416, 318, 0.02), head_rot=(0.06, 0.03, -0.08),
                     S_R=(365, 432), S_L=(490, 422), E_R=(345, 590, 0.02), W_R=(342, 540, 0.15), E_L=(497, 560, -0.02), W_L=(478, 640, 0.08),
                     H_R=(382, 690), H_L=(455, 690), K_R=(386, 900), K_L=(450, 900), A_R=(390, 1130), A_L=(452, 1130)),
    'Daibon-tenno': dict(top=80, sole=1160, hh_px=135, head=(440, 210, 0.02), head_rot=(0.06, 0.0, -0.1),
                     S_R=(375, 332), S_L=(510, 326), E_R=(340, 520, 0.03), W_R=(358, 440, 0.13), E_L=(560, 600, -0.03), W_L=(515, 640, 0.1),
                     H_R=(410, 680), H_L=(490, 680), K_R=(414, 900), K_L=(486, 900), A_R=(410, 1130), A_L=(490, 1130)),
    'Daizurata-o': dict(top=195, sole=1165, hh_px=138, head=(462, 272, 0.03), head_rot=(0.08, 0.0, 0.0),
                     S_R=(382, 402), S_L=(548, 392), E_R=(375, 545, 0.0), W_R=(425, 608, 0.13), E_L=(580, 540, 0.0), W_L=(502, 604, 0.13),
                     H_R=(420, 722), H_L=(520, 722), K_R=(396, 920, 0.08), K_L=(545, 920, 0.08), A_R=(395, 1122), A_L=(555, 1122),
                     foot_r=(0.5, 1, 0), foot_l=(-0.4, 1, 0)),
    'Birurokusha': dict(top=252, sole=1165, hh_px=135, head=(430, 372, 0.02), head_rot=(0.04, 0.0, -0.05),
                     S_R=(362, 446), S_L=(560, 440), E_R=(212, 372, -0.06), W_R=(214, 268, -0.03), E_L=(640, 560, -0.08), W_L=(575, 682, 0.0),
                     H_R=(412, 742), H_L=(530, 742), K_R=(385, 930, 0.08), K_L=(542, 930, 0.08), A_R=(370, 1130), A_L=(560, 1130),
                     foot_r=(0.5, 1, 0), foot_l=(-0.5, 1, 0)),
}
for _s in SPECS:
    if _s['name'] in TRACES: _s['trace'] = TRACES[_s['name']]

TRACES.update({
    'Bishamonten': dict(top=200, sole=1148, hh_px=125, head=(468, 272, 0.02), head_rot=(0.04, 0.0, 0.08),
                     S_R=(395, 395), S_L=(556, 387), E_R=(331, 532, 0.0), W_R=(358, 589, 0.12), E_L=(645, 484, -0.02), W_L=(653, 400, 0.08),
                     H_R=(411, 726), H_L=(532, 726), K_R=(395, 935, 0.06), K_L=(532, 935, 0.06), A_R=(387, 1113), A_L=(556, 1113)),
    'Birubakusha': dict(top=282, sole=1153, hh_px=112, head=(427, 347, 0.04), head_rot=(0.1, 0.05, -0.12), chest_up=(0.08, 0.15, 1.0),
                     S_R=(347, 468), S_L=(532, 452), E_R=(266, 581, 0.04), W_R=(282, 669, 0.12), E_L=(597, 403, -0.04), W_L=(629, 240, 0.0),
                     H_R=(387, 806), H_L=(508, 806), K_R=(363, 968, 0.12), K_L=(516, 952, 0.12), A_R=(387, 1129), A_L=(524, 1113),
                     foot_r=(0.6, 1, 0), foot_l=(-0.5, 1, 0)),
    'Manibadara': dict(top=226, sole=1153, hh_px=120, head=(435, 339, 0.03), head_rot=(0.05, 0.0, 0.05),
                     S_R=(363, 452), S_L=(516, 444), E_R=(306, 548, 0.04), W_R=(387, 452, 0.16), E_L=(613, 565, -0.06), W_L=(548, 653, -0.02),
                     H_R=(395, 758), H_L=(492, 758), K_R=(387, 952, 0.07), K_L=(516, 952, 0.07), A_R=(387, 1113), A_L=(516, 1113)),
    'Sasha-mawara': dict(top=266, sole=1148, hh_px=120, head=(460, 347, 0.03), head_rot=(0.0, 0.05, -0.06),
                     S_R=(371, 460), S_L=(516, 460), E_R=(290, 548, 0.04), W_R=(298, 440, 0.12), E_L=(637, 556, -0.02), W_L=(556, 484, 0.1),
                     H_R=(387, 694), H_L=(492, 694), K_R=(363, 952, 0.05), K_L=(500, 952, 0.05), A_R=(363, 1113), A_L=(516, 1113)),
    'Manzen-shahatsu': dict(top=282, sole=1148, hh_px=128, head=(439, 363, 0.03), head_rot=(0.06, 0.0, 0.05),
                     S_R=(347, 476), S_L=(532, 468), E_R=(266, 540, 0.02), W_R=(282, 420, 0.06), E_L=(556, 597, -0.02), W_L=(573, 718, 0.04),
                     H_R=(387, 758), H_L=(492, 758), K_R=(387, 952, 0.06), K_L=(500, 952, 0.06), A_R=(403, 1113), A_L=(516, 1113)),
    'Gobu-jogo': dict(top=250, sole=1148, hh_px=135, head=(435, 363, 0.03), head_rot=(0.06, 0.0, 0.0),
                     S_R=(347, 460), S_L=(532, 452), E_R=(266, 613, -0.02), W_R=(242, 774, 0.03), E_L=(613, 605, -0.02), W_L=(540, 556, 0.14),
                     H_R=(387, 758), H_L=(492, 758), K_R=(379, 968, 0.06), K_L=(516, 968, 0.06), A_R=(379, 1113), A_L=(516, 1113)),
    'Sanshi-taisho': dict(top=266, sole=1185, hh_px=125, head=(411, 363, 0.03), head_rot=(0.05, 0.0, 0.08),
                     S_R=(339, 460), S_L=(508, 452), E_R=(298, 613, -0.02), W_R=(379, 677, 0.12), E_L=(653, 484, -0.04), W_L=(556, 444, 0.08),
                     H_R=(371, 758), H_L=(484, 758), K_R=(363, 952, 0.06), K_L=(500, 952, 0.06), A_R=(347, 1129), A_L=(492, 1129)),
    'Konjiki-kujaku-o': dict(top=242, sole=1153, hh_px=125, head=(444, 355, 0.03), head_rot=(0.05, 0.0, 0.0),
                     S_R=(363, 468), S_L=(516, 460), E_R=(266, 379, -0.04), W_R=(258, 250, 0.0), E_L=(589, 548, -0.06), W_L=(532, 621, 0.05),
                     H_R=(395, 758), H_L=(484, 758), K_R=(395, 968, 0.06), K_L=(524, 968, 0.06), A_R=(387, 1113), A_L=(524, 1113)),
    'Bishaja': dict(top=258, sole=1121, hh_px=120, head=(460, 347, 0.03), head_rot=(0.0, 0.0, 0.0),
                     S_R=(387, 435), S_L=(524, 435), E_R=(323, 532, 0.0), W_R=(331, 425, 0.1), E_L=(556, 532, -0.02), W_L=(468, 468, 0.14),
                     H_R=(395, 710), H_L=(500, 710), K_R=(387, 935, 0.05), K_L=(508, 935, 0.05), A_R=(387, 1097), A_L=(524, 1097)),
    'Jinmo-nyo': dict(top=121, sole=1113, hh_px=140, head=(460, 218, 0.03), head_rot=(0.1, 0.0, 0.0), chest_up=(0, 0.1, 1),
                     S_R=(379, 355), S_L=(548, 355), E_R=(363, 500, 0.02), W_R=(452, 410, 0.16), E_L=(556, 500, 0.02), W_L=(468, 410, 0.16),
                     H_R=(403, 677), H_L=(516, 677), K_R=(403, 903), K_L=(516, 903), A_R=(411, 1081), A_L=(516, 1081)),
    'Kendatsuba': dict(top=258, sole=1161, hh_px=125, head=(435, 355, 0.03), head_rot=(0.05, 0.0, 0.0),
                     S_R=(347, 468), S_L=(532, 460), E_R=(290, 556, 0.03), W_R=(266, 645, 0.12), E_L=(613, 532, 0.0), W_L=(573, 621, 0.12),
                     H_R=(379, 790), H_L=(492, 790), K_R=(355, 984, 0.06), K_L=(508, 984, 0.06), A_R=(347, 1113), A_L=(508, 1113)),
    'Konpira': dict(top=234, sole=1129, hh_px=125, head=(444, 347, 0.03), head_rot=(0.1, 0.0, 0.05), chest_up=(0, 0.12, 1),
                     S_R=(347, 427), S_L=(516, 427), E_R=(282, 516, 0.03), W_R=(363, 597, 0.13), E_L=(548, 613, 0.0), W_L=(452, 677, 0.13),
                     H_R=(379, 758), H_L=(500, 758), K_R=(371, 952, 0.09), K_L=(532, 952, 0.09), A_R=(371, 1097), A_L=(556, 1097)),
    'Karura': dict(top=266, sole=1161, hh_px=125, head=(452, 363, 0.03), head_rot=(0.05, 0.0, 0.05),
                     S_R=(347, 460), S_L=(532, 460), E_R=(306, 532, 0.06), W_R=(347, 440, 0.2), E_L=(532, 532, 0.06), W_L=(484, 425, 0.2),
                     H_R=(379, 774), H_L=(492, 774), K_R=(363, 984, 0.06), K_L=(508, 984, 0.06), A_R=(339, 1137), A_L=(500, 1137)),
    'Hibakara': dict(top=242, sole=1161, hh_px=125, head=(444, 355, 0.03), head_rot=(0.05, 0.0, 0.0),
                     S_R=(363, 468), S_L=(524, 460), E_R=(331, 597, -0.02), W_R=(363, 677, 0.06), E_L=(629, 581, -0.04), W_L=(540, 532, 0.12),
                     H_R=(387, 774), H_L=(500, 774), K_R=(363, 984, 0.06), K_L=(516, 984, 0.06), A_R=(331, 1129), A_L=(532, 1129)),
    'Kinnara': dict(top=242, sole=1129, hh_px=120, head=(427, 363, 0.03), head_rot=(0.06, 0.0, 0.0),
                     S_R=(363, 468), S_L=(516, 468), E_R=(331, 605, 0.04), W_R=(371, 515, 0.16), E_L=(516, 605, 0.04), W_L=(468, 520, 0.16),
                     H_R=(387, 774), H_L=(484, 774), K_R=(387, 968), K_L=(484, 968), A_R=(387, 1097), A_L=(484, 1097)),
    'Ashura': dict(top=202, sole=1081, hh_px=115, head=(435, 290, 0.03), head_rot=(0.0, 0.0, 0.0),
                     S_R=(363, 395), S_L=(516, 395), E_R=(339, 556, 0.06), W_R=(428, 490, 0.18), E_L=(532, 556, 0.06), W_L=(442, 490, 0.18),
                     H_R=(387, 726), H_L=(484, 726), K_R=(371, 919, 0.04), K_L=(484, 919, 0.04), A_R=(363, 1048), A_L=(492, 1048),
                     extra=[(1, (250, 387, -0.04), (194, 347, -0.02)), (-1, (653, 387, -0.04), (710, 331, -0.02)),
                            (1, (290, 532, -0.02), (226, 565, 0.04)), (-1, (597, 532, -0.02), (661, 565, 0.04))]),
    'Magora': dict(top=226, sole=1129, hh_px=120, head=(435, 331, 0.03), head_rot=(0.08, 0.0, 0.05),
                     S_R=(355, 435), S_L=(516, 435), E_R=(290, 532, 0.03), W_R=(323, 630, 0.14), E_L=(532, 645, 0.0), W_L=(573, 556, 0.12),
                     H_R=(379, 774), H_L=(484, 774), K_R=(363, 952, 0.06), K_L=(500, 952, 0.06), A_R=(331, 1097), A_L=(532, 1097)),
    'Ihatsura': dict(top=250, sole=1153, hh_px=125, head=(435, 363, 0.03), head_rot=(0.05, 0.0, 0.0),
                     S_R=(347, 468), S_L=(532, 460), E_R=(290, 589, 0.02), W_R=(282, 490, 0.12), E_L=(605, 581, -0.02), W_L=(540, 500, 0.14),
                     H_R=(379, 774), H_L=(492, 774), K_R=(363, 968, 0.06), K_L=(508, 968, 0.06), A_R=(339, 1113), A_L=(516, 1113)),
    'Nanda-ryuo': dict(top=258, sole=1145, hh_px=115, head=(468, 339, 0.03), head_rot=(0.06, 0.0, -0.05),
                     S_R=(363, 427), S_L=(532, 427), E_R=(306, 532, 0.04), W_R=(371, 430, 0.16), E_L=(581, 597, -0.02), W_L=(500, 621, 0.13),
                     H_R=(387, 774), H_L=(492, 774), K_R=(379, 968, 0.05), K_L=(492, 968, 0.05), A_R=(379, 1113), A_L=(508, 1113)),
    'Sagara-ryuo': dict(top=250, sole=1153, hh_px=120, head=(444, 339, 0.03), head_rot=(0.05, 0.0, 0.0),
                     S_R=(347, 435), S_L=(524, 435), E_R=(290, 613, 0.02), W_R=(371, 589, 0.14), E_L=(605, 556, -0.02), W_L=(565, 484, 0.12),
                     H_R=(387, 758), H_L=(500, 758), K_R=(371, 968, 0.06), K_L=(532, 968, 0.06), A_R=(371, 1113), A_L=(548, 1113)),
    'Misshaku-kongoshi': dict(top=218, sole=1153, hh_px=150, head=(468, 306, 0.04), head_rot=(0.08, -0.05, 0.3), chest_up=(-0.1, 0.05, 1.0),
                     S_R=(363, 435), S_L=(556, 411), E_R=(274, 605, 0.04), W_R=(250, 475, 0.14), E_L=(629, 556, -0.04), W_L=(613, 661, 0.04),
                     H_R=(419, 726), H_L=(548, 726), K_R=(387, 952, 0.07), K_L=(581, 952, 0.07), A_R=(371, 1097), A_L=(597, 1097),
                     foot_r=(0.5, 1, 0), foot_l=(-0.55, 1, 0)),
})
for _s in SPECS:
    if _s['name'] in TRACES: _s['trace'] = TRACES[_s['name']]
