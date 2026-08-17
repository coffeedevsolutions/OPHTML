#!/bin/sh
# Build the channel-6 game browser end to end: HTML+CSS -> ui.json ->
# ui.uib (+ per-screen preview PNGs), then verify the blob's contract.
#
# The blob carries two screens: `games` (screen 0, the browser you look
# at) and `probe` (screen 1, the conformance grid). Both compile against
# one stylesheet.
set -eu

here=$(dirname "$0")
repo=$(cd "$here/../.." && pwd)
out="$here/build"
mkdir -p "$out"

# The browser navigates without wrap on purpose: walking off the cover
# grid must dead-end, so a stuck D-pad is visible immediately. The probe
# screen wraps, which exercises the other half of --focus-wrap.
node "$repo/packages/layout/bin/ps2ui-layout.js" \
    "$here/ui/games.html" "$here/ui/channel6.css" \
    -o "$out/games.json"

node "$repo/packages/layout/bin/ps2ui-layout.js" \
    "$here/ui/probe.html" "$here/ui/channel6.css" --focus-wrap \
    -o "$out/probe.json"

PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake \
    "$out/games.json" "$out/probe.json" \
    -o "$out/ui.uib" \
    --preview "$out/preview.png" \
    --preview-display "$out/preview-display.png" \
    --montage "$out/states.png"

# The same UI authored for a panel that stretches to 16:9. Same 640x448
# framebuffer, same command list; only the aspect in the header and the
# linter's distortion warnings differ. Bringing both blobs to one panel
# is how you prove the aspect reached the hardware (docs/bringup.md
# step 10): each should read correct in its own TV mode and wrong in the
# other.
node "$repo/packages/layout/bin/ps2ui-layout.js" \
    "$here/ui/games.html" "$here/ui/channel6.css" --mode ntsc16x9 \
    -o "$out/games-16x9.json"

node "$repo/packages/layout/bin/ps2ui-layout.js" \
    "$here/ui/probe.html" "$here/ui/channel6.css" --mode ntsc16x9 --focus-wrap \
    -o "$out/probe-16x9.json"

PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake \
    "$out/games-16x9.json" "$out/probe-16x9.json" \
    -o "$out/ui-16x9.uib" \
    --preview-display "$out/preview-16x9-display.png"

# ps2ui-bake previews screen 0; the probe screen needs the API directly.
PYTHONPATH="$repo/packages/baker" python3 - "$out" <<'PY'
import sys
from ps2ui_bake.uib import read_uib
from ps2ui_bake import preview

out = sys.argv[1]
uib = read_uib(f"{out}/ui.uib")
preview.render(uib, screen="probe").save(f"{out}/probe.png")
preview.montage(uib, screen="probe").save(f"{out}/probe-states.png")
print(f"ps2ui-bake: preview -> {out}/probe.png", file=sys.stderr)
print(f"ps2ui-bake: montage -> {out}/probe-states.png", file=sys.stderr)
PY

# The overlay in situ: the same blob composited over a game frame,
# which is what it looks like when the host app skips its clear.
PYTHONPATH="$repo/packages/baker" python3 "$here/preview_in_game.py" \
    "$out/ui.uib" "$out/in-game.png"

PYTHONPATH="$repo/packages/baker" python3 "$here/check.py" "$out/ui.uib"

echo "channel6 browser: $out/ui.uib"
