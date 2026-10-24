"""The buildings: PLATEAU massing rebuilt as clean 2.5D shells, the Tange grid on the towers, the broken north crown.

Each building yields up to two objects: <id>_fac (FACADE atlas) and <id>_mat (MAT atlas).
"""
import bpy, bmesh, math, random
import numpy as np
from mathutils import Vector, Matrix, geometry
import common as C
import uvmap as U
import materials as M

MC = U.MC
TOWERS = ('b000', 'b001')
ASSEMBLY = ('b002', 'b003', 'b004', 'b005', 'b006', 'b003br', 'b006br')


def ring_area(r):
    return 0.5 * sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1] for i in range(len(r)))


def principal_angle(rings):
    s = c = 0.0
    for r in rings:
        for i in range(len(r)):
            dx = r[(i + 1) % len(r)][0] - r[i][0]; dy = r[(i + 1) % len(r)][1] - r[i][1]
            L = math.hypot(dx, dy); a = math.atan2(dy, dx)
            s += L * math.sin(4 * a); c += L * math.cos(4 * a)
    return math.atan2(s, c) / 4


def tess(outer, holes, z):
    loops = [[Vector((x, y, z)) for x, y in outer]] + [[Vector((x, y, z)) for x, y in h] for h in holes]
    pts = [p for l in loops for p in l]
    tris = geometry.tessellate_polygon(loops)
    return pts, tris


def roof_poly(mb, pr, z, mat, cell, up=True):
    pts, tris = tess(pr['outer'], pr['holes'], z)
    idx = [mb.v(p) for p in pts]
    for t in tris:
        a, b, c = (idx[t[0]], idx[t[1]], idx[t[2]])
        # make it face up
        pa, pb, pc = Vector(pts[t[0]]), Vector(pts[t[1]]), Vector(pts[t[2]])
        n = (pb - pa).cross(pc - pa)
        if (n.z > 0) != up: a, b = b, a
        mb.face([a, b, c], mat, cell)


def zone_split(a, b, L, kind):
    """split a wall edge into (t0, t1, cell) pieces: the Tange facade has a window-band centre and pier-zone sides"""
    if kind == 'tower' and L >= 22:
        return [(0, 0.3, 0), (0.3, 0.7, 1), (0.7, 1.0, 0)]
    if kind == 'tower' and L >= 12:
        return [(0, 1, 1)] if L < 16 else [(0, 0.25, 0), (0.25, 0.75, 1), (0.75, 1, 0)]
    return [(0, 1, 0)]


PLAZA_C = Vector((31.0, 71.0, 0)); PLAZA_R = 57.0


def is_arc(a, b):
    m = (a + b) / 2
    for p in (a, b, m):
        if abs((p - PLAZA_C).xy.length - PLAZA_R) > 4.5: return False
    n = Vector(((b - a).y, -(b - a).x, 0)).normalized()
    return n.dot((PLAZA_C - m).normalized()) > 0.6


FALLEN = []


def qf(mb, pts, want, cell):
    """quad/poly oriented to face 'want'"""
    pts = [Vector(p) for p in pts]
    n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
    if n.dot(Vector(want)) < 0: pts = pts[::-1]
    mb.poly(pts, 0, cell)


def recess(mat, a, b, n, zb, zt, depth, spacing, pw, back, a2=None, b2=None, caps=True, col_cell=None, col_w=None, fall=0.0):
    """ground-floor depth: the wall line a-b becomes a row of piers in front of a recessed back wall"""
    a2 = a - n * depth if a2 is None else a2
    b2 = b - n * depth if b2 is None else b2
    qf(mat, [(a2.x, a2.y, zb), (b2.x, b2.y, zb), (b2.x, b2.y, zt), (a2.x, a2.y, zt)], n, back)
    # soffit (faces down)
    qf(mat, [(a.x, a.y, zt), (b.x, b.y, zt), (b2.x, b2.y, zt), (a2.x, a2.y, zt)], (0, 0, -1), MC['concrete'])
    if caps:
        t_ = (b - a).normalized()
        qf(mat, [(a2.x, a2.y, zb), (a2.x, a2.y, zt), (a.x, a.y, zt), (a.x, a.y, zb)], t_, MC['granite'])
        qf(mat, [(b.x, b.y, zb), (b.x, b.y, zt), (b2.x, b2.y, zt), (b2.x, b2.y, zb)], -t_, MC['granite'])
    L = (b - a).length
    k = max(1, round(L / spacing))
    t = (b - a).normalized()
    cw = col_w or pw
    for i in range(k):
        f = (i + 0.5) / k
        p = a.lerp(b, f) - n * (cw / 2 + 0.02)
        if fall and hnoise(41, round(p.x, 1), round(p.y, 1)) < fall:
            FALLEN.append((p.copy(), math.atan2(n.y, n.x) + (hnoise(42, round(p.x, 1)) - 0.5) * 1.2, zt - zb))
            continue
        ang = math.atan2(t.y, t.x)
        mat.box((p.x, p.y, (zb + zt) / 2), (pw, cw, zt - zb), ang, 0, col_cell or MC['granite'], bottom=False)


def shell(name, data, kind, crown=None):
    """walls + roofs of one building. returns (mb_fac, mb_mat)"""
    fac, mat = C.MB(), C.MB()
    z0 = data['z0']
    floating = name.endswith('br') or name == 'b015'
    for bi, band in enumerate(data['bands']):
        za, zb = band['z0'], band['z1']
        for pr in band['polys']:
            for r in [pr['outer']] + pr['holes']:
                n = len(r)
                for i in range(n):
                    a = Vector(r[i] + [0]); b = Vector(r[(i + 1) % n] + [0])
                    L = (b - a).length
                    if L < 0.05: continue
                    nrm = Vector(((b - a).y, -(b - a).x, 0)).normalized()
                    if crown is not None:
                        mid = (a + b) / 2
                        if crown.region(mid.x, mid.y, za) and za > crown.hb(mid.x, mid.y) - 1: continue
                    lo = za
                    if bi == 0 and not floating:
                        g = min(C.ground(a.x, a.y), C.ground(b.x, b.y), C.ground((a.x + b.x) / 2, (a.y + b.y) / 2))
                        if kind == 'tower' and L > 5 and g + 8.6 < zb:
                            recess(mat, a, b, nrm, g - 0.5, g + 8.4, 1.6, 3.2, 0.9, MC['glazing'])
                            lo = g + 8.4
                        elif kind == 'assembly' and is_arc(a, b) and g + 10 < zb:
                            a2 = a + (a - PLAZA_C).xy.to_3d().normalized() * 5.0; a2.z = 0
                            b2 = b + (b - PLAZA_C).xy.to_3d().normalized() * 5.0; b2.z = 0
                            zt = za + 9.6
                            recess(mat, a, b, nrm, min(g, za) - 0.5, zt, 5.0, 6.4, 1.25, MC['glazing'], a2, b2, caps=False, col_w=1.25, fall=0.1)
                            lo = zt
                    if kind == 'tower' and zb - lo > 2.5:
                        for t0, t1, cell in zone_split(a, b, L, kind):
                            p, q = a.lerp(b, t0), a.lerp(b, t1)
                            fac.quad((p.x, p.y, lo), (q.x, q.y, lo), (q.x, q.y, zb), (p.x, p.y, zb), 0, cell)
                    else:
                        cell = MC['assembly'] if kind == 'assembly' and zb - za > 6 else (MC['granite'] if kind != 'small' else MC['concrete'])
                        mat.quad((a.x, a.y, lo), (b.x, b.y, lo), (b.x, b.y, zb), (a.x, a.y, zb), 0, cell)
            if bi == 0 and (floating or z0 > C.ground(*pr['outer'][0]) + 3):      # floating (bridges): underside
                roof_poly(mat, pr, za, 0, MC['concrete'], up=False)
        for pr in band.get('roof', []):
            if crown is not None:
                cx_, cy_ = np.mean(pr['outer'], axis=0)
                if crown.region(cx_, cy_, zb) and zb > crown.hb(cx_, cy_) - 1.0: continue
            roof_poly(mat, pr, zb, 0, MC['roof'])
    return fac, mat


# ------------------------------------------------------------------------------------------- north crown break
class Frame:
    def __init__(self, ang, cx, cy):
        self.ang = ang; self.c = Vector((cx, cy)); self.ca = math.cos(ang); self.sa = math.sin(ang)

    def loc(self, x, y):
        dx, dy = x - self.c.x, y - self.c.y
        return self.ca * dx + self.sa * dy, -self.sa * dx + self.ca * dy

    def world(self, a, b):
        return self.c.x + self.ca * a - self.sa * b, self.c.y + self.sa * a + self.ca * b


def hnoise(seed, *k):
    return random.Random(hash((seed,) + tuple(k)) & 0xffffffff).random()


def bisect_faces(bm, faces, axis, step, lo, hi):
    """cut the given faces (and only them) along planes axis.p = k*step"""
    fset = set(faces)
    for k in range(math.floor(lo / step) + 1, math.ceil(hi / step)):
        fs = [f for f in bm.faces if f in fset or f.tag]
        geom = list(set(e for f in fs for e in f.edges)) + fs + list(set(v for f in fs for v in f.verts))
        r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=axis * (k * step), plane_no=axis, dist=1e-4)
        for f in bm.faces:
            pass
        fset = set(f for f in bm.faces if f.tag or f in fset)
    return fset


class Crown:
    """the broken north tower: everything above a jagged break surface is gone"""

    def __init__(self, fr):
        self.fr = fr

    def region(self, x, y, z):
        a, b = self.fr.loc(x, y)
        return b > 8.5 and z > 187.5      # north tower (building frame b axis points north-ish)

    def hb(self, x, y):
        """break height (absolute z) over the north tower plan"""
        a, b = self.fr.loc(x, y)
        # high at the south-west (next to the south tower), low at the north-east
        s = ((-a) * 0.55 + (-(b - 32)) * 0.45) / 30.0          # ~ -1 .. 1
        h = 241 + 15 * s
        # bay / floor stepped jaggedness
        ka, kb = math.floor(a / 3.2), math.floor(b / 3.2)
        h += (hnoise(7, ka, kb) - 0.5) * 9 + (hnoise(8, ka // 3, kb // 3) - 0.5) * 10
        return h


def break_crown(ob_fac, crown, mb_mat):
    """delete facade above the break; emit torn wall thickness + inner shell into mb_mat"""
    me = ob_fac.data
    bm = bmesh.new(); bm.from_mesh(me)
    cell = bm.faces.layers.int.get('cell')
    fr = crown.fr
    ax_a = Vector((fr.ca, fr.sa, 0)); ax_b = Vector((-fr.sa, fr.ca, 0)); ax_z = Vector((0, 0, 1))
    def sel():
        out = []
        for f in bm.faces:
            c = f.calc_center_median()
            if crown.region(c.x, c.y, c.z) or any(crown.region(v.co.x, v.co.y, v.co.z) for v in f.verts):
                if max(v.co.z for v in f.verts) > 205: out.append(f)
        return out
    # fine cut 3.2 m bays along both building axes, 4 m floors
    for axis, step in ((ax_a, 3.2), (ax_b, 3.2), (ax_z, 4.0)):
        fs = sel()
        if not fs: continue
        o = fr.c.x * axis.x + fr.c.y * axis.y if axis.z == 0 else 0.0
        vals = [v.co.dot(axis) - o for f in fs for v in f.verts]
        for k in range(math.floor(min(vals) / step) + 1, math.ceil(max(vals) / step)):
            fs = sel()
            geom = list(set(e for f in fs for e in f.edges)) + fs + list(set(v for f in fs for v in f.verts))
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=axis * (k * step + o), plane_no=axis, dist=1e-4)
    dead = []
    for f in bm.faces:
        c = f.calc_center_median()
        if crown.region(c.x, c.y, c.z) and c.z > crown.hb(c.x, c.y):
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    # torn edges: boundary edges of the remaining wall in the region
    torn = []
    for e in bm.edges:
        if len(e.link_faces) == 1:
            c = (e.verts[0].co + e.verts[1].co) / 2
            if crown.region(c.x, c.y, c.z) and c.z > 200:
                f = e.link_faces[0]
                torn.append((e.verts[0].co.copy(), e.verts[1].co.copy(), f.normal.copy(), f))
    # inner shell of the remaining walls near the break
    inner = []
    for f in bm.faces:
        c = f.calc_center_median()
        if crown.region(c.x, c.y, c.z) and abs(f.normal.z) < 0.2 and c.z > crown.hb(c.x, c.y) - 20:
            inner.append(([v.co.copy() for v in f.verts], f.normal.copy()))
    dissolve_cuts(bm)
    bm.to_mesh(me); bm.free(); me.update()
    T = 0.45
    for a, b, n, f in torn:
        mb_mat.quad(a, b, b - n * T, a - n * T, 0, MC['broken'])
    for vs, n in inner:
        mb_mat.poly([v - n * T for v in vs][::-1], 0, MC['interior'])


def crown_structure(crown, data, mb_mat, mb_cut):
    """exposed slabs, steel columns and beams, the core, hanging panels"""
    fr = crown.fr
    R = random.Random(11)
    # tower footprint per floor height: band polygons of b000 whose z-range contains z
    def footprint(z):
        out = []
        for band in data['bands']:
            if band['z0'] <= z < band['z1']:
                for pr in band['polys']:
                    a, b = fr.loc(*np.mean(pr['outer'], axis=0))
                    if b > 8.5: out.append(pr)
        return out
    def inside(pr, x, y):
        def pin(r):
            c = False; n = len(r)
            for i in range(n):
                x1, y1 = r[i]; x2, y2 = r[(i + 1) % n]
                if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1: c = not c
            return c
        return pin(pr['outer']) and not any(pin(h) for h in pr['holes'])
    S = 2.0
    for zf in range(192, 272, 4):
        zf = float(zf)
        prs = footprint(zf + 0.5)
        if not prs: continue
        cells = set()
        allpts = [fr.loc(x, y) for pr in prs for x, y in pr['outer']]
        a0 = min(p[0] for p in allpts); a1 = max(p[0] for p in allpts); b0 = min(p[1] for p in allpts); b1 = max(p[1] for p in allpts)
        for i in range(int((a1 - a0) / S) + 1):
            for j in range(int((b1 - b0) / S) + 1):
                a, b = a0 + (i + 0.5) * S, b0 + (j + 0.5) * S
                x, y = fr.world(a, b)
                cs = [fr.world(a + da, b + db) for da in (-S / 2, S / 2) for db in (-S / 2, S / 2)]
                if not any(all(inside(pr, *c) for c in cs) for pr in prs): continue
                h = crown.hb(x, y)
                jit = (hnoise(3, i, j, int(zf)) - 0.5) * 5
                if zf + 0.4 < h + jit and zf > h - 13:
                    cells.add((i, j))
        if not cells: continue
        # merged slab outline via a temporary bmesh
        bm = bmesh.new()
        vmap = {}
        def V(i, j):
            if (i, j) not in vmap:
                x, y = fr.world(a0 + i * S, b0 + j * S); vmap[(i, j)] = bm.verts.new((x, y, zf))
            return vmap[(i, j)]
        for (i, j) in cells:
            bm.faces.new([V(i, j), V(i + 1, j), V(i + 1, j + 1), V(i, j + 1)])
        inner_e = [e for e in bm.edges if len(e.link_faces) == 2]
        bmesh.ops.dissolve_edges(bm, edges=inner_e, use_verts=True)
        # ragged edge: jitter boundary verts that are not on the facade line
        for v in bm.verts:
            if any(len(e.link_faces) == 1 for e in v.link_edges):
                v.co.x += (R.random() - 0.5) * 1.4; v.co.y += (R.random() - 0.5) * 1.4
                v.co.z += -R.random() * 0.5
        for f in bm.faces:
            if f.normal.z < 0: f.normal_flip()
        th = 0.45
        for f in bm.faces:
            vs = [v.co.copy() for v in f.verts]
            pts, tris = vs, geometry.tessellate_polygon([vs])
            idx = [mb_mat.v(p) for p in vs]; idb = [mb_mat.v(p - Vector((0, 0, th))) for p in vs]
            for t in tris:
                mb_mat.face([idx[t[0]], idx[t[1]], idx[t[2]]], 0, MC['roof'])
                mb_mat.face([idb[t[2]], idb[t[1]], idb[t[0]]], 0, MC['interior'])
            for e in f.edges:
                if len(e.link_faces) == 1:
                    i0 = vs.index(e.verts[0].co) if e.verts[0].co in vs else None
                    a, b = e.verts[0].co, e.verts[1].co
                    # order so the side faces outwards (loop direction)
                    for l in f.loops:
                        if l.edge == e:
                            a, b = l.vert.co, l.link_loop_next.vert.co
                    mb_mat.quad(b.copy(), a.copy(), a - Vector((0, 0, th)), b - Vector((0, 0, th)), 0, MC['broken'])
        bm.free()
    # steel: perimeter columns at 3.2 m along the torn top, interior columns on a 9.6 m grid
    prs = footprint(230)
    for pr in prs:
        r = pr['outer']; n = len(r)
        for i in range(n):
            a = Vector(r[i]); b = Vector(r[(i + 1) % n]); L = (b - a).length
            for k in range(int(L / 3.2)):
                p = a.lerp(b, (k + 0.5) * 3.2 / L)
                h = crown.hb(p.x, p.y)
                if R.random() < 0.55:
                    top = h + R.uniform(0.5, 7.5)
                    column(mb_mat, p, h - 4, top, R, bend=R.random() < 0.35)
    # interior columns
    for i in range(-3, 4):
        for j in range(-3, 4):
            a, b = i * 9.6, 32 + j * 9.6
            x, y = fr.world(a, b)
            if not any(inside(pr, x, y) for pr in prs): continue
            h = crown.hb(x, y)
            column(mb_mat, Vector((x, y)), h - 8, h + R.uniform(-1, 9), R, w=0.8, bend=R.random() < 0.3)
    # the concrete core standing proud
    ca, cb = -4.0, 34.0
    cx, cy = fr.world(ca, cb)
    hc = max(crown.hb(cx, cy) + 7, 250)
    core = [fr.world(ca + da, cb + db) for da, db in ((-6, -5), (6, -5), (6, 5), (-6, 5))]
    mb_mat.prism(core, 200, hc - 3, 0, MC['concrete'], top=False)
    # ragged core top: stepped
    for k, (da, db, dh) in enumerate(((-6, -5, 3), (0, -5, 1), (-6, 0, 0), (0, 0, -1.5))):
        rr = [fr.world(ca + da + u, cb + db + w) for u, w in ((0, 0), (6, 0), (6, 5), (0, 5))]
        mb_mat.prism(rr, hc - 3, hc + dh, 0, MC['concrete'], top=True)


def column(mb, p, z0, z1, R, w=0.55, bend=False):
    if bend:
        zm = z0 + (z1 - z0) * R.uniform(0.4, 0.7)
        ang = R.uniform(0, 2 * math.pi); off = Vector((math.cos(ang), math.sin(ang), 0)) * R.uniform(1.0, 3.0)
        seg(mb, Vector((p.x, p.y, z0)), Vector((p.x, p.y, zm)), w)
        seg(mb, Vector((p.x, p.y, zm)), Vector((p.x, p.y, zm)) + off + Vector((0, 0, (z1 - zm) * 0.6)), w * 0.9)
    else:
        seg(mb, Vector((p.x, p.y, z0)), Vector((p.x, p.y, z1)), w)


def seg(mb, a, b, w, cell=None):
    """square-section beam from a to b (H-steel stand-in)"""
    d = (b - a)
    if d.length < 1e-4: return
    d.normalize()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    s = d.cross(up).normalized() * w / 2; t = d.cross(s).normalized() * w / 2
    P = [a + s + t, a - s + t, a - s - t, a + s - t]; Q = [b + s + t, b - s + t, b - s - t, b + s - t]
    c = MC['rust'] if cell is None else cell
    for i in range(4):
        j = (i + 1) % 4
        mb.quad(P[j], P[i], Q[i], Q[j], 0, c)
    mb.poly(Q, 0, c)


def dissolve_cuts(bm):
    """merge the coplanar pieces left by temporary fine cuts (keeping facade zones apart)"""
    lay = bm.faces.layers.int.get('cell')
    for f in bm.faces: f.material_index = f[lay]
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.2), verts=bm.verts, edges=bm.edges, delimit={'NORMAL', 'MATERIAL'})
    for f in bm.faces: f.material_index = 0


# ------------------------------------------------------------------------------------------- holes in the facades
def punch_holes(ob_fac, mb_mat, fr, regions, depth=7.0):
    """regions: list of (bbox (x0,y0,z0,x1,y1,z1), inside(x, y, z, n) -> bool). Facade bays inside are torn out: a dark
    back wall, the floor slab edges (mossy tops) and the torn panel edges show the depth of the building."""
    me = ob_fac.data
    bm = bmesh.new(); bm.from_mesh(me)
    ax_a = Vector((fr.ca, fr.sa, 0)); ax_b = Vector((-fr.sa, fr.ca, 0)); ax_z = Vector((0, 0, 1))
    def near(f):
        c = f.calc_center_median()
        for (x0, y0, z0, x1, y1, z1), _ in regions:
            if x0 <= c.x <= x1 and y0 <= c.y <= y1 and z0 - 4 <= max(v.co.z for v in f.verts) and min(v.co.z for v in f.verts) <= z1 + 4:
                return True
        return False
    for axis, step in ((ax_a, 3.2), (ax_b, 3.2), (ax_z, 4.0)):
        o = fr.c.x * axis.x + fr.c.y * axis.y if axis.z == 0 else 0.0
        fs = [f for f in bm.faces if near(f) and abs(f.normal.z) < 0.3]
        if not fs: continue
        vals = [v.co.dot(axis) - o for f in fs for v in f.verts]
        for k in range(math.floor(min(vals) / step) + 1, math.ceil(max(vals) / step)):
            fs = [f for f in bm.faces if near(f) and abs(f.normal.z) < 0.3]
            geom = list(set(e for f in fs for e in f.edges)) + fs + list(set(v for f in fs for v in f.verts))
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=axis * (k * step + o), plane_no=axis, dist=1e-4)
    dead = []
    for f in bm.faces:
        if abs(f.normal.z) > 0.3: continue
        c = f.calc_center_median()
        for _, inside in regions:
            if inside(c.x, c.y, c.z, f.normal):
                dead.append(f); break
    holes = [([v.co.copy() for v in f.verts], f.normal.copy()) for f in dead]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    dissolve_cuts(bm)
    bm.to_mesh(me); bm.free(); me.update()
    R = random.Random(len(holes))
    for vs, n in holes:
        zs = [v.z for v in vs]; z0 = min(zs); z1 = max(zs)
        bot = [v for v in vs if v.z < z0 + 0.05]; top = [v for v in vs if v.z > z1 - 0.05]
        if len(bot) < 2 or len(top) < 2: continue
        bot.sort(key=lambda v: v.dot(Vector((-n.y, n.x, 0)))); top.sort(key=lambda v: v.dot(Vector((-n.y, n.x, 0))))
        a, b = bot[0], bot[-1]; d = depth * R.uniform(0.6, 1.0)
        A2, B2 = a - n * d, b - n * d
        t_ = (b - a).normalized()
        # back wall (dark interior)
        qf(mb_mat, [A2, B2, Vector((B2.x, B2.y, z1)), Vector((A2.x, A2.y, z1))], n, MC['interior'])
        # floor slab: top (mossy) and its torn front edge
        sl = 0.45
        qf(mb_mat, [a, b, B2, A2], (0, 0, 1), MC['roof'])
        qf(mb_mat, [a - Vector((0, 0, sl)), b - Vector((0, 0, sl)), b, a], n, MC['broken'])
        # ceiling
        ta, tb = Vector((a.x, a.y, z1 - sl)), Vector((b.x, b.y, z1 - sl))
        qf(mb_mat, [tb, ta, ta - n * d, tb - n * d], (0, 0, -1), MC['interior'])
        # side walls (every bay: reads as the cross walls / columns)
        qf(mb_mat, [Vector((a.x, a.y, z1)), A2 + Vector((0, 0, z1 - z0)), A2, a], t_, MC['interior'])
        qf(mb_mat, [b, B2, B2 + Vector((0, 0, z1 - z0)), Vector((b.x, b.y, z1))], -t_, MC['interior'])


# ------------------------------------------------------------------------------------------- facade variants
def facade_variant(crown):
    def var(cen, c, ku, kv, t):
        if c > 1: return c
        r = hnoise(21, ku, kv, round(t.x, 2), round(t.y, 2))
        p = 0.22
        if crown.region(cen.x, cen.y, cen.z + 30): p = 0.65
        if cen.z < 60: p = 0.5
        return c + 2 if r < p else c
    return var


def build(col):
    data = C.massing()
    mats = M.all_mats()
    objs = {}
    b0 = data['b000']
    ang = principal_angle([pr['outer'] for band in b0['bands'] for pr in band['polys']])
    # tower frame: 'b' axis along the long (north-south-ish) side
    cx, cy = -38.0, 58.0
    fr = Frame(ang if abs(ang) < math.pi / 4 else ang - math.pi / 2, cx, cy)
    a_, b_ = fr.loc(-40, 100)
    if b_ < 0:
        fr = Frame(fr.ang + math.pi, cx, cy)
    print('tower frame angle', math.degrees(fr.ang))
    crown = Crown(fr)
    for name, d in data.items():
        kind = 'tower' if name in TOWERS else 'assembly' if name in ASSEMBLY else 'small'
        fac, mat = shell(name, d, kind, crown if name == 'b000' else None)
        cut = C.MB()
        if fac.F:
            of = fac.build(name + '_fac', [mats['facade']], col)
            if name == 'b000':
                break_crown(of, crown, mat)
                crown_structure(crown, d, mat, cut)
                ax_a = Vector((fr.ca, fr.sa, 0)); ax_b = Vector((-fr.sa, fr.ca, 0))
                def ragged(d, w, *k):
                    """inside a band of half-width w at distance d: solid core, ragged rim, a few stray bays"""
                    r = hnoise(*k)
                    return d < w * 0.45 or (d < w and r < 0.6) or (d < w * 1.6 and r < 0.12)
                def crack_s(x, y, z, n):
                    a, b = fr.loc(x, y)
                    if b > -8 or not 192 < z < 256: return False
                    w = 3.0 + (hnoise(51, int(z / 4)) - 0.5) * 2.0
                    k = (61, int(a / 3.2), int(b / 3.2), int(z / 4))
                    if n.dot(ax_a) > 0.6: return ragged(abs(b - (-30 + (z - 222) * 0.32 + 2 * math.sin(z * 0.15))), w, *k)
                    if n.dot(-ax_b) > 0.6: return ragged(abs(a - (-4 - (z - 222) * 0.25)), w * 0.8, *k)
                    return False
                def gouge_n(x, y, z, n):
                    a, b = fr.loc(x, y)
                    if n.dot(ax_b) < 0.6 or b < 20 or z > 186: return False
                    bot = 146 + 10 * math.sin(a * 0.3)
                    if z < bot - 12: return False
                    return ragged(max(abs(a + 4) / 1.3, (bot - z) * 1.2 if z < bot else 0), 13, 62, int(a / 3.2), int(z / 4))
                def holes_w(x, y, z, n):
                    a, b = fr.loc(x, y)
                    if n.dot(-ax_a) < 0.6: return False
                    k = (63, int(b / 3.2), int(z / 4))
                    return ragged(math.hypot((b - 10) / 1.3, (z - 72) / 1.6), 8, *k) or ragged(math.hypot(b + 30, (z - 128) / 1.5), 5, *k)
                punch_holes(of, mat, fr, [((-80, -10, 190, 0, 60, 260), crack_s), ((-80, 60, 130, 0, 130, 190), gouge_n),
                                          ((-80, -20, 55, -40, 80, 140), holes_w)])
            if name in ('b000', 'b001'):
                for band in d['bands']:
                    if band['z1'] - band['z0'] < 6: continue
                    for pr in band['polys']:
                        ring = pr['outer']
                        cx_, cy_ = np.mean(ring, axis=0)
                        rr = [(cx_ + (x - cx_) * 0.72, cy_ + (y - cy_) * 0.72) for x, y in ring]
                        if ring_area(rr) < 0: rr = rr[::-1]
                        top = band['z1'] - 0.5
                        if name == 'b000' and crown.region(cx_, cy_, top): top = min(top, crown.hb(cx_, cy_) - 6)
                        if top > band['z0'] + 1:
                            mat.prism(rr, band['z0'], top, 0, MC['interior'], top=False)
            if name == 'b001':
                def holes_2(x, y, z, n):
                    if n.x < 0.5: return False
                    return (150 < z < 176 and -100 < y < -82 and hnoise(55, int(z / 4), int(y / 3.2)) < 0.75) or (90 < z < 110 and -140 < y < -128)
                punch_holes(of, mat, fr, [((-40, -160, 85, 30, -50, 180), holes_2)])
            U.cut_and_map(of, U.FACADE_CELLS, variant=facade_variant(crown))
            objs[of.name] = of
        if mat.F:
            om = mat.build(name + '_mat', [mats['mat']], col)
            U.cut_and_map(om, U.MAT_CELLS)
            objs[om.name] = om
    return objs, crown
