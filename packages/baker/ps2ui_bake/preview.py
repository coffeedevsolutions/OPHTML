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
from dataclasses import replace

from .uib import UibFile


def _decode_texture(uib: UibFile, index: int, fills: dict = None) -> Image.Image:
    """None for a streamed slot with nothing in it, which is what the
    runtime draws for one: ps2ui_render skips an unfilled slot and
    counts it in stats.tex_unfilled. Before this the previewer read
    tex.data unconditionally and Pillow raised "not enough image data"
    on any blob carrying a streamed slot -- the first blob that did was
    the streaming bench, months after the format shipped.

    `fills` supplies texels for a named slot exactly as ps2ui_tex_set
    does on the console: raw PSMCT32 of exactly width * height * 4
    bytes. That is what makes a filled console frame comparable against
    a preview at all."""
    tex = uib.textures[index]
    if getattr(tex, "kind", 0) and not tex.data:
        raw = (fills or {}).get(tex.name)
        if raw is None:
            return None
        need = tex.width * tex.height * 4
        if len(raw) != need:
            raise ValueError(
                f"slot {tex.name!r}: {len(raw)} bytes of texels for a "
                f"{tex.width}x{tex.height} PSMCT32 reservation ({need} B). "
                f"ps2ui_tex_set would return PS2UI_ERR_SIZE for this.")
        tex = replace(tex, data=raw)
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
    """GS TEX MODULATE: Cv = Ct * Cf >> 7, identity at 0x80, values
    above 0x80 overbright (and clamp). Every channel of a TEXQUAD
    vertex color is in that domain — mirroring the hardware exactly is
    what lets the previewer catch domain bugs instead of hiding them."""
    r, g, b, a = rgba_gs
    if (r, g, b, a) == (128, 128, 128, 128):
        return img
    ir_, ig, ib, ia = img.split()
    if r != 128:
        ir_ = ir_.point(lambda v: min(v * r // 128, 255))
    if g != 128:
        ig = ig.point(lambda v: min(v * g // 128, 255))
    if b != 128:
        ib = ib.point(lambda v: min(v * b // 128, 255))
    if a != 128:
        ia = ia.point(lambda v: min(v * a // 128, 255))
    return Image.merge("RGBA", (ir_, ig, ib, ia))


def display_size(uib: UibFile):
    """Frame size as the panel shows it. Anamorphic stretching is
    horizontal, so height is authoritative and the width comes from the
    ratio directly rather than from a PAR float."""
    num, den = uib.display_aspect
    return (round(uib.canvas_h * num / den), uib.canvas_h)


def to_display_space(img: Image.Image, uib: UibFile) -> Image.Image:
    """Resample a framebuffer-space render to what the television draws.

    The GS framebuffer is not square-pixel on this hardware, not even at
    4:3 (640x448 shown as 4:3 is PAR 0.9333), so a 1:1 PNG has always
    been a slightly wrong picture of the console. At 16:9 it is wrong by
    24%. Compare hardware photographs against this, and framebuffer
    captures against the 1:1 render."""
    target = display_size(uib)
    if target == img.size:
        return img
    return img.resize(target, Image.LANCZOS)


def _screen_index(uib: UibFile, screen) -> int:
    if isinstance(screen, str):
        for i, sc in enumerate(uib.screens):
            if sc["name"] == screen:
                return i
        raise ValueError(f"no screen named {screen!r}")
    return screen


def render(uib: UibFile, focus_current: int = None, background=(10, 14, 26, 255),
           slot_text: dict = None, screen=0, tex_fills: dict = None,
           theme: int = 0) -> Image.Image:
    """Replay one screen (index or name; default first) to an RGBA image
    with the given focus-table index current. slot_text overrides
    dynamic-text slots by name (else placeholders). tex_fills supplies
    raw PSMCT32 texels for streamed texture slots by name, the host
    mirror of ps2ui_tex_set; a slot with none draws nothing, which is
    what the runtime does.

    theme selects a tint-table row, the host mirror of ps2ui_theme_set.
    A theme nobody can look at without a PS2 is a theme nobody will get
    right, and the screenshot drift check covers every row this can
    draw -- design-p3b-theming.md 4.2."""
    if theme < 0 or theme >= max(1, len(uib.themes)):
        raise ValueError(f"theme {theme} is past the "
                         f"{max(1, len(uib.themes))}-row tint table")

    def tinted(vec, fallback):
        """This record's colour in the selected theme.

        Falls back for a blob written before the reader carried
        vectors, and for the one-theme case where the two are equal by
        construction; it never reconstructs a non-default row from the
        default one, which would make a wrong second row invisible
        here."""
        return tuple(vec[theme]) if vec else tuple(fallback)
    si = _screen_index(uib, screen)
    sc = uib.screens[si] if uib.screens else {
        "cmd_first": 0, "cmd_count": len(uib.records),
        "slot_first": 0, "slot_count": len(uib.slots),
        "initial": uib.initial_focus,
    }
    if focus_current is None:
        focus_current = sc["initial"]
    canvas = Image.new("RGBA", (uib.canvas_w, uib.canvas_h), background)
    tex_cache = {}
    scissors = [(0, 0, uib.canvas_w, uib.canvas_h)]

    def clip_rect(x, y, w, h):
        sx, sy, sw, sh = scissors[-1]
        x0, y0 = max(x, sx), max(y, sy)
        x1, y1 = min(x + w, sx + sw), min(y + h, sy + sh)
        return (x0, y0, x1 - x0, y1 - y0) if x1 > x0 and y1 > y0 else None

    for rec in uib.records[sc["cmd_first"]:sc["cmd_first"] + sc["cmd_count"]]:
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
            r, g, b, a_gs = tinted(rec.rgba_themes, rec.rgba)
            layer = Image.new("RGBA", (c[2], c[3]), (r, g, b, gs_alpha_to_css(min(a_gs, 128))))
            canvas.alpha_composite(layer, (c[0], c[1]))
            continue

        if rec.op == OP_TEXQUAD:
            if rec.tex not in tex_cache:
                tex_cache[rec.tex] = _decode_texture(uib, rec.tex, tex_fills)
            if tex_cache[rec.tex] is None:
                continue        # unfilled slot: the console draws nothing
            src = tex_cache[rec.tex].crop((rec.u0, rec.v0, rec.u1, rec.v1))
            if src.size != (rec.w, rec.h):
                src = src.resize((rec.w, rec.h), Image.BILINEAR)
            src = _tint(src, tinted(rec.rgba_themes, rec.rgba))
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

    # Dynamic text slots: same pen as the C runtime — kern, place,
    # advance over the baked glyph table, optional ellipsis, align,
    # focus color. This mirror is the only place the runtime's slot
    # rendering can be seen without a console, so it has to track
    # render_slots line for line, including the greedy ellipsis fit
    # (the runtime cannot afford layout's shrink-from-the-back search
    # once per frame).
    for slot in uib.slots[sc["slot_first"]:sc["slot_first"] + sc["slot_count"]]:
        text = (slot_text or {}).get(slot["name"]) or slot["placeholder"]
        font = uib.fonts[slot["font"]]
        if font["tex"] not in tex_cache:
            tex_cache[font["tex"]] = _decode_texture(uib, font["tex"])
        atlas = tex_cache[font["tex"]]
        glyphs = font["glyphs"]
        fallback = glyphs.get(ord("?"))
        ell = glyphs.get(0x2026)

        kerns = font["kerns"]
        spacing = slot.get("letter_spacing", 0)

        def advance_of(cp):
            g = glyphs.get(cp, fallback)
            return g["advance"] if g else 0

        def has(cp):
            return cp in glyphs or fallback is not None

        def kern_of(prev, cp):
            # The full junction cost: letter-spacing plus the pair's
            # kern, zero before the first glyph — same as the runtime.
            if prev is None:
                return 0
            return spacing + kerns.get((prev, cp), 0)

        def width_of(seq):
            # A codepoint with no glyph and no fallback is skipped
            # whole, and does not become the `prev` of the next kern —
            # exactly as the runtime's slot_measure does, because a
            # glyph that is not drawn cannot be kerned against.
            w = 0
            prev = None
            for cp in seq:
                if not has(cp):
                    continue
                w += kern_of(prev, cp) + advance_of(cp)
                prev = cp
            return w

        cps = [ord(ch) for ch in text]
        total = width_of(cps)
        ellipsize = False
        if total > slot["w"] and slot["ellipsis"]:
            ellipsize = True
            ell_w = ell["advance"] if ell else 0
            w = 0
            fit = []
            prev = None
            for cp in cps:
                if not has(cp):
                    continue
                w += kern_of(prev, cp)
                # The ellipsis kerns against whatever glyph the cut
                # leaves last, so its cost depends on where the cut is.
                ell_kern = kern_of(cp, 0x2026)
                if w + advance_of(cp) + ell_kern + ell_w > slot["w"]:
                    break
                w += advance_of(cp)
                fit.append(cp)
                prev = cp
            cps = fit
            total = w + kern_of(prev, 0x2026) + ell_w

        pen = slot["x"]
        if slot["align"] == 1 and total < slot["w"]:
            pen += (slot["w"] - total) // 2
        elif slot["align"] == 2 and total < slot["w"]:
            pen += slot["w"] - total

        is_focused = slot["focus"] != FOCUS_NONE and slot["focus"] == focus_current
        color = (tinted(slot.get("color_focus_themes"), slot["color_focus"])
                 if is_focused else
                 tinted(slot.get("color_base_themes"), slot["color_base"]))

        if ellipsize and ell:
            cps = cps + [0x2026]
        prev = None
        for cp in cps:
            g = glyphs.get(cp, fallback)
            if not g:
                continue
            pen += kern_of(prev, cp)
            if g["w"] > 0:
                src = atlas.crop((g["u"], g["v"], g["u"] + g["w"], g["v"] + g["h"]))
                src = _tint(src, color)
                canvas.alpha_composite(
                    src, (pen + g["bearing_x"], slot["text_y"] + g["bearing_y"]))
            pen += g["advance"]
            prev = cp

    return canvas


def montage(uib: UibFile, columns: int = 3, gap: int = 16, screen=0) -> Image.Image:
    """One tile per focusable of one screen, that focusable current —
    the couch QA view: every reachable focus state on one sheet."""
    si = _screen_index(uib, screen)
    sc = uib.screens[si]
    states = [n["index"] for n in
              uib.focus[sc["focus_first"]:sc["focus_first"] + sc["focus_count"]]] \
        or [FOCUS_NONE]
    rows = (len(states) + columns - 1) // columns
    tile_w, tile_h = uib.canvas_w, uib.canvas_h
    sheet = Image.new("RGBA", (
        columns * tile_w + (columns + 1) * gap,
        rows * tile_h + (rows + 1) * gap,
    ), (0, 0, 0, 255))
    for i, st in enumerate(states):
        img = render(uib, focus_current=st, screen=si)
        cx = gap + (i % columns) * (tile_w + gap)
        cy = gap + (i // columns) * (tile_h + gap)
        sheet.paste(img, (cx, cy))
    return sheet
