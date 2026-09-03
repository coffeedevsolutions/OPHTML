#!/bin/sh
# Build the memcard example end to end, then run the host runtime tests
# over the fresh blob and refresh the committed screenshots.
#
# THE BUILD ITSELF IS ps2ui.json, not this file. Every example here
# carried the same script with different flags -- compile each screen,
# bake them together, write a preview -- and a project file describes
# that once. What is left below is what is genuinely this example's:
# the runtime tests, and the screenshots the README embeds.
#
# `python3 -m ps2ui_bake.ps2ui` rather than `ps2ui` because nothing is
# published yet; the tutorial's last section carries the same table.
set -eu

here=$(dirname "$0")
repo=$(cd "$here/../.." && pwd)

PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake.ps2ui build "$here/ps2ui.json"

out="$here/build"
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
