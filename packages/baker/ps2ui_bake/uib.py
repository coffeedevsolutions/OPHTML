""".uib writer and reader (format version 5).

Little-endian throughout (the EE is little-endian; so is every host we
care about). Full layout in docs/format-uib.md; summary:

    header       76 bytes, magic "UIB1", crc32, feature flags, display aspect
    tex table    n_tex    x 16 bytes
    clut table   n_clut   x  8 bytes
    cmd list     n_cmd    x 32 bytes
    focus table  n_focus  x 24 bytes
    font table   n_font   x 24 bytes   (dynamic text, feature bit 0)
    slot table   n_slot   x 32 bytes   (dynamic text, feature bit 0)
    screen table n_screen x 24 bytes   (always >= 1)
    blob         textures, CLUTs, glyph and kern tables, names (NUL-term.)

Screens partition the command, focus and slot tables into contiguous
ranges; textures, CLUTs and fonts are shared across all screens. Focus
indices are global (each screen's D-pad graph only links within its own
range), so switching screens is: remember focus, swap ranges, restore.

Data offsets are relative to the blob, so tooling can rewrite tables
without re-basing pointers. CLUTs are stored linearly; the CSM1
permutation belongs to whoever uploads to the GS (runtime / previewer
tests), not to the file. The crc32 covers the whole file with the crc
field itself zeroed; feature bits a reader does not know mean "reject
loudly", never "ignore quietly".
"""

import struct
import zlib
from dataclasses import dataclass, field

from . import gs
from .quads import (
    DrawRecord, BakedTexture, FOCUS_NONE, TEX_NONE,
    TEXKIND_BAKED, TEXKIND_STREAMED,
    OP_QUAD, OP_TEXQUAD, OP_SCISSOR_PUSH, OP_SCISSOR_POP,
)

MAGIC = 0x31424955  # "UIB1"
VERSION = 6

FEAT_DYNAMIC_TEXT = 1 << 0
FEAT_KERNING = 1 << 1
FEAT_SLOT_SPACING = 1 << 2
# The blob declares at least one streamed texture: a reader that cannot
# fill one must refuse the file rather than draw an empty slot.
FEAT_STREAMED_TEX = 1 << 3
FEAT_KNOWN = (FEAT_DYNAMIC_TEXT | FEAT_KERNING | FEAT_SLOT_SPACING
              | FEAT_STREAMED_TEX)

# A texture with no name. Not 0: offset 0 is a legitimate blob offset.
NAME_NONE = 0xFFFFFFFF

_HEADER = struct.Struct("<IHHHHHHIHHIIIIIIIHHIIHHIHH")  # 76 bytes
_TEX = struct.Struct("<BBHHHIII")              # 20 bytes (v6: kind, name_off)
_CLUT = struct.Struct("<HHI")                  # 8 bytes
_CMD = struct.Struct("<BBHhhHHBBBBHHHHH6x")    # 32 bytes
# Field order keeps every u32 4-aligned so the C runtime can overlay
# plain structs on the file with no packing pragmas.
_FOCUS = struct.Struct("<HHHHHHIhhHH")         # 24 bytes
_FONT = struct.Struct("<HHHHHHIH2xI")          # 24 bytes
# The trailing i16 was pad until slot letter-spacing needed to travel:
# every writer before it wrote zeros there, and zero spacing is the
# meaning zeros already had, so the stride is unchanged and feature
# bit 2 is what makes the new field loud rather than a version bump.
_SLOT = struct.Struct("<IIhhHHBBHHBBBBBBBBh") # 32 bytes
_SCREEN = struct.Struct("<IIIHHHHH2x")        # 24 bytes
_CRC_OFFSET = 48
_GLYF = struct.Struct("<IHHHHhhH2x")           # 20 bytes, in blob
_KERN = struct.Struct("<IIh2x")                # 12 bytes, in blob

assert _HEADER.size == 76 and _TEX.size == 20 and _CLUT.size == 8
assert _SCREEN.size == 24
assert _CMD.size == 32 and _FOCUS.size == 24
assert _FONT.size == 24 and _SLOT.size == 32 and _GLYF.size == 20
assert _KERN.size == 12


def _align16(buf: bytearray):
    while len(buf) % 16:
        buf.append(0)


def write_uib(path, canvas, records, textures, cluts, focus_nodes,
              initial_focus, fonts=(), slots=(), screens=None,
              display_aspect=(4, 3)):
    """focus_nodes: IR focus graph nodes (document order == table order).
    initial_focus: focus-table index or None.
    display_aspect: (num, den) the panel shows the framebuffer at. The
    framebuffer is not square-pixel on this hardware even at 4:3, so
    this travels with the blob for the previewer and the video setup.
    screens: [{name, cmd_first, cmd_count, focus_first, focus_count,
               slot_first, slot_count, initial (global focus index or
               None)}] — omitted means one screen named "main" covering
               everything.
    fonts: [{tex, size, weight, ascent, line_height, glyphs: [Glyph-like
             dicts with codepoint/u/v/w/h/bearing_x/bearing_y/advance]}]
    slots: [{name, placeholder, x, text_y, w, font, align, ellipsis,
             capacity, focus (table index or FOCUS_NONE),
             color_base rgba, color_focus rgba}] — colors already in the
             GS modulate domain."""
    blob = bytearray()

    tex_entries = []
    for t in textures:
        if t.kind == TEXKIND_STREAMED:
            # No texels in the file. data_off addresses nothing and the
            # runtime does not range-check it; data_len is the exact
            # payload ps2ui_tex_set will demand, so the app is told the
            # number instead of deriving it and getting padding wrong.
            name_off = len(blob)
            blob += t.name.encode("utf-8") + b"\0"
            _align16(blob)
            tex_entries.append((t.fmt, TEXKIND_STREAMED, t.width, t.height,
                                t.clut if t.clut is not None else TEX_NONE,
                                0, t.reservation, name_off))
            continue
        off = len(blob)
        blob += t.data
        _align16(blob)
        if t.name:
            name_off = len(blob)
            blob += t.name.encode("utf-8") + b"\0"
            _align16(blob)
        else:
            name_off = NAME_NONE
        tex_entries.append((t.fmt, TEXKIND_BAKED, t.width, t.height,
                            t.clut if t.clut is not None else TEX_NONE,
                            off, len(t.data), name_off))

    clut_entries = []
    for c in cluts:
        off = len(blob)
        blob += c
        _align16(blob)
        clut_entries.append((len(c) // 4, 0, off))

    id_to_index = {n["id"]: i for i, n in enumerate(focus_nodes)}
    focus_entries = []
    for i, n in enumerate(focus_nodes):
        name_off = len(blob)
        blob += n["name"].encode("utf-8") + b"\0"
        def idx(v):
            return id_to_index[v] if v is not None else FOCUS_NONE
        x, y, w, h = n["rect"]
        focus_entries.append((
            i, idx(n["up"]), idx(n["down"]), idx(n["left"]), idx(n["right"]),
            0, name_off, x, y, w, h,
        ))
    _align16(blob)

    font_entries = []
    for f in fonts:
        glyphs = sorted(f["glyphs"], key=lambda g: g["codepoint"])
        glyphs_off = len(blob)
        for g in glyphs:
            blob += _GLYF.pack(g["codepoint"], g["u"], g["v"], g["w"], g["h"],
                               g["bearing_x"], g["bearing_y"], g["advance"])
        _align16(blob)
        kerns = sorted(f.get("kerns", ()), key=lambda k: (k["prev"], k["cur"]))
        kerns_off = len(blob)
        for k in kerns:
            blob += _KERN.pack(k["prev"], k["cur"], k["amount"])
        _align16(blob)
        font_entries.append((f["tex"], f["size"], f["weight"], f["ascent"],
                             f["line_height"], len(glyphs), glyphs_off,
                             len(kerns), kerns_off))

    slot_entries = []
    for sl in slots:
        name_off = len(blob)
        blob += sl["name"].encode("utf-8") + b"\0"
        ph_off = len(blob)
        blob += sl["placeholder"].encode("utf-8") + b"\0"
        cb, cf = sl["color_base"], sl["color_focus"]
        slot_entries.append((
            name_off, ph_off, sl["x"], sl["text_y"], sl["w"], sl["font"],
            sl["align"], 1 if sl["ellipsis"] else 0, sl["capacity"],
            sl["focus"],
            cb[0], cb[1], cb[2], cb[3], cf[0], cf[1], cf[2], cf[3],
            sl.get("letter_spacing", 0),
        ))
    _align16(blob)

    if screens is None:
        screens = [{
            "name": "main",
            "cmd_first": 0, "cmd_count": len(records),
            "focus_first": 0, "focus_count": len(focus_entries),
            "slot_first": 0, "slot_count": len(slot_entries),
            "initial": initial_focus,
        }]
    screen_entries = []
    for sc in screens:
        name_off = len(blob)
        blob += sc["name"].encode("utf-8") + b"\0"
        screen_entries.append((
            name_off, sc["cmd_first"], sc["cmd_count"],
            sc["focus_first"], sc["focus_count"],
            sc["slot_first"], sc["slot_count"],
            sc["initial"] if sc["initial"] is not None else FOCUS_NONE,
        ))
    _align16(blob)

    feature_flags = FEAT_DYNAMIC_TEXT if (font_entries or slot_entries) else 0
    # Set only when a font actually carries pairs, so the runtime can
    # skip the lookup wholesale for a UI whose text is too small to
    # kern, and so "no kerning" is stated rather than inferred from a
    # zero count.
    if any(e[7] for e in font_entries):
        feature_flags |= FEAT_KERNING
    if any(e[18] for e in slot_entries):
        feature_flags |= FEAT_SLOT_SPACING
    if any(e[1] == TEXKIND_STREAMED for e in tex_entries):
        feature_flags |= FEAT_STREAMED_TEX

    off = _HEADER.size
    off_tex = off
    off += _TEX.size * len(tex_entries)
    off_clut = off
    off += _CLUT.size * len(clut_entries)
    off_cmd = off
    off += _CMD.size * len(records)
    off_focus = off
    off += _FOCUS.size * len(focus_entries)
    off_font = off
    off += _FONT.size * len(font_entries)
    off_slot = off
    off += _SLOT.size * len(slot_entries)
    off_screen = off
    off += _SCREEN.size * len(screen_entries)
    # The blob section must start on a 16-byte file offset. Texture
    # data_offs are 16-aligned relative to the blob and bin2c places the
    # whole file 16-aligned in memory, so this padding is the one link
    # that makes the absolute address qword-aligned -- and a GIF
    # source-chain REF tag has no low address bits to carry a remainder:
    # a misaligned source is silently truncated and the transfer starts
    # up to 15 bytes early. Every blob written before this padding
    # existed shipped off_blob at +4 or +12, which shifted every texture
    # by 1-3 texels (PSMCT32) or 4-12 texels (PSMT8) on console and
    # emulator alike. The runtime refuses such a file (PS2UI_ERR_ALIGN).
    blob_pad = (-off) % 16
    off += blob_pad
    off_blob = off

    out = bytearray()
    out += _HEADER.pack(
        MAGIC, VERSION, feature_flags,
        canvas["w"], canvas["h"],
        len(tex_entries), len(clut_entries),
        len(records),
        len(focus_entries),
        initial_focus if initial_focus is not None else FOCUS_NONE,
        off_tex, off_clut, off_cmd, off_focus, off_blob, len(blob),
        0,  # crc32, patched below
        len(font_entries), len(slot_entries), off_font, off_slot,
        len(screen_entries), 0, off_screen,
        int(display_aspect[0]), int(display_aspect[1]),
    )
    for e in tex_entries:
        out += _TEX.pack(*e)
    for e in clut_entries:
        out += _CLUT.pack(*e)
    for r in records:
        out += _CMD.pack(
            r.op, r.state, r.focus, r.x, r.y, r.w, r.h,
            r.rgba[0], r.rgba[1], r.rgba[2], r.rgba[3],
            r.tex, r.u0, r.v0, r.u1, r.v1,
        )
    for e in focus_entries:
        out += _FOCUS.pack(*e)
    for e in font_entries:
        out += _FONT.pack(*e)
    for e in slot_entries:
        out += _SLOT.pack(*e)
    for e in screen_entries:
        out += _SCREEN.pack(*e)
    out += bytes(blob_pad)
    assert len(out) == off_blob, "layout arithmetic and bytes written disagree"
    out += blob

    # CRC over the whole file with the crc field zeroed.
    crc = zlib.crc32(bytes(out)) & 0xFFFFFFFF
    struct.pack_into("<I", out, _CRC_OFFSET, crc)
    with open(path, "wb") as fh:
        fh.write(bytes(out))


@dataclass
class UibFile:
    canvas_w: int
    canvas_h: int
    initial_focus: int
    feature_flags: int = 0
    records: list = field(default_factory=list)
    textures: list = field(default_factory=list)
    cluts: list = field(default_factory=list)
    focus: list = field(default_factory=list)   # dicts with index links + name
    fonts: list = field(default_factory=list)   # dicts incl. glyphs by codepoint
    slots: list = field(default_factory=list)
    screens: list = field(default_factory=list)
    display_aspect: tuple = (4, 3)


def read_uib(path) -> UibFile:
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < _HEADER.size:
        raise ValueError(f"{path}: truncated header")
    (magic, version, feature_flags, cw, ch, n_tex, n_clut, n_cmd, n_focus,
     initial, off_tex, off_clut, off_cmd, off_focus, off_blob, blob_len,
     crc, n_font, n_slot, off_font, off_slot, n_screen, _pad, off_screen,
     dar_num, dar_den,
     ) = _HEADER.unpack_from(data, 0)
    if magic != MAGIC:
        raise ValueError(f"{path}: not a .uib (magic {magic:#x})")
    if version != VERSION:
        raise ValueError(f"{path}: version {version}, expected {VERSION}")
    if feature_flags & ~FEAT_KNOWN:
        raise ValueError(f"{path}: unknown feature bits {feature_flags:#x}")
    zeroed = bytearray(data)
    struct.pack_into("<I", zeroed, _CRC_OFFSET, 0)
    actual = zlib.crc32(bytes(zeroed)) & 0xFFFFFFFF
    if actual != crc:
        raise ValueError(f"{path}: crc mismatch (file {crc:#x}, computed {actual:#x})")
    if off_blob + blob_len > len(data):
        raise ValueError(f"{path}: truncated (blob extends past EOF)")
    blob = data[off_blob:off_blob + blob_len]

    def cstr(off):
        end = blob.index(b"\0", off)
        return blob[off:end].decode("utf-8")

    out = UibFile(cw, ch, initial, feature_flags)
    out.display_aspect = (dar_num, dar_den)
    out.off_blob = off_blob
    for i in range(n_tex):
        (fmt, kind, w, h, clut, doff, dlen,
         noff) = _TEX.unpack_from(data, off_tex + i * _TEX.size)
        streamed = kind == TEXKIND_STREAMED
        out.textures.append(BakedTexture(
            fmt, w, h, None if clut == TEX_NONE else clut,
            b"" if streamed else bytes(blob[doff:doff + dlen]),
            data_off=None if streamed else doff,
            kind=kind,
            name=None if noff == NAME_NONE else cstr(noff),
            reservation=dlen if streamed else 0,
        ))
    for i in range(n_clut):
        ncolors, _pad, doff = _CLUT.unpack_from(data, off_clut + i * _CLUT.size)
        out.cluts.append(bytes(blob[doff:doff + ncolors * 4]))
    for i in range(n_cmd):
        (op, state, focus, x, y, w, h, r, g, b, a,
         tex, u0, v0, u1, v1) = _CMD.unpack_from(data, off_cmd + i * _CMD.size)
        out.records.append(DrawRecord(
            op, state, focus, x, y, w, h, (r, g, b, a), tex, u0, v0, u1, v1,
        ))
    for i in range(n_focus):
        (idx, up, down, left, right, _pad, name_off, x, y, w, h,
         ) = _FOCUS.unpack_from(data, off_focus + i * _FOCUS.size)
        out.focus.append({
            "index": idx, "up": up, "down": down, "left": left, "right": right,
            "rect": (x, y, w, h),
            "name": cstr(name_off),
        })
    for i in range(n_font):
        (tex, size, weight, ascent, line_height, glyph_count, glyphs_off,
         kern_count, kerns_off) = _FONT.unpack_from(
            data, off_font + i * _FONT.size)
        glyphs = {}
        for j in range(glyph_count):
            (cp, u, v, w, h, bx, by, adv) = _GLYF.unpack_from(
                blob, glyphs_off + j * _GLYF.size)
            glyphs[cp] = {"u": u, "v": v, "w": w, "h": h,
                          "bearing_x": bx, "bearing_y": by, "advance": adv}
        kerns = {}
        for j in range(kern_count):
            (prev, cur, amount) = _KERN.unpack_from(
                blob, kerns_off + j * _KERN.size)
            kerns[(prev, cur)] = amount
        out.fonts.append({"tex": tex, "size": size, "weight": weight,
                          "ascent": ascent, "line_height": line_height,
                          "glyphs": glyphs, "kerns": kerns})
    for i in range(n_slot):
        (name_off, ph_off, x, text_y, w, font, align, flags, capacity,
         focus, br, bg_, bb, ba, fr, fg, fb, fa, letter_spacing,
         ) = _SLOT.unpack_from(data, off_slot + i * _SLOT.size)
        out.slots.append({
            "name": cstr(name_off), "placeholder": cstr(ph_off),
            "x": x, "text_y": text_y, "w": w, "font": font,
            "align": align, "ellipsis": bool(flags & 1),
            "capacity": capacity, "focus": focus,
            "letter_spacing": letter_spacing,
            "color_base": (br, bg_, bb, ba), "color_focus": (fr, fg, fb, fa),
        })
    for i in range(n_screen):
        (name_off, cmd_first, cmd_count, focus_first, focus_count,
         slot_first, slot_count, initial_f,
         ) = _SCREEN.unpack_from(data, off_screen + i * _SCREEN.size)
        out.screens.append({
            "name": cstr(name_off),
            "cmd_first": cmd_first, "cmd_count": cmd_count,
            "focus_first": focus_first, "focus_count": focus_count,
            "slot_first": slot_first, "slot_count": slot_count,
            "initial": initial_f,
        })
    return out
