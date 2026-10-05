"""Render reproducible matched views. Run through thermal_run.py."""
import bpy,sys,pathlib,time,json,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
(ROOT/'screenshots/render').mkdir(parents=True, exist_ok=True)
(ROOT/'logs').mkdir(parents=True, exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
scene=bpy.context.scene
pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
for device in pref.devices:device.use=device.type=='OPTIX'
scene.cycles.device='GPU'
print('Render devices',[(d.name,d.type,d.use) for d in pref.devices],flush=True)
size,samples=(1100,24) if '--preview' in args else (2000,96)
if '--quick' in args:size,samples=900,16
names=[a for a in args if not a.startswith('--')] or ['01_Nativity_current','03_Nave_to_altar']
scene.render.resolution_x=size;scene.render.resolution_y=round(size*.7);scene.cycles.samples=samples
manifest=[]
for name in names:
    scene.camera=bpy.data.objects[name]
    scene.render.resolution_y=size if name in ['01_Nativity_current','02_Passion_current','08_Glory_worksite'] else round(size*.7)
    if name=='01_Nativity_current':scene.camera.data.lens=30
    if name=='02_Passion_current':scene.camera.data.lens=34
    suffix='.preview' if '--preview' in args or '--quick' in args else ''
    path=ROOT/'screenshots/render'/f'{name}{suffix}.png'
    scene.render.filepath=str(path);started=time.monotonic()
    bpy.ops.render.render(write_still=True)
    manifest.append({'view':name,'path':str(path),'kind':'offline Cycles render','samples':samples,'seconds':round(time.monotonic()-started,2)})
    print('RENDERED',manifest[-1],flush=True)
(ROOT/'logs/render_latest.json').write_text(json.dumps(manifest,indent=2))
sys.stdout.flush();sys.stderr.flush();os._exit(0)
