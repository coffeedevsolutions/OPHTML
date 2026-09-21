#!/usr/bin/env python3
"""Hold BACKLOG.md's ticks to its rows (F29).

The audit that exists to catch stale ticks missed rows three times, and
none of the three was a judgement call. The 2026-09-07 pass ticked 17
rows and left B8, F24 and B2; a sweep on 2026-09-12 missed B8 again.
B8 was **unmatchable** -- its row read `| B8* |`, a marker no legend
defines, which no ID-keyed pattern matches. F24 was well formed and
missed anyway, findable only by reading `quads.py`. B2 was audited and
recorded as unsettled, which is worse than either, because a reader
consulting the board learned something false from a row somebody had
checked.

WHAT THIS CAN ASSERT, all of it structure and none of it prose:

  1. Every row ID in the three `| ID |` tables matches (F|B|S|P)[0-9]+
     exactly -- no trailing punctuation, no marker the file never
     defines -- and every row survives being rendered as a table row.

  2. Every ID claimed on a status line resolves to exactly one row, or
     is declared consumed.

  3. No status line claims an ID shipped while its row is open.

ONE CORPUS RULE SERVES CHECKS 2 AND 3, and it is the whole design: a
table row contributes only its ID cell, and every tick-claim is read
from the status lines. A bare prose mention is a reference, not a
claim. Without that rule check 2 fires on `S10` in a bench step and on
the two other files' `S` namespace, and check 3 fires on every ticked
row that cites an open one in its prose -- which these rows do
routinely, so run that way over the whole file it returns F19, F5, F8,
S4 and F29's own quoted examples. The scoping is structural, not an
accommodation for one quotation, and nobody should later "improve"
either check by widening it back over table rows.

Check 2 still reads more than the tables, because the collisions it
looks for live in status lines: `✅ F23` and `✅ F25` name rows that do
not exist and never did. The two checks read different corpora and
this docstring has to say so.

FOUR TRAPS THE SPEC NAMES, and the first was hit while writing it:

  (a) Match the ID as a token, THROUGH MARKUP. A pattern anchored on
      `✅ <ID>` misses `✅ **<ID>**`, which on the board this was first
      run against is 10 of the 29 ticks that name an ID -- a third of
      them, invisible. The first hand-run of check 3 used exactly that
      pattern, reported the board clean, and was believed; it found B2
      only because one line happens to be unbolded. A check that found
      a real defect for an accidental reason is still a check that
      passed for the wrong reason.

  (b) `<ID>-partial` is a distinct token and does not assert `<ID>`.
      The board has a genuine third state and spells it that way. A
      check requiring exact tokens never fires on it, so no prose
      carve-out is needed and none should be added.

  (c) Only the three `| ID |` tables are the board. This file also
      holds a three-column table whose first cells read `F27 positional
      API ✅` and `F8 layering`; checks 1 and 2 flag both unless the
      header row is required to be an ID header.

  (d) Check 3 matches NON-ADJACENTLY within a status line. `✅ B9 + B8`
      does not put the ID next to the tick, and B8 is the row this
      exists for.

AND WHAT IT CANNOT DO: a row whose work shipped and whose ID and marker
are both well formed. F24 was exactly that, and only reading the code
found it. This bounds the problem rather than solving it; the residue
is what F28 leaves open.

Usage:
    tools/check-backlog.py            # check, exit 1 on failure
    tools/check-backlog.py --report   # also print what it parsed
"""
import argparse
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(REPO, "BACKLOG.md")

ID_RE = re.compile(r"^(?:F|B|S|P)[0-9]+$")
# A status line is a line inside a paragraph that opens with this. The
# sprint blocks are a closed log and the file says so; the shape is
# what makes "status line" a structural class rather than a judgement.
STATUS_OPEN_RE = re.compile(r"^\*\*Sprint\s+\d+\s+status\s*\(")
# How the file declares an ID spent on work that never got a row. It is
# prose a person reaching for a free ID will read, on purpose: the
# collision this prevents was made twice by people reading the tables.
CONSUMED_RE = re.compile(r"^\*\*Consumed IDs \(never reuse\):\*\*\s*(.+?)\.?\s*$")
TICK = "✅"


def cells(line):
    """A table row's cells, split the way a GFM table splits them.

    The split happens before inline parsing, so a `|` inside a code
    span is a cell delimiter and not a literal. That is the whole
    defect check 1 screens for.
    """
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    out, buf, esc = [], [], False
    for ch in body:
        if esc:
            buf.append(ch)
            esc = False
        elif ch == "\\":
            buf.append(ch)
            esc = True
        elif ch == "|":
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return out


def unescaped(text):
    """The text with backslash escapes removed, so `\\`` is not a delimiter."""
    return re.sub(r"\\.", "", text)


def tokens(text):
    """Word tokens, with bold and code markup stripped off them.

    `S1/S4-partial` gives S1 and S4-partial: the hyphen binds, so the
    partial marker is its own token and asserts nothing (trap b), while
    the slash does not, so the S1 beside it is still seen (trap a).
    """
    flat = text.replace("*", "").replace("`", "")
    return re.findall(r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*", flat)


def board_tables(lines):
    """The three `| ID |` tables, as (line number, width, row) tuples.

    Requiring the header cell to be exactly `ID` is trap (c): the
    sequencing table's first column is prose that starts with an ID.
    The width travels with the row because a row that splits into more
    cells than its header has is the truncation defect, stated.
    """
    rows, i = [], 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        start = i
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            i += 1
        block = lines[start:i]
        if len(block) < 2:
            continue
        head = cells(block[0])
        sep = cells(block[1])
        if not head or head[0].strip() != "ID":
            continue
        if not all(re.fullmatch(r"\s*:?-{2,}:?\s*", c) for c in sep):
            continue
        for k, row in enumerate(block[2:], start=start + 2):
            rows.append((k + 1, len(head), row))
    return rows


def status_lines(lines):
    """Every physical line of every sprint-status BLOCK.

    Physical rather than joined, because that is the unit the file
    wraps claims in and the unit `✅ B9 + B8` fits inside.

    A block runs from its `**Sprint N status (` line to the next one or
    to the next `## ` heading, NOT to the next blank line. The
    difference is three rows: Sprint 6 announces B14, B15 and B16 in a
    second paragraph that opens "Two defects fell out of testing it",
    and a paragraph-scoped rule cannot see any of them. F29 wrote down
    what this should return on the board at 098b134 -- B8 and B10-B16
    -- and the paragraph-scoped first draft returned B10-B13, which is
    the only reason the gap was found. A spec that records its expected
    output is a spec that can fail its implementer.

    The `## ` terminator is what keeps the narrative sections out. They
    quote `✅ B9 + B8` and `✅ B2` while explaining this very check, and
    over that corpus check 3 fires on the quotations.
    """
    out, i = [], 0
    while i < len(lines):
        if not STATUS_OPEN_RE.match(lines[i]):
            i += 1
            continue
        out.append((i + 1, lines[i]))
        i += 1
        while (i < len(lines) and not lines[i].startswith("## ")
               and not STATUS_OPEN_RE.match(lines[i])):
            out.append((i + 1, lines[i]))
            i += 1
    return out


def check(text):
    lines = text.split("\n")
    bad = []
    rows = board_tables(lines)

    # --- check 1: the rows are well formed and survive rendering -----
    declared, dupes = {}, []
    for lineno, width, row in rows:
        cs = cells(row)
        ident = cs[0].strip()
        if not ID_RE.match(ident):
            bad.append("check 1: BACKLOG.md:%d has ID cell %r, which is not "
                       "(F|B|S|P)NN -- a marker nothing defines is a row no "
                       "ID-keyed pattern can match, which is how B8 was "
                       "missed twice" % (lineno, ident))
            continue
        if len(cs) != width:
            shown = len("|".join(cs[:width]))
            bad.append("check 1: %s at BACKLOG.md:%d splits into %d cells in "
                       "a %d-column table, so the rendered board shows %d of "
                       "its %d characters and drops the rest. A `|` inside a "
                       "code span is still a cell delimiter; write \\| for a "
                       "literal pipe"
                       % (ident, lineno, len(cs), width, shown, len(row)))
        for c in cs:
            # A backslash-escaped backtick is a literal one and opens
            # nothing. F29's own row quotes one while explaining this
            # defect, and a naive count calls that row broken.
            if unescaped(c).count("`") % 2:
                bad.append("check 1: %s at BACKLOG.md:%d leaves a code span "
                           "open at %r, so the rest of the cell renders as "
                           "code -- and if a `|` follows it, the row is cut "
                           "there too" % (ident, lineno, c.strip()[-48:]))
                break
        if ident in declared:
            dupes.append((ident, declared[ident], lineno))
        else:
            declared[ident] = lineno
    for ident, first, second in dupes:
        bad.append("check 2: %s has rows at BACKLOG.md:%d and :%d, so a "
                   "claim on it resolves to neither" % (ident, first, second))

    shipped = set()
    for lineno, width, row in rows:
        cs = cells(row)
        ident = cs[0].strip()
        if ID_RE.match(ident) and len(cs) > 1 and cs[1].lstrip().startswith(TICK):
            shipped.add(ident)

    consumed = set()
    for line in lines:
        m = CONSUMED_RE.match(line)
        if m:
            consumed |= {t for t in tokens(m.group(1)) if ID_RE.match(t)}

    # --- checks 2 and 3: the claims, read from the status lines ------
    claims = []
    for lineno, line in status_lines(lines):
        if TICK not in line:
            continue
        for t in tokens(line):
            if ID_RE.match(t):
                claims.append((lineno, t))

    for lineno, ident in claims:
        if ident in declared or ident in consumed:
            continue
        bad.append("check 2: BACKLOG.md:%d ticks %s, which has no row and is "
                   "not declared consumed -- either it was renumbered, or the "
                   "next person reaching for a free ID will take it twice"
                   % (lineno, ident))

    for lineno, ident in claims:
        if ident in declared and ident not in shipped:
            bad.append("check 3: BACKLOG.md:%d claims %s shipped while its "
                       "row at :%d is open. One of the two is wrong and the "
                       "row is the one a reader trusts"
                       % (lineno, ident, declared[ident]))

    return rows, declared, shipped, consumed, claims, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="print what was parsed, not only what failed")
    ap.add_argument("--file", default=BOARD)
    args = ap.parse_args()

    with open(args.file, encoding="utf-8") as fh:
        rows, declared, shipped, consumed, claims, bad = check(fh.read())

    if args.report:
        print("# %d row(s) in the board tables, %d shipped"
              % (len(rows), len(shipped)))
        print("# %d tick-claim(s) on status lines, %d ID(s) declared consumed"
              % (len(claims), len(consumed)))
        for lineno, ident in claims:
            state = ("shipped" if ident in shipped else
                     "OPEN" if ident in declared else
                     "consumed" if ident in consumed else "NO ROW")
            print("#   :%-4d %-5s %s" % (lineno, ident, state))

    for e in bad:
        print("not ok - %s" % e, file=sys.stderr)
    if not bad:
        print("ok - %d row(s) well formed and rendering whole" % len(rows))
        print("ok - %d tick-claim(s) on status lines resolve to a row or a "
              "consumed ID" % len(claims))
        print("ok - no status line claims an ID shipped while its row is open")
    print("%s: %d row(s), %d claim(s), %d problem(s)"
          % ("FAIL" if bad else "PASS", len(rows), len(claims), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
