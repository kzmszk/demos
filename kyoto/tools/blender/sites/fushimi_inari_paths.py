"""伏見稲荷大社: the mountain path network (OSM footways / paths / steps as a graph), the pilgrim routes through it
(本殿 → 千本鳥居 → 奥社 → 熊鷹社 → 三ツ辻 → 四ツ辻 → the summit loop), their height profiles, stone steps and paving,
walk surfaces, and blockers along the torii tunnels."""
import math
import numpy as np
from jk import prim

FOOT = ('footway', 'path', 'steps', 'pedestrian', 'track', 'service', 'living_street')
SURF = ['none', 'asphalt', 'asphalt_lane', 'sidewalk', 'stone_sett', 'gravel', 'soil', 'grass', 'moss', 'forest', 'riverbed', 'ballast', 'concrete',
        'sand', 'graves', 'farm', 'tactile', 'stone_slab', 'wood_deck']

class Net:
    """nodes = OSM vertices (merged by position), edges = way segments"""
    def __init__(self, S, kinds=FOOT):
        self.S = S
        key = {}; self.xy = []; self.edges = []; self.ways = {}
        def node(p):
            k = (round(p[0], 2), round(p[1], 2))
            if k not in key: key[k] = len(self.xy); self.xy.append(p)
            return key[k]
        for w in S.osm['ways']:
            hw = w['tags'].get('highway')
            if hw not in kinds: continue
            self.ways[w['id']] = w
            for L in w['line']:
                for a, b in zip(L[:-1], L[1:]):
                    i, j = node(a), node(b)
                    if i == j: continue
                    ln = math.dist(a, b)
                    pen = {'service': 2.5, 'track': 1.5, 'living_street': 2.5}.get(hw, 1.0)
                    self.edges.append((i, j, w['id'], ln, pen))
        self.xy = np.array(self.xy, float)
        self.deg = np.zeros(len(self.xy), int)
        for (i, j, *_) in self.edges: self.deg[i] += 1; self.deg[j] += 1
        self.adj = {}
        for k, (i, j, wid, ln, pen) in enumerate(self.edges):
            self.adj.setdefault(i, []).append((j, k)); self.adj.setdefault(j, []).append((i, k))

    def nearest(self, x, y):
        return int(np.argmin(np.hypot(self.xy[:, 0] - x, self.xy[:, 1] - y)))

    def route(self, a, b, avoid=(), avoid_pen=8.0, prefer=None):
        """shortest path a -> b (node indices or (x, y)); edges in `avoid` cost avoid_pen x; returns [(node, edge)]"""
        import heapq
        if not isinstance(a, (int, np.integer)): a = self.nearest(*a)
        if not isinstance(b, (int, np.integer)): b = self.nearest(*b)
        avoid = set(avoid)
        dist = {a: 0.0}; prev = {}; pq = [(0.0, a)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == b: break
            if d > dist.get(u, 1e18): continue
            for (v, k) in self.adj.get(u, []):
                e = self.edges[k]
                w = e[3] * e[4] * (avoid_pen if k in avoid else 1.0) * (prefer(e) if prefer else 1.0)
                nd = d + w
                if nd < dist.get(v, 1e18):
                    dist[v] = nd; prev[v] = (u, k); heapq.heappush(pq, (nd, v))
        out = [(b, None)]; u = b
        while u != a:
            u, k = prev[u]; out.append((u, k))
        return out[::-1]          # [(node, edge to the next node)]

def _smooth(z, sig):
    if sig <= 0: return z.copy()
    k = int(3 * sig) + 1
    w = np.exp(-0.5 * (np.arange(-k, k + 1) / sig) ** 2); w /= w.sum()
    zp = np.concatenate([np.full(k, z[0]), z, np.full(k, z[-1])])
    return np.convolve(zp, w, mode='valid')

class Route:
    """a route through the net resampled every ds metres: s, P (x, y), T (unit tangents, smoothed), way ids, z (profile)"""
    def __init__(self, net, steps, S, name='', ds=0.25):
        self.name = name; self.S = S; self.net = net
        nodes = [n for n, e in steps]; edges = [e for n, e in steps[:-1]]
        self.nodes = nodes; self.edge_ids = edges
        V = net.xy[nodes]
        seg = np.linalg.norm(np.diff(V, axis=0), axis=1)
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        self.L = float(cum[-1]); self.node_s = cum
        n = max(2, int(self.L / ds) + 1)
        s = np.linspace(0.0, self.L, n)
        k = np.clip(np.searchsorted(cum, s, side='right') - 1, 0, len(seg) - 1)
        t = (s - cum[k]) / np.maximum(seg[k], 1e-9)
        self.s = s
        self.P = V[k] + (V[k + 1] - V[k]) * t[:, None]
        self.way = np.array([net.edges[edges[i]][2] for i in k])
        self.ds = self.L / (n - 1)
        # tangents: smoothed over ~1.5 m so torii fan smoothly round the bends
        Ps = np.stack([_smooth(self.P[:, 0], 1.5 / self.ds), _smooth(self.P[:, 1], 1.5 / self.ds)], 1)
        T = np.gradient(Ps, axis=0); T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
        self.T = T
        hw = np.array([net.ways[w]['tags'].get('highway') for w in self.way])
        self.is_steps = hw == 'steps'
        self.width = np.array([float(net.ways[w].get('width') or 2.0) for w in self.way])
        # profile: the laser DEM along the centre line, a little smoothed (keeps the stair flights)
        zc = S.ground(self.P[:, 0], self.P[:, 1])
        self.z_raw = zc
        self.z = _smooth(zc, 0.8 / self.ds)
        # junctions along the route: other ways leave here (gaps in the torii rows)
        self.junctions = [float(cum[i]) for i, nd in enumerate(nodes) if net.deg[nd] > 2 and 0 < i < len(nodes) - 1]

    def at(self, sv):
        """(x, y, z, tx, ty) at arc length sv"""
        i = np.clip(np.searchsorted(self.s, sv) , 1, len(self.s) - 1)
        f = (sv - self.s[i - 1]) / max(self.s[i] - self.s[i - 1], 1e-9)
        P = self.P[i - 1] + (self.P[i] - self.P[i - 1]) * f
        z = self.z[i - 1] + (self.z[i] - self.z[i - 1]) * f
        T = self.T[i - 1] + (self.T[i] - self.T[i - 1]) * f; T /= max(np.linalg.norm(T), 1e-9)
        return P[0], P[1], z, T[0], T[1]

    def idx(self, sv):
        return int(np.clip(round(sv / self.ds), 0, len(self.s) - 1))

    def sub(self, s0, s1):
        return (self.s >= s0) & (self.s <= s1)

    def s_near(self, x, y):
        return float(self.s[int(np.argmin(np.hypot(self.P[:, 0] - x, self.P[:, 1] - y)))])

def step_levels(r, riser=0.155, min_run=0.28):
    """stone steps where OSM has steps: the profile quantised into equal risers.  Returns zs (surface height per
    sample, flat treads on the steps, the smooth profile elsewhere) and the riser positions [(i, z_lo, z_hi)]"""
    z = r.z.copy(); zs = z.copy(); risers = []
    n = len(z); i = 0
    st = r.is_steps
    while i < n:
        if not st[i]: i += 1; continue
        j = i
        while j < n and st[j]: j += 1
        # flight i..j-1: quantise relative to its start
        za = z[i]; dz = z[j - 1] - za
        run = (j - 1 - i) * r.ds
        if abs(dz) < 0.12 or run < 0.6:
            i = j; continue
        nst = max(1, int(round(abs(dz) / riser)))
        h = dz / nst
        lvl = za
        last = i
        for k in range(i, j):
            target = za + h * round((z[k] - za) / h)
            if abs(target - lvl) > abs(h) * 0.5 and (k - last) * r.ds >= min_run:
                risers.append((k, lvl, target)); lvl = target; last = k
            zs[k] = lvl
        # blend the end of the flight back into the profile
        i = j
    return zs, risers

def corridor(B, r, zc, risers, o1, o2, pave, shoulder='gravel', bank='forest', every=4, walk=True, cut=None, z_lift=0.03):
    """the path as a terrain corridor (the generic terrain is cut away along it): paving (ground program, surface per
    sample `pave`), shoulders where the torii stand, banks blending into the laser DEM, an overlap skirt under the
    generic terrain's jagged cut edge.  On stair flights the paving is stone treads with stone risers.
    zc: paving level per sample (treads), r.z: the smooth profile; o1 / o2: paving / shoulder half widths per sample.
    Returns the half width cut away (o3) per sample."""
    S = r.S; n = len(r.s)
    o1 = np.broadcast_to(np.asarray(o1, float), (n,)); o2 = np.broadcast_to(np.asarray(o2, float), (n,))
    o3 = o2 + 1.6; o4 = o3 + 1.6
    rk = {k: (a, b) for (k, a, b) in risers}
    keep = set(range(0, n, every)) | {n - 1} | set(rk)
    keep = sorted(keep)
    Nn = np.stack([-r.T[:, 1], r.T[:, 0]], 1)
    secs = []                     # (k, points (8, 3), is_riser_second)
    for k in keep:
        c = r.P[k]; nn = Nn[k]; zs = r.z[k] + z_lift
        offs = np.array([-o4[k], -o3[k], -o2[k], -o1[k], o1[k], o2[k], o3[k], o4[k]])
        xy = c[None, :] + offs[:, None] * nn[None, :]
        zd = S.ground(xy[:, 0], xy[:, 1])
        def pts(zpave):
            z = np.array([zd[0] - 0.05, zd[1], zs, zpave, zpave, zs, zd[6], zd[7] - 0.05])
            return np.c_[xy, z]
        if k in rk:
            lo, hi = rk[k]
            secs.append((k, pts(lo + z_lift), False)); secs.append((k, pts(hi + z_lift), True))
        else:
            secs.append((k, pts(zc[k] + z_lift), False))
    m = len(secs)
    PS = np.array([q for (_, q, _) in secs])         # (m, 8, 3)
    riser_pair = np.array([sec[2] for sec in secs])  # True: this section and the previous form a riser
    # ground bands
    bands = [(0, bank), (1, bank), (2, shoulder), (3, None), (4, shoulder), (5, bank), (6, bank)]
    for b, surf in bands:
        V = np.concatenate([PS[:, b], PS[:, b + 1]])
        I = []
        for i in range(m - 1):
            if riser_pair[i + 1] and b in (2, 3, 4): continue
            I += [[i, i + 1, m + i + 1], [i, m + i + 1, m + i]]
        if not I: continue
        I = np.array(I)
        if b == 3:
            # paving: split by surface
            ks = np.array([secs[i][0] for i in I[:, 0] % m])
            for sf in sorted(set(pave[ks])):
                sel = pave[ks] == sf
                B.add(V, I[sel], 'ground', UV=V[:, :2], smooth=True, c1=(0, 0, 0, SURF.index(sf)))
        else:
            B.add(V, I, 'ground', UV=V[:, :2], smooth=True, c1=(0, 0, 0, SURF.index(surf)))
    # risers: stone faces across the paving (facing the lower side), slivers at the shoulders (both sides)
    Vr = []; Ir = []
    for i in range(1, m):
        if not riser_pair[i]: continue
        A = PS[i - 1]; Bq = PS[i]; k = secs[i][0]
        want = np.r_[-r.T[k], 0.0] * (1.0 if Bq[3][2] > A[3][2] else -1.0)
        q = len(Vr); Vr += [A[3], A[4], Bq[4], Bq[3]]
        fn = np.cross(A[4] - A[3], Bq[4] - A[3])
        Ir += [[q, q + 1, q + 2], [q, q + 2, q + 3]] if fn @ want > 0 else [[q, q + 2, q + 1], [q, q + 3, q + 2]]
        for (a_, b_) in ((3, 2), (4, 5)):
            q = len(Vr); Vr += [A[a_], Bq[a_], A[b_]]
            Ir += [[q, q + 1, q + 2], [q, q + 2, q + 1]]
    if Vr:
        B.add(np.array(Vr), np.array(Ir), 'stone')
    if walk:
        idx = list(range(0, n, every)) + ([n - 1] if (n - 1) % every else [])
        zw = _smooth(r.z, 1.6 / r.ds)          # the walker: a gentler ramp over steep flights (max step 0.42 m per cell)
        P = r.P[idx]; nn = Nn[idx]; zs = zw[idx] + 0.02
        cols = [(-o3[idx], None), (-o2[idx], zs), (o2[idx], zs), (o3[idx], None)]
        V = []
        for off, zz in cols:
            xy = P + off[:, None] * nn
            V.append(np.c_[xy, S.ground(xy[:, 0], xy[:, 1]) if zz is None else zz])
        mm = len(idx); V = np.concatenate(V); I = []
        for c in range(3):
            for i in range(mm - 1):
                a = c * mm + i
                I += [[a, a + 1, a + mm + 1], [a, a + mm + 1, a + mm]]
        B.add(V, np.array(I), 'stone', tag='walk')
    if cut is not None:
        from shapely.geometry import LineString
        ln = LineString(r.P[::4] if len(r.P) > 8 else r.P)
        g = ln.buffer(float(np.median(o3)) + 0.2, cap_style='flat').simplify(0.3)
        cut.append(g)
    return o3

def block_bands(B, r, ranges, inner, outer, every=4):
    """blockers on both sides of a torii tunnel (cells of the 0.5 m walk map): from `inner` to `outer` off the centre;
    inner / outer: scalars or per-sample arrays for each side ((left, right) tuples of arrays)"""
    n = len(r.s)
    def per(v, side):
        if isinstance(v, tuple): v = v[0 if side > 0 else 1]
        return np.broadcast_to(np.asarray(v, float), (n,))
    for (s0, s1) in ranges:
        sel = np.where(r.sub(s0, s1))[0][::every]
        if len(sel) < 2: continue
        P = r.P[sel]; T = r.T[sel]; Nn = np.stack([-T[:, 1], T[:, 0]], 1); z = r.z[sel]
        m = len(sel)
        for sg in (-1, 1):
            a = per(inner, sg)[sel][:, None]; b = per(outer, sg)[sel][:, None]
            V = np.concatenate([np.c_[P + Nn * sg * a, z], np.c_[P + Nn * sg * b, z]])
            I = []
            for i in range(m - 1):
                I += [[i, m + i, m + i + 1], [i, m + i + 1, i + 1]]
            B.add(V, np.array(I), 'stone', tag='block')
