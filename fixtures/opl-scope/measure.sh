#!/usr/bin/env bash
# Re-measure the UC-3 scoping fixture and check the numbers this
# directory's README quotes are still true.
#
# The fixture's whole value is being comparable later: at the Phase 1
# gate the question is "what does an OPL-class environment demand
# now", and a fixture that quietly stopped compiling cannot answer it.
# It used to run the layout stage only, because the bake could not
# complete without raising PS2UI_MAX_SLOTS by hand: 121 slots against a
# ceiling of 16. That ceiling is gone (PLAN 6.3), so this now bakes the
# whole environment and checks the arena it demands -- which is the
# number the resource model was built to produce and the one Phase 2
# will be compared against.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$here/../.."
out="${TMPDIR:-/tmp}/opl-scope"
mkdir -p "$out"

# screen:slots:focusables, as the README's table records them.
EXPECT="landing:15:7 library:43:17 detail:15:4 filters:20:12 recent:28:9"

fail=0
total_slots=0
for spec in $EXPECT; do
    name="${spec%%:*}"; rest="${spec#*:}"
    want_slots="${rest%%:*}"; want_focus="${rest##*:}"
    # --min-font-size 11 for the same reason examples/opl-env/build.sh
    # passes it, and this fixture is where that reason came from: it is
    # the same six screens at the same densities, and its secondary
    # text is 11-13px slot text. None of it warned until P3b-5 taught
    # the linter to see a data-slot at all. 11 keeps the rule live --
    # anything smaller still fails -- and S14 read that layer off an
    # SCPH-50000 and found it legible [F-046].
    node "$repo/packages/layout/bin/ps2ui-layout.js" \
        "$here/ui/$name.html" "$here/ui/opl.css" \
        -o "$out/$name.json" --strict --min-font-size 11 >/dev/null
    got=$(python3 -c "
import json,sys
ir=json.load(open('$out/$name.json'))
print(len(ir['slots']), len(ir['focus']['nodes']))")
    gs="${got%% *}"; gf="${got##* }"
    total_slots=$((total_slots + gs))
    if [ "$gs" = "$want_slots" ] && [ "$gf" = "$want_focus" ]; then
        echo "ok - $name: $gs slots, $gf focusables"
    else
        echo "not ok - $name: $gs slots / $gf focusables, README says $want_slots / $want_focus"
        fail=1
    fi
done

if [ "$total_slots" = "121" ]; then
    echo "ok - environment total: $total_slots slots"
else
    echo "not ok - environment total: $total_slots slots, README says 121"
    fail=1
fi

# The full bake. Nothing is edited to make this work any more, which is
# the whole point of the change that allowed it: an OPL-class
# environment is now something the shipped runtime loads.
bake=$(PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake \
    "$out/landing.json" "$out/library.json" "$out/detail.json" \
    "$out/filters.json" "$out/recent.json" -o "$out/opl.uib" 2>&1)
echo "$bake" | tail -2 | sed 's/^/# /'

slots=$(PYTHONPATH="$repo/packages/baker" python3 -c "
from ps2ui_bake.uib import read_uib
print(len(read_uib('$out/opl.uib').slots))")
if [ "$slots" = "121" ]; then
    echo "ok - the whole environment bakes into one blob: $slots slots, no raised cap"
else
    echo "not ok - baked blob has $slots slots, README says 121"
    fail=1
fi

# EVERY OTHER FIGURE THE README QUOTES, read back out of the blob.
# Until this ran, the checks above were the whole of it -- slot counts
# and an arena ceiling -- so P3b-6 moved draw records, textures, VRAM,
# the blob size and the arena underneath a table that kept reporting
# green. figures.py carries the detail; it is a separate file because a
# figure check written in shell is a figure check nobody extends.
if ! echo "$bake" | PYTHONPATH="$repo/packages/baker" \
        python3 "$here/figures.py" "$out/opl.uib"; then
    fail=1
fi

# The arena is the figure the resource model exists to produce. Asserted
# as a ceiling rather than an equality: this fixture is meant to grow,
# and a test that fails when a screen gains a label teaches people to
# edit the number instead of reading it. What it must not do is quietly
# climb back toward the 36 KiB the fixed model charged every blob.
#
# figures.py above ALSO checks this number, for equality, against the
# README. That is not a contradiction and neither rule replaces the
# other: this one is the regression guard and stays loose on purpose,
# that one is the documentation guard and a documented figure has to be
# true rather than merely under a bound. Growing the fixture means
# updating the README, which you are editing anyway; it does not mean
# editing a threshold.
arena=$(echo "$bake" | sed -n 's/.*arena \([0-9]*\) bytes.*/\1/p')
if [ -n "$arena" ] && [ "$arena" -lt 16384 ]; then
    echo "ok - arena $arena bytes, under 16 KiB (fixed maxima charged ~36 KiB)"
else
    echo "not ok - arena ${arena:-unknown} bytes"
    fail=1
fi

if [ "$fail" != "0" ]; then
    echo "# The demand moved. Re-measure and update the README's table --"
    echo "# those numbers are the input to the Phase 1 resource model."
    exit 1
fi
