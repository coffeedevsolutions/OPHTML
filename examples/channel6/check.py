#!/usr/bin/env python3
"""Verify the channel-6 blob's contract, straight off the baked file.

    PYTHONPATH=packages/baker python3 examples/channel6/check.py build/ui.uib

The memcard example ends in `make -C runtime test`, but that C test
asserts the memcard example's own focus and slot names, so it cannot
double as this example's check. This does the equivalent job on the
Python side: it re-reads the .uib (CRC, version and feature bits are
validated on the way in) and asserts what the console is entitled to
assume.

The first group used to cover three table ceilings —
PS2UI_MAX_TEXTURES, PS2UI_MAX_SLOTS, PS2UI_MAX_SCREENS. Writing this
example is what surfaced that they existed and nothing on the host
knew them. They are gone now: the v6 arena made the context size
itself from the blob, and a number ps2ui.h picked then bounded nothing
the blob's own size did not already bound.

What is asserted in their place is what still constrains a loader —
the format's own uint16 count fields, and the arena the blob demands,
reported rather than compared against an invented threshold. The
direction is the same as before: the baker checks what it is about to
write, this checks what a loader will actually find.
"""

import os
import re
import sys

from ps2ui_bake.quads import (FOCUS_NONE, OP_QUAD, OP_SCISSOR_POP,
                               OP_SCISSOR_PUSH, OP_TEXQUAD)
from ps2ui_bake.rounding import css_channel_to_gs
from ps2ui_bake.clip import can_draw, intersect
from ps2ui_bake import gs
from ps2ui_bake.uib import FEAT_DYNAMIC_TEXT, read_uib

HERE = os.path.dirname(os.path.abspath(__file__))
PS2UI_H = os.path.join(HERE, "..", "..", "runtime", "ps2ui.h")

CANVAS = (640, 448)

GAMES_FOCUS = [
    "game-aurora", "game-cartography", "game-harbor",
    "game-turbo", "game-moth", "game-kaiju",
    "act-launch", "act-saves", "act-probe",
]
PROBE_FOCUS = [
    "probe-alpha", "probe-radius", "probe-type",
    "probe-clip", "probe-modulate", "probe-image", "probe-aspect",
    "probe-flex",
]
# name -> capacity, the buffer the runtime is allowed to write into.
GAMES_SLOTS = {
    "count": 4, "card": 30,
    "sel-title": 24, "sel-sub": 30,
    "sel-id": 16, "sel-from": 16, "sel-save": 16,
    **{f"title-{i}": 24 for i in range(1, 7)},
}
PROBE_SLOTS = {"build": 12, "probe-text": 18}

_checks = []


def check(ok: bool, label: str) -> bool:
    _checks.append((bool(ok), label))
    return bool(ok)


def ceilings_still_gone() -> list:
    """Names ps2ui.h must NOT define any more.

    Asserted from this side rather than assumed, because the failure it
    guards against is silent: reinstating a ceiling in the header would
    make this example unloadable the day it grows a seventeenth slot,
    and nothing else here reads the header at all."""
    with open(PS2UI_H, encoding="utf-8") as fh:
        src = fh.read()
    return [name for name in ("PS2UI_MAX_TEXTURES", "PS2UI_MAX_SLOTS",
                              "PS2UI_MAX_SCREENS")
            if re.search(rf"^#define\s+{name}\s+(\d+)", src, re.M)]


def screen_focus(uib, sc):
    return uib.focus[sc["focus_first"]:sc["focus_first"] + sc["focus_count"]]


def screen_slots(uib, sc):
    return uib.slots[sc["slot_first"]:sc["slot_first"] + sc["slot_count"]]


def reachable(uib, sc):
    """Walk the D-pad graph from the screen's initial focus."""
    lo = sc["focus_first"]
    hi = lo + sc["focus_count"]
    seen = {sc["initial"]}
    queue = [sc["initial"]]
    while queue:
        node = uib.focus[queue.pop()]
        for edge in ("up", "down", "left", "right"):
            nxt = node[edge]
            if nxt == FOCUS_NONE or not lo <= nxt < hi or nxt in seen:
                continue
            seen.add(nxt)
            queue.append(nxt)
    return {uib.focus[i]["name"] for i in seen}


def main(path: str) -> int:
    uib = read_uib(path)  # raises on bad magic/version/CRC/feature bits

    # --- what ps2ui_load() will actually accept ----------------------
    back = ceilings_still_gone()
    check(not back,
          f"no table ceilings in ps2ui.h (found: {', '.join(back)})"
          if back else "no table ceilings in ps2ui.h")
    for count, what in ((len(uib.textures), "textures"),
                        (len(uib.slots), "slots"),
                        (len(uib.screens), "screens")):
        check(count <= 0xFFFF,
              f"{count} {what} fit the format's uint16 count field")
    # PS2UI_SLOT_BUFSZ is gone (v6 resource model): the runtime sizes
    # each slot's storage from the capacity declared in the blob, so a
    # large capacity costs arena bytes instead of making the blob
    # unloadable. There is no cap left to assert from this side.

    check((uib.canvas_w, uib.canvas_h) == CANVAS,
          f"canvas is {CANVAS[0]}x{CANVAS[1]} NTSC")
    names = [sc["name"] for sc in uib.screens]
    check(names == ["games", "probe"],
          f"two screens in document order: {names}")
    check(uib.feature_flags & FEAT_DYNAMIC_TEXT, "dynamic-text feature bit set")
    if names != ["games", "probe"]:
        return report()
    games, probe = uib.screens

    # --- focus graph -------------------------------------------------
    for sc, want in ((games, GAMES_FOCUS), (probe, PROBE_FOCUS)):
        got = [n["name"] for n in screen_focus(uib, sc)]
        check(got == want, f"{sc['name']}: focusables {want}")
        check(reachable(uib, sc) == set(want),
              f"{sc['name']}: every focusable reachable by D-pad")

    initial = uib.focus[games["initial"]]["name"]
    check(initial == "game-aurora",
          f"games opens on the first cover (got {initial})")
    check(uib.focus[probe["initial"]]["name"] == "probe-alpha",
          "probe opens on its first cell")

    # --focus-wrap was passed for probe only: the browser must dead-end
    # at its edges, the probe must come back around.
    by_name = {n["name"]: n for n in uib.focus}
    check(by_name["game-aurora"]["left"] == FOCUS_NONE,
          "games does not wrap: left off the first cover dead-ends")
    check(by_name["probe-type"]["right"] != FOCUS_NONE,
          "probe wraps: right off the last column comes back around")

    # --- dynamic text ------------------------------------------------
    for sc, want in ((games, GAMES_SLOTS), (probe, PROBE_SLOTS)):
        got = {s["name"]: s["capacity"] for s in screen_slots(uib, sc)}
        check(got == want, f"{sc['name']}: {len(want)} slots with the "
                           f"declared capacities")
        check(all(s["placeholder"] for s in screen_slots(uib, sc)),
              f"{sc['name']}: every slot ships a placeholder")

    # --- images ------------------------------------------------------
    covers = [t for t in uib.textures
              if t.fmt == gs.PSMT8 and t.clut is not None and t.width < 200]
    check(len(covers) >= 6, f"six palettized covers (PSMT8 + CLUT), got "
                            f"{len(covers)}")
    card = [t for t in uib.textures if (t.width, t.height) == (64, 48)]
    check(any(t.fmt == gs.PSMT8 for t in card)
          and any(t.fmt == gs.PSMCT32 for t in card),
          "probe card art baked both ways, PSMCT32 and PSMT8 + CLUT")

    # --- domain rules the bring-up checklist warns about --------------
    check(all(r.rgba[3] <= 0x80 for r in uib.records
              if r.op in (OP_QUAD, OP_TEXQUAD)),
          "every quad's alpha is in the GS 0-128 domain")
    check(all(max(r.rgba[:3]) <= 0x80 for r in uib.records
              if r.op == OP_TEXQUAD),
          "texquad colors are in the 0x80 modulate-identity domain")

    # --- CRT hygiene, re-checked on the blob rather than the IR -------
    hairlines = [r for r in uib.records
                 if r.op == OP_QUAD and (r.w == 1 or r.h == 1)]
    check(not hairlines,
          f"no 1px quads to shimmer on an interlaced CRT ({len(hairlines)} found)")

    # --- bring-up steps 4 and 5: the vanish rows ---------------------
    #
    # Text painted the same colour as the block behind it, so a correct
    # console renders nothing. That only tests anything while the two
    # colours actually match, and they match in different domains: the
    # block is a QUAD in full-range CSS RGB, the glyphs are a TEXQUAD in
    # the GS 0x80-identity modulate domain. A CSS edit that nudged
    # either would leave text permanently legible and read as a
    # hardware fault forever.
    #
    # The third row must NOT match, or "I see no text" and "this cell
    # draws no text" become the same observation and the first two rows
    # prove nothing.
    VANISH = ((0x7a, 0x5c, 0x3e), (0x3e, 0x6a, 0x7a))
    CONTROL_INK = (0xd0, 0xd8, 0xe4)

    for css in VANISH:
        want = tuple(css_channel_to_gs(c) for c in css)
        hexc = "#%02x%02x%02x" % css
        # The block must be an untextured QUAD. A border-radius would
        # make it a nine-patch, which reaches the framebuffer through
        # TEX MODULATE just like the glyphs -- a domain error would then
        # scale both by the same factor, the text would vanish anyway,
        # and this cell would pass on broken hardware. The two must
        # arrive by different paths or the comparison is vacuous.
        # Asserting OP_QUAD *is* the untextured assertion: a rounded
        # block bakes as nine textured pieces and no flat quad of this
        # colour survives at all, so this check fires on exactly that.
        #
        # A separate "no TEXQUAD covers the block" check lived here for
        # one commit and could never fail -- it matched the block's own
        # 115px-wide geometry, which a nine-patch never emits, since it
        # splits into corners and edges. Deleted rather than repaired:
        # the property is already covered, and a check that cannot fail
        # is worse than no check, because it reads like coverage.
        block = [r for r in uib.records
                 if r.op == OP_QUAD and r.rgba[:3] == css]
        ink = [r for r in uib.records
               if r.op == OP_TEXQUAD and r.rgba[:3] == want]
        check(bool(block) and bool(ink),
              f"vanish row {hexc}: untextured block and tinted glyphs "
              f"both baked ({len(block)} block, {len(ink)} glyph)")
        # Existence is not the property; the glyphs have to sit ON the
        # block. A future edit that moved the text out of its row would
        # leave both records present, both matched, and the cell testing
        # nothing at all -- text on the canvas ground is legible whatever
        # the modulate domain does.
        on_block = [g for g in ink
                    if any(b.x <= g.x and g.x + g.w <= b.x + b.w
                           and b.y <= g.y and g.y + g.h <= b.y + b.h
                           for b in block)]
        check(len(on_block) == len(ink),
              f"vanish row {hexc}: every glyph sits inside its block "
              f"({len(on_block)}/{len(ink)})")

    want_ctl = tuple(css_channel_to_gs(c) for c in CONTROL_INK)
    ctl = [r for r in uib.records
           if r.op == OP_TEXQUAD and r.rgba[:3] == want_ctl]
    check(bool(ctl), "the control row's glyphs are baked")
    check(want_ctl not in [tuple(css_channel_to_gs(c) for c in v)
                           for v in VANISH],
          "and its ink does not match either block, so it must be "
          "legible when the vanish rows are not")

    # --- bring-up step 3: the CSM1 swizzle tile ----------------------
    #
    # The CLUT ships linearly and the runtime permutes it on upload,
    # swapping bits 3 and 4 of the index. The tile is built so a correct
    # permutation renders it flat with one stripe at the right, and a
    # wrong one puts a stripe at 1/6 (bit 3) or 3/6 (bit 4).
    #
    # None of that survives unless the construction does, and the
    # construction lives in a PNG that nothing else validates. In
    # particular the TRAP entries have to differ from the probe entries:
    # if linear[16] ever equalled linear[8], a bit-3 fault would render
    # identically to a correct upload and the probe could not fail.
    swz_ix = [i for i, t in enumerate(uib.textures)
              if t.fmt == gs.PSMT8 and (t.width, t.height) == (96, 20)]
    swz = [uib.textures[i] for i in swz_ix]
    check(len(swz) == 1, f"the swizzle tile baked as PSMT8 ({len(swz)} found)")
    if len(swz) == 1:
        tile = swz[0]
        check(sorted(set(tile.data)) == [0, 1, 2, 8, 32, 48],
              f"and kept its authored indices "
              f"({sorted(set(tile.data))})")

        # ORDER, not just membership. The whole diagnostic is that a
        # stripe's position names the failing bit, and the position is
        # the region order -- so validating the palette exhaustively
        # while ignoring the geometry validates everything about this
        # instrument except the property it is read by.
        #
        # Reordering REGIONS to [0, 32, 8, 2, 1, 48] passed all 42
        # checks while moving the calibration stripe off the right edge
        # and making every row of bringup.md's reading table wrong.
        cell = tile.width // 6
        first = tile.data[:tile.width]
        order = [first[c * cell] for c in range(6)]
        check(order == [0, 8, 32, 48, 1, 2],
              f"in the order the reading table depends on ({order})")

        # The ruler beneath has to have one segment per region and to
        # span the same width, or it stops being a ruler and becomes a
        # second thing to misread. Tied here rather than trusted,
        # because the tile's region count lives in a Python generator
        # and the ruler's lives in HTML -- two places that cannot see
        # each other. Drawn as untextured quads on purpose: the tile is
        # the thing under test, so its ruler must not share its path.
        ticks = [r for r in uib.records
                 if r.op == OP_QUAD and (r.w, r.h) == (14, 4)]
        check(len(ticks) == 6,
              f"the swizzle ruler has one segment per region "
              f"({len(ticks)} found, 6 regions)")
        if len(ticks) == 6:
            xs = sorted(r.x for r in ticks)
            # STRIDE, not total span. Six 14px segments with 2px gaps
            # cover 94px under a 96px tile -- the trailing gap is not
            # drawn -- so a span equality is simply false, and asserting
            # it would have meant loosening the check until it passed.
            # Stride is the property alignment actually depends on: one
            # segment per region, starting where the region starts.
            strides = {xs[i + 1] - xs[i] for i in range(5)}
            check(strides == {cell},
                  f"one ruler segment per {cell}px region "
                  f"(strides {sorted(strides)})")
            swzq = [r for r in uib.records
                    if r.op == OP_TEXQUAD and r.tex == swz_ix[0]]
            check(len(swzq) == 1 and xs[0] == swzq[0].x,
                  f"and the ruler starts where the tile does "
                  f"(ruler x={xs[0]}, tile x="
                  f"{swzq[0].x if len(swzq) == 1 else '?'})")
        # And every pixel of a region has to match that region's
        # sample, not merely be uniform along its own row. The first
        # version of this check tested each region-row independently,
        # which a per-row shuffle satisfies while rendering six stripes
        # that change down the tile -- uniform on every line, wrong
        # everywhere. The order sample is taken from row 0, so the
        # property is that the rest of the tile agrees with row 0.
        solid = all(
            tile.data[r * tile.width + x] == order[c]
            for c in range(6)
            for x in range(c * cell, (c + 1) * cell)
            for r in range(tile.height)
        )
        check(solid,
              "and every region is that index all the way down, so the "
              "sample above describes the whole tile")
        clut = uib.cluts[tile.clut]

        def entry(i):
            return tuple(clut[i * 4:i * 4 + 3])

        probes = (0, 8, 32, 48, 1)
        check(len({entry(i) for i in probes}) == 1,
              f"every probe index carries one colour "
              f"({sorted({entry(i) for i in probes})})")
        # The three that must differ, and why each one matters:
        #   16 is where index 8 lands if bit 3 is not swapped
        #   40 is where index 48 lands if bit 4 is not swapped
        #   2 is the calibration, which no permutation can reach
        for trap, probe, what in ((16, 8, "bit 3"), (40, 48, "bit 4"),
                                  (2, 1, "the calibration")):
            check(entry(trap) != entry(probe),
                  f"{what}: linear[{trap}] differs from linear[{probe}], "
                  f"so a fault there is visible")

    # --- bring-up step 7's instrument (data-keep) --------------------
    #
    # A PAIR of magenta quads, and the pair is the instrument -- one
    # alone is not. `.tell` sits outside .scissor's clip, so the GS must
    # suppress it; `.tell-twin` sits inside, so the GS must draw it.
    #
    # Without the twin, "no magenta on screen" means either the scissor
    # worked or the quad never drew, and the cell cannot say which. Not
    # a hypothetical: both bake at alpha 0x80, and until the GS blend
    # equation was asserted every quad at that alpha composited to
    # background -- so this cell read "scissor works" on a console where
    # the scissor was doing nothing whatsoever.
    #
    # Classified with clip.py's own stack walk rather than a predicate
    # written here. The one this replaces asked whether some clip
    # CONTAINED the quad, which is not the question: a quad straddling
    # a clip edge is contained by nothing, so it was filed "outside" and
    # passed while 84 of its pixels rendered. With the twin in place
    # that stops being a confusing result and becomes a confident wrong
    # verdict -- a sliver of magenta beside the twin reads as "both
    # visible", which the table below calls a hardware fault.
    #
    # can_draw() asks the real question, intersection not containment,
    # and the walk tracks push/pop nesting inside this screen only. The
    # old version compared against every OP_SCISSOR_PUSH in the blob,
    # the games screen included, so a clip belonging to another screen
    # could flip the classification.
    tell = [i for i, r in enumerate(uib.records)
            if r.rgba[:3] == (255, 0, 255)]
    check(len(tell) == 2,
          f"the scissor tell pair survived the trim ({len(tell)} found)")
    if len(tell) == 2:
        # Effective clip for every record, per screen, exactly as the
        # baker's trim computes it.
        effective = {}
        for sc in uib.screens:
            stack = [(0, 0, uib.canvas_w, uib.canvas_h)]
            lo = sc["cmd_first"]
            for i in range(lo, lo + sc["cmd_count"]):
                r = uib.records[i]
                if r.op == OP_SCISSOR_PUSH:
                    stack.append(intersect(stack[-1], r.x, r.y, r.w, r.h))
                elif r.op == OP_SCISSOR_POP:
                    if len(stack) > 1:
                        stack.pop()
                else:
                    effective[i] = stack[-1]

        drawable = [i for i in tell
                    if i in effective and can_draw(uib.records[i], effective[i])]
        hidden = [i for i in tell if i not in drawable]
        check(len(drawable) == 1 and len(hidden) == 1,
              f"one quad the scissor must hide and one it must draw "
              f"({len(hidden)} hidden, {len(drawable)} drawable)")
        if len(drawable) == 1 and len(hidden) == 1:
            t, twin = uib.records[hidden[0]], uib.records[drawable[0]]
            check(t.x + t.w <= uib.canvas_w and t.y + t.h <= uib.canvas_h,
                  f"the hidden one is inside the canvas, so the scissor "
                  f"is what must hide it (x={t.x}..{t.x + t.w})")
            check(twin.x + twin.w <= uib.canvas_w
                  and twin.y + twin.h <= uib.canvas_h,
                  "and the visible one is on screen, so its absence "
                  "would mean the quad never drew")
            check((t.w, t.h) == (twin.w, twin.h),
                  f"both are the same size ({t.w}x{t.h}), so only "
                  f"position distinguishes them")
            # Clearance, not just correctness. The layout that puts
            # .tell outside its clip has drifted twice already -- once
            # when the twin was added, once when the runner's copy
            # changed length -- and a quad one pixel clear of the edge
            # is a quad that will be inside it after the next edit.
            clip = effective[hidden[0]]
            gap = clip[0] + clip[2] - t.x
            check(gap <= -12,
                  f"and clears the clip edge by {-gap}px, so an ordinary "
                  f"layout edit cannot walk it back inside")

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
