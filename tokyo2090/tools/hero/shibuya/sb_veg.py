"""Vegetation: instanced tree templates (trunk + crown), ivy curtains on facades, strangler roots, roof and
street plants."""
import math
import random

import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion

from sb_mesh import MB
from sb_tex_misc import fol_uv, FOL


# ------------------------------------------------------------------ tubes
def tube(mb, pts, radii, mat='bark', sides=7, col=(1, 1, 1, 1), uscale=2.0, vscale=2.0, cap=False):
    """swept tube along pts (n,3) with radii (n): parallel-transport frames; UV for the tiled bark."""
    P = [Vector(p) for p in pts]
    n = len(P)
    if n < 2:
        return
    T = []
    for i in range(n):
        a = P[max(0, i - 1)]; b = P[min(n - 1, i + 1)]
        t = (b - a)
        T.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N0 = T[0].cross(up).normalized()
    frames = []
    N = N0
    for i in range(n):
        if i > 0:
            ax = T[i - 1].cross(T[i])
            if ax.length > 1e-8:
                ang = T[i - 1].angle(T[i])
                N = Quaternion(ax.normalized(), ang) @ N
        B = T[i].cross(N).normalized()
        N = B.cross(T[i]).normalized()
        frames.append((N, B))
    rings = []
    for i in range(n):
        Nn, Bb = frames[i]
        r = radii[i]
        rings.append([P[i] + (Nn * math.cos(2 * math.pi * k / sides) + Bb * math.sin(2 * math.pi * k / sides)) * r for k in range(sides + 1)])
    # cumulative length for v
    L = [0.0]
    for i in range(1, n):
        L.append(L[-1] + (P[i] - P[i - 1]).length)
    circ = max(1, round(2 * math.pi * max(radii) / uscale))
    for i in range(n - 1):
        for k in range(sides):
            a = rings[i][k]; b = rings[i][k + 1]; c = rings[i + 1][k + 1]; d = rings[i + 1][k]
            u0 = k / sides * circ; u1 = (k + 1) / sides * circ
            v0 = L[i] / vscale; v1 = L[i + 1] / vscale
            mb.face([a, b, c, d], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], mat, col)


def curve(p0, d0, length, steps, rnd, bend=0.08, gravity=0.0, upward=0.0):
    pts = [Vector(p0)]
    d = Vector(d0).normalized()
    seg = length / steps
    for i in range(steps):
        d = (d + Vector((rnd.gauss(0, bend), rnd.gauss(0, bend), rnd.gauss(0, bend) * 0.5 - gravity + upward))).normalized()
        pts.append(pts[-1] + d * seg)
    return pts


# ------------------------------------------------------------------ tree templates
KINDS = {
    #        height  crown_r trunk_r branches clusters cells                       card size
    'big':   (16.0, 8.0, 0.50, 8, 120, ('leafA', 'leafB', 'leafA'), (3.4, 4.6)),
    'mid':   (10.0, 5.0, 0.30, 7, 70, ('leafC', 'leafB'), (2.6, 3.4)),
    'young': (5.0, 2.6, 0.13, 5, 26, ('leafD', 'leafC'), (1.8, 2.4)),
    'roof':  (6.5, 3.4, 0.20, 6, 40, ('leafE', 'leafD'), (2.2, 3.0)),
    'fig':   (13.0, 7.5, 0.70, 8, 110, ('leafF', 'leafD', 'leafF'), (3.2, 4.4)),
}


def card(mb, c, nrm, size, cell, rnd, col, rot=None, crown_c=None, normal_blend=0.65):
    """square leaf card centred at c, facing nrm, using foliage cell"""
    n = Vector(nrm).normalized()
    t = n.cross(Vector((0, 0, 1)))
    if t.length < 1e-3:
        t = Vector((1, 0, 0))
    t.normalize()
    b = n.cross(t).normalized()
    ang = rot if rot is not None else rnd.uniform(0, 2 * math.pi)
    t2 = t * math.cos(ang) + b * math.sin(ang)
    b2 = n.cross(t2).normalized()
    h = size / 2
    P = [c - t2 * h - b2 * h, c + t2 * h - b2 * h, c + t2 * h + b2 * h, c - t2 * h + b2 * h]
    uv = [fol_uv(cell, 0, 0), fol_uv(cell, 1, 0), fol_uv(cell, 1, 1), fol_uv(cell, 0, 1)]
    mb.face(P, uv, 'foliage_leaves', col)
    if crown_c is not None:
        # custom normals: spherical around the crown centre, blended with the card normal
        ns = []
        for p in P:
            s = (p - crown_c); s.z *= 0.8
            s = s.normalized() if s.length > 1e-6 else n
            ns.append((s * normal_blend + Vector((0, 0, 1)) * 0.25 + n * (1 - normal_blend) * 0.3).normalized())
        mb.N = getattr(mb, 'N', {})
        mb.N[len(mb.F) - 1] = ns


def tree_template(kind, seed=1):
    rnd = random.Random(seed)
    H, CR, TR, NB, NC, cells, csz = KINDS[kind]
    trunk = MB(); crown = MB()
    lean = Vector((rnd.gauss(0, 0.12), rnd.gauss(0, 0.12), 1)).normalized()
    if kind == 'roof':
        lean = Vector((rnd.choice((-1, 1)) * 0.35, rnd.gauss(0, 0.2), 1)).normalized()
    tl = H * 0.62
    stems = 1 if kind != 'fig' else 4
    tips = []
    for sidx in range(stems):
        base = Vector((rnd.gauss(0, 0.25), rnd.gauss(0, 0.25), -0.3)) if stems > 1 else Vector((0, 0, -0.4))
        tp = curve(base, lean, tl, 6, rnd, bend=0.07)
        rr = [TR * (1.0 - 0.55 * i / 6) * (0.6 if stems > 1 else 1.0) for i in range(7)]
        rr[0] *= 1.5
        tube(trunk, tp, rr, sides=7 if kind in ('big', 'fig') else 5)
        # primary branches
        for bi in range(NB if sidx == 0 else NB // 3):
            t = rnd.uniform(0.45, 0.95)
            i = int(t * 6)
            p0 = tp[i]
            a = rnd.uniform(0, 2 * math.pi)
            d = Vector((math.cos(a), math.sin(a), rnd.uniform(0.35, 1.1)))
            L = CR * rnd.uniform(0.75, 1.15)
            bp = curve(p0, d, L, 3, rnd, bend=0.12, gravity=0.04)
            r0 = rr[i] * 0.55
            tube(trunk, bp, [r0 * (1 - 0.8 * k / 3) + 0.015 for k in range(4)], sides=4 if kind in ('big', 'fig') else 3)
            tips.append(bp[-1]); tips.append(bp[2])
            # secondary
            for si in range(1):
                q0 = bp[rnd.randint(1, 2)]
                sd = (d + Vector((rnd.gauss(0, 0.6), rnd.gauss(0, 0.6), 0.4))).normalized()
                sp = curve(q0, sd, L * 0.45, 2, rnd, bend=0.15)
                tube(trunk, sp, [r0 * 0.45 * (1 - 0.7 * k / 2) + 0.01 for k in range(3)], sides=3)
                tips.append(sp[-1])
        tips.append(tp[-1])
    # buttress roots spreading on the ground (grown out of asphalt)
    if kind in ('big', 'fig', 'mid'):
        for k in range(5 if kind != 'mid' else 3):
            a = 2 * math.pi * k / 5 + rnd.gauss(0, 0.3)
            d = Vector((math.cos(a), math.sin(a), -0.35))
            rp = curve(Vector((0, 0, 0.8)), d, TR * 5 + rnd.uniform(0, 1.5), 3, rnd, bend=0.1, gravity=0.06)
            tube(trunk, rp, [TR * 0.5 * (1 - 0.8 * j / 3) + 0.03 for j in range(4)], sides=4)
    # crown
    cc = Vector((0, 0, H - CR * 0.75)) + lean * 0.0
    cc = tips[-1] * 0.0 + Vector((sum(t.x for t in tips) / len(tips), sum(t.y for t in tips) / len(tips), H - CR * 0.7))
    tint = rnd.uniform(0.9, 1.08)
    for k in range(NC):
        if k < len(tips) and rnd.random() < 0.8:
            c = tips[k] + Vector((rnd.gauss(0, 0.4), rnd.gauss(0, 0.4), rnd.gauss(0.3, 0.3)))
        else:
            # fill the crown ellipsoid (upper part denser)
            while True:
                v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.6, 1)))
                if v.length < 1:
                    break
            c = cc + Vector((v.x * CR, v.y * CR, v.z * CR * 0.6))
        sz = rnd.uniform(*csz)
        out = (c - cc)
        nrm = Vector((out.x * 0.35 + rnd.gauss(0, 0.25), out.y * 0.35 + rnd.gauss(0, 0.25), 1.0))
        g = tint * rnd.uniform(0.85, 1.1)
        col = (g * rnd.uniform(0.95, 1.05), g, g * rnd.uniform(0.85, 1.0), 1)
        cell = rnd.choice(cells)
        card(crown, c, nrm, sz, cell, rnd, col, crown_c=cc)
        if rnd.random() < 0.45:   # a crossing vertical card for volume from the side
            vn = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0.15))
            card(crown, c, vn, sz * 0.85, cell, rnd, col, crown_c=cc)
    # hanging aerial roots for the fig
    if kind == 'fig':
        for k in range(10):
            a = rnd.uniform(0, 2 * math.pi); rr_ = rnd.uniform(1.5, CR * 0.8)
            top = cc + Vector((math.cos(a) * rr_, math.sin(a) * rr_, -CR * 0.2))
            hh = rnd.uniform(3.0, top.z - 0.5)
            n = Vector((math.cos(a), math.sin(a), 0))
            t = Vector((-n.y, n.x, 0))
            w = rnd.uniform(1.0, 2.0)
            P = [top - t * w / 2 + Vector((0, 0, -hh)), top + t * w / 2 + Vector((0, 0, -hh)), top + t * w / 2, top - t * w / 2]
            crown.face(P, [fol_uv('roots', 0, 0), fol_uv('roots', 1, 0), fol_uv('roots', 1, 1), fol_uv('roots', 0, 1)],
                       'foliage_leaves', (0.9, 0.85, 0.8, 1))
    return trunk, crown


def mb_to_mesh(mb, name, mats, key=None):
    """single-material MB -> mesh datablock (with custom normals if set)"""
    objs = mb.to_objects(name, bpy.context.scene.collection, mats, merge=False)
    ob = list(objs.values())[0]
    me = ob.data
    Nd = getattr(mb, 'N', None)
    if Nd:
        loops = []
        for fi, f in enumerate(mb.F):
            ns = Nd.get(fi)
            if ns is None:
                loops += [(0, 0, 1)] * len(f)
            else:
                loops += [tuple(n) for n in ns]
        try:
            me.normals_split_custom_set(loops)
        except Exception as e:
            print('custom normals failed', e)
    bpy.context.scene.collection.objects.unlink(ob)
    bpy.data.objects.remove(ob)
    me.name = name
    return me


class Trees:
    """Instanced trees: one Empty per template part; children are linked duplicates."""

    def __init__(self, collection, mats, seeds=None):
        self.coll = collection
        self.mats = mats
        self.meshes = {}
        self.empties = {}
        self.count = {}
        self.tris = 0
        for kind in KINDS:
            tr, cr = tree_template(kind, seed=(seeds or {}).get(kind, hash(kind) % 1000))
            self.meshes[kind] = (mb_to_mesh(tr, f'treeT_{kind}', mats), mb_to_mesh(cr, f'treeC_{kind}', mats))
            self.tris_per = getattr(self, 'tris_per', {})
            self.tris_per[kind] = tr.ntris() + cr.ntris()
            for part, nm in ((0, f'bark_{kind}'), (1, f'foliage_{kind}')):
                e = bpy.data.objects.new(nm, None)
                collection.objects.link(e)
                self.empties[(kind, part)] = e

    def place(self, kind, x, y, z, rot=0.0, scale=1.0, tilt=(0.0, 0.0)):
        for part in (0, 1):
            me = self.meshes[kind][part]
            ob = bpy.data.objects.new(f'{me.name}.{self.count.get(kind, 0)}', me)
            self.coll.objects.link(ob)
            ob.parent = self.empties[(kind, part)]
            ob.location = (x, y, z)
            ob.rotation_euler = (tilt[0], tilt[1], rot)
            ob.scale = (scale, scale, scale)
        self.count[kind] = self.count.get(kind, 0) + 1
        self.tris += self.tris_per[kind]
        self.placed = getattr(self, 'placed', [])
        self.placed.append((kind, x, y, z, scale))


# ------------------------------------------------------------------ ivy curtains, roots, plants
def ivy_curtain(mb, a, b, ztop, length, nrm, rnd, off=0.18, col=(1, 1, 1, 1), zmin=None):
    """a hanging ivy card along the wall segment a-b from ztop downward"""
    a = Vector((a[0], a[1], 0)); b = Vector((b[0], b[1], 0))
    n = Vector((nrm[0], nrm[1], 0)).normalized()
    w = (b - a).length
    if w < 0.5:
        return
    L = length
    if zmin is not None:
        L = min(L, ztop - zmin - 0.2)
    if L < 1.0:
        return
    cell = rnd.choice(('ivy1', 'ivy2'))
    # cell is 2 m x 4 m; stretch in pieces of <= 6 m length to keep the leaf scale
    pieces = max(1, int(math.ceil(L / 6.0)))
    pl = L / pieces
    for p in range(pieces):
        z1 = ztop - p * pl; z0 = z1 - pl
        o = n * (off + 0.04 * p)
        P = [a + o + Vector((0, 0, z0)), b + o + Vector((0, 0, z0)), b + o + Vector((0, 0, z1)), a + o + Vector((0, 0, z1))]
        if p == 0:
            v0, v1 = 0.0, 1.0
        else:
            v0, v1 = 0.0, 0.62      # lower pieces reuse the denser upper part of the cell
        mb.face(P, [fol_uv(cell, 0, v0), fol_uv(cell, 1, v0), fol_uv(cell, 1, v1), fol_uv(cell, 0, v1)], 'foliage_leaves', col)


def plant_tuft(mb, x, y, z, rnd, cells=('grass1', 'grass2', 'fern', 'taro'), size=(0.8, 1.6), col=(1, 1, 1, 1), up_cards=True):
    cell = rnd.choice(cells)
    s = rnd.uniform(*size)
    c = Vector((x, y, z))
    if cell in ('grass1', 'grass2'):
        # crossed vertical cards, bottom on the ground
        a0 = rnd.uniform(0, math.pi)
        for k in range(2):
            a = a0 + k * math.pi / 2
            t = Vector((math.cos(a), math.sin(a), 0)) * s / 2
            P = [c - t, c + t, c + t + Vector((0, 0, s)), c - t + Vector((0, 0, s))]
            mb.face(P, [fol_uv(cell, 0, 0), fol_uv(cell, 1, 0), fol_uv(cell, 1, 1), fol_uv(cell, 0, 1)], 'foliage_leaves', col)
    else:
        # low radial plant: a horizontal card slightly raised plus a tilted one
        for k in range(2):
            nrm = Vector((rnd.gauss(0, 0.3), rnd.gauss(0, 0.3), 1.0))
            card(mb, c + Vector((0, 0, 0.15 + 0.15 * k)), nrm, s * (1.0 - 0.2 * k), cell, rnd, col)


def strangler_roots(mb, a, b, ztop, zbot, nrm, rnd, n=5, rmax=0.32, ground=None):
    """strangler-fig roots pouring down a wall from its top edge (a-b) to the ground"""
    a = Vector((a[0], a[1], 0)); b = Vector((b[0], b[1], 0))
    t = (b - a); L = t.length
    if L < 1.0:
        return
    t.normalize()
    nv = Vector((nrm[0], nrm[1], 0)).normalized()
    for k in range(n):
        s = rnd.uniform(0.1, 0.9) * L
        r0 = rmax * rnd.uniform(0.5, 1.0)
        p = a + t * s
        z = ztop + 0.3
        pts = []; rr = []
        lat = 0.0
        # over the parapet, then down the wall
        pts.append(Vector((p.x, p.y, z)) - nv * 0.6); rr.append(r0 * 1.2)
        steps = max(4, int((ztop - zbot) / 1.6))
        for i in range(steps + 1):
            f = i / steps
            lat += rnd.gauss(0, 0.35)
            lat = max(-L * 0.4, min(L * 0.4, lat))
            zz = ztop - (ztop - zbot) * f
            q = a + t * max(0.0, min(L, s + lat))
            off = rr[-1] + 0.05
            pts.append(Vector((q.x, q.y, zz)) + nv * off)
            rr.append(max(0.06, r0 * (1 - 0.45 * f)))
        if ground is not None:
            end = pts[-1] + nv * rnd.uniform(0.8, 2.0)
            pts.append(Vector((end.x, end.y, ground(end.x, end.y) - 0.1))); rr.append(rr[-1] * 1.2)
        tube(mb, pts, rr, mat='bark', sides=5)
        # a side branch
        if rnd.random() < 0.6 and len(pts) > 4:
            j = rnd.randint(2, len(pts) - 3)
            q0 = pts[j]
            br = [q0]
            for i in range(4):
                br.append(br[-1] + t * rnd.choice((-1, 1)) * rnd.uniform(0.5, 1.2) + Vector((0, 0, -rnd.uniform(0.8, 1.6))))
            tube(mb, br, [rr[j] * 0.6 * (1 - i / 5) + 0.03 for i in range(5)], mat='bark', sides=4)
