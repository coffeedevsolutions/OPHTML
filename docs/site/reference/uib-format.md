---
id: reference/uib-format
title: .uib
description: The baked blob the console loads, record by record, with the alignment and CRC rules and the v7 stability pledge.
section: reference
order: 51
version: 0.9.0
sources: [docs/format-uib.md, runtime/ps2ui.h, runtime/ps2ui.c, runtime/tests/test_runtime.c, packages/baker/ps2ui_bake/uib.py, packages/baker/ps2ui_bake/check.py, packages/baker/ps2ui_bake/ps2ui.py, tools/check-format-frozen.py, tools/check-versions.py, docs/PLAN.md, README.md, examples/memcard/build/ui.uib, examples/opl-env/build/ui.uib, examples/channel6/build/ui.uib]
---

# .uib

A `.uib` file is the blob `ps2ui-bake` writes and `ps2ui_load` maps. Every record is little-endian and fixed-size. Every `u32` sits at a 4-aligned offset, so the C runtime overlays the structs in [runtime/ps2ui.h](repo:runtime/ps2ui.h#L81) on the file without parsing or packing pragmas. The Python writer and reader are in [uib.py](repo:packages/baker/ps2ui_bake/uib.py#L117).

## Layout

The file is a header, eight tables, padding, and a blob. Each table starts where the previous one ends. Every `data_off` and `name_off` in a table is relative to the blob, not to the file.

| section | offset field | count field | stride | meaning |
|---|---|---|---|---|
| header | 0 | | 84 | magic, counts, offsets, crc, aspect |
| tex table | `off_tex` | `n_tex` | 20 | one entry per texture |
| clut table | `off_clut` | `n_clut` | 8 | one entry per palette |
| command list | `off_cmd` | `n_cmd` | 32 | draw and scissor commands in replay order |
| focus table | `off_focus` | `n_focus` | 24 | the solved D-pad graph |
| font table | `off_font` | `n_font` | 24 | glyph atlases for dynamic text |
| slot table | `off_slot` | `n_slot` | 28 | dynamic text slots |
| screen table | `off_screen` | `n_screen` | 24 | contiguous ranges of the three tables above |
| tint table | `off_tint` | `n_theme` rows of `n_tint` | 4 | colours, theme-major |
| padding | | | 0 to 12 | brings `off_blob` to a multiple of 16 |
| blob | `off_blob` | `blob_len` | | texels, palettes, glyph and kern records, names |

The writer computes each offset in [write_uib](repo:packages/baker/ps2ui_bake/uib.py#L380). Read the header of the memcard example to see the arithmetic land.

```sh
python3 - <<'PY'
import struct
d = open("examples/memcard/build/ui.uib", "rb").read()
H = struct.Struct("<IHHHHHHIHHIIIIIIIHHIIHHIIHHHH")
names = ("magic version feature_flags canvas_w canvas_h n_tex n_clut n_cmd "
         "n_focus initial_focus off_tex off_clut off_cmd off_focus off_blob "
         "blob_len crc32 n_font n_slot off_font off_slot n_screen n_tint "
         "off_screen off_tint n_theme pad display_aspect_num "
         "display_aspect_den").split()
print("file", len(d), "bytes; header", H.size, "bytes")
for n, v in zip(names, H.unpack_from(d, 0)):
    print(f"{n:<19} {v:#x}" if n in ("magic", "feature_flags", "crc32") else f"{n:<19} {v}")
PY
```

```
file 176208 bytes; header 84 bytes
magic               0x31424955
version             7
feature_flags       0x3
canvas_w            640
canvas_h            448
n_tex               11
n_clut              1
n_cmd               1062
n_focus             16
initial_focus       0
off_tex             84
off_clut            304
off_cmd             312
off_focus           34296
off_blob            35040
blob_len            141168
crc32               0x4d8c37e4
n_font              2
n_slot              6
off_font            34680
off_slot            34728
n_screen            2
n_tint              23
off_screen          34896
off_tint            34944
n_theme             1
pad                 0
display_aspect_num  4
display_aspect_den  3
```

`off_tex` is 84 because the header is 84 bytes. `off_clut` is 84 plus 11 times 20. The tint table ends at 35036 and the blob starts at 35040, after 4 bytes of padding.

### Header

| offset | size | type | field | meaning |
|---|---|---|---|---|
| 0 | 4 | u32 | magic | `0x31424955`, the bytes `UIB1` |
| 4 | 2 | u16 | version | 7 |
| 6 | 2 | u16 | feature_flags | bits from the feature table under Invariants; an unknown bit is refused |
| 8 | 2 | u16 | canvas_w | framebuffer width in pixels |
| 10 | 2 | u16 | canvas_h | framebuffer height in pixels |
| 12 | 2 | u16 | n_tex | texture count |
| 14 | 2 | u16 | n_clut | palette count |
| 16 | 4 | u32 | n_cmd | command count |
| 20 | 2 | u16 | n_focus | focus node count |
| 22 | 2 | u16 | initial_focus | screen 0's initial focus index, `0xFFFF` for none |
| 24 | 4 | u32 | off_tex | file offset of the tex table |
| 28 | 4 | u32 | off_clut | file offset of the clut table |
| 32 | 4 | u32 | off_cmd | file offset of the command list |
| 36 | 4 | u32 | off_focus | file offset of the focus table |
| 40 | 4 | u32 | off_blob | file offset of the blob, a multiple of 16 |
| 44 | 4 | u32 | blob_len | blob length in bytes |
| 48 | 4 | u32 | crc32 | CRC-32 of the file with these 4 bytes read as zero |
| 52 | 2 | u16 | n_font | font count |
| 54 | 2 | u16 | n_slot | slot count |
| 56 | 4 | u32 | off_font | file offset of the font table |
| 60 | 4 | u32 | off_slot | file offset of the slot table |
| 64 | 2 | u16 | n_screen | screen count, at least 1 |
| 66 | 2 | u16 | n_tint | colours per theme row |
| 68 | 4 | u32 | off_screen | file offset of the screen table |
| 72 | 4 | u32 | off_tint | file offset of the tint table |
| 76 | 2 | u16 | n_theme | theme rows, at least 1 |
| 78 | 2 | u16 | pad | zero |
| 80 | 2 | u16 | display_aspect_num | panel aspect numerator |
| 82 | 2 | u16 | display_aspect_den | panel aspect denominator |

The runtime derives the pixel aspect from the last two fields and the canvas size, see [ps2ui_pixel_aspect_x1000](repo:runtime/ps2ui.h#L689). The C struct for every record on this page is listed on [C API reference](page:runtime/api-reference#structs).

## Records

### Texture entry

Stride 20. A baked entry points at texels in the blob. A streamed entry carries no texels; `ps2ui_tex_set` supplies them at runtime.

| offset | size | type | field | meaning |
|---|---|---|---|---|
| 0 | 1 | u8 | format | 0 PSMT8 (indexed), 1 PSMCT32 |
| 1 | 1 | u8 | kind | 0 baked, 1 streamed |
| 2 | 2 | u16 | width | texels |
| 4 | 2 | u16 | height | texels |
| 6 | 2 | u16 | clut | clut index, `0xFFFF` for none; required when format is PSMT8 |
| 8 | 4 | u32 | data_off | blob offset of the texels, a multiple of 16; unused when streamed |
| 12 | 4 | u32 | data_len | texel byte count; the reservation `ps2ui_tex_set` demands when streamed |
| 16 | 4 | u32 | name_off | blob offset of a NUL-terminated name, `0xFFFFFFFF` for none; required when streamed |

PSMCT32 texels are `r g b a` bytes with alpha in the GS 0 to 128 domain. PSMT8 texels are palette indices.

### CLUT entry

Stride 8. Colours are stored in palette order. The CSM1 index swap is applied by the uploader, never by the file.

| offset | size | type | field | meaning |
|---|---|---|---|---|
| 0 | 2 | u16 | ncolors | entries in the palette |
| 2 | 2 | u16 | pad | zero |
| 4 | 4 | u32 | data_off | blob offset of `ncolors` PSMCT32 colours |

### Command

Stride 32. Commands replay in file order. A command draws when `state` is 0, when `state` is 2 and `focus` is the focused node, or when `state` is 1 and it is not.

| offset | size | type | field | meaning |
|---|---|---|---|---|
| 0 | 1 | u8 | op | 0 QUAD, 1 TEXQUAD, 2 SCISSOR_PUSH, 3 SCISSOR_POP |
| 1 | 1 | u8 | state | 0 always, 1 unfocused, 2 focused |
| 2 | 2 | u16 | focus | focus index the state refers to, `0xFFFF` for none |
| 4 | 2 | i16 | x | left edge in pixels |
| 6 | 2 | i16 | y | top edge in pixels |
| 8 | 2 | u16 | w | width in pixels |
| 10 | 2 | u16 | h | height in pixels |
| 12 | 2 | u16 | tint | index into the live theme row |
| 14 | 2 | u16 | tint_focus | index used while `focus` is the focused node; the baker writes the same value as `tint` |
| 16 | 2 | u16 | tex | texture index for TEXQUAD, else `0xFFFF` |
| 18 | 8 | u16 x4 | u0 v0 u1 v1 | texel source rect, `u1` and `v1` exclusive |
| 26 | 6 | u8 x6 | pad | zero |

Scissor commands carry no colour. The writer puts 0 in both tint fields of a scissor command and readers do not range-check them, see [write_uib](repo:packages/baker/ps2ui_bake/uib.py#L271). A QUAD's colour is full-range RGB. A TEXQUAD's colour is in the modulate domain, where `0x80` is identity.

### Focus node

Stride 24. The graph is solved at build time, so a D-pad press is one lookup.

| offset | size | type | field | meaning |
|---|---|---|---|---|
| 0 | 2 | u16 | id | equals the node's table index |
| 2 | 2 | u16 | up | neighbour index, `0xFFFF` for none |
| 4 | 2 | u16 | down | neighbour index, `0xFFFF` for none |
| 6 | 2 | u16 | left | neighbour index, `0xFFFF` for none |
| 8 | 2 | u16 | right | neighbour index, `0xFFFF` for none |
| 10 | 2 | u16 | pad | zero |
| 12 | 4 | u32 | name_off | blob offset of the NUL-terminated UTF-8 name |
| 16 | 2 | i16 | x | rect left, for debugging and the HUD |
| 18 | 2 | i16 | y | rect top |
| 20 | 2 | u16 | w | rect width |
| 22 | 2 | u16 | h | rect height |

### Font entry

Stride 24. Present only with feature bit 0. The atlas must be a baked PSMT8 texture.

| offset | size | type | field | meaning |
|---|---|---|---|---|
| 0 | 2 | u16 | tex | atlas texture index |
| 2 | 2 | u16 | size | pixel size |
| 4 | 2 | u16 | weight | 400 or 700 |
| 6 | 2 | u16 | ascent | pixels, from the metrics JSON |
| 8 | 2 | u16 | line_height | pixels |
| 10 | 2 | u16 | glyph_count | glyph records at `glyphs_off` |
| 12 | 4 | u32 | glyphs_off | blob offset of the glyph records, sorted by codepoint |
| 16 | 2 | u16 | kern_count | kern records at `kerns_off`, 0 unless feature bit 1 |
| 18 | 2 | u16 | pad | zero |
| 20 | 4 | u32 | kerns_off | blob offset of the kern records, sorted by pair |

### Glyph record

Stride 20, in the blob. Read as `glyphs_off + j * 20`.

| offset | size | type | field | meaning |
|---|---|---|---|---|
| 0 | 4 | u32 | codepoint | Unicode scalar |
| 4 | 2 | u16 | u | atlas left |
| 6 | 2 | u16 | v | atlas top |
| 8 | 2 | u16 | w | atlas width |
| 10 | 2 | u16 | h | atlas height |
| 12 | 2 | i16 | bearing_x | from the pen x |
| 14 | 2 | i16 | bearing_y | from the line-box top |
| 16 | 2 | u16 | advance | pixels |
| 18 | 2 | u16 | pad | zero |

### Kern record

Stride 12, in the blob. Pairs are ordered and pairs that round to zero are not stored.

| offset | size | type | field | meaning |
|---|---|---|---|---|
| 0 | 4 | u32 | prev | first codepoint of the pair |
| 4 | 4 | u32 | cur | second codepoint of the pair |
| 8 | 2 | i16 | amount | pixels at this font's size, usually negative |
| 10 | 2 | u16 | pad | zero |

### Slot entry

Stride 28. Present only with feature bit 0. The runtime copies app text into a per-slot buffer of `capacity` bytes and composes glyph quads each frame.

| offset | size | type | field | meaning |
|---|---|---|---|---|
| 0 | 4 | u32 | name_off | blob offset of the NUL-terminated name |
| 4 | 4 | u32 | placeholder_off | blob offset of the text drawn until the app sets one |
| 8 | 2 | i16 | x | content left in pixels |
| 10 | 2 | i16 | text_y | glyph-box top in pixels |
| 12 | 2 | u16 | w | content width in pixels |
| 14 | 2 | u16 | font | font table index |
| 16 | 1 | u8 | align | 0 left, 1 center, 2 right |
| 17 | 1 | u8 | flags | bit 0 ellipsize overflow |
| 18 | 2 | u16 | capacity | maximum runtime bytes |
| 20 | 2 | u16 | focus | focus index or `0xFFFF` |
| 22 | 2 | u16 | tint_base | index into the live theme row |
| 24 | 2 | u16 | tint_focus | index used while the slot's node is focused |
| 26 | 2 | i16 | letter_spacing | pixels per glyph junction; non-zero requires feature bit 2 |

### Screen entry

Stride 24. Screens partition the command, focus and slot tables into contiguous ranges. Textures, palettes and fonts are shared.

| offset | size | type | field | meaning |
|---|---|---|---|---|
| 0 | 4 | u32 | name_off | blob offset of the NUL-terminated name |
| 4 | 4 | u32 | cmd_first | first command index |
| 8 | 4 | u32 | cmd_count | commands in the screen |
| 12 | 2 | u16 | focus_first | first focus index |
| 14 | 2 | u16 | focus_count | focus nodes in the screen |
| 16 | 2 | u16 | slot_first | first slot index |
| 18 | 2 | u16 | slot_count | slots in the screen |
| 20 | 2 | u16 | initial_focus | global focus index or `0xFFFF` |
| 22 | 2 | u8 x2 | pad | zero |

### Tint entry

Stride 4. The table is theme-major: row `t` starts at `off_tint + t * n_tint * 4`. Every painting command and every slot indexes a row, so a themeless blob still has one row. How CSS becomes rows is on [Theming](page:authoring/theming#behaviour).

| offset | size | type | field | meaning |
|---|---|---|---|---|
| 0 | 1 | u8 | r | red |
| 1 | 1 | u8 | g | green |
| 2 | 1 | u8 | b | blue |
| 3 | 1 | u8 | a | alpha in the GS 0 to 128 domain |

## Invariants

The writer establishes each property. `ps2ui_load` refuses a file that breaks one, with the codes listed on [Errors and constants](page:runtime/errors-and-constants#error-codes). `ps2ui-check` asserts the same properties offline, see [ps2ui-check](page:cli/ps2ui-check#output).

| invariant | writer | runtime | ps2ui-check |
|---|---|---|---|
| `off_blob` is a multiple of 16 | `blob_pad` in [uib.py](repo:packages/baker/ps2ui_bake/uib.py#L409) | blob address with low bits set is `PS2UI_ERR_ALIGN`, [ps2ui.c](repo:runtime/ps2ui.c#L373) | check 12 |
| every baked `data_off` is a multiple of 16 | `_align16` after every texture | `PS2UI_ERR_ALIGN`, [ps2ui.c](repo:runtime/ps2ui.c#L396) | check 13 |
| `crc32` is the zlib CRC-32 of the file with bytes 48 to 51 zeroed | `zlib.crc32` patched in at offset 48 | `PS2UI_ERR_CRC` from `crc_file_with_hole`, [ps2ui.c](repo:runtime/ps2ui.c#L48) | reader raises before checks run |
| every table ends inside the file | offsets computed from counts and strides | `PS2UI_ERR_TRUNCATED` | reader raises |
| every table starts at a multiple of 4 | an 84-byte header and entries whose sizes are multiples of 4 | `PS2UI_ERR_ALIGN`, [tables_aligned](repo:runtime/ps2ui.c#L165) | reader raises |
| a font's glyph and kern tables start at a multiple of 4 in the blob | `_align16` before each | `PS2UI_ERR_ALIGN` | reader raises |
| `n_screen` is at least 1 | default screen `main` when none is given | `PS2UI_ERR_BOUNDS`, [ps2ui.c](repo:runtime/ps2ui.c#L307) | check 5 |
| `n_theme` is at least 1 | `n_theme` defaults to 1 | `PS2UI_ERR_BOUNDS`, [ps2ui.c](repo:runtime/ps2ui.c#L312) | check 41 |
| `n_theme` above 1 requires feature bit 4 | bit set from `n_theme` | `PS2UI_ERR_TINTS`, [ps2ui.c](repo:runtime/ps2ui.c#L324) | check 44 |
| a streamed texture requires bit 3, a name and a non-zero `data_len` | bit set from the texture table | `PS2UI_ERR_FEATURES` or `PS2UI_ERR_BOUNDS`, [ps2ui.c](repo:runtime/ps2ui.c#L389) | checks 6 to 9 |
| `4 * n_tint` is below the painting command count | interning in `_tint` | not checked | check 43, once at least 100 commands paint |

The runtime checks the blob's address in memory, not its file offset. A file placed 16-aligned in memory has an aligned blob only because `off_blob` is a multiple of 16, so the two checks are one property. Run the arithmetic on the memcard blob.

```sh
python3 - <<'PY'
import struct, zlib
d = open("examples/memcard/build/ui.uib", "rb").read()
h = struct.unpack_from("<IHHHHHHIHHIIIIIIIHHIIHHIIHHHH", d, 0)
n_tex, n_cmd, off_tex, off_cmd, off_blob, blob_len, crc = h[5], h[7], h[10], h[12], h[14], h[15], h[16]
n_tint, off_tint, n_theme = h[22], h[24], h[25]
print("off_blob % 16 =", off_blob % 16)
print("baked data_off % 16 =", [struct.unpack_from("<BBHHHIII", d, off_tex + 20 * i)[5] % 16 for i in range(n_tex)])
zeroed = bytearray(d); struct.pack_into("<I", zeroed, 48, 0)
print("crc32 in header", hex(crc), "recomputed", hex(zlib.crc32(bytes(zeroed)) & 0xFFFFFFFF))
end = off_tint + n_theme * n_tint * 4
print("tables end", end, "pad", off_blob - end, "off_blob + blob_len", off_blob + blob_len, "file", len(d))
paint = sum(1 for i in range(n_cmd) if d[off_cmd + 32 * i] in (0, 1))
print("painting commands", paint, "n_tint", n_tint, "4 * n_tint < painting:", 4 * n_tint < paint)
PY
```

```
off_blob % 16 = 0
baked data_off % 16 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
crc32 in header 0x4d8c37e4 recomputed 0x4d8c37e4
tables end 35036 pad 4 off_blob + blob_len 176208 file 176208
painting commands 1030 n_tint 23 4 * n_tint < painting: True
```

### Feature bits

A reader refuses any bit outside the known set. The known set is `PS2UI_FEAT_KNOWN` in [ps2ui.h](repo:runtime/ps2ui.h#L63) and `FEAT_KNOWN` in [uib.py](repo:packages/baker/ps2ui_bake/uib.py#L74), both `0x1f`. The writer sets each bit from the tables it wrote, in [write_uib](repo:packages/baker/ps2ui_bake/uib.py#L356).

| bit | name | set when | gates |
|---|---|---|---|
| 0 | `PS2UI_FEAT_DYNAMIC_TEXT` | any font or slot exists | the font and slot tables |
| 1 | `PS2UI_FEAT_KERNING` | any font has kern pairs | the kern lookup in the pen |
| 2 | `PS2UI_FEAT_SLOT_SPACING` | any slot has non-zero `letter_spacing` | reading `letter_spacing` |
| 3 | `PS2UI_FEAT_STREAMED_TEX` | any texture has kind 1 | loading a streamed entry |
| 4 | `PS2UI_FEAT_ROLE_TINTS` | `n_theme` is above 1 | loading more than one theme row |

The memcard blob above carries `0x3`, bits 0 and 1. Its two fonts have 291 kern pairs between them, which `ps2ui-check` reports as check 57.

## Versioning

`version` is 7. Readers refuse any other value: `PS2UI_ERR_VERSION` in the runtime, `ValueError` in the Python reader. `PS2UI_VERSION` in [ps2ui.h](repo:runtime/ps2ui.h#L37) is that format number, not a package version. [check-versions.py](repo:tools/check-versions.py#L400) holds it equal to `uib.VERSION`, and `ps2ui vendor-runtime` writes `ps2ui.c` and `ps2ui.h` from the same package that bakes the blob. What the pledge means for an installed app is on [Compatibility](page:reference/compatibility#format-compatibility).

### The pledge

v7 is the last incompatible layout. An addition from here goes behind a new feature bit and never moves a stride. A reader that lacks the bit refuses the blob by name instead of misreading it. [check-format-frozen.py](repo:tools/check-format-frozen.py#L87) records the v7 layout from the live `Struct` objects and runs in CI.

| frozen | not frozen |
|---|---|
| the format string and size of all eleven structs | the set of feature bits |
| `MAGIC` | new tables behind a new bit, recorded in the same change |
| `VERSION` | |
| the value of every assigned feature bit | |

The check also fails when `uib` defines a `Struct` that the record does not hold. A field swap between two fields of the same type is invisible to it; the pen agreement tests in `packages/baker/tests` cover that case. Breaking the pledge is a deliberate change: bump both version numbers, update the record, and write the entry in the history. The check fails until the record matches.

```sh
python3 tools/check-format-frozen.py
```

```
ok - the format is v7, the version the pledge froze
ok - MAGIC is 0x31424955, unchanged
ok - _CLUT is '<HHI', 8 bytes
ok - _CMD is '<BBHhhHHHHHHHHH6x', 32 bytes
ok - _FOCUS is '<HHHHHHIhhHH', 24 bytes
ok - _FONT is '<HHHHHHIH2xI', 24 bytes
ok - _GLYF is '<IHHHHhhH2x', 20 bytes
ok - _HEADER is '<IHHHHHHIHHIIIIIIIHHIIHHIIHHHH', 84 bytes
ok - _KERN is '<IIh2x', 12 bytes
ok - _SCREEN is '<IIIHHHHH2x', 24 bytes
ok - _SLOT is '<IIhhHHBBHHHHh', 28 bytes
ok - _TEX is '<BBHHHIII', 20 bytes
ok - _TINT is '<BBBB', 4 bytes
ok - FEAT_DYNAMIC_TEXT is still bit 0
ok - FEAT_KERNING is still bit 1
ok - FEAT_SLOT_SPACING is still bit 2
ok - FEAT_STREAMED_TEX is still bit 3
ok - FEAT_ROLE_TINTS is still bit 4
ok - FEAT_KNOWN (0x1f) still admits every frozen bit
ok - all 11 Struct(s) in uib are in the record
```

The C side is held separately. The runtime test `struct layout matches the on-disk format` in [test_runtime.c](repo:runtime/tests/test_runtime.c#L170) asserts every struct size in `ps2ui.h` against the strides above.

### History

Every struct-size change bumped the version. The entries for v5 to v7 are in [docs/format-uib.md](repo:docs/format-uib.md#L466); v1 to v4 are recorded in [docs/PLAN.md](repo:docs/PLAN.md#L92), and `check-versions.py` holds that line to run v1 through the current version.

| version | change | stride moved | feature bit |
|---|---|---|---|
| v1 | initial layout | | |
| v2 | CRC-32, feature bits, dynamic-text tables | font and slot tables added | 0 |
| v3 | multi-screen and images | screen table added | |
| v4 | display aspect | header to 76 bytes | |
| v5 | kerning | font entry 16 to 24 | 1 |
| v6 | texture kinds and streamed textures | texture entry 16 to 20 | 3 |
| v7 | the tint table; colour bytes become u16 indices | slot entry 32 to 28, header to 84 | 4 |
