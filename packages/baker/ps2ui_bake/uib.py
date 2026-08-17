""".uib writer and reader (format version 2).

Little-endian throughout (the EE is little-endian; so is every host we
care about). Full layout in docs/format-uib.md; summary:

    header      64 bytes, magic "UIB1", crc32, feature flags
    tex table   n_tex   x 16 bytes
    clut table  n_clut  x  8 bytes
    cmd list    n_cmd   x 32 bytes
    focus table n_focus x 24 bytes
    font table  n_font  x 16 bytes   (dynamic text, feature bit 0)
    slot table  n_slot  x 32 bytes   (dynamic text, feature bit 0)
    blob        textures, CLUTs, glyph tables, names (NUL-terminated)

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
    OP_QUAD, OP_TEXQUAD, OP_SCISSOR_PUSH, OP_SCISSOR_POP,
)

MAGIC = 0x31424955  # "UIB1"
VERSION = 2

FEAT_DYNAMIC_TEXT = 1 << 0
FEAT_KNOWN = FEAT_DYNAMIC_TEXT

_HEADER = struct.Struct("<IHHHHHHIHHIIIIIIIHHII")  # 64 bytes
_TEX = struct.Struct("<BBHHHII")               # 16 bytes
_CLUT = struct.Struct("<HHI")                  # 8 bytes
_CMD = struct.Struct("<BBHhhHHBBBBHHHHH6x")    # 32 bytes
# Field order keeps every u32 4-aligned so the C runtime can overlay
# plain structs on the file with no packing pragmas.
_FOCUS = struct.Struct("<HHHHHHIhhHH")         # 24 bytes
_FONT = struct.Struct("<HHHHHHI")              # 16 bytes
_SLOT = struct.Struct("<IIhhHHBBHHBBBBBBBB2x") # 32 bytes
_CRC_OFFSET = 48
_GLYF = struct.Struct("<IHHHHhhH2x")           # 20 bytes, in blob

assert _HEADER.size == 64 and _TEX.size == 16 and _CLUT.size == 8
assert _CMD.size == 32 and _FOCUS.size == 24
assert _FONT.size == 16 and _SLOT.size == 32 and _GLYF.size == 20


def _align16(buf: bytearray):
    while len(buf) % 16:
        buf.append(0)


def write_uib(path, canvas, records, textures, cluts, focus_nodes,
              initial_focus, fonts=(), slots=()):
    """focus_nodes: IR focus graph nodes (document order == table order).
    initial_focus: focus-table index or None.
    fonts: [{tex, size, weight, ascent, line_height, glyphs: [Glyph-like
             dicts with codepoint/u/v/w/h/bearing_x/bearing_y/advance]}]
    slots: [{name, placeholder, x, text_y, w, font, align, ellipsis,
             capacity, focus (table index or FOCUS_NONE),
             color_base rgba, color_focus rgba}] — colors already in the
             GS modulate domain."""
    blob = bytearray()

    tex_entries = []
    for t in textures:
        off = len(blob)
        blob += t.data
        _align16(blob)
        tex_entries.append((t.fmt, 0, t.width, t.height,
                            t.clut if t.clut is not None else TEX_NONE,
                            off, len(t.data)))

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
        font_entries.append((f["tex"], f["size"], f["weight"], f["ascent"],
                             f["line_height"], len(glyphs), glyphs_off))

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
        ))
    _align16(blob)

    feature_flags = FEAT_DYNAMIC_TEXT if (font_entries or slot_entries) else 0

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


def read_uib(path) -> UibFile:
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < _HEADER.size:
        raise ValueError(f"{path}: truncated header")
    (magic, version, feature_flags, cw, ch, n_tex, n_clut, n_cmd, n_focus,
     initial, off_tex, off_clut, off_cmd, off_focus, off_blob, blob_len,
     crc, n_font, n_slot, off_font, off_slot,
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
    for i in range(n_tex):
        fmt, _pad, w, h, clut, doff, dlen = _TEX.unpack_from(data, off_tex + i * _TEX.size)
        out.textures.append(BakedTexture(
            fmt, w, h, None if clut == TEX_NONE else clut,
            bytes(blob[doff:doff + dlen]),
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
         ) = _FONT.unpack_from(data, off_font + i * _FONT.size)
        glyphs = {}
        for j in range(glyph_count):
            (cp, u, v, w, h, bx, by, adv) = _GLYF.unpack_from(
                blob, glyphs_off + j * _GLYF.size)
            glyphs[cp] = {"u": u, "v": v, "w": w, "h": h,
                          "bearing_x": bx, "bearing_y": by, "advance": adv}
        out.fonts.append({"tex": tex, "size": size, "weight": weight,
                          "ascent": ascent, "line_height": line_height,
                          "glyphs": glyphs})
    for i in range(n_slot):
        (name_off, ph_off, x, text_y, w, font, align, flags, capacity,
         focus, br, bg_, bb, ba, fr, fg, fb, fa,
         ) = _SLOT.unpack_from(data, off_slot + i * _SLOT.size)
        out.slots.append({
            "name": cstr(name_off), "placeholder": cstr(ph_off),
            "x": x, "text_y": text_y, "w": w, "font": font,
            "align": align, "ellipsis": bool(flags & 1),
            "capacity": capacity, "focus": focus,
            "color_base": (br, bg_, bb, ba), "color_focus": (fr, fg, fb, fa),
        })
    return out
