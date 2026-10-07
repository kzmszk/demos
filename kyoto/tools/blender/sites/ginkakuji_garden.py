"""銀閣寺 garden: 銀沙灘 (the raised plateau of raked white sand), 向月台 (the truncated sand cone), the 銀閣寺垣 approach
(stone wall + 建仁寺垣 + tall clipped camellia hedge on one side, low + tall hedge on the other), paths and stone steps up the
hill to the 展望所, bridges, 洗月泉, rope and bamboo fences, moss mounds, garden stones, trees.
Garden-local coordinates (origin = 銀閣), z absolute."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, MultiLineString
from shapely.ops import unary_union
from jk import prim, arch, Frame
from . import ginkakuji_util as U
from .ginkakuji_pond import chaikin, SID

WD = 'wood_dark'

def osm_lines(S, cat, ids, GX, GY):
    out = {}
    for w in S.osm[cat]:
        if w['id'] in ids:
            L = []
            def rec(q):
                if isinstance(q[0][0], (int, float)): L.append(np.array(q, float) - [GX, GY]); return
                for r in q: rec(r)
            rec(w.get('line') or w.get('poly'))
            out[w['id']] = L[0]
    return out

# ------------------------------------------------------------------ 銀沙灘
SMOOTH_V = 0.06          # sand_raked with a constant uv.y: the shader's ridge term is flat, so this is plain smoothed white sand

def sand_flat(B, V, z, holes=(), tag='main'):
    """a flat polygon of smoothed white sand (sand_raked, constant uv.y)"""
    import mapbox_earcut as earcut
    rings = [np.asarray(V, float)] + [np.asarray(h, float) for h in holes]
    A = np.concatenate(rings); ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    I = earcut.triangulate_float64(A, ends).reshape(-1, 3)
    P = np.c_[A, np.full(len(A), z)]
    U.oadd(B, P, I, 'sand_raked', (0, 0, 1), UV=np.c_[A[:, 0], np.full(len(A), SMOOTH_V)], tag=tag)

GINSHADAN = [(17.6, 30.9), (17.6, 21.2), (18.4, 19.3), (20.2, 17.6), (22.8, 16.6), (25.8, 16.4), (28.6, 17.3), (30.7, 19.0),
             (31.7, 21.4), (31.9, 24.5), (31.4, 30.9)]

def ginshadan(B, gz, z_base, h=0.55, rim=0.55, band=0.5, focus=(-30.0, 23.5)):
    """the raised sand plateau: a steep sand skirt, a smooth rim band, then alternating smooth and raked bands that fan
    from a focus far to the west; raked bands sit 4 cm lower with a small ridge at their edges"""
    out = Polygon(chaikin(GINSHADAN, 2, closed=True)).buffer(0)
    top = out.buffer(-0.3, join_style=1)
    inner = top.buffer(-rim, join_style=1)
    zt = z_base + h
    sand = (0, 0, 0, SID['sand'])
    # skirt: from the outline at ground to the top outline
    ext = np.array(out.exterior.coords)[:-1]; ext2 = np.array([top.exterior.interpolate(top.exterior.project(Point(p))).coords[0] for p in ext])
    n = len(ext)
    P = np.concatenate([np.c_[ext, [gz(*p) - 0.05 for p in ext]], np.c_[ext2, np.full(n, zt)]])
    I = []
    for i in range(n):
        j = (i + 1) % n
        I += [[i, j, j + n], [i, j + n, i + n]]
    I = np.array(I)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    c = np.array(out.centroid.coords[0])
    if (fn[:, :2] * (P[I[:, 0], :2] - c)).sum() < 0: I = I[:, ::-1]
    B.add(P, I, 'sand_raked', UV=np.c_[np.r_[np.arange(n), np.arange(n)] * 0.3, np.full(2 * n, SMOOTH_V)], smooth=True)
    # rim band (smooth)
    rimp = top.difference(inner)
    for g in (rimp.geoms if hasattr(rimp, 'geoms') else [rimp]):
        sand_flat(B, np.array(g.exterior.coords)[:-1], zt, holes=[np.array(r.coords)[:-1] for r in g.interiors])
    # bands: wedges around the focus
    F = np.array(focus)
    cs = np.array(inner.exterior.coords)
    ang = np.arctan2(cs[:, 1] - F[1], cs[:, 0] - F[0])
    R = float(np.linalg.norm(c - F))
    a0, a1 = ang.min() - 0.01, ang.max() + 0.01
    da = band / R
    k = 0; ntri = 0
    a = a0
    while a < a1:
        b = min(a + da, a1)
        wedge = Polygon([F, F + 80 * np.array([math.cos(a), math.sin(a)]), F + 80 * np.array([math.cos((a + b) / 2), math.sin((a + b) / 2)]), F + 80 * np.array([math.cos(b), math.sin(b)])])
        g = inner.intersection(wedge)
        raked = (k % 2 == 1)
        for p in (g.geoms if hasattr(g, 'geoms') else [g]):
            if p.geom_type != 'Polygon' or p.area < 0.01: continue
            V = np.array(p.exterior.coords)[:-1]
            if raked:
                # uv.y across the rake (the shader draws ridges along constant uv.y): the arc length around the focus
                d = V - F
                uv = np.c_[np.linalg.norm(d, axis=1), np.arctan2(d[:, 1], d[:, 0]) * R]
                import mapbox_earcut as earcut
                I = earcut.triangulate_float64(V, np.array([len(V)], np.uint32)).reshape(-1, 3)
                P = np.c_[V, np.full(len(V), zt - 0.04)]
                fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
                I[fn[:, 2] < 0] = I[fn[:, 2] < 0][:, ::-1]
                B.add(P, I, 'sand_raked', UV=uv)
                # the small ridges along both band edges (raked sand heaped at the border)
                for ab in (a, b):
                    line = LineString([F, F + 80 * np.array([math.cos(ab), math.sin(ab)])]).intersection(p.buffer(0.02))
                    for ln in (line.geoms if hasattr(line, 'geoms') else [line]):
                        if ln.geom_type != 'LineString' or ln.length < 0.3: continue
                        pts = np.array(ln.coords)
                        pts = np.array([pts[0] + (pts[-1] - pts[0]) * t for t in np.linspace(0, 1, max(2, int(ln.length / 1.0)) + 1)])
                        prim.sweep(B, np.c_[pts, np.full(len(pts), zt - 0.04)], [(0.06, 0.0), (0.0, 0.055), (-0.06, 0.0)], 'sand_raked', closed=False, tag='detail')
            else:
                sand_flat(B, V, zt)
                # vertical faces down to the raked bands
                for ab in (a, b):
                    line = LineString([F, F + 80 * np.array([math.cos(ab), math.sin(ab)])]).intersection(p.buffer(0.01))
                    for ln in (line.geoms if hasattr(line, 'geoms') else [line]):
                        if ln.geom_type != 'LineString' or ln.length < 0.05: continue
                        q0, q1 = np.array(ln.coords[0]), np.array(ln.coords[-1])
                        quad = np.array([[*q0, zt - 0.045], [*q1, zt - 0.045], [*q1, zt], [*q0, zt]])
                        uvq = np.array([[0, SMOOTH_V]] * 4)
                        B.add(quad, [[0, 1, 2], [0, 2, 3]], 'sand_raked', UV=uvq)
                        B.add(quad, [[0, 2, 1], [0, 3, 2]], 'sand_raked', UV=uvq)
        k += 1; a = b
    # visitors stay off the sand
    prim.prism(B, np.array(out.exterior.coords)[:-1], z_base - 0.2, zt + 0.6, 'stone', tag='block', top=True)
    return out

def kogetsudai(B, x, y, z, h=1.8, rb=1.65, rt=0.62):
    """向月台: a truncated cone of white sand, flat top, standing on a ring of concentrically raked sand"""
    prof = [(rb + 0.06, -0.08), (rb, 0.0), (rb * 0.97, 0.06)] + [(rb + (rt - rb) * t, h * t) for t in np.linspace(0.06, 1, 8)[1:]] + [(rt - 0.03, h + 0.015), (0.0, h + 0.02)]
    seg = 40
    P = np.array([(x + r * math.cos(2 * math.pi * i / seg), y + r * math.sin(2 * math.pi * i / seg), z + zz) for (r, zz) in prof for i in range(seg + 1)])
    I = []
    n_ = seg + 1
    for j in range(len(prof) - 1):
        for i in range(seg):
            a = j * n_ + i
            I += [[a, a + 1, a + n_ + 1], [a, a + n_ + 1, a + n_]]
    I = np.array(I)
    cz = np.array([x, y, z + h * 0.3])
    C = P[I].mean(1)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    flip = (fn * (C - cz)).sum(1) < 0
    I[flip] = I[flip][:, ::-1]
    B.add(P, I, 'sand_raked', UV=np.c_[np.arange(len(P)) * 0.0, np.full(len(P), SMOOTH_V)], smooth=True)
    # concentric raked ring
    seg = 48; rs = np.linspace(rb + 0.02, rb + 1.25, 6)
    P = []; UV = []
    for r in rs:
        for i in range(seg + 1):
            t = 2 * math.pi * i / seg
            P.append((x + r * math.cos(t), y + r * math.sin(t), z + 0.03 - 0.02 * (r - rb) / 1.25)); UV.append((t * r, r))
    I = []
    for j in range(len(rs) - 1):
        for i in range(seg):
            a = j * (seg + 1) + i
            I += [[a, a + 1, a + seg + 2], [a, a + seg + 2, a + seg + 1]]
    I = np.array(I); P = np.array(P)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    if fn[:, 2].sum() < 0: I = I[:, ::-1]
    B.add(P, I, 'sand_raked', UV=np.array(UV))
    prim.cyl(B, (x, y, z - 0.2), (x, y, z + h), rb + 1.0, rb + 1.0, 16, 'stone', tag='block')

# ------------------------------------------------------------------ fences, ropes, bridges
def rope_fence(B, line, gz, h=0.5, step=1.8, tag='detail'):
    p, _ = U.resample(line, step)
    z = np.array([gz(*q) for q in p])
    for (q, zz) in zip(p, z):
        prim.cyl(B, (q[0], q[1], zz - 0.1), (q[0], q[1], zz + h), 0.045, 0.04, 6, WD, tag='main')
    pts = np.c_[p, z + h - 0.08]
    prim.sweep(B, pts, [(0.012 * math.cos(t), 0.012 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 5)[:-1]], 'cloth', c0=(150, 120, 80, 0), tag=tag)
    for i in range(len(p) - 1):
        prim.obox(B, (*p[i], z[i] + 0.4), (*p[i + 1], z[i + 1] + 0.4), 0.1, 0.8, 'stone', tag='block')

def bamboo_fence(B, line, gz, h=0.6):
    """四つ目垣 (low open bamboo fence)"""
    p, _ = U.resample(line, 1.8)
    for i in range(len(p) - 1):
        za = gz(*((p[i] + p[i + 1]) / 2))
        arch.takegaki(B, [p[i], p[i + 1]], za, h=h, kind='yotsume', tag='main')
        prim.obox(B, (*p[i], za + 0.4), (*p[i + 1], za + 0.4), 0.1, 0.8, 'stone', tag='block')

def slab_bridge(B, a, b, z_a, z_b, w=0.7, th=0.22, arch_h=0.08, mat='stone', n=2, walk=True):
    """stone slab bridge (石橋): n slabs side by side, slightly arched"""
    a = np.asarray(a, float); b = np.asarray(b, float)
    d = b - a; L = np.linalg.norm(d); d /= L; nn = np.array([-d[1], d[0]])
    for k in range(n):
        off = (k - (n - 1) / 2) * (w / n)
        pts = []
        for t in np.linspace(0, 1, 7):
            q = a + d * L * t + nn * off
            pts.append((q[0], q[1], z_a + (z_b - z_a) * t + arch_h * math.sin(math.pi * t)))
        hw = w / n / 2 - 0.01
        prim.sweep(B, np.array(pts), [(-hw, -th), (hw, -th), (hw, 0.0), (-hw, 0.0)], mat, up=(0, 0, 1), caps=True)
    if walk:
        P = np.array([(*(a - nn * w / 2), z_a + 0.01), (*(b - nn * w / 2), z_b + 0.01), (*(b + nn * w / 2), z_b + 0.01), (*(a + nn * w / 2), z_a + 0.01)])
        B.add(P, [[0, 1, 2], [0, 2, 3]] if np.cross(P[1] - P[0], P[2] - P[0])[2] > 0 else [[0, 2, 1], [0, 3, 2]], 'stone', tag='walk')

def wood_bridge(B, a, b, z_a, z_b, w=1.4, rail=0.5):
    a = np.asarray(a, float); b = np.asarray(b, float)
    d = b - a; L = np.linalg.norm(d); d /= L; nn = np.array([-d[1], d[0]])
    za = lambda t: z_a + (z_b - z_a) * t + 0.15 * math.sin(math.pi * t)
    for t in np.linspace(0, 1, 5):
        q = a + d * L * t
        for s in (-1, 1):
            prim.box(B, *(q + nn * s * (w / 2 - 0.08) - 0.06), za(t) - 0.6, *(q + nn * s * (w / 2 - 0.08) + 0.06), za(t), WD)
    pts = np.array([(*(a + d * L * t), za(t)) for t in np.linspace(0, 1, 7)])
    prim.sweep(B, pts, [(-w / 2, -0.12), (w / 2, -0.12), (w / 2, 0.0), (-w / 2, 0.0)], 'eave_wood', up=(0, 0, 1), caps=True)
    for s in (-1, 1):
        q = pts + np.r_[nn * s * (w / 2 - 0.04), 0]
        for t in range(len(q)):
            if t % 2 == 0: prim.box(B, q[t][0] - 0.04, q[t][1] - 0.04, q[t][2], q[t][0] + 0.04, q[t][1] + 0.04, q[t][2] + rail, WD)
        prim.sweep(B, q + [0, 0, rail], [(-0.04, -0.04), (0.04, -0.04), (0.04, 0.04), (-0.04, 0.04)], WD, up=(0, 0, 1), caps=True)
        prim.sweep(B, q + [0, 0, rail / 2], [(-0.4 * 0.04, -0.04), (0.4 * 0.04, -0.04), (0.4 * 0.04, 0.04), (-0.4 * 0.04, 0.04)], WD, up=(0, 0, 1), tag='detail')
        prim.sweep(B, q + [0, 0, rail / 2], [(-0.05, -rail / 2), (0.05, -rail / 2), (0.05, rail / 2 + 0.05), (-0.05, rail / 2 + 0.05)], 'stone', up=(0, 0, 1), tag='block')
    P = np.array([(*(a - nn * w / 2), z_a + 0.01), (*(b - nn * w / 2), z_b + 0.01), (*(b + nn * w / 2), z_b + 0.01), (*(a + nn * w / 2), z_a + 0.01)])
    B.add(P, [[0, 1, 2], [0, 2, 3]] if np.cross(P[1] - P[0], P[2] - P[0])[2] > 0 else [[0, 2, 1], [0, 3, 2]], 'stone', tag='walk')

def moss_mound(B, c, rx, ry, h, z, seed=0, seg=16):
    """a low moss hummock (苔の築山)"""
    rng = np.random.default_rng(seed)
    rings = [(1.0, 0.0), (0.85, 0.45), (0.6, 0.8), (0.3, 0.97), (0.0, 1.0)]
    P = [];
    ph = rng.uniform(0, 6.28, 3)
    for (r, t) in rings:
        for i in range(seg):
            a = 2 * math.pi * i / seg
            k = 1 + 0.12 * math.sin(2 * a + ph[0]) + 0.08 * math.sin(3 * a + ph[1])
            P.append((c[0] + rx * r * k * math.cos(a), c[1] + ry * r * k * math.sin(a), z - 0.08 + h * t))
    I = []
    for j in range(len(rings) - 1):
        for i in range(seg):
            a0 = j * seg + i; a1 = j * seg + (i + 1) % seg
            I += [[a0, a1, a1 + seg], [a0, a1 + seg, a0 + seg]]
    P = np.array(P); I = np.array(I)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    if fn[:, 2].sum() < 0: I = I[:, ::-1]
    B.add(P, I, 'moss_mound', smooth=True)

def sengetsusen(B, x, y, gz, wl):
    """洗月泉: a thin fall over a mossy rock face into the pond's south-east corner (the water falls towards -x).
    The face: tall stones set upright against the bank, the lip stone on top, a dark water ribbon in front, a few
    stones in the splash pool."""
    top = wl + 2.1
    face = [((1.55, 0.75), 0.95, 1.7, 0.0), ((1.6, -0.8), 0.9, 1.5, 0.0), ((2.0, 1.8), 1.1, 1.3, 0.0), ((2.1, -1.9), 1.1, 1.2, 0.0),
            ((2.4, 0.0), 1.0, 2.3, 0.0), ((1.25, 1.6), 0.6, 1.0, 0.0), ((1.25, -1.6), 0.65, 0.9, 0.0)]
    for i, ((dx, dy), s, fl, _) in enumerate(face):
        zg = max(float(gz(x + dx, y + dy)), wl)
        U.rock(B, (x + dx, y + dy, zg + s * fl * 0.35), s, 3100 + i, flat=fl, sub=2, sink=0.2, tilt=0.1, aniso=(0.8, 1.0),
               mat='moss_mound' if i in (2, 3) else 'stone')
    # the lip stone the water slides over, and the bank above (mossy)
    U.rock(B, (x + 1.85, y, top - 0.1), 0.75, 3120, flat=0.45, sub=2, sink=0.3, aniso=(1.2, 0.9))
    U.rock(B, (x + 2.9, y + 0.2, top + 0.2), 1.2, 3121, flat=0.6, sub=2, sink=0.4, mat='moss_mound')
    # the fall: a narrow sheet from the lip down the face, landing in the pool
    pts = np.array([(x + 1.75, y, top + 0.02), (x + 1.45, y, top - 0.05), (x + 1.2, y, top - 0.5), (x + 1.08, y, wl + 0.8), (x + 1.0, y, wl + 0.2), (x + 0.85, y, wl + 0.01)])
    prim.sweep(B, pts, [(-0.16, -0.02), (0.16, -0.02), (0.12, 0.03), (-0.12, 0.03)], 'water', up=(1, 0, 0), closed=True)
    prim.sweep(B, pts + [0, 0, 0.0], [(-0.07, 0.03), (0.07, 0.03), (0.05, 0.05), (-0.05, 0.05)], 'white_paint', up=(1, 0, 0), closed=True, tag='detail')
    # splash pool stones
    for i in range(5):
        a = i * 1.25 + 0.6
        U.rock(B, (x + 0.35 + 0.55 * math.cos(a), y + 0.75 * math.sin(a), wl + 0.04), 0.28, 3200 + i, flat=0.5, sub=1, sink=0.5)
