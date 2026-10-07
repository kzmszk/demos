# KYOTO 京都

A browser reconstruction of Kyoto from Kyoto Station to Fushimi Inari, Tōfuku-ji, Tō-ji, Kiyomizu, Gion, Eikandō and Ginkaku-ji, plus Kinkaku-ji and Arashiyama–Sagano, to **walk** (streets, steps, temple grounds, through the torii tunnels) or **fly** over, on an **autumn evening** (maples, ginkgo) or a **snowy evening** (15 cm of snow, bare trees, falling snow). three.js WebGPU, Japanese and English (`#ja` / `#en`), solo piano (Bach's Goldberg Variations, played slowly by an in-browser physical-model piano) and natural sounds.

The city (5.8 x 8.6 km around the station, plus two enclaves: Kinkaku-ji 3.2 x 2.0 km and Arashiyama–Sagano 2.2 x 2.2 km; 1,528 tiles of 200 m) is generated from PLATEAU 2025 (MLIT: measured heights, LOD2 roof shapes, structure and age), OpenStreetMap (streets, water, landuse, trees, street furniture) and the GSI 5 m laser DEM. The landmarks are modelled in Blender with a Japanese-architecture kit (`tools/blender/jk`): curved roofs with corner upsweep, rafters, bracket sets, railings, lattices, torii. Light is baked per vertex with Blender Cycles (sky + bounce); the evening sun is live near the camera (cascaded shadows) and from the bake's sun visibility far away.

Only `public/` is published (`demo.json` has `"serve": "public"`). `tools/` is the build pipeline; raw data lives outside the repo in `/home/kazu/work/kyoto-assets/`.

## Run

```bash
python3 -m http.server 8417 --directory /home/kazu/work/demos     # the "demos" server
# http://127.0.0.1:8417/kyoto/public/index.html
```

Places (the 場所へ / Go to menu): Kyoto Station, Kyoto Tower, Tō-ji (the pagoda, from Kujō-dōri), Sanjūsangen-dō (outside, the hall), Fushimi Inari (the gate, the thousand torii), Tōfuku-ji (Tsūten-kyō from Gaun-kyō, the valley from Tsūten-kyō, the Sanmon), Kiyomizu-dera (the stage, the Niō gate), Yasaka-dōri and the pagoda, Sannenzaka, Ninenzaka, Ishibe-kōji, Hanamikōji, Shirakawa, Yasaka Shrine, Eikandō, Ginkaku-ji, Kinkaku-ji, Arashiyama (Togetsu-kyō, Nagatsuji-dōri), the bamboo grove, Nonomiya Shrine, Tenryū-ji, Jōjakkō-ji, over Arashiyama, over Higashiyama. The enclaves load only when you go there (tiles by distance, their minimaps on arrival).

Query flags: `season=winter`, `set=NAME` (another tile set in `public/data`), `low=1|0` (phone profile), `post=0`, `ao=0`, `aa=0`, `shadows=0`, `trees=0`, `exp=` / `wexp=` (exposure), `grade=` (evening grade strength, 0 = off), `fogd=` (haze distance, m), `spec=` (specular scale), `tm=agx`, `dbg=alb|irr|sun`, `async=0`.
Keys: W A S D walk or fly, Shift run, drag to look, E/Q up/down and wheel for speed (fly), M the map.

## Build

`python` is `/home/kazu/work/kyoto-assets/.venv/bin/python` (numpy, scipy, shapely, pyproj, pyosmium, triangle, mapbox_earcut, Pillow, OpenCV, lxml, numba); `blender` 5.2 on the PATH (Cycles OptiX); `node` with `tools/node_modules` (three, meshoptimizer, esbuild).

```bash
cd kyoto/tools
python -m gen.dem core far                          # GSI elevation tiles -> 2 m core grid + far grids
python -m gen.plateau 8                             # PLATEAU CityGML (core mesh codes) -> cache/plateau/*.pkl
python -c "from gen import osm, world; osm.load(True); world.load(True)"
python build_tiles.py BUILD --bbox -1200 -3200 4600 5400 -j 10     # tiles: buildings, terrain, water, bridges, surface + walk rasters, far LOD
python build_trees.py BUILD -j 8                    # tree placements (OSM, avenues, river banks, parks, forests, hero sites)
python build_props.py BUILD -j 6                    # street furniture
python bake_batches.py BUILD --samples 128 [--reverse]   # Cycles per-vertex bake (two runners can share the work)
python pack.py BUILD STAGE && node pack.mjs STAGE ../public/data/city
python -m gen.treepack ../public/data ../public/tex # tree templates + leaf atlas + impostors
python map_build.py BUILD ../public/tex 3.0          # minimap
python tex_build.py BUILD/tex1k --size 1024 --ktx   # texture arrays (copy city_*_1024.ktx2 to public/tex; also --size 512 for phones)
python split_big.py                                 # files over 24 MiB -> parts .0 .1 + tex/split.json (Cloudflare's 25 MiB limit; main.js joins them)
python sky_grade.py ASSETS/sky/autumn_2k.hdr ASSETS/sky/autumn.json ../public/tex/sky_autumn.hdr   # evening grade of the sky (same for winter)
python statue_pack.py BUILD STAGE_S && node statue_pack.mjs STAGE_S ../public/data/statues           # Sanjūsangen-dō statues (meshopt + gzip, full detail loaded near)
python credits.py                                   # public/credits.html from the asset manifests
node build_web.mjs                                  # public/app.js (--dev for a source map)
```

Packing only (no rebuild/rebake): `kyoto-assets/build/repack_all.sh` (all tiles, ~2.5 min) or `trees_tiles.sh "i,j;..."` (trees + repack). pack.py also paints the heroes' natural ground into the surface raster, drops generic terrain under hero ground, lights trees from the open ground at their foot and flags the heroes' water as still ponds.

One hero site after a change in Blender: `python hero_update.py SITE [SITE ...] [--tiles "i,j;i,j"]` rebuilds the tiles it touches (geometry, trees, props), bakes them and packs them into `public/data/city`. `python build_tiles.py BUILD --tiles ... --walk-only` rewrites only the walk maps (no rebake): height, surface, blocked, water and *covered* (a hero roof above the floor: the viewer opens its exposure indoors).

Hero sites: `python site_data.py SITE` exports the site's terrain, OSM and PLATEAU data; `blender -b --python blender/run_site.py -- SITE --shots` builds `blender/sites/SITE.py` into `kyoto-assets/heroes/SITE.npz` (+ a `.blend` and previews); `build_tiles.py` merges every hero file into the tiles it covers (geometry, generic buildings removed, terrain cut, ground painted, walk surfaces and blockers). See `tools/blender/KIT.md`.

## Sources

PLATEAU (国土交通省 Project PLATEAU, 京都市 2025), OpenStreetMap contributors (ODbL), 国土地理院 標高タイル, Poly Haven / ambientCG (CC0) textures and skies, the Goldberg Variations score by Knute Snortum (LilyPond, CC BY-SA 4.0) after the Open Goldberg Variations (Kimiko Ishizaka, CC0). The full list is on `credits.html`.
