"""Classical architecture kit.  All sizes in metres; local frames: x along the facade,
y = depth (front face at y=0, wall behind at +y), z up — i.e. a facade faces -y.
Build pieces in local frames and place them with geom.frame/mat4."""
import math
import numpy as np
from .geom import Mesh, lathe, sweep, box, prism, cap, frame, mat4, apply, wall, opening_shape, ccw, TAU

# ----------------------------------------------------------------- moulding profiles
# profiles are lists of (s, t): s = projection outward (toward -y for a facade), t = height.
def _arc(s0, t0, s1, t1, convex=True, n=5):
    pts = []
    for i in range(1, n + 1):
        a = i / n * math.pi / 2
        if convex:
            pts.append((s0 + (s1 - s0) * math.sin(a), t0 + (t1 - t0) * (1 - math.cos(a))))
        else:
            pts.append((s0 + (s1 - s0) * (1 - math.cos(a)), t0 + (t1 - t0) * math.sin(a)))
    return pts


def cornice_profile(h, proj, kind='corinthian'):
    """crowning cornice of height h projecting proj. Starts at (0,0) on the wall face."""
    u = h / 10.0; p = proj / 10.0
    P = [(0, 0)]
    P += [(p * 0.6, 0), (p * 0.6, u * 0.6)]                      # fillet
    P += _arc(p * 0.6, u * 0.6, p * 1.4, u * 1.6, True, 4)        # ovolo (egg & dart)
    P += [(p * 1.6, u * 1.6), (p * 1.6, u * 2.8)]                 # dentil band
    P += [(p * 2.2, u * 2.8), (p * 2.2, u * 3.2)]
    P += _arc(p * 2.2, u * 3.2, p * 3.2, u * 4.2, True, 4)        # ovolo
    P += [(p * 7.6, u * 4.2) if kind == 'corinthian' else (p * 6.5, u * 4.2)]  # soffit (modillions zone)
    P += [(p * 8.6, u * 4.6)]
    P += [(p * 8.6, u * 6.4)]                                     # corona
    P += [(p * 8.9, u * 6.4), (p * 8.9, u * 6.8)]
    P += _arc(p * 8.9, u * 6.8, p * 10, u * 9.4, False, 5)        # cyma recta (sima)
    P += [(p * 10, u * 10), (0, u * 10)]
    return P


def architrave_profile(h, proj):
    u = h / 10.0; p = proj / 10.0
    return [(0, 0), (p * 2, 0), (p * 2, u * 2.8), (p * 4, u * 3), (p * 4, u * 5.8), (p * 6, u * 6), (p * 6, u * 8.4),
            (p * 7.5, u * 8.6), (p * 8.5, u * 9.3), (p * 10, u * 9.6), (p * 10, u * 10), (0, u * 10)]


def base_profile(h, proj):
    """attic base (plinth, torus, scotia, torus) projecting proj beyond the shaft face"""
    u = h / 10.0; p = proj
    P = [(0, 0), (p, 0), (p, u * 3)]
    P += _arc(p, u * 3, p * 0.75, u * 5, True, 4)                 # lower torus (rounded)
    P += [(p * 0.55, u * 5.3)]
    P += _arc(p * 0.55, u * 5.3, p * 0.35, u * 7.5, False, 3)     # scotia
    P += [(p * 0.5, u * 7.8)]
    P += _arc(p * 0.5, u * 7.8, p * 0.25, u * 9.4, True, 3)       # upper torus
    P += [(p * 0.1, u * 9.6), (0, u * 10)]
    return P


def string_course(h, proj):
    u = h / 4; p = proj
    return [(0, 0), (p * 0.4, 0), (p * 0.4, u * 0.6), (p, u * 1.2), (p, u * 3), (p * 0.7, u * 3.4), (p * 0.7, u * 4), (0, u * 4)]


def plain_band(h, proj):
    return [(0, 0), (proj, 0), (proj, h), (0, h)]


def run(profile, x0, x1, z, mat, y=0.0, returns=True, back=0.0):
    """moulding running straight along x at height z on a wall face at y (projecting toward -y).
    With returns, the ends turn back into the wall (mitre) so the cut ends are closed."""
    path = [(x0, y, z), (x1, y, z)]
    m = sweep_facade(profile, path, mat, closed=False)
    return m


def sweep_facade(profile, path, mat, closed=False, smooth=False):
    """sweep with s pointing to the LEFT of travel direction (for x-ward runs that is -y,
    i.e. out of a facade that faces -y)."""
    return sweep(profile, path, mat, closed=closed, smooth=smooth)   # right of +x travel = -y = out


def moulding_path(profile, pts2d, z, mat, closed=False):
    """run a moulding along a 2D polyline (x,y) at height z; s points to the right of travel."""
    return sweep(profile, [(p[0], p[1], z) for p in pts2d], mat, closed=closed)


# ----------------------------------------------------------------- columns
def shaft_profile(r_bot, h, entasis=True, n=10, r_top=None):
    r_top = r_top if r_top is not None else r_bot * 0.85
    P = []
    for i in range(n + 1):
        t = i / n
        if entasis:
            # straight lower third, then curved diminution
            k = 0 if t < 1 / 3 else ((t - 1 / 3) / (2 / 3)) ** 1.6
        else:
            k = t
        P.append((r_bot + (r_top - r_bot) * k, h * t))
    return P


def column(d, h, order='corinthian', mat='travertine', cap_mat=None, seg=28, base=True, fluted=False, pedestal=0.0, detail=1.0):
    """free-standing column of lower diameter d, total height h (base + shaft + capital),
    standing at origin.  Returns Mesh."""
    cm = cap_mat or mat
    m = Mesh(); r = d / 2
    z = 0.0
    if pedestal > 0:
        m.merge(box(-r * 1.45, -r * 1.45, 0, r * 1.45, r * 1.45, pedestal, mat))
        z = pedestal
    if order in ('tuscan', 'doric'):
        hb = d * 0.5; hc = d * 0.5
    elif order == 'ionic':
        hb = d * 0.5; hc = d * 0.45
    else:
        hb = d * 0.5; hc = d * 1.17
    hs = h - pedestal - (hb if base else 0) - hc
    if base:
        # square plinth + lathe mouldings
        pl = hb * 0.3
        m.merge(box(-r * 1.38, -r * 1.38, z, r * 1.38, r * 1.38, z + pl, mat))
        bp = base_profile(hb - pl, r * 0.38)
        prof = [(r + s, z + pl + t) for (s, t) in bp][:-1] + [(r, z + hb)]
        m.merge(lathe(prof, seg, mat=mat))
        z += hb
    sp = shaft_profile(r, hs)
    if fluted and seg >= 24:
        m.merge(fluted_shaft(sp, z, 24 if order != 'tuscan' else 20, mat))
    else:
        m.merge(lathe([(rr, z + t) for (rr, t) in sp], seg, mat=mat))
    rt = sp[-1][0]
    z += hs
    # astragal
    m.merge(lathe([(rt, z - d * 0.02), (rt * 1.08, z), (rt * 1.08, z + d * 0.05), (rt, z + d * 0.07)], seg, mat=cm))
    if order in ('tuscan', 'doric'):
        m.merge(lathe([(rt, z), (rt * 1.02, z + hc * 0.3), (rt * 1.25, z + hc * 0.55), (rt * 1.25, z + hc * 0.6)], seg, mat=cm))
        a = rt * 1.32
        m.merge(box(-a, -a, z + hc * 0.6, a, a, z + hc, cm))
    elif order == 'ionic':
        m.merge(ionic_capital(rt, hc, cm, seg).transformed(mat4((0, 0, z))))
    else:
        if detail < 0.2: m.merge(lite_capital(rt, hc, cm, seg).transformed(mat4((0, 0, z))))
        else: m.merge(corinthian_capital(rt, hc, cm, seg, detail).transformed(mat4((0, 0, z))))
    return m


def lite_capital(r, h, mat, seg=8):
    """cheap Corinthian capital for repeated/distant columns: leafy bell (two bulging rings), corner volutes, abacus."""
    m = Mesh()
    prof = [(r, 0), (r * 1.18, h * 0.12), (r * 1.08, h * 0.30), (r * 1.30, h * 0.45), (r * 1.18, h * 0.62), (r * 1.42, h * 0.78), (r * 1.25, h * 0.84)]
    m.merge(lathe(prof, seg, mat=mat))
    a = r * 1.45
    m.merge(box(-a, -a, h * 0.84, a, a, h, mat))
    for (sx, sy) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        m.merge(box(sx * a * 0.78 - r * 0.18, sy * a * 0.78 - r * 0.18, h * 0.62, sx * a * 0.78 + r * 0.18, sy * a * 0.78 + r * 0.18, h * 0.84, mat))
    return m


def fluted_shaft(prof, z0, nflutes, mat):
    """lathe with flutes: each flute = concave groove; built as a polar ring per row."""
    m = Mesh()
    sub = 4
    N = nflutes * sub
    rows = []
    for (r, t) in prof:
        row = []
        for k in range(N):
            a = TAU * k / N
            ph = (k % sub) / sub
            depth = 0.0 if ph == 0 else r * 0.045 * math.sin(math.pi * ph)
            rr = r - depth
            row.append((rr * math.cos(a), rr * math.sin(a), z0 + t))
        rows.append(m.add_v(row))
    for i in range(len(prof) - 1):
        for k in range(N):
            k1 = (k + 1) % N
            m.face([rows[i] + k, rows[i] + k1, rows[i + 1] + k1, rows[i + 1] + k], mat, True)
    return m


def corinthian_capital(r, h, mat, seg=28, detail=1.0):
    """Corinthian capital on a shaft top of radius r, height h (bell to top of abacus).
    Two rows of 8 acanthus leaves with curled lobed tips, caulicoli with corner volutes and
    central helices, concave abacus with fleurons. detail<1 reduces segment counts."""
    m = Mesh()
    nL = max(4, int(7 * detail)); nW = 3
    def bell_r(z):  # kalathos radius at height z
        t = z / h
        return r * (1.0 + 0.10 * t + 0.06 * t * t)
    bell = [(bell_r(h * t), h * t) for t in (0, 0.25, 0.5, 0.7, 0.8)] + [(bell_r(h * 0.8) * 1.04, h * 0.82), (0, h * 0.82)]
    m.merge(lathe(bell, seg, mat=mat))
    up = np.array([0, 0, 1.0])

    def leaf(a, z0, lh, w, curl, lift=0.0):
        """acanthus leaf hugging the bell from z0, height lh, max width w; tip curls out by curl."""
        L = Mesh()
        ca, sa = math.cos(a), math.sin(a)
        rad = np.array([ca, sa, 0.0]); tan = np.array([-sa, ca, 0.0])
        rows = []
        for i in range(nL + 1):
            t = i / nL
            z = z0 + lh * t
            if t > 0.62:                      # tip turns outward and droops
                q = (t - 0.62) / 0.38
                out = curl * math.sin(q * math.pi * 0.55)
                z = z0 + lh * (0.62 + 0.38 * (1 - 0.35 * q * q))
            else:
                out = curl * 0.08 * t
            base = bell_r(min(z, h * 0.8)) + r * 0.03 + lift
            # width profile with three lobes per side
            wl = w * (0.45 + 0.75 * math.sin(math.pi * min(1.0, 0.15 + t * 0.95))) * (1 - 0.75 * t ** 3)
            wl *= 1.0 + 0.12 * math.cos(t * math.pi * 6)
            row = []
            for k in range(nW * 2 + 1):
                u = (k / (nW * 2)) * 2 - 1           # -1..1 across
                cup = r * 0.05 * (1 - u * u)          # leaf is cupped: middle pushed out
                rib = r * 0.025 * math.exp(-(u * 6) ** 2)
                # sides wrap around the bell a little
                ang_off = u * wl / 2 / base
                p = rad * math.cos(ang_off) * (base + out + cup + rib) + tan * math.sin(ang_off) * (base + out + cup + rib)
                row.append(p + up * (z - r * 0.03 * u * u * (1 if t > 0.6 else 0)))
            rows.append(L.add_v(row))
        for i in range(nL):
            for k in range(nW * 2):
                L.face([rows[i] + k, rows[i] + k + 1, rows[i + 1] + k + 1, rows[i + 1] + k], mat, True)
        # underside of the curled tip (thickness) — back faces
        back = []
        for i in range(nL + 1):
            back.append(L.add_v([np.array(L.V[rows[i] + k]) - rad * r * 0.035 for k in range(nW * 2 + 1)]))
        for i in range(int(nL * 0.6), nL):
            for k in range(nW * 2):
                L.face([back[i] + k, back[i + 1] + k, back[i + 1] + k + 1, back[i] + k + 1], mat, True)
        return L

    for k in range(8):                                    # lower row
        a = TAU * k / 8
        m.merge(leaf(a, 0.0, h * 0.40, r * 0.86, r * 0.42, lift=r * 0.03))
    for k in range(8):                                    # upper row (between)
        a = TAU * k / 8 + TAU / 16
        m.merge(leaf(a, h * 0.05, h * 0.64, r * 0.84, r * 0.46, lift=r * 0.06))

    def scroll(a, z0, length, coil, width, out0, rise):
        """caulicolus stalk rising then coiling outward into a volute (ribbon with thickness)."""
        V = Mesh()
        ca, sa = math.cos(a), math.sin(a)
        rad = np.array([ca, sa, 0.0]); tan = np.array([-sa, ca, 0.0])
        N = 18; pts = []
        for i in range(N + 1):
            t = i / N
            if t < 0.4:
                q = t / 0.4
                pts.append(rad * (out0 + length * 0.35 * q) + up * (z0 + rise * q))
            else:
                q = (t - 0.4) / 0.6
                ang = q * math.pi * 1.75
                rr = coil * (1 - 0.6 * q)
                c0 = rad * (out0 + length * 0.35) + up * (z0 + rise)
                pts.append(c0 + rad * (rr * math.sin(ang) + length * 0.25 * q) + up * (rr * (1 - math.cos(ang))))
        o = V.add_v([p + tan * s * width / 2 + rad * d for p in pts for (s, d) in ((-1, 0), (1, 0), (1, -width * 0.6), (-1, -width * 0.6))])
        for i in range(N):
            b0 = o + 4 * i; b1 = b0 + 4
            for j in range(4):
                j1 = (j + 1) % 4
                V.face([b0 + j, b0 + j1, b1 + j1, b1 + j], mat, True)
        return V

    for k in range(4):
        a = TAU * k / 4 + TAU / 8                         # diagonals -> corner volutes
        m.merge(scroll(a, h * 0.56, r * 1.15, r * 0.22, r * 0.26, r * 1.08, h * 0.16))
        for d in (-1, 1):                                   # helices toward the face centres
            m.merge(scroll(a + d * 0.42, h * 0.60, r * 0.55, r * 0.12, r * 0.16, r * 1.12, h * 0.12))
    # abacus: concave sides, clipped corners at diagonal radius ~1.72 r
    A = r * 1.72; zA = h * 0.82
    pts = []
    for k in range(4):
        c0 = np.array([math.cos(TAU * k / 4 + TAU / 8), math.sin(TAU * k / 4 + TAU / 8)]) * A
        c1 = np.array([math.cos(TAU * (k + 1) / 4 + TAU / 8), math.sin(TAU * (k + 1) / 4 + TAU / 8)]) * A
        nrm = -(c0 + c1) / 2; nrm /= np.linalg.norm(nrm)
        dirv = (c1 - c0) / np.linalg.norm(c1 - c0)
        clip = r * 0.12
        for i in range(9):
            t = i / 8
            p = c0 + dirv * clip + (c1 - c0 - 2 * dirv * clip) * t
            p = p + nrm * (A * 0.13 * math.sin(math.pi * t))
            pts.append(tuple(p))
    m.merge(prism([pts], zA, zA + (h - zA) * 0.45, mat))
    big = [tuple(np.array(p) * 1.03) for p in pts]
    m.merge(prism([big], zA + (h - zA) * 0.45, h, mat))
    for k in range(4):                                    # fleurons
        a = TAU * k / 4
        c = (math.cos(a) * A * 0.62, math.sin(a) * A * 0.62)
        m.merge(lathe([(0, 0), (r * 0.10, h * 0.02), (r * 0.14, h * 0.08), (r * 0.08, h * 0.13), (0, h * 0.14)], 8, mat=mat,
                      center=(c[0], c[1], zA - h * 0.06)))
    return m


def ionic_capital(r, h, mat, seg=24):
    m = Mesh()
    m.merge(lathe([(r, 0), (r * 1.12, h * 0.3), (r * 1.12, h * 0.45), (0, h * 0.45)], seg, mat=mat))
    w = r * 2.9
    m.merge(box(-w / 2, -r * 1.05, h * 0.45, w / 2, r * 1.05, h * 0.75, mat))
    for sx in (-1, 1):
        for sy in (-1, 1):
            pass
    # volutes as cylinders along y at both ends
    for sx in (-1, 1):
        m.merge(lathe([(0, -r * 1.05), (r * 0.42, -r * 1.05), (r * 0.42, r * 1.05), (0, r * 1.05)], 14, mat=mat)
                .transformed(frame((sx * w * 0.42, 0, h * 0.42), (1, 0, 0), (0, 0, -1), (0, 1, 0))))
    m.merge(box(-w * 0.45, -w * 0.45 * 0.75, h * 0.75, w * 0.45, w * 0.45 * 0.75, h, mat))
    return m


def pilaster(w, h, depth, order='corinthian', mat='travertine', cap_mat=None, fluted=False):
    """pilaster on a wall face: x in [-w/2,w/2], projecting depth toward -y from y=0."""
    m = Mesh(); cm = cap_mat or mat
    hb = w * 0.5; hc = w * (1.17 if order == 'corinthian' else 0.55)
    hs = h - hb - hc
    pr = w * 0.13
    # base
    m.merge(box(-w / 2 - pr, -depth - pr, 0, w / 2 + pr, 0, hb * 0.3, mat))
    bp = base_profile(hb * 0.7, pr)
    m.merge(sweep([(s, hb * 0.3 + t) for (s, t) in bp], [(-w / 2, 0, 0), (-w / 2, -depth, 0), (w / 2, -depth, 0), (w / 2, 0, 0)], mat))
    # shaft
    if fluted:
        nf = 7; fw = w / (nf + (nf + 1) * 0.35)
        m.merge(box(-w / 2, -depth, hb, w / 2, 0, hb + hs, mat, faces=('-x', '+x')))
        x = -w / 2
        for i in range(nf):
            x0 = -w / 2 + fw * 0.35 * (i + 1) + fw * i
            m.merge(box(x, -depth, hb, x0, -depth + 0.0, hb + hs, mat, faces=('-y',)))
            # flute: shallow channel
            m.merge(box(x0, -depth + fw * 0.25, hb + fw, x0 + fw, -depth + fw * 0.25, hb + hs - fw, mat, faces=('-y',)))
            m.merge(box(x0, -depth, hb, x0 + fw, -depth + fw * 0.25, hb + fw, mat, faces=('-y', '+z')))
            m.merge(box(x0, -depth, hb + hs - fw, x0 + fw, -depth + fw * 0.25, hb + hs, mat, faces=('-y', '-z')))
            m.merge(box(x0, -depth, hb + fw, x0, -depth + fw * 0.25, hb + hs - fw, mat, faces=('+x',)))
            m.merge(box(x0 + fw, -depth, hb + fw, x0 + fw, -depth + fw * 0.25, hb + hs - fw, mat, faces=('-x',)))
            x = x0 + fw
        m.merge(box(x, -depth, hb, w / 2, -depth, hb + hs, mat, faces=('-y',)))
    else:
        m.merge(box(-w / 2, -depth, hb, w / 2, 0, hb + hs, mat, faces=('-y', '-x', '+x')))
    # capital: flattened corinthian = half capital squashed onto the pilaster face
    z = hb + hs
    if order == 'corinthian':
        c = corinthian_capital(w * 0.5, hc, cm, 16)
        # keep only the front half, flatten depth
        c2 = Mesh()
        V = np.array(c.V)
        keep = [i for i, f in enumerate(c.F) if np.mean(V[f, 1]) < w * 0.15]
        sub = Mesh(); sub.V = c.V
        for i in keep:
            sub.F.append(c.F[i]); sub.M.append(c.M[i]); sub.S.append(c.S[i]); sub.UV.append(None)
        Vs = np.array(sub.V); Vs[:, 1] = np.minimum(Vs[:, 1], 0) * (depth + w * 0.25) / (w * 0.75) 
        sub.V = Vs.tolist()
        m.merge(sub.transformed(mat4((0, 0, z))))
        m.merge(box(-w / 2, -depth, z, w / 2, 0, z + hc * 0.86, cm, faces=('-x', '+x')))
    else:
        m.merge(box(-w / 2 - pr * 0.6, -depth - pr * 0.6, z, w / 2 + pr * 0.6, 0, z + hc, cm))
    return m


# ----------------------------------------------------------------- entablature
def entablature(x0, x1, z, h, proj, mat, frieze_mat=None, kind='corinthian', y=0.0):
    """architrave (0.3h) + frieze (0.3h) + cornice (0.4h) running along x at the wall face y.
    The cornice projects proj; returns run closed at both ends."""
    m = Mesh()
    ha, hf, hc = h * 0.3, h * 0.3, h * 0.4
    ap = architrave_profile(ha, proj * 0.12)
    m.merge(straight(ap, x0, x1, z, y, mat))
    m.merge(straight([(0, 0), (proj * 0.04, 0), (proj * 0.04, hf), (0, hf)], x0, x1, z + ha, y, frieze_mat or mat))
    m.merge(straight(cornice_profile(hc, proj), x0, x1, z + ha + hf, y, mat))
    return m


def straight(profile, x0, x1, z, y, mat, end_caps=True):
    """profile run along +x at wall face y (projection toward -y), closed ends."""
    m = Mesh()
    P = [(s, t) for (s, t) in profile]
    n = len(P)
    o = m.add_v([(x0, y - s, z + t) for (s, t) in P] + [(x1, y - s, z + t) for (s, t) in P])
    for i in range(n - 1):
        m.face([o + i, o + n + i, o + n + i + 1, o + i + 1], mat)
    if end_caps:
        poly = [(s, t) for (s, t) in P]
        # cap at x0 facing -x and at x1 facing +x: triangulate profile polygon
        L = ccw(poly)
        Fx0 = frame((x0, y, z), (0, -1, 0), (0, 0, 1), (-1, 0, 0))   # local (s,t) -> (x0, y-s, z+t)
        c0 = cap([poly], 0, mat, True, Fx0)
        Fx1 = frame((x1, y, z), (0, -1, 0), (0, 0, 1), (-1, 0, 0))
        c1 = cap([poly], 0, mat, False, Fx1)
        # orientation: verify normals point outward in x by flipping if needed
        m.merge(fix_orient(c0, (-1, 0, 0))); m.merge(fix_orient(c1, (1, 0, 0)))
    return m


def fix_orient(m, want):
    """flip all faces of a planar cap so its normal agrees with `want`."""
    if not m.F: return m
    V = np.array(m.V); f = m.F[0]
    n = np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]])
    if np.dot(n, want) < 0:
        m.F = [ff[::-1] for ff in m.F]
    return m


def broken_entablature(xs, z, h, proj, mat, y=0.0, ressauts=(), frieze_mat=None):
    """entablature along x from xs[0] to xs[-1] that breaks forward (ressaut) over given
    (xa, xb, dy) ranges, e.g. over columns that stand proud of the wall."""
    m = Mesh()
    # build a 2D path in plan along the face with steps, then sweep each layer
    pts = [(xs[0], y)]
    for (xa, xb, dy) in sorted(ressauts):
        pts += [(xa, y), (xa, y - dy), (xb, y - dy), (xb, y)]
    pts += [(xs[-1], y)]
    clean = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, clean[-1]) > 1e-6: clean.append(p)
    ha, hf, hc = h * 0.3, h * 0.3, h * 0.4
    for prof, zz, mm in ((architrave_profile(ha, proj * 0.12), z, mat),
                         ([(0, 0), (proj * 0.04, 0), (proj * 0.04, hf), (0, hf)], z + ha, frieze_mat or mat),
                         (cornice_profile(hc, proj), z + ha + hf, mat)):
        # s outward = -y side = LEFT of +x travel -> geom.sweep wants right: negate s
        m.merge(sweep(prof, [(p[0], p[1], zz) for p in clean], mm, caps=True))
    return m


# ----------------------------------------------------------------- misc elements
def baluster(h, r, mat, seg=10):
    u = h / 10
    if seg <= 6:
        prof = [(r * 0.85, u * 0.6), (r * 0.55, u * 1.4), (r * 0.95, u * 3.8), (r * 0.4, u * 6.6), (r * 0.5, u * 8.2), (r * 0.75, u * 8.8), (r * 0.75, u * 10)]
        return lathe(prof, seg, mat=mat)
    prof = [(r * 0.9, 0), (r * 0.9, u * 0.8), (r * 0.6, u * 1.1), (r * 0.55, u * 1.6), (r * 0.95, u * 3.6), (r * 0.9, u * 4.6),
            (r * 0.45, u * 6.4), (r * 0.35, u * 7.4), (r * 0.5, u * 7.9), (r * 0.5, u * 8.4), (r * 0.75, u * 8.8), (r * 0.75, u * 10), (0, u * 10)]
    return lathe([(0, 0)] + prof, seg, mat=mat)


def balustrade(x0, x1, z, h, depth, mat, y=0.0, pier_every=None, pier_w=None, bal_seg=8):
    """balustrade along x on top of something, front face at y (toward -y), depth into +y."""
    m = Mesh()
    hp = h * 0.18; hr = h * 0.16
    pier_w = pier_w or depth * 1.2
    m.merge(box(x0, y, z, x1, y + depth, z + hp, mat))                      # plinth
    m.merge(box(x0 - 0.04, y - 0.04, z + h - hr, x1 + 0.04, y + depth + 0.04, z + h, mat))  # rail
    bh = h - hp - hr; br = depth * 0.38
    L = x1 - x0
    piers = []
    if pier_every:
        n = max(1, round(L / pier_every)); piers = [x0 + L * i / n for i in range(n + 1)]
    else:
        piers = [x0, x1]
    for i in range(len(piers) - 1):
        a, b = piers[i] + pier_w / 2, piers[i + 1] - pier_w / 2
        nb = max(1, int((b - a) / (br * 2.6)))
        for k in range(nb):
            cx = a + (b - a) * (k + 0.5) / nb
            m.merge(baluster(bh, br, mat, bal_seg).transformed(mat4((cx, y + depth / 2, z + hp))))
    for p in piers:
        m.merge(box(p - pier_w / 2, y - 0.02, z + hp, p + pier_w / 2, y + depth + 0.02, z + h - hr, mat))
    return m


def pediment_tri(x0, x1, z, rise, depth, proj, h_corn, mat, y=0.0, tymp_mat=None):
    """triangular pediment over [x0,x1] whose base sits at z on face y. raking cornices
    swept along the slopes; tympanum recessed."""
    m = Mesh()
    xc = (x0 + x1) / 2
    prof = cornice_profile(h_corn, proj)
    # horizontal cornice already given by entablature below; raking cornices:
    left = [(x0 - proj * 0.2, y, z), (xc, y, z + rise)]
    right = [(xc, y, z + rise), (x1 + proj * 0.2, y, z)]
    for path in (left, right):
        m.merge(sweep(prof, path, mat, up=(0, 0, 1)))
    # tympanum
    tri = [(x0 + proj, z + h_corn * 0.2), (x1 - proj, z + h_corn * 0.2), (xc, z + rise - h_corn * 0.4)]
    m.merge(fix_orient(cap([tri], 0, tymp_mat or mat, True, frame((0, y - 0.01, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
    # roof behind
    m.merge(prism([[(x0, y), (x1, y), (x1, y + depth), (x0, y + depth)]], z, z + 0.01, mat, top=False))
    return m


def niche(w, h, depth, mat, seg=12):
    """semicircular niche with a conch: opening width w, total height h, in a wall face y=0,
    recessing to +y. local origin bottom centre."""
    m = Mesh(); r = w / 2; zs = h - r
    # cylinder half (back wall), normals facing inward (toward -y)
    pts = []
    for i in range(seg + 1):
        a = math.pi * i / seg
        pts.append((r * math.cos(a), min(depth, r) * math.sin(a)))
    o = m.add_v([(p[0], p[1], 0) for p in pts] + [(p[0], p[1], zs) for p in pts])
    n = len(pts)
    for i in range(n - 1):
        m.face([o + i + 1, o + i, o + n + i, o + n + i + 1], mat, True)
    # conch: quarter sphere
    rows = []
    for j in range(seg // 2 + 1):
        b = (math.pi / 2) * j / (seg // 2)
        rows.append(m.add_v([(r * math.cos(b) * p[0] / r, math.cos(b) * p[1], zs + r * math.sin(b)) for p in pts]))
    for j in range(seg // 2):
        for i in range(n - 1):
            m.face([rows[j] + i + 1, rows[j] + i, rows[j + 1] + i, rows[j + 1] + i + 1], mat, True)
    # floor of niche
    m.merge(fix_orient(cap([[(p[0], p[1]) for p in pts]], 0, mat, True), (0, 0, 1)))
    return m


def aedicule(x, z, w, h, mat, kind='tri', y=0.0, frame_w=None, proj=None, ped_mat=None, window=True, glass='glass'):
    """window/door surround: moulded frame + small entablature + pediment ('tri'|'seg'|'flat').
    Opening itself is assumed cut in the wall; this adds the frame on the face y."""
    m = Mesh()
    fw = frame_w or w * 0.12
    pj = proj or fw * 0.5
    # jambs and head as boxes (with a small profile)
    m.merge(box(x - w / 2 - fw, y - pj, z, x - w / 2, y, z + h, mat))
    m.merge(box(x + w / 2, y - pj, z, x + w / 2 + fw, y, z + h, mat))
    m.merge(box(x - w / 2 - fw, y - pj, z + h, x + w / 2 + fw, y, z + h + fw, mat))
    # sill
    m.merge(box(x - w / 2 - fw * 1.3, y - pj * 1.6, z - fw * 0.35, x + w / 2 + fw * 1.3, y, z, mat))
    # frieze + cornice
    zc = z + h + fw
    m.merge(box(x - w / 2 - fw, y - pj * 0.6, zc, x + w / 2 + fw, y, zc + fw * 0.9, mat))
    cp = cornice_profile(fw * 1.1, pj * 1.6)
    m.merge(straight(cp, x - w / 2 - fw * 1.4, x + w / 2 + fw * 1.4, zc + fw * 0.9, y, mat))
    ztop = zc + fw * 2.0
    if kind == 'tri':
        m.merge(pediment_tri(x - w / 2 - fw * 1.4, x + w / 2 + fw * 1.4, ztop, (w + fw * 2.8) * 0.22, 0.05, pj * 1.4, fw * 0.9, mat, y))
    elif kind == 'seg':
        m.merge(pediment_seg(x - w / 2 - fw * 1.4, x + w / 2 + fw * 1.4, ztop, (w + fw * 2.8) * 0.2, pj * 1.4, fw * 0.9, mat, y))
    if window:
        m.merge(fix_orient(cap([opening_shape(w, h, 'rect', x=x - w / 2, y=z)], 0, glass, True, frame((0, y + 0.25, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
    return m


def pediment_seg(x0, x1, z, rise, proj, h_corn, mat, y=0.0, n=10):
    m = Mesh()
    xc = (x0 + x1) / 2; half = (x1 - x0) / 2
    R = (half ** 2 + rise ** 2) / (2 * rise)
    zc = z + rise - R
    a0 = math.asin(half / R)
    path = []
    for i in range(n + 1):
        a = -a0 + 2 * a0 * i / n
        path.append((xc + R * math.sin(a), y, zc + R * math.cos(a)))
    prof = cornice_profile(h_corn, proj)
    # along a curve the 'up' must follow the radial direction -> sweep with per-point up
    m.merge(sweep_radial(prof, path, (xc, y, zc), mat))
    tymp = [(p[0], p[2]) for p in path]
    tymp = [(x0 + proj, z)] + [(p[0], p[1] - h_corn * 0.1) for p in tymp[1:-1]] + [(x1 - proj, z)]
    m.merge(fix_orient(cap([tymp], 0, mat, True, frame((0, y - 0.01, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0))), (0, -1, 0)))
    return m


def sweep_radial(profile, path, center, mat):
    """sweep where the profile's t axis points radially away from center (for arches)."""
    m = Mesh()
    C = np.array(center, float)
    P = [np.array(p, float) for p in path]
    rings = []
    for i, p in enumerate(P):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]); d /= np.linalg.norm(d)
        up = p - C; up = up - d * np.dot(up, d); up /= np.linalg.norm(up)
        right = np.cross(d, up)
        rings.append(m.add_v([p + right * s + up * t for (s, t) in profile]))
    n = len(profile)
    for i in range(len(P) - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(n - 1):
            m.face([A + j, B + j, B + j + 1, A + j + 1], mat)
    m.face([rings[0] + j for j in range(n)][::-1], mat)
    m.face([rings[-1] + j for j in range(n)], mat)
    return m


def arch_moulding(cx, zs, r, w, proj, mat, y=0.0, n=16):
    """archivolt: a band of width w and projection proj following a semicircle of radius r (to the
    inner edge) centred at (cx, zs) on the wall face y."""
    path = [(cx + (r + w / 2) * math.cos(a), y, zs + (r + w / 2) * math.sin(a)) for a in np.linspace(math.pi, 0, n + 1)]
    prof = [(-0.0, -w / 2), (-proj, -w / 2), (-proj, w / 2), (0, w / 2)]
    prof = [(0, -w / 2), (proj, -w / 2), (proj * 0.7, 0), (proj, w / 2), (0, w / 2)]
    return sweep_radial(prof, path, (cx, y, zs), mat)


def dome_shell(profile_out, seg, mat, ribs=0, rib_w=0.0, rib_h=0.0, rib_mat=None, center=(0, 0, 0)):
    """revolved dome (outer surface), optional raised ribs following the profile."""
    m = lathe(profile_out, seg, mat=mat, center=center)
    if ribs:
        for k in range(ribs):
            a = TAU * k / ribs
            ca, sa = math.cos(a), math.sin(a)
            path = []
            for (r, z) in profile_out:
                if r < rib_w: break
                path.append((center[0] + r * ca, center[1] + r * sa, center[2] + z))
            if len(path) < 2: continue
            # profile: rectangle bump, local s across (tangent), t outward (normal of curve)
            prof = [(-rib_w / 2, -0.05), (-rib_w / 2, rib_h), (rib_w / 2, rib_h), (rib_w / 2, -0.05)]
            m.merge(sweep_normal(prof, path, (center[0], center[1]), rib_mat or mat))
    return m


def sweep_normal(profile, path, axis_xy, mat):
    """sweep a profile along a meridian curve of a surface of revolution: s along the
    circumferential direction, t along the outward surface normal (in the meridian plane).
    Profiles are given left->right over the top (s from - to +); reversed here so faces point out."""
    m = Mesh()
    profile = list(profile)[::-1]
    P = [np.array(p, float) for p in path]
    rings = []
    for i, p in enumerate(P):
        d = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]; d /= np.linalg.norm(d)
        radial = np.array([p[0] - axis_xy[0], p[1] - axis_xy[1], 0.0]); rn = np.linalg.norm(radial)
        radial = radial / rn if rn > 1e-9 else np.array([1.0, 0, 0])
        circ = np.cross(np.array([0, 0, 1.0]), radial)
        nrm = np.cross(circ, d); nrm /= np.linalg.norm(nrm)
        if np.dot(nrm, radial) < 0 and abs(np.dot(nrm, radial)) > 0.05: nrm = -nrm
        if np.dot(nrm, radial) < 0.05 and nrm[2] < 0: nrm = -nrm
        rings.append(m.add_v([p + circ * s + nrm * t for (s, t) in profile]))
    n = len(profile)
    for i in range(len(P) - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(n - 1):
            m.face([A + j, B + j, B + j + 1, A + j + 1], mat)
    m.face([rings[-1] + j for j in range(n)], mat)
    return m


def stairs(x0, x1, y0, depth, z0, rise, nsteps, mat, toward=-1):
    """straight flight along x-width [x0,x1], going down toward y0 + toward*depth."""
    m = Mesh()
    tread = depth / nsteps; hstep = rise / nsteps
    for i in range(nsteps):
        ya = y0 + toward * tread * i
        yb = y0 + toward * tread * nsteps
        zt = z0 + rise - hstep * i
        a, b = sorted((ya, yb))
        m.merge(box(x0, a, z0, x1, b, zt, mat, faces=('+z', '-y', '+y', '-x', '+x') if i == 0 else ('+z', '-y' if toward < 0 else '+y', '-x', '+x')))
    return m
