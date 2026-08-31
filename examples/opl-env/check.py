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
import re
import sys

from ps2ui_bake.quads import OP_QUAD, OP_TEXQUAD
from ps2ui_bake.uib import _CMD, _HEADER, read_uib
from ps2ui_bake import pen
from ps2ui_bake.quads import TEXKIND_STREAMED

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


# ---------------------------------------------------------------- readout

DRIVER_C = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "runtime", "sample", "main.c")


def readout_formats():
    """The driver's telemetry format strings, read from the driver.

    Not a copy of them. A list maintained here would go stale exactly
    when it matters -- someone adds a field, the line overflows, and
    the check that exists to catch that is still measuring yesterday's
    line. So the subject is main.c itself: every string literal inside
    a sprintf whose destination is the `telem` buffer, across all of
    its build arms.
    """
    src = open(DRIVER_C, encoding="utf-8").read()
    out = []
    for call in re.findall(r"sprintf\s*\(\s*telem\s*,(.*?)\);", src, re.S):
        # Strip comments before hunting literals: the surrounding prose
        # quotes field names in "..." and would otherwise be measured.
        call = re.sub(r"/\*.*?\*/", "", call, flags=re.S)
        for lit in re.findall(r'"((?:[^"\\]|\\.)*)"', call):
            out.append(lit)
    return out


_FIELD = re.compile(r"([A-Za-z^@]*)(%l?u(?:\.%02l?u)?|%s)")


def widest(fmt, values):
    """The widest string a format can produce.

    Every conversion is named by the letters in front of it -- `c%lu`,
    `up%u`, `m%lu@%lu` -- and each name gets its widest value from
    `values`. An UNKNOWN name is not skipped and not guessed: it comes
    back in the returned list of misses and fails the check, because a
    new field whose ceiling nobody stated is precisely the field that
    overflows the line.
    """
    miss = []

    def sub(m):
        name = m.group(1)
        if name not in values:
            miss.append(name)
            return m.group(0)
        # The NAME STAYS. Dropping it was this function's first bug and
        # it made every line measure short by one letter per field --
        # the check passed, on a string the driver never prints.
        return name + values[name]

    return _FIELD.sub(sub, fmt), miss


def widest_tag(u):
    """The longest build tag the driver can prefix to line 1.

    Derived, not copied: the tags are string literals in main.c and the
    cycling arm builds its own from a screen name, so the ceiling is
    the widest literal with the blob's longest screen name substituted.
    A new arm with a longer tag then moves this number by itself, which
    is the property the whole ceiling table is built on.
    """
    src = open(DRIVER_C, encoding="utf-8").read()
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    lits = re.findall(r'(?:strcpy|sprintf)\s*\(\s*tag\s*,\s*"([^"]*)"', src)
    # WIDEST IN PIXELS, NOT IN CHARACTERS, because the ceiling feeds a
    # pixel check. Four screen names are seven characters and they are
    # not the same width: [c:confirm] is 64px where [c:landing] is 62.
    # Picking by len understated the worst case by 2px in the one
    # figure whose whole subject is fit.
    font = u.fonts[0]
    longest_screen = max(
        (s_["name"] for s_ in u.screens),
        key=lambda n: pen.slot_width("[c:%s] " % n,
                                     font["glyphs"], font["kerns"]))
    widest = ""
    for lit in lits:
        text = lit.replace("%s", longest_screen)
        if len(text) > len(widest):
            widest = text
    return widest


def driver_const(name):
    """A #define'd integer from the driver, so a ceiling that depends on
    one is not a number copied into this file."""
    src = open(DRIVER_C, encoding="utf-8").read()
    m = re.search(r"^#define\s+%s\s+(\d+)\s*$" % re.escape(name),
                  src, re.M)
    if not m:
        raise SystemExit("check.py: %s is no longer a plain #define in "
                         "main.c, so the readout ceiling that depends on "
                         "it cannot be derived" % name)
    return int(m.group(1))


def pen_width(text, font, letter_spacing):
    """The blob-driven pen, from the baker rather than from here.

    This used to be a private copy of slot_measure's accumulation --
    the FOURTH implementation of that arithmetic in the tree, and the
    only one making a load-bearing claim (that the readout fits) on
    numbers nothing checked. See ps2ui_bake.pen for why it moved."""
    return pen.slot_width(text, font["glyphs"], font["kerns"],
                          letter_spacing)


def field_ceilings(u, scr):
    """The widest value each readout field can reach, on THIS screen.

    Derived where the blob knows the answer, stated where it does not.
    A ceiling that is merely large would make the check reject designs
    that cannot actually overflow -- 99999 commands on a screen whose
    table holds 694 is not a worst case, it is a different program.

      counts   bounded by the screen: cmds by its entry in the screen
               table, slot glyphs by the summed capacities of its own
               slots (the driver cannot write more than it declared),
               prims by their sum. Per screen and not blob-wide,
               because a readout only ever shows the numbers of the
               screen it is drawn on.
      ms       a frame period; the clock is per-field, so 16.68.
      run      m, n and the two @ indices count frames. 99999 is 28
               minutes at 60Hz, longer than any sitting so far.
      up       bytes handed to ps2ui_tex_set in one scroll step. Not a
               blob quantity, so it comes from the driver's own
               constants -- every row of the window re-uploaded at
               once, which is the most one step can move.
    """
    lo, n = scr["slot_first"], scr["slot_count"]
    glyphs = sum(sl["capacity"] for sl in u.slots[lo:lo + n])
    cmds = scr["cmd_count"]
    return {
        # The build tag, whose conversion is %s and whose "name" is
        # therefore the empty prefix in front of it.
        "": widest_tag(u),
        "ee": "16.68", "gs": "16.68", "^": "16.68", "f": "16.68",
        "@": "99999", "m": "99999", "n": "99999",
        "c": str(cmds), "g": str(glyphs), "p": str(cmds + glyphs),
        "u": str(sum(1 for t in u.textures if t.kind == TEXKIND_STREAMED)),
        "up": str(driver_const("OPLENV_ROWS") * driver_const("OPLENV_ART_W")
                  * driver_const("OPLENV_ART_H") * 4),
        "t": str(max(0, len(u.themes) - 1)),
    }


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

    # ---- every screen can report its own cost, and the line fits ----
    #
    # TWO FAILURES, ONE CHECK, because they produce the same photograph.
    # Slots are per-screen: render_slots walks the current screen's slot
    # range, so a readout that exists only on library draws NOTHING on
    # the five other screens P3d's sweep renders -- five points with no
    # numbers on them. And a line that overflows its slot is clipped by
    # the scissor rather than ellipsised, so the last field simply is
    # not there. Either way the bench comes home with a photograph that
    # is missing the number the sitting was for.
    #
    # Measured with the runtime's own pen against the font each slot
    # actually names, so the confirm screen -- 11px in a 256px dialog
    # rather than 14px in a footer, because the scrim has no footer and
    # making one pushed the dialog title out of the title-safe area --
    # is checked on its own terms rather than on library's.
    fmts = readout_formats()
    check(len(fmts) >= 2,
          f"found {len(fmts)} telemetry format string(s) in the driver; "
          f"this check measures what main.c actually prints, and finding "
          f"none means it is measuring nothing")
    # Line 1 carries the timings and goes in -telem; every other arm is
    # a line 2 variant and goes in -telem2.
    #
    # KEYED ON A FIELD THE PREFIX CANNOT MOVE. This read
    # `f.startswith("ee")`, which was true until line 1 gained a build
    # tag and became "%see%lu...". Every format then fell into -telem2,
    # -telem was measured against nothing, and the suite went from 91
    # checks to 79 and passed. Proof the coverage was gone rather than
    # relocated: cutting library-telem's capacity to 12, against a
    # line needing 45, still passed. `ee%lu` survives any prefix.
    lines = {"-telem": [f for f in fmts if "ee%lu" in f],
             "-telem2": [f for f in fmts if "ee%lu" not in f]}
    # AND NEITHER SIDE MAY BE EMPTY. An empty list is not zero
    # failures, it is zero questions asked -- which is exactly how the
    # regression above passed, and the only outward sign was a check
    # count that read as a fact rather than a twelve-check drop.
    for suffix, arms in lines.items():
        check(bool(arms),
              f"line {'1' if suffix == '-telem' else '2'} has at least one "
              f"format to measure; an empty set means the driver's formats "
              f"stopped matching this split and {suffix} is being checked "
              f"against nothing")
    by_name = {sl["name"]: sl for sl in u.slots}
    for scr in u.screens:
        lo, n = scr["slot_first"], scr["slot_count"]
        reachable = {sl["name"] for sl in u.slots[lo:lo + n]}
        ceil = field_ceilings(u, scr)
        for suffix, arms in lines.items():
            name = scr["name"] + suffix
            if not check(name in reachable,
                         f"screen {scr['name']!r} carries its own {name!r}, "
                         f"so the driver can put a readout on it; without one "
                         f"this sweep point photographs no numbers"):
                continue
            sl = by_name[name]
            font = u.fonts[sl["font"]]
            # The two limits are asked SEPARATELY, and of the widest arm
            # under each. They are different limits -- capacity is the
            # buffer, w is the scissor -- and the arm that runs longest
            # in pixels need not be the one that runs longest in bytes,
            # so taking one arm's worst and testing both of its numbers
            # can pass a line that overflows under the other.
            px, ch = [], []
            for fmt in arms:
                text, miss = widest(fmt, ceil)
                if not check(not miss,
                             f"{name}: readout field(s) {sorted(set(miss))} "
                             f"have no stated ceiling, so nothing knows how "
                             f"wide the line can get"):
                    continue
                # THE LABELS ARE PART OF THE LINE. widest()'s first
                # version returned the value without the name in front
                # of it, so every measurement came up one letter per
                # field short -- a passing check on a string the driver
                # never prints. The measured text must still contain
                # every name the format writes.
                labels = [m.group(1) for m in _FIELD.finditer(fmt)
                          if m.group(1)]
                check(all(lb in text for lb in labels),
                      f"{name}: the widest-case line \"{text}\" has lost a "
                      f"field label from {labels}, so it is shorter than "
                      f"anything the driver can print and every limit below "
                      f"is measured against the wrong string")
                px.append((pen_width(text, font, sl["letter_spacing"]), text))
                ch.append((len(text), text))
            if not px:
                continue
            w, wtxt = max(px)
            c, ctxt = max(ch)
            check(w <= sl["w"],
                  f"{name}: widest line \"{wtxt}\" is {w}px of {sl['w']}px; "
                  f"the slot clips rather than ellipsises, so an overflowing "
                  f"line loses its LAST field, which is where the newest "
                  f"number always goes")
            check(c <= sl["capacity"],
                  f"{name}: longest line \"{ctxt}\" is {c} chars of "
                  f"{sl['capacity']}; ps2ui_slot_set truncates at the "
                  f"declared capacity, so the tail is gone before the pen "
                  f"ever sees it")

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
