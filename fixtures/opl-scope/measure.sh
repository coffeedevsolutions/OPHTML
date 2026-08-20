#!/usr/bin/env bash
# Re-measure the UC-3 scoping fixture and check the numbers this
# directory's README quotes are still true.
#
# The fixture's whole value is being comparable later: at the Phase 1
# gate the question is "what does an OPL-class environment demand
# now", and a fixture that quietly stopped compiling cannot answer it.
# This runs the layout stage only -- no bake, so no raised cap needed
# -- and fails if the demand moves.
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
    node "$repo/packages/layout/bin/ps2ui-layout.js" \
        "$here/ui/$name.html" "$here/ui/opl.css" \
        -o "$out/$name.json" --strict >/dev/null
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

if [ "$fail" != "0" ]; then
    echo "# The demand moved. Re-measure and update the README's table --"
    echo "# those numbers are the input to the Phase 1 resource model."
    exit 1
fi
