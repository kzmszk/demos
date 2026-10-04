#!/usr/bin/env bash
set -euo pipefail
runtime_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
godot_bin="$(command -v -- "${GODOT_BIN:-godot}" || true)"
[[ -n "$godot_bin" && -x "$godot_bin" ]] || { echo "Set GODOT_BIN to your Godot 4.7.2 executable, or put it on PATH as godot." >&2; exit 1; }
mkdir -p "$runtime_dir/.userdata" "$runtime_dir/qa"
export XDG_DATA_HOME="$runtime_dir/.userdata"
export XDG_CONFIG_HOME="$runtime_dir/.userdata/config"
export XDG_CACHE_HOME="$runtime_dir/.userdata/cache"
if [[ "${1:-}" != "--check" && ! -d "$runtime_dir/.godot/imported" ]]; then
  "$godot_bin" --headless --audio-driver Dummy --editor --import --path "$runtime_dir" > "$runtime_dir/qa/import.log" 2>&1 || { tail -n 30 "$runtime_dir/qa/import.log" >&2; exit 1; }
fi
case "${1:-}" in
 --check) exec "$godot_bin" --headless --path "$runtime_dir" --check-only --script res://scripts/main.gd ;;
 --qa) exec "$godot_bin" --headless --audio-driver Dummy --path "$runtime_dir" -- --qa ;;
 --forward-plus) shift; exec "$godot_bin" --rendering-method forward_plus --path "$runtime_dir" -- "$@" ;;
 --compatibility) shift; exec "$godot_bin" --rendering-method gl_compatibility --path "$runtime_dir" -- "$@" ;;
 *) exec "$godot_bin" --path "$runtime_dir" -- "$@" ;;
esac
