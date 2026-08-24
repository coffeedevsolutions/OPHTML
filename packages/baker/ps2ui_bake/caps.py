"""Runtime limits the bake has to know about (backlog B10).

Originally four table-count ceilings that ps2ui_load() rejected with
PS2UI_ERR_TOO_MANY. Three of them -- textures, slots, screens -- no
longer exist: once the v6 arena made the context size itself from the
blob, those numbers bounded nothing the blob's own size did not
already bound, and 16 slots was a real obstacle to a real UI (the UC-3
scoping fixture measures 28 on one OPL-class screen). The runtime now
refuses on arithmetic it cannot do rather than on a number ps2ui.h
picked; see arena_compute.

What remains is PS2UI_MAX_SCISSOR_DEPTH, which is genuine fixed
storage: ps2ui_render keeps a scissor stack that deep, and a blob
nesting `overflow: hidden` past it draws the inner subtree under the
outer clip. It fails soft, on a television, so the bake refuses it
here instead.

The value is parsed out of runtime/ps2ui.h when it is reachable, so
raising it in the header raises it here too. FALLBACK covers the
pip-installed case where the runtime source is absent;
test_caps_match_header proves the two agree.
"""

import os
import re

FALLBACK = {
    # The last one. It bounds how deep `overflow: hidden` may nest
    # before ps2ui_render runs out of scissor stack -- real storage,
    # unlike the table counts that used to sit beside it. The regex
    # already matched it; without the key here, caps.update silently
    # dropped it and nothing checked the depth at all.
    "PS2UI_MAX_SCISSOR_DEPTH": 8,
}

_DEFINE = re.compile(r"^#define\s+(PS2UI_MAX_\w+)\s+(\d+)", re.M)


def header_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "..", "runtime", "ps2ui.h"))


def parse_header(path: str = None) -> dict:
    """Caps from ps2ui.h, or FALLBACK when the header is not reachable."""
    path = path or header_path()
    try:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
    except OSError:
        return dict(FALLBACK)
    found = {m.group(1): int(m.group(2)) for m in _DEFINE.finditer(src)}
    caps = dict(FALLBACK)
    caps.update({k: v for k, v in found.items() if k in FALLBACK})
    return caps


def max_scissor_depth(records) -> int:
    """Deepest SCISSOR_PUSH nesting in a command list.

    The runtime keeps a fixed stack and cannot report an overflow. It
    fails soft — the too-deep subtree draws under the enclosing clip —
    but "your dialog is not clipped" is a poor thing to discover on a
    television, so the bake refuses it instead.
    """
    from .quads import OP_SCISSOR_POP, OP_SCISSOR_PUSH
    depth = peak = 0
    for rec in records:
        if rec.op == OP_SCISSOR_PUSH:
            depth += 1
            peak = max(peak, depth)
        elif rec.op == OP_SCISSOR_POP and depth > 0:
            depth -= 1
    return peak


def check(textures, cluts, slots, screens, caps: dict = None, records=None):
    """Returns (errors, caps). Each error names the cap, the value, and
    the header constant to raise if the limit is the wrong one."""
    caps = caps or parse_header()
    errors = []

    if records is not None:
        # >= because the runtime's guard is `depth + 1 >= MAX`, so the
        # last usable slot is MAX - 1.
        peak = max_scissor_depth(records)
        limit = caps["PS2UI_MAX_SCISSOR_DEPTH"]
        if peak >= limit:
            errors.append(
                f"scissor nesting: {peak} levels reaches "
                f"PS2UI_MAX_SCISSOR_DEPTH = {limit}. ps2ui_render has a "
                f"fixed stack and cannot report an overflow, so the "
                f"deepest subtree would draw under its parent's clip "
                f"instead of its own. Flatten the nesting or raise "
                f"PS2UI_MAX_SCISSOR_DEPTH in runtime/ps2ui.h."
            )

    # Textures, slots and screens used to be checked against ceilings
    # here. They are not bounded by a number any more -- only by the
    # format's own uint16 count fields, which the writer below cannot
    # exceed without failing to pack the header at all. What replaced
    # the ceilings is an arena the runtime refuses to carve if it does
    # not fit the target's address space, and the bake already reports
    # that arena in bytes, which is the number an integrator can act on.
    for what, count in (("textures", len(textures)), ("slots", len(slots)),
                        ("screens", len(screens)), ("cluts", len(cluts))):
        if count > 0xFFFF:
            errors.append(
                f"{what}: {count} does not fit the format's uint16 count "
                f"field. This is the format's own limit, not a runtime one."
            )

    # Capacity used to be checked against PS2UI_SLOT_BUFSZ, the
    # runtime's fixed per-slot buffer. There is no such buffer any more
    # (v6 resource model): the runtime sizes each slot's storage from
    # the capacity declared here, so a large capacity costs arena bytes
    # rather than being unloadable. The remaining bound is the format's
    # own -- capacity is a uint16 field.
    for sl in slots:
        if sl["capacity"] > 0xFFFF:
            errors.append(
                f"slot {sl['name']!r}: capacity {sl['capacity']} does not fit "
                f"the format's uint16 capacity field."
            )

    return errors, caps


def summary(textures, cluts, slots, screens, caps: dict) -> str:
    # Counts, not fractions. "15/16 slots" was a useful line while the
    # denominator was a wall you could hit; printing a fraction of
    # 65535 would just be a number with a decorative second half, and
    # the figure that actually constrains a UI now -- the arena -- is
    # printed on its own line by cli.py.
    del caps
    return (
        f"  runtime tables: {len(textures)} textures, {len(cluts)} CLUTs, "
        f"{len(slots)} slots, {len(screens)} screens"
    )
