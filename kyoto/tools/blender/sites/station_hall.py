"""京都駅ビル (Hara Hiroshi, 1997): the long glass-and-frame building seen from the 烏丸口 plaza and from the air.

Site frame: x east, y north, metres from the central exit; heights are above the local street (~27.9 m T.P.).
West -> east along the north side (see the dossier, OSM w136243347 and PLATEAU roofs):
  west wing (Isetan, 59 m)  |  podium + blue glass tower + crystal pavilions (x -101..-62)  |  central gate with the
  JR 京都 drums between two granite pylons under the exposed arch truss, the notch tower above (x -62..-30)  |
  arcade of five steel arches carrying the atrium glass screen (x -32..58): vertical glass to 34 m, then the great
  sloped glass roof to the 52 m ridge  |  Hotel Granvia (east block, 60 m) with its balcony tower, podium, portals and
  faceted glass dome  |  east wing.  The 大階段 stair hall west of the atrium has a sloped glass roof rising westward.
Everything on the plaza side is real geometry (mullions, truss, columns); far / back faces use the viewer's wall
programs (ws = 2 ribbon windows, 3 balconies)."""
import math
import numpy as np
from jk import prim
from . import station_util as U

# ---- the material look of the building
GRANITE = (146, 148, 146)
GRANITE_D = (70, 72, 74)
PANEL = (176, 180, 186)
GLASS_T = (110, 130, 150)
Z = np.array([0.0, 0.0, 1.0])

def zmin(S, x0, y0, x1, y1, n=6):
    xs = np.linspace(x0, x1, n); ys = np.linspace(y0, y1, n)
    X, Y = np.meshgrid(xs, ys)
    return float(S.ground(X, Y).min())

def wprog(B, a, b, z0, z1, zg, mat='glass_curtain', tint=GLASS_T, fh=3.9, ws=2, seed=0, flags=0, tag='main'):
    """a wall drawn by the viewer's facade program (UV: metres along, height above zg)"""
    U.wall(B, a, b, z0, z1, mat, zg=zg, c0=(*tint, int(round(fh * 10))), c1=(0, ws, seed, flags), tag=tag)

def north_grid(B, x0, x1, y, z0, z1, pu, pv, zg=0.0, glass='glass', frame='metal_dark', **kw):
    """curtain wall facing north: the glass plane at y spans x0..x1 (mullions every pu, transoms every pv)"""
    return U.plane_grid(B, (x1, y, z0), (-1, 0, 0), Z, x1 - x0, z1 - z0, pu, pv, glass=glass, frame=frame, uvv0=z0 - zg, **kw)

def south_grid(B, x0, x1, y, z0, z1, pu, pv, zg=0.0, glass='glass', frame='metal_dark', **kw):
    return U.plane_grid(B, (x0, y, z0), (1, 0, 0), Z, x1 - x0, z1 - z0, pu, pv, glass=glass, frame=frame, uvv0=z0 - zg, **kw)

def east_grid(B, y0, y1, x, z0, z1, pu, pv, zg=0.0, glass='glass', frame='metal_dark', **kw):
    # outward +x: U x V = +x  ->  U = +y
    return U.plane_grid(B, (x, y0, z0), (0, 1, 0), Z, y1 - y0, z1 - z0, pu, pv, glass=glass, frame=frame, uvv0=z0 - zg, **kw)

def west_grid(B, y0, y1, x, z0, z1, pu, pv, zg=0.0, glass='glass', frame='metal_dark', **kw):
    return U.plane_grid(B, (x, y1, z0), (0, -1, 0), Z, y1 - y0, z1 - z0, pu, pv, glass=glass, frame=frame, uvv0=z0 - zg, **kw)

def block(B, S, x0, y0, x1, y1, ztop, tint=PANEL, fh=3.9, ws=2, mat='wall_concrete', sides='nsew', roof_tint=(118, 116, 110), zb=None, parapet=1.0, seed=0, ztop_roof=True):
    """a plain volume with the viewer's wall programs on its faces and a flat roof with a parapet"""
    zg = zmin(S, x0, y0, x1, y1) if zb is None else zb
    z0 = zg - 0.6
    if 's' in sides: wprog(B, (x0, y0), (x1, y0), z0, ztop, zg, mat, tint, fh, ws, seed)
    if 'e' in sides: wprog(B, (x1, y0), (x1, y1), z0, ztop, zg, mat, tint, fh, ws, seed + 1)
    if 'n' in sides: wprog(B, (x1, y1), (x0, y1), z0, ztop, zg, mat, tint, fh, ws, seed + 2)
    if 'w' in sides: wprog(B, (x0, y1), (x0, y0), z0, ztop, zg, mat, tint, fh, ws, seed + 3)
    if ztop_roof: roof(B, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], ztop, zg, roof_tint, parapet)
    return zg

def roof(B, ring, z, zg, tint=(118, 116, 110), parapet=1.0):
    ring = U.ccw(ring)
    U.flat(B, ring, z + 0.02, 'roof_flat', up=True, c0=(*tint, 0))
    if parapet > 0:
        inner = U.buffer_ring(ring, -0.4, 2)
        U.wall_ring(B, ring, z, z + parapet, 'wall_concrete', zg=zg, c0=(150, 150, 148, 0))
        if inner is not None:
            U.wall_ring(B, inner[::-1], z, z + parapet - 0.05, 'wall_concrete', zg=zg, c0=(150, 150, 148, 0))
            U.flat(B, ring, z + parapet, 'wall_concrete', up=True, holes=[inner], c0=(160, 160, 158, 0))

def penthouse(B, x0, y0, x1, y1, z, h, tint=(168, 170, 172)):
    zg = z
    U.box(B, x0, y0, z, x1, y1, z + h, 'wall_concrete', c0=(*tint, 30), c1=(0, 0, 0, 0))
    U.box(B, x0 - 0.15, y0 - 0.15, z + h, x1 + 0.15, y1 + 0.15, z + h + 0.2, 'wall_concrete', c0=(110, 110, 108, 0))

def joints(B, p0, p1, z0, z1, pu=1.4, pv=1.2, depth=0.05, mat='metal_dark'):
    """panel joints on a granite-clad wall (thin dark grooves): vertical every pu, horizontal every pv"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L
    n = np.array([d[1], -d[0]]); nn = np.r_[n, 0.0]
    ts = np.arange(pu, L - 0.2, pu)
    if len(ts):
        c = np.c_[p0[0] + d[0] * ts + n[0] * 0.02, p0[1] + d[1] * ts + n[1] * 0.02]
        U.obox_batch(B, np.c_[c, np.full(len(ts), z0)], np.c_[c, np.full(len(ts), z1)], 0.035, depth, mat, up=nn, tag='detail')
    zs = np.arange(z0 + pv, z1 - 0.2, pv)
    if len(zs):
        a = p0 + n * 0.02; b = p1 + n * 0.02
        U.obox_batch(B, np.c_[np.full(len(zs), a[0]), np.full(len(zs), a[1]), zs], np.c_[np.full(len(zs), b[0]), np.full(len(zs), b[1]), zs], depth, 0.035, mat, up=(0, 0, 1), tag='detail')

# ================================================================================================ the front (plaza side)
def build_front(B, S):
    zg = zmin(S, -105, 20, 60, 60)
    arcade(B, S, zg)
    atrium(B, S, zg)
    gate(B, S, zg)
    notch_tower(B, S, zg)
    podium_and_blue_tower(B, S, zg)
    return zg

# ---------------------------------------------------------------------------- arcade: five steel arches under the glass
ARC_X = [-32.0 + 18.0 * i for i in range(6)]      # pier centres
PIER_W = 3.2

def arcade(B, S, zg):
    y_f, y_b = 44.5, 40.0                     # truss front, rear (the glass screen stands at y_b + 1)
    z_spring, z_gird0, z_gird1 = 8.2, 15.2, 17.6
    # piers (granite)
    lo = np.array([[x - PIER_W / 2, y_b, zg - 0.5] for x in ARC_X]); hi = np.array([[x + PIER_W / 2, y_f, zg + z_gird0] for x in ARC_X])
    U.box_batch(B, lo, hi, 'wall_concrete', c0=(*GRANITE, 0))
    # the box girder under the screen (soffit visible from below), light steel colour
    U.box(B, ARC_X[0] - PIER_W / 2, y_b, zg + z_gird0, ARC_X[-1] + PIER_W / 2, y_f, zg + z_gird1, 'metal_grey')
    U.box(B, ARC_X[0] - PIER_W / 2, y_b + 0.3, zg + z_gird0 - 0.35, ARC_X[-1] + PIER_W / 2, y_f - 0.3, zg + z_gird0, 'white_paint', faces='z')
    # arches and the zig-zag truss above them (front plane), and a mirror at the rear
    for i in range(5):
        xa, xb = ARC_X[i] + PIER_W / 2, ARC_X[i + 1] - PIER_W / 2
        xc = (xa + xb) / 2; half = (xb - xa) / 2
        rise = 5.4
        R = (half ** 2 + rise ** 2) / (2 * rise)
        th = np.linspace(-math.asin(half / R), math.asin(half / R), 16)
        arch = np.array([[xc + R * math.sin(t), (y_f - 0.5), zg + z_spring + (R * math.cos(t) - (R - rise))] for t in th])
        for yy in (y_f - 0.5, y_b + 0.6):
            pts = arch.copy(); pts[:, 1] = yy
            U.obox_batch(B, pts[:-1], pts[1:], 0.55, 0.75, 'metal_grey', up=(0, 1, 0), ends=False)
        # truss between the arch extrados and the girder: verticals every ~2.2 m with V diagonals
        nvv = 7
        xs = np.linspace(xa, xb, nvv + 1)
        def arch_z(x):
            tt = np.arcsin(np.clip((x - xc) / R, -1, 1))
            return zg + z_spring + (R * np.cos(tt) - (R - rise)) + 0.38
        for yy in (y_f - 0.5, y_b + 0.6):
            z_lo = np.array([arch_z(x) for x in xs])
            z_hi = np.full(len(xs), zg + z_gird0)
            P0 = np.c_[xs, np.full(len(xs), yy), z_lo]; P1 = np.c_[xs, np.full(len(xs), yy), z_hi]
            U.obox_batch(B, P0, P1, 0.22, 0.30, 'metal_grey', up=(0, 1, 0))
            Q0 = np.c_[xs[:-1], np.full(nvv, yy), z_hi[:-1]]; Q1 = np.c_[(xs[:-1] + xs[1:]) / 2, np.full(nvv, yy), np.array([arch_z((x0_ + x1_) / 2) for x0_, x1_ in zip(xs[:-1], xs[1:])])]
            Q2 = np.c_[xs[1:], np.full(nvv, yy), z_hi[1:]]
            U.obox_batch(B, np.vstack([Q0, Q2]), np.vstack([Q1, Q1]), 0.20, 0.26, 'metal_grey', up=(0, 1, 0))
        # tie members between front and rear planes under the girder (a few)
        # the dark concourse behind the arches
    U.box(B, ARC_X[0] + PIER_W / 2, y_b - 0.6, zg - 0.4, ARC_X[-1] - PIER_W / 2, y_b, zg + z_gird0, 'glass', faces='Y')
    # lit boards behind the arches (departure displays)
    for i in range(5):
        xc = (ARC_X[i] + ARC_X[i + 1]) / 2
        U.box(B, xc - 3.0, y_b - 0.65, zg + 4.0, xc + 3.0, y_b - 0.6, zg + 4.7, 'lamp', faces='Y')
        B.lamp(xc, y_b + 2.0, zg + 5.0, 120, (1.0, 0.82, 0.6))

# ---------------------------------------------------------------------------- the great glass screen and roof
def atrium(B, S, zg):
    x0, x1 = ARC_X[0] - PIER_W / 2, ARC_X[-1] + PIER_W / 2
    y_g = 41.0                                # glass plane of the screen
    z_a = zg + 17.6; z_b = zg + 34.0; z_r = zg + 52.4
    y_r0, y_r1 = 31.0, 23.0                   # ridge strip
    # lower vertical glass
    north_grid(B, x0, x1, y_g, z_a, z_b, 2.25, 2.05, zg=zg, bands=[(0.0, 0.5, 'metal_dark', 0.35)])
    # dark band at the break
    U.obox_batch(B, np.array([[x1, y_g + 0.15, z_b]]), np.array([[x0, y_g + 0.15, z_b]]), 0.6, 0.35, 'metal_dark', up=(0, 1, 0))
    # the sloped glass (leans back to the ridge)
    O = np.array([x1, y_g, z_b]); Uv = np.array([-1.0, 0, 0]); Vv = U.unit([0, y_r0 - y_g, z_r - z_b])
    lv = math.hypot(y_r0 - y_g, z_r - z_b)
    U.plane_grid(B, O, Uv, Vv, x1 - x0, lv, 2.25, 2.35, glass='glass', frame='metal_dark', uvv0=z_b - zg, mw=0.1, md=0.16, tw=0.08, td=0.12)
    # flat ridge strip (glass, light frame)
    U.plane_grid(B, (x0, y_r1, z_r), (1, 0, 0), (0, 1, 0), x1 - x0, y_r0 - y_r1, 2.25, 2.4, glass='glass', frame='metal_grey', mw=0.1, md=0.12, tw=0.08, td=0.1)
    # south slope down to the lower roofs
    y_s = 10.0; z_s = zg + 33.0
    O2 = np.array([x0, y_s, z_s]); V2 = U.unit([0, y_r1 - y_s, z_r - z_s]); lv2 = math.hypot(y_r1 - y_s, z_r - z_s)
    U.plane_grid(B, O2, (1, 0, 0), V2, x1 - x0, lv2, 2.25, 2.4, glass='glass', frame='metal_grey', mw=0.1, md=0.12, tw=0.08, td=0.1)
    # end walls of the glass volume (vertical profile polygons), solid light panels with a few windows
    prof = np.array([[y_g, z_a], [y_g, z_b], [y_r0, z_r], [y_r1, z_r], [y_s, z_s], [y_s, z_a]])
    for xx, out in ((x0, -1), (x1, 1)):
        P = np.c_[np.full(len(prof), xx), prof[:, 0], prof[:, 1]]
        U.plane_poly(B, P, 'glass', normal=(out, 0, 0), cell=8.0)
    # the dark wedge panels where the sloped roof meets the towers (west end): a glassy fin
    # window cleaners' gondola rails on the roof: a pair of thin rails along the ridge
    for yy in (y_r0 - 0.5, y_r1 + 0.5):
        U.obox_batch(B, np.array([[x0 + 1, yy, z_r + 0.1]]), np.array([[x1 - 1, yy, z_r + 0.1]]), 0.12, 0.2, 'metal_dark', up=(0, 0, 1), tag='detail')
    # four small arched alcoves in the lower glass (white boxes with a half-round opening)
    for xc in (-12.0, 8.0, 28.0, 48.0):
        U.box(B, xc - 1.4, y_g + 0.1, z_a + 0.5, xc + 1.4, y_g + 0.7, z_a + 3.3, 'wall_plaster', c0=(205, 205, 200, 30))
        prim.cyl(B, (xc, y_g + 0.72, z_a + 1.5), (xc, y_g + 0.74, z_a + 1.5), 1.0, 1.0, 14, 'glass', caps=(False, True), tag='main')
    # the roof behind: ventilation boxes along the south side of the glass roof
    roof_z = zg + 33.0
    return z_r

# ---------------------------------------------------------------------------- central gate
GATE_X = -47.0

def gate(B, S, zg):
    # two granite pylons
    for (xa, xb) in ((-62.0, -56.0), (-38.0, -32.0)):
        U.box(B, xa, 46.0, zg - 0.5, xb, 59.6, zg + 22.5, 'wall_concrete', c0=(*GRANITE, 0))
        # a plinth of dark stone
        U.box(B, xa - 0.1, 45.9, zg - 0.5, xb + 0.1, 59.7, zg + 2.4, 'wall_concrete', c0=(*GRANITE_D, 0))
    # granite panel joints on the pylons (all four faces) and a lit information board each side of the gate
    zj0, zj1 = zg + 2.4, zg + 22.5
    joints(B, (-56.0, 59.65), (-62.0, 59.65), zj0, zj1); joints(B, (-32.0, 59.65), (-38.0, 59.65), zj0, zj1)
    joints(B, (-56.05, 46.0), (-56.05, 59.6), zj0, zj1); joints(B, (-37.95, 59.6), (-37.95, 46.0), zj0, zj1)
    joints(B, (-62.05, 59.6), (-62.05, 46.0), zj0, zj1); joints(B, (-31.95, 46.0), (-31.95, 59.6), zj0, zj1)
    # round window on the east pylon
    prim.cyl(B, (-35.0, 59.62, zg + 15.0), (-35.0, 59.7, zg + 15.0), 0.9, 0.9, 16, 'glass', caps=(False, True))
    # dark core behind the gate: the concourse front
    U.box(B, -56.0, 44.0, zg - 0.5, -38.0, 46.0, zg + 31.0, 'wall_concrete', c0=(48, 44, 42, 0))
    U.box(B, -56.0, 45.8, zg + 5.0, -38.0, 46.0, zg + 20.0, 'glass', faces='Y')
    # core blocks with brown cubes and lattice windows (visible through the arch)
    for (xa, xb) in ((-55.0, -49.5), (-44.5, -39.0)):
        U.box(B, xa, 44.2, zg + 20.0, xb, 46.2, zg + 31.0, 'wall_tile', c0=(112, 66, 50, 40), c1=(0, 0, 4, 0))
        north_grid(B, xa + 0.4, xb - 0.4, 44.15, zg + 25.0, zg + 30.0, 1.1, 1.1, zg=zg, glass='glass', frame='metal_dark', tag_frame='main')
    # canopy over the entrance: slab with a deep fascia
    U.box(B, -56.0, 49.0, zg + 4.4, -38.0, 59.6, zg + 6.3, 'wall_plaster', c0=(*PANEL, 20))
    U.box(B, -56.0, 49.0, zg + 4.3, -38.0, 59.6, zg + 4.45, 'metal_dark', faces='z')
    for xc in np.linspace(-53.8, -40.2, 6):                 # perforated panels on the fascia
        U.box(B, xc - 1.6, 59.55, zg + 5.0, xc + 1.6, 59.66, zg + 5.9, 'metal_dark')
    # the two sign drums (JR 京都 / Kyoto Station) with wavy tops
    for (xc, rx) in ((-51.8, 3.6), (-42.2, 3.6)):
        th = np.linspace(0, 2 * math.pi, 25)[:-1]
        ring = np.stack([xc + rx * np.cos(th), 54.2 + 2.6 * np.sin(th)], 1)
        prim.prism(B, ring, zg + 6.3, zg + 8.7, 'wall_plaster', top=True, c0=(*PANEL, 20))
    # lettering: raised white blocks on the drums (no glyphs: three bars each)
    for xc in (-52.6, -51.0, -43.2, -41.2, -39.8):
        U.box(B, xc - 0.3, 56.7, zg + 6.8, xc + 0.3, 56.85, zg + 8.0, 'white_paint', tag='detail')
    # the big arch between the pylons with its lattice (front plane y=47)
    y = 47.2
    xa, xb = -56.0, -38.0
    half = 9.0; rise = 6.0
    R = (half ** 2 + rise ** 2) / (2 * rise)
    xc = (xa + xb) / 2
    th = np.linspace(-math.asin(half / R), math.asin(half / R), 20)
    pts = np.array([[xc + R * math.sin(t), y, zg + 22.5 + (R * math.cos(t) - (R - rise))] for t in th])
    U.obox_batch(B, pts[:-1], pts[1:], 0.9, 1.1, 'metal_grey', up=(0, 1, 0), ends=False)
    # girder above and the diagonals/verticals
    U.box(B, -62.0, y - 1.5, zg + 30.5, -32.0, y + 1.5, zg + 33.0, 'metal_grey')
    xs = np.linspace(xa, xb, 10)
    zl = np.array([zg + 22.5 + (math.sqrt(max(R * R - (x - xc) ** 2, 0)) - (R - rise)) + 0.5 for x in xs])
    zh = np.full(len(xs), zg + 30.5)
    U.obox_batch(B, np.c_[xs, np.full(len(xs), y), zl], np.c_[xs, np.full(len(xs), y), zh], 0.3, 0.4, 'metal_grey', up=(0, 1, 0))
    for i in range(len(xs) - 1):
        zm = float(np.interp((xs[i] + xs[i + 1]) / 2, xs, zl))
        for (xx, zz) in ((xs[i], zh[i]), (xs[i + 1], zh[i + 1])):
            U.obox_batch(B, np.array([[xx, y, zz]]), np.array([[(xs[i] + xs[i + 1]) / 2, y, zm]]), 0.26, 0.34, 'metal_grey', up=(0, 1, 0))
    # side X-braces in the pylon tops (the large diagonals)
    for (xa2, xb2) in ((-62.0, -56.0), (-38.0, -32.0)):
        U.obox_batch(B, np.array([[xa2, y, zg + 22.5], [xb2, y, zg + 22.5]]), np.array([[xb2, y, zg + 30.5], [xa2, y, zg + 30.5]]), 0.5, 0.6, 'metal_grey', up=(0, 1, 0))
    B.lamp(-47.0, 53.0, zg + 3.8, 160, (1.0, 0.8, 0.55))
    B.lamp(-47.0, 57.5, zg + 3.8, 120, (1.0, 0.8, 0.55))

# ---------------------------------------------------------------------------- notch tower (above the gate)
def notch_tower(B, S, zg):
    x0, x1 = -62.0, -30.0
    y_n = 48.6; ztop = zg + 61.0
    # north face above the gate: granite panels (viewer wall program), with the notch
    xl, xr = -54.0, -40.0                       # the notch (a through opening) in the middle
    z_c0, z_c1 = zg + 23.0, zg + 42.0
    gt = (*GRANITE, 0)
    # lower part below the notch is mostly hidden by the gate; keep it solid
    wprog(B, (x1, y_n), (xr, y_n), zg + 22.0, ztop, zg, 'wall_concrete', GRANITE, 3.5, 0, seed=7)
    wprog(B, (xl, y_n), (x0, y_n), zg + 22.0, ztop, zg, 'wall_concrete', GRANITE, 3.5, 0, seed=8)
    wprog(B, (xr, y_n), (xl, y_n), z_c1, ztop, zg, 'wall_concrete', GRANITE, 3.5, 0, seed=9)
    # window grid above the notch (6 x 2 small squares)
    for ix in range(6):
        for iz in range(2):
            xc = xr - 2.0 - ix * 2.1 - 0.0; zc = z_c1 + 4.0 + iz * 2.3
            xc = -41.2 - ix * 2.1
            U.box(B, xc - 0.65, y_n - 0.02, zc, xc + 0.65, y_n + 0.08, zc + 1.2, 'glass', faces='Y')
            U.box(B, xc - 0.75, y_n - 0.02, zc - 0.1, xc + 0.75, y_n + 0.12, zc + 1.3, 'metal_dark', faces='xXzZ', tag='detail')
    # the cavity: floor, back wall, side walls, lip (the 'nose') above
    zc0 = z_c0
    U.box(B, xl, 36.0, zc0 - 0.4, xr, y_n, zc0, 'wall_concrete', c0=(60, 60, 62, 0))
    U.box(B, xl, 35.9, zc0, xr, 36.0, z_c1, 'wall_concrete', c0=(28, 28, 30, 0), faces='Y')
    wprog(B, (xl, 36.0), (xl, y_n), zc0, z_c1, zg, 'wall_concrete', GRANITE_D, 3.5, 0, seed=3)
    wprog(B, (xr, y_n), (xr, 36.0), zc0, z_c1, zg, 'wall_concrete', GRANITE_D, 3.5, 0, seed=4)
    nose = np.array([[xr, y_n, z_c1 - 0.2], [xl, y_n, z_c1 - 0.2]])
    U.box(B, xl - 0.2, y_n - 0.5, z_c1 - 0.9, xr + 0.2, y_n + 2.6, z_c1, 'wall_concrete', c0=(*GRANITE, 0))
    # the brown cubes and lattice windows seen inside
    for (xa, xb) in ((xl + 0.8, xl + 5.0), (xr - 5.0, xr - 0.8)):
        U.box(B, xa, 38.0, zc0, xb, 44.0, zc0 + 6.0, 'wall_tile', c0=(112, 66, 50, 40), c1=(0, 0, 5, 0))
        north_grid(B, xa + 0.3, xb - 0.3, 44.02, zc0 + 6.1, zc0 + 11.0, 1.0, 1.0, zg=zg, glass='glass', frame='metal_dark', tag_frame='main')
        U.box(B, xa, 38.0, zc0 + 6.0, xb, 44.0, zc0 + 11.1, 'metal_dark', faces='xXz')
    joints(B, (-40.0, y_n + 0.01), (-30.0, y_n + 0.01), zg + 23.0, ztop, pu=1.6, pv=1.3)
    joints(B, (-62.0, y_n + 0.01), (-54.0, y_n + 0.01), zg + 23.0, ztop, pu=1.6, pv=1.3)
    # east face of the tower (towards the atrium) and the top
    wprog(B, (x1, 20.0), (x1, y_n), zg + 17.0, ztop, zg, 'wall_concrete', GRANITE, 3.5, 0, seed=5)
    wprog(B, (x0, y_n), (x0, 20.0), zg + 17.0, ztop, zg, 'wall_concrete', GRANITE, 3.5, 0, seed=6)
    roof(B, [(x0, 20.0), (x1, 20.0), (x1, y_n), (x0, y_n)], ztop, zg, (130, 128, 124), 0.9)
    penthouse(B, -58.0, 28.0, -48.0, 38.0, ztop, 3.0)
    # pastel drums at the foot (on the podium roof, beside the notch): painted cylinders
    for i, (xx, tint) in enumerate(((-66.0, (120, 160, 200)), (-64.0, (230, 200, 80)), (-62.0, (230, 170, 190)))):
        pass

# ---------------------------------------------------------------------------- podium, blue tower, crystal pavilions
def podium_and_blue_tower(B, S, zg):
    x0, x1 = -101.0, -62.0
    y_f, y_b = 60.0, 47.0
    z_p = zg + 23.0
    # ---- podium: recessed ground floor (colonnade), upper block with ribbon windows
    ztop_g = zg + 9.0
    cols = np.arange(x0 + 3.0, x1, 7.8)
    lo = np.array([[x - 0.5, y_f - 3.5 - 0.5, zg - 0.3] for x in cols]); hi = np.array([[x + 0.5, y_f - 3.5 + 0.5, ztop_g] for x in cols])
    U.box_batch(B, lo, hi, 'wall_concrete', c0=(*GRANITE_D, 0))
    U.box(B, x0, y_b - 0.2, zg - 0.3, x1, y_b, ztop_g, 'glass', faces='Y')                      # shop fronts (dark)
    # lit shop signs
    for xc in cols[::2]:
        U.box(B, xc + 1.0, y_b + 0.0, zg + 5.4, xc + 5.0, y_b + 0.1, zg + 6.0, 'lamp', faces='Y')
    # underside of the first slab and the upper block
    U.box(B, x0, y_b, ztop_g - 0.4, x1, y_f, ztop_g + 4.5, 'wall_concrete', c0=(*PANEL, 0), faces='Z')
    wprog(B, (x0, y_f), (x1, y_f), ztop_g, zg + 13.5, zg, 'wall_concrete', (172, 174, 178), 4.5, 0, seed=11)
    wprog(B, (x0, y_f), (x1, y_f), zg + 21.0, z_p, zg, 'wall_concrete', (172, 174, 178), 4.5, 0, seed=12)
    # ribbon windows with white-grey frames
    north_grid(B, x0, x1, y_f - 0.05, zg + 13.5, zg + 21.0, 3.25, 7.5, zg=zg, glass='glass', frame='metal_grey', mw=0.16, md=0.22)
    wprog(B, (x0, y_f), (x0, y_b), zg - 0.3, z_p, zg, 'wall_concrete', (172, 174, 178), 4.5, 0, seed=13)
    # the slab nose on the ground floor (front)
    U.box(B, x0, y_f - 4.0, ztop_g - 0.4, x1, y_f, ztop_g + 4.5, 'wall_concrete', c0=(*PANEL, 0), faces='')
    roof(B, [(x0, y_b), (x1, y_b), (x1, y_f), (x0, y_f)], z_p, zg, (130, 128, 124), 0.9)
    # a shop sign band on the podium front (lit): a row of coloured panels
    # ---- blue glass tower above the podium (north face and west side)
    z_t = zg + 61.0
    north_grid(B, x0, x1, 48.0, z_p, z_t, 2.1, 2.1, zg=zg, glass='glass', frame='metal_dark')
    west_grid(B, 34.0, 48.0, x0, z_p, z_t, 2.1, 2.1, zg=zg, glass='glass', frame='metal_dark')
    wprog(B, (x1, 34.0), (x1, 48.0), z_p, z_t, zg, 'glass_curtain', GLASS_T, 3.9, 2, seed=15)
    wprog(B, (x0, 34.0), (x1, 34.0), z_p, z_t, zg, 'glass_curtain', GLASS_T, 3.9, 2, seed=16)
    roof(B, [(x0, 34.0), (x1, 34.0), (x1, 48.0), (x0, 48.0)], z_t, zg, (130, 128, 124), 1.0)
    penthouse(B, -92.0, 38.0, -80.0, 45.0, z_t, 3.6, tint=(150, 160, 170))
    # ---- crystal pavilions on the podium roof (facing the tower's foot)
    rng = np.random.default_rng(1997)
    for i, (cx, cy, r, h) in enumerate(((-72.0, 51.5, 4.8, 10.0), (-78.5, 55.0, 4.2, 8.0), (-85.0, 52.5, 5.4, 12.5), (-91.0, 54.5, 3.8, 7.0), (-67.0, 55.5, 3.6, 6.5))):
        U.crystal(B, cx, cy, z_p, r, h, seed=300 + i)
    # pastel drums near the tower foot
    for (xx, yy, tint) in ((-66.8, 44.5, (110, 150, 205)), (-64.6, 46.5, (235, 205, 80)), (-62.6, 44.6, (232, 170, 190))):
        prim.cyl(B, (xx, yy, z_p), (xx, yy, z_p + 3.6), 1.15, 1.15, 12, 'cloth', c0=(*tint, 0))

# ================================================================================================ Hotel Granvia (east block)
def dome(B, cx, cy, z0, rx, ry, rz, sub=2, mat_glass='glass', mat_frame='metal_grey'):
    """a faceted glass dome (flattened ico-sphere, upper half) with frame members on the edges"""
    t = (1 + 5 ** 0.5) / 2
    V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    F = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    V = V / np.linalg.norm(V, axis=1, keepdims=True); V = list(V)
    for _ in range(sub):
        mid = {}; F2 = []
        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                p = (np.asarray(V[a]) + np.asarray(V[b])) / 2; V.append(p / np.linalg.norm(p)); mid[k] = len(V) - 1
            return mid[k]
        for a, b, c in F:
            ab, bc, ca = m(a, b), m(b, c), m(c, a)
            F2 += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        F = F2
    V = np.array(V)
    keep = [f for f in F if V[f][:, 2].min() > -0.02]
    P = V * np.array([rx, ry, rz]) + np.array([cx, cy, z0])
    # outward-facing triangles
    tris = []
    for f in keep:
        a, b, c = P[f]
        n = np.cross(b - a, c - a)
        if n @ ((a + b + c) / 3 - np.array([cx, cy, z0])) < 0: f = [f[0], f[2], f[1]]
        tris.append(f)
    B.add(P, tris, mat_glass, tag='main')
    edges = set()
    for f in keep:
        for i in range(3):
            e = (min(f[i], f[(i + 1) % 3]), max(f[i], f[(i + 1) % 3])); edges.add(e)
    E = np.array(sorted(edges))
    mid_ = (P[E[:, 0]] + P[E[:, 1]]) / 2
    up = mid_ - np.array([cx, cy, z0])
    U.obox_batch(B, P[E[:, 0]], P[E[:, 1]], 0.16, 0.2, mat_frame, up=up, tag='main')

def build_east(B, S):
    zg = zmin(S, 58, -16, 204, 52)
    z_pod = zg + 19.0
    y_f = 50.9
    # ---- NE balcony tower (x 58..73) -- real window / balcony geometry on its north face
    xa, xb = 57.8, 72.9
    z_top = zg + 65.8
    U.box(B, xa, 36.0, zg - 0.6, xb, 50.0, z_top, 'wall_concrete', c0=(148, 150, 152, 33), c1=(0, 0, 14, 0), faces='XZy')
    wprog(B, (xb, 50.0), (xa, 50.0), zg - 0.6, z_top, zg, 'wall_concrete', (150, 152, 156), 3.4, 0, seed=21)
    # skip the box's own north face: it was left out above (faces 'XZy' has no 'Y')
    zf = zg + 20.0
    nfl = int((z_top - 3.0 - zf) / 3.35)
    wins = []; slabs = []; rails = []
    for k in range(nfl):
        z0 = zf + 3.35 * k
        for i in range(4):
            xc = xb - 2.2 - i * 3.45
            wins.append((xc - 0.85, 50.0 + 0.02, z0 + 0.9, xc + 0.85, 50.05, z0 + 2.6))
        slabs.append((xa, 50.0, z0 - 0.15, xb, 51.1, z0 + 0.15))
        rails.append((xa, 51.0, z0 + 0.15, xb, 51.08, z0 + 1.1))
    wins = np.array(wins); slabs = np.array(slabs); rails = np.array(rails)
    U.box_batch(B, wins[:, :3], wins[:, 3:], 'glass', faces='Y')
    U.box_batch(B, slabs[:, :3], slabs[:, 3:], 'white_paint', c0=(220, 220, 215, 0))
    U.box_batch(B, rails[:, :3], rails[:, 3:], 'metal_grey', faces='yY', tag='detail')
    # glazed top terrace
    U.box(B, xa, 36.5, z_top, xb, 50.0, z_top + 3.2, 'glass', faces='xXyYZ')
    U.box(B, xa - 0.2, 36.3, z_top + 3.2, xb + 0.2, 50.2, z_top + 3.5, 'wall_concrete', c0=(120, 120, 118, 0))
    # east face and west face of the tower
    wprog(B, (xb, 36.0), (xb, 50.0), zg - 0.6, z_top, zg, 'wall_concrete', (150, 152, 156), 3.4, 3, seed=22)
    wprog(B, (xa, 50.0), (xa, 44.5), zg - 0.6, z_top, zg, 'wall_concrete', (150, 152, 156), 3.4, 3, seed=23)
    # ---- podium (x 73..151, y 36..50.9): ribbon windows over three big portals
    px0, px1 = xb, 151.0
    z_p0 = zg + 9.0
    portals = [(80.0, 92.0), (96.0, 108.0), (112.0, 124.0)]
    # wall pieces between the portals (full height) and above them
    xs = [px0] + [v for p in portals for v in p] + [px1]
    for i in range(0, len(xs) - 1, 2):
        a, b = xs[i], xs[i + 1]
        wprog(B, (b, y_f), (a, y_f), zg - 0.6, z_pod, zg, 'wall_concrete', (148, 150, 154), 4.0, 0, seed=30 + i)
    for (a, b) in portals:
        wprog(B, (b, y_f), (a, y_f), zg + 8.5, z_pod, zg, 'wall_concrete', (148, 150, 154), 4.0, 0, seed=40)
        # portal interior: dark box + lit ceiling strip
        U.box(B, a, 44.0, zg - 0.5, b, y_f, zg + 8.6, 'wall_concrete', c0=(36, 34, 34, 0), faces='YxXz')
        U.box(B, a + 1.5, y_f - 6.7, zg + 8.2, b - 1.5, y_f - 6.6, zg + 8.45, 'lamp', faces='Y', tag='main')
        B.lamp((a + b) / 2, y_f - 3.0, zg + 7.0, 140, (1.0, 0.85, 0.65))
    # ribbon windows on the podium face (z 11..18)
    north_grid(B, px0 + 2.0, px1 - 1.0, y_f + 0.05, zg + 10.0, zg + 18.4, 3.1, 2.8, zg=zg, glass='glass', frame='metal_grey', mw=0.15, md=0.2,
               bands=[(0.0, 0.9, 'wall_concrete', 0.3), (2.8, 3.7, 'wall_concrete', 0.3), (5.6, 6.5, 'wall_concrete', 0.3)], frame_kw=dict(c0=(150, 152, 156, 0)))
    wprog(B, (px1, 36.0), (px1, y_f), zg - 0.6, z_pod, zg, 'wall_concrete', (148, 150, 154), 4.0, 0, seed=41)
    roof(B, [(px0, 36.0), (px1, 36.0), (px1, y_f), (px0, y_f)], z_pod, zg, (130, 128, 124), 1.0)
    # the hotel's long low canopy in front with thin columns (OSM: x 73..151, y 50..62), and flag poles
    cy0, cy1 = 51.0, 62.0
    U.box(B, 73.5, cy0, zg + 5.2, 150.0, cy1, zg + 5.65, 'white_paint', c0=(210, 210, 206, 0))
    for x in np.arange(76.0, 150.0, 8.0):
        prim.cyl(B, (x, cy1 - 0.6, zg), (x, cy1 - 0.6, zg + 5.2), 0.22, 0.22, 8, 'metal_grey', caps=(False, False))
    for x in (92.0, 96.0, 100.0, 104.0):
        prim.cyl(B, (x, 53.4, zg + 5.65), (x, 53.4, zg + 17.0), 0.07, 0.04, 5, 'metal_grey', tag='detail')
    B.lamp(102, 55.5, zg + 4.6, 100, (1.0, 0.85, 0.65))
    B.lamp(84, 55.5, zg + 4.6, 100, (1.0, 0.85, 0.65))
    # sign band over the central portal
    U.box(B, 87.0, y_f + 0.02, zg + 9.2, 113.0, y_f + 0.1, zg + 10.4, 'white_paint', c0=(235, 235, 235, 0), tag='main')
    U.box(B, 88.0, y_f + 0.1, zg + 9.5, 112.0, y_f + 0.14, zg + 10.1, 'metal_dark', tag='detail')
    # faceted glass dome on the podium roof
    dome(B, 114.0, 43.0, z_pod, 17.0, 6.5, 10.5, sub=2)
    # ---- the tower of the hotel (set back): x 73..204, y -16..36, z 60
    z_t = zg + 60.0
    tx0 = xa
    # north face: balcony program on the concrete part (x 73..110) and blue glass elsewhere
    wprog(B, (110.0, 36.0), (px0, 36.0), z_pod, z_t, zg, 'wall_concrete', (150, 152, 156), 3.4, 3, seed=50)
    wprog(B, (204.0, 36.0), (110.0, 36.0), z_pod, z_t, zg, 'glass_curtain', GLASS_T, 3.4, 2, seed=51)
    wprog(B, (204.0, -16.0), (204.0, 36.0), zg - 0.6, z_t, zg, 'glass_curtain', GLASS_T, 3.4, 2, seed=52)
    wprog(B, (tx0, -16.0), (204.0, -16.0), zg - 0.6, z_t, zg, 'glass_curtain', GLASS_T, 3.4, 2, seed=53)
    wprog(B, (tx0, 36.0), (tx0, -16.0), zg - 0.6, z_t, zg, 'glass_curtain', GLASS_T, 3.4, 2, seed=54)
    # east part of the north face below the podium level (x 151..204): same program from the ground up
    wprog(B, (204.0, 36.0), (151.0, 36.0), zg - 0.6, z_pod, zg, 'glass_curtain', GLASS_T, 3.4, 2, seed=55, flags=4)
    roof(B, [(tx0, -16.0), (204.0, -16.0), (204.0, 36.0), (tx0, 36.0)], z_t, zg, (128, 126, 120), 1.2)
    # roof equipment: the two raised blocks, the helipad and a few plant rooms
    penthouse(B, 80.0, 6.0, 96.0, 20.0, z_t, 4.2, tint=(150, 152, 156))
    penthouse(B, 100.0, 22.0, 120.0, 32.0, z_t, 2.6, tint=(160, 160, 158))
    penthouse(B, 160.0, 10.0, 178.0, 26.0, z_t, 3.4, tint=(150, 152, 156))
    U.box(B, 124.0, 6.0, z_t + 0.03, 146.0, 28.0, z_t + 0.06, 'cloth', c0=(70, 130, 90, 0))        # heliport pad
    for (x0_, y0_, x1_, y1_) in ((131.0, 14.0, 132.4, 20.0), (137.6, 14.0, 139.0, 20.0), (131.0, 16.3, 139.0, 17.7)):
        U.box(B, x0_, y0_, z_t + 0.06, x1_, y1_, z_t + 0.1, 'white_paint', c0=(235, 235, 235, 0))
    # the Karasuma-side annex (east wing): lower block
    return zg

# ================================================================================================ west wing, stair hall, back
def build_west(B, S):
    zg = zmin(S, -256, -22, -62, 34)
    z_w = zg + 59.0
    # ---- the Isetan wing: x -256..-101 (north face y=27), plus x -101..-62 behind the blue tower (z 59)
    xw0, xw1 = -256.0, -62.0
    # wedge-shaped terrace of the stair hall cut out of the roof: x -140..-64, y 3..21
    wd = [(-140.0, 3.0), (-64.0, 3.0), (-64.0, 21.0), (-140.0, 21.0)]
    z_t = zg + 16.7
    # north face (plaza side): panel + ribbon windows, shop fronts, lit windows at dusk
    # (the north face is drawn by build_facades with real ribbons)
    # west and south
    wprog(B, (xw0, 27.0), (xw0, -22.0), zg - 0.6, z_w, zg, 'wall_concrete', (188, 194, 202), 4.2, 2, seed=62, flags=8)
    wprog(B, (xw0, -22.0), (xw1, -22.0), zg - 0.6, z_w, zg, 'wall_concrete', (188, 194, 202), 4.2, 2, seed=63, flags=8)
    wprog(B, (xw1, -22.0), (xw1, 34.0), zg - 0.6, z_w, zg, 'wall_concrete', (188, 194, 202), 4.2, 2, seed=64)
    wprog(B, (-101.0, 34.0), (-101.0, 27.0), zg - 0.6, z_w, zg, 'wall_concrete', (188, 194, 202), 4.2, 2, seed=69)
    # roof with a hole for the stair terrace
    outer = [(xw0, -22.0), (xw1, -22.0), (xw1, 34.0), (-101.0, 34.0), (-101.0, 27.0), (xw0, 27.0)]
    U.flat(B, outer, z_w + 0.02, 'roof_flat', up=True, holes=[wd], c0=(118, 116, 110, 0))
    U.wall_ring(B, outer, z_w, z_w + 1.0, 'wall_concrete', zg=zg, c0=(150, 150, 148, 0))
    # stair terrace: floor, inner walls
    U.flat(B, wd, z_t + 0.02, 'roof_flat', up=True, c0=(130, 128, 122, 0))
    wprog(B, (-140.0, 21.0), (-64.0, 21.0), z_t, z_w, zg, 'wall_concrete', (188, 194, 202), 4.2, 2, seed=65)      # faces south (into the hole) -- walked west->east: outward = south? fixed below
    wprog(B, (-64.0, 3.0), (-140.0, 3.0), z_t, z_w, zg, 'wall_concrete', (188, 194, 202), 4.2, 2, seed=66)
    wprog(B, (-140.0, 3.0), (-140.0, 21.0), z_t, z_w, zg, 'wall_concrete', (188, 194, 202), 4.2, 2, seed=67)
    wprog(B, (-64.0, 21.0), (-64.0, 3.0), z_t, z_w, zg, 'wall_concrete', (188, 194, 202), 4.2, 2, seed=68)
    stair_hall(B, S, zg, z_t)
    # a wavy white tower of the Isetan wing next to the blue tower (curved fins)
    th = np.linspace(0, 2 * math.pi, 49)[:-1]
    rr = 6.8 + 0.7 * np.sin(th * 6)
    ring = np.stack([-109.0 + rr * np.cos(th) * 1.0, 32.0 + rr * 0.85 * np.sin(th)], 1)
    # only the north half is visible: still build the full prism
    prim.prism(B, ring, zg + 20.0, zg + 53.0, 'wall_metal', top=True, c0=(226, 230, 234, 0), c1=(0, 0, 0, 0))
    # roof equipment
    for (x0_, y0_, x1_, y1_, h) in ((-240.0, -12.0, -222.0, 4.0, 3.5), (-215.0, 8.0, -190.0, 18.0, 4.2), (-180.0, -14.0, -160.0, 2.0, 3.0), (-150.0, 10.0, -141.0, 26.0, 5.0), (-120.0, -14.0, -100.0, 2.0, 3.2)):
        penthouse(B, x0_, y0_, x1_, y1_, z_w, h, tint=(170, 174, 180))
    # the west end block (low)
    block(B, S, -271.0, -16.0, -256.0, 14.0, zg + 22.0, tint=(188, 194, 202), fh=4.2, ws=2, zb=zg, seed=70)
    return zg

def stair_hall(B, S, zg, z_t):
    """大階段 hall: a sloped glass roof rising westward over the stair (171 steps, 35 m rise)"""
    xe, xw = -64.0, -134.0
    y0, y1 = 6.0, 18.0
    z_e = z_t + 0.5; z_w = z_t + 26.0
    L = math.hypot(xe - xw, z_w - z_e)
    Vv = U.unit([xw - xe, 0, z_w - z_e])                 # up-slope = toward the west
    # outward normal = U x V; U along +y gives N = y x (-x,z) ... choose U so that N points up
    Uv = np.array([0.0, 1.0, 0.0]); N = np.cross(Uv, Vv)
    if N[2] < 0: Uv = -Uv
    O = np.array([xe, y0 if Uv[1] > 0 else y1, z_e])
    U.plane_grid(B, O, Uv, Vv, y1 - y0, L, 2.2, 2.4, glass='glass', frame='metal_grey', mw=0.11, md=0.14, tw=0.08, td=0.1)
    # side walls (triangles) in light panels
    for yy, out in ((y0, -1), (y1, 1)):
        P = np.array([[xe, yy, z_t], [xw, yy, z_t], [xw, yy, z_w], [xe, yy, z_e]])
        U.plane_poly(B, P, 'wall_concrete', normal=(0, out, 0), cell=6.0, c0=(188, 194, 202, 42))
    # the high end wall (west) of the hall
    U.box(B, xw - 0.6, y0, z_t, xw, y1, z_w, 'wall_concrete', c0=(188, 194, 202, 42))

# ================================================================================================ the middle, the back, the south strip
def build_middle(B, S):
    zg = zmin(S, -62, -16, 58, 36)
    # south of the notch tower and of the atrium glass: lower roofs
    block(B, S, -62.0, -16.0, -30.0, 20.0, zg + 46.6, tint=(160, 164, 170), fh=4.2, ws=2, zb=zg, seed=80)
    block(B, S, -30.0, -16.0, 58.0, 10.0, zg + 33.0, tint=(160, 164, 170), fh=4.2, ws=2, sides='sew', zb=zg, seed=81)
    # the notch tower's south part + the atrium's south wall (seen from the air only)
    # the blue tower's south block: z 59 up to y -22 (covered by build_west)
    # south strip: the long Hachijo-side low block
    block(B, S, -256.0, -29.0, 206.0, -22.0, zg + 17.4, tint=(180, 184, 190), fh=4.0, ws=2, zb=zg, seed=82)
    block(B, S, -62.0, -22.0, -30.0, -16.0, zg + 17.4, tint=(180, 184, 190), fh=4.0, ws=2, zb=zg, seed=83, ztop_roof=False)
    block(B, S, 58.0, -22.0, 204.0, -16.0, zg + 17.4, tint=(180, 184, 190), fh=4.0, ws=2, zb=zg, seed=84, ztop_roof=False)
    return zg

# ================================================================================================ ribbon facades (real geometry)
def ribbon_facade(B, p0, p1, z0, z1, zg, fh=4.2, pitch=3.6, tint=(190, 196, 204), first=1, gl0=1.2, gl1=1.1, flags=8, seed=0, frame='metal_grey', fins=0.0):
    """spandrel wall (viewer wall program) + inset glass ribbons per floor + mullions; outward = right of p0 -> p1"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L
    n = np.array([d[1], -d[0]])
    wprog(B, p0, p1, z0, z1, zg, 'wall_concrete', tint, fh, 0, seed=seed, flags=flags)
    nfl = int((z1 - z0 - first * fh) / fh)
    nc = max(1, int(round(L / pitch)))
    ts = np.linspace(0, L, nc + 1)
    gl_a = []; gl_b = []; zlo = []; zhi = []
    mp0 = []; mp1 = []
    for f in range(first, first + nfl):
        zf = z0 + f * fh
        za, zb = zf + gl0, zf + fh - gl1
        a = p0 + n * 0.07; b = p1 + n * 0.07
        gl_a.append(a); gl_b.append(b); zlo.append(za); zhi.append(zb)
        for t in ts:
            c = p0 + d * t + n * 0.12
            mp0.append((c[0], c[1], za)); mp1.append((c[0], c[1], zb))
        # sill / head bars
        for zz in (za, zb):
            mp0.append((*(p0 + n * 0.12), zz)); mp1.append((*(p1 + n * 0.12), zz))
    if gl_a:
        U.vquads(B, np.array(gl_a), np.array(gl_b), np.array(zlo), np.array(zhi), 'glass', zg=zg)
        P0 = np.array(mp0); P1 = np.array(mp1)
        vert = np.abs(P1[:, 2] - P0[:, 2]) > 0.5
        nn = np.r_[n, 0.0]
        U.obox_batch(B, P0[vert], P1[vert], 0.1, 0.12, frame, up=nn, tag='detail')
        U.obox_batch(B, P0[~vert], P1[~vert], 0.1, 0.1, frame, up=(0, 0, 1), tag='detail')
    if fins > 0:
        for t in np.arange(fins / 2, L, fins):
            c = p0 + d * t
            U.obox_batch(B, np.array([[c[0] + n[0] * 0.3, c[1] + n[1] * 0.3, z0]]), np.array([[c[0] + n[0] * 0.3, c[1] + n[1] * 0.3, z1]]), 1.0, 0.6, 'wall_concrete', up=np.r_[n, 0.0], tag='main', c0=(*tint, 42))

def build_facades(B, S):
    """replace the flat programs on the most visible big faces by real ribbon / curtain geometry"""
    zg = zmin(S, -256, -22, 204, 36)
    # Isetan wing north face (y = 27): the face is drawn by build_west as a flat wall; here the real ribbons on top
    ribbon_facade(B, (-101.0, 27.0 + 0.0), (-256.0, 27.0), zg, zg + 59.0, zg, fh=4.15, pitch=3.7, tint=(190, 196, 204), first=1, flags=12, seed=61, fins=18.5)
    # Hotel Granvia: glass wall above the podium and the east wing's face
    north_grid(B, 110.0, 204.0, 36.1, zg + 19.0, zg + 60.0, 3.2, 3.4, zg=zg, glass='glass', frame='metal_dark')
    north_grid(B, 151.0, 204.0, 36.1, zg + 0.6, zg + 19.0, 3.2, 4.6, zg=zg, glass='glass', frame='metal_dark')
    east_grid(B, -16.0, 36.0, 204.1, zg + 0.6, zg + 60.0, 3.2, 3.4, zg=zg, glass='glass', frame='metal_dark')
    west_grid(B, -22.0, 27.0, -256.1, zg + 0.6, zg + 59.0, 3.6, 4.15, zg=zg, glass='glass', frame='metal_grey')

# ================================================================================================ the Kyoto Station Building: lit details
def evening_lights(B, S):
    zg = zmin(S, -105, 20, 60, 60)
    # glow of the great screen, the gate and the podium shops
    for x in np.arange(-24.0, 56.0, 20.0):
        B.lamp(x, 50.0, zg + 24.0, 220, (0.75, 0.85, 1.0))
    B.lamp(-47.0, 58.0, zg + 6.5, 200, (1.0, 0.9, 0.75))
    for x in (-90.0, -76.0, -64.0):
        B.lamp(x, 62.0, zg + 5.0, 120, (1.0, 0.85, 0.65))
