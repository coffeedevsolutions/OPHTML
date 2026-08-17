"""PNG previewer.

Replays the *baked* command list — not the HTML, not the IR. Same quad
order, same scissor stack, same CLUT lookups, same 0..128 alpha domain
as the console runtime. In the absence of hardware this is the
verification story: if the preview is right and the runtime walks the
same records, the console is right up to gsKit itself.
"""

from PIL import Image

from . import gs
from .quads import (
    OP_QUAD, OP_TEXQUAD, OP_SCISSOR_PUSH, OP_SCISSOR_POP,
    STATE_ALWAYS, STATE_UNFOCUSED, STATE_FOCUSED, FOCUS_NONE,
)
from .rounding import gs_alpha_to_css
from .uib import UibFile


def _decode_texture(uib: UibFile, index: int) -> Image.Image:
    tex = uib.textures[index]
    if tex.fmt == gs.PSMCT32:
        img = Image.frombytes("RGBA", (tex.width, tex.height), tex.data)
        # GS alpha -> CSS alpha for Pillow compositing.
        r, g, b, a = img.split()
        a = a.point(lambda v: gs_alpha_to_css(min(v, 128)))
        return Image.merge("RGBA", (r, g, b, a))
    if tex.fmt == gs.PSMT8:
        clut = uib.cluts[tex.clut]
        # Linear CLUT: index i -> RGBA at i*4. The runtime uploads the
        # CSM1-permuted copy; the *lookup* result is identical.
        lut_r = bytes(clut[i * 4 + 0] for i in range(256))
        lut_g = bytes(clut[i * 4 + 1] for i in range(256))
        lut_b = bytes(clut[i * 4 + 2] for i in range(256))
        lut_a = bytes(gs_alpha_to_css(min(clut[i * 4 + 3], 128)) for i in range(256))
        idx = Image.frombytes("L", (tex.width, tex.height), tex.data)
        return Image.merge("RGBA", (
            idx.point(lut_r), idx.point(lut_g), idx.point(lut_b), idx.point(lut_a),
        ))
    raise ValueError(f"texture format {tex.fmt}")


def _state_visible(record, focus_current: int) -> bool:
    if record.state == STATE_ALWAYS:
        return True
    is_focused = record.focus != FOCUS_NONE and record.focus == focus_current
    return is_focused if record.state == STATE_FOCUSED else not is_focused


def _tint(img: Image.Image, rgba_gs) -> Image.Image:
    r, g, b, a_gs = rgba_gs
    a = gs_alpha_to_css(min(a_gs, 128))
    if (r, g, b, a) == (255, 255, 255, 255):
        return img
    # Modulate: texel x vertex color (the GS TEX_FUNCTION=MODULATE path,
    # where 0x80 vertex alpha is identity).
    ir_, ig, ib, ia = img.split()
    if r != 255:
        ir_ = ir_.point(lambda v: v * r // 255)
    if g != 255:
        ig = ig.point(lambda v: v * g // 255)
    if b != 255:
        ib = ib.point(lambda v: v * b // 255)
    if a != 255:
        ia = ia.point(lambda v: v * a // 255)
    return Image.merge("RGBA", (ir_, ig, ib, ia))


def render(uib: UibFile, focus_current: int = None, background=(10, 14, 26, 255)) -> Image.Image:
    """Replay to an RGBA image with the given focus-table index current."""
    if focus_current is None:
        focus_current = uib.initial_focus
    canvas = Image.new("RGBA", (uib.canvas_w, uib.canvas_h), background)
    tex_cache = {}
    scissors = [(0, 0, uib.canvas_w, uib.canvas_h)]

    def clip_rect(x, y, w, h):
        sx, sy, sw, sh = scissors[-1]
        x0, y0 = max(x, sx), max(y, sy)
        x1, y1 = min(x + w, sx + sw), min(y + h, sy + sh)
        return (x0, y0, x1 - x0, y1 - y0) if x1 > x0 and y1 > y0 else None

    for rec in uib.records:
        if rec.op == OP_SCISSOR_PUSH:
            c = clip_rect(rec.x, rec.y, rec.w, rec.h)
            scissors.append(c if c else (0, 0, 0, 0))
            continue
        if rec.op == OP_SCISSOR_POP:
            scissors.pop()
            continue
        if not _state_visible(rec, focus_current):
            continue

        if rec.op == OP_QUAD:
            c = clip_rect(rec.x, rec.y, rec.w, rec.h)
            if not c:
                continue
            r, g, b, a_gs = rec.rgba
            layer = Image.new("RGBA", (c[2], c[3]), (r, g, b, gs_alpha_to_css(min(a_gs, 128))))
            canvas.alpha_composite(layer, (c[0], c[1]))
            continue

        if rec.op == OP_TEXQUAD:
            if rec.tex not in tex_cache:
                tex_cache[rec.tex] = _decode_texture(uib, rec.tex)
            src = tex_cache[rec.tex].crop((rec.u0, rec.v0, rec.u1, rec.v1))
            if src.size != (rec.w, rec.h):
                src = src.resize((rec.w, rec.h), Image.BILINEAR)
            src = _tint(src, rec.rgba)
            c = clip_rect(rec.x, rec.y, rec.w, rec.h)
            if not c:
                continue
            if c != (rec.x, rec.y, rec.w, rec.h):
                src = src.crop((c[0] - rec.x, c[1] - rec.y,
                                c[0] - rec.x + c[2], c[1] - rec.y + c[3]))
            canvas.alpha_composite(src, (c[0], c[1]))
            continue

        raise ValueError(f"op {rec.op}")

    if len(scissors) != 1:
        raise ValueError("unbalanced scissor stack in command list")
    return canvas


def montage(uib: UibFile, columns: int = 3, gap: int = 16) -> Image.Image:
    """One tile per focusable, that focusable current — the couch QA
    view: every reachable focus state on one sheet."""
    states = [n["index"] for n in uib.focus] or [FOCUS_NONE]
    rows = (len(states) + columns - 1) // columns
    tile_w, tile_h = uib.canvas_w, uib.canvas_h
    sheet = Image.new("RGBA", (
        columns * tile_w + (columns + 1) * gap,
        rows * tile_h + (rows + 1) * gap,
    ), (0, 0, 0, 255))
    for i, st in enumerate(states):
        img = render(uib, focus_current=st)
        cx = gap + (i % columns) * (tile_w + gap)
        cy = gap + (i // columns) * (tile_h + gap)
        sheet.paste(img, (cx, cy))
    return sheet
