# jk — building a Kyoto hero site in Blender

This is the brief for anyone modelling one of the hand-built sites (清水寺, 伏見稲荷大社, 三十三間堂, 永観堂, 銀閣寺, 祇園, 京都駅/京都タワー …) for the KYOTO browser demo. The city around them is generated (PLATEAU + OSM); the sites are modelled by Python scripts that run inside Blender 5.2 with a small kit (`tools/blender/jk`). The output goes into the city's 200 m tiles, is lit by a Cycles bake, and is drawn by three.js WebGPU with the viewer's own shaders.

## Run

```bash
cd /home/kazu/work/demos/kyoto/tools
blender -b --python blender/run_site.py -- SITE --shots          # build, export, save .blend, render SHOTS
blender -b --python blender/run_site.py -- SITE --no-save         # quicker iteration
```

`SITE` is the module `blender/sites/SITE.py`, which defines:

```python
SHOTS = [('front', (x, y, z), (tx, ty, tz), lens_mm), ...]      # preview renders (EEVEE)
def build(B, S, only=None):                                     # B: jk.Builder, S: jk.site.Site
    ...
```

Outputs: `/home/kazu/work/kyoto-assets/heroes/SITE.npz` (what the tiles take), `/home/kazu/work/kyoto-assets/blender/SITE.blend` (for people to open), previews `/home/kazu/work/kyoto-assets/heroes/previews/SITE_<shot>.png`. Blender's Python has numpy, shapely, scipy, mapbox_earcut (from `/home/kazu/work/kyoto-assets/blender_py`, put on `sys.path` by `jk/__init__.py`).

Put helper code for your site in your own files under `blender/sites/` (e.g. `sites/kiyomizu_hondo.py`). **Do not edit the shared kit (`jk/*.py`)**: several sites are built in parallel. If the kit has a bug or lacks something, copy the function into your own module, change it there, and report it.

## Coordinates and data

- World frame: x east, y north (metres from Kyoto Station's central exit), **z = height above T.P.** (the GSI DEM's heights). Kiyomizu's main hall floor is around 120 m, Gion ~40 m.
- `S = Site(name)` (`jk/site.py`) gives:
  - `S.ground(x, y)` terrain height (1 m grid from the GSI 5 m laser DEM; arrays work).
  - `S.bounds` [x0, y0, x1, y1]; `S.polygon` the OSM precinct (list of rings).
  - `S.osm`: `buildings` [{id, tags, poly: [rings]}], `ways` (roads, paths, steps: {id, tags, line: [polylines], width}), `water`, `waterways`, `barriers` (walls, fences, hedges, retaining walls), `landuse`, `trees` ({xy, tags}), `points` ({xy, tags}: lanterns, torii nodes, shrines, viewpoints …). `S.find('buildings', name='本堂')` filters by tag substrings.
  - `S.plateau`: PLATEAU 2025 buildings {id, kind, z0 (ground), h (measured height), st (storeys), year, tags, poly, roof (LOD2 roof polygons, 3D, where surveyed)} — measured heights and roof shapes; good for checking your models' heights.
  - `S.rect(poly)` → (cx, cy, length, width, yaw)  (a shapely Polygon, a ring, or an OSM feature's nested `poly` list: the first outer ring is used) of a footprint's minimum rotated rectangle (yaw = direction of the long side, radians ccw from east).
  - `S.terrain_mesh(B, ring, mat='ground', res=1.0, surf='gravel')` your own ground over a polygon, drawn by the ground program with the given surface, plus a walk surface.
- References: `/home/kazu/work/kyoto-assets/refs/<site>/dossier.md` (dimensions with sources, OSM ids, what to get right) and photos with `manifest.json`. Read the dossier first; check your previews against the photos.

## Builder

```python
import jk
from jk import prim, arch, roof, Frame
B.add(P, I, 'mat', UV=None, N=None, smooth=False, tag='main', c0=(r,g,b,a), c1=(0, param, seed, flags))
with Frame(B, ox, oy, oz, yaw):      # build in a local frame (u along the front, v depth, z up); placed in the world
    ...
B.tree('momiji', x, y, z, scale, yaw)   # species: momiji ichou sakura keyaki matsu sugi hinoki kashi yanagi tsutsuji take
B.lamp(x, y, z, watts, rgb)             # lanterns / lamps (lit in the evening bake)
S.exclude.append(ring)                  # generic city buildings with a point inside are dropped (your precinct)
S.cut.append(ring)                      # the generic terrain is removed inside (only where you model the ground yourself)
S.paint.append({'poly': ring, 'surf': 'gravel'})   # paint the generic ground: asphalt sidewalk stone_sett stone_slab gravel soil grass moss forest sand graves wood_deck riverbed
```

Tags: `main` (drawn, baked, in the far view), `detail` (small parts: rafters, brackets, railings' struts — drawn near, left out of the far LOD), `walk` (invisible walk surfaces: every floor, stair, stage, path and step people should walk on — the viewer's walker follows the topmost walk surface and stops at steps over 0.42 m), `block` (invisible blockers: thin walls, railings, statues, pillars — cells covered become unwalkable). Generic terrain is walkable by default; generic buildings block.

UVs are in metres (if you pass none, a box projection is made). Smooth normals with `smooth=True` or pass `N`.

## Shapes (`jk.prim`)

`box`, `obox(p0, p1, w, h)` beam between points, `cyl(p0, p1, r0, r1, seg)` (pillars, posts, tapered), `lathe(c, [(r, z)...])` (finials, 擬宝珠, 相輪, lanterns), `sweep(path, profile)` (ridges, bargeboards, rails, curved members), `polygon(pts, z)`, `prism(pts, z0, z1)`, `grid_surface(f(u, v), ...)`, `rock(c, size, seed)` (garden stones).

## Architecture (`jk.arch`, `jk.roof`)

- `roof.roof(B, L, D, z_eave, o, kind='irimoya'|'yosemune'|'kirizuma'|'hogyo', cover='hongawara'|'sangawara'|'hiwada'|'kokera'|'copper', pitch, teri, sori, sori_len, gable_frac, verge, edge, rafter (spacing, 0 = none), rafter_mat, rafter_end, tiers, ridge_h, ridge_w, ends='oni'|'shibi'|None, hip, truncate (pagoda storeys), top (finial lathe profile))` — the plan is L x D at the wall plate (pillar line) at height z_eave, eaves `o` beyond it; concave roof profile (照り), corner upsweep (軒反り), rafters under the overhang (two tiers 地垂木 / 飛檐垂木), the eave edge with round tile ends for 本瓦, ridge with 鬼瓦 / 鴟尾, hip ridges, gable walls + 破風 + 懸魚 for 入母屋 / 切妻. Returns heights (`z_edge`, `z_ridge`, `z_break`). Read `jk/roof.py`; it is short.
- `arch.pillar`, `arch.grid(L, D, nu, nv)`, `arch.nageshi` (長押 / 貫 around the pillars), `arch.kumimono` / `arch.bracket_row` (組物: funa, hira, demitsudo, degumi, futatesaki, mitesaki; returns top height and reach — feed `L + 2*reach` to the roof), `arch.infill` between two pillars (plaster, board, renji 連子窓, katomado 花頭窓, shitomi 蔀戸, karado 桟唐戸, koshi 格子, noren, open), `arch.veranda` (縁), `arch.railing` (高欄 with 擬宝珠), `arch.stairs`, `arch.platform` (基壇), `arch.kamebara` (亀腹), `arch.torii` (明神鳥居; Inari colours: vermilion with black kasagi and 根巻; `inscription=True` adds the donor panel), `arch.ishidoro` (石灯籠), `arch.chochin` (提灯, lit), `arch.tsuiji` (築地塀 with `stripes` for 筋塀), `arch.takegaki` (竹垣), `arch.hedge` (生垣).
- `dbg/test_arch.py` and `dbg/test_roof.py` show them in use (a five-bay hall with veranda, brackets and an 入母屋 roof; a torii row; lanterns; walls).

## Materials (names; the viewer's shader decides how they look)

Woods and paints: `wood_dark` (aged dark timber), `wood_natural` (pale hinoki), `vermilion` (丹塗り), `black_lacquer`, `white_paint` (胡粉; rafter ends, plaster lines), `bamboo`, `metal_dark`, `metal_grey`, `bronze`, `gold` (gilding), `copper` (green patina, also roofs), `glass`, `cloth` (tinted by c0: noren, curtains), `tatami`, `lamp` / `lantern_paper` (emissive in the evening).
Stone and ground: `stone` (granite / 石垣), `curb`, `ground` (a surface; set c1.w to a SURF id or use S.terrain_mesh / S.paint), `sand_raked` (銀沙灘: the rake lines run along uv.x, i.e. uv.y counts across them in metres; a constant uv.y gives smooth sand), `moss_mound`, `water` (dark water surface: ponds, streams — give it a flat mesh at the water level).
Walls: `temple_wall` (white plaster; c0 = tint + a 35; c1.y 0 plain, 4 = with painted posts and tie beams), `wall_plaster`, `wall_earth`, `wall_board`, `machiya_front` (generic street-front program: avoid in hero sites, model the lattice), `hedge`.
Roofs: `hongawara` (本瓦: round + flat tiles), `kawara` (桟瓦), `hiwada` (檜皮 / 杮 shingles: fine courses), `copper`, `ridge` (ridge stacks, 鬼瓦).
Look at `public/data/materials.json` for the full list. Pick colours by material, not by vertex colour, except where c0 tints (walls, cloth).

## Budgets and quality bar

- Triangles: a large site (Kiyomizu, Fushimi Inari's lower precinct) ≤ ~1.5 M (main + detail); a small one ≤ 600 k. Rafters, brackets, lattices and tile ends are where the triangles should go — they are what makes a temple read as real at eye level. Avoid hidden geometry (insides of solid platforms, faces inside other faces).
- Scale and proportion from the dossier and PLATEAU heights; orientation from OSM footprints (`S.rect`). Put things on the terrain (`S.ground`), the GSI laser DEM already contains the platforms and steps.
- No photo textures: shape everything; the shader adds wood grain, plaster, tile relief, weathering, snow (winter) and autumn leaves on the ground.
- Every place a visitor walks must have a walk surface (floors, verandas, stages, stairs — stairs as a sloped walk ramp is fine), and walls/railings that should stop them a `block` mesh.
- Plant trees with `B.tree` (maples where the site is famous for them, pines in gardens, cedars on the hills); the city's generic trees are left out inside your excluded precinct.
- Previews: render SHOTS that match reference photos (same viewpoint where possible) and look at them critically. Iterate until the silhouette, proportions, colours and the number of bays / storeys are right.

## Rules

No git, no deploys, no edits outside `tools/blender/sites/` (your own files) and your outputs in kyoto-assets (heroes/, blender/, previews). Do not run the viewer or headless Chrome. Do not run Cycles bakes. Report back with: what was built (buildings, features), triangle counts, preview file paths, known gaps, and any kit problems.
