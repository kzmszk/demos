"""Japanese roofs: 寄棟 yosemune (hip), 入母屋 irimoya (hip-and-gable), 切妻 kirizuma (gable), 宝形 hōgyō (pyramid).

Built in the building's local frame: u along the length (x), v across (y), z up, centred on the plan centre.
L x D is the wall-plate (pillar line) rectangle; the eave line lies `o` outside it.  The roof surface rises from the
eave edge with a concave profile (照り: z = zE + H * t^teri, t = inward distance / half depth) and the eave line curves
up toward the corners (軒反り: zE += sori * (1 - d_corner/Ls)^2).  Hips follow from the distance field of the plan
(45° in plan), so the faces meet exactly.  Under the overhang: the eave edge (鼻隠し / 茅負 with the tile ends on top),
the soffit and the rafters (垂木).  On top: the ridge (大棟) with 鬼瓦 or 鴟尾, hip ridges (隅棟), and for gables the
bargeboards (破風) with a 懸魚 and the gable wall (妻壁).

cover: 'hongawara' | 'sangawara' (kawara program), 'hiwada' (cypress bark), 'kokera' (shingles, hiwada program),
'copper'.  Returns a dict of useful heights (z_eave_edge, z_ridge, ...)."""
import math
import numpy as np
from . import prim

COVER_MAT = {'hongawara': 'hongawara', 'sangawara': 'kawara', 'hiwada': 'hiwada', 'kokera': 'hiwada', 'copper': 'copper', 'thatch': 'hiwada'}

class Roof:
    def __init__(self, L, D, z_eave, o, kind='irimoya', cover='hongawara', pitch=0.62, teri=1.4, sori=0.5, sori_len=0.4, gable_frac=0.5, verge=0.9,
                 edge=0.32, rafter=0.3, rafter_mat='wood_dark', rafter_end='wood_dark', fascia_mat=None, ridge_h=None, ridge_w=None, ends='oni', hip=True,
                 truncate=None, bargeboard_mat='wood_dark', gable_wall='temple_wall', tiers=2, tag='main', top=None):
        self.__dict__.update(locals()); del self.__dict__['self']
        self.a = L / 2 + o; self.c = D / 2 + o                    # half sizes of the eave outline
        if kind == 'hogyo': self.a = self.c = max(self.a, self.c)
        self.H = self.c * pitch                                    # eave edge -> ridge
        self.g = lambda t: np.power(np.clip(t, 0, 1), teri)
        self.zE0 = z_eave - self.H * self.g(o / self.c)            # eave edge height (before the corner sori)
        self.Ls = sori_len * self.c
        self.sg = gable_frac * self.c                                   # irimoya: inward depth where the gable begins
        self.mat = COVER_MAT[cover]
        self.ridge_h = ridge_h if ridge_h is not None else (0.35 if cover in ('hiwada', 'kokera', 'copper') else 0.12 * self.c + 0.25)
        self.ridge_w = ridge_w if ridge_w is not None else (0.45 if cover in ('hiwada', 'kokera', 'copper') else 0.04 * self.c + 0.3)
        self.fascia_mat = fascia_mat or rafter_mat

    # ---- height of the roof surface
    def zE(self, dc):
        """eave edge height at distance dc (along the eave) from the nearest corner"""
        if self.kind == 'kirizuma': return self.zE0 + 0 * dc
        k = np.clip(1 - np.asarray(dc, float) / self.Ls, 0, 1)
        return self.zE0 + self.sori * k * k
    def z(self, s, dc):
        return self.zE(dc) + self.H * self.g(np.asarray(s, float) / self.c)

    def sides(self):
        """eave sides: (start corner, end corner, inward normal, length).  0 front (v-), 1 right (u+), 2 back (v+), 3 left (u-)"""
        a, c = self.a, self.c
        P = [np.array([-a, -c]), np.array([a, -c]), np.array([a, c]), np.array([-a, c])]
        out = []
        for k in range(4):
            p0, p1 = P[k], P[(k + 1) % 4]
            d = (p1 - p0) / np.linalg.norm(p1 - p0)
            out.append((p0, p1, np.array([-d[1], d[0]]), float(np.linalg.norm(p1 - p0))))
        return out

    # ---- the covering surface of one side, as a grid in (x along the eave, t inward fraction)
    def face(self, B, k, x0=None, x1=None, smax=None, s0=0.0, nu=None, nt=None, offset=0.0, mat=None, flip=False, extend=0.0):
        p0, p1, n_in, E = self.sides()[k]
        d = (p1 - p0) / E
        x0 = -extend if x0 is None else x0; x1 = E + extend if x1 is None else x1
        nu = nu or max(4, int((x1 - x0) / 0.6))
        nt = nt or max(6, int(self.c / 0.5))
        xs = np.linspace(x0, x1, nu + 1)
        dc = np.minimum(np.abs(xs), np.abs(E - xs))
        dcc = np.minimum(np.clip(xs, 0, E), np.clip(E - xs, 0, E))
        if smax is None: smax = lambda x, dc_: np.minimum(dc_, self.c)
        sm = smax(xs, dcc)
        P = []; UV = []
        for j in range(nt + 1):
            t = j / nt
            for i in range(nu + 1):
                s = s0 + (sm[i] - s0) * t if sm[i] > s0 else s0
                xy = p0 + d * xs[i] + n_in * s
                zz = float(self.z(s, dcc[i])) - offset
                P.append((xy[0], xy[1], zz))
                # v: distance up the slope
                UV.append((xs[i], s * math.sqrt(1 + (self.H / self.c * self.teri * max(s, 1e-3) / self.c) ** 2) * 1.0))
        P = np.array(P); UV = np.array(UV)
        I = []
        for j in range(nt):
            for i in range(nu):
                a_ = j * (nu + 1) + i
                I += [[a_, a_ + 1, a_ + nu + 2], [a_, a_ + nu + 2, a_ + nu + 1]] if not flip else [[a_, a_ + nu + 2, a_ + 1], [a_, a_ + nu + 1, a_ + nu + 2]]
        I = np.array(I)
        # drop degenerate triangles (corner columns where s collapses)
        A = np.linalg.norm(np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]]), axis=1)
        I = I[A > 1e-6]
        B.add(P, I, mat or self.mat, UV=UV, smooth=True, tag=self.tag)
        return P.reshape(nt + 1, nu + 1, 3)

    # ---- eave edge strip, soffit, rafters for one side between x0..x1 (along the eave)
    def eave(self, B, k, x0, x1, gable_side=False):
        p0, p1, n_in, E = self.sides()[k]
        d = (p1 - p0) / E
        nu = max(4, int((x1 - x0) / 0.4))
        xs = np.linspace(x0, x1, nu + 1)
        dcc = np.minimum(np.clip(xs, 0, E), np.clip(E - xs, 0, E))
        top = np.array([[*(p0 + d * x), float(self.z(0.0, dc))] for x, dc in zip(xs, dcc)])
        out = np.array([-n_in[0], -n_in[1], 0.0])
        th = self.edge
        # the edge: tiles / bark layers on top (cover material), the fascia below
        bot = top - [0, 0, th]
        mid = top - [0, 0, th * 0.45]
        for (A_, B_, m) in ((top, mid, self.mat), (mid, bot, self.fascia_mat)):
            P = np.concatenate([A_, B_]); I = []
            for i in range(nu):
                I += [[i, i + nu + 1, i + 1], [i + 1, i + nu + 1, i + nu + 2]]
            UV = np.c_[np.r_[xs, xs], np.r_[A_[:, 2], B_[:, 2]]]
            B.add(P, I, m, UV=UV, N=np.tile(out, (len(P), 1)), tag=self.tag)
        # round tile ends along the eave (hongawara): small discs facing out
        if self.cover == 'hongawara':
            for x, dc in zip(np.arange(x0 + 0.15, x1, 0.3), None or [0] * 10000):
                pass
            for x in np.arange(x0 + 0.15, x1 - 0.05, 0.3):
                dcx = min(max(x, 0), max(E - x, 0))
                pc = np.array([*(p0 + d * x), float(self.z(0.0, dcx)) - 0.06])
                prim.cyl(B, pc + np.r_[n_in * 0.25, 0.04], pc - np.r_[n_in * 0.03, 0], 0.085, None, 8, self.mat, caps=(False, True), tag='detail')
        # soffit (軒裏): the surface just under the overhang, from the edge back to the wall line
        if gable_side: return
        def smax_(xs_, dc_):
            return np.minimum(np.minimum(dc_, self.c), self.o + 0.2)
        self.face(B, k, x0=x0, x1=x1, smax=smax_, offset=th, mat=self.fascia_mat, flip=True, nt=3)
        # rafters (垂木): parallel, inward from the edge to the wall line, cut at the hip diagonal
        if self.rafter:
            for tier, (s_a, s_b, drop) in enumerate(((0.0, self.o * 0.55, th + 0.06), (self.o * 0.45, self.o + 0.1, th + 0.2))[:self.tiers]):
                for x in np.arange(x0 + self.rafter / 2, x1, self.rafter):
                    dcx = min(max(x, 0), max(E - x, 0))
                    sb = min(s_b, dcx - 0.08)
                    if sb <= s_a + 0.1: continue
                    q0 = np.r_[p0 + d * x + n_in * s_a, float(self.z(s_a, dcx)) - drop]
                    q1 = np.r_[p0 + d * x + n_in * sb, float(self.z(sb, dcx)) - drop]
                    prim.obox(B, q0, q1, 0.085, 0.10, self.rafter_mat, up=(0, 0, 1), tag='detail')
                    if tier == 0 and self.rafter_end != self.rafter_mat:
                        e1 = q0 + np.r_[n_in * 0.02, 0]
                        prim.obox(B, q0 - np.r_[n_in * 0.005, 0], e1, 0.087, 0.102, self.rafter_end, tag='detail')

    def ridge(self, B, pts, w, h, ends=(None, None)):
        pts = np.asarray(pts, float)
        prof = [(-w / 2, -0.15), (w / 2, -0.15), (w / 2, h * 0.7), (w * 0.35, h), (-w * 0.35, h), (-w / 2, h * 0.7)]
        prim.sweep(B, pts, prof, 'ridge', closed=True, tag=self.tag, caps=True)
        for e, p, q in ((ends[0], pts[0], pts[1]), (ends[1], pts[-1], pts[-2])):
            if not e: continue
            dd = p - q; dd /= np.linalg.norm(dd)
            side = np.cross(dd, [0, 0, 1.0]); side /= max(np.linalg.norm(side), 1e-6)
            if e == 'shibi':
                # 鴟尾: a tall curved fin, gilded or dark bronze
                hh = h * 2.6
                prof2 = [(0.0, 0.0), (0.35, 0.2), (0.5, 0.6), (0.42, 0.95), (0.15, 1.0), (-0.05, 0.75), (0.05, 0.4)]
                P = []; I = []
                for k_, (fx, fz) in enumerate(prof2):
                    for sgn in (-1, 1):
                        P.append(p + dd * (fx * hh * 0.6 - 0.1) + side * sgn * w * 0.25 + np.array([0, 0, h * 0.6 + fz * hh]))
                for k_ in range(len(prof2) - 1):
                    a_ = 2 * k_
                    I += [[a_, a_ + 2, a_ + 3], [a_, a_ + 3, a_ + 1]]
                B.add(np.array(P), I, 'bronze', tag=self.tag)
                prim.obox(B, p, p + np.array([0, 0, h * 0.8]), w * 0.6, w * 0.6, 'ridge', tag=self.tag)
            else:
                # 鬼瓦: a plate with a rounded top, slightly leaning out
                ww = w * 1.6; hh = h * 1.5
                c0 = p + dd * 0.05
                R = [(-ww / 2, -0.1), (ww / 2, -0.1), (ww / 2, hh * 0.65), (ww * 0.3, hh), (-ww * 0.3, hh), (-ww / 2, hh * 0.65)]
                P = [c0 + side * x + np.array([0, 0, y]) + dd * (y * 0.12) for x, y in R]
                Pb = [q_ - dd * 0.12 for q_ in P]
                Pall = np.array(P + Pb); n = len(R)
                I = [[0, j, j + 1] for j in range(1, n - 1)] + [[n, n + j + 1, n + j] for j in range(1, n - 1)]
                for j in range(n):
                    k2 = (j + 1) % n
                    I += [[j, j + n, k2 + n], [j, k2 + n, k2]]
                fn = np.cross(Pall[1] - Pall[0], Pall[2] - Pall[0])
                if fn @ dd < 0: I = [t[::-1] for t in I]
                B.add(Pall, I, 'ridge', tag=self.tag, c1=(0, 1, 0, 0))

    def hip_line(self, k, s_to, n=12, off=0.0):
        """points along the hip from corner k (start of side k) inward to depth s_to"""
        p0, p1, n_in, E = self.sides()[k]
        d = (p1 - p0) / E
        pts = []
        for t in np.linspace(0.0, 1.0, n):
            s = s_to * t
            xy = p0 + d * s + n_in * s
            pts.append((xy[0], xy[1], float(self.z(s, s)) + off))
        return np.array(pts)

    def build(self, B):
        a, c, o = self.a, self.c, self.o
        kind = self.kind
        out = dict(z_edge=self.zE0, z_ridge=float(self.z(c, c)))
        if kind in ('yosemune', 'hogyo'):
            smax_trunc = (lambda xs_, dc_: np.minimum(np.minimum(dc_, c), self.truncate)) if self.truncate else None
            for k in range(4): self.face(B, k, smax=smax_trunc)
            for k in range(4):
                E = self.sides()[k][3]; self.eave(B, k, 0.0, E)
            zr = float(self.z(c if not self.truncate else self.truncate, c))
            if kind == 'yosemune' and a - c > 0.05:
                self.ridge(B, [(-(a - c), 0, zr), (a - c, 0, zr)], self.ridge_w, self.ridge_h, ends=(self.ends, self.ends))
            if self.hip:
                s_to = c if not self.truncate else self.truncate
                for k in range(4):
                    hl = self.hip_line(k, s_to * 0.98, off=0.0)
                    self.ridge(B, hl[1:][::-1], self.ridge_w * 0.6, self.ridge_h * 0.55, ends=(None, 'oni' if self.ends else None))
            if kind == 'hogyo' and not self.truncate:
                top = self.top or [(0.35, 0.0), (0.42, 0.25), (0.2, 0.35), (0.22, 0.6), (0.0, 0.9)]
                prim.lathe(B, (0, 0, zr - 0.05), top, 12, 'bronze', tag=self.tag)
            out['z_ridge'] = zr
        elif kind == 'kirizuma':
            vo = self.verge
            for k in (0, 2):
                self.face(B, k, x0=o - vo, x1=2 * a - o + vo, smax=lambda xs_, dc_: np.full_like(xs_, c), nu=max(6, int(2 * a / 0.6)))
                self.eave(B, k, o - vo, 2 * a - o + vo)
            zr = float(self.z(c, c))
            u_end = a - o + vo
            self.ridge(B, [(-u_end, 0, zr), (u_end, 0, zr)], self.ridge_w, self.ridge_h, ends=(self.ends, self.ends))
            self.gable(B, a - o, 0.0, vo)
            out['z_ridge'] = zr
        elif kind == 'irimoya':
            sg = self.sg; vo = self.verge
            # lower skirt: all four faces up to depth sg
            for k in range(4): self.face(B, k, smax=lambda xs_, dc_: np.minimum(np.minimum(dc_, c), sg))
            for k in range(4):
                E = self.sides()[k][3]; self.eave(B, k, 0.0, E)
            # upper gable roof over the inner length, overhanging the skirt by vo at each end
            u_g = a - sg                       # the gable line (where the gable wall stands, plus a small inset)
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
            out['z_ridge'] = zr; out['z_break'] = float(self.z(sg, sg))
        return out

    def gable(self, B, u_g, s_from, vo):
        """gable walls (妻壁) at u = ±u_g, bargeboards (破風) along the verge, a 懸魚 at the apex"""
        c = self.c
        ss = np.linspace(s_from, c, 10)
        for sgn in (-1, 1):
            u = sgn * u_g
            # wall: from the break line up to under the roof, both slopes
            zb = float(self.z(s_from, s_from)) - 0.05
            P = []
            for s in ss: P.append((u, -c + s, float(self.z(s, c)) - self.edge - 0.05))
            for s in ss[::-1][1:]: P.append((u, c - s, float(self.z(s, c)) - self.edge - 0.05))
            P = np.array(P)
            base = np.array([(u, P[-1][1], zb), (u, P[0][1], zb)])
            poly = np.concatenate([P, base])
            # fan from the centre of the base
            cen = np.array([u, 0.0, zb])
            Pall = np.concatenate([[cen], poly]); n = len(poly)
            I = [[0, 1 + j, 1 + (j + 1) % n] for j in range(n)]
            fn = np.cross(Pall[I[0][1]] - Pall[0], Pall[I[0][2]] - Pall[0])
            if fn[0] * sgn < 0: I = [t[::-1] for t in I]
            UV = np.c_[Pall[:, 1], Pall[:, 2]]
            B.add(Pall, I, self.gable_wall, UV=UV, tag=self.tag, c0=(232, 228, 216, 35), c1=(0, 0, 0, 0))
            # bargeboards: a board under each verge edge, meeting at the apex
            ue = u + sgn * vo
            for side in (-1, 1):
                pts = np.array([(ue, side * (c - s), float(self.z(s, c)) - self.edge * 0.6) for s in ss])
                prim.sweep(B, pts, [(-0.06, 0.0), (0.06, 0.0), (0.06, -0.42), (-0.06, -0.42)], self.bargeboard_mat, up=(0, 0, 1), tag=self.tag, caps=True)
                # verge edge of the covering
                pe = np.array([(ue, side * (c - s), float(self.z(s, c))) for s in ss])
                prim.sweep(B, pe, [(-0.12, -self.edge * 0.55), (0.12, -self.edge * 0.55), (0.12, 0.03), (-0.12, 0.03)], self.mat, up=(0, 0, 1), tag=self.tag, caps=True)
                # 降棟: the ridge down the verge
                self.ridge(B, pe[::-1] + np.array([-sgn * 0.25, 0, 0.02]), self.ridge_w * 0.55, self.ridge_h * 0.5, ends=(None, 'oni' if self.ends else None))
            # 懸魚 under the apex
            za = float(self.z(c, c)) - self.edge - 0.5
            gp = [(-0.45, 0.25), (0.45, 0.25), (0.35, -0.35), (0.0, -0.65), (-0.35, -0.35)]
            P = np.array([(ue + sgn * 0.05, y, za + z) for (y, z) in gp])
            I = [[0, 1, 2], [0, 2, 3], [0, 3, 4]]
            if sgn < 0: I = [t[::-1] for t in I]
            B.add(P, I, self.bargeboard_mat, tag='detail')

def roof(B, L, D, z_eave, o, **kw):
    r = Roof(L, D, z_eave, o, **kw)
    return r.build(B)
