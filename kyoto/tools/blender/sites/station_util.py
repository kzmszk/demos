"""Helpers for the Kyoto Tower / Kyoto Station site (vectorised boxes, planar curtain-wall grids, rounded outlines,
smooth revolved shells).  Kept in the site package because the shared kit may not be edited.

Conventions: a wall is walked p0 -> p1 along a counter-clockwise ring, so its outward side is the RIGHT of the walk
direction (n = (dy, -dx)).  plane_grid() takes a frame (U along, V up-slope, N = U x V outward)."""
import math
import numpy as np
from jk import prim

Z = np.array([0.0, 0.0, 1.0])

def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-12)

def _fix_outward(P, I, ctr):
    """flip triangles of convex solids so that normals point away from the solid's centre"""
    n = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    tc = P[I].mean(1)
    flip = (n * (tc - ctr)).sum(1) < 0
    I = I.copy()
    I[flip] = I[flip][:, ::-1]
    return I

def obox_batch(B, p0, p1, w, h, mat, up=(0, 0, 1), tag='main', ends=False, max_len=18.0, **kw):
    """n oriented boxes (beams) from p0[i] to p1[i] with a w x h section; `up` (3,) or (n,3) orients h.
    w / h scalar or (n,).  Beams longer than max_len are cut into pieces (tiles take triangles by centroid)."""
    p0 = np.atleast_2d(np.asarray(p0, float)); p1 = np.atleast_2d(np.asarray(p1, float))
    n = len(p0)
    Lx = np.linalg.norm(p1 - p0, axis=1)
    if n and Lx.max() > max_len:
        nseg = np.maximum(1, np.ceil(Lx / max_len)).astype(int)
        idx = np.repeat(np.arange(n), nseg)
        k = np.concatenate([np.arange(m) for m in nseg])
        f0 = (k / nseg[idx])[:, None]; f1 = ((k + 1) / nseg[idx])[:, None]
        q0 = p0[idx] + (p1[idx] - p0[idx]) * f0; q1 = p0[idx] + (p1[idx] - p0[idx]) * f1
        wv = np.broadcast_to(np.asarray(w, float), (n,))[idx]; hv = np.broadcast_to(np.asarray(h, float), (n,))[idx]
        upv = np.broadcast_to(np.asarray(up, float), (n, 3))[idx]
        return obox_batch(B, q0, q1, wv, hv, mat, up=upv, tag=tag, ends=ends, max_len=1e9, **kw)
    d = p1 - p0
    L = np.linalg.norm(d, axis=1)
    ok = L > 1e-6
    if not ok.any(): return
    p0 = p0[ok]; p1 = p1[ok]; d = d[ok] / L[ok, None]; n = len(p0)
    up = np.asarray(up, float)
    up = np.broadcast_to(up, (len(ok), 3))[ok]
    a = np.cross(d, up)
    bad = np.linalg.norm(a, axis=1) < 1e-6
    if bad.any():
        alt = np.where((np.abs(d[bad][:, 0]) < 0.9)[:, None], np.array([1.0, 0, 0]), np.array([0, 1.0, 0]))
        a[bad] = np.cross(d[bad], alt)
    a = unit(a)
    b = np.cross(a, d)
    w = np.broadcast_to(np.asarray(w, float), (len(ok),))[ok][:, None]
    h = np.broadcast_to(np.asarray(h, float), (len(ok),))[ok][:, None]
    cs = np.array([(-1, -1), (1, -1), (1, 1), (-1, 1)], float)
    off = a[:, None, :] * (cs[None, :, 0:1] * w[:, None, :] / 2) + b[:, None, :] * (cs[None, :, 1:2] * h[:, None, :] / 2)   # (n,4,3)
    P = np.concatenate([p0[:, None, :] + off, p1[:, None, :] + off], axis=1)       # (n,8,3)
    tri = []
    for i in range(4):
        j = (i + 1) % 4
        tri += [[i, j, j + 4], [i, j + 4, i + 4]]
    if ends: tri += [[0, 3, 2], [0, 2, 1], [4, 5, 6], [4, 6, 7]]
    tri = np.array(tri)
    I = (tri[None, :, :] + (np.arange(n) * 8)[:, None, None]).reshape(-1, 3)
    Pf = P.reshape(-1, 3)
    ctr = np.repeat((p0 + p1) / 2, len(tri), axis=0)
    I = _fix_outward(Pf, I, ctr)
    B.add(Pf, I, mat, tag=tag, **kw)

def box_batch(B, lo, hi, mat, tag='main', faces='all', **kw):
    """axis-aligned boxes: lo, hi (n,3).  faces: letters from 'xXyYzZ' (lower/upper faces) to keep"""
    lo = np.atleast_2d(np.asarray(lo, float)); hi = np.atleast_2d(np.asarray(hi, float))
    n = len(lo)
    c = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], float)
    P = lo[:, None, :] + (hi - lo)[:, None, :] * c[None]
    F = {'z': [0, 3, 2, 1], 'Z': [4, 5, 6, 7], 'y': [0, 1, 5, 4], 'Y': [2, 3, 7, 6], 'x': [3, 0, 4, 7], 'X': [1, 2, 6, 5]}
    tri = []
    for k, q in F.items():
        if faces != 'all' and k not in faces: continue
        tri += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    tri = np.array(tri)
    I = (tri[None] + (np.arange(n) * 8)[:, None, None]).reshape(-1, 3)
    B.add(P.reshape(-1, 3), I, mat, tag=tag, **kw)

def _grid_face(B, O, Uv, Vv, lu, lv, mat, tag, max_edge, **kw):
    """a planar face O + Uv*[0,lu] + Vv*[0,lv] (normal = Uv x Vv) subdivided to <= max_edge cells, UV in metres"""
    nu = max(1, int(math.ceil(lu / max_edge))); nv = max(1, int(math.ceil(lv / max_edge)))
    us = np.linspace(0, lu, nu + 1); vs = np.linspace(0, lv, nv + 1)
    P = np.array([O + Uv * a + Vv * b for b in vs for a in us])
    UV = np.array([(a, b) for b in vs for a in us])
    I = []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            I += [[a, a + 1, a + nu + 2], [a, a + nu + 2, a + nu + 1]]
    B.add(P, I, mat, UV=UV, tag=tag, **kw)

def box(B, x0, y0, z0, x1, y1, z1, mat, tag='main', faces='all', max_edge=6.0, **kw):
    """axis-aligned box; faces: 'all' or letters from 'xXyYzZ' to keep.  Large faces are subdivided (the Cycles bake is per vertex)"""
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    if max(dx, dy, dz) <= max_edge:
        prim.box(B, x0, y0, z0, x1, y1, z1, mat, tag=tag, faces=faces, **kw); return
    X, Y, Zv = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])
    F = {'z': ((x0, y1, z0), X, -Y, dx, dy), 'Z': ((x0, y0, z1), X, Y, dx, dy),
         'y': ((x0, y0, z0), X, Zv, dx, dz), 'Y': ((x1, y1, z0), -X, Zv, dx, dz),
         'x': ((x0, y1, z0), -Y, Zv, dy, dz), 'X': ((x1, y0, z0), Y, Zv, dy, dz)}
    for k, (O, Uv, Vv, lu, lv) in F.items():
        if faces != 'all' and k not in faces: continue
        _grid_face(B, np.array(O, float), Uv, Vv, lu, lv, mat, tag, max_edge, **kw)

def quad(B, P4, mat, tag='main', UV=None, **kw):
    """one quad (4 points CCW seen from the outside)"""
    B.add(np.asarray(P4, float), [[0, 1, 2], [0, 2, 3]], mat, UV=UV, tag=tag, **kw)

def plane_grid(B, O, U, V, lu, lv, pu, pv, glass='glass', frame='metal_dark', mw=0.09, md=0.14, tw=0.07, td=0.10,
               tag_glass='main', tag_frame='detail', uvv0=0.0, edge_frame=False, glass_c0=None, bands=(), glass_kw=None, frame_kw=None):
    """a planar curtain wall: glass quad at O + U*[0,lu] + V*[0,lv]; vertical-ish mullions every pu (along U),
    transoms every pv (along V); depths along N = U x V.  bands: list of (v0, v1, mat, depth) full-width strips.
    Returns (U, V, N)."""
    O = np.asarray(O, float); U = unit(U); V = unit(V); N = np.cross(U, V)
    gk = dict(glass_kw or {})
    nu_g = max(1, int(math.ceil(lu / 8.0))); nv_g = max(1, int(math.ceil(lv / 8.0)))
    us_g = np.linspace(0, lu, nu_g + 1); vs_g = np.linspace(0, lv, nv_g + 1)
    PG = np.array([O + U * a + V * b for b in vs_g for a in us_g]); UVG = np.array([(a, uvv0 + b) for b in vs_g for a in us_g])
    IG = []
    for j in range(nv_g):
        for i in range(nu_g):
            a_ = j * (nu_g + 1) + i
            IG += [[a_, a_ + 1, a_ + nu_g + 2], [a_, a_ + nu_g + 2, a_ + nu_g + 1]]
    B.add(PG, IG, glass, UV=UVG, tag=tag_glass, **gk)
    fk = dict(frame_kw or {})
    nu = max(1, int(round(lu / pu))); us = np.linspace(0, lu, nu + 1)
    if not edge_frame: us = us[1:-1]
    if len(us):
        c = O[None, :] + U[None, :] * us[:, None] + N[None, :] * (md / 2)
        obox_batch(B, c, c + V[None, :] * lv, mw, md, frame, up=N, tag=tag_frame, **fk)
    nv = max(1, int(round(lv / pv))); vs = np.linspace(0, lv, nv + 1)
    if not edge_frame: vs = vs[1:-1]
    if len(vs):
        c = O[None, :] + V[None, :] * vs[:, None] + N[None, :] * (td / 2)
        obox_batch(B, c, c + U[None, :] * lu, tw, td, frame, up=N, tag=tag_frame, **fk)
    for (v0, v1, mat, dep) in bands:
        c0_ = O + V * ((v0 + v1) / 2) + N * (dep / 2)
        obox_batch(B, c0_[None], (c0_ + U * lu)[None], (v1 - v0), dep, mat, up=N, tag='main', **fk)
    return U, V, N

def wall(B, p0, p1, z0, z1, mat, zg=None, c0=(255, 255, 255, 0), c1=(0, 0, 0, 0), tag='main', max_edge=5.0):
    """a vertical wall over the walk p0 -> p1 (2D), outward = right.  UV = (metres along, height above zg).  Subdivided to
    ~max_edge so the per-vertex bake has something to interpolate"""
    p0 = np.asarray(p0, float)[:2]; p1 = np.asarray(p1, float)[:2]
    L = np.linalg.norm(p1 - p0)
    if L < 0.02 or z1 - z0 < 0.01: return
    zg = z0 if zg is None else zg
    nu = max(1, int(math.ceil(L / max_edge))); nz = max(1, int(math.ceil((z1 - z0) / max_edge)))
    us = np.linspace(0, 1, nu + 1); zs = np.linspace(z0, z1, nz + 1)
    P = np.array([[p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u, z] for z in zs for u in us])
    UV = np.array([[u * L, z - zg] for z in zs for u in us])
    I = []
    for j in range(nz):
        for i in range(nu):
            a = j * (nu + 1) + i
            I += [[a, a + 1, a + nu + 2], [a, a + nu + 2, a + nu + 1]]
    B.add(P, I, mat, UV=UV, tag=tag, c0=c0, c1=c1)

def wall_ring(B, ring, z0, z1, mat, zg=None, closed=True, **kw):
    ring = np.asarray(ring, float)
    n = len(ring)
    for i in range(n if closed else n - 1):
        wall(B, ring[i], ring[(i + 1) % n], z0, z1, mat, zg=zg, **kw)

def flat(B, ring, z, mat, up=True, holes=(), tag='main', cell=7.0, **kw):
    """a horizontal polygon (optionally with holes); polygons larger than ~cell are cut into grid pieces (per-vertex bake,
    and triangles are assigned to the 200 m tiles by centroid)"""
    from shapely.geometry import Polygon, box as sbox
    poly = Polygon(ring, [list(h) for h in holes]) if len(holes) else Polygon(ring)
    if not poly.is_valid: poly = poly.buffer(0)
    x0, y0, x1, y1 = poly.bounds
    if max(x1 - x0, y1 - y0) <= cell * 1.5:
        prim.polygon(B, ring, z, mat, up=up, tag=tag, holes=holes, **kw); return
    for gx in np.arange(math.floor(x0 / cell) * cell, x1, cell):
        for gy in np.arange(math.floor(y0 / cell) * cell, y1, cell):
            piece = poly.intersection(sbox(gx, gy, gx + cell, gy + cell))
            if piece.is_empty: continue
            geoms = list(piece.geoms) if piece.geom_type in ('MultiPolygon', 'GeometryCollection') else [piece]
            for g in geoms:
                if g.geom_type != 'Polygon' or g.area < 0.05: continue
                ext = np.array(g.exterior.coords)[:-1]
                hs = [np.array(h.coords)[:-1] for h in g.interiors]
                prim.polygon(B, ext, z, mat, up=up, tag=tag, holes=hs, **kw)

def poly_area(r):
    r = np.asarray(r, float)
    return 0.5 * float(np.sum(r[:, 0] * np.roll(r[:, 1], -1) - np.roll(r[:, 0], -1) * r[:, 1]))

def ccw(r):
    r = np.asarray(r, float)
    return r if poly_area(r) > 0 else r[::-1].copy()

def round_outline(pts, radii, seg=6):
    """CCW polygon with each corner replaced by an arc of radius r (0 = sharp)"""
    pts = np.asarray(pts, float); n = len(pts)
    out = []
    for i in range(n):
        p = pts[i]; a = pts[i - 1]; c = pts[(i + 1) % n]
        r = radii[i] if hasattr(radii, '__len__') else radii
        if r <= 1e-6:
            out.append(p); continue
        d1 = unit(a - p); d2 = unit(c - p)
        ang = math.acos(np.clip(d1 @ d2, -1, 1))
        t = r / math.tan(ang / 2)
        t = min(t, np.linalg.norm(a - p) * 0.5, np.linalg.norm(c - p) * 0.5)
        r = t * math.tan(ang / 2)
        s = p + d1 * t; e = p + d2 * t
        bis = unit(d1 + d2); cen = p + bis * (r / math.sin(ang / 2))
        a0 = math.atan2(s[1] - cen[1], s[0] - cen[0]); a1 = math.atan2(e[1] - cen[1], e[0] - cen[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for k in range(seg + 1):
            q = a0 + da * k / seg
            out.append(cen + r * np.array([math.cos(q), math.sin(q)]))
    return np.array(out)

def buffer_ring(ring, d, res=4):
    """offset a ring outward by d (negative = inward); returns the exterior ring (CCW) or None"""
    from shapely.geometry import Polygon
    p = Polygon(ring).buffer(d, join_style=1, quad_segs=res)
    if p.is_empty: return None
    if p.geom_type != 'Polygon': p = max(p.geoms, key=lambda g: g.area)
    return ccw(np.array(p.exterior.coords)[:-1])

def ring_samples(ring, pitch, closed=True, phase=0.0):
    """points along a ring every ~pitch (equal spacing per edge run); returns (pts (k,2), outward normals (k,2) for CCW rings, tangents)"""
    ring = np.asarray(ring, float)
    pts = np.vstack([ring, ring[:1]]) if closed else ring
    seg = np.diff(pts, axis=0); L = np.linalg.norm(seg, axis=1)
    tot = L.sum(); n = max(1, int(round(tot / pitch)))
    s = (np.arange(n) + phase) * (tot / n)
    cum = np.r_[0, np.cumsum(L)]
    idx = np.clip(np.searchsorted(cum, s, side='right') - 1, 0, len(L) - 1)
    f = (s - cum[idx]) / np.maximum(L[idx], 1e-9)
    P = pts[idx] + seg[idx] * f[:, None]
    T = unit(seg[idx])
    Nn = np.stack([T[:, 1], -T[:, 0]], 1)
    return P, Nn, T

def arc_pts(cx, cy, r, a0, a1, n):
    t = np.linspace(a0, a1, n + 1)
    return np.stack([cx + r * np.cos(t), cy + r * np.sin(t)], 1)

def lathe_uv(B, c, prof, seg=24, mat='white_paint', uvs=0.03, tag='main', smooth=True, **kw):
    """prim.lathe with planar world UVs scaled down (so the wood-grain textures of the 'paint' materials read as a smooth
    steel surface, with no seam where the revolution closes)"""
    c = np.asarray(c, float)
    P = []
    for j, (r, z) in enumerate(prof):
        for i in range(seg + 1):
            t = 2 * math.pi * i / seg
            P.append(c + [r * math.cos(t), r * math.sin(t), z])
    P = np.array(P)
    UV = np.c_[(P[:, 0] * 0.8 + P[:, 1] * 0.6) * uvs, P[:, 2] * uvs]
    I = []; n = seg + 1
    for j in range(len(prof) - 1):
        for i in range(seg):
            a = j * n + i
            I += [[a, a + 1, a + n + 1], [a, a + n + 1, a + n]]
    B.add(P, I, mat, UV=UV, smooth=smooth, tag=tag, **kw)

def smooth_profile(pts, n=40):
    """Catmull-Rom through (r, z) points -> n samples"""
    pts = np.asarray(pts, float)
    if len(pts) < 3: return pts
    ext = np.vstack([2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2]])
    out = []
    m = len(pts) - 1
    per = max(2, n // m)
    for i in range(m):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return np.array(out)

def polyline_tube(B, pts, r, mat, seg=6, tag='main', smooth=True, caps=True, **kw):
    """a round tube along a 3D polyline (swept circle)"""
    pts = np.asarray(pts, float)
    prof = [(r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
    prim.sweep(B, pts, prof, mat, up=(0, 0, 1), closed=True, tag=tag, smooth=smooth, caps=caps, **kw)

def ground_z(S, pts):
    pts = np.asarray(pts, float)
    return S.ground(pts[:, 0], pts[:, 1])

def crystal(B, cx, cy, z0, r, h, seed, tilt=0.35, mat_glass='glass', mat_frame='metal_grey', tag='main'):
    """a faceted glass pavilion: a hexagonal prism cut by a tilted plane (the 'crystal' volumes of the Kyoto Station
    Building), frames on the edges"""
    rng = np.random.default_rng(seed)
    n = 6
    ang = np.arange(n) * 2 * math.pi / n + rng.uniform(0, 1)
    rr = r * rng.uniform(0.8, 1.15, n)
    base = np.stack([cx + rr * np.cos(ang), cy + rr * np.sin(ang)], 1)
    dirn = rng.uniform(0, 2 * math.pi)
    nx, ny = math.cos(dirn), math.sin(dirn)
    top = [h * (0.75 + tilt * ((b[0] - cx) * nx + (b[1] - cy) * ny) / r) for b in base]
    Pb = np.c_[base, np.full(n, z0)]; Pt = np.c_[base, z0 + np.array(top)]
    P = np.vstack([Pb, Pt]); I = []
    for i in range(n):
        j = (i + 1) % n
        I += [[i, j, j + n], [i, j + n, i + n]]
    c = P.mean(0)
    B.add(P, _fix_outward(P, np.array(I), c), mat_glass, tag=tag)
    # roof: fan of the top ring from its centroid
    ct = np.r_[base.mean(0), z0 + np.mean(top)]
    P2 = np.vstack([Pt, ct]); I2 = [[i, (i + 1) % n, n] for i in range(n)]
    B.add(P2, _fix_outward(P2, np.array(I2), np.r_[ct[:2], z0 + h * 2]), mat_glass, tag=tag)
    # frames
    a0 = np.vstack([Pb, Pt, Pt]); a1 = np.vstack([Pt, np.roll(Pt, -1, axis=0), np.roll(Pb, -1, axis=0)])
    obox_batch(B, np.vstack([Pb, Pt]), np.vstack([Pt, np.roll(Pt, -1, axis=0)]), 0.12, 0.12, mat_frame, up=(0, 0, 1), tag='detail', ends=True)

def vquads(B, a, b, z0, z1, mat, zg=0.0, tag='main', **kw):
    """n vertical quads between 2D points a[i] -> b[i] (outward = right of the walk), z0 / z1 scalar or (n,)"""
    a = np.atleast_2d(np.asarray(a, float)); b = np.atleast_2d(np.asarray(b, float)); n = len(a)
    z0 = np.broadcast_to(np.asarray(z0, float), (n,)); z1 = np.broadcast_to(np.asarray(z1, float), (n,))
    L = np.linalg.norm(b - a, axis=1)
    if n and L.max() > 18.0:
        nseg = np.maximum(1, np.ceil(L / 18.0)).astype(int)
        idx = np.repeat(np.arange(n), nseg)
        k = np.concatenate([np.arange(m) for m in nseg])
        f0 = (k / nseg[idx])[:, None]; f1 = ((k + 1) / nseg[idx])[:, None]
        a2 = a[idx] + (b[idx] - a[idx]) * f0; b2 = a[idx] + (b[idx] - a[idx]) * f1
        return vquads(B, a2, b2, z0[idx], z1[idx], mat, zg=zg, tag=tag, **kw)
    P = np.stack([np.c_[a, z0], np.c_[b, z0], np.c_[b, z1], np.c_[a, z1]], 1).reshape(-1, 3)
    UV = np.stack([np.c_[np.zeros(n), z0 - zg], np.c_[L, z0 - zg], np.c_[L, z1 - zg], np.c_[np.zeros(n), z1 - zg]], 1).reshape(-1, 2)
    I = (np.array([[0, 1, 2], [0, 2, 3]])[None] + (np.arange(n) * 4)[:, None, None]).reshape(-1, 3)
    B.add(P, I, mat, UV=UV, tag=tag, **kw)

def hquads(B, rings_out, rings_in, z, mat, up=True, tag='main', **kw):
    """a flat band between two rings with the same point count (outer, inner), at height z"""
    ro = np.asarray(rings_out, float); ri = np.asarray(rings_in, float); n = len(ro)
    P = np.vstack([np.c_[ro, np.full(n, z)], np.c_[ri, np.full(n, z)]])
    I = []
    for i in range(n):
        j = (i + 1) % n
        I += [[i, n + j, n + i], [i, j, n + j]] if up else [[i, n + i, n + j], [i, n + j, j]]
    B.add(P, I, mat, UV=P[:, :2], tag=tag, **kw)


def plane_poly(B, P3, mat, normal=None, tag='main', cell=8.0, **kw):
    """a planar polygon in 3D (>= 3 points), cut into ~cell pieces so the per-vertex bake / tile assignment have something
    to work with; `normal` fixes the facing (default: the winding)"""
    import mapbox_earcut as earcut
    from shapely.geometry import Polygon, box as sbox
    P3 = np.asarray(P3, float); c = P3.mean(0)
    n = np.cross(P3[1] - P3[0], P3[2] - P3[0]) if normal is None else np.asarray(normal, float)
    n = unit(n)
    u = unit(P3[1] - P3[0]); u = unit(u - n * (u @ n)); v = np.cross(n, u)
    uv = np.c_[(P3 - c) @ u, (P3 - c) @ v]
    poly = Polygon(uv)
    if not poly.is_valid: poly = poly.buffer(0)
    x0, y0, x1, y1 = poly.bounds
    for gx in np.arange(math.floor(x0 / cell) * cell, x1, cell):
        for gy in np.arange(math.floor(y0 / cell) * cell, y1, cell):
            piece = poly.intersection(sbox(gx, gy, gx + cell, gy + cell))
            if piece.is_empty: continue
            geoms = list(piece.geoms) if piece.geom_type in ('MultiPolygon', 'GeometryCollection') else [piece]
            for g in geoms:
                if g.geom_type != 'Polygon' or g.area < 0.02: continue
                rings = [np.array(g.exterior.coords)[:-1]] + [np.array(h.coords)[:-1] for h in g.interiors]
                V2 = np.concatenate(rings); ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
                I = earcut.triangulate_float64(V2, ends).reshape(-1, 3)
                P = c + u[None, :] * V2[:, 0:1] + v[None, :] * V2[:, 1:2]
                fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
                flip = (fn @ n) < 0
                I[flip] = I[flip][:, ::-1]
                B.add(P, I, mat, UV=V2, tag=tag, **kw)
