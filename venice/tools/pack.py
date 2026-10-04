"""Quantise baked tiles into raw streams (venv python):  python pack.py BUILD_DIR STAGE_DIR [tile names...]
Writes STAGE_DIR/<tile>.raw + <tile>.json; pack.mjs then meshopt-encodes them into public/data/tiles/."""
import sys, os, json, math
import numpy as np

RANGE = 8.0

def rgbm(c, rng=RANGE):
    c = np.maximum(np.asarray(c, np.float32), 0) / rng
    m = np.clip(np.max(c, axis=1), 1e-6, 1.0)
    m = np.ceil(m * 255) / 255
    rgb = np.clip(c / m[:, None], 0, 1)
    out = np.zeros((len(c), 4), np.uint8)
    out[:, :3] = np.round(rgb * 255); out[:, 3] = np.round(m * 255)
    return out

ROOF_M = ('roof', 'roof_old', 'flat_roof', 'copper', 'lead')
WALL_M = ('wall_plaster', 'wall_brick', 'wall_stone', 'basilica_wall', 'campanile_brick', 'istrian', 'trim', 'marble_white')
WIN_T = (1, 2, 3, 4, 8, 9, 11)

def weld(P, I, attrs, q=0.01):
    """merge vertices with identical quantised positions (and identical attribute rows)."""
    key = np.round(P / q).astype(np.int64)
    rows = np.concatenate([key] + [a.reshape(len(P), -1).astype(np.int64) for a in attrs], axis=1)
    uniq, inv = np.unique(rows, axis=0, return_inverse=True)
    first = np.zeros(len(uniq), np.int64); first[inv[::-1]] = np.arange(len(P))[::-1]
    return first, inv.reshape(-1)[I]

def lite_static(d, irr, mats, hero_range, irrn=None):
    """triangles kept for the far LOD, grouped: roofs+upper walls, ground, hero (each simplified separately in pack.mjs)."""
    names = [m['name'] for m in mats]
    MAT = d['MAT']; I = d['I'].astype(np.int64); P = d['P'].astype(np.float64)
    tm = MAT[I[:, 0]]
    zmin = P[I][:, :, 2].min(1)
    hero = np.zeros(len(I), bool)
    if hero_range is not None and hero_range[1] > hero_range[0]: hero[hero_range[0]:hero_range[1]] = True
    isroof = np.isin(tm, [names.index(n) for n in ROOF_M if n in names])
    iswall = np.isin(tm, [names.index(n) for n in WALL_M if n in names]) & (zmin > 3.0)
    isground = np.isin(tm, [names.index('ground'), names.index('coping'), names.index('portico_floor')])
    groups = [('roof', ~hero & (isroof | iswall), 0.25, 0.25), ('ground', ~hero & isground, 0.4, 0.1), ('hero', hero, 1.2, 0.05)]
    out = []
    for name, sel, err, ratio in groups:
        T = I[sel]
        if not len(T): continue
        # per-material weld so materials never merge across seams; irradiance follows the first vertex
        first, Tn = weld(P[T.reshape(-1)], np.arange(T.size).reshape(-1, 3), [MAT[T.reshape(-1)]])
        vid = T.reshape(-1)[first]
        out.append(dict(name=name, P=P[vid], irr=irr[vid], irrn=(irrn[vid] if irrn is not None else np.zeros_like(irr[vid])), c0=d['C0'][vid], mat=MAT[vid], seed=d['C1'][vid][:, 2], I=Tn.astype(np.uint32), err=err, ratio=ratio))
    return out

def lite_facades(fac, girr_rgbm, girrn_rgbm=None):
    """one quad strip per facade (columns every ~6 m, rows every ~3 m) + procedural window grid params."""
    P = []; UV = []; C0 = []; C1 = []; IR = []; IRN = []; W0 = []; W1 = []; I = []
    for f in fac:
        nu, nz, zs = f['g']; go = f['go']; L = f['L']
        p0 = np.array(f['p0']); p1 = np.array(f['p1']); dr = (p1 - p0) / max(L, 1e-6)
        cols = np.unique(np.r_[np.arange(0, nu, 12), nu - 1])
        rows = np.unique(np.r_[0, (nz - 1) // 2 if nz > 10 else 0, nz - 1])
        zt = f['zt']; zb = f['zb']
        # window grid from the upper-floor openings
        ops = [o for o in f['open'] if o[0] in WIN_T and o[2] > f['zg'] + 2.0]
        w0 = (0, 1, 0, 0); w1 = (0, 1, 0, 0)
        if ops:
            us = np.unique(np.round([o[1] for o in ops], 2)); zz = np.unique(np.round([o[2] for o in ops], 1))
            pitch = float(np.median(np.diff(us))) if len(us) > 1 else 2 * L
            fh = float(np.median(np.diff(zz))) if len(zz) > 1 else 50.0
            ncol = int(round((us.max() - us.min()) / pitch)) + 1 if len(us) > 1 else 1
            nrow = int(round((zz.max() - zz.min()) / fh)) + 1 if len(zz) > 1 else 1
            ww = float(np.median([o[3] for o in ops])); wh = float(np.median([o[4] for o in ops]))
            w0 = (float(us.min()), pitch, ncol, ww); w1 = (float(zz.min()), fh, nrow, wh)
        base = len(P)
        for jj, j in enumerate(rows):
            z = zb if j == 0 else zs + (zt - zs) * j / max(nz - 1, 1)
            for ii, i in enumerate(cols):
                u = L * i / max(nu - 1, 1)
                q = p0 + dr * u
                P.append((q[0], q[1], z)); UV.append((u, z))
                C0.append((*f['tint'], int(round(f['dec'] * 255)))); C1.append((f['mat'], 0, int(round(f['seed'] * 255)), 0))
                IR.append(girr_rgbm[go + j * nu + i]); W0.append(w0); W1.append(w1)
                IRN.append(girrn_rgbm[go + j * nu + i] if girrn_rgbm is not None else (0, 0, 0, 0))
        nc = len(cols)
        for jj in range(len(rows) - 1):
            for ii in range(nc - 1):
                a = base + jj * nc + ii
                I.append((a, a + 1, a + nc + 1)); I.append((a, a + nc + 1, a + nc))
    if not P: return None
    return dict(P=np.array(P), uv=np.array(UV, np.float32), c0=np.array(C0, np.uint8), c1=np.array(C1, np.uint8), irr=np.array(IR, np.uint8), irrn=np.array(IRN, np.uint8),
                w0=np.array(W0, np.float32), w1=np.array(W1, np.float32), I=np.array(I, np.uint32))

def smooth_irr(P, N, irr, radius, mask=None, k=16):
    """denoise a per-vertex bake: average with up to k neighbours within `radius` that face the same way
    (bounded memory: n x k arrays, no all-pairs search)."""
    from scipy.spatial import cKDTree
    idx = np.arange(len(P)) if mask is None else np.nonzero(mask)[0]
    if len(idx) < 2: return irr
    Q = P[idx]; tree = cKDTree(Q)
    out = irr.copy()
    for s0 in range(0, len(idx), 200000):
        sl = slice(s0, min(len(idx), s0 + 200000))
        d, nb = tree.query(Q[sl], k=min(k, len(idx)), distance_upper_bound=radius)
        ok = np.isfinite(d)
        nbc = np.where(ok, nb, 0)
        gi = idx[nbc]                                         # global ids of the neighbours
        me = idx[sl]
        w = np.clip((np.einsum('ij,ikj->ik', N[me], N[gi]) - 0.8) / 0.2, 0, 1) * np.clip(1 - d / radius, 0, 1) * ok
        acc = np.einsum('ik,ikj->ij', w, irr[gi].astype(np.float64))
        out[me] = (acc / np.maximum(w.sum(1, keepdims=True), 1e-9)).astype(irr.dtype)
    return out

def main():
    build, stage = sys.argv[1], sys.argv[2]
    os.makedirs(stage, exist_ok=True)
    tiles = json.load(open(os.path.join(build, 'tiles.json')))
    only = set(sys.argv[3:])
    for t in tiles:
        n = t['name']
        if only and n not in only: continue
        d = np.load(os.path.join(build, n + '.npz'))
        bk = os.path.join(build, n + '.day.npz')
        if not os.path.exists(bk): print('no bake for', n); continue
        b = np.load(bk)
        bn = os.path.join(build, n + '.night.npz')
        bnight = np.load(bn) if os.path.exists(bn) else None
        fac = json.load(open(os.path.join(build, n + '.fac.json')))['fac']
        P = d['P'].astype(np.float64); nv = len(P)
        hdr = {'name': n, 'tile': t['tile'], 'bbox': t['bbox'], 'streams': [], 'nv': int(nv), 'ni': int(d['I'].size)}
        bufs = []; off = 0
        def add(name, arr, stride, kind='v'):
            nonlocal off
            a = np.ascontiguousarray(arr); by = a.tobytes()
            hdr['streams'].append({'name': name, 'off': off, 'len': len(by), 'stride': stride, 'count': int(len(a)) if kind == 'v' else int(a.size), 'kind': kind})
            bufs.append(by); off += len(by)
        if nv:
            lo = P.min(0); hi = P.max(0); ext = float(max(np.max(hi - lo), 1e-3))     # cube: uniform scale keeps normals right
            hdr['qmin'] = lo.tolist(); hdr['qext'] = ext
            q = np.zeros((nv, 4), np.uint16)
            q[:, :3] = np.round((P - lo) / ext * 65535)
            add('pos', q, 8)
            N = d['N']; T = d['T']
            nn = np.zeros((nv, 4), np.int8); nn[:, :3] = np.round(np.clip(N, -1, 1) * 127); nn[:, 3] = 127
            add('nrm', nn, 4)
            tt = np.zeros((nv, 4), np.int8); tt[:, :3] = np.round(np.clip(T[:, :3], -1, 1) * 127); tt[:, 3] = np.where(T[:, 3] < 0, -127, 127)
            add('tan', tt, 4)
            add('uv', d['UV'].astype('<f4'), 8)
            add('c0', d['C0'].astype(np.uint8), 4)
            c1 = d['C1'].astype(np.uint8); cc = np.zeros_like(c1); cc[:, 0] = d['MAT']; cc[:, 1] = c1[:, 0]; cc[:, 2] = c1[:, 2]; cc[:, 3] = c1[:, 3]
            add('c1', cc, 4)
            IRR = b['IRR'].astype(np.float32)
            Nf = d['N'].astype(np.float64)
            hero_v = np.zeros(nv, bool)
            if 'HR' in d and d['HR'][1] > d['HR'][0]:
                hero_v[np.unique(d['I'][d['HR'][0]:d['HR'][1]].ravel())] = True
            IRR = smooth_irr(P, Nf, IRR, 0.35, ~hero_v)          # light denoise everywhere
            IRR = smooth_irr(P, Nf, IRR, 0.9, hero_v)            # interiors lit by small lamps/windows: stronger
            add('irr', rgbm(IRR), 4)
            IRRN = None
            if bnight is not None and 'IRR' in bnight:
                IRRN = bnight['IRR'].astype(np.float32)
                IRRN = smooth_irr(P, Nf, IRRN, 0.35, ~hero_v); IRRN = smooth_irr(P, Nf, IRRN, 0.9, hero_v)
                add('irrn', rgbm(IRRN), 4)
            add('idx', d['I'].astype('<u4').ravel(), 4, kind='i')
            if 'HR' in d and d['HR'][1] > d['HR'][0]: hdr['hr'] = [int(d['HR'][0]), int(d['HR'][1])]
        if 'GIRR' in b and len(b['GIRR']):
            add('girr', rgbm(b['GIRR'].astype(np.float32)), 4)
            if bnight is not None and 'GIRR' in bnight: add('girrn', rgbm(bnight['GIRR'].astype(np.float32)), 4)
        if 'IT' in d and len(d['IT']):
            ni = len(d['IT'])
            ip = np.zeros((ni, 4), '<f4'); ip[:, :3] = d['IP']; ip[:, 3] = d['IY']
            add('ipos', ip, 16)
            sc = np.zeros((ni, 4), np.uint8); sc[:, :3] = np.clip(np.round(d['IS'] * 100), 0, 255); sc[:, 3] = d['IT']
            add('isct', sc, 4)
            ic = np.zeros((ni, 4), np.uint8); ic[:, :3] = d['IC']
            add('icol', ic, 4)
            pirr = b['PIRR'].astype(np.float32) if 'PIRR' in b else np.full((ni, 3), 0.1, np.float32)
            add('iirr', rgbm(pirr), 4)
            if bnight is not None and 'PIRR' in bnight: add('iirrn', rgbm(bnight['PIRR'].astype(np.float32)), 4)
        # compact facade records
        F = []
        for f in fac:
            F.append([f['p0'][0], f['p0'][1], f['p1'][0], f['p1'][1], f['n'][0], f['n'][1], f['zb'], f['zt'], f['zg'], f['L'], round(f['u0'], 3),
                      'BGW'.index(f['cls']), f['mat'], f['tint'], f['dec'], f['sh'], ['rect', 'arch', 'gothic', 'renaiss', 'church'].index(f['st']), f['seed'],
                      f['base'], f['bands'], f['cor'], f['g'], f['go'], f['open']])
        hdr['fac'] = F
        # ---- far LOD (lite): groups for simplification + facade strips
        mats = json.load(open(os.path.join(build, 'materials.json')))['mats']
        hr = d['HR'] if 'HR' in d else None
        lbufs = []; loff = 0; lhdr = {'groups': [], 'streams': []}
        def ladd(name, arr, stride, kind='v', extra=None):
            nonlocal loff
            a = np.ascontiguousarray(arr); by = a.tobytes()
            rec = {'name': name, 'off': loff, 'len': len(by), 'stride': stride, 'count': int(len(a)) if kind == 'v' else int(a.size), 'kind': kind}
            if extra: rec.update(extra)
            lhdr['streams'].append(rec); lbufs.append(by); loff += len(by)
        if nv:
            irr8 = rgbm(IRR); irrn8 = rgbm(IRRN) if IRRN is not None else None
            for g in lite_static(d, irr8, mats, hr, irrn8):
                k = g['name']
                ladd(k + ':pos', g['P'].astype('<f4'), 12)
                ladd(k + ':irr', g['irr'], 4); ladd(k + ':irrn', g['irrn'], 4)
                ladd(k + ':c0', g['c0'].astype(np.uint8), 4)
                c1 = np.zeros((len(g['P']), 4), np.uint8); c1[:, 0] = g['mat']; c1[:, 2] = g['seed']
                ladd(k + ':c1', c1, 4)
                ladd(k + ':idx', g['I'].ravel(), 4, kind='i', extra={'err': g['err'], 'ratio': g['ratio']})
                lhdr['groups'].append(k)
        if fac and 'GIRR' in b and len(b['GIRR']):
            lf = lite_facades(fac, rgbm(b['GIRR'].astype(np.float32)), rgbm(bnight['GIRR'].astype(np.float32)) if (bnight is not None and 'GIRR' in bnight) else None)
            if lf is not None:
                ladd('fac:pos', lf['P'].astype('<f4'), 12); ladd('fac:uv', lf['uv'], 8); ladd('fac:c0', lf['c0'], 4); ladd('fac:c1', lf['c1'], 4)
                ladd('fac:irr', lf['irr'], 4); ladd('fac:irrn', lf['irrn'], 4); ladd('fac:w0', lf['w0'], 16); ladd('fac:w1', lf['w1'], 16); ladd('fac:idx', lf['I'].ravel(), 4, kind='i')
                lhdr['groups'].append('fac')
        open(os.path.join(stage, n + '.lite.raw'), 'wb').write(b''.join(lbufs))
        json.dump(lhdr, open(os.path.join(stage, n + '.lite.json'), 'w'))
        wp = os.path.join(build, n + '.walk.png')
        if os.path.exists(wp):
            import shutil; shutil.copy(wp, os.path.join(stage, n + '.walk.png'))
        open(os.path.join(stage, n + '.raw'), 'wb').write(b''.join(bufs))
        json.dump(hdr, open(os.path.join(stage, n + '.json'), 'w'), separators=(',', ':'))
        print(n, nv, 'verts', len(F), 'facades', off // 1024, 'KB raw', flush=True)

if __name__ == '__main__':
    main()
