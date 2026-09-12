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
# A `.dev0` here means the tree is past a release and is not yet the
# next one. A bare version would name a release nothing has tagged, and
# rule 8 fails this line for saying so; step 9 of docs/releasing.md puts
# the suffix back the moment a tag exists.
#
# WRITTEN WITHOUT NAMING VERSIONS ON PURPOSE. This comment used to
# explain the state in terms of the two numbers it was true of, and by
# 0.6.0.dev0 it still opened "0.4.0.dev0 is the section opened after
# 0.3.0 shipped" -- two generations stale, beside a literal that had
# moved twice. Raised in review at #112 and #116. Prose that restates a
# version rots every time the version moves; prose that states the rule
# does not, and the literal below is the only thing here that changes.
#
# WHAT A PRERELEASE DOES AND DOES NOT PROTECT AGAINST is in
# docs/releasing.md. npm needs `publishConfig.tag = "next"` beside it,
# because `npm publish` moves `latest` to whatever the version says;
# that is rule 11, and it runs in both directions. pip's exclusion of
# prereleases lapses when no stable version exists, so it bought nothing
# until the first real release was on PyPI.
__version__ = "0.7.0.dev0"

from .rounding import round_half_up, css_alpha_to_gs, gs_alpha_to_css  # noqa: F401
