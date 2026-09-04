#!/usr/bin/env python3
"""Hold docs/deploying.md to the source it describes.

WHY THIS EXISTS. deploying.md was the first substantial document added
to this tree that nothing read. Every other claim here is derived from
what it describes -- check-example-figures.py reads the blob,
check-sweep-table.py reads the driver's own sprintf formats,
check-tutorial.py executes the tutorial from an empty directory -- and
check-tutorial.py's docstring names the reason:

    A tutorial nobody re-runs is a document that was true on the day it
    was written.

A deployment guide is mostly hardware, and most of it cannot run in CI.
That is what the [bench]/[practice] markers are for. But the parts that
ARE derivable from this repository were sitting in prose, and two of
them matter:

  * THE STATUS-FILL TABLE. Four full-screen flat colours, each a
    literal in runtime/sample/main.c, written out by hand in TWO
    documents. Change a fill in main.c and both quietly describe a
    console that no longer does that -- on the page a person reads
    while looking at a screen they cannot otherwise diagnose, which is
    the worst place in the tree for a stale number.

  * THE BUILD FLAGS. The guide's central command is
    `make -C runtime/sample UIB=...`, plus MINIMAL, STATIC and SCREEN.
    A flag that gets renamed leaves the guide telling a reader to type
    something that silently does nothing.

Run by CI. Not a substitute for someone actually deploying: nothing
here can promote a [practice] marker to [bench].
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIDE = "docs/deploying.md"
LOG = "docs/bringup.md"
SAMPLE = "runtime/sample/main.c"
MAKEFILE = "runtime/sample/Makefile"

# THE ONE FILL THAT IS NOT A STATUS, NAMED RATHER THAN INFERRED.
# `#0a0e1a` is the examples' canvas background: the UI's own ground,
# cleared before drawing, and meaningless as a signal. Every other
# gsKit_clear literal in the sample is a status and must be in the
# table. Naming it here rather than guessing "dark ones are backgrounds"
# means a new background has to be declared deliberately, the same
# friction EXPECTED_NPM has in check-versions.py.
NOT_A_STATUS = {(0x0A, 0x0E, 0x1A)}

# Black is no picture, which is a boot failure rather than a runtime
# one, so a status has to be clear of it. The darkest status today is
# dark red at luma 38; this floor sits below that on purpose. It is not
# a style preference, it is the difference between "the console is
# telling me something" and "the console is not running".
DARK_FLOOR = 30


def read(rel):
    return open(os.path.join(ROOT, *rel.split("/")), encoding="utf-8").read()


def luma(rgb):
    """Rec. 601, which is what bringup.md's luma column already is."""
    r, g, b = rgb
    return round(0.299 * r + 0.587 * g + 0.114 * b)


def table_rows(text, path):
    """(rgb, hex, luma-or-None) for the status-fill table's rows.

    ANCHORED TO THE TABLE'S OWN HEADER, not to row shape. The first
    version matched any `| name `#rrggbb`` row anywhere in the file and
    picked up bringup.md's probe-cell table 110 lines further down,
    reporting a fifth status fill that is a ground colour. A checker
    that reads the wrong table is worse than one that reads none: it
    fails on correct input, and the reader's cheapest way out is to
    stop believing it. Found by running it.
    """
    m = re.search(r"^\| fill \|[^\n]*\|\s*\n\|[-: |]+\|\s*\n"
                  r"((?:\|[^\n]*\|\s*\n)+)", text, re.M)
    if m is None:
        raise SystemExit("check-deploying: no `| fill |` table in %s -- it "
                         "was reformatted or removed, and this check has "
                         "stopped reading it" % path)
    out = []
    for row in m.group(1).strip().splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        hm = re.search(r"`#([0-9a-fA-F]{6})`", cells[0])
        if hm is None:
            raise SystemExit("check-deploying: row %r in %s's fill table "
                             "names no `#rrggbb`" % (row.strip(), path))
        h = hm.group(1).lower()
        lum = int(cells[1]) if len(cells) > 1 and cells[1].isdigit() else None
        out.append(((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)),
                    h, lum))
    return out


def main():
    fail = []

    def check(ok, ok_msg, bad_msg):
        print("%s - %s" % ("ok" if ok else "not ok", ok_msg if ok else bad_msg))
        if not ok:
            fail.append(bad_msg)

    src = read(SAMPLE)
    # Numeric literals only. The probe grounds are symbolic
    # (PROBE_GND_R) and are not statuses; a symbolic status would have
    # to be added here deliberately, which is the point.
    lits = set()
    for m in re.finditer(r"gsKit_clear\(\s*\w+\s*,\s*GS_SETREG_RGBAQ\(\s*"
                         r"0x([0-9a-fA-F]{2})\s*,\s*0x([0-9a-fA-F]{2})\s*,\s*"
                         r"0x([0-9a-fA-F]{2})\s*,", src):
        lits.add(tuple(int(g, 16) for g in m.groups()))
    if not lits:
        raise SystemExit("check-deploying: no gsKit_clear literals in %s -- "
                         "this check has stopped reading the source it is "
                         "supposed to derive from" % SAMPLE)
    status = lits - NOT_A_STATUS

    guide_rows = table_rows(read(GUIDE), GUIDE)
    log_rows = table_rows(read(LOG), LOG)

    # 1. Both documents describe the same four fills.
    check([h for _, h, _l in guide_rows] == [h for _, h, _l in log_rows],
          "%s and %s name the same %d status fills, in the same order"
          % (GUIDE, LOG, len(guide_rows)),
          "%s names %s and %s names %s; they are two copies of one table "
          "and a reader diagnosing a console may open either"
          % (GUIDE, [h for _, h, _l in guide_rows], LOG, [h for _, h, _l in log_rows]))

    # 2. Every fill the documents name is a literal the sample writes.
    for rgb, h, _ in guide_rows:
        check(rgb in status,
              "#%s is a gsKit_clear literal in %s" % (h, SAMPLE),
              "#%s is in the status table but %s never clears to it. Either "
              "the fill changed and both documents are stale, or the table "
              "names a colour that was never a status." % (h, SAMPLE))

    # 3. And every status the sample writes is named. The direction that
    #    catches a NEW fill nobody documented, which is the one an
    #    operator meets on a console with no idea what it means.
    named = {rgb for rgb, _h, _l in guide_rows}
    for rgb in sorted(status - named):
        check(False, "", "%s clears to #%02x%02x%02x and no status table "
                         "names it. A full-screen flat colour is always a "
                         "status; add it to %s and %s, or if it is a "
                         "background, declare it in NOT_A_STATUS here."
                         % (SAMPLE, rgb[0], rgb[1], rgb[2], GUIDE, LOG))
    if not (status - named):
        print("ok - every status fill %s writes is named in both tables "
              "(%d)" % (SAMPLE, len(status)))

    # 4. bringup.md states a luma per fill. It is Rec. 601 over the same
    #    hex, so it is derivable rather than remembered.
    for rgb, h, stated in log_rows:
        if stated is None:
            continue
        check(luma(rgb) == stated,
              "#%s luma %d, derived rather than remembered" % (h, luma(rgb)),
              "%s says #%s has luma %d; Rec. 601 over that hex is %d"
              % (LOG, h, stated, luma(rgb)))

    # 5. The rule the section states in prose, made mechanical.
    for rgb, h, _ in guide_rows:
        check(luma(rgb) >= DARK_FLOOR,
              "#%s is clear of black (luma %d)" % (h, luma(rgb)),
              "#%s has luma %d, under the %d floor. Black is no picture, "
              "which is a boot failure rather than a runtime one, so a "
              "status a person must tell apart from a dead console cannot "
              "be dark." % (h, luma(rgb), DARK_FLOOR))

    # 6. The build flags the guide tells a reader to type are real.
    mk = read(MAKEFILE)
    guide = read(GUIDE)
    flags = sorted(set(re.findall(r"^\s*-\s*`([A-Z][A-Z0-9_]*)=", guide, re.M))
                   | set(re.findall(r"make -C runtime/sample ([A-Z][A-Z0-9_]*)=",
                                    guide)))
    if not flags:
        check(False, "", "%s names no `make -C runtime/sample VAR=` flags; "
                         "this check has stopped reading them" % GUIDE)
    for f in flags:
        check(re.search(r"^\s*#.*\b%s\b" % f, mk, re.M) is not None
              or re.search(r"^\s*(ifdef|ifeq).*\b%s\b|^%s\s*[:?]?=" % (f, f),
                           mk, re.M) is not None
              or ("$(%s)" % f) in mk,
              "`%s=` is real in %s" % (f, MAKEFILE),
              "%s tells a reader to type `%s=` and %s never reads it, so "
              "the flag would do nothing and say nothing"
              % (GUIDE, f, MAKEFILE))

    # 7. Repository paths the guide names exist.
    # BUILD OUTPUTS ARE CHECKED BY THEIR DIRECTORY. ps2ui_sample.elf and
    # ui.uib do not exist until something builds them, so requiring the
    # file would fail on a clean checkout, which is the state a reader
    # of this guide is in. The directory has to be real either way.
    built = (".elf", ".uib", ".png", ".json", ".raw")
    # BOTH THE PROSE AND THE SHELL BLOCKS. The guide's central command
    # lives in a ```sh block, not in backticks, so a check that read
    # only inline code would have validated the paragraphs and skipped
    # the thing a reader actually types.
    RE_PATH = (r"(?:examples|runtime|docs|tools|packages|fixtures)"
               r"/[A-Za-z0-9_./-]+")
    cited = set(re.findall(r"`(%s)`" % RE_PATH, guide))
    for block in re.findall(r"```sh\n(.*?)```", guide, re.S):
        cited |= set(re.findall(RE_PATH, block))
    for rel in sorted(cited):
        # CLEAN-CHECKOUT SAFE. An artifact path is checked up to its
        # `build/` component, not to its directory: `examples/channel6/
        # build/` does not exist until something builds it, and a reader
        # of this guide is in exactly that state. Requiring the build
        # directory would have made this check pass only when it ran
        # after the example builds, which is an ordering dependency of
        # the same kind that once let the baker suite skip in CI.
        target = rel
        if rel.endswith(built):
            parts = rel.split("/")
            target = ("/".join(parts[:parts.index("build")]) if "build" in parts
                      else os.path.dirname(rel))
        check(os.path.exists(os.path.join(ROOT, *target.split("/"))),
              "%s exists" % (rel if target == rel else target + "/ (for " + rel + ")"),
              "%s names `%s` and %s is not in the tree" % (GUIDE, rel, target))

    if fail:
        print("not ok - %d claim(s) in %s disagree with the source"
              % (len(fail), GUIDE))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
