"""Build a hero site in Blender:  blender -b --python tools/blender/run_site.py -- SITE [--shots] [--no-save] [--only part,part]
Imports tools/blender/sites/<SITE>.py, which defines build(B, S, only=None) (B: jk.Builder, S: jk.site.Site) and
optionally SHOTS = [(name, cam_xyz, target_xyz, lens), ...] for preview renders.
Writes /home/kazu/work/kyoto-assets/heroes/<SITE>.npz (viewer geometry, walk/block meshes, lamps, trees, site edits),
/home/kazu/work/kyoto-assets/blender/<SITE>.blend, previews in /home/kazu/work/kyoto-assets/heroes/previews/<SITE>_<shot>.png"""
import bpy, sys, os, importlib, time, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'dbg'))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
name = argv[0]
only = None
if '--only' in argv: only = argv[argv.index('--only') + 1].split(',')
bpy.ops.wm.read_factory_settings(use_empty=True)
import numpy as np
import jk
from jk.site import Site
t0 = time.time()
S = Site(argv[argv.index('--data') + 1] if '--data' in argv else name)
B = jk.Builder(name)
mod = importlib.import_module('sites.' + name)
mod.build(B, S, only=only) if 'only' in mod.build.__code__.co_varnames else mod.build(B, S)
print(f'{name}: built {B.ntri()} tris ({B.ntri("main")} main, {B.ntri("detail")} detail, {B.ntri("walk")} walk, {B.ntri("block")} block), '
      f'{len(B.lamps)} lamps, {len(B.trees)} trees in {time.time()-t0:.1f}s', flush=True)
OUT = '/home/kazu/work/kyoto-assets/heroes'; os.makedirs(os.path.join(OUT, 'previews'), exist_ok=True)
import pickle
edits = dict(exclude=S.exclude, cut=S.cut, paint=S.paint)
jk.export_npz(B, os.path.join(OUT, name + '.npz'), extra={'EDITS': np.frombuffer(json.dumps(edits).encode(), np.uint8)})
objs = jk.to_objects(B, tags=('main', 'detail'))
if '--no-save' not in argv:
    os.makedirs('/home/kazu/work/kyoto-assets/blender', exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=f'/home/kazu/work/kyoto-assets/blender/{name}.blend')
if getattr(mod, 'SHOTS', None):     # the preview cameras, for the viewer's places
    os.makedirs(os.path.join(OUT, 'previews'), exist_ok=True)
    json.dump([dict(name=sn, cam=[float(v) for v in cam], tgt=[float(v) for v in tgt], lens=float(lens)) for (sn, cam, tgt, lens) in mod.SHOTS],
              open(os.path.join(OUT, 'previews', f'{name}_shots.json'), 'w'), indent=0)
if '--shots' in argv and getattr(mod, 'SHOTS', None):
    import render_scene as R
    # the surrounding terrain for context
    tb = jk.Builder('terrain')
    x0, y0, x1, y1 = S.bounds
    xs = np.arange(x0, x1, 4.0); ys = np.arange(y0, y1, 4.0)
    X, Y = np.meshgrid(xs, ys); Z = S.ground(X, Y)
    V = np.stack([X.ravel(), Y.ravel(), Z.ravel() - 0.05], 1); nx = len(xs)
    I = [[j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1] for j in range(len(ys) - 1) for i in range(nx - 1)] + [[j * nx + i, (j + 1) * nx + i + 1, (j + 1) * nx + i] for j in range(len(ys) - 1) for i in range(nx - 1)]
    tb.add(V, I, 'ground', smooth=True)
    jk.to_objects(tb)
    R.setup(res=(1600, 900))
    for (sn, cam, tgt, lens) in mod.SHOTS:
        R.shot(os.path.join(OUT, 'previews', f'{name}_{sn}.png'), cam, tgt, lens)
print(f'done {time.time()-t0:.1f}s')
