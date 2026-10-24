"""Shibuya hero district — full build.

    blender -b -P tools/hero/shibuya/build.py                 # everything
    blender -b -P tools/hero/shibuya/build.py -- tex scene    # some stages

Stages: tex (texture atlases), scene (geometry -> work/scene.blend), bake (UV1 + AO -> work/baked.blend),
export (near/mid/far glb, collide.obj, hero.json), preview (renders into public/hero/shibuya/previews).
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402

from sb_common import WORK, enable_gpu  # noqa: E402

ALL = ['tex', 'scene', 'bake', 'export', 'preview']


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    stages = [a for a in args if a in ALL] or ALL
    enable_gpu()
    t0 = time.time()
    if 'tex' in stages:
        import sb_tex_facade, sb_tex_misc, sb_tex_props
        sb_tex_facade.main()
        sb_tex_misc.main()
        sb_tex_props.main()
    if 'scene' in stages:
        import sb_scene
        sb_scene.build()
    if 'bake' in stages:
        import sb_stage
        sb_stage.bake()
    if 'export' in stages:
        import sb_stage
        sb_stage.export()
    if 'preview' in stages:
        import sb_preview
        sb_preview.main()
    print(f'build done in {time.time() - t0:.0f}s: {stages}')


main()
