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
    -o "$out/library.json"

node "$repo/packages/layout/bin/ps2ui-layout.js" \
    "$here/ui/saves.html" "$here/ui/library.css" \
    -o "$out/saves.json"

PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake \
    "$out/library.json" "$out/saves.json" \
    -o "$out/ui.uib" \
    --preview "$out/preview.png" \
    --montage "$out/states.png"

make -C "$repo/runtime" UIB="$(cd "$out" && pwd)/ui.uib" test

# The README embeds these, so they are committed -- which only stays
# honest if building refreshes them. Copying by hand is how a preview
# ends up showing a renderer that no longer exists.
PYTHONPATH="$repo/packages/baker" python3 - "$out" "$here/screenshots" <<'PY'
import sys
from ps2ui_bake.uib import read_uib
from ps2ui_bake import preview

out, shots = sys.argv[1], sys.argv[2]
uib = read_uib(f"{out}/ui.uib")
preview.render(uib, screen="library").save(f"{shots}/preview.png")
preview.render(uib, screen="saves").save(f"{shots}/saves.png")
preview.montage(uib).save(f"{shots}/states.png")
print(f"ps2ui-bake: screenshots -> {shots}/", file=sys.stderr)
PY

echo "memcard example: $out/ui.uib"
