"""Procedural textures (numpy, inside Blender). Arrays are row 0 = bottom (Blender / OpenGL UV convention).

Each set writes <set>_col.png (sRGB, alpha where needed), <set>_nrm.png (OpenGL tangent normal), <set>_orm.png
(R micro occlusion, G roughness, B metalness).  Cells are seamless tiles wrap-padded into the atlas (see uvmap.py).
"""
import bpy, math, os
import numpy as np
import common as C
import uvmap as U

# ------------------------------------------------------------------------------------------------ noise
def _interp(grid, h, w):
    fy, fx = grid.shape
    y = np.arange(h) * fy / h; x = np.arange(w) * fx / w
    y0 = np.floor(y).astype(int); x0 = np.floor(x).astype(int)
    ty = y - y0; tx = x - x0
    ty = ty * ty * (3 - 2 * ty); tx = tx * tx * (3 - 2 * tx)
    y1 = (y0 + 1) % fy; x1 = (x0 + 1) % fx; y0 %= fy; x0 %= fx
    a = grid[y0][:, x0]; b = grid[y0][:, x1]; c = grid[y1][:, x0]; d = grid[y1][:, x1]
    tx = tx[None, :]; ty = ty[:, None]
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty


def vnoise(h, w, fy, fx, seed):
    r = np.random.default_rng(seed)
    return _interp(r.random((max(1, int(fy)), max(1, int(fx)))), h, w)


def fbm(h, w, f, octaves, seed, gain=0.5, aspect=1.0):
    out = np.zeros((h, w)); amp = 1.0; tot = 0
    for o in range(octaves):
        fy = f * 2 ** o; fx = f * 2 ** o * aspect
        out += amp * vnoise(h, w, fy, fx, seed + o * 101); tot += amp; amp *= gain
    return out / tot


def white(h, w, seed):
    return np.random.default_rng(seed).random((h, w))


def blur(a, r):
    """cheap box blur (wrap) radius r px, 2 passes"""
    if r < 1: return a
    out = a
    for _ in range(2):
        k = 2 * r + 1
        c = np.cumsum(np.concatenate([out[-r - 1:], out, out[:r]], axis=0), axis=0)
        out = (c[k:] - c[:-k]) / k
        c = np.cumsum(np.concatenate([out[:, -r - 1:], out, out[:, :r]], axis=1), axis=1)
        out = (c[:, k:] - c[:, :-k]) / k
    return out


def srgb(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)


def lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def normal_from_height(H, strength, px_per_m):
    """H in metres; returns RGB normal map (OpenGL, +Y up the texture)"""
    dx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * 0.5 * px_per_m
    dy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * 0.5 * px_per_m
    n = np.dstack([-dx * strength, -dy * strength, np.ones_like(H)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


class Cell:
    """one tile: albedo (linear rgb), alpha, height (m), rough, metal, ao"""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.A = np.zeros((h, w, 3)); self.alpha = np.ones((h, w)); self.H = np.zeros((h, w))
        self.R = np.full((h, w), 0.8); self.M = np.zeros((h, w)); self.O = np.ones((h, w))


def save_png(name, arr, alpha=None):
    """arr (h,w,3) or (h,w,4) floats 0..1, already in the file's encoding"""
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        a = np.ones((h, w, 1)) if alpha is None else alpha[..., None]
        arr = np.concatenate([arr, a], axis=2)
    im = bpy.data.images.get('_tmp_' + name)
    if im: bpy.data.images.remove(im)
    im = bpy.data.images.new('_tmp_' + name, w, h, alpha=True)
    im.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    im.filepath_raw = C.TEX + name + '.png'; im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)


class Atlas:
    def __init__(self, size=2048):
        self.s = size
        self.col = np.zeros((size, size, 3)); self.a = np.ones((size, size)); self.nrm = np.zeros((size, size, 3)) + (0.5, 0.5, 1)
        self.orm = np.zeros((size, size, 3)) + (1, 0.8, 0)

    def put(self, cell, x0, y0, px, g, nstrength=1.0, ppm=64.0):
        """place a (px-2g) tile with wrap padding g at (x0, y0) px"""
        def pad(a):
            return np.pad(a, ((g, g), (g, g)) + ((0, 0),) * (a.ndim - 2), mode='wrap')
        self.col[y0:y0 + px, x0:x0 + px] = pad(srgb(cell.A))
        self.a[y0:y0 + px, x0:x0 + px] = pad(cell.alpha)
        self.nrm[y0:y0 + px, x0:x0 + px] = pad(normal_from_height(cell.H, nstrength, ppm))
        self.orm[y0:y0 + px, x0:x0 + px] = pad(np.dstack([cell.O, cell.R, cell.M]))

    def save(self, name, alpha=False):
        save_png(name + '_col', self.col, self.a if alpha else None)
        save_png(name + '_nrm', self.nrm)
        save_png(name + '_orm', self.orm)


# ------------------------------------------------------------------------------------------------ palette (linear)
GRANITE = lin((0.50, 0.485, 0.45))
GRANITE_D = lin((0.22, 0.22, 0.215))
INTERIOR = lin((0.075, 0.072, 0.068))
CONCRETE = lin((0.44, 0.42, 0.38))
MOSS = lin((0.30, 0.36, 0.16))
MOSS_D = lin((0.17, 0.22, 0.09))
RUST = lin((0.42, 0.24, 0.13))
DIRT = lin((0.30, 0.27, 0.22))


def mix(a, b, t):
    t = np.asarray(t)
    if t.ndim == 2: t = t[..., None]
    return a * (1 - t) + b * t


def rect(Y, X, x0, x1, y0, y1):
    return (X >= x0) & (X < x1) & (Y >= y0) & (Y < y1)


# ------------------------------------------------------------------------------------------------ facade
def facade_cell(kind, ruined, seed):
    """kind 0 = pier zone, 1 = window band zone. 12.8 m x 16 m (4 floors) in 1008 px."""
    W = H = 1024 - 2 * U.G
    SU, SV = 12.8, 16.0
    c = Cell(W, H)
    y = (np.arange(H) + 0.5) * SV / H; x = (np.arange(W) + 0.5) * SU / W
    Y, X = np.meshgrid(y, x, indexing='ij')
    fl = np.floor(Y / 4.0); fy = Y - fl * 4.0          # position within the floor (m)
    rnd = np.random.default_rng(seed)
    dark = np.zeros((H, W), bool)                     # dark granite
    win = np.zeros((H, W), bool)                      # opening
    frame = np.zeros((H, W), bool)                    # sash / mullion
    relief = np.zeros((H, W))
    if kind == 1:
        mx = X
        stripes = ((mx < 0.22) | ((mx > 0.42) & (mx < 0.64)) | (mx > SU - 0.22) | ((mx < SU - 0.42) & (mx > SU - 0.64)))
        inner = (mx > 1.0) & (mx < SU - 1.0)
        dark |= stripes
        dark |= inner & (fy > 0.35) & (fy < 1.3)
        win |= inner & (fy > 1.55) & (fy < 3.5)
        sash = ((mx - 1.0) % 0.8)
        frame |= win & ((sash < 0.05) | (sash > 0.75) | (np.abs(fy - 3.0) < 0.03))
        relief += np.where(stripes, -0.03, 0)
        relief += np.where(inner & (fy > 1.35) & (fy < 1.55), 0.04, 0)    # sill ledge
    else:
        m = X % 3.2; col = np.floor(X / 3.2)
        # paired narrow windows
        w1 = (m > 0.45) & (m < 0.88); w2 = (m > 1.04) & (m < 1.47)
        win |= (w1 | w2) & (fy > 1.45) & (fy < 3.35)
        frame |= win & (np.abs(fy - 2.85) < 0.03)
        # dark granite blocks under the window pairs and beside them
        dark |= (m > 0.45) & (m < 1.47) & (fy > 0.45) & (fy < 1.25)
        dark |= (m > 2.0) & (m < 2.62) & (((fy > 1.45) & (fy < 3.35)) | ((fy > 0.45) & (fy < 1.25) & (fl % 2 == 1)))
        # the thin double 'circuit' lines every 6.4 m
        cl = X % 6.4
        dark |= ((cl > 2.86) & (cl < 2.94)) | ((cl > 3.02) & (cl < 3.10))
        relief += np.where((m > 1.9) & (m < 2.72), 0.035, 0)          # shallow pilaster
    # stone joints on light granite: 0.8 m x 1.0 m grid
    jx = (X % 0.8); jy = (fy % 1.0)
    joint = ((jx < 0.012) | (jy < 0.012)) & ~win
    relief -= joint * 0.006
    relief -= win * 0.22                     # window reveal depth
    relief += frame * 0.17
    # granite grain + tone
    grain = white(H, W, seed + 1)
    tone = fbm(H, W, 3, 4, seed + 2)
    base = mix(GRANITE, GRANITE * 0.92 * np.array([1.0, 0.98, 0.95]), tone)
    base = base * (0.94 + 0.12 * grain[..., None])
    dgr = GRANITE_D * (0.85 + 0.3 * grain[..., None])
    A = np.where(dark[..., None], dgr, base)
    A = A * np.where(joint[..., None], 0.82, 1.0)
    # openings: interior seen through missing glass
    inter = INTERIOR * (0.75 + 0.5 * fbm(H, W, 6, 2, seed + 3))[..., None]
    ceil_ = (fy > 3.15) & win
    inter = np.where(ceil_[..., None], inter * 1.8, inter)
    # glass left (dark blue-grey) per pane
    pane_id = (np.floor(X / 0.8) * 7 + fl * 13).astype(int)
    pr = np.random.default_rng(seed + 4).random(pane_id.max() + 2)[pane_id]
    glass_p = 0.04 if ruined else 0.22
    glass = win & ~frame & (pr < glass_p)
    A = np.where(win[..., None], inter, A)
    A = np.where(glass[..., None], lin((0.10, 0.12, 0.14)) + 0.05 * fbm(H, W, 20, 2, seed + 5)[..., None], A)
    A = np.where(frame[..., None], lin((0.33, 0.32, 0.30)) * (0.8 + 0.3 * grain[..., None]), A)
    R = np.where(win, 0.95, np.where(dark, 0.55, 0.72)); R = np.where(glass, 0.12, R); R = np.where(frame, 0.6, R)
    Mt = np.where(frame, 0.25, 0.0)
    O = np.where(win, 0.45, 1.0) * np.where(joint, 0.85, 1.0)
    # --- sixty years: run-off streaks from every sill and ledge, black crust, algae, moss, missing panels
    src = (win & ~np.roll(win, -1, axis=0)).astype(float)                 # bottom edge of openings
    src = np.maximum(src, ((np.abs(fy - 0.35) < 0.02)).astype(float) * 0.5)
    jitter = np.clip(fbm(H, W, 1, 3, seed + 12, aspect=40) * 1.6 - 0.3, 0, 1)   # which columns of the sill drip
    st = src * jitter
    run = st.copy()
    for i in range(170):
        st = np.roll(st, -1, axis=0) * 0.986
        run = np.maximum(run, st)
    run = run * ~win
    streak_n = fbm(H, W, 2, 3, seed + 6, aspect=14)
    crust = np.clip((streak_n - 0.42) * 2.2, 0, 1) * 0.5 + np.clip(run, 0, 1) * 0.8
    k = 0.75 if ruined else 0.55
    A = mix(A, A * 0.42 * np.array([0.95, 0.93, 0.88]), np.clip(crust, 0, 1) * k)
    tone2 = fbm(H, W, 1, 3, seed + 13)
    A = A * (0.82 + 0.3 * tone2[..., None])
    algae = np.clip((fbm(H, W, 4, 4, seed + 7) - (0.48 if ruined else 0.56)) * 4, 0, 1)
    ledge = ((fy > 1.25) & (fy < 1.6)) | (fy < 0.12)
    algae = algae * (0.4 + 0.6 * ledge) * ~win
    A = mix(A, MOSS_D * (0.8 + 0.5 * grain[..., None]), algae * (0.8 if ruined else 0.45))
    R = np.where(algae > 0.3, 0.9, R)
    if ruined:
        # missing stone panels -> concrete backing with rust stains
        pid = (np.floor(X / 0.8) * 31 + np.floor(Y / 1.0) * 17).astype(int)
        pm = np.random.default_rng(seed + 8).random(pid.max() + 2)[pid]
        clump = fbm(H, W, 3, 2, seed + 9)
        miss = (pm < 0.10 + 0.5 * np.clip(clump - 0.55, 0, 1)) & ~win & ~frame
        back = CONCRETE * 0.55 * (0.8 + 0.4 * fbm(H, W, 30, 2, seed + 10)[..., None])
        A = np.where(miss[..., None], back, A)
        relief -= miss * 0.06
        R = np.where(miss, 0.92, R)
        O = O * np.where(miss, 0.8, 1.0)
        # sashes gone in clusters -> fully open bays
        gone = (fbm(H, W, 3, 2, seed + 11) > 0.58) & win
        A = np.where((gone & frame)[..., None], inter, A)
        # moss on sills
        sill = win & (fy < 1.75)
        A = np.where(sill[..., None], mix(A, MOSS, 0.6), A)
    c.A = np.clip(A, 0, 1); c.H = relief + 0.004 * grain; c.R = R; c.M = Mt; c.O = O
    return c


def build_facade():
    at = Atlas()
    for cid, (col, row, px, su, sv) in U.FACADE_CELLS.items():
        kind = cid % 2; ruined = cid >= 2
        cell = facade_cell(kind, ruined, 100 + cid * 17)
        at.put(cell, col * px, row * px, px, U.G, nstrength=1.0, ppm=(px - 2 * U.G) / su)
    at.save('facade')


# ------------------------------------------------------------------------------------------------ material atlas
def mat_cell(name, su, sv, seed):
    W = H = 512 - 2 * U.G
    c = Cell(W, H)
    y = (np.arange(H) + 0.5) * sv / H; x = (np.arange(W) + 0.5) * su / W
    Y, X = np.meshgrid(y, x, indexing='ij')
    g = white(H, W, seed); t = fbm(H, W, 3, 5, seed + 1); t2 = fbm(H, W, 8, 4, seed + 2)
    def blocks(bw, bh, stagger=True):
        row = np.floor(Y / bh); xx = X + (row % 2) * bw * 0.5 * stagger
        jx = xx % bw; jy = Y % bh
        jt = (jx < 0.012 * su / 4 + 0.008) | (jy < 0.012 * sv / 4 + 0.008)
        bid = (np.floor(xx / bw) * 7 + row * 13).astype(int)
        bv = np.random.default_rng(seed + 3).random(bid.max() + 2)[bid]
        return jt, bv
    moss_n = np.clip((fbm(H, W, 4, 4, seed + 4) - 0.55) * 3, 0, 1)
    if name in ('granite', 'granite_dark', 'panel'):
        base = GRANITE if name != 'granite_dark' else GRANITE_D
        jt, bv = blocks(1.2, 0.6) if name != 'panel' else blocks(0.8, 1.0, False)
        A = base * (0.9 + 0.12 * g[..., None]) * (0.92 + 0.12 * bv[..., None])
        A = mix(A, A * 0.6, np.clip((fbm(H, W, 2, 3, seed + 5, aspect=10) - 0.5) * 2, 0, 1) * 0.6)
        A = A * np.where(jt[..., None], 0.7, 1)
        A = mix(A, MOSS_D, moss_n * 0.7)
        c.H = -1.0 * jt * 0.008 + 0.003 * g
        c.R = np.full((H, W), 0.7); c.O = np.where(jt, 0.8, 1.0)
        if name == 'panel':
            # one Tange module: a pair of window holes and a dark block; reads as a fallen facade panel
            m = X; fy = Y
            win = (((m > 0.45) & (m < 0.88)) | ((m > 1.04) & (m < 1.47))) & (fy > 1.45) & (fy < 3.35)
            dk = (m > 2.0) & (m < 2.62) & (fy > 1.45) & (fy < 3.35) | ((m > 0.45) & (m < 1.47) & (fy > 0.45) & (fy < 1.25))
            A = np.where(dk[..., None], GRANITE_D * (0.85 + 0.3 * g[..., None]), A)
            A = np.where(win[..., None], INTERIOR * 0.7, A)
            c.H = c.H - win * 0.15; c.O = np.where(win, 0.4, c.O)
    elif name == 'assembly':
        # Assembly / colonnade upper floors: granite with tall vertical slit windows, 2 floors of 4 m
        fy = Y % 4.0; m = X % 1.6
        slit = (m > 0.55) & (m < 1.05) & (fy > 1.0) & (fy < 3.5)
        jt, bv = blocks(1.6, 1.0, False)
        A = GRANITE * (0.9 + 0.12 * g[..., None]) * (0.94 + 0.1 * bv[..., None])
        streak = np.clip((fbm(H, W, 2, 3, seed + 5, aspect=10) - 0.45) * 2, 0, 1)
        A = mix(A, A * 0.55, streak * 0.6)
        A = A * np.where(jt[..., None], 0.75, 1)
        A = np.where(slit[..., None], INTERIOR * (0.8 + 0.4 * t[..., None]), A)
        A = mix(A, MOSS_D, moss_n * (~slit) * 0.6)
        c.H = -1.0 * jt * 0.008 - slit * 0.25 + ((m > 0.45) & (m < 1.15) & (np.abs(fy - 0.95) < 0.08)) * 0.05
        c.R = np.where(slit, 0.95, 0.7); c.O = np.where(slit, 0.45, 1.0)
    elif name in ('concrete', 'broken', 'roof', 'interior'):
        A = CONCRETE * (0.85 + 0.25 * t[..., None]) * (0.95 + 0.08 * g[..., None])
        hh = 0.003 * g
        if name == 'concrete':
            jt, bv = blocks(1.8, 0.9, False)
            A = A * (0.95 + 0.08 * bv[..., None]) * np.where(jt[..., None], 0.85, 1)
            A = mix(A, A * 0.5, np.clip((fbm(H, W, 2, 3, seed + 5, aspect=8) - 0.48) * 2.5, 0, 1) * 0.7)
            A = mix(A, MOSS_D, moss_n * 0.5)
            hh = hh - jt * 0.004
        if name == 'broken':
            rough = fbm(H, W, 6, 5, seed + 6)
            hh = (rough - 0.5) * 0.12 + 0.01 * g
            A = A * (0.7 + 0.5 * rough[..., None])
            # aggregate and dark fracture lines, a few rust bleeds
            agg = white(H, W, seed + 7) > 0.82
            A = A * np.where(agg[..., None], 0.75, 1.0)
            fr = np.abs(fbm(H, W, 5, 4, seed + 8) - 0.5) < 0.005
            A = np.where(fr[..., None], A * 0.55, A); hh = hh - fr * 0.01
            A = mix(A, DIRT * 0.8, np.clip((fbm(H, W, 2, 4, seed + 12) - 0.45) * 2.5, 0, 1) * 0.6)
            A = mix(A, MOSS_D, np.clip((fbm(H, W, 3, 4, seed + 13) - 0.5) * 3, 0, 1) * 0.5)
            A = mix(A, RUST * 0.7, np.clip((fbm(H, W, 4, 3, seed + 11) - 0.66) * 4, 0, 1) * 0.6)
            A = mix(A, MOSS_D, np.clip((fbm(H, W, 3, 4, seed + 9) - 0.6) * 3, 0, 1) * 0.6)
        if name == 'roof':
            A = mix(A, A * 0.55, np.clip((t2 - 0.5) * 3, 0, 1) * 0.5)           # water stains
            soil = np.clip((fbm(H, W, 2, 5, seed + 10) - 0.42) * 3.5, 0, 1)
            A = mix(A, DIRT * (0.8 + 0.4 * g[..., None]), soil * 0.8)
            mo = np.clip((fbm(H, W, 3, 5, seed + 11) - 0.45) * 3, 0, 1)
            A = mix(A, mix(MOSS, MOSS_D, t2) * (0.85 + 0.3 * g[..., None]), mo * 0.9)
            hh = hh + soil * 0.02 + mo * 0.02 * g
        if name == 'interior':
            A = lin((0.17, 0.165, 0.155)) * (0.6 + 0.6 * t[..., None]) * (0.9 + 0.2 * g[..., None])
            A = mix(A, MOSS_D * 0.6, np.clip((t2 - 0.6) * 3, 0, 1) * 0.5)
        c.A = A; c.H = hh; c.R = np.full((H, W), 0.9)
        return c
    elif name == 'rust':
        A = mix(RUST, lin((0.22, 0.12, 0.07)), t) * (0.8 + 0.4 * g[..., None])
        A = mix(A, lin((0.35, 0.33, 0.30)), np.clip((t2 - 0.62) * 3, 0, 1) * 0.6)
        c.A = A; c.H = (t2 - 0.5) * 0.01 + 0.002 * g; c.R = np.full((H, W), 0.82); c.M = 0.15 + 0.1 * t
        return c
    elif name == 'moss':
        A = mix(MOSS, MOSS_D, t) * (0.75 + 0.5 * g[..., None])
        A = mix(A, lin((0.42, 0.44, 0.20)), np.clip((t2 - 0.6) * 3, 0, 1) * 0.5)
        c.A = A; c.H = (t2 - 0.5) * 0.03 + 0.01 * g; c.R = np.full((H, W), 0.95)
        return c
    elif name == 'paving':
        # plaza: 0.6 m granite setts in two tones with a band every 4 m, moss and grass in the joints
        jt, bv = blocks(0.6, 0.6, False)
        tone = np.where(bv > 0.75, 0.8, 1.0)
        band = (Y % 4.0 < 0.3)
        A = GRANITE * 0.9 * tone[..., None] * (0.9 + 0.15 * g[..., None])
        A = np.where(band[..., None], GRANITE_D * 1.3 * (0.9 + 0.15 * g[..., None]), A)
        A = mix(A, A * 0.6, np.clip((t - 0.5) * 2, 0, 1) * 0.5)
        A = np.where(jt[..., None], mix(DIRT, MOSS_D, t2), A)
        A = mix(A, MOSS_D, moss_n * 0.5)
        c.A = A; c.H = -1.0 * jt * 0.01 + 0.002 * g; c.R = np.where(jt, 0.95, 0.65)
        return c
    elif name == 'bark':
        # fig root / trunk bark: smooth grey-tan, faint horizontal lenticels, vertical fibre
        fib = fbm(H, W, 4, 4, seed + 5, aspect=0.15)
        A = mix(lin((0.40, 0.37, 0.31)), lin((0.24, 0.22, 0.18)), fib) * (0.9 + 0.15 * g[..., None])
        A = mix(A, MOSS_D, np.clip((t - 0.55) * 3, 0, 1) * 0.6)
        len_ = (fbm(H, W, 30, 2, seed + 6, aspect=0.3) > 0.7)
        A = A * np.where(len_[..., None], 0.75, 1)
        c.A = A; c.H = (fib - 0.5) * 0.02 - len_ * 0.003; c.R = np.full((H, W), 0.85)
        return c
    elif name == 'asphalt':
        A = lin((0.20, 0.20, 0.19)) * (0.8 + 0.4 * t[..., None]) * (0.85 + 0.3 * g[..., None])
        cr = blur((fbm(H, W, 6, 3, seed + 5) > 0.48).astype(float) - (fbm(H, W, 6, 3, seed + 5) > 0.5).astype(float), 1)
        A = mix(A, MOSS_D, np.clip(cr * 3, 0, 1)); A = mix(A, MOSS_D, moss_n * 0.5)
        c.A = A; c.H = -np.clip(cr, 0, 1) * 0.01 + 0.002 * g; c.R = np.full((H, W), 0.9)
        return c
    elif name == 'soil':
        A = mix(DIRT, lin((0.20, 0.15, 0.10)), t) * (0.8 + 0.4 * g[..., None])
        leaf = fbm(H, W, 20, 2, seed + 5) > 0.62
        A = np.where(leaf[..., None], lin((0.35, 0.25, 0.12)) * (0.7 + 0.6 * g[..., None]), A)
        A = mix(A, MOSS_D, moss_n * 0.6)
        c.A = A; c.H = (t2 - 0.5) * 0.04 + leaf * 0.005; c.R = np.full((H, W), 0.95)
        return c
    elif name == 'grid':
        # curtain-wall frame: bars every 0.8 m / mullion at 1.6 / transom at 2.9 m, rest transparent
        bar = (X % 0.8 < 0.07) | (Y % 4.0 < 0.12) | (np.abs(Y % 4.0 - 2.9) < 0.04)
        A = mix(lin((0.33, 0.32, 0.30)), RUST, np.clip(t * 1.3 - 0.2, 0, 1)) * (0.8 + 0.4 * g[..., None])
        c.A = A; c.alpha = bar.astype(float); c.H = bar * 0.02; c.R = np.full((H, W), 0.65); c.M = np.where(bar, 0.25, 0)
        return c
    elif name == 'glazing':
        fy = Y % 4.0
        fr = (X % 1.0 < 0.06) | (fy < 0.15) | (np.abs(fy - 2.6) < 0.04)
        broken = fbm(H, W, 4, 3, seed + 5) > 0.5
        A = np.where(broken[..., None], INTERIOR, lin((0.08, 0.10, 0.11)))
        A = np.where(fr[..., None], lin((0.30, 0.29, 0.27)), A)
        c.A = A; c.H = fr * 0.05; c.R = np.where(fr, 0.6, np.where(broken, 0.95, 0.1)); c.M = np.where(fr, 0.25, 0)
        c.O = np.where(fr, 1, 0.6)
        return c
    c.A = np.clip(A, 0, 1)
    return c


def build_mat():
    at = Atlas()
    for cid, (col, row, px, su, sv) in U.MAT_CELLS.items():
        name = U.MAT_NAMES[cid]
        cell = mat_cell(name, su, sv, 500 + cid * 31)
        cell.A = np.clip(cell.A, 0, 1)
        at.put(cell, col * px, row * px, px, U.G, nstrength=1.0, ppm=(px - 2 * U.G) / su)
    at.save('mat', alpha=True)


# ------------------------------------------------------------------------------------------------ ground decals
def decal_cell(name, su, sv, seed, cv=None):
    W = H = 512 - 2 * U.G
    c = Cell(W, H)
    y = (np.arange(H) + 0.5) * sv / H; x = (np.arange(W) + 0.5) * su / W
    Y, X = np.meshgrid(y, x, indexing='ij')
    g = white(H, W, seed); t = fbm(H, W, 3, 5, seed + 1); t2 = fbm(H, W, 8, 4, seed + 2)
    def blob(th, f=2, soft=0.05):
        n = fbm(H, W, f, 5, seed + 3)
        return np.clip((n - th) / soft, 0, 1)
    c.R = np.full((H, W), 0.9)
    if name in ('paving', 'tile'):
        sz = 0.3 if name == 'paving' else 0.6
        row = np.floor(Y / sz); xx = X + (row % 2) * sz * 0.5 * (name == 'tile')
        jt = ((xx % sz) < 0.012) | ((Y % sz) < 0.012)
        bid = (np.floor(xx / sz) * 7 + row * 13).astype(int)
        bv = np.random.default_rng(seed + 4).random(bid.max() + 2)[bid]
        A = GRANITE * 0.85 * (0.75 + 0.22 * bv[..., None]) * (0.9 + 0.14 * g[..., None])
        A = mix(A, A * 0.5, np.clip((t - 0.4) * 2, 0, 1) * 0.7)
        A = mix(A, DIRT * 0.9, np.clip((fbm(H, W, 2, 4, seed + 6) - 0.5) * 3, 0, 1) * 0.5)
        miss = (bv < 0.04)
        A = np.where(miss[..., None], DIRT * 0.8, A)
        A = np.where(jt[..., None], mix(DIRT, MOSS_D, np.clip(t2 * 1.4, 0, 1)), A)
        A = mix(A, MOSS_D * (0.8 + 0.4 * g[..., None]), np.clip((fbm(H, W, 3, 4, seed + 5) - 0.55) * 3, 0, 1) * 0.7)
        c.A = A; c.H = -0.01 * jt - 0.02 * miss + 0.002 * g; c.R = np.where(jt, 0.95, 0.75)
    elif name == 'band':
        jt = ((X % 1.0) < 0.02) | ((Y % 0.5) < 0.02)
        A = GRANITE_D * 1.4 * (0.85 + 0.25 * g[..., None]) * (0.9 + 0.2 * t[..., None])
        A = np.where(jt[..., None], DIRT, A); A = mix(A, MOSS_D, np.clip((t2 - 0.6) * 3, 0, 1) * 0.5)
        c.A = A; c.H = -0.01 * jt; c.R = np.full((H, W), 0.6)
    elif name in ('grass', 'moss'):
        if name == 'grass':
            strokes = fbm(H, W, 30, 2, seed + 6, aspect=0.2)
            A = mix(lin((0.30, 0.40, 0.12)), lin((0.18, 0.26, 0.08)), strokes) * (0.75 + 0.5 * g[..., None])
            A = mix(A, lin((0.45, 0.42, 0.22)), np.clip((t - 0.6) * 3, 0, 1) * 0.5)
            c.alpha = blob(0.45, 2, 0.08) * (0.6 + 0.4 * (g > 0.3))
        else:
            A = mix(MOSS, MOSS_D, t2) * (0.8 + 0.4 * g[..., None])
            c.alpha = blob(0.48, 3, 0.04)
        c.A = A; c.H = (t2 - 0.5) * 0.01 + 0.004 * g; c.R = np.full((H, W), 0.95)
    elif name in ('litter', 'leaves'):
        import foliage as F
        cv = cv or F.Canvas()
        reg = (0, 0, W, H)
        R_ = __import__('random').Random(seed)
        n = 900 if name == 'litter' else 2600
        for i in range(n):
            px = R_.random() * W; py = R_.random() * H
            col = [F.YELLOW, F.BROWN, lin((0.35, 0.22, 0.10)), lin((0.42, 0.38, 0.22)), F.GREENS[3]][R_.randrange(5)]
            L = R_.uniform(10, 24)
            cv.leaf(px, py, R_.uniform(0, 6.28), L, L * 0.5, np.array(col) * R_.uniform(0.7, 1.1), R_.uniform(0.6, 1.0), region=reg)
        A = cv.C[:H, :W].copy(); al = cv.A[:H, :W].copy()
        if name == 'leaves':
            al = np.maximum(al, blob(0.5, 2, 0.1) * 0.0)
        c.A = np.where(al[..., None] > 0, A, DIRT); c.alpha = al; c.H = al * 0.003; c.R = np.full((H, W), 0.85)
    elif name == 'wet':
        c.A = DIRT * 0.45 * (0.8 + 0.3 * t[..., None]); c.alpha = blob(0.5, 2, 0.12); c.R = np.full((H, W), 0.15)
    elif name == 'stain':
        c.A = mix(DIRT * 0.5, RUST * 0.6, t2); c.alpha = blob(0.52, 2, 0.15) * 0.9; c.R = np.full((H, W), 0.8)
    elif name == 'mud':
        c.A = mix(DIRT, lin((0.22, 0.17, 0.11)), t) * (0.8 + 0.4 * g[..., None]); c.alpha = blob(0.47, 2, 0.1)
        c.H = (t2 - 0.5) * 0.03
    elif name == 'cracks':
        n1 = fbm(H, W, 4, 4, seed + 7); n2 = fbm(H, W, 3, 4, seed + 8)
        cr = (np.abs(n1 - 0.5) < 0.012) | (np.abs(n2 - 0.5) < 0.009)
        cr = blur(cr.astype(float), 1) > 0.2
        A = np.where(cr[..., None], lin((0.05, 0.05, 0.04)), MOSS_D)
        weeds = blur(cr.astype(float), 4) > 0.15
        A = np.where(weeds[..., None] & ~cr[..., None], mix(MOSS, MOSS_D, t2), A)
        c.A = A; c.alpha = np.maximum(cr, weeds & (g > 0.35)).astype(float); c.H = -0.02 * cr
    elif name == 'zebra':
        stripe = (X % 0.9) < 0.45
        worn = fbm(H, W, 6, 4, seed + 9) > 0.42
        c.A = lin((0.78, 0.77, 0.72)) * (0.85 + 0.2 * g[..., None]); c.alpha = (stripe & worn & (g > 0.08)).astype(float); c.R = np.full((H, W), 0.7)
    elif name == 'line':
        stripe = np.abs(X % 4.0 - 2.0) < 0.075
        worn = fbm(H, W, 6, 4, seed + 9) > 0.4
        c.A = np.broadcast_to(lin((0.78, 0.77, 0.72)), (H, W, 3)).copy(); c.alpha = (stripe & worn).astype(float)
    elif name in ('rubble', 'gravel'):
        R_ = __import__('random').Random(seed)
        A = np.zeros((H, W, 3)); al = np.zeros((H, W)); hh = np.zeros((H, W))
        n = 220 if name == 'rubble' else 1600
        for i in range(n):
            cx_, cy_ = R_.random() * W, R_.random() * H
            r = R_.uniform(6, 22) if name == 'rubble' else R_.uniform(2, 6)
            dx = (np.arange(W)[None, :] - cx_ + W / 2) % W - W / 2; dy = (np.arange(H)[:, None] - cy_ + H / 2) % H - H / 2
            ang = R_.uniform(0, 6.28)
            u = dx * math.cos(ang) + dy * math.sin(ang); v = -dx * math.sin(ang) + dy * math.cos(ang)
            m = (np.abs(u) < r) & (np.abs(v) < r * R_.uniform(0.5, 1.0)) & (np.abs(u) + np.abs(v) < r * 1.3)
            col = CONCRETE * R_.uniform(0.6, 1.1) if R_.random() < 0.75 else GRANITE * R_.uniform(0.7, 1.0)
            A[m] = col; al[m] = 1; hh[m] = np.maximum(hh[m], 0.02 + 0.03 * R_.random())
        A = mix(A, MOSS_D, np.clip((t2 - 0.6) * 3, 0, 1) * 0.5)
        c.A = A; c.alpha = al; c.H = hh
    elif name == 'roots':
        n1 = fbm(H, W, 3, 3, seed + 10, aspect=0.4)
        rt = np.abs(n1 - 0.5) < 0.03
        c.A = lin((0.40, 0.37, 0.31)) * (0.8 + 0.3 * g[..., None]); c.alpha = rt.astype(float); c.H = rt * 0.04
    else:
        c.A = np.full((H, W, 3), 0.3)
    c.A = np.clip(c.A, 0, 1)
    return c


def build_decal():
    at = Atlas()
    at.a[:] = 0
    for cid, (col, row, px, su, sv) in U.DECAL_CELLS.items():
        name = U.DECAL_NAMES[cid]
        cell = decal_cell(name, su, sv, 900 + cid * 13)
        at.put(cell, col * px, row * px, px, U.G, nstrength=1.0, ppm=(px - 2 * U.G) / su)
    at.save('decal', alpha=True)


def build_all():
    build_facade()
    build_mat()
    build_decal()
    import foliage
    foliage.build_textures()
    import props
    props.build_textures()
