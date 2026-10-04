"""Shared helpers for hand-modelled hero buildings: facade frames, kit placement, piazza frame."""
import math
import numpy as np
from vk import geom as G
from vk.adapt import to_builder
from ..world import GROUND_Z

# Piazza San Marco frame: u along the piazza axis (az 70.5°, ENE), v toward NNW; origin = campanile centroid
AZ = math.radians(70.5)
PU = np.array([math.sin(AZ), math.cos(AZ)]); PV = np.array([-PU[1], PU[0]])

def pf(p):            # world xy -> piazza (u, v)
    return float(np.dot(p, PU)), float(np.dot(p, PV))

def wf(u, v):         # piazza (u, v) -> world xy
    return PU * u + PV * v

def rotated_frame(deg, pivot):
    """a frame like the piazza's turned by deg (ccw) about the piazza point pivot, for buildings that are not
    square to the piazza (the Basilica sits ~3.5 deg off it).  Returns (wf, pf, PU, PV) with the same API."""
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    PU2 = c * PU + s * PV; PV2 = -s * PU + c * PV
    o = wf(*pivot) - (PU2 * pivot[0] + PV2 * pivot[1])
    def wf2(u, v): return o + PU2 * u + PV2 * v
    def pf2(p):
        q = np.asarray(p, float)[:2] - o
        return float(np.dot(q, PU2)), float(np.dot(q, PV2))
    return wf2, pf2, PU2, PV2

def facade_frame(a, b, n_out, z0=GROUND_Z):
    """kit frame for a facade along the world segment a-b whose outward normal is n_out (toward the
    street/piazza).  Kit convention: x along the facade, facade faces -y, z up.  Returns (M, L, flipped)
    where flipped means x runs from b to a."""
    a = np.array(a, float); b = np.array(b, float); n = np.array(n_out, float); n /= np.linalg.norm(n)
    y = np.array([-n[0], -n[1], 0.0]); z = np.array([0, 0, 1.0])
    x = np.cross(y, z)                      # so that x × y = z
    d = b - a; L = float(np.linalg.norm(d))
    flipped = np.dot(d, x[:2]) < 0
    o = b if flipped else a
    M = np.eye(4); M[:3, 0] = x; M[:3, 1] = y; M[:3, 2] = z; M[:3, 3] = (o[0], o[1], z0)
    return M, L, flipped

def place(mb, mesh, M, c0=(255, 255, 255, 0), c1=(0, 0, 0, 0), matmap=None, max_edge=2.0):
    """add a vk Mesh to the MeshBuilder with transform M (local kit coords -> world)."""
    to_builder(mesh, mb, c0=c0, c1=c1, M=M, matmap=matmap, max_edge=max_edge)

def translate(x, y=0.0, z=0.0):
    M = np.eye(4); M[:3, 3] = (x, y, z); return M

def compose(*Ms):
    R = np.eye(4)
    for M in Ms: R = R @ M
    return R

def replicate(mesh, xs):
    """one kit Mesh repeated at x offsets (merged)."""
    out = G.Mesh()
    for x in xs: out.merge(mesh, translate(x))
    return out
