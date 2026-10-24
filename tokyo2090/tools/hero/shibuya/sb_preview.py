"""Preview renders (Cycles, the game's light) into public/hero/shibuya/previews."""
import math
import os
import sys

import bpy

from sb_common import *
from sb_stage import SPAWNS

VIEWS = {
    # name: (eye or camera loc, target or heading, lens, show context)
    'street_crossing': ('spawn', 0, 26, True),
    'street_hachiko': ('spawn', 1, 26, True),
    'street_109': ('spawn', 2, 24, True),
    'aerial_start': ((196.0, -162.0, 194.0), (-10.0, 10.0, 15.0), 30, True),
    'aerial_34': ((150.0, -260.0, 135.0), (-20.0, -10.0, 25.0), 32, False),
    'aerial_context': ((360.0, -110.0, 300.0), (-30.0, 0.0, 20.0), 30, True),
}


def setup(blend='baked.blend'):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, blend))
    enable_gpu()
    game_light(); view_setup()
    sc = bpy.context.scene
    sc.cycles.max_bounces = 4
    # mist-like haze via a volume would be slow: the box is small, skip
    return sc


def render_view(name, w=1600, h=900, samples=96, out_dir=PREV):
    sc = bpy.context.scene
    loc, tgt, lens, ctx = VIEWS[name]
    ground = Ground()
    ref = bpy.data.collections.get('REF')
    for o in ref.objects:
        if o.name.startswith('ctx_'):
            o.hide_render = not ctx
    if loc == 'spawn':
        s = SPAWNS[tgt]
        x, y = s['x'], s['y']
        z = ground(x, y) + 1.6
        camera('cam', (x, y, z), heading=s['heading'], pitch=math.radians(s.get('pitch_deg', 6)), lens=lens)
    else:
        camera('cam', loc, target=tgt, lens=lens)
    render(os.path.join(out_dir, f'{name}.png'), w, h, engine='CYCLES', samples=samples)


def main(names=None):
    setup()
    for n in (names or VIEWS):
        render_view(n)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    main(args or None)
