#!/usr/bin/env bash
# Bake the Phase 1 streaming bench blob and the covers that feed it.
#
# Two screens in one blob, because the sitting asks two questions of
# the same console state:
#
#   covers  -- four 128x128 streamed slots the app fills at runtime
#   dialog  -- an overlay, drawn OVER covers in the same frame
#
# The covers are written as raw PSMCT32 next to the blob. Point this at
# your own art to bake real covers; with no arguments it writes the
# synthetic ones, which are built to be readable from a photograph.
#
#   ./fixtures/bench-stream/build.sh                     # synthetic
#   ./fixtures/bench-stream/build.sh ~/Art/*.png         # your art
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
out="$here/build"
mkdir -p "$out"

for screen in covers dialog; do
    node "$repo/packages/layout/bin/ps2ui-layout.js" \
        "$here/ui/$screen.html" "$here/ui/bench.css" -o "$out/$screen.json"
done

# covers first, so it is screen 0 and the ELF opens on it.
PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake \
    "$out/covers.json" "$out/dialog.json" -o "$out/bench.uib" \
    --preview "$out/preview.png"

PYTHONPATH="$repo/packages/baker" python3 -m ps2ui_bake.check "$out/bench.uib"

python3 "$repo/tools/make_cover_raw.py" "$@" \
    --out-dir "$out/covers" --size 128x128 --count 4

# The references a bench photograph is read against. Three, because the
# sitting has three pictures to compare and only one of them is what
# `--preview` gives you for free:
#
#   unfilled    what an unset slot draws -- nothing. The previewer skips
#               it exactly as ps2ui_render does.
#   filled      the covers in place, the host mirror of ps2ui_tex_set.
#   composited  the dialog over the covers, no clear between them.
PYTHONPATH="$repo/packages/baker" python3 "$repo/tools/bench_references.py" \
    "$out"

echo
echo "bench blob:   $out/bench.uib"
echo "covers:       $out/covers/cover0.raw .. cover3.raw"
echo
echo "Copy $out/covers/ to your USB drive as  ps2ui/  so the ELF finds"
echo "mass:/ps2ui/cover0.raw. The blob is compiled into the ELF; the"
echo "covers are not, which is the point."
