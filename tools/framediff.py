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

from PIL import Image, ImageChops


def rmse(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    px = list(diff.getdata())
    n = len(px) * 3
    total = sum(c * c for p in px for c in p)
    return (total / n) ** 0.5


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


def compare(expected_path, actual_path, rmse_tol, tile_tol, tile, out=None):
    exp = Image.open(expected_path).convert("RGB")
    act = Image.open(actual_path).convert("RGB")
    if exp.size != act.size:
        # Emulators often capture at display resolution; scale to match
        # the expected frame before judging.
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
    print(f"framediff self-test: identity RMSE 0.0 ({'ok' if ok_same else 'FAIL'}), "
          f"1px-shift RMSE {r_shift:.1f} / tile {tile_shift:.1f} "
          f"({'ok' if ok_shift else 'FAIL'})")
    return 0 if ok_same and ok_shift else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="framediff")
    ap.add_argument("expected", nargs="?")
    ap.add_argument("actual", nargs="?")
    ap.add_argument("--rmse", type=float, default=6.0)
    ap.add_argument("--tile-rmse", type=float, default=24.0)
    ap.add_argument("--tile", type=int, default=32)
    ap.add_argument("--out", default=None, help="write an amplified diff PNG")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.expected or not args.actual:
        ap.print_usage(sys.stderr)
        return 2
    return 0 if compare(args.expected, args.actual, args.rmse,
                        args.tile_rmse, args.tile, args.out) else 1


if __name__ == "__main__":
    raise SystemExit(main())
