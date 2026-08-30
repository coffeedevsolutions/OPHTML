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
    246 bytes late, and reported a correctly placed capture as outside
    the window. The comment that documents the mechanism broke the
    check on the mechanism. (The commit that fixed it said "~1.7 kB",
    which was a guess written as a measurement in the account of a bug
    about text being read as code. It is 246.)

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

    # The fill arm has to actually fill.
    #
    # Falsification found this hole: setting the loop bound to zero
    # compiles clean and passes every other rule here, leaving an arm
    # that draws nothing. That failure is less dangerous than the latch
    # it guards against -- a dead arm makes `gs` refuse to move, which
    # reads as alarm rather than as confidence -- but "the alarm and the
    # real fault are indistinguishable" is not a good place to leave a
    # falsifier, because the bench cannot tell which it is looking at.
    #
    # AND ABSENCE IS THE FAILURE. The first version gated these rules on
    # `if "PS2UI_OPLENV_FILL" in block:`, so deleting the arm outright
    # made both rules evaporate and the check printed "ok - and the fill
    # arm still draws what it promises" over a tree that had none. It
    # caught an arm that was weakened and passed an arm that was gone,
    # while asserting the opposite -- in a file whose sibling check
    # already carries the words "a checker that quietly passes when its
    # subject is absent is worse than no checker". Written twice, in
    # consecutive pull requests.
    if "PS2UI_OPLENV_FILL" not in block:
        fail.append("the fill arm is gone; gs has no falsifier, and a "
                    "reading with no arm to move it cannot be told from a "
                    "latched CSR FINISH")
    else:
        loop = re.search(r"for\s*\(\s*\w+\s*=\s*0\s*;\s*\w+\s*<\s*"
                         r"PS2UI_OPLENV_FILL_N\s*;", block)
        if not loop:
            fail.append("the fill arm no longer loops to PS2UI_OPLENV_FILL_N, "
                        "so it can draw a fixed count -- including zero")
        elif not re.search(r"gsKit_prim_sprite\s*\(", block[loop.end():]):
            fail.append("the fill arm loops but draws nothing; a `gs` that "
                        "refuses to move would then be unreadable -- dead arm "
                        "and latched instrument look identical")
        else:
            # AND IT HAS TO PAINT UNDER THE UI, NOT OVER IT.
            #
            # ZBuffering is off and paint order is strict. Drawn after
            # ps2ui_render, the sprites cover the telemetry they exist
            # to make trustworthy: the blend is As=0x40, half retention
            # per pass, so the default eight passes leave 0.0039 of the
            # destination -- under half a level of contrast. The arm
            # still measures correctly and the screen is a flat
            # rectangle, so the bench is told to photograph a build
            # with nothing on it. Every other rule here passed that.
            paint = re.search(r"ps2ui_render\s*\(", block)
            late = [m for m in re.finditer(r"gsKit_prim_sprite\s*\(", block)
                    if paint and m.start() > paint.start()]
            if late:
                fail.append("the fill arm draws after ps2ui_render, so it "
                            "paints over the readout -- at the default "
                            "FILL_N the screen is blank and the fill ELF "
                            "cannot be photographed")

    # THE EE ARM, held to the same three rules, and to one it does not
    # share with the fill arm.
    #
    # Absence is the failure here for the same reason: this is the
    # instrument P3d's gate rests on [F-042], and a check that passes
    # over a tree with no arm asserts the opposite of what it prints.
    if "PS2UI_OPLENV_EE" not in block:
        fail.append("the EE arm is gone; ee has one number and no model, "
                    "so half of F-038 goes back to being asserted rather "
                    "than measured")
    else:
        eloop = re.search(r"for\s*\(\s*\w+\s*=\s*0\s*;\s*\w+\s*<\s*"
                          r"PS2UI_OPLENV_EE_N\s*;", block)
        if not eloop:
            fail.append("the EE arm no longer loops to PS2UI_OPLENV_EE_N, so "
                        "it can run a fixed number of passes -- including "
                        "zero, which is a sweep with one point")
        elif not re.search(r"ps2ui_render\s*\(", block[eloop.end():]):
            fail.append("the EE arm loops but renders nothing; ee would then "
                        "refuse to move and a dead arm is indistinguishable "
                        "from an EE that does not scale with work")
        elif not re.search(
                r"for\s*\(\s*\w+\s*=\s*0\s*;\s*\w+\s*<\s*"
                r"PS2UI_OPLENV_EE_N\s*;[^)]*\)\s*\{?\s*ps2ui_render\s*\(",
                block):
            # AND IT MUST BE ps2ui_render THE LOOP CALLS, asserted
            # POSITIVELY. The whole claim is that the extra passes are
            # WHOLE RENDERS -- same command walk, same slot pen -- so
            # the fitted slope is the per-render EE cost. A loop calling
            # gsKit_prim_sprite instead would move `ee` a little and
            # `gs` a lot, and the slope would be neither quantity: the
            # fill arm wearing this arm's name.
            #
            # THE FIRST VERSION SCANNED FOR THE PRIM CALL IN A 400-BYTE
            # WINDOW AFTER THE LOOP, AND THAT IS ESCAPABLE. strip_comments
            # blanks comments while PRESERVING OFFSETS, so a comment
            # inside the loop body spends the window as spaces -- and the
            # comment on this very arm runs about 1,800 bytes, so the
            # distance is not hypothetical here. Review moved the prim
            # call past 420 bytes of comment and all thirteen checks
            # passed.
            #
            # Matching what MUST be there has no window to escape, which
            # is the same correction the peak-hold rule took in #68:
            # assert the thing that must happen, not the absence of one
            # that must not.
            fail.append("the EE arm's loop does not call ps2ui_render "
                        "directly, so its slope is not the per-render EE "
                        "cost it is fitted as")

    # The boot phase has to be zeroed before the clock starts.
    #
    # Frame 0's period is the only one not bounded by two vsyncs, so
    # without a wait here t_prev lands at an arbitrary phase into a
    # field and frame 0 "misses" when its work exceeds 16.683 minus
    # that phase. HW #263 bracketed frame 0's cost at 15.5-16.1 ms and
    # what it had actually bracketed was cost PLUS phase -- a finding
    # that survived a whole pull request before review caught it.
    if not re.search(r"gsKit_vsync_wait\s*\(\s*\)\s*;\s*\n\s*t_prev\s*=",
                     block):
        fail.append("t_prev is set without an unconditional vsync wait "
                    "before it, so frame 0's period carries an unzeroed "
                    "boot phase and any bracket on its cost is really a "
                    "bracket on cost plus phase")
    if re.search(r"gsKit_sync_flip\s*\(\s*\w+\s*\)\s*;\s*\n\s*t_prev\s*=",
                 block):
        fail.append("gsKit_sync_flip cannot zero the boot phase: it is "
                    "guarded by !FirstFrame, which is still set here, so "
                    "it skips the wait entirely")

    # The one-token invariant rests on GS_ONESHOT, not on the driver's
    # restraint. With the oneshot queue, queue_exec finds Per_Queue empty
    # and returns before appending; under GS_PERSISTENT gsKit appends a
    # second token of its own and gsKit_finish() would return on the
    # wrong one. Forbidding gsKit_set_finish in the driver does not cover
    # that, because the extra token would not be the driver's.
    whole = strip_comments(open(SRC).read())
    if not re.search(r"GS_ONESHOT", whole):
        fail.append("GS_ONESHOT is gone; under GS_PERSISTENT gsKit appends "
                    "its own second FINISH token and gsKit_finish() can "
                    "return on the wrong one")
    if re.search(r"gsKit_mode_switch\s*\([^)]*GS_PERSISTENT", whole):
        fail.append("the driver switches to GS_PERSISTENT, which puts a "
                    "second FINISH token per frame in the chain")

    # The peak-holds, which are what make the scroll frame readable at
    # all -- the means are over a 1-in-30 duty cycle and never print it.
    #
    # BOTH, because the two spikes coincide: the scroll frame does the
    # bind work on the EE and pushes 28,224 bytes through the same
    # chain. An ee peak paired with a gs mean is a lower bound on the
    # worst frame, which is what F-037's 4.59 ms had to be labelled.
    # MATCH THE UPDATE, NOT THE DECLARATION. The first version of this
    # loop tested `\b<var>\s*=`, which `u32 gs_peak = 0;` satisfies --
    # so deleting the peak-hold entirely left the rule green. The rule
    # it replaced, `ee_peak\s*=\s*ee\b`, could not have matched a
    # declaration; generalising it is what introduced the hole. Requiring
    # the comparison inside a condition cannot be satisfied by a
    # definition.
    for var, why in (("ee_peak", "the frame that has to fit inside a field "
                                 "is back to being invisible"),
                     ("gs_peak", "the worst frame is back to being an ee "
                                 "peak paired with a gs mean, which is a "
                                 "lower bound and not a reading")):
        # BOTH HALVES, tied by a backreference so it is the same
        # variable on each side. The rule before this one matched the
        # assignment and missed the declaration; its replacement matched
        # the comparison and missed the assignment -- the mirror image,
        # introduced while fixing the original. `if (gsu > gs_peak)
        # ee_n++;` and `if (ee > ee_peak) ee_peak = 0;` both compile
        # clean and both print ^0.00 forever, which is the same
        # silent-zero failure the fill arm exists to catch on gs.
        if not re.search(r"if\s*\(\s*(\w+)\s*>\s*%s\s*\)\s*%s\s*=\s*\1\s*;"
                         % (var, var), block):
            fail.append("no peak-hold on %s; %s" % (var[:2], why))

    # miss_at, because `m` alone says how many and never when -- and the
    # first explanation offered for HW #262's single miss was wrong by a
    # factor of seven with nothing in the readout able to check it.
    # `= frame` for the same reason as above: `miss_at = 0` is a
    # declaration and must not count as recording anything.
    if not re.search(r"\bmiss_at\s*=\s*frame\b", block):
        fail.append("the dropped-field counter records how many but not "
                    "when; a miss with no frame index cannot be told from "
                    "a boot transient")
    elif not re.search(r"if\s*\(\s*!\s*missed\s*\)\s*miss_at\s*=", block):
        fail.append("miss_at is not latched to the FIRST miss, so a later "
                    "one overwrites the only evidence about the earliest")
    elif not re.search(r"\bmiss_at\s*=\s*frame\s*-\s*1\b", block):
        # `frame`, not `frame - 1`, is the shape this shipped with and
        # the reason @0 was unreachable while the runbook documented it
        # as the boot-transient signal. The off-by-one is the entire
        # meaning of the field, so it is checked rather than remembered.
        fail.append("miss_at records the raw frame index; `loop` is the "
                    "PREVIOUS iteration's duration, so the frame that "
                    "overran is frame - 1 and @0 becomes unreachable")

    # EVERY NUMBER HAS TO REACH THE READOUT.
    #
    # This file checked each figure where it is ACCUMULATED and never
    # where it is PRINTED, so a value could be computed correctly and
    # then dropped on the way to the screen with every rule still green.
    # miss_at is where that bites hardest -- replacing its sprintf
    # argument with a literal 0 makes the bench read `m1@0` on every
    # run, which is exactly the string the runbook documents as a boot
    # transient. A build that silently lost the index would have been
    # indistinguishable from the one condition the index was added to
    # detect. The whole value of these numbers is that a person can read
    # them off a photograph.
    # COUNT the appearances, do not merely find one. A millisecond
    # figure is printed as two arguments -- `x / 1000` and `(x % 1000)
    # / 10` -- so replacing just one of them leaves the other to satisfy
    # a bare search while the screen shows 0.08 for 1.08. Found by
    # falsifying this very rule one commit after writing it.
    printed = "".join(re.findall(r"sprintf\s*\(\s*telem[^;]*;", block, re.S))
    for var, uses, role in (("ee_us", 2, "the EE mean"),
                            ("gs_us", 2, "the GS mean"),
                            ("ee_pk_us", 2, "the EE peak"),
                            ("gs_pk_us", 2, "the GS peak"),
                            ("fld_us", 2, "the frame period"),
                            ("missed", 1, "the dropped-field count"),
                            ("miss_at", 1, "the frame index of the first miss")):
        n = len(re.findall(r"\b%s\b" % var, printed))
        if n == 0:
            fail.append("%s (%s) is computed but never reaches the readout, "
                        "so it cannot be read off a photograph" % (var, role))
        elif n != uses:
            fail.append("%s (%s) reaches the readout %d time(s), not %d -- a "
                        "millisecond figure needs both its whole and "
                        "fractional argument or the screen shows a wrong "
                        "number rather than no number" % (var, role, n, uses))

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
    print("ok - ee and gs both carry a peak-hold beside the mean")
    print("ok - and a dropped field records when, not only how many")
    print("ok - and every figure computed actually reaches the readout")
    print("ok - and the fill arm still draws what it promises, under the UI")
    print("ok - and the EE arm runs whole renders, not primitives")
    print("ok - one FINISH token per frame, on the oneshot queue")
    print("ok - and the boot phase is zeroed before the clock starts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
