#!/usr/bin/env python3
"""Frame comparison for emulator/hardware verification (backlog F1).

Compares a captured frame against the previewer's ground-truth render
with tolerances tuned for emulator output: global RMSE for overall
drift (gamma, dithering) and worst-tile RMSE so a small-but-wrong
region (a shifted checker, one mistinted panel) cannot hide inside a
good global average.

usage:
  python3 tools/framediff.py expected.png actual.png
      [--rmse 6.0] [--tile-rmse 24.0] [--tile 32] [--out diff.png]
  python3 tools/framediff.py --self-test

Exit code 0 = within tolerance, 1 = differs, 2 = usage/size mismatch.
"""

import argparse
import sys

from PIL import Image, ImageChops, ImageStat


def rmse(a: Image.Image, b: Image.Image) -> float:
    # ImageStat.sum2 is the sum of squares, computed in C. The
    # list-of-pixels form this replaced used Image.getdata(), which
    # Pillow deprecates for removal in 14 -- and CI installs Pillow
    # unpinned, so that is a warning in every log today and a break
    # on some future runner.
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    st = ImageStat.Stat(diff)
    n = diff.size[0] * diff.size[1] * 3
    return (sum(st.sum2) / n) ** 0.5


def worst_tile(a: Image.Image, b: Image.Image, tile: int):
    worst = 0.0
    where = (0, 0)
    for ty in range(0, a.height, tile):
        for tx in range(0, a.width, tile):
            box = (tx, ty, min(tx + tile, a.width), min(ty + tile, a.height))
            r = rmse(a.crop(box), b.crop(box))
            if r > worst:
                worst, where = r, (tx, ty)
    return worst, where


def describe(label: str, img: Image.Image, top: int = 6) -> float:
    """Print a numeric fingerprint of an image; return the top colour's
    share of it.

    An RMSE says two frames differ; it never says how. When the capture
    lives on a CI runner and nobody can open it, the palette is what
    identifies the picture: this UI is flat colour over a dark ground,
    so its dominant colours *are* its stylesheet. A frame whose top
    colour is the canvas background at ~50% is our screen; one that is
    black at 100% never drew; one full of greys is somebody else's
    window.

    Call this on the image as captured. Fingerprinting a resized copy
    would report the size it was scaled *to*, which is the one fact a
    bad capture most needs to tell you, and would smear flat colours
    into interpolated neighbours besides.

    Palettes are only this legible on a digital capture of a CT32
    target: gsKit dithers CT16 framebuffers, and composite video smears
    saturated colours across dozens of neighbours. Either turns a top-N
    listing into noise.
    """
    rgb = img.convert("RGB")
    n = rgb.width * rgb.height
    st = ImageStat.Stat(rgb)
    print(f"  {label}: {rgb.width}x{rgb.height} "
          f"mean rgb({st.mean[0]:.1f}, {st.mean[1]:.1f}, {st.mean[2]:.1f}) "
          f"sd({st.stddev[0]:.1f}, {st.stddev[1]:.1f}, {st.stddev[2]:.1f})")
    # getcolors returns (count, color) pairs, so plain descending sort
    # already ranks by frequency.
    ranked = sorted(rgb.getcolors(maxcolors=n) or [], reverse=True)
    for count, color in ranked[:top]:
        print(f"    {100.0 * count / n:5.1f}%  "
              f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}")
    return 100.0 * ranked[0][0] / n if ranked else 0.0


# A frame this uniform is not evidence about a renderer. It is what a
# program that never reached a draw call looks like, and what an
# emulator window that never got a frame looks like.
UNIFORM_PCT = 99.0


def stats_only(path: str, top: int = 6) -> int:
    """One image, one fingerprint, no verdict.

    Comparing a file with itself printed `-> OK` under a step asking
    whether anything drew at all, which reads as a pass no matter what
    the frame contains.
    """
    img = Image.open(path)
    print(f"framediff: fingerprint of {path}")
    share = describe("frame", img, top)
    if share >= UNIFORM_PCT:
        print(f"  NOTE: {share:.1f}% of this frame is one colour. That is "
              f"ambiguous: it may mean nothing drew, or that the program "
              f"never booted far enough to draw. Check its log before "
              f"reading it as a verdict about the renderer.")
    return 0


def compare(expected_path, actual_path, rmse_tol, tile_tol, tile, out=None,
            stats=False):
    exp = Image.open(expected_path).convert("RGB")
    act = Image.open(actual_path).convert("RGB")

    # Fingerprint before any resize. The size of what actually came back
    # is the most useful thing a bad capture can report.
    if stats:
        print("framediff: fingerprints")
        describe("expected", exp)
        describe("actual  ", act)

    if exp.size != act.size:
        # Emulators often capture at display resolution; scale to match
        # the expected frame before judging.
        print(f"framediff: actual is {act.width}x{act.height}, resizing to "
              f"{exp.width}x{exp.height} to compare")
        act = act.resize(exp.size, Image.BILINEAR)

    global_rmse = rmse(exp, act)
    tile_rmse, at = worst_tile(exp, act, tile)

    if out:
        diff = ImageChops.difference(exp, act)
        diff.point(lambda v: min(v * 4, 255)).save(out)

    ok = global_rmse <= rmse_tol and tile_rmse <= tile_tol
    print(f"framediff: global RMSE {global_rmse:.2f} (tol {rmse_tol}), "
          f"worst {tile}px tile RMSE {tile_rmse:.2f} at {at} (tol {tile_tol}) "
          f"-> {'OK' if ok else 'DIFFERS'}")
    return ok


def self_test() -> int:
    """Prove the tool passes identity and fails a real difference,
    using synthetic images so the test needs no baked artifacts."""
    base = Image.new("RGB", (64, 64), (10, 14, 26))
    for x in range(0, 64, 2):
        for y in range(0, 64, 2):
            base.putpixel((x, y), (200, 200, 200))
    same = base.copy()
    shifted = Image.new("RGB", (64, 64), (10, 14, 26))
    shifted.paste(base.crop((0, 0, 63, 64)), (1, 0))  # 1px shift = checker kill

    ok_same = rmse(base, same) == 0.0
    r_shift = rmse(base, shifted)
    tile_shift, _ = worst_tile(base, shifted, 32)
    ok_shift = r_shift > 6.0 and tile_shift > 24.0

    # The fingerprint is a diagnostic others will read a failure through,
    # so it gets checked too: 3 in every 4 pixels of `base` are the
    # background, and that is what it must lead with.
    import io as _io
    buf = _io.StringIO()
    stdout, sys.stdout = sys.stdout, buf
    try:
        describe("t", base, top=1)
    finally:
        sys.stdout = stdout
    line = buf.getvalue()
    ok_desc = "#0a0e1a" in line and "75.0%" in line

    # A capture that comes back the wrong size must say so. This is the
    # regression d8b79ec fixed, and fingerprinting the resized copy made
    # the diagnostic blind to it.
    import os as _os, tempfile as _tf
    with _tf.TemporaryDirectory() as td:
        big = _os.path.join(td, "big.png")
        small = _os.path.join(td, "small.png")
        base.save(small)
        base.resize((128, 128), Image.NEAREST).save(big)
        buf2 = _io.StringIO()
        stdout, sys.stdout = sys.stdout, buf2
        try:
            compare(small, big, 1e9, 1e9, 32, None, True)
        finally:
            sys.stdout = stdout
        out2 = buf2.getvalue()
    ok_size = "128x128" in out2 and "resizing to 64x64" in out2

    # A uniform frame is ambiguous and must be flagged rather than read
    # as a verdict about the renderer.
    with _tf.TemporaryDirectory() as td:
        flat = _os.path.join(td, "flat.png")
        Image.new("RGB", (32, 32), (0, 0, 0)).save(flat)
        buf3 = _io.StringIO()
        stdout, sys.stdout = sys.stdout, buf3
        try:
            stats_only(flat)
        finally:
            sys.stdout = stdout
        out3 = buf3.getvalue()
    ok_uniform = "NOTE" in out3 and "100.0%" in out3

    print(f"framediff self-test: identity RMSE 0.0 ({'ok' if ok_same else 'FAIL'}), "
          f"1px-shift RMSE {r_shift:.1f} / tile {tile_shift:.1f} "
          f"({'ok' if ok_shift else 'FAIL'}), "
          f"fingerprint names the dominant colour ({'ok' if ok_desc else 'FAIL'}), "
          f"reports a wrong capture size ({'ok' if ok_size else 'FAIL'}), "
          f"flags a uniform frame ({'ok' if ok_uniform else 'FAIL'})")
    return 0 if all((ok_same, ok_shift, ok_desc, ok_size, ok_uniform)) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="framediff")
    ap.add_argument("expected", nargs="?")
    ap.add_argument("actual", nargs="?")
    ap.add_argument("--rmse", type=float, default=6.0)
    ap.add_argument("--tile-rmse", type=float, default=24.0)
    ap.add_argument("--tile", type=int, default=32)
    ap.add_argument("--out", default=None, help="write an amplified diff PNG")
    ap.add_argument("--stats", action="store_true",
                    help="print a colour fingerprint of both frames, so a "
                         "capture nobody can open still identifies itself")
    ap.add_argument("--stats-only", action="store_true",
                    help="fingerprint a single image and print no verdict")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.stats_only:
        if not args.expected:
            ap.print_usage(sys.stderr)
            return 2
        return stats_only(args.expected)
    if not args.expected or not args.actual:
        ap.print_usage(sys.stderr)
        return 2
    return 0 if compare(args.expected, args.actual, args.rmse,
                        args.tile_rmse, args.tile, args.out,
                        args.stats) else 1


if __name__ == "__main__":
    raise SystemExit(main())
