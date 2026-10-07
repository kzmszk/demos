"""Evening grade for a prepared sky (sky_prep.py output, sun at its azimuth, disc removed): a warm glow along the
horizon that is strongest under the sun, a pink band opposite (the belt of Venus), a deeper blue overhead.
  python sky_grade.py ASSETS/sky/autumn_2k.hdr ASSETS/sky/autumn.json ../public/tex/sky_autumn.hdr [--preview out.jpg]
Equirect convention as in sky_prep.py (column phi = (u - 0.5) * 2pi -> dir = (-cos phi, sin phi) horizontally)."""
import sys, json, math, shutil
import numpy as np, cv2

GRADE = {
    # warm: tint of the horizon glow (multiplied), its height (rad), its strength toward / away from the sun
    'autumn': dict(warm=(1.75, 0.98, 0.55), wh=0.16, ws=1.0, wa=0.30, belt=(1.18, 0.92, 1.06), bh=0.30, bs=0.55,
                   zen=(0.62, 0.70, 0.98), zh=(0.10, 0.85), gain=0.92, ground=0.75),
    'winter': dict(warm=(1.45, 1.0, 0.72), wh=0.12, ws=0.85, wa=0.22, belt=(1.12, 0.93, 1.08), bh=0.28, bs=0.6,
                   zen=(0.74, 0.76, 0.96), zh=(0.10, 0.85), gain=0.92, ground=0.8),
}

def grade(im, sun_az, g):
    H, W, _ = im.shape
    th = (np.arange(H) + 0.5) / H * math.pi
    e = (math.pi / 2 - th)[:, None]                                  # elevation
    ph = ((np.arange(W) + 0.5) / W - 0.5) * 2 * math.pi
    az = np.arctan2(-np.cos(ph), np.sin(ph))[None, :]               # compass azimuth (rad, cw from north)
    ca = np.cos(az - math.radians(sun_az))                            # 1 toward the sun, -1 away
    toward = ((1 + ca) / 2) ** 3
    away = ((1 - ca) / 2) ** 2
    ep = np.maximum(e, 0.0)
    wg = np.exp(-ep / g['wh']) * (g['wa'] + (g['ws'] - g['wa']) * toward)
    bg = np.exp(-((ep - g['bh'] * 0.45) / (g['bh'] * 0.5)) ** 2) * away * g['bs']
    s = np.clip((ep - g['zh'][0]) / (g['zh'][1] - g['zh'][0]), 0, 1); zg = s * s * (3 - 2 * s)
    out = im.copy()
    for c in range(3):
        f = 1 + (g['warm'][c] - 1) * wg
        f = f * (1 + (g['belt'][c] - 1) * bg)
        f = f * (1 + (g['zen'][c] - 1) * zg)
        out[..., c] *= f
    out[(e < 0)[:, 0]] *= g['ground']
    return out * g['gain']

def main():
    src, info, dst = sys.argv[1:4]
    season = 'winter' if 'winter' in src else 'autumn'
    I = json.load(open(info))
    im = cv2.imread(src, cv2.IMREAD_ANYDEPTH | cv2.IMREAD_COLOR)[:, :, ::-1].astype(np.float32)
    out = grade(im, I['sun_az'], GRADE[season])
    cv2.imwrite(dst, out[:, :, ::-1].copy())
    shutil.copy(info, dst[:-4] + '.json')
    if '--preview' in sys.argv:
        p = sys.argv[sys.argv.index('--preview') + 1]
        def tm(a):
            a = a * 0.5; a = a / (1 + a); return (np.clip(a, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
        H = im.shape[0]
        both = np.concatenate([tm(im[: H // 2 + H // 16]), tm(out[: H // 2 + H // 16])], 0)
        cv2.imwrite(p, cv2.resize(both, (1024, both.shape[0] * 1024 // both.shape[1]))[:, :, ::-1])
    print(dst, 'mean', out.reshape(-1, 3).mean(0))

if __name__ == '__main__':
    main()
