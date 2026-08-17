"""Runtime table caps (backlog B10).

ps2ui.h sizes four tables statically, and ps2ui_load() rejects any blob
that exceeds them with PS2UI_ERR_TOO_MANY. Nothing on the host used to
know those numbers, so an over-sized blob would lay out, bake, preview
and pass every host test while being unloadable on console. The symptom
there is the sample ELF's solid red screen with no diagnostic.

The values are parsed out of runtime/ps2ui.h when it is reachable, so
raising a cap in the header raises it here too. FALLBACK covers the
pip-installed case where the runtime source is absent;
test_caps_match_header proves the two agree.
"""

import os
import re

FALLBACK = {
    "PS2UI_MAX_TEXTURES": 32,
    "PS2UI_MAX_SLOTS": 16,
    "PS2UI_MAX_SCREENS": 8,
    "PS2UI_SLOT_BUFSZ": 96,
}

_DEFINE = re.compile(r"^#define\s+(PS2UI_MAX_\w+|PS2UI_SLOT_BUFSZ)\s+(\d+)", re.M)


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


def check(textures, cluts, slots, screens, caps: dict = None):
    """Returns (errors, caps). Each error names the cap, the value, and
    the header constant to raise if the limit is the wrong one."""
    caps = caps or parse_header()
    errors = []

    def over(what, count, key):
        if count > caps[key]:
            errors.append(
                f"{what}: {count} exceeds {key} = {caps[key]}. "
                f"ps2ui_load() would return PS2UI_ERR_TOO_MANY. "
                f"Reduce the UI or raise {key} in runtime/ps2ui.h."
            )

    over("textures", len(textures), "PS2UI_MAX_TEXTURES")
    over("slots", len(slots), "PS2UI_MAX_SLOTS")
    over("screens", len(screens), "PS2UI_MAX_SCREENS")

    # Capacity is the runtime's per-slot buffer, NUL included.
    for sl in slots:
        if sl["capacity"] >= caps["PS2UI_SLOT_BUFSZ"]:
            errors.append(
                f"slot {sl['name']!r}: capacity {sl['capacity']} does not fit "
                f"PS2UI_SLOT_BUFSZ = {caps['PS2UI_SLOT_BUFSZ']} (NUL included). "
                f"Use data-slot-capacity <= {caps['PS2UI_SLOT_BUFSZ'] - 1}."
            )

    # CLUTs ride along with textures; flag the pressure before it bites.
    if len(cluts) > caps["PS2UI_MAX_TEXTURES"]:
        errors.append(
            f"cluts: {len(cluts)} exceeds PS2UI_MAX_TEXTURES = "
            f"{caps['PS2UI_MAX_TEXTURES']} (one CLUT slot per texture)."
        )
    return errors, caps


def summary(textures, cluts, slots, screens, caps: dict) -> str:
    return (
        f"  runtime tables: {len(textures)}/{caps['PS2UI_MAX_TEXTURES']} textures, "
        f"{len(slots)}/{caps['PS2UI_MAX_SLOTS']} slots, "
        f"{len(screens)}/{caps['PS2UI_MAX_SCREENS']} screens"
    )
