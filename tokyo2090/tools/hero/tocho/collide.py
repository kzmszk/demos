"""collide.obj: what the walker stands on. The game rasterises it from above (highest surface wins), so we only need
tops and solid boxes: roofs, broken floors of the crown, the rubble ramp, vehicles and street furniture (boxes),
tree trunks, the deck wall parapet, stairs, plinths, fallen columns. Bridges over streets and the Assembly wings
over 都庁通り are left out, so are canopies, signs, vines and foliage.
"""
import bpy, math
from mathutils import Vector, Matrix, geometry
import common as C


def roof_tops(mb, mass, crown):
    for name, b in mass.items():
        if name.endswith('br') or name == 'b015': continue
        for r in b.get('croof', []):
            z = r['z']
            if crown and name == 'b000':
                cx = sum(p[0] for p in r['outer']) / len(r['outer']); cy = sum(p[1] for p in r['outer']) / len(r['outer'])
                if crown.region(cx, cy, z) and z > crown.hb(cx, cy) - 1.0: continue
            loops = [[Vector((x, y, z)) for x, y in r['outer']]] + [[Vector((x, y, z)) for x, y in h] for h in r['holes']]
            pts = [p for l in loops for p in l]
            idx = [mb.v(p) for p in pts]
            for t in geometry.tessellate_polygon(loops):
                a, b_, c = pts[t[0]], pts[t[1]], pts[t[2]]
                if ((b_ - a).cross(c - a)).z < 0: mb.face([idx[t[0]], idx[t[2]], idx[t[1]]])
                else: mb.face([idx[t[0]], idx[t[1]], idx[t[2]]])


def boxes(mb, items):
    """items: (matrix_world, [cx, cy, cz, sx, sy, sz])"""
    for mw, (cx, cy, cz, sx, sy, sz) in items:
        P = [mw @ Vector((cx + dx * sx / 2, cy + dy * sy / 2, cz + dz * sz / 2)) for dz in (-1, 1) for dy in (-1, 1) for dx in (-1, 1)]
        i = [mb.v(p) for p in P]
        for f in [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (1, 3, 7, 5), (3, 2, 6, 7), (2, 0, 4, 6)]:
            mb.face([i[k] for k in f])


def mesh_tops(mb, ob, min_nz=0.3):
    """copy the upward faces of an object (world space)"""
    me = ob.data; mw = ob.matrix_world
    nm = mw.to_3x3().inverted_safe().transposed()
    for p in me.polygons:
        n = (nm @ p.normal).normalized()
        if n.z < min_nz: continue
        mb.poly([mw @ me.vertices[v].co for v in p.vertices])


def trunks(mb, planter_objs):
    for o in planter_objs:
        if o.type != 'MESH' or o.get('lod') == 'mid': continue
        nm = o.data.name
        if not any(k in nm for k in ('zelkova', 'street', 'fig', 'young')): continue
        r = 0.35 if 'young' in nm else 0.6 if 'street' in nm else 0.9
        x, y, z = o.location
        ring = [(x + math.cos(a) * r, y + math.sin(a) * r) for a in [k * math.pi / 3 for k in range(6)]]
        mb.prism(ring, z, z + 3.0, top=True)


def build(mass, crown, extra_objs, prop_boxes, planter_objs):
    col = C.coll('collide')
    mb = C.MB()
    roof_tops(mb, mass, crown)
    boxes(mb, prop_boxes)
    trunks(mb, planter_objs)
    for o in extra_objs:
        mesh_tops(mb, o)
    o = mb.build('collide_main', [], col)
    return o
