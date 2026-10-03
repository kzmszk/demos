"""Synthesize the inner-dome texture (u = angle, v = arc from springing to oculus) by back-projecting the CC0
photo '2025-03-10 St. Peter's Basilica Inside' (taken from the floor looking straight up).  Pixels outside
the photo are filled from the same height in another of the 16 identical segments (16-fold symmetry)."""
import sys, json, math
import numpy as np
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
import build_basilica_int as BI
RAW = sys.argv[1]; W, H = int(sys.argv[2]), int(sys.argv[3]); OUT = sys.argv[4]
img = np.fromfile(RAW, np.uint8).reshape(H, W, 3).astype(np.float32)
CX, CY = 805 * W / 1600, 563 * W / 1600          # oculus centre (from the 1600-px thumbnail)
F = 3830 * W / 1600                              # focal length in px (photo top edge = 3rd tier medallions, v~0.62)
CAMZ = 1.6
prof = BI.inner_profile()
arc = np.concatenate([[0], np.cumsum([math.dist(prof[i], prof[i + 1]) for i in range(len(prof) - 1)])]); arc /= arc[-1]
TW, TH = 4096, 2048
v = (np.arange(TH) + 0.5) / TH                   # 0 = springing (bottom row of the texture = v 0)
r_v = np.interp(v, arc, [p[0] for p in prof]); z_v = np.interp(v, arc, [p[1] for p in prof])
rho = F * r_v / (z_v - CAMZ)                     # photo radius for each v
theta = (np.arange(TW) + 0.5) / TW * 2 * math.pi
out = np.zeros((TH, TW, 3), np.float32); filled = np.zeros((TH, TW), bool)
def sample(px, py):
    x0 = np.clip(np.floor(px).astype(int), 0, W - 2); y0 = np.clip(np.floor(py).astype(int), 0, H - 2)
    fx = (px - x0)[..., None]; fy = (py - y0)[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
TT, RR = np.meshgrid(theta, rho)
best_margin = np.full((TH, TW), -1e9)
for k in range(16):                              # try the same point rotated by k segments; keep the most inside
    t = TT + k * 2 * math.pi / 16
    px = CX + RR * np.cos(t); py = CY - RR * np.sin(t)
    margin = np.minimum.reduce([px - 2, W - 3 - px, py - 2, H - 3 - py])
    better = margin > best_margin
    if better.any():
        val = sample(px, py)
        out[better] = val[better]; best_margin[better] = margin[better]
print('unfilled (outside photo for every rotation):', int((best_margin < 0).sum()))
# rows outside the photo (the lower tiers): repeat the lowest fully covered band of tiers (panel + medallion)
cov = (best_margin >= 0).mean(1) > 0.98
good = int(np.where(cov)[0].min())
band = int(0.30 * TH)                            # one panel+medallion period in v
print('lowest covered row', good, 'v=', round(good / TH, 3))
for r in range(good - 1, -1, -1):
    src = good + ((good - 1 - r) % band)
    src = min(TH - 1, src)
    out[r] = out[src] * 0.98
out = np.clip(out, 0, 255).astype(np.uint8)[::-1]      # image row 0 = top = oculus (v = 1)
out.tofile(OUT)
print('wrote', OUT, out.shape)
