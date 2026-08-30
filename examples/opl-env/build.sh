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

# And what THIS blob promises, which check-blobs cannot know: that the
# tint table is role-keyed, that slot text and commands share the
# entries whose names they share, and that naming the colours did not
# stop the palette being a small repeated set. Run here rather than in
# the baker's unit suite because the subject is a build artefact -- see
# the header of check.py for why that distinction is load-bearing.
PYTHONPATH="$repo/packages/baker" python3 "$here/check.py" "$out/ui.uib"

# The README embeds these, so they are committed -- which only stays
# honest if building refreshes them.
PYTHONPATH="$repo/packages/baker" python3 - "$out" "$here/screenshots" <<'PY'
import sys
from ps2ui_bake.uib import read_uib
from ps2ui_bake import preview

out, shots = sys.argv[1], sys.argv[2]
uib = read_uib(f"{out}/ui.uib")
# ONE SET PER THEME. Row 0 keeps the plain names the README embeds;
# every other row gets a suffix. A theme nobody can look at without a
# PS2 is a theme nobody will get right, and this also puts every row
# under the existing screenshot drift check for free -- a second row
# that stopped moving would show up as a diff in these files rather
# than as a photograph nobody took.
for theme in range(len(uib.themes)):
    suffix = "" if theme == 0 else f"-{theme}"
    for name in ("landing", "library", "detail", "filters", "recent", "confirm"):
        preview.render(uib, screen=name, theme=theme).save(
            f"{shots}/{name}{suffix}.png")
print(f"ps2ui-bake: screenshots ({len(uib.themes)} theme(s)) -> {shots}/",
      file=sys.stderr)
PY

echo "opl-env example: $out/ui.uib"
