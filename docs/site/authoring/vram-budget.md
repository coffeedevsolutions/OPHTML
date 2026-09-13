---
id: authoring/vram-budget
title: VRAM budget
description: The bake-time texture budget, the breakdown ps2ui-bake prints, and how to override it.
section: authoring
order: 22
version: 0.6.0
sources: [packages/baker/ps2ui_bake/vram.py, packages/baker/ps2ui_bake/cli.py, packages/baker/ps2ui_bake/check.py, packages/baker/ps2ui_bake/ps2ui.py, packages/baker/tests/test_baker.py, runtime/ps2ui.c, runtime/ps2ui.h, runtime/tests/test_runtime.c, tools/check-vram-model.py, CHANGELOG.md, fixtures/bench-stream/build.sh, examples/memcard/ps2ui.json]
---

# VRAM budget

## What it is

The Graphics Synthesizer holds 4 MiB of VRAM. Framebuffers and textures
share it. `ps2ui-bake` sums every texture and CLUT in the blob, charges
the sum against a budget, prints a per-texture breakdown, and returns 1
without writing the blob when the sum is over.

The budget is a bake-time decision, not a console-time one. The baker
knows every texture it emits, so an over-budget UI fails at the desk with
a table rather than on the console with an allocator error.

The default budget is 4 MiB minus three framebuffers at the canvas
resolution. Override it per project with `vramBudget`, or per command
with `--vram-budget`.

## Minimal example

Bake the memcard example and read the last five lines of the breakdown.

```
$ ps2ui-bake examples/memcard/build/library.json examples/memcard/build/saves.json -o memcard.uib
...
  tex[ 0] PSMT8     256x64   baked       16384 B payload ->   16384 B in pages
...
  tex[ 7] PSMT8      11x11   baked         121 B payload ->    8192 B in pages
...
  clut[0] PSMCT32  256 entries        ->    8192 B in pages
  framebuffers assumed: 2x draw/display + 1x Z @ 640x448 = 3440640 B
  payload 132667 B -> allocator 143104 B -> budget-charged 163840 B
  reclaimable 10437 B (7% of committed) -- the rest of the gap to 163840 B is the budget model's pessimism, which nothing allocates and P3c cannot reclaim
  textures 163840 B of 753664 B budget (21%)
ps2ui-bake: 2 screen(s), 1062 records, 11 textures (128 KiB baked), 1 CLUTs -> memcard.uib
ps2ui-bake: arena 1662 bytes (static uint8_t arena[1662] __attribute__((aligned(16))))
```

The canvas is 640x448. Three framebuffers take 3440640 B and leave
753664 B for textures. The eleven textures plus one CLUT book 163840 B
of that.

The arena line is a separate figure and is not part of the budget. It is
host RAM, and it is per blob.

The full transcript and its ordering live on
[ps2ui-bake](page:cli/ps2ui-bake#output).

## Reference table

Each texture row is
`tex[i] <format> <W>x<H> <kind> <N> B payload -> <M> B in pages`.

| column | meaning |
|---|---|
| `tex[i]` | index in the blob's texture table, the order `ps2ui_upload` walks |
| `<format>` | `PSMT8` or `PSMCT32` |
| `<W>x<H>` | texel dimensions after pre-scaling |
| `<kind>` | `baked` when texels sit in the blob, `streamed` when the app supplies them |
| `payload` | texel bytes: the baked data length, or the streamed slot's reservation |
| `in pages` | the 8 KiB page-rounded footprint, the figure the budget charges |
| `clut[i]` | one 256-entry PSMCT32 palette, charged one whole page |
| `framebuffers assumed` | two draw/display buffers plus one Z buffer at the canvas |
| `payload` total | every texel byte and palette byte in the blob |
| `allocator` | what `ps2ui_upload`'s preflight computes and gsKit commits |
| `budget-charged` | the page-rounded total the bake refuses against |
| `reclaimable` | allocator minus payload, the only part a packer could win back |
| `textures N B of M B budget` | the verdict, with the percentage of the budget used |

Three ways to set the budget:

| flag or key | effect |
|---|---|
| `ps2ui-bake --vram-budget BYTES` | replaces the default for that bake |
| `ps2ui-check --vram-budget BYTES` | replaces the default for that check |
| `vramBudget` in `ps2ui.json` | replaces the default for `ps2ui build` and `ps2ui check` alike |

The project key is documented with the rest of the file on
[the project file](page:authoring/project-file#reference-table).

## Behaviour

### Two cost models

The baker carries two models of what a texture costs, and the breakdown
prints both. The page model rounds to 8 KiB pages and is what the budget
charges. The allocator model charges 256-byte blocks rounded up to an
alignment group, which is what `gsKit_texture_size` does and therefore
what the runtime commits. A full page is the largest group, not the unit.

The page model is deliberately pessimistic. Refusing a blob that would
have fitted is the safe direction, because the console has no way to
report exhaustion once the upload starts.

The allocator port is checked against the vendored C rather than trusted.

```
$ python3 tools/check-vram-model.py
ok - alloc_size agrees with gsKit_texture_size on 45000 sizes
ok - and differs from the page model on 5120 of them, which is why both are reported
```

The gap between the two is why `reclaimable` exists as its own number.
On memcard the allocator commits 143104 B where the budget charges
163840 B, and only the 10437 B above the payload is a prize.

### Which number tex_set wants

`payload` is the `len` argument `ps2ui_tex_set` demands. It must equal
the slot's reservation exactly; the page-rounded figure is
`PS2UI_ERR_SIZE`. Bake the streaming bench fixture and read a slot row.

```
$ ps2ui-layout fixtures/bench-stream/ui/covers.html fixtures/bench-stream/ui/bench.css -o covers.json
$ ps2ui-layout fixtures/bench-stream/ui/dialog.html fixtures/bench-stream/ui/bench.css -o dialog.json
$ ps2ui-bake covers.json dialog.json -o bench.uib
...
  tex[ 1] PSMCT32   128x128  streamed    65536 B payload ->   65536 B in pages
...
  textures 368640 B of 753664 B budget (48%)
ps2ui-bake: 2 screen(s), 74 records, 9 textures (96 KiB baked + 256 KiB reserved by slots), 1 CLUTs -> bench.uib
```

Slot 1 is a 128x128 PSMCT32 cover. Pass 65536 as `len`. The two figures
match here because the texture already fills whole pages. The 11x11 icon
in the memcard bake above carries 121 B of payload and occupies 8192 B in
pages.

A streamed slot costs its reservation from the moment the blob loads. The
four covers are unfilled and still reserve 256 KiB. [Streaming
art](page:runtime/streaming-art#what-it-is) has the runtime call and the
host-side conversion.

### Overriding the budget

New in 0.6.0. The budget reaches the build and the check from one place.
Set `vramBudget` in the project file and both commands charge against it.

```
$ ps2ui build proj
...
  textures 163840 B of 262144 B budget (62%)
$ ps2ui check proj
...
ok 60 - VRAM 160 KiB within budget 256 KiB
```

`proj` is a copy of the memcard sources with `"vramBudget": 262144`.
Without the key the same blob checks against the default:
`ok 60 - VRAM 160 KiB within budget 736 KiB`.

Override the default when the real framebuffer layout is known. The
sample in this tree runs with ZBuffering off and holds two buffers, not
three. The third reservation is there so the default holds for a host
that turns Z on.

### When the default cannot exist

New in 0.6.0. Past a canvas width, three framebuffers do not fit in 4 MiB
and the default budget goes negative. The bake says so instead of blaming
the textures.

```
$ ps2ui-layout wide.html wide.css --canvas 796x448 -o wide.json
$ ps2ui-bake wide.json -o wide.uib
...
  framebuffers assumed: 2x draw/display + 1x Z @ 796x448 = 4472832 B
  the default budget does not exist at this canvas: three framebuffers at 796x448 need 4472832 B of 4194304 B total VRAM, so there is nothing left to charge textures against and an empty blob would fail here
  declare vramBudget (or --vram-budget) for the layout you actually run: with ZBuffering off the console holds two buffers, not three, which leaves 1212416 B
  payload 17408 B -> allocator 17408 B -> budget-charged 24576 B
  ...
  textures 24576 B, and no budget to charge them to
error: texture VRAM footprint exceeds budget (see breakdown above; override with --vram-budget)
```

796x448 is the canvas that gives square pixels at 16:9 on a 448-line
frame. Declaring the two-buffer figure clears it:
`ps2ui-bake wide.json -o wide.uib --vram-budget 1212416` prints
`textures 24576 B of 1212416 B budget (2%)` and exits 0.

Higher still, two framebuffers stop fitting and no budget helps. At 448
lines the two crossovers are 769 and 1153 columns.

```
$ python3 -c "
from ps2ui_bake import vram
V = vram.VRAM_TOTAL
w1 = next(w for w in range(1,4096) if 3*vram.framebuffer_size(w,448) >= V)
w2 = next(w for w in range(1,4096) if 2*vram.framebuffer_size(w,448) >= V)
print('first width where three framebuffers stop fitting:', w1)
print('first width where two framebuffers stop fitting:', w2)
print()
for l in vram.budget_note(1153,448): print(l)
"
first width where three framebuffers stop fitting: 769
first width where two framebuffers stop fitting: 1153

  two framebuffers at 1153x448 need 4358144 B of 4194304 B total VRAM, so this canvas cannot be displayed from GS VRAM under any Z setting
  no budget can be declared for it; a narrower canvas is the only fix
```

`test_the_advice_stops_when_two_buffers_stop_fitting` in
`packages/baker/tests/test_baker.py` pins both regimes and computes the
crossover rather than hard-coding it.

The note prints only when the budget was inherited. A caller who passed
`--vram-budget` has already made the decision it argues for.
`ps2ui-check` prints the same two lines as notes and marks the label:
`not ok 40 - VRAM 24 KiB within budget -272 KiB -- the default budget is
unusable at this canvas, see notes`. The checker's VRAM check is on
[ps2ui-check](page:cli/ps2ui-check#vram).

### On the console

`ps2ui_upload` preflights before it transfers anything. It sums
`gsKit_texture_size` per texture, adds one 16x16 PSMCT32 block per PSMT8
texture for the palette, and returns -1 when the sum plus the current
VRAM pointer exceeds 4 MiB. Nothing is transferred and `ctx->uploaded` stays 0.

The refusal is all-or-nothing by design. `gsKit_TexManager_bind` cannot
report exhaustion: its allocator evicts in a loop that never exits when
nothing can ever fit, so an over-budget blob is a hang rather than an
error code. `make -C runtime test` covers it.

```
ok 309 - upload reports failure when VRAM is exhausted, so step 9's expected 0 is a result and not a constant
ok 310 - and leaves the context not-uploaded, so a caller cannot render through a half-built texture table
ok 311 - upload refuses a budget that holds some textures but not all of them
ok 312 - and transfers nothing at all (0 transfers) -- all-or-nothing, because bind cannot fail and a partial table cannot render
ok 313 - and still leaves it not-uploaded
```

`ps2ui_render` re-tests the same fit every frame against
`ctx->vram_need`, because a host that allocates VRAM after the upload can
shrink what is left. When it no longer fits, every textured draw is
skipped and `stats.vram_lost` reads 1. The signatures are on the
[C API reference](page:runtime/api-reference#lifecycle). Check the return
of `ps2ui_upload` before rendering; [First
boot](page:runtime/first-boot#behaviour) turns that return into step 9.

## Limits and errors

| situation | what happens |
|---|---|
| sum over budget | `error: texture VRAM footprint exceeds budget (see breakdown above; override with --vram-budget)`, exit 1, no blob written |
| sum over budget at check time | `not ok - VRAM N KiB within budget M KiB`, exit 1 |
| default budget not positive | the two diagnostic lines, no percentage, and the bake fails even for an empty blob |
| canvas at or past 1153x448 | no budget can be declared; narrow the canvas |
| `ps2ui_upload` does not fit | returns -1, transfers nothing, leaves the context not uploaded |
| VRAM shrinks after upload | `ps2ui_render` skips every textured draw and sets `stats.vram_lost` |

The budget covers textures and CLUTs only. The arena is host RAM and is
counted separately. Its figure is per blob, not a constant: the bakes in
this session printed `arena 1662 bytes` for memcard, `arena 1875 bytes`
for the bench blob and `arena 1066 bytes` for the 796x448 blob.

The page model charges whole pages, so a texture smaller than a page
costs a whole one. The memcard bake charges 8192 B for an 11x11 icon of
121 B. Pack small art into one atlas image instead.

PSMT8 costs a quarter of PSMCT32 per texel, plus one palette per image.
[Images](page:authoring/images#what-it-costs) has the two bakes that
measure it.

## Related pages

| page | why |
|---|---|
| [ps2ui-bake](page:cli/ps2ui-bake#output) | the full transcript the breakdown sits in |
| [ps2ui-check](page:cli/ps2ui-check#vram) | the VRAM check and its label |
| [The project file](page:authoring/project-file#reference-table) | `vramBudget` and the keys around it |
| [Images](page:authoring/images#what-it-costs) | PSMT8 against PSMCT32, measured |
| [Streaming art](page:runtime/streaming-art#what-it-is) | filling a streamed slot with `ps2ui_tex_set` |
| [C API reference](page:runtime/api-reference#lifecycle) | `ps2ui_upload` and its return |
| [First boot](page:runtime/first-boot#behaviour) | step 9, where an upload refusal shows up |
