"""ps2ui-fontgen: TTF -> metrics JSON.

The metrics file is the seam between the Node layout stage and this
package (see docs/architecture.md). Advances are stored in integer
font units normalized to 1000/em, obtained by measuring the face at
a 1000px em so hinting cannot perturb them differently at different
sizes. Both stages then derive pixel advances with the shared
round_half_up(units * size / 1000).
"""

import json
import string
import sys

from PIL import ImageFont, features

# Latin-1 printable + the punctuation the example UI actually uses.
# chr(32) explicitly: an invisible U+00A0 once impersonated the space
# in this literal and every space advance fell back to '?' width. A
# codepoint number cannot be corrupted by an editor.
DEFAULT_CHARSET = (
    chr(32) + string.printable.strip()
    + " ·–—‘’“”…×△○□◇✕✓←→↑↓"
)


# Kerning is measured, not read from a table, because Pillow exposes no
# kern/GPOS reader and this package's only dependency is Pillow. Measuring
# "AV" against "A" + "V" asks the same shaper the rasterizer will use, so
# whatever it does is what we record.
#
# Substitutions must be off for that to be true. With default features
# DejaVu shapes "ff" as one ligature glyph 15 units narrower than f + f,
# and the pen -- which draws two separate glyphs -- would then be handed a
# kern that does not exist. Positioning (kern/GPOS) is what we want;
# ligatures, contextual alternates and the rest are substitutions.
NO_SUBSTITUTION = ["-liga", "-clig", "-dlig", "-hlig", "-rlig", "-calt"]


def _shaping():
    """The `features` argument to pass Pillow, or None when it has no
    Raqm and would reject the argument rather than honour it."""
    return NO_SUBSTITUTION if features.check("raqm") else None


def build_kerning(font, charset) -> dict:
    """{"cp_prev,cp_cur": units} for every pair the shaper adjusts.

    O(n^2) in the charset, which is ~13k measurements for the default
    120 glyphs -- a fraction of a second, once, at font-build time.
    """
    feat = _shaping()
    if feat is None:
        # Without Raqm, Pillow applies no GPOS at all, so every pair
        # would measure zero. Say so rather than emitting an empty table
        # that is indistinguishable from a font with no kerns.
        print("ps2ui-fontgen: Pillow has no Raqm layout engine; "
              "kerning not extracted", file=sys.stderr)
        return {}

    chars = [c for c in sorted(set(charset)) if ord(c) >= 32]
    widths = {c: font.getlength(c, features=feat) for c in chars}
    kerning = {}
    for a in chars:
        wa = widths[a]
        for b in chars:
            k = font.getlength(a + b, features=feat) - wa - widths[b]
            k = int(round(k))
            if k:
                kerning[f"{ord(a)},{ord(b)}"] = k
    return kerning


def build_metrics(ttf_path: str, family: str, weight: int, charset: str = DEFAULT_CHARSET) -> dict:
    em = 1000
    font = ImageFont.truetype(ttf_path, em)
    ascent, descent = font.getmetrics()
    feat = _shaping()
    advances = {}
    for ch in sorted(set(charset)):
        cp = ord(ch)
        if cp < 32:
            continue
        advances[str(cp)] = int(round(font.getlength(ch, features=feat)))
    return {
        "family": family,
        "weight": weight,
        "unitsPerEm": em,
        "ascent": ascent,
        "descent": descent,
        "advances": advances,
        "kerning": build_kerning(font, charset),
        "missing": advances.get(str(ord("?")), 500),
        "source": ttf_path.rsplit("/", 1)[-1],
    }


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    # Hard requirement, checked before anything is written. Without Raqm
    # the advances come out identical and the kerning table comes out
    # empty -- a diff that deletes every pair while every test still
    # passes, because all three pens agree perfectly on zero kerning.
    # A metrics file that silently un-kerns the project is worse than
    # no metrics file.
    if not features.check("raqm"):
        print("ps2ui-fontgen: this Pillow has no Raqm layout engine, so "
              "kerning cannot be extracted; refusing to write a metrics "
              "file without it. Install a Pillow wheel built with Raqm "
              "(pip's manylinux wheels are).", file=sys.stderr)
        return 2
    if len(argv) < 4:
        print(
            "usage: python -m ps2ui_bake.fontgen <font.ttf> <family> <weight> <out.metrics.json> [charset-file]",
            file=sys.stderr,
        )
        return 2
    ttf, family, weight, out = argv[0], argv[1], int(argv[2]), argv[3]
    charset = DEFAULT_CHARSET
    if len(argv) > 4:
        with open(argv[4], encoding="utf-8") as fh:
            charset = fh.read()
    metrics = build_metrics(ttf, family, weight, charset)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"ps2ui-fontgen: {len(metrics['advances'])} glyphs, "
          f"{len(metrics['kerning'])} kern pairs -> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
