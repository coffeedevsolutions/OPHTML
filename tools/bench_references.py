#!/usr/bin/env python3
"""Render the three pictures the Phase 1 streaming bench is read against.

`ps2ui-bake --preview` gives you one of them for free and it is the
least useful one: a blob whose covers are streamed has nothing in those
slots at bake time, so the preview shows empty boxes. That is correct --
it is exactly what ps2ui_render draws for an unfilled slot -- but a
sitting needs the other two as well.

  preview-unfilled.png    what an unset slot draws: nothing
  preview-filled.png      the covers in place, the host mirror of
                          ps2ui_tex_set
  preview-composited.png  the dialog over the covers, no clear between
"""
import sys

from ps2ui_bake.uib import read_uib
from ps2ui_bake import preview


def main(argv):
    if len(argv) != 2:
        print("usage: bench_references.py <build-dir>", file=sys.stderr)
        return 2
    out = argv[1]
    uib = read_uib(f"{out}/bench.uib")
    fills = {}
    for i in range(4):
        with open(f"{out}/covers/cover{i}.raw", "rb") as fh:
            fills[f"cover{i}"] = fh.read()

    preview.render(uib, screen="covers").save(f"{out}/preview-unfilled.png")
    filled = preview.render(uib, screen="covers", tex_fills=fills)
    filled.save(f"{out}/preview-filled.png")
    # Composited the way the console will do it: draw the base, then
    # draw the overlay over it with no clear in between. The overlay is
    # rendered on a transparent ground so the alpha_composite here is
    # the same operation the GS blend performs.
    over = preview.render(uib, screen="dialog", background=(0, 0, 0, 0))
    filled.alpha_composite(over)
    filled.save(f"{out}/preview-composited.png")
    print(f"bench references -> {out}/preview-unfilled|filled|composited.png",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
