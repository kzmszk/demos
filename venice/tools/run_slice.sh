#!/bin/bash
# regenerate + bake + pack the test slice:  ./run_slice.sh [gen|bake|pack|web ...]  (default: all)
set -e
cd "$(dirname "$0")"
PY=/home/kazu/work/venice-assets/.venv/bin/python
B=/home/kazu/work/venice-assets/build/slice
ST=/home/kazu/work/venice-assets/build/stage
steps="${@:-gen bake pack web}"
for s in $steps; do
  case $s in
    gen) $PY build_tiles.py $B --bbox -600 -200 200 200 | tail -2 ;;
    bake) blender -b --python bake.py -- $B --samples ${SAMPLES:-128} --margin 1 2>&1 | grep -E "done|Error|error" ;;
    pack) rm -rf $ST; $PY pack.py $B $ST | tail -1; $PY pack_templates.py $B $ST; node pack.mjs $ST ../public/data/tiles | tail -2; cp $B/materials.json ../public/data/materials.json ;;
    web) node build_web.mjs --dev 2>&1 | tail -1 ;;
  esac
done
