"""TOKYO 2090 hero district 'tocho' -- the Tokyo Metropolitan Government Buildings as a jungle ruin.

  blender -b -P tools/hero/tocho/build.py [-- --steps geo,tex,bake,export,previews]

geo      massing (venv python + shapely) and every mesh -> WORK/tocho.blend
tex      procedural textures -> WORK/tex/*.png
bake     AO lightmaps (Cycles GPU) and the far atlas
export   near.glb, mid.glb, far.glb, collide.obj, hero.json -> public/hero/tocho/
previews renders -> public/hero/tocho/previews/
"""
import sys, os, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import common as C

VENV_PY = '/home/kazu/work/kyoto-assets/.venv/bin/python'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
steps = 'geo,tex,bake,export,previews'
if '--steps' in argv: steps = argv[argv.index('--steps') + 1]
steps = steps.split(',')
T0 = time.time()


def log(*a):
    print('[tocho %6.1fs]' % (time.time() - T0), *a, flush=True)


if 'tex' in steps:
    import textures
    textures.build_all(); log('textures done')

if 'geo' in steps:
    subprocess.run([VENV_PY, os.path.join(C.HERE, 'massing.py')], check=True)
    import scene
    scene.build(log); log('geometry done')
    C.save()

if 'bake' in steps:
    import bake
    bake.run(log); log('bake done')

if 'export' in steps:
    import export
    export.run(log); log('export done')

if 'previews' in steps:
    import previews
    previews.run(log); log('previews done')
