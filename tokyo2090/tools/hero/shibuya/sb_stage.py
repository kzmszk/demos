"""Stages bake / export."""
import json
import math
import os
import time

import bpy

from sb_common import WORK, OUT, ORIGIN, enable_gpu
import sb_bake
import sb_export

SPAWNS = [
    dict(name='スクランブル交差点', x=95.0, y=-61.0, heading=-0.95, note='SE corner of the scramble, QFRONT and 109 ahead'),
    dict(name='ハチ公', x=85.3, y=-95.2, heading=2.5, note='Hachiko square, the statue in front'),
    dict(name='SHIBUYA109', x=2.0, y=-46.0, heading=-1.5, note='Dogenzaka below the fork, the 109 tower ahead'),
]
LABELS = [
    dict(name='SHIBUYA109', x=-58.0, y=-43.0, z=70.0, kind='building'),
    dict(name='QFRONT', x=66.0, y=-8.0, z=70.0, kind='building'),
    dict(name='MAGNET by SHIBUYA109', x=116.0, y=-15.0, z=62.0, kind='building'),
    dict(name='渋谷西武', x=56.0, y=30.0, z=66.0, kind='building'),
    dict(name='スクランブル交差点', x=78.0, y=-52.0, z=19.0, kind='place'),
    dict(name='ハチ公像', x=88.9, y=-100.0, z=19.0, kind='place'),
    dict(name='センター街', x=60.0, y=-33.0, z=22.0, kind='place'),
    dict(name='道玄坂', x=-70.0, y=-72.0, z=24.0, kind='place'),
    dict(name='文化村通り', x=-90.0, y=-10.0, z=24.0, kind='place'),
]


def near_objects():
    c = bpy.data.collections['NEAR']
    return [o for o in c.all_objects if o.type == 'MESH']


def bake(samples=128):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, 'scene.blend'))
    enable_gpu()
    t = time.time()
    objs = [o for o in near_objects() if o.active_material and o.active_material.node_tree.nodes.get('orm')]
    for o in objs:
        sb_bake.make_uv1(o)
    print(f'uv1 {time.time() - t:.0f}s')
    sb_bake.bake_ao(objs, samples=samples)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, 'baked.blend'))
    print(f'bake done {time.time() - t:.0f}s')


def export(levels=None):
    import sys
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    levels = levels or [a for a in args if a in ('near', 'mid', 'far')] or ('near', 'mid', 'far')
    bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, 'baked.blend'))
    enable_gpu()
    import sb_lod
    near = bpy.data.collections['NEAR']
    objs = [o for o in near.all_objects]
    meshes = [o for o in objs if o.type == 'MESH']
    stats = {}
    old = os.path.join(OUT, 'hero.json')
    if os.path.exists(old):
        try:
            stats.update(json.load(open(old)).get('stats', {}))
        except Exception:
            pass
    if 'near' in levels:
        stats['near_tris'] = sb_export.tri_count(meshes)
        stats['draw_calls'] = sb_export.draw_calls(meshes)
        size = sb_export.export_glb(os.path.join(OUT, 'near.glb'), objs, instances=True)
        stats['near_mb'] = round(size / 1e6, 2)
    if 'mid' in levels:
        mobjs = sb_lod.make_mid(near)
        mm = [o for o in mobjs if o.type == 'MESH']
        stats['mid_tris'] = sb_export.tri_count(mm)
        stats['mid_draw_calls'] = sb_export.draw_calls(mm)
        size = sb_export.export_glb(os.path.join(OUT, 'mid.glb'), mobjs, instances=True)
        stats['mid_mb'] = round(size / 1e6, 2)
    if 'far' in levels:
        fo = sb_lod.make_far(near)
        stats['far_tris'] = sb_export.tri_count([fo])
        size = sb_export.export_glb(os.path.join(OUT, 'far.glb'), [fo], quality=85)
        stats['far_mb'] = round(size / 1e6, 2)
    collide = os.path.join(OUT, 'collide.obj')
    if os.path.exists(collide):
        stats['collide_tris'] = sum(1 for l in open(collide) if l.startswith('f '))
    hero = dict(district='shibuya', title='渋谷 スクランブル交差点〜SHIBUYA109', origin=list(ORIGIN), spawns=SPAWNS,
                labels=LABELS, stats=stats)
    json.dump(hero, open(os.path.join(OUT, 'hero.json'), 'w'), ensure_ascii=False, indent=1)
    print('export', stats)
