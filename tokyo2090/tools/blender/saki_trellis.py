"""Saki from the TRELLIS.2 scan-like model: rig, white wings, the game's five actions.

    blender -b --python tools/blender/saki_trellis.py                  # build + export + previews
    blender -b --python tools/blender/saki_trellis.py -- --no-wings    # body only (rig check)
    options after --: --out PATH (default public/models/saki.glb), --no-previews, --debug

The source is an image-to-3D model made with TRELLIS.2 (~/work/trellis, v3_1536_s1_hair.glb: one fused mesh,
clothes included, 2048² texture, A-pose). It replaces the procedural body of saki.py; the game-facing contract is
the same: armature names (root hips spine chest neck head, shoulder/upperarm/forearm/hand, thigh/shin/foot .L/.R),
actions fly (2 s) sit (3 s) stand (3 s) walk (1.07 s) run (0.67 s) + flyhand (2 s, fly with the right wing folded,
for hand in hand), hips at the origin, facing +Y in Blender
(-Z in glTF). The pose functions are saki.py's, minus the ponytail and the cape; she has wings instead:

  * per side wing1 (arm, from the shoulder blade) -> wing2 (hand), one bone per flight feather
    (fp.* primaries on the hand, fs.* secondaries on the arm) so the feathers can swing from spread to folded;
    coverts are rigid on the arm bones.
  * each feather is a curved, twisted strip cut out by an alpha-masked texture; a rounded leading edge, three rows of
    coverts, a gull shape and a rounded tip keep the spread wing from reading as a flat board.
  * fly: spread wide, feathers trailing toward her feet, a slow glide breathing. stand/sit/walk/run: folded along
    her back, the wrist above the shoulder, the primaries hanging to her knees. flyhand: the right wing tucked back
    over her back (he is on that side), the left one half swept back.

Joints were picked by hand on an orthographic front render of the source (pixel picks below, depth = centre of
the mesh around the pick).
"""
import bpy, bmesh, sys, os, math, time, json
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.kdtree import KDTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC = '/home/kazu/work/trellis/outputs/v3/1536/v3_1536_s1_hair.glb'
LOW = '/home/kazu/work/trellis/outputs/v3/1536/v3_1536_s1_low45k.ply'
FRONT = '/home/kazu/work/trellis/faceproj/front_render.json'     # the ortho camera the picks were made in
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT_GLB = opt('--out', os.path.join(ROOT, 'public', 'models', 'saki.glb'))
PREV_DIR = os.path.join(HERE, 'previews_trellis')
WINGS = '--no-wings' not in ARGS
HEIGHT = 1.60
T0 = time.time()


def log(*a):
    print('[saki-t %6.1fs]' % (time.time() - T0), *a, flush=True)


def activate(ob):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


# ---------------------------------------------------------------- joints (front-render pixels, x right, y down)
# image left is her right (.R): the source faces the camera (-Y), turned 180° below
PICK = {
    'head_top': (1003, 30), 'neck1': (1000, 330), 'neck0': (1000, 405), 'hips': (1000, 985),
    'clav.R': (975, 415), 'clav.L': (1025, 415),
    'shoulder.R': (845, 455), 'shoulder.L': (1165, 455),
    'elbow.R': (725, 745), 'elbow.L': (1285, 745),
    'wrist.R': (600, 987), 'wrist.L': (1440, 980),
    'hand_end.R': (560, 1120), 'hand_end.L': (1490, 1133),
    'hip.R': (905, 1010), 'hip.L': (1095, 1010),
    'knee.R': (905, 1440), 'knee.L': (1140, 1440),
    'ankle.R': (935, 1900), 'ankle.L': (1215, 1900),
}


def load_source():
    bpy.ops.import_scene.gltf(filepath=SRC, merge_vertices=True)
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    activate(meshes[0])
    for o in meshes:
        o.select_set(True)
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in list(bpy.context.scene.objects):
        if o != ob:
            bpy.data.objects.remove(o)
    ob.name = 'SakiMesh'
    return ob


def joints_from_picks(ob):
    cam = json.load(open(FRONT))
    co = np.array([v.co for v in ob.data.vertices])
    J = {}
    for k, (px, py) in PICK.items():
        x = cam['cx'] + (px / cam['res'] - 0.5) * cam['scale']
        z = cam['cz'] + (0.5 - py / cam['res']) * cam['scale']
        r = 0.012 if k.startswith(('wrist', 'hand', 'elbow', 'ankle', 'knee')) else 0.02
        near = co[(np.abs(co[:, 0] - x) < r) & (np.abs(co[:, 2] - z) < r)]
        y = 0.5 * (near[:, 1].min() + near[:, 1].max()) if len(near) else 0.0
        J[k] = np.array([x, y, z])
    if 'head_top' in J:     # the head bone runs up the middle of the skull, not along its front surface
        J['head_top'][1] = J['neck1'][1]
    return J


def normalize(ob, J, others=()):
    """Turn to face +Y, scale to HEIGHT with the feet on z = 0, then put the hips at the origin (ob's bounds;
    the same transform goes to `others`)."""
    co = np.array([v.co for v in ob.data.vertices])
    lo, hi = co.min(0), co.max(0)
    s = HEIGHT / (hi[2] - lo[2])
    M = np.diag([-s, -s, s])                         # 180° about Z, uniform scale
    t = -M @ np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    f = lambda p: M @ p + t
    J = {k: f(p) for k, p in J.items()}
    origin = J['hips'].copy(); origin[1] = 0.0
    J = {k: p - origin for k, p in J.items()}
    for o in (ob,) + tuple(others):
        c0 = np.array([v.co for v in o.data.vertices])
        for v, c in zip(o.data.vertices, c0 @ M.T + t - origin):
            v.co = c
        o.data.update()
    log('scale %.3f, floor at z=%.3f' % (s, -origin[2]))
    return J, -origin[2]


def load_low(hi):
    """The game mesh: SRC simplified by CuMesh (~/work/trellis/faceproj/simplify_glb.py; Blender's collapse decimate
    shreds this mesh into slivers). PLY in glTF axes; gets a copy of the source material, re-unwrapped and baked."""
    bpy.ops.wm.ply_import(filepath=LOW)
    ob = bpy.context.view_layer.objects.active
    ob.rotation_euler = (math.pi / 2, 0, 0)          # glTF Y-up -> Blender Z-up
    activate(ob)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    ob.name = 'SakiMesh'; ob.data.name = 'SakiMesh'
    ob.data.materials.append(hi.data.materials[0].copy())
    bpy.ops.object.shade_smooth()
    log('low mesh %d tris' % sum(len(p.vertices) - 2 for p in ob.data.polygons))
    return ob


def rebake(body, hi, size=2048):
    """Collapse decimation drags UV seams across islands (dark cracks from the texture padding). Re-unwrap the low
    mesh and bake the colour from the full-resolution copy (emission bake, selected to active)."""
    activate(body)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.002)
    bpy.ops.object.mode_set(mode='OBJECT')
    img = bpy.data.images.new('SakiBody', size, size, alpha=False)
    hm = hi.data.materials[0].copy(); hi.data.materials[0] = hm
    nt = hm.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    src = bsdf.inputs['Base Color'].links[0].from_socket
    em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(src, em.inputs['Color'])
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'); nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    bm_ = body.data.materials[0]
    tex = next(n for n in bm_.node_tree.nodes if n.type == 'TEX_IMAGE' and n.outputs['Color'].links)
    tex.image = img
    bm_.node_tree.nodes.active = tex
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'GPU'; scene.cycles.samples = 1
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == 'OPTIX'
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = 0.006
    scene.render.bake.max_ray_distance = 0.02
    scene.render.bake.margin = 6
    activate(hi); body.select_set(True); bpy.context.view_layer.objects.active = body
    bpy.ops.object.bake(type='EMIT')
    img.pack()
    bpy.data.objects.remove(hi, do_unlink=True)
    bpy.context.view_layer.update()
    log('texture re-baked %d²' % size)


def tidy_material(ob):
    """One opaque skin-ish PBR material: drop the metal/rough map (half the file and an odd sheen), JPEG colour."""
    for mat in ob.data.materials:
        mat.name = 'Body'
        nt = mat.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        for inp in ('Metallic', 'Roughness'):
            for l in list(bsdf.inputs[inp].links):
                nt.links.remove(l)
        bsdf.inputs['Metallic'].default_value = 0.0
        bsdf.inputs['Roughness'].default_value = 0.62
        for n in list(nt.nodes):
            if n.type == 'TEX_IMAGE' and not any(l.to_socket == bsdf.inputs['Base Color'] for l in n.outputs['Color'].links):
                if not n.outputs['Color'].links or all(l.to_node.type == 'SEPARATE_COLOR' for l in n.outputs['Color'].links):
                    nt.nodes.remove(n)
        for n in nt.nodes:
            if n.type == 'TEX_IMAGE':
                n.image.file_format = 'JPEG'


# ---------------------------------------------------------------- armature
def nrm(v):
    v = np.asarray(v, dtype=np.float64)
    return v / np.linalg.norm(v)


BODY_BONES = ['root', 'hips', 'spine', 'chest', 'neck', 'head'] + \
    [b + sx for sx in ('.L', '.R') for b in ('shoulder', 'upperarm', 'forearm', 'hand')] + \
    [b + sx for sx in ('.L', '.R') for b in ('thigh', 'shin', 'foot')]


def body_table(J, floor):
    h, n0, n1, top = J['hips'], J['neck0'], J['neck1'], J['head_top']
    up = n0 - h
    T = {
        'root': (h, h + np.array([0, -0.12, 0]), None),
        'hips': (h, h + 0.22 * up, 'root'),
        'spine': (h + 0.22 * up, h + 0.53 * up, 'hips'),
        'chest': (h + 0.53 * up, n0, 'spine'),
        'neck': (n0, n1, 'chest'),
        'head': (n1, top, 'neck'),
    }
    for sx in ('.L', '.R'):
        T['shoulder' + sx] = (J['clav' + sx], J['shoulder' + sx], 'chest')
        T['upperarm' + sx] = (J['shoulder' + sx], J['elbow' + sx], 'shoulder' + sx)
        T['forearm' + sx] = (J['elbow' + sx], J['wrist' + sx], 'upperarm' + sx)
        T['hand' + sx] = (J['wrist' + sx], J['hand_end' + sx], 'forearm' + sx)
        T['thigh' + sx] = (J['hip' + sx], J['knee' + sx], 'hips')
        T['shin' + sx] = (J['knee' + sx], J['ankle' + sx], 'thigh' + sx)
        ball = J['ball' + sx]
        T['foot' + sx] = (J['ankle' + sx], ball, 'shin' + sx)
    return T


def make_armature(T, order):
    arm = bpy.data.armatures.new('SakiRig')
    ob = bpy.data.objects.new('Saki', arm)
    bpy.context.scene.collection.objects.link(ob)
    activate(ob)
    bpy.ops.object.mode_set(mode='EDIT')
    for name in order:
        h, t, par = T[name][:3]
        eb = arm.edit_bones.new(name)
        eb.head = Vector(h); eb.tail = Vector(t)
        d = nrm(np.asarray(t) - np.asarray(h))
        eb.align_roll(Vector((0, 1, 0)) if abs(d[1]) < 0.9 else Vector((0, 0, 1)))
        if par:
            eb.parent = arm.edit_bones[par]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    arm.display_type = 'STICK'
    return ob


def skin(body, rig):
    """Bone heat fails on the scan mesh (open seams, loose bits, fused clothes), so: voxel-remesh a watertight proxy,
    give it automatic weights, and copy them onto the real mesh from the nearest proxy face."""
    proxy = body.copy(); proxy.data = body.data.copy(); proxy.name = 'proxy'
    bpy.context.scene.collection.objects.link(proxy)
    rm = proxy.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.008
    activate(proxy)
    bpy.ops.object.modifier_apply(modifier=rm.name)
    # drop voxel crumbs and small inner shells (they make the heat solve fail); keep real parts such as a foot
    # that the remesh cut off at a thin ankle strap
    bm = bmesh.new(); bm.from_mesh(proxy.data)
    seen, drop = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        comp, stack = [], [v]; seen.add(v.index)
        while stack:
            x = stack.pop(); comp.append(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index); stack.append(o)
        if len(comp) < 600:
            drop += comp
    bmesh.ops.delete(bm, geom=drop, context='VERTS')
    bm.to_mesh(proxy.data); bm.free()
    log('proxy shell %d verts' % len(proxy.data.vertices))
    # bone heat is unreliable at human scale in metres; solve it 20x larger
    proxy.scale = rig.scale = (20, 20, 20)
    bpy.context.view_layer.update()
    activate(proxy); rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    proxy.parent = None
    proxy.scale = rig.scale = (1, 1, 1)
    proxy.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()
    n = sum(1 for v in proxy.data.vertices if len(v.groups))
    log('proxy %d verts, %d weighted' % (len(proxy.data.vertices), n))
    if '--debug' in ARGS:
        gi = {g.index: g.name for g in proxy.vertex_groups}
        tot = {}
        for v in proxy.data.vertices:
            for e in v.groups:
                tot[gi[e.group]] = tot.get(gi[e.group], 0) + e.weight
        log('proxy weight sums', {k: round(w) for k, w in sorted(tot.items())})
        pc = np.array([v.co for v in proxy.data.vertices])
        log('proxy feet verts x+ %d x- %d' % (((pc[:, 2] < -0.77) & (pc[:, 0] > 0)).sum(), ((pc[:, 2] < -0.77) & (pc[:, 0] < 0)).sum()))
    for g in proxy.vertex_groups:
        body.vertex_groups.new(name=g.name)
    dt = body.modifiers.new('dt', 'DATA_TRANSFER'); dt.object = proxy
    dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
    activate(body)
    bpy.ops.object.modifier_apply(modifier=dt.name)
    bpy.data.objects.remove(proxy)
    body.parent = rig
    mod = body.modifiers.new('rig', 'ARMATURE'); mod.object = rig
    activate(body)
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    log('body skinned: %d / %d verts weighted' % (sum(1 for v in body.data.vertices if len(v.groups)), len(body.data.vertices)))


# ---------------------------------------------------------------- wings
WING_PRIM, WING_SEC = 10, 14
WING1_L, WING2_L = 0.44, 0.48
PRIM_LEN = (0.42, 0.72)       # inner -> longest primary (the outermost two are shorter again: a rounded tip)
SEC_LEN = (0.40, 0.36)        # body -> wrist


def wing_names(sx):
    return ['wing1' + sx, 'wing2' + sx] + ['fs%02d%s' % (i, sx) for i in range(WING_SEC)] + \
        ['fp%02d%s' % (i, sx) for i in range(WING_PRIM)]


def wing_rest(J):
    """Spread wings (rest = the gliding shape). The surface faces back (-Y, the sky in flight) and the feathers trail
    toward -Z (her feet in flight). Gull shape: the arm rises from the shoulder blade and reaches forward a little, the
    hand runs level and sweeps back. Secondaries are longest at the body; primaries fan out to point along the span
    and are longest two from the tip, so the tip is rounded rather than a comb."""
    out = {}
    rng = np.random.default_rng(3)                   # a little unevenness: no two feathers quite alike
    jit = lambda: 1.0 + rng.uniform(-0.04, 0.04)
    for s, sx in ((-1, '.L'), (1, '.R')):
        c = J['neck0'] + (J['hips'] - J['neck0']) * 0.22
        r0 = np.array([s * 0.07, J['back_y'] - 0.01, c[2]])
        d1 = nrm([s, -0.24, 0.13]); w1 = r0 + d1 * WING1_L
        d2 = nrm([s, -0.03, -0.10]); w2 = w1 + d2 * WING2_L
        out['wing1' + sx] = (r0, w1, 'chest', d1)
        out['wing2' + sx] = (w1, w2, 'wing1' + sx, d2)
        for i in range(WING_SEC):          # along the arm, root -> wrist
            a = (i + 0.5) / WING_SEC
            p = r0 + (w1 - r0) * a
            f = nrm([s * (0.02 + 0.10 * a + rng.uniform(-0.03, 0.03)), 0.0, -1])
            L = (SEC_LEN[0] + (SEC_LEN[1] - SEC_LEN[0]) * a) * jit()
            out['fs%02d%s' % (i, sx)] = (p, p + f * L, 'wing1' + sx, f)
        for i in range(WING_PRIM):         # along the hand, wrist -> tip, fanning out to point along the span
            a = i / (WING_PRIM - 1)
            p = w1 + (w2 - w1) * (0.04 + 0.94 * a)
            f = nrm(np.array([s * (0.15 + 1.05 * a ** 1.3 + rng.uniform(-0.03, 0.03)), 0.0, -1.0 + 0.62 * a ** 1.2]))
            L = (PRIM_LEN[0] + (PRIM_LEN[1] - PRIM_LEN[0]) * math.sin(min(1.0, a / 0.78) * math.pi / 2) - 0.10 * max(0.0, a - 0.78) / 0.22) * jit()
            out['fp%02d%s' % (i, sx)] = (p, p + f * L, 'wing2' + sx, f)
    return out


def feather(bm, uvl, base, tip, n, width, lift=0.0, camber=0.08, curl=0.0, twist=0.22, lead=1):
    """One feather as a curved, twisted strip; its outline (asymmetric vanes, ragged barbs, downy base) is cut by
    the texture's alpha. n is the side the feather faces (the sky in flight); `camber` bows the shaft away from n
    (the arched wing), `curl` turns the tip back toward n (a loaded primary), `twist` turns the vane about the shaft
    so neighbours overlap like shingles, `lift` raises the whole feather along n (layering). `lead` = which side
    (+-1 along cross(n, shaft)) carries the narrow leading vane."""
    base = np.asarray(base, float); tip = np.asarray(tip, float); n = np.asarray(n, float)
    d = tip - base; L = np.linalg.norm(d); d = d / L
    side = nrm(np.cross(n, d)) * lead
    vs = (0.0, 0.07, 0.16, 0.30, 0.45, 0.60, 0.74, 0.86, 0.95, 1.0)
    us = (0.0, 0.22, 0.38, 0.62, 1.0)          # rachis at u = 0.38: the leading vane (u < 0.38) is the narrow one
    rows = []
    for v in vs:
        env = 0.62 + 0.38 * min(1.0, v / 0.30) if v < 0.30 else math.sqrt(max(0.0, 1 - ((v - 0.30) / 0.74) ** 2)) * 0.9 + 0.1
        c = base + d * L * v + n * lift - n * camber * L * v ** 1.6 + n * curl * L * max(0.0, v - 0.5) ** 2 * 4
        tw = twist * (0.4 + 0.6 * v)
        lat = side * math.cos(tw) + n * math.sin(tw)
        rows.append([c + lat * (u - 0.38) * width * env for u in us])
    verts = [[bm.verts.new(Vector(p)) for p in r] for r in rows]
    for k in range(len(rows) - 1):
        for j in range(len(us) - 1):
            f = bm.faces.new((verts[k][j], verts[k][j + 1], verts[k + 1][j + 1], verts[k + 1][j]))
            for loop in f.loops:
                kk = k if loop.vert in verts[k] else k + 1
                jj = verts[kk].index(loop.vert)
                loop[uvl].uv = (us[jj], vs[kk])
    return [v for r in verts for v in r]


def feather_image(path):
    """Feather texture, u across (rachis at 0.38), v base -> tip. RGB: white vanes with fine barbs angled toward the
    tip, a few splits, a pale rachis, grey down at the base. Alpha: the outline (ragged barb ends, rounded tip, downy
    base), clipped at 0.5 in the material."""
    W, H = 256, 1024
    rng = np.random.default_rng(7)
    u = (np.arange(W) + 0.5) / W; v = (np.arange(H) + 0.5) / H
    U, Vv = np.meshgrid(u, v)
    x = U - 0.38                                   # signed distance from the rachis
    half = np.where(x < 0, 0.38, 0.62)
    r = np.abs(x) / half                          # 0 at the rachis, 1 at the geometry edge
    ang = Vv * 260 - np.abs(x) * 160              # barbs sweep toward the tip
    barb = 0.5 + 0.5 * np.sin(ang * 2 * np.pi / 3.0)
    tuft = rng.random((2, 400))                    # ragged barb ends: each tuft of barbs stops at its own length
    ti = np.clip((ang / 3.0).astype(int), 0, 399)
    edge = 0.86 + 0.10 * tuft[(x > 0).astype(int), ti] + 0.03 * np.sin(ang * 2 * np.pi / 3.0)
    alpha = (r < edge).astype(float)
    tip = Vv > 0.93                               # rounded tip
    alpha[tip & (np.abs(U - 0.42) > 0.5 * np.sqrt(np.clip(1 - ((Vv - 0.93) / 0.07) ** 2, 0, 1)))] = 0
    # splits in the vane: thin gaps along the barb direction
    for k in range(5):
        a0 = rng.uniform(40, 220); side = rng.choice([-1, 1]); wdt = rng.uniform(0.25, 0.7)
        split = (np.abs(ang - a0) < 1.2) & (np.sign(x) == side) & (r > 1 - wdt)
        alpha[split] = 0
    down = Vv < 0.10                               # fluffy base
    alpha[down & (rng.random((H, W)) > 0.35 + 6.5 * Vv)] = 0
    shade = 0.90 + 0.06 * barb - 0.10 * np.exp(-(Vv / 0.12) ** 2) - 0.04 * r ** 3
    rach = np.exp(-(x / 0.012) ** 2) * (0.10 * (1 - Vv) - 0.03)
    g = np.clip(shade - rach, 0, 1)
    rgba = np.stack([g * 0.985, g * 0.985, g, alpha], -1)
    img = bpy.data.images.new('feather', W, H, alpha=True)
    img.pixels = rgba[::-1].ravel().tolist()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    img.pack()
    return img


def wing_arm(bm, uvl, rest, sx):
    """The wing's leading edge: a rounded, tapering tube along wing1 -> wing2, flattened across the wing, so the
    wing has a thick front edge instead of a sheet. Returns [(vert, [(bone, w)])]."""
    r0, w1, w2 = (np.asarray(x) for x in (rest['wing1' + sx][0], rest['wing1' + sx][1], rest['wing2' + sx][1]))
    n = np.array([0.0, -1.0, 0.0])
    pts = [r0 + (w1 - r0) * t for t in np.linspace(0, 1, 9)] + [w1 + (w2 - w1) * t for t in np.linspace(0, 1, 9)[1:]]
    rad = [0.040 - 0.014 * t for t in np.linspace(0, 1, 9)] + [0.026 - 0.020 * t for t in np.linspace(0, 1, 9)[1:]]
    ring, out = [], []
    for k, (p, rr) in enumerate(zip(pts, rad)):
        d = nrm((pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]))
        a = nrm(np.cross(n, d)); b = nrm(np.cross(d, a))
        vs = [bm.verts.new(Vector(p + rr * (math.cos(t) * a * 1.0 + math.sin(t) * b * 0.55))) for t in np.linspace(0, 2 * math.pi, 9)[:-1]]
        dist1 = np.linalg.norm(p - w1)
        if k < 9:
            wgt = [('wing1' + sx, 1.0)] if dist1 > 0.05 else [('wing1' + sx, 0.5 + dist1 * 10), ('wing2' + sx, 0.5 - dist1 * 10)]
        else:
            wgt = [('wing2' + sx, 1.0)] if dist1 > 0.05 else [('wing2' + sx, 0.5 + dist1 * 10), ('wing1' + sx, 0.5 - dist1 * 10)]
        out += [(v_, wgt) for v_ in vs]
        ring.append(vs)
    for k in range(len(ring) - 1):
        for j in range(8):
            f = bm.faces.new((ring[k][j], ring[k][(j + 1) % 8], ring[k + 1][(j + 1) % 8], ring[k + 1][j]))
            for loop in f.loops:
                loop[uvl].uv = (0.30, 0.5)          # plain white vane
    bm.faces.new(ring[-1][::-1])
    return out


def make_wings(rest, rig):
    me = bpy.data.meshes.new('SakiWings')
    ob = bpy.data.objects.new('SakiWings', me)
    bpy.context.scene.collection.objects.link(ob)
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    groups = {}          # vertex -> [(bone, weight)]
    n = np.array([0.0, -1.0, 0.0])
    for s, sx in ((-1, '.L'), (1, '.R')):
        # flight feathers, one bone each; the inner ones lie on top so each tucks its trailing vane under the next
        for i in range(WING_SEC):
            b = 'fs%02d%s' % (i, sx); h, t = rest[b][0], rest[b][1]
            for v in feather(bm, uvl, h, t, n, 0.085, lift=0.004 * (WING_SEC - i), camber=0.10, twist=0.09, lead=-s):
                groups[v] = [(b, 1.0)]
        for i in range(WING_PRIM):
            a = i / (WING_PRIM - 1)
            b = 'fp%02d%s' % (i, sx); h, t = rest[b][0], rest[b][1]
            for v in feather(bm, uvl, h, t, n, 0.078 - 0.012 * a, lift=-0.002 * i, camber=0.06, curl=0.05 + 0.07 * a,
                             twist=0.15, lead=-s):
                groups[v] = [(b, 1.0)]
        # coverts in three rows over the bases of the flight feathers (greater, median, lesser): each rides on the
        # nearest flight feather so it swings with it from spread to folded
        r0, w1, w2 = rest['wing1' + sx][0], rest['wing1' + sx][1], rest['wing2' + sx][1]
        for row, (L, wd, lift, cnt, back) in enumerate(((0.22, 0.070, 0.022, 18, 0.010), (0.13, 0.060, 0.034, 20, 0.004),
                                                         (0.075, 0.050, 0.044, 24, -0.004))):
            for i in range(cnt):
                a = (i + 0.5) / cnt
                p = r0 + (w1 - r0) * a * 2 if a < 0.5 else w1 + (w2 - w1) * (a - 0.5) * 2 * (0.85 - 0.15 * row)
                p = p + np.array([0, 0, back])
                f = nrm([s * (0.05 + 0.4 * max(0, a - 0.5)), 0.0, -1])
                if a < 0.5:
                    fb = 'fs%02d%s' % (min(WING_SEC - 1, int(a * 2 * WING_SEC)), sx)
                else:
                    fb = 'fp%02d%s' % (min(WING_PRIM - 1, int((a - 0.5) * 2 * 0.85 * WING_PRIM)), sx)
                L_ = L * (1.0 - 0.3 * max(0, a - 0.5)) * (1 + 0.08 * math.sin(i * 2.3 + row))
                for v in feather(bm, uvl, p, p + f * L_, n, wd, lift=lift + 0.001 * (i % 2), camber=0.12, twist=0.08, lead=-s):
                    groups[v] = [(fb, 1.0)]
        for v, wgt in wing_arm(bm, uvl, rest, sx):
            groups[v] = wgt
    bm.verts.index_update()
    groups = {v.index: lst for v, lst in groups.items()}
    bm.to_mesh(me); bm.free()
    for poly in me.polygons:
        poly.use_smooth = True
    vg = {}
    for v, lst in groups.items():
        for b, w in lst:
            if b not in vg:
                vg[b] = ob.vertex_groups.new(name=b)
            vg[b].add([v], w, 'REPLACE')
    mat = bpy.data.materials.new('Wing')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = feather_image(os.path.join(PREV_DIR, 'feather.png'))
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    # alpha clip at 0.5: the glTF exporter writes alphaMode MASK for 1 - (alpha < cutoff)
    lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.5
    sub = nt.nodes.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; sub.inputs[0].default_value = 1.0
    nt.links.new(tex.outputs['Alpha'], lt.inputs[0]); nt.links.new(lt.outputs[0], sub.inputs[1])
    nt.links.new(sub.outputs[0], bsdf.inputs['Alpha'])
    bsdf.inputs['Roughness'].default_value = 0.75
    # feathers pass some light: a faint self-glow keeps the shaded underside from going slate grey against the sky
    bsdf.inputs['Emission Color'].default_value = (0.13, 0.13, 0.14, 1.0)
    bsdf.inputs['Emission Strength'].default_value = 1.0
    me.materials.append(mat)
    ob.parent = rig
    mod = ob.modifiers.new('rig', 'ARMATURE'); mod.object = rig
    log('wings: %d tris' % sum(len(p.vertices) - 2 for p in me.polygons))
    return ob


# ---------------------------------------------------------------- animation (saki.py's poses)
def Rx(d): return Quaternion((1, 0, 0), math.radians(d))
def Ry(d): return Quaternion((0, 1, 0), math.radians(d))
def Rz(d): return Quaternion((0, 0, 1), math.radians(d))


def vnorm(*a):
    return Vector(a).normalized()


def toward(d, target, deg):
    d = Vector(d).normalized(); t = Vector(target).normalized()
    ax = d.cross(t)
    if ax.length < 1e-6:
        return d
    return (Quaternion(ax.normalized(), math.radians(deg)) @ d).normalized()


def q_aim(rest_d, rest_u, new_d, new_u):
    def frame(d, u):
        d = Vector(d).normalized(); u = Vector(u); u = (u - d * u.dot(d)).normalized(); w = d.cross(u)
        return Matrix((d, u, w)).transposed()
    return (frame(new_d, new_u) @ frame(rest_d, rest_u).transposed()).to_quaternion()


RF = {}
ORDER = []


def rest_frames(T):
    out = {}
    for b, rec in T.items():
        h, t = np.asarray(rec[0]), np.asarray(rec[1])
        d = Vector(nrm(t - h))
        if b.startswith(('upperarm', 'forearm', 'hand')):
            s = -1 if b.endswith('.L') else 1
            u = Vector(nrm(np.cross(np.asarray(d), [0, 1, 0]) * (-s)))       # palms toward the thighs
        elif b.startswith('foot'):
            u = Vector((0, 0, 1))
        elif b.startswith(('thigh', 'shin')):
            u = Vector((0, 1, 0))
        elif b.startswith(('wing', 'fs', 'fp')):
            u = Vector((0, -1, 0))                                           # wing surface faces back at rest
        else:
            u = Vector((0, 1, 0)) if abs(d.y) < 0.9 else Vector((0, 0, 1))
        out[b] = (d, u)
    return out


def aim(b, d, u):
    return q_aim(RF[b][0], RF[b][1], Vector(d), Vector(u))


def slerpv(a, b, t):
    a = Vector(a).normalized(); b = Vector(b).normalized()
    return a.slerp(b, t) if a.dot(b) > -0.999 else (a * (1 - t) + b * t).normalized()


def wing_rot(fold, t, flap=0.0, fold_r=None, tuck=False):
    """fold 0 = spread for gliding, 1 = folded. flap: small up-down of the spread wing (degrees). fold_r: the right
    wing's own fold amount.
    Folded standing (tuck False), each wing lies in a nearly upright plane facing out (normal n): the arm rises up and
    back from the shoulder blade, the hand comes down, the flight feathers hang down and back in a fan that narrows
    to the tip. Tucked in flight (tuck True), the wing sweeps back flat over her back toward her feet, like a
    stooping bird: folded the standing way, its arch stood up past her head right beside his eyes."""
    r = {}
    if not WINGS:
        return r
    up, down = Vector((0, 0, 1)), Vector((0, 0, -1))
    fold_l = fold
    for s, sx in ((-1, '.L'), (1, '.R')):
        fold = fold_r if (sx == '.R' and fold_r is not None) else fold_l
        fl = Ry(-s * flap)
        if tuck:
            n_fd = Vector((0, -1, 0))
            t1, t2 = vnorm(s * 0.55, -0.12, -0.83), vnorm(-s * 0.06, -0.08, -1)
            fs_d = lambda i: vnorm(s * 0.05, -0.04, -1)
            fp_d = lambda a: vnorm(-s * (0.02 + 0.04 * a), -0.03 - 0.02 * a, -1)
        else:
            n_fd = vnorm(s * 0.95, 0.30, 0.0)                     # facing out and a little forward: a V behind her
            h = (down.cross(n_fd) * s).normalized()              # in the folded plane, pointing back and out
            t1, t2 = (up * 0.85 + h * 0.5).normalized(), (down + h * 0.22).normalized()
            fs_d = lambda i: (down + h * (0.30 + 0.25 * i / WING_SEC)).normalized()
            fp_d = lambda a: (down + h * (0.50 - 0.40 * a)).normalized()   # inner ones angled back, the outer ones close the tip
        n = slerpv(fl @ Vector((0, -1, 0)), n_fd, fold)
        d1 = slerpv(fl @ Vector(RF['wing1' + sx][0]), t1, fold)
        d2 = slerpv(fl @ Ry(-s * 0.6 * flap) @ Vector(RF['wing2' + sx][0]), t2, fold)
        r['wing1' + sx] = aim('wing1' + sx, d1, n)
        r['wing2' + sx] = aim('wing2' + sx, d2, n)
        for i in range(WING_SEC):
            b = 'fs%02d%s' % (i, sx)
            r[b] = aim(b, slerpv(fl @ Vector(RF[b][0]), fs_d(i), fold), n)
        for i in range(WING_PRIM):
            b = 'fp%02d%s' % (i, sx)
            r[b] = aim(b, slerpv(fl @ Ry(-s * 0.6 * flap) @ Vector(RF[b][0]), fp_d(i / (WING_PRIM - 1)), fold), n)
    return r


def pose_fly(t):
    w = 2 * math.pi * t / 2.0
    r = {'spine': Rx(6), 'chest': Rx(14 + 1.0 * math.sin(w)), 'neck': Rx(36), 'head': Rx(72 + 2 * math.sin(w + 1))}
    for s, sx in ((-1, '.L'), (1, '.R')):
        el = math.radians(15 + 5 * math.sin(w))
        du = vnorm(s * math.cos(el), -0.30, -math.sin(el))
        r['shoulder' + sx] = Ry(-s * 6) @ Rx(6)
        r['upperarm' + sx] = aim('upperarm' + sx, du, (0, 1, 0))
        df = toward(du, (0, 0.35, -1), 7 + 5 * math.sin(w + 0.6))
        dh = toward(df, (0, 0.2, -1), 4)
        if s > 0:   # right hand: palm toward the direction of flight, open, to be held
            r['forearm' + sx] = aim('forearm' + sx, df, (0, 0.75, 0.66))
            r['hand' + sx] = aim('hand' + sx, toward(df, (0, 0, 1), 6), (0, 0.15, 1))
        else:
            r['forearm' + sx] = aim('forearm' + sx, df, (0, 1, 0))
            r['hand' + sx] = aim('hand' + sx, dh, (0, 1, 0))
        ph = 0.0 if s < 0 else math.pi
        dt = Rx(-6 + 5 * math.sin(w + ph)) @ vnorm(s * math.sin(math.radians(13)), 0, -math.cos(math.radians(13)))
        r['thigh' + sx] = aim('thigh' + sx, dt, (0, 1, 0))
        ds = toward(dt, (0, -1, 0), 5 + 6 * (0.5 + 0.5 * math.sin(w + ph + 0.9)))
        r['shin' + sx] = aim('shin' + sx, ds, (0, 1, 0))
        dfo = toward(ds, (0, 1, 0), 28)
        r['foot' + sx] = aim('foot' + sx, dfo, (0, 1, 0))
    r.update(wing_rot(FLY_FOLD_L, t, flap=4.0 * math.sin(w) * (1 - FLY_FOLD_L), fold_r=FLY_FOLD_R, tuck=True))
    return {'root_rot': Rx(-90) @ Rz(2 * math.sin(w)), 'rot': r}


FLY_FOLD_R, FLY_FOLD_L = None, 0.0


def pose_flyhand(t):
    """fly while he holds her right hand: he is 1.35 m (drawn in: 0.62 m) to her right, inside the span of her right
    wing, so that wing tucks back over her back; the left one is half swept back (fully spread, so close to his
    eyes, it covered half the view)."""
    global FLY_FOLD_R, FLY_FOLD_L
    FLY_FOLD_R, FLY_FOLD_L = 0.9, 0.45
    try:
        return pose_fly(t)
    finally:
        FLY_FOLD_R, FLY_FOLD_L = None, 0.0


def pose_stand(t):
    w = 2 * math.pi * t / 3.0
    b = math.sin(w)
    r = {'hips': Rz(-4) @ Ry(-7), 'spine': Ry(2), 'chest': Rz(-2) @ Ry(4) @ Rx(1.2 * b), 'neck': Ry(2) @ Rx(-3),
         'head': Rz(6 + 2.5 * math.sin(w + 0.5)) @ Ry(4) @ Rx(-7)}
    for s, sx in ((-1, '.L'), (1, '.R')):
        r['shoulder' + sx] = Ry(s * 3) @ Rx(0.6 * b)
        du = vnorm(s * 0.17, -0.10 + 0.006 * b, -1)
        df = vnorm(s * 0.11, -0.03 + 0.01 * b, -1)
        r['upperarm' + sx] = aim('upperarm' + sx, du, (-s, 0.25, 0))
        r['forearm' + sx] = aim('forearm' + sx, df, (-s, 0.4, 0))
        r['hand' + sx] = aim('hand' + sx, toward(df, (s * 0.2, 0.3, -1), 4), (-s, 0.45, 0))
    r['thigh.R'] = aim('thigh.R', vnorm(-0.02, 0.0, -1), (0, 1, 0))
    r['shin.R'] = aim('shin.R', vnorm(-0.01, -0.02, -1), (0, 1, 0))
    r['thigh.L'] = aim('thigh.L', vnorm(-0.11, 0.12, -1), (-0.15, 1, 0))
    r['shin.L'] = aim('shin.L', vnorm(-0.07, -0.08, -1), (-0.15, 1, 0))
    for sx, yaw in (('.L', 14), ('.R', -6)):
        r['foot' + sx] = Rz(yaw) @ (Rx(8) if sx == '.L' else Quaternion())
    r.update(wing_rot(1.0, t))
    return {'rot': r, 'ground': 'shin.R'}


WALK_T, RUN_T = 32 / 30, 20 / 30


def gait(t, run=False):
    P = RUN_T if run else WALK_T
    w = 2 * math.pi * t / P
    r = {}
    lean = 9 if run else 2.5
    r['hips'] = Rz((7 if run else 5) * math.sin(w)) @ Ry((2 if run else 3) * math.sin(w + math.pi / 2)) @ Rx(-lean * 0.4)
    r['spine'] = Rx(-lean * 0.5) @ Rz(-2.0 * math.sin(w))
    r['chest'] = Rx(-lean * 0.4 + 1.0 * math.sin(2 * w)) @ Rz(-(6 if run else 4) * math.sin(w))
    r['neck'] = Rx(lean * 0.6) @ Rz(1.5 * math.sin(w))
    r['head'] = Rx(-3 + lean * 0.5 + 1.2 * math.sin(2 * w + 0.6)) @ Rz(1.5 * math.sin(w))
    for s, sx in ((-1, '.L'), (1, '.R')):
        ph = w if s < 0 else w + math.pi
        phw = math.atan2(math.sin(ph), math.cos(ph))
        if run:
            a = 30 * math.sin(ph) + 6
            k = 18 + 88 * max(0.0, math.cos(ph + 0.45)) ** 1.6
        else:
            a = 22 * math.sin(ph)
            k = 6 + 52 * max(0.0, math.cos(ph + 0.35)) ** 2.2
        dt = vnorm(s * 0.035, math.sin(math.radians(a)), -math.cos(math.radians(a)))
        r['thigh' + sx] = aim('thigh' + sx, dt, (0, 1, 0))
        ds = toward(dt, (0, -1, 0), k)
        r['shin' + sx] = aim('shin' + sx, ds, (0, 1, 0))
        td = (40 if run else 30) * math.exp(-((phw + 1.25) / 0.55) ** 2)
        tu = (8 if run else 14) * math.exp(-((phw - 1.45) / 0.5) ** 2)
        df = Rx(tu - td) @ vnorm(s * 0.08, 0.87, -0.50)
        r['foot' + sx] = aim('foot' + sx, df, (0, 0, 1))
        b = (28 if run else 16) * math.sin(ph + math.pi) + (-6 if run else 2)
        r['shoulder' + sx] = Ry(s * 3) @ Rx(-0.15 * b)
        du = vnorm(s * (0.22 if run else 0.16), math.sin(math.radians(b)), -math.cos(math.radians(b)))
        el = (72 if run else 14) + (6 if run else 10) * max(0.0, math.sin(math.radians(b)) * 2)
        dfa = toward(du, (0, 1, 0.15), el)
        r['upperarm' + sx] = aim('upperarm' + sx, du, (-s, 0.25, 0))
        r['forearm' + sx] = aim('forearm' + sx, dfa, (-s, 0.4, 0))
        r['hand' + sx] = aim('hand' + sx, toward(dfa, (s * 0.2, 0.3, -1), 4 if not run else 20), (-s, 0.45, 0))
    # folded wings ride along: a little lift and bounce with each step, more when running
    r.update(wing_rot(0.92 if run else 1.0, t))
    bob = (0.035 * math.cos(2 * w)) if run else 0.0
    return {'rot': r, 'ground': ['shin.L', 'shin.R'], 'bob': bob}


def pose_walk(t):
    return gait(t, False)


def pose_run(t):
    return gait(t, True)


def pose_sit(t):
    w = 2 * math.pi * t / 3.0
    b = math.sin(w)
    r = {'hips': Rx(8), 'spine': Rx(2), 'chest': Rx(-1 + 1.2 * b), 'neck': Rx(-3),
         'head': Rz(17 + 3 * math.sin(w + 0.4)) @ Ry(-3) @ Rx(-7 + 1.5 * math.sin(w + 1.3))}
    for s, sx in ((-1, '.L'), (1, '.R')):
        r['shoulder' + sx] = Ry(-s * 4) @ Rx(0.6 * b)
        du = vnorm(s * 0.12, -0.10, -1)
        df = vnorm(s * 0.05, -0.10, -1)
        r['upperarm' + sx] = aim('upperarm' + sx, du, (-s, 1, 0))
        r['forearm' + sx] = aim('forearm' + sx, df, (0, 1, 0))
        r['hand' + sx] = aim('hand' + sx, vnorm(s * 0.25, 0.97, -0.05), (0, 0, -1))
        r['thigh' + sx] = aim('thigh' + sx, vnorm(s * 0.10, 1, -0.06), (0, 0, 1))
        sw = 5 * math.sin(w + (0 if s < 0 else 2.2))
        ds = Rx(sw) @ vnorm(s * 0.03, 0.10, -1)
        r['shin' + sx] = aim('shin' + sx, ds, (0, 1, 0))
        r['foot' + sx] = aim('foot' + sx, Rx(sw) @ vnorm(s * 0.10, 0.62, -0.78), Rx(sw) @ Vector((0, 0.78, 0.62)))
    r.update(wing_rot(1.0, t))
    return {'rot': r}


def solve(rig, pose):
    R = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    Qr = pose.get('root_rot', Quaternion()); Lr = Vector(pose.get('root_loc', (0, 0, 0)))
    rot = pose.get('rot', {})
    rh = R['root'].translation.copy()
    P, out = {}, {}
    for name in ORDER:
        bone = rig.data.bones[name]
        Rb = R[name]
        if name == 'root':
            Pb = Matrix.Translation(rh + Lr) @ (Qr @ Rb.to_quaternion()).to_matrix().to_4x4()
            L = Rb.inverted() @ Pb
        else:
            par = bone.parent.name
            head = P[par] @ (R[par].inverted() @ Rb.translation)
            q = Qr @ rot.get(name, Quaternion())
            Pb = Matrix.Translation(head) @ (q @ Rb.to_quaternion()).to_matrix().to_4x4()
            L = (P[par] @ R[par].inverted() @ Rb).inverted() @ Pb
        P[name] = Pb
        loc, q, sc = L.decompose()
        out[name] = (loc, q, sc)
    return out, P


def bake_action(rig, name, fn, seconds, fps=30):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = act
    nf = int(round(seconds * fps))
    prev = {}
    R = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    for f in range(nf + 1):
        t = (f % nf) / fps
        pose = fn(t)
        out, P = solve(rig, pose)
        if pose.get('ground'):
            gl = pose['ground'] if isinstance(pose['ground'], list) else [pose['ground']]
            dz = None
            for sb in gl:
                ank = P[sb] @ Vector((0, rig.data.bones[sb].length, 0))
                rest_ank = R[sb] @ Vector((0, rig.data.bones[sb].length, 0))
                d = rest_ank.z - ank.z
                dz = d if dz is None else max(dz, d)
            pose['root_loc'] = (0, 0, dz + pose.get('bob', 0.0))
            out, P = solve(rig, pose)
        for bn, (loc, q, sc) in out.items():
            pb = rig.pose.bones[bn]
            pb.rotation_mode = 'QUATERNION'
            if bn in prev and prev[bn].dot(q) < 0:
                q = -q
            prev[bn] = q.copy()
            pb.location = loc
            pb.rotation_quaternion = q
            pb.keyframe_insert('location', frame=f, group=bn)
            pb.keyframe_insert('rotation_quaternion', frame=f, group=bn)
    act.frame_range = (0, nf)
    act.use_frame_range = True
    tr = rig.animation_data.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 0, act)
    tr.mute = True
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    log('action %s: %d frames' % (name, nf + 1))
    return act


# ---------------------------------------------------------------- previews
def previews(rig, floor):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == 'OPTIX'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 640, 800
    scene.view_settings.view_transform = 'Standard'
    world = bpy.data.worlds.new('w'); world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.42, 0.43, 0.46, 1)
    scene.world = world
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam); scene.camera = cam
    cam.data.lens = 40
    os.makedirs(PREV_DIR, exist_ok=True)
    shots = [('stand', 30, 35), ('stand', 30, 180), ('stand', 30, 90), ('walk', 8, 35), ('run', 6, 60), ('sit', 30, 35),
             ('fly', 15, 20), ('fly', 15, 140), ('fly', 15, 180), ('flyhand', 15, 180), ('flyhand', 15, 100)]
    if '--shots' in ARGS:
        keep = opt('--shots', '').split(',')
        shots = [sh for sh in shots if '%s_%d' % (sh[0], sh[2]) in keep]
    for act_name, frame, yaw in shots:
        rig.animation_data.action = bpy.data.actions[act_name]
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        target = Vector((0, 0, -0.05 if act_name != 'fly' else 0.0))
        y = math.radians(yaw); dist = 3.4 if act_name == 'fly' else 2.4
        el = math.radians(12 if act_name != 'fly' else 35)
        cam.location = target + Vector((math.sin(y) * math.cos(el), math.cos(y) * math.cos(el), math.sin(el))) * dist
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = os.path.join(PREV_DIR, '%s_%d_%d.png' % (act_name, frame, yaw))
        bpy.ops.render.render(write_still=True)
    rig.animation_data.action = None


def export(rig, meshes):
    os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
    activate(rig)
    for m in meshes:
        m.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=OUT_GLB, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
        export_texcoords=True, export_normals=True, export_tangents=False, export_materials='EXPORT',
        export_image_format='JPEG', export_jpeg_quality=88, export_skins=True, export_all_influences=False,
        export_def_bones=False, export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
        export_optimize_animation_size=True, export_frame_range=False, export_anim_single_armature=True,
        export_frame_step=2, export_morph=False, export_lights=False, export_cameras=False, export_extras=False)
    log('exported %s (%.0f KB)' % (OUT_GLB, os.path.getsize(OUT_GLB) / 1024))


def build():
    global RF, ORDER
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hi = load_source()
    hi.name = 'SakiHi'
    body = load_low(hi)
    J = joints_from_picks(hi)
    J, floor = normalize(hi, J, others=(body,))
    # the back surface behind the shoulder blades, for the wing roots
    co = np.array([v.co for v in body.data.vertices])
    c = J['neck0'] + (J['hips'] - J['neck0']) * 0.22
    band = co[(np.abs(co[:, 0]) < 0.06) & (np.abs(co[:, 2] - c[2]) < 0.03)]
    J['back_y'] = band[:, 1].min()
    # ankles: centre of the leg section; the ball of the foot 60 % of the way to the toe tip (feet are not parallel)
    for sx in ('.L', '.R'):
        a = J['ankle' + sx]
        leg = co[(np.abs(co[:, 0] - a[0]) < 0.035) & (np.abs(co[:, 2] - a[2]) < 0.008)]
        a[1] = 0.5 * (leg[:, 1].min() + leg[:, 1].max())
        foot = co[(np.abs(co[:, 0] - a[0]) < 0.09) & (np.abs(co[:, 1] - a[1]) < 0.2) & (co[:, 2] < floor + 0.05)]
        toe = foot[np.argmax(foot[:, 1])]                                                  # frontmost
        J['ball' + sx] = np.array([a[0] + 0.6 * (toe[0] - a[0]), a[1] + 0.6 * (toe[1] - a[1]), floor + 0.025])
        log('ankle%s %s toe %s' % (sx, np.round(a, 3), np.round(toe, 3)))
    tidy_material(body)
    rebake(body, hi)
    T = body_table(J, floor)
    ORDER = list(BODY_BONES)
    if WINGS:
        W = wing_rest(J)
        for sx in ('.L', '.R'):
            for b in wing_names(sx):
                T[b] = W[b][:3]
                ORDER.append(b)
    rig = make_armature(T, ORDER)
    RF = rest_frames(T)
    # skin the body to the body bones only (automatic weights), the wings by construction
    if WINGS:
        for b in rig.data.bones:
            b.use_deform = b.name in BODY_BONES and b.name != 'root'
    else:
        rig.data.bones['root'].use_deform = False
    skin(body, rig)
    for b in rig.data.bones:
        b.use_deform = b.name != 'root'
    meshes = [body]
    if WINGS:
        meshes.append(make_wings(W, rig))
    bake_action(rig, 'fly', pose_fly, 2.0)
    if WINGS:
        bake_action(rig, 'flyhand', pose_flyhand, 2.0)
    bake_action(rig, 'sit', pose_sit, 3.0)
    bake_action(rig, 'stand', pose_stand, 3.0)
    bake_action(rig, 'walk', pose_walk, WALK_T)
    bake_action(rig, 'run', pose_run, RUN_T)
    return rig, meshes, floor


if __name__ == '__main__':
    rig, meshes, floor = build()
    export(rig, meshes)
    if '--no-previews' not in ARGS:
        previews(rig, floor)
    log('done')
