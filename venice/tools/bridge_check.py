"""Can a walker cross every bridge?  python bridge_check.py [BUILD_DIR]   (venv python, from venice/tools)

The bridges are chosen as build_tiles.py chooses them (heroes excluded, the gangway fans to vaporetto stops left out,
the ones dead_bridges() closes counted apart).  For each, the walk rasters are searched for a path from walkable ground
off the deck near one foot (straight ahead of it or beside it) to the same near the other, the way controls.js walks:
the body needs walkable ground all round (0.25 m) and no step up or down of more than 0.55 m.  The hand-modelled Grand
Canal crossings are checked along their walk lanes."""
import sys, os, math, collections
import numpy as np
from PIL import Image
from scipy import ndimage
from gen.world import load, GROUND_Z
from gen.bridges import find_bridges, gen_bridge
from gen.mesh import MeshBuilder
from gen import hero as HERO, walk as WALK, pontoons as PT

B = sys.argv[1] if len(sys.argv) > 1 else '/home/kazu/work/venice-assets/build/island'
X0, Y0, TS, RES = -3400.0, -1600.0, 200.0, 0.25
S = int(TS / RES)
_tiles = {}

def tile(i, j):
    if (i, j) not in _tiles:
        p = f'{B}/t_{i}_{j}.walk.png'
        _tiles[(i, j)] = np.array(Image.open(p))[:, :, 0] if os.path.exists(p) else None
    return _tiles[(i, j)]

def patch(x0, y0, x1, y1):
    """height codes over a box; pixel (r, c) is at x = x0 + (c + .5) RES, y = y1 - (r + .5) RES"""
    W = int(math.ceil((x1 - x0) / RES)); H = int(math.ceil((y1 - y0) / RES))
    out = np.zeros((H, W), np.uint8)
    xs = x0 + (np.arange(W) + 0.5) * RES; ys = y1 - (np.arange(H) + 0.5) * RES
    I = np.floor((xs - X0) / TS).astype(int); J = np.floor((ys - Y0) / TS).astype(int)
    for j in np.unique(J):
        for i in np.unique(I):
            A = tile(i, j)
            if A is None: continue
            cm = np.nonzero(I == i)[0]; rm = np.nonzero(J == j)[0]
            pc = ((xs[cm] - (X0 + i * TS)) / RES).astype(int).clip(0, S - 1)
            pr = (((Y0 + (j + 1) * TS) - ys[rm]) / RES).astype(int).clip(0, S - 1)
            out[np.ix_(rm, cm)] = A[np.ix_(pr, pc)]
    return out

def crossable(a, b, ti, margin=6.0):
    """a, b: the feet of the deck; ti: its half width.  (ok, why)"""
    a = np.array(a, float); b = np.array(b, float); L = float(np.linalg.norm(b - a))
    d = (b - a) / max(L, 1e-9); n = np.array([-d[1], d[0]])
    x0, y0 = np.minimum(a, b) - margin; x1, y1 = np.maximum(a, b) + margin
    C = patch(x0, y0, x1, y1)
    walk = C > 0
    z = np.where(walk, (C.astype(float) - 1) * 0.04 - 1.0, np.nan)
    ok = ndimage.binary_erosion(walk, np.ones((3, 3)))
    zmax = ndimage.maximum_filter(np.where(walk, z, -99), size=3); zmin = ndimage.minimum_filter(np.where(walk, z, 99), size=3)
    H, W = C.shape
    rr, cc = np.mgrid[0:H, 0:W]; PX = x0 + (cc + 0.5) * RES; PY = y1 - (rr + 0.5) * RES
    sv = (PX - a[0]) * d[0] + (PY - a[1]) * d[1]; tv = (PX - a[0]) * n[0] + (PY - a[1]) * n[1]
    off = ~((np.abs(tv) <= ti + 0.1) & (sv >= -0.1) & (sv <= L + 0.1))
    near = lambda p: ok & off & (np.hypot(PX - p[0], PY - p[1]) < ti + 1.6)
    ma, goal = near(a), near(b)
    if not ma.any() or not goal.any(): return False, 'no ground off the deck at the ' + ('first' if not ma.any() else 'second') + ' foot'
    seen = ma.copy(); q = collections.deque(zip(*np.nonzero(ma)))          # from any ground near the first foot
    while q:
        r, c = q.popleft()
        if goal[r, c]: return True, ''
        z0 = z[r, c]
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                r2, c2 = r + dr, c + dc
                if (dr or dc) and 0 <= r2 < H and 0 <= c2 < W and ok[r2, c2] and not seen[r2, c2] \
                        and zmax[r2, c2] - z0 <= 0.55 and z0 - zmin[r2, c2] <= 0.55:
                    seen[r2, c2] = True; q.append((r2, c2))
    return False, f'stops {float(sv[seen].max()):.1f} m along {L:.1f} m'

def main():
    w = load(); HERO.setup(w)
    brs = [br for br in find_bridges(w) if not any(math.dist((br['a'] + br['b']) / 2, (x, y)) < r for (x, y, r) in HERO.EXCLUDE_BRIDGES)]
    brs = PT.drop_stop_bridges(w.stops, brs)
    bw = []
    for br in brs:
        try: bw.append(gen_bridge(MeshBuilder(), br)['walk'])
        except Exception: pass
    blockers = [b.poly for b in w.buildings if b.z0 < GROUND_Z + 2.0]
    dead = WALK.dead_bridges(w, bw, blockers, WALK.Passages(w), HERO.walk_areas() + PT.walk_areas(w))
    live = [wk for k, wk in enumerate(bw) if k not in dead]
    fails = []
    for wk in live:
        a = np.array(wk['a']); d = np.array(wk['d']); s_lo, _, _, s_hi = wk['s']
        good, why = crossable(a + d * s_lo, a + d * s_hi, wk['ti'])
        if not good: fails.append(((a + d * (s_lo + s_hi) / 2), s_hi - s_lo, why))
    print(f'{len(bw)} bridges: {len(dead)} closed (no walkable ground ahead of or beside a foot: private bridges to doors), '
          f'{len(live)} open, {len(fails)} of them not crossable')
    for m, L, why in fails: print(f'  ({m[0]:7.1f},{m[1]:7.1f})  {L:5.1f} m: {why}')
    from gen.hero import gc_bridges as GC
    for name, ax, tr in (('Accademia', GC.ACC, GC.ACC_TREADS), ('Scalzi', GC.SCA, GC.SCA_TREADS), ('Costituzione', GC.COS, GC.COS_TREADS)):
        good, why = crossable(ax.xy(tr[0][0] - 0.5), ax.xy(tr[-1][1] + 0.5), 2.5)
        print(f'  {name}: {"crossable" if good else why}')

if __name__ == '__main__':
    main()
