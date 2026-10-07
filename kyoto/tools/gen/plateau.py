"""PLATEAU (国土交通省 Project PLATEAU, 京都市 2025, CityGML 2.0 / i-UR 3.x) building parser.
python -m gen.plateau  -> ASSETS/cache/plateau/<mesh>.pkl for every bldg GML of the core

Per building: id, cls (Building_class), use (Building_usage), year, h (measuredHeight), st (storeys above), struct
(buildingStructureType), z0/z1 (LOD1 solid base/top, T.P.), edge (lod0 roof edge, local xy, CCW, may be several),
lod2 / lod3: {'R' roof, 'W' wall, 'G' ground, 'OF' outer floor, 'OC' outer ceiling, 'C' closure, 'win', 'door', 'inst'}
-> lists of polygons, each a list of rings (exterior first) of float32 (k,3) local xyz."""
import os, sys, glob, pickle, time
import numpy as np
from lxml import etree
from .frame import ASSETS, to_xy

NS = {'gml': 'http://www.opengis.net/gml', 'bldg': 'http://www.opengis.net/citygml/building/2.0',
      'uro': 'https://www.geospatial.jp/iur/uro/3.2', 'core': 'http://www.opengis.net/citygml/2.0', 'xlink': 'http://www.w3.org/1999/xlink'}
G = '{%s}' % NS['gml']; B = '{%s}' % NS['bldg']; U = '{%s}' % NS['uro']
SURF = {'RoofSurface': 'R', 'WallSurface': 'W', 'GroundSurface': 'G', 'OuterFloorSurface': 'OF', 'OuterCeilingSurface': 'OC', 'ClosureSurface': 'C',
        'FloorSurface': 'OF', 'CeilingSurface': 'OC', 'InteriorWallSurface': 'W'}

def poslist(el):
    v = np.array(el.text.split(), np.float64).reshape(-1, 3)
    return v

def polygons(el):
    """all gml:Polygon under el -> list of rings lists (raw lat/lon/h arrays)"""
    out = []
    for p in el.iter(G + 'Polygon'):
        rings = []
        ex = p.find(G + 'exterior')
        if ex is None: continue
        pl = ex.find('.//' + G + 'posList')
        if pl is None or not pl.text: continue
        rings.append(poslist(pl))
        for it in p.findall(G + 'interior'):
            q = it.find('.//' + G + 'posList')
            if q is not None and q.text: rings.append(poslist(q))
        out.append(rings)
    return out

def txt(el, path, conv=str, default=None):
    e = el.find(path, NS)
    if e is None or e.text is None: return default
    try: return conv(e.text.strip())
    except Exception: return default

def parse_building(el):
    b = dict(id=el.get(G + 'id'), cls=txt(el, 'bldg:class', int, 0), use=txt(el, 'bldg:usage', int, 0), year=txt(el, 'bldg:yearOfConstruction', int, 0),
             h=txt(el, 'bldg:measuredHeight', float, 0.0), st=txt(el, 'bldg:storeysAboveGround', int, 0), stb=txt(el, 'bldg:storeysBelowGround', int, 0),
             roof=txt(el, 'bldg:roofType', int, 0))
    s = el.find('.//uro:buildingStructureType', NS); b['struct'] = int(s.text) if s is not None and s.text and s.text.strip().isdigit() else 0
    s = el.find('.//uro:detailedUsage', NS); b['duse'] = int(s.text) if s is not None and s.text and s.text.strip().isdigit() else 0
    s = el.find('.//uro:totalFloorArea', NS); b['tfa'] = float(s.text) if s is not None and s.text else 0.0
    raw = []                              # (kind, lod, rings) with raw coords
    e0 = el.find('bldg:lod0RoofEdge', NS)
    edge = polygons(e0) if e0 is not None else []
    l1 = el.find('bldg:lod1Solid', NS)
    z = [r[:, 2] for p in (polygons(l1) if l1 is not None else []) for r in p]
    if z: zz = np.concatenate(z); b['z0'] = float(zz.min()); b['z1'] = float(zz.max())
    else: b['z0'] = b['z1'] = None
    for bb in el.findall('bldg:boundedBy', NS):
        for surf in bb:
            k = SURF.get(etree.QName(surf).localname)
            if k is None: continue
            for lod in (2, 3):
                m = surf.find(f'bldg:lod{lod}MultiSurface', NS)
                if m is not None:
                    for p in polygons(m): raw.append((k, lod, p))
            for op in surf.findall('bldg:opening', NS):
                for o in op:
                    kk = 'win' if etree.QName(o).localname == 'Window' else 'door'
                    for lod in (3,):
                        m = o.find(f'bldg:lod{lod}MultiSurface', NS)
                        if m is not None:
                            for p in polygons(m): raw.append((kk, lod, p))
    for inst in el.iter(B + 'BuildingInstallation'):
        for lod in (2, 3):
            g = inst.find(f'bldg:lod{lod}Geometry', NS)
            if g is not None:
                for p in polygons(g): raw.append(('inst', lod, p))
    # one projection for everything
    allr = [r for p in edge for r in p] + [r for (_, _, p) in raw for r in p]
    if not allr: return None
    C = np.concatenate(allr)
    x, y = to_xy(C[:, 1], C[:, 0])
    L = np.stack([x, y, C[:, 2]], 1).astype(np.float32)
    k = 0
    def take(r):
        nonlocal k
        a = L[k:k + len(r)]; k += len(r)
        if len(a) > 1 and np.allclose(a[0], a[-1]): a = a[:-1]
        return a
    b['edge'] = [[take(r)[:, :2] for r in p] for p in edge]
    b['lod2'] = {}; b['lod3'] = {}
    for (kk, lod, p) in raw:
        rings = [take(r) for r in p]
        b['lod%d' % lod].setdefault(kk, []).append(rings)
    return b

def parse_file(path):
    out = []
    for ev, el in etree.iterparse(path, events=('end',), tag=B + 'Building', huge_tree=True):
        try:
            b = parse_building(el)
            if b: out.append(b)
        except Exception as e:
            print('fail', path, e, file=sys.stderr)
        el.clear()
        while el.getprevious() is not None: del el.getparent()[0]
    return out

def run_one(path):
    mesh = os.path.basename(path).split('_')[0]
    dst = os.path.join(ASSETS, 'cache', 'plateau', mesh + '.pkl')
    if os.path.exists(dst) and os.path.getmtime(dst) > os.path.getmtime(path): return mesh, -1
    t0 = time.time(); bs = parse_file(path)
    pickle.dump(bs, open(dst, 'wb'), protocol=5)
    return mesh, len(bs), round(time.time() - t0, 1)

if __name__ == '__main__':
    from multiprocessing import Pool
    os.makedirs(os.path.join(ASSETS, 'cache', 'plateau'), exist_ok=True)
    files = sorted(glob.glob(os.path.join(ASSETS, 'plateau', 'gml', 'udx', 'bldg', '*_bldg_*_op.gml')), key=os.path.getsize, reverse=True)
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 6) as pool:
        for r in pool.imap_unordered(run_one, files): print(*r, flush=True)
