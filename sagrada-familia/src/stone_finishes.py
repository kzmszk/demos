"""Restricted, photo-informed construction joints for the V12 Web study.

CPU preparation (existing numpy/Pillow environment):
    python src/stone_finishes.py --prepare
Blender integration, after model modules and before geographic reflection:
    import stone_finishes
    stone_finishes.apply(ctx)

Only copies of six stone materials and explicitly named vertical faces change.
Original geometry, UVs, materials, photos, glazing and lighting stay untouched.
The photograph establishes the construction character, not surveyed dimensions.
No Blender procedural node is required by the glTF/runtime result.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DEST = Path('assets/textures/stone_finishes_v12')
KINDS = {'wall': ('stone', 'stone_light'),
         'shaft': ('sandstone', 'granite', 'basalt', 'porphyry')}
WALL_NAMES = frozenset((
    'Side_wall_structural_pier', 'Side_wall_low_sill', 'Side_wall_upper_band',
    'Central_clerestory_pier', 'Central_clerestory_sill', 'Central_clerestory_top',
    'Transept_return_wall',
))
SHAFT_PATTERN = re.compile(
    r'^(?:Aisle_Montjuic|Nave_granite|Crossing_porphyry|Crossing_basalt|'
    r'Transept_granite|Apse_horseshoe|Ambulatory)_.+_double_helicoid$')
WINDOW_STONE_PATTERN = re.compile(r'^Side_([+-]?1)_([0-4])_stone_light$')
# Reference channel means from the frozen first construction-finish candidate.
# Keep this A/B about local construction contrast, not overall colour/exposure.
FIRST_CANDIDATE_MEAN_RGB = {
    'wall_stone': (179.28588008880615, 164.3042755126953, 142.24900722503662),
    'wall_stone_light': (204.3148307800293, 194.32332038879395, 174.41578006744385),
    'shaft_sandstone': (184.46326065063477, 169.46399402618408, 144.46906185150146),
    'shaft_granite': (172.05274391174316, 173.0883274078369, 170.08266258239746),
    'shaft_basalt': (100.37560749053955, 103.38528060913086, 100.38492965698242),
    'shaft_porphyry': (154.3082275390625, 125.44564914703369, 117.38830852508545),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selected_kind(name):
    """An allowlist, never an all-stone or all-curved-surface operation."""
    name = re.sub(r'\.\d+$', '', name)
    if name in WALL_NAMES or WINDOW_STONE_PATTERN.fullmatch(name):
        return 'wall'
    if SHAFT_PATTERN.fullmatch(name):
        return 'shaft'
    return None


def window_stone_face_ok(name, area, normal, center):
    """Wide side-window stone faces, excluding fine reveals and rose ribs.

    This matches Batch.finish's stone-only object; photographed glass has a
    different object and material. Global X/Z keep the existing wall UV phase.
    A face-area threshold avoids decorating the densely tessellated tiny rings.
    """
    match = WINDOW_STONE_PATTERN.fullmatch(re.sub(r'\.\d+$', '', name))
    if not match:
        return True
    if area < .06 or abs(normal[2]) >= .25 or abs(normal[1]) <= .75:
        return False
    window_x = 3.75 + 7.5*int(match.group(2))
    for bottom, top in ((3.3, 15.15), (18.05, 27.7)):
        height = top-bottom
        rose_z = bottom + height*.869
        rose_radius = min(height*.121, 6.1*.38)
        if (center[0]-window_x)**2 + (center[2]-rose_z)**2 < (rose_radius*1.08)**2:
            return False
    return True


def prepare(root=ROOT):
    """Compose three portable PBR maps per finish; no photographs are sampled."""
    import numpy as np
    from PIL import Image, ImageDraw
    root = Path(root)
    base = root / 'assets/textures'
    dest = root / DEST
    dest.mkdir(parents=True, exist_ok=True)
    source = json.loads((base / 'stone_pbr_web_v11/profile.json').read_text())
    n = 1024
    metres = 2.0
    texel = metres / n
    y, x = np.indices((n, n), dtype=float)
    u, v = (x + .5) / n, 1 - (y + .5) / n
    protected = [p for p in base.rglob('*') if p.is_file() and dest not in p.parents]
    protected += [root / 'src/materials.py', root / 'src/glazing.py']
    before = {str(p.relative_to(root)): sha(p) for p in protected}
    data = {
        'schema_version': 1, 'name': 'stone_finishes_v12',
        'candidate': 'Final V11 construction finish: stronger wall blocks, restrained shaft sections; v12 is an internal stage name.',
        'source_profile': 'web_v11', 'tile_metres': metres, 'size_px': [n, n],
        'license': 'Original procedural artwork; no photographic pixels used.',
        'reference_only': [{
            'file': 'assets/reference/qa_tree_vault.jpg',
            'observation': 'Cut-stone horizontal courses and staggered vertical joints around left windows; thin horizontal section joints on lower shafts.',
            'photo_capture_date': 'unverified',
        }],
        'dimension_status': 'All joint dimensions, colour variation and response are visual estimates, not measurements of the basilica.',
        'scope': {'wall_names': sorted(WALL_NAMES), 'shaft_regex': SHAFT_PATTERN.pattern,
                  'window_stone_regex': WINDOW_STONE_PATTERN.pattern,
                  'window_stone_face_limits': 'Area >=0.06m2, abs(normal.z)<0.25, abs(normal.y)>0.75; rose interior and fine ribs excluded.',
                  'faces': 'Vertical faces only; original V=z/2 UV confirmed per face.',
                  'excluded': 'Capitals, branches, vaults, roofs, organic carving, apse radial walls, floor, photo-reliefs and all glazing.'},
        'construction': {
            'wall': {'course_height_m': 1/3, 'block_length_m': 2/3, 'joint_width_m': .006,
                     'groove_depth_estimate_m': .00065, 'block_albedo_linear_variation': .13,
                     'joint_linear_darkness': .27},
            'shaft': {'section_height_m': 1.0, 'joint_width_m': .004,
                      'groove_depth_estimate_m': .00045, 'section_albedo_linear_variation': .035,
                      'joint_linear_darkness': .18,
                      'vertical_joints': 'Omitted: dominant-axis U seams would create false brick-like jumps.'},
        },
        'materials': {},
        'protected_source_sha256': before,
    }
    sheet = Image.new('RGB', (1100, 100 + 6*280), (240, 239, 235))
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 14), 'CONSTRUCTION FINISH STUDY | Raw 2m texture samples, NOT a render', fill=(30, 30, 30))
    draw.text((18, 35), 'Same stone grain + thin estimated joints. Chrome with actual geometry is the acceptance test.', fill=(55, 55, 55))
    draw.text((18, 58), 'Original base / new base / new normal / roughness. Labels give physical joint spacing.', fill=(55, 55, 55))

    def save(a, path):
        temp = path.with_name(path.name + '.pending')
        Image.fromarray(a).save(temp, format='PNG', optimize=True)
        temp.replace(path)

    def srgb_to_linear(a):
        return np.where(a <= .04045, a/12.92, ((a+.055)/1.055)**2.4)

    def linear_to_srgb(a):
        return np.where(a <= .0031308, a*12.92, 1.055*np.maximum(a, 0)**(1/2.4)-.055)

    def quantize_preserving_mean(a, target):
        # Sub-LSB balanced rounding locks all three first-candidate channel sums.
        # It has no low-frequency pattern and does not create an ageing tint.
        a = np.clip(a + np.asarray(target)-a.mean((0, 1)), 0, 255)
        result = np.round(a).astype('uint8')
        for channel in range(3):
            q = result[..., channel].copy().ravel()
            raw = a[..., channel].ravel()
            difference = int(round(target[channel]*q.size)) - int(q.sum())
            if difference:
                sign = 1 if difference > 0 else -1
                score = (raw-q.astype(float))*sign
                score[(q == 255) if sign > 0 else (q == 0)] = -np.inf
                count = abs(difference)
                chosen = np.argpartition(score, -count)[-count:]
                q[chosen] = q[chosen].astype('int16') + sign
                result[..., channel] = q.reshape(n, n)
        return result

    row_index = 0
    for kind, keys in KINDS.items():
        for key in keys:
            ident = kind+'_'+key
            origin = source['materials'][key]
            input_paths = {channel: base / origin[channel]['file'] for channel in ('base', 'rough', 'normal')}
            for channel, path in input_paths.items():
                if sha(path) != origin[channel]['sha256']:
                    raise ValueError('Source PBR hash changed: ' + str(path))
            rgb8 = np.asarray(Image.open(input_paths['base']).convert('RGB'))
            rough = np.asarray(Image.open(input_paths['rough']).convert('L'), dtype=float)/255
            normal = np.asarray(Image.open(input_paths['normal']).convert('RGB'), dtype=float)/127.5 - 1
            if rgb8.shape != (n, n, 3):
                raise ValueError('Expected 1024px source texture: ' + key)
            rng = np.random.default_rng(12000 + sum(ord(c) for c in key))
            if kind == 'wall':
                row = np.floor(v*6).astype(int) % 6
                along = u*3 - .5*(row % 2)
                col = np.floor(along).astype(int) % 3
                dh = np.abs((v*6+.5) % 1 - .5) * (metres/6)
                dv = np.abs((along+.5) % 1 - .5) * (metres/3)
                distance = np.minimum(dh, dv)
                values = rng.uniform(-1, 1, (6, 3))
                values -= values.mean()
                values /= max(float(np.max(np.abs(values))), .001)
                normalized_block = values[row, col]
                variation = normalized_block * .13
                rough_variation = normalized_block * .035
                width, depth, darkness = .006, .00065, .27
            else:
                row = np.floor(v*2).astype(int) % 2
                distance = np.abs((v*2+.5) % 1 - .5) * (metres/2)
                normalized_block = np.where(row == 0, -1., 1.)
                variation = normalized_block * .035
                # Preserve the first candidate's .035/.055*.021 amplitude.
                rough_variation = normalized_block * (.035/.055) * .021
                width, depth, darkness = .004, .00045, .18
            # A narrow smooth recess: no black outlines, painted cavities or cracks.
            # The transition spans enough texels for antialiasing at native 1K.
            recess = np.exp(-(distance/(width*.52))**4)
            linear = srgb_to_linear(rgb8.astype(float)/255)
            linear *= (1 + variation)[..., None]
            linear *= (1 - darkness*recess)[..., None]
            result_rgb = quantize_preserving_mean(np.clip(linear_to_srgb(linear), 0, 1)*255,
                                                  FIRST_CANDIDATE_MEAN_RGB[ident])
            result_rough = np.round(np.clip(rough + rough_variation + .055*recess, 0, 1)*255).astype('uint8')
            height = -depth*recess
            # PNG rows run opposite the tangent-space V direction.
            gx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1))/(2*texel)
            gy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0))/(2*texel)
            sx = normal[..., 0]/np.maximum(normal[..., 2], .1) - gx
            sy = normal[..., 1]/np.maximum(normal[..., 2], .1) + gy
            composite = np.stack((sx, sy, np.ones_like(sx)), axis=-1)
            composite /= np.linalg.norm(composite, axis=-1, keepdims=True)
            result_normal = np.round(np.clip((composite*.5+.5)*255, 0, 255)).astype('uint8')
            item = {'source_key': key, 'kind': kind,
                    'source': {c: {'file': origin[c]['file'], 'sha256': sha(input_paths[c])} for c in input_paths},
                    'normal_strength': origin['normal_strength'],
                    'statistics': {'mean_rgb_before': rgb8.mean((0, 1)).tolist(),
                                   'mean_rgb_first_candidate': list(FIRST_CANDIDATE_MEAN_RGB[ident]),
                                   'mean_rgb_after': result_rgb.mean((0, 1)).tolist(),
                                   'mean_rgb_first_candidate_drift': float(np.max(np.abs(result_rgb.mean((0, 1))-FIRST_CANDIDATE_MEAN_RGB[ident]))),
                                   'albedo_mip16_std255': float(np.asarray(Image.fromarray(result_rgb).resize((16,16), Image.Resampling.BOX),dtype=float).mean(2).std()),
                                   'joint_coverage_fraction': float((recess > .5).mean()),
                                   'roughness_mean': float(result_rough.mean()/255),
                                   'roughness_std': float(result_rough.std()/255)}}
            for channel, array in [('base', result_rgb), ('rough', result_rough), ('normal', result_normal)]:
                path = dest / (ident+'_'+channel+'.png')
                save(array, path)
                item[channel] = {'file': str(path.relative_to(base)), 'sha256': sha(path)}
            data['materials'][ident] = item
            yy = 98 + row_index*280
            draw.text((18, yy), ident + (' | 0.333m courses / 0.667m blocks / 6mm joint' if kind == 'wall' else ' | 1m sections / 4mm joint'), fill=(35, 35, 35))
            for i, array in enumerate((rgb8, result_rgb, result_normal, result_rough)):
                sample = Image.fromarray(array).convert('RGB').resize((250, 250), Image.Resampling.LANCZOS)
                sheet.paste(sample, (18+i*268, yy+20))
            row_index += 1

    unchanged = all(sha(root / path) == digest for path, digest in before.items())
    if not unchanged:
        raise AssertionError('A protected source changed during preparation')
    data['protected_sources_unchanged'] = unchanged
    data['protected_source_count'] = len(before)
    (dest/'manifest.json').write_text(json.dumps(data, indent=2)+'\n')
    sheet.save(dest/'raw_texture_comparison.png')
    (dest/'README.txt').write_text(
        'STONE FINISHES V12: CPU study, pending actual Chrome review.\n'
        'Source profile: web_v11. Original materials.py, glass and photographs unchanged.\n'
        'Call stone_finishes.apply(ctx) after builders and before geographic reflection.\n'
        'Only allowlisted vertical faces receive copied materials. Dimensions are estimates.\n'
        '18 PBR PNG maps, each1024px,2m period. manifest.json records hashes and sources.\n'
        'raw_texture_comparison.png is a CPU texture plate, not a rendered scene.\n')
    return data


def apply(ctx):
    """Copy/assign prepared materials without changing any source material or UV.

    Requires materials.build_materials(..., stone_profile='web_v11'). The check
    fails closed if another profile or a changed source image would be replaced.
    Idempotent on already finished objects; records exact names and face counts.
    """
    import bpy
    root = Path(ctx['root'])
    manifest = json.loads((root / DEST / 'manifest.json').read_text())
    M = ctx['M']
    materials = {}
    report = {'name': manifest['name'], 'source_profile': manifest['source_profile'],
              'window_stone_regex': WINDOW_STONE_PATTERN.pattern,
              'window_stone_face_limits': 'Area >=0.06m2, abs(normal.z)<0.25, abs(normal.y)>0.75; rose interior and fine ribs excluded.',
              'objects': [], 'copied_materials': [], 'skipped_already_applied': [],
              'excluded_geometry_and_photos_unchanged': True,
              'dimension_status': manifest['dimension_status']}

    def finish_material(ident):
        if ident in materials:
            return materials[ident]
        data = manifest['materials'][ident]
        source = M[data['source_key']]
        if source.get('stone_profile') != 'web_v11':
            raise ValueError('stone_finishes requires SAGRADA_STONE_PROFILE=web_v11: ' + source.name)
        # Each texture is uniquely identified by its source path. This does not
        # rewrite any image node outside the copied material.
        source_images = {}
        for node in source.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                path = Path(bpy.path.abspath(node.image.filepath)).resolve()
                source_images[path] = node.name
        for channel in ('base', 'rough', 'normal'):
            item = data['source'][channel]
            path = (root/'assets/textures'/item['file']).resolve()
            if path not in source_images or sha(path) != item['sha256']:
                raise ValueError('Source material/image mismatch: ' + ident + ' ' + channel)
            final = root/'assets/textures'/data[channel]['file']
            if sha(final) != data[channel]['sha256']:
                raise ValueError('Prepared finish image hash mismatch: ' + str(final))
        result = source.copy()
        result.name = source.name + ' | V12 '+data['kind']+' construction joints'
        for channel in ('base', 'rough', 'normal'):
            oldpath = (root/'assets/textures'/data['source'][channel]['file']).resolve()
            node = result.node_tree.nodes[source_images[oldpath]]
            node.image = bpy.data.images.load(str(root/'assets/textures'/data[channel]['file']), check_existing=True)
            node.image.colorspace_settings.name = 'sRGB' if channel == 'base' else 'Non-Color'
        result['stone_finish'] = ident
        result['joint_dimensions_are_estimates'] = True
        materials[ident] = result
        report['copied_materials'].append({'key': ident, 'name': result.name, 'source_name': source.name})
        return result

    # Validate and collect every face before committing material assignments.
    pending = []
    for obj in list(bpy.context.scene.objects):
        kind = selected_kind(obj.name)
        if obj.type != 'MESH' or kind is None:
            continue
        if obj.get('stone_finish_v12'):
            report['skipped_already_applied'].append(obj.name)
            continue
        mesh = obj.data
        if not mesh.uv_layers:
            raise ValueError('Missing original UV: ' + obj.name)
        uv = mesh.uv_layers[0].data
        assignment = {}
        is_window_stone = bool(WINDOW_STONE_PATTERN.fullmatch(re.sub(r'\.\d+$', '', obj.name)))
        for face in mesh.polygons:
            if is_window_stone:
                if not window_stone_face_ok(obj.name, face.area, face.normal, face.center):
                    continue
            elif abs(face.normal.z) >= (.5 if kind == 'shaft' else .1):
                continue
            material = mesh.materials[face.material_index]
            matches = [key for key in KINDS[kind] if material == M[key]]
            if len(matches) != 1:
                raise ValueError('Unexpected selected source material: ' + obj.name)
            for li in face.loop_indices:
                coord = mesh.vertices[mesh.loops[li].vertex_index].co
                if abs(uv[li].uv.y - coord.z/2) > .0001:
                    raise ValueError('Original UV metre scale mismatch: '+obj.name)
            ident = kind+'_'+matches[0]
            assignment.setdefault(ident, []).append(face.index)
        if not assignment:
            raise ValueError('No valid vertical faces selected: ' + obj.name)
        pending.append((obj, assignment))
    if not pending and not report['skipped_already_applied']:
        raise ValueError('No explicit stone finish objects found; call after model builders.')
    for obj, assignment in pending:
        for ident in assignment:
            finish_material(ident)
    for obj, assignment in pending:
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        mesh = obj.data
        for ident, faces in assignment.items():
            index = len(mesh.materials)
            mesh.materials.append(materials[ident])
            for face_index in faces:
                mesh.polygons[face_index].material_index = index
        obj['stone_finish_v12'] = ','.join(sorted(assignment))
        report['objects'].append({'name': obj.name, 'kind': selected_kind(obj.name),
                                  'changed_faces': sum(map(len, assignment.values())),
                                  'total_faces': len(mesh.polygons),
                                  'uv_and_geometry_unchanged': True,
                                  'materials': sorted(assignment)})
    report['changed_object_count'] = len(report['objects'])
    report['changed_face_count'] = sum(o['changed_faces'] for o in report['objects'])
    report['material_count'] = len(materials)
    ctx['stone_finishes_report'] = report
    dest = root/'logs/stone_finishes_v12_apply.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2)+'\n')
    print('STONE FINISHES', report['changed_object_count'], 'objects,', report['material_count'], 'copied materials', flush=True)
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    if not args.prepare:
        parser.error('Use --prepare for CPU maps, or import apply(ctx) inside Blender.')
    result = prepare()
    print(json.dumps({'materials': len(result['materials']),
                      'protected_source_count': result['protected_source_count'],
                      'protected_sources_unchanged': result['protected_sources_unchanged'],
                      'manifest': str(ROOT / DEST / 'manifest.json')}, indent=2))
