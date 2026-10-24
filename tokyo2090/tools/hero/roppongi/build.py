"""Roppongi Hills hero district build (everything from the source package):
   blender -b -P tools/hero/roppongi/build.py
   blender -b -P tools/hero/roppongi/build.py -- [--lod mid] stage...
stages: tex (procedural textures + prisms, venv python) geo bake export mid (mid+far in a sub-process) render far quick
"""
import sys, os, json, pickle, subprocess, importlib, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import numpy as np
import lib
VENV = '/home/kazu/work/kyoto-assets/.venv/bin/python'

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
if '--lod' in args:
    lib.LOD = args[args.index('--lod') + 1]
    args = [a for i, a in enumerate(args) if a != '--lod' and (i == 0 or args[i - 1] != '--lod')]
STAGES = [a for a in args if not a.startswith('-')] or ['tex', 'geo', 'bake', 'export', 'mid', 'render']
os.makedirs(lib.WORK + 'bake', exist_ok=True)
os.makedirs(lib.OUT + 'previews', exist_ok=True)
T0 = time.time()


def log(*a):
    print('[%6.1fs]' % (time.time() - T0), *a, flush=True)


def mat_for(bucket):
    if bucket.startswith('foliage_'):
        return 'leaves'
    if bucket.startswith('decal_water'):
        return 'water'
    if bucket.startswith('decal_cover'):
        return 'cover'
    if bucket.startswith('decal_'):
        return 'decals'
    if bucket.startswith('glass_'):
        return 'glass'
    return bucket.split('#')[0]


def stage_tex():
    need = [n for n in ('conc', 'top', 'pave', 'metal', 'bark', 'bronze', 'fac', 'fac2', 'leaves', 'decals', 'car', 'signs')
            if not os.path.exists(lib.WORK + 'tex/%s.png' % n)]
    if need:
        subprocess.check_call([VENV, os.path.join(HERE, 'textures.py')] + need)
    if not os.path.exists(lib.WORK + 'prisms.json'):
        subprocess.check_call([VENV, os.path.join(HERE, 'prep.py')])


def stage_geo():
    import bl, ruins, district, tower
    mods = ['plaza', 'maman', 'garden', 'keyaki', 'veg', 'props', 'decals']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    ref = bl.collection('ref'); near = bl.collection('near')
    g = bl.import_obj(lib.SRC + 'ground.obj', ref)
    for o in g:
        o.name = 'ground'
    ctx = {'ground': lib.Ground(), 'spawns': [], 'labels': [], 'meta': lib.meta()}
    sc = lib.Scene(); col = ruins.Collider()
    import veg
    occ = veg.Occ()
    P = json.load(open(lib.WORK + 'prisms.json'))
    for k, v in P.items():
        if k.startswith('b') and k not in ('b022', 'b027', 'b016'):
            for f in v['foot']:
                occ.fill_poly(f, 1)
    ctx['occ'] = occ; ctx['cover'] = veg.cover()
    st = district.build(sc, col, ctx)
    log('district', sum(st.values()), 'tris', sc.stats())
    tower.build(sc, col, ctx)
    log('tower done', sc.stats())
    for m in mods:
        if os.path.exists(os.path.join(HERE, m + '.py')):
            mod = importlib.import_module(m)
            mod.build(sc, col, ctx)
            log(m, 'done')
    import veg as _veg
    ctx['crowns'] = _veg.CROWNS
    log('trees', len(_veg.CROWNS), 'tops', len(ctx.get('tops', [])), 'walls', len(ctx.get('walls', [])))
    # buckets -> objects
    total = 0
    for k, b in sc.b.items():
        if b.nv == 0:
            continue
        mat = bl.make_material(mat_for(k))
        origin = None
        if k.startswith('foliage_'):
            V = np.array(b.V)
            origin = (float(V[:, 0].mean()), float(V[:, 1].mean()), float(V[:, 2].min()))
        ob = bl.bucket_to_object(b, k, mat, near, origin)
        total += b.tris()
        log('obj', k, b.tris())
    log('TOTAL tris', total, 'collider', col.tris())
    if not lib.mid():
        pickle.dump(col.polys, open(lib.WORK + 'collide_polys.pkl', 'wb'))
        json.dump({'spawns': ctx['spawns'], 'labels': ctx['labels'], 'crowns': ctx.get('crowns', [])},
                  open(lib.WORK + 'ctx.json', 'w'), ensure_ascii=False)
    bpy.ops.wm.save_as_mainfile(filepath=lib.WORK + ('geo_mid.blend' if lib.mid() else 'geo.blend'))


def stage_quick():
    import render
    bpy.ops.wm.open_mainfile(filepath=lib.WORK + 'geo.blend')
    scene = bpy.context.scene
    render.setup(scene, samples=8)
    for name, pos, tgt in (('q_air', (220, -230, 170), (-30, 30, 40)),
                           ('q_air2', (-260, 220, 160), (-30, 20, 60))):
        render.camera(scene, pos, tgt, lens=28)
        render.shot(scene, lib.WORK + 'scratch/%s.png' % name, 1200, 700)


for s in STAGES:
    log('stage', s)
    if s == 'tex':
        stage_tex()
    elif s == 'geo':
        stage_geo()
    elif s == 'mid':       # the mid LOD (and far, which is baked from it) in a fresh Blender
        subprocess.check_call([bpy.app.binary_path, '-b', '-P', os.path.abspath(__file__), '--', '--lod', 'mid',
                               'geo', 'bake', 'export', 'far'])
    elif s == 'quick':
        stage_quick()
    else:
        mod = importlib.import_module('stage_' + s)
        mod.run(log)
log('done')
