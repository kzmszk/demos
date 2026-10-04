#!/bin/bash
# whole island: SET=island ./run_island.sh [gen bake pack web]
set -e
cd "$(dirname "$0")"
PY=/home/kazu/work/venice-assets/.venv/bin/python
SET=${SET:-island}
B=/home/kazu/work/venice-assets/build/$SET
ST=/home/kazu/work/venice-assets/build/stage_$SET
OUT=../public/data/$SET
steps="${@:-gen bake pack web}"
for s in $steps; do
  case $s in
    gen) $PY build_tiles.py $B --bbox -2900 -1300 3200 2100 ${TILES:+--tiles "$TILES"} | grep -v "^  hero" | tail -4 ;;
    bake) $PY bake_batches.py $B --samples ${SAMPLES:-128} ;;
    pack) rm -rf $ST; mkdir -p $OUT; $PY pack.py $B $ST | tail -1; $PY pack_templates.py $B $ST; node pack.mjs $ST $OUT | tail -2; cp $B/materials.json ../public/data/materials.json ;;
    web) node build_web.mjs --dev 2>&1 | tail -1 ;;
  esac
done
