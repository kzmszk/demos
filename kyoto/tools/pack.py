"""Quantise tiles into raw streams (venv python):  python pack.py BUILD_DIR STAGE_DIR [tile names...]
Groups per tile: 'b' buildings & structures (city program), 'g' ground (terrain + bridge decks; ground program),
'w' water.  Streams: pos u16x4 (tile cube), nrm s8x4, uv f32x2, c0 u8x4, c1 u8x4 (x = material), irr u8x4
(sqrt-encoded irradiance rgb / IRR_MAX, a = sun visibility), idx u32.  Far LOD ('lite'): buildings + a coarse terrain,
simplified in pack.mjs.  pack.mjs then meshopt-encodes and gzips."""
import sys, os, json, math, shutil
import numpy as np

IRR_MAX = 4.0

def enc_irr(irr, sun):
    q = np.sqrt(np.clip(np.asarray(irr, np.float32) / IRR_MAX, 0, 1))
    out = np.zeros((len(q), 4), np.uint8)
    out[:, :3] = np.round(q * 255); out[:, 3] = np.round(np.clip(sun, 0, 1) * 255)
    return out

def smooth_irr(P, N, irr, radius, k=12):
    from scipy.spatial import cKDTree
    if len(P) < 2: return irr
    tree = cKDTree(P); out = irr.copy()
    for s0 in range(0, len(P), 200000):
        sl = slice(s0, min(len(P), s0 + 200000))
        d, nb = tree.query(P[sl], k=min(k, len(P)), distance_upper_bound=radius)
        ok = np.isfinite(d); nbc = np.where(ok, nb, 0)
        w = np.clip((np.einsum('ij,ikj->ik', N[sl], N[nbc]) - 0.8) / 0.2, 0, 1) * np.clip(1 - d / radius, 0, 1) * ok
        acc = np.einsum('ik,ikj->ij', w, irr[nbc].astype(np.float64))
        out[sl] = (acc / np.maximum(w.sum(1, keepdims=True), 1e-9)).astype(irr.dtype)
    return out

def fake_irr(N):
    """before a bake: sky light by facing (for previews only)"""
    up = np.clip(N[:, 2] * 0.5 + 0.5, 0, 1)
    sky = np.array([0.55, 0.62, 0.75]) * 0.9
    irr = (0.25 + 0.75 * up)[:, None] * sky
    return irr, np.full(len(N), 0.8)

FLOW = '/home/kazu/work/kyoto-assets/build/flow.npz'
FLOWT = None

def main():
    import multiprocessing as mp
    args = [a for a in sys.argv[1:] if not a.startswith('-j')]
    jn = int(([a[2:] for a in sys.argv[1:] if a.startswith('-j')] or ['1'])[0])
    build, stage = args[0], args[1]
    os.makedirs(stage, exist_ok=True)
    tiles = json.load(open(os.path.join(build, 'tiles.json')))
    only = set(args[2:])
    todo = [t for t in tiles if not only or t['name'] in only]
    if jn > 1:
        with mp.get_context('fork').Pool(jn, maxtasksperchild=50) as pool:
            for _ in pool.imap_unordered(one, [(t, build, stage) for t in todo], chunksize=2): pass
    else:
        for t in todo: one((t, build, stage))

def one(job):
    t, build, stage = job
    mats = json.load(open(os.path.join(build, 'materials.json')))['mats']
    kinds = np.array([m['kind'] for m in mats])
    if True:
        n = t['name']
        d = np.load(os.path.join(build, n + '.npz'))
        P = d['P'].astype(np.float64); N = d['N'].astype(np.float32); I = d['I'].astype(np.int64)
        nv = len(P)
        bk = os.path.join(build, n + '.bake.npz')
        if os.path.exists(bk):
            b = np.load(bk); IRR = b['IRR'].astype(np.float32); SUN = b['SUN'].astype(np.float32)
            IRR = smooth_irr(P, N.astype(np.float64), IRR, 0.4)
        else:
            IRR, SUN = fake_irr(N)
        SUN = np.asarray(SUN, np.float32)
        # street furniture (not baked): light from the nearest baked vertices facing the same way
        pp = os.path.join(build, n + '.props.npz')
        MAT = d['MAT']; UVa = d['UV']; C0a = d['C0']; C1a = d['C1']
        if os.path.exists(pp):
            Q = np.load(pp)
            if len(Q['I']):
                from scipy.spatial import cKDTree
                QP = Q['P'].astype(np.float64); QN = Q['N'].astype(np.float64)
                tree = cKDTree(P)
                dd, nb = tree.query(QP, k=10, distance_upper_bound=8.0)
                ok = np.isfinite(dd); nbc = np.where(ok, nb, 0)
                wgt = np.clip(np.einsum('ij,ikj->ik', QN, N[nbc].astype(np.float64)) + 0.3, 0.05, None) * ok / (dd + 0.5)
                ws = wgt.sum(1, keepdims=True)
                qi = (wgt[..., None] * IRR[nbc]).sum(1) / np.maximum(ws, 1e-9); qs = (wgt * SUN[nbc]).sum(1) / np.maximum(ws[:, 0], 1e-9)
                miss = ws[:, 0] < 1e-6
                if miss.any():
                    _, n1 = tree.query(QP[miss], k=1); qi[miss] = IRR[n1]; qs[miss] = SUN[n1]
                I = np.concatenate([I, Q['I'].astype(np.int64) + nv]); P = np.concatenate([P, QP]); N = np.concatenate([N, Q['N'].astype(np.float32)])
                MAT = np.concatenate([MAT, Q['MAT']]); UVa = np.concatenate([UVa, Q['UV']]); C0a = np.concatenate([C0a, Q['C0']]); C1a = np.concatenate([C1a, Q['C1']])
                IRR = np.concatenate([IRR, qi.astype(IRR.dtype)]); SUN = np.concatenate([SUN, qs.astype(np.float32)])
                nv = len(P)
        # hero ground: its natural surfaces (moss, gravel, sand, soil, forest, pond beds) go into the 0.5 m surface raster
        # and the triangles use it, with soft jittered borders in the shader; the per-vertex id, rounded per pixel, drew
        # the borders as saw teeth along the triangles.  Decks and paving keep their vertex ids.
        # the surface raster from its .surf.png (a --walk-only --surf rebuild rewrites only that), else the npz copy
        sp_ = os.path.join(build, n + '.surf.png')
        if os.path.exists(sp_):
            from PIL import Image
            Sr = np.asarray(Image.open(sp_))[::-1].copy()
        else: Sr = d['SURF'].copy() if 'SURF' in d else None
        surf_new = False
        if Sr is not None and 'HR' in d and d['HR'][1] > d['HR'][0]:
            SURFN = [s_['name'] for s_ in json.load(open(os.path.join(build, 'materials.json')))['surf']]
            NAT = [SURFN.index(k) for k in ('soil', 'grass', 'moss', 'forest', 'riverbed', 'sand', 'gravel', 'farm')]
            hr = d['HR']; ti = np.arange(hr[0], hr[1]); T = I[ti]
            e1 = P[T[:, 1]] - P[T[:, 0]]; e2 = P[T[:, 2]] - P[T[:, 0]]; cr = np.cross(e1, e2)
            nz = np.abs(cr[:, 2]) / np.maximum(np.linalg.norm(cr, axis=1), 1e-12)
            cand = (kinds[MAT[T[:, 0]]] == 'ground') & np.isin(C1a[T, 3], NAT).all(1) & (nz > 0.5)
            if cand.any():
                from PIL import Image, ImageDraw
                from scipy.spatial import cKDTree
                ci = ti[cand]; bb = d['BBOX']; res = (bb[2] - bb[0]) / Sr.shape[1]
                m = Image.new('L', (Sr.shape[1], Sr.shape[0]), 0); dr = ImageDraw.Draw(m)
                Q = (P[I[ci]][:, :, :2] - bb[:2]) / res
                for tri in Q: dr.polygon([tuple(v) for v in tri], fill=1)
                mk = np.asarray(m, bool)
                yy, xx = np.nonzero(mk)
                vc = np.unique(I[ci].ravel())
                _, nn = cKDTree(P[vc, :2]).query(np.c_[(xx + 0.5) * res + bb[0], (yy + 0.5) * res + bb[1]], k=1)
                Sr[yy, xx] = C1a[vc[nn], 3]; surf_new = True
                # vertices shared with other triangles are split, so no triangle interpolates between an id and 0
                other = np.ones(len(I), bool); other[ci] = False
                vo = np.zeros(nv, bool); vo[np.unique(I[other].ravel())] = True
                sh = vc[vo[vc]]
                if len(sh):
                    remap = np.arange(nv); remap[sh] = nv + np.arange(len(sh))
                    P = np.concatenate([P, P[sh]]); N = np.concatenate([N, N[sh]]); MAT = np.concatenate([MAT, MAT[sh]])
                    UVa = np.concatenate([UVa, UVa[sh]]); C0a = np.concatenate([C0a, C0a[sh]]); C1a = np.concatenate([C1a, C1a[sh]])
                    IRR = np.concatenate([IRR, IRR[sh]]); SUN = np.concatenate([SUN, SUN[sh]])
                    I[ci] = remap[I[ci]]; nv = len(P)
                C1a = C1a.copy(); C1a[np.unique(I[ci].ravel()), 3] = 0
        HRn = np.array(d['HR']) if 'HR' in d else None
        # where a hero has its own ground, the generic terrain under it goes (it z-fought, or poked through where the
        # DEM had a bump: a 5 m spike before Tōfuku-ji's Sanmon); only triangles wholly inside the hero ground's plan
        if 'HR' in d and d['HR'][1] > d['HR'][0]:
            from PIL import Image, ImageDraw
            from scipy import ndimage
            hr = d['HR']; T = I[hr[0]:hr[1]]
            e1 = P[T[:, 1]] - P[T[:, 0]]; e2 = P[T[:, 2]] - P[T[:, 0]]; cr = np.cross(e1, e2)
            nz = np.abs(cr[:, 2]) / np.maximum(np.linalg.norm(cr, axis=1), 1e-12)
            hg = T[(kinds[MAT[T[:, 0]]] == 'ground') & (nz > 0.5)]
            if len(hg):
                bb = t['bbox']; R = 1.0; n_ = int(round((bb[2] - bb[0]) / R)) + 2
                m = Image.new('L', (n_, n_), 0); dr = ImageDraw.Draw(m)
                for tri in (P[hg][:, :, :2] - np.array([bb[0] - R, bb[1] - R])) / R: dr.polygon([tuple(v) for v in tri], fill=1)
                mk = ndimage.binary_erosion(np.asarray(m, bool), iterations=1)
                gen_ = np.ones(len(I), bool); gen_[hr[0]:hr[1]] = False
                gg = np.where(gen_ & (kinds[MAT[I[:, 0]]] == 'ground'))[0]
                Q = np.concatenate([P[I[gg]][:, :, :2], P[I[gg]][:, :, :2].mean(1, keepdims=True)], 1)
                qi = np.clip(((Q - np.array([bb[0] - R, bb[1] - R])) / R).astype(int), 0, n_ - 1)
                inside = mk[qi[..., 1], qi[..., 0]].all(1)
                if inside.any():
                    k_ = int((gg[inside] < hr[0]).sum()); I = np.delete(I, gg[inside], axis=0)
                    HRn = np.array([hr[0] - k_, hr[1] - k_])
        # the heroes' water is still (garden ponds): flagged in c1.y for a calm surface in the shader
        if HRn is not None and HRn[1] > HRn[0]:
            T = I[HRn[0]:HRn[1]]
            wv = np.unique(T[kinds[MAT[T[:, 0]]] == 'water'].ravel())
            if len(wv): C1a = C1a.copy(); C1a[wv, 1] = 255
        # running water: the flow of the nearest river line (gen/flowfield.py) in c0: direction (x, y), speed / 2 m/s, 255
        Tw_ = I[kinds[MAT[I[:, 0]]] == 'water']
        if len(Tw_) and os.path.exists(FLOW):
            from scipy.spatial import cKDTree
            global FLOWT
            if FLOWT is None:
                F = np.load(FLOW); FLOWT = (cKDTree(F['P']), F['D'], F['S'])
            wv = np.unique(Tw_.ravel()); wv = wv[C1a[wv, 1] < 128]
            if len(wv):
                dd, kk = FLOWT[0].query(P[wv, :2], k=4, distance_upper_bound=90.0)
                ok = np.isfinite(dd); kk = np.where(ok, kk, 0)
                wgt = ok / np.maximum(dd, 1.0)
                Dv = (FLOWT[1][kk] * wgt[..., None]).sum(1); Sv = (FLOWT[2][kk] * wgt).sum(1) / np.maximum(wgt.sum(1), 1e-9)
                Dv /= np.maximum(np.linalg.norm(Dv, axis=1, keepdims=True), 1e-9)
                has = ok.any(1)
                C0a = C0a.copy()
                C0a[wv, 0] = np.round(128 + 127 * Dv[:, 0]); C0a[wv, 1] = np.round(128 + 127 * Dv[:, 1])
                C0a[wv, 2] = np.round(np.clip(Sv / 2.0, 0, 1) * 255); C0a[wv, 3] = np.where(has, 255, 0)
        irr8 = enc_irr(IRR, SUN)
        tk = kinds[MAT[I[:, 0]]]
        groups = {'g': np.isin(tk, ['ground']), 'w': tk == 'water'}
        groups['b'] = ~(groups['g'] | groups['w'])
        hdr = {'name': n, 'tile': t['tile'], 'bbox': t['bbox'], 'groups': []}
        bufs = []; off = 0
        lo = P.min(0) if nv else np.zeros(3); hi = P.max(0) if nv else np.ones(3)
        ext = float(max(np.max(hi - lo), 1e-3))
        hdr['qmin'] = lo.tolist(); hdr['qext'] = ext
        for gname, sel in groups.items():
            T = I[sel]
            if not len(T): continue
            vid, inv = np.unique(T.ravel(), return_inverse=True)
            Tn = inv.reshape(-1, 3).astype(np.uint32)
            g = {'name': gname, 'nv': int(len(vid)), 'ni': int(Tn.size), 'streams': []}
            def add(name, arr, stride, kind='v'):
                nonlocal off
                a = np.ascontiguousarray(arr); by = a.tobytes()
                g['streams'].append({'name': name, 'off': off, 'len': len(by), 'stride': stride, 'count': int(len(a)) if kind == 'v' else int(a.size), 'kind': kind})
                bufs.append(by); off += len(by)
            q = np.zeros((len(vid), 4), np.uint16); q[:, :3] = np.round((P[vid] - lo) / ext * 65535)
            add('pos', q, 8)
            nn = np.zeros((len(vid), 4), np.int8); nn[:, :3] = np.round(np.clip(N[vid], -1, 1) * 127); nn[:, 3] = 127
            add('nrm', nn, 4)
            add('uv', (np.round(UVa[vid].astype(np.float64) * 128) / 128).astype('<f4'), 8)
            add('c0', C0a[vid].astype(np.uint8), 4)
            c1 = C1a[vid].astype(np.uint8).copy(); c1[:, 0] = MAT[vid]
            add('c1', c1, 4)
            add('irr', irr8[vid], 4)
            add('idx', Tn.ravel(), 4, kind='i')
            hdr['groups'].append(g)
        # far LOD: the coarse buildings + terrain from build_tiles (.lite.npz); light taken from the nearest baked vertices
        lb = []; loff = 0; lhdr = {'streams': []}
        def ladd(name, arr, stride, kind='v', extra=None):
            nonlocal loff
            a = np.ascontiguousarray(arr); by = a.tobytes()
            rec = {'name': name, 'off': loff, 'len': len(by), 'stride': stride, 'count': int(len(a)) if kind == 'v' else int(a.size), 'kind': kind}
            if extra: rec.update(extra)
            lhdr['streams'].append(rec); lb.append(by); loff += len(by)
        lp = os.path.join(build, n + '.lite.npz')
        if os.path.exists(lp):
            from scipy.spatial import cKDTree
            L = np.load(lp)
            LP = L['P'].astype(np.float64); LN = L['N'].astype(np.float64); LM = L['MAT']; LI = L['I'].astype(np.int64)
            tree = cKDTree(P)
            dd, nb = tree.query(LP, k=12, distance_upper_bound=6.0)
            ok = np.isfinite(dd); nbc = np.where(ok, nb, 0)
            w = np.clip(np.einsum('ij,ikj->ik', LN, N[nbc].astype(np.float64)) - 0.6, 0, None) * ok / (dd + 0.3)
            ws = w.sum(1, keepdims=True)
            li = (w[..., None] * IRR[nbc]).sum(1) / np.maximum(ws, 1e-9); ls = (w * SUN[nbc]).sum(1) / np.maximum(ws[:, 0], 1e-9)
            d1, n1 = tree.query(LP, k=1)
            miss = ws[:, 0] < 1e-6
            li[miss] = IRR[n1[miss]]; ls[miss] = SUN[n1[miss]]
            LC0 = L['C0'].copy()
            gl = kinds[LM] == 'ground'
            if Sr is not None and gl.any():
                SA = np.array([s_['albedo'] for s_ in json.load(open(os.path.join(build, 'materials.json')))['surf']], np.float32)
                bb = d['BBOX']; res = (bb[2] - bb[0]) / Sr.shape[1]
                ix = np.clip(((LP[gl, 0] - bb[0]) / res).astype(int), 0, Sr.shape[1] - 1); iy = np.clip(((LP[gl, 1] - bb[1]) / res).astype(int), 0, Sr.shape[0] - 1)
                sid = Sr[iy, ix]
                lin = SA[sid]; srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
                LC0[gl, :3] = np.round(np.clip(srgb, 0, 1) * 255); LC0[gl, 3] = np.isin(sid, [1, 2]) * 255
            c1 = np.zeros((len(LP), 4), np.uint8); c1[:, 0] = LM; c1[:, 2] = L['C1'][:, 2]; c1[:, 1] = LC0[:, 3] // 255
            if Sr is not None and gl.any(): c1[gl, 3] = sid                    # the ground's surface id (forest -> canopy far away)
            # the water surface (the coarse terrain has a hole there): the full mesh's water triangles, light from the bake
            Tw = I[groups['w']]
            if len(Tw):
                vw, iw = np.unique(Tw.ravel(), return_inverse=True)
                nl0 = len(LP)
                LP = np.concatenate([LP, P[vw].astype(np.float64)]); LI = np.concatenate([LI, iw.reshape(-1, 3) + nl0])
                cw = np.zeros((len(vw), 4), np.uint8); cw[:, 0] = MAT[vw]
                c1 = np.concatenate([c1, cw]); LC0 = np.concatenate([LC0, np.full((len(vw), 4), 255, LC0.dtype)])
                li = np.concatenate([li, IRR[vw].astype(li.dtype)]); ls = np.concatenate([ls, SUN[vw].astype(ls.dtype)])
            ladd('l:pos', LP.astype('<f4'), 12)
            ladd('l:c0', LC0.astype(np.uint8), 4)
            ladd('l:c1', c1, 4)
            ladd('l:irr', enc_irr(li, ls), 4)
            ladd('l:idx', LI.astype('<u4').ravel(), 4, kind='i', extra={'err': 0.0, 'ratio': 1.0})
        # heroes in the far LOD: their non-detail triangles, simplified in pack.mjs (sloppy)
        if HRn is not None and HRn[1] > HRn[0]:
            hr = HRn; T = I[hr[0]:hr[1]]
            if 'HD' in d and len(d['HD']) == len(T): T = T[d['HD'] == 0]
            if len(T):
                vid, inv = np.unique(T.ravel(), return_inverse=True)
                c1 = np.zeros((len(vid), 4), np.uint8); c1[:, 0] = MAT[vid]; c1[:, 2] = C1a[vid][:, 2]
                ladd('h:pos', P[vid].astype('<f4'), 12); ladd('h:c0', C0a[vid].astype(np.uint8), 4); ladd('h:c1', c1, 4); ladd('h:irr', irr8[vid], 4)
                ladd('h:idx', inv.astype('<u4'), 4, kind='i', extra={'err': 0.5, 'ratio': 0.18, 'sloppy': 1})
        # trees (impostors far away, full templates near): with the far LOD, which is loaded wherever the tile is
        tp_ = os.path.join(build, n + '.trees.npy')
        if os.path.exists(tp_):
            TRE = np.load(tp_)
            if len(TRE):
                from scipy.spatial import cKDTree
                # light from the open ground at the tree's foot: any upward-facing surface but water (generic ground is
                # cut away on the hero sites, and its nearest vertex could lie under a bridge or a roof: black trees),
                # height weighted so a deck or a roof above does not count, averaged over a few vertices
                wid = [k for k, m in enumerate(mats) if m['name'] == 'water']
                cand = np.where((N[:nv, 2] > 0.6) & ~np.isin(MAT[:nv], wid))[0]
                if len(cand) < 8: cand = np.unique(I[groups['g']].ravel()) if groups['g'].any() else np.arange(nv)
                SC = np.array([1.0, 1.0, 3.0])
                kt = cKDTree(P[cand] * SC)
                kk = min(6, len(cand))
                _, nn = kt.query(np.c_[TRE[:, 2:4], TRE[:, 4] + 0.3] * SC, k=kk)
                gi = cand[nn.reshape(len(TRE), kk)]
                tirr = enc_irr(IRR[gi].mean(1) * 1.1, SUN[gi].mean(1))
                tpos = np.zeros((len(TRE), 4), '<f4'); tpos[:, :3] = TRE[:, 2:5]; tpos[:, 3] = TRE[:, 5]
                tq = np.zeros((len(TRE), 4), np.uint8); tq[:, 0] = TRE[:, 0]; tq[:, 1] = TRE[:, 1]
                tq[:, 2] = np.round(TRE[:, 6] / (2 * math.pi) * 255) % 256; tq[:, 3] = (np.arange(len(TRE)) * 97 + int(TRE[0, 2] * 7)) % 256
                ladd('t:pos', tpos, 16); ladd('t:q', tq, 4); ladd('t:irr', tirr, 4)
        open(os.path.join(stage, n + '.lite.raw'), 'wb').write(b''.join(lb))
        json.dump(lhdr, open(os.path.join(stage, n + '.lite.json'), 'w'))
        for ext_ in ('.walk.png', '.surf.png'):
            p = os.path.join(build, n + ext_)
            if ext_ == '.surf.png' and surf_new:
                from PIL import Image
                Image.fromarray(Sr[::-1], 'L').save(os.path.join(stage, n + ext_), optimize=True)
            elif os.path.exists(p): shutil.copy(p, os.path.join(stage, n + ext_))
        open(os.path.join(stage, n + '.raw'), 'wb').write(b''.join(bufs))
        hdr['z'] = t.get('z', [float(lo[2]), float(hi[2])])
        json.dump(hdr, open(os.path.join(stage, n + '.json'), 'w'), separators=(',', ':'))
        print(n, nv, 'verts', off // 1024, 'KB raw', flush=True)
        return n

if __name__ == '__main__':
    main()
