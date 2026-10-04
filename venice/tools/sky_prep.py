"""Remove the sun disc from a puresky HDRI, measure its irradiance and direction, rotate the sky so the sun
sits at the chosen azimuth, and write: <out>.hdr (no sun, full res), <out>_2k.hdr (viewer), <out>.json.
Azimuth convention: degrees clockwise from north; world frame x = east, y = north, z = up.
Equirect convention used here and in the viewer: u = 0.5 + atan2(dir.x, dir.y)/(2*pi)  (u=0.5 -> north),
v = 0.5 - asin(dir.z)/pi (v=0 top)."""
import sys, json, math
import numpy as np, cv2
src, out, az_target = sys.argv[1], sys.argv[2], float(sys.argv[3])
im = cv2.imread(src, cv2.IMREAD_ANYDEPTH | cv2.IMREAD_COLOR)[:, :, ::-1].astype(np.float32)
H, W, _ = im.shape
lum = im @ np.array([0.2126, 0.7152, 0.0722], np.float32)
y, x = np.unravel_index(np.argmax(lum), lum.shape)
el = 90 - (y + 0.5) / H * 180
# Blender/PolyHaven equirect: u -> phi = (u-0.5)*2pi = atan2(dir.y, -dir.x)  => compass azimuth of that column:
u = (x + 0.5) / W
phi = (u - 0.5) * 2 * math.pi
dx, dy = -math.cos(phi), math.sin(phi)
az_src = math.degrees(math.atan2(dx, dy)) % 360
print('sun in source: el', round(el, 2), 'az', round(az_src, 1))
# solid angle per pixel
th = (np.arange(H) + 0.5) / H * math.pi           # polar angle from +z
sa = (np.sin(th) * (math.pi / H) * (2 * math.pi / W))[:, None]
# sun disc: pixels within 2.5 deg of the sun direction above a threshold
sun_dir = np.array([math.sin(math.radians(az_src)) * math.cos(math.radians(el)), math.cos(math.radians(az_src)) * math.cos(math.radians(el)), math.sin(math.radians(el))])
uu = (np.arange(W) + 0.5) / W; ph = (uu - 0.5) * 2 * math.pi
DX = -np.cos(ph)[None, :] * np.sin(th)[:, None]; DY = np.sin(ph)[None, :] * np.sin(th)[:, None]; DZ = np.cos(th)[:, None] * np.ones((1, W))
cosang = DX * sun_dir[0] + DY * sun_dir[1] + DZ * sun_dir[2]
ring = (cosang > math.cos(math.radians(4.0))) & (cosang < math.cos(math.radians(2.5)))
disc = cosang >= math.cos(math.radians(2.5))
ring_med = np.median(im[ring], axis=0)
excess = np.clip(im - ring_med[None, None, :], 0, None) * disc[..., None]
E = (excess * sa[..., None]).sum(axis=(0, 1))          # sun irradiance (rgb) on a surface facing the sun
im2 = im.copy(); im2[disc] = np.minimum(im[disc], ring_med * 1.6)
print('sun irradiance rgb', E, 'ring', ring_med)
# horizontal sky irradiance (diffuse only) for reference
up = DZ > 0
Ehs = ((im2 * (DZ * up)[..., None]) * sa[..., None]).sum(axis=(0, 1))
print('sky horizontal irradiance', Ehs, ' sun horizontal', E * math.sin(math.radians(el)))
# rotate columns so the sun azimuth becomes az_target: compass az increases with ... find shift empirically
def col_az(xc):
    u = (xc + 0.5) / W; phi = (u - 0.5) * 2 * math.pi
    return math.degrees(math.atan2(-math.cos(phi), math.sin(phi))) % 360
best = min(range(W), key=lambda s: abs(((col_az((x + s) % W) - az_target + 180) % 360) - 180))
im3 = np.roll(im2, best, axis=1)
print('roll', best, '-> sun az now', round(col_az((x + best) % W), 2))
cv2.imwrite(out + '.hdr', im3[:, :, ::-1].copy())
small = cv2.resize(im3, (2048, 1024), interpolation=cv2.INTER_AREA)
cv2.imwrite(out + '_2k.hdr', small[:, :, ::-1].copy())
json.dump({'src': src, 'sun_el': el, 'sun_az': az_target, 'sun_rgb': [float(v) for v in E], 'sky_horiz': [float(v) for v in Ehs], 'roll_px': best, 'width': W}, open(out + '.json', 'w'), indent=1)
