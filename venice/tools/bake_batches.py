"""Bake a whole build dir in 4x4-tile batches (margin 1), skipping tiles whose bake is newer than their mesh.
python bake_batches.py BUILD_DIR [--mode day|night] [--samples N] [--block 4]"""
import sys, os, json, subprocess, time, argparse
ap = argparse.ArgumentParser(); ap.add_argument('build'); ap.add_argument('--mode', default='day'); ap.add_argument('--samples', default='128'); ap.add_argument('--block', type=int, default=4)
ap.add_argument('--force', action='store_true')
a = ap.parse_args()
tiles = json.load(open(os.path.join(a.build, 'tiles.json')))
todo = []
for t in tiles:
    n = t['name']; src = os.path.join(a.build, n + '.npz'); dst = os.path.join(a.build, f'{n}.{a.mode}.npz')
    if a.force or not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src): todo.append(t)
blocks = {}
for t in todo:
    i, j = t['tile']; blocks.setdefault((i // a.block, j // a.block), []).append(t['name'])
print(len(todo), 'tiles in', len(blocks), 'batches', flush=True)
t0 = time.time()
for k, (key, names) in enumerate(sorted(blocks.items())):
    r = subprocess.run(['blender', '-b', '--python', os.path.join(os.path.dirname(__file__), 'bake.py'), '--', a.build, '--tiles', ','.join(names),
                        '--mode', a.mode, '--samples', a.samples, '--margin', '1'], capture_output=True, text=True)
    last = [l for l in r.stdout.splitlines() if 'done' in l or 'rror' in l]
    print(f'[{k + 1}/{len(blocks)}] {key} {len(names)} tiles: {last[-1] if last else r.stdout[-300:]}  ({time.time() - t0:.0f}s)', flush=True)
