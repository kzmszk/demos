"""Assemble the whole district into collections:
  near      everything that ships (merged per draw group at bake/export; 'inst' objects stay instanced)
  lib       tree / plant source meshes (instanced from near), props_lib: prop sources (copied into near)
  collide   the walker's proxy
  context   the procedural neighbours and the ground (previews only)
"""
import bpy, math, random
import common as C
import materials as M
import uvmap as U


def build(log=print):
    C.reset()
    near = C.coll('near')
    lib = C.coll('lib')
    ctx = C.coll('context')
    col = C.coll('collide')
    R = random.Random(2090)
    import buildings, decals, plaza, rubble, dressing, foliage, props, collide, structures
    mass = C.massing()
    objs, crown = buildings.build(near)
    log('buildings', len(objs))
    dec = decals.Decals()
    pobjs, info = plaza.build(near, dec, R)
    log('plaza')
    robjs, rcol = rubble.build(near, dec, R)
    log('rubble')
    sobjs = structures.build(near, dec, R)
    log('structures')
    flib = foliage.tree_models(lib, log=lambda *a: None)
    plib = props.models()
    dressing.CROWN = crown
    blocked = dressing.Blocked(mass)
    PR = dressing.Props(plib, near, blocked)
    dressing.leftovers(PR, R)
    dressing.street_furniture(PR, R, rubble)
    nv = dressing.road_vehicles(PR, R, rubble)
    log('props', len(PR.objs), 'vehicles', nv)
    P, occ = dressing.trees(near, flib, mass, blocked, rubble, info.get('pool'), R)
    log('trees', sum(P.n.values()))
    v = dressing.vines(near, mass, R, crown)
    log('vines', len(v.data.polygons))
    d = dec.build('decal_ground', M.make('decal'), near)
    d['grp'] = 'decal_ground'
    log('decals', len(d.data.polygons))
    # hard budget: thin the trees (never near the spawns or in the plaza) until near.glb fits under 392 k triangles
    def tris(me):
        me.calc_loop_triangles(); return len(me.loop_triangles)
    cache = {}
    def ntri(o):
        if o.data.name not in cache: cache[o.data.name] = tris(o.data)
        return cache[o.data.name]
    total = sum(ntri(o) for o in near.all_objects if o.type == 'MESH' and o.get('lod', 'both') in ('both', 'near'))
    import hero_meta
    cand = [o for o in near.all_objects if o.type == 'MESH' and o.get('inst') and o.get('lod') == 'near'
            and any(k in o.data.name for k in ('zelkova', 'street', 'roof'))
            and not (abs(o.location.x - 60) < 40 and abs(o.location.y - 75) < 50)
            and all((o.location.x - sp['x']) ** 2 + (o.location.y - sp['y']) ** 2 > 400 for sp in hero_meta.SPAWNS)]
    R2 = random.Random(7); R2.shuffle(cand)
    removed = 0
    while total > 392000 and cand:
        o = cand.pop()
        total -= ntri(o)
        lo = [c for c in near.all_objects if c.get('lod') == 'mid' and c.type == 'MESH' and (c.location - o.location).length < 0.01]
        for c in lo: bpy.data.objects.remove(c, do_unlink=True)
        bpy.data.objects.remove(o, do_unlink=True); removed += 1
    log('near budget', total, 'removed trees', removed)
    # collision
    extra = [o for o in pobjs if o.name in ('plaza_mat', 'plaza_det')] + [bpy.data.objects['b000_mat']] + [o for o in sobjs if o.get('collide')]
    inst = [o for o in near.all_objects if o.get('inst') and o.type == 'MESH']
    collide.build(mass, crown, extra, PR.boxes, inst)
    log('collide')
    # context for previews
    for o in C.import_obj(C.SRC + 'ground.obj'):
        o.name = 'ground'; C.link(o, ctx)
    for o in C.import_obj(C.SRC + 'context.obj'):
        C.link(o, ctx)
    gm = bpy.data.materials.new('ctx_grey'); gm.diffuse_color = (0.5, 0.5, 0.48, 1)
    gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.11, 0.11, 0.10, 1)
    for o in ctx.objects:
        if o.type == 'MESH':
            o.data.materials.clear(); o.data.materials.append(gm)
    lib_hide = [lib, bpy.data.collections.get('props_lib'), col]
    for c in lib_hide:
        if c is None: continue
        c.hide_render = True
        lc = bpy.context.view_layer.layer_collection.children.get(c.name)
        if lc: lc.exclude = False
