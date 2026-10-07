"""清水寺: the buildings other than the 本堂 — 仁王門, 西門, 三重塔, 鐘楼, 随求堂, 経堂, 田村堂 (開山堂), 朝倉堂, 轟門 + 回廊,
釈迦堂, 阿弥陀堂, 奥の院 (+ its 舞台), 子安塔, 地主神社, 音羽の滝, and plain versions of the precinct's other buildings.

Each building is placed in its own frame from the OSM footprint (S.rect): u along the front, front at -v, z absolute.
Heights from the dossier / PLATEAU (z0 + measuredHeight ~ ridge top)."""
import math
import numpy as np
import jk
from jk import prim, arch, Frame
from sites import kiyomizu_lib as K

# ------------------------------------------------------------------ frames
def bframe(S, osm_id, front_deg, shift=(0.0, 0.0)):
    """(cx, cy, yaw, L_front, D_depth) for an OSM footprint; yaw = the u axis so that the front (-v) faces front_deg"""
    b = S.osm_building(osm_id)
    cx, cy, L, W, yaw = S.rect(b['poly'][0])
    best = None
    for k in range(4):
        y = yaw + k * math.pi / 2
        fd = math.degrees(math.atan2(-math.cos(y), math.sin(y)))
        err = abs((fd - front_deg + 180) % 360 - 180)
        if best is None or err < best[0]: best = (err, y, k)
    _, y, k = best
    Lf, Dd = (L, W) if k % 2 == 0 else (W, L)
    c, s = math.cos(y), math.sin(y)
    return cx + shift[0] * c - shift[1] * s, cy + shift[0] * s + shift[1] * c, y, Lf, Dd

def gfun(S, fr):
    """terrain height in a frame's local coordinates"""
    ox, oy, yaw = fr[:3]
    c, s = math.cos(yaw), math.sin(yaw)
    return lambda u, v: S.ground(ox + u * c - v * s, oy + u * s + v * c)

# ------------------------------------------------------------------ a generic Japanese hall
def bays(widths):
    w = np.asarray(widths, float); x = np.r_[0, np.cumsum(w)]
    return x - x[-1] / 2

def hall(B, us, vs, z0, H, mat='vermilion', r=0.22, walls=None, upper='plaster', nageshi=True, brackets='hira', bscale=0.85, bmat=None, bend='white_paint',
         roof=None, veranda=None, vmat='wood_natural', rail=None, rail_mat=None, giboshi=True, steps=None, base=None, base_mat='stone', interior=True,
         ceiling_dark=True, inner_pillars=False, zground=None, under='lattice', tag='main', post_base='stone'):
    """us, vs: pillar lines (local u along the front, v depth; the front is v = vs[0]).  z0 floor, H pillar height.
    walls: {'front'|'back'|'left'|'right': [kind per bay]} with kinds plaster / board / lattice / shitomi / karado /
    renji / open / door / katomado / kirido (dark doorway).  roof: kwargs for K.mroof (L, D taken from the plan + reach).
    veranda: (width, sides) ; rail: sides with a 高欄 ; steps: [(side, u or v centre, width, z_bottom)] ;
    base: (z_bottom, margin) stone platform under the floor."""
    bmat = bmat or mat
    rail_mat = rail_mat or mat
    L = us[-1] - us[0]; D = vs[-1] - vs[0]
    uc = (us[0] + us[-1]) / 2; vc = (vs[0] + vs[-1]) / 2
    zt = z0 + H
    # platform / plinth
    if base is not None:
        zb, m = base
        a, c = L / 2 + m, D / 2 + m
        if veranda: a += veranda[0]; c += veranda[0]
        arch.platform(B, [(uc - a, vc - c), (uc + a, vc - c), (uc + a, vc + c), (uc - a, vc + c)], zb, (z0 - 0.55) if veranda else z0, base_mat, walk=False)
    # pillars
    for i, u in enumerate(us):
        for j, v in enumerate(vs):
            if 0 < i < len(us) - 1 and 0 < j < len(vs) - 1 and not inner_pillars: continue
            K.post(B, u, v, z0, zt, r, mat, base=None if base is not None or veranda or not post_base else post_base, base_h=0.12)
    # floor
    prim.box(B, us[0] - 0.15, vs[0] - 0.15, z0 - 0.12, us[-1] + 0.15, vs[-1] + 0.15, z0, vmat, faces='Z')
    # beams: 頭貫 (top), 長押 (under the 小壁), 腰長押
    ring = [(us[0], vs[0]), (us[-1], vs[0]), (us[-1], vs[-1]), (us[0], vs[-1]), (us[0], vs[0])]
    zn = zt - 1.0
    for a, b in zip(ring[:-1], ring[1:]):
        K.beam(B, a, b, zt - 0.02, 0.2, 0.26, mat, ext=0.3)
        if nageshi:
            K.beam(B, a, b, zn, 0.14, 0.2, mat, ext=0.12)
            K.beam(B, a, b, z0 + 0.42, 0.12, 0.16, mat, ext=0.1)
    # walls
    walls = walls or {}
    sides = {'front': (list(zip(us[:-1], us[1:])), lambda a: ((a[0], vs[0]), (a[1], vs[0])), (0, -1)),
             'back': (list(zip(us[:-1], us[1:])), lambda a: ((a[1], vs[-1]), (a[0], vs[-1])), (0, 1)),
             'left': (list(zip(vs[:-1], vs[1:])), lambda a: ((us[0], a[1]), (us[0], a[0])), (-1, 0)),
             'right': (list(zip(vs[:-1], vs[1:])), lambda a: ((us[-1], a[0]), (us[-1], a[1])), (1, 0))}
    for side, (spans, seg, out) in sides.items():
        kinds = walls.get(side, ['plaster'] * len(spans))
        for k_, sp in zip(kinds, spans):
            p0, p1 = seg(sp)
            p0 = np.array(p0, float); p1 = np.array(p1, float); d = K.unit(p1 - p0)
            q0 = p0 + d * (r + 0.02); q1 = p1 - d * (r + 0.02)
            o = np.array(out, float)
            zlo, zhi = z0 + 0.5, zn - 0.1
            if k_ == 'plaster':
                K.wall_panel(B, q0 - o * 0.06, q1 - o * 0.06, z0 + 0.34, zhi, 'temple_wall', both=False, out=o, **K.PLASTER)
            elif k_ == 'board':
                K.wall_panel(B, q0 - o * 0.05, q1 - o * 0.05, z0 + 0.34, zhi, 'wall_board', both=False, out=o)
            elif k_ in ('lattice', 'shitomi', 'koshi'):
                K.wall_panel(B, q0 - o * 0.05, q1 - o * 0.05, z0 + 0.34, zlo + 0.3, 'wall_board' if k_ != 'koshi' else mat, both=False, out=o)
                K.lattice(B, q0, q1, zlo + 0.3, zhi, mat='black_lacquer' if mat == 'vermilion' and k_ == 'shitomi' else ('wood_dark' if mat != 'vermilion' else mat),
                          step=0.17, back='glass', out=o)
            elif k_ == 'renji':
                K.wall_panel(B, q0 - o * 0.06, q1 - o * 0.06, z0 + 0.34, zlo + 0.7, 'temple_wall', both=False, out=o, **K.PLASTER)
                arch.infill(B, q0, q1, zlo + 0.7, zhi - 0.25, 'renji', out=o, mat='copper' if mat == 'vermilion' else 'wood_dark')
                K.wall_panel(B, q0 - o * 0.06, q1 - o * 0.06, zhi - 0.25, zhi, 'temple_wall', both=False, out=o, **K.PLASTER)
            elif k_ in ('karado', 'door'):
                arch.infill(B, q0 + d * 0.0, q1, z0 + 0.34, zhi, 'karado', out=o, mat=mat if k_ == 'karado' else 'wood_dark')
            elif k_ == 'katomado':
                arch.infill(B, q0, q1, z0 + 0.34, zhi, 'katomado', out=o, mat=mat)
            elif k_ == 'kirido':
                K.wall_panel(B, q0 - o * 0.4, q1 - o * 0.4, z0, zhi, 'glass', both=False, out=o)
            # 小壁 (upper band) between 長押 and 頭貫
            if upper and k_ != 'open':
                K.wall_panel(B, q0 - o * 0.05, q1 - o * 0.05, zn + 0.1, zt - 0.15, 'temple_wall' if upper == 'plaster' else 'wall_board', both=False, out=o,
                             **(K.PLASTER if upper == 'plaster' else {}))
            elif upper and k_ == 'open':
                K.wall_panel(B, q0 - o * 0.05, q1 - o * 0.05, zn + 0.1, zt - 0.15, 'temple_wall' if upper == 'plaster' else 'wall_board', both=True, out=o,
                             **(K.PLASTER if upper == 'plaster' else {}))
    # interior: a dark box so lattices and open bays read as a room
    if interior:
        a, c = L / 2 - 0.35, D / 2 - 0.35
        if a > 0.5 and c > 0.5:
            prim.box(B, uc - a, vc - c, z0, uc + a, vc + c, zt, 'wall_board', faces='xXyY')
            if ceiling_dark: prim.box(B, uc - a - 0.4, vc - c - 0.4, zt - 0.3, uc + a + 0.4, vc + c + 0.4, zt - 0.25, 'wood_dark', faces='z')
    # veranda (縁) with railing (高欄) and the stairs
    if veranda:
        w, vsides = veranda
        a, c = L / 2, D / 2
        rects = {0: (uc - a - w, vc - c - w, uc + a + w, vc - c), 1: (uc + a, vc - c - w, uc + a + w, vc + c + w), 2: (uc - a - w, vc + c, uc + a + w, vc + c + w), 3: (uc - a - w, vc - c - w, uc - a, vc + c + w)}
        for k in vsides:
            x0, y0, x1, y1 = rects[k]
            prim.box(B, x0, y0, z0 - 0.17, x1, y1, z0 - 0.07, vmat, faces='ZxXyY')
        zg_ = zground if zground is not None else z0 - 1.0
        for k in vsides:
            x0, y0, x1, y1 = rects[k]
            n = max(2, int(round(max(x1 - x0, y1 - y0) / 1.8)))
            for t in np.linspace(0, 1, n + 1):
                px = x0 + (x1 - x0) * t if (x1 - x0) > (y1 - y0) else ((x0 if k == 3 else x1))
                py = y0 + (y1 - y0) * t if (y1 - y0) >= (x1 - x0) else ((y0 if k == 0 else y1))
                zb_ = zg_(px, py) if callable(zg_) else zg_
                prim.box(B, px - 0.08, py - 0.08, zb_ - 0.2, px + 0.08, py + 0.08, z0 - 0.17, mat if mat == 'vermilion' else 'wood_dark', tag='main')
        if rail:
            pts = {0: [(uc - a - w + 0.1, vc - c - w + 0.1), (uc + a + w - 0.1, vc - c - w + 0.1)], 1: [(uc + a + w - 0.1, vc - c - w + 0.1), (uc + a + w - 0.1, vc + c + w - 0.1)],
                   2: [(uc + a + w - 0.1, vc + c + w - 0.1), (uc - a - w + 0.1, vc + c + w - 0.1)], 3: [(uc - a - w + 0.1, vc + c + w - 0.1), (uc - a - w + 0.1, vc - c - w + 0.1)]}
            gaps = [(s_[0], s_[1], s_[2]) for s_ in (steps or [])]
            for k in rail:
                p0, p1 = [np.array(p) for p in pts[k]]
                segs = [(p0, p1)]
                for (side, cu, sw, *_rest) in gaps:
                    if {'front': 0, 'right': 1, 'back': 2, 'left': 3}[side] != k: continue
                    dd = K.unit(p1 - p0)
                    cpt = np.array([cu, p0[1]]) if k in (0, 2) else np.array([p0[0], cu])
                    tt = float((cpt - p0) @ dd)
                    segs = [(p0, p0 + dd * (tt - sw / 2 - 0.1)), (p0 + dd * (tt + sw / 2 + 0.1), p1)]
                for (q0, q1) in segs:
                    if np.linalg.norm(q1 - q0) < 0.3: continue
                    K.rail_line(B, [q0, q1], z0 - 0.07, h=0.8, mat=rail_mat, giboshi_at=(0, 1) if giboshi else (), cap_mat='bronze' if rail_mat == 'vermilion' else 'metal_dark', post_every=2.0, w=0.09)
    if steps:
        for (side, cu, sw, zb_) in steps:
            w0 = veranda[0] if veranda else 0.0
            if side == 'front':
                p1 = (cu, vs[0] - w0 + 0.02); run = max(0.6, (z0 - zb_) * 1.3); p0 = (cu, vs[0] - w0 - run)
            elif side == 'back':
                p1 = (cu, vs[-1] + w0 - 0.02); run = max(0.6, (z0 - zb_) * 1.3); p0 = (cu, vs[-1] + w0 + run)
            elif side == 'left':
                p1 = (us[0] - w0 + 0.02, cu); run = max(0.6, (z0 - zb_) * 1.3); p0 = (us[0] - w0 - run, cu)
            else:
                p1 = (us[-1] + w0 - 0.02, cu); run = max(0.6, (z0 - zb_) * 1.3); p0 = (us[-1] + w0 + run, cu)
            K.steps(B, p0, p1, zb_, z0 - 0.07, sw, 'stone' if mat != 'vermilion' else 'stone', riser=0.18, cheek=0.25)
    # brackets and roof
    if brackets:
        top, reach = arch.bracket_row(B, L, D, zt, brackets, bscale, bmat, bend, us=np.array(us) - uc, vs=np.array(vs) - vc, purlin=True) if (uc == 0 and vc == 0) else _brow(B, us, vs, zt, brackets, bscale, bmat, bend)
        K.soffit_ring(B, uc, vc, L / 2, D / 2, reach + 0.45, top - 0.3, bmat)
    else:
        top, reach = zt, 0.0
    out = dict(top=top, reach=reach, L=L, D=D, uc=uc, vc=vc)
    if roof is not None:
        rk = dict(roof)
        o = rk.pop('o', 2.0)
        lift = rk.pop('lift', 0.35)
        if uc != 0 or vc != 0:
            with Frame(B, uc, vc, 0.0, 0.0):
                out.update(K.mroof(B, L + 2 * reach, D + 2 * reach, top + lift, o, **rk))
        else:
            out.update(K.mroof(B, L + 2 * reach, D + 2 * reach, top + lift, o, **rk))
    return out

def _brow(B, us, vs, zt, kind, s, mat, end):
    uc = (us[0] + us[-1]) / 2; vc = (vs[0] + vs[-1]) / 2
    with Frame(B, uc, vc, 0.0, 0.0):
        return arch.bracket_row(B, us[-1] - us[0], vs[-1] - vs[0], zt, kind, s, mat, end, us=np.array(us) - uc, vs=np.array(vs) - vc, purlin=True)

def block_rect(B, us, vs, m=0.2):
    K.block_poly(B, [(us[0] - m, vs[0] - m), (us[-1] + m, vs[0] - m), (us[-1] + m, vs[-1] + m), (us[0] - m, vs[-1] + m)])

HIWADA = dict(cover='hiwada', rafter=0.24, rafter_mat='vermilion', rafter_end='white_paint', flash='copper', ends='oni', bargeboard_mat='vermilion')
TILE = dict(cover='hongawara', rafter=0.26, rafter_mat='vermilion', rafter_end='white_paint', ends='oni', bargeboard_mat='vermilion')

# ------------------------------------------------------------------ 仁王門 (楼門, 三間一戸, 入母屋 檜皮葺, ~1500, 14 m)
def niomon(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 102164608, 155.5)
    fr = (cx, cy, yaw); g = gfun(S, fr)
    zp = 104.5                      # stone platform top
    us = bays([3.2, 3.6, 3.2]); vs = bays([2.5, 2.5])
    with Frame(B, cx, cy, 0.0, yaw):
        # stone platform with a stone balustrade, wider than the gate
        pa, pc = 7.6, 4.6
        ring = [(-pa, -pc), (pa, -pc), (pa, pc), (-pa, pc)]
        zlow = min(float(g(*p)) for p in ring)
        arch.platform(B, ring, zlow - 0.6, zp, 'stone', walk=False)
        K.walk_poly(B, ring, zp)
        K.tamagaki(B, [(-1.6, -pc + 0.2), (-pa + 0.2, -pc + 0.2), (-pa + 0.2, pc - 0.2), (-1.6, pc - 0.2)], z=zp, h=0.85)
        K.tamagaki(B, [(1.6, -pc + 0.2), (pa - 0.2, -pc + 0.2), (pa - 0.2, pc - 0.2), (1.6, pc - 0.2)], z=zp, h=0.85)
        K.block_line(B, [(-1.6, -pc + 0.2), (-pa + 0.2, -pc + 0.2), (-pa + 0.2, pc - 0.2), (-1.6, pc - 0.2)])
        K.block_line(B, [(1.6, -pc + 0.2), (pa - 0.2, -pc + 0.2), (pa - 0.2, pc - 0.2), (1.6, pc - 0.2)])
        # lower storey: 12 pillars (main + 控柱), the side bays screened with 菱格子 where the 仁王 stand
        z1 = zp + 5.2
        for u in us:
            for v in vs:
                K.post(B, u, v, zp, z1, 0.3, 'vermilion', base='stone', base_h=0.15)
        for v in (vs[0], vs[-1]):
            K.beam(B, (us[0], v), (us[-1], v), z1, 0.24, 0.36, 'vermilion', ext=0.45)
            K.beam(B, (us[0], v), (us[-1], v), z1 - 1.2, 0.16, 0.24, 'vermilion', ext=0.2)
        for u in us:
            K.beam(B, (u, vs[0]), (u, vs[-1]), z1, 0.24, 0.36, 'vermilion', ext=0.45)
            K.beam(B, (u, vs[0]), (u, vs[-1]), z1 - 1.2, 0.16, 0.24, 'vermilion', ext=0.2)
        for (a, b) in ((us[0], us[1]), (us[2], us[3])):
            for v in (vs[0], vs[-1]):
                K.lattice(B, (a + 0.32, v), (b - 0.32, v), zp + 1.4, z1 - 1.35, mat='vermilion', step=0.3, bar=0.045, back='wall_board', diag=True, out=(0, -1 if v < 0 else 1))
                K.wall_panel(B, (a + 0.3, v), (b - 0.3, v), zp + 0.1, zp + 1.4, 'wood_dark', both=True)
                K.wall_panel(B, (a + 0.3, v), (b - 0.3, v), z1 - 1.1, z1 - 0.2, 'temple_wall', both=True, **K.PLASTER)
            K.wall_panel(B, (a + 0.1, 0.0), (b - 0.1, 0.0), zp, z1 - 0.2, 'wall_board', both=True)
        for v in (vs[0], vs[-1]):
            K.wall_panel(B, (us[1] + 0.3, v), (us[2] - 0.3, v), z1 - 1.1, z1 - 0.2, 'temple_wall', both=True, **K.PLASTER)
        for u in (us[0], us[-1]):
            K.wall_panel(B, (u, vs[0] + 0.3), (u, vs[-1] - 0.3), zp + 0.1, z1 - 0.2, 'temple_wall', both=True, **K.PLASTER)
        # 仁王 (金剛力士) figures in the side bays: simple dark-red bodies on plinths
        for u in ((us[0] + us[1]) / 2, (us[2] + us[3]) / 2):
            prim.box(B, u - 0.6, -1.6, zp, u + 0.6, -0.6, zp + 0.5, 'stone')
            prim.cyl(B, (u, -1.1, zp + 0.5), (u, -1.1, zp + 3.4), 0.42, 0.36, 10, 'vermilion', tag='detail')
            prim.lathe(B, (u, -1.1, zp + 3.4), [(0.18, 0), (0.24, 0.1), (0.22, 0.4), (0.0, 0.5)], 8, 'vermilion', tag='detail')
        # balcony brackets (三手先-like 出組) carrying the upper floor's 縁
        top1, reach1 = _brow(B, list(us), list(vs), z1, 'degumi', 0.9, 'vermilion', 'white_paint')
        K.soffit_ring(B, 0.0, 0.0, (us[-1] - us[0]) / 2, (vs[-1] - vs[0]) / 2, reach1 + 0.9, top1 + 0.12, 'vermilion')
        zf2 = top1 + 0.3
        L2, D2 = us[-1] - us[0], vs[-1] - vs[0]
        w = reach1 + 0.9
        prim.box(B, us[0] - w, vs[0] - w, zf2 - 0.14, us[-1] + w, vs[-1] + w, zf2, 'wood_dark', faces='ZxXyYz')
        K.rail_line(B, [(us[0] - w + 0.1, vs[0] - w + 0.1), (us[-1] + w - 0.1, vs[0] - w + 0.1), (us[-1] + w - 0.1, vs[-1] + w - 0.1), (us[0] - w + 0.1, vs[-1] + w - 0.1), (us[0] - w + 0.1, vs[0] - w + 0.1)],
                    zf2, h=0.75, mat='vermilion', giboshi_at=(0, 1, 2, 3), w=0.08)
        # upper storey: set in, 3 x 2 bays, white walls, green 連子窓, central doors
        us2 = bays([3.0, 3.4, 3.0]); vs2 = bays([2.2, 2.2])
        res = hall(B, list(us2), list(vs2), zf2, 3.0, mat='vermilion', r=0.22,
                   walls={'front': ['renji', 'karado', 'renji'], 'back': ['renji', 'karado', 'renji'], 'left': ['plaster', 'plaster'], 'right': ['plaster', 'plaster']},
                   brackets='mitesaki', bscale=0.62, roof=dict(o=2.6, kind='irimoya', pitch=0.9, teri=1.5, sori=0.75, sori_len=0.45, gable_frac=0.45, verge=0.75,
                                                             lift=0.45, prof=K.slope_profile(0.3, 1.25, 0.8, 0.22), **HIWADA), nageshi=True, interior=True)
        info['niomon_top'] = res.get('z_ridge')
        # blockers: the side bays (仁王 behind lattice)
        block_rect(B, [us[0], us[1]], list(vs)); block_rect(B, [us[2], us[3]], list(vs))
        # the stairs down to the plaza (339358818) and the komainu on their plinths
        za = float(g(0.0, -pc - 8.0))
        K.steps(B, (0.0, -pc - 7.8), (0.0, -pc), za, zp, 6.0, 'stone', riser=0.175, cheek=0.5, S=None, base=za - 1.0)
        for s_ in (-1, 1):
            komainu(B, s_ * 4.6, -pc - 9.5, za, 0 if s_ < 0 else math.pi)
            zl = float(g(s_ * 4.6, -pc - 4.0))
            arch.ishidoro(B, s_ * 4.6, -pc - 4.0, zl, h=2.6)
            B.lamp(s_ * 4.6, -pc - 4.0, zl + 1.7, 5.0)
    return fr

def komainu(B, x, y, z, yaw):
    """狛犬 on a stone plinth (simplified seated lion)"""
    prim.box(B, x - 0.9, y - 0.9, z - 0.3, x + 0.9, y + 0.9, z + 1.4, 'stone')
    prim.box(B, x - 0.75, y - 0.75, z + 1.4, x + 0.75, y + 0.75, z + 1.65, 'stone')
    prim.lathe(B, (x, y, z + 1.65), [(0.55, 0), (0.5, 0.5), (0.42, 1.1), (0.0, 1.25)], 8, 'stone', smooth=True)
    prim.rock(B, (x + 0.2 * math.cos(yaw), y + 0.2 * math.sin(yaw), z + 3.0), 0.45, int(abs(x * 10)) % 97, 'stone', flat=0.9)

# ------------------------------------------------------------------ 西門 (八脚門, 切妻 檜皮葺, 正面向拝, 背面軒唐破風, 1631)
def saimon(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 102164575, 160.7)
    fr = (cx, cy, yaw); g = gfun(S, fr)
    zp = 111.75
    us = bays([2.9, 3.4, 2.9]); vs = bays([2.3, 2.3])
    with Frame(B, cx, cy, 0.0, yaw):
        ring = K.rect(0, 0, 6.2, 4.4)
        arch.platform(B, ring, zp - 1.6, zp, 'stone', walk=False)
        K.walk_poly(B, ring, zp)
        zt = zp + 4.6
        for u in us:
            for v in vs:
                K.post(B, u, v, zp, zt, 0.27 if v == 0 else 0.22, 'vermilion', base='stone', base_h=0.2)
        for v in vs:
            K.beam(B, (us[0], v), (us[-1], v), zt, 0.22, 0.32, 'vermilion', ext=0.35)
            K.beam(B, (us[0], v), (us[-1], v), zt - 1.1, 0.14, 0.22, 'vermilion', ext=0.15)
        for u in us:
            K.beam(B, (u, vs[0]), (u, vs[-1]), zt, 0.22, 0.32, 'vermilion', ext=0.35)
        for (a, b) in ((us[0], us[1]), (us[2], us[3])):
            K.wall_panel(B, (a + 0.25, 0.0), (b - 0.25, 0.0), zp, zt - 1.2, 'temple_wall', both=True, **K.PLASTER)
            for v in vs:
                K.wall_panel(B, (a + 0.25, v), (b - 0.25, v), zt - 1.0, zt - 0.17, 'temple_wall', both=True, **K.PLASTER)
            K.lattice(B, (a + 0.25, -0.05), (b - 0.25, -0.05), zp + 1.2, zt - 1.3, mat='vermilion', step=0.28, bar=0.04, back=None, diag=True, out=(0, -1))
        for u in (us[0], us[-1]):
            K.wall_panel(B, (u, vs[0] + 0.25), (u, vs[-1] - 0.25), zp + 0.3, zt - 0.17, 'temple_wall', both=True, **K.PLASTER)
        top, reach = _brow(B, list(us), list(vs), zt, 'demitsudo', 0.85, 'vermilion', 'white_paint')
        K.soffit_ring(B, 0.0, 0.0, (us[-1] - us[0]) / 2, (vs[-1] - vs[0]) / 2, reach + 0.4, top - 0.3, 'vermilion')
        K.mroof(B, us[-1] - us[0] + 2 * reach, vs[-1] - vs[0] + 2 * reach, top + 0.35, 1.9, kind='kirizuma', pitch=0.6, teri=1.5, verge=1.1,
                prof=K.slope_profile(0.35, 1.2, 0.85, 0.2), gable_wall='wall_board', **HIWADA)
        for u in (us[0], us[-1]):                               # 虹梁 + 束 on the gable ends
            K.beam(B, (u - 0.05, vs[0] - reach), (u - 0.05, vs[-1] + reach), top + 0.1, 0.2, 0.32, 'vermilion')
            for v in (-1.0, 1.0):
                prim.box(B, u - 0.12, v - 0.1, top + 0.1, u + 0.02, v + 0.1, top + 1.0, 'vermilion')
        # 向拝 (front porch): two posts and a lean-to roof
        for u in (us[1], us[2]):
            K.post(B, u, vs[0] - 2.4, zp, zt - 0.7, 0.18, 'vermilion', base='stone', base_h=0.2)
        K.beam(B, (us[1], vs[0] - 2.4), (us[2], vs[0] - 2.4), zt - 0.7, 0.18, 0.28, 'vermilion', ext=0.5)
        for u in (us[1], us[2]):
            K.beam(B, (u, vs[0] - 2.4), (u, vs[0]), zt - 0.5, 0.15, 0.24, 'vermilion')
        with Frame(B, 0.0, vs[0] - 1.2, 0.0, 0.0):
            K.mroof(B, us[2] - us[1] + 0.6, 2.4, zt - 0.2, 1.0, kind='kirizuma', pitch=0.5, teri=1.4, verge=0.5, **HIWADA)
        # 軒唐破風 on the back: a curved gable on the back eave
        karahafu(B, 0.0, vs[-1] + reach + 1.6, top + 0.1, 4.2, 1.3, 'hiwada', 'vermilion')
    # the black fence of the terrace (OSM fences) is drawn in the ground module
    return fr

def karahafu(B, u, v, z, w, h, cover='hiwada', mat='vermilion'):
    """唐破風: a cusped curved gable (bargeboard + covering) facing -v, centred at (u, v), base height z"""
    xs = np.linspace(-w / 2, w / 2, 25)
    def prof(x):
        t = abs(x) / (w / 2)
        return h * (1 - t) ** 1.6 * (1 - 0.35 * np.cos(math.pi * min(1.0, abs(x) / (w * 0.18))) * 0) + h * 0.18 * math.exp(-((x / (w * 0.12)) ** 2))
    pts = np.array([(u + x, v, z + prof(x)) for x in xs])
    prim.sweep(B, pts, [(-0.07, -0.45), (0.07, -0.45), (0.07, 0.0), (-0.07, 0.0)], mat, up=(0, -1, 0), tag='main')
    back = pts + [0, 1.6, 0.25]
    P = np.concatenate([pts + [0, -0.05, 0.02], back]); n = len(pts); I = []
    for i in range(n - 1): I += [[i, i + 1, i + n + 1], [i, i + n + 1, i + n]]
    B.add(P, I, cover, tag='main'); B.add(P, [t[::-1] for t in I], cover, tag='main')

# ------------------------------------------------------------------ 三重塔 / 子安塔
def pagoda(B, x, y, zg, yaw, base_w, heights, spans, body_w, cover='hongawara', sorin=8.8, platform=1.0, rail_ground=True, scale=1.0, door_side=0, bk='mitesaki'):
    """a three-storey pagoda (三間三重塔婆): first storey body base_w; per storey body widths body_w[k], storey heights
    heights[k] (floor to wall plate), roof spans spans[k] (eave edge, square).  三手先 brackets, balconies (高欄) on the
    upper storeys, 相輪 of `sorin` m on the top roof."""
    out = {}
    with Frame(B, x, y, 0.0, yaw):
        # stone platform (基壇) with steps
        a = spans[0] / 2 - 0.6
        arch.platform(B, K.rect(0, 0, a, a), zg - 0.8, zg + platform, 'stone', walk=False)
        K.walk_poly(B, K.rect(0, 0, a, a), zg + platform)
        z = zg + platform + 0.45
        # 縁 around the first storey
        w0 = body_w[0]
        prim.box(B, -w0 / 2 - 1.1, -w0 / 2 - 1.1, z - 0.15, w0 / 2 + 1.1, w0 / 2 + 1.1, z, 'wood_natural', faces='ZxXyY')
        K.rail_line(B, [(-w0 / 2 - 1.0, -w0 / 2 - 1.0), (w0 / 2 + 1.0, -w0 / 2 - 1.0), (w0 / 2 + 1.0, w0 / 2 + 1.0), (-w0 / 2 - 1.0, w0 / 2 + 1.0), (-w0 / 2 - 1.0, -w0 / 2 - 1.0)],
                    z, h=0.7, mat='vermilion', giboshi_at=(0, 1, 2, 3), w=0.08)
        for k in range(3):
            bw = body_w[k]; H = heights[k]
            us = bays([bw * 0.3, bw * 0.4, bw * 0.3])
            walls = {s: ['renji', 'karado', 'renji'] for s in ('front', 'back', 'left', 'right')}
            res = hall(B, list(us), list(us), z, H, mat='vermilion', r=0.17 * scale + 0.05, walls=walls, brackets=bk, bscale=0.62 * scale + 0.1,
                       roof=None, interior=True, nageshi=True, post_base='stone' if k == 0 else None)
            top, reach = res['top'], res['reach']
            span = spans[k]
            o = span / 2 - bw / 2 - reach
            Lr = bw + 2 * reach
            if k < 2:
                nb = body_w[k + 1]
                kw = dict(TILE if cover == 'hongawara' else HIWADA); kw['rafter'] = 0.2 * scale + 0.05
                rr = K.MRoof(Lr, Lr, top + 0.3, o, kind='hogyo', pitch=0.42, teri=1.6, sori=0.55 * scale + 0.1, sori_len=0.5, truncate=(span / 2 - nb / 2 - 0.35), tiers=2,
                             prof=K.slope_profile(0.25, 1.1, 0.8, 0.3), **kw)
                rr.build(B)
                zz = float(rr.z(span / 2 - nb / 2 - 0.35, span / 2))
                # balcony on the next storey: 縁 + 高欄 on the roof's top
                z = zz + 0.55
                prim.box(B, -nb / 2 - 0.9, -nb / 2 - 0.9, z - 0.35, nb / 2 + 0.9, nb / 2 + 0.9, z, 'vermilion', faces='ZxXyY')
                K.rail_line(B, [(-nb / 2 - 0.8, -nb / 2 - 0.8), (nb / 2 + 0.8, -nb / 2 - 0.8), (nb / 2 + 0.8, nb / 2 + 0.8), (-nb / 2 - 0.8, nb / 2 + 0.8), (-nb / 2 - 0.8, -nb / 2 - 0.8)],
                            z, h=0.6, mat='vermilion', giboshi_at=(0, 1, 2, 3), w=0.07)
            else:
                kw = dict(TILE if cover == 'hongawara' else HIWADA); kw['rafter'] = 0.2 * scale + 0.05
                rr = K.MRoof(Lr, Lr, top + 0.3, o, kind='hogyo', pitch=0.5, teri=1.6, sori=0.6 * scale + 0.1, sori_len=0.5, tiers=2,
                             prof=K.slope_profile(0.25, 1.1, 0.8, 0.3), top=[(0.01, 0.0)], **kw)
                res2 = rr.build(B)
                zr = res2['z_ridge']
                sorin_(B, zr - 0.2, sorin, scale)
                out['top'] = zr - 0.2 + sorin
    return out

def sorin_(B, z, h, s=1.0):
    """相輪: 露盤, 伏鉢, 請花, 九輪, 水煙, 竜車, 宝珠"""
    prim.box(B, -0.9 * s, -0.9 * s, z, 0.9 * s, 0.9 * s, z + 0.6 * s, 'copper')
    prim.box(B, -1.0 * s, -1.0 * s, z + 0.5 * s, 1.0 * s, 1.0 * s, z + 0.65 * s, 'copper')
    k = h / 8.8
    prim.lathe(B, (0, 0, z + 0.65 * s), [(0.6 * s, 0), (0.62 * s, 0.25 * k), (0.45 * s, 0.6 * k), (0.12 * s, 0.7 * k), (0.4 * s, 0.85 * k), (0.12 * s, 1.0 * k)], 12, 'bronze')
    zc = z + 0.65 * s + 1.0 * k
    prim.cyl(B, (0, 0, zc), (0, 0, z + h - 0.3 * k), 0.08 * s, 0.06 * s, 8, 'bronze')
    for i in range(9):
        zi = zc + 0.25 * k + i * 0.52 * k
        prim.lathe(B, (0, 0, zi), [(0.1 * s, 0), (0.42 * s * (1 - i * 0.02), 0.05 * k), (0.42 * s * (1 - i * 0.02), 0.14 * k), (0.1 * s, 0.19 * k)], 12, 'bronze', tag='detail' if i % 2 else 'main')
    zs = zc + 0.25 * k + 9 * 0.52 * k
    for a in range(4):                                  # 水煙: four flame panels
        ang = a * math.pi / 2 + math.pi / 4
        d = np.array([math.cos(ang), math.sin(ang), 0.0])
        P = np.array([[0, 0, zs], d * 0.55 * s + [0, 0, zs + 0.3 * k], d * 0.5 * s + [0, 0, zs + 1.2 * k], [0, 0, zs + 1.45 * k]])
        B.add(P, [[0, 1, 2], [0, 2, 3]], 'bronze', tag='main'); B.add(P, [[0, 2, 1], [0, 3, 2]], 'bronze', tag='main')
    prim.lathe(B, (0, 0, zs + 1.45 * k), [(0.1 * s, 0), (0.22 * s, 0.1 * k), (0.1 * s, 0.25 * k), (0.2 * s, 0.4 * k), (0.15 * s, 0.6 * k), (0.0, 0.8 * k)], 10, 'bronze')

def sanjunoto(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 102164638, 160.7)
    zg = 112.0
    out = pagoda(B, cx, cy, zg, yaw, 5.6, [3.7, 3.2, 3.0], [12.6, 12.0, 11.6], [5.6, 5.0, 4.5], cover='hongawara', sorin=9.4, platform=1.0)
    info['pagoda_top'] = out.get('top')
    with Frame(B, cx, cy, 0.0, yaw):
        K.steps(B, (0.0, -9.0), (0.0, -5.7), zg - 0.1, zg + 1.0, 2.4, 'stone', cheek=0.3)

def koyasuto(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 333894528, 86.1)
    zg = float(S.ground(cx, cy)) + 0.2
    out = pagoda(B, cx, cy, zg, yaw, 3.0, [2.2, 1.8, 1.7], [6.6, 6.2, 5.9], [3.0, 2.6, 2.3], cover='hiwada', sorin=4.2, platform=0.7, scale=0.55, bk='degumi')
    info['koyasu_top'] = out.get('top')
    with Frame(B, cx, cy, 0.0, yaw):
        fence = [(-5.5, -5.5), (5.5, -5.5), (5.5, 5.5), (-5.5, 5.5), (-5.5, -5.5)]
        arch.platform(B, K.rect(0, 0, 5.8, 5.8), zg - 1.2, zg - 0.05, 'stone', walk=True)
        K.rail_line(B, fence[:2], zg - 0.05, h=1.0, mat='wood_dark', post_every=1.6)
        K.rail_line(B, fence[1:], zg - 0.05, h=1.0, mat='wood_dark', post_every=1.6)
        K.block_line(B, K.rect(0, 0, 3.4, 3.4) + [K.rect(0, 0, 3.4, 3.4)[0]])

# ------------------------------------------------------------------ 鐘楼 (桁行1間 梁間2間, 切妻 本瓦葺, 1607)
def shoro(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 102164614, 155.2 + 90)
    zg = 109.8
    us = [-2.4, 2.4]; vs = [-1.7, 0.0, 1.7]
    with Frame(B, cx, cy, 0.0, yaw):
        arch.platform(B, K.rect(0, 0, 4.2, 3.5), zg - 0.6, zg + 0.35, 'stone', walk=True)
        zt = zg + 0.35 + 4.4
        for u in us:
            for v in vs:
                prim.cyl(B, (u * 1.06, v * 1.06, zg + 0.35), (u, v, zt), 0.25, 0.21, 12, 'vermilion')
        for v in vs:
            K.beam(B, (us[0], v), (us[1], v), zt, 0.22, 0.32, 'vermilion', ext=0.45)
            K.beam(B, (us[0], v), (us[1], v), zg + 0.9, 0.16, 0.24, 'vermilion', ext=0.3)      # 地貫
            K.beam(B, (us[0], v), (us[1], v), zt - 1.3, 0.16, 0.24, 'vermilion', ext=0.3)
        for u in us:
            K.beam(B, (u, vs[0]), (u, vs[-1]), zt, 0.22, 0.32, 'vermilion', ext=0.45)
            K.beam(B, (u, vs[0]), (u, vs[-1]), zg + 0.9, 0.16, 0.24, 'vermilion', ext=0.3)
        top, reach = _brow(B, us, vs, zt, 'demitsudo', 0.8, 'vermilion', 'white_paint')
        K.soffit_ring(B, 0.0, 0.0, 2.4, 1.7, reach + 0.4, top - 0.3, 'vermilion')
        K.mroof(B, 4.8 + 2 * reach, 3.4 + 2 * reach, top + 0.3, 1.5, kind='kirizuma', pitch=0.75, teri=1.5, verge=1.0, **TILE)
        # the bell
        prim.cyl(B, (0, 0, zt - 0.2), (0, 0, zt + 0.5), 0.04, 0.04, 6, 'metal_dark', tag='detail')
        prim.lathe(B, (0, 0, zt - 2.1), [(0.0, 0.0), (0.72, 0.0), (0.7, 0.2), (0.62, 0.9), (0.6, 1.6), (0.45, 1.85), (0.1, 1.95), (0.0, 1.95)], 16, 'bronze')
        K.block_line(B, [(-2.4, -1.7), (2.4, -1.7), (2.4, 1.7), (-2.4, 1.7), (-2.4, -1.7)], w=0.6)

# ------------------------------------------------------------------ 随求堂 (1735; 入母屋 本瓦葺 with a lower skirt roof, white walls, dark timber)
def zuigudo(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 102164570, -99.8)
    zg = 110.1
    z0 = zg + 0.9
    us = bays([3.0, 3.0, 3.4, 3.0, 3.0]); vs = bays([3.0, 3.2, 3.2, 3.0])
    with Frame(B, cx, cy, 0.0, yaw):
        res = hall(B, list(us), list(vs), z0, 4.2, mat='wood_dark', r=0.21,
                   walls={'front': ['open', 'open', 'open', 'open', 'open'], 'back': ['board'] * 5, 'left': ['plaster'] * 4, 'right': ['plaster'] * 4},
                   upper='plaster', brackets='funa', bscale=0.9, roof=None, base=(zg - 0.6, 0.6), steps=[('front', 0.0, 5.0, zg - 0.05)])
        # lower skirt roof (hip, tiles) + the upper 入母屋 over the inner core
        K.mroof(B, us[-1] - us[0] + 0.6, vs[-1] - vs[0] + 0.6, z0 + 4.55, 1.9, kind='yosemune', cover='hongawara', pitch=0.42, teri=1.3, sori=0.35,
                rafter=0.3, rafter_mat='wood_dark', rafter_end='white_paint', ends='oni', truncate=3.3, tiers=1)
        u2 = bays([3.4, 3.4, 3.4]); v2 = bays([3.2, 3.2])
        for u in u2:
            for v in v2:
                if u in (u2[0], u2[-1]) or v in (v2[0], v2[-1]):
                    K.post(B, u, v, z0 + 4.2, z0 + 6.6, 0.2, 'wood_dark', base=None)
        for a, b in zip(K.rect(0, 0, u2[-1], v2[-1]), K.rect(0, 0, u2[-1], v2[-1])[1:] + [K.rect(0, 0, u2[-1], v2[-1])[0]]):
            K.wall_panel(B, a, b, z0 + 4.6, z0 + 6.5, 'temple_wall', both=True, **K.PLASTER)
            K.beam(B, a, b, z0 + 6.6, 0.18, 0.26, 'wood_dark', ext=0.3)
        K.lattice(B, (-1.6, v2[0] - 0.02), (1.6, v2[0] - 0.02), z0 + 5.0, z0 + 6.2, mat='wood_dark', step=0.15, back='wall_board', out=(0, -1))
        K.mroof(B, u2[-1] - u2[0] + 0.6, v2[-1] - v2[0] + 0.6, z0 + 7.0, 1.6, kind='irimoya', cover='hongawara', pitch=0.78, teri=1.5, sori=0.4, gable_frac=0.5, verge=0.7,
                rafter=0.3, rafter_mat='wood_dark', rafter_end='white_paint', ends='oni', gable_wall='temple_wall')
        karahafu(B, 0.0, vs[0] - 2.2, z0 + 4.0, 4.4, 1.2, 'hongawara', 'wood_dark')
        block_rect(B, list(us), list(vs))

# ------------------------------------------------------------------ 経堂 / 田村堂 / 朝倉堂
def kyodo(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 102164586, -107.6)
    zg = 113.3
    z0 = zg + 1.0
    us = bays([2.9, 2.9, 3.2, 2.9, 2.9]); vs = bays([2.8, 2.9, 2.9, 2.8])
    with Frame(B, cx, cy, 0.0, yaw):
        hall(B, list(us), list(vs), z0, 4.2, mat='vermilion', r=0.22,
             walls={'front': ['shitomi', 'shitomi', 'karado', 'shitomi', 'shitomi'], 'back': ['plaster'] * 5, 'left': ['shitomi', 'plaster', 'plaster', 'shitomi'], 'right': ['shitomi', 'plaster', 'plaster', 'shitomi']},
             brackets='demitsudo', bscale=0.85, base=(zg - 0.8, 0.9), steps=[('front', 0.0, 3.0, zg + 0.05)],
             roof=dict(o=2.3, kind='irimoya', pitch=0.82, teri=1.5, sori=0.6, gable_frac=0.45, verge=0.8, gable_wall='temple_wall', prof=K.slope_profile(0.3, 1.2, 0.85, 0.22), **TILE))
        block_rect(B, list(us), list(vs), 0.9)

def tamurado(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 102164632, -106.6)
    zg = 113.9
    z0 = zg + 1.5
    us = bays([2.6, 3.0, 2.6]); vs = bays([2.6, 2.8, 2.6])
    with Frame(B, cx, cy, 0.0, yaw):
        hall(B, list(us), list(vs), z0, 3.9, mat='vermilion', r=0.21,
             walls={'front': ['shitomi', 'shitomi', 'shitomi'], 'back': ['plaster'] * 3, 'left': ['plaster'] * 3, 'right': ['plaster'] * 3},
             brackets='demitsudo', bscale=0.85, veranda=(1.2, (0, 1, 3)), rail=(0, 1, 3), steps=[('front', 0.0, 2.6, zg + 0.05)], zground=zg,
             base=(zg - 0.6, 0.4),
             roof=dict(o=2.2, kind='irimoya', pitch=0.88, teri=1.5, sori=0.6, gable_frac=0.45, verge=0.75, gable_wall='temple_wall', prof=K.slope_profile(0.3, 1.25, 0.85, 0.22), **HIWADA))
        block_rect(B, list(us), list(vs), 1.3)

def asakurado(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 102164640, -86.2)
    zg = 115.1
    z0 = zg + 1.3
    us = bays([2.8, 2.9, 3.1, 2.9, 2.8]); vs = bays([2.9, 3.1, 2.9])
    with Frame(B, cx, cy, 0.0, yaw):
        hall(B, list(us), list(vs), z0, 4.1, mat='wood_dark', r=0.22,
             walls={'front': ['board', 'shitomi', 'door', 'shitomi', 'board'], 'back': ['board'] * 5, 'left': ['board', 'shitomi', 'board'], 'right': ['board', 'shitomi', 'board']},
             upper='plaster', brackets='demitsudo', bscale=0.85, bend='white_paint', veranda=(1.1, (0, 1, 2, 3)), rail=(0, 1, 3), rail_mat='wood_dark', giboshi=True,
             steps=[('right', 0.0, 2.2, zg + 0.05)], zground=zg, base=(zg - 0.5, 0.3),
             roof=dict(o=2.3, kind='irimoya', pitch=0.82, teri=1.5, sori=0.55, gable_frac=0.45, verge=0.8, gable_wall='wall_board', prof=K.slope_profile(0.3, 1.2, 0.85, 0.22),
                       cover='hongawara', rafter=0.26, rafter_mat='wood_dark', rafter_end='white_paint', ends='oni', bargeboard_mat='wood_dark'))
        block_rect(B, list(us), list(vs), 1.2)

# ------------------------------------------------------------------ 轟門 (八脚門, 切妻 本瓦葺, dark timber) + 回廊 to the 本堂
def todorokimon(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 102164595, 185.1)
    zp = 114.85
    us = bays([2.6, 3.2, 2.6]); vs = bays([2.1, 2.1])
    with Frame(B, cx, cy, 0.0, yaw):
        ring = K.rect(0, 0, 5.2, 3.6)
        arch.platform(B, ring, zp - 1.0, zp, 'stone', walk=False)
        K.walk_poly(B, ring, zp)
        zt = zp + 4.5
        for u in us:
            for v in vs:
                K.post(B, u, v, zp, zt, 0.26 if v == 0 else 0.21, 'wood_dark', base='stone', base_h=0.2)
        for v in vs:
            K.beam(B, (us[0], v), (us[-1], v), zt, 0.22, 0.32, 'wood_dark', ext=0.35)
            K.beam(B, (us[0], v), (us[-1], v), zt - 1.2, 0.14, 0.22, 'wood_dark', ext=0.15)
        for u in us:
            K.beam(B, (u, vs[0]), (u, vs[-1]), zt, 0.22, 0.32, 'wood_dark', ext=0.35)
        for (a, b) in ((us[0], us[1]), (us[2], us[3])):
            for v in vs:
                K.lattice(B, (a + 0.25, v), (b - 0.25, v), zp + 1.2, zt - 1.3, mat='wood_dark', step=0.26, bar=0.04, back=None, diag=True, out=(0, -1 if v < 0 else 1))
                K.wall_panel(B, (a + 0.25, v), (b - 0.25, v), zp, zp + 1.2, 'wood_dark', both=True)
                K.wall_panel(B, (a + 0.25, v), (b - 0.25, v), zt - 1.1, zt - 0.17, 'wall_board', both=True)
            K.wall_panel(B, (a + 0.2, 0.0), (b - 0.2, 0.0), zp, zt - 1.25, 'wall_board', both=True)
            # 持国天 / 広目天 figures
            u = (a + b) / 2
            prim.cyl(B, (u, -1.0, zp), (u, -1.0, zp + 2.6), 0.35, 0.3, 8, 'bronze', tag='detail')
        top, reach = _brow(B, list(us), list(vs), zt, 'demitsudo', 0.8, 'wood_dark', 'wood_dark')
        K.soffit_ring(B, 0.0, 0.0, (us[-1] - us[0]) / 2, (vs[-1] - vs[0]) / 2, reach + 0.4, top - 0.3, 'wood_dark')
        K.mroof(B, us[-1] - us[0] + 2 * reach, vs[-1] - vs[0] + 2 * reach, top + 0.3, 1.7, kind='kirizuma', cover='hongawara', pitch=0.72, teri=1.5, verge=1.0,
                rafter=0.26, rafter_mat='wood_dark', rafter_end='wood_dark', ends='oni', bargeboard_mat='wood_dark')
        # the plaque 「轟門」
        prim.box(B, -0.8, vs[0] - 0.08, zt - 0.95, 0.8, vs[0] - 0.02, zt - 0.3, 'black_lacquer', tag='detail')
        block_rect(B, [us[0], us[1]], list(vs), 0.05); block_rect(B, [us[2], us[3]], list(vs), 0.05)
    return (cx, cy, yaw)

def kairo(B, S, info, hframe):
    """回廊: the roofed corridor from the 轟門 to the 本堂's west porch (OSM w102164617), stone-paved floor, tiled roof"""
    ox, oy, hy = hframe
    c, s = math.cos(hy), math.sin(hy)
    zf = 114.95
    # in the hall frame: from U = -40.5 (east of the 轟門) to U = -23.4 (the porch)
    with Frame(B, ox, oy, 0.0, hy):
        u0, u1 = -40.2, -23.6
        vs = (-2.0, 2.0)
        us = np.linspace(u0, u1, 7)
        zt = zf + 3.0
        for u in us:
            for v in vs:
                K.post(B, u, v, zf, zt, 0.17, 'wood_dark', base='stone', base_h=0.15)
        for v in vs:
            K.beam(B, (u0, v), (u1, v), zt, 0.18, 0.26, 'wood_dark', ext=0.3)
        for u in us:
            K.beam(B, (u, vs[0]), (u, vs[1]), zt + 0.1, 0.16, 0.24, 'wood_dark', ext=0.4)
            prim.lathe(B, (u, 0.0, zt - 0.95), [(0.0, 0.0), (0.14, 0.05), (0.17, 0.3), (0.22, 0.34), (0.1, 0.48), (0.0, 0.5)], 6, 'bronze', tag='detail')   # 釣灯籠
            B.lamp(u, 0.0, zt - 0.7, 5.0)
        prim.box(B, u0 - 0.6, -2.6, zf - 0.3, u1 + 0.2, 2.6, zf, 'stone', faces='ZyY')
        with Frame(B, (u0 + u1) / 2, 0.0, 0.0, 0.0):
            K.mroof(B, u1 - u0 + 1.0, 4.0, zt + 0.55, 1.25, kind='kirizuma', cover='hongawara', pitch=0.55, teri=1.4, verge=0.6, rafter=0.3, rafter_mat='wood_dark',
                    rafter_end='wood_dark', ends='oni', bargeboard_mat='wood_dark')
            prim.box(B, -(u1 - u0) / 2 - 0.5, -2.5, zt + 0.45, (u1 - u0) / 2 + 0.5, 2.5, zt + 0.5, 'wood_dark', faces='z')
        K.walk_poly(B, [(u0 - 0.6, -2.4), (u1 + 0.2, -2.4), (u1 + 0.2, 2.4), (u0 - 0.6, 2.4)], zf)
        # steps up into the porch (floor 115.6)
        K.steps(B, (u1 - 0.1, 0.0), (u1 + 1.2, 0.0), zf, 115.48, 3.0, 'stone', riser=0.16)
        # the south side faces the valley: a low wooden railing between the posts, the terrace edge a 石垣 with a stone
        # balustrade further out (honden-stage__..._22_9346)
        K.rail_line(B, [(u0, -2.0), (u1, -2.0)], zf, h=0.8, mat='wood_dark', post_every=2.75)
        K.block_line(B, [(u0, -2.1), (u1, -2.1)])
        gl = lambda U, v: float(S.ground(ox + U * c - v * s, oy + U * s + v * c))
        edge = [(U, -4.2) for U in np.linspace(-46.0, -24.2, 9)]
        prim.box(B, -46.0, -4.2, zf - 0.32, u0 - 0.6, -2.6, zf - 0.02, 'stone', faces='Z')
        K.walk_poly(B, [(-46.0, -4.1), (u1 + 0.2, -4.1), (u1 + 0.2, -2.4), (-46.0, -2.4)], zf - 0.02)
        K.ishigaki(B, edge, zf - 0.05, lambda x, y: gl(x, y - 2.5) - 0.2, batter=0.3, cap=False)
        K.tamagaki(B, [(-46.0, -3.95), (u1 + 0.1, -3.95)], z=zf - 0.02, h=0.85)
        K.block_line(B, [(-46.0, -3.95), (u1 + 0.1, -3.95)])

# ------------------------------------------------------------------ 釈迦堂 / 阿弥陀堂 / 奥の院 (+ 舞台) along the cliff, facing west
def shakado(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 102164574, 178.3)
    zg = 116.2; z0 = zg + 0.8
    us = bays([2.9, 3.2, 2.9]); vs = bays([2.9, 3.0, 2.9, 1.8])
    with Frame(B, cx, cy, 0.0, yaw):
        hall(B, list(us), list(vs), z0, 3.8, mat='wood_dark', r=0.2,
             walls={'front': ['koshi', 'koshi', 'koshi'], 'back': ['board'] * 3, 'left': ['plaster'] * 4, 'right': ['plaster'] * 4},
             upper='plaster', brackets='funa', bscale=0.9, base=(zg - 0.6, 0.35),
             roof=dict(o=2.0, kind='yosemune', cover='hiwada', pitch=0.72, teri=1.6, sori=0.5, rafter=0.26, rafter_mat='wood_dark', rafter_end='wood_dark', flash='copper',
                       ends='oni', prof=K.slope_profile(0.3, 1.25, 0.8, 0.22)))
        block_rect(B, list(us), list(vs), 0.6)

def amidado(B, S, info):
    cx, cy, yaw, Lf, Dd = bframe(S, 102164636, 177.1)
    zg = 116.1; z0 = zg + 0.7
    us = bays([3.2, 3.6, 3.2]); vs = bays([3.0, 3.3, 3.0, 2.4])
    with Frame(B, cx, cy, 0.0, yaw):
        hall(B, list(us), list(vs), z0, 4.2, mat='vermilion', r=0.22,
             walls={'front': ['open', 'open', 'open'], 'back': ['plaster'] * 3, 'left': ['open', 'shitomi', 'plaster', 'plaster'], 'right': ['open', 'plaster', 'plaster', 'plaster']},
             brackets='demitsudo', bscale=0.85, base=(zg - 0.5, 0.3),
             roof=dict(o=2.2, kind='irimoya', pitch=0.85, teri=1.5, sori=0.55, gable_frac=0.45, verge=0.8, gable_wall='temple_wall', prof=K.slope_profile(0.3, 1.2, 0.85, 0.22),
                       cover='sangawara', rafter=0.26, rafter_mat='vermilion', rafter_end='white_paint', ends='oni', bargeboard_mat='vermilion'))
        # the front aisle (old 外陣) is the passage to the 奥の院: walkable, the rest blocked
        K.walk_poly(B, [(us[0] - 0.2, vs[0] - 0.4), (us[-1] + 0.2, vs[0] - 0.4), (us[-1] + 0.2, vs[1]), (us[0] - 0.2, vs[1])], z0)
        K.block_poly(B, [(us[0] - 0.3, vs[1] + 0.3), (us[-1] + 0.3, vs[1] + 0.3), (us[-1] + 0.3, vs[-1] + 0.3), (us[0] - 0.3, vs[-1] + 0.3)])
        K.steps(B, (0.0, vs[0] - 1.6), (0.0, vs[0] - 0.35), zg, z0, 3.0, 'stone', riser=0.17)

def okunoin(B, S, info):
    """奥の院 (懸造, 5 x 5 bays, 寄棟 檜皮葺, 1633): dark timber with vermilion eaves / brackets; its own stage (舞台) to the
    west on posts over the slope (the classic view of the 本堂 stage is from here)"""
    cx, cy, yaw, Lf, Dd = bframe(S, 102164641, 176.6)
    fr = (cx, cy, yaw); g = gfun(S, fr)
    z0 = 116.6
    us = bays([2.9, 3.0, 3.2, 3.0, 2.9]); vs = bays([2.6, 2.8, 2.8, 2.8, 2.6])
    with Frame(B, cx, cy, 0.0, yaw):
        H = 4.4
        hall(B, list(us), list(vs), z0, H, mat='wood_dark', r=0.25,
             walls={'front': ['open', 'open', 'open', 'open', 'open'], 'back': ['board'] * 5, 'left': ['open', 'board', 'board', 'shitomi', 'board'],
                    'right': ['open', 'board', 'board', 'board', 'board']},
             upper='plaster', brackets=None, interior=False)
        # the inner sanctuary walls (front aisle open), vermilion upper beams and colourful bracket sets
        prim.box(B, us[0] + 0.3, vs[1], z0, us[-1] - 0.3, vs[-1] - 0.3, z0 + H, 'wall_board', faces='xXyY')
        for a, b in zip(us[1:-2], us[2:-1]):
            arch.infill(B, (a, vs[1]), (b, vs[1]), z0 + 0.3, z0 + H - 1.1, 'karado', out=(0, -1), mat='wood_dark')
        ring = K.rect(0, 0, us[-1], vs[-1])
        for a, b in zip(ring, ring[1:] + ring[:1]):
            K.beam(B, a, b, z0 + H - 0.05, 0.24, 0.34, 'vermilion', ext=0.35)
            K.beam(B, a, b, z0 + H - 0.95, 0.2, 0.3, 'vermilion', ext=0.25)
        top, reach = arch.bracket_row(B, us[-1] - us[0], vs[-1] - vs[0], z0 + H, 'degumi', 0.95, 'vermilion', 'white_paint', us=np.array(us), vs=np.array(vs), purlin=True)
        K.soffit_ring(B, 0.0, 0.0, us[-1], vs[-1], reach + 0.45, top - 0.3, 'vermilion')
        K.mroof(B, us[-1] - us[0] + 2 * reach, vs[-1] - vs[0] + 2 * reach, top + 0.35, 2.6, kind='yosemune', cover='hiwada', pitch=0.78, teri=1.6, sori=0.65,
                rafter=0.22, rafter_mat='vermilion', rafter_end='gold', flash='copper', ends='oni', tiers=2, prof=K.slope_profile(0.28, 1.3, 0.75, 0.2))
        prim.box(B, us[0] - 0.4, vs[0] - 0.4, z0 + H + 0.25, us[-1] + 0.4, vs[1], z0 + H + 0.3, 'wood_dark', faces='z')
        # floor deck around (縁) and the 舞台 to the west / front (-v) projecting over the slope on posts
        w = 1.4
        prim.box(B, us[0] - w, vs[0] - w, z0 - 0.12, us[-1] + w, vs[-1] + w, z0, 'wood_natural', faces='ZxXyY')
        st0, st1 = vs[0] - 6.2, vs[0] - w
        sx0, sx1 = us[0] - 1.0, us[-1] + 1.0
        for v in np.arange(st0, st1 - 0.01, 0.42):
            prim.box(B, sx0, v + 0.005, z0 - 0.12, sx1, min(st1, v + 0.42) - 0.005, z0, 'wood_natural', faces='ZyY')
        # stage posts and 貫 down to the slope
        pu = np.linspace(sx0 + 0.3, sx1 - 0.3, 6); pv = [st0 + 0.5, (st0 + st1) / 2, st1 + 0.3]
        posts = {}
        for u in pu:
            for v in pv:
                zg_ = float(g(u, v))
                if zg_ > z0 - 0.8: continue
                K.post(B, u, v, zg_, z0 - 0.5, 0.24, 'wood_dark', base='stone', base_h=0.2)
                posts[(u, v)] = zg_
        for v in pv:
            K.beam(B, (sx0, v), (sx1, v), z0 - 0.12, 0.26, 0.38, 'wood_dark')
        for u in pu:
            K.beam(B, (u, st0), (u, vs[0]), z0 - 0.5, 0.22, 0.34, 'wood_dark')
        for k in range(6):
            zt = z0 - 1.6 - 1.6 * k
            for v in pv:
                ok = [u for u in pu if (u, v) in posts and posts[(u, v)] + 0.4 < zt]
                if len(ok) >= 2: K.beam(B, (min(ok) - 0.3, v), (max(ok) + 0.3, v), zt, 0.13, 0.3, 'wood_dark')
            for u in pu:
                ok = [v for v in pv if (u, v) in posts and posts[(u, v)] + 0.4 < zt - 0.8]
                if len(ok) >= 2: K.beam(B, (u, min(ok) - 0.3), (u, max(ok) + 0.3), zt - 0.8, 0.13, 0.3, 'wood_dark')
        rail = [(sx0 + 0.1, vs[0] - w + 0.1), (sx0 + 0.1, st0 + 0.1), (sx1 - 0.1, st0 + 0.1), (sx1 - 0.1, vs[0] - w + 0.1), (us[-1] + w - 0.1, vs[0] - w + 0.1)]
        K.rail_line(B, rail, z0, h=0.95, mat='wood_natural', giboshi_at=(0, 1, 2, 3), cap_mat='bronze', post_every=1.9)
        K.block_line(B, rail)
        K.walk_poly(B, [(sx0, st0), (sx1, st0), (sx1, vs[0]), (us[-1] + w, vs[0]), (us[-1] + w, vs[-1] + w), (us[0] - w, vs[-1] + w), (us[0] - w, vs[0]), (sx0, vs[0])], z0)
        K.block_poly(B, [(us[0] + 0.3, vs[1]), (us[-1] - 0.3, vs[1]), (us[-1] - 0.3, vs[-1] - 0.3), (us[0] + 0.3, vs[-1] - 0.3)])
        # small steps at the north end (to the 阿弥陀堂 path) and the south end (to the path down to the 音羽の滝)
        for (u, v0_, v1_) in ((us[0] - w + 0.8, vs[-1] + w + 1.2, vs[-1] + w), ):
            pass
    info['okunoin'] = fr
    return fr

# ------------------------------------------------------------------ 地主神社 (本殿, 拝殿, 総門, the stone torii and the stair from the 本堂)
def jishu(B, S, info):
    # 本殿: 入母屋 檜皮葺, vermilion with colourful brackets, on a raised floor
    cx, cy, yaw, Lf, Dd = bframe(S, 102164588, -79.5)
    zg = 122.3
    with Frame(B, cx, cy, 0.0, yaw):
        us = bays([2.4, 2.8, 2.4]); vs = bays([2.4, 2.6, 2.4])
        hall(B, list(us), list(vs), zg + 1.3, 3.6, mat='vermilion', r=0.2,
             walls={'front': ['karado', 'karado', 'karado'], 'back': ['plaster'] * 3, 'left': ['plaster'] * 3, 'right': ['plaster'] * 3},
             brackets='demitsudo', bscale=0.8, veranda=(1.0, (0, 1, 3)), rail=(0, 1, 3), steps=[('front', 0.0, 2.4, zg)], zground=zg,
             roof=dict(o=2.0, kind='irimoya', pitch=0.9, teri=1.5, sori=0.5, gable_frac=0.45, verge=0.7, gable_wall='temple_wall', prof=K.slope_profile(0.3, 1.25, 0.85, 0.22), **HIWADA))
        block_rect(B, list(us), list(vs), 1.2)
        # 瑞垣 (red fence) around
        fence = [(-6.0, -4.5), (6.0, -4.5), (6.0, 5.5), (-6.0, 5.5), (-6.0, -4.5)]
        for a, b in zip(fence[:-1], fence[1:]):
            K.rail_line(B, [a, b], zg, h=1.1, mat='vermilion', post_every=1.0, struts=True)
    # 拝殿: open hall, vermilion, 入母屋 檜皮葺, its south side on a 懸造 edge
    cx, cy, yaw, Lf, Dd = bframe(S, 102164583, -79.7)
    fr = (cx, cy, yaw); g = gfun(S, fr)
    zf = 120.6
    with Frame(B, cx, cy, 0.0, yaw):
        us = bays([2.6, 2.8, 2.6]); vs = bays([2.6, 2.6, 2.6])
        hall(B, list(us), list(vs), zf, 3.7, mat='vermilion', r=0.21, walls={s_: ['open'] * 3 for s_ in ('front', 'back', 'left', 'right')}, upper='plaster',
             brackets='demitsudo', bscale=0.8, interior=False,
             roof=dict(o=2.0, kind='irimoya', pitch=0.88, teri=1.5, sori=0.5, gable_frac=0.45, verge=0.7, gable_wall='temple_wall', prof=K.slope_profile(0.3, 1.25, 0.85, 0.22), **HIWADA))
        for u in us:
            for v in vs:
                zg_ = float(g(u, v))
                if zg_ < zf - 0.6:
                    K.post(B, u, v, zg_, zf - 0.1, 0.2, 'vermilion', base='stone', base_h=0.2)
        prim.box(B, us[0] - 0.3, vs[0] - 0.3, zf - 0.5, us[-1] + 0.3, vs[-1] + 0.3, zf - 0.12, 'vermilion', faces='xXyYz')
        prim.box(B, us[0] - 0.4, vs[0] - 0.4, zf + 3.4, us[-1] + 0.4, vs[-1] + 0.4, zf + 3.45, 'wood_dark', faces='z')
        K.walk_poly(B, K.rect(0, 0, us[-1] + 0.3, vs[-1] + 0.3), zf)
        K.rail_line(B, [(us[0] - 0.2, vs[0] - 0.2), (us[-1] + 0.2, vs[0] - 0.2)], zf, h=0.8, mat='vermilion', giboshi_at=(0, 1), w=0.08)
        K.block_line(B, [(us[0] - 0.2, vs[0] - 0.2), (us[-1] + 0.2, vs[0] - 0.2)])
    # the stone torii at the top of the stair from the 本堂 (地主神社鳥居 n at 2410.2, 1027.5) and the 総門
    tx, ty = 2410.2, 1027.5
    ang = math.atan2(1031.2 - 1020.4, 2409.3 - 2412.0)          # the stair's direction (up)
    arch.torii(B, tx, ty, float(S.ground(tx, ty)), ang - math.pi / 2, h=3.6, span=2.9, color='stone', top='stone', base='stone')
    cx, cy, yaw, Lf, Dd = bframe(S, 337096697, 180.0)
    with Frame(B, cx, cy, 0.0, yaw):
        zg = float(S.ground(cx, cy))
        us = [-1.6, 1.6]; vs = [-0.9, 0.9]
        for u in us:
            for v in vs:
                K.post(B, u, v, zg, zg + 3.2, 0.17, 'vermilion', base='stone', base_h=0.15)
        for v in vs: K.beam(B, (us[0], v), (us[1], v), zg + 3.2, 0.18, 0.26, 'vermilion', ext=0.3)
        for u in us: K.beam(B, (u, vs[0]), (u, vs[1]), zg + 3.2, 0.18, 0.26, 'vermilion', ext=0.3)
        K.mroof(B, 3.6, 2.2, zg + 3.65, 1.0, kind='kirizuma', pitch=0.6, teri=1.4, verge=0.6, **HIWADA)
    # the 社務所 (office) and the small shrines: plain
    cx, cy, yaw, Lf, Dd = bframe(S, 102164635, -78.5)
    with Frame(B, cx, cy, 0.0, yaw):
        zg = 118.6
        plain(B, Lf - 1.6, Dd - 1.6, zg, 3.4, 'irimoya', 'kawara', wall='temple_wall')

# ------------------------------------------------------------------ 音羽の滝: the stone pavilion, three streams, the pool, 不動堂 above
def otowa(B, S, info):
    # the pavilion stands against the cliff (east), facing west over the pool (OSM w340393741, waterfall n3476170467);
    # the DEM smooths this stepped court, so it is cut out and modelled at the real levels
    cx, cy = 2416.4, 957.1
    yaw = math.radians(-82.0)          # u along the cliff (south), front (-v) facing west over the pool
    fr = (cx, cy, yaw)
    g = gfun(S, fr)
    zw = 95.95                          # pool water
    zp = 97.45                          # the visitors' platform behind the balustrade
    U0, U1, V0, V1 = -5.0, 3.4, -6.4, 3.4
    ring = [(U0, V0), (U1, V0), (U1, V1), (U0, V1)]
    S.cut.append([tuple(map(float, q)) for q in K.to_world(fr, ring)])
    info.setdefault('cuts', []).append(([tuple(map(float, q)) for q in K.to_world(fr, ring)], zw - 0.8))
    def edge_wall(p0, p1, zb, zmin, out):
        p0 = np.array(p0, float); p1 = np.array(p1, float); n = 8
        for i in range(n):
            a = p0 + (p1 - p0) * i / n; c = p0 + (p1 - p0) * (i + 1) / n
            ta = max(zmin, float(g(*(a + np.array(out) * 0.3))) + 0.08); tc = max(zmin, float(g(*(c + np.array(out) * 0.3))) + 0.08)
            P = np.array([np.r_[a, zb], np.r_[c, zb], np.r_[c, tc], np.r_[a, ta]])
            I = [[0, 1, 2], [0, 2, 3]] if np.cross(P[1] - P[0], P[2] - P[0])[:2] @ -np.array(out) > 0 else [[0, 2, 1], [0, 3, 2]]
            B.add(P, I, 'stone', c1=(0, 3, i, 0)); B.add(P, [t[::-1] for t in I], 'stone', c1=(0, 3, i, 0))
            prim.obox(B, np.r_[a, ta + 0.08], np.r_[c, tc + 0.08], 0.45, 0.16, 'stone')
    with Frame(B, cx, cy, 0.0, yaw):
        # the pool: basin floor, walls up to the surrounding ground, the water, stepping stones
        prim.box(B, U0, V0, zw - 0.7, U1, -2.2, zw - 0.6, 'stone', faces='Z')
        prim.polygon(B, [(U0 + 0.2, V0 + 0.2), (U1 - 0.2, V0 + 0.2), (U1 - 0.2, -2.4), (U0 + 0.2, -2.4)], zw, 'water')
        K.block_poly(B, [(U0, V0), (U1, V0), (U1, -2.3), (U0, -2.3)])
        edge_wall((U0, V0), (U1, V0), zw - 0.7, zw + 0.3, (0, -1))
        edge_wall((U0, V0), (U0, -2.2), zw - 0.7, zw + 0.3, (-1, 0))
        edge_wall((U1, V0), (U1, V1), zw - 0.7, zp, (1, 0))
        for k in range(5):
            u = U0 + 1.2 + k * 1.45
            prim.cyl(B, (u, -4.6 + 0.4 * (k % 2), zw - 0.6), (u, -4.6 + 0.4 * (k % 2), zw + 0.05), 0.45, 0.42, 10, 'stone')
        # the platform, its front wall rising from the pool
        prim.box(B, U0, -2.2, zw - 0.7, U1, V1, zp, 'stone', faces='ZyxX')
        K.walk_poly(B, [(U0, -1.9), (U1, -1.9), (U1, 2.6), (U0, 2.6)], zp)
        K.tamagaki(B, [(U0 + 0.2, -1.95), (U1 - 0.2, -1.95)], z=zp, h=0.8)
        K.block_line(B, [(U0 + 0.2, -1.95), (U1 - 0.2, -1.95)])
        # steps up from the path at the north end (OSM 340393745)
        zn = float(g(U0 - 2.4, 0.4))
        K.steps(B, (U0 - 2.4, 0.4), (U0, 0.4), zn, zp, 2.2, 'stone', riser=0.17)
        # four stone columns, stone beams, three spout beams, a stone roof
        zc = zp + 3.1
        for u in (-2.6, 2.6):
            prim.cyl(B, (u, -1.7, zw - 0.6), (u, -1.7, zp + 0.3), 0.42, 0.42, 4, 'stone')
            prim.cyl(B, (u, -1.7, zp + 0.3), (u, -1.7, zc), 0.22, 0.2, 12, 'stone')
            prim.cyl(B, (u, 1.9, zp), (u, 1.9, zc), 0.22, 0.2, 12, 'stone')
        K.beam(B, (-3.6, -1.7), (3.6, -1.7), zc + 0.45, 0.4, 0.45, 'stone')
        K.beam(B, (-3.6, 1.9), (3.6, 1.9), zc + 0.45, 0.4, 0.45, 'stone')
        for u in (-2.6, 0.0, 2.6):
            K.beam(B, (u, -2.5), (u, 1.9), zc + 0.85, 0.5, 0.4, 'stone')     # spout beams projecting out over the pool
        Bt = jk.Builder('otowa_roof'); Bt.xf = B.xf
        with Frame(Bt, 0.0, 0.1, 0.0, 0.0):
            K.mroof(Bt, 7.6, 4.0, zc + 1.2, 0.9, kind='irimoya', cover='copper', pitch=0.55, teri=1.3, sori=0.15, gable_frac=0.5, verge=0.5,
                    rafter=0.0, ends='oni', bargeboard_mat='stone', gable_wall='stone', ridge_h=0.35, ridge_w=0.5, edge=0.5)
        K.restyle(Bt, {'copper': 'stone', 'ridge': 'stone', 'wood_dark': 'stone'})
        K.merge_into(B, Bt)
        prim.box(B, -3.9, -2.2, zc + 0.95, 3.9, 2.3, zc + 1.0, 'stone', faces='z')
        # the three streams (water) from the spouts into the pool
        for u in (-2.6, 0.0, 2.6):
            prim.cyl(B, (u, -2.45, zc + 0.6), (u, -2.45, zw), 0.035, 0.05, 6, 'water', caps=(False, False))
            prim.cyl(B, (u, -2.45, zw), (u, -2.45, zw + 0.06), 0.22, 0.1, 10, 'water', caps=(False, True), tag='detail')
        # the back: the rock wall with the shrine niches (不動明王), lamps; a retaining wall to the cliff above
        ztop = max(zp + 5.5, float(max(g(u, V1 + 0.5) for u in np.linspace(U0, U1, 6))) + 0.3)
        prim.box(B, U0 - 0.5, 2.6, zp - 0.2, U1 + 0.5, V1, ztop, 'stone', c1=(0, 3, 7, 0))
        for u in (-1.6, 0.0, 1.6):
            prim.box(B, u - 0.45, 2.45, zp + 0.6, u + 0.45, 2.6, zp + 2.1, 'black_lacquer')
            B.lamp(u, 2.2, zp + 2.3, 8.0)
        # 不動堂 (vermilion shrine) above on the cliff, to the south
        with Frame(B, 4.6, 4.6, 0.0, 0.0):
            zs = float(g(4.6, 4.6)) + 0.2
            us = [-1.5, 1.5]; vs = [-1.3, 1.3]
            for u in us:
                for v in vs:
                    K.post(B, u, v, zs, zs + 2.8, 0.15, 'vermilion', base='stone', base_h=0.1)
            for a, b in zip(K.rect(0, 0, 1.5, 1.3), K.rect(0, 0, 1.5, 1.3)[1:] + K.rect(0, 0, 1.5, 1.3)[:1]):
                K.wall_panel(B, a, b, zs + 0.3, zs + 2.7, 'temple_wall', both=True, **K.PLASTER)
            prim.box(B, -2.0, -1.8, zs - 0.8, 2.0, 1.8, zs + 0.05, 'stone')
            K.mroof(B, 3.2, 2.8, zs + 3.2, 0.9, kind='irimoya', pitch=0.75, teri=1.5, sori=0.3, gable_frac=0.5, verge=0.5, **HIWADA)
    return fr

# ------------------------------------------------------------------ the precinct's other buildings: plain halls on their footprints
def plain(B, L, D, zg, H, kind='irimoya', cover='kawara', wall='temple_wall', frame_mat='wood_dark', o=1.2, pitch=0.7, base=0.45):
    """a plain building (temple office, lodging, tea house) centred at the frame origin: white walls with dark posts,
    a tiled roof"""
    L = max(2.5, L); D = max(2.0, D)
    cover = {'kawara': 'sangawara'}.get(cover, cover)
    zf = zg + base
    prim.box(B, -L / 2 - 0.2, -D / 2 - 0.2, zg - 0.6, L / 2 + 0.2, D / 2 + 0.2, zf, 'stone', faces='xXyYZ')
    prim.box(B, -L / 2, -D / 2, zf, L / 2, D / 2, zf + H, wall, faces='xXyY', c0=(236, 232, 222, 35), c1=(0, 4, 0, 0))
    nu = max(1, int(round(L / 2.0))); nv = max(1, int(round(D / 2.0)))
    for i in range(nu + 1):
        u = -L / 2 + L * i / nu
        for v in (-D / 2, D / 2):
            prim.box(B, u - 0.11, v - 0.11, zf, u + 0.11, v + 0.11, zf + H, frame_mat, faces='xXyY')
    for j in range(1, nv):
        v = -D / 2 + D * j / nv
        for u in (-L / 2, L / 2):
            prim.box(B, u - 0.11, v - 0.11, zf, u + 0.11, v + 0.11, zf + H, frame_mat, faces='xXyY')
    for a, b in zip(K.rect(0, 0, L / 2, D / 2), K.rect(0, 0, L / 2, D / 2)[1:] + K.rect(0, 0, L / 2, D / 2)[:1]):
        K.beam(B, a, b, zf + H, 0.2, 0.25, frame_mat, ext=0.2)
        K.beam(B, a, b, zf + H * 0.62, 0.12, 0.16, frame_mat)
    K.mroof(B, L, D, zf + H + 0.25, o, kind=kind, cover=cover, pitch=pitch, teri=1.3, sori=0.2, rafter=0.0, tiers=1,
            rafter_mat='wood_dark', ends='oni', gable_wall='temple_wall', coarse=2.5)
    K.block_poly(B, K.rect(0, 0, L / 2 + 0.3, D / 2 + 0.3))
