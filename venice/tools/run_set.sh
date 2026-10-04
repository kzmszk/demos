#!/bin/bash
# build a named tile set:  SET=test TILES="15,6;12,9" ./run_set.sh [gen bake pack web]   (or BBOX="x0 y0 x1 y1")
# output: venice-assets/build/$SET -> public/data/$SET (viewer: ?set=$SET)
set -e
cd "$(dirname "$0")"
PY=/home/kazu/work/venice-assets/.venv/bin/python
SET=${SET:-test}
B=/home/kazu/work/venice-assets/build/$SET
ST=/home/kazu/work/venice-assets/build/stage_$SET
OUT=../public/data/$SET
steps="${@:-gen bake pack web}"
for s in $steps; do
  case $s in
    gen) if [ -n "$TILES" ]; then $PY build_tiles.py $B --tiles "$TILES" | tail -3; else $PY build_tiles.py $B --bbox $BBOX | tail -3; fi ;;
    bake) blender -b --python bake.py -- $B --samples ${SAMPLES:-128} --margin 1 ${BAKE_TILES:+--tiles $BAKE_TILES} 2>&1 | grep -E "done|Error|error" ;;
    pack) rm -rf $ST; mkdir -p $OUT; $PY pack.py $B $ST | tail -1; $PY pack_templates.py $B $ST; node pack.mjs $ST $OUT | tail -2; cp $B/materials.json ../public/data/materials.json ;;
    web) node build_web.mjs --dev 2>&1 | tail -1 ;;
  esac
done
