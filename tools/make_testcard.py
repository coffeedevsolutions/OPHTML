#!/usr/bin/env python3
"""Build the texel-alignment test card (backlog B3, bring-up step 6).

Writes testcard.uib directly through the baker's Python API — no HTML,
because the point is a hand-controlled texture drawn 1:1:

  * a 64x64 PSMCT32 checkerboard of 1px cells drawn at 1:1 in the
    canvas center: any half-texel sampling offset turns the crisp
    checker into uniform gray mush under bilinear, or a shifted
    checker under nearest;
  * the same checker drawn at the four corners of the safe area;
  * 1px solid rules hugging all four canvas edges: a half-pixel
    primitive offset (or overscan) drops one of them;
  * a 2px white cross at the exact canvas center for eyeballing.

Compare the emulator/hardware frame against the previewer render of
this same blob (tools/framediff.py); the checker regions should match
essentially exactly.

usage: python3 tools/make_testcard.py [out.uib] [--preview out.png]
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
CHECKER = 64  # texture side, 1px cells


def checker_texture() -> BakedTexture:
    pixels = []
    for y in range(CHECKER):
        for x in range(CHECKER):
            v = 255 if (x + y) % 2 == 0 else 0
            pixels.append((v, v, v, 255))
    return BakedTexture(gs.PSMCT32, CHECKER, CHECKER,
                        None, gs.encode_psmct32(pixels))


def solid(x, y, w, h, rgb):
    return DrawRecord(OP_QUAD, STATE_ALWAYS, FOCUS_NONE, x, y, w, h,
                      (rgb[0], rgb[1], rgb[2], 0x80))


def checker_quad(x, y):
    # Identity tint in the modulate domain; 1:1 texel-to-pixel mapping.
    return DrawRecord(OP_TEXQUAD, STATE_ALWAYS, FOCUS_NONE,
                      x, y, CHECKER, CHECKER, (0x80, 0x80, 0x80, 0x80),
                      0, 0, 0, CHECKER, CHECKER)


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
    records.append(checker_quad(cx - CHECKER // 2, cy - CHECKER // 2))
    inset = 32
    for x, y in (
        (inset, inset),
        (CANVAS_W - inset - CHECKER, inset),
        (inset, CANVAS_H - inset - CHECKER),
        (CANVAS_W - inset - CHECKER, CANVAS_H - inset - CHECKER),
    ):
        records.append(checker_quad(x, y))

    records += [
        solid(cx - 16, cy - 1, 32, 2, (255, 255, 255)),
        solid(cx - 1, cy - 16, 2, 32, (255, 255, 255)),
    ]
    return records


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    out = argv[0] if argv and not argv[0].startswith("--") else "testcard.uib"
    write_uib(out, {"w": CANVAS_W, "h": CANVAS_H}, build_records(),
              [checker_texture()], [], [], None)
    print(f"make_testcard: -> {out}", file=sys.stderr)

    if "--preview" in argv:
        from ps2ui_bake import preview
        png = argv[argv.index("--preview") + 1]
        preview.render(read_uib(out)).save(png)
        print(f"make_testcard: preview -> {png}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
