"""Nine-patch generation for rounded-rect chrome.

A rounded rectangle cannot be drawn with untextured GS sprites, and
rasterizing every panel at full size would blow the 4 MB of VRAM on
backgrounds alone. Instead each distinct (radius, border, fill, border
color) style becomes one small square patch, 4x supersampled for the
corner arcs, sliced into nine cells:

        c  e  c        c = corner cell (cell x cell), drawn 1:1
        e  m  e        e = edge strip, stretched along one axis
        c  e  c        m = 1px middle, stretched both ways

Fills may be translucent, so the patch carries real alpha and the
slices butt exactly — overlapping slices would double-blend a seam.
"""

from dataclasses import dataclass

from PIL import Image, ImageDraw

SUPERSAMPLE = 4


def patch_key(radius: int, border_w: int, fill, border_color):
    return (
        radius,
        border_w,
        tuple(fill) if fill else None,
        tuple(border_color) if border_color else None,
    )


@dataclass
class NinePatch:
    cell: int          # corner cell size in px
    image: "Image.Image"  # RGBA, CSS-domain alpha, (2*cell+1) square

    @property
    def size(self) -> int:
        return self.image.width


def rasterize_patch(radius: int, border_w: int, fill, border_color) -> NinePatch:
    """fill / border_color: RGBA in CSS domain (alpha 0..255) or None."""
    cell = max(radius, border_w) + 1
    size = 2 * cell + 1
    s = SUPERSAMPLE
    img = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    box = (0, 0, size * s - 1, size * s - 1)
    draw.rounded_rectangle(
        box,
        radius=radius * s,
        fill=tuple(fill) if fill else None,
        outline=tuple(border_color) if border_color and border_w > 0 else None,
        width=border_w * s,
    )
    img = img.resize((size, size), Image.LANCZOS)
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
