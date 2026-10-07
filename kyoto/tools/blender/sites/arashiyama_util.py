"""嵐山: small shared helpers (ground patches on the terrain, shrubs, batched posts)."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point
from jk import prim
import sites.machiya as M

SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
        'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck']

def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == 'Polygon': return [g]
    return [p for p in getattr(g, 'geoms', []) if p.geom_type == 'Polygon' and p.area > 1e-3]

def ring(p):
    return [[float(x), float(y)] for x, y in list(p.exterior.coords)[:-1]]

def ground_mesh(B, S, P, surf, cell=2.0, dz=0.0, zf=None, tag='main', walk=True):
    """our own ground over polygon P (holes allowed) following the terrain (or zf(x, y)), drawn by the ground program"""
    from sites.arashiyama_river import grid_mesh
    for p in polys(P):
        V, I = grid_mesh(p, cell)
        if len(V) == 0: continue
        Z = (zf(V[:, 0], V[:, 1]) if zf is not None else S.ground(V[:, 0], V[:, 1])) + dz
        P3 = np.c_[V, Z]
        B.add(P3, I, 'ground', UV=V.copy(), smooth=True, tag=tag, c1=(0, 0, 0, SURF.index(surf)))
        if walk: B.add(P3, I, 'ground', UV=V.copy(), smooth=True, tag='walk')

_ICO = None
def blob(B, c, size, rng, mat='hedge', tag='detail', flat=0.85, **kw):
    """a low-poly clipped shrub / reed clump: a jittered icosahedron"""
    global _ICO
    if _ICO is None:
        t = (1 + 5 ** 0.5) / 2
        V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t], [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
        V /= np.linalg.norm(V, axis=1, keepdims=True)
        F = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]])
        _ICO = (V, F)
    V, F = _ICO
    P = V * (1 + rng.uniform(-0.12, 0.12, (len(V), 1))) * [size / 2, size / 2, size / 2 * flat] + np.asarray(c, float)
    B.add(P, F, mat, tag=tag, smooth=True, **kw)

def line_pts(L, step, start=0.0, end=None):
    end = L.length if end is None else end
    return [np.array(L.interpolate(t).coords[0]) for t in np.arange(start, end + 1e-6, step)]

def tangent(L, t):
    a = L.interpolate(max(0.0, t - 0.5)); b = L.interpolate(min(L.length, t + 0.5))
    d = np.array([b.x - a.x, b.y - a.y]); return d / max(np.linalg.norm(d), 1e-9)

def block_strip(B, pts, z, w=0.35):
    """a walk blocker along a polyline (railings, walls, embankment edges)"""
    if len(pts) < 2: return
    g = LineString([tuple(p[:2]) for p in pts]).buffer(w / 2, cap_style='flat')
    for p in polys(g):
        prim.polygon(B, np.asarray(p.exterior.coords)[:-1], z, 'stone', tag='block', holes=[np.asarray(r.coords)[:-1] for r in p.interiors])

def lamp_post(B, x, y, z, h=4.2, head='lantern', yaw=0.0, watts=22.0):
    """a street lamp of the 嵐山 kind: dark post, an arm and a square lantern head (paper-glass, lit)"""
    prim.cyl(B, (x, y, z), (x, y, z + h), 0.08, 0.065, 8, 'metal_dark', tag='main')
    c, s = math.cos(yaw), math.sin(yaw)
    hx, hy = x + c * 0.55, y + s * 0.55
    M.bars(B, [(x, y, z + h - 0.05)], [(hx, hy, z + h - 0.05)], (0, 0, 1), 0.06, 0.06, 'metal_dark', tag='detail', caps=True)
    prim.box(B, hx - 0.17, hy - 0.17, z + h - 0.75, hx + 0.17, hy + 0.17, z + h - 0.2, 'lamp', tag='main')
    prim.lathe(B, (hx, hy, z + h - 0.2), [(0.3, 0.0), (0.22, 0.1), (0.05, 0.2), (0.0, 0.24)], 4, 'metal_dark', tag='main', smooth=False)
    prim.box(B, hx - 0.2, hy - 0.2, z + h - 0.8, hx + 0.2, hy + 0.2, z + h - 0.75, 'metal_dark', tag='detail')
    B.lamp(hx, hy, z + h - 0.48, watts, (1.0, 0.74, 0.48))
    prim.polygon(B, [(x - 0.25, y - 0.25), (x + 0.25, y - 0.25), (x + 0.25, y + 0.25), (x - 0.25, y + 0.25)], z + 0.1, 'stone', tag='block')
