"""Ground decals: flat polygons draped exactly on the game terrain (+0.04 m).

The terrain is planar inside each half cell of the 10 m grid (split along x + y = const), so cutting a decal along
x = 10k, y = 10k and x + y = 10k makes every piece planar on the ground: no floating, no sinking.
"""
import bpy, bmesh, math
from mathutils import Vector
import common as C
import uvmap as U

OFF = 0.04


class Decals:
    def __init__(self):
        self.items = []      # (ring [(x,y)], cell, offset)

    def poly(self, ring, cell, off=OFF):
        if len(ring) >= 3: self.items.append(([tuple(p[:2]) for p in ring], cell, off))

    def disc(self, cx, cy, r, cell, n=14, rng=None, off=OFF, squash=1.0, rot=0.0):
        pts = []
        for k in range(n):
            a = 2 * math.pi * k / n
            rr = r * (1 + (rng.uniform(-0.25, 0.2) if rng else 0))
            x, y = math.cos(a) * rr, math.sin(a) * rr * squash
            pts.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
        self.poly(pts, cell, off)

    def strip(self, pts, w, cell, off=OFF):
        """a band of width w along a polyline"""
        L, R = [], []
        for i, p in enumerate(pts):
            p = Vector(p[:2])
            a = Vector(pts[max(i - 1, 0)][:2]); b = Vector(pts[min(i + 1, len(pts) - 1)][:2])
            d = (b - a).normalized(); n = Vector((-d.y, d.x))
            L.append(p + n * w / 2); R.append(p - n * w / 2)
        self.poly([tuple(v) for v in L] + [tuple(v) for v in R[::-1]], cell, off)

    def build(self, name, mat, col):
        bm = bmesh.new()
        lay = bm.faces.layers.int.new('cell')
        offl = bm.faces.layers.float.new('off')
        for ring, cell, off in self.items:
            vs = [bm.verts.new((x, y, 0)) for x, y in ring]
            try:
                f = bm.faces.new(vs)
            except ValueError:
                continue
            if f.normal.z < 0: f.normal_flip()
            f[lay] = cell; f[offl] = off
        bm.normal_update()
        xs = [v.co.x for v in bm.verts]; ys = [v.co.y for v in bm.verts]
        if not xs:
            bm.free(); return None
        def cut(no, lo, hi, step=10.0):
            for k in range(math.floor(lo / step), math.ceil(hi / step) + 1):
                geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
                bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector(no).normalized() * (k * step / Vector(no).length), plane_no=Vector(no).normalized(), dist=1e-4)
        cut((1, 0, 0), min(xs), max(xs)); cut((0, 1, 0), min(ys), max(ys))
        cut((1, 1, 0), min(xs) + min(ys), max(xs) + max(ys))
        # drape: vertices shared by faces with different offsets take the largest (decals never sink)
        vo = {}
        for f in bm.faces:
            for v in f.verts: vo[v.index] = max(vo.get(v.index, 0), f[offl])
        bm.verts.index_update()
        for f in bm.faces:
            for v in f.verts: vo[v.index] = max(vo.get(v.index, 0), f[offl])
        for v in bm.verts:
            v.co.z = C.ground(v.co.x, v.co.y) + vo.get(v.index, OFF)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me); col.objects.link(ob)
        U.cut_and_map(ob, U.DECAL_CELLS)
        for p in me.polygons: p.use_smooth = False
        return ob
