"""Surface (material) library for the texture factory. Each factory returns a surface function
(nb, co, raw, w) -> dict(col, h[, a, bump, bumpd]). Colours are linear albedo."""
import itertools

_uid = itertools.count()

MOSS = (0.105, 0.135, 0.045)
MOSS2 = (0.16, 0.19, 0.06)
RUSTC = (0.22, 0.10, 0.045)
DIRT = (0.16, 0.14, 0.11)


def _named(f, name):
    f.__name__ = f'{name}{next(_uid)}'
    return f


def _W(w, seed):
    return w if w is not None else float(seed)


def crackmask(nb, co, w, scale=1.0, width=0.012, detail=3.0, dist=0.6, gate=None):
    """meandering crack lines: level set of a distorted noise"""
    n = nb.noise(co, scale=scale, detail=detail, rough=0.55, w=w, dist=dist)
    d = nb.math('ABSOLUTE', nb.sub(n, 0.5))
    m = nb.sub(1.0, nb.smooth(0.0, width, d))
    if gate is not None:
        m = nb.mul(m, gate)
    return m


def weather(nb, col, co, w, streak=0.5, moss=0.3, mottle=0.35, seed=0, moss_scale=0.5, rust=0.0):
    W = _W(w, seed)
    # vertical rain streaks (two scales)
    sc = nb.vmath('MULTIPLY', co, (2.6, 2.6, 0.16))
    n1 = nb.noise(sc, scale=1.0, detail=4.0, rough=0.6, w=W)
    sc2 = nb.vmath('MULTIPLY', co, (9.0, 9.0, 0.5))
    n1b = nb.noise(sc2, scale=1.0, detail=3.0, rough=0.5, w=W + 0.7 if isinstance(W, float) else W)
    st = nb.mul(nb.mx(nb.smooth(0.45, 0.8, n1), nb.mul(nb.smooth(0.55, 0.75, n1b), 0.6)), streak)
    col = nb.mix(st, col, nb.mix(0.75, col, DIRT, 'MULTIPLY'))
    # mottling (large blotches + fine grain)
    n2 = nb.noise(co, scale=0.9, detail=8.0, rough=0.65, w=nb.add(W, 3.1) if not isinstance(W, float) else W + 3.1)
    mot = nb.add(nb.mul(nb.sub(n2, 0.5), mottle * 2.6), 1.0)
    col = nb.mix(1.0, col, nb.comb(mot, mot, mot), 'MULTIPLY')
    n2b = nb.noise(co, scale=12.0, detail=4.0, rough=0.7, w=W + 5.5 if isinstance(W, float) else W)
    mot2 = nb.add(nb.mul(nb.sub(n2b, 0.5), 0.5), 1.0)
    col = nb.mix(1.0, col, nb.comb(mot2, mot2, mot2), 'MULTIPLY')
    if rust > 0:
        sc2 = nb.vmath('MULTIPLY', co, (4.0, 4.0, 0.3))
        n4 = nb.noise(sc2, scale=1.0, detail=4.0, w=W + 11.0 if isinstance(W, float) else W)
        r = nb.mul(nb.smooth(0.6, 0.8, n4), rust)
        col = nb.mix(r, col, RUSTC)
    if moss > 0:
        n3 = nb.noise(co, scale=moss_scale, detail=6.0, rough=0.62, w=W + 7.3 if isinstance(W, float) else W)
        n5 = nb.noise(co, scale=6.0, detail=3.0, w=W + 1.7 if isinstance(W, float) else W)
        mm = nb.mul(nb.smooth(0.55, 0.78, nb.add(n3, nb.mul(n5, 0.18))), moss * 0.85)
        mc = nb.mix(n5, MOSS, MOSS2)
        col = nb.mix(mm, col, mc)
    return col


ALB = 0.64   # global albedo scale for walls (bleached but dirty)


def concrete(base=(0.38, 0.37, 0.345), streak=0.5, moss=0.25, mottle=0.3, seed=0, bump=0.6, rust=0.0, moss_scale=0.5):
    base = tuple(c * ALB for c in base)
    def f(nb, co, raw, w):
        W = _W(w, seed)
        col = weather(nb, nb.rgb(base), co, w, streak, moss, mottle, seed, moss_scale, rust)
        h = nb.noise(co, scale=9.0, detail=5.0, rough=0.7, w=W)
        pits = nb.voronoi(co, scale=14.0, w=W)
        h = nb.add(nb.mul(h, 0.6), nb.mul(nb.smooth(0.0, 0.06, pits), 0.4))
        return dict(col=col, h=h, bump=bump, bumpd=0.01)
    return _named(f, 'conc')


def tiles(c1=(0.50, 0.42, 0.33), c2=(0.44, 0.36, 0.28), cm=(0.36, 0.35, 0.33), tw=0.227, th=0.06,
          streak=0.45, moss=0.2, seed=0):
    """small facade tiles (二丁掛け-ish); tw/th in metres"""
    c1 = tuple(c * ALB for c in c1); c2 = tuple(c * ALB for c in c2); cm = tuple(c * ALB for c in cm)
    def f(nb, co, raw, w):
        x, y, z = raw
        # bricks in object XZ (facade) coordinates: map (x, z) -> (u, v)
        uvv = nb.comb(x, z, 0.0)
        bc, bf = nb.brick(uvv, scale=1.0, mortar=0.006, bw=tw, rh=th, c1=c1, c2=c2, cm=cm, offset=0.5, smooth=0.2)
        col = weather(nb, bc, co, w, streak, moss, 0.25, seed)
        h = nb.sub(1.0, bf)
        return dict(col=col, h=h, bump=0.6, bumpd=0.004)
    return _named(f, 'tile')


def flat_color(c, mottle=0.25, streak=0.3, moss=0.0, seed=0, rust=0.0):
    c = tuple(x * (ALB if max(c) > 0.2 else 1.0) for x in c)
    def f(nb, co, raw, w):
        col = weather(nb, nb.rgb(c), co, w, streak, moss, mottle, seed, rust=rust)
        h = nb.noise(co, scale=5.0, detail=3.0, w=_W(w, seed))
        return dict(col=col, h=h, bump=0.2, bumpd=0.005)
    return _named(f, 'flat')


def paint(c, chip=0.35, under=(0.12, 0.075, 0.05), fade=0.35, seed=0, streak=0.35, moss=0.0):
    """faded paint over rusty metal, chipped."""
    def f(nb, co, raw, w):
        W = _W(w, seed)
        base = nb.rgb(c)
        # sun bleaching toward grey-white
        n0 = nb.noise(co, scale=0.7, detail=3.0, w=W)
        fd = nb.add(fade * 0.7, nb.mul(n0, fade * 0.6))
        base = nb.mix(fd, base, (0.62, 0.6, 0.56))
        nc = nb.noise(co, scale=4.0, detail=8.0, rough=0.7, w=W + 2.0)
        ch = nb.smooth(0.70 - chip * 0.15, 0.72 - chip * 0.15, nc)
        col = nb.mix(ch, base, under)
        col = weather(nb, col, co, w, streak, moss, 0.2, seed)
        return dict(col=col, h=nb.sub(1.0, ch), bump=0.4, bumpd=0.003)
    return _named(f, 'paint')


def metal(c=(0.40, 0.41, 0.40), ox=0.4, seed=0, streak=0.4, rust=0.15):
    def f(nb, co, raw, w):
        W = _W(w, seed)
        n = nb.noise(co, scale=3.0, detail=6.0, w=W)
        col = nb.mix(nb.mul(n, ox), nb.rgb(c), (0.30, 0.31, 0.29))
        col = weather(nb, col, co, w, streak, 0.0, 0.2, seed, rust=rust)
        return dict(col=col, h=n, bump=0.2, bumpd=0.003)
    return _named(f, 'metal')


def rust(c=RUSTC, seed=0, moss=0.0):
    def f(nb, co, raw, w):
        W = _W(w, seed)
        n = nb.noise(co, scale=6.0, detail=8.0, rough=0.7, w=W)
        n2 = nb.noise(co, scale=1.5, detail=3.0, w=W + 5.0 if isinstance(W, float) else W)
        col = nb.mix(n, c, (0.13, 0.06, 0.03))
        col = nb.mix(nb.smooth(0.55, 0.75, n2), col, (0.32, 0.17, 0.08))
        if moss:
            col = weather(nb, col, co, w, 0.2, moss, 0.1, seed)
        return dict(col=col, h=n, bump=0.5, bumpd=0.004)
    return _named(f, 'rust')


def glass(c=(0.022, 0.028, 0.034), seed=0, crack=0.5):
    """dark dirty glass: faint sky gradient, a few crack lines, grime at the bottom"""
    def f(nb, co, raw, w):
        W = _W(w, seed)
        x, y, z = raw
        n = nb.noise(co, scale=0.5, detail=2.0, w=W)
        col = nb.mix(nb.mul(n, 0.8), nb.rgb(c), (0.045, 0.055, 0.065))
        v = nb.voronoi(co, scale=1.1, feature='DISTANCE_TO_EDGE', w=W)
        msk = nb.smooth(0.55, 0.7, nb.noise(co, scale=0.7, detail=2.0, w=W + 9.0 if isinstance(W, float) else W))
        cr = nb.mul(nb.mul(nb.sub(1.0, nb.smooth(0.0, 0.008, v)), msk), crack)
        col = nb.mix(cr, col, (0.13, 0.135, 0.13))
        dirt = nb.noise(nb.vmath('MULTIPLY', co, (2, 2, 0.4)), scale=1.0, detail=3.0, w=W + 3.0 if isinstance(W, float) else W)
        col = nb.mix(nb.mul(nb.smooth(0.55, 0.85, dirt), 0.5), col, (0.10, 0.095, 0.08))
        return dict(col=col, h=None)
    return _named(f, 'glass')


def leafattr(var=0.25, seed=0):
    """leaves made of real polygons: colour from the face attribute 'lc'"""
    def f(nb, co, raw, w):
        at = nb.node('ShaderNodeAttribute', attribute_name='lc')
        col = at.outputs['Color']
        n = nb.noise(co, scale=30.0, detail=2.0, w=float(seed))
        m = nb.add(nb.mul(nb.sub(n, 0.5), var), 1.0)
        col = nb.mix(1.0, col, nb.comb(m, m, m), 'MULTIPLY')
        return dict(col=col, h=None)
    return _named(f, 'leaf')


def interior(c=(0.02, 0.02, 0.018), seed=0, var=0.6):
    def f(nb, co, raw, w):
        W = _W(w, seed)
        n = nb.noise(co, scale=0.8, detail=4.0, w=W)
        col = nb.mix(nb.mul(n, var), nb.rgb(c), (0.045, 0.043, 0.038))
        # ceilings read a little lighter near the top of a storey
        x, y, z = raw
        g = nb.smooth(2.6, 3.6, z)
        col = nb.mix(nb.mul(g, 0.6), col, (0.05, 0.05, 0.048))
        return dict(col=col, h=None)
    return _named(f, 'int')


def vine_curtain(hw=1.0, h=3.0, seed=0, density=0.5, lush=0.5):
    """hanging ivy curtain; object origin at top centre (object coords: x across, z down negative)"""
    def f(nb, co, raw, w):
        W = _W(w, seed)
        x, y, z = raw
        ax = nb.math('ABSOLUTE', x)
        loc = nb.comb(x, y, z)
        n = nb.noise(nb.vmath('MULTIPLY', loc, (1.4, 1.4, 0.55)), scale=1.0, detail=6.0, rough=0.65, w=float(seed), dim='4D')
        strands = nb.noise(nb.vmath('MULTIPLY', loc, (7.0, 7.0, 0.25)), scale=1.0, detail=2.0, w=float(seed) + 3.0, dim='4D')
        side = nb.sub(1.0, nb.smooth(0.25, 1.0, nb.mul(ax, 1.0 / hw)))
        down = nb.mul(nb.mul(z, -1.0 / h), 0.7)
        leaf = nb.voronoi(nb.mul(loc, 1.0) if False else loc, scale=26.0, w=float(seed), out='Distance', dim='4D')
        f_ = nb.add(nb.add(nb.mul(n, 0.9), nb.mul(side, 0.55 + 0.2 * density)), nb.sub(nb.mul(strands, 0.3), down))
        f_ = nb.add(f_, nb.mul(leaf, 0.18))
        a = nb.smooth(0.66, 0.68, f_)
        lv = nb.noise(loc, scale=16.0, detail=2.0, w=float(seed) + 4.0, dim='4D')
        c1 = (0.035 + 0.02 * lush, 0.06 + 0.03 * lush, 0.015)
        col = nb.mix(lv, c1, (0.10, 0.14, 0.035))
        col = nb.mix(nb.smooth(0.0, 0.12, leaf), (0.02, 0.03, 0.01), col)
        return dict(col=col, h=leaf, a=a, bump=0.8, bumpd=0.01)
    return _named(f, 'vinec')


def vines(seed=0, density=0.5):
    """painted ivy patches (alpha)"""
    def f(nb, co, raw, w):
        W = _W(w, seed)
        sc = nb.vmath('MULTIPLY', co, (1.2, 1.2, 0.45))
        n = nb.noise(sc, scale=1.0, detail=6.0, rough=0.7, w=W)
        leaf = nb.voronoi(co, scale=22.0, w=W, out='Distance')
        a = nb.smooth(0.62 - density * 0.15, 0.64 - density * 0.15, nb.add(n, nb.mul(leaf, 0.15)))
        lv = nb.noise(co, scale=14.0, detail=2.0, w=W + 4.0 if isinstance(W, float) else W)
        col = nb.mix(lv, (0.05, 0.075, 0.02), (0.12, 0.16, 0.04))
        return dict(col=col, h=leaf, a=a, bump=0.8, bumpd=0.01)
    return _named(f, 'vine')
