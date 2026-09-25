#!/bin/sh
# Build the console's built-in theme: ui.uib (which console/Makefile
# links into the ELF), its check, and the screenshot the README embeds.
#
# The build itself is ps2ui.json. What is here is what is this
# example's: the blob rules, and a screenshot that is refreshed by
# building rather than by hand.
set -eu

here=$(dirname "$0")
repo=$(cd "$here/../.." && pwd)
out="$here/build"

PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake.ps2ui build "$here/ps2ui.json"

(cd "$repo" && ./tools/check-blobs.sh examples/console/build/ui.uib)

PYTHONPATH="$repo/packages/baker" python3 - "$out" "$here/screenshots" <<'PY'
import sys
from ps2ui_bake.uib import read_uib
from ps2ui_bake import preview

out, shots = sys.argv[1], sys.argv[2]
uib = read_uib(f"{out}/ui.uib")
preview.render(uib, screen="games").save(f"{shots}/games.png")
print(f"ps2ui-bake: screenshots -> {shots}/", file=sys.stderr)
PY

echo "console theme: $out/ui.uib"
