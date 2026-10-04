STONE PBR WEB_V11 - OPT-IN STUDY

V10 stone/photo/glazing assets remain unchanged. This folder contains36new1K
base-color/roughness/OpenGL-normal maps for the12 existing stone materials.
All twelve retain the original V10 mean RGB; no photograph is processed.

Generate (CPU only; existing environment, no installation):
  python3 src/prepare_stone_pbr_web_v11.py

Integrate in the root-managed Blender build:
  SAGRADA_STONE_PROFILE=web_v11 <the existing Blender build command>
or call materials.build_materials(ROOT, stone_profile='web_v11').
Unset SAGRADA_STONE_PROFILE or use 'v10' for unchanged default materials.
The generator itself does not build Blender, render, export GLB, or modify Web.

profile.json lists exact filenames, hashes, per-material normal strength,
roughness, measured statistics, references, and protected V10 hashes.
raw_texture_comparison.png is a RAW SWATCH BOARD, not a rendered comparison.
The existing world UV period stays2metres; no geometry or UV changes are made.

Changes: local mineral detail, controlled shallow normals, varied roughness;
polished granite/porphyry/floor remain smoother than cut/weathered stone.
Old Nativity has scattered neutral weathering, not a broad brown multiplier.
No giant cloud field, painted cavity shadow, baked AO, or invented masonry.

Measured limit: small-scale albedo variations average away at distant mips.
This profile is not a substitute for contact/cavity contrast from lighting/AO.
Only actual Chrome/WebGL2 A/B review can approve the integrated appearance.
