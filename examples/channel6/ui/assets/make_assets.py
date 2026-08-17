#!/usr/bin/env python3
"""Regenerate this example's art.

The art is committed, so you only need this when you want to change it —
it exists so the example stays reproducible instead of carrying opaque
binaries. Everything is drawn from flat shapes with no antialiasing, so
each file stays far under 256 colors: the covers all bake with the
`palettize` attribute (PSMT8 + CLUT, a quarter of the VRAM per texel),
and `card.png` is drawn twice on the probe screen — once PSMCT32, once
palettized — where the two must be indistinguishable.

    python3 examples/channel6/ui/assets/make_assets.py

Art lives next to the HTML document because that is where `<img src>`
resolves from (see the README's Images section).
"""

import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))

COVER_W, COVER_H = 160, 96

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
    save(img, path)


# Six covers, six shape vocabularies, so a mis-ordered texture table is
# obvious at a glance instead of "one of the blue ones is wrong".
def bands(d, w, h, fg, accent):
    for i in range(-h, w, 26):
        d.polygon([(i, h), (i + 13, h), (i + 13 + h, 0), (i + h, 0)], fill=fg)
    d.rectangle([0, h - 14, w, h], fill=accent)


def grid(d, w, h, fg, accent):
    for x in range(12, w, 18):
        d.rectangle([x, 0, x + 1, h], fill=fg)
    for y in range(10, h, 16):
        d.rectangle([0, y, w, y + 1], fill=fg)
    d.rectangle([w // 2 - 12, h // 2 - 12, w // 2 + 12, h // 2 + 12], fill=accent)


def horizon(d, w, h, fg, accent):
    d.ellipse([w - 58, 12, w - 18, 52], fill=accent)
    d.rectangle([0, h - 34, w, h], fill=fg)
    for i, x in enumerate(range(8, w, 22)):
        d.rectangle([x, h - 34 - (6 + (i % 3) * 9), x + 12, h - 34], fill=fg)


def chevrons(d, w, h, fg, accent):
    for i in range(-1, 5):
        x = 10 + i * 34
        d.polygon([(x, 16), (x + 20, h // 2), (x, h - 16),
                   (x + 10, h - 16), (x + 30, h // 2), (x + 10, 16)], fill=fg)
    d.rectangle([0, 0, w, 8], fill=accent)


def wedge(d, w, h, fg, accent):
    d.polygon([(w // 2, 12), (w - 22, h - 16), (22, h - 16)], fill=fg)
    d.rectangle([w // 2 - 3, h - 16, w // 2 + 3, h], fill=accent)


def rings(d, w, h, fg, accent):
    cx, cy = w // 2, h // 2
    for i, r in enumerate((40, 28, 16)):
        d.ellipse([cx - r, cy - r // 1, cx + r, cy + r], outline=fg, width=4)
    d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=accent)


COVERS = [
    ("cover-aurora", (18, 26, 52), (48, 78, 140), (127, 208, 196), bands),
    ("cover-cartography", (12, 38, 40), (28, 74, 78), (232, 182, 76), grid),
    ("cover-harbor", (22, 28, 40), (46, 58, 82), (196, 206, 226), horizon),
    ("cover-turbo", (48, 34, 14), (152, 108, 40), (240, 214, 128), chevrons),
    ("cover-moth", (32, 20, 48), (92, 62, 132), (222, 176, 232), wedge),
    ("cover-kaiju", (40, 24, 26), (120, 66, 62), (226, 150, 108), rings),
]


def cover(path: str, bg, fg, accent, draw_fn) -> None:
    img = Image.new("RGBA", (COVER_W, COVER_H), bg + (255,))
    d = ImageDraw.Draw(img)
    draw_fn(d, COVER_W, COVER_H, fg + (255,), accent + (255,))
    # A 2px inner frame ties the six together as one set.
    d.rectangle([0, 0, COVER_W - 1, COVER_H - 1], outline=accent + (255,), width=2)
    save(img, path)


def save(img: Image.Image, path: str) -> None:
    img.save(path)
    colors = img.getcolors(maxcolors=1 << 16) or []
    print(f"{os.path.basename(path)}: {img.size[0]}x{img.size[1]}, "
          f"{len(colors)} colors")


if __name__ == "__main__":
    card(os.path.join(HERE, "card.png"))
    for name, bg, fg, accent, fn in COVERS:
        cover(os.path.join(HERE, f"{name}.png"), bg, fg, accent, fn)
