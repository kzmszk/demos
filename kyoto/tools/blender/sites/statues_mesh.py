"""statues_mesh — Blender side of the statue kit: decimation (LODs), normals, palettes into a jk.Builder,
preview materials (vertex-colour tints) and EEVEE preview renders."""
import math, time
import numpy as np
import bpy

def face_labels(T, LAB):
    a, b, c = LAB[T[:, 0]], LAB[T[:, 1]], LAB[T[:, 2]]
    return np.where(b == c, b, a).astype(np.int32)

def _mesh(name, P, T, flab=None):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(P)); me.vertices.foreach_set('co', np.asarray(P, np.float32).ravel())
    me.loops.add(T.size); me.loops.foreach_set('vertex_index', T.ravel().astype(np.int32))
    me.polygons.add(len(T)); me.polygons.foreach_set('loop_start', np.arange(0, T.size, 3, dtype=np.int32))
    me.update(calc_edges=True)
    if flab is not None:
        at = me.attributes.new('lab', 'INT', 'FACE'); at.data.foreach_set('value', np.asarray(flab, np.int32))
    return me

def _read(me):
    me.calc_loop_triangles() if hasattr(me, 'calc_loop_triangles') else None
    nv = len(me.vertices); P = np.empty(nv * 3, np.float32); me.vertices.foreach_get('co', P); P = P.reshape(-1, 3)
    nt = len(me.loop_triangles); T = np.empty(nt * 3, np.int32); me.loop_triangles.foreach_get('vertices', T); T = T.reshape(-1, 3)
    pi = np.empty(nt, np.int32); me.loop_triangles.foreach_get('polygon_index', pi)
    lab = None
    if 'lab' in me.attributes:
        L = np.empty(len(me.polygons), np.int32); me.attributes['lab'].data.foreach_get('value', L); lab = L[pi]
    N = np.empty(nv * 3, np.float32); me.vertex_normals.foreach_get('vector', N); N = N.reshape(-1, 3)
    return P, T, lab, N

def decimate(P, T, flab, targets, name='dec', smooth_iters=0, vweight=None, vfactor=1.0):
    """decimate one mesh to several triangle targets (each from the full mesh) -> [(P, T, flab, N)].
    vweight: optional per-vertex weights in [0, 1]; weighted vertices are collapsed first (backs of the statues)"""
    t0 = time.time()
    me = _mesh(name, P, T, flab)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    if vweight is not None:
        vg = ob.vertex_groups.new(name='bias')
        w = np.asarray(vweight, np.float32)
        wr = np.round(w, 2)
        for val in np.unique(wr):
            idx = np.nonzero(wr == val)[0].tolist()
            if val > 0 and idx: vg.add(idx, float(val), 'REPLACE')
    out = []
    if smooth_iters:
        sm = ob.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.5; sm.iterations = smooth_iters
    for tgt in targets:
        ratio = min(1.0, tgt / max(len(T), 1))
        md = ob.modifiers.new('dec', 'DECIMATE'); md.decimate_type = 'COLLAPSE'; md.ratio = ratio; md.use_collapse_triangulate = True
        if vweight is not None: md.vertex_group = 'bias'; md.vertex_group_factor = vfactor
        dg = bpy.context.evaluated_depsgraph_get(); ev = ob.evaluated_get(dg)
        m2 = ev.to_mesh()
        out.append(_read(m2))
        ev.to_mesh_clear(); ob.modifiers.remove(md)
    bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
    return out

def vnormals(P, T):
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    N = np.zeros_like(P)
    for k in range(3): np.add.at(N, T[:, k], fn)
    l = np.linalg.norm(N, axis=1, keepdims=True); l[l == 0] = 1
    return (N / l).astype(np.float32)

TINTED = ('cloth', 'wood_natural', 'vermilion')

def add_labeled(B, P, T, flab, N, pal, xf=None, tag='main', c0fn=None, shade=None):
    """add a labelled mesh to a jk Builder: per label -> pal[label] = (mat, c0 rgba); c0fn(P, c0, shade) varies tints"""
    if xf is not None:
        R, t = xf
        P = P @ np.asarray(R, np.float32).T + np.asarray(t, np.float32); N = N @ np.asarray(R, np.float32).T
        if np.linalg.det(R) < 0: T = T[:, ::-1]
    for lb in np.unique(flab):
        sel = T[flab == lb]
        used = np.unique(sel); remap = np.full(len(P), -1, np.int64); remap[used] = np.arange(len(used))
        mat, c0 = pal[int(lb)]
        PP = P[used]
        c = c0
        if c0fn is not None and mat in TINTED:
            try: c = c0fn(PP, c0, None if shade is None else shade[used])
            except TypeError: c = c0fn(PP, c0)
        B.add(PP, remap[sel], mat, N=N[used], tag=tag, c0=c)

# ------------------------------------------------------------------------------------------------ previews
def srgb2lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def vertex_albedo(matn, C0):
    """what tools/web/statues.js shows: tinted mats albedo * c0^2 * 2.2, others the material albedo"""
    from jk.core import mats
    M = mats()
    out = np.zeros((len(matn), 3), np.float32)
    for n in set(matn):
        sel = matn == n
        al = np.asarray(M[n]['albedo'], np.float32)
        if n in TINTED: out[sel] = al * (C0[sel, :3].astype(np.float32) / 255.0) ** 2 * 2.2
        else: out[sel] = al
    return out

PREVIEW = {   # mat -> (base colour linear or None = vertex tint, metallic, roughness)
    'gold': ((0.80, 0.52, 0.18), 1.0, 0.32),
    'black_lacquer': ((0.012, 0.010, 0.009), 0.0, 0.35),
    'glass': ((0.01, 0.01, 0.012), 0.0, 0.04),
    'wood_dark': ((0.06, 0.04, 0.028), 0.0, 0.7),
    'wood_natural': ((0.30, 0.20, 0.12), 0.0, 0.7),
    'metal_dark': ((0.05, 0.05, 0.05), 0.8, 0.45),
    'bronze': ((0.12, 0.09, 0.06), 0.8, 0.45),
    'white_paint': ((0.62, 0.60, 0.55), 0.0, 0.6),
    'vermilion': ((0.50, 0.09, 0.035), 0.0, 0.6),
    'stone': ((0.30, 0.29, 0.27), 0.0, 0.85),
    'cloth': (None, 0.0, 0.9),
    'wood_natural': (None, 0.0, 0.75),
    'vermilion': (None, 0.0, 0.7),
}

def preview_materials():
    out = {}
    for name, (col, met, rough) in PREVIEW.items():
        mm = bpy.data.materials.get('pv_' + name) or bpy.data.materials.new('pv_' + name)
        mm.use_nodes = True; nt = mm.node_tree
        bs = nt.nodes.get('Principled BSDF')
        bs.inputs['Metallic'].default_value = met; bs.inputs['Roughness'].default_value = rough
        if col is None:
            at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'alb'; at.attribute_type = 'GEOMETRY'
            nt.links.new(at.outputs['Color'], bs.inputs['Base Color'])
        else:
            bs.inputs['Base Color'].default_value = (*col, 1)
        out[name] = mm
    return out

def to_object(b, name, collection=None, loc=(0, 0, 0)):
    """a jk.Builder -> one Blender object with preview materials and the c0 tint as a colour attribute"""
    pm = preview_materials()
    M = b.merged(('main', 'detail'))
    P, I = M['P'], M['I']
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(P)); me.vertices.foreach_set('co', P.ravel())
    me.loops.add(I.size); me.loops.foreach_set('vertex_index', I.ravel().astype(np.int32))
    me.polygons.add(len(I)); me.polygons.foreach_set('loop_start', np.arange(0, I.size, 3, dtype=np.int32))
    me.update(calc_edges=True)
    names = sorted(set(M['MATN']))
    for n in names:
        if n not in pm:
            mm = bpy.data.materials.get('pv_' + n) or bpy.data.materials.new('pv_' + n); pm[n] = mm
        me.materials.append(pm[n])
    midx = {n: k for k, n in enumerate(names)}
    me.polygons.foreach_set('material_index', np.array([midx[n] for n in M['MATN'][I[:, 0]]], np.int32))
    me.polygons.foreach_set('use_smooth', np.ones(len(I), bool))
    me.normals_split_custom_set(M['N'][I.ravel()].tolist())
    ca = me.color_attributes.new('alb', 'FLOAT_COLOR', 'POINT')
    lin = vertex_albedo(M['MATN'], M['C0'])
    ca.data.foreach_set('color', np.concatenate([lin, np.ones((len(lin), 1))], 1).astype(np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    ob.location = loc
    return ob

def setup_render(res=(900, 1200), samples=48, exposure=0.0):
    sc = bpy.context.scene
    names = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    sc.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in names else 'BLENDER_EEVEE_NEXT'
    sc.render.resolution_x, sc.render.resolution_y = res
    try: sc.eevee.taa_render_samples = samples
    except Exception: pass
    try:
        sc.eevee.use_shadows = True
    except Exception: pass
    try: sc.eevee.use_raytracing = True
    except Exception: pass
    w = bpy.data.worlds.get('pvw') or bpy.data.worlds.new('pvw'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.012, 0.010, 0.009, 1); bg.inputs['Strength'].default_value = 1.0
    try: sc.view_settings.view_transform = 'AgX'
    except Exception: pass
    sc.view_settings.exposure = exposure

def lights(center=(0, 0, 1), dist=3.0, power=1.0, side=1):
    """warm key from one side (area light), a dim cool fill from the other, a faint rim"""
    for o in [o for o in bpy.data.objects if o.name.startswith('pvL')]: bpy.data.objects.remove(o)
    from mathutils import Vector
    c = Vector(center)
    def area(name, pos, energy, col, size):
        ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.color = col; ld.size = size
        lo = bpy.data.objects.new(name, ld); bpy.context.scene.collection.objects.link(lo)
        lo.location = pos; lo.rotation_euler = (c - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
        return lo
    area('pvL_key', c + Vector((side * dist * 0.9, dist * 0.8, dist * 0.35)), 420 * power * dist * dist / 9, (1.0, 0.72, 0.45), dist * 0.5)
    area('pvL_fill', c + Vector((-side * dist, dist * 0.6, -dist * 0.1)), 40 * power * dist * dist / 9, (0.75, 0.8, 1.0), dist * 0.8)
    area('pvL_rim', c + Vector((-side * dist * 0.4, -dist, dist * 0.6)), 120 * power * dist * dist / 9, (1.0, 0.8, 0.6), dist * 0.3)

def camera(cam, tgt, lens=50, path=None):
    from mathutils import Vector
    sc = bpy.context.scene
    cd = bpy.data.cameras.get('pvcam') or bpy.data.cameras.new('pvcam'); cd.lens = lens; cd.clip_start = 0.02; cd.clip_end = 500
    co = bpy.data.objects.get('pvcam') or bpy.data.objects.new('pvcam', cd)
    if co.name not in sc.collection.objects: sc.collection.objects.link(co)
    sc.camera = co; co.location = cam; co.rotation_euler = (Vector(tgt) - Vector(cam)).to_track_quat('-Z', 'Y').to_euler()
    if path:
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)

def refine_labels(P, T, N, field, h=0.002, iters=6):
    """crisp material borders: label every vertex from the field, find the border point on every mixed edge by
    bisection on the label function, and split the mixed triangles there -> (P, T, N, face labels)"""
    P = np.asarray(P, np.float32); N = np.asarray(N, np.float32); T = np.asarray(T, np.int64)
    Lv = field.labels_at(P, h).astype(np.int32)
    la, lb, lc = Lv[T[:, 0]], Lv[T[:, 1]], Lv[T[:, 2]]
    mixed = ~((la == lb) & (lb == lc))
    flab = np.where(lb == lc, lb, la)
    if not mixed.any(): return P, T.astype(np.int32), N, Lv[T[:, 0]]
    Tm = T[mixed]
    # unique mixed edges
    E = np.concatenate([Tm[:, [0, 1]], Tm[:, [1, 2]], Tm[:, [2, 0]]])
    E = E[Lv[E[:, 0]] != Lv[E[:, 1]]]
    E = np.sort(E, 1); E = np.unique(E, axis=0)
    a = P[E[:, 0]]; b = P[E[:, 1]]; la_ = Lv[E[:, 0]]
    lo = np.zeros(len(E), np.float32); hi = np.ones(len(E), np.float32)
    for _ in range(iters):
        m = (lo + hi) / 2
        lm = field.labels_at(a + (b - a) * m[:, None], h)
        same = lm == la_
        lo = np.where(same, m, lo); hi = np.where(same, hi, m)
    t = ((lo + hi) / 2)[:, None]
    newP = a + (b - a) * t
    newN = N[E[:, 0]] * (1 - t) + N[E[:, 1]] * t; newN /= np.maximum(np.linalg.norm(newN, axis=1, keepdims=True), 1e-9)
    base = len(P)
    key = {(int(e0), int(e1)): base + i for i, (e0, e1) in enumerate(E)}
    def ev(u, v):
        return key.get((u, v) if u < v else (v, u))
    out_T = [T[~mixed]]; out_L = [flab[~mixed]]
    extra_T = []; extra_L = []
    # centroid vertices for 3-label triangles
    cP = []; cN = []
    for tri in Tm:
        i0, i1, i2 = int(tri[0]), int(tri[1]), int(tri[2])
        l0, l1, l2 = Lv[i0], Lv[i1], Lv[i2]
        if l0 != l1 and l1 != l2 and l0 != l2:
            x, y, z = ev(i0, i1), ev(i1, i2), ev(i2, i0)
            ci = base + len(E) + len(cP)
            cP.append((P[i0] + P[i1] + P[i2]) / 3); cn = N[i0] + N[i1] + N[i2]; cN.append(cn / max(np.linalg.norm(cn), 1e-9))
            extra_T += [(i0, x, ci), (i0, ci, z), (x, i1, ci), (i1, y, ci), (y, i2, ci), (i2, z, ci)]
            extra_L += [l0, l0, l1, l1, l2, l2]
            continue
        # one odd vertex
        if l1 == l2: o, p, q = i0, i1, i2
        elif l0 == l2: o, p, q = i1, i2, i0
        else: o, p, q = i2, i0, i1
        x, y = ev(o, p), ev(o, q)
        extra_T += [(o, x, y), (x, p, q), (x, q, y)]
        extra_L += [Lv[o], Lv[p], Lv[p]]
    P2 = np.concatenate([P, newP.astype(np.float32)] + ([np.array(cP, np.float32)] if cP else []))
    N2 = np.concatenate([N, newN.astype(np.float32)] + ([np.array(cN, np.float32)] if cN else []))
    T2 = np.concatenate(out_T + [np.array(extra_T, np.int64)]).astype(np.int32)
    L2 = np.concatenate(out_L + [np.array(extra_L, np.int32)])
    return P2, T2, N2, L2

def npz_mesh(path, name):
    """an exported statue npz -> Blender mesh (preview materials, c0 colour attribute)"""
    import jk
    from jk.core import mats
    D = np.load(path)
    P, N, I, C0, MAT = D['P'], D['N'], D['I'].astype(np.int64), D['C0'], D['MAT']
    id2name = {m['id']: n for n, m in mats().items()}
    pm = preview_materials()
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(P)); me.vertices.foreach_set('co', P.ravel())
    me.loops.add(I.size); me.loops.foreach_set('vertex_index', I.ravel().astype(np.int32))
    me.polygons.add(len(I)); me.polygons.foreach_set('loop_start', np.arange(0, I.size, 3, dtype=np.int32))
    me.update(calc_edges=True)
    fm = MAT[I[:, 0]]; ids = sorted(set(fm.tolist()))
    for k in ids:
        n = id2name[k]
        if n not in pm:
            mm = bpy.data.materials.get('pv_' + n) or bpy.data.materials.new('pv_' + n); pm[n] = mm
        me.materials.append(pm[n])
    lut = {k: j for j, k in enumerate(ids)}
    me.polygons.foreach_set('material_index', np.array([lut[k] for k in fm], np.int32))
    me.polygons.foreach_set('use_smooth', np.ones(len(I), bool))
    me.normals_split_custom_set(N[I.ravel()].tolist())
    ca = me.color_attributes.new('alb', 'FLOAT_COLOR', 'POINT')
    lin = vertex_albedo(np.array([id2name[k] for k in MAT]), C0)
    ca.data.foreach_set('color', np.concatenate([lin, np.ones((len(lin), 1))], 1).astype(np.float32).ravel())
    return me
