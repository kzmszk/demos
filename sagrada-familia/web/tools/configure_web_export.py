#!/usr/bin/env python3
"""Resolve locally installed single-thread Web templates without running Godot."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template-dir', type=Path, required=True)
    args = parser.parse_args()
    template_dir = args.template_dir.expanduser().resolve()
    config = (ROOT / 'web/godot/export_presets.cfg.in').read_text()
    for kind in ['debug', 'release']:
        template = template_dir / f'web_nothreads_{kind}.zip'
        if not template.is_file():
            parser.error(f'Missing Godot 4.7.2 single-thread template: {template}')
        token = f'"@GODOT_WEB_TEMPLATE_{kind.upper()}@"'
        if config.count(token) != 1:
            raise SystemExit(f'Export preset must contain exactly one {token}')
        config = config.replace(token, json.dumps(str(template), ensure_ascii=False))
    output = ROOT / 'web/godot/export_presets.cfg'
    output.write_text(config)
    print(f'Configured local export templates: {template_dir}')


if __name__ == '__main__':
    main()
