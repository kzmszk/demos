"""Pack the tree templates for the viewer:  python -m gen.treepack OUT_DIR (public/data) TEX_DIR (public/tex)
trees.bin + trees.json: per species x variant x LOD: wood (bark) and leaves (cards) meshes.
Vertex layout (28 bytes): pos f32x3, nrm s8x4, uv f32x2, a u8x4 (wood: wind,0,0,0; leaves: outer, rnd, height, cell).
trees_imp.png: impostors (orthographic side views) in the leaf-atlas convention (R lum, G outer, B bark, A coverage):
cells 8 x 4 of 256 x 512 px: row 0-1 autumn/evergreen crowns per species, row 2-3 winter (deciduous bare)."""
import os, sys, json, math
import numpy as np
from PIL import Image, ImageDraw
from .treegen import NAMES, SPECIES, make

NVAR = 3
ATLAS = '/home/kazu/work/kyoto-assets/build/trees/leaves.png'

def pack_mesh(m, kind):
    P = m['P']; n = len(P)
    if n == 0: return None
    v = np.zeros(n, dtype=[('p', '<f4', 3), ('n', 'i1', 4), ('uv', '<f4', 2), ('a', 'u1', 4)])
    v['p'] = P
    v['n'][:, :3] = np.round(np.clip(m['N'], -1, 1) * 127); v['n'][:, 3] = 127
    v['uv'] = m['UV']
    if kind == 'wood':
        v['a'][:, 0] = np.round(np.clip(m['W'], 0, 1) * 255)
    else:
        K = m['K']
        v['a'][:, 0] = np.round(np.clip(K[:, 0], 0, 1) * 255); v['a'][:, 1] = np.round(np.clip(K[:, 1], 0, 1) * 255)
        v['a'][:, 2] = np.round(np.clip(K[:, 2], 0, 1) * 255); v['a'][:, 3] = K[:, 3].astype(np.uint8)
    return v.tobytes(), np.asarray(m['I'], np.uint32).ravel()

def impostor(t, atlas, W=256, H=512, season='autumn', deciduous=0):
    """software render of a template seen from the side (looking along +y), back to front"""
    S = 2; Wc, Hc = W * S, H * S
    P = t['leaves']['P']; Pw = t['wood']['P']
    allp = np.concatenate([P, Pw]) if len(P) else Pw
    xmin, xmax = allp[:, 0].min(), allp[:, 0].max(); zmax = allp[:, 2].max()
    half = max(abs(xmin), abs(xmax)) * 1.04 + 0.1
    sc = min(Wc / (2 * half), Hc / (zmax * 1.02 + 0.1))
    to = lambda x, z: ((x * sc) + Wc / 2, Hc - z * sc)
    img = Image.new('RGBA', (Wc, Hc), (0, 0, 0, 0))
    # wood: tubes drawn as thick quads per segment, far side first
    wd = t['wood']; I = wd['I'].reshape(-1, 3)
    dr = ImageDraw.Draw(img)
    order = np.argsort(-wd['P'][I].mean(1)[:, 1])
    for k in order:
        tri = [to(wd['P'][v][0], wd['P'][v][2]) for v in I[k]]
        dr.polygon(tri, fill=(70, 0, 255, 255))
    if season == 'autumn' or not deciduous:
        lf = t['leaves']
        Q = lf['P'].reshape(-1, 4, 3); UV = lf['UV'].reshape(-1, 4, 2).copy(); K = lf['K'].reshape(-1, 4, 4)
        if season == 'winter':
            pass
    elif True:
        # winter, deciduous: the same cards show bare twigs (atlas cell 9)
        lf = t['leaves']
        Q = lf['P'].reshape(-1, 4, 3); UV = lf['UV'].reshape(-1, 4, 2).copy(); K = lf['K'].reshape(-1, 4, 4)
        cell = K[:, 0, 3].astype(int)
        UV[..., 0] += ((9 % 4) - (cell % 4))[:, None] / 4.0; UV[..., 1] += ((9 // 4) - (cell // 4))[:, None] / 4.0
    if True:
        A = atlas
        order = np.argsort(-Q.mean(1)[:, 1])
        for k in order:
            q = Q[k]; uv = UV[k]
            d0 = np.array(to(q[0, 0], q[0, 2])); d1 = np.array(to(q[1, 0], q[1, 2])); d3 = np.array(to(q[3, 0], q[3, 2]))
            ex = d1 - d0; ey = d3 - d0
            det = ex[0] * ey[1] - ex[1] * ey[0]
            if abs(det) < 1.0: continue
            # destination pixel -> (s, t) in the card -> atlas pixel
            u0, v0 = uv[0]; u1 = uv[1][0]; v3 = uv[3][1]
            aw, ah = A.size
            inv = np.array([[ey[1], -ey[0]], [-ex[1], ex[0]]]) / det
            # affine: src = S0 + s * (u1-u0)*aw  (x) ; t * (v3-v0)*ah (y), with (s,t) = inv @ (dst - d0)
            ax = (u1 - u0) * aw; ay = (v3 - v0) * ah
            # src_x = u0*aw + ax * (inv[0,0]*(X - d0x) + inv[0,1]*(Y - d0y)); src_y = (1 - v0)*ah ... atlas v points up -> image rows down
            xs = [d0[0], d1[0], d3[0], d1[0] + ey[0]]; ys = [d0[1], d1[1], d3[1], d1[1] + ey[1]]
            bx0, by0 = int(max(0, min(xs))), int(max(0, min(ys))); bx1, by1 = int(min(Wc, max(xs) + 1)), int(min(Hc, max(ys) + 1))
            if bx1 <= bx0 or by1 <= by0: continue
            sx0 = u0 * aw; sy0 = (1 - v0) * ah
            a_ = ax * inv[0, 0]; b_ = ax * inv[0, 1]; c_ = sx0 + ax * (inv[0, 0] * (bx0 - d0[0]) + inv[0, 1] * (by0 - d0[1]))
            d_ = -ay * inv[1, 0]; e_ = -ay * inv[1, 1]; f_ = sy0 - ay * (inv[1, 0] * (bx0 - d0[0]) + inv[1, 1] * (by0 - d0[1]))
            patch = A.transform((bx1 - bx0, by1 - by0), Image.AFFINE, (a_, b_, c_, d_, e_, f_), resample=Image.BILINEAR)
            img.alpha_composite(patch, (bx0, by0))
    img = img.resize((W, H), Image.LANCZOS)
    return img, dict(half=float(half), h=float(zmax * 1.02 + 0.1))

def main(out, texdir):
    os.makedirs(out, exist_ok=True); os.makedirs(texdir, exist_ok=True)
    atlas = Image.open(ATLAS).convert('RGBA')
    bins = []; off = 0; ioff = 0; recs = []
    imp = Image.new('RGBA', (256 * 8, 512 * 4), (0, 0, 0, 0)); impm = []
    for si, n in enumerate(NAMES):
        sp = SPECIES[n]
        for var in range(NVAR):
            rec = dict(species=n, si=si, var=var, deciduous=sp['deciduous'])
            for lod in (0, 1):
                t = make(n, 101 + var * 17, lod)
                rec['H'] = t['H']
                for part in ('wood', 'leaves'):
                    pm = pack_mesh(t[part], part)
                    if pm is None: continue
                    vb, ib = pm
                    rec[f'{part}{lod}'] = dict(voff=off, vcount=len(vb) // 28, ioff=None, icount=int(len(ib)))
                    bins.append(vb); off += len(vb)
                    rec[f'{part}{lod}']['ioff'] = off; bins.append(ib.tobytes()); off += ib.nbytes
                if lod == 0 and var == 0:
                    for season, row in (('autumn', 0), ('winter', 2)):
                        im, meta = impostor(t, atlas, season=season, deciduous=sp['deciduous'])
                        cx, cy = si % 8, row + si // 8
                        imp.paste(im, (cx * 256, cy * 512))
                        if season == 'autumn': impm.append(dict(cell=[cx, cy], wcell=[cx, row + si // 8 + 0], **meta))
            recs.append(rec)
        print(n, 'done', flush=True)
    for k, m in enumerate(impm):
        m['wcell'] = [k % 8, 2 + k // 8]
    open(os.path.join(out, 'trees.bin'), 'wb').write(b''.join(bins))
    json.dump(dict(names=NAMES, templates=recs, imp=impm, stride=28), open(os.path.join(out, 'trees.json'), 'w'))
    imp.save(os.path.join(texdir, 'trees_imp.png'), optimize=True)
    import shutil
    shutil.copy(ATLAS, os.path.join(texdir, 'leaves.png')); shutil.copy(ATLAS.replace('leaves.png', 'leaves_nrm.png'), os.path.join(texdir, 'leaves_nrm.png'))
    print('trees.bin', off // 1024, 'KB')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
