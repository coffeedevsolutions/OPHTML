---
id: runtime/frame-loop
title: The frame loop
description: Size the arena, load the blob, upload once, and what ps2ui_render guarantees on every frame after that.
section: runtime
order: 41
version: 0.8.0
sources: [runtime/ps2ui.h, runtime/ps2ui.c, runtime/sample/main.c, runtime/tests/test_runtime.c, packages/baker/ps2ui_bake/cli.py, packages/baker/ps2ui_bake/check.py, README.md]
---

# The frame loop

## What it is

The runtime opens a blob once and replays it every frame. Setup is three
calls: size an arena, `ps2ui_load`, `ps2ui_upload`. The frame is one call
into `ps2ui_render` between the host's own clear and its own flip.

Nothing is copied. The blob and the arena stay the caller's, and the
context points into both. There is no unload, no free and no destroy
entry point. Teardown is the app dropping two buffers it already owns.

`ps2ui_render` never clears and never allocates. The host keeps the
background, the flip and the texture manager's per-frame tick. Every call
in the loop below belongs to the app except the render.

## Minimal example

The loop from [main.c](repo:runtime/sample/main.c#L1671), with both
checks. This file compiled in this session under the host flags.

```c
#include "ps2ui.h"

extern const unsigned char ui_uib[];   /* bin2c of the baked blob */
extern const unsigned int  size_ui_uib;

static ps2ui_ctx ui;
static uint8_t arena[16 * 1024] __attribute__((aligned(PS2UI_ARENA_ALIGN)));

int frame_loop(GSGLOBAL *gs)
{
    int rc = ps2ui_load(&ui, ui_uib, size_ui_uib, arena, sizeof arena);
    if (rc != PS2UI_OK)
        return rc;                     /* solid red in the sample */
    if (ps2ui_upload(&ui, gs) != 0)
        return -1;                     /* solid yellow in the sample */
    for (;;) {
        gs->PrimAlphaEnable = GS_SETTING_OFF;
        gsKit_clear(gs, GS_SETREG_RGBAQ(0x0a, 0x0e, 0x1a, 0x80, 0x00));
        gs->PrimAlphaEnable = GS_SETTING_ON;
        ps2ui_render(&ui, gs);
        gsKit_queue_exec(gs);
        gsKit_sync_flip(gs);
        gsKit_TexManager_nextFrame(gs);
    }
}
```

```sh
$ cc -std=c99 -Wall -Wextra -Werror -Istub -Ivendor/gsKit -Ivendor/host-shim -I. -c x.c -o x.o
```

The compile exited 0 with no diagnostics.

Both failures are fatal in the sample. A load error loops on a solid red
clear. An upload refusal loops on a solid yellow one. The colours are
[first boot](page:runtime/first-boot#before-you-start) signals, so a console with
no serial line still names the stage that failed.

Blending is off across the clear on purpose. gsKit does not save and
restore `PrimAlphaEnable` around `gsKit_clear`, and on frame 0 the GS still
holds gsKit's default blend. A background clear has nothing to composite
against, so the bracket turns the question off rather than answering it.

### Sizing the arena

`ps2ui-bake` prints the figure the blob needs. Paste it, or keep a static
buffer above it and let `ps2ui_load` report `PS2UI_ERR_ARENA` when it is
short. The sample takes the second route with 16 KiB.

```sh
$ ps2ui-bake library.json saves.json -o ui.uib
...
ps2ui-bake: 2 screen(s), 1062 records, 11 textures (128 KiB baked), 1 CLUTs -> ui.uib
ps2ui-bake: arena 1662 bytes (static uint8_t arena[1662] __attribute__((aligned(16))))
```

That number is this blob's, on the EE. A different blob needs a different
one, and so does a different pointer width. `ps2ui-check` prints both:

```sh
$ ps2ui-check ui.uib
# arena: 1662 bytes on the EE (1750 on a 64-bit host; GSTEXTURE holds pointers, so the two differ)
...
```

`ps2ui_arena_size` answers the same question at runtime from the blob in
hand. It returns 0 when the header is unreadable or the tables do not fit
the buffer, which also reads as "do not call load".

## Reference table

| step | call | must hold |
|---|---|---|
| 1 | `ps2ui_arena_size(data, size)` | A return of 0 means the blob is unusable; skip the load |
| 2 | `static uint8_t arena[N] __attribute__((aligned(PS2UI_ARENA_ALIGN)))` | `N` is at least the arena size; the buffer outlives every render |
| 3 | `ps2ui_load(&ui, data, size, arena, sizeof arena)` | Returns `PS2UI_OK`; the blob stays alive and unmoved afterwards |
| 4 | `ps2ui_upload(&ui, gs)` | Returns 0; runs once, after gsKit init and before the first render |
| 5 | `gs->PrimAlphaEnable = GS_SETTING_OFF` | Brackets the clear, so frame 0 does not composite it |
| 6 | `gsKit_clear(gs, ...)` | The app owns the background; the runtime draws no ground |
| 7 | `gs->PrimAlphaEnable = GS_SETTING_ON` | Closes the bracket before any blended draw |
| 8 | `ps2ui_render(&ui, gs)` | Runs after the clear; read `ctx->stats` before the next render |
| 9 | `gsKit_queue_exec(gs)` | Flushes the frame's primitives |
| 10 | `gsKit_sync_flip(gs)` | Waits for vsync and flips |
| 11 | `gsKit_TexManager_nextFrame(gs)` | Once per frame, after the flip, never between two renders |

Every call is described on the [C API reference](page:runtime/api-reference#lifecycle).

## Behaviour

`make -C runtime test` proves the guarantees below.

```
$ make -C runtime test
...
ok 85 - render sets the GS blend mode rather than inheriting it
ok 86 - and sets it to (Cs - Cd) * As >> 7 + Cd
ok 87 - render turns PrimAlphaEnable on, so TEX0.TCC keeps the atlas alpha a host left off
ok 88 - all primitives inside the canvas
ok 89 - scissor restored to full canvas after replay
...
ok 181 - stats reset every frame
...
ok 271 - compositing two screens draws the sum: render adds to the frame, it does not own it
ok 272 - and render issued no clear, which is the guarantee the sum above only depends on
ok 273 - and issued no residency ageing tick: nextFrame is the frame loop's, once per frame, or the overlay ages the base
ok 274 - a composited frame leaves the scissor at full canvas, so the next drawer inherits the whole screen and not the last clip
...
1..410
PASS: 410 checks, 0 failure(s)
```

| guarantee | consequence |
|---|---|
| `ps2ui_render` writes the GS `ALPHA` register every call | A host that changed the blend between frames cannot invert the UI's alpha |
| It sets `PrimAlphaEnable` to `GS_SETTING_ON` every call | gsKit feeds the field to `TEX0.TCC`, so glyph atlas alpha survives a host that left it off |
| It never clears | Two `screen_set` and `render` pairs composite into one frame |
| It leaves the scissor at the full canvas | A caller drawing after it inherits the whole screen, not the last clip inside the UI |
| Every primitive lands inside the canvas rectangle | Geometry cannot escape the display edge, offset or not |
| It resets `ctx->stats` at entry | The counters describe one render; read them between two renders to sum a frame |
| It never ages texture residency | `gsKit_TexManager_nextFrame` stays the app's call, once after the flip |
| It binds every texture it draws | A texture manager reset heals by re-transfer instead of drawing from stale VRAM |
| A refused `ps2ui_load` never writes the arena | The same buffer can be handed to the next attempt |
| Nothing is copied out of the blob or the arena | Both must stay alive and unmoved, and there is nothing to unload |

The blend assertion exists because the equation was wrong on hardware for
the renderer's whole life. [First boot](page:runtime/first-boot#before-you-start)
carries that history.

Two renders in one frame are the dialog technique, covered on
[screens and overlays](page:authoring/screens-and-overlays#behaviour). The
per-render counters are read on
[telemetry](page:runtime/telemetry#what-it-is).

## Limits and errors

Two return conventions meet in this loop. `ps2ui_load` returns
`PS2UI_OK` or a negative `PS2UI_ERR_*` code. `ps2ui_upload` returns 0 or a
bare -1, and is the only function that does. `ps2ui_arena_size` returns a
byte count, or 0 for a blob it cannot size.

| code | value | triggered by | fix |
|---|---|---|---|
| `PS2UI_ERR_ARENA` | -9 | `arena` is NULL, or `arena_size` is below `ps2ui_arena_size()` | Grow the buffer to the figure the bake printed |
| `PS2UI_ERR_ALIGN` | -8 | The arena, or the blob's address, is not 16-aligned | Add `__attribute__((aligned(PS2UI_ARENA_ALIGN)))` to both |
| `PS2UI_ERR_TOO_MANY` | -5 | The blob's counts are legal but the carve exceeds the target's address space | Split the UI across blobs |
| (upload) | -1 | The texture sum plus `gs->CurrentPointer` passes 4 MiB | Cut texture bytes, or raise the budget the bake checks |

The full catalogue and the order `ps2ui_load` checks in are on
[errors and constants](page:runtime/errors-and-constants#error-codes).

An upload refusal is all or nothing. It transfers zero textures and leaves
the context not uploaded, because a half-built texture table is a worse
state than a refused one. The preflight is load-bearing rather than
polite: `gsKit_TexManager_bind` cannot report exhaustion, and an
over-budget blob hangs the console instead of returning. Budget the bytes
at bake time on [VRAM budget](page:authoring/vram-budget#reference-table).

A render after a refused upload is safe and empty. It skips every textured
draw, still draws untextured quads, and sets `stats.vram_lost` to 1. The
same happens when a host allocation shrinks VRAM below the footprint the
upload approved.

Call `ps2ui_upload` once. It sets `ctx->uploaded` and never reads it, so a
second call re-permutes every CLUT straight from the blob and silently
reverts a `ps2ui_clut_set` swap. Nothing in this repository calls it
twice.

A streamed texture's VRAM is reserved by the preflight, but nothing
transfers until `ps2ui_tex_set` names its texels. An unfilled slot draws
nothing and increments `stats.tex_unfilled`.

`PS2UI_VERSION` is the frozen blob format version, 7. `ps2ui_load` refuses
any other value with `PS2UI_ERR_VERSION`. Baker and runtime agree because
`ps2ui vendor-runtime` ships both files out of one package, not because
the macro is compared across the seam.

## Related pages

| page | why |
|---|---|
| [C API reference](page:runtime/api-reference#function-tables-by-group) | Every call in the loop, with its scope and ordering rules |
| [Errors and constants](page:runtime/errors-and-constants#error-codes) | Every code, what triggers it, and the load check order |
| [Screens and overlays](page:authoring/screens-and-overlays#behaviour) | Two renders in one frame, and what the overlay owns |
| [VRAM budget](page:authoring/vram-budget#reference-table) | The budget the upload preflight enforces |
| [Telemetry](page:runtime/telemetry#what-it-is) | `ps2ui_stats` and the sample's on-screen readout |
| [First boot](page:runtime/first-boot#before-you-start) | The red and yellow screens, and the blend fault history |
| [Deploying](page:runtime/deploying#what-it-is) | From an ELF to a console |
