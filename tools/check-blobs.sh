#!/bin/sh
# Validate every baked blob against what the C runtime assumes.
#
# One script, called by both ci.yml and hw.yml, because the flags below
# ARE the rules: which warnings a blob is allowed to carry, and how
# many. Spelled out in two workflow files a hundred lines apart, they
# drifted -- hw.yml checked the channel-6 blob with no flags at all
# while ci.yml checked the same file with --allow-dead 1 --strict, so
# one workflow's "valid" was looser than the other's for the same
# bytes. A rule that lives in one place cannot disagree with itself.
#
# Every blob runs --strict: warnings are failures. Anything deliberate
# is declared by count, so the instrument passes and one more than the
# instrument still fails. No blob here is allowed a standing warning --
# a log with permanent false alarms is a log people learn to skim.
#
# Usage: tools/check-blobs.sh [blob ...]
#   With no arguments, checks every blob it knows about that exists.
#   Named blobs must exist and must be known, so a typo is an error
#   rather than a silent pass over nothing.
set -eu

here=$(dirname "$0")
repo=$(cd "$here/.." && pwd)

# blob path : flags. Kept beside each other so the differences between
# them are readable as a group rather than hunted for across files.
known_flags() {
    case "$1" in
    examples/memcard/build/ui.uib)
        echo "--strict" ;;
    examples/memcard/build/testcard.uib)
        # The alignment card is made of 1px quads: four edge rules and
        # the step 8 interlace pair. The shimmer is the measurement.
        echo "--allow-hairline 5 --strict" ;;
    examples/channel6/build/ui.uib|examples/channel6/build/ui-16x9.uib)
        # The probe screen parks one quad outside its clip on purpose
        # (bring-up step 7's instrument). data-keep is build-time only
        # and never reaches the blob, so a validator reading the file
        # cannot tell an instrument from waste and should not guess.
        echo "--allow-dead 1 --strict" ;;
    *)
        return 1 ;;
    esac
}

ALL="examples/memcard/build/ui.uib
examples/memcard/build/testcard.uib
examples/channel6/build/ui.uib
examples/channel6/build/ui-16x9.uib"

if [ $# -gt 0 ]; then
    blobs=$*
    require=1          # named explicitly, so it had better be there
else
    blobs=$ALL
    require=0          # not every workflow bakes every blob
fi

checked=0
for blob in $blobs; do
    if ! flags=$(known_flags "$blob"); then
        echo "check-blobs: no rules for $blob" >&2
        echo "check-blobs: add it to this script rather than checking it" \
             "with ad-hoc flags -- that is how the two workflows drifted" >&2
        exit 2
    fi
    if [ ! -f "$repo/$blob" ]; then
        if [ "$require" = 1 ]; then
            echo "check-blobs: $blob does not exist" >&2
            exit 2
        fi
        continue
    fi
    # shellcheck disable=SC2086
    PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake.check \
        "$repo/$blob" $flags
    checked=$((checked + 1))
done

# Zero blobs checked is not success. A rename upstream would otherwise
# turn this whole step into a no-op that reports nothing and passes.
if [ "$checked" = 0 ]; then
    echo "check-blobs: no blobs found -- nothing was validated" >&2
    exit 2
fi
echo "check-blobs: $checked blob(s) validated"
