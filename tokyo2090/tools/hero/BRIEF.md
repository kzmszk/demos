# Hero districts — shared brief for the Blender builders

TOKYO 2090 (`/home/kazu/work/demos/tokyo2090`, three.js r186, live at https://demos.polynous.io/tokyo2090/) is a
cape-glider game over Tokyo 60 years after 99 % of humanity vanished. The whole city is procedural (PLATEAU LOD2
shells + a facade shader + random collapse). The player can now land and **walk the streets**, so three places get
hand-built ruins made in Blender, rich enough to enjoy on foot and recognisable from the air:

| district | box (city frame) | what it is |
|---|---|---|
| `shibuya` | x −235…75, y −75…175 | the scramble crossing to SHIBUYA109 |
| `tocho` | x −880…−645, y 3100…3440 | the Tokyo Metropolitan Government Buildings |
| `roppongi` | x 2470…2830, y −140…240 | Roppongi Hills |

Read first: `docs/concept.md`, `NOTES.md` (top part), and look at the boards in `boards/` — `01-shibuya-key.png`,
`02-shinjuku-tocho.png`, `03-roppongi.png`, `07-street-cars.png`, `09-dawn-fog.png`, `12-title-panorama.png`.
They set the look the user approved.

## Look

- 2090: sixty years untouched. Hot, wet climate. **Jungle ruin like Ta Prohm / Beng Mealea**: strangler-fig roots
  pouring over facades and through windows, curtains of vines, moss on every ledge, trees grown out of cracks, roofs
  and rubble, street trees grown into a canopy. Not horror, not grimy: quiet, beautiful, a little melancholy, the joy
  of flight is the point.
- Structural ruin that reads as real engineering failure: tops sheared off at a jagged line, corners gone in a wedge,
  floor slabs exposed and sagging, rebar, curtain-wall mullions bent, facade panels hanging or fallen, glass gone
  (a few shards), stair cores standing proud, collapsed canopies, rubble cones and spill at the feet of the towers.
- Every place must stay **recognisable**: its silhouette and its signature details (listed per district in your
  prompt). A person who knows the place should know it at a glance, from the air and from the street.
- Palette: muted greens (moss, foliage), rust and iron-oxide browns, bleached concrete, granite. A warm low sun.
  Nothing glows, no emissive, no lights. Faded paint and signage are fine (Japanese, sun-bleached); the player's
  and Saki's capes are the only saturated colour on screen.
- Abandoned vehicles (rusted, tyres flat, glass gone, plants growing through), fallen traffic signals, poles,
  guard rails, bicycles, vending machines, signs.

## Data you get (`/home/kazu/work/tokyo2090-assets/hero/<district>/`, made by `tools/gen/hero_src.py`)

Coordinates are local to the district origin (`buildings.json` → `origin`, in the city frame): **x east, y north,
z up = absolute height in metres (T.P.)** — Blender's own axes, so import OBJs with `forward_axis='Y', up_axis='Z'`.
Keep z absolute (do not move things down to 0).

- `buildings.obj` — PLATEAU LOD2 (2020s) of **every building you must rebuild**: all with their centroid in the box.
  One object per building (`b000` = the tallest). They disappear from the procedural city when your district goes in,
  so each footprint needs something: a ruin of that building, or its collapsed remains.
- `buildings.json` — per object: PLATEAU id, name, use, z0 (ground), z1, height, centroid, LOD2 or LOD1.
- `buildings_game.obj` — the same buildings as the procedural city collapses them today (for reference only).
- `context.obj` — the procedural neighbours that stay (render them in previews for fit; never export them).
- `ground.obj` — **the game terrain exactly as rendered**: a 10 m grid of triangles (each cell split along its
  (x+10, y)–(x, y+10) diagonal). The game draws this surface itself with a cracked-asphalt / sidewalk / moss shader
  (by the land-cover raster `cover.png`, 4 m/px, row 0 = north) and sows grass and ferns on it procedurally near the
  camera. **Do not replace the ground**: lay things on it. Anything flat on the ground (zebra stripes, curbs, cracks,
  puddles, leaf litter, rubble sheets) is a `decal_` mesh that follows ground.obj **+0.04 m** (subdivide to ≤ 1 m and
  shrinkwrap, or project onto the triangles); anything else stands on it. `ground.npz` has the grid (h, x0, y0, s=10).
- `osm.json` — OpenStreetMap in the box + 120 m (local coords): roads with widths, crossings, footways, areas,
  landuse, rails, barriers, trees, named points (shops, artworks...). Use it to put things where they really are.
- `cover.png` — the land-cover raster around the box (R road, G green, B water, A rail).

## What you deliver

Work in `tools/hero/<district>/` (scripts, notes; this goes to git) and
`/home/kazu/work/tokyo2090-assets/hero/<district>/work/` (blend files, bakes, scratch; not in git). The build must be
a script: `blender -b -P tools/hero/<district>/build.py` (more scripts are fine) regenerates everything from the
source package. Outputs go to `public/hero/<district>/`:

1. **`near.glb`** — the full-detail district. glTF 2.0 binary from Blender's exporter with **+Y up** (the default:
   Blender (x, y, z) → glTF (x, z, −y), which is exactly how the game maps the city frame). Budgets: **≤ 400 k
   triangles**, **≤ 40 draw calls** (merge by material; use linked duplicates + `export_gpu_instances` for repeated
   props if it helps), **≤ 16 MB**, textures **WebP**, ≤ 2048², total texture memory ≤ ~20 textures of 2048².
   Draco is fine (keep position quantisation at 16 bits — decals sit 4 cm above the ground). Materials: plain
   Principled BSDF that exports to glTF metallic-roughness: base colour texture (no AO baked into it), ORM texture
   (R = baked ambient occlusion, G = roughness, B = metallic), optional normal map. Alpha-clipped (MASK) for foliage,
   vines, broken edges. No emissive, no transmission, no vertex-colour-only looks.
2. **`mid.glb`** — the same district at **≤ 120 k triangles**, textures ≤ 1024² (phones up close; desktop 350–900 m).
3. **`far.glb`** — the silhouette at **≤ 25 k triangles**, one or two materials with one baked atlas ≤ 2048²
   (base colour may include AO here). Seen from 700 m to 6 km.
4. **`collide.obj`** — the collision proxy, ≤ 60 k triangles, same coordinates. The game rasterises it **from above**
   into a 0.5 m height field (walking) and a 4 m roof raster (flight, roof landings): at each (x, y) the top of the
   highest surface counts. So: building masses, broken floors you can stand on, rubble slopes (walkable if gentler
   than ~1 m rise per 2 m), vehicles, fallen columns, tree trunks (as prisms ≥ 0.6 m), low walls. **Leave out**
   anything a walker should pass under or through: canopies, signs, cables, vines, foliage, lamp arms, bridges higher
   than 2.5 m over a street (put the bridge in, the street under it stays open only if you leave the bridge out —
   prefer leaving it out). A step up of more than 0.55 m is a wall (the player climbs walls with Space); a drop of
   more than 3.2 m is an edge. Interiors cannot be entered (2.5D), so fill ground floors you want closed.
5. **`hero.json`**:
   ```json
   { "district": "shibuya", "origin": [ox, oy],
     "spawns": [ { "name": "スクランブル交差点", "x": 0, "y": 0, "heading": 0.0, "note": "..." } ],
     "labels": [ { "name": "SHIBUYA109", "x": 0, "y": 0, "z": 0, "kind": "building" | "place" } ],
     "stats": { "near_tris": 0, "mid_tris": 0, "far_tris": 0, "near_mb": 0, "draw_calls": 0 } }
   ```
   `spawns` (2–4) are street-level points the in-game menu jumps to (local x, y; the game finds the ground);
   `heading` in radians, **0 = north, +π/2 = east** (forward = (sin h, cos h)). The first spawn is the default and
   should open on the district's best view. `labels` name the signature things (local coords, z = where the label
   pin sits).
6. **`previews/`** — PNG renders (≤ 1600 px wide): at least two street-level views at eye height 1.6 m from the
   spawns, one aerial three-quarter view from ~250 m out and ~120 m up, and one aerial view **with `context.obj`**
   showing the fit into the neighbourhood. Use the game's light so the renders predict the game: sun from
   direction (x −0.76, y −0.40, z +0.24) i.e. toward the west-south-west, 15° high, colour (1.48, 1.12, 0.80);
   sky / hemisphere (0.46, 0.55, 0.70) above, (0.26, 0.28, 0.20) below; haze colour (0.80, 0.72, 0.62); filmic
   ("AgX" or "Filmic") view transform. EEVEE is enough.

## How the game will draw it (so you can predict the result)

- `MeshStandardMaterial` from the glTF, lit by one directional sun (shadow-mapped; your meshes cast and receive),
  a hemisphere light (sky/ground colours above), **no environment map**, ACES filmic tone mapping, exponential fog.
  With no environment map metallic surfaces look black: keep metalness ≤ 0.3 except small bright edges; rust is
  not metallic. Intact glass reads as dark, slightly blue-grey, low roughness.
- The AO in the ORM texture darkens only the ambient light — it is what makes the ruins read. Bake it well
  (Cycles on the RTX 4090 is fine).
- Mesh-name prefixes the game acts on: `decal_` (polygon offset, no shadow casting), `foliage_` (alpha-tested,
  double-sided, sways a little in the wind — keep the pivot at the base), `glass_` (dark, slightly reflective).
- The procedural city, its trees and cars **will not be drawn inside your box**: you own the vegetation and the
  vehicles there. The game will still sow small ground plants (grass, ferns, taro leaves) near the camera.
- The walker sees only `collide.obj`. Saki walks the same field.

## Rules

- Do not edit anything outside `tools/hero/<district>/`, `public/hero/<district>/` and the assets `work/` folder.
  No git, no deploy. Do not download anything from the internet (make textures procedurally in Blender and bake
  them); web search for reference photos and facts about the place is fine. Codex can make a reference image if
  it helps (see `/home/kazu/.claude/projects/-home-kazu-work-demos/memory/codex-image-generation.md`).
- Look at your renders and judge them honestly against the boards and against photos of the real place; iterate
  until it is good. The user's bar is high ("poster-grade"; they reject things that look like programmer art).
- Report at the end: what you built, the signature details, triangle counts and sizes for all three LODs, draw
  calls, known weak spots, and the preview paths.
