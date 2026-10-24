"""Procedural textures for the roppongi hero district (numpy + PIL; run with the kyoto-assets venv python).
   python textures.py [names...]   -> writes PNGs to <assets>/work/tex/
All colour textures are albedo only (no AO). Tiling ones wrap seamlessly.
"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTD = '/home/kazu/work/tokyo2090-assets/hero/roppongi/work/tex/'
os.makedirs(OUTD, exist_ok=True)
R = np.random.default_rng


# ------------------------------------------------------------ periodic noise
def pnoise(h, w, cy, cx, seed, smooth=Image.BICUBIC):
    """periodic value noise (h,w) with cy x cx cells, values ~[0,1]"""
    g = R(seed).random((cy, cx)).astype(np.float32)
    t = np.tile(g, (3, 3))
    im = Image.fromarray(t, mode='F').resize((cx * 3 * (w // cx), cy * 3 * (h // cy)), smooth)
    a = np.asarray(im)
    a = a[cy * (h // cy):cy * (h // cy) + h, cx * (w // cx):cx * (w // cx) + w]
    return np.clip(a, 0, 1)


def pfbm(h, w, c, seed, oct=5, gain=0.5):
    t = np.zeros((h, w), np.float32); amp = 1.0; s = 0
    for o in range(oct):
        cc = c * (2 ** o)
        if cc > min(h, w) // 2:
            break
        t += amp * pnoise(h, w, cc, cc * w // h if w != h else cc, seed + o * 31)
        s += amp; amp *= gain
    return t / s


def ridge(n):
    return 1 - np.abs(2 * n - 1)


def lerp(a, b, t):
    t = np.asarray(t)[..., None] if np.ndim(t) == 2 else t
    return a + (b - a) * t


def col(*c):
    return np.array(c, np.float32)


def save(name, rgb, alpha=None):
    rgb = np.clip(rgb, 0, 1)
    a8 = (rgb * 255 + 0.5).astype(np.uint8)
    if alpha is not None:
        a8 = np.dstack([a8, (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)])
        Image.fromarray(a8, 'RGBA').save(OUTD + name + '.png')
    else:
        Image.fromarray(a8, 'RGB').save(OUTD + name + '.png')
    print('wrote', name, a8.shape)


def srgb(c):
    return np.asarray(c, np.float32)


# ------------------------------------------------------------ concrete (tiling, 1 tile = 4 m)
def concrete(S=1024, seed=1, moss=0.25):
    n1 = pfbm(S, S, 4, seed); n2 = pfbm(S, S, 16, seed + 5); n3 = pfbm(S, S, 64, seed + 9, oct=3)
    base = col(0.66, 0.64, 0.60)
    c = np.ones((S, S, 3), np.float32) * base
    c *= (0.86 + 0.22 * n1[..., None]) * (0.93 + 0.12 * n2[..., None]) * (0.95 + 0.08 * n3[..., None])
    # vertical rain streaks (darker, warm)
    sx = pnoise(S, S, 2, 48, seed + 11, Image.BICUBIC)
    sy = pnoise(S, S, 6, 2, seed + 12)
    streak = np.clip((sx - 0.6) * 2.5, 0, 1) * (0.3 + 0.7 * sy)
    c = lerp(c, c * col(0.72, 0.68, 0.62), streak * 0.6)
    # formwork panel joints (every 1 m horizontally, 0.6 m vertically) + tie holes
    yy, xx = np.mgrid[0:S, 0:S]
    jx = (xx % (S // 4)) < 2; jy = (yy % (S // 6)) < 2
    c[jx | jy] *= 0.85
    th = (((xx + S // 16) % (S // 8)) - S // 16) ** 2 + ((((yy + S // 24) % (S // 12)) - S // 24) ** 2) < 9
    c[th] *= 0.55
    # moss patches (low, green-olive) and dark lichen
    m = np.clip((pfbm(S, S, 6, seed + 20) - (0.62 - moss * 0.3)) * 5, 0, 1) * (0.6 + 0.4 * n3)
    c = lerp(c, col(0.26, 0.31, 0.15) * (0.8 + 0.4 * n2[..., None]), m * 0.85)
    lich = np.clip((pnoise(S, S, 48, 48, seed + 30) - 0.8) * 6, 0, 1)
    c = lerp(c, col(0.35, 0.33, 0.28), lich * 0.5)
    return c


def tex_concrete():
    save('conc', concrete())


# ------------------------------------------------------------ moss / growth top surfaces (tiling, 4 m)
def tex_top(S=1024, seed=40):
    n1 = pfbm(S, S, 4, seed); n2 = pfbm(S, S, 16, seed + 1); n3 = pfbm(S, S, 96, seed + 2, oct=2)
    moss = col(0.24, 0.30, 0.12) * (0.75 + 0.5 * n2[..., None]) * (0.85 + 0.3 * n3[..., None])
    moss = lerp(moss, col(0.36, 0.38, 0.16), np.clip((n1 - 0.5) * 3, 0, 1) * 0.6)
    conc = concrete(S, seed + 3, moss=0.0) * 0.92
    bare = np.clip((pfbm(S, S, 3, seed + 4) - 0.6) * 3, 0, 1) * 0.7
    c = lerp(moss, conc, bare)
    # leaf litter speckles (brown / ochre)
    rr = R(seed + 7)
    img = Image.fromarray((c * 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    for i in range(2600):
        x, y = rr.integers(0, S, 2); a = rr.random() * math.pi
        L = rr.integers(4, 11)
        k = rr.random()
        cc = (int(120 + 60 * k), int(85 + 40 * k), int(40 + 20 * k)) if rr.random() < 0.7 else (int(70 + 40 * k), int(80 + 30 * k), 30)
        dx, dy = math.cos(a) * L, math.sin(a) * L * 0.5
        for ox in (-S, 0, S):
            for oy in (-S, 0, S):
                d.ellipse([x + ox - abs(dx), y + oy - abs(dy) - 2, x + ox + abs(dx), y + oy + abs(dy) + 2], fill=cc)
    c2 = np.asarray(img).astype(np.float32) / 255
    lit = np.clip((pfbm(S, S, 8, seed + 9) - 0.45) * 3, 0, 1)
    c = lerp(c, c2, lit * 0.9)
    save('top', c)


# ------------------------------------------------------------ granite paving (tiling, 4 m, 0.6x0.3 pavers)
def tex_pave(S=1024, seed=60):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    px = S / 4 * 0.6; py = S / 4 * 0.3            # paver in px
    row = np.floor(yy / py)
    sh = (row % 2) * px * 0.5
    cx = np.floor((xx + sh) / px)
    fx = ((xx + sh) % px) / px; fy = (yy % py) / py
    stone = R(seed).random((64, 64)).astype(np.float32)
    sv = stone[(row % 64).astype(int), (cx % 64).astype(int)]
    g = pfbm(S, S, 64, seed + 1, oct=2)
    base = col(0.58, 0.57, 0.55) * (0.82 + 0.25 * sv[..., None]) * (0.9 + 0.18 * g[..., None])
    speck = (R(seed + 2).random((S, S)) < 0.08)
    base[speck] *= 0.75
    joint = (fx < 0.03) | (fx > 0.97) | (fy < 0.05) | (fy > 0.95)
    jcol = col(0.22, 0.27, 0.12)
    c = base.copy(); c[joint] = jcol * (0.8 + 0.4 * g[joint, None])
    # moss creeping out of joints
    m = np.clip((pfbm(S, S, 6, seed + 4) - 0.5) * 4, 0, 1)
    edge = np.minimum(np.minimum(fx, 1 - fx) * px, np.minimum(fy, 1 - fy) * py)
    creep = np.clip(1 - edge / (6 + 18 * m), 0, 1) * m
    c = lerp(c, col(0.25, 0.31, 0.13) * (0.8 + 0.4 * g[..., None]), creep)
    stain = pfbm(S, S, 3, seed + 6)
    c *= (0.85 + 0.25 * stain[..., None])
    save('pave', c)


# ------------------------------------------------------------ rusted / painted metal (tiling)
def tex_metal(S=1024, seed=80):
    n1 = pfbm(S, S, 6, seed); n2 = pfbm(S, S, 32, seed + 1); n3 = pfbm(S, S, 128, seed + 2, oct=2)
    paint = col(0.52, 0.53, 0.52) * (0.9 + 0.15 * n2[..., None])
    rust = lerp(col(0.33, 0.17, 0.08), col(0.50, 0.28, 0.12), n2) * (0.8 + 0.35 * n3[..., None])
    r = np.clip((n1 * 0.7 + n3 * 0.3 - 0.45) * 5, 0, 1)
    c = lerp(paint, rust, r)
    sx = pnoise(S, S, 2, 32, seed + 5, Image.BICUBIC)
    c = lerp(c, rust * 0.85, np.clip((sx - 0.65) * 3, 0, 1) * 0.4)
    save('metal', c)


# ------------------------------------------------------------ bark (tiling; u around, v along)
def tex_bark(S=1024, seed=100):
    # vertical fissures
    a = pnoise(S, S, 12, 24, seed, Image.BICUBIC)
    a2 = pnoise(S, S, 48, 64, seed + 1)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    warp = pnoise(S, S, 4, 8, seed + 2) * 40
    stripes = 0.5 + 0.5 * np.sin((xx + warp) / S * 2 * math.pi * 14 + a * 6)
    f = np.clip(stripes ** 3, 0, 1)
    base = lerp(col(0.40, 0.37, 0.32), col(0.56, 0.53, 0.48), a2)
    c = base * (0.55 + 0.45 * (1 - f[..., None] * 0.8))
    m = np.clip((pfbm(S, S, 4, seed + 4) - 0.55) * 4, 0, 1)
    c = lerp(c, col(0.27, 0.33, 0.14) * (0.8 + 0.4 * a2[..., None]), m * 0.8)
    lich = np.clip((pnoise(S, S, 32, 32, seed + 7) - 0.75) * 5, 0, 1)
    c = lerp(c, col(0.60, 0.62, 0.52), lich * 0.5)
    save('bark', c)


# ------------------------------------------------------------ bronze (Maman) + marble strip at u>0.75
def tex_bronze(S=1024, seed=120):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    n1 = pfbm(S, S, 8, seed); n2 = pfbm(S, S, 48, seed + 1, oct=3)
    # ribbed, knobbly surface: horizontal ridges (v along the leg) with jitter
    w = pnoise(S, S, 8, 4, seed + 2) * 30
    rib = 0.5 + 0.5 * np.sin((yy + w) / S * 2 * math.pi * 26)
    base = lerp(col(0.18, 0.13, 0.09), col(0.30, 0.22, 0.14), n2) * (0.75 + 0.45 * rib[..., None])
    # verdigris patina in streaks and pits
    pat = np.clip((n1 * 0.6 + pnoise(S, S, 2, 48, seed + 3, Image.BILINEAR) * 0.4 - 0.5) * 4, 0, 1)
    c = lerp(base, col(0.24, 0.38, 0.32) * (0.8 + 0.3 * n2[..., None]), pat * 0.75)
    c = lerp(c, col(0.38, 0.30, 0.20), np.clip(rib - 0.85, 0, 1)[..., None] * 3 * 0.5)
    # marble strip
    mx = xx >= S * 0.75
    mn = pfbm(S, S, 6, seed + 9); vein = np.clip(1 - np.abs(np.sin((xx * 0.02 + mn * 9))) * 6, 0, 1)
    marble = col(0.62, 0.60, 0.56) * (0.9 + 0.12 * mn[..., None]) - vein[..., None] * col(0.15, 0.15, 0.16)
    marble = lerp(marble, col(0.45, 0.48, 0.38), np.clip((n1 - 0.6) * 3, 0, 1) * 0.5)
    c[mx] = marble[mx]
    save('bronze', c)


# ------------------------------------------------------------ facade atlas: 8 rows (one floor each), 32 m wide
FAC_ROWS = ['glass', 'glass_ruin', 'apt', 'apt_ruin', 'shop', 'tile', 'mori', 'mori_ruin']


def tex_facade(S=2048, seed=200):
    W = S; RH = S // 8; ppm = W / 32.0          # 64 px per metre horizontally; row = one floor
    out = np.zeros((S, W, 3), np.float32)
    rr = R(seed)
    yy, xx = np.mgrid[0:RH, 0:W].astype(np.float32)
    v = 1 - yy / RH       # 0 bottom .. 1 top of the floor (image rows go down)
    def streaks(sd, k=1.0):
        sx = pnoise(RH, W, 1, 128, sd, Image.BILINEAR)
        return np.clip((sx - 0.5) * 3 * k, 0, 1)
    def moss_sill(sd, h0=0.0, h1=0.12, amt=0.6):
        n = pnoise(RH, W, 2, 48, sd); n2_ = pnoise(RH, W, 4, 160, sd + 1)
        top = h1 + 0.12 * (n2_ - 0.3) + 0.1 * (n - 0.5)
        m = np.clip((n - (1 - amt)) * 3, 0, 1) * np.clip((top - v) * 25, 0, 1) * (v > h0)
        return m
    for ri, kind in enumerate(FAC_ROWS):
        n1 = pnoise(RH, W, 4, 128, seed + ri * 10); n2 = pnoise(RH, W, 16, 512, seed + ri * 10 + 1)
        if kind in ('glass', 'glass_ruin', 'mori', 'mori_ruin'):
            mori = kind.startswith('mori')
            bay = 1.6
            spand = 0.15 if mori else 0.22                     # share of floor that is spandrel (bottom)
            glass_base = col(0.17, 0.19, 0.21) if not mori else col(0.33, 0.36, 0.38)
            refl = (0.75 + 0.5 * n1[..., None]) * (0.85 + 0.3 * v[..., None])
            glass = glass_base * refl
            sp = col(0.68, 0.68, 0.66) if mori else col(0.50, 0.50, 0.49)
            spc = sp * (0.85 + 0.2 * n2[..., None])
            if mori:  # horizontal ribs on the silver spandrel
                spc *= (0.9 + 0.1 * np.sin(yy / RH * math.pi * 2 * 9))[..., None]
            c = np.where((v < spand)[..., None], spc, glass)
            # interior: per-pane broken state
            pane = np.floor(xx / (bay * ppm)).astype(int)
            pr = R(seed + ri).random(4096)
            p_broken = {'glass': 0.12, 'glass_ruin': 0.85, 'mori': 0.10, 'mori_ruin': 0.92}[kind]
            broken = pr[pane % 4096] < p_broken
            interior = col(0.05, 0.05, 0.05) * (0.7 + 0.6 * n2[..., None])
            # ceiling line + far window glow-less depth
            ceil = (v > 0.86) & (v < 0.92)
            interior = np.where(ceil[..., None], col(0.13, 0.12, 0.11), interior)
            # jagged shard edges: keep some glass near frame for broken panes
            fxp = (xx / (bay * ppm)) % 1.0
            shard = (np.abs(fxp - 0.5) > 0.42 - 0.2 * pnoise(RH, W, 6, 256, seed + ri + 5)) & (v > spand)
            bm = broken[..., None] & (v > spand)[..., None] & ~shard[..., None]
            c = np.where(bm, interior, c)
            if kind.endswith('ruin'):
                # vegetation spilling at the sill + hanging
                veg = moss_sill(seed + ri + 7, spand - 0.05, spand + 0.18, 0.75)
                hang = np.clip((pnoise(RH, W, 1, 96, seed + ri + 8, Image.BILINEAR) - 0.6) * 4, 0, 1) * (v > 0.3)
                g = col(0.20, 0.27, 0.10) * (0.7 + 0.6 * n2[..., None])
                c = lerp(c, g, np.clip(veg + hang * 0.8, 0, 1))
            # mullions
            mx = (xx % (bay * ppm)) < (9 if mori else 4)
            mcol = col(0.80, 0.80, 0.78) if mori else col(0.45, 0.46, 0.46)
            mull_present = ~(broken & (pr[(pane * 7) % 4096] < (0.5 if kind.endswith('ruin') else 0.05)))
            c = np.where((mx & mull_present & (v > spand))[..., None], mcol * (0.8 + 0.3 * n1[..., None]), c)
            tr = np.abs(v - spand) < 0.012
            c = np.where(tr[..., None], mcol * 0.8, c)
            # rust / dirt streaks below sills
            st = streaks(seed + ri + 3, 1.0 if kind.endswith('ruin') else 0.6)
            c = lerp(c, c * col(0.65, 0.55, 0.45), st * 0.6 * (v < 0.6))
            c = lerp(c, col(0.25, 0.30, 0.13), moss_sill(seed + ri + 9, 0.0, 0.05, 0.4) * 0.8)
        elif kind in ('apt', 'apt_ruin'):
            # Japanese 'mansion' bay: balcony slab edge, railing panel, recessed wall with sliding doors, unit walls
            ruin = kind == 'apt_ruin'
            unit = 6.4 * ppm
            fx = (xx % unit) / unit
            pane = np.floor(xx / unit).astype(int)
            pr = R(seed + 77).random(4096)
            recess = col(0.36, 0.35, 0.33) * (0.85 + 0.25 * n1[..., None])
            c = recess.copy()
            # sliding doors / windows in the recess (two per unit)
            dx = (fx * 2) % 1.0
            door = (dx > 0.08) & (dx < 0.92) & (v > 0.12) & (v < 0.84)
            dpane = (pane * 2 + (fx > 0.5)).astype(int)
            gone = pr[dpane % 4096] < (0.75 if ruin else 0.3)
            glass = col(0.24, 0.27, 0.29) * (0.8 + 0.4 * n1[..., None]) * (0.8 + 0.3 * v[..., None])
            dark = col(0.13, 0.12, 0.11) * (0.85 + 0.3 * n2[..., None])
            c = np.where(door[..., None], np.where(gone[..., None], dark, glass), c)
            fr = door & ((np.abs(dx - 0.5) < 0.012) | (dx < 0.1) | (dx > 0.9))
            c = np.where(fr[..., None], col(0.45, 0.45, 0.44), c)
            # slab underside shadow at the top, balcony slab edge at the bottom
            c = np.where((v > 0.88)[..., None], col(0.30, 0.29, 0.27) * (0.9 + 0.2 * n2[..., None]), c)
            slab = v < 0.10
            c = np.where(slab[..., None], col(0.70, 0.69, 0.66) * (0.88 + 0.2 * n2[..., None]), c)
            # railing panel: frosted/painted panel on most units, open bars on some, missing on ruins
            rail_z = (v >= 0.10) & (v < 0.36)
            kind_r = pr[(pane * 5) % 4096]
            panel = col(0.60, 0.60, 0.58) * (0.85 + 0.2 * n1[..., None])
            bars = np.where(((xx % 9) < 2)[..., None], col(0.32, 0.28, 0.24), c)
            rail = np.where((kind_r < 0.6)[..., None], panel, bars)
            if ruin:
                rail = np.where((pr[(pane * 11) % 4096] < 0.45)[..., None], c, rail)
            c = np.where(rail_z[..., None], rail, c)
            c = np.where(((v > 0.355) & (v < 0.375))[..., None], col(0.40, 0.36, 0.30), c)
            # unit partition walls
            wall = (fx < 0.035) | (fx > 0.965)
            c = np.where(wall[..., None], col(0.66, 0.65, 0.62) * (0.88 + 0.2 * n2[..., None]), c)
            st = streaks(seed + 88, 1.2 if ruin else 0.8)
            c = lerp(c, c * col(0.62, 0.57, 0.50), st * 0.6)
            c = lerp(c, col(0.24, 0.30, 0.12) * (0.8 + 0.4 * n2[..., None]), moss_sill(seed + 89, 0.0, 0.1, 0.7 if ruin else 0.45))
            if ruin:
                hang = np.clip((pnoise(RH, W, 1, 64, seed + 90, Image.BILINEAR) - 0.6) * 4, 0, 1)
                c = lerp(c, col(0.20, 0.27, 0.10) * (0.7 + 0.6 * n2[..., None]), hang * 0.8)
        elif kind == 'shop':
            wall = col(0.55, 0.53, 0.50) * (0.85 + 0.25 * n1[..., None])
            c = wall.copy()
            bayw = 6.4 * ppm
            fx = (xx % bayw) / bayw
            pane = np.floor(xx / bayw).astype(int)
            pr = R(seed + 99).random(4096)
            opening = (fx > 0.07) & (fx < 0.93) & (v < 0.72)
            kind_b = pr[pane % 4096]
            shutter = (kind_b < 0.45)[..., None]
            corr = 0.5 + 0.5 * np.sin(yy / RH * 2 * math.pi * 60)
            shut = lerp(col(0.42, 0.40, 0.36), col(0.48, 0.26, 0.12), np.clip(n2 * 1.4 - 0.3, 0, 1)) * (0.7 + 0.3 * corr[..., None])
            dark = col(0.05, 0.05, 0.045) * (0.8 + 0.5 * n2[..., None])
            half = (v < 0.72 * (0.3 + 0.7 * pr[(pane * 3) % 4096]))[..., None]   # half-open shutters
            oc = np.where(shutter, np.where(half, dark, shut), dark)
            c = np.where(opening[..., None], oc, c)
            # sign band
            band = (v > 0.76) & (v < 0.95)
            hue = pr[(pane * 5) % 4096]
            sc = lerp(col(0.62, 0.55, 0.45), col(0.50, 0.38, 0.33), hue)
            c = np.where(band[..., None], sc * (0.8 + 0.3 * n1[..., None]), c)
            st = streaks(seed + 101, 1.0)
            c = lerp(c, c * col(0.6, 0.55, 0.48), st * 0.6)
            c = lerp(c, col(0.24, 0.30, 0.12), moss_sill(seed + 102, 0.0, 0.08, 0.6))
        elif kind == 'tile':
            tile = col(0.62, 0.59, 0.53) * (0.85 + 0.25 * n1[..., None])
            tg = ((xx % 14) < 1.5) | ((yy % 7) < 1.2)
            c = np.where(tg[..., None], tile * 0.8, tile)
            bayw = 3.2 * ppm
            fx = (xx % bayw) / bayw
            pane = np.floor(xx / bayw).astype(int)
            pr = R(seed + 111).random(4096)
            win = (fx > 0.2) & (fx < 0.8) & (v > 0.3) & (v < 0.8)
            dark = col(0.07, 0.07, 0.065)
            glass = col(0.19, 0.21, 0.22) * (0.8 + 0.4 * n2[..., None])
            wc = np.where((pr[pane % 4096] < 0.55)[..., None], dark, glass)
            c = np.where(win[..., None], wc, c)
            sill = (fx > 0.18) & (fx < 0.82) & (v > 0.26) & (v < 0.3)
            c = np.where(sill[..., None], col(0.55, 0.55, 0.52), c)
            st = streaks(seed + 112, 1.0)
            c = lerp(c, c * col(0.55, 0.5, 0.45), st * 0.7 * (v < 0.3 + 0.7 * n1))
            c = lerp(c, col(0.24, 0.30, 0.12), moss_sill(seed + 113, 0.25, 0.32, 0.6))
        # openings: never pure black - a dim interior with a lighter ceiling and darker floor
        lum = c.mean(-1)
        hole = np.clip((0.12 - lum) * 25, 0, 1)
        inter = lerp(col(0.085, 0.080, 0.072), col(0.16, 0.15, 0.13), np.clip((v - 0.2) / 0.7, 0, 1)) * (0.85 + 0.3 * n2[..., None])
        c = lerp(c, inter, hole)
        # ivy / creeper masses climbing the wall (painted leaves), heavier on the ruin rows
        cov = {'glass_ruin': 0.2, 'apt_ruin': 0.22, 'mori_ruin': 0.12, 'apt': 0.05, 'tile': 0.06, 'shop': 0.08, 'glass': 0.02, 'mori': 0.0}[kind]
        c = ivy(c, RH, W, seed + 900 + ri, cov)
        out[ri * RH:(ri + 1) * RH] = c
    save('fac', out)


def ivy(c, RH, W, sd, cov):
    if cov <= 0:
        return c
    rr = R(sd)
    m = pnoise(RH, W, 2, 20, sd) * 0.7 + pnoise(RH, W, 4, 64, sd + 1) * 0.3
    thr = np.quantile(m, 1 - cov)
    img = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    ys, xs = np.nonzero(m > thr)
    if len(xs) == 0:
        return c
    n = int(len(xs) / 18)
    pick = rr.integers(0, len(xs), n)
    for k in pick:
        x, y = xs[k], ys[k]
        L = rr.uniform(5, 12); a = rr.uniform(0, 6.28)
        g = rr.uniform(0.6, 1.15)
        colr = (int(52 * g), int(68 * g), int(32 * g)) if rr.random() < 0.85 else (int(84 * g), int(88 * g), int(44 * g))
        dx, dy = math.cos(a) * L, math.sin(a) * L * 0.6
        for ox in (-W, 0, W):
            d.ellipse([x + ox - abs(dx), y - abs(dy) - 2, x + ox + abs(dx), y + abs(dy) + 2], fill=colr)
    return np.asarray(img).astype(np.float32) / 255


# ------------------------------------------------------------ foliage atlas 2048 RGBA, 4x4 cells of 512
LEAF_CELLS = {  # name: (col, row, w, h) in cells
    'zelkova': (0, 0, 1, 1), 'zelkova2': (1, 0, 1, 1), 'cherry': (2, 0, 1, 1), 'fig': (3, 0, 1, 1),
    'jungle': (0, 1, 1, 1), 'fern': (1, 1, 1, 1), 'reed': (2, 1, 1, 1), 'lily': (3, 1, 1, 1),
    'vine': (0, 2, 1, 2), 'vine2': (1, 2, 1, 2), 'ivy': (2, 2, 1, 1), 'grass': (3, 2, 1, 1),
    'shrub': (2, 3, 1, 1), 'bamboo': (3, 3, 1, 1),
}


def _leaf(d, x, y, L, Wd, ang, colr, serr=False):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    N = 14
    for i in range(N + 1):
        t = i / N
        w = Wd * math.sin(math.pi * t) ** 0.8 * (1 + (0.12 if serr and i % 2 else 0))
        pts.append((t * L, w))
    for i in range(N, -1, -1):
        t = i / N
        w = -Wd * math.sin(math.pi * t) ** 0.8 * (1 + (0.12 if serr and i % 2 else 0))
        pts.append((t * L, w))
    P = [(x + px * ca - py * sa, y + px * sa + py * ca) for px, py in pts]
    d.polygon(P, fill=colr)
    # midrib
    d.line([(x, y), (x + L * ca, y + L * sa)], fill=tuple(int(c * 0.8) for c in colr[:3]) + (255,), width=1)


def tex_leaves(S=2048, seed=300):
    C = S // 4
    img = Image.new('RGBA', (S, S), (60, 75, 35, 0))
    rr = R(seed)
    def cell(name):
        cx, cy, w, h = LEAF_CELLS[name]
        return cx * C, cy * C, w * C, h * C
    def cluster(name, base, n, Lr, Wr, serr=False, spread=0.42, var=0.25, twig=True):
        x0, y0, w, h = cell(name)
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        cxp, cyp = w / 2, h / 2
        if twig:
            for k in range(7):
                a = rr.random() * 2 * math.pi
                d.line([(cxp, cyp), (cxp + math.cos(a) * w * 0.4, cyp + math.sin(a) * h * 0.4)], fill=(70, 60, 45, 255), width=3)
        for i in range(n):
            r = (rr.random() ** 0.6) * spread
            a = rr.random() * 2 * math.pi
            x = cxp + math.cos(a) * r * w; y = cyp + math.sin(a) * r * h
            L = rr.uniform(*Lr); Wd = L * rr.uniform(*Wr)
            k = rr.random()
            shade = 0.65 + 0.5 * k * (1 - r / spread * 0.5)
            c = tuple(int(min(255, base[j] * shade * (1 + var * (rr.random() - 0.5)))) for j in range(3)) + (255,)
            _leaf(d, x, y, L, Wd, rr.random() * 2 * math.pi, c, serr)
        img.paste(im, (x0, y0), im)
    cluster('zelkova', (88, 118, 52), 900, (16, 30), (0.28, 0.38), True)
    cluster('zelkova2', (100, 125, 58), 800, (14, 28), (0.28, 0.38), True)
    cluster('cherry', (72, 100, 46), 650, (24, 40), (0.30, 0.42), True)
    cluster('fig', (58, 92, 40), 260, (40, 80), (0.35, 0.5), False)
    cluster('jungle', (66, 104, 42), 420, (30, 70), (0.25, 0.45), False, spread=0.45)
    cluster('shrub', (80, 108, 48), 700, (14, 26), (0.3, 0.45), False, spread=0.44)
    # fern: fronds from bottom centre
    x0, y0, w, h = cell('fern'); im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for f in range(9):
        a = math.pi * (0.15 + 0.7 * f / 8) + rr.normal() * 0.05
        L = h * rr.uniform(0.6, 0.95)
        bx, by = w / 2, h - 4
        for s in range(40):
            t = s / 40
            px = bx - math.cos(a) * L * t; py = by - math.sin(a) * L * t + (t ** 2) * L * 0.25
            pl = (1 - t) * 30 + 4
            nx, ny = math.sin(a), -math.cos(a)
            cc = (int(70 + 30 * t), int(110 + 20 * t), 45, 255)
            d.line([(px, py), (px + nx * pl, py + ny * pl + 6)], fill=cc, width=4)
            d.line([(px, py), (px - nx * pl, py - ny * pl + 6)], fill=cc, width=4)
        d.line([(bx, by), (bx - math.cos(a) * L, by - math.sin(a) * L + L * 0.25)], fill=(70, 90, 40, 255), width=3)
    img.paste(im, (x0, y0), im)
    # reeds: vertical blades from the bottom
    x0, y0, w, h = cell('reed'); im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for f in range(120):
        bx = rr.uniform(0.05, 0.95) * w; L = h * rr.uniform(0.5, 0.98); lean = rr.normal() * 0.15
        cc = (int(rr.uniform(90, 140)), int(rr.uniform(110, 140)), int(rr.uniform(45, 70)), 255)
        pts = [(bx + lean * L * (t / 10) ** 2, h - L * t / 10) for t in range(11)]
        d.line(pts, fill=cc, width=int(rr.uniform(3, 6)))
        if rr.random() < 0.15:
            tx, ty = pts[-1]; d.ellipse([tx - 5, ty - 4, tx + 5, ty + 26], fill=(110, 85, 55, 255))
    img.paste(im, (x0, y0), im)
    # lily pads (seen from above) + few pale flowers
    x0, y0, w, h = cell('lily'); im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for f in range(46):
        r = rr.uniform(22, 48); x = rr.uniform(r, w - r); y = rr.uniform(r, h - r)
        a0 = rr.uniform(0, 360)
        cc = (int(rr.uniform(55, 85)), int(rr.uniform(95, 125)), int(rr.uniform(40, 55)), 255)
        d.pieslice([x - r, y - r, x + r, y + r], a0 + 12, a0 + 348, fill=cc)
        d.line([(x, y), (x + r * math.cos(math.radians(a0 + 180)), y + r * math.sin(math.radians(a0 + 180)))], fill=(int(cc[0] * 0.8), int(cc[1] * 0.8), 40, 255), width=1)
    for f in range(7):
        x = rr.uniform(40, w - 40); y = rr.uniform(40, h - 40)
        for p in range(10):
            a = p / 10 * 2 * math.pi
            d.ellipse([x + math.cos(a) * 9 - 6, y + math.sin(a) * 9 - 6, x + math.cos(a) * 9 + 6, y + math.sin(a) * 9 + 6], fill=(225, 205, 200, 255))
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(220, 180, 60, 255))
    img.paste(im, (x0, y0), im)
    # vines: hanging strands with leaves (tall cells)
    for name, base in (('vine', (74, 104, 44)), ('vine2', (90, 112, 50))):
        x0, y0, w, h = cell(name); im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for s in range(26):
            bx = rr.uniform(0.04, 0.96) * w
            L = h * rr.uniform(0.35, 1.0)
            sway = rr.uniform(4, 18); ph = rr.uniform(0, 6)
            pts = [(bx + math.sin(ph + t * 0.05) * sway, t) for t in range(0, int(L), 6)]
            if len(pts) > 1:
                d.line(pts, fill=(80, 70, 45, 255), width=2)
            for (px, py) in pts[::2]:
                if rr.random() < 0.85:
                    Lf = rr.uniform(10, 20)
                    k = rr.random()
                    c = (int(base[0] * (0.7 + 0.5 * k)), int(base[1] * (0.7 + 0.5 * k)), int(base[2] * (0.7 + 0.5 * k)), 255)
                    _leaf(d, px, py, Lf, Lf * 0.45, math.pi / 2 + rr.normal() * 0.9, c)
        img.paste(im, (x0, y0), im)
    # ivy mat (dense, for draping over edges)
    x0, y0, w, h = cell('ivy'); im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i in range(1300):
        x = rr.uniform(0, w); y = rr.uniform(0, h) ** 1.0
        if rr.random() < (y / h) ** 2.5 * 0.9:   # thinner towards the bottom (hanging edge)
            continue
        L = rr.uniform(12, 24); k = rr.random()
        c = (int(60 + 40 * k), int(92 + 40 * k), int(36 + 15 * k), 255)
        _leaf(d, x, y, L, L * 0.55, rr.random() * 6.28, c)
    img.paste(im, (x0, y0), im)
    # grass tuft
    x0, y0, w, h = cell('grass'); im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for f in range(160):
        bx = rr.normal(0.5, 0.18) * w; L = h * rr.uniform(0.3, 0.9); lean = rr.normal() * 0.35
        cc = (int(rr.uniform(95, 150)), int(rr.uniform(115, 150)), int(rr.uniform(45, 70)), 255)
        pts = [(bx + lean * L * (t / 8) ** 2, h - L * t / 8) for t in range(9)]
        d.line(pts, fill=cc, width=3)
    img.paste(im, (x0, y0), im)
    # bamboo-ish tall leaves
    x0, y0, w, h = cell('bamboo'); im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i in range(220):
        x = rr.uniform(0.1, 0.9) * w; y = rr.uniform(0.05, 0.9) * h
        L = rr.uniform(30, 60); k = rr.random()
        _leaf(d, x, y, L, L * 0.13, math.pi / 2 + rr.normal() * 0.6, (int(80 + 30 * k), int(110 + 30 * k), 45, 255))
    img.paste(im, (x0, y0), im)
    a = np.asarray(img).astype(np.float32) / 255
    rgb = a[..., :3]; al = a[..., 3]
    # bleed colour into transparent areas (avoid dark fringes under mipmaps)
    rgbb = rgb.copy()
    m = al > 0.5
    for it in range(6):
        blur = np.asarray(Image.fromarray((rgbb * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(4))).astype(np.float32) / 255
        rgbb = np.where(m[..., None], rgb, blur)
    save('leaves', rgbb, al)


# ------------------------------------------------------------ decals 2048 RGBA, 4x4 cells
DECAL_CELLS = {'litter': (0, 0), 'litter2': (1, 0), 'crack': (2, 0), 'puddle': (3, 0),
               'gravel': (0, 1), 'moss': (1, 1), 'zebra': (2, 1), 'lane': (3, 1),
               'roots': (0, 2), 'stain': (1, 2), 'petals': (2, 2), 'mud': (3, 2),
               'streak': (0, 3), 'scum': (1, 3), 'edge': (2, 3)}


def tex_decals(S=2048, seed=400):
    C = S // 4
    rgb = np.zeros((S, S, 3), np.float32) + col(0.3, 0.3, 0.25); al = np.zeros((S, S), np.float32)
    rr = R(seed)
    yy, xx = np.mgrid[0:C, 0:C].astype(np.float32)
    rad = np.hypot(xx - C / 2, yy - C / 2) / (C / 2)
    def put(name, c, a):
        cx, cy = DECAL_CELLS[name]
        rgb[cy * C:(cy + 1) * C, cx * C:(cx + 1) * C] = c
        al[cy * C:(cy + 1) * C, cx * C:(cx + 1) * C] = a
    def blobmask(sd, k=1.0):
        n = pfbm(C, C, 4, sd)
        return np.clip((1 - rad) * 1.6 + (n - 0.5) * 1.6 * k - 0.3, 0, 1)
    def leaflitter(sd, palette):
        im = Image.new('RGBA', (C, C), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        r2 = R(sd)
        for i in range(2200):
            x, y = r2.normal(C / 2, C / 4.2, 2)
            Lf = r2.uniform(7, 16)
            k = r2.random(); p = palette[r2.integers(len(palette))]
            c = tuple(int(p[j] * (0.7 + 0.5 * k)) for j in range(3)) + (255,)
            _leaf(d, x, y, Lf, Lf * 0.45, r2.random() * 6.28, c)
        a = np.asarray(im).astype(np.float32) / 255
        return a[..., :3], a[..., 3]
    for nm, pal, sd in (('litter', [(140, 100, 50), (120, 80, 40), (150, 120, 60), (90, 100, 45)], 1),
                        ('litter2', [(110, 90, 50), (90, 110, 50), (130, 95, 45)], 2)):
        c, a = leaflitter(seed + sd, pal)
        base = col(0.22, 0.19, 0.14) * (0.8 + 0.4 * pfbm(C, C, 8, seed + sd)[..., None])
        m = blobmask(seed + 10 + sd)
        put(nm, np.where(a[..., None] > 0.5, c, base), np.clip(np.maximum(a, m * 0.95) * (m > 0.05), 0, 1) * np.clip(m * 3, 0, 1))
    # crack network
    im = Image.new('L', (C, C), 0); d = ImageDraw.Draw(im)
    for k in range(5):
        x, y = rr.uniform(0, C, 2); a = rr.uniform(0, 6.28)
        for s in range(60):
            a += rr.normal() * 0.35; nx, ny = x + math.cos(a) * 9, y + math.sin(a) * 9
            d.line([(x, y), (nx, ny)], fill=255, width=int(rr.uniform(2, 5))); x, y = nx, ny
            if rr.random() < 0.05:
                bx, by, ba = x, y, a + rr.choice([-1, 1]) * 1.2
                for t in range(15):
                    ba += rr.normal() * 0.3; nbx, nby = bx + math.cos(ba) * 7, by + math.sin(ba) * 7
                    d.line([(bx, by), (nbx, nby)], fill=200, width=2); bx, by = nbx, nby
    cm = np.asarray(im.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    cc = np.zeros((C, C, 3), np.float32) + col(0.10, 0.11, 0.07)
    grass = np.asarray(im.filter(ImageFilter.MaxFilter(7))).astype(np.float32) / 255
    cc = lerp(cc, col(0.30, 0.38, 0.15), np.clip(grass - cm, 0, 1))
    put('crack', cc, np.clip(np.maximum(cm * 1.5, grass * 0.9) * (rad < 1), 0, 1))
    # puddle: dark wet, smooth edge
    m = blobmask(seed + 20, 0.8)
    put('puddle', col(0.17, 0.18, 0.16) + pfbm(C, C, 8, seed + 21)[..., None] * 0.05, np.clip(m * 2.5, 0, 1) * 0.6)
    # gravel / rubble sheet
    im = Image.new('RGBA', (C, C), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i in range(1800):
        x, y = rr.normal(C / 2, C / 4.5, 2); r = rr.uniform(2, 11) * (1 if rr.random() < 0.9 else 2.2)
        g = rr.uniform(0.45, 0.75)
        pts = [(x + math.cos(a) * r * rr.uniform(0.6, 1.2), y + math.sin(a) * r * rr.uniform(0.6, 1.2)) for a in np.linspace(0, 6.28, 7)[:-1]]
        d.polygon(pts, fill=(int(255 * g), int(250 * g), int(238 * g), 255))
    a = np.asarray(im).astype(np.float32) / 255
    m = blobmask(seed + 30)
    put('gravel', np.where(a[..., 3:] > 0.5, a[..., :3], col(0.30, 0.28, 0.25)), np.clip(np.maximum(a[..., 3], m * 0.8) * np.clip(m * 4, 0, 1), 0, 1))
    # moss patch
    n = pfbm(C, C, 16, seed + 40)
    m = blobmask(seed + 41, 1.3)
    put('moss', col(0.22, 0.30, 0.11) * (0.7 + 0.6 * n[..., None]), np.clip(m * 2.2, 0, 1))
    # zebra stripe: one faded white bar (full cell = 0.45 x 3 m bar placed with UV), worn
    wear = pfbm(C, C, 12, seed + 50)
    bar = ((xx > C * 0.08) & (xx < C * 0.92)).astype(np.float32)
    put('zebra', col(0.78, 0.77, 0.72) * (0.85 + 0.2 * wear[..., None]), bar * np.clip((wear - 0.3) * 3, 0, 1) * 0.9)
    put('lane', col(0.80, 0.78, 0.70) * (0.85 + 0.2 * wear[..., None]), bar * np.clip((wear - 0.35) * 3, 0, 1) * 0.85)
    # roots crawling on the ground
    im = Image.new('L', (C, C), 0); d = ImageDraw.Draw(im)
    for k in range(9):
        x, y = C / 2 + rr.normal() * 20, C / 2 + rr.normal() * 20; a = rr.uniform(0, 6.28); w = 16
        for s in range(40):
            a += rr.normal() * 0.25; nx, ny = x + math.cos(a) * 8, y + math.sin(a) * 8
            d.line([(x, y), (nx, ny)], fill=255, width=max(2, int(w))); x, y = nx, ny; w *= 0.95
    rm = np.asarray(im.filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32) / 255
    put('roots', col(0.38, 0.33, 0.26) * (0.8 + 0.3 * wear[..., None]), rm)
    m = blobmask(seed + 60)
    put('stain', col(0.24, 0.21, 0.17), np.clip(m * 1.5, 0, 1) * 0.5)
    # cherry petals/blossom litter? (summer: seeds & dry leaves) -> fallen twigs
    c, a = leaflitter(seed + 70, [(150, 130, 90), (120, 90, 60)])
    put('petals', c, a * np.clip(blobmask(seed + 71) * 3, 0, 1))
    m = blobmask(seed + 80)
    put('mud', col(0.25, 0.21, 0.15) * (0.8 + 0.4 * n[..., None]), np.clip(m * 2, 0, 1) * 0.9)
    # weathering streaks for tall facades: dark rain/rust runs from the top edge, fading downwards
    sx = pnoise(C, C, 1, 24, seed + 90, Image.BILINEAR)
    fine = pnoise(C, C, 4, 96, seed + 91, Image.BILINEAR)
    vdown = yy / C                                   # 0 at top .. 1 at bottom
    runs = np.clip((sx * 0.7 + fine * 0.3 - 0.42) * 3.0, 0, 1) * np.clip(1.15 - vdown ** 0.8, 0, 1)
    edge_fade = np.clip(np.minimum(xx, C - xx) / (C * 0.12), 0, 1)
    sc_ = lerp(col(0.10, 0.09, 0.08), col(0.24, 0.16, 0.10), pnoise(C, C, 6, 12, seed + 92))
    put('streak', sc_, runs * edge_fade * 0.85)
    # floating scum / leaf mats on still water
    c2, a2 = leaflitter(seed + 95, [(70, 80, 40), (95, 85, 45), (60, 70, 35)])
    algae = col(0.12, 0.17, 0.08) * (0.8 + 0.4 * pfbm(C, C, 16, seed + 96)[..., None])
    m = blobmask(seed + 97, 1.4)
    put('scum', np.where(a2[..., None] > 0.5, c2, algae), np.clip(np.maximum(a2 * 0.9, m * 0.85) * np.clip(m * 3, 0, 1), 0, 1))
    # dark wet band (bank / waterline): soft, irregular, darker than the water
    m = blobmask(seed + 98, 1.0)
    put('edge', col(0.075, 0.072, 0.050) + pfbm(C, C, 8, seed + 99)[..., None] * 0.04, np.clip(m * 1.8, 0, 1) * 0.95)
    rgbb = rgb.copy()
    save('decals', rgbb, al)


# ------------------------------------------------------------ vehicles atlas 1024 (regions)
# layout (u,v in 0..1, v up): body paints in 4 horizontal strips at v 0.5..1 (each 0.125),
# glass/interior 0.25..0.5 left, tyres 0.25..0.5 right, chassis/rust 0..0.25
def tex_car(S=1024, seed=500):
    c = np.zeros((S, S, 3), np.float32)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    n1 = pfbm(S, S, 8, seed); n2 = pfbm(S, S, 48, seed + 1, oct=3)
    rust = lerp(col(0.30, 0.15, 0.07), col(0.48, 0.26, 0.11), n2) * (0.8 + 0.3 * n1[..., None])
    paints = [col(0.70, 0.69, 0.66), col(0.40, 0.42, 0.44), col(0.22, 0.27, 0.36), col(0.50, 0.24, 0.18)]
    for k, p in enumerate(paints):
        y0 = int(S * (0.5 - 0.125 * (k + 1)) + S * 0.5)   # strips from top
        sl = slice(S - int(S * (0.5 + 0.125 * (k + 1))), S - int(S * (0.5 + 0.125 * k)))
        r = np.clip((n1[sl] * 0.6 + n2[sl] * 0.4 - 0.42 + 0.06 * k) * 4, 0, 1)
        moss = np.clip((pnoise(S, S, 6, 6, seed + 9 + k)[sl] - 0.62) * 5, 0, 1)
        pc = p * (0.85 + 0.2 * n2[sl][..., None])
        cc = lerp(pc, rust[sl], r)
        cc = lerp(cc, col(0.25, 0.32, 0.13), moss * 0.8)
        c[sl] = cc
    # glass / interior band (v .25-.5 left half): dark interior with window frame hint
    sl = slice(S // 2, S * 3 // 4)
    c[sl, :S // 2] = col(0.05, 0.05, 0.05) * (0.8 + 0.6 * n2[sl, :S // 2][..., None])
    # tyre band right half
    tyre = col(0.07, 0.07, 0.07) * (0.8 + 0.5 * n2[sl, S // 2:][..., None])
    c[sl, S // 2:] = tyre
    # chassis rust bottom quarter
    c[S * 3 // 4:] = rust[S * 3 // 4:] * 0.75
    save('car', c)


# ------------------------------------------------------------ signs atlas 1024 RGBA (Japanese, faded)
SIGNS = [  # text, bg, fg, vertical
    ('けやき坂', (70, 70, 72), (220, 215, 200), False),
    ('六本木ヒルズ', (205, 200, 190), (60, 60, 60), False),
    ('テレビ朝日', (200, 200, 198), (150, 40, 40), False),
    ('66 プラザ', (60, 64, 70), (225, 220, 205), False),
    ('毛利庭園', (230, 225, 210), (60, 55, 45), True),
    ('くすり', (200, 195, 170), (40, 90, 140), True),
    ('喫茶', (130, 60, 40), (235, 220, 190), True),
    ('駐車場 P', (40, 80, 140), (235, 235, 235), False),
    ('森タワー', (55, 58, 62), (220, 218, 210), False),
    ('止まれ', (170, 50, 40), (240, 240, 235), False),
    ('ラーメン', (190, 160, 70), (90, 30, 20), True),
    ('メトロハット', (205, 205, 200), (50, 70, 110), False),
    ('六本木駅', (225, 225, 220), (30, 90, 60), False),
    ('出口 1C', (240, 200, 60), (40, 40, 40), False),
    ('グランド ハイアット', (110, 95, 70), (230, 220, 190), False),
    ('レジデンス', (180, 175, 165), (70, 70, 70), False),
]


def tex_signs(S=1024, seed=600):
    img = Image.new('RGBA', (S, S), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    fpath = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
    rr = R(seed)
    cw, ch = S // 2, S // 8   # 2 columns x 8 rows, each 512x128
    for i, (t, bg, fg, vert) in enumerate(SIGNS):
        cx, cy = (i % 2) * cw, (i // 2) * ch
        d.rectangle([cx, cy, cx + cw - 1, cy + ch - 1], fill=bg + (255,))
        d.rectangle([cx + 6, cy + 6, cx + cw - 7, cy + ch - 7], outline=tuple(int(v * 0.8) for v in bg) + (255,), width=3)
        size = 84 if len(t) < 6 else int(84 * 6 / len(t)) + 10
        font = ImageFont.truetype(fpath, size, index=0)
        bb = d.textbbox((0, 0), t, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        d.text((cx + (cw - tw) / 2 - bb[0], cy + (ch - th) / 2 - bb[1]), t, font=font, fill=fg + (255,))
    a = np.asarray(img).astype(np.float32)[..., :3] / 255
    # fade, stain, rust, moss
    n1 = pfbm(S, S, 8, seed); n2 = pfbm(S, S, 64, seed + 1, oct=3)
    a = lerp(a, col(0.62, 0.60, 0.55), 0.35 + 0.2 * n1)            # sun bleaching
    sx = pnoise(S, S, 1, 96, seed + 2, Image.BILINEAR)
    a = lerp(a, a * col(0.55, 0.45, 0.35), np.clip((sx - 0.55) * 3, 0, 1) * 0.7)
    a = lerp(a, col(0.40, 0.25, 0.12), np.clip((n2 - 0.68) * 5, 0, 1))
    a = lerp(a, col(0.25, 0.30, 0.12), np.clip((pnoise(S, S, 6, 12, seed + 3) - 0.8) * 5, 0, 1) * 0.7)
    save('signs', a)


def tex_fac2():
    """mid-LOD facade atlas: 1024^2, each row holds two floors of the same variant"""
    im = Image.open(OUTD + 'fac.png').convert('RGB')
    out = Image.new('RGB', (1024, 1024))
    for r in range(8):
        row = im.crop((0, r * 256, 2048, (r + 1) * 256)).resize((1024, 64), Image.LANCZOS)
        # mid LOD is seen from 350-900 m: soften the mullion grid so it doesn't shimmer into moire
        row = row.filter(ImageFilter.GaussianBlur(1.6))
        out.paste(row, (0, r * 128)); out.paste(row, (0, r * 128 + 64))
    out.save(OUTD + 'fac2.png'); print('wrote fac2')


ALL = {'conc': tex_concrete, 'top': tex_top, 'pave': tex_pave, 'metal': tex_metal, 'bark': tex_bark,
       'bronze': tex_bronze, 'fac': tex_facade, 'leaves': tex_leaves, 'decals': tex_decals, 'car': tex_car,
       'signs': tex_signs, 'fac2': tex_fac2}

if __name__ == '__main__':
    names = sys.argv[1:] or list(ALL)
    for n in names:
        ALL[n]()
