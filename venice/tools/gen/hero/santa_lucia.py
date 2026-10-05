"""Stazione di Venezia Santa Lucia: the 1952-54 front (Paolo Perilli and Virgilio Vallot) on the Fondamenta Santa Lucia.
The generic OSM `building:part`s give the massing behind it; this hero models what you meet walking along the fondamenta or
arriving over the Ponte degli Scalzi:

  * the central hall, 52 m wide and 20 m above the street: one huge glazed wall of tall panes (23 bays of 1.96 m, 11 m high)
    between thin dark mullions and transoms, set 1 m back between two 3.5 m stone piers; above the glass a plain stone band
    carries FERROVIE DELLO STATO in 18 separate bronze capitals (glyph outlines of Liberation Sans Bold with the holes of
    A, O, R and D, 1.2 m tall, 8 cm deep, 25.7 m of text); over it a 50 cm roof slab projects 2.5 m as a deep cornice and
    floats on a dark shadow line;
  * behind the glass a bright interior 9 m deep (terrazzo floor, cream walls and ceiling, a gallery, three gates in the back
    wall, a departures board) whose fittings are `street_glass` (emissive in the night bake only): 15 long ceiling
    fixtures, 4 bars on the board, 12 lights under the canopy; the hall glows and spills light on the forecourt;
  * two two-storey wings of 35.5 m, 12 m high: continuous ribbon windows between thin mullions with one transom, stone plinth,
    spandrel and parapet bands, a thin flat-roof cornice (35 cm, 55 cm out);
  * the long cantilevered canopy: a 24 cm slab 3.2 m above the forecourt, 52 m long and 5.5 m deep, over a glass door in every
    other bay (11 doors) and fixed panes in the others;
  * the forecourt raised 1.04 m on a stone podium (52 x 12.5 m) and the scalinata: eight 13 cm risers and 45 cm treads, the
    full width of the hall, down to the fondamenta; the walk heights run through the middle of every riser.

The viewer's `glass` is an opaque dark mirror (citymat.js has no transparency), so the panes above the canopy are left open
(only mullions and transoms) and the lit interior shows through; the ground-floor panes are glass flagged "lit at night"
(c1.w = 200) like the city's lit windows, and so are part of the wings' ribbons.

Frame (measured on the OSM parts, see check()): the station front is the SE edge of the 12 m ring p817230929, from
A = (-1424.6, 737.6) to B = (-1358.7, 819.9) (105.4 m, 51.3 degrees from the x axis).  u runs along it from A (SW to NE), v
is the outward normal toward the Grand Canal (SE), z is absolute (water 0, street GROUND_Z 1.1).  The shore is a straight
line at v = 48.5 (u 24..95), so the fondamenta stays 33 m wide beyond the foot of the steps (v = 15.65).  Kit frame of the
meshes: x = u, y = -v (into the building), z up, so a facade faces -y as in vk/arch.py.

  u -17.55 .. 18     SW wing       u 18 .. 70  hall: its axis u = 44 is where OSM maps the footway and the steps to the doors
  u 70 .. 105.55     NE wing       (43.9), half way between the side passages OSM maps at u = 17 and 69, and near the middle of
                                   the hall roof block p817230934 (18.7 .. 71.9, 53 m); the masses are 20 m deep (back wall at v = -20)
The NE end stays at the OSM ring's end (105.4: houses and the church of the Scalzi stand 8-14 m beyond it) and the SW end is
the mirror image about the hall's axis, so the front is 123 m long with wings of 35.5 m (the real front is 120-140 m): the SW
wing runs 9 m beyond the OSM ring and porch strip (u = -8.7) over open ground.

OSM parts (setup): p817230934 (the hall's roof block) is hidden; the hall footprint is carved out of p817230928 and
p817230929 (the 12 m ring falls in two, the SW piece becomes p817230929_s1); the 5 m deep porch strip of p817230931 and
the 'roof' box w138842242 in front of the NE wing are removed; the remaining parts get a hero_cut along the front line
and stone walls.  Nothing generic stays inside the hall, on the forecourt or in front of the facade (check()).

Registration in gen/hero/__init__.py:
    from . import ..., santa_lucia
    santa_lucia.setup(world)                                                          (inside setup(world))
    HEROES.append((santa_lucia.ANCHOR, lambda mb, inst: santa_lucia.build(mb)))
    walk_areas() += santa_lucia.walk_areas()
Regenerate the tiles t_9_11, t_10_11, t_10_12 (meshes, bake, walk rasters).
python -m gen.hero.santa_lucia prints the checks, --png renders the previews to /tmp/claude-1000/, --glyphs ABC traces more
capitals with fontTools (the build venv has no matplotlib)."""
import math
import numpy as np
from shapely.geometry import Polygon, LineString
from vk import geom as G
from ..world import GROUND_Z, polys_of, h32
from .common import place

GZ = GROUND_Z

# ================================================================================================ frame
_A = np.array([-1424.6, 737.6]); _B = np.array([-1358.7, 819.9])
D = (_B - _A) / np.linalg.norm(_B - _A)            # along the front, SW -> NE
N = np.array([D[1], -D[0]])                        # outward, toward the Grand Canal (SE)


def xy(u, v):
    p = _A + D * u + N * v
    return (float(p[0]), float(p[1]))


def uv_of(x, y):
    q = np.array([x, y]) - _A
    return float(q @ D), float(q @ N)


def rect(u0, u1, v0, v1):
    return Polygon([xy(u0, v0), xy(u1, v0), xy(u1, v1), xy(u0, v1)])


KIT = G.frame((_A[0], _A[1], 0.0), (D[0], D[1], 0.0), (-N[0], -N[1], 0.0), (0.0, 0.0, 1.0))      # kit (x = u, y = -v, z) -> world

# ================================================================================================ dimensions
U_SW, U_NE = -17.55, 105.55                        # ends of the front: symmetric about the hall's axis, which OSM maps at u = 43.9 (footway and steps)
U_H0, U_H1 = 18.0, 70.0                            # the hall (the OSM hall roof block p817230934 spans 18.7 .. 71.9)
UC = 0.5 * (U_H0 + U_H1)                           # 44.0
DEP = 20.0                                         # depth of the masses behind the front line
PIER = 3.5                                         # hall piers
NSTEP, RISER, TREAD = 8, 0.13, 0.45                # the scalinata
ZF = GZ + NSTEP * RISER                            # forecourt 2.14
PV = 12.5                                          # top riser of the scalinata (v from the front)
V_FOOT = PV + (NSTEP - 1) * TREAD                  # foot of the steps 15.65
# hall
V_GL = -1.0                                        # glass plane (recessed behind the piers)
Z_CAN = ZF + 3.2                                   # canopy soffit 5.34
CAN_T, CAN_V = 0.24, 4.5                           # canopy slab thickness, projection beyond the front line
Z_GL = 16.4                                        # head of the glazing
Z_RF0, Z_RF1 = 20.6, GZ + 20.0                     # roof slab 20.6 .. 21.1
SHADOW = 0.18                                      # dark joint between the facade and the slab above it
NBAY = 23                                          # glazed bays between the piers
V_BACK = -10.0                                     # back wall of the interior
# wings: storeys relative to the street
Z_PL = 1.9                                         # plinth top
Z_G0 = (1.9, 6.9)                                  # sills of the two ribbons
Z_G1 = (5.2, 10.8)                                 # heads
Z_TOP = GZ + 12.0                                  # 13.1 top of the parapet band
Z_CORN = 0.35                                      # cornice slab

ANCHOR = xy(UC, 8.0)                               # tile t_10_11 (9 m inside it)

ME = 2.4                                           # longest face diagonal handed to the builder (see gc_bridges)


# ================================================================================================ small geometry kit
def _split(a, b, me):
    if a * a + b * b <= me * me: return 1, 1
    if b <= 0.5 * me: return max(1, math.ceil(a / math.sqrt(max(me * me - b * b, (0.3 * me) ** 2)))), 1
    if a <= 0.5 * me: return 1, max(1, math.ceil(b / math.sqrt(max(me * me - a * a, (0.3 * me) ** 2))))
    k = me / math.sqrt(2.0)
    return max(1, math.ceil(a / k)), max(1, math.ceil(b / k))


def _uv(p, n):
    """texture coordinates in metres from the kit position: stone and paving keep their joints square to the building."""
    ax, ay, az = abs(n[0]), abs(n[1]), abs(n[2])
    if az >= ax and az >= ay: return (p[0], p[1])
    if ay >= ax: return (p[0], p[2])
    return (p[1], p[2])


def _quad(m, pts, want, mat):
    """planar polygon (3 or 4 points, kit coordinates) wound so that its normal agrees with `want`."""
    P = np.asarray(pts, float)
    n = np.cross(P[2] - P[0], P[3] - P[1]) if len(P) == 4 else np.cross(P[1] - P[0], P[2] - P[0])
    if np.linalg.norm(n) < 1e-12: return
    if np.dot(n, want) < 0: P = P[::-1]; n = -n
    n = n / np.linalg.norm(n)
    m.poly([tuple(p) for p in P], mat, False, [_uv(p, n) for p in P])


def _face(m, pts, want, mat, me=ME):
    """quad p00-p10-p11-p01 cut into cells whose diagonals stay within `me` (the builder would otherwise cut thin faces
    into many more triangles than they need)."""
    p00, p10, p11, p01 = (np.asarray(p, float) for p in pts)
    a = max(np.linalg.norm(p10 - p00), np.linalg.norm(p11 - p01)); b = max(np.linalg.norm(p01 - p00), np.linalg.norm(p11 - p10))
    nu, nv = _split(a, b, me)
    def P(x, y): return (1 - x) * (1 - y) * p00 + x * (1 - y) * p10 + x * y * p11 + (1 - x) * y * p01
    for i in range(nu):
        for j in range(nv):
            x0, x1, y0, y1 = i / nu, (i + 1) / nu, j / nv, (j + 1) / nv
            _quad(m, [P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)], want, mat)


def _poly(m, pts, want, mat):
    """planar polygon of any shape (earcut)."""
    P = np.asarray(pts, float)
    keep = [i for i in range(3) if i != int(np.argmax(np.abs(want)))]
    for (a, b, c) in G.tess([[(p[keep[0]], p[keep[1]]) for p in P]]):
        _quad(m, [P[a], P[b], P[c]], want, mat)


_FACES = ('+v', '-v', '-u', '+u', '+z', '-z')


def box(m, u0, u1, v0, v1, z0, z1, mat, skip=(), me=ME):
    """axis-aligned box in (u, v, z); faces '+v' (toward the canal), '-v', '-u', '+u', '+z', '-z'; mat is a name or a dict
    {face: name, '*': default}."""
    def L(u, v, z): return (u, -v, z)
    F = {'+v': ([L(u0, v1, z0), L(u1, v1, z0), L(u1, v1, z1), L(u0, v1, z1)], (0, -1, 0)),
         '-v': ([L(u0, v0, z0), L(u1, v0, z0), L(u1, v0, z1), L(u0, v0, z1)], (0, 1, 0)),
         '-u': ([L(u0, v0, z0), L(u0, v1, z0), L(u0, v1, z1), L(u0, v0, z1)], (-1, 0, 0)),
         '+u': ([L(u1, v0, z0), L(u1, v1, z0), L(u1, v1, z1), L(u1, v0, z1)], (1, 0, 0)),
         '+z': ([L(u0, v0, z1), L(u1, v0, z1), L(u1, v1, z1), L(u0, v1, z1)], (0, 0, 1)),
         '-z': ([L(u0, v0, z0), L(u1, v0, z0), L(u1, v1, z0), L(u0, v1, z0)], (0, 0, -1))}
    for k in _FACES:
        if k in skip: continue
        mm = mat if isinstance(mat, str) else mat.get(k, mat.get('*'))
        _face(m, F[k][0], F[k][1], mm, me)


def vquad(m, u0, u1, v0, v1, z0, z1, want, mat, me=ME):
    """vertical (or any) rectangle between two (u, v) points at heights z0..z1; want = (du, dv, dz) outward."""
    def L(u, v, z): return (u, -v, z)
    _face(m, [L(u0, v0, z0), L(u1, v1, z0), L(u1, v1, z1), L(u0, v0, z1)], (want[0], -want[1], want[2]), mat, me)


def hquad(m, u0, u1, v0, v1, z, up, mat, me=ME):
    """horizontal rectangle at height z facing up (True) or down."""
    def L(u, v, zz): return (u, -v, zz)
    _face(m, [L(u0, v0, z), L(u1, v0, z), L(u1, v1, z), L(u0, v1, z)], (0, 0, 1 if up else -1), mat, me)


# ================================================================================================ lettering
# Liberation Sans Bold capitals, outlines flattened from the font (glyph units: 1/1000 em, cap height 688, y up);
# traced once with fontTools (matplotlib's TextPath is not installed in the build venv): [outer ring, hole rings...]
_SPACE = 278
_GLYPHS = {
    'F': (611, ['211 577 211 364 563 364 563 252 211 252 211 0 67 0 67 688 574 688 574 577']),
    'E': (667, ['67 0 67 688 608 688 608 577 211 577 211 404 578 404 578 292 211 292 211 111 628 111 628 0']),
    'R': (722, ['540 0 380 261 211 261 211 0 67 0 67 688 411 688 469 685 520 675 564 658 601 635 630 606 651 570 663 530 667 465 657 416 636 372 604 334 564 307 516 289 702 0', '522 477 520 500 505 537 491 551 451 570 396 576 211 576 211 373 399 373 453 380 483 394 505 415 518 443']),
    'O': (778, ['736 347 730 270 712 201 682 138 642 86 591 45 531 15 463 -4 387 -10 311 -4 243 14 183 44 133 86 93 138 64 199 47 269 41 347 47 425 64 495 93 555 133 605 183 646 243 675 311 692 388 698 465 692 534 675 593 646 644 604 684 553 713 493 730 425', '589 347 586 400 576 446 559 487 522 537 491 560 454 576 411 584 343 581 302 569 268 550 239 522 216 488 199 447 189 400 186 347 189 294 200 246 216 204 240 169 269 140 323 113 365 105 411 105 454 112 491 128 523 152 549 184 576 244 586 292']),
    'V': (667, ['407 0 261 0 7 688 157 688 299 246 335 116 370 246 511 688 660 688']),
    'I': (278, ['67 0 67 688 211 688 211 0']),
    'D': (722, ['680 349 678 298 670 249 657 205 638 163 615 126 588 93 556 65 520 42 460 16 393 3 67 0 67 688 316 688 398 683 470 666 532 639 585 600 607 577 643 524 667 461 674 426', '535 349 532 401 513 467 491 503 446 544 408 562 363 573 211 577 211 111 333 111 377 115 416 127 451 147 493 192 514 230 527 273']),
    'L': (611, ['67 0 67 688 211 688 211 111 580 111 580 0']),
    'S': (667, ['628 198 623 151 617 129 599 90 586 73 553 44 533 31 487 11 401 -6 333 -10 270 -7 215 2 167 17 108 50 64 96 43 135 29 179 168 202 189 155 204 137 223 123 272 104 337 98 403 104 450 121 467 134 478 150 485 168 488 190 485 210 475 233 461 247 436 263 390 280 193 330 139 356 102 386 82 414 71 441 63 471 61 506 71 570 79 588 100 621 150 660 193 679 244 691 303 697 366 698 447 688 510 668 542 647 580 605 598 569 610 526 470 507 463 528 448 554 418 579 374 593 301 595 252 585 220 564 203 533 203 495 219 466 256 441 298 428 484 381 519 368 555 348 588 318 611 282 625 239']),
    'T': (611, ['377 577 377 0 233 0 233 577 11 577 11 688 600 688 600 577']),
    'A': (722, ['553 0 492 176 230 176 169 0 25 0 276 688 446 688 696 0', '361 582 262 284 460 284 392 482']),
}
_CAP = 688.0
FERROVIE = 'FERROVIE DELLO STATO'


def _loops(ch):
    adv, rings = _GLYPHS[ch]
    out = []
    for r in rings:
        v = [int(t) for t in r.split()]
        out.append(list(zip(v[0::2], v[1::2])))
    return adv, out


def text_loops(text, track=0.12):
    """[(x offset in glyph units, loops)] for `text` and its total width (glyph units); track in em."""
    x = 0.0; out = []
    for ch in text:
        if ch == ' ': x += _SPACE + 1000 * track; continue
        adv, loops = _loops(ch)
        out.append((x, loops)); x += adv + 1000 * track
    return out, x - 1000 * track


def lettering(m, text, uc, z0, v_plane, height=1.2, depth=0.08, track=0.12, mat='bronze'):
    """separate capitals of the given cap height standing on the wall plane v = v_plane, centred on u = uc, baseline z0:
    each letter is a prism of its outline (holes in A, O, R, D) pointing out of the wall."""
    s = height / _CAP
    glyphs, width = text_loops(text, track)
    x0 = uc - width * s / 2
    M = G.frame((0.0, -v_plane, z0), (1, 0, 0), (0, 0, 1), (0, -1, 0))       # letter (x, y, out) -> kit (u, -v, z)
    for (gx, loops) in glyphs:
        L = [[(x0 + (gx + px) * s, py * s) for (px, py) in ring] for ring in loops]
        m.merge(G.prism(L, 0.0, depth, mat, top=True, bottom=False), M)
    return width * s


def trace_glyphs(chars, font='/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', tol=5.0):
    """the text of _GLYPHS entries for `chars`, flattened from a font file with fontTools (pip install fonttools): outlines in
    1/1000 em, rings simplified to `tol` font units, outer ring first and the holes (A, O, R, D) after it.
    python -m gen.hero.santa_lucia --glyphs ABC [font.ttf]"""
    from fontTools.ttLib import TTFont
    from fontTools.pens.basePen import BasePen
    class Flat(BasePen):
        def __init__(self, gs): super().__init__(gs); self.rings = []; self.cur = None
        def _moveTo(self, p): self.cur = [p]
        def _lineTo(self, p): self.cur.append(p)
        def _curveToOne(self, a, b, c):
            p0 = self.cur[-1]; self.cur += [tuple((1 - t) ** 3 * np.array(p0) + 3 * (1 - t) ** 2 * t * np.array(a) + 3 * (1 - t) * t * t * np.array(b) + t ** 3 * np.array(c)) for t in np.linspace(0, 1, 11)[1:]]
        def _qCurveToOne(self, a, b):
            p0 = self.cur[-1]; self.cur += [tuple((1 - t) ** 2 * np.array(p0) + 2 * (1 - t) * t * np.array(a) + t * t * np.array(b)) for t in np.linspace(0, 1, 9)[1:]]
        def _closePath(self):
            if self.cur and len(self.cur) > 2: self.rings.append(self.cur)
            self.cur = None
        _endPath = _closePath
    f = TTFont(font); gs = f.getGlyphSet(); cmap = f.getBestCmap(); upm = f['head'].unitsPerEm
    lines = [f"# cap height {round(f['OS/2'].sCapHeight * 1000 / upm)}, space {round(gs[cmap[32]].width * 1000 / upm)}"]
    for ch in chars:
        pen = Flat(gs); gs[cmap[ord(ch)]].draw(pen)
        rings = [r[:-1] if math.dist(r[0], r[-1]) < 1e-6 else r for r in pen.rings]
        polys = [Polygon(r) for r in rings]
        depth = [sum(1 for j, q in enumerate(polys) if j != i and q.area > p.area and q.contains(p.representative_point())) for i, p in enumerate(polys)]
        out = []
        for i in sorted(range(len(rings)), key=lambda i: (depth[i] % 2, -polys[i].area)):
            pts = [(round(x * 1000 / upm), round(y * 1000 / upm)) for x, y in list(polys[i].simplify(tol, preserve_topology=True).exterior.coords)[:-1]]
            q = [pts[0]] + [b for a, b in zip(pts[:-1], pts[1:]) if a != b]
            out.append("'" + ' '.join(f'{x} {y}' for x, y in (q[:-1] if q[0] == q[-1] else q)) + "'")
        lines.append(f"    '{ch}': ({round(gs[cmap[ord(ch)]].width * 1000 / upm)}, [{', '.join(out)}]),")
    return '\n'.join(lines)


# ================================================================================================ the parts of one build
class Parts:
    """one Mesh per treatment: the builder subdivides faces to `max_edge`, so cells are cut here to a size that suits each."""
    def __init__(self):
        self.F = G.Mesh()          # stone, steps, frames: cells up to ME
        self.C = G.Mesh()          # big plain faces (roofs, back walls, the interior): cells up to 5 m
        self.T = G.Mesh()          # thin members (mullions, transoms): long cells
        self.LIT = G.Mesh()        # glass panes that glow at night (flag 200)
        self.LAMP = G.Mesh()       # street_glass fittings (emissive in the night bake only)
        self.STEEL = G.Mesh()      # bright steel (flag 12): push bars


def pane(m, u0, u1, z0, z1, v):
    vquad(m, u0, u1, v, v, z0, z1, (0, 1, 0), 'glass', me=7.0)


# ================================================================================================ forecourt and scalinata
def step_profile():
    """(v, z) outline of the stepped side of the podium: platform at ZF to v = PV, then seven treads and the last riser."""
    prof = [(PV, ZF)]
    for j in range(1, NSTEP):
        z = ZF - j * RISER
        prof += [(PV + (j - 1) * TREAD, z), (PV + j * TREAD, z)]
    prof += [(V_FOOT, GZ)]
    return prof


def platform(P):
    m = P.F
    hquad(m, U_H0, U_H1, 0.0, PV, ZF, True, 'portico_floor')
    hquad(m, U_H0 + PIER, U_H1 - PIER, V_GL, 0.0, ZF, True, 'portico_floor')          # the recess in front of the doors
    for j in range(1, NSTEP + 1):                                                      # eight risers, seven treads
        v = PV + (j - 1) * TREAD
        vquad(m, U_H0, U_H1, v, v, ZF - j * RISER, ZF - (j - 1) * RISER, (0, 1, 0), 'istrian')
        if j < NSTEP: hquad(m, U_H0, U_H1, v, v + TREAD, ZF - j * RISER, True, 'istrian')
    zb = GZ - 0.06
    outline = [(0.0, zb), (0.0, ZF), (PV, ZF)] + step_profile()[1:] + [(V_FOOT, zb)]
    for u, s in ((U_H0, -1), (U_H1, 1)):                                               # stone cheeks closing the podium and the steps
        _poly(m, [(u, -v, z) for (v, z) in outline], (s, 0, 0), 'istrian')


# ================================================================================================ the hall
def hall(P):
    F, C = P.F, P.C
    ua, ub = U_H0 + PIER, U_H1 - PIER
    # front: two piers and the band above the glass, all in the plane of the wings' fronts (v = 0)
    zs = Z_RF0 - SHADOW
    vquad(F, U_H0, ua, 0, 0, ZF, zs, (0, 1, 0), 'istrian')
    vquad(F, ub, U_H1, 0, 0, ZF, zs, (0, 1, 0), 'istrian')
    vquad(F, ua, ub, 0, 0, Z_GL, zs, (0, 1, 0), 'istrian')
    vquad(F, U_H0, U_H1, -0.12, -0.12, zs, Z_RF0, (0, 1, 0), 'dark', me=8.0)              # the slab floats on a dark shadow line
    hquad(F, U_H0, U_H1, -0.12, 0.0, zs, True, 'istrian', me=8.0)
    box(F, ua, ub, 0.0, 0.14, Z_GL, Z_GL + 0.30, 'trim', skip=('-v',))                  # architrave under the band
    # the glass stands 1 m back: soffit and jambs of that reveal
    hquad(F, ua, ub, V_GL, 0.0, Z_GL, False, 'istrian')
    vquad(F, ua, ua, V_GL, 0.0, ZF, Z_GL, (1, 0, 0), 'istrian')
    vquad(F, ub, ub, V_GL, 0.0, ZF, Z_GL, (-1, 0, 0), 'istrian')
    # the mass: side walls above the wings, back wall
    vquad(C, U_H0, U_H0, 0, -DEP, 13.0, Z_RF0, (-1, 0, 0), 'istrian', me=5.0)
    vquad(C, U_H1, U_H1, 0, -DEP, 13.0, Z_RF0, (1, 0, 0), 'istrian', me=5.0)
    vquad(C, U_H0, U_H1, -DEP, -DEP, GZ - 0.05, Z_RF0, (0, -1, 0), 'istrian', me=5.0)
    # the roof slab: thin, projecting 2.5 m over the front as a deep cornice, 0.9 m at the sides
    r0, r1, rv0, rv1 = U_H0 - 0.9, U_H1 + 0.9, -DEP - 0.4, 2.5
    box(F, r0, r1, rv0, rv1, Z_RF0, Z_RF1, 'istrian', skip=('+z', '-z'))
    hquad(C, r0, r1, rv0, rv1, Z_RF1, True, 'flat_roof', me=5.0)
    hquad(F, r0, r1, 0.0, rv1, Z_RF0, False, 'istrian')                                 # soffit of the front overhang
    hquad(F, r0, U_H0, rv0, 0.0, Z_RF0, False, 'istrian'); hquad(F, U_H1, r1, rv0, 0.0, Z_RF0, False, 'istrian')
    hquad(F, U_H0, U_H1, rv0, -DEP, Z_RF0, False, 'istrian')
    lettering(F, FERROVIE, UC, 17.95, 0.0)


def canopy(P):
    F = P.F
    box(F, U_H0, U_H1, V_GL, CAN_V - 0.3, Z_CAN, Z_CAN + CAN_T, {'+z': 'flat_roof', '*': 'trim'}, skip=('-v', '+v'))
    box(F, U_H0, U_H1, CAN_V - 0.3, CAN_V, Z_CAN, Z_CAN + 0.44, {'+z': 'flat_roof', '*': 'trim'}, skip=('-v',))
    # a row of long lights under it (emissive at night)
    n = 12; ua, ub = U_H0 + PIER, U_H1 - PIER; pitch = (ub - ua) / n
    for i in range(n):
        uc = ua + (i + 0.5) * pitch
        hquad(P.LAMP, uc - 0.8, uc + 0.8, 1.8, 2.2, Z_CAN - 0.01, False, 'street_glass', me=16.0)


def glazing(P):
    """23 bays of tall panes: thin dark mullions and transoms on the glass plane; glass doors in every other bay under the
    canopy.  The panes above the canopy are left open (the viewer's glass is an opaque dark mirror) so the lit hall shows."""
    T, F, LIT, ST = P.T, P.F, P.LIT, P.STEEL
    ua, ub = U_H0 + PIER, U_H1 - PIER
    bw = (ub - ua) / NBAY
    MW, MD = 0.09, 0.30
    rows = [Z_CAN + (Z_GL - Z_CAN) * k / 3 for k in range(4)]
    for k in range(1, NBAY):                                                            # mullions from the forecourt to the head
        u = ua + k * bw
        box(T, u - MW / 2, u + MW / 2, V_GL - MD / 2, V_GL + MD / 2, ZF, Z_GL, 'cast_iron', skip=('-v', '-z', '+z'), me=4.6)
    for r in (1, 2):
        box(T, ua, ub, V_GL - MD / 2, V_GL + MD / 2, rows[r] - 0.06, rows[r] + 0.06, 'cast_iron', skip=('-v', '-u', '+u'), me=4.6)
    box(T, ua, ub, V_GL - MD / 2, V_GL + MD / 2, Z_GL - 0.14, Z_GL, 'cast_iron', skip=('-v', '-u', '+u', '+z'), me=4.6)
    # ground floor under the canopy
    zd = ZF + 2.5                                                                      # door height, a transom light above
    for i in range(NBAY):
        u0, u1 = ua + i * bw, ua + (i + 1) * bw
        door = i % 2 == 1
        box(T, u0, u1, V_GL - 0.08, V_GL + 0.08, zd, zd + 0.1, 'cast_iron', skip=('-v', '-u', '+u'), me=4.6)   # transom bar
        pane(LIT, u0 + 0.045, u1 - 0.045, zd + 0.1, Z_CAN, V_GL)
        if not door:
            box(T, u0 + 0.045, u1 - 0.045, V_GL - 0.08, V_GL + 0.08, ZF, ZF + 0.45, 'cast_iron', skip=('-v', '-u', '+u', '-z'), me=4.6)
            pane(LIT, u0 + 0.045, u1 - 0.045, ZF + 0.45, zd, V_GL)
        else:
            uc = 0.5 * (u0 + u1)
            box(T, uc - 0.03, uc + 0.03, V_GL - 0.08, V_GL + 0.08, ZF, zd, 'cast_iron', skip=('-v', '-z', '+z'), me=4.6)
            for a, b, s in ((u0 + 0.045, uc - 0.03, -1), (uc + 0.03, u1 - 0.045, 1)):
                box(T, a, b, V_GL - 0.08, V_GL + 0.08, ZF, ZF + 0.32, 'cast_iron', skip=('-v', '-u', '+u', '-z'), me=4.6)    # kick plate
                for ue in (a, b - 0.06):                                                # leaf stiles
                    box(T, ue, ue + 0.06, V_GL - 0.08, V_GL + 0.08, ZF + 0.32, zd, 'cast_iron', skip=('-v', '-z', '+z'), me=4.6)
                pane(LIT, a + 0.06, b - 0.06, ZF + 0.32, zd, V_GL)
                ph = uc + s * 0.14                                                      # push bar beside the meeting stile
                box(ST, min(ph, ph + s * 0.7), max(ph, ph + s * 0.7), V_GL + 0.07, V_GL + 0.10, ZF + 1.0, ZF + 1.03, 'metal', skip=('-v',), me=4.0)


def interior(P):
    """the hall behind the glass: terrazzo floor, cream walls and ceiling, a back wall with three gates and a gallery,
    long fittings under the ceiling (street_glass)."""
    C, F, T, LAMP = P.C, P.F, P.T, P.LAMP
    ua, ub = U_H0 + PIER, U_H1 - PIER
    v0 = V_GL
    hquad(C, ua, ub, V_BACK, v0, ZF, True, 'terrazzo', me=4.0)
    hquad(C, ua, ub, V_BACK, v0, Z_GL, False, 'cream', me=4.0)
    vquad(C, ua, ub, V_BACK, V_BACK, ZF, Z_GL, (0, 1, 0), 'cream', me=3.6)
    vquad(C, ua, ua, V_BACK, v0, ZF, Z_GL, (1, 0, 0), 'cream', me=4.0)
    vquad(C, ub, ub, V_BACK, v0, ZF, Z_GL, (-1, 0, 0), 'cream', me=4.0)
    # three gates in the back wall, with stone architraves
    for k in (-1, 0, 1):
        uc = UC + 12.0 * k
        box(F, uc - 3.0, uc + 3.0, V_BACK, V_BACK + 0.2, ZF, ZF + 8.4, 'trim', skip=('-v', '-z'), me=4.0)
        vquad(F, uc - 2.5, uc + 2.5, V_BACK + 0.21, V_BACK + 0.21, ZF, ZF + 7.9, (0, 1, 0), 'dark', me=8.0)
    # the gallery along the back wall, at the second transom
    zg = Z_CAN + (Z_GL - Z_CAN) / 3
    box(F, UC - 19.0, UC + 19.0, V_BACK + 0.0, V_BACK + 3.2, zg - 0.3, zg, 'trim', skip=('-v',))
    for u in np.linspace(UC - 19.0, UC + 19.0, 26):
        box(T, u - 0.025, u + 0.025, V_BACK + 3.1, V_BACK + 3.17, zg, zg + 0.95, 'cast_iron', skip=('-v', '-z', '+z'), me=4.0)
    box(T, UC - 19.0, UC + 19.0, V_BACK + 3.05, V_BACK + 3.2, zg + 0.95, zg + 1.0, 'cast_iron', skip=('-v', '-u', '+u'), me=4.6)
    # the departures board hanging in the middle of the hall: a dark slab on four rods with four lines of amber text bars
    bu0, bu1, bv, bz0, bz1 = UC - 5.5, UC + 5.5, -6.0, 11.4, 13.4
    box(F, bu0, bu1, bv - 0.15, bv + 0.15, bz0, bz1, 'dark', me=8.0)
    for u in (bu0 + 0.8, bu1 - 0.8):
        for dv in (-0.1, 0.1): box(T, u - 0.02, u + 0.02, bv + dv - 0.02, bv + dv + 0.02, bz1, Z_GL, 'cast_iron', skip=('-z', '+z'), me=6.0)
    for k in range(4):
        z = bz1 - 0.35 - k * 0.42
        vquad(LAMP, bu0 + 0.5, bu1 - 0.5, bv + 0.16, bv + 0.16, z, z + 0.14, (0, 1, 0), 'street_glass', me=16.0)
    # fittings: 3 rows of 5 long fixtures under the ceiling
    for vr in (-3.2, -5.8, -8.4):
        for k in range(-2, 3):
            uc = UC + 9.0 * k
            box(T, uc - 3.55, uc + 3.55, vr - 0.25, vr + 0.25, Z_GL - 0.14, Z_GL, 'cast_iron', skip=('-z', '+z'), me=8.0)
            hquad(LAMP, uc - 3.5, uc + 3.5, vr - 0.2, vr + 0.2, Z_GL - 0.15, False, 'street_glass', me=16.0)


# ================================================================================================ the wings
def wing(P, ua, ub, hall_at_ub):
    F, C, T, LIT = P.F, P.C, P.T, P.LIT
    PW, DPT = 1.4, 0.3
    gu0, gu1 = ua + PW, ub - PW
    nb = max(1, int(round((gu1 - gu0) / 1.6))); bw = (gu1 - gu0) / nb
    so, si = ('-u', '+u') if hall_at_ub else ('+u', '-u')       # the outer end (the end wall closes it) and the end at the hall pier
    # stone front: plinth, the spandrel between the floors, the parapet band and an end pier of every storey
    box(F, ua, ub, -DPT, 0.0, GZ - 0.05, Z_PL, 'istrian', skip=('-v', '-z', so, si))
    box(F, ua, ub, -DPT, 0.0, Z_G1[0], Z_G0[1], 'istrian', skip=('-v', so, si))
    box(F, ua, ub, -DPT, 0.0, Z_G1[1], Z_TOP - 0.12, 'istrian', skip=('-v', so, si))
    vquad(F, ua, ub, -0.1, -0.1, Z_TOP - 0.12, Z_TOP, (0, 1, 0), 'dark', me=8.0)
    outer_pier, hall_pier = ((ua, gu0), (gu1, ub)) if hall_at_ub else ((gu1, ub), (ua, gu0))
    for s in (0, 1):
        box(F, *outer_pier, -DPT, 0.0, Z_G0[s], Z_G1[s], 'istrian', skip=('-v', '+z', '-z', so))
        box(F, *hall_pier, -DPT, 0.0, Z_G0[s], Z_G1[s], 'istrian', skip=('-v', '+z', '-z', si))
    # the ribbons: thin mullions every ~1.6 m, one transom, panes 20 cm behind the front plane
    for s in (0, 1):
        z0, z1 = Z_G0[s], Z_G1[s]; zt = z0 + 0.74 * (z1 - z0)
        for k in range(1, nb):
            u = gu0 + k * bw
            box(T, u - 0.035, u + 0.035, -0.22, -0.04, z0, z1, 'cast_iron', skip=('-v', '-z', '+z'), me=4.6)
        box(T, gu0, gu1, -0.22, -0.04, zt - 0.03, zt + 0.03, 'cast_iron', skip=('-v', '-u', '+u'), me=4.6)
        for k in range(nb):
            a, b = gu0 + k * bw + 0.035, gu0 + (k + 1) * bw - 0.035
            for (p0, p1, tag) in ((z0, zt - 0.03, 'lo'), (zt + 0.03, z1, 'hi')):
                lit = h32('sl', round(ua), s, k, tag) < (0.5 if tag == 'lo' else 0.3)
                pane(LIT if lit else F, a, b, p0, p1, -0.2)
    # cornice: a thin slab projecting 55 cm at the front and at the outer end
    ea, eb = (0.55, 0.0) if hall_at_ub else (0.0, 0.55)        # the outer end is ua on the SW wing, ub on the NE wing
    c0, c1, cv0, cv1 = ua - ea, ub + eb, -DEP, 0.55
    skip = ['+z', '-z'] + (['+u'] if hall_at_ub else ['-u'])
    box(F, c0, c1, cv0, cv1, Z_TOP, Z_TOP + Z_CORN, 'istrian', skip=tuple(skip))
    hquad(C, c0, c1, cv0, cv1, Z_TOP + Z_CORN, True, 'flat_roof', me=5.0)
    hquad(F, c0, c1, 0.0, cv1, Z_TOP, False, 'istrian')
    if hall_at_ub: hquad(F, c0, ua, cv0, 0.0, Z_TOP, False, 'istrian')
    else: hquad(F, ub, c1, cv0, 0.0, Z_TOP, False, 'istrian')
    uh = ub if hall_at_ub else ua                                                       # the overhang's end face next to the hall pier
    vquad(F, uh, uh, 0.0, cv1, Z_TOP, Z_TOP + Z_CORN, (1 if hall_at_ub else -1, 0, 0), 'istrian')
    # the outer end wall and the back wall (plain stone)
    uo = ua if hall_at_ub else ub
    vquad(C, uo, uo, 0, -DEP, GZ - 0.05, Z_TOP, (-1 if hall_at_ub else 1, 0, 0), 'istrian', me=5.0)
    vquad(C, ua, ub, -DEP, -DEP, GZ - 0.05, Z_TOP, (0, -1, 0), 'istrian', me=5.0)


def build(mb):
    P = Parts()
    platform(P); hall(P); canopy(P); glazing(P); interior(P)
    wing(P, U_SW, U_H0, True)
    wing(P, U_H1, U_NE, False)
    place(mb, P.F, KIT, max_edge=ME * 1.05)
    place(mb, P.C, KIT, max_edge=5.2)
    place(mb, P.T, KIT, max_edge=4.8)
    place(mb, P.LIT, KIT, c1=(0, 0, 77, 200), max_edge=7.5)
    place(mb, P.LAMP, KIT, max_edge=17.0)
    place(mb, P.STEEL, KIT, c1=(0, 0, 0, 12), max_edge=4.2)
    return dict(height=Z_RF1)


# ================================================================================================ the OSM parts behind the front
# the generic parts: p817230928 the 7 m body, p817230929 the 12 m ring (the wings), p817230931 the 7 m porch strip with the SW lobes
HALL_BLOCK = 'p817230934'                                   # the 3 m block that stands on the body as the hall's roof: inside my hall
CANOPY_BOX = 'w138842242'                                   # 15.8 x 14.6 m 'roof' box in front of the NE wing (OSM building=roof)
UNBLOCK = rect(77.7, 93.9, 0.2, 14.8)                       # its footprint, walkable again


def front_cut():
    return LineString([xy(U_SW - 3.0, 0.0), xy(U_NE + 3.0, 0.0)])


def _carve(world, b, hole):
    """cut `hole` out of b's footprint.  Pieces beyond the largest become new buildings that copy b."""
    from ..world import Building
    rest = [p for p in polys_of(b.poly.difference(hole)) if p.area > 2.0]
    if not rest:
        b.hero = True; return [b]
    rest.sort(key=lambda p: -p.area)
    b.poly = rest[0]
    out = [b]
    for k, p in enumerate(rest[1:], 1):
        c = Building(f'{b.id}_s{k}', b.tags, p)
        for a in ('seed', 'kind', 'H', 'levels', 'z0', 'roof', 'roof_h', 'parent', 'pmat', 'hero_cut'): setattr(c, a, getattr(b, a))
        world.buildings.append(c); out.append(c)
    return out


def setup(world):
    """call once before the tiles are generated (gen/hero/__init__.py setup): hide what stands inside my masses, carve the
    hall footprint and the porch strip out of the generic parts, mark their fronts as replaced, give them stone walls."""
    B = {b.id: b for b in world.buildings}
    if HALL_BLOCK in B: B[HALL_BLOCK].hero = True
    # the 'roof' box goes altogether: a hidden building would still keep the paving off its footprint
    if CANOPY_BOX in B: world.buildings[:] = [b for b in world.buildings if b.id != CANOPY_BOX]
    cut = front_cut()
    mine = []
    if 'p817230928' in B: mine += _carve(world, B['p817230928'], rect(U_H0, U_H1, -DEP, 1.2))
    if 'p817230929' in B: mine += _carve(world, B['p817230929'], rect(U_H0, U_H1, -DEP, 1.2))
    if 'p817230931' in B: mine += _carve(world, B['p817230931'], rect(U_SW - 1.5, U_H1 + 6.0, -0.35, 7.0))
    for b in mine:
        b.hero_cut = (getattr(b, 'hero_cut', None) or []) + [cut]
        b.pmat = {**(b.pmat or {}), 'wall': 'wall_stone'}
    return [b.id for b in mine]


# ================================================================================================ walking
def step_ramp():
    """the scalinata as a ramp along v through the middle of every riser (never more than half a riser off a tread)."""
    pts = [(PV - 0.3, ZF)] + [(PV + (j - 1) * TREAD, ZF - (j - 0.5) * RISER) for j in range(1, NSTEP + 1)] + [(V_FOOT + 0.3, GZ)]
    a = xy(UC, 0.0)
    return {'a': [a[0], a[1]], 'd': [float(N[0]), float(N[1])], 'prof': [(round(v, 3), round(z, 3)) for v, z in pts]}


def walk_areas():
    """[(polygon, z)]: the masses blocked first, then the forecourt, the recess in front of the doors, the steps (ramp) and the
    footprint of the removed canopy box (walkable again)."""
    return [(rect(U_SW - 0.3, U_NE + 0.3, -DEP - 0.4, 0.0), None),
            (UNBLOCK, GZ),
            (rect(U_H0, U_H1, 0.0, PV + 0.35), ZF),
            (rect(U_H0 + PIER + 0.05, U_H1 - PIER - 0.05, V_GL + 0.2, 0.35), ZF),
            (rect(U_H0, U_H1, PV - 0.3, V_FOOT + 0.3), step_ramp())]


# ================================================================================================ measurement
def _tile(x, y): return int((x + 3400.0) // 200.0), int((y + 1600.0) // 200.0)


def check(world=None):
    """re-measure the placement against the OSM parts and w.land, count triangles, rasterise the walk areas with the real
    gen.walk.raster and walk lines from the fondamenta up the steps to the doors (needs the world cache)."""
    from shapely.geometry import box as sbox, Point
    from shapely.ops import unary_union
    from .. import walk as WALK
    from ..mesh import MeshBuilder
    from ..city import Classifier, gen_building
    from . import gc_bridges
    from ..world import load
    if world is None: world = load()
    old = {b.id: _tile(b.poly.centroid.x, b.poly.centroid.y) for b in world.buildings}
    hid = setup(world)
    # ---- the front against the OSM parts and the water
    ring = next(b for b in world.buildings if b.id == 'p817230929')
    vs = [uv_of(*c)[1] for c in ring.poly.exterior.coords if abs(uv_of(*c)[1]) < 0.3]
    print(f'front: OSM ring front vertices at v = {min(vs):.2f}..{max(vs):.2f} m (frame fitted to them); hall {U_H1 - U_H0:.0f} m, wings {U_H0 - U_SW:.1f} + {U_NE - U_H1:.1f} m, whole front {U_NE - U_SW:.1f} m')
    sh = [world.land.boundary.distance(Point(*xy(u, V_FOOT))) for u in np.linspace(U_H0, U_H1, 11)]
    print(f'fondamenta between the foot of the steps (v = {V_FOOT:.2f}) and the water: {min(sh):.1f}..{max(sh):.1f} m (needs >= 4)')
    # ---- mesh
    mb = MeshBuilder(); r = build(mb); A = mb.arrays()
    T = A['P'][A['I']].astype(np.float64); area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    nlet = len(FERROVIE.replace(' ', '')); zr = (A['P'][:, 2].min(), A['P'][:, 2].max())
    print(f'build: {r}, {len(A["P"])} vertices, {mb.ntri()} triangles ({int((area < 1e-7).sum())} degenerate), z {zr[0]:.2f}..{zr[1]:.2f}, '
          f'{nlet} letters; anchor {tuple(round(c, 1) for c in ANCHOR)} in tile {_tile(*ANCHOR)}')
    mass = unary_union([rect(U_SW, U_NE, -DEP, 0.0), rect(U_H0, U_H1, 0.0, V_FOOT), rect(U_H0, U_H1, V_GL, CAN_V)])
    others = unary_union([b.poly for b in world.buildings if not (b.parent == 'w138841071' or b.id.startswith('p8172309') or b.id.startswith('w1388422'))])
    print(f'my masses, podium and canopy ({mass.area:.0f} m2) overlap other OSM buildings by {mass.intersection(others).area:.2f} m2 and the water by {mass.difference(world.land).area:.2f} m2')
    # ---- generic facades that survive next to the front (hero_cut must have removed the ones on it)
    cl = Classifier(world); fac = []; mbx = MeshBuilder()
    for bi, b in enumerate(world.buildings):
        if b.id in hid and not b.hero: gen_building(world, cl, b, mbx, fac, bi)
    mids = [Point(*(0.5 * (np.array(f['p0']) + np.array(f['p1'])))) for f in fac]
    stray = [m_ for m_ in mids if abs(uv_of(m_.x, m_.y)[1]) < 2.0 and U_SW - 3 < uv_of(m_.x, m_.y)[0] < U_NE + 3 and not mass.buffer(0.1).contains(m_)]
    print(f'generic facades left on the carved parts: {len(fac)}, on the front line and not inside my masses: {len(stray)}')
    # ---- walk
    blockers = [b.poly for b in world.buildings if b.z0 < GZ + 2.0]
    bl = unary_union(blockers)
    for (p, z), name in zip(walk_areas(), ('mass block', 'unblock', 'forecourt', 'recess', 'steps')):
        print(f'  {name:10s}: {p.area:7.1f} m2' + ('' if z is None else f', over water {p.difference(world.land).area:.2f} m2, in buildings {p.intersection(bl).area:.1f} m2' + (' (the removed canopy box)' if name == 'unblock' else '')))
    for (p, z) in gc_bridges.walk_areas():
        if any(p.intersects(q) for q, zz in walk_areas()): print('  OVERLAPS a gc_bridges walk area')
    cx, cy = xy(UC, 10.0); R = sbox(cx - 80, cy - 80, cx + 80, cy + 80)
    rgb = WALK.raster(world, R, [b for b in blockers if b.intersects(R)], WALK.Passages(world), [], walk_areas() + gc_bridges.walk_areas())
    Wr = rgb[..., 0].astype(int); x0, y1 = R.bounds[0], R.bounds[3]
    def zat(x, y):
        c = Wr[int((y1 - y) / WALK.RES), int((x - x0) / WALK.RES)]; return None if c == 0 else (c - 1) * 0.04 - 1.0
    worst = 0.0; blocked = 0; n = 0
    for u in np.linspace(U_H0 + 0.3, U_H1 - 0.3, 41):
        door = U_H0 + PIER + 0.4 < u < U_H1 - PIER - 0.4
        zs = [zat(*xy(u, v)) for v in np.arange(42.0, -0.55 if door else 0.2, -0.25)]
        blocked += sum(z is None for z in zs); n += 1
        zz = [z for z in zs if z is not None]; worst = max(worst, max(abs(b - a) for a, b in zip(zz[:-1], zz[1:])))
    print(f'walk: {n} lines from the fondamenta (v = 42) up the steps to the doors, largest height jump between neighbouring 0.25 m pixels {worst:.2f} m, blocked pixels on them {blocked}')
    print('  heights over the steps at the middle (v: z):', ' '.join(f'{v:.2f}:{zat(*xy(UC, v)):.2f}' for v in np.arange(16.5, 11.9, -0.5)))
    print(f'  z at the doors (v = -0.5): {zat(*xy(UC, -0.5)):.2f}; blocked in the glass line (v = -0.95): {zat(*xy(UC, -0.95)) is None}; fondamenta at v = 20: {zat(*xy(UC, 20.0)):.2f}')
    # ---- tiles
    chg = {}
    for b in world.buildings:
        if b.id in hid or b.id in (HALL_BLOCK, CANOPY_BOX):
            chg.setdefault(_tile(b.poly.centroid.x, b.poly.centroid.y), []).append(b.id)
            if b.id in old: chg.setdefault(old[b.id], []).append(b.id + ' (before)')
    wt = set()
    for p, z in walk_areas():
        a, b_, c, d = p.bounds
        wt |= {(i, j) for i in range(_tile(a, b_)[0], _tile(c, d)[0] + 1) for j in range(_tile(a, b_)[1], _tile(c, d)[1] + 1)}
    print('tiles: hero mesh', _tile(*ANCHOR), '; buildings changed', {k: v for k, v in sorted(chg.items())}, '; walk rasters', sorted(wt))
    res = dict(fondamenta_4m=min(sh) >= 4.0, under_80k_triangles=mb.ntri() < 80000, no_degenerate_triangles=int((area < 1e-7).sum()) == 0, steps_smooth=worst <= 0.5,
               no_blocked_pixels=blocked == 0, no_overlap_with_buildings=mass.intersection(others).area < 0.5, on_land=mass.difference(world.land).area < 0.05, no_stray_facades=not stray)
    print('checks:', 'all pass' if all(res.values()) else 'FAILED ' + ', '.join(k for k, v in res.items() if not v))
    return world


# ================================================================================================ previews (numpy z-buffer + PIL, no GPU)
def _mat_rgb():
    from ..materials import MATS
    pal = {'istrian': (.70, .67, .60), 'trim': (.70, .67, .60), 'flat_roof': (.30, .29, .27), 'portico_floor': (.52, .49, .44), 'ground': (.26, .25, .23),
           'glass': (.02, .028, .04), 'cast_iron': (.03, .03, .03), 'metal': (.55, .55, .56), 'street_glass': (1, .74, .46), 'cream': (.74, .68, .55),
           'terrazzo': (.45, .36, .30), 'dark': (.02, .02, .02), 'bronze': (.12, .09, .06)}
    return np.array([pal.get(n, a) for (n, l, k, a) in MATS], float), [n for (n, *_r) in MATS]


def _context(world, centre, radius):
    """roofs from the real gen_building, walls from its facade descriptors (flat, no openings): the generic buildings as the pipeline makes them."""
    from ..city import Classifier, gen_building
    from ..mesh import MeshBuilder
    rgb, names = _mat_rgb()
    cl = Classifier(world); mbc = MeshBuilder(); fac = []
    for bi, b in enumerate(world.buildings):
        c = b.poly.centroid
        if not b.hero and math.hypot(c.x - centre[0], c.y - centre[1]) < radius: gen_building(world, cl, b, mbc, fac, bi)
    A = mbc.arrays(); T = [A['P'][A['I']].astype(float)]; mid = A['MAT'][A['I'][:, 0]]
    C = [rgb[mid]]; E = [np.zeros(len(mid), bool)]
    for f in fac:
        p0, p1, zb, zt = np.array(f['p0']), np.array(f['p1']), max(f['zb'], 0.0), f['zt']
        if zt <= zb: continue
        col = rgb[f['mat']].copy()
        if names[f['mat']] == 'wall_plaster': col = (np.array(f['tint']) / 255.0) ** 2.2 * 0.8
        q = np.array([[p0[0], p0[1], zb], [p1[0], p1[1], zb], [p1[0], p1[1], zt], [p0[0], p0[1], zt]])
        if np.dot(np.cross(q[1] - q[0], q[3] - q[0]), [f['n'][0], f['n'][1], 0.0]) < 0: q = q[::-1]
        T.append(np.array([[q[0], q[1], q[2]], [q[0], q[2], q[3]]])); C.append(np.tile(col, (2, 1))); E.append(np.zeros(2, bool))
    return np.concatenate(T), np.concatenate(C), np.concatenate(E)


def _render(T, C, E, world, cam, size=(1280, 720), ss=2, ortho=None, sun_az=150.0, sun_el=48.0):
    """z-buffer over triangles T (n,3,3) with colours C (linear) and emissive flags E; the ground (land at GROUND_Z) and the water are analytic planes."""
    from PIL import Image, ImageDraw
    from shapely.geometry import box as sbox
    W, H = size[0] * ss, size[1] * ss
    eye, tgt = np.array(cam[0], float), np.array(cam[1], float)
    f = tgt - eye; f /= np.linalg.norm(f); r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    tan = math.tan(math.radians(cam[2]) / 2); asp = W / H
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ln = np.linalg.norm(n, axis=1); ok = ln > 1e-12
    T, C, E, n, ln = T[ok], C[ok], E[ok], n[ok], ln[ok]; n /= ln[:, None]
    view = (eye - T.mean(axis=1)) if ortho is None else np.tile(-f, (len(T), 1))
    keep = np.einsum('ij,ij->i', n, view) > 0                                   # back faces are culled: a wrongly wound face shows as a hole
    sun = np.array([math.sin(math.radians(sun_az)) * math.cos(math.radians(sun_el)), math.cos(math.radians(sun_az)) * math.cos(math.radians(sun_el)), math.sin(math.radians(sun_el))])
    col = C * (0.40 + 0.18 * n[:, 2:3] + 0.95 * np.clip(n @ sun, 0, 1)[:, None])
    col = np.where(E[:, None], C * 0.9, col)
    q = T.reshape(-1, 3) - eye; x, y, z = q @ r, q @ u, q @ f
    x, y, z = x.reshape(-1, 3), y.reshape(-1, 3), z.reshape(-1, 3)
    if ortho is None:
        keep &= (z > 0.3).all(axis=1); iz = 1.0 / np.maximum(z, 1e-6)
        sx = (x / z / (tan * asp) * 0.5 + 0.5) * W; sy = (0.5 - y / z / tan * 0.5) * H
    else:
        keep &= (z > 0.1).all(axis=1)
        sx = (x / ortho * 0.5 + 0.5) * W; sy = (0.5 - y / (ortho / asp) * 0.5) * H; iz = z
    zb = np.full((H, W), np.inf, np.float32); cb = np.zeros((H, W, 3), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]; tt = (yy + 0.5) / H
    cb[:] = np.array([.50, .66, .92]) * (1 - tt[..., None]) + np.array([.86, .90, .95]) * tt[..., None]
    if ortho is None:
        dx = ((xx + 0.5) / W * 2 - 1) * tan * asp; dy = (1 - (yy + 0.5) / H * 2) * tan
        D_ = f + dx[..., None] * r + dy[..., None] * u; O_ = np.broadcast_to(eye, D_.shape)
        x0, y0, x1, y1 = eye[0] - 400, eye[1] - 400, eye[0] + 400, eye[1] + 400
        res = 0.5; img = Image.new('L', (int((x1 - x0) / res), int((y1 - y0) / res)), 0); dr = ImageDraw.Draw(img)
        for p in polys_of(world.land.intersection(sbox(x0, y0, x1, y1))):
            dr.polygon([((a - x0) / res, (y1 - b) / res) for a, b in p.exterior.coords], fill=255)
            for h in p.interiors: dr.polygon([((a - x0) / res, (y1 - b) / res) for a, b in h.coords], fill=0)
        mask = np.array(img) > 0
        for (pz, land) in ((0.0, False), (GZ, True)):
            with np.errstate(divide='ignore', invalid='ignore'): t_ = (pz - O_[..., 2]) / D_[..., 2]
            hit = np.isfinite(t_) & (t_ > 0.05) & (t_ < 1500)
            px, py = O_[..., 0] + D_[..., 0] * t_, O_[..., 1] + D_[..., 1] * t_
            i_ = np.clip(((y1 - py) / res).astype(int), 0, mask.shape[0] - 1); j_ = np.clip(((px - x0) / res).astype(int), 0, mask.shape[1] - 1)
            on = mask[i_, j_]; sel = hit & (on if land else ~on)
            zc = t_ * (D_ @ f); upd = sel & (zc < zb)
            colg = (np.array([.30, .28, .25]) * (0.93 + ((np.floor(px / 3) + np.floor(py / 3)) % 2)[..., None] * 0.03) * (sun[2] * 0.95 + 0.45)) if land else np.array([.05, .11, .15]) * (0.7 + 0.3 * (1 - tt[..., None]))
            zb[upd] = zc[upd]; cb[upd] = colg[upd]
    mnx, mxx = np.floor(sx.min(1)).astype(int), np.ceil(sx.max(1)).astype(int); mny, mxy = np.floor(sy.min(1)).astype(int), np.ceil(sy.max(1)).astype(int)
    for k in np.nonzero(keep & (mxx >= 0) & (mnx < W) & (mxy >= 0) & (mny < H))[0]:
        xa, xb, ya, yb = max(mnx[k], 0), min(mxx[k], W - 1), max(mny[k], 0), min(mxy[k], H - 1)
        a0, b0, a1, b1, a2, b2 = sx[k, 0], sy[k, 0], sx[k, 1], sy[k, 1], sx[k, 2], sy[k, 2]
        den = (b1 - b2) * (a0 - a2) + (a2 - a1) * (b0 - b2)
        if abs(den) < 1e-9: continue
        xs = np.arange(xa, xb + 1) + 0.5; ys = (np.arange(ya, yb + 1) + 0.5)[:, None]
        l0 = ((b1 - b2) * (xs - a2) + (a2 - a1) * (ys - b2)) / den; l1 = ((b2 - b0) * (xs - a2) + (a0 - a2) * (ys - b2)) / den; l2 = 1 - l0 - l1
        ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not ins.any(): continue
        d = l0 * iz[k, 0] + l1 * iz[k, 1] + l2 * iz[k, 2]
        if ortho is None: d = 1.0 / np.maximum(d, 1e-9)
        sub = zb[ya:yb + 1, xa:xb + 1]; up = ins & (d < sub - 1e-4)
        if up.any(): sub[up] = d[up]; cb[ya:yb + 1, xa:xb + 1][up] = col[k]
    if ortho is None:
        fg = 1 - np.exp(-np.where(np.isfinite(zb), zb, 3000.0) * 0.0012); cb = cb * (1 - fg[..., None]) + np.array([.75, .80, .86]) * fg[..., None]
    c = np.clip(cb, 0, 1); out = np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
    im = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
    return im.resize(size, Image.LANCZOS) if ss > 1 else im


def _plan(world, path, north_up=True):
    """plan over land, water and buildings with the footprints: north up in world metres (the Scalzi bridge's walk lane is drawn for clearance),
    or in the front frame (u to the right, the canal at the top)."""
    from PIL import Image, ImageDraw, ImageFont
    from shapely.geometry import box as sbox
    from . import gc_bridges
    if north_up: bx = (-1495.0, 715.0, -1245.0, 862.0); scale = 6.5
    else: bx = (-45.0, -48.0, 135.0, 62.0); scale = 9.0
    x0, y0, x1, y1 = bx
    img = Image.new('RGB', (int((x1 - x0) * scale), int((y1 - y0) * scale)), (92, 130, 168)); d = ImageDraw.Draw(img); ft = ImageFont.load_default()
    if north_up: P = lambda x, y: ((x - x0) * scale, (y1 - y) * scale)
    else: P = lambda x, y: ((uv_of(x, y)[0] - x0) * scale, (y1 - uv_of(x, y)[1]) * scale)
    region = sbox(*bx) if north_up else rect(x0 - 100, x1 + 100, y0 - 100, y1 + 100)
    for p in polys_of(world.land.intersection(region)):
        d.polygon([P(*c) for c in p.exterior.coords], fill=(218, 212, 196))
        for h in p.interiors: d.polygon([P(*c) for c in h.coords], fill=(92, 130, 168))
    for b in world.buildings:
        if not b.poly.intersects(region): continue
        col = (176, 160, 148) if b.H < 9 else (150, 128, 116)
        if b.parent == 'w138841071' or b.id.startswith('p8172309'): col = (214, 150, 130)
        if b.hero: col = (185, 185, 185)
        for p in polys_of(b.poly): d.polygon([P(*c) for c in p.exterior.coords], fill=col, outline=(50, 50, 50))
        for l in (b.hero_cut or []): d.line([P(*c) for c in l.coords], fill=(255, 0, 255), width=2)
    outl = [(rect(U_H0, U_H1, -DEP, 0), (200, 0, 0)), (rect(U_SW, U_H0, -DEP, 0), (230, 120, 0)), (rect(U_H1, U_NE, -DEP, 0), (230, 120, 0)),
            (rect(U_H0, U_H1, V_GL, CAN_V), (0, 120, 220)), (rect(U_H0, U_H1, 0, V_FOOT), (0, 160, 60)), (rect(U_H0 + PIER, U_H1 - PIER, V_BACK, V_GL), (120, 0, 200))]
    for poly, col in outl: d.line([P(*c) for c in poly.exterior.coords], fill=col, width=3)
    for k in range(NSTEP): d.line([P(*xy(U_H0, PV + k * TREAD)), P(*xy(U_H1, PV + k * TREAD))], fill=(0, 120, 50), width=1)
    for (poly, z) in gc_bridges.walk_areas()[3:4]: d.line([P(*c) for c in poly.exterior.coords], fill=(0, 0, 160), width=2)       # the Scalzi lane
    if north_up:
        for x in range(int(x0 // 20 * 20), int(x1) + 20, 20): d.line([P(x, y0), P(x, y1)], fill=(150, 150, 150)); d.text(P(x + 1, y0 + 3), str(x), fill=(0, 0, 0), font=ft)
        for y in range(int(y0 // 20 * 20), int(y1) + 20, 20): d.line([P(x0, y), P(x1, y)], fill=(150, 150, 150)); d.text(P(x0 + 2, y + 1), str(y), fill=(0, 0, 0), font=ft)
        o = xy(-6, 14)                                                                  # the u and v axes of the front frame, and north
        d.line([P(*o), P(*xy(8, 14))], fill=(0, 0, 0), width=3); d.text(P(*xy(9, 14)), 'u', fill=(0, 0, 0), font=ft)
        d.line([P(*o), P(*xy(-6, 28))], fill=(0, 0, 0), width=3); d.text(P(*xy(-6, 29)), 'v (to the canal)', fill=(0, 0, 0), font=ft)
        d.line([(30, 70), (30, 30)], fill=(0, 0, 0), width=3); d.text((26, 18), 'N', fill=(0, 0, 0), font=ft)
    else:
        for u in range(int(x0 // 10 * 10), int(x1) + 10, 10): d.line([(( u - x0) * scale, 0), ((u - x0) * scale, (y1 - y0) * scale)], fill=(130, 130, 130)); d.text(((u - x0) * scale + 2, (y1 - y0) * scale - 12), str(u), fill=(0, 0, 0), font=ft)
        for v in range(int(y0 // 10 * 10), int(y1) + 10, 10): d.line([(0, (y1 - v) * scale), ((x1 - x0) * scale, (y1 - v) * scale)], fill=(130, 130, 130)); d.text((2, (y1 - v) * scale), str(v), fill=(0, 0, 0), font=ft)
    for b in world.buildings:
        if b.id.startswith(('p8172309', 'p8172309', 'w1388422')):
            c = b.poly.representative_point(); d.text(P(c.x, c.y), b.id[-5:] + (' hidden' if b.hero else ''), fill=(0, 0, 0), font=ft)
    d.text((60, 4), 'Venezia Santa Lucia. red: hall mass, orange: wings, blue: canopy, green: podium and scalinata (steps drawn), violet: interior, magenta: hero_cut, grey: hidden parts, dark blue: Scalzi walk lane', fill=(0, 0, 0), font=ft)
    img.save(path)


def preview(world=None, prefix='/tmp/claude-1000/santa_lucia'):
    """plan, front elevation, two perspectives from the fondamenta at eye height, one from the Ponte degli Scalzi, plus an aerial and a view up at the doors."""
    from ..mesh import MeshBuilder
    from ..world import load
    from . import gc_bridges
    if world is None: world = load()
    setup(world)
    _plan(world, prefix + '_plan.png'); _plan(world, prefix + '_plan_front.png', north_up=False)
    mb = MeshBuilder(); build(mb)
    mbs = MeshBuilder(); gc_bridges.build_scalzi(mbs)
    rgb, names = _mat_rgb()
    def arr(m):
        A = m.arrays(); I = A['I']; mid = A['MAT'][I[:, 0]]
        return A['P'][I].astype(float), rgb[mid], np.isin(mid, [names.index('street_glass')])
    cx, cy = xy(UC, 0.0)
    Tc, Cc, Ec = _context(world, (cx, cy), 230.0)
    parts = [arr(mb), arr(mbs), (Tc, Cc, Ec)]
    T = np.concatenate([p[0] for p in parts]); C = np.concatenate([p[1] for p in parts]); E = np.concatenate([p[2] for p in parts])
    def at(u, v, z): x, y = xy(u, v); return (x, y, z)
    sca = gc_bridges.SCA; crown = sca.xy(0.0)
    shots = [('elevation', ((*xy(UC, 22.0), 11.0), (*xy(UC, 0.0), 11.0), 50), dict(ortho=68.0, size=(1600, 640))),
             ('persp_fondamenta', (at(36, 40, GZ + 1.6), at(48, 0, 9.0), 68), {}),
             ('persp_fondamenta_oblique', (at(-22, 36, GZ + 1.6), at(48, 0, 8.0), 70), {}),
             ('persp_scalzi', ((crown[0], crown[1], gc_bridges.SCA_ZTOP + 1.6), at(46, 0, 9.0), 38), {}),
             ('persp_doors', (at(33, 9.5, ZF + 1.6), at(44, 0, 7.0), 76), {}),
             ('aerial', (at(58, 92, 70.0), at(46, 0, 8.0), 55), {})]
    for name, cam, kw in shots:
        _render(T, C, E, world, cam, **kw).save(f'{prefix}_{name}.png')
    return [prefix + s for s in ('_plan.png', '_plan_front.png') + tuple(f'_{n}.png' for n, *_r in shots)]


if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    if '--png' in sys.argv: print('\n'.join(preview()))
    elif '--glyphs' in sys.argv:
        i = sys.argv.index('--glyphs'); print(trace_glyphs(sys.argv[i + 1], *sys.argv[i + 2:i + 3]))
    else: check()
