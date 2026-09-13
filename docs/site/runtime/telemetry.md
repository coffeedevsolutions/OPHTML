---
id: runtime/telemetry
title: Telemetry
description: What ps2ui_stats counts, when it resets, and how the sample turns it into one line per second.
section: runtime
order: 46
version: 0.6.0
sources: [runtime/ps2ui.h, runtime/ps2ui.c, runtime/sample/main.c, runtime/sample/Makefile, runtime/Makefile, runtime/tests/test_runtime.c]
---

# Telemetry

## What it is

`ps2ui_render` fills `ctx->stats`, a [`ps2ui_stats`](page:runtime/api-reference#stats-struct)
struct of eight `uint32_t` counters, every time it runs. The struct
comment states the scope directly: counters only. The runtime does no
timing, because host tests have no EE cycle counter to read. It does no
I/O either. Where a log goes is the app's decision, the same split
[dynamic text](page:authoring/dynamic-text#what-it-is) leaves to the app
for slot data. Counting costs one increment per command record walked,
plus one per primitive drawn, proportional to the frame and not to the API.

`ps2ui_render` resets `ctx->stats` to zero at entry, before it walks a
single command record. Read the fields after a render call and they
describe that render alone. Two `screen_set`/`render` pairs composite
one frame, [as the frame loop describes](page:runtime/frame-loop#behaviour).
A composited frame ends holding only the last render's numbers, not a
sum of both.

## Minimal example

Reading two fields after a render. This file compiled in this session
under the host flags.

```c
#include "ps2ui.h"
#include <stdio.h>

extern const unsigned char ui_uib[];
extern const unsigned int  size_ui_uib;

static ps2ui_ctx ui;
static uint8_t arena[16 * 1024] __attribute__((aligned(PS2UI_ARENA_ALIGN)));

void log_frame(GSGLOBAL *gs)
{
    ps2ui_render(&ui, gs);
    printf("cmds=%u prims=%u\n", ui.stats.cmds, ui.stats.prims);
}
```

```sh
$ cc -std=c99 -Wall -Wextra -Werror -Istub -Ivendor/gsKit -Ivendor/host-shim -I. -c x.c -o x.o
```

The compile exited 0 with no diagnostics. `cmds` and `prims` are plain
struct fields, so nothing but `ps2ui_render` needs to run first.

## Reference table

| field | counts | note |
|---|---|---|
| `cmds` | command records the current screen walked, SCISSOR_PUSH and SCISSOR_POP included | Equals the screen's `cmd_count` on a frame with nothing hidden |
| `prims` | primitives actually submitted to gsKit, quads and texquads together | Skips a texquad when the render-time VRAM check fails or its streamed slot is unfilled |
| `skipped_hidden` | command records skipped because runtime visibility hid their focus node | A hidden row's own suppressed slot text is not counted here, see `slots_hidden` |
| `slot_glyphs` | glyph quads the slot pen composed | A subset of `prims`; each glyph also counts once there |
| `slots_hidden` | slots suppressed by runtime visibility | Counted where the pen skips a hidden slot's text |
| `scissor_overflow` | SCISSOR_PUSH records refused for want of stack depth | Nonzero means a blob deeper than `PS2UI_MAX_SCISSOR_DEPTH` (8) slipped past the baker |
| `tex_unfilled` | textured draws skipped because a streamed slot has no texels yet | The ordinary state of a row that just scrolled in, not an error |
| `vram_lost` | 1 when this render skipped every textured draw because the uploaded footprint no longer fits | See [VRAM budget](page:authoring/vram-budget#on-the-console) |

## Behaviour

`make -C runtime test` proves the reset and the per-counter increments.

```
$ make -C runtime test
...
ok 174 - stats.prims agrees with the stub's independent count
ok 175 - stats.cmds is the current screen's record count
ok 176 - a baked blob never overflows the scissor stack
ok 177 - nothing hidden, nothing skipped
ok 178 - slot glyphs are a subset of the stub's textured prims
ok 179 - stats.prims still agrees after hiding a node
ok 180 - hidden records are counted, not lost
ok 181 - stats reset every frame
...
1..410
PASS: 410 checks, 0 failure(s)
```

Hiding a focus node moves its records from `prims` to `skipped_hidden`
rather than dropping them. `vram_lost` has one write site, right after
the reset. A render that cannot fit VRAM sets it every time, so it
never keeps a stale zero from an earlier frame. Past that point
`ps2ui_render` touches `ctx->stats` only to increment the walk counters.

Build the sample with `TELEMETRY=1` for a once-a-second log line on
stdout, meant for [the sample build](page:runtime/integrating#behaviour):

```sh
$ make -C runtime/sample TELEMETRY=1 EE_BIN=telemetry.elf
```

`TELEMETRY=1` adds `-DPS2UI_SAMPLE_TELEMETRY` to the EE build flags.
`make -C runtime syntax-check` compiles this variant on the host, with no
EE toolchain and no console to print to:

```
$ make -C runtime syntax-check
...
ok - sample compiles: -DPS2UI_SAMPLE_TELEMETRY
...
```

Enabled, the sample times only the `ps2ui_render` call around each frame
with the EE's COP0 count register, and aggregates every frame the
interval saw before printing:

```
ps2ui-telemetry frame=%u fps=%u.%u miss=%u ee_us(min/avg/max)=%u/%u/%u prims=%u hidden=%u slotg=%u slothid=%u sciov=%u vramlost=%u
```

| token | meaning | aggregation |
|---|---|---|
| `frame` | frame counter at print time | running total, never reset |
| `fps` | frames divided by elapsed wall time in the interval | one decimal, computed from the interval sum |
| `miss` | frames whose wall-clock loop time, vsync included, exceeded one 60 Hz field plus 10 percent | count of frames over threshold in the interval |
| `ee_us` | microseconds `ps2ui_render` itself took, min, avg and max | avg divides the interval's summed render time by frame count |
| `prims` | peak `stats.prims` seen in the interval | running max |
| `hidden` | peak `stats.skipped_hidden` seen in the interval | running max |
| `slotg` | peak `stats.slot_glyphs` seen in the interval | running max |
| `slothid` | peak `stats.slots_hidden` seen in the interval | running max |
| `sciov` | `stats.scissor_overflow` summed over the interval | running sum |
| `vramlost` | `stats.vram_lost` OR-ed over the interval | logical OR, so one bad frame in an otherwise clean second still reads 1 |

Peaks and the sum answer different questions. `prims`, `hidden`, `slotg`
and `slothid` size a budget, so the worst single frame is what matters.
`sciov` and `vramlost` are alarms, so any frame tripping them in the
interval must show, which a max would hide behind a later good frame.
Every aggregate resets to its start value once the line prints, so each
line describes exactly one elapsed second, not a running average since
boot.

## Limits and errors

`ps2ui_stats` is counters only. It carries no timestamps, no history
across frames, and no aggregation of its own. A caller wanting fps,
peaks, or a log line builds them from the eight counters, the way the
sample's `TELEMETRY` build does. `scissor_overflow` and `slots_hidden`
have no dedicated host test isolating them by name. Both are exercised
only as part of the wider visibility and scissor test suites.

## Related pages

| page | why |
|---|---|
| [C API reference](page:runtime/api-reference#stats-struct) | The struct field by field, and where `ps2ui_render` sits among the other calls |
| [The frame loop](page:runtime/frame-loop#behaviour) | Why the reset happens at entry and what a composited frame leaves in `ctx->stats` |
| [Integrating the runtime](page:runtime/integrating#behaviour) | The sample Makefile, `TELEMETRY=1`, and the other build variants |
| [Moving and hiding](page:runtime/moving-and-hiding#behaviour) | What sets `skipped_hidden` and `slots_hidden` |
| [VRAM budget](page:authoring/vram-budget#on-the-console) | The preflight `vram_lost` reports against |
