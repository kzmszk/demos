"""Ruined buildings rebuilt from PLATEAU LOD2 shells.

Each building is re-made floor by floor from horizontal sections of its PLATEAU mesh:
  * walls per floor and per bay (facade band textures: one floor = one band row),
  * a ruin height field H(x, y): a floor exists where H > its ceiling (shear, wedge, collapse),
  * exposed slabs on a 1.5 m strip grid (jagged broken edges), open-storey faces at the steps,
  * breaches (bays open into a dark gutted storey), parapets on intact roofs.
"""
import math
import random
import numpy as np

import sb_geom as G
from sb_mesh import MB, vnoise, fbm

BAY = 3.6            # nominal bay width (m)
BAYS_PER_TILE = 4    # bays across one band texture repeat
ROWS = 8             # bands per facade texture
PAD = 6.0 / 256.0    # v padding inside a band (fraction of band)

BANDS = {
    # key: (material, row)
    'shopA': ('facade_a', 0), 'shopB': ('facade_a', 1), 'office': ('facade_a', 2), 'ribbon': ('facade_a', 3),
    'tile': ('facade_a', 4), 'blind': ('facade_a', 5), 'gutted': ('facade_a', 6), 'silver': ('facade_a', 7),
    'curtain': ('facade_b', 0), 'curtain2': ('facade_b', 1), 'qfront': ('facade_b', 2), 'fins': ('facade_b', 3),
    'signwall': ('facade_b', 4), 'balcony': ('facade_b', 5), 'shopC': ('facade_b', 6), 'overgrown': ('facade_b', 7),
}

STYLES = {
    'office': dict(ground=['shopB', 'shopA'], upper=['office'], alt=['ribbon'], low=['signwall']),
    'commercial': dict(ground=['shopA', 'shopC'], upper=['blind', 'ribbon'], alt=['signwall'], low=['signwall']),
    'glass': dict(ground=['shopB'], upper=['curtain', 'curtain2'], alt=['curtain2'], low=['curtain']),
    'tile': dict(ground=['shopA', 'shopC'], upper=['tile'], alt=['balcony'], low=['signwall']),
    'mixed': dict(ground=['shopC', 'shopA'], upper=['tile', 'office'], alt=['balcony'], low=['signwall']),
    'fins': dict(ground=['shopB'], upper=['fins'], alt=['fins'], low=['fins']),
    'qfront': dict(ground=['shopB'], upper=['qfront'], alt=['qfront'], low=['qfront']),
    'silver': dict(ground=['shopB'], upper=['silver'], alt=['silver'], low=['silver']),
    'magnet': dict(ground=['shopB'], upper=['blind'], alt=['blind'], low=['signwall']),
}

TINTS = [(1.0, 1.0, 1.0), (1.0, 0.96, 0.9), (0.93, 0.93, 0.95), (1.02, 0.97, 0.88), (0.9, 0.88, 0.84),
         (0.97, 0.94, 0.92), (0.86, 0.86, 0.86), (1.03, 1.0, 0.95)]


def band_uv(key, u, t):
    """u in bay units, t in [0,1] within the floor (0 bottom)."""
    mat, row = BANDS[key]
    v0 = 1.0 - (row + 1) / ROWS
    v = v0 + (PAD + t * (1 - 2 * PAD)) / ROWS
    return (u / BAYS_PER_TILE, v)


def concrete_uv(p):
    return (p[0] / 4.0, p[1] / 4.0)


# ------------------------------------------------------------------ ruin height field
class Ruin:
    """H(x,y): floors whose ceiling is above H are gone. Components combined by min()."""

    def __init__(self, seed):
        self.parts = []
        self.seed = seed

    def shear(self, z, direction=(1, 0), slope=0.0, origin=(0, 0), amp=4.0, scale=7.5):
        self.parts.append(('shear', z, np.array(direction, float) / (np.hypot(*direction) + 1e-9), slope,
                           np.array(origin, float), amp, scale))
        return self

    def wedge(self, corner, z, k=1.0, amp=2.0):
        """low at corner (height z), rising with distance at rate k."""
        self.parts.append(('wedge', np.array(corner, float), z, k, amp))
        return self

    def hole(self, center, radius, z, amp=2.0):
        self.parts.append(('hole', np.array(center, float), radius, z, amp))
        return self

    def core(self, center, half=(3.0, 4.0), z=1e9, ang=0.0):
        """a stair / lift core that stands proud of the break (H raised inside a rectangle)"""
        self.raises = getattr(self, 'raises', [])
        self.raises.append((np.array(center, float), half, z, ang))
        return self

    def __call__(self, P):
        P = np.atleast_2d(np.asarray(P, dtype=float))
        H = self._h(P)
        for (c, half, z, ang) in getattr(self, 'raises', []):
            ca, sa = math.cos(-ang), math.sin(-ang)
            d = P - c
            lx = d[:, 0] * ca - d[:, 1] * sa; ly = d[:, 0] * sa + d[:, 1] * ca
            inside = (np.abs(lx) < half[0]) & (np.abs(ly) < half[1])
            H = np.where(inside, np.maximum(H, z), H)
        return H

    def _h(self, P):
        H = np.full(len(P), 1e9)
        for i, p in enumerate(self.parts):
            n = fbm(P[:, 0], P[:, 1], scale=p[-1] if p[0] == 'shear' else 4.5, seed=self.seed + i * 7, octaves=3)
            if p[0] == 'shear':
                _, z, d, slope, o, amp, sc = p
                h = z + slope * ((P - o) @ d) + amp * (n - 0.5) * 2
            elif p[0] == 'wedge':
                _, c, z, k, amp = p
                h = z + k * np.hypot(P[:, 0] - c[0], P[:, 1] - c[1]) + amp * (n - 0.5) * 2
            elif p[0] == 'hole':
                _, c, r, z, amp = p
                d = np.hypot(P[:, 0] - c[0], P[:, 1] - c[1])
                h = np.where(d < r, z + amp * (n - 0.5) * 2 + 0.6 * np.maximum(0, d - 0.6 * r), 1e9)
            H = np.minimum(H, h)
        return H


# ------------------------------------------------------------------ building
class Building:
    def __init__(self, name, V, F, info, ground, style='office', ruin=None, seed=0, fh=None, gf=None,
                 breach=0.12, tint=None, parapet=True, keep_top=False):
        self.name = name
        self.V = V; self.F = F
        self.info = info
        self.ground = ground
        self.z0 = float(V[:, 2].min())
        self.z1 = float(V[:, 2].max())
        self.style = STYLES[style] if isinstance(style, str) else style
        self.ruin = ruin or Ruin(seed)
        self.rnd = random.Random(seed)
        self.seed = seed
        use = info.get('use', '')
        if fh is None:
            fh = 3.0 if '住宅' in use else (3.8 if '商業' in use else 3.7)
        if gf is None:
            gf = 3.6 if '住宅' in use else 4.6
        self.fh = fh; self.gf = gf
        self.breach = breach
        self.tint = tint or tuple(c * self.rnd.uniform(0.82, 1.02) for c in self.rnd.choice(TINTS))
        self.parapet = parapet
        self.floors = self._floors()
        self.sections = []
        for (za, zb) in self.floors:
            zm = za + 0.5 * (zb - za)
            if zm > self.z1 - 0.3:
                break
            S = G.slice_mesh(V, F, zm)
            if not S:
                break
            self.sections.append(S)
        self.floors = self.floors[:len(self.sections)]
        self.theta = G.dominant_angle(self.sections[0]) if self.sections else 0.0
        self.top_surfaces = []   # (ring, z) for collision
        self.exposed = []        # (x, y, z, area) exposed slab cells (for vegetation and rubble)
        self.roof_edges = []     # (p, q, z, outward normal) for vines

    def _floors(self):
        z = self.z0
        out = []
        h = self.z1 - self.z0
        zs = [self.z0, self.z0 + min(self.gf, max(2.8, h))]
        while zs[-1] + self.fh <= self.z1 + 0.6 * self.fh - 1e-6:
            zs.append(zs[-1] + self.fh)
        return list(zip(zs[:-1], zs[1:]))

    # ---- local grid frame
    def to_local(self, P):
        c, s = math.cos(-self.theta), math.sin(-self.theta)
        P = np.asarray(P, float)
        return np.stack([P[..., 0] * c - P[..., 1] * s, P[..., 0] * s + P[..., 1] * c], axis=-1)

    def to_world(self, P):
        c, s = math.cos(self.theta), math.sin(self.theta)
        P = np.asarray(P, float)
        return np.stack([P[..., 0] * c - P[..., 1] * s, P[..., 0] * s + P[..., 1] * c], axis=-1)

    # ---- build
    def build(self, mb, g=1.5):
        if not self.sections:
            return
        nfl = len(self.sections)
        # grid over the local bbox of all sections
        allp = np.concatenate([np.array(r) for S in self.sections for r, _h in S])
        L = self.to_local(allp)
        lx0, ly0 = L.min(axis=0) - 0.01
        lx1, ly1 = L.max(axis=0) + 0.01
        nx = max(1, int(math.ceil((lx1 - lx0) / g)))
        ny = max(1, int(math.ceil((ly1 - ly0) / g)))
        cx = lx0 + (np.arange(nx) + 0.5) * g
        cy = ly0 + (np.arange(ny) + 0.5) * g
        CX, CY = np.meshgrid(cx, cy, indexing='ij')
        centers_l = np.stack([CX.ravel(), CY.ravel()], axis=1)
        centers = self.to_world(centers_l)
        H = self.ruin(centers).reshape(nx, ny)
        # coverage per floor: centre inside, any corner inside, all inside
        offs = np.array([[-.5, -.5], [.5, -.5], [.5, .5], [-.5, .5]]) * g * 0.999
        corners = [self.to_world(centers_l + o) for o in offs]
        occ = []
        full = []
        for k, S in enumerate(self.sections):
            inc = G.in_section(centers, S).reshape(nx, ny)
            ins = [G.in_section(cp, S).reshape(nx, ny) for cp in corners]
            anyin = inc | ins[0] | ins[1] | ins[2] | ins[3]
            allin = inc & ins[0] & ins[1] & ins[2] & ins[3]
            ztop = self.floors[k][1]
            alive = H > ztop
            occ.append(anyin & alive)
            full.append(allin & alive)
        occ.append(np.zeros((nx, ny), bool)); full.append(np.zeros((nx, ny), bool))
        self._grid = (lx0, ly0, g, nx, ny)
        tint = self.tint
        col_slab = (0.95 * tint[0], 0.95 * tint[1], 0.93 * tint[2], 1)

        # ---- slabs (top surfaces) per floor
        for k in range(nfl):
            ztop = self.floors[k][1]
            emit = occ[k] & ~full[k + 1]
            S = self.sections[k]
            for i in range(nx):
                j = 0
                while j < ny:
                    if not emit[i, j]:
                        j += 1
                        continue
                    j0 = j
                    while j < ny and emit[i, j]:
                        j += 1
                    # rect in local coords: x in [lx0+i*g, +g], y in [ly0+j0*g, ly0+j*g]
                    rect_l = np.array([[lx0 + i * g, ly0 + j0 * g], [lx0 + (i + 1) * g, ly0 + j0 * g],
                                       [lx0 + (i + 1) * g, ly0 + j * g], [lx0 + i * g, ly0 + j * g]])
                    rect = [tuple(p) for p in self.to_world(rect_l)]
                    for ring, hole in S:
                        if hole:
                            continue
                        piece = _clip_convex(ring, rect)
                        if len(piece) >= 3 and abs(G.area(piece)) > 0.05:
                            # subtract holes crudely: skip pieces whose centroid is in a hole
                            cpt = np.mean(np.array(piece), axis=0)
                            if any(h and G.point_in_poly(cpt, r) for r, h in S):
                                continue
                            mb.poly_flat(piece, ztop, 'concrete', concrete_uv, col=col_slab)
                            self.top_surfaces.append((piece, ztop))
                            # exposed (open sky) cells for vegetation / rubble
                            exposed_here = ~occ[k + 1][i, j0:j] if k + 1 < nfl else np.ones(j - j0, bool)
                            for jj in range(j0, j):
                                if exposed_here[jj - j0]:
                                    w = self.to_world(np.array([lx0 + (i + .5) * g, ly0 + (jj + .5) * g]))
                                    if G.in_section([w], S)[0]:
                                        self.exposed.append((float(w[0]), float(w[1]), ztop, k == nfl - 1 or not occ[k + 1].any()))

        # ---- column stubs, rebar and sagging slab fragments at the broken top
        rbar = 0
        for k in range(nfl):
            ztop = self.floors[k][1]
            S = self.sections[k]
            ex = occ[k] & ~occ[k + 1]
            inc = G.in_section(centers, S).reshape(nx, ny)
            dead = inc & ~occ[k]
            for i in range(nx):
                for j in range(ny):
                    if not ex[i, j]:
                        continue
                    lc = np.array([lx0 + (i + .5) * g, ly0 + (j + .5) * g])
                    broken = (H[i, j] < self.z1 - 0.5)
                    if not broken:
                        continue
                    # columns on a 7.2 m grid
                    if (i % 5 == 2) and (j % 5 == 2) and self.rnd.random() < 0.7:
                        w = self.to_world(lc)
                        hh = self.rnd.uniform(0.8, self.fh * 1.2)
                        self._column(mb, w, ztop, hh)
                    # hanging slab fragments over the void next to the cell
                    for (di, dj) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ii, jj = i + di, j + dj
                        if 0 <= ii < nx and 0 <= jj < ny and dead[ii, jj] and self.rnd.random() < 0.12:
                            self._hanging_slab(mb, lc, (di, dj), g, ztop)

        # ---- open-storey faces at internal steps (cells alive on floor k next to cells in the section but dead)
        for k in range(nfl):
            za, zb = self.floors[k]
            S = self.sections[k]
            A = occ[k]
            inside_dead = np.zeros_like(A)
            # dead = in section footprint but floor gone
            inc = G.in_section(centers, S).reshape(nx, ny)
            dead = inc & ~A
            for axis in (0, 1):
                if axis == 0:
                    a = A[:-1, :] & dead[1:, :]
                    b = dead[:-1, :] & A[1:, :]
                else:
                    a = A[:, :-1] & dead[:, 1:]
                    b = dead[:, :-1] & A[:, 1:]
                for sign, msk in ((1, a), (-1, b)):
                    ii, jj = np.nonzero(msk)
                    for i, j in zip(ii, jj):
                        if axis == 0:
                            x = lx0 + (i + 1) * g
                            p0 = (x, ly0 + j * g); p1 = (x, ly0 + (j + 1) * g)
                            # face looks toward +x if sign=1 (alive at i, dead at i+1)
                            if sign == -1:
                                p0, p1 = p1, p0
                            else:
                                p0, p1 = p0, p1
                        else:
                            y = ly0 + (j + 1) * g
                            p0 = (lx0 + (i + 1) * g, y); p1 = (lx0 + i * g, y)
                            if sign == -1:
                                p0, p1 = p1, p0
                        w0, w1 = self.to_world(np.array([p0, p1]))
                        # outward normal of the alive cell side: for +x face (sign 1, axis 0) the face
                        # must look toward +x: order the bottom edge so that it runs to the viewer's right.
                        self._open_face(mb, w0, w1, za, zb, k)

        # ---- walls per floor
        for k in range(nfl):
            za, zb = self.floors[k]
            S = self.sections[k]
            if k == 0:
                key_choices = self.style['ground']
            elif k <= 2:
                key_choices = self.style['low'] if self.rnd.random() < 0.7 else self.style['upper']
            else:
                key_choices = self.style['upper'] if self.rnd.random() > 0.18 else self.style['alt']
            band = key_choices[(self.seed + k * 3) % len(key_choices)] if k > 0 else self.rnd.choice(key_choices)
            fl_tint = [min(1.2, t * (0.94 + 0.1 * self.rnd.random())) for t in tint]
            if k <= 1:     # damp, mossy street level
                g_ = 0.82 if k == 0 else 0.92
                fl_tint = [fl_tint[0] * g_ * 0.92, fl_tint[1] * g_, fl_tint[2] * g_ * 0.85]
            fl_tint = tuple(fl_tint)
            for ring, hole in S:
                self._walls(mb, ring, za, zb, k, band, fl_tint)

    def _column(self, mb, w, z, hh, s=0.32):
        x, y = float(w[0]), float(w[1])
        c = self.tint
        col = (0.85 * c[0], 0.85 * c[1], 0.83 * c[2], 1)
        top = z + hh
        P = [(x - s, y - s), (x + s, y - s), (x + s, y + s), (x - s, y + s)]
        for a in range(4):
            p = P[a]; q = P[(a + 1) % 4]
            jag = top - self.rnd.uniform(0, 0.5)
            mb.quad((p[0], p[1], z), (q[0], q[1], z), (q[0], q[1], jag), (p[0], p[1], jag),
                    [(0, z / 4), (0.16, z / 4), (0.16, jag / 4), (0, jag / 4)], 'concrete', col=col)
        mb.face([(p[0], p[1], top - 0.3) for p in P], [(0, 0), (0.16, 0), (0.16, 0.16), (0, 0.16)], 'concrete', col=col)
        # rebar sticking out of the top
        for r_ in range(self.rnd.randint(2, 5)):
            bx = x + self.rnd.uniform(-s, s) * 0.8; by = y + self.rnd.uniform(-s, s) * 0.8
            L = self.rnd.uniform(0.4, 1.4)
            lean = (self.rnd.gauss(0, 0.25), self.rnd.gauss(0, 0.25))
            t = 0.018
            p0 = (bx, by, top - 0.3); p1 = (bx + lean[0] * L, by + lean[1] * L, top - 0.3 + L)
            mb.quad((p0[0] - t, p0[1], p0[2]), (p0[0] + t, p0[1], p0[2]), (p1[0] + t, p1[1], p1[2]), (p1[0] - t, p1[1], p1[2]),
                    [(0, 0), (0.02, 0), (0.02, 0.5), (0, 0.5)], 'metal')
            mb.quad((p0[0], p0[1] - t, p0[2]), (p0[0], p0[1] + t, p0[2]), (p1[0], p1[1] + t, p1[2]), (p1[0], p1[1] - t, p1[2]),
                    [(0, 0), (0.02, 0), (0.02, 0.5), (0, 0.5)], 'metal')

    def _hanging_slab(self, mb, lc, d, g, ztop):
        """a slab piece broken at the edge of the cell and hanging into the void below"""
        di, dj = d
        ex = np.array([di, dj], float)
        side = np.array([-dj, di], float)
        e0 = lc + ex * g * 0.5 - side * g * 0.5 * self.rnd.uniform(0.6, 1.0)
        e1 = lc + ex * g * 0.5 + side * g * 0.5 * self.rnd.uniform(0.6, 1.0)
        L = self.rnd.uniform(1.2, 3.0)
        ang = math.radians(self.rnd.uniform(35, 75))
        out = ex * L * math.cos(ang)
        dz = -L * math.sin(ang)
        f0 = e0 + out + side * self.rnd.uniform(-0.3, 0.3)
        f1 = e1 + out + side * self.rnd.uniform(-0.3, 0.3)
        W = self.to_world(np.array([e0, e1, f1, f0]))
        z = ztop
        zz = [z, z, z + dz + self.rnd.uniform(-0.4, 0.4), z + dz]
        pts = [(W[i][0], W[i][1], zz[i]) for i in range(4)]
        col = (0.8, 0.79, 0.76, 1)
        uv = [(0, 0), (0.4, 0), (0.4, 0.6), (0, 0.6)]
        mb.face(pts, uv, 'concrete', col)
        th = 0.3
        mb.face([(p[0], p[1], p[2] - th) for p in pts[::-1]], uv[::-1], 'concrete', (0.55, 0.55, 0.53, 1))
        # thickness strip at the free end (broken edge)
        a, b = pts[2], pts[3]
        mb.quad((b[0], b[1], b[2] - th), (a[0], a[1], a[2] - th), (a[0], a[1], a[2]), (b[0], b[1], b[2]),
                [(0, 0), (0.4, 0), (0.4, 0.08), (0, 0.08)], 'concrete', (0.7, 0.7, 0.68, 1))

    def _alive(self, P, k):
        """floor k alive at world points P (n,2)"""
        return self.ruin(P) > self.floors[k][1]

    def _open_face(self, mb, w0, w1, za, zb, k):
        # the face must face away from the alive cell: we built p0->p1 so that its right side is the dead side
        d = w1 - w0
        L = float(np.hypot(*d))
        if L < 0.05:
            return
        u0 = self.rnd.random() * 4
        u1 = u0 + L / BAY
        zb2 = zb
        # the gutted band shows an empty storey between two slab edges
        mb.quad((w0[0], w0[1], za), (w1[0], w1[1], za), (w1[0], w1[1], zb2), (w0[0], w0[1], zb2),
                [band_uv('gutted', u0, 0), band_uv('gutted', u1, 0), band_uv('gutted', u1, 1), band_uv('gutted', u0, 1)],
                'facade_a', col=(0.9, 0.9, 0.9, 1))

    def _walls(self, mb, ring, za, zb, k, band, tint):
        n = len(ring)
        P = np.array(ring)
        ubase = self.rnd.random() * 4
        for e in range(n):
            p = P[e]; q = P[(e + 1) % n]
            d = q - p
            L = float(np.hypot(*d))
            if L < 0.05:
                continue
            t = d / L
            nrm = np.array([t[1], -t[0]])          # outward (right of CCW travel)
            nb = max(1, int(round(L / BAY)))
            bw = L / nb
            # bay states
            mids = np.array([p + t * (i + 0.5) * bw - nrm * 0.8 for i in range(nb)])
            alive = self._alive(mids, k)
            s_world = (mids[:, 0] * 0.37 + mids[:, 1] * 0.61)
            bn = vnoise(s_world / 4.0 + k * 0.9, k * 1.7 + self.seed, 1.0, self.seed + 5)
            breach = alive & (bn < self.breach) & (k > 0)
            state = np.where(~alive, 0, np.where(breach, 2, 1))
            i = 0
            while i < nb:
                s = state[i]
                j = i
                while j < nb and state[j] == s:
                    j += 1
                a = p + t * i * bw
                b = p + t * j * bw
                ua = ubase + i * (bw / BAY)
                ub = ubase + j * (bw / BAY)
                zlo = za
                if k == 0:
                    zlo = min(self.ground(a[0], a[1]), self.ground(b[0], b[1]), za) - 0.8
                if k == 0 and s != 0 and zlo < za - 0.01:
                    mb.quad((a[0], a[1], zlo), (b[0], b[1], zlo), (b[0], b[1], za), (a[0], a[1], za),
                            [(ua, zlo / 4), (ub, zlo / 4), (ub, za / 4), (ua, za / 4)], 'concrete', col=(0.6, 0.6, 0.58, 1))
                if s == 1:
                    if True:
                        mb.quad((a[0], a[1], za), (b[0], b[1], za), (b[0], b[1], zb), (a[0], a[1], zb),
                                [band_uv(band, ua, 0), band_uv(band, ub, 0), band_uv(band, ub, 1), band_uv(band, ua, 1)],
                                BANDS[band][0], col=tint)
                elif s == 2:
                    self._recess(mb, a, b, nrm, za, zb, ua, ub, tint)
                i = j
            # parapet on top edges where nothing stands above
            if self.parapet and (k == len(self.floors) - 1 or self._top_edge(p, q, nrm, k)):
                mids2 = np.array([p + t * (i + 0.5) * bw - nrm * 0.8 for i in range(nb)])
                al = self._alive(mids2, k)
                for i in range(nb):
                    if not al[i]:
                        continue
                    a = p + t * i * bw; b = p + t * (i + 1) * bw
                    self._parapet(mb, a, b, nrm, zb, tint)
                    self.roof_edges.append((tuple(a), tuple(b), zb, tuple(nrm)))

    def _top_edge(self, p, q, nrm, k):
        if k + 1 >= len(self.sections):
            return True
        m = 0.5 * (p + q) - nrm * 0.6
        S = self.sections[k + 1]
        return not G.in_section([m], S)[0]

    def _parapet(self, mb, a, b, nrm, z, tint, h=1.0, th=0.25):
        a2 = a - nrm * th; b2 = b - nrm * th
        col = tuple(c * 0.95 for c in tint[:3]) + (1,)
        L = float(np.hypot(*(b - a)))
        uv = lambda x, y: (x / 4.0, y / 4.0)
        mb.quad((a[0], a[1], z), (b[0], b[1], z), (b[0], b[1], z + h), (a[0], a[1], z + h),
                [uv(0, 0), uv(L, 0), uv(L, h), uv(0, h)], 'concrete', col=col)
        mb.quad((b2[0], b2[1], z), (a2[0], a2[1], z), (a2[0], a2[1], z + h), (b2[0], b2[1], z + h),
                [uv(0, 0), uv(L, 0), uv(L, h), uv(0, h)], 'concrete', col=col)
        mb.quad((a[0], a[1], z + h), (b[0], b[1], z + h), (b2[0], b2[1], z + h), (a2[0], a2[1], z + h),
                [uv(0, 0), uv(L, 0), uv(L, th), uv(0, th)], 'concrete', col=col)

    def _recess(self, mb, a, b, nrm, za, zb, ua, ub, tint, depth=2.6):
        ai = a - nrm * depth; bi = b - nrm * depth
        zs = za + 0.02
        zc = zb - 0.4
        dk = (0.8, 0.8, 0.8, 1)
        # back wall: gutted band
        mb.quad((ai[0], ai[1], za), (bi[0], bi[1], za), (bi[0], bi[1], zb), (ai[0], ai[1], zb),
                [band_uv('gutted', ua, 0), band_uv('gutted', ub, 0), band_uv('gutted', ub, 1), band_uv('gutted', ua, 1)],
                'facade_a', col=dk)
        uvf = concrete_uv
        # floor, ceiling
        mb.quad((a[0], a[1], zs), (b[0], b[1], zs), (bi[0], bi[1], zs), (ai[0], ai[1], zs),
                [uvf(a), uvf(b), uvf(bi), uvf(ai)], 'concrete', col=(0.75, 0.74, 0.7, 1))
        mb.quad((ai[0], ai[1], zc), (bi[0], bi[1], zc), (b[0], b[1], zc), (a[0], a[1], zc),
                [uvf(ai), uvf(bi), uvf(b), uvf(a)], 'concrete', col=(0.55, 0.55, 0.55, 1))
        # slab edge band (lintel) across the opening top
        mb.quad((a[0], a[1], zc), (b[0], b[1], zc), (b[0], b[1], zb), (a[0], a[1], zb),
                [(0, 0), (1, 0), (1, 0.1), (0, 0.1)], 'concrete', col=tint)
        # jambs
        for (p, pi, flip) in ((a, ai, False), (b, bi, True)):
            pts = [(p[0], p[1], za), (pi[0], pi[1], za), (pi[0], pi[1], zb), (p[0], p[1], zb)]
            if flip:
                pts = pts[::-1]
            mb.face(pts, [(0, 0), (0.6, 0), (0.6, 1), (0, 1)], 'concrete', col=(0.7, 0.7, 0.68, 1))


def _clip_convex(subject, clip):
    """Sutherland-Hodgman: subject (any simple polygon) clipped by convex CCW polygon clip."""
    out = list(subject)
    n = len(clip)
    # ensure clip CCW
    if G.area(clip) < 0:
        clip = clip[::-1]
    for i in range(n):
        if not out:
            break
        p = clip[i]; q = clip[(i + 1) % n]
        ex, ey = q[0] - p[0], q[1] - p[1]
        # inside = left of edge: cross(e, x-p) >= 0  <=>  (ey)*x - (ex)*y <= ey*px - ex*py
        nx_, ny_ = ey, -ex
        c = nx_ * p[0] + ny_ * p[1]
        out = G.clip_halfplane(out, nx_, ny_, c)
    return out
