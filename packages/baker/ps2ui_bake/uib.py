""".uib writer and reader.

Little-endian throughout (the EE is little-endian; so is every host we
care about). Full layout in docs/format-uib.md; summary:

    header      48 bytes, magic "UIB1"
    tex table   n_tex   x 16 bytes
    clut table  n_clut  x  8 bytes
    cmd list    n_cmd   x 32 bytes
    focus table n_focus x 24 bytes
    blob        texture data, CLUT data, focus names (NUL-terminated)

Data offsets are relative to the blob, so tooling can rewrite tables
without re-basing pointers. CLUTs are stored linearly; the CSM1
permutation belongs to whoever uploads to the GS (runtime / previewer
tests), not to the file.
"""

import struct
from dataclasses import dataclass, field

from . import gs
from .quads import (
    DrawRecord, BakedTexture, FOCUS_NONE, TEX_NONE,
    OP_QUAD, OP_TEXQUAD, OP_SCISSOR_PUSH, OP_SCISSOR_POP,
)

MAGIC = 0x31424955  # "UIB1"
VERSION = 1

_HEADER = struct.Struct("<IHHHHHHIHHIIIIII")   # 48 bytes
_TEX = struct.Struct("<BBHHHII")               # 16 bytes
_CLUT = struct.Struct("<HHI")                  # 8 bytes
_CMD = struct.Struct("<BBHhhHHBBBBHHHHH6x")    # 32 bytes
# Field order keeps every u32 4-aligned so the C runtime can overlay
# plain structs on the file with no packing pragmas.
_FOCUS = struct.Struct("<HHHHHHIhhHH")         # 24 bytes

assert _HEADER.size == 48 and _TEX.size == 16 and _CLUT.size == 8
assert _CMD.size == 32 and _FOCUS.size == 24


def _align16(buf: bytearray):
    while len(buf) % 16:
        buf.append(0)


def write_uib(path, canvas, records, textures, cluts, focus_nodes, initial_focus):
    """focus_nodes: IR focus graph nodes (document order == table order).
    initial_focus: focus-table index or None."""
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

    off = _HEADER.size
    off_tex = off
    off += _TEX.size * len(tex_entries)
    off_clut = off
    off += _CLUT.size * len(clut_entries)
    off_cmd = off
    off += _CMD.size * len(records)
    off_focus = off
    off += _FOCUS.size * len(focus_entries)
    off_blob = off

    with open(path, "wb") as fh:
        fh.write(_HEADER.pack(
            MAGIC, VERSION, 0,
            canvas["w"], canvas["h"],
            len(tex_entries), len(clut_entries),
            len(records),
            len(focus_entries),
            initial_focus if initial_focus is not None else FOCUS_NONE,
            off_tex, off_clut, off_cmd, off_focus, off_blob, len(blob),
        ))
        for e in tex_entries:
            fh.write(_TEX.pack(*e))
        for e in clut_entries:
            fh.write(_CLUT.pack(*e))
        for r in records:
            fh.write(_CMD.pack(
                r.op, r.state, r.focus, r.x, r.y, r.w, r.h,
                r.rgba[0], r.rgba[1], r.rgba[2], r.rgba[3],
                r.tex, r.u0, r.v0, r.u1, r.v1,
            ))
        for e in focus_entries:
            fh.write(_FOCUS.pack(*e))
        fh.write(blob)


@dataclass
class UibFile:
    canvas_w: int
    canvas_h: int
    initial_focus: int
    records: list = field(default_factory=list)
    textures: list = field(default_factory=list)
    cluts: list = field(default_factory=list)
    focus: list = field(default_factory=list)   # dicts with index links + name


def read_uib(path) -> UibFile:
    with open(path, "rb") as fh:
        data = fh.read()
    (magic, version, _flags, cw, ch, n_tex, n_clut, n_cmd, n_focus,
     initial, off_tex, off_clut, off_cmd, off_focus, off_blob, blob_len,
     ) = _HEADER.unpack_from(data, 0)
    if magic != MAGIC:
        raise ValueError(f"{path}: not a .uib (magic {magic:#x})")
    if version != VERSION:
        raise ValueError(f"{path}: version {version}, expected {VERSION}")
    if off_blob + blob_len > len(data):
        raise ValueError(f"{path}: truncated (blob extends past EOF)")
    blob = data[off_blob:off_blob + blob_len]

    out = UibFile(cw, ch, initial)
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
        end = blob.index(b"\0", name_off)
        out.focus.append({
            "index": idx, "up": up, "down": down, "left": left, "right": right,
            "rect": (x, y, w, h),
            "name": blob[name_off:end].decode("utf-8"),
        })
    return out
