import bpy, sys
sys.path.insert(0, '/home/kazu/work/demos/kyoto/tools/blender'); sys.path.insert(0, '/home/kazu/work/demos/kyoto/tools/dbg')
bpy.ops.wm.read_factory_settings(use_empty=True)
import jk, numpy as np
from jk import prim, arch, Frame
import render_scene as R
B = jk.Builder('test')
prim.box(B, -40, -40, -0.5, 60, 40, 0, 'stone')
# a 5 x 4 bay hall: platform, pillars, nageshi, infills, brackets, veranda + railing, irimoya roof
L, D, H = 15.0, 11.0, 4.6
with Frame(B, 0, 0, 0, 0):
    arch.platform(B, [(-L/2-2.2, -D/2-2.2), (L/2+2.2, -D/2-2.2), (L/2+2.2, D/2+2.2), (-L/2-2.2, D/2+2.2)], 0, 0.5)
    us, vs = arch.grid(L, D, 5, 4)
    z0 = 1.3
    for x in us:
        for y in (vs[0], vs[-1]): arch.pillar(B, x, y, z0, z0 + H, 0.24, 'vermilion')
    for y in vs[1:-1]:
        for x in (us[0], us[-1]): arch.pillar(B, x, y, z0, z0 + H, 0.24, 'vermilion')
    kinds = ['shitomi', 'karado', 'karado', 'karado', 'shitomi']
    for i in range(5):
        arch.infill(B, (us[i], vs[0]), (us[i + 1], vs[0]), z0 + 0.3, z0 + H - 0.9, kinds[i], mat='vermilion')
        arch.infill(B, (us[i], vs[0]), (us[i + 1], vs[0]), z0 + H - 0.9, z0 + H - 0.2, 'renji', mat='vermilion')
    for j in range(4):
        arch.infill(B, (us[-1], vs[j]), (us[-1], vs[j + 1]), z0 + 0.3, z0 + H - 0.2, 'plaster')
        arch.infill(B, (us[0], vs[j + 1]), (us[0], vs[j]), z0 + 0.3, z0 + H - 0.2, 'katomado')
    arch.nageshi(B, L, D, z0 + 0.35, 'vermilion'); arch.nageshi(B, L, D, z0 + H - 0.85, 'vermilion'); arch.nageshi(B, L, D, z0 + H, 'vermilion', h=0.3)
    arch.veranda(B, L, D, z0, 1.4)
    a, c = L/2 + 1.4, D/2 + 1.4
    arch.railing(B, [(-a, -c + 3), (-a, c), (a, c), (a, -c), (3, -c)], z0, mat='vermilion')
    arch.stairs(B, (0, -D/2 - 5.5), (0, -D/2 - 1.4), 0.5, z0, 3.5, 'wood_natural')
    top, reach = arch.bracket_row(B, L, D, z0 + H, 'degumi', 1.0, 'vermilion', 'white_paint', us=us, vs=vs)
    jk.roof.roof(B, L + 2 * reach, D + 2 * reach, top, 2.4, kind='irimoya', cover='hongawara', rafter_mat='vermilion', rafter_end='white_paint', pitch=0.58)
for i in range(8):
    arch.torii(B, 30, -12 + i * 1.0, 0, 0.0, 3.0, 2.4, inscription=True)
arch.ishidoro(B, -8, -12, 0); arch.ishidoro(B, 8, -12, 0)
arch.tsuiji(B, [(-30, -25), (-12, -25)], 0, stripes=5)
arch.takegaki(B, [(12, -25), (25, -25)], 0)
arch.hedge(B, [(-30, -20), (-15, -20)], 0)
print('tris', B.ntri(), B.ntri('detail'))
jk.to_objects(B)
R.setup()
R.shot(sys.argv[-1], (14, -34, 9), (2, 0, 4), 30)
R.shot(sys.argv[-1].replace('.png', '_b.png'), (5, -9.5, 2.9), (0, -5, 5.5), 22)
R.shot(sys.argv[-1].replace('.png', '_c.png'), (36, -18, 1.7), (30, -6, 2.0), 30)
