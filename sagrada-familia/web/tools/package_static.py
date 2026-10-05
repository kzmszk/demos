#!/usr/bin/env python3
"""Build a versioned static package with no asset larger than 20 MiB."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

FORMAT = 1
APPLICATION = "sagrada-familia-static-package"
MAX_ASSET = 20 * 1024 * 1024
WEB_ROOT = Path(__file__).resolve().parents[1]


def file_record(path: Path, name: str | None = None) -> dict:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'file': name or path.name, 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def owned_output(path: Path) -> bool:
    if not path.exists() or (path.is_dir() and not any(path.iterdir())):
        return True
    try:
        marker = json.loads((path / 'package_manifest.json').read_text())
        return marker.get('application') == APPLICATION and marker.get('format_version') == FORMAT
    except (OSError, ValueError):
        return False


def make_package(source: Path, output: Path, chunk_bytes: int = MAX_ASSET) -> dict:
    source, output = source.resolve(), output.resolve()
    if not source.is_relative_to(WEB_ROOT) or not output.is_relative_to(WEB_ROOT):
        raise ValueError('Source and output must remain inside this Web project')
    if (source == output or output == WEB_ROOT or source.is_relative_to(output)
            or output.is_relative_to(source)):
        raise ValueError('Source and output must be separate directories')
    if not 16 <= chunk_bytes <= MAX_ASSET:
        raise ValueError('Chunk size must be between 16 bytes and 20 MiB')
    if not owned_output(output):
        raise ValueError('Refusing to replace a directory that is not our marked static package')
    required = ['index.html', 'index.js', 'index.pck', 'index.wasm']
    for filename in required:
        if not (source / filename).is_file():
            raise ValueError(f'Missing export file: {filename}')
    with (source / 'index.pck').open('rb') as stream:
        if stream.read(4) != b'GDPC':
            raise ValueError('Source PCK header is invalid')
    with (source / 'index.wasm').open('rb') as stream:
        if stream.read(8) != b'\0asm\1\0\0\0':
            raise ValueError('Source WASM header is invalid')
    html_bytes = (source / 'index.html').read_bytes()
    html = html_bytes.decode('utf-8')
    if re.search(r'<base\b', html, re.IGNORECASE):
        raise ValueError('Source HTML already contains a base element; adapt it explicitly')
    engine_tag = re.compile(r'<script\b[^>]*\bsrc\s*=\s*([\'\"])(?:\./)?index\.js\1[^>]*>', re.IGNORECASE)
    if len(engine_tag.findall(html)) != 1:
        raise ValueError('Expected exactly one index.js script tag')

    ignored = {'index.pck.gz', 'index.wasm.gz'}
    sources = {}
    for path in sorted(source.rglob('*')):
        relative = path.relative_to(source).as_posix()
        if not path.is_file() or relative in ignored or any(part.startswith('.') for part in path.relative_to(source).parts):
            continue
        if not path.resolve().is_relative_to(source):
            raise ValueError('Export symlink escapes dist: ' + relative)
        record = file_record(path, relative)
        if relative not in {'index.pck', 'index.wasm'} and record['bytes'] > MAX_ASSET:
            raise ValueError('Auxiliary export asset exceeds 20 MiB: ' + relative)
        sources[relative] = record
    loader_source = Path(__file__).with_name('static_loader.js')
    loader_record = file_record(loader_source)
    if hashlib.sha256(html_bytes).hexdigest() != sources['index.html']['sha256']:
        raise ValueError('HTML changed while packaging')
    seed = {'format': FORMAT, 'chunk_bytes': chunk_bytes, 'inputs': sources, 'loader': loader_record, 'packager_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    build_id = hashlib.sha256(json.dumps(seed, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:20]
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.site-package-', dir=output.parent))
    backup = None
    try:
        relative_assets = Path('assets') / build_id
        assets = stage / relative_assets
        assets.mkdir(parents=True)
        for name, record in sources.items():
            if name in {'index.html', 'index.pck', 'index.wasm'}:
                continue
            target = assets / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
            if file_record(target, name) != record:
                raise ValueError('Export changed while packaging: ' + name)
            if name == 'credits.html':
                target.write_text(target.read_text().replace('<a href=\"index.html\">', '<a href=\"../../index.html\">', 1))
        shutil.copyfile(loader_source, assets / 'static_loader.js')
        if file_record(assets / 'static_loader.js') != loader_record:
            raise ValueError('Loader changed while packaging')

        pck_digest = hashlib.sha256()
        chunks = []
        pack = sources['index.pck']
        with (source / 'index.pck').open('rb') as stream:
            for index in range((pack['bytes'] + chunk_bytes - 1) // chunk_bytes):
                data = stream.read(chunk_bytes)
                if not data:
                    raise ValueError('PCK was truncated during packaging')
                pck_digest.update(data)
                filename = f"index.pck.{pack['sha256'][:16]}.part{index:02d}"
                (assets / filename).write_bytes(data)
                chunks.append({'file': filename, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
            if stream.read(1):
                raise ValueError('PCK grew during packaging')
        if pck_digest.hexdigest() != pack['sha256'] or sum(c['bytes'] for c in chunks) != pack['bytes']:
            raise ValueError('PCK changed during packaging')

        wasm_digest = hashlib.sha256()
        gzip_path = assets / '.wasm-compressing'
        with (source / 'index.wasm').open('rb') as stream, gzip_path.open('wb') as output_stream:
            with gzip.GzipFile(filename='', mode='wb', fileobj=output_stream, compresslevel=6, mtime=0) as compressor:
                for data in iter(lambda: stream.read(1024 * 1024), b''):
                    wasm_digest.update(data)
                    compressor.write(data)
        if wasm_digest.hexdigest() != sources['index.wasm']['sha256']:
            raise ValueError('WASM changed during packaging')
        compressed = file_record(gzip_path)
        if compressed['bytes'] > MAX_ASSET:
            raise ValueError('Compressed WASM exceeds 20 MiB; a different packaging strategy is required')
        compressed['file'] = f"index.wasm.{compressed['sha256'][:16]}.gz"
        gzip_path.rename(assets / compressed['file'])
        manifest = {
            'formatVersion': FORMAT, 'packageId': build_id,
            'pck': {'logicalFile': 'index.pck', 'bytes': pack['bytes'], 'sha256': pack['sha256'], 'chunks': chunks},
            'wasm': {'logicalFile': 'index.wasm', 'bytes': sources['index.wasm']['bytes'],
                     'sha256': sources['index.wasm']['sha256'], 'gzip': compressed},
        }
        (assets / 'static_assets.json').write_text(json.dumps(manifest, indent=2) + '\n')
        # The exported engine stays byte-for-byte unchanged. Standard Fetch/Streams
        # adapt only its two logical asset URLs before index.js is evaluated.
        injected = ('<script>window.__SF_STATIC_MANIFEST__=' + json.dumps(manifest, separators=(',', ':')).replace('<', '\\u003c')
                    + ';</script>\n<script src="static_loader.js"></script>\n')
        html = engine_tag.sub(lambda match: injected + match.group(0), html, count=1)
        html, count = re.subn(r'(<head\b[^>]*>)', lambda match: match.group(1) + f'\n<base href="./{relative_assets.as_posix()}/">\n', html, count=1, flags=re.IGNORECASE)
        if count != 1:
            raise ValueError('Source HTML has no head element')
        (stage / 'index.html').write_text(html)
        readme = f'''# Sagrada Família static hosting package

Package: {build_id}

This folder contains the final Web export with individual assets at most 20 MiB (20,971,520 bytes). It is a static bundle; no server-side code, custom CORS headers, COOP/COEP headers, or localhost dependency is required. Serve it over HTTPS. The unchanged Godot engine uses single-threaded WebGL 2 Compatibility.

`index.html` resolves its assets under `assets/{build_id}/`. Versioned directories and hashed PCK-part/WASM filenames prevent mixing asset versions. The hosting service controls caching of the root HTML. Publishing/updating the entire generated folder together is required; this tool does not publish it.

The model PCK remains the same bytes. It is split into {len(chunks)} ordered parts; the loader verifies each part's size and SHA256 and exposes a sequential ReadableStream at the original logical `index.pck` URL. The engine ultimately still assembles/loads the complete PCK in memory. Splitting satisfies per-file limits; it does not reduce total model download or runtime memory.

Only the gzip engine asset is stored. The adapter loads and verifies that compressed file, uses the standard DecompressionStream gzip API, and supplies an application/wasm Response at `index.wasm`. A host that already decodes Content-Encoding:gzip is detected to prevent double decoding. The browser needs Web Crypto, Fetch/Streams, WebAssembly, WebGL 2, and DecompressionStream gzip support.

`index.js` is unchanged. `static_loader.js` wraps window.fetch only for GETs to exactly those two same-directory logical URLs; all other requests are passed through. Its compatibility was checked against the included Godot 4.7.2 loader's public fetch/Response behavior, without modifying the engine internals. Actual browser startup/rendering still requires integration testing.

No .pck or uncompressed .wasm is included, and no external decoder/CDN is used. QA POST endpoints, if requested with ?qa=1, need the separate local QA server; normal static use does not need them. Keep QA query parameters off for hosted use.

Source PCK: {pack['bytes']:,} bytes; SHA256 {pack['sha256']}
Source WASM: {sources['index.wasm']['bytes']:,} bytes; SHA256 {sources['index.wasm']['sha256']}
Compressed WASM: {compressed['bytes']:,} bytes; SHA256 {compressed['sha256']}

`package_manifest.json` records input and output hashes and sizes. `assets/{build_id}/static_assets.json` is the runtime asset manifest also embedded in the HTML. The current script replaces only its own marked output directory, using a staged build, and removes stale files from previous packages.
'''
        (stage / 'README.md').write_text(readme)
        outputs = [file_record(path, path.relative_to(stage).as_posix()) for path in sorted(stage.rglob('*')) if path.is_file()]
        if any(item['bytes'] > MAX_ASSET for item in outputs):
            raise ValueError('Generated bundle contains a file above 20 MiB')
        report = {'application': APPLICATION, 'format_version': FORMAT, 'package_id': build_id,
                  'created_utc': datetime.now(timezone.utc).isoformat(), 'source': source.relative_to(WEB_ROOT).as_posix(),
                  'source_inputs': sources, 'loader_source': loader_record, 'asset_limit_bytes': MAX_ASSET,
                  'chunk_bytes': chunk_bytes, 'runtime_manifest': manifest, 'files': outputs,
                  'file_count_excluding_manifest': len(outputs), 'max_file_bytes': max(item['bytes'] for item in outputs),
                  'total_bytes_excluding_manifest': sum(item['bytes'] for item in outputs),
                  'browser_tested': False}
        (stage / 'package_manifest.json').write_text(json.dumps(report, indent=2) + '\n')
        if (stage / 'package_manifest.json').stat().st_size > MAX_ASSET:
            raise ValueError('Package manifest exceeds the hosting file limit')
        if output.exists():
            backup = output.with_name(output.name + '.previous-' + uuid.uuid4().hex)
            output.rename(backup)
        try:
            stage.rename(output)
        except BaseException:
            if backup is not None and not output.exists():
                backup.rename(output)
                backup = None
            raise
        if backup is not None:
            shutil.rmtree(backup)
        return report
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=WEB_ROOT / 'dist')
    parser.add_argument('--output', type=Path, default=WEB_ROOT / 'site_bundle')
    parser.add_argument('--chunk-bytes', type=int, default=MAX_ASSET)
    args = parser.parse_args()
    report = make_package(args.source, args.output, args.chunk_bytes)
    print(json.dumps({'package_id': report['package_id'], 'output': str(args.output.resolve()),
                      'pck_parts': len(report['runtime_manifest']['pck']['chunks']),
                      'max_file_bytes': report['max_file_bytes'],
                      'total_bytes_excluding_manifest': report['total_bytes_excluding_manifest'],
                      'browser_tested': False}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
