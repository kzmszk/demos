"""Tileable materials (concrete, rust metal, bark, asphalt rubble) and the decal + foliage atlases."""
import math
import random
import numpy as np

import sb_surf as S
from sb_texlib import Shot, save_png, resize
from sb_tex_facade import LEAF_COLS
from sb_common import TEX

DECAL_PXM = 512.0   # px per metre for decal cells that are small


def _norm(n):
    v = n[..., :3] * 2 - 1
    ln = np.linalg.norm(v, axis=-1, keepdims=True)
    n = n.copy()
    n[..., :3] = v / np.maximum(ln, 1e-4) * 0.5 + 0.5
    return n


# ------------------------------------------------------------------ tileables
def tile_shot(name, size_m, res, surf, extra=None, seed=0):
    s = Shot(name, 0, size_m, 0, size_m, res, plane='XY', torus=(size_m, size_m), samples=10)
    s.rnd = random.Random(seed)
    s.box(-1, size_m + 1, -1, size_m + 1, -1, 0, surf, 'base')
    if extra:
        extra(s)
    a, n = s.render()
    s.cleanup()
    return a, _norm(n)


def concrete_top_surface(seed=0):
    """horizontal concrete (roofs, slabs): bleached, cracked, moss and lichen, dark stains"""
    def f(nb, co, raw, w):
        W = w
        base = nb.rgb((0.33, 0.32, 0.30))
        n1 = nb.noise(co, scale=0.35, detail=8.0, rough=0.6, w=W)
        n2 = nb.noise(co, scale=3.0, detail=6.0, rough=0.7, w=nb.add(W, 3.0))
        m = nb.add(nb.mul(nb.sub(n1, 0.5), 0.7), nb.add(nb.mul(nb.sub(n2, 0.5), 0.35), 1.0))
        col = nb.mix(1.0, base, nb.comb(m, m, m), 'MULTIPLY')
        # dark water stains
        st = nb.smooth(0.55, 0.75, nb.noise(co, scale=0.6, detail=4.0, w=nb.add(W, 7.0)))
        col = nb.mix(nb.mul(st, 0.55), col, (0.10, 0.095, 0.085))
        # lichen spots (pale) and moss (green) patches
        li = nb.voronoi(co, scale=9.0, w=nb.add(W, 2.0))
        lic = nb.mul(nb.sub(1.0, nb.smooth(0.0, 0.18, li)), nb.smooth(0.5, 0.65, nb.noise(co, scale=0.8, w=nb.add(W, 5.0))))
        col = nb.mix(nb.mul(lic, 0.5), col, (0.42, 0.42, 0.36))
        mo = nb.smooth(0.52, 0.66, nb.noise(co, scale=0.5, detail=7.0, rough=0.65, w=nb.add(W, 11.0)))
        mc = nb.mix(nb.noise(co, scale=8.0, w=W), S.MOSS, S.MOSS2)
        col = nb.mix(nb.mul(mo, 0.85), col, mc)
        # cracks
        crm = S.crackmask(nb, co, nb.add(W, 13.0), scale=0.7, width=0.006,
                          gate=nb.smooth(0.42, 0.6, nb.noise(co, scale=0.8, w=nb.add(W, 17.0))))
        col = nb.mix(crm, col, (0.03, 0.035, 0.02))
        h = nb.sub(nb.add(nb.mul(n2, 0.5), nb.mul(mo, 0.6)), nb.mul(crm, 0.8))
        return dict(col=col, h=h, bump=0.8, bumpd=0.01)
    return S._named(f, 'ctop')


def rust_surface(seed=0):
    def f(nb, co, raw, w):
        n = nb.noise(co, scale=3.0, detail=8.0, rough=0.7, w=w)
        n2 = nb.noise(co, scale=0.8, detail=3.0, w=nb.add(w, 5.0))
        col = nb.mix(n, (0.13, 0.065, 0.035), (0.065, 0.04, 0.025))
        col = nb.mix(nb.smooth(0.5, 0.75, n2), col, (0.19, 0.10, 0.05))
        # remnants of grey paint
        p = nb.smooth(0.62, 0.64, nb.noise(co, scale=2.0, detail=6.0, w=nb.add(w, 9.0)))
        col = nb.mix(p, col, (0.24, 0.24, 0.22))
        return dict(col=col, h=nb.add(n, nb.mul(p, 0.5)), bump=0.7, bumpd=0.004)
    return S._named(f, 'rustt')


def bark_surface(seed=0):
    def f(nb, co, raw, w):
        x, y, z = raw
        # vertical fibres: stretch in y (u = around, v = along the trunk)
        sc = nb.vmath('MULTIPLY', co, (6.0, 6.0, 1.0))
        n = nb.noise(co, scale=2.0, detail=6.0, rough=0.6, w=w)
        fib = nb.math('ABSOLUTE', nb.sub(nb.noise(nb.vmath('MULTIPLY', co, (1.0, 1.0, 1.0)), scale=3.0, detail=4.0, w=nb.add(w, 3.0), dist=1.5), 0.5))
        col = nb.mix(n, (0.11, 0.095, 0.075), (0.20, 0.18, 0.15))
        col = nb.mix(nb.sub(1.0, nb.smooth(0.0, 0.08, fib)), col, (0.04, 0.035, 0.03))
        mo = nb.smooth(0.55, 0.7, nb.noise(co, scale=0.7, detail=5.0, w=nb.add(w, 8.0)))
        col = nb.mix(nb.mul(mo, 0.8), col, S.MOSS)
        lic = nb.smooth(0.62, 0.7, nb.noise(co, scale=4.0, detail=3.0, w=nb.add(w, 11.0)))
        col = nb.mix(nb.mul(lic, 0.6), col, (0.38, 0.40, 0.33))
        return dict(col=col, h=nb.add(n, nb.mul(fib, 2.0)), bump=1.0, bumpd=0.01)
    return S._named(f, 'bark')


def rubble_surface(seed=0):
    """broken concrete heap seen from above: angular chunks of mixed size in dust and soil, moss (tileable)"""
    def f(nb, co, raw, w):
        warp = nb.noise(co, scale=1.2, detail=3.0, w=nb.add(w, 7.0), color=True)
        wco = nb.vmath('ADD', co, nb.vmath('MULTIPLY', nb.vmath('SUBTRACT', warp, (0.5, 0.5, 0.5)), (0.6, 0.6, 0.6)))
        big = nb.voronoi(wco, scale=2.2, w=w, out='Color')
        bigd = nb.voronoi(wco, scale=2.2, w=w, feature='DISTANCE_TO_EDGE')
        sml = nb.voronoi(wco, scale=7.0, w=nb.add(w, 2.0), out='Color')
        smld = nb.voronoi(wco, scale=7.0, w=nb.add(w, 2.0), feature='DISTANCE_TO_EDGE')
        sep = nb.node('ShaderNodeSeparateColor'); nb.link(big, sep.inputs[0])
        sep2 = nb.node('ShaderNodeSeparateColor'); nb.link(sml, sep2.inputs[0])
        stone = nb.ramp(sep.outputs[0], [(0.0, (0.13, 0.125, 0.115)), (0.45, (0.21, 0.20, 0.185)), (0.8, (0.26, 0.25, 0.235)),
                                         (0.92, (0.16, 0.11, 0.08)), (1.0, (0.10, 0.07, 0.05))])
        stone2 = nb.ramp(sep2.outputs[0], [(0.0, (0.11, 0.105, 0.095)), (0.6, (0.19, 0.18, 0.165)), (1.0, (0.24, 0.23, 0.215))])
        dust = nb.mix(nb.noise(co, scale=5.0, w=w), (0.10, 0.085, 0.065), (0.16, 0.14, 0.11))
        # which pieces exist: big chunks where the cell value is high, small gravel elsewhere, soil in between
        bigm = nb.mul(nb.smooth(0.35, 0.45, sep.outputs[1]), nb.smooth(0.0, 0.04, bigd))
        smlm = nb.mul(nb.smooth(0.3, 0.4, sep2.outputs[1]), nb.smooth(0.0, 0.05, smld))
        col = nb.mix(smlm, dust, stone2)
        col = nb.mix(bigm, col, stone)
        # shading grain on the chunks
        g = nb.noise(co, scale=30.0, detail=3.0, w=w)
        m = nb.add(nb.mul(nb.sub(g, 0.5), 0.35), 1.0)
        col = nb.mix(1.0, col, nb.comb(m, m, m), 'MULTIPLY')
        mo = nb.smooth(0.56, 0.7, nb.noise(co, scale=0.55, detail=6.0, w=nb.add(w, 4.0)))
        col = nb.mix(nb.mul(mo, 0.8), col, nb.mix(nb.noise(co, scale=9.0, w=w), S.MOSS, S.MOSS2))
        h = nb.add(nb.mul(bigm, 1.0), nb.mul(smlm, 0.4))
        return dict(col=col, h=h, bump=1.0, bumpd=0.05)
    return S._named(f, 'rubble')


def moss_carpet_surface(seed=0):
    """patchy moss / grass carpet for roofs and broken slabs (tileable, alpha)"""
    def f(nb, co, raw, w):
        n = nb.noise(co, scale=0.9, detail=7.0, rough=0.65, w=w)
        n2 = nb.noise(co, scale=6.0, detail=4.0, w=nb.add(w, 3.0))
        a = nb.smooth(0.47, 0.5, nb.add(n, nb.mul(n2, 0.12)))
        c1 = nb.mix(n2, (0.045, 0.075, 0.015), (0.10, 0.14, 0.03))
        dry = nb.smooth(0.55, 0.75, nb.noise(co, scale=1.8, w=nb.add(w, 5.0)))
        col = nb.mix(nb.mul(dry, 0.7), c1, (0.16, 0.14, 0.06))
        bl = nb.voronoi(co, scale=40.0, w=w, out='Distance')
        col = nb.mix(nb.mul(nb.smooth(0.0, 0.25, bl), 0.35), col, (0.03, 0.045, 0.01))
        return dict(col=col, h=nb.add(n2, bl), a=a, bump=0.7, bumpd=0.01)
    return S._named(f, 'carpet')


def build_tileables():
    a, n = tile_shot('concrete', 4.0, 1024, concrete_top_surface())
    save_png(a, f'{TEX}/concrete.png'); save_png(n, f'{TEX}/concrete_n.png', 'Non-Color', False)
    a, n = tile_shot('rust', 2.0, 512, rust_surface())
    save_png(a, f'{TEX}/metal.png')
    a, n = tile_shot('bark', 2.0, 512, bark_surface())
    save_png(a, f'{TEX}/bark.png'); save_png(n, f'{TEX}/bark_n.png', 'Non-Color', False)
    s = Shot('mosscarpet', 0, 4.0, 0, 4.0, 1024, plane='XY', torus=(4.0, 4.0), samples=10)
    s.box(-1, 5, -1, 5, -1, 0, moss_carpet_surface())
    a, n = s.render(); s.cleanup()
    save_png(a, f'{TEX}/mosscarpet.png')
    a, n = tile_shot('rubble', 4.0, 1024, rubble_surface())
    save_png(a, f'{TEX}/rubble.png'); save_png(n, f'{TEX}/rubble_n.png', 'Non-Color', False)


# ------------------------------------------------------------------ decals (RGBA, alpha-clipped)
# cell name -> (x, y, w, h) in px of the 2048 atlas (y from top), metres (w_m, h_m)
DECALS = {
    'zebra1': ((0, 0, 256, 2048), (0.5, 4.0)),
    'zebra2': ((256, 0, 256, 2048), (0.5, 4.0)),
    'line_w': ((512, 0, 64, 2048), (0.15, 4.0)),
    'line_y': ((576, 0, 64, 2048), (0.15, 4.0)),
    'moss1': ((640, 0, 384, 384), (3.0, 3.0)),
    'moss2': ((640, 384, 384, 384), (3.0, 3.0)),
    'leaves': ((640, 768, 384, 384), (3.0, 3.0)),
    'puddle': ((640, 1152, 384, 384), (4.0, 4.0)),
    'tomare': ((640, 1536, 384, 256), (3.0, 2.0)),
    'manhole': ((640, 1792, 256, 256), (0.8, 0.8)),
    'arrow': ((896, 1792, 128, 256), (1.0, 2.0)),
    'cracks1': ((1024, 0, 1024, 1024), (8.0, 8.0)),
    'cracks2': ((1024, 1024, 1024, 1024), (8.0, 8.0)),
}


def decal_uv(name, u, v):
    """u, v in [0,1] within the cell -> atlas uv (Blender, v up)"""
    (x, y, w, h), _m = DECALS[name]
    return ((x + u * w) / 2048.0, 1.0 - (y + (1 - v) * h) / 2048.0)


def paint_stripe_surface(white=(0.40, 0.39, 0.36), seed=0):
    def f(nb, co, raw, w):
        W = float(seed)
        x, y, z = raw
        n = nb.noise(co, scale=2.5, detail=8.0, rough=0.65, w=W)
        wear = nb.noise(co, scale=0.8, detail=4.0, w=W + 3.0)
        a = nb.mul(nb.smooth(0.47, 0.50, nb.add(nb.mul(n, 0.7), nb.mul(wear, 0.5))), nb.sub(1.0, nb.mul(S.crackmask(nb, co, W + 5.0, scale=0.9, width=0.006), 1.0)))
        # cracks across the paint with moss
        crk = S.crackmask(nb, co, W + 5.0, scale=0.9, width=0.012, gate=nb.smooth(0.35, 0.5, nb.noise(co, scale=0.6, w=W + 8.0)))
        col = nb.mix(nb.noise(co, scale=6.0, w=W), white, (0.40, 0.39, 0.36))
        dirt = nb.smooth(0.45, 0.75, nb.noise(co, scale=1.5, detail=5.0, w=W + 7.0))
        col = nb.mix(nb.mul(dirt, 0.6), col, (0.22, 0.21, 0.18))
        col = nb.mix(crk, col, nb.mix(nb.noise(co, scale=20.0, w=W), S.MOSS, S.MOSS2))
        mo = nb.smooth(0.6, 0.7, nb.noise(co, scale=1.2, detail=6.0, w=W + 9.0))
        col = nb.mix(nb.mul(mo, 0.9), col, S.MOSS)
        return dict(col=col, h=nb.sub(n, crk), a=a, bump=0.5, bumpd=0.003)
    return S._named(f, 'stripe')


def moss_patch_surface(seed=0, kind='moss'):
    def f(nb, co, raw, w):
        W = float(seed)
        x, y, z = raw
        r = nb.math('SQRT', nb.add(nb.mul(x, x), nb.mul(y, y)))
        n = nb.noise(co, scale=1.0, detail=7.0, rough=0.65, w=W)
        a = nb.smooth(0.5, 0.52, nb.sub(nb.add(n, 0.45), nb.mul(r, 0.55)))
        if kind == 'moss':
            col = nb.mix(nb.noise(co, scale=10.0, detail=4.0, w=W + 1.0), (0.05, 0.08, 0.015), (0.14, 0.17, 0.04))
            col = nb.mix(nb.smooth(0.6, 0.75, nb.noise(co, scale=3.0, w=W + 2.0)), col, (0.17, 0.15, 0.06))
        elif kind == 'leaves':
            v = nb.voronoi(co, scale=25.0, w=W, out='Color')
            sep = nb.node('ShaderNodeSeparateColor'); nb.link(v, sep.inputs[0])
            col = nb.ramp(sep.outputs[0], [(0.0, (0.10, 0.06, 0.025)), (0.5, (0.20, 0.12, 0.04)), (0.8, (0.28, 0.20, 0.07)), (1.0, (0.12, 0.13, 0.04))])
        else:  # puddle: dark wet
            col = nb.mix(nb.noise(co, scale=2.0, w=W), (0.025, 0.028, 0.03), (0.05, 0.055, 0.05))
            a = nb.smooth(0.5, 0.505, nb.sub(nb.add(nb.noise(co, scale=0.6, detail=3.0, w=W), 0.4), nb.mul(r, 0.4)))
        return dict(col=col, h=n, a=a, bump=0.6, bumpd=0.01)
    return S._named(f, kind)


def crack_sheet_surface(seed=0):
    def f(nb, co, raw, w):
        W = w
        big = S.crackmask(nb, co, W, scale=0.35, width=0.010, dist=0.8)
        small = S.crackmask(nb, co, nb.add(W, 3.0), scale=1.4, width=0.008, dist=0.5,
                            gate=nb.smooth(0.45, 0.6, nb.noise(co, scale=0.5, w=nb.add(W, 4.0))))
        line = nb.mx(big, small)
        # moss and grass widen the big cracks in places
        wide = nb.smooth(0.5, 0.72, nb.noise(co, scale=0.6, detail=5.0, w=nb.add(W, 6.0)))
        band = S.crackmask(nb, co, W, scale=0.35, width=nb.add(0.012, nb.mul(wide, 0.05)), dist=0.8)
        a = nb.smooth(0.45, 0.5, nb.mx(line, band))
        col = nb.mix(line, nb.mix(nb.noise(co, scale=14.0, w=W), S.MOSS, S.MOSS2), (0.025, 0.025, 0.02))
        return dict(col=col, h=nb.sub(1.0, line), a=a, bump=0.6, bumpd=0.01)
    return S._named(f, 'cracks')


def build_decals():
    atlas = np.zeros((2048, 2048, 4), np.float32)
    def put(name, a):
        (x, y, w, h), _ = DECALS[name]
        atlas[y:y + h, x:x + w] = resize(a, h, w)
    for k, nm in enumerate(('zebra1', 'zebra2')):
        s = Shot(nm, -0.25, 0.25, 0, 4.0, 256, plane='XY', samples=10)
        s.box(-0.25, 0.25, 0, 4, -0.1, 0, paint_stripe_surface(seed=k * 7 + 1))
        a, _n = s.render(); s.cleanup(); put(nm, a)
    for nm, c in (('line_w', (0.5, 0.49, 0.45)), ('line_y', (0.50, 0.36, 0.08))):
        s = Shot(nm, -0.075, 0.075, 0, 4.0, 64, plane='XY', samples=10)
        s.box(-0.075, 0.075, 0, 4, -0.1, 0, paint_stripe_surface(c, seed=len(nm)))
        a, _n = s.render(); s.cleanup(); put(nm, a)
    for nm, kind, sd in (('moss1', 'moss', 1), ('moss2', 'moss', 2), ('leaves', 'leaves', 3), ('puddle', 'puddle', 4)):
        (x, y, w, h), (mw, mh) = DECALS[nm]
        s = Shot(nm, -mw / 2, mw / 2, -mh / 2, mh / 2, w, plane='XY', samples=10)
        s.box(-mw / 2, mw / 2, -mh / 2, mh / 2, -0.1, 0, moss_patch_surface(sd, kind))
        a, _n = s.render(); s.cleanup(); put(nm, a)
    # 止まれ
    s = Shot('tomare', -1.5, 1.5, -1.0, 1.0, 384, plane='XY', samples=10)
    s.text('止まれ', 0, 0, 1.15, paint_stripe_surface((0.5, 0.49, 0.45), seed=5), d=0.01)
    a, _n = s.render(); s.cleanup(); put('tomare', a)
    s = Shot('arrow', -0.5, 0.5, -1, 1, 128, plane='XY', samples=10)
    s.poly([(-0.12, -0.95), (0.12, -0.95), (0.12, 0.2), (0.35, 0.2), (0.0, 0.95), (-0.35, 0.2), (-0.12, 0.2)], 0.01,
           paint_stripe_surface((0.5, 0.49, 0.45), seed=6))
    a, _n = s.render(); s.cleanup(); put('arrow', a)
    # manhole (Shibuya: concentric rings + radial pattern)
    s = Shot('manhole', -0.4, 0.4, -0.4, 0.4, 256, plane='XY', samples=10)
    iron = S.metal((0.10, 0.095, 0.09), ox=0.6, seed=3, streak=0.0, rust=0.4)
    N = 48
    s.mesh([(0.0, 0.0, 0.0)] + [(0.31 * math.cos(2 * math.pi * i / N), 0.31 * math.sin(2 * math.pi * i / N), 0.0) for i in range(N)],
           [(0, 1 + i, 1 + (i + 1) % N) for i in range(N)], iron)
    for rr in (0.3, 0.22, 0.12):
        for i in range(N):
            a0 = 2 * math.pi * i / N; a1 = 2 * math.pi * (i + 0.5) / N
            s.mesh([(rr * math.cos(a0), rr * math.sin(a0), 0.01), ((rr - 0.012) * math.cos(a0), (rr - 0.012) * math.sin(a0), 0.01),
                    ((rr - 0.012) * math.cos(a1), (rr - 0.012) * math.sin(a1), 0.01), (rr * math.cos(a1), rr * math.sin(a1), 0.01)],
                   [(0, 1, 2, 3)], S.metal((0.2, 0.19, 0.17), seed=1, streak=0.0))
    a, _n = s.render(); s.cleanup(); put('manhole', a)
    for k, nm in enumerate(('cracks1', 'cracks2')):
        s = Shot(nm, 0, 8, 0, 8, 1024, plane='XY', torus=(8.0, 8.0), samples=10)
        s.box(-1, 9, -1, 9, -0.1, 0, crack_sheet_surface(k))
        a, _n = s.render(); s.cleanup(); put(nm, a)
    save_png(atlas, f'{TEX}/decals.png')


# ------------------------------------------------------------------ foliage atlas
# 512 px cells; FOL[name] = (col, row, wcells, hcells, metres_w, metres_h)
FOL = {
    'leafA': (0, 0, 1, 1, 1.6, 1.6), 'leafB': (1, 0, 1, 1, 1.6, 1.6), 'leafC': (2, 0, 1, 1, 1.6, 1.6),
    'leafD': (3, 0, 1, 1, 1.6, 1.6), 'leafE': (0, 1, 1, 1, 1.6, 1.6), 'leafF': (1, 1, 1, 1, 1.6, 1.6),
    'grass1': (2, 1, 1, 1, 1.0, 1.0), 'grass2': (3, 1, 1, 1, 1.0, 1.0),
    'fern': (0, 2, 1, 1, 1.4, 1.4), 'taro': (1, 2, 1, 1, 1.4, 1.4),
    'ivy1': (2, 2, 1, 2, 2.0, 4.0), 'ivy2': (3, 2, 1, 2, 2.0, 4.0),
    'roots': (0, 3, 1, 1, 2.0, 2.0), 'moss': (1, 3, 1, 1, 1.0, 1.0),
}


def fol_uv(name, u, v):
    c, r, wc, hc, _w, _h = FOL[name]
    x = (c + u * wc) * 512.0 / 2048.0
    y = 1.0 - (r + (1 - v) * hc) * 512.0 / 2048.0
    return (x, y)


GREENS = [(0.035, 0.058, 0.012), (0.052, 0.085, 0.016), (0.075, 0.115, 0.022), (0.10, 0.14, 0.028),
          (0.13, 0.165, 0.035), (0.08, 0.10, 0.03), (0.15, 0.16, 0.045)]


def _twig_cluster(rnd, R, nleaves, lsize, elong=1.6, cols=GREENS, twig=True):
    """a dense round clump of leaves (seen from above) over a few radiating twigs"""
    leaves = []
    twigs = []
    nt = rnd.randint(7, 11)
    for t in range(nt):
        ang = rnd.uniform(0, 2 * math.pi)
        L = R * rnd.uniform(0.5, 0.9)
        pts = []
        x = 0.0; y = 0.0; a = ang
        for i in range(10):
            a += rnd.gauss(0, 0.1)
            x += math.cos(a) * L / 10; y += math.sin(a) * L / 10
            pts.append((x, y))
        twigs.append(pts)
    # lobes: the clump is a union of a few blobs so its outline is irregular
    lobes = [(rnd.gauss(0, R * 0.18), rnd.gauss(0, R * 0.18), R * rnd.uniform(0.45, 0.7)) for _ in range(5)]
    n = 0
    tries = 0
    while n < nleaves and tries < nleaves * 6:
        tries += 1
        lx, ly, lr = rnd.choice(lobes)
        rr = lr * math.sqrt(rnd.random())
        a = rnd.uniform(0, 2 * math.pi)
        px = lx + rr * math.cos(a); py = ly + rr * math.sin(a)
        if px * px + py * py > R * R * 0.92:
            continue
        edge = rr / lr
        la = math.atan2(py, px) + rnd.gauss(0, 0.6)
        sz = lsize * rnd.uniform(0.75, 1.2) * (1.0 - 0.25 * edge)
        # leaves near the top of the clump are lighter (sun side), lower ones darker: pick from the palette by depth
        depth = rnd.random()
        ci = min(len(cols) - 1, int((1 - depth * (1 - 0.5 * edge)) * len(cols)))
        leaves.append((px, py, depth * 0.3, sz, la - math.pi / 2, rnd.uniform(-0.9, 0.9), cols[ci]))
        n += 1
    return leaves, twigs


def _leaf_shape_mesh(s, leaves, surf, shape='ellipse', elong=2.0):
    """custom leaf outline: 'ellipse' (pointed oval), 'blade' (grass), 'heart' (taro)"""
    import bpy
    V = []; F = []; C = []
    if shape == 'ellipse':
        prof = [(0, -0.5), (0.16, -0.32), (0.22, -0.05), (0.18, 0.2), (0.08, 0.4), (0, 0.5), (-0.08, 0.4), (-0.18, 0.2), (-0.22, -0.05), (-0.16, -0.32)]
    elif shape == 'blade':
        prof = [(0, -0.5), (0.03, -0.2), (0.025, 0.2), (0.0, 0.5), (-0.025, 0.2), (-0.03, -0.2)]
    else:
        prof = [(0, -0.45), (0.35, -0.2), (0.45, 0.15), (0.3, 0.45), (0.06, 0.4), (0, 0.25), (-0.06, 0.4), (-0.3, 0.45), (-0.45, 0.15), (-0.35, -0.2)]
    for (cx, cy, cz, sz, ang, tilt, col) in leaves:
        ca, sa = math.cos(ang), math.sin(ang)
        ct = math.cos(tilt); st = math.sin(tilt)
        i0 = len(V)
        for (u, v) in prof:
            u *= sz * (1.0 if shape != 'ellipse' else 1.0)
            v *= sz * elong if shape == 'ellipse' else sz
            x = u * ct
            zz = cz + u * st * 0.5
            V.append((cx + x * ca - v * sa, cy + x * sa + v * ca, zz))
        F.append(tuple(range(i0, i0 + len(prof))))
        C.append(col)
    me = bpy.data.meshes.new('lv')
    me.from_pydata(V, [], F)
    me.validate()
    at = me.color_attributes.new('lc', 'FLOAT_COLOR', 'FACE')
    at.data.foreach_set('color', np.array([(*c, 1.0) for c in C], np.float32).ravel())
    ob = bpy.data.objects.new('lv', me)
    return s._link(ob, surf)


def _twigs_mesh(s, twigs, width, surf, z=-0.05):
    V = []; F = []
    for pts in twigs:
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            dx, dy = x1 - x0, y1 - y0
            L = math.hypot(dx, dy) + 1e-9
            nx, ny = -dy / L * width * (1 - i / len(pts) * 0.6), dx / L * width * (1 - i / len(pts) * 0.6)
            i0 = len(V)
            V += [(x0 - nx, y0 - ny, z), (x0 + nx, y0 + ny, z), (x1 + nx, y1 + ny, z), (x1 - nx, y1 - ny, z)]
            F.append((i0, i0 + 1, i0 + 2, i0 + 3))
    if V:
        s.mesh(V, F, surf, 'twig')


def build_foliage():
    atlas = np.zeros((2048, 2048, 4), np.float32)
    natlas = np.zeros((2048, 2048, 4), np.float32); natlas[..., :3] = (0.5, 0.5, 1.0); natlas[..., 3] = 1
    bark = S.flat_color((0.09, 0.075, 0.055), streak=0.0, mottle=0.3)
    leafs = S.leafattr(var=0.35)

    def shot(name):
        c, r, wc, hc, mw, mh = FOL[name]
        return Shot(name, -mw / 2, mw / 2, -mh / 2, mh / 2, 512 * wc, plane='XY', samples=12), (c, r, wc, hc)

    def put(cell, a, n):
        c, r, wc, hc = cell
        y0 = r * 512; x0 = c * 512
        atlas[y0:y0 + hc * 512, x0:x0 + wc * 512] = resize(a, hc * 512, wc * 512)
        natlas[y0:y0 + hc * 512, x0:x0 + wc * 512] = _norm(resize(n, hc * 512, wc * 512))

    specs = {'leafA': (0.085, 1500, 1.8, GREENS), 'leafB': (0.11, 1100, 1.5, GREENS[1:]),
             'leafC': (0.07, 1900, 2.0, GREENS[:6]), 'leafD': (0.15, 700, 1.3, GREENS[2:]),
             'leafE': (0.09, 1400, 1.7, [(0.09, 0.11, 0.03), (0.12, 0.12, 0.04), (0.07, 0.09, 0.02), (0.15, 0.13, 0.05)]),
             'leafF': (0.10, 1300, 2.2, [(0.03, 0.05, 0.012), (0.045, 0.06, 0.015), (0.06, 0.08, 0.02)])}
    for k, (nm, (lsz, nl, el, cols)) in enumerate(specs.items()):
        s, cell = shot(nm)
        rnd = random.Random(100 + k)
        leaves, twigs = _twig_cluster(rnd, 0.72, nl, lsz, cols=cols)
        _twigs_mesh(s, twigs, 0.008, bark)
        _leaf_shape_mesh(s, leaves, leafs, 'ellipse', elong=el)
        a, n = s.render(); s.cleanup(); put(cell, a, n)
    # grass tufts (side view: blades rising from the bottom centre)
    for k, nm in enumerate(('grass1', 'grass2')):
        s, cell = shot(nm)
        rnd = random.Random(200 + k)
        lv = []
        for i in range(140):
            bx = rnd.gauss(0, 0.12)
            L = rnd.uniform(0.3, 0.9)
            lean = rnd.gauss(0, 0.35)
            cy = -0.5 + L * 0.5
            lv.append((bx + lean * L * 0.4, cy, rnd.uniform(0, 0.1), L, -lean * 0.6, 0.0,
                       rnd.choice([(0.06, 0.09, 0.02), (0.09, 0.12, 0.03), (0.13, 0.14, 0.05), (0.18, 0.16, 0.07)] if k == 0 else GREENS)))
        _leaf_shape_mesh(s, lv, leafs, 'blade')
        a, n = s.render(); s.cleanup(); put(cell, a, n)
    # fern: fronds radiating
    s, cell = shot('fern')
    rnd = random.Random(300)
    lv = []
    for f in range(9):
        ang = rnd.uniform(0, 2 * math.pi)
        L = rnd.uniform(0.45, 0.65)
        for i in range(22):
            t = i / 22
            px = math.cos(ang) * L * t; py = math.sin(ang) * L * t
            for side in (-1, 1):
                la = ang + side * 1.3
                sz = 0.06 * (1 - t * 0.7)
                lv.append((px + math.cos(la) * sz * 0.8, py + math.sin(la) * sz * 0.8, t * 0.1, sz, la - math.pi / 2, 0.3 * side,
                           rnd.choice(GREENS[1:5])))
    _leaf_shape_mesh(s, lv, leafs, 'ellipse', elong=2.5)
    a, n = s.render(); s.cleanup(); put(cell, a, n)
    # taro / big heart leaves
    s, cell = shot('taro')
    rnd = random.Random(400)
    lv = [(rnd.gauss(0, 0.2), rnd.gauss(0, 0.2), rnd.uniform(0, 0.2), rnd.uniform(0.35, 0.55), rnd.uniform(0, 6.28), rnd.uniform(-0.5, 0.5),
           rnd.choice(GREENS[2:])) for i in range(7)]
    _leaf_shape_mesh(s, lv, leafs, 'heart')
    a, n = s.render(); s.cleanup(); put(cell, a, n)
    # ivy curtains (hanging, top of the cell = attachment line)
    from sb_tex_facade import ivy_leaves
    for k, nm in enumerate(('ivy1', 'ivy2')):
        c, r, wc, hc, mw, mh = FOL[nm]
        s = Shot(nm, -mw / 2, mw / 2, -mh / 2, mh / 2, 512 * wc, plane='XY', samples=12)
        rnd = random.Random(500 + k)
        lv = ivy_leaves(rnd, 0.0, mh / 2 - 0.05, mh * 0.95, spread=0.8, strands=22, size=(0.06, 0.13), dens=28, d=0.0, bottom=-mh / 2)
        lv2 = [(x, z, 0.1 + rnd.uniform(0, 0.1), sz, ang, tilt, cc) for (x, z, d, sz, ang, tilt, cc) in lv]
        s.leafmesh([(x, y, 0, sz, ang, tilt, cc) for (x, y, d, sz, ang, tilt, cc) in lv2], leafs)
        a, n = s.render(); s.cleanup(); put((c, r, wc, hc), a, n)
    # aerial roots (strangler fig): brown strands hanging from the top
    s, cell = shot('roots')
    rnd = random.Random(600)
    tw = []
    for i in range(26):
        x = rnd.gauss(0, 0.45); y = 0.98
        pts = []
        for j in range(30):
            x += rnd.gauss(0, 0.01); y -= rnd.uniform(0.04, 0.075)
            pts.append((x, y))
            if y < -1.0:
                break
        tw.append(pts)
    _twigs_mesh(s, tw, 0.012, S.flat_color((0.16, 0.13, 0.09), streak=0.0, mottle=0.4), z=0.0)
    a, n = s.render(); s.cleanup(); put(cell, a, n)
    # moss cushion
    s, cell = shot('moss')
    s.box(-0.5, 0.5, -0.5, 0.5, -0.1, 0, moss_patch_surface(9, 'moss'))
    a, n = s.render(); s.cleanup(); put(cell, a, n)
    # bleed colour into transparent texels so mips do not halo
    rgb = atlas[..., :3]; A = atlas[..., 3:4]
    m = (A > 0.5).astype(np.float32)
    for it in range(6):
        acc = np.zeros_like(rgb); cnt = np.zeros_like(A)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(rgb * m, dy, 0), dx, 1); cnt += np.roll(np.roll(m, dy, 0), dx, 1)
        fill = (m == 0) & (cnt > 0)
        rgb = np.where(fill, acc / np.maximum(cnt, 1e-6), rgb)
        m = np.where(fill, 1.0, m)
    atlas[..., :3] = rgb
    save_png(atlas, f'{TEX}/foliage.png')
    save_png(natlas, f'{TEX}/foliage_n.png', 'Non-Color', False)


def main():
    build_tileables()
    build_decals()
    build_foliage()
