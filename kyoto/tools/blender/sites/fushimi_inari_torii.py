"""伏見稲荷大社: torii.  Inari torii (稲荷鳥居 = 台輪鳥居: vermilion pillars and 島木, black 笠木 and 根巻, a 貫 through the
pillars, a 額束 with the 稲荷大神 plaque on the bigger ones), built once per size as a template and instanced by the
thousand (the 千本鳥居 and the mountain tunnels), plus the stone torii of the 神蹟 and the miniature votive torii of the
お塚.

Template frame: the span along x (pillars at x = ±span/2), the path along y with +y = uphill (the back of the torii:
the donor's inscription panels face uphill, 奉 / 納 face the worshipper coming up), z up from the path surface.
Vertices below z = -0.2 are the pillar feet: each instance pushes them down to the terrain under its pillars."""
import math
import numpy as np
import jk
from jk import prim

# size classes: pillar segments, black sheath (根巻) with a lip, stone footing (亀腹), collar (台輪), plaque (額);
# pk / pn: 笠木 / 貫 projection beyond the pillar centres (x span); gap: 貫 top -> 島木 (x d); lift: end upturn (x H)
CLS = {
    'S': dict(seg=8, lip=False, base=False, daiwa=False, plaque=False, pk=0.17, pn=0.10, gap=1.5, lift=0.022, nk=4),
    'M': dict(seg=10, lip=True, base=False, daiwa=False, plaque=True, pk=0.25, pn=0.15, gap=1.35, lift=0.028, nk=5),
    'L': dict(seg=12, lip=True, base=True, daiwa=True, plaque=True, pk=0.33, pn=0.22, gap=1.2, lift=0.032, nk=6),
    'XL': dict(seg=16, lip=True, base=True, daiwa=True, plaque=False, pk=0.52, pn=0.40, gap=1.05, lift=0.036, nk=9),
}

def _panel(B, axis, z0, z1, side, nface, seg, uv_u, uv_v, tag='detail'):
    """a strip on the faces of a pillar (a `seg`-gon: prim.cyl puts vertex i at angle 2*pi*i/seg from +y) facing +y
    (side=+1) or -y (side=-1), nface faces either side of the centre vertex, z0..z1: axis(z) -> (x, radius);
    vermilion with the inscription program (c1.y = 7: black brush strokes)"""
    P = []; UV = []; N = []
    t0 = 0.0 if side > 0 else math.pi
    ks = range(-nface, nface + 1)
    for j, k in enumerate(ks):
        t = t0 + 2 * math.pi * k / seg
        uu = uv_u[0] + (uv_u[1] - uv_u[0]) * j / (2 * nface)
        for z, vv in ((z0, uv_v[0]), (z1, uv_v[1])):
            cx, rr = axis(z)
            P.append((cx + rr * math.sin(t), rr * math.cos(t), z)); UV.append((uu, vv))
            N.append((math.sin(t), math.cos(t), 0.0))
    I = []
    for k in range(2 * nface):
        a = 2 * k
        I += [[a, a + 2, a + 3], [a, a + 3, a + 1]]
    P = np.array(P); I = np.array(I); N = np.array(N)
    fn = np.cross(P[I[0][1]] - P[I[0][0]], P[I[0][2]] - P[I[0][0]])
    if fn @ N[I[0][0]] < 0: I = I[:, ::-1]
    B.add(P, I, 'vermilion', UV=np.array(UV), N=N, tag=tag, c1=(0, 7, 0, 0))

def _head(B, xs_half, z_bot, h, w_bot, w_top, lift, mat, nk, tag='main', open_top=False):
    """a beam with upturned ends (笠木 / 島木): swept along x from -xs_half to xs_half, section w x h (wider at the top);
    the end faces are square to the upturned axis, so they read as the slanted cut of a 明神 笠木"""
    if nk <= 4: xs = np.array([-1.0, -0.55, 0.55, 1.0]) * xs_half
    else: xs = np.unique(np.round(np.concatenate([[-1.0, -0.72], np.linspace(-0.45, 0.45, max(2, nk - 3)), [0.72, 1.0]]) * xs_half, 5))
    zc = z_bot + h / 2 + lift * (np.abs(xs) / xs_half) ** 2.2
    path = np.stack([xs, np.zeros_like(xs), zc], 1)
    if not open_top:
        prof = [(-w_bot / 2, -h / 2), (w_bot / 2, -h / 2), (w_top / 2, h / 2), (-w_top / 2, h / 2)]
        prim.sweep(B, path, prof, mat, up=(0, 0, 1), tag=tag, caps=True)
        return
    prof = [(-w_top / 2, h / 2), (-w_bot / 2, -h / 2), (w_bot / 2, -h / 2), (w_top / 2, h / 2)]
    prim.sweep(B, path, prof, mat, up=(0, 0, 1), closed=False, tag=tag)
    T = np.gradient(path, axis=0)
    for i, sg in ((0, -1), (len(xs) - 1, 1)):
        d, a, b = prim._frame(T[i])
        Q = np.array([path[i] + a * x + b * y for (x, y) in prof]); I = [[0, 1, 2], [0, 2, 3]]
        if np.cross(Q[1] - Q[0], Q[2] - Q[0]) @ (d * sg) < 0: I = [[0, 2, 1], [0, 3, 2]]
        B.add(Q, I, mat, tag=tag)

def inari_torii(B, H, span, d, cls='S', inscribe=True, black_head=True, color='vermilion', plaque=None):
    """one Inari torii at the origin (see the module doc).  H: top of the 笠木 at the centre, span: pillar centres,
    d: pillar diameter (号 x 3 cm)"""
    c = CLS[cls]; r = d / 2; seg = c['seg']
    hk = 0.62 * d; hs = 0.72 * d                    # 笠木 / 島木 heights
    zk0 = H - hk; zs0 = zk0 - hs                    # their bottoms
    lean = H * 0.022                                # 内転び
    zsh = 0.25 * H if cls == 'XL' else max(0.42, 0.21 * H)        # 根巻 top
    zp1 = zs0 - (0.28 * d if c['daiwa'] else 0.0)                  # pillar top (under the 台輪)
    zn1 = zs0 - c['gap'] * d; hn = 0.72 * d; zn0 = zn1 - hn         # 貫
    za = zsh - 0.06
    for s in (-1, 1):
        xb = s * span / 2; xt = s * (span / 2 - lean)
        def axis(z, xb=xb, xt=xt):
            t = (z - za) / (zp1 - za)
            return xb + (xt - xb) * z / zp1, r * (1.0 - 0.07 * t) * 1.015
        prim.cyl(B, (axis(za)[0], 0, za), (xt, 0, zp1), r, r * 0.93, seg, color, caps=(False, False))
        rs = r * 1.13
        if c['lip']:
            prim.lathe(B, (xb, 0, 0), [(rs, -0.3), (rs, zsh), (r * 0.99, zsh + 0.03)], seg, 'black_lacquer')
        else:
            prim.cyl(B, (xb, 0, -0.3), (xb, 0, zsh), rs, rs, seg, 'black_lacquer', caps=(False, False))
        if c['base']:
            prim.lathe(B, (xb, 0, 0), [(r * 1.75, -0.3), (r * 1.75, 0.05), (r * 1.45, 0.16), (rs * 1.01, 0.2)], 8, 'stone', smooth=False)
        if c['daiwa']:
            prim.cyl(B, (xt, 0, zp1 - 0.01), (xt, 0, zs0), r * 1.22, r * 1.22, seg, color, caps=(True, False), tag='detail')
        if inscribe:
            # the donor's panel on the uphill face: date / address / company / name in vertical brush lines
            p0 = zsh + 0.1; p1 = zn0 - 0.1
            if p1 - p0 > 0.3:
                _panel(B, axis, p0, p1, +1, 1 if seg <= 10 else 2, seg, (0.0, 0.5), (0.02, 0.02 + (p1 - p0) * 0.85))
            # 奉 (right pillar, seen walking up) / 納 (left): one big glyph each under the 貫
            g1 = zn0 - 0.05; g0 = g1 - max(0.12, 1.2 * d)
            _panel(B, axis, g0, g1, -1, 1, seg, (0.0, 0.25), (0.0, 1.0 / 9.0))
    # 貫 through the pillars
    pn = c['pn'] * span + r
    prim.obox(B, (-span / 2 - pn, 0, (zn0 + zn1) / 2), (span / 2 + pn, 0, (zn0 + zn1) / 2), 0.5 * d, hn, color)
    # 額束
    prim.box(B, -0.38 * d, -0.26 * d, zn1 - 0.01, 0.38 * d, 0.26 * d, zs0 + 0.01, color, faces='xXyY')
    # 島木 (vermilion) + 笠木 (black)
    ext = span / 2 + c['pk'] * span
    lift = c['lift'] * H
    _head(B, ext * 0.96, zs0, hs, 0.92 * d, 0.98 * d, lift * 0.85, color, c['nk'], open_top=True)
    _head(B, ext, zk0, hk, 1.12 * d, 1.3 * d, lift, 'black_lacquer' if black_head else color, c['nk'])
    if (c['plaque'] if plaque is None else plaque) and inscribe:
        # 額 "稲荷大神": a black board in a gilt frame on the strut, facing downhill
        # it hangs in front of the 島木 and reaches down over the 貫 (the photos: top under the 笠木, bottom at the 貫)
        pw, ph = 1.8 * d, 3.0 * d
        zc = zs0 + 0.62 * d - ph / 2
        y0 = -0.5 * d - 0.012
        prim.box(B, -pw / 2, y0 - 0.045, zc - ph / 2, pw / 2, y0, zc + ph / 2, 'gold', tag='detail', faces='xXyZz')
        prim.box(B, -pw * 0.36, y0 - 0.053, zc - ph * 0.4, pw * 0.36, y0 - 0.035, zc + ph * 0.4, 'black_lacquer', tag='detail', faces='y')

class Template:
    """geometry built once in the template frame and placed many times: one B.add per part for all instances"""
    def __init__(self, fn, *a, **kw):
        tb = jk.Builder('tpl')
        fn(tb, *a, **kw)
        self.parts = tb.parts
        self.inst = []
        self.ntri_each = sum(len(p['I']) for p in self.parts)
    def add(self, x, y, z, yaw, dzl=0.0, dzr=0.0, seed=0):
        """yaw: the template's +x axis direction (world, ccw from east); dzl / dzr (<= 0) lower the left / right feet"""
        self.inst.append((x, y, z, yaw, min(0.0, dzl), min(0.0, dzr), seed % 251))
    def flush(self, B, tag=None):
        if not self.inst: return 0
        A = np.array(self.inst, float); n = len(A)
        c = np.cos(A[:, 3])[:, None]; s = np.sin(A[:, 3])[:, None]
        ntri = 0
        for p in self.parts:
            P = p['P'].astype(np.float64); N = p['N'].astype(np.float64); m = len(P)
            foot = (P[:, 2] < -0.2)[None, :]; left = (P[:, 0] < 0)[None, :]
            X = P[None, :, 0]; Y = P[None, :, 1]
            Wx = X * c - Y * s + A[:, 0:1]; Wy = X * s + Y * c + A[:, 1:2]
            Wz = P[None, :, 2] + A[:, 2:3] + np.where(left, A[:, 4:5], A[:, 5:6]) * foot
            Pw = np.stack([Wx, Wy, Wz], -1).reshape(-1, 3)
            Nx = N[None, :, 0] * c - N[None, :, 1] * s; Ny = N[None, :, 0] * s + N[None, :, 1] * c
            Nw = np.stack([Nx, Ny, np.broadcast_to(N[None, :, 2], Nx.shape)], -1).reshape(-1, 3)
            I = (p['I'][None, :, :] + (np.arange(n) * m)[:, None, None]).reshape(-1, 3)
            c1 = np.tile(p['c1'], (n, 1))
            if p['c1'][:, 1].max() == 7: c1[:, 2] = np.repeat(A[:, 6].astype(np.uint8), m)
            B.add(Pw, I, p['mat'], UV=np.tile(p['UV'], (n, 1)), N=Nw, tag=tag or p['tag'], c0=np.tile(p['c0'], (n, 1)), c1=c1)
            ntri += len(I)
        self.inst = []
        return ntri

def mini_torii(tb, h=0.6, span=None, black=True, color='vermilion'):
    """お塚の小鳥居: a votive miniature (S号 ~0.2 m … 1号 ~0.8 m): square posts, 貫, black-topped 笠木"""
    span = span or h * 0.85
    w = max(0.025, h * 0.065)
    for s in (-1, 1):
        prim.box(tb, s * span / 2 - w / 2, -w / 2, -0.25, s * span / 2 + w / 2, w / 2, h * 0.86, color, faces='xXyY')
    prim.box(tb, -span / 2 - w * 1.6, -w * 0.35, h * 0.62, span / 2 + w * 1.6, w * 0.35, h * 0.62 + w * 0.9, color, faces='xXyYZz')
    prim.box(tb, -span / 2 - w * 2.6, -w * 0.75, h * 0.86, span / 2 + w * 2.6, w * 0.75, h * 0.86 + w * 0.8, color, faces='xXyYz')
    prim.box(tb, -span / 2 - w * 3.0, -w * 0.85, h * 0.86 + w * 0.8, span / 2 + w * 3.0, w * 0.85, h, 'black_lacquer' if black else color, faces='xXyYZz')

def stone_torii(tb, H, span, d):
    """a granite 明神鳥居 (the 神蹟 and the お塚 parent mounds): grey, no black parts, no sheath"""
    r = d / 2; lean = H * 0.025
    for s in (-1, 1):
        prim.cyl(tb, (s * span / 2, 0, -0.3), (s * (span / 2 - lean), 0, H * 0.84), r, r * 0.92, 10, 'stone', caps=(False, False))
        prim.lathe(tb, (s * span / 2, 0, 0), [(r * 1.6, -0.3), (r * 1.6, 0.12), (r * 1.1, 0.16)], 8, 'stone', smooth=False)
    prim.obox(tb, (-span / 2 - 1.6 * d, 0, H * 0.66), (span / 2 + 1.6 * d, 0, H * 0.66), 0.55 * d, 0.7 * d, 'stone')
    prim.box(tb, -0.35 * d, -0.25 * d, H * 0.66 + 0.35 * d, 0.35 * d, 0.25 * d, H * 0.84, 'stone', faces='xXyY')
    ext = span / 2 + 0.3 * span
    _head(tb, ext * 0.95, H * 0.84, 0.6 * d, 0.85 * d, 0.9 * d, H * 0.02, 'stone', 5, open_top=True)
    _head(tb, ext, H * 0.84 + 0.6 * d, 0.6 * d, 1.0 * d, 1.15 * d, H * 0.03, 'stone', 5)

def block_feet(B, pts, half=0.05):
    """walk blockers around pillar feet (the walk map has 0.5 m cells): small squares"""
    P = []; I = []
    for (x, y, z) in pts:
        k = len(P)
        P += [(x - half, y - half, z), (x + half, y - half, z), (x + half, y + half, z), (x - half, y + half, z)]
        I += [[k, k + 1, k + 2], [k, k + 2, k + 3]]
    if P: B.add(np.array(P), np.array(I), 'stone', tag='block')
