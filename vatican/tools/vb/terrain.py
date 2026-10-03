"""Ground height model (metres relative to the obelisk base).  Hand-built from known levels until a
DEM is available: the square and Borgo ~0, the Tiber embankment lower, the Vatican hill rising west
to ~+45 behind the basilica, Janiculum to the south."""
import math
import numpy as np
from .geom import Mesh

def _smooth(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)

def height(x, y):
    z = 0.0
    # gentle rise of the square toward the basilica steps (piazza retta)
    if -200 < x < 0: z += 1.5 * _smooth((-x) / 180.0) * _smooth((70 - abs(y)) / 30.0)
    # Vatican hill: west of the basilica, rising toward the gardens (x<-420) and north-west
    hill = _smooth((-x - 380) / 420.0) * 45.0
    hill *= _smooth((y + 400) / 250.0)                     # dies off to the far south
    z += hill
    # Belvedere / museums plateau north-west: about +12 around the Pigna courtyard
    z += 10.0 * _smooth((y - 120) / 200.0) * _smooth((-x - 150) / 250.0) * (1 - _smooth((-x - 600) / 200.0))
    # Tiber valley east: down to -10 near the river (x ~ +700..+900)
    z -= 10.0 * _smooth((x - 450) / 300.0)
    # Janiculum to the south (y < -600)
    z += 40.0 * _smooth((-y - 550) / 350.0) * _smooth((-x + 200) / 600.0)
    return z

def mesh(x0, y0, x1, y1, step, mat='ground'):
    m = Mesh()
    nx = int((x1 - x0) / step); ny = int((y1 - y0) / step)
    o = m.add_v([(x0 + i * step, y0 + j * step, height(x0 + i * step, y0 + j * step)) for j in range(ny + 1) for i in range(nx + 1)])
    for j in range(ny):
        for i in range(nx):
            a = o + j * (nx + 1) + i
            m.face([a, a + 1, a + nx + 2, a + nx + 1], mat, True)
    return m
