"""Signature pieces: SHIBUYA109 sign ring and letters (one fallen), QFRONT's dead screen, MAGNET's sign,
the Center-gai arch, Hachiko on his pedestal."""
import math
import random

import bpy
import numpy as np
from mathutils import Vector, Matrix

from sb_mesh import MB
from sb_props import X, box, cylinder
from sb_tex_props import props_uv, signs_uv
from sb_common import FONT_JP, CROSS

C109 = Vector((-57.6, -43.8))
R109 = 5.75


def letter_mesh(ch, size=2.4, extrude=0.18, font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
    """a letter as triangles: list of (verts (n,3) local: x across, y depth, z up), faces"""
    cu = bpy.data.curves.new('L_' + ch, 'FONT')
    try:
        cu.font = bpy.data.fonts.load(font_path, check_existing=True)
    except Exception:
        pass
    cu.body = ch
    cu.size = size
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.resolution_u = 3
    ob = bpy.data.objects.new('L_' + ch, cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    V = np.array([v.co[:] for v in me.vertices])
    F = [list(p.vertices) for p in me.polygons]
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    # text lies in XY (reading along +x, up = +y), extruded along z: -> x across, z up, y depth
    V = np.stack([V[:, 0], -V[:, 2], V[:, 1]], 1)
    return V, F


def add_tris(mb, V, F, xf, mat, uvscale=0.5, col=(1, 1, 1, 1)):
    for f in F:
        P = [xf(tuple(V[i])) for i in f]
        uv = [(V[i][0] * uvscale, V[i][2] * uvscale + V[i][1] * uvscale) for i in f]
        mb.face(P, uv, mat, col)


def sign109(mb, ground, rnd, collide):
    z0, z1 = 58.2, 62.6
    rr = R109 + 0.25
    N = 36
    # sign band: silver panels around the top of the cylinder, a few peeled away
    for k in range(N):
        if rnd.random() < 0.14:
            continue
        a0 = 2 * math.pi * k / N; a1 = 2 * math.pi * (k + 1) / N
        p0 = C109 + Vector((math.cos(a0), math.sin(a0))) * rr
        p1 = C109 + Vector((math.cos(a1), math.sin(a1))) * rr
        top = z1 - (rnd.uniform(0.5, 2.0) if rnd.random() < 0.12 else 0)
        mb.face([(p0.x, p0.y, z0), (p1.x, p1.y, z0), (p1.x, p1.y, top), (p0.x, p0.y, top)],
                [props_uv('paint_white', 0, 0), props_uv('paint_white', 1, 0), props_uv('paint_white', 1, 1), props_uv('paint_white', 0, 1)],
                'props', (0.85, 0.86, 0.86, 1))
    # the letters, wrapped around the side facing the crossing
    word = 'SHIBUYA109'
    face_az = math.atan2(CROSS.y - C109.y, CROSS.x - C109.x) + math.radians(18)
    adv = 1.75
    span = adv * (len(word) - 1) / (rr + 0.2)
    fallen = None
    for i, ch in enumerate(word):
        az = face_az - span / 2 + i * adv / (rr + 0.2)
        V, F = letter_mesh(ch, size=2.6, extrude=0.2)
        if ch == '1':
            fallen = (V, F)
            continue
        p = C109 + Vector((math.cos(az), math.sin(az))) * (rr + 0.12)
        yaw = az + math.pi / 2
        tilt = math.radians(rnd.uniform(-6, 6)) if rnd.random() < 0.4 else 0.0
        sag = rnd.uniform(0, 0.6) if rnd.random() < 0.3 else 0.0
        xf = X(p.x, p.y, z0 + 0.8 - sag, yaw, 0, 0)
        if tilt:
            xf.M = xf.M @ Matrix.Rotation(tilt, 4, 'Y')
        add_tris(mb, V, F, xf, 'metal')
    # the '1' lies in the street at the fork, half buried
    if fallen:
        V, F = fallen
        x, y = -41.0, -47.5
        xf = X(x, y, ground(x, y) + 0.05, rnd.uniform(0, 6.28), 0, 0)
        xf.M = xf.M @ Matrix.Rotation(math.radians(-90 + 8), 4, 'X') @ Matrix.Rotation(math.radians(12), 4, 'Y')
        add_tris(mb, V * 1.0, F, xf, 'metal')
        collide.append(('box', X(x, y, ground(x, y)), (-1.2, 1.2, -1.2, 1.2, 0, 0.5)))
    # crown ring on the very top
    cylinder(mb, X(C109.x, C109.y, 0), (0, 0), R109 + 0.05, 64.6, 65.6, 24, 'paint_grey', caps=False)


def qfront(mb, ground, rnd):
    a = Vector((61.7, -22.8)); b = Vector((78.6, -20.8))
    t = (b - a).normalized(); n = Vector((t.y, -t.x))
    W, H = 13.0, 17.0
    z0 = 15.2 + 14.5
    c = a + t * ((b - a).length / 2) + n * 1.3
    # the main panel hangs from its top-left corner, dropped and twisted a little
    ang = math.radians(-9)
    def P(u, v, out=0.0):
        # u: 0..W along t, v: 0..H up, rotated in plane about the top-left corner
        x0 = -W / 2; ztop = z0 + H
        du, dv = u, v - H
        ru = du * math.cos(ang) - dv * math.sin(ang)
        rv = du * math.sin(ang) + dv * math.cos(ang)
        p = c + t * (x0 + ru) + n * (out + 0.06 * ru)
        return (p.x, p.y, ztop + rv)
    # screen face split: upper 3/4 attached, the lower-right quarter torn and hanging outward
    cut = 0.28
    pts = [P(0, H * cut), P(W, H * cut), P(W, H), P(0, H)]
    mb.face(pts, [signs_uv('qscreen', 0, cut), signs_uv('qscreen', 1, cut), signs_uv('qscreen', 1, 1), signs_uv('qscreen', 0, 1)], 'signs')
    pts = [P(0, 0), P(W * 0.45, 0), P(W * 0.45, H * cut), P(0, H * cut)]
    mb.face(pts, [signs_uv('qscreen', 0, 0), signs_uv('qscreen', 0.45, 0), signs_uv('qscreen', 0.45, cut), signs_uv('qscreen', 0, cut)], 'signs')
    # torn piece hangs from the cut line, swung out
    h0 = P(W * 0.45, H * cut); h1 = P(W, H * cut)
    hv = Vector(h1) - Vector(h0)
    down = Vector((n.x * 2.0, n.y * 2.0, -H * cut * 0.9))
    q0 = Vector(h0) + down + Vector((0, 0, -0.5)); q1 = Vector(h1) + down * 1.1
    mb.face([tuple(q0), tuple(q1), h1, h0], [signs_uv('qscreen', 0.45, 0), signs_uv('qscreen', 1, 0), signs_uv('qscreen', 1, cut), signs_uv('qscreen', 0.45, cut)], 'signs')
    # frame members and the brackets back to the wall
    def beam(p, q, w=0.18):
        p = Vector(p); q = Vector(q)
        d = (q - p); L = d.length
        if L < 1e-3:
            return
        yaw = math.atan2(d.y, d.x); pitch = -math.asin(max(-1, min(1, d.z / L)))
        xf = X(p.x, p.y, p.z, yaw, pitch, 0)
        box(mb, xf, 0, L, -w / 2, w / 2, -w / 2, w / 2, {'*': ('rust', props_uv)})
    for (p0, p1) in ((P(0, H, -0.4), P(W, H, -0.4)), (P(0, H * cut, -0.4), P(0, H, -0.4)), (P(W, H * cut, -0.4), P(W, H, -0.4)),
                     (P(0, 0, -0.4), P(0, H * cut, -0.4)), (P(0, 0, -0.4), P(W * 0.45, 0, -0.4))):
        beam(p0, p1, 0.8)
    for u in (0.5, W / 2, W - 0.5):
        p = Vector(P(u, H, 0.1)); q = p - Vector((n.x, n.y, 0)) * 1.3
        beam(tuple(q), tuple(p), 0.14)


def magnet(mb):
    a = Vector((110.9, -39.8)); b = Vector((103.0, -31.8))
    t = (b - a).normalized(); n = Vector((t.y, -t.x))
    L = (b - a).length
    c = a + t * (L / 2) + n * 0.3
    w, h = L - 0.6, (L - 0.6) * 3 / 16
    z = 51.5
    p0 = c - t * w / 2; p1 = c + t * w / 2
    mb.face([(p0.x, p0.y, z), (p1.x, p1.y, z - 0.4), (p1.x, p1.y, z + h - 0.4), (p0.x, p0.y, z + h)],
            [signs_uv('magnet', 0, 0), signs_uv('magnet', 1, 0), signs_uv('magnet', 1, 1), signs_uv('magnet', 0, 1)], 'signs')
    # screen on the west face over Jingu-dori
    a = Vector((103.0, -31.8)); b = Vector((113.9, 19.9))
    t = (b - a).normalized(); n = Vector((t.y, -t.x))
    c = a + t * 9.0 + n * 0.5
    w, h = 11.0, 8.25
    for (z, k) in ((30.0, 0),):
        p0 = c - t * w / 2; p1 = c + t * w / 2
        mb.face([(p0.x, p0.y, z), (p1.x, p1.y, z), (p1.x, p1.y, z + h), (p0.x, p0.y, z + h)],
                [signs_uv('screen2', 0, 0), signs_uv('screen2', 1, 0), signs_uv('screen2', 1, 1), signs_uv('screen2', 0, 1)], 'signs')


def centergai_arch(mb, ground, rnd, collide):
    c = Vector((59.6, -33.2))
    d = Vector((-7.0, 14.0)).normalized()      # along the street
    n = Vector((d.y, -d.x))                    # across
    half = 6.3
    pa = c - n * half; pb = c + n * half
    H = 6.6
    # posts (one leaning)
    for k, p in enumerate((pa, pb)):
        lean = math.radians(7) if k == 1 else 0.0
        xf = X(p.x, p.y, ground(p.x, p.y), math.atan2(n.y, n.x), 0, 0)
        if lean:
            xf.M = xf.M @ Matrix.Rotation(lean, 4, 'X')
        box(mb, xf, -0.22, 0.22, -0.22, 0.22, -0.3, H + 0.4, {'*': ('paint_grey', props_uv)}, skip=('nz',))
        collide.append(('box', X(p.x, p.y, ground(p.x, p.y)), (-0.3, 0.3, -0.3, 0.3, 0, 2.5)))
    zg = (ground(pa.x, pa.y) + ground(pb.x, pb.y)) / 2
    # sign panels back to back, tilted (the right post leans), with an arched top truss
    w = 2 * half - 0.4
    hh = w * 3 / 16
    tilt = 0.45
    for side in (-1, 1):
        off = d * 0.12 * side
        p0 = c - n * w / 2 + off; p1 = c + n * w / 2 + off
        if side > 0:
            p0, p1 = p1, p0
        za = zg + H; zb = zg + H - tilt * (1 if side < 0 else -1)
        za, zb = (zg + H, zg + H - tilt) if side < 0 else (zg + H - tilt, zg + H)
        mb.face([(p0.x, p0.y, za), (p1.x, p1.y, zb), (p1.x, p1.y, zb + hh), (p0.x, p0.y, za + hh)],
                [signs_uv('centergai', 0, 0), signs_uv('centergai', 1, 0), signs_uv('centergai', 1, 1), signs_uv('centergai', 0, 1)], 'signs')
    # arch truss: a bent band of short beams above the sign
    prev = None
    for i in range(13):
        s = i / 12
        p = c - n * w / 2 + n * w * s
        z = zg + H + hh + 0.15 + math.sin(math.pi * s) * 1.1 - tilt * s
        if prev is not None:
            q = Vector((p.x, p.y, z)); pp = Vector(prev)
            dd = q - pp; L = dd.length
            xf = X(pp.x, pp.y, pp.z, math.atan2(dd.y, dd.x), -math.asin(dd.z / L), 0)
            box(mb, xf, 0, L, -0.1, 0.1, -0.12, 0.12, {'*': ('paint_grey', props_uv)})
        prev = (p.x, p.y, z)


def hachiko(collection, mats, ground, rnd, collide):
    import sb_hachiko
    j = sb_hachiko.build(save=False)
    me = j.data
    # vertex colour (white) and UV1 = UVMap (already unique)
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
    ca.data.foreach_set('color', np.ones(len(me.loops) * 4, np.float32))
    uv = me.uv_layers[0]
    uv.name = 'UVMap'
    u1 = me.uv_layers.new(name='UV1')
    a = np.empty(len(me.loops) * 2, np.float32); uv.data.foreach_get('uv', a); u1.data.foreach_set('uv', a)
    me.uv_layers.active = uv
    if 'is_ped' in me.attributes:
        me.attributes.remove(me.attributes['is_ped'])
    import sb_mats
    me.materials.clear(); me.materials.append(sb_mats.make('bronze'))
    x, y = 88.9, -100.0
    j.location = (x, y, ground(x, y) - 0.05)
    j.rotation_euler = (0, 0, 0.61)
    for c in list(j.users_collection):
        c.objects.unlink(j)
    collection.objects.link(j)
    j.name = 'hachiko'
    import sb_hachiko as H
    collide.append(('box', X(x, y, ground(x, y), 0.61), (-H.BASE_W / 2, H.BASE_W / 2, -H.BASE_D / 2, H.BASE_D / 2, 0, H.BASE_H + H.PED_H)))
    return j


def plaque(mb, ground):
    import sb_hachiko as H
    x, y = 88.9, -100.0
    xf = X(x, y, ground(x, y) - 0.05, 0.61)
    yy = H.PED_D / 2 + 0.012
    P = [(-0.4, yy, H.BASE_H + 0.75), (0.4, yy, H.BASE_H + 0.75), (0.4, yy, H.BASE_H + 1.15), (-0.4, yy, H.BASE_H + 1.15)]
    # facing +y: order so the face looks +y
    P = [P[1], P[0], P[3], P[2]]
    mb.face([xf(p) for p in P], [signs_uv('hachi_plate', 0, 0), signs_uv('hachi_plate', 1, 0), signs_uv('hachi_plate', 1, 1), signs_uv('hachi_plate', 0, 1)], 'signs')


def wall_screen(mb, a, b, z, w, h, cell='screen2', off=0.5, tilt=0.0):
    a = Vector(a); b = Vector(b)
    t = (b - a).normalized(); n = Vector((t.y, -t.x))
    c = a + t * ((b - a).length / 2) + n * off
    p0 = c - t * w / 2; p1 = c + t * w / 2
    mb.face([(p0.x, p0.y, z), (p1.x, p1.y, z - tilt), (p1.x, p1.y, z + h - tilt), (p0.x, p0.y, z + h)],
            [signs_uv(cell, 0, 0), signs_uv(cell, 1, 0), signs_uv(cell, 1, 1), signs_uv(cell, 0, 1)], 'signs')


def roof_z(b, x, y):
    import sb_geom as G
    best = None
    for ring, z in b.top_surfaces:
        if G.point_in_poly((x, y), ring) and (best is None or z > best):
            best = z
    return best


def roof_billboard(mb, b, x, y, yaw, rnd, cell):
    z = roof_z(b, x, y)
    if z is None:
        return
    W, H = 8.0, 4.0
    xf = X(x, y, z, yaw, 0, 0)
    lift = 2.2
    # legs and frame (rusty)
    for u in (-3.5, -1.2, 1.2, 3.5):
        box(mb, xf, u - 0.08, u + 0.08, -0.08, 0.08, 0, lift + H, {'*': ('rust', props_uv)}, skip=('nz',))
        box(mb, xf, u - 0.06, u + 0.06, 0.3, 1.6, 0, 0.12, {'*': ('rust', props_uv)})
    box(mb, xf, -W / 2, W / 2, 0.05, 0.2, lift - 0.15, lift, {'*': ('rust', props_uv)})
    # torn poster (alpha) on the front
    sag = rnd.uniform(0, 0.5)
    P = [xf((-W / 2, -0.1, lift)), xf((W / 2, -0.1, lift - sag)), xf((W / 2, -0.1, lift + H - sag)), xf((-W / 2, -0.1, lift + H))]
    mb.face(P, [signs_uv(cell, 0, 0), signs_uv(cell, 1, 0), signs_uv(cell, 1, 1), signs_uv(cell, 0, 1)], 'signs')


def build(mb, ground, rnd, collide, bldgs=None):
    # dead screens around the crossing: the station-side building and Seibu
    wall_screen(mb, (38.9, -71.7), (30.4, -61.8), 33.0, 10.0, 7.5, tilt=0.6)
    wall_screen(mb, (78.9, -19.4), (82.5, -2.0), 44.0, 9.0, 6.75, off=0.6)
    if bldgs:
        face = math.atan2(-52 - 0, 78 - 0)
        for (nm, x, y, cell) in (('b021', 30.0, -16.0, 'bill0'), ('b002', -4.0, -20.0, 'bill1'), ('b006', 25.0, -75.0, 'bill2'),
                                 ('b026', -30.0, -12.0, 'bill3'), ('b012', 118.0, 5.0, 'bill1')):
            b = bldgs.get(nm)
            if b is None:
                continue
            yaw = math.atan2(-52 - y, 78 - x) + math.pi / 2
            roof_billboard(mb, b, x, y, yaw, rnd, cell)
    sign109(mb, ground, rnd, collide)
    qfront(mb, ground, rnd)
    magnet(mb)
    centergai_arch(mb, ground, rnd, collide)
    plaque(mb, ground)
