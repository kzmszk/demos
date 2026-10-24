"""Texture factory infrastructure: orthographic Cycles 'shots' of small scenes rendered as albedo and
tangent-space normal (emission), read back into numpy, composed into atlases, saved as PNG."""
import math
import os
import random

import bpy
import numpy as np

from sb_nodes import NB, make_material
from sb_common import TEX, enable_gpu, FONT_JP, FONT_JP_R

TMP = os.path.join(TEX, 'tmp')
os.makedirs(TMP, exist_ok=True)

_fonts = {}


def font(path=FONT_JP):
    if path not in _fonts:
        _fonts[path] = bpy.data.fonts.load(path)
    return _fonts[path]


def lin2srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def srgb2lin(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.04045, c / 12.92, np.power((c + 0.055) / 1.055, 2.4))


def save_png(arr, path, colorspace='sRGB', encode_srgb=True):
    """arr: (h, w, 3|4) float, top row first, linear if encode_srgb."""
    h, w = arr.shape[:2]
    a = np.ones((h, w, 4), np.float32)
    if encode_srgb:
        a[..., :3] = lin2srgb(arr[..., :3])
    else:
        a[..., :3] = np.clip(arr[..., :3], 0, 1)
    if arr.shape[2] == 4:
        a[..., 3] = np.clip(arr[..., 3], 0, 1)
    name = os.path.basename(path)
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = 'sRGB' if colorspace == 'sRGB' else 'Non-Color'
    img.pixels.foreach_set(a[::-1].ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)


def load_png(path, linear=True):
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    a = a.reshape(h, w, 4)[::-1].copy()
    if linear:
        a[..., :3] = srgb2lin(a[..., :3])
    return a


def resize(arr, h, w):
    """area-average / bilinear resize of (H, W, C) float array."""
    H, W = arr.shape[:2]
    if (H, W) == (h, w):
        return arr
    # separable linear interpolation on pixel centres, with box prefilter when shrinking
    def axis_resize(a, n, axis):
        N = a.shape[axis]
        if n == N:
            return a
        if n < N:
            f = N / n
            k = max(1, int(round(f)))
            if k > 1:
                # box filter
                c = np.cumsum(np.concatenate([np.zeros_like(np.take(a, [0], axis=axis)), a], axis=axis), axis=axis)
                idx0 = np.clip((np.arange(n) * f).astype(int), 0, N - 1)
                idx1 = np.clip(((np.arange(n) + 1) * f).astype(int), 1, N)
                idx1 = np.maximum(idx1, idx0 + 1)
                s = np.take(c, idx1, axis=axis) - np.take(c, idx0, axis=axis)
                cnt = (idx1 - idx0).astype(np.float32)
                shape = [1] * a.ndim; shape[axis] = n
                return s / cnt.reshape(shape)
        x = (np.arange(n) + 0.5) * N / n - 0.5
        x0 = np.clip(np.floor(x).astype(int), 0, N - 1)
        x1 = np.clip(x0 + 1, 0, N - 1)
        t = (x - x0).astype(np.float32)
        shape = [1] * a.ndim; shape[axis] = n
        t = t.reshape(shape)
        return np.take(a, x0, axis=axis) * (1 - t) + np.take(a, x1, axis=axis) * t
    a = axis_resize(arr, h, 0)
    return axis_resize(a, w, 1)


class Shot:
    """A small scene rendered orthographically.

    plane='XZ': a facade. image x -> world X, image up -> world Z; camera looks along +Y
                (geometry with y > 0 is behind the facade surface).
    plane='XY': a sheet seen from above. image x -> X, image up -> Y; camera looks along -Z.
    """

    def __init__(self, name, x0, x1, v0, v1, res_x, plane='XZ', period=None, torus=None, alpha=False, samples=12):
        self.name = name
        self.x0, self.x1, self.v0, self.v1 = x0, x1, v0, v1
        self.res_x = res_x
        self.res_y = max(1, int(round(res_x * (v1 - v0) / (x1 - x0))))
        self.plane = plane
        self.period = period
        self.torus = torus
        self.alpha = alpha
        self.samples = samples
        self.sc = bpy.data.scenes.new(name)
        self.items = []    # (object, surface)
        self.rnd = random.Random(hash(name) & 0xffff)

    # ---------------------------------------------------------- geometry
    def _link(self, ob, surf):
        self.sc.collection.objects.link(ob)
        self.items.append((ob, surf))
        return ob

    def mesh(self, verts, faces, surf, name='m'):
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.validate()
        ob = bpy.data.objects.new(name, me)
        return self._link(ob, surf)

    def box(self, x0, x1, a0, a1, d0, d1, surf, name='box', origin=None):
        """XZ plane: x, z(a), y(d: depth, + = behind). XY plane: x, y(a), z(d: height, + = up).
        origin=(x, a, d): object origin (object-space coords are then relative to it)."""
        ox, oa, od = origin if origin else (0.0, 0.0, 0.0)
        if self.plane == 'XZ':
            P = lambda x, a, d: (x - ox, d - od, a - oa)
        else:
            P = lambda x, a, d: (x - ox, a - oa, d - od)
        v = [P(x0, a0, d0), P(x1, a0, d0), P(x1, a1, d0), P(x0, a1, d0),
             P(x0, a0, d1), P(x1, a0, d1), P(x1, a1, d1), P(x0, a1, d1)]
        f = [(0, 1, 2, 3), (5, 4, 7, 6), (1, 5, 6, 2), (4, 0, 3, 7), (3, 2, 6, 7), (4, 5, 1, 0)]
        if self.plane == 'XY':
            f = [tuple(reversed(t)) for t in f]
        ob = self.mesh(v, f, surf, name)
        if origin:
            ob.location = (ox, od, oa) if self.plane == 'XZ' else (ox, oa, od)
        return ob

    def poly(self, pts2d, d, surf, name='poly'):
        """flat polygon in the image plane at depth d."""
        if self.plane == 'XZ':
            v = [(x, d, a) for x, a in pts2d]
        else:
            v = [(x, a, d) for x, a in pts2d]
        f = [tuple(range(len(v)))]
        ob = self.mesh(v, f, surf, name)
        return ob

    def leafmesh(self, leaves, surf, name='leaves'):
        """leaves: list of (cx, ca, cd, size, angle, tilt, (r,g,b)); ivy-ish 7-gon leaves facing the camera,
        tilted by 'tilt' (rad) around their own axis so the normal pass shows facets."""
        V = []; F = []; C = []
        shape = [(0.0, -0.5), (0.42, -0.1), (0.5, 0.25), (0.22, 0.42), (0.0, 0.6), (-0.22, 0.42), (-0.5, 0.25), (-0.42, -0.1)]
        for (cx, ca, cd, sz, ang, tilt, col) in leaves:
            ca_, sa = math.cos(ang), math.sin(ang)
            ct, st = math.cos(tilt), math.sin(tilt)
            i0 = len(V)
            for (u, v) in shape:
                u *= sz; v *= sz
                x = u * ca_ - v * sa
                a = u * sa + v * ca_
                d = cd - x * st * 0.6 - a * 0.25 * abs(st)
                x = x * ct
                if self.plane == 'XZ':
                    V.append((cx + x, d, ca + a))
                else:
                    V.append((cx + x, ca + a, cd - d + cd))
            F.append(tuple(range(i0, i0 + len(shape))) if self.plane == 'XZ' else tuple(reversed(range(i0, i0 + len(shape)))))
            C.append(col)
        me = bpy.data.meshes.new(name)
        me.from_pydata(V, [], F)
        me.validate()
        at = me.color_attributes.new('lc', 'FLOAT_COLOR', 'FACE')
        at.data.foreach_set('color', np.array([(*c, 1.0) for c in C], np.float32).ravel())
        ob = bpy.data.objects.new(name, me)
        return self._link(ob, surf)

    def text(self, body, x, a, size, surf, d=-0.005, fnt=None, align='CENTER', valign='CENTER', rot=0.0,
             spacing=1.0, vertical=False, name='txt'):
        cu = bpy.data.curves.new(name, 'FONT')
        cu.font = fnt or font()
        if vertical:
            body = '\n'.join(list(body))
            cu.space_line = 0.95
        cu.body = body
        cu.size = size
        cu.align_x = align
        cu.align_y = valign
        cu.space_character = spacing
        ob = bpy.data.objects.new(name, cu)
        if self.plane == 'XZ':
            ob.location = (x, d, a)
            ob.rotation_euler = (math.pi / 2, rot, 0)
        else:
            ob.location = (x, a, d)
            ob.rotation_euler = (0, 0, rot)
        return self._link(ob, surf)

    # ---------------------------------------------------------- render
    def _setup(self):
        sc = self.sc
        sc.render.engine = 'CYCLES'
        sc.cycles.device = 'GPU'
        sc.cycles.samples = self.samples
        sc.cycles.use_denoising = False
        sc.cycles.max_bounces = 0
        sc.cycles.pixel_filter_type = 'BLACKMAN_HARRIS'
        sc.cycles.filter_width = 1.2
        sc.render.resolution_x = self.res_x
        sc.render.resolution_y = self.res_y
        sc.render.resolution_percentage = 100
        sc.render.film_transparent = True
        sc.render.image_settings.file_format = 'OPEN_EXR'
        sc.render.image_settings.color_depth = '32'
        sc.render.image_settings.color_mode = 'RGBA'
        sc.view_settings.view_transform = 'Standard'
        w = bpy.data.worlds.new(self.name + '_w')
        w.color = (0, 0, 0)
        sc.world = w
        cd = bpy.data.cameras.new(self.name + '_cam')
        cd.type = 'ORTHO'
        W = self.x1 - self.x0; Hh = self.v1 - self.v0
        cd.ortho_scale = max(W, Hh)
        cd.clip_start = 0.01; cd.clip_end = 400
        cam = bpy.data.objects.new(self.name + '_cam', cd)
        sc.collection.objects.link(cam)
        cx = 0.5 * (self.x0 + self.x1); cv = 0.5 * (self.v0 + self.v1)
        if self.plane == 'XZ':
            cam.location = (cx, -100, cv)
            cam.rotation_euler = (math.pi / 2, 0, 0)
        else:
            cam.location = (cx, cv, 100)
            cam.rotation_euler = (0, 0, 0)
        sc.camera = cam
        # periodic copies for seamless facades: duplicate everything at +-period
        if self.period:
            for ob, surf in list(self.items):
                for s in (-1, 1):
                    c = ob.copy()
                    c.location = (ob.location[0] + s * self.period, ob.location[1], ob.location[2])
                    sc.collection.objects.link(c)
                    self.items.append((c, surf))

    def render(self):
        self._setup()
        res = {}
        cache = {}
        for mode in ('alb', 'nrm'):
            for ob, surf in self.items:
                key = (id(surf), mode)
                if key not in cache:
                    cache[key] = make_material(getattr(surf, '__name__', 'surf'), surf, period=self.period,
                                               torus=self.torus, mode=mode, flat=(self.plane == 'XY'))
                m = cache[key]
                if ob.type == 'MESH' or ob.type == 'FONT':
                    ob.data.materials.clear()
                    ob.data.materials.append(m)
            path = os.path.join(TMP, f'{self.name}_{mode}.exr')
            self.sc.render.filepath = path
            bpy.ops.render.render(write_still=True, scene=self.sc.name)
            img = bpy.data.images.load(path)
            w, h = img.size
            a = np.empty(w * h * 4, np.float32)
            img.pixels.foreach_get(a)
            bpy.data.images.remove(img)
            res[mode] = a.reshape(h, w, 4)[::-1].copy()
        alb = res['alb']
        nrm = res['nrm']
        # un-premultiply (film transparent) and fill empty normal with flat
        A = alb[..., 3:4]
        alb[..., :3] = np.where(A > 1e-4, alb[..., :3] / np.maximum(A, 1e-4), 0)
        nA = nrm[..., 3:4]
        nrm[..., :3] = np.where(nA > 1e-4, nrm[..., :3] / np.maximum(nA, 1e-4), 0)
        nrm[..., :3] = nrm[..., :3] * nA + np.array([0.5, 0.5, 1.0]) * (1 - nA)
        return alb, nrm

    def cleanup(self):
        for ob, _s in self.items:
            try:
                bpy.data.objects.remove(ob, do_unlink=True)
            except Exception:
                pass
        bpy.data.scenes.remove(self.sc)
