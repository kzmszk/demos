#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${BLENDER_BIN:?Set BLENDER_BIN to the Blender 5.2.1 executable}"
mkdir -p "$root/build" "$root/logs"
python3 "$root/tools/validate_source.py"
export SAGRADA_STONE_PROFILE="${SAGRADA_STONE_PROFILE:-web_v11}"
export SAGRADA_STONE_FINISHES="${SAGRADA_STONE_FINISHES:-on}"
# Blender is invoked only by an explicit call to this script. No render occurs.
exec "$BLENDER_BIN" -b --threads "${BLENDER_THREADS:-8}" --python "$root/src/build_scene.py" -- "$@"
