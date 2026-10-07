import bpy, sys, os
sys.path.insert(0, '/home/kazu/work/demos/kyoto/tools/blender'); sys.path.insert(0, '/home/kazu/work/demos/kyoto/tools/dbg')
bpy.ops.wm.read_factory_settings(use_empty=True)
import jk, numpy as np
from jk import prim, Frame
import render_scene as R
B = jk.Builder('test')
prim.box(B, -40, -40, -0.5, 60, 40, 0, 'stone')
def hall(ox, kind, cover, L, D, H, o, **kw):
    with Frame(B, ox, 0, 0, 0):
        prim.box(B, -L / 2 - 1, -D / 2 - 1, 0, L / 2 + 1, D / 2 + 1, 0.6, 'stone')
        for x in np.linspace(-L / 2, L / 2, 4):
            for y in (-D / 2, D / 2):
                prim.cyl(B, (x, y, 0.6), (x, y, H), 0.22, 0.2, 12, 'vermilion' if cover == 'hongawara' else 'wood_dark')
        prim.box(B, -L / 2 + 0.1, -D / 2 + 0.1, 0.6, L / 2 - 0.1, D / 2 - 0.1, H, 'temple_wall', c0=(232, 228, 216, 35), c1=(0, 4, 0, 0))
        jk.roof.roof(B, L, D, H + 0.6, o, kind=kind, cover=cover, **kw)
hall(-20, 'irimoya', 'hongawara', 12, 8, 5.0, 2.6, rafter_mat='vermilion', rafter_end='white_paint', ends='oni')
hall(5, 'yosemune', 'hiwada', 14, 9, 5.5, 3.0)
hall(28, 'kirizuma', 'sangawara', 8, 6, 4.5, 1.2, rafter=0.45, tiers=1)
hall(48, 'hogyo', 'hongawara', 7, 7, 4.5, 2.2)
print('tris', B.ntri())
jk.to_objects(B)
R.setup()
R.shot(sys.argv[-1], (14, -42, 14), (14, 0, 5), 30)
R.shot(sys.argv[-1].replace('.png', '_low.png'), (-14, -12, 1.7), (-20, 0, 7.5), 24)
