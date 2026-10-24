"""Shared helpers for the shibuya hero district build (run inside Blender 5.2).

Frame: local to the district origin, x east, y north, z up = absolute height (T.P. m).
"""
import json
import math
import os
import random

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = '/home/kazu/work/tokyo2090-assets/hero/shibuya'
WORK = os.path.join(SRC, 'work')
OUT = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'public', 'hero', 'shibuya'))
PREV = os.path.join(OUT, 'previews')
TEX = os.path.join(WORK, 'tex')
for d in (WORK, OUT, PREV, TEX):
    os.makedirs(d, exist_ok=True)

BOX = (-155.0, -125.0, 155.0, 125.0)          # local box (x0, y0, x1, y1)
ORIGIN = (-80.0, 50.0)
CROSS = Vector((83.8, -53.1))                  # scramble node (OSM)
HACHI = Vector((88.9, -100.0))
FONT_JP = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
FONT_JP_R = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'
FONT_JP_P = '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf'


# ---------------------------------------------------------------- data
def read_obj(path):
    """-> {name: (V (n,3) float, F list of index tuples)} with per-object vertex arrays."""
    objs = {}
    V = []
    cur = None
    faces = {}
    for line in open(path):
        if line.startswith('v '):
            V.append([float(t) for t in line.split()[1:4]])
        elif line.startswith('o '):
            cur = line.split()[1]
            faces[cur] = []
        elif line.startswith('f '):
            faces[cur].append([int(t.split('/')[0]) - 1 for t in line.split()[1:]])
    V = np.array(V)
    for n, F in faces.items():
        F = np.array(F)
        idx, inv = np.unique(F, return_inverse=True)
        objs[n] = (V[idx], inv.reshape(F.shape))
    return objs


def load_json(name):
    return json.load(open(os.path.join(SRC, name)))


class Ground:
    """The game terrain: 10 m grid, each cell split along (x+10, y)-(x, y+10)."""

    def __init__(self):
        g = np.load(os.path.join(SRC, 'ground.npz'))
        self.h = g['h'].astype(np.float64)
        self.x0 = float(g['x0']); self.y0 = float(g['y0']); self.s = float(g['s'])

    def __call__(self, x, y):
        fx = (x - self.x0) / self.s
        fy = (y - self.y0) / self.s
        i = int(math.floor(fx)); j = int(math.floor(fy))
        i = max(0, min(self.h.shape[1] - 2, i)); j = max(0, min(self.h.shape[0] - 2, j))
        u = fx - i; v = fy - j
        h = self.h
        if u + v <= 1.0:
            return h[j, i] + (h[j, i + 1] - h[j, i]) * u + (h[j + 1, i] - h[j, i]) * v
        return h[j + 1, i + 1] + (h[j + 1, i] - h[j + 1, i + 1]) * (1 - u) + (h[j, i + 1] - h[j + 1, i + 1]) * (1 - v)

    def many(self, xy):
        xy = np.asarray(xy, dtype=np.float64)
        fx = (xy[:, 0] - self.x0) / self.s
        fy = (xy[:, 1] - self.y0) / self.s
        i = np.clip(np.floor(fx).astype(int), 0, self.h.shape[1] - 2)
        j = np.clip(np.floor(fy).astype(int), 0, self.h.shape[0] - 2)
        u = fx - i; v = fy - j
        h = self.h
        a = h[j, i] + (h[j, i + 1] - h[j, i]) * u + (h[j + 1, i] - h[j, i]) * v
        b = h[j + 1, i + 1] + (h[j + 1, i] - h[j + 1, i + 1]) * (1 - u) + (h[j, i + 1] - h[j + 1, i + 1]) * (1 - v)
        return np.where(u + v <= 1.0, a, b)

    def normal(self, x, y, e=0.5):
        dx = (self(x + e, y) - self(x - e, y)) / (2 * e)
        dy = (self(x, y + e) - self(x, y - e)) / (2 * e)
        return Vector((-dx, -dy, 1)).normalized()


# ---------------------------------------------------------------- scene
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def mesh_obj(name, verts, faces, collection=None, uvs=None, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(clean_customdata=False)
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    return ob


def import_obj(path, collection):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis='Y', up_axis='Z')
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        for c in o.users_collection:
            c.objects.unlink(o)
        collection.objects.link(o)
    return new


# ---------------------------------------------------------------- light (the game's)
SUN_DIR = Vector((-0.76, -0.40, 0.24)).normalized()   # toward the sun
SUN_COL = (1.48, 1.12, 0.80)
SKY_COL = (0.46, 0.55, 0.70)
GND_COL = (0.26, 0.28, 0.20)
HAZE_COL = (0.80, 0.72, 0.62)


def game_light(scene=None, strength_scale=1.0):
    scene = scene or bpy.context.scene
    for o in [o for o in scene.objects if o.type == 'LIGHT']:
        bpy.data.objects.remove(o)
    ld = bpy.data.lights.new('sun', 'SUN')
    # the game multiplies hero albedo by pi (hero.js), i.e. radiance = albedo * (sun * cos + hemisphere):
    # a Blender sun of strength S gives albedo * S * cos / pi, so S = |sun| * pi
    m = max(SUN_COL)
    ld.color = tuple(c / m for c in SUN_COL)
    ld.energy = m * math.pi * strength_scale
    ld.angle = math.radians(0.6)
    sun = bpy.data.objects.new('sun', ld)
    scene.collection.objects.link(sun)
    # light travels along -SUN_DIR; Blender sun shines along its local -Z
    sun.rotation_euler = (-SUN_DIR).to_track_quat('-Z', 'Y').to_euler()
    # world: hemisphere sky / ground; uniform radiance L gives albedo * L, the city's amb = hemisphere * ~0.9
    w = bpy.data.worlds.get('game') or bpy.data.worlds.new('game')
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = -1.0
    mr.inputs['From Max'].default_value = 1.0
    nt.links.new(sep.outputs['Z'], mr.inputs['Value'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    nt.links.new(mr.outputs[0], mix.inputs['Factor'])
    mix.inputs['A'].default_value = (*[c * 0.9 for c in GND_COL], 1)
    mix.inputs['B'].default_value = (*[c * 0.9 for c in SKY_COL], 1)
    # visible sky for the camera: brighter, warm toward the horizon (only matters for previews)
    lp = nt.nodes.new('ShaderNodeLightPath')
    skyv = nt.nodes.new('ShaderNodeMix'); skyv.data_type = 'RGBA'
    mr2 = nt.nodes.new('ShaderNodeMapRange')
    mr2.inputs['From Min'].default_value = 0.0
    mr2.inputs['From Max'].default_value = 0.6
    nt.links.new(sep.outputs['Z'], mr2.inputs['Value'])
    nt.links.new(mr2.outputs[0], skyv.inputs['Factor'])
    skyv.inputs['A'].default_value = (0.95, 0.80, 0.62, 1)
    skyv.inputs['B'].default_value = (0.42, 0.55, 0.78, 1)
    sel = nt.nodes.new('ShaderNodeMix'); sel.data_type = 'RGBA'
    nt.links.new(lp.outputs['Is Camera Ray'], sel.inputs['Factor'])
    nt.links.new(mix.outputs['Result'], sel.inputs['A'])
    nt.links.new(skyv.outputs['Result'], sel.inputs['B'])
    bg = nt.nodes.new('ShaderNodeBackground')
    nt.links.new(sel.outputs['Result'], bg.inputs['Color'])
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(bg.outputs[0], out.inputs[0])
    return sun


def view_setup(scene=None, exposure=0.3):
    scene = scene or bpy.context.scene
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = exposure


def camera(name, loc, target=None, heading=None, pitch=0.0, lens=24.0, scene=None):
    scene = scene or bpy.context.scene
    cd = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_start = 0.1
    cd.clip_end = 6000
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(ob)
    ob.location = Vector(loc)
    if target is not None:
        d = Vector(target) - Vector(loc)
    else:
        d = Vector((math.sin(heading) * math.cos(pitch), math.cos(heading) * math.cos(pitch), math.sin(pitch)))
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = ob
    return ob


def render(path, w=1600, h=900, engine='BLENDER_EEVEE', samples=64, scene=None):
    scene = scene or bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    if engine == 'CYCLES':
        scene.cycles.device = 'GPU'
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
    else:
        try:
            scene.eevee.taa_render_samples = samples
            scene.eevee.use_shadows = True
            scene.eevee.use_raytracing = True
        except Exception:
            pass
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def enable_gpu():
    prefs = bpy.context.preferences
    cp = prefs.addons['cycles'].preferences
    for t in ('OPTIX', 'CUDA'):
        try:
            cp.compute_device_type = t
            cp.get_devices()
            ok = False
            for d in cp.devices:
                d.use = d.type != 'CPU'
                ok = ok or d.use
            if ok:
                return t
        except Exception:
            continue
    return None


def rng(seed):
    return random.Random(seed)
