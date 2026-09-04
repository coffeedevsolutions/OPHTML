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
# 0.4.0.dev0 is the section opened after 0.3.0 shipped. It is a
# prerelease for the same reason 0.3.0 was one before its tag existed:
# the tree is past a release and is not yet the next one, so a bare
# 0.4.0 here would name a release nothing has tagged and rule 8 would
# fail this line for saying so.
#
# WHAT A PRERELEASE DOES AND DOES NOT PROTECT AGAINST is in
# docs/releasing.md. npm needs `publishConfig.tag = "next"` beside it,
# because `npm publish` moves `latest` to whatever the version says;
# that is rule 11, and it runs in both directions. pip's exclusion of
# prereleases bought nothing at all last time, because it lapses when
# no stable version exists -- 0.3.0 on PyPI is what ended that, so
# this is the first `.dev0` the exclusion actually protects.
__version__ = "0.4.0.dev0"

from .rounding import round_half_up, css_alpha_to_gs, gs_alpha_to_css  # noqa: F401
