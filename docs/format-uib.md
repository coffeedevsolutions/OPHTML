# .uib — the baked UI blob

The file the console loads. Fixed-size little-endian records, designed
so the C runtime overlays plain C99 structs on the mapped file with no
parsing, no allocation, and no packing pragmas (every u32 sits at a
4-aligned offset).

```
offset 0            header        48 bytes
header.off_tex      tex table     n_tex   × 16 bytes
header.off_clut     clut table    n_clut  ×  8 bytes
header.off_cmd      command list  n_cmd   × 32 bytes
header.off_focus    focus table   n_focus × 24 bytes
header.off_blob     blob          header.blob_len bytes
```

All `data_off`/`name_off` fields are relative to the **blob**, so tools
can rewrite tables without re-basing data pointers.

## Header (48 bytes)

| off | type | field         | notes                          |
|-----|------|---------------|--------------------------------|
| 0   | u32  | magic         | `0x31424955` — "UIB1"          |
| 4   | u16  | version       | 1                              |
| 6   | u16  | flags         | 0                              |
| 8   | u16  | canvas_w      | 640 for NTSC                   |
| 10  | u16  | canvas_h      | 448 for NTSC                   |
| 12  | u16  | n_tex         |                                |
| 14  | u16  | n_clut        |                                |
| 16  | u32  | n_cmd         |                                |
| 20  | u16  | n_focus       |                                |
| 22  | u16  | initial_focus | focus index, `0xFFFF` = none   |
| 24  | u32×6| off_tex, off_clut, off_cmd, off_focus, off_blob, blob_len |

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

## Versioning

`version` bumps on any incompatible change. Readers must reject unknown
versions (the runtime and the Python reader both do).
