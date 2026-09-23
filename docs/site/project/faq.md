---
id: project/faq
title: FAQ
description: Twenty questions the code answers, each linked to the page that proves it.
section: project
order: 73
version: 0.8.0
sources: [docs/site/ARCHITECTURE.md, docs/findings.md, docs/site/_facts/authoring/css.md, docs/site/_facts/authoring/text-and-fonts.md, docs/site/_facts/getting-started/installation.md, docs/site/_facts/runtime/frame-loop.md, docs/site/_facts/runtime/errors-and-constants.md, docs/site/_facts/runtime/streaming-art.md, docs/site/_facts/cli/previewer.md, docs/site/_facts/authoring/screens-and-overlays.md, docs/site/_facts/runtime/moving-and-hiding.md, docs/site/_facts/authoring/vram-budget.md, docs/site/_facts/authoring/dynamic-text.md, docs/site/_facts/authoring/lists.md, docs/site/_facts/cli/ps2ui-check.md, docs/site/_facts/cli/ps2ui-fontgen.md, docs/site/_facts/authoring/html.md, docs/site/_facts/runtime/integrating.md, docs/site/authoring/css.md, docs/site/authoring/text-and-fonts.md, docs/site/getting-started/installation.md, docs/site/runtime/frame-loop.md, docs/site/runtime/errors-and-constants.md, docs/site/runtime/streaming-art.md, docs/site/cli/previewer.md, docs/site/authoring/screens-and-overlays.md, docs/site/authoring/lists.md, docs/site/cli/ps2ui-check.md, docs/site/authoring/vram-budget.md, docs/site/authoring/html.md, docs/site/authoring/dynamic-text.md, docs/site/runtime/integrating.md]
---

# FAQ

### Why is flex-direction required

A container laying out two or more children must declare `flex-direction`.
CSS's initial value is `row` and ps2ui once used `column`, so no silent
default is right for every author. A container with one child or none is
never asked, because the answer would not change the drawn layout. See
[CSS](page:authoring/css#the-two-hard-rules).

### Why px only

`px` is the only unit most length properties accept: `gap`, `padding`,
`margin`, `border-width`, `border-radius`, `font-size` and
`letter-spacing`. `width`, `height`, `min-*`, `max-*` and `flex-basis`
also take `%` and `auto`. `em`, `rem`, `vw`, `vh` and `ch` are refused by
name, because the format bakes pixel geometry once at compile time. See
[CSS](page:authoring/css#units).

### Why only eight named colours

The named set is `black`, `white`, `red`, `green`, `blue`, `gray`, `grey`
and `transparent`, and nothing else. Any other name, `orange` included, is
a compile error naming the token. Hex and `rgb()`/`rgba()` forms cover
every other colour a screen needs. See [CSS](page:authoring/css#colours).

### fontgen refuses on macOS

`ps2ui fontgen` checks `features.check("raqm")` before opening a font and
refuses to write a metrics file without it. On macOS the remedy is
`brew install fribidi` first, then rebuilding Pillow against `libraqm` if
that does not clear it. Verify with `features.check('raqm')`, not pip's
exit status. See
[Installation](page:getting-started/installation#if-fontgen-refuses).

### Text is boxes on the console

`ps2ui_render` sets `PrimAlphaEnable` to `GS_SETTING_ON` every call,
because gsKit feeds that field to `TEX0.TCC` as well as `PRIM.ABE`. TCC
off tells the GS a glyph atlas is opaque RGB, so every glyph fills its
quad as a solid block (F-004). Restore the field to ON after any app
clear that turned it off. See
[The frame loop](page:runtime/frame-loop#behaviour).

### Solid fills vanish on the console

gsKit's default blend runs backwards: coverage comes out `128 - As`, not
`As` (F-002). An opaque fill authored at `As = 128` composites to zero
coverage under that default, so it disappears. `ps2ui_render` writes its
own `GS_SETREG_ALPHA` every call for exactly this reason, rather than
inheriting gsKit's state. See
[The frame loop](page:runtime/frame-loop#behaviour).

### The arena error at boot

`ps2ui_load` returns `PS2UI_ERR_ARENA` when the `arena` pointer is NULL or
`arena_size` is below `ps2ui_arena_size()`. Size the arena from the bake
transcript's arena line, or call `ps2ui_arena_size` before declaring the
buffer. The figure is per blob and per target, not a constant to
hardcode. See
[Errors and constants](page:runtime/errors-and-constants#error-codes).

### The size error when setting a texture

`ps2ui_tex_set` returns `PS2UI_ERR_SIZE` when `len` differs from the
streamed texture's reservation by any amount. Pass the `payload` figure
from the bake's VRAM breakdown, not the page-rounded `in pages` figure.
The call reports a bare code and never states the size it expected. See
[Streaming art](page:runtime/streaming-art#limits-and-errors).

### The previewer does not show hidden rows

`preview.render` and `ps2ui serve` take no visibility parameter, so a
served page always draws the baked state. A node hidden with
`ps2ui_visible_set` still looks focusable in the previewer and is not on
the console. The runtime list window has the same gap: nothing shows
`top` or `sel` moving. See [Previewer](page:cli/previewer#limits).

### Can I draw over a game

There is no compositing API, only two ordinary renders. Call
`ps2ui_screen_set` and `ps2ui_render` for the overlay after the base
screen, in the same frame, since `ps2ui_render` never clears. The Python
previewer cannot draw the composite itself; a workaround script renders
on a transparent background and alpha-composites the result over a
synthetic frame instead. See
[Screens and overlays](page:authoring/screens-and-overlays#compositing).

### How do I scroll

There is no CSS scrolling; `overflow` accepts only `visible` and
`hidden`. Author a fixed-size window of rows with `data-repeat`, then
drive it at runtime with the `ps2ui_list` API. `list_move` and
`list_select` slide the window the minimum distance to show the
selection; it never wraps or recentres. See
[Lists](page:authoring/lists#runtime-window).

### How do I make a dialog

A dialog is a second screen, baked into the same blob and rendered on
top of the base in one frame. Call `ps2ui_screen_set` to the dialog's
name before the second `ps2ui_render`; the last `screen_set` also owns
the D-pad. Dismissing is one `screen_set` back to the base, which
restores the focus the user left there. See
[Screens and overlays](page:authoring/screens-and-overlays#minimal-example).

### ps2ui check prints a negative budget

Past a canvas width, three framebuffers plus the texture budget do not
fit in 4 MiB of VRAM, and the default budget goes negative.
`ps2ui-check`'s VRAM label then reads
`-- the default budget is unusable at this canvas, see notes`, with two
note lines stating the arithmetic. Declare `vramBudget` for the buffer
count the target actually holds, since a console with `ZBuffering` off
keeps two buffers, not three. See [ps2ui-check](page:cli/ps2ui-check#vram).

### What the payload column means

`payload` is the raw byte count: `len(data)` for a baked texture, the
reservation for a streamed one. It is the exact `len` argument
`ps2ui_tex_set` demands; the page-rounded `in pages` figure is
`PS2UI_ERR_SIZE` if passed instead. The two agree only when a texture
already fills whole 8 KiB pages. See
[VRAM budget](page:authoring/vram-budget#which-number-the-runtime-wants).

### Which number is the arena

`ps2ui-check` prints two arena figures because `GSTEXTURE` holds
pointers, wider on a 64-bit host than on the EE. Ship the first figure,
the one `ps2ui-bake` also prints. The number belongs to one blob and one
target; never copy it from a snippet or another build. See
[ps2ui-check](page:cli/ps2ui-check#the-arena-note).

### Can I use a weight axis

No. There are two faces, regular and bold, and nothing between them.
`font-weight` at or above 600 selects the bold face; below it selects
regular, whatever CSS number was written. See
[Text and fonts](page:authoring/text-and-fonts#faces-and-weights).

### Does &nbsp; work

`&nbsp;` decodes to U+00A0, but the whitespace-collapse pass then matches
it as ordinary whitespace and turns it into U+0020. A no-break space
cannot survive that collapse, so nothing forces two words to stay
together on one line. See [HTML](page:authoring/html#text-and-whitespace).

### Why is my slot text cut

`ps2ui_slot_set` copies at most `data-slot-capacity` bytes into the
slot's buffer, then drops a trailing partial UTF-8 sequence. Capacity
counts bytes, not characters, and defaults to 63 when the attribute is
absent. Add `text-overflow: ellipsis` to cut visually with `…`, or widen
the box, or raise the capacity. See
[Dynamic text](page:authoring/dynamic-text#truncation).

### Two screens use the same slot name

Slot names resolve over the whole blob, not per screen; `ps2ui_slot_set`
walks every slot and takes the first match. The baker refuses a name
repeated on two screens at bake time, naming both. Prefix per-screen
slots with the screen name, as the sample's telemetry lines do. See
[Dynamic text](page:authoring/dynamic-text#names).

### Which test target do I run

Run `make -C runtime test`, which chains `syntax-check`, `timing-check`
and `test-narrow` before the 410-check `test_runtime` suite. Add
`make -C runtime syntax-check CC=clang` to check the same sources under a
second compiler. There is no `test-compat` target; running one fails with
no rule to make it. See
[Integrating the runtime](page:runtime/integrating#what-the-host-targets-prove).
