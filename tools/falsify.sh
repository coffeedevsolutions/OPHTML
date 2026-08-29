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
# The fence must PASS on the real bytes first. Without this, a fence
# command that cannot run at all -- a typo, a missing build step, or
# the whole command quoted as one argv entry, which is how this was
# found -- fails identically before and after the sabotage, and the
# verdict below reads that failure as "caught". A false pass on a
# falsification is worse than no falsification: it is a check this
# project believes it has.
if ! "$@" >/dev/null 2>&1; then
    echo "FENCE ALREADY FAILS ON THE UNMODIFIED FILE -- verdict would be" \
         "meaningless. Check the command: it must be separate arguments," \
         "not one quoted string." >&2
    exit 2
fi
python3 - "$file" || { echo "SABOTAGE FAILED TO APPLY" >&2; exit 2; }
if "$@" >/dev/null 2>&1; then
    echo "PASSED -- HOLE: the fence did not catch it"
    exit 1
fi
# The VERDICT is the exit status above; what follows is a hint at which
# check fired, and it is only a hint. A fence that embeds another
# tool's TAP output (the baker suite runs check.py over deliberately
# bad blobs) prints "not ok" lines that have nothing to do with the
# sabotage, so read the names, do not trust the first one.
echo "caught. failing lines (a hint, not the verdict):"
"$@" 2>&1 | grep -E "^not ok|^FAIL:|^ERROR:" | head -5 \
    || echo "  (fence failed with no recognisable failure line)"
