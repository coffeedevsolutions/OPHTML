"""The blob-driven pen: text width from a baked font table.

WHY THIS IS ITS OWN MODULE. `slot_measure` in runtime/ps2ui.c walks a
slot's text against the glyph and kern tables the .uib carries, and
host-side tools need the same answer -- to check a readout fits, to
render a preview, to lint. Every one of them was reimplementing it.

The count reached FOUR: the layout pen, the baker's pen, the
previewer's `width_of`, and a private copy in examples/opl-env's
check.py written to verify that P3d's telemetry line fits its slot.
The first two are held together by the kerning agreement tests (F9e);
the last two were not held to anything, and the private copy was
making a claim -- "the widest line is 279px of 314" -- on arithmetic
nobody had checked.

That is the shape of the defect P3c's review found in vram.py one
commit earlier: a second implementation of someone else's arithmetic,
written beside a docstring asserting it matched. Structural sharing
beats an agreement test where it is available, and here it is.

THE RULES, and each is a place the copies could drift:

  * a codepoint with no glyph FALLS BACK TO '?', which is
    `find_glyph` at ps2ui.c:1183 and not the `if (!g) continue;` four
    lines further on. That `continue` is the fallback's FALLBACK: it
    fires only when '?' is itself absent from the atlas. The first
    version of this module read the `continue` and skipped, which made
    it the only one of the three pens that disagreed with the console
    -- short by one '?' advance per missing codepoint, in the
    direction that passes a line the console draws wider.
  * the kern stays keyed on the ORIGINAL codepoint, not on '?'. The
    caller never reassigns `cp` after the lookup, so a substituted
    glyph is drawn with '?' metrics and kerned as the character the
    author actually wrote.
  * the junction cost between two glyphs is letter_spacing PLUS the
    pair's kern, and there is no junction before the first glyph.
  * width accumulates advances, not bearings or ink extents.

Ellipsis fitting is deliberately NOT here. `slot_measure` also decides
where to cut and what the ellipsis costs at that cut, which no host
caller has needed yet, and a half-ported version of that would be
worse than none.
"""


def slot_width(text, glyphs, kerns, letter_spacing=0):
    """Width in pixels of `text` under a baked font's tables.

    `glyphs` maps codepoint -> {"advance": int, ...} and `kerns` maps
    (prev, cur) -> int, which is exactly what uib.read_uib returns for
    a font entry.
    """
    width = 0
    prev = None
    fallback = glyphs.get(ord("?"))
    for ch in text:
        cp = ord(ch)
        g = glyphs.get(cp)
        if g is None:
            g = fallback          # ps2ui.c:1183, not the continue below
        if g is None:
            continue              # '?' absent too: the fallback's fallback
        if prev is not None:
            width += letter_spacing + kerns.get((prev, cp), 0)
        width += g["advance"]
        prev = cp                 # the ORIGINAL cp, as the runtime keeps it
    return width
