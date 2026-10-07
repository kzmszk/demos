"""Tree placements for every tile (venv python):  python build_trees.py BUILD_DIR [-j N] [--tiles i,j;...]
Writes t_i_j.trees.npy: (k, 7) float32 = species, variant, x, y, z, scale, yaw (meshes and bakes untouched)."""
import sys, os, json, time, argparse
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_v, "1")
import numpy as np
from gen.frame import tile_bounds
from gen import world as W
from gen.ground import TileGround
from gen import trees as TR

WORLD = None
HEROTREES = []
HEROZONE = None
def one(ij, out):
    i, j = ij; w = WORLD
    b = tile_bounds(i, j); tg = TileGround(w, i, j, b)
    bl = [w.buildings[k] for k in w.btree.query(tg.R.buffer(3))]
    A = TR.place(w, tg, tg.R, bl, tg.road_polys(), tg.water_geom(), HEROZONE)
    # trees planted by the hero sites (species index, x, y, z, scale, yaw)
    for HT in HEROTREES:
        sel = (HT[:, 1] >= b[0]) & (HT[:, 1] < b[2]) & (HT[:, 2] >= b[1]) & (HT[:, 2] < b[3])
        if sel.any():
            h = HT[sel].copy()
            # tended precincts colour in autumn: an evergreen oak there becomes a maple (or a ginkgo); on forest ground
            # (the hills behind the temples) the trees are wild
            wild = np.array([TR.wild_at(tg.landuse, x, y) for x, y in h[:, 1:3]], bool)
            u = (np.abs(np.sin(h[:, 1] * 12.9898 + h[:, 2] * 78.233)) * 43758.5453) % 1.0
            oak = (h[:, 0] == TR.SP['kashi']) & ~wild
            h[oak & (u < 0.75), 0] = TR.SP['momiji']; h[oak & (u >= 0.75) & (u < 0.9), 0] = TR.SP['ichou']
            add = np.column_stack([h[:, 0], (np.arange(len(h)) % 3) + wild * TR.WILD, h[:, 1], h[:, 2], h[:, 3], h[:, 4], h[:, 5]]).astype(np.float32)
            A = np.concatenate([A, add]) if len(A) else add
    np.save(os.path.join(out, f't_{i}_{j}.trees.npy'), A)
    return len(A)

def main():
    global WORLD, HEROTREES, HEROZONE
    from gen.heroes import Heroes
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('-j', type=int, default=1); ap.add_argument('--tiles')
    a = ap.parse_args()
    WORLD = W.load()
    H = Heroes(); HEROTREES = H.trees(); HEROZONE = H.tree_zone(WORLD)
    if a.tiles: tiles = [tuple(map(int, s.split(','))) for s in a.tiles.split(';')]
    else: tiles = [tuple(t['tile']) for t in json.load(open(os.path.join(a.out, 'tiles.json')))]
    t0 = time.time()
    if a.j > 1:
        import multiprocessing as mp
        with mp.get_context('fork').Pool(a.j, maxtasksperchild=40) as pool:
            n = pool.starmap(one, [(t, a.out) for t in tiles], chunksize=4)
    else: n = [one(t, a.out) for t in tiles]
    print(len(tiles), 'tiles', sum(n), 'trees', f'{time.time()-t0:.0f}s')

if __name__ == '__main__':
    main()
