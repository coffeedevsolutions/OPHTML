---
id: runtime/api-reference
title: C API reference
description: Every public function in ps2ui.h with its return convention, scope and ordering rule, plus the public structs and constants.
section: runtime
order: 42
version: 0.6.0
sources: [runtime/ps2ui.h, runtime/ps2ui.c, runtime/tests/test_runtime.c, runtime/stub/gskit_stub.h, runtime/Makefile, runtime/vendor/host-shim/kernel.h, runtime/sample/main.c, packages/baker/ps2ui_bake/caps.py, README.md, docs/site/_facts/README.md]
---

# C API reference

`runtime/ps2ui.h` declares the whole runtime interface. The header is C99, has an `extern "C"` guard, and includes `gsKit.h` and `kernel.h` itself, so it needs gsKit on the include path on the console and the vendored copy on a host. Count the prototypes with the command below.

```sh
grep -nE '^(int|void|size_t|uint32_t|const char \*)\s*ps2ui_[a-z_0-9]+\(' runtime/ps2ui.h | wc -l
```

```
29
```

The 29 functions appear in the group tables below, once each. Every signature was compiled in this session from a scratch file that calls each function once, using the host flags from [runtime/Makefile](repo:runtime/Makefile#L5).

```sh
cd runtime && cc -std=c99 -Wall -Wextra -Werror -Istub -Ivendor/gsKit -Ivendor/host-shim -I. -c api_check.c
```

The scope column says which names a call resolves. "Blob" means the whole file. "Screen" means the current screen only, so a name that exists on another screen returns the failure value. Error codes and what triggers them are on [Errors and constants](page:runtime/errors-and-constants#error-codes). The per-frame call order is on [The frame loop](page:runtime/frame-loop#reference-table).

## Function tables by group

### Return conventions

Four conventions cover every function. The returns column of each table names the one that applies.

| convention | functions | meaning |
|---|---|---|
| code | `load`, `tex_set`, `clut_set`, `theme_set`, `offset_set` | `PS2UI_OK` (0) on success, a negative `PS2UI_ERR_*` value otherwise |
| 0 / -1 | `upload` | 0 on success, -1 when the VRAM preflight fails |
| 1 / 0 | `screen_set`, `focus_set`, `slot_set`, `visible_set`, `move`, `list_move`, `list_select` | 1 when the call took effect, 0 when it did not |
| value | everything else | the answer itself; `NULL`, 0 or -1 stands for "no answer" as the table says |

### Lifecycle

| signature | returns | scope | notes |
|---|---|---|---|
| `size_t ps2ui_arena_size(const void *data, size_t size)` | bytes, or 0 when the header or tables do not fit in `size` | blob | Reads counts only. Does not validate the blob or touch the GS. |
| `int ps2ui_load(ps2ui_ctx *ctx, const void *data, size_t size, void *arena, size_t arena_size)` | code | blob | Zeroes `ctx`, validates, points `ctx` into `data` and `arena`. A refused blob never writes the arena. `arena` must be `PS2UI_ARENA_ALIGN` aligned and at least `ps2ui_arena_size()` bytes. |
| `int ps2ui_upload(ps2ui_ctx *ctx, GSGLOBAL *gs)` | 0 / -1 | blob | Sums VRAM for every texture first. On -1 nothing is transferred and `ctx->uploaded` stays 0. Streamed slots are budgeted but not bound until `tex_set`. |

### Rendering

| signature | returns | scope | notes |
|---|---|---|---|
| `void ps2ui_render(ps2ui_ctx *ctx, GSGLOBAL *gs)` | none | screen | Replays the current screen for the current focus. Never clears. Leaves the scissor at the full canvas. Resets `ctx->stats` on entry. |

### Screens

| signature | returns | scope | notes |
|---|---|---|---|
| `int ps2ui_screen_set(ps2ui_ctx *ctx, const char *name)` | 1 / 0 | blob | Saves the current screen's focus and restores the target's remembered focus, else its baked initial focus. The last call before `render` owns the D-pad. |
| `const char *ps2ui_screen_name(const ps2ui_ctx *ctx)` | name, never `NULL` after load | screen | |

### Focus

| signature | returns | scope | notes |
|---|---|---|---|
| `int ps2ui_move(ps2ui_ctx *ctx, ps2ui_dir dir)` | 1 / 0 | screen | Follows the baked graph. Walks past hidden nodes in the same direction. Returns 0 at an edge or when every candidate is hidden. |
| `int ps2ui_focus_set(ps2ui_ctx *ctx, const char *name)` | 1 / 0 | screen | Reaches a hidden node. Names are unique per screen only, which is why the lookup is screen-scoped. |
| `const char *ps2ui_focus_name(const ps2ui_ctx *ctx)` | name, or `NULL` when nothing is focused | screen | Switch on this value in the app's accept handler. The blob carries no callbacks. |

### Slots

| signature | returns | scope | notes |
|---|---|---|---|
| `int ps2ui_slot_set(ps2ui_ctx *ctx, const char *name, const char *text)` | 1 / 0 | blob | Copies `text`, truncated at the slot's baked capacity without splitting a UTF-8 sequence. `NULL` restores the placeholder. `""` blanks the slot. |
| `const char *ps2ui_slot_get(const ps2ui_ctx *ctx, const char *name)` | runtime text, else the placeholder, or `NULL` for an unknown name | blob | |

Slot lookup walks every slot in the blob, at [ps2ui.c](repo:runtime/ps2ui.c#L1397). Two screens cannot share a slot name and stay distinguishable. Focus and visibility lookups walk only the current screen's range, at [ps2ui.c](repo:runtime/ps2ui.c#L1557).

### Textures and palettes

| signature | returns | scope | notes |
|---|---|---|---|
| `int ps2ui_tex_set(ps2ui_ctx *ctx, GSGLOBAL *gs, const char *name, const void *texels, size_t len)` | code | blob | `len` must equal the slot's reservation exactly. `texels` becomes the DMA source: 16-aligned, alive and unmoved while the slot can draw. Nothing is copied. Call again to swap. |
| `int ps2ui_clut_set(ps2ui_ctx *ctx, GSGLOBAL *gs, unsigned clut_index, const void *colors, unsigned ncolors)` | code | blob | `colors` is linear; the CSM1 permutation is applied on the way in. Recolours every texture sharing the index. `ncolors` below the baked width leaves the tail transparent black. Refused before `upload`. |
| `int ps2ui_theme_set(ps2ui_ctx *ctx, unsigned theme)` | code | blob | Moves the live tint row. No GS traffic. Takes effect on the next `render`. Row 0 is the only legal value on a one-row blob. |
| `uint32_t ps2ui_clut_csm1(uint32_t index)` | the permuted index | none | Swaps bits 3 and 4. An involution over 0..255. Exposed for tests. |

Streaming and palette swaps are described on [Streaming art](page:runtime/streaming-art#setting-a-slot). The tint table and `theme_set` are described on [Theming](page:authoring/theming#runtime).

### Visibility

| signature | returns | scope | notes |
|---|---|---|---|
| `int ps2ui_visible_set(ps2ui_ctx *ctx, const char *name, int visible)` | 1 / 0 | screen | Hides or shows one focus node's subtree, slots included. Geometry does not reflow. A hidden node is skipped by `move`. The bit survives a screen round trip. |
| `int ps2ui_visible_get(const ps2ui_ctx *ctx, const char *name)` | 1 shown, 0 hidden, `PS2UI_VISIBLE_UNKNOWN` for an unknown name | screen | |
| `void ps2ui_visible_reset(ps2ui_ctx *ctx)` | none | blob | Clears every hidden bit on every screen. |

### Offset

| signature | returns | scope | notes |
|---|---|---|---|
| `int ps2ui_offset_set(ps2ui_ctx *ctx, int dx, int dy)` | code | blob | Draw-time translation of every command and derived scissor. The canvas scissor stays put. A value outside int16 is `PS2UI_ERR_RANGE` and the old offset stays. |
| `void ps2ui_offset_get(const ps2ui_ctx *ctx, int *dx, int *dy)` | none | blob | Either pointer may be `NULL`. Queries stay in UI coordinates; add the offset when drawing beside the UI. |

Visibility and the offset are worked through on [Moving and hiding](page:runtime/moving-and-hiding#visibility).

### Lists

| signature | returns | scope | notes |
|---|---|---|---|
| `void ps2ui_list_init(ps2ui_list *list, const char *prefix, uint16_t rows)` | none | none | Binds `rows` baked rows named `prefix` + index. `count`, `top` and `sel` start at 0. |
| `void ps2ui_list_set_count(ps2ui_ctx *ctx, ps2ui_list *list, uint16_t count)` | none | screen | Clamps `sel` and `top`. Moves focus to the clamped row when `ctx` is not `NULL`. |
| `int ps2ui_list_move(ps2ui_ctx *ctx, ps2ui_list *list, int delta)` | 1 / 0 | screen | Clamps at both ends, no wrap. Scrolls the window the minimum distance. Focuses the row. |
| `int ps2ui_list_select(ps2ui_ctx *ctx, ps2ui_list *list, uint16_t item)` | 1 / 0 | screen | Absolute form of `list_move`. Out-of-range clamps to the last item. |
| `int ps2ui_list_item_at(const ps2ui_list *list, uint16_t row)` | item index, or -1 past the end of rows or data | none | The refill loop: fill row `r` from item `top + r`, blank on -1. |
| `int ps2ui_list_selected_row(const ps2ui_list *list)` | row 0..rows-1, or -1 for an empty list | none | |
| `void ps2ui_list_apply_visibility(ps2ui_ctx *ctx, const ps2ui_list *list)` | none | screen | Hides rows whose `item_at` is -1 and shows the rest, by row name. |

The row-name convention is `prefix` followed by the decimal row index, built at [ps2ui.c](repo:runtime/ps2ui.c#L1646). Row focus names come from `data-repeat`, described on [Lists](page:authoring/lists#runtime-window).

### Queries

| signature | returns | scope | notes |
|---|---|---|---|
| `uint32_t ps2ui_pixel_aspect_x1000(const ps2ui_ctx *ctx)` | authored pixel aspect times 1000; 1000 when the header cannot answer | blob | 933 is 4:3 at 640x448. Above 1000 means pixels draw wider than tall. |
| `uint32_t ps2ui_crc32(const void *data, size_t len)` | CRC-32, IEEE reflected | none | The blob integrity check. Exposed for tests. |

## Structs

### Context struct

`ps2ui_ctx` is a public struct, and the app owns its storage. Read the fields below directly. Write the ones marked with a function through that function only, because `render` indexes tables by `screen`, `focus` and `theme` without re-checking them.

| field | type | meaning | write through |
|---|---|---|---|
| `hdr` | `const ps2ui_header *` | the blob header: counts, canvas, feature bits, display aspect | `load` |
| `tex`, `clut`, `cmd`, `focus_nodes`, `blob`, `fonts`, `slots`, `screen_table`, `tints` | const table pointers | the blob's tables, pointing into `data` | `load` |
| `screen` | `uint16_t` | current screen index | `screen_set` |
| `focus` | `uint16_t` | current focus index, or `PS2UI_NONE` | `focus_set`, `move`, `screen_set` |
| `theme` | `uint16_t` | live tint row | `theme_set` |
| `off_x`, `off_y` | `int16_t` | draw-time offset | `offset_set` |
| `stats` | `ps2ui_stats` | counters for the last `render` | `render` |
| `uploaded`, `vram_need` | `int`, `uint32_t` | set by a successful `upload` | `upload` |
| `screen_focus`, `gs_tex`, `clut_pool`, `slot_text`, `slot_off`, `slot_is_set`, `hidden` | arena pointers | carved from the arena by `load` | the runtime |

The focused node's geometry is `ctx->focus_nodes[ctx->focus]`, a `ps2ui_focus_node` with `x`, `y`, `w`, `h` in UI coordinates. The counters are described on [Telemetry](page:runtime/telemetry#reference-table).

### List struct

Every field is public. The list functions own `top` and `sel`; the app reads them.

| field | type | meaning |
|---|---|---|
| `prefix` | `const char *` | focus-name prefix; row `r` is `<prefix>r` |
| `rows` | `uint16_t` | baked rows, from the `data-repeat` count |
| `count` | `uint16_t` | items the app has |
| `top` | `uint16_t` | item shown in row 0 |
| `sel` | `uint16_t` | selected item index |

### Stats struct

Eight `uint32_t` counters, reset at the top of every `render` and complete when it returns.

| field | counts |
|---|---|
| `cmds` | command records walked |
| `prims` | primitives submitted to gsKit |
| `skipped_hidden` | command records skipped by runtime visibility |
| `slot_glyphs` | glyph quads composed by the slot pen |
| `slots_hidden` | slots suppressed by runtime visibility |
| `scissor_overflow` | scissor pushes refused for want of stack |
| `tex_unfilled` | textured draws skipped because a streamed slot has no texels |
| `vram_lost` | 1 when the frame skipped every textured draw because VRAM shrank below the uploaded footprint |

### Direction type

| value | direction |
|---|---|
| `PS2UI_UP` | up |
| `PS2UI_DOWN` | down |
| `PS2UI_LEFT` | left |
| `PS2UI_RIGHT` | right |

## Constants

The runtime has one fixed-size limit. Table counts are bounded by the format's `uint16_t` fields and the arena is sized from them, so no texture, slot, screen or list-row cap exists.

| name | value | meaning |
|---|---|---|
| `PS2UI_VERSION` | 7 | the blob format version; `load` refuses any other with `PS2UI_ERR_VERSION` |
| `PS2UI_MAX_SCISSOR_DEPTH` | 8 | scissor stack depth in `render`; the baker refuses deeper nesting |
| `PS2UI_LIST_NAME_MAX` | 64 | stack buffer for a built row name, prefix plus digits plus NUL; not a table bound |
| `PS2UI_ARENA_ALIGN` | 16 | required arena alignment; the CLUT region is a DMA source |
| `PS2UI_NONE` | `0xFFFF` | "no index" in every `uint16_t` index field |
| `PS2UI_VISIBLE_UNKNOWN` | -1 | `visible_get`'s answer for an unknown name |
| `PS2UI_OK` | 0 | success for every code-returning function |

The error values and their triggers are on [Errors and constants](page:runtime/errors-and-constants#error-codes).

## Ordering rules

| call | must follow | may precede | consequence of getting it wrong |
|---|---|---|---|
| `load` | nothing | everything | every other call reads a context `load` filled |
| `upload` | `load` | `render` | `render` after a refused or missing `upload` draws no textures and sets `vram_lost` |
| `clut_set` | `upload` | `render` | before `upload` it returns `PS2UI_ERR_STATE`; a second `upload` re-permutes every CLUT from the blob and reverts the swap |
| `tex_set` | `load` | `upload` or `render` | none; an unfilled slot is skipped and counted in `tex_unfilled` |
| `theme_set` | `load` | `upload` or `render` | none; it survives an `upload`, so do a CLUT swap last when using both |
| `list_set_count` | `list_init` | any list move | a list starts empty, so a move before `set_count` does nothing |
| `list_apply_visibility` | `list_set_count`, and every `list_move` or `list_select` | `render` | rows past the end keep their panel and border drawn |
| `visible_set` | `screen_set` to the screen that owns the node | `render` | the name resolves on the current screen only; from another screen it returns 0 |
| reading `ctx->stats` | one `render` | the next `render` | a composited frame ends holding only the last render's counters |
| `gsKit_TexManager_nextFrame` | the flip, once per frame | the next frame's first `render` | between two composited renders it ages the first screen's textures and re-uploads them every frame |

The blob and the arena outlive the context. The CLUT region is re-read by gsKit whenever it re-binds an evicted texture, which happens at render time. A `texels` buffer given to `tex_set` has the same lifetime. The full per-frame sequence is on [The frame loop](page:runtime/frame-loop#reference-table).
