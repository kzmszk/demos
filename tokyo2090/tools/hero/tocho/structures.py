"""Pedestrian bridges to Chuo Park over 公園通り (虹の橋, 緑の橋, 水の橋): concrete decks on piers at podium level, one
collapsed into the street. Visual only (left out of collide where they cross the street)."""
import bpy, math, random, json
from mathutils import Vector
import common as C
import uvmap as U
import materials as M
from buildings import seg

MC = U.MC
OSM = json.load(open(C.SRC + 'osm.json'))


def deck(mb, a, b, z, w, th=1.1, par=1.1):
    a = Vector((a[0], a[1], z)); b = Vector((b[0], b[1], z))
    d = (b - a).normalized(); n = Vector((-d.y, d.x, 0)) * w / 2
    P = [a - n, b - n, b + n, a + n]
    mb.poly(P, 0, MC['roof'])                                                   # walking surface (moss, soil)
    mb.poly([p - Vector((0, 0, th)) for p in P][::-1], 0, MC['concrete'])
    for i in range(4):
        j = (i + 1) % 4
        mb.quad(P[i] - Vector((0, 0, th)), P[j] - Vector((0, 0, th)), P[j], P[i], 0, MC['concrete'])
    # parapets
    for s in (-1, 1):
        q0 = a + n * s * 0.92; q1 = b + n * s * 0.92
        mb.box(((q0.x + q1.x) / 2, (q0.y + q1.y) / 2, z + par / 2), ((b - a).length, 0.22, par), math.atan2(d.y, d.x), 0, MC['concrete'], bottom=False)


def build(col, dec, R):
    mats = M.all_mats()
    mb = C.MB()
    out = []
    for r in OSM['roads']:
        if r['hw'] != 'pedestrian' or not r['bridge'] or r['name'] not in ('虹の橋', '緑の橋', '水の橋'): continue
        line = [Vector(p) for p in r['line']]
        # keep the part inside the box (+ a broken stub just past its west edge)
        pts = [p for p in line if p.x > C.BOX[0] - 6]
        if len(pts) < 2: continue
        # deck level = the podium where the bridge starts (east end)
        east = max(pts, key=lambda p: p.x)
        z = C.ground(east.x, east.y) + 0.05
        collapsed = r['name'] == '水の橋'
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if a.x > b.x: a, b = b, a
            L = (b - a).length
            if L < 0.5: continue
            if collapsed and a.x < -100:
                # the span over the street broke: the west part hangs down into the street
                hinge = Vector((max(a.x, -104), a.y + (b.y - a.y) * (max(a.x, -104) - a.x) / max(b.x - a.x, 1e-3)))
                deck(mb, hinge, b, z, 5.0)
                tip = a.copy()
                gz = C.ground(tip.x, tip.y)
                d = (hinge - tip).normalized()
                # tilted slab from the hinge to the street
                h0 = Vector((hinge.x, hinge.y, z)); t0 = Vector((tip.x + d.x * 2, tip.y + d.y * 2, gz + 0.6))
                n = Vector((-d.y, d.x, 0)) * 2.5
                mb.quad(t0 - n, h0 - n, h0 + n, t0 + n, 0, MC['roof'])
                mb.quad(t0 + n - Vector((0, 0, 1)), h0 + n - Vector((0, 0, 1)), h0 - n - Vector((0, 0, 1)), t0 - n - Vector((0, 0, 1)), 0, MC['concrete'])
                for s in (n, -n):
                    mb.quad(t0 + s - Vector((0, 0, 1)), t0 + s, h0 + s, h0 + s - Vector((0, 0, 1)), 0, MC['broken'])
                for k in range(5):     # rebar hanging out of the break
                    p = h0 + n * (k / 2 - 1) * 0.9
                    seg(mb, p, p + Vector((-d.x * 1.5, -d.y * 1.5, -R.uniform(0.5, 2))), 0.06)
                continue
            deck(mb, a, b, z, 5.0)
            # piers where the ground drops away
            for t in [k / max(1, int(L / 14)) for k in range(int(L / 14) + 1)]:
                p = a.lerp(b, t)
                g = C.ground(p.x, p.y)
                if z - g > 3:
                    mb.box((p.x, p.y, (g + z - 1.1) / 2 - 0.3), (1.2, 3.6, z - 1.1 - g + 0.6), math.atan2((b - a).y, (b - a).x), 0, MC['concrete'], bottom=False)
        # broken stub end at the west
        w = min(pts, key=lambda p: p.x)
        mb.box((w.x, w.y, z - 0.6), (0.5, 5.2, 1.3), 0, 0, MC['broken'], bottom=False)
    o = mb.build('bridges', [mats['mat']], col)
    U.cut_and_map(o, U.MAT_CELLS)
    out.append(o)
    return out
