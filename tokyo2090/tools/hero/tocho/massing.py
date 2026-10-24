"""2.5D massing of the PLATEAU LOD2 shells (run with the venv python, needs shapely).

  python massing.py  ->  WORK/massing.json

Every LOD2 building is an extruded-roof model, so it is exactly the union of prisms 'roof polygon from z0 up to its
height'. For each building we collect the upward roof triangles, cluster their heights into levels and write, per
level, the footprint F_k = union of roofs at or above that level. The Blender side extrudes band k from z_{k-1} to z_k
with footprint F_k and caps the exposed roof F_k - F_{k+1}: clean, closed, easy to cut, UV and break.
"""
import json, os, sys
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

SRC = '/home/kazu/work/tokyo2090-assets/hero/tocho/'
WORK = SRC + 'work/'


def load_obj(path):
    objs, cur, V = {}, None, []
    for l in open(path):
        if l.startswith('o '):
            cur = l.split()[1]; objs[cur] = []
        elif l.startswith('v '):
            V.append(tuple(map(float, l.split()[1:4])))
        elif l.startswith('f '):
            objs[cur].append([V[int(t.split('/')[0]) - 1] for t in l.split()[1:]])
    return objs


def polys(g):
    if g.is_empty: return []
    if isinstance(g, Polygon): return [g]
    if isinstance(g, MultiPolygon): return list(g.geoms)
    return [p for p in getattr(g, 'geoms', []) if isinstance(p, Polygon)]


def ring(r):
    c = list(r.coords)[:-1]
    return [[round(x, 3), round(y, 3)] for x, y in c]


BRIDGE_Z = 47.6


def corridor():
    """都庁通り where it passes under the Assembly wings (the road deck at ~40.6 m)"""
    from shapely.geometry import LineString
    o = json.load(open(SRC + 'osm.json'))
    ls = []
    for r in o['roads']:
        if r['name'] == '都庁通り' and r['bridge']:
            l = LineString(r['line'])
            if l.bounds[1] < 150 and l.bounds[3] > -10: ls.append(l.buffer(r['width'] / 2 + 3.5, cap_style=2))
    return unary_union(ls).buffer(1.0)


def main():
    meta = json.load(open(SRC + 'buildings.json'))
    objs = load_obj(SRC + 'buildings.obj')
    out = {}
    for b in meta['buildings']:
        name = b['obj']; fs = np.array([f for f in objs[name] if len(f) == 3])
        z0 = b['z0']
        roofs = []
        for t in fs:
            n = np.cross(t[1] - t[0], t[2] - t[0]); a = np.linalg.norm(n)
            if a < 1e-6 or n[2] / a < 0.5: continue
            p = Polygon(t[:, :2])
            if p.area < 1e-4: continue
            roofs.append((float(t[:, 2].mean()), p.buffer(0.02, join_style=2)))
        # cluster heights (0.6 m)
        zs = sorted(z for z, _ in roofs)
        levels = []
        for z in zs:
            if levels and z - levels[-1][-1] < 0.6: levels[-1].append(z)
            else: levels.append([z])
        lv = [max(c) for c in levels]
        lv = [z for z in lv if z > z0 + 0.3]
        def lvl(z):
            for i, c in enumerate(levels):
                if c[0] - 1e-6 <= z <= c[-1] + 1e-6: return max(c)
            return z
        roofs = [(lvl(z), p) for z, p in roofs]
        bands = []
        prev = z0
        Fs = []
        for zk in lv:
            F = unary_union([p for z, p in roofs if z >= zk - 1e-6]).buffer(-0.02, join_style=2).simplify(0.08)
            F = unary_union([p for p in polys(F) if p.area > 0.5])
            if F.is_empty: continue
            Fs.append((prev, zk, F)); prev = zk
        def enc(g):
            return [dict(outer=ring(orient(p, 1.0).exterior), holes=[ring(h) for h in orient(p, 1.0).interiors if Polygon(h).area > 0.5])
                    for p in polys(g) if p.area > 0.3]
        for k, (za, zb, F) in enumerate(Fs):
            above = Fs[k + 1][2] if k + 1 < len(Fs) else None
            roof = F.difference(above) if above is not None else F
            bands.append(dict(z0=round(za, 3), z1=round(zb, 3), polys=enc(F), roof=enc(roof.buffer(0)) ))
        out[name] = dict(z0=z0, bands=bands, name=b['name'])
        if name in ('b003', 'b006'):
            # the Assembly wings bridge 都庁通り: cut the road corridor out, the part over the road floats at BRIDGE_Z
            cor = corridor()
            keep, over = [], []
            for band in bands:
                pass
            def clip(bands, fn, zmin=None):
                res = []
                for band in bands:
                    if zmin is not None and band['z1'] <= zmin: continue
                    ps = unary_union([Polygon(p['outer'], p['holes']) for p in band['polys']])
                    rf = unary_union([Polygon(p['outer'], p['holes']) for p in band['roof']]) if band['roof'] else Polygon()
                    g = fn(ps); r = fn(rf)
                    if g.is_empty: continue
                    res.append(dict(z0=max(band['z0'], zmin) if zmin else band['z0'], z1=band['z1'], polys=enc(g), roof=enc(r)))
                return res
            out[name]['bands'] = clip(bands, lambda g: g.difference(cor))
            out[name + 'br'] = dict(z0=BRIDGE_Z, bands=clip(bands, lambda g: g.intersection(cor), BRIDGE_Z), name='bridge wing')
        print(name, len(roofs), 'levels', len(bands), 'top', bands[-1]['z1'] if bands else None)
    # collision tops: the exposed roofs; under the Assembly colonnade the arcade strip stays open (walk under it)
    from shapely.geometry import Point
    ann = Point(31.0, 71.0).buffer(62.6, 64).difference(Point(31.0, 71.0).buffer(56.2, 64))
    for name, b in out.items():
        cr = []
        for band in b['bands']:
            g = unary_union([Polygon(p['outer'], p['holes']).buffer(0) for p in band['roof']]) if band['roof'] else Polygon()
            if name in ('b002', 'b003', 'b004', 'b005', 'b006'):
                g = g.difference(ann) if band['z1'] < 70 else g
            for p in polys(g):
                if p.area > 0.5:
                    p = orient(p, 1.0)
                    cr.append(dict(z=band['z1'], outer=ring(p.exterior), holes=[ring(h) for h in p.interiors]))
        b['croof'] = cr
    json.dump(out, open(WORK + 'massing.json', 'w'))


if __name__ == '__main__':
    main()
