#!/usr/bin/env python3
"""CPU-only source inventory and syntax validation; never imports Blender/Godot.

Use --strict to check immutable release asset hashes. Default mode permits edits.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def validate(strict=False):
    errors = []
    ledger = json.loads((ROOT / 'docs/ASSET_PUBLICATION.json').read_text())
    rows = ledger['included']
    for row in rows:
        path = ROOT / row['path']
        if not path.is_file():
            errors.append('Missing source ingredient: ' + row['path'])
        elif strict and hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            errors.append('Release hash differs: ' + row['path'])
    for row in ledger['excluded']:
        if strict and (ROOT / row['path']).exists():
            errors.append('Excluded research asset present: ' + row['path'])
    count = {'python': 0, 'json': 0}
    for folder in ['src', 'assets', 'docs', 'tools', 'runtime', 'web']:
        for path in (ROOT / folder).rglob('*'):
            rel = path.relative_to(ROOT)
            if any(part in {'.godot', '.state', '__pycache__', 'qa', 'logs', 'dist', 'site_bundle'} for part in rel.parts):
                continue
            if not path.is_file() or path.suffix not in {'.py', '.json'}:
                continue
            try:
                if path.suffix == '.py':
                    ast.parse(path.read_text(), filename=str(rel)); count['python'] += 1
                else:
                    json.loads(path.read_text()); count['json'] += 1
            except (SyntaxError, ValueError) as exc:
                errors.append(f'{rel}: {exc}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(json.dumps({'status': 'pass', 'asset_files': len(rows), 'release_hashes_checked': strict,
                      'syntax': count, 'blender_godot_gpu_invoked': False}, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strict', action='store_true', help='Verify packaged release asset SHA-256 values')
    validate(parser.parse_args().strict)
