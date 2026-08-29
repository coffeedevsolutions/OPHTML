#!/usr/bin/env python3
"""Assert the Phase 2 driver's frame timer measures work, not waiting.

WHY THIS EXISTS. Through HW #260 the opl-env driver read COP0 Count
after gsKit_sync_flip, which blocks until vsync. The number it printed
was therefore the field period wearing a frame-time label: it looked
healthy, it was stable to 0.28%, it was photographed, and it could not
have reported a saturated EE any differently from an idle one. The
whole class of defect this project keeps finding -- a check that passes
for the wrong reason -- with a stopwatch instead of a renderer.

The fix is one line's worth of ordering, which is exactly the kind of
thing a later edit reinstates without noticing, because nothing about
the source looks wrong either way and the compiler has no opinion. So
the ordering is asserted here rather than trusted.

WHAT THIS DOES NOT VOUCH FOR. That the number is CORRECT -- only that
the clock is read on the working side of the flip. It also cannot see
whether the GS is still drawing when the EE stops counting; it is not
GS occupancy, and neither is the number it guards.
"""
import os
import re
import sys

# Resolved against the repo root rather than the caller's cwd: this runs
# from runtime/ under make and from the root in CI.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "runtime", "sample", "main.c")
REL = "runtime/sample/main.c"


def frame_loop(text):
    """The OPLENV block that holds the frame loop.

    There is more than one #ifdef PS2UI_SAMPLE_OPLENV in the sample --
    the window helpers get their own -- so this picks the block by what
    is inside it rather than by ordinal, which would silently follow
    the wrong one the day a helper block moves.
    """
    for start in [m.start() for m in
                  re.finditer(r"^#ifdef PS2UI_SAMPLE_OPLENV\b", text, re.M)]:
        depth = 0
        for m in re.finditer(r"^#(ifdef|ifndef|if|endif)\b", text[start:], re.M):
            depth += -1 if m.group(1) == "endif" else 1
            if depth == 0:
                block = text[start:start + m.end()]
                if "gsKit_sync_flip" in block:
                    return block
                break
        else:
            raise SystemExit("check-timing-probe: unterminated "
                             "#ifdef PS2UI_SAMPLE_OPLENV")
    raise SystemExit("check-timing-probe: no OPLENV block contains a frame loop")


def main():
    text = open(SRC).read()
    block = frame_loop(text)
    fail = []

    # Anchor on the accumulation and work backwards. The block also
    # holds the "instrument broken" olive loop, which kicks and flips
    # too, so anything anchored on the FIRST kick would measure that
    # one and pass no matter what the real loop did.
    # `(?:\(\))?` so the regression form -- reading the clock inline at
    # the accumulation, which is where it sat through HW #260 -- is
    # CAUGHT rather than merely unmatched. A pattern that only knew the
    # correct shape would report "no accumulation found" for the one
    # case this check exists to name.
    acc = re.search(r"ee_acc\s*\+=\s*\(\s*([A-Za-z_][A-Za-z0-9_]*(?:\(\))?)\s*-",
                    block)
    flip = kick = -1
    if not acc:
        fail.append("no `ee_acc += (<end> - ...)` accumulation found")
    else:
        flip = block.rfind("gsKit_sync_flip", 0, acc.start())
        kick = block.rfind("gsKit_queue_exec", 0, flip) if flip >= 0 else -1
        if flip < 0 or kick < 0:
            fail.append("the frame loop no longer kicks the DMA and flips "
                        "before accumulating; this check is stale")
    if acc and kick >= 0:
        end = acc.group(1)
        if end == "cop0_count()":
            fail.append("ee_acc reads the clock inline at the accumulation, "
                        "which is after the flip")
        else:
            capture = re.search(r"\b%s\s*=\s*cop0_count\(\)" % re.escape(end), block)
            if not capture:
                fail.append("`%s` is never assigned from cop0_count()" % end)
            elif not kick < capture.start() < flip:
                fail.append("`%s` is captured outside the window between "
                            "gsKit_queue_exec and gsKit_sync_flip" % end)

    # And the wall-clock period must still be reported, or the Phase 2
    # gate reading (F-034) loses the number its falsifier names.
    if not re.search(r"fld_acc\s*\+=", block):
        fail.append("the wall-clock frame period is no longer accumulated; "
                    "F-034's falsifier has nothing to read")

    for f in fail:
        print("not ok - %s: %s" % (REL, f))
    if fail:
        return 1
    print("ok - opl-env frame timer reads the clock before gsKit_sync_flip")
    print("ok - and still reports the wall-clock frame period beside it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
