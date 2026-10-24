"""Stage 'scene': build all near geometry into work/scene.blend.

Collections: NEAR (exported), REF (context + ground, for baking and previews only).
"""
import math
import random
import time
import sys

import bpy
import numpy as np

from sb_common import *
import sb_geom as G
import sb_bldg
import sb_plan
import sb_mats
from sb_mesh import MB


class Footprints:
    """1 m raster of building footprints (ground-floor sections) for quick inside tests."""

    def __init__(self, sections, x0=-200, y0=-170, x1=200, y1=170, res=1.0):
        self.x0, self.y0, self.res = x0, y0, res
        nx = int((x1 - x0) / res); ny = int((y1 - y0) / res)
        xs = x0 + (np.arange(nx) + 0.5) * res
        ys = y0 + (np.arange(ny) + 0.5) * res
        X, Y = np.meshgrid(xs, ys, indexing='ij')
        P = np.stack([X.ravel(), Y.ravel()], 1)
        m = np.zeros(len(P), bool)
        for S in sections:
            allp = np.concatenate([np.array(r) for r, _h in S])
            bx0, by0 = allp.min(0) - 1; bx1, by1 = allp.max(0) + 1
            sel = (P[:, 0] > bx0) & (P[:, 0] < bx1) & (P[:, 1] > by0) & (P[:, 1] < by1)
            if sel.any():
                m[sel] |= G.in_section(P[sel], S)
        self.m = m.reshape(nx, ny)

    def __call__(self, x, y):
        i = int((x - self.x0) / self.res); j = int((y - self.y0) / self.res)
        if 0 <= i < self.m.shape[0] and 0 <= j < self.m.shape[1]:
            return bool(self.m[i, j])
        return False

    def dist_free(self, x, y, r):
        """True if no building within r metres"""
        for dx in (-r, 0, r):
            for dy in (-r, 0, r):
                if self(x + dx, y + dy):
                    return False
        return True


XING_C = (78.0, -52.0)
ROOTS = []


def _bronze():
    import sb_hachiko
    return sb_mats.make('bronze')


def place_trees(trees, bldgs, fp, ground, osm, rnd):
    from sb_plan import intensity
    placed = []
    def ok(x, y, r):
        return all((x - px) ** 2 + (y - py) ** 2 > r * r for px, py in placed)
    # OSM street trees (Jingu-dori), now huge
    for (x, y) in osm['trees']:
        if -150 < x < 150 and -120 < y < 120 and fp.dist_free(x, y, 1.5):
            trees.place('big', x, y, ground(x, y), rnd.uniform(0, 6.28), rnd.uniform(0.85, 1.1))
            placed.append((x, y))
    # Hachiko square: a fig grown beside the statue, and a couple of big trees
    for (k, x, y, s) in (('fig', 99.5, -108.5, 0.75), ('big', 71.0, -97.0, 0.9), ('mid', 79.0, -108.0, 1.0), ('big', 104.0, -88.0, 0.85)):
        trees.place(k, x, y, ground(x, y), rnd.uniform(0, 6.28), s)
        placed.append((x, y))
    # trees grown out of the asphalt: not on the open crossing
    tries = 0
    n = 0
    while n < 75 and tries < 6000:
        tries += 1
        x = rnd.uniform(-150, 150); y = rnd.uniform(-120, 120)
        if math.hypot(x - XING_C[0], y - XING_C[1]) < 30:
            continue
        if not fp.dist_free(x, y, 2.5) or not ok(x, y, 9.0):
            continue
        I = intensity(x, y)
        k = rnd.choices(['big', 'mid', 'young'], [0.25 + 0.3 * I, 0.45, 0.3])[0]
        if k == 'big' and not fp.dist_free(x, y, 4.0):
            k = 'mid'
        trees.place(k, x, y, ground(x, y), rnd.uniform(0, 6.28), rnd.uniform(0.8, 1.15))
        placed.append((x, y)); n += 1
    # trees on roofs and broken slabs
    cand = []
    for b in bldgs.values():
        for (x, y, z, top) in b.exposed:
            cand.append((x, y, z, b))
    # strangler figs: a tree on a roof edge with its roots pouring down the facade to the street
    edges = []
    for b in bldgs.values():
        h = b.z1 - b.z0
        for (a, c, z, nrm) in b.roof_edges:
            L = math.hypot(c[0] - a[0], c[1] - a[1])
            if L > 2.5 and z - b.z0 < 34 and z - b.z0 > 6:
                m = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
                if intensity(*m) > 0.35 and not fp(m[0] + nrm[0] * 3, m[1] + nrm[1] * 3):
                    edges.append((b, a, c, z, nrm))
    rnd.shuffle(edges)
    figs = []
    for (b, a, c, z, nrm) in edges:
        if len(figs) >= 24:
            break
        m = ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2)
        if any((m[0] - fx) ** 2 + (m[1] - fy) ** 2 < 400 for fx, fy in figs):
            continue
        figs.append(m)
        tx, ty = m[0] - nrm[0] * 1.8, m[1] - nrm[1] * 1.8
        trees.place(rnd.choice(['roof', 'mid']), tx, ty, z - 0.1, rnd.uniform(0, 6.28), rnd.uniform(0.75, 1.0))
        ROOTS.append((a, c, z, b.z0, nrm))
    rnd.shuffle(cand)
    nroof = 0
    rp = []
    for (x, y, z, b) in cand:
        if nroof >= 95:
            break
        if any((x - px) ** 2 + (y - py) ** 2 < 49 for px, py in rp):
            continue
        I = intensity(x, y)
        if rnd.random() > 0.35 + 0.6 * I:
            continue
        k = rnd.choices(['roof', 'young', 'mid'], [0.5, 0.35, 0.15])[0]
        trees.place(k, x, y, z - 0.1, rnd.uniform(0, 6.28), rnd.uniform(0.7, 1.1))
        rp.append((x, y)); nroof += 1


def place_plants(vmb, bldgs, fp, ground, rnd):
    import sb_veg
    from sb_plan import intensity
    # roofs and broken slabs
    for b in bldgs.values():
        for (x, y, z, top) in b.exposed:
            if rnd.random() < 0.10 + 0.12 * intensity(x, y):
                sb_veg.plant_tuft(vmb, x + rnd.uniform(-0.7, 0.7), y + rnd.uniform(-0.7, 0.7), z, rnd)
        # ivy hanging from the tops of walls
        for (a, c, z, nrm) in b.roof_edges:
            if rnd.random() < 0.32 + 0.4 * intensity(a[0], a[1]):
                L = rnd.uniform(4.0, 22.0)
                sb_veg.ivy_curtain(vmb, a, c, z + 0.9, L, nrm, rnd, zmin=b.z0)
    # strangler roots below the edge figs
    for (a, c, z, z0, nrm) in ROOTS:
        sb_veg.strangler_roots(vmb, a, c, z + 0.4, z0, nrm, rnd, n=rnd.randint(3, 7), rmax=rnd.uniform(0.2, 0.4), ground=ground)
        sb_veg.ivy_curtain(vmb, a, c, z + 0.9, rnd.uniform(6, 14), nrm, rnd, zmin=z0)
    # plants growing on and through the abandoned cars
    import sb_place
    for (x, y, z) in sb_place.CAR_TOPS:
        if rnd.random() < 0.4:
            sb_veg.plant_tuft(vmb, x, y, z - 0.25, rnd, size=(0.9, 1.6))
    # plants on the rubble heaps
    import sb_props
    for (x, y, z) in sb_props.HEAP_PTS:
        if rnd.random() < 0.06:
            sb_veg.plant_tuft(vmb, x, y, z - 0.1, rnd, size=(0.8, 1.7))
    # street edge: tufts along the building bases
    for k in range(2500):
        x = rnd.uniform(-152, 152); y = rnd.uniform(-122, 122)
        if fp(x, y) or fp.dist_free(x, y, 1.2):
            continue
        if math.hypot(x - XING_C[0], y - XING_C[1]) < 22 and rnd.random() < 0.7:
            continue
        sb_veg.plant_tuft(vmb, x, y, ground(x, y), rnd, size=(0.7, 1.5))


def write_collide(path, bldgs, collide, collide_tris, trees):
    """collision proxy: building top surfaces, rubble surfaces, prop boxes, tree trunk prisms"""
    from mathutils.geometry import tessellate_polygon
    from mathutils import Vector
    V = []; F = []
    def tri(a, b, c):
        i = len(V); V.extend([a, b, c]); F.append((i + 1, i + 2, i + 3))
    # closed ground floors: every footprint filled at the first-floor ceiling (no seams down to the street)
    for b in bldgs.values():
        if not b.sections or b.name == 'b000':     # b000: the rubble ramp climbs into its collapsed bite
            continue
        z = b.floors[0][1]
        for ring, hole in b.sections[0]:
            if hole:
                continue
            pts = [Vector((p[0], p[1], 0)) for p in ring]
            try:
                tt = tessellate_polygon([pts])
            except Exception:
                continue
            for t in tt:
                tri(*[(ring[i][0], ring[i][1], z) for i in t])
    for b in bldgs.values():
        for ring, z in b.top_surfaces:
            pts = [Vector((p[0], p[1], 0)) for p in ring]
            try:
                tt = tessellate_polygon([pts])
            except Exception:
                continue
            for t in tt:
                tri(*[(ring[i][0], ring[i][1], z) for i in t])
    for pts in collide_tris:
        tri(pts[0], pts[1], pts[2]); tri(pts[0], pts[2], pts[3])
    def boxc(xf, e):
        x0, x1, y0, y1, z0, z1 = e
        c = [xf((x, y, z)) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        for f in faces:
            tri(c[f[0]], c[f[1]], c[f[2]]); tri(c[f[0]], c[f[2]], c[f[3]])
    for kind, xf, e in collide:
        boxc(xf, e)
    import sb_props as Pr
    for (kind, x, y, z, s) in getattr(trees, 'placed', []):
        r = {'big': 0.6, 'fig': 0.9, 'mid': 0.4, 'young': 0.3, 'roof': 0.3}[kind] * max(1.0, s)
        boxc(Pr.X(x, y, z), (-r, r, -r, r, -0.3, 3.0))
    with open(path, 'w') as f:
        f.write('# TOKYO 2090 shibuya hero collision proxy (local frame, x east, y north, z up)\no collide\n')
        for v in V:
            f.write(f'v {v[0]:.3f} {v[1]:.3f} {v[2]:.3f}\n')
        for t in F:
            f.write(f'f {t[0]} {t[1]} {t[2]}\n')
    print(f'collide: {len(F)} tris')
    return len(F)


def build(only=None):
    t0 = time.time()
    clear_scene()
    ground = Ground()
    B = read_obj(os.path.join(SRC, 'buildings.obj'))
    info = {b['obj']: b for b in load_json('buildings.json')['buildings']}
    osm = load_json('osm.json')
    near = coll('NEAR')
    ref = coll('REF')
    rnd = random.Random(2090)

    mb = MB()
    bldgs = {}
    for n, (V, F) in B.items():
        if only and n not in only:
            continue
        style, ruin, kw = sb_plan.plan(n, info[n], V)
        b = sb_bldg.Building(n, V, F, info[n], ground, style=style, ruin=ruin, **kw)
        b.build(mb)
        bldgs[n] = b
    print(f'buildings: {mb.ntris()} tris, {time.time() - t0:.1f}s')
    fp = Footprints([b.sections[0] for b in bldgs.values() if b.sections])

    import sb_street
    dmb = MB()
    sb_street.build_decals(dmb, ground, osm, fp, rnd)
    # moss and grass carpets on roofs and broken slabs
    from sb_plan import intensity
    for b in bldgs.values():
        for ring, z in b.top_surfaces:
            c = np.mean(np.array(ring), axis=0)
            if rnd.random() < 0.55 + 0.4 * intensity(c[0], c[1]):
                g = rnd.uniform(0.8, 1.1)
                dmb.poly_flat(ring, z + 0.03, 'decal_moss', lambda p: (p[0] / 4.0, p[1] / 4.0), col=(g, g, g * 0.95, 1))
    print(f'decals: {dmb.ntris()} tris')

    # ---- props and rubble
    import sb_place
    pmb = MB()
    collide = []          # ('box', xform, extents)
    collide_tris = []     # rubble surfaces
    sb_place.place(pmb, bldgs, fp, ground, osm, rnd, collide)
    sb_place.rubble(pmb, bldgs, fp, ground, rnd, collide_tris)
    import sb_land
    sb_land.build(pmb, ground, rnd, collide, bldgs)
    print(f'props+rubble: {pmb.ntris()} tris')
    mb.extend(pmb)

    # ---- Hachiko (bakes tex/bronze.png first)
    hj = sb_land.hachiko(near, None, ground, rnd, collide)

    # ---- vegetation
    import sb_veg
    vmb = MB()
    for k in ('bark', 'foliage_leaves'):
        sb_mats.make(k)
    vm = {'bark': sb_mats.make('bark'), 'foliage_leaves': sb_mats.make('foliage_leaves')}
    trees = sb_veg.Trees(near, vm)
    place_trees(trees, bldgs, fp, ground, osm, rnd)
    place_plants(vmb, bldgs, fp, ground, rnd)
    print(f'trees: {trees.count} ~{trees.tris} tris; plants {vmb.ntris()} tris')

    mats = {}
    def mat(k):
        if k not in mats:
            mats[k] = sb_mats.make(k)
        return mats[k]
    for k in set(mb.M) | set(dmb.M) | set(vmb.M):
        mat(k)
    pobjs = vmb.to_objects('foliage_plants', near, mats, merge=False)
    if 'bark' in pobjs:
        pobjs['bark'].name = 'roots_bark'
    uv1 = {k: v['orm'] for k, v in sb_mats.MATS.items() if v.get('orm')}
    objs = mb.to_objects('bld', near, mats, uv1=uv1)
    dobjs = dmb.to_objects('decal', near, mats, merge=False)
    for k, o in dobjs.items():
        o.name = f'decal_{k}'
    # reference geometry
    for o in import_obj(os.path.join(SRC, 'context.obj'), ref):
        o.name = 'ctx_' + o.name
    for o in import_obj(os.path.join(SRC, 'ground.obj'), ref):
        o.name = 'REF_ground'
    refm = bpy.data.materials.new('ref_grey')
    refm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.25, 0.25, 0.23, 1)
    gm = bpy.data.materials.new('ref_ground')
    # stand-in for the game's ground shader in previews only: cracked asphalt with moss and grass
    from sb_nodes import NB
    nb = NB(gm.node_tree)
    tc = nb.node('ShaderNodeTexCoord')
    n1 = nb.noise(tc.outputs['Object'], scale=0.08, detail=6.0, rough=0.6, w=1.0)
    n2 = nb.noise(tc.outputs['Object'], scale=0.9, detail=3.0, w=2.0)
    col = nb.mix(nb.smooth(0.45, 0.62, nb.add(n1, nb.mul(n2, 0.15))), (0.075, 0.075, 0.072), (0.05, 0.075, 0.02))
    nb.link(col, gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    for o in ref.objects:
        o.data.materials.clear()
        o.data.materials.append(gm if o.name == 'REF_ground' else refm)
    write_collide(os.path.join(OUT, 'collide.obj'), bldgs, collide, collide_tris, trees)
    game_light(); view_setup()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, 'scene.blend'))
    print(f'scene done {time.time() - t0:.1f}s')
    return bldgs


if __name__ == '__main__':
    build()
