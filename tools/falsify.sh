#!/bin/sh
# Run a sabotage against a file, check that a fence catches it, restore.
#
# WHY THIS EXISTS. Deliberate breakage is this project's only reliable
# detector for a check that passes for the wrong reason (docs/method.md),
# so it gets run constantly -- and the obvious way to undo a sabotage is
# `git checkout -- <file>`, which does not restore the file. It restores
# HEAD. Any uncommitted work in that file is gone, silently, with a zero
# exit status.
#
# That has now destroyed work four times in this repository: ps2ui.c,
# the opl-env driver, docs/bench-runbook.md, and the ticks_to_us change
# whose own review is what prompted writing this down. Three of those
# were noticed immediately. One was committed and pushed broken first.
#
# The fix is not to remember. It is to never name git in a restore
# path. This snapshots the real bytes and puts the real bytes back, so
# the blast radius of a mistake is the sabotage and nothing else.
#
#   tools/falsify.sh <file> <fence-command> <<'PY'
#   <python that edits the file in place>
#   PY
#
# Exit 0 means the fence CAUGHT the sabotage, which is a pass.
set -eu
[ $# -ge 2 ] || { echo "usage: falsify.sh <file> <fence-cmd>" >&2; exit 2; }
file=$1; shift
snap=$(mktemp)
cp "$file" "$snap"
# Restore on any exit, including a signal or a failure inside the edit.
trap 'cp "$snap" "$file"; rm -f "$snap"' EXIT INT TERM
python3 - "$file" || { echo "SABOTAGE FAILED TO APPLY" >&2; exit 2; }
if "$@" >/dev/null 2>&1; then
    echo "PASSED -- HOLE: the fence did not catch it"
    exit 1
fi
"$@" 2>&1 | grep -m1 "not ok" || echo "caught (no 'not ok' line)"
