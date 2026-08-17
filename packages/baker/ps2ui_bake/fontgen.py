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

# Latin-1 printable + the punctuation the example UI actually uses.
# chr(32) explicitly: an invisible U+00A0 once impersonated the space
# in this literal and every space advance fell back to '?' width. A
# codepoint number cannot be corrupted by an editor.
DEFAULT_CHARSET = (
    chr(32) + string.printable.strip()
    + " ·–—‘’“”…×△○□◇✕✓←→↑↓"
)


def build_metrics(ttf_path: str, family: str, weight: int, charset: str = DEFAULT_CHARSET) -> dict:
    em = 1000
    font = ImageFont.truetype(ttf_path, em)
    ascent, descent = font.getmetrics()
    advances = {}
    for ch in sorted(set(charset)):
        cp = ord(ch)
        if cp < 32:
            continue
        advances[str(cp)] = int(round(font.getlength(ch)))
    return {
        "family": family,
        "weight": weight,
        "unitsPerEm": em,
        "ascent": ascent,
        "descent": descent,
        "advances": advances,
        "missing": advances.get(str(ord("?")), 500),
        "source": ttf_path.rsplit("/", 1)[-1],
    }


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
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
    print(f"ps2ui-fontgen: {len(metrics['advances'])} glyphs -> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
