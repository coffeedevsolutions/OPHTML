#!/bin/sh
# Build the OPL-class environment end to end: five screens plus one
# overlay -> ui.uib (+ preview PNGs), then run the host runtime tests
# over the fresh blob and write the measurements down.
#
# This is examples/, not fixtures/: it carries the shipped contract
# that fixtures/opl-scope deliberately does not -- warning-free under
# --strict, screenshots refreshed by building rather than by hand.
set -eu

here=$(dirname "$0")
repo=$(cd "$here/../.." && pwd)
out="$here/build"
mkdir -p "$out"

# --strict, because an example that ships with warnings teaches the
# warnings are noise. The scope fixture may warn; this may not.
for screen in landing library detail filters recent confirm; do
    node "$repo/packages/layout/bin/ps2ui-layout.js" \
        "$here/ui/$screen.html" "$here/ui/opl.css" \
        -o "$out/$screen.json" --strict
done

PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake \
    "$out/landing.json" "$out/library.json" "$out/detail.json" \
    "$out/filters.json" "$out/recent.json" "$out/confirm.json" \
    -o "$out/ui.uib" \
    --preview "$out/preview.png" \
    --montage "$out/states.png"

# NOT `make -C runtime test UIB=...`: that suite asserts the memcard
# example's contents by name and refuses any other blob. check-blobs is
# the blob-generic validator, and it is what this example needs -- it
# reads the header, walks every table, and checks the runtime's
# assumptions hold without knowing what the screens are called.
(cd "$repo" && ./tools/check-blobs.sh examples/opl-env/build/ui.uib)

# The README embeds these, so they are committed -- which only stays
# honest if building refreshes them.
PYTHONPATH="$repo/packages/baker" python3 - "$out" "$here/screenshots" <<'PY'
import sys
from ps2ui_bake.uib import read_uib
from ps2ui_bake import preview

out, shots = sys.argv[1], sys.argv[2]
uib = read_uib(f"{out}/ui.uib")
for name in ("landing", "library", "detail", "filters", "recent", "confirm"):
    preview.render(uib, screen=name).save(f"{shots}/{name}.png")
print(f"ps2ui-bake: screenshots -> {shots}/", file=sys.stderr)
PY

echo "opl-env example: $out/ui.uib"
