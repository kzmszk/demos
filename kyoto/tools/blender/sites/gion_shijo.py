"""四条通 between 四条大橋 and 八坂神社: the low shop houses (sites.machiya kind 'shop': glazed fronts, sign boards,
hanging signs, deep 庇; tall ones three storeys) and the sidewalk arcade (アーケード) with its lanterns along both
building lines; the mid-rise blocks stay generic."""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, LineString, Point, box as sbox
from jk import prim
import sites.machiya as M
import sites.gion_streets as G

SHIJO = 854442449

def build(B, S, used, stats):
    L = G.way_line(S, SHIJO)
    picks = [(b, P) for (b, P) in G.select(S, L, 14.5, kinds=('trad', 'house', 'mid'), max_h=12.6, used=used) if P.area > 15]
    def styler(b, P, ring, rng):
        h = float(b['h'] or 8)
        st = dict(kind='shop', degoshi=False, inuyarai=False, komayose=False, chochin=rng.random() < 0.25,
                  noren=M.NOREN[rng.integers(len(M.NOREN))] if rng.random() < 0.6 else False,
                  wall=[(226, 220, 204), (214, 200, 172), (200, 186, 160), (232, 228, 218), (190, 168, 128)][rng.integers(5)])
        if h > 10.6: st['z_wp'] = 8.6 + rng.uniform(-0.2, 0.3)
        if h < 5.8: st['kind'] = 'hiraya'
        return st
    n = G.build_row(B, S, picks, L, prefer='shop', seed0=4, used=used, stats=stats, styler=styler, need=8.0)
    arcade(B, S, L)
    return n

def arcade(B, S, L, depth=3.3, z_f=4.25, z_c=3.95, post=5.6):
    """the Gion Shijo arcade: green steel canopies along both building lines, posts at the curb, lanterns"""
    # building line offsets per side (median of the facades), gaps at the cross streets and at 一力 / 南座
    cross = []
    for w in S.osm['ways']:
        if w['id'] in (SHIJO, 1510539685): continue
        hw = w['tags'].get('highway')
        if hw in (None, 'footway', 'steps', 'path', 'cycleway', 'crossing'): continue
        for l in w['line']:
            if len(l) < 2: continue
            g = LineString(l)
            if g.distance(L) < 1.0:
                x = g.intersection(L.buffer(14.0))
                if x.is_empty: continue
                cross.append((x, (w.get('width') or 4.0) / 2 + 1.2))
    skip = {1: [], -1: [(0, 52.0), (262.0, 300.0), (440.0, 470.0)]}       # 南座, 一力亭, the Yasaka end
    skip[1] += [(0, 14.0), (450.0, 470.0)]
    for side in (1, -1):
        off_f = 11.5; off_c = off_f - depth             # the building line (roof outlines; walls 0.85 behind)
        # walk along the line in post steps, collecting runs not interrupted by a gap
        t = 2.0; run = []
        def flush(run):
            if len(run) >= 2: canopy(B, S, L, run, side, off_f, off_c, z_f, z_c)
        while t < L.length - 2.0:
            p = L.interpolate(t)
            d = tangent(L, t); nrm = np.array([-d[1], d[0]]) * side
            q = Point(p.x + nrm[0] * (off_f + off_c) / 2, p.y + nrm[1] * (off_f + off_c) / 2)
            bad = any(a <= t <= b for (a, b) in skip[side]) or any(g.distance(q) < r for (g, r) in cross)
            if bad:
                flush(run); run = []
            else:
                run.append(t)
            t += 1.4
        flush(run)

def tangent(L, t):
    a = L.interpolate(max(0, t - 1.0)); b = L.interpolate(min(L.length, t + 1.0))
    d = np.array([b.x - a.x, b.y - a.y]); return d / max(np.linalg.norm(d), 1e-9)

def canopy(B, S, L, ts, side, off_f, off_c, z_f, z_c):
    t0, t1 = ts[0], ts[-1]
    n = max(1, int(round((t1 - t0) / 5.6)))
    tt = np.linspace(t0, t1, n * 4 + 1)
    F = []; C = []; Zg = []
    for t in tt:
        p = L.interpolate(t); d = tangent(L, t); nrm = np.array([-d[1], d[0]]) * side
        f = np.array([p.x, p.y]) + nrm * off_f; c = np.array([p.x, p.y]) + nrm * off_c
        F.append(f); C.append(c); Zg.append(float(S.ground(*c)))
    F = np.array(F); C = np.array(C); Zg = np.array(Zg)
    green = (62, 92, 74, 0)
    # roof: a shallow slope from the facade to the curb, a raised clerestory ridge in the middle
    Q = []
    for i in range(len(tt) - 1):
        a, b = i, i + 1
        Q.append([(*C[a], Zg[a] + z_c), (*C[b], Zg[b] + z_c), (*F[b], Zg[b] + z_f), (*F[a], Zg[a] + z_f)])
    Q = np.array(Q)
    up = np.array([0, 0, 1.0])
    for q in Q: M.oquad(B, q, up, 'roof_metal', tag='main', c0=green)
    for q in Q: M.oquad(B, q - [0, 0, 0.12], -up, 'roof_metal', tag='main', c0=(44, 62, 52, 0))
    # fascia along the curb with the sign band, posts, lanterns
    for i in range(len(tt) - 1):
        a, b = i, i + 1
        P4 = np.array([(*C[a], Zg[a] + z_c - 0.55), (*C[b], Zg[b] + z_c - 0.55), (*C[b], Zg[b] + z_c + 0.05), (*C[a], Zg[a] + z_c + 0.05)])
        nrm = np.r_[(C[a] - F[a]) / max(np.linalg.norm(C[a] - F[a]), 1e-6), 0]
        M.oquad(B, P4, nrm, 'roof_metal', tag='main', c0=green)
        M.oquad(B, P4, -nrm, 'roof_metal', tag='main', c0=green)
    for k in range(0, len(tt), 4):
        c = C[k]; z = Zg[k]
        prim.cyl(B, (c[0], c[1], z), (c[0], c[1], z + z_c - 0.5), 0.08, 0.08, 8, 'roof_metal', tag='main', c0=green)
        prim.polygon(B, [(c[0] - 0.3, c[1] - 0.3), (c[0] + 0.3, c[1] - 0.3), (c[0] + 0.3, c[1] + 0.3), (c[0] - 0.3, c[1] + 0.3)], z + 0.05, 'stone', tag='block')
        # a lantern between the posts (the arcade's 祇園 lanterns)
        if k + 2 < len(tt):
            m = (C[k + 2] * 0.85 + F[k + 2] * 0.15); zm = Zg[k + 2]
            M.chochin(B, m[0], m[1], zm + z_c - 0.55, r=0.2, h=0.5, mat='lantern_paper', lamp=(k // 4) % 2 == 0, watts=8.0)
    # beams across, at every post, and a line of lights under the roof
    bars = []
    for k in range(0, len(tt), 2):
        bars.append(((*C[k], Zg[k] + z_c - 0.2), (*F[k], Zg[k] + z_f - 0.2)))
    if bars:
        M.bars(B, [b_[0] for b_ in bars], [b_[1] for b_ in bars], (0, 0, 1), 0.08, 0.12, 'roof_metal', tag='detail', c0=green)
    for k in range(1, len(tt), 4):
        m = (C[k] + F[k]) / 2
        prim.box(B, m[0] - 0.15, m[1] - 0.15, Zg[k] + (z_f + z_c) / 2 - 0.35, m[0] + 0.15, m[1] + 0.15, Zg[k] + (z_f + z_c) / 2 - 0.2, 'lamp', tag='detail')
