"""Night sky for the bake and the viewer (venv python):  python night_sky.py SRC.hdr OUT_PREFIX
Stars and the Milky Way from a Poly Haven night HDRI; the bright glow on its horizon is replaced by a smooth
gradient with a faint warm city glow; the whole sky is scaled to moonlit-night levels; a small moon disc is added
at az 120 deg (over the lagoon), el 32 deg.  Writes OUT.hdr, OUT_2k.hdr and OUT.json (moon = 'sun' fields)."""
import sys, json, math
import numpy as np, cv2

MOON_AZ, MOON_EL, MOON_R = 120.0, 32.0, 0.6          # degrees (disc drawn larger than the real 0.27 for the eye)
SKY_HORIZ = 0.012                                    # target horizontal sky irradiance (day sky is ~0.85)
MOON_E = 0.035                                       # moon irradiance on a surface facing it

def main():
    src, out = sys.argv[1], sys.argv[2]
    im = cv2.imread(src, cv2.IMREAD_ANYDEPTH | cv2.IMREAD_COLOR)[:, :, ::-1].astype(np.float32)
    H, W, _ = im.shape
    th = (np.arange(H) + 0.5) / H * math.pi; el = 90 - np.degrees(th)
    # smooth per-row background (median) and the stars on top of it
    med = np.median(im, axis=1)                                         # (H, 3)
    k = 31; pad = np.pad(med, ((k, k), (0, 0)), mode='edge')
    smooth = np.stack([np.convolve(pad[:, c], np.ones(2 * k + 1) / (2 * k + 1), mode='same')[k:-k] for c in range(3)], 1)
    # stars: point-like detail only (image minus its local blur), so lamp glows and haze in the source drop out
    blur = cv2.GaussianBlur(im, (0, 0), 4.0)
    stars = np.clip(im - blur * 1.05, 0, None)
    w_stars = np.clip((el - 12.0) / 10.0, 0, 1)[:, None, None]
    sky = smooth[:, None, :] * np.ones((1, W, 1)) + stars * w_stars
    # cool it toward a deep blue; a warm haze glow just above the horizon (city lights in the mist)
    lum = sky @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    blue = np.array([0.55, 0.75, 1.25], np.float32)
    sky = sky * 0.4 + lum[..., None] * blue * 0.6
    glow = (np.exp(-np.clip(el, 0, None) / 3.0) * (el >= -0.5))[:, None, None] * np.array([1.0, 0.7, 0.45], np.float32)
    # solid angle per pixel and the horizontal irradiance -> scale
    sa = (np.sin(th) * (math.pi / H) * (2 * math.pi / W))[:, None]
    up = (el > 0)[:, None]
    def horiz(img): return ((img * (np.cos(th)[:, None] * up)[..., None]) * sa[..., None]).sum(axis=(0, 1))
    sky *= SKY_HORIZ / max(1e-9, float(horiz(sky).mean()))
    sky += glow * (0.05 * SKY_HORIZ / max(1e-9, float(horiz(glow * np.ones((1, W, 1))).mean())))
    # ground half: the horizon's haze, dimming downward (the lagoon beyond the water plane reads as the same haze)
    k0 = int(np.argmin(np.abs(el - 0.5)))
    hz = sky[k0].mean(axis=0)[None, None, :]
    fall = (0.25 + 0.75 * np.exp(np.clip(el, None, 0) / 4.0))[:, None, None]
    sky = np.where((el < 0)[:, None, None], hz * fall, sky)
    # the moon disc (equirect convention of sky_prep.py: compass az of column x)
    u = (np.arange(W) + 0.5) / W; phi = (u - 0.5) * 2 * math.pi
    DX = -np.cos(phi)[None, :] * np.sin(th)[:, None]; DY = np.sin(phi)[None, :] * np.sin(th)[:, None]; DZ = np.cos(th)[:, None] * np.ones((1, W))
    md = np.array([math.sin(math.radians(MOON_AZ)) * math.cos(math.radians(MOON_EL)), math.cos(math.radians(MOON_AZ)) * math.cos(math.radians(MOON_EL)), math.sin(math.radians(MOON_EL))])
    cosang = DX * md[0] + DY * md[1] + DZ * md[2]
    disc = cosang >= math.cos(math.radians(MOON_R))
    halo = np.exp(-np.degrees(np.arccos(np.clip(cosang, -1, 1))) / 6.0) * 0.4 * SKY_HORIZ
    sky += halo[..., None] * np.array([0.8, 0.9, 1.0], np.float32)
    sky = sky.astype(np.float32)
    cv2.imwrite(out + '.hdr', sky[:, :, ::-1].copy())                   # bake: the moon itself is a sun lamp
    sky[disc] = np.array([1.0, 1.0, 0.95], np.float32) * (MOON_E / max(1e-9, float((sa * disc).sum())))
    cv2.imwrite(out + '_2k.hdr', cv2.resize(sky.astype(np.float32), (2048, 1024), interpolation=cv2.INTER_AREA)[:, :, ::-1].copy())   # viewer: with the disc
    # the bake uses a sun lamp for the moon, so the json carries its irradiance and direction (disc kept dim in the bake)
    json.dump({'src': src, 'sun_el': MOON_EL, 'sun_az': MOON_AZ, 'sun_rgb': [MOON_E * 0.85, MOON_E * 0.92, MOON_E * 1.0],
               'sky_horiz': [float(v) for v in horiz(sky)], 'moon': True}, open(out + '.json', 'w'), indent=1)
    print('night sky: horizontal irradiance', horiz(sky), 'moon', MOON_E)

if __name__ == '__main__':
    main()
