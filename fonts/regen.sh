#!/usr/bin/env bash
# Regenerate the checked-in metrics JSON from the faces fonts.json names.
#
# The metrics file is the layout/baker seam, so it is committed rather
# than built: a contributor with no TTF still gets byte-identical
# advances. That only holds if regenerating is one command, which is
# what this is. Run it whenever fontgen changes and commit the diff.
#
# IT READS fonts.json RATHER THAN CARRYING ITS OWN LIST. This script
# used to hardcode four DejaVu paths, which made it the FOURTH copy of
# that list -- after the manifest, test_baker.py's own, and
# check-tutorial.py's ttfs(). The other three were collapsed into
# load_font_manifest one at a time, each after a machine found the copy
# that had gone stale; this one was already missing
# /usr/local/share/fonts and ~/Library/Fonts, added to the manifest in
# #104, so on an Intel Mac or a per-user font install it would have
# refused while the build beside it worked.
#
# It also means the metrics are regenerated from the SAME file the
# build rasterizes, which is the property that actually matters:
# advances measured from one DejaVu and glyphs drawn from another is
# wrong on every screen with nothing to say so.
#
# NO SHELL ROUND TRIP FOR THE PATHS. The first version of this had
# Python print `regular=...` and bash `eval` it, quoting by
# repr().replace("'", '"'). repr() switches to double quotes when the
# string itself contains a single quote, so that replace corrupted the
# apostrophe instead of the delimiters and a home directory like
# /Users/O'Brien emitted unbalanced quotes and died in eval. Narrow --
# and ~/Library/Fonts is exactly the candidate that reaches a home
# directory, and it is the one #104 added. Reintroducing a
# macOS-shaped fragility while fixing a macOS-shaped staleness is a
# poor trade, so the paths never leave Python now.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$here/../packages/baker:${PYTHONPATH:-}"

python3 - "$here" <<'PY'
import sys, os
from ps2ui_bake.cli import load_font_manifest
from ps2ui_bake import fontgen

here = sys.argv[1]
faces = load_font_manifest(os.path.join(here, "fonts.json"))
for face, weight, out in (("regular", 400, "default.metrics.json"),
                          ("bold", 700, "default-bold.metrics.json")):
    ttf = faces[face]["ttf"]
    print("regen: %s = %s" % (face, ttf))
    rc = fontgen.main([ttf, "DejaVu Sans", str(weight),
                       os.path.join(here, out)])
    if rc != 0:
        raise SystemExit(rc)
PY
