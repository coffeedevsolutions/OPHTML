#!/usr/bin/env python3
"""Verify the channel-6 blob's contract, straight off the baked file.

    PYTHONPATH=packages/baker python3 examples/channel6/check.py build/ui.uib

The memcard example ends in `make -C runtime test`, but that C test
asserts the memcard example's own focus and slot names, so it cannot
double as this example's check. This does the equivalent job on the
Python side: it re-reads the .uib (CRC, version and feature bits are
validated on the way in) and asserts what the console is entitled to
assume.

The first group covers the runtime's static table caps —
PS2UI_MAX_TEXTURES, PS2UI_MAX_SLOTS, PS2UI_MAX_SCREENS,
PS2UI_SLOT_BUFSZ — which ps2ui_load() enforces with PS2UI_ERR_TOO_MANY,
and whose console symptom is the sample ELF's red screen with no
diagnostic. Writing this example is what surfaced that gap; since B10
the baker refuses to write an over-cap blob at all, so these four are
now a second line of defence rather than the only one. They stay
because they cost nothing and they assert the property from the far
side of the file format: the baker checks what it is about to write,
this checks what a loader will actually find. Both read the numbers out
of ps2ui.h rather than copying them.
"""

import os
import re
import sys

from ps2ui_bake.quads import (FOCUS_NONE, OP_QUAD, OP_SCISSOR_PUSH,
                               OP_TEXQUAD)
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
    "probe-clip", "probe-image", "probe-aspect", "probe-flex",
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


def runtime_caps() -> dict:
    """Read the caps out of ps2ui.h so this file cannot drift from it."""
    with open(PS2UI_H, encoding="utf-8") as fh:
        src = fh.read()
    caps = {}
    for name in ("PS2UI_MAX_TEXTURES", "PS2UI_MAX_SLOTS",
                 "PS2UI_MAX_SCREENS", "PS2UI_SLOT_BUFSZ"):
        m = re.search(rf"^#define\s+{name}\s+(\d+)", src, re.M)
        if not m:
            raise SystemExit(f"error: {name} not found in {PS2UI_H}")
        caps[name] = int(m.group(1))
    return caps


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
    caps = runtime_caps()

    # --- what ps2ui_load() will actually accept ----------------------
    check(len(uib.textures) <= caps["PS2UI_MAX_TEXTURES"],
          f"{len(uib.textures)} textures within PS2UI_MAX_TEXTURES "
          f"({caps['PS2UI_MAX_TEXTURES']})")
    check(len(uib.slots) <= caps["PS2UI_MAX_SLOTS"],
          f"{len(uib.slots)} slots within PS2UI_MAX_SLOTS "
          f"({caps['PS2UI_MAX_SLOTS']})")
    check(len(uib.screens) <= caps["PS2UI_MAX_SCREENS"],
          f"{len(uib.screens)} screens within PS2UI_MAX_SCREENS "
          f"({caps['PS2UI_MAX_SCREENS']})")
    over = [s["name"] for s in uib.slots
            if s["capacity"] >= caps["PS2UI_SLOT_BUFSZ"]]
    check(not over, f"every slot capacity below PS2UI_SLOT_BUFSZ "
                    f"({caps['PS2UI_SLOT_BUFSZ']}): {over or 'ok'}")

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

    # --- bring-up step 7's instrument (data-keep) --------------------
    #
    # A magenta quad parked outside .scissor's clip. It survives the
    # dead-geometry trim only because of data-keep, and it is useful
    # only while two things stay true: it is outside the clip that must
    # suppress it, and inside the canvas so the framebuffer bounds are
    # not doing the job instead. Either drifting turns a positive test
    # for a negative into a quad that proves nothing, silently -- and
    # the previewer cannot tell you, because a working instrument and a
    # broken one both render as nothing.
    tell = [r for r in uib.records if r.rgba[:3] == (255, 0, 255)]
    check(len(tell) == 1,
          f"the scissor tell quad survived the trim ({len(tell)} found)")
    if len(tell) == 1:
        t = tell[0]
        clips = [r for r in uib.records if r.op == OP_SCISSOR_PUSH]
        covering = [c for c in clips
                    if c.x <= t.x and c.x + c.w >= t.x + t.w]
        check(not covering,
              f"and lies outside every clip rect (x={t.x}..{t.x + t.w})")
        check(t.x + t.w <= uib.canvas_w and t.y + t.h <= uib.canvas_h,
              "and inside the canvas, so the scissor is what must hide it")

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
