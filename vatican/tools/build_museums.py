"""Vatican Museums interiors.  Each room is built in its own local frame (x right, y forward, z up, origin on
the floor) and placed in the world near its real position.  Face winding is fixed afterwards with
bake.orient_faces using the viewpoints each room provides, so generators only need correct UVs as seen
from inside (art quads: p0 bottom-left, right, up as seen by a viewer facing the wall)."""
import math, sys, json
import numpy as np
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
from vb.geom import *
from vb.arch import *
from vb import statues as ST, terrain

GOLD = 'gold'; STUCCO = 'stucco_white'

class Room:
    def __init__(self, name, origin, rot, exposure=0.75):
        self.name = name; self.origin = origin; self.rot = rot; self.exposure = exposure
        self.m = Mesh(); self.vp = []; self.lights = []; self.box = None; self.info = []
    @property
    def M(self):
        return mat4(self.origin, rz=self.rot)
    def add(self, mesh): self.m.merge(mesh)
    def view(self, *pts): self.vp.extend(pts)
    def light(self, p, size, energy, rot=(0, 0, 0), color=(1.0, 0.94, 0.85)):
        self.lights.append(dict(p=p, size=size, energy=energy, rot=rot, color=color))
    def world(self):
        M = self.M
        return dict(name=self.name, mesh=self.m.transformed(M), vp=[tuple(apply(M, np.array([p]))[0]) for p in self.vp],
                    lights=[dict(loc=tuple(apply(M, np.array([L['p']]))[0]), size=L['size'], energy=L['energy'],
                                 rot=(L['rot'][0], L['rot'][1], L['rot'][2] + self.rot), color=L['color']) for L in self.lights],
                    box=self.box, origin=self.origin, rot=self.rot, exposure=self.exposure, info=self.info)

def art_quad(p0, right, up, w, h, key, nu=6, nv=6, uv0=(0, 0), uv1=(1, 1)):
    r = np.array(right, float); r /= np.linalg.norm(r); u = np.array(up, float); u /= np.linalg.norm(u)
    return grid_quad(p0, r * w, u * h, nu, nv, f'art:{key}' if not key.startswith(('marble', 'stucco', 'gold', 'travert', 'wood', 'glass', 'plaster')) else key,
                     lambda s, t: (uv0[0] + (uv1[0] - uv0[0]) * s, uv0[1] + (uv1[1] - uv0[1]) * t))

def heightfield(x0, x1, y0, y1, nx, ny, zf, mat, uvf=None):
    m = Mesh()
    xs = np.linspace(x0, x1, nx + 1); ys = np.linspace(y0, y1, ny + 1)
    P = [[(x, y, zf(x, y)) for x in xs] for y in ys]
    for j in range(ny):
        for i in range(nx):
            q = [P[j][i], P[j][i + 1], P[j + 1][i + 1], P[j + 1][i]]
            o = m.add_v(q)
            uv = [uvf(p[0], p[1]) for p in q] if uvf else [None] * 4
            # split along the diagonal that follows a crease (groin vaults): the one whose midpoint height is truer
            cx, cy = (q[0][0] + q[2][0]) / 2, (q[0][1] + q[2][1]) / 2; zt = zf(cx, cy)
            d02 = abs((q[0][2] + q[2][2]) / 2 - zt); d13 = abs((q[1][2] + q[3][2]) / 2 - zt)
            tris = ((0, 1, 2), (0, 2, 3)) if d02 <= d13 else ((0, 1, 3), (1, 2, 3))
            for t in tris:
                m.face([o + k for k in t], mat, True, [uv[k] for k in t] if uvf else None)
    return m

def wall_band(xa, xb, za, zb, y, mat, uvf=None, nx=8, nz=4, facing=-1):
    """vertical wall rectangle in the plane y=const spanning x in [xa,xb], z in [za,zb]."""
    m = Mesh()
    for i in range(nx):
        for j in range(nz):
            x0, x1 = xa + (xb - xa) * i / nx, xa + (xb - xa) * (i + 1) / nx
            z0, z1 = za + (zb - za) * j / nz, za + (zb - za) * (j + 1) / nz
            q = [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]
            o = m.add_v(q); m.face([o, o + 1, o + 2, o + 3], mat, False, [uvf(p) for p in q] if uvf else None)
    return m

def grid_points(x0, x1, y0, y1, zs, step=2.5):
    P = []
    for x in np.arange(x0, x1 + 1e-6, step):
        for y in np.arange(y0, y1 + 1e-6, step):
            for z in zs: P.append((float(x), float(y), float(z)))
    return P

# =============================================================================== Raphael Rooms
def groin(a, b, zsx, zsy):
    """groin vault over [-a,a]x[-b,b]: barrel spanning x (lunettes on the walls y=+-b) springing at zsx and
    barrel spanning y (lunettes on x=+-a) springing at zsy."""
    def z(x, y):
        z1 = zsx + math.sqrt(max(0.0, a * a - x * x))
        z2 = zsy + math.sqrt(max(0.0, b * b - y * y))
        return max(z1, z2)
    return z

def lunette_wall(m, corner, right, w, z_bot, zs, key_img, key_dado, crown, z_img_bot, nx=24, z_other=0.0):
    """a wall of width w (local coords: corner at left as seen from inside, `right` unit vector), plain dado
    from 0 to z_img_bot, image from z_img_bot to crown clipped by the semicircular arch springing at zs."""
    c = np.array(corner, float); r = np.array(right, float)
    R = w / 2.0
    def top(s):  # s in [0,w]: the vault meets the wall along the lunette arc, or the other barrel near the corners
        return max(zs + math.sqrt(max(0.0, R * R - (s - R) ** 2)), z_other) + 0.3   # tucked behind the vault
    for i in range(nx):
        s0, s1 = w * i / nx, w * (i + 1) / nx
        t0, t1 = top(s0), top(s1)
        # dado
        q = [c + r * s0 + [0, 0, z_bot], c + r * s1 + [0, 0, z_bot], c + r * s1 + [0, 0, z_img_bot], c + r * s0 + [0, 0, z_img_bot]]
        o = m.add_v(q); m.face([o, o + 1, o + 2, o + 3], f'art:{key_dado}', False, [(s0 / w * 2, 0), (s1 / w * 2, 0), (s1 / w * 2, 1), (s0 / w * 2, 1)])
        # image part, split vertically in 6 for the arch clipping
        H = crown - z_img_bot
        for k in range(8):
            za, zb = z_img_bot + H * k / 8, z_img_bot + H * (k + 1) / 8
            if za >= max(t0, t1): break   # (image uv keeps its scale: the part above the crown is hidden by the vault)
            qa = [c + r * s0 + [0, 0, za], c + r * s1 + [0, 0, za], c + r * s1 + [0, 0, min(zb, t1)], c + r * s0 + [0, 0, min(zb, t0)]]
            uv = [(s0 / w, min(1, (za - z_img_bot) / H)), (s1 / w, min(1, (za - z_img_bot) / H)), (s1 / w, min(1, (min(zb, t1) - z_img_bot) / H)), (s0 / w, min(1, (min(zb, t0) - z_img_bot) / H))]
            o = m.add_v(qa); m.face([o, o + 1, o + 2, o + 3], f'art:{key_img}', False, uv)

def stanza(name, origin, rot, a, b, walls, ceiling_key, door_walls=('W', 'E'), z_img=(1.9, 1.75)):
    """walls: dict side -> image key for N(+y) S(-y) E(+x) W(-x).  N/S are window walls of width 2a with images
    covering 0.75*2a in height; E/W are partition walls of width 2b with images of the art's own aspect."""
    R = Room(name, origin, rot)
    m = R.m
    crown = 7.2
    zsx = crown - a           # lunettes on N/S walls (span 2a)
    zsy = crown - b           # lunettes on E/W walls (span 2b)
    zf = groin(a, b, zsx, zsy)
    m.merge(heightfield(-a, a, -b, b, 28, 28, zf, f'art:{ceiling_key}', lambda x, y: ((x + a) / (2 * a), (y + b) / (2 * b))))
    # floor (marble opus sectile) and walls
    m.merge(art_quad((-a - 0.1, -b - 0.1, 0), (1, 0, 0), (0, 1, 0), 2 * a + 0.2, 2 * b + 0.2, 'stanza_floor', 6, 6, (0, 0), (2 * a / 3.5, 2 * b / 3.5)))
    # N wall: viewer faces +y, right = +x, corner (-a, b)
    lunette_wall(m, (-a, b, 0), (1, 0, 0), 2 * a, 0, zsx, walls['N'], 'stanza_dado_win', crown, crown - 1.5 * a, z_other=zsy)
    lunette_wall(m, (a, -b, 0), (-1, 0, 0), 2 * a, 0, zsx, walls['S'], 'stanza_dado_win', crown, crown - 1.5 * a, z_other=zsy)
    for side, corner, right in (('E', (a, b, 0), (0, -1, 0)), ('W', (-a, -b, 0), (0, 1, 0))):
        key = walls[side]
        lunette_wall(m, corner, right, 2 * b, 0, zsy, key, 'stanza_dado_door', crown, z_img[0], z_other=zsx)
    for side, pos in (('N', (0, b, 4.5)), ('S', (0, -b, 4.5)), ('E', (a, 0, 4.5)), ('W', (-a, 0, 4.5))):
        R.info.append(dict(key=walls[side], pos=pos))
    R.view(*[p for p in grid_points(-a + 0.6, a - 0.6, -b + 0.6, b - 0.6, (1.6, 3.2, 4.8, 6.4), 1.2) if p[2] < zf(p[0], p[1]) - 0.4])
    R.light((0, 0, crown - 0.3), (2 * a - 1, 2 * b - 1), 900.0, rot=(math.pi, 0, 0))    # soft downlight (museum lighting)
    R.light((0, 0, 0.5), (2 * a - 1, 2 * b - 1), 250.0)                                   # bounce from the floor
    R.box = dict(u0=-a, u1=a, v0=-b, v1=b, z0=-0.5, z1=crown + 0.5)
    return R

def raphael_rooms(base, rot):
    """the four Stanze in a row along +x (west to east): Costantino, Eliodoro, Segnatura, Incendio."""
    rooms = []
    c, s = math.cos(rot), math.sin(rot)
    def P(dx):
        return (base[0] + c * dx, base[1] + s * dx, base[2])
    # Sala di Costantino: bigger, flat coved ceiling
    rooms.append(costantino(P(0.0), rot))
    x = 7.5 + 0.8 + 3.6
    rooms.append(stanza('eliodoro', P(x), rot, 3.6, 3.95, dict(N='bolsena', S='liberation', E='heliodorus', W='attila'), 'vault_eliodoro'))
    x += 3.6 + 0.8 + 3.6
    rooms.append(stanza('segnatura', P(x), rot, 3.5, 3.85, dict(N='parnassus', S='virtues', E='school_of_athens', W='disputa'), 'vault_segnatura'))
    x += 3.5 + 0.8 + 3.6
    rooms.append(stanza('incendio', P(x), rot, 3.6, 3.95, dict(N='ostia', S='oath', E='fire_borgo', W='coronation'), 'vault_incendio'))
    return rooms

def costantino(origin, rot):
    R = Room('costantino', origin, rot)
    m = R.m; a, b, H = 7.5, 5.2, 10.5
    # coved ceiling: flat centre at H, cove from 8.0 at the walls
    def zc(x, y):
        dx = max(0.0, abs(x) - (a - 2.5)) / 2.5; dy = max(0.0, abs(y) - (b - 2.5)) / 2.5
        d = min(1.0, max(dx, dy))
        return H - 2.5 * (1 - math.sqrt(max(0.0, 1 - d * d)))
    m.merge(heightfield(-a, a, -b, b, 30, 22, zc, 'art:vault_costantino', lambda x, y: ((x + a) / (2 * a), (y + b) / (2 * b))))
    m.merge(art_quad((-a, -b, 0), (1, 0, 0), (0, 1, 0), 2 * a, 2 * b, 'stanza_floor', 8, 6, (0, 0), (2 * a / 3.5, 2 * b / 3.5)))
    # walls: painted to 8.0, frescoes as framed 'tapestries' between painted popes & virtues
    def wall(corner, right, w, key, fw, fh, z0):
        cc = np.array(corner, float); r = np.array(right, float)
        m.merge(art_quad(tuple(cc), r, (0, 0, 1), w, 8.0, 'costantino_wall', 8, 4, (0, 0), (w / 4.0, 1)))
        off = (w - fw) / 2
        m.merge(art_quad(tuple(cc + r * off + np.cross(r, [0, 0, 1]) * 0.03), r, (0, 0, 1), fw, fh, key, 8, 6))
    wall((-a, b, 0), (1, 0, 0), 2 * a, 'milvian', 11.6, 7.55 * 1.0 - 0.0, 0.0)
    wall((a, -b, 0), (-1, 0, 0), 2 * a, 'vision_cross', 11.6, 7.5, 0.0)
    wall((a, b, 0), (0, -1, 0), 2 * b, 'baptism_constantine', 8.4, 5.2, 0.0)
    wall((-a, -b, 0), (0, 1, 0), 2 * b, 'donation_constantine', 8.4, 5.8, 0.0)
    # lift the frescoes: re-place (they were built at z=0): shift every art face of the fresco keys up
    keys = {'art:milvian': 0.4, 'art:vision_cross': 0.45, 'art:baptism_constantine': 1.6, 'art:donation_constantine': 1.3}
    V = np.array(m.V); moved = set()
    for fi, mat in enumerate(m.M):
        if mat in keys:
            for v in m.F[fi]:
                if v not in moved: V[v, 2] += keys[mat]; moved.add(v)
    m.V = V.tolist()
    for key, pos in (('milvian', (0, b, 4.5)), ('vision_cross', (0, -b, 4.5)), ('baptism_constantine', (a, 0, 4.5)), ('donation_constantine', (-a, 0, 4.5))):
        R.info.append(dict(key=key, pos=pos))
    R.view(*[p for p in grid_points(-a + 0.8, a - 0.8, -b + 0.8, b - 0.8, (1.6, 5.0, 7.5, 9.5), 1.5) if p[2] < zc(p[0], p[1]) - 0.4])
    R.light((0, 0, H - 0.4), (2 * a - 1, 2 * b - 1), 2400.0, rot=(math.pi, 0, 0))
    R.box = dict(u0=-a, u1=a, v0=-b, v1=b, z0=-0.5, z1=H + 0.5)
    return R

# =============================================================================== Gallery of Maps
MAPS = ['etruria', 'latium', 'patrimonium', 'umbria', 'perusinus', 'flaminia', 'urbini', 'bononiensis', 'ferraria',
        'transpadana', 'forum_iulii', 'mediolanum', 'pedemontium', 'lucania', 'salerno', 'sicilia', 'sardinia', 'corsica',
        'avignon', 'malta']
TALL = ['genua', 'venetiae', 'civitas_vetus', 'corfu', 'tremiti', 'lepanto']

def gallery_of_maps(origin, rot, L=120.0, nb=20):
    R = Room('maps', origin, rot, exposure=0.8)
    m = R.m; hw = 3.0; zc = 6.6; rise = 2.4; bay = L / nb
    def vz(x, y):
        return zc + rise * math.sqrt(max(0.0, 1 - (x / hw) ** 2))
    # vault: one texture tile per bay (u across, v along)
    # vault: each bay shows one of the 8 photographed bays of the atlas (2 columns x 4 rows), uv set per face
    vt = heightfield(-hw, hw, 0, L, 16, nb * 6, vz, 'art:maps_vault', lambda x, y: (0, 0))
    for fi in range(len(vt.F)):
        k = int(sum(vt.V[v][1] for v in vt.F[fi]) / len(vt.F[fi]) // bay); t = k % 8
        vt.UV[fi] = [(((t % 2) + (vt.V[v][0] + hw) / (2 * hw)) / 2, ((t // 2) + (vt.V[v][1] - k * bay) / bay) / 4) for v in vt.F[fi]]
    m.merge(vt)
    m.merge(art_quad((-hw, 0, 0), (1, 0, 0), (0, 1, 0), 2 * hw, L, 'maps_floor', 4, nb * 2, (0, 0), (2 * hw / 3.0, L / 3.0)))
    k = 0
    for side in (-1, 1):
        x = side * hw
        right = (0, -1, 0) if side > 0 else (0, 1, 0)       # viewer faces the wall (+x for side>0): right = -y
        for i in range(nb):
            y0, y1 = bay * i, bay * (i + 1)
            if side > 0: a0, a1 = y1, y0
            else: a0, a1 = y0, y1
            # wall field (painted stucco) full height to the cornice
            m.merge(art_quad((x, a0, 0), right, (0, 0, 1), bay, zc, 'maps_wall', 4, 4, (0, 0), (1, 1)))
            # map in the middle of the bay
            key = MAPS[(i + (0 if side < 0 else 10)) % len(MAPS)] if i not in (0, nb - 1) else TALL[(k) % len(TALL)]
            k += 1
            ww, hh = (4.05, 3.3) if key in MAPS else (1.9, 3.6)
            yc = (y0 + y1) / 2
            start = yc - ww / 2 * (1 if side < 0 else -1)
            m.merge(art_quad((x - side * 0.03, start, 1.7), right, (0, 0, 1), ww, hh, f'map_{key}', 6, 4))
        # lunette windows in the vault penetrations above each pier (light source)
    for yy, right in ((0.0, (-1, 0, 0)), (L, (1, 0, 0))):     # end walls with a doorway painted
        x0 = hw if yy == 0.0 else -hw
        m.merge(art_quad((x0, yy, 0), right, (0, 0, 1), 2 * hw, zc + rise + 0.3, 'maps_end', 4, 6))
    for i in range(nb + 1):
        for side in (-1, 1):
            R.light((side * (hw - 0.3), bay * i, zc - 0.2), (0.8, 1.6), 420.0, rot=(0, side * -1.2, 0), color=(1.0, 0.96, 0.9))
    R.light((0, L / 2, 1.0), (2.0, L - 4), 900.0, rot=(0, 0, 0), color=(1.0, 0.95, 0.88))
    R.view(*[(x, y, z) for x in (-1.8, 0, 1.8) for y in np.arange(1.0, L - 0.9, 2.5) for z in (1.6, 4.5, 7.5)])
    R.box = dict(u0=-hw, u1=hw, v0=0, v1=L, z0=-0.5, z1=zc + rise + 0.5)
    R.info.append(dict(key='gallery_maps', pos=(0, L / 2, 2.0)))
    return R

# =============================================================================== Pio-Clementino
def ottagono(origin, rot):
    """Cortile Ottagono: open octagonal court (side 'a' long, chamfers), arcaded portico on columns, four corner
    gabinetti with Laocoön (NE), Apollo (NW), Perseus/Hermes (stand-ins)."""
    R = Room('ottagono', origin, rot, exposure=1.0)
    m = R.m
    S = 15.0; ch = 5.0        # half size, chamfer
    pts = [(S - ch, -S), (S, -S + ch), (S, S - ch), (S - ch, S), (-S + ch, S), (-S, S - ch), (-S, -S + ch), (-S + ch, -S)]
    # court floor (travertine) inside the portico line
    inner = [(p[0] * 0.66, p[1] * 0.66) for p in pts]
    m.merge(cap([inner], 0.0, 'travertine_light', True))
    m.merge(cap([pts, inner], -0.25, 'marble_grey', True))
    m.merge(prism([inner], -0.25, 0.0, 'travertine', top=False))
    # portico: columns along the inner octagon, arches, roof slab, back wall with niches
    H = 7.5
    for i in range(8):
        A = np.array(inner[i]); B = np.array(inner[(i + 1) % 8])
        L = np.linalg.norm(B - A); d = (B - A) / L; n = np.array([d[1], -d[0]])   # outward
        # Simonetti's arcade: a wall pierced by round arches, Ionic columns before the piers, attic above
        nb = max(1, int(round(L / 4.6))); bay = L / nb; aw = bay - 1.3
        holes = [opening_shape(aw, 5.4, 'arch', x=bay * k + (bay - aw) / 2, y=0.0) for k in range(nb)]
        F = frame((A[0], A[1], 0), (d[0], d[1], 0), (n[0], n[1], 0), (0, 0, 1))
        g = Mesh()
        g.merge(wall(L, H, 0.9, 'travertine_light', holes, back=True, sides=True, top=True))
        for k in range(nb + 1):
            x = min(max(bay * k, 0.5), L - 0.5)
            g.merge(column(0.62, 5.6, 'ionic', 'marble_grey', seg=14).transformed(mat4((x, -0.55, 0))))
            g.merge(box(x - 0.45, -0.95, 5.6, x + 0.45, 0, 6.1, 'travertine'))
        for k in range(nb):
            g.merge(arch_moulding(bay * k + bay / 2, 5.4 - aw / 2, aw / 2, 0.45, 0.12, 'travertine', y=0.0))
        g.merge(straight(cornice_profile(0.6, 0.55), 0, L, 6.1, -0.2, 'travertine'))
        g.merge(straight(cornice_profile(0.5, 0.45), 0, L, H - 0.5, 0, 'travertine'))
        m.merge(g.transformed(F))
        # orange trees in terracotta pots along the court
        for k in range(nb):
            if k % 2: continue
            p = A + d * (bay * k + bay / 2) - n * 2.4
            m.merge(lathe([(0, 0), (0.45, 0), (0.6, 0.75), (0.65, 0.8), (0, 0.8)], 12, mat='terracotta', center=(p[0], p[1], 0)))
            m.merge(lathe([(0.06, 0.8), (0.06, 1.7), (0, 1.75)], 6, mat='bark', center=(p[0], p[1], 0)))
            m.merge(lathe([(0.75 * math.sin(t), 2.3 - 0.75 * math.cos(t)) for t in np.linspace(0, math.pi, 7)], 10, mat='foliage_dark', center=(p[0], p[1], 0)))
        # portico ceiling and the back wall (outer octagon)
        A2 = np.array(pts[i]); B2 = np.array(pts[(i + 1) % 8])
        q = [(A[0], A[1], 5.6), (B[0], B[1], 5.6), (B2[0], B2[1], 5.6), (A2[0], A2[1], 5.6)]
        o = m.add_v(q); m.face([o, o + 1, o + 2, o + 3], 'stucco_white')
        L2 = np.linalg.norm(B2 - A2); d2 = (B2 - A2) / L2
        m.merge(art_quad((A2[0], A2[1], 0), (d2[0], d2[1], 0), (0, 0, 1), L2, 5.6, 'stucco_white', 6, 3))
    # roof of the portico (seen from the court above)
    m.merge(cap([pts, [(p[0] * 0.66 * 0.97, p[1] * 0.66 * 0.97) for p in pts]], H, 'roof_tile', True))
    # outer walls up to the roof
    for i in range(8):
        A2 = np.array(pts[i]); B2 = np.array(pts[(i + 1) % 8])
        q = [(A2[0], A2[1], 5.6), (B2[0], B2[1], 5.6), (B2[0], B2[1], H), (A2[0], A2[1], H)]
        o = m.add_v(q); m.face([o, o + 1, o + 2, o + 3], 'stucco_white')
    # centre fountain basin
    m.merge(lathe([(0, 0), (2.4, 0), (2.5, 0.55), (2.25, 0.6), (2.25, 0.4), (0, 0.4)], 32, mat='marble_grey'))
    m.merge(lathe([(0.0, 0.4), (0.35, 0.4), (0.25, 1.3), (0.55, 1.4), (0.0, 1.5)], 16, mat='marble_white'))
    # gabinetti in the four chamfers: statue on a pedestal facing the court centre
    statues_ = [('laocoon', 2.1, 'laocoon', 0), ('apollo', 2.24, 'apollo', 1), ('doryphoros', 2.1, 'perseus_standin', 1), ('christ', 2.0, 'hermes_standin', 2)]
    for k, (key, h, label, lod) in enumerate(statues_):
        i = 2 * k
        A2 = np.array(pts[i]); B2 = np.array(pts[(i + 1) % 8])
        c = (A2 + B2) / 2; nrm = -c / np.linalg.norm(c)
        pos = c + nrm * 3.4
        face = math.atan2(nrm[1], nrm[0])
        m.merge(box(pos[0] - 1.2, pos[1] - 1.2, 0, pos[0] + 1.2, pos[1] + 1.2, 1.05, 'marble_grey').transformed(mat4((0, 0, 0))))
        m.merge(ST.place(key, pos[0], pos[1], 1.05, h, face - math.pi / 2 + math.pi, lod=lod, mat='statue_marble'))
        R.info.append(dict(key=label, pos=(float(pos[0]), float(pos[1]), 2.2)))
        lp = pos + nrm * 2.2
        R.light((float(lp[0]), float(lp[1]), 5.2), (1.6, 1.6), 900.0, rot=(math.pi * 0.75, 0, math.atan2(nrm[1], nrm[0]) + math.pi / 2), color=(1.0, 0.95, 0.86))
        # the gabinetto: a niche room behind
        g = niche(4.2, 6.2, 2.4, 'stucco_white')
        m.merge(g.transformed(frame((c[0], c[1], 0), (-nrm[1], nrm[0], 0), (-nrm[0], -nrm[1], 0), (0, 0, 1))))
    R.view(*grid_points(-9, 9, -9, 9, (1.6, 4.0, 7.0), 2.0))
    R.view(*[(p[0] * 0.83, p[1] * 0.83, z) for p in pts for z in (1.6, 4.0)])
    R.box = dict(u0=-S, u1=S, v0=-S, v1=S, z0=-0.5, z1=H + 0.5)
    return R

def sala_rotonda(origin, rot):
    """Pantheon-like rotunda (Simonetti 1779): diameter 21.6, coffered dome with oculus, porphyry basin, Otricoli
    floor mosaic, ten niches with colossal statues."""
    R = Room('rotonda', origin, rot)
    m = R.m; r = 10.8; zs = 11.0; H = 21.6
    prof = [(r, 0), (r, zs)] + [(r * math.cos(t), zs + r * math.sin(t)) for t in np.linspace(0, math.pi / 2 * 0.86, 12)[1:]]
    wall = lathe(prof[:2], 40, mat='marble_int')
    m.merge(wall)
    dome = lathe(prof[1:], 40, mat='art:rotonda_dome')
    for fi in range(len(dome.F)):
        dome.UV[fi] = [((math.atan2(dome.V[v][1], dome.V[v][0]) / (2 * math.pi) * 20) % 20, (dome.V[v][2] - zs) / r * 1.0) for v in dome.F[fi]]
    m.merge(seam_unwrap(dome, 20))
    ro = prof[-1][0]
    m.merge(lathe([(ro, prof[-1][1]), (ro, prof[-1][1] + 1.2)], 24, mat='stucco_white'))
    m.merge(art_quad((-r, -r, 0), (1, 0, 0), (0, 1, 0), 2 * r, 2 * r, 'otricoli_floor', 10, 10, (0, 0), (1, 1)))
    # porphyry basin
    m.merge(lathe([(0, 0), (1.0, 0), (1.3, 0.5), (1.1, 0.8), (2.25, 1.1), (2.3, 1.35), (2.1, 1.35), (0, 1.0)], 48, mat='porphyry'))
    # niches with statues + pilasters between
    for k in range(10):
        a = 2 * math.pi * (k + 0.5) / 10
        c = np.array([r * math.cos(a), r * math.sin(a)]); nrm = -c / r
        g = niche(3.2, 7.4, 1.2, 'marble_dark')
        m.merge(g.transformed(frame((c[0], c[1], 0.8), (-nrm[1], nrm[0], 0), (-nrm[0], -nrm[1], 0), (0, 0, 1))))
        key = ['doryphoros', 'baptist', 'polyhymnia', 'christ', 'pudicitia'][k % 5]
        p = c + nrm * 0.4
        m.merge(ST.place(key, p[0], p[1], 0.8, 4.4 if key != 'doryphoros' else 4.0, math.atan2(nrm[1], nrm[0]) + math.pi / 2, lod=1,
                         mat='gilt_bronze' if k == 0 else 'statue_marble'))
        b = 2 * math.pi * k / 10
        pc = np.array([r * math.cos(b), r * math.sin(b)]); pn = -pc / r
        Fp = frame((pc[0], pc[1], 0), (-pn[1], pn[0], 0), (-pn[0], -pn[1], 0), (0, 0, 1))
        m.merge(pilaster(1.0, 10.4, 0.25, 'corinthian', 'marble_white', cap_mat='marble_white').transformed(Fp))
    R.info.append(dict(key='rotonda_basin', pos=(0, 0, 1.6)))
    R.view(*[(x, y, z) for x in np.arange(-8, 8.1, 2) for y in np.arange(-8, 8.1, 2) if x * x + y * y < 80 for z in (1.6, 6, 12, 15, 17, 19)
             if z < zs or x * x + y * y < (r * r - (z - zs) ** 2) - 2.0])
    R.light((0, 0, H + 0.6), (3.2, 3.2), 5000.0, rot=(math.pi, 0, 0), color=(1.0, 0.97, 0.92))
    R.light((0, 0, 9.0), (12, 12), 1500.0, rot=(math.pi, 0, 0))
    R.box = dict(u0=-r, u1=r, v0=-r, v1=r, z0=-0.5, z1=H + 1.5)
    return R

def seam_unwrap(m, period):
    for fi, uv in enumerate(m.UV):
        if uv is None: continue
        us = [p[0] for p in uv]
        if max(us) - min(us) > period / 2:
            m.UV[fi] = [((p[0] + period) if p[0] < period / 2 else p[0], p[1]) for p in uv]
    return m

def sala_muse(origin, rot):
    """Hall of the Muses: octagonal hall with 16 columns, painted cupola (Conca), the Belvedere Torso in the centre,
    muses and herms in the bays."""
    R = Room('muse', origin, rot)
    m = R.m; r = 8.0; zs = 8.5; H = 14.5
    oc = [(r * math.cos(math.pi / 8 + k * math.pi / 4), r * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]
    for k in range(8):
        A, B = np.array(oc[k]), np.array(oc[(k + 1) % 8]); L = np.linalg.norm(B - A); d = (B - A) / L
        m.merge(art_quad((A[0], A[1], 0), (d[0], d[1], 0), (0, 0, 1), L, zs, 'muse_wall', 6, 4, (0, 0), (L / 3.0, 1)))
        for t in (0.18, 0.82):
            p = A + (B - A) * t; nrm = -(A + B) / np.linalg.norm(A + B)
            m.merge(column(0.7, 7.0, 'corinthian', 'marble_grey', cap_mat='marble_white', seg=16).transformed(mat4((p[0] + nrm[0] * 0.9, p[1] + nrm[1] * 0.9, 0))))
        c = (A + B) / 2; nrm = -c / np.linalg.norm(c)
        key = ['polyhymnia', 'pudicitia', 'niobid', 'polyhymnia', 'ecclesia', 'pudicitia', 'niobid', 'polyhymnia'][k]
        m.merge(box(c[0] + nrm[0] * 0.6 - 0.6, c[1] + nrm[1] * 0.6 - 0.6, 0, c[0] + nrm[0] * 0.6 + 0.6, c[1] + nrm[1] * 0.6 + 0.6, 0.9, 'marble_grey'))
        m.merge(ST.place(key, c[0] + nrm[0] * 0.6, c[1] + nrm[1] * 0.6, 0.9, 2.1, math.atan2(nrm[1], nrm[0]) + math.pi / 2, lod=1, mat='statue_marble'))
    # entablature ring and the cupola with the painted ceiling
    m.merge(lathe([(r, 7.0), (r - 1.0, 7.0), (r - 1.0, 8.5), (r, 8.5)], 8, a0=math.pi / 8, a1=math.pi / 8 + 2 * math.pi, mat='marble_white'))
    dome = lathe([(r * math.cos(t), zs + (H - zs) * math.sin(t)) for t in np.linspace(0, math.pi / 2, 10)], 32, mat='art:muse_ceiling')
    for fi in range(len(dome.F)):
        dome.UV[fi] = [(0.5 + dome.V[v][0] / (2 * r), 0.5 + dome.V[v][1] / (2 * r)) for v in dome.F[fi]]
    m.merge(dome)
    m.merge(art_quad((-r, -r, 0), (1, 0, 0), (0, 1, 0), 2 * r, 2 * r, 'stanza_floor', 6, 6, (0, 0), (2 * r / 3.5, 2 * r / 3.5)))
    m.merge(box(-0.9, -0.7, 0, 0.9, 0.7, 1.0, 'marble_dark'))
    m.merge(ST.place('torso', 0, 0, 1.0, 1.59, 0.0, lod=0, mat='statue_marble'))
    R.info.append(dict(key='torso', pos=(0, 0, 1.8)))
    R.view(*[(x, y, z) for x in np.arange(-6, 6.1, 1.5) for y in np.arange(-6, 6.1, 1.5) if x * x + y * y < 42 for z in (1.6, 5, 9, 11, 13)
             if z < zs or (x * x + y * y) / (r * r) + ((z - zs) / (H - zs)) ** 2 < 0.85])
    R.light((0, 0, H - 0.6), (6, 6), 3500.0, rot=(math.pi, 0, 0))
    R.box = dict(u0=-r, u1=r, v0=-r, v1=r, z0=-0.5, z1=H + 0.5)
    return R

# =============================================================================== Pinacoteca (Raphael room)
def pinacoteca(origin, rot):
    R = Room('pinacoteca', origin, rot)
    m = R.m; a, b, H = 7.0, 6.0, 8.5
    m.merge(art_quad((-a, -b, 0), (1, 0, 0), (0, 1, 0), 2 * a, 2 * b, 'pina_floor', 6, 6, (0, 0), (2 * a / 2.0, 2 * b / 2.0)))
    # walls (fabric), skylight velarium ceiling
    for corner, right, w in (((-a, b, 0), (1, 0, 0), 2 * a), ((a, -b, 0), (-1, 0, 0), 2 * a), ((a, b, 0), (0, -1, 0), 2 * b), ((-a, -b, 0), (0, 1, 0), 2 * b)):
        m.merge(art_quad(corner, right, (0, 0, 1), w, H - 1.5, 'pina_wall', 8, 4, (0, 0), (w / 2.0, 1)))
        c = np.array(corner, float); rr = np.array(right, float)
        q = [c + [0, 0, H - 1.5], c + rr * w + [0, 0, H - 1.5]]
        inner = [np.array([q[1][0] * 0.82, q[1][1] * 0.82, H]), np.array([q[0][0] * 0.82, q[0][1] * 0.82, H])]
        o = m.add_v([q[0], q[1], inner[0], inner[1]]); m.face([o, o + 1, o + 2, o + 3], STUCCO)
    m.merge(cap([[(-a * 0.82, -b * 0.82), (a * 0.82, -b * 0.82), (a * 0.82, b * 0.82), (-a * 0.82, b * 0.82)]], H, 'velarium', True))
    # paintings: Transfiguration centre of the end wall (N), Foligno and Oddi on the side walls
    def painting(cx, cy, right, key, w, h, z0):
        r_ = np.array(right, float); p0 = np.array([cx, cy, z0]) - r_ * w / 2
        n = np.cross(r_, [0, 0, 1])          # toward the room
        m.merge(art_quad(tuple(p0 + n * 0.08), r_, (0, 0, 1), w, h, key, 6, 8))
        fr = 0.22
        F = frame(tuple(p0 + n * 0.04 - r_ * fr + [0, 0, -fr]), r_, -n, (0, 0, 1))
        g = Mesh()
        g.merge(box(0, -0.1, 0, w + 2 * fr, 0.06, fr, GOLD)); g.merge(box(0, -0.1, h + fr, w + 2 * fr, 0.06, h + 2 * fr, GOLD))
        g.merge(box(0, -0.1, fr, fr, 0.06, h + fr, GOLD)); g.merge(box(w + fr, -0.1, fr, w + 2 * fr, 0.06, h + fr, GOLD))
        m.merge(g.transformed(F))
        R.info.append(dict(key=key, pos=(cx + n[0] * 3, cy + n[1] * 3, z0 + h / 2)))
    painting(0, b, (1, 0, 0), 'transfiguration', 2.78, 4.05, 1.0)
    painting(-a, 0, (0, 1, 0), 'foligno', 1.94, 3.2, 1.2)
    painting(a, 0, (0, -1, 0), 'oddi', 1.9, 2.67, 1.4)
    painting(0, -b, (-1, 0, 0), 'entombment', 2.03, 3.0, 1.3)
    R.view(*grid_points(-a + 0.8, a - 0.8, -b + 0.8, b - 0.8, (1.6, 4.5, 7.5), 1.5))
    R.light((0, 0, H - 0.1), (2 * a * 0.8, 2 * b * 0.8), 3200.0, rot=(math.pi, 0, 0), color=(1.0, 0.98, 0.95))
    R.box = dict(u0=-a, u1=a, v0=-b, v1=b, z0=-0.5, z1=H + 0.5)
    return R

# =============================================================================== Momo spiral staircase
def momo(origin, rot):
    """Giuseppe Momo's double-helix ramp (1932): two intertwined helical ramps in a cylindrical well under a glass
    dome, bronze balustrade with ornament on the inner edge."""
    R = Room('momo', origin, rot, exposure=0.85)
    m = R.m; Rw = 8.2; Ri = 4.6; Hh = 16.0; turns = 2.0; wdt = Rw - Ri - 0.15
    nseg = 160
    for h in range(2):
        ph = h * math.pi
        for i in range(nseg):
            t0, t1 = i / nseg, (i + 1) / nseg
            a0, a1 = ph + t0 * turns * 2 * math.pi, ph + t1 * turns * 2 * math.pi
            z0, z1 = Hh * (1 - t0), Hh * (1 - t1)
            for (r0, r1, mat) in ((Ri + 0.05, Rw - 0.1, 'momo_ramp'),):
                q = [(r0 * math.cos(a0), r0 * math.sin(a0), z0), (r1 * math.cos(a0), r1 * math.sin(a0), z0),
                     (r1 * math.cos(a1), r1 * math.sin(a1), z1), (r0 * math.cos(a1), r0 * math.sin(a1), z1)]
                o = m.add_v(q); m.face([o, o + 1, o + 2, o + 3], 'marble_grey', False)
                q2 = [(p[0], p[1], p[2] - 0.45) for p in q]
                o = m.add_v(q2); m.face([o + 3, o + 2, o + 1, o], 'stucco_white', False)
                # inner fascia
                qa = [(r0 * math.cos(a0), r0 * math.sin(a0), z0 - 0.45), (r0 * math.cos(a1), r0 * math.sin(a1), z1 - 0.45), (r0 * math.cos(a1), r0 * math.sin(a1), z1), (r0 * math.cos(a0), r0 * math.sin(a0), z0)]
                o = m.add_v(qa); m.face([o, o + 1, o + 2, o + 3], 'stucco_white', False)
            # bronze balustrade: ornamental panel band + rail on the inner edge
            rb = Ri + 0.1
            qa = [(rb * math.cos(a0), rb * math.sin(a0), z0), (rb * math.cos(a1), rb * math.sin(a1), z1), (rb * math.cos(a1), rb * math.sin(a1), z1 + 1.0), (rb * math.cos(a0), rb * math.sin(a0), z0 + 1.0)]
            o = m.add_v(qa); m.face([o, o + 1, o + 2, o + 3], 'art:momo_rail', False, [(t0 * 60, 0), (t1 * 60, 0), (t1 * 60, 1), (t0 * 60, 1)])
            o = m.add_v(qa); m.face([o + 3, o + 2, o + 1, o], 'art:momo_rail', False, [(t0 * 60, 0), (t0 * 60, 1), (t1 * 60, 1), (t1 * 60, 0)][::-1][::-1])
        path = [((Ri + 0.1) * math.cos(ph + t * turns * 2 * math.pi), (Ri + 0.1) * math.sin(ph + t * turns * 2 * math.pi), Hh * (1 - t) + 1.0) for t in np.linspace(0, 1, 121)]
        m.merge(sweep([(-0.07, -0.02), (0.07, -0.02), (0.07, 0.07), (-0.07, 0.07)], path, 'bronze', smooth=True))
    # outer well wall, floor, glass dome
    wall = lathe([(Rw, Hh + 3.0), (Rw, -0.5)], 64, mat='momo_wall')      # profiles reversed: faces point into the well
    m.merge(wall)
    m.merge(lathe([(Rw, -0.45), (0, -0.45)], 48, mat='marble_grey'))
    dome = lathe([(Rw * math.cos(t), Hh + 3.0 + 3.5 * math.sin(t)) for t in np.linspace(0, math.pi / 2, 10)], 48, mat='glass_dome')
    m.merge(dome)
    for k in range(24):
        a = 2 * math.pi * k / 24
        path = [(Rw * 0.995 * math.cos(t) * math.cos(a), Rw * 0.995 * math.cos(t) * math.sin(a), Hh + 3.0 + 3.5 * math.sin(t)) for t in np.linspace(0, math.pi / 2 * 0.97, 10)]
        m.merge(sweep_normal([(-0.08, 0), (-0.08, -0.15), (0.08, -0.15), (0.08, 0)], path, (0, 0), 'iron'))
    def clear_of_ramps(r_, a, z):     # viewpoints inside a ramp slab would vote its faces inside out
        if not (Ri - 0.3 < r_ < Rw + 0.1): return True
        for h in range(2):
            for k in range(-1, 3):
                t = ((a - h * math.pi) % (2 * math.pi) + 2 * math.pi * k) / (turns * 2 * math.pi)
                if 0 <= t <= 1 and Hh * (1 - t) - 0.9 < z < Hh * (1 - t) + 0.4: return False
        return True
    R.view(*[(r_ * math.cos(a), r_ * math.sin(a), z) for r_ in (0.5, 2.5, 4.0, 6.4, 7.5) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)
             for z in np.arange(0.8, Hh + 6.0, 1.8) if clear_of_ramps(r_, a, z)])
    R.light((0, 0, Hh + 6.0), (7, 7), 60000.0, rot=(math.pi, 0, 0), color=(0.95, 0.98, 1.0))
    for k in range(6):
        a = 2 * math.pi * k / 6
        R.light((6.0 * math.cos(a), 6.0 * math.sin(a), Hh + 4.5), (3, 3), 8000.0, rot=(math.pi, 0, 0), color=(0.95, 0.98, 1.0))
    R.box = dict(u0=-Rw, u1=Rw, v0=-Rw, v1=Rw, z0=-1.0, z1=Hh + 7.0)
    R.info.append(dict(key='momo', pos=(0, 0, 8.0)))
    return R

# =============================================================================== Cortile della Pigna (exterior)
def pigna_court(base, rot):
    """Bramante/Ligorio's Nicchione at the north end of the Cortile della Pigna with the bronze pine cone,
    the two peacocks and the double stair; returns a world-space mesh for the exterior zone."""
    m = Mesh()
    W = 26.0; H = 28.0; nr = 6.4; nd = 4.8
    # façade with the great niche (local: x right, facade plane y=0 facing -y, niche recessing to +y)
    holes = [opening_shape(2 * nr, 18.5 + nr, 'arch', x=W / 2 - nr, y=0.0)]
    m.merge(wall(W, H, 3.0, 'stucco_ochre', holes, M=mat4((-W / 2, 0, 0)), back=False, top=True))
    g = niche(2 * nr, 18.5 + nr, nd, 'stucco_white')
    m.merge(g.transformed(mat4((0, 0, 0))))
    # coffered conch look comes from the texture-less stucco; add the semicircular loggia at the top
    m.merge(lathe([(nr + 2.2, H), (nr + 2.2, H + 1.0), (0, H + 1.0)], 24, a0=math.pi, a1=2 * math.pi, mat='travertine', center=(0, 0, 0)))
    m.merge(balustrade(-W / 2, W / 2, H, 1.3, 0.6, 'travertine', y=-0.6, bal_seg=6))
    for x in (-W / 2 + 1.0, -nr - 1.6, nr + 1.6, W / 2 - 1.0):
        m.merge(pilaster(1.6, 18.0, 0.4, 'corinthian', 'travertine').transformed(mat4((x, 0, 0))))
    m.merge(straight(cornice_profile(1.4, 1.0), -W / 2, W / 2, 18.0, -0.4, 'travertine'))
    # terrace + double stair in front, the giant capital and the pine cone
    m.merge(box(-8.0, -9.0, 0, 8.0, 0, 3.6, 'travertine'))
    m.merge(balustrade(-8.0, 8.0, 3.6, 1.0, 0.45, 'travertine', y=-9.0, bal_seg=6))
    for sx in (-1, 1):
        for i in range(12):
            z = 3.6 * (1 - i / 12)
            m.merge(box(sx * 8.0 + (sx * 0.5 * i if True else 0), -9.0 + 0.6 * i * 0 - 0.0, 0, sx * (8.0 + 0.55 * (i + 1)), -0.5, z, 'travertine'))
    m.merge(box(-1.6, -3.4, 3.6, 1.6, -0.2, 4.4, 'marble_white'))
    m.merge(corinthian_capital(1.3, 2.6, 'marble_white', 24).transformed(mat4((0, -1.8, 4.4))))
    pine = []
    for t in np.linspace(0, 1, 14):
        r = 1.45 * math.sin(math.pi * (0.08 + 0.92 * t)) ** 0.75 * (1 - 0.35 * t)
        pine.append((r, t * 4.0))
    pine.append((0, 4.05))
    pc = lathe(pine, 28, mat='bronze_green')
    V = np.array(pc.V)
    ang = np.arctan2(V[:, 1], V[:, 0]); rr = np.hypot(V[:, 0], V[:, 1])
    bump = 1 + 0.07 * np.sin(ang * 13 + V[:, 2] * 9)
    V[:, 0] = rr * bump * np.cos(ang); V[:, 1] = rr * bump * np.sin(ang)
    pc.V = V.tolist()
    m.merge(pc.transformed(mat4((0, -1.8, 7.0))))
    for sx in (-1, 1):   # peacocks (simplified bronze bodies with fanned tails folded)
        body = lathe([(0, 0), (0.35, 0.1), (0.4, 0.5), (0.25, 0.9), (0.12, 1.3), (0.15, 1.5), (0, 1.6)], 10, mat='bronze_green')
        m.merge(body.transformed(mat4((sx * 3.6, -4.0, 3.6))))
        tail = sweep([(-0.3, 0), (0.3, 0), (0.25, 0.08), (-0.25, 0.08)], [(sx * 3.6, -4.0 + 0.2, 3.9), (sx * 3.6, -4.0 + 1.6, 3.65)], 'bronze_green')
        m.merge(tail)
    # courtyard lawn quadrants and gravel paths (south of the niche)
    for (x0, x1) in ((-30, -2), (2, 30)):
        for (y0, y1) in ((-95, -52), (-48, -12)):
            m.merge(box(x0, y0, -0.15, x1, y1, 0.05, 'lawn', faces=('+z',)))
    m.merge(box(-32, -100, -0.3, 32, -10, -0.02, 'gravel', faces=('+z',)))
    zb = terrain.height(base[0], base[1])
    return m.transformed(mat4((base[0], base[1], zb), rz=rot))

# =============================================================================== assembly
def rooms():
    out = []
    # positions near the real ones (world metres, see notes): floors above the local ground
    out += raphael_rooms((-214.0, 131.0, 18.0), 0.0)
    out.append(gallery_of_maps((-262.0, 205.0, 13.0), 0.0))
    out.append(ottagono((-205.0, 488.0, terrain.height(-205, 488)), math.radians(-3)))
    out.append(sala_muse((-182.0, 461.0, terrain.height(-182, 461)), 0.0))
    out.append(sala_rotonda((-170.0, 490.0, terrain.height(-170, 490)), 0.0))
    out.append(pinacoteca((-369.0, 395.0, terrain.height(-369, 395) + 0.6), math.radians(90)))
    out.append(momo((-330.0, 468.0, terrain.height(-330, 468) - 2.0), 0.0))
    return out

if __name__ == '__main__':
    import bpy
    from vb import bl
    outp = sys.argv[sys.argv.index('--') + 1]
    only = [a[5:] for a in sys.argv if a.startswith('room=')]
    bl.clear_scene()
    rs = [r for r in rooms() if not only or r.name in only[0].split(',')]
    for r in rs:
        print(r.name, r.m.count())
        bl.to_object(r.m, r.name)
    bl.setup_world()
    r = rs[0]
    for L in r.lights:
        ld = bpy.data.lights.new('l', 'AREA'); ld.shape = 'RECTANGLE'; ld.size, ld.size_y = L['size']; ld.energy = L['energy']
        lo = bpy.data.objects.new('l', ld); bpy.context.scene.collection.objects.link(lo); lo.location = L['p']; lo.rotation_euler = L['rot']
    vp = [a[3:] for a in sys.argv if a.startswith('vp=')]
    cams = json.loads(vp[0]) if vp else [[[0, -3, 1.6], [0, 3, 4], 18]]
    for i, (p, t, lens) in enumerate(cams):
        bl.camera(p, t, lens); bl.render(outp + f'-{r.name}-{i}.jpg', 1200, 700, 32)
