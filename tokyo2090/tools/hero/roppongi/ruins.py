"""Generic ruin shells: prisms (polygon + z0..z1) -> walls with facade atlas UVs, broken bays, sheared tops,
exposed slabs, stair cores, collision top surfaces."""
import math
import numpy as np
import lib
from lib import vnoise, fbm, norm, ccw, offset_poly

FAC_ROWS = ['glass', 'glass_ruin', 'apt', 'apt_ruin', 'shop', 'tile', 'mori', 'mori_ruin']
ATLAS_W = 32.0   # metres per u


def row_uv(row, s0, s1, f0=(0.0, 0.0), f1=(1.0, 1.0)):
    """quad uvs for facade row; f0=(bottom-left frac, bottom-right frac) f1=(top-right, top-left)"""
    r = FAC_ROWS.index(row)
    vb = 1 - (r + 1) / 8 + 0.003; vt = 1 - r / 8 - 0.003
    V = lambda f: vb + (vt - vb) * f
    return [(s0 / ATLAS_W, V(f0[0])), (s1 / ATLAS_W, V(f0[1])), (s1 / ATLAS_W, V(f1[0])), (s0 / ATLAS_W, V(f1[1]))]


class Cut:
    """top-of-ruin field. kind: none | top | wedge | both.  cut(x,y) -> height above which nothing stands"""
    def __init__(self, kind='none', h0=1e9, grad=(0.0, 0.0), c=(0.0, 0.0), jag=1.5, seed=0, top=1e9, h1=None, grad1=None):
        self.kind = kind; self.h0 = h0; self.g = grad; self.c = c; self.jag = jag; self.seed = seed; self.top = top
        self.h1 = h1; self.g1 = grad1

    def plane(self, x, y):
        if self.kind == 'none':
            return np.full(np.shape(x), 1e9) if np.ndim(x) else 1e9
        z = self.h0 + self.g[0] * (np.asarray(x) - self.c[0]) + self.g[1] * (np.asarray(y) - self.c[1])
        if self.h1 is not None:
            z = np.minimum(z, self.h1 + self.g1[0] * (np.asarray(x) - self.c[0]) + self.g1[1] * (np.asarray(y) - self.c[1]))
        return np.minimum(z, self.top)

    def __call__(self, x, y):
        if self.kind == 'none':
            return 1e9
        n = (fbm(np.asarray(x) / 6.0, np.asarray(y) / 6.0, self.seed, 3) - 0.5) * 2 * self.jag
        n2 = (vnoise(np.asarray(x) / 1.7, np.asarray(y) / 1.7, self.seed + 9) - 0.5) * self.jag * 0.6
        return self.plane(x, y) + n + n2


def clip_halfplane(poly, f):
    """keep part of polygon where f(p) > 0 (f linear along edges assumed) - Sutherland-Hodgman"""
    out = []
    n = len(poly)
    for i in range(n):
        a = poly[i]; b = poly[(i + 1) % n]
        fa = f(a); fb = f(b)
        if fa > 0:
            out.append(a)
        if (fa > 0) != (fb > 0):
            t = fa / (fa - fb)
            out.append(a + (b - a) * t)
    return out


def jag_cut_edges(poly, f, amp, seed):
    """insert jitter along edges that lie on the clip boundary (where f ~ 0)"""
    out = []
    n = len(poly)
    rr = lib.rng(seed)
    for i in range(n):
        a = poly[i]; b = poly[(i + 1) % n]
        out.append(a)
        if abs(f(a)) < 0.05 and abs(f(b)) < 0.05:
            L = np.linalg.norm(b - a)
            k = int(L / 3.0)
            d = norm(b - a); nrm = np.array([d[1], -d[0]])   # outward for ccw
            for j in range(1, k):
                p = a + (b - a) * j / k
                out.append(p - nrm * rr.uniform(0.0, amp))
    return out


class Collider:
    def __init__(self):
        self.polys = []    # list of list of 3d points (horizontal or not)

    def top(self, pts2, z):
        if len(pts2) >= 3:
            self.polys.append([(float(p[0]), float(p[1]), float(z)) for p in pts2])

    def poly(self, pts3):
        self.polys.append([tuple(map(float, p)) for p in pts3])

    def box(self, c, size, rot=0.0):
        sx, sy, sz = size; cx, cy, cz = c
        ca, sa = math.cos(rot), math.sin(rot)
        P = lambda x, y, z: (cx + x * ca - y * sa, cy + x * sa + y * ca, cz + z)
        hx, hy = sx / 2, sy / 2
        top = [P(-hx, -hy, sz), P(hx, -hy, sz), P(hx, hy, sz), P(-hx, hy, sz)]
        self.polys.append(top)
        b = [P(-hx, -hy, 0), P(hx, -hy, 0), P(hx, hy, 0), P(-hx, hy, 0)]
        for i in range(4):
            self.polys.append([b[i], b[(i + 1) % 4], top[(i + 1) % 4], top[i]])

    def tris(self):
        return sum(len(p) - 2 for p in self.polys)


def slab(sc, region, z, thick, top_mat, bot_mat='interior', edge_mat='interior', uvs=4.0):
    if len(region) < 3:
        return
    tri = lib.triangulate([tuple(p) for p in region])
    tu = 11.0 if top_mat == 'top' else uvs
    top = sc[top_mat]; bot = sc[bot_mat]; ed = sc[edge_mat]
    for (a, b, c) in tri:
        P = [region[a], region[b], region[c]]
        top.poly([(p[0], p[1], z) for p in P], [(p[0] / tu, p[1] / tu) for p in P])
        if lib.mid():
            continue
        bot.poly([(p[0], p[1], z - thick) for p in P[::-1]], [(p[0] / uvs, p[1] / uvs) for p in P[::-1]])
    n = len(region)
    s = 0.0
    for i in range(n if not lib.mid() else 0):
        a = region[i]; b = region[(i + 1) % n]
        L = float(np.linalg.norm(b - a))
        ed.poly([(a[0], a[1], z - thick), (b[0], b[1], z - thick), (b[0], b[1], z), (a[0], a[1], z)],
                [(s / uvs, 0), ((s + L) / uvs, 0), ((s + L) / uvs, thick / uvs), (s / uvs, thick / uvs)])
        s += L


def ruin_prism(sc, col, poly, z0, z1, style, cut, seed, holes=0.06, seg=5.0, wall_mat='fac', top_mat='top',
               slab_all=False, core=None, parapet=True, ruin_rows=0.15, ground_row=True, interior='interior',
               collide=True, roof=True, rec=None, bid=''):
    """poly: list of (x,y) ccw.  style: dict(upper, ruin, ground, fh)"""
    poly = [np.asarray(p[:2], float) for p in ccw([tuple(p[:2]) for p in poly])]
    rr = lib.rng(seed)
    H = z1 - z0
    fh0 = style.get('fh', 3.5)
    if lib.mid():
        fh0 *= 2.0; seg *= 2.2; holes *= 0.6; slab_all = False
    n = max(1, int(round(H / fh0)))
    fh = H / n
    wb = sc[wall_mat]
    np_ = len(poly)
    # sample cut field over polygon for statistics
    bx = [p[0] for p in poly]; by = [p[1] for p in poly]
    gx, gy = np.meshgrid(np.linspace(min(bx), max(bx), 9), np.linspace(min(by), max(by), 9))
    ins = lib.points_in_poly(gx, gy, poly)
    cs = np.array([cut(p[0], p[1]) for p in poly] + list(np.atleast_1d(cut(gx[ins], gy[ins])) if ins.any() else []))
    cmin = float(cs.min()); cmax = float(cs.max())
    open_floor = set()
    s = rr.uniform(0, ATLAS_W)       # random start along the atlas so neighbours don't line up
    for i in range(np_):
        a = poly[i]; b = poly[(i + 1) % np_]
        L = float(np.linalg.norm(b - a))
        if L < 0.05:
            continue
        k_n = max(1, int(round(L / seg)))
        for k in range(k_n):
            p0 = a + (b - a) * k / k_n; p1 = a + (b - a) * (k + 1) / k_n
            S0 = s + L * k / k_n; S1 = s + L * (k + 1) / k_n
            c0 = float(cut(p0[0], p0[1])); c1 = float(cut(p1[0], p1[1]))
            pm = 0.5 * (p0 + p1); cm = float(cut(pm[0], pm[1]))
            for j in range(n):
                zb = z0 + j * fh; zt = zb + fh
                fo = 6.4 * int(float(lib._hash(seed, j)) * 5)     # per-floor atlas offset (keeps window columns aligned)
                s0 = S0 + fo; s1 = S1 + fo
                top_c = max(c0, c1, cm)
                if zb >= top_c - 0.25:
                    break
                near = float(np.clip(1 - (min(c0, c1) - zt) / (2.5 * fh), 0, 1))
                hn = vnoise((S0 + S1) * 0.5 / 7.0, zb / 6.0, seed + 3)
                p_hole = holes + 0.45 * near * (1 if cut.kind != 'none' else 0)
                if j > 0 and hn < p_hole:
                    open_floor.add(j)
                    if rr.random() < 0.18 and zt < top_c and not lib.mid():
                        # a facade panel hanging/peeled at an angle (stays on wall face, tilted out)
                        nrm = np.array([(b - a)[1], -(b - a)[0]]) / L
                        tilt = rr.uniform(0.4, 1.2)
                        dz = fh * math.cos(tilt); dout = fh * math.sin(tilt)
                        q0 = (p0[0], p0[1], zt); q1 = (p1[0], p1[1], zt)
                        q2 = (p1[0] + nrm[0] * dout, p1[1] + nrm[1] * dout, zt - dz)
                        q3 = (p0[0] + nrm[0] * dout, p0[1] + nrm[1] * dout, zt - dz)
                        row = style.get('ruin', style['upper'])
                        uvq = row_uv(row, s0, s1)
                        wb.poly([q3, q2, q1, q0], uvq)
                    continue
                if j == 0 and ground_row:
                    row = style.get('ground', style['upper'])
                elif near > 0.35 or rr.random() < ruin_rows:
                    row = style.get('ruin', style['upper'])
                else:
                    row = style['upper']
                t0 = min(zt, max(zb, c0)); t1 = min(zt, max(zb, c1)); tm = min(zt, max(zb, cm))
                if max(t0, t1, tm) - zb < 0.3:
                    continue
                f0 = (t0 - zb) / fh; f1 = (t1 - zb) / fh
                if t0 >= zt - 1e-3 and t1 >= zt - 1e-3 and tm >= zt - 1e-3:
                    wb.poly([(p0[0], p0[1], zb), (p1[0], p1[1], zb), (p1[0], p1[1], zt), (p0[0], p0[1], zt)],
                            row_uv(row, s0, s1))
                else:
                    # jagged broken top: pentagon with a dip/peak in the middle
                    jm = min(zt, max(zb + 0.2, tm + rr.uniform(-0.9, 0.4)))
                    fm = (jm - zb) / fh
                    u = row_uv(row, s0, s1, (0, 0), (f1, f0))
                    um = ((s0 + s1) * 0.5 / ATLAS_W, u[0][1] + (u[3][1] - u[0][1]) / max(f0, 1e-3) * fm if f0 > 1e-3 else u[0][1] + fm * 0.12)
                    pts = [(p0[0], p0[1], zb), (p1[0], p1[1], zb), (p1[0], p1[1], max(t1, zb + 0.05)),
                           (pm[0], pm[1], jm), (p0[0], p0[1], max(t0, zb + 0.05))]
                    r_ = FAC_ROWS.index(row); vb = 1 - (r_ + 1) / 8 + 0.003; vt = 1 - r_ / 8 - 0.003
                    V = lambda f: vb + (vt - vb) * min(max(f, 0), 1)
                    uvs = [(s0 / ATLAS_W, V(0)), (s1 / ATLAS_W, V(0)), (s1 / ATLAS_W, V((pts[2][2] - zb) / fh)),
                           ((s0 + s1) * 0.5 / ATLAS_W, V(fm)), (s0 / ATLAS_W, V((pts[4][2] - zb) / fh))]
                    wb.poly(pts, uvs)
                    open_floor.add(j)
        s += L
    # slabs
    inset = [np.asarray(p) for p in offset_poly(poly, -0.12)]
    tops = []
    for j in range(1, n + 1):
        z = z0 + j * fh
        if cut.kind != 'none' and z > cmax - 0.2:
            break
        is_roof = (j == n)
        near_cut = cut.kind != 'none' and z > cmin - fh * 1.2
        if not (is_roof or slab_all or near_cut or ((j in open_floor or j - 1 in open_floor) and not lib.mid())):
            continue
        region = inset
        if cut.kind != 'none' and z > cmin - 0.5:
            # clip by the cut plane (plane - z > 0) with noisy edge
            zoff = rr.uniform(-1.4, 1.4)
            f = lambda p, zo=zoff: float(cut.plane(p[0], p[1])) + zo - z
            region = clip_halfplane(inset, f)
            if len(region) < 3 or abs(lib.poly_area([tuple(p) for p in region])) < 2:
                continue
            # a slab torn at the break sags down from its edge
            if not lib.mid() and rr.random() < 0.35:
                best = None
                for q in range(len(region)):
                    a_, b_ = region[q], region[(q + 1) % len(region)]
                    if abs(f(a_)) < 0.05 and abs(f(b_)) < 0.05:
                        Lq = float(np.linalg.norm(b_ - a_))
                        if best is None or Lq > best[0]:
                            best = (Lq, a_, b_)
                if best and best[0] > 2.0:
                    Lq, a_, b_ = best
                    t0 = rr.uniform(0, 0.4); t1 = rr.uniform(0.6, 1.0)
                    pa = a_ + (b_ - a_) * t0; pb = a_ + (b_ - a_) * t1
                    dd = norm(b_ - a_); out = np.array([dd[1], -dd[0]])
                    sag = rr.uniform(0.5, 1.2); Ls = rr.uniform(2.0, min(6.0, fh * 1.8))
                    dv = np.r_[out * math.cos(sag) * Ls, -math.sin(sag) * Ls]
                    A = np.r_[pa, z]; B = np.r_[pb, z]
                    sc[top_mat].poly([A, B, B + dv, A + dv], [(0, 0), (1, 0), (1, 0.5), (0, 0.5)])
                    sc[interior].poly([A + dv - [0, 0, 0.3], B + dv - [0, 0, 0.3], B - [0, 0, 0.3], A - [0, 0, 0.3]])
            region = jag_cut_edges(region, f, 2.6, seed + j)
        exposed = is_roof or near_cut
        if is_roof and roof and cut.kind == 'none':
            slab(sc, region, z, 0.35, top_mat, interior, interior)
        elif exposed:
            slab(sc, region, z, 0.35, top_mat, interior, interior)
        else:
            slab(sc, region, z, 0.30, interior, interior, interior)
        tops.append((region, z))
        if collide and (exposed or is_roof):
            col.top(region, z)
        if rec is not None and (exposed or is_roof) and top_mat == 'top':
            rec.setdefault('tops', []).append(([tuple(map(float, p)) for p in region], z, bid))
    # parapet on intact roof
    if parapet and cut.kind == 'none' and roof and not lib.mid():
        pb = sc['conc']
        ph = 0.9
        ss = 0.0
        for i in range(np_):
            a = poly[i]; b = poly[(i + 1) % np_]
            L = float(np.linalg.norm(b - a))
            pb.poly([(a[0], a[1], z1), (b[0], b[1], z1), (b[0], b[1], z1 + ph), (a[0], a[1], z1 + ph)],
                    [(ss / 4, 0), ((ss + L) / 4, 0), ((ss + L) / 4, ph / 4), (ss / 4, ph / 4)])
            ii = [np.asarray(q) for q in offset_poly(poly, -0.25)]
            ai = ii[i]; bi = ii[(i + 1) % np_]
            pb.poly([(bi[0], bi[1], z1), (ai[0], ai[1], z1), (ai[0], ai[1], z1 + ph), (bi[0], bi[1], z1 + ph)],
                    [(ss / 4, 0), ((ss + L) / 4, 0), ((ss + L) / 4, ph / 4), (ss / 4, ph / 4)])
            pb.poly([(a[0], a[1], z1 + ph), (b[0], b[1], z1 + ph), (bi[0], bi[1], z1 + ph), (ai[0], ai[1], z1 + ph)],
                    [(0, 0), (L / 4, 0), (L / 4, 0.06), (0, 0.06)])
            ss += L
    if collide and not tops:
        col.top(inset, min(z1, cmax))
    if rec is not None:
        rec.setdefault('walls', []).append(([tuple(map(float, p)) for p in poly],
                                            (lambda x, y, c=cut, t=z1: min(t, float(c(x, y)))), z0, bid))
    # stair/lift core standing proud of the break
    if core is not None:
        cx, cy, w, d, rot = core
        ztop = min(z1 + 3.5, max(cmin, z0 + fh) + rr.uniform(0.5, 2.5) * fh) if cut.kind != 'none' else z1 + 3.2
        lib.box(sc['conc'], (cx, cy, z0), (w, d, ztop - z0), rot, uvscale=0.25)
        if collide:
            col.box((cx, cy, z0), (w, d, ztop - z0), rot)
    return tops, cmin, cmax, n, fh


def style_for(use, h, rnd):
    if use == '共同住宅':
        return dict(upper='apt', ruin='apt_ruin', ground='shop' if rnd.random() < 0.4 else 'apt', fh=3.1)
    if use in ('住宅', '店舗等併用住宅'):
        return dict(upper=rnd.choice(['tile', 'apt']), ruin='apt_ruin', ground='shop' if use != '住宅' else 'tile', fh=3.0)
    if use == '業務施設':
        if h > 30 or rnd.random() < 0.4:
            return dict(upper='glass', ruin='glass_ruin', ground='shop', fh=4.0)
        return dict(upper='tile', ruin='apt_ruin', ground='shop', fh=3.6)
    if use == '商業施設':
        return dict(upper=rnd.choice(['glass', 'tile']), ruin='glass_ruin', ground='shop', fh=4.5)
    if use == '文教厚生施設':
        return dict(upper='tile', ruin='apt_ruin', ground='tile', fh=3.8)
    return dict(upper=rnd.choice(['tile', 'apt', 'glass']), ruin='apt_ruin', ground='shop', fh=3.6)
