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

from PIL import ImageFont

from . import __version__

# Latin-1 printable + the punctuation the example UI actually uses.
# chr(32) explicitly: an invisible U+00A0 once impersonated the space
# in this literal and every space advance fell back to '?' width. A
# codepoint number cannot be corrupted by an editor.
DEFAULT_CHARSET = (
    chr(32) + string.printable.strip()
    + " ·–—‘’“”…×△○□◇✕✓←→↑↓"
)


# Kerning is measured, not read from a table: shaping "AV" and
# subtracting "A" and "V" asks HarfBuzz the same question for a GPOS
# font, a legacy `kern` font and anything else it understands, and
# whatever it answers is what we record.
#
# Substitutions must be off for that to be true. With default features
# DejaVu shapes "ff" as one ligature glyph 15 units narrower than f + f,
# and the pen -- which draws two separate glyphs -- would then be handed a
# kern that does not exist. Positioning (kern/GPOS) is what we want;
# ligatures, contextual alternates and the rest are substitutions.
NO_SUBSTITUTION = {"liga": False, "clig": False, "dlig": False,
                   "hlig": False, "rlig": False, "calt": False}


# WHY HarfBuzz DIRECTLY, AND NOT PILLOW'S RAQM ENGINE ANY MORE (F47).
#
# This file used to measure through `ImageFont.getlength(features=...)`,
# which needs Pillow's Raqm layout engine, which needs fribidi, which
# no Pillow wheel bundles: Pillow loads it from the machine at run
# time. So on a stock Mac or Windows box the first command of the
# tutorial refused, over a bidirectional-text library this tool never
# needed -- the default charset is Latin, where bidi does nothing --
# and the remedy was a system package the reader had to go and find.
# Four functions of platform-specific advice existed only to say so.
#
# uharfbuzz is the same shaper Raqm drives, as a wheel for every
# platform pip serves, with no system half. Driven at the same 1000px
# em with the same substitutions off, it reproduces what Raqm measured
# exactly: both committed DejaVu tables pair for pair (284 and 163
# pairs, 115 advances each), and zero differences across 45 other
# faces, two more rebuilt to carry their kerning only in a legacy
# `kern` table, and a Greek, Cyrillic, Hebrew, Arabic, Thai and
# Japanese charset on the faces that cover it.
#
# THE FLOOR IN pyproject.toml IS 0.51.7 because it is the newest
# uharfbuzz with Python 3.9 wheels, which this package still supports,
# and it was measured to the same result as 0.56.2: pip on 3.9 lands
# on it, so it is the version a 3.9 reader actually runs.
#
# IMPORTED HERE RATHER THAN AT THE TOP, so a checkout that has not
# installed it loses this one command, with a sentence saying why,
# rather than every command that happens to import this module.
def _shaper(ttf_path, em):
    """A function returning the advance of a string, in pixels at `em`.

    26.6 fixed point, like FreeType's pixel sizes: the scale is em * 64
    and the sum is divided back out, so rounding happens once, in the
    caller, exactly where it happened when Pillow did the arithmetic.
    The font is read into memory rather than opened by path, because a
    path HarfBuzz opens itself goes through the C runtime's idea of the
    filename encoding, and Windows paths are where that has bitten
    this project before.
    """
    try:
        import uharfbuzz as hb
    except ImportError:
        raise SystemExit(
            "ps2ui-fontgen: needs the uharfbuzz package, which `pip "
            "install ophtml` installs. From a checkout, install it "
            "yourself: pip install uharfbuzz")
    with open(ttf_path, "rb") as fh:
        font = hb.Font(hb.Face(hb.Blob(fh.read())))
    font.scale = (em * 64, em * 64)

    def length(text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, NO_SUBSTITUTION)
        return sum(p.x_advance for p in buf.glyph_positions) / 64
    return length


def build_kerning(length, charset) -> dict:
    """{"cp_prev,cp_cur": units} for every pair the shaper adjusts.

    O(n^2) in the charset, which is ~13k shapes for the default 115
    glyphs -- a fraction of a second, once, at font-build time.
    """
    chars = [c for c in sorted(set(charset)) if ord(c) >= 32]
    widths = {c: length(c) for c in chars}
    kerning = {}
    for a in chars:
        wa = widths[a]
        for b in chars:
            k = length(a + b) - wa - widths[b]
            k = int(round(k))
            if k:
                kerning[f"{ord(a)},{ord(b)}"] = k
    return kerning


def build_metrics(ttf_path: str, family: str, weight: int, charset: str = DEFAULT_CHARSET) -> dict:
    em = 1000
    font = ImageFont.truetype(ttf_path, em)
    ascent, descent = font.getmetrics()
    length = _shaper(ttf_path, em)
    advances = {}
    for ch in sorted(set(charset)):
        cp = ord(ch)
        if cp < 32:
            continue
        advances[str(cp)] = int(round(length(ch)))
    return {
        "family": family,
        "weight": weight,
        "unitsPerEm": em,
        "ascent": ascent,
        "descent": descent,
        "advances": advances,
        "kerning": build_kerning(length, charset),
        "missing": advances.get(str(ord("?")), 500),
        "source": ttf_path.rsplit("/", 1)[-1],
    }


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    # First, and before anything that imports a dependency: asking a
    # tool what it is must not be able to fail for an unrelated reason.
    if argv and argv[0] in ("--version", "-V"):
        print("ps2ui-fontgen %s" % __version__)
        return 0
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
