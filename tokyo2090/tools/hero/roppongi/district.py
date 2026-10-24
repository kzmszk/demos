"""Every PLATEAU footprint -> a ruin (generic) unless a signature module owns it."""
import json, math
import numpy as np
import lib, ruins
from ruins import Cut

# buildings handled elsewhere (signature modules) -> skip here
OWNED = {'b026'}          # Metro Hat (metrohat in plaza.py)
# per-building overrides: style / cut / extra
OVR = {
    # TV Asahi: Maki's long glass block by the garden; west end sheared, roof garden gone wild
    'b007': dict(style=dict(upper='glass', ruin='glass_ruin', ground='glass', fh=4.6), holes=0.05,
                 cut=('wedge', 0.62, (0.35, 0.0), 1.0), seg=6.0),
    # Grand Hyatt + West Walk + Keyakizaka complex podium (b000 minus the tower)
    'b000': dict(style=dict(upper='glass', ruin='glass_ruin', ground='shop', fh=4.4), holes=0.035, seg=6.0),
    # Residence towers: tall, sheared tops
    'b001': dict(style=dict(upper='apt', ruin='apt_ruin', ground='shop', fh=3.2), cut=('both', 0.76, (0.0, -0.5), 3.0), core=True),
    'b002': dict(style=dict(upper='apt', ruin='apt_ruin', ground='shop', fh=3.2), cut=('wedge', 0.70, (-1.1, 0.3), 2.5), core=True),
    'b003': dict(style=dict(upper='glass', ruin='glass_ruin', ground='shop', fh=4.0), cut=('top', 0.85, (0.0, 0.0), 1.5)),
    'b004': dict(style=dict(upper='apt', ruin='apt_ruin', ground='shop', fh=3.1), cut=('wedge', 0.78, (0.6, 0.6), 2.0), core=True),
    'b005': dict(style=dict(upper='apt', ruin='apt_ruin', ground='apt', fh=3.1), cut=('top', 0.86, (0, 0), 2.0)),
    'b008': dict(style=dict(upper='apt', ruin='apt_ruin', ground='apt', fh=3.1), cut=('wedge', 0.8, (-0.5, -0.8), 2.0)),
    'b006': dict(style=dict(upper='glass', ruin='glass_ruin', ground='shop', fh=4.0), cut=('wedge', 0.75, (-0.8, 0.5), 2.0)),
    # arena canopy footprint: the arena itself is built in plaza.py; here only nothing
    'b022': dict(skip=True),
    # museum cone footprint (built in plaza.py)
    'b016': dict(skip=True),
    # the small pavilions on 66 Plaza: they stand on the deck
    'b014': dict(remains=True, base=lib.PLAZA_Z),
    'b018': dict(remains=True, base=lib.PLAZA_Z), 'b019': dict(remains=True), 'b020': dict(remains=True, base=lib.PLAZA_Z),
    'b023': dict(remains=True), 'b025': dict(remains=True), 'b028': dict(remains=True, base=lib.PLAZA_Z),
    'b030': dict(remains=True), 'b075': dict(remains=True),
    'b027': dict(skip=True),     # the curved canopy over the Metro Hat -> plaza walkway (plaza.py)
}


def build(sc, col, ctx):
    P = json.load(open(lib.WORK + 'prisms.json'))
    G = ctx['ground']
    stats = {}
    for name in sorted(k for k in P if k.startswith('b')):
        b = P[name]
        if name in OWNED or not b['prisms']:
            continue
        o = OVR.get(name, {})
        if o.get('skip'):
            continue
        idx = int(name[1:])
        rr = lib.rng(1000 + idx)
        h = b['z1'] - b['z0']
        st = o.get('style') or ruins.style_for(b['use'], h, rr)
        before = sum(v.tris() for v in sc.b.values())
        ib = sc['interior'].tris()
        gbase = b['gmin'] - 0.4
        base = o.get('base', None)
        if o.get('top'):
            b = dict(b); b['prisms'] = [dict(p, z1=min(p['z1'], o['top'])) for p in b['prisms']]
        z1max = max(p['z1'] for p in b['prisms'])
        # damage
        cspec = o.get('cut')
        if cspec is None:
            r = rr.random()
            if h > 30 and r < 0.75:
                cspec = (rr.choice(['top', 'wedge', 'both']), rr.uniform(0.6, 0.85), (rr.uniform(-0.8, 0.8), rr.uniform(-0.8, 0.8)), 2.0)
            elif h > 12 and r < 0.45:
                cspec = ('wedge', rr.uniform(0.65, 0.9), (rr.uniform(-0.7, 0.7), rr.uniform(-0.7, 0.7)), 1.5)
            else:
                cspec = None
        zlo = base if base is not None else gbase
        if cspec:
            kind, frac, g, jag = cspec
            h0 = zlo + (z1max - zlo) * frac
            cut = Cut(kind if kind != 'both' else 'wedge', h0, g, (b['cx'], b['cy']), jag, seed=idx * 7 + 1, top=z1max,
                      h1=(h0 - 2 if kind == 'both' else None), grad1=((0.0, 0.0) if kind == 'both' else None))
            if kind == 'top':
                cut = Cut('top', h0, (g[0] * 0.15, g[1] * 0.15), (b['cx'], b['cy']), jag, seed=idx * 7 + 1, top=z1max)
        else:
            cut = Cut('none')
        if o.get('remains'):
            # collapsed: a stump of broken walls + rubble (rubble heap added by rubble.py via ctx)
            pr = b['prisms'][0]
            hh = rr.uniform(1.2, 3.0)
            ruins.ruin_prism(sc, col, pr['poly'], zlo, (base or b['gmax']) + hh, dict(upper='apt_ruin', ground='apt_ruin', fh=3.0),
                             Cut('top', (base or b['gmax']) + hh * 0.7, (0, 0), (b['cx'], b['cy']), 1.2, seed=idx, top=(base or b['gmax']) + hh),
                             seed=idx * 31, holes=0.3, seg=2.0)
            ar = abs(lib.poly_area(pr['poly'])) ** 0.5
            ctx.setdefault('rubble', []).append((b['cx'], b['cy'], (2.0 + ar * 0.3) if base else (3.0 + ar * 0.5),
                                                 min(hh + 0.5, 1.4 if base else 2.2), base))
            stats[name] = sum(v.tris() for v in sc.b.values()) - before
            continue
        if cspec and cspec[0] in ('wedge', 'both') and h > 12:
            g = np.array(cspec[2], float)
            if np.linalg.norm(g) > 0.05:
                area0 = sum(abs(lib.poly_area(p['poly'])) for p in b['prisms'][:1])
                dirv = -g / np.linalg.norm(g)
                Rb = math.sqrt(area0) * 0.55
                ctx.setdefault('falls', []).append((b['cx'] + dirv[0] * (Rb + 3), b['cy'] + dirv[1] * (Rb + 3),
                                                    min(4 + h * 0.12, 14), min(1.5 + h * 0.05, 5.5), None))
        for k, pr in enumerate(b['prisms']):
            if name == 'b000':
                # open 66 Plaza: nothing of the podium stands NE of the tower's tangent (the plaza side)
                C = np.array([-49.6, 49.4]); nv = np.array([0.7071, 0.7071])
                poly = ruins.clip_halfplane([np.array(q, float) for q in lib.ccw([tuple(q) for q in pr['poly']])],
                                            lambda q: 46.0 - float(np.dot(q - C, nv)))
                if len(poly) < 3 or abs(lib.poly_area([tuple(q) for q in poly])) < 20:
                    continue
                pr = dict(pr, poly=[list(map(float, q)) for q in poly])
            z0 = pr['z0']
            if k == 0 or abs(z0 - b['z0']) < 0.5:
                z0 = zlo
            if pr['z1'] - z0 < 1.0:
                continue
            area = abs(lib.poly_area(pr['poly']))
            core = None
            if o.get('core') and k == 0:
                xs = [p[0] for p in pr['poly']]; ys = [p[1] for p in pr['poly']]
                core = (b['cx'], b['cy'], 7.0, 9.0, 0.0)
            ruins.ruin_prism(sc, col, pr['poly'], z0, pr['z1'], st, cut, seed=idx * 31 + k,
                             holes=o.get('holes', 0.06 if h > 15 else 0.04), seg=o.get('seg', 5.0 if area > 300 else 3.5),
                             core=core, rec=ctx, bid=name)
        stats[name] = sum(v.tris() for v in sc.b.values()) - before
        ctx.setdefault('int_by', {})[name] = sc['interior'].tris() - ib
    ctx['labels'] += [{'name': 'グランドハイアット東京', 'x': -128.0, 'y': -12.0, 'z': 124.0, 'kind': 'building'},
                      {'name': '六本木ヒルズレジデンス', 'x': 48.0, 'y': -121.0, 'z': 150.0, 'kind': 'building'}]
    print('interior by building', sorted(ctx['int_by'].items(), key=lambda kv: -kv[1])[:12])
    return stats
