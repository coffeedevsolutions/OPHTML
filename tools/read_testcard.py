#!/usr/bin/env python3
"""Read the alignment test card's resolution wedge from a capture.

Bring-up step 6 asks whether texels land on pixel centres. The card
answers it by drawing a checkerboard at 1:1 in three cell sizes with a
flat grey patch at each end: a correctly sampled checker is patterned,
and one sampled off-centre averages its two colours into exactly that
grey. So the reading is "patterned or flat", never "what colour is
this" -- the judgement a camera, a panel or a resample cannot corrupt.

That matters here because the emulator capture is not 1:1. Play!
presents at ~1.4x and the capture is scaled back down, so a pixel-wise
diff of this card would measure the resampler. Variance against a
reference measured in the same frame does not.

Geometry is imported from make_testcard, never restated, so a change to
the card moves this reader with it rather than leaving it reading the
wrong rectangles.

  read_testcard.py CAPTURE          read a capture, print a verdict
  read_testcard.py --self-test      prove the reader can fail
"""
import argparse
import sys

from PIL import Image

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from make_testcard import CANVAS_W, CANVAS_H, CHECKER, WEDGE, MUSH  # noqa: E402

GAP = 8

# How far above the flat reference's variation a rung must sit before it
# counts as patterned. The flat patches are a single colour by
# construction, so their spread is entirely capture noise; a real
# checker of any surviving cell size clears it by a wide margin. Set
# from the noise, not from an absolute number, because the noise is a
# property of whatever pipeline produced the capture.
CRISP_RATIO = 4.0

# And an absolute floor, because a ratio alone cannot decide this. When
# every rung has mushed, the flat references and the rungs are the same
# grey, the denominator goes to zero and "infinitely more varied than
# flat" is exactly backwards -- they are identical. The reader's own
# self-test caught that. A surviving checker of any cell size clears
# this comfortably; a black-and-white checker at 1:1 sits near 127.
MIN_CRISP_SD = 8.0

# Above this, the "flat" references are not flat, so nothing in the
# frame is where this reader thinks it is and every rung below is
# meaningless. In units of the 0..255 channel range.
FLAT_SD_MAX = 12.0


def patch_boxes(w, h):
    """The five wedge patches, in capture pixels.

    Mirrors make_testcard.build_records' layout maths rather than
    hardcoding coordinates, and scales to the capture so a frame that
    is not exactly 640x448 still reads.
    """
    cx, cy = CANVAS_W // 2, CANVAS_H // 2
    cols = 1 + len(WEDGE) + 1
    span = cols * CHECKER + GAP * (cols - 1)
    wx = cx - span // 2
    wy = cy - CHECKER // 2
    step = CHECKER + GAP
    sx, sy = w / CANVAS_W, h / CANVAS_H
    out = []
    for i in range(cols):
        x0 = wx + i * step
        # Inset by a fifth of the patch: the capture's scaling softens
        # every edge, and an edge is not what is being measured.
        pad = CHECKER // 5
        box = (x0 + pad, wy + pad, x0 + CHECKER - pad, wy + CHECKER - pad)
        out.append(tuple(int(round(v * s))
                         for v, s in zip(box, (sx, sy, sx, sy))))
    return out


def stats(im, box):
    px = list(im.crop(box).convert("L").getdata())
    n = len(px)
    mean = sum(px) / n
    var = sum((p - mean) ** 2 for p in px) / n
    return mean, var ** 0.5


def read(path, verbose=True):
    im = Image.open(path).convert("RGB")
    boxes = patch_boxes(*im.size)
    measured = [stats(im, b) for b in boxes]
    left, right = measured[0], measured[-1]
    rungs = measured[1:-1]
    flat_sd = max(left[1], right[1])
    lines = []
    ok = True
    void = False

    if verbose:
        lines.append(f"capture {im.size[0]}x{im.size[1]}, "
                     f"wedge {WEDGE}, flat reference {MUSH}")
        lines.append(f"  flat left : mean {left[0]:6.1f}  sd {left[1]:5.2f}")
        lines.append(f"  flat right: mean {right[0]:6.1f}  sd {right[1]:5.2f}")

    # The calibration first: if the flat patches are not flat, the rungs
    # below are noise being read as a verdict.
    if flat_sd > FLAT_SD_MAX:
        void = True
        lines.append(f"VOID: the flat references vary (sd {flat_sd:.2f} > "
                     f"{FLAT_SD_MAX}). This capture is not the card, or not "
                     f"aligned to it -- the rungs below mean nothing.")

    for cell, (mean, sd) in zip(WEDGE, rungs):
        ratio = sd / flat_sd if flat_sd > 0.01 else 0.0
        # Both conditions, never either: the ratio catches a rung that
        # is merely capture noise, the floor catches the case where
        # nothing in the frame varies at all.
        crisp = sd >= MIN_CRISP_SD and sd >= flat_sd * CRISP_RATIO
        if void:
            verdict = "void"
        elif crisp:
            verdict = "CRISP"
        else:
            verdict = "MUSH"
            ok = False
        lines.append(f"  {cell}px rung : mean {mean:6.1f}  sd {sd:5.2f}  "
                     f"({ratio:5.1f}x flat)  {verdict}")

    if not void and not ok:
        lines.append("Some rung mushed. On a 1:1 display that is a half-texel "
                     "sampling offset (bring-up step 6). Through a scaled "
                     "capture the finest rung may simply be below what "
                     "survives the resample -- read the coarser rungs first: "
                     "a mushed 4px rung cannot be blamed on resolution.")
    if verbose:
        print("\n".join(lines))
    return {"void": void, "ok": ok and not void,
            "flat_sd": flat_sd,
            "rungs": {c: v for c, v in zip(WEDGE, [m[1] for m in rungs])}}


def _synth(mush_cells=()):
    """A test card as this reader expects to see one.

    Built here rather than read from a baked artifact: a reader whose
    self-test skips when a file is missing is a test that passes without
    running.
    """
    im = Image.new("RGB", (CANVAS_W, CANVAS_H), (10, 14, 26))
    px = im.load()
    for i, box in enumerate(patch_boxes(CANVAS_W, CANVAS_H)):
        # Undo the reader's inset so the synthetic patch fills the real
        # 64x64 cell, not just the region the reader samples.
        pad = CHECKER // 5
        x0, y0 = box[0] - pad, box[1] - pad
        cell = None if i in (0, len(WEDGE) + 1) else WEDGE[i - 1]
        for y in range(CHECKER):
            for x in range(CHECKER):
                if cell is None or cell in mush_cells:
                    c = MUSH
                else:
                    on = ((x // cell) + (y // cell)) % 2 == 0
                    c = (255, 255, 255) if on else (0, 0, 0)
                px[x0 + x, y0 + y] = c
    return im


def self_test():
    import tempfile
    import os
    fails = []

    def check(cond, label):
        print(("ok   - " if cond else "not ok - ") + label)
        if not cond:
            fails.append(label)

    with tempfile.TemporaryDirectory() as td:
        crisp = os.path.join(td, "crisp.png")
        _synth().save(crisp)
        r = read(crisp, verbose=False)
        check(r["ok"] and not r["void"], "a correct card reads every rung CRISP")

        # The half that matters: a reader that cannot report MUSH would
        # pass this card forever.
        mushed = os.path.join(td, "mush.png")
        _synth(mush_cells=WEDGE).save(mushed)
        r = read(mushed, verbose=False)
        check(not r["ok"] and not r["void"],
              "a card whose checkers averaged to grey reads MUSH, not CRISP")

        # And one rung alone, which is the real step 6 signature: the
        # finest mushes first.
        one = os.path.join(td, "one.png")
        _synth(mush_cells=(WEDGE[0],)).save(one)
        r = read(one, verbose=False)
        check(not r["ok"], f"a mushed {WEDGE[0]}px rung alone still fails")
        check(r["rungs"][WEDGE[-1]] > r["rungs"][WEDGE[0]],
              "and the coarser rungs are still read as patterned")

        # Calibration: a frame whose flat references are not flat must be
        # void rather than a verdict. Noise everywhere is the shape of a
        # capture that missed the card entirely.
        import random
        rnd = random.Random(1)
        noise = _synth()
        p = noise.load()
        for y in range(CANVAS_H):
            for x in range(CANVAS_W):
                v = rnd.randrange(256)
                p[x, y] = (v, v, v)
        npath = os.path.join(td, "noise.png")
        noise.save(npath)
        r = read(npath, verbose=False)
        check(r["void"], "a frame that is not the card reads VOID, not MUSH")

    print(f"read_testcard self-test: {'PASS' if not fails else 'FAIL'}"
          f" ({len(fails)} failure(s))")
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="read-testcard", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("capture", nargs="?", help="captured frame (PNG)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--report-only", action="store_true",
                    help="print the reading but always exit 0")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if not args.capture:
        ap.error("a capture is required unless --self-test")
    r = read(args.capture)
    if args.report_only:
        return 0
    # Void is not a pass and not a failure. Exit 2 keeps it distinct from
    # both, so a caller cannot read "the card could not be read" as "the
    # card was fine".
    return 2 if r["void"] else (0 if r["ok"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())
