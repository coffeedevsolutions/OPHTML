---
id: project/glossary
title: Glossary
description: Alphabetical terms from the toolchain and runtime, each linked to the page that uses it.
section: project
order: 74
version: 0.8.0
sources: [docs/site/ARCHITECTURE.md, docs/site/_facts/reference/uib-format.md, docs/site/_facts/runtime/frame-loop.md, docs/site/_facts/authoring/theming.md, docs/site/_facts/authoring/text-and-fonts.md, docs/site/_facts/authoring/crt-linter.md, docs/site/_facts/cli/previewer.md, docs/site/_facts/authoring/lists.md, docs/site/_facts/authoring/dynamic-text.md, docs/site/_facts/authoring/images.md, docs/site/_facts/authoring/vram-budget.md, docs/site/_facts/authoring/video-modes.md, docs/site/_facts/authoring/focus-and-navigation.md, docs/site/_facts/authoring/screens-and-overlays.md, docs/site/_facts/reference/ir-format.md, docs/site/_facts/runtime/api-reference.md, docs/site/_facts/runtime/moving-and-hiding.md, docs/site/_facts/runtime/streaming-art.md, docs/site/reference/uib-format.md, docs/site/runtime/frame-loop.md, docs/site/authoring/theming.md, docs/site/authoring/text-and-fonts.md, docs/site/authoring/crt-linter.md, docs/site/cli/previewer.md, docs/site/authoring/lists.md, docs/site/authoring/dynamic-text.md, docs/site/authoring/images.md, docs/site/authoring/vram-budget.md, docs/site/authoring/video-modes.md, docs/site/authoring/focus-and-navigation.md, docs/site/authoring/screens-and-overlays.md, docs/site/reference/ir-format.md, docs/site/runtime/api-reference.md, docs/site/runtime/streaming-art.md, docs/site/cli/ps2ui-bake.md, docs/site/cli/ps2ui-layout.md, docs/site/runtime/integrating.md]
---

# Glossary

### arena

A caller-provided buffer, aligned to 16 bytes, that `ps2ui_load` carves the
runtime's tables into. `ps2ui-bake` prints the exact byte count a blob
needs. See [the frame loop](page:runtime/frame-loop#sizing-the-arena).

### atlas

The baked texture holding every glyph a font uses, rasterized from the TTF
by the baker rather than measured from it. A codepoint outside the shipped
charset falls back to the atlas's `?` glyph. See
[text and fonts](page:authoring/text-and-fonts#the-charset).

### baker

`ps2ui-bake`, the tool that rasterizes glyph atlases and nine-patches,
flattens IR commands to GS quads, and writes the `.uib` blob. It reads TTF
files directly, where the layout stage reads only precomputed metrics. See
[ps2ui-bake](page:cli/ps2ui-bake#synopsis).

### blob

The `.uib` file the baker writes: a header, eight fixed-stride tables,
padding to 16 bytes, then packed texel and string data. A trailing CRC-32
over the zeroed header covers the whole file. See
[.uib](page:reference/uib-format#invariants).

### CLUT

A colour lookup table baked alongside a PSMT8 texture. `ps2ui_clut_set`
repoints one CLUT's palette without moving a texel, and every texture
sharing its index recolours together. See
[streaming art](page:runtime/streaming-art#reference-table).

### CSM1

The GS palette index permutation the runtime applies whenever it writes a
CLUT, at upload and inside `ps2ui_clut_set`. `ps2ui_clut_csm1` exposes the
bit-3/bit-4 swap for tests. See
[C API reference](page:runtime/api-reference#textures-and-palettes).

### command list

The blob's ordered table of QUAD, TEXQUAD, SCISSOR_PUSH and SCISSOR_POP
records that the runtime replays every frame. Layout ran at compile time,
so replaying the list is the whole render. See
[.uib](page:reference/uib-format#layout).

### composite

Two `screen_set`/`render` pairs drawn into one frame with no clear between
them, the technique behind a dialog over a base screen. `ctx->stats` and
`gsKit_TexManager_nextFrame` both describe only the last render. See
[screens and overlays](page:authoring/screens-and-overlays#compositing).

### display aspect

The panel ratio stored in the header as `display_aspect_num` and
`display_aspect_den`, independent of the framebuffer's own pixel size.
`ps2ui-check` prints it in its summary line. See
[video modes](page:authoring/video-modes#the-header-field).

### focus node

One D-pad-navigable element: a rect plus four solved neighbour ids, created
by the `focusable` attribute and nothing else. See
[focus and navigation](page:authoring/focus-and-navigation#what-it-is).

### GS

The PS2 Graphics Synthesizer. `ps2ui_render` writes its ALPHA register
every call, to the equation `Cv = (Cs - Cd) * As >> 7 + Cd`. It never
inherits whatever blend mode a host left set. See
[the frame loop](page:runtime/frame-loop#behaviour).

### gsKit

The ps2dev graphics library the runtime links against for texture and DMA
calls. It does not save or restore `PrimAlphaEnable` around `gsKit_clear`,
which is why the frame loop brackets the app's own clear. See
[integrating the runtime](page:runtime/integrating#the-cross-toolchain).

### IR

`ui.json`, the JSON the layout stage emits and the baker consumes: canvas,
fonts, themes, paint commands, the focus graph, slots and warnings, in that
order. See [ui.json](page:reference/ir-format#layout).

### kern pair

A per-size pixel adjustment between two codepoints, applied by the pen
before it places the second glyph, that shrinks toward zero as font size
drops. See [text and fonts](page:authoring/text-and-fonts#kerning).

### layout stage

`ps2ui-layout`, the compiler that turns one HTML file and one CSS file into
IR. It reads font metrics only; rasterizing glyphs is the baker's job. See
[ps2ui-layout](page:cli/ps2ui-layout#synopsis).

### list window

The runtime's `top`/`sel` bookkeeping inside `ps2ui_list`, which slides the
minimum distance to keep the selection on screen and never wraps at either
end. See [lists](page:authoring/lists#runtime-window).

### modulate domain

The GS colour range every tint index and texel alpha lives in. 128, not
255, is full scale, the domain the blend equation's `As >> 7` divides by.
See [.uib](page:reference/uib-format#command).

### montage

A render of one canvas per focusable of a screen, that focusable current on
each tile. `ps2ui serve` publishes the same render at `/montage.png`. See
[the previewer](page:cli/previewer#routes).

### nine-patch

Rounded-rectangle chrome the baker rasterizes once and slices into a baked
texture, replayed through the same texture-entry record as any other art.
See [ps2ui-bake](page:cli/ps2ui-bake#synopsis).

### PAR

Pixel aspect ratio, derived from the display aspect and the canvas ratio.
Every shipped mode is anamorphic, so no canvas draws a CSS square as a
round one on the panel. See
[video modes](page:authoring/video-modes#anamorphic-pixels).

### pen

The one walk, shared by the layout stage, the baker and the runtime, that
kerns before each glyph, records its position, then advances. Measuring,
wrapping and ellipsizing all run through it. See
[text and fonts](page:authoring/text-and-fonts#measuring-and-rounding).

### previewer

`ps2ui serve`, which builds a project or serves a bare blob and binds a
loopback port. Every frame it serves comes from the baker's own
`preview.render`. See [the previewer](page:cli/previewer#synopsis).

### PSMT8

An 8-bit indexed GS texture format: one byte per texel plus a 256-entry
PSMCT32 CLUT. See [.uib](page:reference/uib-format#texture-entry).

### PSMCT32

The default 32-bit GS texture format: four bytes per texel, alpha in the GS
0-to-128 domain, no CLUT. See
[.uib](page:reference/uib-format#texture-entry).

### role

A `var()` name kept as one tint-table entry per whole colour vector. A
theme can then move it independently of any literal that matches it by
chance. See [theming](page:authoring/theming#roles-not-values).

### scissor

The GS clip rectangle `ps2ui_render` pushes and pops around a box with
`overflow: hidden`, restored to the full canvas before the call returns.
See [the frame loop](page:runtime/frame-loop#behaviour).

### screen

One IR file baked into the blob, named by its file stem. Screens share one
texture space, one font table and one CLUT set, and every screen in a bake
must carry the same canvas. See
[screens and overlays](page:authoring/screens-and-overlays#what-it-is).

### slot (text)

A `data-slot` element: one line of runtime text with baked geometry, font
and colours, filled by `ps2ui_slot_set` and truncated at its byte capacity.
See [dynamic text](page:authoring/dynamic-text#what-it-is).

### slot (texture)

An `<img data-tex-slot>` reservation: baked geometry and a PSMCT32 byte
budget with no texels, filled at runtime by `ps2ui_tex_set`. See
[streaming art](page:runtime/streaming-art#setting-a-slot).

### tint table

The blob's theme-major colour array, one row per theme, that every painting
command and slot indexes instead of carrying RGBA directly. See
[.uib](page:reference/uib-format#tint-entry).

### title-safe

The inset the `overscan` lint measures text against, 5% of the canvas per
side, distinct from the previewer's own safe-area overlay. See
[the CRT linter](page:authoring/crt-linter#reference-table).

### .uib

The compiled blob format the baker writes and `ps2ui_load` maps directly
onto C structs, frozen at version 7. See
[.uib](page:reference/uib-format#layout).

### VRAM budget

The texture VRAM ceiling `ps2ui-bake` and `ps2ui-check` charge baked and
streamed textures against: 4 MiB minus the framebuffers the canvas needs,
by default. See [VRAM budget](page:authoring/vram-budget#what-it-is).
