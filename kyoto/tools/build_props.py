"""Street furniture for every tile (venv python):  python build_props.py BUILD_DIR [-j N] [--tiles i,j;...]
Writes t_i_j.props.npz (P, N, UV, MAT, C0, C1, I, DETAIL); pack.py merges them, lit from the nearest baked vertices."""
import sys, os, json, time, argparse
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_v, "1")
import numpy as np
import shapely
from shapely.geometry import box
from gen.frame import tile_bounds
from gen import world as W
from gen.ground import TileGround
from gen import props as PR
from gen.heroes import Heroes

WORLD = None; HEROES = None; TEMPLE = None; NOPOLE = None
def one(ij, out):
    i, j = ij; w = WORLD
    b = tile_bounds(i, j); tg = TileGround(w, i, j, b)
    bl = [w.buildings[k] for k in w.btree.query(tg.R.buffer(10)) if not HEROES.excluded(w.buildings[k])]
    B = PR.build(w, tg, bl, tg.water_geom(), TEMPLE, NOPOLE, HEROES.exclude)
    import jk
    M = jk.core.mats()
    D = B.merged(('main', 'detail'))
    if D is None:
        np.savez_compressed(os.path.join(out, f't_{i}_{j}.props.npz'), P=np.zeros((0, 3), np.float32), I=np.zeros((0, 3), np.uint32)); return 0
    np.savez_compressed(os.path.join(out, f't_{i}_{j}.props.npz'), P=D['P'], N=D['N'], UV=D['UV'], I=D['I'].astype(np.uint32), C0=D['C0'], C1=D['C1'],
                        MAT=np.array([M[n]['id'] for n in D['MATN']], np.uint8), DETAIL=(D['TAG'] == 'detail').astype(np.uint8))
    return len(D['I'])

def main():
    global WORLD, HEROES, TEMPLE, NOPOLE
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('-j', type=int, default=1); ap.add_argument('--tiles')
    a = ap.parse_args()
    WORLD = W.load(); HEROES = Heroes()
    TEMPLE = shapely.unary_union([f['poly'] for f in WORLD.osm['landuse'] if f['kind'] in ('religious', 'place_of_worship')]); shapely.prepare(TEMPLE)
    zones = [box(1180, 1750, 2120, 2700)] + ([HEROES.exclude] if HEROES.exclude is not None else [])     # Gion: lines are underground
    NOPOLE = shapely.unary_union(zones); shapely.prepare(NOPOLE)
    tiles = [tuple(map(int, s.split(','))) for s in a.tiles.split(';')] if a.tiles else [tuple(t['tile']) for t in json.load(open(os.path.join(a.out, 'tiles.json')))]
    t0 = time.time()
    if a.j > 1:
        import multiprocessing as mp
        with mp.get_context('fork').Pool(a.j, maxtasksperchild=30) as pool:
            n = pool.starmap(one, [(t, a.out) for t in tiles], chunksize=2)
    else: n = [one(t, a.out) for t in tiles]
    print(len(tiles), 'tiles', sum(n), 'prop triangles', f'{time.time()-t0:.0f}s')

if __name__ == '__main__':
    main()
