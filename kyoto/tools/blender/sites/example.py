"""A smoke test of the pipeline: one hall on the Sanjusangendo data (run with --data sanjusangendo)."""
import numpy as np
from jk import prim, arch, roof, Frame
SHOTS = [('a', (1150, 160, 60), (1185, 240, 35), 35)]
def build(B, S, only=None):
    cx, cy = 1185.0, 242.0; z = S.ground(cx, cy)
    with Frame(B, cx, cy, z, 0.0):
        arch.platform(B, [(-12, -8), (12, -8), (12, 8), (-12, 8)], -0.5, 0.6)
        us, vs = arch.grid(18, 10, 5, 3)
        for x in us:
            for y in (vs[0], vs[-1]): arch.pillar(B, x, y, 0.6, 5.0, 0.24, 'wood_dark')
        roof.roof(B, 18, 10, 5.3, 2.5, kind='irimoya', cover='hongawara')
    B.tree('momiji', cx + 16, cy, z)
    S.paint.append({'poly': [[cx - 20, cy - 15], [cx + 20, cy - 15], [cx + 20, cy + 15], [cx - 20, cy + 15]], 'surf': 'gravel'})
