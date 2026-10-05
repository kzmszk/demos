#!/usr/bin/env python3
"""Verify the locally produced split bundle; this does not perform a browser test."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "web/qa/static_integrity.json")
    args = parser.parse_args()
    bundle = ROOT / "web/site_bundle"
    manifest = json.loads((bundle / "package_manifest.json").read_text())
    failures = []
    files = manifest["files"]
    for entry in files:
        path = bundle / entry["file"]
        if not path.is_file():
            failures.append(f"Missing file: {entry['file']}")
        elif path.stat().st_size != entry["bytes"] or digest(path) != entry["sha256"]:
            failures.append(f"Size/hash mismatch: {entry['file']}")
        if entry["bytes"] > 20 * 1024 * 1024:
            failures.append(f"Over 20MiB: {entry['file']}")
    staged = json.loads((ROOT / "web/qa/staged_sources.json").read_text())
    for name, entry in staged.items():
        for path in [ROOT / "build" / name, ROOT / "web/godot/assets" / name]:
            if digest(path) != entry["sha256"]:
                failures.append(f"Source not current: {path.relative_to(ROOT)}")
    project = (ROOT / "web/godot/project.godot").read_text()
    if 'renderer/rendering_method="gl_compatibility"' not in project:
        failures.append("Web renderer is not GL Compatibility")
    for path in (ROOT / "runtime/scripts").iterdir():
        if path.suffix not in (".gd", ".gdshader"):
            continue
        if path.read_bytes() != (ROOT / "web/godot/scripts" / path.name).read_bytes():
            failures.append(f"Web script not current: {path.name}")
    credits = bundle / "assets" / manifest["package_id"] / "credits.html"
    if 'href="../../index.html"' not in credits.read_text():
        failures.append("Packaged credits return link is not relative to package root")
    report = {
        "passed": not failures,
        "source_glb": staged["sagrada_familia.glb"],
        "files": len(files),
        "failures": failures,
        "total_bytes": sum(x["bytes"] for x in files),
        "max_file_bytes": max(x["bytes"] for x in files),
        "pck_parts": sum(".pck." in x["file"] and ".part" in x["file"] for x in files),
        "package_id": manifest["package_id"],
        "renderer": "gl_compatibility",
        "browser_tested": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
