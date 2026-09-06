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
# check-tutorial.py's ttfs(). The other three have been collapsed into
# load_font_manifest one at a time, each after a machine found the
# copy that had gone stale; this one was already missing
# /usr/local/share/fonts and ~/Library/Fonts, added to the manifest in
# #104, so on an Intel Mac or a per-user font install it would have
# refused while the build beside it worked.
#
# It also means the metrics are regenerated from the SAME file the
# build rasterizes, which is the property that actually matters here:
# advances measured from one DejaVu and glyphs drawn from another is
# wrong on every screen with nothing to say so.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$here/../packages/baker:${PYTHONPATH:-}"

eval "$(python3 - "$here/fonts.json" <<'PY'
import sys
from ps2ui_bake.cli import load_font_manifest
m = load_font_manifest(sys.argv[1])
print('regular=%s' % repr(m["regular"]["ttf"]).replace("'", '"'))
print('bold=%s' % repr(m["bold"]["ttf"]).replace("'", '"'))
PY
)"
echo "regen: regular=$regular"
echo "regen: bold=$bold"

python3 -m ps2ui_bake.fontgen "$regular" "DejaVu Sans" 400 "$here/default.metrics.json"
python3 -m ps2ui_bake.fontgen "$bold"    "DejaVu Sans" 700 "$here/default-bold.metrics.json"
