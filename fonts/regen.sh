#!/usr/bin/env bash
# Regenerate the checked-in metrics JSON from the system DejaVu faces.
#
# The metrics file is the layout/baker seam, so it is committed rather
# than built: a contributor with no TTF still gets byte-identical
# advances. That only holds if regenerating is one command, which is
# what this is. Run it whenever fontgen changes and commit the diff.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$here/../packages/baker:${PYTHONPATH:-}"

pick() {
  for p in "$@"; do [ -f "$p" ] && { echo "$p"; return; }; done
  echo "none of these exist: $*" >&2
  exit 1
}

regular=$(pick /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
               /usr/share/fonts/TTF/DejaVuSans.ttf \
               /opt/homebrew/share/fonts/DejaVuSans.ttf \
               /Library/Fonts/DejaVuSans.ttf)
bold=$(pick /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf \
            /usr/share/fonts/TTF/DejaVuSans-Bold.ttf \
            /opt/homebrew/share/fonts/DejaVuSans-Bold.ttf \
            /Library/Fonts/DejaVuSans-Bold.ttf)

python3 -m ps2ui_bake.fontgen "$regular" "DejaVu Sans" 400 "$here/default.metrics.json"
python3 -m ps2ui_bake.fontgen "$bold"    "DejaVu Sans" 700 "$here/default-bold.metrics.json"
