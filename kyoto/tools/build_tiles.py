"""Generate Kyoto tiles (venv python):  python build_tiles.py OUT_DIR (--bbox x0 y0 x1 y1 | --tiles i,j;i,j) [-j N]
Per tile t_i_j: .npz (static mesh), .surf.png (ground surface ids, 0.5 m), .walk.png (walk map)."""
import sys, os, json, math, time, argparse
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"): os.environ.setdefault(_v, "1")   # forked workers deadlocked in threaded BLAS
import numpy as np
import shapely
from PIL import Image
from gen.frame import X0, Y0, TILE, tile_of, tile_bounds, NTX, NTY, tiles_in, region_tiles
from gen import world as W
from gen.city import Ctx, gen_building
from gen import city as CITY
from gen.ground import TileGround
from gen import walk as WALK
from gen.mesh import MeshBuilder
from gen import materials
from gen.heroes import Heroes, raster_tris

WORLD = None
HEROES = None

def drop_hero_bridges(tg, cut):
    """generic bridges whose line lies mostly inside a hero site's cut (the site models its own bridge, e.g. 渡月橋)"""
    if cut is None or cut.is_empty: return
    tg.roads = [r for r in tg.roads if not (r['bridge'] and r['line'].length > 0 and r['line'].intersection(cut).length > 0.5 * r['line'].length)]

def build(ij, out):
    i, j = ij
    w = WORLD
    ts = time.time()
    bounds = tile_bounds(i, j)
    tg = TileGround(w, i, j, bounds)
    mb = MeshBuilder()
    road = tg.street_geom()
    ctx = Ctx(w, tg.R, road)
    R = tg.R
    bl = []
    for k in w.btree.query(R):
        b = w.buildings[k]
        c = b.poly.representative_point()
        if not (bounds[0] <= c.x < bounds[2] and bounds[1] <= c.y < bounds[3]): continue
        bl.append(b)
    nfail = 0
    H = HEROES
    bl = [b for b in bl if not H.excluded(b)]
    for b in bl:
        try: gen_building(ctx, b, mb)
        except Exception as e:
            nfail += 1
            if nfail < 4: print('  building fail', b.id, repr(e), flush=True)
    nb_tris = mb.ntri()
    h0 = mb.ntri(); nh = H.add_geometry(mb, bounds); hero_range = [h0, mb.ntri()]
    # far LOD: the same buildings without subdivision or details, a coarse terrain
    mbL = MeshBuilder()
    CITY.COARSE[0] = True
    for b in bl:
        try: gen_building(ctx, b, mbL)
        except Exception: pass
    CITY.COARSE[0] = False
    wg = tg.water_geom(); wl = tg.water_level(wg)
    cut = H.cut(tg.R)
    drop_hero_bridges(tg, cut)
    tg.terrain_mesh(mb, wg, wl, cut=cut)
    tg.water_mesh(mb, wg.difference(cut) if (cut is not None and wg is not None) else wg, wl)   # a hero site models its own water
    tg.terrain_mesh(mbL, wg, wl, grid=8.0, cut=cut)
    brs = tg.bridges(mb)
    surf = tg.surface(bl)
    for (pg, sname) in H.paint(tg.R): tg.paint(surf, pg, sname)
    near = [w.buildings[k] for k in w.btree.query(R.buffer(2)) if not H.excluded(w.buildings[k])]
    walk = WALK.raster(tg, surf, near, wg, wl, brs, hero=H.walk_edits(bounds) + (H.roof_tris(bounds),))
    A = mb.arrays(); AL = mbL.arrays()
    name = f't_{i}_{j}'
    np.savez_compressed(os.path.join(out, name + '.lite.npz'), P=AL['P'], N=AL['N'], MAT=AL['MAT'], C0=AL['C0'], C1=AL['C1'], I=AL['I'])
    np.savez_compressed(os.path.join(out, name + '.npz'), P=A['P'], N=A['N'], UV=A['UV'], MAT=A['MAT'], C0=A['C0'], C1=A['C1'], I=A['I'], SURF=surf, BBOX=np.array(bounds), HR=np.array(hero_range, np.int64), HD=(np.concatenate(H.last_detail) if H.last_detail else np.zeros(0, np.uint8)))
    Image.fromarray(surf[::-1], 'L').save(os.path.join(out, name + '.surf.png'), optimize=True)
    Image.fromarray(walk, 'RGBA').save(os.path.join(out, name + '.walk.png'), optimize=True)
    zr = [float(A['P'][:, 2].min()), float(A['P'][:, 2].max())] if len(A['P']) else [0, 0]
    rec = {'name': name, 'tile': [i, j], 'bbox': list(bounds), 'nv': int(len(A['P'])), 'nt': int(len(A['I'])), 'nb': len(bl), 'z': zr}
    print(f'{name}: {len(bl)} bld ({nfail} failed) {nb_tris} bld tris, {nh} hero tris, mesh {len(A["P"])}v/{len(A["I"])}t, {len(brs)} bridges  {time.time()-ts:.1f}s', flush=True)
    return rec

def walk_only(ij, out):
    """only the walk map (.walk.png): meshes, surfaces and bakes stay as they are"""
    i, j = ij; w = WORLD; H = HEROES
    bounds = tile_bounds(i, j); tg = TileGround(w, i, j, bounds); R = tg.R
    bl = [w.buildings[k] for k in w.btree.query(R)]
    bl = [b for b in bl if (lambda c: bounds[0] <= c.x < bounds[2] and bounds[1] <= c.y < bounds[3])(b.poly.representative_point()) and not H.excluded(b)]
    wg = tg.water_geom(); wl = tg.water_level(wg)
    drop_hero_bridges(tg, H.cut(tg.R))
    brs = tg.bridges(MeshBuilder())
    surf = tg.surface(bl)
    for (pg, sname) in H.paint(tg.R): tg.paint(surf, pg, sname)
    near = [w.buildings[k] for k in w.btree.query(R.buffer(2)) if not H.excluded(w.buildings[k])]
    walk = WALK.raster(tg, surf, near, wg, wl, brs, hero=H.walk_edits(bounds) + (H.roof_tris(bounds),))
    name = f't_{i}_{j}'
    Image.fromarray(walk, 'RGBA').save(os.path.join(out, name + '.walk.png'), optimize=True)
    if SURF_TOO[0]: Image.fromarray(surf[::-1], 'L').save(os.path.join(out, name + '.surf.png'), optimize=True)
    return {'name': name, 'covered': int(((walk[:, :, 2] >> 5) & 1).sum())}
SURF_TOO = [False]

def main():
    global WORLD, HEROES
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--bbox', nargs=4, type=float); ap.add_argument('--tiles'); ap.add_argument('-j', type=int, default=1)
    ap.add_argument('--index', action='store_true', help='only rebuild tiles.json from the .npz files')
    ap.add_argument('--walk-only', action='store_true', help='only the walk maps (no mesh, so no rebake)')
    ap.add_argument('--surf', action='store_true', help='with --walk-only: the surface rasters too (pack.py reads them from the .surf.png)')
    a = ap.parse_args()
    if a.index:
        import glob
        man = []
        for f in sorted(glob.glob(os.path.join(a.out, 't_*_*.npz'))):
            if f.endswith('.lite.npz') or f.endswith('.bake.npz'): continue
            d = np.load(f); n = os.path.basename(f)[:-4]; i, j = map(int, n.split('_')[1:3])
            man.append({'name': n, 'tile': [i, j], 'bbox': [float(v) for v in d['BBOX']], 'nv': int(len(d['P'])), 'nt': int(len(d['I'])),
                        'z': [float(d['P'][:, 2].min()), float(d['P'][:, 2].max())] if len(d['P']) else [0, 0]})
        json.dump(man, open(os.path.join(a.out, 'tiles.json'), 'w'), indent=0); print(len(man), 'tiles indexed'); return
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    WORLD = W.load()
    HEROES = Heroes()
    print(f'world {time.time()-t0:.1f}s, heroes {[s["name"] for s in HEROES.sites]}', flush=True)
    if a.tiles: tiles = [tuple(map(int, s.split(','))) for s in a.tiles.split(';')]
    else:
        x0, y0, x1, y1 = a.bbox
        tiles = tiles_in(x0, y0, x1 - 0.01, y1 - 0.01)          # only tiles of the built regions
    if a.walk_only:
        SURF_TOO[0] = a.surf
        import multiprocessing as mp
        with mp.get_context('fork').Pool(max(1, a.j)) as pool: res = pool.starmap(walk_only, [(t, a.out) for t in tiles], chunksize=1)
        print('walk maps', len(res), 'covered cells', sum(r['covered'] for r in res), f'{time.time()-t0:.1f}s'); return
    materials.export(os.path.join(a.out, 'materials.json'))
    if a.j > 1:
        import multiprocessing as mp
        ctx = mp.get_context('fork')
        with ctx.Pool(a.j, maxtasksperchild=40) as pool:
            man = pool.starmap(build, [(t, a.out) for t in tiles], chunksize=1)
    else:
        man = [build(t, a.out) for t in tiles]
    mp_ = os.path.join(a.out, 'tiles.json')
    old = []
    if os.path.exists(mp_):
        old = [m for m in json.load(open(mp_)) if m['name'] not in {x['name'] for x in man}]
    json.dump(old + man, open(mp_, 'w'), indent=0)
    print(f'done {len(man)} tiles in {time.time()-t0:.1f}s')

if __name__ == '__main__':
    main()
