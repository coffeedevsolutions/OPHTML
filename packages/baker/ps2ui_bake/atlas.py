"""Glyph atlas baking.

One atlas per (weight, size) pair used by the document. Glyphs are
rasterized by FreeType (via Pillow) at the exact pixel size the layout
measured — never scaled on the GS, where bilinear filtering would turn
14px text into soup.

The atlas is PSMT8: each texel is a coverage value 0..255 indexing a
CLUT of white-with-alpha-ramp, and the runtime tints by vertex color
modulation. One atlas therefore serves every text color in the UI.

Glyph advances are re-derived from the *metrics JSON*, not from what
FreeType reports at this size — layout already positioned every line
using metrics advances, and the bitmap must follow the measurement, not
the other way around. The bitmap's own bearing places ink within the
advance box.
"""

import json
from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

from .rounding import glyph_advance_px, kern_px

ATLAS_WIDTH = 256  # GS-friendly; height grows in shelf packing


@dataclass
class Glyph:
    codepoint: int
    u: int
    v: int
    w: int
    h: int
    bearing_x: int  # ink offset from pen x
    bearing_y: int  # ink offset from the line-box top, measured via the
                    # METRICS ascent — see AtlasBuilder.add (backlog B2)
    advance: int    # px, from metrics — matches layout exactly


@dataclass
class Atlas:
    weight: int
    size: int
    image: "Image.Image"
    glyphs: dict = field(default_factory=dict)  # codepoint -> Glyph
    line_ascent: int = 0
    line_descent: int = 0


class AtlasBuilder:
    """Shelf-packs glyphs for one (weight, size)."""

    def __init__(self, ttf_path: str, metrics_path: str, weight: int, size: int):
        self.weight = weight
        self.size = size
        self.font = ImageFont.truetype(ttf_path, size)
        with open(metrics_path, encoding="utf-8") as fh:
            self.metrics = json.load(fh)
        self.image = Image.new("L", (ATLAS_WIDTH, 64), 0)
        self.draw = ImageDraw.Draw(self.image)
        self.glyphs = {}
        self.shelf_x = 1
        self.shelf_y = 1
        self.shelf_h = 0
        ascent, descent = self.font.getmetrics()
        self.ascent = ascent
        self.descent = descent
        # The layout stage positioned every line box using the METRICS
        # ascent (units -> px via the shared rounding rule). Pillow's
        # per-size ascent can differ by a pixel, so ink placement must
        # go through the metrics value or text drifts off its measured
        # box (backlog B2).
        self.metrics_ascent_px = glyph_advance_px(self.metrics["ascent"], size)
        self.kerning = self.metrics.get("kerning", {})

    def kern(self, prev_cp, cp: int) -> int:
        """Pixel kern applied before `cp` because `prev_cp` precedes it.

        Mirrors layout's Font.kernPx, including that the first glyph of
        a run is never kerned."""
        if prev_cp is None:
            return 0
        return kern_px(self.kerning.get(f"{prev_cp},{cp}", 0), self.size)

    def _grow(self, needed_h: int):
        if needed_h <= self.image.height:
            return
        h = self.image.height
        while h < needed_h:
            h *= 2
        grown = Image.new("L", (ATLAS_WIDTH, h), 0)
        grown.paste(self.image, (0, 0))
        self.image = grown
        self.draw = ImageDraw.Draw(self.image)

    def add(self, ch: str) -> Glyph:
        cp = ord(ch)
        if cp in self.glyphs:
            return self.glyphs[cp]

        adv_units = self.metrics["advances"].get(str(cp), self.metrics["missing"])
        advance = glyph_advance_px(adv_units, self.size)

        # Rasterize into a scratch tile and crop to ink.
        pad = 2
        tile_w = advance + self.size + 2 * pad
        tile_h = self.ascent + self.descent + 2 * pad
        tile = Image.new("L", (tile_w, tile_h), 0)
        ImageDraw.Draw(tile).text((pad, pad), ch, font=self.font, fill=255)
        bbox = tile.getbbox()
        if bbox is None:  # space & friends: advance with no ink
            g = Glyph(cp, 0, 0, 0, 0, 0, 0, advance)
            self.glyphs[cp] = g
            return g
        x0, y0, x1, y1 = bbox
        ink = tile.crop(bbox)
        w, h = ink.size

        if self.shelf_x + w + 1 > ATLAS_WIDTH:
            self.shelf_y += self.shelf_h + 1
            self.shelf_x = 1
            self.shelf_h = 0
        self._grow(self.shelf_y + h + 1)
        self.image.paste(ink, (self.shelf_x, self.shelf_y))

        # Pillow's default anchor puts the FreeType ascender at y=pad,
        # so (y0 - pad) is ink-below-PIL-ascender. Re-express it as
        # ink-below-baseline, then hang it from the metrics ascent that
        # layout actually measured with.
        ink_from_baseline = (y0 - pad) - self.ascent
        g = Glyph(
            codepoint=cp,
            u=self.shelf_x, v=self.shelf_y, w=w, h=h,
            bearing_x=x0 - pad,
            bearing_y=self.metrics_ascent_px + ink_from_baseline,
            advance=advance,
        )
        self.shelf_x += w + 1
        self.shelf_h = max(self.shelf_h, h)
        self.glyphs[cp] = g
        return g

    def build(self) -> Atlas:
        # Snap height up to the next multiple of 8 lest odd heights upset
        # GS transfer alignment.
        h = (self.image.height + 7) & ~7
        if h != self.image.height:
            self._grow(h)
        atlas = Atlas(self.weight, self.size, self.image, dict(self.glyphs))
        atlas.line_ascent = self.ascent
        atlas.line_descent = self.descent
        return atlas
