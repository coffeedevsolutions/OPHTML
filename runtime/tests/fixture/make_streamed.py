#!/usr/bin/env python3
"""Build the streamed-texture fixture for the runtime suite.

Written directly against write_uib rather than through HTML, because
authoring a streamed slot from markup is a separate change (Phase 1
item §3, authoring half) and the runtime half needs a blob to test
against first. Everything here is the minimum that makes the streamed
path readable:

  tex 0  BAKED    16x16 CT32, named "logo"  -- a named baked texture, so
                                              the name lookup has to
                                              tell the kinds apart
  tex 1  STREAMED  8x8  CT32, named "cover" -- reservation 8*8*4 = 256
  tex 2  BAKED    16x16 CT32, unnamed       -- the anonymous majority

Two TEXQUADs draw the baked and the streamed one, so a frame can be
counted before and after the slot is filled.

THE BAKED TEXTURES ARE 16x16 FOR A REASON. They were 4x4, which made
the blob smaller than the streamed entry's 256-byte reservation -- and
that let "a texture with an unknown kind is refused" pass while the
kind check was deleted, because an unknown kind falls through to the
baked path and the bounds check caught it by accident. A fixture has
to be big enough for the check under test to be the one that fires.

There is also a font, pointing at the baked atlas. Nothing draws text
with it; it exists so "no font points at a streamed texture" has a
font to be wrong about.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "packages", "baker"))

from ps2ui_bake import gs                                    # noqa: E402
from ps2ui_bake.quads import DrawRecord, BakedTexture, OP_TEXQUAD  # noqa: E402
from ps2ui_bake.uib import TEXKIND_STREAMED, write_uib       # noqa: E402

COVER_W = COVER_H = 8
COVER_BYTES = COVER_W * COVER_H * 4     # CT32


def main(out):
    textures = [
        BakedTexture(gs.PSMCT32, 16, 16, None, bytes(16 * 16 * 4), name="logo"),
        BakedTexture(gs.PSMCT32, COVER_W, COVER_H, None, b"",
                     kind=TEXKIND_STREAMED, name="cover",
                     reservation=COVER_BYTES),
        BakedTexture(gs.PSMCT32, 16, 16, None, bytes(16 * 16 * 4)),
    ]
    fonts = [{
        "tex": 0, "size": 8, "weight": 400, "ascent": 6, "line_height": 10,
        "glyphs": [{"codepoint": ord("A"), "u": 0, "v": 0, "w": 4, "h": 6,
                    "bearing_x": 0, "bearing_y": 0, "advance": 5}],
    }]
    records = [
        DrawRecord(OP_TEXQUAD, 0, 0xFFFF, 10, 10, 16, 16, (128, 128, 128, 128),
                   tex=0, u0=0, v0=0, u1=16, v1=16),
        DrawRecord(OP_TEXQUAD, 0, 0xFFFF, 20, 20, COVER_W, COVER_H,
                   (128, 128, 128, 128),
                   tex=1, u0=0, v0=0, u1=COVER_W, v1=COVER_H),
    ]
    write_uib(out, {"w": 640, "h": 448}, records, textures, [], [], None,
              fonts=fonts)
    print(f"make_streamed: {out}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "streamed.uib")
