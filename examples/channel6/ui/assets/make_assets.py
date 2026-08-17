#!/usr/bin/env python3
"""Regenerate this example's art.

The art is committed, so you only need this when you want to change it —
it exists so the example stays reproducible instead of carrying opaque
binaries. Deliberately few colors: `card.png` is drawn twice on the probe
screen, once as PSMCT32 and once with the `palettize` attribute, and the
two must be indistinguishable at 8-bit + CLUT.

    python3 examples/channel6/ui/assets/make_assets.py

Art lives next to the HTML document because that is where `<img src>`
resolves from (see the README's Images section).
"""

import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))

BODY = (36, 49, 78, 255)
EDGE = (79, 143, 208, 255)
LABEL = (159, 232, 214, 255)
PORT = (14, 21, 38, 255)
CLEAR = (0, 0, 0, 0)


def card(path: str, w: int = 64, h: int = 48) -> None:
    """A memory-card silhouette: rounded body, connector notch, label."""
    img = Image.new("RGBA", (w, h), CLEAR)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([2, 2, w - 3, h - 3], radius=5, fill=BODY, outline=EDGE, width=2)
    # Connector end (left), then the label patch (right).
    d.rectangle([6, 12, 16, h - 13], fill=PORT)
    for y in range(14, h - 13, 3):
        d.rectangle([7, y, 15, y], fill=EDGE)
    d.rounded_rectangle([22, 10, w - 8, h - 11], radius=3, fill=LABEL)
    d.rectangle([26, 16, w - 12, 17], fill=BODY)
    d.rectangle([26, 22, w - 16, 23], fill=BODY)
    d.rectangle([26, 28, w - 20, 29], fill=BODY)
    img.save(path)
    colors = img.getcolors(maxcolors=1 << 16) or []
    print(f"{path}: {img.size[0]}x{img.size[1]}, {len(colors)} distinct colors")


if __name__ == "__main__":
    card(os.path.join(HERE, "card.png"))
