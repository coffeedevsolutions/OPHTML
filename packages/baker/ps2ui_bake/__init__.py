"""ps2ui-bake: turns the ui.json IR into a .uib blob the PS2 runtime replays.

Stages inside this package:

    fontgen   TTF -> metrics JSON (the seam shared with @ophtml/layout)
    atlas     glyph atlases per (weight, size), 8-bit coverage + CLUT
    ninepatch rounded-rect chrome -> 9-sliced RGBA patches
    quads     IR commands -> flat GS quad records
    uib       binary .uib writer / reader
    preview   replays a baked blob to PNG, montages focus states

The one rule: everything the console would otherwise compute happens here.
"""

# THE ONE PLACE THIS PACKAGE'S VERSION IS WRITTEN. pyproject.toml reads
# it (`dynamic = ["version"]`), because from the 0.2.0 release onward
# this file said 0.1.0 while pyproject said 0.2.0 -- two numbers for one
# package, neither read by anything, so neither could be wrong out loud.
#
# `.dev0` is not decoration. There is no 0.2.0 tag and never was; the
# tree is past that release by four format moves (v4-v7) and is not the
# next one either. What a prerelease does and does NOT protect against
# is in docs/releasing.md -- pip's exclusion of prereleases lapses when
# no stable version exists, which is precisely the case here.
# tools/check-versions.py holds all of it together.
__version__ = "0.3.0.dev0"

from .rounding import round_half_up, css_alpha_to_gs, gs_alpha_to_css  # noqa: F401
