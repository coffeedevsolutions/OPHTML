#!/usr/bin/env python3
"""Hold the `.uib` v7 layout to the stability pledge.

WHY THIS EXISTS. docs/format-uib.md already says "version bumps on any
incompatible change", and the version history shows that rule being
followed honestly four times: v4, v5, v6 and v7 each explain which
stride moved and why a feature bit could not have carried it.

That rule permits v8 next week. The PLEDGE is the stronger promise
docs/PLAN.md's Phase 4 has been carrying since before v6 and deferring
ever since -- deferred twice, because a format break kept landing
inside the phase that was supposed to end them:

    "Then npm + PyPI, and a format stability pledge post-v7."

Making it means saying that v7 is the last incompatible layout, and
that additions from here go in FEATURE BITS rather than in strides. A
promise about what will not happen is worth exactly as much as the
thing that notices when it does, so this file is that thing.

WHAT IS FROZEN, AND WHAT IS DELIBERATELY NOT.

  * FROZEN: every struct's format string and size, MAGIC, VERSION, and
    the VALUE of every feature bit already assigned. Those are what a
    v7 reader in the field walks; move any of them and blobs it has
    already been handed stop parsing.

  * NOT FROZEN: the SET of feature bits. Adding FEAT_* and widening
    FEAT_KNOWN is the growth path the pledge points at, so this check
    must let that through -- a fence that forbids the escape hatch it
    recommends would just get deleted the first time someone needed it.

  * NOT COVERED HERE: the C side. runtime/ps2ui.h has its own structs
    and check-versions.py already holds PS2UI_VERSION to uib.VERSION;
    the two pens are held to each other by the cross-language tests in
    packages/baker/tests. This file is about the writer's layout, which
    is the one a third-party reader would be written against.

WHAT THE FALSIFICATION HAD TO GET PAST, WHICH IS WORTH WRITING
DOWN. uib.py already carries its own size asserts -- five statements
covering eleven structs, `assert _KERN.size == 12` among them -- so the
obvious sabotage, widen a struct and run this, is intercepted at IMPORT
time and never reaches a single check below. It exits nonzero and looks
caught. It is caught, by a fence that predates this file.

So the stride-growth case was re-run with uib.py's matching assert
updated in the same edit, which is what a person actually breaking the
format would do, and only then does the failure below belong to this
file. The distinction is the whole reason this repository falsifies
anything: a check that exits nonzero for somebody else's reason is a
check nobody has tested.

The asserts also cover strictly less than this does. They know sizes
and only sizes, for the structs that have one. They do not see a
field-order swap that keeps the total, a renumbered feature bit, MAGIC,
or VERSION -- which is four of the five sabotages run against this
file. Only the stride case overlaps at all.

BREAKING THE PLEDGE IS ALLOWED AND HAS A PRICE. It is a decision, not
an accident: bump VERSION, and this check fails until the record below
is updated in the same change, which is where somebody has to write
down what broke and why. That is the whole mechanism -- it does not
prevent a v8, it prevents a v8 that nobody noticed shipping.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packages", "baker"))

PLEDGED_VERSION = 7

# Recorded from the tree on the day the pledge was made, not retyped
# from the spec: `s.format` and `s.size` off the live Struct objects.
# A copy of a document would drift from the code the document
# describes, which is the failure this repository has found in a font
# path list four times.
FROZEN_STRUCTS = {
    "_HEADER": ("<IHHHHHHIHHIIIIIIIHHIIHHIIHHHH", 84),
    "_TEX": ("<BBHHHIII", 20),
    "_CLUT": ("<HHI", 8),
    "_CMD": ("<BBHhhHHHHHHHHH6x", 32),
    "_FOCUS": ("<HHHHHHIhhHH", 24),
    "_FONT": ("<HHHHHHIH2xI", 24),
    "_SLOT": ("<IIhhHHBBHHHHh", 28),
    "_SCREEN": ("<IIIHHHHH2x", 24),
    "_TINT": ("<BBBB", 4),
    "_KERN": ("<IIh2x", 12),
}

FROZEN_MAGIC = 0x31424955  # "UIB1"

# Value, not membership. A sixth bit may be added; bit 1 may not stop
# meaning kerning.
FROZEN_FEATURE_BITS = {
    "FEAT_DYNAMIC_TEXT": 1 << 0,
    "FEAT_KERNING": 1 << 1,
    "FEAT_SLOT_SPACING": 1 << 2,
    "FEAT_STREAMED_TEX": 1 << 3,
    "FEAT_ROLE_TINTS": 1 << 4,
}

BREAKING_IT = (
    "Breaking the pledge is a decision this check exists to make "
    "deliberate rather than to forbid. If the break is intended: bump "
    "uib.VERSION and PS2UI_VERSION together, update PLEDGED_VERSION, "
    "FROZEN_STRUCTS and FROZEN_FEATURE_BITS here in the same change, "
    "add the entry to docs/format-uib.md's Versioning list saying which "
    "stride moved and why a feature bit could not carry it, and say in "
    "docs/PLAN.md that the pledge was broken and when. If it is not "
    "intended, this is the message that was supposed to reach you.")


def main():
    from ps2ui_bake import uib

    fail = []

    def check(ok, ok_msg, bad_msg):
        print("%s - %s" % ("ok" if ok else "not ok", ok_msg if ok else bad_msg))
        if not ok:
            fail.append(bad_msg)

    # 1. The version the pledge is about.
    check(uib.VERSION == PLEDGED_VERSION,
          "the format is v%d, the version the pledge froze" % PLEDGED_VERSION,
          "uib.VERSION is %d and the pledge was made at v%d. %s"
          % (uib.VERSION, PLEDGED_VERSION, BREAKING_IT))

    # 2. MAGIC. Changing it does not break a reader so much as make
    #    every existing blob unrecognisable, which is worse.
    check(uib.MAGIC == FROZEN_MAGIC,
          "MAGIC is 0x%08x, unchanged" % FROZEN_MAGIC,
          "MAGIC is 0x%08x and the pledge froze 0x%08x. Every blob ever "
          "written carries the old one. %s"
          % (uib.MAGIC, FROZEN_MAGIC, BREAKING_IT))

    # 3. Every struct, by format string AND size. The size alone would
    #    miss a field-order swap that kept the total; the format string
    #    alone would miss nothing, but printing both makes the failure
    #    readable without opening struct's documentation.
    for name, (fmt, size) in sorted(FROZEN_STRUCTS.items()):
        s = getattr(uib, name, None)
        if s is None:
            check(False, "", "uib.%s is gone. A v7 reader in the field still "
                             "walks it. %s" % (name, BREAKING_IT))
            continue
        check(s.format == fmt and s.size == size,
              "%s is %r, %d bytes" % (name, fmt, size),
              "%s is now %r (%d bytes); the pledge froze %r (%d bytes). A "
              "v7 reader walks this table at the frozen stride, so a blob "
              "written by this tree would be parsed as garbage rather than "
              "refused. %s"
              % (name, s.format, s.size, fmt, size, BREAKING_IT))

    # 4. Assigned feature bits keep their values. New ones are the
    #    growth path and are allowed -- this loop is over the FROZEN
    #    dict, not over uib's, on purpose.
    for name, value in sorted(FROZEN_FEATURE_BITS.items(),
                              key=lambda kv: kv[1]):
        got = getattr(uib, name, None)
        check(got == value,
              "%s is still bit %d" % (name, value.bit_length() - 1),
              "%s is %r and the pledge froze %r. A blob in the field sets "
              "that bit meaning the old feature; renumbering it makes every "
              "such blob claim something else. %s"
              % (name, got, value, BREAKING_IT))

    # 5. And the growth path is open rather than merely permitted: every
    #    frozen bit must still be inside FEAT_KNOWN, or a loader would
    #    refuse blobs that legitimately set it.
    missing = [n for n, v in FROZEN_FEATURE_BITS.items()
               if not (uib.FEAT_KNOWN & v)]
    check(not missing,
          "FEAT_KNOWN (0x%02x) still admits every frozen bit" % uib.FEAT_KNOWN,
          "FEAT_KNOWN no longer admits %s, so a loader would refuse blobs "
          "that legitimately set it. %s" % (", ".join(sorted(missing)),
                                            BREAKING_IT))

    if fail:
        print("not ok - %d part(s) of the frozen v%d layout have moved"
              % (len(fail), PLEDGED_VERSION))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
