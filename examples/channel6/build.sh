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

# WHY probe.html SETS focusWrap IN ps2ui.json AND games.html DOES NOT.
# The browser navigates without wrap on purpose: walking off the cover
# grid must dead-end, so a stuck D-pad is visible immediately. The probe
# screen wraps, which exercises the other half. That is the one setting
# this project varies per screen, and it is why a screen may be an
# object rather than a bare path.
# THE BUILD ITSELF IS ps2ui.json. The 16:9 blob is a SECOND BUILD of
# the same project, which is why the project file has no `variants`
# block: everything a second blob needs differently is a flag.
PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake.ps2ui build "$here/ps2ui.json"

PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake.ps2ui build "$here/ps2ui.json" \
    --mode ntsc16x9 -o build/ui-16x9.uib

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

# Refresh the committed screenshots the README embeds. Same reason as
# the memcard example: a hand-copied preview drifts from its renderer.
cp "$out/preview.png"  "$here/screenshots/games.png"
cp "$out/probe.png"    "$here/screenshots/probe.png"
cp "$out/states.png"   "$here/screenshots/states.png"
cp "$out/in-game.png"  "$here/screenshots/in-game.png"
echo "ps2ui-bake: screenshots -> $here/screenshots/" >&2

PYTHONPATH="$repo/packages/baker" python3 "$here/check.py" "$out/ui.uib"

echo "channel6 browser: $out/ui.uib"
