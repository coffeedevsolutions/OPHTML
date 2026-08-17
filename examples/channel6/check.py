#!/usr/bin/env python3
"""Verify the channel-6 blob's contract, straight off the baked file.

    PYTHONPATH=packages/baker python3 examples/channel6/check.py build/ui.uib

The memcard example ends in `make -C runtime test`, but that C test
asserts the memcard example's own focus and slot names, so it cannot
double as this example's check. This does the equivalent job on the
Python side: it re-reads the .uib (CRC, version and feature bits are
validated on the way in) and asserts what the console is entitled to
assume — screen names, the D-pad graph, slot names and capacities, the
palettized image, and the two domain rules the bring-up checklist warns
about (GS alpha 0-128, modulate RGB in the 0x80-identity domain).

Output is TAP, matching the runtime test, so the two read the same in a
build log. Exit status is 0 only when every check passes.
"""

import sys

from ps2ui_bake.quads import FOCUS_NONE, OP_QUAD, OP_TEXQUAD
from ps2ui_bake import gs
from ps2ui_bake.uib import FEAT_DYNAMIC_TEXT, read_uib

CANVAS = (640, 448)

OVERLAY_FOCUS = [
    "ch-1", "ch-2", "ch-3", "ch-4", "ch-5", "ch-6", "ch-7", "ch-8",
    "act-mount", "act-rename", "act-probe",
]
PROBE_FOCUS = [
    "probe-alpha", "probe-radius", "probe-type",
    "probe-clip", "probe-image", "probe-flex",
]
# name -> capacity, the buffer the runtime is allowed to write into.
OVERLAY_SLOTS = {
    "channel": 3, "card-name": 26, "card-sub": 30,
    "blocks": 18, "gameid": 18, "mode": 18, "autoboot": 18,
    **{f"ch{i}": 10 for i in range(1, 9)},
}
PROBE_SLOTS = {"build": 12, "probe-text": 18}

_checks = []


def check(ok: bool, label: str) -> bool:
    _checks.append((bool(ok), label))
    return bool(ok)


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

    check((uib.canvas_w, uib.canvas_h) == CANVAS,
          f"canvas is {CANVAS[0]}x{CANVAS[1]} NTSC")
    names = [sc["name"] for sc in uib.screens]
    check(names == ["overlay", "probe"],
          f"two screens in document order: {names}")
    check(uib.feature_flags & FEAT_DYNAMIC_TEXT, "dynamic-text feature bit set")
    if names != ["overlay", "probe"]:
        return report()
    overlay, probe = uib.screens

    # --- focus graph -------------------------------------------------
    for sc, want in ((overlay, OVERLAY_FOCUS), (probe, PROBE_FOCUS)):
        got = [n["name"] for n in screen_focus(uib, sc)]
        check(got == want, f"{sc['name']}: focusables {want}")
        check(reachable(uib, sc) == set(want),
              f"{sc['name']}: every focusable reachable by D-pad")

    initial = uib.focus[overlay["initial"]]["name"]
    check(initial == "ch-6", f"overlay opens focused on the mounted channel "
                             f"(ch-6, got {initial})")
    check(uib.focus[probe["initial"]]["name"] == "probe-alpha",
          "probe opens on its first cell")

    # --focus-wrap was passed for probe only: the overlay must dead-end
    # at its edges, the probe must come back around.
    by_name = {n["name"]: n for n in uib.focus}
    check(by_name["ch-1"]["left"] == FOCUS_NONE,
          "overlay does not wrap: left off the first chip dead-ends")
    check(by_name["probe-type"]["right"] != FOCUS_NONE,
          "probe wraps: right off the last column comes back around")

    # --- dynamic text ------------------------------------------------
    for sc, want in ((overlay, OVERLAY_SLOTS), (probe, PROBE_SLOTS)):
        got = {s["name"]: s["capacity"] for s in screen_slots(uib, sc)}
        check(got == want, f"{sc['name']}: {len(want)} slots with the "
                           f"declared capacities")
        check(all(s["placeholder"] for s in screen_slots(uib, sc)),
              f"{sc['name']}: every slot ships a placeholder")

    # --- images ------------------------------------------------------
    art = [t for t in uib.textures if (t.width, t.height) == (64, 48)]
    check(any(t.fmt == gs.PSMT8 and t.clut is not None for t in art),
          "card art baked once as PSMT8 + CLUT (palettize)")
    check(any(t.fmt == gs.PSMCT32 for t in art),
          "card art baked once as PSMCT32 (probe comparison)")

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
