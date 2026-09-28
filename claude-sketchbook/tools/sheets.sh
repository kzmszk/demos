#!/bin/bash
# usage: tools/sheets.sh prefix per-sheet "chars"
cd "$(dirname "$0")/.."
PREFIX=$1; N=$2; CH=$3
node -e '
const [chars,n]=[process.argv[1],+process.argv[2]]; const a=[...chars];
for(let i=0;i<a.length;i+=n) console.log(a.slice(i,i+n).join(""));' "$CH" "$N" | nl -v0 | while read idx chunk; do
  node tools/sheet.mjs "${PREFIX}${idx}.png" "$chunk" 5 2>&1 | grep -v -E "b.js|Done|^$"
done
