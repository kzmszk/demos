"""PLATEAU building tiles (b3dm: batch table + Draco glTF with CESIUM_RTC) -> per-building meshes in the local frame.
  python -m gen.plateau [N]      -> ASSETS/cache/plateau/<ward>.pkl   (list of buildings, deduplicated by gml_id)

Building: id, bid (uro:buildingID), h (measuredHeight), st (storeys), use (usage text), cls, lod2 (bool),
          V float32 (n,3) local xyz, F int32 (m,3) triangles, N float32 (m,3) face normals,
          z0/z1 (ground / top), cx/cy (centroid), foot: float32 (k,2) ground-surface outline (may be empty)."""
import os, sys, json, struct, pickle, time, glob
import numpy as np
import DracoPy
from .frame import ASSETS, ecef_to_local, X0, Y0, X1, Y1

PL = os.path.join(ASSETS, 'plateau')

def read_b3dm(path):
    b = open(path, 'rb').read()
    magic, ver, ln, fjl, fbl, bjl, bbl = struct.unpack('<4sIIIIII', b[:28])
    assert magic == b'b3dm'
    o = 28
    fj = json.loads(b[o:o + fjl]); o += fjl + fbl
    bj = json.loads(b[o:o + bjl]); o += bjl
    bbin = b[o:o + bbl]; o += bbl
    glb = b[o:]
    n = fj['BATCH_LENGTH']
    # binary batch columns
    for k, v in list(bj.items()):
        if isinstance(v, dict) and 'byteOffset' in v:
            ct = {'DOUBLE': 'f8', 'FLOAT': 'f4', 'INT': 'i4', 'UNSIGNED_INT': 'u4', 'SHORT': 'i2', 'UNSIGNED_SHORT': 'u2', 'BYTE': 'i1', 'UNSIGNED_BYTE': 'u1'}[v['componentType']]
            bj[k] = np.frombuffer(bbin, dtype='<' + ct, count=n, offset=v['byteOffset']).tolist()
    assert glb[:4] == b'glTF'
    jl = struct.unpack('<I', glb[12:16])[0]
    gj = json.loads(glb[20:20 + jl])
    bl = struct.unpack('<I', glb[20 + jl:24 + jl])[0]
    bin0 = glb[28 + jl:28 + jl + bl]
    rtc = gj.get('extensions', {}).get('CESIUM_RTC', {}).get('center', [0, 0, 0])
    out = []
    for mesh in gj['meshes']:
        for prim in mesh['primitives']:
            ext = prim.get('extensions', {}).get('KHR_draco_mesh_compression')
            if ext is None: continue
            bv = gj['bufferViews'][ext['bufferView']]
            raw = bin0[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]
            m = DracoPy.decode(raw)
            P = np.asarray(m.points, np.float64).reshape(-1, 3)
            F = np.asarray(m.faces, np.int64).reshape(-1, 3)
            # the batch id attribute: DracoPy lists every attribute with its data under m.attributes
            bid = None
            want = ext['attributes'].get('_BATCHID')
            for a in m.attributes:
                if a['unique_id'] == want: bid = np.asarray(a['data'], np.int64).ravel()
            out.append((P, F, bid, rtc))
    return bj, n, out

def tile_buildings(path):
    bj, n, prims = read_b3dm(path)
    bs = {}
    for P, F, bid, rtc in prims:
        if bid is None or len(bid) != len(P):
            continue
        # glTF is y-up; 3D Tiles turns it z-up before adding the RTC centre: ECEF = RTC + (x, -z, y)
        x, y, z = ecef_to_local(P[:, 0] + rtc[0], -P[:, 2] + rtc[1], P[:, 1] + rtc[2])
        V = np.stack([x, y, z], 1).astype(np.float32)
        fb = bid[F[:, 0]]
        for k in np.unique(fb):
            sel = F[fb == k]
            used, inv = np.unique(sel.ravel(), return_inverse=True)
            Vk = V[used]; Fk = inv.reshape(-1, 3).astype(np.int32)
            b = bs.setdefault(int(k), dict(V=[], F=[]))
            off = sum(len(v) for v in b['V'])
            b['V'].append(Vk); b['F'].append(Fk + off)
    out = []
    for k, b in bs.items():
        V = np.concatenate(b['V']); F = np.concatenate(b['F'])
        cx, cy = float(V[:, 0].mean()), float(V[:, 1].mean())
        if not (X0 - 50 <= cx <= X1 + 50 and Y0 - 50 <= cy <= Y1 + 50): continue
        e1 = V[F[:, 1]] - V[F[:, 0]]; e2 = V[F[:, 2]] - V[F[:, 0]]
        N = np.cross(e1, e2); ln = np.linalg.norm(N, axis=1); ok = ln > 1e-9
        N = np.where(ok[:, None], N / np.maximum(ln, 1e-9)[:, None], 0).astype(np.float32)
        h = bj.get('bldg:measuredHeight', [None] * n)[k]
        st = bj.get('bldg:storeysAboveGround', [None] * n)[k]
        a = bj.get('attributes', [None] * n)[k] or {}
        dq = (a.get('uro:DataQualityAttribute') or [{}])[0]
        lod2 = dq.get('uro:geometrySrcDescLod2_code', '999') != '999'
        did = (a.get('uro:BuildingIDAttribute') or [{}])[0].get('uro:buildingID')
        out.append(dict(id=bj['gml_id'][k], bid=did, h=float(h) if h is not None and h == h else None, st=st if st not in (None, 9999) else None,
                        use=a.get('bldg:usage'), cls=a.get('bldg:class'), name=a.get('gml:name'), lod2=lod2,
                        V=V, F=F, N=N, z0=float(V[:, 2].min()), z1=float(V[:, 2].max()), cx=cx, cy=cy))
    return out

def run_ward(code):
    t0 = time.time()
    files = sorted(glob.glob(os.path.join(PL, code, 'data', '*.b3dm')))
    seen = {}; nt = 0
    for f in files:
        for b in tile_buildings(f):
            nt += 1
            o = seen.get(b['id'])
            if o is None or len(b['F']) > len(o['F']): seen[b['id']] = b
    bs = list(seen.values())
    os.makedirs(os.path.join(ASSETS, 'cache', 'plateau'), exist_ok=True)
    pickle.dump(bs, open(os.path.join(ASSETS, 'cache', 'plateau', code + '.pkl'), 'wb'), protocol=5)
    tri = sum(len(b['F']) for b in bs); l2 = sum(1 for b in bs if b['lod2'])
    return code, len(files), nt, len(bs), tri, l2, round(time.time() - t0, 1)

if __name__ == '__main__':
    from multiprocessing import Pool
    codes = [c for c in sorted(os.listdir(PL)) if c.isdigit() and glob.glob(os.path.join(PL, c, 'data', '*.b3dm'))]
    if len(sys.argv) > 1 and sys.argv[1].isdigit() and len(sys.argv[1]) == 5: codes = [sys.argv[1]]
    with Pool(min(8, len(codes))) as pool:
        for r in pool.imap_unordered(run_ward, codes): print('ward files tiles-bldgs bldgs tris lod2 s:', *r, flush=True)
