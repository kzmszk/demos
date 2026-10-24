"""Tiny node-graph helper for procedural texture materials (albedo + height + alpha).

A 'surface' is a python function (nb, co) -> dict(col=socket, h=socket|None, a=socket|None)
where co is the coordinate vector socket (object space, metres). Materials are wrapped in two
render modes: 'alb' (emission = albedo, alpha) and 'nrm' (emission = tangent-space normal).
"""
import math
import bpy


class NB:
    def __init__(self, nt):
        self.nt = nt
        self.N = nt.nodes
        self.L = nt.links

    def node(self, kind, **props):
        n = self.N.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.L.new(a, b)

    def _in(self, node, i, v):
        s = node.inputs[i]
        if isinstance(v, bpy.types.NodeSocket):
            self.link(v, s)
        elif v is not None:
            if isinstance(v, (tuple, list)) and len(v) == 3 and s.type == 'RGBA':
                v = (*v, 1.0)
            s.default_value = v

    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.node('ShaderNodeMath', operation=op, use_clamp=clamp)
        self._in(n, 0, a)
        if b is not None:
            self._in(n, 1, b)
        if c is not None:
            self._in(n, 2, c)
        return n.outputs[0]

    def add(self, a, b): return self.math('ADD', a, b)
    def sub(self, a, b): return self.math('SUBTRACT', a, b)
    def mul(self, a, b): return self.math('MULTIPLY', a, b)
    def mx(self, a, b): return self.math('MAXIMUM', a, b)
    def mn(self, a, b): return self.math('MINIMUM', a, b)

    def smooth(self, e0, e1, x):
        n = self.node('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
        self._in(n, 'Value', x); self._in(n, 'From Min', e0); self._in(n, 'From Max', e1)
        return n.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        n = self.node('ShaderNodeVectorMath', operation=op)
        self._in(n, 0, a)
        if b is not None:
            self._in(n, 1, b)
        if scale is not None:
            n.inputs['Scale'].default_value = scale
        return n.outputs[0] if op not in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else n.outputs['Value']

    def sep(self, v):
        n = self.node('ShaderNodeSeparateXYZ')
        self._in(n, 0, v)
        return n.outputs['X'], n.outputs['Y'], n.outputs['Z']

    def comb(self, x, y, z):
        n = self.node('ShaderNodeCombineXYZ')
        self._in(n, 0, x); self._in(n, 1, y); self._in(n, 2, z)
        return n.outputs[0]

    def rgb(self, c):
        n = self.node('ShaderNodeRGB')
        n.outputs[0].default_value = (*c[:3], 1)
        return n.outputs[0]

    def mix(self, f, a, b, blend='MIX'):
        n = self.node('ShaderNodeMix', data_type='RGBA', blend_type=blend)
        self._in(n, 'Factor', f)
        self._in(n, 6, a)
        self._in(n, 7, b)
        return n.outputs[2]

    def mixf(self, f, a, b):
        n = self.node('ShaderNodeMix', data_type='FLOAT')
        self._in(n, 'Factor', f); self._in(n, 2, a); self._in(n, 3, b)
        return n.outputs[0]

    def noise(self, co, scale=1.0, detail=4.0, rough=0.55, w=0.0, dim='4D', dist=0.0, color=False):
        n = self.node('ShaderNodeTexNoise', noise_dimensions=dim)
        self._in(n, 'Vector', co)
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        n.inputs['Distortion'].default_value = dist
        if dim == '4D':
            self._in(n, 'W', w)
        return n.outputs['Color'] if color else n.outputs['Fac']

    def voronoi(self, co, scale=1.0, feature='F1', out='Distance', w=0.0, dim='4D', rand=1.0):
        n = self.node('ShaderNodeTexVoronoi', voronoi_dimensions=dim, feature=feature)
        self._in(n, 'Vector', co)
        n.inputs['Scale'].default_value = scale
        n.inputs['Randomness'].default_value = rand
        if dim == '4D':
            self._in(n, 'W', w)
        return n.outputs[out]

    def ramp(self, x, stops):
        n = self.node('ShaderNodeValToRGB')
        self._in(n, 0, x)
        el = n.color_ramp.elements
        while len(el) < len(stops):
            el.new(0.5)
        for e, (p, c) in zip(el, stops):
            e.position = p
            e.color = (*c[:3], 1) if len(c) == 3 else c
        return n.outputs[0]

    def brick(self, co, scale=1.0, mortar=0.02, bw=0.5, rh=0.25, c1=(0.6, 0.5, 0.4), c2=(0.55, 0.45, 0.35), cm=(0.4, 0.4, 0.38), offset=0.5, smooth=0.1):
        n = self.node('ShaderNodeTexBrick')
        self._in(n, 'Vector', co)
        n.inputs['Scale'].default_value = scale
        n.inputs['Mortar Size'].default_value = mortar
        n.inputs['Brick Width'].default_value = bw
        n.inputs['Row Height'].default_value = rh
        n.inputs['Mortar Smooth'].default_value = smooth
        n.inputs['Color1'].default_value = (*c1, 1)
        n.inputs['Color2'].default_value = (*c2, 1)
        n.inputs['Mortar'].default_value = (*cm, 1)
        n.offset = offset
        return n.outputs['Color'], n.outputs['Fac']


def periodic_co(nb, period=None, seed=0.0):
    """Object-space coordinate; if period is set, x is wrapped onto a circle (seamless in x).
    Returns (vector socket for 3D/4D noise, raw (x,y,z))."""
    tc = nb.node('ShaderNodeTexCoord')
    obj = tc.outputs['Object']
    x, y, z = nb.sep(obj)
    if period:
        R = period / (2 * math.pi)
        ang = nb.mul(x, 2 * math.pi / period)
        cx = nb.mul(nb.math('SINE', ang), R)
        cy = nb.mul(nb.math('COSINE', ang), R)
        v = nb.comb(cx, nb.add(cy, nb.mul(y, 0.0)), z)
    else:
        v = obj
    return v, (x, y, z)


def torus_co(nb, px, py):
    """seamless in x (period px) and y (period py): returns (vec3, w) for 4D noise."""
    tc = nb.node('ShaderNodeTexCoord')
    x, y, z = nb.sep(tc.outputs['Object'])
    Rx = px / (2 * math.pi); Ry = py / (2 * math.pi)
    ax = nb.mul(x, 2 * math.pi / px); ay = nb.mul(y, 2 * math.pi / py)
    v = nb.comb(nb.mul(nb.math('SINE', ax), Rx), nb.mul(nb.math('COSINE', ax), Rx), nb.mul(nb.math('SINE', ay), Ry))
    w = nb.mul(nb.math('COSINE', ay), Ry)
    return v, w, (x, y, z)


def make_material(name, surface, period=None, mode='alb', seed=0.0, double=True, torus=None, flat=None):
    """Build a material in render mode 'alb' or 'nrm' from a surface function."""
    m = bpy.data.materials.new(f'{name}.{mode}')
    nt = m.node_tree
    nt.nodes.clear()
    nb = NB(nt)
    if torus:
        co, w, raw = torus_co(nb, *torus)
        s = surface(nb, co, raw, w)
    else:
        co, raw = periodic_co(nb, period, seed)
        s = surface(nb, co, raw, None)
    out = nb.node('ShaderNodeOutputMaterial')
    if mode == 'alb':
        em = nb.node('ShaderNodeEmission')
        nb.link(s['col'], em.inputs['Color'])
        em.inputs['Strength'].default_value = 1.0
        if s.get('a') is not None:
            tr = nb.node('ShaderNodeBsdfTransparent')
            mx = nb.node('ShaderNodeMixShader')
            nb.link(s['a'], mx.inputs[0])
            nb.link(tr.outputs[0], mx.inputs[1])
            nb.link(em.outputs[0], mx.inputs[2])
            nb.link(mx.outputs[0], out.inputs['Surface'])
        else:
            nb.link(em.outputs[0], out.inputs['Surface'])
    else:
        # tangent-space normal for a camera looking along +Y at an XZ facade (T=+X, B=+Z, N=-Y),
        # or along -Z at an XY sheet (T=+X, B=+Y, N=+Z) when the material is used flat.
        geo = nb.node('ShaderNodeNewGeometry')
        nrm = geo.outputs['Normal']
        if s.get('h') is not None:
            bump = nb.node('ShaderNodeBump')
            bump.inputs['Strength'].default_value = s.get('bump', 1.0)
            bump.inputs['Distance'].default_value = s.get('bumpd', 0.02)
            nb.link(s['h'], bump.inputs['Height'])
            nrm = bump.outputs['Normal']
        x, y, z = nb.sep(nrm)
        flat = s.get('flat', False) if flat is None else flat
        if flat:
            enc = nb.comb(x, y, z)
        else:
            enc = nb.comb(x, z, nb.mul(y, -1.0))
        enc = nb.vmath('MULTIPLY_ADD', enc, (0.5, 0.5, 0.5))
        n = enc.node
        n.inputs[2].default_value = (0.5, 0.5, 0.5)
        em = nb.node('ShaderNodeEmission')
        nb.link(enc, em.inputs['Color'])
        if s.get('a') is not None:
            tr = nb.node('ShaderNodeBsdfTransparent')
            mx = nb.node('ShaderNodeMixShader')
            nb.link(s['a'], mx.inputs[0])
            nb.link(tr.outputs[0], mx.inputs[1])
            nb.link(em.outputs[0], mx.inputs[2])
            nb.link(mx.outputs[0], out.inputs['Surface'])
        else:
            nb.link(em.outputs[0], out.inputs['Surface'])
    m.use_backface_culling = False
    return m
