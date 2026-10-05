"""Reproducible, restrained Nativity-only render grading; originals untouched.

This is an artistic scene-light harmonization, not a claim about measured stone
albedo. All figure pixels retain the source photograph's spatial detail. The
already-reviewed V8 masks preserve the children's face and narrow robe cores.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
DIR = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return str(path.relative_to(ROOT))


def main():
    specs_path = DIR / 'reliefs.json'
    specs = json.loads(specs_path.read_text())
    records = []
    stone_path = ROOT / 'assets/textures/nativity_stone_detail_base.png'
    stone = Image.open(stone_path).convert('RGB')
    # Track every source, masked input, V8 derivative and mask, plus the three
    # active Passion render images: this update must never modify any of them.
    protected = {}
    for spec in specs:
        source = ROOT / 'assets/reference' / spec['source']
        paths = [source, ROOT / spec['texture'], ROOT / spec['edge_transition_mask'],
                 DIR / (spec['id'] + '_edge_blended.png')]
        if spec['sign'] < 0:
            paths.append(ROOT / spec.get('render_texture', spec['texture']))
        for path in paths:
            protected[rel(path)] = digest(path)

    comparison = Image.new('RGB', (1050, 1580), '#e6e2d8')
    draw = ImageDraw.Draw(comparison)
    draw.text((20, 10), 'V8 render derivative (left) / restrained Nativity render grade (right)', fill='#28261f')
    row = 0
    for spec in specs:
        if spec['sign'] < 0:
            continue
        source_path = ROOT / spec['texture']
        original = Image.open(source_path).convert('RGBA')
        rgb = original.convert('RGB')
        alpha = original.getchannel('A')
        mask_path = ROOT / spec['edge_transition_mask']
        mask = Image.open(mask_path).convert('L')
        assert mask.size == original.size
        if spec['id'].startswith('Busquets_'):
            wb, brightness = (1.04, .997, .925), .94
        else:
            # Sotoo's later work remains visibly lighter than the aged facade.
            wb, brightness = (1.025, 1.005, .955), .96
        gains = tuple(value * brightness for value in wb)
        channels = [channel.point([min(255, max(0, round(i * gain))) for i in range(256)])
                    for channel, gain in zip(rgb.split(), gains)]
        graded = Image.merge('RGB', channels)
        resized_stone = stone.resize(rgb.size, Image.Resampling.BILINEAR)
        mixed = Image.composite(graded, resized_stone, mask).convert('RGBA')
        mixed.putalpha(alpha)
        output = DIR / (spec['id'] + '_nativity_warm_render.png')
        mixed.save(output, optimize=True)
        reloaded = Image.open(output).convert('RGBA')
        assert reloaded.size == original.size
        assert reloaded.getchannel('A').tobytes() == alpha.tobytes()
        # Pure photograph cores, including protected face interiors, must equal
        # the exact channel LUT result: no smoothing or invented facial detail.
        a_bytes = alpha.tobytes(); m_bytes = mask.tobytes()
        out_bytes = reloaded.convert('RGB').tobytes(); grade_bytes = graded.tobytes()
        core_count = 0
        for i, (a, m) in enumerate(zip(a_bytes, m_bytes)):
            if a and m == 255:
                assert out_bytes[i*3:i*3+3] == grade_bytes[i*3:i*3+3]
                core_count += 1
        spec['render_texture'] = rel(output)
        spec['return_material'] = 'nativity_stone_detail'
        spec['render_grade'] = 'Nativity-only restrained sRGB channel gains; original RGB detail and V8 face-protected transition mask preserved. See docs/NATIVITY_RENDER_GRADE.json.'
        records.append({
            'id': spec['id'], 'author': spec['author'], 'license': spec['license'],
            'capture_date': spec['date'],
            'original_photo': rel(ROOT / 'assets/reference' / spec['source']),
            'original_photo_sha256': digest(ROOT / 'assets/reference' / spec['source']),
            'masked_source_png': rel(source_path), 'masked_source_sha256': digest(source_path),
            'previous_v8_render_png': rel(DIR / (spec['id'] + '_edge_blended.png')),
            'previous_v8_render_sha256': digest(DIR / (spec['id'] + '_edge_blended.png')),
            'output_render_png': rel(output), 'output_sha256': digest(output),
            'dimensions': list(original.size), 'white_balance_gains_srgb': list(wb),
            'brightness_gain_srgb': brightness, 'net_channel_gains_srgb': list(gains),
            'channel_transform': 'round(source_8bit_sRGB * net_channel_gain), clamped to 0..255; no resampling, blur, sharpening or painted detail',
            'transition_mask': rel(mask_path), 'transition_mask_sha256': digest(mask_path),
            'transition_method': 'Unchanged V8 smooth UV edge mask, including protected choir faces/robes; composite(graded source, stone tile, mask). No alpha or mesh changes.',
            'neutral_return_texture': rel(stone_path), 'neutral_return_texture_sha256': digest(stone_path),
            'neutral_return_material': 'nativity_stone_detail',
            'core_pixels_verified_equal_to_exact_lut': core_count,
            'alpha_byte_identical': True,
            'limitation': 'Photograph-derived 2.5D relief; estimated shallow depth and neutral unseen returns. Grade is restrained scene harmonization, not measured artwork albedo.'
        })
        y0 = 45 + row * 380
        draw.text((20, y0), spec['id'], fill='#28261f')
        before = Image.open(DIR / (spec['id'] + '_edge_blended.png')).convert('RGBA')
        for x0, im in [(20, before), (535, mixed)]:
            im.thumbnail((495, 345), Image.Resampling.LANCZOS)
            backdrop = Image.new('RGBA', (495, 345), (158, 140, 111, 255))
            backdrop.alpha_composite(im, ((495-im.width)//2, (345-im.height)//2))
            comparison.paste(backdrop.convert('RGB'), (x0, y0+20))
        row += 1

    assert all(digest(ROOT / path) == checksum for path, checksum in protected.items())
    specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2) + '\n')
    review_path = ROOT / 'docs/NATIVITY_RENDER_GRADE_comparison.jpg'
    comparison.save(review_path, quality=92)
    report = {
        'scope': 'Four Nativity photo relief render textures and their neutral return material only. Passion, stained glass, source photographs, masked source PNGs, V8 textures/masks, and geometry unchanged.',
        'implementation': rel(Path(__file__)), 'implementation_sha256': digest(Path(__file__)),
        'render_compatibility': 'Baked RGBA PNGs directly connected to Principled Base Color; no new shader-node dependency, lighting change or emission.',
        'all_protected_source_hashes_unchanged': True,
        'protected_file_count': len(protected), 'protected_sha256': protected,
        'records': records, 'comparison_image': rel(review_path),
        'final_scene_review': 'CPU derivative inspection only; integrated Blender and real-time lighting must be reviewed separately.'
    }
    report_path = ROOT / 'docs/NATIVITY_RENDER_GRADE.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    ledger_path = ROOT / 'docs/EXTERIOR_EVIDENCE.json'
    ledger = json.loads(ledger_path.read_text())
    ledger['nativity_render_harmonization'] = {
        'report': rel(report_path), 'comparison': rel(review_path),
        'source_and_previous_derivatives_unchanged': True,
        'records': records,
        'scope_limit': report['scope']
    }
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'graded_nativity': len(records), 'protected_files_unchanged': len(protected),
                      'photo_core_pixels': sum(r['core_pixels_verified_equal_to_exact_lut'] for r in records),
                      'report': rel(report_path), 'comparison': rel(review_path)}))


if __name__ == '__main__':
    main()
