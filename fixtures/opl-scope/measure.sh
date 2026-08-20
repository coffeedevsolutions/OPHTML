#!/usr/bin/env bash
# Re-measure the UC-3 scoping fixture and check the numbers this
# directory's README quotes are still true.
#
# The fixture's whole value is being comparable later: at the Phase 1
# gate the question is "what does an OPL-class screen demand now",
# and a fixture that quietly stopped compiling cannot answer it. This
# runs the layout stage only -- no bake, so no raised cap needed --
# and fails if the demand moves.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$here/../.."
out="${TMPDIR:-/tmp}/opl-scope.json"

EXPECT_SLOTS=43
EXPECT_FOCUS=17

node "$repo/packages/layout/bin/ps2ui-layout.js" \
    "$here/ui/library.html" "$here/ui/opl.css" -o "$out" --strict

python3 - "$out" "$EXPECT_SLOTS" "$EXPECT_FOCUS" <<'PY'
import json, sys
ir = json.load(open(sys.argv[1]))
want_slots, want_focus = int(sys.argv[2]), int(sys.argv[3])
slots = len(ir["slots"])
focus = len(ir["focus"]["nodes"])
ok = True
for name, got, want in (("slots", slots, want_slots),
                        ("focusables", focus, want_focus)):
    if got == want:
        print(f"ok - opl-scope {name}: {got}")
    else:
        ok = False
        print(f"not ok - opl-scope {name}: {got}, README says {want}")
if not ok:
    print("# The demand moved. Re-measure and update the README's table --"
          "\n# that number is the input to the Phase 1 resource model.")
    sys.exit(1)
PY
