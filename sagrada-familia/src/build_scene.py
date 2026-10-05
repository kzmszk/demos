"""Reproducible editable Sagrada Família reconstruction, evidence cutoff 2026-09-22."""
import bpy, sys, os, pathlib, math, json, time
from mathutils import Vector, Matrix
ROOT=pathlib.Path(__file__).resolve().parents[1]
(ROOT/'build').mkdir(parents=True, exist_ok=True)
sys.path.insert(0,str(ROOT/'src'))
import geom as H, materials, glazing, interior, exterior, site_context
started=time.monotonic()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for c in list(bpy.data.collections):
    if c.name!='Collection' and not c.objects:bpy.data.collections.remove(c)
M=materials.build_materials(ROOT, stone_profile=os.environ.get('SAGRADA_STONE_PROFILE','web_v11'))
ctx={'M':M,'H':H,'root':ROOT,'colliders':[]}
for module in [interior,exterior,glazing,site_context]:
    print('BUILD',module.__name__,flush=True);module.build(ctx)
# Surface-only finish pass; source dimensions and UVs remain editable/unchanged.
if os.environ.get('SAGRADA_STONE_FINISHES','on')=='on':
    import stone_finishes
    stone_finishes.apply(ctx)
print('GEOMETRY COMPLETE',len(bpy.data.objects),flush=True)

# Convert text/curve details before the geographic transform and GLTF handoff.
depsgraph=bpy.context.evaluated_depsgraph_get()
for old in list(bpy.context.scene.objects):
    if old.type not in {'FONT','CURVE'}:continue
    me=bpy.data.meshes.new_from_object(old.evaluated_get(depsgraph));ob=bpy.data.objects.new(old.name+' mesh',me);ob.matrix_world=old.matrix_world.copy()
    for coll in old.users_collection:coll.objects.link(ob)
    bpy.data.objects.remove(old,do_unlink=True)
# Daylight is an explicit artistic reconstruction; no claim of physically surveyed illuminance.
H.collection('90 Daylight and spectral study')
def area(name,pos,target,energy,color,size,size_y=None):
    light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.color=color
    light.shape='RECTANGLE';light.size=size;light.size_y=size_y or size
    ob=bpy.data.objects.new(name,light);H.ACTIVE.objects.link(ob);ob.location=pos
    ob.rotation_euler=(Vector(target)-Vector(pos)).to_track_quat('-Z','Y').to_euler()
    return ob
runtime_lights={'coordinate_system':'Blender XYZ, Z up, metres','point_lights':[],'spot_lights':[],
 'note':'Realtime colored light is a visual approximation, not spectral simulation.'}
for side in [-1,1]:
    for i,x in enumerate([3.75,11.25,18.75,26.25,33.75,73.5]):
        color=((1,.12,.025),(1,.32,.035),(1,.56,.09))[i%3] if side<0 else ((.06,.32,1),(.04,.8,.66),(.14,.62,.8))[i%3]
        area('Window colored transmission',(x,side*21.5,13),(x-5,side*3,5),1400 if side<0 else 950,color,4,10)
        area('Window broad sky fill',(x,side*21.3,22),(x,0,18),1400,(.77,.85,1),4,6)
        runtime_lights['point_lights'].append(dict(name=f'Glass spill {side} {i}',position=[x,side*15.5,10],color=list(color),energy=2.0,range=17,attenuation=1.1))
for x in [8,23,38,53,72]:
    area('Vault diffuse sky fill',(x,0,40 if x<45 else 55),(x,0,2),2600,(.94,.94,1),10,9)
    runtime_lights['point_lights'].append(dict(name=f'Vault fill {x}',position=[x,0,24],color=[.91,.91,1],energy=.8,range=34,attenuation=.9))
area('Apse warm daylight',(85,0,27),(62,0,10),3400,(1,.82,.56),9,18)
area('Glory entrance fill',(1,0,10),(22,0,12),1800,(.83,.9,1),12,15)
world=bpy.data.worlds.new('Barcelona autumn daylight');world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.57,.72,.93,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.4;bpy.context.scene.world=world
light=bpy.data.lights.new('Mediterranean afternoon sun','SUN');light.energy=2.7;light.angle=.065;light.color=(1,.88,.7)
ob=bpy.data.objects.new(light.name,light);H.ACTIVE.objects.link(ob)
ob.rotation_euler=(math.radians(34),math.radians(-24),math.radians(-30))

H.collection('99 Review cameras')
def camera(name,pos,target,lens):
    data=bpy.data.cameras.new(name);data.lens=lens;data.clip_end=700
    ob=bpy.data.objects.new(name,data);H.ACTIVE.objects.link(ob);ob.location=pos
    ob.rotation_euler=(Vector(target)-Vector(pos)).to_track_quat('-Z','Y').to_euler()
    return ob
camera('01_Nativity_current',(22,175,3),(52,0,79),30)
camera('02_Passion_current',(-50,-177,57),(48,0,77),34)
camera('03_Nave_to_altar',(5,0,1.7),(68,0,23),18)
camera('04_Tree_canopy',(27,-1.4,1.7),(31,0,45),15)
camera('05_Warm_glass',(23,4,1.7),(28,-21,16),21)
camera('06_Cool_glass',(23,-4,1.7),(28,21,16),21)
camera('07_Crossing_apse',(43,0,1.7),(81,0,24),19)
camera('08_Glory_worksite',(-102,-75,36),(25,0,45),34)
camera('09_Central_towers',(117,-125,145),(55,0,135),34)
camera('10_Nativity_sculptures',(52.5,49,11),(52.5,35.2,14.5),38)
camera('11_Passion_sculptures',(52.5,-49,15),(52.5,-33.65,17),42)
camera('15_Judas_and_magic_square',(42.6,-45,5),(42.6,-33.7,6.4),42)
camera('12_Botanical_doors',(50,45,2.1),(50,35.7,3.9),47)
camera('13_Warm_window_detail',(18.75,-8.5,7),(18.75,-22.58,9.3),26)
camera('14_Cool_window_detail',(18.75,8.5,7),(18.75,22.58,9.3),26)
camera('16_Holy_Family_left_oblique',(46.4,48,12),(52.5,38,13.5),45)
camera('17_Holy_Family_right_oblique',(58.6,48,12),(52.5,38,13.5),45)
camera('18_Sotoo_musician_angels',(52.5,56,24),(52.5,38,24.8),34)
camera('19_Passion_full_sculptural_facade',(52.5,-76,13),(52.5,-28,19),38)
camera('20_Judas_oblique',(38,-46,5.2),(42.6,-34,6.5),44)
camera('21_Granite_column_full_height',(2,-18,5),(15,7.5,17),16)
camera('22_Porphyry_crossing_full_height',(31,-15,5),(45,7.5,20),14)
camera('23_Warm_runtime_matched',(20,-11.5,1.67),(18.75,-22.5,13),24)
camera('25_Granite_capital_detail',(11,0,18),(15,7.5,19.72),55)
camera('26_Basalt_capital_detail',(41,5,18),(45,15,20.12),50)
camera('27_Star_lightwell_detail',(18.75,0,33),(18.75,3.75,44),30)
camera('28_East_window_sequence',(19,0,13),(18.75,22.5,13),18)
camera('29_West_window_sequence',(19,0,13),(18.75,-22.5,13),18)
scene=bpy.context.scene;scene.camera=bpy.data.objects['03_Nave_to_altar']
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.cycles.max_bounces=10;scene.cycles.diffuse_bounces=6;scene.cycles.glossy_bounces=4
scene.cycles.transparent_max_bounces=12
scene.render.resolution_x=1440;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.threads_mode='FIXED';scene.render.threads=8
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.55
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['Reconstruction date']='Requested present: 2026-10-01; latest verified construction bulletin: 2026-09-22'
scene['Scope']='Evidence-led interpretive reconstruction, not an official digital twin or surveyed model'
scene['Current works']='Jesus exterior172.5m complete; interior unavailable; Glory and Assumption unfinished; central crane174m'
scene['Coordinate system']='Final: X Glory(SE) toward apse(NW), +Y Passion(SW) warm, -Y Nativity(NE) cool, Z up'
# Builders share their originally agreed drawing frame. Reflect it once into a
# right-handed geographic frame so altar-facing warm glass is LEFT, cool RIGHT.
# Mesh winding is reversed together with positions; UVs remain attached to corners.
mirror=Matrix.Diagonal((1.,-1.,1.,1.))
for ob in list(scene.objects):
    if ob.type=='MESH':
        if ob.data.users>1:ob.data=ob.data.copy()
        ob.data.transform(mirror @ ob.matrix_world)
        ob.data.flip_normals();ob.matrix_world=Matrix.Identity(4);ob.data.update()
    elif ob.type in {'CAMERA','LIGHT'}:
        direction=mirror.to_3x3() @ (ob.rotation_euler.to_matrix() @ Vector((0,0,-1)))
        ob.location=mirror @ ob.location
        ob.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
for item in ctx['colliders']:
    if 'center' in item:item['center']=[item['center'][0],-item['center'][1],item['center'][2]]
    if 'rotation_z' in item:item['rotation_z']=-item['rotation_z']
    if 'points' in item:item['points']=[[p[0],-p[1],p[2]] for p in item['points']]
for item in runtime_lights['point_lights']+runtime_lights['spot_lights']:
    for key in ['position','target']:
        if key in item:item[key]=[item[key][0],-item[key][1],item[key][2]]
import lighting
lighting.refine_existing_scene()
for ob in scene.objects:
    if ob.type=='MESH':
        ob['Evidence']='See docs evidence ledger for measured anchors vs interpretive detail'
        if not ob.data.uv_layers:H.uv_auto(ob)
(ROOT/'build/colliders.json').write_text(json.dumps({'coordinate_system':'Blender XYZ, Z up, metres; +Y Passion SW, -Y Nativity NE','colliders':ctx['colliders']},indent=2))
(ROOT/'build/runtime_lighting.json').write_text(json.dumps(runtime_lights,indent=2))
stats={'objects':len(scene.objects),'meshes':sum(o.type=='MESH' for o in scene.objects),'vertices':sum(len(o.data.vertices) for o in scene.objects if o.type=='MESH'),'polygons':sum(len(o.data.polygons) for o in scene.objects if o.type=='MESH'),'seconds':round(time.monotonic()-started,1)}
print('SAVE editable blend',stats,flush=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'build/Sagrada_Familia_2026.blend'))
(ROOT/'build/model_stats.json').write_text(json.dumps(stats,indent=2))
if '--skip-export' not in sys.argv:
    import export_runtime
    export_runtime.export(ROOT)
print('FINISHED',round(time.monotonic()-started,1),'seconds',flush=True)
sys.stdout.flush();sys.stderr.flush();os._exit(0)
