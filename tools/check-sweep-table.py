#!/usr/bin/env python3
"""Derive P3d's content-sweep table from the blob and the driver.

WHY THIS EXISTS. The sweep table is the x-axis of the next bench
sitting: `ee = base + k_cmd x cmds + k_glyph x glyphs`, six screens,
and the numbers are written down BEFORE the sitting so it scores a
prediction rather than producing one. It is restated in two documents,
docs/PLAN.md and docs/bench-phase2.md, and nothing re-derived either.

#87 prefixed a build tag to the readout's line 1 -- `[c:library] ` --
so the sweep photographs would document themselves. The tag is slot
text: its glyphs are drawn, counted in `stats.slot_glyphs`, and
reported in `g`, the field the sitting reads. Every row of the
`slot glyphs` column went 10-11 short, and `p` with it, in the same
pull request that added the tag. #87's own text argued the tag is
"a constant across the sweep, absorbed into base" -- it is 10 or 11,
not constant, and either way neither table moved.

The fit barely notices one glyph in 145-387. That is not the point:
this is the column a person reads off a photograph at a console and
compares against a printed prediction, and it was wrong for a pull
request before anyone looked.

WHAT IS DERIVED AND WHAT IS DECLARED.

  commands      the screen's cmd_count                        -- blob
  drawn         focus-state resolved at the screen's initial
                focus: state 0 always draws, state 1 draws
                when the node is NOT focused, state 2 when it
                is                                            -- blob
  static glyphs every slot's placeholder except the two the
                driver overwrites, counting only glyphs with
                w > 0, because render_slots gates both
                prims++ and slot_glyphs++ on that -- a space
                draws nothing and is not counted              -- blob
  tag glyphs    each arm's own tag, off the driver's #if
                chain: [c:<screen>], [<screen>], [compose],
                [theme], [clearopq]                           -- main.c
  telemetry     the two printf formats, walked literal by
                literal and conversion by conversion          -- main.c
  @ and n       the two frame counters' widths, from the
                reading's own n                               -- arithmetic
  field widths  what every OTHER runtime value prints at      -- DECLARED

THE DECLARED PART USED TO BE ONE NUMBER AND IT WAS WRONG. Until S15
this read "the driver's two telemetry lines reconstruct to 55 glyphs"
out of bench-phase2.md and added it. The lines reconstruct to 52 at
four-digit counters and 54 at five, which S15 watched happen inside a
single run as n crossed 10000, so every row of both tables was three
high and so was the compose arm's predicted identity.

A character count nobody was going to redo is a bad thing to declare.
Twelve field widths are a better one: each is a glance at a
photograph, `cmds` and `glyphs` are fenced against the blob below, and
the two counters are not declared at all.

AND THE SITTING'S OWN PHOTOGRAPHS ARE RE-DERIVED, not just the
prediction. A table that is checked before a sitting and transcribed
after it is only half fenced -- the half that was wrong. The readings
S15 transcribed are derived here from the blob, the format strings and
each one's own frame count, across five arms, three tag lengths, two
line-2 formats and three counter widths.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "packages", "baker"))

from ps2ui_bake.uib import read_uib                    # noqa: E402
from ps2ui_bake.quads import OP_QUAD, OP_TEXQUAD       # noqa: E402

BLOB = os.path.join(ROOT, "examples", "opl-env", "build", "ui.uib")
MAIN_C = os.path.join(ROOT, "runtime", "sample", "main.c")
DOCS = [os.path.join(ROOT, "docs", "PLAN.md"),
        os.path.join(ROOT, "docs", "bench-phase2.md")]
BENCH = DOCS[1]

# `| confirm | 110 | 156 | 64 | 220 |` under the sweep table's header.
# Leading whitespace allowed: PLAN.md indents the table three spaces
# inside a list item, and the first version of this anchored to column
# zero and read PLAN's table as empty -- reporting "0 rows" as a
# mismatch it could not explain rather than as a parse that failed.
ROW = re.compile(r"^\s*\|\s*(\w+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|"
                 r"\s*(\d+)\s*\|\s*(\d+)\s*\|\s*$")
HEADER = "| screen | commands | slot glyphs | drawn | `p` |"

# S15's own photographs, re-derived rather than transcribed and left.
# One table per line-2 format: the cycling, compose and standalone
# screen arms print `c g u`, the plain, clearopaque and theme arms
# print `p up`.
READ_CGU = "| arm | screen | `n` | `c` | `g` |"
READ_PUP = "| arm | `n` | top row | `p` |"

# NAMED HERE RATHER THAN COUNTED FROM THE FILE, BECAUSE A FLOOR IS NOT
# A FENCE. check-tutorial.py's phrase, and #94's review found this file
# repeating the exact shape it was written to close: check_readings
# returned a count and main tested `if not n`, so thirteen readings
# eroding to four still exited 0. Reword either header by one backtick
# and that whole table silently stops being read; delete a row, or give
# one an extra column, and it is skipped without a word.
#
# The sweep half never had that hole -- it fails per document when its
# header finds nothing -- and the asymmetry sat inside one file.
#
# An exact set, so lowering it is an edit to a check. Keyed by the
# fields that identify a photograph: which arm, which screen, and the
# frame count that fixes the telemetry width.
S15_CGU = {("cycle", "detail", 1320), ("cycle", "filters", 9393),
           ("cycle", "library", 10399), ("cycle", "confirm", 11283),
           ("cycle", "detail", 12121), ("cycle", "landing", 13082),
           ("compose", "compose", 542), ("compose", "compose", 1289),
           ("screen", "library", 3505)}
S15_PUP = {("plain", 1421), ("clearopq", 1242),
           ("theme", 823), ("theme", 1163)}


def oplenv_rows():
    """OPLENV_ROWS out of the driver, not restated here."""
    src = open(MAIN_C, encoding="utf-8").read()
    m = re.search(r"#define OPLENV_ROWS\s+(\d+)", src)
    if not m:
        raise SystemExit("not ok - runtime/sample/main.c no longer defines "
                         "OPLENV_ROWS; the bound-window glyph delta counts "
                         "one title index per row")
    return int(m.group(1))


# THE TELEMETRY LINES, DERIVED FROM THEIR FORMAT STRINGS.
#
# This used to be one hand-counted scalar -- "the driver's two
# telemetry lines reconstruct to 55 glyphs" -- declared in
# bench-phase2.md and read back here. S15 measured 52, and then 54 in
# the same run, because it is not a constant: `@` and `n` are frame
# counters and they gain a digit as the run goes on. The table was
# three high on every row for a pull request, and the compose arm's
# predicted identity with it.
#
# So the format strings are parsed now and only the VALUE WIDTHS are
# declared. That is a better place for the hand-supplied number: a
# width is one glance at a photograph, where a 55-glyph total was a
# character count nobody was going to redo. Two of the widths are
# fenced against the blob below, and the two frame counters are not
# declared at all -- `@` is a frame index from the window just past,
# so it is within one window of `n` and its width follows.
WIDTHS_HEADER = "telemetry field widths, in digits"

# Positional names for the variable-width conversions in each format.
# `%02lu` is a zero-padded two-wide fraction and is not named; `%s` is
# the arm's tag and is measured separately. A format that stops
# matching its list is a FAILURE rather than a silent miscount, which
# is the whole reason the old scalar could rot unnoticed.
L1_VARS = ["ee", "ee_peak", "gs", "gs_peak", "gs_peak_at"]
L2_VARS = {
    "cgu": ["field", "cmds", "glyphs", "unfilled", "missed", "missed_at",
            "frame"],
    "pup": ["field", "prims", "uploaded", "missed", "missed_at", "frame"],
    "pupt": ["field", "prims", "uploaded", "missed", "missed_at", "frame",
             "theme"],
}


def declared_widths():
    """{field: digits} from bench-phase2.md's declared width block."""
    text = open(BENCH, encoding="utf-8").read()
    i = text.find(WIDTHS_HEADER)
    if i < 0:
        raise SystemExit(
            "not ok - docs/bench-phase2.md no longer carries the %r block. "
            "Those widths are the only hand-supplied input to the sweep "
            "table, and without them on the page it is unfalsifiable again."
            % WIDTHS_HEADER)
    end = text.find("```", i)
    if end < 0:
        raise SystemExit("not ok - docs/bench-phase2.md's %r block is not "
                         "closed" % WIDTHS_HEADER)
    got = dict((k, int(v)) for k, v
               in re.findall(r"(\w+)\s+(\d+)", text[i + len(WIDTHS_HEADER):end]))
    return got


def telemetry_formats():
    """(line 1, {kind: line 2}) as printf formats, out of the driver."""
    src = open(MAIN_C, encoding="utf-8").read()
    one = re.search(r'sprintf\(telem,\s*\n\s*"(%see[^"]*)"', src)
    if not one:
        raise SystemExit("not ok - runtime/sample/main.c no longer builds "
                         "the readout's line 1 with sprintf(telem, \"%see"
                         "...\"); its glyphs are counted in g and this "
                         "derives them from the format")
    two = {}
    for fmt in re.findall(r'"(f%lu[^"]*)"', src):
        if " c%lu g%lu u%lu " in fmt:
            kind = "cgu"
        else:
            # The theme arm prints a trailing t%u and the plain arms do
            # not. Keyed apart rather than merged: reading the plain
            # arm's p against a format one field too long is the same
            # class of quiet miscount this whole check exists to stop.
            kind = "pupt" if fmt.rstrip().endswith("t%u") else "pup"
        two[kind] = fmt
    if "cgu" not in two:
        raise SystemExit("not ok - runtime/sample/main.c no longer prints "
                         "c/g/u on line 2; the sweep's x-axis is read off "
                         "that field")
    return one.group(1), two


def fmt_glyphs(fmt, names, widths, font, where):
    """Glyphs a printf format renders to, given each value's width.

    Literals go through the same w > 0 rule as any other slot text --
    a space draws nothing -- and every conversion consumes the next
    name in `names`. A leftover name, or a conversion with no name to
    consume, means the driver's format and this list have diverged.
    """
    total, rest = 0, list(names)
    i = 0
    while i < len(fmt):
        if fmt[i] != "%":
            total += glyphs(fmt[i], font)
            i += 1
            continue
        m = re.match(r"%(\d*)(?:l)?([usd])", fmt[i:])
        if not m:
            raise SystemExit("not ok - %s: unparsed conversion at %r"
                             % (where, fmt[i:i + 6]))
        i += m.end()
        if m.group(2) == "s":
            continue                      # the arm's tag, measured apart
        if m.group(1):                    # %02lu: a fixed-width fraction
            total += int(m.group(1))
            continue
        if not rest:
            raise SystemExit(
                "not ok - %s: the driver prints more fields than this "
                "check names (%r). A field was added to the readout and "
                "the glyph count silently went low -- which is exactly "
                "what the 55-glyph constant did." % (where, fmt))
        name = rest.pop(0)
        if name not in widths:
            raise SystemExit("not ok - %s: no declared width for %r"
                             % (where, name))
        total += widths[name]
    if rest:
        raise SystemExit(
            "not ok - %s: this check names fields the driver no longer "
            "prints (%s). The readout lost a field and the glyph count "
            "silently went high." % (where, ", ".join(rest)))
    return total


def telemetry(widths, font, kind="cgu"):
    """Both telemetry lines in glyphs, EXCLUDING the arm's tag."""
    one, two = telemetry_formats()
    return (fmt_glyphs(one, L1_VARS, widths, font, "line 1")
            + fmt_glyphs(two[kind], L2_VARS[kind], widths, font,
                         "line 2 (%s)" % kind))


def driver_tags():
    """Every arm's readout tag, out of the driver's own #if chain.

    Returns ({screen: cycling tag}, {screen: standalone tag},
    {arm: literal tag}). Five arms name themselves on line 1 and the
    tag is slot text, so each one's glyphs land in `g` -- S15 read
    `[library]` at 9, `[c:library]` at 11, `[clearopq]` at 10 and
    `[theme]` at 7 off four photographs, and only the first two were
    known to this check before that sitting.
    """
    src = open(MAIN_C, encoding="utf-8").read()
    m = re.search(r"oplenv_cycle\[\]\s*=\s*\{(.*?)\}", src, re.S)
    if not m:
        raise SystemExit("not ok - runtime/sample/main.c has no "
                         "oplenv_cycle[] array; this check reads the sweep "
                         "order out of the driver, not out of the document")
    names = re.findall(r'"([^"]+)"', m.group(1))

    built = {}
    for pre, post, arg in re.findall(
            r'sprintf\(tag,\s*"([^"]*)%s([^"]*)",\s*(\w+)', src):
        built["cycle" if arg.startswith("oplenv_cycle") else "screen"] = (
            pre, post)
    lit = dict((t.strip("[] "), t)
               for t in re.findall(r'strcpy\(tag,\s*"(\[[^"]*)"\)', src))

    missing = ([k for k in ("cycle", "screen") if k not in built]
               + [k for k in ("compose", "theme", "clearopq")
                  if k not in lit])
    if missing:
        raise SystemExit(
            "not ok - runtime/sample/main.c no longer sets a readout tag "
            "for: %s. Every arm names itself on line 1 and the tag is slot "
            "text, so an arm this check cannot see is an arm whose `g` it "
            "derives low." % ", ".join(missing))

    cyc = dict((n, built["cycle"][0] + n + built["cycle"][1]) for n in names)
    std = dict((n, built["screen"][0] + n + built["screen"][1])
               for n in names)
    return cyc, std, lit


def glyphs(text, font):
    """Glyphs the runtime would DRAW: missing codepoints fall back to
    '?' (ps2ui.c:1183) and zero-width glyphs are not counted at all,
    since render_slots gates prims++/slot_glyphs++ on g->w > 0."""
    n = 0
    for ch in text:
        g = font["glyphs"].get(ord(ch)) or font["glyphs"].get(ord("?"))
        if g and g["w"] > 0:
            n += 1
    return n


def screen_parts(u):
    """{screen: (cmds, drawn, static glyphs, telemetry font)}.

    `static` is every slot's placeholder except the two the driver
    overwrites; `drawn` resolves focus state at the screen's initial
    focus -- state 0 always draws, state 1 when the node is NOT
    focused, state 2 when it is.
    """
    out = {}
    for sc in u.screens:
        first, count = sc["cmd_first"], sc["cmd_count"]
        recs = [r for r in u.records[first:first + count]
                if r.op in (OP_QUAD, OP_TEXQUAD)]
        init = sc["initial"]
        drawn = sum(1 if r.state == 0 else
                    (r.focus != init) if r.state == 1 else
                    (r.focus == init)
                    for r in recs)
        slots = u.slots[sc["slot_first"]:sc["slot_first"] + sc["slot_count"]]
        tel = [s for s in slots
               if s["name"].endswith(("-telem", "-telem2"))]
        static = sum(glyphs(s["placeholder"], u.fonts[s["font"]])
                     for s in slots if s not in tel)
        font = u.fonts[tel[0]["font"]] if tel else u.fonts[0]
        out[sc["name"]] = (count, drawn, static, font)
    return out


def derive(parts, telem, tags):
    """The pre-registered sweep table: the cycling arm, one render."""
    out = {}
    for name, (count, drawn, static, font) in parts.items():
        tag = glyphs(tags.get(name, ""), font)
        g = static + telem + tag
        out[name] = (count, g, drawn, drawn + g, tag)
    return out


def counter_digits(n):
    """(digits(n), digits(@)) for a reading whose frame count is `n`.

    `@` is the frame that held the peak in the window just past, kept
    absolute so `@ % OPLENV_SCROLL_EVERY == 0` reads as "the peak was a
    scroll frame" (main.c). The window is 60 frames and the readout
    shows the last completed one, so `@` is within two windows of `n`
    and its width follows -- which is why it is derived here instead of
    being a thirteenth declared number. Straddle a power of ten and
    this refuses rather than guessing.
    """
    lo, hi = max(n - 120, 0), n
    if len(str(lo)) != len(str(hi)):
        raise SystemExit(
            "not ok - a reading at n%d sits within 120 frames of a digit "
            "boundary, so `@` could print at %d digits or %d and the "
            "telemetry width is ambiguous. Record `@` alongside `n` for "
            "that row, or drop it." % (n, len(str(lo)), len(str(hi))))
    return len(str(n)), len(str(hi))


def md_rows(path, header):
    """Rows under every occurrence of `header`, as lists of cells.

    Walks CONSECUTIVE lines and stops at the first non-row, so a later
    table cannot be absorbed into this one.
    """
    lines = open(path, encoding="utf-8").read().splitlines()
    found = []
    for i, line in enumerate(lines):
        if line.strip() != header:
            continue
        rows = []
        for nxt in lines[i + 1:]:
            t = nxt.strip()
            if not t.startswith("|"):
                break
            cells = [c.strip().strip("`*") for c in t.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue                        # the |---|---:| rule
            rows.append(cells)
        found.append(rows)
    return found


def tables(path):
    """Every pre-registered sweep table, as {screen: (c, g, drawn, p)}."""
    out = []
    for rows in md_rows(path, HEADER):
        got = {}
        for cells in rows:
            if len(cells) == 5 and cells[1].isdigit():
                got[cells[0]] = tuple(int(c) for c in cells[1:])
        out.append(got)
    return out


def check_readings(parts, widths, cyc, std, lit, fail):
    """Re-derive `g` or `p` for every photograph the sitting recorded.

    The prediction table is one width profile on one arm. S15 was
    twenty-two photographs across five arms at three frame-counter
    widths, and its whole correction came from noticing that `g` moved
    between two of its own readings. Every row below is derived from
    the blob, the driver's format strings and that row's own `n`.

    Not every photograph left a transcribed `n`, and one sweep screen
    -- `recent` -- has no row here at all. S15_CGU and S15_PUP name
    what does, so that gap stays visible instead of being absorbed
    into a count.
    """
    seen_cgu, seen_pup = set(), set()
    for cells in [r for t in md_rows(BENCH, READ_CGU) for r in t]:
        if len(cells) != 5 or not cells[2].isdigit():
            continue
        arm, screen, n, c, g = (cells[0], cells[1], int(cells[2]),
                                int(cells[3]), int(cells[4]))
        dn, dat = counter_digits(n)
        w = dict(widths, frame=dn, gs_peak_at=dat)
        if screen == "compose":
            lib, con = parts["library"], parts["confirm"]
            font = lib[3]
            tel = 2 * telemetry(w, font, "cgu")
            tag = 2 * glyphs(lit["compose"], font)
            want_c, static = lib[0] + con[0], lib[2] + con[2]
        else:
            if screen not in parts:
                fail.append("bench readings name a screen %r the blob does "
                            "not carry" % screen)
                continue
            want_c, _, static, font = parts[screen]
            tel = telemetry(w, font, "cgu")
            table = {"cycle": cyc, "screen": std}.get(arm)
            if table is None:
                fail.append("bench readings name an arm %r that does not "
                            "print c/g/u" % arm)
                continue
            tag = glyphs(table[screen], font)
        want_g = static + tag + tel
        if (c, g) != (want_c, want_g):
            fail.append(
                "bench reading %s/%s at n%d reads c=%d g=%d; derived c=%d "
                "g=%d (static %d + tag %d + telemetry %d at %d-digit n, "
                "%d-digit @)"
                % (arm, screen, n, c, g, want_c, want_g, static, tag, tel,
                   dn, dat))
        else:
            seen_cgu.add((arm, screen, n))

    for cells in [r for t in md_rows(BENCH, READ_PUP) for r in t]:
        if len(cells) != 4 or not cells[1].isdigit():
            continue
        arm, n, top, p = (cells[0], int(cells[1]), int(cells[2]),
                          int(cells[3]))
        dn, dat = counter_digits(n)
        w = dict(widths, frame=dn, gs_peak_at=dat)
        _, drawn, static, font = parts["library"]
        kind = "pupt" if arm == "theme" else "pup"
        tag = glyphs(lit[arm], font) if arm in lit else 0
        # oplenv_bind_window writes "Title of a Game %d" over each row's
        # placeholder, and the placeholders are Game 1..9. Every other
        # bound field keeps its width -- "%d - Action" against
        # "2003 - Action", a two-digit score against "92", USB against
        # HDD -- so the row indices are the whole difference.
        bound = sum(len(str(top + i)) - 1 for i in range(oplenv_rows()))
        want = drawn + static + bound + tag + telemetry(w, font, kind)
        if p != want:
            fail.append(
                "bench reading %s at n%d with row %d at the top reads "
                "p=%d; derived %d (drawn %d + static %d + bound %+d + tag "
                "%d + telemetry %d at %d-digit n, %d-digit @)"
                % (arm, n, top, p, want, drawn, static, bound, tag,
                   telemetry(w, font, kind), dn, dat))
        else:
            seen_pup.add((arm, n))
    return seen_cgu, seen_pup
def main():
    if not os.path.exists(BLOB):
        # FAIL, never skip: a checker that passes when its subject is
        # absent reports green for the one state it verified nothing in.
        raise SystemExit("not ok - no blob at %s. Run "
                         "examples/opl-env/build.sh first; this check does "
                         "not bake." % os.path.relpath(BLOB, ROOT))
    u = read_uib(BLOB)
    parts = screen_parts(u)
    widths = declared_widths()
    cyc, std, lit = driver_tags()

    fail = []

    # TWO OF THE TWELVE DECLARED WIDTHS ARE FENCED AGAINST THE BLOB.
    # `c` and `g` are printed by the driver and derived here, so a
    # screen that crosses a digit boundary invalidates the profile --
    # silently, and in the direction of a table that is one glyph low
    # on the row that grew. The other ten are one glance at a
    # photograph; these two are not, because they move with the blob.
    telem = telemetry(widths, u.fonts[0], "cgu")
    want = derive(parts, telem, cyc)
    for name, (count, g, _drawn, _p, _tag) in sorted(want.items()):
        for field, value in (("cmds", count), ("glyphs", g)):
            if len(str(value)) != widths.get(field):
                fail.append(
                    "docs/bench-phase2.md declares %s at %d digits; %s "
                    "prints %d, which is %d. The blob has moved past the "
                    "width the sweep table was written at."
                    % (field, widths.get(field, -1), name, value,
                       len(str(value))))

    for path in DOCS:
        rel = os.path.relpath(path, ROOT)
        found = tables(path)
        bad = []
        if not found:
            bad.append("%s carries no sweep table -- the header this reads "
                       "(%r) was reworded, and either way this check has "
                       "stopped covering it" % (rel, HEADER))
        for rows in found:
            if set(rows) != set(want):
                bad.append("%s's sweep table lists [%s]; the blob has [%s]"
                           % (rel, ", ".join(sorted(rows)),
                              ", ".join(sorted(want))))
                continue
            for name, got in sorted(rows.items()):
                exp = want[name][:4]
                if got != exp:
                    bad.append(
                        "%s: %s is c=%d g=%d drawn=%d p=%d; derived "
                        "c=%d g=%d drawn=%d p=%d (tag %r is %d glyphs, "
                        "telemetry %d)"
                        % ((rel, name) + got + exp
                           + (cyc.get(name, ""), want[name][4], telem)))
        print("%s - %s: %d sweep table(s), %d rows each, derived from the "
              "blob and the driver"
              % ("ok" if not bad else "not ok", rel, len(found), len(want)))
        fail.extend(bad)

    # The composition arm reads `g` against the two sweep photographs
    # BEFORE it trusts any timing -- and the arms carry different tags,
    # so the sum no longer lands on the nose. The offset is derived
    # here rather than left for someone to rediscover at a console.
    font = u.fonts[0]
    off = 2 * glyphs(lit["compose"], font) - (want["library"][4]
                                              + want["confirm"][4])
    stated = re.search(r"g\(library\) \+ g\(confirm\) ([-+] \d+)",
                       open(BENCH, encoding="utf-8").read())
    if not stated:
        fail.append("docs/bench-phase2.md states the composition "
                    "identity without the tag offset; the compose arm "
                    "carries %r twice and the two sweep points carry "
                    "their own, so g does not add on the nose -- it is "
                    "%+d" % (lit["compose"], off))
    elif int(stated.group(1).replace(" ", "")) != off:
        fail.append("docs/bench-phase2.md states a composition offset "
                    "of %s; the tags give %+d" % (stated.group(1), off))
    else:
        print("ok - the composition arm's glyph identity carries its "
              "%+d tag offset, derived from the driver" % off)

    got_cgu, got_pup = check_readings(parts, widths, cyc, std, lit, fail)
    for got, want, header in ((got_cgu, S15_CGU, READ_CGU),
                              (got_pup, S15_PUP, READ_PUP)):
        if got != want:
            fail.append(
                "the S15 readings under %r do not re-derive as the named "
                "set. Missing: %s. Unexpected: %s. A sitting whose "
                "photographs are transcribed and never re-derived is how "
                "the 55-glyph constant survived three documents, and a "
                "COUNT of them is how that check erodes back to nothing."
                % (header,
                   sorted(want - got) or "none",
                   sorted(got - want) or "none"))
    if got_cgu == S15_CGU and got_pup == S15_PUP:
        print("ok - all %d named S15 readings re-derived from the blob, "
              "the driver's format strings and each row's own frame count"
              % (len(S15_CGU) + len(S15_PUP)))

    for f in fail:
        print("not ok - %s" % f)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
