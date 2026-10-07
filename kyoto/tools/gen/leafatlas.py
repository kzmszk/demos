"""Leaf atlas for the tree cards (procedural, no photographs): 4 x 4 cells of 512 px.
Each cell is a cluster of leaves on fine twigs, drawn as shapes: R = luminance (the shader tints by species and season),
G = 'outer' mask (leaf tips, redden first in autumn), B = twig mask (bark-coloured), A = coverage (alpha test).
A normal map is derived from a height field (midribs raised, blades curved).

Cells:  0 maple (イロハモミジ: 7 deep, narrow, toothed lobes, 4-6 cm)   1 evergreen broadleaf (elliptic, glossy)   2 ginkgo (notched fans)
        3 cherry (ovate, acuminate, serrate)   4 pine (needle tufts)   5 cedar spray (sugi)   6 cypress fronds (hinoki)   7 willow strands
        8 bamboo leaves   9 bare twigs (winter)   10 azalea / box (small dense)   11 camellia (dense glossy)
        12 maple (オオモミジ: broader lobes, 6-9 cm)   13 zelkova (keyaki: small, two-ranked)   14 evergreen broadleaf (copy)
        15 maple (ハウチワカエデ: round, 9-11 shallow lobes)
The viewer picks one maple cell per tree.  Leaves are drawn at life size for their card (scale per kind, SCALE below),
G = a random value per leaf (the shader varies the colour leaf by leaf within a tree)."""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

C = 512
N = 4

def rng(s): return np.random.default_rng(s)

def rot(pts, a, c):
    ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + x * ca - y * sa, c[1] + x * sa + y * ca) for x, y in pts]

def maple_leaf(size):
    """palmate leaf outline (7 lobes), petiole at origin pointing -y; returns polygon points."""
    pts = []
    lobes = 7
    for k in range(lobes * 2 * 12 + 1):
        t = k / (lobes * 2 * 12)
        a = -math.pi * 0.92 + t * math.pi * 1.84         # spread of the lobes around the top
        lob = abs(math.sin(t * lobes * math.pi))
        r = size * (0.32 + 0.68 * lob ** 1.6)
        # serration
        r *= 1.0 + 0.05 * math.sin(t * lobes * math.pi * 6)
        pts.append((math.sin(a) * r, -math.cos(a) * r * -1.0 + size * 0.1))
    return pts

def ellipse_leaf(L, W, tip=1.0, serr=0.0):
    pts = []
    for k in range(41):
        t = k / 40 * 2 * math.pi
        x = math.sin(t) * W * 0.5 * (1 + serr * 0.15 * math.sin(t * 24))
        y = (1 - math.cos(t)) * 0.5 * L
        # pointed tip
        x *= (1.0 - (y / L) ** (2.5 / tip) * 0.6) if y > L * 0.5 else 1.0
        pts.append((x, y))
    return pts

def fan_leaf(size):
    pts = [(0, 0)]
    for k in range(25):
        a = -0.95 + k / 24 * 1.9
        r = size * (1.0 - 0.18 * (abs(a) < 0.12))     # the notch of the ginkgo fan
        pts.append((math.sin(a) * r, math.cos(a) * r))
    return pts

# metres per cell (the card size the species uses, treegen SPECIES card): leaves are drawn at life size
SCALE = {0: 0.8, 12: 0.8, 15: 0.8, 2: 1.1, 3: 1.0, 13: 1.25, 1: 1.25, 14: 1.25, 11: 1.0}

def saw(pts, amp, period, closed=False):
    """serrate an outline: teeth pointing forward along the outline"""
    out = []
    n = len(pts)
    acc = 0.0
    for i in range(n - (0 if closed else 1)):
        a = np.array(pts[i]); b = np.array(pts[(i + 1) % n]); d = b - a; L = float(np.hypot(*d))
        if L < 1e-6: continue
        nrm = np.array([d[1], -d[0]]) / L
        k = max(1, int(L / max(period / 4, 1e-6)))
        for j in range(k):
            t = j / k; acc += L / k
            ph = (acc / period) % 1.0
            out.append(tuple(a + d * t + nrm * amp * (ph ** 2)))
    return out

def lobe(L, W, ang, base=0.0, tooth=0.0, tip=1.3, pb=0.45, neck=0.0):
    """one lanceolate lobe from the leaf centre along angle ang (0 = +y): outline points"""
    left, right = [], []
    for k in range(25):
        s = k / 24
        w = W * (s ** pb) * ((1 - s) ** tip) / ((pb / (pb + tip)) ** pb * (tip / (pb + tip)) ** tip)
        if neck: u = min(1.0, s / neck); w *= u * u * (3 - 2 * u)          # narrowing to the base: deep sinuses
        y = base + s * (L - base)
        left.append((-w, y)); right.append((w, y))
    pts = left + right[::-1]
    if tooth: pts = saw(pts, tooth, L * 0.09, closed=True)
    ca, sa = math.cos(ang), math.sin(ang)
    return [(x * ca + y * sa, -x * sa + y * ca) for x, y in pts]

def palmate(size, kind, r):
    """a palmate maple leaf (petiole at the origin, blade toward +y): list of polygons (lobes + body), vein lines"""
    if kind == 0:     # イロハモミジ: 7 lobes cut deep, narrow, long-pointed, double-toothed
        angs = [0, 0.52, 1.05, 1.68]; lens = [1.0, 0.93, 0.78, 0.42]; W = 0.15; body = 0.15; tooth = 0.03; pb = 0.6; neck = 0.5
    elif kind == 12:  # オオモミジ: 7 broader lobes, finely and evenly toothed
        angs = [0, 0.55, 1.1, 1.72]; lens = [1.0, 0.95, 0.8, 0.48]; W = 0.21; body = 0.16; tooth = 0.02; pb = 0.6; neck = 0.35
    else:             # ハウチワカエデ: round, 9-11 shallow lobes
        n = int(r.integers(4, 6)); angs = [0] + [k * 2.75 / n for k in range(1, n + 1)]; lens = [1.0] + [1.0 - 0.35 * (k / n) ** 2 for k in range(1, n + 1)]
        W = 0.2; body = 0.55; tooth = 0.03; pb = 0.45; neck = 0.0
    polys, veins = [], []
    cy = size * 0.25                       # the blade's centre (where the lobes meet) above the petiole end
    for a, l in zip(angs, lens):
        for sgn in ((1,) if a == 0 else (1, -1)):
            aa = a * sgn * r.uniform(0.95, 1.05)
            pts = lobe(size * l, size * W * (0.9 + 0.2 * r.random()), aa, 0.0, size * tooth, tip=1.25 if kind == 0 else 1.0, pb=pb, neck=neck)
            polys.append([(x, y + cy) for x, y in pts])
            veins.append(((0, cy), (math.sin(aa) * size * l * 0.85, cy + math.cos(aa) * size * l * 0.85)))
    body_pts = [(math.sin(t) * size * body, cy + math.cos(t) * size * body) for t in np.linspace(0, 2 * math.pi, 24)]
    polys.append(body_pts)
    return polys, veins

def ginkgo_leaf(size, r):
    """a ginkgo fan: wedge base on a petiole, wavy outer edge, often notched in the middle; radial veins"""
    spread = r.uniform(1.0, 1.2); notch = r.uniform(0.0, 0.35) if r.random() < 0.7 else 0.0
    pts = [(0.0, size * 0.08)]
    for k in range(41):
        a = -spread + k / 40 * 2 * spread
        rr = size * (1.0 + 0.04 * math.sin(a * 23 + r.random())) * (1 - notch * math.exp(-(a / 0.06) ** 2))
        pts.append((math.sin(a) * rr, size * 0.08 + math.cos(a) * rr * 0.92))
    veins = [((0, size * 0.08), (math.sin(a) * size * 0.95, size * 0.08 + math.cos(a) * size * 0.88)) for a in np.linspace(-spread * 0.95, spread * 0.95, 13)]
    return [pts], veins

def ovate(L, Wd, r, tooth, tip=1.6, asym=0.0):
    """ovate / elliptic leaf, petiole at the origin toward +y, acuminate tip, toothed margin; midrib + side veins"""
    left, right = [], []
    for k in range(31):
        s = k / 30
        w = Wd * 0.5 * math.sin(math.pi * s ** 0.85) ** 0.9 * (1 - 0.35 * s ** (tip * 2))
        left.append((-w * (1 + asym * (1 - s)), s * L)); right.append((w, s * L))
    pts = left + right[::-1]
    if tooth: pts = saw(pts, tooth, L * 0.06, closed=True)
    veins = [((0, 0), (0, L * 0.95))] + [((0, L * t), (sg * Wd * 0.42, L * (t + 0.12))) for t in np.linspace(0.15, 0.75, 6) for sg in (-1, 1)]
    return [pts], veins

def broadleaf_cell(kind, r, W, S, cx, cy, ims, dr):
    """a spray of life-size leaves on fine twigs (maples, ginkgo, cherry, zelkova, evergreen oak)"""
    dl, do, dt, da, dh = dr
    ppm = W / SCALE[kind]                                   # working pixels per metre
    def stick(p0, p1, w, shade=70):
        for d in (dt, da): d.line([p0, p1], fill=255, width=max(1, int(w)))
        dl.line([p0, p1], fill=shade, width=max(1, int(w))); dh.line([p0, p1], fill=120, width=max(1, int(w)))
    def put(polys, veins, at, ang, shade, g, vein_d):
        D = (math.sin(ang), -math.cos(ang)); Pp = (math.cos(ang), math.sin(ang))
        tr = lambda x, y: (at[0] + Pp[0] * x + D[0] * y, at[1] + Pp[1] * x + D[1] * y)
        for poly in polys:
            q = [tr(x, y) for x, y in poly]
            da.polygon(q, fill=255); dl.polygon(q, fill=int(shade)); do.polygon(q, fill=int(g)); dh.polygon(q, fill=170)
        for a, b in veins:
            dl.line([tr(*a), tr(*b)], fill=int(max(0, min(255, shade + vein_d))), width=max(1, S))
            dh.line([tr(*a), tr(*b)], fill=200, width=max(1, S))
    def leaf_at(base, ang):
        g = r.uniform(0, 255); shade = r.uniform(165, 240)
        if kind in (0, 12, 15):
            size = ppm * (r.uniform(0.022, 0.03) if kind == 0 else r.uniform(0.03, 0.04) if kind == 12 else r.uniform(0.032, 0.042))
            pet = size * r.uniform(0.5, 0.9)
            tip = (base[0] + math.sin(ang) * pet, base[1] - math.cos(ang) * pet)
            stick(base, tip, S * 1.2, 120)
            polys, veins = palmate(size, kind, r)
            put(polys, veins, tip, ang + r.normal(0, 0.15), shade, g, 22)
        elif kind == 2:
            size = ppm * r.uniform(0.025, 0.035); pet = size * r.uniform(0.6, 1.1)
            tip = (base[0] + math.sin(ang) * pet, base[1] - math.cos(ang) * pet)
            stick(base, tip, S, 120)
            polys, veins = ginkgo_leaf(size, r); put(polys, veins, tip, ang, shade, g, -18)
        else:
            if kind == 3: L = ppm * r.uniform(0.07, 0.1); Wd = L * r.uniform(0.45, 0.55); tooth = L * 0.012; asym = 0.0
            elif kind == 13: L = ppm * r.uniform(0.04, 0.065); Wd = L * r.uniform(0.36, 0.44); tooth = L * 0.03; asym = 0.15
            else: L = ppm * r.uniform(0.07, 0.1); Wd = L * r.uniform(0.3, 0.38); tooth = L * 0.008; asym = 0.0
            pet = L * 0.12
            tip = (base[0] + math.sin(ang) * pet, base[1] - math.cos(ang) * pet)
            stick(base, tip, S, 100)
            polys, veins = ovate(L, Wd, r, tooth, asym=asym)
            put(polys, veins, tip, ang, shade if kind not in (1, 14) else shade * 0.85, g, -14)
    # twig skeleton: segments (p, q, depth)
    segs = []
    def grow(p, ang, length, depth, w, maxd):
        q = (p[0] + math.sin(ang) * length, p[1] - math.cos(ang) * length)
        segs.append((p, q, depth, ang, w))
        if depth < maxd:
            for side in (-1, 1):
                for t in ((0.35, 0.75) if depth < 2 else (0.5,)):
                    if r.random() < 0.85:
                        mid = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
                        grow(mid, ang + side * r.uniform(0.5, 1.15), length * r.uniform(0.55, 0.7), depth + 1, w * 0.65, maxd)
    grow((cx, cy), r.uniform(-0.12, 0.12), W * 0.5, 0, 5 * S, 4)
    for (p, q, depth, ang, w) in segs: stick(p, q, w)
    leaves = []
    for (p, q, depth, ang, w) in segs:
        if depth < 1: continue
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        if kind in (0, 12, 15):              # opposite pairs along the twig, a pair and a terminal leaf at its end
            sp = ppm * (0.035 if kind == 0 else 0.05)
            n = max(1, int(L / sp))
            for i in range(1, n + 1):
                t = i / n; b = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
                rot_ = r.uniform(0.9, 1.5)
                leaves += [(b, ang + rot_), (b, ang - rot_)]
            leaves.append((q, ang + r.normal(0, 0.2)))
        elif kind == 2:                      # short spurs with 3-5 fans
            sp = ppm * 0.055
            for i in range(max(1, int(L / sp))):
                t = (i + 0.5) / max(1, int(L / sp)); b = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
                for k in range(r.integers(3, 6)): leaves.append((b, ang + r.normal(0, 0.9)))
        else:                                # alternate along the twig (two-ranked for zelkova)
            sp = ppm * (0.05 if kind == 3 else 0.03 if kind == 13 else 0.045)
            n = max(1, int(L / sp))
            for i in range(n):
                t = (i + 0.5) / n; b = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
                side = 1 if i % 2 else -1
                leaves.append((b, ang + side * r.uniform(0.6, 1.1) + (r.normal(0, 0.5) if kind in (1, 14) else 0)))
    order = r.permutation(len(leaves))
    for i in order: leaf_at(*leaves[i])
    out = []
    for im, blur in zip(ims, (0.5, 0.0, 0.5, 0.5, 1.4)):
        if blur: im = im.filter(ImageFilter.GaussianBlur(blur * S))
        out.append(np.asarray(im.resize((C, C), Image.LANCZOS if blur else Image.NEAREST), np.float32) / 255.0)
    return out

def draw_cell(kind, seed):
    """returns float arrays (C,C): lum, outer, twig, alpha, height"""
    S = 2  # supersample
    W = C * S
    lum = Image.new('L', (W, W), 0); outer = Image.new('L', (W, W), 0); twig = Image.new('L', (W, W), 0); alpha = Image.new('L', (W, W), 0); hgt = Image.new('L', (W, W), 0)
    dl, do, dt, da, dh = (ImageDraw.Draw(x) for x in (lum, outer, twig, alpha, hgt))
    r = rng(seed)
    cx, cy = W * 0.5, W * 0.95                       # the cluster grows from the bottom centre of the card
    def stick(p0, p1, w):
        for d in (dt, da):
            d.line([p0, p1], fill=255, width=max(1, int(w)))
        dl.line([p0, p1], fill=70, width=max(1, int(w)))
        dh.line([p0, p1], fill=120, width=max(1, int(w)))
    def leaf(poly, shade, out_k):
        da.polygon(poly, fill=255)
        dl.polygon(poly, fill=int(shade))
        do.polygon(poly, fill=int(out_k))
        dh.polygon(poly, fill=170)
    # twig skeleton: a main twig and side twigs; leaves at nodes / tips
    nodes = []
    def grow(p, ang, length, depth, w, maxd=4):
        q = (p[0] + math.sin(ang) * length, p[1] - math.cos(ang) * length)
        stick(p, q, w)
        nodes.append((q, ang, depth))
        # leaves along the segment too (not only at its tip)
        for t in (0.35, 0.65):
            nodes.append(((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t), ang, depth + 1))
        if depth < maxd:
            for side in (-1, 1):
                if r.random() < 0.9:
                    a2 = ang + side * r.uniform(0.45, 1.0)
                    mid = (p[0] + (q[0] - p[0]) * r.uniform(0.3, 0.8), p[1] + (q[1] - p[1]) * r.uniform(0.3, 0.8))
                    grow(mid, a2, length * r.uniform(0.5, 0.68), depth + 1, w * 0.68, maxd)
    if kind in (0, 12, 15, 2, 3, 13, 1, 14):
        return broadleaf_cell(kind, r, W, S, cx, cy, (lum, outer, twig, alpha, hgt), (dl, do, dt, da, dh))
    if kind in (0, 1, 2, 3, 10, 11, 9):
        grow((cx, cy), r.uniform(-0.15, 0.15), W * 0.5, 0, 7 * S, 3 if kind == 9 else 4)
    if kind == 9:                                    # bare twigs only: finer, more forks
        for _ in range(3):
            grow((cx + r.uniform(-W * 0.2, W * 0.2), cy), r.uniform(-0.6, 0.6), W * 0.4, 1, 4 * S)
    elif kind == 0:                                  # maple: palmate leaves in layered whorls at twig ends
        for (q, ang, dep) in nodes:
            for k in range(r.integers(2, 5)):
                sz = W * r.uniform(0.06, 0.09)
                a = ang + r.uniform(-1.4, 1.4)
                c = (q[0] + math.sin(a) * sz * 1.4, q[1] - math.cos(a) * sz * 1.4)
                leaf(rot(maple_leaf(sz), a + math.pi, c), r.uniform(150, 235), 255 if dep >= 2 else r.uniform(80, 200))
    elif kind in (1, 11):                            # evergreen broadleaf / camellia: elliptic glossy leaves
        for (q, ang, dep) in nodes:
            for k in range(r.integers(2, 5)):
                L = W * r.uniform(0.09, 0.13) * (0.8 if kind == 11 else 1.0); Wd = L * r.uniform(0.38, 0.5)
                a = ang + r.uniform(-1.5, 1.5)
                leaf(rot(ellipse_leaf(L, Wd, 1.0), a + math.pi, q), r.uniform(120, 210), r.uniform(60, 160))
    elif kind == 2:                                  # ginkgo: fans on short spurs
        for (q, ang, dep) in nodes:
            for k in range(r.integers(2, 5)):
                sz = W * r.uniform(0.065, 0.095)
                a = ang + r.uniform(-1.6, 1.6)
                leaf(rot(fan_leaf(sz), a + math.pi, q), r.uniform(170, 245), r.uniform(120, 255))
    elif kind == 3:                                  # cherry / zelkova: serrated ovals, alternate
        for (q, ang, dep) in nodes:
            for k in range(r.integers(2, 4)):
                L = W * r.uniform(0.1, 0.14); Wd = L * r.uniform(0.42, 0.55)
                a = ang + r.uniform(-1.6, 1.6)
                leaf(rot(ellipse_leaf(L, Wd, 1.6, serr=1.0), a + math.pi, q), r.uniform(130, 220), r.uniform(80, 220))
    elif kind == 10:                                 # azalea: many small leaves
        for (q, ang, dep) in nodes:
            for k in range(r.integers(8, 14)):
                L = W * r.uniform(0.03, 0.05); Wd = L * 0.45
                a = r.uniform(0, 2 * math.pi)
                c = (q[0] + r.normal() * W * 0.04, q[1] + r.normal() * W * 0.04)
                leaf(rot(ellipse_leaf(L, Wd), a, c), r.uniform(110, 200), r.uniform(50, 150))
    elif kind == 4:                                  # pine: needle tufts (pairs of long needles) fanning from twigs
        grow((cx, cy), 0.0, W * 0.5, 1, 6 * S)
        for (q, ang, dep) in nodes:
            for k in range(28):
                a = ang + r.normal() * 0.9
                L = W * r.uniform(0.07, 0.12)
                p0 = (q[0] + r.normal() * W * 0.02, q[1] + r.normal() * W * 0.02)
                p1 = (p0[0] + math.sin(a) * L, p0[1] - math.cos(a) * L)
                for d, v in ((da, 255), (dl, int(r.uniform(110, 200))), (dh, 160)): d.line([p0, p1], fill=v, width=2 * S)
    elif kind in (5, 6):                             # cedar / cypress: flat sprays of scale-leaves
        def spray(p, ang, length, depth):
            q = (p[0] + math.sin(ang) * length, p[1] - math.cos(ang) * length)
            w = (9 if kind == 6 else 3) * S * (1.0 - depth * 0.2)
            for d, v in ((da, 255), (dl, int(r.uniform(110, 190))), (dh, 170)): d.line([p, q], fill=v, width=max(2, int(w)))
            if kind == 5:                            # sugi: awl needles all along
                for t in np.linspace(0.05, 1, 14):
                    m = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
                    for sd in (-1, 1):
                        a2 = ang + sd * 0.7
                        e = (m[0] + math.sin(a2) * W * 0.022, m[1] - math.cos(a2) * W * 0.022)
                        for d, v in ((da, 255), (dl, int(r.uniform(100, 180)))): d.line([m, e], fill=v, width=2 * S)
            if depth < 3:
                for t in (0.3, 0.55, 0.8):
                    for sd in (-1, 1):
                        if r.random() < 0.8:
                            m = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
                            spray(m, ang + sd * r.uniform(0.6, 0.95), length * r.uniform(0.35, 0.5), depth + 1)
        spray((cx, cy), r.uniform(-0.1, 0.1), W * 0.8, 0)
    elif kind == 7:                                  # willow: hanging strands (the card hangs: grows downward from the top)
        for k in range(14):
            x0 = W * r.uniform(0.15, 0.85); y0 = W * 0.03
            pts = [(x0, y0)]
            for s_ in range(20):
                pts.append((pts[-1][0] + r.normal() * 3 * S, pts[-1][1] + W * 0.046))
            for i in range(len(pts) - 1):
                for d, v in ((da, 255), (dl, 80)): d.line([pts[i], pts[i + 1]], fill=v, width=2 * S)
                if i % 1 == 0:
                    for sd in (-1, 1):
                        a = math.pi + sd * r.uniform(0.2, 0.5)
                        L = W * r.uniform(0.05, 0.08)
                        leaf(rot(ellipse_leaf(L, L * 0.18), a, pts[i]), r.uniform(130, 210), r.uniform(60, 200))
    elif kind == 8:                                  # bamboo: slender leaves in fans
        grow((cx, cy), 0.0, W * 0.6, 1, 4 * S)
        for (q, ang, dep) in nodes:
            for k in range(r.integers(2, 4)):
                L = W * r.uniform(0.14, 0.2); Wd = L * 0.16
                a = ang + r.uniform(-1.2, 1.2)
                leaf(rot(ellipse_leaf(L, Wd, 1.4), a + math.pi, q), r.uniform(130, 210), r.uniform(60, 160))
    out = []
    for im, blur in ((lum, 0.6), (outer, 0.6), (twig, 0.5), (alpha, 0.5), (hgt, 1.6)):
        im = im.filter(ImageFilter.GaussianBlur(blur * S)).resize((C, C), Image.LANCZOS)
        out.append(np.asarray(im, np.float32) / 255.0)
    return out

def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    A = np.zeros((C * N, C * N, 4), np.float32); H = np.zeros((C * N, C * N), np.float32)
    kinds = list(range(12)) + [12, 13, 14, 15]
    for cell, kind in enumerate(kinds):
        lum, outer, twig, alpha, hgt = draw_cell(kind, 1000 + cell * 7)
        y0, x0 = (cell // N) * C, (cell % N) * C
        A[y0:y0 + C, x0:x0 + C] = np.dstack([lum, outer, twig, alpha])
        H[y0:y0 + C, x0:x0 + C] = hgt
        print('cell', cell, 'kind', kind, 'coverage', round(float((alpha > 0.5).mean()), 3), flush=True)
    # alpha: dilate colour into the transparent texels so mipmaps do not darken the edges
    from scipy import ndimage
    for c in range(3):
        ch = A[..., c]; m = A[..., 3] > 0.05
        if m.any():
            idx = ndimage.distance_transform_edt(~m, return_distances=False, return_indices=True)
            A[..., c] = np.where(m, ch, ch[tuple(idx)])
    gy, gx = np.gradient(ndimage.gaussian_filter(H, 1.2))
    Nm = np.dstack([-gx * 6, gy * 6, np.ones_like(H)]); Nm /= np.linalg.norm(Nm, axis=2, keepdims=True)
    Image.fromarray(np.clip(A * 255 + 0.5, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(out_dir, 'leaves.png'))
    Image.fromarray(np.clip((Nm * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8), 'RGB').save(os.path.join(out_dir, 'leaves_nrm.png'))

if __name__ == '__main__':
    import sys
    build(sys.argv[1])
