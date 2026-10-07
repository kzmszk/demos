"""Bring the tiles of one or more hero sites up to date (venv python):  python hero_update.py SITE [SITE ...] [--no-bake] [--samples N]
tiles touched by the site (its geometry, walk/block meshes and edits) -> build_tiles, build_trees, build_props, bake, pack."""
import sys, os, json, subprocess, time
import numpy as np
from gen.frame import tile_of, tiles_in

PY = '/home/kazu/work/kyoto-assets/.venv/bin/python'
BUILD = '/home/kazu/work/kyoto-assets/build/city'
STAGE = '/home/kazu/work/kyoto-assets/build/stage_city'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public', 'data', 'city')

def tiles_of(site):
    d = np.load(f'/home/kazu/work/kyoto-assets/heroes/{site}.npz')
    pts = [d[k][:, :2] for k in ('P', 'WP', 'KP') if k in d and len(d[k])]
    if 'EDITS' in d:
        ed = json.loads(bytes(d['EDITS']).decode())
        for k in ('exclude', 'cut'):
            for ring in ed.get(k, []):
                r = ring[0] if isinstance(ring[0][0], (list, tuple)) else ring
                pts.append(np.array(r)[:, :2])
        for e in ed.get('paint', []):
            r = e['poly']
            while isinstance(r[0][0], (list, tuple)): r = r[0]          # [outer, holes...] -> outer
            pts.append(np.array(r)[:, :2])
    P = np.concatenate(pts)
    x0, y0 = P.min(0) - 5; x1, y1 = P.max(0) + 5
    return tiles_in(x0, y0, x1, y1)

def run(cmd):
    t = time.time(); print('>', ' '.join(cmd)[:160], flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
    print('  ', f'{time.time()-t:.0f}s', *tail, sep='\n   ', flush=True)
    if r.returncode: raise SystemExit(f'failed: {cmd[1]}')

def main():
    av = sys.argv[1:]
    extra = []
    if '--tiles' in av:                     # plain tiles too:  --tiles "i,j;i,j"
        k = av.index('--tiles'); extra = [tuple(map(int, p.split(','))) for p in av[k + 1].split(';')]; del av[k:k + 2]
    if '--samples' in av: k = av.index('--samples'); del av[k:k + 2]
    sites = [a for a in av if not a.startswith('--')]
    tl = sorted({t for s in sites for t in tiles_of(s)} | set(extra))
    spec = ';'.join(f'{i},{j}' for i, j in tl); names = ','.join(f't_{i}_{j}' for i, j in tl)
    print(sites, len(tl), 'tiles', flush=True)
    run([PY, 'build_tiles.py', BUILD, '--tiles=' + spec, '-j', '8'])
    run([PY, 'build_trees.py', BUILD, '--tiles=' + spec, '-j', '8'])
    run([PY, 'build_props.py', BUILD, '--tiles=' + spec, '-j', '6'])
    if '--no-bake' not in sys.argv:
        smp = sys.argv[sys.argv.index('--samples') + 1] if '--samples' in sys.argv else '128'
        run([PY, 'bake_batches.py', BUILD, '--samples', smp, '--tiles', names])
    st = STAGE + '_upd_' + str(os.getpid())          # per run: two merges never share a staging folder
    if os.path.exists(st): subprocess.run(['rm', '-rf', st])
    run([PY, 'pack.py', BUILD, st, '-j8'] + names.split(','))
    run(['node', 'pack.mjs', st, OUT])
    import shutil; shutil.rmtree(st, ignore_errors=True)

if __name__ == '__main__':
    main()
