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


def strip_comments(text):
    """Blank out comments and string literals, preserving offsets.

    A source-level check that reads prose as code is a check with a
    silent false answer, and this one had it: the comment explaining
    that `gsKit_queue_exec_real` appends the FINISH token contains the
    string "gsKit_queue_exec", so an rfind for the DMA kick landed on
    the sentence ABOUT the kick rather than the kick, put the anchor
    ~1.7 kB late, and reported a correctly placed capture as outside
    the window. The comment that documents the mechanism broke the
    check on the mechanism.

    Offsets are preserved (comments become spaces) so every position
    computed here still indexes the real source.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        two = text[i:i + 2]
        if two == "/*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(" " if c != "\n" else "\n" for c in text[i:j]))
            i = j
        elif two == "//":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif text[i] in "\"'":
            q, j = text[i], i + 1
            while j < n and text[j] != q:
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(" " * (j - i))
            i = j
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def accumulation(block, acc_name):
    """Where the value fed to `<acc_name> +=` was captured.

    Two spellings reach the same place, and a check that knew only one
    would report "no accumulation found" for the other -- which reads
    as a missing measurement rather than an unrecognised one, and is
    the wrong alarm:

        ee_acc += ticks_to_us(t_work - t0);        direct
        u32 ee = ticks_to_us(t_work - t0);         via a local, which
        ee_acc += ee;                              peak-hold needs

    Returns (end_name, position_of_the_accumulation), or (None, None).
    The `(?:\(\))?` keeps the regression form -- reading the clock
    inline at the accumulation -- CAUGHT rather than merely unmatched.
    """
    direct = re.search(r"\b%s\s*\+=\s*(?:ticks_to_us)?\s*\(\s*"
                       r"([A-Za-z_][A-Za-z0-9_]*(?:\(\))?)\s*-" % acc_name,
                       block)
    if direct:
        return direct.group(1), direct.start()
    via = re.search(r"\b%s\s*\+=\s*([A-Za-z_][A-Za-z0-9_]*)\s*;" % acc_name,
                    block)
    if not via:
        return None, None
    local = re.search(r"\b%s\s*=\s*(?:ticks_to_us)?\s*\(\s*"
                      r"([A-Za-z_][A-Za-z0-9_]*(?:\(\))?)\s*-"
                      % re.escape(via.group(1)), block)
    if not local:
        return None, None
    return local.group(1), via.start()


def main():
    text = open(SRC).read()
    block = strip_comments(frame_loop(text))
    fail = []

    # Anchor on the accumulation and work backwards. The block also
    # holds the "instrument broken" olive loop, which kicks and flips
    # too, so anything anchored on the FIRST kick would measure that
    # one and pass no matter what the real loop did.
    end_name, acc_at = accumulation(block, "ee_acc")

    class _A:  # keep the existing shape below readable
        def __init__(self, g, p): self._g, self._p = g, p
        def group(self, _): return self._g
        def start(self): return self._p
    acc = _A(end_name, acc_at) if end_name is not None else None
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
            # EVERY assignment before the accumulation, not the first.
            #
            # re.search stops at the first match, and PR #64's review
            # found the hole that leaves: keep the correct capture and
            # ADD a second one after the flip. ee_acc then holds the
            # post-flip value -- exactly the HW #260 defect -- while
            # this check reports ok, because it had already stopped
            # looking. Reproduced before fixing: syntax-check green,
            # timing-check green, the regression live.
            #
            # A check that passes because it stopped looking is the
            # fault class this file exists to prevent. It is not much
            # of a defence against it to contain one.
            caps = [m for m in
                    re.finditer(r"\b%s\s*=\s*cop0_count\(\)" % re.escape(end),
                                block)
                    if m.start() < acc.start()]
            if not caps:
                fail.append("`%s` is never assigned from cop0_count()" % end)
            elif not all(kick < m.start() < flip for m in caps):
                fail.append("`%s` is captured outside the window between "
                            "gsKit_queue_exec and gsKit_sync_flip" % end)

    # And the wall-clock period must still be reported, or the Phase 2
    # gate reading (F-034) loses the number its falsifier names.
    if not re.search(r"fld_acc\s*\+=", block):
        fail.append("the wall-clock frame period is no longer accumulated; "
                    "F-034's falsifier has nothing to read")

    # P3a's gs capture. Same shape of rule as the ee one, because it
    # has the same shape of failure: the number is only a measurement
    # if the clock is read AFTER gsKit_finish() has actually waited.
    # Read it before, and gs is whatever the DMA kick cost -- small,
    # stable, and indistinguishable from an idle GS, which is the
    # answer the plan already expects.
    gend0, gacc_at = accumulation(block, "gs_acc")
    gacc = _A(gend0, gacc_at) if gend0 is not None else None
    if not gacc:
        fail.append("no `gs_acc += (<end> - ...)` accumulation; the GS's "
                    "share of the field is no longer measured")
    else:
        gend = gend0
        wait = block.rfind("gsKit_finish()", 0, gacc.start())
        if wait < 0:
            fail.append("gs_acc accumulates without a gsKit_finish() before "
                        "it, so nothing waited for the GS")
        elif gend == "cop0_count()":
            fail.append("gs_acc reads the clock inline at the accumulation, "
                        "which is after the flip rather than after the wait")
        else:
            gcaps = [m for m in
                     re.finditer(r"\b%s\s*=\s*cop0_count\(\)" % re.escape(gend),
                                 block)
                     if m.start() < gacc.start()]
            if not gcaps:
                fail.append("`%s` is never assigned from cop0_count()" % gend)
            elif not all(m.start() > wait for m in gcaps):
                fail.append("`%s` is captured before gsKit_finish() returns, "
                            "so it measures the DMA kick and not the GS"
                            % gend)
        # Arming a second FINISH token puts two per frame in the chain.
        if re.search(r"\bgsKit_set_finish\s*\(", block):
            fail.append("the driver arms its own FINISH token; "
                        "gsKit_queue_exec_real already appended one")

    # The peak-hold, which is what makes the scroll frame readable at
    # all -- the mean is over a 1-in-30 duty cycle and never prints it.
    if not re.search(r"ee_peak\s*=\s*ee\b|>\s*ee_peak", block):
        fail.append("no peak-hold on ee; the frame that has to fit inside "
                    "a field is back to being invisible")

    # F-034's falsifier is "any dropped field", and a 60-frame mean can
    # only be read for that indirectly and only while the drop is
    # inside the window. The counter that reads it directly has to
    # survive, and it has to be cumulative -- a reset would put it back
    # to answering "was a field dropped recently", which is a different
    # question from the one the finding asks.
    if not re.search(r"\bmissed\+\+", block):
        fail.append("no dropped-field counter; F-034's falsifier is back to "
                    "being inferred from a rolling mean")
    elif re.search(r"\bmissed\s*=\s*0\s*;",
                   # rindex: the block's FIRST `while (1)` is the olive
                   # "instrument broken" loop, same hazard as the kick.
                   block[block.rindex("while (1)"):] if "while (1)" in block
                   else ""):
        fail.append("the dropped-field counter resets inside the frame loop, "
                    "so it only reports drops in the current window")

    for f in fail:
        print("not ok - %s: %s" % (REL, f))
    if fail:
        return 1
    print("ok - opl-env frame timer reads the clock before gsKit_sync_flip")
    print("ok - on every capture that reaches the accumulation, not just the first")
    print("ok - and still reports the wall-clock frame period beside it")
    print("ok - and counts dropped fields cumulatively")
    print("ok - gs is read after gsKit_finish() waited, not after the kick")
    print("ok - and the driver does not arm a second FINISH token")
    print("ok - ee carries a peak-hold beside the mean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
