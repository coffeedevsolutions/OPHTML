#!/usr/bin/env python3
"""Build the CSM1 swizzle tile (bring-up step 3).

The CLUT is stored linearly in the .uib and the *runtime* permutes it on
upload (`ps2ui_clut_csm1`), swapping bits 3 and 4 of the palette index.
Step 3 asks whether that permutation agrees with the GS. With a correct
one, index i renders linear[i]; with a wrong one it renders
linear[csm1(i)].

Asking "do the glyphs look garbled" is the failure mode that cost the
step 2 probe three rewrites -- it wants a judgement of appearance. This
tile asks whether a stripe is there.

A straight swap is symmetric and therefore invisible: two regions using
indices 8 and 16 just exchange colours, which looks like a boundary
either way. Break the symmetry with an index the swap does not touch.

    bit 3:  index 0 beside index 8    linear[0]=X linear[8]=X linear[16]=Y
    bit 4:  index 32 beside index 48  linear[32]=X linear[48]=X linear[40]=Y
    calib:  index 1 beside index 2    linear[1]=X linear[2]=Y

Indices 0, 1, 2 have bit3 == bit4 == 0, so the permutation leaves them
where they are. Every X region is therefore flat on correct hardware and
the tile reads:

    [ X X X X X | Y ]     one stripe, hard against the right edge

A bit-3 fault turns region B into Y and a stripe appears at 1/6. A bit-4
fault turns region D into Y and one appears at 3/6. So the tile does not
merely say "wrong" -- the stripe's position names which bit.

The calibration is the last pair. Its two indices carry genuinely
different palette entries, so its boundary is unconditional: no
permutation, right or wrong, can remove it. Without it, "I see no
stripes" and "this cell cannot show me a stripe" are the same
observation and the first two probes prove nothing.

Run from the repo root:

    python3 tools/make_swizzle_tile.py examples/channel6/ui/assets/swizzle.png
"""
import sys

from PIL import Image

# Not used anywhere else in the probe, and far apart in LUMINANCE as
# well as hue -- measured, not assumed.
#
#   Rec.601  54.4 vs 173.4   delta 119
#   Rec.709  60.2 vs 168.6   delta 108
#
# The first pair tried here was #2e7d6b against #d94f2b, which looks
# emphatic and is not: 16.8 apart in Rec.601 and 1.2 in Rec.709, so in
# greyscale they are #636363 against #747474. That claim sat in this
# docstring as a justification while being numerically false, in a repo
# that had already lost a probe revision to exactly that assumption --
# the step 2 ladder, whose rungs a camera flattened to within ten units
# of each other. A stripe that only exists in chroma is a stripe that
# vanishes on a monochrome capture, a badly tinted CRT, or a photograph
# with the saturation crushed.
X = (0x0d, 0x4a, 0x3e)   # dark teal
Y = (0xff, 0x9a, 0x3c)   # bright orange

# (index, colour). The three Y entries are traps: nothing draws them on
# correct hardware except the calibration's.
PALETTE = {
    0: X, 8: X, 16: Y,      # bit 3: 0 <-> 8, trap at 16
    32: X, 48: X, 40: Y,    # bit 4: 32 <-> 48, trap at 40
    1: X, 2: Y,             # calibration, untouched by the permutation
}
REGIONS = [0, 8, 32, 48, 1, 2]

CELL_W = 16
HEIGHT = 20


def build() -> Image.Image:
    w = CELL_W * len(REGIONS)
    img = Image.new("P", (w, HEIGHT))
    flat = [0, 0, 0] * 256
    for idx, rgb in PALETTE.items():
        flat[idx * 3:idx * 3 + 3] = list(rgb)
    img.putpalette(flat)
    for col, idx in enumerate(REGIONS):
        for x in range(col * CELL_W, (col + 1) * CELL_W):
            for y in range(HEIGHT):
                img.putpixel((x, y), idx)
    return img


def main(argv):
    if len(argv) != 2:
        print(f"usage: {argv[0]} <out.png>", file=sys.stderr)
        return 2
    img = build()
    # Bit depth matters: the baker reads mode "P" and takes the indices
    # verbatim, so the file has to actually store index 48 rather than
    # be helpfully re-encoded to a 3-colour palette. bits=8 keeps all
    # 256 entries addressable.
    img.save(argv[1], bits=8)
    print(f"wrote {argv[1]}: {img.size[0]}x{img.size[1]} indexed, "
          f"regions {REGIONS}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
