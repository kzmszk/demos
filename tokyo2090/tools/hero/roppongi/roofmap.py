"""Top-down max-height raster of buildings.obj (debug aid). venv python: roofmap.py out.png"""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
SRC = '/home/kazu/work/tokyo2090-assets/hero/roppongi/'
V = []; F = []; names = []
cur = None
for l in open(SRC+'buildings.obj'):
    if l.startswith('o '): cur = l[2:].strip()
    elif l.startswith('v '): V.append(list(map(float, l.split()[1:4])))
    elif l.startswith('f '):
        idx = [int(t.split('/')[0])-1 for t in l.split()[1:]]
        for k in range(1, len(idx)-1): F.append((idx[0], idx[k], idx[k+1])); names.append(cur)
V = np.array(V); R = 1.0
X0, Y0, N = -200, -210, 420
Hm = np.full((N, N), np.nan)
for (a, b, c) in F:
    p = V[[a, b, c]]
    x0, x1 = int(np.floor((p[:, 0].min()-X0)/R)), int(np.ceil((p[:, 0].max()-X0)/R))
    y0, y1 = int(np.floor((p[:, 1].min()-Y0)/R)), int(np.ceil((p[:, 1].max()-Y0)/R))
    xs, ys = np.meshgrid(np.arange(max(x0, 0), min(x1+1, N)), np.arange(max(y0, 0), min(y1+1, N)))
    if xs.size == 0: continue
    px = X0+(xs+0.5)*R; py = Y0+(ys+0.5)*R
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = p
    det = (by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
    if abs(det) < 1e-9: continue
    l1 = ((by-cy)*(px-cx)+(cx-bx)*(py-cy))/det
    l2 = ((cy-ay)*(px-cx)+(ax-cx)*(py-cy))/det
    l3 = 1-l1-l2
    m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
    z = l1*az+l2*bz+l3*cz
    cur = Hm[ys[m], xs[m]]
    Hm[ys[m], xs[m]] = np.fmax(cur, z[m])
np.save(SRC+'work/scratch/roof.npy', Hm)
img = np.zeros((N, N, 3), np.uint8)
v = np.nan_to_num(Hm, nan=0)
# colour by height bands
bands = [(0, (30, 30, 30)), (20, (60, 60, 120)), (30, (40, 120, 200)), (40, (60, 180, 80)), (50, (200, 200, 60)), (60, (230, 140, 40)), (75, (200, 60, 60)), (100, (220, 120, 220)), (150, (255, 255, 255))]
for z, c in bands: img[v >= z] = c
img = img[::-1]
im = Image.fromarray(img).resize((N*3, N*3), Image.NEAREST)
d = ImageDraw.Draw(im)
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
for gx in range(-200, 221, 20):
    d.line([((gx-X0)*3, 0), ((gx-X0)*3, N*3)], fill=(90, 90, 90))
    d.text(((gx-X0)*3+2, 2), str(gx), fill=(255, 255, 0), font=font)
for gy in range(-200, 221, 20):
    d.line([(0, (N-(gy-Y0))*3), (N*3, (N-(gy-Y0))*3)], fill=(90, 90, 90))
    d.text((2, (N-(gy-Y0))*3+2), str(gy), fill=(255, 255, 0), font=font)
# print height samples every 10 m
for gx in range(-195, 200, 10):
    for gy in range(-205, 210, 10):
        z = Hm[gy-Y0, gx-X0]
        if not np.isnan(z): d.text(((gx-X0)*3-8, (N-(gy-Y0))*3-6), f'{z:.0f}', fill=(0, 0, 0), font=font)
im.save(sys.argv[1])
