#!/usr/bin/env python3
"""Build the texel-alignment test card (backlog B3, bring-up step 6).

Writes testcard.uib directly through the baker's Python API — no HTML,
because the point is a hand-controlled texture drawn 1:1:

  * a RESOLUTION WEDGE across the canvas center: 64x64 PSMCT32
    checkerboards of 1px, 2px and 4px cells drawn at 1:1, beside a
    flat 50% grey patch. Any half-texel sampling offset turns a crisp
    checker into that grey under bilinear, or a shifted checker under
    nearest;

    The wedge exists because one checker cannot tell a fault from a
    limit. A 1px checker photographed as grey means either the
    sampling is wrong or the panel cannot resolve 1px from where the
    camera is standing, and those look identical. Coarser cells
    separate them:

        1px crisp                       -> pass
        1px grey, 2px and 4px crisp     -> real sampling fault
        1px and 2px grey, 4px crisp     -> panel's resolution limit;
                                           the 1px reading is VOID
        all three grey                  -> void, read nothing here

    The flat patch is what a mushed checker looks like, placed next to
    them so the comparison is side by side rather than remembered;
  * the finest checker repeated at the four corners of the 10%
    title-safe box. These have no coarser rung beside them, so they
    carry the fault/limit ambiguity the wedge exists to remove: read
    them ONLY once the centre wedge shows 1px crisp. Until then a
    mushy corner says nothing;
  * 1px solid rules hugging all four canvas edges: a half-pixel
    primitive offset (or overscan) drops one of them;
  * a 2px white cross at the exact canvas center for eyeballing;

  * an INTERLACE PAIR below the wedge: one 1px-tall rule above one
    2px-tall rule, same width and the same x. On a real 480i output the
    1px rule lives in a single field and flickers at 30 Hz while the
    2px rule spans both and sits still.

    Step 8 used to say "expect a stable image" over an example the
    linter had already stripped of every 1px line -- a screen with
    nothing that could shimmer, confirmed not to shimmer. The pair
    gives the step something that must move:

        thin flickers, thick steady  -> interlaced, as expected
        neither flickers             -> progressive output, or the
                                        panel is deinterlacing; this
                                        cell can say nothing, VOID
        both flicker                 -> not field structure; suspect
                                        the framebuffer height or sync

    No photograph can capture this. Step 8 is an operator report by
    design rather than by omission, and the thick rule is what stops
    "nothing moved" from being both the pass and the void.

Compare the emulator/hardware frame against the previewer render of
this same blob (tools/framediff.py); the checker regions should match
essentially exactly.

usage: python3 tools/make_testcard.py [out.uib] [--preview out.png]
       python3 tools/make_testcard.py --self-test
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages", "baker"))

from ps2ui_bake import gs  # noqa: E402
from ps2ui_bake.quads import (  # noqa: E402
    BakedTexture, DrawRecord, OP_QUAD, OP_TEXQUAD, STATE_ALWAYS, FOCUS_NONE,
)
from ps2ui_bake.uib import write_uib, read_uib  # noqa: E402

CANVAS_W, CANVAS_H = 640, 448
CHECKER = 64  # texture side, in texels

# Cell sizes in the wedge, finest first. 1 is the test; 2 and 4 are
# what separate a sampling fault from a panel that cannot resolve the
# fine one. The average of any of them is the same 50% grey, which is
# exactly why a mushed checker is indistinguishable from the flat patch
# and why the flat patch is worth drawing.
WEDGE = (1, 2, 4)
MUSH = (128, 128, 128)

# Step 8's pair. 200 is wide enough to read from a couch and narrow
# enough to stay inside the title-safe box; y sits clear of the wedge.
INTERLACE_W = 200
INTERLACE_Y = 300


def checker_texture(cell: int) -> BakedTexture:
    pixels = []
    for y in range(CHECKER):
        for x in range(CHECKER):
            v = 255 if ((x // cell) + (y // cell)) % 2 == 0 else 0
            pixels.append((v, v, v, 255))
    return BakedTexture(gs.PSMCT32, CHECKER, CHECKER,
                        None, gs.encode_psmct32(pixels))


def solid(x, y, w, h, rgb):
    return DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, x, y, w, h,
                      (rgb[0], rgb[1], rgb[2], 0x80))


def checker_quad(x, y, tex=0):
    # Identity tint in the modulate domain; 1:1 texel-to-pixel mapping.
    return DrawRecord(OP_TEXQUAD, STATE_ALWAYS, FOCUS_NONE,
                      x, y, CHECKER, CHECKER, (0x80, 0x80, 0x80, 0x80),
                      tex, 0, 0, CHECKER, CHECKER)


def build_records():
    records = [solid(0, 0, CANVAS_W, CANVAS_H, (10, 14, 26))]

    # Edge rules (1px, deliberately outside the CRT linter's blessing —
    # this card is for finding edges, not for shipping).
    records += [
        solid(0, 0, CANVAS_W, 1, (255, 0, 0)),                # top: red
        solid(0, CANVAS_H - 1, CANVAS_W, 1, (0, 255, 0)),     # bottom: green
        solid(0, 0, 1, CANVAS_H, (0, 128, 255)),              # left: blue
        solid(CANVAS_W - 1, 0, 1, CANVAS_H, (255, 255, 0)),   # right: yellow
    ]

    cx, cy = CANVAS_W // 2, CANVAS_H // 2

    # The wedge: 1px, 2px, 4px, then flat grey, centred as one row.
    # A flat patch at BOTH ends. One patch sat beside the 4px rung --
    # the one least likely to mush -- and 216px from the 1px rung whose
    # mushing is actually being judged. Finest-first is right for
    # reading the wedge as a ramp, but it put the reference where it was
    # least needed. Two costs one quad and puts one against each end.
    gap = 8
    cols = 1 + len(WEDGE) + 1
    span = cols * CHECKER + gap * (cols - 1)
    wx = cx - span // 2
    wy = cy - CHECKER // 2
    step = CHECKER + gap
    records.append(solid(wx, wy, CHECKER, CHECKER, MUSH))
    for i, _cell in enumerate(WEDGE):
        records.append(checker_quad(wx + (i + 1) * step, wy, tex=i))
    records.append(solid(wx + (len(WEDGE) + 1) * step, wy,
                         CHECKER, CHECKER, MUSH))

    # 64 is the 10% title-safe inset the linter and the rest of bring-up
    # use. It was 32 -- 5% -- while the docstring called it "the four
    # corners of the safe area", so these sat outside the box they claim
    # to mark, in the region where CRT focus and convergence are worst
    # and overscan crops first. A mushy corner there was more likely to
    # be the panel than the centre checker ever was, with nothing beside
    # it to say so.
    inset = 64
    for x, y in (
        (inset, inset),
        (CANVAS_W - inset - CHECKER, inset),
        (inset, CANVAS_H - inset - CHECKER),
        (CANVAS_W - inset - CHECKER, CANVAS_H - inset - CHECKER),
    ):
        records.append(checker_quad(x, y, tex=0))

    records += [
        solid(cx - 16, cy - 1, 32, 2, (255, 255, 255)),
        solid(cx - 1, cy - 16, 2, 32, (255, 255, 255)),
    ]

    # Interlace pair (step 8). Same width, same x, adjacent: only the
    # height differs, so only field structure can make them behave
    # differently.
    records += [
        solid(cx - INTERLACE_W // 2, INTERLACE_Y, INTERLACE_W, 1,
              (255, 255, 255)),
        solid(cx - INTERLACE_W // 2, INTERLACE_Y + 20, INTERLACE_W, 2,
              (255, 255, 255)),
    ]
    return records


def self_test() -> int:
    """Assert the card still tests what its reading table claims.

    Nothing else validates this file. It is generated, not committed,
    so there is no screenshot to drift against and no check.py to catch
    a construction that has quietly stopped meaning anything.

    The property most worth fencing is the 1:1 mapping. A wedge quad
    drawn at any size other than its UV span makes the GS resample, and
    a resampled checker mushes for reasons that have nothing to do with
    texel centres -- a false fault, reported confidently, on correct
    hardware. That is the shape of bug this bring-up work has turned up
    nine times, so it gets a test rather than a comment.
    """
    failures = []

    def check(ok, label):
        print(f"{'ok' if ok else 'not ok'} - {label}")
        if not ok:
            failures.append(label)

    texes = [checker_texture(c) for c in WEDGE]
    for cell, tex in zip(WEDGE, texes):
        # Red channel straight out of the encoded texels. There was a
        # hasattr() probe for a gs.decode_psmct32 here; no such function
        # exists, so only this branch ever ran -- and adding one would
        # have fed RGBA tuples into arithmetic expecting ints and
        # crashed the self-test. A defensive branch whose only reachable
        # effect is to break the thing it guards.
        px = [tex.data[i] for i in range(0, len(tex.data), 4)]
        vals = sorted(set(px))
        check(vals == [0, 255], f"{cell}px checker is pure black and white ({vals})")
        mean = sum(px) / len(px)
        check(abs(mean - 127.5) <= 1.0,
              f"{cell}px checker averages {mean:.1f}, so mushing it lands on "
              f"the flat patch and the comparison means something")

    records = build_records()
    quads = [r for r in records if r.op == OP_TEXQUAD]
    check(len(quads) == len(WEDGE) + 4,
          f"{len(WEDGE)} wedge quads plus 4 corners ({len(quads)})")
    one_to_one = [r for r in quads
                  if r.w == r.u1 - r.u0 and r.h == r.v1 - r.v0]
    check(len(one_to_one) == len(quads),
          f"every checker is drawn 1:1, so nothing mushes from resampling "
          f"({len(one_to_one)}/{len(quads)})")

    # Cell SIZES, not texture indices. Checking `used == range(len(WEDGE))`
    # passed with WEDGE = (1, 1, 4): three textures, three indices, and a
    # wedge that no longer separates a fault from a panel limit because
    # two of its rungs are the same. The indices are an implementation
    # detail; the sizes are the instrument.
    check(len(set(WEDGE)) == len(WEDGE) and list(WEDGE) == sorted(WEDGE),
          f"the wedge is distinct sizes, finest first ({WEDGE})")
    check(WEDGE[0] == 1,
          f"and starts at 1px, which is the size step 6 is about "
          f"({WEDGE[0]}px)")

    # The flat patch has to BE the checker average, computed from the
    # checker. Searching records for MUSH and asserting it equals MUSH
    # is a tautology -- it passed with the patch recoloured to a red
    # nobody could confuse with mush, which is the entire point of it.
    #
    # From WEDGE[0] explicitly. This used to reuse `px` after the loop,
    # which is whichever rung iteration happened to end on; it worked
    # only because all three average the same, so the assertion's stated
    # intent and its actual subject had drifted apart silently.
    finest = checker_texture(WEDGE[0])
    fine_px = [finest.data[i] for i in range(0, len(finest.data), 4)]
    want = round(sum(fine_px) / len(fine_px))
    flat = [r for r in records
            if r.op == OP_QUAD and r.w == CHECKER and r.h == CHECKER
            and len(set(r.rgba[:3])) == 1]
    # The edge rules are the second instrument on this card and they
    # test a different fault -- a half-pixel PRIMITIVE offset, not a
    # half-texel UV one. A rewrite of bringup.md dropped them from the
    # procedure entirely: the card still drew them, the operator was no
    # longer told to look, and the failure reading was gone. An
    # instrument nobody is told to read is in the same category as one
    # that cannot fail, so the count is fenced here.
    rules = [r for r in records if r.op == OP_QUAD
             and (r.w == 1 or r.h == 1)
             and len(set(r.rgba[:3])) > 1]
    check(len(rules) == 4,
          f"four colour-coded edge rules, one per side ({len(rules)})")
    check(len({r.rgba[:3] for r in rules}) == 4,
          "each a different colour, so a missing one names its side")

    # Step 8's pair. Same width and x, adjacent, differing only in
    # height -- if anything else about them differs, "the thin one
    # moved" stops being attributable to field structure.
    pair = sorted((r for r in records
                   if r.op == OP_QUAD and r.w == INTERLACE_W),
                  key=lambda r: r.h)
    check(len(pair) == 2, f"an interlace pair below the wedge ({len(pair)})")
    if len(pair) == 2:
        thin, thick = pair
        check((thin.h, thick.h) == (1, 2),
              f"one 1px rule and one 2px rule ({thin.h}px, {thick.h}px)")
        check(thin.x == thick.x and thin.w == thick.w,
              "at the same x and width, so only height can explain a "
              "difference in behaviour")
        check(thin.rgba[:3] == thick.rgba[:3],
              "and the same colour, so brightness cannot either")

    check(len(flat) == 2,
          f"a flat reference at each end of the wedge ({len(flat)})")
    for f in flat:
        check(abs(f.rgba[0] - want) <= 1,
              f"and it is the colour a mushed checker becomes "
              f"({f.rgba[0]} vs {want})")

    print(f"{'PASS' if not failures else 'FAIL'}: "
          f"{len(failures)} failure(s)")
    return 1 if failures else 0


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if "--self-test" in argv:
        return self_test()
    out = argv[0] if argv and not argv[0].startswith("--") else "testcard.uib"
    write_uib(out, {"w": CANVAS_W, "h": CANVAS_H}, build_records(),
              [checker_texture(c) for c in WEDGE], [], [], None)
    print(f"make_testcard: -> {out}", file=sys.stderr)

    if "--preview" in argv:
        from ps2ui_bake import preview
        png = argv[argv.index("--preview") + 1]
        preview.render(read_uib(out)).save(png)
        print(f"make_testcard: preview -> {png}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
