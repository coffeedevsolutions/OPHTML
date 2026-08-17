#!/bin/sh
# Build the memcard example end to end: HTML+CSS -> ui.json -> ui.uib
# (+ preview PNGs), then run the host runtime tests over the fresh blob.
set -eu

here=$(dirname "$0")
repo=$(cd "$here/../.." && pwd)
out="$here/build"
mkdir -p "$out"

node "$repo/packages/layout/bin/ps2ui-layout.js" \
    "$here/ui/library.html" "$here/ui/library.css" \
    -o "$out/ui.json"

PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake "$out/ui.json" \
    -o "$out/ui.uib" \
    --preview "$out/preview.png" \
    --montage "$out/states.png"

make -C "$repo/runtime" UIB="$(cd "$out" && pwd)/ui.uib" test

echo "memcard example: $out/ui.uib"
