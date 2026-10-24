"""Fold the hand-built districts (public/hero/<d>/, made in Blender: see tools/hero/BRIEF.md) into the game's data.
  python -m gen.hero_collide      -> public/hero/<d>/field.bin, public/data/heroes.json, merges into ASSETS/build/roof.npz

Run after gen.city (which leaves the districts' buildings out, see exclude.json) and before gen.roofpack and gen.foot.
For every district with a near.glb and a collide.obj:
  field.bin  the collision proxy seen from above at 0.5 m: the top of the highest surface (int16, 0.1 m, T.P.;
             -32768 = nothing there, the terrain counts). The walker stands on it inside the district.
  roof.npz   the 4 m roof raster gets the district's raised surfaces (more than 1.5 m above the ground) for flight
             collision and roof landings.
heroes.json lists the districts the viewer loads (box, origin, spawns, labels, the LOD files present)."""
import os, json, gzip, struct
import numpy as np
from .frame import ASSETS, PUBLIC
from .hero_src import DISTRICTS, origin, ground_grid, ground_at

RES = 0.5


def read_obj(path):
    V = []; F = []
    for line in open(path):
        if line.startswith('v '):
            V.append([float(t) for t in line.split()[1:4]])
        elif line.startswith('f '):
            idx = [int(t.split('/')[0]) for t in line.split()[1:]]
            idx = [i - 1 if i > 0 else len(V) + i for i in idx]
            for k in range(1, len(idx) - 1): F.append((idx[0], idx[k], idx[k + 1]))
    return np.asarray(V, np.float64), np.asarray(F, np.int64)


def rasterise(V, F, x0, y0, w, h):
    """max z of the triangles over a grid of cell centres (x0 + (i + .5) RES); vertical faces through their edges"""
    Z = np.full((h, w), -np.inf)
    T = V[F]                                            # (m, 3, 3)
    for t in T:
        xs, ys = t[:, 0], t[:, 1]
        i0 = max(0, int(np.floor((xs.min() - x0) / RES - 0.5))); i1 = min(w - 1, int(np.ceil((xs.max() - x0) / RES - 0.5)))
        j0 = max(0, int(np.floor((ys.min() - y0) / RES - 0.5))); j1 = min(h - 1, int(np.ceil((ys.max() - y0) / RES - 0.5)))
        if i1 < i0 or j1 < j0: continue
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) > 1e-9:
            gx = x0 + (np.arange(i0, i1 + 1) + 0.5) * RES; gy = y0 + (np.arange(j0, j1 + 1) + 0.5) * RES
            X, Y = np.meshgrid(gx, gy)
            l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / det
            l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / det
            l3 = 1 - l1 - l2
            ins = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
            if ins.any():
                z = l1 * az + l2 * bz + l3 * cz
                sub = Z[j0:j1 + 1, i0:i1 + 1]
                np.maximum(sub, np.where(ins, z, -np.inf), out=sub)
        # the edges, so walls without a top (and slivers) still stop you
        for (p, q) in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            L = np.hypot(q[0] - p[0], q[1] - p[1]); n = max(2, int(L / (RES * 0.5)) + 1)
            s = np.linspace(0, 1, n); px = p[0] + (q[0] - p[0]) * s; py = p[1] + (q[1] - p[1]) * s; pz = p[2] + (q[2] - p[2]) * s
            ii = np.floor((px - x0) / RES).astype(int); jj = np.floor((py - y0) / RES).astype(int)
            ok = (ii >= 0) & (ii < w) & (jj >= 0) & (jj < h)
            np.maximum.at(Z, (jj[ok], ii[ok]), pz[ok])
    return Z


def main():
    r, gh = ground_grid()
    out = []
    rz = np.load(os.path.join(ASSETS, 'build', 'roof.npz')); roof = rz['roof'].copy(); rx0 = float(rz['x0']); ry0 = float(rz['y0']); rres = float(rz['res'])
    for name, d in DISTRICTS.items():
        base = os.path.join(PUBLIC, 'hero', name)
        if not (os.path.exists(os.path.join(base, 'near.glb')) and os.path.exists(os.path.join(base, 'collide.obj'))):
            print(name, 'not built yet'); continue
        ox, oy = origin(d['box']); bx0, by0, bx1, by1 = d['box']
        meta = json.load(open(os.path.join(base, 'hero.json')))
        V, F = read_obj(os.path.join(base, 'collide.obj')); V[:, 0] += ox; V[:, 1] += oy
        # the field covers the box and whatever of the proxy reaches out of it, on the 4 m grid of the roof raster
        fx0 = np.floor(min(bx0, V[:, 0].min()) / 4) * 4 - 4; fy0 = np.floor(min(by0, V[:, 1].min()) / 4) * 4 - 4
        fx1 = np.ceil(max(bx1, V[:, 0].max()) / 4) * 4 + 4; fy1 = np.ceil(max(by1, V[:, 1].max()) / 4) * 4 + 4
        w = int((fx1 - fx0) / RES); h = int((fy1 - fy0) / RES)
        Z = rasterise(V, F, fx0, fy0, w, h)
        X, Y = np.meshgrid(fx0 + (np.arange(w) + 0.5) * RES, fy0 + (np.arange(h) + 0.5) * RES)
        G = ground_at(r, gh, X, Y)
        # below the terrain, or within 5 cm of it, is the terrain: leave those cells to the ground sampler
        Z = np.where(Z > G + 0.05, Z, -np.inf)
        q = np.where(np.isfinite(Z), np.clip(np.round(Z * 10), -32767, 32767), -32768).astype(np.int16)
        head = json.dumps(dict(x0=float(fx0), y0=float(fy0), res=RES, w=w, h=h)).encode()
        with gzip.open(os.path.join(base, 'field.bin'), 'wb', compresslevel=9) as f: f.write(struct.pack('<I', len(head)) + head + q.tobytes())
        # roof raster: raised surfaces only, the highest in each 4 m cell
        k = int(4 / RES); raised = np.where(Z > G + 1.5, Z, -np.inf)
        R = raised[:h // k * k, :w // k * k].reshape(h // k, k, w // k, k).max(axis=(1, 3))
        ci = int(round((fx0 - rx0) / rres)); cj = int(round((fy0 - ry0) / rres))
        sub = roof[cj:cj + R.shape[0], ci:ci + R.shape[1]]
        Rf = np.where(np.isfinite(R), R, -1000.0)[:sub.shape[0], :sub.shape[1]]
        np.maximum(sub, Rf, out=sub)
        files = {k_: os.path.exists(os.path.join(base, k_ + '.glb')) for k_ in ('near', 'mid', 'far')}
        out.append(dict(name=name, title=d['title'], origin=[ox, oy], box=[bx0, by0, bx1, by1], files=files, spawns=meta.get('spawns', []), labels=meta.get('labels', []),
                        field=dict(x0=float(fx0), y0=float(fy0), w=w, h=h)))
        print(name, 'field', (w, h), 'covered', round(float(np.isfinite(Z).mean()), 3), 'raised cells', int(np.isfinite(R).sum()), 'tris', len(F))
    np.savez_compressed(os.path.join(ASSETS, 'build', 'roof.npz'), roof=roof, x0=rx0, y0=ry0, res=rres)
    json.dump(out, open(os.path.join(PUBLIC, 'data', 'heroes.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    print('heroes.json', [o['name'] for o in out])


if __name__ == '__main__':
    main()
