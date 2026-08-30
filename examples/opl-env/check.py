#!/usr/bin/env python3
"""Verify the opl-env blob's theming contract, straight off the baked file.

    PYTHONPATH=packages/baker python3 examples/opl-env/check.py build/ui.uib

WHY HERE AND NOT IN THE BAKER'S UNIT SUITE. These two assertions read a
BUILD ARTEFACT, and the unit suite runs before anything is built --
ci.yml bakes this example at line 129 and runs the baker tests at 75.
Putting them there made CI red (correctly: #73's tripwire turned a
missing fixture into a failure instead of a silent skip), and the
obvious fix, hoisting the bake above the suite, is the thing #73
explicitly argued against: with the integration builds running first, a
broken baker is reported by a shell script instead of by the file whose
job it is.

There is a second reason, and it is the sharper one. A test that reads
a build artefact answers a question about WHENEVER THAT ARTEFACT WAS
BAKED, not about the source in front of it. Review found exactly that
while checking this change: sabotaging paint.js and running the suite
reported OK, because the blob on disk was stale. Run from build.sh,
immediately after the bake that produced the bytes, the subject cannot
be stale.

channel6/check.py is the precedent -- the baker checks what it is about
to write, this checks what a loader will actually find.
"""

import os
import sys

from ps2ui_bake.quads import OP_QUAD, OP_TEXQUAD
from ps2ui_bake.uib import _CMD, _HEADER, read_uib

_checks = []


def check(ok: bool, label: str) -> bool:
    _checks.append((bool(ok), label))
    return bool(ok)


def command_tints(path):
    """The tint index each painting command holds.

    Read from the file rather than through read_uib, which resolves
    indices to colours on the way in -- the index is the thing being
    asserted about here, so resolving it away first would leave nothing
    to check.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    h = _HEADER.unpack_from(data, 0)
    n_cmd, off_cmd = h[7], h[12]
    out = set()
    for i in range(n_cmd):
        e = _CMD.unpack_from(data, off_cmd + i * _CMD.size)
        if e[0] in (OP_QUAD, OP_TEXQUAD):
            out.add(e[7])
    return out


def art_tints(path, u):
    """Tint entries used by TEXQUADs whose colour is in their TEXELS.

    Since P3b-6 that is images and only images: glyph atlases and the
    rounded-box coverage patches both carry coverage in the texels and
    take their colour from the tint, so both are identified here by the
    thing that makes them so -- they share the one coverage CLUT.

    Excluded by TEXTURE rather than by value, deliberately. A glyph
    tinted white modulates to (128,128,128,128), which is byte-for-byte
    the identity an image carries; telling those apart by looking at
    the number is impossible, and getting it wrong means either
    freezing a themeable colour or letting a theme multiply a
    photograph.
    """
    cov = {t.clut for i, t in enumerate(u.textures)
           if i in {f["tex"] for f in u.fonts}}
    font_texs = {i for i, t in enumerate(u.textures) if t.clut in cov}
    with open(path, "rb") as fh:
        data = fh.read()
    h = _HEADER.unpack_from(data, 0)
    n_cmd, off_cmd = h[7], h[12]
    out = set()
    for i in range(n_cmd):
        e = _CMD.unpack_from(data, off_cmd + i * _CMD.size)
        if e[0] == OP_TEXQUAD and e[9] not in font_texs:
            out.add(e[7])
    return out


def main(path: str) -> int:
    u = read_uib(path)
    row = u.themes[0]

    # ---- the tint table is role-keyed, and that is visible in it ----
    #
    # #ffffff as text modulates to (128,128,128,128), which is exactly
    # the identity tint the emitter uses on untinted art -- images,
    # since P3b-6 moved the rounded boxes onto coverage masks. A
    # value-keyed table fuses them, and a theme touching --ink-max then
    # tints every image in the environment. Two entries holding the
    # same four bytes is something only role-keying can produce.
    ident = (128, 128, 128, 128)
    check(row.count(ident) == 2,
          f"--ink-max and the untinted-art identity are separate entries "
          f"holding the same bytes ({row.count(ident)} found); one means "
          f"they fused and a theme would tint every image")

    # ---- colour lives in two tables and both key the same way ----
    #
    # This seam has been the gap four times: the design missed slots,
    # v7's tint_focus fence missed them, ps2ui_theme_set's first check
    # missed them, and the first fence written for THIS change could not
    # fail. A slot and a command that carry the same var name are one
    # role and must share one entry. Dropping colorBaseVar/colorFocusVar
    # from paint.js takes this blob from 13 entries to 16.
    cmd = command_tints(path)
    slot = ({s["tint_base"] for s in u.slots}
            | {s["tint_focus"] for s in u.slots})
    shared = cmd & slot
    check(len(shared) >= 4,
          f"{len(shared)} tint entries are shared between slot text and "
          f"commands; fewer than 4 means one side stopped keying on the "
          f"name and a theme would recolour the panels and leave the "
          f"labels baked")

    # ---- and the palette is still a palette ----
    paints = sum(1 for r in u.records if r.op in (OP_QUAD, OP_TEXQUAD))
    check(len(row) * 4 < paints,
          f"{len(row)} tints over {paints} painting commands: naming the "
          f"colours must not stop the palette being a small repeated set, "
          f"which is what makes a theme a table swap")

    # ---- the second row exists, moves, and knows what not to move ----
    #
    # The point of the whole slice, and three separate claims because
    # each fails on its own: one row (the @theme block stopped being
    # parsed), a second row that copies the first (the writer keyed the
    # row on something that does not vary), and a second row that moved
    # the identity tint too.
    check(len(u.themes) == 2,
          f"the blob carries {len(u.themes)} theme rows, expected 2 "
          f"(:root and @theme light)")
    if len(u.themes) == 2:
        base, light = u.themes
        moved = [i for i in range(len(base)) if base[i] != light[i]]
        check(len(moved) == len(base) - 1,
              f"{len(moved)} of {len(base)} entries differ between the two "
              f"themes; every entry but the untinted-art identity should, and "
              f"a row that mostly matches row 0 means the theme's values "
              f"were not carried rather than that the palettes agree")

        # AND THE IDENTITY STAYS IDENTITY. Asked of the ENTRY the art
        # points at, not of the value: two entries hold
        # (128,128,128,128) in row 0 -- --ink-max and the nine-patch
        # identity -- and the whole reason they are two entries is that
        # exactly one of them is allowed to move. Testing the value
        # would either pass with both frozen (--ink-max unthemed) or
        # fail with both moving, and could not tell those apart.
        art = art_tints(path, u)
        check(bool(art) and all(light[i] == ident for i in art),
              f"the {len(art)} entry/entries the premixed art points at "
              f"(images -- since P3b-6 the rounded boxes are coverage, not "
              f"premix) hold the identity in every theme; a theme moving one "
              f"would multiply baked texels by a colour instead of "
              f"recolouring anything")

    print(f"# {path}: {len(row)} tints over {len(u.themes)} theme(s), "
          f"{len(shared)} shared with slots, {paints} painting commands")
    return report()


def report() -> int:
    for i, (ok, label) in enumerate(_checks, 1):
        print(f"{'ok' if ok else 'not ok'} {i} - {label}")
    print(f"1..{len(_checks)}")
    failures = sum(1 for ok, _ in _checks if not ok)
    print(f"{'PASS' if failures == 0 else 'FAIL'}: {len(_checks)} checks, "
          f"{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <ui.uib>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
