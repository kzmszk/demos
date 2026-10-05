"""Generate city tiles (venv python):  python build_tiles.py OUT_DIR [x0 y0 x1 y1] [--tiles i,j;i,j]
Per tile t_i_j:  .npz (static mesh + facade bake grids) and .fac.json (facade descriptors)."""
import sys, os, json, math, time, argparse
import numpy as np
import shapely
from shapely.geometry import box
from shapely.ops import unary_union
from gen.world import load, GROUND_Z, WATER_BOTTOM
from gen.city import Classifier, gen_building
from gen.ground import gen_ground, StreetDirs
from gen.bridges import find_bridges, gen_bridge
from gen import props as PR
from gen import hero as HERO
from gen import walk as WALK
from gen import pontoons as PT
from PIL import Image
from gen.world import h32
from gen.mesh import MeshBuilder, tangents
from gen import materials

TILE = 200.0
X0, Y0 = -3400.0, -1600.0
NTX, NTY = 30, 17

def tile_of(x, y): return int((x - X0) // TILE), int((y - Y0) // TILE)
def tile_box(i, j): return box(X0 + i * TILE, Y0 + j * TILE, X0 + (i + 1) * TILE, Y0 + (j + 1) * TILE)

def facade_grid(f):
    """bake grid for a facade descriptor; MUST match web/facade.js gridLevels()."""
    L = f['L']; nu = max(2, int(math.ceil(L / 1.0)) + 1)
    zs = max(f['zb'], 0.05 if f['cls'] == 'W' else f['zg'] + 0.03)
    nz = max(2, int(math.ceil((f['zt'] - zs) / 1.0)) + 1)
    f['g'] = [nu, nz, round(zs, 3)]
    p0 = np.array(f['p0']); p1 = np.array(f['p1']); n = np.array(f['n'])
    us = np.linspace(0, 1, nu); zz = np.linspace(zs, f['zt'], nz)
    P = np.zeros((nz, nu, 3))
    P[:, :, 0] = (p0[0] + (p1[0] - p0[0]) * us)[None, :]; P[:, :, 1] = (p0[1] + (p1[1] - p0[1]) * us)[None, :]; P[:, :, 2] = zz[:, None]
    P = P.reshape(-1, 3)
    I = []
    for j in range(nz - 1):
        for i in range(nu - 1):
            a = j * nu + i; b = a + 1; c = a + nu + 1; d = a + nu
            I += [[a, b, c], [a, c, d]]
    # outward normal: (dx,dy) x z -> check winding so that faces point along n
    return P, np.array(I, np.int64), n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--bbox', nargs=4, type=float); ap.add_argument('--tiles')
    ap.add_argument('--walk-only', action='store_true', help='only rewrite the walk rasters (meshes and bakes untouched)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    w = load(); HERO.setup(w); cl = Classifier(w); sd = StreetDirs(w)
    print(f'world {time.time()-t0:.1f}s', flush=True)
    if a.tiles: tiles = [tuple(map(int, s.split(','))) for s in a.tiles.split(';')]
    else:
        x0, y0, x1, y1 = a.bbox
        i0, j0 = tile_of(x0, y0); i1, j1 = tile_of(x1 - 0.01, y1 - 0.01)
        tiles = [(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)]
    brs = [br for br in find_bridges(w) if not any(math.dist((br['a'] + br['b']) / 2, (x, y)) < r for (x, y, r) in HERO.EXCLUDE_BRIDGES)]
    nb = len(brs); brs = PT.drop_stop_bridges(w.stops, brs)            # the stops bring their own gangways
    print('bridges to vaporetto stops left out:', nb - len(brs), flush=True)
    brt = {}
    for br in brs:
        c = (br['a'] + br['b']) / 2; brt.setdefault(tile_of(c[0], c[1]), []).append(br)
    bwalk = []
    for br in brs:
        try: bwalk.append(gen_bridge(MeshBuilder(), br)['walk'])
        except Exception: pass
    passages = WALK.Passages(w)
    hero_walk = HERO.walk_areas() + PT.walk_areas(w)
    stt = {}
    for it in w.stops + w.ships: stt.setdefault(tile_of(*it['c']), []).append(it)
    blockers = [b for b in w.buildings if b.z0 < GROUND_Z + 2.0]
    btree_low = shapely.STRtree([b.poly for b in blockers])
    dead = WALK.dead_bridges(w, bwalk, [b.poly for b in blockers], passages, hero_walk)
    walk_bridges = [wk for k, wk in enumerate(bwalk) if k not in dead]
    print('bridges', len(brs), f'({len(dead)} closed: a landing in a building or in water)', 'passages', len(passages.geoms), f'({passages.n_untagged} untagged through buildings)', 'hero walk areas', len(hero_walk), flush=True)
    bt = {}
    for bi, b in enumerate(w.buildings):
        c = b.poly.centroid; bt.setdefault(tile_of(c.x, c.y), []).append(bi)
    man = []
    materials.export(os.path.join(a.out, 'materials.json'))
    if a.walk_only:
        names = {m['name'] for m in json.load(open(os.path.join(a.out, 'tiles.json')))} if os.path.exists(os.path.join(a.out, 'tiles.json')) else None
        n = 0
        for (i, j) in tiles:
            if names is not None and f't_{i}_{j}' not in names: continue
            R = tile_box(i, j)
            rgb = WALK.raster(w, R, [blockers[k].poly for k in btree_low.query(R)], passages, walk_bridges, hero_walk)
            Image.fromarray(rgb, 'RGB').save(os.path.join(a.out, f't_{i}_{j}.walk.png'), optimize=True); n += 1
        print(f'walk rasters: {n} tiles in {time.time()-t0:.1f}s', flush=True)
        return
    for (i, j) in tiles:
        ts = time.time()
        R = tile_box(i, j)
        mb = MeshBuilder(); fac = []; inst = []
        bl = bt.get((i, j), [])
        for bi in bl:
            b = w.buildings[bi]
            if b.hero: continue
            try:
                n0 = len(fac)
                info = gen_building(w, cl, b, mb, fac, bi)
                PR.place_chimneys(b, info['poly'], info['zt'], info['eave_edges'], lambda k, b=b: h32(b.id, 'ch', k), inst)
                for fi in range(n0, len(fac)):
                    PR.place_facade_props(fac[fi], lambda k, fi=fi: h32(b.id, 'fp', fi, k), inst)
            except Exception as e: print('  building fail', b.id, e, flush=True)
        PR.place_osm_points(w, R, inst)
        t_h0 = mb.ntri()
        for hm in HERO.build(R, mb, inst): print('  hero', {k: v for k, v in hm.items() if k != 'line'}, flush=True)
        hero_range = [t_h0, mb.ntri()]
        near = [w.buildings[k].poly for k in w.btree.query(R.buffer(2.0))]
        bun = unary_union(near).buffer(0) if near else None
        st = gen_ground(w, R, mb, sd, bun)
        bridges_meta = []
        for br in brt.get((i, j), []):
            try: bridges_meta.append(gen_bridge(mb, br))
            except Exception as e: print('  bridge fail', e, flush=True)
        st['bridges'] = len(bridges_meta)
        for it in stt.get((i, j), []):
            try: PT.build(mb, it)
            except Exception as e: print('  stop fail', it['id'], e, flush=True)
        A = mb.arrays()
        if len(A['I']) == 0 and not fac:
            continue
        # walk / water raster
        rgb = WALK.raster(w, R, [blockers[k].poly for k in btree_low.query(R)], passages, walk_bridges, hero_walk)
        Image.fromarray(rgb, 'RGB').save(os.path.join(a.out, f't_{i}_{j}.walk.png'), optimize=True)
        # facade bake grids
        GP = []; GI = []; GN = []; off = 0
        for f in fac:
            P, I, n = facade_grid(f)
            f['go'] = off
            GP.append(P); GI.append(I + off); GN.append(np.tile([n[0], n[1], 0.0], (len(P), 1))); off += len(P)
        GP = np.concatenate(GP) if GP else np.zeros((0, 3)); GI = np.concatenate(GI) if GI else np.zeros((0, 3), np.int64); GN = np.concatenate(GN) if GN else np.zeros((0, 3))
        T = tangents(A['P'].astype(np.float64), A['N'].astype(np.float64), A['UV'].astype(np.float64), A['I'].astype(np.int64)) if len(A['I']) else np.zeros((0, 4))
        IT = np.array([x['t'] for x in inst], np.uint8); IP = np.array([x['p'] for x in inst], np.float32).reshape(-1, 3)
        IY = np.array([x['yaw'] for x in inst], np.float32); IS = np.array([x['s'] for x in inst], np.float32).reshape(-1, 3)
        IC = np.array([x['c'] for x in inst], np.uint8).reshape(-1, 3); PN = np.array([x['n'] for x in inst], np.float32).reshape(-1, 3)
        PN = PN / np.maximum(np.linalg.norm(PN, axis=1, keepdims=True), 1e-6)
        # bake probe: a little above the base (or in front of wall props)
        PP = IP + np.where(PN[:, 2:3] > 0.9, np.array([0, 0, 0.7], np.float32), PN * 0.8 + np.array([0, 0, -0.3], np.float32))
        name = f't_{i}_{j}'
        np.savez_compressed(os.path.join(a.out, name + '.npz'), P=A['P'], N=A['N'], T=T.astype(np.float32), UV=A['UV'], MAT=A['MAT'], C0=A['C0'], C1=A['C1'], I=A['I'],
                            GP=GP.astype(np.float32), GN=GN.astype(np.float32), GI=GI.astype(np.uint32),
                            IT=IT, IP=IP, IY=IY, IS=IS, IC=IC, PP=PP.astype(np.float32), PN=PN, HR=np.array(hero_range, np.int64))
        json.dump({'tile': [i, j], 'bbox': list(R.bounds), 'fac': fac}, open(os.path.join(a.out, name + '.fac.json'), 'w'), separators=(',', ':'))
        man.append({'name': name, 'tile': [i, j], 'bbox': list(R.bounds), 'nv': int(len(A['P'])), 'nt': int(len(A['I'])), 'nf': len(fac), 'gv': int(len(GP))})
        print(f'{name}: {len(inst)} props, {len(bl)} bld, mesh {len(A["P"])}v/{len(A["I"])}t, facades {len(fac)} ({sum(len(f["open"]) for f in fac)} openings), grid {len(GP)}v, ground {st} {time.time()-ts:.1f}s', flush=True)
    # prop templates (shared by all tiles)
    tp = PR.templates(); tarr = {}
    for k, name in enumerate(PR.T_NAMES):
        A = tp[name].arrays()
        Tg = tangents(A['P'].astype(np.float64), A['N'].astype(np.float64), A['UV'].astype(np.float64), A['I'].astype(np.int64))
        for key in ('P', 'N', 'UV', 'MAT', 'C0', 'C1', 'I'): tarr[f'{key}{k}'] = A[key]
        tarr[f'T{k}'] = Tg.astype(np.float32)
    np.savez_compressed(os.path.join(a.out, 'templates.npz'), names=np.array(PR.T_NAMES), **tarr)
    old = []
    mp = os.path.join(a.out, 'tiles.json')
    if os.path.exists(mp):
        old = [m for m in json.load(open(mp)) if m['name'] not in {x['name'] for x in man}]
    json.dump(old + man, open(mp, 'w'), indent=0)
    print(f'done {len(man)} tiles in {time.time()-t0:.1f}s')

if __name__ == '__main__':
    main()
