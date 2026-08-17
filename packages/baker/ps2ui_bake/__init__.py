"""ps2ui-bake: turns the ui.json IR into a .uib blob the PS2 runtime replays.

Stages inside this package:

    fontgen   TTF -> metrics JSON (the seam shared with @ps2ui/layout)
    atlas     glyph atlases per (weight, size), 8-bit coverage + CLUT
    ninepatch rounded-rect chrome -> 9-sliced RGBA patches
    quads     IR commands -> flat GS quad records
    uib       binary .uib writer / reader
    preview   replays a baked blob to PNG, montages focus states

The one rule: everything the console would otherwise compute happens here.
"""

__version__ = "0.1.0"

from .rounding import round_half_up, css_alpha_to_gs, gs_alpha_to_css  # noqa: F401
