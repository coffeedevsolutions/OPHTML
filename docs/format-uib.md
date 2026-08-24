# .uib — the baked UI blob

The file the console loads. Fixed-size little-endian records, designed
so the C runtime overlays plain C99 structs on the mapped file with no
parsing, no allocation, and no packing pragmas (every u32 sits at a
4-aligned offset).

```
offset 0            header        76 bytes
header.off_tex      tex table     n_tex   × 16 bytes
header.off_clut     clut table    n_clut  ×  8 bytes
header.off_cmd      command list  n_cmd   × 32 bytes
header.off_focus    focus table   n_focus × 24 bytes
header.off_font     font table    n_font  × 24 bytes
header.off_slot     slot table    n_slot  × 32 bytes
header.off_screen   screen table  n_screen × 24 bytes (always ≥ 1)
header.off_blob     blob          header.blob_len bytes
```

All `data_off`/`name_off` fields are relative to the **blob**, so tools
can rewrite tables without re-basing data pointers.

> **Alignment invariant.** The blob section's file offset and every
> texture's `data_off` within it are multiples of 16, so that a file
> placed 16-aligned in memory (as `bin2c` output is) yields
> qword-aligned DMA source addresses. A GIF source-chain REF tag has no
> low address bits; a violating address is truncated, not faulted, and
> every texture arrives shifted. The runtime refuses such a file with
> `PS2UI_ERR_ALIGN`; `ps2ui-check` asserts the same property offline.

## Header (76 bytes)

| off | type | field         | notes                          |
|-----|------|---------------|--------------------------------|
| 0   | u32  | magic         | `0x31424955` — "UIB1"          |
| 4   | u16  | version       | 5                              |
| 6   | u16  | feature_flags | bit 0 = dynamic text, bit 1 = kerning, bit 2 = slot letter-spacing, bit 3 = streamed textures; a reader that sees a bit it does not know MUST reject the file |
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
| 64  | u16  | n_screen      | ≥ 1 — every file has a screen table |
| 66  | u16  | pad           |                                |
| 68  | u32  | off_screen    |                                |
| 72  | u16  | display_aspect_num | panel aspect numerator, e.g. 16 |
| 74  | u16  | display_aspect_den | denominator, e.g. 9        |

**Display aspect.** The framebuffer is a pixel grid; the television
decides how wide it is drawn, and on this hardware the two disagree
even in the ordinary case. 640x448 shown as 4:3 has a pixel aspect
ratio of 0.9333, and shown as 16:9 it is 1.2444. PS2 widescreen is
anamorphic: the same grid, stretched. Consumers derive
`PAR = (num/den) / (canvas_w/canvas_h)`; the runtime exposes it as
`ps2ui_pixel_aspect_x1000()`. The renderer draws in framebuffer pixels
regardless, so this field exists to keep the previewer honest and to
let an app assert its video setup matches what the UI was authored
for.

## Texture entry (20 bytes)

| off | type | field    | notes                                          |
|-----|------|----------|------------------------------------------------|
| 0   | u8   | format   | 0 = PSMT8 (indexed), 1 = PSMCT32               |
| 1   | u8   | kind     | 0 = baked, 1 = streamed                        |
| 2   | u16  | width    | texels                                         |
| 4   | u16  | height   |                                                |
| 6   | u16  | clut     | CLUT index, `0xFFFF` = none                    |
| 8   | u32  | data_off | into blob; **unused when streamed**            |
| 12  | u32  | data_len | bytes; **the reservation when streamed**       |
| 16  | u32  | name_off | NUL-terminated name in blob, `0xFFFFFFFF` = none |

### Baked and streamed

A **baked** texture is every texture that existed before v6: its texels
are in the blob and the GIF DMAs them in place out of the caller's
file.

Authored as `<img data-tex-slot="name">` with an explicit width and
height in CSS (there is no file to take an intrinsic size from). See
the README's images section.

A **streamed** texture is a slot the application fills at runtime —
cover art off a disc, HDD or network, which cannot be baked because
nothing at bake time knows what it is. The entry carries geometry, a
name, and a reservation, and **no texel data**. `ps2ui_tex_set(ctx, gs,
name, texels, len)` points it at the caller's buffer; `len` must equal
`data_len` exactly.

Nothing is copied. `texels` becomes that slot's DMA source, so it must
stay alive, unmoved and 16-aligned for as long as the slot can be
drawn — the same contract the blob itself already has, and for the same
reason: gsKit re-reads the source whenever the texture manager re-binds
an evicted texture, which is render time, not upload time.

Rules a reader enforces, all of which the runtime refuses at load:

- a `kind` outside `{0, 1}` is invalid;
- a streamed entry requires **feature bit 3**, so a reader that cannot
  stream rejects the file instead of drawing a slot nothing can fill;
- a streamed entry needs a name (otherwise nothing could address it)
  and a non-zero reservation;
- `data_off` is **not** range-checked for a streamed entry — it
  addresses nothing;
- a font's atlas must be baked: the glyph pen binds it without
  checking for texels;
- texture names are unique.

A streamed slot that has not been filled draws nothing and increments
`stats.tex_unfilled`. That is the ordinary state of a row that has just
scrolled into view, not an error.

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

## Font entry (24 bytes) — dynamic text

| off | type | field       | notes                                |
|-----|------|-------------|--------------------------------------|
| 0   | u16  | tex         | PSMT8 glyph-atlas texture index      |
| 2   | u16  | size        | px                                   |
| 4   | u16  | weight      | 400 / 700                            |
| 6   | u16  | ascent      | px, from the metrics JSON            |
| 8   | u16  | line_height | px                                   |
| 10  | u16  | glyph_count |                                      |
| 12  | u32  | glyphs_off  | glyph records in blob, **codepoint-sorted** for bsearch |
| 16  | u16  | kern_count  | 0 unless feature bit 1               |
| 18  | u16  | pad         |                                      |
| 20  | u32  | kerns_off   | kern records in blob, **pair-sorted** for bsearch |

Glyph record (20 bytes, in blob): `u32 codepoint; u16 u,v,w,h;
i16 bearing_x, bearing_y; u16 advance; u16 pad`. `bearing_y` is
measured from the line-box top via the metrics ascent; `advance` obeys
the shared rounding rule, so runtime-composed text lands exactly where
static text would have.

Kern record (12 bytes, in blob): `u32 prev, cur; i16 amount; u16 pad`.
`amount` is **already in pixels at this font's size** — the EE is not
going to divide by 1000 per glyph pair — and is negative in almost
every case. Sorted by `(prev, cur)`, so a reader binary-searches the
pair exactly as it does a codepoint.

The pair is ordered: `To` and `oT` are different entries and a font may
adjust one and not the other. Pairs whose adjustment rounds to zero at
this size are not stored, which is most of them at UI sizes — kerning
is a sub-em correction and only survives rounding once the text is
large. Feature bit 1 is set only when some font ends up with pairs, so
a reader can skip the lookup wholesale rather than infer it from a zero
count. In the two shipped examples the tables are 2.0% and 2.8% of the
file.

**The pen.** Every stage walks a string the same way, and they must
agree to the pixel or text drifts out of the box that was measured for
it: for each glyph after the first, add the letter-spacing and the kern
for `(previous, current)`, place the glyph, then add its advance. The
three implementations are `Font.layout` (layout), `_flatten_text`
(baker) and `render_slots` (runtime).

One known divergence, deliberate: when a string overflows a slot, the
build-time `ellipsize` strips trailing spaces before attaching `…` and
searches from the back, while the runtime (and the previewer, which
mirrors the runtime) uses a one-pass greedy fit that keeps them. The
same string can therefore cut one glyph differently between a baked
placeholder and the same text set at runtime. Both results fit the box;
the runtime's version is the one a player sees.

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
| 30  | i16  | letter_spacing  | px per glyph junction; feature bit 2 |

The runtime (`ps2ui_slot_set`) copies app strings into fixed per-slot
buffers and composes glyph quads per frame: advance walk, optional
ellipsis, alignment — no wrapping, no allocation.

`letter_spacing` occupies what was pad. Every writer before the field
wrote zeros there, and zero spacing is the meaning zeros already had,
so the stride is unchanged and no version moved; feature bit 2 is what
makes the field loud — it is set only when some slot carries a
non-zero value, and a reader that predates it rejects the file rather
than silently drawing unspaced text next to a box that was measured
spaced. The pen applies it at every glyph junction, added to the kern,
including the junction into the ellipsis.

## Screen entry (24 bytes)

| off | type | field         | notes                                |
|-----|------|---------------|--------------------------------------|
| 0   | u32  | name_off      | NUL-terminated UTF-8 in blob         |
| 4   | u32  | cmd_first     | index into the command list          |
| 8   | u32  | cmd_count     |                                      |
| 12  | u16  | focus_first   | index into the focus table           |
| 14  | u16  | focus_count   |                                      |
| 16  | u16  | slot_first    | index into the slot table            |
| 18  | u16  | slot_count    |                                      |
| 20  | u16  | initial_focus | global focus index or `0xFFFF`       |
| 22  | u8×2 | pad           |                                      |

Screens partition commands, focus nodes and slots into contiguous
ranges; textures, CLUTs and font tables are shared across screens.
Focus indices are global and each screen's D-pad graph links only
within its own range, so `ps2ui_screen_set` is: remember the current
focus, switch ranges, restore the target's remembered focus (or its
baked initial). The header's `initial_focus` duplicates screen 0's.

## Versioning

`version` bumps on any incompatible change. Readers must reject unknown
versions (the runtime and the Python reader both do).

- **v6** — texture kinds. The texture entry grew from 16 to 20 bytes
  for `kind` and `name_off`, and feature bit 3 was assigned for
  streamed textures. A v5 reader would have walked the texture table at
  the wrong stride, so this is a version bump rather than a bit alone.
  The `pad` byte at offset 1 became `kind`, and every writer before v6
  wrote zero there — which is `PS2UI_TEXKIND_BAKED`, the meaning the
  zeros already had.
- **v5** — kerning. The font entry grew from 16 to 24 bytes for
  `kern_count`/`kerns_off`, and feature bit 1 was assigned. The struct
  changed size, so this is a version bump rather than a bit alone: a v4
  reader would have walked the font table at the wrong stride.
