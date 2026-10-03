#!/bin/bash
# pack every baked zone into public/data and copy the room table
set -e
cd "$(dirname "$0")"
B=/home/kazu/work/vatican-assets/bake
pack() { [ -f $B/ext_$1.json ] && node --max-old-space-size=24000 pack.mjs $B/ext_$1 ../public/data $2 $3; }
for z in "$@"; do case $z in
  core) pack core core 96;; city) pack city city 256;; sistine) pack sistine sistine 64;; basilica) pack basilica basilica 64;;
  rooms) for r in costantino eliodoro segnatura incendio maps ottagono muse rotonda pinacoteca momo; do pack room_$r room_$r 64; done;;
esac; done
cp ref/rooms.json ../public/data/rooms.json
