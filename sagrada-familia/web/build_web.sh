#!/usr/bin/env bash
set -euo pipefail
web_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
godot_bin="$(command -v -- "${GODOT_BIN:-godot}" || true)"
[[ -n "$godot_bin" && -x "$godot_bin" ]] || { echo "Set GODOT_BIN to your Godot 4.7.2 executable, or put it on PATH as godot." >&2; exit 1; }
: "${GODOT_WEB_TEMPLATE_DIR:?Set GODOT_WEB_TEMPLATE_DIR to the matching Godot 4.7.2 Web templates directory.}"
mkdir -p "$web_root/dist" "$web_root/logs" "$web_root/qa" "$web_root/.state"
export XDG_DATA_HOME="$web_root/.state/data"
export XDG_CONFIG_HOME="$web_root/.state/config"
export XDG_CACHE_HOME="$web_root/.state/cache"
python3 "$web_root/tools/configure_web_export.py" --template-dir "$GODOT_WEB_TEMPLATE_DIR"
python3 "$web_root/tools/stage_assets.py"
font_pythonpath="${FONTTOOLS_PYTHONPATH:-}"
PYTHONPATH="$font_pythonpath${PYTHONPATH:+:$PYTHONPATH}" python3 "$web_root/tools/build_ui_font.py" > "$web_root/logs/font_build.log"
mkdir -p "$web_root/../runtime/assets"
cp "$web_root/godot/assets/sagrada_familia_ui.woff2" "$web_root/../runtime/assets/"
for step in import export; do
 if [[ "$step" == "import" ]]; then args=(--editor --import); else args=(--export-release Web "$web_root/dist/index.html"); fi
 timeout 900 "$godot_bin" --headless --audio-driver Dummy --path "$web_root/godot" "${args[@]}" > "$web_root/logs/build_$step.log" 2>&1 || { tail -n 40 "$web_root/logs/build_$step.log" >&2; exit 1; }
 if grep -Eq '(^|[[:space:]])(SCRIPT )?ERROR:' "$web_root/logs/build_$step.log"; then tail -n 40 "$web_root/logs/build_$step.log" >&2; exit 1; fi
done
cp "$web_root/godot/assets/sagrada_familia_ui.woff2" "$web_root/dist/"
python3 "$web_root/tools/build_credits.py"
python3 - "$web_root/dist" <<'PY'
from pathlib import Path
import gzip,sys
for p in Path(sys.argv[1]).iterdir():
 if p.suffix in ['.pck','.wasm','.js']:
  with p.open('rb') as src, gzip.GzipFile(filename='',mode='wb',fileobj=Path(str(p)+'.gz').open('wb'),mtime=0,compresslevel=6) as dst:
   import shutil
   shutil.copyfileobj(src,dst)
PY
if [[ "${SKIP_STATIC_PACKAGE:-0}" != "1" ]]; then
 python3 "$web_root/tools/package_static.py" > "$web_root/qa/package_summary.json"
 echo "Web build complete. Open the split bundle with: python3 $web_root/open_local.py"
else
 echo "Static packaging skipped; existing site_bundle and package summary preserved."
 echo "Web build complete. Open the new dist with: python3 $web_root/open_local.py --bundle dist --port 8778"
fi
echo "For a foreground dist server: $web_root/START_WEB.sh --no-browser"
