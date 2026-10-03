"""Trace the exterior outline of the basilica from Fontana's plan (Templum Vaticanum, plate 5922347).
Run with Blender's python (numpy).  Output: ref/basilica_outline.json in basilica local metres (u east, v north)."""
import json, math, sys, struct, zlib
import numpy as np
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
from vb.geom import simplify_ring

SRC = '/home/kazu/work/vatican-assets/refs/drawings/Templum_Vaticanum_et_ipsius_origo_1694_5922347_.jpg'
GREY = '/tmp/claude-1000/-home-kazu-work-demos/1f48e580-beae-4176-8eee-fdee54a01026/scratchpad/plan_grey.raw'
# crop (src px) and calibration
X0, Y0, W, H = 900, 420, 3250, 3850
CX, CY, S = 2528, 1952, 0.0538          # dome centre (src px), metres per src px
DS = 2

g = np.fromfile(GREY, np.uint8).reshape(H, W)
g = g[:H // DS * DS, :W // DS * DS].reshape(H // DS, DS, W // DS, DS).min(axis=(1, 3))
h, w = g.shape
dark = g < 150
# cut at the facade (portico columns line ~ src y 4472) so the portico/vestibules are excluded:
# everything below the inner facade wall line becomes background, then we add the facade separately
cut_y = (4235 - Y0) // DS
dark[cut_y:, :] = False
# flood fill background from the border through non-dark pixels
# region of interest in plan metres; everything outside it is background
yy, xx = np.mgrid[0:h, 0:w]
U = ((yy * DS + Y0) - CY) * S; V = ((xx * DS + X0) - CX) * S
roi = (U > -79.5) & (U < 122) & (np.abs(V) < 81.5)
bg = ~roi
def dil(m, r):
    for _ in range(r):
        n = m.copy(); n[1:, :] |= m[:-1, :]; n[:-1, :] |= m[1:, :]; n[:, 1:] |= m[:, :-1]; n[:, :-1] |= m[:, 1:]; m = n
    return m
R = int(2.6 / (S * DS))
darkc = dil(dark, R)
bg &= ~darkc
free = ~darkc
for it in range(4000):
    nb = bg.copy()
    nb[1:, :] |= bg[:-1, :]; nb[:-1, :] |= bg[1:, :]; nb[:, 1:] |= bg[:, :-1]; nb[:, :-1] |= bg[:, 1:]
    nb &= free
    if (nb == bg).all(): break
    bg = nb
print('flood iterations', it)
inside = ~dil(bg, R)          # erode the building blob back by the closing radius
# keep the largest component (the basilica) via another flood from the dome centre
seed = ((CY - Y0) // DS, (CX - X0) // DS)
comp = np.zeros_like(inside); comp[seed] = True
for it in range(4000):
    nb = comp.copy()
    nb[1:, :] |= comp[:-1, :]; nb[:-1, :] |= comp[1:, :]; nb[:, 1:] |= comp[:, :-1]; nb[:, :-1] |= comp[:, 1:]
    nb &= inside
    if (nb == comp).all(): break
    comp = nb
# boundary trace (Moore neighbour) starting at the top-most pixel
ys, xs = np.nonzero(comp)
start = (ys.min(), xs[ys == ys.min()].min())
dirs = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
def ins(p): return 0 <= p[0] < h and 0 <= p[1] < w and comp[p]
path = [start]; cur = start; back = 6  # came from the west
for step in range(200000):
    for k in range(8):
        d = (back + 1 + k) % 8
        nxt = (cur[0] + dirs[d][0], cur[1] + dirs[d][1])
        if ins(nxt):
            back = (d + 4) % 8
            cur = nxt; break
    if cur == start and len(path) > 10: break
    path.append(cur)
print('boundary px', len(path))
pts = [(((y * DS + Y0) - CY) * S, ((x * DS + X0) - CX) * S) for (y, x) in path]   # (u, v)
ring = simplify_ring(pts, 0.35)
print('ring', len(ring))
json.dump({'outline': ring, 'note': 'u east (toward facade), v north; traced from Fontana 1694 plan, cut at inner facade wall'},
          open('/home/kazu/work/demos/vatican/tools/ref/basilica_outline.json', 'w'))
# preview svg
svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="1100" viewBox="-90 -90 230 180"><rect x="-90" y="-90" width="230" height="180" fill="#fff"/>']
svg.append('<polygon points="%s" fill="#ddd" stroke="#000" stroke-width="0.25"/>' % ' '.join(f'{p[0]:.2f},{-p[1]:.2f}' for p in ring))
for gx in range(-80, 140, 20): svg.append(f'<line x1="{gx}" y1="-90" x2="{gx}" y2="90" stroke="#0a0" stroke-width="0.1"/><text x="{gx}" y="88" font-size="3">{gx}</text>')
for gy in range(-80, 90, 20): svg.append(f'<line x1="-90" y1="{gy}" x2="140" y2="{gy}" stroke="#0a0" stroke-width="0.1"/><text x="-89" y="{gy}" font-size="3">{-gy}</text>')
svg.append('</svg>')
open('/tmp/claude-1000/-home-kazu-work-demos/1f48e580-beae-4176-8eee-fdee54a01026/scratchpad/outline.svg', 'w').write('\n'.join(svg))
