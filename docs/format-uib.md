# .uib — the baked UI blob

The file the console loads. Fixed-size little-endian records, designed
so the C runtime overlays plain C99 structs on the mapped file with no
parsing, no allocation, and no packing pragmas (every u32 sits at a
4-aligned offset).

```
offset 0            header        64 bytes
header.off_tex      tex table     n_tex   × 16 bytes
header.off_clut     clut table    n_clut  ×  8 bytes
header.off_cmd      command list  n_cmd   × 32 bytes
header.off_focus    focus table   n_focus × 24 bytes
header.off_font     font table    n_font  × 16 bytes
header.off_slot     slot table    n_slot  × 32 bytes
header.off_blob     blob          header.blob_len bytes
```

All `data_off`/`name_off` fields are relative to the **blob**, so tools
can rewrite tables without re-basing data pointers.

## Header (64 bytes)

| off | type | field         | notes                          |
|-----|------|---------------|--------------------------------|
| 0   | u32  | magic         | `0x31424955` — "UIB1"          |
| 4   | u16  | version       | 2                              |
| 6   | u16  | feature_flags | bit 0 = dynamic text; a reader that sees a bit it does not know MUST reject the file |
| 8   | u16  | canvas_w      | 640 for NTSC                   |
| 10  | u16  | canvas_h      | 448 (NTSC) / 512 (PAL)         |
| 12  | u16  | n_tex         |                                |
| 14  | u16  | n_clut        |                                |
| 16  | u32  | n_cmd         |                                |
| 20  | u16  | n_focus       |                                |
| 22  | u16  | initial_focus | focus index, `0xFFFF` = none   |
| 24  | u32×6| off_tex, off_clut, off_cmd, off_focus, off_blob, blob_len |
| 48  | u32  | crc32         | IEEE CRC-32 of the whole file with this field zeroed (matches zlib) |
| 52  | u16  | n_font        | dynamic-text font tables       |
| 54  | u16  | n_slot        | dynamic-text slots             |
| 56  | u32×2| off_font, off_slot |

## Texture entry (16 bytes)

| off | type | field    | notes                                  |
|-----|------|----------|----------------------------------------|
| 0   | u8   | format   | 0 = PSMT8 (indexed), 1 = PSMCT32       |
| 1   | u8   | pad      |                                        |
| 2   | u16  | width    | texels                                 |
| 4   | u16  | height   |                                        |
| 6   | u16  | clut     | CLUT index, `0xFFFF` = none            |
| 8   | u32  | data_off | into blob                              |
| 12  | u32  | data_len | bytes                                  |

PSMCT32 texel = `r g b a` bytes with **alpha already in the GS 0–128
domain** (0x80 = opaque). PSMT8 texels are CLUT indices; glyph atlases
use index = coverage with a white alpha-ramp CLUT and are tinted by
vertex color (`GS_TFX_MODULATE`).

## CLUT entry (8 bytes)

| off | type | field    |
|-----|------|----------|
| 0   | u16  | ncolors  |
| 2   | u16  | pad      |
| 4   | u32  | data_off |

Entries are PSMCT32 colors stored **linearly** (index 0 first). The GS
CSM1 storage order — the bit-3/bit-4 index swap — is applied by the
uploader (`ps2ui_clut_csm1`), never by the file. A hex dump of a .uib
CLUT reads in palette order.

## Command (32 bytes)

| off | type | field   | notes                                       |
|-----|------|---------|---------------------------------------------|
| 0   | u8   | op      | 0 QUAD, 1 TEXQUAD, 2 SCISSOR_PUSH, 3 SCISSOR_POP |
| 1   | u8   | state   | 0 always, 1 unfocused, 2 focused            |
| 2   | u16  | focus   | focus index, `0xFFFF` = none                |
| 4   | i16  | x       |                                             |
| 6   | i16  | y       |                                             |
| 8   | u16  | w       |                                             |
| 10  | u16  | h       |                                             |
| 12  | u8×4 | r g b a | vertex color, see domain note below         |
| 16  | u16  | tex     | texture index (TEXQUAD), else `0xFFFF`      |
| 18  | u16×4| u0 v0 u1 v1 | texel source rect, u1/v1 exclusive      |
| 26  | u8×6 | pad     |                                             |

**Color domain note.** Alpha is always in the GS 0–128 domain (0x80 =
opaque). RGB depends on the op: a **QUAD** is flat-shaded, so `r g b`
are full-range 0–255; a **TEXQUAD** is drawn with `TEX MODULATE`
(`Cv = Ct·Cf >> 7`), so its `r g b` are in the 0x80-identity domain —
`0x80 0x80 0x80` is an untinted texture, and values above 0x80
overbright. The baker converts exactly once; writers of .uib files
must do the same or tinted textures render up to 2× too bright on
hardware.

Draw rule per frame with current focus index `F`:

```
visible(cmd) = cmd.state == ALWAYS
            || (cmd.state == FOCUSED   && cmd.focus == F)
            || (cmd.state == UNFOCUSED && cmd.focus != F)
```

Commands replay strictly in file order. Scissor commands nest by
intersection; the baker guarantees balance.

## Focus node (24 bytes)

| off | type | field    | notes                              |
|-----|------|----------|------------------------------------|
| 0   | u16  | id       | == its own table index             |
| 2   | u16×4| up down left right | neighbor indices, `0xFFFF` = none |
| 10  | u16  | pad      |                                    |
| 12  | u32  | name_off | NUL-terminated UTF-8 in blob       |
| 16  | i16×2| x y      | on-screen rect (for debugging/HUD) |
| 20  | u16×2| w h      |                                    |

The graph is solved at build time; a D-pad press is one table lookup.

## Font entry (16 bytes) — dynamic text

| off | type | field       | notes                                |
|-----|------|-------------|--------------------------------------|
| 0   | u16  | tex         | PSMT8 glyph-atlas texture index      |
| 2   | u16  | size        | px                                   |
| 4   | u16  | weight      | 400 / 700                            |
| 6   | u16  | ascent      | px, from the metrics JSON            |
| 8   | u16  | line_height | px                                   |
| 10  | u16  | glyph_count |                                      |
| 12  | u32  | glyphs_off  | glyph records in blob, **codepoint-sorted** for bsearch |

Glyph record (20 bytes, in blob): `u32 codepoint; u16 u,v,w,h;
i16 bearing_x, bearing_y; u16 advance; u16 pad`. `bearing_y` is
measured from the line-box top via the metrics ascent; `advance` obeys
the shared rounding rule, so runtime-composed text lands exactly where
static text would have.

## Slot entry (32 bytes) — dynamic text

| off | type | field           | notes                              |
|-----|------|-----------------|------------------------------------|
| 0   | u32  | name_off        | NUL-terminated UTF-8 in blob       |
| 4   | u32  | placeholder_off | rendered until the app sets text   |
| 8   | i16  | x               | content-left px                    |
| 10  | i16  | text_y          | glyph-box top px                   |
| 12  | u16  | w               | content width px                   |
| 14  | u16  | font            | font table index                   |
| 16  | u8   | align           | 0 left, 1 center, 2 right          |
| 17  | u8   | flags           | bit 0 = ellipsize overflow         |
| 18  | u16  | capacity        | max runtime bytes                  |
| 20  | u16  | focus           | focus index or `0xFFFF`            |
| 22  | u8×4 | color_base      | modulate domain, like any TEXQUAD  |
| 26  | u8×4 | color_focus     |                                    |
| 30  | u8×2 | pad             |                                    |

The runtime (`ps2ui_slot_set`) copies app strings into fixed per-slot
buffers and composes glyph quads per frame: advance walk, optional
ellipsis, alignment — no wrapping, no allocation.

## Versioning

`version` bumps on any incompatible change. Readers must reject unknown
versions (the runtime and the Python reader both do).
