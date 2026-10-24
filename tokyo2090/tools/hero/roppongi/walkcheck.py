"""Walkability check of collide.obj as the game will see it: rasterise from above at 0.5 m (highest surface,
terrain where nothing), then flood-fill from the spawns with step-up <= 0.55 m and drop <= 3.2 m.
venv python walkcheck.py [out.png]"""
import sys, json
import numpy as np
from collections import deque
sys.path.insert(0, __file__.rsplit('/', 1)[0])
import lib

RES = 0.5
X0, Y0, X1, Y1 = -185, -195, 185, 195
W = int((X1 - X0) / RES); H = int((Y1 - Y0) / RES)
G = lib.Ground()
V = []; F = []
for line in open(lib.OUT + 'collide.obj'):
    if line.startswith('v '):
        V.append([float(t) for t in line.split()[1:4]])
    elif line.startswith('f '):
        F.append([int(t) - 1 for t in line.split()[1:4]])
V = np.array(V); F = np.array(F)
top = np.full((H, W), -np.inf)
for f in F:
    p = V[f]
    ix0 = max(int((p[:, 0].min() - X0) / RES), 0); ix1 = min(int((p[:, 0].max() - X0) / RES) + 1, W - 1)
    iy0 = max(int((p[:, 1].min() - Y0) / RES), 0); iy1 = min(int((p[:, 1].max() - Y0) / RES) + 1, H - 1)
    if ix1 < ix0 or iy1 < iy0:
        continue
    xs, ys = np.meshgrid(np.arange(ix0, ix1 + 1), np.arange(iy0, iy1 + 1))
    px = X0 + (xs + 0.5) * RES; py = Y0 + (ys + 0.5) * RES
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = p
    det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(det) < 1e-9:
        continue
    l1 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / det
    l2 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / det
    l3 = 1 - l1 - l2
    m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
    z = l1 * az + l2 * bz + l3 * cz
    top[ys[m], xs[m]] = np.maximum(top[ys[m], xs[m]], z[m])
gx, gy = np.meshgrid(X0 + (np.arange(W) + 0.5) * RES, Y0 + (np.arange(H) + 0.5) * RES)
terr = G(gx, gy)
Hf = np.maximum(top, terr)
args = [a for a in sys.argv[1:]]
if '--north' in args:      # wall off everything north of y (to test the stair routes alone)
    yn = float(args[args.index('--north') + 1]); del args[args.index('--north'):args.index('--north') + 2]
    Hf[int((yn - Y0) / RES):, :] = 1000.0
sys.argv = [sys.argv[0]] + args


def cell(x, y):
    return int((y - Y0) / RES), int((x - X0) / RES)


def flood(start):
    seen = np.zeros((H, W), bool)
    q = deque([cell(*start)]); seen[q[0]] = True
    while q:
        j, i = q.popleft()
        h = Hf[j, i]
        for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = j + dj, i + di
            if 0 <= a < H and 0 <= b < W and not seen[a, b]:
                d = Hf[a, b] - h
                if d <= 0.55 and d >= -3.2:
                    seen[a, b] = True; q.append((a, b))
    return seen


hj = json.load(open(lib.OUT + 'hero.json'))
res = {}
reach = None
for sp in hj['spawns']:
    s = flood((sp['x'], sp['y']))
    reach = s if reach is None else (reach | s)
    res[sp['name']] = s
targets = {'Maman (deck)': (12.0, 97.0), 'stair A mid': (6.2, 49.0), 'stair B mid': (32.5, 52.5), 'pond edge': (52.0, 46.0), 'Keyakizaka (10,-85)': (10.0, -85.0),
           'stair A top': (1.8, 61.5), 'stair B bottom': (40.0, 39.5), 'Metro Hat floor': (-26.0, 165.0)}
for name, s in res.items():
    print(name, {t: bool(s[cell(*p)]) for t, p in targets.items()}, 'start h %.1f' % Hf[cell(hj['spawns'][0]['x'], hj['spawns'][0]['y'])])
if len(sys.argv) > 1:
    from PIL import Image
    img = np.zeros((H, W, 3), np.uint8)
    hn = np.clip((Hf - 10) / 40, 0, 1)
    img[..., 0] = (hn * 200).astype(np.uint8); img[..., 1] = (hn * 200).astype(np.uint8); img[..., 2] = (hn * 200).astype(np.uint8)
    img[reach] = (img[reach] * 0.5 + np.array([0, 120, 0])).astype(np.uint8)
    for t, p in targets.items():
        j, i = cell(*p); img[max(j - 3, 0):j + 3, max(i - 3, 0):i + 3] = (255, 0, 0)
    Image.fromarray(img[::-1]).save(sys.argv[1])
