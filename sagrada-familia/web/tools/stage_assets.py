#!/usr/bin/env python3
"""Stage a self-contained Godot Web project from the editable native source."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[2]
web=ROOT/'web/godot'
(ROOT/'web/qa').mkdir(parents=True,exist_ok=True)
for name in ['sagrada_familia.glb','colliders.json','runtime_lighting.json']:
 source=ROOT/'build'/name
 if not source.is_file(): raise SystemExit(f'Missing source: {source}')
 (web/'assets').mkdir(parents=True,exist_ok=True)
 shutil.copy2(source,web/'assets'/name)
for name in ['project.godot','main.tscn']:
 shutil.copy2(ROOT/'runtime'/name,web/name)
project=web/'project.godot'
project.write_text(project.read_text().replace('\"4.7\", \"Forward Plus\"','\"4.7\", \"GL Compatibility\"').replace('renderer/rendering_method=\"forward_plus\"','renderer/rendering_method=\"gl_compatibility\"'))
shutil.copytree(ROOT/'runtime/scripts',web/'scripts',dirs_exist_ok=True)
records={name:{'bytes':(web/'assets'/name).stat().st_size,'sha256':hashlib.sha256((web/'assets'/name).read_bytes()).hexdigest()} for name in ['sagrada_familia.glb','colliders.json','runtime_lighting.json']}
(ROOT/'web/qa/staged_sources.json').write_text(json.dumps(records,indent=2)+'\n')
(web/'assets/source_manifest.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records))
