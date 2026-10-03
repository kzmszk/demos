"""Sculpture library (decimated scans from process_scans.py)."""
import math, random
import numpy as np
from .geom import Mesh, mat4
LOD = '/home/kazu/work/vatican-assets/scans/lod'
_cache = {}

def load(key, lod=1):
    k = (key, lod)
    if k not in _cache:
        d = np.load(f'{LOD}/{key}_{lod}.npz')
        _cache[k] = (d['V'].astype(np.float64), d['F'].astype(np.int64))
    return _cache[k]

def place(key, x, y, z, height, rot, lod=1, mat='statue'):
    V, F = load(key, lod)
    m = Mesh()
    c, s = math.cos(rot), math.sin(rot)
    W = V * height
    P = np.stack([W[:, 0] * c - W[:, 1] * s + x, W[:, 0] * s + W[:, 1] * c + y, W[:, 2] + z], 1)
    m.V = P.tolist()
    m.F = F.tolist(); m.M = [mat] * len(F); m.S = [True] * len(F); m.UV = [None] * len(F)
    return m

SAINTS = ['baptist', 'ecclesia', 'francis', 'niobid', 'pudicitia', 'polyhymnia']
