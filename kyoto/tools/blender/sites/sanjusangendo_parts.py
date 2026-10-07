"""三十三間堂: shared plan constants and helpers (double-sided wall pieces, blocker strips, a hall roof with a cut for
the 向拝, a lean-to porch roof, small generic temple buildings).

Hall frame (Frame in sanjusangendo.py): u along the hall axis, +u = north (2° east of north), v across, +v = WEST
(the back, 通し矢 side), -v = EAST (the front, 向拝, garden); z = 0 at the veranda deck (FL)."""
import math
import numpy as np
from jk import prim, roof as jroof

# ------------------------------------------------------------------ plan (metres, hall frame)
NB = 35                                  # 桁行三十五間 (33 inner bays + one 庇 bay at each end)
BAY = 118.2 / NB                         # 3.377 m (S11: 118.2 m column to column)
UL = np.array([-59.1 + k * BAY for k in range(NB + 1)])          # pillar lines along the hall
VL = np.array([-8.2, -4.7, -1.5667, 1.5667, 4.7, 8.2])          # 梁間五間: 庇 3.5 + 身舎 3 x 3.13 + 庇 3.5
UO, VO = 59.1, 8.2                       # outer pillar rectangle (half sizes)
VI = 4.7                                 # 身舎 (inner) pillar lines
H_OUT = 4.45                             # outer pillar top (頭貫 top) above FL
H_IN = 6.2                               # inner pillar top
FLI = 0.06                               # interior floor above the veranda deck
VER = 2.2                                # veranda width outside the pillar line
UC = 5.07                                # half width of the central 3 bays (内々陣)
US0, US1 = 5.30, 55.50                   # standing-Kannon stage span per side (|u|)

WOOD = 'wood_dark'
PLASTER = dict(c0=(236, 232, 222, 35))

def bay_mid(k):
    return 0.5 * (UL[k] + UL[k + 1])

# ------------------------------------------------------------------ simple geometry helpers
def slab(B, x0, y0, x1, y1, z0, z1, mat, tag='main', **kw):
    """an axis-aligned box in the current frame (sorted corners)"""
    prim.box(B, min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1), mat, tag=tag, **kw)

def quad(B, p0, p1, p2, p3, mat, tag='main', uv=None, **kw):
    P = np.array([p0, p1, p2, p3], float)
    B.add(P, [[0, 1, 2], [0, 2, 3]], mat, UV=uv, tag=tag, **kw)

def quad2(B, p0, p1, p2, p3, mat, tag='main', **kw):
    """a double-sided quad"""
    P = np.array([p0, p1, p2, p3], float)
    B.add(P, [[0, 1, 2], [0, 2, 3]], mat, tag=tag, **kw)
    B.add(P, [[0, 2, 1], [0, 3, 2]], mat, tag=tag, **kw)

def walk_rect(B, x0, y0, x1, y1, z):
    prim.polygon(B, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z, 'stone', tag='walk')

def walk_poly(B, pts, z):
    prim.polygon(B, pts, z, 'stone', tag='walk')

def block_rect(B, x0, y0, x1, y1, z=0.0):
    """a blocker: rasterised in plan, so it must have area (≥ 0.5 m wide to hit a 0.5 m cell centre)"""
    prim.polygon(B, [(min(x0, x1), min(y0, y1)), (max(x0, x1), min(y0, y1)), (max(x0, x1), max(y0, y1)), (min(x0, x1), max(y0, y1))], z, 'stone', tag='block')

def block_line(B, pts, z=0.0, w=0.6):
    """a blocker strip along a 2D polyline"""
    pts = [np.asarray(p, float) for p in pts]
    for a, b in zip(pts[:-1], pts[1:]):
        d = b - a; L = np.linalg.norm(d)
        if L < 1e-6: continue
        d /= L; n = np.array([-d[1], d[0]]) * w / 2
        a2 = a - d * w / 2; b2 = b + d * w / 2
        P = np.array([np.r_[a2 - n, z], np.r_[b2 - n, z], np.r_[b2 + n, z], np.r_[a2 + n, z]])
        B.add(P, [[0, 1, 2], [0, 2, 3]], 'stone', tag='block')

def arch_beam(B, p0, p1, z, w, h, rise, mat=WOOD, tag='main', n=8):
    """虹梁: a beam between two 2D points at height z (centre of its bottom), with an arched (rainbow) camber"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    pts = []
    for t in np.linspace(0, 1, n + 1):
        q = p0 + (p1 - p0) * t
        pts.append((q[0], q[1], z + rise * math.sin(math.pi * t) ** 0.7))
    prim.sweep(B, np.array(pts), [(-w / 2, 0.0), (w / 2, 0.0), (w / 2, h * 0.85), (w * 0.35, h), (-w * 0.35, h), (-w / 2, h * 0.85)], mat, tag=tag, caps=True)

def kaerumata(B, x, y, z, w, h, along, mat=WOOD, tag='detail', th=0.12):
    """蟇股: a frog-leg strut (two curved legs + a block on top), in the plane spanned by `along` (2D) and z"""
    a = np.array([along[0], along[1], 0.0]); a /= np.linalg.norm(a)
    n = np.array([-a[1], a[0], 0.0])
    c = np.array([x, y, z])
    pts = []
    for t in np.linspace(-1, 1, 13):
        xx = t * w / 2
        zz = h * 0.72 * (1 - abs(t) ** 1.6) ** 0.8
        pts.append(c + a * xx + [0, 0, zz])
    pts = np.array(pts)
    prim.sweep(B, pts, [(-th / 2, -0.06), (th / 2, -0.06), (th / 2, 0.06), (-th / 2, 0.06)], mat, up=tuple(n), tag=tag)
    prim.obox(B, c + [0, 0, h * 0.72], c + [0, 0, h], w * 0.22, th * 1.4, mat, up=tuple(a), tag=tag)
    prim.obox(B, c + [0, 0, h * 0.86] - a * w * 0.18, c + [0, 0, h * 0.86] + a * w * 0.18, th * 1.6, h * 0.28, mat, tag=tag)

# ------------------------------------------------------------------ the main roof: irimoya with a cut on the front for the 向拝
class HallRoof(jroof.Roof):
    """jroof.Roof (irimoya) whose front side (side 0, v-) is cut between u0 and u1 below the inward depth s_cut:
    the lower part there is replaced by the 向拝 roof (葺き降ろし), built separately with porch_roof()."""
    def __init__(self, *a, cut=None, gutter=False, **kw):
        super().__init__(*a, **kw)
        self.cut = cut
        self.gutter = gutter

    def surf_z(self, s, dc=1e9):
        return float(self.z(s, dc))

    def slope(self, s):
        """dz/ds of the roof surface at inward depth s (away from corners)"""
        return self.H * self.teri * (max(s, 1e-6) / self.c) ** (self.teri - 1) / self.c

    def build(self, B):
        assert self.kind == 'irimoya'
        a, c, o = self.a, self.c, self.o
        sg = self.sg; vo = self.verge
        skirt = lambda xs_, dc_: np.minimum(np.minimum(dc_, c), sg)
        out = dict(z_edge=self.zE0, z_ridge=float(self.z(c, c)))
        for k in range(4):
            E = self.sides()[k][3]
            if k == 0 and self.cut:
                u0, u1, s_cut = self.cut
                xa, xb = u0 + a, u1 + a
                self.face(B, 0, x0=0.0, x1=xa, smax=skirt, nu=max(4, int(xa / 0.6)))
                self.face(B, 0, x0=xb, x1=E, smax=skirt, nu=max(4, int((E - xb) / 0.6)))
                self.face(B, 0, x0=xa, x1=xb, s0=s_cut, smax=skirt, nu=max(4, int((xb - xa) / 0.6)), nt=max(4, int((sg - s_cut) / 0.5)))
                self.eave(B, 0, 0.0, xa); self.eave(B, 0, xb, E)
            else:
                self.face(B, k, smax=skirt)
                self.eave(B, k, 0.0, E)
        u_g = a - sg
        for k in (0, 2):
            E = self.sides()[k][3]
            self.face(B, k, x0=sg - vo, x1=E - sg + vo, s0=sg, smax=lambda xs_, dc_: np.full_like(xs_, c), nu=max(6, int(2 * u_g / 0.6)))
        zr = float(self.z(c, c))
        self.ridge(B, [(-(u_g + vo), 0, zr), (u_g + vo, 0, zr)], self.ridge_w, self.ridge_h, ends=(self.ends, self.ends))
        self.gable(B, u_g, sg, vo)
        if self.hip:
            for k in range(4):
                hl = self.hip_line(k, sg * 0.97)
                self.ridge(B, hl[1:][::-1], self.ridge_w * 0.6, self.ridge_h * 0.55, ends=(None, 'oni' if self.ends else None))
        out['z_ridge'] = zr; out['z_break'] = float(self.z(sg, sg)); out['u_gable'] = u_g
        return out

def _gable_fixed(self, B, u_g, s_from, vo):
    """jroof.Roof.gable with the bargeboards (破風) and verge tiles standing upright (sweep up = z)"""
    c = self.c
    ss = np.linspace(s_from, c, 12)
    for sgn in (-1, 1):
        u = sgn * u_g
        zb = float(self.z(s_from, s_from)) - 0.05
        Pw = []
        for s in ss: Pw.append((u, -c + s, float(self.z(s, c)) - self.edge - 0.05))
        for s in ss[::-1][1:]: Pw.append((u, c - s, float(self.z(s, c)) - self.edge - 0.05))
        Pw = np.array(Pw)
        poly = np.concatenate([Pw, np.array([(u, Pw[-1][1], zb), (u, Pw[0][1], zb)])])
        cen = np.array([u, 0.0, zb])
        Pall = np.concatenate([[cen], poly]); n = len(poly)
        I = [[0, 1 + j, 1 + (j + 1) % n] for j in range(n)]
        fn = np.cross(Pall[I[0][1]] - Pall[0], Pall[I[0][2]] - Pall[0])
        if fn[0] * sgn < 0: I = [t[::-1] for t in I]
        B.add(Pall, I, self.gable_wall, UV=np.c_[Pall[:, 1], Pall[:, 2]], tag=self.tag, c0=(150, 140, 125, 35))
        ue = u + sgn * vo
        for side in (-1, 1):
            pts = np.array([(ue, side * (c - s), float(self.z(s, c)) - self.edge * 0.55) for s in ss])
            prim.sweep(B, pts, [(-0.07, 0.0), (0.07, 0.0), (0.07, -0.5), (-0.07, -0.5)], self.bargeboard_mat, up=(0, 0, 1), tag=self.tag, caps=True)
            pe = np.array([(ue, side * (c - s), float(self.z(s, c))) for s in ss])
            prim.sweep(B, pe, [(-0.18, -self.edge * 0.6), (0.18, -self.edge * 0.6), (0.18, 0.05), (-0.18, 0.05)], self.mat, up=(0, 0, 1), tag=self.tag, caps=True)
            # the soffit of the verge overhang (board between the gable wall and the bargeboard)
            pin = np.array([(u, side * (c - s), float(self.z(s, c)) - self.edge - 0.03) for s in ss])
            for j in range(len(ss) - 1):
                quad2(B, pin[j], pin[j + 1], pe[j + 1] - [0, 0, self.edge + 0.03], pe[j] - [0, 0, self.edge + 0.03], self.bargeboard_mat, tag=self.tag)
            self.ridge(B, pe[::-1] + np.array([-sgn * 0.3, 0, 0.02]), self.ridge_w * 0.55, self.ridge_h * 0.5, ends=(None, 'oni' if self.ends else None))
        # 懸魚 under the apex (both faces)
        za = float(self.z(c, c)) - self.edge - 0.55
        gp = [(-0.5, 0.3), (0.5, 0.3), (0.4, -0.4), (0.0, -0.75), (-0.4, -0.4)]
        Pk = np.array([(ue + sgn * 0.08, y, za + z) for (y, z) in gp])
        I = [[0, 1, 2], [0, 2, 3], [0, 3, 4]]
        B.add(Pk, I, 'white_paint', tag='detail'); B.add(Pk + [sgn * 0.04, 0, 0], [t[::-1] for t in I], 'white_paint', tag='detail')

HallRoof.gable = _gable_fixed

def gutter(B, pts, r=0.09, mat='copper', tag='detail'):
    """軒樋: a half-round copper gutter along a 3D polyline (open at the top)"""
    prof = [(r * math.cos(t), -r * math.sin(t)) for t in np.linspace(0, math.pi, 7)]
    prim.sweep(B, np.asarray(pts, float), prof, mat, closed=False, tag=tag)
    prim.sweep(B, np.asarray(pts, float), [(x * 0.92, y * 0.92) for (x, y) in prof][::-1], mat, closed=False, tag=tag)

# ------------------------------------------------------------------ a lean-to roof (向拝, galleries' outer roofs)
def lean_to(B, x0, x1, v_top, z_top, v_eave, slope, cover='hongawara', rafter=0.32, rafter_mat=WOOD, verge=True, edge=0.3,
            tile_ends=True, soffit_to=None, z_soffit_top=None, tag='main'):
    """a mono-pitch tiled roof between u = x0..x1 (hall frame), from the line v_top (height z_top) down to the eave
    line v_eave (either side) at `slope` (dz per m).  Rafters, eave edge with round tile ends, soffit back to
    v = soffit_to at z_soffit_top, verges (破風) at both ends.  Returns the eave edge height."""
    mat = jroof.COVER_MAT[cover]
    sgn = 1.0 if v_eave > v_top else -1.0
    run = abs(v_eave - v_top)
    z_e = z_top - slope * run
    Ls = run * math.sqrt(1 + slope * slope)
    nu = max(2, int((x1 - x0) / 0.6)); nv = max(2, int(run / 0.5))
    us = np.linspace(x0, x1, nu + 1); ts = np.linspace(0, 1, nv + 1)
    Pg = np.array([(u, v_top + sgn * run * t, z_top - slope * run * t) for t in ts for u in us])
    UVg = np.array([(u, Ls * (1 - t)) for t in ts for u in us])
    I = []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            I += [[a, a + nu + 2, a + 1], [a, a + nu + 1, a + nu + 2]] if sgn > 0 else [[a, a + 1, a + nu + 2], [a, a + nu + 2, a + nu + 1]]
    I = np.array(I)
    fn = np.cross(Pg[I[:, 1]] - Pg[I[:, 0]], Pg[I[:, 2]] - Pg[I[:, 0]])
    if fn[:, 2].sum() < 0: I = I[:, ::-1]
    B.add(Pg, I, mat, UV=UVg, smooth=True, tag=tag)
    # eave edge: the tile layer and the fascia
    th = edge
    for (za, zb, m) in ((z_e, z_e - th * 0.45, mat), (z_e - th * 0.45, z_e - th, rafter_mat)):
        quad2(B, (x0, v_eave, za), (x1, v_eave, za), (x1, v_eave, zb), (x0, v_eave, zb), m, tag=tag)
    if tile_ends and cover == 'hongawara':
        for x in np.arange(x0 + 0.15, x1 - 0.05, 0.3):
            pc = np.array([x, v_eave, z_e - 0.06])
            prim.cyl(B, pc - [0, sgn * 0.25, -0.04], pc + [0, sgn * 0.03, 0], 0.085, None, 8, mat, caps=(False, True), tag='detail')
    # soffit + rafters
    if soffit_to is not None:
        zs0 = z_e - th; zs1 = z_soffit_top
        quad2(B, (x0, v_eave, zs0), (x1, v_eave, zs0), (x1, soffit_to, zs1), (x0, soffit_to, zs1), rafter_mat, tag=tag)
        if rafter:
            for x in np.arange(x0 + rafter / 2, x1, rafter):
                q0 = np.array([x, v_eave - sgn * 0.02, zs0 - 0.05]); q1 = np.array([x, soffit_to, zs1 - 0.05])
                prim.obox(B, q0, q1, 0.08, 0.1, rafter_mat, tag='detail')
                e = q0 + (q1 - q0) / np.linalg.norm(q1 - q0) * 0.03
                prim.obox(B, q0 - (q1 - q0) / np.linalg.norm(q1 - q0) * 0.005, e, 0.082, 0.102, 'white_paint', tag='detail')
    if verge:
        for x in (x0, x1):
            pts = np.array([(x, v_top, z_top - th * 0.6), (x, v_eave, z_e - th * 0.6)])
            prim.sweep(B, pts, [(-0.06, 0.0), (0.06, 0.0), (0.06, -0.42), (-0.06, -0.42)], rafter_mat, up=(0, 0, 1), tag=tag, caps=True)
            pts2 = np.array([(x, v_top, z_top + 0.02), (x, v_eave, z_e + 0.02)])
            prim.sweep(B, pts2, [(-0.16, -0.18), (0.16, -0.18), (0.16, 0.1), (-0.16, 0.1)], 'ridge', up=(0, 0, 1), tag=tag, caps=True)
    return z_e

# ------------------------------------------------------------------ doors and windows (double sided)
def plank_leaf(B, hinge, along, out, w, z0, z1, ang, mat=WOOD, th=0.08):
    """one leaf of a plank door (板扉) hinged at the 2D point `hinge`, closing along `along`, opening `ang` radians toward `out`"""
    h = np.asarray(hinge, float); a = np.asarray(along, float); o = np.asarray(out, float)
    d = a * math.cos(ang) + o * math.sin(ang)
    n = np.array([-d[1], d[0]])
    p0 = h; p1 = h + d * w
    prim.obox(B, np.r_[p0, (z0 + z1) / 2], np.r_[p1, (z0 + z1) / 2], th, z1 - z0, mat, up=(0, 0, 1), tag='main')
    # battens (端喰 / 桟) on the face
    for zz in np.linspace(z0 + 0.35, z1 - 0.35, 3):
        for s in (-1, 1):
            q = n * s * (th / 2 + 0.02)
            prim.obox(B, np.r_[p0 + d * 0.06 + q, zz], np.r_[p1 - d * 0.06 + q, zz], 0.04, 0.12, mat, tag='detail')
    # studs (乳金物): a few dark metal bosses
    for zz in (z0 + 0.35, z1 - 0.35):
        for s in (-1, 1):
            q = n * s * (th / 2 + 0.05)
            prim.cyl(B, np.r_[p0 + d * 0.25 + q - n * s * 0.03, zz], np.r_[p0 + d * 0.25 + q, zz], 0.05, 0.03, 6, 'metal_dark', tag='detail')

def shoji(B, p0, p1, z0, z1, th=0.05):
    """障子: a white paper panel with a dark lattice frame (both faces), between the 2D points p0, p1"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L; n = np.array([-d[1], d[0]])
    prim.obox(B, np.r_[(p0 + p1) / 2, (z0 + z1) / 2], np.r_[(p0 + p1) / 2 + d * 0.001, (z0 + z1) / 2], th * 0.5, z1 - z0, 'white_paint', tag='main')
    prim.obox(B, np.r_[p0, (z0 + z1) / 2], np.r_[p1, (z0 + z1) / 2], th * 0.4, z1 - z0, 'white_paint', up=(0, 0, 1), tag='main')
    for s in (-1, 1):
        q = n * s * th * 0.4
        for zz in (z0 + 0.03, z1 - 0.03, z0 + 0.6):
            prim.obox(B, np.r_[p0 + q, zz], np.r_[p1 + q, zz], 0.03, 0.06, WOOD, tag='detail')
        for t in (0.02, L - 0.02):
            pp = p0 + d * t + q
            prim.obox(B, np.r_[pp, z0], np.r_[pp, z1], 0.05, 0.03, WOOD, tag='detail', up=(d[0], d[1], 0))
        for zz in np.arange(z0 + 0.9, z1 - 0.1, 0.32):
            prim.obox(B, np.r_[p0 + q, zz], np.r_[p1 + q, zz], 0.015, 0.02, WOOD, tag='detail')

def renji(B, p0, p1, z0, z1, th=0.12, step=0.11, mat=WOOD):
    """連子窓: an open window of close vertical square bars in a frame (both faces visible)"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L
    for zz in (z0 + 0.05, z1 - 0.05):
        prim.obox(B, np.r_[p0, zz], np.r_[p1, zz], th, 0.1, mat, tag='main')
    for t in np.arange(step / 2, L, step):
        q = p0 + d * t
        prim.obox(B, np.r_[q, z0 + 0.1], np.r_[q, z1 - 0.1], 0.045, 0.045, mat, tag='detail', ends=False, up=(d[0], d[1], 0))

def lattice(B, p0, p1, z0, z1, cell=0.16, bar=0.035, mat=WOOD, th=0.06):
    """格子戸: a square lattice (both directions) in a frame"""
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    d = p1 - p0; L = np.linalg.norm(d); d /= L
    for zz in (z0 + 0.05, z1 - 0.05):
        prim.obox(B, np.r_[p0, zz], np.r_[p1, zz], th, 0.1, mat, tag='main')
    for t in (0.04, L - 0.04):
        q = p0 + d * t
        prim.obox(B, np.r_[q, z0], np.r_[q, z1], 0.08, th, mat, tag='main', up=(d[0], d[1], 0))
    for t in np.arange(cell, L - 0.05, cell):
        q = p0 + d * t
        prim.obox(B, np.r_[q, z0 + 0.1], np.r_[q, z1 - 0.1], bar, bar, mat, tag='detail', ends=False, up=(d[0], d[1], 0))
    for zz in np.arange(z0 + cell, z1 - 0.1, cell):
        prim.obox(B, np.r_[p0, zz], np.r_[p1, zz], bar, bar, mat, tag='detail', ends=False)

# ------------------------------------------------------------------ a small generic temple building (for minor halls)
def small_hall(B, L, D, H, kind='irimoya', cover='hongawara', o=1.4, wood=WOOD, wall='plaster', pitch=0.6, z0=0.0, base=0.45, nu=None, nv=None,
               bracket='funa', rafter_mat=None, rafter_end=None, ends='oni', front='karado', walls=True, ridge_h=None):
    """a hall in the current frame centred at the origin: stone base, pillars, wall infills, nageshi, brackets, roof.
    Returns the roof heights."""
    from jk import arch
    nu = nu or max(1, int(round(L / 3.0))); nv = nv or max(1, int(round(D / 3.0)))
    zb = z0 + base
    arch.platform(B, [(-L / 2 - 0.9, -D / 2 - 0.9), (L / 2 + 0.9, -D / 2 - 0.9), (L / 2 + 0.9, D / 2 + 0.9), (-L / 2 - 0.9, D / 2 + 0.9)], z0 - 0.4, zb)
    us, vs = arch.grid(L, D, nu, nv)
    for x in us:
        for y in (vs[0], vs[-1]): arch.pillar(B, x, y, zb, zb + H, 0.18, wood)
    for y in vs[1:-1]:
        for x in (us[0], us[-1]): arch.pillar(B, x, y, zb, zb + H, 0.18, wood)
    if walls:
        def wallpiece(p0, p1, kind_):
            p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
            d = p1 - p0; Lw = np.linalg.norm(d); d /= Lw
            q0 = p0 + d * 0.18; q1 = p1 - d * 0.18
            if kind_ == 'plaster':
                prim.obox(B, np.r_[q0, zb + (H - 0.3) / 2], np.r_[q1, zb + (H - 0.3) / 2], 0.14, H - 0.3, 'temple_wall', c0=PLASTER['c0'])
            elif kind_ == 'board':
                prim.obox(B, np.r_[q0, zb + (H - 0.3) / 2], np.r_[q1, zb + (H - 0.3) / 2], 0.1, H - 0.3, wood)
            elif kind_ == 'karado':
                prim.obox(B, np.r_[q0, zb + (H - 0.3) / 2], np.r_[q1, zb + (H - 0.3) / 2], 0.1, H - 0.3, wood)
                for t in np.linspace(0.2, 0.8, 4):
                    pp = q0 + (q1 - q0) * t
                    prim.obox(B, np.r_[pp, zb + 0.15], np.r_[pp, zb + H - 0.5], 0.06, 0.14, wood, tag='detail')
        for i in range(nu):
            wallpiece((us[i], vs[0]), (us[i + 1], vs[0]), front if i == nu // 2 else wall)
            wallpiece((us[i], vs[-1]), (us[i + 1], vs[-1]), wall)
        for j in range(nv):
            wallpiece((us[0], vs[j]), (us[0], vs[j + 1]), wall)
            wallpiece((us[-1], vs[j]), (us[-1], vs[j + 1]), wall)
    arch.nageshi(B, L, D, zb + 0.25, wood, h=0.16, w=0.1, out=0.12)
    arch.nageshi(B, L, D, zb + H - 0.75, wood, h=0.18, w=0.1, out=0.12)
    arch.nageshi(B, L, D, zb + H, wood, h=0.22, w=0.12, out=0.08)
    top, reach = arch.bracket_row(B, L, D, zb + H, bracket, 0.8, wood, us=us, vs=vs)
    return jroof.roof(B, L + 2 * reach, D + 2 * reach, top + 0.35, o, kind=kind, cover=cover, pitch=pitch, rafter_mat=rafter_mat or wood,
                      rafter_end=rafter_end or rafter_mat or wood, ends=ends, ridge_h=ridge_h)
