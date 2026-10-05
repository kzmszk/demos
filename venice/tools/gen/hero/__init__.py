"""Hero buildings: setup() adjusts/marks OSM buildings they replace; build(tile_box, mb, inst) adds geometry
for heroes anchored in that tile."""
import numpy as np
from shapely.geometry import Point, LineString
from .common import wf, pf
from . import procuratie, campanile, basilica, basilica_int, rialto, ducale, piazzetta, florian, fenice, piazza_props, gc_bridges, santa_lucia

HEROES = []          # (anchor world xy, builder fn)
# generic OSM bridges replaced by hand-modelled ones: (x, y, radius)
EXCLUDE_BRIDGES = [(float(rialto.C[0]), float(rialto.C[1]), 30.0), (float(ducale.PAG_C[0]), float(ducale.PAG_C[1]), 16.0)] + gc_bridges.EXCLUDE

def setup(world):
    B = {b.id: b for b in world.buildings}
    def adjust(bid, H=None, cut=None, simplify=None):
        b = B.get(bid)
        if b is None: return
        if H is not None: b.H = H; b.levels = 0 if b.levels == 0 else b.levels
        if simplify: b.poly = b.poly.simplify(simplify, preserve_topology=True)
        if cut is not None: b.hero_cut = (getattr(b, 'hero_cut', None) or []) + [LineString(cut)]
    # Procuratie Nuove: piazza facade replaced, building raised to Scamozzi's height
    a, b2 = wf(-142.3, -23.0), wf(-5.7, -18.7)
    adjust('w138803888', H=procuratie.NUOVE['top'], cut=[tuple(a), tuple(b2)], simplify=0.6)
    HEROES.append((tuple((a + b2) / 2), lambda mb, inst: procuratie.build_nuove(mb)))
    # Procuratie Vecchie (north side) and the Ala Napoleonica (west end)
    a, b2 = wf(*procuratie.VECCHIE_LINE[0]), wf(*procuratie.VECCHIE_LINE[1])
    adjust('w410344923', H=procuratie.VECCHIE['frieze_top'], cut=[tuple(a), tuple(b2)], simplify=0.6)
    HEROES.append((tuple((a + b2) / 2), lambda mb, inst: procuratie.build_vecchie(mb)))
    a, b2 = wf(-142.2, -23.0), wf(-142.2, 37.0)
    adjust('w410344936', H=procuratie.NUOVE['f1_top'] + 5.4, cut=[tuple(a), tuple(b2)], simplify=0.6)
    HEROES.append((tuple((a + b2) / 2), lambda mb, inst: procuratie.build_napoleonica(mb)))
    # Campanile + Loggetta replace their OSM footprints completely
    for bid in ('w252637693', 'w252637694'):
        if bid in B: B[bid].hero = True
    HEROES.append((tuple(wf(0.0, 0.0)), lambda mb, inst: campanile.build(mb)))
    # Palazzo Ducale: Gothic fronts on the Molo and the Piazzetta replace the generic ones; the rest stays generic
    bd = B.get('w138803915')
    if bd is not None:
        bd.H = ducale.Z_COR; bd.pmat = {'wall': 'wall_stone', 'roof': 'lead'}
        bd.hero_cut = [LineString([tuple(ducale.SW), tuple(ducale.SE)]), LineString([tuple(ducale.SW), tuple(ducale.NW)])]
        HEROES.append(((100.0, -20.0), lambda mb, inst: ducale.build(mb)))
    # Libreria (east front on the Piazzetta) and the two columns
    bl = B.get('w206333242')
    if bl is not None:
        bl.H = piazzetta.LIB['cor']; bl.pmat = {'wall': 'wall_stone', 'roof': 'lead'}; bl.kind = 'palazzo'
        bl.hero_cut = [LineString([tuple(piazzetta.LIB_A), tuple(piazzetta.LIB_B)])]
        HEROES.append((tuple((piazzetta.LIB_A + piazzetta.LIB_B) / 2), lambda mb, inst: piazzetta.build_libreria(mb)))
    for bid in ('w430963095', 'w431003750'):
        if bid in B: B[bid].hero = True
    HEROES.append(((59.0, -83.0), lambda mb, inst: piazzetta.build_columns(mb)))
    # Torre dell'Orologio: hand-modelled front, the OSM parts stay behind it
    tl = LineString([tuple(piazzetta.TORRE_LINE[0]), tuple(piazzetta.TORRE_LINE[1])])
    for b in world.buildings:
        if b.parent == 'w410344943':
            b.hero_cut = [tl]; b.kind = 'palazzo'; b.roof = 'flat'; b.roof_h = None
            b.H = 24.0 if b.H > 20 else 15.6
    HEROES.append((tuple(wf(19.8, 72.0)), lambda mb, inst: piazzetta.build_torre(mb)))
    # Caffè Florian: rooms behind the Nuove portico + terrace and orchestra stage in the piazza
    HEROES.append((tuple(wf(-72.0, -30.0)), lambda mb, inst: florian.build_interior(mb)))
    HEROES.append((tuple(wf(-72.0, -12.0)), lambda mb, inst: florian.build_terrace(mb)))
    # Teatro La Fenice: OSM parts give the massing; the front on Campo San Fantin, foyer, corridor and hall are modelled
    fl = LineString([tuple(fenice.FAC_S), tuple(fenice.FAC_N)])
    for b in world.buildings:
        if b.parent == 'w813451645': b.hero_cut = [fl]; b.pmat = {'wall': 'wall_stone'} if b.H < 24 else b.pmat
    HEROES.append((tuple((fenice.FAC_S + fenice.FAC_N) / 2), lambda mb, inst: fenice.build_front(mb)))
    HEROES.append((tuple(fenice.O), lambda mb, inst: fenice.build_hall(mb)))
    # Ponte di Rialto
    HEROES.append((tuple(rialto.C), lambda mb, inst: rialto.build(mb)))
    # the other Grand Canal crossings: Accademia (timber arch), Scalzi (stone arch), Costituzione (Calatrava steel)
    HEROES.append((gc_bridges.ANCHORS['accademia'], lambda mb, inst: gc_bridges.build_accademia(mb)))
    HEROES.append((gc_bridges.ANCHORS['scalzi'], lambda mb, inst: gc_bridges.build_scalzi(mb)))
    HEROES.append((gc_bridges.ANCHORS['costituzione'], lambda mb, inst: gc_bridges.build_costituzione(mb)))
    # Stazione di Santa Lucia: the 1950s front (hall with its glass wall and lettering, wings, canopy, scalinata);
    # the OSM parts behind it are cut back to it
    santa_lucia.setup(world)
    HEROES.append((santa_lucia.ANCHOR, lambda mb, inst: santa_lucia.build(mb)))
    # Basilica di San Marco (full replacement: massing, domes, west front)
    bb = B.get('w138800932')
    if bb is not None:
        bb.hero = True
        poly = bb.poly
        HEROES.append((tuple(wf(70.0, 36.0)), lambda mb, inst, poly=poly: basilica.build(mb, world, poly)))
    # Piazza San Marco: the three flagpoles on the pedestals OSM maps (their generic stubs hidden), the white Istrian
    # bands of the paving, the lamps of the Molo, the columns and the Loggetta (one entry per part and tile)
    piazza_props.set_pole_sites(piazza_props.OSM_POLE_SITES)
    for bid in piazza_props.osm_pole_stubs(world):
        if bid in B: B[bid].hero = True
    HEROES.extend(piazza_props.hero_entries())
    # setups may split or add buildings: index them again
    from shapely import STRtree
    world.btree = STRtree([b.poly for b in world.buildings])
    world.bidx = {b.id: i for i, b in enumerate(world.buildings)}

def walk_areas():
    """[(polygon, z or None)] walkable overrides (porticoes, interiors) and blocked spots (piers, columns)."""
    return procuratie.walk_areas() + rialto.walk_areas() + gc_bridges.walk_areas() + ducale.walk_areas() + piazzetta.libreria_walk() + piazzetta.columns_walk() + florian.walk_areas() + basilica_int.walk_area() + fenice.walk_areas() + piazza_props.walk_areas() + santa_lucia.walk_areas()

def build(tile_box, mb, inst):
    """heroes whose anchor falls in this tile (half-open box, so a point on a border belongs to one tile)."""
    x0, y0, x1, y1 = tile_box.bounds
    out = []
    for anchor, fn in HEROES:
        if x0 <= anchor[0] < x1 and y0 <= anchor[1] < y1:
            out.append(fn(mb, inst))
    return out
