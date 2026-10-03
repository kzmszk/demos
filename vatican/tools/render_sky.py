"""render the bake world (Nishita sky, no sun disc) as an equirect Radiance HDR for the viewer."""
import bpy, sys, math
sys.path.insert(0, '/home/kazu/work/demos/vatican/tools')
from vb import bl
import build_exterior as BX
out = sys.argv[sys.argv.index('--') + 1]
bl.clear_scene()
bl.setup_world(**BX.SUN)
sc = bpy.context.scene
cd = bpy.data.cameras.new('pano'); cd.type = 'PANO'
try: cd.panorama_type = 'EQUIRECTANGULAR'
except Exception: cd.cycles.panorama_type = 'EQUIRECTANGULAR'
ob = bpy.data.objects.new('pano', cd); sc.collection.objects.link(ob)
ob.location = (0, 0, 2); ob.rotation_euler = (math.pi / 2, 0, -math.pi / 2)   # +y forward? centre of image = +x (east)
sc.camera = ob
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16
sc.render.resolution_x = 2048; sc.render.resolution_y = 1024
sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'HDR'
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
