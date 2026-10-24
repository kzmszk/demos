# roppongi — Roppongi Hills hero district

`blender -b -P tools/hero/roppongi/build.py` rebuilds everything (≈100 s) from
`/home/kazu/work/tokyo2090-assets/hero/roppongi/` into `public/hero/roppongi/`.
Stages: `tex` (venv python: textures.py + prep.py), `geo`, `bake` (Cycles AO into UV1 ORM atlases), `export`
(near.glb, collide.obj, hero.json), `mid` (sub-process: `--lod mid geo bake export far`), `render` (previews).
Single stages: `blender -b -P build.py -- [--lod mid] geo bake export`.

| file | what |
|---|---|
| prep.py | PLATEAU buildings → stacked prisms by roof level (`work/prisms.json`), Mori Tower plan |
| textures.py | procedural albedo textures (facade atlas rows = one floor; fac2 = two floors for mid), leaves, decals, signs (Noto CJK) |
| ruins.py | generic ruin shell: facade-atlas walls, broken bays, sheared/wedge tops, exposed & sagging slabs, collision tops |
| district.py | every footprint → ruin; per-building overrides (TV Asahi, Residences, Hyatt podium opened toward 66 Plaza, remains) |
| tower.py | Mori Tower: Fourier plan, 28 overlapping curved bays, notch + mid fins, crown comb + ring beams, tears, columns, peeled fins/sheets, green spill |
| plaza.py | 66 Plaza deck (z 31.3) on a ruined podium, stairs A (arena → plaza) and B (plaza → garden), Metro Hat, curved canopy, Museum Cone, arena |
| maman.py | Maman (legs, knees, body, egg sac with marble eggs, vine) |
| garden.py | Mohri Garden: flat pool (terrain bumps = islands), lilies, reeds, mossy stones, lanterns, cherries, Kin no Kokoro |
| keyaki.py | Keyakizaka zelkova rows, stopped traffic, lamps, guard rails, signs |
| veg.py / props.py / decals.py | trees, vines, roots, roof growth / cars, lamps, rubble / ground decals and deck tufts |
| stage_bake / stage_export / stage_far / stage_render | AO bake, glb export + stats, far atlas bake, previews |
| walkcheck.py | venv: rasterise collide.obj like the game and flood-fill from the spawns (`--north 125` tests the stairs alone) |
| look.py, map.py, roofmap.py | debug renders / plan maps |

Notes
- Facade quads carry UVs into an 8-row atlas (one floor per row, 32 m per u); bay widths divide 32 m and each floor
  gets a 6.4 m-multiple u offset so neighbours/floors don't repeat.
- ORM = baked AO (R) on UV1, constant roughness/metal per material; base colour on UV0 (no AO in it).
- Mid LOD walls are single-sided: double-sided walls self-shadow into diagonal acne at mid range in three.js.
- Draco texcoord quantisation 16 bit (facade u values run to ~30).
- The game terrain under the pond has 3 m bumps: the water is a flat plane at 19.72 m, the bumps are reed islands.
