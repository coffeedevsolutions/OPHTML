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
  tag glyphs    the cycling arm's `[c:<screen>] `             -- main.c
  telemetry     what the driver's two lines reconstruct to    -- DECLARED

The last one is the only hand-supplied number, because it depends on
how wide the runtime values print. bench-phase2.md states it and this
reads it back, so the assumption is on the page rather than inside a
tool. With it at the declared value the pre-#87 table reproduces
exactly on all six screens, which is what makes the rest trustworthy.
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


def declared_telemetry():
    """The driver's two telemetry lines, in glyphs, from bench-phase2.md."""
    m = re.search(r"driver's two telemetry lines reconstruct to (\d+) "
                  r"glyphs", open(BENCH, encoding="utf-8").read())
    if not m:
        raise SystemExit(
            "not ok - docs/bench-phase2.md no longer states what the "
            "driver's two telemetry lines reconstruct to. That number is "
            "the one input this check cannot derive, and without it on the "
            "page the sweep table is unfalsifiable again.")
    return int(m.group(1))


def driver_tags():
    """{screen: tag string} for the cycling arm, plus the compose arm's."""
    src = open(MAIN_C, encoding="utf-8").read()
    m = re.search(r"oplenv_cycle\[\]\s*=\s*\{(.*?)\}", src, re.S)
    if not m:
        raise SystemExit("not ok - runtime/sample/main.c has no "
                         "oplenv_cycle[] array; this check reads the sweep "
                         "order out of the driver, not out of the document")
    names = re.findall(r'"([^"]+)"', m.group(1))
    fmt = re.search(r'sprintf\(tag,\s*"([^"]*)%s([^"]*)"', src)
    if not fmt:
        raise SystemExit("not ok - runtime/sample/main.c no longer builds "
                         "the cycling arm's tag with sprintf(tag, ...); the "
                         "tag is slot text and its glyphs are counted in g")
    tags = {n: fmt.group(1) + n + fmt.group(2) for n in names}
    comp = re.search(r'strcpy\(tag,\s*"(\[compose\][^"]*)"\)', src)
    return tags, (comp.group(1) if comp else None)


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


def derive(u, telem, tags):
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
        telem_slots = [s for s in slots
                       if s["name"].endswith(("-telem", "-telem2"))]
        static = sum(glyphs(s["placeholder"], u.fonts[s["font"]])
                     for s in slots if s not in telem_slots)
        font = u.fonts[telem_slots[0]["font"]] if telem_slots else u.fonts[0]
        tag = glyphs(tags.get(sc["name"], ""), font)
        g = static + telem + tag
        out[sc["name"]] = (count, g, drawn, drawn + g, tag)
    return out


def tables(path):
    """Every sweep table in one document, as {screen: (c, g, drawn, p)}.

    Walks CONSECUTIVE lines after the header and stops at the first one
    that is not a row, so a second table further down the file cannot
    be absorbed into this one.
    """
    lines = open(path, encoding="utf-8").read().splitlines()
    found = []
    for i, line in enumerate(lines):
        if line.strip() != HEADER:
            continue
        rows = {}
        for nxt in lines[i + 1:]:
            m = ROW.match(nxt)
            if m:
                rows[m.group(1)] = tuple(int(m.group(k))
                                         for k in (2, 3, 4, 5))
            elif nxt.strip().startswith("|"):
                continue          # the |---|---:| separator
            else:
                break
        found.append(rows)
    return found


def main():
    if not os.path.exists(BLOB):
        # FAIL, never skip: a checker that passes when its subject is
        # absent reports green for the one state it verified nothing in.
        raise SystemExit("not ok - no blob at %s. Run "
                         "examples/opl-env/build.sh first; this check does "
                         "not bake." % os.path.relpath(BLOB, ROOT))
    u = read_uib(BLOB)
    telem = declared_telemetry()
    tags, compose_tag = driver_tags()
    want = derive(u, telem, tags)

    fail = []
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
                        "c=%d g=%d drawn=%d p=%d (tag %r is %d glyphs)"
                        % ((rel, name) + got + exp
                           + (tags.get(name, ""), want[name][4])))
        print("%s - %s: %d sweep table(s), %d rows each, derived from the "
              "blob and the driver"
              % ("ok" if not bad else "not ok", rel, len(found), len(want)))
        fail.extend(bad)

    # The composition arm reads `g` against the two sweep photographs
    # BEFORE it trusts any timing -- and the arms carry different tags,
    # so the sum no longer lands on the nose. The offset is derived
    # here rather than left for someone to rediscover at a console.
    if compose_tag is None:
        fail.append("runtime/sample/main.c no longer sets a [compose] tag; "
                    "the glyph identity below is derived from it")
    else:
        font = u.fonts[0]
        off = 2 * glyphs(compose_tag, font) - (want["library"][4]
                                               + want["confirm"][4])
        stated = re.search(r"g\(library\) \+ g\(confirm\) ([-+] \d+)",
                           open(BENCH, encoding="utf-8").read())
        if not stated:
            fail.append("docs/bench-phase2.md states the composition "
                        "identity without the tag offset; the compose arm "
                        "carries %r twice and the two sweep points carry "
                        "their own, so g does not add on the nose -- it is "
                        "%+d" % (compose_tag, off))
        elif int(stated.group(1).replace(" ", "")) != off:
            fail.append("docs/bench-phase2.md states a composition offset "
                        "of %s; the tags give %+d"
                        % (stated.group(1), off))
        else:
            print("ok - the composition arm's glyph identity carries its "
                  "%+d tag offset, derived from the driver" % off)

    for f in fail:
        print("not ok - %s" % f)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
