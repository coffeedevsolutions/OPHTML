#!/usr/bin/env python3
"""Read this fixture's README table back out of the blob it describes.

WHY THIS EXISTS. measure.sh checked the per-screen slot counts, the
121 total, and that the arena stayed under 16 KiB. Everything else in
the README's "from the baked blob" table was written once and never
re-derived, so when P3b-6 turned rounded boxes into tinted coverage
pairs, five figures went stale at once and the fixture's own checker
reported green:

    draw records  1,232 -> 2,048        textures  15 -> 12
    VRAM         248 -> 224 KiB         blob      210 -> 233 KiB
    arena        8,285 -> 8,165 B

The arena was the one that mattered most and the one deliberately
checked LOOSELY. measure.sh explains why -- an equality test fails when
a screen gains a label, which teaches people to edit the number instead
of reading it -- and that reasoning is still right for a REGRESSION
guard, so the ceiling stays exactly as it was. It is the wrong tool for
a DOCUMENTED figure, because a documented figure has to be true, not
merely under a bound. So there are now two rules over one number: the
ceiling says the demand has not crept back toward the 36 KiB the fixed
model charged, and this says the README is not lying about it.

Usage: figures.py <blob>. Exits non-zero on any disagreement.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "packages", "baker"))

from ps2ui_bake.uib import read_uib          # noqa: E402
from ps2ui_bake.arena import arena_size      # noqa: E402
from ps2ui_bake import vram                  # noqa: E402

# label in the README's first column -> how to compute it from the blob.
# VRAM is the BUDGET-charged figure, the same page-rounded model the
# bake's own budget check and examples/opl-env/README.md report, not
# the 256-byte allocator total: two models, and mixing them is how a
# footprint got published three times too large once already.
ROWS = {
    "slots":        lambda u, p: len(u.slots),
    "screens":      lambda u, p: len(u.screens),
    "textures":     lambda u, p: len(u.textures),
    "fonts":        lambda u, p: len(u.fonts),
    "draw records": lambda u, p: len(u.records),
    "VRAM":         lambda u, p: (
        sum(vram.page_rounded_size(t.width, t.height, t.fmt)
            for t in u.textures) + vram.clut_size() * len(u.cluts)) // 1024,
    "blob":         lambda u, p: os.path.getsize(p),
    "arena":        lambda u, p: arena_size(u),
}

# The fenced block under "What it says now" quotes ps2ui-bake's own
# output. A quotation of a tool that no longer says that is the same
# defect in a different shape, so it is compared verbatim -- minus the
# `-> path` tail, which is a temp directory and not a measurement.
TRANSCRIPT = re.compile(r"^What it says now:\s*\n+```\n(.*?)```", re.M | re.S)


def documented():
    """{label: int} from the `| **slots** | **121** | ... |` table."""
    text = open(os.path.join(HERE, "README.md"), encoding="utf-8").read()
    m = re.search(r"^And from the baked blob.*?\n(\|.*?)\n\n", text,
                  re.M | re.S)
    if not m:
        raise SystemExit("not ok - opl-scope/README.md: no 'And from the "
                         "baked blob' table. It was reworded or removed, "
                         "and this check has stopped reading it.")
    figs = {}
    for line in m.group(1).splitlines():
        cells = [c.strip().strip("*") for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        v = re.match(r"^([\d,]+)", cells[1])
        if cells[0] and v:
            figs[cells[0]] = int(v.group(1).replace(",", ""))
    return figs, text


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: figures.py <blob>")
    blob = sys.argv[1]
    u = read_uib(blob)
    doc, text = documented()

    fail = []
    matched = 0
    for label, compute in sorted(ROWS.items()):
        got = compute(u, blob)
        if label not in doc:
            fail.append("opl-scope/README.md's table has no `%s` row; the "
                        "blob says %s" % (label, format(got, ",")))
        elif doc[label] != got:
            fail.append("opl-scope/README.md says %s = %s, blob says %s"
                        % (label, format(doc[label], ","), format(got, ",")))
        else:
            matched += 1
    print("%s - opl-scope: %d of %d table figures match the blob"
          % ("ok" if matched == len(ROWS) else "not ok", matched, len(ROWS)))

    m = TRANSCRIPT.search(text)
    if not m:
        fail.append("opl-scope/README.md has no fenced block under 'What it "
                    "says now'; that quotation is what this check reads")
    else:
        want = [ln.split(" -> ")[0].rstrip()
                for ln in m.group(1).strip().splitlines()]
        got = [ln.split(" -> ")[0].rstrip()
               for ln in sys.stdin.read().strip().splitlines()
               if ln.startswith("ps2ui-bake:")]
        # NEITHER SIDE MAY BE EMPTY. `want == got` is true of two empty
        # lists, so a fenced block that stopped containing anything --
        # or a bake whose lines stopped starting with `ps2ui-bake:` --
        # would compare equal and report a verbatim match of nothing.
        if not want or not got:
            fail.append("opl-scope: the transcript comparison has %s to "
                        "compare; an empty side matches anything, which is "
                        "not a pass"
                        % ("no README lines" if not want
                           else "no bake output"))
        elif want == got:
            print("ok - opl-scope: the README quotes what ps2ui-bake now "
                  "prints, %d line(s), verbatim" % len(want))
        else:
            fail.append("opl-scope/README.md quotes a bake that no longer "
                        "happens.\n#   README: %s\n#   actual: %s"
                        % (" / ".join(want), " / ".join(got)))

    for f in fail:
        print("not ok - %s" % f)
    if fail:
        print("# The demand moved. Re-measure and update the README --")
        print("# those numbers are the input to the Phase 1 resource model.")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
