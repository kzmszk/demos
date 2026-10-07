"""Pack the Sanjūsangen-dō statues (venv python):  python statue_pack.py BUILD_DIR STAGE_DIR && node statue_pack.mjs STAGE_DIR ../public/data/statues
Reads ASSETS/heroes/statues/index.json + <id>[_lod1|_lod2].npz (jk.export_npz, local frame: origin at the pedestal's
bottom centre, facing +y) and ASSETS/heroes/sanjusangendo_slots.json (world positions).  Writes STAGE_DIR/<id>_<lod>.v/.i +
statues.json: per statue model and LOD a mesh (pos i16x4 / Q, nrm s8x4, c0 u8x4, c1 u8x4: x = material id) and
per model its instances (x, y, z, yaw, light: sky + bounce from the hall's bake at chest height).  The 1000 standing
Kannon spread over the variants a/b/c."""
import sys, os, json, math
import numpy as np
from scipy.spatial import cKDTree
from gen.frame import tile_of

ASSETS = '/home/kazu/work/kyoto-assets'
SD = os.path.join(ASSETS, 'heroes', 'statues')
IRR_MAX = 4.0

def enc_irr(irr, sun):
    q = np.sqrt(np.clip(np.asarray(irr, np.float32) / IRR_MAX, 0, 1))
    out = np.zeros((len(q), 4), np.uint8); out[:, :3] = np.round(q * 255); out[:, 3] = np.round(np.clip(sun, 0, 1) * 255)
    return out

Q = 4096.0                                       # position units per metre (int16: +-8 m, 0.24 mm)

def mesh_bytes(d):
    """20-byte vertices: pos i16x4 (metres x Q), nrm s8x4, c0 u8x4, c1 u8x4 (x = material id)"""
    P = d['P']; n = len(P)
    v = np.zeros(n, dtype=[('p', '<i2', 4), ('n', 'i1', 4), ('c0', 'u1', 4), ('c1', 'u1', 4)])
    v['p'][:, :3] = np.round(np.clip(P * Q, -32767, 32767)); v['n'][:, :3] = np.round(np.clip(d['N'], -1, 1) * 127); v['n'][:, 3] = 127
    v['c0'] = d['C0']; c1 = d['C1'].copy(); c1[:, 0] = d['MAT']; v['c1'] = c1
    return v.tobytes(), d['I'].astype(np.uint32).ravel()

def light_at(build, pts):
    """sky + bounce light (and sun visibility) of the nearest baked vertices of the tiles around the points"""
    out_i = np.zeros((len(pts), 3), np.float32); out_s = np.zeros(len(pts), np.float32)
    by = {}
    for k, p in enumerate(pts): by.setdefault(tile_of(p[0], p[1]), []).append(k)
    for (i, j), ks in by.items():
        n = f't_{i}_{j}'
        f = os.path.join(build, n + '.npz'); b = os.path.join(build, n + '.bake.npz')
        if not (os.path.exists(f) and os.path.exists(b)): out_i[ks] = 0.15; continue
        d = np.load(f); bk = np.load(b)
        tree = cKDTree(d['P'])
        q = np.array([pts[k] for k in ks])
        dd, nb = tree.query(q, k=24)
        out_i[ks] = bk['IRR'][nb].astype(np.float32).mean(1); out_s[ks] = bk['SUN'][nb].astype(np.float32).mean(1)
    return out_i, out_s

def main(build, out):
    idx = json.load(open(os.path.join(SD, 'index.json')))
    slots = json.load(open(os.path.join(ASSETS, 'heroes', 'sanjusangendo_slots.json')))
    insts = {}                                   # model id -> list of (x, y, z, yaw)
    ks = [k for k in idx if k.startswith('kannon_standing')]
    for n, s in enumerate(slots.get('kannon_standing', [])):
        insts.setdefault(ks[(n * 7 + (n // 50) * 3) % len(ks)], []).append(s[:4])
    for k in ('kannon_seated', 'fujin', 'raijin'):
        if k in slots and k in idx:
            s = slots[k][0] if isinstance(slots[k][0], (list, tuple)) else slots[k]
            insts.setdefault(k, []).append(s[:4])
    for a in slots.get('attendants', []):
        key = a.get('id') or a['name']
        if key not in idx:
            norm = lambda t: str(t).lower().replace(' ', '_').replace('-', '_')
            cand = [k for k in idx if norm(k) == norm(a['name'])]
            key = cand[0] if cand else None
        if key: insts.setdefault(key, []).append([a['x'], a['y'], a['z'], a['yaw']])
    models = []
    os.makedirs(out, exist_ok=True)
    for k, meta in idx.items():
        if k not in insts: continue
        rec = dict(id=k, name_ja=meta.get('name_ja'), name_en=meta.get('name_en'), lods=[])
        for li, f in enumerate(meta['lods']):
            d = np.load(os.path.join(SD, os.path.basename(f)))
            vb, ib = mesh_bytes(d)
            nm = f'{k}_{li}'
            open(os.path.join(out, nm + '.v'), 'wb').write(vb); open(os.path.join(out, nm + '.i'), 'wb').write(ib.tobytes())
            rec['lods'].append(dict(name=nm, vcount=len(vb) // 20, icount=int(len(ib))))
        I = np.array(insts[k], np.float64)
        h = float(meta.get('height_m', 1.7))
        li_, ls = light_at(build, np.c_[I[:, 0], I[:, 1], I[:, 2] + h * 0.6])
        rec['inst'] = np.round(I, 3).tolist(); rec['light'] = enc_irr(li_ * 1.0, ls).tolist(); rec['height'] = h
        models.append(rec)
        print(k, len(I), 'instances', [l['icount'] // 3 for l in rec['lods']], 'tris/LOD', flush=True)
    json.dump(dict(models=models, stride=20, q=Q), open(os.path.join(out, 'statues.json'), 'w'))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
