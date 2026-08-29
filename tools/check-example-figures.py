#!/usr/bin/env python3
"""Diff a shipped example's documented figures against its actual blob.

WHY THIS EXISTS. examples/opl-env/README.md opens its measurement block
with "Taken from the blob, not estimated." They were, once. Then #63
added the telem slot to library.html, the library screen went 43 -> 44,
and every figure derived from a count went stale: 125 slots became 126,
a 246,032-byte blob became 246,096, a 6,951-byte arena became 7,003.

Nothing noticed, through two pull requests and a phase lock, because
F-031 names its instrument as that README -- a hand-written document --
and nothing read the header back into it. A number nobody re-derives is
a number that is true on the day it is written and unfalsifiable after.
F-031's falsifier (an arena past the old 35,648-byte ceiling) was never
close to threatened, so the FINDING was right the whole time and its
CLAIM still carried a wrong number. That is the failure this closes.

WHAT THIS DOES NOT VOUCH FOR. That the blob is current. It reads
whatever build/ holds and does not bake, so a stale local build with a
matching README passes. In CI that cannot happen -- examples/*/build/
is gitignored, so the blob only exists because the step before this one
made it -- but on a workstation it can, and the failure is silent.
Rebuild before trusting a pass.

(The first version of this file said "reads the committed build/". It
is not committed. The step was also placed before the build that
creates it, on a comment asserting it ran after. Both were written with
the same confidence as the figures they exist to check.)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packages", "baker"))

from ps2ui_bake.uib import read_uib          # noqa: E402
from ps2ui_bake.arena import arena_size      # noqa: E402

EXAMPLES = [("opl-env", "examples/opl-env")]


def documented(readme):
    """The fenced `name  value` block under ## Measurements."""
    text = open(readme).read()
    m = re.search(r"^## Measurements\s*$(.*?)^```(.*?)^```",
                  text, re.M | re.S)
    if not m:
        raise SystemExit("check-example-figures: no fenced measurement "
                         "block under ## Measurements in %s" % readme)
    figs = {}
    for line in m.group(2).splitlines():
        line = line.split("(")[0].strip()
        if not line:
            continue
        f = re.match(r"^(\S+(?:\s+\S+)*?)\s+([\d,]+)\s*(bytes|KiB)?$", line)
        if f:
            figs[f.group(1)] = int(f.group(2).replace(",", ""))
    return figs


def actual(dirpath):
    blob = os.path.join(ROOT, dirpath, "build", "ui.uib")
    if not os.path.exists(blob):
        # FAIL, never skip. A checker that quietly passes when its
        # subject is absent is worse than no checker: it reports green
        # for the one state in which it has verified nothing.
        raise SystemExit(
            "not ok - %s: no blob at %s. Run its build.sh first; this "
            "check does not bake, and passing it by not running is not "
            "passing it." % (dirpath, os.path.relpath(blob, ROOT)))
    u = read_uib(blob)
    return {
        "blob": os.path.getsize(blob),
        "arena": arena_size(u),
        "screens": len(u.screens),
        "slots": len(u.slots),
        "focus nodes": len(u.focus),
        "textures": len(u.textures),
        "fonts": len(u.fonts),
    }


def main():
    fail = []
    for name, dirpath in EXAMPLES:
        readme = os.path.join(ROOT, dirpath, "README.md")
        doc, act = documented(readme), actual(dirpath)
        # Count MATCHES, not comparisons. Counting comparisons would
        # print "7 figures match" on a run where three of them did not,
        # which is the genre of bug this file is here to close.
        matched = 0
        for key, got in sorted(act.items()):
            if key not in doc:
                fail.append("%s/README.md documents no `%s`; the blob has "
                            "%d" % (name, key, got))
            elif doc[key] != got:
                fail.append("%s/README.md says %s = %s, blob says %s"
                            % (name, key, format(doc[key], ","),
                               format(got, ",")))
            else:
                matched += 1
        print("%s - %s: %d of %d documented figures match the blob"
              % ("ok" if matched == len(act) else "not ok",
                 name, matched, len(act)))
    for f in fail:
        print("not ok - %s" % f)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
