# shibuya hero district — build notes

`cd tokyo2090 && blender -b -P tools/hero/shibuya/build.py` regenerates everything from
`/home/kazu/work/tokyo2090-assets/hero/shibuya/` in about 4 minutes on the RTX 4090. Stages can be run one at a time:
`-- tex scene bake export preview`; `export` also takes `near mid far` to export only some levels.
Scratch files go to `assets/hero/shibuya/work/`: `tex/` (atlases), `orm/`, `scene.blend` and `baked.blend`.

## Pipeline
- **Textures** (`sb_tex_*.py`, `sb_texlib.py`, `sb_surf.py`, `sb_nodes.py`): small scenes rendered orthographically in Cycles as
  emission. One render gives the albedo, a second gives the tangent-space normal. All noise is wrapped on a circle or torus, so
  the textures tile.
  - `facade_a` / `facade_b`: 2 × 8 bands. One band is one storey of 4 bays (14.4 m) and tiles in u.
  - Signs and props atlases.
  - Decals: zebra stripes, cracks, moss, 止まれ, manhole.
  - Foliage: leaves made of real polygons.
  - Tileable materials: concrete, rubble, rust, bark, moss carpet.
- **Buildings** (`sb_bldg.py`, `sb_plan.py`): each PLATEAU shell is sliced once per floor. Walls are built per floor and per bay,
  and each floor uses one band row of the facade texture.
  - A ruin height field `Ruin` (shear, wedge, hole, plus "core" raises) decides which floors still stand.
  - Exposed slabs come from a 1.5 m strip grid. The faces of open storeys use the gutted band.
  - Breaches are recesses. The broken tops also get column stubs with rebar and hanging slab pieces.
  - Signature building ids are listed in `sb_plan.SPECIAL`: b003 QFRONT, b012 MAGNET, b007 SHIBUYA109, b006 the station-side
    corner, b008/b009 Seibu, and b000 (its north part collapsed into Dogenzaka; the rubble ramp lives in `sb_place.rubble`).
- **Street** (`sb_street.py`, `sb_place.py`, `sb_props.py`): the scramble's zebras, including the second diagonal. Decals are
  draped on `ground.npz` at +0.04 to +0.05 m. Also cars and the bus from OSM roads, signals, lamps, fences, vending machines,
  bicycles, facade signboards, and rubble heaps.
- **Landmarks** (`sb_land.py`, `sb_hachiko.py`):
  - 109: a sign band with extruded letters; the "1" lies at the fork.
  - QFRONT: a hanging, dead screen.
  - MAGNET: sign and screen.
  - Center-gai: the arch.
  - Rooftop billboards.
  - Hachiko: metaballs → remesh → smooth → decimate. Its unique bronze/granite albedo is baked to `tex/bronze.png`.
- **Vegetation** (`sb_veg.py`): five instanced tree templates (EXT_mesh_gpu_instancing; trunk `bark_*`, crown `foliage_*`,
  pivot at the base). Also ivy curtains from the wall tops, strangler-fig roots below the edge trees, and tufts on roofs,
  cars and rubble.
- **UV1 / AO** (`sb_uv1.py`, `sb_bake.py`): planar charts packed at uniform density, one ORM atlas per material.
  Cycles AO is baked into R; roughness and metalness are constants in G and B.
- **LODs** (`sb_lod.py`):
  - mid: decimated copies, every texture downsized to 1024, crowns thinned.
  - far: decimated silhouette plus blob crowns. Its single atlas is baked from its own materials through a fresh UV, times AO.
- **Collision** (`sb_scene.write_collide`): every footprint filled at the first-floor ceiling (except b000, so the ramp
  works), plus all top surfaces, coarse rubble heaps, boxes for props and prisms for tree trunks.

## Lessons
- Blender previews use the game's convention (hero.js multiplies albedo by π): sun strength = |sun colour| × π, world =
  hemisphere × 0.9.
- Do not `pkill -f` a pattern that appears in the same shell command: it kills the shell itself (exit 144).
- The exporter needs a `Math: ROUND` on alpha to write MASK. `UV Map` nodes pick the texCoord. A Color Attribute multiplied
  into the base colour exports COLOR_0.
