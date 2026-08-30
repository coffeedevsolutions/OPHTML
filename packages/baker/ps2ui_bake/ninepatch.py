"""Nine-patch generation for rounded-rect chrome.

A rounded rectangle cannot be drawn with untextured GS sprites, and
rasterizing every panel at full size would blow the 4 MB of VRAM on
backgrounds alone. Instead each distinct style becomes one small square
patch, 4x supersampled for the corner arcs, sliced into nine cells:

        c  e  c        c = corner cell (cell x cell), drawn 1:1
        e  m  e        e = edge strip, stretched along one axis
        c  e  c        m = 1px middle, stretched both ways

Fills may be translucent, so the patch carries real alpha and the
slices butt exactly -- overlapping slices would double-blend a seam.

COVERAGE, NOT COLOUR (P3b-6). A patch used to be premixed: fill and
border rasterized together into one RGBA image, drawn with an identity
tint. That put the colour in the TEXELS, where a tint table cannot
reach it -- so in opl-env 107 of 113 rects were unreachable by a theme,
and switching themes recoloured the text and left every panel dark.

Now a patch is a COVERAGE MASK -- how much of this texel the shape
covers, and nothing about what colour it is -- palettized to PSMT8
against the one shared coverage CLUT, exactly as a glyph atlas is. The
colour arrives as the vertex tint, which is a tint-table entry, which
is a thing a theme can move.

It is also much smaller, and that is the same trade the image path
makes: 8bpp plus one shared palette instead of 32bpp per texel. A patch
now keys on (radius, border_w) alone rather than on the colours too,
because coverage has no colour in it, so opl-env's 11 patch textures
collapse to 4. Each held 324-484 bytes of texels while occupying a full
8 KiB page, so that is 88 KiB of VRAM down to 32 KiB.

Deliberately NOT a per-theme CLUT swap, which was the other candidate.
A CLUT costs a full page, the same as the texture: an 11x11 patch would
carry 8 KiB of palette for 324 bytes of texels, once per colour
combination per theme. That is 176 KiB for two themes here and 88 KiB
more for each one after. CLUT swapping earns its keep on a 256x256
asset, where one page of palette covers 64 KiB of texels; it is
upside-down at this size.

THE TWO MASKS COME FROM ONE GEOMETRY, and they have to. Fill coverage
is the shape inset by the border; ring coverage is the outer shape
MINUS that same inset shape, computed pointwise at the same
supersample. So at the seam the two sum to the outer shape's coverage
and never to more -- rasterizing the ring independently would make an
antialiased corner blend twice and draw a dark hairline nobody
authored.
"""

from dataclasses import dataclass

from PIL import Image, ImageChops, ImageDraw

SUPERSAMPLE = 4


# Which of the two masks a coverage patch holds.
COVERAGE_FILL = 0
COVERAGE_RING = 1


def patch_key(radius: int, border_w: int, part: int):
    """A coverage patch is identified by its GEOMETRY and nothing else.

    The colours are gone from this key on purpose -- that is the whole
    saving. Two chips with different backgrounds and the same corner
    radius were two textures and are now one.
    """
    return (radius, border_w, part)


@dataclass
class NinePatch:
    cell: int          # corner cell size in px
    image: "Image.Image"  # RGBA, CSS-domain alpha, (2*cell+1) square

    @property
    def size(self) -> int:
        return self.image.width

    def cell_empty(self, u, v, w, h) -> bool:
        """True when this source cell has no coverage anywhere.

        The ring mask's centre cell is the entire interior of the box,
        and the fill mask's is solid -- so this is what keeps the split
        from costing a second full-box textured draw per rounded
        element to composite a rectangle of zeros.
        """
        if w <= 0 or h <= 0:
            return True
        return not self.image.crop((u, v, u + w, v + h)).getbbox()


def _mask(size, s, radius, inset):
    """Coverage of a rounded rect inset by `inset` px, at 1x.

    Rendered at `s`x and area-averaged down. BOX, not the LANCZOS the
    premixed patch used, because a coverage fraction IS an area
    average and BOX is the filter that computes one. A windowed-sinc
    filter resamples, which is a different job: measured over these
    shapes it preserves the rasterized area to within 0.47 px^2 where
    BOX is within 0.02, so it can invent or destroy half a pixel of
    rounded corner.

    NOT for the reason the first version of this comment gave. It
    claimed LANCZOS would make fill + ring sum past full coverage --
    falsified immediately: ring is `subtract(outer, inner)`, which
    clamps at zero, so fill + ring is bounded by max(inner, outer) and
    never exceeds 255 whatever the filter does. The seam is safe
    because of the subtraction, not because of the filter, and those
    are two independent properties that happened to be written as one.
    """
    if inset * 2 >= size:
        return Image.new("L", (size, size), 0)
    img = Image.new("L", (size * s, size * s), 0)
    ImageDraw.Draw(img).rounded_rectangle(
        (inset * s, inset * s, (size - inset) * s - 1, (size - inset) * s - 1),
        radius=max(radius - inset, 0) * s,
        fill=255,
    )
    return img.resize((size, size), Image.BOX)


def rasterize_coverage(radius: int, border_w: int, part: int) -> NinePatch:
    """A coverage mask for one half of a rounded box.

    COVERAGE_FILL is the shape inside the border; COVERAGE_RING is the
    border itself. Both come out of the same pair of rasterizations, so
    ring = outer - inner exactly and the two never sum past the outer
    shape at an antialiased corner.
    """
    cell = max(radius, border_w) + 1
    size = 2 * cell + 1
    outer = _mask(size, SUPERSAMPLE, radius, 0)
    inner = _mask(size, SUPERSAMPLE, radius, border_w)
    if part == COVERAGE_FILL:
        img = inner
    else:
        # Pointwise, and clamped at zero by ImageChops: a texel the
        # border covers is one the fill does not, and vice versa.
        img = ImageChops.subtract(outer, inner)
    return NinePatch(cell=cell, image=img)


def slice_quads(patch: NinePatch, x: int, y: int, w: int, h: int):
    """Yield (dst_rect, src_rect) pairs mapping the nine cells onto a
    w x h rectangle at (x, y). Rects are (x, y, w, h); src in patch
    texels. Cells clamp when the target is smaller than two corners."""
    c = min(patch.cell, w // 2, h // 2)
    size = patch.size
    pc = patch.cell

    xs = [(x, c), (x + c, w - 2 * c), (x + w - c, c)]
    ys = [(y, c), (y + c, h - 2 * c), (y + h - c, c)]
    su = [(0, c), (pc, size - 2 * pc), (size - c, c)]
    sv = [(0, c), (pc, size - 2 * pc), (size - c, c)]

    for row in range(3):
        for col in range(3):
            dw, dh = xs[col][1], ys[row][1]
            if dw <= 0 or dh <= 0:
                continue
            yield (
                (xs[col][0], ys[row][0], dw, dh),
                (su[col][0], sv[row][0], su[col][1], sv[row][1]),
            )
