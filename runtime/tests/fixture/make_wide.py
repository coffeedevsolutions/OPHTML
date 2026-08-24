#!/usr/bin/env python3
"""Blobs whose table counts sit past the ceilings that used to exist.

Two fixtures, and the second is the reason the first is not enough.

`wide.uib` -- 200 slots, 40 textures and 12 screens, each past a
number ps2ui.h used to refuse (16, 32, 8). It is the "the obstacle is
actually gone" fixture: it has to load, and every slot has to be
addressable, or the ceiling was removed in the header and left
standing somewhere else. 200 is not arbitrary: the UC-3 scoping
fixture measures 28 slots on one OPL-class screen and 121 across the
environment, so a library at real scale lands in this range.

`huge.uib` -- 65535 slots at capacity 65535, the largest arena a
well-formed header can legally demand. Every count in the header is a
uint16 and so is capacity, so this blob asks for 65535 * 65536 bytes
of slot text: 0xFFFF0000, and the rest of the carve pushes the total
past 4 GiB. That is the number a 32-bit size_t cannot hold, which is
what the EE has. Nothing about this blob is malformed -- that is the
point. The ceilings used to make it unreachable as a side effect of
refusing 17 slots; with them gone, the arena arithmetic has to refuse
it on its own terms.

The file is ~2 MB, which is why it is generated into build/ rather
than committed. Its slot table is the bulk; there is no other way to
reach the boundary, since capacity cannot exceed 65535.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "packages", "baker"))

from ps2ui_bake import gs                                          # noqa: E402
from ps2ui_bake.quads import DrawRecord, BakedTexture, OP_QUAD     # noqa: E402
from ps2ui_bake.uib import write_uib                               # noqa: E402

WIDE_SLOTS = 200
WIDE_TEX = 40
WIDE_SCREENS = 12

# uint16 fields, both of them. This is the ceiling the format itself
# imposes, and the only one left.
MAX_COUNT = 0xFFFF
MAX_CAP = 0xFFFF


def _font(tex=0):
    return {"tex": tex, "size": 8, "weight": 400, "ascent": 6,
            "line_height": 10,
            "glyphs": [{"codepoint": ord("A"), "u": 0, "v": 0, "w": 4, "h": 6,
                        "bearing_x": 0, "bearing_y": 0, "advance": 5}]}


def _slot(i, capacity):
    return {"name": f"s{i}", "placeholder": f"p{i}", "x": 0, "text_y": 0,
            "w": 64, "font": 0, "align": 0, "ellipsis": False,
            "capacity": capacity, "focus": 0xFFFF,
            "color_base": (128, 128, 128, 128),
            "color_focus": (128, 128, 128, 128)}


def wide(out):
    """Past every old ceiling, and small enough to actually load."""
    textures = [BakedTexture(gs.PSMCT32, 16, 16, None, bytes(16 * 16 * 4))
                for _ in range(WIDE_TEX)]
    slots = [_slot(i, 32) for i in range(WIDE_SLOTS)]
    # One drawn quad per screen, so every screen has something to own
    # and screen_set has a real target rather than an empty range.
    records = [DrawRecord(OP_QUAD, 0, 0xFFFF, 4 * i, 4 * i, 8, 8,
                          (32, 32, 32, 255))
               for i in range(WIDE_SCREENS)]
    per = WIDE_SLOTS // WIDE_SCREENS
    screens = []
    for s in range(WIDE_SCREENS):
        first = s * per
        count = (WIDE_SLOTS - first) if s == WIDE_SCREENS - 1 else per
        screens.append({"name": f"screen{s}", "cmd_first": s, "cmd_count": 1,
                        "focus_first": 0, "focus_count": 0,
                        "slot_first": first, "slot_count": count,
                        "initial": None})
    write_uib(out, {"w": 640, "h": 448}, records, textures, [], [], None,
              fonts=[_font()], slots=slots, screens=screens)
    return len(slots), len(textures), len(screens)


def huge(out):
    """The largest arena a legal header can ask for."""
    textures = [BakedTexture(gs.PSMCT32, 16, 16, None, bytes(16 * 16 * 4))]
    slots = [_slot(i, MAX_CAP) for i in range(MAX_COUNT)]
    records = [DrawRecord(OP_QUAD, 0, 0xFFFF, 0, 0, 8, 8, (32, 32, 32, 255))]
    write_uib(out, {"w": 640, "h": 448}, records, textures, [], [], None,
              fonts=[_font()], slots=slots)
    # The number the runtime must arrive at, computed here from the same
    # rules and NOT from the runtime's own header -- two implementations
    # of one layout, which is the only way this can be evidence.
    return (MAX_COUNT * (MAX_CAP + 1)), len(slots)


def main(argv):
    if len(argv) != 3:
        print("usage: make_wide.py <wide.uib> <huge.uib>", file=sys.stderr)
        return 2
    n_sl, n_tx, n_sc = wide(argv[1])
    text, n_huge = huge(argv[2])
    print(f"make_wide: {argv[1]} ({n_sl} slots, {n_tx} textures, "
          f"{n_sc} screens)", file=sys.stderr)
    print(f"make_wide: {argv[2]} ({n_huge} slots, {text} bytes of slot text "
          f"= {text / (1 << 30):.2f} GiB)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
