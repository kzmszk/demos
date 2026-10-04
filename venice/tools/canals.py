"""Canal network for the gondola (venv python):  python canals.py OUT.json
OSM waterway=canal centre lines -> graph (OSM node ids at junctions) -> named gondola routes through
waypoints (shortest paths), resampled every metre and smoothed so the boat turns gently."""
import sys, json, math, heapq
import numpy as np
import shapely
from shapely.geometry import LineString, Point
from gen.world import load

BBOX = (-2400, -800, 2400, 1700)       # the historic centre (rii + Grand Canal + Giudecca/Bacino edges)

def graph(w):
    o = w.o
    adj = {}; pos = {}; names = {}
    for wid, way in o.ways.items():
        t = way.get('tags', {})
        if t.get('waterway') != 'canal' or way['nodes'][0] == way['nodes'][-1]: continue
        ns = [n for n in way['nodes'] if n in o.nodes]
        if len(ns) < 2: continue
        P = [o.xy(n) for n in ns]
        if not any(BBOX[0] < x < BBOX[2] and BBOX[1] < y < BBOX[3] for x, y in P): continue
        for n, p in zip(ns, P): pos[n] = p
        for a, b in zip(ns[:-1], ns[1:]):
            d = math.dist(pos[a], pos[b])
            adj.setdefault(a, {})[b] = d; adj.setdefault(b, {})[a] = d
            names[(a, b)] = names[(b, a)] = t.get('name', '')
    # join dangling ends that stop just short of another line (mapping gaps at junctions)
    ends = [n for n, e in adj.items() if len(e) == 1]
    P = np.array([pos[n] for n in adj]); ids = list(adj)
    for n in ends:
        d = np.linalg.norm(P - np.array(pos[n]), axis=1)
        for k in np.argsort(d)[1:6]:
            m = ids[k]
            if m != n and d[k] < 8.0 and m not in adj[n]:
                adj[n][m] = adj.setdefault(m, {})[n] = float(d[k]); names[(n, m)] = names[(m, n)] = ''
                break
    return adj, pos, names

def nearest(pos, xy):
    best = min(pos, key=lambda n: (pos[n][0] - xy[0]) ** 2 + (pos[n][1] - xy[1]) ** 2)
    return best

def dijkstra(adj, a, b, penalty=None):
    dist = {a: 0.0}; prev = {}; pq = [(0.0, a)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == b: break
        if d > dist.get(u, 1e18): continue
        for v, wgt in adj[u].items():
            nd = d + wgt * (penalty(u, v) if penalty else 1.0)
            if nd < dist.get(v, 1e18): dist[v] = nd; prev[v] = u; heapq.heappush(pq, (nd, v))
    path = [b]
    while path[-1] != a:
        if path[-1] not in prev: return None
        path.append(prev[path[-1]])
    return path[::-1]

def smooth(P, step=1.0, win=9, iters=3):
    """resample a polyline every `step` metres, then relax corners (keeps the ends)."""
    L = LineString(P)
    n = max(2, int(L.length / step))
    Q = np.array([L.interpolate(t, normalized=True).coords[0] for t in np.linspace(0, 1, n)])
    for _ in range(iters):
        R = Q.copy()
        k = win // 2
        for i in range(k, len(Q) - k): R[i] = Q[i - k:i + k + 1].mean(0)
        Q = R
    return Q

def route(adj, pos, names, pts, land=None):
    """shortest path through waypoints (world xy); returns polyline + names along it."""
    nodes = [nearest(pos, p) for p in pts]
    out = []; nm = []
    for a, b in zip(nodes[:-1], nodes[1:]):
        p = dijkstra(adj, a, b)
        if p is None: raise RuntimeError(f'no path {a}->{b}')
        if out: p = p[1:]
        for u, v in zip(p[:-1], p[1:]): nm.append(names.get((u, v), ''))
        out += p
    return [pos[n] for n in out], nm

def main():
    w = load()
    adj, pos, names = graph(w)
    print('canal graph', len(adj), 'nodes', sum(len(e) for e in adj.values()) // 2, 'edges')
    o = w.o
    def named(n):
        for wid, way in o.ways.items():
            t = way.get('tags', {})
            if t.get('name') == n and ('building' in t or 'bridge' in t or 'man_made' in t or 'highway' in t):
                P = np.array(o.way_xy(wid)); return P.mean(0)
        return None
    from gen.hero.common import wf
    # waypoints (world xy): Molo by the Ponte della Paglia, Rio di Palazzo under the Bridge of Sighs, the Rialto,
    # Rio della Fenice by the theatre's water gate, Bacino Orseolo (the gondola basin behind the piazza)
    WP = {
        'molo': (150.0, -75.0), 'sospiri': (144.5, -0.5), 'rialto': (-240.0, 445.0),
        'fenice': (-482.0, -60.0), 'orseolo': (-168.0, 26.0), 'salute': (-330.0, -310.0), 'accademia': (-790.0, -270.0),
    }
    routes = {
        # the classic: Bridge of Sighs -> Rialto -> La Fenice -> Bacino Orseolo
        'grand': ['molo', 'sospiri', 'rialto', 'fenice', 'orseolo'],
        # short: from the basin through the small canals to the Bridge of Sighs and out to the Molo
        'sospiri': ['orseolo', 'sospiri', 'molo'],
        # the Grand Canal from the Salute to the Rialto
        'canalgrande': ['salute', 'accademia', 'rialto'],
    }
    out = {'routes': {}, 'graph': None}
    for k, wps in routes.items():
        P, nm = route(adj, pos, names, [WP[x] for x in wps])
        Q = smooth(np.array(P))
        L = float(np.sum(np.linalg.norm(np.diff(Q, axis=0), axis=1)))
        # names along the route at their arc positions
        segs = []; acc = 0.0
        for (a, b), n in zip(zip(P[:-1], P[1:]), nm):
            if n and (not segs or segs[-1][1] != n): segs.append([round(acc, 1), n])
            acc += math.dist(a, b)
        out['routes'][k] = {'pts': np.round(Q, 2).tolist(), 'length': round(L, 1), 'names': segs, 'via': wps}
        print(k, f'{L:.0f} m', [s[1] for s in segs][:20])
    # compact graph (for 'go to' requests): node positions + edges
    ids = {n: i for i, n in enumerate(adj)}
    out['graph'] = {'nodes': [[round(pos[n][0], 1), round(pos[n][1], 1)] for n in adj],
                    'edges': sorted({(min(ids[a], ids[b]), max(ids[a], ids[b])) for a in adj for b in adj[a]})}
    json.dump(out, open(sys.argv[1], 'w'), separators=(',', ':'))

if __name__ == '__main__':
    main()
