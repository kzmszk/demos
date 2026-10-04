# Coordinate and module contract

Metres; Blender Z up. `build_scene.py` builds in a drawing frame and mirrors Y once into the final geographic frame: +X runs from the Glory façade (SE) toward the apse (NW), +Y is Passion (SW / warm glass), −Y is Nativity (NE / cool glass). Modules must not apply a second mirror. Cameras, collision JSON and runtime lights use the final frame.

The basilica is reconstructed with an approximately 90 m longitudinal span, 45 m nave width, 7.5 m bays, a 45 m main vault, 30 m aisle vaults and a 60 m crossing. Photo-derived placement, tapers and ornament are approximations; see `INTERIOR_EVIDENCE.json`, `EXTERIOR_EVIDENCE.json` and `MODEL_LIMITS.md`.

`interior.py` constructs the branching columns, walls, openings and vaults. `exterior.py` constructs the distinct Nativity, Passion and unfinished Glory fronts and the tower groups. `glazing.py` maps the licensed window photographs into traced apertures. `materials.py`, `stone_finishes.py` and the texture manifests define the editable materials. `site_context.py` supplies simplified surroundings. `geom.py` provides mesh primitives; `export_runtime.py` joins spatial/material groups for the GLB after the editable master is saved.

Glory's four future towers are not completed in this model. The Jesus tower exterior reaches 172.5 m but its unfinished interior is unavailable. Source code sometimes calls the small flower-shaped glazing divisions “rose”; these are not the great rose windows of Notre-Dame. This project does not modify the Notre-Dame work.
